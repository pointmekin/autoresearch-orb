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
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            runs.append(
                {
                    "tag": row.get("tag", ""),
                    "commit": row["commit"],
                    "mean_sharpe": float(row["mean_sharpe"]),
                    "mean_max_dd": float(row["mean_max_dd"]),
                    "status": row["status"],
                    "description": row["description"],
                }
            )
    return runs


def load_symbol_data(tag, results_dir="results"):
    """Load per-symbol data from results/<tag>.json.

    Returns None if the file does not exist or tag is empty.
    Returns a dict with keys: mean_total_return (float or None), symbols (dict).
    """
    if not tag:
        return None
    path = pathlib.Path(results_dir) / f"{tag}.json"
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return {
        "mean_total_return": data.get("aggregate", {}).get("mean_total_return"),
        "symbols": data.get("results", {}),
    }


def generate_html(runs):
    """Generate a self-contained HTML dashboard string from a list of run dicts."""
    runs_json = json.dumps(runs, indent=2)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ORB Autoresearch — Results</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html {{ overflow-x: hidden; }}
  html, body {{ height: 100%; overflow-y: hidden; }}
  body {{ background: #0d0d0d; color: #ccc; font-family: 'Courier New', monospace;
          padding: 12px; display: flex; flex-direction: column; gap: 10px; }}
  #header {{ display: flex; justify-content: space-between; align-items: center;
             background: #1a1a2e; padding: 10px 14px; border-radius: 6px;
             flex-shrink: 0; }}
  #header .title {{ color: #e0e0ff; font-size: 12px; font-weight: bold; letter-spacing: 1px; }}
  #header .meta {{ color: #555; font-size: 10px; }}
  #layout {{ flex: 1; display: grid; grid-template-columns: 1.5fr 1fr; gap: 10px; min-height: 0; }}
  #chart-col {{ display: flex; flex-direction: column; gap: 8px; min-height: 0; }}
  #chart-panel {{ background: #111; border: 1px solid #222; border-radius: 6px;
                  padding: 12px; flex: 1; display: flex; flex-direction: column; min-height: 0; }}
  #chart-toolbar {{ display: flex; justify-content: space-between; align-items: center;
                    margin-bottom: 10px; flex-shrink: 0; }}
  .chart-tabs {{ display: flex; gap: 2px; }}
  .chart-tab {{ padding: 3px 10px; border-radius: 3px; font-size: 9px;
                text-transform: uppercase; letter-spacing: 0.5px; cursor: pointer;
                background: #0d0d0d; color: #444; border: none; font-family: inherit;
                transition: all 0.15s; }}
  .chart-tab:hover {{ color: #888; }}
  .chart-tab.active {{ background: #1a1a2e; color: #e0e0ff; }}
  #hide-neg-label {{ display: flex; align-items: center; gap: 5px; cursor: pointer;
                     font-size: 9px; color: #555; text-transform: uppercase;
                     letter-spacing: 0.5px; }}
  #hide-neg {{ cursor: pointer; accent-color: #4fc3f7; }}
  .chart-container {{ position: relative; flex: 1; min-height: 0;
                      overflow-x: auto; overflow-y: hidden; }}
  #chart-scroll {{ position: relative; }}
  #chart-footer {{ display: flex; justify-content: space-between; align-items: center;
                   margin-top: 8px; flex-shrink: 0; }}
  .legend {{ display: flex; gap: 14px; }}
  .legend-item {{ display: flex; align-items: center; gap: 5px; font-size: 9px; color: #444; }}
  .legend-dot {{ width: 9px; height: 9px; border-radius: 2px; }}
  #right-col {{ display: flex; flex-direction: column; min-height: 0; overflow-y: auto; }}
  #detail-panel {{ background: #111; border: 1px solid #222; border-radius: 6px;
                   padding: 14px; flex: 1; display: flex; flex-direction: column; gap: 10px; }}
  #nav-controls {{ display: flex; align-items: center; gap: 6px; flex-shrink: 0; }}
  #nav-prev, #nav-next {{ background: #0d0d0d; border: 1px solid #2a2a2a; color: #555;
                           font-family: inherit; font-size: 11px; padding: 3px 8px;
                           border-radius: 3px; cursor: pointer; line-height: 1;
                           transition: all 0.15s; }}
  #nav-prev:hover, #nav-next:hover {{ color: #aaa; border-color: #444; }}
  #nav-prev:disabled, #nav-next:disabled {{ opacity: 0.2; cursor: default; }}
  #nav-pos {{ font-size: 10px; color: #444; flex: 1; text-align: center; }}
  #detail-placeholder {{ color: #2a2a2a; text-align: center; padding: 40px 0;
                          font-size: 11px; text-transform: uppercase; letter-spacing: 1px; }}
  #detail-content {{ display: none; flex: 1; overflow-y: auto; }}
  #best-so-far {{ font-size: 9px; color: #444; text-transform: uppercase; letter-spacing: 0.5px;
                  padding: 5px 8px; background: #0d0d0d; border-radius: 3px;
                  margin-bottom: 10px; display: flex; gap: 6px; align-items: center; }}
  #best-so-far .bsf-val {{ color: #4fc3f7; }}
  #detail-header {{ display: flex; align-items: center; gap: 8px; margin-bottom: 6px; flex-wrap: wrap; }}
  #detail-tag {{ font-size: 11px; color: #888; }}
  #detail-commit {{ font-size: 10px; color: #444; }}
  .badge {{ padding: 2px 7px; border-radius: 3px; font-size: 9px;
            text-transform: uppercase; letter-spacing: 0.5px; }}
  .badge-keep {{ background: #1a3a1a; color: #66bb6a; }}
  .badge-discard {{ background: #2a2a2a; color: #666; }}
  .badge-crash {{ background: #3a1a1a; color: #ef5350; }}
  #detail-desc {{ font-size: 11px; color: #aaa; margin-bottom: 12px;
                  line-height: 1.5; border-left: 2px solid #222; padding-left: 8px; }}
  .metrics-row {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; margin-bottom: 14px; }}
  .metric-box {{ background: #0d0d0d; border-radius: 4px; padding: 8px; text-align: center; }}
  .metric-val {{ font-size: 16px; }}
  .metric-val.pos {{ color: #4fc3f7; }}
  .metric-val.neg {{ color: #ef5350; }}
  .metric-val.neutral {{ color: #888; }}
  .metric-val.warn {{ color: #ff9800; }}
  .metric-label {{ font-size: 8px; color: #444; text-transform: uppercase;
                   letter-spacing: 0.5px; margin-top: 3px; }}
  #symbols-section {{ display: none; }}
  .symbols-header {{ display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }}
  .symbol-tabs {{ display: flex; gap: 2px; }}
  .symbol-tab {{ padding: 3px 10px; border-radius: 3px; font-size: 9px;
                 text-transform: uppercase; letter-spacing: 0.5px; cursor: pointer;
                 background: #0d0d0d; color: #444; border: none; font-family: inherit;
                 transition: all 0.15s; }}
  .symbol-tab:hover {{ color: #888; }}
  .symbol-tab.active {{ background: #1a1a2e; color: #e0e0ff; }}
  .symbol-row {{ display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }}
  .symbol-name {{ font-size: 10px; color: #555; width: 72px; flex-shrink: 0; }}
  .symbol-bar-bg {{ flex: 1; height: 10px; background: #0d0d0d; border-radius: 2px; overflow: hidden; }}
  .symbol-bar-fill {{ height: 100%; border-radius: 2px; transition: width 0.2s; }}
  .symbol-bar-fill.pos {{ background: #4fc3f7; }}
  .symbol-bar-fill.neg {{ background: #ef5350; }}
  .symbol-bar-fill.warn {{ background: #ff9800; }}
  .symbol-val {{ font-size: 10px; width: 50px; text-align: right; }}
  .symbol-val.pos {{ color: #4fc3f7; }}
  .symbol-val.neg {{ color: #ef5350; }}
  .symbol-val.warn {{ color: #ff9800; }}

  @media (max-width: 768px) {{
    html, body {{ height: auto; overflow-y: auto; }}
    body {{ padding: 8px; gap: 8px; }}
    #header {{ flex-direction: column; align-items: flex-start; gap: 3px; padding: 10px 12px; }}
    #header .title {{ font-size: 11px; }}
    #header .meta {{ font-size: 10px; }}
    #layout {{ grid-template-columns: 1fr; flex: none; height: auto; min-height: 0; }}
    #chart-col {{ gap: 0; }}
    #chart-panel {{ flex: none; height: 52vw; min-height: 240px; border-radius: 6px 6px 0 0;
                    border-bottom: none; padding: 10px 10px 8px; }}
    #chart-toolbar {{ margin-bottom: 8px; }}
    .chart-tab {{ padding: 5px 10px; font-size: 9px; }}
    .chart-container {{ min-height: 0; }}
    #chart-footer {{ margin-top: 6px; }}
    #right-col {{ overflow-y: visible; border-radius: 0 0 6px 6px; }}
    #detail-panel {{ flex: none; border-radius: 0 0 6px 6px; border-top: none;
                     border-color: #222; padding: 12px; gap: 8px; }}
    #detail-content {{ overflow-y: visible; flex: none; }}
    #nav-prev, #nav-next {{ padding: 8px 16px; font-size: 14px; min-width: 44px;
                             min-height: 36px; }}
    #nav-pos {{ font-size: 11px; }}
    #detail-desc {{ font-size: 11px; }}
    .metric-val {{ font-size: 15px; }}
    .metrics-row {{ gap: 5px; margin-bottom: 12px; }}
    .metric-box {{ padding: 8px 4px; }}
    .symbol-name {{ width: 60px; }}
    .symbol-val {{ width: 46px; }}
    .symbol-tab, .chart-tab {{ padding: 5px 10px; }}
    #best-so-far {{ flex-wrap: wrap; font-size: 9px; }}
    #detail-placeholder {{ padding: 28px 0; }}
  }}
</style>
</head>
<body>

<div id="header">
  <span class="title">ORB AUTORESEARCH — RESULTS</span>
  <span class="meta" id="header-meta"></span>
</div>

<div id="layout">
  <div id="chart-col">
    <div id="chart-panel">
      <div id="chart-toolbar">
        <div class="chart-tabs">
          <button class="chart-tab active" data-chart="sharpe">sharpe</button>
          <button class="chart-tab" data-chart="dd">drawdown</button>
          <button class="chart-tab" data-chart="winrate">win rate</button>
        </div>
        <label id="hide-neg-label">
          <input type="checkbox" id="hide-neg" checked> hide negative
        </label>
      </div>
      <div class="chart-container"><div id="chart-scroll"><canvas id="main-chart"></canvas></div></div>
      <div id="chart-footer">
        <div class="legend">
          <div class="legend-item"><div class="legend-dot" id="legend-keep-dot"></div>keep</div>
          <div class="legend-item"><div class="legend-dot" style="background:#3a3a3a"></div>discard</div>
          <div class="legend-item"><div class="legend-dot" style="background:#b71c1c"></div>crash</div>
        </div>
      </div>
    </div>
  </div>

  <div id="right-col">
    <div id="detail-panel">
      <div id="nav-controls">
        <button id="nav-prev" disabled>&#8592;</button>
        <span id="nav-pos">— / —</span>
        <button id="nav-next" disabled>&#8594;</button>
      </div>
      <div id="detail-placeholder">click a bar or use arrow keys</div>
      <div id="detail-content">
        <div id="best-so-far">
          best so far: <span id="bsf-tag" class="bsf-val">—</span>
          &nbsp;·&nbsp; sharpe <span id="bsf-sharpe" class="bsf-val">—</span>
        </div>
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
            <div class="symbol-tabs">
              <button class="symbol-tab active" data-metric="sharpe">sharpe</button>
              <button class="symbol-tab" data-metric="dd">drawdown</button>
              <button class="symbol-tab" data-metric="return">return</button>
            </div>
          </div>
          <div id="symbols-list"></div>
        </div>
      </div>
    </div>
  </div>
</div>

<script>
const RUNS = {runs_json};
let chartMetric = 'sharpe';
let symbolMetric = 'sharpe';
let selectedIndex = null;
let selectedRun = null;

// Header meta
const total = RUNS.length;
const best = Math.max(...RUNS.map(r => r.mean_sharpe));
const bestDD = Math.min(...RUNS.map(r => r.mean_max_dd));
document.getElementById('header-meta').textContent =
  total + ' runs · best sharpe: ' + best.toFixed(4) + ' · worst dd: ' + bestDD.toFixed(2) + '%';

const labels = RUNS.map((r, i) => r.tag || ('#' + (i + 1)));
const hideNeg = document.getElementById('hide-neg');

// Compression helpers
function compressSharpe(v) {{
  return v >= 0 ? v : -Math.pow(Math.abs(v), 0.5);
}}
function compressDD(v) {{
  return v >= 0 ? v : -Math.sqrt(Math.abs(v));
}}

// Per-metric config
const METRIC_CONFIG = {{
  sharpe: {{
    keepColor: '#4fc3f7',
    barData: () => RUNS.map(r =>
      (!hideNeg.checked || r.mean_sharpe >= 0) ? compressSharpe(r.mean_sharpe) : null),
    lineData: () => RUNS.map(r =>
      (r.status === 'keep' && (!hideNeg.checked || r.mean_sharpe >= 0))
        ? compressSharpe(r.mean_sharpe) : null),
    yTick: v => v >= 0 ? v.toFixed(2) : (-Math.pow(Math.abs(v), 2)).toFixed(1),
    tooltip: (r) => ['sharpe: ' + r.mean_sharpe.toFixed(4), truncDesc(r.description)],
    yOpts: {{}},
  }},
  dd: {{
    keepColor: '#ff9800',
    barData: () => RUNS.map(r => compressDD(r.mean_max_dd)),
    lineData: () => RUNS.map(() => null),
    yTick: v => v >= 0 ? v.toFixed(1) + '%' : (-Math.pow(Math.abs(v), 2)).toFixed(1) + '%',
    tooltip: (r) => ['max dd: ' + r.mean_max_dd.toFixed(2) + '%', truncDesc(r.description)],
    yOpts: {{}},
  }},
  winrate: {{
    keepColor: '#66bb6a',
    barData: () => RUNS.map(r => r.mean_win_rate),
    lineData: () => RUNS.map(() => null),
    yTick: v => (v * 100).toFixed(0) + '%',
    tooltip: (r) => [
      'win rate: ' + (r.mean_win_rate !== null ? (r.mean_win_rate * 100).toFixed(1) + '%' : '—'),
      truncDesc(r.description),
    ],
    yOpts: {{ suggestedMin: 0, suggestedMax: 1 }},
  }},
}};

function truncDesc(d) {{
  return d.length > 60 ? d.slice(0, 57) + '...' : d;
}}

function getColors(metric) {{
  const keep = METRIC_CONFIG[metric].keepColor;
  return RUNS.map(r =>
    r.status === 'keep' ? keep :
    r.status === 'crash' ? '#b71c1c' : '#3a3a3a'
  );
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

// Precompute cumulative best keep run by index
const cumulativeBest = RUNS.map((_, i) => {{
  let best = null;
  for (let j = 0; j <= i; j++) {{
    if (RUNS[j].status === 'keep' && (best === null || RUNS[j].mean_sharpe > best.sharpe)) {{
      best = {{ idx: j, tag: labels[j], sharpe: RUNS[j].mean_sharpe }};
    }}
  }}
  return best;
}});

function navigateTo(idx) {{
  if (idx < 0 || idx >= RUNS.length) return;
  selectedIndex = idx;
  selectedRun = RUNS[idx];
  renderDetail(selectedRun);
  // Highlight bar in chart
  mainChart.setActiveElements([{{ datasetIndex: 0, index: idx }}]);
  mainChart.update('none');
}}

function clearSelection() {{
  selectedIndex = null;
  selectedRun = null;
  mainChart.setActiveElements([]);
  mainChart.update('none');
  document.getElementById('detail-placeholder').style.display = 'block';
  document.getElementById('detail-content').style.display = 'none';
  document.getElementById('nav-pos').textContent = '— / —';
  document.getElementById('nav-prev').disabled = true;
  document.getElementById('nav-next').disabled = true;
}}

document.getElementById('nav-prev').addEventListener('click', () => {{
  if (selectedIndex !== null) navigateTo(selectedIndex - 1);
}});
document.getElementById('nav-next').addEventListener('click', () => {{
  if (selectedIndex !== null) navigateTo(selectedIndex + 1);
  else navigateTo(0);
}});

document.addEventListener('keydown', e => {{
  if (e.key === 'ArrowLeft') {{ e.preventDefault(); selectedIndex !== null ? navigateTo(selectedIndex - 1) : navigateTo(0); }}
  if (e.key === 'ArrowRight') {{ e.preventDefault(); selectedIndex !== null ? navigateTo(selectedIndex + 1) : navigateTo(0); }}
  if (e.key === 'Escape') clearSelection();
}});

// Touch swipe to navigate
let touchStartX = 0;
document.addEventListener('touchstart', e => {{ touchStartX = e.changedTouches[0].clientX; }}, {{ passive: true }});
document.addEventListener('touchend', e => {{
  const dx = e.changedTouches[0].clientX - touchStartX;
  if (Math.abs(dx) < 40) return;
  if (dx < 0) {{ selectedIndex !== null ? navigateTo(selectedIndex + 1) : navigateTo(0); }}
  else {{ selectedIndex !== null ? navigateTo(selectedIndex - 1) : navigateTo(0); }}
}}, {{ passive: true }});

// Single chart instance
const cfg = METRIC_CONFIG.sharpe;
const mainCtx = document.getElementById('main-chart').getContext('2d');
const mainChart = new Chart(mainCtx, {{
  data: {{
    labels,
    datasets: [
      {{
        type: 'bar',
        label: 'main',
        data: cfg.barData(),
        backgroundColor: getColors('sharpe'),
        borderWidth: 0,
        borderRadius: 2,
      }},
      {{
        type: 'line',
        label: 'keep frontier',
        data: cfg.lineData(),
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
    responsive: false,
    maintainAspectRatio: false,
    onClick: (e, elements) => {{
      if (!elements.length) return;
      const idx = elements[0].index;
      if (idx === selectedIndex) {{
        clearSelection();
      }} else {{
        navigateTo(idx);
      }}
    }},
    plugins: {{
      legend: {{ display: false }},
      tooltip: {{
        callbacks: {{
          title: (items) => labels[items[0].dataIndex],
          label: (item) => {{
            if (item.datasetIndex !== 0) return null;
            return METRIC_CONFIG[chartMetric].tooltip(RUNS[item.dataIndex]);
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
        ticks: {{ color: '#555', font: {{ size: 10 }}, callback: cfg.yTick }},
        border: {{ dash: [2, 2] }}
      }}
    }}
  }}
}});

function setChartMetric(metric) {{
  chartMetric = metric;
  const mcfg = METRIC_CONFIG[metric];
  mainChart.data.datasets[0].data = mcfg.barData();
  mainChart.data.datasets[0].backgroundColor = getColors(metric);
  mainChart.data.datasets[1].data = mcfg.lineData();
  mainChart.options.scales.y.ticks.callback = mcfg.yTick;
  // Reset then apply suggestedMin/Max
  delete mainChart.options.scales.y.suggestedMin;
  delete mainChart.options.scales.y.suggestedMax;
  Object.assign(mainChart.options.scales.y, mcfg.yOpts);
  mainChart.update();
  document.getElementById('legend-keep-dot').style.background = mcfg.keepColor;
  document.getElementById('hide-neg-label').style.display =
    metric === 'sharpe' ? 'flex' : 'none';
  // Update frontier line color to match metric
  const lineColor = metric === 'sharpe' ? 'rgba(79,195,247,0.4)' :
                    metric === 'dd' ? 'rgba(255,152,0,0.4)' : 'rgba(102,187,106,0.4)';
  mainChart.data.datasets[1].borderColor = lineColor;
}}

// Chart tab switching
document.querySelectorAll('.chart-tab').forEach(tab => {{
  tab.addEventListener('click', () => {{
    document.querySelectorAll('.chart-tab').forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
    setChartMetric(tab.dataset.chart);
  }});
}});

hideNeg.addEventListener('change', () => setChartMetric(chartMetric));

// Size chart explicitly so it fills the panel height and scrolls horizontally
const chartContainer = document.querySelector('.chart-container');
const chartScroll = document.getElementById('chart-scroll');
const BAR_MIN_PX = 7;

function resizeChart() {{
  const h = chartContainer.clientHeight;
  const w = Math.max(RUNS.length * BAR_MIN_PX, chartContainer.clientWidth);
  chartScroll.style.width = w + 'px';
  mainChart.resize(w, h);
}}

window.addEventListener('resize', resizeChart);
resizeChart();

// Initialize legend dot
document.getElementById('legend-keep-dot').style.background = METRIC_CONFIG.sharpe.keepColor;

// Symbol tab switching
document.querySelectorAll('.symbol-tab').forEach(tab => {{
  tab.addEventListener('click', () => {{
    document.querySelectorAll('.symbol-tab').forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
    symbolMetric = tab.dataset.metric;
    if (selectedRun) renderSymbolBars(selectedRun);
  }});
}});

function renderSymbolBars(run) {{
  const symbolsList = document.getElementById('symbols-list');
  symbolsList.innerHTML = '';
  if (!run.symbols || Object.keys(run.symbols).length === 0) return;

  const metricKey = symbolMetric === 'sharpe' ? 'sharpe_ratio' :
                    symbolMetric === 'dd' ? 'max_drawdown_pct' : 'total_return_pct';

  const entries = Object.entries(run.symbols)
    .map(([sym, d]) => [sym, d[metricKey] ?? 0])
    .sort((a, b) => b[1] - a[1]);

  const maxAbs = Math.max(...entries.map(([, v]) => Math.abs(v)), 0.001);
  const cssClass = symbolMetric === 'dd' ? 'warn' : '';

  entries.forEach(([sym, val]) => {{
    const pct = Math.abs(val) / maxAbs * 100;
    const cls = cssClass || (val >= 0 ? 'pos' : 'neg');
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
  document.getElementById('detail-placeholder').style.display = 'none';
  document.getElementById('detail-content').style.display = 'block';

  // Nav controls
  const idx = selectedIndex;
  document.getElementById('nav-pos').textContent = (idx + 1) + ' / ' + RUNS.length;
  document.getElementById('nav-prev').disabled = idx <= 0;
  document.getElementById('nav-next').disabled = idx >= RUNS.length - 1;

  // Cumulative best
  const best = cumulativeBest[idx];
  if (best) {{
    document.getElementById('bsf-tag').textContent = best.tag;
    document.getElementById('bsf-sharpe').textContent = best.sharpe.toFixed(4);
  }} else {{
    document.getElementById('bsf-tag').textContent = '—';
    document.getElementById('bsf-sharpe').textContent = '—';
  }}

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
    tsv_path = script_dir / "results.tsv"
    results_dir = script_dir / "results"
    output_path = script_dir / "dashboard.html"

    if not tsv_path.exists():
        print(f"Error: {tsv_path} not found. Run some experiments first.")
        return

    runs = parse_tsv(str(tsv_path))

    # When TSV lacks tags, assign from JSON filenames by position
    has_tags = any(run["tag"] for run in runs)
    if not has_tags and results_dir.exists():
        tags = []
        for f in results_dir.glob("*.json"):
            try:
                with open(f, encoding="utf-8") as fh:
                    agg = json.load(fh).get("aggregate", {})
                if agg.get("mean_sharpe", 0) == -999.0:
                    continue
            except Exception:
                continue
            tags.append(f.stem)

        def sort_key(t):
            parts = t.rsplit("_", 1)
            if len(parts) == 2 and parts[1].isdigit():
                return (0, int(parts[1]))
            return (1, t)

        tags.sort(key=sort_key)
        for i, run in enumerate(runs):
            if i < len(tags):
                run["tag"] = tags[i]

    for run in runs:
        sym_data = load_symbol_data(run["tag"], str(results_dir))
        if sym_data:
            run["mean_total_return"] = sym_data["mean_total_return"]
            run["symbols"] = sym_data["symbols"]
            wr_vals = [
                s["win_rate"]
                for s in sym_data["symbols"].values()
                if s.get("win_rate") is not None
            ]
            run["mean_win_rate"] = sum(wr_vals) / len(wr_vals) if wr_vals else None
        else:
            run["mean_total_return"] = None
            run["symbols"] = None
            run["mean_win_rate"] = None

    html = generate_html(runs)
    output_path.write_text(html, encoding="utf-8")
    print(f"Dashboard written to {output_path}")
    webbrowser.open(output_path.as_uri())


if __name__ == "__main__":
    main()
