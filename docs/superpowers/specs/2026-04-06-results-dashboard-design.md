# Results Dashboard Design

**Date:** 2026-04-06  
**Status:** Approved

## Overview

A `dashboard.py` script that reads experiment results and generates a self-contained `dashboard.html` file, then opens it in the browser. No server, no new dependencies. Used to visualize strategy improvements across the autoresearch loop.

## Files Changed

| File | Change |
|------|--------|
| `dashboard.py` | New script — generates `dashboard.html` |
| `dashboard.html` | Generated artifact — gitignored |
| `results.tsv` | Add `tag` as first column |
| `program.md` | Update TSV format docs and loop instructions |
| `.gitignore` | Add `dashboard.html` |

## Data Model

### `results.tsv` (updated format)

Tab-separated, one row per run:

```
tag	commit	mean_sharpe	mean_max_dd	status	description
apr5_001	20a9ab6	1.8279	-0.45	keep	remove threshold, SL=1.0x, min_range=0: more trades, much better
apr5_002	bd1cb06	2.1835	-0.70	keep	max 2 trades/session: more samples, higher sharpe
apr5_003	786ab5c	0.9755	-0.84	discard	TP=3.0x: wider TP hurt, fewer fills
```

- `tag` — unique run identifier matching `results/<tag>.json` (e.g. `apr5_001`)
- `commit` — 7-char git hash
- `mean_sharpe` — aggregate sharpe across all symbols
- `mean_max_dd` — aggregate max drawdown (negative value)
- `status` — `keep`, `discard`, or `crash`
- `description` — short explanation of what the experiment tried

### `results/<tag>.json`

Existing format. Used for per-symbol breakdown. Dashboard loads it when the user clicks a run. Rows without a matching JSON show aggregate metrics only.

## Architecture

`dashboard.py`:

1. Reads `results.tsv` → list of run dicts
2. For each row, checks if `results/<tag>.json` exists; if so, loads per-symbol data
3. Embeds all data as a JSON blob into an HTML template string
4. Writes `dashboard.html`
5. Opens `dashboard.html` via `python -m webbrowser`

No Flask, no Jinja2, no external packages beyond stdlib. Chart.js loaded from CDN in the generated HTML.

## UI Layout

### Chart (full width)

- X-axis: iteration order (all runs in sequence)
- Y-axis: `mean_sharpe`
- **Blue bars** — `keep` runs, connected by a thin line showing the improvement frontier
- **Dark grey bars** — `discard` runs
- **Red bars** — `crash` runs
- **Zero line** — dashed horizontal at y=0
- Hover tooltip: tag + mean_sharpe + description (truncated)
- Click a bar → selects it, expands detail panel below
- Click same bar again → collapses detail panel

### Detail Panel (below chart, shown on click)

- **Header**: tag · status badge · commit hash
- **Description**: full description text from TSV
- **Metric boxes** (3): mean_sharpe · mean_max_dd · mean_total_return. The first two come from TSV; `mean_total_return` comes from `results/<tag>.json` aggregate. If no JSON exists, the third box shows `—`.
- **Per-symbol sharpe bars**: horizontal bars sorted descending, green (positive) / red (negative). Only rendered if matching JSON exists.

## Program Loop Changes

`program.md` loop step 8 (log to results.tsv) must now write:
```
<tag>\t<commit>\t<mean_sharpe>\t<mean_max_dd>\t<status>\t<description>
```

The tag is the same tag used for `--tag` in the run command (e.g. `apr5_001`).

## Gitignore

Add `dashboard.html` to `.gitignore`. The script is committed; the artifact is not.
