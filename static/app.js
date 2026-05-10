function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(";").shift();
  return "";
}

const suggestionsBox = document.getElementById("suggestions");
const searchInput = document.getElementById("searchInput");
if (searchInput) {
  searchInput.addEventListener("input", async (event) => {
    const query = event.target.value.trim();
    if (!query) {
      suggestionsBox.style.display = "none";
      return;
    }
    const response = await fetch(`/search/suggest/?q=${encodeURIComponent(query)}`);
    const data = await response.json();
    suggestionsBox.innerHTML = "";
    data.suggestions.forEach((item) => {
      const li = document.createElement("li");
      li.textContent = item;
      li.addEventListener("click", () => {
        searchInput.value = item;
        suggestionsBox.style.display = "none";
        searchInput.form.submit();
      });
      suggestionsBox.appendChild(li);
    });
    suggestionsBox.style.display = data.suggestions.length ? "block" : "none";
  });
}

const themeToggle = document.getElementById("themeToggle");
const body = document.body;
const storedTheme = localStorage.getItem("theme");
if (storedTheme) {
  body.classList.remove("theme-light", "theme-dark");
  body.classList.add(`theme-${storedTheme}`);
}
if (themeToggle) {
  themeToggle.addEventListener("click", () => {
    const current = body.classList.contains("theme-dark") ? "dark" : "light";
    const next = current === "dark" ? "light" : "dark";
    body.classList.remove("theme-light", "theme-dark");
    body.classList.add(`theme-${next}`);
    localStorage.setItem("theme", next);
  });
}

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

document.querySelectorAll(".chapter-row .eye").forEach((eye) => {
  eye.addEventListener("click", async (event) => {
    event.preventDefault();
    const chapterId = eye.closest(".chapter-row").dataset.chapter;
    const response = await fetch(`/chapter/${chapterId}/toggle-read/`, {
      method: "POST",
      headers: {
        "X-CSRFToken": getCookie("csrftoken"),
      },
    });
    if (response.ok) {
      eye.classList.toggle("read");
    }
  });
});
