from __future__ import annotations

import scripts.knowledge_ttl_from_threshold_csv as knowledge_ttl
import scripts.json_to_sprayline_ttl as runtime_ttl
import validation.validate_sprayline_stack as validate_stack
import rdf_native_infer_sparql as infer_runtime


def main() -> None:
    # 1. Generate knowledge/SprayLine_knowledge.ttl from threshold CSV files.
    knowledge_ttl.main()

    # 2. Generate runtime/SprayLine_runtime_observation.ttl from all JSON files in samples/.
    runtime_ttl.main()

    # 3. Run SHACL validation on ontology + knowledge and ontology + runtime.
    validate_stack.main()

    # 4. Run SPARQL CONSTRUCT inference and save output/SprayLine_runtime_inferred_sparql.ttl.
    infer_runtime.main()


if __name__ == "__main__":
    main()
