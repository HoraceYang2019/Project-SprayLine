from __future__ import annotations
from pathlib import Path
from rdflib import Graph, Namespace

BASE_DIR = Path(__file__).resolve().parent
ONTOLOGY_DIR = BASE_DIR/'ontology'
FILES = [ONTOLOGY_DIR/'SprayLine_ontology.ttl', ONTOLOGY_DIR/'SprayLine_knowledge.ttl', ONTOLOGY_DIR/'SprayLine_runtime_observation.ttl']
RULE_DIR = BASE_DIR/'rules'
OUTPUT_TTL = BASE_DIR/'SprayLine_runtime_inferred_sparql.ttl'
STH = Namespace("http://nkust.edu.tw/mislab/cnc/ontology/sth#")
MIS = Namespace("http://nkust.edu.tw/mislab#")

def load_graph() -> Graph:
    g = Graph()
    for f in FILES:
        g.parse(f, format='turtle')
    return g

def apply_construct_rule(g: Graph, rule_file: Path) -> int:
    added = 0
    for triple in g.query(rule_file.read_text(encoding='utf-8')):
        if triple not in g:
            g.add(triple)
            added += 1
    return added

def run_inference() -> Graph:
    g = load_graph()
    for rule in sorted(RULE_DIR.glob('*.rq')):
        print(f'{rule.name}: added {apply_construct_rule(g, rule)} triples')
    g.serialize(destination=OUTPUT_TTL, format='turtle')
    print(f'Saved: {OUTPUT_TTL}')
    print(f'Total triples: {len(g)}')
    return g

def print_expected_result(g):
    print("\nExpected inferred result:")

    diagnosis_found = False

    for diagnosis in g.subjects(RDF.type, STH.DiagnosisWindow):
        diagnosis_found = True

        filter_state = g.value(diagnosis, MIS.indicatesFilterState)
        nozzle_state = g.value(diagnosis, MIS.indicatesNozzleState)
        process_state = g.value(diagnosis, STH.indicatesProcessState)

        print(f"  Diagnosis:     {diagnosis}")
        print(f"  Filter state:  {g.namespace_manager.normalizeUri(filter_state) if filter_state else 'None'}")
        print(f"  Nozzle state:  {g.namespace_manager.normalizeUri(nozzle_state) if nozzle_state else 'None'}")
        print(f"  Process state: {g.namespace_manager.normalizeUri(process_state) if process_state else 'None'}")

    if not diagnosis_found:
        print("  No inferred diagnosis found.")

if __name__ == '__main__':
    g = run_inference()
    print_expected_result(g)