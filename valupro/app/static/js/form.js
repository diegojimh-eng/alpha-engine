/**
 * form.js
 * Handles DCF form submission, client-side validation, and API call.
 * Passes the JSON response to results.js for rendering.
 */

"use strict";

// Bootstrap tooltip init
document.addEventListener("DOMContentLoaded", () => {
  // Init tooltips
  const tips = document.querySelectorAll('[data-bs-toggle="tooltip"]');
  tips.forEach(el => new bootstrap.Tooltip(el, { placement: "top" }));

  // Currency prefix sync
  const currencySelect = document.getElementById("currency");
  const symbols = { USD: "$", EUR: "€", GBP: "£", JPY: "¥", CAD: "CA$", AUD: "A$", CHF: "CHF " };
  const prefixIds = ["currencyPrefix", "cashPrefix", "debtPrefix"];

  function updateCurrencyPrefixes() {
    const sym = symbols[currencySelect.value] || currencySelect.value + " ";
    prefixIds.forEach(id => {
      const el = document.getElementById(id);
      if (el) el.textContent = sym;
    });
  }
  if (currencySelect) {
    currencySelect.addEventListener("change", updateCurrencyPrefixes);
  }

  // Form submit
  const form = document.getElementById("dcfForm");
  if (!form) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    e.stopPropagation();

    // Clear previous alerts
    showAlert(null);

    // Additional cross-field validation
    const wacc = parseFloat(document.getElementById("wacc").value);
    const tgr  = parseFloat(document.getElementById("terminal_growth_rate").value);
    if (!isNaN(wacc) && !isNaN(tgr) && tgr >= wacc) {
      showAlert(`Terminal Growth Rate (${tgr}%) must be less than WACC (${wacc}%). Please adjust.`, "danger");
      document.getElementById("terminal_growth_rate").classList.add("is-invalid");
      return;
    }

    // Bootstrap native validation
    form.classList.add("was-validated");
    if (!form.checkValidity()) {
      showAlert("Please fix the highlighted fields before running the valuation.", "danger");
      return;
    }

    // Build payload
    const payload = collectFormData();

    // Show loading state
    setLoading(true);
    showLoading();

    try {
      const resp = await fetch("/calculate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: "Unknown server error" }));
        throw new Error(err.detail || `HTTP ${resp.status}`);
      }

      const data = await resp.json();
      renderResults(data);           // handed to results.js
      scrollToResults();

    } catch (err) {
      showAlert(`Calculation failed: ${err.message}`, "danger");
      hideResults();
    } finally {
      setLoading(false);
    }
  });
});

/**
 * Collect all form field values and convert to the API payload shape.
 * The API's pct_to_decimal validator expects raw percent numbers (e.g. 8 for 8%).
 */
function collectFormData() {
  const g = (id) => {
    const el = document.getElementById(id);
    return el ? el.value : "";
  };
  const n = (id) => {
    const v = parseFloat(g(id));
    return isNaN(v) ? 0 : v;
  };

  return {
    company_name: g("company_name").trim(),
    currency: g("currency"),
    revenue: n("revenue"),
    revenue_growth_rate: n("revenue_growth_rate"),   // percent → API converts to decimal
    operating_margin: n("operating_margin"),
    tax_rate: n("tax_rate"),
    capex_pct_revenue: n("capex_pct_revenue"),
    depreciation_pct_revenue: n("depreciation_pct_revenue"),
    nwc_change_pct_revenue: n("nwc_change_pct_revenue"),
    wacc: n("wacc"),
    terminal_growth_rate: n("terminal_growth_rate"),
    projection_years: parseInt(g("projection_years")) || 10,
    shares_outstanding: n("shares_outstanding"),
    cash: n("cash"),
    debt: n("debt"),
  };
}

function setLoading(loading) {
  const btn = document.getElementById("submitBtn");
  const spinner = document.getElementById("submitSpinner");
  const icon = document.getElementById("submitIcon");
  if (!btn) return;

  btn.disabled = loading;
  if (spinner) spinner.classList.toggle("d-none", !loading);
  if (icon) icon.classList.toggle("d-none", loading);
}

function showLoading() {
  const sec = document.getElementById("resultsSection");
  const con = document.getElementById("resultsContainer");
  if (!sec || !con) return;
  sec.classList.remove("d-none");
  con.innerHTML = `
    <div class="vp-loading">
      <div class="vp-spinner"></div>
      <p>Running DCF valuation…</p>
    </div>`;
}

function hideResults() {
  const con = document.getElementById("resultsContainer");
  if (con) con.innerHTML = "";
}

function scrollToResults() {
  const sec = document.getElementById("resultsSection");
  if (sec) sec.scrollIntoView({ behavior: "smooth", block: "start" });
}

function showAlert(message, type = "danger") {
  const box = document.getElementById("alertBox");
  if (!box) return;
  if (!message) {
    box.classList.add("d-none");
    box.innerHTML = "";
    return;
  }
  box.className = `alert alert-${type} mb-4`;
  box.innerHTML = `<i class="fa-solid fa-triangle-exclamation me-2"></i>${message}`;
}
