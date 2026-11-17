"""Dip-bounce + breakout-union BTC bot for make.fun btc-race-24h-20261117-0603.

Submitted entry, sprint-3 revision: dip-bounce + breakout union.
Single general strategy, same on every window (no dev/race detection, no
hardcoded schedule, no clock, no files, no randomness -- pure function of
the bars seen so far). Standard library only.

Two entry arms, ONE position at a time (first signal wins while flat):
  * DIP arm (the submitted live bot, unchanged): RSI(60) < 35 while the
    close is below EMA(240) AND the close fell >= 1.1% over the last
    60 minutes. Exit: RSI(60) > 65, or close 0.7% below entry. After a
    stop-loss, dip re-entries pause 120 bars.
  * BREAKOUT arm: close breaks above the highest high of the previous
    20 bars by >= 0.4%. Exit: +0.8% take-profit, or close 0.5% below
    entry. No cooldown (it only fires while flat).
  * Fallback (same as live): if no trade by bar 1200 and close > EMA(240)
    with RSI(60) > 50, buy once so the entry always clears the race's
    minimum-1-trade bar.

Why the union: on the 4-window race-expectation test the breakout arm
never fires an extra trade on dev / mirror / down-5% (identical trades
and PnL to the live bot there), but in the choppy-2x window it adds 6
trades netting +$12.32. Bootstrap (40 resampled real-data windows)
median +$11.44 vs live +$8.13, same worst case -$12.65, same frac>0 0.80.
Standalone the breakout arm LOSES (mean -$2.61) -- its value here is
only as a second chance while flat, never as a replacement for the dip.
Numbers (exact-port sim, verified identical on a second machine):
  dev +$40.01 (6t, dd -0.7%) | mirror +$14.13 (2t) | choppy2 +$30.29 (12t)
  down-5% +$0.71 (4t) | race mean +$21.29 vs live +$18.21, worst +$0.71
  (same as live). Dev score UNCHANGED (+$40.01): this candidate does not
  move the dev leaderboard, it only improves expected race robustness.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars

SYMBOL = "CBBTC"

# --- dip arm (live bot, unchanged) ---
RSI_N = 60
RSI_LO = 35.0
RSI_HI = 65.0
EMA_N = 240
STOP_PCT = 0.007
DIP_60M_PCT = -0.011
COOLDOWN_BARS = 120
FALLBACK_BAR = 1200
FALLBACK_RSI = 50.0
# --- breakout arm ---
BRK_N = 20            # highest high of previous N bars
BRK_THR = 0.004       # close must exceed that high by 0.4%
BRK_TP = 0.008        # take profit 0.8% above entry
BRK_STOP = 0.005      # stop 0.5% below entry
MAX_SLIPPAGE_BPS = 200

_closes = []
_highs = []
_ema = None
_entry_close = None
_last_stop_bar = -10 ** 9
_traded = False
_mode = None          # "dip" | "brk" | "fallback" for the open position


def _rsi():
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
    global _ema, _entry_close, _last_stop_bar, _traded, _mode
    if state.warming_up:
        return []
    bar = None
    for b in batch["bars"]:
        if b["symbol"] == SYMBOL:
            bar = b
            break
    if bar is None:
        return []
    close = int(bar["c"])
    _closes.append(close)
    _highs.append(int(bar["h"]))
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
        dip = (rsi < RSI_LO and close < _ema and dip_60m < DIP_60M_PCT
               and i - _last_stop_bar >= COOLDOWN_BARS)
        brk = False
        if len(_highs) > BRK_N:
            brk = close > max(_highs[-BRK_N - 1:-1]) * (1.0 + BRK_THR)
        if dip or brk:
            _entry_close = close
            _traded = True
            _mode = "dip" if dip else "brk"
            return [{"side": "buy", "symbol": SYMBOL,
                     "notional_quote_units": state.cash,
                     "max_slippage_bps": MAX_SLIPPAGE_BPS}]
        if (not _traded) and i >= FALLBACK_BAR and close > _ema and rsi > FALLBACK_RSI:
            _entry_close = close
            _traded = True
            _mode = "fallback"
            return [{"side": "buy", "symbol": SYMBOL,
                     "notional_quote_units": state.cash,
                     "max_slippage_bps": MAX_SLIPPAGE_BPS}]
        return []
    if _mode == "brk":
        if _entry_close is not None and close >= _entry_close * (1.0 + BRK_TP):
            return [{"side": "sell", "symbol": SYMBOL, "qty": holding.qty,
                     "max_slippage_bps": MAX_SLIPPAGE_BPS}]
        if _entry_close is not None and close < _entry_close * (1.0 - BRK_STOP):
            _last_stop_bar = i
            return [{"side": "sell", "symbol": SYMBOL, "qty": holding.qty,
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
