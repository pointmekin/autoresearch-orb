import csv
import json
import pathlib
import webbrowser


def parse_tsv(path):
    """Read results.tsv and return a list of run dicts."""
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
    """Load per-symbol data from results/<tag>.json."""
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
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
<title>ORB Autoresearch</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  :root {{
    --bg: #07070a; --surface: #0f0f14; --hi: #17171f;
    --border: #1c1c28; --text: #b0b0be; --muted: #484858; --dim: #28283a;
    --accent: #4fc3f7; --dd: #ff9800; --wr: #66bb6a;
    --font: 'IBM Plex Mono', 'Courier New', monospace;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html {{ overflow-x: hidden; }}
  html, body {{ height: 100%; overflow-y: hidden; }}
  body {{ background: var(--bg); color: var(--text); font-family: var(--font);
          padding: 10px; display: flex; flex-direction: column; gap: 8px; }}

  /* Header */
  #header {{
    display: flex; justify-content: space-between; align-items: center;
    background: var(--hi); padding: 10px 14px; border-radius: 6px;
    border: 1px solid var(--border); flex-shrink: 0;
  }}
  .title {{ color: #e0e0f0; font-size: 11px; font-weight: 600; letter-spacing: 1.5px; }}
  .meta {{ color: var(--muted); font-size: 10px; }}

  /* Grid layout */
  #layout {{ flex: 1; display: grid; grid-template-columns: 1.5fr 1fr; gap: 8px; min-height: 0; }}

  /* Chart panel */
  #chart-panel {{
    background: var(--surface); border: 1px solid var(--border); border-radius: 6px;
    padding: 10px; display: flex; flex-direction: column; min-height: 0; overflow: hidden;
  }}
  #chart-toolbar {{
    display: flex; justify-content: space-between; align-items: center;
    margin-bottom: 8px; flex-shrink: 0;
  }}
  .tabs {{ display: flex; gap: 2px; }}
  .tab {{
    padding: 4px 10px; border-radius: 3px; font-size: 9px;
    text-transform: uppercase; letter-spacing: 0.5px; cursor: pointer;
    background: var(--bg); color: var(--muted); border: none; font-family: var(--font);
    transition: all 0.15s;
  }}
  .tab:hover {{ color: var(--text); }}
  .tab.active {{ background: var(--hi); color: #e0e0f0; }}
  #hide-neg-label {{
    display: flex; align-items: center; gap: 5px; cursor: pointer;
    font-size: 9px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.5px;
  }}
  #hide-neg {{ cursor: pointer; accent-color: var(--accent); }}

  /* Chart scroll area */
  .chart-wrap {{
    flex: 1; min-height: 0; position: relative;
    overflow-x: auto; overflow-y: hidden;
  }}
  .chart-wrap::-webkit-scrollbar {{ height: 3px; }}
  .chart-wrap::-webkit-scrollbar-track {{ background: var(--bg); }}
  .chart-wrap::-webkit-scrollbar-thumb {{ background: var(--border); border-radius: 2px; }}
  #chart-inner {{ height: 100%; min-width: 100%; }}

  /* Legend */
  #chart-footer {{ display: flex; margin-top: 6px; flex-shrink: 0; }}
  .legend {{ display: flex; gap: 14px; }}
  .legend-item {{ display: flex; align-items: center; gap: 5px; font-size: 9px; color: var(--muted); }}
  .legend-dot {{ width: 8px; height: 8px; border-radius: 2px; }}

  /* Right column */
  #right-col {{
    display: flex; flex-direction: column; min-height: 0; overflow-y: auto;
  }}
  #right-col::-webkit-scrollbar {{ width: 3px; }}
  #right-col::-webkit-scrollbar-track {{ background: transparent; }}
  #right-col::-webkit-scrollbar-thumb {{ background: var(--border); border-radius: 2px; }}
  #detail-panel {{
    background: var(--surface); border: 1px solid var(--border); border-radius: 6px;
    padding: 12px; flex: 1; display: flex; flex-direction: column; gap: 8px;
  }}

  /* Nav */
  #nav {{ display: flex; align-items: center; gap: 6px; flex-shrink: 0; }}
  #nav button {{
    background: var(--bg); border: 1px solid var(--border); color: var(--muted);
    font-family: var(--font); font-size: 12px; padding: 4px 10px;
    border-radius: 3px; cursor: pointer; line-height: 1; transition: all 0.15s;
  }}
  #nav button:hover {{ color: var(--text); border-color: var(--muted); }}
  #nav button:disabled {{ opacity: 0.2; cursor: default; }}
  #nav-pos {{ font-size: 10px; color: var(--muted); flex: 1; text-align: center; }}

  /* Placeholder */
  #placeholder {{
    color: var(--dim); text-align: center; padding: 40px 0;
    font-size: 10px; text-transform: uppercase; letter-spacing: 1px;
  }}
  #detail {{ display: none; flex: 1; overflow-y: auto; }}

  /* Best-so-far strip */
  #bsf {{
    font-size: 9px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.5px;
    padding: 5px 8px; background: var(--bg); border-radius: 3px;
    margin-bottom: 8px; display: flex; gap: 6px; align-items: center; flex-wrap: wrap;
  }}
  .bsf-v {{ color: var(--accent); }}

  /* Detail header */
  #d-head {{ display: flex; align-items: center; gap: 8px; margin-bottom: 6px; flex-wrap: wrap; }}
  #d-tag {{ font-size: 11px; color: var(--muted); }}
  #d-commit {{ font-size: 10px; color: var(--dim); }}
  .badge {{ padding: 2px 7px; border-radius: 3px; font-size: 9px; text-transform: uppercase; letter-spacing: 0.5px; }}
  .badge-keep {{ background: #0f2a0f; color: #66bb6a; }}
  .badge-discard {{ background: #1a1a22; color: #666; }}
  .badge-crash {{ background: #2a0f0f; color: #ef5350; }}
  #d-desc {{
    font-size: 11px; color: #8888a0; margin-bottom: 10px;
    line-height: 1.5; border-left: 2px solid var(--border); padding-left: 8px;
  }}

  /* Metrics */
  .metrics {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 5px; margin-bottom: 12px; }}
  .m-box {{ background: var(--bg); border-radius: 4px; padding: 8px; text-align: center; }}
  .m-val {{ font-size: 15px; font-weight: 500; }}
  .m-val.pos {{ color: var(--accent); }}
  .m-val.neg {{ color: #ef5350; }}
  .m-val.neutral {{ color: var(--muted); }}
  .m-val.warn {{ color: var(--dd); }}
  .m-lbl {{ font-size: 8px; color: var(--dim); text-transform: uppercase; letter-spacing: 0.5px; margin-top: 2px; }}

  /* Symbols */
  #sym-section {{ display: none; }}
  .sym-row {{ display: flex; align-items: center; gap: 8px; margin-bottom: 3px; }}
  .sym-name {{ font-size: 10px; color: var(--muted); width: 68px; flex-shrink: 0; }}
  .sym-bg {{ flex: 1; height: 10px; background: var(--bg); border-radius: 2px; overflow: hidden; }}
  .sym-fill {{ height: 100%; border-radius: 2px; transition: width 0.2s; }}
  .sym-fill.pos {{ background: var(--accent); }}
  .sym-fill.neg {{ background: #ef5350; }}
  .sym-fill.warn {{ background: var(--dd); }}
  .sym-val {{ font-size: 10px; width: 48px; text-align: right; }}
  .sym-val.pos {{ color: var(--accent); }}
  .sym-val.neg {{ color: #ef5350; }}
  .sym-val.warn {{ color: var(--dd); }}

  /* Mobile */
  @media (max-width: 768px) {{
    html {{ overflow-x: hidden; }}
    html, body {{ height: auto; overflow-y: auto; }}
    body {{ padding: 0; gap: 0; }}
    #header {{
      border-radius: 0; border-left: none; border-right: none; border-top: none;
      padding: 10px 12px; flex-direction: column; align-items: flex-start; gap: 2px;
    }}
    .title {{ font-size: 10px; }}
    .meta {{ font-size: 9px; }}
    #layout {{ grid-template-columns: 1fr; flex: none; height: auto; min-height: 0; }}
    #chart-panel {{
      border-radius: 0; border-left: none; border-right: none;
      flex: none; height: 46vh; min-height: 230px; max-height: 360px;
      padding: 8px 8px 6px;
    }}
    .tab {{ padding: 6px 12px; font-size: 10px; }}
    #chart-footer {{ margin-top: 4px; }}
    #right-col {{ overflow-y: visible; }}
    #detail-panel {{
      border-radius: 0 0 6px 6px;
      border-top: none; border-left: none; border-right: none;
      padding: 10px; gap: 8px;
    }}
    #detail {{ overflow-y: visible; flex: none; }}
    #nav button {{ padding: 10px 20px; font-size: 16px; min-width: 48px; min-height: 44px; }}
    #nav-pos {{ font-size: 12px; }}
    .m-val {{ font-size: 14px; }}
    .metrics {{ gap: 4px; margin-bottom: 10px; }}
    .m-box {{ padding: 6px 4px; }}
    .sym-name {{ width: 56px; font-size: 11px; }}
    .sym-val {{ width: 44px; font-size: 11px; }}
    #d-desc {{ font-size: 12px; margin-bottom: 8px; }}
    #placeholder {{ padding: 24px 0; }}
  }}
</style>
</head>
<body>

<div id="header">
  <span class="title">ORB AUTORESEARCH</span>
  <span class="meta" id="header-meta"></span>
</div>

<div id="layout">
  <div id="chart-panel">
    <div id="chart-toolbar">
      <div class="tabs" id="chart-tabs">
        <button class="tab active" data-chart="sharpe">sharpe</button>
        <button class="tab" data-chart="dd">drawdown</button>
        <button class="tab" data-chart="winrate">win rate</button>
      </div>
      <label id="hide-neg-label">
        <input type="checkbox" id="hide-neg" checked> hide negative
      </label>
    </div>
    <div class="chart-wrap">
      <div id="chart-inner"><canvas id="chart"></canvas></div>
    </div>
    <div id="chart-footer">
      <div class="legend">
        <div class="legend-item"><div class="legend-dot" id="leg-keep"></div>keep</div>
        <div class="legend-item"><div class="legend-dot" style="background:#2a2a34"></div>discard</div>
        <div class="legend-item"><div class="legend-dot" style="background:#b71c1c"></div>crash</div>
      </div>
    </div>
  </div>

  <div id="right-col">
    <div id="detail-panel">
      <div id="nav">
        <button id="nav-prev" disabled>&larr;</button>
        <span id="nav-pos">&mdash; / &mdash;</span>
        <button id="nav-next" disabled>&rarr;</button>
      </div>
      <div id="placeholder">click a bar or use arrow keys</div>
      <div id="detail">
        <div id="bsf">
          best so far: <span id="bsf-tag" class="bsf-v">&mdash;</span>
          &nbsp;&middot;&nbsp; sharpe <span id="bsf-sharpe" class="bsf-v">&mdash;</span>
        </div>
        <div id="d-head">
          <span id="d-tag"></span>
          <span id="d-badge" class="badge"></span>
          <span id="d-commit"></span>
        </div>
        <div id="d-desc"></div>
        <div class="metrics">
          <div class="m-box">
            <div class="m-val" id="m-sharpe"></div>
            <div class="m-lbl">mean sharpe</div>
          </div>
          <div class="m-box">
            <div class="m-val" id="m-dd"></div>
            <div class="m-lbl">mean max dd</div>
          </div>
          <div class="m-box">
            <div class="m-val" id="m-ret"></div>
            <div class="m-lbl">mean return %</div>
          </div>
        </div>
        <div id="sym-section">
          <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">
            <div class="tabs" id="sym-tabs">
              <button class="tab active" data-metric="sharpe">sharpe</button>
              <button class="tab" data-metric="dd">drawdown</button>
              <button class="tab" data-metric="return">return</button>
            </div>
          </div>
          <div id="sym-list"></div>
        </div>
      </div>
    </div>
  </div>
</div>

<script>
const RUNS = {runs_json};
let chartMetric = 'sharpe', symMetric = 'sharpe';
let selIdx = null, selRun = null;

// Header
const best = Math.max(...RUNS.map(r => r.mean_sharpe));
const worstDD = Math.min(...RUNS.map(r => r.mean_max_dd));
document.getElementById('header-meta').textContent =
  RUNS.length + ' runs · best sharpe ' + best.toFixed(4) + ' · worst dd ' + worstDD.toFixed(2) + '%';

const labels = RUNS.map((r, i) => r.tag || ('#' + (i + 1)));
const hideNeg = document.getElementById('hide-neg');

// Compression
const cs = v => v >= 0 ? v : -Math.pow(Math.abs(v), 0.5);
const cd = v => v >= 0 ? v : -Math.sqrt(Math.abs(v));
const trunc = d => d.length > 60 ? d.slice(0, 57) + '...' : d;

// Per-metric config
const MC = {{
  sharpe: {{
    color: '#4fc3f7',
    bars: () => RUNS.map(r => (!hideNeg.checked || r.mean_sharpe >= 0) ? cs(r.mean_sharpe) : null),
    line: () => RUNS.map(r => (r.status === 'keep' && (!hideNeg.checked || r.mean_sharpe >= 0)) ? cs(r.mean_sharpe) : null),
    yTick: v => v >= 0 ? v.toFixed(2) : (-Math.pow(Math.abs(v), 2)).toFixed(1),
    tip: r => ['sharpe: ' + r.mean_sharpe.toFixed(4), trunc(r.description)],
  }},
  dd: {{
    color: '#ff9800',
    bars: () => RUNS.map(r => cd(r.mean_max_dd)),
    line: () => RUNS.map(() => null),
    yTick: v => v >= 0 ? v.toFixed(1) + '%' : (-Math.pow(Math.abs(v), 2)).toFixed(1) + '%',
    tip: r => ['max dd: ' + r.mean_max_dd.toFixed(2) + '%', trunc(r.description)],
  }},
  winrate: {{
    color: '#66bb6a',
    bars: () => RUNS.map(r => r.mean_win_rate),
    line: () => RUNS.map(() => null),
    yTick: v => (v * 100).toFixed(0) + '%',
    tip: r => ['win rate: ' + (r.mean_win_rate !== null ? (r.mean_win_rate * 100).toFixed(1) + '%' : '—'), trunc(r.description)],
  }},
}};

function colors(m) {{
  const k = MC[m].color;
  return RUNS.map(r => r.status === 'keep' ? k : r.status === 'crash' ? '#b71c1c' : '#2a2a34');
}}

// Zero-line plugin
Chart.register({{
  id: 'z',
  afterDraw(c) {{
    const y0 = c.scales.y.getPixelForValue(0);
    if (y0 < c.chartArea.top || y0 > c.chartArea.bottom) return;
    const x = c.ctx; x.save(); x.beginPath(); x.setLineDash([4, 4]);
    x.strokeStyle = '#252530'; x.lineWidth = 1;
    x.moveTo(c.chartArea.left, y0); x.lineTo(c.chartArea.right, y0);
    x.stroke(); x.restore();
  }}
}});

// Cumulative best
const cumBest = RUNS.map((_, i) => {{
  let b = null;
  for (let j = 0; j <= i; j++)
    if (RUNS[j].status === 'keep' && (!b || RUNS[j].mean_sharpe > b.s))
      b = {{ t: labels[j], s: RUNS[j].mean_sharpe }};
  return b;
}});

// Navigation
function navTo(i) {{
  if (i < 0 || i >= RUNS.length) return;
  selIdx = i; selRun = RUNS[i];
  renderDetail(selRun);
  chart.setActiveElements([{{ datasetIndex: 0, index: i }}]);
  chart.update('none');
  // Scroll chart to show selected bar
  const wrap = document.querySelector('.chart-wrap');
  const barW = chartInner.clientWidth / RUNS.length;
  const target = barW * i - wrap.clientWidth / 2;
  wrap.scrollTo({{ left: Math.max(0, target), behavior: 'smooth' }});
}}

function clearSel() {{
  selIdx = null; selRun = null;
  chart.setActiveElements([]); chart.update('none');
  document.getElementById('placeholder').style.display = 'block';
  document.getElementById('detail').style.display = 'none';
  document.getElementById('nav-pos').textContent = '\\u2014 / ' + RUNS.length;
  document.getElementById('nav-prev').disabled = true;
  document.getElementById('nav-next').disabled = true;
}}

document.getElementById('nav-prev').onclick = () => selIdx !== null && navTo(selIdx - 1);
document.getElementById('nav-next').onclick = () => selIdx !== null ? navTo(selIdx + 1) : navTo(0);

document.addEventListener('keydown', e => {{
  if (e.key === 'ArrowLeft') {{ e.preventDefault(); selIdx !== null ? navTo(selIdx - 1) : navTo(0); }}
  if (e.key === 'ArrowRight') {{ e.preventDefault(); selIdx !== null ? navTo(selIdx + 1) : navTo(0); }}
  if (e.key === 'Escape') clearSel();
}});

// Touch swipe
let tx = 0;
document.addEventListener('touchstart', e => {{ tx = e.changedTouches[0].clientX; }}, {{ passive: true }});
document.addEventListener('touchend', e => {{
  const dx = e.changedTouches[0].clientX - tx;
  if (Math.abs(dx) < 50) return;
  dx < 0 ? (selIdx !== null ? navTo(selIdx + 1) : navTo(0)) : (selIdx !== null ? navTo(selIdx - 1) : navTo(0));
}}, {{ passive: true }});

// Chart
const cfg = MC.sharpe;
const ctx = document.getElementById('chart').getContext('2d');
const chart = new Chart(ctx, {{
  data: {{
    labels,
    datasets: [
      {{ type: 'bar', label: 'main', data: cfg.bars(), backgroundColor: colors('sharpe'),
         borderWidth: 0, borderRadius: 2 }},
      {{ type: 'line', label: 'frontier', data: cfg.line(),
         borderColor: 'rgba(79,195,247,0.4)', borderWidth: 1.5,
         pointRadius: 0, fill: false, spanGaps: true, tension: 0 }},
    ]
  }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    onClick: (e, els) => {{
      if (!els.length) return;
      els[0].index === selIdx ? clearSel() : navTo(els[0].index);
    }},
    plugins: {{
      legend: {{ display: false }},
      tooltip: {{
        callbacks: {{
          title: items => labels[items[0].dataIndex],
          label: item => item.datasetIndex !== 0 ? null : MC[chartMetric].tip(RUNS[item.dataIndex]),
        }},
        backgroundColor: '#14141e', titleColor: '#e0e0f0',
        bodyColor: '#707088', borderColor: '#2a2a34', borderWidth: 1, padding: 10,
      }}
    }},
    scales: {{
      x: {{ grid: {{ display: false }}, ticks: {{ color: '#383848', maxRotation: 60, font: {{ size: 9 }} }} }},
      y: {{ grid: {{ color: '#141420' }}, border: {{ dash: [2, 2] }},
           ticks: {{ color: '#484858', font: {{ size: 10 }}, callback: cfg.yTick }} }},
    }}
  }}
}});

function setMetric(m) {{
  chartMetric = m;
  const c = MC[m];
  chart.data.datasets[0].data = c.bars();
  chart.data.datasets[0].backgroundColor = colors(m);
  chart.data.datasets[1].data = c.line();
  chart.data.datasets[1].borderColor = m === 'sharpe' ? 'rgba(79,195,247,0.4)' :
    m === 'dd' ? 'rgba(255,152,0,0.4)' : 'rgba(102,187,106,0.4)';
  chart.options.scales.y.ticks.callback = c.yTick;
  delete chart.options.scales.y.suggestedMin;
  delete chart.options.scales.y.suggestedMax;
  if (m === 'winrate') {{ chart.options.scales.y.suggestedMin = 0; chart.options.scales.y.suggestedMax = 1; }}
  chart.update();
  document.getElementById('leg-keep').style.background = c.color;
  document.getElementById('hide-neg-label').style.display = m === 'sharpe' ? 'flex' : 'none';
}}

document.querySelectorAll('#chart-tabs .tab').forEach(t =>
  t.addEventListener('click', () => {{
    document.querySelectorAll('#chart-tabs .tab').forEach(x => x.classList.remove('active'));
    t.classList.add('active');
    setMetric(t.dataset.chart);
  }})
);
hideNeg.addEventListener('change', () => setMetric(chartMetric));
document.getElementById('leg-keep').style.background = MC.sharpe.color;

// Chart scroll sizing — set min-width so bars don't crush on mobile
const chartInner = document.getElementById('chart-inner');
function setChartWidth() {{
  const wrap = document.querySelector('.chart-wrap');
  const minW = Math.max(RUNS.length * 7, wrap.clientWidth);
  chartInner.style.minWidth = minW + 'px';
}}
window.addEventListener('resize', setChartWidth);
setChartWidth();

// Symbol tabs
document.querySelectorAll('#sym-tabs .tab').forEach(t =>
  t.addEventListener('click', () => {{
    document.querySelectorAll('#sym-tabs .tab').forEach(x => x.classList.remove('active'));
    t.classList.add('active');
    symMetric = t.dataset.metric;
    if (selRun) renderSymbols(selRun);
  }})
);

function renderSymbols(run) {{
  const list = document.getElementById('sym-list');
  list.innerHTML = '';
  if (!run.symbols || !Object.keys(run.symbols).length) return;
  const key = symMetric === 'sharpe' ? 'sharpe_ratio' : symMetric === 'dd' ? 'max_drawdown_pct' : 'total_return_pct';
  const entries = Object.entries(run.symbols).map(([s, d]) => [s, d[key] ?? 0]).sort((a, b) => b[1] - a[1]);
  const maxA = Math.max(...entries.map(([, v]) => Math.abs(v)), 0.001);
  const cls = symMetric === 'dd' ? 'warn' : '';
  entries.forEach(([sym, val]) => {{
    const pct = Math.abs(val) / maxA * 100;
    const c = cls || (val >= 0 ? 'pos' : 'neg');
    const row = document.createElement('div');
    row.className = 'sym-row';
    row.innerHTML = `<span class="sym-name">${{sym}}</span><div class="sym-bg"><div class="sym-fill ${{c}}" style="width:${{pct.toFixed(1)}}%"></div></div><span class="sym-val ${{c}}">${{val.toFixed(2)}}</span>`;
    list.appendChild(row);
  }});
}}

function renderDetail(run) {{
  document.getElementById('placeholder').style.display = 'none';
  document.getElementById('detail').style.display = 'block';
  document.getElementById('nav-pos').textContent = (selIdx + 1) + ' / ' + RUNS.length;
  document.getElementById('nav-prev').disabled = selIdx <= 0;
  document.getElementById('nav-next').disabled = selIdx >= RUNS.length - 1;

  const b = cumBest[selIdx];
  document.getElementById('bsf-tag').textContent = b ? b.t : '\\u2014';
  document.getElementById('bsf-sharpe').textContent = b ? b.s.toFixed(4) : '\\u2014';

  document.getElementById('d-tag').textContent = run.tag || run.commit;
  document.getElementById('d-commit').textContent = run.commit;
  const badge = document.getElementById('d-badge');
  badge.textContent = run.status;
  badge.className = 'badge badge-' + run.status;
  document.getElementById('d-desc').textContent = run.description;

  const se = document.getElementById('m-sharpe');
  se.textContent = run.mean_sharpe.toFixed(4);
  se.className = 'm-val ' + (run.mean_sharpe >= 0 ? 'pos' : 'neg');
  const de = document.getElementById('m-dd');
  de.textContent = run.mean_max_dd.toFixed(2) + '%';
  de.className = 'm-val warn';
  const re = document.getElementById('m-ret');
  if (run.mean_total_return != null) {{
    re.textContent = run.mean_total_return.toFixed(2) + '%';
    re.className = 'm-val ' + (run.mean_total_return >= 0 ? 'pos' : 'neg');
  }} else {{
    re.textContent = '\\u2014'; re.className = 'm-val neutral';
  }}

  const ss = document.getElementById('sym-section');
  if (run.symbols && Object.keys(run.symbols).length) {{
    ss.style.display = 'block'; renderSymbols(run);
  }} else {{
    ss.style.display = 'none';
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
