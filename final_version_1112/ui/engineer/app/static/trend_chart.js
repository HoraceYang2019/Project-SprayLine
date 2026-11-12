(function () {
    const NS = "http://www.w3.org/2000/svg";
    const COLORS = { ok: "#2e7d32", warn: "#ef6c00", bad: "#c62828" };

    function svgEl(name, attrs = {}, text = null) {
        const el = document.createElementNS(NS, name);
        Object.entries(attrs).forEach(([key, value]) => el.setAttribute(key, value));
        if (text !== null) el.textContent = text;
        return el;
    }

    function finiteValues(points) {
        return points.map(p => Number(p.value)).filter(Number.isFinite);
    }

    function rangeCandidates(reference) {
        const values = [];
        if (!reference) return values;
        const groups = [reference.normal, ...(reference.warning || []), ...(reference.fault || [])].filter(Boolean);
        groups.forEach(group => {
            ["min", "min_exclusive", "max", "max_exclusive"].forEach(key => {
                if (Number.isFinite(Number(group[key]))) values.push(Number(group[key]));
            });
        });
        return values;
    }

    window.renderTrendChart = function renderTrendChart(container, payload) {
        container.innerHTML = "";
        const points = payload.points || [];
        const values = finiteValues(points);
        if (!values.length) {
            container.textContent = "目前沒有可顯示的趨勢資料。";
            return;
        }

        const width = 760;
        const height = 270;
        const margin = { top: 24, right: 24, bottom: 48, left: 62 };
        const plotW = width - margin.left - margin.right;
        const plotH = height - margin.top - margin.bottom;
        const referenceValues = rangeCandidates(payload.threshold_reference);
        let minValue = Math.min(...values, ...referenceValues);
        let maxValue = Math.max(...values, ...referenceValues);
        let padding = (maxValue - minValue) * 0.14;
        if (!Number.isFinite(padding) || padding === 0) padding = Math.max(Math.abs(maxValue) * 0.1, 1);
        minValue -= padding;
        maxValue += padding;

        const svg = svgEl("svg", { viewBox: `0 0 ${width} ${height}`, class: "trend-chart", role: "img" });
        container.appendChild(svg);

        const xAt = index => margin.left + (points.length === 1 ? plotW / 2 : (index / (points.length - 1)) * plotW);
        const yAt = value => margin.top + ((maxValue - Number(value)) / (maxValue - minValue)) * plotH;

        svg.appendChild(svgEl("rect", { x: margin.left, y: margin.top, width: plotW, height: plotH, fill: "#fbfcfd", rx: 5 }));

        const normal = payload.threshold_reference?.normal;
        if (normal && Number.isFinite(Number(normal.min)) && Number.isFinite(Number(normal.max))) {
            const y1 = yAt(Number(normal.max));
            const y2 = yAt(Number(normal.min));
            svg.appendChild(svgEl("rect", {
                x: margin.left,
                y: Math.min(y1, y2),
                width: plotW,
                height: Math.abs(y2 - y1),
                fill: "rgba(46,125,50,0.10)"
            }));
            svg.appendChild(svgEl("text", {
                x: margin.left + 7,
                y: Math.min(y1, y2) + 15,
                fill: "#2e7d32",
                "font-size": 11,
                "font-weight": 700
            }, `正常範圍 ${normal.min}～${normal.max} ${payload.unit || ""}`));
        }

        for (let i = 0; i <= 4; i++) {
            const y = margin.top + (i / 4) * plotH;
            const value = maxValue - (i / 4) * (maxValue - minValue);
            svg.appendChild(svgEl("line", { x1: margin.left, y1: y, x2: margin.left + plotW, y2: y, stroke: "#dfe5e8", "stroke-width": 1 }));
            svg.appendChild(svgEl("text", { x: margin.left - 9, y: y + 4, "text-anchor": "end", fill: "#607d8b", "font-size": 11 }, value.toFixed(value < 1 ? 3 : 1)));
        }

        let selectedIndex = points.findIndex(point => point.selected_snapshot === true);
        const selectedSlider = Number(payload.selected_snapshot?.slider_value);
        if (selectedIndex < 0 && Number.isFinite(selectedSlider)) {
            selectedIndex = points.findIndex(point => Number(point.slider_value) === selectedSlider);
            if (selectedIndex >= 0) points[selectedIndex].selected_snapshot = true;
        }

        const currentIndex = points.findIndex(point => point.time_type === "current" || Number(point.slider_value) === 0);
        if (currentIndex >= 0) {
            const nowX = xAt(currentIndex);
            svg.appendChild(svgEl("line", { x1: nowX, y1: margin.top, x2: nowX, y2: margin.top + plotH, stroke: "#263238", "stroke-width": 2, "stroke-dasharray": "4 4" }));
            svg.appendChild(svgEl("text", { x: nowX, y: margin.top - 7, "text-anchor": "middle", fill: "#263238", "font-size": 11, "font-weight": 800 }, "現在"));
        }

        if (selectedIndex >= 0) {
            const selectedX = xAt(selectedIndex);
            const selectedLabel = payload.selected_snapshot?.display_label || "卡片時間點";
            svg.appendChild(svgEl("line", { x1: selectedX, y1: margin.top, x2: selectedX, y2: margin.top + plotH, stroke: "#1565c0", "stroke-width": 3, "stroke-dasharray": "3 5" }));
            svg.appendChild(svgEl("text", { x: selectedX, y: margin.top + 13, "text-anchor": "middle", fill: "#1565c0", "font-size": 11, "font-weight": 900 }, selectedLabel));
        }

        function pathFor(indices) {
            return indices.map((index, order) => `${order === 0 ? "M" : "L"}${xAt(index)},${yAt(points[index].value)}`).join(" ");
        }

        const pastCurrent = points.map((p, i) => p.time_type !== "future" ? i : -1).filter(i => i >= 0);
        const future = points.map((p, i) => p.time_type === "future" || (currentIndex >= 0 && i === currentIndex) ? i : -1).filter(i => i >= 0);
        if (pastCurrent.length > 1) svg.appendChild(svgEl("path", { d: pathFor(pastCurrent), fill: "none", stroke: "#455a64", "stroke-width": 3, "stroke-linejoin": "round", "stroke-linecap": "round" }));
        if (future.length > 1) svg.appendChild(svgEl("path", { d: pathFor(future), fill: "none", stroke: "#6a1b9a", "stroke-width": 3, "stroke-dasharray": "7 5", "stroke-linejoin": "round", "stroke-linecap": "round" }));

        points.forEach((point, index) => {
            const isSelected = point.selected_snapshot === true;
            if (isSelected) {
                svg.appendChild(svgEl("circle", {
                    cx: xAt(index), cy: yAt(point.value), r: 8.5,
                    fill: "none", stroke: "#1565c0", "stroke-width": 2.5
                }));
            }
            const dot = svgEl("circle", {
                cx: xAt(index), cy: yAt(point.value),
                r: isSelected ? 5.5 : (point.time_type === "current" ? 5 : 3.3),
                fill: COLORS[point.level] || "#607d8b", stroke: "white", "stroke-width": 1.5
            });
            const selectedText = isSelected ? "｜與上方卡片相同數值" : "";
            const title = svgEl("title", {}, `${new Date(point.timestamp).toLocaleString("zh-TW", {hour12:false})}｜${point.value} ${payload.unit || ""}｜${point.level === "bad" ? "異常" : point.level === "warn" ? "注意" : "正常"}${selectedText}`);
            dot.appendChild(title);
            svg.appendChild(dot);
        });

        const xLabels = [0, Math.floor((points.length - 1) * 0.25), currentIndex >= 0 ? currentIndex : Math.floor((points.length - 1) * 0.75), points.length - 1];
        [...new Set(xLabels)].forEach(index => {
            const date = new Date(points[index].timestamp);
            const label = points[index].time_type === "current" ? "現在" : date.toLocaleTimeString("zh-TW", { hour: "2-digit", minute: "2-digit", hour12: false });
            svg.appendChild(svgEl("text", { x: xAt(index), y: margin.top + plotH + 22, "text-anchor": "middle", fill: "#607d8b", "font-size": 11 }, label));
        });

        svg.appendChild(svgEl("text", { x: width / 2, y: height - 7, "text-anchor": "middle", fill: "#455a64", "font-size": 12, "font-weight": 700 }, payload.axis_caption || "過去 6 小時　→　現在　→　未來 2 小時"));
        svg.appendChild(svgEl("text", { x: 15, y: height / 2, transform: `rotate(-90 15 ${height / 2})`, "text-anchor": "middle", fill: "#455a64", "font-size": 12, "font-weight": 700 }, `${payload.value_label} (${payload.unit || ""})`));
    };
})();
