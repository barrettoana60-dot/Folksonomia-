"""
CLI de automação para o Sistema Folksonomia Digital Inteligente.
Este arquivo operacionaliza a parte "gerar automação" do pedido do usuário:
- reconciliação semântica em lote;
- treino supervisionado incremental;
- geração de relatórios;
- export de snapshot;
- modo completo.

Uso:
    python automation_pipeline.py --mode reconcile
    python automation_pipeline.py --mode train
    python automation_pipeline.py --mode report
    python automation_pipeline.py --mode snapshot
    python automation_pipeline.py --mode full
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

from semantic_engine import SemanticKnowledgeBase, bootstrap_default_concepts, normalize_text

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
EXPORT_DIR = BASE_DIR / "exports"
REPORT_DIR = EXPORT_DIR / "reports"
OBRAS_FILE = DATA_DIR / "obras.json"
TAGS_FILE = DATA_DIR / "tags.json"
USERS_FILE = DATA_DIR / "users.json"


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def now_slug() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json(path: Path, data: Any) -> None:
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_obras_df() -> pd.DataFrame:
    data = load_json(OBRAS_FILE, [])
    return pd.DataFrame(data) if data else pd.DataFrame()


def load_tags_df() -> pd.DataFrame:
    data = load_json(TAGS_FILE, [])
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data)
    if "timestamp" in df.columns:
        df["timestamp_dt"] = pd.to_datetime(df["timestamp"], errors="coerce")
        df["date"] = df["timestamp_dt"].dt.date
        df["month"] = df["timestamp_dt"].dt.to_period("M").astype(str)
    return df


def load_users_df() -> pd.DataFrame:
    data = load_json(USERS_FILE, [])
    return pd.DataFrame(data) if data else pd.DataFrame()


def persist_tags_df(df: pd.DataFrame) -> None:
    save_json(TAGS_FILE, df.to_dict(orient="records"))


def build_report_header(title: str) -> str:
    return "\n".join([
        "=" * 80,
        title,
        "=" * 80,
        f"Gerado em: {datetime.now().isoformat(timespec='seconds')}",
        "",
    ])


def report_entity_distribution(kb: SemanticKnowledgeBase, tags_df: pd.DataFrame) -> str:
    if tags_df.empty:
        return "Sem tags registradas."
    summary = kb.semantic_summary(tags_df)
    lines = [build_report_header("Distribuição semântica")]
    lines.append("Tipos de entidade:")
    for entity, count in sorted(summary["entity_distribution"].items(), key=lambda x: x[1], reverse=True):
        lines.append(f"  - {entity}: {count}")
    lines.append("")
    lines.append("Conceitos mais frequentes:")
    for concept, count in summary["concept_distribution"].items():
        lines.append(f"  - {concept}: {count}")
    lines.append("")
    lines.append(f"Taxa de ambiguidade: {summary['ambiguity_rate']:.2%}")
    lines.append("")
    lines.append("Lacunas de reconciliação:")
    for tag, count in summary["top_unresolved"]:
        lines.append(f"  - {tag}: {count}")
    lines.append("")
    return "\n".join(lines)


def report_lexical_diversity(tags_df: pd.DataFrame, obras_df: pd.DataFrame) -> str:
    lines = [build_report_header("Diversidade lexical por obra")]
    if tags_df.empty:
        lines.append("Sem tags registradas.")
        return "\n".join(lines)
    grouped = tags_df.groupby("obra_id").agg(
        tags_total=("tag", "count"),
        tags_unicas=("tag", lambda x: x.astype(str).apply(normalize_text).nunique()),
    ).reset_index()
    grouped["ttr"] = grouped["tags_unicas"] / grouped["tags_total"]
    obras_lookup = {int(r["id"]): r.get("titulo", f"Obra {r['id']}") for _, r in obras_df.iterrows()} if not obras_df.empty else {}
    for _, row in grouped.sort_values(["ttr", "tags_total"], ascending=[False, False]).iterrows():
        titulo = obras_lookup.get(int(row["obra_id"]), f"Obra {row['obra_id']}")
        lines.append(f"- {titulo}: total={int(row['tags_total'])} únicas={int(row['tags_unicas'])} ttr={row['ttr']:.3f}")
    lines.append("")
    return "\n".join(lines)


def report_validation_state(kb: SemanticKnowledgeBase, tags_df: pd.DataFrame) -> str:
    lines = [build_report_header("Estado de validação")]
    if tags_df.empty:
        lines.append("Sem tags registradas.")
        return "\n".join(lines)
    validated = tags_df["validated"].fillna(False).astype(bool).sum() if "validated" in tags_df.columns else 0
    pending = len(tags_df) - validated
    lines.append(f"Total de tags: {len(tags_df)}")
    lines.append(f"Validadas: {validated}")
    lines.append(f"Pendentes: {pending}")
    lines.append(f"Conceitos na base: {len(kb.concept_store)}")
    lines.append(f"Relações na base: {len(kb.relation_store)}")
    lines.append(f"Exemplos de treino: {len(kb.learning_examples)}")
    lines.append("")
    return "\n".join(lines)


def report_concept_gaps(kb: SemanticKnowledgeBase, tags_df: pd.DataFrame) -> str:
    lines = [build_report_header("Lacunas conceituais")]
    gap = kb.concept_gap_report(tags_df)
    lines.append(f"Cobertura semântica estimada: {gap['cobertura']:.2%}")
    lines.append(f"Total de tags analisadas: {gap['total_tags']}")
    lines.append("")
    lines.append("Tags sem boa reconciliação:")
    if not gap["sem_conceito"]:
        lines.append("  Nenhuma lacuna relevante.")
    else:
        for tag, count in gap["sem_conceito"]:
            lines.append(f"  - {tag}: {count}")
    lines.append("")
    return "\n".join(lines)


def export_text_report(name: str, content: str) -> Path:
    ensure_dir(REPORT_DIR)
    path = REPORT_DIR / f"{name}_{now_slug()}.txt"
    path.write_text(content, encoding="utf-8")
    return path


def run_reconcile(kb: SemanticKnowledgeBase, tags_df: pd.DataFrame, obras_df: pd.DataFrame) -> Dict[str, Any]:
    before_rel = len(kb.relation_store)
    before_concepts = len(kb.concept_store)
    result = kb.run_automation(obras_df, tags_df, admin_user="automation_cli")
    after_rel = len(kb.relation_store)
    after_concepts = len(kb.concept_store)
    payload = {
        "mode": "reconcile",
        "concepts_before": before_concepts,
        "concepts_after": after_concepts,
        "relations_before": before_rel,
        "relations_after": after_rel,
        "clusters_created": result.clusters_created,
        "concepts_created": result.concepts_created,
        "relations_created": result.relations_created,
        "trained_samples": result.trained_samples,
    }
    return payload


def run_train(kb: SemanticKnowledgeBase) -> Dict[str, Any]:
    meta = kb.train_entity_classifier()
    return {"mode": "train", **meta}


def run_report(kb: SemanticKnowledgeBase, tags_df: pd.DataFrame, obras_df: pd.DataFrame) -> Dict[str, Any]:
    reports = {
        "entity_distribution": export_text_report("entity_distribution", report_entity_distribution(kb, tags_df)),
        "lexical_diversity": export_text_report("lexical_diversity", report_lexical_diversity(tags_df, obras_df)),
        "validation_state": export_text_report("validation_state", report_validation_state(kb, tags_df)),
        "concept_gaps": export_text_report("concept_gaps", report_concept_gaps(kb, tags_df)),
    }
    return {"mode": "report", "files": {k: str(v) for k, v in reports.items()}}


def run_snapshot(kb: SemanticKnowledgeBase, tags_df: pd.DataFrame, users_df: pd.DataFrame, obras_df: pd.DataFrame) -> Dict[str, Any]:
    ensure_dir(EXPORT_DIR)
    slug = now_slug()
    tags_path = EXPORT_DIR / f"tags_snapshot_{slug}.csv"
    users_path = EXPORT_DIR / f"users_snapshot_{slug}.csv"
    works_path = EXPORT_DIR / f"works_snapshot_{slug}.csv"
    semantic_path = EXPORT_DIR / f"semantic_snapshot_{slug}.json"
    tags_df.to_csv(tags_path, index=False)
    users_df.to_csv(users_path, index=False)
    obras_df.to_csv(works_path, index=False)
    save_json(semantic_path, {
        "concepts": kb.concept_store,
        "relations": kb.relation_store,
        "validations": kb.validation_store,
        "learning_examples": kb.learning_examples,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    })
    return {
        "mode": "snapshot",
        "tags_csv": str(tags_path),
        "users_csv": str(users_path),
        "works_csv": str(works_path),
        "semantic_json": str(semantic_path),
    }


def run_full(kb: SemanticKnowledgeBase, tags_df: pd.DataFrame, users_df: pd.DataFrame, obras_df: pd.DataFrame) -> Dict[str, Any]:
    payload = {
        "reconcile": run_reconcile(kb, tags_df, obras_df),
        "train": run_train(kb),
        "report": run_report(kb, tags_df, obras_df),
        "snapshot": run_snapshot(kb, tags_df, users_df, obras_df),
    }
    return {"mode": "full", "payload": payload}


def cli() -> None:
    parser = argparse.ArgumentParser(description="Automação do Sistema Folksonomia Digital Inteligente")
    parser.add_argument(
        "--mode",
        default="full",
        choices=["reconcile", "train", "report", "snapshot", "full"],
        help="Modo de execução",
    )
    args = parser.parse_args()

    ensure_dir(DATA_DIR)
    ensure_dir(EXPORT_DIR)
    ensure_dir(REPORT_DIR)

    kb = SemanticKnowledgeBase(DATA_DIR)
    if not kb.concept_store:
        bootstrap_default_concepts(kb)

    obras_df = load_obras_df()
    tags_df = load_tags_df()
    users_df = load_users_df()

    if args.mode == "reconcile":
        result = run_reconcile(kb, tags_df, obras_df)
    elif args.mode == "train":
        result = run_train(kb)
    elif args.mode == "report":
        result = run_report(kb, tags_df, obras_df)
    elif args.mode == "snapshot":
        result = run_snapshot(kb, tags_df, users_df, obras_df)
    else:
        result = run_full(kb, tags_df, users_df, obras_df)

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    cli()
