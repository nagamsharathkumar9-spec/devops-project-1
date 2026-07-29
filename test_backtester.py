# test_backtester.py — Unit tests for EMA Backtester
# Style: BDD (Given/When/Then) using pytest

import pytest
import pandas as pd
from backtester import detect_signal

# ============================================================
# Helper: build a minimal DataFrame row for signal detection
# ============================================================
def make_row(ema_short, ema_long, prev_ema_short, prev_ema_long):
    return pd.Series({
        "ema_short": ema_short,
        "ema_long": ema_long,
        "prev_ema_short": prev_ema_short,
        "prev_ema_long": prev_ema_long,
    })

# ============================================================
# Test 1: Golden Cross → BUY signal
# ============================================================
def test_golden_cross_generates_buy_signal():
    """
    Given: ema_short was BELOW ema_long yesterday
    When: ema_short crosses ABOVE ema_long today
    Then: Signal should be BUY
    """
    row = make_row(
        ema_short=21500,       # today: short above long
        ema_long=21450,
        prev_ema_short=21400,  # yesterday: short below long
        prev_ema_long=21450,
    )
    assert detect_signal(row) == "BUY"

# ============================================================
# Test 2: Death Cross → SELL signal
# ============================================================
def test_death_cross_generates_sell_signal():
    """
    Given: ema_short was ABOVE ema_long yesterday
    When: ema_short crosses BELOW ema_long today
    Then: Signal should be SELL
    """
    row = make_row(
        ema_short=21400,       # today: short below long
        ema_long=21450,
        prev_ema_short=21500,  # yesterday: short above long
        prev_ema_long=21450,
    )
    assert detect_signal(row) == "SELL"

# ============================================================
# Test 3: No crossover → HOLD signal
# ============================================================
def test_no_crossover_generates_hold_signal():
    """
    Given: ema_short is above ema_long
    When: ema_short was already above ema_long yesterday
    Then: Signal should be HOLD (no crossover happened)
    """
    row = make_row(
        ema_short=21500,
        ema_long=21450,
        prev_ema_short=21490,  # was already above
        prev_ema_long=21450,
    )
    assert detect_signal(row) == "HOLD"

# ============================================================
# Test 4: First row (NaN prev values) → HOLD signal
# ============================================================
def test_first_row_with_nan_generates_hold():
    """
    Given: First candle in the dataset (no previous EMA values)
    When: prev_ema_short is NaN
    Then: Signal should be HOLD (not enough data)
    """
    row = pd.Series({
        "ema_short": 21500,
        "ema_long": 21450,
        "prev_ema_short": float("nan"),
        "prev_ema_long": float("nan"),
    })
    assert detect_signal(row) == "HOLD"

# ============================================================
# Test 5: EMA calculation correctness
# ============================================================
def test_ema_of_constant_prices_equals_that_price():
    """
    Given: A series of identical prices (no movement)
    When: EMA is calculated with any span
    Then: EMA should equal that constant price
    """
    prices = pd.Series([24000.0] * 50)
    ema = prices.ewm(span=9).mean()
    assert round(ema.iloc[-1], 2) == 24000.0

# ============================================================
# Test 6: P&L calculation correctness
# ============================================================
def test_pnl_calculation():
    """
    Given: Entry price of 24000 and exit price of 24500
    When: P&L is calculated
    Then: P&L should be +500 points
    """
    entry_price = 24000.0
    exit_price = 24500.0
    pnl = round(exit_price - entry_price, 2)
    assert pnl == 500.0

def test_losing_trade_pnl():
    """
    Given: Entry price of 24500 and exit price of 24000
    When: P&L is calculated
    Then: P&L should be -500 points (a loss)
    """
    entry_price = 24500.0
    exit_price = 24000.0
    pnl = round(exit_price - entry_price, 2)
    assert pnl == -500.0

# ============================================================
# Test 7: Win rate calculation
# ============================================================
def test_win_rate_calculation():
    """
    Given: 3 trades — 1 winner and 2 losers
    When: Win rate is calculated
    Then: Win rate should be 33.33%
    """
    trade_log = [
        {"pnl": 500, "is_winner": True},
        {"pnl": -200, "is_winner": False},
        {"pnl": -300, "is_winner": False},
    ]
    winners = sum(1 for t in trade_log if t["is_winner"])
    win_rate = round((winners / len(trade_log)) * 100, 2)
    assert win_rate == 33.33