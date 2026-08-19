const TOPICS = [
  "Functions - Roots", "Quadratics", "Exponentials - Logarithms", "Graphs",
  "Sequences - Series", "Complex Numbers", "Permutation - Combination",
  "Binomial Theorem", "Remainder & Factor Theorem", "Mathematical Induction",
  "Radian", "Trigonometry", "Matrices", "Vectors - Lines - Planes",
  "Statistics", "Probability", "Differentiation", "Integration",
  "Differential Equations", "Kinematics"
];

const state = { questions: [], topics: new Set(), papers: new Set(), zones: new Set(), query: "", sort: "paper" };
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

function selectedValues(name) {
  return new Set($$(`input[name="${name}"]:checked`).map(input => input.value));
}

function syncState() {
  state.topics = selectedValues("topic");
  state.papers = selectedValues("paper");
  state.zones = selectedValues("zone");
  state.query = $("#search").value.trim().toLowerCase();
  state.sort = $("#sort").value;
}

function filteredQuestions() {
  const items = state.questions.filter(q => {
    const matchesPaper = !state.papers.size || state.papers.has(String(q.paper));
    const matchesZone = !state.zones.size || state.zones.has(q.zone);
    const matchesTopic = !state.topics.size || q.labels.some(label => state.topics.has(label));
    const haystack = `${q.summary} ${q.labels.join(" ")} paper ${q.paper} zone ${q.zone}`.toLowerCase();
    return matchesPaper && matchesZone && matchesTopic && (!state.query || haystack.includes(state.query));
  });

  return items.sort((a, b) => {
    if (state.sort === "marks-desc") return b.marks - a.marks || a.id.localeCompare(b.id);
    if (state.sort === "marks-asc") return a.marks - b.marks || a.id.localeCompare(b.id);
    if (state.sort === "topic") return a.labels[0].localeCompare(b.labels[0]) || a.id.localeCompare(b.id);
    return a.paper - b.paper || a.zone.localeCompare(b.zone) || a.number - b.number;
  });
}

function renderActiveFilters() {
  const host = $("#active-filters");
  host.replaceChildren();
  const chips = [
    ...[...state.papers].map(value => ["paper", value, `Paper ${value}`]),
    ...[...state.zones].map(value => ["zone", value, `Zone ${value}`]),
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

function renderQuestion(q) {
  const card = $("#question-template").content.firstElementChild.cloneNode(true);
  card.dataset.questionId = q.id;
  card.querySelector(".paper-badge").textContent = `Paper ${q.paper} · Zone ${q.zone}`;
  card.querySelector(".question-meta").textContent = `Question ${q.number} · ${q.year} · page${q.pages.length > 1 ? "s" : ""} ${q.pages.join("–")}`;
  card.querySelector(".marks").textContent = `${q.marks} mark${q.marks === 1 ? "" : "s"}`;
  card.querySelector("h3").textContent = q.summary;
  const labels = card.querySelector(".labels");
  q.labels.forEach(text => {
    const span = document.createElement("span");
    span.className = "label";
    span.textContent = text;
    labels.append(span);
  });
  const paperLink = card.querySelector(".paper-link");
  paperLink.href = `${q.pdfUrl}#page=${q.pages[0]}`;
  paperLink.setAttribute("aria-label", `Open Paper ${q.paper} Zone ${q.zone}, question ${q.number}`);
  const solution = card.querySelector(".solution");
  const button = card.querySelector(".solution-button");
  card.querySelector(".solution-content").textContent = q.solution;
  button.addEventListener("click", () => {
    const opening = solution.hidden;
    solution.hidden = !opening;
    button.textContent = opening ? "Hide solution" : "Show solution";
    button.setAttribute("aria-expanded", String(opening));
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
    $("#question-count").textContent = payload.questions.length;
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
  }

  $("#search").addEventListener("input", update);
  $("#sort").addEventListener("change", update);
  $(".filters").addEventListener("change", update);
  $("#clear-filters").addEventListener("click", clearFilters);
  $("[data-clear]").addEventListener("click", clearFilters);
}

document.addEventListener("DOMContentLoaded", init);
