"""Generates a self-contained HTML dashboard (day/week/month breakdown) from
the SQLite activity log, using the validated categorical palette."""
import json
import os

import aggregate

DASHBOARD_PATH = os.path.expanduser("~/timetrack/dashboard.html")


def generate_dashboard():
    data = aggregate.get_data()
    html = _render_html(data)
    with open(DASHBOARD_PATH, "w") as f:
        f.write(html)
    return DASHBOARD_PATH


def _render_html(data):
    data_json = json.dumps(data)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>TimeTrack Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<style>
  :root {{
    color-scheme: light;
    --surface-1: #fcfcfb;
    --page: #f9f9f7;
    --text-primary: #0b0b0b;
    --text-secondary: #52514e;
    --muted: #898781;
    --grid: #e1e0d9;
    --border: rgba(11,11,11,0.10);
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      color-scheme: dark;
      --surface-1: #1a1a19;
      --page: #0d0d0d;
      --text-primary: #ffffff;
      --text-secondary: #c3c2b7;
      --muted: #898781;
      --grid: #2c2c2a;
      --border: rgba(255,255,255,0.10);
    }}
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    padding: 24px 16px 48px;
    background: var(--page);
    color: var(--text-primary);
    font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  }}
  .wrap {{ max-width: 920px; margin: 0 auto; }}
  h1 {{ font-size: 20px; margin: 0 0 4px; }}
  .subtitle {{ color: var(--text-secondary); font-size: 13px; margin-bottom: 24px; }}
  .card {{
    background: var(--surface-1);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 20px;
  }}
  .card h2 {{ font-size: 15px; margin: 0 0 4px; }}
  .card .meta {{ color: var(--text-secondary); font-size: 12px; margin-bottom: 16px; }}
  canvas {{ max-width: 100%; }}
</style>
</head>
<body>
<div class="wrap">
  <h1>TimeTrack</h1>
  <div class="subtitle" id="generated"></div>

  <div class="card">
    <h2>Today by category</h2>
    <div class="meta" id="today-meta"></div>
    <canvas id="todayChart" height="180"></canvas>
  </div>

  <div class="card">
    <h2>Last 7 days</h2>
    <div class="meta">Minutes per category, per day</div>
    <canvas id="weekChart" height="260"></canvas>
  </div>

  <div class="card">
    <h2>Last 30 days</h2>
    <div class="meta">Minutes per category, per day</div>
    <canvas id="monthChart" height="260"></canvas>
  </div>
</div>

<script>
const DATA = {data_json};
const isDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
const textColor = isDark ? '#c3c2b7' : '#52514e';
const gridColor = isDark ? '#2c2c2a' : '#e1e0d9';

document.getElementById('generated').textContent = 'Generated ' + new Date(DATA.generated_at).toLocaleString();

function fmtMinutes(m) {{
  const h = Math.floor(m / 60);
  const mm = Math.round(m % 60);
  return h > 0 ? `${{h}}h ${{mm}}m` : `${{mm}}m`;
}}

document.getElementById('today-meta').textContent = DATA.today.date;

// Today: one bar per category, fixed order (never sorted by value)
new Chart(document.getElementById('todayChart'), {{
  type: 'bar',
  data: {{
    labels: DATA.today.labels,
    datasets: [{{
      label: 'Minutes',
      data: DATA.today.minutes,
      backgroundColor: isDark ? DATA.today.colors_dark : DATA.today.colors_light,
      borderRadius: 4,
      maxBarThickness: 40,
    }}]
  }},
  options: {{
    indexAxis: 'y',
    plugins: {{
      legend: {{ display: false }},
      tooltip: {{ callbacks: {{ label: (ctx) => fmtMinutes(ctx.parsed.x) }} }},
    }},
    scales: {{
      x: {{ ticks: {{ color: textColor }}, grid: {{ color: gridColor }},
            title: {{ display: true, text: 'minutes', color: textColor }} }},
      y: {{ ticks: {{ color: textColor }}, grid: {{ display: false }} }},
    }}
  }}
}});

function stackedBarConfig(dayLabels, series) {{
  return {{
    type: 'bar',
    data: {{
      labels: dayLabels,
      datasets: series.map(s => ({{
        label: s.label,
        data: s.data,
        backgroundColor: isDark ? s.color_dark : s.color_light,
        borderRadius: 4,
        maxBarThickness: 28,
      }}))
    }},
    options: {{
      responsive: true,
      scales: {{
        x: {{ stacked: true, ticks: {{ color: textColor }}, grid: {{ display: false }} }},
        y: {{ stacked: true, ticks: {{ color: textColor }}, grid: {{ color: gridColor }},
              title: {{ display: true, text: 'minutes', color: textColor }} }},
      }},
      plugins: {{
        legend: {{ position: 'bottom', labels: {{ color: textColor, boxWidth: 12 }} }},
        tooltip: {{ callbacks: {{ label: (ctx) => `${{ctx.dataset.label}}: ${{fmtMinutes(ctx.parsed.y)}}` }} }},
      }}
    }}
  }};
}}

new Chart(document.getElementById('weekChart'), stackedBarConfig(DATA.week.day_labels, DATA.week.series));
new Chart(document.getElementById('monthChart'), stackedBarConfig(DATA.month.day_labels, DATA.month.series));
</script>
</body>
</html>
"""


if __name__ == "__main__":
    print(generate_dashboard())
