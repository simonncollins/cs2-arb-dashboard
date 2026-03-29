"""Tests for cs2_arb.data.blast_events — BLAST event detection."""

from __future__ import annotations

import pytest

from cs2_arb.data.blast_events import BLAST_KEYWORDS, is_blast_event


class TestIsBlastEvent:
    """Unit tests for is_blast_event()."""

    def test_blast_keyword_matches(self) -> None:
        assert is_blast_event("BLAST Premier Spring 2026") is True

    def test_iem_keyword_matches(self) -> None:
        assert is_blast_event("IEM Cologne 2026") is True

    def test_esl_keyword_matches(self) -> None:
        assert is_blast_event("ESL One Cologne 2026") is True

    def test_pgl_major_matches(self) -> None:
        assert is_blast_event("PGL Major Copenhagen 2026") is True

    def test_cologne_keyword_matches(self) -> None:
        assert is_blast_event("Cologne CS2 Championship") is True

    def test_case_insensitive(self) -> None:
        assert is_blast_event("BLAST PREMIER FALL FINALS") is True
        assert is_blast_event("blast premier fall finals") is True
        assert is_blast_event("Blast Premier Fall Finals") is True

    def test_non_blast_event_returns_false(self) -> None:
        assert is_blast_event("Random Online League") is False

    def test_empty_string_returns_false(self) -> None:
        assert is_blast_event("") is False

    def test_regular_match_returns_false(self) -> None:
        assert is_blast_event("Natus Vincere vs Team Vitality") is False

    def test_katowice_matches(self) -> None:
        assert is_blast_event("IEM Katowice 2026") is True

    def test_all_keywords_present(self) -> None:
        """Ensure BLAST_KEYWORDS is non-empty and contains expected entries."""
        assert len(BLAST_KEYWORDS) > 0
        assert "blast" in BLAST_KEYWORDS
        assert "iem" in BLAST_KEYWORDS
        assert "pgl" in BLAST_KEYWORDS

    @pytest.mark.parametrize("keyword", ["blast", "iem", "esl", "pgl", "cologne"])
    def test_parametrized_keywords(self, keyword: str) -> None:
        assert is_blast_event(f"Event with {keyword} in name") is True
