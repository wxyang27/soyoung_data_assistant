const form = document.querySelector("#chat-form");
const input = document.querySelector("#question");
const messages = document.querySelector("#messages");
const userTemplate = document.querySelector("#user-template");
const assistantTemplate = document.querySelector("#assistant-template");

function appendUserMessage(text) {
  const node = userTemplate.content.cloneNode(true);
  node.querySelector(".bubble").textContent = text;
  messages.appendChild(node);
  scrollToBottom();
}

function appendAssistantMessage(data) {
  const node = assistantTemplate.content.cloneNode(true);

  node.querySelector(".intent").textContent = data.intent.label;
  node.querySelector(".confidence").textContent = `confidence ${(data.intent.confidence * 100).toFixed(0)}%`;
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

function scrollToBottom() {
  messages.scrollTop = messages.scrollHeight;
}

async function sendQuestion(question) {
  appendUserMessage(question);
  form.querySelector("button").disabled = true;

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
    form.querySelector("button").disabled = false;
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
