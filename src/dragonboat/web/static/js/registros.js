// ── Mapa GPS del día con segmentos coloreados y tramos de prueba ──
(function() {
    var container = document.getElementById("mapa-registros");
    if (!container) return;

    var dataAttr = container.getAttribute("data-segments") || "[]";
    var testDataAttr = container.getAttribute("data-test-segments") || "[]";
    var segments, testSegments;
    try {
        segments = JSON.parse(dataAttr);
    } catch (e) {
        segments = [];
    }
    try {
        testSegments = JSON.parse(testDataAttr);
    } catch (e) {
        testSegments = [];
    }

    var hasSegments = segments.length && !segments.every(function(s) { return s.points.length < 2; });
    var hasTestSegments = testSegments.length && !testSegments.every(function(s) { return s.points.length < 2; });

    if (!hasSegments && !hasTestSegments) {
        container.innerHTML = '<div style="text-align:center;padding:2rem;color:#64748b;">Mapa no disponible — datos GPS no registrados</div>';
        return;
    }

    var allPoints = [];
    var map = L.map(container);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: "&copy; OpenStreetMap contributors",
        maxZoom: 18
    }).addTo(map);

    function addDirectionArrows(latlngs) {
        var arrowColor = "#3c3c3f";
        var interval = Math.max(15, Math.floor(latlngs.length / 10));
        if (interval < 5 || latlngs.length < interval * 2) return;

        for (var i = interval; i < latlngs.length - 2; i += interval) {
            var p1 = latlngs[i - 2] || latlngs[i - 1];
            var p2 = latlngs[i];
            if (!p1 || !p2) continue;

            var dx = p2[0] - p1[0];
            var dy = p2[1] - p1[1];
            var len = Math.sqrt(dx * dx + dy * dy);
            if (len < 0.000001) continue;

            var ux = dx / len;
            var uy = dy / len;
            var size = Math.min(len * 4.1, 0.052);

            var tip = [p2[0], p2[1]];
            var tail = [
                p2[0] - size * 2.5 * ux,
                p2[1] - size * 2.5 * uy
            ];

            // Stem (thin line)
            L.polyline([tail, tip], {
                color: arrowColor,
                weight: 1,
                opacity: 0.6,
                interactive: false
            }).addTo(map);

            // Arrowhead (triangle)
            var wingSize = size * 0.38;
            var leftWing = [
                p2[0] - wingSize * ux + wingSize * 0.7 * uy,
                p2[1] - wingSize * uy - wingSize * 0.7 * ux
            ];
            var rightWing = [
                p2[0] - wingSize * ux - wingSize * 0.7 * uy,
                p2[1] - wingSize * uy + wingSize * 0.7 * ux
            ];

            L.polygon([tip, leftWing, rightWing], {
                color: arrowColor,
                fillColor: arrowColor,
                fillOpacity: 0.55,
                opacity: 0.85,
                weight: 1,
                interactive: false
            }).addTo(map);
        }
    }

    // ── Background segments (moving/stopped) ──
    segments.forEach(function(seg) {
        var color = seg.status === "moving" ? "#22c55e" : "#ef4444";
        var latlngs = seg.points.map(function(p) { return [p[0], p[1]]; });
        if (latlngs.length >= 2) {
            L.polyline(latlngs, {color: color, weight: 4, opacity: 0.85}).addTo(map);
            addDirectionArrows(latlngs);
            for (var i = 0; i < latlngs.length; i++) {
                allPoints.push(latlngs[i]);
            }
        }
    });

    // ── Test segments (colored by distance, clickable) ──
    testSegments.forEach(function(seg) {
        var latlngs = seg.points.map(function(p) { return [p[0], p[1]]; });
        if (latlngs.length < 2) return;

        var polyline = L.polyline(latlngs, {
            color: seg.color,
            weight: 6,
            opacity: 0.9
        }).addTo(map);
        addDirectionArrows(latlngs);

        // Star marker at start
        var startPt = latlngs[0];
        L.marker(startPt, {
            icon: L.divIcon({
                className: "",
                html: '<div style="color:#22c55e;font-size:22px;font-weight:bold;text-align:center;line-height:1.1;">★<br><span style="font-size:10px;letter-spacing:1px;color:#22c55e;">STAR</span></div>',
                iconSize: [40, 44],
                iconAnchor: [20, 44]
            }),
            interactive: false
        }).addTo(map);

        // Checkered flag at end
        var endPt = latlngs[latlngs.length - 1];
        L.marker(endPt, {
            icon: L.divIcon({
                className: "",
                html: '<div style="font-size:26px;text-align:center;line-height:1;">🏁</div>',
                iconSize: [32, 32],
                iconAnchor: [16, 32]
            }),
            interactive: false
        }).addTo(map);

        polyline.bindTooltip(seg.name + " (" + seg.distance + "m)", { sticky: true });
        polyline.on("click", function() {
            window.location = "/test/" + seg.id;
        });

        for (var i = 0; i < latlngs.length; i++) {
            allPoints.push(latlngs[i]);
        }
    });

    if (allPoints.length >= 2) {
        var first = allPoints[0];
        var last = allPoints[allPoints.length - 1];
        L.circleMarker(first, {color: "#22c55e", radius: 6}).addTo(map).bindTooltip("Inicio del día");
        L.circleMarker(last, {color: "#ef4444", radius: 6}).addTo(map).bindTooltip("Fin del día");
        map.fitBounds(allPoints, {padding: [20, 20]});
    } else if (allPoints.length === 1) {
        map.setView(allPoints[0], 14);
    }

    setTimeout(function() { map.invalidateSize(); }, 200);
})();

function toggleMapaRegistros() {
    var el = document.getElementById("mapa-registros");
    var btn = document.getElementById("btn-mapa-registros");
    if (!el || !btn) return;
    el.classList.toggle("minimized");
    btn.textContent = el.classList.contains("minimized") ? "Mostrar" : "Minimizar";
}
