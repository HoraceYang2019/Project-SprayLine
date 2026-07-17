from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

try:
    from ontology.threshold_to_ttl import _literal, _num, _read_csv_text
except ModuleNotFoundError:
    from threshold_to_ttl import _literal, _num, _read_csv_text


PREFIX = """@prefix sl: <http://example.org/sprayline#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

"""

COMPONENTS = {
    "air_compressor": ("AirCompressor", "Air Compressor"),
    "filter_mesh": ("FilterMesh", "Filter Mesh"),
    "nozzle": ("Nozzle", "Nozzle"),
    "spray_width": ("SprayWidthModule", "Spray Width Module"),
    "quality": ("QualityModule", "Quality Module"),
    "robot_arm": ("RobotArm", "Robot Arm"),
    "environment": ("EnvironmentModule", "Environment Module"),
}

THRESHOLD_PROPERTIES = {
    "normal_min": "normalMin",
    "normal_max": "normalMax",
    "warning_low_min": "warningLowMin",
    "warning_low_max": "warningLowMax",
    "warning_high_min": "warningHighMin",
    "warning_high_max": "warningHighMax",
    "fault_low_max": "faultLowMax",
    "fault_high_min": "faultHighMin",
}


def _safe(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in value)


def _label_from_id(value: str) -> str:
    return value.replace("_", " ").title()


def build_full_ontology(csv_path: Path, output_path: Path) -> None:
    rows = list(csv.DictReader(_read_csv_text(csv_path).splitlines()))
    component_metrics: dict[str, list[str]] = defaultdict(list)
    causes: set[str] = set()
    responses: set[str] = set()

    for row in rows:
        component_metrics[row["component"].strip()].append(row["metric"].strip())
        if row.get("cause_id", "").strip():
            causes.add(row["cause_id"].strip())
        responses.update(item for item in row.get("response_ids", "").split("|") if item)

    lines = [PREFIX]
    lines.extend([
        "sl:SprayLineOntology a owl:Ontology ;",
        '    rdfs:label "SprayLine Ontology 0628 Runtime Aligned" ;',
        f'    rdfs:comment "Generated from ontology/{csv_path.name}; aligned with formal runtime inference." ;',
        '    owl:versionInfo "0628_runtime" .',
        "",
        "sl:SprayLineSystem a owl:Class .",
        "sl:Station a owl:Class .",
        "sl:Component a owl:Class .",
        "sl:SensorMetric a owl:Class .",
        "sl:SensorThreshold a owl:Class .",
        "sl:ThresholdSet a owl:Class .",
        "sl:State a owl:Class .",
        "sl:Cause a owl:Class .",
        "sl:ResponseAction a owl:Class .",
        "sl:InferenceRule a owl:Class .",
        "",
        "sl:hasStation a owl:ObjectProperty ; rdfs:domain sl:SprayLineSystem ; rdfs:range sl:Station .",
        "sl:hasComponent a owl:ObjectProperty ; rdfs:domain sl:Station ; rdfs:range sl:Component .",
        "sl:monitorsMetric a owl:ObjectProperty ; rdfs:domain sl:Component ; rdfs:range sl:SensorMetric .",
        "sl:hasThreshold a owl:ObjectProperty ; rdfs:domain sl:SensorMetric ; rdfs:range sl:SensorThreshold .",
        "sl:belongsToThresholdSet a owl:ObjectProperty ; rdfs:domain sl:SensorThreshold ; rdfs:range sl:ThresholdSet .",
        "sl:hasNormalState a owl:ObjectProperty ; rdfs:domain sl:SensorThreshold ; rdfs:range sl:State .",
        "sl:hasWarningState a owl:ObjectProperty ; rdfs:domain sl:SensorThreshold ; rdfs:range sl:State .",
        "sl:hasFaultState a owl:ObjectProperty ; rdfs:domain sl:SensorThreshold ; rdfs:range sl:State .",
        "sl:indicatesCause a owl:ObjectProperty ; rdfs:domain sl:SensorThreshold ; rdfs:range sl:Cause .",
        "sl:recommendsAction a owl:ObjectProperty ; rdfs:domain sl:SensorThreshold ; rdfs:range sl:ResponseAction .",
        "sl:usesThreshold a owl:ObjectProperty ; rdfs:domain sl:InferenceRule ; rdfs:range sl:SensorThreshold .",
        "",
        "sl:stationId a owl:DatatypeProperty ; rdfs:domain sl:Station ; rdfs:range xsd:string .",
        "sl:componentName a owl:DatatypeProperty ; rdfs:domain sl:Component ; rdfs:range xsd:string .",
        "sl:metricName a owl:DatatypeProperty ; rdfs:range xsd:string .",
        "sl:unit a owl:DatatypeProperty ; rdfs:range xsd:string .",
        "sl:causeId a owl:DatatypeProperty ; rdfs:domain sl:Cause ; rdfs:range xsd:string .",
        "sl:responseId a owl:DatatypeProperty ; rdfs:domain sl:ResponseAction ; rdfs:range xsd:string .",
        "sl:description a owl:DatatypeProperty ; rdfs:range xsd:string .",
    ])
    for prop in THRESHOLD_PROPERTIES.values():
        lines.append(f"sl:{prop} a owl:DatatypeProperty ; rdfs:domain sl:SensorThreshold ; rdfs:range xsd:decimal .")

    component_uris = [f"sl:{uri}" for uri, _ in COMPONENTS.values()]
    lines.extend([
        "",
        "sl:SprayLine_A a sl:SprayLineSystem ; rdfs:label \"SprayLine A\" ;",
        "    sl:hasStation sl:Station_1, sl:Station_2, sl:Station_3 .",
        "",
    ])
    for index in range(1, 4):
        lines.extend([
            f"sl:Station_{index} a sl:Station ; rdfs:label \"Station {index}\" ; sl:stationId \"Station_{index}\" ;",
            f"    sl:hasComponent {', '.join(component_uris)} .",
        ])

    lines.extend([
        "",
        'sl:Normal a sl:State ; rdfs:label "Normal" .',
        'sl:Warning a sl:State ; rdfs:label "Warning" .',
        'sl:Fault a sl:State ; rdfs:label "Fault" .',
        "",
        "sl:ThresholdSet_0628_runtime a sl:ThresholdSet ;",
        '    rdfs:label "Threshold Set 0628 Runtime" ;',
        f'    sl:description "Generated from ontology/{csv_path.name}." .',
        "",
    ])

    for component, (uri, label) in COMPONENTS.items():
        metrics = component_metrics.get(component, [])
        lines.append(f"sl:{uri} a sl:Component ; rdfs:label {_literal(label)} ; sl:componentName {_literal(component)}" + (" ;" if metrics else " ."))
        if metrics:
            metric_uris = ", ".join(f"sl:Metric_{_safe(metric)}" for metric in metrics)
            lines.append(f"    sl:monitorsMetric {metric_uris} .")
        lines.append("")

    threshold_uris: list[str] = []
    for row in rows:
        metric = row["metric"].strip()
        threshold_uri = f"sl:Threshold_{_safe(metric)}"
        threshold_uris.append(threshold_uri)
        response_ids = [item for item in row.get("response_ids", "").split("|") if item]
        cause_id = row.get("cause_id", "").strip()

        lines.extend([
            f"sl:Metric_{_safe(metric)} a sl:SensorMetric ; rdfs:label {_literal(metric)} ;",
            f"    sl:metricName {_literal(metric)} ; sl:unit {_literal(row.get('unit'))} ;",
            f"    sl:hasThreshold {threshold_uri} .",
            "",
            f"{threshold_uri} a sl:SensorThreshold ; rdfs:label {_literal('Threshold for ' + metric)} ;",
            "    sl:belongsToThresholdSet sl:ThresholdSet_0628_runtime ;",
            "    sl:hasNormalState sl:Normal ; sl:hasWarningState sl:Warning ; sl:hasFaultState sl:Fault ;",
        ])
        if cause_id:
            lines.append(f"    sl:indicatesCause sl:Cause_{_safe(cause_id)} ;")
        if response_ids:
            action_uris = ", ".join(f"sl:Action_{_safe(item)}" for item in response_ids)
            lines.append(f"    sl:recommendsAction {action_uris} ;")
        for source, prop in THRESHOLD_PROPERTIES.items():
            value = _num(row.get(source))
            if value is not None:
                lines.append(f"    sl:{prop} {_literal(value, 'xsd:decimal')} ;")
        lines.append(f"    sl:description {_literal(row.get('description'))} .")
        lines.append("")

    for cause_id in sorted(causes):
        lines.append(
            f"sl:Cause_{_safe(cause_id)} a sl:Cause ; rdfs:label {_literal(_label_from_id(cause_id))} ; sl:causeId {_literal(cause_id)} ."
        )
    lines.append("")
    for response_id in sorted(responses):
        lines.append(
            f"sl:Action_{_safe(response_id)} a sl:ResponseAction ; rdfs:label {_literal(_label_from_id(response_id))} ; sl:responseId {_literal(response_id)} ."
        )

    lines.extend([
        "",
        'sl:Rule_Threshold_State_Inference a sl:InferenceRule ; rdfs:label "Threshold state inference rule" ;',
        f"    sl:usesThreshold {', '.join(threshold_uris)} ;",
        '    sl:description "Compare a runtime metric value with its threshold, then return State, Cause, and ResponseAction." .',
        "",
    ])
    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the Protégé ontology from formal runtime thresholds.")
    parser.add_argument("--csv", default="ontology/runtime_threshold_reference.csv")
    parser.add_argument("--output", default="ontology/sprayline_full_ontology.ttl")
    args = parser.parse_args()
    build_full_ontology(Path(args.csv), Path(args.output))
    print(f"[OK] Full ontology generated: {args.output}")


if __name__ == "__main__":
    main()
