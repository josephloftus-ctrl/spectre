"""Guardrails for recommendation quality control."""

import yaml
from collections import defaultdict
from pathlib import Path


def load_keyword_families(config_path: Path = None) -> dict:
    """Load ingredient family definitions."""
    if config_path is None:
        config_path = Path(__file__).parent.parent / "config" / "keywords.yaml"

    if config_path.exists():
        with open(config_path) as f:
            config = yaml.safe_load(f)
            return config.get('families', {})
    return {}


def detect_theme_collisions(recommendations: list[dict]) -> list[dict]:
    """Flag multiple conflicting themes on same day."""
    event_themes = {'super-bowl', 'mardi-gras', 'valentines', 'fish-friday'}

    by_date = defaultdict(list)
    for rec in recommendations:
        by_date[rec['date']].append(rec)

    flags = []
    for date, recs in by_date.items():
        day_themes = set()
        for rec in recs:
            theme = rec['promo_recipe'].get('theme')
            if theme in event_themes:
                day_themes.add(theme)

        if len(day_themes) > 1:
            flags.append({
                'type': 'theme_collision',
                'date': date,
                'themes': list(day_themes),
                'message': f"Multiple event themes on {date}: {', '.join(day_themes)}"
            })

    return flags


def detect_weekday_repeats(recommendations: list[dict]) -> list[dict]:
    """Flag same theme on same weekday in consecutive weeks."""
    by_weekday_theme = defaultdict(list)

    for rec in recommendations:
        day = rec.get('day_of_week')
        theme = rec['promo_recipe'].get('theme')
        week = rec.get('week_number')

        if day and theme and week:
            by_weekday_theme[(day, theme)].append((week, rec))

    flags = []
    for (day, theme), week_recs in by_weekday_theme.items():
        week_recs.sort(key=lambda x: x[0])

        for i in range(len(week_recs) - 1):
            week1, _ = week_recs[i]
            week2, _ = week_recs[i + 1]

            if week2 - week1 == 1:
                flags.append({
                    'type': 'weekday_repeat',
                    'day_of_week': day,
                    'theme': theme,
                    'weeks': [week1, week2],
                    'message': f"Theme '{theme}' on {day} in consecutive weeks"
                })

    return flags


def detect_ingredient_collisions(
    recommendations: list[dict],
    keyword_families: dict = None
) -> list[dict]:
    """Flag recipes sharing ingredient families in same week."""
    if keyword_families is None:
        keyword_families = load_keyword_families()

    keyword_to_family = {}
    for family, keywords in keyword_families.items():
        for kw in keywords:
            keyword_to_family[kw.lower()] = family

    by_week = defaultdict(list)
    for rec in recommendations:
        week = rec.get('week_number')
        if week:
            by_week[week].append(rec)

    flags = []
    for week, recs in by_week.items():
        recipe_families = defaultdict(list)

        for rec in recs:
            recipe_name = rec['promo_recipe'].get('name', '')
            recipe_keywords = rec['promo_recipe'].get('keywords', [])
            master_ref = rec['promo_recipe'].get('master_ref')

            for kw in recipe_keywords:
                kw_lower = kw.lower()
                if kw_lower in keyword_to_family:
                    family = keyword_to_family[kw_lower]
                    recipe_families[family].append((master_ref, recipe_name))

        for family, recipes in recipe_families.items():
            unique_refs = set(r[0] for r in recipes)
            if len(unique_refs) > 1:
                flags.append({
                    'type': 'ingredient_collision',
                    'week': week,
                    'family': family,
                    'recipes': list(set(recipes)),
                    'message': f"Week {week}: Multiple '{family}' items"
                })

    return flags


def apply_guardrail_penalties(recommendations: list[dict]) -> list[dict]:
    """Apply score penalties for guardrail violations."""
    weekday_themes = defaultdict(lambda: defaultdict(int))

    for rec in sorted(recommendations, key=lambda x: (x.get('week_number', 0), x['date'])):
        day = rec.get('day_of_week')
        theme = rec['promo_recipe'].get('theme')

        if day and theme:
            prior_uses = weekday_themes[day][theme]
            if prior_uses > 0:
                rec['scores']['weekday_repeat_penalty'] = -20
                rec['scores']['total'] += -20
                rec['total_score'] = rec['scores']['total']

            weekday_themes[day][theme] += 1

    return recommendations


def filter_recommendations(
    recommendations: list[dict],
    max_per_day: int = 5,
    max_per_station_per_day: int = 2,
    min_score: int = 50
) -> list[dict]:
    """Filter and limit recommendations."""
    filtered = [r for r in recommendations if r['total_score'] >= min_score]

    by_date = defaultdict(list)
    for rec in filtered:
        by_date[rec['date']].append(rec)

    result = []
    for date, recs in by_date.items():
        recs.sort(key=lambda x: -x['total_score'])

        station_counts = defaultdict(int)
        day_count = 0

        for rec in recs:
            station = rec['current_item'].get('station_group', 'unknown')

            if day_count >= max_per_day:
                break
            if station_counts[station] >= max_per_station_per_day:
                continue

            result.append(rec)
            station_counts[station] += 1
            day_count += 1

    return result


def generate_flags_report(recommendations: list[dict]) -> dict:
    """Generate comprehensive flags report."""
    theme_collisions = detect_theme_collisions(recommendations)
    weekday_repeats = detect_weekday_repeats(recommendations)
    ingredient_collisions = detect_ingredient_collisions(recommendations)

    return {
        'theme_collisions': theme_collisions,
        'weekday_repeats': weekday_repeats,
        'ingredient_collisions': ingredient_collisions,
        'total_flags': len(theme_collisions) + len(weekday_repeats) + len(ingredient_collisions)
    }
