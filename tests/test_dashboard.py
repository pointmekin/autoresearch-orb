import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from dashboard import parse_tsv, load_symbol_data


class TestParseTsv(unittest.TestCase):

    def _write_tsv(self, content):
        f = tempfile.NamedTemporaryFile(mode='w', suffix='.tsv', delete=False)
        f.write(content)
        f.close()
        return f.name

    def test_new_format_six_columns(self):
        path = self._write_tsv(
            "tag\tcommit\tmean_sharpe\tmean_max_dd\tstatus\tdescription\n"
            "apr5_001\tabc1234\t1.23\t-0.45\tkeep\tbaseline run\n"
        )
        runs = parse_tsv(path)
        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0]['tag'], 'apr5_001')
        self.assertEqual(runs[0]['commit'], 'abc1234')
        self.assertAlmostEqual(runs[0]['mean_sharpe'], 1.23)
        self.assertAlmostEqual(runs[0]['mean_max_dd'], -0.45)
        self.assertEqual(runs[0]['status'], 'keep')
        self.assertEqual(runs[0]['description'], 'baseline run')
        os.unlink(path)

    def test_old_format_five_columns(self):
        # Old format has no tag column — tag should be set to empty string
        path = self._write_tsv(
            "commit\tmean_sharpe\tmean_max_dd\tstatus\tdescription\n"
            "abc1234\t1.23\t-0.45\tkeep\tbaseline run\n"
        )
        runs = parse_tsv(path)
        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0]['tag'], '')
        self.assertEqual(runs[0]['commit'], 'abc1234')
        self.assertAlmostEqual(runs[0]['mean_sharpe'], 1.23)
        os.unlink(path)

    def test_header_only_returns_empty(self):
        path = self._write_tsv(
            "tag\tcommit\tmean_sharpe\tmean_max_dd\tstatus\tdescription\n"
        )
        runs = parse_tsv(path)
        self.assertEqual(runs, [])
        os.unlink(path)

    def test_multiple_rows(self):
        path = self._write_tsv(
            "tag\tcommit\tmean_sharpe\tmean_max_dd\tstatus\tdescription\n"
            "apr5_001\tabc1234\t1.23\t-0.45\tkeep\tfirst\n"
            "apr5_002\tdef5678\t0.50\t-1.20\tdiscard\tsecond\n"
            "apr5_003\tghi9012\t0.00\t0.00\tcrash\tthird\n"
        )
        runs = parse_tsv(path)
        self.assertEqual(len(runs), 3)
        self.assertEqual(runs[1]['status'], 'discard')
        self.assertEqual(runs[2]['tag'], 'apr5_003')
        os.unlink(path)
