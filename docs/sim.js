/* ============================================================
   Interactive simulation driver.
   - Loads Pyodide + numpy + networkx
   - Mounts the bundled water_abm package and a tiny mesa-shim
   - UI: parameter sliders, Setup / Start / Step / Reset, live chart + canvas grid
   ============================================================ */

const PYODIDE_VERSION = "v0.26.4";

const $ = (id) => document.getElementById(id);

// ---------- DOM ------------------------------------------------------------

const ui = {
  loading: $("loading"),
  loadingStatus: $("loading-status"),
  main: $("sim-main"),

  // Status
  step: $("status-step"),
  water: $("status-water"),
  cf: $("status-cf"),
  ext: $("status-ext"),
  coop: $("status-coop"),
  verdict: $("status-verdict"),
  waterbarFill: $("waterbar-fill"),

  // Canvas + chart
  gridCanvas: $("grid-canvas"),
  chartCanvas: $("chart-canvas"),

  // Controls
  btnSetup: $("btn-setup"),
  btnStep: $("btn-step"),
  btnRun: $("btn-run"),
  btnReset: $("btn-reset"),
  speed: $("speed-slider"),
  speedLabel: $("speed-label"),

  // Params
  pN: $("p-n"), pAlpha: $("p-alpha"), pGamma: $("p-gamma"),
  pEps: $("p-eps"), pDetect: $("p-detect"), pR: $("p-r"),
  pClimate: $("p-climate"), pSeed: $("p-seed"),
};

const paramVal = {
  "p-n": $("p-n-val"), "p-alpha": $("p-alpha-val"), "p-gamma": $("p-gamma-val"),
  "p-eps": $("p-eps-val"), "p-detect": $("p-detect-val"), "p-r": $("p-r-val"),
};

const ACTION_COLORS = ["#1f77ff", "#5da5da", "#cccc00", "#ff9933", "#cc0000"];

let pyodide = null;
let model = null;       // Python proxy
let running = false;
let runTimer = null;

// ---------- Chart ----------------------------------------------------------

const waterHistory = []; // last N steps
const HISTORY_LEN = 200;
let chart = null;

function initChart() {
  const ctx = ui.chartCanvas.getContext("2d");
  chart = new Chart(ctx, {
    type: "line",
    data: {
      labels: [],
      datasets: [{
        label: "Water level",
        data: [],
        borderColor: "#0d9488",
        backgroundColor: "rgba(13, 148, 136, 0.10)",
        fill: true,
        tension: 0.2,
        pointRadius: 0,
        borderWidth: 2,
      }],
    },
    options: {
      animation: { duration: 0 },
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: {
          title: { display: true, text: "step", color: "#64748b" },
          grid: { color: "#f1f5f9" },
        },
        y: {
          min: 0,
          max: 1050,
          title: { display: true, text: "water (units of K)", color: "#64748b" },
          grid: { color: "#f1f5f9" },
        },
      },
      plugins: {
        legend: { display: false },
        annotation: {},
      },
    },
  });
}

function pushChartPoint(step, water) {
  waterHistory.push({ x: step, y: water });
  while (waterHistory.length > HISTORY_LEN) waterHistory.shift();
  chart.data.labels = waterHistory.map(p => p.x);
  chart.data.datasets[0].data = waterHistory.map(p => p.y);
  chart.update("none");
}

function resetChart() {
  waterHistory.length = 0;
  chart.data.labels = [];
  chart.data.datasets[0].data = [];
  chart.update("none");
}

// ---------- Grid canvas ----------------------------------------------------

function drawGrid(state) {
  const cnv = ui.gridCanvas;
  const ctx = cnv.getContext("2d");
  const W = cnv.width, H = cnv.height;
  const cell = W / state.grid_w;

  // Background = light farmland green.
  ctx.fillStyle = "#f0f9eb";
  ctx.fillRect(0, 0, W, H);

  // River column shading (left column, cell width 'cell').
  const waterNorm = Math.max(0, Math.min(1, state.water_normalized));
  let riverColor;
  if (waterNorm <= 0.02)        riverColor = "#7a5230"; // dry bed
  else if (waterNorm < 0.20)    riverColor = "#c9d9e8";
  else if (waterNorm < 0.45)    riverColor = "#7fb3d5";
  else if (waterNorm < 0.70)    riverColor = "#2980b9";
  else                          riverColor = "#1b4f72";
  ctx.fillStyle = riverColor;
  ctx.fillRect(0, 0, cell, H);

  // Cell gridlines (very subtle).
  ctx.strokeStyle = "#e5e7eb";
  ctx.lineWidth = 0.5;
  for (let i = 0; i <= state.grid_w; i++) {
    ctx.beginPath(); ctx.moveTo(i * cell, 0); ctx.lineTo(i * cell, H); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(0, i * cell); ctx.lineTo(W, i * cell); ctx.stroke();
  }

  // Monitor (star on the river column).
  const mx = (state.monitor_pos[0] + 0.5) * cell;
  const my = (state.grid_h - state.monitor_pos[1] - 1 + 0.5) * cell;
  drawStar(ctx, mx, my, cell * 0.35, "#000000", "#ffd166");

  // Agents.
  for (const ag of state.agents) {
    const ax = (ag.x + 0.5) * cell;
    const ay = (state.grid_h - ag.y - 1 + 0.5) * cell;
    // Radius grows with action level.
    const r = cell * (0.22 + 0.12 * (ag.a / 4));
    ctx.beginPath();
    ctx.arc(ax, ay, r, 0, Math.PI * 2);
    ctx.fillStyle = ACTION_COLORS[ag.a];
    ctx.fill();
    ctx.strokeStyle = "rgba(15, 23, 42, 0.4)";
    ctx.lineWidth = 0.7;
    ctx.stroke();
  }
}

function drawStar(ctx, cx, cy, r, stroke, fill) {
  const spikes = 5;
  ctx.beginPath();
  for (let i = 0; i < spikes * 2; i++) {
    const angle = (Math.PI / spikes) * i - Math.PI / 2;
    const radius = i % 2 === 0 ? r : r * 0.45;
    const x = cx + Math.cos(angle) * radius;
    const y = cy + Math.sin(angle) * radius;
    if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
  }
  ctx.closePath();
  ctx.fillStyle = fill;
  ctx.fill();
  ctx.strokeStyle = stroke;
  ctx.lineWidth = 1.2;
  ctx.stroke();
}

// ---------- Pyodide bootstrap ---------------------------------------------

async function bootstrap() {
  const setStatus = (s) => { ui.loadingStatus.textContent = s; };

  setStatus("Starting Pyodide…");
  pyodide = await loadPyodide({
    indexURL: `https://cdn.jsdelivr.net/pyodide/${PYODIDE_VERSION}/full/`,
  });

  setStatus("Loading numpy + networkx…");
  await pyodide.loadPackage(["numpy", "networkx"]);

  setStatus("Bundling water_abm…");
  // Files we ship from docs/sim_assets/
  const files = [
    "mesa_shim.py",
    "water_abm/__init__.py",
    "water_abm/q_learning.py",
    "water_abm/climate.py",
    "water_abm/environment.py",
    "water_abm/agents.py",
    "water_abm/model.py",
  ];
  // Create the directories in Pyodide FS.
  pyodide.FS.mkdir("/home/pyodide/sim");
  pyodide.FS.mkdir("/home/pyodide/sim/water_abm");

  for (const f of files) {
    const resp = await fetch(`sim_assets/${f}`);
    if (!resp.ok) throw new Error(`Failed to fetch ${f}`);
    const text = await resp.text();
    const target = `/home/pyodide/sim/${f}`;
    pyodide.FS.writeFile(target, text);
  }

  setStatus("Installing mesa shim…");
  await pyodide.runPythonAsync(`
import sys
sys.path.insert(0, "/home/pyodide/sim")
import mesa_shim   # registers fake 'mesa' module in sys.modules
from water_abm.model import WaterCommonsModel
print("Pyodide ready: WaterCommonsModel loaded")
`);

  setStatus("Ready");
  ui.loading.style.display = "none";
  ui.main.style.display = "block";
}

// ---------- Build / reset / step ------------------------------------------

function readParams() {
  return {
    n_farmers: parseInt(ui.pN.value),
    alpha: parseFloat(ui.pAlpha.value),
    gamma: parseFloat(ui.pGamma.value),
    epsilon_0: parseFloat(ui.pEps.value),
    p_detect: parseFloat(ui.pDetect.value),
    regeneration_rate: parseFloat(ui.pR.value),
    climate_scenario: ui.pClimate.value,
    seed: parseInt(ui.pSeed.value),
  };
}

async function buildModel() {
  const p = readParams();
  // Pass params as a Python dict via globals.
  pyodide.globals.set("ui_params", pyodide.toPy(p));
  await pyodide.runPythonAsync(`
from water_abm.model import WaterCommonsModel
p = dict(ui_params)
model = WaterCommonsModel(
    n_farmers      = int(p['n_farmers']),
    alpha          = float(p['alpha']),
    gamma          = float(p['gamma']),
    epsilon_0      = float(p['epsilon_0']),
    p_detect       = float(p['p_detect']),
    regeneration_rate = float(p['regeneration_rate']),
    climate_scenario  = p['climate_scenario'],
    seed           = int(p['seed']),
)
`);
}

function readState() {
  const obj = pyodide.runPython(`
def __state():
    agents = []
    for a in model.schedule.agents:
        agents.append({"x": a.pos[0], "y": a.pos[1], "a": a.last_action_idx,
                       "strat": a.strategy_type})
    return {
        "step": model.step_count,
        "water": float(model.water.level),
        "water_normalized": float(model.water.normalized_level),
        "carrying_capacity": float(model.water.carrying_capacity),
        "climate_factor": float(model.current_climate_factor()),
        "mean_extraction": float(model.mean_extraction_this_step),
        "cooperation_index": float(model.cooperation_index),
        "grid_w": model.grid.width,
        "grid_h": model.grid.height,
        "monitor_pos": list(model.monitor.pos),
        "agents": agents,
    }
__state()
`);
  return obj.toJs({ dict_converter: Object.fromEntries });
}

function renderState(s) {
  ui.step.textContent = s.step;
  ui.water.textContent = s.water.toFixed(1);
  ui.cf.textContent = s.climate_factor.toFixed(2);
  ui.ext.textContent = s.mean_extraction.toFixed(2);
  ui.coop.textContent = s.cooperation_index.toFixed(2);

  // Verdict + waterbar
  const pct = (s.water / s.carrying_capacity) * 100;
  ui.waterbarFill.style.width = `${Math.max(2, pct).toFixed(1)}%`;
  ui.verdict.classList.remove("verdict-healthy", "verdict-stressed", "verdict-depleting", "verdict-collapsed");
  if (pct >= 60)      { ui.verdict.textContent = "HEALTHY";    ui.verdict.classList.add("verdict-healthy"); }
  else if (pct >= 30) { ui.verdict.textContent = "STRESSED";   ui.verdict.classList.add("verdict-stressed"); }
  else if (pct >= 5)  { ui.verdict.textContent = "DEPLETING";  ui.verdict.classList.add("verdict-depleting"); }
  else                { ui.verdict.textContent = "COLLAPSED";  ui.verdict.classList.add("verdict-collapsed"); }

  drawGrid(s);
  pushChartPoint(s.step, s.water);
}

async function doSetup() {
  ui.btnSetup.disabled = true;
  ui.btnSetup.textContent = "Setting up…";
  try {
    await buildModel();
    resetChart();
    const s = readState();
    renderState(s);
    ui.btnStep.disabled = false;
    ui.btnRun.disabled = false;
    ui.btnReset.disabled = false;
  } catch (e) {
    alert("Setup failed: " + e);
    console.error(e);
  } finally {
    ui.btnSetup.disabled = false;
    ui.btnSetup.textContent = "Setup";
  }
}

function doStep() {
  pyodide.runPython("model.step()");
  const s = readState();
  renderState(s);
  return s;
}

function startRun() {
  if (running) return;
  running = true;
  ui.btnRun.textContent = "⏸ Pause";
  const tick = () => {
    if (!running) return;
    try {
      const s = doStep();
      // Stop if water collapses fully (optional)
      if (s.step >= 1000) { stopRun(); return; }
    } catch (e) {
      stopRun(); alert("Error during step: " + e); return;
    }
    const fps = parseInt(ui.speed.value);
    runTimer = setTimeout(tick, 1000 / fps);
  };
  tick();
}

function stopRun() {
  running = false;
  if (runTimer) clearTimeout(runTimer);
  ui.btnRun.textContent = "▶ Start";
}

function toggleRun() {
  if (running) stopRun(); else startRun();
}

async function doReset() {
  stopRun();
  await buildModel();
  resetChart();
  renderState(readState());
}

// ---------- Param wiring --------------------------------------------------

function bindParamDisplay() {
  for (const key of Object.keys(paramVal)) {
    const input = $(key);
    const out = paramVal[key];
    const fmt = (v) => {
      if (key === "p-n") return v;
      if (key === "p-detect" || key === "p-eps" || key === "p-alpha" || key === "p-r") return parseFloat(v).toFixed(2);
      return parseFloat(v).toFixed(2);
    };
    input.addEventListener("input", () => { out.textContent = fmt(input.value); });
    out.textContent = fmt(input.value);
  }
  ui.speed.addEventListener("input", () => {
    ui.speedLabel.textContent = `${ui.speed.value} fps`;
  });
  ui.speedLabel.textContent = `${ui.speed.value} fps`;
}

function bindControls() {
  ui.btnSetup.addEventListener("click", doSetup);
  ui.btnStep.addEventListener("click", () => doStep());
  ui.btnRun.addEventListener("click", toggleRun);
  ui.btnReset.addEventListener("click", doReset);
}

function bindPresets() {
  document.querySelectorAll(".preset").forEach(btn => {
    btn.addEventListener("click", () => {
      const preset = btn.dataset.preset;
      const map = {
        tragedy:     { climate: "stable",  detect: 0,    eps: 0.30 },
        cooperation: { climate: "stable",  detect: 0.3,  eps: 0.30 },
        shock:       { climate: "shock",   detect: 0.3,  eps: 0.30 },
        strong:      { climate: "shock",   detect: 0.9,  eps: 0.30 },
      };
      const p = map[preset];
      if (!p) return;
      ui.pClimate.value = p.climate;
      ui.pDetect.value = p.detect; paramVal["p-detect"].textContent = p.detect.toFixed(2);
      ui.pEps.value = p.eps;       paramVal["p-eps"].textContent = p.eps.toFixed(2);
      doSetup();
    });
  });
}

// ---------- Init ----------------------------------------------------------

window.addEventListener("error", (ev) => {
  const msg = `Error: ${ev.message}\nat ${ev.filename}:${ev.lineno}`;
  console.error(msg);
  if (ui.loading.style.display !== "none") {
    ui.loadingStatus.innerHTML = `<span style="color:#dc2626">${msg}</span>`;
  }
});
window.addEventListener("unhandledrejection", (ev) => {
  const msg = `Promise rejection: ${ev.reason}`;
  console.error(msg);
  if (ui.loading.style.display !== "none") {
    ui.loadingStatus.innerHTML = `<span style="color:#dc2626">${msg}</span>`;
  }
});

(async () => {
  bindParamDisplay();
  bindControls();
  bindPresets();
  initChart();
  try {
    await bootstrap();
    // Auto-setup with default params for instant gratification.
    await doSetup();
  } catch (e) {
    ui.loadingStatus.innerHTML = `<span style="color:#dc2626">Failed to load: ${e.message || e}</span>`;
    console.error(e);
  }
})();
