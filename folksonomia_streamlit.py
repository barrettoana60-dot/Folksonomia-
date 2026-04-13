from __future__ import annotations

import base64
import copy
import hashlib
import json
import math
import os
import random
import re
import textwrap
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
import streamlit as st

try:
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except Exception:
    PLOTLY_AVAILABLE = False
    go = None

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    REPORTLAB_AVAILABLE = True
except Exception:
    REPORTLAB_AVAILABLE = False

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    SKLEARN_AVAILABLE = True
except Exception:
    SKLEARN_AVAILABLE = False


st.set_page_config(page_title="folksonomia", page_icon="🏛️", layout="wide", initial_sidebar_state="collapsed")

APP_TITLE = "folksonomia"
APP_ROOT = Path("data_folksonomia_nlu")
WORKS_FILE = APP_ROOT / "works.json"
USERS_FILE = APP_ROOT / "users.json"
TAGS_FILE = APP_ROOT / "tags.json"
VALIDATIONS_FILE = APP_ROOT / "validations.json"
SETTINGS_FILE = APP_ROOT / "settings.json"
ADMIN_FILE = APP_ROOT / "admin.json"
REPORT_FILE = APP_ROOT / "last_report.json"

ADMIN_USERNAME = "nugep239@"
ADMIN_PASSWORD = "Artemis289@"

ENTITY_CATEGORIES = [
    "pessoa",
    "lugar",
    "período",
    "material",
    "técnica",
    "tema",
    "instituição",
    "coleção",
    "conceito",
]

LEGACY_DIRS = [
    "data_folksonomia",
    "data_folksonomia_v2",
    "data_folksonomia_visual",
    "data_folksonomia_nlu",
    "data",
]


DEFAULT_WORKS = [
    {
        "id": 1,
        "title": "Guernica",
        "artist": "Pablo Picasso",
        "year": "1937",
        "image": "https://upload.wikimedia.org/wikipedia/en/7/74/PicassoGuernica.jpg",
        "museum": "Museo Nacional Centro de Arte Reina Sofía",
        "collection": "Coleção Permanente",
        "place": "Espanha",
        "period": "modernismo do século XX",
        "technique": "óleo sobre tela",
        "material": "tela",
        "institutional_tags": ["guerra", "violência", "cavalo", "bomba", "modernismo", "espanha"],
        "external_refs": ["wikidata:Q175036", "dbpedia:Guernica_(Picasso)"],
        "description": "Grande composição de denúncia sobre a violência da guerra, com figuras humanas e animais fragmentadas.",
    },
    {
        "id": 2,
        "title": "A Noite Estrelada",
        "artist": "Vincent van Gogh",
        "year": "1889",
        "image": "https://upload.wikimedia.org/wikipedia/commons/e/ea/The_Starry_Night.jpg",
        "museum": "The Museum of Modern Art",
        "collection": "MoMA Collection",
        "place": "França",
        "period": "pós-impressionismo",
        "technique": "óleo sobre tela",
        "material": "tela",
        "institutional_tags": ["noite", "céu", "estrela", "aldeia", "pós-impressionismo", "paisagem"],
        "external_refs": ["wikidata:Q219831", "dbpedia:The_Starry_Night"],
        "description": "Paisagem noturna com céu em redemoinho, astros brilhantes e vila ao fundo.",
    },
    {
        "id": 3,
        "title": "Mona Lisa",
        "artist": "Leonardo da Vinci",
        "year": "1503",
        "image": "https://upload.wikimedia.org/wikipedia/commons/6/6a/Mona_Lisa.jpg",
        "museum": "Musée du Louvre",
        "collection": "Peintures",
        "place": "Itália",
        "period": "renascimento",
        "technique": "óleo sobre madeira",
        "material": "madeira",
        "institutional_tags": ["retrato", "renascimento", "mulher", "sorriso", "paisagem"],
        "external_refs": ["wikidata:Q12418", "dbpedia:Mona_Lisa"],
        "description": "Retrato feminino com expressão sutil e paisagem distante ao fundo.",
    },
    {
        "id": 4,
        "title": "O Grito",
        "artist": "Edvard Munch",
        "year": "1893",
        "image": "https://upload.wikimedia.org/wikipedia/commons/f/f4/The_Scream.jpg",
        "museum": "National Museum of Art, Architecture and Design",
        "collection": "Munch Collection",
        "place": "Noruega",
        "period": "simbolismo",
        "technique": "óleo, têmpera e pastel sobre cartão",
        "material": "cartão",
        "institutional_tags": ["angústia", "expressão", "ponte", "céu", "figura humana"],
        "external_refs": ["wikidata:Q471379", "dbpedia:The_Scream"],
        "description": "Figura central em forte expressão de desespero sobre uma ponte, com paisagem vibrante.",
    },
    {
        "id": 5,
        "title": "Operários",
        "artist": "Tarsila do Amaral",
        "year": "1933",
        "image": "https://upload.wikimedia.org/wikipedia/commons/4/4d/Tarsila_do_Amaral_-_Oper%C3%A1rios.jpg",
        "museum": "Palácio Boa Vista",
        "collection": "Acervo do Governo do Estado de São Paulo",
        "place": "Brasil",
        "period": "modernismo brasileiro",
        "technique": "óleo sobre tela",
        "material": "tela",
        "institutional_tags": ["trabalho", "industrialização", "rostos", "brasil", "modernismo"],
        "external_refs": ["wikidata:Q7085918"],
        "description": "Conjunto de rostos de trabalhadores diante de fábricas, discutindo diversidade e industrialização.",
    },
    {
        "id": 6,
        "title": "Abaporu",
        "artist": "Tarsila do Amaral",
        "year": "1928",
        "image": "https://upload.wikimedia.org/wikipedia/en/0/0f/Tarsila_do_Amaral%2C_Abaporu%2C_1928.jpg",
        "museum": "Museo de Arte Latinoamericano de Buenos Aires",
        "collection": "Coleção MALBA",
        "place": "Brasil",
        "period": "antropofagia",
        "technique": "óleo sobre tela",
        "material": "tela",
        "institutional_tags": ["antropofagia", "corpo", "sol", "cacto", "modernismo brasileiro"],
        "external_refs": ["wikidata:Q4662581"],
        "description": "Figura solitária de formas exageradas ao lado de cacto e sol intenso.",
    },
]

SEED_EXAMPLES = {
    "pessoa": ["homem", "mulher", "rosto", "trabalhador", "pessoa", "figura humana", "mãe", "criança"],
    "lugar": ["cidade", "vila", "ponte", "espanha", "brasil", "frança", "italia", "italía", "rio", "paisagem"],
    "período": ["renascimento", "modernismo", "pós-impressionismo", "simbolismo", "século xx", "antropofagia"],
    "material": ["madeira", "tela", "cartão", "papel", "ouro", "bronze", "pedra"],
    "técnica": ["óleo", "têmpera", "pastel", "xilogravura", "escultura", "gravura"],
    "tema": ["guerra", "noite", "trabalho", "angústia", "religião", "violência", "paisagem", "retrato", "céu"],
    "instituição": ["museu", "moma", "louvre", "reina sofía", "malba", "coleção"],
    "coleção": ["coleção permanente", "acervo", "peintures", "collection"],
    "conceito": ["memória", "identidade", "representação", "conflito", "devoção"],
}


# =====================
# UTILITÁRIOS
# =====================

def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def slugify(text: str) -> str:
    text = text or ""
    text = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    return text or "item"


def normalize_text(text: Any) -> str:
    text = "" if text is None else str(text)
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"\s+", " ", text.lower()).strip()
    return text


def tokenize(text: Any) -> List[str]:
    base = normalize_text(text)
    return [tok for tok in re.split(r"[^a-z0-9]+", base) if tok]


def unique_preserve(seq: Iterable[Any]) -> List[Any]:
    seen = set()
    out = []
    for item in seq:
        marker = json.dumps(item, sort_keys=True, ensure_ascii=False) if isinstance(item, (dict, list)) else item
        if marker not in seen:
            seen.add(marker)
            out.append(item)
    return out


def seq_sim(a: str, b: str) -> float:
    return SequenceMatcher(None, normalize_text(a), normalize_text(b)).ratio()


def trigram_jaccard(a: str, b: str) -> float:
    a = normalize_text(a)
    b = normalize_text(b)
    if not a or not b:
        return 0.0
    def trigrams(s: str) -> set[str]:
        if len(s) < 3:
            return {s}
        return {s[i:i + 3] for i in range(len(s) - 2)}
    ta, tb = trigrams(a), trigrams(b)
    denom = len(ta | tb)
    return len(ta & tb) / denom if denom else 0.0


def combined_similarity(a: str, b: str) -> float:
    if normalize_text(a) == normalize_text(b):
        return 1.0
    sa = set(tokenize(a))
    sb = set(tokenize(b))
    word_jacc = len(sa & sb) / len(sa | sb) if (sa | sb) else 0.0
    return 0.45 * seq_sim(a, b) + 0.35 * trigram_jaccard(a, b) + 0.20 * word_jacc


def human_count(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def tiny_text(text: str) -> str:
    return textwrap.shorten(text or "", width=120, placeholder="…")


def default_settings() -> Dict[str, Any]:
    return {
        "font_scale": 1.0,
        "high_contrast": False,
        "simple_text": False,
        "avatar_enabled": True,
    }


# =====================
# DADOS
# =====================

class DataStore:
    def __init__(self) -> None:
        APP_ROOT.mkdir(parents=True, exist_ok=True)
        self.ensure_admin()
        self.bootstrap_defaults()
        self.migrate_legacy_if_needed()

    def _load_json(self, path: Path, default: Any) -> Any:
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                return copy.deepcopy(default)
        return copy.deepcopy(default)

    def _save_json(self, path: Path, data: Any) -> None:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def bootstrap_defaults(self) -> None:
        if not WORKS_FILE.exists():
            self._save_json(WORKS_FILE, DEFAULT_WORKS)
        if not USERS_FILE.exists():
            self._save_json(USERS_FILE, [])
        if not TAGS_FILE.exists():
            self._save_json(TAGS_FILE, [])
        if not VALIDATIONS_FILE.exists():
            self._save_json(VALIDATIONS_FILE, [])
        if not SETTINGS_FILE.exists():
            self._save_json(SETTINGS_FILE, default_settings())
        if not REPORT_FILE.exists():
            self._save_json(REPORT_FILE, {})

    def ensure_admin(self) -> None:
        default_admin = [{"username": ADMIN_USERNAME, "password": hash_password(ADMIN_PASSWORD)}]
        if not ADMIN_FILE.exists():
            self._save_json(ADMIN_FILE, default_admin)
            return
        admins = self._load_json(ADMIN_FILE, default_admin)
        if not admins:
            self._save_json(ADMIN_FILE, default_admin)

    def migrate_legacy_if_needed(self) -> None:
        # Migração leve: se estiver vazio, tenta importar dados antigos compatíveis.
        works = self.works()
        if len(works) > 0 and self.tags():
            return
        imported_users: List[dict] = []
        imported_tags: List[dict] = []
        imported_validations: List[dict] = []
        for dirname in LEGACY_DIRS:
            root = Path(dirname)
            if not root.exists() or root.resolve() == APP_ROOT.resolve():
                continue
            for fname, bucket in [
                ("users.json", imported_users),
                ("tags.json", imported_tags),
                ("validations.json", imported_validations),
            ]:
                fpath = root / fname
                if fpath.exists():
                    try:
                        bucket.extend(json.loads(fpath.read_text(encoding="utf-8")))
                    except Exception:
                        pass
        if imported_users and not self.users():
            cleaned_users = []
            for idx, user in enumerate(imported_users, start=1):
                cleaned_users.append({
                    "id": user.get("id") or user.get("user_id") or f"u{idx}",
                    "q1": user.get("q1", ""),
                    "q2": user.get("q2", ""),
                    "q3": user.get("q3", ""),
                    "timestamp": user.get("timestamp", now_str()),
                })
            self._save_json(USERS_FILE, unique_preserve(cleaned_users))
        if imported_tags and not self.tags():
            cleaned_tags = []
            for idx, tag in enumerate(imported_tags, start=1):
                cleaned_tags.append({
                    "id": tag.get("id") or idx,
                    "user_id": tag.get("user_id") or tag.get("uid") or "publico",
                    "work_id": tag.get("work_id") or tag.get("obra_id") or tag.get("item_id") or 1,
                    "tag": tag.get("tag", "").strip(),
                    "timestamp": tag.get("timestamp", now_str()),
                })
            cleaned_tags = [t for t in cleaned_tags if t["tag"]]
            self._save_json(TAGS_FILE, unique_preserve(cleaned_tags))
        if imported_validations and not self.validations():
            cleaned_vals = []
            for idx, val in enumerate(imported_validations, start=1):
                cleaned_vals.append({
                    "id": val.get("id") or idx,
                    "tag_text": val.get("tag_text") or val.get("tag") or "",
                    "work_id": val.get("work_id") or val.get("obra_id") or 1,
                    "category": val.get("category") or val.get("validated_category") or "",
                    "concept": val.get("concept") or val.get("reconciled_concept") or "",
                    "decision": val.get("decision") or "approved",
                    "notes": val.get("notes") or val.get("curatorial_notes") or "",
                    "timestamp": val.get("timestamp") or now_str(),
                })
            cleaned_vals = [v for v in cleaned_vals if v["tag_text"]]
            self._save_json(VALIDATIONS_FILE, unique_preserve(cleaned_vals))

    def works(self) -> List[dict]:
        works = self._load_json(WORKS_FILE, DEFAULT_WORKS)
        fixed = []
        for idx, work in enumerate(works, start=1):
            fixed.append({
                "id": int(work.get("id") or idx),
                "title": work.get("title") or work.get("titulo") or f"Obra {idx}",
                "artist": work.get("artist") or work.get("artista") or "",
                "year": str(work.get("year") or work.get("ano") or ""),
                "image": work.get("image") or work.get("imagem") or "",
                "museum": work.get("museum") or work.get("museu") or "",
                "collection": work.get("collection") or work.get("colecao") or "",
                "place": work.get("place") or work.get("lugar") or "",
                "period": work.get("period") or work.get("periodo") or "",
                "technique": work.get("technique") or work.get("tecnica") or "",
                "material": work.get("material") or "",
                "institutional_tags": work.get("institutional_tags") or work.get("tags_institucionais") or [],
                "external_refs": work.get("external_refs") or work.get("referencias_externas") or [],
                "description": work.get("description") or work.get("descricao") or "",
            })
        return fixed

    def save_works(self, works: List[dict]) -> None:
        self._save_json(WORKS_FILE, works)

    def users(self) -> List[dict]:
        users = self._load_json(USERS_FILE, [])
        fixed = []
        for idx, user in enumerate(users, start=1):
            fixed.append({
                "id": user.get("id") or user.get("user_id") or f"u{idx}",
                "q1": user.get("q1", ""),
                "q2": user.get("q2", ""),
                "q3": user.get("q3", ""),
                "timestamp": user.get("timestamp", now_str()),
            })
        return fixed

    def save_users(self, users: List[dict]) -> None:
        self._save_json(USERS_FILE, users)

    def tags(self) -> List[dict]:
        tags = self._load_json(TAGS_FILE, [])
        fixed = []
        for idx, tag in enumerate(tags, start=1):
            value = str(tag.get("tag", "")).strip()
            if not value:
                continue
            fixed.append({
                "id": tag.get("id") or idx,
                "user_id": tag.get("user_id") or tag.get("uid") or "publico",
                "work_id": int(tag.get("work_id") or tag.get("obra_id") or 1),
                "tag": value,
                "timestamp": tag.get("timestamp", now_str()),
            })
        return fixed

    def save_tags(self, tags: List[dict]) -> None:
        self._save_json(TAGS_FILE, tags)

    def validations(self) -> List[dict]:
        vals = self._load_json(VALIDATIONS_FILE, [])
        fixed = []
        for idx, val in enumerate(vals, start=1):
            tag_text = str(val.get("tag_text") or val.get("tag") or "").strip()
            if not tag_text:
                continue
            fixed.append({
                "id": val.get("id") or idx,
                "tag_text": tag_text,
                "work_id": int(val.get("work_id") or 1),
                "category": val.get("category") or val.get("validated_category") or "",
                "concept": val.get("concept") or val.get("reconciled_concept") or "",
                "decision": val.get("decision") or "approved",
                "notes": val.get("notes") or val.get("curatorial_notes") or "",
                "timestamp": val.get("timestamp") or now_str(),
            })
        return fixed

    def save_validations(self, vals: List[dict]) -> None:
        self._save_json(VALIDATIONS_FILE, vals)

    def settings(self) -> Dict[str, Any]:
        settings = self._load_json(SETTINGS_FILE, default_settings())
        return {**default_settings(), **settings}

    def save_settings(self, settings: Dict[str, Any]) -> None:
        merged = {**default_settings(), **settings}
        self._save_json(SETTINGS_FILE, merged)

    def update_report_cache(self, data: Dict[str, Any]) -> None:
        self._save_json(REPORT_FILE, data)

    def report_cache(self) -> Dict[str, Any]:
        return self._load_json(REPORT_FILE, {})

    def check_admin(self, username: str, password: str) -> bool:
        admins = self._load_json(ADMIN_FILE, [])
        password_hash = hash_password(password)
        for admin in admins:
            if admin.get("username") == username and admin.get("password") == password_hash:
                return True
        return False

    def add_user_response(self, q1: str, q2: str, q3: str) -> str:
        users = self.users()
        uid = f"u{len(users) + 1}-{slugify(now_str())}"
        users.append({"id": uid, "q1": q1, "q2": q2, "q3": q3, "timestamp": now_str()})
        self.save_users(users)
        return uid

    def add_tag(self, user_id: str, work_id: int, tag_text: str) -> None:
        tags = self.tags()
        tags.append({
            "id": len(tags) + 1,
            "user_id": user_id,
            "work_id": int(work_id),
            "tag": tag_text.strip(),
            "timestamp": now_str(),
        })
        self.save_tags(tags)

    def add_validation(self, payload: Dict[str, Any]) -> None:
        vals = self.validations()
        vals.append({
            "id": len(vals) + 1,
            "tag_text": payload.get("tag_text", "").strip(),
            "work_id": int(payload.get("work_id") or 1),
            "category": payload.get("category", ""),
            "concept": payload.get("concept", ""),
            "decision": payload.get("decision", "approved"),
            "notes": payload.get("notes", ""),
            "timestamp": now_str(),
        })
        self.save_validations(vals)

    def add_work(self, work: Dict[str, Any]) -> None:
        works = self.works()
        next_id = max([w["id"] for w in works], default=0) + 1
        work = {**work, "id": next_id}
        works.append(work)
        self.save_works(works)

    def remove_work(self, work_id: int) -> None:
        works = [w for w in self.works() if int(w["id"]) != int(work_id)]
        self.save_works(works)
        self.save_tags([t for t in self.tags() if int(t["work_id"]) != int(work_id)])
        self.save_validations([v for v in self.validations() if int(v["work_id"]) != int(work_id)])


# =====================
# ESTILO
# =====================

def inject_css(settings: Dict[str, Any]) -> None:
    font_scale = float(settings.get("font_scale", 1.0))
    body_bg = "#efefef" if not settings.get("high_contrast") else "#e7e7e7"
    card_bg = "rgba(255,255,255,0.28)" if not settings.get("high_contrast") else "rgba(255,255,255,0.36)"
    border_color = "rgba(255,255,255,0.36)"
    text_color = "#1c1c1f"
    secondary = "#4b4b52"
    input_bg = "rgba(255,255,255,0.72)"

    st.markdown(
        f"""
        <style>
        :root {{
            --font-scale: {font_scale};
            --bg: {body_bg};
            --card: {card_bg};
            --border: {border_color};
            --text: {text_color};
            --secondary: {secondary};
            --accent: #0d1b34;
            --input: {input_bg};
        }}
        html, body, [class*="css"]  {{font-family: "Times New Roman", Georgia, serif !important;}}
        .stApp {{background: linear-gradient(180deg, #f2f2f2 0%, #ededed 100%); color: var(--text);}}
        #MainMenu, footer, header {{visibility: hidden;}}
        .block-container {{padding-top: 1rem; padding-bottom: 2rem; max-width: 1400px;}}
        .glass {{
            background: var(--card);
            backdrop-filter: blur(22px) saturate(150%);
            -webkit-backdrop-filter: blur(22px) saturate(150%);
            border: 1px solid var(--border);
            border-radius: 28px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.06);
        }}
        .hero-min {{padding: 0.2rem 0 0.6rem 0; margin-bottom: 0.8rem;}}
        .hero-title {{font-size: calc(3.2rem * var(--font-scale)); font-weight: 700; letter-spacing: -0.03em; color: var(--text); margin: 0;}}
        .hero-sub {{font-size: calc(1.05rem * var(--font-scale)); color: var(--secondary); margin-top: 0.2rem;}}
        .section-card {{padding: 1.2rem 1.4rem; margin-bottom: 1rem;}}
        .section-title {{font-size: calc(1.6rem * var(--font-scale)); font-weight: 700; margin: 0 0 .25rem 0; color: var(--text);}}
        .section-sub {{font-size: calc(1.0rem * var(--font-scale)); color: var(--secondary); margin: 0; line-height: 1.6;}}
        .mini-note {{font-size: calc(0.92rem * var(--font-scale)); color: var(--secondary); line-height: 1.55;}}
        .metric-card {{padding: 1rem 1.1rem; min-height: 126px;}}
        .metric-label {{font-size: calc(0.92rem * var(--font-scale)); letter-spacing: .16em; text-transform: uppercase; color: var(--secondary); margin-bottom: .75rem;}}
        .metric-value {{font-size: calc(2.4rem * var(--font-scale)); font-weight: 700; line-height: 1; color: var(--text);}}
        .metric-desc {{font-size: calc(0.95rem * var(--font-scale)); color: var(--secondary); margin-top: .75rem; line-height: 1.45;}}
        .works-grid-header {{display:flex; justify-content:space-between; align-items:center; gap:1rem; margin: 0.4rem 0 0.9rem 0;}}
        .works-grid-header h2 {{margin:0; font-size: calc(1.8rem * var(--font-scale)); color: var(--text);}}
        .works-grid-header p {{margin:0; color: var(--secondary); font-size: calc(0.98rem * var(--font-scale));}}
        .work-card {{padding: 0.85rem; margin-bottom: 1rem;}}
        .work-image-wrap {{position: relative; overflow: hidden; border-radius: 24px;}}
        .work-image-wrap img {{width: 100%; height: 260px; object-fit: cover; border-radius: 24px; transition: transform .28s ease;}}
        .work-image-wrap:hover img {{transform: scale(1.03);}}
        .work-action {{margin-top: .7rem;}}
        .own-tag-chip {{display:inline-block; padding: .22rem .68rem; border-radius: 999px; background: rgba(13,27,52,0.08); border:1px solid rgba(13,27,52,0.10); margin: .18rem .2rem 0 0; font-size: calc(0.9rem * var(--font-scale)); color: var(--accent);}}
        .flow-chip {{display:inline-block; padding: .32rem .72rem; border-radius: 999px; background: rgba(13,27,52,0.06); border:1px solid rgba(13,27,52,0.10); margin: .18rem .2rem 0 0; font-size: calc(0.92rem * var(--font-scale)); color: var(--text);}}
        .timeline-card {{padding: 1rem 1.1rem;}}
        .timeline-title {{font-size: calc(1.25rem * var(--font-scale)); font-weight: 700; color: var(--text); margin-bottom: .4rem;}}
        .timeline-list {{font-size: calc(0.98rem * var(--font-scale)); color: var(--secondary); line-height: 1.8;}}
        div[data-baseweb="input"] input, div[data-baseweb="textarea"] textarea, .stTextInput input, .stTextArea textarea {{
            background: var(--input) !important;
            color: #202126 !important;
            border-radius: 18px !important;
            border: 1px solid rgba(70,70,80,0.18) !important;
        }}
        .stTextInput input::placeholder, .stTextArea textarea::placeholder {{color: #555760 !important; opacity: .85 !important;}}
        .stSelectbox div[data-baseweb="select"] > div {{
            background: var(--input) !important;
            color: #202126 !important;
            border-radius: 18px !important;
            border: 1px solid rgba(70,70,80,0.18) !important;
        }}
        label, .stMarkdown p, .stMarkdown li, .stMarkdown span {{color: var(--text);}}
        .stButton button, .stDownloadButton button {{
            background: linear-gradient(180deg, #091225 0%, #0d1b34 100%) !important;
            color: #f0f2f7 !important;
            border-radius: 24px !important;
            border: 1px solid rgba(255,255,255,0.22) !important;
            padding: .68rem 1.1rem !important;
            font-size: calc(1rem * var(--font-scale)) !important;
            box-shadow: 0 8px 18px rgba(10,18,37,0.18) !important;
        }}
        .stButton button:hover, .stDownloadButton button:hover {{filter: brightness(1.06); transform: translateY(-1px);}}
        .admin-open button {{width:100%;}}
        .stTabs [data-baseweb="tab-list"] {{gap: 0.45rem; background: transparent;}}
        .stTabs [data-baseweb="tab"] {{
            background: rgba(255,255,255,0.42);
            border: 1px solid rgba(255,255,255,0.4);
            border-radius: 999px;
            color: var(--text);
            padding: .55rem .95rem;
        }}
        .stTabs [aria-selected="true"] {{background: rgba(13,27,52,0.10) !important; color: var(--accent) !important;}}
        .plain-card {{padding:1rem 1.1rem; margin-bottom: 1rem;}}
        .plain-card h4 {{margin:0 0 .35rem 0; color: var(--text); font-size: calc(1.15rem * var(--font-scale));}}
        .plain-card p {{margin:0; color: var(--secondary); font-size: calc(.98rem * var(--font-scale)); line-height: 1.65;}}
        .avatar-box {{display:flex; gap:1rem; align-items:center;}}
        .avatar-3d {{width:96px; height:120px; position:relative; transform-style: preserve-3d; animation: spinAvatar 7s linear infinite;}}
        .avatar-3d .part {{position:absolute; background: rgba(13,27,52,0.9); border:1px solid rgba(255,255,255,0.28);}}
        .avatar-head {{width:38px; height:38px; border-radius:50%; left:29px; top:0;}}
        .avatar-body {{width:52px; height:46px; border-radius:16px; left:22px; top:40px;}}
        .avatar-leg-l {{width:16px; height:34px; left:28px; top:88px; border-radius:12px;}}
        .avatar-leg-r {{width:16px; height:34px; left:52px; top:88px; border-radius:12px;}}
        .avatar-arm-l {{width:14px; height:34px; left:8px; top:48px; border-radius:12px; transform: rotate(18deg);}}
        .avatar-arm-r {{width:14px; height:34px; left:74px; top:48px; border-radius:12px; transform: rotate(-18deg);}}
        @keyframes spinAvatar {{from {{transform: rotateY(0deg);}} to {{transform: rotateY(360deg);}}}}
        .caption-muted {{font-size: calc(0.95rem * var(--font-scale)); color: var(--secondary); margin-top: .3rem;}}
        .hr-soft {{height:1px; background: rgba(200,200,210,0.45); margin: 1rem 0; border: none;}}
        .search-hit {{padding:.8rem 1rem; margin-bottom:.7rem;}}
        .search-hit-title {{font-weight:700; font-size: calc(1.12rem * var(--font-scale)); color: var(--text); margin-bottom:.28rem;}}
        .search-hit-body {{font-size: calc(0.95rem * var(--font-scale)); color: var(--secondary); line-height: 1.6;}}
        .validation-card {{padding:1rem 1rem; margin-bottom:1rem;}}
        .validation-tag {{font-size: calc(1.4rem * var(--font-scale)); font-weight:700; color: var(--text); margin-bottom:.2rem;}}
        .validation-meta {{font-size: calc(.98rem * var(--font-scale)); color: var(--secondary); line-height:1.65;}}
        .public-instruction {{font-size: calc(1rem * var(--font-scale)); color: var(--secondary); margin: .15rem 0 1rem 0;}}
        .small-helper {{font-size: calc(.9rem * var(--font-scale)); color: var(--secondary);}}
        .stDataFrame, .stTable {{background: rgba(255,255,255,0.35); border-radius: 22px; overflow:hidden;}}
        @media (max-width: 900px) {{
            .hero-title {{font-size: calc(2.8rem * var(--font-scale));}}
            .block-container {{padding-left: .7rem; padding-right: .7rem;}}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


# =====================
# NLU / MACHINE LEARNING
# =====================

def metadata_field_examples(store: DataStore) -> List[Dict[str, str]]:
    examples: List[Dict[str, str]] = []
    for work in store.works():
        mapping = {
            "pessoa": [work.get("artist", "")],
            "lugar": [work.get("place", "")],
            "período": [work.get("period", "")],
            "técnica": [work.get("technique", "")],
            "material": [work.get("material", "")],
            "instituição": [work.get("museum", "")],
            "coleção": [work.get("collection", "")],
            "tema": work.get("institutional_tags", []),
        }
        for category, values in mapping.items():
            for value in values:
                value = str(value).strip()
                if value:
                    examples.append({"text": value, "category": category, "origin": "metadata"})
    for category, values in SEED_EXAMPLES.items():
        for value in values:
            examples.append({"text": value, "category": category, "origin": "seed"})
    return unique_preserve(examples)


def build_learning_records(store: DataStore) -> pd.DataFrame:
    rows = []
    for ex in metadata_field_examples(store):
        rows.append({"text": ex["text"], "category": ex["category"], "origin": ex["origin"]})
    for val in store.validations():
        if val.get("decision") == "approved" and val.get("category"):
            rows.append({
                "text": val.get("tag_text", ""),
                "category": val.get("category", ""),
                "origin": "validation",
            })
            if val.get("concept"):
                rows.append({
                    "text": val.get("concept", ""),
                    "category": val.get("category", ""),
                    "origin": "concept",
                })
    if not rows:
        rows = [{"text": "obra", "category": "conceito", "origin": "seed"}]
    df = pd.DataFrame(rows)
    for col in ["text", "category", "origin"]:
        if col not in df.columns:
            df[col] = ""
    df["text"] = df["text"].astype(str)
    df["category"] = df["category"].astype(str)
    df["origin"] = df["origin"].astype(str)
    return df[df["text"].str.strip().astype(bool)].reset_index(drop=True)


class HeuristicNLU:
    def __init__(self, examples: pd.DataFrame):
        self.examples = examples
        self.by_category = defaultdict(list)
        for _, row in examples.iterrows():
            self.by_category[row["category"]].append(row["text"])

    def predict(self, text: str) -> Tuple[str, float, str]:
        raw = str(text).strip()
        norm = normalize_text(raw)
        if not norm:
            return "conceito", 0.0, "Sem conteúdo suficiente para classificação."
        best_cat = "conceito"
        best_score = 0.0
        best_hit = ""
        for category, values in self.by_category.items():
            for value in values[:120]:
                score = combined_similarity(norm, value)
                if value and normalize_text(value) in norm:
                    score = max(score, 0.86)
                if norm in normalize_text(value) and len(norm) >= 3:
                    score = max(score, 0.82)
                if score > best_score:
                    best_score = score
                    best_cat = category
                    best_hit = value
        for category, values in SEED_EXAMPLES.items():
            for value in values:
                if normalize_text(value) == norm:
                    return category, 0.96, f"Correspondência direta com vocabulário de referência: {value}."
        if best_score < 0.35:
            keyword_map = {
                "pessoa": ["homem", "mulher", "rosto", "pessoa", "trabalhador", "figura"],
                "lugar": ["cidade", "vila", "paisagem", "ponte", "espanha", "brasil", "franca", "italia"],
                "período": ["renascimento", "modernismo", "pos impressionismo", "simbolismo", "antropofagia"],
                "técnica": ["oleo", "tempera", "pastel", "gravura", "escultura"],
                "material": ["tela", "madeira", "cartao", "papel", "bronze", "pedra"],
                "tema": ["guerra", "angustia", "trabalho", "noite", "ceu", "violencia", "retrato"],
                "instituição": ["museu", "moma", "louvre", "malba", "reina"],
            }
            for cat, kws in keyword_map.items():
                if any(kw in norm for kw in kws):
                    return cat, 0.62, f"Classificação inferida por aproximação semântica e vocabulário de domínio."
            return "conceito", 0.42, "Sem correspondência forte; mantido como conceito em observação."
        return best_cat, min(0.99, best_score), f"Mais próximo de '{best_hit}' dentro da categoria {best_cat}."


@st.cache_resource(show_spinner=False)
def build_ml_model(cache_key: str, records_json: str):
    data = pd.DataFrame(json.loads(records_json))
    if SKLEARN_AVAILABLE and len(data["category"].unique()) >= 2 and len(data) >= 8:
        pipe = Pipeline([
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), lowercase=True)),
            ("clf", LogisticRegression(max_iter=2000, class_weight="balanced")),
        ])
        pipe.fit(data["text"], data["category"])
        return {"kind": "sklearn", "model": pipe, "train_rows": len(data)}
    return {"kind": "heuristic", "model": HeuristicNLU(data), "train_rows": len(data)}


def build_learning_pack(store: DataStore) -> Dict[str, Any]:
    records = build_learning_records(store)
    records_json = records.to_json(orient="records", force_ascii=False)
    model_bundle = build_ml_model(hashlib.md5(records_json.encode("utf-8")).hexdigest(), records_json)
    validations = store.validations()
    tags = store.tags()
    works = store.works()
    approved = [v for v in validations if v.get("decision") == "approved"]
    pending_count = max(0, len(tags) - len(approved))
    latest_summary = (
        f"Total {len(tags)} marcações. {len(set(normalize_text(t['tag']) for t in tags))} formas únicas. "
        f"{len(approved)} validadas e {pending_count} pendentes."
    )
    return {
        "records": records,
        "model_bundle": model_bundle,
        "train_rows": model_bundle.get("train_rows", len(records)),
        "summary": latest_summary,
        "works": works,
        "tags": tags,
        "validations": validations,
    }


def predict_entity(pack: Dict[str, Any], text: str) -> Tuple[str, float, str]:
    model_bundle = pack["model_bundle"]
    if model_bundle["kind"] == "sklearn":
        model = model_bundle["model"]
        pred = model.predict([text])[0]
        proba = None
        try:
            proba = float(np.max(model.predict_proba([text])[0]))
        except Exception:
            proba = 0.74
        rationale = "Classificação aprendida a partir de metadados, vocabulário seed e validações curatoriais."
        return pred, proba, rationale
    return model_bundle["model"].predict(text)


# =====================
# ANÁLISE E CONECTIVIDADE
# =====================

def work_map(store: DataStore) -> Dict[int, dict]:
    return {int(w["id"]): w for w in store.works()}


def user_tags_for_work(store: DataStore, user_id: str, work_id: int) -> List[str]:
    return [t["tag"] for t in store.tags() if t["user_id"] == user_id and int(t["work_id"]) == int(work_id)]


def build_search_documents(store: DataStore) -> List[dict]:
    works = store.works()
    tags = store.tags()
    validations = store.validations()
    tags_by_work = defaultdict(list)
    vals_by_work = defaultdict(list)
    for tag in tags:
        tags_by_work[int(tag["work_id"])].append(tag["tag"])
    for val in validations:
        vals_by_work[int(val["work_id"])].append(val)
    docs = []
    for work in works:
        wid = int(work["id"])
        validated_concepts = [v.get("concept") for v in vals_by_work[wid] if v.get("decision") == "approved" and v.get("concept")]
        validated_categories = [v.get("category") for v in vals_by_work[wid] if v.get("decision") == "approved" and v.get("category")]
        text_parts = [
            work.get("title", ""), work.get("artist", ""), work.get("museum", ""), work.get("collection", ""),
            work.get("place", ""), work.get("period", ""), work.get("technique", ""), work.get("material", ""),
            work.get("description", ""), " ".join(work.get("institutional_tags", [])), " ".join(tags_by_work[wid]),
            " ".join(validated_concepts), " ".join(validated_categories), " ".join(work.get("external_refs", [])),
        ]
        docs.append({
            "work_id": wid,
            "title": work["title"],
            "text": " ".join([p for p in text_parts if p]),
            "tags_public": tags_by_work[wid],
            "concepts": validated_concepts,
            "categories": validated_categories,
        })
    return docs


def search_connected(store: DataStore, query: str, limit: int = 12) -> List[dict]:
    docs = build_search_documents(store)
    q = normalize_text(query)
    q_tokens = set(tokenize(query))
    results = []
    if not q:
        return []
    if SKLEARN_AVAILABLE and len(docs) >= 2:
        corpus = [d["text"] for d in docs]
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer as _TV
            from sklearn.metrics.pairwise import cosine_similarity as _cos
            vect = _TV(ngram_range=(1, 2), lowercase=True)
            X = vect.fit_transform(corpus + [query])
            sims = _cos(X[-1], X[:-1]).flatten()
            for doc, sim in zip(docs, sims):
                lexical = len(q_tokens & set(tokenize(doc["text"])))
                score = float(sim) + 0.06 * lexical
                if score > 0:
                    results.append({**doc, "score": score})
        except Exception:
            pass
    if not results:
        for doc in docs:
            text_norm = normalize_text(doc["text"])
            token_overlap = len(q_tokens & set(tokenize(text_norm)))
            contains = 1 if q in text_norm else 0
            fuzzy = max([combined_similarity(query, part) for part in tokenize(text_norm)[:50]] + [0.0])
            score = 0.42 * contains + 0.33 * fuzzy + 0.25 * min(token_overlap / max(1, len(q_tokens)), 1.0)
            if score > 0.08:
                results.append({**doc, "score": float(score)})
    results = sorted(results, key=lambda d: d["score"], reverse=True)[:limit]
    wm = work_map(store)
    enriched = []
    for item in results:
        work = wm[item["work_id"]]
        enriched.append({
            **item,
            "work": work,
            "reason": (
                f"Metadados conectados: {', '.join([v for v in [work.get('artist'), work.get('period'), work.get('technique'), work.get('material')] if v])}. "
                f"Tags públicas associadas: {', '.join(item['tags_public'][:6]) or 'nenhuma ainda'}."
            ),
        })
    return enriched


def build_candidate_concepts(store: DataStore) -> List[dict]:
    tags = store.tags()
    counter = Counter(normalize_text(t["tag"]) for t in tags if t.get("tag"))
    raw_map = defaultdict(list)
    for tag in tags:
        raw_map[normalize_text(tag["tag"])].append(tag["tag"])
    candidates = []
    for norm_tag, freq in counter.items():
        if not norm_tag:
            continue
        variants = sorted(set(raw_map[norm_tag]))
        candidates.append({
            "label": variants[0] if variants else norm_tag,
            "norm": norm_tag,
            "frequency": freq,
            "variants": variants,
        })
    return sorted(candidates, key=lambda x: (-x["frequency"], x["label"]))


def detect_orthographic_variants(store: DataStore, threshold: float = 0.82) -> List[dict]:
    tags = sorted(set(t["tag"] for t in store.tags() if t.get("tag")))
    pairs = []
    for i, a in enumerate(tags):
        for b in tags[i + 1:]:
            score = combined_similarity(a, b)
            if score >= threshold and normalize_text(a) != normalize_text(b):
                pairs.append({"tag_a": a, "tag_b": b, "score": round(score, 3)})
    return sorted(pairs, key=lambda x: x["score"], reverse=True)


def detect_equal_tags_across_works(store: DataStore) -> List[dict]:
    tags = store.tags()
    wm = work_map(store)
    mapping = defaultdict(set)
    for tag in tags:
        mapping[normalize_text(tag["tag"])].add(int(tag["work_id"]))
    results = []
    for norm_tag, work_ids in mapping.items():
        if len(work_ids) >= 2:
            results.append({
                "tag": norm_tag,
                "works": [wm[w]["title"] for w in sorted(work_ids) if w in wm],
                "count": len(work_ids),
            })
    return sorted(results, key=lambda x: (-x["count"], x["tag"]))


def build_validation_queue(store: DataStore, pack: Dict[str, Any]) -> List[dict]:
    wm = work_map(store)
    validations = store.validations()
    validated_keys = {(normalize_text(v["tag_text"]), int(v["work_id"])) for v in validations}
    same_tags = detect_equal_tags_across_works(store)
    same_map = {item["tag"]: item for item in same_tags}
    orth_map = defaultdict(list)
    for pair in detect_orthographic_variants(store):
        orth_map[normalize_text(pair["tag_a"])] .append(pair)
        orth_map[normalize_text(pair["tag_b"])] .append(pair)
    queue = []
    tags = sorted(store.tags(), key=lambda x: x.get("timestamp", ""), reverse=True)
    for tag in tags:
        key = (normalize_text(tag["tag"]), int(tag["work_id"]))
        if key in validated_keys:
            continue
        work = wm.get(int(tag["work_id"]), {})
        category, confidence, rationale = predict_entity(pack, tag["tag"])
        concept = suggest_concept(store, tag["tag"], category, work)
        related_examples = related_examples_for_tag(store, tag["tag"], 3)
        queue.append({
            "tag": tag["tag"],
            "tag_id": tag["id"],
            "work_id": int(tag["work_id"]),
            "work_title": work.get("title", ""),
            "work": work,
            "predicted_category": category,
            "confidence": float(confidence),
            "rationale": rationale,
            "suggested_concept": concept,
            "same_tag_network": same_map.get(normalize_text(tag["tag"])),
            "orthographic_variants": orth_map.get(normalize_text(tag["tag"]), []),
            "related_examples": related_examples,
        })
    return queue


def related_examples_for_tag(store: DataStore, tag_text: str, limit: int = 3) -> List[dict]:
    tags = store.tags()
    wm = work_map(store)
    scored = []
    for row in tags:
        score = combined_similarity(tag_text, row["tag"])
        if score >= 0.30:
            scored.append({
                "tag": row["tag"],
                "work_title": wm.get(int(row["work_id"]), {}).get("title", ""),
                "score": score,
            })
    scored = sorted(scored, key=lambda x: x["score"], reverse=True)
    return scored[:limit]


def suggest_concept(store: DataStore, tag_text: str, category: str, work: dict) -> str:
    norm = normalize_text(tag_text)
    for value in SEED_EXAMPLES.get(category, []):
        if normalize_text(value) == norm:
            return value
    fields = [work.get("artist"), work.get("museum"), work.get("collection"), work.get("place"), work.get("period"), work.get("technique"), work.get("material")]
    for field in fields:
        if normalize_text(field) == norm:
            return str(field)
    if category == "tema":
        for item in work.get("institutional_tags", []):
            if combined_similarity(item, tag_text) > 0.72:
                return item
    return tag_text


def tags_dataframe(store: DataStore) -> pd.DataFrame:
    rows = store.tags()
    if not rows:
        return pd.DataFrame(columns=["id", "user_id", "work_id", "tag", "timestamp"])
    df = pd.DataFrame(rows)
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    return df


def temporal_grouping(store: DataStore) -> Dict[str, pd.DataFrame]:
    df = tags_dataframe(store)
    if df.empty:
        empty = pd.DataFrame(columns=["period", "count", "tags_detail"])
        return {"day": empty, "month": empty, "year": empty}
    df["day"] = df["timestamp"].dt.strftime("%Y-%m-%d")
    df["month"] = df["timestamp"].dt.strftime("%Y-%m")
    df["year"] = df["timestamp"].dt.strftime("%Y")
    out = {}
    for gran in ["day", "month", "year"]:
        grouped = (
            df.groupby(gran)
            .agg(
                count=("tag", "count"),
                tags_detail=("tag", lambda x: ", ".join(pd.Series(x).astype(str).value_counts().head(12).index.tolist())),
            )
            .reset_index()
            .rename(columns={gran: "period"})
            .sort_values("period")
        )
        out[gran] = grouped
    return out


def temporal_detail_text(df: pd.DataFrame, top_n: int = 8) -> List[str]:
    lines = []
    for _, row in df.tail(top_n).iterrows():
        lines.append(f"{row['period']}: {int(row['count'])} marcações. Tags observadas: {row['tags_detail'] or 'sem detalhe' }.")
    return lines


def institution_collection_summary(store: DataStore) -> Dict[str, Any]:
    works = store.works()
    tags = store.tags()
    validations = store.validations()
    by_work = Counter(int(t["work_id"]) for t in tags)
    approved = Counter(int(v["work_id"]) for v in validations if v.get("decision") == "approved")
    completeness = []
    for work in works:
        filled_fields = sum(bool(work.get(field)) for field in ["artist", "year", "museum", "collection", "place", "period", "technique", "material", "description"])
        completeness.append({
            "work_id": work["id"],
            "work_title": work["title"],
            "metadata_filled": filled_fields,
            "public_tags": by_work[int(work["id"])],
            "approved_validations": approved[int(work["id"])],
            "institutional_tags": len(work.get("institutional_tags", [])),
        })
    return {
        "works_total": len(works),
        "public_tags_total": len(tags),
        "approved_total": sum(v.get("decision") == "approved" for v in validations),
        "completeness": completeness,
    }


def build_connectivity_network(store: DataStore) -> Tuple[List[dict], List[Tuple[str, str, str]]]:
    nodes: Dict[str, dict] = {}
    edges: List[Tuple[str, str, str]] = []
    validations = store.validations()
    val_lookup = defaultdict(list)
    for v in validations:
        if v.get("decision") == "approved":
            val_lookup[(normalize_text(v["tag_text"]), int(v["work_id"]))].append(v)
    for work in store.works():
        wid = f"work:{work['id']}"
        nodes[wid] = {"id": wid, "label": work["title"], "kind": "obra"}
        meta_map = {
            "artist": ("artista", work.get("artist")),
            "museum": ("museu", work.get("museum")),
            "collection": ("coleção", work.get("collection")),
            "place": ("lugar", work.get("place")),
            "period": ("período", work.get("period")),
            "technique": ("técnica", work.get("technique")),
            "material": ("material", work.get("material")),
        }
        for prefix, (kind, value) in meta_map.items():
            value = str(value or "").strip()
            if not value:
                continue
            nid = f"{prefix}:{slugify(value)}"
            nodes[nid] = {"id": nid, "label": value, "kind": kind}
            edges.append((wid, nid, "metadado"))
        for item in work.get("institutional_tags", []):
            nid = f"it:{slugify(item)}"
            nodes[nid] = {"id": nid, "label": item, "kind": "tag institucional"}
            edges.append((wid, nid, "tag institucional"))
        for ref in work.get("external_refs", []):
            nid = f"ext:{slugify(ref)}"
            nodes[nid] = {"id": nid, "label": ref, "kind": "open data"}
            edges.append((wid, nid, "referência externa"))
    for tag in store.tags():
        wid = f"work:{tag['work_id']}"
        tag_node = f"tag:{slugify(tag['tag'])}"
        nodes[tag_node] = {"id": tag_node, "label": tag["tag"], "kind": "tag pública"}
        edges.append((wid, tag_node, "tag pública"))
        vals = val_lookup.get((normalize_text(tag["tag"]), int(tag["work_id"])), [])
        for val in vals:
            if val.get("concept"):
                concept_node = f"concept:{slugify(val['concept'])}"
                nodes[concept_node] = {"id": concept_node, "label": val["concept"], "kind": "conceito reconciliado"}
                edges.append((tag_node, concept_node, "reconciliação"))
            if val.get("category"):
                cat_node = f"cat:{slugify(val['category'])}"
                nodes[cat_node] = {"id": cat_node, "label": val['category'], "kind": "categoria"}
                edges.append((tag_node, cat_node, "classificação"))
    return list(nodes.values()), unique_preserve(edges)


def build_3d_layout(nodes: List[dict], edges: List[Tuple[str, str, str]]) -> Optional[Any]:
    if not PLOTLY_AVAILABLE:
        return None
    by_kind = defaultdict(list)
    for node in nodes:
        by_kind[node["kind"]].append(node)
    kind_layers = {
        "obra": (0, 0),
        "artista": (1, 6),
        "museu": (2, 6),
        "coleção": (2, -6),
        "lugar": (3, 6),
        "período": (3, -6),
        "técnica": (4, 6),
        "material": (4, -6),
        "tag institucional": (5, 8),
        "tag pública": (6, 10),
        "conceito reconciliado": (7, 8),
        "open data": (8, 4),
        "categoria": (9, 0),
    }
    coords = {}
    for kind, items in by_kind.items():
        ring, z = kind_layers.get(kind, (10, 0))
        radius = 5 + ring * 1.25
        total = len(items)
        for idx, node in enumerate(items):
            angle = 2 * math.pi * idx / max(total, 1)
            x = radius * math.cos(angle)
            y = radius * math.sin(angle)
            coords[node["id"]] = (x, y, z)
    kind_colors = {
        "obra": "#1d4ed8",
        "artista": "#0f766e",
        "museu": "#7c3aed",
        "coleção": "#a16207",
        "lugar": "#059669",
        "período": "#9333ea",
        "técnica": "#0ea5e9",
        "material": "#f59e0b",
        "tag institucional": "#334155",
        "tag pública": "#111827",
        "conceito reconciliado": "#dc2626",
        "open data": "#64748b",
        "categoria": "#be123c",
    }
    edge_x, edge_y, edge_z = [], [], []
    for src, dst, _label in edges:
        if src not in coords or dst not in coords:
            continue
        x0, y0, z0 = coords[src]
        x1, y1, z1 = coords[dst]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])
        edge_z.extend([z0, z1, None])
    edge_trace = go.Scatter3d(
        x=edge_x, y=edge_y, z=edge_z,
        mode="lines",
        line=dict(color="rgba(80,80,90,0.34)", width=3),
        hoverinfo="none",
        showlegend=False,
    )
    node_traces = []
    for kind, items in by_kind.items():
        xs, ys, zs, texts, custom = [], [], [], [], []
        for node in items:
            x, y, z = coords[node["id"]]
            xs.append(x)
            ys.append(y)
            zs.append(z)
            texts.append(node["label"])
            custom.append(kind)
        node_traces.append(
            go.Scatter3d(
                x=xs, y=ys, z=zs,
                mode="markers+text",
                text=texts,
                textposition="top center",
                marker=dict(size=7, color=kind_colors.get(kind, "#111827"), opacity=0.92),
                name=kind,
                hovertemplate="<b>%{text}</b><br>tipo: %{customdata}<extra></extra>",
                customdata=custom,
            )
        )
    fig = go.Figure([edge_trace] + node_traces)
    fig.update_layout(
        height=760,
        margin=dict(l=0, r=0, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        scene=dict(
            bgcolor="rgba(0,0,0,0)",
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, title=""),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, title=""),
            zaxis=dict(showgrid=False, zeroline=False, showticklabels=False, title=""),
            camera=dict(eye=dict(x=1.6, y=1.4, z=1.2)),
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0.0),
    )
    return fig


# =====================
# ACESSIBILIDADE
# =====================

def interpret_work_text(work: dict, user_tags: Optional[List[str]] = None) -> str:
    user_tags = user_tags or []
    parts = [
        f"Obra {work.get('title', '')}.",
        f"Artista: {work.get('artist', 'não informado')}." if work.get("artist") else "",
        f"Período: {work.get('period', 'não informado')}." if work.get("period") else "",
        f"Técnica: {work.get('technique', 'não informado')}." if work.get("technique") else "",
        f"Material: {work.get('material', 'não informado')}." if work.get("material") else "",
        f"Descrição base: {work.get('description', '')}." if work.get("description") else "",
    ]
    if user_tags:
        parts.append(f"Tags registradas por você nesta obra: {', '.join(user_tags)}.")
    return " ".join([p for p in parts if p])


def simplified_text(text: str) -> str:
    text = text.strip()
    if not text:
        return "Ainda não há conteúdo selecionado para leitura simplificada."
    replacements = {
        "reconciliação": "ligação entre uma tag criada e um conceito equivalente",
        "metadados": "dados básicos da obra, como artista, técnica e lugar",
        "interoperabilidade": "troca de informações entre bases e sistemas",
        "validação": "revisão feita pela equipe",
        "categoria": "tipo principal da marcação",
    }
    out = text
    for old, new in replacements.items():
        out = re.sub(old, new, out, flags=re.IGNORECASE)
    return out


def libras_gloss(text: str) -> str:
    words = tokenize(text)
    if not words:
        return "SEM CONTEUDO"
    return " ".join(word.upper() for word in words[:40])


def tts_button(text: str, label: str = "Ouvir leitura") -> None:
    if not text:
        return
    encoded = base64.b64encode(text.encode("utf-8")).decode("ascii")
    html = f"""
    <div class='glass plain-card'>
      <div class='avatar-box'>
        <div class='avatar-3d'>
          <div class='part avatar-head'></div>
          <div class='part avatar-body'></div>
          <div class='part avatar-leg-l'></div>
          <div class='part avatar-leg-r'></div>
          <div class='part avatar-arm-l'></div>
          <div class='part avatar-arm-r'></div>
        </div>
        <div>
          <button onclick="(function(){{
              const txt = decodeURIComponent(escape(window.atob('{encoded}')));
              const utt = new SpeechSynthesisUtterance(txt);
              utt.lang = 'pt-BR';
              utt.rate = 1.0;
              window.speechSynthesis.cancel();
              window.speechSynthesis.speak(utt);
          }})()" style="padding:10px 18px;border-radius:18px;border:1px solid rgba(255,255,255,0.2);background:#0d1b34;color:white;cursor:pointer;">{label}</button>
          <div class='caption-muted'>Assistente 3D experimental para leitura e apoio visual.</div>
        </div>
      </div>
    </div>
    """
    st.components.v1.html(html, height=180)


# =====================
# PDF
# =====================

def generate_pdf_report(store: DataStore) -> Optional[Path]:
    if not REPORTLAB_AVAILABLE:
        return None
    output = APP_ROOT / "relatorio_folksonomia.pdf"
    summary = institution_collection_summary(store)
    temporal = temporal_grouping(store)
    validations = store.validations()
    candidates = build_candidate_concepts(store)[:12]
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="BodyPT", fontName="Times-Roman", fontSize=11, leading=16))
    doc = SimpleDocTemplate(str(output), pagesize=A4, rightMargin=1.6 * cm, leftMargin=1.6 * cm, topMargin=1.2 * cm, bottomMargin=1.2 * cm)
    story = []
    story.append(Paragraph("Relatório integrado de marcação, validação e conectividade", styles["Title"]))
    story.append(Spacer(1, 0.35 * cm))
    story.append(Paragraph(f"Gerado em {now_str()}.", styles["BodyPT"]))
    story.append(Spacer(1, 0.25 * cm))
    story.append(Paragraph(
        f"A instituição acompanha {summary['works_total']} obras, {summary['public_tags_total']} tags públicas e {summary['approved_total']} validações aprovadas.",
        styles["BodyPT"],
    ))
    story.append(Spacer(1, 0.3 * cm))
    data = [["Obra", "Metadados preenchidos", "Tags públicas", "Validações aprovadas", "Tags institucionais"]]
    for row in summary["completeness"]:
        data.append([
            row["work_title"],
            str(row["metadata_filled"]),
            str(row["public_tags"]),
            str(row["approved_validations"]),
            str(row["institutional_tags"]),
        ])
    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#d8dce8")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#8890a0")),
        ("FONTNAME", (0, 0), (-1, -1), "Times-Roman"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f6f6f8")]),
    ]))
    story.append(table)
    story.append(Spacer(1, 0.35 * cm))
    for label, df in [("Dia", temporal["day"]), ("Mês", temporal["month"]), ("Ano", temporal["year"] )]:
        story.append(Paragraph(f"Análise temporal por {label.lower()}", styles["Heading2"]))
        lines = temporal_detail_text(df)
        for line in lines:
            story.append(Paragraph(line, styles["BodyPT"]))
        story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph("Conceitos em circulação", styles["Heading2"]))
    for item in candidates:
        story.append(Paragraph(f"{item['label']}: {item['frequency']} ocorrência(s). Variantes: {', '.join(item['variants'][:4])}", styles["BodyPT"]))
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph("Validações curatoriais", styles["Heading2"]))
    for item in validations[-12:]:
        story.append(Paragraph(
            f"Tag '{item['tag_text']}' na obra {item['work_id']}: categoria {item['category'] or 'não definida'}, conceito {item['concept'] or 'não reconciliado'}, decisão {item['decision']}.",
            styles["BodyPT"],
        ))
    doc.build(story)
    return output


# =====================
# RENDERIZAÇÃO PÚBLICA
# =====================

def brand_header() -> None:
    st.markdown(
        "<div class='hero-min'><h1 class='hero-title'>folksonomia</h1><div class='hero-sub'>Marcação participativa com leitura conectada entre tags do público e metadados institucionais.</div></div>",
        unsafe_allow_html=True,
    )


def render_questionnaire(store: DataStore) -> None:
    brand_header()
    st.markdown(
        "<div class='glass section-card'><div class='section-title'>Antes de começar</div><p class='section-sub'>Responda ao questionário inicial. Depois disso, a marcação das obras será liberada.</p></div>",
        unsafe_allow_html=True,
    )
    with st.form("questionnaire"):
        c1, c2 = st.columns(2)
        with c1:
            q1 = st.selectbox(
                "Qual é a sua frequência de visita a museus?",
                ["nunca", "raramente", "às vezes", "com frequência"],
            )
            q2 = st.selectbox(
                "Você já ouviu falar sobre documentação museológica?",
                ["nenhum", "já ouvi falar", "tenho noção básica", "sim, conheço bem"],
            )
        with c2:
            q3 = st.text_area(
                "O que você entende por tags aplicadas a acervos?",
                placeholder="Escreva com suas palavras.",
                height=180,
            )
        submitted = st.form_submit_button("Liberar acesso às obras", use_container_width=True)
        if submitted:
            if not q3.strip():
                st.error("Escreva sua resposta para liberar a marcação das obras.")
            else:
                uid = store.add_user_response(q1, q2, q3)
                st.session_state["public_uid"] = uid
                st.session_state["questionnaire_done"] = True
                st.rerun()


def render_public_gallery(store: DataStore, settings: Dict[str, Any]) -> None:
    brand_header()
    st.markdown("<div class='public-instruction'>Toque em <strong>Marcar</strong> para abrir um campo pequeno de tag na própria imagem. Nenhum metadado curatorial é mostrado aqui para não influenciar sua leitura.</div>", unsafe_allow_html=True)
    works = store.works()
    cols = st.columns(3)
    uid = st.session_state.get("public_uid", "publico")
    open_card = st.session_state.get("open_card")
    for i, work in enumerate(works):
        with cols[i % 3]:
            st.markdown("<div class='glass work-card'>", unsafe_allow_html=True)
            st.markdown(f"<div class='work-image-wrap'><img src='{work['image']}' alt='obra'/></div>", unsafe_allow_html=True)
            st.markdown("<div class='work-action'>", unsafe_allow_html=True)
            if st.button("Marcar", key=f"mark-{work['id']}", use_container_width=True):
                st.session_state["open_card"] = work["id"]
                st.rerun()
            user_existing = user_tags_for_work(store, uid, work["id"])
            if open_card == work["id"]:
                with st.form(f"tag-form-{work['id']}"):
                    tag_text = st.text_input("Sua tag", placeholder="Ex.: céu, guerra, rosto, trabalho")
                    cform1, cform2 = st.columns(2)
                    submit_tag = cform1.form_submit_button("Registrar tag", use_container_width=True)
                    close_tag = cform2.form_submit_button("Fechar", use_container_width=True)
                    if submit_tag:
                        if tag_text.strip():
                            store.add_tag(uid, work["id"], tag_text.strip())
                            st.session_state["open_card"] = None
                            st.success("Tag registrada.")
                            st.rerun()
                        else:
                            st.error("Digite uma tag antes de registrar.")
                    if close_tag:
                        st.session_state["open_card"] = None
                        st.rerun()
            if user_existing:
                chips = "".join([f"<span class='own-tag-chip'>{stt}</span>" for stt in user_existing[-8:]])
                st.markdown(f"<div class='small-helper'>Suas tags nesta obra</div>{chips}", unsafe_allow_html=True)
            st.markdown("</div></div>", unsafe_allow_html=True)
    st.markdown("<hr class='hr-soft'/>", unsafe_allow_html=True)
    st.markdown("<div class='admin-open'>", unsafe_allow_html=True)
    if st.button("Abrir administração", use_container_width=True):
        st.session_state["show_admin_login"] = True
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


# =====================
# ADMINISTRAÇÃO
# =====================

def admin_login(store: DataStore) -> None:
    brand_header()
    st.markdown("<div class='glass section-card'><div class='section-title'>Login administrativo</div><p class='section-sub'>Entre para revisar marcações, acompanhar a análise temporal, validar conceitos e navegar pela teia 3D de conectividade.</p></div>", unsafe_allow_html=True)
    with st.form("admin-login"):
        username = st.text_input("Usuário administrativo")
        password = st.text_input("Senha administrativa", type="password")
        submitted = st.form_submit_button("Entrar na administração", use_container_width=True)
        if submitted:
            if store.check_admin(username, password):
                st.session_state["admin_ok"] = True
                st.session_state["show_admin_login"] = False
                st.rerun()
            else:
                st.error("Credenciais inválidas.")


def panel_metrics(store: DataStore, pack: Dict[str, Any]) -> None:
    summary = institution_collection_summary(store)
    validations = store.validations()
    queue = build_validation_queue(store, pack)
    total_tags = len(store.tags())
    approved = len([v for v in validations if v.get("decision") == "approved"])
    search_docs = build_search_documents(store)
    top_hits = sorted(summary["completeness"], key=lambda x: x["public_tags"], reverse=True)[:3]

    c1, c2, c3, c4 = st.columns(4)
    metric_data = [
        ("Obras monitoradas", human_count(summary["works_total"]), "Conjunto com metadados e tags institucionais disponíveis para conexão."),
        ("Tags coletadas", human_count(total_tags), "Marcações criadas pelo público e prontas para leitura conectada."),
        ("Fila curatorial", human_count(len(queue)), "Registros aguardando supervisão, validação e reconciliação."),
        ("Validações concluídas", human_count(approved), "Entradas já revistas e utilizadas para treinar o mecanismo de aprendizagem."),
    ]
    for col, (label, value, desc) in zip([c1, c2, c3, c4], metric_data):
        with col:
            st.markdown(f"<div class='glass metric-card'><div class='metric-label'>{label}</div><div class='metric-value'>{value}</div><div class='metric-desc'>{desc}</div></div>", unsafe_allow_html=True)

    st.markdown("<div class='glass section-card'><div class='section-title'>Resumo analítico</div><p class='section-sub'>"
                f"O mecanismo aprendeu com {pack['train_rows']} exemplos entre vocabulário seed, metadados institucionais e validações. Hoje, a coleção conectada reúne {len(search_docs)} documentos de busca, {len(build_candidate_concepts(store))} conceitos em circulação e {len(detect_equal_tags_across_works(store))} ligações por coincidência entre obras."
                "</p></div>", unsafe_allow_html=True)
    if top_hits:
        lines = [f"<span class='flow-chip'>{row['work_title']}: {row['public_tags']} tags públicas, {row['approved_validations']} validações aprovadas</span>" for row in top_hits]
        st.markdown("<div class='glass plain-card'><h4>Onde a coleta está mais ativa</h4><p>" + " ".join(lines) + "</p></div>", unsafe_allow_html=True)


def render_search_tab(store: DataStore) -> None:
    st.markdown("<div class='glass section-card'><div class='section-title'>Busca conectada</div><p class='section-sub'>Pesquise por artista, técnica, material, período, lugar, museu, coleção, conceito validado ou tag criada. O resultado cruza metadados institucionais com a linguagem do público.</p></div>", unsafe_allow_html=True)
    query = st.text_input("Buscar na rede conectada", placeholder="Ex.: guerra, óleo sobre tela, modernismo brasileiro, trabalho")
    if query.strip():
        hits = search_connected(store, query)
        if not hits:
            st.info("Nenhuma correspondência forte foi encontrada para essa consulta.")
        for item in hits:
            work = item["work"]
            st.markdown(
                f"<div class='glass search-hit'><div class='search-hit-title'>{work['title']} · score {item['score']:.2f}</div>"
                f"<div class='search-hit-body'>{item['reason']}<br>Metadados-chave: artista {work.get('artist') or '—'}, período {work.get('period') or '—'}, técnica {work.get('technique') or '—'}, material {work.get('material') or '—'}.</div></div>",
                unsafe_allow_html=True,
            )


def render_validation_tab(store: DataStore, pack: Dict[str, Any]) -> None:
    queue = build_validation_queue(store, pack)
    st.markdown("<div class='glass section-card'><div class='section-title'>Monitoramento, supervisão e validação</div><p class='section-sub'>Aqui a equipe observa a marcação social, compara a saída do sistema com os metadados da coleção, verifica confusões, acompanha erros ortográficos e aprova ou corrige a classificação. Cada validação entra no ciclo de aprendizagem do mecanismo.</p></div>", unsafe_allow_html=True)

    same_tags = detect_equal_tags_across_works(store)[:8]
    ortho = detect_orthographic_variants(store)[:8]
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("<div class='glass plain-card'><h4>Tags iguais em obras diferentes</h4><p>" + ("<br>".join([f"{row['tag']} → {', '.join(row['works'])}" for row in same_tags]) or "Ainda não há coincidências suficientes para comparação.") + "</p></div>", unsafe_allow_html=True)
    with c2:
        st.markdown("<div class='glass plain-card'><h4>Possíveis grafias próximas ou confundidas</h4><p>" + ("<br>".join([f"{row['tag_a']} ↔ {row['tag_b']} · similaridade {row['score']}" for row in ortho]) or "Ainda não há variantes fortes detectadas.") + "</p></div>", unsafe_allow_html=True)

    for item in queue[:24]:
        work = item["work"]
        meta_line = " · ".join([v for v in [work.get("museum"), work.get("period"), work.get("technique"), work.get("material")] if v])
        examples_line = "; ".join([f"{ex['tag']} em {ex['work_title']} ({ex['score']:.2f})" for ex in item["related_examples"]]) or "sem exemplos próximos"
        same_line = ", ".join(item["same_tag_network"]["works"]) if item.get("same_tag_network") else "não encontrada em outras obras"
        ortho_line = ", ".join(sorted(set([f"{p['tag_a']} / {p['tag_b']}" for p in item["orthographic_variants"]]))) if item["orthographic_variants"] else "sem variantes fortes"
        st.markdown(
            f"<div class='glass validation-card'><div class='validation-tag'>{item['tag']} · {item['work_title']}</div>"
            f"<div class='validation-meta'>Previsão: {item['predicted_category']} · confiança {item['confidence']:.2f}<br>"
            f"Conceito sugerido: {item['suggested_concept']}<br>"
            f"Metadados conectados: {meta_line or 'sem detalhe'}<br>"
            f"Ocorrência em outras obras: {same_line}<br>"
            f"Grafias e confusões observadas: {ortho_line}<br>"
            f"Amostra de 3 exemplos: {examples_line}<br>"
            f"Justificativa do mecanismo: {item['rationale']}</div></div>",
            unsafe_allow_html=True,
        )
        with st.form(f"validation-{item['tag_id']}"):
            col1, col2, col3 = st.columns(3)
            category = col1.selectbox("Categoria validada", ENTITY_CATEGORIES, index=max(0, ENTITY_CATEGORIES.index(item["predicted_category"]) if item["predicted_category"] in ENTITY_CATEGORIES else 0))
            concept = col2.text_input("Conceito reconciliado", value=item["suggested_concept"])
            decision = col3.selectbox("Decisão", ["approved", "review", "rejected"], index=0)
            notes = st.text_area("Notas curatoriais", placeholder="Registre o motivo da decisão, ajuste conceitual, comparação com metadados e observações sobre erros ou ambiguidades.", height=110)
            submitted = st.form_submit_button("Registrar validação", use_container_width=True)
            if submitted:
                store.add_validation({
                    "tag_text": item["tag"],
                    "work_id": item["work_id"],
                    "category": category,
                    "concept": concept,
                    "decision": decision,
                    "notes": notes,
                })
                st.success("Validação registrada. O mecanismo irá reaprender com esse novo exemplo.")
                st.rerun()


def render_temporal_tab(store: DataStore) -> None:
    st.markdown("<div class='glass section-card'><div class='section-title'>Análise temporal</div><p class='section-sub'>A leitura temporal acompanha as tags criadas por dia, mês e ano, destacando o que entrou em cada período e quais termos se repetem ao longo do tempo.</p></div>", unsafe_allow_html=True)
    grouped = temporal_grouping(store)
    for label, key in [("Por dia", "day"), ("Por mês", "month"), ("Por ano", "year")]:
        df = grouped[key]
        st.markdown(f"<div class='glass timeline-card'><div class='timeline-title'>{label}</div>", unsafe_allow_html=True)
        if df.empty:
            st.markdown("<div class='timeline-list'>Ainda não há marcações suficientes para essa leitura.</div></div>", unsafe_allow_html=True)
            continue
        if PLOTLY_AVAILABLE:
            fig = go.Figure([go.Scatter(x=df["period"], y=df["count"], mode="lines+markers", line=dict(color="#0d1b34", width=3), marker=dict(size=8, color="#0d1b34"))])
            fig.update_layout(height=300, margin=dict(l=0, r=0, t=10, b=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(255,255,255,0.15)")
            fig.update_xaxes(title="", tickangle=-30, showgrid=False)
            fig.update_yaxes(title="tags", showgrid=True, gridcolor="rgba(0,0,0,0.08)")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.line_chart(df.set_index("period")["count"])
        lines = temporal_detail_text(df, 6)
        st.markdown("<div class='timeline-list'>" + "<br>".join(lines) + "</div></div>", unsafe_allow_html=True)


def render_connectivity_tab(store: DataStore) -> None:
    nodes, edges = build_connectivity_network(store)
    st.markdown("<div class='glass section-card'><div class='section-title'>Teia 3D de compartilhamento e interoperabilidade</div><p class='section-sub'>A rede liga obras, artistas, museus, coleção, lugar, período, técnica, material, tags institucionais, tags do público, conceitos reconciliados e referências externas em um mesmo espaço de navegação. O foco aqui é mostrar tráfego de informação e acesso rápido entre metadados e marcações.</p></div>", unsafe_allow_html=True)
    if PLOTLY_AVAILABLE:
        fig = build_3d_layout(nodes, edges)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("A teia 3D depende do Plotly. Instale o pacote para visualizar a rede completa.")
    kind_counter = Counter(node["kind"] for node in nodes)
    chips = " ".join([f"<span class='flow-chip'>{kind}: {count}</span>" for kind, count in kind_counter.items()])
    st.markdown("<div class='glass plain-card'><h4>Como a rede está organizada agora</h4><p>" + chips + "</p></div>", unsafe_allow_html=True)


def render_works_admin_tab(store: DataStore) -> None:
    st.markdown("<div class='glass section-card'><div class='section-title'>Obras e metadados</div><p class='section-sub'>Inclua, revise ou exclua obras e seus metadados. Esses dados são a base da leitura conectada, da busca real e do treino progressivo do mecanismo.</p></div>", unsafe_allow_html=True)
    t1, t2 = st.tabs(["Listar e excluir", "Adicionar nova obra"])
    with t1:
        for work in store.works():
            st.markdown(
                f"<div class='glass plain-card'><h4>{work['title']}</h4><p>Artista: {work.get('artist') or '—'} · Museu: {work.get('museum') or '—'} · Período: {work.get('period') or '—'} · Técnica: {work.get('technique') or '—'} · Material: {work.get('material') or '—'}</p></div>",
                unsafe_allow_html=True,
            )
            if st.button(f"Excluir {work['title']}", key=f"delete-{work['id']}"):
                store.remove_work(work["id"])
                st.success("Obra excluída.")
                st.rerun()
    with t2:
        with st.form("add-work"):
            c1, c2 = st.columns(2)
            title = c1.text_input("Título")
            artist = c2.text_input("Artista")
            year = c1.text_input("Ano")
            museum = c2.text_input("Museu")
            image = c1.text_input("URL da imagem")
            collection = c2.text_input("Coleção")
            place = c1.text_input("Lugar")
            period = c2.text_input("Período")
            technique = c1.text_input("Técnica")
            material = c2.text_input("Material")
            description = st.text_area("Descrição")
            institutional_tags = st.text_input("Tags institucionais", placeholder="Separe por vírgula")
            external_refs = st.text_input("Referências externas / open data", placeholder="Separe por vírgula")
            submitted = st.form_submit_button("Adicionar obra", use_container_width=True)
            if submitted:
                if not title.strip() or not image.strip():
                    st.error("Título e imagem são obrigatórios.")
                else:
                    store.add_work({
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
                        "description": description.strip(),
                        "institutional_tags": [i.strip() for i in institutional_tags.split(",") if i.strip()],
                        "external_refs": [i.strip() for i in external_refs.split(",") if i.strip()],
                    })
                    st.success("Obra adicionada.")
                    st.rerun()


def render_export_tab(store: DataStore) -> None:
    st.markdown("<div class='glass section-card'><div class='section-title'>Exportação e acessos de saída</div><p class='section-sub'>Baixe os dados coletados, o histórico de validação e o relatório em PDF com o fluxo entre metadados, tags públicas e conceitos reconciliados.</p></div>", unsafe_allow_html=True)
    tags_df = pd.DataFrame(store.tags())
    vals_df = pd.DataFrame(store.validations())
    works_df = pd.DataFrame(store.works())
    if not tags_df.empty:
        st.download_button("Baixar tags em CSV", tags_df.to_csv(index=False).encode("utf-8"), "tags.csv", "text/csv", use_container_width=True)
    if not vals_df.empty:
        st.download_button("Baixar validações em CSV", vals_df.to_csv(index=False).encode("utf-8"), "validacoes.csv", "text/csv", use_container_width=True)
    st.download_button("Baixar obras em CSV", works_df.to_csv(index=False).encode("utf-8"), "obras.csv", "text/csv", use_container_width=True)
    if st.button("Gerar relatório em PDF", use_container_width=True):
        pdf_path = generate_pdf_report(store)
        if pdf_path is None:
            st.error("Não foi possível gerar o PDF nesta execução porque o pacote reportlab não está instalado.")
        else:
            st.success("Relatório em PDF gerado.")
            st.download_button("Baixar PDF", pdf_path.read_bytes(), pdf_path.name, "application/pdf", use_container_width=True)


def render_accessibility_tab(store: DataStore, settings: Dict[str, Any]) -> None:
    st.markdown("<div class='glass section-card'><div class='section-title'>Acessibilidade</div><p class='section-sub'>Ajuste o tamanho do texto, ative contraste reforçado, gere interpretação textual da obra selecionada, use leitura em voz alta e apoio visual experimental com glosa para Libras.</p></div>", unsafe_allow_html=True)
    work_options = {w["title"]: w for w in store.works()}
    selected_title = st.selectbox("Escolha uma obra para leitura acessível", list(work_options.keys()))
    selected_work = work_options[selected_title]
    user_id = st.session_state.get("public_uid", "publico")
    reading = interpret_work_text(selected_work, user_tags_for_work(store, user_id, selected_work["id"]))
    simple = simplified_text(reading) if settings.get("simple_text") else reading
    st.markdown(f"<div class='glass plain-card'><h4>Interpretação textual</h4><p>{simple}</p></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='glass plain-card'><h4>Glosa de apoio</h4><p>{libras_gloss(simple)}</p></div>", unsafe_allow_html=True)
    tts_button(simple)


def render_admin(store: DataStore, settings: Dict[str, Any]) -> None:
    brand_header()
    pack = build_learning_pack(store)
    panel_metrics(store, pack)
    tabs = st.tabs([
        "Busca real",
        "Validação",
        "Temporal",
        "Teia 3D",
        "Obras",
        "Exportar",
        "Acessibilidade",
    ])
    with tabs[0]:
        render_search_tab(store)
    with tabs[1]:
        render_validation_tab(store, pack)
    with tabs[2]:
        render_temporal_tab(store)
    with tabs[3]:
        render_connectivity_tab(store)
    with tabs[4]:
        render_works_admin_tab(store)
    with tabs[5]:
        render_export_tab(store)
    with tabs[6]:
        render_accessibility_tab(store, settings)
    if st.button("Sair da administração", use_container_width=True):
        st.session_state["admin_ok"] = False
        st.session_state["show_admin_login"] = False
        st.rerun()


# =====================
# CONFIG GERAL
# =====================

def render_settings_sidebar(store: DataStore) -> Dict[str, Any]:
    current = store.settings()
    with st.sidebar:
        st.markdown("### Acessibilidade")
        font_scale = st.slider("Tamanho da letra", 0.9, 1.5, float(current.get("font_scale", 1.0)), 0.05)
        high_contrast = st.toggle("Contraste reforçado", value=bool(current.get("high_contrast", False)))
        simple_text = st.toggle("Interpretação textual simplificada", value=bool(current.get("simple_text", False)))
        avatar_enabled = st.toggle("Assistente 3D experimental", value=bool(current.get("avatar_enabled", True)))
        updated = {
            "font_scale": font_scale,
            "high_contrast": high_contrast,
            "simple_text": simple_text,
            "avatar_enabled": avatar_enabled,
        }
        if updated != current:
            store.save_settings(updated)
            current = updated
    return current


def init_session() -> None:
    st.session_state.setdefault("questionnaire_done", False)
    st.session_state.setdefault("public_uid", "publico")
    st.session_state.setdefault("show_admin_login", False)
    st.session_state.setdefault("admin_ok", False)
    st.session_state.setdefault("open_card", None)


def main() -> None:
    init_session()
    store = DataStore()
    settings = render_settings_sidebar(store)
    inject_css(settings)
    if st.session_state.get("admin_ok"):
        render_admin(store, settings)
    elif st.session_state.get("show_admin_login"):
        admin_login(store)
    elif not st.session_state.get("questionnaire_done"):
        render_questionnaire(store)
    else:
        render_public_gallery(store, settings)


if __name__ == "__main__":
    main()
