const $ = (id) => document.getElementById(id);

const stateText = {
  CLEAR: "CLEAR",
  WATCH: "WATCH",
  TRIGGERED: "TRIGGERED",
};

const stateMeaning = {
  CLEAR: "尚未形成反轉訊號",
  WATCH: "已有早期跡象，持續追蹤",
  TRIGGERED: "條件已明顯成立",
};

function clamp(n, min = 0, max = 100) {
  return Math.min(max, Math.max(min, Number(n) || 0));
}

function phaseSummary(score, phase) {
  if (score >= 85) return `目前為「${phase}」。多數反轉條件已成立，接近全面供過於求。`;
  if (score >= 70) return `目前為「${phase}」。下跌週期風險偏高，需特別注意庫存與廠商降價。`;
  if (score >= 50) return `目前為「${phase}」。需求、庫存與供給已有多項反轉條件同時成立。`;
  if (score >= 30) return `目前為「${phase}」。市場進入築頂觀察區，但尚未確認全面熊市。`;
  return `目前為「${phase}」。供應仍偏緊，距離 2022–2023 式全面下跌仍有距離。`;
}

function renderEvents(events = []) {
  const grid = $("eventGrid");
  if (!events.length) {
    grid.innerHTML = '<div class="error-box">目前沒有事件資料。</div>';
    return;
  }

  grid.innerHTML = events.map((event, index) => {
    const state = stateText[event.state] || "CLEAR";
    const weight = Number(event.weight || 0);
    const multiplier = Number(event.multiplier || 0);
    const contribution = Math.round(weight * multiplier * 10) / 10;
    return `
      <article class="event-card" data-state="${state}">
        <div class="event-top">
          <span class="event-index">EVENT ${String(index + 1).padStart(2, "0")}</span>
          <span class="state-pill">${state}</span>
        </div>
        <h3>${escapeHtml(event.label_zh || event.id || "未命名事件")}</h3>
        <p class="event-note">${escapeHtml(event.note_zh || stateMeaning[state])}</p>
        <div class="event-foot">
          <span>${stateMeaning[state]}</span>
          <strong>權重 ${weight} · 貢獻 ${contribution}</strong>
        </div>
      </article>`;
  }).join("");

  const watches = events.filter((e) => e.state === "WATCH").length;
  const triggered = events.filter((e) => e.state === "TRIGGERED").length;
  $("watchCount").textContent = watches + triggered;
  $("triggerCountText").textContent = triggered
    ? `其中 ${triggered} 項已 TRIGGERED，${watches} 項仍在 WATCH。`
    : `目前 ${watches} 項 WATCH，尚無事件正式 TRIGGERED。`;
}

function renderEvidence(items = []) {
  const list = $("evidenceList");
  if (!items.length) {
    list.innerHTML = '<div class="error-box">目前沒有證據來源。</div>';
    return;
  }
  list.innerHTML = items.map((item) => `
    <a class="evidence-item" href="${escapeAttr(item.url || "#")}" target="_blank" rel="noopener noreferrer">
      <strong>${escapeHtml(item.title || "Evidence source")}</strong>
      <span>↗</span>
    </a>`).join("");
}

function parseCsv(text) {
  const rows = text.trim().split(/\r?\n/).filter(Boolean);
  if (rows.length < 2) return [];
  const header = rows[0].split(",");
  return rows.slice(1).map((line) => {
    const cols = splitCsvLine(line);
    return Object.fromEntries(header.map((key, idx) => [key, cols[idx] ?? ""]));
  });
}

function splitCsvLine(line) {
  const out = [];
  let value = "";
  let quoted = false;
  for (let i = 0; i < line.length; i += 1) {
    const ch = line[i];
    if (ch === '"') {
      if (quoted && line[i + 1] === '"') {
        value += '"';
        i += 1;
      } else {
        quoted = !quoted;
      }
    } else if (ch === "," && !quoted) {
      out.push(value);
      value = "";
    } else {
      value += ch;
    }
  }
  out.push(value);
  return out;
}

function renderHistory(rows) {
  const target = $("historyChart");
  const valid = rows
    .map((r) => ({ date: r.as_of, score: Number(r.downturn_readiness) }))
    .filter((r) => r.date && Number.isFinite(r.score));

  $("historyCount").textContent = `${valid.length} 筆`;
  if (valid.length < 2) {
    target.innerHTML = '<div class="chart-empty">目前只有 1 筆基準資料。每日自動更新後，這裡會逐步形成週期趨勢曲線。</div>';
    return;
  }

  const width = 760;
  const height = 260;
  const left = 42;
  const right = 14;
  const top = 12;
  const bottom = 34;
  const innerW = width - left - right;
  const innerH = height - top - bottom;
  const x = (i) => left + (valid.length === 1 ? 0 : (i / (valid.length - 1)) * innerW);
  const y = (score) => top + innerH - (clamp(score) / 100) * innerH;
  const points = valid.map((r, i) => `${x(i)},${y(r.score)}`);
  const linePath = `M ${points.join(" L ")}`;
  const areaPath = `${linePath} L ${x(valid.length - 1)},${top + innerH} L ${x(0)},${top + innerH} Z`;
  const gridLevels = [0, 25, 50, 75, 100];
  const tickIndices = [...new Set([0, Math.floor((valid.length - 1) / 2), valid.length - 1])];

  target.innerHTML = `
    <svg class="chart-svg" viewBox="0 0 ${width} ${height}" role="img" aria-label="下跌準備度歷史曲線">
      <defs>
        <linearGradient id="areaGradient" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#56d6ff" stop-opacity="0.24"/>
          <stop offset="100%" stop-color="#56d6ff" stop-opacity="0"/>
        </linearGradient>
      </defs>
      ${gridLevels.map((level) => `
        <line class="chart-grid" x1="${left}" y1="${y(level)}" x2="${width - right}" y2="${y(level)}" />
        <text class="chart-label" x="2" y="${y(level) + 4}">${level}</text>`).join("")}
      <path class="chart-area" d="${areaPath}" />
      <path class="chart-path" d="${linePath}" />
      ${valid.map((r, i) => `<circle class="chart-dot" cx="${x(i)}" cy="${y(r.score)}" r="4"><title>${escapeHtml(r.date)}：${r.score}</title></circle>`).join("")}
      ${tickIndices.map((i) => `<text class="chart-label" text-anchor="${i === 0 ? "start" : i === valid.length - 1 ? "end" : "middle"}" x="${x(i)}" y="${height - 8}">${formatShortDate(valid[i].date)}</text>`).join("")}
    </svg>`;
}

function formatShortDate(date) {
  const m = String(date).match(/^(\d{4})-(\d{2})-(\d{2})$/);
  return m ? `${m[2]}/${m[3]}` : date;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function escapeAttr(value) {
  const text = String(value ?? "").trim();
  if (!/^https?:\/\//i.test(text)) return "#";
  return escapeHtml(text);
}

async function fetchNoCache(path, asText = false) {
  const sep = path.includes("?") ? "&" : "?";
  const response = await fetch(`${path}${sep}t=${Date.now()}`, { cache: "no-store" });
  if (!response.ok) throw new Error(`${path}: HTTP ${response.status}`);
  return asText ? response.text() : response.json();
}

async function loadDashboard() {
  $("footerStatus").textContent = "Updating…";
  try {
    const [latest, historyText] = await Promise.all([
      fetchNoCache("./data/latest.json"),
      fetchNoCache("./data/history/daily.csv", true),
    ]);

    const score = clamp(latest?.scores?.downturn_readiness);
    const phase = latest?.scores?.phase || "未分類";
    const eventScore = clamp(latest?.scores?.event_score);

    $("asOf").textContent = latest.as_of || "--";
    $("scoreValue").textContent = Number.isInteger(score) ? score : score.toFixed(1);
    $("scoreRing").style.setProperty("--score", score);
    $("phaseBadge").textContent = phase;
    $("scoreSummary").textContent = phaseSummary(score, phase);
    $("eventScore").textContent = Number.isInteger(eventScore) ? eventScore : eventScore.toFixed(1);

    renderEvents(latest.events || []);
    renderEvidence(latest.evidence_sources || []);
    renderHistory(parseCsv(historyText));

    $("footerStatus").textContent = `Last data: ${latest.as_of || "unknown"}`;
  } catch (error) {
    console.error(error);
    $("footerStatus").textContent = "Data load failed";
    $("eventGrid").innerHTML = `<div class="error-box">資料載入失敗：${escapeHtml(error.message)}。請稍後重新整理，或檢查 GitHub Actions 是否更新成功。</div>`;
  }
}

$("refreshBtn").addEventListener("click", loadDashboard);
window.addEventListener("DOMContentLoaded", loadDashboard);
