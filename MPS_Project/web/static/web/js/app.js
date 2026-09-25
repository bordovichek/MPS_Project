const root = document.documentElement;

function readTheme() {
  try {
    return localStorage.getItem("theme");
  } catch {
    return null;
  }
}

function applyTheme(theme, remember) {
  root.dataset.theme = theme;
  if (remember) {
    try {
      localStorage.setItem("theme", theme);
    } catch {
      /* тема просто не запомнится */
    }
  }
  document.dispatchEvent(new CustomEvent("themechange", { detail: { theme } }));
}

document.querySelector("[data-theme-toggle]")?.addEventListener("click", () => {
  applyTheme(root.dataset.theme === "dark" ? "light" : "dark", true);
});

matchMedia("(prefers-color-scheme: dark)").addEventListener("change", (event) => {
  if (!readTheme()) applyTheme(event.matches ? "dark" : "light", false);
});

const header = document.querySelector(".site-header");
const navToggle = document.querySelector(".nav-toggle");
navToggle?.addEventListener("click", () => {
  const open = header.classList.toggle("nav-open");
  navToggle.setAttribute("aria-expanded", String(open));
});

for (const form of document.querySelectorAll("form[data-autosubmit]")) {
  form.addEventListener("change", (event) => {
    if (event.target.matches("select, input[type=radio], input[type=checkbox]")) form.requestSubmit();
  });
}

// Пустые поля не попадают в адрес: ?q=&country= превращается в чистый URL.
for (const form of document.querySelectorAll("form[data-clean-empty]")) {
  form.addEventListener("submit", () => {
    for (const field of form.elements) {
      if (field.name && !field.value && field.type !== "radio") field.disabled = true;
    }
    for (const radio of form.querySelectorAll("input[type=radio]:checked")) {
      if (!radio.value) radio.disabled = true;
    }
    setTimeout(() => {
      for (const field of form.elements) field.disabled = false;
    });
  });
}

if (matchMedia("(prefers-reduced-motion: reduce)").matches) {
  for (const svg of document.querySelectorAll("svg")) svg.pauseAnimations?.();
}
