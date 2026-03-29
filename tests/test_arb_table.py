"""Tests for cs2_arb/ui/arb_table.py — the arbitrage table widget helpers.

We test the non-Streamlit helper functions (_is_blast, _opps_to_df) directly.
The render_arb_table function requires a live Streamlit context, so it is
integration-tested manually via `streamlit run app.py`.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from cs2_arb.ui.arb_table import _is_blast, _opps_to_df

# ---------------------------------------------------------------------------
# Minimal stub matching the _OppProto protocol
# ---------------------------------------------------------------------------


@dataclass
class _StubOpp:
    event_name: str = "Team A vs Team B"
    team_a: str = "Team A"
    team_b: str = "Team B"
    outcome: str = "team_a"
    poly_prob: float = 0.55
    book_prob: float = 0.48
    edge_pct: float = 7.0
    ev_adjusted: float = 0.05
    kelly_fraction: float = 0.1
    book_name: str = "bet365"
    volume_usd: float = 10_000.0


# ---------------------------------------------------------------------------
# _is_blast
# ---------------------------------------------------------------------------


class TestIsBlast:
    def test_iem_cologne_detected(self) -> None:
        assert _is_blast("IEM Cologne 2026") is True

    def test_blast_premier_detected(self) -> None:
        assert _is_blast("BLAST Premier Spring 2026") is True

    def test_esl_detected(self) -> None:
        assert _is_blast("ESL Pro League Season 20") is True

    def test_major_detected(self) -> None:
        assert _is_blast("CS2 Major Paris 2026") is True

    def test_ordinary_match_not_blast(self) -> None:
        assert _is_blast("Random Online League") is False

    def test_case_insensitive(self) -> None:
        assert _is_blast("blast premier") is True
        assert _is_blast("IEM") is True


# ---------------------------------------------------------------------------
# _opps_to_df
# ---------------------------------------------------------------------------


class TestOppsToDf:
    def test_empty_returns_empty_df_with_correct_columns(self) -> None:
        df = _opps_to_df([])
        assert len(df) == 0
        assert "Edge %" in df.columns
        assert "Volume ($)" in df.columns

    def test_single_row_columns_present(self) -> None:
        opp = _StubOpp()
        df = _opps_to_df([opp])
        assert len(df) == 1
        expected_cols = {
            "Event",
            "Outcome",
            "Poly Prob",
            "Book Prob",
            "Edge %",
            "EV (adj)",
            "Volume ($)",
            "Kelly %",
            "Book",
            "BLAST",
        }
        assert expected_cols.issubset(set(df.columns))

    def test_blast_event_gets_lightning_prefix(self) -> None:
        opp = _StubOpp(event_name="IEM Cologne 2026")
        df = _opps_to_df([opp])
        assert df.iloc[0]["Event"].startswith("⚡")
        assert bool(df.iloc[0]["BLAST"]) is True

    def test_non_blast_event_no_prefix(self) -> None:
        opp = _StubOpp(event_name="Online League Week 3")
        df = _opps_to_df([opp])
        assert not df.iloc[0]["Event"].startswith("⚡")
        assert bool(df.iloc[0]["BLAST"]) is False

    def test_outcome_team_a_maps_to_team_a_name(self) -> None:
        opp = _StubOpp(outcome="team_a", team_a="NaVi", team_b="Astralis")
        df = _opps_to_df([opp])
        assert df.iloc[0]["Outcome"] == "NaVi"

    def test_outcome_team_b_maps_to_team_b_name(self) -> None:
        opp = _StubOpp(outcome="team_b", team_a="NaVi", team_b="Astralis")
        df = _opps_to_df([opp])
        assert df.iloc[0]["Outcome"] == "Astralis"

    def test_kelly_fraction_converted_to_pct(self) -> None:
        opp = _StubOpp(kelly_fraction=0.25)
        df = _opps_to_df([opp])
        assert df.iloc[0]["Kelly %"] == pytest.approx(25.0)

    def test_multiple_rows(self) -> None:
        opps = [_StubOpp(edge_pct=5.0), _StubOpp(edge_pct=3.0), _StubOpp(edge_pct=8.0)]
        df = _opps_to_df(opps)
        assert len(df) == 3

    def test_poly_prob_preserved(self) -> None:
        opp = _StubOpp(poly_prob=0.72)
        df = _opps_to_df([opp])
        assert df.iloc[0]["Poly Prob"] == pytest.approx(0.72)
