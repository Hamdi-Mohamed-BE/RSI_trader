const chartColor = (name, fallback) =>
  getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback;

function drawLineChart(canvas) {
  const source = document.getElementById(canvas.dataset.chartSource);
  if (!source) return;

  const points = JSON.parse(source.textContent);
  if (!Array.isArray(points) || points.length < 2) return;

  const context = canvas.getContext("2d");
  const isDrawdown = canvas.dataset.chartKind === "drawdown";
  const line = isDrawdown
    ? chartColor("--color-signal-red", "#ff3b6b")
    : chartColor("--color-neon-cyan", "#00e5ff");

  const render = () => {
    const ratio = window.devicePixelRatio || 1;
    const width = canvas.clientWidth;
    const height = canvas.clientHeight;
    canvas.width = Math.floor(width * ratio);
    canvas.height = Math.floor(height * ratio);
    context.setTransform(ratio, 0, 0, ratio, 0, 0);
    context.clearRect(0, 0, width, height);

    const padding = { top: 16, right: 14, bottom: 16, left: 14 };
    const chartWidth = width - padding.left - padding.right;
    const chartHeight = height - padding.top - padding.bottom;
    const min = Math.min(...points);
    const max = Math.max(...points);
    const spread = max - min || 1;

    context.strokeStyle = "rgba(30, 51, 85, 0.55)";
    context.lineWidth = 1;
    for (let row = 0; row <= 4; row += 1) {
      const y = padding.top + (chartHeight / 4) * row;
      context.beginPath();
      context.moveTo(padding.left, y);
      context.lineTo(width - padding.right, y);
      context.stroke();
    }

    const coordinates = points.map((value, index) => ({
      x: padding.left + (index / (points.length - 1)) * chartWidth,
      y: padding.top + (1 - (value - min) / spread) * chartHeight,
    }));

    const gradient = context.createLinearGradient(0, padding.top, 0, height);
    gradient.addColorStop(0, isDrawdown ? "rgba(255,59,107,.22)" : "rgba(0,229,255,.2)");
    gradient.addColorStop(1, "rgba(5,7,13,0)");
    context.beginPath();
    context.moveTo(coordinates[0].x, height - padding.bottom);
    coordinates.forEach(({ x, y }) => context.lineTo(x, y));
    context.lineTo(coordinates.at(-1).x, height - padding.bottom);
    context.closePath();
    context.fillStyle = gradient;
    context.fill();

    context.beginPath();
    coordinates.forEach(({ x, y }, index) => {
      if (index === 0) context.moveTo(x, y);
      else context.lineTo(x, y);
    });
    context.strokeStyle = line;
    context.lineWidth = 2;
    context.shadowColor = line;
    context.shadowBlur = 8;
    context.stroke();
    context.shadowBlur = 0;
  };

  render();
  new ResizeObserver(render).observe(canvas);
}

document.querySelectorAll("canvas[data-chart-source]").forEach(drawLineChart);

const codeKeywords = new Set([
  "break",
  "case",
  "class",
  "const",
  "continue",
  "default",
  "do",
  "else",
  "enum",
  "export",
  "for",
  "if",
  "import",
  "input",
  "new",
  "private",
  "protected",
  "public",
  "return",
  "series",
  "static",
  "switch",
  "var",
  "while",
]);

const codeTypes = new Set([
  "bool",
  "char",
  "color",
  "datetime",
  "double",
  "float",
  "int",
  "long",
  "MqlDateTime",
  "MqlRates",
  "short",
  "string",
  "uint",
  "ulong",
  "ushort",
  "void",
]);

const codeConstants = new Set(["false", "na", "null", "true"]);
const constantPrefixes = [
  "ACCOUNT_",
  "COLOR_",
  "INIT_",
  "INVALID_",
  "MODE_",
  "ORDER_",
  "PERIOD_",
  "POSITION_",
  "PRICE_",
  "SYMBOL_",
  "TRADE_",
];

function appendCodeToken(parent, value, tokenClass = "") {
  if (!value) return;
  if (!tokenClass) {
    parent.append(document.createTextNode(value));
    return;
  }
  const token = document.createElement("span");
  token.className = `vscode-token-${tokenClass}`;
  token.textContent = value;
  parent.append(token);
}

function highlightCodeLine(codeElement, line) {
  const firstContent = line.search(/\S/);
  if (firstContent >= 0) {
    const trimmed = line.slice(firstContent);
    if (trimmed.startsWith("#") || trimmed.startsWith("//@version")) {
      appendCodeToken(codeElement, line.slice(0, firstContent));
      appendCodeToken(codeElement, trimmed, "preprocessor");
      return;
    }
  }

  let index = 0;
  while (index < line.length) {
    const character = line[index];
    const nextCharacter = line[index + 1];

    if (character === "/" && nextCharacter === "/") {
      appendCodeToken(codeElement, line.slice(index), "comment");
      break;
    }

    if (character === '"' || character === "'") {
      const quote = character;
      let end = index + 1;
      while (end < line.length) {
        if (line[end] === quote && line[end - 1] !== "\\") {
          end += 1;
          break;
        }
        end += 1;
      }
      appendCodeToken(codeElement, line.slice(index, end), "string");
      index = end;
      continue;
    }

    if (/\d/.test(character) || (character === "." && /\d/.test(nextCharacter || ""))) {
      const numberMatch = line.slice(index).match(/^(?:0x[\da-f]+|\d*\.?\d+(?:e[+-]?\d+)?)/i);
      if (numberMatch) {
        appendCodeToken(codeElement, numberMatch[0], "number");
        index += numberMatch[0].length;
        continue;
      }
    }

    if (/[A-Za-z_]/.test(character)) {
      const identifierMatch = line.slice(index).match(/^[A-Za-z_]\w*/);
      const identifier = identifierMatch ? identifierMatch[0] : character;
      const remainder = line.slice(index + identifier.length);
      let tokenClass = "";
      if (codeKeywords.has(identifier)) tokenClass = "keyword";
      else if (codeTypes.has(identifier)) tokenClass = "type";
      else if (
        codeConstants.has(identifier) ||
        constantPrefixes.some((prefix) => identifier.startsWith(prefix))
      ) {
        tokenClass = "constant";
      } else if (/^\s*\(/.test(remainder)) tokenClass = "function";
      appendCodeToken(codeElement, identifier, tokenClass);
      index += identifier.length;
      continue;
    }

    if (/[+\-*/%=!<>&|?:~^]/.test(character)) {
      const operatorMatch = line.slice(index).match(/^(?:==|!=|<=|>=|&&|\|\||\+\+|--|->|[+\-*/%=!<>&|?:~^])/);
      const operator = operatorMatch ? operatorMatch[0] : character;
      appendCodeToken(codeElement, operator, "operator");
      index += operator.length;
      continue;
    }

    appendCodeToken(codeElement, character);
    index += 1;
  }

  if (!line.length) codeElement.append(document.createTextNode("\u200b"));
}

async function copyCode(source, button) {
  try {
    await navigator.clipboard.writeText(source);
  } catch {
    const fallback = document.createElement("textarea");
    fallback.value = source;
    fallback.style.position = "fixed";
    fallback.style.opacity = "0";
    document.body.append(fallback);
    fallback.select();
    document.execCommand("copy");
    fallback.remove();
  }

  const label = button.querySelector("[data-copy-label]");
  if (!label) return;
  label.textContent = "Copied";
  window.setTimeout(() => {
    label.textContent = "Copy";
  }, 1600);
}

function initializeCodeEditor(editor) {
  if (editor.dataset.initialized === "true") return;
  const rawSource = editor.querySelector("[data-raw-source]");
  const lineList = editor.querySelector("[data-code-lines]");
  if (!rawSource || !lineList) return;

  const source = rawSource.textContent.replace(/\r\n?/g, "\n");
  source.split("\n").forEach((line, lineIndex) => {
    const lineItem = document.createElement("li");
    lineItem.dataset.line = String(lineIndex + 1);
    const codeElement = document.createElement("code");
    highlightCodeLine(codeElement, line);
    lineItem.append(codeElement);
    lineList.append(lineItem);
  });

  lineList.addEventListener("click", (event) => {
    const selectedLine = event.target.closest("li");
    if (!selectedLine) return;
    lineList.querySelector(".vscode-line-active")?.classList.remove("vscode-line-active");
    selectedLine.classList.add("vscode-line-active");
    const cursor = editor.querySelector("[data-cursor-position]");
    if (cursor) cursor.textContent = `Ln ${selectedLine.dataset.line}, Col 1`;
  });

  editor.querySelector("[data-copy-code]")?.addEventListener("click", (event) => {
    copyCode(source, event.currentTarget);
  });
  editor.dataset.initialized = "true";
}

function initializeCodeEditors(root = document) {
  if (root.matches?.("[data-code-editor]")) initializeCodeEditor(root);
  root.querySelectorAll?.("[data-code-editor]").forEach(initializeCodeEditor);
}

initializeCodeEditors();
document.body.addEventListener("htmx:afterSwap", (event) => initializeCodeEditors(event.target));

function scrollChatThread(root = document) {
  const thread = root.matches?.("[data-chat-scroll]")
    ? root
    : root.querySelector?.("[data-chat-scroll]");
  if (thread) thread.scrollTop = thread.scrollHeight;
}

document.querySelectorAll("[data-chat-prompt]").forEach((button) => {
  button.addEventListener("click", () => {
    const messageInput = document.getElementById("id_message");
    if (!messageInput) return;
    messageInput.value = button.dataset.chatPrompt;
    messageInput.focus();
    messageInput.scrollIntoView({ behavior: "smooth", block: "center" });
  });
});

scrollChatThread();
document.body.addEventListener("htmx:afterSwap", (event) => scrollChatThread(event.target));
