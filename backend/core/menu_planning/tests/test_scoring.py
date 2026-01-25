"""Tests for scoring service."""

import pytest
from ..services.scoring import (
    score_replacement,
    _score_keyword_fit,
    _score_station_fit,
    _score_date_relevance,
)


def test_keyword_fit_strong_match():
    """3+ shared keywords = 20 points."""
    menu = {'keywords': ['buffalo', 'chicken', 'sandwich', 'spicy']}
    promo = {'keywords': ['buffalo', 'chicken', 'wings', 'spicy']}
    assert _score_keyword_fit(menu, promo) == 20


def test_keyword_fit_good_match():
    """2 shared keywords = 15 points."""
    menu = {'keywords': ['buffalo', 'chicken']}
    promo = {'keywords': ['buffalo', 'wings', 'chicken']}
    assert _score_keyword_fit(menu, promo) == 15


def test_keyword_fit_weak_match():
    """1 shared keyword = 8 points."""
    menu = {'keywords': ['chicken']}
    promo = {'keywords': ['chicken', 'teriyaki']}
    assert _score_keyword_fit(menu, promo) == 8


def test_keyword_fit_no_match():
    """0 shared keywords = 0 points."""
    menu = {'keywords': ['beef']}
    promo = {'keywords': ['chicken']}
    assert _score_keyword_fit(menu, promo) == 0


def test_station_fit_exact_match():
    """Same station group = 25 points."""
    menu = {'station_group': 'grill'}
    promo = {'station_groups': ['grill', 'entree']}
    assert _score_station_fit(menu, promo) == 25


def test_station_fit_compatible():
    """Compatible groups = 15 points."""
    menu = {'station_group': 'grill'}
    promo = {'station_groups': ['entree']}
    assert _score_station_fit(menu, promo) == 15


def test_station_fit_strict_mismatch():
    """Strict stations don't cross-match."""
    menu = {'station_group': 'soup'}
    promo = {'station_groups': ['grill']}
    assert _score_station_fit(menu, promo) == 0


def test_date_relevance_direct_hit():
    """Within theme window = 25 points."""
    promo = {'theme_dates': ['2026-02-08'], 'theme_window': 1}
    assert _score_date_relevance(promo, '2026-02-08') == 25
    assert _score_date_relevance(promo, '2026-02-07') == 25  # Within window


def test_date_relevance_near():
    """±1 day from window = 18 points."""
    promo = {'theme_dates': ['2026-02-08'], 'theme_window': 0}
    assert _score_date_relevance(promo, '2026-02-09') == 18


def test_date_relevance_far():
    """±3 days = 10 points."""
    promo = {'theme_dates': ['2026-02-08'], 'theme_window': 0}
    assert _score_date_relevance(promo, '2026-02-11') == 10


def test_date_relevance_outside():
    """Outside window = 0 points."""
    promo = {'theme_dates': ['2026-02-08'], 'theme_window': 0}
    assert _score_date_relevance(promo, '2026-02-20') == 0


def test_date_relevance_all_month():
    """All-month themes = 15 points."""
    promo = {'theme_all_month': True}
    assert _score_date_relevance(promo, '2026-02-15') == 15
