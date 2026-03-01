/* SnapXAI – Product Catalog Generator – Frontend Logic */

(function () {
  "use strict";

  // ── Element refs ──────────────────────────────────────────────────────────
  const dropZone       = document.getElementById("dropZone");
  const fileInput      = document.getElementById("fileInput");
  const uploadSection  = document.getElementById("uploadSection");
  const previewSection = document.getElementById("previewSection");
  const previewImage   = document.getElementById("previewImage");
  const generateBtn    = document.getElementById("generateBtn");
  const resetBtn       = document.getElementById("resetBtn");
  const loadingSection = document.getElementById("loadingSection");
  const errorBanner    = document.getElementById("errorBanner");
  const errorMessage   = document.getElementById("errorMessage");
  const errorClose     = document.getElementById("errorClose");
  const resultSection  = document.getElementById("resultSection");
  const resultImage    = document.getElementById("resultImage");
  const resultMeta     = document.getElementById("resultMeta");
  const resultTitle    = document.getElementById("resultTitle");
  const resultCategory = document.getElementById("resultCategory");
  const resultShortDesc = document.getElementById("resultShortDesc");
  const bulletList     = document.getElementById("bulletList");
  const resultLongDesc = document.getElementById("resultLongDesc");
  const tagCloud       = document.getElementById("tagCloud");
  const copyBtn        = document.getElementById("copyBtn");
  const newListingBtn  = document.getElementById("newListingBtn");

  let selectedFile = null;

  // ── Utility ───────────────────────────────────────────────────────────────
  function show(el)  { el.classList.remove("hidden"); }
  function hide(el)  { el.classList.add("hidden"); }
  function showError(msg) {
    errorMessage.textContent = msg;
    show(errorBanner);
  }

  // ── Drop-zone interaction ─────────────────────────────────────────────────
  dropZone.addEventListener("click", () => fileInput.click());
  dropZone.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") fileInput.click();
  });

  dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("drag-over");
  });
  dropZone.addEventListener("dragleave", () => dropZone.classList.remove("drag-over"));
  dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("drag-over");
    const file = e.dataTransfer?.files?.[0];
    if (file) handleFile(file);
  });

  fileInput.addEventListener("change", () => {
    if (fileInput.files?.[0]) handleFile(fileInput.files[0]);
  });

  // ── Handle file selection ─────────────────────────────────────────────────
  function handleFile(file) {
    const allowed = ["image/jpeg", "image/jpg", "image/png", "image/webp", "image/gif"];
    if (!allowed.includes(file.type)) {
      showError("Unsupported file type. Please upload a JPEG, PNG, WebP or GIF image.");
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      showError("File is too large. Maximum allowed size is 10 MB.");
      return;
    }
    hide(errorBanner);
    selectedFile = file;
    const url = URL.createObjectURL(file);
    previewImage.src = url;
    hide(uploadSection);
    hide(resultSection);
    show(previewSection);
  }

  // ── Reset ─────────────────────────────────────────────────────────────────
  function reset() {
    selectedFile = null;
    fileInput.value = "";
    hide(previewSection);
    hide(resultSection);
    hide(loadingSection);
    hide(errorBanner);
    show(uploadSection);
  }

  resetBtn.addEventListener("click", reset);
  newListingBtn.addEventListener("click", reset);

  // ── Generate ──────────────────────────────────────────────────────────────
  generateBtn.addEventListener("click", () => {
    if (!selectedFile) return;
    hide(previewSection);
    hide(errorBanner);
    show(loadingSection);

    const formData = new FormData();
    formData.append("file", selectedFile);

    fetch("/api/generate", { method: "POST", body: formData })
      .then((res) => {
        if (!res.ok) {
          return res.json().then((body) => {
            throw new Error(body?.detail || `Server error: ${res.status}`);
          });
        }
        return res.json();
      })
      .then((data) => {
        hide(loadingSection);
        if (!data.success || !data.listing) {
          showError(data.error || "Failed to generate listing. Please try again.");
          show(previewSection);
          return;
        }
        renderListing(data.listing, previewImage.src, data.image_filename);
      })
      .catch((err) => {
        hide(loadingSection);
        showError(err.message || "Network error. Please check your connection.");
        show(previewSection);
      });
  });

  // ── Render listing ────────────────────────────────────────────────────────
  function renderListing(listing, imageSrc, filename) {
    resultImage.src = imageSrc;
    resultTitle.textContent = listing.title;
    resultCategory.textContent = listing.category;
    resultShortDesc.textContent = listing.short_description;
    resultLongDesc.textContent = listing.long_description;

    // Bullet points
    bulletList.innerHTML = "";
    (listing.bullet_points || []).forEach((point) => {
      const li = document.createElement("li");
      li.textContent = point;
      bulletList.appendChild(li);
    });

    // Tags
    tagCloud.innerHTML = "";
    (listing.suggested_tags || []).forEach((tag) => {
      const span = document.createElement("span");
      span.className = "tag";
      span.textContent = `#${tag}`;
      tagCloud.appendChild(span);
    });

    // Meta sidebar
    const metaItems = [
      listing.suggested_price_range ? `💰 Price range: ${listing.suggested_price_range}` : null,
      listing.condition             ? `🏷️ Condition: ${listing.condition}`               : null,
      listing.color                 ? `🎨 Color: ${listing.color}`                        : null,
      listing.material              ? `🧵 Material: ${listing.material}`                  : null,
      listing.target_audience       ? `👥 Audience: ${listing.target_audience}`            : null,
      filename                      ? `📁 File: ${filename}`                               : null,
    ].filter(Boolean);

    resultMeta.innerHTML = metaItems.map((t) => `<span>${t}</span>`).join("");

    show(resultSection);
  }

  // ── Copy listing to clipboard ─────────────────────────────────────────────
  copyBtn.addEventListener("click", () => {
    const title    = resultTitle.textContent;
    const category = resultCategory.textContent;
    const shortDesc = resultShortDesc.textContent;
    const bullets  = Array.from(bulletList.querySelectorAll("li"))
      .map((li) => `• ${li.textContent}`)
      .join("\n");
    const longDesc = resultLongDesc.textContent;
    const tags     = Array.from(tagCloud.querySelectorAll(".tag"))
      .map((t) => t.textContent)
      .join(" ");

    const text = [
      title,
      `Category: ${category}`,
      "",
      shortDesc,
      "",
      "Key Features:",
      bullets,
      "",
      longDesc,
      "",
      `Tags: ${tags}`,
    ].join("\n");

    navigator.clipboard.writeText(text).then(() => {
      const orig = copyBtn.textContent;
      copyBtn.textContent = "✅ Copied!";
      setTimeout(() => { copyBtn.textContent = orig; }, 2000);
    });
  });

  // ── Dismiss error ─────────────────────────────────────────────────────────
  errorClose.addEventListener("click", () => hide(errorBanner));
})();
