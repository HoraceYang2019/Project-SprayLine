from ontology.rule_inference import infer_state, smoke_cases
import json

if __name__ == "__main__":
    results = [infer_state(metric, value) for metric, value in smoke_cases()]
    print(json.dumps(results, ensure_ascii=False, indent=2))
