const form = document.querySelector("#support-form");
const accountId = document.querySelector("#account-id");
const customerMessage = document.querySelector("#customer-message");
const conversationHistory = document.querySelector("#conversation-history");
const analyzeButton = document.querySelector("#analyze-button");

const emptyState = document.querySelector("#empty-state");
const result = document.querySelector("#result");

const statusElement = document.querySelector("#status");
const confidenceElement = document.querySelector("#confidence");
const categoryElement = document.querySelector("#issue-category");
const summaryElement = document.querySelector("#summary");
const resolutionElement = document.querySelector("#recommended-resolution");
const evidenceElement = document.querySelector("#evidence");
const missingInformationElement = document.querySelector("#missing-information");
const escalationElement = document.querySelector("#escalation");
const handoffElement = document.querySelector("#handoff-summary");

function addListItems(container, items) {
  container.replaceChildren();

  items.forEach((item) => {
    const listItem = document.createElement("li");
    listItem.textContent = item;
    container.appendChild(listItem);
  });
}

function statusClass(status) {
  if (status === "READY_FOR_AGENT") return "ready";
  if (status === "MORE_INFORMATION_REQUIRED") return "more";
  return "escalate";
}

function renderEvidence(evidence) {
  evidenceElement.replaceChildren();

  if (!evidence.length) {
    evidenceElement.textContent = "No local evidence is available.";
    return;
  }

  evidence.forEach((item) => {
    const card = document.createElement("div");
    card.className = "evidence-card";

    const title = document.createElement("strong");
    title.textContent = `${item.article_id} — ${item.title}`;

    const section = document.createElement("span");
    section.textContent = `Source section: ${item.section}`;

    card.append(title, section);
    evidenceElement.appendChild(card);
  });
}

function renderHandoff(handoff) {
  handoffElement.replaceChildren();

  const card = document.createElement("div");
  card.className = "handoff-card";

  const fields = [
    ["Issue", handoff.issue],
    ["Established facts", (handoff.established_facts || []).join("; ")],
    ["Steps already tried", (handoff.steps_already_tried || []).join("; ")],
    ["Human action needed", handoff.human_action_needed],
  ];

  fields.forEach(([label, value]) => {
    if (!value) return;

    const paragraph = document.createElement("p");
    paragraph.innerHTML = `<strong>${label}:</strong> `;
    paragraph.append(document.createTextNode(value));
    card.appendChild(paragraph);
  });

  handoffElement.appendChild(card);
}

function renderResult(data) {
  emptyState.classList.add("hidden");
  result.classList.remove("hidden");

  statusElement.textContent = data.status.replaceAll("_", " ");
  statusElement.className = `status ${statusClass(data.status)}`;

  confidenceElement.textContent = `Confidence: ${data.confidence}`;
  categoryElement.textContent = data.issue_category;
  summaryElement.textContent = data.summary;

  addListItems(resolutionElement, data.recommended_resolution || []);
  addListItems(missingInformationElement, data.missing_information || []);
  renderEvidence(data.evidence || []);

  escalationElement.textContent = data.escalation_required
    ? data.escalation_reason || "Human escalation is required."
    : "No escalation is currently required.";

  renderHandoff(data.handoff_summary || {});
}

function showError(message) {
  renderResult({
    issue_category: "Request error",
    summary: message,
    recommended_resolution: [],
    evidence: [],
    missing_information: [],
    confidence: "low",
    status: "MORE_INFORMATION_REQUIRED",
    escalation_required: false,
    escalation_reason: "",
    handoff_summary: {},
  });
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  analyzeButton.disabled = true;
  analyzeButton.textContent = "Analyzing…";

  try {
    const response = await fetch("/analyze", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        account_id: accountId.value,
        customer_message: customerMessage.value,
        conversation_history: conversationHistory.value,
      }),
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "The support case could not be processed.");
    }

    renderResult(data);
  } catch (error) {
    showError(error.message);
  } finally {
    analyzeButton.disabled = false;
    analyzeButton.textContent = "Analyze safely";
  }
});

document.querySelectorAll("[data-account]").forEach((button) => {
  button.addEventListener("click", () => {
    accountId.value = button.dataset.account;
    customerMessage.value = button.dataset.message;
    conversationHistory.value = "";
  });
});