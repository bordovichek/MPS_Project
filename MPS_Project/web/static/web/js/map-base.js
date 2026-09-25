import { cssVar, onThemeChange } from "./utils.js";

const L = window.L;

const TILES = {
  light: "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png",
  dark: "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
};
const ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>';

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

  const tiles = L.tileLayer(TILES[currentTheme()], {
    subdomains: "abcd",
    maxZoom: 19,
    attribution: ATTRIBUTION,
  }).addTo(map);

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
    tiles.setUrl(TILES[currentTheme()]);
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
