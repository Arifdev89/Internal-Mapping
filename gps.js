
document.addEventListener("DOMContentLoaded", () => {


    const $ = id => document.getElementById(id);

    const el = {
        destination: $("destination"),
        searchForm: $("search-form"),
        searchButton: $("search-btn"),
        searchStatus: $("search-status"),
        searchResults: $("search-results"),

        selectedPlace: $("selected-place"),
        placeName: $("place-name"),
        placeAddress: $("place-address"),
        clearButton: $("clear-destination"),

        gpsStatus: $("gps-status"),
        dbStatus: $("db-status"),
        lat: $("lat"),
        lng: $("lng"),
        acc: $("acc"),
        follow: $("follow"),
        locate: $("locate-btn"),

        routeStatus: $("route-status"),
        routeDistance: $("route-distance"),
        routeDuration: $("route-duration"),

        indoorControls: $("indoor-controls"),
        enterBuilding: $("enter-building-btn"),
        indoorPanel: $("indoor-panel"),
        buildingName: $("indoor-building-name"),

        floorSelect: $("floor-select"),
        indoorStart: $("indoor-start"),
        indoorDestination: $("indoor-destination"),
        navigate: $("indoor-navigate-btn"),
        clearRoute: $("indoor-clear-route-btn"),

        indoorRouteStatus: $("indoor-route-status"),
        indoorRouteDetails: $("indoor-route-details"),

        indoorStatus: $("indoor-status"),
        indoorLocations: $("indoor-locations"),
        indoorNodes: $("indoor-nodes"),

        indoorMap: $("indoor-svg-wrapper")
    };

    for (const [key, value] of Object.entries(el)) {
        if (!value) {
            console.error("Missing HTML element:", key);
            return;
        }
    }

    if (typeof L === "undefined") {
        el.searchStatus.textContent =
            "Leaflet failed to load.";
        return;
    }


    let map;
    let currentMarker = null;
    let accuracyCircle = null;
    let destinationMarker = null;
    let outdoorRouteLayer = null;

    let currentPosition = null;
    let watchId = null;

    let selectedBuilding = null;

    let floors = [];
    let allFloorData = new Map();

    let selectedFloor = null;
    let currentLocations = [];
    let currentNodes = [];

    let routeData = null;
    let routeLayer = null;

    let requestNumber = 0;
    let routeRequestController = null;

    const SVG_NS = "http://www.w3.org/2000/svg";



    map = L.map("map").setView(
        [20.5937, 78.9629],
        5
    );

    L.tileLayer(
        "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        {
            maxZoom: 20,
            attribution: "&copy; OpenStreetMap contributors"
        }
    ).addTo(map);

   

    function status(element, message, type = "warn") {
        element.textContent = message;
        element.className = "badge " + type;
    }

    function getCookie(name) {
        const value = document.cookie
            .split("; ")
            .find(row => row.startsWith(name + "="));

        return value
            ? decodeURIComponent(value.split("=").slice(1).join("="))
            : null;
    }

    async function fetchJSON(url, options = {}) {
        const response = await fetch(url, {
            credentials: "same-origin",
            ...options
        });

        const text = await response.text();

        let data;

        try {
            data = JSON.parse(text);
        } catch {
            throw new Error(
                `Invalid server response (${response.status}).`
            );
        }

        if (!response.ok) {
            throw new Error(
                data.error ||
                data.message ||
                `HTTP ${response.status}`
            );
        }

        return data;
    }

    async function postJSON(url, body, signal) {
        const csrf = getCookie("csrftoken");

        if (!csrf) {
            throw new Error(
                "CSRF token missing. Refresh the page."
            );
        }

        return fetchJSON(url, {
            method: "POST",
            signal,
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": csrf
            },
            body: JSON.stringify(body)
        });
    }

    function formatDistance(value) {
        const distance = Number(value);

        if (!Number.isFinite(distance)) return "";

        return distance >= 1000
            ? (distance / 1000).toFixed(2) + " km"
            : Math.round(distance) + " m";
    }

    function formatDuration(value) {
        const minutes = Math.round(Number(value) / 60);

        if (!Number.isFinite(minutes)) return "";

        if (minutes < 60) {
            return minutes + " minutes";
        }

        return (
            Math.floor(minutes / 60) +
            " hr " +
            (minutes % 60) +
            " min"
        );
    }

    function number(value, fallback = 0) {
        const n = Number(value);
        return Number.isFinite(n) ? n : fallback;
    }

    function createSVG(tag, attributes = {}) {
        const node = document.createElementNS(SVG_NS, tag);

        Object.entries(attributes).forEach(([key, value]) => {
            node.setAttribute(key, String(value));
        });

        return node;
    }



    async function checkDatabase() {
        try {
            const data = await fetchJSON(
                "/api/status/database/"
            );

            status(
                el.dbStatus,
                data.success ? "Connected" : "Disconnected",
                data.success ? "success" : "warn"
            );

        } catch (error) {
            console.error(error);
            status(el.dbStatus, "Connection error");
        }
    }

  

    function startGPS() {
        if (!navigator.geolocation) {
            status(el.gpsStatus, "Not supported");
            return;
        }

        if (watchId !== null) return;

        status(el.gpsStatus, "Requesting GPS");

        watchId = navigator.geolocation.watchPosition(
            position => {
                const coords = position.coords;

                currentPosition = {
                    latitude: coords.latitude,
                    longitude: coords.longitude,
                    accuracy: coords.accuracy
                };

                el.lat.textContent =
                    coords.latitude.toFixed(6);

                el.lng.textContent =
                    coords.longitude.toFixed(6);

                el.acc.textContent =
                    Math.round(coords.accuracy) + " metres";

                status(el.gpsStatus, "Active", "success");

                updateGPSMap();
            },

            error => {
                const messages = {
                    1: "Permission denied",
                    2: "Unavailable",
                    3: "GPS timeout"
                };

                status(
                    el.gpsStatus,
                    messages[error.code] || "GPS error"
                );

                console.error(error);
            },

            {
                enableHighAccuracy: true,
                maximumAge: 5000,
                timeout: 30000
            }
        );
    }

    function updateGPSMap() {
        if (!currentPosition) return;

        const point = [
            currentPosition.latitude,
            currentPosition.longitude
        ];

        if (!currentMarker) {
            currentMarker = L.marker(point).addTo(map);
            currentMarker.bindPopup("Your location");
        } else {
            currentMarker.setLatLng(point);
        }

        if (!accuracyCircle) {
            accuracyCircle = L.circle(point, {
                radius: currentPosition.accuracy,
                color: "#2563eb",
                fillOpacity: 0.12
            }).addTo(map);
        } else {
            accuracyCircle.setLatLng(point);
            accuracyCircle.setRadius(
                currentPosition.accuracy
            );
        }

        if (el.follow.checked) {
            map.panTo(point);
        }
    }

   

    async function searchBuildings(query) {
        el.searchButton.disabled = true;
        el.searchResults.innerHTML = "";

        el.searchStatus.textContent =
            "Searching buildings...";

        try {
            const data = await fetchJSON(
                "/api/osm/buildings/search/?q=" +
                encodeURIComponent(query)
            );

            const results = data.results || [];

            if (!results.length) {
                el.searchStatus.textContent =
                    "No buildings found.";
                return;
            }

            el.searchStatus.textContent =
                results.length + " results found.";

            results.forEach(building => {
                const item = document.createElement("div");
                item.className = "search-result";

                const name = document.createElement("strong");
                name.textContent = building.name;

                const address = document.createElement("p");
                address.textContent = building.address || "";

                item.append(name, address);

                item.addEventListener("click", () => {
                    selectBuilding(building);
                });

                el.searchResults.appendChild(item);
            });

        } catch (error) {
            el.searchStatus.textContent = error.message;
        } finally {
            el.searchButton.disabled = false;
        }
    }



    async function importBuilding(building) {
        const data = await postJSON(
            "/api/osm/buildings/import/",
            {
                osm_ref: building.osm_ref,
                osm_type: building.osm_type,
                osm_id: building.osm_id
            }
        );

        if (!data.success) {
            throw new Error(
                data.error || "Building import failed."
            );
        }

        return data.building;
    }



    async function selectBuilding(osmBuilding) {
        try {
            el.searchStatus.textContent =
                "Importing building...";

            resetApplication();

            const building = await importBuilding(osmBuilding);

            selectedBuilding = building;

            el.selectedPlace.hidden = false;
            el.placeName.textContent = building.name;
            el.placeAddress.textContent = building.address || "";

            el.searchResults.innerHTML = "";

            el.searchStatus.textContent =
                "Building imported successfully.";

            el.indoorControls.hidden = false;
            el.enterBuilding.disabled = false;

            const lat = number(building.latitude, NaN);
            const lng = number(building.longitude, NaN);

            if (Number.isFinite(lat) && Number.isFinite(lng)) {
                const point = [lat, lng];

                if (destinationMarker) {
                    map.removeLayer(destinationMarker);
                }

                destinationMarker = L.marker(point)
                    .addTo(map)
                    .bindPopup(building.name);

                map.setView(point, 17);
            }

            el.routeStatus.textContent =
                "Building selected. Enter the building for indoor navigation.";

            if (currentPosition) {
                drawOutdoorRoute();
            }

        } catch (error) {
            console.error(error);
            el.searchStatus.textContent = error.message;
        }
    }


    async function drawOutdoorRoute() {
        if (!currentPosition || !selectedBuilding) return;

        el.routeStatus.textContent =
            "Calculating outdoor walking route...";

        try {
            const data = await postJSON(
                "/api/outdoor/route/",
                {
                    building_id: selectedBuilding.id,
                    latitude: currentPosition.latitude,
                    longitude: currentPosition.longitude
                }
            );

            if (!data.success) {
                throw new Error(
                    data.error || "Outdoor route failed."
                );
            }

            const coordinates =
                data.route.geometry.coordinates;

            const points = coordinates.map(point => [
                point[1],
                point[0]
            ]);

            if (outdoorRouteLayer) {
                map.removeLayer(outdoorRouteLayer);
            }

            outdoorRouteLayer = L.polyline(points, {
                color: "#2563eb",
                weight: 6
            }).addTo(map);

            map.fitBounds(
                outdoorRouteLayer.getBounds(),
                { padding: [40, 40] }
            );

            el.routeDistance.textContent =
                "Distance: " +
                formatDistance(data.route.distance_meters);

            el.routeDuration.textContent =
                "Estimated time: " +
                formatDuration(data.route.duration_seconds);

            el.routeStatus.textContent =
                "Outdoor route ready.";

        } catch (error) {
            console.error(error);
            el.routeStatus.textContent = error.message;
        }
    }



    async function enterBuilding() {
        if (!selectedBuilding) return;

        el.enterBuilding.disabled = true;

        el.indoorStatus.textContent =
            "Loading building floors...";

        try {
            const data = await fetchJSON(
                `/api/buildings/${selectedBuilding.id}/floors/`
            );

            if (!data.success || !data.results.length) {
                throw new Error(
                    "No indoor floors configured for this building."
                );
            }

            floors = data.results;

            // Clear previously loaded floor data.
            allFloorData.clear();

            // Create floor selector.
            el.floorSelect.innerHTML =
                '<option value="">Choose floor</option>';

            floors.forEach(floor => {
                const option = document.createElement("option");

                option.value = floor.id;
                option.textContent = floor.name;

                el.floorSelect.appendChild(option);
            });

            el.indoorPanel.hidden = false;
            el.indoorControls.hidden = true;

            // Load locations and nodes for EVERY floor.
            el.indoorStatus.textContent =
                "Loading rooms and navigation nodes for all floors...";

            await Promise.all(
                floors.map(loadFloorData)
            );

            populateRouteSelectors();

            // Automatically select the first floor.
            if (floors.length) {
                el.floorSelect.value = floors[0].id;
                displayFloor(floors[0].id);
            }

            el.indoorStatus.textContent =
                `${floors.length} floors loaded successfully.`;

        } catch (error) {
            console.error(error);
            el.indoorStatus.textContent = error.message;
            el.enterBuilding.disabled = false;
        }
    }

  

    async function loadFloorData(floor) {
        const [locationData, nodeData] = await Promise.all([
            fetchJSON(`/api/floors/${floor.id}/locations/`),
            fetchJSON(`/api/floors/${floor.id}/nodes/`)
        ]);

        if (!locationData.success || !nodeData.success) {
            throw new Error(
                `Could not load ${floor.name}.`
            );
        }

        allFloorData.set(String(floor.id), {
            floor,
            locations: locationData.results || [],
            nodes: nodeData.results || []
        });
    }


    function populateRouteSelectors() {
        el.indoorStart.innerHTML =
            '<option value="">Choose starting location</option>';

        el.indoorDestination.innerHTML =
            '<option value="">Choose destination</option>';

        floors.forEach(floor => {
            const data = allFloorData.get(String(floor.id));

            if (!data) return;

            const group1 = document.createElement("optgroup");
            const group2 = document.createElement("optgroup");

            group1.label = floor.name;
            group2.label = floor.name;

            data.locations.forEach(location => {
                const linkedNode = data.nodes.find(
                    node =>
                        String(node.location_id) === String(location.id)
                );

                if (!linkedNode) return;

                const option1 = document.createElement("option");

                option1.value = linkedNode.id;
                option1.textContent = location.name;

                option1.dataset.floorId = floor.id;

                const option2 = option1.cloneNode(true);

                group1.appendChild(option1);
                group2.appendChild(option2);
            });

            if (group1.children.length) {
                el.indoorStart.appendChild(group1);
                el.indoorDestination.appendChild(group2);
            }
        });
    }



    function displayFloor(floorId) {
        const data = allFloorData.get(String(floorId));

        if (!data) return;

        selectedFloor = data.floor;
        currentLocations = data.locations;
        currentNodes = data.nodes;

        displayFloorMap(
            selectedFloor,
            currentLocations,
            currentNodes
        );

        displayLocations(currentLocations);
        displayNodes(currentNodes);

        // If a route has already been calculated,
        // display the correct part of that route.
        if (routeData) {
            drawRouteForFloor(floorId);
        }

        el.indoorStatus.textContent =
            `${selectedFloor.name}: ` +
            `${currentLocations.length} rooms, ` +
            `${currentNodes.length} navigation nodes.`;
    }



    function displayFloorMap(floor, locations, nodes) {
        el.indoorMap.innerHTML = "";

        const width = number(floor.svg_width, 1000);
        const height = number(floor.svg_height, 600);

        if (width <= 0 || height <= 0) {
            throw new Error("Invalid SVG floor dimensions.");
        }

        const svg = createSVG("svg", {
            viewBox: `0 0 ${width} ${height}`,
            role: "img",
            "aria-label": floor.name
        });

        svg.style.width = "100%";
        svg.style.height = "auto";

        // Floor background.
        svg.appendChild(createSVG("rect", {
            x: 0,
            y: 0,
            width,
            height,
            fill: "#f1f5f9",
            stroke: "#64748b",
            "stroke-width": 4
        }));

        // Floor title.
        const title = createSVG("text", {
            x: width / 2,
            y: 28,
            "text-anchor": "middle",
            "font-size": 22,
            "font-weight": "bold",
            fill: "#1e293b"
        });

        title.textContent = floor.name;
        svg.appendChild(title);

        // Draw rooms.
        locations.forEach(location => {
            const x = number(location.x);
            const y = number(location.y);
            const w = number(location.width);
            const h = number(location.height);

            if (w <= 0 || h <= 0) return;

            const group = createSVG("g", {
                "data-location-id": location.id
            });

            const rect = createSVG("rect", {
                x, y,
                width: w,
                height: h,
                rx: 5,
                fill: "#dbeafe",
                stroke: "#2563eb",
                "stroke-width": 2
            });

            const label = createSVG("text", {
                x: x + w / 2,
                y: y + h / 2,
                "text-anchor": "middle",
                "dominant-baseline": "middle",
                "font-size": Math.max(10, Math.min(16, w / 8)),
                fill: "#1e3a8a",
                "pointer-events": "none"
            });

            label.textContent = location.name;

            group.append(rect, label);

            group.addEventListener("click", () => {
                selectLocation(location.id);
            });

            svg.appendChild(group);
        });

        // Draw navigation nodes.
        nodes.forEach(node => {
            const x = number(node.x);
            const y = number(node.y);

            const group = createSVG("g", {
                class: "indoor-node"
            });

            const circle = createSVG("circle", {
                cx: x,
                cy: y,
                r: 6,
                fill: "#2563eb",
                stroke: "white",
                "stroke-width": 2
            });

            const label = createSVG("text", {
                x: x + 9,
                y: y - 8,
                "font-size": 10,
                fill: "#1e40af"
            });

            label.textContent = node.code || "";

            const tooltip = createSVG("title");
            tooltip.textContent =
                node.name || node.code || "Navigation node";

            group.append(circle, label, tooltip);
            svg.appendChild(group);
        });

        el.indoorMap.appendChild(svg);
    }



    function displayLocations(locations) {
        el.indoorLocations.innerHTML = "";

        if (!locations.length) {
            el.indoorLocations.textContent =
                "No rooms found.";
            return;
        }

        locations.forEach(location => {
            const item = document.createElement("div");

            item.className = "indoor-item";
            item.textContent = location.name;

            item.addEventListener("click", () => {
                selectLocation(location.id);
            });

            el.indoorLocations.appendChild(item);
        });
    }



    function displayNodes(nodes) {
        el.indoorNodes.innerHTML = "";

        if (!nodes.length) {
            el.indoorNodes.textContent =
                "No navigation nodes found.";
            return;
        }

        nodes.forEach(node => {
            const item = document.createElement("div");

            item.className = "indoor-item";

            item.textContent =
                `${node.name || node.code} (${node.node_type})`;

            el.indoorNodes.appendChild(item);
        });
    }

    

    function selectLocation(locationId) {
        const location = currentLocations.find(
            item => String(item.id) === String(locationId)
        );

        if (!location) return;

        const node = currentNodes.find(
            item =>
                String(item.location_id) === String(locationId)
        );

        if (!node) {
            el.indoorStatus.textContent =
                "This room has no connected navigation node.";
            return;
        }

        el.indoorStart.value = String(node.id);

        el.indoorStatus.textContent =
            `Selected starting location: ${location.name}`;
    }



    async function calculateIndoorRoute() {
        const startId = el.indoorStart.value;
        const endId = el.indoorDestination.value;

        if (!startId || !endId) {
            el.indoorRouteStatus.textContent =
                "Select both starting and destination locations.";
            return;
        }

        if (startId === endId) {
            el.indoorRouteStatus.textContent =
                "Starting and destination locations must differ.";
            return;
        }

        if (!selectedBuilding) {
            el.indoorRouteStatus.textContent =
                "Select a building first.";
            return;
        }

        if (routeRequestController) {
            routeRequestController.abort();
        }

        const controller = new AbortController();
        routeRequestController = controller;

        el.navigate.disabled = true;

        el.indoorRouteStatus.textContent =
            "Calculating shortest indoor route...";

        try {
            const data = await postJSON(
                "/api/indoor/route/",
                {
                    start_node_id: Number(startId),
                    end_node_id: Number(endId),
                    accessible_only: false
                },
                controller.signal
            );

            if (controller !== routeRequestController) return;

            if (!data.success) {
                throw new Error(
                    data.error || "Indoor navigation failed."
                );
            }

            if (!Array.isArray(data.nodes) || !data.nodes.length) {
                throw new Error(
                    "The server returned no navigation nodes."
                );
            }

            if (
                !Array.isArray(data.floor_segments) ||
                !data.floor_segments.length
            ) {
                throw new Error(
                    "The server returned no floor segments."
                );
            }

            routeData = data;

           
            const firstSegment = data.floor_segments[0];

            el.floorSelect.value = firstSegment.floor_id;

            displayFloor(firstSegment.floor_id);

            drawRouteForFloor(firstSegment.floor_id);

            displayRouteInstructions(data);

            el.indoorRouteStatus.textContent =
                "Route calculated successfully! Follow the orange path.";

        } catch (error) {
            if (error.name === "AbortError") return;

            console.error("Indoor route error:", error);

            el.indoorRouteStatus.textContent =
                error.message;

        } finally {
            if (controller === routeRequestController) {
                routeRequestController = null;
            }

            el.navigate.disabled = false;
        }
    }

   

    function drawRouteForFloor(floorId) {
        const svg = el.indoorMap.querySelector("svg");

        if (!svg || !routeData) return;

        if (routeLayer) {
            routeLayer.remove();
            routeLayer = null;
        }

        const segment = routeData.floor_segments.find(
            item => String(item.floor_id) === String(floorId)
        );

        if (!segment || !segment.nodes.length) {
            return;
        }

        const points = segment.nodes.map(node => ({
            x: number(node.x, NaN),
            y: number(node.y, NaN),
            id: node.id
        }));

        if (points.some(point =>
            !Number.isFinite(point.x) ||
            !Number.isFinite(point.y)
        )) {
            el.indoorRouteStatus.textContent =
                "Some route nodes have invalid coordinates.";
            return;
        }

        const group = createSVG("g", {
            class: "indoor-route-group"
        });

        // Route path.
        const path = createSVG("path", {
            d: points.map((point, index) =>
                `${index === 0 ? "M" : "L"} ${point.x} ${point.y}`
            ).join(" "),
            class: "indoor-route-line"
        });

        group.appendChild(path);

        // Starting and destination markers on this floor.
        points.forEach((point, index) => {
            const isFirst = index === 0;
            const isLast = index === points.length - 1;

            const circle = createSVG("circle", {
                cx: point.x,
                cy: point.y,
                r: isFirst || isLast ? 12 : 6,
                fill: isFirst
                    ? "#16a34a"
                    : isLast
                        ? "#dc2626"
                        : "#f97316",
                class: "indoor-route-point"
            });

            const tooltip = createSVG("title");

            tooltip.textContent = isFirst
                ? "Starting point"
                : isLast
                    ? "Destination"
                    : "Route waypoint";

            circle.appendChild(tooltip);
            group.appendChild(circle);
        });

        svg.appendChild(group);

        routeLayer = group;
    }


    function displayRouteInstructions(data) {
        el.indoorRouteDetails.innerHTML = "";

        const details = document.createElement("div");
        details.className = "route-details";

        const distance = document.createElement("p");
        distance.textContent =
            "Total distance: " + formatDistance(data.distance);

        const duration = document.createElement("p");
        duration.textContent =
            "Estimated time: " +
            formatDuration(data.estimated_time_seconds);

        const floorsText = document.createElement("p");
        floorsText.textContent =
            "Floors involved: " + data.floor_segments.length;

        details.append(distance, duration, floorsText);

        const heading = document.createElement("h4");
        heading.textContent = "Route instructions";

        details.appendChild(heading);

        data.floor_segments.forEach((segment, index) => {
            const instruction = document.createElement("div");

            instruction.className = "route-instruction";

            let message =
                `${index + 1}. ${segment.floor_name}: ` +
                `${segment.nodes.length} route points`;

            if (index < data.floor_segments.length - 1) {
                message +=
                    ". Continue to the next floor using the connected staircase.";
            }

            instruction.textContent = message;

            details.appendChild(instruction);
        });

        el.indoorRouteDetails.appendChild(details);
    }

 

    function clearIndoorRoute() {
        if (routeRequestController) {
            routeRequestController.abort();
            routeRequestController = null;
        }

        routeData = null;

        if (routeLayer) {
            routeLayer.remove();
            routeLayer = null;
        }

        el.indoorRouteStatus.textContent =
            "Select a starting point and destination.";

        el.indoorRouteDetails.innerHTML = "";
    }

    

    function resetApplication() {
        clearIndoorRoute();

        floors = [];
        allFloorData.clear();

        selectedFloor = null;
        currentLocations = [];
        currentNodes = [];

        el.indoorPanel.hidden = true;
        el.indoorControls.hidden = true;

        el.enterBuilding.disabled = true;

        el.floorSelect.innerHTML =
            '<option value="">Choose floor</option>';

        el.indoorStart.innerHTML =
            '<option value="">Choose starting location</option>';

        el.indoorDestination.innerHTML =
            '<option value="">Choose destination</option>';

        el.indoorMap.innerHTML = "";

        el.indoorLocations.innerHTML = "";
        el.indoorNodes.innerHTML = "";
        el.indoorRouteDetails.innerHTML = "";
    }

   

    el.searchForm.addEventListener("submit", event => {
        event.preventDefault();

        const query = el.destination.value.trim();

        if (query.length < 3) {
            el.searchStatus.textContent =
                "Enter at least 3 characters.";
            return;
        }

        searchBuildings(query);
    });

 

    el.enterBuilding.addEventListener(
        "click",
        enterBuilding
    );



    el.floorSelect.addEventListener("change", event => {
        const floorId = event.target.value;

        if (!floorId) return;

        displayFloor(floorId);
    });



    el.navigate.addEventListener(
        "click",
        calculateIndoorRoute
    );

 

    el.clearRoute.addEventListener(
        "click",
        clearIndoorRoute
    );


    el.clearButton.addEventListener("click", () => {
        selectedBuilding = null;

        resetApplication();

        if (destinationMarker) {
            map.removeLayer(destinationMarker);
            destinationMarker = null;
        }

        if (outdoorRouteLayer) {
            map.removeLayer(outdoorRouteLayer);
            outdoorRouteLayer = null;
        }

        el.selectedPlace.hidden = true;
        el.searchResults.innerHTML = "";
        el.destination.value = "";

        el.routeStatus.textContent =
            "Search for a destination to begin.";

        el.routeDistance.textContent = "";
        el.routeDuration.textContent = "";

        el.searchStatus.textContent = "";
    });


    el.locate.addEventListener("click", () => {
        if (!currentPosition) {
            el.gpsStatus.textContent =
                "Waiting for GPS...";
            return;
        }

        map.setView(
            [
                currentPosition.latitude,
                currentPosition.longitude
            ],
            18
        );
    });



    async function initialize() {
        await checkDatabase();

        startGPS();

        console.log(
            "VVIT Hybrid Indoor Navigator initialized."
        );
    }

    initialize();

   

    window.addEventListener("beforeunload", () => {
        if (watchId !== null) {
            navigator.geolocation.clearWatch(watchId);
        }

        if (routeRequestController) {
            routeRequestController.abort();
        }
    });

});
