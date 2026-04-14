
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
    .app-subtitle {{
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
    st.markdown("<div class='section-card'><h2>acesso inicial</h2><p class='small-note'>primeiro responda ao questionário. só depois a interface de marcação das obras será liberada.</p></div>", unsafe_allow_html=True)
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
                st.session_state["selected_work_id"] = work["id"]
        with c2:
            accessibility_popover(work)

        if st.session_state.get("selected_work_id") == work["id"]:
            st.text_input("sua tag", key=f"tag_input_{work['id']}", placeholder="escreva a tag")
            c3, c4 = st.columns([1, 1])
            with c3:
                if st.button("registrar tag", key=f"save_tag_{work['id']}", use_container_width=True):
                    value = st.session_state.get(f"tag_input_{work['id']}", "").strip()
                    if value:
                        add_tag(user_id, work["id"], value)
                        st.success("tag registrada.")
                        st.session_state[f"tag_input_{work['id']}"] = ""
                        st.rerun()
                    else:
                        st.error("digite uma tag.")
            with c4:
                if st.button("fechar", key=f"close_{work['id']}", use_container_width=True):
                    st.session_state["selected_work_id"] = None
                    st.rerun()

        user_tags = get_user_tags_for_work(user_id, work["id"])
        st.markdown("<div class='small-note'>suas tags nesta imagem</div>", unsafe_allow_html=True)
        if user_tags:
            chips = "".join([f"<span class='success-chip'>{x['tag']}</span>" for x in user_tags])
            st.markdown(chips, unsafe_allow_html=True)
        else:
            st.markdown("<div class='section-card'>nenhuma tag registrada por você nesta imagem ainda.</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

def render_public():
    if not st.session_state["public_unlocked"]:
        render_questionnaire()
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
