"""Tests for cs2_arb/ui/tournament_view.py."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from cs2_arb.ui.tournament_view import _badge, _is_blast, _opps_to_df


@dataclass
class _StubOpp:
    event_name: str = "IEM Cologne 2026"
    team_name: str = "NaVi"
    poly_prob: float = 0.30
    book_prob: float = 0.25
    edge_pct: float = 4.0
    is_blast_event: bool = True
    is_significant: bool = True


class TestIsBlast:
    def test_iem_detected(self) -> None:
        assert _is_blast("IEM Cologne 2026") is True

    def test_blast_detected(self) -> None:
        assert _is_blast("BLAST Premier Spring Finals 2026") is True

    def test_pgl_detected(self) -> None:
        assert _is_blast("PGL Major Copenhagen 2026") is True

    def test_esl_detected(self) -> None:
        assert _is_blast("ESL Pro League Season 21") is True

    def test_ordinary_event_not_blast(self) -> None:
        assert _is_blast("Random Online Qualifier") is False

    def test_case_insensitive(self) -> None:
        assert _is_blast("iem katowice") is True


class TestBadge:
    def test_blast_premier_badge(self) -> None:
        assert _badge("BLAST Premier Spring 2026") == "⚡ BLAST"

    def test_iem_badge(self) -> None:
        badge = _badge("IEM Cologne 2026")
        assert "⚡" in badge

    def test_major_badge(self) -> None:
        badge = _badge("CS2 Major Copenhagen")
        assert "🏆" in badge or "⚡" in badge  # 'major' keyword

    def test_no_badge_for_ordinary(self) -> None:
        assert _badge("Random Online League") == ""


class TestOppsToDf:
    def test_empty_input(self) -> None:
        df = _opps_to_df([])
        assert len(df) == 0
        assert "Edge %" in df.columns

    def test_single_opportunity(self) -> None:
        opp = _StubOpp()
        df = _opps_to_df([opp])
        assert len(df) == 1
        assert df.iloc[0]["Team"] == "NaVi"

    def test_blast_flag_set_correctly(self) -> None:
        opp = _StubOpp(event_name="IEM Cologne 2026")
        df = _opps_to_df([opp])
        assert bool(df.iloc[0]["BLAST"]) is True

    def test_non_blast_flag_false(self) -> None:
        opp = _StubOpp(event_name="Random Online League")
        df = _opps_to_df([opp])
        assert bool(df.iloc[0]["BLAST"]) is False

    def test_significant_preserved(self) -> None:
        opp = _StubOpp(is_significant=True)
        df = _opps_to_df([opp])
        assert bool(df.iloc[0]["Significant"]) is True

    def test_poly_prob_preserved(self) -> None:
        opp = _StubOpp(poly_prob=0.45)
        df = _opps_to_df([opp])
        assert df.iloc[0]["Poly Prob"] == pytest.approx(0.45)

    def test_multiple_events_grouped_by_event_name(self) -> None:
        opps = [
            _StubOpp(event_name="IEM Cologne 2026", team_name="NaVi"),
            _StubOpp(event_name="IEM Cologne 2026", team_name="Astralis"),
            _StubOpp(event_name="PGL Major Copenhagen 2026", team_name="Vitality"),
        ]
        df = _opps_to_df(opps)
        assert len(df) == 3
        assert len(df["Event"].unique()) == 2
