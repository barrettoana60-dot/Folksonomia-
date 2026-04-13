
from __future__ import annotations

import base64
import colorsys
import difflib
import hashlib
import io
import json
import math
import os
import random
import re
import statistics
import textwrap
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics.pairwise import cosine_similarity


# ============================================================
# CONFIGURAÇÃO
# ============================================================

st.set_page_config(
    page_title="folksonomia",
    page_icon="🖼️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

APP_TITLE = "folksonomia"
APP_DIR = Path("folksonomia_data")
WORKS_FILE = APP_DIR / "works.json"
TAGS_FILE = APP_DIR / "tags.json"
USERS_FILE = APP_DIR / "users.json"
VALIDATIONS_FILE = APP_DIR / "validations.json"
SETTINGS_FILE = APP_DIR / "settings.json"
REPORTS_FILE = APP_DIR / "reports.json"

ADMIN_USERNAME = "nugep239@"
ADMIN_PASSWORD = "Artemis289@"

ENTITY_LABELS = [
    "tema",
    "pessoa",
    "lugar",
    "período",
    "material",
    "técnica",
    "iconografia",
    "evento histórico",
    "grupo social/cultural",
]

SEED_CONCEPTS = [
    {"label": "azul", "category": "tema", "aliases": ["azul", "azulado", "céu azul", "mar azul"]},
    {"label": "branco", "category": "material", "aliases": ["branco", "esbranquiçado"]},
    {"label": "guerra", "category": "tema", "aliases": ["guerra", "conflito", "violência", "bombardeio"]},
    {"label": "noite", "category": "tema", "aliases": ["noite", "noturno", "escuro"]},
    {"label": "estrela", "category": "iconografia", "aliases": ["estrela", "astros", "astro"]},
    {"label": "óleo sobre tela", "category": "técnica", "aliases": ["óleo sobre tela", "óleo", "pintura a óleo"]},
    {"label": "cubismo", "category": "período", "aliases": ["cubismo", "cubista"]},
    {"label": "pós-impressionismo", "category": "período", "aliases": ["pós-impressionismo", "pós impressionismo"]},
    {"label": "mulher", "category": "pessoa", "aliases": ["mulher", "feminino", "figura feminina"]},
    {"label": "cavalo", "category": "iconografia", "aliases": ["cavalo", "equino"]},
    {"label": "touro", "category": "iconografia", "aliases": ["touro", "boi"]},
    {"label": "mãe", "category": "pessoa", "aliases": ["mãe", "mae"]},
]

RANDOM_WORDS_A = [
    "Neblina", "Argila", "Aurora", "Cedro", "Prisma", "Vidro", "Rastro", "Sílex",
    "Jaspe", "Véu", "Faísca", "Lúmen", "Atlas", "Íris", "Néctar", "Brisa",
]
RANDOM_WORDS_B = [
    "Clara", "Firme", "Sutil", "Viva", "Densa", "Nítida", "Atena", "Mansa",
    "Solar", "Alta", "Gentil", "Móvel", "Franca", "Ágil", "Longa", "Serena",
]


# ============================================================
# UTILIDADES
# ============================================================

def ensure_dir() -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)


def load_json(path: Path, default: Any) -> Any:
    ensure_dir()
    if not path.exists():
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json(path: Path, data: Any) -> None:
    ensure_dir()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def slug(text: str) -> str:
    text = text or ""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = re.sub(r"[^a-z0-9à-ÿ\s-]", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def tokenize(text: str) -> List[str]:
    base = slug(text)
    return [tok for tok in base.split() if tok]


def similarity(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, slug(a), slug(b)).ratio()


def jaccard_tokens(a: str, b: str) -> float:
    sa = set(tokenize(a))
    sb = set(tokenize(b))
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / max(1, len(sa | sb))


def normalize_tag(text: str) -> str:
    t = slug(text)
    return t.strip()


def generate_user_label() -> str:
    return f"{random.choice(RANDOM_WORDS_A)} {random.choice(RANDOM_WORDS_B)}"


def hashed_password(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def percent(num: float, den: float) -> str:
    if den == 0:
        return "0%"
    return f"{(100 * num / den):.1f}%"


def safe_int(v: Any) -> int:
    try:
        return int(v)
    except Exception:
        return 0


def html_escape(text: str) -> str:
    text = str(text or "")
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#039;")
    )


def datetime_parts(ts: str) -> Tuple[str, str, str]:
    try:
        dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%Y-%m-%d"), dt.strftime("%Y-%m"), dt.strftime("%Y")
    except Exception:
        return "", "", ""


def month_label(year_month: str) -> str:
    try:
        dt = datetime.strptime(year_month, "%Y-%m")
        meses = [
            "jan", "fev", "mar", "abr", "mai", "jun",
            "jul", "ago", "set", "out", "nov", "dez",
        ]
        return f"{meses[dt.month - 1]}/{dt.year}"
    except Exception:
        return year_month


# ============================================================
# DADOS INICIAIS
# ============================================================

def default_works() -> List[Dict[str, Any]]:
    return [
        {
            "id": 1,
            "title": "Guernica",
            "artist": "Pablo Picasso",
            "year": "1937",
            "museum": "Museo Nacional Centro de Arte Reina Sofía",
            "collection": "Pintura moderna",
            "place": "Espanha",
            "period": "modernismo do século XX",
            "technique": "óleo sobre tela",
            "material": "tela",
            "description": "Grande composição em preto, branco e cinza, associada ao bombardeio de Guernica e à dor humana.",
            "institution_tags": ["guerra", "bombardeio", "dor", "cavalo", "touro", "mãe", "modernismo"],
            "open_data": ["wikidata:Q175129", "dbpedia:Guernica_(Picasso)"],
            "image": "https://upload.wikimedia.org/wikipedia/en/7/74/PicassoGuernica.jpg",
            "audio_seed": "Pintura de grande formato, com figuras fragmentadas, contraste forte entre luz e sombra e sensação de conflito.",
        },
        {
            "id": 2,
            "title": "A Noite Estrelada",
            "artist": "Vincent van Gogh",
            "year": "1889",
            "museum": "The Museum of Modern Art",
            "collection": "Pintura",
            "place": "França",
            "period": "pós-impressionismo",
            "technique": "óleo sobre tela",
            "material": "tela",
            "description": "Céu noturno em espirais, estrelas luminosas, lua intensa e aldeia ao fundo.",
            "institution_tags": ["noite", "estrela", "céu", "paisagem", "espiral", "pós-impressionismo"],
            "open_data": ["wikidata:Q219831", "dbpedia:The_Starry_Night"],
            "image": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ea/Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg/1200px-Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg",
            "audio_seed": "Paisagem noturna com céu em movimento, azuis profundos, estrelas brilhantes e pinceladas curvas muito marcadas.",
        },
        {
            "id": 3,
            "title": "Mona Lisa",
            "artist": "Leonardo da Vinci",
            "year": "1503",
            "museum": "Musée du Louvre",
            "collection": "Pintura renascentista",
            "place": "Itália",
            "period": "Renascimento",
            "technique": "óleo sobre madeira",
            "material": "madeira",
            "description": "Retrato feminino de meio corpo, sorriso sutil e paisagem ao fundo.",
            "institution_tags": ["retrato", "mulher", "sorriso", "renascimento", "paisagem"],
            "open_data": ["wikidata:Q12418", "dbpedia:Mona_Lisa"],
            "image": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ec/Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_retouched.jpg/800px-Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_retouched.jpg",
            "audio_seed": "Retrato frontal de uma mulher, mãos apoiadas, expressão calma e fundo com paisagem esfumaçada.",
        },
        {
            "id": 4,
            "title": "O Grito",
            "artist": "Edvard Munch",
            "year": "1893",
            "museum": "Munchmuseet",
            "collection": "Pintura expressionista",
            "place": "Noruega",
            "period": "Expressionismo",
            "technique": "óleo, têmpera e pastel",
            "material": "cartão",
            "description": "Figura central em desespero diante de um céu intenso e distorcido.",
            "institution_tags": ["angústia", "expressão", "figura", "céu", "ponte", "expressionismo"],
            "open_data": ["wikidata:Q471379", "dbpedia:The_Scream"],
            "image": "https://upload.wikimedia.org/wikipedia/commons/f/f4/The_Scream.jpg",
            "audio_seed": "Figura central com mãos no rosto, céu alaranjado ondulante e clima forte de angústia.",
        },
        {
            "id": 5,
            "title": "Abaporu",
            "artist": "Tarsila do Amaral",
            "year": "1928",
            "museum": "MALBA",
            "collection": "Modernismo latino-americano",
            "place": "Brasil",
            "period": "Modernismo brasileiro",
            "technique": "óleo sobre tela",
            "material": "tela",
            "description": "Figura humana de pés e mãos grandes, sol e cacto em composição sintética.",
            "institution_tags": ["modernismo brasileiro", "figura humana", "sol", "cacto", "antropofagia"],
            "open_data": ["wikidata:Q4664184"],
            "image": "https://upload.wikimedia.org/wikipedia/commons/0/0f/Abaporu.jpg",
            "audio_seed": "Figura sentada com pés muito grandes, braço apoiado no joelho, cacto ao lado e sol amarelo acima.",
        },
        {
            "id": 6,
            "title": "Las Meninas",
            "artist": "Diego Velázquez",
            "year": "1656",
            "museum": "Museo del Prado",
            "collection": "Pintura barroca",
            "place": "Espanha",
            "period": "Barroco",
            "technique": "óleo sobre tela",
            "material": "tela",
            "description": "Cena de corte com infanta, damas de companhia, pintor e jogo complexo de olhares.",
            "institution_tags": ["infanta", "corte", "pintor", "espelho", "barroco", "olhar"],
            "open_data": ["wikidata:Q253437", "dbpedia:Las_Meninas"],
            "image": "https://upload.wikimedia.org/wikipedia/commons/3/38/Las_Meninas_01.jpg",
            "audio_seed": "Cena interna com várias figuras, uma menina ao centro, pessoas ao redor e profundidade marcada pelo espelho e pela porta ao fundo.",
        },
    ]


# ============================================================
# STORE
# ============================================================

class Store:
    def __init__(self) -> None:
        ensure_dir()
        if not WORKS_FILE.exists():
            save_json(WORKS_FILE, default_works())
        if not TAGS_FILE.exists():
            save_json(TAGS_FILE, [])
        if not USERS_FILE.exists():
            save_json(USERS_FILE, [])
        if not VALIDATIONS_FILE.exists():
            save_json(VALIDATIONS_FILE, [])
        if not SETTINGS_FILE.exists():
            save_json(SETTINGS_FILE, {"font_scale": 1.0, "high_contrast": False})
        if not REPORTS_FILE.exists():
            save_json(REPORTS_FILE, [])

    def works(self) -> List[Dict[str, Any]]:
        return load_json(WORKS_FILE, default_works())

    def tags(self) -> List[Dict[str, Any]]:
        return load_json(TAGS_FILE, [])

    def users(self) -> List[Dict[str, Any]]:
        return load_json(USERS_FILE, [])

    def validations(self) -> List[Dict[str, Any]]:
        return load_json(VALIDATIONS_FILE, [])

    def settings(self) -> Dict[str, Any]:
        return load_json(SETTINGS_FILE, {"font_scale": 1.0, "high_contrast": False})

    def save_settings(self, data: Dict[str, Any]) -> None:
        save_json(SETTINGS_FILE, data)

    def save_user_if_missing(self, user_id: str, user_label: str, answers: Dict[str, str]) -> None:
        users = self.users()
        already = next((u for u in users if u.get("id") == user_id), None)
        if already:
            return
        users.append(
            {
                "id": user_id,
                "label": user_label,
                "created_at": now_iso(),
                **answers,
            }
        )
        save_json(USERS_FILE, users)

    def add_tag(self, item: Dict[str, Any]) -> None:
        tags = self.tags()
        item["id"] = max([safe_int(t.get("id")) for t in tags] + [0]) + 1
        tags.append(item)
        save_json(TAGS_FILE, tags)

    def add_validation(self, item: Dict[str, Any]) -> None:
        vals = self.validations()
        item["id"] = max([safe_int(v.get("id")) for v in vals] + [0]) + 1
        vals.append(item)
        save_json(VALIDATIONS_FILE, vals)

    def add_work(self, item: Dict[str, Any]) -> None:
        works = self.works()
        item["id"] = max([safe_int(w.get("id")) for w in works] + [0]) + 1
        works.append(item)
        save_json(WORKS_FILE, works)

    def remove_work(self, work_id: int) -> None:
        works = [w for w in self.works() if safe_int(w.get("id")) != work_id]
        save_json(WORKS_FILE, works)

    def save_report_meta(self, item: Dict[str, Any]) -> None:
        data = load_json(REPORTS_FILE, [])
        item["id"] = max([safe_int(v.get("id")) for v in data] + [0]) + 1
        data.append(item)
        save_json(REPORTS_FILE, data)


# ============================================================
# LEARNING / NLU
# ============================================================

def build_learning_records(store: Store) -> pd.DataFrame:
    works = store.works()
    tags = store.tags()
    validations = store.validations()

    work_map = {safe_int(w["id"]): w for w in works}
    validated_map = defaultdict(list)
    for val in validations:
        tag_id = safe_int(val.get("tag_id"))
        validated_map[tag_id].append(val)

    rows = []
    for tag in tags:
        work = work_map.get(safe_int(tag.get("work_id")))
        if not work:
            continue
        tag_text = str(tag.get("tag", "")).strip()
        text_blob = " ".join(
            [
                tag_text,
                tag.get("notes", "") or "",
                work.get("title", ""),
                work.get("artist", ""),
                work.get("museum", ""),
                work.get("place", ""),
                work.get("period", ""),
                work.get("technique", ""),
                work.get("material", ""),
                work.get("description", ""),
                " ".join(work.get("institution_tags", [])),
                " ".join(work.get("open_data", [])),
            ]
        ).strip()
        approved = [v for v in validated_map.get(safe_int(tag.get("id")), []) if v.get("decision") == "approved"]
        if approved:
            last = approved[-1]
            category = last.get("validated_category") or ""
            concept = last.get("reconciled_concept") or ""
        else:
            category = ""
            concept = ""
        rows.append(
            {
                "tag_id": safe_int(tag.get("id")),
                "work_id": safe_int(tag.get("work_id")),
                "tag": tag_text,
                "notes": tag.get("notes", ""),
                "text_blob": text_blob,
                "category": category,
                "concept": concept,
                "created_at": tag.get("created_at", ""),
            }
        )

    return pd.DataFrame(rows)


@dataclass
class LearningPack:
    search_vectorizer: Optional[TfidfVectorizer]
    search_matrix: Optional[Any]
    search_docs: List[Dict[str, Any]]
    category_model: Optional[LogisticRegression]
    category_vectorizer: Optional[TfidfVectorizer]
    category_labels: List[str]
    concept_alias_map: Dict[str, Dict[str, Any]]
    concept_by_label: Dict[str, Dict[str, Any]]
    trained_examples: int
    summary: str


def build_concept_memory(store: Store) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    works = store.works()
    tags = store.tags()
    validations = store.validations()

    concept_by_label: Dict[str, Dict[str, Any]] = {}
    for seed in SEED_CONCEPTS:
        concept_by_label[seed["label"]] = {
            "label": seed["label"],
            "category": seed["category"],
            "aliases": set(seed["aliases"]),
            "frequency": 1,
            "source": "seed",
        }

    work_map = {safe_int(w["id"]): w for w in works}
    tag_map = {safe_int(t["id"]): t for t in tags}

    for val in validations:
        if val.get("decision") != "approved":
            continue
        cat = (val.get("validated_category") or "").strip()
        concept = (val.get("reconciled_concept") or "").strip()
        tag_obj = tag_map.get(safe_int(val.get("tag_id")))
        if not tag_obj:
            continue
        tag_text = str(tag_obj.get("tag", "")).strip()
        if not concept:
            concept = normalize_tag(tag_text)
        if concept not in concept_by_label:
            concept_by_label[concept] = {
                "label": concept,
                "category": cat or "tema",
                "aliases": set(),
                "frequency": 0,
                "source": "validation",
            }
        concept_by_label[concept]["aliases"].add(tag_text)
        concept_by_label[concept]["frequency"] += 1

        wid = safe_int(tag_obj.get("work_id"))
        work = work_map.get(wid)
        if work:
            for field in ["title", "artist", "museum", "place", "period", "technique", "material"]:
                value = work.get(field)
                if value:
                    concept_by_label[concept]["aliases"].add(str(value))

    alias_map: Dict[str, Dict[str, Any]] = {}
    for concept in concept_by_label.values():
        aliases = set(concept["aliases"])
        aliases.add(concept["label"])
        for alias in aliases:
            alias_map[normalize_tag(alias)] = {
                "label": concept["label"],
                "category": concept["category"],
                "frequency": concept["frequency"],
            }
        concept["aliases"] = sorted(a for a in aliases if a)

    return alias_map, concept_by_label


def build_search_docs(store: Store, concept_by_label: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    works = store.works()
    tags = store.tags()
    validations = store.validations()

    tags_by_work = defaultdict(list)
    for t in tags:
        tags_by_work[safe_int(t.get("work_id"))].append(str(t.get("tag", "")).strip())

    concepts_by_work = defaultdict(list)
    tag_map = {safe_int(t["id"]): t for t in tags}
    for v in validations:
        if v.get("decision") != "approved":
            continue
        tag = tag_map.get(safe_int(v.get("tag_id")))
        if not tag:
            continue
        if v.get("reconciled_concept"):
            concepts_by_work[safe_int(tag.get("work_id"))].append(str(v["reconciled_concept"]).strip())

    docs = []
    for w in works:
        wid = safe_int(w.get("id"))
        parts = [
            w.get("title", ""),
            w.get("artist", ""),
            w.get("museum", ""),
            w.get("collection", ""),
            w.get("place", ""),
            w.get("period", ""),
            w.get("technique", ""),
            w.get("material", ""),
            w.get("description", ""),
            " ".join(w.get("institution_tags", [])),
            " ".join(tags_by_work.get(wid, [])),
            " ".join(concepts_by_work.get(wid, [])),
            " ".join(w.get("open_data", [])),
        ]
        docs.append(
            {
                "work_id": wid,
                "title": w.get("title", ""),
                "text": " ".join([str(p) for p in parts if p]).strip(),
                "work": w,
                "tags_count": len(tags_by_work.get(wid, [])),
            }
        )
    return docs


def build_learning_pack(store: Store) -> LearningPack:
    alias_map, concept_by_label = build_concept_memory(store)
    docs = build_search_docs(store, concept_by_label)

    search_vectorizer = None
    search_matrix = None
    if docs:
        search_vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1)
        search_matrix = search_vectorizer.fit_transform([d["text"] for d in docs])

    records = build_learning_records(store)
    category_model = None
    category_vectorizer = None
    category_labels = []

    trainable = records[(records["category"].astype(str).str.len() > 0)]
    trained_examples = len(trainable)
    if trained_examples >= 4 and trainable["category"].nunique() >= 2:
        category_vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1)
        X = category_vectorizer.fit_transform(trainable["text_blob"].astype(str).tolist())
        y = trainable["category"].astype(str).tolist()
        category_model = LogisticRegression(max_iter=2000)
        category_model.fit(X, y)
        category_labels = sorted(set(y))

    tags_total = len(store.tags())
    works_total = len(store.works())
    validations_total = len(store.validations())
    approved_total = len([v for v in store.validations() if v.get("decision") == "approved"])

    summary = (
        f"O motor analítico foi atualizado com {works_total} obras, {tags_total} marcações, "
        f"{validations_total} validações registradas e {len(concept_by_label)} conceitos ativos. "
        f"Há {trained_examples} exemplos diretamente reutilizados no aprendizado supervisionado. "
        f"A busca foi enriquecida com metadados, tags públicas, conceitos reconciliados e pontos externos."
    )

    return LearningPack(
        search_vectorizer=search_vectorizer,
        search_matrix=search_matrix,
        search_docs=docs,
        category_model=category_model,
        category_vectorizer=category_vectorizer,
        category_labels=category_labels,
        concept_alias_map=alias_map,
        concept_by_label=concept_by_label,
        trained_examples=trained_examples,
        summary=summary,
    )


def guess_category_from_tag(tag: str, work: Dict[str, Any]) -> Tuple[str, float, str]:
    t = normalize_tag(tag)
    if not t:
        return "tema", 0.0, "sem texto"

    heuristics = {
        "técnica": ["óleo", "pintura", "pastel", "têmpera", "aquarela", "escultura", "tela"],
        "material": ["madeira", "metal", "pedra", "ferro", "bronze", "papel", "cartão", "tela"],
        "lugar": ["brasil", "espanha", "frança", "itália", "noruega", "europa", "paris", "madrid"],
        "pessoa": ["mulher", "homem", "mãe", "criança", "pintor", "rei", "rainha", "infanta"],
        "período": ["barroco", "renascimento", "modernismo", "expressionismo", "pós-impressionismo", "cubismo"],
        "iconografia": ["estrela", "lua", "cavalo", "touro", "sol", "ponte", "espelho", "cacto"],
        "tema": ["guerra", "dor", "angústia", "noite", "paisagem", "conflito", "sorriso", "olhar"],
    }
    for cat, words in heuristics.items():
        if t in [normalize_tag(w) for w in words]:
            return cat, 0.68, "regra temática"
    if len(tokenize(tag)) == 1 and t in [normalize_tag(x) for x in work.get("institution_tags", [])]:
        return "tema", 0.61, "aproximação por metadado institucional"
    return "tema", 0.52, "heurística geral"


def predict_tag(tag: str, work: Dict[str, Any], pack: LearningPack) -> Dict[str, Any]:
    normalized = normalize_tag(tag)
    if not normalized:
        return {
            "category": "tema",
            "confidence": 0.0,
            "concept": "",
            "reason": "sem conteúdo",
            "examples": [],
        }

    if normalized in pack.concept_alias_map:
        found = pack.concept_alias_map[normalized]
        examples = [found["label"]]
        return {
            "category": found["category"],
            "confidence": min(0.95, 0.55 + min(found.get("frequency", 1), 8) * 0.04),
            "concept": found["label"],
            "reason": "conceito já aprendido por validação/seed",
            "examples": examples,
        }

    blob = " ".join(
        [
            tag,
            work.get("title", ""),
            work.get("artist", ""),
            work.get("museum", ""),
            work.get("place", ""),
            work.get("period", ""),
            work.get("technique", ""),
            work.get("material", ""),
            work.get("description", ""),
            " ".join(work.get("institution_tags", [])),
        ]
    )

    if pack.category_model is not None and pack.category_vectorizer is not None:
        X = pack.category_vectorizer.transform([blob])
        pred = str(pack.category_model.predict(X)[0])
        prob = 0.0
        try:
            probs = pack.category_model.predict_proba(X)[0]
            prob = float(np.max(probs))
        except Exception:
            prob = 0.62
        concept_candidate = best_concept_for_text(tag, pack)
        return {
            "category": pred,
            "confidence": prob,
            "concept": concept_candidate,
            "reason": "modelo supervisionado com metadados e validações",
            "examples": closest_learned_aliases(tag, pack, limit=3),
        }

    cat, conf, reason = guess_category_from_tag(tag, work)
    concept_candidate = best_concept_for_text(tag, pack)
    return {
        "category": cat,
        "confidence": conf,
        "concept": concept_candidate,
        "reason": reason,
        "examples": closest_learned_aliases(tag, pack, limit=3),
    }


def closest_learned_aliases(text: str, pack: LearningPack, limit: int = 3) -> List[str]:
    scores = []
    for alias, meta in pack.concept_alias_map.items():
        s = max(similarity(text, alias), jaccard_tokens(text, alias))
        if s >= 0.40:
            scores.append((s, alias, meta["label"]))
    scores.sort(reverse=True)
    result = []
    seen = set()
    for _, alias, label in scores:
        label_text = f"{alias} → {label}"
        if label_text not in seen:
            result.append(label_text)
            seen.add(label_text)
        if len(result) >= limit:
            break
    return result


def best_concept_for_text(text: str, pack: LearningPack) -> str:
    best_label = ""
    best_score = 0.0
    for alias, meta in pack.concept_alias_map.items():
        s = max(similarity(text, alias), jaccard_tokens(text, alias))
        if s > best_score:
            best_score = s
            best_label = meta["label"]
    if best_score >= 0.45:
        return best_label
    return normalize_tag(text)


def search_works(query: str, pack: LearningPack) -> List[Dict[str, Any]]:
    query = (query or "").strip()
    if not query or pack.search_vectorizer is None or pack.search_matrix is None:
        return []

    qvec = pack.search_vectorizer.transform([query])
    sims = cosine_similarity(qvec, pack.search_matrix)[0]
    ranked_idx = np.argsort(-sims)
    results = []
    for idx in ranked_idx[:8]:
        score = float(sims[idx])
        if score <= 0:
            continue
        item = dict(pack.search_docs[idx])
        item["score"] = score
        results.append(item)
    return results


# ============================================================
# ANÁLISES
# ============================================================

def tags_by_period(tags: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_day = defaultdict(list)
    by_month = defaultdict(list)
    by_year = defaultdict(list)

    for t in tags:
        day, month, year = datetime_parts(t.get("created_at", ""))
        if day:
            by_day[day].append(t)
        if month:
            by_month[month].append(t)
        if year:
            by_year[year].append(t)

    return {"day": by_day, "month": by_month, "year": by_year}


def compute_interoperability(store: Store) -> Dict[str, Any]:
    works = store.works()
    tags = store.tags()
    validations = store.validations()

    work_map = {safe_int(w["id"]): w for w in works}
    approved = [v for v in validations if v.get("decision") == "approved"]
    approved_tag_ids = {safe_int(v.get("tag_id")) for v in approved}

    total_tags = len(tags)
    integrated = 0
    institution_match = 0
    external_match = 0
    confusion_cases = []

    seen_pairs = defaultdict(set)

    for tag in tags:
        tag_text = normalize_tag(str(tag.get("tag", "")))
        work = work_map.get(safe_int(tag.get("work_id")))
        if not work:
            continue

        institutional = [normalize_tag(x) for x in work.get("institution_tags", [])]
        external = [normalize_tag(x) for x in work.get("open_data", [])]

        if tag_text in institutional:
            institution_match += 1
        if any(tag_text in x or x in tag_text for x in external):
            external_match += 1
        if safe_int(tag.get("id")) in approved_tag_ids:
            integrated += 1

        key = (safe_int(tag.get("work_id")), tag_text)
        seen_pairs[key].add(str(tag.get("user_id")))

    for (work_id, tag_text), users in seen_pairs.items():
        if len(users) >= 2:
            confusion_cases.append(
                {
                    "work_id": work_id,
                    "tag": tag_text,
                    "users": len(users),
                    "kind": "recorrência compartilhada",
                }
            )

    return {
        "total_tags": total_tags,
        "integrated": integrated,
        "institution_match": institution_match,
        "external_match": external_match,
        "confusion_cases": confusion_cases[:20],
    }


def orthographic_groups(tags: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    unique_tags = sorted(set(normalize_tag(t.get("tag", "")) for t in tags if t.get("tag")))
    used = set()
    groups = []

    for i, tag in enumerate(unique_tags):
        if tag in used:
            continue
        bucket = [tag]
        for other in unique_tags[i + 1:]:
            if other in used:
                continue
            sim = similarity(tag, other)
            jac = jaccard_tokens(tag, other)
            if sim >= 0.82 or jac >= 0.70:
                bucket.append(other)
                used.add(other)
        if len(bucket) > 1:
            used.add(tag)
            groups.append({"base": tag, "variants": sorted(bucket), "score": round(max(similarity(tag, x) for x in bucket), 3)})

    groups.sort(key=lambda g: len(g["variants"]), reverse=True)
    return groups


def common_links_analysis(store: Store) -> List[Dict[str, Any]]:
    works = store.works()
    tags = store.tags()
    work_map = {safe_int(w["id"]): w for w in works}

    work_tags = defaultdict(list)
    for tag in tags:
        work_tags[safe_int(tag.get("work_id"))].append(normalize_tag(tag.get("tag", "")))

    links = []
    for work_id, tag_list in work_tags.items():
        counter = Counter([t for t in tag_list if t])
        if not counter:
            continue
        top = counter.most_common(10)
        for base, _ in top:
            relatives = []
            for other in counter:
                if other == base:
                    continue
                if jaccard_tokens(base, other) >= 0.5 or similarity(base, other) >= 0.7:
                    relatives.append(other)
            if relatives:
                links.append(
                    {
                        "work_title": work_map.get(work_id, {}).get("title", f"Obra {work_id}"),
                        "tag": base,
                        "related": sorted(set(relatives)),
                        "count": counter[base],
                    }
                )
    return links


def comparative_fill_balance(store: Store) -> Dict[str, Any]:
    works = store.works()
    tags = store.tags()
    validations = store.validations()
    approved_tag_ids = {safe_int(v.get("tag_id")) for v in validations if v.get("decision") == "approved"}

    rows = []
    for work in works:
        wid = safe_int(work.get("id"))
        work_tags = [t for t in tags if safe_int(t.get("work_id")) == wid]
        approved = [t for t in work_tags if safe_int(t.get("id")) in approved_tag_ids]
        rows.append(
            {
                "title": work.get("title", ""),
                "total_tags": len(work_tags),
                "approved_tags": len(approved),
                "institutional_terms": len(work.get("institution_tags", [])),
                "external_points": len(work.get("open_data", [])),
                "balance": round((len(approved) + len(work.get("institution_tags", []))) / max(1, len(work_tags) + 1), 3),
            }
        )
    return {"rows": rows}


def build_summary_text(store: Store, pack: LearningPack) -> str:
    tags = store.tags()
    works = store.works()
    validations = store.validations()
    periods = tags_by_period(tags)
    ortho = orthographic_groups(tags)
    inter = compute_interoperability(store)

    total_days = len(periods["day"])
    total_months = len(periods["month"])
    total_years = len(periods["year"])
    total_approved = len([v for v in validations if v.get("decision") == "approved"])

    densest_work = ""
    if tags:
        counts = Counter([safe_int(t.get("work_id")) for t in tags])
        if counts:
            wid, qty = counts.most_common(1)[0]
            work = next((w for w in works if safe_int(w.get("id")) == wid), None)
            densest_work = f"A obra com maior fluxo atual é {work.get('title', 'sem título')} com {qty} marcações."

    text = (
        f"Foram registradas {len(tags)} marcações em {len(works)} obras. "
        f"O sistema reaproveitou {pack.trained_examples} exemplos supervisionados para atualizar o modelo. "
        f"Há {total_approved} validações aprovadas e {len(pack.concept_by_label)} conceitos ativos na memória. "
        f"A análise temporal encontrou {total_days} dias, {total_months} meses e {total_years} anos com atividade registrada. "
        f"{densest_work} "
        f"Na interoperabilidade, {inter['institution_match']} marcações coincidem com termos institucionais e "
        f"{inter['external_match']} dialogam diretamente com pontos externos. "
        f"Foram identificados {len(ortho)} grupos fortes de variantes ortográficas que pedem revisão curatorial."
    )
    return text.strip()


# ============================================================
# TEIA 3D
# ============================================================

NODE_CATEGORY_COLORS = {
    "obra": "#9bd0ff",
    "artista": "#ffd166",
    "museu": "#f4978e",
    "coleção": "#cdb4db",
    "lugar": "#90be6d",
    "período": "#ffadad",
    "técnica": "#84dcc6",
    "material": "#caffbf",
    "tag institucional": "#f1c0e8",
    "tag pública": "#a0c4ff",
    "conceito": "#bde0fe",
    "open data": "#ffd6a5",
}


def add_node(nodes, labels_seen, node_id, label, category, text):
    if node_id in labels_seen:
        return
    labels_seen.add(node_id)
    nodes.append(
        {
            "id": node_id,
            "label": label,
            "category": category,
            "text": text,
        }
    )


def build_connectivity_web(store: Store, pack: LearningPack) -> Tuple[List[Dict[str, Any]], List[Tuple[str, str, str]]]:
    works = store.works()
    tags = store.tags()
    validations = store.validations()

    nodes = []
    seen = set()
    edges: List[Tuple[str, str, str]] = []

    tag_map = {safe_int(t["id"]): t for t in tags}
    approved_by_tag = defaultdict(list)
    for v in validations:
        if v.get("decision") == "approved":
            approved_by_tag[safe_int(v.get("tag_id"))].append(v)

    for work in works:
        wid = safe_int(work["id"])
        work_node = f"obra:{wid}"
        add_node(nodes, seen, work_node, work["title"], "obra", work["description"])

        artist_node = f"artista:{slug(work['artist'])}"
        add_node(nodes, seen, artist_node, work["artist"], "artista", work["artist"])
        edges.append((work_node, artist_node, "autor"))

        museum_node = f"museu:{slug(work['museum'])}"
        add_node(nodes, seen, museum_node, work["museum"], "museu", work["museum"])
        edges.append((work_node, museum_node, "custódia"))

        collection_node = f"colecao:{slug(work['collection'])}"
        add_node(nodes, seen, collection_node, work["collection"], "coleção", work["collection"])
        edges.append((work_node, collection_node, "coleção"))

        place_node = f"lugar:{slug(work['place'])}"
        add_node(nodes, seen, place_node, work["place"], "lugar", work["place"])
        edges.append((work_node, place_node, "lugar"))

        period_node = f"periodo:{slug(work['period'])}"
        add_node(nodes, seen, period_node, work["period"], "período", work["period"])
        edges.append((work_node, period_node, "período"))

        tech_node = f"tecnica:{slug(work['technique'])}"
        add_node(nodes, seen, tech_node, work["technique"], "técnica", work["technique"])
        edges.append((work_node, tech_node, "técnica"))

        material_node = f"material:{slug(work['material'])}"
        add_node(nodes, seen, material_node, work["material"], "material", work["material"])
        edges.append((work_node, material_node, "material"))

        for inst in work.get("institution_tags", [])[:12]:
            node = f"taginst:{slug(inst)}"
            add_node(nodes, seen, node, inst, "tag institucional", inst)
            edges.append((work_node, node, "descritor institucional"))

        for ext in work.get("open_data", [])[:6]:
            node = f"external:{slug(ext)}"
            add_node(nodes, seen, node, ext, "open data", ext)
            edges.append((work_node, node, "referência externa"))

    for tag in tags:
        wid = safe_int(tag.get("work_id"))
        work = next((w for w in works if safe_int(w["id"]) == wid), None)
        if not work:
            continue
        work_node = f"obra:{wid}"
        tag_text = str(tag.get("tag", "")).strip()
        if not tag_text:
            continue
        tag_node = f"tagpub:{slug(tag_text)}"
        add_node(nodes, seen, tag_node, tag_text, "tag pública", tag_text)
        edges.append((work_node, tag_node, "marcação pública"))

        for val in approved_by_tag.get(safe_int(tag.get("id")), []):
            concept = (val.get("reconciled_concept") or "").strip()
            if concept:
                cnode = f"conceito:{slug(concept)}"
                add_node(nodes, seen, cnode, concept, "conceito", concept)
                edges.append((tag_node, cnode, "reconciliação"))

    return nodes, edges


def layout_3d(nodes: List[Dict[str, Any]]) -> Dict[str, Tuple[float, float, float]]:
    groups = defaultdict(list)
    for node in nodes:
        groups[node["category"]].append(node)

    positions = {}
    categories = list(groups.keys())
    big_radius = 10
    for idx, cat in enumerate(categories):
        angle = (2 * math.pi * idx) / max(1, len(categories))
        cat_x = math.cos(angle) * big_radius
        cat_y = math.sin(angle) * big_radius
        cat_z = (idx % 5) * 1.8 - 4.0

        members = groups[cat]
        inner_radius = 2.5 + idx * 0.04
        for j, node in enumerate(members):
            a2 = (2 * math.pi * j) / max(1, len(members))
            r2 = inner_radius + (j % 3) * 0.6
            x = cat_x + math.cos(a2) * r2
            y = cat_y + math.sin(a2) * r2
            z = cat_z + math.sin(a2 * 2) * 1.2
            positions[node["id"]] = (x, y, z)
    return positions


def render_connectivity_web_3d(store: Store, pack: LearningPack) -> None:
    nodes, edges = build_connectivity_web(store, pack)
    pos = layout_3d(nodes)

    edge_x = []
    edge_y = []
    edge_z = []
    for a, b, _ in edges:
        if a not in pos or b not in pos:
            continue
        x0, y0, z0 = pos[a]
        x1, y1, z1 = pos[b]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])
        edge_z.extend([z0, z1, None])

    fig = go.Figure()
    fig.add_trace(
        go.Scatter3d(
            x=edge_x,
            y=edge_y,
            z=edge_z,
            mode="lines",
            line=dict(color="rgba(110,180,255,0.25)", width=2),
            hoverinfo="none",
            showlegend=False,
        )
    )

    by_cat = defaultdict(list)
    for node in nodes:
        by_cat[node["category"]].append(node)

    for cat, items in by_cat.items():
        xs, ys, zs, texts, labels = [], [], [], [], []
        for n in items:
            x, y, z = pos[n["id"]]
            xs.append(x)
            ys.append(y)
            zs.append(z)
            labels.append(n["label"])
            texts.append(f"{n['label']}<br>{n['category']}<br>{html_escape(n['text'])[:160]}")
        fig.add_trace(
            go.Scatter3d(
                x=xs,
                y=ys,
                z=zs,
                mode="markers+text",
                marker=dict(
                    size=6 if cat not in ["obra", "conceito"] else 8,
                    color=NODE_CATEGORY_COLORS.get(cat, "#cccccc"),
                    opacity=0.92,
                    line=dict(color="rgba(255,255,255,0.45)", width=0.6),
                ),
                text=labels,
                textposition="top center",
                textfont=dict(size=9, color="#f7f7f7"),
                hovertemplate="%{customdata}<extra></extra>",
                customdata=texts,
                name=cat,
            )
        )

    fig.update_layout(
        height=760,
        margin=dict(l=0, r=0, t=0, b=0),
        scene=dict(
            bgcolor="rgba(0,0,0,0)",
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            zaxis=dict(visible=False),
            camera=dict(eye=dict(x=1.7, y=1.6, z=1.2)),
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(
            orientation="h",
            bgcolor="rgba(0,0,0,0)",
            font=dict(color="#f2f2f2"),
            yanchor="bottom",
            y=1.02,
            x=0.0,
        ),
    )

    st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})


# ============================================================
# ACESSIBILIDADE
# ============================================================

def render_accessibility_controls(store: Store) -> None:
    settings = store.settings()
    col1, col2 = st.columns([1, 1])
    with col1:
        scale = st.slider(
            "Tamanho das letras",
            min_value=0.90,
            max_value=1.55,
            value=float(settings.get("font_scale", 1.0)),
            step=0.05,
        )
    with col2:
        contrast = st.toggle("Contraste reforçado", value=bool(settings.get("high_contrast", False)))
    if scale != settings.get("font_scale") or contrast != settings.get("high_contrast"):
        settings["font_scale"] = scale
        settings["high_contrast"] = contrast
        store.save_settings(settings)
        st.rerun()


def audio_description_text(work: Dict[str, Any], user_tags: List[str]) -> str:
    base = [
        f"Imagem referente à obra {work.get('title', '')}, de {work.get('artist', '')}.",
        work.get("audio_seed", ""),
        f"Museu: {work.get('museum', '')}.",
        f"Período: {work.get('period', '')}.",
        f"Técnica: {work.get('technique', '')}.",
    ]
    if user_tags:
        base.append("Palavras marcadas até agora nesta imagem: " + ", ".join(sorted(set(user_tags))[:12]) + ".")
    return " ".join([b for b in base if b]).strip()


def easy_read_text(work: Dict[str, Any]) -> str:
    return (
        f"Leitura simplificada: esta imagem mostra a obra {work.get('title', '')}. "
        f"Ela é atribuída a {work.get('artist', '')}. "
        f"O museu indicado é {work.get('museum', '')}. "
        f"A técnica informada é {work.get('technique', '')} e o período registrado é {work.get('period', '')}. "
        f"O objetivo desta tela é permitir que você observe a imagem e escolha palavras que descrevam o que percebe."
    )


def libras_gloss_text(text: str) -> str:
    tokens = tokenize(text)
    if not tokens:
        return "SEM TEXTO MARCADO"
    return " · ".join(tok.upper() for tok in tokens[:18])


def render_tts_and_avatar(selected_text: str, title: str = "Acessibilidade") -> None:
    safe_text = html_escape(selected_text or "Nenhum texto selecionado.")
    gloss = html_escape(libras_gloss_text(selected_text))
    html = f"""
    <div style="padding:14px 0 0 0;">
      <div style="
        display:grid;
        grid-template-columns: minmax(220px, 280px) 1fr;
        gap:18px;
        align-items:start;
      ">
        <div style="
          background:rgba(255,255,255,0.08);
          border:1px solid rgba(255,255,255,0.16);
          border-radius:22px;
          padding:18px;
          backdrop-filter:blur(16px);
        ">
          <div style="font-family:'Times New Roman',serif;color:#f2f2f2;font-size:20px;margin-bottom:12px;">
            Avatar 3D experimental
          </div>

          <div style="perspective:900px; height:260px; position:relative; margin-bottom:14px;">
            <div id="folk-avatar" style="
              width:120px;height:220px;position:absolute;left:50%;transform:translateX(-50%) rotateY(-18deg);
              transform-style:preserve-3d;
              animation:floatAvatar 4s ease-in-out infinite;
            ">
              <div style="
                position:absolute; width:78px; height:78px; left:21px; top:0;
                border-radius:50%; background:linear-gradient(145deg,#d9d9d9,#9a9a9a);
                box-shadow:0 8px 18px rgba(0,0,0,0.25); transform:translateZ(12px);
              "></div>
              <div style="
                position:absolute; width:10px;height:10px;border-radius:50%;background:#222;
                left:42px; top:28px; transform:translateZ(18px);
              "></div>
              <div style="
                position:absolute; width:10px;height:10px;border-radius:50%;background:#222;
                left:69px; top:28px; transform:translateZ(18px);
              "></div>
              <div style="
                position:absolute; width:26px;height:6px;border-radius:12px;background:#333;
                left:47px; top:50px; transform:translateZ(18px);
              "></div>
              <div style="
                position:absolute; width:92px;height:96px;left:14px;top:82px;border-radius:24px;
                background:linear-gradient(145deg,#58657c,#20293b); transform:translateZ(4px);
              "></div>
              <div id="armL" style="
                position:absolute;width:18px;height:86px;left:-2px;top:94px;border-radius:18px;
                background:linear-gradient(145deg,#7b8798,#364153);transform-origin:50% 12%;
                transform:rotateZ(28deg) translateZ(6px);animation:signLeft 1.7s ease-in-out infinite;
              "></div>
              <div id="armR" style="
                position:absolute;width:18px;height:86px;right:-2px;top:94px;border-radius:18px;
                background:linear-gradient(145deg,#7b8798,#364153);transform-origin:50% 12%;
                transform:rotateZ(-28deg) translateZ(6px);animation:signRight 1.7s ease-in-out infinite;
              "></div>
              <div style="
                position:absolute;width:18px;height:88px;left:34px;top:170px;border-radius:18px;
                background:linear-gradient(145deg,#6f7988,#2d3647);transform:translateZ(4px);
              "></div>
              <div style="
                position:absolute;width:18px;height:88px;left:68px;top:170px;border-radius:18px;
                background:linear-gradient(145deg,#6f7988,#2d3647);transform:translateZ(4px);
              "></div>
            </div>
          </div>

          <button onclick="speakSelectedText()" style="
            width:100%;padding:12px 16px;border:none;border-radius:16px;
            background:#0e1826;color:#fff;cursor:pointer;font-family:'Times New Roman',serif;font-size:18px;
          ">Ler em voz alta</button>
        </div>

        <div style="
          background:rgba(255,255,255,0.08);
          border:1px solid rgba(255,255,255,0.16);
          border-radius:22px;
          padding:18px;
          backdrop-filter:blur(16px);
          color:#f2f2f2;
          font-family:'Times New Roman',serif;
        ">
          <div style="font-size:22px; margin-bottom:12px;">Texto atual</div>
          <div style="font-size:20px; line-height:1.65; margin-bottom:14px;">{safe_text}</div>
          <div style="font-size:19px; margin-bottom:6px;">Apoio em Libras (glosa textual)</div>
          <div style="
            font-size:18px; line-height:1.6; background:rgba(255,255,255,0.06);
            border-radius:16px; padding:14px;
          ">{gloss}</div>
        </div>
      </div>
    </div>

    <script>
      function speakSelectedText() {{
        const text = `{safe_text}`.replace(/&lt;/g,"<").replace(/&gt;/g,">").replace(/&amp;/g,"&");
        if (!window.speechSynthesis) {{
          alert("Seu navegador não oferece síntese de voz.");
          return;
        }}
        const u = new SpeechSynthesisUtterance(text);
        u.lang = "pt-BR";
        u.rate = 0.95;
        u.pitch = 1.0;
        window.speechSynthesis.cancel();
        window.speechSynthesis.speak(u);
      }}
    </script>

    <style>
      @keyframes floatAvatar {{
        0% {{ transform:translateX(-50%) rotateY(-18deg) translateY(0px); }}
        50% {{ transform:translateX(-50%) rotateY(-8deg) translateY(-6px); }}
        100% {{ transform:translateX(-50%) rotateY(-18deg) translateY(0px); }}
      }}
      @keyframes signLeft {{
        0% {{ transform:rotateZ(28deg) translateZ(6px); }}
        50% {{ transform:rotateZ(6deg) translateZ(10px); }}
        100% {{ transform:rotateZ(28deg) translateZ(6px); }}
      }}
      @keyframes signRight {{
        0% {{ transform:rotateZ(-28deg) translateZ(6px); }}
        50% {{ transform:rotateZ(-6deg) translateZ(10px); }}
        100% {{ transform:rotateZ(-28deg) translateZ(6px); }}
      }}
    </style>
    """
    components.html(html, height=430, scrolling=False)


# ============================================================
# PDF
# ============================================================

def build_admin_pdf(store: Store, pack: LearningPack) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=1.4 * cm,
        rightMargin=1.4 * cm,
        topMargin=1.2 * cm,
        bottomMargin=1.2 * cm,
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="TitleFolk", parent=styles["Title"], fontName="Times-Roman", fontSize=22, leading=26))
    styles.add(ParagraphStyle(name="BodyFolk", parent=styles["BodyText"], fontName="Times-Roman", fontSize=11.5, leading=15))

    story = []
    story.append(Paragraph("folksonomia — relatório analítico", styles["TitleFolk"]))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(build_summary_text(store, pack), styles["BodyFolk"]))
    story.append(Spacer(1, 0.4 * cm))

    tags = store.tags()
    validations = store.validations()
    works = store.works()
    inter = compute_interoperability(store)

    resumo_table = Table(
        [
            ["Obras", str(len(works)), "Tags", str(len(tags)), "Validações", str(len(validations)), "Conceitos", str(len(pack.concept_by_label))],
            ["Coincidem com instituição", str(inter["institution_match"]), "Coincidem com open data", str(inter["external_match"]), "Integrações aprovadas", str(inter["integrated"]), "Exemplos de treino", str(pack.trained_examples)],
        ],
        colWidths=[4.2 * cm, 2.2 * cm, 3.2 * cm, 2.2 * cm, 3.2 * cm, 2.2 * cm, 3.0 * cm, 2.2 * cm],
    )
    resumo_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1d2a3a")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f1f1f1")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d3d3d3")),
                ("FONTNAME", (0, 0), (-1, -1), "Times-Roman"),
                ("FONTSIZE", (0, 0), (-1, -1), 10.5),
                ("LEADING", (0, 0), (-1, -1), 12),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    story.append(resumo_table)
    story.append(Spacer(1, 0.4 * cm))

    periods = tags_by_period(tags)
    story.append(Paragraph("análise temporal", styles["Heading2"]))
    day_lines = []
    for day, items in sorted(periods["day"].items()):
        tag_list = ", ".join(sorted(set(str(i.get("tag", "")) for i in items))[:10])
        day_lines.append(f"{day}: {len(items)} marcações — {tag_list}")
    story.append(Paragraph("<br/>".join(day_lines[:20]) or "Sem dados temporais.", styles["BodyFolk"]))
    story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph("variantes ortográficas", styles["Heading2"]))
    ortho = orthographic_groups(tags)
    ortho_lines = [f"{g['base']}: {', '.join(g['variants'])}" for g in ortho[:20]]
    story.append(Paragraph("<br/>".join(ortho_lines) or "Sem variantes fortes nesta execução.", styles["BodyFolk"]))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    store.save_report_meta({"created_at": now_iso(), "name": "relatorio_admin_pdf", "size": len(pdf_bytes)})
    return pdf_bytes


# ============================================================
# ESTILO
# ============================================================

def inject_css(store: Store) -> None:
    settings = store.settings()
    scale = float(settings.get("font_scale", 1.0))
    high_contrast = bool(settings.get("high_contrast", False))
    fg = "#111111" if not high_contrast else "#000000"
    muted = "#505050" if not high_contrast else "#151515"
    border = "rgba(255,255,255,0.28)" if not high_contrast else "rgba(0,0,0,0.18)"
    glass = "rgba(255,255,255,0.22)" if not high_contrast else "rgba(255,255,255,0.34)"

    st.markdown(
        f"""
        <style>
        :root {{
            --font-scale: {scale};
            --fg: {fg};
            --muted: {muted};
            --border: {border};
            --glass: {glass};
        }}

        html, body, [class*="css"], .stApp {{
            font-family: "Times New Roman", Georgia, serif !important;
            color: var(--fg) !important;
        }}

        .stApp {{
            background:
              radial-gradient(circle at 12% 18%, rgba(255,255,255,0.85), rgba(255,255,255,0.08) 38%, transparent 39%),
              radial-gradient(circle at 78% 30%, rgba(255,255,255,0.45), rgba(255,255,255,0.04) 35%, transparent 36%),
              linear-gradient(180deg, #e2e2e2 0%, #dcdcdc 38%, #d9d9d9 100%);
            background-attachment: fixed;
        }}

        #MainMenu, footer, header, .stDeployButton {{
            visibility: hidden;
        }}

        .block-container {{
            max-width: 1480px;
            padding-top: 1.2rem;
            padding-bottom: 3rem;
        }}

        h1, h2, h3, h4, h5, h6, p, span, label, li, div {{
            color: var(--fg) !important;
            font-family: "Times New Roman", Georgia, serif !important;
        }}

        h1 {{
            font-size: calc(2.4rem * var(--font-scale)) !important;
        }}
        h2 {{
            font-size: calc(1.8rem * var(--font-scale)) !important;
        }}
        h3 {{
            font-size: calc(1.32rem * var(--font-scale)) !important;
        }}

        .glass {{
            background: var(--glass);
            border: 1px solid var(--border);
            backdrop-filter: blur(18px);
            -webkit-backdrop-filter: blur(18px);
            box-shadow: 0 10px 30px rgba(255,255,255,0.16), inset 0 1px 0 rgba(255,255,255,0.26);
            border-radius: 24px;
        }}

        .section-card {{
            background: var(--glass);
            border: 1px solid var(--border);
            backdrop-filter: blur(18px);
            -webkit-backdrop-filter: blur(18px);
            border-radius: 26px;
            padding: 1.2rem 1.2rem;
            box-shadow: 0 12px 30px rgba(255,255,255,0.12);
        }}

        .metric-box {{
            padding: 1.05rem 1.1rem;
            border-radius: 22px;
            background: rgba(255,255,255,0.16);
            border: 1px solid var(--border);
            min-height: 150px;
        }}

        .metric-kicker {{
            font-size: calc(0.98rem * var(--font-scale));
            letter-spacing: 0.18em;
            text-transform: uppercase;
            color: var(--muted) !important;
            margin-bottom: 0.6rem;
        }}

        .metric-value {{
            font-size: calc(3rem * var(--font-scale));
            font-weight: 700;
            margin-bottom: 0.3rem;
        }}

        .metric-sub {{
            font-size: calc(0.92rem * var(--font-scale));
            color: var(--muted) !important;
            line-height: 1.5;
        }}

        .topbar {{
            display:flex;
            justify-content:space-between;
            align-items:center;
            gap:1rem;
            padding: 1rem 1.2rem;
            margin-bottom: 1rem;
            background: rgba(255,255,255,0.22);
            border:1px solid var(--border);
            border-radius: 28px;
            backdrop-filter: blur(18px);
        }}

        .brand-title {{
            font-size: calc(2.25rem * var(--font-scale));
            font-weight: 700;
            letter-spacing: -0.04em;
        }}

        .brand-sub {{
            font-size: calc(1.02rem * var(--font-scale));
            color: var(--muted) !important;
        }}

        .mini-pills {{
            display:flex;
            flex-wrap:wrap;
            gap:0.6rem;
            justify-content:flex-end;
        }}

        .mini-pill {{
            padding: 0.62rem 0.85rem;
            border-radius: 999px;
            background: rgba(255,255,255,0.20);
            border: 1px solid var(--border);
            font-size: calc(0.98rem * var(--font-scale));
            color: var(--fg) !important;
        }}

        .public-intro {{
            padding: 0.8rem 0.4rem 0.6rem 0.4rem;
            font-size: calc(1.02rem * var(--font-scale));
            line-height: 1.7;
            color: var(--muted) !important;
        }}

        div[data-testid="stButton"] > button {{
            width:100%;
            border-radius: 18px !important;
            background: #0d1624 !important;
            color: #ffffff !important;
            border: 1px solid rgba(255,255,255,0.18) !important;
            padding: 0.72rem 1rem !important;
            font-size: calc(1.03rem * var(--font-scale)) !important;
            transition: all 0.22s ease !important;
            box-shadow: 0 8px 16px rgba(0,0,0,0.14) !important;
        }}

        div[data-testid="stButton"] > button:hover {{
            transform: translateY(-1px);
            background: #101e30 !important;
        }}

        .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] > div {{
            background: rgba(255,255,255,0.22) !important;
            color: #111111 !important;
            border-radius: 18px !important;
            border: 1px solid rgba(0,0,0,0.12) !important;
            font-size: calc(1.05rem * var(--font-scale)) !important;
        }}

        .stTextArea textarea::placeholder, .stTextInput input::placeholder {{
            color: #4a4a4a !important;
        }}

        .tag-pill {{
            display:inline-flex;
            align-items:center;
            gap:0.35rem;
            padding:0.38rem 0.72rem;
            border-radius:999px;
            margin:0.18rem 0.18rem 0 0;
            background: rgba(255,255,255,0.16);
            border:1px solid var(--border);
            font-size: calc(0.94rem * var(--font-scale));
            color: var(--fg) !important;
        }}

        .small-note {{
            font-size: calc(0.93rem * var(--font-scale));
            color: var(--muted) !important;
            line-height: 1.55;
        }}

        .clean-card {{
            background: rgba(255,255,255,0.14);
            border: 1px solid var(--border);
            border-radius: 24px;
            padding: 1rem;
            backdrop-filter: blur(16px);
        }}

        .work-card {{
            background: rgba(255,255,255,0.14);
            border: 1px solid rgba(255,255,255,0.26);
            border-radius: 24px;
            overflow: hidden;
            transition: transform .22s ease, box-shadow .22s ease;
            backdrop-filter: blur(15px);
            box-shadow: 0 10px 20px rgba(255,255,255,0.10);
        }}

        .work-card:hover {{
            transform: translateY(-3px);
            box-shadow: 0 16px 28px rgba(255,255,255,0.14);
        }}

        .work-image {{
            width:100%;
            aspect-ratio:1/1;
            object-fit:cover;
            display:block;
            border-radius: 18px;
        }}

        .instruction-box {{
            background: rgba(255,255,255,0.12);
            border:1px solid var(--border);
            border-radius: 18px;
            padding:0.9rem 1rem;
            line-height:1.65;
        }}

        .admin-note {{
            padding:0.95rem 1rem;
            border-radius:22px;
            background: rgba(255,255,255,0.14);
            border: 1px solid var(--border);
            line-height:1.75;
        }}

        .queue-card {{
            background: rgba(255,255,255,0.12);
            border: 1px solid var(--border);
            border-radius: 24px;
            padding: 1rem 1rem;
            margin-bottom: 1rem;
        }}

        .tiny-kicker {{
            letter-spacing:0.17em;
            text-transform: uppercase;
            color: var(--muted) !important;
            font-size: calc(0.86rem * var(--font-scale));
            margin-bottom:0.28rem;
        }}

        .plot-shell {{
            background: rgba(255,255,255,0.12);
            border:1px solid var(--border);
            border-radius:24px;
            padding:0.8rem;
        }}

        .search-hit {{
            padding:0.9rem 1rem;
            border-radius: 18px;
            background: rgba(255,255,255,0.10);
            border:1px solid var(--border);
            margin-bottom:0.7rem;
        }}

        .temporal-card {{
            padding:0.9rem 1rem;
            border-radius:18px;
            background: rgba(255,255,255,0.10);
            border:1px solid var(--border);
            margin-bottom:0.6rem;
        }}

        .stTabs [data-baseweb="tab-list"] {{
            gap: .55rem;
            background: rgba(255,255,255,0.12);
            border-radius: 18px;
            padding: 0.4rem;
        }}

        .stTabs [data-baseweb="tab"] {{
            border-radius: 14px !important;
            padding: 0.55rem 0.85rem !important;
            height: auto !important;
            background: rgba(255,255,255,0.08);
        }}

        .stTabs [aria-selected="true"] {{
            background: rgba(255,255,255,0.25) !important;
        }}

        @media (max-width: 900px) {{
            .topbar {{
                display:block;
            }}
            .mini-pills {{
                justify-content:flex-start;
                margin-top:0.8rem;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# COMPONENTES DE TEXTO
# ============================================================

def brand_header(store: Store, public: bool = True) -> None:
    pack = build_learning_pack(store)
    tags = store.tags()
    validations = store.validations()
    html = f"""
    <div class="topbar">
      <div>
        <div class="brand-title">{APP_TITLE}</div>
        <div class="brand-sub">{'marcação pública de obras' if public else 'administração documental e conectividade'}</div>
      </div>
      <div class="mini-pills">
        <div class="mini-pill">obras {len(store.works())}</div>
        <div class="mini-pill">tags {len(tags)}</div>
        <div class="mini-pill">validações {len(validations)}</div>
        <div class="mini-pill">conceitos {len(pack.concept_by_label)}</div>
      </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def metric_box(title: str, value: str, subtitle: str) -> str:
    return f"""
    <div class="metric-box">
      <div class="metric-kicker">{html_escape(title)}</div>
      <div class="metric-value">{html_escape(value)}</div>
      <div class="metric-sub">{html_escape(subtitle)}</div>
    </div>
    """


def section_title(text: str, desc: Optional[str] = None) -> None:
    st.markdown(f"<h2 style='margin-bottom:0.2rem'>{html_escape(text)}</h2>", unsafe_allow_html=True)
    if desc:
        st.markdown(f"<div class='small-note' style='margin-bottom:0.9rem'>{html_escape(desc)}</div>", unsafe_allow_html=True)


# ============================================================
# AUTENTICAÇÃO / ESTADO
# ============================================================

def init_session() -> None:
    if "user_id" not in st.session_state:
        st.session_state["user_id"] = base64.b64encode(os.urandom(9)).decode("ascii")
    if "user_label" not in st.session_state:
        st.session_state["user_label"] = generate_user_label()
    if "questionnaire_done" not in st.session_state:
        st.session_state["questionnaire_done"] = False
    if "questionnaire_answers" not in st.session_state:
        st.session_state["questionnaire_answers"] = {}
    if "selected_work_id" not in st.session_state:
        st.session_state["selected_work_id"] = None
    if "admin_logged" not in st.session_state:
        st.session_state["admin_logged"] = False
    if "accessibility_text" not in st.session_state:
        st.session_state["accessibility_text"] = ""
    if "public_tab" not in st.session_state:
        st.session_state["public_tab"] = "explorar"


def admin_login_ok(username: str, password: str) -> bool:
    return username == ADMIN_USERNAME and password == ADMIN_PASSWORD


# ============================================================
# INTERFACES PÚBLICAS
# ============================================================

def render_questionnaire(store: Store) -> None:
    brand_header(store, public=True)
    section_title("Primeiro passo", "Responda rapidamente e depois siga para a marcação das imagens.")

    with st.container():
        c1, c2 = st.columns(2)
        with c1:
            q1 = st.selectbox(
                "Com que frequência você visita museus?",
                ["nunca", "raramente", "às vezes", "frequentemente"],
            )
            q2 = st.selectbox(
                "Você já ouviu falar sobre documentação museológica?",
                ["nenhum", "pouco", "básico", "sim, conheço"],
            )
        with c2:
            q3 = st.text_area(
                "O que você entende por tags aplicadas a acervos?",
                placeholder="Descreva com suas palavras.",
                height=180,
            )
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        if st.button("Liberar acesso às obras"):
            if not q3.strip():
                st.error("Escreva sua resposta antes de continuar.")
            else:
                st.session_state["questionnaire_done"] = True
                st.session_state["questionnaire_answers"] = {"q1": q1, "q2": q2, "q3": q3}
                store.save_user_if_missing(
                    st.session_state["user_id"],
                    st.session_state["user_label"],
                    st.session_state["questionnaire_answers"],
                )
                st.rerun()


def user_tags_for_work(store: Store, work_id: int, user_id: str) -> List[Dict[str, Any]]:
    return [t for t in store.tags() if safe_int(t.get("work_id")) == work_id and str(t.get("user_id")) == user_id]


def render_public_gallery(store: Store) -> None:
    brand_header(store, public=True)
    st.markdown(
        "<div class='instruction-box'>Observe a imagem, clique em <strong>marcar</strong> e escreva a palavra que melhor descreve o que você percebe. Você pode registrar mais de uma palavra por obra.</div>",
        unsafe_allow_html=True,
    )
    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    works = store.works()
    cols = st.columns(3)
    for idx, work in enumerate(works):
        with cols[idx % 3]:
            st.markdown("<div class='work-card'>", unsafe_allow_html=True)
            st.image(work["image"], use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)
            if st.button("Marcar", key=f"pick_{work['id']}"):
                st.session_state["selected_work_id"] = safe_int(work["id"])
                st.session_state["accessibility_text"] = easy_read_text(work)
                st.rerun()

            if st.session_state.get("selected_work_id") == safe_int(work["id"]):
                with st.container():
                    tag_text = st.text_input(
                        "Sua tag",
                        key=f"tag_small_{work['id']}",
                        placeholder="ex.: azul, noite, dor, estrela",
                    )
                    note = st.text_input(
                        "Comentário opcional",
                        key=f"note_small_{work['id']}",
                        placeholder="se quiser, explique rapidamente sua escolha",
                    )
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("Registrar tag", key=f"save_tag_{work['id']}"):
                            if not tag_text.strip():
                                st.warning("Digite uma palavra antes de registrar.")
                            else:
                                store.add_tag(
                                    {
                                        "user_id": st.session_state["user_id"],
                                        "work_id": safe_int(work["id"]),
                                        "tag": tag_text.strip(),
                                        "notes": note.strip(),
                                        "created_at": now_iso(),
                                    }
                                )
                                st.session_state["accessibility_text"] = f"Tag registrada: {tag_text.strip()}"
                                st.success("Tag registrada.")
                                st.rerun()
                    with c2:
                        if st.button("Fechar", key=f"close_{work['id']}"):
                            st.session_state["selected_work_id"] = None
                            st.rerun()

                    own = user_tags_for_work(store, safe_int(work["id"]), st.session_state["user_id"])
                    if own:
                        pills = "".join(
                            f"<span class='tag-pill'>{html_escape(t['tag'])}</span>"
                            for t in own[-12:]
                        )
                        st.markdown(pills, unsafe_allow_html=True)

                    audio_text = audio_description_text(work, [t["tag"] for t in own])
                    st.session_state["accessibility_text"] = audio_text
                    render_tts_and_avatar(audio_text)

    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
    if st.button("Abrir administração"):
        st.session_state["public_tab"] = "admin"


# ============================================================
# ADMIN
# ============================================================

def render_admin_login(store: Store) -> None:
    brand_header(store, public=False)
    section_title("Entrar na administração", "Use o acesso administrativo para revisar marcações, validar entidades e acompanhar a conectividade dos metadados.")

    username = st.text_input("Login administrativo")
    password = st.text_input("Senha administrativa", type="password")
    if st.button("Entrar na administração"):
        if admin_login_ok(username, password):
            st.session_state["admin_logged"] = True
            st.rerun()
        else:
            st.error("Acesso não reconhecido.")


def render_admin_overview(store: Store, pack: LearningPack) -> None:
    section_title(
        "Visão geral",
        "O painel destaca o fluxo documental, o que já foi integrado ao vocabulário institucional e o que ainda precisa de revisão.",
    )
    tags = store.tags()
    validations = store.validations()
    approved = [v for v in validations if v.get("decision") == "approved"]
    pending = [t for t in tags if safe_int(t.get("id")) not in {safe_int(v.get("tag_id")) for v in validations}]
    inter = compute_interoperability(store)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(metric_box("obras monitoradas", str(len(store.works())), "base atualmente disponível"), unsafe_allow_html=True)
    with c2:
        st.markdown(metric_box("tags coletadas", str(len(tags)), "fluxo público registrado"), unsafe_allow_html=True)
    with c3:
        st.markdown(metric_box("fila curatorial", str(len(pending)), "marcações ainda sem decisão"), unsafe_allow_html=True)
    with c4:
        st.markdown(metric_box("validações concluídas", str(len(approved)), "entradas aprovadas"), unsafe_allow_html=True)

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class='admin-note'>
        <strong>Resumo atual.</strong> {html_escape(build_summary_text(store, pack))}
        <br/><br/>
        <strong>Interoperabilidade.</strong> {inter['institution_match']} marcações já coincidem com descritores institucionais, 
        {inter['external_match']} dialogam diretamente com pontos externos e {inter['integrated']} foram absorvidas na camada validada.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
    section_title("Busca conectada", "Pesquise com base em metadados, conceitos, tags públicas e validações.")
    query = st.text_input("Buscar obra, artista, museu, técnica, material, lugar, período ou tag")
    if query.strip():
        results = search_works(query, pack)
        if not results:
            st.info("Nenhum resultado apareceu para esta busca.")
        for r in results:
            st.markdown(
                f"""
                <div class='search-hit'>
                  <strong>{html_escape(r['title'])}</strong><br/>
                  correspondência: {r['score']:.2f}<br/>
                  artista: {html_escape(r['work'].get('artist',''))} · museu: {html_escape(r['work'].get('museum',''))}<br/>
                  período: {html_escape(r['work'].get('period',''))} · técnica: {html_escape(r['work'].get('technique',''))}
                </div>
                """,
                unsafe_allow_html=True,
            )


def validation_examples_for_tag(tag_text: str, store: Store, pack: LearningPack, limit: int = 3) -> List[str]:
    tags = store.tags()
    examples = []
    for t in tags:
        other = str(t.get("tag", "")).strip()
        if other and other != tag_text:
            s = max(similarity(tag_text, other), jaccard_tokens(tag_text, other))
            if s >= 0.58:
                work = next((w for w in store.works() if safe_int(w["id"]) == safe_int(t.get("work_id"))), None)
                label = f"{other} — {work.get('title','obra') if work else 'obra'}"
                examples.append((s, label))
    examples.sort(reverse=True)
    out = []
    for _, item in examples[:limit]:
        out.append(item)
    return out


def render_admin_validation(store: Store, pack: LearningPack) -> None:
    section_title(
        "Monitoramento, supervisão e validação",
        "Aqui a equipe revê entidades extraídas, compara grafias, observa confusões e decide como cada marcação deve entrar no grafo da instituição.",
    )

    tags = store.tags()
    works = {safe_int(w["id"]): w for w in store.works()}
    validations = store.validations()
    validated_ids = {safe_int(v.get("tag_id")) for v in validations}

    pending = [t for t in tags if safe_int(t.get("id")) not in validated_ids]
    if not pending:
        st.success("Não há marcações pendentes agora.")
    else:
        for tag in pending[:24]:
            work = works.get(safe_int(tag.get("work_id")))
            if not work:
                continue
            pred = predict_tag(str(tag.get("tag", "")), work, pack)
            examples = validation_examples_for_tag(str(tag.get("tag", "")), store, pack, 3)
            current_audio = audio_description_text(work, [tag.get("tag", "")])
            st.markdown("<div class='queue-card'>", unsafe_allow_html=True)
            st.markdown(
                f"""
                <div class='tiny-kicker'>{html_escape(str(tag.get('tag','')).upper())} · {html_escape(work.get('title',''))}</div>
                <div style='font-size:1.25rem;font-weight:700;margin-bottom:0.45rem'>previsão {html_escape(pred['category'])} · confiança {pred['confidence']:.2f}</div>
                <div class='small-note' style='margin-bottom:0.4rem'>
                  conceito sugerido: <strong>{html_escape(pred['concept'] or '—')}</strong><br/>
                  base da sugestão: {html_escape(pred['reason'])}<br/>
                  museu: {html_escape(work.get('museum',''))} · período: {html_escape(work.get('period',''))} · técnica: {html_escape(work.get('technique',''))}
                </div>
                """,
                unsafe_allow_html=True,
            )

            if examples:
                st.markdown("<div class='small-note'><strong>3 exemplos comparativos.</strong> " + "; ".join(html_escape(x) for x in examples) + "</div>", unsafe_allow_html=True)

            with st.form(f"validation_form_{tag['id']}"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    validated_category = st.selectbox(
                        "Categoria validada",
                        ENTITY_LABELS,
                        index=max(0, ENTITY_LABELS.index(pred["category"]) if pred["category"] in ENTITY_LABELS else 0),
                    )
                with c2:
                    concept_options = ["nenhum"] + sorted(list(pack.concept_by_label.keys()))[:800]
                    default_idx = concept_options.index(pred["concept"]) if pred["concept"] in concept_options else 0
                    reconciled_concept = st.selectbox("Conceito reconciliado", concept_options, index=default_idx)
                with c3:
                    decision = st.selectbox("Decisão", ["approved", "rejected", "review_later"])

                curator_notes = st.text_area("Notas curatoriais", placeholder="Use este campo para registrar contexto, dúvida, erro percebido ou justificativa da decisão.", height=110)
                submitted = st.form_submit_button("Registrar validação")
                if submitted:
                    store.add_validation(
                        {
                            "tag_id": safe_int(tag["id"]),
                            "validated_category": validated_category,
                            "reconciled_concept": "" if reconciled_concept == "nenhum" else reconciled_concept,
                            "decision": decision,
                            "curator_notes": curator_notes.strip(),
                            "predicted_category": pred["category"],
                            "predicted_concept": pred["concept"],
                            "confidence": pred["confidence"],
                            "created_at": now_iso(),
                        }
                    )
                    st.success("Validação registrada.")
                    st.rerun()

            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            render_tts_and_avatar(current_audio, "Acessibilidade da validação")
            st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    section_title("Erros, grafias e recorrências", "As verificações abaixo ajudam a identificar aproximações fortes, confusões e padrões de preenchimento.")
    ortho = orthographic_groups(tags)
    common = common_links_analysis(store)
    balance = comparative_fill_balance(store)["rows"]

    t1, t2, t3 = st.tabs(["grafias próximas", "ligações em comum", "balanceamento do preenchimento"])
    with t1:
        if not ortho:
            st.info("Não apareceram variantes ortográficas fortes neste momento.")
        for item in ortho[:25]:
            st.markdown(
                f"<div class='temporal-card'><strong>{html_escape(item['base'])}</strong><br/>variantes: {html_escape(', '.join(item['variants']))}</div>",
                unsafe_allow_html=True,
            )
    with t2:
        if not common:
            st.info("Ainda não há ligações fortes em comum para exibir.")
        for item in common[:24]:
            st.markdown(
                f"<div class='temporal-card'><strong>{html_escape(item['work_title'])}</strong><br/>{html_escape(item['tag'])} → {html_escape(', '.join(item['related']))}</div>",
                unsafe_allow_html=True,
            )
    with t3:
        for row in balance[:24]:
            st.markdown(
                f"<div class='temporal-card'><strong>{html_escape(row['title'])}</strong><br/>tags: {row['total_tags']} · aprovadas: {row['approved_tags']} · termos institucionais: {row['institutional_terms']} · pontos externos: {row['external_points']} · equilíbrio: {row['balance']}</div>",
                unsafe_allow_html=True,
            )


def temporal_series(cards: Dict[str, List[Dict[str, Any]]], title: str, label_formatter=lambda x: x) -> go.Figure:
    keys = sorted(cards.keys())
    counts = [len(cards[k]) for k in keys]
    labels = [label_formatter(k) for k in keys]
    fig = go.Figure(
        go.Bar(
            x=labels,
            y=counts,
            marker_color="#84bff2",
            hovertemplate="%{x}<br>marcações %{y}<extra></extra>",
        )
    )
    fig.update_layout(
        height=320,
        margin=dict(l=20, r=20, t=20, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#050a14",
        font=dict(color="#f3f3f3", family="Times New Roman"),
        xaxis=dict(title="", tickangle=-30, gridcolor="rgba(255,255,255,0.12)"),
        yaxis=dict(title="", gridcolor="rgba(255,255,255,0.12)"),
    )
    return fig


def render_admin_temporal(store: Store) -> None:
    section_title(
        "Análise temporal",
        "A leitura temporal acompanha as tags criadas por dia, mês e ano, detalhando o que entrou em cada período.",
    )
    tags = store.tags()
    periods = tags_by_period(tags)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("<div class='plot-shell'>", unsafe_allow_html=True)
        st.plotly_chart(temporal_series(periods["day"], "dia"), use_container_width=True, config={"displaylogo": False})
        st.markdown("</div>", unsafe_allow_html=True)
    with c2:
        st.markdown("<div class='plot-shell'>", unsafe_allow_html=True)
        st.plotly_chart(temporal_series(periods["month"], "mês", month_label), use_container_width=True, config={"displaylogo": False})
        st.markdown("</div>", unsafe_allow_html=True)
    with c3:
        st.markdown("<div class='plot-shell'>", unsafe_allow_html=True)
        st.plotly_chart(temporal_series(periods["year"], "ano"), use_container_width=True, config={"displaylogo": False})
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    t1, t2, t3 = st.tabs(["detalhamento por dia", "detalhamento por mês", "detalhamento por ano"])
    with t1:
        for day, items in sorted(periods["day"].items(), reverse=True)[:30]:
            labels = sorted(set(str(i.get("tag", "")) for i in items if i.get("tag")))
            st.markdown(
                f"<div class='temporal-card'><strong>{html_escape(day)}</strong><br/>{len(items)} marcações<br/>{html_escape(', '.join(labels[:16]))}</div>",
                unsafe_allow_html=True,
            )
    with t2:
        for month, items in sorted(periods["month"].items(), reverse=True)[:24]:
            labels = sorted(set(str(i.get("tag", "")) for i in items if i.get("tag")))
            st.markdown(
                f"<div class='temporal-card'><strong>{html_escape(month_label(month))}</strong><br/>{len(items)} marcações<br/>{html_escape(', '.join(labels[:16]))}</div>",
                unsafe_allow_html=True,
            )
    with t3:
        for year, items in sorted(periods["year"].items(), reverse=True)[:8]:
            labels = sorted(set(str(i.get("tag", "")) for i in items if i.get("tag")))
            st.markdown(
                f"<div class='temporal-card'><strong>{html_escape(year)}</strong><br/>{len(items)} marcações<br/>{html_escape(', '.join(labels[:18]))}</div>",
                unsafe_allow_html=True,
            )


def render_admin_web(store: Store, pack: LearningPack) -> None:
    section_title(
        "Teia 3D de conectividade",
        "Esta visualização reúne obras, artistas, museus, coleções, lugares, períodos, técnicas, materiais, tags institucionais, tags públicas, conceitos reconciliados e referências externas em um mesmo espaço navegável.",
    )
    render_connectivity_web_3d(store, pack)


def render_admin_works(store: Store) -> None:
    section_title(
        "Obras e metadados",
        "Inclua novas obras, revise metadados e remova registros que não devam permanecer na base.",
    )

    t1, t2 = st.tabs(["obras atuais", "inserir nova obra"])
    with t1:
        for work in store.works():
            st.markdown("<div class='queue-card'>", unsafe_allow_html=True)
            st.markdown(
                f"""
                <strong>{html_escape(work.get('title',''))}</strong><br/>
                artista: {html_escape(work.get('artist',''))} · museu: {html_escape(work.get('museum',''))}<br/>
                período: {html_escape(work.get('period',''))} · técnica: {html_escape(work.get('technique',''))} · material: {html_escape(work.get('material',''))}<br/>
                descritores institucionais: {html_escape(', '.join(work.get('institution_tags', [])))}<br/>
                open data: {html_escape(', '.join(work.get('open_data', [])))}
                """,
                unsafe_allow_html=True,
            )
            if st.button(f"Excluir {work.get('title','obra')}", key=f"rm_{work['id']}"):
                store.remove_work(safe_int(work["id"]))
                st.success("Obra excluída.")
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    with t2:
        with st.form("new_work_form"):
            title = st.text_input("Título")
            artist = st.text_input("Artista")
            year = st.text_input("Ano")
            museum = st.text_input("Museu")
            collection = st.text_input("Coleção")
            place = st.text_input("Lugar")
            period = st.text_input("Período")
            technique = st.text_input("Técnica")
            material = st.text_input("Material")
            description = st.text_area("Descrição")
            institution_tags = st.text_input("Descritores institucionais", placeholder="separe por vírgula")
            open_data = st.text_input("Referências externas", placeholder="separe por vírgula")
            image = st.text_input("URL da imagem")
            audio_seed = st.text_input("Base da áudio descrição")
            if st.form_submit_button("Inserir obra"):
                if not title.strip() or not image.strip():
                    st.error("Preencha pelo menos título e imagem.")
                else:
                    store.add_work(
                        {
                            "title": title.strip(),
                            "artist": artist.strip(),
                            "year": year.strip(),
                            "museum": museum.strip(),
                            "collection": collection.strip(),
                            "place": place.strip(),
                            "period": period.strip(),
                            "technique": technique.strip(),
                            "material": material.strip(),
                            "description": description.strip(),
                            "institution_tags": [x.strip() for x in institution_tags.split(",") if x.strip()],
                            "open_data": [x.strip() for x in open_data.split(",") if x.strip()],
                            "image": image.strip(),
                            "audio_seed": audio_seed.strip() or description.strip(),
                        }
                    )
                    st.success("Obra inserida.")
                    st.rerun()


def render_admin_accessibility(store: Store) -> None:
    section_title(
        "Acessibilidade",
        "Este painel reúne controle de tamanho de fonte, leitura simplificada, áudio e apoio em Libras por glosa com avatar 3D experimental.",
    )
    render_accessibility_controls(store)

    works = store.works()
    options = {f"{w['title']} — {w['artist']}": w for w in works}
    selected_label = st.selectbox("Escolha uma obra para leitura acessível", list(options.keys()))
    work = options[selected_label]
    user_tags = [t.get("tag", "") for t in store.tags() if safe_int(t.get("work_id")) == safe_int(work["id"])]
    text = audio_description_text(work, user_tags)
    st.markdown("<div class='admin-note'>" + html_escape(easy_read_text(work)) + "</div>", unsafe_allow_html=True)
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    render_tts_and_avatar(text)


def render_admin_export(store: Store, pack: LearningPack) -> None:
    section_title(
        "Exportar relatório",
        "Gere um PDF com a síntese das marcações, validações, análise temporal, variantes ortográficas e estado atual do aprendizado.",
    )
    if st.button("Gerar PDF administrativo"):
        try:
            pdf = build_admin_pdf(store, pack)
            st.download_button(
                "Baixar relatório PDF",
                data=pdf,
                file_name=f"folksonomia_relatorio_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                mime="application/pdf",
            )
        except Exception as e:
            st.error(f"Não foi possível gerar o PDF nesta execução: {e}")


def render_admin_main(store: Store) -> None:
    brand_header(store, public=False)
    pack = build_learning_pack(store)

    tabs = st.tabs(
        [
            "painel",
            "validação",
            "análise temporal",
            "teia 3D",
            "obras",
            "acessibilidade",
            "exportar",
        ]
    )
    with tabs[0]:
        render_admin_overview(store, pack)
    with tabs[1]:
        render_admin_validation(store, pack)
    with tabs[2]:
        render_admin_temporal(store)
    with tabs[3]:
        render_admin_web(store, pack)
    with tabs[4]:
        render_admin_works(store)
    with tabs[5]:
        render_admin_accessibility(store)
    with tabs[6]:
        render_admin_export(store, pack)

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    if st.button("Sair da administração"):
        st.session_state["admin_logged"] = False
        st.rerun()


# ============================================================
# APP
# ============================================================

def main() -> None:
    store = Store()
    init_session()
    inject_css(store)

    if st.session_state.get("public_tab") == "admin" and not st.session_state.get("admin_logged"):
        render_admin_login(store)
        return

    if st.session_state.get("admin_logged"):
        render_admin_main(store)
        return

    if not st.session_state.get("questionnaire_done"):
        render_questionnaire(store)
    else:
        render_public_gallery(store)


if __name__ == "__main__":
    main()
