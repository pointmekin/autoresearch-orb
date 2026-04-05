# Results Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `dashboard.py` — a script that reads `results.tsv` + per-run JSON files and generates a self-contained interactive `dashboard.html` for visualizing experiment progress.

**Architecture:** `dashboard.py` parses `results.tsv` (which now includes a `tag` column), enriches each row with per-symbol data from `results/<tag>.json` if available, embeds everything as a JSON blob into an HTML template, writes `dashboard.html`, and opens it via `python -m webbrowser`. The HTML uses Chart.js (CDN) for the chart and vanilla JS for interactivity.

**Tech Stack:** Python 3 stdlib only (`json`, `csv`, `pathlib`, `webbrowser`, `unittest`). Chart.js 4.x via CDN in generated HTML.

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `dashboard.py` | Create | Data loading, HTML generation, entrypoint |
| `tests/test_dashboard.py` | Create | Unit tests for parse_tsv and load_symbol_data |
| `.gitignore` | Create | Exclude `dashboard.html` and `.superpowers/` |
| `program.md` | Modify | Update TSV format docs + loop step 8 + header row |

---

### Task 1: Create .gitignore and update program.md

**Files:**
- Create: `.gitignore`
- Modify: `program.md`

- [ ] **Step 1: Create `.gitignore`**

```
dashboard.html
.superpowers/
```

- [ ] **Step 2: Update `program.md` — TSV header row format**

Find the "Format:" block in `program.md` under "Logging Results". Replace:
```
commit\tmean_sharpe\tmean_max_dd\tstatus\tdescription
```
with:
```
tag\tcommit\tmean_sharpe\tmean_max_dd\tstatus\tdescription
```

- [ ] **Step 3: Update `program.md` — TSV column list**

Find the "Columns:" list under "Logging Results". Replace:
```
1. git commit hash (short, 7 chars)
2. mean_sharpe across all symbols (e.g. `0.8234`)
3. mean_max_drawdown (e.g. `-18.4`)
4. status: `keep`, `discard`, or `crash`
5. short description of what this experiment tried
```
with:
```
1. tag — the same tag used for `--tag` in the run command (e.g. `apr5_001`)
2. git commit hash (short, 7 chars)
3. mean_sharpe across all symbols (e.g. `0.8234`)
4. mean_max_drawdown (e.g. `-18.4`)
5. status: `keep`, `discard`, or `crash`
6. short description of what this experiment tried
```

- [ ] **Step 4: Update `program.md` — TSV example block**

Find the example block under "Example:". Replace:
```
commit	mean_sharpe	mean_max_dd	status	description
a1b2c3d	0.4521	-22.3	keep	baseline ORB 2-bar range
b2c3d4e	0.5103	-19.8	keep	reduce SL to 0.3x range
c3d4e5f	0.3812	-28.1	discard	increase breakout threshold to 0.003
d4e5f6g	0.0000	0.0	crash	vectorized ORB (bug in indicator)
e5f6g7h	0.6441	-17.2	keep	add Mon-Thu filter only
```
with:
```
tag	commit	mean_sharpe	mean_max_dd	status	description
apr5_001	a1b2c3d	0.4521	-22.3	keep	baseline ORB 2-bar range
apr5_002	b2c3d4e	0.5103	-19.8	keep	reduce SL to 0.3x range
apr5_003	c3d4e5f	0.3812	-28.1	discard	increase breakout threshold to 0.003
apr5_004	d4e5f6g	0.0000	0.0	crash	vectorized ORB (bug in indicator)
apr5_005	e5f6g7h	0.6441	-17.2	keep	add Mon-Thu filter only
```

- [ ] **Step 5: Update `program.md` — loop step 8**

Find step 8 in "The Experiment Loop":
```
8. Log result to `results.tsv`
```
Replace with:
```
8. **Stage and amend the commit to include the log and results**: `git add logs/<prefix>_NNN.log results/<prefix>_NNN.json && git commit --amend --no-edit`
9. Log result to `results.tsv`: `<tag>\t<commit>\t<mean_sharpe>\t<mean_max_dd>\t<status>\t<description>`
```
(Note: renumber subsequent steps — old 9 becomes 10, old 10 becomes 11, old 11 becomes 12.)

- [ ] **Step 6: Commit**

```bash
git add .gitignore program.md
git commit -m "docs: add tag column to results.tsv format, add .gitignore"
```

---

### Task 2: Implement `parse_tsv` with tests

**Files:**
- Create: `tests/test_dashboard.py`
- Create: `dashboard.py` (initial skeleton + `parse_tsv`)

- [ ] **Step 1: Write the failing tests**

Create `tests/test_dashboard.py`:

```python
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
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
python -m unittest tests.test_dashboard.TestParseTsv -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError: No module named 'dashboard'`

- [ ] **Step 3: Create `dashboard.py` skeleton with `parse_tsv`**

```python
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
```

- [ ] **Step 4: Run tests — confirm parse_tsv passes**

```bash
python -m unittest tests.test_dashboard.TestParseTsv -v
```

Expected: 4 tests pass, `load_symbol_data` tests still skipped/not yet added.

- [ ] **Step 5: Commit**

```bash
git add dashboard.py tests/test_dashboard.py
git commit -m "feat: add parse_tsv with tests"
```

---

### Task 3: Implement `load_symbol_data` with tests

**Files:**
- Modify: `tests/test_dashboard.py`
- Modify: `dashboard.py`

- [ ] **Step 1: Add tests for `load_symbol_data` to `tests/test_dashboard.py`**

Add this class after `TestParseTsv`:

```python
class TestLoadSymbolData(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir)

    def _write_json(self, tag, data):
        path = os.path.join(self.tmpdir, f"{tag}.json")
        with open(path, 'w') as f:
            json.dump(data, f)

    def test_returns_none_for_missing_tag(self):
        result = load_symbol_data('nonexistent_tag', self.tmpdir)
        self.assertIsNone(result)

    def test_returns_symbol_data_and_total_return(self):
        self._write_json('apr5_001', {
            "tag": "apr5_001",
            "aggregate": {
                "mean_sharpe": 1.82,
                "mean_total_return": 3.45,
            },
            "results": {
                "EURUSD=X": {"sharpe_ratio": 2.1, "num_trades": 10},
                "GC=F": {"sharpe_ratio": -0.5, "num_trades": 8},
            }
        })
        result = load_symbol_data('apr5_001', self.tmpdir)
        self.assertIsNotNone(result)
        self.assertAlmostEqual(result['mean_total_return'], 3.45)
        self.assertIn('EURUSD=X', result['symbols'])
        self.assertAlmostEqual(result['symbols']['EURUSD=X']['sharpe_ratio'], 2.1)
```

- [ ] **Step 2: Run to confirm new tests fail**

```bash
python -m unittest tests.test_dashboard.TestLoadSymbolData -v
```

Expected: both tests fail — `load_symbol_data` returns `None` for all inputs.

- [ ] **Step 3: Implement `load_symbol_data` in `dashboard.py`**

Replace the stub:

```python
def load_symbol_data(tag, results_dir='results'):
    """Load per-symbol data from results/<tag>.json.

    Returns None if the file does not exist.
    Returns a dict with keys: mean_total_return (float), symbols (dict).
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
```

- [ ] **Step 4: Run all tests**

```bash
python -m unittest discover -s tests -v
```

Expected: all 6 tests pass.

- [ ] **Step 5: Commit**

```bash
git add dashboard.py tests/test_dashboard.py
git commit -m "feat: add load_symbol_data with tests"
```

---

### Task 4: Implement `generate_html`

**Files:**
- Modify: `dashboard.py`
- Modify: `tests/test_dashboard.py`

- [ ] **Step 1: Add smoke test for `generate_html` to `tests/test_dashboard.py`**

Add after `TestLoadSymbolData`:

```python
class TestGenerateHtml(unittest.TestCase):

    def _make_run(self, tag, sharpe, status):
        return {
            'tag': tag,
            'commit': 'abc1234',
            'mean_sharpe': sharpe,
            'mean_max_dd': -0.5,
            'status': status,
            'description': 'test run',
            'mean_total_return': None,
            'symbols': None,
        }

    def test_returns_html_string(self):
        runs = [self._make_run('apr5_001', 1.5, 'keep')]
        html = generate_html(runs)
        self.assertIsInstance(html, str)
        self.assertTrue(html.startswith('<!DOCTYPE html>'))

    def test_embeds_run_data(self):
        runs = [self._make_run('apr5_001', 1.5, 'keep')]
        html = generate_html(runs)
        self.assertIn('apr5_001', html)
        self.assertIn('chart.js', html.lower())

    def test_embeds_multiple_runs(self):
        runs = [
            self._make_run('apr5_001', 1.5, 'keep'),
            self._make_run('apr5_002', 0.8, 'discard'),
        ]
        html = generate_html(runs)
        self.assertIn('apr5_002', html)
```

- [ ] **Step 2: Run to confirm they fail**

```bash
python -m unittest tests.test_dashboard.TestGenerateHtml -v
```

Expected: 3 failures — `generate_html` returns `None`.

- [ ] **Step 3: Implement `generate_html` in `dashboard.py`**

Replace the stub:

```python
def generate_html(runs):
    """Generate a self-contained HTML dashboard string from a list of run dicts."""
    runs_json = json.dumps(runs, indent=2)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>ORB Autoresearch — Results</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: #0d0d0d; color: #ccc; font-family: 'Courier New', monospace; padding: 20px; }}
  #header {{ display: flex; justify-content: space-between; align-items: center;
             background: #1a1a2e; padding: 12px 16px; border-radius: 6px; margin-bottom: 16px; }}
  #header .title {{ color: #e0e0ff; font-size: 13px; font-weight: bold; letter-spacing: 1px; }}
  #header .meta {{ color: #555; font-size: 11px; }}
  #chart-panel {{ background: #111; border: 1px solid #222; border-radius: 6px;
                  padding: 16px; margin-bottom: 16px; }}
  #chart-label {{ font-size: 10px; color: #444; text-transform: uppercase;
                  letter-spacing: 1px; margin-bottom: 12px; }}
  #chart-container {{ position: relative; height: 300px; }}
  .legend {{ display: flex; gap: 16px; margin-top: 10px; }}
  .legend-item {{ display: flex; align-items: center; gap: 6px; font-size: 10px; color: #555; }}
  .legend-dot {{ width: 10px; height: 10px; border-radius: 2px; }}
  #detail-panel {{ background: #111; border: 1px solid #222; border-radius: 6px;
                   padding: 16px; display: none; }}
  #detail-header {{ display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }}
  #detail-tag {{ font-size: 11px; color: #888; }}
  #detail-commit {{ font-size: 10px; color: #444; }}
  .badge {{ padding: 2px 7px; border-radius: 3px; font-size: 9px;
            text-transform: uppercase; letter-spacing: 0.5px; }}
  .badge-keep {{ background: #1a3a1a; color: #66bb6a; }}
  .badge-discard {{ background: #2a2a2a; color: #666; }}
  .badge-crash {{ background: #3a1a1a; color: #ef5350; }}
  #detail-desc {{ font-size: 12px; color: #e0e0ff; margin-bottom: 14px;
                  line-height: 1.5; border-left: 2px solid #333; padding-left: 10px; }}
  .metrics-row {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-bottom: 16px; }}
  .metric-box {{ background: #0d0d0d; border-radius: 4px; padding: 10px; text-align: center; }}
  .metric-val {{ font-size: 18px; }}
  .metric-val.pos {{ color: #4fc3f7; }}
  .metric-val.neg {{ color: #ef5350; }}
  .metric-val.neutral {{ color: #888; }}
  .metric-label {{ font-size: 9px; color: #444; text-transform: uppercase;
                   letter-spacing: 0.5px; margin-top: 3px; }}
  #symbols-section {{ display: none; }}
  #symbols-title {{ font-size: 10px; color: #444; text-transform: uppercase;
                    letter-spacing: 1px; margin-bottom: 10px; }}
  .symbol-row {{ display: flex; align-items: center; gap: 8px; margin-bottom: 5px; }}
  .symbol-name {{ font-size: 10px; color: #555; width: 80px; flex-shrink: 0; }}
  .symbol-bar-bg {{ flex: 1; height: 12px; background: #0d0d0d; border-radius: 2px; overflow: hidden; }}
  .symbol-bar-fill {{ height: 100%; border-radius: 2px; transition: width 0.2s; }}
  .symbol-bar-fill.pos {{ background: #4fc3f7; }}
  .symbol-bar-fill.neg {{ background: #ef5350; }}
  .symbol-val {{ font-size: 10px; width: 44px; text-align: right; }}
  .symbol-val.pos {{ color: #4fc3f7; }}
  .symbol-val.neg {{ color: #ef5350; }}
</style>
</head>
<body>

<div id="header">
  <span class="title">ORB AUTORESEARCH — RESULTS</span>
  <span class="meta" id="header-meta"></span>
</div>

<div id="chart-panel">
  <div id="chart-label">mean_sharpe by iteration — click a bar to inspect</div>
  <div id="chart-container"><canvas id="chart"></canvas></div>
  <div class="legend">
    <div class="legend-item"><div class="legend-dot" style="background:#4fc3f7"></div>keep</div>
    <div class="legend-item"><div class="legend-dot" style="background:#3a3a3a"></div>discard</div>
    <div class="legend-item"><div class="legend-dot" style="background:#b71c1c"></div>crash</div>
  </div>
</div>

<div id="detail-panel">
  <div id="detail-header">
    <span id="detail-tag"></span>
    <span id="detail-badge" class="badge"></span>
    <span id="detail-commit"></span>
  </div>
  <div id="detail-desc"></div>
  <div class="metrics-row">
    <div class="metric-box">
      <div class="metric-val" id="m-sharpe"></div>
      <div class="metric-label">mean sharpe</div>
    </div>
    <div class="metric-box">
      <div class="metric-val" id="m-dd"></div>
      <div class="metric-label">mean max dd</div>
    </div>
    <div class="metric-box">
      <div class="metric-val" id="m-return"></div>
      <div class="metric-label">mean return %</div>
    </div>
  </div>
  <div id="symbols-section">
    <div id="symbols-title">per-symbol sharpe ratio</div>
    <div id="symbols-list"></div>
  </div>
</div>

<script>
const RUNS = {runs_json};

// Header meta
const total = RUNS.length;
const best = Math.max(...RUNS.map(r => r.mean_sharpe));
document.getElementById('header-meta').textContent =
  total + ' runs · best sharpe: ' + best.toFixed(4);

// Chart data
const labels = RUNS.map((r, i) => r.tag || ('#' + (i + 1)));
const barColors = RUNS.map(r =>
  r.status === 'keep' ? '#4fc3f7' :
  r.status === 'crash' ? '#b71c1c' : '#3a3a3a'
);
const lineData = RUNS.map(r => r.status === 'keep' ? r.mean_sharpe : null);

let selectedIndex = null;

const ctx = document.getElementById('chart').getContext('2d');
const chart = new Chart(ctx, {{
  data: {{
    labels,
    datasets: [
      {{
        type: 'bar',
        label: 'mean_sharpe',
        data: RUNS.map(r => r.mean_sharpe),
        backgroundColor: barColors,
        borderWidth: 0,
        borderRadius: 2,
      }},
      {{
        type: 'line',
        label: 'keep frontier',
        data: lineData,
        borderColor: 'rgba(79,195,247,0.4)',
        borderWidth: 1.5,
        pointRadius: 0,
        fill: false,
        spanGaps: false,
        tension: 0,
      }}
    ]
  }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    onClick: (e, elements) => {{
      if (!elements.length) return;
      const idx = elements[0].index;
      if (idx === selectedIndex) {{
        selectedIndex = null;
        document.getElementById('detail-panel').style.display = 'none';
      }} else {{
        selectedIndex = idx;
        renderDetail(RUNS[idx]);
      }}
    }},
    plugins: {{
      legend: {{ display: false }},
      tooltip: {{
        callbacks: {{
          title: (items) => labels[items[0].dataIndex],
          label: (item) => {{
            if (item.datasetIndex !== 0) return null;
            const r = RUNS[item.dataIndex];
            const desc = r.description.length > 60
              ? r.description.slice(0, 57) + '...'
              : r.description;
            return ['sharpe: ' + r.mean_sharpe.toFixed(4), desc];
          }}
        }},
        backgroundColor: '#1a1a2e',
        titleColor: '#e0e0ff',
        bodyColor: '#888',
        borderColor: '#333',
        borderWidth: 1,
        padding: 10,
      }}
    }},
    scales: {{
      x: {{
        grid: {{ display: false }},
        ticks: {{ color: '#444', maxRotation: 60, font: {{ size: 9 }} }}
      }},
      y: {{
        grid: {{ color: '#1a1a1a' }},
        ticks: {{ color: '#555', font: {{ size: 10 }} }},
        border: {{ dash: [2, 2] }}
      }}
    }}
  }}
}});

// Zero reference line plugin
Chart.register({{
  id: 'zeroline',
  afterDraw(chart) {{
    const y0 = chart.scales.y.getPixelForValue(0);
    const ctx = chart.ctx;
    ctx.save();
    ctx.beginPath();
    ctx.setLineDash([4, 4]);
    ctx.strokeStyle = '#333';
    ctx.lineWidth = 1;
    ctx.moveTo(chart.chartArea.left, y0);
    ctx.lineTo(chart.chartArea.right, y0);
    ctx.stroke();
    ctx.restore();
  }}
}});

function renderDetail(run) {{
  document.getElementById('detail-panel').style.display = 'block';
  document.getElementById('detail-tag').textContent = run.tag || run.commit;
  document.getElementById('detail-commit').textContent = run.commit;

  const badge = document.getElementById('detail-badge');
  badge.textContent = run.status;
  badge.className = 'badge badge-' + run.status;

  document.getElementById('detail-desc').textContent = run.description;

  const sharpeEl = document.getElementById('m-sharpe');
  sharpeEl.textContent = run.mean_sharpe.toFixed(4);
  sharpeEl.className = 'metric-val ' + (run.mean_sharpe >= 0 ? 'pos' : 'neg');

  const ddEl = document.getElementById('m-dd');
  ddEl.textContent = run.mean_max_dd.toFixed(2);
  ddEl.className = 'metric-val neg';

  const retEl = document.getElementById('m-return');
  if (run.mean_total_return !== null && run.mean_total_return !== undefined) {{
    retEl.textContent = run.mean_total_return.toFixed(2) + '%';
    retEl.className = 'metric-val ' + (run.mean_total_return >= 0 ? 'pos' : 'neg');
  }} else {{
    retEl.textContent = '—';
    retEl.className = 'metric-val neutral';
  }}

  const symbolsSection = document.getElementById('symbols-section');
  const symbolsList = document.getElementById('symbols-list');
  symbolsList.innerHTML = '';

  if (run.symbols && Object.keys(run.symbols).length > 0) {{
    symbolsSection.style.display = 'block';
    const entries = Object.entries(run.symbols)
      .map(([sym, d]) => [sym, d.sharpe_ratio])
      .sort((a, b) => b[1] - a[1]);

    const maxAbs = Math.max(...entries.map(([, v]) => Math.abs(v)), 0.001);

    entries.forEach(([sym, sharpe]) => {{
      const pct = Math.abs(sharpe) / maxAbs * 100;
      const isPos = sharpe >= 0;
      const row = document.createElement('div');
      row.className = 'symbol-row';
      row.innerHTML = `
        <span class="symbol-name">${{sym}}</span>
        <div class="symbol-bar-bg">
          <div class="symbol-bar-fill ${{isPos ? 'pos' : 'neg'}}" style="width:${{pct.toFixed(1)}}%"></div>
        </div>
        <span class="symbol-val ${{isPos ? 'pos' : 'neg'}}">${{sharpe.toFixed(2)}}</span>
      `;
      symbolsList.appendChild(row);
    }});
  }} else {{
    symbolsSection.style.display = 'none';
  }}
}}
</script>
</body>
</html>"""
```

- [ ] **Step 4: Run all tests**

```bash
python -m unittest discover -s tests -v
```

Expected: all 9 tests pass.

- [ ] **Step 5: Commit**

```bash
git add dashboard.py tests/test_dashboard.py
git commit -m "feat: implement generate_html with Chart.js"
```

---

### Task 5: Implement `main()` and wire everything

**Files:**
- Modify: `dashboard.py`

- [ ] **Step 1: Implement `main()` in `dashboard.py`**

Replace the stub:

```python
def main():
    """Generate dashboard.html from results.tsv + results/*.json and open it."""
    script_dir = pathlib.Path(__file__).parent
    tsv_path = script_dir / 'results.tsv'
    results_dir = script_dir / 'results'
    output_path = script_dir / 'dashboard.html'

    if not tsv_path.exists():
        print(f"Error: {tsv_path} not found. Run some experiments first.")
        return

    runs = parse_tsv(str(tsv_path))

    for run in runs:
        sym_data = load_symbol_data(run['tag'], str(results_dir))
        if sym_data:
            run['mean_total_return'] = sym_data['mean_total_return']
            run['symbols'] = sym_data['symbols']
        else:
            run['mean_total_return'] = None
            run['symbols'] = None

    html = generate_html(runs)
    output_path.write_text(html, encoding='utf-8')
    print(f"Dashboard written to {output_path}")
    webbrowser.open(output_path.as_uri())
```

- [ ] **Step 2: Run all tests to make sure nothing broke**

```bash
python -m unittest discover -s tests -v
```

Expected: all 9 tests pass.

- [ ] **Step 3: Smoke-test manually with real data**

```bash
python dashboard.py
```

Expected: prints `Dashboard written to .../dashboard.html` and opens it in browser. Chart shows ~76 bars. Clicking a bar with a matching JSON expands the detail panel with per-symbol breakdown.

- [ ] **Step 4: Commit**

```bash
git add dashboard.py
git commit -m "feat: wire main() — dashboard.py generates and opens dashboard.html"
```

---

## Self-Review

**Spec coverage check:**
- ✅ `python dashboard.py` generates and opens HTML — Task 5
- ✅ Keep commits as progress line — Task 4 (`generate_html`, line dataset)
- ✅ Discards as grey bars, crashes as red bars — Task 4 (`barColors`)
- ✅ Zero dashed line — Task 4 (zeroline plugin)
- ✅ Hover tooltip with tag + sharpe + description — Task 4 (tooltip callbacks)
- ✅ Click to expand detail panel — Task 4 (`onClick`, `renderDetail`)
- ✅ Click same bar to collapse — Task 4 (`selectedIndex` toggle)
- ✅ Detail: tag, status badge, commit — Task 4
- ✅ Detail: description — Task 4
- ✅ Detail: 3 metric boxes (sharpe, dd, return) — Task 4; return from JSON aggregate
- ✅ Per-symbol sharpe bars, sorted descending, pos/neg colors — Task 4
- ✅ `tag` column added to TSV format — Task 1
- ✅ `program.md` updated — Task 1
- ✅ `.gitignore` with `dashboard.html` and `.superpowers/` — Task 1
- ✅ Old 5-column TSV still works — Task 2 (`parse_tsv` detects format)
- ✅ Rows without JSON show `—` for return, no symbol bars — Task 4 + Task 5

**Placeholder scan:** None found.

**Type consistency:** `parse_tsv` returns dicts with `tag`, `commit`, `mean_sharpe`, `mean_max_dd`, `status`, `description`. `main()` adds `mean_total_return` and `symbols` to each dict before passing to `generate_html`. `generate_html` uses all 8 keys. `renderDetail` JS function uses all 8 keys — consistent.
