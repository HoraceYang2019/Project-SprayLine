from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any

from rdflib import Graph, Literal, Namespace, RDF, RDFS, OWL, URIRef
from rdflib.namespace import XSD

BASE_DIR = Path(__file__).resolve().parents[1]
SPRAY = Namespace("http://nkust.edu.tw/mislab/spray/ontology#")
MIS = Namespace("http://nkust.edu.tw/mislab#")
KNOWLEDGE_ONTOLOGY = URIRef("http://nkust.edu.tw/mislab/spray/knowledge/batch-A")


def _as_float(value: Any) -> Literal:
    return Literal(float(value), datatype=XSD.double)


def _as_int(value: Any) -> Literal:
    return Literal(int(float(value)), datatype=XSD.integer)


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def bind_graph() -> Graph:
    g = Graph()
    g.bind("spray", SPRAY)
    g.bind("mis", MIS)
    g.bind("owl", OWL)
    g.bind("rdfs", RDFS)
    g.bind("xsd", XSD)
    return g


def add_header(g: Graph, dataset: str, confidence: float) -> None:
    g.add((KNOWLEDGE_ONTOLOGY, RDF.type, OWL.Ontology))
    g.add((KNOWLEDGE_ONTOLOGY, RDFS.label, Literal("SprayLine learned threshold knowledge - generated from CSV", lang="en")))
    g.add((KNOWLEDGE_ONTOLOGY, MIS.confidence, Literal(confidence, datatype=XSD.double)))
    g.add((KNOWLEDGE_ONTOLOGY, MIS.derivedFromDataset, Literal(dataset)))


def add_filter_rows(g: Graph, rows: list[dict[str, str]]) -> None:
    for r in rows:
        s = MIS[r["state_id"]]
        g.add((s, RDF.type, MIS.BatchKnowledge))
        g.add((s, RDF.type, SPRAY[r["state_class"]]))
        g.add((s, MIS.hasKnowledgeCategory, Literal(r["knowledge_category"])))
        g.add((s, MIS.minFlowLossRatio, _as_float(r["min_flow_loss_ratio"])))
        g.add((s, MIS.maxFlowLossRatio, _as_float(r["max_flow_loss_ratio"])))
        g.add((s, MIS.severityRank, _as_int(r["severity_rank"])))
        g.add((s, MIS.confidence, _as_float(r["confidence"])))
        g.add((s, MIS.derivedFromDataset, Literal(r["dataset"])))


def add_nozzle_rows(g: Graph, rows: list[dict[str, str]]) -> None:
    for r in rows:
        s = MIS[r["state_id"]]
        g.add((s, RDF.type, MIS.BatchKnowledge))
        g.add((s, RDF.type, SPRAY[r["state_class"]]))
        g.add((s, MIS.hasKnowledgeCategory, Literal(r["knowledge_category"])))
        g.add((s, MIS.minPressureErrorRatio, _as_float(r["min_pressure_error_ratio"])))
        g.add((s, MIS.maxPressureErrorRatio, _as_float(r["max_pressure_error_ratio"])))
        g.add((s, MIS.minSprayWidthErrorRatio, _as_float(r["min_spray_width_error_ratio"])))
        g.add((s, MIS.maxSprayWidthErrorRatio, _as_float(r["max_spray_width_error_ratio"])))
        g.add((s, MIS.severityRank, _as_int(r["severity_rank"])))
        g.add((s, MIS.confidence, _as_float(r["confidence"])))
        g.add((s, MIS.derivedFromDataset, Literal(r["dataset"])))


def add_process_rows(g: Graph, rows: list[dict[str, str]]) -> None:
    for r in rows:
        s = MIS[r["state_id"]]
        g.add((s, RDF.type, MIS.BatchKnowledge))
        g.add((s, RDF.type, SPRAY[r["state_class"]]))
        g.add((s, MIS.hasKnowledgeCategory, Literal(r["knowledge_category"])))
        g.add((s, MIS.minThicknessErrorRatio, _as_float(r["min_thickness_error_ratio"])))
        g.add((s, MIS.maxThicknessErrorRatio, _as_float(r["max_thickness_error_ratio"])))
        g.add((s, MIS.minSeverityRank, _as_int(r["min_severity_rank"])))
        g.add((s, MIS.maxSeverityRank, _as_int(r["max_severity_rank"])))
        g.add((s, MIS.confidence, _as_float(r["confidence"])))
        g.add((s, MIS.derivedFromDataset, Literal(r["dataset"])))


def generate(filter_csv: Path, nozzle_csv: Path, process_csv: Path, out: Path) -> None:
    filter_rows = _read_csv(filter_csv)
    nozzle_rows = _read_csv(nozzle_csv)
    process_rows = _read_csv(process_csv)
    all_rows = filter_rows + nozzle_rows + process_rows
    dataset = all_rows[0].get("dataset", "sprayline_threshold_dataset") if all_rows else "sprayline_threshold_dataset"
    confidence = float(all_rows[0].get("confidence", 1.0)) if all_rows else 1.0

    g = bind_graph()
    add_header(g, dataset, confidence)
    add_filter_rows(g, filter_rows)
    add_nozzle_rows(g, nozzle_rows)
    add_process_rows(g, process_rows)
    out.parent.mkdir(parents=True, exist_ok=True)
    g.serialize(destination=out, format="turtle")
    print(f"[WRITE] {out} ({len(g)} triples)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate SprayLine knowledge TTL from threshold CSV files.")
    parser.add_argument("--filter-csv", default="knowledge/filter_thresholds.csv")
    parser.add_argument("--nozzle-csv", default="knowledge/nozzle_thresholds.csv")
    parser.add_argument("--process-csv", default="knowledge/process_thresholds.csv")
    parser.add_argument("--out", default="knowledge/SprayLine_knowledge.ttl")
    args = parser.parse_args()
    generate(
        BASE_DIR / args.filter_csv,
        BASE_DIR / args.nozzle_csv,
        BASE_DIR / args.process_csv,
        BASE_DIR / args.out,
    )


if __name__ == "__main__":
    main()
