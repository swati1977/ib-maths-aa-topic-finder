const TOPICS = [
  "Functions - Roots", "Quadratics", "Exponentials - Logarithms", "Graphs",
  "Sequences - Series", "Complex Numbers", "Permutation - Combination",
  "Binomial Theorem", "Remainder & Factor Theorem", "Mathematical Induction",
  "Radian", "Trigonometry", "Matrices", "Vectors - Lines - Planes",
  "Statistics", "Probability", "Differentiation", "Integration",
  "Differential Equations", "Kinematics"
];

const state = {
  questions: [], topics: new Set(), papers: new Set(), zones: new Set(),
  years: new Set(), sessions: new Set(), query: "", sort: "paper"
};
const $ = selector => document.querySelector(selector);
const $$ = selector => [...document.querySelectorAll(selector)];

function buildTopicFilters() {
  const host = $("#topic-filters");
  TOPICS.forEach(topic => {
    const label = document.createElement("label");
    const input = document.createElement("input");
    const text = document.createElement("span");
    label.className = "check-row";
    input.type = "checkbox";
    input.name = "topic";
    input.value = topic;
    text.textContent = topic;
    label.append(input, text);
    host.append(label);
  });
}

function appendCheckbox(host, name, value, text) {
  const label = document.createElement("label");
  const input = document.createElement("input");
  const caption = document.createElement("span");
  label.className = "check-row";
  input.type = "checkbox";
  input.name = name;
  input.value = String(value);
  caption.textContent = text;
  label.append(input, caption);
  host.append(label);
}

function formatZone(zone) {
  if (/^\d+$/.test(zone)) return `TZ${zone}`;
  if (zone === "N") return "Single zone";
  return `Zone ${zone}`;
}

function buildDynamicFilters(questions) {
  const years = [...new Set(questions.map(q => q.year))].sort((a, b) => b - a);
  const sessions = [...new Set(questions.map(q => q.session))].sort();
  const zones = [...new Set(questions.map(q => q.zone))].sort();
  years.forEach(year => appendCheckbox($("#year-filters"), "year", year, String(year)));
  sessions.forEach(session => appendCheckbox($("#session-filters"), "session", session, session));
  zones.forEach(zone => appendCheckbox($("#zone-filters"), "zone", zone, formatZone(zone)));
}

function selectedValues(name) {
  return new Set($$(`input[name="${name}"]:checked`).map(input => input.value));
}

function syncState() {
  state.topics = selectedValues("topic");
  state.papers = selectedValues("paper");
  state.zones = selectedValues("zone");
  state.years = selectedValues("year");
  state.sessions = selectedValues("session");
  state.query = $("#search").value.trim().toLowerCase();
  state.sort = $("#sort").value;
}

function filteredQuestions() {
  const items = state.questions.filter(q => {
    const matchesPaper = !state.papers.size || state.papers.has(String(q.paper));
    const matchesZone = !state.zones.size || state.zones.has(q.zone);
    const matchesYear = !state.years.size || state.years.has(String(q.year));
    const matchesSession = !state.sessions.size || state.sessions.has(q.session);
    const matchesTopic = !state.topics.size || q.labels.some(label => state.topics.has(label));
    const haystack = `${q.accessibleText} ${q.labels.join(" ")} paper ${q.paper} zone ${q.zone} ${q.session} ${q.year}`.toLowerCase();
    return matchesPaper && matchesZone && matchesYear && matchesSession && matchesTopic && (!state.query || haystack.includes(state.query));
  });

  return items.sort((a, b) => {
    if (state.sort === "marks-desc") return b.marks - a.marks || a.id.localeCompare(b.id);
    if (state.sort === "marks-asc") return a.marks - b.marks || a.id.localeCompare(b.id);
    if (state.sort === "topic") return a.labels[0].localeCompare(b.labels[0]) || a.id.localeCompare(b.id);
    return b.year - a.year || a.session.localeCompare(b.session) || a.paper - b.paper || a.zone.localeCompare(b.zone) || a.number - b.number;
  });
}

function renderActiveFilters() {
  const host = $("#active-filters");
  host.replaceChildren();
  const chips = [
    ...[...state.papers].map(value => ["paper", value, `Paper ${value}`]),
    ...[...state.years].map(value => ["year", value, value]),
    ...[...state.sessions].map(value => ["session", value, value]),
    ...[...state.zones].map(value => ["zone", value, formatZone(value)]),
    ...[...state.topics].map(value => ["topic", value, value])
  ];
  if (state.query) chips.unshift(["search", state.query, `Search: ${state.query}`]);
  chips.forEach(([type, value, text]) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "filter-chip";
    button.textContent = `${text} ×`;
    button.addEventListener("click", () => {
      if (type === "search") $("#search").value = "";
      else {
        const input = $$(`input[name="${type}"]`).find(node => node.value === value);
        if (input) input.checked = false;
      }
      update();
    });
    host.append(button);
  });
}

function buildPaperUrl(q) {
  return `${q.pdfUrl}#page=${q.pages[0]}&view=FitH&toolbar=1&navpanes=0`;
}

function renderSolutionParts(host, text) {
  const markerPattern = /(?<!\S)(\([a-h]\)(?:\((?:i{1,3}|iv)\))?|\((?:i{1,3}|iv)\))(?=\s)/gi;
  const matches = [...text.matchAll(markerPattern)];
  host.replaceChildren();

  if (!matches.length) {
    const paragraph = document.createElement("p");
    paragraph.className = "solution-part";
    paragraph.textContent = text;
    host.append(paragraph);
    return;
  }

  const preamble = text.slice(0, matches[0].index).trim();
  if (preamble) {
    const paragraph = document.createElement("p");
    paragraph.className = "solution-part";
    paragraph.textContent = preamble;
    host.append(paragraph);
  }

  matches.forEach((match, index) => {
    const row = document.createElement("div");
    const label = document.createElement("span");
    const body = document.createElement("p");
    const start = match.index + match[0].length;
    const end = index + 1 < matches.length ? matches[index + 1].index : text.length;
    row.className = "solution-part";
    label.className = "solution-part-label";
    label.textContent = match[0];
    body.textContent = text.slice(start, end).trim();
    row.append(label, body);
    host.append(row);
  });
}

function renderQuestion(q) {
  const card = $("#question-template").content.firstElementChild.cloneNode(true);
  card.dataset.questionId = q.id;
  card.querySelector(".paper-badge").textContent = `Paper ${q.paper} · ${formatZone(q.zone)}`;
  card.querySelector(".question-meta").textContent = `Question ${q.number} · ${q.session} ${q.year} · page${q.pages.length > 1 ? "s" : ""} ${q.pages.join("–")}`;
  card.querySelector(".marks").textContent = `${q.marks} mark${q.marks === 1 ? "" : "s"}`;
  card.querySelector("h3").textContent = `Question ${q.number}`;
  card.querySelector(".question-text").textContent = q.accessibleText;
  const labels = card.querySelector(".labels");
  q.labels.forEach(text => {
    const span = document.createElement("span");
    span.className = "label";
    span.textContent = text;
    labels.append(span);
  });
  const paperLink = card.querySelector(".paper-link");
  paperLink.href = buildPaperUrl(q);
  paperLink.setAttribute("aria-label", `View exact Paper ${q.paper} ${formatZone(q.zone)}, question ${q.number}`);
  if (!q.viewerAvailable) {
    paperLink.href = q.sourceUrl;
    paperLink.textContent = "View source record ↗";
    paperLink.setAttribute("aria-label", `View source record for Paper ${q.paper} ${formatZone(q.zone)}, question ${q.number}`);
  }

  const solution = card.querySelector(".solution");
  const solutionButton = card.querySelector(".solution-button");
  const solutionId = `solution-${q.id}`;
  solution.id = solutionId;
  solutionButton.setAttribute("aria-controls", solutionId);
  renderSolutionParts(card.querySelector(".solution-content"), q.solution);
  solutionButton.addEventListener("click", () => {
    const opening = solution.hidden;
    solution.hidden = !opening;
    solutionButton.textContent = opening ? "Hide solution" : "Show solution";
    solutionButton.setAttribute("aria-expanded", String(opening));
  });
  return card;
}

function update() {
  syncState();
  const items = filteredQuestions();
  $("#visible-count").textContent = items.length;
  $("#questions").replaceChildren(...items.map(renderQuestion));
  $("#empty-state").hidden = items.length !== 0;
  renderActiveFilters();
}

function clearFilters() {
  $$("input[type=checkbox]").forEach(input => { input.checked = false; });
  $("#search").value = "";
  $("#sort").value = "paper";
  update();
}

async function init() {
  buildTopicFilters();
  try {
    const response = await fetch("data/questions.json");
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const payload = await response.json();
    state.questions = payload.questions;
    buildDynamicFilters(payload.questions);
    $("#question-count").textContent = payload.questions.length;
    $("#paper-count").textContent = payload.papers.length;
    update();
  } catch (error) {
    const failure = document.createElement("div");
    const heading = document.createElement("h3");
    const detail = document.createElement("p");
    failure.className = "empty-state";
    heading.textContent = "Question data could not be loaded";
    detail.textContent = error.message;
    failure.append(heading, detail);
    $("#questions").replaceChildren(failure);
    $("#visible-count").textContent = "0";
    $("#question-count").textContent = "0";
    $("#paper-count").textContent = "0";
  }

  $("#search").addEventListener("input", update);
  $("#sort").addEventListener("change", update);
  $(".filters").addEventListener("change", update);
  $("#clear-filters").addEventListener("click", clearFilters);
  $("[data-clear]").addEventListener("click", clearFilters);
}

document.addEventListener("DOMContentLoaded", init);
