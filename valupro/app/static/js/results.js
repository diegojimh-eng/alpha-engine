/**
 * results.js
 * Renders the complete DCF results dashboard from the API JSON response.
 *
 * Called by form.js after a successful /calculate response.
 * All values displayed are taken directly from the API response —
 * no recalculation is performed here.
 */

"use strict";

// Keep chart instances so we can destroy before re-render
let _chartRevenue = null;
let _chartFcff    = null;
let _chartCompose = null;

/**
 * Main entry point called by form.js.
 * @param {Object} data — ValuationResponse JSON from the API
 */
function renderResults(data) {
  const container = document.getElementById("resultsContainer");
  if (!container) return;

  const { summary, projections, warnings, chart_years,
          chart_revenue, chart_fcff, chart_pv_fcff,
          company_name, currency } = data;

  const sym = currencySymbol(currency);

  // Destroy previous charts to avoid canvas reuse errors
  [_chartRevenue, _chartFcff, _chartCompose].forEach(c => { if (c) c.destroy(); });

  container.innerHTML = buildResultsHTML(data, sym);

  renderWarnings(warnings);
  _chartRevenue = renderRevenueChart(chart_years, chart_revenue, sym);
  _chartFcff    = renderFcffChart(chart_years, chart_fcff, chart_pv_fcff, sym);
  _chartCompose = renderComposeChart(summary, sym);
}

// ── HTML builder ──────────────────────────────────────────────────────────────

function buildResultsHTML(data, sym) {
  const { summary, projections, company_name, currency, warnings } = data;
  const s = summary;

  const fmtB = (v) => {
    if (Math.abs(v) >= 1e12) return `${sym}${(v / 1e12).toFixed(2)}T`;
    if (Math.abs(v) >= 1e9)  return `${sym}${(v / 1e9).toFixed(2)}B`;
    if (Math.abs(v) >= 1e6)  return `${sym}${(v / 1e6).toFixed(2)}M`;
    return `${sym}${v.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
  };
  const fmtS = (v) => `${sym}${v.toFixed(2)}`;
  const fmtP = (v) => `${(v * 100).toFixed(1)}%`;
  const fmtF = (v) => v.toFixed(5);

  const evClass  = s.enterprise_value >= 0 ? "positive" : "negative";
  const eqClass  = s.equity_value >= 0     ? "positive" : "negative";
  const fvpClass = s.fair_value_per_share >= 0 ? "" : "negative";

  const warningsHtml = warnings && warnings.length
    ? `<div class="vp-warnings" id="warningBox">
        <div class="vp-warn-title"><i class="fa-solid fa-triangle-exclamation me-2"></i>Valuation Notices</div>
        <ul>${warnings.map(w => `<li>${escHtml(w)}</li>`).join("")}</ul>
      </div>`
    : "";

  return `
    ${warningsHtml}

    <!-- ── KPI Cards ── -->
    <div class="row g-3 mb-4">
      <div class="col-sm-6 col-lg-3">
        <div class="vp-kpi-card">
          <div class="vp-kpi-label">Enterprise Value</div>
          <div class="vp-kpi-value ${evClass}">${fmtB(s.enterprise_value)}</div>
          <div class="vp-kpi-sub">${currency}</div>
        </div>
      </div>
      <div class="col-sm-6 col-lg-3">
        <div class="vp-kpi-card">
          <div class="vp-kpi-label">Equity Value</div>
          <div class="vp-kpi-value ${eqClass}">${fmtB(s.equity_value)}</div>
          <div class="vp-kpi-sub">EV − Net Debt</div>
        </div>
      </div>
      <div class="col-sm-6 col-lg-3">
        <div class="vp-kpi-card">
          <div class="vp-kpi-label">Fair Value / Share</div>
          <div class="vp-kpi-value ${fvpClass}">${fmtS(s.fair_value_per_share)}</div>
          <div class="vp-kpi-sub">${currency}</div>
        </div>
      </div>
      <div class="col-sm-6 col-lg-3">
        <div class="vp-kpi-card">
          <div class="vp-kpi-label">Terminal Value % EV</div>
          <div class="vp-kpi-value neutral">${fmtP(s.terminal_value_pct_ev)}</div>
          <div class="vp-kpi-sub">PV(TV) / EV</div>
        </div>
      </div>
    </div>

    <!-- ── Charts row ── -->
    <div class="row g-3 mb-4">
      <div class="col-lg-6">
        <div class="vp-result-card">
          <div class="vp-result-card-header">
            <i class="fa-solid fa-chart-line me-2 text-success"></i>Revenue Forecast
          </div>
          <div class="vp-result-card-body">
            <div class="vp-chart-wrapper"><canvas id="chartRevenue"></canvas></div>
          </div>
        </div>
      </div>
      <div class="col-lg-6">
        <div class="vp-result-card">
          <div class="vp-result-card-header">
            <i class="fa-solid fa-chart-bar me-2 text-info"></i>Free Cash Flow Forecast
          </div>
          <div class="vp-result-card-body">
            <div class="vp-chart-wrapper"><canvas id="chartFcff"></canvas></div>
          </div>
        </div>
      </div>
      <div class="col-12">
        <div class="vp-result-card">
          <div class="vp-result-card-header">
            <i class="fa-solid fa-chart-pie me-2" style="color:var(--vp-accent)"></i>Value Composition
          </div>
          <div class="vp-result-card-body">
            <div class="vp-chart-wrapper" style="height:240px"><canvas id="chartCompose"></canvas></div>
          </div>
        </div>
      </div>
    </div>

    <!-- ── Terminal Value Breakdown ── -->
    <div class="vp-result-card mb-4">
      <div class="vp-result-card-header">
        <i class="fa-solid fa-infinity me-2" style="color:var(--vp-accent)"></i>Terminal Value Breakdown
      </div>
      <div class="vp-result-card-body">
        <div class="row g-3">
          <div class="col-md-3">
            <div class="text-muted small mb-1">Terminal FCFF</div>
            <div class="fw-semibold">${fmtB(s.terminal_value - (s.terminal_value - s.pv_terminal_value * (1 + 0)))}</div>
            <div class="text-muted" style="font-size:.75rem">FCFF in final year (undiscounted)</div>
          </div>
          <div class="col-md-3">
            <div class="text-muted small mb-1">Terminal Value (TV)</div>
            <div class="fw-semibold" style="color:var(--vp-accent)">${fmtB(s.terminal_value)}</div>
            <div class="text-muted" style="font-size:.75rem">Gordon Growth: FCFF×(1+g)/(WACC−g)</div>
          </div>
          <div class="col-md-3">
            <div class="text-muted small mb-1">PV of Terminal Value</div>
            <div class="fw-semibold" style="color:var(--vp-accent)">${fmtB(s.pv_terminal_value)}</div>
            <div class="text-muted" style="font-size:.75rem">TV discounted to today</div>
          </div>
          <div class="col-md-3">
            <div class="text-muted small mb-1">Sum PV(FCFF)</div>
            <div class="fw-semibold">${fmtB(s.sum_pv_fcff)}</div>
            <div class="text-muted" style="font-size:.75rem">Explicit period value</div>
          </div>
        </div>
        <div class="mt-3 vp-formula-reminder">
          <code>EV = Σ PV(FCFF<sub>t</sub>) + PV(TV) = ${fmtB(s.sum_pv_fcff)} + ${fmtB(s.pv_terminal_value)} = ${fmtB(s.enterprise_value)}</code>
        </div>
      </div>
    </div>

    <!-- ── Equity Bridge ── -->
    <div class="vp-result-card mb-4">
      <div class="vp-result-card-header">
        <i class="fa-solid fa-scale-balanced me-2"></i>Equity Bridge
      </div>
      <div class="vp-result-card-body">
        <table class="vp-table">
          <tbody>
            <tr>
              <td>Enterprise Value</td>
              <td class="num">${fmtB(s.enterprise_value)}</td>
            </tr>
            <tr>
              <td>Less: Net Debt (Debt − Cash)</td>
              <td class="num">(${fmtB(s.net_debt)})</td>
            </tr>
            <tr style="border-top:1px solid var(--vp-accent); font-weight:700;">
              <td>= Equity Value</td>
              <td class="num" style="color:var(--vp-accent)">${fmtB(s.equity_value)}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- ── Projection Table ── -->
    <div class="vp-result-card mb-4">
      <div class="vp-result-card-header">
        <i class="fa-solid fa-table me-2"></i>Year-by-Year DCF Schedule
      </div>
      <div class="vp-result-card-body p-0">
        <div class="vp-table-scroll">
          <table class="vp-table">
            <thead>
              <tr>
                <th>Year</th>
                <th class="num">Revenue</th>
                <th class="num">EBIT</th>
                <th class="num">NOPAT</th>
                <th class="num">D&amp;A</th>
                <th class="num">CapEx</th>
                <th class="num">ΔNWC</th>
                <th class="num">FCFF</th>
                <th class="num">Disc. Factor</th>
                <th class="num">PV(FCFF)</th>
              </tr>
            </thead>
            <tbody>
              ${projections.map(p => `
                <tr>
                  <td><strong>${p.year}</strong></td>
                  <td class="num">${fmtB(p.revenue)}</td>
                  <td class="num">${fmtB(p.ebit)}</td>
                  <td class="num">${fmtB(p.nopat)}</td>
                  <td class="num">${fmtB(p.depreciation)}</td>
                  <td class="num">${fmtB(p.capex)}</td>
                  <td class="num">${fmtB(p.delta_nwc)}</td>
                  <td class="num" style="color:var(--vp-accent)">${fmtB(p.fcff)}</td>
                  <td class="num">${fmtF(p.discount_factor)}</td>
                  <td class="num">${fmtB(p.pv_fcff)}</td>
                </tr>`).join("")}
            </tbody>
            <tfoot>
              <tr style="font-weight:700; border-top:2px solid var(--vp-border)">
                <td>Total</td>
                <td colspan="6"></td>
                <td class="num" style="color:var(--vp-accent)">${fmtB(projections.reduce((a, p) => a + p.fcff, 0))}</td>
                <td></td>
                <td class="num">${fmtB(s.sum_pv_fcff)}</td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>
    </div>
  `;
}

// ── Chart renderers ───────────────────────────────────────────────────────────

const CHART_DEFAULTS = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      labels: { color: "#8b949e", font: { size: 11 } }
    },
    tooltip: {
      backgroundColor: "#1c2330",
      borderColor: "#30363d",
      borderWidth: 1,
      titleColor: "#e6edf3",
      bodyColor: "#8b949e",
    }
  },
  scales: {
    x: {
      ticks: { color: "#8b949e", font: { size: 11 } },
      grid: { color: "rgba(48,54,61,0.6)" }
    },
    y: {
      ticks: { color: "#8b949e", font: { size: 11 } },
      grid: { color: "rgba(48,54,61,0.6)" }
    }
  }
};

function renderRevenueChart(years, revenues, sym) {
  const ctx = document.getElementById("chartRevenue");
  if (!ctx) return null;
  return new Chart(ctx, {
    type: "bar",
    data: {
      labels: years,
      datasets: [{
        label: `Revenue (${sym})`,
        data: revenues,
        backgroundColor: "rgba(59,130,246,0.5)",
        borderColor: "#3b82f6",
        borderWidth: 1,
        borderRadius: 3,
      }]
    },
    options: {
      ...CHART_DEFAULTS,
      plugins: {
        ...CHART_DEFAULTS.plugins,
        tooltip: {
          ...CHART_DEFAULTS.plugins.tooltip,
          callbacks: {
            label: (ctx) => ` ${sym}${humanise(ctx.parsed.y)}`
          }
        }
      },
      scales: {
        ...CHART_DEFAULTS.scales,
        y: {
          ...CHART_DEFAULTS.scales.y,
          ticks: {
            ...CHART_DEFAULTS.scales.y.ticks,
            callback: (v) => `${sym}${humanise(v)}`
          }
        }
      }
    }
  });
}

function renderFcffChart(years, fcff, pvFcff, sym) {
  const ctx = document.getElementById("chartFcff");
  if (!ctx) return null;
  return new Chart(ctx, {
    type: "line",
    data: {
      labels: years,
      datasets: [
        {
          label: "FCFF",
          data: fcff,
          borderColor: "#00d4aa",
          backgroundColor: "rgba(0,212,170,0.08)",
          borderWidth: 2,
          pointRadius: 4,
          pointBackgroundColor: "#00d4aa",
          tension: 0.3,
          fill: true,
        },
        {
          label: "PV(FCFF)",
          data: pvFcff,
          borderColor: "#f59e0b",
          backgroundColor: "rgba(245,158,11,0.06)",
          borderWidth: 2,
          borderDash: [5, 3],
          pointRadius: 3,
          tension: 0.3,
          fill: false,
        }
      ]
    },
    options: {
      ...CHART_DEFAULTS,
      plugins: {
        ...CHART_DEFAULTS.plugins,
        tooltip: {
          ...CHART_DEFAULTS.plugins.tooltip,
          callbacks: {
            label: (ctx) => ` ${ctx.dataset.label}: ${sym}${humanise(ctx.parsed.y)}`
          }
        }
      },
      scales: {
        ...CHART_DEFAULTS.scales,
        y: {
          ...CHART_DEFAULTS.scales.y,
          ticks: {
            ...CHART_DEFAULTS.scales.y.ticks,
            callback: (v) => `${sym}${humanise(v)}`
          }
        }
      }
    }
  });
}

function renderComposeChart(summary, sym) {
  const ctx = document.getElementById("chartCompose");
  if (!ctx) return null;

  const pvFcff = summary.sum_pv_fcff;
  const pvTv   = summary.pv_terminal_value;
  const nd     = Math.max(summary.net_debt, 0);

  return new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: ["PV of FCFF (Explicit)", "PV of Terminal Value", "Net Debt"],
      datasets: [{
        data: [Math.max(pvFcff, 0), Math.max(pvTv, 0), nd],
        backgroundColor: [
          "rgba(59,130,246,0.75)",
          "rgba(0,212,170,0.75)",
          "rgba(248,81,73,0.65)",
        ],
        borderColor: ["#3b82f6", "#00d4aa", "#f85149"],
        borderWidth: 1,
        hoverOffset: 6,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: "65%",
      plugins: {
        legend: {
          position: "right",
          labels: { color: "#8b949e", font: { size: 11 }, padding: 14 }
        },
        tooltip: {
          backgroundColor: "#1c2330",
          borderColor: "#30363d",
          borderWidth: 1,
          titleColor: "#e6edf3",
          bodyColor: "#8b949e",
          callbacks: {
            label: (ctx) => ` ${sym}${humanise(ctx.parsed)}`
          }
        }
      }
    }
  });
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function humanise(v) {
  const abs = Math.abs(v);
  if (abs >= 1e12) return (v / 1e12).toFixed(2) + "T";
  if (abs >= 1e9)  return (v / 1e9).toFixed(2)  + "B";
  if (abs >= 1e6)  return (v / 1e6).toFixed(2)  + "M";
  if (abs >= 1e3)  return (v / 1e3).toFixed(1)  + "K";
  return v.toFixed(0);
}

function currencySymbol(code) {
  const m = { USD: "$", EUR: "€", GBP: "£", JPY: "¥", CAD: "CA$", AUD: "A$", CHF: "CHF " };
  return m[code] || code + " ";
}

function escHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function renderWarnings(warnings) {
  // Already rendered inline in buildResultsHTML — nothing to do.
}
