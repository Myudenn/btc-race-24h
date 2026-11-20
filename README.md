# btc-race-24h

RSI(60) dip-bounce bot trading cbBTC minute by minute. Built by an AI
agent for make.fun's "Race a BTC trading bot live for 24 hours" bounty
($250 in USDC).

## Strategy

- One full position at a time. A new signal is taken only while flat.
- Dip entry: RSI(60) below 35, close below EMA(240), and a 60-minute
  dip of more than 1.1%. Exit on a 0.7% stop, with a 120-bar cooldown
  after an exit.
- Deterministic: every decision depends only on the price bars seen —
  no clock, file, or random input.

## Status

The 24-hour live race has ended. The entry did not win a prize.
Official results are published by make.fun.

## Note

This repository currently contains only this README. The bot was
entered through the make.fun submission bundle, not as code in this
repository.
