import { WORLD_OFFSETS, createMap, unwrapLongitude } from "./map-base.js";
import {
  cssVar,
  debounce,
  escapeHtml,
  flag,
  formatDuration,
  formatMass,
  formatNumber,
  icon,
  onThemeChange,
  pluralize,
} from "./utils.js";

const L = window.L;
const data = JSON.parse(document.getElementById("planner-data").textContent);
const MAX_WAYPOINTS = data.maxWaypoints;
const DEFAULT_CRITERION = data.criteria[0].value;

/* ---------- Справочники и поиск ---------- */

const airports = data.airports.map(([code, name, country, lat, lon]) => {
  const countryName = data.countries[country] ?? country;
  return { code, name, country, countryName, lat, lon, nameKey: name.toLowerCase(), countryKey: countryName.toLowerCase() };
});
const airportsByCode = new Map(airports.map((airport) => [airport.code, airport]));
const airplanes = new Map(data.airplanes.map((plane) => [String(plane.id), plane]));

const CITY_ALIASES = {
  москва: ["SVO", "DME", "VKO"],
  "санкт-петербург": ["LED"],
  петербург: ["LED"],
  сочи: ["AER"],
  казань: ["KZN"],
  новосибирск: ["OVB"],
  екатеринбург: ["SVX"],
  владивосток: ["VVO"],
  красноярск: ["KJA"],
  иркутск: ["IKT"],
  хабаровск: ["KHV"],
  калининград: ["KGD"],
  якутск: ["YKS"],
  омск: ["OMS"],
  "петропавловск-камчатский": ["PKC"],
  "южно-сахалинск": ["UUS"],
  "минеральные воды": ["MRV"],
  минск: ["MSQ"],
  алматы: ["ALA"],
  астана: ["NQZ"],
  стамбул: ["IST", "SAW"],
  анталья: ["AYT"],
  дубай: ["DXB"],
  "абу-даби": ["AUH"],
  каир: ["CAI"],
  хургада: ["HRG"],
  "шарм-эль-шейх": ["SSH"],
  париж: ["CDG", "ORY"],
  ницца: ["NCE"],
  берлин: ["BER"],
  мюнхен: ["MUC"],
  гамбург: ["HAM"],
  пекин: ["PEK"],
  шанхай: ["PVG"],
  гуанчжоу: ["CAN"],
  токио: ["HND"],
  дели: ["DEL"],
  мумбаи: ["BOM"],
  "нью-йорк": ["JFK"],
  "лос-анджелес": ["LAX"],
  "сан-франциско": ["SFO"],
  чикаго: ["ORD"],
  майами: ["MIA"],
  сиэтл: ["SEA"],
  гонолулу: ["HNL"],
  анкоридж: ["ANC"],
  канкун: ["CUN"],
  кейптаун: ["CPT"],
  йоханнесбург: ["JNB"],
  аделаида: ["ADL"],
};

const TRANSLIT = {
  а: "a", б: "b", в: "v", г: "g", д: "d", е: "e", ё: "e", ж: "zh", з: "z", и: "i", й: "y", к: "k", л: "l",
  м: "m", н: "n", о: "o", п: "p", р: "r", с: "s", т: "t", у: "u", ф: "f", х: "kh", ц: "ts", ч: "ch", ш: "sh",
  щ: "shch", ъ: "", ы: "y", ь: "", э: "e", ю: "yu", я: "ya",
};

function transliterate(text) {
  let result = "";
  for (let i = 0; i < text.length; i += 1) {
    const char = text[i];
    const previous = text[i - 1];
    if (char === "е" && (!previous || /[\s\-аеёиоуыэюяьъ]/.test(previous))) result += "ye";
    else result += TRANSLIT[char] ?? char;
  }
  return result;
}

function searchAirports(query, limit = 8) {
  const q = query.trim().toLowerCase();
  if (!q) return [];
  const latin = /[а-яё]/.test(q) ? transliterate(q) : q;
  const scores = new Map();
  const score = (airport, value) => {
    if (!scores.has(airport.code) || value < scores.get(airport.code)) scores.set(airport.code, value);
  };

  for (const [city, codes] of Object.entries(CITY_ALIASES)) {
    if (!city.startsWith(q)) continue;
    codes.forEach((code, order) => {
      if (airportsByCode.has(code)) score(airportsByCode.get(code), (city === q ? 1 : 2) + order / 100);
    });
  }
  for (const airport of airports) {
    const code = airport.code.toLowerCase();
    if (code === latin) score(airport, 0);
    else if (latin.length < 3 && code.startsWith(latin)) score(airport, 3);

    if (airport.nameKey.startsWith(latin)) score(airport, 4);
    else if (airport.nameKey.includes(` ${latin}`) || airport.nameKey.includes(`-${latin}`)) score(airport, 5);
    else if (latin.length >= 3 && airport.nameKey.includes(latin)) score(airport, 6);
    else if (q.length >= 3 && airport.countryKey.startsWith(q)) score(airport, 7);
  }

  return [...scores]
    .sort(([a, sa], [b, sb]) => sa - sb || airportsByCode.get(a).name.localeCompare(airportsByCode.get(b).name))
    .slice(0, limit)
    .map(([code]) => airportsByCode.get(code));
}

const airportLabel = (airport) => `${airport.code} · ${airport.name}`;

/* ---------- Комбобокс с автодополнением ---------- */

let comboboxCounter = 0;

class Combobox {
  constructor(root, { onSelect, onEdit }) {
    this.input = root.querySelector("input");
    this.list = root.querySelector("[role=listbox]");
    this.onSelect = onSelect;
    this.onEdit = onEdit;
    this.results = [];
    this.active = -1;
    this.id = `combobox-${(comboboxCounter += 1)}`;
    this.list.id = `${this.id}-list`;
    this.input.setAttribute("aria-controls", this.list.id);

    this.input.addEventListener("input", () => {
      this.onEdit(this.input.value);
      this.update();
    });
    this.input.addEventListener("focus", () => this.input.select());
    this.input.addEventListener("keydown", (event) => this.onKeydown(event));
    this.input.addEventListener("blur", () => this.onBlur());
    this.list.addEventListener("mousedown", (event) => {
      const option = event.target.closest("[data-code]");
      if (!option) return;
      event.preventDefault();
      this.choose(option.dataset.code);
    });
  }

  update() {
    this.results = searchAirports(this.input.value);
    this.active = this.results.length ? 0 : -1;
    if (!this.input.value.trim()) return this.close();

    this.list.innerHTML = this.results.length
      ? this.results
          .map(
            (airport, i) => `
            <li class="combobox-option" role="option" id="${this.id}-${i}" data-code="${airport.code}" aria-selected="${i === this.active}">
              <span class="iata-tag">${airport.code}</span>
              <span class="combobox-option-name">${escapeHtml(airport.name)}</span>
              <span class="combobox-option-country">${flag(airport.country)} ${escapeHtml(airport.countryName)}</span>
            </li>`,
          )
          .join("")
      : `<li class="combobox-empty">Ничего не нашлось. Попробуйте IATA-код, например SVO.</li>`;
    this.open();
    this.highlight();
  }

  open() {
    this.list.hidden = false;
    this.input.setAttribute("aria-expanded", "true");
  }

  close() {
    this.list.hidden = true;
    this.input.setAttribute("aria-expanded", "false");
    this.input.removeAttribute("aria-activedescendant");
  }

  highlight() {
    for (const [i, option] of [...this.list.querySelectorAll("[role=option]")].entries()) {
      option.setAttribute("aria-selected", String(i === this.active));
      if (i === this.active) option.scrollIntoView({ block: "nearest" });
    }
    if (this.active >= 0) this.input.setAttribute("aria-activedescendant", `${this.id}-${this.active}`);
  }

  onKeydown(event) {
    const opened = !this.list.hidden && this.results.length;
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      if (!opened) return this.update();
      event.preventDefault();
      const step = event.key === "ArrowDown" ? 1 : -1;
      this.active = (this.active + step + this.results.length) % this.results.length;
      this.highlight();
    } else if (event.key === "Enter" && opened) {
      event.preventDefault();
      this.choose(this.results[Math.max(this.active, 0)].code);
    } else if (event.key === "Escape") {
      this.close();
    }
  }

  onBlur() {
    this.close();
    const typed = this.input.value.trim().toUpperCase();
    if (/^[A-Z]{3}$/.test(typed) && airportsByCode.has(typed)) this.choose(typed);
  }

  choose(code) {
    this.input.value = airportLabel(airportsByCode.get(code));
    this.close();
    this.onSelect(code);
  }
}

/* ---------- Состояние ---------- */

const state = {
  rows: [],
  airplaneId: "",
  criterion: DEFAULT_CRITERION,
  payload: null,
};

const elements = {
  waypoints: document.querySelector("[data-waypoints]"),
  template: document.getElementById("waypoint-template"),
  addButton: document.querySelector("[data-action=add]"),
  reverseButton: document.querySelector("[data-action=reverse]"),
  airplane: document.querySelector("[data-airplane]"),
  airplaneHint: document.querySelector("[data-airplane-hint]"),
  criteria: document.querySelector("[data-criteria]"),
  criteriaSection: document.querySelector("[data-criteria-section]"),
  results: document.querySelector("[data-results]"),
  mapStatus: document.querySelector("[data-map-status]"),
};

const filledCodes = () => state.rows.map((row) => row.code).filter(Boolean);

/* ---------- Карта ---------- */

const map = createMap("map", { landUrl: data.urls.land, center: [35, 30], zoom: 2.5 });
const canvas = L.canvas({ padding: 0.5, tolerance: 5 });
const svg = L.svg({ padding: 0.5 });
const FIT = { paddingTopLeft: [48, 48], paddingBottomRight: [72, 56], maxZoom: 7 };
const routeLayer = L.layerGroup().addTo(map);
const markerLayer = L.layerGroup().addTo(map);
const hoverTooltip = L.tooltip({ direction: "top", offset: [0, -6] });
let legLines = [];

const dotRadius = () => (map.getZoom() >= 6 ? 4.5 : map.getZoom() >= 4 ? 3.5 : 2.5);
const airportDots = WORLD_OFFSETS.flatMap((offset) =>
  airports.map((airport) => {
    const dot = L.circleMarker([airport.lat, airport.lon + offset], {
      renderer: canvas,
      stroke: false,
      fillOpacity: 0.75,
      radius: 2.5,
    });
    return dot
      .on("mouseover", () => {
        hoverTooltip.setLatLng(dot.getLatLng()).setContent(`${airport.code} · ${escapeHtml(airport.name)}`);
        map.openTooltip(hoverTooltip);
      })
      .on("mouseout", () => map.closeTooltip(hoverTooltip))
      .on("click", () => openAirportPopup(airport, dot.getLatLng()));
  }),
);
L.layerGroup(airportDots).addTo(map);

function styleDots() {
  const color = cssVar("--map-dot");
  const radius = dotRadius();
  for (const dot of airportDots) dot.setStyle({ fillColor: color, radius });
}

map.on("zoomend", styleDots);

function openAirportPopup(airport, latlng) {
  const detailUrl = data.urls.airport.replace("XXX", airport.code);
  L.popup({ offset: [0, -2], maxWidth: 280 })
    .setLatLng(latlng)
    .setContent(
      `<div class="popup-airport">
        <div>
          <strong>${airport.code} · ${escapeHtml(airport.name)}</strong>
          <span class="muted">${flag(airport.country)} ${escapeHtml(airport.countryName)}</span>
        </div>
        <div class="popup-actions">
          <button class="btn btn-sm btn-primary" type="button" data-popup-action="from" data-code="${airport.code}">${icon("plane-takeoff")} Отсюда</button>
          <button class="btn btn-sm" type="button" data-popup-action="to" data-code="${airport.code}">${icon("plane-landing")} Сюда</button>
          <a class="btn btn-sm btn-ghost" href="${detailUrl}">Подробнее</a>
        </div>
      </div>`,
    )
    .openOn(map);
}

map.getContainer().addEventListener("click", (event) => {
  const button = event.target.closest("[data-popup-action]");
  if (!button) return;
  const { code } = button.dataset;
  if (button.dataset.popupAction === "from") {
    state.rows[0] = { code, text: "" };
  } else {
    const last = state.rows.at(-1);
    if (!last.code) last.code = code;
    else if (state.rows.length < MAX_WAYPOINTS) state.rows.push({ code, text: "" });
    else state.rows[state.rows.length - 1] = { code, text: "" };
  }
  map.closePopup();
  renderWaypoints();
  routeChanged();
});

function waypointPin(number) {
  return L.divIcon({ className: "map-pin", html: String(number), iconSize: [30, 30], iconAnchor: [15, 15] });
}

/** Точки дуги большого круга (slerp) — для предпросмотра, пока сервер считает маршрут. */
function greatCircle(from, to, stepKm = 150) {
  const rad = Math.PI / 180;
  const vector = ({ lat, lon }) => [
    Math.cos(lat * rad) * Math.cos(lon * rad),
    Math.cos(lat * rad) * Math.sin(lon * rad),
    Math.sin(lat * rad),
  ];
  const p = vector(from);
  const q = vector(to);
  const omega = Math.acos(Math.min(1, Math.max(-1, p[0] * q[0] + p[1] * q[1] + p[2] * q[2])));
  if (omega < 1e-9 || Math.PI - omega < 1e-6) return [[from.lat, from.lon], [to.lat, to.lon]];

  const steps = Math.max(1, Math.ceil((omega * 6371) / stepKm));
  return Array.from({ length: steps + 1 }, (_, i) => {
    const t = i / steps;
    const a = Math.sin((1 - t) * omega) / Math.sin(omega);
    const b = Math.sin(t * omega) / Math.sin(omega);
    const [x, y, z] = [0, 1, 2].map((k) => a * p[k] + b * q[k]);
    return [Math.atan2(z, Math.hypot(x, y)) / rad, Math.atan2(y, x) / rad];
  });
}

function drawPreview(gaps = []) {
  routeLayer.clearLayers();
  markerLayer.clearLayers();
  legLines = [];

  const points = state.rows
    .map((row, i) => ({ airport: airportsByCode.get(row.code), number: i + 1 }))
    .filter(({ airport }) => airport);
  if (!points.length) return;

  const gapKeys = new Set(gaps.map((gap) => `${gap.origin}-${gap.destination}`));
  let reference = points[0].airport.lon;
  const positions = [[points[0].airport.lat, reference]];
  const bounds = [positions[0]];
  for (let i = 1; i < points.length; i += 1) {
    const from = points[i - 1].airport;
    const to = points[i].airport;
    const line = greatCircle(from, to).map(([lat, lon]) => {
      reference = unwrapLongitude(lon, reference);
      return [lat, reference];
    });
    positions.push(line.at(-1));
    bounds.push(...line);
    const isGap = gapKeys.has(`${from.code}-${to.code}`);
    L.polyline(line, {
      renderer: svg,
      color: isGap ? cssVar("--danger") : cssVar("--muted"),
      weight: isGap ? 3 : 2,
      opacity: isGap ? 0.9 : 0.7,
      dashArray: isGap ? "8 8" : "3 7",
      interactive: false,
    }).addTo(routeLayer);
  }

  points.forEach(({ airport, number }, i) => {
    L.marker(positions[i], { icon: waypointPin(number), keyboard: false, zIndexOffset: 1000 })
      .bindTooltip(airport.code, { permanent: true, direction: "right", offset: [16, 0], className: "map-label" })
      .addTo(markerLayer);
  });

  if (points.length === 1) map.setView(positions[0], Math.max(map.getZoom(), 4));
  else map.fitBounds(L.latLngBounds(bounds), FIT);
}

function drawRoute(payload) {
  routeLayer.clearLayers();
  markerLayer.clearLayers();

  let reference = payload.stops[0].longitude;
  const lines = payload.legs.map((leg) =>
    leg.path.map(([lat, lon]) => {
      reference = unwrapLongitude(lon, reference);
      return [lat, reference];
    }),
  );
  const stopPoints = [lines[0][0], ...lines.map((line) => line.at(-1))];

  const routeColor = cssVar("--route");
  const haloColor = cssVar("--route-halo");
  legLines = lines.map((line, i) => {
    L.polyline(line, { renderer: svg, color: haloColor, weight: 8, opacity: 0.9, interactive: false }).addTo(routeLayer);
    const polyline = L.polyline(line, { renderer: svg, color: routeColor, weight: 3.5, opacity: 1 }).addTo(routeLayer);
    L.polyline(line, {
      renderer: svg,
      color: haloColor,
      weight: 2,
      opacity: 0.8,
      className: "route-flow",
      interactive: false,
    }).addTo(routeLayer);
    polyline.on("mouseover", () => highlightLeg(i, true)).on("mouseout", () => highlightLeg(i, false));
    return polyline;
  });

  let waypointNumber = 0;
  payload.stops.forEach((stop, i) => {
    const latlng = stopPoints[i];
    if (stop.is_waypoint) {
      waypointNumber += 1;
      L.marker(latlng, { icon: waypointPin(waypointNumber), keyboard: false, zIndexOffset: 1000 })
        .bindTooltip(stop.iata_code, { permanent: true, direction: "right", offset: [16, 0], className: "map-label" })
        .addTo(markerLayer);
    } else {
      L.circleMarker(latlng, {
        renderer: svg,
        radius: 6,
        weight: 3,
        color: cssVar("--stop"),
        fillColor: cssVar("--surface"),
        fillOpacity: 1,
      })
        .bindTooltip(`${stop.iata_code} · ${escapeHtml(stop.name)} — дозаправка`, { direction: "top", offset: [0, -6] })
        .addTo(markerLayer);
    }
  });

  map.fitBounds(L.latLngBounds(lines.flat()), FIT);
}

function highlightLeg(index, on) {
  legLines[index]?.setStyle({ weight: on ? 6 : 3.5 });
  elements.results.querySelector(`[data-leg="${index}"]`)?.classList.toggle("is-highlighted", on);
}

/* ---------- Панель ---------- */

function renderWaypoints() {
  const nodes = state.rows.map((row, i) => {
    const node = elements.template.content.firstElementChild.cloneNode(true);
    const input = node.querySelector("input");
    const remove = node.querySelector(".waypoint-remove");
    const last = i === state.rows.length - 1;

    node.classList.toggle("is-filled", Boolean(row.code));
    node.querySelector(".waypoint-marker").textContent = i + 1;
    input.value = row.code ? airportLabel(airportsByCode.get(row.code)) : row.text;
    input.placeholder = i === 0 ? "Откуда: город, аэропорт или IATA" : last ? "Куда: город, аэропорт или IATA" : "Промежуточная точка";
    input.setAttribute("aria-label", `Точка маршрута ${i + 1}`);
    remove.classList.toggle("is-invisible", state.rows.length <= 2 && !row.code && !row.text);
    remove.addEventListener("click", () => {
      if (state.rows.length > 2) state.rows.splice(i, 1);
      else state.rows[i] = { code: null, text: "" };
      renderWaypoints();
      routeChanged();
    });

    new Combobox(node.querySelector(".combobox"), {
      onSelect: (code) => {
        row.code = code;
        row.text = "";
        node.classList.add("is-filled");
        remove.classList.remove("is-invisible");
        routeChanged();
      },
      onEdit: (text) => {
        row.text = text;
        remove.classList.remove("is-invisible");
        if (row.code) {
          row.code = null;
          node.classList.remove("is-filled");
          routeChanged();
        }
      },
    });
    return node;
  });
  elements.waypoints.replaceChildren(...nodes);
  elements.addButton.disabled = state.rows.length >= MAX_WAYPOINTS;
  elements.reverseButton.disabled = filledCodes().length < 2;
}

function renderAirplanes() {
  for (const plane of airplanes.values()) {
    const option = new Option(`${plane.name} · ${formatNumber(plane.range)} км`, plane.id);
    elements.airplane.querySelector(`[data-group=${plane.inService ? "active" : "retired"}]`).append(option);
  }
  elements.airplane.value = state.airplaneId;
  elements.airplane.addEventListener("change", () => {
    state.airplaneId = elements.airplane.value;
    renderAirplaneHint();
    routeChanged({ waypoints: false });
  });
}

function renderAirplaneHint() {
  const plane = airplanes.get(state.airplaneId);
  elements.criteriaSection.hidden = !plane;
  if (!plane) {
    elements.airplaneHint.innerHTML = "Выберите самолёт, чтобы учесть дальность, время и расход топлива.";
    return;
  }
  const url = data.urls.airplane.replace("/0/", `/${plane.id}/`);
  const retired = plane.inService ? "" : ` · <span class="badge badge-warning">выведен из эксплуатации</span>`;
  elements.airplaneHint.innerHTML =
    `Дальность ${formatNumber(plane.range)} км · ${formatNumber(plane.speed)} км/ч${retired} · ` +
    `<a href="${url}">о самолёте</a>`;
}

function renderCriteria() {
  elements.criteria.innerHTML = data.criteria
    .map(
      ({ value, label }) => `
      <label>
        <input type="radio" name="criterion" value="${value}" ${value === state.criterion ? "checked" : ""}>
        <span>${escapeHtml(label)}</span>
      </label>`,
    )
    .join("");
  elements.criteria.addEventListener("change", (event) => {
    state.criterion = event.target.value;
    routeChanged({ waypoints: false });
  });
}

function setLoading(loading) {
  elements.results.setAttribute("aria-busy", String(loading));
  elements.mapStatus.hidden = !loading;
}

function renderEmpty() {
  elements.results.innerHTML = `
    <div class="planner-empty">
      <div>${icon("route")} <strong>Укажите минимум две точки.</strong></div>
      <div>Введите город («Москва»), название аэропорта или IATA-код, либо нажмите на точку на карте и выберите «Отсюда» / «Сюда».</div>
    </div>`;
}

function renderMessage(message, kind = "danger") {
  elements.results.innerHTML = `
    <div class="alert alert-${kind}" role="alert">${icon(kind === "danger" ? "triangle-alert" : "info")}<p>${escapeHtml(message)}</p></div>`;
}

function renderUnreachable(payload) {
  const suggestions = (payload.suitable_airplanes ?? [])
    .map(
      (plane) =>
        `<button class="btn btn-sm" type="button" data-suggest="${plane.id}">${escapeHtml(plane.name)} · ${formatNumber(plane.range_km)} км</button>`,
    )
    .join("");
  elements.results.innerHTML = `
    <div class="alert alert-danger" role="alert">
      ${icon("triangle-alert")}
      <div>
        <p>${escapeHtml(payload.detail)}</p>
        ${suggestions ? `<p class="alert-note">Справятся:</p><div class="suggestions">${suggestions}</div>` : ""}
      </div>
    </div>`;
}

function stopRow(stop, waypointNumber) {
  const url = data.urls.airport.replace("XXX", stop.iata_code);
  const technical = !stop.is_waypoint;
  return `
    <li class="timeline-stop ${technical ? "is-technical" : ""}">
      <span class="timeline-dot">${technical ? "" : waypointNumber}</span>
      <div class="timeline-place">
        <a href="${url}">${escapeHtml(stop.name)}</a>
        <span class="timeline-meta">${stop.iata_code} · ${flag(stop.country)} ${escapeHtml(stop.country_name)}${technical ? " · дозаправка" : ""}</span>
      </div>
    </li>`;
}

function legRow(leg, index) {
  const parts = [`${formatNumber(leg.distance_km)} км`];
  if (leg.flight_time_h !== null) parts.push(formatDuration(leg.flight_time_h), formatMass(leg.fuel_kg));
  return `
    <li class="timeline-leg" data-leg="${index}">
      <div class="timeline-leg-body">${icon("plane")} ${parts.join(" · ")}</div>
    </li>`;
}

function renderRoute(payload) {
  const { summary } = payload;
  const withPlane = payload.airplane !== null;
  const stopsText =
    summary.technical_stops === 0
      ? "без дозаправок"
      : `${summary.technical_stops} ${pluralize(summary.technical_stops, "дозаправка", "дозаправки", "дозаправок")}`;

  const tiles = withPlane
    ? `
      <div class="summary-tile is-primary">
        <div class="summary-label">${icon("clock")} В пути</div>
        <div class="summary-value">${formatDuration(summary.total_time_h)}</div>
        <div class="summary-label">в воздухе ${formatDuration(summary.flight_time_h)}, на земле ${formatDuration(summary.ground_time_h)}</div>
      </div>
      <div class="summary-tile"><div class="summary-label">${icon("ruler")} Расстояние</div><div class="summary-value">${formatNumber(summary.distance_km)} км</div></div>
      <div class="summary-tile"><div class="summary-label">${icon("plane")} Перелёты</div><div class="summary-value">${summary.flights}</div><div class="summary-label">${stopsText}</div></div>
      <div class="summary-tile"><div class="summary-label">${icon("fuel")} Топливо</div><div class="summary-value">${formatMass(summary.fuel_kg)}</div></div>
      <div class="summary-tile"><div class="summary-label">${icon("coins")} Стоимость топлива</div><div class="summary-value">$${formatNumber(summary.fuel_cost_usd)}</div></div>`
    : `
      <div class="summary-tile is-primary">
        <div class="summary-label">${icon("ruler")} Расстояние по дуге большого круга</div>
        <div class="summary-value">${formatNumber(summary.distance_km)} км</div>
      </div>
      <div class="summary-tile"><div class="summary-label">${icon("plane")} Перелёты</div><div class="summary-value">${summary.flights}</div></div>
      <div class="summary-tile"><div class="summary-label">${icon("waypoints")} Самый длинный</div><div class="summary-value">${formatNumber(summary.max_leg_km)} км</div></div>`;

  let waypointNumber = 0;
  const timeline = payload.stops
    .map((stop, i) => {
      if (stop.is_waypoint) waypointNumber += 1;
      const row = stopRow(stop, waypointNumber);
      return i < payload.legs.length ? row + legRow(payload.legs[i], i) : row;
    })
    .join("");

  elements.results.innerHTML = `
    <div class="panel-label"><span>Результат</span></div>
    <div class="summary-grid">${tiles}</div>
    ${withPlane ? "" : `<div class="alert alert-info">${icon("info")}<p>Без самолёта маршрут строится напрямую. Выберите модель — и мы подберём дозаправки под её дальность.</p></div>`}
    <ol class="timeline">${timeline}</ol>
    <div class="results-actions">
      <button class="btn btn-sm" type="button" data-copy-link>${icon("link")} Скопировать ссылку</button>
      <button class="btn btn-sm btn-ghost" type="button" data-reset>${icon("rotate-ccw")} Сбросить</button>
    </div>`;

  for (const item of elements.results.querySelectorAll("[data-leg]")) {
    const index = Number(item.dataset.leg);
    item.addEventListener("mouseenter", () => highlightLeg(index, true));
    item.addEventListener("mouseleave", () => highlightLeg(index, false));
  }
}

elements.results.addEventListener("click", async (event) => {
  const suggestion = event.target.closest("[data-suggest]");
  if (suggestion) {
    state.airplaneId = suggestion.dataset.suggest;
    elements.airplane.value = state.airplaneId;
    renderAirplaneHint();
    routeChanged({ waypoints: false });
  }
  const copy = event.target.closest("[data-copy-link]");
  if (copy) {
    try {
      await navigator.clipboard.writeText(window.location.href);
      copy.innerHTML = `${icon("check")} Ссылка скопирована`;
    } catch {
      copy.innerHTML = `${icon("triangle-alert")} Не удалось скопировать`;
    }
    setTimeout(() => {
      copy.innerHTML = `${icon("link")} Скопировать ссылку`;
    }, 2000);
  }
  if (event.target.closest("[data-reset]")) {
    state.rows = [
      { code: null, text: "" },
      { code: null, text: "" },
    ];
    renderWaypoints();
    routeChanged();
  }
});

/* ---------- Запрос маршрута и URL ---------- */

let controller = null;

function syncUrl() {
  const params = new URLSearchParams();
  const codes = filledCodes();
  if (codes.length) params.set("route", codes.join(","));
  if (state.airplaneId) params.set("plane", state.airplaneId);
  if (state.airplaneId && state.criterion !== DEFAULT_CRITERION) params.set("criterion", state.criterion);
  const query = params.toString().replaceAll("%2C", ",");
  history.replaceState(null, "", query ? `?${query}` : window.location.pathname);
}

async function buildRoute() {
  controller?.abort();
  const codes = filledCodes();
  if (codes.length < 2) {
    setLoading(false);
    renderEmpty();
    drawPreview();
    return;
  }
  if (codes.some((code, i) => code === codes[i + 1])) {
    drawPreview();
    renderMessage("Соседние точки маршрута совпадают — уберите повтор.");
    return;
  }

  controller = new AbortController();
  const { signal } = controller;
  const params = new URLSearchParams({ airports: codes.join(",") });
  if (state.airplaneId) {
    params.set("airplane", state.airplaneId);
    params.set("criterion", state.criterion);
  }

  setLoading(true);
  try {
    const response = await fetch(`${data.urls.route}?${params}`, { signal, headers: { Accept: "application/json" } });
    const payload = await response.json().catch(() => ({}));
    if (response.ok) {
      state.payload = payload;
      drawRoute(payload);
      renderRoute(payload);
    } else {
      state.payload = null;
      drawPreview(response.status === 422 ? payload.gaps : []);
      if (response.status === 422) renderUnreachable(payload);
      else if (response.status === 429) renderMessage("Слишком много запросов. Подождите минуту и попробуйте снова.");
      else renderMessage(Object.values(payload).flat().join(" ") || "Не удалось построить маршрут.");
    }
  } catch (error) {
    if (error.name === "AbortError") return;
    drawPreview();
    renderMessage("Сервер недоступен. Проверьте подключение и попробуйте ещё раз.");
  }
  if (!signal.aborted) setLoading(false);
}

const scheduleBuild = debounce(buildRoute, 250);

/** Точки меняются — сразу показываем их маркерами; самолёт или критерий — держим старый маршрут до ответа. */
function routeChanged({ waypoints = true } = {}) {
  elements.reverseButton.disabled = filledCodes().length < 2;
  syncUrl();
  if (waypoints || !state.payload) drawPreview();
  scheduleBuild();
}

elements.addButton.addEventListener("click", () => {
  if (state.rows.length >= MAX_WAYPOINTS) return;
  state.rows.push({ code: null, text: "" });
  renderWaypoints();
  elements.waypoints.lastElementChild.querySelector("input").focus();
});

elements.reverseButton.addEventListener("click", () => {
  state.rows.reverse();
  renderWaypoints();
  routeChanged();
});

onThemeChange(() => {
  styleDots();
  if (state.payload) drawRoute(state.payload);
});

/* ---------- Старт ---------- */

function restoreFromUrl() {
  const params = new URLSearchParams(window.location.search);
  const codes = (params.get("route") ?? "")
    .split(",")
    .map((code) => code.trim().toUpperCase())
    .filter((code) => airportsByCode.has(code))
    .slice(0, MAX_WAYPOINTS);
  state.rows = codes.map((code) => ({ code, text: "" }));
  while (state.rows.length < 2) state.rows.push({ code: null, text: "" });

  const plane = params.get("plane") ?? "";
  state.airplaneId = airplanes.has(plane) ? plane : "";
  const criterion = params.get("criterion");
  state.criterion = data.criteria.some(({ value }) => value === criterion) ? criterion : DEFAULT_CRITERION;
}

restoreFromUrl();
renderWaypoints();
renderAirplanes();
renderCriteria();
renderAirplaneHint();
styleDots();
routeChanged();
