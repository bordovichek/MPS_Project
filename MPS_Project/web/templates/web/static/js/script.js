document.addEventListener("DOMContentLoaded", async function() {
    // Функция для получения CSRF токена из cookie
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                // Does this cookie string begin with the name we want?
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    // --- Инициализация и обработка для уведомления о списанном самолете ---
    const aircraftSelectNotice = document.getElementById("aircraft");
    const retiredNotice = document.getElementById("retiredAircraftNotice");
    const retiredNameSpan = document.getElementById("retiredAircraftName");

    if (aircraftSelectNotice) {
        aircraftSelectNotice.addEventListener("change", function() {
            const selectedOption = aircraftSelectNotice.options[aircraftSelectNotice.selectedIndex];
            const inService = selectedOption.getAttribute("data-in-service");
            const aircraftName = selectedOption.textContent.trim();

            if (inService === "false") {
                retiredNameSpan.textContent = aircraftName;
                retiredNotice.classList.remove("hidden");
            } else {
                retiredNotice.classList.add("hidden");
            }
        });
    }

    // --- Инициализация карты и глобальных переменных ---
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

    // Используем L.layerGroup для легкой очистки маркеров и полилиний
    let routePolylineLayerGroup = L.layerGroup().addTo(map);
    let routeMarkerLayerGroup = L.layerGroup().addTo(map);


    let airportSelectors = [];
    let airportSearchInputs = [];
    let originalAirportOptions = []; // Будет содержать клоны <option> элементов

    // --- НАЧАЛЬНАЯ НАСТРОЙКА ДЛЯ СУЩЕСТВУЮЩИХ ВЫБОРОВ АЭРОПОРТОВ ---
    const airport1Select = document.getElementById('airport1');
    const airport2Select = document.getElementById('airport2');
    const searchAirport1Input = document.getElementById('searchAirport1');
    const searchAirport2Input = document.getElementById('searchAirport2');

    airportSelectors.push(airport1Select);
    airportSelectors.push(airport2Select);
    airportSearchInputs.push(searchAirport1Input);
    airportSearchInputs.push(searchAirport2Input);

    // --- НОВЫЕ ГЛОБАЛЬНЫЕ ДАННЫЕ ДЛЯ АЭРОПОРТОВ И САМОЛЕТОВ ---
    let allAirportsData = [];
    let airportsByCode = {}; // Для быстрого поиска аэропорта по IATA-коду
    let allAirplanesData = [];

    // --- НОВАЯ ФУНКЦИЯ ДЛЯ ЗАГРУЗКИ НАЧАЛЬНЫХ ДАННЫХ С БЭКЕНДА ---
    async function loadInitialData() {
        try {
            const response = await fetch('/api/initial_data/');
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            const data = await response.json();
            console.log('Данные о самолетах и аэропортах получены (из initial_data):', data);

            allAirportsData = data.airports;
            allAirplanesData = data.airplanes;

            allAirportsData.forEach(airport => {
                airportsByCode[airport.iata_code] = airport;
            });

            // Создаем массив клонированных <option> элементов
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

            // Заполняем существующие селекторы
            airportSelectors.forEach(select => {
                select.innerHTML = ''; // Очищаем текущие опции
                const defaultOption = document.createElement('option');
                defaultOption.value = "";
                defaultOption.textContent = "--";
                select.appendChild(defaultOption);
                originalAirportOptions.forEach(opt => select.appendChild(opt.cloneNode(true)));
            });

            // Заполняем селектор самолетов
            aircraftSelect.innerHTML = '';
            const noPlaneOption = document.createElement('option');
            noPlaneOption.value = ""; // Значение для "Без выбора самолета"
            noPlaneOption.textContent = "Без выбора самолета";
            aircraftSelect.appendChild(noPlaneOption);

            allAirplanesData.forEach(plane => {
                const option = document.createElement('option');
                option.value = plane.id; // Используем plane.id в качестве значения
                option.textContent = plane.name;
                option.setAttribute('data-in-service', plane.in_service ? 'true' : 'false');
                aircraftSelect.appendChild(option);
            });

            airport1Select.disabled = false;
            searchAirport1Input.disabled = false;
            updateMapAndSelections(); // Инициализация состояния карты и кнопок

        } catch (error) {
            console.error("Ошибка загрузки initial data:", error);
            showErrorMessage(`Ошибка загрузки данных аэропортов/самолетов: ${error.message}`);
        }
    }

    // --- Вспомогательные функции UI ---
    function hideRouteDetailsAndErrors() {
        routeDetailsDiv.classList.add('hidden');
        errorMessageDiv.classList.add('hidden');
        errorMessageDiv.textContent = '';
    }

    function showErrorMessage(message) {
        errorMessageDiv.textContent = message;
        errorMessageDiv.classList.remove('hidden');
        routeDetailsDiv.classList.add('hidden');
    }

    function filterAirportOptions(selectElement, searchInput) {
        const searchText = searchInput.value.toLowerCase();
        const currentValue = selectElement.value; // Сохраняем текущее выбранное значение
        selectElement.innerHTML = '';

        const defaultOption = document.createElement('option');
        defaultOption.value = "";
        defaultOption.textContent = "--";
        selectElement.appendChild(defaultOption);

        let foundCurrentValue = false; // Флаг, чтобы отметить, найдено ли текущее значение среди отфильтрованных

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

        // Если текущее значение было выбрано, но не нашлось среди отфильтрованных, сбрасываем его
        if (!foundCurrentValue && currentValue !== "") {
            selectElement.value = "";
        }
    }

    function updateMapAndSelections() {
        routePolylineLayerGroup.clearLayers(); // Очищаем все полилинии
        routeMarkerLayerGroup.clearLayers();   // Очищаем все маркеры
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
                        number: index + 1 // Номер аэропорта в последовательности
                    });
                    validSelectionsCount++;
                }
            }
        });

        // Управление состоянием селекторов и полей поиска
        for (let i = 0; i < airportSelectors.length; i++) {
            const currentSelect = airportSelectors[i];
            const currentSearch = airportSearchInputs[i];
            const currentGroup = currentSelect.closest('.select-group');
            const removeBtn = currentGroup ? currentGroup.querySelector('.remove-airport-btn') : null;

            if (i === 0) { // Первый аэропорт всегда активен
                currentSelect.disabled = false;
                currentSearch.disabled = false;
                if (removeBtn) removeBtn.classList.add('hidden'); // У первого нет кнопки удаления
            } else {
                const prevSelect = airportSelectors[i - 1];
                if (prevSelect && prevSelect.value) { // Если предыдущий аэропорт выбран
                    currentSelect.disabled = false;
                    currentSearch.disabled = false;
                    if (removeBtn) removeBtn.classList.remove('hidden'); // Показать кнопку удаления
                } else { // Если предыдущий аэропорт не выбран
                    currentSelect.disabled = true;
                    currentSelect.value = ""; // Сбросить значение
                    currentSearch.disabled = true;
                    currentSearch.value = ""; // Сбросить значение
                    filterAirportOptions(currentSelect, currentSearch); // Обновить фильтр
                    if (removeBtn) removeBtn.classList.add('hidden'); // Скрыть кнопку удаления
                }
            }
        }

        // Управление кнопкой "Добавить аэропорт"
        const lastActiveAirportSelect = airportSelectors.findLast(select => !select.disabled);
        const maxAirports = 6; // Ограничение на количество аэропортов
        if (lastActiveAirportSelect && lastActiveAirportSelect.value && airportSelectors.length < maxAirports) {
            addAirportBtn.disabled = false;
        } else {
            addAirportBtn.disabled = true;
        }

        // Управление кнопкой "Построить маршрут"
        if (validSelectionsCount >= 2) {
            buildRouteBtn.disabled = false;
        } else {
            buildRouteBtn.disabled = true;
        }

        // Отрисовка маркеров для выбранных аэропортов (нумерованных)
        if (selectedAirports.length > 0) {
            let allLatsLons = [];
            selectedAirports.forEach(airport => {
                // Маркеры здесь - это для начала/конца/промежуточных остановок,
                // а не для точек разрыва меридиана.
                const iataHtml = `<div class="marker-iata-code">${airport.iata}</div>`;
                const numberIcon = L.divIcon({
                    className: 'numbered-marker-icon',
                    html: `<div class="marker-number">${airport.number}</div>${iataHtml}`, // Добавляем IATA-код
                    iconSize: [30, 30], // Уменьшаем размер иконки в JS
                    iconAnchor: [15, 30] // Соответственно корректируем якорь (центр внизу маркера)
                });

                const m = L.marker([airport.lat, airport.lon], { icon: numberIcon }).addTo(routeMarkerLayerGroup)
                    .bindPopup(`<b>${airport.name}</b> (${airport.iata})`);
                allLatsLons.push([airport.lat, airport.lon]);
            });

            if (allLatsLons.length > 0) {
                const bounds = L.latLngBounds(allLatsLons);
                map.fitBounds(bounds.pad(0.5)); // Подстроить карту под выбранные аэропорты
            }
        }
    }

    // --- Функции для динамического добавления/удаления аэропортов ---
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

        // Кнопка удаления для всех, кроме первых двух
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

        // Добавляем слушатели событий
        selectElement.addEventListener('change', updateMapAndSelections);
        searchInput.addEventListener('input', () => {
            filterAirportOptions(selectElement, searchInput);
        });

        // Прокрутка вниз к новому селектору
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

            // Удаляем элементы из массивов
            airportSelectors.splice(indexToRemove - 1, 1);
            airportSearchInputs.splice(indexToRemove - 1, 1);

            // Обновляем ID и текст для оставшихся селекторов
            for (let i = indexToRemove - 1; i < airportSelectors.length; i++) {
                const currentGroup = airportSelectors[i].closest('.select-group');
                const newIndex = i + 1; // Новый номер для этого селектора

                currentGroup.id = `airportGroup${newIndex}`;
                currentGroup.querySelector('label').htmlFor = `airport${newIndex}`;
                currentGroup.querySelector('label').textContent = `Выберите аэропорт ${newIndex}:`;
                airportSelectors[i].id = `airport${newIndex}`;
                airportSelectors[i].name = `airport${newIndex}`;
                airportSearchInputs[i].id = `searchAirport${newIndex}`;
                airportSearchInputs[i].placeholder = `Поиск Аэропорта ${newIndex} (имя/IATA/страна)`;

                // Обновляем обработчик события для кнопки удаления
                const removeBtn = currentGroup.querySelector('.remove-airport-btn');
                if (removeBtn) {
                    // Удаляем старый обработчик, чтобы избежать дублирования
                    const oldRemoveHandler = removeBtn._currentClickHandler;
                    if (oldRemoveHandler) {
                        removeBtn.removeEventListener('click', oldRemoveHandler);
                    }
                    const newRemoveHandler = () => removeAirportSelector(newIndex);
                    removeBtn.addEventListener('click', newRemoveHandler);
                    removeBtn._currentClickHandler = newRemoveHandler; // Сохраняем ссылку на текущий обработчик
                }
            }
        }
        updateMapAndSelections(); // Обновить карту и состояние UI после удаления
    }

    // --- НОВАЯ ФУНКЦИЯ ДЛЯ РАСЧЕТА ОПТИМАЛЬНОГО МАРШРУТА ---
    async function buildRoute() {
        routePolylineLayerGroup.clearLayers(); // Очищаем все полилинии перед отрисовкой нового
        routeMarkerLayerGroup.clearLayers();   // Очищаем все маркеры перед отрисовкой нового
        hideRouteDetailsAndErrors();

        let selectedAirportIATAs = [];
        airportSelectors.forEach(select => {
            const option = select.selectedOptions[0];
            if (option && option.value) {
                selectedAirportIATAs.push(option.value);
            }
        });

        // Удаляем дубликаты и пустые значения
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
            console.log('Данные от бэка (в buildRoute):', data);

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

                                // Улучшенная проверка на пересечение 180-го меридиана
                                // Если разница долгот больше 180 (т.е. пересекаем меридиан) ИЛИ
                                // если обе долготы находятся очень близко к меридиану (+170...-170)
                                // ИЛИ если они по разные стороны от меридиана (одна > 0, другая < 0) и их сумма по модулю больше 180
                                const crossesMeridian = (lonDiff > 180) ||
                                                        (Math.sign(p1[1]) !== Math.sign(p2[1]) && Math.abs(p1[1]) + Math.abs(p2[1]) > 180);

                                if (crossesMeridian) {
                                    // Пересечение меридиана!
                                    // Отрисовываем текущий накопленный сегмент до точки разрыва
                                    if (currentSegmentPoints.length > 1) {
                                        L.polyline(currentSegmentPoints, { color: 'blue', weight: 3, opacity: 0.7 }).addTo(routePolylineLayerGroup);
                                    }

                                    // --- Маркер "вылета" (закрашенная точка) ---
                                    // Используем p1 как место "отрыва".
                                    // Если нужны точные координаты на 180 меридиане, потребуется интерполяция.
                                    L.circleMarker(p1, { // Используем p1 как место "отрыва"
                                        radius: 6,
                                        color: 'blue',      // Цвет линии
                                        fillColor: 'blue',  // Закрашенная
                                        fillOpacity: 1,
                                        weight: 1           // Тонкая обводка
                                    }).addTo(routePolylineLayerGroup).bindTooltip(`Отлетаем через меридиан от ${p1[0].toFixed(2)}, ${p1[1].toFixed(2)}`);

                                    // --- Маркер "прилёта" (выколотая точка) ---
                                    // Используем p2 как место "приземления".
                                    L.circleMarker(p2, { // Используем p2 как место "приземления"
                                        radius: 6,
                                        color: 'blue',      // Цвет линии
                                        fillColor: 'white', // Белая заливка
                                        fillOpacity: 1,
                                        weight: 2           // Обводка потолще
                                    }).addTo(routePolylineLayerGroup).bindTooltip(`Прибываем через меридиан в ${p2[0].toFixed(2)}, ${p2[1].toFixed(2)}`);


                                    // Начинаем новый сегмент с p2
                                    currentSegmentPoints = [p2]; // Новый сегмент начинается с текущей p2
                                } else {
                                    currentSegmentPoints.push(p1); // Добавляем текущую точку
                                }
                            }
                            // Добавляем последнюю точку и отрисовываем оставшийся сегмент
                            currentSegmentPoints.push(pathCoordinates[pathCoordinates.length - 1]);
                            if (currentSegmentPoints.length > 1) {
                                L.polyline(currentSegmentPoints, { color: 'blue', weight: 3, opacity: 0.7 }).addTo(routePolylineLayerGroup);
                            }
                        }
                    });
                }
            });

            // --- Отображение предупреждения, если самолет не смог совершить перелет без дозаправок ---
            if (data.plane_cant) {
                showErrorMessage("Самолет не смог совершить перелет без промежуточных дозаправок. Маршрут включает дополнительные остановки или некоторые сегменты были построены как прямые.");
            }

            // --- Отрисовка маркеров для начального/конечного/промежуточных аэропортов ---
            const routeAirports = data.all_path_airports_iatas;
            console.log("Отрисовка маркеров для аэропортов маршрута:", routeAirports);

            // Сохраняем выбранные пользователем аэропорты в отдельный массив для логики маркеров
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
                    // Используем selectedAirportIATAsForMarkers для проверки
                    const isSelectedStartOrEnd = selectedAirportIATAsForMarkers.includes(iata);
                    let markerIcon;

                    const iataHtml = `<div class="marker-iata-code">${iata}</div>`;

                    if (isSelectedStartOrEnd) {
                        // Используем индекс из массива selectedAirportIATAsForMarkers
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
                    console.log(`  Добавлен маркер для ${airportData.name} (${iata})`);
                } else {
                    console.error(`  Ошибка: Аэропорт с IATA-кодом ${iata} не найден в allAirportsData.`);
                }
            });

            // --- Обновление информации о маршруте в UI ---
            document.getElementById('detailPlaneName').textContent = data.plane || 'Не выбран';
            document.getElementById('detailWholeDistance').textContent = data.whole_distance.toFixed(2);
            document.getElementById('detailFlights').textContent = data.flights;
            document.getElementById('detailMaxSegmentDistance').textContent = data.max_distance.toFixed(2);
            document.getElementById('detailTime').textContent = data.time.toFixed(2);
            document.getElementById('detailCost').textContent = data.cost.toFixed(2);
            routeDetailsDiv.classList.remove('hidden');

            // --- ПОДСТРОЙКА КАРТЫ ПОД МАРШРУТ ---
            const layersInGroup = routePolylineLayerGroup.getLayers();
            console.log(" layersInGroup (массив слоев):", layersInGroup);
            console.log(" Количество слоев в группе:", layersInGroup.length);

            if (layersInGroup.length > 0) {
                console.log("Группа полилиний не пуста. Пытаемся вручную собрать границы...");

                let allCoords = [];
                layersInGroup.forEach(layer => {
                    // Проверяем, что слой является полилинией и имеет метод getLatLngs
                    if (layer && typeof layer.getLatLngs === 'function') {
                        const latlngs = layer.getLatLngs();
                        // Если полилиния имеет несколько частей (мультиполилиния)
                        if (Array.isArray(latlngs[0]) && Array.isArray(latlngs[0][0])) {
                            latlngs.forEach(part => allCoords.push(...part));
                        } else {
                            allCoords.push(...latlngs);
                        }
                    }
                });

                if (allCoords.length > 0) {
                    let bounds = L.latLngBounds(allCoords);
                    console.log("Собранные границы (bounds) вручную:", bounds);
                    console.log("Тип 'bounds' вручную:", typeof bounds);
                    console.log("bounds instanceof L.LatLngBounds вручную:", bounds instanceof L.LatLngBounds);

                    if (bounds.isValid()) {
                        console.log("Границы валидны. Пытаемся подстроить карту...");
                        try {
                            map.fitBounds(bounds.pad(0.1));
                            console.log("Карта успешно подстроена под маршрут.");
                        } catch (e) {
                            console.error("Ошибка при вызове map.fitBounds(bounds.pad(0.1)):", e);
                            showErrorMessage("Ошибка при центрировании карты по маршруту.");
                        }
                    } else {
                        console.warn("Вручную собранные границы маршрута невалидны. Возможно, некорректные координаты?");
                        showErrorMessage("Не удалось центрировать карту по маршруту (невалидные координаты).");
                    }
                } else {
                    console.warn("Не удалось собрать координаты из слоев для построения границ.");
                    showErrorMessage("Не удалось центрировать карту по маршруту (нет координат).");
                }
            } else {
                console.warn("Нет слоев полилиний для центрирования карты. Пропускаем fitBounds.");
            }
            // --- КОНЕЦ БЛОКА ПОДСТРОЙКИ КАРТЫ ---

        } catch (error) {
            console.error("Ошибка построения маршрута:", error);
            showErrorMessage(`Ошибка построения маршрута: ${error.message}`);
        }
    }

    // --- Слушатели событий ---
    addAirportBtn.addEventListener('click', () => {
        if (airportSelectors.length < 6) { // Максимум 6 аэропортов
            initializeNewAirportSelector(airportSelectors.length + 1);
            updateMapAndSelections();
        }
    });

    // Добавляем слушатели для существующих селекторов и полей поиска
    airport1Select.addEventListener('change', updateMapAndSelections);
    airport2Select.addEventListener('change', updateMapAndSelections);
    searchAirport1Input.addEventListener('input', () => filterAirportOptions(airport1Select, searchAirport1Input));
    searchAirport2Input.addEventListener('input', () => filterAirportOptions(airport2Select, searchAirport2Input));

    buildRouteBtn.addEventListener('click', buildRoute);

    // --- Инициализация при загрузке страницы ---
    await loadInitialData(); // Загружаем начальные данные
    // updateMapAndSelections() вызывается внутри loadInitialData после загрузки
});