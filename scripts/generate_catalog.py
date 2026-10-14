"""Génère docs/metric_catalog.md depuis semantic_manifest.json (source de vérité)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
man = json.loads((ROOT / "dbt_project/target/semantic_manifest.json").read_text())

lines = ["# Catalogue de métriques", "",
         "_Généré automatiquement depuis `semantic_manifest.json`._", "",
         "| Métrique | Type | Définition |", "|---|---|---|"]
for m in sorted(man["metrics"], key=lambda x: x["name"]):
    tp = m["type_params"]
    if m["type"] == "simple":
        d = f"mesure `{tp['measure']['name']}`"
    elif m["type"] == "ratio":
        d = f"`{tp['numerator']['name']}` / `{tp['denominator']['name']}`"
    elif m["type"] == "derived":
        d = f"`{tp['expr']}`"
    else:
        d = ""
    desc = (m.get("description") or "").replace("\n", " ")
    lines.append(f"| `{m['name']}` | {m['type']} | {d} {('— ' + desc) if desc else ''} |")

lines += ["", "## Modèles sémantiques", "", "| Modèle | Entités | Dimensions | Mesures |", "|---|---|---|---|"]
for s in man["semantic_models"]:
    lines.append("| {} | {} | {} | {} |".format(
        s["name"],
        ", ".join(e["name"] for e in s["entities"]),
        ", ".join(d["name"] for d in s["dimensions"]),
        ", ".join(x["name"] for x in s["measures"])))
(ROOT / "docs").mkdir(exist_ok=True)
(ROOT / "docs/metric_catalog.md").write_text("\n".join(lines) + "\n")
print("docs/metric_catalog.md écrit")
