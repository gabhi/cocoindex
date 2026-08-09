function initTabs() {
  const buttons = document.querySelectorAll("nav.tabs button");
  const panels = document.querySelectorAll(".tab-panel");
  buttons.forEach((btn) => {
    btn.addEventListener("click", () => {
      buttons.forEach((b) => b.classList.remove("active"));
      panels.forEach((p) => p.classList.remove("active"));
      btn.classList.add("active");
      document.getElementById(btn.dataset.target).classList.add("active");
    });
  });
}

function initSplitterDemo() {
  const runBtn = document.getElementById("splitter-run");
  const results = document.getElementById("splitter-results");
  if (!runBtn) return;

  async function run() {
    runBtn.disabled = true;
    runBtn.textContent = "Chunking...";
    results.innerHTML = "";
    try {
      const res = await fetch("/api/chunk", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: document.getElementById("splitter-text").value,
          language: document.getElementById("splitter-language").value,
          chunk_size: Number(document.getElementById("splitter-chunk-size").value),
          chunk_overlap: Number(document.getElementById("splitter-chunk-overlap").value),
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        results.innerHTML = `<p class="error">${data.detail || "Something went wrong."}</p>`;
        return;
      }
      if (data.count === 0) {
        results.innerHTML = '<p class="empty">No chunks produced.</p>';
        return;
      }
      results.innerHTML = data.chunks
        .map(
          (c) => `
        <div class="chunk-card">
          <div class="chunk-meta">#${c.index} · chars ${c.char_start}-${c.char_end} · lines ${c.line_start}-${c.line_end}</div>
          <div class="chunk-text"></div>
        </div>
      `
        )
        .join("");
      document.querySelectorAll("#splitter-results .chunk-text").forEach((el, i) => {
        el.textContent = data.chunks[i].text;
      });
    } catch (err) {
      results.innerHTML = `<p class="error">${err}</p>`;
    } finally {
      runBtn.disabled = false;
      runBtn.textContent = "Chunk it";
    }
  }

  runBtn.addEventListener("click", run);
  run();
}

function initMarkdownDemo() {
  const runBtn = document.getElementById("markdown-run");
  const results = document.getElementById("markdown-results");
  if (!runBtn) return;

  async function run() {
    runBtn.disabled = true;
    runBtn.textContent = "Rendering...";
    try {
      const res = await fetch("/api/markdown", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: document.getElementById("markdown-text").value,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        results.innerHTML = `<p class="error">${data.detail || "Something went wrong."}</p>`;
        return;
      }
      // Rendered via gfm-like preset (html: true), so the output can contain
      // raw HTML/script tags from the input. A sandboxed iframe with no
      // "allow-scripts" keeps that content isolated from this page.
      results.innerHTML = "";
      const frame = document.createElement("iframe");
      frame.sandbox = "";
      frame.className = "markdown-frame";
      results.appendChild(frame);
      frame.srcdoc = data.html;
    } catch (err) {
      results.innerHTML = `<p class="error">${err}</p>`;
    } finally {
      runBtn.disabled = false;
      runBtn.textContent = "Render it";
    }
  }

  runBtn.addEventListener("click", run);
  run();
}

function initEmbedSearchDemo() {
  const runBtn = document.getElementById("embed-run");
  const results = document.getElementById("embed-results");
  if (!runBtn) return;

  async function run() {
    runBtn.disabled = true;
    runBtn.textContent = "Searching...";
    results.innerHTML = '<p class="empty">Embedding (first run downloads the model, this can take a minute)...</p>';
    try {
      const res = await fetch("/api/embed-search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: document.getElementById("embed-text").value,
          query: document.getElementById("embed-query").value,
          language: document.getElementById("embed-language").value,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        results.innerHTML = `<p class="error">${data.detail || "Something went wrong."}</p>`;
        return;
      }
      if (data.hits.length === 0) {
        results.innerHTML = '<p class="empty">No matches found.</p>';
        return;
      }
      results.innerHTML = data.hits
        .map(
          (h) => `
        <div class="chunk-card">
          <div class="chunk-meta">score ${h.score.toFixed(3)} · chars ${h.char_start}-${h.char_end} · lines ${h.line_start}-${h.line_end}</div>
          <div class="chunk-text"></div>
        </div>
      `
        )
        .join("");
      document.querySelectorAll("#embed-results .chunk-text").forEach((el, i) => {
        el.textContent = data.hits[i].text;
      });
    } catch (err) {
      results.innerHTML = `<p class="error">${err}</p>`;
    } finally {
      runBtn.disabled = false;
      runBtn.textContent = "Search";
    }
  }

  runBtn.addEventListener("click", run);
}

function initSummarizeDemo() {
  const runBtn = document.getElementById("summarize-run");
  const results = document.getElementById("summarize-results");
  if (!runBtn) return;

  async function run() {
    runBtn.disabled = true;
    runBtn.textContent = "Summarizing...";
    results.innerHTML = '<p class="empty">Calling the LLM...</p>';
    try {
      const res = await fetch("/api/summarize-code", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: document.getElementById("summarize-text").value }),
      });
      const data = await res.json();
      if (!res.ok) {
        results.innerHTML = `<p class="error">${data.detail || "Something went wrong."}</p>`;
        return;
      }
      const classes = data.public_classes
        .map((c) => `<li><b>${c.name}</b> — ${c.summary}</li>`)
        .join("");
      const functions = data.public_functions
        .map((f) => `<li><b>${f.name}</b> — ${f.summary}</li>`)
        .join("");
      results.innerHTML = `
        <div class="chunk-card">
          <div class="chunk-meta">Summary</div>
          <div class="chunk-text">${data.summary}</div>
        </div>
        ${classes ? `<div class="chunk-card"><div class="chunk-meta">Classes</div><ul>${classes}</ul></div>` : ""}
        ${functions ? `<div class="chunk-card"><div class="chunk-meta">Functions</div><ul>${functions}</ul></div>` : ""}
      `;
    } catch (err) {
      results.innerHTML = `<p class="error">${err}</p>`;
    } finally {
      runBtn.disabled = false;
      runBtn.textContent = "Summarize it";
    }
  }

  runBtn.addEventListener("click", run);
}

function initPdfToMarkdownDemo() {
  const runBtn = document.getElementById("pdf-run");
  const results = document.getElementById("pdf-results");
  const fileInput = document.getElementById("pdf-file");
  if (!runBtn) return;

  async function run() {
    const file = fileInput.files[0];
    if (!file) {
      results.innerHTML = '<p class="error">Choose a PDF file first.</p>';
      return;
    }
    runBtn.disabled = true;
    runBtn.textContent = "Converting...";
    results.innerHTML = '<p class="empty">Converting (first run downloads layout models, this can take a minute)...</p>';
    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await fetch("/api/pdf-to-markdown", { method: "POST", body: formData });
      const data = await res.json();
      if (!res.ok) {
        results.innerHTML = `<p class="error">${data.detail || "Something went wrong."}</p>`;
        return;
      }
      results.innerHTML = '<div class="chunk-card"><div class="chunk-text"></div></div>';
      results.querySelector(".chunk-text").textContent = data.markdown;
    } catch (err) {
      results.innerHTML = `<p class="error">${err}</p>`;
    } finally {
      runBtn.disabled = false;
      runBtn.textContent = "Convert it";
    }
  }

  runBtn.addEventListener("click", run);
}

function initPatientIntakeDemo() {
  const runBtn = document.getElementById("patient-run");
  const results = document.getElementById("patient-results");
  const fileInput = document.getElementById("patient-file");
  if (!runBtn) return;

  async function run() {
    const file = fileInput.files[0];
    if (!file) {
      results.innerHTML = '<p class="error">Choose a PDF file first.</p>';
      return;
    }
    runBtn.disabled = true;
    runBtn.textContent = "Extracting...";
    results.innerHTML = '<p class="empty">Calling the LLM...</p>';
    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await fetch("/api/patient-intake", { method: "POST", body: formData });
      const data = await res.json();
      if (!res.ok) {
        results.innerHTML = `<p class="error">${data.detail || "Something went wrong."}</p>`;
        return;
      }
      results.innerHTML = '<div class="chunk-card"><div class="chunk-text"></div></div>';
      results.querySelector(".chunk-text").textContent = JSON.stringify(data.patient, null, 2);
    } catch (err) {
      results.innerHTML = `<p class="error">${err}</p>`;
    } finally {
      runBtn.disabled = false;
      runBtn.textContent = "Extract it";
    }
  }

  runBtn.addEventListener("click", run);
}

document.addEventListener("DOMContentLoaded", () => {
  initTabs();
  initSplitterDemo();
  initMarkdownDemo();
  initEmbedSearchDemo();
  initSummarizeDemo();
  initPdfToMarkdownDemo();
  initPatientIntakeDemo();
});
