"""
Scoring algorithm for menu replacement recommendations.

Factors (total 100 points):
- Date relevance: 25 points
- Station fit: 25 points
- Keyword fit: 20 points
- Cost delta: 15 points
- Dietary value: 10 points
- Variety bonus: 5 points
"""

from collections import Counter, defaultdict
from datetime import datetime, timedelta


def score_replacement(
    menu_item: dict,
    promo_recipe: dict,
    date: str,
    unit_config: dict,
    context: dict
) -> dict:
    """Score a potential menu item replacement."""
    scores = {
        'date_relevance': _score_date_relevance(promo_recipe, date),
        'station_fit': _score_station_fit(menu_item, promo_recipe),
        'keyword_fit': _score_keyword_fit(menu_item, promo_recipe),
        'cost_delta': _score_cost_delta(promo_recipe),
        'dietary_value': _score_dietary_value(promo_recipe, context),
        'variety_bonus': _score_variety_bonus(promo_recipe, context),
    }

    scores['total'] = sum(scores.values())
    scores['passes_threshold'] = scores['total'] >= 50

    return scores


def _score_date_relevance(promo_recipe: dict, date: str) -> int:
    """Score based on theme date alignment."""
    if promo_recipe.get('theme_all_month'):
        return 15

    theme_dates = promo_recipe.get('theme_dates', [])
    window = promo_recipe.get('theme_window', 0)

    if not theme_dates:
        return 0

    target_date = datetime.strptime(date, '%Y-%m-%d').date()
    min_dist = float('inf')

    for theme_date_str in theme_dates:
        theme_date = datetime.strptime(theme_date_str, '%Y-%m-%d').date()
        window_start = theme_date - timedelta(days=window)
        window_end = theme_date

        if window_start <= target_date <= window_end:
            return 25

        if target_date < window_start:
            dist = (window_start - target_date).days
        else:
            dist = (target_date - window_end).days

        min_dist = min(min_dist, dist)

    if min_dist <= 1:
        return 18
    elif min_dist <= 3:
        return 10
    return 0


def _score_station_fit(menu_item: dict, promo_recipe: dict) -> int:
    """Score based on station compatibility."""
    menu_group = menu_item.get('station_group')
    promo_groups = promo_recipe.get('station_groups', [])

    if not menu_group or not promo_groups:
        return 0

    strict_stations = {'dessert', 'soup', 'breakfast', 'salad'}

    if menu_group in strict_stations:
        return 25 if menu_group in promo_groups else 0

    if menu_group in promo_groups:
        return 25

    compatible_pairs = [
        ('grill', 'entree'),
        ('entree', 'grill'),
        ('deli', 'grill'),
        ('grill', 'deli'),
    ]

    for promo_group in promo_groups:
        if (menu_group, promo_group) in compatible_pairs:
            return 15

    return 0


def _score_keyword_fit(menu_item: dict, promo_recipe: dict) -> int:
    """Score based on keyword overlap."""
    menu_keywords = set(menu_item.get('keywords', []))
    promo_keywords = set(promo_recipe.get('keywords', []))

    if not menu_keywords or not promo_keywords:
        return 0

    overlap = len(menu_keywords & promo_keywords)

    if overlap >= 3:
        return 20
    elif overlap == 2:
        return 15
    elif overlap == 1:
        return 8
    return 0


def _score_cost_delta(promo_recipe: dict) -> int:
    """Score based on cost."""
    cost = promo_recipe.get('cost')

    if cost is None:
        return 7

    if cost <= 1.50:
        return 15
    elif cost <= 2.00:
        return 12
    elif cost <= 2.50:
        return 10
    elif cost <= 3.00:
        return 5
    return 0


def _score_dietary_value(promo_recipe: dict, context: dict) -> int:
    """Score based on dietary contribution."""
    dietary = promo_recipe.get('dietary', [])
    day_dietary = context.get('day_dietary', set())

    if not dietary:
        return 3

    for tag in dietary:
        if tag not in day_dietary:
            return 10

    return 3


def _score_variety_bonus(promo_recipe: dict, context: dict) -> int:
    """Score based on usage frequency."""
    used_promos = context.get('used_promos', {})
    master_ref = promo_recipe.get('master_ref')

    usage_count = used_promos.get(master_ref, 0)

    if usage_count == 0:
        return 5
    elif usage_count == 1:
        return 2
    return 0


def generate_recommendations(
    cycle_menu: list[dict],
    promo_recipes: list[dict],
    unit_config: dict,
    month: str
) -> list[dict]:
    """Generate all recommendations for a month."""
    recommendations = []

    menu_by_date = defaultdict(list)
    for item in cycle_menu:
        menu_by_date[item['date']].append(item)

    used_promos = Counter()
    day_dietary = defaultdict(set)

    for date in sorted(menu_by_date.keys()):
        items = menu_by_date[date]
        day_recs = []

        for menu_item in items:
            for promo in promo_recipes:
                context = {
                    'used_promos': used_promos,
                    'day_dietary': day_dietary[date],
                }

                scores = score_replacement(menu_item, promo, date, unit_config, context)

                if scores['passes_threshold']:
                    day_recs.append({
                        'date': date,
                        'day_of_week': menu_item.get('day_of_week'),
                        'week_number': menu_item.get('week_number'),
                        'current_item': menu_item,
                        'promo_recipe': promo,
                        'scores': scores,
                        'total_score': scores['total'],
                    })

        day_recs.sort(key=lambda x: -x['total_score'])

        seen_stations = set()
        for rec in day_recs:
            station = rec['current_item'].get('station_group')
            if station not in seen_stations or rec['total_score'] >= 70:
                recommendations.append(rec)
                seen_stations.add(station)
                used_promos[rec['promo_recipe']['master_ref']] += 1
                for tag in rec['promo_recipe'].get('dietary', []):
                    day_dietary[date].add(tag)

    return recommendations
