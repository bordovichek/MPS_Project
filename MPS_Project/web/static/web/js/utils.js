const ESCAPES = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };

export const escapeHtml = (value) => String(value).replace(/[&<>"']/g, (char) => ESCAPES[char]);

export const icon = (name, className = "") =>
  `<svg class="icon ${className}" aria-hidden="true" focusable="false"><use href="${document.body.dataset.icons}#i-${name}"></use></svg>`;

export function formatNumber(value, digits = 0) {
  return new Intl.NumberFormat("ru-RU", { minimumFractionDigits: digits, maximumFractionDigits: digits }).format(value);
}

export function formatDuration(hours) {
  const total = Math.round(hours * 60);
  const h = Math.floor(total / 60);
  const m = total % 60;
  if (!h) return `${m} мин`;
  return m ? `${h} ч ${String(m).padStart(2, "0")} мин` : `${h} ч`;
}

export function formatMass(kg) {
  return kg >= 1000 ? `${formatNumber(kg / 1000, 1)} т` : `${formatNumber(kg)} кг`;
}

export function pluralize(count, one, few, many) {
  const mod10 = count % 10;
  const mod100 = count % 100;
  if (mod10 === 1 && mod100 !== 11) return one;
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return few;
  return many;
}

export function flag(code) {
  if (!/^[A-Za-z]{2}$/.test(code ?? "")) return "";
  return String.fromCodePoint(...[...code.toUpperCase()].map((char) => 0x1f1e6 + char.charCodeAt(0) - 65));
}

export const cssVar = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

export const onThemeChange = (callback) => document.addEventListener("themechange", callback);

export function debounce(callback, delay) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => callback(...args), delay);
  };
}

export const storage = {
  get(key, fallback = null) {
    try {
      const raw = localStorage.getItem(key);
      return raw === null ? fallback : JSON.parse(raw);
    } catch {
      return fallback;
    }
  },
  set(key, value) {
    try {
      localStorage.setItem(key, JSON.stringify(value));
    } catch {
      /* приватный режим или запрещённое хранилище — просто не запоминаем */
    }
  },
};
