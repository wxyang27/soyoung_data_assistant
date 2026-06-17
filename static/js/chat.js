const form = document.querySelector("#chat-form");
const input = document.querySelector("#question");
const messages = document.querySelector("#messages");
const sessions = document.querySelector("#sessions");
const newSessionButton = document.querySelector("#new-session");
const userTemplate = document.querySelector("#user-template");
const assistantTemplate = document.querySelector("#assistant-template");

let currentSessionId = null;
let sessionItems = [];

const welcomeMessage = {
  intent: { label: "系统提示", confidence: 1 },
  summary: "你好，我是连锁数据智能运营助手。你可以自由提问，系统会先检索本地业务知识库，再调用 DeepSeek 生成结构化回答。",
  sections: [
    {
      title: "可以尝试的问法",
      items: [
        "L0灌券为什么会拖累毛利？",
        "常规品毛利率低应该从哪些角度排查？",
        "0元单成本怎么查，口径要注意什么？",
      ],
    },
  ],
  sql: "",
  caliber: ["每个对话任务独立保存，你可以新建、重命名、归档或删除。"],
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
  if (data.llm_mode) {
    const badge = document.createElement("span");
    badge.className = "llm-badge";
    const provider = data.llm?.provider || "LLM";
    const model = data.llm?.model || "RAG";
    badge.textContent = `${provider} · ${model}`;
    node.querySelector(".answer-head").appendChild(badge);
  }
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

async function requestJson(url, options = {}) {
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "请求失败");
  }
  return data;
}

async function loadSessions(preferredSessionId = currentSessionId) {
  const data = await requestJson("/api/sessions");
  sessionItems = data.sessions || [];
  renderSessions();

  if (sessionItems.length === 0) {
    const created = await createSession(false);
    currentSessionId = created.id;
  } else if (preferredSessionId && sessionItems.some((item) => item.id === preferredSessionId)) {
    currentSessionId = preferredSessionId;
  } else {
    currentSessionId = sessionItems[0].id;
  }

  renderSessions();
  await loadHistory(currentSessionId);
}

function renderSessions() {
  sessions.innerHTML = "";
  for (const session of sessionItems) {
    const item = document.createElement("article");
    item.className = `session-item${session.id === currentSessionId ? " active" : ""}`;
    item.dataset.sessionId = session.id;

    const body = document.createElement("button");
    body.className = "session-main";
    body.type = "button";
    body.addEventListener("click", () => switchSession(session.id));

    const title = document.createElement("strong");
    title.textContent = session.title;

    const meta = document.createElement("span");
    const count = Number(session.message_count || 0);
    meta.textContent = count ? `${count} 条消息 · ${session.preview || "暂无摘要"}` : "空白任务";

    body.appendChild(title);
    body.appendChild(meta);

    const actions = document.createElement("div");
    actions.className = "session-actions";
    actions.appendChild(buildSessionAction("改", () => renameSession(session)));
    actions.appendChild(buildSessionAction("归", () => archiveSession(session.id)));
    actions.appendChild(buildSessionAction("删", () => removeSession(session.id)));

    item.appendChild(body);
    item.appendChild(actions);
    sessions.appendChild(item);
  }
}

function buildSessionAction(label, handler) {
  const button = document.createElement("button");
  button.type = "button";
  button.textContent = label;
  button.addEventListener("click", (event) => {
    event.stopPropagation();
    handler();
  });
  return button;
}

async function createSession(shouldLoad = true) {
  const data = await requestJson("/api/sessions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title: "新对话任务" }),
  });
  if (shouldLoad) {
    currentSessionId = data.session.id;
    await loadSessions(currentSessionId);
  }
  return data.session;
}

async function switchSession(sessionId) {
  if (sessionId === currentSessionId) return;
  currentSessionId = sessionId;
  renderSessions();
  await loadHistory(sessionId);
}

async function renameSession(session) {
  const title = window.prompt("修改对话任务名称", session.title);
  if (!title || title.trim() === session.title) return;
  await requestJson(`/api/sessions/${session.id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title: title.trim() }),
  });
  await loadSessions(session.id);
}

async function archiveSession(sessionId) {
  if (!window.confirm("归档后将从当前任务列表隐藏，确认归档吗？")) return;
  await requestJson(`/api/sessions/${sessionId}/archive`, { method: "POST" });
  currentSessionId = null;
  await loadSessions();
}

async function removeSession(sessionId) {
  if (!window.confirm("删除会同时删除该任务下的历史消息，确认删除吗？")) return;
  await requestJson(`/api/sessions/${sessionId}`, { method: "DELETE" });
  currentSessionId = null;
  await loadSessions();
}

async function loadHistory(sessionId) {
  try {
    const data = await requestJson(`/api/history?session_id=${sessionId}`);
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
  if (!currentSessionId) {
    const created = await createSession(false);
    currentSessionId = created.id;
  }

  appendUserMessage(question);
  const submitButton = form.querySelector("button");
  submitButton.disabled = true;
  submitButton.textContent = "分析中";

  try {
    const data = await requestJson("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, session_id: currentSessionId }),
    });

    appendAssistantMessage(data);
    await loadSessions(currentSessionId);
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

newSessionButton.addEventListener("click", () => createSession(true));

document.querySelectorAll(".example").forEach((button) => {
  button.addEventListener("click", () => {
    const question = button.dataset.question;
    input.value = question;
    sendQuestion(question);
  });
});

loadSessions().catch((error) => {
  clearMessages();
  appendErrorMessage(`会话任务加载失败：${error.message}`);
});
