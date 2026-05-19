from __future__ import annotations

from pathlib import Path
from rdflib import Graph, Namespace, RDF

BASE = Path(__file__).resolve().parent
ONTOLOGY_FILE = BASE / "ontology" / "SprayLine_ontology.ttl"
KNOWLEDGE_FILES = [BASE / "knowledge" / "SprayLine_knowledge.ttl"]
RUNTIME_FILES = [BASE / "runtime" / "SprayLine_runtime_observation.ttl"]
RULE_DIR = BASE / "rules"
OUTPUT_TTL = BASE / "output" / "SprayLine_runtime_inferred_sparql.ttl"

SPRAY = Namespace("http://nkust.edu.tw/mislab/spray/ontology#")
MIS = Namespace("http://nkust.edu.tw/mislab#")


def load_graph() -> Graph:
    g = Graph()
    g.bind("spray", SPRAY)
    g.bind("mis", MIS)
    g.parse(ONTOLOGY_FILE, format="turtle")
    for f in KNOWLEDGE_FILES + RUNTIME_FILES:
        if not f.exists():
            raise FileNotFoundError(f)
        g.parse(f, format="turtle")
    return g


def apply_construct_rule(g: Graph, rule_file: Path) -> int:
    added = 0
    query = rule_file.read_text(encoding="utf-8")
    for triple in g.query(query):
        if triple not in g:
            g.add(triple)
            added += 1
    return added


def _fmt(g: Graph, node) -> str:
    return g.namespace_manager.normalizeUri(node) if node else "None"


def print_results(g: Graph) -> None:
    print("\n===== SprayLine Inferred Results =====\n")
    found = False
    for window in sorted(g.subjects(RDF.type, SPRAY.SprayWindow), key=str):
        if not str(window).startswith(str(MIS) + "RuntimeWindow_"):
            continue
        found = True
        filter_state = g.value(window, SPRAY.indicatesFilterCondition)
        nozzle_state = g.value(window, SPRAY.indicatesNozzleCondition)
        process_state = g.value(window, SPRAY.indicatesProcessState)
        print(f"Window: {g.namespace_manager.normalizeUri(window)}")
        print(f"  Filter condition: {_fmt(g, filter_state)}")
        print(f"  Nozzle condition: {_fmt(g, nozzle_state)}")
        print(f"  Process state:    {_fmt(g, process_state)}\n")
    if not found:
        print("No runtime SprayWindow instances found.")


def main() -> None:
    g = load_graph()
    print(f"Loaded graph size: {len(g)}")
    total = 0
    for rule in sorted(RULE_DIR.glob("*.rq")):
        n = apply_construct_rule(g, rule)
        total += n
        print(f"{rule.name}: added {n} triples")
    OUTPUT_TTL.parent.mkdir(parents=True, exist_ok=True)
    g.serialize(destination=OUTPUT_TTL, format="turtle")
    print(f"Saved: {OUTPUT_TTL}")
    print(f"Total inferred triples added: {total}")
    print(f"Final graph size: {len(g)}")
    print_results(g)


if __name__ == "__main__":
    main()
