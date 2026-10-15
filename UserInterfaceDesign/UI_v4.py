from pathlib import Path

html_code = r"""
<!DOCTYPE html>
<html lang="zh-Hant">
<head>
    <meta charset="UTF-8">
    <title>噴塗產線監控系統</title>

    <style>
        body {
            margin: 0;
            font-family: "Microsoft JhengHei", Arial, sans-serif;
            background: #f4f6f8;
            color: #222;
        }

        .header {
            background: #263238;
            color: white;
            padding: 20px 30px;
        }

        .header h1 {
            margin: 0;
            font-size: 28px;
        }

        .header p {
            margin: 8px 0 0;
            color: #cfd8dc;
        }

        .main {
            padding: 22px;
            max-width: 1600px;
            margin: auto;
        }

        .summary {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 15px;
            margin-bottom: 22px;
        }

        .summary-card {
            background: white;
            border-radius: 14px;
            padding: 18px;
            text-align: center;
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        }

        .summary-card h3 {
            margin: 0;
            font-size: 15px;
            color: #666;
        }

        .summary-card .number {
            margin-top: 10px;
            font-size: 30px;
            font-weight: bold;
        }

        .station-area {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(430px, 1fr));
            gap: 22px;
        }

        .station-card {
            background: white;
            border-radius: 18px;
            padding: 20px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            border-top: 10px solid #aaa;
            transition: 0.3s;
        }

        .station-title {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 12px;
        }

        .station-title h2 {
            margin: 0;
            font-size: 24px;
        }

        .station-title p {
            margin: 6px 0 0;
            color: #666;
        }

        .status-badge {
            padding: 8px 14px;
            border-radius: 20px;
            color: white;
            font-weight: bold;
            font-size: 14px;
            white-space: nowrap;
        }

        .section-title {
            font-weight: bold;
            margin: 16px 0 10px;
            color: #37474f;
        }

        .component-wrap {
            margin: 18px 0 10px;
            padding: 14px;
            border-radius: 16px;
            background: #f1f3f4;
            box-sizing: border-box;
        }

        .component-overview {
            width: 100%;
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
        }

        .component-mini {
            min-height: 118px;
            border-radius: 14px;
            padding: 10px 8px;
            text-align: center;
            background: white;
            border: 1px solid #dfe6e9;
            border-top: 6px solid #90a4ae;
            box-shadow: 0 2px 6px rgba(0,0,0,0.04);
            box-sizing: border-box;
            cursor: pointer;
            transition: 0.2s;
        }

        .component-mini:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.12);
        }

        .component-icon {
            width: 32px;
            height: 32px;
            margin: 0 auto 6px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
            background: #eef3f6;
        }

        .component-name {
            font-size: 14px;
            font-weight: bold;
            line-height: 1.2;
        }

        .component-en {
            font-size: 11px;
            color: #777;
            margin-top: 2px;
        }

        .component-value {
            margin-top: 5px;
            font-size: 12px;
            color: #555;
        }

        .component-status {
            display: inline-block;
            margin-top: 6px;
            padding: 3px 9px;
            border-radius: 12px;
            color: white;
            font-size: 12px;
            font-weight: bold;
        }

        .component-hint {
            margin-top: 5px;
            font-size: 11px;
            color: #777;
        }

        .component-mini.ok {
            border-top-color: #2e7d32;
            background: #f1faf3;
        }

        .component-mini.ok .component-status {
            background: #2e7d32;
        }

        .component-mini.warn {
            border-top-color: #ef6c00;
            background: #fff8ef;
        }

        .component-mini.warn .component-status {
            background: #ef6c00;
        }

        .component-mini.bad {
            border-top-color: #c62828;
            background: #fff2f2;
        }

        .component-mini.bad .component-status {
            background: #c62828;
        }

        .component-mini.neutral {
            border-top-color: #1976d2;
            background: #f1f7ff;
        }

        .component-mini.neutral .component-status {
            background: #1976d2;
        }

        .action-row {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            margin-top: 14px;
        }

        .toggle-btn {
            border: none;
            border-radius: 18px;
            padding: 9px 14px;
            cursor: pointer;
            background: #eceff1;
            color: #263238;
            font-weight: bold;
        }

        .toggle-btn:hover {
            background: #cfd8dc;
        }

        .toggle-btn.danger {
            background: #c62828;
            color: white;
        }

        .toggle-btn.warn {
            background: #ef6c00;
            color: white;
        }

        .toggle-btn.info {
            background: #2e7d32;
            color: white;
        }

        .toggle-btn.info:hover {
            background: #1b5e20;
        }

        .toggle-btn.active-process {
            background: #1976d2;
            color: white;
            box-shadow: 0 0 0 3px rgba(25,118,210,0.16);
        }

        .toggle-btn.active-image {
            background: #00897b;
            color: white;
            box-shadow: 0 0 0 3px rgba(0,137,123,0.22);
        }

        .toggle-btn.active-image:hover {
            background: #00796b;
        }

        .toggle-btn.active-fault {
            box-shadow: 0 0 0 3px rgba(198,40,40,0.14);
        }

        .toggle-btn.info.active-fault {
            box-shadow: 0 0 0 3px rgba(46,125,50,0.18);
        }

        .toggle-btn.warn.active-fault {
            box-shadow: 0 0 0 3px rgba(239,108,0,0.18);
        }

        .toggle-btn.danger.active-fault {
            box-shadow: 0 0 0 3px rgba(198,40,40,0.18);
        }

        .fault-detail-panel {
            display: none;
            margin-top: 14px;
            border-radius: 14px;
            background: #ffffff;
            border-left: none;
            padding: 16px 18px;
            line-height: 1.85;
        }

        .fault-detail-panel h4 {
            margin: 0 0 14px;
            color: #263238;
            font-weight: 900;
            font-size: 20px;
            letter-spacing: 0.3px;
        }

        .fault-item {
            padding: 14px 0;
            border-top: 1px solid #f0d6d6;
        }

        .fault-item:first-child {
            border-top: none;
            padding-top: 0;
        }

        .fault-line {
            margin: 7px 0;
        }

        .fault-label {
            display: inline-block;
            min-width: 96px;
            font-weight: 900;
            font-size: 18px;
            color: #111111;
            margin-right: 8px;
            letter-spacing: 0.3px;
        }

        .warn-detail {
            background: #fff8ef;
            border-left-color: #ef6c00;
        }

        .warn-detail h4 {
            color: #ef6c00;
        }

        .warn-detail .fault-item {
            border-top-color: #f5d6b8;
        }

        .mixed-detail {
            background: #ffffff;
            border-left: none;
            padding-left: 24px;
        }

        .mixed-detail h4 {
            color: #263238;
        }

        .issue-item {
            margin: 12px 0;
            padding: 14px 16px;
            border-top: none;
            border-radius: 12px;
        }

        .issue-item.warn-item {
            background: #fff8ef;
            border-left: 6px solid #ef6c00;
        }

        .issue-item.bad-item {
            background: #fff8f8;
            border-left: 6px solid #c62828;
        }

        .issue-item.ok-item {
            background: #f1faf3;
            border-left: 6px solid #2e7d32;
        }

        .issue-status {
            font-weight: 900;
        }

        .warn-text {
            color: #ef6c00;
        }

        .bad-text {
            color: #c62828;
        }

        .ok-text {
            color: #2e7d32;
        }

        .normal-detail {
            background: #f1faf3;
            border-left-color: #2e7d32;
        }

        .normal-detail h4 {
            color: #2e7d32;
        }

        .process-panel,
        .spray-image-box {
            display: none;
            margin-top: 12px;
        }

        .process-panel {
            background: #f1f7ff;
            border-left: 6px solid #1976d2;
            border-radius: 14px;
            padding: 14px;
        }

        .process-panel .section-title {
            margin-top: 0;
            color: #1565c0;
        }

        .metric-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
        }

        .metric {
            background: #fafafa;
            border-radius: 10px;
            padding: 10px;
            border: 1px solid #eee;
        }

        .metric span {
            display: block;
            color: #666;
            font-size: 13px;
        }

        .metric strong {
            display: block;
            margin-top: 5px;
            font-size: 18px;
        }

        .spray-image-inner {
            background: #f1f3f4;
            border-radius: 14px;
            padding: 12px;
            border: 1px solid transparent;
            border-left: 6px solid transparent;
        }

        .spray-image-inner.spray-ok {
            background: #f1faf3;
            border-color: #c8e6c9;
            border-left-color: #2e7d32;
        }

        .spray-image-inner.spray-warn {
            background: #fff8ef;
            border-color: #f5d6b8;
            border-left-color: #ef6c00;
        }

        .spray-image-inner.spray-bad {
            background: #fff8f8;
            border-color: #f0c4c4;
            border-left-color: #c62828;
        }

        .spray-svg {
            width: 100%;
            height: 230px;
            display: block;
        }

        .spray-image-note {
            font-size: 13px;
            color: #666;
            margin-top: 8px;
            line-height: 1.6;
        }

        .timeline-panel {
            margin-top: 24px;
            background: white;
            border-radius: 18px;
            padding: 22px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        }

        .timeline-top {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 15px;
            flex-wrap: wrap;
        }

        .mode-buttons button {
            border: none;
            padding: 10px 15px;
            border-radius: 20px;
            margin-right: 8px;
            margin-bottom: 8px;
            cursor: pointer;
            background: #eceff1;
            font-weight: bold;
        }

        .mode-buttons button.active {
            background: #263238;
            color: white;
        }

        .live-badge {
            display: inline-block;
            margin-left: 8px;
            padding: 5px 10px;
            border-radius: 16px;
            background: #2e7d32;
            color: white;
            font-size: 13px;
            font-weight: bold;
        }

        .pause-badge {
            display: inline-block;
            margin-left: 8px;
            padding: 5px 10px;
            border-radius: 16px;
            background: #ef6c00;
            color: white;
            font-size: 13px;
            font-weight: bold;
        }

        .time-chips {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
            margin-top: 18px;
        }

        .time-chip {
            border-radius: 14px;
            background: #f7f9fa;
            border: 1px solid #e0e0e0;
            padding: 12px;
            text-align: center;
            color: #546e7a;
            font-weight: bold;
        }

        .time-chip.active {
            background: #263238;
            color: white;
        }

        .slider-area {
            margin-top: 18px;
        }

        input[type="range"] {
            width: 100%;
        }

        .time-labels {
            position: relative;
            height: 22px;
            font-size: 13px;
            color: #666;
            margin-top: 5px;
        }

        .time-labels span {
            position: absolute;
            white-space: nowrap;
        }

        .time-labels .left-label {
            left: 0;
        }

        .time-labels .right-label {
            right: 0;
        }

        .time-labels.time-mode .now-label {
            left: 60%;
            transform: translateX(-50%);
        }

        .time-labels.batch-mode .now-label {
            left: 50%;
            transform: translateX(-50%);
        }

        .selected-time {
            margin-top: 12px;
            font-size: 20px;
            font-weight: bold;
            color: #263238;
        }

        .timeline-result {
            margin-top: 16px;
            background: #f7f7f7;
            padding: 14px;
            border-radius: 12px;
            line-height: 1.8;
        }

        .future-warning {
            color: #c62828;
            font-weight: bold;
        }

        .history-note {
            color: #1565c0;
            font-weight: bold;
        }

        .running {
            border-top-color: #2e7d32;
        }

        .running .status-badge {
            background: #2e7d32;
        }

        .standby {
            border-top-color: #1976d2;
        }

        .standby .status-badge {
            background: #1976d2;
        }

        .stop {
            border-top-color: #c62828;
        }

        .stop .status-badge {
            background: #c62828;
        }

        .maintenance {
            border-top-color: #ef6c00;
        }

        .maintenance .status-badge {
            background: #ef6c00;
        }

        .alarm {
            border-top-color: #b71c1c;
            animation: alarmFlash 1s infinite;
        }

        .alarm .status-badge {
            background: #b71c1c;
        }

        @keyframes alarmFlash {
            0% { box-shadow: 0 0 5px rgba(183,28,28,0.3); }
            50% { box-shadow: 0 0 25px rgba(183,28,28,0.7); }
            100% { box-shadow: 0 0 5px rgba(183,28,28,0.3); }
        }

        @media (max-width: 900px) {
            .component-overview,
            .metric-grid,
            .time-chips {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>

<body>

    <div class="header">
        <h1>噴塗產線監控系統</h1>
        <p>SprayingLineMonitoringSystem</p>
        <p id="updateTime">最後更新時間：</p>
    </div>

    <div class="main">

        <div class="summary">
            <div class="summary-card">
                <h3>總站數 TotalStations</h3>
                <div class="number" id="totalCount">3</div>
            </div>

            <div class="summary-card">
                <h3>正常 Normal</h3>
                <div class="number" id="normalCount">0</div>
            </div>

            <div class="summary-card">
                <h3>注意 Warning</h3>
                <div class="number" id="warningCount">0</div>
            </div>

            <div class="summary-card">
                <h3>預測風險 PredictRisk</h3>
                <div class="number" id="riskCount">0</div>
            </div>
        </div>

        <div class="station-area" id="stationArea"></div>

        <div class="timeline-panel">
            <div class="timeline-top">
                <div>
                    <h2>
                        時間序列檢視 TimeSeriesViewer
                        <span id="liveStatusBadge" class="live-badge">即時更新中</span>
                    </h2>
                    <p>可切換現在、過去與未來預測；往左查看歷史資料，往右查看未來風險。</p>
                </div>

                <div class="mode-buttons">
                    <button id="timeModeBtn" class="active" onclick="setMode('time')">時間模式 TimeMode</button>
                    <button id="batchModeBtn" onclick="setMode('batch')">批次模式 BatchMode</button>
                    <button onclick="backToLive()">回到即時 BackToLive</button>
                </div>
            </div>

            <div class="time-chips">
                <div class="time-chip" id="pastChip">過去 Past</div>
                <div class="time-chip active" id="nowChip">現在 Now</div>
                <div class="time-chip" id="futureChip">未來 Future</div>
            </div>

            <div class="slider-area">
                <input type="range" id="timeSlider" min="-6" max="4" step="1" value="0" oninput="handleSliderChange()">

                <div class="time-labels time-mode" id="sliderLabels">
                    <span class="left-label">過去6小時</span>
                    <span class="now-label">現在</span>
                    <span class="right-label">未來2小時</span>
                </div>

                <div class="selected-time" id="selectedTimeText">
                    目前時間點：現在
                </div>
            </div>

            <div class="timeline-result" id="timelineResult">
                資料載入中...
            </div>
        </div>

    </div>

    <script>
        let currentMode = "time";
        let autoUpdate = true;
        let openedFaultPanels = new Map();
        let openedProcessPanels = new Set();
        let openedImagePanels = new Set();
        let latestDiagnosis = {};

        const baseStations = [
            {
                id: "M1",
                name: "底漆站",
                englishName: "PrimerStation",
                recipe: "Primer_A",
                basePressure: 2.5,
                baseWidth: 120,
                baseTemp: 28,
                baseAvailability: 95,
                baseMaintainability: 92,
                baseClog: 12,
                baseQuality: 96,
                baseUtilization: 78,
                baseCycle: 42
            },
            {
                id: "M2",
                name: "面漆站",
                englishName: "TopcoatStation",
                recipe: "Topcoat_B",
                basePressure: 2.1,
                baseWidth: 100,
                baseTemp: 27,
                baseAvailability: 88,
                baseMaintainability: 86,
                baseClog: 25,
                baseQuality: 91,
                baseUtilization: 72,
                baseCycle: 46
            },
            {
                id: "M3",
                name: "金漆站",
                englishName: "GoldPaintStation",
                recipe: "Gold_C",
                basePressure: 1.7,
                baseWidth: 82,
                baseTemp: 26,
                baseAvailability: 72,
                baseMaintainability: 65,
                baseClog: 55,
                baseQuality: 82,
                baseUtilization: 60,
                baseCycle: 55
            }
        ];

        const stateMap = {
            "Running": {
                text: "運行中",
                className: "running"
            },
            "Standby": {
                text: "待機",
                className: "standby"
            },
            "Stop": {
                text: "停止",
                className: "stop"
            },
            "Maintenance": {
                text: "維護",
                className: "maintenance"
            },
            "Alarm": {
                text: "異常",
                className: "alarm"
            }
        };

        function clamp(value, min, max) {
            return Math.max(min, Math.min(max, value));
        }

        function getSliderValue() {
            return Number(document.getElementById("timeSlider").value);
        }

        function buildStationData() {
            const offset = getSliderValue();
            const liveWave = Math.sin(Date.now() / 1500);

            return baseStations.map((s, index) => {
                let factor;

                if (currentMode === "time") {
                    if (offset > 0) {
                        factor = offset * 0.5;
                    } else {
                        factor = offset;
                    }
                } else {
                    factor = offset * 0.35;
                }

                let clog = s.baseClog + factor * (index + 1) * 7;
                let availability = s.baseAvailability - Math.max(0, factor) * (index + 1) * 4;
                let maintainability = s.baseMaintainability - Math.max(0, factor) * (index + 1) * 5;
                let quality = s.baseQuality - Math.max(0, factor) * (index + 1) * 3;
                let cycle = s.baseCycle + Math.max(0, factor) * (index + 1) * 2;

                if (offset === 0) {
                    clog = s.baseClog + liveWave * 3 + index * 2;
                    availability = s.baseAvailability + liveWave * 2;
                    maintainability = s.baseMaintainability + liveWave * 2;
                    quality = s.baseQuality + liveWave * 1.5;
                    cycle = s.baseCycle + liveWave * 1.5;
                }

                if (offset < 0) {
                    clog = s.baseClog + Math.sin(offset + index) * 6;
                    availability = s.baseAvailability + Math.sin(offset + index) * 3;
                    maintainability = s.baseMaintainability + Math.cos(offset + index) * 3;
                    quality = s.baseQuality + Math.sin(offset + index) * 2;
                    cycle = s.baseCycle + Math.cos(offset + index) * 2;
                }

                clog = clamp(Math.round(clog), 0, 100);
                availability = clamp(Math.round(availability), 0, 100);
                maintainability = clamp(Math.round(maintainability), 0, 100);
                quality = clamp(Math.round(quality), 0, 100);
                cycle = Math.round(cycle);

                let pressure = s.basePressure - clog * 0.006;
                let sprayWidth = s.baseWidth - clog * 0.45;
                let temp = s.baseTemp + Math.max(0, factor) * 0.4;

                pressure = Number(pressure.toFixed(1));
                sprayWidth = Math.round(sprayWidth);

                const components = getComponents({
                    ...s,
                    pressure,
                    sprayWidth,
                    temperature: temp.toFixed(1),
                    availability,
                    maintainability,
                    clog,
                    quality,
                    cycle,
                    utilization: clamp(Math.round(s.baseUtilization - Math.max(0, factor) * 2), 0, 100)
                });

                const badCount = components.filter(c => c.level === "bad").length;
                const warnCount = components.filter(c => c.level === "warn").length;

                let overall = "Running";
                let riskText = "低風險";

                if (badCount > 0) {
                    overall = "Alarm";
                    riskText = "高風險";
                } else if (warnCount > 0) {
                    overall = "Maintenance";
                    riskText = "中風險";
                } else if (availability < 80) {
                    overall = "Standby";
                    riskText = "低至中風險";
                }

                return {
                    ...s,
                    overall,
                    riskText,
                    pressure: pressure.toFixed(1),
                    sprayWidth,
                    temperature: temp.toFixed(1),
                    availability,
                    maintainability,
                    clog,
                    quality,
                    utilization: clamp(Math.round(s.baseUtilization - Math.max(0, factor) * 2), 0, 100),
                    cycle
                };
            });
        }

        function partClass(value, type) {
            if (type === "clog") {
                if (value >= 75) return "bad";
                if (value >= 50) return "warn";
                return "ok";
            }

            if (type === "percent") {
                if (value < 60) return "bad";
                if (value < 80) return "warn";
                return "ok";
            }

            return "neutral";
        }

        function pressureClass(value) {
            const pressure = Number(value);

            if (pressure < 1.5) return "bad";
            if (pressure < 2.0) return "warn";
            return "ok";
        }

        function sprayWidthClass(value) {
            const width = Number(value);

            if (width < 100 || width > 140) return "bad";
            if (width < 110 || width > 130) return "warn";
            return "ok";
        }

        function sprayWidthIssue(width) {
            const w = Number(width);

            if (w < 110) {
                return "噴幅低於目標範圍，可能造成塗布範圍不足、邊緣漏噴或膜厚集中。";
            }

            if (w > 130) {
                return "噴幅高於目標範圍，可能造成噴塗過度擴散、邊緣飛漆或膜厚不足。";
            }

            return "噴幅位於目標範圍內，目前狀態穩定。";
        }

        function sprayWidthReason(width) {
            const w = Number(width);

            if (w < 110) {
                return "可能原因為噴嘴距離過近、空壓機壓力偏低、塗料流量不足或噴嘴局部堵塞。";
            }

            if (w > 130) {
                return "可能原因為噴嘴距離過遠、空壓機壓力偏高、塗料流量過大或噴幅調整過大。";
            }

            return "目前噴幅正常，維持原設定並定期確認影像即可。";
        }

        function sprayWidthSolution(width) {
            const w = Number(width);

            if (w < 110) {
                return "建議檢查噴嘴是否堵塞，並適度調整噴嘴距離、空壓機壓力與塗料流量，讓噴幅回到 110~130mm。";
            }

            if (w > 130) {
                return "建議確認噴嘴距離是否過遠，並降低過大的壓力或流量設定，重新校正噴幅至 110~130mm。";
            }

            return "維持目前參數，持續監控即可。";
        }


        function statusText(level) {
            if (level === "ok") return "正常";
            if (level === "warn") return "注意";
            if (level === "bad") return "異常";
            return "監控";
        }

        function getComponents(station) {
            const armLevel = partClass(station.availability, "percent");
            const nozzleLevel = partClass(station.clog, "clog");
            const airLevel = pressureClass(station.pressure);
            const widthLevel = sprayWidthClass(station.sprayWidth);
            const filterLevel = partClass(station.maintainability, "percent");
            const qualityLevel = partClass(station.quality, "percent");

            return [
                {
                    key: "arm",
                    icon: "🦾",
                    name: "機械手臂",
                    en: "RobotArm",
                    level: armLevel,
                    value: `可用度 ${station.availability}%`,
                    issue: "機械手臂可用度下降，可能影響噴塗路徑穩定性。",
                    reason: "可能原因為關節負載過高、馬達溫升、定位偏移或保養週期接近。",
                    solution: "建議檢查手臂關節、馬達狀態與座標校正，必要時安排保養。"
                },
                {
                    key: "nozzle",
                    icon: "💧",
                    name: "噴嘴",
                    en: "Nozzle",
                    level: nozzleLevel,
                    value: `堵塞率 ${station.clog}%`,
                    issue: "噴嘴堵塞率偏高，可能造成噴塗量不足或噴幅不均。",
                    reason: "可能原因為塗料顆粒、黏度過高、乾漆殘留或清潔不足。",
                    solution: "建議清潔噴嘴、檢查塗料黏度，並確認前段過濾是否正常。"
                },
                {
                    key: "air",
                    icon: "⚙️",
                    name: "空壓機",
                    en: "AirCompressor",
                    level: airLevel,
                    value: `壓力 ${station.pressure} bar`,
                    issue: "空壓機壓力偏低，可能導致霧化不足或噴塗不均。",
                    reason: "可能原因為空壓機輸出不足、管路漏氣、調壓閥設定不當或濾水杯堵塞。",
                    solution: "建議檢查空壓機輸出、管線接頭、調壓閥與空氣過濾器。"
                },
                {
                    key: "width",
                    icon: "↔️",
                    name: "噴幅",
                    en: "SprayWidth",
                    level: widthLevel,
                    value: `噴幅 ${station.sprayWidth} mm`,
                    issue: sprayWidthIssue(station.sprayWidth),
                    reason: sprayWidthReason(station.sprayWidth),
                    solution: sprayWidthSolution(station.sprayWidth)
                },
                {
                    key: "filter",
                    icon: "🧽",
                    name: "濾網",
                    en: "FilterMesh",
                    level: filterLevel,
                    value: `維護性 ${station.maintainability}%`,
                    issue: "濾網維護性偏低，可能影響塗料流量與噴嘴堵塞率。",
                    reason: "可能原因為濾網累積雜質、塗料顆粒過多或清潔週期過長。",
                    solution: "建議清潔或更換濾網，並縮短檢查週期。"
                },
                {
                    key: "quality",
                    icon: "📏",
                    name: "品質",
                    en: "Quality",
                    level: qualityLevel,
                    value: `膜厚穩定度 ${station.quality}%`,
                    issue: "品質穩定度下降，可能代表膜厚變異增加。",
                    reason: "可能原因為噴塗速度、壓力、噴幅或塗料條件不穩。",
                    solution: "建議檢查配方、噴塗速度、壓力與噴幅影像，確認膜厚是否需重新校正。"
                }
            ];
        }

        function componentOverview(station) {
            const components = getComponents(station);
            latestDiagnosis[station.id] = {
                station,
                components,
                issues: components.filter(component => component.level !== "ok")
            };

            return `
                <div class="component-wrap">
                    <div class="section-title">零件狀態 PartStatus</div>
                    <div class="component-overview">
                        ${components.map(component => `
                            <div class="component-mini ${component.level}" onclick="openComponentDetail('${station.id}', '${component.key}')">
                                <div class="component-icon">${component.icon}</div>
                                <div class="component-name">${component.name}</div>
                                <div class="component-en">${component.en}</div>
                                <div class="component-value">${component.value}</div>
                                <div class="component-status">${statusText(component.level)}</div>
                                <div class="component-hint">${component.level === "ok" ? "狀態穩定" : "點擊查看原因"}</div>
                            </div>
                        `).join("")}
                    </div>
                </div>
            `;
        }

        function sprayWidthImage(station) {
            const widthValue = Number(station.sprayWidth);
            const statusClass = sprayWidthClass(widthValue);
            const statusLabel = statusText(statusClass);

            let statusColor = "#2e7d32";
            if (statusClass === "warn") {
                statusColor = "#ef6c00";
            } else if (statusClass === "bad") {
                statusColor = "#c62828";
            }

            const minOk = 110;
            const maxOk = 130;
            const displayWidth = clamp(widthValue, 70, 145);
            const halfWidth = displayWidth * 0.65;
            const leftX = 180 - halfWidth;
            const rightX = 180 + halfWidth;

            return `
                <svg viewBox="0 0 360 230" class="spray-svg">
                    <rect x="0" y="0" width="360" height="230" rx="16" fill="#f7f9fa"/>

                    <text x="20" y="28" font-size="14" font-weight="bold" fill="#263238">
                        噴幅影像 SprayWidthImage
                    </text>

                    <rect x="286" y="12" width="52" height="24" rx="12" fill="${statusColor}"/>
                    <text x="312" y="29" text-anchor="middle" font-size="12" font-weight="bold" fill="#ffffff">
                        ${statusLabel}
                    </text>

                    <rect x="18" y="45" width="324" height="160" rx="12" fill="#ffffff" stroke="#dfe6e9"/>

                    <rect x="164" y="60" width="32" height="20" rx="5" fill="#455a64"/>
                    <polygon points="180,80 170,96 190,96" fill="#455a64"/>

                    <polygon points="180,96 ${leftX},165 ${rightX},165"
                            fill="rgba(25,118,210,0.18)"
                            stroke="${statusColor}"
                            stroke-width="3"/>

                    <rect x="108" y="145" width="144" height="18" rx="8"
                        fill="rgba(46,125,50,0.10)"
                        stroke="#2e7d32"
                        stroke-dasharray="5 4"/>
                    <text x="180" y="139" text-anchor="middle" font-size="12" fill="#2e7d32">
                        目標範圍 ${minOk}~${maxOk}mm
                    </text>

                    <line x1="${leftX}" y1="164" x2="${leftX}" y2="180" stroke="${statusColor}" stroke-width="3"/>
                    <line x1="${rightX}" y1="164" x2="${rightX}" y2="180" stroke="${statusColor}" stroke-width="3"/>
                    <line x1="${leftX}" y1="176" x2="${rightX}" y2="176" stroke="#263238" stroke-width="2"/>

                    <text x="180" y="195" text-anchor="middle" font-size="14" font-weight="bold" fill="#263238">
                        目前噴幅：${widthValue}mm
                    </text>
                </svg>

                <div class="spray-image-note">
                    平常此區塊收起；需要確認噴幅異常時，再展開查看影像、目標範圍與實際噴幅。
                </div>
            `;
        }

        function renderStations(stationData) {
            const stationArea = document.getElementById("stationArea");
            stationArea.innerHTML = "";
            latestDiagnosis = {};

            stationData.forEach(station => {
                const stateInfo = stateMap[station.overall];
                const components = getComponents(station);
                const issues = components.filter(component => component.level !== "ok");
                const hasBad = issues.some(component => component.level === "bad");

                const card = document.createElement("div");
                card.className = `station-card ${stateInfo.className}`;

                card.innerHTML = `
                    <div class="station-title">
                        <div>
                            <h2>${station.name}</h2>
                            <p>${station.englishName}</p>
                        </div>
                        <div class="status-badge">${stateInfo.text}</div>
                    </div>

                    ${componentOverview(station)}

                    <div class="action-row">
                        <button id="fault-btn-${station.id}" class="toggle-btn ${hasBad ? "danger" : issues.length > 0 ? "warn" : "info"}" onclick="toggleAllIssues('${station.id}')">
                            ${issues.length > 0 ? "查看異常原因與改善 FaultDetail" : "零件正常 NoFault"}
                        </button>

                        <button id="process-btn-${station.id}" class="toggle-btn" onclick="toggleProcessPanel('${station.id}')">
                            製程參數 ProcessParameters
                        </button>

                        <button id="image-btn-${station.id}" class="toggle-btn" onclick="toggleImagePanel('${station.id}')">
                            噴幅影像 SprayWidthImage
                        </button>
                    </div>

                    <div class="fault-detail-panel" id="fault-${station.id}"></div>

                    <div class="process-panel" id="process-${station.id}">
                        <div class="section-title">製程參數 ProcessParameters</div>

                        <div class="metric-grid">
                            <div class="metric">
                                <span>配方 Recipe</span>
                                <strong>${station.recipe}</strong>
                            </div>

                            <div class="metric">
                                <span>溫度 Temperature</span>
                                <strong>${station.temperature}°C</strong>
                            </div>

                            <div class="metric">
                                <span>利用率 Utilization</span>
                                <strong>${station.utilization}%</strong>
                            </div>

                            <div class="metric">
                                <span>週期時間 CycleTime</span>
                                <strong>${station.cycle}sec</strong>
                            </div>
                        </div>
                    </div>

                    <div class="spray-image-box" id="image-${station.id}">
                        <div class="section-title">噴幅影像 SprayWidthImage</div>
                        <div class="spray-image-inner spray-${sprayWidthClass(station.sprayWidth)}">
                            ${sprayWidthImage(station)}
                        </div>
                    </div>
                `;

                stationArea.appendChild(card);
            });

            restoreOpenedPanels();
        }

        function restoreOpenedPanels() {
            openedProcessPanels.forEach(stationId => {
                const panel = document.getElementById(`process-${stationId}`);
                const btn = document.getElementById(`process-btn-${stationId}`);

                if (panel) {
                    panel.style.display = "block";
                }

                if (btn) {
                    btn.classList.add("active-process");
                }
            });

            openedImagePanels.forEach(stationId => {
                const panel = document.getElementById(`image-${stationId}`);
                const btn = document.getElementById(`image-btn-${stationId}`);

                if (panel) {
                    panel.style.display = "block";
                }

                if (btn) {
                    btn.classList.add("active-image");
                }
            });

            openedFaultPanels.forEach((componentKey, stationId) => {
                if (componentKey === "ALL") {
                    renderAllIssues(stationId);
                } else {
                    renderComponentIssue(stationId, componentKey);
                }
            });
        }

        function toggleProcessPanel(stationId) {
            const panel = document.getElementById(`process-${stationId}`);
            const btn = document.getElementById(`process-btn-${stationId}`);

            if (!panel) return;

            if (panel.style.display === "block") {
                panel.style.display = "none";
                openedProcessPanels.delete(stationId);

                if (btn) {
                    btn.classList.remove("active-process");
                }
            } else {
                panel.style.display = "block";
                openedProcessPanels.add(stationId);

                if (btn) {
                    btn.classList.add("active-process");
                }
            }
        }

        function toggleImagePanel(stationId) {
            const panel = document.getElementById(`image-${stationId}`);
            const btn = document.getElementById(`image-btn-${stationId}`);

            if (!panel) return;

            if (panel.style.display === "block") {
                panel.style.display = "none";
                openedImagePanels.delete(stationId);

                if (btn) {
                    btn.classList.remove("active-image");
                }
            } else {
                panel.style.display = "block";
                openedImagePanels.add(stationId);

                if (btn) {
                    btn.classList.add("active-image");
                }
            }
        }

        function openComponentDetail(stationId, componentKey) {
            openedFaultPanels.set(stationId, componentKey);
            renderComponentIssue(stationId, componentKey);
        }

        function toggleAllIssues(stationId) {
            if (openedFaultPanels.get(stationId) === "ALL") {
                closeFaultDetail(stationId);
                return;
            }

            openedFaultPanels.set(stationId, "ALL");
            renderAllIssues(stationId);
        }

        function closeFaultDetail(stationId) {
            const panel = document.getElementById(`fault-${stationId}`);

            if (panel) {
                panel.style.display = "none";
                panel.innerHTML = "";
            }

            const btn = document.getElementById(`fault-btn-${stationId}`);
            if (btn) {
                btn.classList.remove("active-fault");
            }

            openedFaultPanels.delete(stationId);
        }

        function renderComponentIssue(stationId, componentKey) {
            const data = latestDiagnosis[stationId];
            const panel = document.getElementById(`fault-${stationId}`);

            if (!data || !panel) return;

            const component = data.components.find(item => item.key === componentKey);
            if (!component) return;

            panel.className = component.level === "ok"
                ? "fault-detail-panel normal-detail"
                : "fault-detail-panel mixed-detail";
            panel.style.display = "block";

            const btn = document.getElementById(`fault-btn-${stationId}`);
            if (btn) {
                btn.classList.add("active-fault");
            }

            if (component.level === "ok") {
                panel.innerHTML = `
                    <h4>${component.name} ${component.en}｜${statusText(component.level)}</h4>
                    <div class="fault-item issue-item ok-item">
                        <div class="fault-line"><span class="fault-label">目前數值：</span>${component.value}</div>
                        <div class="fault-line"><span class="fault-label">問題說明：</span>目前狀態穩定，暫時不需要處理。</div>
                        <div class="fault-line"><span class="fault-label">可能原因：</span>無明顯異常。</div>
                        <div class="fault-line"><span class="fault-label">處理建議：</span>維持定期檢查即可。</div>
                    </div>
                    <button class="toggle-btn" onclick="closeFaultDetail('${stationId}')">收起 Close</button>
                `;
                return;
            }

            panel.innerHTML = `
                <h4>${component.level === "bad" ? "異常原因與改善建議" : "注意原因與改善建議"}</h4>
                <div class="fault-item issue-item ${component.level}-item">
                    <div class="fault-line"><span class="fault-label">零件：</span><span class="issue-status ${component.level}-text">${component.name} ${component.en}｜${statusText(component.level)}</span></div>
                    <div class="fault-line"><span class="fault-label">目前數值：</span>${component.value}</div>
                    <div class="fault-line"><span class="fault-label">問題說明：</span>${component.issue}</div>
                    <div class="fault-line"><span class="fault-label">可能原因：</span>${component.reason}</div>
                    <div class="fault-line"><span class="fault-label">處理建議：</span>${component.solution}</div>
                </div>
                <button class="toggle-btn" onclick="closeFaultDetail('${stationId}')">收起 Close</button>
            `;
        }

        function renderAllIssues(stationId) {
            const data = latestDiagnosis[stationId];
            const panel = document.getElementById(`fault-${stationId}`);

            if (!data || !panel) return;

            const issues = data.issues;

            if (issues.length === 0) {
                panel.className = "fault-detail-panel normal-detail";
                panel.style.display = "block";

                const btn = document.getElementById(`fault-btn-${stationId}`);
                if (btn) {
                    btn.classList.add("active-fault");
                }

                panel.innerHTML = `
                    <h4>${data.station.name}｜目前無異常</h4>
                    <div class="fault-item">所有零件目前皆為正常狀態，平常可保持收起，只需定期巡檢。</div>
                    <button class="toggle-btn" onclick="closeFaultDetail('${stationId}')">收起 Close</button>
                `;
                return;
            }

            const hasBadIssue = issues.some(component => component.level === "bad");
            const hasWarnIssue = issues.some(component => component.level === "warn");

            panel.className = "fault-detail-panel mixed-detail";

            panel.style.display = "block";

            const btn = document.getElementById(`fault-btn-${stationId}`);
            if (btn) {
                btn.classList.add("active-fault");
            }

            const issueTitle = hasBadIssue && hasWarnIssue
                ? "異常與注意原因及改善建議"
                : hasBadIssue
                    ? "異常原因與改善建議"
                    : "注意原因與改善建議";

            panel.innerHTML = `
                <h4>${data.station.name}｜${issueTitle}</h4>
                ${issues.map(component => `
                    <div class="fault-item issue-item ${component.level}-item">
                        <div class="fault-line"><span class="fault-label">零件：</span><span class="issue-status ${component.level}-text">${component.name} ${component.en}｜${statusText(component.level)}</span></div>
                        <div class="fault-line"><span class="fault-label">目前數值：</span>${component.value}</div>
                        <div class="fault-line"><span class="fault-label">問題說明：</span>${component.issue}</div>
                        <div class="fault-line"><span class="fault-label">可能原因：</span>${component.reason}</div>
                        <div class="fault-line"><span class="fault-label">處理建議：</span>${component.solution}</div>
                    </div>
                `).join("")}
                <button class="toggle-btn" onclick="closeFaultDetail('${stationId}')">收起 Close</button>
            `;
        }

        function updateSummary(stationData) {
            let normalCount = 0;
            let warningCount = 0;
            let riskCount = 0;

            stationData.forEach(station => {
                if (station.overall === "Running" || station.overall === "Standby") {
                    normalCount++;
                }

                if (station.overall === "Maintenance" || station.overall === "Alarm") {
                    warningCount++;
                }

                if (station.overall === "Maintenance" || station.overall === "Alarm" || station.clog >= 50 || station.availability < 80) {
                    riskCount++;
                }
            });

            document.getElementById("totalCount").innerText = stationData.length;
            document.getElementById("normalCount").innerText = normalCount;
            document.getElementById("warningCount").innerText = warningCount;
            document.getElementById("riskCount").innerText = riskCount;
        }

        function updateTime() {
            const now = new Date();

            const timeText = now.getFullYear() + "/" +
                String(now.getMonth() + 1).padStart(2, "0") + "/" +
                String(now.getDate()).padStart(2, "0") + " " +
                String(now.getHours()).padStart(2, "0") + ":" +
                String(now.getMinutes()).padStart(2, "0") + ":" +
                String(now.getSeconds()).padStart(2, "0");

            document.getElementById("updateTime").innerText = "最後更新時間：" + timeText;
        }

        function updateLiveBadge() {
            const badge = document.getElementById("liveStatusBadge");

            if (autoUpdate && getSliderValue() === 0) {
                badge.className = "live-badge";
                badge.innerText = "即時更新中";
            } else {
                badge.className = "pause-badge";
                badge.innerText = "時間軸檢視中";
            }
        }

        function updateTimeChips() {
            const offset = getSliderValue();
            const pastChip = document.getElementById("pastChip");
            const nowChip = document.getElementById("nowChip");
            const futureChip = document.getElementById("futureChip");

            pastChip.classList.remove("active");
            nowChip.classList.remove("active");
            futureChip.classList.remove("active");

            if (offset < 0) {
                pastChip.classList.add("active");
            } else if (offset > 0) {
                futureChip.classList.add("active");
            } else {
                nowChip.classList.add("active");
            }
        }

        function updateTimelineText(stationData) {
            const offset = getSliderValue();
            let label = "";

            if (currentMode === "time") {
                if (offset < 0) {
                    label = `過去${Math.abs(offset)}小時`;
                } else if (offset === 0) {
                    label = "現在";
                } else {
                    const futureHour = offset * 0.5;

                    if (futureHour % 1 === 0) {
                        label = `未來${futureHour.toFixed(0)}小時預測`;
                    } else {
                        label = `未來${futureHour}小時預測`;
                    }
                }
            } else {
                if (offset < 0) {
                    label = `過去第${Math.abs(offset)}批`;
                } else if (offset === 0) {
                    label = "目前批次";
                } else {
                    label = `未來第${offset}批預測`;
                }
            }

            document.getElementById("selectedTimeText").innerText = "目前時間點：" + label;

            let result = "";

            if (offset < 0) {
                result += `<span class="history-note">歷史資料檢視：</span><br>`;
                result += `目前顯示的是 ${label} 的設備狀態，可回看當時噴嘴堵塞率、空壓機壓力、可用度與品質變化。<br><br>`;
            } else if (offset === 0) {
                result += `<b>目前狀態：</b><br>`;
                result += `目前顯示的是三站即時狀態，資料會每1秒自動更新一次。<br><br>`;
            } else {
                result += `<span class="future-warning">未來預測：</span><br>`;
                result += `目前顯示的是 ${label}。系統根據噴嘴堵塞率、空壓機壓力、噴幅、可用度與品質變化推估可能風險。<br><br>`;
            }

            stationData.forEach(station => {
                result += `${station.name}：噴嘴堵塞率 ${station.clog}%，空壓機壓力 ${station.pressure}bar，噴幅 ${station.sprayWidth}mm，可用度 ${station.availability}%，品質 ${station.quality}%，風險判斷為「${station.riskText}」。<br>`;
            });

            document.getElementById("timelineResult").innerHTML = result;
            updateTimeChips();
        }

        function handleSliderChange() {
            const offset = getSliderValue();

            if (offset === 0) {
                autoUpdate = true;
            } else {
                autoUpdate = false;
            }

            refreshDashboard();
        }

        function backToLive() {
            const slider = document.getElementById("timeSlider");
            slider.value = 0;
            autoUpdate = true;
            refreshDashboard();
        }

        function setMode(mode) {
            currentMode = mode;

            const slider = document.getElementById("timeSlider");

            if (mode === "time") {
                slider.min = -6;
                slider.max = 4;
                slider.step = 1;
                slider.value = 0;

                document.getElementById("sliderLabels").className = "time-labels time-mode";
                document.getElementById("sliderLabels").innerHTML = `
                    <span class="left-label">過去6小時</span>
                    <span class="now-label">現在</span>
                    <span class="right-label">未來2小時</span>
                `;

                document.getElementById("timeModeBtn").classList.add("active");
                document.getElementById("batchModeBtn").classList.remove("active");
            } else {
                slider.min = -10;
                slider.max = 10;
                slider.step = 1;
                slider.value = 0;

                document.getElementById("sliderLabels").className = "time-labels batch-mode";
                document.getElementById("sliderLabels").innerHTML = `
                    <span class="left-label">過去10批</span>
                    <span class="now-label">目前批次</span>
                    <span class="right-label">未來10批</span>
                `;

                document.getElementById("timeModeBtn").classList.remove("active");
                document.getElementById("batchModeBtn").classList.add("active");
            }

            autoUpdate = true;
            refreshDashboard();
        }

        function refreshDashboard() {
            updateTime();

            const stationData = buildStationData();

            renderStations(stationData);
            updateSummary(stationData);
            updateTimelineText(stationData);
            updateLiveBadge();
        }

        refreshDashboard();

        setInterval(() => {
            if (autoUpdate && getSliderValue() === 0) {
                refreshDashboard();
            } else {
                updateTime();
                updateLiveBadge();
                updateTimeChips();
            }
        }, 1000);
    </script>

</body>
</html>
"""

output_path = Path(__file__).with_name("spraying_dashboard_updated.html")
output_path.write_text(html_code, encoding="utf-8")

main_code = r"""
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse

app = FastAPI(title="Spraying Line Monitoring System")

BASE_DIR = Path(__file__).resolve().parent
HTML_FILE = BASE_DIR / "spraying_dashboard_updated.html"

NO_CACHE_HEADERS = {
    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    "Pragma": "no-cache",
    "Expires": "0",
}

@app.get("/", response_class=HTMLResponse)
def home():
    if not HTML_FILE.exists():
        return HTMLResponse(
            content=(
                "<h2>找不到 spraying_dashboard_updated.html</h2>"
                "<p>請先執行 spraying_dashboard_updated_fixed_v4.py，"
                "或確認 main.py 和 spraying_dashboard_updated.html 放在同一個資料夾。</p>"
            ),
            status_code=404,
            headers=NO_CACHE_HEADERS,
        )

    return FileResponse(
        HTML_FILE,
        media_type="text/html; charset=utf-8",
        headers=NO_CACHE_HEADERS,
    )

@app.get("/spraying_dashboard_updated.html")
def dashboard_html():
    return home()
"""

main_path = Path(__file__).with_name("main.py")
main_path.write_text(main_code.strip() + "\n", encoding="utf-8")

print("已更新HTML：" + str(output_path))
print("已更新FastAPI入口：" + str(main_path))
print("現在可以執行：python -m uvicorn main:app --host 127.0.0.1 --port 8000")
