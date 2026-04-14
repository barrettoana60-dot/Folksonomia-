from __future__ import annotations

import html
import hashlib
import json
import math
import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st
import streamlit.components.v1 as components

try:
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except Exception:
    go = None
    PLOTLY_AVAILABLE = False

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
    REPORTLAB_AVAILABLE = True
except Exception:
    REPORTLAB_AVAILABLE = False

APP_DIR = Path("data_folksonomia_clean")
WORKS_FILE = APP_DIR / "works.json"
TAGS_FILE = APP_DIR / "tags.json"
QUESTIONNAIRE_FILE = APP_DIR / "questionnaire.json"
VALIDATIONS_FILE = APP_DIR / "validations.json"
ONTOLOGIES_FILE = APP_DIR / "ontologies.json"
ADMIN_FILE = APP_DIR / "admin.json"

ADMIN_LOGIN = "nugep239@"
ADMIN_PASSWORD = "nugep123"
CATEGORIES = ["tema", "pessoa", "lugar", "período", "técnica", "material", "evento", "conceito", "outro"]
NODE_COLORS = {
    "obra": "#1d4ed8",
    "artista": "#7c3aed",
    "museu": "#0f766e",
    "período": "#dc2626",
    "técnica": "#b45309",
    "material": "#0ea5e9",
    "tag": "#111827",
    "conceito": "#16a34a",
    "open_data": "#9333ea",
}

st.set_page_config(page_title="folksonomia", layout="wide", initial_sidebar_state="collapsed")


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
                {"id": "ont-tema", "label": "tema", "description": "conceitos temáticos"},
                {"id": "ont-material", "label": "material", "description": "materiais e suportes"},
                {"id": "ont-tecnica", "label": "técnica", "description": "modos de feitura"},
            ])
        if not ADMIN_FILE.exists():
            save_json(ADMIN_FILE, {"login": ADMIN_LOGIN, "password_hash": hashlib.sha256(ADMIN_PASSWORD.encode()).hexdigest()})

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

    def save_tags(self, data: List[Dict[str, Any]]) -> None:
        save_json(TAGS_FILE, data)

    def save_works(self, data: List[Dict[str, Any]]) -> None:
        save_json(WORKS_FILE, data)

    def save_validations(self, data: List[Dict[str, Any]]) -> None:
        save_json(VALIDATIONS_FILE, data)

    def save_ontologies(self, data: List[Dict[str, Any]]) -> None:
        save_json(ONTOLOGIES_FILE, data)

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
        data.append({"id": f"ont-{slug(label)}-{len(data)+1}", "label": label.strip(), "description": description.strip()})
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


def get_user_id() -> str:
    if "public_user_id" not in st.session_state:
        st.session_state["public_user_id"] = hashlib.sha1(str(datetime.now().timestamp()).encode()).hexdigest()[:12]
    return st.session_state["public_user_id"]


def inject_css() -> None:
    scale = float(st.session_state.get("font_scale", 1.0))
    contrast = bool(st.session_state.get("high_contrast", False))
    base_font = max(16, int(18 * scale))
    text = "#111111" if not contrast else "#000000"
    sub = "#4b5563" if not contrast else "#1f2937"
    glass = "rgba(255,255,255,0.44)" if not contrast else "rgba(255,255,255,0.78)"
    border = "rgba(17,24,39,0.12)"
    button = "linear-gradient(135deg, rgba(255,255,255,0.18), rgba(9,21,48,0.74))"
    st.markdown(f"""
    <style>
    :root {{
        --txt: {text};
        --sub: {sub};
        --glass: {glass};
        --border: {border};
        --button: {button};
        --baseFont: {base_font}px;
    }}
    html, body, [data-testid="stAppViewContainer"], .stApp {{
        background: radial-gradient(circle at top, #f3f3f3 0%, #ececec 36%, #e8e8e8 100%);
        color: var(--txt);
        font-family: "Times New Roman", Georgia, serif;
        font-size: var(--baseFont);
    }}
    #MainMenu, header, footer {{visibility:hidden;}}
    .block-container {{max-width: 1280px; padding-top: 1rem; padding-bottom: 2rem;}}
    .glass {{
        background: var(--glass);
        border: 1px solid var(--border);
        border-radius: 28px;
        backdrop-filter: blur(18px);
        box-shadow: inset 0 8px 22px rgba(255,255,255,0.35), 0 8px 24px rgba(0,0,0,0.04);
    }}
    .titleBar {{padding: 1rem 1.25rem; margin-bottom: .8rem;}}
    .titleBar h1 {{margin:0; font-size: clamp(2.2rem, 4vw, 3.2rem); color: var(--txt);}}
    .titleBar p {{margin:.25rem 0 0 0; color: var(--sub);}}
    .helper {{color: var(--sub); line-height: 1.7;}}
    .workCard {{padding:.7rem; margin-bottom:1rem;}}
    .workCard img {{width:100%; display:block; border-radius:22px;}}
    .smallPanel {{padding:.9rem 1rem;}}
    .tagPill {{display:inline-block; margin:.12rem .2rem .12rem 0; padding:.24rem .68rem; border-radius:999px; background:rgba(255,255,255,.6); border:1px solid rgba(17,24,39,.1); color:var(--txt);}}
    .metric {{padding:1rem 1.1rem; min-height:116px;}}
    .metric .t {{color: var(--sub); text-transform: uppercase; letter-spacing: .12em; font-size:.82rem;}}
    .metric .v {{font-size: 2rem; font-weight:700; margin-top:.3rem; color:var(--txt);}}
    .metric .n {{margin-top:.25rem; color: var(--sub);}}
    .sectionTitle {{font-size:2rem; font-weight:700; color:var(--txt); margin:.1rem 0 .6rem 0;}}

    .stButton > button, div[data-testid="stFormSubmitButton"] button {{
        width:100%;
        border-radius: 22px !important;
        background: var(--button) !important;
        border: 1px solid rgba(255,255,255,0.26) !important;
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
        font-weight: 700 !important;
        text-shadow: 0 1px 2px rgba(0,0,0,.32) !important;
        box-shadow: 0 10px 24px rgba(0,0,0,.14), inset 0 1px 0 rgba(255,255,255,.18) !important;
        padding: .82rem 1rem !important;
    }}
    .stButton > button:hover, div[data-testid="stFormSubmitButton"] button:hover {{filter: brightness(1.04);}}

    .stTextInput input, .stTextArea textarea {{
        background: rgba(255,255,255,.88) !important;
        color: #111111 !important;
        -webkit-text-fill-color: #111111 !important;
        border: 1px solid rgba(17,24,39,.18) !important;
        border-radius: 18px !important;
        caret-color: #111111 !important;
    }}
    .stTextInput input::placeholder, .stTextArea textarea::placeholder {{color:#6b7280 !important; opacity:1 !important;}}
    .stTextArea textarea {{min-height: 120px;}}

    .stSelectbox [data-baseweb="select"] > div {{
        background: rgba(20,24,40,.9) !important;
        color: #ffffff !important;
        border: 1px solid rgba(255,255,255,.14) !important;
        border-radius: 18px !important;
    }}
    .stSelectbox [data-baseweb="select"] * {{
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
        fill: #ffffff !important;
    }}
    div[data-baseweb="popover"] *, ul[role="listbox"] *, div[role="listbox"] * {{
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
    }}
    div[data-baseweb="popover"] ul, div[data-baseweb="popover"] li, ul[role="listbox"], li[role="option"], div[role="option"] {{
        background: rgba(17,24,39,.96) !important;
        color: #ffffff !important;
    }}
    li[aria-selected="true"], div[aria-selected="true"] {{
        background: rgba(59,130,246,.3) !important;
    }}

    .stTabs [data-baseweb="tab-list"] {{
        gap: .45rem; background: rgba(255,255,255,.24); border-radius: 28px; padding:.35rem; border:1px solid rgba(17,24,39,.1);
    }}
    .stTabs [data-baseweb="tab"] {{border-radius:22px; color: var(--txt);}}
    .stTabs [aria-selected="true"] {{background: rgba(255,255,255,.75) !important; box-shadow: inset 0 -4px 0 #ef4444;}}
    label, .stMarkdown, p, li, span, strong, h1, h2, h3 {{color: var(--txt) !important; font-family:"Times New Roman", Georgia, serif !important;}}
    .hr {{height:1px; background: rgba(17,24,39,.08); margin:.9rem 0;}}
    </style>
    """, unsafe_allow_html=True)


def render_brand() -> None:
    st.markdown(
        """
        <div class="glass titleBar">
            <h1>folksonomia</h1>
            <p>marcação pública, acessibilidade, validação, ontologias, análise temporal e teia 3d conectada.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def speech_html(text: str, key: str) -> None:
    safe = json.dumps(text)
    components.html(
        f"""
        <div style='display:flex;gap:8px;'>
          <button onclick='window.speechSynthesis.cancel(); const u = new SpeechSynthesisUtterance({safe}); u.lang="pt-BR"; u.rate=0.95; window.speechSynthesis.speak(u);' style='padding:10px 14px;border-radius:14px;border:none;background:#0f172a;color:white;'>ouvir descrição</button>
          <button onclick='window.speechSynthesis.cancel();' style='padding:10px 14px;border-radius:14px;border:none;background:#334155;color:white;'>parar leitura</button>
        </div>
        """,
        height=56,
        key=key,
    )


def build_description(work: Dict[str, Any], user_tags: List[str]) -> str:
    title = work["title"]
    base = [
        f"Imagem da obra {title}, de {work['artist']}, pertencente ao museu {work['museum']}.",
        f"Período {work['period']}, técnica {work['technique']} e material {work['material']}.",
    ]
    title_n = normalize(title)
    if "guernica" in title_n:
        base.append("A cena é monocromática, em preto, branco e cinzas. Aparecem figuras fragmentadas, um cavalo central em tensão, um touro à esquerda, braços erguidos, rostos partidos e uma atmosfera de bombardeio, dor e movimento brusco.")
    elif "noite estrelada" in title_n or "starry" in title_n:
        base.append("A imagem mostra um céu noturno em espirais intensas, estrelas brilhantes, lua amarela e uma vila ao fundo. O movimento das pinceladas faz o céu parecer girar sobre a paisagem.")
    elif "mona" in title_n:
        base.append("Trata-se de um retrato frontal de uma mulher sentada, com expressão serena e sorriso discreto. O fundo mostra uma paisagem suave e nebulosa, em tons terrosos e verdes.")
    if user_tags:
        base.append("As tags registradas nesta imagem até agora incluem: " + ", ".join(user_tags[:10]) + ".")
    base.append("Essa descrição foi montada a partir dos metadados institucionais e das marcações públicas disponíveis.")
    return " ".join(base)


def explain_words(text: str) -> Dict[str, str]:
    glossary = {
        "bombardeio": "ataque com explosões lançadas sobre um local.",
        "fragmentadas": "divididas em partes, sem continuidade visual completa.",
        "monocromática": "imagem construída com uma variação muito restrita de cores.",
        "pós-impressionismo": "movimento artístico posterior ao impressionismo, com cor e forma mais expressivas.",
        "renascimento": "período artístico europeu marcado por estudo da perspectiva, anatomia e equilíbrio formal.",
        "ontologia": "estrutura que organiza conceitos, categorias e relações entre elementos de um domínio.",
        "interoperabilidade": "capacidade de sistemas e bases diferentes trocarem e entenderem informações entre si.",
        "reconciliação": "processo de ligar termos livres a conceitos organizados e equivalentes.",
    }
    found = {}
    for word, meaning in glossary.items():
        if word in normalize(text):
            found[word] = meaning
    return found


def get_user_tags_for_work(store: Store, work_id: str) -> List[str]:
    uid = get_user_id()
    return [t["tag"] for t in store.tags() if t["work_id"] == work_id and t.get("user_id") == uid]


def render_accessibility_controls(store: Store, work: Dict[str, Any]) -> None:
    user_tags = get_user_tags_for_work(store, work["id"])
    description = build_description(work, user_tags)
    st.markdown('<div class="glass smallPanel">', unsafe_allow_html=True)
    st.markdown("**acessibilidade**")
    col_a, col_b = st.columns([1, 1])
    with col_a:
        st.session_state["font_scale"] = st.slider("tamanho da fonte", 0.9, 1.6, float(st.session_state.get("font_scale", 1.0)), 0.05, key=f"font_{work['id']}")
        st.session_state["high_contrast"] = st.toggle("contraste reforçado", value=bool(st.session_state.get("high_contrast", False)), key=f"contrast_{work['id']}")
    with col_b:
        speech_html(description, key=f"speech_{work['id']}")
    st.markdown("**descrição detalhada da imagem**")
    st.markdown(f'<div class="helper">{html.escape(description)}</div>', unsafe_allow_html=True)
    words = explain_words(description)
    if words:
        choice = st.selectbox("explicar palavra complexa", ["nenhuma"] + list(words.keys()), key=f"explain_sel_{work['id']}")
        if choice != "nenhuma":
            st.info(words[choice])
    st.markdown('</div>', unsafe_allow_html=True)


def render_gallery(store: Store) -> None:
    works = store.works()
    for work in works:
        st.markdown('<div class="glass workCard">', unsafe_allow_html=True)
        st.image(work["image"], use_container_width=True)
        col_btn1, col_btn2 = st.columns([1, 1])
        with col_btn1:
            if st.button("Marcar", key=f"mark_{work['id']}"):
                current = st.session_state.get("open_work")
                st.session_state["open_work"] = None if current == work["id"] else work["id"]
                st.session_state["show_accessibility"] = None
                st.rerun()
        with col_btn2:
            if st.button("Acessibilidade", key=f"acc_{work['id']}"):
                current = st.session_state.get("show_accessibility")
                st.session_state["show_accessibility"] = None if current == work["id"] else work["id"]
                st.session_state["open_work"] = None
                st.rerun()

        if st.session_state.get("open_work") == work["id"]:
            st.markdown('<div class="glass smallPanel">', unsafe_allow_html=True)
            st.markdown('<div class="helper">sua tag</div>', unsafe_allow_html=True)
            tag_text = st.text_input("sua tag", placeholder="escreva a tag", label_visibility="collapsed", key=f"tag_input_{work['id']}")
            c1, c2 = st.columns([1, 1])
            with c1:
                if st.button("registrar tag", key=f"save_tag_{work['id']}"):
                    if tag_text.strip():
                        store.add_tag(work["id"], tag_text, get_user_id())
                        st.success("Tag registrada.")
                        st.session_state[f"tag_input_{work['id']}"] = ""
                        st.rerun()
                    else:
                        st.warning("Escreva uma tag antes de registrar.")
            with c2:
                if st.button("fechar", key=f"close_tag_{work['id']}"):
                    st.session_state["open_work"] = None
                    st.rerun()
            tags = get_user_tags_for_work(store, work["id"])
            st.markdown("**suas tags nesta imagem**")
            if tags:
                st.markdown(" ".join([f'<span class="tagPill">{html.escape(t)}</span>' for t in tags]), unsafe_allow_html=True)
            else:
                st.markdown('<div class="helper">Nenhuma tag registrada por você nesta imagem ainda.</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        if st.session_state.get("show_accessibility") == work["id"]:
            render_accessibility_controls(store, work)
        st.markdown('</div>', unsafe_allow_html=True)


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
            "tag_id": tag["id"],
            "tag": tag["tag"],
            "norm": normalize(tag["tag"]),
            "work_id": work["id"],
            "title": work["title"],
            "artist": work["artist"],
            "museum": work["museum"],
            "period": work["period"],
            "technique": work["technique"],
            "material": work["material"],
            "metadata_tokens": list({*tokenize(work["title"]), *tokenize(work["artist"]), *tokenize(work["museum"]), *tokenize(work["period"]), *tokenize(work["technique"]), *tokenize(work["material"]), *[normalize(x) for x in work.get("institution_tags", [])]}),
            "validated_category": val.get("category", ""),
            "validated_concept": val.get("concept_label", ""),
            "ontology_matches": [o for o in ontology_labels if o in normalize(tag["tag"])],
        })
    return index


def predict_category_and_concept(store: Store, raw_tag: str, work: Dict[str, Any]) -> Dict[str, Any]:
    tag_n = normalize(raw_tag)
    ontology_labels = [o["label"] for o in store.ontologies()]
    validations = [v for v in store.validations() if v.get("decision") == "approved"]
    by_cat = Counter()
    by_concept = Counter()
    for v in validations:
        source = next((t for t in store.tags() if t["id"] == v.get("tag_id")), None)
        if not source:
            continue
        sim = token_overlap(tag_n, normalize(source["tag"]))
        if sim > 0:
            by_cat[v.get("category", "outro")] += sim
            if v.get("concept_label"):
                by_concept[v["concept_label"]] += sim
    category = by_cat.most_common(1)[0][0] if by_cat else infer_category_from_metadata(tag_n, work)
    concept = by_concept.most_common(1)[0][0] if by_concept else next((o for o in ontology_labels if o in tag_n), "")
    conf = 0.55 if by_cat else 0.45
    return {"category": category, "concept": concept, "confidence": round(conf, 2)}


def infer_category_from_metadata(tag_n: str, work: Dict[str, Any]) -> str:
    if tag_n in [normalize(x) for x in work.get("institution_tags", [])]:
        return "tema"
    if any(t in tag_n for t in tokenize(work["artist"])):
        return "pessoa"
    if any(t in tag_n for t in tokenize(work["place"])):
        return "lugar"
    if any(t in tag_n for t in tokenize(work["technique"])):
        return "técnica"
    if any(t in tag_n for t in tokenize(work["material"])):
        return "material"
    if any(t in tag_n for t in tokenize(work["period"])):
        return "período"
    return "tema"


def token_overlap(a: str, b: str) -> float:
    sa, sb = set(tokenize(a)), set(tokenize(b))
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def similar_examples(store: Store, raw_tag: str, work_id: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    rows = build_learning_index(store)
    examples = []
    parallels = []
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


def char_similarity(a: str, b: str) -> float:
    a, b = normalize(a), normalize(b)
    if not a or not b:
        return 0.0
    same = sum(1 for ch1, ch2 in zip(a, b) if ch1 == ch2)
    return same / max(len(a), len(b))


def render_validation(store: Store) -> None:
    st.markdown('<div class="glass smallPanel">', unsafe_allow_html=True)
    st.markdown('<div class="sectionTitle">validação</div>', unsafe_allow_html=True)
    st.markdown('<div class="helper">Aqui a equipe de documentação revisa as tags, aproxima conceitos, administra ontologias e reduz erros por repetição, grafia e confusão semântica.</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    works = {w["id"]: w for w in store.works()}
    validated = {v["tag_id"] for v in store.validations()}
    pending = [t for t in store.tags() if t["id"] not in validated]
    if not pending:
        st.info("Não há tags pendentes de validação neste momento.")
        return
    for tag in pending:
        work = works.get(tag["work_id"])
        if not work:
            continue
        pred = predict_category_and_concept(store, tag["tag"], work)
        ex1, ex2 = similar_examples(store, tag["tag"], work["id"])
        st.markdown('<div class="glass smallPanel">', unsafe_allow_html=True)
        st.markdown(f"### {tag['tag']} · {work['title']}")
        st.markdown(f"<div class='helper'>previsão de categoria: <strong>{pred['category']}</strong> · confiança {pred['confidence']}<br>conceito sugerido: <strong>{pred['concept'] or 'nenhum'}</strong><br>museu: {html.escape(work['museum'])} · período: {html.escape(work['period'])} · técnica: {html.escape(work['technique'])}</div>", unsafe_allow_html=True)
        if ex1:
            st.markdown("**3 exemplos próximos na mesma obra**")
            for item in ex1:
                st.markdown(f"- {item['tag']} · similaridade {item['score']}")
        if ex2:
            st.markdown("**ligações em comum com outras obras**")
            for item in ex2:
                st.markdown(f"- {item['tag']} · {item['work']} · similaridade {item['score']}")
        col1, col2, col3 = st.columns(3)
        with col1:
            category = st.selectbox("categoria validada", CATEGORIES, index=max(0, CATEGORIES.index(pred['category']) if pred['category'] in CATEGORIES else 0), key=f"cat_{tag['id']}")
        ontology_options = ["nenhum"] + [o["label"] for o in store.ontologies()]
        with col2:
            concept_label = st.selectbox("conceito reconciliado", ontology_options, index=ontology_options.index(pred['concept']) if pred['concept'] in ontology_options else 0, key=f"concept_{tag['id']}")
        with col3:
            decision = st.selectbox("decisão", ["approved", "rejected"], key=f"decision_{tag['id']}")
        notes = st.text_area("notas curatoriais", key=f"notes_{tag['id']}", height=90)
        if st.button("registrar validação", key=f"save_val_{tag['id']}"):
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


def render_ontologies(store: Store) -> None:
    st.markdown('<div class="glass smallPanel">', unsafe_allow_html=True)
    st.markdown('<div class="sectionTitle">ontologias</div>', unsafe_allow_html=True)
    st.markdown('<div class="helper">Crie, revise e exclua ontologias conceituais usadas para reconciliar termos livres do público com categorias organizadas.</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    with st.container():
        c1, c2 = st.columns([1, 1])
        with c1:
            label = st.text_input("nome da ontologia", key="ont_label")
        with c2:
            desc = st.text_input("descrição", key="ont_desc")
        if st.button("criar ontologia", key="create_ontology"):
            if label.strip():
                store.add_ontology(label, desc)
                st.success("Ontologia criada.")
                st.rerun()
    for ont in store.ontologies():
        col1, col2 = st.columns([5, 1])
        with col1:
            st.markdown(f'<div class="glass smallPanel"><strong>{html.escape(ont["label"])}</strong><br><span class="helper">{html.escape(ont.get("description", ""))}</span></div>', unsafe_allow_html=True)
        with col2:
            if st.button("excluir", key=f"del_ont_{ont['id']}"):
                store.delete_ontology(ont["id"])
                st.rerun()


def real_search(store: Store, query: str) -> List[Dict[str, Any]]:
    q = normalize(query)
    results = []
    validations_by_tag = {v["tag_id"]: v for v in store.validations() if v.get("decision") == "approved"}
    work_tags = defaultdict(list)
    concepts_by_work = defaultdict(list)
    for tag in store.tags():
        work_tags[tag["work_id"]].append(tag["tag"])
        val = validations_by_tag.get(tag["id"])
        if val and val.get("concept_label"):
            concepts_by_work[tag["work_id"]].append(val["concept_label"])
    for work in store.works():
        metadata = [work["title"], work["artist"], work["museum"], work["period"], work["technique"], work["material"], work["place"], work["collection"]] + work.get("institution_tags", []) + work.get("open_data", [])
        score = 0.0
        matched_metadata, matched_tags, matched_concepts = [], [], []
        for item in metadata:
            if not item:
                continue
            norm = normalize(item)
            s = max(token_overlap(q, norm), char_similarity(q, norm))
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
                "title": work["title"], "artist": work["artist"], "museum": work["museum"],
                "score": round(score, 2),
                "matched_metadata": matched_metadata[:8],
                "matched_tags": matched_tags[:8],
                "matched_concepts": matched_concepts[:8],
            })
    return sorted(results, key=lambda x: x["score"], reverse=True)


def render_search_learning(store: Store) -> None:
    st.markdown('<div class="glass smallPanel">', unsafe_allow_html=True)
    st.markdown('<div class="sectionTitle">busca conectada e aprendizagem</div>', unsafe_allow_html=True)
    st.markdown('<div class="helper">A busca cruza metadados institucionais, tags públicas, validações e ontologias. O mecanismo aprende com as validações aprovadas e melhora a reconciliação dos termos.</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    query = st.text_input("busca conectada", placeholder="tema, técnica, material, lugar, artista, conceito ou tag", key="search_query_real")
    if query.strip():
        results = real_search(store, query)
        if not results:
            st.info("Nenhum resultado relevante foi encontrado.")
        for item in results:
            st.markdown(f'<div class="glass smallPanel"><strong>{html.escape(item["title"])} · {html.escape(item["artist"])} </strong><br><span class="helper">museu: {html.escape(item["museum"])} · score {item["score"]}</span><br><span class="helper">metadados: {", ".join(item["matched_metadata"]) or "nenhum"}<br>tags: {", ".join(item["matched_tags"]) or "nenhuma"}<br>conceitos: {", ".join(item["matched_concepts"]) or "nenhum"}</span></div>', unsafe_allow_html=True)


def temporal_summary(store: Store) -> Dict[str, List[Dict[str, Any]]]:
    tags = store.tags()
    works = {w["id"]: w["title"] for w in store.works()}
    out = {"day": defaultdict(list), "month": defaultdict(list), "year": defaultdict(list)}
    for tag in tags:
        ts = datetime.strptime(tag["timestamp"], "%Y-%m-%d %H:%M:%S")
        out["day"][ts.strftime("%Y-%m-%d")].append(tag)
        out["month"][ts.strftime("%Y-%m")].append(tag)
        out["year"][ts.strftime("%Y")].append(tag)
    result = {}
    for key, buckets in out.items():
        data = []
        for period, items in sorted(buckets.items()):
            data.append({
                "period": period,
                "count": len(items),
                "works": sorted({works.get(i["work_id"], i["work_id"]) for i in items}),
                "tags": sorted({i["tag"] for i in items}),
            })
        result[key] = data
    return result


def render_temporal(store: Store) -> None:
    st.markdown('<div class="glass smallPanel">', unsafe_allow_html=True)
    st.markdown('<div class="sectionTitle">análise temporal</div>', unsafe_allow_html=True)
    st.markdown('<div class="helper">A leitura temporal acompanha as tags criadas por dia, mês e ano, mostrando termos observados e obras envolvidas em cada período.</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    summary = temporal_summary(store)
    if not summary["day"]:
        st.info("Ainda não há tags suficientes para análise temporal.")
        return
    tabs = st.tabs(["por dia", "por mês", "por ano"])
    for tab, key in zip(tabs, ["day", "month", "year"]):
        with tab:
            for bucket in summary[key]:
                st.markdown(f'<div class="glass smallPanel"><strong>{bucket["period"]}</strong><br><span class="helper">total de tags: {bucket["count"]}<br>obras: {", ".join(bucket["works"])}<br>tags observadas: {", ".join(bucket["tags"][:20])}</span></div>', unsafe_allow_html=True)


def build_network(store: Store) -> Optional[Any]:
    if not PLOTLY_AVAILABLE:
        return None
    selected = st.session_state.get("network_types", list(NODE_COLORS.keys()))
    node_size = st.session_state.get("network_size", 11)
    works = store.works()
    validations = {v["tag_id"]: v for v in store.validations() if v.get("decision") == "approved"}

    nodes = []
    edges = []
    index = {}

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
        artist = f"artista:{work['artist']}"
        museum = f"museu:{work['museum']}"
        period = f"periodo:{work['period']}"
        tech = f"tecnica:{work['technique']}"
        material = f"material:{work['material']}"
        add_node(artist, work["artist"], "artista")
        add_node(museum, work["museum"], "museu")
        add_node(period, work["period"], "período")
        add_node(tech, work["technique"], "técnica")
        add_node(material, work["material"], "material")
        add_edge(wid, artist)
        add_edge(wid, museum)
        add_edge(wid, period)
        add_edge(wid, tech)
        add_edge(wid, material)
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

    n = len(nodes)
    golden = math.pi * (3 - math.sqrt(5))
    xs, ys, zs = [], [], []
    for i, node in enumerate(nodes):
        y = 1 - (i / float(max(1, n - 1))) * 2
        radius = math.sqrt(max(0.0, 1 - y * y))
        theta = golden * i
        x = math.cos(theta) * radius
        z = math.sin(theta) * radius
        xs.append(x)
        ys.append(y)
        zs.append(z)

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
        line=dict(color="rgba(80,80,80,0.25)", width=2),
        hoverinfo="none",
        showlegend=False,
    ))

    by_kind = defaultdict(list)
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
            marker=dict(size=node_size, color=NODE_COLORS.get(kind, "#111827"), opacity=0.92),
            name=kind,
            hovertemplate="%{text}<extra>" + kind + "</extra>",
        ))

    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        height=760,
        paper_bgcolor="rgba(255,255,255,0)",
        plot_bgcolor="rgba(255,255,255,0)",
        scene=dict(
            bgcolor="rgba(255,255,255,0)",
            xaxis=dict(visible=False), yaxis=dict(visible=False), zaxis=dict(visible=False),
            camera=dict(eye=dict(x=1.45, y=1.4, z=1.15)),
            dragmode="turntable",
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    )
    return fig


def render_network(store: Store) -> None:
    st.markdown('<div class="glass smallPanel">', unsafe_allow_html=True)
    st.markdown('<div class="sectionTitle">teia 3d de conectividade</div>', unsafe_allow_html=True)
    st.markdown('<div class="helper">Rede de compartilhamento e interoperabilidade entre metadados institucionais, tags públicas, conceitos validados, ontologias e fontes externas. Você pode girar, aproximar, afastar, filtrar camadas e redimensionar os nós.</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    if not PLOTLY_AVAILABLE:
        st.error("Plotly não está disponível nesta execução. Instale a dependência para usar a teia 3D.")
        return
    col1, col2 = st.columns([3, 1])
    with col2:
        st.session_state["network_types"] = st.multiselect("camadas visíveis", list(NODE_COLORS.keys()), default=st.session_state.get("network_types", list(NODE_COLORS.keys())), key="net_types")
        st.session_state["network_size"] = st.slider("tamanho dos nós", 8, 20, int(st.session_state.get("network_size", 11)), 1, key="net_size")
    with col1:
        fig = build_network(store)
        if fig is not None:
            st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False, "scrollZoom": True, "modeBarButtonsToAdd": ["toggleSpikelines"], "responsive": True}, key="network_3d_main")


def render_works_admin(store: Store) -> None:
    st.markdown('<div class="glass smallPanel"><div class="sectionTitle">obras</div><div class="helper">Cadastre novas obras, revise metadados e exclua registros quando necessário.</div></div>', unsafe_allow_html=True)
    with st.expander("adicionar nova obra"):
        title = st.text_input("título", key="new_title")
        artist = st.text_input("artista", key="new_artist")
        museum = st.text_input("museu", key="new_museum")
        period = st.text_input("período", key="new_period")
        technique = st.text_input("técnica", key="new_technique")
        material = st.text_input("material", key="new_material")
        place = st.text_input("lugar", key="new_place")
        collection = st.text_input("coleção", key="new_collection")
        image = st.text_input("url da imagem", key="new_image")
        institution_tags = st.text_input("tags institucionais separadas por vírgula", key="new_inst_tags")
        open_data = st.text_input("fontes externas separadas por vírgula", key="new_open_data")
        if st.button("adicionar obra", key="save_new_work"):
            if title.strip() and image.strip():
                store.add_work({
                    "id": f"obra-{slug(title)}-{len(store.works())+1}",
                    "title": title.strip(), "artist": artist.strip(), "museum": museum.strip(), "period": period.strip(),
                    "technique": technique.strip(), "material": material.strip(), "place": place.strip(), "collection": collection.strip(),
                    "institution_tags": [x.strip() for x in institution_tags.split(",") if x.strip()],
                    "open_data": [x.strip() for x in open_data.split(",") if x.strip()],
                    "image": image.strip(),
                })
                st.success("Obra adicionada.")
                st.rerun()
            else:
                st.warning("Preencha pelo menos título e URL da imagem.")
    for work in store.works():
        col1, col2 = st.columns([5, 1])
        with col1:
            st.markdown(f'<div class="glass smallPanel"><strong>{html.escape(work["title"])} · {html.escape(work["artist"] or "sem artista")}</strong><br><span class="helper">{html.escape(work["museum"])} · {html.escape(work["period"])} · {html.escape(work["technique"])} · {html.escape(work["material"])} </span></div>', unsafe_allow_html=True)
        with col2:
            if st.button("excluir", key=f"del_work_{work['id']}"):
                store.delete_work(work["id"])
                st.rerun()


def export_pdf(store: Store) -> Optional[bytes]:
    if not REPORTLAB_AVAILABLE:
        return None
    pdf_path = APP_DIR / f"relatorio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    doc = SimpleDocTemplate(str(pdf_path), pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    story.append(Paragraph("Relatório Folksonomia", styles["Title"]))
    story.append(Spacer(1, 12))
    story.append(Paragraph(f"Obras monitoradas: {len(store.works())}", styles["BodyText"]))
    story.append(Paragraph(f"Tags coletadas: {len(store.tags())}", styles["BodyText"]))
    story.append(Paragraph(f"Validações: {len(store.validations())}", styles["BodyText"]))
    story.append(Paragraph(f"Ontologias: {len(store.ontologies())}", styles["BodyText"]))
    story.append(Spacer(1, 12))
    for work in store.works():
        story.append(Paragraph(f"{work['title']} · {work['artist']}", styles["Heading3"]))
        story.append(Paragraph(f"Museu: {work['museum']}", styles["BodyText"]))
        story.append(Paragraph(f"Período: {work['period']} · Técnica: {work['technique']} · Material: {work['material']}", styles["BodyText"]))
        related = [t['tag'] for t in store.tags() if t['work_id'] == work['id']]
        story.append(Paragraph("Tags: " + (", ".join(related[:20]) if related else "nenhuma"), styles["BodyText"]))
        story.append(Spacer(1, 8))
    doc.build(story)
    return pdf_path.read_bytes()


def render_export(store: Store) -> None:
    st.markdown('<div class="glass smallPanel"><div class="sectionTitle">exportar</div><div class="helper">Exporte o relatório em PDF ou os dados em CSV para análise externa e documentação institucional.</div></div>', unsafe_allow_html=True)
    pdf_data = export_pdf(store)
    if pdf_data is None:
        st.warning("Não foi possível gerar o PDF nesta execução porque reportlab não está disponível.")
    else:
        st.download_button("exportar pdf", pdf_data, file_name=f"folksonomia_relatorio_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf", mime="application/pdf", key="dl_pdf")
    st.download_button("exportar tags csv", data=json.dumps(store.tags(), ensure_ascii=False, indent=2), file_name="tags.json", mime="application/json", key="dl_tags")
    st.download_button("exportar obras csv", data=json.dumps(store.works(), ensure_ascii=False, indent=2), file_name="works.json", mime="application/json", key="dl_works")
    st.download_button("exportar ontologias csv", data=json.dumps(store.ontologies(), ensure_ascii=False, indent=2), file_name="ontologies.json", mime="application/json", key="dl_ont")


def render_admin(store: Store) -> None:
    if not st.session_state.get("admin_logged", False):
        st.markdown('<div class="glass smallPanel"><div class="sectionTitle">área administrativa</div><div class="helper">Use suas credenciais para entrar na área de monitoramento, validação, ontologias, análise temporal e teia 3d.</div></div>', unsafe_allow_html=True)
        login = st.text_input("login", key="admin_login")
        password = st.text_input("senha", type="password", key="admin_password")
        if st.button("entrar", key="admin_enter"):
            if store.admin_ok(login, password):
                st.session_state["admin_logged"] = True
                st.rerun()
            else:
                st.error("credenciais inválidas.")
        return

    tabs = st.tabs(["painel", "validação", "ontologias", "busca e aprendizagem", "análise temporal", "teia 3d", "obras", "exportar"])
    with tabs[0]:
        c1, c2, c3, c4 = st.columns(4)
        metrics = [
            ("obras monitoradas", len(store.works()), "base institucional ativa"),
            ("tags coletadas", len(store.tags()), "marcação social acumulada"),
            ("fila curatorial", max(0, len(store.tags()) - len(store.validations())), "itens em revisão"),
            ("ontologias", len(store.ontologies()), "estrutura conceitual"),
        ]
        for col, (t, v, n) in zip([c1, c2, c3, c4], metrics):
            with col:
                st.markdown(f'<div class="glass metric"><div class="t">{t}</div><div class="v">{v}</div><div class="n">{n}</div></div>', unsafe_allow_html=True)
        st.markdown('<div class="glass smallPanel"><div class="helper">O painel acompanha o que a instituição coleta na participação pública, o que ainda precisa de revisão e como as camadas institucionais se conectam aos termos sociais.</div></div>', unsafe_allow_html=True)
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
    if st.button("sair da administração", key="admin_logout"):
        st.session_state["admin_logged"] = False
        st.rerun()


def intro_flow(store: Store) -> None:
    st.markdown('<div class="glass smallPanel"><div class="sectionTitle">acesso inicial</div><div class="helper">Primeiro responda ao questionário. Só depois a interface de marcação das obras será liberada.</div></div>', unsafe_allow_html=True)
    familiarity = st.selectbox("1. qual é a sua frequência de visita a museus?", ["nunca", "raramente", "ocasionalmente", "frequentemente"], key="intro_familiarity")
    documentation = st.selectbox("2. você já ouviu falar sobre documentação museológica?", ["nenhum", "já ouvi falar", "tenho noção básica", "conheço bem"], key="intro_documentation")
    understanding = st.text_area("3. o que você entende por tags aplicadas a acervos? descreva com suas palavras.", placeholder="escreva com suas palavras", key="intro_understanding")
    if st.button("liberar acesso às obras", key="unlock_button"):
        if understanding.strip():
            store.add_questionnaire({"user_id": get_user_id(), "familiarity": familiarity, "documentation": documentation, "understanding": understanding.strip(), "timestamp": now_str()})
            st.session_state["public_access"] = True
            st.rerun()
        else:
            st.warning("Escreva sua resposta na terceira pergunta para liberar o acesso.")


def render_public(store: Store) -> None:
    tabs = st.tabs(["explorar obras", "área administrativa"])
    with tabs[0]:
        if not st.session_state.get("public_access", False):
            intro_flow(store)
        else:
            render_gallery(store)
    with tabs[1]:
        render_admin(store)


def main() -> None:
    store = Store()
    inject_css()
    render_brand()
    render_public(store)


if __name__ == "__main__":
    main()
