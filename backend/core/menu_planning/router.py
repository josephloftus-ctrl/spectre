"""FastAPI router for menu planning endpoints."""

import yaml
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .database import get_session, init_db
from .schemas import (
    Unit, CycleMenu, CycleMenuItem, PromoPacket, PromoRecipe,
    Recommendation, ProcessingStatus
)
from .models import (
    UnitCreate, UnitResponse, CycleMenuResponse, CycleMenuListResponse,
    PromoPacketResponse, RecommendationResponse, GenerateRequest, ThemesResponse
)
from .services import (
    parse_cycle_menu, parse_promo_pdf, extract_theme_from_filename,
    generate_recommendations, apply_guardrail_penalties,
    filter_recommendations, generate_flags_report,
    generate_calendar_markdown, generate_flags_markdown, generate_why
)

router = APIRouter(prefix="/menu-planning", tags=["menu-planning"])

CONFIG_PATH = Path(__file__).parent / "config"
UPLOAD_PATH = Path(__file__).parent.parent.parent.parent / "data" / "menu_planning_uploads"


@router.on_event("startup")
async def startup():
    """Initialize database on startup."""
    await init_db()
    UPLOAD_PATH.mkdir(parents=True, exist_ok=True)


# === Units ===

@router.get("/units", response_model=list[UnitResponse])
async def list_units(session: AsyncSession = Depends(get_session)):
    """List all units."""
    result = await session.execute(select(Unit))
    return result.scalars().all()


@router.post("/units", response_model=UnitResponse)
async def create_unit(unit: UnitCreate, session: AsyncSession = Depends(get_session)):
    """Create a new unit."""
    db_unit = Unit(**unit.model_dump())
    session.add(db_unit)
    await session.commit()
    await session.refresh(db_unit)
    return db_unit


@router.get("/units/{unit_id}", response_model=UnitResponse)
async def get_unit(unit_id: str, session: AsyncSession = Depends(get_session)):
    """Get a unit by ID."""
    result = await session.execute(select(Unit).where(Unit.id == unit_id))
    unit = result.scalar_one_or_none()
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")
    return unit


@router.put("/units/{unit_id}", response_model=UnitResponse)
async def update_unit(unit_id: str, unit: UnitCreate, session: AsyncSession = Depends(get_session)):
    """Update a unit."""
    result = await session.execute(select(Unit).where(Unit.id == unit_id))
    db_unit = result.scalar_one_or_none()
    if not db_unit:
        raise HTTPException(status_code=404, detail="Unit not found")

    for key, value in unit.model_dump().items():
        setattr(db_unit, key, value)

    await session.commit()
    await session.refresh(db_unit)
    return db_unit


# === Themes ===

@router.get("/themes", response_model=ThemesResponse)
async def get_themes():
    """Get theme definitions."""
    themes_path = CONFIG_PATH / "themes.yaml"
    if themes_path.exists():
        with open(themes_path) as f:
            themes = yaml.safe_load(f) or {}
    else:
        themes = {}
    return ThemesResponse(themes=themes)


@router.put("/themes")
async def update_themes(themes: dict):
    """Update theme definitions."""
    themes_path = CONFIG_PATH / "themes.yaml"
    with open(themes_path, 'w') as f:
        yaml.dump(themes, f)
    return {"status": "ok"}


# === Cycle Menus ===

@router.post("/cycle-menus/upload")
async def upload_cycle_menu(
    unit_id: str,
    month: str,
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    session: AsyncSession = Depends(get_session)
):
    """Upload a cycle menu xlsx file."""
    # Verify unit exists
    result = await session.execute(select(Unit).where(Unit.id == unit_id))
    unit = result.scalar_one_or_none()
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")

    # Save file
    file_path = UPLOAD_PATH / f"{unit_id}_{month}_{file.filename}"
    content = await file.read()
    file_path.write_bytes(content)

    # Create record
    cycle_menu = CycleMenu(
        unit_id=unit_id,
        month=month,
        filename=file.filename,
        status=ProcessingStatus.PENDING
    )
    session.add(cycle_menu)
    await session.commit()
    await session.refresh(cycle_menu)

    # Process in background
    if background_tasks:
        background_tasks.add_task(
            process_cycle_menu,
            cycle_menu.id,
            file_path,
            unit.station_groups
        )

    return {"id": cycle_menu.id, "status": "processing"}


async def process_cycle_menu(menu_id: int, file_path: Path, station_groups: dict):
    """Background task to process cycle menu."""
    from .database import async_session

    async with async_session() as session:
        result = await session.execute(select(CycleMenu).where(CycleMenu.id == menu_id))
        menu = result.scalar_one()

        try:
            menu.status = ProcessingStatus.PROCESSING
            await session.commit()

            items = parse_cycle_menu(file_path, {'station_groups': station_groups})

            for item in items:
                db_item = CycleMenuItem(
                    cycle_menu_id=menu_id,
                    date=item['date'],
                    day_of_week=item['day_of_week'],
                    week_number=item['week_number'],
                    meal=item['meal'],
                    station=item['station'],
                    station_group=item['station_group'],
                    item_name=item['item_name'],
                    keywords=item['keywords']
                )
                session.add(db_item)

            menu.status = ProcessingStatus.COMPLETED
            await session.commit()

        except Exception as e:
            menu.status = ProcessingStatus.ERROR
            menu.error_message = str(e)
            await session.commit()


@router.get("/cycle-menus", response_model=list[CycleMenuListResponse])
async def list_cycle_menus(
    unit_id: Optional[str] = None,
    month: Optional[str] = None,
    session: AsyncSession = Depends(get_session)
):
    """List cycle menus."""
    query = select(CycleMenu)
    if unit_id:
        query = query.where(CycleMenu.unit_id == unit_id)
    if month:
        query = query.where(CycleMenu.month == month)

    result = await session.execute(query.options(selectinload(CycleMenu.items)))
    menus = result.scalars().all()

    return [
        CycleMenuListResponse(
            id=m.id,
            unit_id=m.unit_id,
            month=m.month,
            filename=m.filename,
            uploaded_at=m.uploaded_at,
            status=m.status.value,
            item_count=len(m.items)
        )
        for m in menus
    ]


@router.get("/cycle-menus/{menu_id}", response_model=CycleMenuResponse)
async def get_cycle_menu(menu_id: int, session: AsyncSession = Depends(get_session)):
    """Get a cycle menu with items."""
    result = await session.execute(
        select(CycleMenu)
        .where(CycleMenu.id == menu_id)
        .options(selectinload(CycleMenu.items))
    )
    menu = result.scalar_one_or_none()
    if not menu:
        raise HTTPException(status_code=404, detail="Cycle menu not found")

    return CycleMenuResponse(
        id=menu.id,
        unit_id=menu.unit_id,
        month=menu.month,
        filename=menu.filename,
        uploaded_at=menu.uploaded_at,
        status=menu.status.value,
        error_message=menu.error_message,
        items=[CycleMenuResponse.model_fields['items'].annotation.__args__[0].model_validate(i) for i in menu.items]
    )


@router.delete("/cycle-menus/{menu_id}")
async def delete_cycle_menu(menu_id: int, session: AsyncSession = Depends(get_session)):
    """Delete a cycle menu."""
    result = await session.execute(select(CycleMenu).where(CycleMenu.id == menu_id))
    menu = result.scalar_one_or_none()
    if not menu:
        raise HTTPException(status_code=404, detail="Cycle menu not found")

    await session.delete(menu)
    await session.commit()
    return {"status": "deleted"}


# === Promos ===

@router.post("/promos/upload")
async def upload_promo(
    month: str,
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    session: AsyncSession = Depends(get_session)
):
    """Upload a promo PDF."""
    theme = extract_theme_from_filename(file.filename)

    file_path = UPLOAD_PATH / f"promo_{month}_{file.filename}"
    content = await file.read()
    file_path.write_bytes(content)

    packet = PromoPacket(
        month=month,
        theme=theme,
        filename=file.filename,
        status=ProcessingStatus.PENDING
    )
    session.add(packet)
    await session.commit()
    await session.refresh(packet)

    if background_tasks:
        background_tasks.add_task(process_promo_packet, packet.id, file_path, month)

    return {"id": packet.id, "theme": theme, "status": "processing"}


async def process_promo_packet(packet_id: int, file_path: Path, month: str):
    """Background task to process promo PDF."""
    from .database import async_session

    async with async_session() as session:
        result = await session.execute(select(PromoPacket).where(PromoPacket.id == packet_id))
        packet = result.scalar_one()

        try:
            packet.status = ProcessingStatus.PROCESSING
            await session.commit()

            themes_path = CONFIG_PATH / "themes.yaml"
            themes_config = {}
            if themes_path.exists():
                with open(themes_path) as f:
                    themes_config = yaml.safe_load(f) or {}

            recipes = parse_promo_pdf(file_path, themes_config, month)

            for recipe in recipes:
                db_recipe = PromoRecipe(
                    packet_id=packet_id,
                    master_ref=recipe['master_ref'],
                    name=recipe['name'],
                    station=recipe['station'],
                    station_groups=recipe['station_groups'],
                    calories=recipe['calories'],
                    cost=recipe['cost'],
                    dietary=recipe['dietary'],
                    theme=recipe['theme'],
                    theme_dates=recipe['theme_dates'],
                    theme_window=recipe['theme_window'],
                    theme_all_month=recipe['theme_all_month'],
                    keywords=recipe['keywords']
                )
                session.add(db_recipe)

            packet.status = ProcessingStatus.COMPLETED
            await session.commit()

        except Exception as e:
            packet.status = ProcessingStatus.ERROR
            packet.error_message = str(e)
            await session.commit()


@router.get("/promos", response_model=list[PromoPacketResponse])
async def list_promos(
    month: Optional[str] = None,
    theme: Optional[str] = None,
    session: AsyncSession = Depends(get_session)
):
    """List promo packets."""
    query = select(PromoPacket)
    if month:
        query = query.where(PromoPacket.month == month)
    if theme:
        query = query.where(PromoPacket.theme == theme)

    result = await session.execute(query.options(selectinload(PromoPacket.recipes)))
    return result.scalars().all()


@router.get("/promos/{packet_id}", response_model=PromoPacketResponse)
async def get_promo(packet_id: int, session: AsyncSession = Depends(get_session)):
    """Get a promo packet with recipes."""
    result = await session.execute(
        select(PromoPacket)
        .where(PromoPacket.id == packet_id)
        .options(selectinload(PromoPacket.recipes))
    )
    packet = result.scalar_one_or_none()
    if not packet:
        raise HTTPException(status_code=404, detail="Promo packet not found")
    return packet


@router.delete("/promos/{packet_id}")
async def delete_promo(packet_id: int, session: AsyncSession = Depends(get_session)):
    """Delete a promo packet."""
    result = await session.execute(select(PromoPacket).where(PromoPacket.id == packet_id))
    packet = result.scalar_one_or_none()
    if not packet:
        raise HTTPException(status_code=404, detail="Promo packet not found")

    await session.delete(packet)
    await session.commit()
    return {"status": "deleted"}


# === Recommendations ===

@router.post("/recommendations/generate")
async def generate_recs(
    request: GenerateRequest,
    session: AsyncSession = Depends(get_session)
):
    """Generate recommendations for a unit and month."""
    # Get unit
    result = await session.execute(select(Unit).where(Unit.id == request.unit_id))
    unit = result.scalar_one_or_none()
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")

    # Get cycle menu
    result = await session.execute(
        select(CycleMenu)
        .where(CycleMenu.unit_id == request.unit_id)
        .where(CycleMenu.month == request.month)
        .where(CycleMenu.status == ProcessingStatus.COMPLETED)
        .options(selectinload(CycleMenu.items))
    )
    menu = result.scalar_one_or_none()
    if not menu:
        raise HTTPException(status_code=404, detail="No completed cycle menu found")

    # Get promos
    result = await session.execute(
        select(PromoPacket)
        .where(PromoPacket.month == request.month)
        .where(PromoPacket.status == ProcessingStatus.COMPLETED)
        .options(selectinload(PromoPacket.recipes))
    )
    packets = result.scalars().all()

    if not packets:
        raise HTTPException(status_code=404, detail="No completed promo packets found")

    # Convert to dicts
    cycle_items = [
        {
            'date': str(i.date),
            'day_of_week': i.day_of_week,
            'week_number': i.week_number,
            'meal': i.meal,
            'station': i.station,
            'station_group': i.station_group,
            'item_name': i.item_name,
            'keywords': i.keywords
        }
        for i in menu.items
    ]

    promo_recipes = []
    for p in packets:
        for r in p.recipes:
            promo_recipes.append({
                'master_ref': r.master_ref,
                'name': r.name,
                'station': r.station,
                'station_groups': r.station_groups,
                'calories': r.calories,
                'cost': float(r.cost) if r.cost else None,
                'dietary': r.dietary,
                'theme': r.theme,
                'theme_dates': r.theme_dates,
                'theme_window': r.theme_window,
                'theme_all_month': r.theme_all_month,
                'keywords': r.keywords
            })

    unit_config = {
        'unit_id': unit.id,
        'name': unit.name,
        'station_groups': unit.station_groups
    }

    # Generate
    recs = generate_recommendations(cycle_items, promo_recipes, unit_config, request.month)
    recs = apply_guardrail_penalties(recs)
    filtered = filter_recommendations(recs, max_per_day=request.max_per_day, min_score=request.min_score)
    flags = generate_flags_report(filtered)

    # Add why to each rec
    for rec in filtered:
        rec['why'] = generate_why(rec)

    # Save
    db_rec = Recommendation(
        cycle_menu_id=menu.id,
        config_snapshot={'min_score': request.min_score, 'max_per_day': request.max_per_day},
        results=filtered,
        flags=flags
    )
    session.add(db_rec)
    await session.commit()
    await session.refresh(db_rec)

    return {"id": db_rec.id, "count": len(filtered), "flags": flags['total_flags']}


@router.get("/recommendations", response_model=list[dict])
async def list_recommendations(session: AsyncSession = Depends(get_session)):
    """List recommendation runs."""
    result = await session.execute(select(Recommendation))
    recs = result.scalars().all()
    return [
        {
            'id': r.id,
            'cycle_menu_id': r.cycle_menu_id,
            'run_at': r.run_at,
            'result_count': len(r.results),
            'flag_count': r.flags.get('total_flags', 0)
        }
        for r in recs
    ]


@router.get("/recommendations/{rec_id}")
async def get_recommendation(rec_id: int, session: AsyncSession = Depends(get_session)):
    """Get recommendation details."""
    result = await session.execute(select(Recommendation).where(Recommendation.id == rec_id))
    rec = result.scalar_one_or_none()
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")

    return {
        'id': rec.id,
        'cycle_menu_id': rec.cycle_menu_id,
        'run_at': rec.run_at,
        'config_snapshot': rec.config_snapshot,
        'results': rec.results,
        'flags': rec.flags
    }


@router.get("/recommendations/{rec_id}/export")
async def export_recommendation(rec_id: int, session: AsyncSession = Depends(get_session)):
    """Export recommendation as markdown."""
    result = await session.execute(
        select(Recommendation)
        .where(Recommendation.id == rec_id)
    )
    rec = result.scalar_one_or_none()
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")

    # Get unit info
    result = await session.execute(
        select(CycleMenu).where(CycleMenu.id == rec.cycle_menu_id)
    )
    menu = result.scalar_one()

    result = await session.execute(select(Unit).where(Unit.id == menu.unit_id))
    unit = result.scalar_one()

    unit_config = {'unit_id': unit.id, 'name': unit.name}

    calendar_md = generate_calendar_markdown(rec.results, unit_config, menu.month)
    flags_md = generate_flags_markdown(rec.flags)

    return {
        'calendar': calendar_md,
        'flags': flags_md
    }
