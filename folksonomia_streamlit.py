import streamlit as st
import pandas as pd
import numpy as np
import os
import json
import base64
import hashlib
import html
import random
import re
import unicodedata
from datetime import datetime
from collections import defaultdict, Counter

warnings_filter = __import__("warnings")
warnings_filter.filterwarnings("ignore")

# ============================================================
# CONFIG
# ============================================================
st.set_page_config(
    page_title="Sistema Folksonomia Digital",
    layout="wide",
    initial_sidebar_state="collapsed",
    page_icon="📚"
)

DATA_DIR = "data"
OBRAS_FILE = os.path.join(DATA_DIR, "obras.json")
TAGS_FILE = os.path.join(DATA_DIR, "tags.json")
USERS_FILE = os.path.join(DATA_DIR, "users.json")
ADMIN_FILE = os.path.join(DATA_DIR, "admin.json")
ONTOLOGIES_FILE = os.path.join(DATA_DIR, "ontologias.json")
LEDGER_FILE = os.path.join(DATA_DIR, "ledger.json")
CIRCULATION_FILE = os.path.join(DATA_DIR, "circulacao.json")
OPEN_DATA_FILE = os.path.join(DATA_DIR, "open_data.json")

ADMIN_USERNAME = "nugep"
ADMIN_PASSWORD = "nugep123"

ANIMAIS = [
    "Águia", "Boto", "Capivara", "Doninha", "Ema", "Falcão", "Gavião", "Harpia", "Irara", "Jaguar",
    "Lontra", "Mico", "Onça", "Paca", "Quati", "Raposa", "Tamanduá", "Urubu", "Veado", "Zorrilho",
    "Arara", "Bugio", "Caititu", "Jaguatirica", "Lobo", "Mutum", "Pirarucu", "Tucano", "Sucuri", "Tatu"
]

ADJETIVOS = [
    "Azul", "Bravo", "Calmo", "Dourado", "Esperto", "Feroz", "Gracioso", "Intenso", "Jovial", "Lento",
    "Mágico", "Nobre", "Ousado", "Preciso", "Rápido", "Sábio", "Tímido", "Único", "Valente", "Zeloso",
    "Curioso", "Furtivo", "Altivo", "Sereno", "Vibrante", "Audaz", "Brilhante", "Corajoso", "Distinto", "Elegante"
]

STATUS_METADADO = ["bruto", "sugerido", "validado", "revisado", "publicado"]
FONT_OPTIONS = ["16px", "18px", "20px", "22px", "24px"]

SEMANTIC_GROUPS = {
    "religioso": [
        "religioso", "religião", "igreja", "santo", "santa", "cristo", "crucifixo", "bíblia",
        "biblia", "anjo", "divino", "sagrado", "maria", "jesus", "oração", "oracao", "altar"
    ],
    "guerra": [
        "guerra", "batalha", "soldado", "arma", "espada", "escudo", "conflito", "militar",
        "exército", "exercito", "violência", "violencia", "sangue", "morte", "ataque", "defesa"
    ],
    "cor": [
        "azul", "verde", "vermelho", "amarelo", "roxo", "rosa", "preto", "branco", "cinza",
        "laranja", "marrom", "dourado", "prateado", "colorido", "escuro", "claro"
    ],
    "natureza": [
        "árvore", "arvore", "flor", "céu", "ceu", "mar", "rio", "montanha", "sol", "lua",
        "estrela", "nuvem", "terra", "animal", "folha", "grama", "floresta"
    ],
    "emoção": [
        "triste", "feliz", "medo", "angústia", "angustia", "dor", "esperança", "esperanca",
        "alegria", "melancolia", "raiva", "calma", "tensão", "tensao", "solidão", "solidao"
    ],
    "forma": [
        "círculo", "circulo", "quadrado", "triângulo", "triangulo", "linha", "curva", "geometria",
        "simetria", "abstrato", "vertical", "horizontal", "volume"
    ]
}

DEFAULT_ONTOLOGIES = [
    {
        "id": 1,
        "nome": "Cores",
        "descricao": "Vocabulário controlado para identificação cromática.",
        "categoria": "visual",
        "termos": ["azul", "verde", "vermelho", "amarelo", "preto", "branco", "cinza", "dourado"],
        "ativo": True,
        "criado_em": None,
        "atualizado_em": None
    },
    {
        "id": 2,
        "nome": "Temáticas Religiosas",
        "descricao": "Vocabulário controlado para temas religiosos.",
        "categoria": "tema",
        "termos": ["religioso", "sagrado", "anjo", "santo", "jesus", "maria", "altar", "igreja"],
        "ativo": True,
        "criado_em": None,
        "atualizado_em": None
    },
    {
        "id": 3,
        "nome": "Conflito e Guerra",
        "descricao": "Vocabulário controlado para guerra, conflito e violência.",
        "categoria": "tema",
        "termos": ["guerra", "batalha", "arma", "soldado", "militar", "sangue", "ataque"],
        "ativo": True,
        "criado_em": None,
        "atualizado_em": None
    }
]

DEFAULT_OBRAS = [
    {
        "id": 1,
        "titulo": "Guernica",
        "artista": "Pablo Picasso",
        "ano": "1937",
        "imagem": "https://upload.wikimedia.org/wikipedia/en/7/74/PicassoGuernica.jpg",
        "audio_descricao": "Pintura monumental em tons de preto, branco e cinza. A composição é fragmentada, com figuras humanas e animais em sofrimento. Há corpos distorcidos, rostos em desespero, um cavalo ferido ao centro, um touro à esquerda e uma lâmpada acima como foco dramático. A cena transmite violência, ruptura e caos de guerra.",
        "metadados": {
            "instituicao": "Acervo Demonstrativo",
            "origem_registro": "seed",
            "status": "publicado"
        }
    },
    {
        "id": 2,
        "titulo": "A Noite Estrelada",
        "artista": "Vincent van Gogh",
        "ano": "1889",
        "imagem": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ea/Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg/1200px-Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg",
        "audio_descricao": "Paisagem noturna com céu azul profundo e redemoinhos luminosos. As estrelas aparecem como círculos brilhantes em amarelo intenso. A lua também se destaca. Abaixo, um vilarejo calmo contrasta com o movimento vibrante do céu. Um cipreste escuro se ergue em primeiro plano.",
        "metadados": {
            "instituicao": "Acervo Demonstrativo",
            "origem_registro": "seed",
            "status": "publicado"
        }
    },
    {
        "id": 3,
        "titulo": "Mona Lisa",
        "artista": "Leonardo da Vinci",
        "ano": "1503",
        "imagem": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ec/Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_retouched.jpg/800px-Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_retouched.jpg",
        "audio_descricao": "Retrato feminino de meio corpo, com expressão serena e sorriso sutil. A personagem está sentada, com as mãos cruzadas. Ao fundo há uma paisagem distante com rios, caminhos e montanhas. Os tons são suaves, em marrom, verde e azul acinzentado.",
        "metadados": {
            "instituicao": "Acervo Demonstrativo",
            "origem_registro": "seed",
            "status": "publicado"
        }
    }
]

# ============================================================
# CORE UTIL
# ============================================================
def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def ensure_data_dir():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)


def load_json_file(filepath, default):
    ensure_data_dir()
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    return default


def save_json_file(filepath, data):
    ensure_data_dir()
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar {filepath}: {e}")
        return False


def generate_animal_name():
    random.seed()
    return f"{random.choice(ANIMAIS)} {random.choice(ADJETIVOS)}"


def gen_uid():
    return base64.b64encode(os.urandom(12)).decode("ascii")


def normalize_text(text):
    text = str(text or "").strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"\s+", " ", text)
    return text


def slugify(text):
    text = normalize_text(text)
    text = re.sub(r"[^a-z0-9\s_-]", "", text)
    text = re.sub(r"[\s-]+", "-", text).strip("-")
    return text


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def safe_int(v, default=0):
    try:
        return int(v)
    except Exception:
        return default


# ============================================================
# LEDGER / BLOCKCHAIN-LIKE AUDIT
# ============================================================
def init_ledger():
    ledger = load_json_file(LEDGER_FILE, [])
    if not ledger:
        genesis = {
            "id": 1,
            "timestamp": now_str(),
            "actor_id": "system",
            "actor_name": "system",
            "actor_role": "system",
            "event_type": "genesis",
            "entity_type": "ledger",
            "entity_id": "genesis",
            "status": "publicado",
            "origin": "system",
            "automatic": False,
            "payload": {"message": "Genesis block do sistema"},
            "prev_hash": "0" * 64
        }
        genesis["hash"] = compute_event_hash(genesis)
        save_json_file(LEDGER_FILE, [genesis])


def compute_event_hash(event):
    event_copy = dict(event)
    event_copy.pop("hash", None)
    canonical = json.dumps(event_copy, ensure_ascii=False, sort_keys=True)
    return sha256_text(canonical)


def append_ledger_event(
    actor_id,
    actor_name,
    actor_role,
    event_type,
    entity_type,
    entity_id,
    payload,
    status="bruto",
    origin="manual",
    automatic=False
):
    init_ledger()
    ledger = load_json_file(LEDGER_FILE, [])
    prev_hash = ledger[-1]["hash"] if ledger else "0" * 64

    event = {
        "id": len(ledger) + 1,
        "timestamp": now_str(),
        "actor_id": actor_id,
        "actor_name": actor_name,
        "actor_role": actor_role,
        "event_type": event_type,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "status": status,
        "origin": origin,
        "automatic": automatic,
        "payload": payload,
        "prev_hash": prev_hash
    }
    event["hash"] = compute_event_hash(event)
    ledger.append(event)
    save_json_file(LEDGER_FILE, ledger)
    update_open_data_snapshot()


def verify_ledger_integrity():
    ledger = load_json_file(LEDGER_FILE, [])
    if not ledger:
        return True, []
    issues = []
    prev_hash = "0" * 64
    for idx, ev in enumerate(ledger):
        expected_hash = compute_event_hash(ev)
        if ev.get("prev_hash") != prev_hash:
            issues.append(f"Evento {ev.get('id')} com prev_hash inconsistente.")
        if ev.get("hash") != expected_hash:
            issues.append(f"Evento {ev.get('id')} com hash inválido.")
        prev_hash = ev.get("hash")
    return len(issues) == 0, issues


def record_circulation(actor_id, actor_name, actor_role, export_type, entity_scope, details):
    records = load_json_file(CIRCULATION_FILE, [])
    record = {
        "id": len(records) + 1,
        "timestamp": now_str(),
        "actor_id": actor_id,
        "actor_name": actor_name,
        "actor_role": actor_role,
        "export_type": export_type,
        "entity_scope": entity_scope,
        "details": details
    }
    records.append(record)
    save_json_file(CIRCULATION_FILE, records)
    append_ledger_event(
        actor_id=actor_id,
        actor_name=actor_name,
        actor_role=actor_role,
        event_type="share_export",
        entity_type="circulacao",
        entity_id=str(record["id"]),
        payload=record,
        status="publicado",
        origin="manual",
        automatic=False
    )


# ============================================================
# DATA INIT
# ============================================================
def check_admin():
    admins = load_json_file(ADMIN_FILE, [])
    if not admins:
        hashed = sha256_text(ADMIN_PASSWORD)
        admins = [{"id": 1, "username": ADMIN_USERNAME, "password": hashed}]
        save_json_file(ADMIN_FILE, admins)


def init_default_obras():
    obras = load_json_file(OBRAS_FILE, [])
    if not obras:
        for ob in DEFAULT_OBRAS:
            if not ob.get("metadados"):
                ob["metadados"] = {"instituicao": "Acervo Demonstrativo", "origem_registro": "seed", "status": "publicado"}
        save_json_file(OBRAS_FILE, DEFAULT_OBRAS)


def init_default_ontologies():
    onts = load_json_file(ONTOLOGIES_FILE, [])
    if not onts:
        base = []
        for item in DEFAULT_ONTOLOGIES:
            cloned = dict(item)
            cloned["criado_em"] = now_str()
            cloned["atualizado_em"] = now_str()
            base.append(cloned)
        save_json_file(ONTOLOGIES_FILE, base)


def init_open_data():
    od = load_json_file(OPEN_DATA_FILE, {})
    if not od:
        update_open_data_snapshot()


def bootstrap():
    ensure_data_dir()
    check_admin()
    init_default_obras()
    init_default_ontologies()
    init_ledger()
    init_open_data()


# ============================================================
# CACHE LOADERS
# ============================================================
@st.cache_data(ttl=5, show_spinner=False)
def load_obras():
    return load_json_file(OBRAS_FILE, DEFAULT_OBRAS)


@st.cache_data(ttl=5, show_spinner=False)
def load_tags():
    return load_json_file(TAGS_FILE, [])


@st.cache_data(ttl=5, show_spinner=False)
def load_users():
    return load_json_file(USERS_FILE, [])


@st.cache_data(ttl=5, show_spinner=False)
def load_ontologies():
    return load_json_file(ONTOLOGIES_FILE, DEFAULT_ONTOLOGIES)


def clear_app_cache():
    st.cache_data.clear()


# ============================================================
# DADOS TABULARES
# ============================================================
def all_tags():
    t = load_tags()
    return pd.DataFrame(t) if t else pd.DataFrame()


def all_users():
    u = load_users()
    return pd.DataFrame(u) if u else pd.DataFrame()


def all_ontologies_df():
    o = load_ontologies()
    return pd.DataFrame(o) if o else pd.DataFrame()


# ============================================================
# ACCESSIBILITY / THEME
# ============================================================
def init_accessibility_state():
    defaults = {
        "font_size": "18px",
        "high_contrast": False,
        "dark_mode": True,
        "focus_audio": True
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def load_css():
    font_size = st.session_state.get("font_size", "18px")
    dark = st.session_state.get("dark_mode", True)
    high_contrast = st.session_state.get("high_contrast", False)

    if dark and high_contrast:
        bg1, bg2, text, card, border, button = "#000000", "#09111f", "#ffffff", "rgba(255,255,255,.08)", "rgba(255,255,255,.45)", "rgba(255,255,255,.18)"
        accent = "#f5f5f5"
    elif dark:
        bg1, bg2, text, card, border, button = "#040404", "#001F3F", "#f3f4f6", "rgba(255,255,255,.12)", "rgba(255,255,255,.24)", "rgba(255,255,255,.18)"
        accent = "#dbeafe"
    elif high_contrast:
        bg1, bg2, text, card, border, button = "#f5f5f5", "#e2e8f0", "#111111", "rgba(255,255,255,.92)", "rgba(0,0,0,.45)", "rgba(255,255,255,.95)"
        accent = "#111111"
    else:
        bg1, bg2, text, card, border, button = "#f7fafc", "#dbeafe", "#111827", "rgba(255,255,255,.82)", "rgba(0,0,0,.12)", "rgba(255,255,255,.95)"
        accent = "#111827"

    st.markdown(
        f"""
        <style>
        * {{
            font-family: "Times New Roman", Times, serif !important;
        }}
        html, body, [class*="css"] {{
            font-size: {font_size};
        }}
        .stApp {{
            background: linear-gradient(135deg, {bg1}, {bg2});
            color: {text};
        }}
        #MainMenu, header, footer {{
            visibility: hidden;
        }}
        .main-content {{
            max-width: 1650px;
            margin: 0 auto;
            padding: 1.2rem 2rem 2rem 2rem;
        }}
        .top-navbar {{
            position: sticky;
            top: 0;
            z-index: 999;
            background: {card};
            backdrop-filter: blur(18px);
            border: 1px solid {border};
            border-radius: 20px;
            padding: 1rem 1.4rem;
            margin-bottom: 1rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .navbar-logo {{
            font-size: 2rem;
            font-weight: 700;
            color: {accent};
            letter-spacing: .2px;
        }}
        .glass-card {{
            background: {card};
            border: 1px solid {border};
            border-radius: 24px;
            padding: 1.6rem;
            box-shadow: 0 12px 34px rgba(0,0,0,.12);
            margin: 1rem 0;
        }}
        .main-title {{
            text-align: center;
            font-size: 3rem;
            font-weight: 700;
            margin: .8rem 0;
            color: {text};
        }}
        .subtitle {{
            text-align: center;
            line-height: 1.6;
            opacity: .92;
            margin-bottom: 1.1rem;
        }}
        .tag-badge {{
            display: inline-block;
            padding: .35rem .8rem;
            border-radius: 999px;
            background: rgba(99,102,241,.18);
            border: 1px solid rgba(99,102,241,.35);
            margin: .2rem;
            font-size: .95rem;
        }}
        .tag-green {{
            background: rgba(34,197,94,.18);
            border-color: rgba(34,197,94,.45);
        }}
        .tag-red {{
            background: rgba(239,68,68,.18);
            border-color: rgba(239,68,68,.45);
        }}
        .tag-yellow {{
            background: rgba(245,158,11,.18);
            border-color: rgba(245,158,11,.45);
        }}
        .tag-blue {{
            background: rgba(59,130,246,.18);
            border-color: rgba(59,130,246,.45);
        }}
        .kpi-card {{
            background: {card};
            border: 1px solid {border};
            border-radius: 20px;
            padding: 1.1rem;
            text-align: center;
            min-height: 140px;
        }}
        .kpi-val {{
            font-size: 2rem;
            font-weight: 700;
            margin-top: .5rem;
        }}
        .kpi-lbl {{
            text-transform: uppercase;
            letter-spacing: 1.5px;
            opacity: .75;
            font-size: .9rem;
        }}
        .kpi-sub {{
            margin-top: .4rem;
            opacity: .72;
            font-size: .85rem;
        }}
        .insight {{
            background: rgba(14,165,233,.10);
            border: 1px solid rgba(14,165,233,.28);
            padding: 1rem 1.2rem;
            border-radius: 16px;
            margin: .6rem 0;
            line-height: 1.7;
        }}
        .divider {{
            height: 1px;
            background: linear-gradient(90deg, transparent, {border}, transparent);
            margin: 1rem 0 1.4rem 0;
        }}
        .obra-card {{
            background: {card};
            border: 1px solid {border};
            border-radius: 18px;
            overflow: hidden;
            margin-bottom: .9rem;
        }}
        .obra-card img {{
            width: 100%;
            height: 290px;
            object-fit: cover;
        }}
        .animal-badge {{
            display:inline-block;
            padding:.25rem .8rem;
            border-radius: 999px;
            background: rgba(14,165,233,.14);
            border:1px solid rgba(14,165,233,.3);
        }}
        .conn-row {{
            display:flex;
            justify-content:space-between;
            align-items:center;
            gap:8px;
            flex-wrap:wrap;
            border:1px solid {border};
            background:{card};
            border-radius:14px;
            padding:.8rem 1rem;
            margin:.35rem 0;
        }}
        .cluster-wrap {{
            border:1px solid {border};
            background:{card};
            border-radius:14px;
            padding:1rem;
            margin:.5rem 0;
        }}
        .cluster-pill {{
            display:inline-block;
            margin:.2rem;
            padding:.3rem .8rem;
            border-radius:999px;
            background:rgba(168,85,247,.18);
            border:1px solid rgba(168,85,247,.35);
        }}
        .small-note {{
            font-size:.9rem;
            opacity:.75;
        }}
        .status-chip {{
            display:inline-block;
            margin:.2rem;
            padding:.28rem .75rem;
            border-radius:999px;
            border:1px solid {border};
            background:{card};
        }}
        .liquid-box {{
            background: {button};
            backdrop-filter: blur(14px);
            border: 1px solid {border};
            border-radius: 18px;
            padding: 1rem;
        }}
        div[data-testid="stTabs"] button {{
            border-radius: 12px !important;
        }}
        .stButton>button, .stDownloadButton>button {{
            border-radius: 999px !important;
            padding: .8rem 1.4rem !important;
            border: 1px solid {border} !important;
            background: {button} !important;
        }}
        .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] > div {{
            border-radius: 14px !important;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )


def kpi(label, value, sub="", color="#0ea5e9"):
    return (
        f"<div class='kpi-card'>"
        f"<div class='kpi-lbl'>{label}</div>"
        f"<div class='kpi-val' style='color:{color}'>{value}</div>"
        f"{f'<div class=\"kpi-sub\">{sub}</div>' if sub else ''}"
        f"</div>"
    )


def divider():
    return "<div class='divider'></div>"


def insight(text):
    return f"<div class='insight'>{text}</div>"


def status_badge(status):
    color_map = {
        "bruto": "tag-yellow",
        "sugerido": "tag-blue",
        "validado": "tag-green",
        "revisado": "tag-blue",
        "publicado": "tag-green"
    }
    cls = color_map.get(status, "tag-blue")
    return f"<span class='tag-badge {cls}'>{status}</span>"


# ============================================================
# SIMILARIDADE / CONEXÕES
# ============================================================
def words(tag):
    return set(normalize_text(tag).split())


def ngrams(text, n=3):
    t = normalize_text(text)
    return set([t]) if len(t) < n else set(t[i:i+n] for i in range(len(t)-n+1))


def sim(t1, t2):
    a, b = normalize_text(t1), normalize_text(t2)
    if a == b:
        return 1.0
    if not a or not b:
        return 0.0
    if a in b or b in a:
        return 0.55 + 0.45 * (min(len(a), len(b)) / max(len(a), len(b)))
    w1, w2 = words(t1), words(t2)
    if w1 and w2:
        j = len(w1 & w2) / len(w1 | w2)
        if j >= 0.5:
            return j
    if len(a) >= 3 and len(b) >= 3:
        ng1, ng2 = ngrams(a), ngrams(b)
        nj = len(ng1 & ng2) / len(ng1 | ng2) if (ng1 | ng2) else 0
        if nj > 0:
            wj = len(w1 & w2) / len(w1 | w2) if (w1 | w2) else 0
            return 0.6 * nj + 0.4 * wj
    return 0.0


def tag_connections(tags_list, threshold=0.35):
    uniq = list(set(normalize_text(t) for t in tags_list if str(t).strip()))
    conns = []
    for i in range(len(uniq)):
        for j in range(i + 1, len(uniq)):
            score = sim(uniq[i], uniq[j])
            if score >= threshold:
                w1, w2 = words(uniq[i]), words(uniq[j])
                shared = w1 & w2
                if uniq[i] in uniq[j] or uniq[j] in uniq[i]:
                    tipo = "Contenção"
                elif shared:
                    tipo = f"Palavra comum: {', '.join(sorted(shared))}"
                else:
                    tipo = "Similaridade fonética"
                conns.append({
                    "tag_a": uniq[i],
                    "tag_b": uniq[j],
                    "similaridade": round(score, 3),
                    "tipo": tipo
                })
    conns.sort(key=lambda x: x["similaridade"], reverse=True)
    return conns


def tag_clusters(tags_list, threshold=0.35):
    uniq = list(set(normalize_text(t) for t in tags_list if str(t).strip()))
    conns = tag_connections(uniq, threshold=threshold)
    parent = {u: u for u in uniq}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for c in conns:
        union(c["tag_a"], c["tag_b"])

    grouped = defaultdict(list)
    for u in uniq:
        grouped[find(u)].append(u)
    return [sorted(v) for v in grouped.values() if len(v) > 1]


# ============================================================
# ORTOGRAFIA / ONTOLOGIAS / SEMÂNTICA
# ============================================================
def levenshtein(a, b):
    a, b = normalize_text(a), normalize_text(b)
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    dp = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        prev = dp[0]
        dp[0] = i
        for j, cb in enumerate(b, 1):
            cur = dp[j]
            if ca == cb:
                dp[j] = prev
            else:
                dp[j] = min(prev + 1, dp[j] + 1, dp[j - 1] + 1)
            prev = cur
    return dp[-1]


def ontology_terms():
    onts = load_ontologies()
    terms = set()
    for ont in onts:
        if ont.get("ativo"):
            for t in ont.get("termos", []):
                if normalize_text(t):
                    terms.add(normalize_text(t))
    return sorted(terms)


def semantic_group_for_tag(tag):
    nt = normalize_text(tag)
    groups = []
    for group_name, vocab in SEMANTIC_GROUPS.items():
        if nt in [normalize_text(v) for v in vocab]:
            groups.append(group_name)
        else:
            for term in vocab:
                if sim(nt, term) >= 0.75:
                    groups.append(group_name)
                    break
    return groups


def ontology_matches(tag):
    nt = normalize_text(tag)
    matches = []
    for ont in load_ontologies():
        if not ont.get("ativo"):
            continue
        termos = [normalize_text(t) for t in ont.get("termos", [])]
        best_score = 0.0
        best_term = None
        for term in termos:
            score = sim(nt, term)
            if score > best_score:
                best_score = score
                best_term = term
        if best_score >= 0.75:
            matches.append({
                "ontologia": ont["nome"],
                "termo": best_term,
                "score": round(best_score, 3),
                "categoria": ont.get("categoria", "")
            })
    matches.sort(key=lambda x: x["score"], reverse=True)
    return matches


def spelling_analysis(tag):
    nt = normalize_text(tag)
    terms = ontology_terms()
    if not nt:
        return {"status": "vazio", "sugestoes": []}
    if nt in terms:
        return {"status": "correto", "sugestoes": []}

    suggestions = []
    for term in terms:
        dist = levenshtein(nt, term)
        ratio = 1 - (dist / max(len(nt), len(term)))
        score = max(0, ratio)
        if score >= 0.60:
            suggestions.append({"termo": term, "score": round(score, 3), "dist": dist})
    suggestions.sort(key=lambda x: (-x["score"], x["dist"], x["termo"]))
    return {
        "status": "suspeito" if suggestions else "desconhecido",
        "sugestoes": suggestions[:5]
    }


def analyze_single_tag(tag):
    spell = spelling_analysis(tag)
    groups = semantic_group_for_tag(tag)
    ont_matches = ontology_matches(tag)

    if spell["status"] == "correto":
        quality = "validado"
    elif ont_matches:
        quality = "sugerido"
    elif spell["status"] == "suspeito":
        quality = "revisado"
    else:
        quality = "bruto"

    return {
        "tag_normalizada": normalize_text(tag),
        "ortografia_status": spell["status"],
        "sugestoes_ortograficas": spell["sugestoes"],
        "grupos_semanticos": groups,
        "ontologias_relacionadas": ont_matches,
        "status_sugerido": quality
    }


# ============================================================
# USER / TAG SAVE
# ============================================================
def save_answers(uid, animal, answers):
    users = load_json_file(USERS_FILE, [])
    already = [u for u in users if u.get("user_id") == uid]
    if already:
        for idx, row in enumerate(users):
            if row.get("user_id") == uid:
                users[idx] = {
                    "user_id": uid,
                    "animal_name": animal,
                    "timestamp": now_str(),
                    **answers
                }
                break
    else:
        users.append({
            "user_id": uid,
            "animal_name": animal,
            "timestamp": now_str(),
            **answers
        })
    ok = save_json_file(USERS_FILE, users)
    if ok:
        append_ledger_event(
            actor_id=uid,
            actor_name=animal,
            actor_role="user",
            event_type="questionnaire_submit",
            entity_type="user_profile",
            entity_id=uid,
            payload=answers,
            status="validado",
            origin="manual",
            automatic=False
        )
        clear_app_cache()
    return ok


def next_tag_id(tags):
    return max([t.get("id", 0) for t in tags], default=0) + 1


def save_tag(uid, animal, obra_id, tag, origem="manual", automatic=False):
    tags = load_json_file(TAGS_FILE, [])
    tag_clean = normalize_text(tag)
    analysis = analyze_single_tag(tag_clean)
    related_ont = analysis.get("ontologias_relacionadas", [])
    related_groups = analysis.get("grupos_semanticos", [])

    record = {
        "id": next_tag_id(tags),
        "user_id": uid,
        "obra_id": obra_id,
        "tag": tag_clean,
        "tag_original": tag,
        "timestamp": now_str(),
        "origem_metadado": origem,
        "automatic": automatic,
        "status_metadado": analysis["status_sugerido"],
        "grupos_semanticos": related_groups,
        "ontologias_relacionadas": related_ont,
        "ortografia_status": analysis["ortografia_status"],
        "sugestoes_ortograficas": analysis["sugestoes_ortograficas"],
        "historico": [{
            "timestamp": now_str(),
            "actor_id": uid,
            "actor_name": animal,
            "acao": "criação",
            "valor": tag_clean,
            "status": analysis["status_sugerido"]
        }]
    }

    tags.append(record)
    ok = save_json_file(TAGS_FILE, tags)
    if ok:
        append_ledger_event(
            actor_id=uid,
            actor_name=animal,
            actor_role="user",
            event_type="tag_create",
            entity_type="tag",
            entity_id=str(record["id"]),
            payload=record,
            status=record["status_metadado"],
            origin=origem,
            automatic=automatic
        )
        clear_app_cache()
    return ok, analysis


def update_tag_status_admin(tag_id, new_status, admin_name="nugep"):
    tags = load_json_file(TAGS_FILE, [])
    changed = None
    for idx, tg in enumerate(tags):
        if tg.get("id") == tag_id:
            old_status = tg.get("status_metadado", "bruto")
            tags[idx]["status_metadado"] = new_status
            tags[idx].setdefault("historico", []).append({
                "timestamp": now_str(),
                "actor_id": "admin",
                "actor_name": admin_name,
                "acao": "status_update",
                "de": old_status,
                "para": new_status
            })
            changed = tags[idx]
            break

    if changed:
        ok = save_json_file(TAGS_FILE, tags)
        if ok:
            append_ledger_event(
                actor_id="admin",
                actor_name=admin_name,
                actor_role="admin",
                event_type="tag_status_update",
                entity_type="tag",
                entity_id=str(tag_id),
                payload={"new_status": new_status, "tag": changed.get("tag")},
                status=new_status,
                origin="manual",
                automatic=False
            )
            clear_app_cache()
            return True
    return False


def correct_tag_text_admin(tag_id, new_text, admin_name="nugep"):
    tags = load_json_file(TAGS_FILE, [])
    changed = None
    for idx, tg in enumerate(tags):
        if tg.get("id") == tag_id:
            old_tag = tg.get("tag", "")
            analysis = analyze_single_tag(new_text)
            tags[idx]["tag"] = normalize_text(new_text)
            tags[idx]["tag_original"] = new_text
            tags[idx]["status_metadado"] = analysis["status_sugerido"]
            tags[idx]["grupos_semanticos"] = analysis["grupos_semanticos"]
            tags[idx]["ontologias_relacionadas"] = analysis["ontologias_relacionadas"]
            tags[idx]["ortografia_status"] = analysis["ortografia_status"]
            tags[idx]["sugestoes_ortograficas"] = analysis["sugestoes_ortograficas"]
            tags[idx].setdefault("historico", []).append({
                "timestamp": now_str(),
                "actor_id": "admin",
                "actor_name": admin_name,
                "acao": "correção_humana",
                "de": old_tag,
                "para": normalize_text(new_text)
            })
            changed = tags[idx]
            break

    if changed:
        ok = save_json_file(TAGS_FILE, tags)
        if ok:
            append_ledger_event(
                actor_id="admin",
                actor_name=admin_name,
                actor_role="admin",
                event_type="tag_corrected",
                entity_type="tag",
                entity_id=str(tag_id),
                payload={"new_text": normalize_text(new_text)},
                status=changed["status_metadado"],
                origin="manual",
                automatic=False
            )
            clear_app_cache()
            return True, changed
    return False, None


# ============================================================
# OBRAS CRUD
# ============================================================
def next_obra_id(obras):
    return max([o.get("id", 0) for o in obras], default=0) + 1


def add_obra(titulo, artista, ano, imagem, audio_descricao, instituicao, actor_name="nugep"):
    obras = load_json_file(OBRAS_FILE, [])
    nid = next_obra_id(obras)
    obra = {
        "id": nid,
        "titulo": titulo,
        "artista": artista,
        "ano": str(ano),
        "imagem": imagem,
        "audio_descricao": audio_descricao,
        "metadados": {
            "instituicao": instituicao,
            "origem_registro": "manual_admin",
            "status": "publicado",
            "criado_em": now_str(),
            "atualizado_em": now_str()
        }
    }
    obras.append(obra)
    ok = save_json_file(OBRAS_FILE, obras)
    if ok:
        append_ledger_event(
            actor_id="admin",
            actor_name=actor_name,
            actor_role="admin",
            event_type="obra_create",
            entity_type="obra",
            entity_id=str(nid),
            payload=obra,
            status="publicado",
            origin="manual",
            automatic=False
        )
        clear_app_cache()
    return ok


def remove_obra(obra_id, actor_name="nugep"):
    obras = load_json_file(OBRAS_FILE, [])
    removed = None
    new_list = []
    for ob in obras:
        if ob.get("id") == obra_id:
            removed = ob
        else:
            new_list.append(ob)

    if removed is None:
        return False

    ok = save_json_file(OBRAS_FILE, new_list)
    if ok:
        append_ledger_event(
            actor_id="admin",
            actor_name=actor_name,
            actor_role="admin",
            event_type="obra_delete",
            entity_type="obra",
            entity_id=str(obra_id),
            payload=removed,
            status="revisado",
            origin="manual",
            automatic=False
        )
        clear_app_cache()
        return True
    return False


# ============================================================
# ONTOLOGIAS CRUD
# ============================================================
def next_ontology_id(onts):
    return max([o.get("id", 0) for o in onts], default=0) + 1


def add_ontology(nome, descricao, categoria, termos, ativo=True, actor_name="nugep"):
    onts = load_json_file(ONTOLOGIES_FILE, [])
    nid = next_ontology_id(onts)
    rec = {
        "id": nid,
        "nome": nome.strip(),
        "descricao": descricao.strip(),
        "categoria": categoria.strip(),
        "termos": sorted(list({normalize_text(t) for t in termos if normalize_text(t)})),
        "ativo": ativo,
        "criado_em": now_str(),
        "atualizado_em": now_str()
    }
    onts.append(rec)
    ok = save_json_file(ONTOLOGIES_FILE, onts)
    if ok:
        append_ledger_event(
            actor_id="admin",
            actor_name=actor_name,
            actor_role="admin",
            event_type="ontology_create",
            entity_type="ontology",
            entity_id=str(nid),
            payload=rec,
            status="validado",
            origin="manual",
            automatic=False
        )
        clear_app_cache()
    return ok


def remove_ontology(ont_id, actor_name="nugep"):
    onts = load_json_file(ONTOLOGIES_FILE, [])
    removed = None
    new_list = []
    for o in onts:
        if o.get("id") == ont_id:
            removed = o
        else:
            new_list.append(o)

    if removed is None:
        return False

    ok = save_json_file(ONTOLOGIES_FILE, new_list)
    if ok:
        append_ledger_event(
            actor_id="admin",
            actor_name=actor_name,
            actor_role="admin",
            event_type="ontology_delete",
            entity_type="ontology",
            entity_id=str(ont_id),
            payload=removed,
            status="revisado",
            origin="manual",
            automatic=False
        )
        clear_app_cache()
        return True
    return False


# ============================================================
# OPEN DATA SNAPSHOT
# ============================================================
def update_open_data_snapshot():
    tdf = all_tags()
    udf = all_users()
    obras = load_json_file(OBRAS_FILE, [])
    onts = load_json_file(ONTOLOGIES_FILE, [])
    ledger = load_json_file(LEDGER_FILE, [])
    circ = load_json_file(CIRCULATION_FILE, [])

    payload = {
        "updated_at": now_str(),
        "resumo": {
            "obras": len(obras),
            "tags": len(tdf) if not tdf.empty else 0,
            "usuarios": len(udf) if not udf.empty else 0,
            "ontologias": len(onts),
            "eventos_ledger": len(ledger),
            "registros_circulacao": len(circ)
        },
        "status_metadado": dict(Counter(tdf["status_metadado"])) if not tdf.empty and "status_metadado" in tdf.columns else {},
        "grupos_semanticos": {},
        "top_tags": {},
        "obras_mais_tagueadas": {}
    }

    if not tdf.empty:
        exploded = []
        if "grupos_semanticos" in tdf.columns:
            for groups in tdf["grupos_semanticos"].tolist():
                for g in groups or []:
                    exploded.append(g)
        payload["grupos_semanticos"] = dict(Counter(exploded))
        payload["top_tags"] = dict(tdf["tag"].value_counts().head(30))
        payload["obras_mais_tagueadas"] = dict(tdf["obra_id"].value_counts().head(30))

    save_json_file(OPEN_DATA_FILE, payload)


# ============================================================
# LOGIN
# ============================================================
def check_login(username, password):
    h = sha256_text(password)
    return username == ADMIN_USERNAME and h == sha256_text(ADMIN_PASSWORD)


# ============================================================
# RELATÓRIOS / HTML EXPORT
# ============================================================
def html_quest(uid, animal, users_df):
    if users_df.empty:
        return None
    ud = users_df[users_df["user_id"] == uid]
    if ud.empty:
        return None
    ui = ud.iloc[0]
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
    <style>
    *{{box-sizing:border-box;font-family:"Times New Roman",serif}}
    body{{background:#f8fafc;color:#111827;padding:40px}}
    .c{{max-width:960px;margin:0 auto;background:#fff;padding:40px;border:1px solid #dbeafe;border-radius:18px}}
    h1{{text-align:center}} .qb{{margin:16px 0;padding:16px;border-left:4px solid #0ea5e9;background:#eff6ff;border-radius:10px}}
    </style></head><body><div class="c"><h1>Respostas do Questionário</h1>
    <p><strong>Usuário:</strong> {html.escape(str(animal))}</p>
    <p><strong>Data:</strong> {html.escape(str(ui.get('timestamp','N/A')))}</p>
    <div class="qb"><strong>1. Familiaridade com museus</strong><br>{html.escape(str(ui.get('q1','N/A')))}</div>
    <div class="qb"><strong>2. Conhecimento sobre documentação museológica</strong><br>{html.escape(str(ui.get('q2','N/A')))}</div>
    <div class="qb"><strong>3. Entendimento sobre tags</strong><br>{html.escape(str(ui.get('q3','N/A')))}</div>
    </div></body></html>"""


def html_tags(uid, animal, obras, tags_df):
    ut = tags_df[tags_df["user_id"] == uid] if not tags_df.empty else pd.DataFrame()
    if ut.empty:
        return None
    od = {o["id"]: o for o in obras}
    rows = ""
    for i, (_, r) in enumerate(ut.iterrows(), start=1):
        obra = od.get(r["obra_id"], {}).get("titulo", f"Obra {r['obra_id']}")
        rows += f"""
        <tr>
            <td>{i}</td>
            <td>{html.escape(str(obra))}</td>
            <td>{html.escape(str(r.get('tag','')))}</td>
            <td>{html.escape(str(r.get('status_metadado','')))}</td>
            <td>{html.escape(str(r.get('timestamp','')))}</td>
        </tr>
        """

    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
    <style>
    *{{box-sizing:border-box;font-family:"Times New Roman",serif}}
    body{{background:#f8fafc;color:#111827;padding:40px}}
    .c{{max-width:1100px;margin:0 auto;background:#fff;padding:40px;border:1px solid #dbeafe;border-radius:18px}}
    table{{width:100%;border-collapse:collapse}}
    th,td{{border-bottom:1px solid #e5e7eb;padding:10px;text-align:left}}
    th{{background:#eff6ff}}
    </style></head><body><div class="c">
    <h1>Relatório de Tags</h1>
    <p><strong>Usuário:</strong> {html.escape(str(animal))}</p>
    <p><strong>Total de tags:</strong> {len(ut)}</p>
    <table>
    <thead><tr><th>#</th><th>Obra</th><th>Tag</th><th>Status</th><th>Data</th></tr></thead>
    <tbody>{rows}</tbody>
    </table>
    </div></body></html>"""


def tags_export_df():
    tdf = all_tags()
    if tdf.empty:
        return pd.DataFrame()
    df = tdf.copy()
    df["ontologias_relacionadas"] = df["ontologias_relacionadas"].apply(lambda x: json.dumps(x, ensure_ascii=False) if isinstance(x, list) else "")
    df["sugestoes_ortograficas"] = df["sugestoes_ortograficas"].apply(lambda x: json.dumps(x, ensure_ascii=False) if isinstance(x, list) else "")
    df["grupos_semanticos"] = df["grupos_semanticos"].apply(lambda x: ", ".join(x) if isinstance(x, list) else "")
    df["historico"] = df["historico"].apply(lambda x: json.dumps(x, ensure_ascii=False) if isinstance(x, list) else "")
    return df


# ============================================================
# AUDIO DESCRIPTION
# ============================================================
def speech_button(text, key):
    safe_text = html.escape(str(text)).replace("\n", " ")
    st.markdown(
        f"""
        <div>
            <button id="speak_{key}" style="
                border-radius:999px;
                padding:.65rem 1rem;
                border:1px solid rgba(255,255,255,.25);
                cursor:pointer;
                font-family:'Times New Roman',serif;">
                Ouvir audiodescrição
            </button>
        </div>
        <script>
        const btn_{key} = window.parent.document.getElementById("speak_{key}");
        if (btn_{key}) {{
            btn_{key}.onclick = function() {{
                const synth = window.speechSynthesis;
                if (synth.speaking) synth.cancel();
                const utter = new SpeechSynthesisUtterance("{safe_text}");
                utter.lang = "pt-BR";
                utter.rate = 0.95;
                synth.speak(utter);
            }};
        }}
        </script>
        """,
        unsafe_allow_html=True
    )


# ============================================================
# HELPERS USER-TAGS
# ============================================================
def get_user_tags(uid):
    tags = load_tags()
    ut = [t for t in tags if t.get("user_id") == uid]
    return pd.DataFrame(ut) if ut else pd.DataFrame()


def get_obra_user_tags(obra_id, uid):
    tags = load_tags()
    filtered = [t for t in tags if t.get("obra_id") == obra_id and t.get("user_id") == uid]
    if not filtered:
        return pd.DataFrame(columns=["tag", "count"])
    df = pd.DataFrame(filtered)
    count = df["tag"].value_counts().reset_index()
    count.columns = ["tag", "count"]
    return count


# ============================================================
# HEADER / ACCESSIBILITY PANEL
# ============================================================
def show_header():
    st.markdown(
        "<div class='top-navbar'>"
        "<div class='navbar-logo'>Sistema Folksonomia Digital</div>"
        "<div class='small-note'>Gestão semântica, auditoria encadeada e acessibilidade</div>"
        "</div>",
        unsafe_allow_html=True
    )


def show_accessibility_controls():
    with st.expander("Acessibilidade e Visual"):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.session_state["font_size"] = st.selectbox(
                "Tamanho da tipografia",
                FONT_OPTIONS,
                index=FONT_OPTIONS.index(st.session_state.get("font_size", "18px")),
                key="font_size_select"
            )
        with c2:
            st.session_state["high_contrast"] = st.toggle(
                "Alto contraste",
                value=st.session_state.get("high_contrast", False)
            )
        with c3:
            st.session_state["dark_mode"] = st.toggle(
                "Modo escuro",
                value=st.session_state.get("dark_mode", True)
            )
        with c4:
            st.session_state["focus_audio"] = st.toggle(
                "Foco em audiodescrição",
                value=st.session_state.get("focus_audio", True)
            )
        if st.button("Aplicar preferências visuais", use_container_width=True):
            st.rerun()


# ============================================================
# INTRO
# ============================================================
def show_intro():
    st.markdown("<div class='main-content'>", unsafe_allow_html=True)
    st.markdown("<h1 class='main-title'>Sistema Folksonomia Digital</h1>", unsafe_allow_html=True)
    st.markdown(
        "<p class='subtitle'>Sistema colaborativo de catalogação, ontologias, validação de tags, trilha auditável e acessibilidade.<br>Preencha o questionário para acessar a plataforma.</p>",
        unsafe_allow_html=True
    )
    show_accessibility_controls()
    load_css()

    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.markdown("<h2 style='text-align:center'>Questionário de Acesso</h2>", unsafe_allow_html=True)

    with st.form("intro_form"):
        c1, c2 = st.columns(2)
        with c1:
            q1 = st.selectbox(
                "1. Qual é o seu nível de familiaridade com museus?",
                ["Nunca visito museus", "Visito raramente", "Visito ocasionalmente", "Visito frequentemente"]
            )
            q2 = st.selectbox(
                "2. Você já ouviu falar sobre documentação museológica?",
                ["Nunca ouvi falar", "Já ouvi, mas não sei o que é", "Tenho uma ideia básica", "Conheço bem o tema"]
            )
        with c2:
            q3 = st.text_area(
                "3. O que você entende por tags ou etiquetas digitais aplicadas a acervo?",
                max_chars=700,
                height=210,
                placeholder="Descreva sua compreensão sobre o conceito..."
            )
        submitted = st.form_submit_button("Acessar Plataforma", use_container_width=True)
        if submitted:
            if not q3.strip():
                st.error("Responda todas as perguntas.")
            else:
                st.session_state["answers"] = {"q1": q1, "q2": q2, "q3": q3}
                save_answers(st.session_state["user_id"], st.session_state["animal_name"], st.session_state["answers"])
                st.session_state["step"] = "completed"
                st.success("Questionário concluído.")
                st.rerun()
    st.markdown("</div></div>", unsafe_allow_html=True)


# ============================================================
# OBRAS / EXPLORE
# ============================================================
def show_obras():
    st.markdown("<h1 class='main-title'>Explorar Obras</h1>", unsafe_allow_html=True)
    st.markdown(
        "<p class='subtitle'>Explore, ouça audiodescrição, ajuste a interface e contribua com tags com rastreabilidade de origem e revisão.</p>",
        unsafe_allow_html=True
    )
    show_accessibility_controls()
    load_css()

    obras = load_obras()
    if not obras:
        st.info("Nenhuma obra cadastrada.")
        return

    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        search = st.text_input("Buscar por título, artista ou número", "")
    with c2:
        order = st.selectbox("Ordenar por", ["Número crescente", "Número decrescente", "Título A-Z"])
    with c3:
        filter_status = st.selectbox("Status institucional", ["Todos", "publicado", "revisado", "validado", "bruto"])
    st.markdown("</div>", unsafe_allow_html=True)

    filtered = obras[:]
    if search.strip():
        ns = normalize_text(search)
        filtered = [
            o for o in filtered
            if ns in normalize_text(o.get("titulo", ""))
            or ns in normalize_text(o.get("artista", ""))
            or ns == str(o.get("id", ""))
        ]

    if filter_status != "Todos":
        filtered = [o for o in filtered if o.get("metadados", {}).get("status", "publicado") == filter_status]

    if order == "Número crescente":
        filtered = sorted(filtered, key=lambda x: x.get("id", 0))
    elif order == "Número decrescente":
        filtered = sorted(filtered, key=lambda x: x.get("id", 0), reverse=True)
    else:
        filtered = sorted(filtered, key=lambda x: normalize_text(x.get("titulo", "")))

    st.markdown(
        f"<div class='glass-card'><strong>{len(filtered)}</strong> obra(s) em exibição.</div>",
        unsafe_allow_html=True
    )

    cols = st.columns(3)
    for i, obra in enumerate(filtered):
        with cols[i % 3]:
            met = obra.get("metadados", {})
            status = met.get("status", "publicado")
            st.markdown(
                f"""
                <div class='obra-card'>
                    <img src='{html.escape(str(obra.get("imagem","")))}' alt='obra'/>
                    <div style='padding:1rem'>
                        <h3>Obra #{obra.get("id")} — {html.escape(str(obra.get("titulo","")))}</h3>
                        <p><strong>Artista:</strong> {html.escape(str(obra.get("artista","")))}</p>
                        <p><strong>Ano:</strong> {html.escape(str(obra.get("ano","")))}</p>
                        <p><strong>Instituição:</strong> {html.escape(str(met.get("instituicao","N/A")))}</p>
                        <p><strong>Status:</strong> {html.escape(str(status))}</p>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

            if st.session_state.get("focus_audio", True):
                st.markdown("**Audiodescrição**")
                st.write(obra.get("audio_descricao", "Sem audiodescrição cadastrada."))
                speech_button(obra.get("audio_descricao", ""), f"obra_{obra.get('id')}")

            if st.button("Adicionar tag", key=f"tag_open_{obra['id']}", use_container_width=True):
                st.session_state["selected_obra"] = obra["id"]

            if st.session_state.get("selected_obra") == obra["id"]:
                st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
                with st.form(f"tag_form_{obra['id']}"):
                    tag = st.text_input("Sua tag")
                    submitted = st.form_submit_button("Salvar tag", use_container_width=True)
                    if submitted:
                        if not tag.strip():
                            st.error("Digite uma tag.")
                        else:
                            ok, analysis = save_tag(
                                st.session_state["user_id"],
                                st.session_state["animal_name"],
                                obra["id"],
                                tag,
                                origem="manual",
                                automatic=False
                            )
                            if ok:
                                st.success("Tag registrada com histórico, análise semântica e trilha de auditoria.")
                                if analysis["sugestoes_ortograficas"]:
                                    st.info("Sugestões ortográficas: " + ", ".join([s["termo"] for s in analysis["sugestoes_ortograficas"][:3]]))
                                if analysis["grupos_semanticos"]:
                                    st.info("Grupos detectados: " + ", ".join(analysis["grupos_semanticos"]))
                                st.session_state["selected_obra"] = None
                                st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

            ut = get_obra_user_tags(obra["id"], st.session_state["user_id"])
            if not ut.empty:
                st.markdown("**Suas tags nesta obra**")
                st.markdown(
                    "".join([f"<span class='tag-badge'>{html.escape(str(r['tag']))} ({r['count']})</span>" for _, r in ut.iterrows()]),
                    unsafe_allow_html=True
                )
            else:
                st.info("Você ainda não adicionou tags nesta obra.")


# ============================================================
# ADMIN ROOT
# ============================================================
def show_admin():
    if "admin_logged_in" not in st.session_state:
        st.session_state["admin_logged_in"] = False

    if not st.session_state["admin_logged_in"]:
        st.markdown("<h1 class='main-title'>Área Administrativa</h1>", unsafe_allow_html=True)
        st.markdown("<p class='subtitle'>Acesso restrito à gestão institucional, ontologias, validação e auditoria.</p>", unsafe_allow_html=True)
        _, c, _ = st.columns([1, 1, 1])
        with c:
            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
            with st.form("admin_login"):
                username = st.text_input("Usuário")
                password = st.text_input("Senha", type="password")
                submitted = st.form_submit_button("Entrar", use_container_width=True)
                if submitted:
                    if check_login(username, password):
                        st.session_state["admin_logged_in"] = True
                        st.session_state["admin_username"] = username
                        append_ledger_event(
                            actor_id="admin",
                            actor_name=username,
                            actor_role="admin",
                            event_type="admin_login",
                            entity_type="session",
                            entity_id=username,
                            payload={"username": username},
                            status="validado",
                            origin="manual",
                            automatic=False
                        )
                        st.success("Login realizado.")
                        st.rerun()
                    else:
                        st.error("Credenciais inválidas.")
            st.markdown("</div>", unsafe_allow_html=True)
        return

    admin_name = st.session_state.get("admin_username", "admin")
    st.markdown(f"<h1 class='main-title'>Dashboard Administrativo</h1>", unsafe_allow_html=True)
    st.markdown(f"<p class='subtitle'>Bem-vindo, <strong>{html.escape(admin_name)}</strong></p>", unsafe_allow_html=True)

    tabs = st.tabs([
        "Visão Geral",
        "Ontologias",
        "Validação de Tags",
        "Conexões e Grafo",
        "Usuários e Familiaridade",
        "Obras",
        "Ledger e Auditoria",
        "Open Data",
        "Exportar"
    ])
    with tabs[0]:
        tab_overview()
    with tabs[1]:
        tab_ontologies(admin_name)
    with tabs[2]:
        tab_tag_validation(admin_name)
    with tabs[3]:
        tab_connections_graph()
    with tabs[4]:
        tab_users_quest()
    with tabs[5]:
        tab_obras(admin_name)
    with tabs[6]:
        tab_ledger_audit()
    with tabs[7]:
        tab_open_data()
    with tabs[8]:
        tab_export(admin_name)

    if st.button("Sair da área administrativa", use_container_width=True):
        append_ledger_event(
            actor_id="admin",
            actor_name=admin_name,
            actor_role="admin",
            event_type="admin_logout",
            entity_type="session",
            entity_id=admin_name,
            payload={"username": admin_name},
            status="validado",
            origin="manual",
            automatic=False
        )
        st.session_state["admin_logged_in"] = False
        st.rerun()


# ============================================================
# TAB OVERVIEW
# ============================================================
def tab_overview():
    tdf = all_tags()
    udf = all_users()
    obs = load_obras()
    onts = load_ontologies()
    ledger = load_json_file(LEDGER_FILE, [])
    ok_integrity, issues = verify_ledger_integrity()

    total = len(tdf) if not tdf.empty else 0
    uniq = tdf["tag"].nunique() if not tdf.empty else 0
    users = len(udf) if not udf.empty else 0
    obras = len(obs)
    ont_count = len(onts)

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        st.markdown(kpi("Tags", total, "registros", "#0ea5e9"), unsafe_allow_html=True)
    with c2:
        st.markdown(kpi("Tags únicas", uniq, "vocabulário", "#8b5cf6"), unsafe_allow_html=True)
    with c3:
        st.markdown(kpi("Usuários", users, "participantes", "#10b981"), unsafe_allow_html=True)
    with c4:
        st.markdown(kpi("Obras", obras, "cadastradas", "#f59e0b"), unsafe_allow_html=True)
    with c5:
        st.markdown(kpi("Ontologias", ont_count, "ativas e cadastradas", "#ef4444"), unsafe_allow_html=True)
    with c6:
        st.markdown(kpi("Ledger", len(ledger), "eventos", "#14b8a6"), unsafe_allow_html=True)

    st.markdown(divider(), unsafe_allow_html=True)
    if ok_integrity:
        st.success("Integridade do ledger verificada. Cadeia hash consistente.")
    else:
        st.error("Foram detectadas inconsistências no ledger.")
        for issue in issues:
            st.write("-", issue)

    if not tdf.empty:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### Status dos metadados")
            if "status_metadado" in tdf.columns:
                st.bar_chart(tdf["status_metadado"].value_counts())
        with c2:
            st.markdown("### Top tags")
            st.bar_chart(tdf["tag"].value_counts().head(15))

        st.markdown(divider(), unsafe_allow_html=True)

        if "grupos_semanticos" in tdf.columns:
            group_counter = Counter()
            for groups in tdf["grupos_semanticos"].tolist():
                for g in groups or []:
                    group_counter[g] += 1
            if group_counter:
                st.markdown("### Grupos semânticos detectados")
                st.dataframe(
                    pd.DataFrame(group_counter.items(), columns=["Grupo", "Quantidade"]).sort_values("Quantidade", ascending=False),
                    use_container_width=True,
                    hide_index=True
                )

    st.markdown(insight(
        "<strong>Arquitetura ativa:</strong> cada alteração gera evento, cada evento recebe hash, cada revisão mantém referência ao estado anterior, "
        "cada metadado registra origem, cada relação automática fica marcada e cada correção humana sobrescreve sem apagar o histórico."
    ), unsafe_allow_html=True)


# ============================================================
# TAB ONTOLOGIES
# ============================================================
def tab_ontologies(admin_name):
    st.markdown("### Ontologias Administrativas")
    onts = load_ontologies()

    t1, t2, t3 = st.tabs(["Listar e analisar", "Criar ontologia", "Cobertura analítica"])

    with t1:
        if not onts:
            st.info("Nenhuma ontologia cadastrada.")
        else:
            for ont in onts:
                st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
                c1, c2 = st.columns([4, 1])
                with c1:
                    st.markdown(f"**#{ont['id']} — {ont['nome']}**")
                    st.write(ont.get("descricao", ""))
                    st.write(f"Categoria: {ont.get('categoria','')}")
                    st.write(f"Ativa: {'Sim' if ont.get('ativo') else 'Não'}")
                    st.write("Termos:", ", ".join(ont.get("termos", [])))
                with c2:
                    if st.button("Remover ontologia", key=f"rm_ont_{ont['id']}", use_container_width=True):
                        if remove_ontology(ont["id"], admin_name):
                            st.success("Ontologia removida.")
                            st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

    with t2:
        with st.form("create_ontology_form"):
            nome = st.text_input("Nome da ontologia")
            descricao = st.text_area("Descrição")
            categoria = st.text_input("Categoria")
            termos_txt = st.text_area("Termos separados por vírgula")
            ativo = st.toggle("Ativa", value=True)
            submitted = st.form_submit_button("Criar ontologia", use_container_width=True)
            if submitted:
                termos = [t.strip() for t in termos_txt.split(",") if t.strip()]
                if not nome.strip() or not termos:
                    st.error("Informe nome e ao menos um termo.")
                else:
                    if add_ontology(nome, descricao, categoria, termos, ativo, admin_name):
                        st.success("Ontologia criada.")
                        st.rerun()

    with t3:
        tdf = all_tags()
        if tdf.empty:
            st.info("Sem tags para analisar cobertura ontológica.")
        else:
            rows = []
            for ont in onts:
                termos = [normalize_text(t) for t in ont.get("termos", [])]
                matched = 0
                for tag in tdf["tag"].tolist():
                    if any(sim(tag, term) >= 0.75 for term in termos):
                        matched += 1
                rows.append({
                    "Ontologia": ont["nome"],
                    "Categoria": ont.get("categoria", ""),
                    "Quantidade de termos": len(termos),
                    "Tags relacionadas": matched,
                    "Cobertura (%)": round((matched / len(tdf)) * 100, 2) if len(tdf) else 0
                })
            cdf = pd.DataFrame(rows).sort_values("Tags relacionadas", ascending=False)
            st.dataframe(cdf, use_container_width=True, hide_index=True)
            if not cdf.empty:
                st.bar_chart(cdf.set_index("Ontologia")["Tags relacionadas"])


# ============================================================
# TAB TAG VALIDATION
# ============================================================
def tab_tag_validation(admin_name):
    st.markdown("### Validação de Tags")
    tdf = all_tags()
    if tdf.empty:
        st.info("Nenhuma tag registrada.")
        return

    # Refresh analyses when needed
    c1, c2, c3 = st.columns(3)
    with c1:
        status_filter = st.selectbox("Filtrar por status do metadado", ["Todos"] + STATUS_METADADO)
    with c2:
        ortho_filter = st.selectbox("Filtrar por ortografia", ["Todos", "correto", "suspeito", "desconhecido"])
    with c3:
        group_filter = st.selectbox("Filtrar por grupo semântico", ["Todos"] + sorted(SEMANTIC_GROUPS.keys()))

    display = tdf.copy()
    if status_filter != "Todos":
        display = display[display["status_metadado"] == status_filter]
    if ortho_filter != "Todos":
        display = display[display["ortografia_status"] == ortho_filter]
    if group_filter != "Todos":
        display = display[display["grupos_semanticos"].apply(lambda x: group_filter in x if isinstance(x, list) else False)]

    st.markdown(divider(), unsafe_allow_html=True)

    if display.empty:
        st.info("Nenhuma tag encontrada com os filtros.")
        return

    for _, row in display.sort_values("timestamp", ascending=False).iterrows():
        obra = next((o for o in load_obras() if o["id"] == row["obra_id"]), None)
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.markdown(f"**Tag #{row['id']} — {row['tag']}**")
        st.write(f"Obra: {obra['titulo'] if obra else row['obra_id']}")
        st.write(f"Usuário: {row.get('user_id')} | Data: {row.get('timestamp')}")
        st.write(f"Origem: {row.get('origem_metadado','manual')} | Automática: {'Sim' if row.get('automatic') else 'Não'}")
        st.markdown(f"Status atual: {status_badge(row.get('status_metadado','bruto'))}", unsafe_allow_html=True)

        cols = st.columns([1.2, 1.2, 1.6])
        with cols[0]:
            st.write("Ortografia:", row.get("ortografia_status", ""))
            suggestions = row.get("sugestoes_ortograficas", [])
            if suggestions:
                st.write("Sugestões:", ", ".join([s["termo"] for s in suggestions[:5]]))
        with cols[1]:
            groups = row.get("grupos_semanticos", [])
            st.write("Grupos:", ", ".join(groups) if groups else "Nenhum")
        with cols[2]:
            onts = row.get("ontologias_relacionadas", [])
            if onts:
                st.write("Ontologias:", ", ".join([f"{o['ontologia']} ({o['termo']})" for o in onts[:4]]))
            else:
                st.write("Ontologias: nenhuma relação forte")

        c1, c2, c3 = st.columns([1, 1.2, 1.5])
        with c1:
            new_status = st.selectbox(
                f"Atualizar status #{row['id']}",
                STATUS_METADADO,
                index=STATUS_METADADO.index(row.get("status_metadado", "bruto")),
                key=f"status_sel_{row['id']}"
            )
            if st.button("Salvar status", key=f"save_status_{row['id']}", use_container_width=True):
                if update_tag_status_admin(int(row["id"]), new_status, admin_name):
                    st.success("Status atualizado.")
                    st.rerun()

        with c2:
            corrected = st.text_input("Correção humana", value=row["tag"], key=f"corr_{row['id']}")
            if st.button("Aplicar correção", key=f"apply_corr_{row['id']}", use_container_width=True):
                ok, _ = correct_tag_text_admin(int(row["id"]), corrected, admin_name)
                if ok:
                    st.success("Correção registrada no histórico.")
                    st.rerun()

        with c3:
            hist = row.get("historico", [])
            if hist:
                st.write("Últimos eventos do histórico")
                for item in hist[-3:]:
                    st.caption(json.dumps(item, ensure_ascii=False))

        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(divider(), unsafe_allow_html=True)

    st.markdown("### Agrupamentos por familiaridade e comportamento")
    udf = all_users()
    if not udf.empty:
        merged = display.merge(udf[["user_id", "q1", "q2"]], on="user_id", how="left")
        if "q1" in merged.columns:
            fam = merged.groupby("q1").agg(
                total_tags=("id", "count"),
                tags_unicas=("tag", "nunique")
            ).reset_index().sort_values("total_tags", ascending=False)
            st.dataframe(fam, use_container_width=True, hide_index=True)
            st.bar_chart(fam.set_index("q1")["total_tags"])


# ============================================================
# TAB CONNECTIONS / GRAPH
# ============================================================
def tab_connections_graph():
    st.markdown("### Conexões de Tags e Grafo Analítico")
    tdf = all_tags()
    obs = load_obras()

    if tdf.empty:
        st.info("Sem tags suficientes.")
        return

    c1, c2, c3 = st.columns(3)
    with c1:
        threshold = st.slider("Limiar de similaridade", 0.20, 0.90, 0.35, 0.05)
    with c2:
        obra_filter = st.selectbox("Obra", ["Todas"] + [f"#{o['id']} — {o['titulo']}" for o in obs])
    with c3:
        max_edges = st.number_input("Máximo de conexões", 10, 300, 80, 10)

    fdf = tdf.copy()
    if obra_filter != "Todas":
        oid = int(obra_filter.split("—")[0].replace("#", "").strip())
        fdf = fdf[fdf["obra_id"] == oid]

    tags = fdf["tag"].tolist()
    conns = tag_connections(tags, threshold=threshold)
    clusters = tag_clusters(tags, threshold=threshold)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(kpi("Conexões", len(conns), f"≥ {threshold:.2f}", "#0ea5e9"), unsafe_allow_html=True)
    with c2:
        st.markdown(kpi("Clusters", len(clusters), "grupos", "#8b5cf6"), unsafe_allow_html=True)
    with c3:
        involved = len(set([c["tag_a"] for c in conns] + [c["tag_b"] for c in conns]))
        st.markdown(kpi("Tags envolvidas", involved, "no grafo", "#10b981"), unsafe_allow_html=True)

    t1, t2, t3 = st.tabs(["Lista de conexões", "Clusters", "Matriz de adjacência"])

    with t1:
        if not conns:
            st.info("Nenhuma conexão encontrada.")
        else:
            freq_map = fdf["tag"].value_counts().to_dict()
            for c in conns[:max_edges]:
                st.markdown(
                    f"<div class='conn-row'>"
                    f"<div><span class='tag-badge'>{c['tag_a']}</span> ↔ <span class='tag-badge'>{c['tag_b']}</span></div>"
                    f"<div><strong>{c['similaridade']}</strong> | {c['tipo']} | freq: {freq_map.get(c['tag_a'],0)} / {freq_map.get(c['tag_b'],0)}</div>"
                    f"</div>",
                    unsafe_allow_html=True
                )

    with t2:
        if not clusters:
            st.info("Nenhum cluster.")
        else:
            for idx, cluster in enumerate(sorted(clusters, key=len, reverse=True), start=1):
                pills = "".join([f"<span class='cluster-pill'>{t}</span>" for t in cluster])
                st.markdown(
                    f"<div class='cluster-wrap'><strong>Grupo {idx}</strong><br>{pills}</div>",
                    unsafe_allow_html=True
                )

    with t3:
        uniq = sorted(set(tags))
        if len(uniq) > 40:
            st.warning("Muitas tags para exibir matriz completa. Reduza os filtros.")
        else:
            mat = pd.DataFrame(0.0, index=uniq, columns=uniq)
            for a in uniq:
                for b in uniq:
                    mat.loc[a, b] = 1.0 if a == b else round(sim(a, b), 2)
            st.dataframe(mat, use_container_width=True)


# ============================================================
# TAB USERS / QUESTIONARIO / FAMILIARIDADE
# ============================================================
def tab_users_quest():
    st.markdown("### Usuários, Questionário e Familiaridade")
    tdf = all_tags()
    udf = all_users()
    if udf.empty:
        st.info("Sem usuários.")
        return

    if tdf.empty:
        st.dataframe(udf, use_container_width=True, hide_index=True)
        return

    uct = tdf.groupby("user_id").size().reset_index(name="Tags")
    uuq = tdf.groupby("user_id")["tag"].nunique().reset_index(name="Tags únicas")
    uob = tdf.groupby("user_id")["obra_id"].nunique().reset_index(name="Obras")
    merged = udf.merge(uct, on="user_id", how="left").merge(uuq, on="user_id", how="left").merge(uob, on="user_id", how="left").fillna(0)
    merged["TTR"] = (merged["Tags únicas"] / merged["Tags"].replace(0, np.nan)).fillna(0).round