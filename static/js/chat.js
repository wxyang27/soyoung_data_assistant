const form = document.querySelector("#chat-form");
const input = document.querySelector("#question");
const messages = document.querySelector("#messages");
const userTemplate = document.querySelector("#user-template");
const assistantTemplate = document.querySelector("#assistant-template");

const welcomeMessage = {
  intent: { label: "系统提示", confidence: 1 },
  summary: "你好，我是连锁数据智能运营助手。第一阶段我可以演示自然语言问答、毛利率诊断结构、SQL 和口径卡片。",
  sections: [],
  sql: "",
  caliber: ["聊天历史会自动从本地 SQLite 读取。"],
};

function clearMessages() {
  messages.innerHTML = "";
}

function appendUserMessage(text) {
  const node = userTemplate.content.cloneNode(true);
  node.querySelector(".bubble").textContent = text;
  messages.appendChild(node);
  scrollToBottom();
}

function appendAssistantMessage(data) {
  const node = assistantTemplate.content.cloneNode(true);

  node.querySelector(".intent").textContent = data.intent.label;
  node.querySelector(".confidence").textContent = `置信度 ${(data.intent.confidence * 100).toFixed(0)}%`;
  node.querySelector(".summary").textContent = data.summary;

  const sections = node.querySelector(".sections");
  for (const section of data.sections || []) {
    const block = document.createElement("section");
    block.className = "section";

    const title = document.createElement("h3");
    title.textContent = section.title;
    block.appendChild(title);

    const list = document.createElement("ul");
    for (const item of section.items || []) {
      const li = document.createElement("li");
      li.textContent = item;
      list.appendChild(li);
    }
    block.appendChild(list);
    sections.appendChild(block);
  }

  const sqlBlock = node.querySelector(".sql-block");
  if (data.sql) {
    sqlBlock.querySelector("code").textContent = data.sql;
  } else {
    sqlBlock.remove();
  }

  if (data.citations && data.citations.length) {
    const citations = document.createElement("div");
    citations.className = "citations";

    const title = document.createElement("h3");
    title.textContent = "引用来源";
    citations.appendChild(title);

    const list = document.createElement("ol");
    for (const citation of data.citations) {
      const item = document.createElement("li");
      const heading = document.createElement("strong");
      heading.textContent = `${citation.title || "未命名片段"} · ${citation.filename}`;

      const meta = document.createElement("span");
      meta.textContent = `topic=${citation.topic} score=${citation.score}`;

      const text = document.createElement("p");
      text.textContent = citation.snippet;

      item.appendChild(heading);
      item.appendChild(meta);
      item.appendChild(text);
      list.appendChild(item);
    }
    citations.appendChild(list);
    node.querySelector(".bubble").appendChild(citations);
  }

  const caliber = node.querySelector(".caliber");
  const caliberTitle = document.createElement("h3");
  caliberTitle.textContent = "口径声明";
  caliber.appendChild(caliberTitle);

  const caliberList = document.createElement("ul");
  for (const item of data.caliber || []) {
    const li = document.createElement("li");
    li.textContent = item;
    caliberList.appendChild(li);
  }
  caliber.appendChild(caliberList);

  messages.appendChild(node);
  scrollToBottom();
}

function appendErrorMessage(text) {
  appendAssistantMessage({
    intent: { label: "系统提示", confidence: 1 },
    summary: text,
    sections: [],
    sql: "",
    caliber: ["请稍后重试，或检查后端服务是否正常。"],
  });
}

function parsePayload(payloadJson) {
  if (!payloadJson) return null;
  try {
    return JSON.parse(payloadJson);
  } catch (error) {
    return null;
  }
}

function appendHistoryMessage(message) {
  if (message.role === "user") {
    appendUserMessage(message.content);
    return;
  }

  const payload = parsePayload(message.payload_json);
  if (payload) {
    appendAssistantMessage(payload);
    return;
  }

  appendAssistantMessage({
    intent: { label: message.intent || "历史消息", confidence: 1 },
    summary: message.content,
    sections: [],
    sql: message.sql_text || "",
    caliber: ["这条历史消息来自本地 SQLite。"],
  });
}

async function loadHistory() {
  try {
    const response = await fetch("/api/history");
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "历史记录加载失败");
    }

    clearMessages();
    if (!data.messages || data.messages.length === 0) {
      appendAssistantMessage(welcomeMessage);
      return;
    }

    for (const message of data.messages) {
      appendHistoryMessage(message);
    }
  } catch (error) {
    clearMessages();
    appendErrorMessage(`历史记录加载失败：${error.message}`);
  }
}

function scrollToBottom() {
  messages.scrollTop = messages.scrollHeight;
}

async function sendQuestion(question) {
  appendUserMessage(question);
  const submitButton = form.querySelector("button");
  submitButton.disabled = true;
  submitButton.textContent = "分析中";

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "请求失败");
    }

    appendAssistantMessage(data);
  } catch (error) {
    appendErrorMessage(error.message);
  } finally {
    submitButton.disabled = false;
    submitButton.textContent = "发送";
    input.focus();
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const question = input.value.trim();
  if (!question) return;
  input.value = "";
  sendQuestion(question);
});

document.querySelectorAll(".example").forEach((button) => {
  button.addEventListener("click", () => {
    const question = button.dataset.question;
    input.value = question;
    sendQuestion(question);
  });
});

loadHistory();
