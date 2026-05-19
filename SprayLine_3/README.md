# SprayLine Ontology Project

This project is a spraying-line ontology stack adapted from the updated CNC TMV720 hybrid pattern.
It uses `samples/` instead of `examples/`.

## Folder layout

```text
sprayline_ontology/
├─ knowledge/       # learned threshold knowledge
├─ ontology/        # core OWL/RDF ontology
├─ rules/           # SPARQL CONSTRUCT inference rules
├─ schema/          # JSON Schema files
├─ scripts/         # JSON-to-TTL and inference scripts
├─ shapes/          # SHACL validation shapes
├─ validation/      # validation runner
├─ samples/         # sample runtime JSON files
├─ runtime/         # generated runtime observation TTL
└─ output/          # inferred TTL and validation reports
```

## Install

```bash
pip install rdflib pyshacl jsonschema
```

## Run

```bash
python scripts/json_to_sprayline_ttl.py
python scripts/infer_sprayline.py
python validation/validate_sprayline_stack.py
```

## Main files

- `ontology/SprayLine_ontology.ttl`
- `knowledge/SprayLine_knowledge.ttl`
- `samples/sprayline_runtime_w0001.json`
- `samples/sprayline_runtime_w0002.json`
- `runtime/SprayLine_runtime_observation.ttl`
- `output/SprayLine_runtime_inferred_sparql.ttl`


## CSV threshold knowledge generation

Threshold CSV files are stored in `knowledge/`:

- `filter_thresholds.csv`
- `nozzle_thresholds.csv`
- `process_thresholds.csv`

Generate the RDF knowledge layer:

```bash
python scripts/knowledge_ttl_from_threshold_csv.py
```

This writes:

```text
knowledge/SprayLine_knowledge.ttl
```

## Full SprayLine semantic pipeline

Run the complete pipeline from the project root:

```bash
python pipeline.py
```

The pipeline performs:

1. CSV thresholds → `knowledge/SprayLine_knowledge.ttl`
2. `samples/*.json` → `runtime/SprayLine_runtime_observation.ttl`
3. SHACL validation → `output/*_validation_report.*`
4. SPARQL CONSTRUCT inference → `output/SprayLine_runtime_inferred_sparql.ttl`

You can also run inference only:

```bash
python rdf_native_infer_sparql.py
```
