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
    "Aguia","Boto","Capivara","Doninha","Ema","Falcao","Gaviao","Harpia","Irara","Jaguar",
    "Lontra","Mico","Onca","Paca","Quati","Raposa","Tamandua","Urubu","Veado","Zorrilho",
    "Arara","Bugio","Caititu","Jaguatirica","Lobo","Mutum","Pirarucu","Tucano","Sucuri","Tatu"
]
ADJETIVOS = [
    "Azul","Bravo","Calmo","Dourado","Esperto","Feroz","Gracioso","Intenso","Jovial","Lento",
    "Magico","Nobre","Ousado","Preciso","Rapido","Sabio","Timido","Unico","Valente","Zeloso",
    "Curioso","Furtivo","Altivo","Sereno","Vibrante","Audaz","Brilhante","Corajoso","Distinto","Elegante"
]

OBRAS_DESC = {
    1: (
        "Guernica, de Pablo Picasso, pintada em 1937. "
        "Oleo sobre tela em preto, branco e tons de cinza. "
        "Retrata o bombardeio da cidade basca de Guernica durante a Guerra Civil Espanhola. "
        "Figuras humanas e animais em agonia preenchem a composicao: "
        "uma mae segura um bebe morto no canto esquerdo, um touro impassivel ao fundo, "
        "um cavalo ferido no centro com a cabeca erguida em desespero, "
        "soldados caidos e fragmentados, e chamas a direita. "
        "A composicao e caotica e angustiante, com formas cubistas sobrepostas "
        "que expressam o horror da guerra sem perspectiva convencional."
    ),
    2: (
        "A Noite Estrelada, de Vincent van Gogh, pintada em 1889. "
        "Oleo sobre tela de estilo pos-impressionista. "
        "Representa o ceu noturno sobre Saint-Remy-de-Provence "
        "visto da janela do asilo onde o artista estava internado. "
        "O ceu e dominado por redemoinhos espirais em azuis profundos e amarelos luminosos, "
        "com uma lua crescente brilhante no canto superior direito "
        "e estrelas grandes e radiantes espalhadas pela composicao. "
        "Na base, uma aldeia tranquila com uma igreja de torre alta ao centro "
        "e ciprestes escuros em primeiro plano a esquerda."
    ),
    3: (
        "Mona Lisa, de Leonardo da Vinci, pintada por volta de 1503. "
        "Pintura a oleo sobre madeira de alamo. "
        "Retrato de uma mulher de expressao enigmatica e sorriso sutil e ambiguo, "
        "identificada como Lisa Gherardini, esposa de um comerciante florentino. "
        "O fundo revela paisagem montanhosa e aquatica esmaecida pela tecnica sfumato, "
        "que cria transicoes suaves entre luz e sombra sem contornos definidos. "
        "A mulher veste roupas renascentistas escuras, cabelos soltos sob veu translucido "
        "e maos sobrepostas no colo. Seus olhos parecem acompanhar o observador "
        "de qualquer angulo de visao."
    ),
}


def generate_animal_name():
    random.seed()
    return "{} {}".format(random.choice(ANIMAIS), random.choice(ADJETIVOS))


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
        st.error("Erro ao salvar {}: {}".format(filepath, e))
        return False


# ── SIMILARIDADE ──────────────────────────────────────────────────────
def ntag(tag):
    return tag.lower().strip()


def words(tag):
    return set(ntag(tag).split())


def ngrams(text, n=3):
    t = ntag(text)
    if len(t) < n:
        return set([t])
    return set(t[i:i+n] for i in range(len(t) - n + 1))


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
        nj = len(ng1 & ng2) / len(ng1 | ng2) if ng1 | ng2 else 0
        if nj > 0:
            wj = len(w1 & w2) / len(w1 | w2) if w1 | w2 else 0
            return 0.6 * nj + 0.4 * wj
    return 0.0


def tag_connections(tags_list, threshold=0.35):
    uniq = list(set(ntag(t) for t in tags_list))
    conns = []
    for i in range(len(uniq)):
        for j in range(i + 1, len(uniq)):
            s = sim(uniq[i], uniq[j])
            if s >= threshold:
                w1, w2 = words(uniq[i]), words(uniq[j])
                shared = w1 & w2
                if uniq[i] in uniq[j] or uniq[j] in uniq[i]:
                    tipo = "Contencao"
                elif shared:
                    tipo = "Palavra comum: '{}'".format(', '.join(shared))
                else:
                    tipo = "Similaridade fonetica"
                conns.append({
                    "tag_a": uniq[i], "tag_b": uniq[j],
                    "similaridade": round(s, 3), "tipo": tipo
                })
    conns.sort(key=lambda x: x["similaridade"], reverse=True)
    return conns


def tag_clusters(tags_list, threshold=0.35):
    uniq  = list(set(ntag(t) for t in tags_list))
    conns = tag_connections(uniq, threshold)
    par   = {t: t for t in uniq}

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


# ── ACESSIBILIDADE ────────────────────────────────────────────────────
def init_acc():
    defaults = {
        'acc_font': 'normal',
        'acc_theme': 'dark',
        'acc_hc': False,
        'acc_dyslexia': False,
        'acc_help': False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def build_css():
    init_acc()
    theme    = st.session_state['acc_theme']
    hc       = st.session_state['acc_hc']
    dyslexia = st.session_state['acc_dyslexia']
    font_sz  = st.session_state['acc_font']

    fs_map = {'pequena': '0.82rem', 'normal': '1rem', 'grande': '1.18rem', 'muito_grande': '1.38rem'}
    fs = fs_map.get(font_sz, '1rem')
    ff = "'OpenDyslexic','Poppins',sans-serif" if dyslexia else "'Poppins',sans-serif"

    if hc:
        p = dict(
            body_bg="#000", body_anim="none",
            card_bg="#111", card_brd="#fff",
            text="#fff", text2="#ffff00",
            inp_bg="#0a0a0a", inp_brd="#fff",
            nav_bg="#000", nav_brd="#fff",
            tab_bg="#1a1a1a", tab_sel="#333",
            btn_bg="#222", btn_hov="#444",
            kpi_bg="#111", sc_bg="#0d0d0d",
            acc_bg="#000", acc_brd="#fff",
            bdg_bg="#222", tag_col="#fff",
            logo="linear-gradient(135deg,#fff 0%,#ccc 100%)",
        )
    elif theme == 'light':
        p = dict(
            body_bg="linear-gradient(-45deg,#e8f4f8,#f0e8ff,#e8f0ff,#f8f0e8,#e8f4f8)",
            body_anim="bg 15s ease infinite",
            card_bg="rgba(255,255,255,0.88)", card_brd="rgba(0,0,0,0.14)",
            text="#1a1a2e", text2="rgba(0,0,0,0.55)",
            inp_bg="rgba(255,255,255,0.95)", inp_brd="rgba(0,0,0,0.22)",
            nav_bg="rgba(255,255,255,0.88)", nav_brd="rgba(0,0,0,0.10)",
            tab_bg="rgba(0,0,0,0.06)", tab_sel="rgba(0,0,0,0.16)",
            btn_bg="rgba(0,0,0,0.10)", btn_hov="rgba(0,0,0,0.20)",
            kpi_bg="rgba(255,255,255,0.75)", sc_bg="rgba(0,0,0,0.04)",
            acc_bg="rgba(255,255,255,0.96)", acc_brd="rgba(0,0,0,0.12)",
            bdg_bg="rgba(0,0,0,0.09)", tag_col="#1a1a2e",
            logo="linear-gradient(135deg,#0050a0,#6030a0)",
        )
    else:
        p = dict(
            body_bg="linear-gradient(-45deg,#000,#001F3F,#000,#001F3F,#000)",
            body_anim="bg 15s ease infinite",
            card_bg="rgba(255,255,255,0.15)", card_brd="rgba(255,255,255,0.30)",
            text="#e0e0e0", text2="rgba(255,255,255,0.65)",
            inp_bg="rgba(255,255,255,0.18)", inp_brd="rgba(255,255,255,0.28)",
            nav_bg="rgba(255,255,255,0.10)", nav_brd="rgba(255,255,255,0.20)",
            tab_bg="rgba(255,255,255,0.10)", tab_sel="rgba(255,255,255,0.33)",
            btn_bg="rgba(255,255,255,0.25)", btn_hov="rgba(255,255,255,0.40)",
            kpi_bg="rgba(255,255,255,0.16)", sc_bg="rgba(255,255,255,0.07)",
            acc_bg="rgba(255,255,255,0.08)", acc_brd="rgba(255,255,255,0.20)",
            bdg_bg="rgba(255,255,255,0.25)", tag_col="white",
            logo="linear-gradient(135deg,#a7e6ff,#d1baff)",
        )

    css = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800&display=swap');
@font-face {{
  font-family:'OpenDyslexic';
  src:url('https://cdn.jsdelivr.net/npm/opendyslexic@0.91.12/dist/OpenDyslexic-Regular.otf');
}}
@keyframes bg {{
  0%{{background-position:0% 50%}}
  50%{{background-position:100% 50%}}
  100%{{background-position:0% 50%}}
}}
*,*::before,*::after{{margin:0;padding:0;box-sizing:border-box;font-family:{ff}!important}}
html{{font-size:{fs}}}
.stApp{{
  background:{body_bg};background-size:400% 400%;
  animation:{body_anim};color:{text}
}}
/* ── BARRA ACESSIBILIDADE ── */
.acc-bar{{
  position:fixed;top:0;left:0;right:0;z-index:10001;
  background:{acc_bg};backdrop-filter:blur(20px) saturate(180%);
  border-bottom:1px solid {acc_brd};
  padding:.35rem 1.5rem;min-height:44px;
  display:flex;align-items:center;gap:.55rem;flex-wrap:wrap;
}}
.acc-label{{
  color:{text};font-size:.68rem!important;font-weight:700;
  text-transform:uppercase;letter-spacing:1.4px;opacity:.85;white-space:nowrap;
}}
.acc-sep{{width:1px;height:20px;background:{acc_brd};margin:0 .2rem;flex-shrink:0}}
/* ── NAVBAR ── */
.top-navbar{{
  position:fixed;top:44px;left:0;right:0;z-index:9999;
  background:{nav_bg};backdrop-filter:blur(20px) saturate(180%);
  border-bottom:1px solid {nav_brd};
  padding:1rem 3rem;
  display:flex;justify-content:space-between;align-items:center;
  box-shadow:0 8px 32px rgba(0,0,0,.12);
}}
.navbar-logo{{
  font-size:1.6rem;font-weight:800;
  background:{logo};-webkit-background-clip:text;
  -webkit-text-fill-color:transparent;background-clip:text;letter-spacing:-1px;
}}
/* ── CONTEUDO ── */
.main-content{{
  margin-top:158px;padding:2rem 3rem;
  max-width:1600px;margin-left:auto;margin-right:auto;
}}
/* ── GLASS CARD ── */
.glass-card{{
  background:{card_bg};backdrop-filter:blur(20px) saturate(180%);
  border:1px solid {card_brd};border-radius:24px;padding:2.5rem;margin:1.5rem 0;
  box-shadow:0 8px 32px rgba(0,0,0,.1);
  transition:all .4s cubic-bezier(.4,0,.2,1);position:relative;overflow:hidden;
}}
.glass-card::before{{
  content:'';position:absolute;top:0;left:-100%;width:100%;height:100%;
  background:linear-gradient(90deg,transparent,rgba(255,255,255,.1),transparent);
  transition:left .5s;
}}
.glass-card:hover::before{{left:100%}}
.glass-card:hover{{transform:translateY(-6px) scale(1.01);box-shadow:0 16px 48px rgba(0,0,0,.2)}}
/* ── OBRA CARD ── */
.obra-card{{
  background:{card_bg};backdrop-filter:blur(15px) saturate(180%);
  border:1px solid {card_brd};border-radius:20px;overflow:hidden;
  transition:all .4s cubic-bezier(.4,0,.2,1);position:relative;
}}
.obra-card:hover{{transform:translateY(-10px) scale(1.02);box-shadow:0 20px 60px rgba(0,31,63,.4)}}
.obra-card img{{width:100%;height:280px;object-fit:cover;transition:transform .6s cubic-bezier(.4,0,.2,1)}}
.obra-card:hover img{{transform:scale(1.1)}}
/* ── TIPOGRAFIA ── */
.main-title{{
  color:{text};font-size:2.9rem;font-weight:800;text-align:center;
  margin:2rem 0 1rem;letter-spacing:-2px;text-shadow:0 4px 20px rgba(0,0,0,.3);
}}
.subtitle{{color:{text2};font-size:1.1rem;text-align:center;margin-bottom:2.5rem;line-height:1.8;font-weight:300}}
h1,h2,h3,h4,h5,h6{{color:{text}!important;font-weight:700!important;text-shadow:0 2px 15px rgba(0,0,0,.3)}}
/* ── BADGES ── */
.tag-badge{{
  display:inline-block;background:{bdg_bg};backdrop-filter:blur(10px);
  border:1px solid {card_brd};color:{tag_col};padding:.45rem 1rem;
  border-radius:50px;margin:.3rem;font-size:.84rem;font-weight:600;transition:all .3s;
}}
.tag-badge:hover{{transform:translateY(-3px) scale(1.05)}}
.tag-green{{background:rgba(34,197,94,.25)!important;border-color:rgba(34,197,94,.5)!important;color:#dcfce7!important}}
.tag-amber{{background:rgba(245,158,11,.25)!important;border-color:rgba(245,158,11,.5)!important;color:#fef3c7!important}}
.tag-blue{{background:rgba(96,165,250,.25)!important;border-color:rgba(96,165,250,.5)!important;color:#dbeafe!important}}
.animal-badge{{
  display:inline-block;background:rgba(167,230,255,.2);border:1px solid rgba(167,230,255,.45);
  color:#a7e6ff;padding:.35rem 1rem;border-radius:50px;font-size:.84rem;font-weight:700;
}}
/* ── KPI ── */
.kpi-card{{
  background:{kpi_bg};backdrop-filter:blur(20px) saturate(180%);
  border:1px solid {card_brd};border-radius:18px;padding:1.5rem;
  text-align:center;color:{text};box-shadow:0 8px 32px rgba(0,0,0,.12);transition:all .4s;
}}
.kpi-card:hover{{transform:translateY(-6px) scale(1.04);box-shadow:0 16px 48px rgba(0,31,63,.28)}}
.kpi-val{{font-size:2.3rem;font-weight:800;margin:.6rem 0;text-shadow:0 4px 20px rgba(0,0,0,.2)}}
.kpi-lbl{{font-size:.73rem!important;text-transform:uppercase;letter-spacing:2px;font-weight:600;opacity:.8}}
.kpi-sub{{font-size:.67rem!important;opacity:.5;margin-top:.3rem}}
/* ── SECTION CARDS ── */
.sc{{background:{sc_bg};border:1px solid {card_brd};border-radius:14px;padding:1.2rem;margin:.6rem 0}}
.sc-b{{border-left:4px solid #60a5fa;background:rgba(96,165,250,.07)}}
.sc-g{{border-left:4px solid #34d399;background:rgba(52,211,153,.07)}}
.sc-p{{border-left:4px solid #a78bfa;background:rgba(167,139,250,.07)}}
.sc-a{{border-left:4px solid #fbbf24;background:rgba(251,191,36,.07)}}
/* ── INSIGHT ── */
.insight{{
  background:rgba(167,230,255,.09);border:1px solid rgba(167,230,255,.25);
  border-radius:12px;padding:.9rem 1.3rem;margin:.6rem 0;color:{text2};
  font-size:.87rem;line-height:1.7;
}}
.insight strong{{color:#a7e6ff}}
/* ── CONEXOES ── */
.conn-row{{
  display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;
  background:{sc_bg};border-radius:11px;padding:.8rem 1.2rem;margin:.3rem 0;
  border-left:3px solid {card_brd};transition:background .2s;
}}
.conn-row:hover{{background:rgba(255,255,255,.1)}}
/* ── CLUSTERS ── */
.cluster-wrap{{background:{sc_bg};border-radius:14px;padding:1rem 1.3rem;margin:.5rem 0;border:1px solid {card_brd}}}
.cluster-title{{font-size:.73rem!important;text-transform:uppercase;letter-spacing:1.5px;color:rgba(167,139,250,.8);margin-bottom:.5rem;font-weight:700}}
.cluster-pill{{
  display:inline-flex;align-items:center;gap:5px;background:rgba(168,85,247,.2);
  border:1px solid rgba(168,85,247,.38);border-radius:50px;padding:.3rem .8rem;
  margin:.2rem;font-size:.75rem!important;font-weight:600;color:#f3e8ff;
}}
/* ── PROGRESS ── */
.pbar-o{{background:rgba(255,255,255,.1);border-radius:50px;height:6px;margin:3px 0;overflow:hidden}}
.pbar-i{{height:100%;border-radius:50px;transition:width .5s}}
/* ── DIVIDER ── */
.divider{{height:1px;background:linear-gradient(90deg,transparent,{card_brd},transparent);margin:1.5rem 0}}
/* ── AUDIO DESC ── */
.audio-desc-box{{
  background:rgba(96,165,250,.09);border:1px solid rgba(96,165,250,.28);
  border-radius:14px;padding:.9rem 1.2rem;margin:.5rem 0;
}}
.audio-desc-title{{color:#a7e6ff;font-size:.72rem!important;font-weight:700;text-transform:uppercase;letter-spacing:1.4px;margin-bottom:.45rem}}
.audio-desc-text{{color:{text2};font-size:.85rem!important;line-height:1.7}}
/* ── SKIP LINK ── */
.skip-link{{
  position:absolute;top:-60px;left:0;background:#a7e6ff;color:#000;
  padding:.5rem .9rem;z-index:99999;font-weight:700;border-radius:0 0 8px 0;
  text-decoration:none;transition:top .2s;font-size:.83rem;
}}
.skip-link:focus{{top:0}}
*:focus-visible{{outline:3px solid #a7e6ff!important;outline-offset:2px!important;border-radius:4px}}
/* ── BOTOES ── */
.stButton button{{
  background:{btn_bg}!important;backdrop-filter:blur(15px)!important;
  color:{text}!important;border:1px solid {card_brd}!important;
  border-radius:50px!important;padding:.82rem 2rem!important;
  font-weight:700!important;font-size:.93rem!important;
  transition:all .4s!important;box-shadow:0 8px 25px rgba(0,0,0,.15)!important;
  letter-spacing:.4px;
}}
.stButton button:hover{{
  background:{btn_hov}!important;box-shadow:0 12px 40px rgba(0,31,63,.4)!important;
  transform:translateY(-3px) scale(1.04)!important;
}}
/* ── INPUTS ── */
.stTextInput input,.stTextArea textarea{{
  background:{inp_bg}!important;border:1px solid {inp_brd}!important;
  color:{text}!important;border-radius:14px!important;padding:.85rem!important;font-weight:500!important;
}}
.stTextInput input::placeholder,.stTextArea textarea::placeholder{{color:{text2}!important}}
.stTextInput input:focus,.stTextArea textarea:focus{{
  border-color:#a7e6ff!important;box-shadow:0 0 0 3px rgba(167,230,255,.18)!important;
}}
label{{color:{text}!important;font-weight:700!important}}
/* ── TABS ── */
.stTabs [data-baseweb="tab-list"]{{gap:.6rem;background:{tab_bg};backdrop-filter:blur(10px);padding:.4rem;border-radius:14px}}
.stTabs [data-baseweb="tab"]{{
  background:rgba(255,255,255,.12);border:1px solid {card_brd};
  border-radius:10px;color:{text};padding:.7rem 1.4rem;font-weight:700;transition:all .3s;
}}
.stTabs [data-baseweb="tab"]:hover{{background:rgba(255,255,255,.22);transform:translateY(-2px)}}
.stTabs [aria-selected="true"]{{background:{tab_sel}!important;border-color:{card_brd}!important;box-shadow:0 6px 20px rgba(0,31,63,.25)!important}}
/* ── ALERTAS ── */
.stAlert{{background:{card_bg}!important;backdrop-filter:blur(15px)!important;border-radius:14px!important;color:{text}!important}}
/* ── TABELAS ── */
.dataframe{{background:{card_bg}!important;border:1px solid {card_brd}!important;border-radius:14px!important;color:{text}!important}}
.dataframe th{{background:{tab_sel}!important;color:{text}!important;font-weight:700!important}}
.dataframe td{{color:{text}!important}}
/* ── MISC ── */
#MainMenu,footer,header{{visibility:hidden}}
.stDeployButton{{display:none}}
[data-testid="stSidebar"]{{display:none}}
div[data-testid="stTextInput"]>div{{background:transparent!important;border:none!important;box-shadow:none!important;padding:0!important}}
@media(max-width:768px){{
  .main-title{{font-size:1.9rem}}
  .main-content{{margin-top:180px;padding:1rem}}
  .acc-bar{{padding:.3rem .8rem;gap:.4rem}}
  .top-navbar{{padding:.8rem 1.2rem}}
}}
</style>
""".format(
        ff=ff, fs=fs,
        body_bg=p['body_bg'], body_anim=p['body_anim'],
        acc_bg=p['acc_bg'], acc_brd=p['acc_brd'],
        nav_bg=p['nav_bg'], nav_brd=p['nav_brd'],
        logo=p['logo'], text=p['text'], text2=p['text2'],
        card_bg=p['card_bg'], card_brd=p['card_brd'],
        inp_bg=p['inp_bg'], inp_brd=p['inp_brd'],
        tab_bg=p['tab_bg'], tab_sel=p['tab_sel'],
        btn_bg=p['btn_bg'], btn_hov=p['btn_hov'],
        kpi_bg=p['kpi_bg'], sc_bg=p['sc_bg'],
        bdg_bg=p['bdg_bg'], tag_col=p['tag_col'],
    )
    st.markdown(css, unsafe_allow_html=True)


def render_acc_bar():
    init_acc()
    st.markdown("<a class='skip-link' href='#main-content' tabindex='1'>Pular para o conteudo</a>",
                unsafe_allow_html=True)

    (c_lbl, c_tsz, c_dec, c_rst, c_inc,
     c_s1, c_theme, c_hc, c_s2, c_dy, c_help) = st.columns(
        [1.5, .45, .38, .38, .38, .15, .85, 1.1, .15, 1.05, .65]
    )
    with c_lbl:
        st.markdown("<span class='acc-label'>Acessibilidade</span>", unsafe_allow_html=True)
    with c_tsz:
        st.markdown("<span class='acc-label' style='font-size:.62rem!important'>Texto:</span>",
                    unsafe_allow_html=True)
    with c_dec:
        if st.button("A-", key="acc_dec", help="Diminuir texto"):
            ordem = ['pequena', 'normal', 'grande', 'muito_grande']
            idx = ordem.index(st.session_state['acc_font'])
            if idx > 0:
                st.session_state['acc_font'] = ordem[idx - 1]
            st.rerun()
    with c_rst:
        if st.button("A", key="acc_rst", help="Tamanho padrao"):
            st.session_state['acc_font'] = 'normal'
            st.rerun()
    with c_inc:
        if st.button("A+", key="acc_inc", help="Aumentar texto"):
            ordem = ['pequena', 'normal', 'grande', 'muito_grande']
            idx = ordem.index(st.session_state['acc_font'])
            if idx < len(ordem) - 1:
                st.session_state['acc_font'] = ordem[idx + 1]
            st.rerun()
    with c_s1:
        st.markdown("<div class='acc-sep'></div>", unsafe_allow_html=True)
    with c_theme:
        lbl = "Claro" if st.session_state['acc_theme'] == 'dark' else "Escuro"
        if st.button(lbl, key="acc_theme_btn", help="Alternar tema"):
            st.session_state['acc_theme'] = ('light' if st.session_state['acc_theme'] == 'dark' else 'dark')
            st.rerun()
    with c_hc:
        lbl_hc = "Contraste ON" if st.session_state['acc_hc'] else "Alto Contraste"
        if st.button(lbl_hc, key="acc_hc_btn", help="Modo alto contraste"):
            st.session_state['acc_hc'] = not st.session_state['acc_hc']
            if st.session_state['acc_hc']:
                st.session_state['acc_theme'] = 'dark'
            st.rerun()
    with c_s2:
        st.markdown("<div class='acc-sep'></div>", unsafe_allow_html=True)
    with c_dy:
        lbl_dy = "Dislexia ON" if st.session_state['acc_dyslexia'] else "Fonte Dislexia"
        if st.button(lbl_dy, key="acc_dy_btn", help="Fonte OpenDyslexic"):
            st.session_state['acc_dyslexia'] = not st.session_state['acc_dyslexia']
            st.rerun()
    with c_help:
        if st.button("Ajuda", key="acc_help_btn", help="Guia de acessibilidade"):
            st.session_state['acc_help'] = not st.session_state.get('acc_help', False)
            st.rerun()


def render_acc_help():
    st.markdown("""
<div class='glass-card' style='margin-top:158px' role='dialog' aria-modal='true'>
<h2 style='text-align:center;margin-bottom:1.5rem'>Guia de Acessibilidade</h2>
<div style='display:grid;grid-template-columns:1fr 1fr;gap:1rem'>
  <div class='sc sc-b'>
    <strong>Tamanho do Texto</strong><br>
    <span style='opacity:.8;font-size:.85rem'>
      Use A-, A e A+ na barra superior para ajustar o tamanho das letras em toda a plataforma.
      Quatro niveis disponiveis.
    </span>
  </div>
  <div class='sc sc-g'>
    <strong>Tema Claro e Escuro</strong><br>
    <span style='opacity:.8;font-size:.85rem'>
      Alterne entre fundo escuro (padrao) e fundo claro para maior conforto visual
      em diferentes condicoes de iluminacao.
    </span>
  </div>
  <div class='sc sc-p'>
    <strong>Alto Contraste</strong><br>
    <span style='opacity:.8;font-size:.85rem'>
      Fundo preto com texto branco de maximo contraste.
      Ideal para pessoas com baixa visao ou sensibilidade ao brilho da tela.
    </span>
  </div>
  <div class='sc sc-a'>
    <strong>Fonte para Dislexia</strong><br>
    <span style='opacity:.8;font-size:.85rem'>
      Ativa a fonte OpenDyslexic, projetada para facilitar
      a leitura para pessoas com dislexia.
    </span>
  </div>
  <div class='sc sc-b' style='grid-column:span 2'>
    <strong>Audiodescricao das Obras</strong><br>
    <span style='opacity:.8;font-size:.85rem'>
      Cada obra na galeria possui um botao "Ouvir Descricao".
      Ao clicar, uma voz em portugues brasileiro narra detalhes da imagem:
      composicao, cores, personagens e contexto historico.
      Clique novamente para interromper a naracao a qualquer momento.
    </span>
  </div>
  <div class='sc sc-g' style='grid-column:span 2'>
    <strong>Navegacao por Teclado</strong><br>
    <span style='opacity:.8;font-size:.85rem'>
      Use Tab para mover entre elementos interativos e Enter ou Espaco para ativar botoes.
      O link "Pular para o conteudo" no topo evita repetir a navegacao pela barra de acessibilidade.
      Todos os elementos possuem indicador de foco visivel destacado em azul claro.
    </span>
  </div>
</div>
</div>
""", unsafe_allow_html=True)
    if st.button("Fechar guia", key="close_acc_help"):
        st.session_state['acc_help'] = False
        st.rerun()


def tts_button(text, key, label="Ouvir Descricao"):
    safe = (text
            .replace("\\", "\\\\")
            .replace("'", "\\'")
            .replace('"', '\\"')
            .replace("\n", " ")
            .replace("\r", ""))
    bid = "tts_{}".format(key)
    html = """
<div style='margin:.4rem 0'>
  <button id='{bid}'
    onclick="(function(){{
      if(window._ttsU){{window.speechSynthesis.cancel();}}
      var u=new SpeechSynthesisUtterance('{safe}');
      u.lang='pt-BR';u.rate=0.9;u.pitch=1.05;
      window._ttsU=u;
      var b=document.getElementById('{bid}');
      if(b)b.textContent='Parar naracao';
      u.onend=function(){{if(b)b.textContent='{label}';}};
      u.onerror=function(){{if(b)b.textContent='{label}';}};
      window.speechSynthesis.speak(u);
    }})()"
    aria-label="Reproduzir audiodescricao da obra"
    style="background:rgba(96,165,250,.22);border:1px solid rgba(96,165,250,.48);
      color:#dbeafe;border-radius:50px;padding:.46rem 1.2rem;cursor:pointer;
      font-weight:700;font-size:.81rem;transition:all .3s;font-family:inherit;
      display:inline-flex;align-items:center;gap:.4rem;"
    onmouseover="this.style.background='rgba(96,165,250,.38)'"
    onmouseout="this.style.background='rgba(96,165,250,.22)'"
  >{label}</button>
</div>
""".format(bid=bid, safe=safe, label=label)
    st.markdown(html, unsafe_allow_html=True)


# ── HELPERS ───────────────────────────────────────────────────────────
def kpi(label, value, sub="", color="#a7e6ff"):
    sub_h = "<div class='kpi-sub'>{}</div>".format(sub) if sub else ""
    return (
        "<div class='kpi-card'>"
        "<div class='kpi-lbl'>{}</div>"
        "<div class='kpi-val' style='color:{}'>{}</div>"
        "{}</div>"
    ).format(label, color, value, sub_h)


def insight(text):
    return "<div class='insight'>{}</div>".format(text)


def divider():
    return "<div class='divider'></div>"


def pbar(pct, color="#60a5fa"):
    w = min(100, max(0, pct * 100))
    return (
        "<div class='pbar-o'>"
        "<div class='pbar-i' style='width:{:.1f}%;background:{}'></div>"
        "</div>"
    ).format(w, color)


def audio_desc_box(descricao, obra_id):
    st.markdown(
        "<div class='audio-desc-box' role='region' aria-label='Audiodescricao'>"
        "<div class='audio-desc-title'>Audiodescricao</div>"
        "<div class='audio-desc-text'>{}</div>"
        "</div>".format(descricao),
        unsafe_allow_html=True,
    )
    tts_button(descricao, key="obra_{}".format(obra_id), label="Ouvir Descricao")


# ── DADOS ─────────────────────────────────────────────────────────────
def check_admin():
    admins = load_json_file(ADMIN_FILE, [])
    if not admins:
        hashed = hashlib.sha256(ADMIN_PASSWORD.encode()).hexdigest()
        save_json_file(ADMIN_FILE, [{"id": 1, "username": ADMIN_USERNAME, "password": hashed}])


def gen_uid():
    return base64.b64encode(os.urandom(12)).decode('ascii')


@st.cache_data(ttl=5, show_spinner=False)
def load_obras():
    default = [
        {
            "id": 1, "titulo": "Guernica", "artista": "Pablo Picasso", "ano": "1937",
            "imagem": "https://upload.wikimedia.org/wikipedia/en/7/74/PicassoGuernica.jpg",
            "descricao": OBRAS_DESC[1],
        },
        {
            "id": 2, "titulo": "A Noite Estrelada", "artista": "Vincent van Gogh", "ano": "1889",
            "imagem": (
                "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ea/"
                "Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg/"
                "1200px-Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg"
            ),
            "descricao": OBRAS_DESC[2],
        },
        {
            "id": 3, "titulo": "Mona Lisa", "artista": "Leonardo da Vinci", "ano": "1503",
            "imagem": (
                "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ec/"
                "Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_retouched.jpg/"
                "800px-Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_retouched.jpg"
            ),
            "descricao": OBRAS_DESC[3],
        },
    ]
    obras = load_json_file(OBRAS_FILE, default)
    if not obras:
        save_json_file(OBRAS_FILE, default)
        return default
    for o in obras:
        if not o.get('descricao'):
            fb = OBRAS_DESC.get(o['id'])
            o['descricao'] = fb if fb else (
                "Obra intitulada {}, de {}, criada em {}. "
                "Nenhuma descricao detalhada cadastrada."
            ).format(o.get('titulo', ''), o.get('artista', ''), o.get('ano', ''))
    return obras


def save_answers(uid, animal, answers):
    users = load_json_file(USERS_FILE, [])
    entry = {
        "user_id": uid, "animal_name": animal,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    entry.update(answers)
    users.append(entry)
    return save_json_file(USERS_FILE, users)


def save_tag(uid, obra_id, tag):
    tags = load_json_file(TAGS_FILE, [])
    tags.append({
        "id": len(tags) + 1, "user_id": uid, "obra_id": obra_id,
        "tag": tag.lower().strip(),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })
    st.cache_data.clear()
    return save_json_file(TAGS_FILE, tags)


def get_user_tags(uid):
    tags = load_json_file(TAGS_FILE, [])
    ut = [t for t in tags if t['user_id'] == uid]
    return pd.DataFrame(ut) if ut else pd.DataFrame()


def get_obra_user_tags(obra_id, uid):
    tags = load_json_file(TAGS_FILE, [])
    f = [t for t in tags if t['obra_id'] == obra_id and t['user_id'] == uid]
    if f:
        df = pd.DataFrame(f)
        c = df['tag'].value_counts().reset_index()
        c.columns = ["tag", "count"]
        return c
    return pd.DataFrame(columns=["tag", "count"])


def check_login(username, password):
    h = hashlib.sha256(password.encode()).hexdigest()
    return (username == ADMIN_USERNAME and
            h == hashlib.sha256(ADMIN_PASSWORD.encode()).hexdigest())


def all_tags():
    t = load_json_file(TAGS_FILE, [])
    return pd.DataFrame(t) if t else pd.DataFrame()


def all_users():
    u = load_json_file(USERS_FILE, [])
    return pd.DataFrame(u) if u else pd.DataFrame()


# ── EXPORTACAO ────────────────────────────────────────────────────────
def html_quest(uid, animal, users_df):
    if users_df.empty:
        return None
    ud = users_df[users_df['user_id'] == uid]
    if ud.empty:
        return None
    ui = ud.iloc[0]
    return (
        '<!DOCTYPE html><html><head><meta charset="UTF-8">'
        '<style>'
        '*{margin:0;padding:0;box-sizing:border-box}'
        'body{font-family:sans-serif;background:linear-gradient(135deg,#000,#001F3F);padding:40px;color:white}'
        '.c{max-width:900px;margin:0 auto;background:rgba(255,255,255,.15);padding:50px;border-radius:24px;border:1px solid rgba(255,255,255,.3)}'
        'h1{text-align:center;margin-bottom:15px;font-size:2.2rem}'
        '.hi{text-align:center;margin-bottom:35px;opacity:.9}'
        '.ab{background:rgba(167,230,255,.25);border:1px solid rgba(167,230,255,.5);color:#a7e6ff;padding:.3rem 1rem;border-radius:50px;font-weight:700;display:inline-block}'
        '.qb{margin:22px 0;padding:18px 22px;background:rgba(255,255,255,.1);border-left:4px solid rgba(255,255,255,.5);border-radius:12px}'
        '.q{font-weight:700;margin-bottom:8px}.a{line-height:1.7;opacity:.92}'
        '.ft{text-align:center;margin-top:40px;padding-top:18px;border-top:1px solid rgba(255,255,255,.2);opacity:.65;font-size:.88rem}'
        '</style></head><body><div class="c"><h1>Respostas do Questionario</h1>'
        '<div class="hi">'
        '<p>Usuario Anonimo: <span class="ab">{animal}</span></p>'
        '<p style="margin-top:6px;opacity:.65">Data: {ts}</p>'
        '</div>'
        '<div class="qb"><div class="q">1. Nivel de familiaridade com museus</div><div class="a">{q1}</div></div>'
        '<div class="qb"><div class="q">2. Conhecimento sobre documentacao museologica</div><div class="a">{q2}</div></div>'
        '<div class="qb"><div class="q">3. O que voce entende por tags?</div><div class="a">{q3}</div></div>'
        '<div class="ft">Sistema Folksonomia Digital — Ctrl+P para salvar como PDF</div>'
        '</div></body></html>'
    ).format(
        animal=animal,
        ts=ui.get('timestamp', 'N/A'),
        q1=ui.get('q1', 'N/A'),
        q2=ui.get('q2', 'N/A'),
        q3=ui.get('q3', 'N/A'),
    )


def html_tags(uid, animal, obras, tags_df):
    ut = tags_df[tags_df['user_id'] == uid] if not tags_df.empty else pd.DataFrame()
    if ut.empty:
        return None
    od = {o['id']: o for o in obras}
    rows = ""
    for i, (_, r) in enumerate(ut.iterrows()):
        titulo = od.get(r['obra_id'], {}).get('titulo', 'Obra {}'.format(r['obra_id']))
        rows += (
            '<tr><td>{n}</td><td>{titulo}</td>'
            '<td><span style="background:rgba(255,255,255,.22);padding:3px 10px;border-radius:50px">{tag}</span></td>'
            '<td>{ts}</td></tr>'
        ).format(n=i + 1, titulo=titulo, tag=r['tag'], ts=r['timestamp'])
    top = ""
    for i, (t, c) in enumerate(ut['tag'].value_counts().head(10).items(), 1):
        top += '<tr><td>{}</td><td>{}</td><td>{}</td></tr>'.format(i, t, c)

    return (
        '<!DOCTYPE html><html><head><meta charset="UTF-8">'
        '<style>'
        '*{margin:0;padding:0;box-sizing:border-box}'
        'body{font-family:sans-serif;background:linear-gradient(135deg,#000,#001F3F);padding:40px;color:white}'
        '.c{max-width:1100px;margin:0 auto;background:rgba(255,255,255,.15);padding:50px;border-radius:24px;border:1px solid rgba(255,255,255,.3)}'
        'h1{text-align:center;margin-bottom:15px;font-size:2.2rem}'
        '.hi{text-align:center;margin-bottom:28px;opacity:.9}'
        '.ab{background:rgba(167,230,255,.25);border:1px solid rgba(167,230,255,.5);color:#a7e6ff;padding:.3rem 1rem;border-radius:50px;font-weight:700;display:inline-block}'
        '.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin:22px 0}'
        '.sb{background:rgba(255,255,255,.14);border:1px solid rgba(255,255,255,.28);padding:18px;border-radius:12px;text-align:center}'
        '.sv{font-size:2.6rem;font-weight:800}.sl{font-size:.82rem;text-transform:uppercase;letter-spacing:1.5px;margin-top:7px;opacity:.85}'
        'table{width:100%;border-collapse:collapse;margin:18px 0}'
        'th,td{padding:13px;text-align:left;border-bottom:1px solid rgba(255,255,255,.14)}'
        'th{background:rgba(255,255,255,.18);font-weight:700;text-transform:uppercase;font-size:.82rem}'
        'tr:nth-child(even){background:rgba(255,255,255,.04)}'
        '.ft{text-align:center;margin-top:38px;padding-top:18px;border-top:1px solid rgba(255,255,255,.2);opacity:.65;font-size:.88rem}'
        '</style></head><body><div class="c"><h1>Relatorio de Tags</h1>'
        '<div class="hi">'
        '<p>Usuario Anonimo: <span class="ab">{animal}</span></p>'
        '<p style="margin-top:6px;opacity:.65">Gerado em: {dt}</p>'
        '</div>'
        '<div class="stats">'
        '<div class="sb"><div class="sv">{total}</div><div class="sl">Total de Tags</div></div>'
        '<div class="sb"><div class="sv">{unicas}</div><div class="sl">Tags Unicas</div></div>'
        '<div class="sb"><div class="sv">{obras_n}</div><div class="sl">Obras Etiquetadas</div></div>'
        '</div>'
        '<h2 style="margin:28px 0 14px;font-size:1.5rem">Todas as Tags</h2>'
        '<table><thead><tr><th>#</th><th>Obra</th><th>Tag</th><th>Data/Hora</th></tr></thead>'
        '<tbody>{rows}</tbody></table>'
        '<h2 style="margin:28px 0 14px;font-size:1.5rem">Top 10 Tags</h2>'
        '<table><thead><tr><th>Pos.</th><th>Tag</th><th>Freq.</th></tr></thead>'
        '<tbody>{top}</tbody></table>'
        '<div class="ft">Sistema Folksonomia Digital — Ctrl+P para salvar como PDF</div>'
        '</div></body></html>'
    ).format(
        animal=animal,
        dt=datetime.now().strftime('%d/%m/%Y %H:%M'),
        total=len(ut),
        unicas=ut['tag'].nunique(),
        obras_n=ut['obra_id'].nunique(),
        rows=rows,
        top=top,
    )


# ── INTERFACE PRINCIPAL ───────────────────────────────────────────────
def show_header():
    st.markdown(
        "<div class='top-navbar' role='banner'>"
        "<div class='navbar-logo'>Sistema Folksonomia Digital</div>"
        "<div style='font-size:.76rem;opacity:.55'>Catalogacao Colaborativa de Arte</div>"
        "</div>",
        unsafe_allow_html=True,
    )


def main():
    init_acc()
    render_acc_bar()
    build_css()

    if st.session_state.get('acc_help', False):
        render_acc_help()
        return

    try:
        check_admin()
    except Exception as e:
        st.error("Erro ao inicializar: {}".format(e))

    for k, v in [
        ('user_id', gen_uid()),
        ('animal_name', generate_animal_name()),
        ('step', 'intro'),
        ('answers', {}),
    ]:
        if k not in st.session_state:
            st.session_state[k] = v

    if st.session_state['step'] != 'completed':
        show_intro()
    else:
        show_header()
        st.markdown("<div class='main-content' id='main-content' role='main'>", unsafe_allow_html=True)
        t1, t2 = st.tabs(["Explorar Obras", "Area Administrativa"])
        with t1:
            show_obras()
        with t2:
            show_admin()
        st.markdown("</div>", unsafe_allow_html=True)


# ── INTRO ─────────────────────────────────────────────────────────────
def show_intro():
    st.markdown("<div class='main-content' id='main-content'>", unsafe_allow_html=True)
    st.markdown("<h1 class='main-title'>Sistema Folksonomia Digital</h1>", unsafe_allow_html=True)
    st.markdown(
        "<p class='subtitle'>Sistema colaborativo de catalogacao de obras de arte<br>"
        "Complete o questionario para acessar a plataforma</p>",
        unsafe_allow_html=True,
    )
    st.markdown("<div class='glass-card' role='form' aria-label='Questionario de acesso'>",
                unsafe_allow_html=True)
    st.markdown(
        "<h2 style='text-align:center;margin-bottom:2rem;font-size:1.6rem'>Questionario de Acesso</h2>",
        unsafe_allow_html=True,
    )
    with st.form("intro_form"):
        c1, c2 = st.columns(2)
        with c1:
            q1 = st.selectbox(
                "1. Qual e o seu nivel de familiaridade com museus?",
                ["Nunca visito museus", "Visito raramente",
                 "Visito ocasionalmente", "Visito frequentemente"],
            )
            q2 = st.selectbox(
                "2. Voce ja ouviu falar sobre documentacao museologica?",
                ["Nunca ouvi falar", "Ja ouvi, mas nao sei o que e",
                 "Tenho uma ideia basica", "Conheco bem o tema"],
            )
        with c2:
            q3 = st.text_area(
                "3. O que voce entende por 'tags' ou etiquetas digitais aplicadas a acervo?",
                max_chars=500, height=200,
                placeholder="Descreva sua compreensao sobre o conceito...",
            )
        _, cb, _ = st.columns([1, 1, 1])
        with cb:
            submitted = st.form_submit_button("Acessar Plataforma", use_container_width=True)
        if submitted:
            if not q3.strip():
                st.error("Por favor, responda todas as perguntas para continuar.")
            else:
                st.session_state['answers'] = {"q1": q1, "q2": q2, "q3": q3}
                save_answers(
                    st.session_state['user_id'],
                    st.session_state['animal_name'],
                    st.session_state['answers'],
                )
                st.session_state['step'] = 'completed'
                st.success("Questionario completo! Acesso liberado.")
                st.balloons()
                st.rerun()
    st.markdown("</div></div>", unsafe_allow_html=True)


# ── GALERIA ───────────────────────────────────────────────────────────
def show_obras():
    st.markdown("<h1 class='main-title'>Galeria de Obras de Arte</h1>", unsafe_allow_html=True)
    st.markdown(
        "<p class='subtitle'>Explore as obras, ouça as descricoes em audio e contribua com suas tags</p>",
        unsafe_allow_html=True,
    )
    st.markdown(
        insight(
            "<strong>Acessibilidade:</strong> Cada obra possui audiodescricao detalhada. "
            "Clique em <strong>Ouvir Descricao</strong> para ouvir a naracao em voz alta. "
            "Use os controles no topo para ajustar texto, tema e contraste."
        ),
        unsafe_allow_html=True,
    )

    obras = load_obras()
    if not obras:
        st.info("Nenhuma obra cadastrada.")
        return

    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    c1, c2 = st.columns([2, 1])
    with c1:
        sid = st.text_input("Filtrar por numero da obra:", "",
                            placeholder="Ex: 1, 2, 3...",
                            help="Digite o numero da obra para filtrar a galeria")
    with c2:
        sord = st.selectbox("Ordenar por:", ["Numero (crescente)", "Numero (decrescente)"])
    st.markdown("</div>", unsafe_allow_html=True)

    filtered = obras
    if sid.strip().isdigit():
        filtered = [o for o in obras if str(o['id']) == sid.strip()]
    filtered = sorted(filtered, key=lambda x: x['id'], reverse=(sord == "Numero (decrescente)"))

    st.markdown(
        "<div style='text-align:center;margin:1.8rem 0;font-size:1.05rem;font-weight:600'>"
        "Exibindo <strong style='font-size:1.35rem'>{}</strong> obra(s)"
        "</div>".format(len(filtered)),
        unsafe_allow_html=True,
    )

    cols = st.columns(3)
    for i, obra in enumerate(filtered):
        with cols[i %

