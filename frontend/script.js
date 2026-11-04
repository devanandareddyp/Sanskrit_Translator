/* Sanskrit Translator frontend. Keep API calls in this file. */
const API_BASE_URL = "https://sanskrit-translator-api.onrender.com";
const $ = (id) => document.getElementById(id);
let lastTranslation = "";

function setMessage(id, message, type = "") {
  const el = $(id);
  el.textContent = message;
  el.className = `message ${type}`.trim();
}
function setBusy(button, busy, busyText = "Working...") {
  if (busy) {
    button.dataset.originalText = button.textContent;
    button.textContent = busyText;
    button.disabled = true;
  } else {
    button.textContent = button.dataset.originalText || button.textContent;
    button.disabled = false;
  }
}
async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = typeof data.detail === "string" ? data.detail : `Request failed (HTTP ${response.status}).`;
    throw new Error(detail);
  }
  return data;
}
async function checkBackend() {
  const button = $("checkBackendBtn");
  const status = $("backendStatus");
  setBusy(button, true, "Checking...");
  status.textContent = "Checking backend...";
  status.className = "status status-unknown";
  try {
    const data = await fetchJson(`${API_BASE_URL}/health`);
    status.textContent = data.loaded ? "Backend connected · model loaded" : "Backend connected · model not loaded yet";
    status.className = "status status-ok";
  } catch (error) {
    status.textContent = "Backend unavailable";
    status.className = "status status-error";
    console.error("Backend health check failed:", error);
  } finally {
    setBusy(button, false);
  }
}
function downloadText(filename, text) {
  const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
function showTab(panelId) {
  document.querySelectorAll(".tab").forEach((tab) => {
    const active = tab.dataset.tab === panelId;
    tab.classList.toggle("active", active);
    tab.setAttribute("aria-selected", String(active));
  });
  document.querySelectorAll(".tab-panel").forEach((panel) => panel.classList.toggle("hidden", panel.id !== panelId));
}

 document.querySelectorAll(".tab").forEach((tab) => tab.addEventListener("click", () => showTab(tab.dataset.tab)));
$("checkBackendBtn").addEventListener("click", checkBackend);
$("sourceText").addEventListener("input", () => { $("charCount").textContent = `${$("sourceText").value.length} / 30000`; });
$("clearBtn").addEventListener("click", () => {
  $("sourceText").value = "";
  $("charCount").textContent = "0 / 30000";
  $("translationOutput").textContent = "Your English translation will appear here.";
  $("translationStatus").textContent = "Ready to translate";
  lastTranslation = "";
  setMessage("textMessage", "");
});
$("copyBtn").addEventListener("click", async () => {
  if (!lastTranslation) return setMessage("textMessage", "There is no translation to copy yet.", "error");
  try { await navigator.clipboard.writeText(lastTranslation); setMessage("textMessage", "Translation copied to clipboard.", "success"); }
  catch { setMessage("textMessage", "Clipboard access was blocked by the browser.", "error"); }
});
$("translateBtn").addEventListener("click", async () => {
  const text = $("sourceText").value.trim();
  if (!text) return setMessage("textMessage", "Enter Sanskrit text before translating.", "error");
  const button = $("translateBtn");
  setBusy(button, true, "Translating...");
  setMessage("textMessage", "Translation may take a while the first time.");
  $("translationStatus").textContent = "Translating...";
  $("translationOutput").textContent = "Please wait while the model translates your text...";
  try {
    const data = await fetchJson(`${API_BASE_URL}/translate`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text }) });
    lastTranslation = data.translation || data.translated_text || "";
    $("translationOutput").textContent = lastTranslation || "The model returned an empty translation.";
    $("translationStatus").textContent = "Translation complete";
    setMessage("textMessage", "Translation completed.", "success");
  } catch (error) {
    $("translationOutput").textContent = "Translation failed. Check the backend terminal for details.";
    $("translationStatus").textContent = "Translation failed";
    setMessage("textMessage", error.message, "error");
    console.error(error);
  } finally { setBusy(button, false); }
});

$("pdfFile").addEventListener("change", () => { $("pdfFileName").textContent = $("pdfFile").files[0]?.name || "No file selected"; });
$("translatePdfBtn").addEventListener("click", async () => {
  const file = $("pdfFile").files[0];
  if (!file) return setMessage("pdfMessage", "Choose a PDF file first.", "error");
  if (file.size > 15 * 1024 * 1024) return setMessage("pdfMessage", "The file exceeds the 15 MB limit.", "error");
  const button = $("translatePdfBtn"); const form = new FormData(); form.append("file", file);
  setBusy(button, true, "Processing PDF..."); setMessage("pdfMessage", "Extracting and translating pages...");
  try {
    const data = await fetchJson(`${API_BASE_URL}/translate/pdf`, { method: "POST", body: form });
    $("pdfOutput").textContent = data.translation || "No readable text was found.";
    $("pdfResult").classList.remove("hidden"); setMessage("pdfMessage", "PDF processing completed.", "success");
  } catch (error) { setMessage("pdfMessage", error.message, "error"); console.error(error); }
  finally { setBusy(button, false); }
});
$("downloadPdfTextBtn").addEventListener("click", () => downloadText("sanskrit-translation.txt", $("pdfOutput").textContent));

$("imageFile").addEventListener("change", () => { $("imageFileName").textContent = $("imageFile").files[0]?.name || "No file selected"; });
$("translateImageBtn").addEventListener("click", async () => {
  const file = $("imageFile").files[0];
  if (!file) return setMessage("imageMessage", "Choose an image first.", "error");
  if (file.size > 15 * 1024 * 1024) return setMessage("imageMessage", "The file exceeds the 15 MB limit.", "error");
  const button = $("translateImageBtn"); const form = new FormData(); form.append("file", file);
  setBusy(button, true, "Extracting and translating..."); setMessage("imageMessage", "Running Sanskrit OCR and translation...");
  try {
    const data = await fetchJson(`${API_BASE_URL}/translate/image`, { method: "POST", body: form });
    $("extractedText").value = data.extracted_text || "";
    $("imageOutput").textContent = data.translation || "No readable Sanskrit text was found.";
    $("imageResult").classList.remove("hidden"); setMessage("imageMessage", "Image processing completed.", "success");
  } catch (error) { setMessage("imageMessage", error.message, "error"); console.error(error); }
  finally { setBusy(button, false); }
});
$("downloadImageTextBtn").addEventListener("click", () => downloadText("image-sanskrit-translation.txt", $("imageOutput").textContent));

// Run a lightweight health check when the page opens.
checkBackend();
