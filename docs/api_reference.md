# API Reference

Internal module API documentation for the CS2 Esports Arbitrage Dashboard.

---

## `cs2_arb.api.polymarket`

### `PolymarketMarket`

```python
@dataclass
class PolymarketMarket:
    market_id: str      # Polymarket market identifier
    team_a: str         # Home/first team name
    team_b: str         # Away/second team name
    yes_price: float    # Implied probability for team_a winning (0–1)
    no_price: float     # Implied probability for team_b winning (0–1)
    closes_at: str      # ISO 8601 market close timestamp
```

### `PolymarketClient`

```python
class PolymarketClient:
    def get_cs2_markets(self) -> list[PolymarketMarket]: ...
    def get_market_prices(self, token_id: str) -> dict[str, float]: ...
```

- `get_cs2_markets()` — fetches all active CS2 prediction markets. Cached via `@st.cache_data(ttl=POLYMARKET_CACHE_TTL_SECS)`.
- `get_market_prices(token_id)` — fetches current best bid/ask for a specific CLOB token.

**No authentication required.**

---

## `cs2_arb.api.odds_api`

### `BookmakerOdds`

```python
@dataclass
class BookmakerOdds:
    event_id: str
    team_a: str
    team_b: str
    book_name: str
    team_a_price: float   # Implied probability for team_a (0–1, vig-removed)
    team_b_price: float   # Implied probability for team_b (0–1, vig-removed)
    commence_time: str    # ISO 8601
```

### `OddsApiClient`

```python
class OddsApiClient:
    def get_cs2_odds(self) -> list[BookmakerOdds]: ...
```

- Requires `ODDS_API_KEY` environment variable.
- Converts decimal/American odds to implied probability, removing vig via normalisation.

---

## `cs2_arb.engine.detector`

### `MatchArbitrageOpportunity`

```python
@dataclass
class MatchArbitrageOpportunity:
    event_name: str
    team_a: str
    team_b: str
    outcome: str           # "team_a" or "team_b"
    poly_prob: float       # Raw Polymarket probability (0–1)
    book_prob: float       # Bookmaker implied probability (0–1)
    edge_pct: float        # (poly_prob_adj - book_prob) * 100
    book_name: str
    volume_usd: float
    ev_adjusted: float     # Set by ev.py annotator
    kelly_fraction: float  # Set by ev.py annotator
```

### `detect_opportunities`

```python
def detect_opportunities(
    poly_markets: list[PolymarketMarket],
    bookmaker_odds: list[BookmakerOdds],
    min_edge_pct: float = 0.5,
    poly_fee: float = 0.02,
) -> list[MatchArbitrageOpportunity]:
```

Returns arbitrage opportunities where `edge_pct >= min_edge_pct`, sorted by edge descending.

---

## `cs2_arb.engine.ev`

### `compute_ev`

```python
def compute_ev(
    poly_prob: float,
    book_implied_prob: float,
    poly_fee: float = 0.02,
) -> float:
```

Returns adjusted expected value (can be negative).

### `compute_kelly`

```python
def compute_kelly(edge: float, odds: float) -> float:
```

Returns Kelly fraction (0–1). For display purposes only.

### `annotate_opportunities`

```python
def annotate_opportunities(
    opportunities: list[MatchArbitrageOpportunity],
    poly_fee: float = 0.02,
) -> list[MatchArbitrageOpportunity]:
```

Mutates each opportunity in-place, setting `ev_adjusted` and `kelly_fraction`. Returns the same list.

---

## `cs2_arb.engine.tournament_detector`

### `detect_tournament_opportunities`

```python
def detect_tournament_opportunities(
    poly_markets: list[PolymarketMarket],
    bookmaker_odds: list[BookmakerOdds],
    min_edge_pct: float = 0.5,
) -> list[MatchArbitrageOpportunity]:
```

Wraps `detect_opportunities`, filtering results to BLAST/major events via `is_blast_event()`.

---

## `cs2_arb.data.blast_events`

### `is_blast_event`

```python
def is_blast_event(event_name: str) -> bool:
```

Returns `True` if `event_name` contains a BLAST/IEM/ESL/major tournament keyword (case-insensitive). This is the **single source of truth** for tournament classification throughout the codebase.

**Matched keywords:** `blast`, `iem`, `esl`, `major`, `cologne`, `rio`, `paris`, `katowice`, `stockholm`, `copenhagen`, `lisboa`, `austin`

---

## `cs2_arb.alerts.alerter`

### `AlertManager`

```python
class AlertManager:
    def __init__(
        self,
        min_edge_pct: float = 2.0,
        cooldown_secs: int = 3600,
        log_path: str | Path = "alert_log.json",
    ) -> None: ...

    def check_and_alert(
        self,
        opportunities: list[MatchArbitrageOpportunity],
    ) -> list[dict]: ...

    def clear_log(self) -> None: ...
```

- `check_and_alert(opportunities)` — fires for opportunities above `min_edge_pct` that have not been alerted within `cooldown_secs`. Returns list of alert payload dicts.
- Dedup key: `{event_name}|{outcome}`

---

## `cs2_arb.alerts.new_market_detector`

### `NewMarketAlert`

```python
@dataclass
class NewMarketAlert:
    market_id: str
    question: str           # e.g. "Team A vs Team B"
    volume_usd: float
    polymarket_url: str     # https://polymarket.com/event/{market_id}
```

### `NewMarketDetector`

```python
class NewMarketDetector:
    def __init__(
        self,
        snapshot_path: str | Path = "new_market_snapshot.json",
    ) -> None: ...

    def check_new_markets(
        self,
        markets: list[PolymarketMarket],
    ) -> list[NewMarketAlert]: ...

    def clear_snapshot(self) -> None: ...
```

- `check_new_markets(markets)` — first call establishes baseline (returns `[]`). Subsequent calls return `NewMarketAlert` for any market not in the previous snapshot.

---

## `cs2_arb.alerts.notifier`

### `SlackNotifier`

```python
class SlackNotifier:
    def __init__(self, webhook_url: str) -> None: ...
    def send(self, message: str) -> bool: ...
    def send_alert(self, alert: dict) -> bool: ...
```

### `WebhookNotifier`

```python
class WebhookNotifier:
    def __init__(self, webhook_url: str) -> None: ...
    def send(self, payload: dict) -> bool: ...
```

Both notifiers are no-ops (return `False`) if `webhook_url` is empty or `None`.

---

## `cs2_arb.ui.arb_table`

### `render_arb_table`

```python
def render_arb_table(opportunities: list[MatchArbitrageOpportunity]) -> None:
```

Renders a sortable Streamlit dataframe with per-column formatting. Shows an empty-state message when `opportunities` is empty.

---

## `cs2_arb.ui.tournament_view`

### `render_tournament_view`

```python
def render_tournament_view(
    poly_markets: list[PolymarketMarket],
    bookmaker_odds: list[BookmakerOdds],
    min_edge_pct: float = 0.5,
) -> None:
```

Renders the BLAST/majors tab with a stats summary bar and filtered opportunities table.

---

## `cs2_arb.ui.detail_view`

### `render_detail_view`

```python
def render_detail_view(
    opportunity: MatchArbitrageOpportunity,
) -> None:
```

Renders side-by-side Polymarket vs bookmaker probability display for a single match.
