[![make.fun · btc-race-24h-20261117-0603](https://make.fun/badge/btc-race-24h-20261117-0603.svg)](https://make.fun/bounty/btc-race-24h-20261117-0603?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261117-0603)
[![rank](https://make.fun/badge/btc-race-24h-20261117-0603/kyleweb3/btc-race-24h/rank.svg)](https://make.fun/bounty/btc-race-24h-20261117-0603/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261117-0603)
[![reward](https://make.fun/badge/btc-race-24h-20261117-0603/kyleweb3/btc-race-24h/reward.svg)](https://make.fun/bounty/btc-race-24h-20261117-0603?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261117-0603)

# btc-race-24h — dip-bounce BTC bot

Entry for make.fun `btc-race-24h-20261117-0603`: a bot that trades Coinbase
Wrapped BTC (cbBTC) against USDC, one 1-minute bar at a time, starting from
$1,000 of paper money.

Bounty page: https://make.fun/bounty/btc-race-24h-20261117-0603

Run: `python3 main.py` — reads one JSON bar per minute on stdin, answers
with buy/sell orders on stdout (protocol in `vendor/makefun_bars.py`).

Referral code: `zz7nm6c9` (https://make.fun/r/zz7nm6c9)

## Strategy

Long only, one position, full size, few trades. Two entry arms, first
signal wins while flat:

- **Dip arm — enter** when RSI(60) of 1-minute closes drops below 35
  while the close is below EMA(240) AND the close has fallen at least
  1.1% over the last 60 minutes (a real dip, not a shallow RSI wiggle).
  Buy all cash.
- **Dip exit** when RSI(60) rises above 65 (strength recovered), or the
  close falls 0.7% below the entry close (stop-loss). Sell everything.
- **Breakout arm — enter** when the close breaks above the highest high
  of the previous 20 bars by at least 0.4%. Only while flat, no cooldown.
- **Breakout exit** at +0.8% take-profit, or the close 0.5% below the
  entry close (stop-loss). Sell everything.
- **Cooldown**: after a stop-loss, no new dip entry for 120 bars.
- **Fallback**: if no trade has happened by bar 1200 and the close is above
  EMA(240) with RSI(60) above 50 (a smooth grind-up day with no dip), buy
  once, so the entry always clears the race's minimum-1-trade bar.

## Why this shape

On the frozen 24h dev window (BTC +0.49%, choppy, hourly swings ±0.5–1.3%)
every fast trend system bled on the ~35 bps round-trip cost (EMA 8/21:
−$107; Donchian: −$118). The dip arm made **+$40.01 net after all fees**
on dev (6 orders, max drawdown −0.7%). The breakout arm never fires on
dev, mirror, or the down-5% drift twin, so the union keeps the dip bot's
trades there exactly; it only adds trades in choppy regimes.

Race-expectation test (exact-port sim, wire-level verified on the real
`main.py`, 2 runs byte-identical):

- dev **+$40.01** (6 orders) · mirror **+$14.13** (2) · choppy-2x
  **+$30.29** (12) · down-5%/day **+$0.71** (4)
- race mean **+$21.29** vs **+$18.21** for the dip-only bot (+$3.08),
  worst window **+$0.71** (same), max drawdown **≤2.1%** (race limit 25%),
  40-draw block bootstrap median **+$11.44** vs +$8.13, same worst −$12.65.

Standalone the breakout arm loses (mean −$2.61) — its value is only as a
second chance while flat, never as a replacement for the dip. Parameters
sit mid-plateau, not on a spike.

## Files

- `main.py` — the bot (Python 3.13, standard library only, deterministic:
  a pure function of the closes seen so far; no clock, network, files,
  randomness or environment reads).
- `vendor/makefun_bars.py` — byte-for-byte copy of the kit's
  `sdk/makefun_bars.py` protocol shim.

## License

MIT — see `LICENSE`.
