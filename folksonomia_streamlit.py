from __future__ import annotations

import html
import hashlib
import json
import math
import re
import subprocess
import sys
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st
import streamlit.components.v1 as components

# ── Auto-install heavy deps if missing ────────────────────────────────────────
def _ensure_pkg(pkg: str, import_name: str) -> bool:
    try:
        __import__(import_name)
        return True
    except ImportError:
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", pkg, "--quiet"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            __import__(import_name)
            return True
        except Exception:
            return False

PLOTLY_AVAILABLE   = _ensure_pkg("plotly",    "plotly")
REPORTLAB_AVAILABLE = _ensure_pkg("reportlab", "reportlab")

if PLOTLY_AVAILABLE:
    import plotly.graph_objects as go

if REPORTLAB_AVAILABLE:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib import colors as rlcolors
    from reportlab.platypus import (
        Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle, HRFlowable,
    )

# ── Paths & Constants ─────────────────────────────────────────────────────────
APP_DIR             = Path("data_folksonomia_clean")
WORKS_FILE          = APP_DIR / "works.json"
TAGS_FILE           = APP_DIR / "tags.json"
QUESTIONNAIRE_FILE  = APP_DIR / "questionnaire.json"
VALIDATIONS_FILE    = APP_DIR / "validations.json"
ONTOLOGIES_FILE     = APP_DIR / "ontologies.json"
ADMIN_FILE          = APP_DIR / "admin.json"

ADMIN_LOGIN    = "nugep239@"
ADMIN_PASSWORD = "nugep123"

CATEGORIES = [
    "tema", "pessoa", "lugar", "período",
    "técnica", "material", "evento", "conceito", "outro",
]

NODE_COLORS = {
    "obra":      "#2563eb",
    "artista":   "#7c3aed",
    "museu":     "#0f766e",
    "período":   "#dc2626",
    "técnica":   "#b45309",
    "material":  "#0ea5e9",
    "tag":       "#374151",
    "conceito":  "#16a34a",
    "open_data": "#9333ea",
}

st.set_page_config(
    page_title="folksonomia",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Utilities ─────────────────────────────────────────────────────────────────
def slug(text: str) -> str:
    text = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    return text or "item"

def normalize(text: str) -> str:
    if text is None:
        return ""
    text = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"\s+", " ", text.lower()).strip()
    return text

def tokenize(text: str) -> List[str]:
    return [t for t in re.split(r"[^a-zA-ZÀ-ÿ0-9]+", normalize(text)) if len(t) > 1]

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

def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def get_user_id() -> str:
    if "public_user_id" not in st.session_state:
        st.session_state["public_user_id"] = hashlib.sha1(
            str(datetime.now().timestamp()).encode()
        ).hexdigest()[:12]
    return st.session_state["public_user_id"]

def char_similarity(a: str, b: str) -> float:
    a, b = normalize(a), normalize(b)
    if not a or not b:
        return 0.0
    same = sum(1 for c1, c2 in zip(a, b) if c1 == c2)
    return same / max(len(a), len(b))

def token_overlap(a: str, b: str) -> float:
    sa, sb = set(tokenize(a)), set(tokenize(b))
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)

# ── Default data ───────────────────────────────────────────────────────────────
def default_works() -> List[Dict[str, Any]]:
    return [
        {
            "id": "obra-guernica",
            "title": "Guernica",
            "artist": "Pablo Picasso",
            "museum": "Museo Nacional Centro de Arte Reina Sofía",
            "period": "modernismo do século XX",
            "technique": "óleo sobre tela",
            "material": "tinta a óleo",
            "place": "Espanha",
            "collection": "arte moderna europeia",
            "institution_tags": ["guerra", "bombardeio", "cavalo", "touro", "violência"],
            "open_data": ["Dbpedia", "Wikidata"],
            "image": "https://upload.wikimedia.org/wikipedia/en/7/74/PicassoGuernica.jpg",
        },
        {
            "id": "obra-starry-night",
            "title": "A Noite Estrelada",
            "artist": "Vincent van Gogh",
            "museum": "The Museum of Modern Art",
            "period": "pós-impressionismo",
            "technique": "óleo sobre tela",
            "material": "tinta a óleo",
            "place": "França",
            "collection": "pintura moderna",
            "institution_tags": ["céu", "noite", "vila", "movimento", "paisagem"],
            "open_data": ["Dbpedia", "Wikidata"],
            "image": "https://upload.wikimedia.org/wikipedia/commons/e/ea/The_Starry_Night.jpg",
        },
        {
            "id": "obra-monalisa",
            "title": "Mona Lisa",
            "artist": "Leonardo da Vinci",
            "museum": "Musée du Louvre",
            "period": "renascimento",
            "technique": "óleo sobre madeira",
            "material": "madeira e tinta",
            "place": "Itália",
            "collection": "renascimento europeu",
            "institution_tags": ["retrato", "sorriso", "mulher", "paisagem"],
            "open_data": ["Dbpedia", "Wikidata"],
            "image": "https://upload.wikimedia.org/wikipedia/commons/6/6a/Mona_Lisa.jpg",
        },
    ]

# ── Store ──────────────────────────────────────────────────────────────────────
@dataclass
class Store:
    def __post_init__(self) -> None:
        ensure_dir()
        self.bootstrap()

    def bootstrap(self) -> None:
        if not WORKS_FILE.exists():
            save_json(WORKS_FILE, default_works())
        if not TAGS_FILE.exists():
            save_json(TAGS_FILE, [])
        if not QUESTIONNAIRE_FILE.exists():
            save_json(QUESTIONNAIRE_FILE, [])
        if not VALIDATIONS_FILE.exists():
            save_json(VALIDATIONS_FILE, [])
        if not ONTOLOGIES_FILE.exists():
            save_json(ONTOLOGIES_FILE, [
                {"id": "ont-tema",     "label": "tema",     "description": "conceitos temáticos"},
                {"id": "ont-material", "label": "material", "description": "materiais e suportes"},
                {"id": "ont-tecnica",  "label": "técnica",  "description": "modos de feitura"},
            ])
        if not ADMIN_FILE.exists():
            save_json(ADMIN_FILE, {
                "login": ADMIN_LOGIN,
                "password_hash": hashlib.sha256(ADMIN_PASSWORD.encode()).hexdigest(),
            })

    def works(self) -> List[Dict[str, Any]]:
        return load_json(WORKS_FILE, default_works())

    def tags(self) -> List[Dict[str, Any]]:
        return load_json(TAGS_FILE, [])

    def validations(self) -> List[Dict[str, Any]]:
        return load_json(VALIDATIONS_FILE, [])

    def ontologies(self) -> List[Dict[str, Any]]:
        return load_json(ONTOLOGIES_FILE, [])

    def questionnaire(self) -> List[Dict[str, Any]]:
        return load_json(QUESTIONNAIRE_FILE, [])

    def save_tags(self, data):       save_json(TAGS_FILE, data)
    def save_works(self, data):      save_json(WORKS_FILE, data)
    def save_validations(self, data): save_json(VALIDATIONS_FILE, data)
    def save_ontologies(self, data): save_json(ONTOLOGIES_FILE, data)

    def add_tag(self, work_id: str, tag: str, user_id: str) -> None:
        data = self.tags()
        data.append({
            "id": f"tag-{len(data)+1}",
            "work_id": work_id,
            "tag": tag.strip(),
            "normalized": normalize(tag),
            "user_id": user_id,
            "timestamp": now_str(),
        })
        self.save_tags(data)

    def add_questionnaire(self, item: Dict[str, Any]) -> None:
        data = self.questionnaire()
        data.append(item)
        save_json(QUESTIONNAIRE_FILE, data)

    def add_validation(self, item: Dict[str, Any]) -> None:
        data = self.validations()
        data.append(item)
        self.save_validations(data)

    def add_ontology(self, label: str, description: str) -> None:
        data = self.ontologies()
        oid = f"ont-{slug(label)}-{len(data)+1}"
        data.append({"id": oid, "label": label.strip(), "description": description.strip()})
        self.save_ontologies(data)

    def delete_ontology(self, ontology_id: str) -> None:
        self.save_ontologies([o for o in self.ontologies() if o["id"] != ontology_id])

    def add_work(self, work: Dict[str, Any]) -> None:
        data = self.works()
        data.append(work)
        self.save_works(data)

    def delete_work(self, work_id: str) -> None:
        self.save_works([w for w in self.works() if w["id"] != work_id])
        self.save_tags([t for t in self.tags() if t["work_id"] != work_id])
        self.save_validations([v for v in self.validations() if v.get("work_id") != work_id])

    def admin_ok(self, login: str, password: str) -> bool:
        admin = load_json(ADMIN_FILE, {})
        typed_hash = hashlib.sha256(password.encode()).hexdigest()
        if login == ADMIN_LOGIN and password == ADMIN_PASSWORD:
            if admin.get("login") != ADMIN_LOGIN or admin.get("password_hash") != typed_hash:
                save_json(ADMIN_FILE, {"login": ADMIN_LOGIN, "password_hash": typed_hash})
            return True
        return login == admin.get("login") and typed_hash == admin.get("password_hash")

# ── CSS Injection ──────────────────────────────────────────────────────────────
def inject_css() -> None:
    scale    = float(st.session_state.get("font_scale", 1.0))
    contrast = bool(st.session_state.get("high_contrast", False))
    base_font = max(16, int(18 * scale))

    # colour tokens
    if contrast:
        bg_body  = "#f0f0f0"
        txt      = "#000000"
        sub      = "#1f2937"
        glass_bg = "rgba(255,255,255,0.90)"
        glass_border = "rgba(0,0,0,0.25)"
    else:
        bg_body  = "radial-gradient(ellipse at 20% 0%, #e8edf5 0%, #dfe3ec 40%, #d8dce8 100%)"
        txt      = "#111827"
        sub      = "#4b5563"
        glass_bg = "rgba(255,255,255,0.38)"
        glass_border = "rgba(255,255,255,0.55)"

    st.markdown(f"""
    <style>
    /* ── Google fonts ── */
    @import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:wght@300;400;500;600&display=swap');

    :root {{
        --txt:   {txt};
        --sub:   {sub};
        --glass: {glass_bg};
        --border: {glass_border};
        --base:  {base_font}px;
        --r:     26px;
        --shadow-glass: 0 8px 32px rgba(0,0,0,0.07), 0 1.5px 0 rgba(255,255,255,0.55) inset, 0 -1px 0 rgba(0,0,0,0.04) inset;
        --shadow-btn: 0 4px 18px rgba(0,0,0,0.10), 0 1.5px 0 rgba(255,255,255,0.45) inset;
    }}

    /* ── Reset & base ── */
    html, body,
    [data-testid="stAppViewContainer"], .stApp {{
        background: {bg_body} !important;
        background-attachment: fixed !important;
        color: var(--txt) !important;
        font-family: 'DM Sans', 'Helvetica Neue', sans-serif !important;
        font-size: var(--base) !important;
    }}
    #MainMenu, header, footer {{ visibility: hidden !important; }}
    .block-container {{ max-width: 1300px; padding-top: 1rem; padding-bottom: 3rem; }}

    /* ── Glass surface ── */
    .glass {{
        background: var(--glass) !important;
        backdrop-filter: blur(22px) saturate(180%) !important;
        -webkit-backdrop-filter: blur(22px) saturate(180%) !important;
        border: 1px solid var(--border) !important;
        border-radius: var(--r) !important;
        box-shadow: var(--shadow-glass) !important;
    }}
    .glass-dark {{
        background: rgba(15,23,42,0.55) !important;
        backdrop-filter: blur(22px) saturate(160%) !important;
        -webkit-backdrop-filter: blur(22px) saturate(160%) !important;
        border: 1px solid rgba(255,255,255,0.12) !important;
        border-radius: var(--r) !important;
        box-shadow: 0 8px 32px rgba(0,0,0,0.18) !important;
    }}

    /* ── Title bar ── */
    .titleBar {{ padding: 1.4rem 1.6rem; margin-bottom: 1rem; }}
    .titleBar h1 {{
        margin: 0;
        font-family: 'DM Serif Display', Georgia, serif !important;
        font-size: clamp(2.4rem, 5vw, 3.6rem);
        font-weight: 400;
        letter-spacing: -0.02em;
        color: var(--txt) !important;
        line-height: 1.1;
    }}
    .titleBar p {{
        margin: .35rem 0 0 0;
        color: var(--sub) !important;
        font-size: .95rem;
        font-weight: 300;
    }}

    /* ── Cards & panels ── */
    .workCard  {{ padding: .8rem; margin-bottom: 1.2rem; }}
    .workCard img {{ width: 100%; display: block; border-radius: 18px; }}
    .smallPanel {{ padding: 1rem 1.2rem; margin-bottom: .7rem; }}
    .metric {{ padding: 1.1rem 1.2rem; min-height: 118px; }}
    .metric .t {{ color: var(--sub) !important; text-transform: uppercase; letter-spacing: .1em; font-size: .78rem; font-weight: 500; }}
    .metric .v {{ font-size: 2.2rem; font-weight: 700; margin-top: .3rem; color: var(--txt) !important; font-family: 'DM Serif Display', serif !important; }}
    .metric .n {{ margin-top: .2rem; color: var(--sub) !important; font-size: .85rem; }}
    .sectionTitle {{
        font-family: 'DM Serif Display', Georgia, serif !important;
        font-size: 1.8rem;
        font-weight: 400;
        color: var(--txt) !important;
        margin: .1rem 0 .5rem 0;
    }}
    .helper {{ color: var(--sub) !important; line-height: 1.75; font-size: .93rem; }}
    .hr {{ height: 1px; background: rgba(17,24,39,0.08); margin: .8rem 0; }}

    /* ── Tag pills ── */
    .tagPill {{
        display: inline-block;
        margin: .14rem .18rem .14rem 0;
        padding: .28rem .72rem;
        border-radius: 999px;
        background: rgba(255,255,255,0.55);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255,255,255,0.7);
        color: var(--txt) !important;
        font-size: .86rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }}

    /* ══════════════════════════════════════════════
       LIQUID GLASS BUTTONS  — every .stButton variant
       ══════════════════════════════════════════════ */
    .stButton > button,
    div[data-testid="stFormSubmitButton"] button,
    .stDownloadButton > button {{
        width: 100% !important;
        border-radius: 20px !important;
        /* liquid glass base */
        background: rgba(255,255,255,0.22) !important;
        backdrop-filter: blur(18px) saturate(160%) !important;
        -webkit-backdrop-filter: blur(18px) saturate(160%) !important;
        border: 1px solid rgba(255,255,255,0.55) !important;
        /* text */
        color: var(--txt) !important;
        -webkit-text-fill-color: var(--txt) !important;
        font-family: 'DM Sans', sans-serif !important;
        font-weight: 500 !important;
        font-size: .92rem !important;
        letter-spacing: .02em !important;
        /* depth */
        box-shadow:
            0 6px 22px rgba(0,0,0,0.09),
            0 1px 0 rgba(255,255,255,0.70) inset,
            0 -1px 0 rgba(0,0,0,0.05) inset !important;
        padding: .82rem 1rem !important;
        transition: all .18s ease !important;
        text-shadow: none !important;
    }}
    .stButton > button:hover,
    div[data-testid="stFormSubmitButton"] button:hover,
    .stDownloadButton > button:hover {{
        background: rgba(255,255,255,0.38) !important;
        border-color: rgba(255,255,255,0.80) !important;
        box-shadow:
            0 10px 30px rgba(0,0,0,0.12),
            0 1px 0 rgba(255,255,255,0.80) inset !important;
        transform: translateY(-1px) !important;
    }}
    .stButton > button:active,
    div[data-testid="stFormSubmitButton"] button:active,
    .stDownloadButton > button:active {{
        transform: translateY(0px) !important;
        box-shadow: 0 3px 10px rgba(0,0,0,0.08), 0 1px 0 rgba(255,255,255,0.55) inset !important;
    }}

    /* danger / delete button — subtle red tint */
    .stButton > button[kind="secondary"],
    .btn-danger > button {{
        background: rgba(239,68,68,0.12) !important;
        border-color: rgba(239,68,68,0.35) !important;
        color: #b91c1c !important;
        -webkit-text-fill-color: #b91c1c !important;
    }}

    /* ── Inputs ── */
    .stTextInput input, .stTextArea textarea {{
        background: rgba(255,255,255,0.75) !important;
        color: var(--txt) !important;
        -webkit-text-fill-color: var(--txt) !important;
        border: 1px solid rgba(17,24,39,0.15) !important;
        border-radius: 16px !important;
        caret-color: var(--txt) !important;
        font-family: 'DM Sans', sans-serif !important;
        backdrop-filter: blur(8px) !important;
    }}
    .stTextInput input:focus, .stTextArea textarea:focus {{
        border-color: rgba(59,130,246,0.5) !important;
        box-shadow: 0 0 0 3px rgba(59,130,246,0.12) !important;
    }}
    .stTextInput input::placeholder, .stTextArea textarea::placeholder {{
        color: #9ca3af !important; opacity: 1 !important;
    }}
    .stTextArea textarea {{ min-height: 110px; }}

    /* ── Selects ── */
    .stSelectbox [data-baseweb="select"] > div {{
        background: rgba(255,255,255,0.70) !important;
        color: var(--txt) !important;
        border: 1px solid rgba(17,24,39,0.15) !important;
        border-radius: 16px !important;
        backdrop-filter: blur(8px) !important;
    }}
    .stSelectbox [data-baseweb="select"] * {{
        color: var(--txt) !important;
        -webkit-text-fill-color: var(--txt) !important;
    }}
    div[data-baseweb="popover"] ul,
    div[data-baseweb="popover"] li,
    ul[role="listbox"],
    li[role="option"],
    div[role="option"] {{
        background: rgba(240,242,248,0.96) !important;
        backdrop-filter: blur(12px) !important;
        color: var(--txt) !important;
    }}
    li[aria-selected="true"], div[aria-selected="true"] {{
        background: rgba(59,130,246,0.15) !important;
    }}

    /* ── Multiselect ── */
    .stMultiSelect [data-baseweb="select"] > div {{
        background: rgba(255,255,255,0.70) !important;
        border-radius: 16px !important;
        border: 1px solid rgba(17,24,39,0.15) !important;
    }}

    /* ── Tabs ── */
    .stTabs [data-baseweb="tab-list"] {{
        gap: .4rem;
        background: rgba(255,255,255,0.28);
        backdrop-filter: blur(14px);
        border-radius: 28px;
        padding: .32rem;
        border: 1px solid rgba(255,255,255,0.55);
    }}
    .stTabs [data-baseweb="tab"] {{
        border-radius: 22px !important;
        color: var(--sub) !important;
        font-family: 'DM Sans', sans-serif !important;
        font-size: .88rem !important;
        font-weight: 500 !important;
    }}
    .stTabs [aria-selected="true"] {{
        background: rgba(255,255,255,0.75) !important;
        color: var(--txt) !important;
        box-shadow: 0 2px 10px rgba(0,0,0,0.08) !important;
    }}

    /* ── Slider ── */
    .stSlider [data-testid="stThumbValue"] {{ color: var(--txt) !important; }}

    /* ── Toggle ── */
    .stToggle label {{ color: var(--txt) !important; }}

    /* ── Expander ── */
    .streamlit-expanderHeader {{
        background: rgba(255,255,255,0.28) !important;
        border-radius: 18px !important;
        backdrop-filter: blur(10px) !important;
        border: 1px solid rgba(255,255,255,0.50) !important;
        color: var(--txt) !important;
        font-family: 'DM Sans', sans-serif !important;
        font-weight: 500 !important;
    }}
    .streamlit-expanderContent {{
        background: rgba(255,255,255,0.18) !important;
        border-radius: 0 0 18px 18px !important;
        backdrop-filter: blur(10px) !important;
    }}

    /* ── Info / success / warning boxes ── */
    .stAlert {{
        border-radius: 18px !important;
        backdrop-filter: blur(10px) !important;
        background: rgba(255,255,255,0.40) !important;
        border: 1px solid rgba(255,255,255,0.55) !important;
    }}

    /* ── Typography overrides ── */
    label, .stMarkdown, p, li, span, strong,
    h1, h2, h3, h4, h5, h6 {{
        color: var(--txt) !important;
        font-family: 'DM Sans', 'Helvetica Neue', sans-serif !important;
    }}
    h1, h2, h3, .sectionTitle {{
        font-family: 'DM Serif Display', Georgia, serif !important;
    }}

    /* ── Scrollbar ── */
    ::-webkit-scrollbar {{ width: 6px; height: 6px; }}
    ::-webkit-scrollbar-track {{ background: transparent; }}
    ::-webkit-scrollbar-thumb {{ background: rgba(17,24,39,0.18); border-radius: 6px; }}

    /* ── Download button specific fix ── */
    .stDownloadButton {{ width: 100%; }}
    </style>
    """, unsafe_allow_html=True)


# ── Brand header ───────────────────────────────────────────────────────────────
def render_brand() -> None:
    st.markdown(
        """
        <div class="glass titleBar">
            <h1>folksonomia</h1>
            <p>
                marcação pública · acessibilidade · validação curatorial ·
                ontologias · análise temporal · teia 3d conectada
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Speech widget ───────────────────────────────────────────────────────────────
def speech_html(text: str, key: str) -> None:
    safe = json.dumps(text)
    components.html(
        f"""
        <div style='display:flex;gap:10px;'>
          <button onclick='
            window.speechSynthesis.cancel();
            const u = new SpeechSynthesisUtterance({safe});
            u.lang="pt-BR"; u.rate=0.95;
            window.speechSynthesis.speak(u);
          ' style='
            padding:10px 18px;border-radius:16px;
            border:1px solid rgba(255,255,255,0.55);
            background:rgba(255,255,255,0.28);
            backdrop-filter:blur(12px);
            color:#111;font-size:14px;cursor:pointer;
            box-shadow:0 4px 14px rgba(0,0,0,0.09);
          '>▶ ouvir descrição</button>
          <button onclick='window.speechSynthesis.cancel();' style='
            padding:10px 18px;border-radius:16px;
            border:1px solid rgba(255,255,255,0.40);
            background:rgba(255,255,255,0.18);
            backdrop-filter:blur(12px);
            color:#555;font-size:14px;cursor:pointer;
          '>◼ parar</button>
        </div>
        """,
        height=56, key=key,
    )


# ── Accessibility helpers ──────────────────────────────────────────────────────
def build_description(work: Dict[str, Any], user_tags: List[str]) -> str:
    title = work["title"]
    base = [
        f"Imagem da obra {title}, de {work['artist']}, pertencente ao museu {work['museum']}.",
        f"Período {work['period']}, técnica {work['technique']} e material {work['material']}.",
    ]
    title_n = normalize(title)
    if "guernica" in title_n:
        base.append(
            "A cena é monocromática, em preto, branco e cinzas. "
            "Aparecem figuras fragmentadas, um cavalo central em tensão, um touro à esquerda, "
            "braços erguidos, rostos partidos e uma atmosfera de bombardeio, dor e movimento brusco."
        )
    elif "noite estrelada" in title_n or "starry" in title_n:
        base.append(
            "A imagem mostra um céu noturno em espirais intensas, estrelas brilhantes, "
            "lua amarela e uma vila ao fundo. O movimento das pinceladas faz o céu parecer girar."
        )
    elif "mona" in title_n:
        base.append(
            "Trata-se de um retrato frontal de uma mulher sentada, com expressão serena e sorriso discreto. "
            "O fundo mostra uma paisagem suave e nebulosa, em tons terrosos e verdes."
        )
    if user_tags:
        base.append("Tags registradas nesta imagem: " + ", ".join(user_tags[:10]) + ".")
    base.append("Descrição gerada a partir de metadados institucionais e marcações públicas.")
    return " ".join(base)


def explain_words(text: str) -> Dict[str, str]:
    glossary = {
        "bombardeio":      "ataque com explosões lançadas sobre um local.",
        "fragmentadas":    "divididas em partes, sem continuidade visual completa.",
        "monocromática":   "imagem construída com variação muito restrita de cores.",
        "pós-impressionismo": "movimento artístico posterior ao impressionismo, com cor e forma mais expressivas.",
        "renascimento":    "período artístico europeu marcado por perspectiva, anatomia e equilíbrio formal.",
        "ontologia":       "estrutura que organiza conceitos, categorias e relações entre elementos de um domínio.",
        "interoperabilidade": "capacidade de sistemas diferentes trocarem e entenderem informações entre si.",
        "reconciliação":   "processo de ligar termos livres a conceitos organizados e equivalentes.",
    }
    return {w: m for w, m in glossary.items() if w in normalize(text)}


def get_user_tags_for_work(store: Store, work_id: str) -> List[str]:
    uid = get_user_id()
    return [t["tag"] for t in store.tags() if t["work_id"] == work_id and t.get("user_id") == uid]


def render_accessibility_controls(store: Store, work: Dict[str, Any]) -> None:
    user_tags = get_user_tags_for_work(store, work["id"])
    description = build_description(work, user_tags)
    st.markdown('<div class="glass smallPanel">', unsafe_allow_html=True)
    st.markdown("**⚙ acessibilidade**")
    col_a, col_b = st.columns([1, 1])
    with col_a:
        st.session_state["font_scale"] = st.slider(
            "tamanho da fonte", 0.9, 1.6,
            float(st.session_state.get("font_scale", 1.0)), 0.05,
            key=f"font_{work['id']}",
        )
        st.session_state["high_contrast"] = st.toggle(
            "contraste reforçado",
            value=bool(st.session_state.get("high_contrast", False)),
            key=f"contrast_{work['id']}",
        )
    with col_b:
        speech_html(description, key=f"speech_{work['id']}")

    st.markdown("**descrição detalhada**")
    st.markdown(f'<div class="helper">{html.escape(description)}</div>', unsafe_allow_html=True)
    words = explain_words(description)
    if words:
        choice = st.selectbox(
            "explicar palavra complexa", ["nenhuma"] + list(words.keys()),
            key=f"explain_sel_{work['id']}",
        )
        if choice != "nenhuma":
            st.info(words[choice])
    st.markdown('</div>', unsafe_allow_html=True)


# ── Gallery ────────────────────────────────────────────────────────────────────
def render_gallery(store: Store) -> None:
    works = store.works()
    for work in works:
        st.markdown('<div class="glass workCard">', unsafe_allow_html=True)
        st.image(work["image"], use_container_width=True)

        # Work title
        st.markdown(
            f'<div style="padding:.4rem .2rem .6rem .2rem;">'
            f'<strong style="font-size:1.08rem">{html.escape(work["title"])}</strong>'
            f'<span class="helper"> · {html.escape(work["artist"])}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

        col_btn1, col_btn2 = st.columns([1, 1])
        with col_btn1:
            if st.button("✏ marcar obra", key=f"mark_{work['id']}"):
                current = st.session_state.get("open_work")
                st.session_state["open_work"] = None if current == work["id"] else work["id"]
                st.session_state["show_accessibility"] = None
                st.rerun()
        with col_btn2:
            if st.button("♿ acessibilidade", key=f"acc_{work['id']}"):
                current = st.session_state.get("show_accessibility")
                st.session_state["show_accessibility"] = None if current == work["id"] else work["id"]
                st.session_state["open_work"] = None
                st.rerun()

        if st.session_state.get("open_work") == work["id"]:
            st.markdown('<div class="glass smallPanel" style="margin-top:.5rem">', unsafe_allow_html=True)
            tag_text = st.text_input(
                "sua tag", placeholder="escreva uma tag para esta obra",
                label_visibility="collapsed", key=f"tag_input_{work['id']}",
            )
            c1, c2 = st.columns([1, 1])
            with c1:
                if st.button("💾 registrar tag", key=f"save_tag_{work['id']}"):
                    if tag_text.strip():
                        store.add_tag(work["id"], tag_text, get_user_id())
                        st.success("Tag registrada com sucesso.")
                        st.rerun()
                    else:
                        st.warning("Escreva uma tag antes de registrar.")
            with c2:
                if st.button("✕ fechar", key=f"close_tag_{work['id']}"):
                    st.session_state["open_work"] = None
                    st.rerun()

            tags = get_user_tags_for_work(store, work["id"])
            if tags:
                st.markdown("**suas tags nesta obra:**")
                st.markdown(
                    " ".join([f'<span class="tagPill">{html.escape(t)}</span>' for t in tags]),
                    unsafe_allow_html=True,
                )
            else:
                st.markdown('<div class="helper">Nenhuma tag sua nesta obra ainda.</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        if st.session_state.get("show_accessibility") == work["id"]:
            render_accessibility_controls(store, work)

        st.markdown('</div>', unsafe_allow_html=True)


# ── ML helpers ────────────────────────────────────────────────────────────────
def build_learning_index(store: Store) -> List[Dict[str, Any]]:
    works = {w["id"]: w for w in store.works()}
    validations = {v["tag_id"]: v for v in store.validations() if v.get("decision") == "approved"}
    ontology_labels = [o["label"] for o in store.ontologies()]
    index = []
    for tag in store.tags():
        work = works.get(tag["work_id"])
        if not work:
            continue
        val = validations.get(tag["id"], {})
        index.append({
            "tag_id":          tag["id"],
            "tag":             tag["tag"],
            "norm":            normalize(tag["tag"]),
            "work_id":         work["id"],
            "title":           work["title"],
            "artist":          work["artist"],
            "museum":          work["museum"],
            "period":          work["period"],
            "technique":       work["technique"],
            "material":        work["material"],
            "metadata_tokens": list({
                *tokenize(work["title"]), *tokenize(work["artist"]),
                *tokenize(work["museum"]), *tokenize(work["period"]),
                *tokenize(work["technique"]), *tokenize(work["material"]),
                *[normalize(x) for x in work.get("institution_tags", [])],
            }),
            "validated_category": val.get("category", ""),
            "validated_concept":  val.get("concept_label", ""),
            "ontology_matches":   [o for o in ontology_labels if o in normalize(tag["tag"])],
        })
    return index


def predict_category_and_concept(
    store: Store, raw_tag: str, work: Dict[str, Any]
) -> Dict[str, Any]:
    tag_n = normalize(raw_tag)
    ontology_labels = [o["label"] for o in store.ontologies()]
    validations = [v for v in store.validations() if v.get("decision") == "approved"]
    by_cat, by_concept = Counter(), Counter()
    for v in validations:
        source = next((t for t in store.tags() if t["id"] == v.get("tag_id")), None)
        if not source:
            continue
        sim = token_overlap(tag_n, normalize(source["tag"]))
        if sim > 0:
            by_cat[v.get("category", "outro")] += sim
            if v.get("concept_label"):
                by_concept[v["concept_label"]] += sim
    category = (
        by_cat.most_common(1)[0][0]
        if by_cat
        else infer_category_from_metadata(tag_n, work)
    )
    concept = (
        by_concept.most_common(1)[0][0]
        if by_concept
        else next((o for o in ontology_labels if o in tag_n), "")
    )
    return {"category": category, "concept": concept, "confidence": round(0.55 if by_cat else 0.45, 2)}


def infer_category_from_metadata(tag_n: str, work: Dict[str, Any]) -> str:
    if tag_n in [normalize(x) for x in work.get("institution_tags", [])]:
        return "tema"
    if any(t in tag_n for t in tokenize(work["artist"])):
        return "pessoa"
    if any(t in tag_n for t in tokenize(work.get("place", ""))):
        return "lugar"
    if any(t in tag_n for t in tokenize(work["technique"])):
        return "técnica"
    if any(t in tag_n for t in tokenize(work["material"])):
        return "material"
    if any(t in tag_n for t in tokenize(work["period"])):
        return "período"
    return "tema"


def similar_examples(
    store: Store, raw_tag: str, work_id: str
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    rows = build_learning_index(store)
    examples, parallels = [], []
    for row in rows:
        sim = max(token_overlap(raw_tag, row["tag"]), char_similarity(raw_tag, row["tag"]))
        if sim <= 0:
            continue
        item = {"tag": row["tag"], "work": row["title"], "score": round(sim, 2)}
        if row["work_id"] == work_id:
            examples.append(item)
        else:
            parallels.append(item)
    examples.sort(key=lambda x: x["score"], reverse=True)
    parallels.sort(key=lambda x: x["score"], reverse=True)
    return examples[:3], parallels[:5]


# ── Validation ────────────────────────────────────────────────────────────────
def render_validation(store: Store) -> None:
    st.markdown(
        '<div class="glass smallPanel">'
        '<div class="sectionTitle">validação curatorial</div>'
        '<div class="helper">Revise as tags, aproxime conceitos, gerencie ontologias e reduza '
        'erros por repetição, grafia e confusão semântica.</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # ── Ontology quick-management inside validation ──────────────────────────
    with st.expander("⚙ criar e gerenciar ontologias"):
        _render_ontology_form(store)
        _render_ontology_list(store)

    st.markdown('<div class="hr"></div>', unsafe_allow_html=True)

    # ── Pending tags ─────────────────────────────────────────────────────────
    works = {w["id"]: w for w in store.works()}
    validated = {v["tag_id"] for v in store.validations()}
    pending = [t for t in store.tags() if t["id"] not in validated]

    if not pending:
        st.info("✓ Não há tags pendentes de validação neste momento.")
        return

    st.markdown(
        f'<div class="glass smallPanel"><span class="helper">'
        f'{len(pending)} tag(s) aguardando revisão</span></div>',
        unsafe_allow_html=True,
    )

    for tag in pending:
        work = works.get(tag["work_id"])
        if not work:
            continue
        pred = predict_category_and_concept(store, tag["tag"], work)
        ex1, ex2 = similar_examples(store, tag["tag"], work["id"])

        st.markdown('<div class="glass smallPanel">', unsafe_allow_html=True)
        st.markdown(
            f'<strong style="font-size:1.05rem">{html.escape(tag["tag"])}</strong>'
            f'<span class="helper"> · {html.escape(work["title"])}</span>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="helper" style="margin:.4rem 0">'
            f'categoria prevista: <strong>{pred["category"]}</strong> '
            f'(confiança {pred["confidence"]}) · '
            f'conceito sugerido: <strong>{pred["concept"] or "nenhum"}</strong><br>'
            f'museu: {html.escape(work["museum"])} · '
            f'período: {html.escape(work["period"])} · '
            f'técnica: {html.escape(work["technique"])}'
            f'</div>',
            unsafe_allow_html=True,
        )
        if ex1:
            st.markdown("**Exemplos próximos na mesma obra:**")
            for item in ex1:
                st.markdown(f"- `{item['tag']}` · similaridade {item['score']}")
        if ex2:
            st.markdown("**Ligações com outras obras:**")
            for item in ex2:
                st.markdown(f"- `{item['tag']}` · {item['work']} · {item['score']}")

        col1, col2, col3 = st.columns(3)
        with col1:
            category = st.selectbox(
                "categoria validada", CATEGORIES,
                index=max(0, CATEGORIES.index(pred["category"]) if pred["category"] in CATEGORIES else 0),
                key=f"cat_{tag['id']}",
            )
        ontology_options = ["nenhum"] + [o["label"] for o in store.ontologies()]
        with col2:
            concept_label = st.selectbox(
                "conceito reconciliado", ontology_options,
                index=ontology_options.index(pred["concept"]) if pred["concept"] in ontology_options else 0,
                key=f"concept_{tag['id']}",
            )
        with col3:
            decision = st.selectbox("decisão", ["approved", "rejected"], key=f"decision_{tag['id']}")

        notes = st.text_area("notas curatoriais", key=f"notes_{tag['id']}", height=80)

        if st.button("💾 registrar validação", key=f"save_val_{tag['id']}"):
            store.add_validation({
                "id": f"val-{len(store.validations())+1}",
                "tag_id": tag["id"],
                "work_id": work["id"],
                "decision": decision,
                "category": category,
                "concept_label": "" if concept_label == "nenhum" else concept_label,
                "notes": notes.strip(),
                "timestamp": now_str(),
            })
            st.success("Validação registrada.")
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)


# ── Ontologies ────────────────────────────────────────────────────────────────
def _render_ontology_form(store: Store) -> None:
    """Inline form to create a new ontology."""
    c1, c2 = st.columns([1, 1])
    with c1:
        label = st.text_input("nome da ontologia", key="ont_label_v2", placeholder="ex: iconografia")
    with c2:
        desc = st.text_input("descrição breve", key="ont_desc_v2", placeholder="ex: representações simbólicas")
    if st.button("➕ criar ontologia", key="create_ontology_v2"):
        if label.strip():
            store.add_ontology(label, desc)
            st.success(f'Ontologia "{label.strip()}" criada.')
            st.rerun()
        else:
            st.warning("Informe o nome da ontologia.")


def _render_ontology_list(store: Store) -> None:
    """List existing ontologies with delete buttons."""
    onts = store.ontologies()
    if not onts:
        st.markdown('<div class="helper">Nenhuma ontologia cadastrada ainda.</div>', unsafe_allow_html=True)
        return
    st.markdown(f'<div class="helper">{len(onts)} ontologia(s) cadastrada(s):</div>', unsafe_allow_html=True)
    for ont in onts:
        col1, col2 = st.columns([6, 1])
        with col1:
            st.markdown(
                f'<div class="glass smallPanel" style="padding:.6rem 1rem;">'
                f'<strong>{html.escape(ont["label"])}</strong>'
                f'<span class="helper"> — {html.escape(ont.get("description", ""))}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
        with col2:
            if st.button("🗑 excluir", key=f"del_ont_v2_{ont['id']}"):
                store.delete_ontology(ont["id"])
                st.rerun()


def render_ontologies(store: Store) -> None:
    st.markdown(
        '<div class="glass smallPanel">'
        '<div class="sectionTitle">ontologias</div>'
        '<div class="helper">Crie, revise e exclua ontologias conceituais usadas para '
        'reconciliar termos livres com categorias organizadas.</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    _render_ontology_form(store)
    st.markdown('<div class="hr"></div>', unsafe_allow_html=True)
    _render_ontology_list(store)


# ── Search & learning ─────────────────────────────────────────────────────────
def real_search(store: Store, query: str) -> List[Dict[str, Any]]:
    q = normalize(query)
    validations_by_tag = {v["tag_id"]: v for v in store.validations() if v.get("decision") == "approved"}
    work_tags = defaultdict(list)
    concepts_by_work = defaultdict(list)
    for tag in store.tags():
        work_tags[tag["work_id"]].append(tag["tag"])
        val = validations_by_tag.get(tag["id"])
        if val and val.get("concept_label"):
            concepts_by_work[tag["work_id"]].append(val["concept_label"])
    results = []
    for work in store.works():
        metadata = (
            [work["title"], work["artist"], work["museum"],
             work["period"], work["technique"], work["material"],
             work.get("place",""), work.get("collection","")]
            + work.get("institution_tags", [])
            + work.get("open_data", [])
        )
        score = 0.0
        matched_metadata, matched_tags, matched_concepts = [], [], []
        for item in metadata:
            if not item:
                continue
            s = max(token_overlap(q, normalize(item)), char_similarity(q, normalize(item)))
            if s > 0:
                score += s * 1.5
                matched_metadata.append(item)
        for tag in work_tags.get(work["id"], []):
            s = max(token_overlap(q, normalize(tag)), char_similarity(q, normalize(tag)))
            if s > 0:
                score += s * 2.0
                matched_tags.append(tag)
        for concept in concepts_by_work.get(work["id"], []):
            s = max(token_overlap(q, normalize(concept)), char_similarity(q, normalize(concept)))
            if s > 0:
                score += s * 2.3
                matched_concepts.append(concept)
        if score > 0:
            results.append({
                "title": work["title"], "artist": work["artist"],
                "museum": work["museum"], "image": work.get("image",""),
                "score": round(score, 2),
                "matched_metadata": matched_metadata[:8],
                "matched_tags": matched_tags[:8],
                "matched_concepts": matched_concepts[:8],
            })
    return sorted(results, key=lambda x: x["score"], reverse=True)


def render_search_learning(store: Store) -> None:
    st.markdown(
        '<div class="glass smallPanel">'
        '<div class="sectionTitle">busca conectada</div>'
        '<div class="helper">Cruza metadados institucionais, tags públicas, validações e ontologias. '
        'O mecanismo aprende com as validações aprovadas.</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    query = st.text_input(
        "busca conectada",
        placeholder="tema, técnica, material, lugar, artista, conceito ou tag…",
        key="search_query_real",
    )
    if query.strip():
        results = real_search(store, query)
        if not results:
            st.info("Nenhum resultado relevante encontrado.")
            return
        st.markdown(f'<div class="helper">{len(results)} resultado(s) encontrado(s)</div>', unsafe_allow_html=True)
        for item in results:
            st.markdown(
                f'<div class="glass smallPanel">'
                f'<strong>{html.escape(item["title"])} · {html.escape(item["artist"])}</strong>'
                f'<span class="helper"> — score {item["score"]}</span><br>'
                f'<span class="helper">museu: {html.escape(item["museum"])}</span><br>'
                f'<span class="helper">metadados: {", ".join(item["matched_metadata"]) or "—"}</span><br>'
                f'<span class="helper">tags: {", ".join(item["matched_tags"]) or "—"}</span><br>'
                f'<span class="helper">conceitos: {", ".join(item["matched_concepts"]) or "—"}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )


# ── Temporal analysis ──────────────────────────────────────────────────────────
def temporal_summary(store: Store) -> Dict[str, List[Dict[str, Any]]]:
    tags = store.tags()
    works = {w["id"]: w["title"] for w in store.works()}
    out: Dict[str, Any] = {
        "day":   defaultdict(list),
        "month": defaultdict(list),
        "year":  defaultdict(list),
    }
    for tag in tags:
        try:
            ts = datetime.strptime(tag["timestamp"], "%Y-%m-%d %H:%M:%S")
        except Exception:
            continue
        out["day"][ts.strftime("%Y-%m-%d")].append(tag)
        out["month"][ts.strftime("%Y-%m")].append(tag)
        out["year"][ts.strftime("%Y")].append(tag)
    result = {}
    for key, buckets in out.items():
        data = []
        for period, items in sorted(buckets.items()):
            data.append({
                "period": period,
                "count":  len(items),
                "works":  sorted({works.get(i["work_id"], i["work_id"]) for i in items}),
                "tags":   sorted({i["tag"] for i in items}),
            })
        result[key] = data
    return result


def render_temporal(store: Store) -> None:
    st.markdown(
        '<div class="glass smallPanel">'
        '<div class="sectionTitle">análise temporal</div>'
        '<div class="helper">Acompanha as tags criadas por dia, mês e ano, '
        'mostrando termos observados e obras envolvidas.</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    summary = temporal_summary(store)
    if not any(summary.get(k) for k in ("day","month","year")):
        st.info("Ainda não há tags suficientes para análise temporal.")
        return
    tabs = st.tabs(["por dia", "por mês", "por ano"])
    for tab, key, label in zip(tabs, ["day","month","year"], ["dia","mês","ano"]):
        with tab:
            data = summary.get(key, [])
            if not data:
                st.info(f"Sem dados por {label}.")
                continue
            # Bar chart via plotly if available
            if PLOTLY_AVAILABLE:
                periods = [b["period"] for b in data]
                counts  = [b["count"] for b in data]
                fig = go.Figure(go.Bar(
                    x=periods, y=counts,
                    marker_color="rgba(37,99,235,0.55)",
                    marker_line_color="rgba(37,99,235,0.9)",
                    marker_line_width=1.5,
                ))
                fig.update_layout(
                    height=280,
                    margin=dict(l=0,r=0,t=20,b=0),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    xaxis=dict(showgrid=False, color="#4b5563"),
                    yaxis=dict(showgrid=True, gridcolor="rgba(17,24,39,0.06)", color="#4b5563"),
                )
                st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})
            for bucket in data:
                st.markdown(
                    f'<div class="glass smallPanel">'
                    f'<strong>{bucket["period"]}</strong>'
                    f'<span class="helper"> · {bucket["count"]} tag(s)</span><br>'
                    f'<span class="helper">obras: {", ".join(bucket["works"])}<br>'
                    f'tags: {", ".join(bucket["tags"][:20])}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )


# ── 3D Network ────────────────────────────────────────────────────────────────
def build_network(store: Store) -> Optional[Any]:
    if not PLOTLY_AVAILABLE:
        return None

    selected  = st.session_state.get("network_types", list(NODE_COLORS.keys()))
    node_size = st.session_state.get("network_size", 11)
    works      = store.works()
    validations = {v["tag_id"]: v for v in store.validations() if v.get("decision") == "approved"}

    nodes:  List[Dict[str,Any]] = []
    edges:  List[Tuple[str,str]] = []
    index:  Dict[str,int] = {}

    def add_node(node_id: str, label: str, kind: str) -> None:
        if kind not in selected:
            return
        if node_id not in index:
            index[node_id] = len(nodes)
            nodes.append({"id": node_id, "label": label, "kind": kind})

    def add_edge(a: str, b: str) -> None:
        if a in index and b in index:
            edges.append((a, b))

    for work in works:
        wid = f"obra:{work['id']}"
        add_node(wid, work["title"], "obra")
        for attr, kind, prefix in [
            ("artist",    "artista",  "artista"),
            ("museum",    "museu",    "museu"),
            ("period",    "período",  "periodo"),
            ("technique", "técnica",  "tecnica"),
            ("material",  "material", "material"),
        ]:
            nid = f"{prefix}:{work[attr]}"
            add_node(nid, work[attr], kind)
            add_edge(wid, nid)
        for od in work.get("open_data", []):
            oid = f"open:{od}"
            add_node(oid, od, "open_data")
            add_edge(wid, oid)

    for tag in store.tags():
        work = next((w for w in works if w["id"] == tag["work_id"]), None)
        if not work:
            continue
        tid = f"tag:{tag['id']}"
        add_node(tid, tag["tag"], "tag")
        add_edge(f"obra:{work['id']}", tid)
        val = validations.get(tag["id"])
        if val and val.get("concept_label"):
            cid = f"conceito:{val['concept_label']}"
            add_node(cid, val["concept_label"], "conceito")
            add_edge(tid, cid)

    if not nodes:
        return None

    # Fibonacci sphere layout
    n      = len(nodes)
    golden = math.pi * (3 - math.sqrt(5))
    xs, ys, zs = [], [], []
    for i in range(n):
        y      = 1 - (i / float(max(1, n - 1))) * 2
        radius = math.sqrt(max(0.0, 1 - y * y))
        theta  = golden * i
        xs.append(math.cos(theta) * radius)
        ys.append(y)
        zs.append(math.sin(theta) * radius)

    x_edge, y_edge, z_edge = [], [], []
    for a, b in edges:
        ia, ib = index[a], index[b]
        x_edge += [xs[ia], xs[ib], None]
        y_edge += [ys[ia], ys[ib], None]
        z_edge += [zs[ia], zs[ib], None]

    fig = go.Figure()
    fig.add_trace(go.Scatter3d(
        x=x_edge, y=y_edge, z=z_edge,
        mode="lines",
        line=dict(color="rgba(100,120,160,0.20)", width=1.5),
        hoverinfo="none", showlegend=False,
    ))

    by_kind: Dict[str, list] = defaultdict(list)
    for i, node in enumerate(nodes):
        by_kind[node["kind"]].append((i, node))

    for kind, items in by_kind.items():
        fig.add_trace(go.Scatter3d(
            x=[xs[i] for i, _ in items],
            y=[ys[i] for i, _ in items],
            z=[zs[i] for i, _ in items],
            mode="markers+text",
            text=[node["label"] for _, node in items],
            textposition="top center",
            textfont=dict(size=9, color="#374151"),
            marker=dict(
                size=node_size,
                color=NODE_COLORS.get(kind, "#374151"),
                opacity=0.88,
                line=dict(width=1, color="rgba(255,255,255,0.6)"),
            ),
            name=kind,
            hovertemplate="%{text}<extra>" + kind + "</extra>",
        ))

    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        height=780,
        paper_bgcolor="rgba(255,255,255,0)",
        plot_bgcolor="rgba(255,255,255,0)",
        scene=dict(
            bgcolor="rgba(255,255,255,0)",
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            zaxis=dict(visible=False),
            camera=dict(eye=dict(x=1.45, y=1.4, z=1.15)),
            dragmode="turntable",
        ),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, x=0,
            font=dict(size=11, color="#374151"),
            bgcolor="rgba(255,255,255,0.45)",
            bordercolor="rgba(255,255,255,0.70)",
            borderwidth=1,
        ),
    )
    return fig


def render_network(store: Store) -> None:
    st.markdown(
        '<div class="glass smallPanel">'
        '<div class="sectionTitle">teia 3d de conectividade</div>'
        '<div class="helper">Rede de interoperabilidade entre metadados institucionais, '
        'tags públicas, conceitos validados, ontologias e fontes externas. '
        'Gire, aproxime, filtre camadas e redimensione nós.</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    if not PLOTLY_AVAILABLE:
        st.error("Plotly não está disponível. Execute: pip install plotly")
        return

    col1, col2 = st.columns([4, 1])
    with col2:
        st.session_state["network_types"] = st.multiselect(
            "camadas visíveis", list(NODE_COLORS.keys()),
            default=st.session_state.get("network_types", list(NODE_COLORS.keys())),
            key="net_types",
        )
        st.session_state["network_size"] = st.slider(
            "tamanho dos nós", 6, 22,
            int(st.session_state.get("network_size", 11)), 1,
            key="net_size",
        )
        # Legend
        st.markdown('<div style="margin-top:.8rem">', unsafe_allow_html=True)
        for kind, color in NODE_COLORS.items():
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">'
                f'<span style="width:12px;height:12px;border-radius:50%;background:{color};display:inline-block"></span>'
                f'<span style="font-size:.82rem;color:#4b5563">{kind}</span></div>',
                unsafe_allow_html=True,
            )
        st.markdown('</div>', unsafe_allow_html=True)

    with col1:
        fig = build_network(store)
        if fig is not None:
            st.plotly_chart(
                fig, use_container_width=True,
                config={"displaylogo": False, "scrollZoom": True, "responsive": True},
                key="network_3d_main",
            )
        else:
            st.info("Adicione obras e tags para visualizar a teia 3D.")


# ── Works admin ────────────────────────────────────────────────────────────────
def render_works_admin(store: Store) -> None:
    st.markdown(
        '<div class="glass smallPanel">'
        '<div class="sectionTitle">obras</div>'
        '<div class="helper">Cadastre novas obras e gerencie o acervo. '
        'Excluir uma obra remove também todas as suas tags e validações.</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    with st.expander("➕ adicionar nova obra"):
        col_l, col_r = st.columns(2)
        with col_l:
            title      = st.text_input("título *",         key="new_title")
            artist     = st.text_input("artista",          key="new_artist")
            museum     = st.text_input("museu",            key="new_museum")
            period     = st.text_input("período",          key="new_period")
            technique  = st.text_input("técnica",          key="new_technique")
        with col_r:
            material         = st.text_input("material",             key="new_material")
            place            = st.text_input("lugar",                key="new_place")
            collection       = st.text_input("coleção",              key="new_collection")
            image            = st.text_input("url da imagem *",      key="new_image")
            institution_tags = st.text_input(
                "tags institucionais (separadas por vírgula)", key="new_inst_tags"
            )
            open_data_str    = st.text_input(
                "fontes externas (separadas por vírgula)",    key="new_open_data"
            )

        if image.strip():
            st.image(image.strip(), width=200)

        if st.button("💾 adicionar obra", key="save_new_work"):
            if title.strip() and image.strip():
                store.add_work({
                    "id": f"obra-{slug(title)}-{len(store.works())+1}",
                    "title":      title.strip(),
                    "artist":     artist.strip(),
                    "museum":     museum.strip(),
                    "period":     period.strip(),
                    "technique":  technique.strip(),
                    "material":   material.strip(),
                    "place":      place.strip(),
                    "collection": collection.strip(),
                    "institution_tags": [x.strip() for x in institution_tags.split(",") if x.strip()],
                    "open_data":  [x.strip() for x in open_data_str.split(",")  if x.strip()],
                    "image":      image.strip(),
                })
                st.success(f'Obra "{title.strip()}" adicionada.')
                st.rerun()
            else:
                st.warning("Preencha pelo menos o título (*) e a URL da imagem (*).")

    st.markdown('<div class="hr"></div>', unsafe_allow_html=True)
    works = store.works()
    st.markdown(
        f'<div class="helper">{len(works)} obra(s) no acervo</div>',
        unsafe_allow_html=True,
    )

    for work in works:
        col_img, col_info, col_del = st.columns([1, 5, 1])
        with col_img:
            if work.get("image"):
                st.image(work["image"], width=90)
        with col_info:
            tag_count = sum(1 for t in store.tags() if t["work_id"] == work["id"])
            st.markdown(
                f'<div class="glass smallPanel" style="padding:.7rem 1rem">'
                f'<strong>{html.escape(work["title"])}</strong>'
                f'<span class="helper"> · {html.escape(work.get("artist",""))}</span><br>'
                f'<span class="helper">'
                f'{html.escape(work.get("museum",""))} · '
                f'{html.escape(work.get("period",""))} · '
                f'{html.escape(work.get("technique",""))}'
                f'</span><br>'
                f'<span class="helper" style="font-size:.8rem">'
                f'{tag_count} tag(s) · ID: {work["id"]}'
                f'</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
        with col_del:
            st.markdown("")
            if st.button("🗑", key=f"del_work_{work['id']}", help=f"Excluir {work['title']}"):
                store.delete_work(work["id"])
                st.success(f'"{work["title"]}" removida.')
                st.rerun()


# ── Export ─────────────────────────────────────────────────────────────────────
def export_pdf_bytes(store: Store) -> Optional[bytes]:
    if not REPORTLAB_AVAILABLE:
        return None

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2.2*cm, rightMargin=2.2*cm,
        topMargin=2.2*cm,  bottomMargin=2.2*cm,
    )
    styles  = getSampleStyleSheet()
    palette = dict(
        title=rlcolors.HexColor("#1e3a5f"),
        blue=rlcolors.HexColor("#2563eb"),
        grey=rlcolors.HexColor("#6b7280"),
        light=rlcolors.HexColor("#f1f5f9"),
        border=rlcolors.HexColor("#e2e8f0"),
        red=rlcolors.HexColor("#dc2626"),
        green=rlcolors.HexColor("#16a34a"),
    )

    title_style = ParagraphStyle(
        "FolkTitle", parent=styles["Title"],
        textColor=palette["title"], fontSize=26, spaceAfter=4,
        fontName="Helvetica-Bold",
    )
    heading_style = ParagraphStyle(
        "FolkHead", parent=styles["Heading2"],
        textColor=palette["blue"], fontSize=13, spaceBefore=12, spaceAfter=4,
        fontName="Helvetica-Bold",
    )
    sub_style = ParagraphStyle(
        "FolkSub", parent=styles["BodyText"],
        textColor=palette["grey"], fontSize=9, spaceAfter=2,
        fontName="Helvetica",
    )
    body_style = ParagraphStyle(
        "FolkBody", parent=styles["BodyText"],
        textColor=rlcolors.HexColor("#111827"), fontSize=10, spaceAfter=4,
        fontName="Helvetica",
    )

    story = []

    # ── Cover ─────────────────────────────────────────────────────────────────
    story.append(Paragraph("folksonomia", title_style))
    story.append(Paragraph(
        f"Relatório gerado em {datetime.now().strftime('%d/%m/%Y às %H:%M')}",
        sub_style,
    ))
    story.append(Spacer(1, 6))
    story.append(HRFlowable(width="100%", thickness=1, color=palette["border"]))
    story.append(Spacer(1, 10))

    # ── Summary metrics ───────────────────────────────────────────────────────
    works_l       = store.works()
    tags_l        = store.tags()
    validations_l = store.validations()
    ontologies_l  = store.ontologies()

    approved  = [v for v in validations_l if v.get("decision") == "approved"]
    rejected  = [v for v in validations_l if v.get("decision") == "rejected"]
    pending_n = max(0, len(tags_l) - len(validations_l))

    summary_data = [
        ["Métrica", "Valor"],
        ["Obras monitoradas",  str(len(works_l))],
        ["Tags coletadas",     str(len(tags_l))],
        ["Validações totais",  str(len(validations_l))],
        ["  ↳ aprovadas",      str(len(approved))],
        ["  ↳ rejeitadas",     str(len(rejected))],
        ["Fila curatorial",    str(pending_n)],
        ["Ontologias ativas",  str(len(ontologies_l))],
    ]
    tbl = Table(summary_data, colWidths=[9*cm, 5*cm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), palette["blue"]),
        ("TEXTCOLOR",  (0,0), (-1,0), rlcolors.white),
        ("FONTNAME",   (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",   (0,0), (-1,0), 10),
        ("BACKGROUND", (0,1), (-1,-1), palette["light"]),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [rlcolors.white, palette["light"]]),
        ("FONTNAME",   (0,1), (-1,-1), "Helvetica"),
        ("FONTSIZE",   (0,1), (-1,-1), 9),
        ("GRID",       (0,0), (-1,-1), 0.5, palette["border"]),
        ("LEFTPADDING",  (0,0), (-1,-1), 8),
        ("RIGHTPADDING", (0,0), (-1,-1), 8),
        ("TOPPADDING",   (0,0), (-1,-1), 5),
        ("BOTTOMPADDING",(0,0), (-1,-1), 5),
        ("ROUNDEDCORNERS", [4]),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 14))

    # ── Works detail ──────────────────────────────────────────────────────────
    story.append(Paragraph("Acervo monitorado", heading_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=palette["border"]))
    story.append(Spacer(1, 6))

    for work in works_l:
        story.append(Paragraph(f"{work['title']} · {work['artist']}", heading_style))
        meta_rows = [
            ["Museu",     work.get("museum","—")],
            ["Período",   work.get("period","—")],
            ["Técnica",   work.get("technique","—")],
            ["Material",  work.get("material","—")],
            ["Lugar",     work.get("place","—")],
            ["Coleção",   work.get("collection","—")],
        ]
        meta_tbl = Table(meta_rows, colWidths=[4*cm, 12*cm])
        meta_tbl.setStyle(TableStyle([
            ("FONTNAME",   (0,0), (0,-1), "Helvetica-Bold"),
            ("FONTNAME",   (1,0), (1,-1), "Helvetica"),
            ("FONTSIZE",   (0,0), (-1,-1), 9),
            ("TEXTCOLOR",  (0,0), (0,-1), palette["grey"]),
            ("TEXTCOLOR",  (1,0), (1,-1), rlcolors.HexColor("#111827")),
            ("TOPPADDING",   (0,0),(-1,-1), 3),
            ("BOTTOMPADDING",(0,0),(-1,-1), 3),
            ("LEFTPADDING",  (0,0),(-1,-1), 0),
        ]))
        story.append(meta_tbl)

        # Tags
        work_tags_all = [t["tag"] for t in tags_l if t["work_id"] == work["id"]]
        if work_tags_all:
            story.append(Paragraph(
                f"Tags ({len(work_tags_all)}): " + ", ".join(work_tags_all[:30]),
                body_style,
            ))
        else:
            story.append(Paragraph("Tags: nenhuma registrada.", sub_style))

        # Validated tags
        work_vals = [v for v in approved if v.get("work_id") == work["id"]]
        if work_vals:
            val_rows = [["Tag", "Categoria", "Conceito", "Notas"]]
            for v in work_vals[:10]:
                src_tag = next((t["tag"] for t in tags_l if t["id"] == v["tag_id"]), v["tag_id"])
                val_rows.append([
                    src_tag[:30],
                    v.get("category","—"),
                    v.get("concept_label","—") or "—",
                    (v.get("notes","") or "—")[:40],
                ])
            val_tbl = Table(val_rows, colWidths=[4*cm, 3*cm, 3.5*cm, 5.5*cm])
            val_tbl.setStyle(TableStyle([
                ("BACKGROUND",  (0,0), (-1,0), palette["green"]),
                ("TEXTCOLOR",   (0,0), (-1,0), rlcolors.white),
                ("FONTNAME",    (0,0), (-1,0), "Helvetica-Bold"),
                ("FONTSIZE",    (0,0), (-1,-1), 8),
                ("FONTNAME",    (0,1), (-1,-1), "Helvetica"),
                ("GRID",        (0,0), (-1,-1), 0.3, palette["border"]),
                ("ROWBACKGROUNDS", (0,1), (-1,-1), [rlcolors.white, palette["light"]]),
                ("LEFTPADDING",  (0,0),(-1,-1), 5),
                ("RIGHTPADDING", (0,0),(-1,-1), 5),
                ("TOPPADDING",   (0,0),(-1,-1), 3),
                ("BOTTOMPADDING",(0,0),(-1,-1), 3),
            ]))
            story.append(Spacer(1, 4))
            story.append(val_tbl)

        story.append(Spacer(1, 10))
        story.append(HRFlowable(width="100%", thickness=0.4, color=palette["border"]))
        story.append(Spacer(1, 6))

    # ── Ontologies ────────────────────────────────────────────────────────────
    if ontologies_l:
        story.append(Paragraph("Ontologias conceituais", heading_style))
        ont_data = [["Rótulo", "Descrição"]] + [
            [o["label"], o.get("description","—")] for o in ontologies_l
        ]
        ont_tbl = Table(ont_data, colWidths=[5*cm, 11*cm])
        ont_tbl.setStyle(TableStyle([
            ("BACKGROUND",  (0,0), (-1,0), palette["title"]),
            ("TEXTCOLOR",   (0,0), (-1,0), rlcolors.white),
            ("FONTNAME",    (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTNAME",    (0,1), (-1,-1), "Helvetica"),
            ("FONTSIZE",    (0,0), (-1,-1), 9),
            ("GRID",        (0,0), (-1,-1), 0.4, palette["border"]),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [rlcolors.white, palette["light"]]),
            ("LEFTPADDING",  (0,0),(-1,-1), 6),
            ("TOPPADDING",   (0,0),(-1,-1), 4),
            ("BOTTOMPADDING",(0,0),(-1,-1), 4),
        ]))
        story.append(ont_tbl)

    doc.build(story)
    return buf.getvalue()


def render_export(store: Store) -> None:
    st.markdown(
        '<div class="glass smallPanel">'
        '<div class="sectionTitle">exportar dados</div>'
        '<div class="helper">Exporte o relatório em PDF ou os dados em JSON para '
        'análise externa e documentação institucional.</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Relatório PDF completo**")
        if REPORTLAB_AVAILABLE:
            pdf_data = export_pdf_bytes(store)
            if pdf_data:
                st.download_button(
                    "⬇ exportar relatório PDF",
                    data=pdf_data,
                    file_name=f"folksonomia_relatorio_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                    mime="application/pdf",
                    key="dl_pdf",
                )
            else:
                st.error("Erro ao gerar PDF.")
        else:
            st.warning("reportlab não disponível. Execute: pip install reportlab")

    with col2:
        st.markdown("**Dados estruturados (JSON)**")
        st.download_button(
            "⬇ exportar tags",
            data=json.dumps(store.tags(), ensure_ascii=False, indent=2),
            file_name="tags.json", mime="application/json", key="dl_tags",
        )
        st.download_button(
            "⬇ exportar obras",
            data=json.dumps(store.works(), ensure_ascii=False, indent=2),
            file_name="works.json", mime="application/json", key="dl_works",
        )
        st.download_button(
            "⬇ exportar ontologias",
            data=json.dumps(store.ontologies(), ensure_ascii=False, indent=2),
            file_name="ontologies.json", mime="application/json", key="dl_ont",
        )
        st.download_button(
            "⬇ exportar validações",
            data=json.dumps(store.validations(), ensure_ascii=False, indent=2),
            file_name="validations.json", mime="application/json", key="dl_val",
        )


# ── Admin panel ────────────────────────────────────────────────────────────────
def render_admin(store: Store) -> None:
    if not st.session_state.get("admin_logged", False):
        st.markdown(
            '<div class="glass smallPanel">'
            '<div class="sectionTitle">área administrativa</div>'
            '<div class="helper">Credenciais necessárias para acessar '
            'monitoramento, validação, ontologias, análise temporal e teia 3D.</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        login    = st.text_input("login",  key="admin_login")
        password = st.text_input("senha",  type="password", key="admin_password")
        if st.button("→ entrar", key="admin_enter"):
            if store.admin_ok(login, password):
                st.session_state["admin_logged"] = True
                st.rerun()
            else:
                st.error("Credenciais inválidas.")
        return

    tabs = st.tabs([
        "📊 painel",
        "✅ validação",
        "🏷 ontologias",
        "🔍 busca",
        "📅 temporal",
        "🕸 teia 3d",
        "🖼 obras",
        "📤 exportar",
    ])

    with tabs[0]:
        c1, c2, c3, c4 = st.columns(4)
        metrics = [
            ("obras monitoradas",  len(store.works()),                                      "acervo ativo"),
            ("tags coletadas",     len(store.tags()),                                       "marcação pública acumulada"),
            ("fila curatorial",    max(0, len(store.tags()) - len(store.validations())),    "itens aguardando revisão"),
            ("ontologias",         len(store.ontologies()),                                 "estrutura conceitual"),
        ]
        for col, (t, v, n) in zip([c1, c2, c3, c4], metrics):
            with col:
                st.markdown(
                    f'<div class="glass metric">'
                    f'<div class="t">{t}</div>'
                    f'<div class="v">{v}</div>'
                    f'<div class="n">{n}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        # Approved vs rejected chart
        approved_n  = sum(1 for v in store.validations() if v.get("decision") == "approved")
        rejected_n  = sum(1 for v in store.validations() if v.get("decision") == "rejected")
        if (approved_n + rejected_n) > 0 and PLOTLY_AVAILABLE:
            st.markdown('<div style="margin-top:1rem">', unsafe_allow_html=True)
            fig_pie = go.Figure(go.Pie(
                labels=["aprovadas","rejeitadas"],
                values=[approved_n, rejected_n],
                marker_colors=["#16a34a","#dc2626"],
                hole=0.55,
                textinfo="percent+label",
            ))
            fig_pie.update_layout(
                height=260, margin=dict(l=0,r=0,t=20,b=0),
                paper_bgcolor="rgba(0,0,0,0)",
                showlegend=True,
                legend=dict(bgcolor="rgba(255,255,255,0.3)"),
            )
            st.plotly_chart(fig_pie, use_container_width=True, config={"displaylogo":False})
            st.markdown('</div>', unsafe_allow_html=True)

        st.markdown(
            '<div class="glass smallPanel" style="margin-top:.8rem">'
            '<div class="helper">O painel acompanha o que a instituição coleta na participação '
            'pública, o que ainda precisa de revisão e como as camadas institucionais se conectam '
            'aos termos sociais.</div>'
            '</div>',
            unsafe_allow_html=True,
        )

    with tabs[1]:
        render_validation(store)
    with tabs[2]:
        render_ontologies(store)
    with tabs[3]:
        render_search_learning(store)
    with tabs[4]:
        render_temporal(store)
    with tabs[5]:
        render_network(store)
    with tabs[6]:
        render_works_admin(store)
    with tabs[7]:
        render_export(store)

    st.markdown('<div style="height:1rem"></div>', unsafe_allow_html=True)
    if st.button("← sair da administração", key="admin_logout"):
        st.session_state["admin_logged"] = False
        st.rerun()


# ── Public intro flow ──────────────────────────────────────────────────────────
def intro_flow(store: Store) -> None:
    st.markdown(
        '<div class="glass smallPanel">'
        '<div class="sectionTitle">acesso inicial</div>'
        '<div class="helper">'
        'Antes de marcar as obras, responda brevemente ao questionário abaixo. '
        'Suas respostas ajudam a entender o perfil dos participantes.'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    familiarity   = st.selectbox(
        "1. qual é a sua frequência de visita a museus?",
        ["nunca","raramente","ocasionalmente","frequentemente"],
        key="intro_familiarity",
    )
    documentation = st.selectbox(
        "2. você já ouviu falar sobre documentação museológica?",
        ["nenhum","já ouvi falar","tenho noção básica","conheço bem"],
        key="intro_documentation",
    )
    understanding = st.text_area(
        "3. o que você entende por tags aplicadas a acervos? descreva com suas palavras.",
        placeholder="escreva com suas palavras…",
        key="intro_understanding",
    )
    if st.button("→ liberar acesso às obras", key="unlock_button"):
        if understanding.strip():
            store.add_questionnaire({
                "user_id":       get_user_id(),
                "familiarity":   familiarity,
                "documentation": documentation,
                "understanding": understanding.strip(),
                "timestamp":     now_str(),
            })
            st.session_state["public_access"] = True
            st.rerun()
        else:
            st.warning("Preencha a terceira resposta para liberar o acesso.")


def render_public(store: Store) -> None:
    tabs = st.tabs(["🖼 explorar obras", "⚙ área administrativa"])
    with tabs[0]:
        if not st.session_state.get("public_access", False):
            intro_flow(store)
        else:
            render_gallery(store)
    with tabs[1]:
        render_admin(store)


# ── Main ───────────────────────────────────────────────────────────────────────
def main() -> None:
    store = Store()
    inject_css()
    render_brand()
    render_public(store)


if __name__ == "__main__":
    main()
