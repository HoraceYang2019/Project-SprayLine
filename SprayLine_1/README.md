# SprayLine Ontology + Knowledge + Runtime Pipeline

This package separates the spray-line digital-twin inference model into three layers.

## 1. Files

| File | Role |
|---|---|
| `SprayLine_ontology.ttl` | Static ontology: classes, properties, individuals, semantic relationships. |
| `SprayLine_knowledge.ttl` | Dynamic knowledge: thresholds, severity ranks, dataset provenance, confidence. |
| `sprayline_runtime.example.json` | Runtime sensing window from the spray line. |
| `sprayline_runtime.schema.json` | JSON Schema for the runtime sensing window. |
| `sprayline_runtime_inference.py` | Inference engine. It loads both TTL files and infers states. |
| `thresholds_batch_A.csv` | Editable learned threshold table. |
| `update_knowledge_from_csv.py` | Converts the CSV threshold table into a new knowledge TTL. |
| `SprayLine_runtime_inferred.ttl` | Output produced by the inference engine. |
| `test_run_output.txt` | Example test result. |

## 2. Architecture

```text
SprayLine_ontology.ttl      = stable semantic model
SprayLine_knowledge.ttl     = updateable learned thresholds and confidence
sprayline_runtime.json      = online sensing data / MQTT payload / OPC UA bridge payload
sprayline_runtime_inference.py = runtime inference engine
```

## 3. Run

```bash
pip install rdflib
python sprayline_runtime_inference.py
```

Expected result:

```json
{
  "filter_state": "FilterModerateBlock",
  "nozzle_state": "NozzleEarly",
  "process_state": "IssuedProcess"
}
```

## 4. Update thresholds without touching the ontology

Edit:

```text
thresholds_batch_A.csv
```

Then run:

```bash
python update_knowledge_from_csv.py
```

This produces:

```text
SprayLine_knowledge_updated.ttl
```

Use it in the runtime engine by changing the `knowledge_ttl` argument.

## 5. Why this split is better

- Ontology remains stable and reusable.
- Thresholds can be retrained per machine, batch, coating material, nozzle, or filter.
- Runtime data remains lightweight JSON.
- Inference is ontology-driven because threshold ranges are read from TTL, not hard-coded in Python.
