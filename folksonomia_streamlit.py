import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import datetime
import hashlib
import base64
import json
import random
import warnings
from collections import defaultdict

import plotly.express as px
import plotly.graph_objects as go
import streamlit.components.v1 as components

warnings.filterwarnings("ignore")

# ═════════════════════════════════════════════════════════════════════
# CONFIG
# ═════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Sistema Folksonomia Digital",
    layout="wide",
    initial_sidebar_state="collapsed",
    page_icon="📚"
)

DATA_DIR   = "data"
OBRAS_FILE = os.path.join(DATA_DIR, "obras.json")
TAGS_FILE  = os.path.join(DATA_DIR, "tags.json")
USERS_FILE = os.path.join(DATA_DIR, "users.json")
ADMIN_FILE = os.path.join(DATA_DIR, "admin.json")

ADMIN_USERNAME = "nugep"
ADMIN_PASSWORD = "nugep123"

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


# ═════════════════════════════════════════════════════════════════════
# ESTADO / ACESSIBILIDADE
# ═════════════════════════════════════════════════════════════════════
def init_accessibility():
    defaults = {
        "theme_mode": "dark",
        "font_scale": 1.00,
        "high_contrast": False,
        "reduce_motion": False,
        "reader_mode": True
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def init_session():
    defaults = {
        "user_id": gen_uid(),
        "animal_name": generate_animal_name(),
        "step": "intro",
        "answers": {},
        "admin_logged_in": False
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


# ═════════════════════════════════════════════════════════════════════
# HELPERS CORE
# ═════════════════════════════════════════════════════════════════════
def generate_animal_name():
    random.seed()
    return f"{random.choice(ANIMAIS)} {random.choice(ADJETIVOS)}"


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


def gen_uid():
    return base64.b64encode(os.urandom(12)).decode("ascii")


def check_admin():
    admins = load_json_file(ADMIN_FILE, [])
    if not admins:
        hashed = hashlib.sha256(ADMIN_PASSWORD.encode()).hexdigest()
        save_json_file(ADMIN_FILE, [{"id": 1, "username": ADMIN_USERNAME, "password": hashed}])


def check_login(username, password):
    h = hashlib.sha256(password.encode()).hexdigest()
    return username == ADMIN_USERNAME and h == hashlib.sha256(ADMIN_PASSWORD.encode()).hexdigest()


# ═════════════════════════════════════════════════════════════════════
# NORMALIZAÇÃO / SIMILARIDADE
# ═════════════════════════════════════════════════════════════════════
def ntag(tag):
    return str(tag).lower().strip()


def words(tag):
    return set(ntag(tag).split())


def ngrams(text, n=3):
    t = ntag(text)
    return set([t]) if len(t) < n else set(t[i:i+n] for i in range(len(t)-n+1))


def sim(t1, t2):
    a, b = ntag(t1), ntag(t2)
    if a == b:
        return 1.0

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
    uniq = list(set(ntag(t) for t in tags_list if str(t).strip()))
    conns = []

    for i in range(len(uniq)):
        for j in range(i + 1, len(uniq)):
            s = sim(uniq[i], uniq[j])
            if s >= threshold:
                w1, w2 = words(uniq[i]), words(uniq[j])
                shared = w1 & w2

                if uniq[i] in uniq[j] or uniq[j] in uniq[i]:
                    tipo = "Contenção"
                elif shared:
                    tipo = f"Palavra comum: '{', '.join(shared)}'"
                else:
                    tipo = "Similaridade fonética"

                conns.append({
                    "tag_a": uniq[i],
                    "tag_b": uniq[j],
                    "similaridade": round(s, 3),
                    "tipo": tipo
                })

    conns.sort(key=lambda x: x["similaridade"], reverse=True)
    return conns


def tag_clusters(tags_list, threshold=0.35):
    uniq = list(set(ntag(t) for t in tags_list if str(t).strip()))
    conns = tag_connections(uniq, threshold)
    par = {t: t for t in uniq}

    def find(x):
        while par[x] != x:
            par[x] = par[par[x]]
            x = par[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            par[ra] = rb

    for c in conns:
        union(c["tag_a"], c["tag_b"])

    cl = defaultdict(list)
    for t in uniq:
        cl[find(t)].append(t)

    return [sorted(v) for v in cl.values() if len(v) > 1]


# ═════════════════════════════════════════════════════════════════════
# DADOS
# ═════════════════════════════════════════════════════════════════════
@st.cache_data(ttl=5, show_spinner=False)
def load_obras():
    default = [
        {
            "id": 1,
            "titulo": "Guernica",
            "artista": "Pablo Picasso",
            "ano": "1937",
            "imagem": "https://upload.wikimedia.org/wikipedia/en/7/74/PicassoGuernica.jpg",
            "descricao": "Pintura em preto, branco e tons de cinza. A cena mostra figuras humanas e animais fragmentados, com forte sensação de dor, conflito e desordem."
        },
        {
            "id": 2,
            "titulo": "A Noite Estrelada",
            "artista": "Vincent van Gogh",
            "ano": "1889",
            "imagem": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ea/Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg/1200px-Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg",
            "descricao": "Paisagem noturna com céu em espirais, estrelas brilhantes e uma vila abaixo. Predominam azuis intensos e amarelos luminosos."
        },
        {
            "id": 3,
            "titulo": "Mona Lisa",
            "artista": "Leonardo da Vinci",
            "ano": "1503",
            "imagem": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ec/Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_retouched.jpg/800px-Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_retouched.jpg",
            "descricao": "Retrato de uma mulher sentada com expressão serena e leve sorriso. Fundo com paisagem distante, tons suaves e composição equilibrada."
        }
    ]

    obras = load_json_file(OBRAS_FILE, default)
    if not obras:
        save_json_file(OBRAS_FILE, default)
        return default

    changed = False
    for o in obras:
        if "descricao" not in o:
            o["descricao"] = f"Obra intitulada {o.get('titulo', 'Sem título')}, de {o.get('artista', 'autor desconhecido')}, ano {o.get('ano', 'não informado')}."
            changed = True

    if changed:
        save_json_file(OBRAS_FILE, obras)

    return obras


def save_answers(uid, animal, answers):
    users = load_json_file(USERS_FILE, [])
    users.append({
        "user_id": uid,
        "animal_name": animal,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        **answers
    })
    return save_json_file(USERS_FILE, users)


def save_tag(uid, obra_id, tag):
    tag = tag.lower().strip()
    if not tag:
        return False

    tags = load_json_file(TAGS_FILE, [])
    tags.append({
        "id": len(tags) + 1,
        "user_id": uid,
        "obra_id": obra_id,
        "tag": tag,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    st.cache_data.clear()
    return save_json_file(TAGS_FILE, tags)


def get_user_tags(uid):
    tags = load_json_file(TAGS_FILE, [])
    ut = [t for t in tags if t["user_id"] == uid]
    return pd.DataFrame(ut) if ut else pd.DataFrame()


def get_obra_user_tags(obra_id, uid):
    tags = load_json_file(TAGS_FILE, [])
    f = [t for t in tags if t["obra_id"] == obra_id and t["user_id"] == uid]
    if f:
        df = pd.DataFrame(f)
        c = df["tag"].value_counts().reset_index()
        c.columns = ["tag", "count"]
        return c
    return pd.DataFrame(columns=["tag", "count"])


def all_tags():
    t = load_json_file(TAGS_FILE, [])
    return pd.DataFrame(t) if t else pd.DataFrame()


def all_users():
    u = load_json_file(USERS_FILE, [])
    return pd.DataFrame(u) if u else pd.DataFrame()


# ═════════════════════════════════════════════════════════════════════
# CSS
# ═════════════════════════════════════════════════════════════════════
def load_css():
    theme = st.session_state.get("theme_mode", "dark")
    font_scale = st.session_state.get("font_scale", 1.0)
    high_contrast = st.session_state.get("high_contrast", False)
    reduce_motion = st.session_state.get("reduce_motion", False)

    if theme == "dark":
        bg1, bg2 = "#050d18", "#0f2746"
        text, subtext = "#f2f7ff", "#d7e5f5"
        card = "rgba(255,255,255,.10)"
        card2 = "rgba(255,255,255,.14)"
        border = "rgba(255,255,255,.22)"
        input_bg = "rgba(255,255,255,.12)"
    else:
        bg1, bg2 = "#eef4fa", "#d9e7f4"
        text, subtext = "#11253a", "#30485f"
        card = "rgba(255,255,255,.75)"
        card2 = "rgba(255,255,255,.90)"
        border = "rgba(17,37,58,.12)"
        input_bg = "rgba(255,255,255,.95)"

    if high_contrast:
        text = "#ffffff" if theme == "dark" else "#000000"
        subtext = "#ffffff" if theme == "dark" else "#111111"
        border = "rgba(255,255,255,.5)" if theme == "dark" else "rgba(0,0,0,.35)"

    motion = "none" if reduce_motion else "bg 15s ease infinite"
    hover_transform = "none" if reduce_motion else "translateY(-6px) scale(1.02)"

    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800&display=swap');

    :root {{
      --bg1:{bg1};
      --bg2:{bg2};
      --text:{text};
      --subtext:{subtext};
      --card:{card};
      --card2:{card2};
      --border:{border};
      --inputbg:{input_bg};
      --accent:#7dd3fc;
      --accent2:#c4b5fd;
      --success:#86efac;
      --warning:#fcd34d;
      --danger:#fca5a5;
      --fontScale:{font_scale};
    }}

    * {{
      margin:0;
      padding:0;
      box-sizing:border-box;
      font-family:'Poppins',sans-serif!important;
    }}

    @keyframes bg {{
      0% {{background-position:0% 50%}}
      50% {{background-position:100% 50%}}
      100% {{background-position:0% 50%}}
    }}

    html, body, [class*="css"] {{
      font-size: calc(16px * var(--fontScale));
    }}

    .stApp {{
      background: linear-gradient(-45deg, var(--bg1) 0%, var(--bg2) 50%, var(--bg1) 100%);
      background-size: 300% 300%;
      animation: {motion};
      color: var(--text);
    }}

    .top-navbar {{
      position:fixed;
      top:0; left:0; right:0;
      z-index:9999;
      background:var(--card);
      backdrop-filter:blur(18px) saturate(180%);
      border-bottom:1px solid var(--border);
      padding:1rem 2rem;
      display:flex;
      justify-content:space-between;
      align-items:center;
      box-shadow:0 8px 30px rgba(0,0,0,.08);
    }}

    .navbar-logo {{
      font-size:1.5rem;
      font-weight:800;
      color:var(--text);
    }}

    .main-content {{
      margin-top:100px;
      padding:1.3rem 2rem;
      max-width:1600px;
      margin-left:auto;
      margin-right:auto;
    }}

    .glass-card, .kpi-card, .cluster-wrap, .sc, .conn-row {{
      background:var(--card);
      backdrop-filter:blur(18px) saturate(180%);
      border:1px solid var(--border);
      color:var(--text);
      box-shadow:0 8px 24px rgba(0,0,0,.08);
    }}

    .glass-card {{
      border-radius:24px;
      padding:1.6rem;
      margin:1rem 0;
    }}

    .obra-card {{
      background:var(--card2);
      border:1px solid var(--border);
      border-radius:20px;
      overflow:hidden;
      transition:all .3s ease;
      box-shadow:0 10px 28px rgba(0,0,0,.10);
    }}

    .obra-card:hover {{
      transform:{hover_transform};
    }}

    .obra-card img {{
      width:100%;
      height:280px;
      object-fit:cover;
    }}

    .main-title {{
      color:var(--text);
      font-size:3rem;
      font-weight:800;
      text-align:center;
      margin:1rem 0 .4rem;
    }}

    .subtitle {{
      color:var(--subtext);
      font-size:1.05rem;
      text-align:center;
      margin-bottom:1.8rem;
      line-height:1.7;
    }}

    .tag-badge {{
      display:inline-block;
      background:rgba(125,211,252,.18);
      border:1px solid rgba(125,211,252,.35);
      color:var(--text);
      padding:.45rem .95rem;
      border-radius:50px;
      margin:.25rem;
      font-size:.84rem;
      font-weight:600;
    }}

    .tag-green {{
      background:rgba(34,197,94,.25)!important;
      border-color:rgba(34,197,94,.50)!important;
    }}

    .tag-amber {{
      background:rgba(245,158,11,.25)!important;
      border-color:rgba(245,158,11,.50)!important;
    }}

    .tag-blue {{
      background:rgba(96,165,250,.25)!important;
      border-color:rgba(96,165,250,.50)!important;
    }}

    .animal-badge {{
      display:inline-block;
      background:rgba(196,181,253,.18);
      border:1px solid rgba(196,181,253,.35);
      color:var(--text);
      padding:.35rem .9rem;
      border-radius:50px;
      font-size:.82rem;
      font-weight:700;
    }}

    .kpi-card {{
      border-radius:18px;
      padding:1.2rem;
      text-align:center;
      min-height:120px;
    }}

    .kpi-val {{
      font-size:2.1rem;
      font-weight:800;
      margin:.45rem 0;
    }}

    .kpi-lbl {{
      font-size:.78rem;
      text-transform:uppercase;
      letter-spacing:1.5px;
      opacity:.88;
    }}

    .kpi-sub {{
      font-size:.76rem;
      opacity:.72;
      margin-top:.25rem;
    }}

    .sc {{
      border-radius:16px;
      padding:1rem 1.2rem;
      margin:.6rem 0;
    }}

    .sc-b {{border-left:4px solid #60a5fa}}
    .sc-g {{border-left:4px solid #34d399}}
    .sc-p {{border-left:4px solid #a78bfa}}
    .sc-a {{border-left:4px solid #fbbf24}}

    .insight {{
      background:rgba(125,211,252,.10);
      border:1px solid rgba(125,211,252,.25);
      border-radius:14px;
      padding:1rem 1.2rem;
      margin:.7rem 0;
      color:var(--text);
      line-height:1.7;
    }}

    .conn-row {{
      display:flex;
      justify-content:space-between;
      align-items:center;
      flex-wrap:wrap;
      gap:8px;
      border-radius:14px;
      padding:.9rem 1.1rem;
      margin:.35rem 0;
    }}

    .cluster-wrap {{
      border-radius:16px;
      padding:1rem 1.2rem;
      margin:.5rem 0;
    }}

    .cluster-title {{
      font-size:.78rem;
      text-transform:uppercase;
      letter-spacing:1.5px;
      color:var(--subtext)!important;
      margin-bottom:.55rem;
      font-weight:700;
    }}

    .cluster-pill {{
      display:inline-flex;
      align-items:center;
      gap:5px;
      background:rgba(168,85,247,.18);
      border:1px solid rgba(168,85,247,.35);
      border-radius:50px;
      padding:.32rem .85rem;
      margin:.2rem;
      font-size:.80rem;
      font-weight:600;
      color:var(--text)!important;
    }}

    .pbar-o {{
      background:rgba(255,255,255,.12);
      border-radius:50px;
      height:6px;
      margin:3px 0;
      overflow:hidden;
    }}

    .pbar-i {{
      height:100%;
      border-radius:50px;
      transition:width .5s;
    }}

    .divider {{
      height:1px;
      background:linear-gradient(90deg,transparent,var(--border),transparent);
      margin:1.3rem 0;
    }}

    .stButton button {{
      background:var(--card2)!important;
      color:var(--text)!important;
      border:1px solid var(--border)!important;
      border-radius:14px!important;
      padding:.85rem 1.3rem!important;
      font-weight:700!important;
    }}

    .stTextInput input, .stTextArea textarea, .stSelectbox select {{
      background:var(--inputbg)!important;
      color:var(--text)!important;
      border:1px solid var(--border)!important;
      border-radius:12px!important;
    }}

    label, h1, h2, h3, h4, h5, h6, p, span, div {{
      color:var(--text)!important;
    }}

    .dataframe {{
      border-radius:12px!important;
      overflow:hidden!important;
    }}

    [data-testid="stSidebar"] {{
      display:none;
    }}

    #MainMenu, footer, header {{
      visibility:hidden;
    }}

    @media (max-width: 768px) {{
      .main-title {{
        font-size:2.2rem;
      }}
      .main-content {{
        padding:1rem;
      }}
    }}
    </style>
    """, unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════
# UI HELPERS
# ═════════════════════════════════════════════════════════════════════
def kpi(label, value, sub="", color="#7dd3fc"):
    return (
        f"<div class='kpi-card'>"
        f"<div class='kpi-lbl'>{label}</div>"
        f"<div class='kpi-val' style='color:{color}'>{value}</div>"
        f"{'<div class=kpi-sub>'+sub+'</div>' if sub else ''}"
        f"</div>"
    )


def insight(text):
    return f"<div class='insight'>{text}</div>"


def divider():
    return "<div class='divider'></div>"


def pbar(pct, color="#60a5fa"):
    w = min(100, max(0, pct * 100))
    return f"<div class='pbar-o'><div class='pbar-i' style='width:{w:.1f}%;background:{color}'></div></div>"


def show_header():
    st.markdown(
        "<div class='top-navbar'>"
        "<div class='navbar-logo'>Sistema Folksonomia Digital</div>"
        "</div>",
        unsafe_allow_html=True
    )


def render_accessibility_bar():
    st.markdown("### Acessibilidade")
    c1, c2, c3, c4, c5 = st.columns(5)

    with c1:
        mode = st.selectbox(
            "Tema",
            ["dark", "light"],
            index=0 if st.session_state["theme_mode"] == "dark" else 1,
            key="theme_selector"
        )
        st.session_state["theme_mode"] = mode

    with c2:
        scale = st.slider(
            "Fonte",
            0.9, 1.4, float(st.session_state["font_scale"]), 0.05,
            key="font_scale_slider"
        )
        st.session_state["font_scale"] = scale

    with c3:
        st.session_state["high_contrast"] = st.checkbox(
            "Alto contraste",
            value=st.session_state["high_contrast"],
            key="high_contrast_check"
        )

    with c4:
        st.session_state["reduce_motion"] = st.checkbox(
            "Reduzir animações",
            value=st.session_state["reduce_motion"],
            key="reduce_motion_check"
        )

    with c5:
        st.session_state["reader_mode"] = st.checkbox(
            "Leitor ativo",
            value=st.session_state["reader_mode"],
            key="reader_mode_check"
        )


def speak_text(text, key="speak"):
    safe = json.dumps(text)
    components.html(f"""
    <div style="display:flex;gap:8px;align-items:center;margin:6px 0 10px 0;flex-wrap:wrap;">
        <button onclick="
            window.speechSynthesis.cancel();
            const u = new SpeechSynthesisUtterance({safe});
            u.lang = 'pt-BR';
            u.rate = 0.95;
            u.pitch = 1.0;
            speechSynthesis.speak(u);
        " style="padding:10px 16px;border-radius:12px;border:none;cursor:pointer;font-weight:700;">
            🔊 Ouvir descrição
        </button>

        <button onclick="window.speechSynthesis.cancel();"
            style="padding:10px 16px;border-radius:12px;border:none;cursor:pointer;font-weight:700;">
            ⏹ Parar
        </button>
    </div>
    """, height=65, key=key)


# ═════════════════════════════════════════════════════════════════════
# EXPORTAÇÃO HTML
# ═════════════════════════════════════════════════════════════════════
def html_quest(uid, animal, users_df):
    if users_df.empty:
        return None

    ud = users_df[users_df["user_id"] == uid]
    if ud.empty:
        return None

    ui = ud.iloc[0]

    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:sans-serif;background:linear-gradient(135deg,#000,#001F3F);padding:40px;color:white}}
.c{{max-width:900px;margin:0 auto;background:rgba(255,255,255,.15);padding:50px;border-radius:24px;border:1px solid rgba(255,255,255,.3)}}
h1{{text-align:center;margin-bottom:15px;font-size:2.2rem}}
.hi{{text-align:center;margin-bottom:35px;opacity:.9}}
.ab{{background:rgba(167,230,255,.25);border:1px solid rgba(167,230,255,.5);color:#a7e6ff;padding:.3rem 1rem;border-radius:50px;font-weight:700;display:inline-block}}
.qb{{margin:22px 0;padding:18px 22px;background:rgba(255,255,255,.1);border-left:4px solid rgba(255,255,255,.5);border-radius:12px}}
.q{{font-weight:700;margin-bottom:8px}}
.a{{line-height:1.7;opacity:.92}}
.ft{{text-align:center;margin-top:40px;padding-top:18px;border-top:1px solid rgba(255,255,255,.2);opacity:.65;font-size:.88rem}}
</style></head>
<body><div class="c"><h1>Respostas do Questionário</h1>
<div class="hi">
  <p>Usuário Anônimo: <span class="ab">🐾 {animal}</span></p>
  <p style="margin-top:6px;opacity:.65">Data: {ui.get('timestamp','N/A')}</p>
</div>
<div class="qb"><div class="q">1. Nível de familiaridade com museus</div><div class="a">{ui.get('q1','N/A')}</div></div>
<div class="qb"><div class="q">2. Conhecimento sobre documentação museológica</div><div class="a">{ui.get('q2','N/A')}</div></div>
<div class="qb"><div class="q">3. O que você entende por 'tags'?</div><div class="a">{ui.get('q3','N/A')}</div></div>
<div class="ft">Sistema Folksonomia Digital — Ctrl+P → Salvar como PDF</div>
</div></body></html>"""


def html_tags(uid, animal, obras, tags_df):
    ut = tags_df[tags_df["user_id"] == uid] if not tags_df.empty else pd.DataFrame()
    if ut.empty:
        return None

    od = {o["id"]: o for o in obras}

    rows = "".join(
        f"<tr><td>{i+1}</td>"
        f"<td>{od.get(r['obra_id'], {}).get('titulo', 'Obra '+str(r['obra_id']))}</td>"
        f"<td><span style='background:rgba(255,255,255,.22);padding:3px 10px;border-radius:50px'>{r['tag']}</span></td>"
        f"<td>{r['timestamp']}</td></tr>"
        for i, (_, r) in enumerate(ut.iterrows())
    )

    top = "".join(
        f"<tr><td>{i}</td><td>{t}</td><td>{c}</td></tr>"
        for i, (t, c) in enumerate(ut["tag"].value_counts().head(10).items(), 1)
    )

    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:sans-serif;background:linear-gradient(135deg,#000,#001F3F);padding:40px;color:white}}
.c{{max-width:1100px;margin:0 auto;background:rgba(255,255,255,.15);padding:50px;border-radius:24px;border:1px solid rgba(255,255,255,.3)}}
h1{{text-align:center;margin-bottom:15px;font-size:2.2rem}}
.hi{{text-align:center;margin-bottom:28px;opacity:.9}}
.ab{{background:rgba(167,230,255,.25);border:1px solid rgba(167,230,255,.5);color:#a7e6ff;padding:.3rem 1rem;border-radius:50px;font-weight:700;display:inline-block}}
.stats{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin:22px 0}}
.sb{{background:rgba(255,255,255,.14);border:1px solid rgba(255,255,255,.28);padding:18px;border-radius:12px;text-align:center}}
.sv{{font-size:2.6rem;font-weight:800}}
.sl{{font-size:.82rem;text-transform:uppercase;letter-spacing:1.5px;margin-top:7px;opacity:.85}}
table{{width:100%;border-collapse:collapse;margin:18px 0}}
th,td{{padding:13px;text-align:left;border-bottom:1px solid rgba(255,255,255,.14)}}
th{{background:rgba(255,255,255,.18);font-weight:700;text-transform:uppercase;font-size:.82rem}}
tr:nth-child(even){{background:rgba(255,255,255,.04)}}
.ft{{text-align:center;margin-top:38px;padding-top:18px;border-top:1px solid rgba(255,255,255,.2);opacity:.65;font-size:.88rem}}
</style></head>
<body><div class="c"><h1>Relatório de Tags</h1>
<div class="hi">
  <p>Usuário Anônimo: <span class="ab">🐾 {animal}</span></p>
  <p style="margin-top:6px;opacity:.65">Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
</div>
<div class="stats">
  <div class="sb"><div class="sv">{len(ut)}</div><div class="sl">Total de Tags</div></div>
  <div class="sb"><div class="sv">{ut['tag'].nunique()}</div><div class="sl">Tags Únicas</div></div>
  <div class="sb"><div class="sv">{ut['obra_id'].nunique()}</div><div class="sl">Obras Etiquetadas</div></div>
</div>
<h2 style="margin:28px 0 14px;font-size:1.5rem">Todas as Tags</h2>
<table><thead><tr><th>#</th><th>Obra</th><th>Tag</th><th>Data/Hora</th></tr></thead>
<tbody>{rows}</tbody></table>
<h2 style="margin:28px 0 14px;font-size:1.5rem">Top 10 Tags</h2>
<table><thead><tr><th>Pos.</th><th>Tag</th><th>Freq.</th></tr></thead>
<tbody>{top}</tbody></table>
<div class="ft">Sistema Folksonomia Digital — Ctrl+P → Salvar como PDF</div>
</div></body></html>"""


# ═════════════════════════════════════════════════════════════════════
# GRÁFICOS
# ═════════════════════════════════════════════════════════════════════
def pie_chart_from_series(series, title="Distribuição"):
    if series.empty:
        st.info("Sem dados para exibir.")
        return

    chart_df = series.reset_index()
    chart_df.columns = ["Categoria", "Valor"]

    fig = px.pie(
        chart_df,
        names="Categoria",
        values="Valor",
        hole=0.35,
        title=title
    )
    fig.update_traces(textposition="inside", textinfo="percent+label")
    fig.update_layout(margin=dict(l=20, r=20, t=60, b=20))
    st.plotly_chart(fig, use_container_width=True)


def bar_chart_from_series(series, title=""):
    if series.empty:
        st.info("Sem dados para exibir.")
        return
    fig = px.bar(
        x=series.index.astype(str),
        y=series.values,
        labels={"x": "", "y": "Quantidade"},
        title=title
    )
    fig.update_layout(margin=dict(l=20, r=20, t=60, b=20))
    st.plotly_chart(fig, use_container_width=True)


def line_chart_from_df(df, xcol, ycol, title=""):
    if df.empty:
        st.info("Sem dados para exibir.")
        return
    fig = px.line(df, x=xcol, y=ycol, title=title, markers=True)
    fig.update_layout(margin=dict(l=20, r=20, t=60, b=20))
    st.plotly_chart(fig, use_container_width=True)


# ═════════════════════════════════════════════════════════════════════
# TELA INTRO
# ═════════════════════════════════════════════════════════════════════
def show_intro():
    st.markdown("<div class='main-content'>", unsafe_allow_html=True)
    st.markdown("<h1 class='main-title'>Sistema Folksonomia Digital</h1>", unsafe_allow_html=True)
    st.markdown(
        "<p class='subtitle'>Sistema colaborativo de catalogação de obras de arte<br>"
        "Complete o questionário para acessar a plataforma</p>",
        unsafe_allow_html=True
    )

    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    render_accessibility_bar()

    st.markdown(
        "<h2 style='text-align:center;margin-bottom:2rem;font-size:1.7rem'>Questionário de Acesso</h2>",
        unsafe_allow_html=True
    )

    with st.form("intro_form"):
        c1, c2 = st.columns(2)

        with c1:
            q1 = st.selectbox(
                "1. Qual é o seu nível de familiaridade com museus?",
                [
                    "Nunca visito museus",
                    "Visito raramente",
                    "Visito ocasionalmente",
                    "Visito frequentemente"
                ]
            )
            q2 = st.selectbox(
                "2. Você já ouviu falar sobre documentação museológica?",
                [
                    "Nunca ouvi falar",
                    "Já ouvi, mas não sei o que é",
                    "Tenho uma ideia básica",
                    "Conheço bem o tema"
                ]
            )

        with c2:
            q3 = st.text_area(
                "3. O que você entende por 'tags' ou etiquetas digitais aplicadas a acervo?",
                max_chars=500,
                height=200,
                placeholder="Descreva sua compreensão sobre o conceito..."
            )

        _, cb, _ = st.columns([1, 1, 1])
        with cb:
            submit = st.form_submit_button("Acessar Plataforma", use_container_width=True)

        if submit:
            if not q3.strip():
                st.error("Por favor, responda todas as perguntas para continuar.")
            else:
                st.session_state["answers"] = {"q1": q1, "q2": q2, "q3": q3}
                save_answers(
                    st.session_state["user_id"],
                    st.session_state["animal_name"],
                    st.session_state["answers"]
                )
                st.session_state["step"] = "completed"
                st.success("Questionário completo! Acesso liberado.")
                st.balloons()
                st.rerun()

    st.markdown("</div></div>", unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════
# GALERIA DE OBRAS
# ═════════════════════════════════════════════════════════════════════
def show_obras():
    st.markdown("<h1 class='main-title'>Galeria de Obras de Arte</h1>", unsafe_allow_html=True)
    st.markdown(
        "<p class='subtitle'>Explore as obras, ouça a descrição acessível e contribua com tags descritivas</p>",
        unsafe_allow_html=True
    )

    render_accessibility_bar()
    obras = load_obras()

    if not obras:
        st.info("Nenhuma obra cadastrada.")
        return

    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    c1, c2 = st.columns([2, 1])

    with c1:
        sid = st.text_input("Filtrar por número da obra:", "", placeholder="Ex: 1, 2, 3…")

    with c2:
        sord = st.selectbox("Ordenar por:", ["Número (crescente)", "Número (decrescente)"])

    st.markdown("</div>", unsafe_allow_html=True)

    filtered = obras
    if sid.strip().isdigit():
        filtered = [o for o in obras if str(o["id"]) == sid.strip()]

    filtered = sorted(filtered, key=lambda x: x["id"], reverse=(sord == "Número (decrescente)"))

    st.markdown(
        f"<div style='text-align:center;margin:1rem 0;font-weight:600'>Exibindo {len(filtered)} obra(s)</div>",
        unsafe_allow_html=True
    )

    cols = st.columns(3)

    for i, obra in enumerate(filtered):
        with cols[i % 3]:
            st.markdown(
                f"""
                <div class='obra-card'>
                    <img src='{obra["imagem"]}' alt='Imagem da obra {obra["titulo"]}' />
                    <div style='padding:1.1rem'>
                        <h3 style='margin-bottom:.25rem'>Obra #{obra["id"]} — {obra["titulo"]}</h3>
                        <p style='opacity:.85;font-size:.92rem'>{obra["artista"]} — {obra["ano"]}</p>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

            with st.expander("Acessibilidade e descrição"):
                st.write(f"**Descrição acessível:** {obra.get('descricao', 'Sem descrição cadastrada.')}")
                if st.session_state.get("reader_mode", True):
                    speak_text(
                        f"Obra {obra['titulo']}, de {obra['artista']}, ano {obra['ano']}. {obra.get('descricao', '')}",
                        key=f"voice_{obra['id']}"
                    )

            if st.button("Adicionar Tag", key=f"btn_{obra['id']}", use_container_width=True):
                st.session_state["selected_obra"] = obra
                st.rerun()

            if (
                "selected_obra" in st.session_state
                and st.session_state["selected_obra"]["id"] == obra["id"]
            ):
                with st.form(f"tf_{obra['id']}"):
                    tag = st.text_input(
                        "Sua tag:",
                        key=f"t_{obra['id']}",
                        placeholder="Ex: azul, noite, sofrimento, retrato…"
                    )
                    ca, cb = st.columns(2)
                    with ca:
                        sub = st.form_submit_button("Enviar", use_container_width=True)
                    with cb:
                        can = st.form_submit_button("Cancelar", use_container_width=True)

                    if sub and tag:
                        save_tag(st.session_state["user_id"], obra["id"], tag)
                        st.success(f"Tag '{tag}' adicionada!")
                        del st.session_state["selected_obra"]
                        st.rerun()

                    if can:
                        del st.session_state["selected_obra"]
                        st.rerun()

            ut = get_obra_user_tags(obra["id"], st.session_state["user_id"])
            if not ut.empty:
                st.markdown("**Suas tags nesta obra:**")
                st.markdown(
                    "".join(
                        f"<span class='tag-badge'>{r['tag']} ({r['count']})</span>"
                        for _, r in ut.iterrows()
                    ),
                    unsafe_allow_html=True
                )
            else:
                st.info("Você ainda não criou tags para esta obra.")


# ═════════════════════════════════════════════════════════════════════
# ADMIN
# ═════════════════════════════════════════════════════════════════════
def show_admin():
    if not st.session_state["admin_logged_in"]:
        st.markdown("<h1 class='main-title'>Área Administrativa</h1>", unsafe_allow_html=True)
        st.markdown("<p class='subtitle'>Acesso restrito</p>", unsafe_allow_html=True)

        _, c2, _ = st.columns([1, 1, 1])
        with c2:
            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
            st.markdown(
                "<h2 style='text-align:center;margin-bottom:1.8rem'>Login Administrativo</h2>",
                unsafe_allow_html=True
            )

            with st.form("login"):
                username = st.text_input("Usuário:", placeholder="Digite seu usuário")
                password = st.text_input("Senha:", type="password", placeholder="Digite sua senha")
                sub = st.form_submit_button("Entrar no Sistema", use_container_width=True)

                if sub:
                    if check_login(username, password):
                        st.session_state["admin_logged_in"] = True
                        st.session_state["admin_username"] = username
                        st.success("Login realizado com sucesso!")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("Credenciais inválidas. Acesso negado.")

            st.markdown("</div>", unsafe_allow_html=True)

    else:
        st.markdown(
            f"<h1 class='main-title'>Dashboard Administrativo</h1>"
            f"<p class='subtitle'>Bem-vindo, <strong>{st.session_state.get('admin_username','Admin')}</strong></p>",
            unsafe_allow_html=True
        )

        tabs = st.tabs([
            "Visão Geral",
            "Análise de Tags",
            "Conexões de Tags",
            "Usuários & Questionário",
            "Obras",
            "Exportar"
        ])

        with tabs[0]:
            tab_overview()
        with tabs[1]:
            tab_tags()
        with tabs[2]:
            tab_connections()
        with tabs[3]:
            tab_users_quest()
        with tabs[4]:
            tab_obras()
        with tabs[5]:
            tab_export()

        _, c2, _ = st.columns([1, 1, 1])
        with c2:
            if st.button("Sair do Sistema", use_container_width=True):
                st.session_state["admin_logged_in"] = False
                st.rerun()


# ═════════════════════════════════════════════════════════════════════
# ABA 1 — VISÃO GERAL
# ═════════════════════════════════════════════════════════════════════
def tab_overview():
    tdf = all_tags()
    udf = all_users()
    obs = load_obras()

    st.markdown("### Métricas Gerais do Sistema")

    total = len(tdf) if not tdf.empty else 0
    unicas = tdf["tag"].nunique() if not tdf.empty else 0
    nusers = udf["user_id"].nunique() if not udf.empty else 0
    nobs = len(obs)
    obs_ct = tdf["obra_id"].nunique() if not tdf.empty else 0

    c1, c2, c3, c4, c5 = st.columns(5)
    for col, lbl, val, sub, clr in [
        (c1, "Total de Tags", total, "registros", "#7dd3fc"),
        (c2, "Tags Únicas", unicas, f"{unicas/total:.0%} do total" if total else "—", "#c4b5fd"),
        (c3, "Participantes", nusers, "usuários ativos", "#86efac"),
        (c4, "Obras Cadastradas", nobs, f"{obs_ct} com tags", "#fcd34d"),
        (c5, "Média Tags/Usuário", f"{total/nusers:.1f}" if nusers else "—", "por participante", "#f9a8d4"),
    ]:
        with col:
            st.markdown(kpi(lbl, val, sub, clr), unsafe_allow_html=True)

    st.markdown(divider(), unsafe_allow_html=True)

    if not udf.empty and not tdf.empty:
        st.markdown("### Participantes Anônimos")

        uct = tdf.groupby("user_id").size().reset_index(name="tags")
        uuq = tdf.groupby("user_id")["tag"].nunique().reset_index(name="unicas")
        m = udf.merge(uct, on="user_id", how="left").merge(uuq, on="user_id", how="left").fillna(0)

        for _, row in m.iterrows():
            animal = row.get("animal_name", "?")
            ts = row.get("timestamp", "N/A")
            nt, nu = int(row["tags"]), int(row["unicas"])
            p = nu / nt if nt > 0 else 0

            st.markdown(
                f"<div class='sc sc-b' style='padding:.85rem 1.3rem;margin:.25rem 0'>"
                f"<div style='display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px'>"
                f"<div><span class='animal-badge'>🐾 {animal}</span>"
                f"<span style='opacity:.65;font-size:.75rem;margin-left:10px'>Acesso: {ts}</span></div>"
                f"<div style='text-align:right;min-width:170px'>"
                f"<span style='font-weight:700'>{nt} tags</span>"
                f"<span style='opacity:.65;font-size:.78rem'> ({nu} únicas)</span>"
                f"{pbar(p, '#7dd3fc')}"
                f"<span style='opacity:.65;font-size:.7rem'>riqueza: {p:.0%}</span>"
                f"</div></div></div>",
                unsafe_allow_html=True
            )

    st.markdown(divider(), unsafe_allow_html=True)

    if not tdf.empty:
        od = {o["id"]: o["titulo"] for o in obs}

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### Top 15 Tags Mais Usadas")
            top = tdf["tag"].value_counts().head(15).reset_index()
            top.columns = ["Tag", "Qtd"]
            top["%"] = (top["Qtd"] / top["Qtd"].sum() * 100).round(1)
            st.dataframe(top, use_container_width=True, hide_index=True)

        with c2:
            st.markdown("#### Obras Mais Tagueadas")
            ot = tdf.groupby("obra_id").size().reset_index(name="Tags")
            ot["Obra"] = ot["obra_id"].map(od)
            st.dataframe(
                ot[["Obra", "Tags"]].sort_values("Tags", ascending=False),
                use_container_width=True,
                hide_index=True
            )

        st.markdown(divider(), unsafe_allow_html=True)

        c3, c4 = st.columns(2)
        with c3:
            pie_chart_from_series(tdf["obra_id"].map(lambda x: f"Obra {x}").value_counts(), "Distribuição de Tags por Obra")
        with c4:
            pie_chart_from_series(tdf["tag"].value_counts().head(10), "Top 10 Tags Mais Frequentes")


# ═════════════════════════════════════════════════════════════════════
# ABA 2 — ANÁLISE DE TAGS
# ═════════════════════════════════════════════════════════════════════
def tab_tags():
    tdf = all_tags()
    if tdf.empty:
        st.info("Nenhuma tag disponível.")
        return

    st.markdown("### Análise Avançada de Tags")

    tf = tdf.copy()
    tf["timestamp"] = pd.to_datetime(tf["timestamp"], errors="coerce")

    total_tags = len(tf)
    tags_unicas = tf["tag"].nunique()
    media_por_tag = total_tags / tags_unicas if tags_unicas else 0

    t1, t2, t3 = st.tabs([
        "Visão Geral",
        "Distribuições",
        "Evolução Temporal"
    ])

    with t1:
        freq = tf["tag"].value_counts().reset_index()
        freq.columns = ["Tag", "Frequência"]
        hapax = (freq["Frequência"] == 1).sum()
        ttr = tags_unicas / total_tags if total_tags else 0

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(kpi("Total de Tags", total_tags, "registros", "#7dd3fc"), unsafe_allow_html=True)
        with c2:
            st.markdown(kpi("Tags Únicas", tags_unicas, "vocabulário", "#c4b5fd"), unsafe_allow_html=True)
        with c3:
            st.markdown(kpi("Hapax", hapax, "1 ocorrência", "#86efac"), unsafe_allow_html=True)
        with c4:
            st.markdown(kpi("TTR", f"{ttr:.2%}", "riqueza vocabular", "#fcd34d"), unsafe_allow_html=True)

        st.markdown(divider(), unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            bar_chart_from_series(tf["tag"].value_counts().head(20), "Top 20 tags")

        with c2:
            freq["%"] = (freq["Frequência"] / freq["Frequência"].sum() * 100).round(2)
            freq["% Acumulada"] = freq["%"].cumsum().round(2)
            line_chart_from_df(freq.head(20), "Tag", "% Acumulada", "Frequência acumulada")

        st.markdown(
            insight(
                f"<strong>Leitura analítica:</strong> o sistema possui <strong>{tags_unicas}</strong> tags únicas em "
                f"<strong>{total_tags}</strong> registros. O índice TTR de <strong>{ttr:.2%}</strong> sugere "
                f"{'alta' if ttr > 0.50 else 'média' if ttr > 0.25 else 'baixa'} diversidade lexical."
            ),
            unsafe_allow_html=True
        )

        st.markdown("#### Tabela completa de frequências")
        st.dataframe(freq, use_container_width=True, hide_index=True)

    with t2:
        st.markdown("#### Distribuições das tags")

        freq = tf["tag"].value_counts().reset_index()
        freq.columns = ["Tag", "Frequência"]

        freq["Categoria"] = pd.cut(
            freq["Frequência"],
            bins=[0, 1, 2, 5, 10, 999999],
            labels=["1 uso", "2 usos", "3–5 usos", "6–10 usos", "11+ usos"]
        )

        c1, c2 = st.columns(2)
        with c1:
            pie_chart_from_series(freq["Categoria"].value_counts(), "Categorias de frequência das tags")
        with c2:
            pie_chart_from_series(tf["obra_id"].map(lambda x: f"Obra {x}").value_counts(), "Distribuição de tags por obra")

        st.markdown(divider(), unsafe_allow_html=True)

        c3, c4 = st.columns(2)
        with c3:
            if "user_id" in tf.columns:
                pie_chart_from_series(tf["user_id"].value_counts().head(10), "Participação por usuário")

        with c4:
            top10 = tf["tag"].value_counts().head(10)
            pie_chart_from_series(top10, "Top 10 tags mais usadas")

        st.markdown("#### Resumo tabular")
        resumo = pd.DataFrame({
            "Métrica": [
                "Total de registros",
                "Tags únicas",
                "Média de usos por tag",
                "Hapax",
                "Obras com tags"
            ],
            "Valor": [
                total_tags,
                tags_unicas,
                round(media_por_tag, 2),
                (freq["Frequência"] == 1).sum(),
                tf["obra_id"].nunique()
            ]
        })
        st.dataframe(resumo, use_container_width=True, hide_index=True)

    with t3:
        if tf["timestamp"].isna().all():
            st.info("Sem datas válidas para análise temporal.")
            return

        tf["date"] = tf["timestamp"].dt.date
        tf["hora"] = tf["timestamp"].dt.hour
        tf["mes"] = tf["timestamp"].dt.to_period("M").astype(str)

        c1, c2 = st.columns(2)
        with c1:
            daily = tf.groupby("date").size().reset_index(name="Tags")
            line_chart_from_df(daily, "date", "Tags", "Tags por dia")

        with c2:
            monthly = tf.groupby("mes").size().reset_index(name="Tags")
            fig = px.bar(monthly, x="mes", y="Tags", title="Tags por mês")
            fig.update_layout(margin=dict(l=20, r=20, t=60, b=20))
            st.plotly_chart(fig, use_container_width=True)

        st.markdown(divider(), unsafe_allow_html=True)

        c3, c4 = st.columns(2)
        with c3:
            hourly = tf.groupby("hora").size()
            bar_chart_from_series(hourly, "Distribuição por hora")

        with c4:
            pie_chart_from_series(tf["mes"].value_counts().sort_index(), "Participação percentual por mês")

        st.markdown("#### Tabela temporal detalhada")
        temp_table = tf.groupby("date").agg(
            Tags=("tag", "count"),
            Tags_Unicas=("tag", "nunique"),
            Usuarios=("user_id", "nunique")
        ).reset_index()

        st.dataframe(temp_table, use_container_width=True, hide_index=True)


# ═════════════════════════════════════════════════════════════════════
# ABA 3 — CONEXÕES
# ═════════════════════════════════════════════════════════════════════
def tab_connections():
    tdf = all_tags()
    obs = load_obras()

    if tdf.empty:
        st.warning("Nenhuma tag disponível.")
        return

    st.markdown("### Conexões e Agrupamentos de Tags")
    st.markdown(
        insight(
            "<strong>Como funciona:</strong> O algoritmo combina três métricas — "
            "<strong>Contenção de substring</strong>, "
            "<strong>Jaccard de palavras</strong> e "
            "<strong>Jaccard de trigramas</strong>. "
            "O score vai de 0 a 1."
        ),
        unsafe_allow_html=True
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        threshold = st.slider("Limiar de similaridade:", 0.20, 0.90, 0.35, 0.05, key="ct")
    with c2:
        obra_f = st.selectbox("Filtrar por obra:", ["Todas"] + [f"#{o['id']} — {o['titulo']}" for o in obs], key="co")
    with c3:
        max_c = st.number_input("Máx. conexões:", 10, 300, 60, 10, key="cm")

    fdf = tdf.copy()
    if obra_f != "Todas":
        oid = int(obra_f.split("—")[0].replace("#", "").strip())
        fdf = tdf[tdf["obra_id"] == oid]

    all_t = fdf["tag"].tolist()
    if len(set(all_t)) < 2:
        st.warning("Necessário ao menos 2 tags distintas.")
        return

    with st.spinner("Calculando conexões…"):
        conns = tag_connections(all_t, threshold=threshold)
        clusters = tag_clusters(all_t, threshold=threshold)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(kpi("Total de Conexões", len(conns), f"limiar ≥ {threshold:.2f}", "#7dd3fc"), unsafe_allow_html=True)
    with c2:
        st.markdown(kpi("Grupos Formados", len(clusters), "clusters de tags", "#c4b5fd"), unsafe_allow_html=True)
    with c3:
        involved = len(set(c["tag_a"] for c in conns) | set(c["tag_b"] for c in conns)) if conns else 0
        st.markdown(kpi("Tags Envolvidas", involved, "tags conectadas", "#86efac"), unsafe_allow_html=True)

    st.markdown(divider(), unsafe_allow_html=True)

    t1, t2 = st.tabs(["Lista de Conexões", "Grupos de Tags"])

    with t1:
        if not conns:
            st.info("Nenhuma conexão encontrada. Reduza o limiar de similaridade.")
        else:
            tipos = sorted(set(c["tipo"] for c in conns))
            tipo_sel = st.multiselect("Filtrar por tipo:", tipos, default=tipos, key="tsel")
            cf = [c for c in conns if c["tipo"] in tipo_sel][:max_c]
            freq_map = tdf["tag"].value_counts().to_dict()

            st.markdown(f"Exibindo **{len(cf)}** de **{len(conns)}** conexões")
            st.markdown(divider(), unsafe_allow_html=True)

            for c in cf:
                s = c["similaridade"]
                bar = "█" * int(s * 10) + "░" * (10 - int(s * 10))
                fa = freq_map.get(c["tag_a"], 0)
                fb = freq_map.get(c["tag_b"], 0)

                st.markdown(
                    f"<div class='conn-row'>"
                    f"<div style='display:flex;align-items:center;gap:10px;flex-wrap:wrap'>"
                    f"<span class='tag-badge'>{c['tag_a']}</span>"
                    f"<span style='opacity:.65;font-size:.72rem'>({fa}×)</span>"
                    f"<span style='opacity:.65'>↔</span>"
                    f"<span class='tag-badge'>{c['tag_b']}</span>"
                    f"<span style='opacity:.65;font-size:.72rem'>({fb}×)</span>"
                    f"</div>"
                    f"<div style='text-align:right;min-width:195px'>"
                    f"<span style='font-family:monospace;font-size:.78rem'>{bar} {s:.3f}</span><br>"
                    f"<span style='font-size:.72rem;opacity:.72'>{c['tipo']}</span>"
                    f"</div></div>",
                    unsafe_allow_html=True
                )

            st.markdown(divider(), unsafe_allow_html=True)
            st.download_button(
                "Baixar conexões (CSV)",
                pd.DataFrame(conns).to_csv(index=False).encode("utf-8"),
                f"conexoes_{datetime.now().strftime('%Y%m%d')}.csv",
                "text/csv"
            )

    with t2:
        if not clusters:
            st.info("Nenhum grupo formado. Reduza o limiar de similaridade.")
        else:
            COLORS = ["#60a5fa", "#34d399", "#f9a8d4", "#fcd34d", "#a78bfa", "#f87171"]
            freq_map = tdf["tag"].value_counts().to_dict()
            cls_sorted = sorted(clusters, key=len, reverse=True)

            st.markdown(f"**{len(cls_sorted)} grupo(s) de tags relacionadas**")
            st.markdown(divider(), unsafe_allow_html=True)

            for i, cl in enumerate(cls_sorted, 1):
                color = COLORS[(i - 1) % len(COLORS)]
                total_uses = sum(freq_map.get(t, 0) for t in cl)
                pills = "".join(
                    f"<span class='cluster-pill'>{t} "
                    f"<span style='opacity:.6;font-size:.7rem'>({freq_map.get(t,0)}×)</span></span>"
                    for t in sorted(cl, key=lambda x: freq_map.get(x, 0), reverse=True)
                )

                st.markdown(
                    f"<div class='cluster-wrap' style='border-left:3px solid {color}'>"
                    f"<div class='cluster-title'>Grupo {i} · {len(cl)} tags · {total_uses} usos totais</div>"
                    f"{pills}</div>",
                    unsafe_allow_html=True
                )

            st.markdown(divider(), unsafe_allow_html=True)
            st.markdown("#### Resumo dos Grupos")

            summ = pd.DataFrame([{
                "Grupo": f"Grupo {i}",
                "Qtd Tags": len(cl),
                "Total Usos": sum(freq_map.get(t, 0) for t in cl),
                "Tags": ", ".join(sorted(cl, key=lambda x: freq_map.get(x, 0), reverse=True)[:6]) + ("…" if len(cl) > 6 else "")
            } for i, cl in enumerate(cls_sorted, 1)])

            st.dataframe(summ, use_container_width=True, hide_index=True)

            st.download_button(
                "Baixar grupos (CSV)",
                summ.to_csv(index=False).encode("utf-8"),
                f"clusters_{datetime.now().strftime('%Y%m%d')}.csv",
                "text/csv"
            )


# ═════════════════════════════════════════════════════════════════════
# ABA 4 — USUÁRIOS & QUESTIONÁRIO
# ═════════════════════════════════════════════════════════════════════
def tab_users_quest():
    tdf = all_tags()
    udf = all_users()
    obs = load_obras()
    od = {o["id"]: o["titulo"] for o in obs}

    if udf.empty:
        st.info("Nenhum dado de usuário disponível.")
        return

    st.markdown("### Usuários & Questionário")

    uct = tdf.groupby("user_id").size().reset_index(name="Total_Tags") if not tdf.empty else pd.DataFrame(columns=["user_id", "Total_Tags"])
    uuq = tdf.groupby("user_id")["tag"].nunique().reset_index(name="Tags_Unicas") if not tdf.empty else pd.DataFrame(columns=["user_id", "Tags_Unicas"])
    uob = tdf.groupby("user_id")["obra_id"].nunique().reset_index(name="Obras") if not tdf.empty else pd.DataFrame(columns=["user_id", "Obras"])

    merged = udf.merge(uct, on="user_id", how="left").merge(uuq, on="user_id", how="left").merge(uob, on="user_id", how="left").fillna(0)
    merged["TTR"] = (merged["Tags_Unicas"] / merged["Total_Tags"].replace(0, np.nan)).fillna(0).round(3)
    merged["Usuário"] = merged.apply(lambda r: r.get("animal_name", r["user_id"][:8]), axis=1)

    c1, c2, c3, c4 = st.columns(4)
    top_u = merged.loc[merged["Total_Tags"].idxmax(), "Usuário"] if not merged.empty else "—"

    with c1:
        st.markdown(kpi("Participantes", len(merged), "usuários", "#7dd3fc"), unsafe_allow_html=True)
    with c2:
        st.markdown(kpi("Média Tags/Usuário", f"{merged['Total_Tags'].mean():.1f}", "", "#86efac"), unsafe_allow_html=True)
    with c3:
        st.markdown(kpi("Maior Contribuição", int(merged["Total_Tags"].max()) if not merged.empty else 0, top_u[:16], "#fcd34d"), unsafe_allow_html=True)
    with c4:
        st.markdown(kpi("Riqueza Média (TTR)", f"{merged['TTR'].mean():.2%}", "vocabular", "#c4b5fd"), unsafe_allow_html=True)

    st.markdown(divider(), unsafe_allow_html=True)

    t1, t2, t3, t4 = st.tabs([
        "Tabela de Participantes",
        "Perfil Individual",
        "Respostas do Questionário",
        "Cruzamentos"
    ])

    with t1:
        st.markdown("#### Comparativo Geral de Participantes")
        dcols = ["Usuário", "Total_Tags", "Tags_Unicas", "TTR", "Obras", "q1", "q2"]
        avail = [c for c in dcols if c in merged.columns]

        disp = merged[avail].rename(columns={
            "Total_Tags": "Tags Criadas",
            "Tags_Unicas": "Tags Únicas",
            "Obras": "Obras Etiquetadas",
            "q1": "Familiaridade c/ Museus",
            "q2": "Conhec. Museológico"
        }).sort_values("Tags Criadas", ascending=False)

        st.dataframe(disp, use_container_width=True, hide_index=True)

        st.markdown(divider(), unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            bar_chart_from_series(merged.set_index("Usuário")["Total_Tags"].sort_values(ascending=False), "Contribuição por Participante")
        with c2:
            bar_chart_from_series(merged.set_index("Usuário")["TTR"].sort_values(ascending=False), "Riqueza Vocabular (TTR) por Usuário")

    with t2:
        st.markdown("#### Perfil Detalhado por Participante")
        uopts = [f"🐾 {r.get('animal_name', r['user_id'][:8])}" for _, r in udf.iterrows()]
        usel = st.selectbox("Selecione um participante:", uopts, key="ui_sel")
        uidx = uopts.index(usel)
        uid = udf.iloc[uidx]["user_id"]
        uanim = udf.iloc[uidx].get("animal_name", uid[:8])

        utags = tdf[tdf["user_id"] == uid] if not tdf.empty else pd.DataFrame()
        if utags.empty:
            st.info("Este participante ainda não criou tags.")
        else:
            ttl = len(utags)
            unq = utags["tag"].nunique()
            ttr_u = unq / ttl if ttl else 0

            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown(kpi("Tags Criadas", ttl, "", "#7dd3fc"), unsafe_allow_html=True)
            with c2:
                st.markdown(kpi("Tags Únicas", unq, f"TTR: {ttr_u:.2%}", "#86efac"), unsafe_allow_html=True)
            with c3:
                st.markdown(kpi("Obras Tagueadas", utags["obra_id"].nunique(), "", "#fcd34d"), unsafe_allow_html=True)

            c1, c2 = st.columns(2)
            with c1:
                bar_chart_from_series(utags["tag"].value_counts().head(15), f"Top tags de {uanim}")
            with c2:
                obra_counts = utags.groupby("obra_id").size()
                obra_counts.index = [od.get(i, f"Obra {i}") for i in obra_counts.index]
                bar_chart_from_series(obra_counts, "Distribuição por obra")

            st.markdown("**Conexões nas tags deste participante (limiar 0.30):**")
            uconns = tag_connections(utags["tag"].tolist(), threshold=0.30)
            if uconns:
                freq_map = utags["tag"].value_counts().to_dict()
                for c in uconns[:10]:
                    fa = freq_map.get(c["tag_a"], 0)
                    fb = freq_map.get(c["tag_b"], 0)
                    st.markdown(
                        f"<div class='conn-row'>"
                        f"<div style='display:flex;align-items:center;gap:9px;flex-wrap:wrap'>"
                        f"<span class='tag-badge'>{c['tag_a']}</span>"
                        f"<span style='opacity:.65;font-size:.7rem'>({fa}×)</span>"
                        f"<span style='opacity:.65'>↔</span>"
                        f"<span class='tag-badge'>{c['tag_b']}</span>"
                        f"<span style='opacity:.65;font-size:.7rem'>({fb}×)</span>"
                        f"</div>"
                        f"<span style='opacity:.72;font-size:.75rem'>{c['similaridade']:.3f} · {c['tipo']}</span>"
                        f"</div>",
                        unsafe_allow_html=True
                    )
            else:
                st.info("Nenhuma conexão encontrada nas tags deste participante.")

            st.markdown(divider(), unsafe_allow_html=True)
            st.markdown("**Todas as tags criadas:**")
            ft = utags.copy()
            ft["Obra"] = ft["obra_id"].map(od)
            st.dataframe(
                ft[["tag", "Obra", "timestamp"]].rename(columns={"tag": "Tag", "timestamp": "Data/Hora"}),
                use_container_width=True,
                hide_index=True
            )

    with t3:
        st.markdown("#### Respostas do Questionário de Perfil")

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Q1 — Familiaridade com Museus**")
            q1c = udf["q1"].value_counts()
            pie_chart_from_series(q1c, "Familiaridade com Museus")

        with c2:
            st.markdown("**Q2 — Conhecimento sobre Documentação Museológica**")
            q2c = udf["q2"].value_counts()
            pie_chart_from_series(q2c, "Conhecimento Museológico")

        st.markdown(divider(), unsafe_allow_html=True)
        st.markdown("**Q3 — Respostas Abertas**")

        disp = udf.copy()
        if "animal_name" in disp.columns:
            disp = disp.rename(columns={"animal_name": "Usuário Anônimo"})
        disp["Palavras"] = disp["q3"].astype(str).str.split().str.len()

        st.markdown(f"Comprimento médio das respostas: **{disp['Palavras'].mean():.0f} palavras** por participante")
        bar_chart_from_series(disp["Palavras"].value_counts().sort_index(), "Distribuição do tamanho das respostas")

        st.dataframe(
            disp[["Usuário Anônimo", "q3", "Palavras", "timestamp"]]
            .sort_values("timestamp", ascending=False)
            .rename(columns={"q3": "Resposta", "timestamp": "Data/Hora"}),
            use_container_width=True,
            hide_index=True
        )

    with t4:
        if tdf.empty:
            st.info("Dados de tags insuficientes para cruzamentos.")
            return

        st.markdown("#### Cruzamentos: Perfil × Comportamento de Tagging")

        m = merged.copy()
        m["TTR"] = (m["Tags_Unicas"] / m["Total_Tags"].replace(0, np.nan)).fillna(0)

        st.markdown("**Familiaridade com Museus × Média de Tags Criadas**")
        avg_q1 = m.groupby("q1")["Total_Tags"].mean().sort_values(ascending=False)
        bar_chart_from_series(avg_q1, "Familiaridade × Média de Tags")

        st.markdown(divider(), unsafe_allow_html=True)

        st.markdown("**Conhecimento Museológico × Tags Únicas**")
        avg_q2 = m.groupby("q2")["Tags_Unicas"].mean().sort_values(ascending=False)
        bar_chart_from_series(avg_q2, "Conhecimento × Tags Únicas")

        st.markdown(divider(), unsafe_allow_html=True)

        cross = m.groupby("q1").agg(
            Usuários=("user_id", "count"),
            Média_Tags=("Total_Tags", "mean"),
            Média_Únicas=("Tags_Unicas", "mean"),
            Riqueza_TTR=("TTR", "mean"),
        ).round(2).reset_index()

        cross.columns = ["Familiaridade", "Usuários", "Média Tags", "Média Únicas", "Riqueza (TTR)"]
        st.dataframe(cross, use_container_width=True, hide_index=True)

        st.markdown(
            insight(
                "<strong>Interpretação:</strong> compare se participantes mais familiarizados com museus "
                "produzem mais tags, maior diversidade vocabular e maior riqueza lexical."
            ),
            unsafe_allow_html=True
        )


# ═════════════════════════════════════════════════════════════════════
# ABA 5 — OBRAS
# ═════════════════════════════════════════════════════════════════════
def tab_obras():
    st.markdown("### Gestão de Obras")
    obras = load_obras()

    t1, t2 = st.tabs(["Listar Obras", "Adicionar Nova"])

    with t1:
        if obras:
            for obra in obras:
                c1, c2, c3 = st.columns([1, 2, 1])

                with c1:
                    st.image(obra["imagem"], use_container_width=True)

                with c2:
                    st.markdown(f"**#{obra['id']} – {obra['titulo']}**")
                    st.markdown(f"*{obra['artista']} — {obra['ano']}*")
                    st.markdown(f"**Descrição acessível:** {obra.get('descricao','Sem descrição.')}")

                with c3:
                    if st.button("🗑️ Remover", key=f"del_{obra['id']}"):
                        obras.remove(obra)
                        save_json_file(OBRAS_FILE, obras)
                        st.success("Obra removida!")
                        st.cache_data.clear()
                        st.rerun()

                st.divider()
        else:
            st.info("Nenhuma obra cadastrada.")

    with t2:
        with st.form("add_obra"):
            titulo = st.text_input("Título da Obra")
            artista = st.text_input("Artista")
            ano = st.text_input("Ano")
            imagem = st.text_input("URL da Imagem")
            descricao = st.text_area(
                "Descrição acessível da imagem",
                placeholder="Descreva visualmente a obra para narração acessível."
            )

            if st.form_submit_button("Adicionar Obra"):
                if titulo and artista and ano and imagem:
                    nid = max([o["id"] for o in obras]) + 1 if obras else 1
                    obras.append({
                        "id": nid,
                        "titulo": titulo,
                        "artista": artista,
                        "ano": ano,
                        "imagem": imagem,
                        "descricao": descricao.strip() if descricao.strip() else f"Obra intitulada {titulo}, de {artista}, do ano {ano}."
                    })
                    save_json_file(OBRAS_FILE, obras)
                    st.success("Obra adicionada!")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("Preencha todos os campos obrigatórios.")


# ═════════════════════════════════════════════════════════════════════
# ABA 6 — EXPORTAR
# ═════════════════════════════════════════════════════════════════════
def tab_export():
    st.markdown("### Central de Exportação")
    tdf = all_tags()
    udf = all_users()
    obs = load_obras()

    t1, t2 = st.tabs(["Exportação Geral", "Por Participante"])

    with t1:
        c1, c2, c3 = st.columns(3)

        with c1:
            st.markdown("#### Tags")
            if not tdf.empty:
                st.download_button(
                    "Todas as Tags (CSV)",
                    tdf.to_csv(index=False).encode("utf-8"),
                    f"tags_{datetime.now().strftime('%Y%m%d')}.csv",
                    "text/csv",
                    use_container_width=True
                )

                freq = tdf["tag"].value_counts().reset_index()
                freq.columns = ["Tag", "Frequência"]
                freq["%"] = (freq["Frequência"] / freq["Frequência"].sum() * 100).round(2)

                st.download_button(
                    "Frequências (CSV)",
                    freq.to_csv(index=False).encode("utf-8"),
                    f"freq_{datetime.now().strftime('%Y%m%d')}.csv",
                    "text/csv",
                    use_container_width=True
                )

        with c2:
            st.markdown("#### Usuários")
            if not udf.empty:
                st.download_button(
                    "Usuários (CSV)",
                    udf.to_csv(index=False).encode("utf-8"),
                    f"usuarios_{datetime.now().strftime('%Y%m%d')}.csv",
                    "text/csv",
                    use_container_width=True
                )

        with c3:
            st.markdown("#### Obras")
            if obs:
                st.download_button(
                    "Obras (CSV)",
                    pd.DataFrame(obs).to_csv(index=False).encode("utf-8"),
                    f"obras_{datetime.now().strftime('%Y%m%d')}.csv",
                    "text/csv",
                    use_container_width=True
                )

        st.markdown(divider(), unsafe_allow_html=True)
        st.markdown("#### Exportar Conexões de Tags")

        if not tdf.empty:
            thr = st.slider("Limiar de similaridade:", 0.2, 0.9, 0.35, 0.05, key="exp_thr")
            if st.button("Gerar arquivo de conexões"):
                with st.spinner("Calculando…"):
                    conns = tag_connections(tdf["tag"].tolist(), threshold=thr)

                if conns:
                    cdf = pd.DataFrame(conns)
                    st.download_button(
                        "Conexões (CSV)",
                        cdf.to_csv(index=False).encode("utf-8"),
                        f"conexoes_{datetime.now().strftime('%Y%m%d')}.csv",
                        "text/csv",
                        use_container_width=True
                    )
                    st.success(f"{len(conns)} conexões exportadas.")
                else:
                    st.info("Nenhuma conexão encontrada com este limiar.")

    with t2:
        if udf.empty:
            st.info("Nenhum participante cadastrado.")
            return

        uopts = [f"🐾 {r.get('animal_name', r['user_id'][:8])}" for _, r in udf.iterrows()]
        usel = st.selectbox("Selecione um participante:", uopts, key="exp_u")
        uidx = uopts.index(usel)
        uid = udf.iloc[uidx]["user_id"]
        uanim = udf.iloc[uidx].get("animal_name", uid[:8])

        st.markdown(f"#### Dados de: **{uanim}**")

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("##### Questionário")
            hq = html_quest(uid, uanim, udf)
            if hq:
                st.download_button(
                    "Respostas (HTML/PDF)",
                    hq,
                    f"quest_{uid[:8]}.html",
                    "text/html",
                    use_container_width=True
                )

            ud = udf[udf["user_id"] == uid]
            if not ud.empty:
                st.download_button(
                    "Respostas (CSV)",
                    ud.to_csv(index=False).encode("utf-8"),
                    f"quest_{uid[:8]}.csv",
                    "text/csv",
                    use_container_width=True
                )

        with c2:
            st.markdown("##### Tags Criadas")
            ht = html_tags(uid, uanim, obs, tdf)
            if ht:
                st.download_button(
                    "Tags (HTML/PDF)",
                    ht,
                    f"tags_{uid[:8]}.html",
                    "text/html",
                    use_container_width=True
                )

            ut = get_user_tags(uid)
            if not ut.empty:
                st.download_button(
                    "Tags (CSV)",
                    ut.to_csv(index=False).encode("utf-8"),
                    f"tags_{uid[:8]}.csv",
                    "text/csv",
                    use_container_width=True
                )


# ═════════════════════════════════════════════════════════════════════
# MAIN
# ═════════════════════════════════════════════════════════════════════
def main():
    init_accessibility()
    init_session()
    load_css()

    try:
        check_admin()
    except Exception as e:
        st.error(f"Erro ao inicializar: {e}")

    if st.session_state["step"] != "completed":
        show_intro()
    else:
        show_header()
        st.markdown("<div class='main-content'>", unsafe_allow_html=True)

        t1, t2 = st.tabs(["Explorar Obras", "Área Administrativa"])
        with t1:
            show_obras()
        with t2:
            show_admin()

        st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
