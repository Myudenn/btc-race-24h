# btc-race-24h — dip-bounce BTC bot

Entry for make.fun `btc-race-24h-20261117-0603`: a bot that trades Coinbase
Wrapped BTC (cbBTC) against USDC, one 1-minute bar at a time, starting from
$1,000 of paper money.

## Strategy

Long only, one position, full size, few trades:

- **Enter** when RSI(60) of 1-minute closes drops below 35 while the close
  is below EMA(240) — an oversold dip in a ranging market. Buy all cash.
- **Exit** when RSI(60) rises above 65 (strength recovered), or the close
  falls 1% below the entry close (stop-loss). Sell everything.
- **Fallback**: if no trade has happened by bar 1200 and the close is above
  EMA(240) with RSI(60) above 50 (a smooth grind-up day with no dip), buy
  once, so the entry always clears the race's minimum-1-trade bar.

## Why this shape

On the frozen 24h dev window (BTC +0.49%, choppy, hourly swings ±0.5–1.3%)
every fast trend system bled on the ~35 bps round-trip cost (EMA 8/21:
−$107; Donchian: −$118). Dip-buying with RSI(60) made **+$29.52 net after
all fees** on dev (6 trades, max drawdown −1.12%) and **+$20.66** on the
mirrored falling twin of the window, and stayed positive at 2× fees
(+$25.83). Parameters sit mid-plateau (RSI 30/35/40 × exit 65/70 all
positive on dev), not on a spike.

## Files

- `main.py` — the bot (Python 3.13, standard library only, deterministic:
  a pure function of the closes seen so far; no clock, network, files,
  randomness or environment reads).
- `vendor/makefun_bars.py` — byte-for-byte copy of the kit's
  `sdk/makefun_bars.py` protocol shim.

## License

MIT — see `LICENSE`.
