// Dark mode handling
function initTheme() {
  const savedTheme = localStorage.getItem("theme");
  if (savedTheme) {
    document.documentElement.setAttribute("data-theme", savedTheme);
  }
  updateThemeToggleIcon();
}

function toggleTheme() {
  const newTheme = document.documentElement.classList.contains("dark")
    ? "light"
    : "dark";

  document.documentElement.setAttribute("data-theme", newTheme);
  localStorage.setItem("theme", newTheme);
  updateThemeToggleIcon();
}

function updateThemeToggleIcon() {
  const isDark =
    document.documentElement.getAttribute("data-theme") === "dark" ||
    (!document.documentElement.getAttribute("data-theme") &&
      window.matchMedia("(prefers-color-scheme: dark)").matches);
  document.documentElement.classList.toggle("dark", isDark);
  const btn = document.querySelector(".theme-toggle");
  if (btn) {
    btn.textContent = isDark ? "☀️" : "🌙";
  }
}

// Apply 0build colors before the first paint, then update the button on load.
initTheme();

// Initialize theme on load
document.addEventListener("DOMContentLoaded", initTheme);

// Metadata expansion state handling
function initMetadataState() {
  const savedState = localStorage.getItem("metadataExpanded");
  // Only apply saved state if it exists (respecting default collapsed state)
  if (savedState !== null) {
    document.querySelectorAll("details.metadata-section").forEach((details) => {
      if (savedState === "true") {
        details.setAttribute("open", "");
      } else {
        details.removeAttribute("open");
      }
    });
  }
}

function toggleMetadataState(event) {
  const isOpen = event.target.hasAttribute("open");
  localStorage.setItem("metadataExpanded", isOpen);

  // Sync state across all metadata sections
  document.querySelectorAll("details.metadata-section").forEach((details) => {
    if (isOpen) {
      details.setAttribute("open", "");
    } else {
      details.removeAttribute("open");
    }
  });
}

// Watch for dynamically loaded metadata sections
const metadataObserver = new MutationObserver((mutations) => {
  mutations.forEach((mutation) => {
    mutation.addedNodes.forEach((node) => {
      if (node.nodeType === 1) {
        // Element node
        const metadataDetails = node.querySelector("details.metadata-section");
        if (metadataDetails) {
          const savedState = localStorage.getItem("metadataExpanded");
          // Only apply saved state if it exists
          if (savedState !== null) {
            if (savedState === "true") {
              metadataDetails.setAttribute("open", "");
            } else {
              metadataDetails.removeAttribute("open");
            }
          }
          metadataDetails.addEventListener("toggle", toggleMetadataState);
        }
      }
    });
  });
});

// Start observing when DOM is loaded
document.addEventListener("DOMContentLoaded", () => {
  initMetadataState();
  metadataObserver.observe(document.body, { childList: true, subtree: true });

  // Add event listeners to existing metadata sections
  document.querySelectorAll("details.metadata-section").forEach((details) => {
    details.addEventListener("toggle", toggleMetadataState);
  });
});

// Swiper owns slide removal. HTMX only applies the out-of-band count update.
document.addEventListener("delete-successful", function (event) {
  event.target.dataset.deleteSucceeded = "true";
});

function removeDeletedSlide(form) {
  const slide = form.closest("swiper-slide");
  const swiper = document.querySelector("swiper-container")?.swiper;
  if (!slide || !swiper) return;
  const index = Array.from(swiper.slides).indexOf(slide);
  if (index < 0) return;
  swiper.removeSlide(index);
  if (navigator.vibrate) navigator.vibrate(50);
}

// Button loading state handling
function setButtonLoading(button, isLoading) {
  if (isLoading) {
    button.classList.add("loading");
    button.disabled = true;
  } else {
    button.classList.remove("loading");
    button.disabled = false;
  }
}

function showButtonFeedback(button, type, duration = 1500) {
  button.classList.remove("loading");
  button.classList.add(type);
  setTimeout(() => {
    button.classList.remove(type);
    button.disabled = false;
  }, duration);
}

// Intercept form submissions for loading states
document.addEventListener("submit", function (event) {
  const form = event.target;
  const button = form.querySelector('button[type="submit"]');

  if (
    button &&
    (button.classList.contains("delete-image") ||
      button.classList.contains("show-in-finder"))
  ) {
    setButtonLoading(button, true);

    // For delete action, add optimistic animation
    if (button.classList.contains("delete-image")) {
      const slide = button.closest(".swiper-slide");
      if (slide) {
        slide.classList.add("deleting");
      }
    }
  }
});

// Handle successful actions
document.addEventListener("htmx:afterRequest", function (event) {
  const button = event.detail.elt.querySelector('button[type="submit"]');
  if (button) {
    if (event.detail.successful) {
      if (button.classList.contains("show-in-finder")) {
        showButtonFeedback(button, "success");
      } else if (button.classList.contains("delete-image")) {
        // Delete is successful, but button will be removed with the slide
        setButtonLoading(button, false);
        if (event.detail.elt.dataset.deleteSucceeded === "true") {
          removeDeletedSlide(event.detail.elt);
        }
      }
    } else {
      button.closest("swiper-slide")?.classList.remove("deleting");
      showButtonFeedback(button, "error");
    }
  }
});

// One shortcut handler keeps navigation consistent and leaves native inputs alone.
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    setFocusMode(false);
    return;
  }
  if (
    event.target.closest('input, select, textarea, [contenteditable="true"]') ||
    event.ctrlKey ||
    event.metaKey ||
    event.altKey
  )
    return;
  const key = event.key.toLowerCase();
  const routes = { a: "/", z: "/oldest", s: "/shuffled" };
  const widths = { 1: "256", 2: "512", 3: "768", 4: "1024" };
  if (routes[key] || widths[key]) {
    event.preventDefault();
    const params = new URLSearchParams(location.search);
    if (widths[key]) params.set("resize_width", widths[key]);
    location.href = (routes[key] || location.pathname) + "?" + params;
    return;
  }
  const swiper = document.querySelector("swiper-container")?.swiper;
  if (!swiper) return;
  const moves = { n: 1, p: -1, j: -10, k: 10 };
  if (moves[key]) {
    event.preventDefault();
    swiper.slideTo(
      Math.max(
        0,
        Math.min(swiper.slides.length - 1, swiper.activeIndex + moves[key]),
      ),
    );
  } else if (key === "home" || key === "end" || key === "e") {
    event.preventDefault();
    swiper.slideTo(key === "home" ? 0 : swiper.slides.length - 1);
  } else if (key === "d" || key === "f") {
    if (!event.repeat)
      document
        .querySelector(
          `.swiper-slide-active .${key === "d" ? "delete-image" : "show-in-finder"}`,
        )
        ?.click();
  } else if (key === "m") {
    const metadata = document.querySelector(
      ".swiper-slide-active .metadata-section",
    );
    if (metadata) metadata.open = !metadata.open;
  } else if (key === "h") {
    const help = document.getElementById("keyboard-controls");
    help.open = !help.open;
  } else if (key === "v") {
    event.preventDefault();
    setFocusMode(!document.documentElement.classList.contains("focus-mode"));
  }
});

// Delegation also covers slides inserted after the initial page load.
document.addEventListener("click", async function (event) {
  const button = event.target.closest(".copy-filename, .copy-prompt");
  if (!button) return;
  const isPrompt = button.classList.contains("copy-prompt");
  const filename = isPrompt
    ? button.closest(".metadata-section").querySelector(".prompt-text")
        .textContent
    : button.dataset.filename;
  const hint = isPrompt ? button : button.querySelector(".copy-hint");
  button.disabled = true;
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(filename);
    } else {
      // Local HTTP galleries may not have access to the Clipboard API.
      const field = document.createElement("textarea");
      field.value = filename;
      field.style.cssText = "position:fixed;left:-9999px;top:0";
      document.body.appendChild(field);
      try {
        field.select();
        if (!document.execCommand("copy")) throw new Error("Copy unavailable");
      } finally {
        field.remove();
      }
    }
    hint.textContent = "Copied!";
  } catch {
    hint.textContent = "Copy failed";
  } finally {
    button.classList.add("copy-feedback");
    button.disabled = false;
    button.focus({ preventScroll: true });
    clearTimeout(button.copyFeedbackTimer);
    button.copyFeedbackTimer = setTimeout(() => {
      hint.textContent = isPrompt ? "Copy prompt" : "Copy filename";
      button.classList.remove("copy-feedback");
    }, 1800);
  }
});

function updateNavigation() {
  const swiper = document.querySelector("swiper-container")?.swiper;
  if (!swiper) return;
  const count = swiper.slides.length;
  const position = document.getElementById("slide-position");
  position.textContent = `${count ? swiper.activeIndex + 1 : 0} of ${count}`;
  document.getElementById("empty-gallery").hidden = count > 0;
  document.querySelectorAll("[data-step]").forEach((button) => {
    button.disabled =
      !count ||
      (Number(button.dataset.step) < 0 ? swiper.isBeginning : swiper.isEnd);
  });
  swiper.updateAutoHeight(0);
  updateGalleryImages();
  updateFilmstrip();
}
document.addEventListener("DOMContentLoaded", () => {
  const container = document.querySelector("swiper-container");
  ["swiperinit", "swiperslidechange", "swiperslideslengthchange"].forEach(
    (event) => {
      container.addEventListener(event, updateNavigation);
    },
  );
  updateNavigation();
});
document.addEventListener("click", (event) => {
  const button = event.target.closest("[data-step]");
  if (!button) return;
  const swiper = document.querySelector("swiper-container").swiper;
  swiper.slideTo(
    Math.max(
      0,
      Math.min(
        swiper.slides.length - 1,
        swiper.activeIndex + Number(button.dataset.step),
      ),
    ),
  );
});
document.addEventListener(
  "toggle",
  () => {
    document.querySelector("swiper-container")?.swiper?.updateAutoHeight(0);
  },
  true,
);
document.addEventListener("htmx:afterSettle", updateNavigation);

function setFocusMode(enabled) {
  document.documentElement.classList.toggle("focus-mode", enabled);
  const button = document.querySelector('[data-action="focus"]');
  button.setAttribute("aria-pressed", String(enabled));
  button.textContent = enabled ? "Exit focus" : "Focus";
  document.querySelector("swiper-container")?.swiper?.update();
}
document.addEventListener("click", (event) => {
  if (event.target.closest('[data-action="focus"]')) {
    setFocusMode(!document.documentElement.classList.contains("focus-mode"));
  }
});
// Retain only the previous, current, and next image bodies. At most two
// requests run for a stable position; obsolete requests are aborted on jumps.
const imageRequests = new Map();
function resetImageLoader(loader) {
  imageRequests.get(loader)?.abort();
  imageRequests.delete(loader);
  if (loader.placeholderHTML !== undefined)
    loader.innerHTML = loader.placeholderHTML;
  delete loader.dataset.loaded;
  delete loader.dataset.failed;
  loader.setAttribute("aria-busy", "true");
}
async function loadGalleryImage(loader) {
  if (
    !loader ||
    loader.dataset.loaded ||
    loader.dataset.failed ||
    imageRequests.has(loader)
  )
    return;
  loader.placeholderHTML ??= loader.innerHTML;
  const controller = new AbortController();
  imageRequests.set(loader, controller);
  loader.setAttribute("aria-busy", "true");
  try {
    const response = await fetch(loader.dataset.imageUrl, {
      headers: { "HX-Request": "true" },
      signal: controller.signal,
    });
    if (!response.ok) throw new Error("Image request failed");
    const html = await response.text();
    if (controller.signal.aborted || !loader.isConnected) return;
    const content = document.createElement("template");
    content.innerHTML = html;
    if (!content.content.querySelector("img"))
      throw new Error("Image unavailable");
    loader.replaceChildren(content.content);
    loader.dataset.loaded = "true";
  } catch (error) {
    if (controller.signal.aborted || !loader.isConnected) return;
    loader.dataset.failed = "true";
    const message = document.createElement("div");
    message.className = "image-load-error";
    message.setAttribute("role", "status");
    message.append("Could not load this image. ");
    const retry = document.createElement("button");
    retry.type = "button";
    retry.className = "z-button z-button-default";
    retry.dataset.action = "retry-image";
    retry.textContent = "Retry";
    message.append(retry);
    loader.replaceChildren(message);
  } finally {
    if (imageRequests.get(loader) === controller) {
      imageRequests.delete(loader);
      loader.setAttribute("aria-busy", "false");
      document.querySelector("swiper-container")?.swiper?.updateAutoHeight(0);
    }
  }
}
function updateGalleryImages() {
  const swiper = document.querySelector("swiper-container")?.swiper;
  if (!swiper) return;
  const keep = new Set(
    Array.from(swiper.slides)
      .slice(Math.max(0, swiper.activeIndex - 1), swiper.activeIndex + 2)
      .map((slide) => slide.querySelector(".image-loader")),
  );
  for (const loader of imageRequests.keys()) {
    if (!keep.has(loader)) resetImageLoader(loader);
  }
  document
    .querySelectorAll(".image-loader[data-loaded], .image-loader[data-failed]")
    .forEach((loader) => {
      if (!keep.has(loader)) resetImageLoader(loader);
    });
  loadGalleryImage(
    swiper.slides[swiper.activeIndex]?.querySelector(".image-loader"),
  );
  loadGalleryImage(
    swiper.slides[swiper.activeIndex + 1]?.querySelector(".image-loader"),
  );
}
document.addEventListener("click", (event) => {
  const retry = event.target.closest('[data-action="retry-image"]');
  if (!retry) return;
  const loader = retry.closest(".image-loader");
  resetImageLoader(loader);
  loadGalleryImage(loader);
});

let thumbnailObserver;
function updateFilmstrip() {
  const strip = document.getElementById("filmstrip");
  if (strip.hidden) return;
  const swiper = document.querySelector("swiper-container").swiper;
  const items = document.getElementById("filmstrip-items");
  const start = Math.floor(swiper.activeIndex / 9) * 9;
  const slides = Array.from(swiper.slides).slice(start, start + 9);
  const key = slides.map((slide) => slide.id).join("|");
  if (items.dataset.window !== key) {
    thumbnailObserver?.disconnect();
    items.replaceChildren();
    items.dataset.window = key;
    thumbnailObserver = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting && entry.target.dataset.src) {
            entry.target.src = entry.target.dataset.src;
            delete entry.target.dataset.src;
            thumbnailObserver.unobserve(entry.target);
          }
        });
      },
      { root: items, rootMargin: "0px 64px" },
    );
    slides.forEach((slide, offset) => {
      const button = document.createElement("button");
      button.type = "button";
      button.dataset.slideId = slide.id;
      const path = slide.querySelector('input[name="gallery_path"]').value;
      button.setAttribute("aria-label", `Image ${start + offset + 1}: ${path}`);
      button.title = path;
      const image = document.createElement("img");
      image.width = 128;
      image.height = 96;
      image.alt = path;
      image.decoding = "async";
      image.dataset.src =
        "/thumbnail?" + new URLSearchParams({ gallery_path: path });
      button.append(image);
      items.append(button);
      thumbnailObserver.observe(image);
    });
  }
  items.querySelectorAll("button").forEach((button) => {
    const active =
      button.dataset.slideId === swiper.slides[swiper.activeIndex]?.id;
    button.setAttribute("aria-current", String(active));
    if (active) button.scrollIntoView({ block: "nearest", inline: "nearest" });
  });
}
document.addEventListener("click", (event) => {
  const toggle = event.target.closest('[data-action="filmstrip"]');
  if (toggle) {
    const strip = document.getElementById("filmstrip");
    strip.hidden = !strip.hidden;
    toggle.setAttribute("aria-expanded", String(!strip.hidden));
    if (strip.hidden) {
      thumbnailObserver?.disconnect();
      const items = document.getElementById("filmstrip-items");
      items.replaceChildren();
      delete items.dataset.window;
    } else updateFilmstrip();
  }
  const thumbnail = event.target.closest("[data-slide-id]");
  if (thumbnail) {
    const swiper = document.querySelector("swiper-container").swiper;
    const index = Array.from(swiper.slides).findIndex(
      (slide) => slide.id === thumbnail.dataset.slideId,
    );
    if (index >= 0) swiper.slideTo(index);
  }
});
