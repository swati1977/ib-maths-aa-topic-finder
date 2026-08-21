const TOPICS = [
  "Functions - Roots", "Quadratics", "Exponentials - Logarithms", "Graphs",
  "Sequences - Series", "Complex Numbers", "Permutation - Combination",
  "Binomial Theorem", "Remainder & Factor Theorem", "Mathematical Induction",
  "Radian", "Trigonometry", "Matrices", "Vectors - Lines - Planes",
  "Statistics", "Probability", "Differentiation", "Integration",
  "Differential Equations", "Kinematics"
];

const PAGE_SIZE = 24;

const state = {
  questions: [], topics: new Set(), papers: new Set(), zones: new Set(),
  years: new Set(), sessions: new Set(), subjects: new Set(), query: "", sort: "paper",
  visibleLimit: PAGE_SIZE
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

function formatSubject(subject) {
  return subject.includes("analysis and approaches") ? "Math AA SL" : "Mathematics SL";
}

function buildDynamicFilters(questions) {
  const years = [...new Set(questions.map(q => q.year))].sort((a, b) => b - a);
  const sessions = [...new Set(questions.map(q => q.session))].sort();
  const subjects = [...new Set(questions.map(q => q.subject))].sort();
  const zones = [...new Set(questions.map(q => q.zone))].sort();
  years.forEach(year => appendCheckbox($("#year-filters"), "year", year, String(year)));
  sessions.forEach(session => appendCheckbox($("#session-filters"), "session", session, session));
  subjects.forEach(subject => appendCheckbox($("#subject-filters"), "subject", subject, formatSubject(subject)));
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
  state.subjects = selectedValues("subject");
  state.query = $("#search").value.trim().toLowerCase();
  state.sort = $("#sort").value;
}

function filteredQuestions() {
  const items = state.questions.filter(q => {
    const matchesPaper = !state.papers.size || state.papers.has(String(q.paper));
    const matchesZone = !state.zones.size || state.zones.has(q.zone);
    const matchesYear = !state.years.size || state.years.has(String(q.year));
    const matchesSession = !state.sessions.size || state.sessions.has(q.session);
    const matchesSubject = !state.subjects.size || state.subjects.has(q.subject);
    const matchesTopic = !state.topics.size || q.labels.some(label => state.topics.has(label));
    const haystack = `${q.accessibleText} ${q.labels.join(" ")} ${q.subject} paper ${q.paper} zone ${q.zone} ${q.session} ${q.year}`.toLowerCase();
    return matchesPaper && matchesZone && matchesYear && matchesSession && matchesSubject && matchesTopic && (!state.query || haystack.includes(state.query));
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
    ...[...state.subjects].map(value => ["subject", value, formatSubject(value)]),
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
      update(true);
    });
    host.append(button);
  });
}

function buildPaperUrl(q) {
  return `${q.pdfUrl}#page=${q.pages[0]}&view=FitH&toolbar=1&navpanes=0`;
}

function answerText(q) {
  return q.independentSolution || q.solution;
}

function buildMarkschemeUrl(q) {
  const page = q.officialMarkscheme?.pages?.[0];
  return `${q.markschemeUrl}#page=${page}&view=FitH&toolbar=1&navpanes=0`;
}

function renderQuestionImages(host, q) {
  host.replaceChildren();
  q.questionImages.forEach((src, index) => {
    const figure = document.createElement("figure");
    const caption = document.createElement("figcaption");
    const image = document.createElement("img");
    figure.className = "question-image-page";
    const reconstructed = q.imageStatus === "verified reconstruction";
    caption.textContent = reconstructed
      ? `Question ${q.number} · verified reconstruction · page ${q.displayPages[index]}`
      : `Question ${q.number} · source page ${q.displayPages[index]}`;
    image.className = "question-image";
    image.src = src;
    image.alt = reconstructed
      ? `Verified reconstruction of Paper ${q.paper} ${formatZone(q.zone)}, question ${q.number}, page ${q.displayPages[index]}`
      : `Original Paper ${q.paper} ${formatZone(q.zone)}, question ${q.number}, source page ${q.displayPages[index]}`;
    image.loading = "lazy";
    image.decoding = "async";
    figure.append(caption, image);
    host.append(figure);
  });
}

function renderMarkschemeImages(host, q) {
  host.replaceChildren();
  q.officialMarkscheme.images.forEach((src, index) => {
    const figure = document.createElement("figure");
    const caption = document.createElement("figcaption");
    const image = document.createElement("img");
    figure.className = "markscheme-image-page";
    caption.textContent = `Official IB markscheme · Question ${q.number} · page ${q.officialMarkscheme.pages[index]}`;
    image.className = "markscheme-image";
    image.src = src;
    image.alt = `Official IB markscheme for Paper ${q.paper} ${formatZone(q.zone)}, question ${q.number}, page ${q.officialMarkscheme.pages[index]}`;
    image.loading = "lazy";
    image.decoding = "async";
    figure.append(caption, image);
    host.append(figure);
  });
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

const VISUAL_DESCRIPTION_PATTERN = /\[[^\]]*\b(?:Diagram|Graph|Table|Box|Coordinate|Probability|Frequency|Scatter|Histogram|Circle|Curve|Tree|Venn|Sample|Triangle|Grid|Cumulative|Axis|Set|Blank|Sign|Normal|Cuboid|Velocity|Displacement|Sine|Slope)\b[^\]]*\]/gi;
let pdfFontPromise;

function stripVisualDescriptions(text) {
  return text.replace(VISUAL_DESCRIPTION_PATTERN, "").replace(/\n{3,}/g, "\n\n").trim();
}

function arrayBufferToBase64(buffer) {
  const bytes = new Uint8Array(buffer);
  let binary = "";
  for (let start = 0; start < bytes.length; start += 0x8000) {
    binary += String.fromCharCode(...bytes.subarray(start, start + 0x8000));
  }
  return btoa(binary);
}

async function loadPdfFont(doc) {
  pdfFontPromise ||= fetch("vendor/DejaVuSans.ttf")
    .then(response => {
      if (!response.ok) throw new Error(`Font HTTP ${response.status}`);
      return response.arrayBuffer();
    })
    .then(arrayBufferToBase64);
  const font = await pdfFontPromise;
  doc.addFileToVFS("DejaVuSans.ttf", font);
  doc.addFont("DejaVuSans.ttf", "DejaVu", "normal");
  doc.setFont("DejaVu", "normal");
}

function beginPdfPage(doc, pageState) {
  if (pageState.used) doc.addPage();
  pageState.used = true;
}

function addPdfTextSection(doc, pageState, heading, text) {
  beginPdfPage(doc, pageState);
  const margin = 16;
  const maxWidth = 210 - 2 * margin;
  let y = 18;
  doc.setFontSize(13);
  doc.text(heading, margin, y);
  y += 9;
  doc.setFontSize(9.5);
  const paragraphs = text.split(/\n+/).map(value => value.trim()).filter(Boolean);
  paragraphs.forEach(paragraph => {
    const lines = doc.splitTextToSize(paragraph, maxWidth);
    lines.forEach(line => {
      if (y > 282) {
        doc.addPage();
        y = 18;
      }
      doc.text(line, margin, y);
      y += 5;
    });
    y += 2;
  });
}

function loadPdfImage(url) {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => {
      const canvas = document.createElement("canvas");
      canvas.width = image.naturalWidth;
      canvas.height = image.naturalHeight;
      canvas.getContext("2d").drawImage(image, 0, 0);
      resolve({ data: canvas.toDataURL("image/jpeg", 0.92), width: image.naturalWidth, height: image.naturalHeight });
    };
    image.onerror = () => reject(new Error(`Could not load question image: ${url}`));
    image.src = url;
  });
}

async function addPdfImagePage(doc, pageState, heading, url) {
  const image = await loadPdfImage(url);
  beginPdfPage(doc, pageState);
  const margin = 10;
  doc.setFontSize(10);
  doc.text(heading, margin, 10);
  const maxWidth = 210 - 2 * margin;
  const maxHeight = 297 - 24;
  const scale = Math.min(maxWidth / image.width, maxHeight / image.height);
  const width = image.width * scale;
  const height = image.height * scale;
  doc.addImage(image.data, "JPEG", (210 - width) / 2, 15, width, height, undefined, "FAST");
}

function questionHeading(q, suffix = "") {
  return `${q.session} ${q.year} · ${formatSubject(q.subject)} · Paper ${q.paper} ${formatZone(q.zone)} · Question ${q.number}${suffix}`;
}

function hasOriginalVisual(q) {
  return /\[(?:Diagram|Graph|Table|Box|Coordinate|Probability|Frequency|Scatter|Histogram|Circle|Curve)/i.test(q.accessibleText);
}

function renderAccessibleQuestion(host, q) {
  const images = q.diagramImages?.length ? q.diagramImages : q.questionImages;
  if (!hasOriginalVisual(q) || !images?.length) {
    host.textContent = q.accessibleText;
    return;
  }
  let cursor = 0;
  for (const match of q.accessibleText.matchAll(VISUAL_DESCRIPTION_PATTERN)) {
    host.append(document.createTextNode(q.accessibleText.slice(cursor, match.index)));
    const description = document.createElement("span");
    description.className = "visual-description sr-only";
    description.textContent = match[0];
    host.append(description);
    cursor = match.index + match[0].length;
  }
  host.append(document.createTextNode(q.accessibleText.slice(cursor)));
}

function renderInlineVisuals(host, q) {
  const images = q.diagramImages?.length ? q.diagramImages : q.questionImages;
  if (!hasOriginalVisual(q) || !images?.length) {
    host.remove();
    return;
  }
  images.forEach((src, index) => {
    const figure = document.createElement("figure");
    const image = document.createElement("img");
    const caption = document.createElement("figcaption");
    figure.className = "question-visual";
    image.className = "question-visual-image";
    image.src = src;
    image.alt = q.imageStatus === "verified reconstruction"
      ? `Verified reconstructed visual for Paper ${q.paper} ${formatZone(q.zone)}, question ${q.number}${images.length > 1 ? `, part ${index + 1}` : ""}`
      : `Original visual for Paper ${q.paper} ${formatZone(q.zone)}, question ${q.number}${images.length > 1 ? `, part ${index + 1}` : ""}`;
    image.loading = "lazy";
    image.decoding = "async";
    caption.textContent = q.imageStatus === "verified reconstruction"
      ? "Verified reconstruction from alternate source text"
      : "Original diagram / table from the source question";
    figure.append(image, caption);
    host.append(figure);
  });
}

async function exportMatchingQuestions(contentMode, formatMode) {
  const items = filteredQuestions();
  if (!items.length) throw new Error("No matching questions to export.");
  if (!window.jspdf?.jsPDF) throw new Error("PDF engine did not load.");

  const { jsPDF } = window.jspdf;
  const doc = new jsPDF({ unit: "mm", format: "a4", compress: true });
  await loadPdfFont(doc);
  const pageState = { used: false };

  for (const q of items) {
    const includeQuestions = contentMode !== "solutions";
    const includeSolutions = contentMode !== "questions";
    if (includeQuestions && formatMode === "original" && q.questionImages?.length) {
      for (const image of q.questionImages) {
        await addPdfImagePage(doc, pageState, questionHeading(q), image);
      }
    } else if (includeQuestions) {
      addPdfTextSection(doc, pageState, questionHeading(q), stripVisualDescriptions(q.accessibleText));
      const visualImages = q.diagramImages?.length ? q.diagramImages : (hasOriginalVisual(q) ? q.questionImages : []);
      for (const image of visualImages) {
        await addPdfImagePage(doc, pageState, questionHeading(q, " · original visual"), image);
      }
    }
    if (includeSolutions) {
      if (q.officialMarkscheme?.images?.length) {
        for (const image of q.officialMarkscheme.images) {
          await addPdfImagePage(doc, pageState, questionHeading(q, " · official markscheme"), image);
        }
      } else {
        addPdfTextSection(doc, pageState, questionHeading(q, " · independent solution"), answerText(q));
      }
    }
  }

  doc.save(`math-practice-${contentMode}-${formatMode}-${items.length}-questions.pdf`);
}

function renderQuestion(q) {
  const card = $("#question-template").content.firstElementChild.cloneNode(true);
  card.dataset.questionId = q.id;
  card.querySelector(".paper-badge").textContent = `${formatSubject(q.subject)} · Paper ${q.paper} · ${formatZone(q.zone)}`;
  card.querySelector(".question-meta").textContent = `Question ${q.number} · ${q.session} ${q.year} · page${q.pages.length > 1 ? "s" : ""} ${q.pages.join("–")}`;
  card.querySelector(".marks").textContent = `${q.marks} mark${q.marks === 1 ? "" : "s"}`;
  card.querySelector("h3").textContent = `Question ${q.number}`;
  renderQuestionImages(card.querySelector(".question-primary-images"), q);
  renderAccessibleQuestion(card.querySelector(".question-text"), q);
  const labels = card.querySelector(".labels");
  q.labels.forEach(text => {
    const span = document.createElement("span");
    span.className = "label";
    span.textContent = text;
    labels.append(span);
  });
  const paperLink = card.querySelector(".paper-link");
  paperLink.href = buildPaperUrl(q);
  paperLink.setAttribute("aria-label", `Open source Paper ${q.paper} ${formatZone(q.zone)}, question ${q.number}`);
  if (!q.viewerAvailable) {
    paperLink.href = q.sourceUrl;
    paperLink.textContent = "Open source record ↗";
    paperLink.setAttribute("aria-label", `Open source record for Paper ${q.paper} ${formatZone(q.zone)}, question ${q.number}`);
  }

  const solution = card.querySelector(".solution");
  const solutionButton = card.querySelector(".solution-button");
  const answerTitle = card.querySelector(".answer-title");
  const answerNote = card.querySelector(".answer-note");
  const markschemeLink = card.querySelector(".markscheme-link");
  const solutionId = `solution-${q.id}`;
  solution.id = solutionId;
  solutionButton.setAttribute("aria-controls", solutionId);
  if (q.officialMarkscheme) {
    renderMarkschemeImages(card.querySelector(".markscheme-images"), q);
    renderSolutionParts(card.querySelector(".official-accessible-content"), answerText(q));
    card.querySelector(".solution-content").remove();
    solutionButton.textContent = "View official markscheme";
    answerTitle.textContent = "Official IB markscheme";
    answerNote.textContent = `Question ${q.number} · markscheme page${q.officialMarkscheme.pages.length > 1 ? "s" : ""} ${q.officialMarkscheme.pages.join("–")}`;
    if (q.markschemeUrl) {
      markschemeLink.hidden = false;
      markschemeLink.href = buildMarkschemeUrl(q);
      markschemeLink.textContent = `Open full official markscheme at page ${q.officialMarkscheme.pages[0]} ↗`;
    }
  } else {
    card.querySelector(".markscheme-images").remove();
    card.querySelector(".official-accessible-answer").remove();
    renderSolutionParts(card.querySelector(".solution-content"), answerText(q));
    solutionButton.textContent = "View independent solution";
    answerTitle.textContent = "Independent worked solution — official markscheme unavailable";
    answerNote.textContent = "Not an official IB markscheme";
  }
  solutionButton.addEventListener("click", () => {
    const opening = solution.hidden;
    solution.hidden = !opening;
    solutionButton.textContent = opening ? "Hide answer" : (q.officialMarkscheme ? "View official markscheme" : "View independent solution");
    solutionButton.setAttribute("aria-expanded", String(opening));
  });
  return card;
}

function update(resetLimit = false) {
  if (resetLimit) state.visibleLimit = PAGE_SIZE;
  syncState();
  const items = filteredQuestions();
  $("#visible-count").textContent = items.length;
  const renderedItems = items.slice(0, state.visibleLimit);
  $("#questions").replaceChildren(...renderedItems.map(renderQuestion));
  $("#empty-state").hidden = items.length !== 0;
  $("#load-more").hidden = renderedItems.length >= items.length;
  renderActiveFilters();
}

function clearFilters() {
  $$("input[type=checkbox]").forEach(input => { input.checked = false; });
  $("#search").value = "";
  $("#sort").value = "paper";
  update(true);
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

  $("#search").addEventListener("input", () => update(true));
  $("#sort").addEventListener("change", () => update(true));
  $(".filters").addEventListener("change", () => update(true));
  $("#clear-filters").addEventListener("click", clearFilters);
  $("[data-clear]").addEventListener("click", clearFilters);
  $("#load-more").addEventListener("click", () => {
    state.visibleLimit += PAGE_SIZE;
    update();
  });
  $("#toggle-filters").addEventListener("click", event => {
    const opening = !$(".filters").classList.contains("filters-open");
    $(".filters").classList.toggle("filters-open", opening);
    event.currentTarget.textContent = opening ? "Hide filters" : "Show filters";
    event.currentTarget.setAttribute("aria-expanded", String(opening));
  });

  const exportDialog = $("#pdf-export-dialog");
  const exportStatus = $("#pdf-export-status");
  const exportButton = $("#generate-pdf");
  $("#download-pdf").addEventListener("click", () => {
    exportStatus.textContent = `${filteredQuestions().length} matching questions will be included.`;
    exportDialog.showModal();
  });
  $("#pdf-content").addEventListener("change", event => {
    $("#pdf-format").disabled = event.target.value === "solutions";
  });
  exportButton.addEventListener("click", async () => {
    exportButton.disabled = true;
    exportStatus.textContent = "Generating PDF…";
    try {
      await exportMatchingQuestions($("#pdf-content").value, $("#pdf-format").value);
      exportStatus.textContent = "PDF downloaded.";
    } catch (error) {
      exportStatus.textContent = error.message;
    } finally {
      exportButton.disabled = false;
    }
  });
}

document.addEventListener("DOMContentLoaded", init);
