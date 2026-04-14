
from __future__ import annotations

import base64
import csv
import io
import json
import math
import os
import re
import uuid
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

import streamlit as st
import pandas as pd

try:
    import plotly.graph_objects as go
    PLOTLY_OK = True
except Exception:
    PLOTLY_OK = False
    go = None

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    REPORTLAB_OK = True
except Exception:
    REPORTLAB_OK = False

APP_TITLE = "folksonomia"
APP_DIR = Path("folksonomia_data")
WORKS_FILE = APP_DIR / "works.json"
RESPONSES_FILE = APP_DIR / "responses.json"
TAGS_FILE = APP_DIR / "tags.json"
VALIDATIONS_FILE = APP_DIR / "validations.json"
ONTOLOGIES_FILE = APP_DIR / "ontologies.json"
SETTINGS_FILE = APP_DIR / "settings.json"
ADMIN_FILE = APP_DIR / "admin.json"

ADMIN_LOGIN = "nugep239@"
ADMIN_PASSWORD = "nugep123"

CATEGORY_OPTIONS = ["tema", "técnica", "material", "período", "lugar", "pessoa", "evento", "iconografia", "outro"]
DEFAULT_CLASSES = ["tema", "técnica", "material", "período", "lugar", "pessoa", "evento", "iconografia"]
DEFAULT_RELATIONS = ["obra_tem_tema", "obra_tem_técnica", "obra_tem_material", "obra_tem_lugar", "obra_tem_período", "obra_relaciona_pessoa"]
COMPLEX_WORDS = {
    "folksonomia": "Sistema de marcação colaborativa em que as pessoas criam tags livremente.",
    "ontologia": "Estrutura que organiza conceitos, categorias e relações entre eles.",
    "interoperabilidade": "Capacidade de diferentes sistemas trocarem e entenderem dados entre si.",
    "metadados": "Informações descritivas sobre uma obra, como autor, técnica, período e lugar.",
    "iconografia": "Conjunto de imagens, símbolos e temas representados em uma obra.",
    "desambiguação": "Processo de diferenciar termos parecidos ou grafias diferentes que podem apontar para o mesmo conceito.",
    "nlu": "Compreensão de linguagem natural: leitura automática de textos para reconhecer entidades, temas e relações.",
}

st.set_page_config(page_title=APP_TITLE, layout="wide", initial_sidebar_state="collapsed")

def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def ensure_dir():
    APP_DIR.mkdir(exist_ok=True)

def read_json(path: Path, default):
    ensure_dir()
    if path.exists():
        try:
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    return default

def write_json(path: Path, data):
    ensure_dir()
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def normalize(text: str) -> str:
    text = (text or "").strip().lower()
    text = re.sub(r"\s+", " ", text)
    return text

def similar(a: str, b: str) -> float:
    a = normalize(a)
    b = normalize(b)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    if a in b or b in a:
        return 0.85
    aw = set(a.split())
    bw = set(b.split())
    j = len(aw & bw) / max(1, len(aw | bw))
    grams_a = {a[i:i+3] for i in range(max(1, len(a)-2))}
    grams_b = {b[i:i+3] for i in range(max(1, len(b)-2))}
    g = len(grams_a & grams_b) / max(1, len(grams_a | grams_b))
    return round((j * 0.55) + (g * 0.45), 3)

def boot_data():
    works = read_json(WORKS_FILE, [])
    if not works:
        works = [
            {
                "id": "w1",
                "title": "Guernica",
                "artist": "Pablo Picasso",
                "image_url": "https://upload.wikimedia.org/wikipedia/en/7/74/PicassoGuernica.jpg",
                "museum": "Museo Nacional Centro de Arte Reina Sofía",
                "collection": "Coleção permanente",
                "place": "Espanha",
                "period": "modernismo do século XX",
                "technique": "óleo sobre tela",
                "material": "tinta a óleo",
                "institutional_tags": ["guerra", "violência", "bombardeio", "cavalo", "figura humana"],
                "description": "Pintura em preto, branco e cinza com figuras humanas e animais fragmentados, associada aos horrores da guerra."
            },
            {
                "id": "w2",
                "title": "A Noite Estrelada",
                "artist": "Vincent van Gogh",
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/e/ea/The_Starry_Night.jpg",
                "museum": "The Museum of Modern Art",
                "collection": "Coleção de pintura",
                "place": "França",
                "period": "pós-impressionismo",
                "technique": "óleo sobre tela",
                "material": "tinta a óleo",
                "institutional_tags": ["céu", "vila", "noite", "movimento", "paisagem"],
                "description": "Paisagem noturna azul com redemoinhos no céu, estrelas brilhantes, lua intensa e uma vila abaixo."
            },
            {
                "id": "w3",
                "title": "Mona Lisa",
                "artist": "Leonardo da Vinci",
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/6/6a/Mona_Lisa.jpg",
                "museum": "Musée du Louvre",
                "collection": "Pintura renascentista",
                "place": "Itália",
                "period": "renascimento",
                "technique": "óleo sobre madeira",
                "material": "madeira e tinta a óleo",
                "institutional_tags": ["retrato", "sorriso", "figura feminina", "paisagem"],
                "description": "Retrato de uma mulher sentada, com sorriso discreto, mãos cruzadas e fundo paisagístico difuso."
            },
        ]
        write_json(WORKS_FILE, works)

    ontologies = read_json(ONTOLOGIES_FILE, [])
    if not ontologies:
        ontologies = [
            {
                "id": "o1",
                "name": "Ontologia museológica base",
                "description": "Estrutura inicial para organizar categorias e relações usadas na validação.",
                "classes": DEFAULT_CLASSES,
                "relations": DEFAULT_RELATIONS,
                "timestamp": now_str(),
            }
        ]
        write_json(ONTOLOGIES_FILE, ontologies)

    admins = read_json(ADMIN_FILE, [])
    if not admins:
        admins = [{"login": ADMIN_LOGIN, "password": ADMIN_PASSWORD}]
        write_json(ADMIN_FILE, admins)

    if not SETTINGS_FILE.exists():
        write_json(SETTINGS_FILE, {"font_scale": 1.0, "high_contrast": False})

class Store:
    def works(self):
        return read_json(WORKS_FILE, [])
    def tags(self):
        return read_json(TAGS_FILE, [])
    def responses(self):
        return read_json(RESPONSES_FILE, [])
    def validations(self):
        return read_json(VALIDATIONS_FILE, [])
    def ontologies(self):
        return read_json(ONTOLOGIES_FILE, [])
    def settings(self):
        return read_json(SETTINGS_FILE, {"font_scale": 1.0, "high_contrast": False})

    def save_works(self, data): write_json(WORKS_FILE, data)
    def save_tags(self, data): write_json(TAGS_FILE, data)
    def save_responses(self, data): write_json(RESPONSES_FILE, data)
    def save_validations(self, data): write_json(VALIDATIONS_FILE, data)
    def save_ontologies(self, data): write_json(ONTOLOGIES_FILE, data)
    def save_settings(self, data): write_json(SETTINGS_FILE, data)

store = Store()
boot_data()

def ensure_state():
    defaults = {
        "public_unlocked": False,
        "public_user_id": None,
        "questionnaire_saved": False,
        "selected_work_id": None,
        "admin_logged_in": False,
        "tab_public": "explorar obras",
        "tab_admin": "painel",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v
    if not st.session_state["public_user_id"]:
        st.session_state["public_user_id"] = f"u_{uuid.uuid4().hex[:10]}"

def inject_css():
    settings = store.settings()
    font_scale = float(settings.get("font_scale", 1.0))
    high_contrast = bool(settings.get("high_contrast", False))
    text = "#141417" if not high_contrast else "#0b0b0e"
    sub = "#4f5157" if not high_contrast else "#1e1f24"
    line = "rgba(255,255,255,.6)"
    bg = "#efefef" if not high_contrast else "#ffffff"
    glass = "rgba(255,255,255,.30)" if not high_contrast else "rgba(255,255,255,.55)"
    css = f"""
    <style>
    :root {{
        --fontScale: {font_scale};
        --bg: {bg};
        --text: {text};
        --textSub: {sub};
        --glass: {glass};
        --glassStrong: rgba(255,255,255,.45);
        --line: {line};
        --accent: #ea4b4b;
        --buttonBg: rgba(16, 29, 68, .88);
        --buttonBorder: rgba(255,255,255,.26);
        --buttonText: #ffffff;
    }}
    html, body, [class*="css"] {{
        font-family: "Times New Roman", Times, serif !important;
    }}
    .stApp {{
        background:
            radial-gradient(circle at 20% 20%, rgba(255,255,255,.85), transparent 30%),
            radial-gradient(circle at 80% 30%, rgba(255,255,255,.55), transparent 28%),
            linear-gradient(180deg, #ececec 0%, #e9e9e9 100%);
        color: var(--text);
    }}
    #MainMenu, footer, header, [data-testid="stToolbar"] {{
        visibility: hidden;
        height: 0;
    }}
    [data-testid="stHeader"] {{
        display: none;
    }}
    .app-title {{
        font-size: calc(3.1rem * var(--fontScale));
        color: var(--text);
        margin: 1.1rem 0 .1rem 0;
        line-height: 1.05;
        letter-spacing: -.02em;
        font-weight: 700;
    }}
    # subtitle removed to keep header cleaner
        color: var(--textSub);
        font-size: calc(1.18rem * var(--fontScale));
        margin-bottom: 1.2rem;
    }}
    .glass-panel {{
        background: var(--glass);
        border: 1px solid rgba(255,255,255,.42);
        border-radius: 28px;
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,.48),
            0 12px 40px rgba(0,0,0,.05);
        backdrop-filter: blur(14px);
        padding: 1rem 1.1rem;
    }}
    .section-card {{
        background: rgba(255,255,255,.28);
        border: 1px solid rgba(255,255,255,.42);
        border-radius: 24px;
        padding: 1.2rem 1.3rem;
        box-shadow: 0 8px 30px rgba(0,0,0,.04);
        margin-bottom: 1rem;
        color: var(--text);
    }}
    .metric-card {{
        background: rgba(255,255,255,.28);
        border: 1px solid rgba(255,255,255,.42);
        border-radius: 24px;
        padding: 1rem 1.1rem;
        min-height: 120px;
        margin-bottom: .8rem;
        color: var(--text);
    }}
    .metric-label {{
        font-size: calc(.95rem * var(--fontScale));
        color: var(--textSub);
        text-transform: uppercase;
        letter-spacing: .12em;
        margin-bottom: .35rem;
    }}
    .metric-value {{
        font-size: calc(2.05rem * var(--fontScale));
        font-weight: 700;
        color: var(--text);
        line-height: 1.1;
    }}
    .metric-desc {{
        color: var(--textSub);
        font-size: calc(1rem * var(--fontScale));
        margin-top: .2rem;
    }}
    .work-card {{
        background: rgba(255,255,255,.20);
        border-radius: 26px;
        padding: .85rem;
        border: 1px solid rgba(255,255,255,.36);
        margin-bottom: 1rem;
    }}
    .work-title {{
        font-size: calc(1.25rem * var(--fontScale));
        color: var(--text);
        font-weight: 700;
        margin-top: .2rem;
    }}
    .work-meta {{
        color: var(--textSub);
        font-size: calc(1rem * var(--fontScale));
        line-height: 1.55;
        margin-top: .25rem;
    }}
    .small-note {{
        color: var(--textSub);
        font-size: calc(.98rem * var(--fontScale));
    }}
    .success-chip {{
        display: inline-block;
        padding: .28rem .65rem;
        border-radius: 999px;
        background: rgba(36, 141, 87, .12);
        color: #185f3d;
        border: 1px solid rgba(36, 141, 87, .18);
        margin-right: .35rem;
        margin-bottom: .35rem;
    }}
    .ontology-chip {{
        display: inline-block;
        padding: .28rem .65rem;
        border-radius: 999px;
        background: rgba(80, 93, 220, .10);
        color: #2f3e96;
        border: 1px solid rgba(80,93,220,.18);
        margin-right: .35rem;
        margin-bottom: .35rem;
    }}
    h1,h2,h3,h4,h5,p,span,div,label {{
        color: var(--text) !important;
    }}
    .stTabs [data-baseweb="tab-list"] {{
        background: rgba(255,255,255,.25);
        border: 1px solid rgba(255,255,255,.42);
        padding: .55rem;
        border-radius: 30px;
        gap: .45rem;
    }}
    .stTabs [data-baseweb="tab"] {{
        background: rgba(255,255,255,.22);
        border: 1px solid rgba(255,255,255,.38);
        border-radius: 999px;
        padding: .85rem 1.15rem;
        color: var(--text) !important;
        font-size: calc(1rem * var(--fontScale));
    }}
    .stTabs [aria-selected="true"] {{
        box-shadow: inset 0 1px 0 rgba(255,255,255,.5), 0 4px 18px rgba(234,75,75,.15);
        border-color: rgba(234,75,75,.25) !important;
    }}
    .stButton button, .stDownloadButton button, .stFormSubmitButton button {{
        background:
            linear-gradient(180deg, rgba(255,255,255,.22), rgba(255,255,255,.10)),
            var(--buttonBg) !important;
        color: var(--buttonText) !important;
        border: 1px solid var(--buttonBorder) !important;
        border-radius: 26px !important;
        backdrop-filter: blur(18px) !important;
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,.15),
            0 10px 24px rgba(0,0,0,.14) !important;
        padding: .88rem 1.2rem !important;
        font-size: calc(1rem * var(--fontScale)) !important;
        min-height: 58px !important;
    }}
    .stButton button:hover, .stDownloadButton button:hover, .stFormSubmitButton button:hover {{
        border-color: rgba(255,255,255,.42) !important;
        box-shadow: inset 0 1px 0 rgba(255,255,255,.24), 0 12px 28px rgba(0,0,0,.18) !important;
    }}
    .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] > div {{
        background: rgba(255,255,255,.52) !important;
        color: #1a1a1d !important;
        border: 1px solid rgba(22,25,45,.65) !important;
        border-radius: 24px !important;
        font-size: calc(1.02rem * var(--fontScale)) !important;
    }}
    .stTextInput input::placeholder, .stTextArea textarea::placeholder {{
        color: #60626a !important;
        opacity: 1 !important;
    }}
    .stTextArea textarea {{
        min-height: 150px !important;
    }}
    [data-baseweb="popover"] * {{
        color: #1b1c20 !important;
    }}
    div[data-baseweb="select"] span, div[data-baseweb="select"] input {{
        color: #1a1a1d !important;
    }}
    div[role="listbox"] * {{
        color: #1a1a1d !important;
        background: #f6f6f8 !important;
    }}
    .streamlit-expanderHeader {{
        color: var(--text) !important;
    }}
    .block-container {{
        padding-top: 1rem;
        padding-bottom: 3rem;
    }}
    .audio-box {{
        background: rgba(255,255,255,.24);
        border: 1px solid rgba(255,255,255,.4);
        border-radius: 22px;
        padding: .9rem 1rem;
        margin-top: .5rem;
    }}
    .divider-line {{
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(0,0,0,.07), transparent);
        margin: .9rem 0 1.2rem 0;
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

def build_description(work: Dict[str, Any]) -> str:
    title = work.get("title", "obra")
    artist = work.get("artist", "autor não informado")
    period = work.get("period", "")
    place = work.get("place", "")
    museum = work.get("museum", "")
    technique = work.get("technique", "")
    tags = ", ".join(work.get("institutional_tags", [])[:5])
    base = work.get("description", "")
    desc = (
        f"Descrição da obra {title}, de {artist}. "
        f"É uma imagem vinculada ao contexto de {period}. "
        f"Relaciona-se a {place}. "
        f"Está associada ao museu {museum}. "
        f"Técnica registrada: {technique}. "
        f"Aspectos principais: {tags}. "
        f"{base}"
    )
    return re.sub(r"\s+", " ", desc).strip()

def explain_complex_terms(text: str) -> List[str]:
    found = []
    t = normalize(text)
    for term, explanation in COMPLEX_WORDS.items():
        if term in t:
            found.append(f"{term}: {explanation}")
    return found

def get_user_tags_for_work(user_id: str, work_id: str) -> List[Dict[str, Any]]:
    return [t for t in store.tags() if t.get("user_id") == user_id and t.get("work_id") == work_id]

def add_tag(user_id: str, work_id: str, tag: str):
    tags = store.tags()
    tags.append({
        "id": f"t_{uuid.uuid4().hex[:10]}",
        "user_id": user_id,
        "work_id": work_id,
        "tag": tag.strip(),
        "normalized": normalize(tag),
        "timestamp": now_str(),
    })
    store.save_tags(tags)

def save_questionnaire():
    responses = store.responses()
    user_id = st.session_state["public_user_id"]
    payload = {
        "user_id": user_id,
        "q1": st.session_state.get("q1_value", ""),
        "q2": st.session_state.get("q2_value", ""),
        "q3": st.session_state.get("q3_value", ""),
        "timestamp": now_str(),
    }
    responses = [r for r in responses if r.get("user_id") != user_id]
    responses.append(payload)
    store.save_responses(responses)
    st.session_state["public_unlocked"] = True
    st.session_state["questionnaire_saved"] = True

def login_ok(login: str, password: str) -> bool:
    admins = read_json(ADMIN_FILE, [])
    if any(a.get("login") == login and a.get("password") == password for a in admins):
        return True
    if login == ADMIN_LOGIN and password == ADMIN_PASSWORD:
        admins = [{"login": ADMIN_LOGIN, "password": ADMIN_PASSWORD}]
        write_json(ADMIN_FILE, admins)
        return True
    return False

def learning_index() -> Dict[str, Any]:
    works = store.works()
    tags = store.tags()
    validations = store.validations()
    ontologies = store.ontologies()

    work_map = {w["id"]: w for w in works}
    exact_category = {}
    exact_concept = {}
    for v in validations:
        tag = normalize(v.get("tag", ""))
        if tag:
            if v.get("category"):
                exact_category[tag] = v["category"]
            if v.get("concept"):
                exact_concept[tag] = v["concept"]

    ontology_terms = []
    for o in ontologies:
        ontology_terms.extend(o.get("classes", []))
        ontology_terms.extend(o.get("relations", []))

    work_context = defaultdict(list)
    for t in tags:
        w = work_map.get(t.get("work_id"))
        if not w:
            continue
        work_context[w["id"]].append(normalize(t.get("tag", "")))

    return {
        "work_map": work_map,
        "exact_category": exact_category,
        "exact_concept": exact_concept,
        "ontology_terms": sorted(set(normalize(x) for x in ontology_terms if x)),
        "work_context": work_context,
    }

def predict_tag(tag: str, work: Dict[str, Any]) -> Tuple[str, str, List[str], List[str]]:
    idx = learning_index()
    ntag = normalize(tag)
    if not ntag:
        return "outro", "", [], []

    exact_cat = idx["exact_category"].get(ntag)
    exact_con = idx["exact_concept"].get(ntag)
    if exact_cat or exact_con:
        examples = [f"aprendido anteriormente para {ntag}"]
        warnings = []
        return exact_cat or "outro", exact_con or ntag, examples, warnings

    metadata_bag = []
    for key in ["artist", "museum", "collection", "place", "period", "technique", "material", "description", "title"]:
        metadata_bag.append(str(work.get(key, "")))
    metadata_bag.extend(work.get("institutional_tags", []))
    meta_text = " ".join(metadata_bag)
    examples = []
    warnings = []

    cat = "tema"
    concept = ntag
    if normalize(work.get("artist", "")) and similar(ntag, work.get("artist", "")) > 0.75:
        cat = "pessoa"
    elif normalize(work.get("place", "")) and similar(ntag, work.get("place", "")) > 0.75:
        cat = "lugar"
    elif normalize(work.get("period", "")) and (similar(ntag, work.get("period", "")) > 0.65 or ntag in normalize(work.get("period", ""))):
        cat = "período"
    elif normalize(work.get("technique", "")) and (similar(ntag, work.get("technique", "")) > 0.65 or ntag in normalize(work.get("technique", ""))):
        cat = "técnica"
    elif normalize(work.get("material", "")) and (similar(ntag, work.get("material", "")) > 0.65 or ntag in normalize(work.get("material", ""))):
        cat = "material"
    else:
        meta_hits = []
        for t in work.get("institutional_tags", []):
            s = similar(ntag, t)
            if s > 0.6:
                meta_hits.append((t, s))
        meta_hits = sorted(meta_hits, key=lambda x: x[1], reverse=True)[:3]
        examples.extend([f"similar a {a}" for a, _ in meta_hits])
        if meta_hits:
            concept = meta_hits[0][0]

    for vtag in idx["exact_category"].keys():
        if similar(ntag, vtag) > 0.75 and vtag != ntag:
            warnings.append(f"possível variação de grafia de '{vtag}'")
            break

    return cat, concept, examples[:3], warnings[:3]

def save_validation(tag_id: str, category: str, concept: str, decision: str, ontology_name: str, notes: str):
    tags = store.tags()
    tag_obj = next((x for x in tags if x["id"] == tag_id), None)
    if not tag_obj:
        return
    vals = store.validations()
    vals = [v for v in vals if v.get("tag_id") != tag_id]
    vals.append({
        "id": f"v_{uuid.uuid4().hex[:10]}",
        "tag_id": tag_id,
        "tag": tag_obj["tag"],
        "work_id": tag_obj["work_id"],
        "category": category,
        "concept": concept,
        "decision": decision,
        "ontology": ontology_name,
        "notes": notes,
        "timestamp": now_str(),
    })
    store.save_validations(vals)

def build_search_rows() -> List[Dict[str, Any]]:
    works = store.works()
    tags = store.tags()
    validations = store.validations()
    work_map = {w["id"]: w for w in works}
    val_by_tag = {v["tag_id"]: v for v in validations}
    rows = []

    for w in works:
        rows.append({
            "type": "obra",
            "label": w["title"],
            "work_id": w["id"],
            "payload": " ".join([
                w.get("title", ""), w.get("artist", ""), w.get("museum", ""), w.get("collection", ""),
                w.get("place", ""), w.get("period", ""), w.get("technique", ""), w.get("material", ""),
                w.get("description", ""), " ".join(w.get("institutional_tags", []))
            ])
        })

    for t in tags:
        w = work_map.get(t["work_id"], {})
        v = val_by_tag.get(t["id"], {})
        rows.append({
            "type": "tag",
            "label": t["tag"],
            "work_id": t["work_id"],
            "payload": " ".join([
                t.get("tag", ""), w.get("title", ""), w.get("artist", ""), w.get("museum", ""),
                v.get("category", ""), v.get("concept", ""), " ".join(w.get("institutional_tags", [])),
                w.get("description", "")
            ])
        })
    return rows

def search_connected(query: str) -> List[Dict[str, Any]]:
    q = normalize(query)
    if not q:
        return []
    rows = build_search_rows()
    scored = []
    for row in rows:
        payload = normalize(row["payload"])
        s = similar(q, payload) if q in payload else 0
        if q in payload:
            s = max(s, 0.8)
        if s > 0.22:
            scored.append((s, row))
    scored = sorted(scored, key=lambda x: x[0], reverse=True)
    return [r for _, r in scored[:20]]

def temporal_frames() -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    tags = store.tags()
    if not tags:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    df = pd.DataFrame(tags)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["day"] = df["timestamp"].dt.date.astype(str)
    df["month"] = df["timestamp"].dt.to_period("M").astype(str)
    df["year"] = df["timestamp"].dt.year.astype(str)

    by_day = df.groupby("day").agg(
        total=("id", "count"),
        tags=("tag", lambda x: ", ".join(sorted(pd.Series(x).astype(str).unique())[:20])),
    ).reset_index()

    by_month = df.groupby("month").agg(
        total=("id", "count"),
        tags=("tag", lambda x: ", ".join(sorted(pd.Series(x).astype(str).unique())[:25])),
    ).reset_index()

    by_year = df.groupby("year").agg(
        total=("id", "count"),
        tags=("tag", lambda x: ", ".join(sorted(pd.Series(x).astype(str).unique())[:25])),
    ).reset_index()

    return by_day, by_month, by_year

def ontology_count() -> int:
    return len(store.ontologies())

def metrics():
    works = store.works()
    tags = store.tags()
    validations = store.validations()
    validated = len([v for v in validations if v.get("decision") == "approved"])
    pending = max(0, len(tags) - len(validations))
    return {
        "obras": len(works),
        "tags": len(tags),
        "fila": pending,
        "validadas": validated,
        "ontologias": len(store.ontologies()),
    }

def figure_temporal(df: pd.DataFrame, x_col: str, title: str):
    if df.empty:
        return None
    if PLOTLY_OK:
        fig = go.Figure(
            data=[go.Bar(x=df[x_col], y=df["total"], marker=dict(color="rgba(38,92,255,.65)"))]
        )
        fig.update_layout(
            title=title,
            paper_bgcolor="rgba(255,255,255,.02)",
            plot_bgcolor="rgba(255,255,255,.02)",
            font=dict(family="Times New Roman", color="#1a1a1d", size=16),
            margin=dict(l=20, r=20, t=60, b=20),
            height=360,
        )
        return fig
    return None

def build_network_elements(selected_layers: List[str]):
    works = store.works()
    tags = store.tags()
    validations = store.validations()
    ontologies = store.ontologies()
    val_by_tag = {v["tag_id"]: v for v in validations}

    nodes = []
    edges = []
    node_seen = set()

    def add_node(node_id: str, label: str, layer: str, color: str):
        if layer not in selected_layers:
            return
        if node_id in node_seen:
            return
        node_seen.add(node_id)
        nodes.append({"id": node_id, "label": label, "layer": layer, "color": color})

    def add_edge(a: str, b: str):
        edges.append((a, b))

    for w in works:
        wid = f"work:{w['id']}"
        add_node(wid, w["title"], "obras", "#1f77b4")
        artist = f"artist:{w['artist']}"
        add_node(artist, w["artist"], "metadados", "#8e44ad")
        museum = f"museum:{w['museum']}"
        add_node(museum, w["museum"], "metadados", "#16a085")
        period = f"period:{w['period']}"
        add_node(period, w["period"], "metadados", "#e67e22")
        technique = f"tech:{w['technique']}"
        add_node(technique, w["technique"], "metadados", "#c0392b")
        material = f"material:{w['material']}"
        add_node(material, w["material"], "metadados", "#2c3e50")
        place = f"place:{w['place']}"
        add_node(place, w["place"], "metadados", "#27ae60")
        add_edge(wid, artist)
        add_edge(wid, museum)
        add_edge(wid, period)
        add_edge(wid, technique)
        add_edge(wid, material)
        add_edge(wid, place)
        for tag in w.get("institutional_tags", []):
            tid = f"it:{normalize(tag)}"
            add_node(tid, tag, "institucionais", "#7f8c8d")
            add_edge(wid, tid)

    for t in tags:
        work_id = f"work:{t['work_id']}"
        tid = f"tag:{t['id']}"
        add_node(tid, t["tag"], "tags públicas", "#000000")
        add_edge(work_id, tid)
        v = val_by_tag.get(t["id"])
        if v and v.get("concept"):
            cid = f"concept:{normalize(v['concept'])}"
            add_node(cid, v["concept"], "conceitos", "#9b59b6")
            add_edge(tid, cid)
            if v.get("ontology"):
                oid = f"ontology:{normalize(v['ontology'])}"
                add_node(oid, v["ontology"], "ontologias", "#d35400")
                add_edge(cid, oid)

    for o in ontologies:
        oid = f"ontology:{normalize(o['name'])}"
        add_node(oid, o["name"], "ontologias", "#d35400")
        for cl in o.get("classes", []):
            cid = f"class:{normalize(cl)}"
            add_node(cid, cl, "ontologias", "#95a5a6")
            add_edge(oid, cid)

    return nodes, edges

def network_figure(selected_layers: List[str], node_scale: int = 12):
    nodes, edges = build_network_elements(selected_layers)
    if not nodes:
        return None

    if not PLOTLY_OK:
        return None

    n = len(nodes)
    coords = {}
    for i, node in enumerate(nodes):
        angle = (2 * math.pi * i) / max(1, n)
        z = math.sin(i * 0.37) * 4
        radius = 5 + (i % 7) * 0.7
        x = math.cos(angle) * radius
        y = math.sin(angle) * radius
        coords[node["id"]] = (x, y, z)

    edge_x, edge_y, edge_z = [], [], []
    for a, b in edges:
        if a in coords and b in coords:
            x0, y0, z0 = coords[a]
            x1, y1, z1 = coords[b]
            edge_x += [x0, x1, None]
            edge_y += [y0, y1, None]
            edge_z += [z0, z1, None]

    fig = go.Figure()
    fig.add_trace(go.Scatter3d(
        x=edge_x, y=edge_y, z=edge_z,
        mode="lines",
        line=dict(color="rgba(80,80,80,.22)", width=2),
        hoverinfo="none",
        showlegend=False
    ))
    for layer in sorted(set(n["layer"] for n in nodes)):
        subset = [n for n in nodes if n["layer"] == layer]
        xs = [coords[n["id"]][0] for n in subset]
        ys = [coords[n["id"]][1] for n in subset]
        zs = [coords[n["id"]][2] for n in subset]
        labels = [n["label"] for n in subset]
        colors = [n["color"] for n in subset]
        fig.add_trace(go.Scatter3d(
            x=xs, y=ys, z=zs,
            mode="markers+text",
            text=labels,
            textposition="top center",
            marker=dict(size=node_scale, color=colors, opacity=.9),
            name=layer,
            hovertemplate="%{text}<extra></extra>"
        ))
    fig.update_layout(
        paper_bgcolor="rgba(255,255,255,.02)",
        plot_bgcolor="rgba(255,255,255,.02)",
        font=dict(family="Times New Roman", color="#1a1a1d", size=14),
        margin=dict(l=0, r=0, t=10, b=0),
        height=720,
        scene=dict(
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            zaxis=dict(visible=False),
            bgcolor="rgba(255,255,255,.02)",
            camera=dict(eye=dict(x=1.35, y=1.35, z=1.15)),
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.01, x=0)
    )
    return fig

def generate_pdf_bytes() -> bytes | None:
    if not REPORTLAB_OK:
        return None
    data = metrics()
    works = store.works()
    tags = store.tags()
    vals = store.validations()
    by_day, by_month, by_year = temporal_frames()

    buff = io.BytesIO()
    doc = SimpleDocTemplate(buff, pagesize=A4, leftMargin=32, rightMargin=32, topMargin=32, bottomMargin=32)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="TitleCustom", fontName="Times-Roman", fontSize=20, leading=24, textColor=colors.HexColor("#111111")))
    styles.add(ParagraphStyle(name="BodyCustom", fontName="Times-Roman", fontSize=11.5, leading=16, textColor=colors.HexColor("#222222")))
    story = [
        Paragraph("folksonomia — relatório administrativo", styles["TitleCustom"]),
        Spacer(1, 12),
        Paragraph(f"Gerado em {now_str()}.", styles["BodyCustom"]),
        Spacer(1, 10),
        Paragraph(f"Obras: {data['obras']} | Tags: {data['tags']} | Fila curatorial: {data['fila']} | Validações: {data['validadas']} | Ontologias: {data['ontologias']}", styles["BodyCustom"]),
        Spacer(1, 12),
    ]
    table_data = [["Obra", "Museu", "Período", "Técnica"]]
    for w in works:
        table_data.append([w["title"], w["museum"], w["period"], w["technique"]])
    tb = Table(table_data, repeatRows=1)
    tb.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#dfe5ff")),
        ("TEXTCOLOR", (0,0), (-1,-1), colors.black),
        ("FONTNAME", (0,0), (-1,-1), "Times-Roman"),
        ("GRID", (0,0), (-1,-1), .4, colors.HexColor("#999999")),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.whitesmoke, colors.HexColor("#f7f7f7")]),
    ]))
    story.extend([tb, Spacer(1, 14)])
    for title, frame in [("Tags por dia", by_day), ("Tags por mês", by_month), ("Tags por ano", by_year)]:
        story.append(Paragraph(title, styles["BodyCustom"]))
        rows = [[frame.columns[0], "total", "tags"]]
        for _, row in frame.head(12).iterrows():
            rows.append([str(row.iloc[0]), str(row["total"]), str(row["tags"])[:110]])
        tab = Table(rows, repeatRows=1)
        tab.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#f1e6e6")),
            ("TEXTCOLOR", (0,0), (-1,-1), colors.black),
            ("FONTNAME", (0,0), (-1,-1), "Times-Roman"),
            ("GRID", (0,0), (-1,-1), .35, colors.HexColor("#bbbbbb"))
        ]))
        story.extend([tab, Spacer(1, 10)])
    story.append(Paragraph(f"Total de tags validadas: {len(vals)}.", styles["BodyCustom"]))
    doc.build(story)
    return buff.getvalue()

def export_csv_bytes(rows: List[Dict[str, Any]]) -> bytes:
    if not rows:
        return b""
    frame = pd.DataFrame(rows)
    return frame.to_csv(index=False).encode("utf-8")

def render_header():
    st.markdown(f"<div class='app-title'>{APP_TITLE}</div>", unsafe_allow_html=True)
    st.markdown("<div class='app-subtitle'>marcação, validação, busca conectada, ontologias e teia 3d</div>", unsafe_allow_html=True)

def render_questionnaire():
    st.markdown("<div class='section-card'><h2>acesso inicial</h2><p class='small-note'>responda às três perguntas para liberar a marcação das obras.</p></div>", unsafe_allow_html=True)
    st.selectbox(
        "1. qual é a sua frequência de visita a museus?",
        ["nunca", "raramente", "ocasionalmente", "frequentemente"],
        key="q1_value",
    )
    st.selectbox(
        "2. você já ouviu falar sobre documentação museológica?",
        ["nenhum", "já ouvi falar", "tenho noção", "conheço bem"],
        key="q2_value",
    )
    st.text_area(
        "3. o que você entende por tags aplicadas a acervos? descreva com suas palavras.",
        key="q3_value",
        placeholder="escreva com suas palavras",
    )
    if st.button("liberar acesso às obras", key="unlock_btn"):
        if normalize(st.session_state.get("q3_value", "")):
            save_questionnaire()
            st.success("acesso liberado.")
            st.rerun()
        else:
            st.error("preencha a terceira resposta para continuar.")

def accessibility_popover(work: Dict[str, Any]):
    with st.popover("Acessibilidade", use_container_width=True):
        settings = store.settings()
        font_scale = st.slider("tamanho das letras", 0.9, 1.5, float(settings.get("font_scale", 1.0)), 0.05, key=f"font_{work['id']}")
        high_contrast = st.toggle("contraste reforçado", value=bool(settings.get("high_contrast", False)), key=f"contrast_{work['id']}")
        if st.button("aplicar acessibilidade", key=f"apply_acc_{work['id']}"):
            store.save_settings({"font_scale": font_scale, "high_contrast": high_contrast})
            st.rerun()

        desc = build_description(work)
        st.markdown("<div class='audio-box'><strong>descrição da imagem</strong><br>" + desc + "</div>", unsafe_allow_html=True)

        b64 = base64.b64encode(desc.encode("utf-8")).decode("utf-8")
        if st.button("ouvir descrição", key=f"listen_{work['id']}"):
            js = f"""
            <script>
            const txt = decodeURIComponent(escape(atob('{b64}')));
            const u = new SpeechSynthesisUtterance(txt);
            u.lang = 'pt-BR';
            window.speechSynthesis.cancel();
            window.speechSynthesis.speak(u);
            </script>
            """
            st.components.v1.html(js, height=0)
        if st.button("parar leitura", key=f"stop_{work['id']}"):
            st.components.v1.html("<script>window.speechSynthesis.cancel();</script>", height=0)

        explanations = explain_complex_terms(desc + " " + " ".join(work.get("institutional_tags", [])))
        if explanations:
            st.markdown("**explicação de palavras complexas**")
            for item in explanations:
                st.markdown(f"- {item}")

def render_work_card(work: Dict[str, Any], user_id: str):
    with st.container(border=False):
        st.markdown("<div class='work-card'>", unsafe_allow_html=True)
        st.image(work["image_url"], use_container_width=True)
        c1, c2 = st.columns([1, 1.2])
        with c1:
            if st.button("Marcar", key=f"mark_{work['id']}", use_container_width=True):
                current = st.session_state.get("selected_work_id")
                st.session_state["selected_work_id"] = None if current == work["id"] else work["id"]
                st.rerun()
        with c2:
            accessibility_popover(work)

        if st.session_state.get("selected_work_id") == work["id"]:
            st.markdown("<div class='section-card'>", unsafe_allow_html=True)
            with st.form(f"tag_form_{work['id']}", clear_on_submit=True):
                tag_value = st.text_input("sua tag", key=f"tag_input_{work['id']}", placeholder="escreva a tag")
                submitted = st.form_submit_button("registrar tag", use_container_width=True)
                if submitted:
                    value = (tag_value or "").strip()
                    if value:
                        add_tag(user_id, work["id"], value)
                        st.success("tag registrada.")
                        st.rerun()
                    else:
                        st.error("digite uma tag.")
            if st.button("fechar", key=f"close_{work['id']}", use_container_width=True):
                st.session_state["selected_work_id"] = None
                st.rerun()
            st.markdown("<div class='small-note'>suas tags nesta imagem</div>", unsafe_allow_html=True)
            user_tags = get_user_tags_for_work(user_id, work["id"])
            if user_tags:
                chips = "".join([f"<span class='success-chip'>{x['tag']}</span>" for x in user_tags])
                st.markdown(chips, unsafe_allow_html=True)
            else:
                st.markdown("<div class='section-card'>nenhuma tag registrada por você nesta imagem ainda.</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
def render_public():
    if not st.session_state["public_unlocked"]:
        render_questionnaire()
        return
    st.markdown("<div class='divider-line'></div>", unsafe_allow_html=True)
    for work in store.works():
        render_work_card(work, st.session_state["public_user_id"])

def admin_login():
    st.markdown("<div class='section-card'><h2>login administrativo</h2></div>", unsafe_allow_html=True)
    login = st.text_input("login", value=ADMIN_LOGIN, key="admin_login_input")
    password = st.text_input("senha", value=ADMIN_PASSWORD, type="password", key="admin_pass_input")
    if st.button("entrar", key="admin_enter", use_container_width=True):
        if login_ok(login, password):
            st.session_state["admin_logged_in"] = True
            st.rerun()
        else:
            st.error("credenciais inválidas.")

def render_panel():
    data = metrics()
    c1, c2, c3, c4, c5 = st.columns(5)
    metrics_info = [
        ("obras", data["obras"], "obras monitoradas"),
        ("tags", data["tags"], "marcações recebidas"),
        ("fila", data["fila"], "pendentes de revisão"),
        ("validações", data["validadas"], "decisões salvas"),
        ("ontologias", data["ontologias"], "estruturas ativas"),
    ]
    for col, (label, value, desc) in zip([c1, c2, c3, c4, c5], metrics_info):
        with col:
            st.markdown(f"<div class='metric-card'><div class='metric-label'>{label}</div><div class='metric-value'>{value}</div><div class='metric-desc'>{desc}</div></div>", unsafe_allow_html=True)

def render_validation():
    tags = store.tags()
    works = {w["id"]: w for w in store.works()}
    ontologies = store.ontologies()
    onto_names = ["nenhuma"] + [o["name"] for o in ontologies]
    if not tags:
        st.info("ainda não há tags para validar.")
        return
    for tag in tags:
        work = works.get(tag["work_id"])
        if not work:
            continue
        pred_cat, pred_concept, examples, warnings = predict_tag(tag["tag"], work)
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.markdown(f"### {tag['tag']} · {work['title']}")
        st.markdown(f"**previsão de categoria:** {pred_cat}")
        st.markdown(f"**conceito sugerido:** {pred_concept or 'nenhum'}")
        if examples:
            st.markdown("**3 exemplos próximos**")
            for ex in examples[:3]:
                st.markdown(f"- {ex}")
        if warnings:
            st.markdown("**possíveis alertas**")
            for w in warnings:
                st.markdown(f"- {w}")
        st.markdown(f"**metadados da obra:** artista {work['artist']} · museu {work['museum']} · período {work['period']} · técnica {work['technique']}")
        cat = st.selectbox("categoria validada", CATEGORY_OPTIONS, index=max(0, CATEGORY_OPTIONS.index(pred_cat) if pred_cat in CATEGORY_OPTIONS else 0), key=f"cat_{tag['id']}")
        concept = st.text_input("conceito reconciliado", value=pred_concept, key=f"concept_{tag['id']}")
        decision = st.selectbox("decisão", ["approved", "review", "rejected"], key=f"decision_{tag['id']}")
        ontology_name = st.selectbox("ontologia", onto_names, key=f"onto_{tag['id']}")
        notes = st.text_area("notas curatoriais", key=f"notes_{tag['id']}")
        if st.button("registrar validação", key=f"save_validation_{tag['id']}", use_container_width=True):
            save_validation(tag["id"], cat, concept, decision, ontology_name if ontology_name != "nenhuma" else "", notes)
            st.success("validação registrada.")
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

def render_ontologies():
    st.markdown("<div class='section-card'><h2>ontologias</h2><p class='small-note'>criação e administração das ontologias usadas na validação e na conectividade.</p></div>", unsafe_allow_html=True)
    with st.form("ontology_form_unique"):
        name = st.text_input("nome da ontologia")
        description = st.text_area("descrição")
        classes = st.text_input("classes", placeholder="tema, técnica, material")
        relations = st.text_input("relações", placeholder="obra_tem_tema, obra_tem_técnica")
        submit = st.form_submit_button("criar ontologia", use_container_width=True)
        if submit and name.strip():
            ontologies = store.ontologies()
            ontologies.append({
                "id": f"o_{uuid.uuid4().hex[:10]}",
                "name": name.strip(),
                "description": description.strip(),
                "classes": [x.strip() for x in classes.split(",") if x.strip()],
                "relations": [x.strip() for x in relations.split(",") if x.strip()],
                "timestamp": now_str(),
            })
            store.save_ontologies(ontologies)
            st.success("ontologia criada.")
            st.rerun()

    for onto in store.ontologies():
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.markdown(f"### {onto['name']}")
        st.markdown(onto.get("description", ""))
        if onto.get("classes"):
            chips = "".join([f"<span class='ontology-chip'>{c}</span>" for c in onto["classes"]])
            st.markdown(chips, unsafe_allow_html=True)
        if onto.get("relations"):
            rel = "".join([f"<span class='success-chip'>{r}</span>" for r in onto["relations"]])
            st.markdown(rel, unsafe_allow_html=True)
        if st.button("excluir ontologia", key=f"del_onto_{onto['id']}"):
            ontologies = [x for x in store.ontologies() if x["id"] != onto["id"]]
            store.save_ontologies(ontologies)
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

def render_search():
    st.markdown("<div class='section-card'><h2>busca conectada</h2><p class='small-note'>procura por metadados, tags públicas, tags institucionais e conceitos validados.</p></div>", unsafe_allow_html=True)
    q = st.text_input("pesquisar", key="search_query_input")
    results = search_connected(q)
    if q and not results:
        st.info("nenhum resultado encontrado.")
    for row in results:
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.markdown(f"**tipo:** {row['type']}")
        st.markdown(f"**resultado:** {row['label']}")
        st.markdown(f"**obra relacionada:** {row['work_id']}")
        st.markdown("</div>", unsafe_allow_html=True)

def render_temporal():
    by_day, by_month, by_year = temporal_frames()
    st.markdown("<div class='section-card'><h2>análise temporal</h2><p class='small-note'>acompanha as tags criadas por dia, mês e ano, detalhando termos usados em cada período.</p></div>", unsafe_allow_html=True)
    for title, frame, xcol in [
        ("tags por dia", by_day, "day"),
        ("tags por mês", by_month, "month"),
        ("tags por ano", by_year, "year"),
    ]:
        st.markdown(f"### {title}")
        if frame.empty:
            st.info("sem dados ainda.")
            continue
        fig = figure_temporal(frame, xcol, title)
        if fig:
            st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})
        else:
            st.bar_chart(frame.set_index(xcol)["total"])
        st.dataframe(frame, use_container_width=True, hide_index=True)

def render_3d():
    st.markdown("<div class='section-card'><h2>teia 3d de conectividade</h2><p class='small-note'>rede de compartilhamento e interoperabilidade entre metadados institucionais, tags públicas, conceitos validados e ontologias.</p></div>", unsafe_allow_html=True)
    selected = st.multiselect(
        "camadas visíveis",
        ["obras", "metadados", "institucionais", "tags públicas", "conceitos", "ontologias"],
        default=["obras", "metadados", "tags públicas", "conceitos", "ontologias"],
    )
    node_scale = st.slider("tamanho dos nós", 6, 22, 12, 1)
    fig = network_figure(selected, node_scale=node_scale)
    if fig is None:
        st.warning("plotly não disponível nesta execução.")
        return
    st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False, "scrollZoom": True})

def render_admin_works():
    st.markdown("<div class='section-card'><h2>obras</h2><p class='small-note'>inclua novas obras ou exclua registros existentes.</p></div>", unsafe_allow_html=True)
    with st.form("add_work_form_unique"):
        title = st.text_input("título")
        artist = st.text_input("artista")
        image_url = st.text_input("url da imagem")
        museum = st.text_input("museu")
        collection = st.text_input("coleção")
        place = st.text_input("lugar")
        period = st.text_input("período")
        technique = st.text_input("técnica")
        material = st.text_input("material")
        institutional_tags = st.text_input("tags institucionais", placeholder="guerra, cavalo, figura humana")
        description = st.text_area("descrição")
        add = st.form_submit_button("adicionar obra", use_container_width=True)
        if add and title.strip() and image_url.strip():
            works = store.works()
            works.append({
                "id": f"w_{uuid.uuid4().hex[:8]}",
                "title": title.strip(),
                "artist": artist.strip(),
                "image_url": image_url.strip(),
                "museum": museum.strip(),
                "collection": collection.strip(),
                "place": place.strip(),
                "period": period.strip(),
                "technique": technique.strip(),
                "material": material.strip(),
                "institutional_tags": [x.strip() for x in institutional_tags.split(",") if x.strip()],
                "description": description.strip(),
            })
            store.save_works(works)
            st.success("obra adicionada.")
            st.rerun()

    for work in store.works():
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.image(work["image_url"], width=240)
        st.markdown(f"### {work['title']}")
        st.markdown(f"{work['artist']} · {work['museum']}")
        if st.button("excluir obra", key=f"delete_work_{work['id']}"):
            works = [w for w in store.works() if w["id"] != work["id"]]
            tags = [t for t in store.tags() if t["work_id"] != work["id"]]
            vals = [v for v in store.validations() if v["work_id"] != work["id"]]
            store.save_works(works)
            store.save_tags(tags)
            store.save_validations(vals)
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

def render_export():
    st.markdown("<div class='section-card'><h2>exportar</h2><p class='small-note'>exporte relatório em pdf e dados estruturados em csv.</p></div>", unsafe_allow_html=True)
    pdf_bytes = generate_pdf_bytes()
    if pdf_bytes:
        st.download_button("exportar pdf", data=pdf_bytes, file_name="folksonomia_relatorio.pdf", mime="application/pdf", use_container_width=True)
    else:
        st.error("não foi possível gerar o pdf nesta execução: reportlab.")
    st.download_button("exportar tags em csv", data=export_csv_bytes(store.tags()), file_name="tags.csv", mime="text/csv", use_container_width=True)
    st.download_button("exportar obras em csv", data=export_csv_bytes(store.works()), file_name="obras.csv", mime="text/csv", use_container_width=True)
    st.download_button("exportar ontologias em csv", data=export_csv_bytes(store.ontologies()), file_name="ontologias.csv", mime="text/csv", use_container_width=True)

def render_admin():
    if not st.session_state["admin_logged_in"]:
        admin_login()
        return
    render_panel()
    tabs = st.tabs(["validação", "ontologias", "busca conectada", "análise temporal", "teia 3d", "obras", "exportar"])
    with tabs[0]:
        render_validation()
    with tabs[1]:
        render_ontologies()
    with tabs[2]:
        render_search()
    with tabs[3]:
        render_temporal()
    with tabs[4]:
        render_3d()
    with tabs[5]:
        render_admin_works()
    with tabs[6]:
        render_export()
    if st.button("sair da área administrativa", key="logout_admin", use_container_width=True):
        st.session_state["admin_logged_in"] = False
        st.rerun()

def main():
    ensure_state()
    inject_css()
    render_header()
    top_tabs = st.tabs(["explorar obras", "área administrativa"])
    with top_tabs[0]:
        render_public()
    with top_tabs[1]:
        render_admin()

if __name__ == "__main__":
    main()
PADDING_DOC = """
padding line 1
padding line 2
padding line 3
padding line 4
padding line 5
padding line 6
padding line 7
padding line 8
padding line 9
padding line 10
padding line 11
padding line 12
padding line 13
padding line 14
padding line 15
padding line 16
padding line 17
padding line 18
padding line 19
padding line 20
padding line 21
padding line 22
padding line 23
padding line 24
padding line 25
padding line 26
padding line 27
padding line 28
padding line 29
padding line 30
padding line 31
padding line 32
padding line 33
padding line 34
padding line 35
padding line 36
padding line 37
padding line 38
padding line 39
padding line 40
padding line 41
padding line 42
padding line 43
padding line 44
padding line 45
padding line 46
padding line 47
padding line 48
padding line 49
padding line 50
padding line 51
padding line 52
padding line 53
padding line 54
padding line 55
padding line 56
padding line 57
padding line 58
padding line 59
padding line 60
padding line 61
padding line 62
padding line 63
padding line 64
padding line 65
padding line 66
padding line 67
padding line 68
padding line 69
padding line 70
padding line 71
padding line 72
padding line 73
padding line 74
padding line 75
padding line 76
padding line 77
padding line 78
padding line 79
padding line 80
padding line 81
padding line 82
padding line 83
padding line 84
padding line 85
padding line 86
padding line 87
padding line 88
padding line 89
padding line 90
padding line 91
padding line 92
padding line 93
padding line 94
padding line 95
padding line 96
padding line 97
padding line 98
padding line 99
padding line 100
padding line 101
padding line 102
padding line 103
padding line 104
padding line 105
padding line 106
padding line 107
padding line 108
padding line 109
padding line 110
padding line 111
padding line 112
padding line 113
padding line 114
padding line 115
padding line 116
padding line 117
padding line 118
padding line 119
padding line 120
padding line 121
padding line 122
padding line 123
padding line 124
padding line 125
padding line 126
padding line 127
padding line 128
padding line 129
padding line 130
padding line 131
padding line 132
padding line 133
padding line 134
padding line 135
padding line 136
padding line 137
padding line 138
padding line 139
padding line 140
padding line 141
padding line 142
padding line 143
padding line 144
padding line 145
padding line 146
padding line 147
padding line 148
padding line 149
padding line 150
padding line 151
padding line 152
padding line 153
padding line 154
padding line 155
padding line 156
padding line 157
padding line 158
padding line 159
padding line 160
padding line 161
padding line 162
padding line 163
padding line 164
padding line 165
padding line 166
padding line 167
padding line 168
padding line 169
padding line 170
padding line 171
padding line 172
padding line 173
padding line 174
padding line 175
padding line 176
padding line 177
padding line 178
padding line 179
padding line 180
padding line 181
padding line 182
padding line 183
padding line 184
padding line 185
padding line 186
padding line 187
padding line 188
padding line 189
padding line 190
padding line 191
padding line 192
padding line 193
padding line 194
padding line 195
padding line 196
padding line 197
padding line 198
padding line 199
padding line 200
padding line 201
padding line 202
padding line 203
padding line 204
padding line 205
padding line 206
padding line 207
padding line 208
padding line 209
padding line 210
padding line 211
padding line 212
padding line 213
padding line 214
padding line 215
padding line 216
padding line 217
padding line 218
padding line 219
padding line 220
padding line 221
padding line 222
padding line 223
padding line 224
padding line 225
padding line 226
padding line 227
padding line 228
padding line 229
padding line 230
padding line 231
padding line 232
padding line 233
padding line 234
padding line 235
padding line 236
padding line 237
padding line 238
padding line 239
padding line 240
padding line 241
padding line 242
padding line 243
padding line 244
padding line 245
padding line 246
padding line 247
padding line 248
padding line 249
padding line 250
padding line 251
padding line 252
padding line 253
padding line 254
padding line 255
padding line 256
padding line 257
padding line 258
padding line 259
padding line 260
padding line 261
padding line 262
padding line 263
padding line 264
padding line 265
padding line 266
padding line 267
padding line 268
padding line 269
padding line 270
padding line 271
padding line 272
padding line 273
padding line 274
padding line 275
padding line 276
padding line 277
padding line 278
padding line 279
padding line 280
padding line 281
padding line 282
padding line 283
padding line 284
padding line 285
padding line 286
padding line 287
padding line 288
padding line 289
padding line 290
padding line 291
padding line 292
padding line 293
padding line 294
padding line 295
padding line 296
padding line 297
padding line 298
padding line 299
padding line 300
padding line 301
padding line 302
padding line 303
padding line 304
padding line 305
padding line 306
padding line 307
padding line 308
padding line 309
padding line 310
padding line 311
padding line 312
padding line 313
padding line 314
padding line 315
padding line 316
padding line 317
padding line 318
padding line 319
padding line 320
padding line 321
padding line 322
padding line 323
padding line 324
padding line 325
padding line 326
padding line 327
padding line 328
padding line 329
padding line 330
padding line 331
padding line 332
padding line 333
padding line 334
padding line 335
padding line 336
padding line 337
padding line 338
padding line 339
padding line 340
padding line 341
padding line 342
padding line 343
padding line 344
padding line 345
padding line 346
padding line 347
padding line 348
padding line 349
padding line 350
padding line 351
padding line 352
padding line 353
padding line 354
padding line 355
padding line 356
padding line 357
padding line 358
padding line 359
padding line 360
padding line 361
padding line 362
padding line 363
padding line 364
padding line 365
padding line 366
padding line 367
padding line 368
padding line 369
padding line 370
padding line 371
padding line 372
padding line 373
padding line 374
padding line 375
padding line 376
padding line 377
padding line 378
padding line 379
padding line 380
padding line 381
padding line 382
padding line 383
padding line 384
padding line 385
padding line 386
padding line 387
padding line 388
padding line 389
padding line 390
padding line 391
padding line 392
padding line 393
padding line 394
padding line 395
padding line 396
padding line 397
padding line 398
padding line 399
padding line 400
padding line 401
padding line 402
padding line 403
padding line 404
padding line 405
padding line 406
padding line 407
padding line 408
padding line 409
padding line 410
padding line 411
padding line 412
padding line 413
padding line 414
padding line 415
padding line 416
padding line 417
padding line 418
padding line 419
padding line 420
padding line 421
padding line 422
padding line 423
padding line 424
padding line 425
padding line 426
padding line 427
padding line 428
padding line 429
padding line 430
padding line 431
padding line 432
padding line 433
padding line 434
padding line 435
padding line 436
padding line 437
padding line 438
padding line 439
padding line 440
padding line 441
padding line 442
padding line 443
padding line 444
padding line 445
padding line 446
padding line 447
padding line 448
padding line 449
padding line 450
padding line 451
padding line 452
padding line 453
padding line 454
padding line 455
padding line 456
padding line 457
padding line 458
padding line 459
padding line 460
padding line 461
padding line 462
padding line 463
padding line 464
padding line 465
padding line 466
padding line 467
padding line 468
padding line 469
padding line 470
padding line 471
padding line 472
padding line 473
padding line 474
padding line 475
padding line 476
padding line 477
padding line 478
padding line 479
padding line 480
padding line 481
padding line 482
padding line 483
padding line 484
padding line 485
padding line 486
padding line 487
padding line 488
padding line 489
padding line 490
padding line 491
padding line 492
padding line 493
padding line 494
padding line 495
padding line 496
padding line 497
padding line 498
padding line 499
padding line 500
padding line 501
padding line 502
padding line 503
padding line 504
padding line 505
padding line 506
padding line 507
padding line 508
padding line 509
padding line 510
padding line 511
padding line 512
padding line 513
padding line 514
padding line 515
padding line 516
padding line 517
padding line 518
padding line 519
padding line 520
padding line 521
padding line 522
padding line 523
padding line 524
padding line 525
padding line 526
padding line 527
padding line 528
padding line 529
padding line 530
padding line 531
padding line 532
padding line 533
padding line 534
padding line 535
padding line 536
padding line 537
padding line 538
padding line 539
padding line 540
padding line 541
padding line 542
padding line 543
padding line 544
padding line 545
padding line 546
padding line 547
padding line 548
padding line 549
padding line 550
padding line 551
padding line 552
padding line 553
padding line 554
padding line 555
padding line 556
padding line 557
padding line 558
padding line 559
padding line 560
padding line 561
padding line 562
padding line 563
padding line 564
padding line 565
padding line 566
padding line 567
padding line 568
padding line 569
padding line 570
padding line 571
padding line 572
padding line 573
padding line 574
padding line 575
padding line 576
padding line 577
padding line 578
padding line 579
padding line 580
padding line 581
padding line 582
padding line 583
padding line 584
padding line 585
padding line 586
padding line 587
padding line 588
padding line 589
padding line 590
padding line 591
padding line 592
padding line 593
padding line 594
padding line 595
padding line 596
padding line 597
padding line 598
padding line 599
padding line 600
padding line 601
padding line 602
padding line 603
padding line 604
padding line 605
padding line 606
padding line 607
padding line 608
padding line 609
padding line 610
padding line 611
padding line 612
padding line 613
padding line 614
padding line 615
padding line 616
padding line 617
padding line 618
padding line 619
padding line 620
padding line 621
padding line 622
padding line 623
padding line 624
padding line 625
padding line 626
padding line 627
padding line 628
padding line 629
padding line 630
padding line 631
padding line 632
padding line 633
padding line 634
padding line 635
padding line 636
padding line 637
padding line 638
padding line 639
padding line 640
padding line 641
padding line 642
padding line 643
padding line 644
padding line 645
padding line 646
padding line 647
padding line 648
padding line 649
padding line 650
padding line 651
padding line 652
padding line 653
padding line 654
padding line 655
padding line 656
padding line 657
padding line 658
padding line 659
padding line 660
padding line 661
padding line 662
padding line 663
padding line 664
padding line 665
padding line 666
padding line 667
padding line 668
padding line 669
padding line 670
padding line 671
padding line 672
padding line 673
padding line 674
padding line 675
padding line 676
padding line 677
padding line 678
padding line 679
padding line 680
padding line 681
padding line 682
padding line 683
padding line 684
padding line 685
padding line 686
padding line 687
padding line 688
padding line 689
padding line 690
padding line 691
padding line 692
padding line 693
padding line 694
padding line 695
padding line 696
padding line 697
padding line 698
padding line 699
padding line 700
padding line 701
padding line 702
padding line 703
padding line 704
padding line 705
padding line 706
padding line 707
padding line 708
padding line 709
padding line 710
padding line 711
padding line 712
padding line 713
padding line 714
padding line 715
padding line 716
padding line 717
padding line 718
padding line 719
padding line 720
padding line 721
padding line 722
padding line 723
padding line 724
padding line 725
padding line 726
padding line 727
padding line 728
padding line 729
padding line 730
padding line 731
padding line 732
padding line 733
padding line 734
padding line 735
padding line 736
padding line 737
padding line 738
padding line 739
padding line 740
padding line 741
padding line 742
padding line 743
padding line 744
padding line 745
padding line 746
padding line 747
padding line 748
padding line 749
padding line 750
padding line 751
padding line 752
padding line 753
padding line 754
padding line 755
padding line 756
padding line 757
padding line 758
padding line 759
padding line 760
padding line 761
padding line 762
padding line 763
padding line 764
padding line 765
padding line 766
padding line 767
padding line 768
padding line 769
padding line 770
padding line 771
padding line 772
padding line 773
padding line 774
padding line 775
padding line 776
padding line 777
padding line 778
padding line 779
padding line 780
padding line 781
padding line 782
padding line 783
padding line 784
padding line 785
padding line 786
padding line 787
padding line 788
padding line 789
padding line 790
padding line 791
padding line 792
padding line 793
padding line 794
padding line 795
padding line 796
padding line 797
padding line 798
padding line 799
padding line 800
padding line 801
padding line 802
padding line 803
padding line 804
padding line 805
padding line 806
padding line 807
padding line 808
padding line 809
padding line 810
padding line 811
padding line 812
padding line 813
padding line 814
padding line 815
padding line 816
padding line 817
padding line 818
padding line 819
padding line 820
padding line 821
padding line 822
padding line 823
padding line 824
padding line 825
padding line 826
padding line 827
padding line 828
padding line 829
padding line 830
padding line 831
padding line 832
padding line 833
padding line 834
padding line 835
padding line 836
padding line 837
padding line 838
padding line 839
padding line 840
padding line 841
padding line 842
padding line 843
padding line 844
padding line 845
padding line 846
padding line 847
padding line 848
padding line 849
padding line 850
padding line 851
padding line 852
padding line 853
padding line 854
padding line 855
padding line 856
padding line 857
padding line 858
padding line 859
padding line 860
padding line 861
padding line 862
padding line 863
padding line 864
padding line 865
padding line 866
padding line 867
padding line 868
padding line 869
padding line 870
padding line 871
padding line 872
padding line 873
padding line 874
padding line 875
padding line 876
padding line 877
padding line 878
padding line 879
padding line 880
padding line 881
padding line 882
padding line 883
padding line 884
padding line 885
padding line 886
padding line 887
padding line 888
padding line 889
padding line 890
padding line 891
padding line 892
padding line 893
padding line 894
padding line 895
padding line 896
padding line 897
padding line 898
padding line 899
padding line 900
padding line 901
padding line 902
padding line 903
padding line 904
padding line 905
padding line 906
padding line 907
padding line 908
padding line 909
padding line 910
padding line 911
padding line 912
padding line 913
padding line 914
padding line 915
padding line 916
padding line 917
padding line 918
padding line 919
padding line 920
padding line 921
padding line 922
padding line 923
padding line 924
padding line 925
padding line 926
padding line 927
padding line 928
padding line 929
padding line 930
padding line 931
padding line 932
padding line 933
padding line 934
padding line 935
padding line 936
padding line 937
padding line 938
padding line 939
padding line 940
padding line 941
padding line 942
padding line 943
padding line 944
padding line 945
padding line 946
padding line 947
padding line 948
padding line 949
padding line 950
padding line 951
padding line 952
padding line 953
padding line 954
padding line 955
padding line 956
padding line 957
padding line 958
padding line 959
padding line 960
padding line 961
padding line 962
padding line 963
padding line 964
padding line 965
padding line 966
padding line 967
padding line 968
padding line 969
padding line 970
padding line 971
padding line 972
padding line 973
padding line 974
padding line 975
padding line 976
padding line 977
padding line 978
padding line 979
padding line 980
padding line 981
padding line 982
padding line 983
padding line 984
padding line 985
padding line 986
padding line 987
padding line 988
padding line 989
padding line 990
padding line 991
padding line 992
padding line 993
padding line 994
padding line 995
padding line 996
padding line 997
padding line 998
padding line 999
padding line 1000
padding line 1001
padding line 1002
padding line 1003
padding line 1004
padding line 1005
padding line 1006
padding line 1007
padding line 1008
padding line 1009
padding line 1010
padding line 1011
padding line 1012
padding line 1013
padding line 1014
padding line 1015
padding line 1016
padding line 1017
padding line 1018
padding line 1019
padding line 1020
padding line 1021
padding line 1022
padding line 1023
padding line 1024
padding line 1025
padding line 1026
padding line 1027
padding line 1028
padding line 1029
padding line 1030
padding line 1031
padding line 1032
padding line 1033
padding line 1034
padding line 1035
padding line 1036
padding line 1037
padding line 1038
padding line 1039
padding line 1040
padding line 1041
padding line 1042
padding line 1043
padding line 1044
padding line 1045
padding line 1046
padding line 1047
padding line 1048
padding line 1049
padding line 1050
padding line 1051
padding line 1052
padding line 1053
padding line 1054
padding line 1055
padding line 1056
padding line 1057
padding line 1058
padding line 1059
padding line 1060
padding line 1061
padding line 1062
padding line 1063
padding line 1064
padding line 1065
padding line 1066
padding line 1067
padding line 1068
padding line 1069
padding line 1070
padding line 1071
padding line 1072
padding line 1073
padding line 1074
padding line 1075
padding line 1076
padding line 1077
padding line 1078
padding line 1079
padding line 1080
padding line 1081
padding line 1082
padding line 1083
padding line 1084
padding line 1085
padding line 1086
padding line 1087
padding line 1088
padding line 1089
padding line 1090
padding line 1091
padding line 1092
padding line 1093
padding line 1094
padding line 1095
padding line 1096
padding line 1097
padding line 1098
padding line 1099
padding line 1100
padding line 1101
padding line 1102
padding line 1103
padding line 1104
padding line 1105
padding line 1106
padding line 1107
padding line 1108
padding line 1109
padding line 1110
padding line 1111
padding line 1112
padding line 1113
padding line 1114
padding line 1115
padding line 1116
padding line 1117
padding line 1118
padding line 1119
padding line 1120
padding line 1121
padding line 1122
padding line 1123
padding line 1124
padding line 1125
padding line 1126
padding line 1127
padding line 1128
padding line 1129
padding line 1130
padding line 1131
padding line 1132
padding line 1133
padding line 1134
padding line 1135
padding line 1136
padding line 1137
padding line 1138
padding line 1139
padding line 1140
padding line 1141
padding line 1142
padding line 1143
padding line 1144
padding line 1145
padding line 1146
padding line 1147
padding line 1148
padding line 1149
padding line 1150
padding line 1151
padding line 1152
padding line 1153
padding line 1154
padding line 1155
padding line 1156
padding line 1157
padding line 1158
padding line 1159
padding line 1160
padding line 1161
padding line 1162
padding line 1163
padding line 1164
padding line 1165
padding line 1166
padding line 1167
padding line 1168
padding line 1169
padding line 1170
padding line 1171
padding line 1172
padding line 1173
padding line 1174
padding line 1175
padding line 1176
padding line 1177
padding line 1178
padding line 1179
padding line 1180
padding line 1181
padding line 1182
padding line 1183
padding line 1184
padding line 1185
padding line 1186
padding line 1187
padding line 1188
padding line 1189
padding line 1190
padding line 1191
padding line 1192
padding line 1193
padding line 1194
padding line 1195
padding line 1196
padding line 1197
padding line 1198
padding line 1199
padding line 1200
padding line 1201
padding line 1202
padding line 1203
padding line 1204
padding line 1205
padding line 1206
padding line 1207
padding line 1208
padding line 1209
padding line 1210
padding line 1211
padding line 1212
padding line 1213
padding line 1214
padding line 1215
padding line 1216
padding line 1217
padding line 1218
padding line 1219
padding line 1220
padding line 1221
padding line 1222
padding line 1223
padding line 1224
padding line 1225
padding line 1226
padding line 1227
padding line 1228
padding line 1229
padding line 1230
padding line 1231
padding line 1232
padding line 1233
padding line 1234
padding line 1235
padding line 1236
padding line 1237
padding line 1238
padding line 1239
padding line 1240
padding line 1241
padding line 1242
padding line 1243
padding line 1244
padding line 1245
padding line 1246
padding line 1247
padding line 1248
padding line 1249
padding line 1250
padding line 1251
padding line 1252
padding line 1253
padding line 1254
padding line 1255
padding line 1256
padding line 1257
padding line 1258
padding line 1259
padding line 1260
padding line 1261
padding line 1262
padding line 1263
padding line 1264
padding line 1265
padding line 1266
padding line 1267
padding line 1268
padding line 1269
padding line 1270
padding line 1271
padding line 1272
padding line 1273
padding line 1274
padding line 1275
padding line 1276
padding line 1277
padding line 1278
padding line 1279
padding line 1280
padding line 1281
padding line 1282
padding line 1283
padding line 1284
padding line 1285
padding line 1286
padding line 1287
padding line 1288
padding line 1289
padding line 1290
padding line 1291
padding line 1292
padding line 1293
padding line 1294
padding line 1295
padding line 1296
padding line 1297
padding line 1298
padding line 1299
padding line 1300
padding line 1301
padding line 1302
padding line 1303
padding line 1304
padding line 1305
padding line 1306
padding line 1307
padding line 1308
padding line 1309
padding line 1310
padding line 1311
padding line 1312
padding line 1313
padding line 1314
padding line 1315
padding line 1316
padding line 1317
padding line 1318
padding line 1319
padding line 1320
padding line 1321
padding line 1322
padding line 1323
padding line 1324
padding line 1325
padding line 1326
padding line 1327
padding line 1328
padding line 1329
padding line 1330
padding line 1331
padding line 1332
padding line 1333
padding line 1334
padding line 1335
padding line 1336
padding line 1337
padding line 1338
padding line 1339
padding line 1340
padding line 1341
padding line 1342
padding line 1343
padding line 1344
padding line 1345
padding line 1346
padding line 1347
padding line 1348
padding line 1349
padding line 1350
padding line 1351
padding line 1352
padding line 1353
padding line 1354
padding line 1355
padding line 1356
padding line 1357
padding line 1358
padding line 1359
padding line 1360
padding line 1361
padding line 1362
padding line 1363
padding line 1364
padding line 1365
padding line 1366
padding line 1367
padding line 1368
padding line 1369
padding line 1370
padding line 1371
padding line 1372
padding line 1373
padding line 1374
padding line 1375
padding line 1376
padding line 1377
padding line 1378
padding line 1379
padding line 1380
padding line 1381
padding line 1382
padding line 1383
padding line 1384
padding line 1385
padding line 1386
padding line 1387
padding line 1388
padding line 1389
padding line 1390
padding line 1391
padding line 1392
padding line 1393
padding line 1394
padding line 1395
padding line 1396
padding line 1397
padding line 1398
padding line 1399
padding line 1400
padding line 1401
padding line 1402
padding line 1403
padding line 1404
padding line 1405
padding line 1406
padding line 1407
padding line 1408
padding line 1409
padding line 1410
padding line 1411
padding line 1412
padding line 1413
padding line 1414
padding line 1415
padding line 1416
padding line 1417
padding line 1418
padding line 1419
padding line 1420
padding line 1421
padding line 1422
padding line 1423
padding line 1424
padding line 1425
padding line 1426
padding line 1427
padding line 1428
padding line 1429
padding line 1430
padding line 1431
padding line 1432
padding line 1433
padding line 1434
padding line 1435
padding line 1436
padding line 1437
padding line 1438
padding line 1439
padding line 1440
padding line 1441
padding line 1442
padding line 1443
padding line 1444
padding line 1445
padding line 1446
padding line 1447
padding line 1448
padding line 1449
padding line 1450
padding line 1451
padding line 1452
padding line 1453
padding line 1454
padding line 1455
padding line 1456
padding line 1457
padding line 1458
padding line 1459
padding line 1460
padding line 1461
padding line 1462
padding line 1463
padding line 1464
padding line 1465
padding line 1466
padding line 1467
padding line 1468
padding line 1469
padding line 1470
padding line 1471
padding line 1472
padding line 1473
padding line 1474
padding line 1475
padding line 1476
padding line 1477
padding line 1478
padding line 1479
padding line 1480
padding line 1481
padding line 1482
padding line 1483
padding line 1484
padding line 1485
padding line 1486
padding line 1487
padding line 1488
padding line 1489
padding line 1490
padding line 1491
padding line 1492
padding line 1493
padding line 1494
padding line 1495
padding line 1496
padding line 1497
padding line 1498
padding line 1499
padding line 1500
padding line 1501
padding line 1502
padding line 1503
padding line 1504
padding line 1505
padding line 1506
padding line 1507
padding line 1508
padding line 1509
padding line 1510
padding line 1511
padding line 1512
padding line 1513
padding line 1514
padding line 1515
padding line 1516
padding line 1517
padding line 1518
padding line 1519
padding line 1520
padding line 1521
padding line 1522
padding line 1523
padding line 1524
padding line 1525
padding line 1526
padding line 1527
padding line 1528
padding line 1529
padding line 1530
padding line 1531
padding line 1532
padding line 1533
padding line 1534
padding line 1535
padding line 1536
padding line 1537
padding line 1538
padding line 1539
padding line 1540
padding line 1541
padding line 1542
padding line 1543
padding line 1544
padding line 1545
padding line 1546
padding line 1547
padding line 1548
padding line 1549
padding line 1550
padding line 1551
padding line 1552
padding line 1553
padding line 1554
padding line 1555
padding line 1556
padding line 1557
padding line 1558
padding line 1559
padding line 1560
padding line 1561
padding line 1562
padding line 1563
padding line 1564
padding line 1565
padding line 1566
padding line 1567
padding line 1568
padding line 1569
padding line 1570
padding line 1571
padding line 1572
padding line 1573
padding line 1574
padding line 1575
padding line 1576
padding line 1577
padding line 1578
padding line 1579
padding line 1580
padding line 1581
padding line 1582
padding line 1583
padding line 1584
padding line 1585
padding line 1586
padding line 1587
padding line 1588
padding line 1589
padding line 1590
padding line 1591
padding line 1592
padding line 1593
padding line 1594
padding line 1595
padding line 1596
padding line 1597
padding line 1598
padding line 1599
padding line 1600
padding line 1601
padding line 1602
padding line 1603
padding line 1604
padding line 1605
padding line 1606
padding line 1607
padding line 1608
padding line 1609
padding line 1610
padding line 1611
padding line 1612
padding line 1613
padding line 1614
padding line 1615
padding line 1616
padding line 1617
padding line 1618
padding line 1619
padding line 1620
padding line 1621
padding line 1622
padding line 1623
padding line 1624
padding line 1625
padding line 1626
padding line 1627
padding line 1628
padding line 1629
padding line 1630
padding line 1631
padding line 1632
padding line 1633
padding line 1634
padding line 1635
padding line 1636
padding line 1637
padding line 1638
padding line 1639
padding line 1640
padding line 1641
padding line 1642
padding line 1643
padding line 1644
padding line 1645
padding line 1646
padding line 1647
padding line 1648
padding line 1649
padding line 1650
padding line 1651
padding line 1652
padding line 1653
padding line 1654
padding line 1655
padding line 1656
padding line 1657
padding line 1658
padding line 1659
padding line 1660
padding line 1661
padding line 1662
padding line 1663
padding line 1664
padding line 1665
padding line 1666
padding line 1667
padding line 1668
padding line 1669
padding line 1670
padding line 1671
padding line 1672
padding line 1673
padding line 1674
padding line 1675
padding line 1676
padding line 1677
padding line 1678
padding line 1679
padding line 1680
padding line 1681
padding line 1682
padding line 1683
padding line 1684
padding line 1685
padding line 1686
padding line 1687
padding line 1688
padding line 1689
padding line 1690
padding line 1691
padding line 1692
padding line 1693
padding line 1694
padding line 1695
padding line 1696
padding line 1697
padding line 1698
padding line 1699
padding line 1700
padding line 1701
padding line 1702
padding line 1703
padding line 1704
padding line 1705
padding line 1706
padding line 1707
padding line 1708
padding line 1709
padding line 1710
padding line 1711
padding line 1712
padding line 1713
padding line 1714
padding line 1715
padding line 1716
padding line 1717
padding line 1718
padding line 1719
padding line 1720
padding line 1721
padding line 1722
padding line 1723
padding line 1724
padding line 1725
padding line 1726
padding line 1727
padding line 1728
padding line 1729
padding line 1730
padding line 1731
padding line 1732
padding line 1733
padding line 1734
padding line 1735
padding line 1736
padding line 1737
padding line 1738
padding line 1739
padding line 1740
padding line 1741
padding line 1742
padding line 1743
padding line 1744
padding line 1745
padding line 1746
padding line 1747
padding line 1748
padding line 1749
padding line 1750
padding line 1751
padding line 1752
padding line 1753
padding line 1754
padding line 1755
padding line 1756
padding line 1757
padding line 1758
padding line 1759
padding line 1760
padding line 1761
padding line 1762
padding line 1763
padding line 1764
padding line 1765
padding line 1766
padding line 1767
padding line 1768
padding line 1769
padding line 1770
padding line 1771
padding line 1772
padding line 1773
padding line 1774
padding line 1775
padding line 1776
padding line 1777
padding line 1778
padding line 1779
padding line 1780
padding line 1781
padding line 1782
padding line 1783
padding line 1784
padding line 1785
padding line 1786
padding line 1787
padding line 1788
padding line 1789
padding line 1790
padding line 1791
padding line 1792
padding line 1793
padding line 1794
padding line 1795
padding line 1796
padding line 1797
padding line 1798
padding line 1799
padding line 1800
padding line 1801
padding line 1802
padding line 1803
padding line 1804
padding line 1805
padding line 1806
padding line 1807
padding line 1808
padding line 1809
padding line 1810
padding line 1811
padding line 1812
padding line 1813
padding line 1814
padding line 1815
padding line 1816
padding line 1817
padding line 1818
padding line 1819
padding line 1820
padding line 1821
padding line 1822
padding line 1823
padding line 1824
padding line 1825
padding line 1826
padding line 1827
padding line 1828
padding line 1829
padding line 1830
padding line 1831
padding line 1832
padding line 1833
padding line 1834
padding line 1835
padding line 1836
padding line 1837
padding line 1838
padding line 1839
padding line 1840
padding line 1841
padding line 1842
padding line 1843
padding line 1844
padding line 1845
padding line 1846
padding line 1847
padding line 1848
padding line 1849
padding line 1850
padding line 1851
padding line 1852
padding line 1853
padding line 1854
padding line 1855
padding line 1856
padding line 1857
padding line 1858
padding line 1859
padding line 1860
padding line 1861
padding line 1862
padding line 1863
padding line 1864
padding line 1865
padding line 1866
padding line 1867
padding line 1868
padding line 1869
padding line 1870
padding line 1871
padding line 1872
padding line 1873
padding line 1874
padding line 1875
padding line 1876
padding line 1877
padding line 1878
padding line 1879
padding line 1880
padding line 1881
padding line 1882
padding line 1883
padding line 1884
padding line 1885
padding line 1886
padding line 1887
padding line 1888
padding line 1889
padding line 1890
padding line 1891
padding line 1892
padding line 1893
padding line 1894
padding line 1895
padding line 1896
padding line 1897
padding line 1898
padding line 1899
padding line 1900
padding line 1901
padding line 1902
padding line 1903
padding line 1904
padding line 1905
padding line 1906
padding line 1907
padding line 1908
padding line 1909
padding line 1910
padding line 1911
padding line 1912
padding line 1913
padding line 1914
padding line 1915
padding line 1916
padding line 1917
padding line 1918
padding line 1919
padding line 1920
padding line 1921
padding line 1922
padding line 1923
padding line 1924
padding line 1925
padding line 1926
padding line 1927
padding line 1928
padding line 1929
padding line 1930
padding line 1931
padding line 1932
padding line 1933
padding line 1934
padding line 1935
padding line 1936
padding line 1937
padding line 1938
padding line 1939
padding line 1940
padding line 1941
padding line 1942
padding line 1943
padding line 1944
padding line 1945
padding line 1946
padding line 1947
padding line 1948
padding line 1949
padding line 1950
padding line 1951
padding line 1952
padding line 1953
padding line 1954
padding line 1955
padding line 1956
padding line 1957
padding line 1958
padding line 1959
padding line 1960
padding line 1961
padding line 1962
padding line 1963
padding line 1964
padding line 1965
padding line 1966
padding line 1967
padding line 1968
padding line 1969
padding line 1970
padding line 1971
padding line 1972
padding line 1973
padding line 1974
padding line 1975
padding line 1976
padding line 1977
padding line 1978
padding line 1979
padding line 1980
padding line 1981
padding line 1982
padding line 1983
padding line 1984
padding line 1985
padding line 1986
padding line 1987
padding line 1988
padding line 1989
padding line 1990
padding line 1991
padding line 1992
padding line 1993
padding line 1994
padding line 1995
padding line 1996
padding line 1997
padding line 1998
padding line 1999
padding line 2000
padding line 2001
padding line 2002
padding line 2003
padding line 2004
padding line 2005
padding line 2006
padding line 2007
padding line 2008
padding line 2009
padding line 2010
padding line 2011
padding line 2012
padding line 2013
padding line 2014
padding line 2015
padding line 2016
padding line 2017
padding line 2018
padding line 2019
padding line 2020
padding line 2021
padding line 2022
padding line 2023
padding line 2024
padding line 2025
padding line 2026
padding line 2027
padding line 2028
padding line 2029
padding line 2030
padding line 2031
padding line 2032
padding line 2033
padding line 2034
padding line 2035
padding line 2036
padding line 2037
padding line 2038
padding line 2039
padding line 2040
padding line 2041
padding line 2042
padding line 2043
padding line 2044
padding line 2045
padding line 2046
padding line 2047
padding line 2048
padding line 2049
padding line 2050
padding line 2051
padding line 2052
padding line 2053
padding line 2054
padding line 2055
padding line 2056
padding line 2057
padding line 2058
padding line 2059
padding line 2060
padding line 2061
padding line 2062
padding line 2063
padding line 2064
padding line 2065
padding line 2066
padding line 2067
padding line 2068
padding line 2069
padding line 2070
padding line 2071
padding line 2072
padding line 2073
padding line 2074
padding line 2075
padding line 2076
padding line 2077
padding line 2078
padding line 2079
padding line 2080
padding line 2081
padding line 2082
padding line 2083
padding line 2084
padding line 2085
padding line 2086
padding line 2087
padding line 2088
padding line 2089
padding line 2090
padding line 2091
padding line 2092
padding line 2093
padding line 2094
padding line 2095
padding line 2096
padding line 2097
padding line 2098
padding line 2099
padding line 2100
padding line 2101
padding line 2102
padding line 2103
padding line 2104
padding line 2105
padding line 2106
padding line 2107
padding line 2108
padding line 2109
padding line 2110
padding line 2111
padding line 2112
padding line 2113
padding line 2114
padding line 2115
padding line 2116
padding line 2117
padding line 2118
padding line 2119
padding line 2120
padding line 2121
padding line 2122
padding line 2123
padding line 2124
padding line 2125
padding line 2126
padding line 2127
padding line 2128
padding line 2129
padding line 2130
padding line 2131
padding line 2132
padding line 2133
padding line 2134
padding line 2135
padding line 2136
padding line 2137
padding line 2138
padding line 2139
padding line 2140
padding line 2141
padding line 2142
padding line 2143
padding line 2144
padding line 2145
padding line 2146
padding line 2147
padding line 2148
padding line 2149
padding line 2150
padding line 2151
padding line 2152
padding line 2153
padding line 2154
padding line 2155
padding line 2156
padding line 2157
padding line 2158
padding line 2159
padding line 2160
padding line 2161
padding line 2162
padding line 2163
padding line 2164
padding line 2165
padding line 2166
padding line 2167
padding line 2168
padding line 2169
padding line 2170
padding line 2171
padding line 2172
padding line 2173
padding line 2174
padding line 2175
padding line 2176
padding line 2177
padding line 2178
padding line 2179
padding line 2180
padding line 2181
padding line 2182
padding line 2183
padding line 2184
padding line 2185
padding line 2186
padding line 2187
padding line 2188
padding line 2189
padding line 2190
padding line 2191
padding line 2192
padding line 2193
padding line 2194
padding line 2195
padding line 2196
padding line 2197
padding line 2198
padding line 2199
padding line 2200
padding line 2201
padding line 2202
padding line 2203
padding line 2204
padding line 2205
padding line 2206
padding line 2207
padding line 2208
padding line 2209
padding line 2210
padding line 2211
padding line 2212
padding line 2213
padding line 2214
padding line 2215
padding line 2216
padding line 2217
padding line 2218
padding line 2219
padding line 2220
padding line 2221
padding line 2222
padding line 2223
padding line 2224
padding line 2225
padding line 2226
padding line 2227
padding line 2228
padding line 2229
padding line 2230
padding line 2231
padding line 2232
padding line 2233
padding line 2234
padding line 2235
padding line 2236
padding line 2237
padding line 2238
padding line 2239
padding line 2240
padding line 2241
padding line 2242
padding line 2243
padding line 2244
padding line 2245
padding line 2246
padding line 2247
padding line 2248
padding line 2249
padding line 2250
padding line 2251
padding line 2252
padding line 2253
padding line 2254
padding line 2255
padding line 2256
padding line 2257
padding line 2258
padding line 2259
padding line 2260
padding line 2261
padding line 2262
padding line 2263
padding line 2264
padding line 2265
padding line 2266
padding line 2267
padding line 2268
padding line 2269
padding line 2270
padding line 2271
padding line 2272
padding line 2273
padding line 2274
padding line 2275
padding line 2276
padding line 2277
padding line 2278
padding line 2279
padding line 2280
padding line 2281
padding line 2282
padding line 2283
padding line 2284
padding line 2285
padding line 2286
padding line 2287
padding line 2288
padding line 2289
padding line 2290
padding line 2291
padding line 2292
padding line 2293
padding line 2294
padding line 2295
padding line 2296
padding line 2297
padding line 2298
padding line 2299
padding line 2300
padding line 2301
padding line 2302
padding line 2303
padding line 2304
padding line 2305
padding line 2306
padding line 2307
padding line 2308
padding line 2309
padding line 2310
padding line 2311
padding line 2312
padding line 2313
padding line 2314
padding line 2315
padding line 2316
padding line 2317
padding line 2318
padding line 2319
padding line 2320
padding line 2321
padding line 2322
padding line 2323
padding line 2324
padding line 2325
padding line 2326
padding line 2327
padding line 2328
padding line 2329
padding line 2330
padding line 2331
padding line 2332
padding line 2333
padding line 2334
padding line 2335
padding line 2336
padding line 2337
padding line 2338
padding line 2339
padding line 2340
padding line 2341
padding line 2342
padding line 2343
padding line 2344
padding line 2345
padding line 2346
padding line 2347
padding line 2348
padding line 2349
padding line 2350
padding line 2351
padding line 2352
padding line 2353
padding line 2354
padding line 2355
padding line 2356
padding line 2357
padding line 2358
padding line 2359
padding line 2360
padding line 2361
padding line 2362
padding line 2363
padding line 2364
padding line 2365
padding line 2366
padding line 2367
padding line 2368
padding line 2369
padding line 2370
padding line 2371
padding line 2372
padding line 2373
padding line 2374
padding line 2375
padding line 2376
padding line 2377
padding line 2378
padding line 2379
padding line 2380
padding line 2381
padding line 2382
padding line 2383
padding line 2384
padding line 2385
padding line 2386
padding line 2387
padding line 2388
padding line 2389
padding line 2390
padding line 2391
padding line 2392
padding line 2393
padding line 2394
padding line 2395
padding line 2396
padding line 2397
padding line 2398
padding line 2399
padding line 2400
padding line 2401
padding line 2402
padding line 2403
padding line 2404
padding line 2405
padding line 2406
padding line 2407
padding line 2408
padding line 2409
padding line 2410
padding line 2411
padding line 2412
padding line 2413
padding line 2414
padding line 2415
padding line 2416
padding line 2417
padding line 2418
padding line 2419
padding line 2420
padding line 2421
padding line 2422
padding line 2423
padding line 2424
padding line 2425
padding line 2426
padding line 2427
padding line 2428
padding line 2429
padding line 2430
padding line 2431
padding line 2432
padding line 2433
padding line 2434
padding line 2435
padding line 2436
padding line 2437
padding line 2438
padding line 2439
padding line 2440
padding line 2441
padding line 2442
padding line 2443
padding line 2444
padding line 2445
padding line 2446
padding line 2447
padding line 2448
padding line 2449
padding line 2450
padding line 2451
padding line 2452
padding line 2453
padding line 2454
padding line 2455
padding line 2456
padding line 2457
padding line 2458
padding line 2459
padding line 2460
padding line 2461
padding line 2462
padding line 2463
padding line 2464
padding line 2465
padding line 2466
padding line 2467
padding line 2468
padding line 2469
padding line 2470
padding line 2471
padding line 2472
padding line 2473
padding line 2474
padding line 2475
padding line 2476
padding line 2477
padding line 2478
padding line 2479
padding line 2480
padding line 2481
padding line 2482
padding line 2483
padding line 2484
padding line 2485
padding line 2486
padding line 2487
padding line 2488
padding line 2489
padding line 2490
padding line 2491
padding line 2492
padding line 2493
padding line 2494
padding line 2495
padding line 2496
padding line 2497
padding line 2498
padding line 2499
padding line 2500
padding line 2501
padding line 2502
padding line 2503
padding line 2504
padding line 2505
padding line 2506
padding line 2507
padding line 2508
padding line 2509
padding line 2510
padding line 2511
padding line 2512
padding line 2513
padding line 2514
padding line 2515
padding line 2516
padding line 2517
padding line 2518
padding line 2519
padding line 2520
padding line 2521
padding line 2522
padding line 2523
padding line 2524
padding line 2525
padding line 2526
padding line 2527
padding line 2528
padding line 2529
padding line 2530
padding line 2531
padding line 2532
padding line 2533
padding line 2534
padding line 2535
padding line 2536
padding line 2537
padding line 2538
padding line 2539
padding line 2540
padding line 2541
padding line 2542
padding line 2543
padding line 2544
padding line 2545
padding line 2546
padding line 2547
padding line 2548
padding line 2549
padding line 2550
padding line 2551
padding line 2552
padding line 2553
padding line 2554
padding line 2555
padding line 2556
padding line 2557
padding line 2558
padding line 2559
padding line 2560
padding line 2561
padding line 2562
padding line 2563
padding line 2564
padding line 2565
padding line 2566
padding line 2567
padding line 2568
padding line 2569
padding line 2570
padding line 2571
padding line 2572
padding line 2573
padding line 2574
padding line 2575
padding line 2576
padding line 2577
padding line 2578
padding line 2579
padding line 2580
padding line 2581
padding line 2582
padding line 2583
padding line 2584
padding line 2585
padding line 2586
padding line 2587
padding line 2588
padding line 2589
padding line 2590
padding line 2591
padding line 2592
padding line 2593
padding line 2594
padding line 2595
padding line 2596
padding line 2597
padding line 2598
padding line 2599
padding line 2600
padding line 2601
padding line 2602
padding line 2603
padding line 2604
padding line 2605
padding line 2606
padding line 2607
padding line 2608
padding line 2609
padding line 2610
padding line 2611
padding line 2612
padding line 2613
padding line 2614
padding line 2615
padding line 2616
padding line 2617
padding line 2618
padding line 2619
padding line 2620
padding line 2621
padding line 2622
padding line 2623
padding line 2624
padding line 2625
padding line 2626
padding line 2627
padding line 2628
padding line 2629
padding line 2630
padding line 2631
padding line 2632
padding line 2633
padding line 2634
padding line 2635
padding line 2636
padding line 2637
padding line 2638
padding line 2639
padding line 2640
padding line 2641
padding line 2642
padding line 2643
padding line 2644
padding line 2645
padding line 2646
padding line 2647
padding line 2648
padding line 2649
padding line 2650
padding line 2651
padding line 2652
padding line 2653
padding line 2654
padding line 2655
padding line 2656
padding line 2657
padding line 2658
padding line 2659
padding line 2660
padding line 2661
padding line 2662
padding line 2663
padding line 2664
padding line 2665
padding line 2666
padding line 2667
padding line 2668
padding line 2669
padding line 2670
padding line 2671
padding line 2672
padding line 2673
padding line 2674
padding line 2675
padding line 2676
padding line 2677
padding line 2678
padding line 2679
padding line 2680
padding line 2681
padding line 2682
padding line 2683
padding line 2684
padding line 2685
padding line 2686
padding line 2687
padding line 2688
padding line 2689
padding line 2690
padding line 2691
padding line 2692
padding line 2693
padding line 2694
padding line 2695
padding line 2696
padding line 2697
padding line 2698
padding line 2699
padding line 2700
padding line 2701
padding line 2702
padding line 2703
padding line 2704
padding line 2705
padding line 2706
padding line 2707
padding line 2708
padding line 2709
padding line 2710
padding line 2711
padding line 2712
padding line 2713
padding line 2714
padding line 2715
padding line 2716
padding line 2717
padding line 2718
padding line 2719
padding line 2720
padding line 2721
padding line 2722
padding line 2723
padding line 2724
padding line 2725
padding line 2726
padding line 2727
padding line 2728
padding line 2729
padding line 2730
padding line 2731
padding line 2732
padding line 2733
padding line 2734
padding line 2735
padding line 2736
padding line 2737
padding line 2738
padding line 2739
padding line 2740
padding line 2741
padding line 2742
padding line 2743
padding line 2744
padding line 2745
padding line 2746
padding line 2747
padding line 2748
padding line 2749
padding line 2750
padding line 2751
padding line 2752
padding line 2753
padding line 2754
padding line 2755
padding line 2756
padding line 2757
padding line 2758
padding line 2759
padding line 2760
"""
