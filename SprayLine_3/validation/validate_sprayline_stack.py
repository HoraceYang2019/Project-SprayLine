from __future__ import annotations

from pathlib import Path
from typing import Iterable

from pyshacl import validate
from rdflib import Graph, Literal, Namespace

BASE_DIR = Path(__file__).resolve().parents[1]
ONTOLOGY_DIR = BASE_DIR / "ontology"
KNOWLEDGE_DIR = BASE_DIR / "knowledge"
RUNTIME_DIR = BASE_DIR / "runtime"
SHAPES_DIR = BASE_DIR / "shapes"
OUTPUT_DIR = BASE_DIR / "output"

SPRAY = Namespace("http://nkust.edu.tw/mislab/spray/ontology#")
MIS = Namespace("http://nkust.edu.tw/mislab#")


def parse_existing(files: Iterable[Path]) -> Graph:
    g = Graph()
    g.bind("spray", SPRAY)
    g.bind("mis", MIS)
    for f in files:
        if f.exists():
            print(f"[LOAD] {f}")
            g.parse(f, format="turtle")
        else:
            print(f"[SKIP] {f}")
    return g


def normalize_category_literals(g: Graph) -> None:
    for s, p, o in list(g.triples((None, MIS.hasKnowledgeCategory, None))):
        if isinstance(o, Literal):
            g.remove((s, p, o))
            g.add((s, p, Literal(str(o))))


def run_validation(data_graph: Graph, shapes_graph: Graph, label: str, out_prefix: str) -> bool:
    conforms, report_graph, report_text = validate(
        data_graph=data_graph,
        shacl_graph=shapes_graph,
        inference="rdfs",
        advanced=True,
        debug=False,
    )
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / f"{out_prefix}_validation_report.txt").write_text(report_text, encoding="utf-8")
    report_graph.serialize(destination=OUTPUT_DIR / f"{out_prefix}_validation_report.ttl", format="turtle")
    print(f"\n[{label}] {'PASS' if conforms else 'FAIL'}")
    print(report_text)
    return bool(conforms)


def main() -> None:
    shapes = parse_existing([SHAPES_DIR / "SprayLine_hybrid_shapes.ttl"])

    knowledge_graph = parse_existing([
        ONTOLOGY_DIR / "SprayLine_ontology.ttl",
        *sorted(KNOWLEDGE_DIR.glob("*.ttl")),
    ])
    normalize_category_literals(knowledge_graph)
    k_ok = run_validation(knowledge_graph, shapes, "knowledge layer", "knowledge")

    runtime_graph = parse_existing([
        ONTOLOGY_DIR / "SprayLine_ontology.ttl",
        RUNTIME_DIR / "SprayLine_runtime_observation.ttl",
    ])
    r_ok = run_validation(runtime_graph, shapes, "runtime layer", "runtime")

    if not (k_ok and r_ok):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
