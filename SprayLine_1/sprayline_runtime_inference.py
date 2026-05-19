from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from rdflib import Graph, Namespace, RDF, Literal, URIRef
from rdflib.namespace import XSD

MIS = Namespace("http://nkust.edu.tw/mislab#")
STH = Namespace("http://nkust.edu.tw/mislab/cnc/ontology/sth#")
Ontology_path = Path("ontology/SprayLine_ontology.ttl")
Knowledge_path = Path("ontology/SprayLine_knowledge.ttl")
Runtime_path = Path("runtime/sprayline_runtime.example.json")
Inferred_path = Path("ontology/SprayLine_runtime_inferred.ttl")

@dataclass
class InferenceResult:
    window_id: str
    filter_state: str
    nozzle_state: str
    process_state: str
    flow_loss_ratio: float
    spray_width_error_ratio: float
    pressure_error_ratio: float
    thickness_error_ratio: float
    confidence: float
    diagnosis_uri: str


def load_knowledge_graph(ontology_ttl: str | Path, knowledge_ttl: str | Path) -> Graph:
    """Load static ontology + dynamic knowledge as one RDF graph."""
    g = Graph()
    g.parse(str(ontology_ttl), format="turtle")
    g.parse(str(knowledge_ttl), format="turtle")
    return g


def _as_float(value: Any) -> Optional[float]:
    return None if value is None else float(value)


def _local_name(uri: URIRef) -> str:
    return str(uri).split("#")[-1].split("/")[-1]


def find_threshold_state(g: Graph, state_class: URIRef, value: float, min_prop: URIRef, max_prop: URIRef) -> URIRef:
    """Find the state whose min/max range in SprayLine_knowledge.ttl covers value."""
    candidates: list[tuple[float, URIRef]] = []
    for state in g.subjects(RDF.type, state_class):
        lo = _as_float(g.value(state, min_prop))
        hi = _as_float(g.value(state, max_prop))
        if lo is None or hi is None:
            continue
        if lo <= value < hi or abs(value - hi) < 1e-12:
            rank = _as_float(g.value(state, MIS.severityRank)) or 0.0
            candidates.append((rank, state))
    if not candidates:
        raise ValueError(f"No TTL threshold range covers {value=} for {state_class}")
    return sorted(candidates, key=lambda item: item[0])[-1][1]


def infer_filter_state(g: Graph, in_flow: float, out_flow: float) -> tuple[URIRef, float]:
    if in_flow <= 0:
        raise ValueError("filter.in_flow must be > 0")
    flow_loss_ratio = max(0.0, min(1.0, (in_flow - out_flow) / in_flow))
    state = find_threshold_state(g, MIS.FilterState, flow_loss_ratio, MIS.minFlowLossRatio, MIS.maxFlowLossRatio)
    return state, flow_loss_ratio


def infer_nozzle_state(g: Graph, spray_width: float, target_width: float, pressure: float, target_pressure: float) -> tuple[URIRef, float, float]:
    if target_width <= 0 or target_pressure <= 0:
        raise ValueError("target spray_width and spray_pressure must be > 0")
    width_error = abs(spray_width - target_width) / target_width
    pressure_error = abs(pressure - target_pressure) / target_pressure
    severity_value = max(width_error, pressure_error)
    state = find_threshold_state(g, MIS.NozzleState, severity_value, MIS.minSprayWidthErrorRatio, MIS.maxSprayWidthErrorRatio)
    return state, width_error, pressure_error


def infer_process_state(g: Graph, filter_state: URIRef, nozzle_state: URIRef, measured_t: float, target_t: float) -> tuple[URIRef, float]:
    if target_t <= 0:
        raise ValueError("target.thickness must be > 0")
    thickness_error = abs(measured_t - target_t) / target_t
    thickness_state = find_threshold_state(g, STH.ChamberState, thickness_error, MIS.minThicknessErrorRatio, MIS.maxThicknessErrorRatio)

    filter_rank = int(g.value(filter_state, MIS.severityRank) or 0)
    nozzle_rank = int(g.value(nozzle_state, MIS.severityRank) or 0)
    thickness_rank = int(g.value(thickness_state, MIS.severityRank) or 0)
    max_rank = max(filter_rank, nozzle_rank, thickness_rank)

    # The mapping from severity rank to process state is in the knowledge TTL.
    for state in g.subjects(RDF.type, STH.ChamberState):
        rank = int(g.value(state, MIS.severityRank) or -1)
        if rank == max_rank:
            return state, thickness_error
    return thickness_state, thickness_error


def add_runtime_triples(g: Graph, result: InferenceResult) -> None:
    diagnosis = URIRef(result.diagnosis_uri)
    window = STH[result.window_id]
    g.add((window, RDF.type, STH.SensingWindow))
    g.add((diagnosis, RDF.type, STH.DiagnosisWindow))
    g.add((diagnosis, STH.diagnosesWindow, window))
    g.add((diagnosis, MIS.inferredFilterState, MIS[result.filter_state]))
    g.add((diagnosis, MIS.inferredNozzleState, MIS[result.nozzle_state]))
    g.add((diagnosis, MIS.inferredProcessState, MIS[result.process_state]))
    g.add((diagnosis, MIS.hasFlowLossRatio, Literal(result.flow_loss_ratio, datatype=XSD.decimal)))
    g.add((diagnosis, MIS.hasSprayWidthErrorRatio, Literal(result.spray_width_error_ratio, datatype=XSD.decimal)))
    g.add((diagnosis, MIS.hasPressureErrorRatio, Literal(result.pressure_error_ratio, datatype=XSD.decimal)))
    g.add((diagnosis, MIS.hasThicknessErrorRatio, Literal(result.thickness_error_ratio, datatype=XSD.decimal)))
    g.add((diagnosis, MIS.hasConfidence, Literal(result.confidence, datatype=XSD.decimal)))
    g.add((diagnosis, MIS.hasDiagnosisTimestamp, Literal(datetime.now(timezone.utc).isoformat(), datatype=XSD.dateTime)))


def infer_from_json(
    ontology_ttl: str | Path = Ontology_path,
    knowledge_ttl: str | Path = Knowledge_path,
    runtime_json: str | Path = Runtime_path,
    output_ttl: str | Path = Inferred_path,
) -> InferenceResult:
    g = load_knowledge_graph(ontology_ttl, knowledge_ttl)
    data = json.loads(Path(runtime_json).read_text(encoding="utf-8"))

    filter_state, flow_loss = infer_filter_state(g, data["filter"]["in_flow"], data["filter"]["out_flow"])
    nozzle_state, width_error, pressure_error = infer_nozzle_state(
        g,
        data["nozzle"]["spray_width"], data["target"]["spray_width"],
        data["nozzle"]["spray_pressure"], data["target"]["spray_pressure"],
    )
    process_state, thickness_error = infer_process_state(
        g, filter_state, nozzle_state, data["quality"]["measured_thickness"], data["target"]["thickness"]
    )

    confidence = round(max(0.50, 1.0 - max(flow_loss, width_error, pressure_error, thickness_error)), 4)
    result = InferenceResult(
        window_id=data["window_id"],
        filter_state=_local_name(filter_state),
        nozzle_state=_local_name(nozzle_state),
        process_state=_local_name(process_state),
        flow_loss_ratio=round(flow_loss, 6),
        spray_width_error_ratio=round(width_error, 6),
        pressure_error_ratio=round(pressure_error, 6),
        thickness_error_ratio=round(thickness_error, 6),
        confidence=confidence,
        diagnosis_uri=str(STH[f"Diagnosis_{data['window_id']}_{_local_name(process_state)}"]),
    )
    add_runtime_triples(g, result)
    g.serialize(destination=str(output_ttl), format="turtle")
    return result


if __name__ == "__main__":
    result = infer_from_json()
    print(json.dumps(result.__dict__, indent=2))
