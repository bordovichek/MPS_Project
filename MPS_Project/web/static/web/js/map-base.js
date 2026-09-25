import { cssVar, onThemeChange } from "./utils.js";

const L = window.L;

// Стандартные тайлы OSM: единственный публичный источник без API-ключа и регистрации
// (у CARTO и большинства альтернатив с 2024–2025 бесплатный доступ закрыт ключом).
// Тёмную тему делаем CSS-инверсией слоя тайлов, а не отдельным источником.
const TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
const ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';

const currentTheme = () => (document.documentElement.dataset.theme === "dark" ? "dark" : "light");

/** Маршрут через 180-й меридиан рисуется непрерывно и уходит в соседнюю «копию» мира — слои дублируем туда. */
export const WORLD_OFFSETS = [-360, 0, 360];

/** Карта с тайлами под текущую тему. Если тайлы недоступны (офлайн, блокировка) — подкладываем контуры суши. */
export function createMap(element, { landUrl, ...options } = {}) {
  const map = L.map(element, {
    minZoom: 2,
    zoomSnap: 0.5,
    maxBounds: [
      [-88, -540],
      [88, 540],
    ],
    maxBoundsViscosity: 1,
    ...options,
  });
  map.attributionControl.setPrefix(false);

  const tiles = L.tileLayer(TILE_URL, { maxZoom: 19, attribution: ATTRIBUTION }).addTo(map);
  const applyTileTheme = () => map.getPane("tilePane").classList.toggle("is-dark-tiles", currentTheme() === "dark");
  applyTileTheme();

  let land = null;
  let failures = 0;
  const landStyle = () => ({
    color: cssVar("--map-land-stroke"),
    weight: 1,
    fillColor: cssVar("--map-land"),
    fillOpacity: 1,
  });

  tiles.on("tileerror", async () => {
    failures += 1;
    if (land || failures < 2 || !landUrl) return;
    land = "loading";
    try {
      const geojson = await (await fetch(landUrl)).json();
      map.createPane("land").style.zIndex = 150;
      const copies = WORLD_OFFSETS.map((offset) =>
        L.geoJSON(geojson, {
          pane: "land",
          interactive: false,
          style: landStyle,
          coordsToLatLng: ([lon, lat]) => L.latLng(lat, lon + offset),
        }),
      );
      land = L.featureGroup(copies).addTo(map);
    } catch {
      land = null;
    }
  });

  onThemeChange(() => {
    applyTileTheme();
    if (land && land !== "loading") land.setStyle(landStyle());
  });

  return map;
}

/** Сдвигает долготу на ±360°, чтобы линия не «перепрыгивала» через всю карту на 180-м меридиане. */
export function unwrapLongitude(lon, reference) {
  let value = lon;
  while (value - reference > 180) value -= 360;
  while (value - reference < -180) value += 360;
  return value;
}
