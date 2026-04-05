# ORB Autoresearch

This is an autonomous experiment loop for optimizing Opening Range Breakout (ORB) trading strategies across multiple forex pairs and CFDs using backtesting.py and Yahoo Finance data.

It is modeled after karpathy/autoresearch: you modify `strategy.py`, run the backtest, keep improvements, discard regressions, and loop indefinitely while the human sleeps.

**Data interval:** 5-minute bars. yfinance free tier caps 5m data at ~60 days rolling, so the usable backtest window is approximately the last 60 days.

**Backtest period:** Use the **full available 60-day window** ending at the current date. This means `BACKTEST_END` should be today (or the most recent trading day) and `BACKTEST_START` should be ~60 days before that. A 1–2 day backtest is useless for evaluating strategy robustness — we need weeks of data to see how the strategy performs across different market conditions. Before each experiment run, refresh the data by running `python prepare.py` with `force_refresh=True` so that the most recent data is fetched and cached.

**Session design (FIXED — do not deviate):**
- Trade ONLY during the opening ranges of **London** (08:00 UTC) and **New York** (13:30 UTC) sessions.
- For the first **15 minutes** of each session (3 bars at 5m), do **nothing** — let the opening range zone form. Do not enter any trade during this formation window.
- After the 15-minute range is established, trade breakouts above/below the range high/low.
- Close all open positions at session end (London closes ~12:30 UTC; NY closes ~20:00 UTC).

---

## Setup

To begin a new research run, work with the user to:

1. **Agree on a run tag**: propose a tag based on today's date (e.g. `apr5`). The branch `autoresearch/<tag>` must not already exist.
2. **Create the branch**: `git checkout -b autoresearch/<tag>` from current master.
3. **Read the in-scope files**: Read these files in full before experimenting:
   - `README.md` — project overview and quick-start
   - `prepare.py` — fixed constants, data download, evaluation metrics. **Do not modify** (except `BACKTEST_START`/`BACKTEST_END` should be dynamic — see below).
   - `strategy.py` — the ORB strategy file. **This is the only file you modify.**
4. **Ensure backtest window is full 60 days**: Before the first experiment run, update `BACKTEST_END` in `prepare.py` to today's date and `BACKTEST_START` to ~60 days prior. Then run `python prepare.py` with `force_refresh=True` to download fresh data covering the full window. This gives you ~60 trading days of 5-minute bars — enough to evaluate strategy performance across multiple weeks and market conditions.
5. **Verify data exists**: Check that the `data/` directory contains `.parquet` files with data spanning the full 60-day window. If data is stale or missing, re-run `python prepare.py`.
6. **Initialize results.tsv**: Create `results.tsv` with just the header row (see format below).
7. **Confirm and go**.

---

## Experimentation

Each experiment runs the backtest across **all symbols** (`ALL_SYMBOLS` in `prepare.py`).

**Before starting the experiment loop**, refresh data to ensure you have the full 60-day window:
```bash
python -c "from prepare import download_data; download_data(force_refresh=True)"
```

**What you CAN do (all fair game in `strategy.py`):**
- Change any value in the `PARAMS` dict
- Rewrite the `ORBStrategy.next()` logic entirely
- Add new indicators using `self.I()` (backtesting.py's indicator helper)
- Add time-of-day filters, session filters, day-of-week filters
- Change position sizing logic
- Change stop loss and take profit calculation methods
- Add trailing stops
- Try alternative entry triggers (e.g. volume confirmation, momentum filters)
- Change the `run_experiment()` function (e.g. to add per-symbol optimization)

**What you CANNOT do:**
- Modify `prepare.py` — it is read-only infrastructure
- Change `ALL_SYMBOLS`, `BACKTEST_START`, `BACKTEST_END`, `INTRADAY_INTERVAL` (defined in prepare.py)
- Use data sources other than what `prepare.py` loads
- Install new packages

**Data note:** With 5m bars, `opening_range_bars = 3` = 15 minutes. Sessions at 5m:
- London: starts 08:00 UTC, range forms 08:00–08:15, trade 08:15–12:30
- New York: starts 13:30 UTC, range forms 13:30–13:45, trade 13:45–20:00
- Each session is independent — reset range state at each session open.

**The goal: MAXIMIZE `mean_sharpe` across all symbols on in-sample training data.**

We optimize for robustness across the whole portfolio, not for a single pair. A strategy that scores 1.2 on 13 symbols beats one that scores 2.5 on 3 symbols and -0.3 on the rest.

**Secondary objectives** (tiebreakers):
1. Lower `mean_max_drawdown` (less negative is better)
2. Higher `mean_total_return`
3. Reasonable `num_trades` (strategies with <5 trades per symbol are suspect — may be overfitting)

---

## Running an Experiment

```bash
python strategy.py --tag <tag> > logs/<tag>.log 2>&1
```

Extract the key metrics:
```bash
grep "mean_sharpe\|median_sharpe\|mean_max_drawdown\|mean_total_return" logs/<tag>.log
```

Or read the full summary:
```bash
tail -n 40 logs/<tag>.log
```

If the script crashes, check:
```bash
tail -n 60 logs/<tag>.log
```

---

## Reading Results

Results are saved as JSON to `results/<tag>.json`. The "aggregate" section has the headline numbers:
```json
{
  "aggregate": {
    "mean_sharpe": 0.82,
    "median_sharpe": 0.74,
    "mean_max_drawdown": -18.4,
    "mean_total_return": 34.2,
    "num_symbols": 15
  }
}
```

---

## Logging Results

Log all runs to `results.tsv` (tab-separated, NOT comma-separated — commas break in descriptions).

**Format:**
```
commit\tmean_sharpe\tmean_max_dd\tstatus\tdescription
```

Columns:
1. git commit hash (short, 7 chars)
2. mean_sharpe across all symbols (e.g. `0.8234`)
3. mean_max_drawdown (e.g. `-18.4`)
4. status: `keep`, `discard`, or `crash`
5. short description of what this experiment tried

**Example:**
```
commit	mean_sharpe	mean_max_dd	status	description
a1b2c3d	0.4521	-22.3	keep	baseline ORB 2-bar range
b2c3d4e	0.5103	-19.8	keep	reduce SL to 0.3x range
c3d4e5f	0.3812	-28.1	discard	increase breakout threshold to 0.003
d4e5f6g	0.0000	0.0	crash	vectorized ORB (bug in indicator)
e5f6g7h	0.6441	-17.2	keep	add Mon-Thu filter only
```

Do NOT commit `results.tsv` — leave it untracked by git.

---

## The Experiment Loop

**LOOP FOREVER:**

1. Look at git state: current branch and HEAD commit
2. Think about what to change in `strategy.py` (see Ideas section below)
3. Edit `strategy.py` directly
4. `git add strategy.py && git commit -m "experiment: <short description>"`
5. Run experiment: `python strategy.py --tag <tagNNN> > logs/<tagNNN>.log 2>&1`
6. Extract metrics: `grep "mean_sharpe\|mean_max_drawdown\|mean_total_return" logs/<tagNNN>.log`
7. If empty output → crash. Run `tail -n 60 logs/<tagNNN>.log` to debug. Fix if trivial, skip if not.
8. Log result to `results.tsv`
9. If `mean_sharpe` improved → **advance** (keep commit, this is the new baseline)
10. If `mean_sharpe` is equal or worse → `git reset HEAD~1` to discard, revert changes

Commit only the working experiments. The TSV captures the full history including discards.

**Timeouts:** A full run across all 15 symbols should complete in under 10 minutes. If a run exceeds 15 minutes, kill it and treat as a crash.

**Crashes:** If trivially fixable (typo, wrong column name), fix and rerun. If the idea is broken, log "crash" and move on.

**NEVER STOP:** Once the loop begins, do NOT pause to ask the human if you should continue. The human is sleeping. You are autonomous. If you run out of ideas, read the Ideas section below, try combinations of past near-misses, or try more radical changes. Loop until manually interrupted.

---

## Ideas to Explore

When you feel stuck, consult this list. You are also encouraged to generate your own hypotheses.

**Parameter tuning:**
- Range window: 3 bars (15m), 6 bars (30m), 12 bars (1h) — which is most robust at 5m?
- Breakout threshold: 0 (any breakout), 0.1%, 0.2%, 0.5%
- SL/TP ratios: asymmetric? (different multipliers per instrument class?)
- Multiple TP/SL ratio combos: e.g. 1.0x, 1.5x, 2.0x, 3.0x TP vs 0.5x, 1.0x SL — grid search which ratio maximizes Sharpe
- Max trades per session: 1 vs 2 vs unlimited (note: two sessions per day now)

**Entry filters:**
- Volume confirmation: only trade if volume on breakout bar > N-period average
- Momentum filter: only go long if price > 20-bar SMA
- Volatility filter: skip if ATR is too low (dead market) or too high (chaotic)
- Time filter: only enter in first 4 hours of session, not in last 2

**Exit rules / stop loss placement:**
- SL at range midpoint: set stop at the 50% level of the opening range (tighter SL, smaller loss if wrong)
- SL at range high/low: for a long breakout, SL at range low; for a short breakout, SL at range high (full-range SL, wider but cleaner invalidation)
- Trailing stop: activate after price moves X% in our favor
- Time-based exit: close trade if still open after N hours
- Re-entry: allow re-entry after stopped out if breakout continues

**Session logic:**
- Only trade certain days of the week (e.g., Tue–Thu tend to trend better)
- Different parameters per instrument class (forex vs equity ETFs vs commodities)

**Structure changes:**
- Per-symbol parameter optimization using backtesting.py's built-in optimizer
- Separate parameter sets for "trending" vs "ranging" market regimes (use ATR ratio as proxy)

---

## Simplicity Criterion

All else being equal, simpler is better. A strategy with 2 parameters that achieves 0.72 mean Sharpe beats one with 8 parameters that achieves 0.74. Prefer clean, legible code. Removing complexity and getting the same result is a win.

---

## Footer

*Modeled after karpathy/autoresearch. The agent runs overnight. The human wakes to results.*
