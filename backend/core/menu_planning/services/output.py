"""Output generation for recommendations."""

from collections import defaultdict
from datetime import datetime


THEME_DISPLAY = {
    'super-bowl': ('Super Bowl', '🏈'),
    'mardi-gras': ('Mardi Gras', '🎭'),
    'valentines': ("Valentine's Day", '❤️'),
    'fish-friday': ('Fish Friday', '🐟'),
    'black-history-month': ('Black History Month', '✊'),
    'heart-healthy': ('Heart Healthy', '💚'),
}

FLAVOR_KEYWORDS = {
    'spicy': {'spicy', 'hot', 'buffalo', 'nashville', 'cajun'},
    'comfort': {'mac', 'cheese', 'melt', 'grilled', 'fried'},
    'hearty': {'beef', 'pork', 'brisket', 'pulled', 'bbq'},
    'light': {'salad', 'grilled', 'fresh', 'veggie'},
    'indulgent': {'bacon', 'cheese', 'loaded', 'stuffed'},
}


def generate_why(rec: dict) -> str:
    """Generate plain-English explanation for recommendation."""
    parts = []
    scores = rec.get('scores', {})

    keyword_score = scores.get('keyword_fit', 0)
    if keyword_score >= 15:
        menu_kw = set(k.lower() for k in rec['current_item'].get('keywords', []))
        promo_kw = set(k.lower() for k in rec['promo_recipe'].get('keywords', []))
        shared = menu_kw & promo_kw

        flavor = None
        for f, words in FLAVOR_KEYWORDS.items():
            if shared & words:
                flavor = f
                break

        if flavor == 'spicy':
            parts.append("Both are spicy favorites")
        elif flavor == 'comfort':
            parts.append("Both are comfort food")
        elif flavor == 'hearty':
            parts.append("Both are hearty and filling")
        elif shared:
            sample = list(shared)[:2]
            parts.append(f"Similar style ({', '.join(sample)})")

    station_score = scores.get('station_fit', 0)
    if station_score >= 25:
        parts.append("Same station")
    elif station_score >= 15:
        parts.append("Compatible station")

    date_score = scores.get('date_relevance', 0)
    if date_score >= 25:
        parts.append("Perfect timing for theme")
    elif date_score >= 15:
        parts.append("Good timing")

    dietary_score = scores.get('dietary_value', 0)
    if dietary_score >= 10:
        dietary = rec['promo_recipe'].get('dietary', [])
        if dietary:
            parts.append(f"Adds {'/'.join(dietary)} option")

    return ". ".join(parts) + "." if parts else "Good overall fit."


def select_tiers(theme_recs: list[dict]) -> tuple[list[dict], list[dict]]:
    """Select top picks and also-consider items."""
    seen_refs = {}
    for rec in sorted(theme_recs, key=lambda x: -x['total_score']):
        ref = rec['promo_recipe']['master_ref']
        if ref not in seen_refs:
            seen_refs[ref] = rec

    unique_recs = list(seen_refs.values())

    top_picks = []
    seen_stations = set()
    for rec in unique_recs:
        station = rec['current_item'].get('station_group', 'unknown')
        if station not in seen_stations and len(top_picks) < 2:
            if rec['total_score'] >= 70 or len(top_picks) == 0:
                top_picks.append(rec)
                seen_stations.add(station)

    if not top_picks and unique_recs:
        top_picks = [unique_recs[0]]

    top_refs = {r['promo_recipe']['master_ref'] for r in top_picks}
    also_consider = [
        r for r in unique_recs
        if r['promo_recipe']['master_ref'] not in top_refs
        and r['total_score'] >= 55
    ][:3]

    return top_picks, also_consider


def generate_calendar_markdown(
    recommendations: list[dict],
    unit_config: dict,
    month: str
) -> str:
    """Generate markdown calendar output."""
    lines = []
    DIVIDER = "═" * 65

    month_dt = datetime.strptime(month + '-01', '%Y-%m-%d')
    month_name = month_dt.strftime('%B %Y')
    unit_name = unit_config.get('name', unit_config.get('unit_id', 'Unknown'))

    lines.append(DIVIDER)
    lines.append(f"  {month_name} Menu Recommendations")
    lines.append(f"  {unit_name}")
    lines.append(DIVIDER)
    lines.append(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")

    by_theme = defaultdict(list)
    for rec in recommendations:
        theme = rec['promo_recipe'].get('theme', 'other')
        by_theme[theme].append(rec)

    def theme_sort_key(theme):
        recs = by_theme[theme]
        dates = [r['date'] for r in recs]
        return min(dates) if dates else '9999'

    for theme in sorted(by_theme.keys(), key=theme_sort_key):
        theme_recs = by_theme[theme]

        if theme in THEME_DISPLAY:
            theme_name, emoji = THEME_DISPLAY[theme]
        else:
            theme_name = theme.replace('-', ' ').title()
            emoji = '📋'

        dates = sorted(set(r['date'] for r in theme_recs))
        date_strs = []
        for d in dates[:4]:
            dt = datetime.strptime(d, '%Y-%m-%d')
            date_strs.append(dt.strftime('%a %b %d'))
        dates_display = ', '.join(date_strs)

        lines.append("")
        lines.append(DIVIDER)
        lines.append(f"  {emoji} {theme_name.upper()}")
        lines.append(f"  Feature on: {dates_display}")
        lines.append(DIVIDER)

        top_picks, also_consider = select_tiers(theme_recs)

        if top_picks:
            lines.append("")
            lines.append("  TOP PICK")
            lines.append("")

            for rec in top_picks:
                promo = rec['promo_recipe']
                current = rec['current_item']

                lines.append(f"  {promo.get('name', '')[:50]}")
                lines.append(f"    → replaces {current.get('item_name', '')[:35]}")
                lines.append("  " + "─" * 61)
                lines.append(f"  Why: {generate_why(rec)}")

                details = []
                if promo.get('cost'):
                    details.append(f"${promo['cost']:.2f}")
                if promo.get('station'):
                    details.append(promo['station'][:20])
                if promo.get('master_ref'):
                    details.append(f"#{promo['master_ref']}")
                lines.append(f"  {' | '.join(details)}")
                lines.append("")

        if also_consider:
            lines.append("")
            lines.append("  ALSO CONSIDER")
            lines.append("")

            for rec in also_consider:
                promo = rec['promo_recipe']
                current = rec['current_item']

                lines.append(f"  • {promo.get('name', '')[:40]}")
                lines.append(f"    → replaces {current.get('item_name', '')[:25]}")

                why = generate_why(rec).split('.')[0] + '.'
                cost_str = f"${promo['cost']:.2f}" if promo.get('cost') else ""
                lines.append(f"    {why} {cost_str} | #{promo.get('master_ref', '')}")
                lines.append("")

        lines.append("─" * 65)

    return '\n'.join(lines)


def generate_flags_markdown(flags: dict) -> str:
    """Generate flags markdown output."""
    lines = []

    lines.append("# Needs Review")
    lines.append("")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")

    total = flags.get('total_flags', 0)
    if total == 0:
        lines.append("No flags - all recommendations look good!")
        return '\n'.join(lines)

    lines.append(f"**Total flags:** {total}")
    lines.append("")

    if flags.get('theme_collisions'):
        lines.append("## Theme Collisions")
        lines.append("")
        for flag in flags['theme_collisions']:
            lines.append(f"- **{flag['date']}:** {', '.join(flag['themes'])}")
        lines.append("")

    if flags.get('weekday_repeats'):
        lines.append("## Weekday Repeats")
        lines.append("")
        for flag in flags['weekday_repeats']:
            lines.append(f"- **{flag['day_of_week']}:** '{flag['theme']}' in weeks {flag['weeks']}")
        lines.append("")

    if flags.get('ingredient_collisions'):
        lines.append("## Ingredient Family Collisions")
        lines.append("")
        for flag in flags['ingredient_collisions']:
            lines.append(f"### Week {flag['week']}: {flag['family'].title()}")
            for ref, name in flag['recipes']:
                lines.append(f"- {name} ({ref})")
            lines.append("")

    return '\n'.join(lines)
