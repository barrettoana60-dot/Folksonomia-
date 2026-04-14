from __future__ import annotations

import base64
import hashlib
import html
import json
import math
import os
import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

try:
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except Exception:
    PLOTLY_AVAILABLE = False
    go = None

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    REPORTLAB_AVAILABLE = True
except Exception:
    REPORTLAB_AVAILABLE = False

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    SKLEARN_AVAILABLE = True
except Exception:
    SKLEARN_AVAILABLE = False


APP_TITLE = "folksonomia"
APP_DIR = Path("data_folksonomia_stable")
WORKS_FILE = APP_DIR / "works.json"
TAGS_FILE = APP_DIR / "tags.json"
USERS_FILE = APP_DIR / "users.json"
VALIDATIONS_FILE = APP_DIR / "validations.json"
CONCEPTS_FILE = APP_DIR / "concepts.json"
ADMIN_FILE = APP_DIR / "admin.json"

ADMIN_LOGIN = "nugep239@"
ADMIN_PASSWORD = "nugep123"

CATEGORY_OPTIONS = [
    "tema",
    "pessoa",
    "lugar",
    "periodo",
    "material",
    "tecnica",
    "iconografia",
    "evento_historico",
    "grupo_social_cultural",
]

GLOSSARY = {
    "iconografia": "Descrição dos temas, figuras e símbolos representados em uma obra.",
    "interoperabilidade": "Capacidade de diferentes sistemas trocarem dados entre si com sentido preservado.",
    "metadados": "Dados que descrevem outros dados, como título, técnica, material, autor e data.",
    "desambiguação": "Processo de decidir qual significado correto um termo tem em determinado contexto.",
    "ontologia": "Estrutura organizada de conceitos e relações usada para conectar informações.",
    "acervo": "Conjunto de objetos, obras e documentos mantidos por uma instituição.",
    "proveniência": "Histórico de origem, posse e circulação de um objeto ou obra.",
    "periodo": "Recorte temporal associado à obra, ao estilo ou ao contexto histórico.",
    "tecnica": "Modo de produção da obra, como óleo sobre tela, gravura ou escultura.",
    "material": "Substância física empregada na obra, como madeira, tela, bronze ou papel.",
}


def normalize_text(text: Any) -> str:
    text = str(text or "").strip().lower()
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("utf-8")
    text = re.sub(r"[^a-z0-9\s\-_/]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def tokenize(text: Any) -> List[str]:
    text = normalize_text(text)
    return [t for t in text.split(" ") if t]


def uid() -> str:
    return base64.urlsafe_b64encode(os.urandom(9)).decode("utf-8").strip("=")


def now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def safe_int(v: Any, default: int = 0) -> int:
    try:
        return int(v)
    except Exception:
        return default


def sequence_ratio(a: str, b: str) -> float:
    return SequenceMatcher(None, normalize_text(a), normalize_text(b)).ratio()


def tokens_overlap(a: str, b: str) -> float:
    ta, tb = set(tokenize(a)), set(tokenize(b))
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def similar_score(a: str, b: str) -> float:
    return max(sequence_ratio(a, b), tokens_overlap(a, b))


def ensure_dir() -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)


def load_json(path: Path, default: Any) -> Any:
    ensure_dir()
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return default
    return default


def save_json(path: Path, data: Any) -> None:
    ensure_dir()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


@dataclass
class Work:
    id: str
    title: str
    artist: str
    year: str
    image: str
    museum: str
    collection: str
    place: str
    period: str
    technique: str
    material: str
    institution_tags: List[str]
    description: str
    open_data: List[str]


class Store:
    def __init__(self) -> None:
        ensure_dir()
        self.bootstrap()

    def bootstrap(self) -> None:
        if not WORKS_FILE.exists():
            works = [
                Work(
                    id="w1",
                    title="Guernica",
                    artist="Pablo Picasso",
                    year="1937",
                    image="https://upload.wikimedia.org/wikipedia/en/7/74/PicassoGuernica.jpg",
                    museum="Museo Nacional Centro de Arte Reina Sofía",
                    collection="Coleção principal",
                    place="Espanha",
                    period="modernismo do século XX",
                    technique="óleo sobre tela",
                    material="tela",
                    institution_tags=["guerra", "violência", "civis", "bombardeio", "espanha", "modernismo"],
                    description="Grande pintura associada ao bombardeio de Guernica, com figuras humanas, animais e tensão dramática.",
                    open_data=["Wikidata", "Wikipedia", "Reina Sofía"],
                ),
                Work(
                    id="w2",
                    title="A Noite Estrelada",
                    artist="Vincent van Gogh",
                    year="1889",
                    image="https://upload.wikimedia.org/wikipedia/commons/e/ea/The_Starry_Night.JPG",
                    museum="The Museum of Modern Art",
                    collection="European Painting",
                    place="França",
                    period="pós-impressionismo",
                    technique="óleo sobre tela",
                    material="tela",
                    institution_tags=["céu", "noite", "estrelas", "vila", "paisagem", "expressividade"],
                    description="Paisagem noturna com céu em movimento, estrelas brilhantes e pequena vila ao fundo.",
                    open_data=["Wikidata", "Wikipedia", "MoMA"],
                ),
                Work(
                    id="w3",
                    title="Mona Lisa",
                    artist="Leonardo da Vinci",
                    year="1503",
                    image="https://upload.wikimedia.org/wikipedia/commons/6/6a/Mona_Lisa.jpg",
                    museum="Musée du Louvre",
                    collection="Renaissance",
                    place="Itália",
                    period="renascimento",
                    technique="óleo sobre madeira",
                    material="madeira",
                    institution_tags=["retrato", "mulher", "sorriso", "renascimento", "paisagem"],
                    description="Retrato feminino célebre pela expressão do rosto, pela composição e pela paisagem ao fundo.",
                    open_data=["Wikidata", "Wikipedia", "Louvre"],
                ),
            ]
            save_json(WORKS_FILE, [w.__dict__ for w in works])

        if not CONCEPTS_FILE.exists():
            concepts = [
                {"id": "c1", "label": "guerra", "category": "tema", "aliases": ["conflito", "bombardeio"]},
                {"id": "c2", "label": "violência", "category": "tema", "aliases": ["dor", "sofrimento"]},
                {"id": "c3", "label": "paisagem", "category": "tema", "aliases": ["cenário", "vista"]},
                {"id": "c4", "label": "estrelas", "category": "iconografia", "aliases": ["astro", "céu estrelado"]},
                {"id": "c5", "label": "retrato", "category": "iconografia", "aliases": ["figura humana"]},
                {"id": "c6", "label": "Pablo Picasso", "category": "pessoa", "aliases": ["picasso"]},
                {"id": "c7", "label": "Vincent van Gogh", "category": "pessoa", "aliases": ["van gogh", "vincent"]},
                {"id": "c8", "label": "Leonardo da Vinci", "category": "pessoa", "aliases": ["da vinci", "leonardo"]},
                {"id": "c9", "label": "Espanha", "category": "lugar", "aliases": ["espanha republicana"]},
                {"id": "c10", "label": "pós-impressionismo", "category": "periodo", "aliases": ["pos impressionismo"]},
                {"id": "c11", "label": "óleo sobre tela", "category": "tecnica", "aliases": ["oleo sobre tela"]},
                {"id": "c12", "label": "madeira", "category": "material", "aliases": ["painel de madeira"]},
            ]
            save_json(CONCEPTS_FILE, concepts)

        if not TAGS_FILE.exists():
            save_json(TAGS_FILE, [])
        if not USERS_FILE.exists():
            save_json(USERS_FILE, [])
        if not VALIDATIONS_FILE.exists():
            save_json(VALIDATIONS_FILE, [])
        if not ADMIN_FILE.exists():
            save_json(
                ADMIN_FILE,
                {
                    "login": ADMIN_LOGIN,
                    "password_hash": hashlib.sha256(ADMIN_PASSWORD.encode()).hexdigest(),
                },
            )

    def works(self) -> List[Dict[str, Any]]:
        rows = load_json(WORKS_FILE, [])
        clean = []
        for row in rows:
            row = dict(row)
            row["institution_tags"] = list(row.get("institution_tags", []))
            row["open_data"] = list(row.get("open_data", []))
            clean.append(row)
        return clean

    def tags(self) -> List[Dict[str, Any]]:
        rows = load_json(TAGS_FILE, [])
        clean = []
        for row in rows:
            row = dict(row)
            row.setdefault("id", uid())
            row.setdefault("created_at", now_iso())
            row.setdefault("user_id", "")
            row.setdefault("work_id", "")
            row.setdefault("tag", "")
            clean.append(row)
        return clean

    def users(self) -> List[Dict[str, Any]]:
        rows = load_json(USERS_FILE, [])
        clean = []
        for row in rows:
            row = dict(row)
            row.setdefault("id", row.get("user_id", uid()))
            row.setdefault("created_at", now_iso())
            clean.append(row)
        return clean

    def validations(self) -> List[Dict[str, Any]]:
        rows = load_json(VALIDATIONS_FILE, [])
        clean = []
        for row in rows:
            row = dict(row)
            row.setdefault("id", uid())
            row.setdefault("tag_id", "")
            row.setdefault("decision", "pending")
            row.setdefault("category", "")
            row.setdefault("concept_id", "")
            row.setdefault("notes", "")
            row.setdefault("created_at", now_iso())
            clean.append(row)
        return clean

    def concepts(self) -> List[Dict[str, Any]]:
        rows = load_json(CONCEPTS_FILE, [])
        clean = []
        for row in rows:
            row = dict(row)
            row.setdefault("aliases", [])
            clean.append(row)
        return clean

    def save_tags(self, rows: List[Dict[str, Any]]) -> None:
        save_json(TAGS_FILE, rows)

    def save_users(self, rows: List[Dict[str, Any]]) -> None:
        save_json(USERS_FILE, rows)

    def save_validations(self, rows: List[Dict[str, Any]]) -> None:
        save_json(VALIDATIONS_FILE, rows)

    def save_works(self, rows: List[Dict[str, Any]]) -> None:
        save_json(WORKS_FILE, rows)

    def admin_ok(self, login: str, password: str) -> bool:
        admin = load_json(ADMIN_FILE, {})
        typed_hash = hashlib.sha256(password.encode()).hexdigest()
        stored_hash = admin.get("password_hash", "")
        stored_login = admin.get("login", ADMIN_LOGIN)
        if login == ADMIN_LOGIN and password == ADMIN_PASSWORD:
            if stored_login != ADMIN_LOGIN or stored_hash != typed_hash:
                save_json(ADMIN_FILE, {"login": ADMIN_LOGIN, "password_hash": typed_hash})
            return True
        return login == stored_login and typed_hash == stored_hash

    def add_user_response(self, payload: Dict[str, Any]) -> str:
        rows = self.users()
        user_id = payload.get("id") or uid()
        payload = dict(payload)
        payload["id"] = user_id
        payload["created_at"] = now_iso()
        rows = [r for r in rows if r.get("id") != user_id]
        rows.append(payload)
        self.save_users(rows)
        return user_id

    def add_tag(self, payload: Dict[str, Any]) -> None:
        rows = self.tags()
        row = dict(payload)
        row["id"] = uid()
        row["created_at"] = now_iso()
        rows.append(row)
        self.save_tags(rows)

    def add_validation(self, payload: Dict[str, Any]) -> None:
        rows = self.validations()
        tag_id = payload.get("tag_id", "")
        rows = [r for r in rows if r.get("tag_id") != tag_id]
        row = dict(payload)
        row["id"] = uid()
        row["created_at"] = now_iso()
        rows.append(row)
        self.save_validations(rows)


def user_record(store: Store, user_id: str) -> Optional[Dict[str, Any]]:
    for row in store.users():
        if row.get("id") == user_id:
            return row
    return None


def work_by_id(store: Store, work_id: str) -> Optional[Dict[str, Any]]:
    for row in store.works():
        if row.get("id") == work_id:
            return row
    return None


def tags_df(store: Store) -> pd.DataFrame:
    return pd.DataFrame(store.tags())


def validations_df(store: Store) -> pd.DataFrame:
    return pd.DataFrame(store.validations())


def combined_work_text(work: Dict[str, Any]) -> str:
    parts = [
        work.get("title", ""),
        work.get("artist", ""),
        work.get("museum", ""),
        work.get("collection", ""),
        work.get("place", ""),
        work.get("period", ""),
        work.get("technique", ""),
        work.get("material", ""),
        work.get("description", ""),
        " ".join(work.get("institution_tags", [])),
        " ".join(work.get("open_data", [])),
    ]
    return " ".join([str(p) for p in parts if p])


def concept_lookup(store: Store) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, str]]:
    by_id = {}
    alias_to_id = {}
    for c in store.concepts():
        by_id[c["id"]] = c
        alias_to_id[normalize_text(c["label"])] = c["id"]
        for alias in c.get("aliases", []):
            alias_to_id[normalize_text(alias)] = c["id"]
    return by_id, alias_to_id


def build_learning_examples(store: Store) -> pd.DataFrame:
    works = {w["id"]: w for w in store.works()}
    vals = store.validations()
    concepts_by_id, _ = concept_lookup(store)

    examples = []
    for val in vals:
        if val.get("decision") != "approved":
            continue
        tag_obj = next((t for t in store.tags() if t.get("id") == val.get("tag_id")), None)
        if not tag_obj:
            continue
        work = works.get(tag_obj.get("work_id"))
        if not work:
            continue
        concept = concepts_by_id.get(val.get("concept_id", ""))
        text = f"{tag_obj.get('tag','')} {combined_work_text(work)}"
        examples.append(
            {
                "text": text,
                "tag": tag_obj.get("tag", ""),
                "category": val.get("category", ""),
                "concept_label": concept.get("label", "") if concept else "",
                "work_id": work.get("id"),
            }
        )

    # Seed examples from institutional tags and concepts to start learning
    for work in store.works():
        meta_map = [
            (work.get("artist", ""), "pessoa"),
            (work.get("place", ""), "lugar"),
            (work.get("period", ""), "periodo"),
            (work.get("technique", ""), "tecnica"),
            (work.get("material", ""), "material"),
        ]
        for label, category in meta_map:
            if not label:
                continue
            examples.append(
                {
                    "text": f"{label} {combined_work_text(work)}",
                    "tag": label,
                    "category": category,
                    "concept_label": label,
                    "work_id": work.get("id"),
                }
            )
        for tag in work.get("institution_tags", []):
            examples.append(
                {
                    "text": f"{tag} {combined_work_text(work)}",
                    "tag": tag,
                    "category": "tema",
                    "concept_label": tag,
                    "work_id": work.get("id"),
                }
            )
    df = pd.DataFrame(examples)
    if df.empty:
        return pd.DataFrame(columns=["text", "tag", "category", "concept_label", "work_id"])
    return df


def heuristic_category(tag: str, work: Dict[str, Any]) -> str:
    t = normalize_text(tag)
    if normalize_text(work.get("artist")) in t or t in normalize_text(work.get("artist")):
        return "pessoa"
    if any(tok in t for tok in ["renascimento", "barroco", "modernismo", "impressionismo", "seculo", "século"]):
        return "periodo"
    if any(tok in t for tok in ["oleo", "óleo", "tinta", "gravura", "aquarela"]):
        return "tecnica"
    if any(tok in t for tok in ["madeira", "bronze", "tela", "papel", "pedra"]):
        return "material"
    if any(tok in t for tok in ["espanha", "franca", "frança", "italia", "itália", "paris"]):
        return "lugar"
    return "tema"


def predict_tag(store: Store, tag: str, work: Dict[str, Any]) -> Dict[str, Any]:
    tag = str(tag).strip()
    _, alias_to_id = concept_lookup(store)
    concepts_by_id, _ = concept_lookup(store)

    direct_id = alias_to_id.get(normalize_text(tag))
    if direct_id:
        c = concepts_by_id[direct_id]
        return {
            "category": c.get("category", "tema"),
            "concept_id": c["id"],
            "concept_label": c["label"],
            "confidence": 0.96,
            "source": "conceito_existente",
        }

    examples = build_learning_examples(store)
    predicted_category = heuristic_category(tag, work)
    confidence = 0.55
    concept_id = ""
    concept_label = ""

    if SKLEARN_AVAILABLE and len(examples) >= 12 and examples["category"].nunique() >= 2:
        try:
            vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1)
            X = vectorizer.fit_transform(examples["text"].astype(str))
            model = LogisticRegression(max_iter=600)
            model.fit(X, examples["category"].astype(str))
            query = f"{tag} {combined_work_text(work)}"
            qx = vectorizer.transform([query])
            probs = model.predict_proba(qx)[0]
            labels = list(model.classes_)
            best_idx = int(np.argmax(probs))
            predicted_category = labels[best_idx]
            confidence = float(probs[best_idx])
        except Exception:
            pass

    # Reconcile concept by nearest existing concept label
    best = ("", 0.0, "")
    for c in store.concepts():
        values = [c.get("label", "")] + list(c.get("aliases", []))
        for label in values:
            score = similar_score(tag, label)
            if predicted_category == c.get("category"):
                score += 0.08
            if score > best[1]:
                best = (c["id"], score, c["label"])
    if best[1] >= 0.58:
        concept_id, concept_label = best[0], best[2]
        confidence = max(confidence, min(0.93, best[1]))

    return {
        "category": predicted_category,
        "concept_id": concept_id,
        "concept_label": concept_label,
        "confidence": round(float(confidence), 2),
        "source": "aprendizagem" if confidence > 0.6 else "heuristica",
    }


def suggestions_for_tag(store: Store, tag: str, work_id: str) -> Dict[str, Any]:
    tag = str(tag).strip()
    all_tags = store.tags()
    works = {w["id"]: w for w in store.works()}
    same_or_close = []
    for row in all_tags:
        if not row.get("tag"):
            continue
        score = similar_score(tag, row.get("tag", ""))
        if score >= 0.55:
            work = works.get(row.get("work_id"), {})
            same_or_close.append(
                {
                    "tag": row.get("tag", ""),
                    "work_title": work.get("title", ""),
                    "score": round(score, 2),
                }
            )
    same_or_close = sorted(same_or_close, key=lambda x: x["score"], reverse=True)[:8]

    concept_candidates = []
    for c in store.concepts():
        score = similar_score(tag, c.get("label", ""))
        if score >= 0.42:
            concept_candidates.append(
                {
                    "label": c.get("label", ""),
                    "category": c.get("category", ""),
                    "score": round(score, 2),
                }
            )
    concept_candidates = sorted(concept_candidates, key=lambda x: x["score"], reverse=True)[:5]

    examples = []
    df = tags_df(store)
    if not df.empty:
        for _, row in df.iterrows():
            score = similar_score(tag, row["tag"])
            if score >= 0.4:
                w = works.get(row["work_id"], {})
                examples.append(
                    {
                        "tag": row["tag"],
                        "obra": w.get("title", ""),
                        "score": round(score, 2),
                    }
                )
        examples = sorted(examples, key=lambda x: x["score"], reverse=True)[:3]

    conflicts = []
    vals = validations_df(store)
    if not df.empty and not vals.empty:
        merged = df.merge(vals, left_on="id", right_on="tag_id", how="inner")
        same_norm = merged[merged["tag"].astype(str).apply(lambda x: normalize_text(x) == normalize_text(tag))]
        if not same_norm.empty and same_norm["concept_id"].astype(str).nunique() > 1:
            conflicts.append("A mesma grafia já apareceu ligada a conceitos diferentes em registros anteriores.")
        if not same_norm.empty and same_norm["category"].astype(str).nunique() > 1:
            conflicts.append("A mesma grafia já apareceu com categorias diferentes e merece revisão humana.")

    return {
        "similar_tags": same_or_close,
        "concept_candidates": concept_candidates,
        "examples": examples,
        "conflicts": conflicts,
    }


def real_search(store: Store, query: str) -> List[Dict[str, Any]]:
    query = str(query).strip()
    if not query:
        return []
    q_tokens = set(tokenize(query))
    concepts_by_id, alias_to_id = concept_lookup(store)
    vals = {v["tag_id"]: v for v in store.validations() if v.get("decision") == "approved"}
    results = []

    for work in store.works():
        combined = combined_work_text(work)
        w_tokens = set(tokenize(combined))
        base = len(q_tokens & w_tokens) / max(1, len(q_tokens))
        score = base
        matched_tags = []
        matched_concepts = []
        for tag in store.tags():
            if tag.get("work_id") != work.get("id"):
                continue
            tag_norm = normalize_text(tag.get("tag", ""))
            if tag_norm in normalize_text(query) or normalize_text(query) in tag_norm or tokens_overlap(query, tag.get("tag", "")) > 0:
                score += 0.35
                matched_tags.append(tag.get("tag", ""))
            v = vals.get(tag.get("id"))
            if v and v.get("concept_id"):
                concept = concepts_by_id.get(v["concept_id"])
                if concept and (tokens_overlap(query, concept["label"]) > 0 or normalize_text(concept["label"]) in normalize_text(query)):
                    score += 0.3
                    matched_concepts.append(concept["label"])
        if score > 0:
            results.append(
                {
                    "work_id": work["id"],
                    "title": work["title"],
                    "artist": work["artist"],
                    "museum": work["museum"],
                    "score": round(score, 2),
                    "matched_tags": sorted(set(matched_tags)),
                    "matched_concepts": sorted(set(matched_concepts)),
                    "matched_metadata": [t for t in q_tokens if t in w_tokens],
                }
            )

    return sorted(results, key=lambda x: x["score"], reverse=True)[:20]


def build_temporal_summary(store: Store) -> Dict[str, Any]:
    df = tags_df(store)
    works = {w["id"]: w["title"] for w in store.works()}
    if df.empty:
        return {
            "by_day": [],
            "by_month": [],
            "by_year": [],
        }
    df["created_at_dt"] = pd.to_datetime(df["created_at"], errors="coerce")
    df = df.dropna(subset=["created_at_dt"]).copy()
    df["day"] = df["created_at_dt"].dt.strftime("%Y-%m-%d")
    df["month"] = df["created_at_dt"].dt.strftime("%Y-%m")
    df["year"] = df["created_at_dt"].dt.strftime("%Y")

    def detail_group(frame: pd.DataFrame, col: str) -> List[Dict[str, Any]]:
        out = []
        for bucket, sub in frame.groupby(col):
            out.append(
                {
                    "period": str(bucket),
                    "count": int(len(sub)),
                    "unique_tags": sorted(sub["tag"].astype(str).str.lower().unique().tolist()),
                    "works": sorted({works.get(wid, "") for wid in sub["work_id"].tolist() if works.get(wid, "")}),
                }
            )
        out.sort(key=lambda x: x["period"])
        return out

    return {
        "by_day": detail_group(df, "day"),
        "by_month": detail_group(df, "month"),
        "by_year": detail_group(df, "year"),
    }


def connectivity_report(store: Store) -> Dict[str, Any]:
    works = store.works()
    tags = store.tags()
    vals = {v["tag_id"]: v for v in store.validations() if v.get("decision") == "approved"}
    concepts_by_id, _ = concept_lookup(store)

    collection_output = {
        "obras_monitoradas": len(works),
        "tags_coletadas": len(tags),
        "validacoes_concluidas": len(vals),
        "fila_curatorial": max(0, len(tags) - len(vals)),
    }

    by_work = []
    for work in works:
        work_tags = [t for t in tags if t.get("work_id") == work["id"]]
        normalized = [normalize_text(t["tag"]) for t in work_tags if t.get("tag")]
        repeated = [k for k, v in Counter(normalized).items() if v > 1]
        completion_fields = ["artist", "museum", "collection", "place", "period", "technique", "material", "description"]
        completed = sum(1 for f in completion_fields if str(work.get(f, "")).strip())
        balance = round(completed / len(completion_fields), 2)
        by_work.append(
            {
                "work_id": work["id"],
                "title": work["title"],
                "tags": len(work_tags),
                "tags_unicas": len(set(normalized)),
                "repetidas": repeated,
                "preenchimento": balance,
            }
        )

    confusion = []
    df = tags_df(store)
    if not df.empty:
        for tag_norm, sub in df.assign(tag_norm=df["tag"].astype(str).apply(normalize_text)).groupby("tag_norm"):
            works_here = sub["work_id"].nunique()
            if works_here > 1:
                confusion.append(
                    {
                        "tag": tag_norm,
                        "works_count": int(works_here),
                        "total_count": int(len(sub)),
                    }
                )
    confusion = sorted(confusion, key=lambda x: (x["works_count"], x["total_count"]), reverse=True)

    links = []
    for work in works:
        current_tags = [t for t in tags if t.get("work_id") == work["id"]]
        for tag in current_tags:
            v = vals.get(tag.get("id"))
            concept = concepts_by_id.get(v.get("concept_id")) if v else None
            links.append(
                {
                    "work": work["title"],
                    "tag": tag.get("tag", ""),
                    "concept": concept.get("label", "") if concept else "",
                    "category": v.get("category", "") if v else "",
                }
            )
    return {
        "collection_output": collection_output,
        "by_work": by_work,
        "confusion": confusion[:20],
        "links": links,
    }


def build_3d_network(store: Store) -> Optional[Any]:
    if not PLOTLY_AVAILABLE:
        return None

    works = store.works()
    tags = store.tags()
    vals = {v["tag_id"]: v for v in store.validations() if v.get("decision") == "approved"}
    concepts_by_id, _ = concept_lookup(store)

    nodes = []
    edges = []

    def add_node(key: str, label: str, ntype: str) -> None:
        if key not in {n["key"] for n in nodes}:
            nodes.append({"key": key, "label": label, "type": ntype})

    def add_edge(a: str, b: str) -> None:
        edges.append((a, b))

    for work in works:
        wk = f"work:{work['id']}"
        add_node(wk, work["title"], "obra")
        for f, prefix, ntype in [
            ("artist", "artist", "artista"),
            ("museum", "museum", "museu"),
            ("collection", "collection", "colecao"),
            ("place", "place", "lugar"),
            ("period", "period", "periodo"),
            ("technique", "tech", "tecnica"),
            ("material", "material", "material"),
        ]:
            val = str(work.get(f, "")).strip()
            if val:
                key = f"{prefix}:{normalize_text(val)}"
                add_node(key, val, ntype)
                add_edge(wk, key)
        for tag in work.get("institution_tags", []):
            key = f"it:{normalize_text(tag)}"
            add_node(key, tag, "tag_institucional")
            add_edge(wk, key)
        for od in work.get("open_data", []):
            key = f"od:{normalize_text(od)}"
            add_node(key, od, "open_data")
            add_edge(wk, key)

    for tag in tags:
        label = str(tag.get("tag", "")).strip()
        if not label:
            continue
        key = f"pt:{normalize_text(label)}:{tag.get('id')}"
        add_node(key, label, "tag_publica")
        add_edge(f"work:{tag.get('work_id')}", key)
        v = vals.get(tag.get("id"))
        if v and v.get("concept_id"):
            concept = concepts_by_id.get(v["concept_id"])
            if concept:
                ckey = f"concept:{concept['id']}"
                add_node(ckey, concept["label"], "conceito")
                add_edge(key, ckey)

    type_order = {
        "obra": 0,
        "artista": 1,
        "museu": 2,
        "colecao": 3,
        "lugar": 4,
        "periodo": 5,
        "tecnica": 6,
        "material": 7,
        "tag_institucional": 8,
        "tag_publica": 9,
        "conceito": 10,
        "open_data": 11,
    }

    palette = {
        "obra": "#111827",
        "artista": "#7c3aed",
        "museu": "#2563eb",
        "colecao": "#14b8a6",
        "lugar": "#0891b2",
        "periodo": "#db2777",
        "tecnica": "#ea580c",
        "material": "#65a30d",
        "tag_institucional": "#f59e0b",
        "tag_publica": "#0f766e",
        "conceito": "#dc2626",
        "open_data": "#64748b",
    }

    # deterministic radial 3d layout
    typed = defaultdict(list)
    for node in nodes:
        typed[node["type"]].append(node)

    coords = {}
    layer_gap = 2.2
    for ntype, group in typed.items():
        layer = type_order.get(ntype, 0)
        radius = 2.3 + layer * 0.55
        z = (layer - 5) * 0.8
        n = max(1, len(group))
        for i, node in enumerate(group):
            angle = 2 * math.pi * (i / n)
            x = radius * math.cos(angle)
            y = radius * math.sin(angle)
            coords[node["key"]] = (x, y, z)

    edge_x, edge_y, edge_z = [], [], []
    for a, b in edges:
        if a not in coords or b not in coords:
            continue
        xa, ya, za = coords[a]
        xb, yb, zb = coords[b]
        edge_x.extend([xa, xb, None])
        edge_y.extend([ya, yb, None])
        edge_z.extend([za, zb, None])

    edge_trace = go.Scatter3d(
        x=edge_x,
        y=edge_y,
        z=edge_z,
        mode="lines",
        line=dict(color="rgba(80,80,100,0.35)", width=3),
        hoverinfo="none",
    )

    traces = [edge_trace]
    for ntype, group in typed.items():
        xs, ys, zs, text = [], [], [], []
        for node in group:
            x, y, z = coords[node["key"]]
            xs.append(x)
            ys.append(y)
            zs.append(z)
            text.append(node["label"])
        traces.append(
            go.Scatter3d(
                x=xs,
                y=ys,
                z=zs,
                mode="markers+text",
                text=text,
                textposition="top center",
                marker=dict(size=8, color=palette.get(ntype, "#334155")),
                name=ntype.replace("_", " "),
                hovertemplate="%{text}<extra></extra>",
            )
        )

    fig = go.Figure(data=traces)
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(255,255,255,0)",
        plot_bgcolor="rgba(255,255,255,0)",
        scene=dict(
            xaxis=dict(visible=False, showbackground=False),
            yaxis=dict(visible=False, showbackground=False),
            zaxis=dict(visible=False, showbackground=False),
            bgcolor="rgba(255,255,255,0)",
            camera=dict(eye=dict(x=1.8, y=1.6, z=1.25)),
        ),
        legend=dict(orientation="h"),
        height=760,
    )
    return fig


def explanation_terms(text: str) -> List[Tuple[str, str]]:
    seen = []
    normalized_text = normalize_text(text)
    for term, meaning in GLOSSARY.items():
        if normalize_text(term) in normalized_text:
            seen.append((term, meaning))
    return seen


def detailed_visual_summary(work: Dict[str, Any]) -> str:
    title = normalize_text(work.get("title", ""))
    custom = {
        "guernica": "Em preto, branco e cinza, a composição apresenta figuras humanas e animais fragmentados. Um touro aparece à esquerda. No centro há um cavalo em tensão, com o corpo cortado por linhas agudas. Rostos, braços e bocas abertas sugerem grito, medo e movimento. À direita, figuras erguidas e inclinadas reforçam a sensação de tragédia e bombardeio.",
        "a noite estrelada": "A cena mostra um céu noturno azul intenso com grandes espirais luminosas. Estrelas circulares e a lua amarela brilham acima de uma pequena vila. Um cipreste escuro sobe em primeiro plano, criando contraste forte com o céu em movimento.",
        "mona lisa": "A imagem mostra uma mulher sentada, vista de frente, com mãos cruzadas. O rosto tem expressão serena e sorriso discreto. Ao fundo aparece uma paisagem com caminhos, água e montanhas em profundidade."
    }
    if title in custom:
        return custom[title]
    return str(work.get("description", "")).strip()

def make_audio_description(work: Dict[str, Any], user_tags: List[str]) -> str:
    title = work.get('title', 'obra sem título')
    artist = work.get('artist', 'artista não identificado')
    museum = work.get('museum', 'museu não informado')
    period = work.get('period', 'período não informado')
    technique = work.get('technique', 'técnica não informada')
    material = work.get('material', 'material não informado')
    place = work.get('place', 'local não informado')
    visual = detailed_visual_summary(work)
    tags_part = ', '.join(user_tags[:8]) if user_tags else 'sem tags registradas por você nesta imagem até o momento'
    return (
        f'Áudio descrição da obra {title}, de {artist}. '
        f'Instituição: {museum}. Contexto: {period}, em {place}. '
        f'Técnica: {technique}, material: {material}. '
        f'Leitura visual detalhada: {visual}. '
        f'Tags registradas por você nesta imagem: {tags_part}.'
    )



def simplified_text(work: Dict[str, Any]) -> str:
    return (
        f"Esta imagem mostra a obra {work.get('title','')}. "
        f"Ela foi criada por {work.get('artist','')}. "
        f"O museu responsável é {work.get('museum','')}. "
        f"A obra se relaciona com {work.get('period','')} e usa {work.get('technique','')} sobre {work.get('material','')}. "
        f"O principal conteúdo visual descrito é: {work.get('description','')}."
    )


def init_session() -> None:
    defaults = {
        "current_user_id": "",
        "intro_done": False,
        "selected_work_id": "",
        "admin_logged": False,
        "font_scale": 1.0,
        "high_contrast": False,
        "accessibility_work_id": "",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def inject_css() -> None:
    font_px = int(17 * float(st.session_state.get("font_scale", 1.0)))
    contrast = st.session_state.get("high_contrast", False)
    text = "#101418" if contrast else "#222222"
    subtitle = "#4b5563" if contrast else "#5b5b5b"
    border = "rgba(20,20,30,0.10)" if not contrast else "rgba(0,0,0,0.28)"
    button_bg = "linear-gradient(135deg,#071225,#0b1730)"
    panel = "rgba(255,255,255,0.52)" if not contrast else "rgba(255,255,255,0.68)"
    st.markdown(
        f"""
        <style>
        :root {{
            --fontSize: {font_px}px;
            --textMain: {text};
            --textSub: {subtitle};
            --panel: {panel};
            --borderGlass: {border};
            --buttonBg: {button_bg};
        }}
        html, body, [data-testid="stAppViewContainer"], .stApp {{
            background: radial-gradient(circle at top, #efefef 0%, #ececec 36%, #e7e7e7 100%);
            color: var(--textMain);
            font-family: "Times New Roman", Georgia, serif;
            font-size: var(--fontSize);
        }}
        #MainMenu, header, footer {{
            visibility: hidden;
        }}
        .block-container {{
            max-width: 1280px;
            padding-top: 1.3rem;
            padding-bottom: 3rem;
        }}
        .glass {{
            background: var(--panel);
            border: 1px solid var(--borderGlass);
            border-radius: 28px;
            box-shadow: 0 12px 42px rgba(255,255,255,0.32) inset, 0 10px 30px rgba(0,0,0,0.04);
            backdrop-filter: blur(20px);
        }}
        .brand {{
            padding: 1.1rem 1.35rem;
            margin-bottom: 0.6rem;
            display:flex;
            align-items:center;
            justify-content:space-between;
            gap:1rem;
        }}
        .brand h1 {{
            margin: 0;
            font-size: clamp(2.2rem, 4vw, 3.3rem);
            line-height: 1;
            color: var(--textMain);
        }}
        .brand .mini {{
            color: var(--textSub);
            font-size: .95rem;
        }}
        .helper {{
            color: var(--textSub);
            line-height: 1.7;
        }}
        .metricCard {{
            padding: 1rem 1.15rem;
            min-height: 118px;
        }}
        .metricTop {{
            color: var(--textSub);
            text-transform: uppercase;
            letter-spacing: .14em;
            font-size: .86rem;
        }}
        .metricValue {{
            font-size: 2.25rem;
            margin-top: .3rem;
            font-weight: 700;
            color: var(--textMain);
        }}
        .metricNote {{
            color: var(--textSub);
            margin-top: .25rem;
        }}
        .sectionTitle {{
            font-size: 2rem;
            font-weight: 700;
            margin: .2rem 0 .7rem 0;
            color: var(--textMain);
        }}
        .subTitle {{
            color: var(--textSub);
            margin-top: 0;
            line-height: 1.7;
        }}
        .workCard {{
            padding: 0.7rem;
            margin-bottom: 1.2rem;
        }}
        .workCard img {{
            width: 100%;
            height: auto;
            border-radius: 20px;
            display:block;
        }}
        .smallPanel {{
            padding: .95rem 1rem;
            margin-top: .65rem;
        }}
        .tagPill {{
            display:inline-block;
            padding:.24rem .7rem;
            margin:.1rem .2rem .1rem 0;
            border-radius:999px;
            background:rgba(255,255,255,0.58);
            border:1px solid var(--borderGlass);
            color:var(--textMain);
            font-size:.95rem;
        }}
        .stButton>button, div[data-testid="stFormSubmitButton"] button {{
            width:100%;
            opacity: 1 !important;
            border-radius: 22px !important;
            background: var(--buttonBg) !important;
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
            border: 1px solid rgba(255,255,255,.14) !important;
            padding: .85rem 1rem !important;
            font-size: 1.08rem !important;
            font-weight: 700 !important;
            text-shadow: 0 1px 2px rgba(0,0,0,.35) !important;
            box-shadow: 0 6px 18px rgba(0,0,0,.18) !important;
        }}
        .stButton>button:hover, div[data-testid="stFormSubmitButton"] button:hover {{
            filter: brightness(1.06);
            transform: translateY(-1px);
        }}
        .stTextInput input, .stTextArea textarea, .stSelectbox [data-baseweb="select"] > div {{
            background: rgba(255,255,255,0.82) !important;
            color: var(--textMain) !important;
            border: 1px solid rgba(25,25,35,.18) !important;
            border-radius: 18px !important;
        }}
        textarea::placeholder, input::placeholder {{
            color: #6b7280 !important;
            opacity: 1 !important;
        }}
        .stTabs [data-baseweb="tab-list"] {{
            gap: .45rem;
            background: rgba(255,255,255,0.28);
            border-radius: 26px;
            padding: .35rem;
            border: 1px solid var(--borderGlass);
        }}
        .stTabs [data-baseweb="tab"] {{
            border-radius: 20px;
            padding: .7rem 1rem;
            color: var(--textMain);
        }}
        .stTabs [aria-selected="true"] {{
            background: rgba(255,255,255,0.62) !important;
            box-shadow: inset 0 -3px 0 #ef4444;
        }}
        .noteBox {{
            padding:1rem 1.1rem;
            line-height:1.75;
        }}
        .inlineAudio button {{
            margin-right: .5rem;
        }}
        .divider {{
            height:1px;
            background: rgba(15,23,42,.08);
            margin: .8rem 0 1rem 0;
        }}
        .smallLabel {{
            color: var(--textSub);
            font-size: .94rem;
        }}
        label, .stTextInput label, .stTextArea label, .stSelectbox label, .stSlider label, .stToggle label {{
            color: var(--textMain) !important;
            font-family: "Times New Roman", Georgia, serif !important;
        }}
        div[data-testid="stMarkdownContainer"] p,
        div[data-testid="stMarkdownContainer"] li,
        div[data-testid="stMarkdownContainer"] span,
        div[data-testid="stMarkdownContainer"] strong,
        div[data-testid="stMarkdownContainer"] em {{
            color: var(--textMain) !important;
        }}
        .accessSideButton button {{
            margin-top: .6rem;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_brand() -> None:
    st.markdown(
        """
        <div class="glass noteBox" style="padding:1rem 1.2rem; margin-bottom:.9rem;">
            <div style="font-family:'Times New Roman', Georgia, serif; font-size:2.5rem; font-weight:700; color:var(--textMain); line-height:1;">folksonomia</div>
            <div class="subTitle" style="margin-top:.35rem;">marque as obras livremente e use a área administrativa para validação, busca conectada, temporalidade e teia 3d.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_questionnaire(store: Store) -> None:
    st.markdown(
        """
        <div class="glass noteBox">
            <div class="sectionTitle">questionário inicial</div>
            <p class="subTitle">Responda às três perguntas para liberar a marcação das imagens.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    familiarity = st.selectbox(
        "1. qual é a sua frequência de visita a museus?",
        ["nunca", "raramente", "ocasionalmente", "frequentemente"],
        key="intro_familiarity",
    )
    documentation = st.selectbox(
        "2. você já ouviu falar sobre documentação museológica?",
        ["nenhum", "já ouvi falar", "tenho noção básica", "conheço bem"],
        key="intro_documentation",
    )
    understanding = st.text_area(
        "3. o que você entende por tags aplicadas a acervos?",
        key="intro_understanding",
        placeholder="descreva com suas palavras",
        height=180,
    )

    if st.button("liberar acesso às obras", key="intro_unlock"):
        if not understanding.strip():
            st.warning("Preencha a terceira resposta para continuar.")
            return
        user_id = st.session_state.get("current_user_id") or uid()
        st.session_state["current_user_id"] = store.add_user_response(
            {
                "id": user_id,
                "familiarity": familiarity,
                "documentation": documentation,
                "understanding": understanding.strip(),
            }
        )
        st.session_state["intro_done"] = True
        st.rerun()


def ensure_user(store: Store) -> str:
    if not st.session_state.get("current_user_id"):
        st.session_state["current_user_id"] = uid()
    if st.session_state.get("intro_done") and not user_record(store, st.session_state["current_user_id"]):
        st.session_state["intro_done"] = False
    return st.session_state["current_user_id"]



def render_accessibility_controls(work: Dict[str, Any], user_tags: List[str]) -> None:
    st.markdown('<div class="glass smallPanel">', unsafe_allow_html=True)
    st.markdown("### acessibilidade da imagem")
    font_scale = st.slider(
        "tamanho da fonte",
        0.85,
        1.6,
        float(st.session_state.get("font_scale", 1.0)),
        0.05,
        key=f"font_scale_{work['id']}",
    )
    contrast = st.toggle(
        "contraste reforçado",
        value=bool(st.session_state.get("high_contrast", False)),
        key=f"contrast_{work['id']}",
    )
    if font_scale != st.session_state.get("font_scale"):
        st.session_state["font_scale"] = font_scale
        st.rerun()
    if contrast != st.session_state.get("high_contrast"):
        st.session_state["high_contrast"] = contrast
        st.rerun()

    desc = make_audio_description(work, user_tags)
    simple = simplified_text(work)
    glossary_hits = explanation_terms(" ".join([desc, simple, combined_work_text(work)]))

    st.markdown('<div class="smallLabel">interpretação textual</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="glass noteBox">{html.escape(simple)}</div>', unsafe_allow_html=True)

    escaped = json.dumps(desc)
    components.html(
        f"""
        <div class="inlineAudio">
            <button onclick='window.speechSynthesis.cancel(); let u = new SpeechSynthesisUtterance({escaped}); u.lang="pt-BR"; u.rate=1; u.pitch=1; speechSynthesis.speak(u);'>ouvir descrição</button>
            <button onclick='window.speechSynthesis.cancel();'>parar leitura</button>
        </div>
        """,
        height=54,
    )

    st.markdown('<div class="smallLabel">explicação de palavras</div>', unsafe_allow_html=True)
    if glossary_hits:
        for term, meaning in glossary_hits:
            st.markdown(
                f'<div class="glass noteBox"><strong>{html.escape(term)}</strong><br>{html.escape(meaning)}</div>',
                unsafe_allow_html=True,
            )
    else:
        st.markdown(
            '<div class="glass noteBox">Os principais termos desta obra já estão em linguagem direta e simples.</div>',
            unsafe_allow_html=True,
        )
    st.markdown('</div>', unsafe_allow_html=True)


def render_gallery(store: Store) -> None:
    works = store.works()
    current_user = ensure_user(store)

    cols = st.columns(2)
    for idx, work in enumerate(works):
        user_tags = [t["tag"] for t in store.tags() if t.get("user_id") == current_user and t.get("work_id") == work["id"]]
        with cols[idx % 2]:
            st.markdown('<div class="glass workCard">', unsafe_allow_html=True)
            st.image(work["image"], use_container_width=True)

            action_left, action_right = st.columns([1, 1])
            with action_left:
                if st.button("Marcar", key=f"mark_{work['id']}"):
                    st.session_state["selected_work_id"] = work["id"]
                    st.rerun()
            with action_right:
                if st.button("Acessibilidade", key=f"access_btn_{work['id']}"):
                    current = st.session_state.get("accessibility_work_id", "")
                    st.session_state["accessibility_work_id"] = "" if current == work["id"] else work["id"]
                    st.rerun()

            if st.session_state.get("selected_work_id") == work["id"]:
                st.markdown('<div class="glass smallPanel">', unsafe_allow_html=True)
                # Chave única para o input
                input_key = f"tag_input_{work['id']}"
                # Usa o valor atual do session_state ou string vazia
                current_value = st.session_state.get(input_key, "")
                tag_value = st.text_input(
                    "sua tag",
                    key=input_key,
                    value=current_value,
                    placeholder="escreva a tag"
                )
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("registrar tag", key=f"submit_tag_{work['id']}"):
                        if tag_value.strip():
                            store.add_tag(
                                {
                                    "user_id": current_user,
                                    "work_id": work["id"],
                                    "tag": tag_value.strip(),
                                }
                            )
                            # Limpa o input após registrar
                            st.session_state[input_key] = ""
                            st.rerun()
                        else:
                            st.warning("Digite uma tag antes de registrar.")
                with c2:
                    if st.button("fechar", key=f"close_tag_{work['id']}"):
                        st.session_state["selected_work_id"] = ""
                        # Remove a chave do session_state ao fechar
                        if input_key in st.session_state:
                            del st.session_state[input_key]
                        st.rerun()
                st.markdown('<div class="smallLabel">suas tags nesta imagem</div>', unsafe_allow_html=True)
                user_tags = [t["tag"] for t in store.tags() if t.get("user_id") == current_user and t.get("work_id") == work["id"]]
                if user_tags:
                    st.markdown("".join([f'<span class="tagPill">{html.escape(t)}</span>' for t in user_tags]), unsafe_allow_html=True)
                else:
                    st.markdown('<div class="glass noteBox">Nenhuma tag registrada por você nesta imagem ainda.</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

            if st.session_state.get("accessibility_work_id") == work["id"]:
                render_accessibility_controls(work, user_tags)

            st.markdown('</div>', unsafe_allow_html=True)


def render_public_area(store: Store) -> None:
    tab_public, tab_admin = st.tabs(["explorar obras", "área administrativa"])
    with tab_public:
        render_gallery(store)
    with tab_admin:
        render_admin(store)


def admin_login_box(store: Store) -> None:
    st.markdown('<div class="glass noteBox">', unsafe_allow_html=True)
    st.markdown("### área administrativa")
    login = st.text_input("login", key="admin_login_field")
    password = st.text_input("senha", type="password", key="admin_password_field")
    if st.button("entrar", key="admin_login_button"):
        if store.admin_ok(login, password):
            st.session_state["admin_logged"] = True
            st.rerun()
        st.error("credenciais inválidas.")
    st.markdown('</div>', unsafe_allow_html=True)


def render_panel(store: Store) -> None:
    report = connectivity_report(store)
    out = report["collection_output"]
    c1, c2, c3, c4, c5 = st.columns(5)
    data = [
        ("obras monitoradas", out["obras_monitoradas"], "base institucional ativa"),
        ("tags coletadas", out["tags_coletadas"], "marcação social acumulada"),
        ("fila curatorial", out["fila_curatorial"], "itens aguardando revisão"),
        ("validações concluídas", out["validacoes_concluidas"], "retorno curatorial"),
        ("termos para busca", len(store.concepts()), "camada reconciliada"),
    ]
    for col, (title, value, note) in zip([c1, c2, c3, c4, c5], data):
        with col:
            st.markdown(
                f'<div class="glass metricCard"><div class="metricTop">{html.escape(title)}</div><div class="metricValue">{value}</div><div class="metricNote">{html.escape(note)}</div></div>',
                unsafe_allow_html=True,
            )

    st.markdown(
        f"""
        <div class="glass noteBox">
            <strong>resumo analítico.</strong> A instituição registra entradas públicas, validações curatoriais,
            conexões com metadados e pontos externos. Neste momento, há {out["tags_coletadas"]} tags,
            {out["fila_curatorial"]} itens em revisão e {out["validações_concluidas"] if "validações_concluidas" in out else out["validacoes_concluidas"]} validações concluídas.
            O foco do painel é mostrar o que foi coletado, o que ainda precisa de revisão e como essas camadas se conectam.
        </div>
        """.replace("validações_concluidas", "validacoes_concluidas"),
        unsafe_allow_html=True,
    )


def render_validation(store: Store) -> None:
    st.markdown("## validação")
    works = {w["id"]: w for w in store.works()}
    validated_ids = {v["tag_id"] for v in store.validations()}
    pending = [t for t in store.tags() if t.get("id") not in validated_ids]
    if not pending:
        st.markdown('<div class="glass noteBox">Não há tags pendentes de validação neste momento.</div>', unsafe_allow_html=True)
        return
    for tag_obj in pending:
        work = works.get(tag_obj.get("work_id"))
        if not work:
            continue
        pred = predict_tag(store, tag_obj["tag"], work)
        sug = suggestions_for_tag(store, tag_obj["tag"], work["id"])
        st.markdown('<div class="glass noteBox">', unsafe_allow_html=True)
        st.markdown(f"### {tag_obj['tag']} · {work['title']}")
        st.markdown(
            f"""
            <div class="helper">
            previsão de categoria: <strong>{pred['category']}</strong> · confiança {pred['confidence']}<br>
            conceito sugerido: <strong>{pred['concept_label'] or "nenhum"}</strong><br>
            museu: {html.escape(work['museum'])} · período: {html.escape(work['period'])} · técnica: {html.escape(work['technique'])}
            </div>
            """,
            unsafe_allow_html=True,
        )

        if sug["examples"]:
            st.markdown("**3 exemplos próximos**")
            for ex in sug["examples"]:
                st.markdown(f'- {ex["tag"]} · {ex["obra"]} · similaridade {ex["score"]}')

        if sug["similar_tags"]:
            st.markdown("**ligações em comum e possíveis repetições**")
            for ex in sug["similar_tags"][:5]:
                st.markdown(f'- {ex["tag"]} · {ex["work_title"]} · similaridade {ex["score"]}')

        if sug["concept_candidates"]:
            st.markdown("**conceitos candidatos**")
            for item in sug["concept_candidates"]:
                st.markdown(f'- {item["label"]} · {item["category"]} · score {item["score"]}')

        if sug["conflicts"]:
            st.warning(" ".join(sug["conflicts"]))

        col1, col2, col3 = st.columns(3)
        with col1:
            category = st.selectbox("categoria validada", CATEGORY_OPTIONS, index=max(0, CATEGORY_OPTIONS.index(pred["category"]) if pred["category"] in CATEGORY_OPTIONS else 0), key=f"val_cat_{tag_obj['id']}")
        concept_options = ["nenhum"] + [c["label"] for c in store.concepts()]
        default_concept = pred["concept_label"] if pred["concept_label"] in concept_options else "nenhum"
        with col2:
            concept_label = st.selectbox("conceito reconciliado", concept_options, index=concept_options.index(default_concept), key=f"val_con_{tag_obj['id']}")
        with col3:
            decision = st.selectbox("decisão", ["approved", "rejected"], key=f"val_dec_{tag_obj['id']}")

        notes = st.text_area("notas curatoriais", key=f"val_notes_{tag_obj['id']}", height=90)
        if st.button("registrar validação", key=f"val_save_{tag_obj['id']}"):
            concept_id = ""
            for c in store.concepts():
                if c["label"] == concept_label:
                    concept_id = c["id"]
                    break
            store.add_validation(
                {
                    "tag_id": tag_obj["id"],
                    "decision": decision,
                    "category": category,
                    "concept_id": concept_id,
                    "notes": notes.strip(),
                }
            )
            st.success("Validação registrada.")
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)


def render_learning_and_search(store: Store) -> None:
    st.markdown("## busca e aprendizagem")
    st.markdown(
        '<div class="glass noteBox">A aprendizagem considera metadados da obra, tags institucionais, tags criadas pelo público e validações curatoriais. A busca cruza tudo isso em uma leitura conectada.</div>',
        unsafe_allow_html=True,
    )
    examples = build_learning_examples(store)
    st.markdown(
        f'<div class="glass noteBox">Exemplos de aprendizagem ativos: <strong>{len(examples)}</strong>. Classes presentes: <strong>{", ".join(sorted(examples["category"].astype(str).unique().tolist())[:8]) if not examples.empty else "nenhuma ainda"}</strong>.</div>',
        unsafe_allow_html=True,
    )

    query = st.text_input("busca conectada", placeholder="busque por tema, técnica, material, lugar, artista, conceito ou tag", key="real_search_query")
    if query.strip():
        results = real_search(store, query)
        if not results:
            st.info("Nenhum resultado relevante foi encontrado para esta consulta.")
        else:
            for item in results:
                st.markdown(
                    f"""
                    <div class="glass noteBox">
                    <strong>{html.escape(item['title'])}</strong> · {html.escape(item['artist'])}<br>
                    museu: {html.escape(item['museum'])} · score {item['score']}<br>
                    metadados correspondentes: {", ".join(item["matched_metadata"]) or "nenhum"}<br>
                    tags coincidentes: {", ".join(item["matched_tags"]) or "nenhuma"}<br>
                    conceitos coincidentes: {", ".join(item["matched_concepts"]) or "nenhum"}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


def render_temporal(store: Store) -> None:
    st.markdown("## análise temporal")
    summary = build_temporal_summary(store)
    if not summary["by_day"]:
        st.markdown('<div class="glass noteBox">Ainda não há tags suficientes para análise temporal.</div>', unsafe_allow_html=True)
        return

    for title, key in [("por dia", "by_day"), ("por mês", "by_month"), ("por ano", "by_year")]:
        st.markdown(f"### {title}")
        for bucket in summary[key]:
            st.markdown(
                f"""
                <div class="glass noteBox">
                    <strong>{bucket['period']}</strong><br>
                    total de tags: {bucket['count']}<br>
                    obras envolvidas: {", ".join(bucket['works']) or "nenhuma"}<br>
                    tags observadas: {", ".join(bucket['unique_tags']) or "nenhuma"}
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_network(store: Store) -> None:
    st.markdown("## teia 3d")
    st.markdown(
        '<div class="glass noteBox">A teia 3D representa a rede de compartilhamento e interoperabilidade entre metadados institucionais, tags públicas, conceitos reconciliados e pontos de open data.</div>',
        unsafe_allow_html=True,
    )
    fig = build_3d_network(store)
    if fig is None:
        st.warning("A teia 3D precisa do plotly para ser exibida nesta execução.")
    else:
        st.plotly_chart(fig, use_container_width=True, key="network3d")

    report = connectivity_report(store)
    st.markdown("### o que a instituição coleta")
    output = report["collection_output"]
    st.markdown(
        f"""
        <div class="glass noteBox">
        entradas sociais: {output['tags_coletadas']} · obras monitoradas: {output['obras_monitoradas']} · fila curatorial: {output['fila_curatorial']} · validações concluídas: {output['validacoes_concluidas']}.
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("### pontos de atenção")
    for item in report["confusion"][:10]:
        st.markdown(
            f'<div class="glass noteBox">A tag <strong>{html.escape(item["tag"])}</strong> aparece em {item["works_count"]} obras e {item["total_count"]} registros. Isso merece conferência por compartilhamento, repetição ou confusão semântica.</div>',
            unsafe_allow_html=True,
        )


def render_data_and_works(store: Store) -> None:
    st.markdown("## dados e obras")
    works = store.works()
    for work in works:
        with st.expander(work["title"]):
            st.markdown(f"**artista:** {work['artist']}")
            st.markdown(f"**museu:** {work['museum']}")
            st.markdown(f"**período:** {work['period']}")
            st.markdown(f"**técnica:** {work['technique']}")
            st.markdown(f"**material:** {work['material']}")
            st.markdown(f"**tags institucionais:** {', '.join(work['institution_tags'])}")
            st.markdown(f"**open data:** {', '.join(work['open_data'])}")


def export_pdf(store: Store) -> Optional[bytes]:
    if not REPORTLAB_AVAILABLE:
        return None
    pdf_path = APP_DIR / f"relatorio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    doc = SimpleDocTemplate(str(pdf_path), pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    story.append(Paragraph("Relatório Folksonomia", styles["Title"]))
    story.append(Spacer(1, 12))
    report = connectivity_report(store)
    out = report["collection_output"]
    story.append(Paragraph(f"Obras monitoradas: {out['obras_monitoradas']}", styles["BodyText"]))
    story.append(Paragraph(f"Tags coletadas: {out['tags_coletadas']}", styles["BodyText"]))
    story.append(Paragraph(f"Fila curatorial: {out['fila_curatorial']}", styles["BodyText"]))
    story.append(Paragraph(f"Validações concluídas: {out['validacoes_concluidas']}", styles["BodyText"]))
    story.append(Spacer(1, 12))
    story.append(Paragraph("Análise temporal", styles["Heading2"]))
    temporal = build_temporal_summary(store)
    for bucket in temporal["by_month"][:24]:
        story.append(Paragraph(f"{bucket['period']}: {bucket['count']} tags", styles["BodyText"]))
        story.append(Paragraph(f"Tags: {', '.join(bucket['unique_tags'])}", styles["BodyText"]))
        story.append(Spacer(1, 6))
    story.append(Spacer(1, 12))
    story.append(Paragraph("Confusões e repetições", styles["Heading2"]))
    for item in report["confusion"][:20]:
        story.append(Paragraph(f"Tag {item['tag']} em {item['works_count']} obras e {item['total_count']} ocorrências.", styles["BodyText"]))
    story.append(Spacer(1, 12))
    table_data = [["Obra", "Tags", "Tags únicas", "Preenchimento"]]
    for item in report["by_work"]:
        table_data.append([item["title"], str(item["tags"]), str(item["tags_unicas"]), str(item["preenchimento"])])
    table = Table(table_data)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dbeafe")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#9ca3af")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ]
        )
    )
    story.append(table)
    doc.build(story)
    data = pdf_path.read_bytes()
    try:
        pdf_path.unlink(missing_ok=True)
    except Exception:
        pass
    return data


def render_export(store: Store) -> None:
    st.markdown("## exportar")
    pdf_data = export_pdf(store)
    if pdf_data is None:
        st.warning("Não foi possível gerar o PDF nesta execução: reportlab.")
    else:
        st.download_button("baixar relatório em pdf", pdf_data, file_name="relatorio_folksonomia.pdf", mime="application/pdf")
    st.download_button(
        "baixar tags em csv",
        pd.DataFrame(store.tags()).to_csv(index=False).encode("utf-8"),
        file_name="tags_folksonomia.csv",
        mime="text/csv",
    )


def render_admin(store: Store) -> None:
    if not st.session_state.get("admin_logged"):
        admin_login_box(store)
        return
    tabs = st.tabs(["painel", "validação", "busca e aprendizagem", "análise temporal", "teia 3d", "dados e obras", "exportar"])
    with tabs[0]:
        render_panel(store)
    with tabs[1]:
        render_validation(store)
    with tabs[2]:
        render_learning_and_search(store)
    with tabs[3]:
        render_temporal(store)
    with tabs[4]:
        render_network(store)
    with tabs[5]:
        render_data_and_works(store)
    with tabs[6]:
        render_export(store)

    if st.button("sair da área administrativa", key="logout_admin"):
        st.session_state["admin_logged"] = False
        st.rerun()


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, layout="wide", initial_sidebar_state="collapsed")
    init_session()
    inject_css()
    store = Store()
    ensure_user(store)
    render_brand()
    if not st.session_state.get("intro_done"):
        render_questionnaire(store)
    else:
        render_public_area(store)


if __name__ == "__main__":
    main()
