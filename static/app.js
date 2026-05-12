const form = document.querySelector("#transcript-form");
const submitButton = document.querySelector("#submit-button");
const result = document.querySelector("#result");
const resultTitle = document.querySelector("#result-title");
const meta = document.querySelector("#meta");
const copyButton = document.querySelector("#copy-button");
const downloadButton = document.querySelector("#download-button");

let currentTranscript = "";
let currentVideoId = "transcript";

function setBusy(isBusy) {
  submitButton.disabled = isBusy;
  submitButton.textContent = isBusy ? "Đang lấy transcript..." : "Lấy transcript";
}

function setActions(enabled) {
  copyButton.disabled = !enabled;
  downloadButton.disabled = !enabled;
}

function renderMeta(payload) {
  const minutes = Math.max(1, Math.round(payload.durationSeconds / 60));
  meta.innerHTML = [
    `Video: ${payload.videoId}`,
    `Ngôn ngữ: ${payload.language} (${payload.languageCode})`,
    payload.isGenerated ? "Tự động tạo" : "Phụ đề thủ công",
    `${payload.snippetCount} đoạn`,
    `Khoảng ${minutes} phút`,
  ]
    .map((item) => `<span>${item}</span>`)
    .join("");
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  setBusy(true);
  setActions(false);
  result.classList.remove("is-error");
  resultTitle.textContent = "Đang xử lý video";
  result.textContent = "Đang kết nối YouTube và đọc caption...";
  meta.innerHTML = "";

  const formData = new FormData(form);
  const payload = {
    url: formData.get("url"),
    languages: String(formData.get("languages") || "vi,en")
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean),
    timestamps: formData.get("format") === "timestamp",
  };

  try {
    const response = await fetch("/api/transcript", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();

    if (!data.ok) {
      throw new Error(data.error || "Không lấy được transcript.");
    }

    currentTranscript = data.transcript;
    currentVideoId = data.videoId;
    resultTitle.textContent = "Transcript đã sẵn sàng";
    result.textContent = currentTranscript;
    renderMeta(data);
    setActions(true);
  } catch (error) {
    currentTranscript = "";
    resultTitle.textContent = "Chưa lấy được transcript";
    result.classList.add("is-error");
    result.textContent = error.message;
    setActions(false);
  } finally {
    setBusy(false);
  }
});

copyButton.addEventListener("click", async () => {
  if (!currentTranscript) return;
  await navigator.clipboard.writeText(currentTranscript);
  copyButton.textContent = "Đã copy";
  window.setTimeout(() => {
    copyButton.textContent = "Copy";
  }, 1400);
});

downloadButton.addEventListener("click", () => {
  if (!currentTranscript) return;
  const blob = new Blob([currentTranscript], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${currentVideoId}-transcript.txt`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
});
