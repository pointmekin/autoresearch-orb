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
        has_tag = 'tag' in (reader.fieldnames or [])
        for row in reader:
            if has_tag:
                runs.append({
                    'tag': row['tag'],
                    'commit': row['commit'],
                    'mean_sharpe': float(row['mean_sharpe']),
                    'mean_max_dd': float(row['mean_max_dd']),
                    'status': row['status'],
                    'description': row['description'],
                })
            else:
                runs.append({
                    'tag': '',
                    'commit': row['commit'],
                    'mean_sharpe': float(row['mean_sharpe']),
                    'mean_max_dd': float(row['mean_max_dd']),
                    'status': row['status'],
                    'description': row['description'],
                })
    return runs


def load_symbol_data(tag, results_dir='results'):
    pass


def generate_html(runs):
    pass


def main():
    pass


if __name__ == '__main__':
    main()
