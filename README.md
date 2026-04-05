# ORB Autoresearch
**Autonomous Overnight ORB Strategy Optimization**

Powered by backtesting.py · Yahoo Finance · Claude (AI Agent)

# Overview

ORB Autoresearch is an autonomous overnight research loop for optimizing Opening Range Breakout (ORB) trading strategies. It is directly inspired by Andrej Karpathy's autoresearch project: you configure the research loop, start it before bed, and wake up to a log of completed experiments and (hopefully) a better strategy.

The agent modifies `strategy.py`, runs the backtest across 15 instruments, checks if performance improved, keeps or discards the change, and repeats — indefinitely, without human supervision.

# How It Works

The design follows Karpathy's autoresearch architecture exactly, adapted for trading strategy research instead of LLM training:

## The Three Key Files

### `prepare.py` — Fixed Infrastructure (Do Not Modify)

Contains all fixed constants, data download logic, train/test split, and the canonical metric computation function. The agent never touches this file. This ensures that all experiments use identical data and identical evaluation logic — apples-to-apples comparisons.

### `strategy.py` — The File the Agent Modifies

Contains the `ORBStrategy` class (a `backtesting.py` Strategy subclass), the `PARAMS` dict, and the `run_experiment()` function. Everything is fair game: the agent can change parameters, rewrite entry/exit logic, add indicators, add session filters, change position sizing, etc.

### `program.md` — Agent Instructions

A Markdown file that the agent reads at the start of each session. It defines the setup procedure, the experiment loop, what is and is not allowed, the logging format, and a menu of ideas to explore. This is the file the human iterates on over time to improve the research process itself.

# Instrument Universe

## Forex Pairs

## CFDs & ETFs

# Quick Start

## 1. Install Dependencies

Requires Python 3.10+ and [`uv`](https://docs.astral.sh/uv/). Install `uv` if you don't have it:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then sync the project environment (creates `.venv` and installs all dependencies from `uv.lock`):

```bash
uv sync
```

To include dev dependencies (Jupyter, notebook):

```bash
uv sync --dev
```

## 2. Download Data (one-time, ~2–5 min)

```bash
uv run python prepare.py
```

## 3. Run Baseline Experiment

```bash
uv run python strategy.py
```

## 4. Start the Agent

Open Claude Code (or your preferred AI coding agent) in this directory. Point it to `program.md` and kick off the loop:

```
Read program.md and start the experiment loop.
```

Then go to sleep. The agent will run experiments autonomously until you interrupt it. The agent should use `uv run python` for all script invocations.

## 5. Review Results in the Morning

```bash
uv run python analysis.py
```

# The Experiment Loop

The agent follows this loop indefinitely until manually stopped. Each iteration takes roughly 5–10 minutes.

## Results TSV Format

The agent logs every experiment to `results.tsv` (tab-separated, never committed to git):

# Strategy Parameters

These are the default `PARAMS` values in `strategy.py`. The agent may change any of them freely:

# Research Ideas for the Agent

These are catalogued in `program.md` for the agent to consult when it runs out of ideas:

## Parameter Tuning

- Opening range window: 1h, 2h, 3h, 4h — which is most consistent across instruments?
- Breakout threshold: 0 (any breakout), 0.1%, 0.2%, 0.5%
- Asymmetric SL/TP: different ratios for long vs short side
- Per-instrument-class params: separate settings for forex vs commodity futures vs equity ETFs

## Entry Filters

- Volume confirmation: only enter if breakout bar volume > N-period average
- Momentum filter: only go long if Close > 20-bar SMA, only go short if Close < SMA
- Volatility filter: skip entries if ATR is below or above historical percentile
- Time filter: only enter during specific hours (e.g., London session open for forex)

## Exit Enhancements

- Trailing stop: activate after price moves 50% toward TP
- Time-based exit: close if trade has been open for >N bars without hitting TP
- Partial exit: take 50% profit at 1x range, let rest run to 2x

## Structural Changes

- Per-symbol optimization using `backtesting.py`'s built-in optimizer (`--optimize` flag)
- Regime filter: only trade ORB in trending regimes (ATR expanding, ADX > 25)
- Two-legged breakout: require a retest of range before entering

# Evaluation Metrics

All metrics are computed by `prepare.py`'s `compute_metrics()` function and cannot be changed by the agent. This ensures fair comparison across all experiments.

The optimization target is `mean_sharpe` — we prioritize consistency across the full portfolio, not peak performance on a single instrument. A strategy that achieves Sharpe 0.9 on 13 symbols is preferred over one that achieves 2.0 on 3 symbols and -0.5 on the rest.

# Project Structure

# Important Constraints

## What the Agent Can Change

- Any value in the `PARAMS` dict in `strategy.py`
- The `ORBStrategy` class: `init()`, `next()`, any indicator via `self.I()`
- The `run_experiment()` function
- Import and use any package already listed in `pyproject.toml`

## What the Agent Cannot Change

- `prepare.py` — it is read-only infrastructure
- `ALL_SYMBOLS`, `BACKTEST_START`, `BACKTEST_END`, `INTRADAY_INTERVAL` (defined in `prepare.py`)
- The `compute_metrics()` function — this is the ground-truth evaluator
- Install new packages not in `pyproject.toml`
- Use external data sources other than Yahoo Finance via `yfinance`

# Tips for Best Results

- Run `uv sync` once to install dependencies, then `uv run python prepare.py` to download data. Both only need to happen once.
- Use `--dangerously-skip-permissions` in Claude Code so the agent doesn't pause to ask for confirmation on file edits or terminal commands.
- The more specific `program.md` is about what to explore, the better the overnight results. After your first run, read `results.tsv`, identify which ideas showed promise but didn't quite beat baseline, and annotate them in `program.md`'s Ideas section.
- A crash is not a failure — it gives the agent information. Let it log crashes and move on rather than getting stuck.
- The simplicity criterion matters: a +0.001 Sharpe gain from 30 lines of complex code is not worth it. The agent is instructed to weight complexity against improvement magnitude.
- For OOS validation after finding good IS params, run: `uv run python analysis.py --best` then manually run the best strategy on the test split to check for overfitting.

---

*ORB Autoresearch · Inspired by [karpathy/autoresearch](https://github.com/karpathy/autoresearch) · April 2026*
