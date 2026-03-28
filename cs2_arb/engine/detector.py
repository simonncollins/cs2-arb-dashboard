"""Arbitrage opportunity detector.

Compares Polymarket implied probabilities against bookmaker implied
probabilities to identify arbitrage opportunities.

TODO: Implement detect_arbitrage(matched_events, min_edge) returning
      a list of ArbitrageOpportunity dataclasses. An opportunity exists
      when sum of best implied probs across platforms < 1.0 - min_edge.
"""
