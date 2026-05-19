from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path
from typing import Iterable

from rdflib import Graph, Literal, Namespace, RDF
from rdflib.namespace import XSD

BASE_DIR = Path(__file__).resolve().parents[1]
SPRAY = Namespace("http://nkust.edu.tw/mislab/spray/ontology#")
MIS = Namespace("http://nkust.edu.tw/mislab#")


def expand_json_inputs(patterns: Iterable[str], sample_dir: str | None) -> list[Path]:
    paths: list[Path] = []
    if sample_dir:
        paths.extend(sorted((BASE_DIR / sample_dir).glob("*.json")))
    for p in patterns:
        matches = glob.glob(str(BASE_DIR / p)) if not Path(p).is_absolute() else glob.glob(p)
        paths.extend(Path(m) for m in matches)
    # de-duplicate while preserving order
    seen = set()
    out = []
    for p in paths:
        rp = p.resolve()
        if rp not in seen:
            seen.add(rp)
            out.append(rp)
    return out


def ratio_abs(actual: float, target: float) -> float:
    if target == 0:
        return 0.0
    return abs(actual - target) / abs(target)


def flow_loss(actual: float, nominal: float) -> float:
    if nominal == 0:
        return 0.0
    return max(0.0, (nominal - actual) / nominal)


def add_window(g: Graph, obj: dict) -> None:
    wid = str(obj["window_id"])
    w = MIS[f"RuntimeWindow_{wid}"]
    ref = obj["reference"]
    sig = obj["signals"]

    g.add((w, RDF.type, SPRAY.SprayWindow))
    g.add((w, SPRAY.hasWindowId, Literal(wid)))
    g.add((w, SPRAY.hasLineId, Literal(obj["line_id"])))
    g.add((w, SPRAY.hasBatchId, Literal(obj["batch_id"])))
    g.add((w, SPRAY.hasSegmentId, Literal(obj["segment_id"])))
    g.add((w, SPRAY.hasStartTime, Literal(obj["start_time"], datatype=XSD.dateTime)))
    g.add((w, SPRAY.hasEndTime, Literal(obj["end_time"], datatype=XSD.dateTime)))
    g.add((w, SPRAY.mapsToJSONField, SPRAY.Field_window))
    g.add((w, SPRAY.mapsToMQTTTopic, SPRAY.Topic_Window))
    g.add((w, SPRAY.mapsToOPCUANode, SPRAY.OPCUA_Window))

    pressure_err = ratio_abs(float(sig["pressure_bar"]), float(ref["nominal_pressure_bar"]))
    flow_loss_ratio = flow_loss(float(sig["flow_ml_min"]), float(ref["nominal_flow_ml_min"]))
    width_err = ratio_abs(float(sig["spray_width_mm"]), float(ref["nominal_spray_width_mm"]))
    thickness_err = ratio_abs(float(sig["thickness_um"]), float(ref["target_thickness_um"]))

    g.add((w, MIS.pressureErrorRatio, Literal(pressure_err, datatype=XSD.double)))
    g.add((w, MIS.flowLossRatio, Literal(flow_loss_ratio, datatype=XSD.double)))
    g.add((w, MIS.sprayWidthErrorRatio, Literal(width_err, datatype=XSD.double)))
    g.add((w, MIS.thicknessErrorRatio, Literal(thickness_err, datatype=XSD.double)))

    signal_map = {
        "pressure_bar": (SPRAY.PressureSignal, "bar", SPRAY.Field_pressure),
        "flow_ml_min": (SPRAY.FlowSignal, "ml/min", SPRAY.Field_flow),
        "spray_width_mm": (SPRAY.SprayWidthSignal, "mm", SPRAY.Field_spray_width),
        "thickness_um": (SPRAY.ThicknessSignal, "um", SPRAY.Field_thickness),
        "viscosity_cp": (SPRAY.ViscositySignal, "cP", None),
        "temperature_c": (SPRAY.TemperatureSignal, "degC", None),
    }
    for key, value in sig.items():
        if key not in signal_map:
            continue
        cls, unit, field = signal_map[key]
        s = MIS[f"Signal_{wid}_{key}"]
        g.add((s, RDF.type, cls))
        g.add((s, SPRAY.belongsToWindow, w))
        g.add((s, SPRAY.hasValue, Literal(float(value), datatype=XSD.double)))
        g.add((s, SPRAY.hasUnit, Literal(unit)))
        if field is not None:
            g.add((s, SPRAY.mapsToJSONField, field))


def convert(json_files: list[Path], out: Path) -> None:
    g = Graph()
    g.bind("spray", SPRAY)
    g.bind("mis", MIS)
    g.bind("xsd", XSD)

    for f in json_files:
        print(f"[LOAD] {f}")
        add_window(g, json.loads(f.read_text(encoding="utf-8")))

    out.parent.mkdir(parents=True, exist_ok=True)
    g.serialize(destination=out, format="turtle")
    print(f"[WRITE] {out}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert SprayLine runtime JSON samples into runtime TTL.")
    parser.add_argument("--json", nargs="*", default=[], help="JSON file paths or glob patterns, e.g. samples/sprayline_runtime_*.json")
    parser.add_argument("--sample-dir", default="samples", help="Default folder containing sample JSON files. Use empty string to disable.")
    parser.add_argument("--out", default="runtime/SprayLine_runtime_observation.ttl")
    args = parser.parse_args()
    sample_dir = args.sample_dir if args.sample_dir else None
    json_files = expand_json_inputs(args.json, sample_dir)
    if not json_files:
        raise FileNotFoundError("No JSON files found. Put files in samples/ or pass --json.")
    convert(json_files, BASE_DIR / args.out)


if __name__ == "__main__":
    main()
