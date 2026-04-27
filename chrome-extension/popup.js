const DEFAULT_ENDPOINT = "http://localhost:15200";

document.addEventListener("DOMContentLoaded", async () => {
  const settings = await chrome.storage.local.get([
    "endpoint",
    "token",
    "useLlm",
  ]);
  document.getElementById("endpoint").value =
    settings.endpoint || DEFAULT_ENDPOINT;
  document.getElementById("token").value = settings.token || "";
  document.getElementById("use-llm").checked = settings.useLlm !== false;

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

  document.getElementById("title").value = tab.title || "";
  document.getElementById("url").value = tab.url || "";

  try {
    const [result] = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: () => {
        const canonicalUrl =
          document.querySelector('link[rel~="canonical" i]')?.href || "";
        const selection = window.getSelection().toString().trim();
        if (selection) return { content: selection, canonicalUrl };

        const NOISE =
          "nav,header,footer,aside,.sidebar,.menu,.nav,.ad,.advertisement,.cookie-banner,[role=navigation],[role=banner],[role=contentinfo]";
        const clone = document.body.cloneNode(true);
        clone.querySelectorAll(NOISE).forEach((el) => el.remove());
        clone
          .querySelectorAll("script,style,noscript,svg,iframe")
          .forEach((el) => el.remove());

        const article = clone.querySelector("article");
        const main = clone.querySelector("main,[role=main]");
        const target = article || main || clone;

        const lines = target.innerText
          .split("\n")
          .map((l) => l.trim())
          .filter((l) => l.length > 0);

        const deduped = lines.filter((l, i) => i === 0 || l !== lines[i - 1]);
        return {
          content: deduped.join("\n").slice(0, 10000),
          canonicalUrl,
        };
      },
    });
    if (result?.result?.content) {
      document.getElementById("content").value = result.result.content;
    }
    if (result?.result?.canonicalUrl) {
      document.getElementById("canonical-url").value = result.result.canonicalUrl;
    }
  } catch {
    // content script may not be injected (e.g. chrome:// pages)
  }

  document.getElementById("clip").addEventListener("click", handleClip);
  document.getElementById("toggle-settings").addEventListener("click", () => {
    document.getElementById("settings-panel").classList.toggle("open");
  });
  document
    .getElementById("save-settings")
    .addEventListener("click", saveSettings);
  document.getElementById("check-token").addEventListener("click", checkToken);
  document
    .getElementById("use-llm")
    .addEventListener("change", async (event) => {
      await chrome.storage.local.set({ useLlm: event.target.checked });
    });
});

async function handleClip() {
  const btn = document.getElementById("clip");
  const statusEl = document.getElementById("status");
  btn.disabled = true;
  btn.textContent = "Saving...";
  statusEl.className = "status";
  statusEl.style.display = "none";

  const settings = await chrome.storage.local.get(["endpoint", "token"]);
  const endpoint = (settings.endpoint || DEFAULT_ENDPOINT).replace(/\/+$/, "");
  const token = settings.token || "";

  const title = document.getElementById("title").value.trim();
  const url = document.getElementById("url").value.trim();
  const canonicalUrl = document.getElementById("canonical-url").value.trim();
  const tagsRaw = document.getElementById("tags").value.trim();
  const content = document.getElementById("content").value.trim();

  if (!title) {
    showStatus("error", "Title is required");
    btn.disabled = false;
    btn.textContent = "Clip";
    return;
  }

  if (!token) {
    showStatus("error", "Bearer token is required. Open Settings.");
    btn.disabled = false;
    btn.textContent = "Clip";
    return;
  }

  const tags = tagsRaw
    ? tagsRaw
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean)
    : [];
  const skipLlm = !document.getElementById("use-llm").checked;

  const payload = {
    title,
    url,
    canonical_url: canonicalUrl || null,
    content: content || null,
    tags,
    skip_llm: skipLlm,
  };

  const headers = { "Content-Type": "application/json" };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  try {
    const res = await fetch(`${endpoint}/api/clip`, {
      method: "POST",
      headers,
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const text = await res.text();
      throw new Error(`${res.status}: ${text}`);
    }

    const result = await res.json();
    const mode = result.capture_mode === "ai" ? "AI summary" : "mechanical text";
    showStatus("success", `Clipped with ${mode}`);
    setTimeout(() => window.close(), 1200);
  } catch (err) {
    showStatus("error", err.message);
    btn.disabled = false;
    btn.textContent = "Clip";
  }
}

function showStatus(type, message) {
  const el = document.getElementById("status");
  el.textContent = message;
  el.className = `status ${type}`;
}

async function saveSettings() {
  const endpoint = document
    .getElementById("endpoint")
    .value.trim()
    .replace(/\/+$/, "");
  const token = document.getElementById("token").value.trim();
  const useLlm = document.getElementById("use-llm").checked;
  await chrome.storage.local.set({ endpoint, token, useLlm });
  showStatus("success", "Settings saved");
}

async function checkToken() {
  const endpoint = document
    .getElementById("endpoint")
    .value.trim()
    .replace(/\/+$/, "");
  const token = document.getElementById("token").value.trim();

  if (!endpoint) {
    showStatus("error", "API Endpoint is required.");
    return;
  }

  if (!token) {
    showStatus("error", "Bearer Token is required.");
    return;
  }

  try {
    const res = await fetch(`${endpoint}/api/auth/check`, {
      method: "GET",
      headers: { Authorization: `Bearer ${token}` },
    });

    if (res.ok) {
      await chrome.storage.local.set({ endpoint, token });
      showStatus("success", "接続できました。token は有効です。");
      return;
    }

    if (res.status === 401) {
      showStatus(
        "error",
        "Authorization header がありません。token を確認してください。",
      );
    } else if (res.status === 403) {
      showStatus(
        "error",
        "token が一致しません。reset-token 後の値を貼ってください。",
      );
    } else if (res.status === 503) {
      showStatus("error", "server 側に BRAIN_API_TOKEN が設定されていません。");
    } else {
      const text = await res.text();
      showStatus("error", `${res.status}: ${text}`);
    }
  } catch (err) {
    showStatus("error", `server に接続できません: ${err.message}`);
  }
}
