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
import io
from collections import defaultdict
import plotly.express as px
from gtts import gTTS

warnings.filterwarnings("ignore")

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


# ═════════════════════════════════════════════════════════════════════
# UTILITÁRIOS
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


# ═════════════════════════════════════════════════════════════════════
# ACESSIBILIDADE
# ═════════════════════════════════════════════════════════════════════
def init_accessibility():
    if "theme_mode" not in st.session_state:
        st.session_state["theme_mode"] = "Escuro"
    if "font_scale" not in st.session_state:
        st.session_state["font_scale"] = 1.0
    if "alto_contraste" not in st.session_state:
        st.session_state["alto_contraste"] = False
    if "audio_auto" not in st.session_state:
        st.session_state["audio_auto"] = True


def accessibility_panel():
    st.markdown("### Acessibilidade e visual")
    c1, c2 = st.columns(2)

    with c1:
        theme = st.radio(
            "Tema",
            ["Escuro", "Claro"],
            index=0 if st.session_state["theme_mode"] == "Escuro" else 1,
            horizontal=True
        )
        st.session_state["theme_mode"] = theme

        font = st.slider(
            "Tamanho da fonte",
            min_value=0.90,
            max_value=1.40,
            value=float(st.session_state["font_scale"]),
            step=0.05
        )
        st.session_state["font_scale"] = font

    with c2:
        st.session_state["alto_contraste"] = st.toggle(
            "Alto contraste",
            value=st.session_state["alto_contraste"]
        )
        st.session_state["audio_auto"] = st.toggle(
            "Ativar audiodescrição/narração",
            value=st.session_state["audio_auto"]
        )


def gerar_audio_descricao(texto, lang="pt-br"):
    try:
        if not texto or not str(texto).strip():
            return None
        fp = io.BytesIO()
        tts = gTTS(text=str(texto), lang=lang)
        tts.write_to_fp(fp)
        fp.seek(0)
        return fp
    except Exception as e:
        st.warning(f"Não foi possível gerar áudio: {e}")
        return None


def montar_descricao_obra(obra, user_tags_df=None):
    base = f"Obra número {obra['id']}. Título: {obra['titulo']}. Artista: {obra['artista']}. Ano: {obra['ano']}."

    desc = obra.get("descricao_acessivel", "").strip()
    if desc:
        base += f" Descrição acessível da imagem: {desc}"

    if user_tags_df is not None and not user_tags_df.empty:
        top_tags = user_tags_df.sort_values("count", ascending=False)["tag"].astype(str).tolist()[:5]
        if top_tags:
            base += " Principais tags registradas pelo participante: " + ", ".join(top_tags) + "."

    return base


# ═════════════════════════════════════════════════════════════════════
# SIMILARIDADE DE TAGS
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
                    tipo = f"Palavra comum: {', '.join(sorted(shared))}"
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
# CSS
# ═════════════════════════════════════════════════════════════════════
def load_css():
    init_accessibility()

    dark = st.session_state["theme_mode"] == "Escuro"
    contrast = st.session_state["alto_contraste"]
    scale = st.session_state["font_scale"]

    if dark:
        bg1 = "#06121f"
        bg2 = "#102944"
        txt = "#f8fafc"
        subtxt = "#dbe7f5"
        card = "rgba(255,255,255,.10)"
        border = "rgba(255,255,255,.18)"
        badge_bg = "rgba(96,165,250,.18)"
        badge_bd = "rgba(96,165,250,.36)"
    else:
        bg1 = "#edf4fb"
        bg2 = "#dcecff"
        txt = "#0f172a"
        subtxt = "#334155"
        card = "rgba(255,255,255,.78)"
        border = "rgba(15,23,42,.12)"
        badge_bg = "rgba(59,130,246,.12)"
        badge_bd = "rgba(59,130,246,.25)"

    if contrast:
        txt = "#ffffff" if dark else "#000000"
        subtxt = "#ffffff" if dark else "#111111"
        border = "rgba(255,255,255,.65)" if dark else "rgba(0,0,0,.4)"

    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800&display=swap');

    :root {{
        --bg1: {bg1};
        --bg2: {bg2};
        --txt: {txt};
        --subtxt: {subtxt};
        --card: {card};
        --border: {border};
        --badge_bg: {badge_bg};
        --badge_bd: {badge_bd};
        --scale: {scale};
    }}

    * {{
        font-family: 'Poppins', sans-serif !important;
        box-sizing: border-box;
    }}

    html, body, [class*="css"] {{
        font-size: calc(16px * var(--scale));
    }}

    .stApp {{
        background: linear-gradient(135deg, var(--bg1), var(--bg2));
        color: var(--txt);
    }}

    .top-navbar {{
        position: fixed;
        top: 0; left: 0; right: 0;
        z-index: 9999;
        background: var(--card);
        backdrop-filter: blur(18px);
        border-bottom: 1px solid var(--border);
        padding: 1.1rem 2rem;
        box-shadow: 0 8px 30px rgba(0,0,0,.08);
    }}

    .navbar-logo {{
        font-size: 1.65rem;
        font-weight: 800;
        letter-spacing: -0.5px;
        color: var(--txt);
    }}

    .main-content {{
        margin-top: 95px;
        padding: 1.4rem 2rem 3rem 2rem;
        max-width: 1500px;
        margin-left: auto;
        margin-right: auto;
    }}

    .main-title {{
        font-size: 3rem;
        font-weight: 800;
        text-align: center;
        margin: 1rem 0 .8rem 0;
        color: var(--txt);
    }}

    .subtitle {{
        text-align: center;
        color: var(--subtxt) !important;
        font-size: 1.08rem;
        margin-bottom: 2rem;
        line-height: 1.7;
    }}

    .glass-card {{
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 22px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 12px 30px rgba(0,0,0,.10);
        backdrop-filter: blur(14px);
    }}

    .obra-card {{
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 18px;
        overflow: hidden;
        box-shadow: 0 10px 25px rgba(0,0,0,.10);
    }}

    .obra-card img {{
        width: 100%;
        height: 280px;
        object-fit: cover;
        display: block;
    }}

    .tag-badge {{
        display: inline-block;
        background: var(--badge_bg);
        border: 1px solid var(--badge_bd);
        padding: .40rem .80rem;
        border-radius: 999px;
        margin: .15rem;
        font-size: .86rem;
        font-weight: 600;
        color: var(--txt);
    }}

    .animal-badge {{
        display: inline-block;
        padding: .35rem .9rem;
        border-radius: 999px;
        border: 1px solid var(--border);
        background: var(--card);
        font-weight: 700;
        color: var(--txt);
    }}

    .kpi-card {{
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 18px;
        padding: 1.2rem;
        text-align: center;
        box-shadow: 0 10px 25px rgba(0,0,0,.08);
    }}

    .kpi-lbl {{
        font-size: .82rem;
        text-transform: uppercase;
        letter-spacing: 1px;
        opacity: .85;
        color: var(--subtxt);
        font-weight: 700;
    }}

    .kpi-val {{
        font-size: 2.15rem;
        font-weight: 800;
        margin: .45rem 0;
        color: var(--txt);
    }}

    .kpi-sub {{
        font-size: .78rem;
        color: var(--subtxt);
    }}

    .divider {{
        height: 1px;
        background: linear-gradient(90deg, transparent, var(--border), transparent);
        margin: 1.3rem 0;
    }}

    .insight {{
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 14px;
        padding: 1rem 1.2rem;
        line-height: 1.7;
        color: var(--txt);
    }}

    .conn-row {{
        display: flex;
        justify-content: space-between;
        gap: 12px;
        flex-wrap: wrap;
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: .9rem 1rem;
        margin: .45rem 0;
    }}

    .cluster-wrap {{
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 14px;
        padding: 1rem 1.1rem;
        margin: .5rem 0;
    }}

    .cluster-title {{
        font-size: .82rem;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-weight: 700;
        margin-bottom: .6rem;
        color: var(--subtxt);
    }}

    .cluster-pill {{
        display: inline-flex;
        gap: 5px;
        align-items: center;
        padding: .30rem .8rem;
        border-radius: 999px;
        margin: .15rem;
        background: var(--badge_bg);
        border: 1px solid var(--badge_bd);
        font-size: .82rem;
        font-weight: 600;
        color: var(--txt);
    }}

    h1,h2,h3,h4,h5,h6,p,span,div,label {{
        color: var(--txt);
    }}

    .stButton button {{
        border-radius: 999px !important;
        font-weight: 700 !important;
        padding: .8rem 1.3rem !important;
    }}

    #MainMenu, footer, header {{
        visibility: hidden;
    }}

    .stDeployButton {{
        display: none;
    }}

    [data-testid="stSidebar"] {{
        display: none;
    }}
    </style>
    """, unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════
# HELPERS
# ═════════════════════════════════════════════════════════════════════
def kpi(label, value, sub="", color="#60a5fa"):
    return (
        f"<div class='kpi-card'>"
        f"<div class='kpi-lbl'>{label}</div>"
        f"<div class='kpi-val' style='color:{color}'>{value}</div>"
        f"{'<div class=\"kpi-sub\">'+sub+'</div>' if sub else ''}"
        f"</div>"
    )


def insight(text):
    return f"<div class='insight'>{text}</div>"


def divider():
    return "<div class='divider'></div>"


def pbar(pct, color="#60a5fa"):
    w = min(100, max(0, pct * 100))
    return (
        f"<div style='background:rgba(255,255,255,.12);border-radius:999px;height:7px;overflow:hidden;margin-top:4px'>"
        f"<div style='width:{w:.1f}%;height:100%;background:{color};border-radius:999px'></div>"
        f"</div>"
    )


# ═════════════════════════════════════════════════════════════════════
# DADOS
# ═════════════════════════════════════════════════════════════════════
def check_admin():
    admins = load_json_file(ADMIN_FILE, [])
    if not admins:
        hashed = hashlib.sha256(ADMIN_PASSWORD.encode()).hexdigest()
        save_json_file(ADMIN_FILE, [{"id": 1, "username": ADMIN_USERNAME, "password": hashed}])


@st.cache_data(ttl=5, show_spinner=False)
def load_obras():
    default = [
        {
            "id": 1,
            "titulo": "Guernica",
            "artista": "Pablo Picasso",
            "ano": "1937",
            "imagem": "https://upload.wikimedia.org/wikipedia/en/7/74/PicassoGuernica.jpg",
            "descricao_acessivel": "Pintura em preto, branco e cinza. A cena apresenta figuras humanas e animais fragmentados, transmitindo dor, caos e tensão."
        },
        {
            "id": 2,
            "titulo": "A Noite Estrelada",
            "artista": "Vincent van Gogh",
            "ano": "1889",
            "imagem": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ea/Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg/1200px-Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg",
            "descricao_acessivel": "Paisagem noturna com céu azul em movimento, estrelas amarelas brilhantes e uma vila ao fundo. A pincelada cria sensação de energia e profundidade."
        },
        {
            "id": 3,
            "titulo": "Mona Lisa",
            "artista": "Leonardo da Vinci",
            "ano": "1503",
            "imagem": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ec/Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_retouched.jpg/800px-Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_retouched.jpg",
            "descricao_acessivel": "Retrato de uma mulher sentada, com mãos cruzadas, expressão serena e leve sorriso. Ao fundo, uma paisagem distante em tons suaves."
        }
    ]
    obras = load_json_file(OBRAS_FILE, default)
    if not obras:
        save_json_file(OBRAS_FILE, default)
        return default

    changed = False
    for obra in obras:
        if "descricao_acessivel" not in obra:
            obra["descricao_acessivel"] = ""
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
    tags = load_json_file(TAGS_FILE, [])
    tags.append({
        "id": len(tags) + 1,
        "user_id": uid,
        "obra_id": obra_id,
        "tag": str(tag).lower().strip(),
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


def check_login(username, password):
    h = hashlib.sha256(password.encode()).hexdigest()
    return username == ADMIN_USERNAME and h == hashlib.sha256(ADMIN_PASSWORD.encode()).hexdigest()


def all_tags():
    t = load_json_file(TAGS_FILE, [])
    return pd.DataFrame(t) if t else pd.DataFrame()


def all_users():
    u = load_json_file(USERS_FILE, [])
    return pd.DataFrame(u) if u else pd.DataFrame()


# ═════════════════════════════════════════════════════════════════════
# EXPORT HTML
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
body{{font-family:sans-serif;background:linear-gradient(135deg,#0b1320,#163558);padding:40px;color:white}}
.c{{max-width:900px;margin:0 auto;background:rgba(255,255,255,.12);padding:50px;border-radius:24px;border:1px solid rgba(255,255,255,.22)}}
h1{{text-align:center;margin-bottom:15px;font-size:2.2rem}}
.hi{{text-align:center;margin-bottom:35px;opacity:.95}}
.ab{{background:rgba(96,165,250,.18);border:1px solid rgba(96,165,250,.4);color:#bfdbfe;padding:.35rem 1rem;border-radius:50px;font-weight:700;display:inline-block}}
.qb{{margin:22px 0;padding:18px 22px;background:rgba(255,255,255,.08);border-left:4px solid rgba(255,255,255,.45);border-radius:12px}}
.q{{font-weight:700;margin-bottom:8px}}
.a{{line-height:1.7;opacity:.92}}
.ft{{text-align:center;margin-top:40px;padding-top:18px;border-top:1px solid rgba(255,255,255,.2);opacity:.65;font-size:.88rem}}
</style></head>
<body><div class="c"><h1>Respostas do Questionário</h1>
<div class="hi">
  <p>Usuário Anônimo: <span class="ab">🐾 {animal}</span></p>
  <p style="margin-top:6px;opacity:.7">Data: {ui.get('timestamp','N/A')}</p>
</div>
<div class="qb"><div class="q">1. Nível de familiaridade com museus</div><div class="a">{ui.get('q1','N/A')}</div></div>
<div class="qb"><div class="q">2. Conhecimento sobre documentação museológica</div><div class="a">{ui.get('q2','N/A')}</div></div>
<div class="qb"><div class="q">3. O que você entende por tags?</div><div class="a">{ui.get('q3','N/A')}</div></div>
<div class="ft">Sistema Folksonomia Digital — Ctrl+P → Salvar como PDF</div>
</div></body></html>"""


def html_tags(uid, animal, obras, tags_df):
    ut = tags_df[tags_df["user_id"] == uid] if not tags_df.empty else pd.DataFrame()
    if ut.empty:
        return None
    od = {o["id"]: o for o in obras}

    rows = "".join(
        f"<tr><td>{i+1}</td>"
        f"<td>{od.get(r['obra_id'],{}).get('titulo','Obra '+str(r['obra_id']))}</td>"
        f"<td><span style='background:rgba(255,255,255,.15);padding:3px 10px;border-radius:50px'>{r['tag']}</span></td>"
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
body{{font-family:sans-serif;background:linear-gradient(135deg,#0b1320,#163558);padding:40px;color:white}}
.c{{max-width:1100px;margin:0 auto;background:rgba(255,255,255,.12);padding:50px;border-radius:24px;border:1px solid rgba(255,255,255,.22)}}
h1{{text-align:center;margin-bottom:15px;font-size:2.2rem}}
.hi{{text-align:center;margin-bottom:28px;opacity:.9}}
.ab{{background:rgba(96,165,250,.18);border:1px solid rgba(96,165,250,.4);color:#bfdbfe;padding:.35rem 1rem;border-radius:50px;font-weight:700;display:inline-block}}
.stats{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin:22px 0}}
.sb{{background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.18);padding:18px;border-radius:12px;text-align:center}}
.sv{{font-size:2.6rem;font-weight:800}}
.sl{{font-size:.82rem;text-transform:uppercase;letter-spacing:1.5px;margin-top:7px;opacity:.85}}
table{{width:100%;border-collapse:collapse;margin:18px 0}}
th,td{{padding:13px;text-align:left;border-bottom:1px solid rgba(255,255,255,.14)}}
th{{background:rgba(255,255,255,.14);font-weight:700;text-transform:uppercase;font-size:.82rem}}
tr:nth-child(even){{background:rgba(255,255,255,.03)}}
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
# INTERFACE
# ═════════════════════════════════════════════════════════════════════
def show_header():
    st.markdown(
        "<div class='top-navbar'><div class='navbar-logo'>Sistema Folksonomia Digital</div></div>",
        unsafe_allow_html=True
    )


def main():
    load_css()
    try:
        check_admin()
    except Exception as e:
        st.error(f"Erro ao inicializar: {e}")

    defaults = [
        ("user_id", gen_uid()),
        ("animal_name", generate_animal_name()),
        ("step", "intro"),
        ("answers", {})
    ]

    for k, v in defaults:
        if k not in st.session_state:
            st.session_state[k] = v

    if st.session_state["step"] != "completed":
        show_intro()
    else:
        show_header()
        st.markdown("<div class='main-content'>", unsafe_allow_html=True)
        with st.expander("Configurações de acessibilidade e visual", expanded=False):
            accessibility_panel()

        t1, t2 = st.tabs(["Explorar Obras", "Área Administrativa"])
        with t1:
            show_obras()
        with t2:
            show_admin()

        st.markdown("</div>", unsafe_allow_html=True)


def show_intro():
    st.markdown("<div class='main-content'>", unsafe_allow_html=True)
    st.markdown("<h1 class='main-title'>Sistema Folksonomia Digital</h1>", unsafe_allow_html=True)
    st.markdown(
        "<p class='subtitle'>Sistema colaborativo de catalogação de obras de arte<br>"
        "Complete o questionário para acessar a plataforma</p>",
        unsafe_allow_html=True
    )

    with st.expander("Configurações de acessibilidade e visual", expanded=False):
        accessibility_panel()

    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.markdown("<h2 style='text-align:center;margin-bottom:2rem;'>Questionário de Acesso</h2>", unsafe_allow_html=True)

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
                st.success("Questionário completo. Acesso liberado.")
                st.balloons()
                st.rerun()

    st.markdown("</div></div>", unsafe_allow_html=True)


def show_obras():
    st.markdown("<h1 class='main-title'>Galeria de Obras de Arte</h1>", unsafe_allow_html=True)
    st.markdown(
        "<p class='subtitle'>Explore as obras e contribua com suas tags descritivas</p>",
        unsafe_allow_html=True
    )

    obras = load_obras()
    if not obras:
        st.info("Nenhuma obra cadastrada.")
        return

    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    c1, c2 = st.columns([2, 1])
    with c1:
        sid = st.text_input("Filtrar por número da obra", "", placeholder="Ex: 1, 2, 3")
    with c2:
        sord = st.selectbox("Ordenar por", ["Número (crescente)", "Número (decrescente)"])
    st.markdown("</div>", unsafe_allow_html=True)

    filtered = obras
    if sid.strip().isdigit():
        filtered = [o for o in obras if str(o["id"]) == sid.strip()]
    filtered = sorted(filtered, key=lambda x: x["id"], reverse=(sord == "Número (decrescente)"))

    st.markdown(
        f"<div style='text-align:center;margin:1rem 0 1.6rem 0;font-weight:700'>Exibindo {len(filtered)} obra(s)</div>",
        unsafe_allow_html=True
    )

    cols = st.columns(3)
    for i, obra in enumerate(filtered):
        with cols[i % 3]:
            st.markdown(
                f"""
                <div class='obra-card'>
                    <img src="{obra['imagem']}" alt="Obra {obra['id']}">
                    <div style="padding:1rem 1rem 1.2rem 1rem">
                        <h3 style="margin-bottom:.3rem;">Obra #{obra['id']} — {obra['titulo']}</h3>
                        <p style="opacity:.85;font-size:.93rem;">{obra['artista']} — {obra['ano']}</p>
                        <p style="opacity:.72;font-size:.85rem;margin-top:.4rem;">Adicione uma tag descritiva para esta imagem</p>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

            if st.button("Adicionar Tag", key=f"btn_{obra['id']}", use_container_width=True):
                st.session_state["selected_obra"] = obra
                st.rerun()

            if "selected_obra" in st.session_state and st.session_state["selected_obra"]["id"] == obra["id"]:
                with st.form(f"tf_{obra['id']}"):
                    tag = st.text_input(
                        "Sua tag",
                        key=f"t_{obra['id']}",
                        placeholder="Ex: azul, retrato, dramático, céu..."
                    )
                    ca, cb = st.columns(2)
                    with ca:
                        sub = st.form_submit_button("Enviar", use_container_width=True)
                    with cb:
                        can = st.form_submit_button("Cancelar", use_container_width=True)

                    if sub and tag.strip():
                        save_tag(st.session_state["user_id"], obra["id"], tag)
                        st.success(f"Tag '{tag}' adicionada.")
                        del st.session_state["selected_obra"]
                        st.rerun()

                    if can:
                        del st.session_state["selected_obra"]
                        st.rerun()

            ut = get_obra_user_tags(obra["id"], st.session_state["user_id"])
            if not ut.empty:
                st.markdown("**Suas tags nesta obra:**")
                st.markdown(
                    "".join(f"<span class='tag-badge'>{r['tag']} ({r['count']})</span>" for _, r in ut.iterrows()),
                    unsafe_allow_html=True
                )
            else:
                st.info("Você ainda não criou tags para esta obra.")

            st.markdown("**Recursos de acessibilidade da obra:**")
            descricao_texto = montar_descricao_obra(obra, ut if not ut.empty else None)
            st.caption(descricao_texto)

            if st.session_state.get("audio_auto", False):
                audio_bytes = gerar_audio_descricao(descricao_texto)
                if audio_bytes:
                    st.audio(audio_bytes, format="audio/mp3")


def show_admin():
    if "admin_logged_in" not in st.session_state:
        st.session_state["admin_logged_in"] = False

    if not st.session_state["admin_logged_in"]:
        st.markdown("<h1 class='main-title'>Área Administrativa</h1>", unsafe_allow_html=True)
        st.markdown("<p class='subtitle'>Acesso restrito</p>", unsafe_allow_html=True)

        _, c2, _ = st.columns([1, 1, 1])
        with c2:
            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
            st.markdown("<h2 style='text-align:center;margin-bottom:1.5rem;'>Login Administrativo</h2>", unsafe_allow_html=True)

            with st.form("login"):
                username = st.text_input("Usuário", placeholder="Digite seu usuário")
                password = st.text_input("Senha", type="password", placeholder="Digite sua senha")
                sub = st.form_submit_button("Entrar no Sistema", use_container_width=True)

                if sub:
                    if check_login(username, password):
                        st.session_state["admin_logged_in"] = True
                        st.session_state["admin_username"] = username
                        st.success("Login realizado com sucesso.")
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
# ABA 1
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
    cards = [
        (c1, "Total de Tags", total, "registros", "#60a5fa"),
        (c2, "Tags Únicas", unicas, f"{unicas/total:.0%} do total" if total else "—", "#a78bfa"),
        (c3, "Participantes", nusers, "usuários ativos", "#34d399"),
        (c4, "Obras Cadastradas", nobs, f"{obs_ct} com tags", "#f59e0b"),
        (c5, "Média Tags/Usuário", f"{total/nusers:.1f}" if nusers else "—", "por participante", "#f472b6"),
    ]

    for col, lbl, val, sub, clr in cards:
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
                f"<div class='glass-card' style='padding:.9rem 1rem;'>"
                f"<div style='display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap'>"
                f"<div><span class='animal-badge'>🐾 {animal}</span> "
                f"<span style='opacity:.65;font-size:.78rem'>Acesso: {ts}</span></div>"
                f"<div style='min-width:200px;text-align:right'>"
                f"<strong>{nt} tags</strong> <span style='opacity:.7'>({nu} únicas)</span>"
                f"{pbar(p, '#60a5fa')}"
                f"<span style='opacity:.65;font-size:.75rem'>riqueza: {p:.0%}</span>"
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


# ═════════════════════════════════════════════════════════════════════
# ABA 2
# ═════════════════════════════════════════════════════════════════════
def tab_tags():
    tdf = all_tags()
    if tdf.empty:
        st.info("Nenhuma tag disponível.")
        return

    st.markdown("### Análise de Tags")
    t1, t2, t3 = st.tabs(["Visão Geral", "Frequência e Pizza", "Evolução Temporal"])

    df = tdf.copy()
    df["tag"] = df["tag"].astype(str).str.strip().str.lower()
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

    freq = df["tag"].value_counts().reset_index()
    freq.columns = ["Tag", "Frequência"]
    total_usos = int(freq["Frequência"].sum())
    freq["% do Total"] = (freq["Frequência"] / total_usos * 100).round(2)

    freq["Categoria"] = pd.cut(
        freq["Frequência"],
        bins=[0, 1, 2, 5, 10, 999999],
        labels=["Hapax (1x)", "Rara (2x)", "Ocasional (3–5x)", "Frequente (6–10x)", "Muito Frequente (10x+)"]
    )

    hapax = int((freq["Frequência"] == 1).sum())
    unicas = int(freq["Tag"].nunique())
    ttr = unicas / total_usos if total_usos else 0

    with t1:
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(kpi("Total de tags", total_usos, "usos registrados", "#60a5fa"), unsafe_allow_html=True)
        with c2:
            st.markdown(kpi("Tags únicas", unicas, "vocabulário", "#34d399"), unsafe_allow_html=True)
        with c3:
            st.markdown(kpi("Hapax", hapax, "uso único", "#f59e0b"), unsafe_allow_html=True)
        with c4:
            st.markdown(kpi("TTR", f"{ttr:.2%}", "riqueza vocabular", "#a78bfa"), unsafe_allow_html=True)

        st.markdown(divider(), unsafe_allow_html=True)

        cat_df = freq["Categoria"].value_counts().reset_index()
        cat_df.columns = ["Categoria", "Quantidade"]

        fig_cat = px.pie(
            cat_df,
            names="Categoria",
            values="Quantidade",
            hole=0.52,
            title="Distribuição das categorias de frequência"
        )
        fig_cat.update_traces(textinfo="percent+label")
        st.plotly_chart(fig_cat, use_container_width=True)

        st.markdown(insight(
            f"<strong>Leitura geral:</strong> O sistema possui <strong>{unicas}</strong> tags únicas em "
            f"<strong>{total_usos}</strong> usos. Existem <strong>{hapax}</strong> tags usadas apenas uma vez. "
            f"O índice TTR é de <strong>{ttr:.2%}</strong>, indicando o nível de diversidade vocabular."
        ), unsafe_allow_html=True)

    with t2:
        c1, c2 = st.columns([2, 1])

        with c1:
            top_n = st.slider("Quantidade de tags no gráfico principal", 5, 30, 10)
            top_freq = freq.head(top_n).copy()

            fig_bar = px.bar(
                top_freq,
                x="Tag",
                y="Frequência",
                text="Frequência",
                title=f"Top {top_n} tags mais utilizadas"
            )
            fig_bar.update_layout(xaxis_title="Tag", yaxis_title="Frequência")
            st.plotly_chart(fig_bar, use_container_width=True)

        with c2:
            pie_n = st.slider("Quantidade de tags no gráfico pizza", 3, 12, 6)
            pie_df = freq.head(pie_n).copy()
            resto = int(freq.iloc[pie_n:]["Frequência"].sum())

            if resto > 0:
                pie_df = pd.concat([
                    pie_df,
                    pd.DataFrame([{"Tag": "Outras", "Frequência": resto}])
                ], ignore_index=True)

            fig_pie = px.pie(
                pie_df,
                names="Tag",
                values="Frequência",
                hole=0.45,
                title="Participação das tags no total"
            )
            fig_pie.update_traces(textinfo="percent+label")
            st.plotly_chart(fig_pie, use_container_width=True)

        st.markdown(divider(), unsafe_allow_html=True)

        c3, c4 = st.columns(2)

        with c3:
            obra_tag = df.groupby(["obra_id", "tag"]).size().reset_index(name="Qtd")
            if not obra_tag.empty:
                top_heat = obra_tag.sort_values("Qtd", ascending=False).head(15)
                fig_tree = px.treemap(
                    top_heat,
                    path=["obra_id", "tag"],
                    values="Qtd",
                    title="Treemap de tags por obra"
                )
                st.plotly_chart(fig_tree, use_container_width=True)

        with c4:
            cat_table = freq.groupby("Categoria").agg(
                Quantidade=("Tag", "count"),
                Frequencia_Total=("Frequência", "sum")
            ).reset_index()
            st.dataframe(cat_table, use_container_width=True, hide_index=True)

        st.markdown("#### Tabela completa de frequências")
        st.dataframe(freq, use_container_width=True, hide_index=True)

        st.download_button(
            "Baixar frequências em CSV",
            freq.to_csv(index=False).encode("utf-8"),
            file_name=f"frequencias_tags_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )

    with t3:
        temp = df.dropna(subset=["timestamp"]).copy()
        if temp.empty:
            st.info("Sem dados temporais válidos.")
            return

        temp["Data"] = temp["timestamp"].dt.date
        temp["Hora"] = temp["timestamp"].dt.hour
        temp["AnoMes"] = temp["timestamp"].dt.to_period("M").astype(str)

        daily = temp.groupby("Data").agg(
            Tags=("tag", "count"),
            Tags_Unicas=("tag", "nunique"),
            Usuarios=("user_id", "nunique")
        ).reset_index()

        c1, c2 = st.columns(2)
        with c1:
            fig_line = px.line(
                daily,
                x="Data",
                y="Tags",
                markers=True,
                title="Evolução diária da criação de tags"
            )
            st.plotly_chart(fig_line, use_container_width=True)

        with c2:
            fig_line2 = px.line(
                daily,
                x="Data",
                y=["Tags_Unicas", "Usuarios"],
                markers=True,
                title="Tags únicas e usuários ativos por dia"
            )
            st.plotly_chart(fig_line2, use_container_width=True)

        st.markdown(divider(), unsafe_allow_html=True)

        c3, c4 = st.columns(2)
        with c3:
            monthly = temp.groupby("AnoMes").size().reset_index(name="Qtd")
            fig_month = px.bar(
                monthly,
                x="AnoMes",
                y="Qtd",
                text="Qtd",
                title="Distribuição mensal"
            )
            st.plotly_chart(fig_month, use_container_width=True)

        with c4:
            hour_df = temp.groupby("Hora").size().reset_index(name="Qtd")
            fig_hour = px.area(
                hour_df,
                x="Hora",
                y="Qtd",
                title="Distribuição por hora do dia"
            )
            st.plotly_chart(fig_hour, use_container_width=True)

        st.markdown("#### Tabela temporal consolidada")
        st.dataframe(daily.sort_values("Data", ascending=False), use_container_width=True, hide_index=True)


# ═════════════════════════════════════════════════════════════════════
# ABA 3
# ═════════════════════════════════════════════════════════════════════
def tab_connections():
    tdf = all_tags()
    obs = load_obras()

    if tdf.empty:
        st.warning("Nenhuma tag disponível.")
        return

    st.markdown("### Conexões e Agrupamentos de Tags")
    st.markdown(insight(
        "<strong>Como funciona:</strong> o algoritmo combina contenção de texto, "
        "palavras em comum e trigramas para identificar relações entre tags."
    ), unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        threshold = st.slider("Limiar de similaridade", 0.20, 0.90, 0.35, 0.05, key="ct")
    with c2:
        obra_f = st.selectbox("Filtrar por obra", ["Todas"] + [f"#{o['id']} — {o['titulo']}" for o in obs], key="co")
    with c3:
        max_c = st.number_input("Máx. conexões", 10, 300, 60, 10, key="cm")

    fdf = tdf.copy()
    if obra_f != "Todas":
        oid = int(obra_f.split("—")[0].replace("#", "").strip())
        fdf = tdf[tdf["obra_id"] == oid]

    all_t = fdf["tag"].tolist()
    if len(set(all_t)) < 2:
        st.warning("Necessário ao menos 2 tags distintas.")
        return

    with st.spinner("Calculando conexões..."):
        conns = tag_connections(all_t, threshold=threshold)
        clusters = tag_clusters(all_t, threshold=threshold)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(kpi("Total de Conexões", len(conns), f"limiar ≥ {threshold:.2f}", "#60a5fa"), unsafe_allow_html=True)
    with c2:
        st.markdown(kpi("Grupos Formados", len(clusters), "clusters de tags", "#a78bfa"), unsafe_allow_html=True)
    with c3:
        envolvidas = len(set([c["tag_a"] for c in conns] + [c["tag_b"] for c in conns]))
        st.markdown(kpi("Tags Envolvidas", envolvidas, "tags conectadas", "#34d399"), unsafe_allow_html=True)

    st.markdown(divider(), unsafe_allow_html=True)

    t1, t2 = st.tabs(["Lista de Conexões", "Grupos de Tags"])

    with t1:
        if not conns:
            st.info("Nenhuma conexão encontrada. Reduza o limiar.")
        else:
            tipos = sorted(set(c["tipo"] for c in conns))
            tipo_sel = st.multiselect("Filtrar por tipo", tipos, default=tipos, key="tsel")
            cf = [c for c in conns if c["tipo"] in tipo_sel][:max_c]
            freq_map = tdf["tag"].value_counts().to_dict()

            st.markdown(f"Exibindo **{len(cf)}** de **{len(conns)}** conexões")
            st.markdown(divider(), unsafe_allow_html=True)

            for c in cf:
                s = c["similaridade"]
                fa = freq_map.get(c["tag_a"], 0)
                fb = freq_map.get(c["tag_b"], 0)
                bar = "█" * int(s * 10) + "░" * (10 - int(s * 10))

                st.markdown(
                    f"<div class='conn-row'>"
                    f"<div>"
                    f"<span class='tag-badge'>{c['tag_a']}</span> "
                    f"<span style='opacity:.65;font-size:.78rem'>({fa}×)</span> "
                    f"<span style='opacity:.55'>↔</span> "
                    f"<span class='tag-badge'>{c['tag_b']}</span> "
                    f"<span style='opacity:.65;font-size:.78rem'>({fb}×)</span>"
                    f"</div>"
                    f"<div style='text-align:right'>"
                    f"<div style='font-family:monospace'>{bar} {s:.3f}</div>"
                    f"<div style='opacity:.7;font-size:.78rem'>{c['tipo']}</div>"
                    f"</div>"
                    f"</div>",
                    unsafe_allow_html=True
                )

            st.download_button(
                "Baixar conexões (CSV)",
                pd.DataFrame(conns).to_csv(index=False).encode("utf-8"),
                f"conexoes_{datetime.now().strftime('%Y%m%d')}.csv",
                "text/csv"
            )

    with t2:
        if not clusters:
            st.info("Nenhum grupo formado. Reduza o limiar.")
        else:
            colors = ["#60a5fa", "#34d399", "#f59e0b", "#a78bfa", "#f472b6", "#22d3ee"]
            freq_map = tdf["tag"].value_counts().to_dict()
            cls_sorted = sorted(clusters, key=len, reverse=True)

            st.markdown(f"**{len(cls_sorted)} grupo(s) de tags relacionadas**")
            st.markdown(divider(), unsafe_allow_html=True)

            for i, cl in enumerate(cls_sorted, 1):
                color = colors[(i - 1) % len(colors)]
                total_uses = sum(freq_map.get(t, 0) for t in cl)
                pills = "".join(
                    f"<span class='cluster-pill'>{t} <span style='opacity:.65;font-size:.72rem'>({freq_map.get(t, 0)}×)</span></span>"
                    for t in sorted(cl, key=lambda x: freq_map.get(x, 0), reverse=True)
                )

                st.markdown(
                    f"<div class='cluster-wrap' style='border-left:4px solid {color}'>"
                    f"<div class='cluster-title'>Grupo {i} · {len(cl)} tags · {total_uses} usos totais</div>"
                    f"{pills}</div>",
                    unsafe_allow_html=True
                )

            st.markdown("#### Resumo dos grupos")
            summ = pd.DataFrame([{
                "Grupo": f"Grupo {i}",
                "Qtd Tags": len(cl),
                "Total Usos": sum(freq_map.get(t, 0) for t in cl),
                "Tags": ", ".join(sorted(cl, key=lambda x: freq_map.get(x, 0), reverse=True)[:6]) + ("..." if len(cl) > 6 else "")
            } for i, cl in enumerate(cls_sorted, 1)])
            st.dataframe(summ, use_container_width=True, hide_index=True)

            st.download_button(
                "Baixar grupos (CSV)",
                summ.to_csv(index=False).encode("utf-8"),
                f"clusters_{datetime.now().strftime('%Y%m%d')}.csv",
                "text/csv"
            )


# ═════════════════════════════════════════════════════════════════════
# ABA 4
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
        st.markdown(kpi("Participantes", len(merged), "usuários", "#60a5fa"), unsafe_allow_html=True)
    with c2:
        st.markdown(kpi("Média Tags/Usuário", f"{merged['Total_Tags'].mean():.1f}", "", "#34d399"), unsafe_allow_html=True)
    with c3:
        st.markdown(kpi("Maior Contribuição", int(merged["Total_Tags"].max()) if not merged.empty else 0, top_u[:18], "#f59e0b"), unsafe_allow_html=True)
    with c4:
        st.markdown(kpi("Riqueza Média (TTR)", f"{merged['TTR'].mean():.2%}", "vocabular", "#a78bfa"), unsafe_allow_html=True)

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
        st.markdown("#### Contribuição por Participante")
        st.bar_chart(merged.set_index("Usuário")["Total_Tags"].sort_values(ascending=False))

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Riqueza Vocabular (TTR) por Usuário**")
            st.bar_chart(merged.set_index("Usuário")["TTR"].sort_values(ascending=False))
        with c2:
            st.markdown("**Obras Etiquetadas por Usuário**")
            st.bar_chart(merged.set_index("Usuário")["Obras"].sort_values(ascending=False))

    with t2:
        st.markdown("#### Perfil Detalhado por Participante")
        uopts = [f"🐾 {r.get('animal_name', r['user_id'][:8])}" for _, r in udf.iterrows()]
        usel = st.selectbox("Selecione um participante", uopts, key="ui_sel")
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
                st.markdown(kpi("Tags Criadas", ttl, "", "#60a5fa"), unsafe_allow_html=True)
            with c2:
                st.markdown(kpi("Tags Únicas", unq, f"TTR: {ttr_u:.2%}", "#34d399"), unsafe_allow_html=True)
            with c3:
                st.markdown(kpi("Obras Tagueadas", utags["obra_id"].nunique(), "", "#f59e0b"), unsafe_allow_html=True)

            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"**Top tags de {uanim}:**")
                st.bar_chart(utags["tag"].value_counts().head(15))
            with c2:
                st.markdown("**Distribuição por obra:**")
                st.bar_chart(utags.groupby("obra_id").size().rename(index=od))

            st.markdown("**Conexões nas tags deste participante (limiar 0.30):**")
            uconns = tag_connections(utags["tag"].tolist(), threshold=0.30)
            if uconns:
                freq_map = utags["tag"].value_counts().to_dict()
                for c in uconns[:10]:
                    fa = freq_map.get(c["tag_a"], 0)
                    fb = freq_map.get(c["tag_b"], 0)
                    st.markdown(
                        f"<div class='conn-row'>"
                        f"<div>"
                        f"<span class='tag-badge'>{c['tag_a']}</span> "
                        f"<span style='opacity:.65;font-size:.75rem'>({fa}×)</span> "
                        f"<span style='opacity:.55'>↔</span> "
                        f"<span class='tag-badge'>{c['tag_b']}</span> "
                        f"<span style='opacity:.65;font-size:.75rem'>({fb}×)</span>"
                        f"</div>"
                        f"<div style='opacity:.8;font-size:.82rem'>{c['similaridade']:.3f} · {c['tipo']}</div>"
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
            st.bar_chart(q1c)
            q1p = (q1c / q1c.sum() * 100).round(1).reset_index()
            q1p.columns = ["Resposta", "%"]
            st.dataframe(q1p, use_container_width=True, hide_index=True)

        with c2:
            st.markdown("**Q2 — Conhecimento sobre Documentação Museológica**")
            q2c = udf["q2"].value_counts()
            st.bar_chart(q2c)
            q2p = (q2c / q2c.sum() * 100).round(1).reset_index()
            q2p.columns = ["Resposta", "%"]
            st.dataframe(q2p, use_container_width=True, hide_index=True)

        st.markdown(divider(), unsafe_allow_html=True)
        st.markdown("**Q3 — Respostas abertas**")

        disp = udf.copy()
        if "animal_name" in disp.columns:
            disp = disp.rename(columns={"animal_name": "Usuário Anônimo"})
        disp["Palavras"] = disp["q3"].astype(str).str.split().str.len()

        st.markdown(f"Comprimento médio das respostas: **{disp['Palavras'].mean():.0f} palavras** por participante")
        st.bar_chart(disp["Palavras"].value_counts().sort_index().rename("Qtd Respostas"))

        st.markdown(divider(), unsafe_allow_html=True)
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

        st.markdown("#### Cruzamentos: Perfil do Participante × Comportamento de Tagging")

        m = merged.copy()
        m["TTR"] = (m["Tags_Unicas"] / m["Total_Tags"].replace(0, np.nan)).fillna(0)

        st.markdown(divider(), unsafe_allow_html=True)
        st.markdown("**Familiaridade com Museus × Média de Tags Criadas**")
        avg_q1 = m.groupby("q1")["Total_Tags"].mean().sort_values(ascending=False)
        st.bar_chart(avg_q1)
        t_q1 = avg_q1.reset_index()
        t_q1.columns = ["Familiaridade", "Média de Tags"]
        t_q1["Média de Tags"] = t_q1["Média de Tags"].round(2)
        st.dataframe(t_q1, use_container_width=True, hide_index=True)

        st.markdown(divider(), unsafe_allow_html=True)
        st.markdown("**Conhecimento Museológico × Tags Únicas**")
        avg_q2 = m.groupby("q2")["Tags_Unicas"].mean().sort_values(ascending=False)
        st.bar_chart(avg_q2)
        t_q2 = avg_q2.reset_index()
        t_q2.columns = ["Conhecimento", "Média Tags Únicas"]
        t_q2["Média Tags Únicas"] = t_q2["Média Tags Únicas"].round(2)
        st.dataframe(t_q2, use_container_width=True, hide_index=True)

        st.markdown(divider(), unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Familiaridade × TTR**")
            avg_ttr = m.groupby("q1")["TTR"].mean().sort_values(ascending=False)
            st.bar_chart(avg_ttr)
        with c2:
            st.markdown("**Conhecimento Museológico × TTR**")
            avg_ttr2 = m.groupby("q2")["TTR"].mean().sort_values(ascending=False)
            st.bar_chart(avg_ttr2)

        st.markdown(divider(), unsafe_allow_html=True)
        st.markdown("#### Tabela Consolidada de Cruzamentos")
        cross = m.groupby("q1").agg(
            Usuários=("user_id", "count"),
            Média_Tags=("Total_Tags", "mean"),
            Média_Únicas=("Tags_Unicas", "mean"),
            Riqueza_TTR=("TTR", "mean")
        ).round(2).reset_index()
        cross.columns = ["Familiaridade", "Usuários", "Média Tags", "Média Únicas", "Riqueza (TTR)"]
        st.dataframe(cross, use_container_width=True, hide_index=True)

        st.markdown(insight(
            "<strong>Interpretação:</strong> compare se participantes com maior familiaridade com museus "
            "produzem mais tags, maior diversidade vocabular e maior riqueza terminológica."
        ), unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════
# ABA 5
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
                    st.caption(obra.get("descricao_acessivel", "Sem descrição acessível cadastrada."))

                    if st.session_state.get("audio_auto", False):
                        audio = gerar_audio_descricao(montar_descricao_obra(obra))
                        if audio:
                            st.audio(audio, format="audio/mp3")

                with c3:
                    if st.button("Remover", key=f"del_{obra['id']}"):
                        obras.remove(obra)
                        save_json_file(OBRAS_FILE, obras)
                        st.success("Obra removida.")
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
            descricao_acessivel = st.text_area(
                "Descrição acessível da imagem",
                height=140,
                placeholder="Descreva visualmente a obra para pessoas cegas ou com baixa visão."
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
                        "descricao_acessivel": descricao_acessivel
                    })
                    save_json_file(OBRAS_FILE, obras)
                    st.success("Obra adicionada.")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("Preencha todos os campos obrigatórios.")


# ═════════════════════════════════════════════════════════════════════
# ABA 6
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
                obras_df = pd.DataFrame(obs)
                st.download_button(
                    "Obras (CSV)",
                    obras_df.to_csv(index=False).encode("utf-8"),
                    f"obras_{datetime.now().strftime('%Y%m%d')}.csv",
                    "text/csv",
                    use_container_width=True
                )

        st.markdown(divider(), unsafe_allow_html=True)
        st.markdown("#### Exportar Conexões de Tags")

        if not tdf.empty:
            thr = st.slider("Limiar de similaridade", 0.2, 0.9, 0.35, 0.05, key="exp_thr")

            if st.button("Gerar arquivo de conexões"):
                with st.spinner("Calculando..."):
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
        usel = st.selectbox("Selecione um participante", uopts, key="exp_u")
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


if __name__ == "__main__":
    main()
