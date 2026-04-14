
from __future__ import annotations

import base64
import csv
import hashlib
import html
import json
import math
import os
import random
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import streamlit as st
import streamlit.components.v1 as components

try:
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except Exception:
    go = None
    PLOTLY_AVAILABLE = False

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    REPORTLAB_AVAILABLE = True
except Exception:
    REPORTLAB_AVAILABLE = False

APP_TITLE = "folksonomia"
APP_DIR = Path("data_folksonomia_final")
WORKS_FILE = APP_DIR / "works.json"
USERS_FILE = APP_DIR / "users.json"
TAGS_FILE = APP_DIR / "tags.json"
VALIDATIONS_FILE = APP_DIR / "validations.json"
CONCEPTS_FILE = APP_DIR / "concepts.json"
ONTOLOGIES_FILE = APP_DIR / "ontologies.json"
ADMIN_FILE = APP_DIR / "admin.json"

ADMIN_LOGIN = "nugep239@"
ADMIN_PASSWORD = "nugep123"

CATEGORY_OPTIONS = [
    "tema", "pessoa", "lugar", "periodo", "material", "tecnica",
    "iconografia", "evento_historico", "grupo_social_cultural"
]

GLOSSARY = {
    "acervo": "Conjunto de obras, objetos e documentos mantidos por uma instituição.",
    "metadados": "Informações que descrevem a obra, como título, autor, data, técnica, material e procedência.",
    "interoperabilidade": "Capacidade de diferentes sistemas trocarem e reaproveitarem dados entre si.",
    "iconografia": "Leitura dos temas, figuras e símbolos que aparecem na imagem.",
    "ontologia": "Estrutura organizada de conceitos e relações usada para conectar e normalizar informações.",
    "desambiguação": "Processo de reconhecer quando nomes ou termos diferentes apontam para a mesma entidade.",
    "tecnica": "Modo de execução da obra, como óleo sobre tela, gravura, escultura ou fotografia.",
    "material": "Matéria física usada na obra, como tela, madeira, bronze ou papel.",
    "proveniência": "Histórico de origem e circulação de uma obra."
}


def ensure_dir():
    APP_DIR.mkdir(parents=True, exist_ok=True)


def now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def uid(prefix: str = "id") -> str:
    return f"{prefix}_{base64.urlsafe_b64encode(os.urandom(8)).decode().strip('=')}"


def normalize_text(text: Any) -> str:
    text = str(text or "").strip().lower()
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("utf-8")
    text = re.sub(r"[^a-z0-9\s\-_/]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def tokenize(text: Any) -> List[str]:
    return [tok for tok in normalize_text(text).split(" ") if tok]


def sequence_ratio(a: str, b: str) -> float:
    a2, b2 = normalize_text(a), normalize_text(b)
    if not a2 or not b2:
        return 0.0
    if a2 == b2:
        return 1.0
    common = len(set(tokenize(a2)) & set(tokenize(b2)))
    base = max(len(set(tokenize(a2)) | set(tokenize(b2))), 1)
    token_score = common / base
    prefix = 1.0 if a2 in b2 or b2 in a2 else 0.0
    return max(token_score, 0.75 if prefix else 0.0)


def load_json(path: Path, default: Any) -> Any:
    ensure_dir()
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return default
    return default


def save_json(path: Path, data: Any):
    ensure_dir()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


class Store:
    def __init__(self):
        ensure_dir()
        self.bootstrap()

    def bootstrap(self):
        if not WORKS_FILE.exists():
            works = [
                {
                    "id": "w1",
                    "title": "Guernica",
                    "artist": "Pablo Picasso",
                    "year": "1937",
                    "image": "https://upload.wikimedia.org/wikipedia/en/7/74/PicassoGuernica.jpg",
                    "museum": "Museo Nacional Centro de Arte Reina Sofía",
                    "collection": "Coleção principal",
                    "place": "Espanha",
                    "period": "modernismo do século XX",
                    "technique": "óleo sobre tela",
                    "material": "tela",
                    "institution_tags": ["guerra", "violência", "civis", "bombardeio", "cavalo", "touro", "espanha"],
                    "description": "Grande composição em preto, branco e cinza com figuras fragmentadas, cavalo central, touro à esquerda, mulher com criança, lâmpada no alto e sensação de ruína e dor.",
                    "open_data": ["Wikidata", "Wikipedia", "Reina Sofía"]
                },
                {
                    "id": "w2",
                    "title": "A Noite Estrelada",
                    "artist": "Vincent van Gogh",
                    "year": "1889",
                    "image": "https://upload.wikimedia.org/wikipedia/commons/e/ea/The_Starry_Night.JPG",
                    "museum": "The Museum of Modern Art",
                    "collection": "European Painting",
                    "place": "França",
                    "period": "pós-impressionismo",
                    "technique": "óleo sobre tela",
                    "material": "tela",
                    "institution_tags": ["céu", "noite", "estrelas", "vila", "paisagem", "movimento"],
                    "description": "Paisagem noturna com céu em movimento, espirais luminosas, lua ou estrela intensa à direita, cipreste escuro em primeiro plano e vila ao fundo.",
                    "open_data": ["Wikidata", "Wikipedia", "MoMA"]
                },
                {
                    "id": "w3",
                    "title": "Mona Lisa",
                    "artist": "Leonardo da Vinci",
                    "year": "1503",
                    "image": "https://upload.wikimedia.org/wikipedia/commons/6/6a/Mona_Lisa.jpg",
                    "museum": "Musée du Louvre",
                    "collection": "Renaissance",
                    "place": "Itália",
                    "period": "renascimento",
                    "technique": "óleo sobre madeira",
                    "material": "madeira",
                    "institution_tags": ["retrato", "mulher", "sorriso", "paisagem", "renascimento"],
                    "description": "Retrato feminino em meia figura, mãos cruzadas, fundo com paisagem distante e expressão facial sutil.",
                    "open_data": ["Wikidata", "Wikipedia", "Louvre"]
                },
            ]
            save_json(WORKS_FILE, works)

        if not USERS_FILE.exists():
            save_json(USERS_FILE, [])
        if not TAGS_FILE.exists():
            save_json(TAGS_FILE, [])
        if not VALIDATIONS_FILE.exists():
            save_json(VALIDATIONS_FILE, [])
        if not CONCEPTS_FILE.exists():
            save_json(CONCEPTS_FILE, [
                {"id": "c1", "label": "guerra", "category": "tema", "aliases": ["conflito", "bombardeio"]},
                {"id": "c2", "label": "Pablo Picasso", "category": "pessoa", "aliases": ["picasso"]},
                {"id": "c3", "label": "Espanha", "category": "lugar", "aliases": ["espanha republicana"]},
                {"id": "c4", "label": "retrato", "category": "iconografia", "aliases": ["figura humana"]},
                {"id": "c5", "label": "pós-impressionismo", "category": "periodo", "aliases": ["pos impressionismo"]},
                {"id": "c6", "label": "óleo sobre tela", "category": "tecnica", "aliases": ["oleo sobre tela"]},
            ])
        if not ONTOLOGIES_FILE.exists():
            save_json(ONTOLOGIES_FILE, [
                {
                    "id": "o1",
                    "label": "Obra",
                    "broader": "",
                    "description": "Classe principal para representar objetos museológicos.",
                    "aliases": ["item", "obra de arte"]
                },
                {
                    "id": "o2",
                    "label": "Pessoa",
                    "broader": "",
                    "description": "Classe para artistas, retratados e agentes históricos.",
                    "aliases": ["autor", "indivíduo"]
                },
            ])
        if not ADMIN_FILE.exists():
            save_json(ADMIN_FILE, {
                "login": ADMIN_LOGIN,
                "password_hash": hashlib.sha256(ADMIN_PASSWORD.encode()).hexdigest()
            })

    def works(self) -> List[Dict[str, Any]]:
        return load_json(WORKS_FILE, [])

    def tags(self) -> List[Dict[str, Any]]:
        return load_json(TAGS_FILE, [])

    def users(self) -> List[Dict[str, Any]]:
        return load_json(USERS_FILE, [])

    def validations(self) -> List[Dict[str, Any]]:
        return load_json(VALIDATIONS_FILE, [])

    def concepts(self) -> List[Dict[str, Any]]:
        return load_json(CONCEPTS_FILE, [])

    def ontologies(self) -> List[Dict[str, Any]]:
        return load_json(ONTOLOGIES_FILE, [])

    def update_admin_credentials(self, login: str, password: str):
        save_json(ADMIN_FILE, {
            "login": login,
            "password_hash": hashlib.sha256(password.encode()).hexdigest()
        })

    def authenticate(self, login: str, password: str) -> bool:
        if login == ADMIN_LOGIN and password == ADMIN_PASSWORD:
            self.update_admin_credentials(ADMIN_LOGIN, ADMIN_PASSWORD)
            return True
        admin = load_json(ADMIN_FILE, {})
        stored_hash = admin.get("password_hash", "")
        return login == admin.get("login", ADMIN_LOGIN) and hashlib.sha256(password.encode()).hexdigest() == stored_hash

    def save_user_intro(self, user_id: str, familiarity: str, documentation: str, understanding: str):
        users = self.users()
        existing = next((u for u in users if u.get("id") == user_id), None)
        payload = {
            "id": user_id,
            "familiarity": familiarity,
            "documentation": documentation,
            "understanding": understanding,
            "created_at": now_iso(),
        }
        if existing:
            existing.update(payload)
        else:
            users.append(payload)
        save_json(USERS_FILE, users)

    def add_tag(self, user_id: str, work_id: str, label: str):
        tags = self.tags()
        tags.append({
            "id": uid("tag"),
            "user_id": user_id,
            "work_id": work_id,
            "label": label.strip(),
            "created_at": now_iso()
        })
        save_json(TAGS_FILE, tags)

    def tags_for_user_work(self, user_id: str, work_id: str) -> List[Dict[str, Any]]:
        return [t for t in self.tags() if t.get("user_id") == user_id and t.get("work_id") == work_id]

    def add_validation(self, payload: Dict[str, Any]):
        rows = self.validations()
        rows.append(payload)
        save_json(VALIDATIONS_FILE, rows)

    def add_ontology(self, label: str, broader: str, description: str, aliases: List[str]):
        rows = self.ontologies()
        rows.append({
            "id": uid("onto"),
            "label": label.strip(),
            "broader": broader.strip(),
            "description": description.strip(),
            "aliases": aliases,
        })
        save_json(ONTOLOGIES_FILE, rows)

    def delete_ontology(self, ontology_id: str):
        rows = [r for r in self.ontologies() if r.get("id") != ontology_id]
        save_json(ONTOLOGIES_FILE, rows)

    def add_work(self, payload: Dict[str, Any]):
        rows = self.works()
        rows.append(payload)
        save_json(WORKS_FILE, rows)

    def delete_work(self, work_id: str):
        save_json(WORKS_FILE, [r for r in self.works() if r.get("id") != work_id])
        save_json(TAGS_FILE, [r for r in self.tags() if r.get("work_id") != work_id])


def init_state():
    if "public_user_id" not in st.session_state:
        st.session_state.public_user_id = uid("user")
    if "intro_done" not in st.session_state:
        st.session_state.intro_done = False
    if "selected_work" not in st.session_state:
        st.session_state.selected_work = None
    if "accessibility_work" not in st.session_state:
        st.session_state.accessibility_work = None
    if "admin_logged_in" not in st.session_state:
        st.session_state.admin_logged_in = False
    if "font_scale" not in st.session_state:
        st.session_state.font_scale = 1.0
    if "high_contrast" not in st.session_state:
        st.session_state.high_contrast = False


def inject_css():
    st.markdown("""
    <style>
    :root{
        --bg:#ededee;
        --card:rgba(255,255,255,.34);
        --card-strong:rgba(255,255,255,.42);
        --line:rgba(0,0,0,.08);
        --text:#1d1e22;
        --text-sub:#57585f;
        --accent:#e65b5b;
        --glass-shadow:0 10px 32px rgba(0,0,0,.08);
    }
    html, body, [class*="css"] {
        font-family:"Times New Roman", Times, serif !important;
        color:var(--text) !important;
    }
    .stApp{
        background:linear-gradient(180deg,#f2f2f3 0%, #ececec 100%);
        color:var(--text);
    }
    .main .block-container{
        max-width:1100px;
        padding-top:1.2rem;
        padding-bottom:4rem;
    }
    h1,h2,h3,h4,h5,h6,p,div,span,label{
        color:var(--text) !important;
    }
    .folk-title{
        font-size:4rem;
        line-height:1;
        margin:0 0 .3rem 0;
        color:#17181b;
        font-weight:700;
        letter-spacing:-0.03em;
    }
    .folk-sub{
        margin:0 0 1rem 0;
        color:#5a5b61 !important;
        font-size:1.15rem;
    }
    .glass-wrap{
        background:var(--card);
        backdrop-filter: blur(18px) saturate(130%);
        -webkit-backdrop-filter: blur(18px) saturate(130%);
        border:1px solid rgba(255,255,255,.55);
        box-shadow:var(--glass-shadow);
        border-radius:28px;
        padding:1.1rem 1.2rem;
    }
    .work-card{
        background:transparent;
        border:none;
        box-shadow:none;
        padding:0;
        margin:0 0 1rem 0;
    }
    .work-img{
        width:100%;
        height:auto;
        border-radius:24px;
        display:block;
        box-shadow:var(--glass-shadow);
    }
    .small-note{
        color:var(--text-sub) !important;
        font-size:1rem;
    }
    .pill-title{
        letter-spacing:.14em;
        text-transform:uppercase;
        font-size:0.9rem;
        color:#5a5b61 !important;
        margin-bottom:.25rem;
    }
    .metric-card{
        background:var(--card);
        backdrop-filter: blur(16px);
        border-radius:24px;
        border:1px solid rgba(255,255,255,.56);
        box-shadow:var(--glass-shadow);
        padding:1rem 1.2rem;
        min-height:125px;
    }
    .metric-value{
        font-size:2.1rem;
        font-weight:700;
        line-height:1.1;
    }
    .metric-label{
        font-size:1rem;
        color:var(--text-sub) !important;
    }
    .helper-box{
        background:var(--card);
        border:1px solid rgba(255,255,255,.56);
        box-shadow:var(--glass-shadow);
        border-radius:24px;
        padding:1rem 1.2rem;
    }
    .tag-chip{
        display:inline-block;
        padding:.34rem .82rem;
        margin:.2rem .3rem .2rem 0;
        border-radius:999px;
        background:rgba(255,255,255,.42);
        border:1px solid rgba(255,255,255,.64);
        color:var(--text);
        font-size:.95rem;
    }
    .stTabs [data-baseweb="tab-list"]{
        gap:0.6rem;
        background:rgba(255,255,255,.22);
        border-radius:30px;
        padding:0.4rem;
        border:1px solid rgba(0,0,0,.06);
        box-shadow:var(--glass-shadow);
        margin-bottom:1rem;
    }
    .stTabs [data-baseweb="tab"]{
        border-radius:26px;
        padding:.72rem 1.2rem;
        background:rgba(255,255,255,.38);
        color:var(--text) !important;
        border:1px solid rgba(255,255,255,.68);
        box-shadow:0 8px 24px rgba(0,0,0,.04);
        font-size:1rem;
    }
    .stTabs [aria-selected="true"]{
        background:rgba(255,255,255,.68) !important;
        color:var(--text) !important;
        border-color:rgba(255,255,255,.9) !important;
        box-shadow:0 10px 26px rgba(0,0,0,.06) !important;
    }
    .stButton>button, .stDownloadButton>button{
        width:100%;
        background:rgba(255,255,255,.18) !important;
        border:1px solid rgba(255,255,255,.62) !important;
        color:#191a1f !important;
        border-radius:24px !important;
        backdrop-filter: blur(18px) saturate(140%) !important;
        -webkit-backdrop-filter: blur(18px) saturate(140%) !important;
        box-shadow:var(--glass-shadow) !important;
        min-height:56px !important;
        font-size:1rem !important;
        font-family:"Times New Roman", Times, serif !important;
    }
    .stButton>button:hover, .stDownloadButton>button:hover{
        background:rgba(255,255,255,.35) !important;
        color:#111215 !important;
        border:1px solid rgba(255,255,255,.82) !important;
    }
    .stTextInput input, .stTextArea textarea, .stSelectbox select{
        background:rgba(255,255,255,.66) !important;
        border:1px solid rgba(0,0,0,.08) !important;
        color:#1b1c20 !important;
        border-radius:22px !important;
        font-size:1rem !important;
        font-family:"Times New Roman", Times, serif !important;
    }
    .stTextInput input::placeholder, .stTextArea textarea::placeholder{
        color:#6f7077 !important;
    }
    .stSlider [data-testid="stTickBar"]{
        color:#d35f5f !important;
    }
    .stAlert{
        border-radius:20px !important;
    }
    .audio-buttons{margin-top:.4rem;}
    #MainMenu, header, footer{visibility:hidden;}
    </style>
    """, unsafe_allow_html=True)


def semantic_description(work: Dict[str, Any], user_tags: List[str]) -> str:
    parts = [
        f"Imagem intitulada {work.get('title','obra sem título')}, de {work.get('artist','autor não informado')}.",
        f"A obra pertence ao museu {work.get('museum','instituição não informada')} e está associada ao período {work.get('period','período não informado')}.",
        f"Técnica registrada: {work.get('technique','não informada')}. Material registrado: {work.get('material','não informado')}.",
        f"Descrição visual base: {work.get('description','descrição não disponível')}.",
    ]
    if user_tags:
        parts.append(f"As tags já registradas por você nesta imagem são: {', '.join(user_tags)}.")
    inst_tags = work.get("institution_tags", [])
    if inst_tags:
        parts.append(f"Termos institucionais ligados a esta imagem: {', '.join(inst_tags[:8])}.")
    return " ".join(parts)


def explain_words(text: str) -> List[Tuple[str, str]]:
    found = []
    normalized = normalize_text(text)
    for term, meaning in GLOSSARY.items():
        if term in normalized:
            found.append((term, meaning))
    return found


def learner_map(store: Store) -> Dict[str, Dict[str, Any]]:
    mapping: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"count": 0, "categories": Counter(), "concepts": Counter()})
    concepts = store.concepts()
    concepts_by_label = {normalize_text(c["label"]): c for c in concepts}
    for c in concepts:
        all_terms = [c["label"]] + c.get("aliases", [])
        for term in all_terms:
            key = normalize_text(term)
            mapping[key]["count"] += 2
            mapping[key]["categories"][c["category"]] += 2
            mapping[key]["concepts"][c["label"]] += 2
    for work in store.works():
        meta_terms = [
            (work.get("artist", ""), "pessoa"),
            (work.get("place", ""), "lugar"),
            (work.get("period", ""), "periodo"),
            (work.get("technique", ""), "tecnica"),
            (work.get("material", ""), "material"),
        ]
        for term, cat in meta_terms:
            key = normalize_text(term)
            if key:
                mapping[key]["count"] += 1
                mapping[key]["categories"][cat] += 1
        for term in work.get("institution_tags", []):
            key = normalize_text(term)
            mapping[key]["count"] += 1
            mapping[key]["categories"]["tema"] += 1
    for tag in store.tags():
        key = normalize_text(tag.get("label", ""))
        if key:
            mapping[key]["count"] += 1
    for row in store.validations():
        key = normalize_text(row.get("label", ""))
        if key:
            if row.get("decision") == "approved":
                mapping[key]["count"] += 3
            mapping[key]["categories"][row.get("category", "")] += 3
            mapping[key]["concepts"][row.get("concept", "")] += 3
    return mapping


def predict_label(store: Store, label: str, work: Dict[str, Any]) -> Tuple[str, str, float]:
    label_n = normalize_text(label)
    mapping = learner_map(store)
    best_cat = "tema"
    best_concept = ""
    conf = 0.35

    # learned exact term
    if label_n in mapping:
        info = mapping[label_n]
        if info["categories"]:
            best_cat = info["categories"].most_common(1)[0][0] or "tema"
            conf = 0.82
        if info["concepts"]:
            best_concept = info["concepts"].most_common(1)[0][0]
    # concepts similarity
    for concept in store.concepts():
        for term in [concept["label"]] + concept.get("aliases", []):
            score = sequence_ratio(label_n, term)
            if score > conf:
                conf = score
                best_cat = concept["category"]
                best_concept = concept["label"]
    # metadata cues
    metadata_fields = {
        "pessoa": [work.get("artist", "")],
        "lugar": [work.get("place", ""), work.get("museum", "")],
        "periodo": [work.get("period", ""), work.get("year", "")],
        "tecnica": [work.get("technique", "")],
        "material": [work.get("material", "")],
    }
    for cat, values in metadata_fields.items():
        for value in values:
            if sequence_ratio(label_n, value) > 0.75:
                return cat, value, 0.9
    return best_cat or "tema", best_concept, round(float(conf), 2)


def connected_search(store: Store, query: str) -> List[Dict[str, Any]]:
    q_tokens = set(tokenize(query))
    results = []
    for work in store.works():
        bag = []
        bag.extend(tokenize(work.get("title", "")))
        bag.extend(tokenize(work.get("artist", "")))
        bag.extend(tokenize(work.get("museum", "")))
        bag.extend(tokenize(work.get("collection", "")))
        bag.extend(tokenize(work.get("place", "")))
        bag.extend(tokenize(work.get("period", "")))
        bag.extend(tokenize(work.get("technique", "")))
        bag.extend(tokenize(work.get("material", "")))
        bag.extend([normalize_text(t) for t in work.get("institution_tags", [])])
        user_tags = [t["label"] for t in store.tags() if t.get("work_id") == work.get("id")]
        bag.extend([normalize_text(t) for t in user_tags])
        validations = [v for v in store.validations() if v.get("work_id") == work.get("id")]
        bag.extend([normalize_text(v.get("concept", "")) for v in validations if v.get("concept")])
        bag_set = set([x for x in bag if x])
        common = q_tokens & bag_set
        score = len(common)
        if score > 0:
            results.append({
                "work": work,
                "score": score,
                "matches": sorted(common)
            })
    return sorted(results, key=lambda x: x["score"], reverse=True)


def temporal_rows(store: Store) -> List[Dict[str, Any]]:
    rows = []
    works_by_id = {w["id"]: w for w in store.works()}
    for tag in store.tags():
        dt = datetime.strptime(tag["created_at"], "%Y-%m-%d %H:%M:%S")
        work = works_by_id.get(tag.get("work_id"), {})
        rows.append({
            "tag": tag.get("label", ""),
            "day": dt.strftime("%Y-%m-%d"),
            "month": dt.strftime("%Y-%m"),
            "year": dt.strftime("%Y"),
            "work_title": work.get("title", ""),
            "museum": work.get("museum", "")
        })
    return rows


def build_network(store: Store) -> Tuple[List[Dict[str, Any]], List[Tuple[str, str, str]]]:
    nodes = {}
    edges = []

    def add_node(node_id: str, label: str, kind: str):
        if node_id not in nodes:
            nodes[node_id] = {"id": node_id, "label": label, "kind": kind}

    for work in store.works():
        wid = work["id"]
        add_node(wid, work["title"], "obra")
        meta_map = {
            f"artist:{work['artist']}": ("artist", work["artist"]),
            f"museum:{work['museum']}": ("museu", work["museum"]),
            f"place:{work['place']}": ("lugar", work["place"]),
            f"period:{work['period']}": ("periodo", work["period"]),
            f"tech:{work['technique']}": ("tecnica", work["technique"]),
            f"mat:{work['material']}": ("material", work["material"]),
            f"collection:{work['collection']}": ("colecao", work["collection"]),
        }
        for nid, (kind, label) in meta_map.items():
            add_node(nid, label, kind)
            edges.append((wid, nid, kind))
        for term in work.get("institution_tags", []):
            nid = f"inst:{normalize_text(term)}"
            add_node(nid, term, "tag_institucional")
            edges.append((wid, nid, "tag_institucional"))

    for tag in store.tags():
        label = tag["label"]
        nid = f"tag:{normalize_text(label)}"
        add_node(nid, label, "tag_publica")
        edges.append((tag["work_id"], nid, "tag_publica"))

    for val in store.validations():
        concept = val.get("concept", "")
        label = val.get("label", "")
        if concept:
            cid = f"concept:{normalize_text(concept)}"
            add_node(cid, concept, "conceito")
            edges.append((val["work_id"], cid, "conceito"))
        if label:
            tid = f"tag:{normalize_text(label)}"
            if tid in nodes and concept:
                edges.append((tid, cid, "reconciliacao"))

    for onto in store.ontologies():
        oid = f"onto:{normalize_text(onto['label'])}"
        add_node(oid, onto["label"], "ontologia")
        if onto.get("broader"):
            bid = f"onto:{normalize_text(onto['broader'])}"
            add_node(bid, onto["broader"], "ontologia")
            edges.append((oid, bid, "hierarquia"))

    return list(nodes.values()), edges


def network_html(store: Store) -> str:
    nodes, edges = build_network(store)
    if not nodes:
        return "<div style='padding:16px;color:#222;'>Nenhuma relação disponível.</div>"
    colors = {
        "obra": "#1d1e22",
        "museu": "#4065d6",
        "artist": "#a64bd4",
        "lugar": "#13a17f",
        "periodo": "#d65b5b",
        "tecnica": "#d6954b",
        "material": "#9a8c5d",
        "colecao": "#3c77a0",
        "tag_institucional": "#555",
        "tag_publica": "#111",
        "conceito": "#842f9c",
        "ontologia": "#0b6f84",
    }
    rnd = random.Random(7)
    payload_nodes = []
    for i, node in enumerate(nodes):
        phi = rnd.random() * 2 * math.pi
        costheta = rnd.uniform(-1, 1)
        theta = math.acos(costheta)
        r = 140 + (i % 7) * 18
        x = r * math.sin(theta) * math.cos(phi)
        y = r * math.sin(theta) * math.sin(phi)
        z = r * math.cos(theta)
        payload_nodes.append({
            "id": node["id"], "label": node["label"], "kind": node["kind"],
            "x": x, "y": y, "z": z, "color": colors.get(node["kind"], "#333")
        })
    payload = json.dumps({"nodes": payload_nodes, "edges": edges}, ensure_ascii=False)
    html_code = f"""
    <div style="width:100%;height:620px;background:rgba(255,255,255,.34);border:1px solid rgba(255,255,255,.55);border-radius:24px;box-shadow:0 10px 32px rgba(0,0,0,.08);overflow:hidden">
      <canvas id="netCanvas" width="900" height="620" style="width:100%;height:100%"></canvas>
    </div>
    <script>
    const payload = {payload};
    const canvas = document.getElementById("netCanvas");
    const ctx = canvas.getContext("2d");
    let rx = 0.6, ry = -0.6, dragging=false, lx=0, ly=0;
    function rotX(p,a) {{
      return {{x:p.x, y:p.y*Math.cos(a)-p.z*Math.sin(a), z:p.y*Math.sin(a)+p.z*Math.cos(a)}};
    }}
    function rotY(p,a) {{
      return {{x:p.x*Math.cos(a)+p.z*Math.sin(a), y:p.y, z:-p.x*Math.sin(a)+p.z*Math.cos(a)}};
    }}
    function project(p) {{
      const scale = 420 / (420 + p.z + 250);
      return {{x: canvas.width/2 + p.x*scale, y: canvas.height/2 + p.y*scale, s: scale}};
    }}
    function draw() {{
      ctx.clearRect(0,0,canvas.width,canvas.height);
      const rotated = {{}};
      payload.nodes.forEach(n => {{
        let p = rotY(rotX(n, rx), ry);
        rotated[n.id] = p;
      }});
      ctx.strokeStyle = "rgba(30,30,35,.20)";
      ctx.lineWidth = 1;
      payload.edges.forEach(e => {{
        const a = project(rotated[e[0]]);
        const b = project(rotated[e[1]]);
        ctx.beginPath();
        ctx.moveTo(a.x,a.y);
        ctx.lineTo(b.x,b.y);
        ctx.stroke();
      }});
      const sorted = payload.nodes.map(n => {{
        const p = rotated[n.id];
        const pr = project(p);
        return {{...n, p, pr}};
      }}).sort((a,b)=>a.p.z-b.p.z);
      sorted.forEach(n => {{
        ctx.beginPath();
        ctx.fillStyle = n.color;
        ctx.globalAlpha = 0.9;
        ctx.arc(n.pr.x, n.pr.y, Math.max(4, 12*n.pr.s), 0, Math.PI*2);
        ctx.fill();
        ctx.globalAlpha = 1;
        if(n.pr.s > 0.55) {{
          ctx.fillStyle = "#1b1c20";
          ctx.font = "14px Times New Roman";
          ctx.fillText(n.label, n.pr.x + 10, n.pr.y - 6);
        }}
      }});
      requestAnimationFrame(draw);
    }}
    canvas.addEventListener("mousedown", e=>{{dragging=true; lx=e.clientX; ly=e.clientY;}});
    canvas.addEventListener("mouseup", ()=>dragging=false);
    canvas.addEventListener("mouseleave", ()=>dragging=false);
    canvas.addEventListener("mousemove", e=>{{
      if(!dragging) return;
      const dx = e.clientX-lx; const dy = e.clientY-ly;
      ry += dx*0.01; rx += dy*0.01;
      lx=e.clientX; ly=e.clientY;
    }});
    draw();
    </script>
    """
    return html_code


def plotly_network(store: Store):
    nodes, edges = build_network(store)
    if not nodes:
        return None
    rng = np.random.default_rng(7)
    positions = {}
    for i, node in enumerate(nodes):
        phi = rng.random() * 2 * math.pi
        costheta = rng.uniform(-1, 1)
        theta = math.acos(costheta)
        r = 8 + (i % 6) * 1.3
        positions[node["id"]] = (
            r * math.sin(theta) * math.cos(phi),
            r * math.sin(theta) * math.sin(phi),
            r * math.cos(theta),
        )
    edge_x, edge_y, edge_z = [], [], []
    for a, b, _ in edges:
        if a in positions and b in positions:
            x0, y0, z0 = positions[a]
            x1, y1, z1 = positions[b]
            edge_x += [x0, x1, None]
            edge_y += [y0, y1, None]
            edge_z += [z0, z1, None]
    fig = go.Figure()
    fig.add_trace(go.Scatter3d(
        x=edge_x, y=edge_y, z=edge_z,
        mode="lines", line=dict(color="rgba(30,30,35,.25)", width=2), hoverinfo="none"
    ))
    kinds = [n["kind"] for n in nodes]
    labels = [n["label"] for n in nodes]
    xs = [positions[n["id"]][0] for n in nodes]
    ys = [positions[n["id"]][1] for n in nodes]
    zs = [positions[n["id"]][2] for n in nodes]
    fig.add_trace(go.Scatter3d(
        x=xs, y=ys, z=zs, mode="markers+text",
        text=labels, textposition="top center",
        marker=dict(size=6, color=np.linspace(0,1,len(nodes)), colorscale="Viridis"),
        hovertext=kinds, hoverinfo="text"
    ))
    fig.update_layout(
        margin=dict(l=0,r=0,t=0,b=0),
        scene=dict(
            xaxis=dict(visible=False), yaxis=dict(visible=False), zaxis=dict(visible=False),
            bgcolor="rgba(0,0,0,0)"
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        height=620
    )
    return fig


def export_pdf_bytes(store: Store) -> bytes:
    if REPORTLAB_AVAILABLE:
        path = APP_DIR / "tmp_report.pdf"
        doc = SimpleDocTemplate(str(path), pagesize=A4)
        styles = getSampleStyleSheet()
        story = []
        story.append(Paragraph("Relatório folksonomia", styles["Title"]))
        story.append(Spacer(1, 12))
        story.append(Paragraph(f"Gerado em {now_iso()}", styles["Normal"]))
        story.append(Spacer(1, 12))
        story.append(Paragraph("Resumo", styles["Heading2"]))
        story.append(Paragraph(f"Obras: {len(store.works())}. Tags: {len(store.tags())}. Validações: {len(store.validations())}. Ontologias: {len(store.ontologies())}.", styles["Normal"]))
        story.append(Spacer(1, 12))
        rows = [["Obra", "Museu", "Total de tags"]]
        counts = Counter([t["work_id"] for t in store.tags()])
        for w in store.works():
            rows.append([w["title"], w["museum"], str(counts.get(w["id"], 0))])
        table = Table(rows, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
            ("GRID", (0,0), (-1,-1), .4, colors.grey),
            ("FONTNAME", (0,0), (-1,-1), "Times-Roman"),
            ("PADDING", (0,0), (-1,-1), 6),
        ]))
        story.append(table)
        doc.build(story)
        data = path.read_bytes()
        try:
            path.unlink()
        except Exception:
            pass
        return data

    # fallback minimal PDF
    lines = [
        "Relatorio folksonomia",
        f"Gerado em {now_iso()}",
        f"Obras: {len(store.works())}",
        f"Tags: {len(store.tags())}",
        f"Validações: {len(store.validations())}",
        f"Ontologias: {len(store.ontologies())}",
        "",
        "Obras:",
    ]
    counts = Counter([t["work_id"] for t in store.tags()])
    for w in store.works():
        lines.append(f"- {w['title']} | {w['museum']} | tags: {counts.get(w['id'],0)}")
    def esc(s: str) -> str:
        return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    content_lines = ["BT", "/F1 12 Tf", "72 800 Td"]
    first = True
    for line in lines:
        if not first:
            content_lines.append("0 -16 Td")
        first = False
        content_lines.append(f"({esc(line)}) Tj")
    content_lines.append("ET")
    stream = "\n".join(content_lines).encode("latin-1", "replace")
    objs = []
    def obj(n, body: bytes):
        return f"{n} 0 obj\n".encode() + body + b"\nendobj\n"
    objs.append(obj(1, b"<< /Type /Catalog /Pages 2 0 R >>"))
    objs.append(obj(2, b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>"))
    objs.append(obj(3, b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"))
    objs.append(obj(4, b"<< /Type /Font /Subtype /Type1 /BaseFont /Times-Roman >>"))
    objs.append(obj(5, b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream"))
    pdf = b"%PDF-1.4\n"
    offsets = [0]
    for o in objs:
        offsets.append(len(pdf))
        pdf += o
    xref_pos = len(pdf)
    pdf += f"xref\n0 {len(objs)+1}\n".encode()
    pdf += b"0000000000 65535 f \n"
    for off in offsets[1:]:
        pdf += f"{off:010d} 00000 n \n".encode()
    pdf += f"trailer\n<< /Size {len(objs)+1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF".encode()
    return pdf


def render_header():
    st.markdown(f"<div class='folk-title'>{APP_TITLE}</div>", unsafe_allow_html=True)
    st.markdown("<div class='folk-sub'>interface translúcida para marcação, validação, busca conectada, ontologias e teia 3d</div>", unsafe_allow_html=True)


def intro_flow(store: Store):
    st.markdown("<div class='glass-wrap'><h2 style='margin-top:0'>acesso inicial</h2><div class='small-note'>primeiro responda ao questionário. só depois a interface de marcação das obras será liberada.</div></div>", unsafe_allow_html=True)
    with st.form("intro_form_single"):
        familiarity = st.selectbox("1. qual é a sua frequência de visita a museus?", ["nunca", "raramente", "ocasionalmente", "frequentemente"], key="intro_familiarity")
        documentation = st.selectbox("2. você já ouviu falar sobre documentação museológica?", ["nenhum", "já ouvi", "tenho noção básica", "conheço bem"], key="intro_documentation")
        understanding = st.text_area("3. o que você entende por tags aplicadas a acervos?\ndescreva com suas palavras.", key="intro_understanding", placeholder="escreva com suas palavras", height=170)
        submitted = st.form_submit_button("liberar acesso às obras")
    if submitted:
        if not understanding.strip():
            st.error("preencha a terceira resposta para liberar o acesso.")
            return
        store.save_user_intro(st.session_state.public_user_id, familiarity, documentation, understanding)
        st.session_state.intro_done = True
        st.rerun()


def render_accessibility(work: Dict[str, Any], tags_user: List[str]):
    st.markdown("<div class='glass-wrap'><h3 style='margin-top:0'>acessibilidade</h3></div>", unsafe_allow_html=True)
    st.session_state.font_scale = st.slider("tamanho da fonte", 0.9, 1.6, float(st.session_state.font_scale), 0.05, key=f"font_{work['id']}")
    st.session_state.high_contrast = st.toggle("contraste reforçado", value=bool(st.session_state.high_contrast), key=f"contrast_{work['id']}")
    desc = semantic_description(work, tags_user)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("ouvir descrição", key=f"speak_{work['id']}"):
            components.html(f"""
            <script>
            const txt = {json.dumps(desc)};
            window.speechSynthesis.cancel();
            const u = new SpeechSynthesisUtterance(txt);
            u.lang = 'pt-BR';
            u.rate = 1.0;
            speechSynthesis.speak(u);
            </script>
            """, height=0)
    with c2:
        if st.button("parar leitura", key=f"stop_{work['id']}"):
            components.html("<script>window.speechSynthesis.cancel();</script>", height=0)
    st.markdown("<div class='helper-box'><strong>descrição detalhada</strong><br>" + html.escape(desc) + "</div>", unsafe_allow_html=True)
    explanations = explain_words(desc)
    if explanations:
        st.markdown("<div class='helper-box' style='margin-top:0.7rem'><strong>palavras complexas explicadas</strong><br>" +
                    "<br>".join([f"<strong>{html.escape(k)}</strong>: {html.escape(v)}" for k, v in explanations]) +
                    "</div>", unsafe_allow_html=True)


def render_public(store: Store):
    works = store.works()
    for work in works:
        my_tags = [t["label"] for t in store.tags_for_user_work(st.session_state.public_user_id, work["id"])]
        st.markdown("<div class='work-card'>", unsafe_allow_html=True)
        st.image(work["image"], use_container_width=True)
        c1, c2 = st.columns([1, 1])
        with c1:
            if st.button("Marcar", key=f"mark_{work['id']}"):
                st.session_state.selected_work = work["id"]
                st.session_state.accessibility_work = None if st.session_state.accessibility_work == work["id"] else st.session_state.accessibility_work
        with c2:
            if st.button("Acessibilidade", key=f"acc_{work['id']}"):
                st.session_state.accessibility_work = None if st.session_state.accessibility_work == work["id"] else work["id"]
                st.session_state.selected_work = None if st.session_state.selected_work == work["id"] else st.session_state.selected_work

        if st.session_state.selected_work == work["id"]:
            with st.form(f"tag_form_{work['id']}"):
                tag_value = st.text_input("sua tag", key=f"tag_input_{work['id']}", placeholder="escreva a tag")
                c3, c4 = st.columns(2)
                with c3:
                    save_pressed = st.form_submit_button("registrar tag")
                with c4:
                    close_pressed = st.form_submit_button("fechar")
                if save_pressed:
                    if tag_value.strip():
                        store.add_tag(st.session_state.public_user_id, work["id"], tag_value)
                        st.success("tag registrada.")
                        st.rerun()
                    else:
                        st.error("escreva uma tag antes de registrar.")
                if close_pressed:
                    st.session_state.selected_work = None
                    st.rerun()
            st.markdown("<div class='small-note' style='margin-top:0.6rem'>suas tags nesta imagem</div>", unsafe_allow_html=True)
            if my_tags:
                st.markdown("".join([f"<span class='tag-chip'>{html.escape(t)}</span>" for t in my_tags]), unsafe_allow_html=True)
            else:
                st.markdown("<div class='helper-box'>Nenhuma tag registrada por você nesta imagem ainda.</div>", unsafe_allow_html=True)

        if st.session_state.accessibility_work == work["id"]:
            render_accessibility(work, my_tags)
        st.markdown("</div>", unsafe_allow_html=True)


def render_admin_login(store: Store):
    st.markdown("<div class='glass-wrap'><h2 style='margin-top:0'>login administrativo</h2></div>", unsafe_allow_html=True)
    with st.form("admin_login_form"):
        login = st.text_input("login", value="nugep239@", key="admin_login_input")
        password = st.text_input("senha", type="password", value="nugep123", key="admin_password_input")
        submitted = st.form_submit_button("entrar")
    if submitted:
        if store.authenticate(login, password):
            st.session_state.admin_logged_in = True
            st.success("acesso liberado.")
            st.rerun()
        else:
            st.error("credenciais inválidas.")


def render_admin_panel(store: Store):
    tags = store.tags()
    validations = store.validations()
    ontologies = store.ontologies()
    works = store.works()
    users = store.users()
    c1, c2, c3, c4, c5 = st.columns(5)
    metrics = [
        ("obras", len(works)),
        ("tags coletadas", len(tags)),
        ("participantes", len(users)),
        ("fila curatorial", len([v for v in validations if v.get("decision") != "approved"])),
        ("ontologias", len(ontologies)),
    ]
    for col, (label, value) in zip([c1,c2,c3,c4,c5], metrics):
        with col:
            st.markdown(f"<div class='metric-card'><div class='pill-title'>{html.escape(label)}</div><div class='metric-value'>{value}</div><div class='metric-label'>painel principal</div></div>", unsafe_allow_html=True)
    st.markdown("<div style='height:0.8rem'></div>", unsafe_allow_html=True)
    query = st.text_input("busca conectada", placeholder="busque por artista, técnica, material, lugar, tema, tag pública ou conceito", key="connected_query")
    if query.strip():
        res = connected_search(store, query)
        if res:
            for item in res[:8]:
                work = item["work"]
                st.markdown(f"<div class='helper-box'><strong>{html.escape(work['title'])}</strong> · {html.escape(work['artist'])}<br>correspondências: {html.escape(', '.join(item['matches']))}</div>", unsafe_allow_html=True)
        else:
            st.info("nenhuma obra apareceu nessa busca.")


def examples_for_tag(store: Store, label: str) -> List[str]:
    label_n = normalize_text(label)
    ex = []
    for tag in store.tags():
        other = tag.get("label", "")
        if other and other != label and sequence_ratio(label_n, other) >= 0.45:
            work = next((w for w in store.works() if w["id"] == tag["work_id"]), {})
            ex.append(f"{other} · {work.get('title','obra')}")
    return ex[:3]


def render_validation(store: Store):
    works_by_id = {w["id"]: w for w in store.works()}
    tags = store.tags()
    if not tags:
        st.info("ainda não há tags para validar.")
        return
    for row in tags[-20:][::-1]:
        work = works_by_id.get(row["work_id"], {})
        category, concept, confidence = predict_label(store, row["label"], work)
        similar = examples_for_tag(store, row["label"])
        box = f"<div class='helper-box'><strong>{html.escape(row['label'])}</strong> · {html.escape(work.get('title','obra'))}<br>previsão {html.escape(category)} · confiança {confidence}<br>"
        if concept:
            box += f"conceito sugerido {html.escape(concept)}<br>"
        box += f"museu {html.escape(work.get('museum',''))} · período {html.escape(work.get('period',''))} · técnica {html.escape(work.get('technique',''))}</div>"
        st.markdown(box, unsafe_allow_html=True)
        if similar:
            st.markdown("<div class='small-note'>3 exemplos próximos</div>", unsafe_allow_html=True)
            st.markdown("".join([f"<span class='tag-chip'>{html.escape(s)}</span>" for s in similar]), unsafe_allow_html=True)
        with st.form(f"val_form_{row['id']}"):
            c1, c2, c3 = st.columns(3)
            with c1:
                category_v = st.selectbox("categoria validada", CATEGORY_OPTIONS, index=max(CATEGORY_OPTIONS.index(category), 0) if category in CATEGORY_OPTIONS else 0, key=f"cat_{row['id']}")
            with c2:
                concept_options = [""] + [c["label"] for c in store.concepts()]
                concept_v = st.selectbox("conceito reconciliado", concept_options, index=concept_options.index(concept) if concept in concept_options else 0, key=f"concept_{row['id']}")
            with c3:
                decision_v = st.selectbox("decisão", ["approved", "review", "rejected"], key=f"decision_{row['id']}")
            note = st.text_area("notas curatoriais", key=f"note_{row['id']}", height=90)
            submitted = st.form_submit_button("registrar validação")
        if submitted:
            store.add_validation({
                "id": uid("val"),
                "tag_id": row["id"],
                "work_id": row["work_id"],
                "label": row["label"],
                "category": category_v,
                "concept": concept_v,
                "decision": decision_v,
                "note": note,
                "created_at": now_iso()
            })
            st.success("validação registrada.")
            st.rerun()
        st.markdown("<div style='height:.8rem'></div>", unsafe_allow_html=True)


def render_ontologies(store: Store):
    st.markdown("<div class='glass-wrap'><h3 style='margin-top:0'>criação e administração de ontologias</h3><div class='small-note'>cadastre classes, conceitos amplos, relações hierárquicas e sinônimos de apoio.</div></div>", unsafe_allow_html=True)
    with st.form("ontology_add_form"):
        label = st.text_input("nome da ontologia")
        broader = st.text_input("conceito mais amplo")
        description = st.text_area("descrição")
        aliases = st.text_input("sinônimos, separados por vírgula")
        submitted = st.form_submit_button("criar ontologia")
    if submitted and label.strip():
        store.add_ontology(label, broader, description, [a.strip() for a in aliases.split(",") if a.strip()])
        st.success("ontologia criada.")
        st.rerun()
    for onto in store.ontologies():
        st.markdown(f"<div class='helper-box'><strong>{html.escape(onto['label'])}</strong><br>mais amplo: {html.escape(onto.get('broader','') or 'nenhum')}<br>{html.escape(onto.get('description',''))}</div>", unsafe_allow_html=True)
        if onto.get("aliases"):
            st.markdown("".join([f"<span class='tag-chip'>{html.escape(a)}</span>" for a in onto["aliases"]]), unsafe_allow_html=True)
        if st.button("excluir ontologia", key=f"del_onto_{onto['id']}"):
            store.delete_ontology(onto["id"])
            st.rerun()


def render_temporal(store: Store):
    rows = temporal_rows(store)
    if not rows:
        st.info("a análise temporal aparecerá quando houver tags registradas.")
        return
    st.markdown("<div class='glass-wrap'><h3 style='margin-top:0'>análise temporal</h3><div class='small-note'>leitura de tags criadas por dia, mês e ano, com detalhamento das obras e termos registrados.</div></div>", unsafe_allow_html=True)
    daily = defaultdict(list)
    monthly = defaultdict(list)
    yearly = defaultdict(list)
    for r in rows:
        daily[r["day"]].append(r)
        monthly[r["month"]].append(r)
        yearly[r["year"]].append(r)

    def series_chart(grouped: Dict[str, List[Dict[str, Any]]], title: str, key: str):
        labels = sorted(grouped.keys())
        values = [len(grouped[k]) for k in labels]
        st.markdown(f"<div class='helper-box'><strong>{title}</strong></div>", unsafe_allow_html=True)
        if PLOTLY_AVAILABLE:
            fig = go.Figure(go.Bar(x=labels, y=values, marker_color="#6a8bd6"))
            fig.update_layout(margin=dict(l=0,r=0,t=10,b=0), height=280, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(255,255,255,.0)")
            st.plotly_chart(fig, use_container_width=True, key=key)
        else:
            st.bar_chart({"quantidade": values}, x_label=labels)
        for label in labels[-6:][::-1]:
            tags = [r["tag"] for r in grouped[label]]
            works = sorted(set([r["work_title"] for r in grouped[label] if r["work_title"]]))
            st.markdown(f"<div class='helper-box'><strong>{html.escape(label)}</strong><br>tags: {html.escape(', '.join(tags[:12]))}<br>obras: {html.escape(', '.join(works[:6]))}</div>", unsafe_allow_html=True)

    series_chart(daily, "por dia", "temporal_day")
    series_chart(monthly, "por mês", "temporal_month")
    series_chart(yearly, "por ano", "temporal_year")


def render_teia_3d(store: Store):
    st.markdown("<div class='glass-wrap'><h3 style='margin-top:0'>teia 3d de conectividade</h3><div class='small-note'>rede de compartilhamento e interoperabilidade entre metadados institucionais, tags públicas, conceitos validados e ontologias.</div></div>", unsafe_allow_html=True)
    if PLOTLY_AVAILABLE:
        fig = plotly_network(store)
        if fig is not None:
            st.plotly_chart(fig, use_container_width=True, key="network3d_plotly")
            return
    components.html(network_html(store), height=640, scrolling=False)


def render_works_admin(store: Store):
    st.markdown("<div class='glass-wrap'><h3 style='margin-top:0'>obras na área administrativa</h3><div class='small-note'>cadastre novas obras e exclua obras existentes.</div></div>", unsafe_allow_html=True)
    with st.form("add_work_form"):
        title = st.text_input("título")
        artist = st.text_input("artista")
        year = st.text_input("ano")
        image = st.text_input("url da imagem")
        museum = st.text_input("museu")
        collection = st.text_input("coleção")
        place = st.text_input("lugar")
        period = st.text_input("período")
        technique = st.text_input("técnica")
        material = st.text_input("material")
        institution_tags = st.text_input("tags institucionais separadas por vírgula")
        description = st.text_area("descrição")
        open_data = st.text_input("fontes externas separadas por vírgula")
        submitted = st.form_submit_button("adicionar obra")
    if submitted:
        if title.strip() and image.strip():
            store.add_work({
                "id": uid("w"),
                "title": title.strip(),
                "artist": artist.strip(),
                "year": year.strip(),
                "image": image.strip(),
                "museum": museum.strip(),
                "collection": collection.strip(),
                "place": place.strip(),
                "period": period.strip(),
                "technique": technique.strip(),
                "material": material.strip(),
                "institution_tags": [x.strip() for x in institution_tags.split(",") if x.strip()],
                "description": description.strip(),
                "open_data": [x.strip() for x in open_data.split(",") if x.strip()],
            })
            st.success("obra adicionada.")
            st.rerun()
        else:
            st.error("preencha ao menos título e url da imagem.")
    for work in store.works():
        st.markdown(f"<div class='helper-box'><strong>{html.escape(work['title'])}</strong> · {html.escape(work['artist'])}<br>{html.escape(work['museum'])}</div>", unsafe_allow_html=True)
        if st.button("excluir obra", key=f"del_work_{work['id']}"):
            store.delete_work(work["id"])
            st.rerun()


def render_export(store: Store):
    pdf_data = export_pdf_bytes(store)
    st.download_button("exportar em pdf", pdf_data, file_name="relatorio_folksonomia.pdf", mime="application/pdf")
    def to_csv_bytes(rows: List[Dict[str, Any]]) -> bytes:
        if not rows:
            return b""
        headers = sorted({k for r in rows for k in r.keys()})
        out = []
        out.append(",".join(headers))
        for r in rows:
            vals = []
            for h in headers:
                v = r.get(h, "")
                if isinstance(v, list):
                    v = "; ".join(map(str, v))
                vals.append('"' + str(v).replace('"', '""') + '"')
            out.append(",".join(vals))
        return "\n".join(out).encode("utf-8")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.download_button("csv de tags", to_csv_bytes(store.tags()), file_name="tags.csv", mime="text/csv")
    with c2:
        st.download_button("csv de obras", to_csv_bytes(store.works()), file_name="obras.csv", mime="text/csv")
    with c3:
        st.download_button("csv de ontologias", to_csv_bytes(store.ontologies()), file_name="ontologias.csv", mime="text/csv")


def admin_area(store: Store):
    if not st.session_state.admin_logged_in:
        render_admin_login(store)
        return
    tabs = st.tabs(["painel", "validação", "ontologias", "análise temporal", "teia 3d", "obras", "exportar"])
    with tabs[0]:
        render_admin_panel(store)
    with tabs[1]:
        render_validation(store)
    with tabs[2]:
        render_ontologies(store)
    with tabs[3]:
        render_temporal(store)
    with tabs[4]:
        render_teia_3d(store)
    with tabs[5]:
        render_works_admin(store)
    with tabs[6]:
        render_export(store)
    if st.button("sair da área administrativa", key="logout_admin"):
        st.session_state.admin_logged_in = False
        st.rerun()


def main():
    st.set_page_config(page_title=APP_TITLE, layout="wide", initial_sidebar_state="collapsed")
    init_state()
    inject_css()
    store = Store()
    render_header()
    if not st.session_state.intro_done:
        intro_flow(store)
        return
    top_tabs = st.tabs(["explorar obras", "área administrativa"])
    with top_tabs[0]:
        render_public(store)
    with top_tabs[1]:
        admin_area(store)


if __name__ == "__main__":
    main()
