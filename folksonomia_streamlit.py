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
import urllib.request
warnings.filterwarnings('ignore')

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

# Descrições de acessibilidade para as obras padrão
OBRAS_DESCRICOES = {
    1: "Guernica, de Pablo Picasso, 1937. Pintura em óleo sobre tela em preto, branco e tons de cinza. Retrata o bombardeio da cidade basca de Guernica durante a Guerra Civil Espanhola. Figuras humanas e animais em agonia: uma mãe segura um bebê morto, um touro, um cavalo ferido, soldados caídos e chamas ao fundo. A composição é caótica e angustiante, expressando o horror da guerra.",
    2: "A Noite Estrelada, de Vincent van Gogh, 1889. Óleo sobre tela de estilo pós-impressionista. Representa o céu noturno sobre Saint-Rémy-de-Provence visto da janela do asilo onde o artista estava internado. O céu é dominado por redemoinhos espirais azuis e amarelos, com uma lua crescente luminosa e estrelas grandes e brilhantes. Na base, uma aldeia tranquila com uma igreja de torre alta e ciprestes escuros em primeiro plano.",
    3: "Mona Lisa, de Leonardo da Vinci, 1503. Pintura a óleo sobre madeira de álamo. Retrato de uma mulher de expressão enigmática e sorriso sutil, conhecida como Lisa Gherardini. O fundo revela uma paisagem montanhosa e aquática esmaecida pela técnica sfumato. A mulher veste roupas renascentistas escuras, com cabelos soltos sob um véu translúcido, e olha diretamente para o observador."
}

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
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return default
    return default

def save_json_file(filepath, data):
    ensure_data_dir()
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar {filepath}: {e}")
        return False

# ── SIMILARIDADE ──────────────────────────────────────────────────────
def ntag(tag):   return tag.lower().strip()
def words(tag):  return set(ntag(tag).split())
def ngrams(text, n=3):
    t = ntag(text)
    return set([t]) if len(t) < n else set(t[i:i+n] for i in range(len(t)-n+1))

def sim(t1, t2):
    a, b = ntag(t1), ntag(t2)
    if a == b: return 1.0
    if a in b or b in a:
        return 0.55 + 0.45*(min(len(a),len(b))/max(len(a),len(b)))
    w1,w2 = words(t1),words(t2)
    if w1 and w2:
        j = len(w1&w2)/len(w1|w2)
        if j >= 0.5: return j
    if len(a)>=3 and len(b)>=3:
        ng1,ng2 = ngrams(a),ngrams(b)
        nj = len(ng1&ng2)/len(ng1|ng2) if ng1|ng2 else 0
        if nj > 0:
            wj = len(w1&w2)/len(w1|w2) if w1|w2 else 0
            return 0.6*nj + 0.4*wj
    return 0.0

def tag_connections(tags_list, threshold=0.35):
    uniq = list(set(ntag(t) for t in tags_list))
    conns = []
    for i in range(len(uniq)):
        for j in range(i+1, len(uniq)):
            s = sim(uniq[i], uniq[j])
            if s >= threshold:
                w1,w2 = words(uniq[i]),words(uniq[j])
                shared = w1&w2
                if uniq[i] in uniq[j] or uniq[j] in uniq[i]: tipo = "Contenção"
                elif shared: tipo = f"Palavra comum: '{', '.join(shared)}'"
                else: tipo = "Similaridade fonética"
                conns.append({"tag_a":uniq[i],"tag_b":uniq[j],"similaridade":round(s,3),"tipo":tipo})
    conns.sort(key=lambda x: x["similaridade"], reverse=True)
    return conns

def tag_clusters(tags_list, threshold=0.35):
    uniq  = list(set(ntag(t) for t in tags_list))
    conns = tag_connections(uniq, threshold)
    par   = {t:t for t in uniq}
    def find(x):
        while par[x]!=x: par[x]=par[par[x]]; x=par[x]
        return x
    def union(a,b):
        ra,rb = find(a),find(b)
        if ra!=rb: par[ra]=rb
    for c in conns: union(c["tag_a"],c["tag_b"])
    cl = defaultdict(list)
    for t in uniq: cl[find(t)].append(t)
    return [sorted(v) for v in cl.values() if len(v)>1]

# ── ACESSIBILIDADE ────────────────────────────────────────────────────
def get_accessibility_settings():
    if 'acc_font_size' not in st.session_state:
        st.session_state['acc_font_size'] = 'normal'
    if 'acc_theme' not in st.session_state:
        st.session_state['acc_theme'] = 'dark'
    if 'acc_high_contrast' not in st.session_state:
        st.session_state['acc_high_contrast'] = False
    if 'acc_dyslexia' not in st.session_state:
        st.session_state['acc_dyslexia'] = False

def accessibility_bar():
    """Barra de acessibilidade fixa no topo."""
    get_accessibility_settings()
    theme     = st.session_state['acc_theme']
    font_size = st.session_state['acc_font_size']
    high_c    = st.session_state['acc_high_contrast']
    dyslexia  = st.session_state['acc_dyslexia']

    font_map  = {'pequena':'0.82rem','normal':'1rem','grande':'1.18rem','muito_grande':'1.38rem'}
    fs        = font_map.get(font_size,'1rem')

    # Paleta de tema
    if theme == 'light':
        bg_body   = "linear-gradient(-45deg,#e8f4f8 0%,#f0e8ff 25%,#e8f0ff 50%,#f8f0e8 75%,#e8f4f8 100%)"
        card_bg   = "rgba(255,255,255,0.85)"
        card_brd  = "rgba(0,0,0,0.15)"
        text_col  = "#1a1a2e"
        text_sec  = "rgba(0,0,0,0.6)"
        input_bg  = "rgba(255,255,255,0.9)"
        input_brd = "rgba(0,0,0,0.25)"
        navbar_bg = "rgba(255,255,255,0.85)"
        navbar_brd= "rgba(0,0,0,0.1)"
        tab_bg    = "rgba(0,0,0,0.06)"
        tab_sel   = "rgba(0,0,0,0.18)"
        btn_bg    = "rgba(0,0,0,0.12)"
        btn_hov   = "rgba(0,0,0,0.22)"
        kpi_bg    = "rgba(255,255,255,0.7)"
        sc_bg     = "rgba(0,0,0,0.04)"
        acc_bg    = "rgba(255,255,255,0.95)"
        acc_brd   = "rgba(0,0,0,0.15)"
        badge_bg  = "rgba(0,0,0,0.1)"
        tag_col   = "#1a1a2e"
    elif high_c:
        bg_body   = "#000000"
        card_bg   = "#1a1a1a"
        card_brd  = "#ffffff"
        text_col  = "#ffffff"
        text_sec  = "#ffff00"
        input_bg  = "#111111"
        input_brd = "#ffffff"
        navbar_bg = "#000000"
        navbar_brd= "#ffffff"
        tab_bg    = "#222222"
        tab_sel   = "#444444"
        btn_bg    = "#333333"
        btn_hov   = "#555555"
        kpi_bg    = "#1a1a1a"
        sc_bg     = "#111111"
        acc_bg    = "#000000"
        acc_brd   = "#ffffff"
        badge_bg  = "#333333"
        tag_col   = "#ffffff"
    else:
        bg_body   = "linear-gradient(-45deg,#000 0%,#001F3F 25%,#000 50%,#001F3F 75%,#000 100%)"
        card_bg   = "rgba(255,255,255,0.15)"
        card_brd  = "rgba(255,255,255,0.3)"
        text_col  = "#e0e0e0"
        text_sec  = "rgba(255,255,255,0.65)"
        input_bg  = "rgba(255,255,255,0.18)"
        input_brd = "rgba(255,255,255,0.28)"
        navbar_bg = "rgba(255,255,255,0.1)"
        navbar_brd= "rgba(255,255,255,0.2)"
        tab_bg    = "rgba(255,255,255,0.1)"
        tab_sel   = "rgba(255,255,255,0.33)"
        btn_bg    = "rgba(255,255,255,0.25)"
        btn_hov   = "rgba(255,255,255,0.4)"
        kpi_bg    = "rgba(255,255,255,0.16)"
        sc_bg     = "rgba(255,255,255,0.07)"
        acc_bg    = "rgba(255,255,255,0.08)"
        acc_brd   = "rgba(255,255,255,0.2)"
        badge_bg  = "rgba(255,255,255,0.25)"
        tag_col   = "white"

    font_family = "'OpenDyslexic', 'Poppins', sans-serif" if dyslexia else "'Poppins', sans-serif"

    st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800&display=swap');
@font-face {{
  font-family: 'OpenDyslexic';
  src: url('https://cdn.jsdelivr.net/npm/opendyslexic@0.91.12/dist/OpenDyslexic-Regular.otf');
}}

* {{ margin:0; padding:0; box-sizing:border-box; font-family:{font_family} !important; font-size:{fs}; }}

@keyframes bg {{0%{{background-position:0% 50%}}50%{{background-position:100% 50%}}100%{{background-position:0% 50%}}}}
.stApp {{
  background:{bg_body};
  background-size:400% 400%;
  animation:bg 15s ease infinite;
  color:{text_col};
}}

/* ── BARRA DE ACESSIBILIDADE ── */
.acc-bar {{
  position:fixed; top:0; left:0; right:0; z-index:10001;
  background:{acc_bg};
  backdrop-filter:blur(20px) saturate(180%);
  border-bottom:1px solid {acc_brd};
  padding:.45rem 2rem;
  display:flex; align-items:center; gap:.9rem; flex-wrap:wrap;
}}
.acc-label {{
  color:{text_col}; font-size:.75rem !important; font-weight:700;
  text-transform:uppercase; letter-spacing:1.5px; opacity:.8;
  white-space:nowrap;
}}
.acc-sep {{
  width:1px; height:22px;
  background:{acc_brd};
  margin:0 .3rem;
}}

/* ── NAVBAR ── */
.top-navbar {{
  position:fixed; top:42px; left:0; right:0; z-index:9999;
  background:{navbar_bg};
  backdrop-filter:blur(20px) saturate(180%);
  border-bottom:1px solid {navbar_brd};
  padding:1.2rem 3rem;
  display:flex; justify-content:space-between; align-items:center;
  box-shadow:0 8px 32px rgba(0,0,0,.1);
}}
.navbar-logo {{
  font-size:1.7rem; font-weight:800;
  background:linear-gradient(135deg,#a7e6ff 0%,#d1baff 100%);
  -webkit-background-clip:text; -webkit-text-fill-color:transparent;
  background-clip:text; letter-spacing:-1px;
}}

/* ── CONTEÚDO PRINCIPAL ── */
.main-content {{
  margin-top:155px; padding:2rem 3rem;
  max-width:1600px; margin-left:auto; margin-right:auto;
}}

/* ── GLASS CARDS ── */
.glass-card {{
  background:{card_bg};
  backdrop-filter:blur(20px) saturate(180%);
  border:1px solid {card_brd};
  border-radius:24px; padding:2.5rem; margin:1.5rem 0;
  box-shadow:0 8px 32px rgba(0,0,0,.1);
  transition:all .4s cubic-bezier(.4,0,.2,1);
  position:relative; overflow:hidden;
}}
.glass-card::before {{
  content:''; position:absolute; top:0; left:-100%;
  width:100%; height:100%;
  background:linear-gradient(90deg,transparent,rgba(255,255,255,.15),transparent);
  transition:left .5s;
}}
.glass-card:hover::before {{ left:100%; }}
.glass-card:hover {{
  transform:translateY(-8px) scale(1.01);
  box-shadow:0 16px 48px rgba(0,0,0,.2);
  border-color:{card_brd};
}}

/* ── OBRA CARD ── */
.obra-card {{
  background:{card_bg};
  backdrop-filter:blur(15px) saturate(180%);
  border:1px solid {card_brd};
  border-radius:20px; overflow:hidden;
  transition:all .4s cubic-bezier(.4,0,.2,1);
  cursor:pointer; position:relative;
}}
.obra-card:hover {{
  transform:translateY(-10px) scale(1.02);
  box-shadow:0 20px 60px rgba(0,31,63,.4);
  border-color:{card_brd};
}}
.obra-card img {{
  width:100%; height:280px; object-fit:cover;
  transition:transform .6s cubic-bezier(.4,0,.2,1);
}}
.obra-card:hover img {{ transform:scale(1.1); }}

/* ── TÍTULOS E TEXTOS ── */
.main-title {{
  color:{text_col}; font-size:3.2rem; font-weight:800;
  text-align:center; margin:2rem 0 1rem;
  letter-spacing:-2px; text-shadow:0 4px 20px rgba(0,0,0,.3);
}}
.subtitle {{
  color:{text_sec}; font-size:1.2rem;
  text-align:center; margin-bottom:3rem;
  line-height:1.8; font-weight:300;
}}

/* ── TAG BADGES ── */
.tag-badge {{
  display:inline-block;
  background:{badge_bg};
  backdrop-filter:blur(10px);
  border:1px solid {card_brd};
  color:{tag_col}; padding:.5rem 1.1rem;
  border-radius:50px; margin:.3rem;
  font-size:.88rem; font-weight:600;
  transition:all .3s;
}}
.tag-badge:hover {{
  background:rgba(255,255,255,.4);
  transform:translateY(-3px) scale(1.05);
}}
.tag-green  {{ background:rgba(34,197,94,.25)!important;  border-color:rgba(34,197,94,.5)!important;  color:#dcfce7!important }}
.tag-amber  {{ background:rgba(245,158,11,.25)!important; border-color:rgba(245,158,11,.5)!important; color:#fef3c7!important }}
.tag-blue   {{ background:rgba(96,165,250,.25)!important; border-color:rgba(96,165,250,.5)!important; color:#dbeafe!important }}

.animal-badge {{
  display:inline-block;
  background:rgba(167,230,255,.2);
  border:1px solid rgba(167,230,255,.45);
  color:#a7e6ff; padding:.35rem 1rem;
  border-radius:50px; font-size:.85rem; font-weight:700;
}}

/* ── KPI CARDS ── */
.kpi-card {{
  background:{kpi_bg};
  backdrop-filter:blur(20px) saturate(180%);
  border:1px solid {card_brd};
  border-radius:18px; padding:1.6rem;
  text-align:center; color:{text_col};
  box-shadow:0 8px 32px rgba(0,0,0,.12);
  transition:all .4s;
}}
.kpi-card:hover {{
  transform:translateY(-6px) scale(1.04);
  box-shadow:0 16px 48px rgba(0,31,63,.28);
}}
.kpi-val {{
  font-size:2.5rem; font-weight:800;
  margin:.6rem 0;
  text-shadow:0 4px 20px rgba(0,0,0,.2);
}}
.kpi-lbl {{
  font-size:.78rem !important;
  text-transform:uppercase; letter-spacing:2px;
  font-weight:600; opacity:.8;
}}
.kpi-sub {{ font-size:.7rem !important; opacity:.5; margin-top:.3rem; }}

/* ── SECTION CARDS ── */
.sc {{
  background:{sc_bg};
  border:1px solid {card_brd};
  border-radius:14px; padding:1.3rem; margin:.7rem 0;
}}
.sc-b {{ border-left:4px solid #60a5fa; background:rgba(96,165,250,.07); }}
.sc-g {{ border-left:4px solid #34d399; background:rgba(52,211,153,.07); }}
.sc-p {{ border-left:4px solid #a78bfa; background:rgba(167,139,250,.07); }}
.sc-a {{ border-left:4px solid #fbbf24; background:rgba(251,191,36,.07); }}

/* ── INSIGHT BOX ── */
.insight {{
  background:rgba(167,230,255,.1);
  border:1px solid rgba(167,230,255,.28);
  border-radius:12px; padding:1rem 1.4rem;
  margin:.6rem 0; color:{text_sec};
  font-size:.9rem; line-height:1.7;
}}
.insight strong {{ color:#a7e6ff; }}

/* ── CONEXÕES ── */
.conn-row {{
  display:flex; justify-content:space-between;
  align-items:center; flex-wrap:wrap; gap:8px;
  background:{sc_bg};
  border-radius:11px; padding:.85rem 1.2rem; margin:.3rem 0;
  border-left:3px solid {card_brd};
  transition:background .2s;
}}
.conn-row:hover {{ background:rgba(255,255,255,.12); }}

/* ── CLUSTERS ── */
.cluster-wrap {{
  background:{sc_bg};
  border-radius:14px; padding:1.1rem 1.4rem;
  margin:.5rem 0; border:1px solid {card_brd};
}}
.cluster-title {{
  font-size:.76rem !important; text-transform:uppercase;
  letter-spacing:1.5px; color:rgba(167,139,250,.8);
  margin-bottom:.55rem; font-weight:700;
}}
.cluster-pill {{
  display:inline-flex; align-items:center; gap:5px;
  background:rgba(168,85,247,.2);
  border:1px solid rgba(168,85,247,.38);
  border-radius:50px; padding:.32rem .85rem;
  margin:.2rem; font-size:.78rem !important;
  font-weight:600; color:#f3e8ff;
}}

/* ── PROGRESS BAR ── */
.pbar-o {{ background:rgba(255,255,255,.1); border-radius:50px; height:6px; margin:3px 0; overflow:hidden; }}
.pbar-i {{ height:100%; border-radius:50px; transition:width .5s; }}

/* ── DIVIDER ── */
.divider {{
  height:1px;
  background:linear-gradient(90deg,transparent,{card_brd},transparent);
  margin:1.6rem 0;
}}

/* ── BOTÕES ── */
.stButton button {{
  background:{btn_bg} !important;
  backdrop-filter:blur(15px) !important;
  color:{text_col} !important;
  border:1px solid {card_brd} !important;
  border-radius:50px !important;
  padding:.9rem 2.2rem !important;
  font-weight:700 !important; font-size:1rem !important;
  transition:all .4s !important;
  box-shadow:0 8px 25px rgba(0,0,0,.15) !important;
  text-transform:uppercase; letter-spacing:1px;
}}
.stButton button:hover {{
  background:{btn_hov} !important;
  box-shadow:0 12px 40px rgba(0,31,63,.4) !important;
  transform:translateY(-4px) scale(1.05) !important;
}}

/* ── INPUTS ── */
.stTextInput input, .stTextArea textarea, .stSelectbox select {{
  background:{input_bg} !important;
  backdrop-filter:blur(10px) !important;
  border:1px solid {input_brd} !important;
  color:{text_col} !important;
  border-radius:14px !important;
  padding:.9rem !important; font-weight:500 !important;
}}
.stTextInput input::placeholder, .stTextArea textarea::placeholder {{
  color:{text_sec} !important;
}}
.stTextInput input:focus, .stTextArea textarea:focus {{
  border-color:{card_brd} !important;
  box-shadow:0 0 0 3px rgba(255,255,255,.18) !important;
}}
label {{
  color:{text_col} !important; font-weight:700 !important;
  text-shadow:0 2px 10px rgba(0,0,0,.2);
}}

/* ── TABS ── */
.stTabs [data-baseweb="tab-list"] {{
  gap:.7rem; background:{tab_bg};
  backdrop-filter:blur(10px);
  padding:.45rem; border-radius:14px;
}}
.stTabs [data-baseweb="tab"] {{
  background:rgba(255,255,255,.14);
  border:1px solid {card_brd};
  border-radius:10px; color:{text_col};
  padding:.75rem 1.5rem; font-weight:700; transition:all .3s;
}}
.stTabs [data-baseweb="tab"]:hover {{
  background:rgba(255,255,255,.24); transform:translateY(-2px);
}}
.stTabs [aria-selected="true"] {{
  background:{tab_sel} !important;
  border-color:{card_brd} !important;
  box-shadow:0 6px 20px rgba(0,31,63,.25) !important;
}}

/* ── ALERTAS ── */
.stAlert {{
  background:{card_bg} !important;
  backdrop-filter:blur(15px) !important;
  border-radius:14px !important;
  border-left:4px solid !important;
  color:{text_col} !important;
}}

/* ── TABELAS ── */
.dataframe {{
  background:{card_bg} !important;
  border:1px solid {card_brd} !important;
  border-radius:14px !important;
  color:{text_col} !important;
}}
.dataframe th {{
  background:{tab_sel} !important;
  color:{text_col} !important; font-weight:700 !important;
}}
.dataframe td {{ color:{text_col} !important; }}

/* ── AUDIO DESC ── */
.audio-desc-wrap {{
  background:rgba(96,165,250,.1);
  border:1px solid rgba(96,165,250,.3);
  border-radius:14px; padding:1rem 1.3rem;
  margin:.6rem 0;
}}
.audio-desc-title {{
  color:#a7e6ff; font-size:.8rem !important;
  font-weight:700; text-transform:uppercase;
  letter-spacing:1.5px; margin-bottom:.5rem;
}}
.audio-desc-text {{
  color:{text_sec}; font-size:.88rem !important; line-height:1.7;
}}

/* ── FOCUS / SKIP ── */
.skip-link {{
  position:absolute; top:-40px; left:0;
  background:#a7e6ff; color:#000;
  padding:.6rem 1rem; z-index:99999;
  font-weight:700; border-radius:0 0 8px 0;
  text-decoration:none; transition:top .2s;
}}
.skip-link:focus {{ top:0; }}
*:focus-visible {{
  outline:3px solid #a7e6ff !important;
  outline-offset:2px !important;
}}

/* ── MISC ── */
#MainMenu, footer, header {{ visibility:hidden; }}
.stDeployButton {{ display:none; }}
[data-testid="stSidebar"] {{ display:none; }}
h1,h2,h3,h4,h5,h6 {{
  color:{text_col}; font-weight:700;
  text-shadow:0 2px 15px rgba(0,0,0,.3);
}}
div[data-testid="stTextInput"]>div {{
  background:transparent !important; border:none !important;
  box-shadow:none !important; padding:0 !important;
}}
div[data-testid="stTextInput"] {{
  background:transparent !important; border:none !important;
}}
div[data-testid="stTextInput"] input {{
  border-radius:11px !important;
  background:{input_bg} !important;
  border:1px solid {input_brd} !important;
  padding:.75rem 1rem !important;
}}
@media(max-width:768px) {{
  .main-title {{ font-size:2rem; }}
  .main-content {{ margin-top:175px; padding:1rem; }}
  .acc-bar {{ padding:.35rem 1rem; gap:.5rem; }}
}}
</style>""", unsafe_allow_html=True)


def render_accessibility_bar():
    """Renderiza a barra de acessibilidade via botões Streamlit no topo."""
    get_accessibility_settings()

    # Link pular para conteúdo
    st.markdown("<a class='skip-link' href='#conteudo-principal' tabindex='1'>Pular para o conteúdo</a>",
                unsafe_allow_html=True)

    with st.container():
        st.markdown("<div class='acc-bar' role='toolbar' aria-label='Barra de acessibilidade'>", unsafe_allow_html=True)
        cols = st.columns([1.2, .5, .5, .5, .5, .3, .7, .7, .3, .7, .7])

        with cols[0]:
            st.markdown("<span class='acc-label'>♿ Acessibilidade</span>", unsafe_allow_html=True)
        with cols[1]:
            st.markdown("<span class='acc-label' style='font-size:.65rem!important'>Texto:</span>", unsafe_allow_html=True)
        with cols[2]:
            if st.button("A−", key="acc_dec", help="Diminuir tamanho do texto"):
                ordem = ['pequena','normal','grande','muito_grande']
                idx = ordem.index(st.session_state['acc_font_size'])
                if idx > 0:
                    st.session_state['acc_font_size'] = ordem[idx-1]
                    st.rerun()
        with cols[3]:
            if st.button("A", key="acc_rst", help="Tamanho padrão do texto"):
                st.session_state['acc_font_size'] = 'normal'
                st.rerun()
        with cols[4]:
            if st.button("A+", key="acc_inc", help="Aumentar tamanho do texto"):
                ordem = ['pequena','normal','grande','muito_grande']
                idx = ordem.index(st.session_state['acc_font_size'])
                if idx < len(ordem)-1:
                    st.session_state['acc_font_size'] = ordem[idx+1]
                    st.rerun()

        with cols[5]:
            st.markdown("<div class='acc-sep'></div>", unsafe_allow_html=True)

        with cols[6]:
            lbl = "☀️ Claro" if st.session_state['acc_theme']=='dark' else "🌙 Escuro"
            if st.button(lbl, key="acc_theme_btn", help="Alternar entre tema claro e escuro"):
                st.session_state['acc_theme'] = 'light' if st.session_state['acc_theme']=='dark' else 'dark'
                st.rerun()
        with cols[7]:
            hc_lbl = "🔲 Contraste: ON" if st.session_state['acc_high_contrast'] else "🔳 Alto Contraste"
            if st.button(hc_lbl, key="acc_hc_btn", help="Ativar modo de alto contraste"):
                st.session_state['acc_high_contrast'] = not st.session_state['acc_high_contrast']
                if st.session_state['acc_high_contrast']:
                    st.session_state['acc_theme'] = 'dark'
                st.rerun()

        with cols[8]:
            st.markdown("<div class='acc-sep'></div>", unsafe_allow_html=True)

        with cols[9]:
            dy_lbl = "🔤 Dislexia: ON" if st.session_state['acc_dyslexia'] else "🔤 Fonte Dislexia"
            if st.button(dy_lbl, key="acc_dy_btn", help="Ativar fonte OpenDyslexic"):
                st.session_state['acc_dyslexia'] = not st.session_state['acc_dyslexia']
                st.rerun()

        with cols[10]:
            if st.button("❓ Ajuda", key="acc_help_btn", help="Abrir guia de acessibilidade"):
                st.session_state['show_acc_help'] = not st.session_state.get('show_acc_help', False)
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

    # Modal de ajuda de acessibilidade
    if st.session_state.get('show_acc_help', False):
        st.markdown("""
<div class='glass-card' style='margin-top:160px;z-index:9998;position:relative'
     role='dialog' aria-modal='true' aria-label='Guia de Acessibilidade'>
<h2 style='margin-bottom:1.2rem'>♿ Guia de Acessibilidade</h2>
<div style='display:grid;grid-template-columns:1fr 1fr;gap:1rem'>
<div class='sc sc-b'>
  <strong>Tamanho do Texto</strong><br>
  <span style='opacity:.8;font-size:.85rem'>Use os botões A−, A e A+ para ajustar o tamanho das letras em toda a plataforma.</span>
</div>
<div class='sc sc-g'>
  <strong>Tema Claro / Escuro</strong><br>
  <span style='opacity:.8;font-size:.85rem'>Alterne entre fundo escuro (padrão) e fundo claro para maior conforto visual.</span>
</div>
<div class='sc sc-p'>
  <strong>Alto Contraste</strong><br>
  <span style='opacity:.8;font-size:.85rem'>Ativa fundo preto com texto branco de alto contraste, ideal para baixa visão.</span>
</div>
<div class='sc sc-a'>
  <strong>Fonte para Dislexia</strong><br>
  <span style='opacity:.8;font-size:.85rem'>Ativa a fonte OpenDyslexic, projetada para facilitar a leitura para pessoas com dislexia.</span>
</div>
<div class='sc sc-b' style='grid-column:span 2'>
  <strong>Audiodescrição das Obras</strong><br>
  <span style='opacity:.8;font-size:.85rem'>Em cada obra de arte, clique em "🔊 Ouvir Descrição" para ouvir uma descrição detalhada da imagem em voz alta usando síntese de voz do navegador. A descrição cobre composição, cores, personagens e contexto histórico da obra.</span>
</div>
<div class='sc sc-g' style='grid-column:span 2'>
  <strong>Navegação por Teclado</strong><br>
  <span style='opacity:.8;font-size:.85rem'>Use Tab para navegar entre elementos interativos, Enter/Espaço para ativar botões e Esc para fechar painéis. O link "Pular para o conteúdo" no topo evita repetir a navegação pela barra de acessibilidade.</span>
</div>
</div>
</div>""", unsafe_allow_html=True)
        if st.button("✕ Fechar guia", key="close_acc_help"):
            st.session_state['show_acc_help'] = False
            st.rerun()
        return  # Não renderiza mais nada enquanto o modal está aberto


def tts_button(text, key, label="🔊 Ouvir Descrição", aria_label="Reproduzir audiodescrição"):
    """Botão que dispara síntese de voz via Web Speech API."""
    safe = text.replace("'", "\\'").replace("\n", " ").replace('"', '\\"')
    button_id = f"tts_{key}"
    st.markdown(f"""
<div style='margin:.4rem 0'>
  <button
    id='{button_id}'
    onclick="
      if(window._ttsUtterance){{ window.speechSynthesis.cancel(); }}
      var u = new SpeechSynthesisUtterance('{safe}');
      u.lang = 'pt-BR'; u.rate = 0.92; u.pitch = 1.05;
      window._ttsUtterance = u;
      var btn = document.getElementById('{button_id}');
      btn.textContent = '⏹ Parar';
      u.onend = function(){{ btn.textContent = '{label}'; }};
      u.onerror = function(){{ btn.textContent = '{label}'; }};
      window.speechSynthesis.speak(u);
    "
    aria-label="{aria_label}"
    style="
      background:rgba(96,165,250,.25);
      border:1px solid rgba(96,165,250,.5);
      color:#dbeafe; border-radius:50px;
      padding:.5rem 1.3rem; cursor:pointer;
      font-weight:700; font-size:.85rem;
      transition:all .3s; font-family:inherit;
      display:inline-flex; align-items:center; gap:.5rem;
    "
    onmouseover="this.style.background='rgba(96,165,250,.4)'"
    onmouseout="this.style.background='rgba(96,165,250,.25)'"
  >{label}</button>
</div>""", unsafe_allow_html=True)


# ── CSS ───────────────────────────────────────────────────────────────
def load_css():
    # O CSS dinâmico é gerado pela barra de acessibilidade
    pass

# ── HELPERS ───────────────────────────────────────────────────────────
def kpi(label, value, sub="", color="#a7e6ff"):
    return (f"<div class='kpi-card'>"
            f"<div class='kpi-lbl'>{label}</div>"
            f"<div class='kpi-val' style='color:{color}'>{value}</div>"
            f"{'<div class=kpi-sub>'+sub+'</div>' if sub else ''}"
            f"</div>")

def insight(text):
    return f"<div class='insight'>{text}</div>"

def divider():
    return "<div class='divider'></div>"

def pbar(pct, color="#60a5fa"):
    w = min(100, max(0, pct*100))
    return f"<div class='pbar-o'><div class='pbar-i' style='width:{w:.1f}%;background:{color}'></div></div>"

def audio_desc_box(descricao, obra_id):
    """Caixa de audiodescrição com botão TTS."""
    st.markdown(f"""
<div class='audio-desc-wrap' role='region' aria-label='Audiodescrição da obra'>
  <div class='audio-desc-title'>🎧 Audiodescrição</div>
  <div class='audio-desc-text'>{descricao}</div>
</div>""", unsafe_allow_html=True)
    tts_button(descricao, key=f"obra_{obra_id}", label="🔊 Ouvir Descrição",
               aria_label=f"Reproduzir audiodescrição da obra {obra_id}")

# ── DADOS ─────────────────────────────────────────────────────────────
def check_admin():
    admins = load_json_file(ADMIN_FILE, [])
    if not admins:
        hashed = hashlib.sha256(ADMIN_PASSWORD.encode()).hexdigest()
        save_json_file(ADMIN_FILE, [{"id":1,"username":ADMIN_USERNAME,"password":hashed}])

def gen_uid():
    return base64.b64encode(os.urandom(12)).decode('ascii')

@st.cache_data(ttl=5, show_spinner=False)
def load_obras():
    default = [
        {"id":1,"titulo":"Guernica","artista":"Pablo Picasso","ano":"1937",
         "imagem":"https://upload.wikimedia.org/wikipedia/en/7/74/PicassoGuernica.jpg",
         "descricao": OBRAS_DESCRICOES[1]},
        {"id":2,"titulo":"A Noite Estrelada","artista":"Vincent van Gogh","ano":"1889",
         "imagem":"https://upload.wikimedia.org/wikipedia/commons/thumb/e/ea/Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg/1200px-Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg",
         "descricao": OBRAS_DESCRICOES[2]},
        {"id":3,"titulo":"Mona Lisa","artista":"Leonardo da Vinci","ano":"1503",
         "imagem":"https://upload.wikimedia.org/wikipedia/commons/thumb/e/ec/Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_retouched.jpg/800px-Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_retouched.jpg",
         "descricao": OBRAS_DESCRICOES[3]}
    ]
    obras = load_json_file(OBRAS_FILE, default)
    if not obras:
        save_json_file(OBRAS_FILE, default)
        return default
    # Garante campo descricao nas obras existentes
    for o in obras:
        if 'descricao' not in o or not o['descricao']:
            o['descricao'] = OBRAS_DESCRICOES.get(o['id'], f"Obra intitulada {o.get('titulo','sem título')}, de autoria de {o.get('artista','artista desconhecido')}, criada em {o.get('ano','ano desconhecido')}.")
    return obras

def save_answers(uid, animal, answers):
    users = load_json_file(USERS_FILE, [])
    users.append({"user_id":uid,"animal_name":animal,
                  "timestamp":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),**answers})
    return save_json_file(USERS_FILE, users)

def save_tag(uid, obra_id, tag):
    tags = load_json_file(TAGS_FILE, [])
    tags.append({"id":len(tags)+1,"user_id":uid,"obra_id":obra_id,
                 "tag":tag.lower().strip(),
                 "timestamp":datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
    st.cache_data.clear()
    return save_json_file(TAGS_FILE, tags)

def get_user_tags(uid):
    tags = load_json_file(TAGS_FILE, [])
    ut = [t for t in tags if t['user_id']==uid]
    return pd.DataFrame(ut) if ut else pd.DataFrame()

def get_obra_user_tags(obra_id, uid):
    tags = load_json_file(TAGS_FILE, [])
    f = [t for t in tags if t['obra_id']==obra_id and t['user_id']==uid]
    if f:
        df = pd.DataFrame(f)
        c  = df['tag'].value_counts().reset_index()
        c.columns = ["tag","count"]
        return c
    return pd.DataFrame(columns=["tag","count"])

def check_login(username, password):
    h = hashlib.sha256(password.encode()).hexdigest()
    return username==ADMIN_USERNAME and h==hashlib.sha256(ADMIN_PASSWORD.encode()).hexdigest()

def all_tags():
    t = load_json_file(TAGS_FILE, [])
    return pd.DataFrame(t) if t else pd.DataFrame()

def all_users():
    u = load_json_file(USERS_FILE, [])
    return pd.DataFrame(u) if u else pd.DataFrame()

# ── EXPORTAÇÃO ────────────────────────────────────────────────────────
def html_quest(uid, animal, users_df):
    if users_df.empty: return None
    ud = users_df[users_df['user_id']==uid]
    if ud.empty: return None
    ui = ud.iloc[0]
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<style>*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:sans-serif;background:linear-gradient(135deg,#000,#001F3F);padding:40px;color:white}}
.c{{max-width:900px;margin:0 auto;background:rgba(255,255,255,.15);padding:50px;border-radius:24px;border:1px solid rgba(255,255,255,.3)}}
h1{{text-align:center;margin-bottom:15px;font-size:2.2rem}}
.hi{{text-align:center;margin-bottom:35px;opacity:.9}}
.ab{{background:rgba(167,230,255,.25);border:1px solid rgba(167,230,255,.5);color:#a7e6ff;
  padding:.3rem 1rem;border-radius:50px;font-weight:700;display:inline-block}}
.qb{{margin:22px 0;padding:18px 22px;background:rgba(255,255,255,.1);
  border-left:4px solid rgba(255,255,255,.5);border-radius:12px}}
.q{{font-weight:700;margin-bottom:8px}}.a{{line-height:1.7;opacity:.92}}
.ft{{text-align:center;margin-top:40px;padding-top:18px;
  border-top:1px solid rgba(255,255,255,.2);opacity:.65;font-size:.88rem}}</style></head>
<body><div class="c"><h1>Respostas do Questionário</h1>
<div class="hi">
  <p>Usuário Anônimo: <span class="ab">🐾 {animal}</span></p>
  <p style="margin-top:6px;opacity:.65">Data: {ui.get('timestamp','N/A')}</p>
</div>
<div class="qb"><div class="q">1. Nível de familiaridade com museus</div>
<div class="a">{ui.get('q1','N/A')}</div></div>
<div class="qb"><div class="q">2. Conhecimento sobre documentação museológica</div>
<div class="a">{ui.get('q2','N/A')}</div></div>
<div class="qb"><div class="q">3. O que você entende por 'tags'?</div>
<div class="a">{ui.get('q3','N/A')}</div></div>
<div class="ft">Sistema Folksonomia Digital — Ctrl+P → Salvar como PDF</div>
</div></body></html>"""

def html_tags(uid, animal, obras, tags_df):
    ut = tags_df[tags_df['user_id']==uid] if not tags_df.empty else pd.DataFrame()
    if ut.empty: return None
    od = {o['id']:o for o in obras}
    rows = "".join(
        f"<tr><td>{i+1}</td>"
        f"<td>{od.get(r['obra_id'],{}).get('titulo','Obra '+str(r['obra_id']))}</td>"
        f"<td><span style='background:rgba(255,255,255,.22);padding:3px 10px;border-radius:50px'>{r['tag']}</span></td>"
        f"<td>{r['timestamp']}</td></tr>"
        for i,(_,r) in enumerate(ut.iterrows())
    )
    top = "".join(
        f"<tr><td>{i}</td><td>{t}</td><td>{c}</td></tr>"
        for i,(t,c) in enumerate(ut['tag'].value_counts().head(10).items(),1)
    )
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<style>*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:sans-serif;background:linear-gradient(135deg,#000,#001F3F);padding:40px;color:white}}
.c{{max-width:1100px;margin:0 auto;background:rgba(255,255,255,.15);padding:50px;border-radius:24px;border:1px solid rgba(255,255,255,.3)}}
h1{{text-align:center;margin-bottom:15px;font-size:2.2rem}}
.hi{{text-align:center;margin-bottom:28px;opacity:.9}}
.ab{{background:rgba(167,230,255,.25);border:1px solid rgba(167,230,255,.5);color:#a7e6ff;
  padding:.3rem 1rem;border-radius:50px;font-weight:700;display:inline-block}}
.stats{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin:22px 0}}
.sb{{background:rgba(255,255,255,.14);border:1px solid rgba(255,255,255,.28);
  padding:18px;border-radius:12px;text-align:center}}
.sv{{font-size:2.6rem;font-weight:800}}.sl{{font-size:.82rem;text-transform:uppercase;
  letter-spacing:1.5px;margin-top:7px;opacity:.85}}
table{{width:100%;border-collapse:collapse;margin:18px 0}}
th,td{{padding:13px;text-align:left;border-bottom:1px solid rgba(255,255,255,.14)}}
th{{background:rgba(255,255,255,.18);font-weight:700;text-transform:uppercase;font-size:.82rem}}
tr:nth-child(even){{background:rgba(255,255,255,.04)}}
.ft{{text-align:center;margin-top:38px;padding-top:18px;
  border-top:1px solid rgba(255,255,255,.2);opacity:.65;font-size:.88rem}}</style></head>
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

# ── INTERFACE PRINCIPAL ───────────────────────────────────────────────
def show_header():
    st.markdown(
        "<div class='top-navbar' role='banner'>"
        "<div class='navbar-logo'>📚 Sistema Folksonomia Digital</div>"
        "<div style='font-size:.8rem;opacity:.6'>Catalogação Colaborativa de Arte</div>"
        "</div>", unsafe_allow_html=True)

def main():
    # Inicializar acessibilidade antes de qualquer coisa
    get_accessibility_settings()

    # Renderizar barra de acessibilidade (inclui o CSS dinâmico)
    render_accessibility_bar()

    # Se o modal de ajuda estiver aberto, parar aqui
    if st.session_state.get('show_acc_help', False):
        return

    try: check_admin()
    except Exception as e: st.error(f"Erro ao inicializar: {e}")

    for k,v in [('user_id',gen_uid()),('animal_name',generate_animal_name()),
                ('step','intro'),('answers',{})]:
        if k not in st.session_state: st.session_state[k] = v

    if st.session_state['step'] != 'completed':
        show_intro()
    else:
        show_header()
        st.markdown("<div class='main-content' id='conteudo-principal' role='main'>", unsafe_allow_html=True)
        t1, t2 = st.tabs(["📖 Explorar Obras", "🔧 Área Administrativa"])
        with t1: show_obras()
        with t2: show_admin()
        st.markdown("</div>", unsafe_allow_html=True)

# ── INTRO ─────────────────────────────────────────────────────────────
def show_intro():
    st.markdown("<div class='main-content' id='conteudo-principal'>", unsafe_allow_html=True)
    st.markdown("<h1 class='main-title'>Sistema Folksonomia Digital</h1>", unsafe_allow_html=True)
    st.markdown("<p class='subtitle'>Sistema colaborativo de catalogação de obras de arte<br>"
                "Complete o questionário para acessar a plataforma</p>", unsafe_allow_html=True)
    st.markdown("<div class='glass-card' role='form' aria-label='Questionário de acesso'>", unsafe_allow_html=True)
    st.markdown("<h2 style='text-align:center;margin-bottom:2.2rem;font-size:1.7rem'>"
                "Questionário de Acesso</h2>", unsafe_allow_html=True)
    with st.form("intro_form"):
        c1, c2 = st.columns(2)
        with c1:
            q1 = st.selectbox("1. Qual é o seu nível de familiaridade com museus?",
                ["Nunca visito museus","Visito raramente","Visito ocasionalmente","Visito frequentemente"])
            q2 = st.selectbox("2. Você já ouviu falar sobre documentação museológica?",
                ["Nunca ouvi falar","Já ouvi, mas não sei o que é","Tenho uma ideia básica","Conheço bem o tema"])
        with c2:
            q3 = st.text_area("3. O que você entende por 'tags' ou etiquetas digitais aplicadas a acervo?",
                max_chars=500, height=200, placeholder="Descreva sua compreensão sobre o conceito...")
        _, cb, _ = st.columns([1,1,1])
        with cb:
            submit = st.form_submit_button("Acessar Plataforma", use_container_width=True)
        if submit:
            if not q3.strip():
                st.error("Por favor, responda todas as perguntas para continuar!")
            else:
                st.session_state['answers'] = {"q1":q1,"q2":q2,"q3":q3}
                save_answers(st.session_state['user_id'], st.session_state['animal_name'],
                             st.session_state['answers'])
                st.session_state['step'] = 'completed'
                st.success("Questionário completo! Acesso liberado.")
                st.balloons()
                st.rerun()
    st.markdown("</div></div>", unsafe_allow_html=True)

# ── GALERIA ───────────────────────────────────────────────────────────
def show_obras():
    st.markdown("<h1 class='main-title'>Galeria de Obras de Arte</h1>", unsafe_allow_html=True)
    st.markdown("<p class='subtitle'>Explore as obras, ouça as descrições e contribua com suas tags</p>",
                unsafe_allow_html=True)

    # Dica de acessibilidade
    st.markdown("""
<div class='insight' role='note' aria-label='Dica de acessibilidade'>
  <strong>♿ Acessibilidade:</strong> Cada obra possui um botão
  <strong>🔊 Ouvir Descrição</strong> que narra a imagem em voz alta.
  Use os controles de acessibilidade no topo para ajustar o tamanho do texto e o tema.
</div>""", unsafe_allow_html=True)

    obras = load_obras()
    if not obras:
        st.info("Nenhuma obra cadastrada.")
        return

    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    c1, c2 = st.columns([2,1])
    with c1:
        sid = st.text_input("Filtrar por número da obra:", "", placeholder="Ex: 1, 2, 3…",
                            help="Digite o número da obra para filtrar")
    with c2:
        sord = st.selectbox("Ordenar por:", ["Número (crescente)","Número (decrescente)"])
    st.markdown("</div>", unsafe_allow_html=True)

    filtered = obras
    if sid.strip().isdigit():
        filtered = [o for o in obras if str(o['id'])==sid.strip()]
    filtered = sorted(filtered, key=lambda x: x['id'], reverse=(sord=="Número (decrescente)"))

    st.markdown(f"<div style='text-align:center;margin:1.8rem 0;font-size:1.1rem;font-weight:600'>"
                f"Exibindo <strong style='font-size:1.4rem'>{len(filtered)}</strong> obra(s)</div>",
                unsafe_allow_html=True)

    cols = st.columns(3)
    for i, obra in enumerate(filtered):
        with cols[i%3]:
            desc = obra.get('descricao', f"Obra {obra.get

