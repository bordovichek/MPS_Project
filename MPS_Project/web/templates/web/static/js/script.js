function getCookie(name) {
            let cookieValue = null;
            if (document.cookie && document.cookie !== '') {
                const cookies = document.cookie.split(';');
                for (let i = 0; i < cookies.length; i++) {
                    const cookie = cookies[i].trim();
                    if (cookie.substring(0, name.length + 1) === (name + '=')) {
                        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                        break;
                    }
                }
            }
            return cookieValue;
        }

        const aircraftSelectNotice = document.getElementById("aircraft");
const retiredNotice = document.getElementById("retiredAircraftNotice");
const retiredNameSpan = document.getElementById("retiredAircraftName");

if (aircraftSelectNotice) {
    aircraftSelectNotice.addEventListener("change", function() {
        const selectedOption = aircraftSelectNotice.options[aircraftSelectNotice.selectedIndex];
        // Получаем значение атрибута data-in-service
        const inService = selectedOption.getAttribute("data-in-service");
        const aircraftName = selectedOption.textContent.trim();

        if (inService === "false") { // Если самолет выведен из эксплуатации
            retiredNameSpan.textContent = aircraftName;
            retiredNotice.classList.add("show"); // Показываем плашку, используя класс 'show'
        } else {
            retiredNotice.classList.remove("show"); // Скрываем, если самолет действующий
        }
    });
}

        const map = L.map('map').setView([20, 0], 2);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }).addTo(map);

        const airportSelectionArea = document.getElementById('airportSelectionArea');
        const addAirportBtn = document.getElementById('addAirportBtn');
        const buildRouteBtn = document.getElementById('buildRouteBtn');
        const aircraftSelect = document.getElementById('aircraft');
        const routeDetailsDiv = document.getElementById('routeDetails');
        const errorMessageDiv = document.getElementById('errorMessage');

        let routePolylineLayerGroup = L.layerGroup().addTo(map);
        let routeMarkerLayerGroup = L.layerGroup().addTo(map);

        let airportSelectors = [];
        let airportSearchInputs = [];
        let originalAirportOptions = [];

        const airport1Select = document.getElementById('airport1');
        const airport2Select = document.getElementById('airport2');
        const searchAirport1Input = document.getElementById('searchAirport1');
        const searchAirport2Input = document.getElementById('searchAirport2');

        airportSelectors.push(airport1Select);
        airportSelectors.push(airport2Select);
        airportSearchInputs.push(searchAirport1Input);
        airportSearchInputs.push(searchAirport2Input);

        let allAirportsData = [];
        let airportsByCode = {};
        let allAirplanesData = [];

        async function loadInitialData() {
            try {
                const response = await fetch('/api/initial_data/');
                if (!response.ok) {
                    throw new Error(`HTTP error! Status: ${response.status}`);
                }
                const data = await response.json();

                allAirportsData = data.airports;
                allAirplanesData = data.airplanes;

                allAirportsData.forEach(airport => {
                    airportsByCode[airport.iata_code] = airport;
                });

                originalAirportOptions = allAirportsData.map(airport => {
                    const option = document.createElement('option');
                    option.value = airport.iata_code;
                    option.textContent = `${airport.name} (${airport.iata_code}) - ${airport.country}`;
                    option.dataset.lat = airport.latitude;
                    option.dataset.lon = airport.longitude;
                    option.dataset.name = airport.name;
                    option.dataset.country = airport.country;
                    return option;
                });

                airportSelectors.forEach(select => {
                    select.innerHTML = '';
                    const defaultOption = document.createElement('option');
                    defaultOption.value = "";
                    defaultOption.textContent = "--";
                    select.appendChild(defaultOption);
                    originalAirportOptions.forEach(opt => select.appendChild(opt.cloneNode(true)));
                });

                aircraftSelect.innerHTML = '';
                const noPlaneOption = document.createElement('option');
                noPlaneOption.value = "";
                noPlaneOption.textContent = "Без выбора самолета";
                aircraftSelect.appendChild(noPlaneOption);

                allAirplanesData.forEach(plane => {
                    const option = document.createElement('option');
                    option.value = plane.id;
                    option.textContent = plane.name;
                    option.setAttribute('data-in-service', plane.in_service ? 'true' : 'false');
                    aircraftSelect.appendChild(option);
                });

                airport1Select.disabled = false;
                searchAirport1Input.disabled = false;
                updateMapAndSelections();

            } catch (error) {
                console.error("Ошибка загрузки initial data:", error);
                showErrorMessage(`Ошибка загрузки данных аэропортов/самолетов: ${error.message}`);
            }
        }

        function hideRouteDetailsAndErrors() {
    routeDetailsDiv.classList.remove('show'); // Используем 'show' для показа/скрытия
    errorMessageDiv.classList.remove('show');
    errorMessageDiv.textContent = '';
    retiredNotice.classList.remove('show'); // Скрываем уведомление о списанном самолете
}

        function showErrorMessage(message) {
    errorMessageDiv.textContent = message;
    errorMessageDiv.classList.add('show'); // Показываем ошибку
    routeDetailsDiv.classList.remove('show'); // Скрываем детали маршрута
    retiredNotice.classList.remove('show'); // Скрываем уведомление о списанном самолете
}

        function filterAirportOptions(selectElement, searchInput) {
            const searchText = searchInput.value.toLowerCase();
            const currentValue = selectElement.value;
            selectElement.innerHTML = '';

            const defaultOption = document.createElement('option');
            defaultOption.value = "";
            defaultOption.textContent = "--";
            selectElement.appendChild(defaultOption);

            let foundCurrentValue = false;

            originalAirportOptions.forEach(option => {
                const airportName = option.dataset.name ? option.dataset.name.toLowerCase() : '';
                const iataCode = option.value.toLowerCase();
                const country = option.dataset.country ? option.dataset.country.toLowerCase() : '';

                if (airportName.includes(searchText) || iataCode.includes(searchText) || country.includes(searchText)) {
                    const clonedOption = option.cloneNode(true);
                    if (clonedOption.value === currentValue) {
                        clonedOption.selected = true;
                        foundCurrentValue = true;
                    }
                    selectElement.appendChild(clonedOption);
                }
            });

            if (!foundCurrentValue && currentValue !== "") {
                selectElement.value = "";
            }
        }

        function updateMapAndSelections() {
            routePolylineLayerGroup.clearLayers();
            routeMarkerLayerGroup.clearLayers();
            hideRouteDetailsAndErrors();

            let selectedAirports = [];
            let validSelectionsCount = 0;

            airportSelectors.forEach((select, index) => {
                const option = select.selectedOptions[0];
                if (option && option.value) {
                    const airportData = airportsByCode[option.value];
                    if (airportData) {
                        selectedAirports.push({
                            lat: airportData.latitude,
                            lon: airportData.longitude,
                            name: airportData.name,
                            iata: airportData.iata_code,
                            number: index + 1
                        });
                        validSelectionsCount++;
                    }
                }
            });

            for (let i = 0; i < airportSelectors.length; i++) {
                const currentSelect = airportSelectors[i];
                const currentSearch = airportSearchInputs[i];
                const currentGroup = currentSelect.closest('.select-group');
                const removeBtn = currentGroup ? currentGroup.querySelector('.remove-airport-btn') : null;

                if (i === 0) {
                    currentSelect.disabled = false;
                    currentSearch.disabled = false;
                    if (removeBtn) removeBtn.classList.add('hidden');
                } else {
                    const prevSelect = airportSelectors[i - 1];
                    if (prevSelect && prevSelect.value) {
                        currentSelect.disabled = false;
                        currentSearch.disabled = false;
                        if (removeBtn) removeBtn.classList.remove('hidden');
                    } else {
                        currentSelect.disabled = true;
                        currentSelect.value = "";
                        currentSearch.disabled = true;
                        currentSearch.value = "";
                        filterAirportOptions(currentSelect, currentSearch);
                        if (removeBtn) removeBtn.classList.add('hidden');
                    }
                }
            }

            const lastActiveAirportSelect = airportSelectors.findLast(select => !select.disabled);
            const maxAirports = 6;
            if (lastActiveAirportSelect && lastActiveAirportSelect.value && airportSelectors.length < maxAirports) {
                addAirportBtn.disabled = false;
            } else {
                addAirportBtn.disabled = true;
            }

            if (validSelectionsCount >= 2) {
                buildRouteBtn.disabled = false;
            } else {
                buildRouteBtn.disabled = true;
            }

            if (selectedAirports.length > 0) {
                let allLatsLons = [];
                selectedAirports.forEach(airport => {
                    const iataHtml = `<div class="marker-iata-code">${airport.iata}</div>`;
                    const numberIcon = L.divIcon({
                        className: 'numbered-marker-icon',
                        html: `<div class="marker-number">${airport.number}</div>${iataHtml}`,
                        iconSize: [30, 30],
                        iconAnchor: [15, 30]
                    });

                    const m = L.marker([airport.lat, airport.lon], { icon: numberIcon }).addTo(routeMarkerLayerGroup)
                        .bindPopup(`<b>${airport.name}</b> (${airport.iata})`);
                    allLatsLons.push([airport.lat, airport.lon]);
                });

                if (allLatsLons.length > 0) {
                    const bounds = L.latLngBounds(allLatsLons);
                    map.fitBounds(bounds.pad(0.5));
                }
            }
        }

        function initializeNewAirportSelector(index) {
            const selectGroup = document.createElement('div');
            selectGroup.className = 'select-group';
            selectGroup.id = `airportGroup${index}`;

            const label = document.createElement('label');
            label.htmlFor = `airport${index}`;
            label.textContent = `Выберите аэропорт ${index}:`;
            label.className = 'font-medium text-gray-700';
            selectGroup.appendChild(label);

            const selectElement = document.createElement('select');
            selectElement.id = `airport${index}`;
            selectElement.name = `airport${index}`;
            selectElement.disabled = true;
            airportSelectors.push(selectElement);

            const defaultOption = document.createElement('option');
            defaultOption.value = "";
            defaultOption.textContent = "--";
            selectElement.appendChild(defaultOption);

            originalAirportOptions.forEach(opt => {
                selectElement.appendChild(opt.cloneNode(true));
            });

            const searchInput = document.createElement('input');
            searchInput.type = 'text';
            searchInput.id = `searchAirport${index}`;
            searchInput.placeholder = `Поиск Аэропорта ${index} (имя/IATA/страна)`;
            searchInput.disabled = true;
            airportSearchInputs.push(searchInput);

            selectGroup.appendChild(selectElement);
            selectGroup.appendChild(searchInput);

            if (index > 2) {
                const removeBtn = document.createElement('button');
                removeBtn.type = 'button';
                removeBtn.className = 'remove-airport-btn';
                removeBtn.textContent = 'x';
                removeBtn.addEventListener('click', () => {
                    removeAirportSelector(index);
                });
                selectGroup.appendChild(removeBtn);
            }

            const addAirportBtnElement = document.getElementById('addAirportBtn');
            airportSelectionArea.insertBefore(selectGroup, addAirportBtnElement);

            selectElement.addEventListener('change', updateMapAndSelections);
            searchInput.addEventListener('input', () => {
                filterAirportOptions(selectElement, searchInput);
            });

            setTimeout(() => {
                airportSelectionArea.scrollTop = airportSelectionArea.scrollHeight;
            }, 0);
        }

        function removeAirportSelector(indexToRemove) {
            if (indexToRemove <= 2) {
                console.warn("Невозможно удалить первые два аэропорта.");
                return;
            }

            const groupToRemove = document.getElementById(`airportGroup${indexToRemove}`);
            if (groupToRemove) {
                groupToRemove.remove();

                airportSelectors.splice(indexToRemove - 1, 1);
                airportSearchInputs.splice(indexToRemove - 1, 1);

                for (let i = indexToRemove - 1; i < airportSelectors.length; i++) {
                    const currentGroup = airportSelectors[i].closest('.select-group');
                    const newIndex = i + 1;

                    currentGroup.id = `airportGroup${newIndex}`;
                    currentGroup.querySelector('label').htmlFor = `airport${newIndex}`;
                    currentGroup.querySelector('label').textContent = `Выберите аэропорт ${newIndex}:`;
                    airportSelectors[i].id = `airport${newIndex}`;
                    airportSelectors[i].name = `airport${newIndex}`;
                    airportSearchInputs[i].id = `searchAirport${newIndex}`;
                    airportSearchInputs[i].placeholder = `Поиск Аэропорта ${newIndex} (имя/IATA/страна)`;

                    const removeBtn = currentGroup.querySelector('.remove-airport-btn');
                    if (removeBtn) {
                        const oldRemoveHandler = removeBtn._currentClickHandler;
                        if (oldRemoveHandler) {
                            removeBtn.removeEventListener('click', oldRemoveHandler);
                        }
                        const newRemoveHandler = () => removeAirportSelector(newIndex);
                        removeBtn.addEventListener('click', newRemoveHandler);
                        removeBtn._currentClickHandler = newRemoveHandler;
                    }
                }
            }
            updateMapAndSelections();
        }

        async function buildRoute() {
            routePolylineLayerGroup.clearLayers();
            routeMarkerLayerGroup.clearLayers();
            hideRouteDetailsAndErrors();

            let selectedAirportIATAs = [];
            airportSelectors.forEach(select => {
                const option = select.selectedOptions[0];
                if (option && option.value) {
                    selectedAirportIATAs.push(option.value);
                }
            });

            selectedAirportIATAs = [...new Set(selectedAirportIATAs.filter(iata => iata !== ''))];

            if (selectedAirportIATAs.length < 2) {
                showErrorMessage("Пожалуйста, выберите как минимум два уникальных аэропорта для построения маршрута.");
                return;
            }

            const selectedAircraftId = aircraftSelect.selectedOptions[0] && aircraftSelect.selectedOptions[0].value !== "" ? parseInt(aircraftSelect.selectedOptions[0].value, 10) : null;

            try {
                const csrfToken = getCookie('csrftoken');

                const response = await fetch('/api/calculate_route/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken
                    },
                    body: JSON.stringify({
                        airport_iatas: selectedAirportIATAs,
                        airplane_id: selectedAircraftId
                    }),
                });

                const data = await response.json();

                if (!response.ok || !data.success) {
                    throw new Error(data.error || `HTTP error! Status: ${response.status}`);
                }

                routeMarkerLayerGroup.clearLayers();

                data.route_segments.forEach(segmentResult => {
                    if (segmentResult.routes && Array.isArray(segmentResult.routes)) {
                        segmentResult.routes.forEach(route => {
                            const pathCoordinates = route.inbetween;

                            if (pathCoordinates && pathCoordinates.length > 1) {
                                let currentSegmentPoints = [];
                                for (let i = 0; i < pathCoordinates.length - 1; i++) {
                                    const p1 = pathCoordinates[i];
                                    const p2 = pathCoordinates[i + 1];

                                    const lonDiff = Math.abs(p1[1] - p2[1]);

                                    const crossesMeridian = (lonDiff > 180) ||
                                                            (Math.sign(p1[1]) !== Math.sign(p2[1]) && Math.abs(p1[1]) + Math.abs(p2[1]) > 180);

                                    if (crossesMeridian) {
                                        if (currentSegmentPoints.length > 1) {
                                            L.polyline(currentSegmentPoints, { color: 'blue', weight: 3, opacity: 0.7 }).addTo(routePolylineLayerGroup);
                                        }

                                        L.circleMarker(p1, {
                                            radius: 6,
                                            color: 'blue',
                                            fillColor: 'blue',
                                            fillOpacity: 1,
                                            weight: 1
                                        }).addTo(routePolylineLayerGroup).bindTooltip(`Отлетаем через меридиан от ${p1[0].toFixed(2)}, ${p1[1].toFixed(2)}`);

                                        L.circleMarker(p2, {
                                            radius: 6,
                                            color: 'blue',
                                            fillColor: 'white',
                                            fillOpacity: 1,
                                            weight: 2
                                        }).addTo(routePolylineLayerGroup).bindTooltip(`Прибываем через меридиан в ${p2[0].toFixed(2)}, ${p2[1].toFixed(2)}`);

                                        currentSegmentPoints = [p2];
                                    } else {
                                        currentSegmentPoints.push(p1);
                                    }
                                }
                                currentSegmentPoints.push(pathCoordinates[pathCoordinates.length - 1]);
                                if (currentSegmentPoints.length > 1) {
                                    L.polyline(currentSegmentPoints, { color: 'blue', weight: 3, opacity: 0.7 }).addTo(routePolylineLayerGroup);
                                }
                            }
                        });
                    }
                });

                if (data.plane_cant) {
                    showErrorMessage("Самолет не смог совершить перелет без промежуточных дозаправок. Маршрут включает дополнительные остановки или некоторые сегменты были построены как прямые.");
                }

                const routeAirports = data.all_path_airports_iatas;

                const selectedAirportIATAsForMarkers = [];
                airportSelectors.forEach(select => {
                    const option = select.selectedOptions[0];
                    if (option && option.value) {
                        selectedAirportIATAsForMarkers.push(option.value);
                    }
                });

                routeAirports.forEach(iata => {
                    const airportData = airportsByCode[iata];
                    if (airportData) {
                        const isSelectedStartOrEnd = selectedAirportIATAsForMarkers.includes(iata);
                        let markerIcon;

                        const iataHtml = `<div class="marker-iata-code">${iata}</div>`;

                        if (isSelectedStartOrEnd) {
                            const index = selectedAirportIATAsForMarkers.indexOf(iata);
                            markerIcon = L.divIcon({
                                className: 'numbered-marker-icon',
                                html: `<div class="marker-number">${index + 1}</div>${iataHtml}`,
                                iconSize: [30, 30],
                                iconAnchor: [15, 30]
                            });
                        } else {
                            markerIcon = L.divIcon({
                                className: 'intermediate-marker-icon',
                                html: iataHtml,
                                iconSize: [25, 25],
                                iconAnchor: [12, 25]
                            });
                        }

                        const m = L.marker([airportData.latitude, airportData.longitude], { icon: markerIcon }).addTo(routeMarkerLayerGroup);
                        m.bindPopup(`<b>${airportData.name}</b> (${airportData.iata_code})`);
                    } else {
                        console.error(`Ошибка: Аэропорт с IATA-кодом ${iata} не найден в allAirportsData.`);
                    }
                });

                document.getElementById('detailPlaneName').textContent = data.plane || 'Не выбран';
                document.getElementById('detailWholeDistance').textContent = data.whole_distance.toFixed(2);
                document.getElementById('detailFlights').textContent = data.flights;
                document.getElementById('detailMaxSegmentDistance').textContent = data.max_distance.toFixed(2);
                document.getElementById('detailTime').textContent = data.time.toFixed(2);
                document.getElementById('detailCost').textContent = data.cost.toFixed(2);

                routeDetailsDiv.classList.add('show');
        errorMessageDiv.classList.remove('show');
        retiredNotice.classList.remove('show');

                const layersInGroup = routePolylineLayerGroup.getLayers();

                if (layersInGroup.length > 0) {
                    let allCoords = [];
                    layersInGroup.forEach(layer => {
                        if (layer && typeof layer.getLatLngs === 'function') {
                            const latlngs = layer.getLatLngs();
                            if (Array.isArray(latlngs[0]) && Array.isArray(latlngs[0][0])) {
                                latlngs.forEach(part => allCoords.push(...part));
                            } else {
                                allCoords.push(...latlngs);
                            }
                        }
                    });

                    if (allCoords.length > 0) {
                        let bounds = L.latLngBounds(allCoords);
                        if (bounds.isValid()) {
                            try {
                                map.fitBounds(bounds.pad(0.1));
                            } catch (e) {
                                console.error("Ошибка при вызове map.fitBounds(bounds.pad(0.1)):", e);
                                showErrorMessage("Ошибка при центрировании карты по маршруту.");
                            }
                        } else {
                            showErrorMessage("Не удалось центрировать карту по маршруту (невалидные координаты).");
                        }
                    } else {
                        showErrorMessage("Не удалось центрировать карту по маршруту (нет координат).");
                    }
                }
            } catch (error) {
                console.error("Ошибка построения маршрута:", error);
                showErrorMessage(`Ошибка построения маршрута: ${error.message}`);
            }
        }

        function createRipple(event) {
            const button = event.currentTarget;
            const circle = document.createElement('span');
            const diameter = Math.max(button.clientWidth, button.clientHeight);
            const radius = diameter / 2;

            circle.style.width = circle.style.height = `${diameter}px`;
            circle.style.left = `${event.clientX - button.offsetLeft - radius}px`;
            circle.style.top = `${event.clientY - button.offsetTop - radius}px`;
            circle.classList.add('ripple');

            const oldRipple = button.querySelector('.ripple');
            if (oldRipple) {
                oldRipple.remove();
            }

            button.appendChild(circle);

            circle.addEventListener('animationend', () => {
                circle.remove();
            });
        }

        document.addEventListener("DOMContentLoaded", async function() {
            const themeToggleBtn = document.getElementById('themeToggleBtn');
            const homeBtn = document.getElementById('homeBtn');
            const body = document.body;
            const themeIcon = themeToggleBtn.querySelector('i');

            const savedTheme = localStorage.getItem('theme');
            if (savedTheme === 'dark') {
                body.classList.add('dark-theme');
                themeIcon.classList.remove('fa-moon');
                themeIcon.classList.add('fa-sun');
            } else {
                body.classList.remove('dark-theme');
                themeIcon.classList.remove('fa-sun');
                themeIcon.classList.add('fa-moon');
            }

            themeToggleBtn.addEventListener('click', (event) => {
                body.classList.toggle('dark-theme');
                if (body.classList.contains('dark-theme')) {
                    themeIcon.classList.remove('fa-moon');
                    themeIcon.classList.add('fa-sun');
                    localStorage.setItem('theme', 'dark');
                } else {
                    themeIcon.classList.remove('fa-sun');
                    themeIcon.classList.add('fa-moon');
                    localStorage.setItem('theme', 'light');
                }
                createRipple(event);
            });

            homeBtn.addEventListener('click', (event) => {
                createRipple(event);
                window.location.href = '/';
            });

            addAirportBtn.addEventListener('click', () => {
                if (airportSelectors.length < 6) {
                    initializeNewAirportSelector(airportSelectors.length + 1);
                    updateMapAndSelections();
                }
            });

            airport1Select.addEventListener('change', updateMapAndSelections);
            airport2Select.addEventListener('change', updateMapAndSelections);
            searchAirport1Input.addEventListener('input', () => filterAirportOptions(airport1Select, searchAirport1Input));
            searchAirport2Input.addEventListener('input', () => filterAirportOptions(airport2Select, searchAirport2Input));

            buildRouteBtn.addEventListener('click', buildRoute);

            await loadInitialData();
        });