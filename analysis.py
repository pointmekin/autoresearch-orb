"""
analysis.py — Morning review script. Run after the overnight autoresearch loop.

Usage:
    python analysis.py                  # Summary of all experiments
    python analysis.py --best           # Print the best experiment's params
    python analysis.py --compare A B    # Compare two experiment tags side-by-side
    python analysis.py --plot           # Plot equity curves for best experiment
"""

import os
import json
import argparse
import glob
import pandas as pd
import matplotlib.pyplot as plt
from prepare import RESULTS_DIR, DATA_DIR, ALL_SYMBOLS, split_train_test, load_data

# ─── Load all experiment results ──────────────────────────────────────────────

def load_all_results():
    results = []
    for path in sorted(glob.glob(os.path.join(RESULTS_DIR, "*.json"))):
        with open(path) as f:
            try:
                data = json.load(f)
                data["_path"] = path
                results.append(data)
            except Exception as e:
                print(f"  [WARN] Could not load {path}: {e}")
    return results


def results_to_df(results):
    rows = []
    for r in results:
        agg = r.get("aggregate", {})
        rows.append({
            "tag":             r.get("tag", "?"),
            "timestamp":       r.get("timestamp", "?"),
            "mean_sharpe":     agg.get("mean_sharpe", None),
            "median_sharpe":   agg.get("median_sharpe", None),
            "mean_max_drawdown": agg.get("mean_max_drawdown", None),
            "mean_total_return": agg.get("mean_total_return", None),
            "num_symbols":     agg.get("num_symbols", 0),
            "notes":           r.get("notes", ""),
        })
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values("mean_sharpe", ascending=False)
    return df


def print_leaderboard(df, top_n=20):
    print("\n" + "═" * 80)
    print("  ORB AUTORESEARCH — EXPERIMENT LEADERBOARD")
    print("═" * 80)
    print(f"  {'TAG':<20} {'SHARPE':>8} {'MED.SH':>8} {'MAXDD%':>8} {'RET%':>8}  NOTES")
    print("─" * 80)
    for _, row in df.head(top_n).iterrows():
        print(
            f"  {str(row['tag']):<20} "
            f"{row['mean_sharpe']:>8.4f} "
            f"{row['median_sharpe']:>8.4f} "
            f"{row['mean_max_drawdown']:>8.2f} "
            f"{row['mean_total_return']:>8.2f}  "
            f"{str(row['notes'])[:40]}"
        )
    print("═" * 80)
    print(f"  Total experiments: {len(df)}")
    print()


def compare_experiments(tag_a, tag_b, results):
    """Print side-by-side comparison of two experiments."""
    exp = {r["tag"]: r for r in results}
    a = exp.get(tag_a)
    b = exp.get(tag_b)

    if not a or not b:
        print(f"Could not find both tags: {tag_a}, {tag_b}")
        return

    syms = sorted(set(list(a["results"].keys()) + list(b["results"].keys())))
    print(f"\n{'SYM':<14} {'SHARPE ' + tag_a:>14} {'SHARPE ' + tag_b:>14}   DELTA")
    print("─" * 55)
    for sym in syms:
        sa = a["results"].get(sym, {}).get("sharpe_ratio", None)
        sb = b["results"].get(sym, {}).get("sharpe_ratio", None)
        if sa is not None and sb is not None:
            delta = sb - sa
            arrow = "▲" if delta > 0 else "▼" if delta < 0 else "="
            print(f"  {sym:<14} {sa:>12.4f} {sb:>12.4f}   {arrow} {abs(delta):.4f}")

    print("\nAggregate:")
    for key in ["mean_sharpe", "median_sharpe", "mean_max_drawdown", "mean_total_return"]:
        va = a["aggregate"].get(key, "?")
        vb = b["aggregate"].get(key, "?")
        print(f"  {key:<25} {str(va):>10}  →  {str(vb):>10}")
    print()


def plot_best(results):
    """Plot equity curves for the best experiment's top symbols."""
    df = results_to_df(results)
    if df.empty:
        print("No results to plot.")
        return

    best_tag = df.iloc[0]["tag"]
    best_exp = next(r for r in results if r["tag"] == best_tag)

    print(f"Plotting best experiment: {best_tag}")
    print(f"  mean_sharpe = {best_exp['aggregate']['mean_sharpe']}")

    # Show top 6 symbols by individual Sharpe
    sym_sharpes = {
        sym: m.get("sharpe_ratio", -999)
        for sym, m in best_exp["results"].items()
    }
    top_syms = sorted(sym_sharpes, key=sym_sharpes.get, reverse=True)[:6]

    data_all = load_data(top_syms)

    from backtesting import Backtest
    from strategy import ORBStrategy, PARAMS

    # Apply best params
    best_params = best_exp.get("params", PARAMS)
    ORBStrategy.opening_range_bars         = best_params["opening_range_bars"]
    ORBStrategy.breakout_threshold         = best_params["breakout_threshold"]
    ORBStrategy.stop_loss_range_multiple   = best_params["stop_loss_range_multiple"]
    ORBStrategy.take_profit_range_multiple = best_params["take_profit_range_multiple"]

    fig, axes = plt.subplots(2, 3, figsize=(16, 9))
    axes = axes.flatten()

    for i, sym in enumerate(top_syms):
        df_sym = data_all[sym]
        if isinstance(df_sym.columns, pd.MultiIndex):
            df_sym.columns = df_sym.columns.get_level_values(0)
        df_sym = df_sym[["Open", "High", "Low", "Close", "Volume"]].dropna()

        train_df, test_df = split_train_test(df_sym)

        bt = Backtest(train_df, ORBStrategy, cash=100_000, commission=0.0002)
        stats = bt.run()
        equity = stats["_equity_curve"]["Equity"]

        ax = axes[i]
        equity.plot(ax=ax, color="#2196F3", linewidth=1.2)
        ax.set_title(
            f"{sym}\nSharpe: {sym_sharpes[sym]:.3f}",
            fontsize=10
        )
        ax.set_ylabel("Equity ($)")
        ax.grid(True, alpha=0.3)
        ax.axhline(100_000, color="gray", linestyle="--", linewidth=0.8)

    fig.suptitle(f"Best Experiment: {best_tag} | mean Sharpe: {best_exp['aggregate']['mean_sharpe']}", fontsize=13)
    plt.tight_layout()

    out_path = os.path.join(RESULTS_DIR, f"{best_tag}_equity_curves.png")
    plt.savefig(out_path, dpi=120, bbox_inches="tight")
    print(f"  Saved: {out_path}")
    plt.show()


# ─── CLI ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ORB Autoresearch Analysis")
    parser.add_argument("--best",    action="store_true", help="Print best experiment params")
    parser.add_argument("--compare", nargs=2, metavar=("TAG_A", "TAG_B"), help="Compare two experiments")
    parser.add_argument("--plot",    action="store_true", help="Plot equity curves for best experiment")
    parser.add_argument("--top",     type=int, default=20, help="Show top N in leaderboard")
    args = parser.parse_args()

    results = load_all_results()
    if not results:
        print("No experiment results found in results/. Run strategy.py first.")
        exit(0)

    df = results_to_df(results)
    print_leaderboard(df, top_n=args.top)

    if args.best:
        best = results[0] if results else None
        if best:
            best_tag = df.iloc[0]["tag"]
            best_exp = next(r for r in results if r["tag"] == best_tag)
            print("Best experiment parameters:")
            print(json.dumps(best_exp.get("params", {}), indent=2))

    if args.compare:
        compare_experiments(args.compare[0], args.compare[1], results)

    if args.plot:
        plot_best(results)
