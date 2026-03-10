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
import math
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

AUDIO_DESCRIPTIONS = {
    1: "Guernica, de Pablo Picasso, 1937. Obra monumental em tons de cinza, preto e branco. Representa a tragédia do bombardeio da cidade basca de Guernica durante a Guerra Civil Espanhola. Figuras fragmentadas de humanos e animais expressam angústia, dor e desespero. Uma mãe segura seu filho morto, um touro observa a cena, um cavalo ferido grita ao centro. Composição caótica que simboliza os horrores da guerra.",
    2: "A Noite Estrelada, de Vincent van Gogh, 1889. Paisagem noturna com céu turbilhonante em azuis e dourados intensos. Redemoinhos de tinta representam o vento e o movimento das estrelas sobre a vila de Saint-Rémy-de-Provence. No centro, uma lua crescente brilhante. À esquerda, um cipreste escuro sobe em espiral. Casas com janelas iluminadas trazem calor humano sob o céu dramático.",
    3: "Mona Lisa, de Leonardo da Vinci, 1503-1519. Retrato feminino sobre fundo de paisagem nebulosa. A figura apresenta um sorriso enigmático e ambíguo que mudou ao longo dos séculos. Seus olhos parecem seguir o espectador. Cabelos escuros cobertos por véu translúcido. Técnica de sfumato cria transições suaves entre luz e sombra, conferindo profundidade e realismo à figura."
}

def generate_animal_name():
    random.seed()
    return f"{random.choice(ANIMAIS)} {random.choice(ADJETIVOS)}"

# ── CORE ──────────────────────────────────────────────────────────────
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

def tag_entropy(tag_counts):
    total = sum(tag_counts.values())
    if total == 0: return 0
    return -sum((c/total)*math.log2(c/total) for c in tag_counts.values() if c > 0)

def tag_cooccurrence(tdf, top_n=15):
    if tdf.empty: return pd.DataFrame()
    top_tags = tdf['tag'].value_counts().head(top_n).index.tolist()
    user_obra = tdf.groupby(['user_id','obra_id'])['tag'].apply(list).reset_index()
    matrix = pd.DataFrame(0, index=top_tags, columns=top_tags)
    for _, row in user_obra.iterrows():
        session_tags = [t for t in row['tag'] if t in top_tags]
        for i in range(len(session_tags)):
            for j in range(i+1, len(session_tags)):
                t1, t2 = session_tags[i], session_tags[j]
                if t1 != t2:
                    matrix.loc[t1, t2] += 1
                    matrix.loc[t2, t1] += 1
    return matrix

# ── CSS ───────────────────────────────────────────────────────────────
def load_css():
    theme = st.session_state.get('theme', 'dark')
    font_size = st.session_state.get('font_size', 'medium')
    high_contrast = st.session_state.get('high_contrast', False)

    font_map = {'small':'13px','medium':'15px','large':'17px','xlarge':'20px'}
    base_font = font_map.get(font_size, '15px')

    if theme == 'light':
        bg = "linear-gradient(-45deg,#e8f4fd 0%,#f0f7ff 25%,#e8f4fd 50%,#dbeeff 75%,#e8f4fd 100%)"
        card_bg = "rgba(255,255,255,0.85)"
        card_border = "rgba(0,80,160,0.18)"
        text_color = "#0a1628"
        text_muted = "rgba(10,22,40,0.55)"
        navbar_bg = "rgba(255,255,255,0.88)"
        navbar_border = "rgba(0,80,160,0.15)"
        kpi_bg = "rgba(0,80,160,0.09)"
        kpi_border = "rgba(0,80,160,0.18)"
        badge_bg = "rgba(0,80,160,0.12)"
        badge_border = "rgba(0,80,160,0.3)"
        input_bg = "rgba(0,80,160,0.07)"
        input_border = "rgba(0,80,160,0.25)"
        btn_bg = "rgba(0,80,160,0.14)"
        btn_hover = "rgba(0,80,160,0.28)"
        tab_bg = "rgba(0,80,160,0.07)"
        tab_sel = "rgba(0,80,160,0.22)"
        conn_bg = "rgba(0,80,160,0.06)"
        conn_hover = "rgba(0,80,160,0.13)"
        sc_bg = "rgba(0,80,160,0.05)"
        title_color = "#001F3F"
        subtitle_color = "#1a3a6b"
        logo_grad = "linear-gradient(135deg,#001F3F 0%,#0056b3 100%)"
    else:
        bg = "linear-gradient(-45deg,#000 0%,#001F3F 25%,#000 50%,#001F3F 75%,#000 100%)"
        card_bg = "rgba(255,255,255,0.15)"
        card_border = "rgba(255,255,255,0.3)"
        text_color = "#e0e0e0"
        text_muted = "rgba(255,255,255,0.45)"
        navbar_bg = "rgba(255,255,255,0.1)"
        navbar_border = "rgba(255,255,255,0.2)"
        kpi_bg = "rgba(255,255,255,0.16)"
        kpi_border = "rgba(255,255,255,0.28)"
        badge_bg = "rgba(255,255,255,0.25)"
        badge_border = "rgba(255,255,255,0.4)"
        input_bg = "rgba(255,255,255,0.18)"
        input_border = "rgba(255,255,255,0.28)"
        btn_bg = "rgba(255,255,255,0.25)"
        btn_hover = "rgba(255,255,255,0.4)"
        tab_bg = "rgba(255,255,255,0.1)"
        tab_sel = "rgba(255,255,255,0.33)"
        conn_bg = "rgba(255,255,255,0.06)"
        conn_hover = "rgba(255,255,255,0.12)"
        sc_bg = "rgba(255,255,255,0.07)"
        title_color = "white"
        subtitle_color = "rgba(255,255,255,0.9)"
        logo_grad = "linear-gradient(135deg,#a7e6ff 0%,#d1baff 100%)"

    if high_contrast:
        text_color = "#ffffff" if theme=='dark' else "#000000"
        card_border = "2px solid " + ("#ffffff" if theme=='dark' else "#000000")

    st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');
*{{margin:0;padding:0;box-sizing:border-box;font-family:'Inter',sans-serif!important;font-size:{base_font}}}
@keyframes bgani{{0%{{background-position:0% 50%}}50%{{background-position:100% 50%}}100%{{background-position:0% 50%}}}}
@keyframes fadeUp{{from{{opacity:0;transform:translateY(24px)}}to{{opacity:1;transform:translateY(0)}}}}
@keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:.7}}}}
@keyframes shimmer{{0%{{left:-100%}}100%{{left:100%}}}}
@keyframes spin{{to{{transform:rotate(360deg)}}}}

.stApp{{
  background:{bg};
  background-size:400% 400%;animation:bgani 18s ease infinite;
  color:{text_color}
}}

/* ── NAVBAR ── */
.top-navbar{{
  position:fixed;top:0;left:0;right:0;z-index:9999;
  background:{navbar_bg};backdrop-filter:blur(24px) saturate(180%);
  border-bottom:1px solid {navbar_border};padding:1.1rem 2.5rem;
  display:flex;justify-content:space-between;align-items:center;
  box-shadow:0 4px 30px rgba(0,0,0,0.08)
}}
.navbar-logo{{
  font-size:1.5rem;font-weight:900;letter-spacing:-1px;
  background:{logo_grad};
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text
}}
.navbar-sub{{
  font-size:.72rem;font-weight:500;
  color:{text_muted};letter-spacing:1px;text-transform:uppercase
}}

/* ── ACCESSIBILITY BAR ── */
.access-bar{{
  position:fixed;top:72px;right:0;z-index:9998;
  background:{navbar_bg};backdrop-filter:blur(20px);
  border:1px solid {navbar_border};border-right:none;border-radius:16px 0 0 16px;
  padding:.55rem .8rem;display:flex;flex-direction:column;gap:6px;
  box-shadow:-4px 4px 20px rgba(0,0,0,0.12);transition:all .3s
}}
.access-btn{{
  display:inline-flex;align-items:center;justify-content:center;
  background:{badge_bg};border:1px solid {badge_border};
  color:{text_color};border-radius:10px;padding:.38rem .6rem;
  font-size:.75rem;font-weight:700;cursor:pointer;transition:all .2s;
  white-space:nowrap;min-width:38px;text-align:center;text-decoration:none
}}
.access-btn:hover{{background:{btn_hover};transform:scale(1.08)}}
.access-btn.active{{background:rgba(96,165,250,0.35);border-color:#60a5fa}}
.access-section-label{{
  font-size:.58rem;color:{text_muted};text-transform:uppercase;
  letter-spacing:1px;text-align:center;padding:.15rem 0
}}

/* ── MAIN CONTENT ── */
.main-content{{
  margin-top:80px;padding:2rem 2.5rem;
  max-width:1700px;margin-left:auto;margin-right:auto
}}

/* ── GLASS CARDS ── */
.glass-card{{
  background:{card_bg};backdrop-filter:blur(20px) saturate(180%);
  border:1px solid {card_border};border-radius:24px;padding:2.2rem;margin:1.2rem 0;
  box-shadow:0 8px 32px rgba(0,0,0,0.08);transition:all .4s cubic-bezier(.4,0,.2,1);
  position:relative;overflow:hidden;animation:fadeUp .5s ease both
}}
.glass-card::before{{
  content:'';position:absolute;top:0;left:-100%;width:100%;height:2px;
  background:{logo_grad};transition:left .5s
}}
.glass-card:hover::before{{left:100%}}
.glass-card:hover{{
  transform:translateY(-6px);
  box-shadow:0 20px 60px rgba(0,0,0,0.15);
  border-color:{badge_border}
}}

/* ── OBRA CARDS ── */
.obra-card{{
  background:{card_bg};backdrop-filter:blur(15px);
  border:1px solid {card_border};border-radius:22px;overflow:hidden;
  transition:all .45s cubic-bezier(.4,0,.2,1);cursor:pointer;position:relative
}}
.obra-card::after{{
  content:'';position:absolute;inset:0;
  background:linear-gradient(to top,rgba(0,0,0,0.5),transparent 60%);
  opacity:0;transition:opacity .4s
}}
.obra-card:hover::after{{opacity:1}}
.obra-card:hover{{
  transform:translateY(-14px) scale(1.025);
  box-shadow:0 24px 70px rgba(0,31,63,0.35);
  border-color:{badge_border}
}}
.obra-card img{{
  width:100%;height:260px;object-fit:cover;
  transition:transform .65s cubic-bezier(.4,0,.2,1)
}}
.obra-card:hover img{{transform:scale(1.12)}}

/* ── LIST VIEW ── */
.obra-list-item{{
  display:flex;gap:1.5rem;align-items:flex-start;
  background:{card_bg};backdrop-filter:blur(15px);
  border:1px solid {card_border};border-radius:18px;
  padding:1.2rem;margin:.7rem 0;
  transition:all .3s cubic-bezier(.4,0,.2,1);
  animation:fadeUp .4s ease both
}}
.obra-list-item:hover{{
  transform:translateX(6px);
  border-color:{badge_border};
  box-shadow:0 8px 30px rgba(0,31,63,0.2)
}}
.obra-list-img{{
  width:140px;min-width:140px;height:100px;
  object-fit:cover;border-radius:12px
}}

/* ── TYPOGRAPHY ── */
.main-title{{
  color:{title_color};font-size:3.2rem;font-weight:900;
  text-align:center;margin:1.5rem 0 .8rem;letter-spacing:-2px;
  animation:fadeUp .6s ease both
}}
.subtitle{{
  color:{subtitle_color};font-size:1.15rem;text-align:center;
  margin-bottom:2.5rem;line-height:1.8;font-weight:400;
  animation:fadeUp .7s ease both
}}

/* ── BADGES & TAGS ── */
.tag-badge{{
  display:inline-flex;align-items:center;gap:4px;
  background:{badge_bg};backdrop-filter:blur(10px);
  border:1px solid {badge_border};color:{text_color};
  padding:.42rem 1rem;border-radius:50px;margin:.25rem;
  font-size:.84rem;font-weight:600;transition:all .25s;cursor:default
}}
.tag-badge:hover{{
  background:{btn_hover};transform:translateY(-3px) scale(1.06);
  box-shadow:0 6px 20px rgba(0,0,0,0.12)
}}
.tag-green{{background:rgba(34,197,94,.2)!important;border-color:rgba(34,197,94,.45)!important;color:#86efac!important}}
.tag-amber{{background:rgba(245,158,11,.2)!important;border-color:rgba(245,158,11,.45)!important;color:#fde68a!important}}
.tag-blue {{background:rgba(96,165,250,.2)!important;border-color:rgba(96,165,250,.45)!important;color:#bfdbfe!important}}
.tag-rose {{background:rgba(244,63,94,.2)!important;border-color:rgba(244,63,94,.45)!important;color:#fecdd3!important}}

.animal-badge{{
  display:inline-flex;align-items:center;gap:6px;
  background:rgba(167,230,255,.18);border:1px solid rgba(167,230,255,.4);
  color:#a7e6ff;padding:.38rem 1rem;border-radius:50px;
  font-size:.84rem;font-weight:700
}}

/* ── KPI CARDS ── */
.kpi-card{{
  background:{kpi_bg};backdrop-filter:blur(20px);
  border:1px solid {kpi_border};border-radius:20px;padding:1.6rem;
  text-align:center;color:{text_color};
  box-shadow:0 6px 24px rgba(0,0,0,0.08);
  transition:all .4s cubic-bezier(.4,0,.2,1);
  animation:fadeUp .5s ease both
}}
.kpi-card:hover{{transform:translateY(-8px) scale(1.04);box-shadow:0 16px 48px rgba(0,31,63,0.2)}}
.kpi-val{{font-size:2.4rem;font-weight:900;margin:.5rem 0;letter-spacing:-1px}}
.kpi-lbl{{font-size:.72rem;text-transform:uppercase;letter-spacing:2px;font-weight:700;opacity:.75}}
.kpi-sub{{font-size:.68rem;opacity:.5;margin-top:.3rem}}
.kpi-trend{{font-size:.78rem;margin-top:.4rem;font-weight:600}}

/* ── SECTION CARDS ── */
.sc{{background:{sc_bg};border:1px solid {card_border};border-radius:14px;padding:1.2rem;margin:.6rem 0}}
.sc-b{{border-left:4px solid #60a5fa;background:rgba(96,165,250,0.07)}}
.sc-g{{border-left:4px solid #34d399;background:rgba(52,211,153,0.07)}}
.sc-p{{border-left:4px solid #a78bfa;background:rgba(167,139,250,0.07)}}
.sc-a{{border-left:4px solid #fbbf24;background:rgba(251,191,36,0.07)}}
.sc-r{{border-left:4px solid #f87171;background:rgba(248,113,113,0.07)}}

/* ── INSIGHTS ── */
.insight{{
  background:rgba(96,165,250,0.1);
  border:1px solid rgba(96,165,250,0.25);border-radius:14px;
  padding:1rem 1.4rem;margin:.6rem 0;
  color:{text_color};font-size:.9rem;line-height:1.75
}}
.insight strong{{color:#60a5fa}}

/* ── CONNECTIONS ── */
.conn-row{{
  display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;
  background:{conn_bg};border-radius:13px;padding:.8rem 1.2rem;margin:.3rem 0;
  border-left:3px solid rgba(96,165,250,0.3);
  transition:background .2s,transform .2s;
  animation:fadeUp .4s ease both
}}
.conn-row:hover{{background:{conn_hover};transform:translateX(4px)}}

/* ── CLUSTERS ── */
.cluster-wrap{{
  background:{sc_bg};border-radius:16px;padding:1.2rem 1.4rem;
  margin:.5rem 0;border:1px solid {card_border};
  transition:all .3s;animation:fadeUp .5s ease both
}}
.cluster-wrap:hover{{border-color:{badge_border};box-shadow:0 6px 24px rgba(0,0,0,0.08)}}
.cluster-title{{font-size:.73rem;text-transform:uppercase;letter-spacing:1.5px;
  color:rgba(167,139,250,0.85);margin-bottom:.6rem;font-weight:800}}
.cluster-pill{{
  display:inline-flex;align-items:center;gap:5px;
  background:rgba(168,85,247,0.18);border:1px solid rgba(168,85,247,0.35);
  border-radius:50px;padding:.3rem .85rem;margin:.2rem;
  font-size:.78rem;font-weight:600;color:#f3e8ff;transition:all .2s
}}
.cluster-pill:hover{{background:rgba(168,85,247,0.35);transform:scale(1.05)}}

/* ── PROGRESS BAR ── */
.pbar-o{{background:rgba(255,255,255,0.1);border-radius:50px;height:5px;margin:3px 0;overflow:hidden}}
.pbar-i{{height:100%;border-radius:50px;transition:width .6s cubic-bezier(.4,0,.2,1)}}

/* ── DIVIDER ── */
.divider{{
  height:1px;
  background:linear-gradient(90deg,transparent,{card_border},transparent);
  margin:1.8rem 0
}}

/* ── FILTER PANEL ── */
.filter-panel{{
  background:{card_bg};backdrop-filter:blur(20px);
  border:1px solid {card_border};border-radius:20px;
  padding:1.5rem;margin:1rem 0;
  box-shadow:0 4px 20px rgba(0,0,0,0.08)
}}
.filter-chip{{
  display:inline-flex;align-items:center;gap:5px;
  background:{badge_bg};border:1px solid {badge_border};
  color:{text_color};padding:.3rem .8rem;border-radius:50px;
  font-size:.78rem;font-weight:600;margin:.2rem;cursor:pointer;
  transition:all .2s
}}
.filter-chip.active{{background:rgba(96,165,250,0.3);border-color:#60a5fa;color:#bfdbfe}}

/* ── AUDIO DESCRIPTION ── */
.audio-desc-btn{{
  display:inline-flex;align-items:center;gap:6px;
  background:rgba(52,211,153,0.18);border:1px solid rgba(52,211,153,0.4);
  color:#6ee7b7;padding:.38rem .9rem;border-radius:50px;
  font-size:.8rem;font-weight:700;cursor:pointer;
  transition:all .25s;border:none;width:100%;justify-content:center;
  margin:.3rem 0
}}
.audio-desc-btn:hover{{background:rgba(52,211,153,0.35);transform:scale(1.03)}}

/* ── OBRA NUMBER BADGE ── */
.obra-num{{
  position:absolute;top:12px;left:12px;z-index:10;
  background:rgba(0,0,0,0.6);backdrop-filter:blur(10px);
  color:white;padding:.25rem .7rem;border-radius:50px;
  font-size:.75rem;font-weight:800;letter-spacing:1px
}}

/* ── VIEW MODE TOGGLE ── */
.view-toggle{{
  display:inline-flex;background:{sc_bg};
  border:1px solid {card_border};border-radius:12px;overflow:hidden
}}
.view-toggle-btn{{
  padding:.5rem 1rem;font-size:.82rem;font-weight:700;
  cursor:pointer;transition:all .2s;border:none;
  background:transparent;color:{text_color}
}}
.view-toggle-btn.active{{background:rgba(96,165,250,0.25);color:#60a5fa}}

/* ── STREAMLIT OVERRIDES ── */
.stButton button{{
  background:{btn_bg}!important;backdrop-filter:blur(15px)!important;
  color:{text_color}!important;border:1px solid {badge_border}!important;
  border-radius:14px!important;padding:.75rem 1.8rem!important;
  font-weight:700!important;font-size:.88rem!important;
  transition:all .3s!important;box-shadow:0 4px 15px rgba(0,0,0,0.08)!important;
  letter-spacing:.3px
}}
.stButton button:hover{{
  background:{btn_hover}!important;
  box-shadow:0 10px 30px rgba(0,31,63,0.2)!important;
  transform:translateY(-3px) scale(1.03)!important;
  border-color:{badge_border}!important
}}
.stTextInput input,.stTextArea textarea,.stSelectbox select,.stMultiSelect {{
  background:{input_bg}!important;backdrop-filter:blur(10px)!important;
  border:1px solid {input_border}!important;color:{text_color}!important;
  border-radius:12px!important;padding:.8rem!important;font-weight:500!important
}}
.stTextInput input::placeholder,.stTextArea textarea::placeholder{{color:{text_muted}!important}}
.stTextInput input:focus,.stTextArea textarea:focus{{
  border-color:rgba(96,165,250,0.7)!important;
  box-shadow:0 0 0 3px rgba(96,165,250,0.15)!important
}}
label{{color:{text_color}!important;font-weight:700!important;font-size:.9rem!important}}
.stTabs [data-baseweb="tab-list"]{{
  gap:.5rem;background:{tab_bg};
  backdrop-filter:blur(10px);padding:.4rem;border-radius:14px;
  border:1px solid {card_border}
}}
.stTabs [data-baseweb="tab"]{{
  background:rgba(255,255,255,0.06);
  border:1px solid transparent;border-radius:10px;
  color:{text_color};padding:.65rem 1.3rem;font-weight:700;
  font-size:.85rem;transition:all .25s
}}
.stTabs [data-baseweb="tab"]:hover{{background:rgba(255,255,255,0.12);transform:translateY(-1px)}}
.stTabs [aria-selected="true"]{{
  background:{tab_sel}!important;
  border-color:{badge_border}!important;
  box-shadow:0 4px 16px rgba(0,31,63,0.15)!important
}}
.stAlert{{
  background:{card_bg}!important;backdrop-filter:blur(15px)!important;
  border-radius:14px!important;border-left:4px solid!important;color:{text_color}!important
}}
.dataframe{{
  background:{card_bg}!important;border:1px solid {card_border}!important;
  border-radius:14px!important;color:{text_color}!important
}}
.dataframe th{{background:{kpi_bg}!important;color:{text_color}!important;font-weight:800!important;font-size:.8rem!important;text-transform:uppercase;letter-spacing:.5px}}
.dataframe td{{color:{text_color}!important;font-size:.85rem!important}}
h1,h2,h3,h4,h5,h6{{color:{title_color};font-weight:800}}
#MainMenu,footer,header,.stDeployButton{{visibility:hidden}}
[data-testid="stSidebar"]{{display:none}}
div[data-testid="stTextInput"]>div{{background:transparent!important;border:none!important;box-shadow:none!important;padding:0!important}}
div[data-testid="stTextInput"]{{background:transparent!important;border:none!important}}

/* ── STAT RING ── */
.stat-ring{{
  width:80px;height:80px;border-radius:50%;
  display:flex;align-items:center;justify-content:center;
  font-weight:900;font-size:1.3rem;margin:0 auto .5rem;
  border:3px solid;transition:all .4s
}}

/* ── HEATMAP ── */
.heatmap-cell{{
  display:inline-block;width:28px;height:28px;border-radius:6px;
  margin:2px;transition:transform .2s;cursor:default;
  display:flex;align-items:center;justify-content:center;
  font-size:.6rem;font-weight:700
}}
.heatmap-cell:hover{{transform:scale(1.3);z-index:10;position:relative}}

/* ── TOOLTIP ── */
[data-tooltip]{{position:relative;cursor:help}}
[data-tooltip]::after{{
  content:attr(data-tooltip);position:absolute;bottom:calc(100% + 8px);left:50%;
  transform:translateX(-50%);background:rgba(0,0,0,0.85);color:white;
  padding:.4rem .8rem;border-radius:8px;font-size:.72rem;font-weight:500;
  white-space:nowrap;pointer-events:none;opacity:0;transition:opacity .2s;z-index:100
}}
[data-tooltip]:hover::after{{opacity:1}}

@media(max-width:768px){{
  .main-title{{font-size:2rem}}
  .main-content{{margin-top:160px;padding:1rem 1.2rem}}
  .access-bar{{flex-direction:row;flex-wrap:wrap;position:static;border-radius:14px;border:1px solid {card_border};margin:1rem 0}}
  .top-navbar{{flex-direction:column;gap:.5rem;padding:1rem}}
}}
</style>""", unsafe_allow_html=True)

# ── ACCESSIBILITY TOOLBAR ──────────────────────────────────────────────
def render_accessibility_bar():
    theme = st.session_state.get('theme', 'dark')
    font_size = st.session_state.get('font_size', 'medium')
    hc = st.session_state.get('high_contrast', False)

    theme_icon = "☀️" if theme == 'dark' else "🌙"
    theme_label = "Claro" if theme == 'dark' else "Escuro"

    font_sizes = [('P-','small'),('P','medium'),('P+','large'),('P++','xlarge')]
    font_btns = "".join(
        f"<button class='access-btn {'active' if font_size==fs else ''}' "
        f"onclick=\"parent.postMessage({{type:'streamlit:setComponentValue',value:'font_{fs}'}}, '*')\">"
        f"{label}</button>"
        for label, fs in font_sizes
    )

    st.markdown(f"""
<div class='access-bar' role='toolbar' aria-label='Ferramentas de acessibilidade'>
  <div class='access-section-label'>Texto</div>
  <button class='access-btn {"active" if font_size=="small" else ""}' 
    title='Texto pequeno'
    onclick="document.querySelector('.stApp').style.fontSize='13px'">A-</button>
  <button class='access-btn {"active" if font_size=="medium" else ""}' 
    title='Texto médio'
    onclick="document.querySelector('.stApp').style.fontSize='15px'">A</button>
  <button class='access-btn {"active" if font_size=="large" else ""}' 
    title='Texto grande'
    onclick="document.querySelector('.stApp').style.fontSize='17px'">A+</button>
  <button class='access-btn {"active" if font_size=="xlarge" else ""}' 
    title='Texto extra grande'
    onclick="document.querySelector('.stApp').style.fontSize='20px'">A++</button>
  <div class='divider' style='margin:.3rem 0'></div>
  <div class='access-section-label'>Tema</div>
  <div class='access-section-label' style='font-size:.68rem;opacity:.6'>{theme_icon} {'Escuro' if theme=='dark' else 'Claro'}</div>
  <div class='access-section-label' style='font-size:.62rem;opacity:.4'>Use o botão abaixo</div>
</div>
<script>
function speak(text) {{
  if ('speechSynthesis' in window) {{
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.lang = 'pt-BR';u.rate=0.88;u.pitch=1;
    const voices = window.speechSynthesis.getVoices();
    const ptVoice = voices.find(v => v.lang && v.lang.startsWith('pt'));
    if(ptVoice) u.voice = ptVoice;
    window.speechSynthesis.speak(u);
  }}
}}
function stopSpeak() {{
  if ('speechSynthesis' in window) window.speechSynthesis.cancel();
}}
</script>
""", unsafe_allow_html=True)

# ── HELPERS ───────────────────────────────────────────────────────────
def kpi(label, value, sub="", color="#a7e6ff", trend=""):
    trend_html = f"<div class='kpi-trend' style='color:{color}'>{trend}</div>" if trend else ""
    return (f"<div class='kpi-card'>"
            f"<div class='kpi-lbl'>{label}</div>"
            f"<div class='kpi-val' style='color:{color}'>{value}</div>"
            f"{'<div class=kpi-sub>'+sub+'</div>' if sub else ''}"
            f"{trend_html}"
            f"</div>")

def insight(text):
    return f"<div class='insight'>{text}</div>"

def divider():
    return "<div class='divider'></div>"

def pbar(pct, color="#60a5fa"):
    w = min(100, max(0, pct*100))
    return f"<div class='pbar-o'><div class='pbar-i' style='width:{w:.1f}%;background:{color}'></div></div>"

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
         "categoria":"Pintura","tecnica":"Óleo sobre tela","dimensoes":"349.3 × 776.6 cm",
         "descricao":"Obra de protesto contra os bombardeios da Guerra Civil Espanhola",
         "imagem":"https://upload.wikimedia.org/wikipedia/en/7/74/PicassoGuernica.jpg"},
        {"id":2,"titulo":"A Noite Estrelada","artista":"Vincent van Gogh","ano":"1889",
         "categoria":"Pintura","tecnica":"Óleo sobre tela","dimensoes":"73.7 × 92.1 cm",
         "descricao":"Paisagem noturna com céu turbilhonante sobre vila",
         "imagem":"https://upload.wikimedia.org/wikipedia/commons/thumb/e/ea/Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg/1200px-Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg"},
        {"id":3,"titulo":"Mona Lisa","artista":"Leonardo da Vinci","ano":"1503",
         "categoria":"Pintura","tecnica":"Óleo sobre madeira","dimensoes":"77 × 53 cm",
         "descricao":"Retrato de mulher com sorriso enigmático usando técnica de sfumato",
         "imagem":"https://upload.wikimedia.org/wikipedia/commons/thumb/e/ec/Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_retouched.jpg/800px-Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_retouched.jpg"}
    ]
    obras = load_json_file(OBRAS_FILE, default)
    if not obras:
        save_json_file(OBRAS_FILE, default)
        return default
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
body{{font-family:'Inter',sans-serif;background:linear-gradient(135deg,#000,#001F3F);padding:40px;color:white}}
.c{{max-width:900px;margin:0 auto;background:rgba(255,255,255,.15);padding:50px;border-radius:24px;border:1px solid rgba(255,255,255,.3)}}
h1{{text-align:center;margin-bottom:15px;font-size:2rem;font-weight:900}}
.hi{{text-align:center;margin-bottom:35px;opacity:.9}}
.ab{{background:rgba(167,230,255,.25);border:1px solid rgba(167,230,255,.5);color:#a7e6ff;padding:.3rem 1rem;border-radius:50px;font-weight:700;display:inline-block}}
.qb{{margin:22px 0;padding:18px 22px;background:rgba(255,255,255,.1);border-left:4px solid rgba(255,255,255,.5);border-radius:12px}}
.q{{font-weight:800;margin-bottom:8px;font-size:.9rem;text-transform:uppercase;letter-spacing:.5px;opacity:.7}}.a{{line-height:1.7;opacity:.95;font-size:1rem}}
.ft{{text-align:center;margin-top:40px;padding-top:18px;border-top:1px solid rgba(255,255,255,.2);opacity:.5;font-size:.82rem}}</style></head>
<body><div class="c"><h1>Respostas do Questionário</h1>
<div class="hi"><p>Usuário Anônimo: <span class="ab">🐾 {animal}</span></p>
<p style="margin-top:6px;opacity:.6">Data: {ui.get('timestamp','N/A')}</p></div>
<div class="qb"><div class="q">1. Nível de familiaridade com museus</div><div class="a">{ui.get('q1','N/A')}</div></div>
<div class="qb"><div class="q">2. Conhecimento sobre documentação museológica</div><div class="a">{ui.get('q2','N/A')}</div></div>
<div class="qb"><div class="q">3. O que você entende por 'tags'?</div><div class="a">{ui.get('q3','N/A')}</div></div>
<div class="ft">Sistema Folksonomia Digital — Ctrl+P → Salvar como PDF</div></div></body></html>"""

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
body{{font-family:'Inter',sans-serif;background:linear-gradient(135deg,#000,#001F3F);padding:40px;color:white}}
.c{{max-width:1100px;margin:0 auto;background:rgba(255,255,255,.15);padding:50px;border-radius:24px;border:1px solid rgba(255,255,255,.3)}}
h1,h2{{font-weight:900}}h1{{text-align:center;margin-bottom:15px;font-size:2rem}}
.hi{{text-align:center;margin-bottom:28px;opacity:.9}}
.ab{{background:rgba(167,230,255,.25);border:1px solid rgba(167,230,255,.5);color:#a7e6ff;padding:.3rem 1rem;border-radius:50px;font-weight:700;display:inline-block}}
.stats{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin:22px 0}}
.sb{{background:rgba(255,255,255,.14);border:1px solid rgba(255,255,255,.28);padding:18px;border-radius:12px;text-align:center}}
.sv{{font-size:2.4rem;font-weight:900}}.sl{{font-size:.78rem;text-transform:uppercase;letter-spacing:1.5px;margin-top:7px;opacity:.8}}
table{{width:100%;border-collapse:collapse;margin:18px 0}}
th,td{{padding:13px;text-align:left;border-bottom:1px solid rgba(255,255,255,.12)}}
th{{background:rgba(255,255,255,.16);font-weight:800;text-transform:uppercase;font-size:.78rem;letter-spacing:.5px}}
tr:nth-child(even){{background:rgba(255,255,255,.04)}}
.ft{{text-align:center;margin-top:38px;padding-top:18px;border-top:1px solid rgba(255,255,255,.2);opacity:.5;font-size:.82rem}}</style></head>
<body><div class="c"><h1>Relatório de Tags</h1>
<div class="hi"><p>Usuário Anônimo: <span class="ab">🐾 {animal}</span></p>
<p style="margin-top:6px;opacity:.6">Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}</p></div>
<div class="stats">
  <div class="sb"><div class="sv">{len(ut)}</div><div class="sl">Total de Tags</div></div>
  <div class="sb"><div class="sv">{ut['tag'].nunique()}</div><div class="sl">Tags Únicas</div></div>
  <div class="sb"><div class="sv">{ut['obra_id'].nunique()}</div><div class="sl">Obras Etiquetadas</div></div>
</div>
<h2 style="margin:28px 0 14px;font-size:1.4rem">Todas as Tags</h2>
<table><thead><tr><th>#</th><th>Obra</th><th>Tag</th><th>Data/Hora</th></tr></thead><tbody>{rows}</tbody></table>
<h2 style="margin:28px 0 14px;font-size:1.4rem">Top 10 Tags</h2>
<table><thead><tr><th>Pos.</th><th>Tag</th><th>Freq.</th></tr></thead><tbody>{top}</tbody></table>
<div class="ft">Sistema Folksonomia Digital — Ctrl+P → Salvar como PDF</div></div></body></html>"""

# ── HEADER ────────────────────────────────────────────────────────────
def show_header():
    st.markdown(
        "<div class='top-navbar'>"
        "<div>"
        "<div class='navbar-logo'>📚 Folksonomia Digital</div>"
        "<div class='navbar-sub'>Sistema colaborativo de catalogação de arte</div>"
        "</div>"
        "</div>", unsafe_allow_html=True)

# ── MAIN ──────────────────────────────────────────────────────────────
def main():
    for k, v in [
        ('user_id', gen_uid()), ('animal_name', generate_animal_name()),
        ('step', 'intro'), ('answers', {}),
        ('theme', 'dark'), ('font_size', 'medium'), ('high_contrast', False),
        ('view_mode', 'grid'), ('filter_tags', [])
    ]:
        if k not in st.session_state:
            st.session_state[k] = v

    load_css()
    render_accessibility_bar()

    try: check_admin()
    except Exception as e: st.error(f"Erro ao inicializar: {e}")

    # Accessibility controls in sidebar-style columns at top
    with st.container():
        a1, a2, a3, a4, a5 = st.columns([1,1,1,1,4])
        with a1:
            if st.button("🌙/☀️ Tema", help="Alternar tema claro/escuro"):
                st.session_state['theme'] = 'light' if st.session_state['theme']=='dark' else 'dark'
                st.rerun()
        with a2:
            if st.button(" A+", help="Aumentar tamanho da fonte"):
                sizes = ['small','medium','large','xlarge']
                idx = sizes.index(st.session_state.get('font_size','medium'))
                st.session_state['font_size'] = sizes[min(idx+1, 3)]
                st.rerun()
        with a3:
            if st.button(" A-", help="Diminuir tamanho da fonte"):
                sizes = ['small','medium','large','xlarge']
                idx = sizes.index(st.session_state.get('font_size','medium'))
                st.session_state['font_size'] = sizes[max(idx-1, 0)]
                st.rerun()
        with a4:
            hc_label = " Normal" if st.session_state.get('high_contrast') else " Contraste"
            if st.button(hc_label, help="Alto contraste"):
                st.session_state['high_contrast'] = not st.session_state.get('high_contrast', False)
                st.rerun()

    if st.session_state['step'] != 'completed':
        show_intro()
    else:
        show_header()
        st.markdown("<div class='main-content'>", unsafe_allow_html=True)
        t1, t2 = st.tabs(["  Explorar Obras", "  Área Administrativa"])
        with t1: show_obras()
        with t2: show_admin()
        st.markdown("</div>", unsafe_allow_html=True)

# ── INTRO ─────────────────────────────────────────────────────────────
def show_intro():
    st.markdown("<div class='main-content'>", unsafe_allow_html=True)
    st.markdown("<h1 class='main-title'>Sistema Folksonomia Digital</h1>", unsafe_allow_html=True)
    st.markdown(
        "<p class='subtitle'>Sistema colaborativo de catalogação de obras de arte<br>"
        "Contribua com suas perspectivas únicas sobre cada obra</p>", unsafe_allow_html=True)
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.markdown("<h2 style='text-align:center;margin-bottom:2rem;font-size:1.6rem'>"
                " Questionário de Acesso</h2>", unsafe_allow_html=True)
    with st.form("intro_form"):
        c1, c2 = st.columns(2)
        with c1:
            q1 = st.selectbox("1. Nível de familiaridade com museus:",
                ["Nunca visito museus","Visito raramente","Visito ocasionalmente","Visito frequentemente"])
            q2 = st.selectbox("2. Conhecimento sobre documentação museológica:",
                ["Nunca ouvi falar","Já ouvi, mas não sei o que é","Tenho uma ideia básica","Conheço bem o tema"])
        with c2:
            q3 = st.text_area(
                "3. O que você entende por 'tags' ou etiquetas digitais aplicadas a acervo?",
                max_chars=500, height=195,
                placeholder="Descreva sua compreensão sobre o conceito de tags em sistemas digitais...")
        _, cb, _ = st.columns([1,1,1])
        with cb:
            submit = st.form_submit_button(" Acessar a Plataforma", use_container_width=True)
        if submit:
            if not q3.strip():
                st.error("Por favor, responda todas as perguntas para continuar!")
            else:
                st.session_state['answers'] = {"q1":q1,"q2":q2,"q3":q3}
                save_answers(st.session_state['user_id'], st.session_state['animal_name'],
                             st.session_state['answers'])
                st.session_state['step'] = 'completed'
                st.success(" Questionário completo! Acesso liberado.")
                st.balloons()
                st.rerun()
    st.markdown("</div></div>", unsafe_allow_html=True)

# ── GALERIA ───────────────────────────────────────────────────────────
def show_obras():
    st.markdown("<h1 class='main-title'> Galeria de Obras de Arte</h1>", unsafe_allow_html=True)
    st.markdown("<p class='subtitle'>Explore, filtre e contribua com suas tags descritivas</p>",
                unsafe_allow_html=True)
    obras = load_obras()
    tdf   = all_tags()
    if not obras:
        st.info("Nenhuma obra cadastrada.")
        return

    # ── PAINEL DE FILTROS AVANÇADOS ──
    with st.expander(" Filtros Avançados", expanded=True):
        st.markdown("<div class='filter-panel'>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        with col1:
            busca_titulo = st.text_input(" Buscar por título:", placeholder="Ex: Guernica…")
            busca_artista = st.text_input(" Filtrar por artista:", placeholder="Ex: Van Gogh…")
        with col2:
            anos_disponiveis = sorted(set(str(o.get('ano','')) for o in obras if o.get('ano')))
            ano_sel = st.multiselect(" Ano(s):", anos_disponiveis)
            categorias = sorted(set(o.get('categoria','Pintura') for o in obras))
            cat_sel = st.multiselect(" Categoria:", categorias)
        with col3:
            if not tdf.empty:
                all_unique_tags = sorted(tdf['tag'].unique().tolist())
                tags_filtro = st.multiselect(" Obras com estas tags:", all_unique_tags[:50])
            else:
                tags_filtro = []
            sord = st.selectbox(" Ordenar por:", [
                "Número ↑","Número ↓","Título A-Z","Título Z-A",
                "Mais tagueadas","Menos tagueadas","Ano ↑","Ano ↓"
            ])
        st.markdown("</div>", unsafe_allow_html=True)

    # ── MODO DE VISUALIZAÇÃO ──
    vc1, vc2, vc3 = st.columns([2,1,3])
    with vc1:
        view_col1, view_col2 = st.columns(2)
        with view_col1:
            if st.button("⊞ Grade", use_container_width=True):
                st.session_state['view_mode'] = 'grid'
                st.rerun()
        with view_col2:
            if st.button("☰ Lista", use_container_width=True):
                st.session_state['view_mode'] = 'list'
                st.rerun()
    view_mode = st.session_state.get('view_mode', 'grid')

    # ── APLICAR FILTROS ──
    filtered = obras[:]
    if busca_titulo.strip():
        filtered = [o for o in filtered if busca_titulo.lower() in o['titulo'].lower()]
    if busca_artista.strip():
        filtered = [o for o in filtered if busca_artista.lower() in o.get('artista','').lower()]
    if ano_sel:
        filtered = [o for o in filtered if str(o.get('ano','')) in ano_sel]
    if cat_sel:
        filtered = [o for o in filtered if o.get('categoria','Pintura') in cat_sel]
    if tags_filtro and not tdf.empty:
        obras_com_tags = set()
        for tag in tags_filtro:
            obras_com_tags |= set(tdf[tdf['tag']==tag]['obra_id'].tolist())
        filtered = [o for o in filtered if o['id'] in obras_com_tags]

    # Tags count per obra
    tag_count_per_obra = {}
    if not tdf.empty:
        tc = tdf.groupby('obra_id').size().to_dict()
        tag_count_per_obra = tc

    def sort_key(o):
        tc = tag_count_per_obra.get(o['id'], 0)
        try: yr = int(o.get('ano', 0))
        except: yr = 0
        if sord == "Número ↑": return o['id']
        if sord == "Número ↓": return -o['id']
        if sord == "Título A-Z": return o['titulo']
        if sord == "Título Z-A": return [-ord(c) for c in o['titulo']]
        if sord == "Mais tagueadas": return -tc
        if sord == "Menos tagueadas": return tc
        if sord == "Ano ↑": return yr
        if sord == "Ano ↓": return -yr
        return o['id']

    try:
        filtered = sorted(filtered, key=sort_key)
    except: pass

    # ── CONTADOR ──
    st.markdown(
        f"<div style='text-align:center;margin:1.5rem 0;font-size:1rem;font-weight:600'>"
        f"Exibindo <strong style='font-size:1.4rem;color:#60a5fa'>{len(filtered)}</strong> "
        f"de {len(obras)} obra(s) · Modo: {'Grade' if view_mode=='grid' else 'Lista'}"
        f"</div>", unsafe_allow_html=True)

    if not filtered:
        st.warning("Nenhuma obra encontrada com os filtros aplicados.")
        return

    # ── RENDERIZAR ──
    if view_mode == 'grid':
        render_grid(filtered, tag_count_per_obra, tdf)
    else:
        render_list(filtered, tag_count_per_obra, tdf)

def render_grid(obras, tag_count_per_obra, tdf):
    cols = st.columns(3)
    for i, obra in enumerate(obras):
        with cols[i % 3]:
            tc = tag_count_per_obra.get(obra['id'], 0)
            audio_desc = AUDIO_DESCRIPTIONS.get(obra['id'], obra.get('descricao','Sem descrição disponível.'))

            st.markdown(f"""
<div class='obra-card'>
  <span class='obra-num'>#{obra['id']}</span>
  <img src='{obra['imagem']}' alt='{obra['titulo']} — {obra.get('artista','')}' />
  <div style='padding:1.2rem'>
    <h3 style='font-size:1rem;font-weight:800;margin-bottom:.2rem'>{obra['titulo']}</h3>
    <p style='font-size:.82rem;opacity:.65;margin-bottom:.3rem'>
      {obra.get('artista','')} · {obra.get('ano','')}
    </p>
    <p style='font-size:.78rem;opacity:.5'>{obra.get('categoria','Pintura')} · {obra.get('tecnica','')}</p>
    <div style='margin-top:.5rem'>
      <span class='tag-badge tag-blue'> {tc} tags</span>
    </div>
  </div>
</div>""", unsafe_allow_html=True)

            # Botão de áudio descrição
            if st.button(f"🔊 Áudio-Descrição", key=f"audio_{obra['id']}", use_container_width=True,
                         help="Ouvir descrição acessível da obra"):
                st.session_state[f'play_audio_{obra["id"]}'] = audio_desc
                st.rerun()

            if st.session_state.get(f'play_audio_{obra["id"]}'):
                desc = st.session_state[f'play_audio_{obra["id"]}']
                st.markdown(f"""
<div class='sc sc-g' style='margin:.3rem 0;padding:.8rem'>
  <div style='font-size:.8rem;font-weight:700;color:#6ee7b7;margin-bottom:.4rem'>
    🔊 Áudio-Descrição — {obra['titulo']}
  </div>
  <p style='font-size:.8rem;line-height:1.65;opacity:.9'>{desc}</p>
  <button onclick="speak(`{desc.replace('`',"'")}`)"
    style='margin-top:.5rem;background:rgba(52,211,153,.2);border:1px solid rgba(52,211,153,.4);
    color:#6ee7b7;padding:.3rem .9rem;border-radius:50px;font-size:.78rem;font-weight:700;cursor:pointer'>
    ▶ Reproduzir
  </button>
  <button onclick="stopSpeak()"
    style='margin-top:.5rem;margin-left:.4rem;background:rgba(248,113,113,.15);
    border:1px solid rgba(248,113,113,.35);color:#fca5a5;
    padding:.3rem .9rem;border-radius:50px;font-size:.78rem;font-weight:700;cursor:pointer'>
    ⏹ Parar
  </button>
</div>""", unsafe_allow_html=True)
                if st.button("✕ Fechar descrição", key=f"close_audio_{obra['id']}"):
                    del st.session_state[f'play_audio_{obra["id"]}']
                    st.rerun()

            if st.button(" Adicionar Tag", key=f"btn_{obra['id']}", use_container_width=True):
                st.session_state['selected_obra'] = obra
                st.rerun()

            if ('selected_obra' in st.session_state and
                    st.session_state['selected_obra']['id'] == obra['id']):
                render_tag_form(obra)

            ut = get_obra_user_tags(obra['id'], st.session_state['user_id'])
            if not ut.empty:
                st.markdown("**Suas Tags:**")
                st.markdown("".join(
                    f"<span class='tag-badge'>{r['tag']} "
                    f"<span style='opacity:.5;font-size:.75rem'>({r['count']}×)</span></span>"
                    for _, r in ut.iterrows()
                ), unsafe_allow_html=True)
            else:
                st.markdown("<div class='sc' style='padding:.6rem;text-align:center;font-size:.82rem;opacity:.55'>"
                            "Você ainda não criou tags para esta obra</div>", unsafe_allow_html=True)

def render_list(obras, tag_count_per_obra, tdf):
    for obra in obras:
        tc = tag_count_per_obra.get(obra['id'], 0)
        audio_desc = AUDIO_DESCRIPTIONS.get(obra['id'], obra.get('descricao','Sem descrição.'))
        all_obra_tags = []
        if not tdf.empty:
            obra_tags = tdf[tdf['obra_id']==obra['id']]['tag'].value_counts().head(5)
            all_obra_tags = [f"<span class='tag-badge' style='font-size:.72rem'>{t}</span>" for t in obra_tags.index]

        st.markdown(f"""
<div class='obra-list-item'>
  <img src='{obra['imagem']}' alt='{obra['titulo']}' class='obra-list-img'/>
  <div style='flex:1'>
    <div style='display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px'>
      <div>
        <h3 style='font-size:1.05rem;font-weight:800;margin-bottom:.25rem'>
          #{obra['id']} · {obra['titulo']}
        </h3>
        <p style='font-size:.85rem;opacity:.7;margin-bottom:.2rem'>
          {obra.get('artista','')} · {obra.get('ano','')}
        </p>
        <p style='font-size:.78rem;opacity:.5'>{obra.get('categoria','Pintura')} · {obra.get('tecnica','')} · {obra.get('dimensoes','')}</p>
      </div>
      <span class='tag-badge tag-blue'> {tc} tags</span>
    </div>
    <p style='font-size:.82rem;opacity:.65;margin:.5rem 0;line-height:1.6'>
      {obra.get('descricao','')}
    </p>
    <div>{''.join(all_obra_tags) if all_obra_tags else "<span style='font-size:.78rem;opacity:.4'>Sem tags ainda</span>"}</div>
  </div>
</div>""", unsafe_allow_html=True)

        lc1, lc2, lc3 = st.columns([1,1,2])
        with lc1:
            if st.button(" Tag", key=f"list_btn_{obra['id']}", use_container_width=True):
                st.session_state['selected_obra'] = obra
                st.rerun()
        with lc2:
            if st.button("🔊 Áudio", key=f"list_audio_{obra['id']}", use_container_width=True):
                st.session_state[f'play_audio_{obra["id"]}'] = audio_desc
                st.rerun()

        if st.session_state.get(f'play_audio_{obra["id"]}'):
            desc = st.session_state[f'play_audio_{obra["id"]}']
            st.markdown(f"""
<div class='sc sc-g' style='margin:.3rem 0'>
  <strong style='color:#6ee7b7;font-size:.82rem'>🔊 Áudio-Descrição</strong>
  <p style='font-size:.82rem;margin:.4rem 0;line-height:1.6'>{desc}</p>
  <button onclick="speak(`{desc.replace('`',"'")}`)"
    style='background:rgba(52,211,153,.2);border:1px solid rgba(52,211,153,.4);color:#6ee7b7;
    padding:.28rem .8rem;border-radius:50px;font-size:.75rem;font-weight:700;cursor:pointer'>
    ▶ Reproduzir</button>
  <button onclick="stopSpeak()"
    style='margin-left:.4rem;background:rgba(248,113,113,.15);border:1px solid rgba(248,113,113,.35);
    color:#fca5a5;padding:.28rem .8rem;border-radius:50px;font-size:.75rem;font-weight:700;cursor:pointer'>
    ⏹ Parar</button>
</div>""", unsafe_allow_html=True)
            if st.button("✕", key=f"close_list_audio_{obra['id']}"):
                del st.session_state[f'play_audio_{obra["id"]}']
                st.rerun()

        if ('selected_obra' in st.session_state and
                st.session_state['selected_obra']['id'] == obra['id']):
            render_tag_form(obra)

        ut = get_obra_user_tags(obra['id'], st.session_state['user_id'])
        if not ut.empty:
            st.markdown("**Suas Tags:** " + "".join(
                f"<span class='tag-badge'>{r['tag']} ({r['count']}×)</span>"
                for _, r in ut.iterrows()
            ), unsafe_allow_html=True)

def render_tag_form(obra):
    with st.form(f"tf_{obra['id']}"):
        tag = st.text_input("Nova tag:", key=f"t_{obra['id']}",
                            placeholder="Ex: melancólico, azul noturno, abstrato…")
        sugestoes = ["guerra","paz","dor","esperança","escuridão","luz","natureza",
                     "movimento","silêncio","beleza","mistério","emoção"]
        st.markdown("**Sugestões:** " + " ".join(
            f"<span class='filter-chip'>{s}</span>" for s in sugestoes[:8]
        ), unsafe_allow_html=True)
        ca, cb = st.columns(2)
        with ca: sub = st.form_submit_button(" Enviar Tag", use_container_width=True)
        with cb: can = st.form_submit_button("✕ Cancelar", use_container_width=True)
        if sub and tag:
            if len(tag.strip()) < 2:
                st.error("Tag deve ter ao menos 2 caracteres.")
            else:
                save_tag(st.session_state['user_id'], obra['id'], tag)
                st.success(f" Tag '{tag}' adicionada com sucesso!")
                del st.session_state['selected_obra']
                st.rerun()
        if can:
            del st.session_state['selected_obra']
            st.rerun()

# ── ADMIN ─────────────────────────────────────────────────────────────
def show_admin():
    if 'admin_logged_in' not in st.session_state:
        st.session_state['admin_logged_in'] = False
    if not st.session_state['admin_logged_in']:
        st.markdown("<h1 class='main-title'>⚙️ Área Administrativa</h1>", unsafe_allow_html=True)
        _, c2, _ = st.columns([1,1,1])
        with c2:
            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
            st.markdown("<h2 style='text-align:center;margin-bottom:1.5rem'>🔐 Login</h2>", unsafe_allow_html=True)
            with st.form("login"):
                username = st.text_input("Usuário:", placeholder="Digite seu usuário")
                password = st.text_input("Senha:", type="password", placeholder="Digite sua senha")
                sub = st.form_submit_button("Entrar no Sistema", use_container_width=True)
                if sub:
                    if check_login(username, password):
                        st.session_state['admin_logged_in'] = True
                        st.session_state['admin_username'] = username
                        st.success(" Login realizado!")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error(" Credenciais inválidas. Acesso negado.")
            st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.markdown(
            f"<h1 class='main-title'> Dashboard Administrativo</h1>"
            f"<p class='subtitle'>Bem-vindo, <strong>{st.session_state.get('admin_username','Admin')}</strong></p>",
            unsafe_allow_html=True)
        tabs = st.tabs([
            " Visão Geral",
            " Análise de Tags",
            " Conexões",
            " Coocorrências",
            " Usuários",
            " Obras",
            " Exportar"
        ])
        with tabs[0]: tab_overview()
        with tabs[1]: tab_tags()
        with tabs[2]: tab_connections()
        with tabs[3]: tab_cooccurrence()
        with tabs[4]: tab_users_quest()
        with tabs[5]: tab_obras()
        with tabs[6]: tab_export()
        _, c2, _ = st.columns([1,1,1])
        with c2:
            if st.button(" Sair do Sistema", use_container_width=True):
                st.session_state['admin_logged_in'] = False
                st.rerun()

# ═══════════════════════════════════════════════════════════════════════
# ABA 1 — VISÃO GERAL
# ═══════════════════════════════════════════════════════════════════════
def tab_overview():
    tdf = all_tags()
    udf = all_users()
    obs = load_obras()

    st.markdown("###  Métricas Gerais do Sistema")
    total  = len(tdf) if not tdf.empty else 0
    unicas = tdf['tag'].nunique() if not tdf.empty else 0
    nusers = udf['user_id'].nunique() if not udf.empty else 0
    nobs   = len(obs)
    obs_ct = tdf['obra_id'].nunique() if not tdf.empty else 0
    ent    = tag_entropy(tdf['tag'].value_counts().to_dict()) if not tdf.empty else 0

    c1,c2,c3,c4,c5,c6 = st.columns(6)
    for col, lbl, val, sub, clr in [
        (c1,"Total Tags",     total,   "registros","#60a5fa"),
        (c2,"Tags Únicas",    unicas,  f"{unicas/total:.0%} do total" if total else "—","#a78bfa"),
        (c3,"Participantes",  nusers,  "usuários ativos","#34d399"),
        (c4,"Obras",          nobs,    f"{obs_ct} com tags","#fbbf24"),
        (c5,"Média/Usuário",  f"{total/nusers:.1f}" if nusers else "—","tags por participante","#f472b6"),
        (c6,"Entropia",       f"{ent:.2f}","bits — diversidade","#fb923c"),
    ]:
        with col: st.markdown(kpi(lbl,val,sub,clr), unsafe_allow_html=True)

    st.markdown(divider(), unsafe_allow_html=True)

    if not tdf.empty:
        st.markdown("###  Resumo por Obra")
        od = {o['id']:o['titulo'] for o in obs}
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("####  Top 15 Tags Mais Usadas")
            top = tdf['tag'].value_counts().head(15).reset_index()
            top.columns = ['Tag','Qtd']
            top['%'] = (top['Qtd']/top['Qtd'].sum()*100).round(1)
            st.dataframe(top, use_container_width=True, hide_index=True)
        with c2:
            st.markdown("####  Engajamento por Obra")
            ot = tdf.groupby('obra_id').agg(
                Tags=('tag','count'),
                Tags_Unicas=('tag','nunique'),
                Usuarios=('user_id','nunique')
            ).reset_index()
            ot['Obra'] = ot['obra_id'].map(od)
            ot['Diversidade'] = (ot['Tags_Unicas']/ot['Tags']).round(2)
            st.dataframe(
                ot[['Obra','Tags','Tags_Unicas','Usuarios','Diversidade']]
                .sort_values('Tags',ascending=False).rename(columns={
                    'Tags':'Total','Tags_Unicas':'Únicas','Usuarios':'Usuários'
                }),
                use_container_width=True, hide_index=True)

    st.markdown(divider(), unsafe_allow_html=True)

    if not udf.empty and not tdf.empty:
        st.markdown("### 👥 Participantes Anônimos")
        uct = tdf.groupby('user_id').size().reset_index(name='tags')
        uuq = tdf.groupby('user_id')['tag'].nunique().reset_index(name='unicas')
        m   = udf.merge(uct,on='user_id',how='left').merge(uuq,on='user_id',how='left').fillna(0)
        max_tags = m['tags'].max() if m['tags'].max() > 0 else 1
        for _, row in m.iterrows():
            animal = row.get('animal_name','?')
            ts     = row.get('timestamp','N/A')
            nt, nu = int(row['tags']), int(row['unicas'])
            p      = nu/nt if nt>0 else 0
            bar_w  = nt/max_tags
            st.markdown(
                f"<div class='sc sc-b' style='padding:.85rem 1.3rem;margin:.25rem 0'>"
                f"<div style='display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px'>"
                f"<div><span class='animal-badge'>🐾 {animal}</span>"
                f"<span style='opacity:.4;font-size:.72rem;margin-left:10px'>Acesso: {ts}</span></div>"
                f"<div style='text-align:right;min-width:200px'>"
                f"<span style='font-weight:800;color:#60a5fa'>{nt}</span> tags · "
                f"<span style='opacity:.6;font-size:.8rem'>{nu} únicas · TTR: {p:.0%}</span>"
                f"{pbar(bar_w,'#60a5fa')}"
                f"</div></div></div>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════
# ABA 2 — ANÁLISE DE TAGS (Frequência + Temporal + Diversidade)
# ═══════════════════════════════════════════════════════════════════════
def tab_tags():
    tdf = all_tags()
    if tdf.empty:
        st.info("Nenhuma tag disponível.")
        return

    st.markdown("###  Análise Detalhada de Tags")
    t1, t2, t3 = st.tabs([" Frequência & Vocabulário", " Evolução Temporal", " Diversidade & Entropia"])

    # ─── FREQUÊNCIA ────────────────────────────────────────────────────
    with t1:
        freq = tdf['tag'].value_counts().reset_index()
        freq.columns = ['Tag','Frequência']
        total_usos = freq['Frequência'].sum()
        freq['% do Total']  = (freq['Frequência']/total_usos*100).round(2)
        freq['% Acumulada'] = freq['% do Total'].cumsum().round(2)
        freq['Comprimento'] = freq['Tag'].str.len()
        freq['Palavras']    = freq['Tag'].str.split().str.len()
        freq['Categoria']   = pd.cut(
            freq['Frequência'],
            bins=[0,1,2,5,10,99999],
            labels=['Hapax (1×)','Rara (2×)','Ocasional (3–5×)','Frequente (6–10×)','Muito Frequente (10+×)']
        )

        hapax  = (freq['Frequência']==1).sum()
        lei80  = (freq['% Acumulada']<=80).sum()
        ttr    = len(freq)/total_usos if total_usos else 0
        media_len = freq['Comprimento'].mean()
        multi_word = (freq['Palavras']>1).sum()

        c1,c2,c3,c4,c5,c6 = st.columns(6)
        for col, lbl, val, sub, clr in [
            (c1,"Vocabulário",     len(freq),"tags distintas","#60a5fa"),
            (c2,"Hapax Legomena", hapax,     f"{hapax/len(freq):.0%} vocab.","#f472b6"),
            (c3,"Lei de Zipf 80%",f"{lei80} tags","cobrem 80% usos","#34d399"),
            (c4,"TTR Global",     f"{ttr:.3f}","diversidade lexical","#fbbf24"),
            (c5,"Comprimento médio",f"{media_len:.1f}","caracteres/tag","#a78bfa"),
            (c6,"Tags compostas", multi_word,f"{multi_word/len(freq):.0%} do vocab.","#fb923c"),
        ]:
            with col: st.markdown(kpi(lbl,val,sub,clr), unsafe_allow_html=True)

        st.markdown(insight(
            f"<strong>Distribuição de Zipf:</strong> As <strong>{lei80} tags</strong> mais frequentes cobrem "
            f"80% de todos os usos. Existem <strong>{hapax} hapax legomena</strong> ({hapax/len(freq):.0%} do vocabulário). "
            f"TTR de <strong>{ttr:.3f}</strong> indica "
            f"{'alta' if ttr>0.5 else 'moderada' if ttr>0.25 else 'baixa'} diversidade lexical. "
            f"<strong>{multi_word} tags compostas</strong> ({multi_word/len(freq):.0%}) contêm múltiplas palavras."
        ), unsafe_allow_html=True)

        st.markdown(divider(), unsafe_allow_html=True)

        c1, c2 = st.columns([3,2])
        with c1:
            st.markdown("#### Top 25 Tags")
            st.bar_chart(tdf['tag'].value_counts().head(25))
        with c2:
            st.markdown("#### Distribuição por Comprimento")
            len_dist = freq['Comprimento'].value_counts().sort_index()
            st.bar_chart(len_dist.rename("Tags"))

        st.markdown(divider(), unsafe_allow_html=True)

        st.markdown("#### Tabela Completa de Frequências")
        cat_opts = list(freq['Categoria'].cat.categories)
        col1, col2, col3 = st.columns([2,1,1])
        with col1:
            cat_sel = st.multiselect("Filtrar por categoria:", cat_opts, default=cat_opts, key="fc")
        with col2:
            min_freq = st.number_input("Freq. mínima:", 1, 100, 1, key="min_f")
        with col3:
            busca_tag = st.text_input("Buscar tag:", key="bt")

        disp = freq[freq['Categoria'].isin(cat_sel)] if cat_sel else freq
        disp = disp[disp['Frequência'] >= min_freq]
        if busca_tag.strip():
            disp = disp[disp['Tag'].str.contains(busca_tag.lower().strip(), na=False)]
        st.dataframe(disp, use_container_width=True, hide_index=True)

        st.download_button(
            " Frequências (CSV)",
            freq.to_csv(index=False).encode('utf-8'),
            f"frequencias_{datetime.now().strftime('%Y%m%d')}.csv",
            "text/csv", use_container_width=True)

    # ─── TEMPORAL ──────────────────────────────────────────────────────
    with t2:
        try:
            tf = tdf.copy()
            tf['ts']    = pd.to_datetime(tf['timestamp'])
            tf['date']  = tf['ts'].dt.date
            tf['hora']  = tf['ts'].dt.hour
            tf['dow']   = tf['ts'].dt.day_name()
            tf['mes']   = tf['ts'].dt.month
            tf['ano']   = tf['ts'].dt.year

            dias_ativos = tf['date'].nunique()
            media_dia   = len(tf)/dias_ativos if dias_ativos else 0
            pico_dia    = tf.groupby('date').size()
            pico_val    = int(pico_dia.max()) if not pico_dia.empty else 0
            pico_dt     = str(pico_dia.idxmax()) if not pico_dia.empty else "—"

            c1,c2,c3,c4 = st.columns(4)
            with c1: st.markdown(kpi("Dias Ativos", dias_ativos,"","#60a5fa"), unsafe_allow_html=True)
            with c2: st.markdown(kpi("Média/Dia", f"{media_dia:.1f}","tags","#34d399"), unsafe_allow_html=True)
            with c3: st.markdown(kpi("Pico", pico_val,f"em {pico_dt}","#fbbf24"), unsafe_allow_html=True)
            with c4: st.markdown(kpi("Período", f"{dias_ativos}d","registrado","#a78bfa"), unsafe_allow_html=True)

            st.markdown(divider(), unsafe_allow_html=True)

            daily = tf.groupby('date').agg(
                Tags=('tag','count'),
                Tags_Unicas=('tag','nunique'),
                Usuarios=('user_id','nunique')
            ).reset_index().rename(columns={'date':'Data'})

            c1, c2 = st.columns(2)
            with c1:
                st.markdown("#### Tags criadas por dia")
                st.line_chart(daily.set_index('Data')['Tags'])
            with c2:
                st.markdown("#### Usuários ativos por dia")
                st.line_chart(daily.set_index('Data')['Usuarios'])

            st.markdown(divider(), unsafe_allow_html=True)

            meses_pt = {1:"Jan",2:"Fev",3:"Mar",4:"Abr",5:"Mai",6:"Jun",
                        7:"Jul",8:"Ago",9:"Set",10:"Out",11:"Nov",12:"Dez"}
            monthly = tf.groupby(['ano','mes']).agg(
                Tags=('tag','count'), Tags_Unicas=('tag','nunique'), Usuarios=('user_id','nunique')
            ).reset_index()
            monthly['Mês/Ano'] = monthly['mes'].map(meses_pt)+"/"+monthly['ano'].astype(str)
            monthly = monthly.sort_values(['ano','mes'])

            c1, c2 = st.columns(2)
            with c1:
                st.markdown("#### Distribuição mensal — Total")
                st.bar_chart(monthly.set_index('Mês/Ano')['Tags'])
            with c2:
                st.markdown("#### Distribuição mensal — Únicas")
                st.bar_chart(monthly.set_index('Mês/Ano')['Tags_Unicas'])

            st.markdown(divider(), unsafe_allow_html=True)

            c1, c2 = st.columns(2)
            with c1:
                st.markdown("#### Por hora do dia")
                st.bar_chart(tf['hora'].value_counts().sort_index().rename("Tags"))
            with c2:
                st.markdown("#### Por dia da semana")
                dow_order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
                dow_pt = {"Monday":"Seg","Tuesday":"Ter","Wednesday":"Qua","Thursday":"Qui",
                          "Friday":"Sex","Saturday":"Sáb","Sunday":"Dom"}
                dow_c = tf['dow'].value_counts().reindex(dow_order, fill_value=0)
                dow_c.index = [dow_pt.get(d,d) for d in dow_c.index]
                st.bar_chart(dow_c.rename("Tags"))

            st.markdown(divider(), unsafe_allow_html=True)
            st.markdown("#### Tabela Diária Detalhada")
            daily_full = tf.groupby('date').agg(
                Total=('tag','count'), Unicas=('tag','nunique'), Usuarios=('user_id','nunique'),
                Top_Tag=('tag', lambda x: x.value_counts().index[0])
            ).reset_index()
            daily_full.columns = ['Data','Tags Criadas','Tags Únicas','Usuários','Tag Mais Usada']
            st.dataframe(daily_full.sort_values('Data',ascending=False), use_container_width=True, hide_index=True)

        except Exception as e:
            st.info(f"Dados insuficientes para análise temporal: {e}")

    # ─── DIVERSIDADE & ENTROPIA ────────────────────────────────────────
    with t3:
        st.markdown("####  Análise de Diversidade e Entropia Lexical")
        obs = load_obras()
        od  = {o['id']:o['titulo'] for o in obs}

        freq = tdf['tag'].value_counts()
        ent_global = tag_entropy(freq.to_dict())

        c1,c2,c3,c4 = st.columns(4)
        with c1: st.markdown(kpi("Entropia Global",f"{ent_global:.3f}","bits — Shannon","#60a5fa"), unsafe_allow_html=True)
        with c2:
            max_ent = math.log2(len(freq)) if len(freq) > 1 else 1
            st.markdown(kpi("Entropia Máx. Possível",f"{max_ent:.3f}","bits (distribuição uniforme)","#34d399"), unsafe_allow_html=True)
        with c3:
            norm_ent = ent_global/max_ent if max_ent > 0 else 0
            st.markdown(kpi("Entropia Normalizada",f"{norm_ent:.3f}","0=monótono · 1=diverso","#fbbf24"), unsafe_allow_html=True)
        with c4:
            top1_pct = (freq.iloc[0]/freq.sum()*100) if not freq.empty else 0
            st.markdown(kpi("Dominância da Top Tag",f"{top1_pct:.1f}%","concentração","#f472b6"), unsafe_allow_html=True)

        st.markdown(insight(
            f"<strong>Entropia de Shannon:</strong> O vocabulário apresenta entropia de "
            f"<strong>{ent_global:.3f} bits</strong> (máximo possível: {max_ent:.3f} bits). "
            f"A entropia normalizada de <strong>{norm_ent:.2f}</strong> indica que o sistema está a "
            f"<strong>{norm_ent:.0%}</strong> da diversidade máxima possível. "
            f"{'Alta diversidade' if norm_ent > 0.7 else 'Diversidade moderada' if norm_ent > 0.4 else 'Baixa diversidade'} "
            f"— o sistema {'incentiva vocabulário variado' if norm_ent > 0.6 else 'tende a concentrar tags em poucos termos'}."
        ), unsafe_allow_html=True)

        st.markdown(divider(), unsafe_allow_html=True)

        # Entropia por obra
        if not tdf.empty and tdf['obra_id'].nunique() > 0:
            st.markdown("#### Entropia por Obra")
            obra_ent = []
            for oid in tdf['obra_id'].unique():
                ot = tdf[tdf['obra_id']==oid]['tag'].value_counts().to_dict()
                e  = tag_entropy(ot)
                n  = sum(ot.values())
                u  = len(ot)
                me = math.log2(u) if u > 1 else 1
                obra_ent.append({
                    'Obra': od.get(oid, f'Obra #{oid}'),
                    'Total Tags': n,
                    'Tags Únicas': u,
                    'Entropia': round(e, 3),
                    'Ent. Norm.': round(e/me if me > 0 else 0, 3),
                    'TTR': round(u/n if n > 0 else 0, 3)
                })
            obra_ent_df = pd.DataFrame(obra_ent).sort_values('Entropia', ascending=False)
            st.dataframe(obra_ent_df, use_container_width=True, hide_index=True)
            st.bar_chart(obra_ent_df.set_index('Obra')['Entropia'])

        st.markdown(divider(), unsafe_allow_html=True)

        # Distribuição de comprimento de tags
        st.markdown("#### Distribuição de Comprimento e Palavras")
        c1, c2 = st.columns(2)
        freq_df = tdf['tag'].value_counts().reset_index()
        freq_df.columns = ['Tag','Freq']
        freq_df['Len'] = freq_df['Tag'].str.len()
        freq_df['Words'] = freq_df['Tag'].str.split().str.len()
        with c1:
            st.markdown("**Caracteres por tag**")
            st.bar_chart(freq_df['Len'].value_counts().sort_index().rename("Tags"))
        with c2:
            st.markdown("**Palavras por tag**")
            st.bar_chart(freq_df['Words'].value_counts().sort_index().rename("Tags"))

        st.markdown(divider(), unsafe_allow_html=True)

        # Tags únicas por usuário ao longo do tempo
        if not tdf.empty and tdf['user_id'].nunique() > 1:
            st.markdown("#### Riqueza Vocabular (TTR) por Participante")
            udf = all_users()
            ttr_data = []
            for uid in tdf['user_id'].unique():
                ut = tdf[tdf['user_id']==uid]
                n, u = len(ut), ut['tag'].nunique()
                animal = "?"
                if not udf.empty:
                    row = udf[udf['user_id']==uid]
                    if not row.empty:
                        animal = row.iloc[0].get('animal_name', uid[:8])
                ttr_data.append({'Usuário': animal, 'TTR': round(u/n if n > 0 else 0, 3),
                                 'Tags': n, 'Únicas': u})
            ttr_df = pd.DataFrame(ttr_data).sort_values('TTR', ascending=False)
            st.bar_chart(ttr_df.set_index('Usuário')['TTR'])
            st.dataframe(ttr_df, use_container_width=True, hide_index=True)

# ═══════════════════════════════════════════════════════════════════════
# ABA 3 — CONEXÕES
# ═══════════════════════════════════════════════════════════════════════
def tab_connections():
    tdf  = all_tags()
    obs  = load_obras()
    od   = {o['id']:o['titulo'] for o in obs}
    if tdf.empty:
        st.warning("Nenhuma tag disponível.")
        return

    st.markdown("###  Conexões e Agrupamentos de Tags")
    st.markdown(insight(
        "<strong>Como funciona:</strong> O algoritmo combina três métricas — "
        "<strong>Contenção</strong> (ex: 'vaso' → 'vaso verde'), "
        "<strong>Jaccard de palavras</strong> (ex: 'barco preto' ↔ 'barco de barro') e "
        "<strong>Jaccard de trigramas</strong> (similaridade fonética). Score 0→1."
    ), unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1: threshold = st.slider("Limiar de similaridade:", 0.20, 0.90, 0.35, 0.05, key="ct")
    with c2: obra_f    = st.selectbox("Filtrar por obra:", ["Todas"]+[f"#{o['id']} — {o['titulo']}" for o in obs], key="co")
    with c3: max_c     = st.number_input("Máx. conexões:", 10, 300, 60, 10, key="cm")

    fdf = tdf.copy()
    if obra_f != "Todas":
        oid = int(obra_f.split("—")[0].replace("#","").strip())
        fdf = tdf[tdf['obra_id']==oid]

    all_t = fdf['tag'].tolist()
    if len(set(all_t)) < 2:
        st.warning("Necessário ao menos 2 tags distintas.")
        return

    with st.spinner("Calculando conexões…"):
        conns    = tag_connections(all_t, threshold=threshold)
        clusters = tag_clusters(all_t, threshold=threshold)

    n_involved = len(set(c['tag_a'] for c in conns) | set(c['tag_b'] for c in conns))
    density = (2*len(conns)) / (len(set(all_t))*(len(set(all_t))-1)) if len(set(all_t)) > 1 else 0

    c1,c2,c3,c4 = st.columns(4)
    with c1: st.markdown(kpi("Conexões", len(conns), f"limiar ≥ {threshold:.2f}","#60a5fa"), unsafe_allow_html=True)
    with c2: st.markdown(kpi("Grupos", len(clusters),"clusters","#a78bfa"), unsafe_allow_html=True)
    with c3: st.markdown(kpi("Tags Conectadas", n_involved,"","#34d399"), unsafe_allow_html=True)
    with c4: st.markdown(kpi("Densidade de Rede", f"{density:.3f}","0=esparsa · 1=densa","#fbbf24"), unsafe_allow_html=True)

    st.markdown(divider(), unsafe_allow_html=True)

    t1, t2 = st.tabs([" Lista de Conexões", " Grupos de Tags"])

    with t1:
        if not conns:
            st.info("Nenhuma conexão encontrada. Reduza o limiar.")
        else:
            tipos    = sorted(set(c['tipo'] for c in conns))
            tipo_sel = st.multiselect("Filtrar por tipo:", tipos, default=tipos, key="tsel")
            cf = [c for c in conns if c['tipo'] in tipo_sel][:max_c]
            freq_map = tdf['tag'].value_counts().to_dict()

            st.markdown(f"Exibindo **{len(cf)}** de **{len(conns)}** conexões")
            st.markdown(divider(), unsafe_allow_html=True)

            for c in cf:
                s   = c['similaridade']
                bar = "█"*int(s*10)+"░"*(10-int(s*10))
                fa  = freq_map.get(c['tag_a'],0)
                fb  = freq_map.get(c['tag_b'],0)
                clr = "#34d399" if s>0.7 else "#fbbf24" if s>0.5 else "#60a5fa"
                st.markdown(
                    f"<div class='conn-row'>"
                    f"<div style='display:flex;align-items:center;gap:10px;flex-wrap:wrap'>"
                    f"<span class='tag-badge'>{c['tag_a']}</span>"
                    f"<span style='opacity:.35;font-size:.72rem'>({fa}×)</span>"
                    f"<span style='opacity:.35;margin:0 .3rem'>↔</span>"
                    f"<span class='tag-badge'>{c['tag_b']}</span>"
                    f"<span style='opacity:.35;font-size:.72rem'>({fb}×)</span>"
                    f"</div>"
                    f"<div style='text-align:right;min-width:200px'>"
                    f"<span style='font-family:monospace;color:{clr};font-size:.8rem'>{bar} {s:.3f}</span><br>"
                    f"<span style='font-size:.7rem;opacity:.4'>{c['tipo']}</span>"
                    f"</div></div>", unsafe_allow_html=True)

            st.markdown(divider(), unsafe_allow_html=True)
            st.download_button(" Conexões (CSV)",
                pd.DataFrame(conns).to_csv(index=False).encode('utf-8'),
                f"conexoes_{datetime.now().strftime('%Y%m%d')}.csv","text/csv")

    with t2:
        if not clusters:
            st.info("Nenhum grupo formado. Reduza o limiar.")
        else:
            COLORS = ["#60a5fa","#34d399","#f472b6","#fbbf24","#a78bfa",
                      "#f87171","#67e8f9","#86efac","#fb923c","#c084fc"]
            freq_map   = tdf['tag'].value_counts().to_dict()
            cls_sorted = sorted(clusters, key=len, reverse=True)
            st.markdown(f"**{len(cls_sorted)} grupo(s) de tags semanticamente relacionadas**")
            st.markdown(divider(), unsafe_allow_html=True)
            for i, cl in enumerate(cls_sorted, 1):
                color      = COLORS[(i-1) % len(COLORS)]
                total_uses = sum(freq_map.get(t,0) for t in cl)
                pills = "".join(
                    f"<span class='cluster-pill'>{t} "
                    f"<span style='opacity:.45;font-size:.68rem'>({freq_map.get(t,0)}×)</span></span>"
                    for t in sorted(cl, key=lambda x: freq_map.get(x,0), reverse=True)
                )
                st.markdown(
                    f"<div class='cluster-wrap' style='border-left:4px solid {color}'>"
                    f"<div class='cluster-title'>Grupo {i} · {len(cl)} tags · {total_uses} usos</div>"
                    f"{pills}</div>", unsafe_allow_html=True)

            st.markdown(divider(), unsafe_allow_html=True)
            summ = pd.DataFrame([{
                "Grupo": f"Grupo {i}",
                "Tags": len(cl),
                "Usos Totais": sum(freq_map.get(t,0) for t in cl),
                "Amostra": ", ".join(sorted(cl,key=lambda x:freq_map.get(x,0),reverse=True)[:5])
                           + ("…" if len(cl)>5 else "")
            } for i,cl in enumerate(cls_sorted,1)])
            st.dataframe(summ, use_container_width=True, hide_index=True)
            st.download_button(" Grupos (CSV)",
                summ.to_csv(index=False).encode('utf-8'),
                f"clusters_{datetime.now().strftime('%Y%m%d')}.csv","text/csv")

# ═══════════════════════════════════════════════════════════════════════
# ABA 4 — COOCORRÊNCIAS
# ═══════════════════════════════════════════════════════════════════════
def tab_cooccurrence():
    tdf = all_tags()
    obs = load_obras()
    od  = {o['id']:o['titulo'] for o in obs}

    if tdf.empty:
        st.info("Nenhuma tag disponível.")
        return

    st.markdown("###  Análise de Coocorrência de Tags")
    st.markdown(insight(
        "<strong>Coocorrência:</strong> Indica quantas vezes duas tags foram aplicadas na mesma "
        "sessão (mesmo usuário + mesma obra). Revela <strong>padrões de associação semântica</strong> "
        "entre os conceitos usados pelos participantes."
    ), unsafe_allow_html=True)

    c1, c2 = st.columns([1,2])
    with c1:
        top_n = st.slider("Top N tags para matriz:", 5, 20, 10, 1, key="cooc_n")
        obra_f2 = st.selectbox("Filtrar por obra:",
            ["Todas"]+[f"#{o['id']} — {o['titulo']}" for o in obs], key="cooc_obra")

    fdf2 = tdf.copy()
    if obra_f2 != "Todas":
        oid2 = int(obra_f2.split("—")[0].replace("#","").strip())
        fdf2 = tdf[tdf['obra_id']==oid2]

    matrix = tag_cooccurrence(fdf2, top_n=top_n)

    if matrix.empty:
        st.info("Dados insuficientes para calcular coocorrências.")
        return

    # KPIs
    max_val = matrix.values.max() if matrix.values.max() > 0 else 1
    nonzero = (matrix > 0).values.sum() // 2
    tags_used = len(matrix.columns)

    c1,c2,c3 = st.columns(3)
    with c1: st.markdown(kpi("Tags na Matriz", tags_used,"top por frequência","#60a5fa"), unsafe_allow_html=True)
    with c2: st.markdown(kpi("Pares Coocorrentes", nonzero,"pares únicos","#34d399"), unsafe_allow_html=True)
    with c3: st.markdown(kpi("Coocorrência Máx.", int(max_val),"vezes","#fbbf24"), unsafe_allow_html=True)

    st.markdown(divider(), unsafe_allow_html=True)

    # Heatmap visual com HTML
    st.markdown("#### Mapa de Calor — Coocorrências")
    tags_list = list(matrix.columns)
    max_v = matrix.values.max() if matrix.values.max() > 0 else 1

    def heat_color(v, max_v):
        if v == 0: return "rgba(255,255,255,0.04)"
        pct = v / max_v
        r = int(96 + pct*(248-96))
        g = int(165 - pct*(165-113))
        b = int(250 - pct*(250-113))
        return f"rgb({r},{g},{b})"

    header = "<div style='display:flex;gap:2px;margin-bottom:2px;padding-left:90px'>"
    for t in tags_list:
        header += (f"<div style='width:28px;min-width:28px;font-size:.55rem;color:rgba(255,255,255,.5);"
                   f"transform:rotate(-45deg);transform-origin:bottom left;height:50px;"
                   f"display:flex;align-items:flex-end;overflow:hidden;white-space:nowrap'>{t[:8]}</div>")
    header += "</div>"

    rows_html = header
    for i, t1_tag in enumerate(tags_list):
        row = f"<div style='display:flex;gap:2px;align-items:center;margin-bottom:2px'>"
        row += (f"<div style='width:88px;min-width:88px;font-size:.65rem;color:rgba(255,255,255,.65);"
                f"text-align:right;padding-right:6px;overflow:hidden;white-space:nowrap;font-weight:600'>{t1_tag[:12]}</div>")
        for j, t2_tag in enumerate(tags_list):
            v = matrix.loc[t1_tag, t2_tag] if (t1_tag in matrix.index and t2_tag in matrix.columns) else 0
            bg = heat_color(v, max_v)
            txt = str(int(v)) if v > 0 else ""
            row += (f"<div style='width:28px;min-width:28px;height:28px;background:{bg};"
                    f"border-radius:5px;display:flex;align-items:center;justify-content:center;"
                    f"font-size:.58rem;font-weight:700;color:white;title={t1_tag}↔{t2_tag}:{v}'>{txt}</div>")
        row += "</div>"
        rows_html += row

    st.markdown(
        f"<div style='overflow-x:auto;padding:1rem;background:rgba(255,255,255,0.04);"
        f"border-radius:16px;border:1px solid rgba(255,255,255,0.1)'>{rows_html}</div>",
        unsafe_allow_html=True)

    st.markdown(divider(), unsafe_allow_html=True)

    # Top pares coocorrentes
    st.markdown("#### Top Pares de Coocorrência")
    pairs = []
    for i, t1_tag in enumerate(tags_list):
        for j, t2_tag in enumerate(tags_list):
            if j > i:
                v = matrix.loc[t1_tag, t2_tag] if (t1_tag in matrix.index and t2_tag in matrix.columns) else 0
                if v > 0:
                    pairs.append({'Tag A': t1_tag, 'Tag B': t2_tag, 'Coocorrências': int(v)})
    if pairs:
        pairs_df = pd.DataFrame(pairs).sort_values('Coocorrências', ascending=False).head(20)
        st.dataframe(pairs_df, use_container_width=True, hide_index=True)

        st.markdown(divider(), unsafe_allow_html=True)
        st.markdown("#### Visualização de Pares")
        for _, row in pairs_df.head(10).iterrows():
            pct = row['Coocorrências'] / max_v
            clr = "#34d399" if pct > 0.7 else "#fbbf24" if pct > 0.4 else "#60a5fa"
            st.markdown(
                f"<div class='conn-row'>"
                f"<div style='display:flex;align-items:center;gap:10px'>"
                f"<span class='tag-badge'>{row['Tag A']}</span>"
                f"<span style='opacity:.3'>+</span>"
                f"<span class='tag-badge'>{row['Tag B']}</span>"
                f"</div>"
                f"<div style='min-width:200px'>"
                f"{pbar(pct, clr)}"
                f"<span style='font-size:.75rem;font-weight:800;color:{clr}'>{int(row['Coocorrências'])}× juntas</span>"
                f"</div></div>",
                unsafe_allow_html=True)

        st.download_button(" Coocorrências (CSV)",
            pairs_df.to_csv(index=False).encode('utf-8'),
            f"coocorrencias_{datetime.now().strftime('%Y%m%d')}.csv","text/csv")

# ═══════════════════════════════════════════════════════════════════════
# ABA 5 — USUÁRIOS & QUESTIONÁRIO
# ═══════════════════════════════════════════════════════════════════════
def tab_users_quest():
    tdf = all_tags()
    udf = all_users()
    obs = load_obras()
    od  = {o['id']:o['titulo'] for o in obs}

    if udf.empty:
        st.info("Nenhum dado de usuário disponível.")
        return

    st.markdown("### 👥 Usuários & Questionário")

    uct = tdf.groupby('user_id').size().reset_index(name='Total_Tags') if not tdf.empty else pd.DataFrame(columns=['user_id','Total_Tags'])
    uuq = tdf.groupby('user_id')['tag'].nunique().reset_index(name='Tags_Unicas') if not tdf.empty else pd.DataFrame(columns=['user_id','Tags_Unicas'])
    uob = tdf.groupby('user_id')['obra_id'].nunique().reset_index(name='Obras') if not tdf.empty else pd.DataFrame(columns=['user_id','Obras'])

    merged = udf.merge(uct,on='user_id',how='left') \
                .merge(uuq,on='user_id',how='left') \
                .merge(uob,on='user_id',how='left').fillna(0)
    merged['TTR']     = (merged['Tags_Unicas']/merged['Total_Tags'].replace(0,np.nan)).fillna(0).round(3)
    merged['Usuário'] = merged.apply(lambda r: r.get('animal_name', r['user_id'][:8]), axis=1)

    c1,c2,c3,c4 = st.columns(4)
    top_u = merged.loc[merged['Total_Tags'].idxmax(),'Usuário'] if not merged.empty else "—"
    with c1: st.markdown(kpi("Participantes",       len(merged),"usuários","#60a5fa"), unsafe_allow_html=True)
    with c2: st.markdown(kpi("Média Tags/Usuário",  f"{merged['Total_Tags'].mean():.1f}","","#34d399"), unsafe_allow_html=True)
    with c3: st.markdown(kpi("Maior Contribuição",  int(merged['Total_Tags'].max()),top_u[:16],"#fbbf24"), unsafe_allow_html=True)
    with c4: st.markdown(kpi("Riqueza Média (TTR)", f"{merged['TTR'].mean():.2%}","vocabular","#a78bfa"), unsafe_allow_html=True)

    st.markdown(divider(), unsafe_allow_html=True)

    t1, t2, t3, t4 = st.tabs([
        " Tabela Geral",
        " Perfil Individual",
        " Questionário",
        " Cruzamentos"
    ])

    with t1:
        dcols = ['Usuário','Total_Tags','Tags_Unicas','TTR','Obras','q1','q2']
        avail = [c for c in dcols if c in merged.columns]
        disp  = merged[avail].rename(columns={
            'Total_Tags':'Tags Criadas','Tags_Unicas':'Tags Únicas',
            'Obras':'Obras Etiquetadas','q1':'Familiaridade','q2':'Conhecimento Museológico'
        }).sort_values('Tags Criadas',ascending=False)
        st.dataframe(disp, use_container_width=True, hide_index=True)
        st.markdown(divider(), unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Tags por participante**")
            st.bar_chart(merged.set_index('Usuário')['Total_Tags'].sort_values(ascending=False))
        with c2:
            st.markdown("**TTR por participante**")
            st.bar_chart(merged.set_index('Usuário')['TTR'].sort_values(ascending=False))

    with t2:
        uopts = [f"🐾 {r.get('animal_name',r['user_id'][:8])}" for _,r in udf.iterrows()]
        usel  = st.selectbox("Selecione um participante:", uopts, key="ui_sel")
        uidx  = uopts.index(usel)
        uid   = udf.iloc[uidx]['user_id']
        uanim = udf.iloc[uidx].get('animal_name', uid[:8])

        utags = tdf[tdf['user_id']==uid] if not tdf.empty else pd.DataFrame()
        if utags.empty:
            st.info("Este participante ainda não criou tags.")
        else:
            ttl = len(utags); unq = utags['tag'].nunique()
            ttr_u = unq/ttl if ttl else 0
            ent_u = tag_entropy(utags['tag'].value_counts().to_dict())

            c1,c2,c3,c4 = st.columns(4)
            with c1: st.markdown(kpi("Tags Criadas", ttl,"","#60a5fa"), unsafe_allow_html=True)
            with c2: st.markdown(kpi("Tags Únicas",  unq,f"TTR: {ttr_u:.2%}","#34d399"), unsafe_allow_html=True)
            with c3: st.markdown(kpi("Entropia",     f"{ent_u:.3f}","bits","#fbbf24"), unsafe_allow_html=True)
            with c4: st.markdown(kpi("Obras",        utags['obra_id'].nunique(),"etiquetadas","#a78bfa"), unsafe_allow_html=True)

            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"**Top tags de {uanim}:**")
                st.bar_chart(utags['tag'].value_counts().head(15))
            with c2:
                st.markdown("**Distribuição por obra:**")
                st.bar_chart(utags.groupby('obra_id').size().rename(index=od))

            st.markdown("**Conexões deste participante (limiar 0.30):**")
            uconns = tag_connections(utags['tag'].tolist(), threshold=0.30)
            if uconns:
                freq_map = utags['tag'].value_counts().to_dict()
                for c in uconns[:10]:
                    fa = freq_map.get(c['tag_a'],0); fb = freq_map.get(c['tag_b'],0)
                    st.markdown(
                        f"<div class='conn-row'>"
                        f"<div style='display:flex;align-items:center;gap:9px;flex-wrap:wrap'>"
                        f"<span class='tag-badge'>{c['tag_a']}</span>"
                        f"<span style='opacity:.3;font-size:.7rem'>({fa}×)</span>"
                        f"<span style='opacity:.3'>↔</span>"
                        f"<span class='tag-badge'>{c['tag_b']}</span>"
                        f"<span style='opacity:.3;font-size:.7rem'>({fb}×)</span>"
                        f"</div>"
                        f"<span style='opacity:.4;font-size:.75rem'>{c['similaridade']:.3f} · {c['tipo']}</span>"
                        f"</div>", unsafe_allow_html=True)
            else:
                st.info("Nenhuma conexão nas tags deste participante.")

            st.markdown(divider(), unsafe_allow_html=True)
            ft = utags.copy(); ft['Obra'] = ft['obra_id'].map(od)
            st.dataframe(
                ft[['tag','Obra','timestamp']].rename(columns={'tag':'Tag','timestamp':'Data/Hora'}),
                use_container_width=True, hide_index=True)

    with t3:
        c1,c2 = st.columns(2)
        with c1:
            st.markdown("**Q1 — Familiaridade com Museus**")
            q1c = udf['q1'].value_counts()
            st.bar_chart(q1c)
            q1p = (q1c/q1c.sum()*100).round(1).reset_index()
            q1p.columns=['Resposta','%']
            st.dataframe(q1p, use_container_width=True, hide_index=True)
        with c2:
            st.markdown("**Q2 — Conhecimento Museológico**")
            q2c = udf['q2'].value_counts()
            st.bar_chart(q2c)
            q2p = (q2c/q2c.sum()*100).round(1).reset_index()
            q2p.columns=['Resposta','%']
            st.dataframe(q2p, use_container_width=True, hide_index=True)

        st.markdown(divider(), unsafe_allow_html=True)
        st.markdown("**Q3 — Respostas Abertas sobre Tags**")
        disp = udf.copy()
        if 'animal_name' in disp.columns:
            disp = disp.rename(columns={'animal_name':'Usuário Anônimo'})
        disp['Palavras'] = disp['q3'].str.split().str.len()
        st.markdown(f"Comprimento médio: **{disp['Palavras'].mean():.0f} palavras** por resposta")
        st.bar_chart(disp['Palavras'].value_counts().sort_index().rename("Respostas"))
        st.dataframe(
            disp[['Usuário Anônimo','q3','Palavras','timestamp']]
            .sort_values('timestamp',ascending=False)
            .rename(columns={'q3':'Resposta','timestamp':'Data/Hora'}),
            use_container_width=True, hide_index=True)

    with t4:
        if tdf.empty:
            st.info("Dados insuficientes."); return
        m = merged.copy()
        m['TTR'] = (m['Tags_Unicas']/m['Total_Tags'].replace(0,np.nan)).fillna(0)

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Familiaridade com Museus × Média de Tags**")
            avg_q1 = m.groupby('q1')['Total_Tags'].mean().sort_values(ascending=False)
            st.bar_chart(avg_q1)
        with c2:
            st.markdown("**Conhecimento Museológico × Tags Únicas**")
            avg_q2 = m.groupby('q2')['Tags_Unicas'].mean().sort_values(ascending=False)
            st.bar_chart(avg_q2)

        st.markdown(divider(), unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Familiaridade × TTR**")
            st.bar_chart(m.groupby('q1')['TTR'].mean().sort_values(ascending=False))
        with c2:
            st.markdown("**Conhecimento Museológico × TTR**")
            st.bar_chart(m.groupby('q2')['TTR'].mean().sort_values(ascending=False))

        st.markdown(divider(), unsafe_allow_html=True)
        cross = m.groupby('q1').agg(
            Usuários=('user_id','count'),
            Média_Tags=('Total_Tags','mean'),
            Média_Únicas=('Tags_Unicas','mean'),
            Riqueza_TTR=('TTR','mean'),
        ).round(2).reset_index()
        cross.columns = ['Familiaridade','Usuários','Média Tags','Média Únicas','Riqueza (TTR)']
        st.dataframe(cross, use_container_width=True, hide_index=True)

        st.markdown(insight(
            "<strong>Interpretação:</strong> Compare se participantes mais familiarizados com museus "
            "produzem mais tags, maior diversidade vocabular (TTR) ou tags mais criativas. "
            "TTR próximo de 1.0 = alta originalidade e variedade vocabular."
        ), unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════
# ABA 6 — OBRAS
# ═══════════════════════════════════════════════════════════════════════
def tab_obras():
    st.markdown("###  Gestão de Obras")
    obras = load_obras()
    t1, t2 = st.tabs([" Listar Obras"," Adicionar Nova"])

    with t1:
        if obras:
            for obra in obras:
                c1,c2,c3 = st.columns([1,3,1])
                with c1:
                    st.image(obra['imagem'], use_container_width=True)
                with c2:
                    st.markdown(f"**#{obra['id']} — {obra['titulo']}**")
                    st.markdown(f"*{obra.get('artista','')} · {obra.get('ano','')}*")
                    st.markdown(f"Categoria: {obra.get('categoria','—')} · Técnica: {obra.get('tecnica','—')}")
                    st.markdown(f"Dimensões: {obra.get('dimensoes','—')}")
                    if obra.get('descricao'):
                        st.markdown(f"_{obra['descricao']}_")
                with c3:
                    if st.button(" Remover", key=f"del_{obra['id']}"):
                        obras.remove(obra)
                        save_json_file(OBRAS_FILE, obras)
                        st.cache_data.clear()
                        st.rerun()
                st.divider()
        else:
            st.info("Nenhuma obra cadastrada.")

    with t2:
        with st.form("add_obra"):
            c1, c2 = st.columns(2)
            with c1:
                titulo   = st.text_input("Título da Obra*")
                artista  = st.text_input("Artista*")
                ano      = st.text_input("Ano*")
                imagem   = st.text_input("URL da Imagem*")
            with c2:
                categoria  = st.selectbox("Categoria:", ["Pintura","Escultura","Fotografia","Gravura","Desenho","Arte Digital","Outro"])
                tecnica    = st.text_input("Técnica:", placeholder="Ex: Óleo sobre tela")
                dimensoes  = st.text_input("Dimensões:", placeholder="Ex: 100 × 80 cm")
                descricao  = st.text_area("Descrição / Áudio-descrição:", height=100,
                                          placeholder="Descrição acessível da obra para usuários com deficiência visual…")
            if st.form_submit_button(" Adicionar Obra", use_container_width=True):
                if titulo and artista and ano and imagem:
                    nid = max([o['id'] for o in obras])+1 if obras else 1
                    obras.append({
                        "id":nid,"titulo":titulo,"artista":artista,"ano":ano,
                        "categoria":categoria,"tecnica":tecnica,"dimensoes":dimensoes,
                        "descricao":descricao,"imagem":imagem
                    })
                    save_json_file(OBRAS_FILE, obras)
                    st.success(" Obra adicionada com sucesso!")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("Preencha os campos obrigatórios (*)")

# ═══════════════════════════════════════════════════════════════════════
# ABA 7 — EXPORTAR
# ═══════════════════════════════════════════════════════════════════════
def tab_export():
    st.markdown("###  Central de Exportação")
    tdf  = all_tags()
    udf  = all_users()
    obs  = load_obras()

    t1, t2 = st.tabs([" Exportação Geral"," Por Participante"])

    with t1:
        c1,c2,c3 = st.columns(3)
        with c1:
            st.markdown("####  Tags")
            if not tdf.empty:
                st.download_button(" Todas as Tags (CSV)",
                    tdf.to_csv(index=False).encode('utf-8'),
                    f"tags_{datetime.now().strftime('%Y%m%d')}.csv","text/csv",
                    use_container_width=True)
                freq = tdf['tag'].value_counts().reset_index()
                freq.columns=['Tag','Frequência']
                freq['%']=(freq['Frequência']/freq['Frequência'].sum()*100).round(2)
                st.download_button(" Frequências (CSV)",
                    freq.to_csv(index=False).encode('utf-8'),
                    f"freq_{datetime.now().strftime('%Y%m%d')}.csv","text/csv",
                    use_container_width=True)
        with c2:
            st.markdown("####  Usuários")
            if not udf.empty:
                st.download_button(" Usuários (CSV)",
                    udf.to_csv(index=False).encode('utf-8'),
                    f"usuarios_{datetime.now().strftime('%Y%m%d')}.csv","text/csv",
                    use_container_width=True)
        with c3:
            st.markdown("####  Obras")
            if obs:
                st.download_button(" Obras (CSV)",
                    pd.DataFrame(obs).to_csv(index=False).encode('utf-8'),
                    f"obras_{datetime.now().strftime('%Y%m%d')}.csv","text/csv",
                    use_container_width=True)

        st.markdown(divider(), unsafe_allow_html=True)
        st.markdown("####  Exportar Conexões")
        if not tdf.empty:
            thr = st.slider("Limiar:", 0.2, 0.9, 0.35, 0.05, key="exp_thr")
            if st.button("Gerar conexões"):
                with st.spinner("Calculando…"):
                    conns = tag_connections(tdf['tag'].tolist(), threshold=thr)
                if conns:
                    cdf = pd.DataFrame(conns)
                    st.download_button(" Conexões (CSV)",
                        cdf.to_csv(index=False).encode('utf-8'),
                        f"conexoes_{datetime.now().strftime('%Y%m%d')}.csv","text/csv",
                        use_container_width=True)
                    st.success(f" {len(conns)} conexões prontas.")
                else:
                    st.info("Nenhuma conexão com este limiar.")

        st.markdown(divider(), unsafe_allow_html=True)
        st.markdown("####  Exportar Coocorrências")
        if not tdf.empty:
            top_exp = st.slider("Top N tags:", 5, 20, 10, key="cooc_exp")
            if st.button("Gerar coocorrências"):
                matrix = tag_cooccurrence(tdf, top_n=top_exp)
                if not matrix.empty:
                    pairs = []
                    tags_l = list(matrix.columns)
                    for i, t1_t in enumerate(tags_l):
                        for j, t2_t in enumerate(tags_l):
                            if j > i:
                                v = matrix.loc[t1_t, t2_t]
                                if v > 0:
                                    pairs.append({'Tag A':t1_t,'Tag B':t2_t,'Coocorrências':int(v)})
                    if pairs:
                        pdf = pd.DataFrame(pairs).sort_values('Coocorrências', ascending=False)
                        st.download_button(" Coocorrências (CSV)",
                            pdf.to_csv(index=False).encode('utf-8'),
                            f"cooc_{datetime.now().strftime('%Y%m%d')}.csv","text/csv",
                            use_container_width=True)

    with t2:
        if udf.empty:
            st.info("Nenhum participante.")
            return
        uopts = [f"🐾 {r.get('animal_name',r['user_id'][:8])}" for _,r in udf.iterrows()]
        usel  = st.selectbox("Participante:", uopts, key="exp_u")
        uidx  = uopts.index(usel)
        uid   = udf.iloc[uidx]['user_id']
        uanim = udf.iloc[uidx].get('animal_name', uid[:8])

        st.markdown(f"#### Dados de: **{uanim}**")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#####  Questionário")
            hq = html_quest(uid, uanim, udf)
            if hq:
                st.download_button(" Respostas (HTML/PDF)", hq,
                    f"quest_{uid[:8]}.html","text/html", use_container_width=True)
            ud = udf[udf['user_id']==uid]
            if not ud.empty:
                st.download_button(" Respostas (CSV)",
                    ud.to_csv(index=False).encode('utf-8'),
                    f"quest_{uid[:8]}.csv","text/csv", use_container_width=True)
        with c2:
            st.markdown("#####  Tags Criadas")
            ht = html_tags(uid, uanim, obs, tdf)
            if ht:
                st.download_button("⬇️ Tags (HTML/PDF)", ht,
                    f"tags_{uid[:8]}.html","text/html", use_container_width=True)
            ut = get_user_tags(uid)
            if not ut.empty:
                st.download_button(" Tags (CSV)",
                    ut.to_csv(index=False).encode('utf-8'),
                    f"tags_{uid[:8]}.csv","text/csv", use_container_width=True)

if __name__ == "__main__":
    main()                
