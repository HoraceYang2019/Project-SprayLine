from __future__ import annotations

from typing import Any


ISSUE_CATALOG: dict[str, dict[str, str]] = {
    "SERVO_OVERLOAD": {
        "issue": "機械手臂伺服負載偏高，可能影響路徑穩定與定位精度。",
        "reason": "可能原因為關節阻力增加、潤滑不足、負載過高或伺服元件磨耗。",
    },
    "PATH_ERROR_HIGH": {
        "issue": "機械手臂路徑誤差偏高，實際軌跡可能偏離設定路徑。",
        "reason": "可能原因為 TCP 校正偏移、工件定位誤差或關節背隙增加。",
    },
    "NOZZLE_CLOG": {
        "issue": "噴嘴塗料流量偏離正常範圍，可能造成膜厚不均或漏噴。",
        "reason": "可能原因為噴嘴堵塞、塗料黏度變化、供料不穩或前段過濾異常。",
    },
    "FILTER_CLOG": {
        "issue": "濾網壓差偏高，可能造成塗料流量下降並增加噴嘴堵塞風險。",
        "reason": "可能原因為濾網累積雜質、塗料顆粒增加或清潔週期過長。",
    },
    "AIR_PRESSURE_UNSTABLE": {
        "issue": "空壓機壓力超出正常範圍，可能造成霧化不穩與噴塗不均。",
        "reason": "可能原因為調壓閥設定偏移、管路漏氣、空壓機輸出不穩或濾水杯堵塞。",
    },
    "SPRAY_WIDTH_DEVIATION": {
        "issue": "噴幅寬度偏離正常範圍，可能造成覆蓋不足、飛漆或膜厚分布不均。",
        "reason": "可能原因為噴嘴距離、空氣壓力、塗料流量或噴嘴狀態異常。",
    },
    "SURFACE_DEFECT": {
        "issue": "環境溫度或濕度偏離正常範圍，可能增加表面缺陷與乾燥不穩風險。",
        "reason": "可能原因為環控設備輸出不足、空調設定偏移或環境負載改變。",
    },
    "FILM_THICKNESS_OOC": {
        "issue": "膜厚偏離品質參考範圍，可能造成保護性或外觀品質不穩。",
        "reason": "可能原因為噴塗速度、流量、噴幅、距離或環境條件共同變動。",
    },
}


RESPONSE_CATALOG: dict[str, str] = {
    "LUBRICATE_SERVO": "檢查關節與伺服負載，依保養規範補充潤滑。",
    "REPLACE_SERVO": "若負載持續異常，安排伺服元件檢測或更換。",
    "RECALIBRATE_TCP": "重新校正 TCP 與工件座標，確認定位基準。",
    "CLEAN_NOZZLE": "清潔噴嘴並確認塗料黏度與供料狀態。",
    "REPLACE_NOZZLE": "清潔後仍異常時，檢查或更換噴嘴。",
    "REPLACE_FILTER": "清潔或更換濾網，並確認前後端流量。",
    "BACKWASH_FILTER": "依設備規範進行反沖洗或縮短清潔週期。",
    "CALIBRATE_PRESSURE_VALVE": "檢查空壓機、管線與調壓閥，重新校正壓力。",
    "ADJUST_TCP_Z": "調整噴嘴與工件距離，重新確認 TCP Z 高度。",
    "ADJUST_FLOW_PRESSURE": "同步調整塗料流量與空氣壓力，使噴幅回到正常範圍。",
    "CALIBRATE_ENV_CONTROL": "檢查環控設備並重新調整溫度與濕度設定。",
    "ADJUST_SPEED_FLOW": "調整機械手臂速度與塗料流量，重新確認膜厚。",
    "TIGHTEN_BASE": "檢查底座與固定件，排除振動來源。",
    "FORCED_COOLDOWN": "安排降溫並檢查減速機與潤滑狀態。",
}


class DiagnosisService:
    def build_detail(
        self,
        component: dict[str, Any],
        source_sensor: str | None,
        mapping: dict[str, Any],
    ) -> dict[str, Any]:
        level = component.get("level", "ok")
        if level == "ok":
            return {
                "issue": "目前狀態位於正常範圍。",
                "reason": "目前未偵測到明顯異常。",
                "solution": "維持目前參數並持續定期監控。",
                "issue_state": None,
                "cause_id": None,
                "response_ids": [],
                "source_sensor": source_sensor,
            }

        issue_state = mapping.get("issue_state") or "UNMAPPED_STATE"
        cause_id = mapping.get("cause_id")
        response_ids = list(mapping.get("response_ids") or [])
        catalog = ISSUE_CATALOG.get(
            issue_state,
            {
                "issue": "此零件目前超出正常狀態範圍。",
                "reason": "需要依感測數值與現場設備狀況進一步確認。",
            },
        )
        solutions = [RESPONSE_CATALOG.get(item, item) for item in response_ids]
        return {
            "issue": catalog["issue"],
            "reason": catalog["reason"],
            "solution": " ".join(solutions) if solutions else "建議由維護人員進一步檢查。",
            "issue_state": issue_state,
            "cause_id": cause_id,
            "response_ids": response_ids,
            "source_sensor": source_sensor,
        }
