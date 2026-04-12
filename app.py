from __future__ import annotations

import base64
import hashlib
import json
import math
import os
import random
import statistics
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import streamlit as st

try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except Exception:
    nx = None
    NETWORKX_AVAILABLE = False

try:
    import plotly.express as px
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except Exception:
    px = None
    go = None
    PLOTLY_AVAILABLE = False

from semantic_engine import (
    SemanticKnowledgeBase,
    bootstrap_default_concepts,
    lexical_similarity,
    normalize_text,
)

st.set_page_config(
    page_title="Sistema Folksonomia Digital Inteligente",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="collapsed",
)

APP_TITLE = "Sistema Folksonomia Digital Inteligente"
APP_SUBTITLE = "Folksonomia assistida semanticamente, reconciliação conceitual, aprendizado incremental e automação"
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
EXPORT_DIR = BASE_DIR / "exports"
CONFIG_DIR = BASE_DIR / "config"

OBRAS_FILE = DATA_DIR / "obras.json"
TAGS_FILE = DATA_DIR / "tags.json"
USERS_FILE = DATA_DIR / "users.json"
ADMIN_FILE = DATA_DIR / "admin.json"
FEEDBACK_FILE = DATA_DIR / "feedback.json"
EVENTS_FILE = DATA_DIR / "events.json"
AUTOMATION_PRESETS_FILE = CONFIG_DIR / "automation_presets.json"

DEFAULT_ADMIN_USERNAME = "nugep"
DEFAULT_ADMIN_PASSWORD = "nugep123"

ANIMAIS = [
    "Águia","Boto","Capivara","Doninha","Ema","Falcão","Gavião","Harpia","Irara","Jaguar",
    "Lontra","Mico","Onça","Paca","Quati","Raposa","Tamanduá","Urubu","Veado","Zorrilho",
    "Arara","Bugio","Caititu","Jaguatirica","Lobo","Mutum","Pirarucu","Tucano","Sucuri","Tatu"
]
ADJETIVOS = [
    "Azul","Bravo","Calmo","Dourado","Esperto","Feroz","Gracioso","Intenso","Jovial","Lento",
    "Mágico","Nobre","Ousado","Preciso","Rápido","Sábio","Tímido","Único","Valente","Zeloso",
    "Curioso","Furtivo","Altivo","Sereno","Vibrante","Audaz","Brilhante","Corajoso","Distinto","Elegante"
]

ENTITY_COLOR_MAP = {
    "material": "#6ee7b7",
    "técnica": "#9fdcff",
    "tema": "#f9a8d4",
    "período": "#fcd34d",
    "lugar": "#c7b0ff",
    "iconografia": "#fdba74",
    "conceito": "#cbd5e1",
    "pessoa": "#fda4af",
}

CSS_BLOCK = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');
*{font-family:'Inter',sans-serif!important}
:root{
    --bg-0:#050816;
    --bg-1:#091224;
    --bg-2:#0f1f35;
    --glass:rgba(255,255,255,.12);
    --glass-2:rgba(255,255,255,.18);
    --line:rgba(255,255,255,.16);
    --text:#f5f7fb;
    --muted:rgba(245,247,251,.72);
    --brand:#9fdcff;
    --brand-2:#c7b0ff;
    --ok:#6ee7b7;
    --warn:#fcd34d;
    --danger:#fca5a5;
}
.stApp{
    background:
        radial-gradient(circle at 20% 20%, rgba(77,140,255,.12), transparent 30%),
        radial-gradient(circle at 80% 10%, rgba(199,176,255,.12), transparent 28%),
        radial-gradient(circle at 40% 80%, rgba(0,214,201,.10), transparent 30%),
        linear-gradient(135deg, var(--bg-0) 0%, var(--bg-1) 55%, var(--bg-2) 100%);
    color:var(--text);
}
#MainMenu, header, footer {visibility:hidden;}
.stDeployButton{display:none;}
[data-testid="stSidebar"]{display:none;}
.block-container{padding-top:1.4rem;padding-bottom:3rem;max-width:1550px;}
.top-shell{
    background:linear-gradient(180deg, rgba(255,255,255,.14), rgba(255,255,255,.08));
    border:1px solid rgba(255,255,255,.16);
    box-shadow:0 20px 80px rgba(0,0,0,.25);
    backdrop-filter:blur(18px);
    border-radius:26px;
    padding:1.2rem 1.4rem;
    margin-bottom:1.2rem;
}
.hero-title{
    font-size:2.8rem;
    font-weight:900;
    letter-spacing:-0.04em;
    line-height:1.02;
    color:white;
}
.hero-subtitle{
    color:var(--muted);
    font-size:1.05rem;
    line-height:1.75;
    margin-top:.45rem;
}
.pill{
    display:inline-flex;
    align-items:center;
    gap:.45rem;
    background:rgba(255,255,255,.1);
    border:1px solid rgba(255,255,255,.16);
    border-radius:999px;
    padding:.42rem .85rem;
    color:white;
    font-size:.82rem;
    font-weight:700;
    margin:.2rem .28rem .2rem 0;
}
.panel{
    background:linear-gradient(180deg, rgba(255,255,255,.12), rgba(255,255,255,.06));
    border:1px solid rgba(255,255,255,.14);
    border-radius:24px;
    padding:1.2rem 1.25rem;
    box-shadow:0 14px 50px rgba(0,0,0,.20);
    margin-bottom:1rem;
}
.metric-shell{
    background:linear-gradient(180deg, rgba(255,255,255,.14), rgba(255,255,255,.08));
    border:1px solid rgba(255,255,255,.16);
    border-radius:20px;
    padding:1rem 1rem .9rem;
    min-height:134px;
    box-shadow:0 10px 35px rgba(0,0,0,.16);
}
.metric-label{
    color:rgba(255,255,255,.74);
    text-transform:uppercase;
    letter-spacing:.12em;
    font-size:.72rem;
    font-weight:800;
}
.metric-value{
    color:white;
    font-size:2rem;
    font-weight:900;
    margin-top:.45rem;
    letter-spacing:-0.03em;
}
.metric-note{
    color:rgba(255,255,255,.60);
    font-size:.82rem;
    margin-top:.32rem;
    line-height:1.5;
}
.note{
    background:rgba(159,220,255,.10);
    border:1px solid rgba(159,220,255,.18);
    border-left:4px solid rgba(159,220,255,.65);
    padding:.9rem 1rem;
    border-radius:16px;
    color:var(--text);
    line-height:1.72;
    font-size:.94rem;
}
.note strong{color:#cfeeff}
.work-card{
    background:linear-gradient(180deg, rgba(255,255,255,.12), rgba(255,255,255,.06));
    border:1px solid rgba(255,255,255,.14);
    border-radius:22px;
    overflow:hidden;
    box-shadow:0 18px 50px rgba(0,0,0,.20);
    height:100%;
}
.work-card img{
    width:100%;
    height:280px;
    object-fit:cover;
}
.work-body{padding:1rem 1rem 1.1rem}
.work-title{
    color:white;
    font-weight:800;
    font-size:1.08rem;
    line-height:1.35;
}
.work-meta{
    color:rgba(255,255,255,.68);
    font-size:.86rem;
    margin-top:.35rem;
    line-height:1.5;
}
.section-title{
    color:white;
    font-size:1.28rem;
    font-weight:900;
    letter-spacing:-0.02em;
    margin-bottom:.8rem;
}
.small-muted{color:rgba(255,255,255,.62);font-size:.84rem;line-height:1.6}
.tag-chip{
    display:inline-flex;
    align-items:center;
    gap:.35rem;
    background:rgba(255,255,255,.10);
    border:1px solid rgba(255,255,255,.14);
    border-radius:999px;
    color:white;
    font-weight:700;
    font-size:.79rem;
    padding:.36rem .75rem;
    margin:.18rem .22rem .18rem 0;
}
.tag-chip.blue{background:rgba(96,165,250,.16);border-color:rgba(96,165,250,.22)}
.tag-chip.green{background:rgba(110,231,183,.16);border-color:rgba(110,231,183,.22)}
.tag-chip.amber{background:rgba(252,211,77,.16);border-color:rgba(252,211,77,.22)}
.tag-chip.pink{background:rgba(244,114,182,.14);border-color:rgba(244,114,182,.20)}
.entity-line{
    display:flex;
    align-items:flex-start;
    justify-content:space-between;
    gap:12px;
    border:1px solid rgba(255,255,255,.08);
    background:rgba(255,255,255,.04);
    border-radius:16px;
    padding:.85rem .95rem;
    margin-bottom:.55rem;
}
.entity-left{
    display:flex;
    flex-direction:column;
    gap:.25rem;
}
.entity-title{color:white;font-weight:800;font-size:.95rem}
.entity-sub{color:rgba(255,255,255,.65);font-size:.81rem;line-height:1.55}
.conf{
    min-width:95px;
    text-align:right;
    color:#dff6ff;
    font-weight:800;
}
.table-note{color:rgba(255,255,255,.56);font-size:.8rem;margin-top:.45rem}
.divider{
    height:1px;
    background:linear-gradient(90deg, transparent, rgba(255,255,255,.16), transparent);
    margin:1.1rem 0 1rem;
}
.stTabs [data-baseweb="tab-list"]{
    gap:.5rem;
    background:rgba(255,255,255,.06);
    border:1px solid rgba(255,255,255,.10);
    padding:.35rem;
    border-radius:16px;
}
.stTabs [data-baseweb="tab"]{
    background:transparent;
    border-radius:12px;
    border:1px solid transparent;
    color:white;
    font-weight:700;
    min-height:46px;
}
.stTabs [aria-selected="true"]{
    background:rgba(255,255,255,.12)!important;
    border:1px solid rgba(255,255,255,.14)!important;
}
.stButton>button, .stDownloadButton>button{
    border-radius:14px!important;
    border:1px solid rgba(255,255,255,.16)!important;
    background:linear-gradient(180deg, rgba(255,255,255,.16), rgba(255,255,255,.08))!important;
    color:white!important;
    font-weight:800!important;
    box-shadow:0 10px 30px rgba(0,0,0,.16)!important;
}
.stTextInput input, .stTextArea textarea, .stSelectbox select, .stMultiSelect div[data-baseweb="select"]{
    background:rgba(255,255,255,.08)!important;
    color:white!important;
    border-radius:14px!important;
    border:1px solid rgba(255,255,255,.14)!important;
}
.stNumberInput input{
    background:rgba(255,255,255,.08)!important;
    color:white!important;
    border-radius:14px!important;
    border:1px solid rgba(255,255,255,.14)!important;
}
label, .stMarkdown, p, li, .stCaption {color:white!important}
div[data-testid="stMetric"]{
    background:linear-gradient(180deg, rgba(255,255,255,.12), rgba(255,255,255,.06));
    border:1px solid rgba(255,255,255,.14);
    border-radius:18px;
    padding:.7rem .8rem;
}
div[data-testid="stMetric"] label{font-weight:800!important}
div[data-testid="stDataFrame"], div[data-testid="stTable"]{
    border:1px solid rgba(255,255,255,.10);
    border-radius:16px;
    overflow:hidden;
}
@media(max-width:900px){
    .hero-title{font-size:2.1rem}
}
</style>
"""

DEFAULT_WORKS = [
    {
        "id": 1,
        "titulo": "Guernica",
        "artista": "Pablo Picasso",
        "ano": "1937",
        "periodo": "Século XX",
        "descricao": "Pintura monumental associada à guerra, violência e memória coletiva.",
        "imagem": "https://upload.wikimedia.org/wikipedia/en/7/74/PicassoGuernica.jpg",
        "materiais": ["Tinta a óleo", "Tela"],
        "tecnicas": ["Pintura"],
        "temas": ["Guerra", "Violência", "Memória"],
        "origem": "Espanha"
    },
    {
        "id": 2,
        "titulo": "A Noite Estrelada",
        "artista": "Vincent van Gogh",
        "ano": "1889",
        "periodo": "Século XIX",
        "descricao": "Obra relacionada à paisagem, noite, céu e expressão subjetiva.",
        "imagem": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ea/Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg/1200px-Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg",
        "materiais": ["Tinta a óleo", "Tela"],
        "tecnicas": ["Óleo sobre tela"],
        "temas": ["Paisagem", "Noite", "Natureza"],
        "origem": "França"
    },
    {
        "id": 3,
        "titulo": "Mona Lisa",
        "artista": "Leonardo da Vinci",
        "ano": "1503",
        "periodo": "Renascimento",
        "descricao": "Retrato célebre ligado a figuração, retrato, olhar e história da arte.",
        "imagem": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ec/Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_retouched.jpg/800px-Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_retouched.jpg",
        "materiais": ["Tinta a óleo", "Madeira"],
        "tecnicas": ["Óleo sobre madeira"],
        "temas": ["Retrato", "Figura Humana", "História da Arte"],
        "origem": "Itália"
    },
]

DEFAULT_AUTOMATION_PRESETS = {
    "daily_reconcile": {
        "name": "Reconciliar conceitos diariamente",
        "description": "Agrupa variantes, gera relações e atualiza conceitos sugeridos.",
        "cron": "0 2 * * *",
        "enabled": True,
    },
    "weekly_training": {
        "name": "Treinar classificador semanalmente",
        "description": "Usa validações humanas acumuladas para reentreinar o classificador.",
        "cron": "0 3 * * 1",
        "enabled": True,
    },
    "weekly_gap_report": {
        "name": "Gerar relatório de lacunas",
        "description": "Lista tags sem conceito reconciliado e potenciais conflitos vocabulares.",
        "cron": "30 3 * * 1",
        "enabled": True,
    },
}

# ======================================================================================
# INFRAESTRUTURA BÁSICA
# ======================================================================================

def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def ensure_app_dirs() -> None:
    ensure_dir(DATA_DIR)
    ensure_dir(EXPORT_DIR)
    ensure_dir(CONFIG_DIR)


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def now_display() -> str:
    return datetime.now().strftime("%d/%m/%Y %H:%M")


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


def append_json_record(path: Path, record: Dict[str, Any]) -> None:
    data = load_json(path, [])
    data.append(record)
    save_json(path, data)


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def generate_uid() -> str:
    return base64.urlsafe_b64encode(os.urandom(12)).decode("ascii").rstrip("=")


def generate_animal_name() -> str:
    return f"{random.choice(ANIMAIS)} {random.choice(ADJETIVOS)}"


def seed_admin_if_needed() -> None:
    admins = load_json(ADMIN_FILE, [])
    if admins:
        return
    admins = [{
        "id": 1,
        "username": DEFAULT_ADMIN_USERNAME,
        "password_hash": hash_password(DEFAULT_ADMIN_PASSWORD),
        "role": "superadmin",
        "created_at": now_iso(),
    }]
    save_json(ADMIN_FILE, admins)


def seed_works_if_needed() -> None:
    obras = load_json(OBRAS_FILE, [])
    if not obras:
        save_json(OBRAS_FILE, DEFAULT_WORKS)


def seed_automation_presets_if_needed() -> None:
    presets = load_json(AUTOMATION_PRESETS_FILE, {})
    if not presets:
        save_json(AUTOMATION_PRESETS_FILE, DEFAULT_AUTOMATION_PRESETS)


def load_obras() -> List[Dict[str, Any]]:
    return load_json(OBRAS_FILE, DEFAULT_WORKS)


def save_obras(obras: List[Dict[str, Any]]) -> None:
    save_json(OBRAS_FILE, obras)


def load_tags_df() -> pd.DataFrame:
    data = load_json(TAGS_FILE, [])
    return pd.DataFrame(data) if data else pd.DataFrame()


def save_tag_record(record: Dict[str, Any]) -> None:
    append_json_record(TAGS_FILE, record)


def load_users_df() -> pd.DataFrame:
    data = load_json(USERS_FILE, [])
    return pd.DataFrame(data) if data else pd.DataFrame()


def save_user_record(record: Dict[str, Any]) -> None:
    users = load_json(USERS_FILE, [])
    existing = {u["user_id"]: u for u in users if "user_id" in u}
    existing[record["user_id"]] = record
    save_json(USERS_FILE, list(existing.values()))


def load_feedback_df() -> pd.DataFrame:
    data = load_json(FEEDBACK_FILE, [])
    return pd.DataFrame(data) if data else pd.DataFrame()


def save_feedback_record(record: Dict[str, Any]) -> None:
    append_json_record(FEEDBACK_FILE, record)


def log_event(kind: str, payload: Dict[str, Any]) -> None:
    append_json_record(EVENTS_FILE, {
        "id": generate_uid(),
        "kind": kind,
        "payload": payload,
        "timestamp": now_iso(),
    })


def load_admins() -> List[Dict[str, Any]]:
    return load_json(ADMIN_FILE, [])


def authenticate_admin(username: str, password: str) -> bool:
    for admin in load_admins():
        if admin.get("username") == username and admin.get("password_hash") == hash_password(password):
            return True
    return False


def get_admin_role(username: str) -> str:
    for admin in load_admins():
        if admin.get("username") == username:
            return admin.get("role", "admin")
    return "admin"


def bootstrap_system() -> SemanticKnowledgeBase:
    ensure_app_dirs()
    seed_admin_if_needed()
    seed_works_if_needed()
    seed_automation_presets_if_needed()
    kb = SemanticKnowledgeBase(DATA_DIR)
    if not kb.concept_store:
        bootstrap_default_concepts(kb)
    kb.train_entity_classifier()
    return kb


KB = bootstrap_system()

# ======================================================================================
# HELPERS DE APRESENTAÇÃO
# ======================================================================================

def inject_css() -> None:
    st.markdown(CSS_BLOCK, unsafe_allow_html=True)


def hero() -> None:
    st.markdown(
        f"""
        <div class='top-shell'>
            <div class='hero-title'>{APP_TITLE}</div>
            <div class='hero-subtitle'>{APP_SUBTITLE}</div>
            <div style='margin-top:.9rem'>
                <span class='pill'>🧩 folksonomia assistida semanticamente</span>
                <span class='pill'>🧠 aprendizado incremental</span>
                <span class='pill'>🕸️ grafo folksonômico</span>
                <span class='pill'>🛠️ validação curatorial</span>
                <span class='pill'>⚙️ automação do pipeline</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_title(text: str, caption: str = "") -> None:
    block = f"<div class='section-title'>{text}</div>"
    if caption:
        block += f"<div class='small-muted'>{caption}</div>"
    st.markdown(block, unsafe_allow_html=True)


def metric_card(label: str, value: Any, note: str = "") -> str:
    return f"""
    <div class='metric-shell'>
        <div class='metric-label'>{label}</div>
        <div class='metric-value'>{value}</div>
        <div class='metric-note'>{note}</div>
    </div>
    """


def note_box(text: str) -> None:
    st.markdown(f"<div class='note'>{text}</div>", unsafe_allow_html=True)


def divider() -> None:
    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)


def render_tag_chips(tags: List[str], cls: str = "blue") -> str:
    if not tags:
        return "<span class='small-muted'>Sem dados</span>"
    return "".join([f"<span class='tag-chip {cls}'>{t}</span>" for t in tags])


def color_for_entity(entity_type: str) -> str:
    return ENTITY_COLOR_MAP.get(entity_type, "#cbd5e1")


def confidence_label(value: float) -> str:
    if value >= 0.90:
        return "muito alta"
    if value >= 0.75:
        return "alta"
    if value >= 0.55:
        return "média"
    return "baixa"


def df_to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


# ======================================================================================
# SESSÃO E ESTADO
# ======================================================================================

def init_session_state() -> None:
    defaults = {
        "user_id": generate_uid(),
        "animal_name": generate_animal_name(),
        "step": "questionnaire",
        "admin_logged_in": False,
        "admin_username": "",
        "selected_work_id": None,
        "semantic_preview_text": "",
        "last_automation_result": None,
        "questionnaire_answers": {},
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def current_user_record() -> Dict[str, Any]:
    users_df = load_users_df()
    if users_df.empty or st.session_state["user_id"] not in users_df.get("user_id", []).tolist():
        return {}
    row = users_df[users_df["user_id"] == st.session_state["user_id"]].iloc[0]
    return row.to_dict()


# ======================================================================================
# FUNÇÕES DE DADOS DERIVADOS
# ======================================================================================

def build_obras_df() -> pd.DataFrame:
    obras = load_obras()
    return pd.DataFrame(obras) if obras else pd.DataFrame()


def normalize_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(v) for v in value if str(v).strip()]
    if isinstance(value, str) and value.strip():
        return [v.strip() for v in value.split(",") if v.strip()]
    return []


def enrich_tags_df(tags_df: pd.DataFrame) -> pd.DataFrame:
    if tags_df.empty:
        return tags_df
    df = tags_df.copy()
    if "timestamp" in df.columns:
        df["timestamp_dt"] = pd.to_datetime(df["timestamp"], errors="coerce")
        df["date"] = df["timestamp_dt"].dt.date
        df["month"] = df["timestamp_dt"].dt.to_period("M").astype(str)
        df["hour"] = df["timestamp_dt"].dt.hour
    if "tag" in df.columns:
        df["tag_normalized"] = df["tag"].astype(str).apply(normalize_text)
    if "semantic_entity_type" not in df.columns:
        suggestions = [KB.suggest_semantics(t) for t in df["tag"].fillna("").astype(str).tolist()]
        df["semantic_entity_type"] = [s.tipo_entidade for s in suggestions]
        df["semantic_concept"] = [s.conceito_sugerido for s in suggestions]
        df["semantic_confidence"] = [s.confianca for s in suggestions]
        df["semantic_ambiguous"] = [s.ambiguo for s in suggestions]
    return df


def public_metrics(tags_df: pd.DataFrame, obras_df: pd.DataFrame, users_df: pd.DataFrame) -> Dict[str, Any]:
    tags_total = len(tags_df) if not tags_df.empty else 0
    unique_tags = tags_df["tag_normalized"].nunique() if not tags_df.empty and "tag_normalized" in tags_df.columns else 0
    users_total = users_df["user_id"].nunique() if not users_df.empty and "user_id" in users_df.columns else 0
    works_with_tags = tags_df["obra_id"].nunique() if not tags_df.empty and "obra_id" in tags_df.columns else 0
    ttr = round(unique_tags / tags_total, 4) if tags_total else 0.0
    return {
        "tags_total": tags_total,
        "unique_tags": unique_tags,
        "users_total": users_total,
        "works_total": len(obras_df),
        "works_with_tags": works_with_tags,
        "ttr": ttr,
    }


def top_tags(tags_df: pd.DataFrame, n: int = 15) -> pd.DataFrame:
    if tags_df.empty:
        return pd.DataFrame(columns=["tag", "count"])
    vc = tags_df["tag_normalized"].value_counts().head(n).reset_index()
    vc.columns = ["tag", "count"]
    return vc


def top_concepts(tags_df: pd.DataFrame, n: int = 15) -> pd.DataFrame:
    if tags_df.empty or "semantic_concept" not in tags_df.columns:
        return pd.DataFrame(columns=["concept", "count"])
    vc = tags_df["semantic_concept"].fillna("").astype(str)
    vc = vc[vc.str.strip() != ""].value_counts().head(n).reset_index()
    vc.columns = ["concept", "count"]
    return vc


def work_tags(tags_df: pd.DataFrame, obra_id: int) -> pd.DataFrame:
    if tags_df.empty:
        return pd.DataFrame()
    return tags_df[tags_df["obra_id"] == obra_id].copy()


def work_by_id(obra_id: int) -> Dict[str, Any]:
    for obra in load_obras():
        if int(obra["id"]) == int(obra_id):
            return obra
    return {}


def user_tags(tags_df: pd.DataFrame, user_id: str) -> pd.DataFrame:
    if tags_df.empty:
        return pd.DataFrame()
    return tags_df[tags_df["user_id"] == user_id].copy()


def pending_validation_df(tags_df: pd.DataFrame) -> pd.DataFrame:
    if tags_df.empty:
        return pd.DataFrame()
    df = tags_df.copy()
    if "validated" not in df.columns:
        df["validated"] = False
    return df[df["validated"] != True].copy()


def validated_df(tags_df: pd.DataFrame) -> pd.DataFrame:
    if tags_df.empty:
        return pd.DataFrame()
    if "validated" not in tags_df.columns:
        return pd.DataFrame(columns=tags_df.columns)
    return tags_df[tags_df["validated"] == True].copy()


def lexical_diversity_by_work(tags_df: pd.DataFrame) -> pd.DataFrame:
    if tags_df.empty:
        return pd.DataFrame(columns=["obra_id", "tags_total", "tags_unicas", "ttr"])
    grouped = tags_df.groupby("obra_id").agg(
        tags_total=("tag_normalized", "count"),
        tags_unicas=("tag_normalized", "nunique"),
    ).reset_index()
    grouped["ttr"] = (grouped["tags_unicas"] / grouped["tags_total"]).round(4)
    return grouped.sort_values(["ttr", "tags_total"], ascending=[False, False])


def semantic_distribution(tags_df: pd.DataFrame) -> pd.DataFrame:
    if tags_df.empty:
        return pd.DataFrame(columns=["entity_type", "count"])
    vc = tags_df["semantic_entity_type"].fillna("conceito").value_counts().reset_index()
    vc.columns = ["entity_type", "count"]
    return vc


def ambiguity_report(tags_df: pd.DataFrame) -> pd.DataFrame:
    if tags_df.empty:
        return pd.DataFrame(columns=["tag", "concept", "confidence", "ambiguous"])
    df = tags_df.copy()
    return df[df["semantic_ambiguous"] == True][[
        "tag", "semantic_concept", "semantic_confidence", "obra_id", "timestamp"
    ]].rename(columns={
        "semantic_concept": "concept",
        "semantic_confidence": "confidence",
    })


def cooccurrence_matrix(tags_df: pd.DataFrame, min_count: int = 2) -> pd.DataFrame:
    if tags_df.empty:
        return pd.DataFrame()
    work_to_tags = defaultdict(set)
    for _, row in tags_df.iterrows():
        work_to_tags[int(row["obra_id"])].add(row["tag_normalized"])
    tag_counter = Counter([tag for tags in work_to_tags.values() for tag in tags])
    kept_tags = {tag for tag, count in tag_counter.items() if count >= min_count}
    if not kept_tags:
        return pd.DataFrame()
    kept_tags = sorted(kept_tags)
    matrix = pd.DataFrame(0, index=kept_tags, columns=kept_tags)
    for tags in work_to_tags.values():
        tags = sorted([t for t in tags if t in kept_tags])
        for i, a in enumerate(tags):
            for b in tags[i:]:
                matrix.loc[a, b] += 1
                if a != b:
                    matrix.loc[b, a] += 1
    return matrix


def concept_alignment_report(tags_df: pd.DataFrame) -> pd.DataFrame:
    if tags_df.empty:
        return pd.DataFrame(columns=["tag", "concept", "entity_type", "confidence"])
    df = tags_df[["tag", "semantic_concept", "semantic_entity_type", "semantic_confidence"]].copy()
    df.columns = ["tag", "concept", "entity_type", "confidence"]
    return df.sort_values(["confidence", "tag"], ascending=[False, True])


def latest_automation_log_df() -> pd.DataFrame:
    logs = KB.automation_log
    return pd.DataFrame(logs) if logs else pd.DataFrame()


def export_snapshot(tags_df: pd.DataFrame, users_df: pd.DataFrame, obras_df: pd.DataFrame) -> Dict[str, Path]:
    ensure_dir(EXPORT_DIR)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    paths = {
        "tags_csv": EXPORT_DIR / f"tags_snapshot_{ts}.csv",
        "users_csv": EXPORT_DIR / f"users_snapshot_{ts}.csv",
        "works_csv": EXPORT_DIR / f"works_snapshot_{ts}.csv",
        "semantic_json": EXPORT_DIR / f"semantic_snapshot_{ts}.json",
    }
    tags_df.to_csv(paths["tags_csv"], index=False)
    users_df.to_csv(paths["users_csv"], index=False)
    obras_df.to_csv(paths["works_csv"], index=False)
    semantic_payload = {
        "concepts": KB.concept_store,
        "relations": KB.relation_store,
        "validations": KB.validation_store,
        "training_examples": KB.learning_examples,
        "exported_at": now_iso(),
    }
    save_json(paths["semantic_json"], semantic_payload)
    return paths


def cron_script_text() -> str:
    presets = load_json(AUTOMATION_PRESETS_FILE, DEFAULT_AUTOMATION_PRESETS)
    lines = [
        "#!/usr/bin/env bash",
        "# Script de referência para automatizar o pipeline local do protótipo.",
        "# Ajuste o caminho do Python e do projeto conforme o ambiente.",
        "",
        "PROJECT_DIR=\"$(cd \"$(dirname \"$0\")\" && pwd)\"",
        "cd \"$PROJECT_DIR\" || exit 1",
        "",
        "# Reconciliar conceitos / relações",
        f"echo \"{presets['daily_reconcile']['cron']} python automation_pipeline.py --mode reconcile\"",
        "",
        "# Treinar classificador",
        f"echo \"{presets['weekly_training']['cron']} python automation_pipeline.py --mode train\"",
        "",
        "# Gerar relatório de lacunas",
        f"echo \"{presets['weekly_gap_report']['cron']} python automation_pipeline.py --mode report\"",
        "",
        "echo \"Copie as linhas acima para o crontab do servidor se desejar automação externa.\"",
    ]
    return "\n".join(lines)


# ======================================================================================
# QUESTIONÁRIO E ACESSO PÚBLICO
# ======================================================================================

def render_questionnaire() -> None:
    hero()
    section_title("Questionário de entrada", "A plataforma libera a área pública após o preenchimento inicial.")
    note_box(
        "O código original tinha um questionário de acesso, mas agora ele foi ampliado para capturar sinais "
        "de repertório, interesse temático e abertura à participação semântica."
    )
    with st.form("entry_questionnaire"):
        c1, c2 = st.columns(2)
        with c1:
            q1 = st.selectbox(
                "1. Qual é o seu nível de familiaridade com museus?",
                ["Nunca visito museus", "Visito raramente", "Visito ocasionalmente", "Visito frequentemente"],
            )
            q2 = st.selectbox(
                "2. Você já ouviu falar sobre documentação museológica?",
                ["Nunca ouvi falar", "Já ouvi, mas não sei o que é", "Tenho uma ideia básica", "Conheço bem o tema"],
            )
            q3 = st.selectbox(
                "3. Como você costuma descrever uma obra?",
                ["Mais pelo sentimento", "Mais pelo tema", "Mais pela técnica/material", "Misturo várias formas"],
            )
        with c2:
            q4 = st.text_area(
                "4. O que você entende por tags aplicadas a acervos?",
                placeholder="Descreva sua compreensão livremente...",
                height=160,
                max_chars=700,
            )
            q5 = st.text_area(
                "5. Que tipo de conexão você gostaria de descobrir entre obras?",
                placeholder="Ex.: temas, técnicas, materiais, períodos, emoções, lugares...",
                height=140,
                max_chars=600,
            )
        submitted = st.form_submit_button("Liberar acesso à plataforma", use_container_width=True)
        if submitted:
            if not q4.strip():
                st.error("Preencha ao menos a questão aberta principal para seguir.")
                return
            record = {
                "user_id": st.session_state["user_id"],
                "animal_name": st.session_state["animal_name"],
                "timestamp": now_iso(),
                "q1": q1,
                "q2": q2,
                "q3": q3,
                "q4": q4,
                "q5": q5,
            }
            save_user_record(record)
            st.session_state["questionnaire_answers"] = record
            st.session_state["step"] = "public"
            log_event("questionnaire_completed", {"user_id": st.session_state["user_id"]})
            st.success("Acesso liberado. Você já pode explorar, marcar e ajudar o sistema a aprender.")
            st.rerun()


# ======================================================================================
# COMPONENTES PÚBLICOS
# ======================================================================================

def render_public_metrics(tags_df: pd.DataFrame, obras_df: pd.DataFrame, users_df: pd.DataFrame) -> None:
    metrics = public_metrics(tags_df, obras_df, users_df)
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    blocks = [
        ("tags registradas", metrics["tags_total"], "volume de marcações colaborativas"),
        ("tags únicas", metrics["unique_tags"], "vocabulário social distinto"),
        ("participantes", metrics["users_total"], "usuários que passaram pelo questionário"),
        ("obras", metrics["works_total"], "itens no protótipo"),
        ("obras com tags", metrics["works_with_tags"], "itens já atravessados pelo público"),
        ("riqueza lexical", f"{metrics['ttr']:.2%}", "type-token ratio"),
    ]
    for col, (label, value, note) in zip([c1, c2, c3, c4, c5, c6], blocks):
        with col:
            st.markdown(metric_card(label, value, note), unsafe_allow_html=True)


def render_public_home(tags_df: pd.DataFrame, obras_df: pd.DataFrame, users_df: pd.DataFrame) -> None:
    hero()
    render_public_metrics(tags_df, obras_df, users_df)
    divider()
    note_box(
        "A lógica do documento foi incorporada aqui de forma direta: a tag do visitante continua livre, "
        "mas o sistema agora produz uma camada interpretativa acima dela, com sugestão de conceito, "
        "tipo de entidade, termos relacionados e taxa de ambiguidade."
    )


def work_filter_ui(obras_df: pd.DataFrame) -> Tuple[str, str, str]:
    c1, c2, c3 = st.columns([1.5, 1.1, 1.2])
    with c1:
        search = st.text_input("Buscar obra, artista ou tema", placeholder="Ex.: guerra, retrato, Van Gogh")
    with c2:
        period = st.selectbox("Período", ["Todos"] + sorted(obras_df["periodo"].fillna("Não informado").unique().tolist() if not obras_df.empty else ["Todos"]))
    with c3:
        origem = st.selectbox("Origem", ["Todas"] + sorted(obras_df["origem"].fillna("Não informada").unique().tolist() if not obras_df.empty else ["Todas"]))
    return search, period, origem


def filter_obras(obras_df: pd.DataFrame, search: str, period: str, origem: str) -> pd.DataFrame:
    if obras_df.empty:
        return obras_df
    df = obras_df.copy()
    if search.strip():
        s = normalize_text(search)
        mask = (
            df["titulo"].fillna("").astype(str).apply(normalize_text).str.contains(s) |
            df["artista"].fillna("").astype(str).apply(normalize_text).str.contains(s) |
            df["descricao"].fillna("").astype(str).apply(normalize_text).str.contains(s) |
            df["periodo"].fillna("").astype(str).apply(normalize_text).str.contains(s) |
            df["origem"].fillna("").astype(str).apply(normalize_text).str.contains(s)
        )
        df = df[mask]
    if period != "Todos":
        df = df[df["periodo"].fillna("") == period]
    if origem != "Todas":
        df = df[df["origem"].fillna("") == origem]
    return df


def render_work_grid(obras_df: pd.DataFrame, tags_df: pd.DataFrame) -> None:
    section_title("Explorar obras", "O visitante pode observar a obra, inserir tags, justificar sua leitura e ver a camada semântica sugerida.")
    search, period, origem = work_filter_ui(obras_df)
    filtered = filter_obras(obras_df, search, period, origem)
    st.caption(f"{len(filtered)} obra(s) exibida(s).")
    if filtered.empty:
        st.info("Nenhuma obra encontrada com esses filtros.")
        return

    cols = st.columns(3)
    for i, (_, obra) in enumerate(filtered.iterrows()):
        with cols[i % 3]:
            obra_tags = work_tags(tags_df, int(obra["id"]))
            work_count = len(obra_tags)
            unique_count = obra_tags["tag_normalized"].nunique() if not obra_tags.empty else 0
            st.markdown(
                f"""
                <div class='work-card'>
                    <img src='{obra["imagem"]}' alt='{obra["titulo"]}' />
                    <div class='work-body'>
                        <div class='work-title'>{obra["titulo"]}</div>
                        <div class='work-meta'>{obra["artista"]} · {obra["ano"]} · {obra.get("origem","")}</div>
                        <div class='work-meta' style='margin-top:.55rem'>{obra.get("descricao","")}</div>
                        <div style='margin-top:.8rem'>
                            <span class='tag-chip blue'>{work_count} tags</span>
                            <span class='tag-chip green'>{unique_count} únicas</span>
                            <span class='tag-chip amber'>{obra.get("periodo","")}</span>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("Abrir obra", key=f"open_work_{obra['id']}", use_container_width=True):
                st.session_state["selected_work_id"] = int(obra["id"])
                st.rerun()


def render_work_detail(tags_df: pd.DataFrame) -> None:
    selected = st.session_state.get("selected_work_id")
    if not selected:
        return
    obra = work_by_id(selected)
    if not obra:
        return
    obra_tags_df = work_tags(tags_df, selected)

    divider()
    section_title(f"Obra #{obra['id']} · {obra['titulo']}", "Entrada de tags, justificativa e leitura semântica da contribuição.")
    c1, c2 = st.columns([1.2, 1.1])
    with c1:
        st.image(obra["imagem"], use_container_width=True)
        st.markdown(f"**Artista:** {obra['artista']}")
        st.markdown(f"**Ano:** {obra['ano']}")
        st.markdown(f"**Período:** {obra.get('periodo','Não informado')}")
        st.markdown(f"**Origem:** {obra.get('origem','Não informada')}")
        st.markdown(f"**Descrição:** {obra.get('descricao','')}")
        st.markdown("**Materiais institucionais:**")
        st.markdown(render_tag_chips(normalize_list(obra.get("materiais")), "green"), unsafe_allow_html=True)
        st.markdown("**Técnicas institucionais:**")
        st.markdown(render_tag_chips(normalize_list(obra.get("tecnicas")), "blue"), unsafe_allow_html=True)
        st.markdown("**Temas institucionais:**")
        st.markdown(render_tag_chips(normalize_list(obra.get("temas")), "pink"), unsafe_allow_html=True)
    with c2:
        render_tag_submission_form(obra, obra_tags_df)
        divider()
        render_work_semantic_summary(obra_tags_df)
        divider()
        render_existing_tags(obra_tags_df)

    if st.button("Fechar obra", key="close_work_detail"):
        st.session_state["selected_work_id"] = None
        st.rerun()


def render_tag_submission_form(obra: Dict[str, Any], obra_tags_df: pd.DataFrame) -> None:
    section_title("Contribuir com uma tag", "A tag permanece livre. A camada semântica é apenas uma interpretação assistiva.")
    preview_text = st.text_input(
        "Digite sua tag",
        value=st.session_state.get("semantic_preview_text", ""),
        placeholder="Ex.: devoção, ouro, barroco, mulher, retrato, Rio de Janeiro...",
        key=f"input_tag_{obra['id']}",
    )
    st.session_state["semantic_preview_text"] = preview_text

    suggestion = KB.suggest_semantics(preview_text) if preview_text.strip() else None
    if suggestion:
        st.markdown(
            f"""
            <div class='entity-line'>
                <div class='entity-left'>
                    <div class='entity-title'>Leitura semântica sugerida</div>
                    <div class='entity-sub'>
                        <strong>Tipo:</strong> {suggestion.tipo_entidade} ·
                        <strong>Conceito sugerido:</strong> {suggestion.conceito_sugerido or "—"}<br>
                        <strong>Interpretação:</strong> {suggestion.justificativa}<br>
                        <strong>Ambiguidade:</strong> {"sim" if suggestion.ambiguo else "não"}
                    </div>
                </div>
                <div class='conf'>{suggestion.confianca:.0%}<br><span class='small-muted'>{confidence_label(suggestion.confianca)}</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if suggestion.relacionados:
            st.markdown("**Termos relacionados:**")
            st.markdown(render_tag_chips(suggestion.relacionados[:8], "amber"), unsafe_allow_html=True)

    with st.form(f"tag_form_{obra['id']}"):
        justificativa = st.text_area(
            "Justificativa opcional",
            placeholder="Explique por que escolheu essa tag. Isso ajuda a análise semântica e a validação curatorial.",
            height=120,
        )
        wants_suggestion = st.checkbox("Aceitar a sugestão de conceito gerada pelo sistema", value=True)
        sent = st.form_submit_button("Salvar tag", use_container_width=True)
        if sent:
            if not preview_text.strip():
                st.error("Digite uma tag antes de salvar.")
                return
            semantic = KB.suggest_semantics(preview_text)
            record = {
                "id": generate_uid(),
                "user_id": st.session_state["user_id"],
                "animal_name": st.session_state["animal_name"],
                "obra_id": int(obra["id"]),
                "tag": preview_text.strip(),
                "tag_normalized": normalize_text(preview_text),
                "justificativa": justificativa.strip(),
                "semantic_entity_type": semantic.tipo_entidade,
                "semantic_concept": semantic.conceito_sugerido if wants_suggestion else "",
                "semantic_confidence": semantic.confianca,
                "semantic_ambiguous": semantic.ambiguo,
                "semantic_why": semantic.justificativa,
                "semantic_related": semantic.relacionados,
                "validated": False,
                "timestamp": now_iso(),
            }
            save_tag_record(record)
            KB.upsert_concept(
                preferred_label=semantic.conceito_sugerido or preview_text.strip().title(),
                entity_type=semantic.tipo_entidade,
                aliases=[preview_text.strip()],
                source="submissao_publica",
            )
            log_event("tag_created", {
                "obra_id": int(obra["id"]),
                "user_id": st.session_state["user_id"],
                "tag": preview_text.strip(),
                "semantic_entity_type": semantic.tipo_entidade,
                "semantic_concept": semantic.conceito_sugerido,
            })
            st.session_state["semantic_preview_text"] = ""
            st.success("Tag registrada com sucesso. Ela entrará no fluxo de validação e aprendizado.")
            st.rerun()

    st.caption("A camada semântica não apaga a tag do usuário. Ela cria uma camada interpretativa adicional, como pede o documento.")


def render_existing_tags(obra_tags_df: pd.DataFrame) -> None:
    section_title("Tags já associadas a esta obra")
    if obra_tags_df.empty:
        st.info("Nenhuma tag foi registrada ainda para esta obra.")
        return
    top = obra_tags_df["tag_normalized"].value_counts().head(20)
    st.markdown(render_tag_chips([f"{tag} ({count})" for tag, count in top.items()], "blue"), unsafe_allow_html=True)
    display_cols = ["tag", "semantic_concept", "semantic_entity_type", "semantic_confidence", "justificativa", "timestamp"]
    disp = obra_tags_df[display_cols].copy()
    disp.columns = ["Tag", "Conceito sugerido", "Tipo", "Confiança", "Justificativa", "Data"]
    st.dataframe(disp.sort_values("Data", ascending=False), use_container_width=True, hide_index=True)


def render_work_semantic_summary(obra_tags_df: pd.DataFrame) -> None:
    section_title("Resumo semântico da obra")
    if obra_tags_df.empty:
        st.info("Sem material colaborativo suficiente ainda.")
        return
    summary = KB.semantic_summary(obra_tags_df)
    c1, c2, c3 = st.columns(3)
    with c1:
        major_entity = max(summary["entity_distribution"], key=summary["entity_distribution"].get) if summary["entity_distribution"] else "—"
        st.markdown(metric_card("tipo dominante", major_entity, "distribuição semântica das tags"), unsafe_allow_html=True)
    with c2:
        st.markdown(metric_card("ambiguidade", f"{summary['ambiguity_rate']:.1%}", "quanto maior, mais atenção curatorial"), unsafe_allow_html=True)
    with c3:
        st.markdown(metric_card("conceitos", len(summary["concept_distribution"]), "conceitos emergentes identificados"), unsafe_allow_html=True)
    st.markdown("**Conceitos mais frequentes:**")
    if summary["concept_distribution"]:
        st.markdown(render_tag_chips([f"{k} ({v})" for k, v in summary["concept_distribution"].items()], "green"), unsafe_allow_html=True)
    else:
        st.caption("Sem conceitos suficientes.")
    unresolved = summary["top_unresolved"]
    if unresolved:
        st.markdown("**Lacunas de reconciliação:**")
        st.markdown(render_tag_chips([f"{t} ({c})" for t, c in unresolved[:10]], "amber"), unsafe_allow_html=True)


def render_concept_explorer(tags_df: pd.DataFrame, obras_df: pd.DataFrame) -> None:
    section_title("Explorador semântico público", "Navegação por conceitos emergentes e distribuições aproximadas.")
    concepts = top_concepts(tags_df, n=50)
    if concepts.empty:
        st.info("Ainda não há conceitos suficientes para navegação semântica.")
        return
    selected_concept = st.selectbox("Selecione um conceito emergente", concepts["concept"].tolist())
    concept_rows = tags_df[tags_df["semantic_concept"] == selected_concept]
    c1, c2 = st.columns([1.2, 1])
    with c1:
        st.markdown("**Obras relacionadas:**")
        work_counts = concept_rows["obra_id"].value_counts().reset_index()
        work_counts.columns = ["obra_id", "count"]
        work_counts["titulo"] = work_counts["obra_id"].map(lambda x: work_by_id(int(x)).get("titulo", f"Obra {x}"))
        st.dataframe(work_counts[["titulo", "count"]], use_container_width=True, hide_index=True)
    with c2:
        st.markdown("**Tags que conduzem a este conceito:**")
        vc = concept_rows["tag_normalized"].value_counts().head(20)
        st.markdown(render_tag_chips([f"{t} ({c})" for t, c in vc.items()], "pink"), unsafe_allow_html=True)
    note_box(
        "Esta tela materializa a ideia do documento de permitir navegação por trilhas semânticas criadas pelo público, "
        "e não apenas por metadados institucionais fixos."
    )


def render_user_panel(tags_df: pd.DataFrame) -> None:
    section_title("Seu percurso", "Resumo individual de participação e riqueza vocabular.")
    utags = user_tags(tags_df, st.session_state["user_id"])
    if utags.empty:
        st.info("Você ainda não criou tags neste acesso.")
        return
    unique_tags = utags["tag_normalized"].nunique()
    ttr = unique_tags / len(utags)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(metric_card("suas tags", len(utags), "volume total de contribuições"), unsafe_allow_html=True)
    with c2:
        st.markdown(metric_card("tags únicas", unique_tags, "variedade do seu vocabulário"), unsafe_allow_html=True)
    with c3:
        st.markdown(metric_card("riqueza lexical", f"{ttr:.2%}", "diversidade em relação ao total"), unsafe_allow_html=True)
    st.dataframe(
        utags[["tag", "semantic_concept", "semantic_entity_type", "semantic_confidence", "timestamp"]]
        .sort_values("timestamp", ascending=False)
        .rename(columns={
            "tag": "Tag",
            "semantic_concept": "Conceito",
            "semantic_entity_type": "Tipo",
            "semantic_confidence": "Confiança",
            "timestamp": "Data",
        }),
        use_container_width=True,
        hide_index=True,
    )


def render_public_feedback() -> None:
    section_title("Feedback do visitante", "Canal curto para registrar percepção sobre o sistema.")
    with st.form("public_feedback_form"):
        score = st.slider("Quão útil foi a camada semântica para sua navegação?", 1, 10, 8)
        comment = st.text_area("Comentário", placeholder="O que funcionou? O que confundiu? O que você mudaria?", height=120)
        submitted = st.form_submit_button("Enviar feedback", use_container_width=True)
        if submitted:
            save_feedback_record({
                "id": generate_uid(),
                "user_id": st.session_state["user_id"],
                "animal_name": st.session_state["animal_name"],
                "score": score,
                "comment": comment.strip(),
                "timestamp": now_iso(),
            })
            st.success("Feedback registrado. Isso também ajuda o aperfeiçoamento do sistema.")


# ======================================================================================
# ÁREA ADMINISTRATIVA
# ======================================================================================

def admin_login_view() -> None:
    section_title("Área administrativa", "Login para validação, automação, análise e gestão curatorial.")
    with st.form("admin_login_form"):
        username = st.text_input("Usuário")
        password = st.text_input("Senha", type="password")
        submitted = st.form_submit_button("Entrar", use_container_width=True)
        if submitted:
            if authenticate_admin(username, password):
                st.session_state["admin_logged_in"] = True
                st.session_state["admin_username"] = username
                log_event("admin_login", {"username": username})
                st.success("Login realizado.")
                st.rerun()
            else:
                st.error("Credenciais inválidas.")


def render_admin_overview(tags_df: pd.DataFrame, obras_df: pd.DataFrame, users_df: pd.DataFrame) -> None:
    section_title("Visão geral administrativa", "KPIs ampliados para leitura documental, semântica e participativa.")
    metrics = public_metrics(tags_df, obras_df, users_df)
    validated = validated_df(tags_df)
    pending = pending_validation_df(tags_df)
    ambiguity = ambiguity_report(tags_df)
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    blocks = [
        ("tags totais", metrics["tags_total"], "marcações livres registradas"),
        ("tags únicas", metrics["unique_tags"], "variedade lexical"),
        ("pendentes", len(pending), "aguardando validação"),
        ("validadas", len(validated), "usadas como aprendizagem supervisionada"),
        ("ambíguas", len(ambiguity), "necessitam atenção curatorial"),
        ("conceitos", len(KB.concept_store), "micro-ontologia viva"),
    ]
    for col, (label, value, note) in zip([c1, c2, c3, c4, c5, c6], blocks):
        with col:
            st.markdown(metric_card(label, value, note), unsafe_allow_html=True)

    divider()
    c1, c2 = st.columns(2)
    with c1:
        section_title("Top tags")
        st.dataframe(top_tags(tags_df, 20), use_container_width=True, hide_index=True)
    with c2:
        section_title("Top conceitos")
        st.dataframe(top_concepts(tags_df, 20), use_container_width=True, hide_index=True)

    divider()
    lexical_df = lexical_diversity_by_work(tags_df)
    if not lexical_df.empty:
        lexical_df["obra"] = lexical_df["obra_id"].map(lambda x: work_by_id(int(x)).get("titulo", f"Obra {x}"))
        st.dataframe(lexical_df[["obra", "tags_total", "tags_unicas", "ttr"]], use_container_width=True, hide_index=True)

    note_box(
        "O código original já possuía frequência, temporalidade e similaridade lexical. "
        "Agora a camada administrativa também passa a enxergar pendência de validação, ambiguidade, "
        "conceitos reconciliados e material de treino supervisionado."
    )


def render_admin_semantics(tags_df: pd.DataFrame) -> None:
    section_title("Análise semântica", "Distribuição por tipo de entidade, conceitos emergentes, lacunas e conflitos.")
    if tags_df.empty:
        st.info("Ainda não há tags para análise semântica.")
        return
    summary = KB.semantic_summary(tags_df)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(metric_card("tipos semânticos", len(summary["entity_distribution"]), "classes detectadas"), unsafe_allow_html=True)
    with c2:
        st.markdown(metric_card("conceitos frequentes", len(summary["concept_distribution"]), "conceitos mais recorrentes"), unsafe_allow_html=True)
    with c3:
        st.markdown(metric_card("taxa de ambiguidade", f"{summary['ambiguity_rate']:.2%}", "quanto maior, mais revisão"), unsafe_allow_html=True)

    divider()
    c1, c2 = st.columns(2)
    with c1:
        entity_df = semantic_distribution(tags_df)
        st.dataframe(entity_df, use_container_width=True, hide_index=True)
        if PLOTLY_AVAILABLE and not entity_df.empty:
            fig = px.pie(entity_df, names="entity_type", values="count", title="Distribuição por tipo de entidade")
            st.plotly_chart(fig, use_container_width=True)
    with c2:
        concept_df = top_concepts(tags_df, 25)
        st.dataframe(concept_df, use_container_width=True, hide_index=True)
        if PLOTLY_AVAILABLE and not concept_df.empty:
            fig = px.bar(concept_df, x="concept", y="count", title="Conceitos emergentes")
            st.plotly_chart(fig, use_container_width=True)

    divider()
    st.markdown("**Lacunas de reconciliação:**")
    unresolved = summary["top_unresolved"]
    if unresolved:
        st.markdown(render_tag_chips([f"{t} ({c})" for t, c in unresolved], "amber"), unsafe_allow_html=True)
    else:
        st.caption("Nenhuma lacuna expressiva detectada.")

    divider()
    ambiguity_df = ambiguity_report(tags_df)
    st.markdown("**Registros ambíguos:**")
    if not ambiguity_df.empty:
        st.dataframe(ambiguity_df, use_container_width=True, hide_index=True)
    else:
        st.caption("Nenhuma ambiguidade crítica no momento.")

    note_box(
        "Aqui aparece a tradução prática do documento: o sistema reconhece entidades, reconcilia conceitos, "
        "detecta ambiguidade e mostra onde o vocabulário social ainda não conversa bem com a base documental."
    )


def persist_tags_df(tags_df: pd.DataFrame) -> None:
    save_json(TAGS_FILE, tags_df.to_dict(orient="records"))


def render_validation_lab(tags_df: pd.DataFrame) -> None:
    section_title("Laboratório de validação", "Espaço de supervisão humana inspirado no mecanismo descrito no caso do Prado.")
    pending = pending_validation_df(tags_df)
    if pending.empty:
        st.success("Não há tags pendentes de validação.")
        return

    display = pending[[
        "id","obra_id","tag","semantic_concept","semantic_entity_type","semantic_confidence","semantic_ambiguous","timestamp"
    ]].copy()
    display.columns = ["id","obra","tag","conceito","tipo","confiança","ambígua","data"]
    st.dataframe(display, use_container_width=True, hide_index=True)

    selected_id = st.selectbox("Selecione uma tag pendente", display["id"].tolist())
    selected_row = pending[pending["id"] == selected_id].iloc[0].to_dict()
    obra = work_by_id(int(selected_row["obra_id"]))
    st.markdown(f"**Obra:** {obra.get('titulo','')} · **Tag:** {selected_row['tag']}")
    st.markdown(f"**Sugestão atual:** {selected_row.get('semantic_concept','')} · **Tipo:** {selected_row.get('semantic_entity_type','')} · **Confiança:** {selected_row.get('semantic_confidence',0):.0%}")
    st.markdown(f"**Justificativa do usuário:** {selected_row.get('justificativa','—')}")

    c1, c2 = st.columns(2)
    with c1:
        approved_type = st.selectbox("Tipo aprovado", ["conceito","tema","material","técnica","lugar","período","iconografia","pessoa"], index=0)
    with c2:
        approved_concept = st.text_input("Conceito aprovado", value=selected_row.get("semantic_concept","") or selected_row["tag"].title())
    notes = st.text_area("Notas curatoriais", placeholder="Explique a decisão, especialmente se houver ambiguidade ou conflito.", height=120)

    c1, c2, c3 = st.columns(3)
    with c1:
        approve = st.button("Aprovar e ensinar", use_container_width=True)
    with c2:
        reject = st.button("Marcar como ambígua", use_container_width=True)
    with c3:
        skip = st.button("Ignorar por enquanto", use_container_width=True)

    if approve:
        tags_df.loc[tags_df["id"] == selected_id, "validated"] = True
        tags_df.loc[tags_df["id"] == selected_id, "semantic_entity_type"] = approved_type
        tags_df.loc[tags_df["id"] == selected_id, "semantic_concept"] = approved_concept
        tags_df.loc[tags_df["id"] == selected_id, "semantic_ambiguous"] = False
        tags_df.loc[tags_df["id"] == selected_id, "validation_notes"] = notes
        tags_df.loc[tags_df["id"] == selected_id, "validated_by"] = st.session_state["admin_username"]
        tags_df.loc[tags_df["id"] == selected_id, "validated_at"] = now_iso()
        persist_tags_df(tags_df)
        KB.record_validation(
            tag_original=selected_row["tag"],
            tag_normalizada=normalize_text(selected_row["tag"]),
            approved_entity_type=approved_type,
            approved_concept=approved_concept,
            approved=True,
            validated_by=st.session_state["admin_username"],
            notes=notes,
        )
        KB.train_entity_classifier()
        st.success("Tag validada e enviada ao conjunto de aprendizagem.")
        st.rerun()

    if reject:
        tags_df.loc[tags_df["id"] == selected_id, "semantic_ambiguous"] = True
        tags_df.loc[tags_df["id"] == selected_id, "validation_notes"] = notes or "Marcada como ambígua"
        persist_tags_df(tags_df)
        KB.record_validation(
            tag_original=selected_row["tag"],
            tag_normalizada=normalize_text(selected_row["tag"]),
            approved_entity_type=selected_row.get("semantic_entity_type","conceito"),
            approved_concept=selected_row.get("semantic_concept",""),
            approved=False,
            validated_by=st.session_state["admin_username"],
            notes=notes or "Marcada como ambígua",
        )
        st.warning("Registro marcado como ambíguo. A tag segue disponível, mas sinalizada.")
        st.rerun()

    if skip:
        st.info("Nenhuma alteração feita.")


def render_automation_center(tags_df: pd.DataFrame, obras_df: pd.DataFrame) -> None:
    section_title("Central de automação", "Pipeline de enriquecimento, treino e geração de relatórios.")
    presets = load_json(AUTOMATION_PRESETS_FILE, DEFAULT_AUTOMATION_PRESETS)
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("Executar pipeline completo", use_container_width=True):
            result = KB.run_automation(obras_df, tags_df, admin_user=st.session_state["admin_username"])
            st.session_state["last_automation_result"] = result.__dict__
            st.success("Pipeline executado.")
            st.rerun()
    with c2:
        if st.button("Reconciliar relações agora", use_container_width=True):
            created = KB.build_tag_relations(tags_df)
            st.info(f"{len(created)} relação(ões) gerada(s).")
    with c3:
        if st.button("Treinar classificador agora", use_container_width=True):
            meta = KB.train_entity_classifier()
            st.success(f"Treino atualizado. Amostras usadas: {meta.get('samples', 0)}")

    divider()
    st.markdown("**Presets de automação:**")
    preset_df = pd.DataFrame([
        {"preset": key, **value} for key, value in presets.items()
    ])
    st.dataframe(preset_df, use_container_width=True, hide_index=True)

    divider()
    logs_df = latest_automation_log_df()
    st.markdown("**Logs recentes:**")
    if not logs_df.empty:
        st.dataframe(logs_df.sort_values("ran_at", ascending=False), use_container_width=True, hide_index=True)
    else:
        st.caption("Nenhuma execução registrada ainda.")

    divider()
    script = cron_script_text()
    st.code(script, language="bash")
    st.download_button(
        "Baixar script de automação",
        script.encode("utf-8"),
        "run_automation_reference.sh",
        "text/x-shellscript",
        use_container_width=True,
    )

    note_box(
        "Como o protótipo roda em Streamlit, a automação contínua real depende de um ambiente externo. "
        "Por isso, além dos botões internos, o sistema gera o script de referência para cron."
    )


def render_network_tab(tags_df: pd.DataFrame, obras_df: pd.DataFrame) -> None:
    section_title("Grafo folksonômico", "Relações entre obras, tags e conceitos reconciliados.")
    if tags_df.empty:
        st.info("Sem dados suficientes para montar o grafo.")
        return
    graph = KB.build_semantic_graph(obras_df, tags_df)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(metric_card("nós", len(graph["nodes"]), "obras, tags e conceitos"), unsafe_allow_html=True)
    with c2:
        st.markdown(metric_card("arestas", len(graph["edges"]), "relações documentais e semânticas"), unsafe_allow_html=True)
    with c3:
        density = len(graph["edges"]) / max(1, len(graph["nodes"]))
        st.markdown(metric_card("densidade simples", f"{density:.2f}", "arestas por nó"), unsafe_allow_html=True)

    if not NETWORKX_AVAILABLE or not PLOTLY_AVAILABLE:
        st.warning("Instale networkx e plotly para visualizar o grafo interativo.")
        st.json(graph)
        return

    G = nx.Graph()
    for node in graph["nodes"]:
        G.add_node(node["id"], **node)
    for edge in graph["edges"]:
        G.add_edge(edge["source"], edge["target"], weight=edge.get("weight", 1.0), relation=edge.get("relation", ""))

    pos = nx.spring_layout(G, seed=7, k=0.8)
    node_x, node_y, node_text, node_color, node_size = [], [], [], [], []
    for node_id, attrs in G.nodes(data=True):
        x, y = pos[node_id]
        node_x.append(x)
        node_y.append(y)
        node_text.append(f"{attrs.get('label', node_id)}<br>tipo={attrs.get('type','')}")
        node_color.append(color_for_entity(attrs.get("entity_type", attrs.get("type", "conceito"))))
        node_size.append(18 if attrs.get("type") == "obra" else 12)

    edge_x, edge_y = [], []
    for s, t in G.edges():
        x0, y0 = pos[s]
        x1, y1 = pos[t]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=edge_x, y=edge_y, mode="lines",
        line=dict(width=0.8, color="rgba(255,255,255,.28)"),
        hoverinfo="none",
    ))
    fig.add_trace(go.Scatter(
        x=node_x, y=node_y, mode="markers",
        marker=dict(size=node_size, color=node_color, line=dict(width=1, color="white")),
        text=node_text, hoverinfo="text"
    ))
    fig.update_layout(
        height=700,
        margin=dict(l=20, r=20, t=30, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Nós maiores tendem a ser obras; tags e conceitos aparecem como conectores.")

    divider()
    rel_df = pd.DataFrame(KB.relation_store)
    if not rel_df.empty:
        st.dataframe(rel_df.sort_values("confidence", ascending=False), use_container_width=True, hide_index=True)


def render_reports_tab(tags_df: pd.DataFrame, users_df: pd.DataFrame, obras_df: pd.DataFrame) -> None:
    section_title("Relatórios e cruzamentos", "Métricas de diversidade, temporalidade, coocorrência e alinhamento conceitual.")
    if tags_df.empty:
        st.info("Sem dados suficientes para relatórios.")
        return

    t1, t2, t3, t4 = st.tabs(["Temporal", "Lexical", "Coocorrência", "Alinhamento"])

    with t1:
        if "date" in tags_df.columns:
            daily = tags_df.groupby("date").agg(tags=("id","count"), unicas=("tag_normalized","nunique"), usuarios=("user_id","nunique")).reset_index()
            st.dataframe(daily, use_container_width=True, hide_index=True)
            if PLOTLY_AVAILABLE and not daily.empty:
                fig = px.line(daily, x="date", y="tags", title="Tags por dia")
                st.plotly_chart(fig, use_container_width=True)
        if "month" in tags_df.columns:
            monthly = tags_df.groupby("month").agg(tags=("id","count"), unicas=("tag_normalized","nunique")).reset_index()
            st.dataframe(monthly, use_container_width=True, hide_index=True)

    with t2:
        lexical_df = lexical_diversity_by_work(tags_df)
        lexical_df["obra"] = lexical_df["obra_id"].map(lambda x: work_by_id(int(x)).get("titulo", f"Obra {x}"))
        st.dataframe(lexical_df[["obra","tags_total","tags_unicas","ttr"]], use_container_width=True, hide_index=True)
        if PLOTLY_AVAILABLE and not lexical_df.empty:
            fig = px.bar(lexical_df, x="obra", y="ttr", title="Riqueza lexical por obra")
            st.plotly_chart(fig, use_container_width=True)

    with t3:
        matrix = cooccurrence_matrix(tags_df, min_count=2)
        if matrix.empty:
            st.info("Poucas coocorrências consistentes até o momento.")
        else:
            st.dataframe(matrix, use_container_width=True)
            if PLOTLY_AVAILABLE:
                fig = px.imshow(matrix, text_auto=True, aspect="auto", title="Matriz de coocorrência de tags")
                st.plotly_chart(fig, use_container_width=True)

    with t4:
        alignment = concept_alignment_report(tags_df)
        st.dataframe(alignment.sort_values("confidence", ascending=False), use_container_width=True, hide_index=True)
        gap_report = KB.concept_gap_report(tags_df)
        st.markdown("**Tags ainda sem boa reconciliação:**")
        st.markdown(render_tag_chips([f"{t} ({c})" for t, c in gap_report["sem_conceito"][:20]], "amber"), unsafe_allow_html=True)

    divider()
    note_box(
        "Esses relatórios ampliam as métricas pedidas no documento: não apenas frequência, mas também diversidade lexical, "
        "coocorrência, lacuna vocabular, emergência temática e pontos de conflito entre a linguagem do público e a base técnica."
    )


def render_works_management(obras_df: pd.DataFrame) -> None:
    section_title("Gestão de obras", "Cadastro, edição rápida e manutenção do corpus institucional.")
    t1, t2 = st.tabs(["Obras atuais", "Adicionar nova obra"])

    with t1:
        st.dataframe(obras_df, use_container_width=True, hide_index=True)
        remove_id = st.selectbox("Remover obra", ["Nenhuma"] + obras_df["id"].astype(int).astype(str).tolist())
        if remove_id != "Nenhuma":
            if st.button("Remover obra selecionada", use_container_width=True):
                remaining = [o for o in load_obras() if int(o["id"]) != int(remove_id)]
                save_obras(remaining)
                st.success("Obra removida.")
                st.rerun()

    with t2:
        with st.form("add_work_form"):
            c1, c2 = st.columns(2)
            with c1:
                titulo = st.text_input("Título")
                artista = st.text_input("Artista")
                ano = st.text_input("Ano")
                periodo = st.text_input("Período")
                origem = st.text_input("Origem")
            with c2:
                imagem = st.text_input("URL da imagem")
                descricao = st.text_area("Descrição", height=140)
                materiais = st.text_input("Materiais (separados por vírgula)")
                tecnicas = st.text_input("Técnicas (separadas por vírgula)")
                temas = st.text_input("Temas (separados por vírgula)")
            submitted = st.form_submit_button("Adicionar obra", use_container_width=True)
            if submitted:
                if not titulo or not artista or not imagem:
                    st.error("Preencha título, artista e imagem.")
                    return
                obras = load_obras()
                new_id = max([int(o["id"]) for o in obras], default=0) + 1
                obras.append({
                    "id": new_id,
                    "titulo": titulo,
                    "artista": artista,
                    "ano": ano,
                    "periodo": periodo,
                    "origem": origem,
                    "imagem": imagem,
                    "descricao": descricao,
                    "materiais": normalize_list(materiais),
                    "tecnicas": normalize_list(tecnicas),
                    "temas": normalize_list(temas),
                })
                save_obras(obras)
                log_event("work_added", {"id": new_id, "titulo": titulo})
                st.success("Obra adicionada.")
                st.rerun()


def render_export_center(tags_df: pd.DataFrame, users_df: pd.DataFrame, obras_df: pd.DataFrame) -> None:
    section_title("Exportação", "Arquivos CSV, JSON e snapshot semântico do protótipo.")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.download_button("Baixar tags (CSV)", df_to_csv_bytes(tags_df), "tags.csv", "text/csv", use_container_width=True)
        st.download_button("Baixar usuários (CSV)", df_to_csv_bytes(users_df), "users.csv", "text/csv", use_container_width=True)
    with c2:
        st.download_button("Baixar obras (CSV)", df_to_csv_bytes(obras_df), "works.csv", "text/csv", use_container_width=True)
        training_df = KB.export_training_dataset()
        st.download_button("Baixar treino supervisionado (CSV)", df_to_csv_bytes(training_df), "training_examples.csv", "text/csv", use_container_width=True)
    with c3:
        semantic_payload = json.dumps({
            "concepts": KB.concept_store,
            "relations": KB.relation_store,
            "validations": KB.validation_store,
            "automation_log": KB.automation_log,
        }, ensure_ascii=False, indent=2)
        st.download_button("Baixar base semântica (JSON)", semantic_payload.encode("utf-8"), "semantic_base.json", "application/json", use_container_width=True)

    if st.button("Gerar snapshot em arquivos", use_container_width=True):
        paths = export_snapshot(tags_df, users_df, obras_df)
        st.success("Snapshot gerado.")
        for label, path in paths.items():
            st.markdown(f"- {label}: `{path.name}`")


# ======================================================================================
# ROTEAMENTO PRINCIPAL
# ======================================================================================

def public_area(tags_df: pd.DataFrame, obras_df: pd.DataFrame, users_df: pd.DataFrame) -> None:
    render_public_home(tags_df, obras_df, users_df)
    tabs = st.tabs(["Explorar", "Trilhas semânticas", "Meu percurso", "Feedback", "Admin"])
    with tabs[0]:
        render_work_grid(obras_df, tags_df)
        render_work_detail(tags_df)
    with tabs[1]:
        render_concept_explorer(tags_df, obras_df)
    with tabs[2]:
        render_user_panel(tags_df)
    with tabs[3]:
        render_public_feedback()
    with tabs[4]:
        if st.session_state["admin_logged_in"]:
            admin_area(tags_df, obras_df, users_df)
        else:
            admin_login_view()


def admin_area(tags_df: pd.DataFrame, obras_df: pd.DataFrame, users_df: pd.DataFrame) -> None:
    section_title(
        f"Painel curatorial · {st.session_state['admin_username']}",
        "Validação, aprendizado supervisionado, automação e leitura analítica do sistema."
    )
    tabs = st.tabs(["Visão geral", "Semântica", "Validação", "Automação", "Grafo", "Relatórios", "Obras", "Exportação"])
    with tabs[0]:
        render_admin_overview(tags_df, obras_df, users_df)
    with tabs[1]:
        render_admin_semantics(tags_df)
    with tabs[2]:
        render_validation_lab(tags_df)
    with tabs[3]:
        render_automation_center(tags_df, obras_df)
    with tabs[4]:
        render_network_tab(tags_df, obras_df)
    with tabs[5]:
        render_reports_tab(tags_df, users_df, obras_df)
    with tabs[6]:
        render_works_management(obras_df)
    with tabs[7]:
        render_export_center(tags_df, users_df, obras_df)

    divider()
    if st.button("Sair da área administrativa", use_container_width=True):
        st.session_state["admin_logged_in"] = False
        st.session_state["admin_username"] = ""
        st.rerun()


def app_main() -> None:
    inject_css()
    init_session_state()

    obras_df = build_obras_df()
    tags_df = enrich_tags_df(load_tags_df())
    users_df = load_users_df()

    if st.session_state["step"] == "questionnaire":
        render_questionnaire()
        return

    public_area(tags_df, obras_df, users_df)


if __name__ == "__main__":
    app_main()
