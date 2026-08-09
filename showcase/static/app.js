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

document.addEventListener("DOMContentLoaded", () => {
  initTabs();
  initSplitterDemo();
  initMarkdownDemo();
});
