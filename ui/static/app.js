/* ============================================================
   GRADE ADVISOR — frontend application logic
   ============================================================ */

"use strict";

const $ = (sel) => document.querySelector(sel);

const SCENARIOS = [
  {
    id: "01", title: "Cold work shock punching",
    desc: "Max toughness · HRC 60 · zero cobalt",
    query: "Cold work tooling, max toughness, HRC around 60, zero cobalt."
  },
  {
    id: "02", title: "Dry high-speed gear skiving",
    desc: "Extreme hot hardness · ultra-high cobalt",
    query: "Dry high-speed gear skiving requiring extreme hot hardness and ultra-high cobalt (>20% cobalt)."
  },
  {
    id: "03", title: "Corrosive plastic injection molds",
    desc: "Stainless · high chromium PM tool steel",
    query: "Plastic injection molds in corrosive environment, stainless high chromium PM tool steel."
  },
  {
    id: "04", title: "Machine tap manufacturing",
    desc: "Balanced grindability and toughness",
    query: "Dedicated steel for manufacturing machine taps, balanced grindability and toughness."
  },
  {
    id: "05", title: "Boundary failure stress test",
    desc: ">35% Co · >75 HRC — must reject",
    query: "Impossible constraint: tool steel with > 35% cobalt and hardness > 75 HRC."
  }
];

/* ---------- helpers ---------- */

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  }[c]));
}

function num(v) {
  const n = Number(v);
  return Number.isFinite(n) ? n : 0;
}

function fmt(v, d = 1) {
  return num(v).toFixed(d).replace(/\.0$/, "");
}

/* ---------- status / catalog ---------- */

async function initStatus() {
  try {
    const res = await fetch("/api/health");
    const h = await res.json();
    $("#status-text").textContent = `ROUTER: ${h.router} · MODEL: ${h.model} · CATALOG: ${h.catalog_size} GRADES`;
  } catch {
    $("#status-text").textContent = "ROUTER: OFFLINE";
    $(".status-chip .dot").style.background = "var(--bad)";
  }
}

async function loadCatalog() {
  const tbody = $("#catalog-table tbody");
  try {
    const res = await fetch("/api/catalog");
    const data = await res.json();
    tbody.innerHTML = data.map((g) => `
      <tr>
        <td class="grade">${esc(g.name)}</td>
        <td>${esc(g.family)}</td>
        <td>${fmt(g.c_pct)}</td>
        <td>${fmt(g.cr_pct)}</td>
        <td>${fmt(g.mo_pct)}</td>
        <td>${fmt(g.w_pct)}</td>
        <td>${fmt(g.v_pct)}</td>
        <td>${fmt(g.co_pct)}</td>
        <td>${fmt(g.hardness_min)}</td>
        <td>${fmt(g.hardness_max)}</td>
        <td>${esc(g.standards)}</td>
      </tr>`).join("");
  } catch {
    tbody.innerHTML = '<tr class="placeholder-row"><td colspan="11">Catalog unavailable</td></tr>';
  }
}

/* ---------- renderers ---------- */

function renderResult(res) {
  const matches = res.matches || [];

  if (!matches.length) {
    const conds = (res.sql_conditions || []).join(" AND ") || "the specified constraints";
    $("#result-body").innerHTML = `
      <div class="datasheet reject">
        <div class="reject-head">
          <div class="reject-title">No matching catalog grades</div>
          <div class="reject-sub">Physical &amp; chemical boundary rejection — constraint set unsatisfiable within the verified catalog</div>
        </div>
        <div class="reject-body">
          <div class="reject-conds">${esc(conds)}</div>
          <div class="reject-note">Zero-tolerance enforcement: the SQL gatekeeper refuses to return a near-miss grade. Relax the hard bounds or rephrase the qualitative intent.</div>
        </div>
      </div>`;
    return;
  }

  const top = matches[0];
  const d = top.data || {};
  const dist = num(top.distance);
  const proximity = Math.max(0, 100 - dist * 50);

  const comp = [
    ["C", d.c_pct], ["Cr", d.cr_pct], ["Mo", d.mo_pct],
    ["W", d.w_pct], ["V", d.v_pct], ["Co", d.co_pct]
  ].map(([el, v]) => `
    <div class="comp-cell">
      <div class="el">${el}</div>
      <div class="val">${fmt(v)}%</div>
    </div>`).join("");

  const props = [
    ["Machinability", d.machinability],
    ["Wear resistance", d.wear_resistance],
    ["Toughness", d.toughness],
    ["Hot hardness", d.hot_hardness],
    ["Grindability", d.grindability]
  ].map(([name, v]) => {
    const score = num(v);
    const pct = Math.min(Math.max(score * 10, 0), 100);
    return `
      <div class="prop-row">
        <span class="name">${name}</span>
        <div class="track"><div class="fill" style="width:${pct}%"></div></div>
        <span class="score">${score.toFixed(1)} / 10</span>
      </div>`;
  }).join("");

  const alts = matches.length > 1 ? `
    <div class="alts">
      <span class="micro-label">Secondary candidates</span>
      ${matches.slice(1).map((m) => `
        <span class="alt-chip"><b>${esc(m.name)}</b> &nbsp;d=${num(m.distance).toFixed(3)}</span>`).join("")}
    </div>` : "";

  $("#result-body").innerHTML = `
    <div class="datasheet">
      <div class="ds-head">
        <div>
          <div class="ds-name">${esc(d.name)}</div>
          <div class="ds-tags">
            <span class="tag family">${esc(d.family)}</span>
            <span class="tag std">${esc(d.standards || "Erasteel proprietary spec")}</span>
          </div>
        </div>
        <div class="ds-proximity">
          <div class="label">Vector proximity</div>
          <div class="value">${proximity.toFixed(0)}%</div>
          <div class="raw">d = ${dist.toFixed(3)}</div>
        </div>
      </div>

      <div class="ds-section">
        <div class="hardness-line">
          <span class="micro-label">Working hardness window</span>
          <span class="range">${fmt(d.hardness_min)} – ${fmt(d.hardness_max)} HRC</span>
        </div>
        <div class="comp-grid">${comp}</div>
      </div>

      <div class="ds-section">
        <div class="micro-label" style="margin-bottom:10px;">Property ratings</div>
        ${props}
      </div>

      <div class="ds-section ds-text">
        <div style="margin-bottom:10px;"><strong>Metallurgical rationale</strong><br>${esc(d.description)}</div>
        <div style="margin-bottom:10px;"><strong>Recommended applications</strong><br>${esc(d.applications)}</div>
        <div><strong>Heat treatment</strong><br>${esc(d.heat_treatment)}</div>
      </div>
      ${alts}
    </div>`;
}


/* ---------- audit trail renderers ---------- */

function renderAudit(res) {
  // SQL terminal
  const conds = res.sql_conditions || [];
  let sql;
  if (conds.length) {
    sql = "SELECT name, family, c_pct, cr_pct, mo_pct, w_pct, v_pct, co_pct,\n       hardness_min, hardness_max\nFROM steel_grades\n"
      + conds.map((c, i) => (i === 0 ? `WHERE ${c}` : `  AND ${c}`)).join("\n");
  } else {
    sql = "SELECT * FROM steel_grades  -- no strict numeric bounds extracted";
  }
  const matched = res.sql_matched_names || [];
  sql += `\n\n-- surviving candidate pool: ${matched.length} grade(s) passed hard bounds`
       + (matched.length ? `\n-- ${matched.join(", ")}` : `\n-- ZERO candidates matched (constraint violated)`);
  $("#sql-terminal").innerHTML = `<span class="dim">-- step 1 · DuckDB relational gatekeeper</span>\n` + esc(sql);

  // Semantic terminal
  $("#semantic-terminal").innerHTML =
    `<span class="dim">-- step 2 · query text fed to ChromaDB</span>\n`
    + esc(res.semantic_query || "N/A");

  // Ranking table
  const tbody = $("#ranking-table tbody");
  const matches = res.matches || [];
  tbody.innerHTML = matches.length
    ? matches.map((m, i) => {
        const g = m.data || {};
        return `
        <tr class="${i === 0 ? "top-rank" : ""}">
          <td>${i + 1}</td>
          <td class="grade">${esc(m.name)}</td>
          <td>${num(m.distance).toFixed(4)}</td>
          <td>${esc(g.family)}</td>
          <td>${fmt(g.hardness_max)}</td>
          <td>${fmt(g.co_pct)}</td>
        </tr>`;
      }).join("")
    : '<tr class="placeholder-row"><td colspan="6">—</td></tr>';

  // Raw payloads
  $("#json-terminal").innerHTML =
    `<span class="dim">-- ground-truth datasheet payloads retrieved from disk</span>\n`
    + esc(JSON.stringify(matches.map((m) => m.data || {}), null, 2));
}

/* ---------- query pipeline ---------- */

let busy = false;

async function runQuery(query, fillInput = true) {
  if (busy) return;
  busy = true;
  if (fillInput) $("#query-input").value = query;

  const runBtn = $("#run-btn");
  runBtn.disabled = true;
  runBtn.textContent = "Running";

  $("#result-body").innerHTML = `
    <div class="loading-state">
      <div class="bar"></div>
      <p>DUAL-STAGE RETRIEVAL IN PROGRESS</p>
    </div>`;

  try {
    const res = await fetch("/api/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query })
    });
    const data = await res.json();
    if (!res.ok || data.error) {
      throw new Error(data.error || `HTTP ${res.status}`);
    }
    renderResult(data);
    renderAudit(data);
  } catch (err) {
    $("#result-body").innerHTML = `
      <div class="error-card">
        <h3>Retrieval error</h3>
        <pre>${esc(err.message)}</pre>
      </div>`;
  } finally {
    busy = false;
    runBtn.disabled = false;
    runBtn.textContent = "Run Retrieval";
  }
}

function resetAll() {
  $("#query-input").value = "";
  $("#result-body").innerHTML = `
    <div class="empty-state" id="empty-state">
      <div class="empty-rule"></div>
      <p>NO ACTIVE QUERY</p>
      <p class="small">Awaiting input — select a scenario or compose a query.</p>
      <div class="empty-rule"></div>
    </div>`;
  $("#sql-terminal").textContent = "-- Awaiting query submission...";
  $("#semantic-terminal").textContent = "N/A";
  $("#json-terminal").textContent = "{}";
  $("#ranking-table tbody").innerHTML = '<tr class="placeholder-row"><td colspan="6">—</td></tr>';
}

/* ---------- init ---------- */

function initScenarios() {
  $("#scenario-list").innerHTML = SCENARIOS.map((s) => `
    <button class="scenario" data-query="${esc(s.query)}">
      <span class="num">${s.id}</span>
      <span>
        <span class="title">${esc(s.title)}</span>
        <div class="desc">${esc(s.desc)}</div>
      </span>
      <span class="arrow">&rarr;</span>
    </button>`).join("");

  document.querySelectorAll(".scenario").forEach((btn) => {
    btn.addEventListener("click", () => runQuery(btn.dataset.query));
  });
}

function initTabs() {
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
      document.querySelectorAll(".tab-pane").forEach((p) => p.classList.remove("active"));
      tab.classList.add("active");
      $(`#pane-${tab.dataset.tab}`).classList.add("active");
    });
  });
}

document.addEventListener("DOMContentLoaded", () => {
  initStatus();
  loadCatalog();
  initScenarios();
  initTabs();

  $("#run-btn").addEventListener("click", () => {
    const q = $("#query-input").value.trim();
    if (q) runQuery(q, false);
  });

  $("#clear-btn").addEventListener("click", resetAll);

  $("#query-input").addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      const q = $("#query-input").value.trim();
      if (q) runQuery(q, false);
    }
  });
});

