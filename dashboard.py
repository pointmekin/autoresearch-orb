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
  .chart-panel {{ background: #111; border: 1px solid #222; border-radius: 6px;
                  padding: 16px; margin-bottom: 16px; }}
  .chart-label {{ display: flex; justify-content: space-between; align-items: center;
                  font-size: 10px; color: #444; text-transform: uppercase;
                  letter-spacing: 1px; margin-bottom: 12px; }}
  #hide-neg-label {{ display: flex; align-items: center; gap: 5px; cursor: pointer;
                     font-size: 10px; color: #555; text-transform: uppercase;
                     letter-spacing: 0.5px; }}
  #hide-neg {{ cursor: pointer; accent-color: #4fc3f7; }}
  .chart-container {{ position: relative; height: 300px; }}
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
  .metric-val.warn {{ color: #ff9800; }}
  .metric-label {{ font-size: 9px; color: #444; text-transform: uppercase;
                   letter-spacing: 0.5px; margin-top: 3px; }}
  #symbols-section {{ display: none; }}
  .symbols-header {{ display: flex; align-items: center; gap: 12px; margin-bottom: 10px; }}
  .metric-tabs {{ display: flex; gap: 2px; }}
  .metric-tab {{ padding: 3px 10px; border-radius: 3px; font-size: 9px;
                 text-transform: uppercase; letter-spacing: 0.5px; cursor: pointer;
                 background: #0d0d0d; color: #444; border: none; font-family: inherit;
                 transition: all 0.15s; }}
  .metric-tab:hover {{ color: #888; }}
  .metric-tab.active {{ background: #1a1a2e; color: #e0e0ff; }}
  .symbol-row {{ display: flex; align-items: center; gap: 8px; margin-bottom: 5px; }}
  .symbol-name {{ font-size: 10px; color: #555; width: 80px; flex-shrink: 0; }}
  .symbol-bar-bg {{ flex: 1; height: 12px; background: #0d0d0d; border-radius: 2px; overflow: hidden; }}
  .symbol-bar-fill {{ height: 100%; border-radius: 2px; transition: width 0.2s; }}
  .symbol-bar-fill.pos {{ background: #4fc3f7; }}
  .symbol-bar-fill.neg {{ background: #ef5350; }}
  .symbol-bar-fill.warn {{ background: #ff9800; }}
  .symbol-val {{ font-size: 10px; width: 52px; text-align: right; }}
  .symbol-val.pos {{ color: #4fc3f7; }}
  .symbol-val.neg {{ color: #ef5350; }}
  .symbol-val.warn {{ color: #ff9800; }}
</style>
</head>
<body>

<div id="header">
  <span class="title">ORB AUTORESEARCH — RESULTS</span>
  <span class="meta" id="header-meta"></span>
</div>

<div class="chart-panel" id="sharpe-panel">
  <div class="chart-label">
    <span>mean_sharpe by iteration — click a bar to inspect</span>
    <label id="hide-neg-label">
      <input type="checkbox" id="hide-neg" checked> hide negative sharpe
    </label>
  </div>
  <div class="chart-container"><canvas id="chart"></canvas></div>
  <div class="legend">
    <div class="legend-item"><div class="legend-dot" style="background:#4fc3f7"></div>keep</div>
    <div class="legend-item"><div class="legend-dot" style="background:#3a3a3a"></div>discard</div>
    <div class="legend-item"><div class="legend-dot" style="background:#b71c1c"></div>crash</div>
  </div>
</div>

<div class="chart-panel" id="dd-panel">
  <div class="chart-label">
    <span>mean_max_drawdown by iteration — click a bar to inspect</span>
  </div>
  <div class="chart-container" style="height:200px"><canvas id="dd-chart"></canvas></div>
  <div class="legend">
    <div class="legend-item"><div class="legend-dot" style="background:#ff9800"></div>keep</div>
    <div class="legend-item"><div class="legend-dot" style="background:#3a3a3a"></div>discard</div>
    <div class="legend-item"><div class="legend-dot" style="background:#b71c1c"></div>crash</div>
  </div>
</div>

<div class="chart-panel" id="wr-panel">
  <div class="chart-label">
    <span>mean_win_rate by iteration — click a bar to inspect</span>
  </div>
  <div class="chart-container" style="height:180px"><canvas id="wr-chart"></canvas></div>
  <div class="legend">
    <div class="legend-item"><div class="legend-dot" style="background:#66bb6a"></div>keep</div>
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
    <div class="symbols-header">
      <div class="metric-tabs">
        <button class="metric-tab active" data-metric="sharpe">sharpe</button>
        <button class="metric-tab" data-metric="dd">drawdown</button>
        <button class="metric-tab" data-metric="return">return</button>
      </div>
    </div>
    <div id="symbols-list"></div>
  </div>
</div>

<script>
const RUNS = {runs_json};
let activeMetric = 'sharpe';
let selectedRun = null;

// Header meta
const total = RUNS.length;
const best = Math.max(...RUNS.map(r => r.mean_sharpe));
const bestDD = Math.max(...RUNS.map(r => r.mean_max_dd));
document.getElementById('header-meta').textContent =
  total + ' runs · best sharpe: ' + best.toFixed(4) + ' · best dd: ' + bestDD.toFixed(2);

// Shared chart data
const labels = RUNS.map((r, i) => r.tag || ('#' + (i + 1)));
const statusColor = (keep, crash) =>
  status === 'keep' ? keep : (status === 'crash' ? crash : '#3a3a3a');

const sharpeColors = RUNS.map(r =>
  r.status === 'keep' ? '#4fc3f7' :
  r.status === 'crash' ? '#b71c1c' : '#3a3a3a'
);
const ddColors = RUNS.map(r =>
  r.status === 'keep' ? '#ff9800' :
  r.status === 'crash' ? '#b71c1c' : '#3a3a3a'
);
const wrColors = RUNS.map(r =>
  r.status === 'keep' ? '#66bb6a' :
  r.status === 'crash' ? '#b71c1c' : '#3a3a3a'
);

let selectedIndex = null;
const hideNeg = document.getElementById('hide-neg');

function compressSharpe(v) {{
  return v >= 0 ? v : -Math.pow(Math.abs(v), 0.5);
}}

function getBarData() {{
  return RUNS.map(r => (!hideNeg.checked || r.mean_sharpe >= 0) ? compressSharpe(r.mean_sharpe) : null);
}}

function getLineData() {{
  return RUNS.map(r => (r.status === 'keep' && (!hideNeg.checked || r.mean_sharpe >= 0)) ? compressSharpe(r.mean_sharpe) : null);
}}

function getDDBarData() {{
  return RUNS.map(r => r.mean_max_dd);
}}

// Zero reference line plugin
Chart.register({{
  id: 'zeroline',
  afterDraw(chart) {{
    const y0 = chart.scales.y.getPixelForValue(0);
    if (y0 < chart.chartArea.top || y0 > chart.chartArea.bottom) return;
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

// Shared click handler
function handleBarClick(chartInstance, elements) {{
  if (!elements.length) return;
  const idx = elements[0].index;
  if (idx === selectedIndex) {{
    selectedIndex = null;
    selectedRun = null;
    document.getElementById('detail-panel').style.display = 'none';
  }} else {{
    selectedIndex = idx;
    selectedRun = RUNS[idx];
    renderDetail(selectedRun);
  }}
}}

// --- Sharpe chart ---
const sharpeCtx = document.getElementById('chart').getContext('2d');
const sharpeChart = new Chart(sharpeCtx, {{
  data: {{
    labels,
    datasets: [
      {{
        type: 'bar',
        label: 'mean_sharpe',
        data: getBarData(),
        backgroundColor: sharpeColors,
        borderWidth: 0,
        borderRadius: 2,
      }},
      {{
        type: 'line',
        label: 'keep frontier',
        data: getLineData(),
        borderColor: 'rgba(79,195,247,0.4)',
        borderWidth: 1.5,
        pointRadius: 0,
        fill: false,
        spanGaps: true,
        tension: 0,
      }}
    ]
  }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    onClick: (e, elements) => handleBarClick(sharpeChart, elements),
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
        ticks: {{
          color: '#555',
          font: {{ size: 10 }},
          callback: function(value) {{
            if (value >= 0) return value.toFixed(2);
            return (-Math.pow(Math.abs(value), 2)).toFixed(1);
          }}
        }},
        border: {{ dash: [2, 2] }}
      }}
    }}
  }}
}});

// --- Drawdown chart ---
const ddCtx = document.getElementById('dd-chart').getContext('2d');
const ddChart = new Chart(ddCtx, {{
  type: 'bar',
  data: {{
    labels,
    datasets: [{{
      label: 'mean_max_dd',
      data: getDDBarData(),
      backgroundColor: ddColors,
      borderWidth: 0,
      borderRadius: 2,
    }}]
  }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    onClick: (e, elements) => handleBarClick(ddChart, elements),
    plugins: {{
      legend: {{ display: false }},
      tooltip: {{
        callbacks: {{
          title: (items) => labels[items[0].dataIndex],
          label: (item) => {{
            const r = RUNS[item.dataIndex];
            const desc = r.description.length > 60
              ? r.description.slice(0, 57) + '...'
              : r.description;
            return ['max dd: ' + r.mean_max_dd.toFixed(2) + '%', desc];
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
        ticks: {{ color: '#555', font: {{ size: 10 }}, callback: v => v.toFixed(1) + '%' }},
        border: {{ dash: [2, 2] }}
      }}
    }}
  }}
}});

hideNeg.addEventListener('change', () => {{
  sharpeChart.data.datasets[0].data = getBarData();
  sharpeChart.data.datasets[1].data = getLineData();
  sharpeChart.update();
}});

// --- Win rate chart ---
const wrCtx = document.getElementById('wr-chart').getContext('2d');
const wrChart = new Chart(wrCtx, {{
  type: 'bar',
  data: {{
    labels,
    datasets: [{{
      label: 'mean_win_rate',
      data: RUNS.map(r => r.mean_win_rate),
      backgroundColor: wrColors,
      borderWidth: 0,
      borderRadius: 2,
    }}]
  }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    onClick: (e, elements) => handleBarClick(wrChart, elements),
    plugins: {{
      legend: {{ display: false }},
      tooltip: {{
        callbacks: {{
          title: (items) => labels[items[0].dataIndex],
          label: (item) => {{
            const r = RUNS[item.dataIndex];
            const wr = r.mean_win_rate !== null ? (r.mean_win_rate * 100).toFixed(1) + '%' : '—';
            const desc = r.description.length > 60 ? r.description.slice(0, 57) + '...' : r.description;
            return ['win rate: ' + wr, desc];
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
      x: {{ grid: {{ display: false }}, ticks: {{ color: '#444', maxRotation: 60, font: {{ size: 9 }} }} }},
      y: {{
        grid: {{ color: '#1a1a1a' }},
        ticks: {{ color: '#555', font: {{ size: 10 }}, callback: v => (v * 100).toFixed(0) + '%' }},
        border: {{ dash: [2, 2] }},
        suggestedMin: 0, suggestedMax: 1
      }}
    }}
  }}
}});

// --- Metric tab switching ---
document.querySelectorAll('.metric-tab').forEach(tab => {{
  tab.addEventListener('click', () => {{
    document.querySelectorAll('.metric-tab').forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
    activeMetric = tab.dataset.metric;
    if (selectedRun) renderSymbolBars(selectedRun);
  }});
}});

function renderSymbolBars(run) {{
  const symbolsList = document.getElementById('symbols-list');
  symbolsList.innerHTML = '';

  if (!run.symbols || Object.keys(run.symbols).length === 0) return;

  const metricKey = activeMetric === 'sharpe' ? 'sharpe_ratio' :
                    activeMetric === 'dd' ? 'max_drawdown_pct' : 'total_return_pct';

  const entries = Object.entries(run.symbols)
    .map(([sym, d]) => [sym, d[metricKey] ?? 0])
    .sort((a, b) => b[1] - a[1]);

  const maxAbs = Math.max(...entries.map(([, v]) => Math.abs(v)), 0.001);
  const cssClass = activeMetric === 'dd' ? 'warn' : '';

  entries.forEach(([sym, val]) => {{
    const pct = Math.abs(val) / maxAbs * 100;
    const isPos = val >= 0;
    const cls = cssClass || (isPos ? 'pos' : 'neg');
    const row = document.createElement('div');
    row.className = 'symbol-row';
    row.innerHTML = `
      <span class="symbol-name">${{sym}}</span>
      <div class="symbol-bar-bg">
        <div class="symbol-bar-fill ${{cls}}" style="width:${{pct.toFixed(1)}}%"></div>
      </div>
      <span class="symbol-val ${{cls}}">${{val.toFixed(2)}}</span>
    `;
    symbolsList.appendChild(row);
  }});
}}

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
  ddEl.textContent = run.mean_max_dd.toFixed(2) + '%';
  ddEl.className = 'metric-val warn';

  const retEl = document.getElementById('m-return');
  if (run.mean_total_return !== null && run.mean_total_return !== undefined) {{
    retEl.textContent = run.mean_total_return.toFixed(2) + '%';
    retEl.className = 'metric-val ' + (run.mean_total_return >= 0 ? 'pos' : 'neg');
  }} else {{
    retEl.textContent = '—';
    retEl.className = 'metric-val neutral';
  }}

  const symbolsSection = document.getElementById('symbols-section');
  if (run.symbols && Object.keys(run.symbols).length > 0) {{
    symbolsSection.style.display = 'block';
    renderSymbolBars(run);
  }} else {{
    symbolsSection.style.display = 'none';
  }}
}}
</script>
</body>
</html>"""


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

    # When TSV lacks tags, assign from JSON filenames by position
    has_tags = any(run['tag'] for run in runs)
    if not has_tags and results_dir.exists():
        tags = []
        for f in results_dir.glob('*.json'):
            try:
                with open(f, encoding='utf-8') as fh:
                    agg = json.load(fh).get('aggregate', {})
                if agg.get('mean_sharpe', 0) == -999.0:
                    continue
            except Exception:
                continue
            tags.append(f.stem)
        def sort_key(t):
            parts = t.rsplit('_', 1)
            if len(parts) == 2 and parts[1].isdigit():
                return (0, int(parts[1]))
            return (1, t)
        tags.sort(key=sort_key)
        for i, run in enumerate(runs):
            if i < len(tags):
                run['tag'] = tags[i]

    for run in runs:
        sym_data = load_symbol_data(run['tag'], str(results_dir))
        if sym_data:
            run['mean_total_return'] = sym_data['mean_total_return']
            run['symbols'] = sym_data['symbols']
            wr_vals = [s['win_rate'] for s in sym_data['symbols'].values()
                       if s.get('win_rate') is not None]
            run['mean_win_rate'] = sum(wr_vals) / len(wr_vals) if wr_vals else None
        else:
            run['mean_total_return'] = None
            run['symbols'] = None
            run['mean_win_rate'] = None

    html = generate_html(runs)
    output_path.write_text(html, encoding='utf-8')
    print(f"Dashboard written to {output_path}")
    webbrowser.open(output_path.as_uri())


if __name__ == '__main__':
    main()
