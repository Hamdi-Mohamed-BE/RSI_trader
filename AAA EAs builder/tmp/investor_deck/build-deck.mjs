import fs from "node:fs/promises";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const OUT = "C:/Users/hama101/Desktop/geek/ai trader/AAA EAs builder/docs/investor/AAA_EAs_Builder_Investor_Briefing.pptx";
const ROOT = "C:/Users/hama101/Desktop/geek/ai trader/AAA EAs builder";
const ASSETS = `${ROOT}/tmp/investor_deck/assets`;

const W = 1280;
const H = 720;
const C = {
  bg: "#040812",
  panel: "#081425",
  panel2: "#0B1A2E",
  ink: "#F4F8FF",
  muted: "#A9B7CC",
  dim: "#64748B",
  cyan: "#10DFF2",
  cyan2: "#0EA5E9",
  violet: "#A855F7",
  green: "#32D583",
  amber: "#F8B84E",
  red: "#FF5277",
  border: "#193452",
  grid: "#0A2034",
};

const presentation = Presentation.create({ slideSize: { width: W, height: H } });

function rect(slide, x, y, w, h, fill, stroke = "none", radius = "rect", name) {
  return slide.shapes.add({
    geometry: radius,
    name,
    position: { left: x, top: y, width: w, height: h },
    fill,
    line: { style: "solid", fill: stroke, width: stroke === "none" ? 0 : 1 },
    ...(radius === "roundRect" ? { borderRadius: "rounded-xl" } : {}),
  });
}

function text(slide, value, x, y, w, h, size = 20, color = C.ink, bold = false, align = "left", name) {
  const shape = slide.shapes.add({
    geometry: "textbox",
    name,
    position: { left: x, top: y, width: w, height: h },
    fill: "none",
    line: { style: "solid", fill: "none", width: 0 },
  });
  shape.text = value;
  shape.text.style = { fontSize: size, color, bold, alignment: align };
  return shape;
}

function label(slide, value, x, y, w, color = C.cyan) {
  text(slide, value.toUpperCase(), x, y, w, 24, 14, color, true);
}

function bullet(slide, value, x, y, w, color = C.ink, marker = C.cyan, size = 18) {
  rect(slide, x, y + 8, 8, 8, marker, "none", "ellipse");
  text(slide, value, x + 22, y, w - 22, 54, size, color, false);
}

function addImage(slide, path, x, y, w, h, alt, fit = "cover") {
  return fs.readFile(path).then((bytes) =>
    slide.images.add({
      blob: bytes,
      contentType: "image/png",
      alt,
      fit,
      geometry: "roundRect",
      borderRadius: "rounded-xl",
      position: { left: x, top: y, width: w, height: h },
    }),
  );
}

function baseSlide(titleValue, section, number) {
  const slide = presentation.slides.add();
  slide.background.fill = C.bg;

  for (let x = 0; x <= W; x += 80) rect(slide, x, 0, 1, H, C.grid);
  for (let y = 0; y <= H; y += 80) rect(slide, 0, y, W, 1, C.grid);
  rect(slide, 0, 0, W, 8, C.cyan);
  label(slide, section, 56, 34, 360);
  text(slide, titleValue, 56, 68, 1168, 60, 36, C.ink, true, "left", `slide-${number}-title`);
  rect(slide, 56, 132, 1168, 1, C.border);
  text(slide, "AAA EAs BUILDER", 56, 686, 240, 18, 11, C.dim, true);
  text(slide, String(number).padStart(2, "0"), 1170, 684, 54, 18, 11, C.dim, true, "right");
  return slide;
}

function addNotes(slide, body, sources) {
  slide.speakerNotes.textFrame.setText(`${body}\n\n[Sources]\n${sources.map((source) => `- ${source}`).join("\n")}\n[/Sources]`);
  slide.speakerNotes.setVisible(true);
}

function node(slide, x, y, w, h, eyebrow, titleValue, color = C.cyan) {
  rect(slide, x, y, w, h, C.panel, C.border, "roundRect");
  rect(slide, x, y, 6, h, color);
  label(slide, eyebrow, x + 22, y + 16, w - 34, color);
  text(slide, titleValue, x + 22, y + 45, w - 36, h - 52, 20, C.ink, true);
}

function statusTag(slide, value, x, y, w, color) {
  rect(slide, x, y, w, 30, C.panel, color, "roundRect");
  text(slide, value.toUpperCase(), x, y + 6, w, 18, 12, color, true, "center");
}

// 1 — Cover
{
  const slide = presentation.slides.add();
  slide.background.fill = C.bg;
  for (let x = 0; x <= W; x += 80) rect(slide, x, 0, 1, H, C.grid);
  for (let y = 0; y <= H; y += 80) rect(slide, 0, y, W, 1, C.grid);
  rect(slide, 0, 0, 10, H, C.cyan);
  label(slide, "Investor product briefing", 70, 70, 350);
  text(slide, "AAA EAs\nBuilder", 70, 130, 470, 180, 64, C.ink, true, "left", "cover-title");
  text(slide, "AI-native creation, repair, and evidence-first commerce for MT5 and TradingView.", 70, 330, 470, 112, 24, C.muted, false);
  rect(slide, 70, 486, 290, 3, C.violet);
  text(slide, "WORKING MVP  •  AUGUST 2026", 70, 510, 400, 26, 14, C.cyan, true);
  await addImage(slide, `${ASSETS}/live-homepage.png`, 610, 76, 580, 540, "Live AAA EAs Builder homepage");
  rect(slide, 610, 76, 580, 6, C.cyan);
  text(slide, "Confidential product overview", 70, 666, 360, 22, 12, C.dim, false);
  addNotes(slide, "Open with the core proposition: this is not a generic chatbot. It is a governed product workflow for turning trading logic into inspectable software and, later, distributing validated products.", ["Internal: current local homepage capture", "Internal: README.md"]);
}

// 2 — Problem
{
  const slide = baseSlide("Trading automation is powerful—but still difficult to build and trust", "The problem", 2);
  text(slide, "Most traders can describe an edge. Far fewer can safely turn it into maintainable code and credible evidence.", 56, 158, 1110, 64, 24, C.muted, false);

  node(slide, 56, 258, 350, 210, "01 / Access", "Ideas remain trapped in natural language", C.cyan);
  text(slide, "MQL5 and Pine expertise create a high barrier between strategy intent and executable software.", 78, 350, 300, 84, 18, C.muted);

  node(slide, 465, 258, 350, 210, "02 / Reliability", "Debugging is slow and fragmented", C.violet);
  text(slide, "Prompts, code, compiler errors, revisions, and testing live in separate tools with weak continuity.", 487, 350, 300, 84, 18, C.muted);

  node(slide, 874, 258, 350, 210, "03 / Trust", "Performance claims lack context", C.amber);
  text(slide, "Metrics without test period, assumptions, drawdown, trade count, and verification status are hard to compare.", 896, 350, 300, 92, 18, C.muted);

  rect(slide, 56, 520, 1168, 110, C.panel2, C.border, "roundRect");
  label(slide, "Product opportunity", 80, 540, 250, C.green);
  text(slide, "Unify creation, repair, validation, evidence, and distribution in one accountable workflow.", 80, 574, 1080, 44, 25, C.ink, true);
  addNotes(slide, "Frame the problem as a workflow and trust gap rather than simply a lack of code generation. The product serves traders, independent developers, and marketplace operators.", ["Internal: PROJECT_PLAN.md sections 1, 3, 4, and 7"]);
}

// 3 — Solution lifecycle
{
  const slide = baseSlide("One product turns an idea into inspectable trading software", "The solution", 3);
  text(slide, "A single lifecycle keeps intent, source, diagnostics, versions, and evidence connected.", 56, 158, 1080, 44, 23, C.muted);

  // Connectors first.
  for (let i = 0; i < 5; i += 1) {
    rect(slide, 176 + i * 198, 315, 92, 3, C.border);
    text(slide, "→", 222 + i * 198, 292, 40, 40, 26, C.cyan, true, "center");
  }
  const steps = [
    ["01", "Describe", "Plain-language rules"],
    ["02", "Specify", "Structured strategy"],
    ["03", "Generate", "MQL5 or Pine"],
    ["04", "Validate", "Checks + compiler"],
    ["05", "Improve", "Context-aware chat"],
    ["06", "Distribute", "Download or list"],
  ];
  steps.forEach((step, index) => {
    const x = 56 + index * 198;
    rect(slide, x, 244, 156, 150, C.panel, index === 4 ? C.violet : C.border, "roundRect");
    label(slide, step[0], x + 18, 260, 60, index === 4 ? C.violet : C.cyan);
    text(slide, step[1], x + 18, 292, 122, 28, 21, C.ink, true);
    text(slide, step[2], x + 18, 332, 122, 44, 15, C.muted, false);
  });

  rect(slide, 56, 452, 1168, 162, C.panel2, C.border, "roundRect");
  label(slide, "Outputs", 80, 474, 160);
  text(slide, "MT5 Expert Advisors", 80, 518, 250, 32, 22, C.ink, true);
  text(slide, "MT5 Indicators", 360, 518, 210, 32, 22, C.ink, true);
  text(slide, "Pine Strategies", 620, 518, 210, 32, 22, C.ink, true);
  text(slide, "Pine Indicators", 880, 518, 210, 32, 22, C.ink, true);
  text(slide, "Every result retains an explanation, assumptions, validation state, source hash, workflow snapshot, and revision history.", 80, 570, 1060, 36, 17, C.muted);
  addNotes(slide, "Walk investors through the full customer loop. Distribution includes protected source downloads today and an evidence-first catalog; payments and entitlements are the next commerce milestone.", ["Internal: README.md", "Internal: PROJECT_PLAN.md sections 2, 4, and 6"]);
}

// 4 — Live customer experience
{
  const slide = baseSlide("The customer experience is already product-shaped", "Live product", 4);
  await addImage(slide, `${ASSETS}/live-homepage.png`, 56, 160, 790, 474, "Live AAA EAs Builder customer homepage", "contain");
  rect(slide, 56, 160, 790, 5, C.cyan);
  label(slide, "Live local build", 886, 170, 260, C.green);
  text(slide, "Plain language in", 886, 214, 300, 32, 23, C.ink, true);
  text(slide, "Describe entries, exits, risk, sessions, and filters without writing code first.", 886, 252, 300, 78, 17, C.muted);
  text(slide, "Controlled workflow", 886, 354, 300, 32, 23, C.ink, true);
  text(slide, "Specialist agents and deterministic checks expose progress instead of hiding it behind one response.", 886, 392, 300, 86, 17, C.muted);
  text(slide, "Inspectable outputs", 886, 500, 300, 32, 23, C.ink, true);
  text(slide, "Users keep the source, version history, diagnostics, and download artifacts.", 886, 538, 300, 70, 17, C.muted);
  addNotes(slide, "This screenshot is from the current running application. Emphasize that the visual system and customer navigation are already integrated with the backend workflows.", ["Internal: live local homepage capture", "Internal: templates/core/home.html"]);
}

// 5 — Controlled workflow
{
  const slide = baseSlide("A controlled agent workflow replaces the one-shot prompt", "AI generation", 5);
  text(slide, "The MVP uses LangChain for provider/model abstraction and LangGraph for bounded, typed orchestration.", 56, 158, 1100, 44, 22, C.muted);

  // Flow lines first.
  rect(slide, 172, 304, 860, 3, C.border);
  [220, 448, 676, 904].forEach((x) => rect(slide, x, 286, 3, 40, C.cyan));
  const agents = [
    ["ARCHITECT", "Normalizes strategy logic", C.cyan],
    ["GENERATOR", "Writes platform code", C.violet],
    ["REVIEWER", "Finds correctness risks", C.amber],
    ["REPAIRER", "Applies bounded fixes", C.green],
  ];
  agents.forEach((agent, i) => {
    const x = 90 + i * 270;
    rect(slide, x, 226, 218, 158, C.panel, agent[2], "roundRect");
    label(slide, agent[0], x + 20, 246, 176, agent[2]);
    text(slide, agent[1], x + 20, 288, 178, 60, 20, C.ink, true);
  });
  rect(slide, 56, 430, 1168, 176, C.panel2, C.border, "roundRect");
  label(slide, "Deterministic guardrails", 80, 450, 320, C.green);
  bullet(slide, "Typed outputs and versioned prompts", 80, 492, 340, C.ink, C.green, 17);
  bullet(slide, "Source inspection and forbidden-pattern checks", 430, 492, 360, C.ink, C.green, 17);
  bullet(slide, "Optional allowlisted MetaEditor compilation", 820, 492, 350, C.ink, C.green, 17);
  bullet(slide, "Pinned workflow snapshot for reproducibility", 80, 548, 340, C.ink, C.green, 17);
  bullet(slide, "Repair loop capped by policy and budget", 430, 548, 360, C.ink, C.green, 17);
  bullet(slide, "Token and estimated-cost accounting", 820, 548, 350, C.ink, C.green, 17);
  addNotes(slide, "The current published generation graph contains four specialist agents: architect, generator, reviewer, and repairer. Deterministic code performs schema and safety checks. This makes the workflow easier to govern than an open-ended agent swarm.", ["Internal: apps/ai_config/services/default_workflow.py", "Internal: apps/builder/services/runtime.py", "Internal: README.md"]);
}

// 6 — Copilot
{
  const slide = baseSlide("The copilot closes the loop on real code", "Project-aware repair", 6);
  await addImage(slide, `${ROOT}/docs/design/mockups/builder-workspace-v1.png`, 56, 164, 706, 448, "AAA EAs Builder workspace design", "cover");
  statusTag(slide, "Workspace direction", 76, 184, 170, C.violet);

  label(slide, "Fresh context per answer", 806, 170, 360, C.cyan);
  const contextLines = [
    "Project rules + run progress",
    "Pinned workflow snapshot",
    "Latest complete source",
    "Versions + diagnostics",
    "Compiler output + recent chat",
  ];
  contextLines.forEach((lineValue, i) => bullet(slide, lineValue, 806, 210 + i * 44, 380, C.ink, C.cyan, 17));

  rect(slide, 806, 446, 382, 166, C.panel2, C.violet, "roundRect");
  label(slide, "Safe fix workflow", 828, 466, 250, C.violet);
  text(slide, "1  Copilot proposes a complete file", 828, 505, 334, 26, 17, C.ink, true);
  text(slide, "2  Proposal stays tied to its base version", 828, 537, 334, 26, 17, C.ink, true);
  text(slide, "3  Apply creates a new immutable version", 828, 569, 334, 26, 16, C.ink, true);
  addNotes(slide, "The new project-aware copilot is the key continuity feature. It can explain failures, answer questions, and propose full corrected source. It never silently overwrites code: application is explicit and creates a new version that is revalidated.", ["Internal: apps/builder/services/chat.py", "Internal: apps/builder/services/revisions.py", "Internal: templates/builder/partials/generation_chat.html", "Internal: docs/design/mockups/builder-workspace-v1.png"]);
}

// 7 — Trust ladder
{
  const slide = baseSlide("Trust is a product feature, not a disclaimer", "Validation", 7);
  text(slide, "Each state is labeled separately so AI review, static validation, compilation, and backtests are never conflated.", 56, 158, 1120, 54, 22, C.muted);

  const tiers = [
    ["LEVEL 1", "Source inspection", "Required functions, size limits, forbidden patterns", "IMPLEMENTED", C.green],
    ["LEVEL 2", "Structural diagnostics", "Platform-aware checks and structured warnings", "IMPLEMENTED", C.green],
    ["LEVEL 3", "MQL5 compilation", "Isolated allowlisted MetaEditor worker", "OPTIONAL", C.amber],
    ["LEVEL 4", "Declared backtest", "Data, spread, dates, settings, and evidence lineage", "ROADMAP", C.violet],
  ];
  tiers.forEach((tier, i) => {
    const y = 238 + i * 94;
    rect(slide, 56 + i * 20, y, 1080 - i * 40, 74, C.panel, tier[4], "roundRect");
    label(slide, tier[0], 80 + i * 20, y + 16, 110, tier[4]);
    text(slide, tier[1], 208 + i * 20, y + 13, 280, 28, 21, C.ink, true);
    text(slide, tier[2], 490 + i * 20, y + 15, 430 - i * 20, 42, 16, C.muted);
    statusTag(slide, tier[3], 1000 - i * 20, y + 20, 120, tier[4]);
  });
  text(slide, "Safety boundary: generated code is downloaded for controlled testing; it is not executed inside the web application.", 56, 632, 1120, 28, 17, C.amber, true);
  addNotes(slide, "Investors should understand that trust comes from explicit evidence levels. MQL5 compilation is available only when a dedicated Windows worker is configured. Automated Pine compilation and full backtesting are not claimed in the current MVP.", ["Internal: README.md Optional MQL5 compiler", "Internal: PROJECT_PLAN.md validation levels and safety boundaries", "Internal: apps/builder/services/compiler.py"]);
}

// 8 — Marketplace
{
  const slide = baseSlide("The marketplace monetizes reusable automation with visible evidence", "Commerce", 8);
  await addImage(slide, `${ASSETS}/live-product.png`, 56, 160, 770, 472, "Live marketplace evidence page with fictional demo data", "contain");
  rect(slide, 56, 160, 770, 5, C.cyan);
  statusTag(slide, "Fictional demo data", 76, 182, 174, C.amber);

  label(slide, "Evidence before purchase", 866, 170, 320, C.cyan);
  bullet(slide, "Profit factor, win rate, drawdown, trades", 866, 214, 320, C.ink, C.cyan, 16);
  bullet(slide, "Test period and modelling assumptions", 866, 270, 320, C.ink, C.cyan, 16);
  bullet(slide, "Verification state and report lineage", 866, 326, 320, C.ink, C.cyan, 16);
  bullet(slide, "Equity and drawdown visualization", 866, 382, 320, C.ink, C.cyan, 16);
  bullet(slide, "Version, compatibility, support, source policy", 866, 438, 320, C.ink, C.cyan, 16);

  rect(slide, 866, 520, 320, 112, C.panel2, C.border, "roundRect");
  label(slide, "Next commerce milestone", 888, 540, 260, C.violet);
  text(slide, "Checkout → order → entitlement → protected download", 888, 574, 270, 46, 17, C.ink, true);
  addNotes(slide, "The catalog and product evidence experience are implemented. The screenshot uses explicitly fictional demo data. Checkout, orders, entitlements, and license delivery are intentionally deferred to the next milestone.", ["Internal: live local marketplace product capture", "Internal: apps/marketplace/models.py", "Internal: README.md"]);
}

// 9 — Admin
{
  const slide = baseSlide("The admin panel is the product’s operating system", "Unfold admin", 9);
  text(slide, "A private Django Unfold console controls AI supply, workflow policy, product operations, and evidence governance.", 56, 158, 1120, 48, 22, C.muted);

  const cols = [
    [56, "AI SUPPLY", C.cyan, ["Gateways + encrypted keys", "Provider/model identifiers", "Budgets, priority, health", "Fallback + capabilities"]],
    [352, "REASONING", C.violet, ["Versioned system prompts", "Agent definitions", "Typed schemas + limits", "Published workflows"]],
    [648, "OPERATIONS", C.green, ["Users + projects", "Runs, tokens, cost", "Code versions + diagnostics", "Chat + proposals"]],
    [944, "COMMERCE", C.amber, ["Products + pricing", "Publishing status", "Test evidence", "Verification labels"]],
  ];
  cols.forEach((col) => {
    rect(slide, col[0], 236, 256, 330, C.panel, col[2], "roundRect");
    label(slide, col[1], col[0] + 22, 258, 210, col[2]);
    col[3].forEach((item, i) => bullet(slide, item, col[0] + 22, 310 + i * 55, 210, C.ink, col[2], 16));
  });
  rect(slide, 56, 596, 1144, 52, C.panel2, C.border, "roundRect");
  text(slide, "Governance by design: write-only secrets  •  versioned publishing  •  searchable audit records  •  existing runs keep pinned configuration", 76, 612, 1104, 24, 16, C.muted, true, "center");
  addNotes(slide, "This is where a small operations team can manage the entire system without a separate internal tool. API credentials are encrypted and write-only after entry. Prompts, agents, and workflows are versioned; active generations retain their pinned snapshot.", ["Internal: apps/ai_config/admin.py and models.py", "Internal: apps/builder/admin.py", "Internal: apps/marketplace/admin.py", "Internal: apps/accounts/admin.py"]);
}

// 10 — Lineage
{
  const slide = baseSlide("Every generation carries an auditable chain of custody", "Data lineage", 10);
  text(slide, "The system records what was requested, what configuration ran, what code changed, and what evidence supports the result.", 56, 158, 1120, 52, 22, C.muted);

  // Connectors first.
  for (let i = 0; i < 5; i += 1) {
    rect(slide, 190 + i * 205, 322, 56, 3, C.border);
    text(slide, "→", 210 + i * 205, 300, 32, 34, 23, C.cyan, true, "center");
  }
  const chain = [
    ["ADMIN", "Published\nconfig", C.cyan],
    ["RUN", "Pinned workflow\nsnapshot", C.violet],
    ["CODE", "Version + source\nhash", C.green],
    ["CHECKS", "Diagnostics +\ncompiler output", C.amber],
    ["COPILOT", "Proposal tied to\nbase version", C.violet],
    ["EVIDENCE", "Test run +\nverification", C.cyan],
  ];
  chain.forEach((item, i) => {
    const x = 56 + i * 205;
    rect(slide, x, 246, 154, 156, C.panel, item[2], "roundRect");
    label(slide, item[0], x + 18, 266, 120, item[2]);
    text(slide, item[1], x + 18, 310, 118, 62, 18, C.ink, true);
  });

  rect(slide, 56, 460, 1168, 146, C.panel2, C.border, "roundRect");
  label(slide, "Why investors should care", 80, 482, 300, C.green);
  text(slide, "Reproducibility", 80, 526, 220, 28, 21, C.ink, true);
  text(slide, "Support & disputes", 380, 526, 220, 28, 21, C.ink, true);
  text(slide, "Quality analytics", 680, 526, 220, 28, 21, C.ink, true);
  text(slide, "Marketplace trust", 980, 526, 200, 28, 21, C.ink, true);
  text(slide, "This lineage becomes the foundation for safer iteration, customer support, model evaluation, and evidence-based merchandising.", 80, 566, 1080, 28, 16, C.muted);
  addNotes(slide, "The chain of custody is a core data advantage. It enables later evaluation by model, prompt, agent version, diagnostic type, product type, and evidence quality without losing provenance.", ["Internal: apps/ai_config/models.py", "Internal: apps/builder/models.py", "Internal: apps/marketplace/models.py"]);
}

// 11 — Architecture
{
  const slide = baseSlide("Built for an MVP today—and production scale tomorrow", "Architecture", 11);
  text(slide, "A modular Django core keeps the first release fast to ship while preserving clear upgrade paths.", 56, 158, 1100, 44, 22, C.muted);

  const layers = [
    ["EXPERIENCE", "Django templates  •  Tailwind  •  HTMX  •  Alpine.js", C.cyan],
    ["APPLICATION", "Class-based views  •  domain services  •  permissions  •  protected downloads", C.violet],
    ["AI ORCHESTRATION", "LangChain providers  •  LangGraph workflow  •  structured outputs", C.green],
    ["ASYNC + DATA", "Celery  •  Redis  •  SQLite development  →  PostgreSQL production", C.amber],
    ["OPERATIONS", "Unfold admin  •  Docker  •  Windows BAT  •  Makefile", C.cyan],
  ];
  layers.forEach((layer, i) => {
    const y = 232 + i * 72;
    rect(slide, 56 + i * 16, y, 1120 - i * 32, 56, i % 2 === 0 ? C.panel : C.panel2, layer[2], "roundRect");
    label(slide, layer[0], 80 + i * 16, y + 17, 210, layer[2]);
    text(slide, layer[1], 300 + i * 16, y + 15, 820 - i * 32, 28, 18, C.ink, true);
  });
  text(slide, "Deployment choice", 56, 626, 170, 24, 16, C.dim, true);
  text(slide, "Normal Windows workflow for local teams  •  Docker web/worker/Redis stack for consistent environments", 226, 625, 930, 26, 16, C.muted);
  addNotes(slide, "The architecture intentionally avoids an early split into multiple frontends or microservices. The current app runs locally without Docker and includes a containerized path. Production migration replaces SQLite with PostgreSQL and runs background work through Celery and Redis.", ["Internal: README.md", "Internal: docker-compose.yml", "Internal: dev.bat", "Internal: Makefile", "Internal: config/settings/"]);
}

// 12 — Proof
{
  const slide = baseSlide("The current MVP proves the core technical risk", "Implementation proof", 12);
  await addImage(slide, `${ASSETS}/live-marketplace.png`, 56, 170, 600, 392, "Live marketplace listing page", "contain");
  rect(slide, 56, 170, 600, 5, C.cyan);

  const proof = [
    ["4", "artifact types", "MT5 EA + indicator, Pine strategy + indicator", C.cyan],
    ["5", "admin-managed AI agents", "Four generation roles plus the project copilot", C.violet],
    ["22", "automated tests passing", "Accounts, AI config, builder, core, and marketplace", C.green],
    ["LIVE", "Gemini integration verified", "A real fix proposal reduced internal diagnostics from 4 to 1", C.amber],
  ];
  proof.forEach((item, i) => {
    const y = 170 + i * 105;
    text(slide, item[0], 710, y, 110, 52, i === 3 ? 28 : 40, item[3], true, "right");
    text(slide, item[1], 842, y + 3, 330, 28, 20, C.ink, true);
    text(slide, item[2], 842, y + 36, 330, 48, 15, C.muted);
  });
  statusTag(slide, "Internal verification—not customer traction", 56, 588, 322, C.amber);
  text(slide, "Implemented: authentication, projects, generation, versioned code, diagnostics, copilot proposals, admin AI configuration, catalog, evidence pages, and downloads.", 404, 588, 784, 54, 16, C.muted, true);
  addNotes(slide, "Be precise: these are product and engineering proof points, not revenue or customer traction. The live Gemini test created a full proposal and improved the diagnostic count, but still left one issue for another iteration; this is why the product retains validation and human application steps.", ["Internal: automated test suite run on 2026-08-10", "Internal: live Gemini verification performed on 2026-08-10", "Internal: current local marketplace capture", "Internal: README.md"]);
}

// 13 — Business model
{
  const slide = baseSlide("Revenue can combine creation, usage, and commerce", "Proposed business model", 13);
  text(slide, "The same platform can monetize both software creation and distribution without depending on a single revenue stream.", 56, 158, 1120, 52, 22, C.muted);

  const models = [
    ["SUBSCRIPTION", "Builder access", "Projects, saved versions, templates, and included monthly generations", C.cyan],
    ["USAGE", "Advanced AI + validation", "Additional generation credits, premium models, compilation, and evidence services", C.violet],
    ["MARKETPLACE", "Transaction take rate", "Commission on licensed pre-made EAs, indicators, and strategy products", C.green],
    ["PREMIUM", "Vendor and team tools", "Higher limits, managed publishing, support, analytics, and governance", C.amber],
  ];
  models.forEach((model, i) => {
    const x = 56 + i * 292;
    rect(slide, x, 248, 260, 300, C.panel, model[3], "roundRect");
    label(slide, model[0], x + 22, 270, 210, model[3]);
    text(slide, model[1], x + 22, 318, 216, 58, 23, C.ink, true);
    text(slide, model[2], x + 22, 404, 216, 108, 17, C.muted);
  });
  rect(slide, 56, 584, 1144, 58, C.panel2, C.border, "roundRect");
  text(slide, "Pricing, take rate, and packaging remain to be validated with launch users; no revenue assumptions are presented here.", 76, 601, 1104, 30, 17, C.amber, true, "center");
  addNotes(slide, "Present this as a proposed model to test, not a finalized forecast. The sequencing can begin with subscriptions and usage, then add marketplace transactions once checkout and entitlements are complete.", ["Internal: PROJECT_PLAN.md product vision and marketplace scope", "Internal product strategy assumption; not yet validated"]);
}

// 14 — Roadmap and close
{
  const slide = baseSlide("The path from working MVP to investable launch is clear", "Roadmap & close", 14);
  const phases = [
    ["NOW", "Core workflow proven", ["AI generation + repair", "Versioned code + validation", "Admin AI control plane", "Evidence-first catalog"], C.green],
    ["0–3 MONTHS", "Production launch", ["Checkout + entitlements", "PostgreSQL + observability", "Email/account hardening", "Isolated compile worker"], C.cyan],
    ["3–6 MONTHS", "Evidence engine", ["Report ingestion + parsing", "Backtest provenance", "Guided templates", "Initial seller pilot"], C.violet],
    ["6–12 MONTHS", "Marketplace scale", ["Seller onboarding + payouts", "Optimization/forward tests", "Team and vendor tools", "Distribution partnerships"], C.amber],
  ];
  phases.forEach((phase, i) => {
    const x = 56 + i * 292;
    rect(slide, x, 170, 260, 356, C.panel, phase[3], "roundRect");
    label(slide, phase[0], x + 20, 190, 210, phase[3]);
    text(slide, phase[1], x + 20, 232, 216, 58, 22, C.ink, true);
    phase[2].forEach((item, j) => bullet(slide, item, x + 20, 314 + j * 48, 216, C.ink, phase[3], 15));
  });
  rect(slide, 56, 560, 1144, 84, C.panel2, C.cyan, "roundRect");
  label(slide, "Investor conversation", 80, 576, 260, C.cyan);
  text(slide, "Capital accelerates production hardening, evidence infrastructure, payments, and launch distribution.", 80, 608, 1080, 26, 17, C.ink, true);
  addNotes(slide, "Close by asking for feedback and alignment on the next financing milestone. The specific round size and financial projections should be added only after the founder defines the raise, runway, hiring plan, and customer-validation targets.", ["Internal: PROJECT_PLAN.md roadmap and deferred scope", "Internal: README.md current vs deferred capabilities"]);
}

const pptx = await PresentationFile.exportPptx(presentation);
await pptx.save(OUT);
console.log(`Saved ${OUT}`);
