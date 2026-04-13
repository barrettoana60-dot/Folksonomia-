from __future__ import annotations

import base64
import hashlib
import io
import json
import math
import os
import random
import re
import statistics
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
import streamlit as st

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    REPORTLAB_AVAILABLE = True
except ModuleNotFoundError:
    REPORTLAB_AVAILABLE = False

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import accuracy_score
    from sklearn.model_selection import train_test_split
    SKLEARN_AVAILABLE = True
except ModuleNotFoundError:
    TfidfVectorizer = None
    LogisticRegression = None
    accuracy_score = None
    train_test_split = None
    SKLEARN_AVAILABLE = False


# ============================================================
# CONFIGURAÇÃO GERAL
# ============================================================
st.set_page_config(page_title="folksonomia", layout="wide", initial_sidebar_state="collapsed")

APP_TITLE = "folksonomia"
DATA_DIR = Path("data_folksonomia")
WORKS_FILE = DATA_DIR / "works.json"
USERS_FILE = DATA_DIR / "users.json"
TAGS_FILE = DATA_DIR / "tags.json"
CONCEPTS_FILE = DATA_DIR / "concepts.json"
VALIDATIONS_FILE = DATA_DIR / "validations.json"
MODEL_STATE_FILE = DATA_DIR / "model_state.json"
SETTINGS_FILE = DATA_DIR / "settings.json"
ADMIN_FILE = DATA_DIR / "admin.json"

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "folksonomia2026"

ENTITY_LABELS = [
    "tema",
    "pessoa",
    "lugar",
    "periodo",
    "material",
    "tecnica",
    "iconografia",
    "evento_historico",
    "grupo_social_cultural",
    "indefinido",
]

SEED_TRAINING = {
    "tema": [
        "mulher", "religiao", "devoção", "fé", "trabalho", "família", "violência",
        "guerra", "paisagem", "natureza", "memória", "identidade", "poder",
        "cotidiano", "resistência", "ancestralidade", "alegria", "dor", "esperança"
    ],
    "pessoa": [
        "tarsila", "picasso", "leonardo", "velazquez", "maria", "jesus", "napoleao",
        "dom pedro", "van gogh", "portinari", "anita", "candido", "alice neel"
    ],
    "lugar": [
        "rio de janeiro", "brasil", "espanha", "madrid", "paris", "lisboa", "bahia",
        "amazônia", "europa", "africa", "minas gerais", "são paulo"
    ],
    "periodo": [
        "barroco", "renascimento", "moderno", "contemporâneo", "século xix", "século xx",
        "colonial", "imperial", "medieval", "oitocentista", "novecentista"
    ],
    "material": [
        "ouro", "madeira", "bronze", "ferro", "papel", "tela", "argila", "óleo",
        "mármore", "tinta", "gesso", "vidro", "cerâmica", "algodão"
    ],
    "tecnica": [
        "óleo sobre tela", "gravura", "escultura", "fotografia", "desenho", "aquarela",
        "litografia", "xilogravura", "bordado", "colagem", "instalação"
    ],
    "iconografia": [
        "cruz", "anjo", "coroa", "cavaleiro", "madona", "virgem", "santo", "cavalo",
        "sol", "lua", "espada", "barco", "flor", "coração"
    ],
    "evento_historico": [
        "independência", "abolição", "revolução", "segunda guerra", "primeira guerra",
        "ditadura", "república", "descobrimento"
    ],
    "grupo_social_cultural": [
        "indígena", "afro-brasileiro", "mulheres", "operários", "camponeses", "elite",
        "povo", "comunidade", "quilombola", "imigrantes"
    ],
    "indefinido": ["abstrato", "difícil", "forte", "interessante", "bonito"],
}

DEFAULT_WORKS = [
    {
        "id": 1,
        "title": "Guernica",
        "artist": "Pablo Picasso",
        "year": "1937",
        "image_url": "https://upload.wikimedia.org/wikipedia/en/7/74/PicassoGuernica.jpg",
        "description": "Pintura sobre guerra, dor coletiva, fragmentação, violência e memória histórica.",
        "institutional_terms": ["guerra", "violência", "memória", "história", "modernismo", "pintura"],
    },
    {
        "id": 2,
        "title": "A Noite Estrelada",
        "artist": "Vincent van Gogh",
        "year": "1889",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/e/ea/Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg",
        "description": "Paisagem noturna com céu em movimento, energia, cor intensa e sensação de contemplação.",
        "institutional_terms": ["paisagem", "céu", "noite", "pós-impressionismo", "óleo sobre tela"],
    },
    {
        "id": 3,
        "title": "Mona Lisa",
        "artist": "Leonardo da Vinci",
        "year": "1503",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/e/ec/Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_retouched.jpg",
        "description": "Retrato feminino de expressão enigmática, associado ao Renascimento e à história da arte.",
        "institutional_terms": ["retrato", "renascimento", "mulher", "expressão", "óleo"],
    },
]

PSEUDO_A = [
    "Arquivo", "Bruma", "Vidro", "Lume", "Rastro", "Prisma", "Cedro", "Lótus", "Marfim",
    "Traço", "Memória", "Neblina", "Grafo", "Atlas", "Fresta", "Matiz", "Pulso", "Limiar"
]
PSEUDO_B = [
    "Semântico", "Curatorial", "Moderno", "Assistido", "Profundo", "Documental", "Relacional",
    "Persistente", "Analítico", "Contextual", "Plural", "Translúcido", "Técnico", "Digital"
]

STOPWORDS = {
    "a", "o", "os", "as", "de", "da", "do", "das", "dos", "e", "em", "na", "no", "nas", "nos",
    "para", "por", "com", "sem", "um", "uma", "uns", "umas", "ao", "aos", "à", "às", "que", "se",
    "sobre", "sob", "entre", "como", "mais", "menos", "muito", "pouco", "ser", "estar", "foi", "era"
}


# ============================================================
# UTILITÁRIOS DE DADOS
# ============================================================

def ensure_storage() -> None:
    DATA_DIR.mkdir(exist_ok=True, parents=True)


def read_json(path: Path, default: Any) -> Any:
    ensure_storage()
    if not path.exists():
        return default
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def write_json(path: Path, data: Any) -> None:
    ensure_storage()
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def normalize_text(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"\s+", " ", text)
    return text


def clean_token(value: str) -> str:
    text = normalize_text(value)
    text = re.sub(r"[^a-z0-9à-úç\-\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def tokenize(value: str) -> List[str]:
    text = clean_token(value)
    return [tok for tok in text.split() if tok and tok not in STOPWORDS]


def text_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def random_alias() -> str:
    return f"{random.choice(PSEUDO_A)} {random.choice(PSEUDO_B)}"


def check_admin(username: str, password: str) -> bool:
    admin = read_json(ADMIN_FILE, {})
    if not admin:
        admin = {
            "username": ADMIN_USERNAME,
            "password_hash": hashlib.sha256(ADMIN_PASSWORD.encode()).hexdigest(),
        }
        write_json(ADMIN_FILE, admin)
    return (
        username == admin.get("username")
        and hashlib.sha256(password.encode()).hexdigest() == admin.get("password_hash")
    )


@st.cache_data(show_spinner=False)
def load_works() -> List[Dict[str, Any]]:
    works = read_json(WORKS_FILE, DEFAULT_WORKS)
    if not works:
        works = DEFAULT_WORKS
        write_json(WORKS_FILE, works)
    return works


@st.cache_data(show_spinner=False)
def load_users() -> pd.DataFrame:
    rows = read_json(USERS_FILE, [])
    return pd.DataFrame(rows) if rows else pd.DataFrame()


@st.cache_data(show_spinner=False)
def load_tags() -> pd.DataFrame:
    rows = read_json(TAGS_FILE, [])
    return pd.DataFrame(rows) if rows else pd.DataFrame()


@st.cache_data(show_spinner=False)
def load_concepts() -> pd.DataFrame:
    rows = read_json(CONCEPTS_FILE, [])
    return pd.DataFrame(rows) if rows else pd.DataFrame()


@st.cache_data(show_spinner=False)
def load_validations() -> pd.DataFrame:
    rows = read_json(VALIDATIONS_FILE, [])
    return pd.DataFrame(rows) if rows else pd.DataFrame()


@st.cache_data(show_spinner=False)
def load_settings() -> Dict[str, Any]:
    return read_json(SETTINGS_FILE, {"dark_gray_level": "medium_dark"})


def clear_caches() -> None:
    st.cache_data.clear()


# ============================================================
# CSS E INTERFACE
# ============================================================

def inject_css() -> None:
    st.markdown(
        """
        <style>
        :root {
            --bg-1: #111214;
            --bg-2: #17191d;
            --bg-3: #1e2126;
            --glass: rgba(255,255,255,0.08);
            --glass-strong: rgba(255,255,255,0.12);
            --border: rgba(255,255,255,0.16);
            --text: #f2f2f3;
            --muted: rgba(255,255,255,0.64);
            --accent: #d6d7da;
            --soft: rgba(255,255,255,0.05);
        }
        html, body, [class*="css"]  {
            font-family: "Times New Roman", Times, Georgia, serif !important;
        }
        .stApp {
            background:
                radial-gradient(circle at top left, rgba(255,255,255,0.05), transparent 30%),
                radial-gradient(circle at bottom right, rgba(255,255,255,0.04), transparent 30%),
                linear-gradient(135deg, var(--bg-1) 0%, var(--bg-2) 48%, var(--bg-3) 100%);
            color: var(--text);
        }
        #MainMenu, header, footer, .stDeployButton {visibility:hidden;}
        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 2.5rem;
            max-width: 1450px;
        }
        .topbar {
            position: sticky;
            top: 0;
            z-index: 999;
            margin-bottom: 1.2rem;
            padding: 1rem 1.3rem;
            border: 1px solid var(--border);
            border-radius: 22px;
            background: rgba(255,255,255,0.07);
            backdrop-filter: blur(22px) saturate(150%);
            -webkit-backdrop-filter: blur(22px) saturate(150%);
            box-shadow: 0 20px 50px rgba(0,0,0,0.22);
            display:flex;
            justify-content:space-between;
            align-items:center;
        }
        .brand {
            font-size: 2rem;
            letter-spacing: 0.08rem;
            color: #ffffff;
            font-weight: 700;
        }
        .brand-sub {
            font-size: 0.96rem;
            color: var(--muted);
        }
        .hero, .glass, .panel-card, .metric-card, .work-card, .soft-card {
            border: 1px solid var(--border);
            background: var(--glass);
            backdrop-filter: blur(22px) saturate(155%);
            -webkit-backdrop-filter: blur(22px) saturate(155%);
            border-radius: 24px;
            box-shadow: 0 25px 60px rgba(0,0,0,0.20);
        }
        .hero {
            padding: 2.6rem;
            margin-bottom: 1.2rem;
        }
        .hero h1 {
            font-size: 3rem;
            margin-bottom: 0.4rem;
            color: #ffffff;
            font-weight: 700;
        }
        .hero p {
            font-size: 1.12rem;
            color: var(--muted);
            line-height: 1.7;
        }
        .section-title {
            font-size: 1.55rem;
            color: #ffffff;
            margin: 0.7rem 0 0.9rem 0;
            font-weight: 700;
            letter-spacing: 0.03rem;
        }
        .metric-card {
            padding: 1.1rem 1.15rem;
            min-height: 130px;
        }
        .metric-label {
            color: var(--muted);
            font-size: 0.88rem;
            text-transform: uppercase;
            letter-spacing: 0.08rem;
        }
        .metric-value {
            color: #ffffff;
            font-size: 2rem;
            margin-top: 0.4rem;
            font-weight: 700;
        }
        .metric-note {
            color: var(--muted);
            font-size: 0.9rem;
            margin-top: 0.35rem;
            line-height: 1.5;
        }
        .panel-card {
            padding: 1.25rem;
            margin-bottom: 1rem;
        }
        .work-card {
            padding: 1rem;
            margin-bottom: 1rem;
        }
        .work-card img {
            width: 100%;
            height: 300px;
            object-fit: cover;
            border-radius: 18px;
            border: 1px solid rgba(255,255,255,0.09);
            margin-bottom: 0.75rem;
        }
        .work-title {
            font-size: 1.25rem;
            color: white;
            font-weight: 700;
        }
        .work-meta {
            color: var(--muted);
            font-size: 0.95rem;
            line-height: 1.55;
            margin-top: 0.2rem;
        }
        .chip {
            display:inline-block;
            padding: 0.32rem 0.9rem;
            border-radius: 999px;
            border: 1px solid rgba(255,255,255,0.16);
            background: rgba(255,255,255,0.07);
            color: #f7f7f7;
            margin: 0.15rem 0.2rem 0.15rem 0;
            font-size: 0.86rem;
        }
        .soft-card {
            padding: 1rem 1.1rem;
            margin-bottom: 0.8rem;
        }
        .insight {
            border-left: 3px solid rgba(255,255,255,0.28);
            padding: 0.85rem 1rem;
            border-radius: 14px;
            background: rgba(255,255,255,0.05);
            color: var(--muted);
            line-height: 1.7;
            margin-bottom: 0.8rem;
        }
        .status-pill {
            display:inline-block;
            padding: 0.22rem 0.74rem;
            font-size: 0.82rem;
            border-radius: 999px;
            border: 1px solid rgba(255,255,255,0.14);
            background: rgba(255,255,255,0.08);
            color:#ffffff;
        }
        .divider {
            height: 1px;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.18), transparent);
            margin: 1.1rem 0;
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: 0.55rem;
            padding: 0.3rem;
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.09);
            border-radius: 18px;
        }
        .stTabs [data-baseweb="tab"] {
            border-radius: 14px;
            background: rgba(255,255,255,0.06);
            color: white;
            border: 1px solid rgba(255,255,255,0.10);
            padding: 0.75rem 1.05rem;
            font-weight: 600;
        }
        .stTabs [aria-selected="true"] {
            background: rgba(255,255,255,0.14) !important;
            border-color: rgba(255,255,255,0.18) !important;
        }
        .stTextInput input, .stTextArea textarea, .stSelectbox select, .stNumberInput input {
            background: rgba(255,255,255,0.08) !important;
            border: 1px solid rgba(255,255,255,0.14) !important;
            color: white !important;
            border-radius: 16px !important;
        }
        .stButton button, .stDownloadButton button, .stFormSubmitButton button {
            border-radius: 16px !important;
            border: 1px solid rgba(255,255,255,0.15) !important;
            background: rgba(255,255,255,0.10) !important;
            color: white !important;
            font-weight: 600 !important;
            box-shadow: none !important;
        }
        .stButton button:hover, .stDownloadButton button:hover, .stFormSubmitButton button:hover {
            background: rgba(255,255,255,0.14) !important;
            border-color: rgba(255,255,255,0.22) !important;
        }
        .stDataFrame, div[data-testid="stTable"] {
            border-radius: 18px !important;
            overflow: hidden !important;
        }
        .small-note {
            color: var(--muted);
            font-size: 0.9rem;
            line-height: 1.65;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def topbar() -> None:
    alias = st.session_state.get("alias", "acesso público")
    st.markdown(
        f"""
        <div class="topbar">
            <div>
                <div class="brand">folksonomia</div>
                <div class="brand-sub">interface em liquid glass, semântica assistida e validação curatorial</div>
            </div>
            <div class="brand-sub">usuário: {alias}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def metric_card(label: str, value: Any, note: str = "") -> str:
    return f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{value}</div>
        <div class="metric-note">{note}</div>
    </div>
    """


def hero(title: str, subtitle: str) -> None:
    st.markdown(
        f"""
        <div class="hero">
            <h1>{title}</h1>
            <p>{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section(title: str) -> None:
    st.markdown(f"<div class='section-title'>{title}</div>", unsafe_allow_html=True)


def insight(text: str) -> None:
    st.markdown(f"<div class='insight'>{text}</div>", unsafe_allow_html=True)


# ============================================================
# CAMADA SEMÂNTICA E ML
# ============================================================

def seed_training_rows() -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for label, values in SEED_TRAINING.items():
        for value in values:
            rows.append({"text": clean_token(value), "label": label, "source": "seed"})
    return rows


def validation_training_rows() -> List[Dict[str, str]]:
    validations = read_json(VALIDATIONS_FILE, [])
    rows = []
    for row in validations:
        label = row.get("validated_entity_type") or row.get("entity_type") or "indefinido"
        tag = clean_token(row.get("tag", ""))
        if tag:
            rows.append({"text": tag, "label": label, "source": "validation"})
    return rows


def train_ml_pipeline() -> Dict[str, Any]:
    dataset = seed_training_rows() + validation_training_rows()
    dataset = [row for row in dataset if row["text"] and row["label"] in ENTITY_LABELS]
    result = {
        "enabled": False,
        "message": "scikit-learn indisponível",
        "accuracy": None,
        "labels": ENTITY_LABELS,
        "trained_at": now_str(),
        "samples": len(dataset),
        "vectorizer_vocab_size": 0,
    }
    if not SKLEARN_AVAILABLE:
        write_json(MODEL_STATE_FILE, result)
        return result

    texts = [row["text"] for row in dataset]
    labels = [row["label"] for row in dataset]
    if len(set(labels)) < 2 or len(texts) < 20:
        result["message"] = "amostra insuficiente para treino supervisionado; fallback heurístico em uso"
        write_json(MODEL_STATE_FILE, result)
        return result

    vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1)
    X = vectorizer.fit_transform(texts)
    y = labels

    if len(texts) >= 30:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.25, random_state=42, stratify=y
        )
        model = LogisticRegression(max_iter=250)
        model.fit(X_train, y_train)
        pred = model.predict(X_test)
        acc = float(accuracy_score(y_test, pred))
    else:
        model = LogisticRegression(max_iter=250)
        model.fit(X, y)
        acc = None

    state = {
        "enabled": True,
        "message": "modelo supervisionado treinado com sucesso",
        "accuracy": acc,
        "labels": sorted(set(labels)),
        "trained_at": now_str(),
        "samples": len(texts),
        "vectorizer_vocab_size": len(vectorizer.vocabulary_),
        "training_texts": texts,
        "training_labels": labels,
        "vocabulary": vectorizer.vocabulary_,
        "idf": vectorizer.idf_.tolist(),
        "classes": model.classes_.tolist(),
        "coef": model.coef_.tolist(),
        "intercept": model.intercept_.tolist(),
    }
    write_json(MODEL_STATE_FILE, state)
    return state


def get_model_state() -> Dict[str, Any]:
    state = read_json(MODEL_STATE_FILE, {})
    if not state:
        return train_ml_pipeline()
    return state


def reconstruct_model(state: Dict[str, Any]):
    if not SKLEARN_AVAILABLE or not state.get("enabled"):
        return None, None
    try:
        vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1)
        vectorizer.fit(state["training_texts"])
        model = LogisticRegression(max_iter=250)
        model.classes_ = np.array(state["classes"])
        model.coef_ = np.array(state["coef"])
        model.intercept_ = np.array(state["intercept"])
        model.n_features_in_ = model.coef_.shape[1]
        return vectorizer, model
    except Exception:
        return None, None


def lexical_similarity(a: str, b: str) -> float:
    a_n = clean_token(a)
    b_n = clean_token(b)
    if not a_n or not b_n:
        return 0.0
    if a_n == b_n:
        return 1.0
    a_tokens = set(tokenize(a_n))
    b_tokens = set(tokenize(b_n))
    word_jacc = len(a_tokens & b_tokens) / len(a_tokens | b_tokens) if (a_tokens | b_tokens) else 0.0
    a_grams = {a_n[i:i+3] for i in range(max(1, len(a_n)-2))}
    b_grams = {b_n[i:i+3] for i in range(max(1, len(b_n)-2))}
    gram_jacc = len(a_grams & b_grams) / len(a_grams | b_grams) if (a_grams | b_grams) else 0.0
    contain = 1.0 if a_n in b_n or b_n in a_n else 0.0
    return round(max(0.55 * gram_jacc + 0.35 * word_jacc + 0.10 * contain, contain * 0.75), 4)


HEURISTIC_MAP = {
    "material": {"ouro", "madeira", "bronze", "ferro", "papel", "argila", "gesso", "marmore", "vidro", "ceramica", "oleo", "tela"},
    "tecnica": {"gravura", "escultura", "fotografia", "aquarela", "desenho", "litografia", "xilogravura", "bordado", "colagem", "instalacao"},
    "periodo": {"barroco", "renascimento", "contemporaneo", "moderno", "colonial", "imperial", "medieval", "seculo", "oitocentista", "novecentista"},
    "lugar": {"rio", "brasil", "bahia", "madrid", "paris", "lisboa", "africa", "europa", "amazonia", "sao paulo", "minas"},
    "iconografia": {"cruz", "anjo", "santo", "virgem", "maria", "coroa", "espada", "barco", "flor", "coração", "cavalo"},
    "tema": {"dor", "memoria", "guerra", "familia", "mulher", "religiao", "fe", "violencia", "identidade", "cotidiano", "natureza", "resistencia", "esperanca"},
    "pessoa": {"picasso", "tarsila", "leonardo", "velazquez", "jesus", "napoleao", "portinari", "alice", "anita", "candido", "van", "gogh"},
    "evento_historico": {"independencia", "abolicao", "guerra", "revolucao", "ditadura", "republica"},
    "grupo_social_cultural": {"indigena", "afro", "quilombola", "mulheres", "operarios", "camponeses", "elite", "imigrantes", "povo"},
}


def heuristic_entity_type(text: str) -> Tuple[str, float, str]:
    token_set = set(tokenize(text))
    text_n = clean_token(text)
    best_label = "indefinido"
    best_score = 0.0
    why = "sem padrão definido"
    for label, keywords in HEURISTIC_MAP.items():
        score = 0.0
        for keyword in keywords:
            if keyword in text_n:
                score += 0.3
            if keyword in token_set:
                score += 0.5
        if score > best_score:
            best_score = score
            best_label = label
            why = f"presença de termos associados a {label}"
    confidence = min(0.92, 0.35 + best_score)
    if best_score == 0:
        confidence = 0.22
    return best_label, round(confidence, 3), why


def predict_entity_type(text: str) -> Dict[str, Any]:
    state = get_model_state()
    heur_label, heur_conf, heur_reason = heuristic_entity_type(text)
    if state.get("enabled") and SKLEARN_AVAILABLE:
        vectorizer, model = reconstruct_model(state)
        if vectorizer is not None and model is not None:
            try:
                X = vectorizer.transform([clean_token(text)])
                pred = model.predict(X)[0]
                if hasattr(model, "predict_proba"):
                    proba = model.predict_proba(X)[0]
                    pred_conf = float(np.max(proba))
                else:
                    pred_conf = 0.65
                if pred_conf >= max(0.45, heur_conf - 0.1):
                    return {
                        "entity_type": pred,
                        "confidence": round(pred_conf, 3),
                        "source": "ml_supervisionado",
                        "reason": f"predição supervisionada baseada em dados validados e sementes internas",
                    }
            except Exception:
                pass
    return {
        "entity_type": heur_label,
        "confidence": heur_conf,
        "source": "heuristica_semantica",
        "reason": heur_reason,
    }


def extract_candidates(text: str) -> List[str]:
    tokens = tokenize(text)
    phrases = []
    if len(tokens) >= 2:
        for i in range(len(tokens) - 1):
            phrases.append(f"{tokens[i]} {tokens[i+1]}")
    unique = []
    seen = set()
    for item in tokens + phrases:
        if len(item) > 2 and item not in seen:
            unique.append(item)
            seen.add(item)
    return unique[:8]


def concepts_for_similarity() -> List[Dict[str, Any]]:
    concepts_df = load_concepts()
    concepts = concepts_df.to_dict("records") if not concepts_df.empty else []
    if not concepts:
        # conceitos iniciais derivados das sementes
        seen = set()
        for label, values in SEED_TRAINING.items():
            for value in values[:6]:
                concept = clean_token(value)
                if concept not in seen:
                    concepts.append({"concept_name": concept, "entity_type": label, "status": "seed"})
                    seen.add(concept)
    return concepts


def suggest_related_concepts(text: str, limit: int = 6) -> List[Dict[str, Any]]:
    base = []
    for concept in concepts_for_similarity():
        score = lexical_similarity(text, concept.get("concept_name", ""))
        if score >= 0.18:
            base.append({
                "concept_name": concept.get("concept_name", ""),
                "entity_type": concept.get("entity_type", "indefinido"),
                "similarity": score,
                "status": concept.get("status", "seed"),
            })
    base.sort(key=lambda x: x["similarity"], reverse=True)
    return base[:limit]


def semantic_analysis_for_tag(tag: str, work: Dict[str, Any], justification: str = "") -> Dict[str, Any]:
    full_text = f"{tag} {justification}"
    prediction = predict_entity_type(full_text)
    candidates = extract_candidates(full_text)
    concept_suggestions = suggest_related_concepts(full_text)

    institutional_terms = [clean_token(x) for x in work.get("institutional_terms", [])]
    work_text = " ".join([work.get("title", ""), work.get("artist", ""), work.get("description", "")])
    work_similarity = lexical_similarity(tag, work_text)

    institutional_overlap = [term for term in institutional_terms if lexical_similarity(tag, term) >= 0.34]
    novelty_score = round(max(0.0, 1 - max([lexical_similarity(tag, t) for t in institutional_terms] + [0.0])), 3)

    ambiguity_flag = False
    ambiguity_reason = ""
    if len(concept_suggestions) >= 2 and abs(concept_suggestions[0]["similarity"] - concept_suggestions[1]["similarity"]) < 0.08:
        ambiguity_flag = True
        ambiguity_reason = "múltiplos conceitos próximos com diferença pequena de similaridade"
    if prediction["confidence"] < 0.40:
        ambiguity_flag = True
        ambiguity_reason = ambiguity_reason or "baixa confiança classificatória"

    return {
        "entity_type": prediction["entity_type"],
        "entity_confidence": prediction["confidence"],
        "classification_source": prediction["source"],
        "classification_reason": prediction["reason"],
        "candidate_terms": candidates,
        "concept_suggestions": concept_suggestions,
        "institutional_overlap": institutional_overlap,
        "novelty_score": novelty_score,
        "work_similarity": work_similarity,
        "ambiguity_flag": ambiguity_flag,
        "ambiguity_reason": ambiguity_reason,
    }


# ============================================================
# FUNÇÕES DE ESCRITA
# ============================================================

def create_user_record(answers: Dict[str, Any]) -> str:
    rows = read_json(USERS_FILE, [])
    user_id = base64.b64encode(os.urandom(12)).decode("ascii")
    alias = random_alias()
    rows.append({
        "user_id": user_id,
        "alias": alias,
        "created_at": now_str(),
        **answers,
    })
    write_json(USERS_FILE, rows)
    clear_caches()
    st.session_state["user_id"] = user_id
    st.session_state["alias"] = alias
    st.session_state["access_granted"] = True
    return user_id


def save_tag_submission(user_id: str, work_id: int, tag: str, justification: str) -> None:
    works = load_works()
    work = next((item for item in works if item["id"] == work_id), None)
    if work is None:
        return
    analysis = semantic_analysis_for_tag(tag, work, justification)
    rows = read_json(TAGS_FILE, [])
    rows.append({
        "id": len(rows) + 1,
        "user_id": user_id,
        "work_id": work_id,
        "tag": clean_token(tag),
        "raw_tag": tag.strip(),
        "justification": justification.strip(),
        "created_at": now_str(),
        **analysis,
    })
    write_json(TAGS_FILE, rows)
    clear_caches()


def add_work(title: str, artist: str, year: str, image_url: str, description: str, institutional_terms: str) -> None:
    works = read_json(WORKS_FILE, load_works())
    next_id = max([w["id"] for w in works], default=0) + 1
    works.append({
        "id": next_id,
        "title": title.strip(),
        "artist": artist.strip(),
        "year": year.strip(),
        "image_url": image_url.strip(),
        "description": description.strip(),
        "institutional_terms": [clean_token(x) for x in institutional_terms.split(",") if clean_token(x)],
    })
    write_json(WORKS_FILE, works)
    clear_caches()


def delete_work(work_id: int) -> None:
    works = [w for w in read_json(WORKS_FILE, load_works()) if w["id"] != work_id]
    write_json(WORKS_FILE, works)
    clear_caches()


def save_validation(tag_row: Dict[str, Any], concept_name: str, validated_entity_type: str, note: str) -> None:
    rows = read_json(VALIDATIONS_FILE, [])
    rows.append({
        "tag_id": tag_row.get("id"),
        "tag": tag_row.get("tag"),
        "raw_tag": tag_row.get("raw_tag"),
        "work_id": tag_row.get("work_id"),
        "concept_name": clean_token(concept_name),
        "entity_type": tag_row.get("entity_type", "indefinido"),
        "validated_entity_type": validated_entity_type,
        "note": note.strip(),
        "created_at": now_str(),
    })
    write_json(VALIDATIONS_FILE, rows)

    concepts = read_json(CONCEPTS_FILE, [])
    existing_key = (clean_token(concept_name), validated_entity_type)
    concept_exists = False
    for concept in concepts:
        if clean_token(concept.get("concept_name", "")) == existing_key[0] and concept.get("entity_type") == existing_key[1]:
            concept["updated_at"] = now_str()
            concept["usage_count"] = int(concept.get("usage_count", 0)) + 1
            concept["status"] = "validado"
            concept_exists = True
            break
    if not concept_exists:
        concepts.append({
            "id": len(concepts) + 1,
            "concept_name": clean_token(concept_name),
            "entity_type": validated_entity_type,
            "usage_count": 1,
            "status": "validado",
            "created_at": now_str(),
            "updated_at": now_str(),
        })
    write_json(CONCEPTS_FILE, concepts)
    clear_caches()


# ============================================================
# ANÁLISES E MÉTRICAS
# ============================================================

def df_tags_with_joins() -> pd.DataFrame:
    tags = load_tags().copy()
    if tags.empty:
        return tags
    works = pd.DataFrame(load_works())
    users = load_users()
    if not works.empty:
        tags = tags.merge(works[["id", "title", "artist", "year"]], left_on="work_id", right_on="id", how="left", suffixes=("", "_work"))
    if not users.empty:
        tags = tags.merge(users[["user_id", "alias", "q1", "q2"]], on="user_id", how="left")
    return tags


def semantic_summary(tags_df: pd.DataFrame) -> Dict[str, Any]:
    if tags_df.empty:
        return {
            "total_tags": 0,
            "unique_tags": 0,
            "avg_novelty": 0.0,
            "avg_confidence": 0.0,
            "ambiguous": 0,
        }
    return {
        "total_tags": int(len(tags_df)),
        "unique_tags": int(tags_df["tag"].nunique()),
        "avg_novelty": round(float(tags_df["novelty_score"].fillna(0).mean()), 3),
        "avg_confidence": round(float(tags_df["entity_confidence"].fillna(0).mean()), 3),
        "ambiguous": int(tags_df["ambiguity_flag"].fillna(False).sum()),
    }


def build_similarity_table(tags_df: pd.DataFrame, threshold: float = 0.32) -> pd.DataFrame:
    if tags_df.empty:
        return pd.DataFrame()
    unique_tags = list(tags_df["tag"].dropna().astype(str).unique())
    rows = []
    for idx, tag_a in enumerate(unique_tags):
        for tag_b in unique_tags[idx + 1:]:
            score = lexical_similarity(tag_a, tag_b)
            if score >= threshold:
                rows.append({
                    "tag_a": tag_a,
                    "tag_b": tag_b,
                    "similarity": round(score, 3),
                })
    return pd.DataFrame(rows).sort_values("similarity", ascending=False) if rows else pd.DataFrame()


def generate_automation_recommendations(tags_df: pd.DataFrame) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    if tags_df.empty:
        return pd.DataFrame()

    ambiguous = tags_df[tags_df["ambiguity_flag"] == True]
    for _, row in ambiguous.head(60).iterrows():
        rows.append({
            "priority": "alta",
            "type": "validacao_ambiguidade",
            "work": row.get("title", f"obra {row.get('work_id')}") or f"obra {row.get('work_id')}",
            "tag": row.get("tag", ""),
            "reason": row.get("ambiguity_reason", "baixa confiança classificatória"),
        })

    freq = tags_df["tag"].value_counts()
    for tag, count in freq.items():
        if count >= 3:
            subset = tags_df[tags_df["tag"] == tag]
            entity_modes = subset["entity_type"].value_counts()
            rows.append({
                "priority": "média",
                "type": "conceito_candidato",
                "work": "múltiplas obras",
                "tag": tag,
                "reason": f"tag recorrente com {count} ocorrências; entidade predominante: {entity_modes.index[0]}",
            })

    sim_df = build_similarity_table(tags_df, threshold=0.42)
    if not sim_df.empty:
        for _, row in sim_df.head(40).iterrows():
            rows.append({
                "priority": "média",
                "type": "agrupamento_sugerido",
                "work": "rede geral",
                "tag": f"{row['tag_a']} ↔ {row['tag_b']}",
                "reason": f"similaridade lexical/semântica {row['similarity']:.3f}",
            })

    out = pd.DataFrame(rows)
    if out.empty:
        return out
    priority_order = {"alta": 0, "média": 1, "baixa": 2}
    out["_order"] = out["priority"].map(priority_order)
    out = out.sort_values(["_order", "type", "tag"]).drop(columns="_order")
    return out.reset_index(drop=True)


def deep_questionnaire_analysis(users_df: pd.DataFrame, tags_df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    out: Dict[str, pd.DataFrame] = {}
    if users_df.empty:
        return out
    out["q1"] = users_df["q1"].value_counts().rename_axis("resposta").reset_index(name="frequencia") if "q1" in users_df else pd.DataFrame()
    out["q2"] = users_df["q2"].value_counts().rename_axis("resposta").reset_index(name="frequencia") if "q2" in users_df else pd.DataFrame()

    if not tags_df.empty and "q1" in tags_df.columns:
        cross = tags_df.groupby("q1").agg(
            media_tags=("id", "count"),
            riqueza_lexical=("tag", pd.Series.nunique),
            novidade_media=("novelty_score", "mean"),
            confianca_media=("entity_confidence", "mean"),
        ).reset_index()
        out["cross_q1"] = cross
    if not tags_df.empty and "q2" in tags_df.columns:
        cross2 = tags_df.groupby("q2").agg(
            media_tags=("id", "count"),
            riqueza_lexical=("tag", pd.Series.nunique),
            novidade_media=("novelty_score", "mean"),
            confianca_media=("entity_confidence", "mean"),
        ).reset_index()
        out["cross_q2"] = cross2
    return out


def entity_distribution(tags_df: pd.DataFrame) -> pd.DataFrame:
    if tags_df.empty:
        return pd.DataFrame()
    df = tags_df["entity_type"].fillna("indefinido").value_counts().rename_axis("entity_type").reset_index(name="count")
    df["percentual"] = (df["count"] / df["count"].sum() * 100).round(2)
    return df


def novelty_by_work(tags_df: pd.DataFrame) -> pd.DataFrame:
    if tags_df.empty:
        return pd.DataFrame()
    out = tags_df.groupby(["work_id", "title"]).agg(
        tags=("id", "count"),
        unicas=("tag", pd.Series.nunique),
        novidade_media=("novelty_score", "mean"),
        confianca_media=("entity_confidence", "mean"),
        ambiguas=("ambiguity_flag", "sum"),
    ).reset_index().sort_values("novidade_media", ascending=False)
    out["riqueza_ttr"] = (out["unicas"] / out["tags"]).round(3)
    return out


def most_frequent_terms(tags_df: pd.DataFrame, n: int = 20) -> pd.DataFrame:
    if tags_df.empty:
        return pd.DataFrame()
    freq = tags_df["tag"].value_counts().head(n).rename_axis("tag").reset_index(name="count")
    freq["percentual"] = (freq["count"] / freq["count"].sum() * 100).round(2)
    return freq


# ============================================================
# PDF
# ============================================================

def dataframe_to_table(df: pd.DataFrame, max_rows: int = 28) -> Table:
    limited = df.head(max_rows).copy()
    data = [list(map(str, limited.columns.tolist()))]
    for _, row in limited.iterrows():
        data.append([str(x)[:120] for x in row.tolist()])
    tbl = Table(data, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3a3d44")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#8d9098")),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f7f7f8")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("LEADING", (0, 0), (-1, -1), 10),
    ]))
    return tbl


def build_general_pdf() -> Optional[bytes]:
    if not REPORTLAB_AVAILABLE:
        return None
    tags_df = df_tags_with_joins()
    users_df = load_users()
    summary = semantic_summary(tags_df)
    entity_df = entity_distribution(tags_df)
    novelty_df = novelty_by_work(tags_df)
    frequent_df = most_frequent_terms(tags_df, n=25)
    autom_df = generate_automation_recommendations(tags_df)
    questionnaire = deep_questionnaire_analysis(users_df, tags_df)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=1.5 * cm, rightMargin=1.5 * cm, topMargin=1.5 * cm, bottomMargin=1.5 * cm)
    styles = getSampleStyleSheet()
    title = ParagraphStyle("title", parent=styles["Heading1"], fontName="Times-Bold", fontSize=18, leading=22, textColor=colors.HexColor("#22252b"))
    sub = ParagraphStyle("sub", parent=styles["Heading2"], fontName="Times-Bold", fontSize=13, leading=16, textColor=colors.HexColor("#2c3038"))
    body = ParagraphStyle("body", parent=styles["BodyText"], fontName="Times-Roman", fontSize=10, leading=14)

    story = []
    story.append(Paragraph("folksonomia — relatório administrativo detalhado", title))
    story.append(Spacer(1, 0.35 * cm))
    story.append(Paragraph(f"Gerado em {now_str()}. Este relatório consolida dados de participação, análise semântica, recorrência de tags, novidade lexical, ambiguidades e recomendações automáticas de curadoria.", body))
    story.append(Spacer(1, 0.45 * cm))

    story.append(Paragraph("1. Síntese executiva", sub))
    synthesis = (
        f"Total de tags: {summary['total_tags']}. Tags únicas: {summary['unique_tags']}. "
        f"Novidade média: {summary['avg_novelty']}. Confiança média classificatória: {summary['avg_confidence']}. "
        f"Ocorrências ambíguas detectadas: {summary['ambiguous']}."
    )
    story.append(Paragraph(synthesis, body))
    story.append(Spacer(1, 0.35 * cm))

    if not tags_df.empty:
        story.append(Paragraph("2. Distribuição semântica por tipo de entidade", sub))
        story.append(dataframe_to_table(entity_df))
        story.append(Spacer(1, 0.35 * cm))

        story.append(Paragraph("3. Obras com maior novidade lexical", sub))
        story.append(dataframe_to_table(novelty_df[["title", "tags", "unicas", "novidade_media", "confianca_media", "ambiguas", "riqueza_ttr"]]))
        story.append(Spacer(1, 0.35 * cm))

        story.append(Paragraph("4. Termos mais frequentes", sub))
        story.append(dataframe_to_table(frequent_df))
        story.append(Spacer(1, 0.35 * cm))

    story.append(Paragraph("5. Recomendações de automação e revisão", sub))
    if autom_df.empty:
        story.append(Paragraph("Nenhuma recomendação automática gerada até o momento.", body))
    else:
        story.append(dataframe_to_table(autom_df[["priority", "type", "work", "tag", "reason"]], max_rows=34))
    story.append(Spacer(1, 0.35 * cm))

    story.append(Paragraph("6. Questionário e comportamento de tagging", sub))
    if questionnaire.get("q1") is not None and not questionnaire["q1"].empty:
        story.append(Paragraph("Distribuição da resposta Q1.", body))
        story.append(dataframe_to_table(questionnaire["q1"]))
        story.append(Spacer(1, 0.25 * cm))
    if questionnaire.get("q2") is not None and not questionnaire["q2"].empty:
        story.append(Paragraph("Distribuição da resposta Q2.", body))
        story.append(dataframe_to_table(questionnaire["q2"]))
        story.append(Spacer(1, 0.25 * cm))
    if questionnaire.get("cross_q1") is not None and not questionnaire["cross_q1"].empty:
        story.append(Paragraph("Cruzamento entre familiaridade com museus e produção de tags.", body))
        story.append(dataframe_to_table(questionnaire["cross_q1"].round(3)))
        story.append(Spacer(1, 0.25 * cm))
    if questionnaire.get("cross_q2") is not None and not questionnaire["cross_q2"].empty:
        story.append(Paragraph("Cruzamento entre conhecimento museológico e produção de tags.", body))
        story.append(dataframe_to_table(questionnaire["cross_q2"].round(3)))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()


# ============================================================
# PÁGINA PÚBLICA
# ============================================================

def init_session() -> None:
    if "access_granted" not in st.session_state:
        st.session_state["access_granted"] = False
    if "user_id" not in st.session_state:
        st.session_state["user_id"] = None
    if "alias" not in st.session_state:
        st.session_state["alias"] = "acesso público"
    if "admin_logged" not in st.session_state:
        st.session_state["admin_logged"] = False


def public_questionnaire() -> None:
    hero(
        "questionário de entrada",
        "primeiro o visitante responde ao questionário. depois o acesso é liberado para etiquetar as obras. toda a análise profunda fica reservada à área administrativa.",
    )
    st.markdown("<div class='panel-card'>", unsafe_allow_html=True)
    with st.form("questionario"):
        c1, c2 = st.columns(2)
        with c1:
            q1 = st.selectbox(
                "1. Qual é o seu nível de familiaridade com museus?",
                [
                    "Nunca visito museus",
                    "Visito raramente",
                    "Visito ocasionalmente",
                    "Visito frequentemente",
                ],
            )
            q2 = st.selectbox(
                "2. Você conhece documentação museológica?",
                [
                    "Nunca ouvi falar",
                    "Já ouvi, mas sei pouco",
                    "Tenho noção geral",
                    "Conheço bem o tema",
                ],
            )
        with c2:
            q3 = st.text_area(
                "3. O que você entende por tags aplicadas a acervos?",
                height=170,
                placeholder="Descreva com suas palavras.",
            )
            q4 = st.text_area(
                "4. Ao marcar uma obra, o que você considera mais importante: tema, técnica, material, período, lugar ou percepção pessoal?",
                height=170,
                placeholder="Explique rapidamente seu critério.",
            )
        submitted = st.form_submit_button("liberar acesso para etiquetar obras", use_container_width=True)
        if submitted:
            if not q3.strip() or not q4.strip():
                st.error("Preencha todas as respostas para liberar o acesso.")
            else:
                create_user_record({"q1": q1, "q2": q2, "q3": q3.strip(), "q4": q4.strip()})
                st.success("Acesso liberado. Você já pode etiquetar as obras.")
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def render_work_card(work: Dict[str, Any], user_tags_df: pd.DataFrame) -> None:
    st.markdown(
        f"""
        <div class="work-card">
            <img src="{work['image_url']}" alt="{work['title']}">
            <div class="work-title">{work['title']}</div>
            <div class="work-meta">{work['artist']} · {work['year']}</div>
            <div class="work-meta" style="margin-top:0.35rem;">{work.get('description','')}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    existing = user_tags_df[user_tags_df["work_id"] == work["id"]] if not user_tags_df.empty else pd.DataFrame()
    if not existing.empty:
        st.markdown("<div class='small-note'>Suas tags nesta obra:</div>", unsafe_allow_html=True)
        chips = "".join([f"<span class='chip'>{row['tag']}</span>" for _, row in existing.iterrows()])
        st.markdown(chips, unsafe_allow_html=True)

    with st.form(f"tag_form_{work['id']}"):
        tag = st.text_input("Adicionar tag")
        justification = st.text_area("Justificativa opcional", height=110, placeholder="Explique por que escolheu essa tag.")
        sent = st.form_submit_button("salvar tag", use_container_width=True)
        if sent:
            if not tag.strip():
                st.error("Digite uma tag antes de salvar.")
            else:
                save_tag_submission(st.session_state["user_id"], work["id"], tag, justification)
                analysis = semantic_analysis_for_tag(tag, work, justification)
                st.success("Tag registrada.")
                st.markdown(
                    f"<div class='soft-card'><strong>Leitura semântica imediata:</strong><br>"
                    f"tipo estimado: <span class='status-pill'>{analysis['entity_type']}</span> · "
                    f"confiança: {analysis['entity_confidence']:.3f} · "
                    f"novidade: {analysis['novelty_score']:.3f}</div>",
                    unsafe_allow_html=True,
                )
                if analysis["concept_suggestions"]:
                    st.markdown("<div class='small-note'>conceitos relacionados sugeridos</div>", unsafe_allow_html=True)
                    st.markdown(
                        "".join([
                            f"<span class='chip'>{item['concept_name']} · {item['entity_type']} · {item['similarity']:.2f}</span>"
                            for item in analysis["concept_suggestions"]
                        ]),
                        unsafe_allow_html=True,
                    )
                st.rerun()


def public_area() -> None:
    hero(
        "explorar obras",
        "nesta área pública o visitante apenas vê as obras e envia tags. análises profundas, machine learning, exportações detalhadas em pdf e gestão de obras ficam na área administrativa.",
    )
    works = load_works()
    tags_df = load_tags()
    user_tags = tags_df[tags_df["user_id"] == st.session_state["user_id"]] if not tags_df.empty and st.session_state["user_id"] else pd.DataFrame()

    c1, c2 = st.columns([2, 1])
    with c1:
        search = st.text_input("Filtrar obras por título, artista ou ano")
    with c2:
        sort_mode = st.selectbox("Ordenação", ["Número crescente", "Número decrescente", "Título"])

    filtered = works[:]
    if search.strip():
        key = clean_token(search)
        filtered = [
            item for item in filtered
            if key in clean_token(item.get("title", ""))
            or key in clean_token(item.get("artist", ""))
            or key in clean_token(item.get("year", ""))
        ]
    if sort_mode == "Número decrescente":
        filtered = sorted(filtered, key=lambda x: x["id"], reverse=True)
    elif sort_mode == "Título":
        filtered = sorted(filtered, key=lambda x: x["title"])
    else:
        filtered = sorted(filtered, key=lambda x: x["id"])

    if not filtered:
        st.info("Nenhuma obra encontrada.")
        return

    cols = st.columns(3)
    for idx, work in enumerate(filtered):
        with cols[idx % 3]:
            render_work_card(work, user_tags)


# ============================================================
# ÁREA ADMINISTRATIVA
# ============================================================

def admin_login() -> None:
    section("acesso administrativo")
    st.markdown("<div class='panel-card'>", unsafe_allow_html=True)
    with st.form("admin_login"):
        username = st.text_input("Usuário")
        password = st.text_input("Senha", type="password")
        submitted = st.form_submit_button("entrar na área administrativa", use_container_width=True)
        if submitted:
            if check_admin(username, password):
                st.session_state["admin_logged"] = True
                st.success("Login administrativo realizado.")
                st.rerun()
            else:
                st.error("Credenciais inválidas.")
    st.markdown("</div>", unsafe_allow_html=True)


def admin_overview(tags_df: pd.DataFrame, users_df: pd.DataFrame) -> None:
    summary = semantic_summary(tags_df)
    works = load_works()
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown(metric_card("total de tags", summary["total_tags"], "volume acumulado de marcações"), unsafe_allow_html=True)
    with c2:
        st.markdown(metric_card("tags únicas", summary["unique_tags"], "diversidade lexical observada"), unsafe_allow_html=True)
    with c3:
        st.markdown(metric_card("participantes", len(users_df), "questionários concluídos"), unsafe_allow_html=True)
    with c4:
        st.markdown(metric_card("obras", len(works), "itens disponíveis para etiquetagem"), unsafe_allow_html=True)
    with c5:
        st.markdown(metric_card("ambiguidades", summary["ambiguous"], "casos para revisão humana"), unsafe_allow_html=True)

    insight(
        "A área administrativa concentra as leituras profundas: análise semântica, recorrência de tags, agrupamentos próximos, automação de revisão, exportação detalhada em PDF e o painel de machine learning supervisionado."
    )

    if not tags_df.empty:
        section("visão geral de produção")
        left, right = st.columns(2)
        with left:
            st.bar_chart(tags_df["tag"].value_counts().head(15))
        with right:
            ent = entity_distribution(tags_df)
            if not ent.empty:
                st.bar_chart(ent.set_index("entity_type")["count"])

        novelty = novelty_by_work(tags_df)
        if not novelty.empty:
            st.dataframe(
                novelty[["title", "tags", "unicas", "novidade_media", "confianca_media", "ambiguas", "riqueza_ttr"]].round(3),
                use_container_width=True,
                hide_index=True,
            )


def admin_semantic_analysis(tags_df: pd.DataFrame) -> None:
    section("análise semântica profunda")
    insight(
        "Esta camada segue a lógica pedida no documento: leitura de tags livres e justificativas, classificação por tipo de entidade, desambiguação assistida, aproximação a conceitos, monitoramento de ambiguidade e preservação da linguagem do público sem normalização rígida."
    )

    if tags_df.empty:
        st.info("Ainda não há tags para análise.")
        return

    c1, c2, c3 = st.columns(3)
    with c1:
        min_conf = st.slider("Confiança mínima", 0.0, 1.0, 0.0, 0.05)
    with c2:
        only_amb = st.selectbox("Filtrar ambiguidade", ["Todas", "Somente ambíguas", "Somente claras"])
    with c3:
        entity_filter = st.selectbox("Filtrar entidade", ["Todas"] + ENTITY_LABELS)

    df = tags_df.copy()
    df = df[df["entity_confidence"].fillna(0) >= min_conf]
    if only_amb == "Somente ambíguas":
        df = df[df["ambiguity_flag"] == True]
    elif only_amb == "Somente claras":
        df = df[df["ambiguity_flag"] != True]
    if entity_filter != "Todas":
        df = df[df["entity_type"] == entity_filter]

    st.dataframe(
        df[[
            "id", "tag", "raw_tag", "title", "entity_type", "entity_confidence", "classification_source",
            "novelty_score", "ambiguity_flag", "ambiguity_reason", "created_at"
        ]].sort_values("created_at", ascending=False),
        use_container_width=True,
        hide_index=True,
    )

    section("revisão e validação")
    options_df = df.sort_values("created_at", ascending=False)
    if options_df.empty:
        st.info("Nenhuma ocorrência disponível para revisão com os filtros atuais.")
        return

    selector_labels = [f"#{int(r['id'])} · {r['tag']} · {r.get('title','obra')}" for _, r in options_df.head(100).iterrows()]
    selected_label = st.selectbox("Selecione uma ocorrência para validar", selector_labels)
    selected_id = int(selected_label.split("·")[0].replace("#", "").strip())
    row = options_df[options_df["id"] == selected_id].iloc[0].to_dict()

    st.markdown(
        f"<div class='soft-card'><strong>tag:</strong> {row.get('raw_tag') or row.get('tag')}<br>"
        f"<strong>obra:</strong> {row.get('title','')}<br>"
        f"<strong>tipo previsto:</strong> {row.get('entity_type')}<br>"
        f"<strong>confiança:</strong> {row.get('entity_confidence',0):.3f}<br>"
        f"<strong>motivo:</strong> {row.get('classification_reason','')}</div>",
        unsafe_allow_html=True,
    )

    suggestions = row.get("concept_suggestions", [])
    if suggestions:
        st.markdown("<div class='small-note'>conceitos sugeridos automaticamente</div>", unsafe_allow_html=True)
        st.markdown(
            "".join([
                f"<span class='chip'>{item['concept_name']} · {item['entity_type']} · {item['similarity']:.2f}</span>"
                for item in suggestions
            ]),
            unsafe_allow_html=True,
        )

    with st.form("validation_form"):
        concept_name = st.text_input("Conceito reconciliado", value=row.get("tag", ""))
        validated_entity_type = st.selectbox("Tipo de entidade validado", ENTITY_LABELS, index=max(0, ENTITY_LABELS.index(row.get("entity_type", "indefinido")) if row.get("entity_type", "indefinido") in ENTITY_LABELS else ENTITY_LABELS.index("indefinido")))
        note = st.text_area("Observação curatorial", height=120)
        confirm = st.form_submit_button("salvar validação", use_container_width=True)
        if confirm:
            save_validation(row, concept_name, validated_entity_type, note)
            st.success("Validação registrada. Agora o modelo pode aprender com esse caso.")
            st.rerun()


def admin_tag_analysis(tags_df: pd.DataFrame, users_df: pd.DataFrame) -> None:
    section("análise de tags e comportamento")
    if tags_df.empty:
        st.info("Sem dados de tags para análise.")
        return

    freq = most_frequent_terms(tags_df, n=30)
    left, right = st.columns(2)
    with left:
        st.dataframe(freq, use_container_width=True, hide_index=True)
    with right:
        st.bar_chart(freq.set_index("tag")["count"])

    sim_df = build_similarity_table(tags_df, threshold=0.35)
    section("agrupamentos próximos e desambiguação")
    if sim_df.empty:
        st.info("Nenhum agrupamento acima do limiar atual.")
    else:
        st.dataframe(sim_df.head(60), use_container_width=True, hide_index=True)

    section("questionário e cruzamentos")
    deep = deep_questionnaire_analysis(users_df, tags_df)
    tabs = st.tabs(["Q1", "Q2", "Cruzamento Q1", "Cruzamento Q2"])
    with tabs[0]:
        if deep.get("q1") is not None and not deep["q1"].empty:
            st.dataframe(deep["q1"], use_container_width=True, hide_index=True)
            st.bar_chart(deep["q1"].set_index("resposta")["frequencia"])
        else:
            st.info("Sem respostas registradas.")
    with tabs[1]:
        if deep.get("q2") is not None and not deep["q2"].empty:
            st.dataframe(deep["q2"], use_container_width=True, hide_index=True)
            st.bar_chart(deep["q2"].set_index("resposta")["frequencia"])
        else:
            st.info("Sem respostas registradas.")
    with tabs[2]:
        if deep.get("cross_q1") is not None and not deep["cross_q1"].empty:
            st.dataframe(deep["cross_q1"].round(3), use_container_width=True, hide_index=True)
        else:
            st.info("Sem cruzamentos disponíveis.")
    with tabs[3]:
        if deep.get("cross_q2") is not None and not deep["cross_q2"].empty:
            st.dataframe(deep["cross_q2"].round(3), use_container_width=True, hide_index=True)
        else:
            st.info("Sem cruzamentos disponíveis.")


def admin_automation(tags_df: pd.DataFrame) -> None:
    section("automação e fila de revisão")
    if tags_df.empty:
        st.info("Ainda não há dados para automação.")
        return
    automation_df = generate_automation_recommendations(tags_df)
    if automation_df.empty:
        st.info("Nenhuma recomendação gerada neste momento.")
        return
    st.dataframe(automation_df, use_container_width=True, hide_index=True)
    priority_count = automation_df["priority"].value_counts()
    st.bar_chart(priority_count)
    insight(
        "A automação aqui não substitui a curadoria. Ela organiza a fila de revisão: detecta ambiguidades, recorrências, aproximações entre termos e conceitos candidatos para validação administrativa."
    )


def admin_work_management() -> None:
    section("gestão de obras")
    works = load_works()
    left, right = st.columns([1.2, 1])
    with left:
        st.dataframe(pd.DataFrame(works), use_container_width=True, hide_index=True)
        if works:
            selected = st.selectbox("Selecionar obra para excluir", [f"#{w['id']} · {w['title']}" for w in works])
            if st.button("excluir obra selecionada", use_container_width=True):
                work_id = int(selected.split("·")[0].replace("#", "").strip())
                delete_work(work_id)
                st.success("Obra excluída.")
                st.rerun()
    with right:
        with st.form("add_work_form"):
            title = st.text_input("Título")
            artist = st.text_input("Artista")
            year = st.text_input("Ano")
            image_url = st.text_input("URL da imagem")
            description = st.text_area("Descrição")
            institutional_terms = st.text_area("Termos institucionais, separados por vírgula")
            submitted = st.form_submit_button("incluir obra", use_container_width=True)
            if submitted:
                if not all([title.strip(), artist.strip(), year.strip(), image_url.strip()]):
                    st.error("Preencha pelo menos título, artista, ano e URL da imagem.")
                else:
                    add_work(title, artist, year, image_url, description, institutional_terms)
                    st.success("Obra incluída.")
                    st.rerun()


def admin_exports(tags_df: pd.DataFrame, users_df: pd.DataFrame) -> None:
    section("exportações detalhadas")
    left, right = st.columns(2)
    with left:
        if not tags_df.empty:
            st.download_button(
                "baixar tags em csv",
                tags_df.to_csv(index=False).encode("utf-8"),
                file_name=f"folksonomia_tags_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv",
                use_container_width=True,
            )
        if not users_df.empty:
            st.download_button(
                "baixar questionários em csv",
                users_df.to_csv(index=False).encode("utf-8"),
                file_name=f"folksonomia_questionarios_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv",
                use_container_width=True,
            )
    with right:
        if REPORTLAB_AVAILABLE:
            pdf_bytes = build_general_pdf()
            if pdf_bytes:
                st.download_button(
                    "baixar relatório administrativo em pdf",
                    pdf_bytes,
                    file_name=f"folksonomia_relatorio_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
        else:
            st.warning("reportlab não está instalado; a exportação em PDF está indisponível.")

    insight(
        "O PDF geral inclui síntese executiva, distribuição semântica, obras com maior novidade lexical, frequência de termos, recomendações de automação e cruzamentos do questionário com o comportamento de tagging."
    )


def admin_machine_learning(tags_df: pd.DataFrame) -> None:
    section("machine learning")
    state = get_model_state()
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(metric_card("amostras", state.get("samples", 0), "base usada no treino"), unsafe_allow_html=True)
    with c2:
        accuracy_text = "—" if state.get("accuracy") is None else f"{state.get('accuracy', 0):.3f}"
        st.markdown(metric_card("acurácia", accuracy_text, "medida interna, quando disponível"), unsafe_allow_html=True)
    with c3:
        st.markdown(metric_card("vocabulário tf-idf", state.get("vectorizer_vocab_size", 0), "dimensão lexical do modelo"), unsafe_allow_html=True)
    with c4:
        st.markdown(metric_card("status", "ativo" if state.get("enabled") else "fallback", state.get("message", "")), unsafe_allow_html=True)

    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
    insight(
        "O sistema aprende de duas formas: primeiro por sementes semânticas internas; depois por validações administrativas. Cada validação alimenta uma base supervisionada. Quando há amostras e biblioteca disponíveis, o classificador TF-IDF + regressão logística é reconstituído e passa a prever o tipo de entidade das novas tags."
    )

    if st.button("retreinar modelo agora", use_container_width=True):
        new_state = train_ml_pipeline()
        st.success(new_state.get("message", "treino concluído"))
        st.rerun()

    if not tags_df.empty:
        sample = tags_df[["tag", "entity_type", "entity_confidence", "classification_source"]].sort_values("entity_confidence", ascending=False).head(30)
        st.dataframe(sample, use_container_width=True, hide_index=True)

    validations_df = load_validations()
    if not validations_df.empty:
        st.markdown("<div class='small-note'>Exemplos validados que alimentam o aprendizado supervisionado</div>", unsafe_allow_html=True)
        st.dataframe(
            validations_df[["tag", "concept_name", "validated_entity_type", "created_at"]].sort_values("created_at", ascending=False),
            use_container_width=True,
            hide_index=True,
        )


def admin_area() -> None:
    if not st.session_state.get("admin_logged", False):
        admin_login()
        return

    tags_df = df_tags_with_joins()
    users_df = load_users()

    hero(
        "área administrativa",
        "aqui ficam concentradas a análise semântica profunda, a validação curatorial, a automação de revisão, a gestão das obras, a exportação detalhada em pdf e o painel de machine learning.",
    )

    tabs = st.tabs([
        "visão geral",
        "análise semântica",
        "análise de tags",
        "automação",
        "obras",
        "exportações",
        "machine learning",
    ])
    with tabs[0]:
        admin_overview(tags_df, users_df)
    with tabs[1]:
        admin_semantic_analysis(tags_df)
    with tabs[2]:
        admin_tag_analysis(tags_df, users_df)
    with tabs[3]:
        admin_automation(tags_df)
    with tabs[4]:
        admin_work_management()
    with tabs[5]:
        admin_exports(tags_df, users_df)
    with tabs[6]:
        admin_machine_learning(tags_df)

    if st.button("sair do modo administrativo", use_container_width=True):
        st.session_state["admin_logged"] = False
        st.rerun()


# ============================================================
# APP
# ============================================================

def main() -> None:
    ensure_storage()
    inject_css()
    init_session()
    topbar()

    if not st.session_state["access_granted"]:
        public_questionnaire()
        admin_area()
        return

    public_tabs = st.tabs(["explorar obras", "área administrativa"])
    with public_tabs[0]:
        public_area()
    with public_tabs[1]:
        admin_area()


if __name__ == "__main__":
    main()
