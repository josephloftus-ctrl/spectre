"""Menu planning services."""

from .parsing import (
    parse_cycle_menu,
    parse_promo_pdf,
    extract_keywords,
    extract_theme_from_filename,
)
from .scoring import (
    score_replacement,
    generate_recommendations,
)
from .guardrails import (
    apply_guardrail_penalties,
    filter_recommendations,
    generate_flags_report,
)
from .output import (
    generate_why,
    generate_calendar_markdown,
    generate_flags_markdown,
)

__all__ = [
    'parse_cycle_menu',
    'parse_promo_pdf',
    'extract_keywords',
    'extract_theme_from_filename',
    'score_replacement',
    'generate_recommendations',
    'apply_guardrail_penalties',
    'filter_recommendations',
    'generate_flags_report',
    'generate_why',
    'generate_calendar_markdown',
    'generate_flags_markdown',
]
