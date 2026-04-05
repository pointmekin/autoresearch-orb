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
        spanGaps: true,
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


if __name__ == '__main__':
    main()
