import csv
import json
import os
import pathlib
import webbrowser


def parse_tsv(path):
    """Read results.tsv and return a list of run dicts.

    Handles both 6-column (new: tag+commit+...) and 5-column (old: commit+...)
    formats. Numeric fields mean_sharpe and mean_max_dd are cast to float.
    """
    runs = []
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            runs.append({
                'tag': row.get('tag', ''),
                'commit': row['commit'],
                'mean_sharpe': float(row['mean_sharpe']),
                'mean_max_dd': float(row['mean_max_dd']),
                'status': row['status'],
                'description': row['description'],
            })
    return runs


def load_symbol_data(tag, results_dir='results'):
    """Load per-symbol data from results/<tag>.json.

    Returns None if the file does not exist or tag is empty.
    Returns a dict with keys: mean_total_return (float or None), symbols (dict).
    """
    if not tag:
        return None
    path = pathlib.Path(results_dir) / f"{tag}.json"
    if not path.exists():
        return None
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    return {
        'mean_total_return': data.get('aggregate', {}).get('mean_total_return'),
        'symbols': data.get('results', {}),
    }


def generate_html(runs):
    pass


def main():
    pass


if __name__ == '__main__':
    main()
