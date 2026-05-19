from __future__ import annotations

import csv
from pathlib import Path
from rdflib import Graph, Namespace, Literal, URIRef
from rdflib.namespace import XSD

MIS = Namespace("http://nkust.edu.tw/mislab#")
PREFIX = {"mis": str(MIS)}

KNOWLEDGE_path = Path("ontology/SprayLine_knowledge.ttl")
UPDATED_KNOWLEDGE_path = Path("ontology/SprayLine_runtime_inferred.ttl")
CSV_path = Path("knowledge/thresholds_batch_A.csv")

def uri(qname: str) -> URIRef:
    prefix, local = qname.split(":", 1)
    return URIRef(PREFIX[prefix] + local)

def update_knowledge_from_csv(csv_path=CSV_path, in_ttl=KNOWLEDGE_path, out_ttl=UPDATED_KNOWLEDGE_path):
    g = Graph(); g.parse(in_ttl, format="turtle"); g.bind("mis", MIS)
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            s = uri(row["state"])
            min_p, max_p = uri(row["min_prop"]), uri(row["max_prop"])
            # remove old values for these properties
            for o in list(g.objects(s, min_p)): g.remove((s, min_p, o))
            for o in list(g.objects(s, max_p)): g.remove((s, max_p, o))
            for o in list(g.objects(s, MIS.severityRank)): g.remove((s, MIS.severityRank, o))
            for o in list(g.objects(s, MIS.derivedFromDataset)): g.remove((s, MIS.derivedFromDataset, o))
            for o in list(g.objects(s, MIS.confidence)): g.remove((s, MIS.confidence, o))
            g.add((s, min_p, Literal(float(row["min_value"]), datatype=XSD.decimal)))
            g.add((s, max_p, Literal(float(row["max_value"]), datatype=XSD.decimal)))
            g.add((s, MIS.severityRank, Literal(int(row["severity_rank"]), datatype=XSD.integer)))
            g.add((s, MIS.derivedFromDataset, Literal(row["dataset"])))
            g.add((s, MIS.confidence, Literal(float(row["confidence"]), datatype=XSD.decimal)))
    g.serialize(destination=out_ttl, format="turtle")
    print(f"Saved {out_ttl}")

if __name__ == "__main__":
    update_knowledge_from_csv()
