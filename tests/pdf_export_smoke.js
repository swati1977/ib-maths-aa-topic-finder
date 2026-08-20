const fs = require("fs");
const vm = require("vm");

let savedName = "";
const renderedText = [];
let renderedImages = 0;

class MockPdf {
  addFileToVFS() {}
  addFont() {}
  setFont() {}
  addPage() {}
  setFontSize() {}
  text(value) { renderedText.push(String(value)); }
  splitTextToSize(value) { return [String(value)]; }
  addImage() { renderedImages += 1; }
  save(name) { savedName = name; }
}

global.window = { jspdf: { jsPDF: MockPdf } };
global.document = {
  addEventListener() {},
  querySelector() { return null; },
  querySelectorAll() { return []; },
  createElement(tag) {
    if (tag === "canvas") {
      return {
        width: 0,
        height: 0,
        getContext() { return { drawImage() {} }; },
        toDataURL() { return "data:image/jpeg;base64,AA=="; }
      };
    }
    return {};
  }
};
global.fetch = async () => ({ ok: true, arrayBuffer: async () => new Uint8Array([0, 1, 2]).buffer });
global.btoa = value => Buffer.from(value, "binary").toString("base64");

global.Image = class {
  constructor() { this.naturalWidth = 1200; this.naturalHeight = 800; }
  set src(value) { this._src = value; queueMicrotask(() => this.onload()); }
};

const app = fs.readFileSync("site/app.js", "utf8") + "\n;globalThis.__exportMatchingQuestions = exportMatchingQuestions; globalThis.__state = state;";
vm.runInThisContext(app, { filename: "site/app.js" });

const question = {
  id: "smoke-q1",
  session: "May",
  year: 2026,
  paper: 1,
  subject: "Mathematics: analysis and approaches SL",
  zone: "A",
  number: 1,
  labels: ["Differentiation"],
  accessibleText: "1. [Maximum mark: 2] Find f′(x). [2]",
  solution: "Differentiate term by term.",
  questionImages: [],
  diagramImages: []
};

(async () => {
  __state.questions = [question];
  await __exportMatchingQuestions("questions", "clean");
  if (!savedName.endsWith(".pdf")) throw new Error("PDF save was not invoked");
  if (!renderedText.some(value => value.includes("Find f′(x)"))) throw new Error("Question text was not rendered");
  if (renderedText.some(value => value.includes("Differentiate term"))) throw new Error("Question-only export included a solution");

  renderedText.length = 0;
  await __exportMatchingQuestions("solutions", "clean");
  if (!renderedText.some(value => value.includes("Differentiate term"))) throw new Error("Solution text was not rendered");

  renderedText.length = 0;
  await __exportMatchingQuestions("both", "clean");
  if (!renderedText.some(value => value.includes("Find f′(x)"))) throw new Error("Combined export omitted the question");
  if (!renderedText.some(value => value.includes("Differentiate term"))) throw new Error("Combined export omitted the solution");

  question.questionImages = ["questions/smoke.webp"];
  renderedImages = 0;
  await __exportMatchingQuestions("questions", "original");
  if (renderedImages !== 1) throw new Error("Original-image export did not render the question image");
  console.log("pdf export smoke passed");
})().catch(error => {
  console.error(error);
  process.exit(1);
});
