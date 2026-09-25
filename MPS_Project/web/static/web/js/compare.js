import { escapeHtml, pluralize, storage } from "./utils.js";

const KEY = "compare";
const LIMIT = 3;

const tray = document.querySelector("[data-compare-tray]");
let selection = storage.get(KEY, []).filter((item) => Number.isInteger(item?.id));

function render() {
  for (const button of document.querySelectorAll("[data-compare-toggle]")) {
    const selected = selection.some((item) => item.id === Number(button.dataset.id));
    button.setAttribute("aria-pressed", String(selected));
  }
  if (!tray) return;

  const count = selection.length;
  tray.classList.toggle("is-visible", count > 0);
  tray.querySelector("[data-compare-count]").textContent =
    count < 2
      ? "Выберите ещё хотя бы один самолёт"
      : `${count} ${pluralize(count, "самолёт", "самолёта", "самолётов")} для сравнения`;
  tray.querySelector("[data-compare-names]").innerHTML = selection.map((item) => escapeHtml(item.name)).join(" · ");

  const link = tray.querySelector("[data-compare-link]");
  link.href = `${tray.dataset.compareUrl}?ids=${selection.map((item) => item.id).join(",")}`;
  link.toggleAttribute("aria-disabled", count < 2);
}

function toggle(id, name) {
  if (selection.some((item) => item.id === id)) {
    selection = selection.filter((item) => item.id !== id);
  } else {
    selection = [...selection, { id, name }].slice(-LIMIT);
  }
  storage.set(KEY, selection);
  render();
}

document.addEventListener("click", (event) => {
  const button = event.target.closest("[data-compare-toggle]");
  if (button) {
    event.preventDefault();
    toggle(Number(button.dataset.id), button.dataset.name);
  }
  if (event.target.closest("[data-compare-clear]")) {
    selection = [];
    storage.set(KEY, selection);
    render();
  }
});

window.addEventListener("storage", (event) => {
  if (event.key === KEY) {
    selection = storage.get(KEY, []);
    render();
  }
});

render();
