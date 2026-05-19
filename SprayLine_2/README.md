# SprayLine RDF-native inference + MQTT pipeline

This package upgrades the previous SprayLine pipeline into a more RDF-native architecture.

## Layers

1. `SprayLine_ontology.ttl`  
   Stable ontology layer: classes, individuals, object/data properties, diagnosis structure.

2. `SprayLine_knowledge.ttl`  
   Dynamic knowledge layer: threshold ranges, severity ranks, confidence, and dataset provenance.

3. `SprayLine_runtime_observation.ttl`  
   Runtime observation layer generated from streaming sensor data.

4. `rules/*.rq`  
   SPARQL `CONSTRUCT` rules. These are the inference rules. Python does not contain threshold `if/else` logic.

5. `sprayline_shacl_rules.ttl`  
   SHACL-AF/SPARQL rules for RDF-native inference using a SHACL engine such as pySHACL.

## Install

```bash
pip install -r requirements.txt
```

## RDF-native SPARQL inference

```bash
python rdf_native_infer_sparql.py
```

The script loads:

```text
SprayLine_ontology.ttl
SprayLine_knowledge.ttl
SprayLine_runtime_observation.ttl
```

Then executes:

```text
rules/01_filter_state.rq
rules/02_nozzle_state.rq
rules/03_process_state.rq
rules/04_diagnosis_construct.rq
```

Output:

```text
SprayLine_runtime_inferred_sparql.ttl
```

Expected inferred states:

```text
Filter state  = mis:FilterModerateBlock
Nozzle state  = mis:NozzleEarly
Process state = mis:IssuedProcess
```

## SHACL-AF inference

```bash
python rdf_native_infer_shacl.py
```

This uses `sprayline_shacl_rules.ttl` with `advanced=True` and `iterate_rules=True`.

Output:

```text
SprayLine_runtime_inferred_shacl.ttl
```

## MQTT streaming pipeline

Start a broker, for example Mosquitto:

```bash
mosquitto -v -p 1883
```

Start the subscriber:

```bash
python mqtt_to_ttl_subscriber.py
```

Publish an example runtime window:

```bash
python mqtt_publish_example.py
```

The subscriber receives JSON on:

```text
sprayline/+/window
```

Then it writes:

```text
SprayLine_runtime_observation.ttl
```

and runs RDF-native SPARQL inference to generate:

```text
SprayLine_runtime_inferred_sparql.ttl
```

## Important design point

The inference decision boundaries are not hard-coded in Python. They are stored in `SprayLine_knowledge.ttl`, for example:

```ttl
mis:FilterModerateBlock
    mis:minFlowLossRatio 0.132 ;
    mis:maxFlowLossRatio 0.387 ;
    mis:severityRank 1 .
```

The rule engine reads these triples through SPARQL.

## Recommended deployment pattern

```text
MQTT sensor JSON
      ↓
Observation TTL
      ↓
Ontology TTL + Knowledge TTL + SPARQL/SHACL rules
      ↓
Inferred diagnosis TTL
      ↓
MQTT / OPC UA / dashboard / database
```
