from __future__ import annotations

import base64
import copy
import hashlib
import io
import json
import os
import random
import re
import unicodedata
import uuid
import zipfile
from collections import Counter, defaultdict
from datetime import datetime
from difflib import get_close_matches
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import networkx as nx
    HAS_NETWORKX = True
except ModuleNotFoundError:
    HAS_NETWORKX = False

    class SimpleGraph:
        def __init__(self):
            self._nodes = {}
            self._edges = []

        def add_node(self, node, **attrs):
            self._nodes[node] = {**self._nodes.get(node, {}), **attrs}

        def add_edge(self, source, target, **attrs):
            if not self.has_node(source):
                self.add_node(source)
            if not self.has_node(target):
                self.add_node(target)
            if not self.has_edge(source, target):
                self._edges.append((source, target, attrs))

        def has_edge(self, source, target):
            return any(
                (a == source and b == target) or (a == target and b == source)
                for a, b, _ in self._edges
            )

        def has_node(self, node):
            return node in self._nodes

        def number_of_nodes(self):
            return len(self._nodes)

        def edges(self):
            return [(a, b) for a, b, _ in self._edges]

        def nodes(self, data=False):
            if data:
                return list(self._nodes.items())
            return list(self._nodes.keys())

    class _NXFallback:
        Graph = SimpleGraph

    nx = _NXFallback()

import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="Folksonomia Digital com Auditoria Semântica",
    layout="wide",
    initial_sidebar_state="collapsed",
    page_icon="📚",
)

# ──────────────────────────────────────────────────────────────────────
# PATHS E CONSTANTES
# ──────────────────────────────────────────────────────────────────────
BASE_DIR = Path("data")
OBRAS_FILE = BASE_DIR / "obras.json"
TAGS_FILE = BASE_DIR / "tags.json"
USERS_FILE = BASE_DIR / "users.json"
ADMINS_FILE = BASE_DIR / "admins.json"
ONTOLOGIES_FILE = BASE_DIR / "ontologies.json"
RELATIONS_FILE = BASE_DIR / "relations.json"
EVENTS_FILE = BASE_DIR / "events.json"
VERSIONS_FILE = BASE_DIR / "versions.json"
EXPORTS_FILE = BASE_DIR / "exports.json"
INSTITUTION_FILE = BASE_DIR / "institution_metadata.json"
CONFIG_FILE = BASE_DIR / "config.json"

ADMIN_DEFAULT = {
    "id": 1,
    "username": "nugep",
    "password_hash": hashlib.sha256("nugep123".encode("utf-8")).hexdigest(),
    "role": "admin",
}

TAG_STATUSES = ["bruto", "sugerido", "validado", "revisado", "publicado"]
ACCESS_THEMES = {
    "escuro": {"bg": "#08111f", "surface": "rgba(12,25,42,0.82)", "text": "#f5f7fb", "muted": "#d5dbe7"},
    "claro": {"bg": "#f7f3ec", "surface": "rgba(255,255,255,0.92)", "text": "#1f1f1f", "muted": "#444444"},
}
CONTRAST_MODES = {
    "normal": {"border": "rgba(255,255,255,0.20)", "accent": "#95b8ff"},
    "alto": {"border": "#ffffff", "accent": "#ffd54f"},
}
ANIMAIS = [
    "Águia", "Boto", "Capivara", "Doninha", "Ema", "Falcão", "Gavião", "Harpia", "Irara", "Jaguar",
    "Lontra", "Mico", "Onça", "Paca", "Quati", "Raposa", "Tamanduá", "Urubu", "Veado", "Zorrilho",
    "Arara", "Bugio", "Caititu", "Jaguatirica", "Lobo", "Mutum", "Pirarucu", "Tucano", "Sucuri", "Tatu",
]
ADJETIVOS = [
    "Azul", "Bravo", "Calmo", "Dourado", "Esperto", "Feroz", "Gracioso", "Intenso", "Jovial", "Lento",
    "Mágico", "Nobre", "Ousado", "Preciso", "Rápido", "Sábio", "Tímido", "Único", "Valente", "Zeloso",
    "Curioso", "Furtivo", "Altivo", "Sereno", "Vibrante", "Audaz", "Brilhante", "Corajoso", "Distinto", "Elegante",
]

BASE_ONTOLOGIES = [
    {
        "name": "Cor",
        "description": "Ontologia para cores percebidas na obra.",
        "terms": ["azul", "vermelho", "amarelo", "verde", "preto", "branco", "cinza", "dourado", "prata", "rosa", "laranja", "violeta", "marrom"],
    },
    {
        "name": "Religioso",
        "description": "Termos de religiosidade, espiritualidade e iconografia sacra.",
        "terms": ["igreja", "santo", "sagrada", "cruz", "crucifixo", "oração", "religioso", "religiosa", "anjo", "milagre", "deus", "sacrifício", "fé"],
    },
    {
        "name": "Guerra",
        "description": "Termos associados a conflito, violência e guerra.",
        "terms": ["guerra", "batalha", "soldado", "arma", "violência", "conflito", "morte", "ruína", "destruição", "bombardeio", "ferido"],
    },
    {
        "name": "Natureza",
        "description": "Elementos naturais e paisagem.",
        "terms": ["árvore", "céu", "mar", "terra", "sol", "lua", "estrela", "flor", "natureza", "rio", "montanha", "folha"],
    },
    {
        "name": "Figura Humana",
        "description": "Representações humanas, corpo, rosto e papéis sociais.",
        "terms": ["rosto", "mulher", "homem", "criança", "família", "corpo", "mão", "olhar", "retrato", "mãe", "pai", "pessoa"],
    },
    {
        "name": "Emoção",
        "description": "Vocabulário de afeto e emoção.",
        "terms": ["tristeza", "alegria", "medo", "dor", "esperança", "calma", "caos", "solidão", "amor", "raiva", "angústia"],
    },
    {
        "name": "Material e Técnica",
        "description": "Vocabulário de materialidade e técnica artística.",
        "terms": ["óleo", "tinta", "madeira", "metal", "pedra", "tecido", "gravura", "escultura", "desenho", "pintura", "cerâmica", "papel"],
    },
]

# ──────────────────────────────────────────────────────────────────────
# UTILIDADES GERAIS
# ──────────────────────────────────────────────────────────────────────
def now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def generate_animal_name() -> str:
    random.seed()
    return f"{random.choice(ANIMAIS)} {random.choice(ADJETIVOS)}"


def ensure_data_dir() -> None:
    BASE_DIR.mkdir(parents=True, exist_ok=True)


def normalize_text(text: str) -> str:
    if text is None:
        return ""
    text = str(text).strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"\s+", " ", text)
    return text


def slugify(text: str) -> str:
    text = normalize_text(text)
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or str(uuid.uuid4())[:8]


def generate_uid() -> str:
    return base64.b64encode(os.urandom(12)).decode("ascii")


def json_hash(data: Any) -> str:
    normalized = json.dumps(data, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def load_json(path: Path, default: Any) -> Any:
    ensure_data_dir()
    if not path.exists():
        return copy.deepcopy(default)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return copy.deepcopy(default)


def save_json(path: Path, data: Any) -> None:
    ensure_data_dir()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def next_id(records: List[Dict[str, Any]]) -> int:
    return (max((int(r.get("id", 0)) for r in records), default=0) + 1) if records else 1


def require_columns(df: pd.DataFrame, columns: List[str]) -> pd.DataFrame:
    for col in columns:
        if col not in df.columns:
            df[col] = np.nan
    return df


def latest_versions_index() -> Dict[Tuple[str, str], Dict[str, Any]]:
    versions = load_json(VERSIONS_FILE, [])
    idx: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for version in versions:
        idx[(version["entity_type"], str(version["entity_id"]))] = version
    return idx


# ──────────────────────────────────────────────────────────────────────
# TRILHA IMUTÁVEL / AUDITORIA / VERSIONAMENTO
# ──────────────────────────────────────────────────────────────────────
def register_version(
    entity_type: str,
    entity_id: str,
    snapshot: Dict[str, Any],
    actor: str,
    status: Optional[str] = None,
    origin: str = "humano",
) -> Dict[str, Any]:
    versions = load_json(VERSIONS_FILE, [])
    prev = None
    for version in reversed(versions):
        if version["entity_type"] == entity_type and str(version["entity_id"]) == str(entity_id):
            prev = version
            break

    version_record = {
        "id": next_id(versions),
        "timestamp": now_iso(),
        "entity_type": entity_type,
        "entity_id": str(entity_id),
        "snapshot": snapshot,
        "snapshot_hash": json_hash(snapshot),
        "previous_snapshot_hash": prev["snapshot_hash"] if prev else None,
        "actor": actor,
        "status": status,
        "origin": origin,
    }
    versions.append(version_record)
    save_json(VERSIONS_FILE, versions)
    return version_record


def register_event(
    action: str,
    entity_type: str,
    entity_id: str,
    actor: str,
    payload: Dict[str, Any],
    status: Optional[str] = None,
    automatic: bool = False,
    origin: str = "humano",
    provenance: str = "interface_streamlit",
    circulation: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    events = load_json(EVENTS_FILE, [])
    previous_hash = events[-1]["event_hash"] if events else None
    payload_hash = json_hash(payload)
    event = {
        "id": next_id(events),
        "timestamp": now_iso(),
        "action": action,
        "entity_type": entity_type,
        "entity_id": str(entity_id),
        "actor": actor,
        "payload_hash": payload_hash,
        "previous_event_hash": previous_hash,
        "provenance": provenance,
        "automatic": automatic,
        "origin": origin,
        "circulation": circulation or {},
        "status": status,
    }
    event["event_hash"] = json_hash(event)
    events.append(event)
    save_json(EVENTS_FILE, events)
    return event


def audit_write(
    collection_file: Path,
    entity_type: str,
    records: List[Dict[str, Any]],
    target_record: Dict[str, Any],
    actor: str,
    action: str,
    status: Optional[str] = None,
    automatic: bool = False,
    origin: str = "humano",
    provenance: str = "interface_streamlit",
    circulation: Optional[Dict[str, Any]] = None,
) -> None:
    save_json(collection_file, records)
    version = register_version(entity_type, str(target_record["id"]), target_record, actor, status=status, origin=origin)
    payload = {
        "record_id": target_record["id"],
        "version_hash": version["snapshot_hash"],
        "record": target_record,
    }
    register_event(
        action=action,
        entity_type=entity_type,
        entity_id=str(target_record["id"]),
        actor=actor,
        payload=payload,
        status=status,
        automatic=automatic,
        origin=origin,
        provenance=provenance,
        circulation=circulation,
    )


def audit_delete(
    collection_file: Path,
    entity_type: str,
    entity_id: str,
    remaining_records: List[Dict[str, Any]],
    actor: str,
    payload: Dict[str, Any],
    provenance: str = "interface_streamlit",
) -> None:
    save_json(collection_file, remaining_records)
    register_event(
        action="delete",
        entity_type=entity_type,
        entity_id=str(entity_id),
        actor=actor,
        payload=payload,
        status="revisado",
        provenance=provenance,
    )


# ──────────────────────────────────────────────────────────────────────
# DADOS INICIAIS
# ──────────────────────────────────────────────────────────────────────
def default_works() -> List[Dict[str, Any]]:
    return [
        {
            "id": 1,
            "titulo": "Guernica",
            "artista": "Pablo Picasso",
            "ano": "1937",
            "imagem": "https://upload.wikimedia.org/wikipedia/en/7/74/PicassoGuernica.jpg",
            "descricao": "Pintura monumental em preto, branco e cinza que trata da violência e do impacto da guerra sobre corpos, animais e arquitetura fragmentada.",
            "audio_descricao": "Guernica é uma pintura horizontal e extensa, construída em tons de preto, branco e cinza. Vários corpos humanos e animais surgem despedaçados, com expressões de dor, medo e desorientação. À esquerda aparece um touro escuro e, abaixo dele, uma mãe ergue o rosto enquanto segura o filho morto. No centro, um cavalo de boca aberta parece gritar. Linhas angulosas sugerem ruptura, ruína e bombardeio.",
            "metadados": {"colecao": "Acervo de referência", "origem": "Open access", "licenca": "Uso educacional"},
        },
        {
            "id": 2,
            "titulo": "A Noite Estrelada",
            "artista": "Vincent van Gogh",
            "ano": "1889",
            "imagem": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ea/Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg/1200px-Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg",
            "descricao": "Paisagem noturna com céu em redemoinhos e vila abaixo, marcada por cor, ritmo e sensação de movimento.",
            "audio_descricao": "Em formato horizontal, a cena mostra uma vila pequena ao fundo e, acima dela, um céu azul profundo atravessado por espirais luminosas. As estrelas aparecem como círculos amarelos intensos, quase vibrando. À esquerda, um cipreste escuro sobe como uma chama vertical. A pintura transmite noite, vento, ritmo e contemplação.",
            "metadados": {"colecao": "Acervo de referência", "origem": "Open access", "licenca": "Uso educacional"},
        },
        {
            "id": 3,
            "titulo": "Mona Lisa",
            "artista": "Leonardo da Vinci",
            "ano": "1503",
            "imagem": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ec/Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_retouched.jpg/800px-Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_retouched.jpg",
            "descricao": "Retrato de meia figura com paisagem ao fundo e expressão enigmática.",
            "audio_descricao": "Uma mulher é vista da cintura para cima, sentada e levemente virada para a direita, enquanto encara o observador. O rosto apresenta expressão serena e um sorriso discreto. Os cabelos escuros caem sobre os ombros. As mãos aparecem cruzadas em primeiro plano. Ao fundo há uma paisagem de montanhas, água e caminhos sinuosos em tons suaves.",
            "metadados": {"colecao": "Acervo de referência", "origem": "Open access", "licenca": "Uso educacional"},
        },
    ]


def default_institution_metadata() -> Dict[str, Any]:
    return {
        "instituicao": "Instituição Museológica",
        "sigla": "NUGEP",
        "responsavel": "Coordenação de documentação",
        "politica_dados": "Dados analíticos e metadados com trilha auditável, versionamento e controle de proveniência.",
        "padroes": ["DCMI", "CIDOC-CRM", "Vocabulários híbridos", "Folksonomia"],
        "colecoes": ["Pintura", "Escultura", "Documentação"],
        "ultima_atualizacao": now_iso(),
    }


def bootstrap_files() -> None:
    ensure_data_dir()
    if not ADMINS_FILE.exists():
        save_json(ADMINS_FILE, [ADMIN_DEFAULT])
    if not OBRAS_FILE.exists():
        save_json(OBRAS_FILE, default_works())
    if not TAGS_FILE.exists():
        save_json(TAGS_FILE, [])
    if not USERS_FILE.exists():
        save_json(USERS_FILE, [])
    if not ONTOLOGIES_FILE.exists():
        default_records = []
        for idx, ontology in enumerate(BASE_ONTOLOGIES, start=1):
            default_records.append(
                {
                    "id": idx,
                    "name": ontology["name"],
                    "slug": slugify(ontology["name"]),
                    "description": ontology["description"],
                    "terms": ontology["terms"],
                    "status": "publicado",
                    "created_at": now_iso(),
                    "updated_at": now_iso(),
                    "created_by": "bootstrap",
                    "automatic": False,
                    "origin": "humano",
                }
            )
        save_json(ONTOLOGIES_FILE, default_records)
    if not RELATIONS_FILE.exists():
        save_json(RELATIONS_FILE, [])
    if not EVENTS_FILE.exists():
        save_json(EVENTS_FILE, [])
    if not VERSIONS_FILE.exists():
        save_json(VERSIONS_FILE, [])
    if not EXPORTS_FILE.exists():
        save_json(EXPORTS_FILE, [])
    if not INSTITUTION_FILE.exists():
        save_json(INSTITUTION_FILE, default_institution_metadata())
    if not CONFIG_FILE.exists():
        save_json(CONFIG_FILE, {"seed_loaded": True})


# ──────────────────────────────────────────────────────────────────────
# LOADERS
# ──────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=5, show_spinner=False)
def load_obras() -> List[Dict[str, Any]]:
    return load_json(OBRAS_FILE, default_works())


@st.cache_data(ttl=5, show_spinner=False)
def load_tags_df() -> pd.DataFrame:
    df = pd.DataFrame(load_json(TAGS_FILE, []))
    if df.empty:
        return pd.DataFrame(columns=[
            "id", "user_id", "obra_id", "tag_original", "tag_normalized", "created_at",
            "status", "ontology_group", "ontology_term", "automatic", "origin", "provenance",
            "validated_by", "validated_at", "notes", "familiaridade", "conhecimento_museologico"
        ])
    return require_columns(df, [
        "id", "user_id", "obra_id", "tag_original", "tag_normalized", "created_at",
        "status", "ontology_group", "ontology_term", "automatic", "origin", "provenance",
        "validated_by", "validated_at", "notes", "familiaridade", "conhecimento_museologico"
    ])


@st.cache_data(ttl=5, show_spinner=False)
def load_users_df() -> pd.DataFrame:
    df = pd.DataFrame(load_json(USERS_FILE, []))
    if df.empty:
        return pd.DataFrame(columns=["user_id", "animal_name", "timestamp", "q1", "q2", "q3"])
    return require_columns(df, ["user_id", "animal_name", "timestamp", "q1", "q2", "q3"])


@st.cache_data(ttl=5, show_spinner=False)
def load_ontologies_df() -> pd.DataFrame:
    df = pd.DataFrame(load_json(ONTOLOGIES_FILE, []))
    if df.empty:
        return pd.DataFrame(columns=["id", "name", "slug", "description", "terms", "status", "created_at", "updated_at", "created_by", "automatic", "origin"])
    return require_columns(df, ["id", "name", "slug", "description", "terms", "status", "created_at", "updated_at", "created_by", "automatic", "origin"])


@st.cache_data(ttl=5, show_spinner=False)
def load_relations_df() -> pd.DataFrame:
    df = pd.DataFrame(load_json(RELATIONS_FILE, []))
    if df.empty:
        return pd.DataFrame(columns=["id", "source_type", "source_id", "target_type", "target_id", "relation_type", "confidence", "automatic", "active", "created_at"])
    return df


@st.cache_data(ttl=5, show_spinner=False)
def load_events_df() -> pd.DataFrame:
    df = pd.DataFrame(load_json(EVENTS_FILE, []))
    if df.empty:
        return pd.DataFrame(columns=["id", "timestamp", "action", "entity_type", "entity_id", "actor", "event_hash", "previous_event_hash", "status", "provenance", "automatic"])
    return df


@st.cache_data(ttl=5, show_spinner=False)
def load_versions_df() -> pd.DataFrame:
    df = pd.DataFrame(load_json(VERSIONS_FILE, []))
    if df.empty:
        return pd.DataFrame(columns=["id", "timestamp", "entity_type", "entity_id", "snapshot_hash", "previous_snapshot_hash", "actor", "status", "origin"])
    return df


def clear_caches() -> None:
    st.cache_data.clear()


# ──────────────────────────────────────────────────────────────────────
# CSS / ACESSIBILIDADE
# ──────────────────────────────────────────────────────────────────────
def ensure_accessibility_session() -> None:
    defaults = {
        "font_scale": 1.0,
        "theme_mode": "escuro",
        "contrast_mode": "normal",
        "focus_audio": True,
        "user_id": generate_uid(),
        "animal_name": generate_animal_name(),
        "step": "intro",
        "answers": {},
        "admin_logged_in": False,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def load_css() -> None:
    theme = ACCESS_THEMES[st.session_state.get("theme_mode", "escuro")]
    contrast = CONTRAST_MODES[st.session_state.get("contrast_mode", "normal")]
    font_scale = float(st.session_state.get("font_scale", 1.0))
    focus_audio = st.session_state.get("focus_audio", True)
    audio_border = contrast["accent"] if focus_audio else contrast["border"]

    st.markdown(
        f"""
        <style>
        :root {{
            --app-bg: {theme['bg']};
            --surface: {theme['surface']};
            --surface-2: rgba(255,255,255,0.08);
            --text-main: {theme['text']};
            --text-muted: {theme['muted']};
            --border: {contrast['border']};
            --accent: {contrast['accent']};
            --font-scale: {font_scale};
            --audio-border: {audio_border};
        }}
        html, body, [class*="css"], [class*="st-"] {{
            font-family: 'Times New Roman', Times, serif !important;
        }}
        .stApp {{
            background: linear-gradient(135deg, var(--app-bg) 0%, #10253f 100%);
            color: var(--text-main);
        }}
        #MainMenu, footer, header {{visibility: hidden;}}
        .block-container {{padding-top: 1.2rem; padding-bottom: 3rem;}}
        h1, h2, h3, h4, h5, h6, p, span, div, label {{
            color: var(--text-main) !important;
            font-size: calc(1rem * var(--font-scale));
        }}
        .app-wrap {{max-width: 1500px; margin: 0 auto;}}
        .hero {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 24px;
            padding: 1.6rem 1.8rem;
            margin-bottom: 1rem;
            box-shadow: 0 8px 30px rgba(0,0,0,0.18);
        }}
        .hero h1 {{font-size: calc(2.5rem * var(--font-scale)); margin-bottom: .5rem;}}
        .hero p {{color: var(--text-muted) !important; line-height: 1.6;}}
        .glass-card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 22px;
            padding: 1.2rem 1.4rem;
            margin: .9rem 0;
            box-shadow: 0 8px 24px rgba(0,0,0,0.12);
        }}
        .obra-card {{
            background: var(--surface);
            border: 1px solid var(--audio-border);
            border-radius: 24px;
            padding: 1rem;
            margin-bottom: 1rem;
            box-shadow: 0 8px 24px rgba(0,0,0,0.12);
        }}
        .obra-card img {{width:100%; height:300px; object-fit:cover; border-radius:18px;}}
        .micro-card {{
            background: rgba(255,255,255,0.06);
            border: 1px solid var(--border);
            border-radius: 18px;
            padding: 1rem;
            min-height: 120px;
        }}
        .kpi {{font-size: calc(2rem * var(--font-scale)); font-weight: 700; margin: .2rem 0;}}
        .muted {{color: var(--text-muted) !important;}}
        .tag-badge {{
            display:inline-block;
            margin:.2rem .3rem .2rem 0;
            padding:.35rem .75rem;
            border-radius:50px;
            border:1px solid var(--border);
            background: rgba(255,255,255,0.08);
        }}
        .status-pill {{
            display:inline-block;
            padding:.25rem .7rem;
            border-radius:50px;
            background: rgba(149,184,255,.18);
            border:1px solid var(--accent);
            margin-left:.3rem;
        }}
        .audio-box {{
            border-left: 5px solid var(--audio-border);
            background: rgba(255,255,255,0.06);
            padding: 1rem;
            border-radius: 16px;
            margin-top: .7rem;
        }}
        .audit-row {{
            background: rgba(255,255,255,0.04);
            border:1px solid var(--border);
            border-radius:16px;
            padding:.85rem 1rem;
            margin-bottom:.45rem;
        }}
        .stButton > button, .stDownloadButton > button {{
            border-radius: 999px !important;
            border: 1px solid var(--accent) !important;
            background: rgba(255,255,255,0.10) !important;
            color: var(--text-main) !important;
            font-weight: 700 !important;
        }}
        .stTextInput input, .stTextArea textarea, .stSelectbox select, .stNumberInput input {{
            background: rgba(255,255,255,0.06) !important;
            border: 1px solid var(--border) !important;
            color: var(--text-main) !important;
            border-radius: 14px !important;
        }}
        .stTabs [data-baseweb="tab-list"] {{gap:.5rem;}}
        .stTabs [data-baseweb="tab"] {{
            border-radius: 999px;
            background: rgba(255,255,255,0.06);
            border:1px solid var(--border);
        }}
        .stDataFrame, .stTable {{border-radius: 14px; overflow:hidden;}}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_accessibility_controls() -> None:
    with st.expander("Acessibilidade e leitura", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.session_state["font_scale"] = st.slider("Tamanho do texto", 0.9, 1.6, float(st.session_state["font_scale"]), 0.1)
        with c2:
            st.session_state["contrast_mode"] = st.selectbox("Contraste", list(CONTRAST_MODES.keys()), index=list(CONTRAST_MODES.keys()).index(st.session_state["contrast_mode"]))
        with c3:
            st.session_state["theme_mode"] = st.selectbox("Tema", list(ACCESS_THEMES.keys()), index=list(ACCESS_THEMES.keys()).index(st.session_state["theme_mode"]))
        with c4:
            st.session_state["focus_audio"] = st.toggle("Foco em audiodescrição", value=st.session_state["focus_audio"])
    load_css()


# ──────────────────────────────────────────────────────────────────────
# ONTOLOGIAS / SUGESTÕES / RELAÇÕES
# ──────────────────────────────────────────────────────────────────────
def ontology_terms_map() -> Dict[str, List[str]]:
    ont_df = load_ontologies_df()
    mapping: Dict[str, List[str]] = {}
    if ont_df.empty:
        return mapping
    for _, row in ont_df.iterrows():
        terms = row["terms"] if isinstance(row["terms"], list) else []
        mapping[row["name"]] = [normalize_text(term) for term in terms if str(term).strip()]
    return mapping


def build_lexicon() -> List[str]:
    tag_df = load_tags_df()
    ontology_map = ontology_terms_map()
    lexicon = set()
    if not tag_df.empty:
        lexicon.update(normalize_text(tag) for tag in tag_df["tag_normalized"].dropna().astype(str).tolist())
        lexicon.update(normalize_text(tag) for tag in tag_df["tag_original"].dropna().astype(str).tolist())
    for terms in ontology_map.values():
        lexicon.update(terms)
    return sorted(t for t in lexicon if t)


def infer_ontology_groups(tag_text: str) -> List[Tuple[str, str, float]]:
    normalized = normalize_text(tag_text)
    matches: List[Tuple[str, str, float]] = []
    for group_name, terms in ontology_terms_map().items():
        for term in terms:
            if not term:
                continue
            if normalized == term:
                matches.append((group_name, term, 1.0))
            elif normalized in term or term in normalized:
                confidence = round(min(len(normalized), len(term)) / max(len(normalized), len(term)), 3)
                matches.append((group_name, term, max(0.55, confidence)))
            else:
                ratio = len(set(normalized.split()) & set(term.split())) / max(1, len(set(normalized.split()) | set(term.split())))
                if ratio >= 0.5:
                    matches.append((group_name, term, round(ratio, 3)))
    dedup = {}
    for group_name, term, confidence in matches:
        key = (group_name, term)
        dedup[key] = max(confidence, dedup.get(key, 0.0))
    return sorted([(a, b, c) for (a, b), c in dedup.items()], key=lambda x: x[2], reverse=True)


def suggest_corrections(tag_text: str) -> List[str]:
    normalized = normalize_text(tag_text)
    if not normalized:
        return []
    lexicon = build_lexicon()
    if normalized in lexicon:
        return []
    suggestions = get_close_matches(normalized, lexicon, n=5, cutoff=0.72)
    repeated_fix = re.sub(r"(.)\1{2,}", r"\1", normalized)
    if repeated_fix != normalized and repeated_fix in lexicon:
        suggestions = [repeated_fix] + suggestions
    seen = []
    for item in suggestions:
        if item not in seen:
            seen.append(item)
    return seen[:5]


def semantic_group_from_tag(tag_text: str) -> str:
    matches = infer_ontology_groups(tag_text)
    return matches[0][0] if matches else "Sem classificação"


def refresh_tag_relations(tag_record: Dict[str, Any], actor: str = "sistema") -> None:
    relations = load_json(RELATIONS_FILE, [])
    target_tag_id = tag_record["id"]
    for relation in relations:
        if relation.get("source_type") == "tag" and relation.get("source_id") == target_tag_id and relation.get("automatic"):
            relation["active"] = False
            relation["updated_at"] = now_iso()

    matches = infer_ontology_groups(tag_record.get("tag_normalized") or tag_record.get("tag_original", ""))
    ontologies = load_json(ONTOLOGIES_FILE, [])
    ont_by_name = {row["name"]: row for row in ontologies}
    for group_name, term, confidence in matches:
        ontology = ont_by_name.get(group_name)
        if not ontology:
            continue
        relation = {
            "id": next_id(relations),
            "source_type": "tag",
            "source_id": target_tag_id,
            "target_type": "ontology",
            "target_id": ontology["id"],
            "relation_type": "classificado_em",
            "confidence": confidence,
            "automatic": True,
            "active": True,
            "created_at": now_iso(),
            "updated_at": now_iso(),
            "term_match": term,
        }
        relations.append(relation)
        register_event(
            action="relation_create",
            entity_type="relation",
            entity_id=str(relation["id"]),
            actor=actor,
            payload=relation,
            automatic=True,
            origin="ia_heuristica",
            provenance="classificacao_automatica",
        )
    save_json(RELATIONS_FILE, relations)
    clear_caches()


# ──────────────────────────────────────────────────────────────────────
# CRUD PRINCIPAL
# ──────────────────────────────────────────────────────────────────────
def check_login(username: str, password: str) -> bool:
    admins = load_json(ADMINS_FILE, [ADMIN_DEFAULT])
    password_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
    return any(a.get("username") == username and a.get("password_hash") == password_hash for a in admins)


def save_answers(user_id: str, animal_name: str, answers: Dict[str, Any]) -> None:
    users = load_json(USERS_FILE, [])
    existing = next((u for u in users if u.get("user_id") == user_id), None)
    record = {
        "user_id": user_id,
        "animal_name": animal_name,
        "timestamp": now_iso(),
        **answers,
    }
    if existing:
        existing.update(record)
        save_json(USERS_FILE, users)
        register_event("update", "user", user_id, user_id, record, status="publicado")
    else:
        users.append(record)
        save_json(USERS_FILE, users)
        register_version("user", user_id, record, user_id, status="publicado")
        register_event("create", "user", user_id, user_id, record, status="publicado")
    clear_caches()


def user_profile(user_id: str) -> Dict[str, Any]:
    users_df = load_users_df()
    if users_df.empty:
        return {}
    row = users_df[users_df["user_id"] == user_id]
    return row.iloc[0].to_dict() if not row.empty else {}


def save_tag(user_id: str, obra_id: int, tag_text: str) -> Dict[str, Any]:
    tags = load_json(TAGS_FILE, [])
    profile = user_profile(user_id)
    record = {
        "id": next_id(tags),
        "user_id": user_id,
        "obra_id": int(obra_id),
        "tag_original": tag_text.strip(),
        "tag_normalized": normalize_text(tag_text),
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "status": "bruto",
        "ontology_group": semantic_group_from_tag(tag_text),
        "ontology_term": infer_ontology_groups(tag_text)[0][1] if infer_ontology_groups(tag_text) else "",
        "automatic": False,
        "origin": "humano",
        "provenance": "explorar_obras",
        "validated_by": "",
        "validated_at": "",
        "notes": "",
        "familiaridade": profile.get("q1", "Não informado"),
        "conhecimento_museologico": profile.get("q2", "Não informado"),
        "correction_suggestions": suggest_corrections(tag_text),
    }
    tags.append(record)
    audit_write(
        TAGS_FILE,
        "tag",
        tags,
        record,
        actor=user_id,
        action="create",
        status=record["status"],
        provenance="submissao_publica",
    )
    refresh_tag_relations(record, actor=user_id)
    clear_caches()
    return record


def update_tag_record(tag_id: int, updates: Dict[str, Any], actor: str, action: str = "update") -> Optional[Dict[str, Any]]:
    tags = load_json(TAGS_FILE, [])
    updated = None
    for record in tags:
        if int(record["id"]) == int(tag_id):
            record.update(updates)
            record["updated_at"] = now_iso()
            updated = record
            break
    if updated is None:
        return None
    audit_write(
        TAGS_FILE,
        "tag",
        tags,
        updated,
        actor=actor,
        action=action,
        status=updated.get("status"),
        provenance="administracao_tags",
    )
    refresh_tag_relations(updated, actor=actor)
    clear_caches()
    return updated


def create_ontology(name: str, description: str, terms_text: str, actor: str) -> Dict[str, Any]:
    ontologies = load_json(ONTOLOGIES_FILE, [])
    terms = [normalize_text(term) for term in re.split(r"[,;\n]", terms_text) if term.strip()]
    record = {
        "id": next_id(ontologies),
        "name": name.strip(),
        "slug": slugify(name),
        "description": description.strip(),
        "terms": sorted(dict.fromkeys(terms)),
        "status": "publicado",
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "created_by": actor,
        "automatic": False,
        "origin": "humano",
    }
    ontologies.append(record)
    audit_write(ONTOLOGIES_FILE, "ontology", ontologies, record, actor=actor, action="create", status="publicado", provenance="administracao_ontologias")
    clear_caches()
    return record


def update_ontology(ontology_id: int, updates: Dict[str, Any], actor: str) -> Optional[Dict[str, Any]]:
    ontologies = load_json(ONTOLOGIES_FILE, [])
    updated = None
    for record in ontologies:
        if int(record["id"]) == int(ontology_id):
            record.update(updates)
            record["updated_at"] = now_iso()
            if isinstance(record.get("terms"), str):
                record["terms"] = [normalize_text(t) for t in re.split(r"[,;\n]", record["terms"]) if t.strip()]
            updated = record
            break
    if updated:
        audit_write(ONTOLOGIES_FILE, "ontology", ontologies, updated, actor=actor, action="update", status=updated.get("status", "publicado"), provenance="administracao_ontologias")
        clear_caches()
    return updated


def add_work(payload: Dict[str, Any], actor: str) -> Dict[str, Any]:
    works = load_json(OBRAS_FILE, default_works())
    record = {
        "id": next_id(works),
        "titulo": payload["titulo"].strip(),
        "artista": payload.get("artista", "").strip(),
        "ano": payload.get("ano", "").strip(),
        "imagem": payload.get("imagem", "").strip(),
        "descricao": payload.get("descricao", "").strip(),
        "audio_descricao": payload.get("audio_descricao", "").strip(),
        "metadados": {
            "colecao": payload.get("colecao", ""),
            "origem": payload.get("origem", ""),
            "licenca": payload.get("licenca", ""),
        },
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    works.append(record)
    audit_write(OBRAS_FILE, "obra", works, record, actor=actor, action="create", status="publicado", provenance="administracao_obras")
    clear_caches()
    return record


def delete_work(work_id: int, actor: str) -> bool:
    works = load_json(OBRAS_FILE, default_works())
    target = next((w for w in works if int(w["id"]) == int(work_id)), None)
    if not target:
        return False
    remaining = [w for w in works if int(w["id"]) != int(work_id)]
    audit_delete(OBRAS_FILE, "obra", str(work_id), remaining, actor, payload=target, provenance="administracao_obras")
    clear_caches()
    return True


def update_institution_metadata(metadata: Dict[str, Any], actor: str) -> None:
    save_json(INSTITUTION_FILE, metadata)
    register_version("institution_metadata", "principal", metadata, actor, status="publicado")
    register_event("update", "institution_metadata", "principal", actor, metadata, status="publicado", provenance="metadados_institucionais")
    clear_caches()


def register_export(actor: str, export_type: str, destination: str, note: str, file_hash: str) -> None:
    exports = load_json(EXPORTS_FILE, [])
    record = {
        "id": next_id(exports),
        "timestamp": now_iso(),
        "actor": actor,
        "export_type": export_type,
        "destination": destination,
        "note": note,
        "file_hash": file_hash,
    }
    exports.append(record)
    save_json(EXPORTS_FILE, exports)
    register_version("export", str(record["id"]), record, actor, status="publicado")
    register_event(
        action="export",
        entity_type="export",
        entity_id=str(record["id"]),
        actor=actor,
        payload=record,
        status="publicado",
        provenance="exportacao_open_data",
        circulation={"destination": destination, "note": note},
    )
    clear_caches()


# ──────────────────────────────────────────────────────────────────────
# VISUAIS / MÉTRICAS
# ──────────────────────────────────────────────────────────────────────
def card(title: str, value: Any, subtitle: str = "") -> None:
    st.markdown(
        f"""
        <div class="micro-card">
            <div class="muted">{title}</div>
            <div class="kpi">{value}</div>
            <div class="muted">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def speech_player(text: str, label: str = "Ouvir audiodescrição") -> None:
    if not text:
        return
    element_id = f"speech_{uuid.uuid4().hex[:8]}"
    safe_text = json.dumps(text)
    components.html(
        f"""
        <div>
          <button id="{element_id}" style="padding:10px 18px;border-radius:999px;border:1px solid #8fb0ff;background:rgba(255,255,255,.08);color:#ffffff;cursor:pointer;font-family:'Times New Roman',serif;">
            🔊 {label}
          </button>
          <script>
            const btn = document.getElementById('{element_id}');
            btn.onclick = () => {{
              const synth = window.speechSynthesis;
              synth.cancel();
              const utter = new SpeechSynthesisUtterance({safe_text});
              utter.lang = 'pt-BR';
              utter.rate = 0.95;
              synth.speak(utter);
            }};
          </script>
        </div>
        """,
        height=56,
    )


def tags_by_user_and_work(obra_id: int, user_id: str) -> pd.DataFrame:
    tag_df = load_tags_df()
    if tag_df.empty:
        return pd.DataFrame(columns=["tag_original", "count"])
    subset = tag_df[(tag_df["obra_id"].astype(int) == int(obra_id)) & (tag_df["user_id"] == user_id)]
    if subset.empty:
        return pd.DataFrame(columns=["tag_original", "count"])
    count_df = subset["tag_original"].value_counts().reset_index()
    count_df.columns = ["tag_original", "count"]
    return count_df


def tag_frequency_df() -> pd.DataFrame:
    tag_df = load_tags_df()
    if tag_df.empty:
        return pd.DataFrame(columns=["tag", "frequencia"])
    freq = tag_df["tag_normalized"].value_counts().reset_index()
    freq.columns = ["tag", "frequencia"]
    return freq


def ontology_coverage_df() -> pd.DataFrame:
    tag_df = load_tags_df()
    ont_df = load_ontologies_df()
    if ont_df.empty:
        return pd.DataFrame(columns=["Ontologia", "Termos", "Tags ligadas", "Cobertura %"])
    total_tags = len(tag_df) if not tag_df.empty else 0
    rows = []
    for _, row in ont_df.iterrows():
        terms = row["terms"] if isinstance(row["terms"], list) else []
        linked = 0
        if not tag_df.empty:
            linked = int((tag_df["ontology_group"].fillna("") == row["name"]).sum())
        rows.append({
            "Ontologia": row["name"],
            "Termos": len(terms),
            "Tags ligadas": linked,
            "Cobertura %": round((linked / total_tags) * 100, 2) if total_tags else 0,
            "Descrição": row.get("description", ""),
        })
    return pd.DataFrame(rows).sort_values("Tags ligadas", ascending=False)


def build_graph(familiaridade_filter: str = "Todas") -> Tuple[nx.Graph, pd.DataFrame]:
    tag_df = load_tags_df()
    if tag_df.empty:
        return nx.Graph(), pd.DataFrame()
    if familiaridade_filter != "Todas":
        tag_df = tag_df[tag_df["familiaridade"].fillna("Não informado") == familiaridade_filter]
    works = {w["id"]: w for w in load_obras()}
    graph = nx.Graph()
    edges_meta = []
    grouped = tag_df.groupby("obra_id")
    for obra_id, subset in grouped:
        obra_node = f"obra_{obra_id}"
        obra_label = works.get(int(obra_id), {}).get("titulo", f"Obra {obra_id}")
        graph.add_node(obra_node, label=obra_label, node_type="obra")
        unique_tags = subset["tag_normalized"].dropna().astype(str).unique().tolist()
        for tag in unique_tags:
            tag_node = f"tag_{tag}"
            graph.add_node(tag_node, label=tag, node_type="tag")
            graph.add_edge(obra_node, tag_node, relation="descreve")
            edges_meta.append({"source": obra_label, "target": tag, "relation": "descreve"})
        for idx, tag_a in enumerate(unique_tags):
            for tag_b in unique_tags[idx + 1:]:
                if graph.has_edge(f"tag_{tag_a}", f"tag_{tag_b}"):
                    continue
                graph.add_edge(f"tag_{tag_a}", f"tag_{tag_b}", relation="coocorrencia")
                edges_meta.append({"source": tag_a, "target": tag_b, "relation": "coocorrencia"})

    ont_df = load_ontologies_df()
    for _, ont in ont_df.iterrows():
        ont_node = f"ont_{ont['id']}"
        graph.add_node(ont_node, label=ont["name"], node_type="ontology")
    for _, tag in tag_df.iterrows():
        group_name = tag.get("ontology_group")
        if pd.isna(group_name) or not str(group_name).strip() or group_name == "Sem classificação":
            continue
        tag_node = f"tag_{tag['tag_normalized']}"
        ont_row = ont_df[ont_df["name"] == group_name]
        if ont_row.empty:
            continue
        ont_node = f"ont_{int(ont_row.iloc[0]['id'])}"
        if not graph.has_node(tag_node):
            graph.add_node(tag_node, label=tag["tag_normalized"], node_type="tag")
        graph.add_edge(tag_node, ont_node, relation="pertence_a")
        edges_meta.append({"source": tag["tag_normalized"], "target": group_name, "relation": "pertence_a"})
    return graph, pd.DataFrame(edges_meta)


def compute_graph_positions(graph: nx.Graph) -> Dict[str, Tuple[float, float]]:
    nodes = [node for node in graph.nodes()]
    if not nodes:
        return {}
    if HAS_NETWORKX:
        return nx.spring_layout(graph, seed=42, k=0.9)
    total = max(len(nodes), 1)
    radius = 1.0
    positions: Dict[str, Tuple[float, float]] = {}
    for idx, node in enumerate(nodes):
        angle = (2 * np.pi * idx) / total
        positions[node] = (float(radius * np.cos(angle)), float(radius * np.sin(angle)))
    return positions


def plot_network(graph: nx.Graph) -> Optional[go.Figure]:
    if graph.number_of_nodes() == 0:
        return None
    pos = compute_graph_positions(graph)
    edge_x, edge_y = [], []
    for source, target in graph.edges():
        x0, y0 = pos[source]
        x1, y1 = pos[target]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])
    edge_trace = go.Scatter(
        x=edge_x,
        y=edge_y,
        mode="lines",
        line=dict(width=1),
        hoverinfo="none",
    )

    node_x, node_y, labels, node_types, sizes = [], [], [], [], []
    for node, data in graph.nodes(data=True):
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        labels.append(data.get("label", node))
        node_types.append(data.get("node_type", "nó"))
        if data.get("node_type") == "obra":
            sizes.append(28)
        elif data.get("node_type") == "ontology":
            sizes.append(24)
        else:
            sizes.append(18)

    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers+text",
        text=labels,
        textposition="top center",
        hovertext=[f"{label} · {node_type}" for label, node_type in zip(labels, node_types)],
        hoverinfo="text",
        marker=dict(size=sizes, line=dict(width=1)),
    )
    fig = go.Figure(data=[edge_trace, node_trace])
    fig.update_layout(height=650, margin=dict(l=20, r=20, t=20, b=20), showlegend=False)
    return fig


def compute_analytics_summary() -> Dict[str, Any]:
    tag_df = load_tags_df()
    users_df = load_users_df()
    ont_df = load_ontologies_df()
    events_df = load_events_df()
    works = load_obras()
    return {
        "gerado_em": now_iso(),
        "total_tags": int(len(tag_df)),
        "tags_unicas": int(tag_df["tag_normalized"].nunique()) if not tag_df.empty else 0,
        "usuarios": int(users_df["user_id"].nunique()) if not users_df.empty else 0,
        "obras": int(len(works)),
        "ontologias": int(len(ont_df)),
        "eventos_auditoria": int(len(events_df)),
        "status_tags": tag_df["status"].value_counts(dropna=False).to_dict() if not tag_df.empty else {},
        "grupos_semanticos": tag_df["ontology_group"].value_counts(dropna=False).to_dict() if not tag_df.empty else {},
        "familiaridade": tag_df["familiaridade"].value_counts(dropna=False).to_dict() if not tag_df.empty else {},
    }


# ──────────────────────────────────────────────────────────────────────
# INTRO / FLUXO PÚBLICO
# ──────────────────────────────────────────────────────────────────────
def show_intro() -> None:
    st.markdown("<div class='app-wrap'>", unsafe_allow_html=True)
    st.markdown(
        """
        <div class='hero'>
            <h1>Sistema Folksonomia Digital com auditoria semântica</h1>
            <p>
                Plataforma com trilha de eventos, versionamento de metadados, ontologias administráveis,
                validação humana e acessibilidade com foco em audiodescrição.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.container(border=False):
        st.markdown("### Questionário de entrada")
        with st.form("intro_form"):
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
            with c2:
                q3 = st.text_area(
                    "3. O que você entende por tags ou etiquetas digitais aplicadas ao acervo?",
                    height=190,
                    placeholder="Descreva com suas palavras.",
                )
            submitted = st.form_submit_button("Entrar na plataforma", use_container_width=True)
            if submitted:
                if not q3.strip():
                    st.error("Preencha todas as perguntas.")
                else:
                    answers = {"q1": q1, "q2": q2, "q3": q3.strip()}
                    st.session_state["answers"] = answers
                    save_answers(st.session_state["user_id"], st.session_state["animal_name"], answers)
                    st.session_state["step"] = "completed"
                    st.success("Acesso liberado.")
                    st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def public_filters_ui(obras: List[Dict[str, Any]]) -> Tuple[str, str]:
    c1, c2 = st.columns([2, 1])
    with c1:
        search = st.text_input("Buscar obra", placeholder="Título, artista ou palavra-chave")
    with c2:
        group_filter = st.selectbox("Filtrar por grupo semântico", ["Todos"] + sorted(load_ontologies_df()["name"].dropna().astype(str).unique().tolist()))
    return search, group_filter


def show_obras() -> None:
    obras = load_obras()
    tag_df = load_tags_df()
    st.markdown("### Explorar obras")
    st.markdown("Use as ferramentas abaixo para explorar, ouvir a audiodescrição e contribuir com tags.")

    search, group_filter = public_filters_ui(obras)
    normalized_search = normalize_text(search)
    filtered = []
    for obra in obras:
        haystack = " ".join([
            obra.get("titulo", ""),
            obra.get("artista", ""),
            obra.get("descricao", ""),
            obra.get("audio_descricao", ""),
        ])
        if normalized_search and normalized_search not in normalize_text(haystack):
            continue
        if group_filter != "Todos" and not tag_df.empty:
            obra_tags = tag_df[(tag_df["obra_id"].astype(int) == int(obra["id"])) & (tag_df["ontology_group"].fillna("") == group_filter)]
            if obra_tags.empty:
                continue
        filtered.append(obra)

    st.info(f"Obras exibidas: {len(filtered)}")
    cols = st.columns(2)
    for idx, obra in enumerate(filtered):
        with cols[idx % 2]:
            st.markdown("<div class='obra-card'>", unsafe_allow_html=True)
            st.image(obra.get("imagem", ""), use_container_width=True)
            st.markdown(f"#### {obra['titulo']}")
            st.markdown(f"**Artista:** {obra.get('artista','Não informado')}  ")
            st.markdown(f"**Ano:** {obra.get('ano','Não informado')}  ")
            st.markdown(f"**Descrição curatorial:** {obra.get('descricao','')}  ")
            if st.session_state.get("focus_audio", True):
                st.markdown(f"<div class='audio-box'><strong>Audiodescrição:</strong><br>{obra.get('audio_descricao','Sem audiodescrição cadastrada.')}</div>", unsafe_allow_html=True)
            with st.expander("Ouvir e detalhar audiodescrição"):
                st.write(obra.get("audio_descricao", "Sem audiodescrição cadastrada."))
                speech_player(obra.get("audio_descricao", ""), label="Ler audiodescrição")
            my_tags = tags_by_user_and_work(obra["id"], st.session_state["user_id"])
            if not my_tags.empty:
                st.markdown("**Suas tags nesta obra**")
                badges = "".join([f"<span class='tag-badge'>{row['tag_original']} ({row['count']})</span>" for _, row in my_tags.iterrows()])
                st.markdown(badges, unsafe_allow_html=True)
            with st.form(f"tag_form_{obra['id']}"):
                tag_text = st.text_input("Adicionar tag", placeholder="Ex.: guerra, azul, sofrimento, religioso")
                send = st.form_submit_button("Salvar tag", use_container_width=True)
                if send:
                    if not tag_text.strip():
                        st.error("Digite uma tag.")
                    else:
                        record = save_tag(st.session_state["user_id"], obra["id"], tag_text)
                        if record.get("correction_suggestions"):
                            st.warning("Sugestões ortográficas: " + ", ".join(record["correction_suggestions"]))
                        st.success(f"Tag '{tag_text}' registrada com status bruto.")
                        st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────
# ADMIN
# ──────────────────────────────────────────────────────────────────────
def show_admin() -> None:
    st.markdown("### Área administrativa")
    if not st.session_state.get("admin_logged_in", False):
        with st.form("login_admin"):
            c1, c2 = st.columns(2)
            with c1:
                username = st.text_input("Usuário")
            with c2:
                password = st.text_input("Senha", type="password")
            submit = st.form_submit_button("Entrar", use_container_width=True)
            if submit:
                if check_login(username, password):
                    st.session_state["admin_logged_in"] = True
                    st.session_state["admin_username"] = username
                    st.success("Login realizado.")
                    st.rerun()
                else:
                    st.error("Credenciais inválidas.")
        return

    st.success(f"Conectado como {st.session_state.get('admin_username', 'admin')}")
    tabs = st.tabs([
        "Painel geral",
        "Ontologias",
        "Validação de tags",
        "Grafo analítico",
        "Metadados e open data",
        "Obras",
        "Auditoria",
    ])
    with tabs[0]:
        tab_dashboard()
    with tabs[1]:
        tab_ontologies()
    with tabs[2]:
        tab_tag_validation()
    with tabs[3]:
        tab_graph_analysis()
    with tabs[4]:
        tab_open_data_and_metadata()
    with tabs[5]:
        tab_works_admin()
    with tabs[6]:
        tab_audit()
    if st.button("Sair da administração", use_container_width=True):
        st.session_state["admin_logged_in"] = False
        st.rerun()


def tab_dashboard() -> None:
    tag_df = load_tags_df()
    users_df = load_users_df()
    ont_df = load_ontologies_df()
    events_df = load_events_df()
    works = load_obras()

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: card("Tags totais", len(tag_df), "com histórico e status")
    with c2: card("Tags únicas", tag_df["tag_normalized"].nunique() if not tag_df.empty else 0, "vocabulário")
    with c3: card("Participantes", users_df["user_id"].nunique() if not users_df.empty else 0, "questionários completos")
    with c4: card("Ontologias", len(ont_df), "grupos e termos")
    with c5: card("Eventos", len(events_df), "cadeia de auditoria")

    st.markdown("### Síntese analítica")
    c1, c2 = st.columns(2)
    with c1:
        if not tag_df.empty:
            st.markdown("**Status das tags**")
            st.bar_chart(tag_df["status"].fillna("Sem status").value_counts())
        else:
            st.info("Sem tags para analisar.")
    with c2:
        if not tag_df.empty:
            st.markdown("**Grupos semânticos**")
            st.bar_chart(tag_df["ontology_group"].fillna("Sem classificação").value_counts().head(15))
        else:
            st.info("Sem grupos calculados.")

    st.markdown("### Familiaridade e produção de tags")
    if not tag_df.empty:
        fam = tag_df.groupby("familiaridade").agg(Tags=("id", "count"), Tags_unicas=("tag_normalized", "nunique")).reset_index()
        st.dataframe(fam, use_container_width=True, hide_index=True)
        st.bar_chart(fam.set_index("familiaridade")["Tags"])
    else:
        st.info("Ainda não há dados suficientes.")

    st.markdown("### Cobertura do acervo")
    works_df = pd.DataFrame(works)
    if not works_df.empty:
        coverage = tag_df.groupby("obra_id").size().reset_index(name="tags") if not tag_df.empty else pd.DataFrame(columns=["obra_id", "tags"])
        merged = works_df.merge(coverage, how="left", left_on="id", right_on="obra_id").fillna({"tags": 0})
        st.dataframe(merged[["id", "titulo", "artista", "ano", "tags"]], use_container_width=True, hide_index=True)


def tab_ontologies() -> None:
    ont_df = load_ontologies_df()
    st.markdown("### Ontologias predefinidas e administráveis")
    coverage_df = ontology_coverage_df()
    if not coverage_df.empty:
        st.dataframe(coverage_df, use_container_width=True, hide_index=True)
        st.bar_chart(coverage_df.set_index("Ontologia")["Tags ligadas"])

    st.markdown("### Criar nova ontologia")
    with st.form("create_ontology_form"):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("Nome da ontologia")
            description = st.text_area("Descrição")
        with c2:
            terms_text = st.text_area("Termos pré-marcados", placeholder="Separe por vírgula, ponto e vírgula ou quebra de linha")
        submitted = st.form_submit_button("Criar ontologia", use_container_width=True)
        if submitted:
            if not name.strip() or not terms_text.strip():
                st.error("Informe nome e termos.")
            else:
                create_ontology(name, description, terms_text, st.session_state.get("admin_username", "admin"))
                st.success("Ontologia criada.")
                st.rerun()

    st.markdown("### Editar ontologia existente")
    if ont_df.empty:
        st.info("Nenhuma ontologia cadastrada.")
        return
    options = {f"{row['id']} · {row['name']}": row["id"] for _, row in ont_df.iterrows()}
    selected_label = st.selectbox("Selecione a ontologia", list(options.keys()))
    selected_id = options[selected_label]
    selected = ont_df[ont_df["id"].astype(int) == int(selected_id)].iloc[0].to_dict()
    with st.form("edit_ontology_form"):
        edit_name = st.text_input("Nome", value=selected["name"])
        edit_description = st.text_area("Descrição", value=selected.get("description", ""))
        edit_terms = st.text_area("Termos", value=", ".join(selected.get("terms", []) if isinstance(selected.get("terms"), list) else []))
        edit_status = st.selectbox("Status", TAG_STATUSES, index=TAG_STATUSES.index(selected.get("status", "publicado")) if selected.get("status", "publicado") in TAG_STATUSES else 4)
        update = st.form_submit_button("Salvar alterações", use_container_width=True)
        if update:
            update_ontology(
                selected_id,
                {
                    "name": edit_name,
                    "slug": slugify(edit_name),
                    "description": edit_description,
                    "terms": [normalize_text(t) for t in re.split(r"[,;\n]", edit_terms) if t.strip()],
                    "status": edit_status,
                },
                st.session_state.get("admin_username", "admin"),
            )
            st.success("Ontologia atualizada.")
            st.rerun()


def validation_dataframe() -> pd.DataFrame:
    tag_df = load_tags_df().copy()
    if tag_df.empty:
        return tag_df
    works = {w["id"]: w["titulo"] for w in load_obras()}
    tag_df["Obra"] = tag_df["obra_id"].map(works)
    tag_df["Sugestões ortográficas"] = tag_df["tag_original"].apply(lambda x: ", ".join(suggest_corrections(str(x))))
    tag_df["Grupo sugerido"] = tag_df["tag_original"].apply(semantic_group_from_tag)
    return tag_df


def tab_tag_validation() -> None:
    tag_df = validation_dataframe()
    st.markdown("### Validação administrativa das tags")
    if tag_df.empty:
        st.info("Nenhuma tag cadastrada.")
        return
    c1, c2, c3 = st.columns(3)
    with c1:
        status_filter = st.selectbox("Filtrar por status", ["Todos"] + TAG_STATUSES)
    with c2:
        fam_options = ["Todas"] + sorted(tag_df["familiaridade"].fillna("Não informado").astype(str).unique().tolist())
        fam_filter = st.selectbox("Filtrar por familiaridade", fam_options)
    with c3:
        group_options = ["Todos"] + sorted(tag_df["ontology_group"].fillna("Sem classificação").astype(str).unique().tolist())
        group_filter = st.selectbox("Filtrar por grupo", group_options)

    filtered = tag_df.copy()
    if status_filter != "Todos":
        filtered = filtered[filtered["status"].fillna("") == status_filter]
    if fam_filter != "Todas":
        filtered = filtered[filtered["familiaridade"].fillna("Não informado") == fam_filter]
    if group_filter != "Todos":
        filtered = filtered[filtered["ontology_group"].fillna("Sem classificação") == group_filter]

    display_cols = [
        "id", "Obra", "tag_original", "tag_normalized", "status", "Grupo sugerido",
        "ontology_group", "familiaridade", "Sugestões ortográficas", "created_at"
    ]
    st.dataframe(filtered[display_cols], use_container_width=True, hide_index=True)

    tag_options = {f"{int(row['id'])} · {row['tag_original']} · {row['Obra']}": int(row["id"]) for _, row in filtered.iterrows()}
    if not tag_options:
        st.warning("Nenhuma tag atende aos filtros.")
        return

    selected_label = st.selectbox("Selecione uma tag para revisar", list(tag_options.keys()))
    tag_id = tag_options[selected_label]
    selected = filtered[filtered["id"].astype(int) == int(tag_id)].iloc[0].to_dict()
    ont_df = load_ontologies_df()
    ont_names = ["Sem classificação"] + sorted(ont_df["name"].dropna().astype(str).tolist())
    default_group = selected.get("ontology_group") if selected.get("ontology_group") in ont_names else selected.get("Grupo sugerido", "Sem classificação")
    if default_group not in ont_names:
        default_group = "Sem classificação"

    with st.form("validate_tag_form"):
        corrected = st.text_input("Forma corrigida", value=selected.get("tag_original", ""))
        chosen_status = st.selectbox("Novo status", TAG_STATUSES, index=TAG_STATUSES.index(selected.get("status", "bruto")) if selected.get("status", "bruto") in TAG_STATUSES else 0)
        chosen_group = st.selectbox("Grupo ontológico", ont_names, index=ont_names.index(default_group))
        notes = st.text_area("Notas curatoriais / correção humana", value=selected.get("notes", ""))
        submit = st.form_submit_button("Aplicar validação", use_container_width=True)
        if submit:
            updates = {
                "tag_original": corrected.strip(),
                "tag_normalized": normalize_text(corrected),
                "status": chosen_status,
                "ontology_group": chosen_group,
                "ontology_term": infer_ontology_groups(corrected)[0][1] if infer_ontology_groups(corrected) else "",
                "validated_by": st.session_state.get("admin_username", "admin"),
                "validated_at": now_iso(),
                "notes": notes.strip(),
                "origin": "humano",
                "automatic": False,
                "correction_suggestions": suggest_corrections(corrected),
            }
            update_tag_record(tag_id, updates, st.session_state.get("admin_username", "admin"), action="human_override")
            st.success("Tag revisada sem apagar o histórico anterior.")
            st.rerun()

    st.markdown("### Revisão automática sugerida")
    risky = filtered[filtered["Sugestões ortográficas"].astype(str) != ""]
    if risky.empty:
        st.info("Nenhuma sugestão ortográfica pendente.")
    else:
        st.dataframe(risky[["id", "tag_original", "Sugestões ortográficas", "Grupo sugerido", "familiaridade"]], use_container_width=True, hide_index=True)


def tab_graph_analysis() -> None:
    st.markdown("### Grafo de análise dos dados coletados")
    tag_df = load_tags_df()
    if tag_df.empty:
        st.info("Cadastre tags para construir o grafo.")
        return
    familiaridade_options = ["Todas"] + sorted(tag_df["familiaridade"].fillna("Não informado").astype(str).unique().tolist())
    familiaridade_filter = st.selectbox("Separar por familiaridade", familiaridade_options)
    graph, edge_df = build_graph(familiaridade_filter)
    c1, c2, c3 = st.columns(3)
    with c1: card("Nós", graph.number_of_nodes(), "obras, tags e ontologias")
    with c2: card("Arestas", graph.number_of_edges(), "relações e coocorrências")
    with c3: card("Familiaridade ativa", familiaridade_filter, "filtro do grafo")

    fig = plot_network(graph)
    if fig is not None:
        st.plotly_chart(fig, use_container_width=True)
    if not edge_df.empty:
        st.markdown("### Relações do grafo")
        st.dataframe(edge_df, use_container_width=True, hide_index=True)


def build_open_data_bundle() -> bytes:
    tag_df = load_tags_df()
    users_df = load_users_df()
    ont_df = load_ontologies_df()
    events_df = load_events_df()
    versions_df = load_versions_df()
    relations_df = load_relations_df()
    works_df = pd.DataFrame(load_obras())
    metadata = load_json(INSTITUTION_FILE, default_institution_metadata())
    analytics = compute_analytics_summary()

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("obras.json", works_df.to_json(orient="records", force_ascii=False, indent=2))
        archive.writestr("tags.json", tag_df.to_json(orient="records", force_ascii=False, indent=2))
        archive.writestr("usuarios.json", users_df.to_json(orient="records", force_ascii=False, indent=2))
        archive.writestr("ontologias.json", ont_df.to_json(orient="records", force_ascii=False, indent=2))
        archive.writestr("relations.json", relations_df.to_json(orient="records", force_ascii=False, indent=2))
        archive.writestr("eventos_auditoria.json", events_df.to_json(orient="records", force_ascii=False, indent=2))
        archive.writestr("versionamento.json", versions_df.to_json(orient="records", force_ascii=False, indent=2))
        archive.writestr("metadados_institucionais.json", json.dumps(metadata, ensure_ascii=False, indent=2))
        archive.writestr("analytics_summary.json", json.dumps(analytics, ensure_ascii=False, indent=2))
        archive.writestr("tags.csv", tag_df.to_csv(index=False))
        archive.writestr("eventos_auditoria.csv", events_df.to_csv(index=False))
        archive.writestr("ontologias.csv", ont_df.to_csv(index=False))
    return buffer.getvalue()


def tab_open_data_and_metadata() -> None:
    st.markdown("### Metadados institucionais conectados")
    metadata = load_json(INSTITUTION_FILE, default_institution_metadata())
    with st.form("institution_form"):
        c1, c2 = st.columns(2)
        with c1:
            instituicao = st.text_input("Instituição", value=metadata.get("instituicao", ""))
            sigla = st.text_input("Sigla", value=metadata.get("sigla", ""))
            responsavel = st.text_input("Responsável", value=metadata.get("responsavel", ""))
        with c2:
            politica = st.text_area("Política de dados", value=metadata.get("politica_dados", ""), height=150)
            padroes = st.text_area("Padrões e vocabulários", value=", ".join(metadata.get("padroes", [])))
            colecoes = st.text_area("Coleções", value=", ".join(metadata.get("colecoes", [])))
        save = st.form_submit_button("Salvar metadados institucionais", use_container_width=True)
        if save:
            update_institution_metadata(
                {
                    "instituicao": instituicao,
                    "sigla": sigla,
                    "responsavel": responsavel,
                    "politica_dados": politica,
                    "padroes": [item.strip() for item in padroes.split(",") if item.strip()],
                    "colecoes": [item.strip() for item in colecoes.split(",") if item.strip()],
                    "ultima_atualizacao": now_iso(),
                },
                st.session_state.get("admin_username", "admin"),
            )
            st.success("Metadados institucionais atualizados.")
            st.rerun()

    st.markdown("### Registro open data")
    summary = compute_analytics_summary()
    st.json(summary)
    bundle = build_open_data_bundle()
    bundle_hash = hashlib.sha256(bundle).hexdigest()
    c1, c2 = st.columns(2)
    with c1:
        st.download_button(
            "Baixar pacote open data (.zip)",
            data=bundle,
            file_name=f"open_data_folksonomia_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
            mime="application/zip",
            use_container_width=True,
        )
    with c2:
        with st.form("register_share_form"):
            destination = st.text_input("Destino do compartilhamento", placeholder="Ex.: equipe interna, laboratório, repositório")
            note = st.text_input("Observação de circulação", placeholder="Ex.: open data institucional")
            submit = st.form_submit_button("Registrar compartilhamento / exportação", use_container_width=True)
            if submit:
                register_export(st.session_state.get("admin_username", "admin"), "open_data_bundle", destination or "interno", note or "sem nota", bundle_hash)
                st.success("Trilha de circulação registrada na auditoria.")
                st.rerun()
    st.caption(f"Hash atual do pacote open data: {bundle_hash}")


def tab_works_admin() -> None:
    works = load_obras()
    st.markdown("### Gestão de obras")
    works_df = pd.DataFrame(works)
    if not works_df.empty:
        st.dataframe(works_df[["id", "titulo", "artista", "ano", "imagem"]], use_container_width=True, hide_index=True)

    st.markdown("### Cadastrar nova obra")
    with st.form("add_work_form"):
        c1, c2 = st.columns(2)
        with c1:
            titulo = st.text_input("Título")
            artista = st.text_input("Artista")
            ano = st.text_input("Ano")
            imagem = st.text_input("URL da imagem")
        with c2:
            colecao = st.text_input("Coleção")
            origem = st.text_input("Origem")
            licenca = st.text_input("Licença")
        descricao = st.text_area("Descrição curatorial")
        audio_descricao = st.text_area("Audiodescrição detalhada")
        create = st.form_submit_button("Adicionar obra", use_container_width=True)
        if create:
            if not titulo.strip() or not imagem.strip():
                st.error("Título e imagem são obrigatórios.")
            else:
                add_work(
                    {
                        "titulo": titulo,
                        "artista": artista,
                        "ano": ano,
                        "imagem": imagem,
                        "descricao": descricao,
                        "audio_descricao": audio_descricao,
                        "colecao": colecao,
                        "origem": origem,
                        "licenca": licenca,
                    },
                    st.session_state.get("admin_username", "admin"),
                )
                st.success("Obra adicionada.")
                st.rerun()

    st.markdown("### Excluir obra")
    if works:
        options = {f"{work['id']} · {work['titulo']}": work["id"] for work in works}
        choice = st.selectbox("Selecione a obra para excluir", list(options.keys()))
        if st.button("Excluir obra selecionada", use_container_width=True):
            ok = delete_work(options[choice], st.session_state.get("admin_username", "admin"))
            if ok:
                st.success("Obra excluída com registro de auditoria.")
                st.rerun()
            else:
                st.error("Não foi possível excluir a obra.")


def tab_audit() -> None:
    st.markdown("### Camada de tráfego, auditoria e arquivo semântico")
    events_df = load_events_df()
    versions_df = load_versions_df()
    exports_df = pd.DataFrame(load_json(EXPORTS_FILE, []))

    c1, c2, c3, c4 = st.columns(4)
    with c1: card("Eventos auditados", len(events_df), "log imutável por evento")
    with c2: card("Versões registradas", len(versions_df), "versionamento de metadados")
    with c3: card("Exportações", len(exports_df), "trilha de circulação")
    with c4:
        integrity = "Íntegra"
        if not events_df.empty:
            integrity = "Íntegra" if events_df["previous_event_hash"].isna().sum() <= 1 else "Verificar"
        card("Cadeia", integrity, "hash encadeado")

    st.markdown("### Últimos eventos")
    if events_df.empty:
        st.info("Nenhum evento registrado ainda.")
    else:
        for _, row in events_df.sort_values("id", ascending=False).head(30).iterrows():
            st.markdown(
                f"""
                <div class='audit-row'>
                    <strong>#{int(row['id'])}</strong> · {row['timestamp']} · {row['action']} · {row['entity_type']}:{row['entity_id']}
                    <br><span class='muted'>ator: {row['actor']} · origem: {row.get('origin', '')} · proveniência: {row.get('provenance', '')} · hash: {row.get('event_hash', '')[:18]}...</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        st.dataframe(events_df.sort_values("id", ascending=False), use_container_width=True, hide_index=True)

    st.markdown("### Histórico de versões")
    if versions_df.empty:
        st.info("Nenhuma versão registrada.")
    else:
        st.dataframe(versions_df.sort_values("id", ascending=False), use_container_width=True, hide_index=True)

    if not exports_df.empty:
        st.markdown("### Exportações e circulação")
        st.dataframe(exports_df.sort_values("id", ascending=False), use_container_width=True, hide_index=True)


# ──────────────────────────────────────────────────────────────────────
# APP PRINCIPAL
# ──────────────────────────────────────────────────────────────────────
def main() -> None:
    bootstrap_files()
    ensure_accessibility_session()
    load_css()

    st.markdown("<div class='app-wrap'>", unsafe_allow_html=True)
    render_accessibility_controls()

    if st.session_state.get("step") != "completed":
        show_intro()
    else:
        st.markdown(
            f"""
            <div class='hero'>
                <h1>Folksonomia Digital</h1>
                <p>
                    Usuário anônimo atual: <strong>{st.session_state.get('animal_name')}</strong>.
                    O sistema registra eventos encadeados por hash, mantém versões anteriores,
                    marca relações automáticas da IA e preserva correções humanas sem apagar o histórico.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        public_tab, admin_tab = st.tabs(["Explorar obras", "Área administrativa"])
        with public_tab:
            show_obras()
        with admin_tab:
            show_admin()
    st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
