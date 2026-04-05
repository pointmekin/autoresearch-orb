"""
strategy.py — Opening Range Breakout strategy implementation.
THIS IS THE ONLY FILE THE AGENT MODIFIES.

The agent may freely change:
  - ORB parameters (opening_range_minutes, breakout_threshold, etc.)
  - Entry/exit logic
  - Stop loss and take profit rules
  - Time filters (session hours, day-of-week)
  - Position sizing
  - Any other strategy logic

The agent may NOT:
  - Modify prepare.py
  - Change the metric computation logic
  - Add external data sources outside of Yahoo Finance
  - Change the symbols list (defined in prepare.py)

Goal: MAXIMIZE mean_sharpe across all symbols on in-sample data.
      We care about robustness (consistent across symbols), not curve-fitting one pair.
"""

import sys
import os
import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
from backtesting.lib import crossover

# Import fixed infrastructure (do not modify)
sys.path.insert(0, os.path.dirname(__file__))
from prepare import (
    load_data, split_train_test, compute_metrics,
    save_results, print_summary, ALL_SYMBOLS,
    LOGS_DIR
)

# ─── Strategy Parameters (agent modifies these) ──────────────────────────────

PARAMS = {
    # Opening range duration (bars). With 5m bars: 6 bars = 30 minutes.
    "opening_range_bars": 6,

    # Breakout threshold: how far price must exceed the range high/low to trigger entry.
    # 0.001 = 0.1% (tighter threshold suits 5m precision)
    "breakout_threshold": 0.001,

    # Stop loss as fraction of the opening range height.
    "stop_loss_range_multiple": 0.5,

    # Take profit as fraction of the opening range height.
    "take_profit_range_multiple": 1.5,

    # Maximum number of trades per day per symbol (0 = unlimited)
    "max_trades_per_day": 1,

    # Close all positions at end of session (True = no overnight holds)
    "close_at_session_end": True,

    # Session start hour (UTC). Range builds from first N bars at/after this hour.
    # 8 = London open (forex). Equity ETFs (SPY/QQQ) naturally start at 14:30 UTC.
    "session_start_hour_utc": 8,

    # Session end hour (UTC). Trades are closed after this hour.
    "session_end_hour_utc": 21,

    # Day-of-week filter: list of allowed weekdays (0=Mon, 4=Fri, 5=Sat, 6=Sun)
    "allowed_weekdays": [0, 1, 2, 3, 4],  # Mon–Fri
}

# ─── ORB Strategy Class ───────────────────────────────────────────────────────

class ORBStrategy(Strategy):
    """
    Classic Opening Range Breakout.

    Logic:
    1. Define opening range as the High/Low of the first `opening_range_bars` bars.
    2. If price breaks above range_high * (1 + breakout_threshold), go long.
    3. If price breaks below range_low * (1 - breakout_threshold), go short.
    4. Stop loss and take profit based on range height multiples.
    5. Close all trades at session_end_hour_utc.
    """

    # Strategy parameters (set by backtesting.py optimizer or from PARAMS)
    opening_range_bars        = PARAMS["opening_range_bars"]
    breakout_threshold        = PARAMS["breakout_threshold"]
    stop_loss_range_multiple  = PARAMS["stop_loss_range_multiple"]
    take_profit_range_multiple = PARAMS["take_profit_range_multiple"]
    max_trades_per_day        = PARAMS["max_trades_per_day"]
    close_at_session_end      = PARAMS["close_at_session_end"]
    session_start_hour_utc    = PARAMS["session_start_hour_utc"]
    session_end_hour_utc      = PARAMS["session_end_hour_utc"]

    def init(self):
        self._range_high = None
        self._range_low  = None
        self._current_session = None
        self._trades_today = 0
        self._range_set = False

    def next(self):
        current_time = self.data.index[-1]
        current_hour = current_time.hour

        # ── Session boundary: shifts "day" to start at session_start_hour_utc ─
        session_day = (current_time - pd.Timedelta(hours=self.session_start_hour_utc)).date()

        # ── New session: reset state ──────────────────────────────────────
        if session_day != self._current_session:
            self._current_session = session_day
            self._trades_today = 0
            self._range_set    = False
            self._range_high   = None
            self._range_low    = None
            self._day_open_bar = len(self.data) - 1

        # ── Before session start: skip ────────────────────────────────────
        if current_hour < self.session_start_hour_utc:
            return

        # ── Session end: close everything ─────────────────────────────────
        if self.close_at_session_end and current_hour >= self.session_end_hour_utc:
            if self.position:
                self.position.close()
            return

        # ── Skip disallowed weekdays ───────────────────────────────────────
        if current_time.weekday() not in PARAMS["allowed_weekdays"]:
            return

        # ── Build opening range ────────────────────────────────────────────
        bars_into_session = len(self.data) - 1 - self._day_open_bar

        if not self._range_set:
            if bars_into_session < self.opening_range_bars:
                return  # Still in range-formation window
            # Range is now complete — use first N bars of the session
            range_slice_high = self.data.High[-self.opening_range_bars - 1 : -1]
            range_slice_low  = self.data.Low[-self.opening_range_bars - 1 : -1]
            self._range_high = max(range_slice_high)
            self._range_low  = min(range_slice_low)
            self._range_set  = True

        if self._range_high is None or self._range_low is None:
            return

        range_height = self._range_high - self._range_low
        if range_height <= 0:
            return

        # ── Trade limit ───────────────────────────────────────────────────
        if self.max_trades_per_day > 0 and self._trades_today >= self.max_trades_per_day:
            return

        # ── Entry signals (breakout direction) ───────────────────────────
        close = self.data.Close[-1]
        sl_dist = range_height * self.stop_loss_range_multiple
        tp_dist = range_height * self.take_profit_range_multiple

        long_trigger  = self._range_high * (1 + self.breakout_threshold)
        short_trigger = self._range_low  * (1 - self.breakout_threshold)

        if not self.position:
            if close > long_trigger:
                sl = close - sl_dist
                tp = close + tp_dist
                self.buy(sl=sl, tp=tp)
                self._trades_today += 1

            elif close < short_trigger:
                sl = close + sl_dist
                tp = close - tp_dist
                self.sell(sl=sl, tp=tp)
                self._trades_today += 1


# ─── Run Backtest ─────────────────────────────────────────────────────────────

def run_experiment(tag: str, params: dict = None, optimize: bool = False):
    """
    Run backtest on all symbols, collect metrics, save results.

    Args:
        tag:      Short label for this experiment run (e.g. "baseline", "apr5_v1")
        params:   Override PARAMS dict (if None, uses module-level PARAMS)
        optimize: If True, run backtesting.py's optimizer on IS data before final evaluation
    """
    params = params or PARAMS
    data_all = load_data()

    metrics_by_symbol = {}

    for sym in ALL_SYMBOLS:
        df = data_all.get(sym)
        if df is None or df.empty:
            print(f"  [SKIP] {sym}: no data")
            continue

        # Flatten multi-level columns if present (yfinance quirk)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # Rename to backtesting.py expected format
        df = df.rename(columns={
            "Open": "Open", "High": "High", "Low": "Low",
            "Close": "Close", "Volume": "Volume"
        })
        df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()

        if len(df) < 50:
            print(f"  [SKIP] {sym}: insufficient data ({len(df)} rows)")
            continue

        train_df, test_df = split_train_test(df)

        # ── Set class-level params ────────────────────────────────────────
        ORBStrategy.opening_range_bars         = params["opening_range_bars"]
        ORBStrategy.breakout_threshold         = params["breakout_threshold"]
        ORBStrategy.stop_loss_range_multiple   = params["stop_loss_range_multiple"]
        ORBStrategy.take_profit_range_multiple = params["take_profit_range_multiple"]
        ORBStrategy.max_trades_per_day         = params["max_trades_per_day"]
        ORBStrategy.close_at_session_end       = params["close_at_session_end"]
        ORBStrategy.session_start_hour_utc     = params["session_start_hour_utc"]
        ORBStrategy.session_end_hour_utc       = params["session_end_hour_utc"]

        try:
            bt = Backtest(
                train_df,
                ORBStrategy,
                cash=100_000,
                commission=0.0002,   # 2 bps (realistic for forex/CFD)
                exclusive_orders=True,
                finalize_trades=True,
            )

            if optimize:
                stats = bt.optimize(
                    opening_range_bars        = [1, 2, 3, 4],
                    breakout_threshold        = [0.0, 0.001, 0.002],
                    stop_loss_range_multiple  = [0.3, 0.5, 0.75, 1.0],
                    take_profit_range_multiple= [1.0, 1.5, 2.0, 3.0],
                    maximize="Sharpe Ratio",
                    max_tries=200,
                )
            else:
                stats = bt.run()

            # Extract equity curve
            equity = stats["_equity_curve"]["Equity"]

            m = compute_metrics(equity)
            m["num_trades"] = int(stats.get("# Trades", 0))
            m["win_rate"]   = round(float(stats.get("Win Rate [%]", 0)) / 100, 4)

            metrics_by_symbol[sym] = m

        except Exception as e:
            print(f"  [ERR]  {sym}: {e}")
            metrics_by_symbol[sym] = {
                "sharpe_ratio": -999.0, "max_drawdown_pct": -999.0,
                "total_return_pct": -999.0, "calmar_ratio": -999.0,
                "num_trades": 0, "win_rate": 0.0, "error": str(e),
            }

    print_summary(tag, metrics_by_symbol, params)
    save_results(tag, metrics_by_symbol, params)
    return metrics_by_symbol


# ─── Entry point ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse, datetime

    parser = argparse.ArgumentParser(description="ORB Autoresearch — single experiment run")
    parser.add_argument("--tag",      default=None, help="Experiment tag (default: date-based)")
    parser.add_argument("--optimize", action="store_true", help="Run backtesting.py optimizer on IS data")
    args = parser.parse_args()

    tag = args.tag or datetime.datetime.now().strftime("%Y%m%d_%H%M")
    run_experiment(tag=tag, optimize=args.optimize)
