"""
prepare.py — Fixed constants, one-time data download, and runtime evaluation utilities.
DO NOT MODIFY. This file is read-only for the agent.

Analogous to prepare.py in karpathy/autoresearch — this is the "ground truth" infrastructure.
The agent only touches strategy.py.
"""

import os
import json
import datetime
import pandas as pd
import yfinance as yf

# ─── Fixed Constants ───────────────────────────────────────────────────────────

# All instruments to download and backtest across
FOREX_PAIRS = [
    "EURUSD=X", "USDJPY=X", "GBPUSD=X", "AUDUSD=X",
    "USDCAD=X", "USDCHF=X", "NZDUSD=X", "EURJPY=X",
]

CFDS = [
    "GC=F",    # Gold futures
    "SI=F",    # Silver futures
    "CL=F",    # Crude oil futures
    "SPY",     # S&P 500 ETF
    "QQQ",     # Nasdaq ETF
    "ES=F",    # S&P 500 futures
    "NQ=F",    # Nasdaq futures
]

ALL_SYMBOLS = FOREX_PAIRS + CFDS

# Data configuration
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
LOGS_DIR = os.path.join(os.path.dirname(__file__), "logs")

# Backtest period
BACKTEST_START = "2018-01-01"
BACKTEST_END   = "2024-12-31"

# Walk-forward out-of-sample window (last N months of data are OOS)
OOS_MONTHS = 12

# Fixed evaluation metric: Sharpe Ratio (annualized, higher is better)
# Secondary: Max Drawdown (lower magnitude is better), Win Rate
METRIC_PRIMARY = "sharpe_ratio"

# Opening range window (in minutes). This is the "opening range" duration.
# FIXED — do not change this constant. The agent parameterizes it in strategy.py.
DEFAULT_ORB_MINUTES = 30

# Intraday data interval for backtesting
INTRADAY_INTERVAL = "1h"  # 1-hour bars (yfinance free tier supports up to 2 years of 1h data)


def ensure_dirs():
    for d in [DATA_DIR, RESULTS_DIR, LOGS_DIR]:
        os.makedirs(d, exist_ok=True)


def download_data(symbols=None, force_refresh=False):
    """Download historical OHLCV data for all symbols. Cached to disk."""
    ensure_dirs()
    symbols = symbols or ALL_SYMBOLS
    downloaded = {}

    for sym in symbols:
        cache_path = os.path.join(DATA_DIR, f"{sym.replace('=', '_').replace('/', '_')}.parquet")
        if os.path.exists(cache_path) and not force_refresh:
            df = pd.read_parquet(cache_path)
            downloaded[sym] = df
            print(f"  [cache] {sym}: {len(df)} rows")
            continue

        try:
            df = yf.download(
                sym,
                start=BACKTEST_START,
                end=BACKTEST_END,
                interval=INTRADAY_INTERVAL,
                auto_adjust=True,
                progress=False,
            )
            if df.empty:
                print(f"  [WARN]  {sym}: no data returned")
                continue
            df.to_parquet(cache_path)
            downloaded[sym] = df
            print(f"  [dl]    {sym}: {len(df)} rows")
        except Exception as e:
            print(f"  [ERR]   {sym}: {e}")

    return downloaded


def load_data(symbols=None):
    """Load cached data for all symbols. Raises if data not found."""
    symbols = symbols or ALL_SYMBOLS
    data = {}
    for sym in symbols:
        cache_path = os.path.join(DATA_DIR, f"{sym.replace('=', '_').replace('/', '_')}.parquet")
        if not os.path.exists(cache_path):
            raise FileNotFoundError(
                f"Data for {sym} not found. Run: python prepare.py"
            )
        data[sym] = pd.read_parquet(cache_path)
    return data


def split_train_test(df):
    """
    Split data into training (in-sample) and test (out-of-sample) sets.
    OOS = last OOS_MONTHS months. IS = everything before.
    """
    cutoff = df.index[-1] - pd.DateOffset(months=OOS_MONTHS)
    train = df[df.index <= cutoff].copy()
    test  = df[df.index >  cutoff].copy()
    return train, test


def compute_metrics(equity_curve: pd.Series) -> dict:
    """
    Compute standardized performance metrics from an equity curve.
    equity_curve: pd.Series indexed by datetime, values are portfolio equity.
    Returns dict with standardized metric keys.
    """
    if equity_curve is None or len(equity_curve) < 2:
        return {
            "sharpe_ratio": -999.0,
            "max_drawdown_pct": -999.0,
            "total_return_pct": -999.0,
            "win_rate": 0.0,
            "num_trades": 0,
            "calmar_ratio": -999.0,
        }

    returns = equity_curve.pct_change().dropna()

    # Annualized Sharpe (assume ~252 trading days, ~6 hours/day for intraday)
    periods_per_year = 252 * 6  # hourly bars
    sharpe = (
        returns.mean() / returns.std() * (periods_per_year ** 0.5)
        if returns.std() > 0 else -999.0
    )

    # Max drawdown
    roll_max = equity_curve.cummax()
    drawdown = (equity_curve - roll_max) / roll_max
    max_dd = drawdown.min()  # negative number

    # Total return
    total_return = (equity_curve.iloc[-1] / equity_curve.iloc[0] - 1) * 100

    # Calmar
    calmar = (total_return / 100) / abs(max_dd) if max_dd != 0 else 0.0

    return {
        "sharpe_ratio": round(float(sharpe), 4),
        "max_drawdown_pct": round(float(max_dd * 100), 2),
        "total_return_pct": round(float(total_return), 2),
        "calmar_ratio": round(float(calmar), 4),
        "num_trades": 0,   # strategy.py should fill this in
        "win_rate": 0.0,   # strategy.py should fill this in
    }


def save_results(tag: str, metrics_by_symbol: dict, params: dict, notes: str = ""):
    """Save experiment results to results/{tag}.json"""
    ensure_dirs()
    output = {
        "tag": tag,
        "timestamp": datetime.datetime.now().isoformat(),
        "params": params,
        "notes": notes,
        "results": metrics_by_symbol,
        "aggregate": _aggregate(metrics_by_symbol),
    }
    path = os.path.join(RESULTS_DIR, f"{tag}.json")
    with open(path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"  [saved] {path}")
    return output


def _aggregate(metrics_by_symbol: dict) -> dict:
    """Compute portfolio-level aggregate metrics across all symbols."""
    if not metrics_by_symbol:
        return {}
    sharpes  = [v["sharpe_ratio"] for v in metrics_by_symbol.values() if "sharpe_ratio" in v]
    drawdowns = [v["max_drawdown_pct"] for v in metrics_by_symbol.values() if "max_drawdown_pct" in v]
    returns  = [v["total_return_pct"] for v in metrics_by_symbol.values() if "total_return_pct" in v]
    return {
        "mean_sharpe":      round(sum(sharpes) / len(sharpes), 4) if sharpes else 0,
        "median_sharpe":    round(sorted(sharpes)[len(sharpes)//2], 4) if sharpes else 0,
        "mean_max_drawdown": round(sum(drawdowns) / len(drawdowns), 2) if drawdowns else 0,
        "mean_total_return": round(sum(returns) / len(returns), 2) if returns else 0,
        "num_symbols":      len(metrics_by_symbol),
    }


def print_summary(tag: str, metrics_by_symbol: dict, params: dict):
    """Print standardized experiment summary (agent reads this)."""
    agg = _aggregate(metrics_by_symbol)
    print("\n" + "─" * 50)
    print(f"TAG:              {tag}")
    print(f"mean_sharpe:      {agg.get('mean_sharpe', 'N/A')}")
    print(f"median_sharpe:    {agg.get('median_sharpe', 'N/A')}")
    print(f"mean_max_drawdown:{agg.get('mean_max_drawdown', 'N/A')}%")
    print(f"mean_total_return:{agg.get('mean_total_return', 'N/A')}%")
    print(f"num_symbols:      {agg.get('num_symbols', 0)}")
    print(f"params:           {json.dumps(params)}")
    print("─" * 50)
    for sym, m in metrics_by_symbol.items():
        print(f"  {sym:<14} sharpe={m.get('sharpe_ratio','?'):>7}  "
              f"dd={m.get('max_drawdown_pct','?'):>7}%  "
              f"ret={m.get('total_return_pct','?'):>7}%  "
              f"trades={m.get('num_trades','?')}")
    print("─" * 50 + "\n")


if __name__ == "__main__":
    print("Downloading data for all symbols...")
    data = download_data(force_refresh=False)
    print(f"\nDone. {len(data)}/{len(ALL_SYMBOLS)} symbols loaded.")
    print("Data ready. You can now run: python strategy.py")
