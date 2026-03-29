"""Tests for cs2_arb/ui/detail_view.py — match detail view helpers."""

from __future__ import annotations

from cs2_arb.ui.detail_view import _poly_url


class TestPolyUrl:
    def test_slug_generates_direct_url(self) -> None:
        url = _poly_url("NaVi vs Astralis", slug="navi-vs-astralis")
        assert "polymarket.com/event/navi-vs-astralis" in url

    def test_no_slug_generates_search_url(self) -> None:
        url = _poly_url("IEM Cologne 2026")
        assert "polymarket.com" in url
        assert "iem" in url.lower() or "cologne" in url.lower() or "q=" in url

    def test_search_url_is_lowercase(self) -> None:
        url = _poly_url("NaVi vs Astralis")
        # The query part should be lowercase
        query_part = url.split("q=")[-1]
        assert query_part == query_part.lower()

    def test_spaces_replaced_in_search(self) -> None:
        url = _poly_url("IEM Cologne 2026")
        # Spaces should be encoded
        query_part = url.split("q=")[-1]
        assert " " not in query_part

    def test_slug_none_falls_back_to_search(self) -> None:
        url = _poly_url("Test Event", slug=None)
        assert "markets?q=" in url
