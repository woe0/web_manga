function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(";").shift();
  return "";
}

// Theme toggle
(function () {
  const root = document.documentElement;
  const body = document.body;
  function applyTheme(t) {
    root.classList.remove("theme-light", "theme-dark");
    body.classList.remove("theme-light", "theme-dark");
    root.classList.add("theme-" + t);
    body.classList.add("theme-" + t);
    localStorage.setItem("theme", t);
    document.cookie = "theme=" + t + ";path=/;max-age=" + 60 * 60 * 24 * 365;
  }
  const saved = localStorage.getItem("theme") || "light";
  applyTheme(saved);
  const themeToggle = document.getElementById("themeToggle");
  if (themeToggle) {
    themeToggle.addEventListener("click", () => {
      const current = body.classList.contains("theme-dark") ? "dark" : "light";
      applyTheme(current === "dark" ? "light" : "dark");
    });
  }
})();

// Mobile nav
const navToggle = document.getElementById("navToggle");
const mainNav = document.getElementById("mainNav");
if (navToggle && mainNav) {
  navToggle.addEventListener("click", () => mainNav.classList.toggle("open"));
}

// Search suggestions
const suggestionsBox = document.getElementById("suggestions");
const searchInput = document.getElementById("searchInput");
let searchTimer = null;
if (searchInput && suggestionsBox) {
  searchInput.addEventListener("input", (event) => {
    const query = event.target.value.trim();
    clearTimeout(searchTimer);
    if (!query) {
      suggestionsBox.style.display = "none";
      return;
    }
    searchTimer = setTimeout(async () => {
      try {
        const response = await fetch(`/search/suggest/?q=${encodeURIComponent(query)}`);
        const data = await response.json();
        suggestionsBox.innerHTML = "";
        data.suggestions.forEach((item) => {
          const li = document.createElement("li");
          li.textContent = item.title || item;
          li.addEventListener("mousedown", (e) => {
            e.preventDefault();
            if (item.url) {
              window.location.href = item.url;
            } else {
              searchInput.value = item.title || item;
              suggestionsBox.style.display = "none";
              searchInput.form.submit();
            }
          });
          suggestionsBox.appendChild(li);
        });
        suggestionsBox.style.display = data.suggestions.length ? "block" : "none";
      } catch (e) {
        suggestionsBox.style.display = "none";
      }
    }, 150);
  });
  document.addEventListener("click", (e) => {
    if (!suggestionsBox.contains(e.target) && e.target !== searchInput) {
      suggestionsBox.style.display = "none";
    }
  });
}

// Reader modes
const reader = document.getElementById("reader");
const storedMode = localStorage.getItem("reader_mode") || "vertical";
if (reader) {
  reader.classList.remove("vertical", "horizontal", "webtoon");
  reader.classList.add(storedMode);
  if (localStorage.getItem("merge_pages") === "true") {
    reader.classList.add("merge");
  }
}
document.querySelectorAll("[data-mode]").forEach((button) => {
  button.addEventListener("click", () => {
    if (reader) {
      reader.classList.remove("vertical", "horizontal", "webtoon");
      reader.classList.add(button.dataset.mode);
    }
    localStorage.setItem("reader_mode", button.dataset.mode);
  });
});
const mergeToggle = document.getElementById("mergeToggle");
if (mergeToggle) {
  mergeToggle.addEventListener("click", () => {
    let isMerged = localStorage.getItem("merge_pages") === "true";
    if (reader) {
      reader.classList.toggle("merge");
      isMerged = reader.classList.contains("merge");
    } else {
      isMerged = !isMerged;
    }
    localStorage.setItem("merge_pages", isMerged);
  });
}

// Toggle "read" eye
document.querySelectorAll(".chapter-row .eye").forEach((eye) => {
  eye.addEventListener("click", async (event) => {
    event.preventDefault();
    const chapterId = eye.closest(".chapter-row").dataset.chapter;
    const response = await fetch(`/chapter/${chapterId}/toggle-read/`, {
      method: "POST",
      headers: { "X-CSRFToken": getCookie("csrftoken") },
    });
    if (response.ok) eye.classList.toggle("read");
  });
});

// Spoiler reveal on click
document.querySelectorAll(".spoiler-text").forEach((el) => {
  el.addEventListener("click", () => el.classList.toggle("revealed"));
});

// Reply toggle
document.querySelectorAll(".reply-toggle").forEach((btn) => {
  btn.addEventListener("click", () => {
    const target = document.querySelector(btn.dataset.target);
    if (target) target.classList.toggle("open");
  });
});

// Profile list tabs
const tabs = document.querySelectorAll(".lists-tabs button");
if (tabs.length) {
  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      tabs.forEach((t) => t.classList.remove("active"));
      tab.classList.add("active");
      const filter = tab.dataset.filter;
      document.querySelectorAll(".list-entry").forEach((entry) => {
        entry.style.display =
          filter === "all" || entry.dataset.list === filter ? "" : "none";
      });
    });
  });
}
