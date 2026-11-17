"""Dip-bounce BTC bot for make.fun btc-race-24h-20261117-0603.

Strategy (long only, one asset CBBTC, full-size positions, few trades):
  * Entry: RSI(60) of 1-minute closes drops below 35 while the close is
    below EMA(240) -- an oversold dip in a ranging market -- AND the
    close has fallen at least 0.8% over the last 60 minutes (a real dip,
    not a shallow RSI wiggle). Buy all cash.
  * Exit: RSI(60) rises above 65 (strength recovered), or the close falls
    1% below the entry close (stop-loss). Sell the whole position.
    After a stop-loss, dip re-entries are paused for 120 bars: a dip that
    just stopped out is usually a falling knife, and re-buying the next
    bar bled repeatedly on the -5%/day drift twin (-$25.84 -> -$12.66
    with the pause, dev and mirror unchanged at +$29.52 / +$20.66).
  * Fallback: if no trade has happened by bar 1200 and the close is above
    EMA(240) with RSI(60) above 50 (a smooth grind-up day with no dip),
    buy once so the entry always clears the race's minimum-1-trade bar.

Why this shape: on the 24h dev window (BTC +0.49%, choppy, hourly swings
+-0.5-1.3%) every fast trend system bled on the ~35 bps round-trip cost
(EMA 8/21: -$107; Donchian: -$118). Dip-buying with RSI(60) made
+$33.87 net after all fees on dev (6 trades, max drawdown -0.96%) and
+$22.09 on the mirrored falling twin of the window, and stayed positive
at 2x fees (+$30.16). The parameters sit mid-plateau (RSI 30/35/40 x
exit 65/70 all positive on dev), not on a spike. The 60-minute dip
filter is what keeps the bot out of shallow wiggles: without it the same
bot scores +$29.52 dev / +$20.66 mirror / -$12.66 on the -5% drift twin,
and its 40-draw block-bootstrap median is -$7.55 (38% of draws positive);
with the filter the median is +$5.13 (62% positive).

Deterministic: pure function of the closes seen so far. No clock, no
network, no files, no randomness, no environment. Standard library only.
The vendor shim is a byte-for-byte copy of the kit's sdk/makefun_bars.py.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars

SYMBOL = "CBBTC"

# --- parameters (chosen on the dev window, mid-plateau, see docstring) ---
RSI_N = 60            # RSI lookback, in 1-minute bars
RSI_LO = 35.0         # enter below this RSI
RSI_HI = 65.0         # exit above this RSI
EMA_N = 240           # slow EMA, in 1-minute bars
STOP_PCT = 0.01       # exit if close falls 1% below the entry close
DIP_60M_PCT = -0.008  # entry only if the close fell >=0.8% over the last
                      # 60 minutes: a real dip, not a shallow RSI wiggle.
                      # Sprint 17 Nov 17:00-17:20 WIB (243-param grid +
                      # 20 structural variants + combos, exact-port sim):
                      # the filter beats the no-filter bot on dev
                      # (+$33.87 vs +$29.52), mirror (+$22.09 vs +$20.66)
                      # and the -5%/day drift twin (-$4.93 vs -$12.66),
                      # ties choppy-2x (+$12.66), improves max drawdown on
                      # every window, and flips the 40-draw block
                      # bootstrap median from -$7.55 to +$5.13 (frac>0
                      # 0.38 -> 0.62). -0.75% also passes; -0.85% loses a
                      # winning mirror trade, so -0.80% is the pick.
COOLDOWN_BARS = 120   # after a stop-loss exit, wait this many bars before
                      # re-entering on a dip (a dip that just stopped out
                      # is usually a falling knife, not a bounce)
FALLBACK_BAR = 1200   # buy once by here if nothing traded yet
FALLBACK_RSI = 50.0   # ... only in an uptrend (close above EMA, RSI above this)
MAX_SLIPPAGE_BPS = 200  # ~4x the largest 1-minute move in the dev window

# --- incremental indicator state (built bar by bar, in order) ---
_closes = []          # closes seen so far, ints (price_scale 5)
_ema = None           # EMA(240) as float, seeded on the first close
_entry_close = None   # close of the bar on which the current position opened
_last_stop_bar = -10 ** 9  # seq of the bar on which the last stop-loss exit fired
_traded = False       # True once any buy has been sent


def _rsi():
    """RSI over the last RSI_N one-minute changes, exactly as backtested:
    simple mean of gains / mean of losses over the window."""
    if len(_closes) <= RSI_N:
        return None
    gains = 0.0
    losses = 0.0
    for k in range(len(_closes) - RSI_N, len(_closes)):
        d = _closes[k] - _closes[k - 1]
        if d > 0:
            gains += d
        else:
            losses -= d
    if losses == 0.0:
        return 100.0
    rs = gains / losses
    return 100.0 - 100.0 / (1.0 + rs)


def on_batch(state, batch):
    global _ema, _entry_close, _last_stop_bar, _traded
    if state.warming_up:
        return []
    # Only CBBTC bars advance the indicators; a gap minute has none.
    bar = None
    for b in batch["bars"]:
        if b["symbol"] == SYMBOL:
            bar = b
            break
    if bar is None:
        return []
    close = int(bar["c"])
    _closes.append(close)
    if _ema is None:
        _ema = float(close)
    else:
        k = 2.0 / (EMA_N + 1)
        _ema = close * k + _ema * (1.0 - k)
    i = state.seq
    if i < EMA_N + 1:
        return []
    rsi = _rsi()
    if rsi is None:
        return []
    holding = state.positions.get(SYMBOL)
    if holding is None:
        dip_60m = close / _closes[-61] - 1.0 if len(_closes) > 60 else 0.0
        if (rsi < RSI_LO and close < _ema and dip_60m < DIP_60M_PCT
                and i - _last_stop_bar >= COOLDOWN_BARS):
            _entry_close = close
            _traded = True
            return [{"side": "buy", "symbol": SYMBOL,
                     "notional_quote_units": state.cash,
                     "max_slippage_bps": MAX_SLIPPAGE_BPS}]
        if (not _traded) and i >= FALLBACK_BAR and close > _ema and rsi > FALLBACK_RSI:
            _entry_close = close
            _traded = True
            return [{"side": "buy", "symbol": SYMBOL,
                     "notional_quote_units": state.cash,
                     "max_slippage_bps": MAX_SLIPPAGE_BPS}]
        return []
    if rsi > RSI_HI:
        return [{"side": "sell", "symbol": SYMBOL, "qty": holding.qty,
                 "max_slippage_bps": MAX_SLIPPAGE_BPS}]
    if _entry_close is not None and close < _entry_close * (1.0 - STOP_PCT):
        _last_stop_bar = i
        return [{"side": "sell", "symbol": SYMBOL, "qty": holding.qty,
                 "max_slippage_bps": MAX_SLIPPAGE_BPS}]
    return []


makefun_bars.run(on_batch)
