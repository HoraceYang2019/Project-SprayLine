from __future__ import annotations

import argparse
import csv
from pathlib import Path

PREFIX = """@prefix sl: <http://example.org/sprayline#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

"""


def _read_csv_text(csv_path: Path) -> str:
    data = csv_path.read_bytes()
    for enc in ("utf-8-sig", "utf-8", "cp950", "big5", "gb18030"):
        try:
            text = data.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        text = data.decode("latin1")

    lines = text.splitlines()
    if lines and lines[0].strip().lower().replace(" ", "") == "sep=,":
        lines = lines[1:]
    return "\n".join(lines)



def _num(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value if value else None


def _literal(value: str | None, datatype: str = "xsd:string") -> str | None:
    if value is None:
        return None
    value = str(value).strip()
    if not value:
        return None
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    if datatype == "xsd:string":
        return f'"{escaped}"'
    return f'"{escaped}"^^{datatype}'


def _metric_uri(metric: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in metric)
    return f"sl:Threshold_{safe}"


def convert_csv_to_ttl(csv_path: Path, ttl_path: Path) -> None:
    rows = list(csv.DictReader(_read_csv_text(csv_path).splitlines()))

    lines: list[str] = [PREFIX]
    lines.append("sl:SprayLineThresholdSet a sl:ThresholdSet ;")
    lines.append(f'    sl:sourceFile "ontology/{csv_path.name}" ;')
    lines.append('    sl:version "0628_runtime" .')
    lines.append("")

    for row in rows:
        metric = row["metric"].strip()
        uri = _metric_uri(metric)
        triples: list[tuple[str, str]] = [
            ("a", "sl:SensorThreshold"),
            ("sl:metricName", _literal(metric)),
            ("sl:component", _literal(row.get("component"))),
            ("sl:componentZh", _literal(row.get("component_zh"))),
            ("sl:unit", _literal(row.get("unit"))),
            ("sl:causeId", _literal(row.get("cause_id"))),
            ("sl:responseIds", _literal(row.get("response_ids"))),
            ("sl:description", _literal(row.get("description"))),
            ("sl:belongsTo", "sl:SprayLineThresholdSet"),
        ]

        for key in [
            "normal_min",
            "normal_max",
            "warning_low_min",
            "warning_low_max",
            "warning_high_min",
            "warning_high_max",
            "fault_low_max",
            "fault_high_min",
        ]:
            value = _num(row.get(key))
            if value is not None:
                triples.append((f"sl:{key}", _literal(value, "xsd:decimal")))

        lines.append(f"{uri} " + triples[0][0] + " " + triples[0][1] + " ;")
        for pred, obj in triples[1:-1]:
            lines.append(f"    {pred} {obj} ;")
        lines.append(f"    {triples[-1][0]} {triples[-1][1]} .")
        lines.append("")

    ttl_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert SprayLine threshold CSV to TTL.")
    parser.add_argument("--csv", default="ontology/runtime_threshold_reference.csv")
    parser.add_argument("--ttl", default="ontology/sprayline_threshold.ttl")
    args = parser.parse_args()
    convert_csv_to_ttl(Path(args.csv), Path(args.ttl))
    print(f"[OK] TTL generated: {args.ttl}")


if __name__ == "__main__":
    main()
