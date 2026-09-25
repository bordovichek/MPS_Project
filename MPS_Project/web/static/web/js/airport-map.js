import { createMap, unwrapLongitude } from "./map-base.js";
import { cssVar, escapeHtml, icon, onThemeChange } from "./utils.js";

const L = window.L;
const data = JSON.parse(document.getElementById("airport-map-data").textContent);
const [lat, lon, code] = data.airport;

const map = createMap("airport-map", { landUrl: data.landUrl, scrollWheelZoom: false });

const neighbours = data.nearest.map(([nLat, nLon, nCode]) => {
  const marker = L.circleMarker([nLat, unwrapLongitude(nLon, lon)], { radius: 6, weight: 2 })
    .bindTooltip(escapeHtml(nCode), { permanent: true, direction: "right", offset: [6, 0], className: "map-label" })
    .on("click", () => {
      window.location.href = data.airportUrl.replace("XXX", nCode);
    });
  return marker.addTo(map);
});

const style = () => {
  for (const marker of neighbours) {
    marker.setStyle({ color: cssVar("--route-halo"), fillColor: cssVar("--map-dot"), fillOpacity: 1 });
  }
};
style();
onThemeChange(style);

L.marker([lat, lon], {
  icon: L.divIcon({ className: "map-pin", html: icon("plane"), iconSize: [34, 34], iconAnchor: [17, 17] }),
  keyboard: false,
  zIndexOffset: 1000,
})
  .bindTooltip(escapeHtml(code), { permanent: true, direction: "right", offset: [18, 0], className: "map-label" })
  .addTo(map);

const points = [[lat, lon], ...neighbours.map((marker) => marker.getLatLng())];
map.fitBounds(L.latLngBounds(points).pad(0.3), { maxZoom: 9 });
