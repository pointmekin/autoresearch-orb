"""
backtest_all.py — Run and visualize backtests for each ticker individually.

Uses backtesting.py's built-in plotting to generate interactive HTML charts
for every symbol in the portfolio.

Usage:
    python backtest_all.py                  # All symbols, train data
    python backtest_all.py --test           # Use out-of-sample data
    python backtest_all.py --symbols SPY QQQ  # Specific symbols only
"""

import sys
import os
import argparse
import pandas as pd
from backtesting import Backtest

sys.path.insert(0, os.path.dirname(__file__))
from prepare import load_data, split_train_test, ALL_SYMBOLS, RESULTS_DIR
from strategy import ORBStrategy, PARAMS

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "backtest_plots")


def run_and_plot(symbol: str, df: pd.DataFrame, use_test: bool = False) -> dict:
    """Run backtest for a single symbol and save interactive HTML plot."""
    train_df, test_df = split_train_test(df)
    data = test_df if use_test else train_df
    label = "OOS" if use_test else "IS"

    # Set strategy params
    ORBStrategy.opening_range_bars         = PARAMS["opening_range_bars"]
    ORBStrategy.breakout_threshold         = PARAMS["breakout_threshold"]
    ORBStrategy.stop_loss_range_multiple   = PARAMS["stop_loss_range_multiple"]
    ORBStrategy.take_profit_range_multiple = PARAMS["take_profit_range_multiple"]
    ORBStrategy.max_trades_per_session     = PARAMS["max_trades_per_session"]
    ORBStrategy.min_range_pct              = PARAMS["min_range_pct"]
    ORBStrategy.close_at_session_end       = PARAMS["close_at_session_end"]

    bt = Backtest(
        data,
        ORBStrategy,
        cash=100_000,
        commission=0.0002,
        exclusive_orders=True,
        finalize_trades=True,
    )

    stats = bt.run()

    # Save plot
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    safe_name = symbol.replace("=", "_").replace("/", "_")
    plot_path = os.path.join(OUTPUT_DIR, f"{safe_name}_{label}.html")
    bt.plot(filename=plot_path, open_browser=False)

    return {
        "symbol": symbol,
        "period": label,
        "bars": len(data),
        "trades": int(stats.get("# Trades", 0)),
        "win_rate": round(float(stats.get("Win Rate [%]", 0)), 2),
        "return": round(float(stats.get("Return [%]", 0)), 2),
        "sharpe": round(float(stats.get("Sharpe Ratio", 0)), 4),
        "max_dd": round(float(stats.get("Max. Drawdown [%]", 0)), 2),
        "plot": plot_path,
    }


def main():
    parser = argparse.ArgumentParser(description="Backtest each ticker and generate plots")
    parser.add_argument("--test", action="store_true", help="Use out-of-sample (test) data")
    parser.add_argument("--symbols", nargs="+", help="Specific symbols to backtest")
    args = parser.parse_args()

    symbols = args.symbols or ALL_SYMBOLS
    data_all = load_data(symbols)

    results = []
    for sym in symbols:
        df = data_all.get(sym)
        if df is None or df.empty:
            print(f"[SKIP] {sym}: no data")
            continue

        # Flatten multi-level columns
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.rename(columns={"Open": "Open", "High": "High", "Low": "Low",
                                "Close": "Close", "Volume": "Volume"})
        df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()

        if len(df) < 50:
            print(f"[SKIP] {sym}: insufficient data ({len(df)} rows)")
            continue

        print(f"Backtesting {sym}...")
        try:
            r = run_and_plot(sym, df, use_test=args.test)
            results.append(r)
            print(f"  -> {r['trades']} trades | ret={r['return']}% | "
                  f"sharpe={r['sharpe']} | dd={r['max_dd']}% | "
                  f"wr={r['win_rate']}%")
        except Exception as e:
            print(f"  [ERR] {sym}: {e}")

    # Summary table
    if not results:
        print("No results.")
        return

    print("\n" + "=" * 90)
    print(f"{'Symbol':<14} {'Period':<6} {'Bars':>7} {'Trades':>7} "
          f"{'Return%':>9} {'Sharpe':>9} {'MaxDD%':>9} {'WinRate%':>9}")
    print("-" * 90)
    for r in results:
        print(f"{r['symbol']:<14} {r['period']:<6} {r['bars']:>7} {r['trades']:>7} "
              f"{r['return']:>9.2f} {r['sharpe']:>9.4f} {r['max_dd']:>9.2f} {r['win_rate']:>9.2f}")
    print("=" * 90)

    # Averages
    avg_ret = sum(r['return'] for r in results) / len(results)
    avg_sharpe = sum(r['sharpe'] for r in results) / len(results)
    avg_dd = sum(r['max_dd'] for r in results) / len(results)
    avg_wr = sum(r['win_rate'] for r in results) / len(results)
    print(f"{'AVERAGE':<14} {'':<6} {'':>7} {'':>7} "
          f"{avg_ret:>9.2f} {avg_sharpe:>9.4f} {avg_dd:>9.2f} {avg_wr:>9.2f}")
    print()
    print(f"Interactive HTML plots saved to: {OUTPUT_DIR}/")
    for r in results:
        print(f"  {r['symbol']}: file://{r['plot']}")


if __name__ == "__main__":
    main()
