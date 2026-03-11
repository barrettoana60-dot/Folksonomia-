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
from collections import defaultdict, Counter
import math

warnings.filterwarnings("ignore")

st.set_page_config(
    page_title="Sistema Folksonomia Digital",
    layout="wide",
    initial_sidebar_state="collapsed",
    page_icon="F",
)

# ── CONSTANTS ──────────────────────────────────────────────────────────────────
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
    "Arara","Bugio","Caititu","Jaguatirica","Lobo","Mutum","Pirarucu","Tucano","Sucuri","Tatu",
]
ADJETIVOS = [
    "Azul","Bravo","Calmo","Dourado","Esperto","Feroz","Gracioso","Intenso","Jovial","Lento",
    "Magico","Nobre","Ousado","Preciso","Rapido","Sabio","Timido","Unico","Valente","Zeloso",
    "Curioso","Furtivo","Altivo","Sereno","Vibrante","Audaz","Brilhante","Corajoso","Distinto","Elegante",
]

CATEGORIAS_TAGS = {
    "Cores": [
        "azul","vermelho","verde","amarelo","preto","branco","cinza","laranja","roxo","rosa",
        "marrom","dourado","prateado","escuro","claro","colorido","monocromatico","vibrante",
        "palido","saturado","negro","bege","turquesa","indigo","violeta",
    ],
    "Emocoes": [
        "triste","alegre","melancolia","angustia","paz","guerra","amor","medo","esperanca",
        "desespero","sofrimento","violencia","calmo","agitado","tenso","sereno","dor","paixao",
        "raiva","tristeza","felicidade","ansiedade","nostalgia","melancolia","tensao","horror",
        "terror","sublime","contemplacao","meditacao",
    ],
    "Estilos": [
        "abstrato","realismo","impressionismo","cubismo","modernismo","barroco","classico",
        "contemporaneo","expressionismo","surrealismo","geometrico","figurativo","minimalista",
        "romantico","simbolismo","dadaismo","futurismo","pop","hiperrealismo","conceptual",
    ],
    "Elementos Visuais": [
        "luz","sombra","natureza","figura","paisagem","retrato","simbolo","geometria","linha",
        "forma","textura","perspectiva","composicao","espaco","volume","contraste","movimento",
        "ritmo","equilibrio","detalhe","fragmento","escala","profundidade","plano",
    ],
    "Periodo Historico": [
        "antigo","medieval","renascentista","moderno","historico","contemporaneo","seculo",
        "era","epoca","guerra","revolucao","colonial","pre-colombiano","industrial",
    ],
    "Temas": [
        "religiao","mitologia","politica","social","cotidiano","fantasia","ciencia","tecnologia",
        "cultura","identidade","memoria","tempo","morte","vida","corpo","feminismo","poder",
        "natureza","urbano","rural","trabalho","familia","infancia","velhice",
    ],
}


def categorize_tag(tag):
    t = tag.lower().strip()
    for cat, kws in CATEGORIAS_TAGS.items():
        if any(kw in t or t in kw for kw in kws):
            return cat
    return "Outros"


def generate_animal_name():
    random.seed()
    return f"{random.choice(ANIMAIS)} {random.choice(ADJETIVOS)}"


# ── CORE DATA ──────────────────────────────────────────────────────────────────
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


# ── SIMILARITY & ANALYSIS ──────────────────────────────────────────────────────
def ntag(tag):
    return tag.lower().strip()


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
        nj = len(ng1 & ng2) / len(ng1 | ng2) if ng1 | ng2 else 0
        if nj > 0:
            wj = len(w1 & w2) / len(w1 | w2) if w1 | w2 else 0
            return 0.6 * nj + 0.4 * wj
    return 0.0


def tag_connections(tags_list, threshold=0.35):
    uniq = list(set(ntag(t) for t in tags_list))
    conns = []
    for i in range(len(uniq)):
        for j in range(i+1, len(uniq)):
            s = sim(uniq[i], uniq[j])
            if s >= threshold:
                w1, w2 = words(uniq[i]), words(uniq[j])
                shared = w1 & w2
                if uniq[i] in uniq[j] or uniq[j] in uniq[i]:
                    tipo = "Contencao"
                elif shared:
                    tipo = f"Palavra comum: '{', '.join(shared)}'"
                else:
                    tipo = "Similaridade fonetica"
                conns.append({"tag_a": uniq[i], "tag_b": uniq[j],
                               "similaridade": round(s, 3), "tipo": tipo})
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


def tag_cooccurrence(tags_df):
    """Tags that appear together on the same obra (any user)."""
    if tags_df.empty:
        return pd.DataFrame()
    obra_tags = tags_df.groupby("obra_id")["tag"].apply(list).reset_index()
    cooc = defaultdict(int)
    for _, row in obra_tags.iterrows():
        ts = list(set(row["tag"]))
        for i in range(len(ts)):
            for j in range(i+1, len(ts)):
                pair = tuple(sorted([ts[i], ts[j]]))
                cooc[pair] += 1
    if not cooc:
        return pd.DataFrame(columns=["Tag A", "Tag B", "Co-ocorrencias"])
    result = [(a, b, c) for (a, b), c in cooc.items()]
    df = pd.DataFrame(result, columns=["Tag A", "Tag B", "Co-ocorrencias"])
    return df.sort_values("Co-ocorrencias", ascending=False).reset_index(drop=True)


def vocabulary_metrics(tags_list):
    tokens = [t.lower().strip() for t in tags_list]
    if not tokens:
        return {"N": 0, "V": 0, "TTR": 0, "Hapax": 0, "Entropy": 0}
    N = len(tokens)
    freq = Counter(tokens)
    V = len(freq)
    ttr = V / N
    hapax = sum(1 for c in freq.values() if c == 1)
    entropy = -sum((c/N) * math.log2(c/N) for c in freq.values() if c > 0)
    return {"N": N, "V": V, "TTR": round(ttr, 4),
            "Hapax": hapax, "Entropy": round(entropy, 3)}


def build_audio_desc(obra, tags_df):
    """Build Portuguese audio description text for an obra."""
    tid  = obra.get("id", "")
    title  = obra.get("titulo", f"Obra {tid}")
    artist = obra.get("artista", "Artista desconhecido")
    year   = obra.get("ano", "Ano desconhecido")
    if not tags_df.empty:
        ot = tags_df[tags_df["obra_id"] == tid]
        count = len(ot)
        top   = ot["tag"].value_counts().head(3).index.tolist()
        top_text = ", ".join(top) if top else "nenhuma"
    else:
        count, top_text = 0, "nenhuma"
    return (
        f"Obra numero {tid}: {title}, de {artist}, ano {year}. "
        f"Esta obra possui {count} registros de tags. "
        f"As etiquetas mais frequentes sao: {top_text}."
    )


# ── CSS ────────────────────────────────────────────────────────────────────────
def load_css():
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

/* ── CSS VARIABLES (Dark Theme default) ──────────────────── */
:root {
    --fs-html: 16px;
    --bg-a: #000000;
    --bg-b: #001025;
    --bg-c: #000a1a;
    --card-bg: rgba(255,255,255,0.12);
    --card-bg-hover: rgba(255,255,255,0.20);
    --card-border: rgba(255,255,255,0.22);
    --card-border-hover: rgba(255,255,255,0.45);
    --navbar-bg: rgba(0,5,20,0.70);
    --text-main: #f0f4ff;
    --text-sub: rgba(220,228,255,0.75);
    --text-dim: rgba(200,215,255,0.40);
    --accent-1: #7ecfff;
    --accent-2: #c5a8ff;
    --accent-3: #5ee8b0;
    --accent-4: #ffe080;
    --accent-5: #ffb0d0;
    --accent-red: #ff7070;
    --btn-bg: rgba(255,255,255,0.14);
    --btn-border: rgba(255,255,255,0.28);
    --btn-hover-bg: rgba(255,255,255,0.26);
    --input-bg: rgba(255,255,255,0.10);
    --input-border: rgba(255,255,255,0.22);
    --tag-bg: rgba(255,255,255,0.16);
    --tag-border: rgba(255,255,255,0.32);
    --kpi-bg: rgba(255,255,255,0.10);
    --conn-bg: rgba(255,255,255,0.05);
    --conn-hover: rgba(255,255,255,0.10);
    --divider: rgba(255,255,255,0.12);
    --shadow: rgba(0,0,0,0.35);
    --insight-bg: rgba(126,207,255,0.08);
    --insight-border: rgba(126,207,255,0.25);
}

/* Light Theme */
html[data-theme="light"] {
    --bg-a: #ddeeff;
    --bg-b: #f0f8ff;
    --bg-c: #e8f2ff;
    --card-bg: rgba(255,255,255,0.88);
    --card-bg-hover: rgba(255,255,255,0.98);
    --card-border: rgba(20,80,180,0.15);
    --card-border-hover: rgba(20,80,180,0.40);
    --navbar-bg: rgba(230,242,255,0.90);
    --text-main: #0a1628;
    --text-sub: rgba(10,22,40,0.68);
    --text-dim: rgba(10,22,40,0.35);
    --accent-1: #1a6ac9;
    --accent-2: #6a32c0;
    --accent-3: #0a8a58;
    --accent-4: #b06a00;
    --accent-5: #b03070;
    --accent-red: #c01020;
    --btn-bg: rgba(20,80,180,0.10);
    --btn-border: rgba(20,80,180,0.30);
    --btn-hover-bg: rgba(20,80,180,0.20);
    --input-bg: rgba(255,255,255,0.95);
    --input-border: rgba(20,80,180,0.25);
    --tag-bg: rgba(20,80,180,0.10);
    --tag-border: rgba(20,80,180,0.28);
    --kpi-bg: rgba(255,255,255,0.80);
    --conn-bg: rgba(20,80,180,0.04);
    --conn-hover: rgba(20,80,180,0.08);
    --divider: rgba(20,80,180,0.12);
    --shadow: rgba(10,30,80,0.15);
    --insight-bg: rgba(20,80,180,0.06);
    --insight-border: rgba(20,80,180,0.22);
}

/* High Contrast Theme */
html[data-theme="high-contrast"] {
    --bg-a: #000000;
    --bg-b: #000000;
    --bg-c: #0a0a00;
    --card-bg: #111100;
    --card-bg-hover: #1a1a00;
    --card-border: #ffff00;
    --card-border-hover: #ffffff;
    --navbar-bg: rgba(0,0,0,0.97);
    --text-main: #ffff00;
    --text-sub: #eeee00;
    --text-dim: #bbbb00;
    --accent-1: #ffff00;
    --accent-2: #ff8800;
    --accent-3: #00ff80;
    --accent-4: #ff4400;
    --accent-5: #ff00aa;
    --accent-red: #ff0000;
    --btn-bg: #1a1a00;
    --btn-border: #ffff00;
    --btn-hover-bg: #2a2a00;
    --input-bg: #111100;
    --input-border: #ffff00;
    --tag-bg: rgba(255,255,0,0.12);
    --tag-border: #ffff00;
    --kpi-bg: #111100;
    --conn-bg: rgba(255,255,0,0.04);
    --conn-hover: rgba(255,255,0,0.10);
    --divider: #444400;
    --shadow: rgba(0,0,0,0.80);
    --insight-bg: rgba(255,255,0,0.06);
    --insight-border: #ffff00;
}

/* ── GLOBAL ───────────────────────────────────────────────── */
*, *::before, *::after { margin:0; padding:0; box-sizing:border-box; }
html { font-size: var(--fs-html); transition: font-size 0.25s; }

@keyframes bgAnim {
    0%   { background-position: 0% 50%; }
    50%  { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}

.stApp {
    font-family: 'Inter', sans-serif !important;
    background: linear-gradient(-45deg,
        var(--bg-a) 0%, var(--bg-b) 30%,
        var(--bg-c) 60%, var(--bg-a) 100%) !important;
    background-size: 400% 400% !important;
    animation: bgAnim 18s ease infinite !important;
    color: var(--text-main) !important;
    min-height: 100vh;
}

/* ── NAVBAR ───────────────────────────────────────────────── */
.top-navbar {
    position: fixed; top: 0; left: 0; right: 0; z-index: 9900;
    background: var(--navbar-bg);
    backdrop-filter: blur(24px) saturate(180%);
    -webkit-backdrop-filter: blur(24px) saturate(180%);
    border-bottom: 1px solid var(--card-border);
    padding: 1.2rem 2.5rem;
    display: flex; justify-content: space-between; align-items: center;
    box-shadow: 0 4px 30px var(--shadow);
    transition: background 0.4s;
}
.navbar-logo {
    font-size: 1.55rem; font-weight: 800; letter-spacing: -0.5px;
    background: linear-gradient(135deg, var(--accent-1) 0%, var(--accent-2) 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text;
}
.navbar-info {
    font-size: 0.78rem; color: var(--text-dim); font-weight: 500;
    letter-spacing: 0.5px; text-transform: uppercase;
}

/* ── MAIN CONTENT ─────────────────────────────────────────── */
.main-content {
    margin-top: 100px; padding: 2rem 2.5rem;
    max-width: 1680px; margin-left: auto; margin-right: auto;
}

/* ── GLASS CARD ───────────────────────────────────────────── */
.glass-card {
    background: var(--card-bg);
    backdrop-filter: blur(20px) saturate(160%);
    -webkit-backdrop-filter: blur(20px) saturate(160%);
    border: 1px solid var(--card-border);
    border-radius: 20px; padding: 2.2rem; margin: 1.2rem 0;
    box-shadow: 0 8px 32px var(--shadow);
    transition: all 0.35s cubic-bezier(0.4,0,0.2,1);
    position: relative; overflow: hidden;
}
.glass-card::before {
    content: ''; position: absolute; top: 0; left: -100%;
    width: 100%; height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.15), transparent);
    transition: left 0.6s;
}
.glass-card:hover::before { left: 100%; }
.glass-card:hover {
    background: var(--card-bg-hover);
    border-color: var(--card-border-hover);
    transform: translateY(-4px);
    box-shadow: 0 16px 48px var(--shadow);
}

/* ── OBRA CARD ────────────────────────────────────────────── */
.obra-card {
    background: var(--card-bg);
    backdrop-filter: blur(16px);
    border: 1px solid var(--card-border);
    border-radius: 18px; overflow: hidden;
    transition: all 0.4s cubic-bezier(0.4,0,0.2,1);
    position: relative;
}
.obra-card:hover {
    transform: translateY(-10px) scale(1.02);
    border-color: var(--card-border-hover);
    box-shadow: 0 24px 60px var(--shadow);
}
.obra-card img {
    width: 100%; height: 260px; object-fit: cover;
    transition: transform 0.6s cubic-bezier(0.4,0,0.2,1);
    display: block;
}
.obra-card:hover img { transform: scale(1.12); }
.obra-card-body { padding: 1.2rem 1.4rem; }
.obra-card-title {
    font-size: 1rem; font-weight: 700; color: var(--text-main);
    margin-bottom: 0.3rem;
}
.obra-card-meta {
    font-size: 0.78rem; color: var(--text-sub); margin-bottom: 0.8rem;
}

/* ── AUDIO BUTTON ─────────────────────────────────────────── */
.audio-btn {
    display: inline-flex; align-items: center; gap: 6px;
    background: var(--btn-bg); border: 1px solid var(--btn-border);
    color: var(--text-main); padding: 0.45rem 1.1rem;
    border-radius: 50px; font-size: 0.78rem; font-weight: 600;
    cursor: pointer; transition: all 0.25s; margin: 0.2rem 0.2rem 0.6rem 0;
    font-family: 'Inter', sans-serif;
}
.audio-btn:hover {
    background: var(--btn-hover-bg);
    border-color: var(--accent-1);
    color: var(--accent-1);
    transform: translateY(-2px);
}
.audio-btn-stop {
    border-color: var(--accent-red); color: var(--accent-red);
}

/* ── ACCESSIBILITY PANEL ──────────────────────────────────── */
.access-panel {
    position: fixed; bottom: 28px; right: 28px; z-index: 99999;
    font-family: 'Inter', sans-serif;
}
.access-toggle {
    background: linear-gradient(135deg, var(--accent-1), var(--accent-2));
    border: none; border-radius: 50px; padding: 0.75rem 1.4rem;
    color: #fff; font-weight: 700; font-size: 0.85rem;
    cursor: pointer; box-shadow: 0 6px 24px var(--shadow);
    transition: all 0.3s; letter-spacing: 0.3px;
    display: flex; align-items: center; gap: 8px;
}
.access-toggle:hover { transform: translateY(-3px) scale(1.04); }
.access-panel-body {
    position: absolute; bottom: 60px; right: 0;
    background: var(--card-bg); backdrop-filter: blur(24px);
    border: 1px solid var(--card-border); border-radius: 18px;
    padding: 1.4rem; width: 290px;
    box-shadow: 0 16px 60px var(--shadow);
    display: none; flex-direction: column; gap: 1rem;
}
.access-panel-body.open { display: flex; }
.access-group-label {
    font-size: 0.68rem; text-transform: uppercase; letter-spacing: 1.5px;
    color: var(--text-dim); font-weight: 700; margin-bottom: 0.4rem;
}
.access-group { display: flex; flex-direction: column; gap: 4px; }
.access-row { display: flex; gap: 6px; flex-wrap: wrap; }
.access-btn {
    flex: 1; background: var(--btn-bg); border: 1px solid var(--btn-border);
    color: var(--text-main); padding: 0.5rem 0.5rem; border-radius: 10px;
    font-size: 0.78rem; font-weight: 600; cursor: pointer;
    transition: all 0.2s; font-family: 'Inter', sans-serif; text-align: center;
    min-width: 52px;
}
.access-btn:hover { background: var(--btn-hover-bg); border-color: var(--accent-1); color: var(--accent-1); }
.access-btn.active-btn { border-color: var(--accent-1); color: var(--accent-1); background: rgba(126,207,255,0.15); }
.access-divider { height: 1px; background: var(--divider); margin: 0.2rem 0; }
.access-shortcut {
    font-size: 0.68rem; color: var(--text-dim); line-height: 1.6;
}

/* ── TYPOGRAPHY ───────────────────────────────────────────── */
.main-title {
    color: var(--text-main); font-size: 3rem; font-weight: 900;
    text-align: center; margin: 1.5rem 0 0.8rem;
    letter-spacing: -1.5px; line-height: 1.1;
}
.subtitle {
    color: var(--text-sub); font-size: 1.1rem; text-align: center;
    margin-bottom: 2.5rem; line-height: 1.8; font-weight: 400;
}
h1,h2,h3,h4,h5,h6 { color: var(--text-main) !important; font-weight: 700; }
label { color: var(--text-main) !important; font-weight: 600 !important; }
p, li, span { color: var(--text-main); }

/* ── KPI CARD ─────────────────────────────────────────────── */
.kpi-card {
    background: var(--kpi-bg);
    backdrop-filter: blur(16px);
    border: 1px solid var(--card-border);
    border-radius: 16px; padding: 1.4rem; text-align: center;
    box-shadow: 0 6px 24px var(--shadow);
    transition: all 0.35s; height: 100%;
}
.kpi-card:hover { transform: translateY(-5px) scale(1.03); box-shadow: 0 14px 40px var(--shadow); }
.kpi-val { font-size: 2.2rem; font-weight: 800; margin: 0.5rem 0; }
.kpi-lbl { font-size: 0.72rem; text-transform: uppercase; letter-spacing: 1.8px; font-weight: 700; color: var(--text-sub); }
.kpi-sub { font-size: 0.68rem; color: var(--text-dim); margin-top: 0.25rem; }

/* ── INSIGHT BOX ──────────────────────────────────────────── */
.insight-box {
    background: var(--insight-bg); border: 1px solid var(--insight-border);
    border-radius: 12px; padding: 1rem 1.4rem;
    color: var(--text-sub); font-size: 0.88rem; line-height: 1.75;
    margin: 0.6rem 0;
}
.insight-box strong { color: var(--accent-1); }

/* ── TAG BADGE ────────────────────────────────────────────── */
.tag-badge {
    display: inline-block;
    background: var(--tag-bg); border: 1px solid var(--tag-border);
    color: var(--text-main); padding: 0.4rem 1rem; border-radius: 50px;
    margin: 0.25rem; font-size: 0.82rem; font-weight: 600;
    transition: all 0.25s; cursor: default;
}
.tag-badge:hover { background: var(--card-bg-hover); transform: translateY(-2px) scale(1.04); }

/* ── CONNECTION ROW ───────────────────────────────────────── */
.conn-row {
    display: flex; justify-content: space-between; align-items: center;
    flex-wrap: wrap; gap: 8px;
    background: var(--conn-bg); border-radius: 11px;
    padding: 0.85rem 1.2rem; margin: 0.3rem 0;
    border-left: 3px solid var(--card-border);
    transition: background 0.2s;
}
.conn-row:hover { background: var(--conn-hover); }

/* ── CLUSTER ──────────────────────────────────────────────── */
.cluster-wrap {
    background: var(--conn-bg); border-radius: 14px;
    padding: 1.1rem 1.4rem; margin: 0.5rem 0;
    border: 1px solid var(--card-border);
}
.cluster-title {
    font-size: 0.72rem; text-transform: uppercase; letter-spacing: 1.5px;
    color: var(--accent-2); margin-bottom: 0.5rem; font-weight: 700;
}
.cluster-pill {
    display: inline-flex; align-items: center; gap: 4px;
    background: rgba(197,168,255,0.15); border: 1px solid rgba(197,168,255,0.30);
    border-radius: 50px; padding: 0.28rem 0.8rem;
    margin: 0.2rem; font-size: 0.75rem; font-weight: 600; color: var(--accent-2);
}

/* ── PROGRESS BAR ─────────────────────────────────────────── */
.pbar-outer { background: var(--conn-bg); border-radius: 50px; height: 5px; margin: 3px 0; overflow: hidden; }
.pbar-inner { height: 100%; border-radius: 50px; transition: width 0.5s; }

/* ── ANIMAL BADGE ─────────────────────────────────────────── */
.animal-badge {
    display: inline-block;
    background: rgba(126,207,255,0.15); border: 1px solid rgba(126,207,255,0.35);
    color: var(--accent-1); padding: 0.3rem 0.9rem;
    border-radius: 50px; font-size: 0.82rem; font-weight: 700;
}

/* ── SECTION CARDS ────────────────────────────────────────── */
.sc { background: var(--conn-bg); border: 1px solid var(--card-border); border-radius: 12px; padding: 1.1rem; margin: 0.6rem 0; }
.sc-b { border-left: 4px solid var(--accent-1); }
.sc-g { border-left: 4px solid var(--accent-3); }
.sc-p { border-left: 4px solid var(--accent-2); }
.sc-a { border-left: 4px solid var(--accent-4); }
.sc-r { border-left: 4px solid var(--accent-red); }

/* ── DIVIDER ──────────────────────────────────────────────── */
.divider { height: 1px; background: linear-gradient(90deg, transparent, var(--divider), transparent); margin: 1.5rem 0; }

/* ── FILTER PANEL ─────────────────────────────────────────── */
.filter-panel {
    background: var(--card-bg); border: 1px solid var(--card-border);
    border-radius: 16px; padding: 1.4rem 1.8rem; margin: 1rem 0;
}

/* ── STREAMLIT OVERRIDES ──────────────────────────────────── */
.stButton > button {
    background: var(--btn-bg) !important;
    border: 1px solid var(--btn-border) !important;
    color: var(--text-main) !important;
    border-radius: 50px !important;
    padding: 0.75rem 2rem !important;
    font-weight: 700 !important; font-size: 0.92rem !important;
    transition: all 0.3s !important; letter-spacing: 0.3px !important;
    font-family: 'Inter', sans-serif !important;
}
.stButton > button:hover {
    background: var(--btn-hover-bg) !important;
    border-color: var(--accent-1) !important;
    transform: translateY(-3px) !important;
    box-shadow: 0 8px 24px var(--shadow) !important;
}
.stTextInput input, .stTextArea textarea {
    background: var(--input-bg) !important;
    border: 1px solid var(--input-border) !important;
    color: var(--text-main) !important;
    border-radius: 12px !important;
    padding: 0.8rem 1rem !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 500 !important;
}
.stTextInput input::placeholder, .stTextArea textarea::placeholder {
    color: var(--text-dim) !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
    border-color: var(--accent-1) !important;
    box-shadow: 0 0 0 3px rgba(126,207,255,0.15) !important;
}
.stSelectbox > div > div {
    background: var(--input-bg) !important;
    border: 1px solid var(--input-border) !important;
    color: var(--text-main) !important;
    border-radius: 12px !important;
}
.stSlider > div > div > div { background: var(--accent-1) !important; }
.stTabs [data-baseweb="tab-list"] {
    gap: 0.5rem; background: var(--conn-bg);
    backdrop-filter: blur(10px); padding: 0.4rem; border-radius: 12px;
    border: 1px solid var(--card-border);
}
.stTabs [data-baseweb="tab"] {
    background: transparent; border: 1px solid transparent;
    border-radius: 9px; color: var(--text-sub);
    padding: 0.6rem 1.2rem; font-weight: 600;
    transition: all 0.25s; font-size: 0.88rem;
}
.stTabs [data-baseweb="tab"]:hover { background: var(--btn-bg); color: var(--text-main); }
.stTabs [aria-selected="true"] {
    background: var(--btn-hover-bg) !important;
    border-color: var(--accent-1) !important;
    color: var(--accent-1) !important;
}
.stAlert { background: var(--card-bg) !important; border-radius: 12px !important; color: var(--text-main) !important; }
.stDataFrame, .stDataFrame table { background: var(--conn-bg) !important; color: var(--text-main) !important; border-radius: 12px !important; }
.stDataFrame th { background: var(--card-bg) !important; color: var(--text-main) !important; }
.stDataFrame td { color: var(--text-main) !important; }
div[data-testid="stExpander"] { background: var(--conn-bg) !important; border: 1px solid var(--card-border) !important; border-radius: 12px !important; }
.stCheckbox > label { color: var(--text-main) !important; }
.stRadio > label { color: var(--text-main) !important; }
#MainMenu, footer, header { visibility: hidden; }
.stDeployButton { display: none; }
[data-testid="stSidebar"] { display: none; }

@media (max-width: 768px) {
    .main-title { font-size: 2.2rem; }
    .main-content { margin-top: 90px; padding: 1rem; }
    .access-panel { bottom: 16px; right: 16px; }
}
</style>
""", unsafe_allow_html=True)


# ── ACCESSIBILITY & TTS JAVASCRIPT ─────────────────────────────────────────────
def inject_accessibility():
    st.markdown("""
<script>
// ── TTS (Text-to-Speech) ────────────────────────────────────
function speakText(text) {
    if (!('speechSynthesis' in window)) {
        alert('Seu navegador nao suporta sintese de voz.');
        return;
    }
    window.speechSynthesis.cancel();
    var u = new SpeechSynthesisUtterance(text);
    u.lang = 'pt-BR';
    u.rate = 0.88;
    u.pitch = 1.05;
    u.volume = 1.0;
    // Try to select a Portuguese voice
    var voices = window.speechSynthesis.getVoices();
    var ptVoice = voices.find(v => v.lang.startsWith('pt'));
    if (ptVoice) u.voice = ptVoice;
    window.speechSynthesis.speak(u);
}

function stopSpeech() {
    if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
    }
}

// Load voices asynchronously (needed for Chrome)
if ('speechSynthesis' in window) {
    window.speechSynthesis.onvoiceschanged = function() {
        window.speechSynthesis.getVoices();
    };
}

// ── Font Size ────────────────────────────────────────────────
function setFontSize(px, btnEl) {
    document.documentElement.style.fontSize = px + 'px';
    localStorage.setItem('sfd_font', px);
    document.querySelectorAll('.fs-btn').forEach(b => b.classList.remove('active-btn'));
    if (btnEl) btnEl.classList.add('active-btn');
}

// ── Theme ────────────────────────────────────────────────────
function setTheme(theme, btnEl) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('sfd_theme', theme);
    document.querySelectorAll('.theme-btn').forEach(b => b.classList.remove('active-btn'));
    if (btnEl) btnEl.classList.add('active-btn');
}

// ── Panel Toggle ─────────────────────────────────────────────
function toggleAccessPanel() {
    var body = document.getElementById('access-body');
    if (body) body.classList.toggle('open');
}

// ── Keyboard Shortcuts ────────────────────────────────────────
document.addEventListener('keydown', function(e) {
    if (e.altKey) {
        if (e.key === '1') setFontSize(14, null);
        else if (e.key === '2') setFontSize(16, null);
        else if (e.key === '3') setFontSize(18, null);
        else if (e.key === '4') setFontSize(20, null);
        else if (e.key === 't') {
            var cur = document.documentElement.getAttribute('data-theme') || 'dark';
            setTheme(cur === 'dark' ? 'light' : 'dark', null);
        }
        else if (e.key === 'c') setTheme('high-contrast', null);
        else if (e.key === 's') stopSpeech();
    }
});

// ── Restore preferences ───────────────────────────────────────
(function restorePrefs() {
    var savedFont  = localStorage.getItem('sfd_font');
    var savedTheme = localStorage.getItem('sfd_theme');
    if (savedFont)  document.documentElement.style.fontSize = savedFont + 'px';
    if (savedTheme) document.documentElement.setAttribute('data-theme', savedTheme);
    // Highlight active buttons after DOM settles
    setTimeout(function() {
        if (savedFont) {
            document.querySelectorAll('.fs-btn').forEach(function(b) {
                if (b.getAttribute('data-fs') === savedFont) b.classList.add('active-btn');
            });
        }
        if (savedTheme) {
            document.querySelectorAll('.theme-btn').forEach(function(b) {
                if (b.getAttribute('data-th') === savedTheme) b.classList.add('active-btn');
            });
        }
    }, 300);
})();
</script>

<div class="access-panel" role="region" aria-label="Painel de Acessibilidade">
    <button class="access-toggle" onclick="toggleAccessPanel()" aria-expanded="false"
            aria-controls="access-body" title="Abrir painel de acessibilidade (Alt+A)">
        Acessibilidade
    </button>
    <div class="access-panel-body" id="access-body" role="dialog" aria-label="Opcoes de acessibilidade">

        <div class="access-group">
            <div class="access-group-label">Tamanho do Texto</div>
            <div class="access-row">
                <button class="access-btn fs-btn" data-fs="14"
                        onclick="setFontSize(14, this)" aria-label="Texto pequeno (Alt+1)">A-</button>
                <button class="access-btn fs-btn active-btn" data-fs="16"
                        onclick="setFontSize(16, this)" aria-label="Texto normal (Alt+2)">A</button>
                <button class="access-btn fs-btn" data-fs="18"
                        onclick="setFontSize(18, this)" aria-label="Texto grande (Alt+3)">A+</button>
                <button class="access-btn fs-btn" data-fs="20"
                        onclick="setFontSize(20, this)" aria-label="Texto muito grande (Alt+4)">A++</button>
            </div>
        </div>

        <div class="access-divider"></div>

        <div class="access-group">
            <div class="access-group-label">Tema Visual</div>
            <div class="access-row">
                <button class="access-btn theme-btn active-btn" data-th="dark"
                        onclick="setTheme('dark', this)" aria-label="Tema escuro (Alt+T)">Escuro</button>
                <button class="access-btn theme-btn" data-th="light"
                        onclick="setTheme('light', this)" aria-label="Tema claro (Alt+T)">Claro</button>
                <button class="access-btn theme-btn" data-th="high-contrast"
                        onclick="setTheme('high-contrast', this)" aria-label="Alto contraste (Alt+C)">Contraste</button>
            </div>
        </div>

        <div class="access-divider"></div>

        <div class="access-group">
            <div class="access-group-label">Audiodesccricao</div>
            <div class="access-row">
                <button class="access-btn audio-btn-stop" onclick="stopSpeech()"
                        aria-label="Parar audio (Alt+S)" style="flex:1">
                    Parar Audio
                </button>
            </div>
        </div>

        <div class="access-divider"></div>

        <div class="access-shortcut">
            <strong style="color:var(--text-sub)">Atalhos de teclado</strong><br>
            Alt+1/2/3/4 — tamanho do texto<br>
            Alt+T — alternar escuro/claro<br>
            Alt+C — alto contraste<br>
            Alt+S — parar audio
        </div>
    </div>
</div>
""", unsafe_allow_html=True)


# ── HELPERS ────────────────────────────────────────────────────────────────────
def kpi(label, value, sub="", color="var(--accent-1)"):
    return (
        f"<div class='kpi-card'>"
        f"<div class='kpi-lbl'>{label}</div>"
        f"<div class='kpi-val' style='color:{color}'>{value}</div>"
        f"{'<div class=kpi-sub>' + sub + '</div>' if sub else ''}"
        f"</div>"
    )


def insight(text):
    return f"<div class='insight-box'>{text}</div>"


def divider():
    return "<div class='divider'></div>"


def pbar(pct, color="var(--accent-1)"):
    w = min(100, max(0, pct * 100))
    return (
        f"<div class='pbar-outer'>"
        f"<div class='pbar-inner' style='width:{w:.1f}%;background:{color}'></div>"
        f"</div>"
    )


# ── DATA LAYER ─────────────────────────────────────────────────────────────────
def check_admin():
    admins = load_json_file(ADMIN_FILE, [])
    if not admins:
        hashed = hashlib.sha256(ADMIN_PASSWORD.encode()).hexdigest()
        save_json_file(ADMIN_FILE, [{"id": 1, "username": ADMIN_USERNAME, "password": hashed}])


@st.cache_data(ttl=5, show_spinner=False)
def load_obras():
    default = [
        {"id": 1, "titulo": "Guernica", "artista": "Pablo Picasso", "ano": "1937",
         "descricao": "Obra simbolo do sofrimento humano durante a Guerra Civil Espanhola.",
         "imagem": "https://upload.wikimedia.org/wikipedia/en/7/74/PicassoGuernica.jpg"},
        {"id": 2, "titulo": "A Noite Estrelada", "artista": "Vincent van Gogh", "ano": "1889",
         "descricao": "Vista noturna da vila de Saint-Remy-de-Provence com ceu turbilhonante.",
         "imagem": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ea/Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg/1200px-Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg"},
        {"id": 3, "titulo": "Mona Lisa", "artista": "Leonardo da Vinci", "ano": "1503",
         "descricao": "Retrato renascentista de mulher com sorriso enigmatico, uma das obras mais famosas do mundo.",
         "imagem": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ec/Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_retouched.jpg/800px-Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_retouched.jpg"},
    ]
    obras = load_json_file(OBRAS_FILE, default)
    if not obras:
        save_json_file(OBRAS_FILE, default)
        return default
    return obras


def save_answers(uid, animal, answers):
    users = load_json_file(USERS_FILE, [])
    users.append({
        "user_id": uid, "animal_name": animal,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        **answers,
    })
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


def get_obra_user_tags(obra_id, uid):
    tags = load_json_file(TAGS_FILE, [])
    f = [t for t in tags if t["obra_id"] == obra_id and t["user_id"] == uid]
    if f:
        df = pd.DataFrame(f)
        c  = df["tag"].value_counts().reset_index()
        c.columns = ["tag", "count"]
        return c
    return pd.DataFrame(columns=["tag", "count"])


def get_user_tags(uid):
    tags = load_json_file(TAGS_FILE, [])
    ut   = [t for t in tags if t["user_id"] == uid]
    return pd.DataFrame(ut) if ut else pd.DataFrame()


def check_login(username, password):
    h = hashlib.sha256(password.encode()).hexdigest()
    return (username == ADMIN_USERNAME and
            h == hashlib.sha256(ADMIN_PASSWORD.encode()).hexdigest())


@st.cache_data(ttl=5, show_spinner=False)
def all_tags():
    t = load_json_file(TAGS_FILE, [])
    return pd.DataFrame(t) if t else pd.DataFrame()


@st.cache_data(ttl=5, show_spinner=False)
def all_users():
    u = load_json_file(USERS_FILE, [])
    return pd.DataFrame(u) if u else pd.DataFrame()


# ── EXPORT ────────────────────────────────────────────────────────────────────
def html_quest(uid, animal, users_df):
    if users_df.empty:
        return None
    ud = users_df[users_df["user_id"] == uid]
    if ud.empty:
        return None
    ui = ud.iloc[0]
    return f"""<!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8">
<title>Respostas do Questionario</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Segoe UI',sans-serif;background:linear-gradient(135deg,#000814,#001F3F);
padding:40px;color:white;min-height:100vh}}
.c{{max-width:860px;margin:0 auto;background:rgba(255,255,255,.12);
padding:50px;border-radius:24px;border:1px solid rgba(255,255,255,.25)}}
h1{{text-align:center;margin-bottom:12px;font-size:2rem;font-weight:800;letter-spacing:-1px}}
.hi{{text-align:center;margin-bottom:30px;opacity:.9;font-size:.95rem}}
.ab{{background:rgba(126,207,255,.2);border:1px solid rgba(126,207,255,.4);
color:#7ecfff;padding:.3rem 1rem;border-radius:50px;font-weight:700;display:inline-block}}
.qb{{margin:20px 0;padding:18px 22px;background:rgba(255,255,255,.08);
border-left:4px solid rgba(126,207,255,.5);border-radius:12px}}
.q{{font-weight:700;margin-bottom:8px;font-size:.95rem;color:#7ecfff}}
.a{{line-height:1.75;opacity:.92;font-size:.92rem}}
.ft{{text-align:center;margin-top:38px;padding-top:16px;
border-top:1px solid rgba(255,255,255,.15);opacity:.55;font-size:.82rem}}
</style></head>
<body><div class="c">
<h1>Respostas do Questionario</h1>
<div class="hi">
  <p>Usuario Anonimo: <span class="ab">{animal}</span></p>
  <p style="margin-top:6px;opacity:.6">Data: {ui.get('timestamp','N/A')}</p>
</div>
<div class="qb"><div class="q">1. Nivel de familiaridade com museus</div>
<div class="a">{ui.get('q1','N/A')}</div></div>
<div class="qb"><div class="q">2. Conhecimento sobre documentacao museologica</div>
<div class="a">{ui.get('q2','N/A')}</div></div>
<div class="qb"><div class="q">3. O que voce entende por tags?</div>
<div class="a">{ui.get('q3','N/A')}</div></div>
<div class="ft">Sistema Folksonomia Digital -- use Ctrl+P para salvar como PDF</div>
</div></body></html>"""


def html_tags(uid, animal, obras, tags_df):
    ut = tags_df[tags_df["user_id"] == uid] if not tags_df.empty else pd.DataFrame()
    if ut.empty:
        return None
    od    = {o["id"]: o["titulo"] for o in obras}
    rows  = "".join(
        f"<tr><td>{i+1}</td>"
        f"<td>{od.get(r['obra_id'], 'Obra ' + str(r['obra_id']))}</td>"
        f"<td><span style='background:rgba(126,207,255,.18);padding:3px 10px;border-radius:50px;"
        f"font-size:.82rem'>{r['tag']}</span></td>"
        f"<td>{r['timestamp']}</td></tr>"
        for i, (_, r) in enumerate(ut.iterrows())
    )
    top = "".join(
        f"<tr><td>{i}</td><td>{t}</td><td>{c}</td></tr>"
        for i, (t, c) in enumerate(ut["tag"].value_counts().head(10).items(), 1)
    )
    return f"""<!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8">
<title>Relatorio de Tags</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Segoe UI',sans-serif;background:linear-gradient(135deg,#000814,#001F3F);
padding:40px;color:white;min-height:100vh}}
.c{{max-width:1080px;margin:0 auto;background:rgba(255,255,255,.12);
padding:50px;border-radius:24px;border:1px solid rgba(255,255,255,.25)}}
h1{{text-align:center;margin-bottom:12px;font-size:2rem;font-weight:800}}
.hi{{text-align:center;margin-bottom:24px;opacity:.9}}
.ab{{background:rgba(126,207,255,.2);border:1px solid rgba(126,207,255,.4);
color:#7ecfff;padding:.3rem 1rem;border-radius:50px;font-weight:700;display:inline-block}}
.stats{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin:22px 0}}
.sb{{background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.2);
padding:18px;border-radius:12px;text-align:center}}
.sv{{font-size:2.4rem;font-weight:800;color:#7ecfff}}
.sl{{font-size:.75rem;text-transform:uppercase;letter-spacing:1.5px;margin-top:6px;opacity:.8}}
table{{width:100%;border-collapse:collapse;margin:16px 0}}
th,td{{padding:12px;text-align:left;border-bottom:1px solid rgba(255,255,255,.1);font-size:.88rem}}
th{{background:rgba(255,255,255,.15);font-weight:700;text-transform:uppercase;font-size:.75rem}}
tr:nth-child(even){{background:rgba(255,255,255,.04)}}
h2{{margin:26px 0 12px;font-size:1.35rem}}
.ft{{text-align:center;margin-top:36px;padding-top:16px;
border-top:1px solid rgba(255,255,255,.15);opacity:.55;font-size:.82rem}}
</style></head>
<body><div class="c">
<h1>Relatorio de Tags</h1>
<div class="hi">
  <p>Usuario Anonimo: <span class="ab">{animal}</span></p>
  <p style="margin-top:6px;opacity:.6">Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
</div>
<div class="stats">
  <div class="sb"><div class="sv">{len(ut)}</div><div class="sl">Total de Tags</div></div>
  <div class="sb"><div class="sv">{ut['tag'].nunique()}</div><div class="sl">Tags Unicas</div></div>
  <div class="sb"><div class="sv">{ut['obra_id'].nunique()}</div><div class="sl">Obras Etiquetadas</div></div>
</div>
<h2>Todas as Tags</h2>
<table><thead><tr><th>#</th><th>Obra</th><th>Tag</th><th>Data/Hora</th></tr></thead>
<tbody>{rows}</tbody></table>
<h2>Top 10 Tags</h2>
<table><thead><tr><th>Pos.</th><th>Tag</th><th>Frequencia</th></tr></thead>
<tbody>{top}</tbody></table>
<div class="ft">Sistema Folksonomia Digital -- use Ctrl+P para salvar como PDF</div>
</div></body></html>"""


# ── HEADER ────────────────────────────────────────────────────────────────────
def show_header(subtitle=""):
    st.markdown(
        f"<div class='top-navbar' role='banner'>"
        f"<div class='navbar-logo'>Sistema Folksonomia Digital</div>"
        f"<div class='navbar-info'>{subtitle}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )


# ── INTRO / QUESTIONNAIRE ─────────────────────────────────────────────────────
def show_intro():
    st.markdown("<div class='main-content'>", unsafe_allow_html=True)
    st.markdown("<h1 class='main-title'>Sistema Folksonomia Digital</h1>", unsafe_allow_html=True)
    st.markdown(
        "<p class='subtitle'>Plataforma colaborativa de catalogacao de obras de arte<br>"
        "Complete o questionario de perfil para acessar a galeria</p>",
        unsafe_allow_html=True,
    )
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.markdown(
        "<h2 style='text-align:center;margin-bottom:1.8rem;font-size:1.55rem'>"
        "Questionario de Acesso</h2>",
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
                "3. O que voce entende por tags ou etiquetas digitais aplicadas a acervo?",
                max_chars=600, height=210,
                placeholder="Descreva sua compreensao sobre o conceito de etiquetagem digital...",
            )
        _, cb, _ = st.columns([1, 1, 1])
        with cb:
            submit = st.form_submit_button("Acessar a Plataforma", use_container_width=True)
        if submit:
            if not q3.strip():
                st.error("Por favor, responda todas as perguntas para continuar.")
            else:
                st.session_state["answers"] = {"q1": q1, "q2": q2, "q3": q3}
                save_answers(
                    st.session_state["user_id"],
                    st.session_state["animal_name"],
                    st.session_state["answers"],
                )
                st.session_state["step"] = "completed"
                st.success("Questionario concluido. Acesso liberado.")
                st.balloons()
                st.rerun()
    st.markdown("</div></div>", unsafe_allow_html=True)


# ── GALLERY ───────────────────────────────────────────────────────────────────
def show_obras():
    st.markdown("<h1 class='main-title'>Galeria de Obras de Arte</h1>", unsafe_allow_html=True)
    st.markdown(
        "<p class='subtitle'>Explore as obras, ouva a audiodescricao e contribua com suas etiquetas</p>",
        unsafe_allow_html=True,
    )
    obras   = load_obras()
    tdf_all = all_tags()

    # ── ADVANCED FILTER PANEL ─────────────────────────────────
    with st.expander("Filtros e Ordenacao Avancada", expanded=True):
        r1c1, r1c2, r1c3 = st.columns(3)
        with r1c1:
            s_text = st.text_input(
                "Buscar por titulo ou artista:",
                placeholder="Ex: Picasso, Noite..."
            )
        with r1c2:
            s_tag = st.text_input(
                "Mostrar obras com a tag:",
                placeholder="Ex: azul, guerra..."
            )
        with r1c3:
            anos = []
            for o in obras:
                try:
                    anos.append(int(str(o.get("ano", "0"))[:4]))
                except ValueError:
                    pass
            if len(set(anos)) > 1:
                year_range = st.slider(
                    "Intervalo de ano:", min(anos), max(anos),
                    (min(anos), max(anos)), key="yr"
                )
            else:
                year_range = None

        r2c1, r2c2, r2c3 = st.columns(3)
        with r2c1:
            s_min_tags = st.number_input(
                "Numero minimo de tags recebidas:", min_value=0, value=0, step=1, key="mnt"
            )
        with r2c2:
            s_sort = st.selectbox(
                "Ordenar por:",
                ["Numero (crescente)", "Numero (decrescente)",
                 "Titulo A-Z", "Titulo Z-A", "Mais tags", "Menos tags"],
            )
        with r2c3:
            show_meta = st.checkbox("Exibir metadados da obra", value=True)

    # ── APPLY FILTERS ─────────────────────────────────────────
    filtered = list(obras)

    if s_text.strip():
        q = s_text.strip().lower()
        filtered = [
            o for o in filtered
            if q in o.get("titulo", "").lower() or q in o.get("artista", "").lower()
        ]

    if s_tag.strip() and not tdf_all.empty:
        t_lower = s_tag.strip().lower()
        obra_ids_with_tag = set(
            tdf_all[tdf_all["tag"].str.contains(t_lower, case=False, na=False)]["obra_id"].tolist()
        )
        filtered = [o for o in filtered if o["id"] in obra_ids_with_tag]

    if year_range:
        def year_ok(o):
            try:
                y = int(str(o.get("ano", "0"))[:4])
                return year_range[0] <= y <= year_range[1]
            except ValueError:
                return True
        filtered = [o for o in filtered if year_ok(o)]

    if s_min_tags > 0 and not tdf_all.empty:
        tag_counts = tdf_all.groupby("obra_id").size().to_dict()
        filtered = [o for o in filtered if tag_counts.get(o["id"], 0) >= s_min_tags]

    def sort_key(o):
        if s_sort == "Titulo A-Z":
            return o.get("titulo", "")
        elif s_sort == "Titulo Z-A":
            return o.get("titulo", "")
        elif s_sort in ("Mais tags", "Menos tags"):
            if not tdf_all.empty:
                tc = tdf_all.groupby("obra_id").size().to_dict()
                return tc.get(o["id"], 0)
            return 0
        return o["id"]

    reverse = s_sort in ("Numero (decrescente)", "Titulo Z-A", "Mais tags")
    filtered = sorted(filtered, key=sort_key, reverse=reverse)

    # ── RESULTS SUMMARY ───────────────────────────────────────
    tc_map = {}
    if not tdf_all.empty:
        tc_map = tdf_all.groupby("obra_id").size().to_dict()

    st.markdown(
        f"<div style='text-align:center;color:var(--text-sub);margin:1.2rem 0;"
        f"font-size:1rem;font-weight:600'>"
        f"Exibindo <strong style='color:var(--accent-1);font-size:1.3rem'>"
        f"{len(filtered)}</strong> obra(s)</div>",
        unsafe_allow_html=True,
    )

    if not filtered:
        st.info("Nenhuma obra encontrada com os filtros aplicados. Tente ajustar os criterios.")
        return

    cols = st.columns(3)
    for i, obra in enumerate(filtered):
        obra_id    = obra["id"]
        titulo     = obra.get("titulo", f"Obra {obra_id}")
        artista    = obra.get("artista", "Artista desconhecido")
        ano        = obra.get("ano", "")
        descricao  = obra.get("descricao", f"Obra de {artista}.")
        tag_count  = tc_map.get(obra_id, 0)
        audio_desc = build_audio_desc(obra, tdf_all)

        with cols[i % 3]:
            st.markdown(
                f"<div class='obra-card' role='article' aria-label='Obra: {titulo}'>"
                f"<img src='{obra['imagem']}' alt='Imagem da obra {titulo} de {artista}' "
                f"loading='lazy' />"
                f"<div class='obra-card-body'>"
                f"<div class='obra-card-title'>Obra #{obra_id} — {titulo}</div>"
                f"{'<div class=\"obra-card-meta\">' + artista + ' &mdash; ' + ano + '</div>' if show_meta else ''}"
                f"<div style='font-size:0.75rem;color:var(--text-dim);margin-bottom:0.6rem'>"
                f"{tag_count} tag(s) registrada(s)</div>"
                f"<button class='audio-btn' "
                f"onclick=\"speakText('{audio_desc.replace(chr(39), '')}')\" "
                f"aria-label='Ouvir audiodescricao da obra {titulo}'>"
                f"Ouvir Descricao</button>"
                f"</div></div>",
                unsafe_allow_html=True,
            )

            if show_meta and descricao:
                with st.expander("Sobre esta obra"):
                    st.write(descricao)

            if st.button("Adicionar Etiqueta", key=f"btn_{obra_id}", use_container_width=True):
                st.session_state["selected_obra"] = obra
                st.rerun()

            if (
                "selected_obra" in st.session_state
                and st.session_state["selected_obra"]["id"] == obra_id
            ):
                with st.form(f"tf_{obra_id}"):
                    tag = st.text_input(
                        "Sua etiqueta:",
                        key=f"t_{obra_id}",
                        placeholder="Ex: azul, melancolia, cubismo...",
                    )
                    ca, cb = st.columns(2)
                    with ca:
                        sub = st.form_submit_button("Enviar", use_container_width=True)
                    with cb:
                        can = st.form_submit_button("Cancelar", use_container_width=True)
                    if sub and tag.strip():
                        save_tag(st.session_state["user_id"], obra_id, tag.strip())
                        st.success(f"Etiqueta '{tag.strip()}' registrada com sucesso.")
                        del st.session_state["selected_obra"]
                        st.rerun()
                    if can:
                        del st.session_state["selected_obra"]
                        st.rerun()

            ut = get_obra_user_tags(obra_id, st.session_state["user_id"])
            if not ut.empty:
                st.markdown("<strong style='color:var(--text-sub);font-size:.82rem'>Suas etiquetas:</strong>",
                            unsafe_allow_html=True)
                st.markdown(
                    "".join(
                        f"<span class='tag-badge'>{r['tag']} ({r['count']})</span>"
                        for _, r in ut.iterrows()
                    ),
                    unsafe_allow_html=True,
                )
            else:
                st.caption("Voce ainda nao etiquetou esta obra.")


# ── ADMIN SHELL ───────────────────────────────────────────────────────────────
def show_admin():
    if "admin_logged_in" not in st.session_state:
        st.session_state["admin_logged_in"] = False

    if not st.session_state["admin_logged_in"]:
        st.markdown("<h1 class='main-title'>Area Administrativa</h1>", unsafe_allow_html=True)
        st.markdown("<p class='subtitle'>Acesso restrito aos gestores do sistema</p>", unsafe_allow_html=True)
        _, c2, _ = st.columns([1, 1, 1])
        with c2:
            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
            st.markdown(
                "<h2 style='text-align:center;margin-bottom:1.8rem'>Login Administrativo</h2>",
                unsafe_allow_html=True,
            )
            with st.form("login"):
                username = st.text_input("Usuario:", placeholder="Digite seu usuario")
                password = st.text_input("Senha:", type="password", placeholder="Digite sua senha")
                sub = st.form_submit_button("Entrar no Sistema", use_container_width=True)
                if sub:
                    if check_login(username, password):
                        st.session_state["admin_logged_in"] = True
                        st.session_state["admin_username"]  = username
                        st.success("Login realizado com sucesso.")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("Credenciais invalidas. Acesso negado.")
            st.markdown("</div>", unsafe_allow_html=True)
        return

    st.markdown(
        f"<h1 class='main-title'>Dashboard Administrativo</h1>"
        f"<p class='subtitle'>Bem-vindo, "
        f"<strong style='color:var(--accent-1)'>"
        f"{st.session_state.get('admin_username','Admin')}</strong></p>",
        unsafe_allow_html=True,
    )
    tabs = st.tabs([
        "Visao Geral",
        "Analise de Tags",
        "Conexoes",
        "Vocabulario",
        "Co-ocorrencias",
        "Usuarios",
        "Obras",
        "Exportar",
    ])
    with tabs[0]: tab_overview()
    with tabs[1]: tab_tags()
    with tabs[2]: tab_connections()
    with tabs[3]: tab_vocabulary()
    with tabs[4]: tab_cooccurrence()
    with tabs[5]: tab_users_quest()
    with tabs[6]: tab_obras()
    with tabs[7]: tab_export()

    _, c2, _ = st.columns([1, 1, 1])
    with c2:
        if st.button("Sair do Sistema", use_container_width=True):
            st.session_state["admin_logged_in"] = False
            st.rerun()


# ═════════════════════════════════════════════════════════════════
# TAB 1 — OVERVIEW
# ═════════════════════════════════════════════════════════════════
def tab_overview():
    tdf = all_tags()
    udf = all_users()
    obs = load_obras()

    st.markdown("### Metricas Gerais do Sistema")

    total   = len(tdf) if not tdf.empty else 0
    unicas  = tdf["tag"].nunique() if not tdf.empty else 0
    nusers  = udf["user_id"].nunique() if not udf.empty else 0
    nobs    = len(obs)
    obs_ct  = tdf["obra_id"].nunique() if not tdf.empty else 0
    med_tpu = f"{total/nusers:.1f}" if nusers else "—"

    c1, c2, c3, c4, c5 = st.columns(5)
    for col, lbl, val, sub, clr in [
        (c1, "Total de Tags",     total,   "registros",            "var(--accent-1)"),
        (c2, "Tags Unicas",       unicas,  f"{unicas/total:.0%} do total" if total else "—", "var(--accent-2)"),
        (c3, "Participantes",     nusers,  "usuarios ativos",      "var(--accent-3)"),
        (c4, "Obras Cadastradas", nobs,    f"{obs_ct} com tags",   "var(--accent-4)"),
        (c5, "Media Tags/Usario", med_tpu, "por participante",     "var(--accent-5)"),
    ]:
        with col:
            st.markdown(kpi(lbl, val, sub, clr), unsafe_allow_html=True)

    st.markdown(divider(), unsafe_allow_html=True)

    if not tdf.empty:
        od = {o["id"]: o.get("titulo", f"Obra {o['id']}") for o in obs}
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### Top 15 Tags Mais Usadas")
            top = tdf["tag"].value_counts().head(15).reset_index()
            top.columns = ["Tag", "Frequencia"]
            top["%"] = (top["Frequencia"] / top["Frequencia"].sum() * 100).round(1)
            st.dataframe(top, use_container_width=True, hide_index=True)
        with c2:
            st.markdown("#### Obras com Mais Etiquetas")
            ot = tdf.groupby("obra_id").size().reset_index(name="Tags")
            ot["Obra"] = ot["obra_id"].map(od)
            st.dataframe(
                ot[["Obra", "Tags"]].sort_values("Tags", ascending=False),
                use_container_width=True, hide_index=True,
            )

    if not udf.empty and not tdf.empty:
        st.markdown(divider(), unsafe_allow_html=True)
        st.markdown("#### Participantes Anonimos")
        uct = tdf.groupby("user_id").size().reset_index(name="tags")
        uuq = tdf.groupby("user_id")["tag"].nunique().reset_index(name="unicas")
        m   = udf.merge(uct, on="user_id", how="left").merge(uuq, on="user_id", how="left").fillna(0)
        for _, row in m.iterrows():
            animal = row.get("animal_name", "?")
            ts     = row.get("timestamp", "N/A")
            nt, nu = int(row["tags"]), int(row["unicas"])
            p      = nu / nt if nt > 0 else 0
            st.markdown(
                f"<div class='sc sc-b' style='padding:.85rem 1.3rem;margin:.25rem 0'>"
                f"<div style='display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px'>"
                f"<div><span class='animal-badge'>{animal}</span>"
                f"<span style='color:var(--text-dim);font-size:.72rem;margin-left:10px'>Acesso: {ts}</span></div>"
                f"<div style='text-align:right;min-width:180px'>"
                f"<span style='color:var(--text-main);font-weight:700'>{nt} tags</span>"
                f"<span style='color:var(--text-dim);font-size:.76rem'> ({nu} unicas)</span>"
                f"{pbar(p)}"
                f"<span style='color:var(--text-dim);font-size:.68rem'>riqueza: {p:.0%}</span>"
                f"</div></div></div>",
                unsafe_allow_html=True,
            )


# ═════════════════════════════════════════════════════════════════
# TAB 2 — TAG ANALYSIS
# ═════════════════════════════════════════════════════════════════
def tab_tags():
    tdf = all_tags()
    if tdf.empty:
        st.info("Nenhuma tag disponivel.")
        return

    st.markdown("### Analise de Tags")
    t1, t2 = st.tabs(["Frequencia e Vocabulario", "Evolucao Temporal"])

    with t1:
        freq = tdf["tag"].value_counts().reset_index()
        freq.columns = ["Tag", "Frequencia"]
        total_usos = freq["Frequencia"].sum()
        freq["% do Total"]  = (freq["Frequencia"] / total_usos * 100).round(2)
        freq["% Acumulada"] = freq["% do Total"].cumsum().round(2)
        freq["Categoria"]   = freq["Tag"].apply(categorize_tag)
        freq["Comprimento"] = freq["Tag"].str.len()
        freq["Palavras"]    = freq["Tag"].str.split().str.len()

        hapax  = (freq["Frequencia"] == 1).sum()
        lei80  = (freq["% Acumulada"] <= 80).sum()
        ttr    = len(freq) / total_usos if total_usos else 0
        entropy = -sum(
            (c / total_usos) * math.log2(c / total_usos)
            for c in freq["Frequencia"] if c > 0
        ) if total_usos > 0 else 0

        c1, c2, c3, c4 = st.columns(4)
        with c1: st.markdown(kpi("Vocabulario", len(freq), "tags distintas", "var(--accent-1)"), unsafe_allow_html=True)
        with c2: st.markdown(kpi("Hapax Legomena", hapax, f"{hapax/len(freq):.0%} do vocab.", "var(--accent-5)"), unsafe_allow_html=True)
        with c3: st.markdown(kpi("80% dos Usos", f"{lei80} tags", "lei de Zipf", "var(--accent-3)"), unsafe_allow_html=True)
        with c4: st.markdown(kpi("Entropia", f"{entropy:.2f} bits", "diversidade", "var(--accent-4)"), unsafe_allow_html=True)

        st.markdown(insight(
            f"<strong>Distribuicao de Zipf:</strong> As {lei80} tags mais frequentes cobrem 80% de todos os usos. "
            f"Existem {hapax} hapax legomena ({hapax/len(freq):.0%} do vocabulario). "
            f"TTR global de <strong>{ttr:.3f}</strong> indica "
            f"{'alta' if ttr > 0.5 else 'moderada' if ttr > 0.25 else 'baixa'} diversidade lexical. "
            f"Entropia de <strong>{entropy:.2f} bits</strong> mede a imprevisibilidade do vocabulario."
        ), unsafe_allow_html=True)

        st.markdown(divider(), unsafe_allow_html=True)
        st.markdown("#### Top 25 Tags por Frequencia")
        st.bar_chart(tdf["tag"].value_counts().head(25))

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### Distribuicao por Categoria Semantica")
            cat_counts = freq.groupby("Categoria")["Frequencia"].sum().sort_values(ascending=False)
            st.bar_chart(cat_counts)
        with c2:
            st.markdown("#### Distribuicao por Comprimento de Tag")
            st.bar_chart(freq["Comprimento"].value_counts().sort_index().rename("Qtd Tags"))

        st.markdown(divider(), unsafe_allow_html=True)
        st.markdown("#### Tabela Completa de Frequencias")
        cat_opts = sorted(freq["Categoria"].unique())
        cat_sel  = st.multiselect("Filtrar por categoria:", cat_opts, default=cat_opts, key="fc")
        disp = freq[freq["Categoria"].isin(cat_sel)] if cat_sel else freq
        st.dataframe(disp, use_container_width=True, hide_index=True)

        c1, c2 = st.columns(2)
        with c1:
            st.download_button(
                "Baixar Frequencias (CSV)",
                freq.to_csv(index=False).encode("utf-8"),
                f"frequencias_{datetime.now().strftime('%Y%m%d')}.csv",
                "text/csv", use_container_width=True,
            )
        with c2:
            cd = freq.groupby("Categoria").agg(
                Tags=("Tag", "count"), Usos=("Frequencia", "sum")
            ).reset_index().sort_values("Usos", ascending=False)
            st.dataframe(cd, use_container_width=True, hide_index=True)

    with t2:
        st.markdown("#### Evolucao Temporal das Etiquetas")
        try:
            tf = tdf.copy()
            tf["ts"]   = pd.to_datetime(tf["timestamp"])
            tf["date"] = tf["ts"].dt.date
            tf["ano"]  = tf["ts"].dt.year
            tf["mes"]  = tf["ts"].dt.month
            tf["hora"] = tf["ts"].dt.hour
            tf["dow"]  = tf["ts"].dt.day_name()

            dias_ativos = tf["date"].nunique()
            pico_dia    = tf.groupby("date").size()
            pico_val    = int(pico_dia.max()) if not pico_dia.empty else 0
            pico_dt     = str(pico_dia.idxmax()) if not pico_dia.empty else "—"
            media_dia   = len(tf) / dias_ativos if dias_ativos else 0

            c1, c2, c3, c4 = st.columns(4)
            with c1: st.markdown(kpi("Dias com Atividade", dias_ativos, "dias", "var(--accent-1)"), unsafe_allow_html=True)
            with c2: st.markdown(kpi("Media por Dia", f"{media_dia:.1f}", "tags/dia", "var(--accent-3)"), unsafe_allow_html=True)
            with c3: st.markdown(kpi("Pico de Tags", pico_val, f"em {pico_dt}", "var(--accent-4)"), unsafe_allow_html=True)
            with c4: st.markdown(kpi("Anos Registrados", tf["ano"].nunique(), "anos", "var(--accent-2)"), unsafe_allow_html=True)

            st.markdown(divider(), unsafe_allow_html=True)

            daily = tf.groupby("date").agg(
                Tags=("tag", "count"),
                Tags_Unicas=("tag", "nunique"),
                Usuarios=("user_id", "nunique"),
            ).reset_index().rename(columns={"date": "Data"})

            st.markdown("#### Tags por Dia")
            st.line_chart(daily.set_index("Data")[["Tags", "Tags_Unicas"]])

            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Usuarios ativos por dia**")
                st.line_chart(daily.set_index("Data")["Usuarios"])
            with c2:
                st.markdown("**Distribuicao por hora do dia**")
                st.bar_chart(tf["hora"].value_counts().sort_index().rename("Tags"))

            meses_pt = {1:"Jan",2:"Fev",3:"Mar",4:"Abr",5:"Mai",6:"Jun",
                        7:"Jul",8:"Ago",9:"Set",10:"Out",11:"Nov",12:"Dez"}
            monthly = tf.groupby(["ano", "mes"]).agg(
                Tags=("tag", "count"),
                Tags_Unicas=("tag", "nunique"),
                Usuarios=("user_id", "nunique"),
            ).reset_index()
            monthly["Mes/Ano"] = monthly["mes"].map(meses_pt) + "/" + monthly["ano"].astype(str)
            monthly = monthly.sort_values(["ano", "mes"])

            st.markdown(divider(), unsafe_allow_html=True)
            st.markdown("#### Distribuicao Mensal")
            st.bar_chart(monthly.set_index("Mes/Ano")["Tags"])

            st.markdown("#### Tabela Diaria Detalhada")
            daily_full = tf.groupby("date").agg(
                Total=("tag", "count"),
                Unicas=("tag", "nunique"),
                Usuarios=("user_id", "nunique"),
                Tag_Top=("tag", lambda x: x.value_counts().index[0] if len(x) else "—"),
            ).reset_index()
            daily_full.columns = ["Data", "Tags", "Unicas", "Usuarios", "Tag Mais Usada"]
            st.dataframe(daily_full.sort_values("Data", ascending=False),
                         use_container_width=True, hide_index=True)

        except Exception:
            st.info("Dados insuficientes para analise temporal.")


# ═════════════════════════════════════════════════════════════════
# TAB 3 — CONNECTIONS
# ═════════════════════════════════════════════════════════════════
def tab_connections():
    tdf = all_tags()
    obs = load_obras()
    od  = {o["id"]: o.get("titulo", f"Obra {o['id']}") for o in obs}
    if tdf.empty:
        st.warning("Nenhuma tag disponivel.")
        return

    st.markdown("### Conexoes e Agrupamentos de Tags")
    st.markdown(insight(
        "<strong>Como funciona:</strong> O algoritmo combina tres metricas: "
        "<strong>Contencao de substring</strong> (ex: 'vaso' -> 'vaso verde'), "
        "<strong>Jaccard de palavras</strong> (termos compartilhados) e "
        "<strong>Jaccard de trigramas</strong> (similaridade fonetica). "
        "Score de 0 (sem relacao) a 1 (identicas)."
    ), unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1: threshold = st.slider("Limiar de similaridade:", 0.20, 0.90, 0.35, 0.05, key="ct")
    with c2:
        obra_f = st.selectbox(
            "Filtrar por obra:",
            ["Todas"] + [f"#{o['id']} — {o.get('titulo', '')}" for o in obs],
            key="co",
        )
    with c3: max_c = st.number_input("Max. conexoes exibidas:", 10, 500, 80, 10, key="cm")

    fdf = tdf.copy()
    if obra_f != "Todas":
        oid = int(obra_f.split("—")[0].replace("#", "").strip())
        fdf = tdf[tdf["obra_id"] == oid]

    all_t = fdf["tag"].tolist()
    if len(set(all_t)) < 2:
        st.warning("Necessario ao menos 2 tags distintas.")
        return

    with st.spinner("Calculando conexoes..."):
        conns    = tag_connections(all_t, threshold=threshold)
        clusters = tag_clusters(all_t, threshold=threshold)

    c1, c2, c3 = st.columns(3)
    with c1: st.markdown(kpi("Total de Conexoes", len(conns), f"limiar >= {threshold:.2f}", "var(--accent-1)"), unsafe_allow_html=True)
    with c2: st.markdown(kpi("Grupos Formados", len(clusters), "clusters de tags", "var(--accent-2)"), unsafe_allow_html=True)
    involved = len(set(c["tag_a"] for c in conns) | set(c["tag_b"] for c in conns))
    with c3: st.markdown(kpi("Tags Conectadas", involved, "tags em relacao", "var(--accent-3)"), unsafe_allow_html=True)

    st.markdown(divider(), unsafe_allow_html=True)
    t1, t2 = st.tabs(["Lista de Conexoes", "Grupos de Tags"])

    with t1:
        if not conns:
            st.info("Nenhuma conexao encontrada. Reduza o limiar.")
        else:
            tipos    = sorted(set(c["tipo"] for c in conns))
            tipo_sel = st.multiselect("Filtrar por tipo:", tipos, default=tipos, key="tsel")
            cf       = [c for c in conns if c["tipo"] in tipo_sel][:max_c]
            freq_map = tdf["tag"].value_counts().to_dict()

            st.markdown(f"Exibindo **{len(cf)}** de **{len(conns)}** conexoes")
            st.markdown(divider(), unsafe_allow_html=True)

            for c in cf:
                s   = c["similaridade"]
                bar = "=" * int(s * 12) + "-" * (12 - int(s * 12))
                fa  = freq_map.get(c["tag_a"], 0)
                fb  = freq_map.get(c["tag_b"], 0)
                st.markdown(
                    f"<div class='conn-row'>"
                    f"<div style='display:flex;align-items:center;gap:10px;flex-wrap:wrap'>"
                    f"<span class='tag-badge'>{c['tag_a']}</span>"
                    f"<span style='color:var(--text-dim);font-size:.7rem'>({fa}x)</span>"
                    f"<span style='color:var(--text-dim)'>&#8596;</span>"
                    f"<span class='tag-badge'>{c['tag_b']}</span>"
                    f"<span style='color:var(--text-dim);font-size:.7rem'>({fb}x)</span>"
                    f"</div>"
                    f"<div style='text-align:right;min-width:195px'>"
                    f"<span style='font-family:monospace;color:var(--text-sub);font-size:.75rem'>"
                    f"[{bar}] {s:.3f}</span><br>"
                    f"<span style='font-size:.68rem;color:var(--text-dim)'>{c['tipo']}</span>"
                    f"</div></div>",
                    unsafe_allow_html=True,
                )

            st.markdown(divider(), unsafe_allow_html=True)
            st.download_button(
                "Baixar Conexoes (CSV)",
                pd.DataFrame(conns).to_csv(index=False).encode("utf-8"),
                f"conexoes_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv",
            )

    with t2:
        if not clusters:
            st.info("Nenhum grupo formado. Reduza o limiar.")
        else:
            COLORS = ["var(--accent-1)","var(--accent-2)","var(--accent-3)",
                      "var(--accent-4)","var(--accent-5)","var(--accent-red)"]
            freq_map   = tdf["tag"].value_counts().to_dict()
            cls_sorted = sorted(clusters, key=len, reverse=True)

            for i, cl in enumerate(cls_sorted, 1):
                color      = COLORS[(i-1) % len(COLORS)]
                total_uses = sum(freq_map.get(t, 0) for t in cl)
                pills = "".join(
                    f"<span class='cluster-pill'>{t} "
                    f"<span style='opacity:.5;font-size:.68rem'>({freq_map.get(t,0)}x)</span></span>"
                    for t in sorted(cl, key=lambda x: freq_map.get(x, 0), reverse=True)
                )
                st.markdown(
                    f"<div class='cluster-wrap' style='border-left:3px solid {color}'>"
                    f"<div class='cluster-title'>Grupo {i} · {len(cl)} tags · {total_uses} usos totais</div>"
                    f"{pills}</div>",
                    unsafe_allow_html=True,
                )

            st.markdown(divider(), unsafe_allow_html=True)
            summ = pd.DataFrame([{
                "Grupo": f"Grupo {i}",
                "Qtd Tags": len(cl),
                "Total Usos": sum(freq_map.get(t, 0) for t in cl),
                "Tags (top 6)": ", ".join(
                    sorted(cl, key=lambda x: freq_map.get(x, 0), reverse=True)[:6]
                ) + ("..." if len(cl) > 6 else ""),
            } for i, cl in enumerate(cls_sorted, 1)])
            st.dataframe(summ, use_container_width=True, hide_index=True)
            st.download_button(
                "Baixar Grupos (CSV)",
                summ.to_csv(index=False).encode("utf-8"),
                f"clusters_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv",
            )


# ═════════════════════════════════════════════════════════════════
# TAB 4 — VOCABULARY (NEW)
# ═════════════════════════════════════════════════════════════════
def tab_vocabulary():
    tdf = all_tags()
    if tdf.empty:
        st.info("Nenhuma tag disponivel.")
        return

    st.markdown("### Analise de Vocabulario")
    st.markdown(insight(
        "<strong>Riqueza Vocabular:</strong> Esta secao analisa a diversidade e complexidade do vocabulario "
        "produzido coletivamente. Metricas como TTR, Hapax Legomena e Entropia de Shannon revelam "
        "o quanto o repertorio de etiquetas e variado, original e distribuido."
    ), unsafe_allow_html=True)

    tokens  = tdf["tag"].str.lower().str.strip().tolist()
    metrics = vocabulary_metrics(tokens)

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: st.markdown(kpi("Total Tokens (N)", metrics["N"], "ocorrencias totais", "var(--accent-1)"), unsafe_allow_html=True)
    with c2: st.markdown(kpi("Types (V)", metrics["V"], "formas distintas", "var(--accent-2)"), unsafe_allow_html=True)
    with c3: st.markdown(kpi("TTR Global", f"{metrics['TTR']:.4f}", "riqueza vocabular", "var(--accent-3)"), unsafe_allow_html=True)
    with c4: st.markdown(kpi("Hapax Legomena", metrics["Hapax"], f"{metrics['Hapax']/metrics['V']:.0%} do vocab", "var(--accent-4)"), unsafe_allow_html=True)
    with c5: st.markdown(kpi("Entropia (H)", f"{metrics['Entropy']} bits", "Shannon", "var(--accent-5)"), unsafe_allow_html=True)

    st.markdown(divider(), unsafe_allow_html=True)

    # ── Frequency spectrum ─────────────────────────────────────
    freq = tdf["tag"].value_counts()
    spectrum = freq.value_counts().sort_index()
    st.markdown("#### Espectro de Frequencias (Quantas tags aparecem N vezes?)")
    st.bar_chart(spectrum.rename("Qtd de Tags"))

    st.markdown(insight(
        f"<strong>Espectro:</strong> Tags que aparecem apenas 1 vez (hapax): <strong>{metrics['Hapax']}</strong>. "
        f"A distribuicao segue a lei de Zipf: poucos termos concentram a maioria dos usos, "
        f"enquanto a maioria dos termos e raro. "
        f"Entropia de <strong>{metrics['Entropy']} bits</strong>: "
        f"{'vocabulario muito diversificado' if metrics['Entropy'] > 4 else 'vocabulario moderadamente concentrado' if metrics['Entropy'] > 2 else 'vocabulario concentrado em poucos termos'}."
    ), unsafe_allow_html=True)

    st.markdown(divider(), unsafe_allow_html=True)

    # ── Category breakdown ─────────────────────────────────────
    st.markdown("#### Distribuicao por Categoria Semantica")
    freq_df = freq.reset_index()
    freq_df.columns = ["Tag", "Frequencia"]
    freq_df["Categoria"] = freq_df["Tag"].apply(categorize_tag)
    freq_df["Comprimento"] = freq_df["Tag"].str.len()
    freq_df["Multi-palavra"] = freq_df["Tag"].str.split().str.len() > 1

    c1, c2 = st.columns(2)
    with c1:
        cat_stat = freq_df.groupby("Categoria").agg(
            Tags_Unicas=("Tag", "count"),
            Usos_Totais=("Frequencia", "sum"),
            Media_Comprimento=("Comprimento", "mean"),
        ).round(2).reset_index().sort_values("Usos_Totais", ascending=False)
        st.dataframe(cat_stat, use_container_width=True, hide_index=True)
    with c2:
        cat_usos = freq_df.groupby("Categoria")["Frequencia"].sum().sort_values(ascending=False)
        st.bar_chart(cat_usos)

    st.markdown(divider(), unsafe_allow_html=True)

    # ── Tag length ─────────────────────────────────────────────
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Distribuicao de Comprimento de Tags (caracteres)")
        st.bar_chart(freq_df["Comprimento"].value_counts().sort_index().rename("Qtd Tags"))
    with c2:
        st.markdown("#### Tags Simples vs Multi-palavra")
        mp = freq_df["Multi-palavra"].value_counts().rename(index={True: "Multi-palavra", False: "Palavra unica"})
        st.bar_chart(mp)

    st.markdown(divider(), unsafe_allow_html=True)

    # ── TTR per user ───────────────────────────────────────────
    udf = all_users()
    if not udf.empty:
        st.markdown("#### TTR por Participante (Riqueza Individual)")
        rows = []
        for _, ur in udf.iterrows():
            uid  = ur["user_id"]
            name = ur.get("animal_name", uid[:8])
            utags = tdf[tdf["user_id"] == uid]["tag"].tolist()
            if utags:
                m = vocabulary_metrics(utags)
                rows.append({
                    "Participante": name, "N": m["N"], "V": m["V"],
                    "TTR": m["TTR"], "Hapax": m["Hapax"], "Entropia": m["Entropy"],
                })
        if rows:
            ttr_df = pd.DataFrame(rows).sort_values("TTR", ascending=False)
            st.dataframe(ttr_df, use_container_width=True, hide_index=True)
            st.bar_chart(ttr_df.set_index("Participante")["TTR"])
            st.markdown(insight(
                f"<strong>TTR medio dos participantes:</strong> {ttr_df['TTR'].mean():.4f}. "
                f"TTR proximo de 1.0 indica alta originalidade (sem repeticao). "
                f"TTR proximo de 0 indica forte concentracao em poucos termos."
            ), unsafe_allow_html=True)

    # ── Download ───────────────────────────────────────────────
    st.markdown(divider(), unsafe_allow_html=True)
    st.download_button(
        "Baixar Analise de Frequencias (CSV)",
        freq_df.to_csv(index=False).encode("utf-8"),
        f"vocabulario_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv",
    )


# ═════════════════════════════════════════════════════════════════
# TAB 5 — CO-OCCURRENCE (NEW)
# ═════════════════════════════════════════════════════════════════
def tab_cooccurrence():
    tdf = all_tags()
    obs = load_obras()
    od  = {o["id"]: o.get("titulo", f"Obra {o['id']}") for o in obs}
    if tdf.empty:
        st.info("Nenhuma tag disponivel.")
        return

    st.markdown("### Co-ocorrencia de Tags")
    st.markdown(insight(
        "<strong>Co-ocorrencia:</strong> Duas tags co-ocorrem quando ambas sao aplicadas a mesma obra "
        "(por qualquer participante). Altas frequencias de co-ocorrencia indicam associacoes "
        "semanticas fortes no imaginario coletivo dos usuarios."
    ), unsafe_allow_html=True)

    obra_f = st.selectbox(
        "Filtrar por obra:",
        ["Todas"] + [f"#{o['id']} — {o.get('titulo', '')}" for o in obs],
        key="coo_obra",
    )
    fdf = tdf.copy()
    if obra_f != "Todas":
        oid = int(obra_f.split("—")[0].replace("#", "").strip())
        fdf = tdf[tdf["obra_id"] == oid]

    with st.spinner("Calculando co-ocorrencias..."):
        cooc_df = tag_cooccurrence(fdf)

    if cooc_df.empty:
        st.info("Sem co-ocorrencias. Cada obra precisa ter ao menos 2 tags distintas.")
        return

    c1, c2, c3 = st.columns(3)
    with c1: st.markdown(kpi("Pares Unicos", len(cooc_df), "co-ocorrencias", "var(--accent-1)"), unsafe_allow_html=True)
    with c2: st.markdown(kpi("Max Co-ocorrencias", int(cooc_df["Co-ocorrencias"].max()), cooc_df.iloc[0]["Tag A"] + " + " + cooc_df.iloc[0]["Tag B"], "var(--accent-2)"), unsafe_allow_html=True)
    with c3: st.markdown(kpi("Tags Envolvidas", len(set(cooc_df["Tag A"]) | set(cooc_df["Tag B"])), "tags distintas", "var(--accent-3)"), unsafe_allow_html=True)

    st.markdown(divider(), unsafe_allow_html=True)

    t1, t2, t3 = st.tabs(["Top Pares", "Por Obra", "Tabela Completa"])

    with t1:
        n_top = st.slider("Mostrar top N pares:", 5, 50, 20, key="coo_top")
        top_cooc = cooc_df.head(n_top)
        st.markdown(f"#### Top {n_top} Pares de Tags Mais Co-ocorrentes")
        freq_map = tdf["tag"].value_counts().to_dict()
        for _, row in top_cooc.iterrows():
            fa = freq_map.get(row["Tag A"], 0)
            fb = freq_map.get(row["Tag B"], 0)
            n  = int(row["Co-ocorrencias"])
            st.markdown(
                f"<div class='conn-row'>"
                f"<div style='display:flex;align-items:center;gap:10px;flex-wrap:wrap'>"
                f"<span class='tag-badge'>{row['Tag A']}</span>"
                f"<span style='color:var(--text-dim);font-size:.7rem'>({fa}x)</span>"
                f"<span style='color:var(--accent-3);font-weight:700;font-size:.9rem'>+</span>"
                f"<span class='tag-badge'>{row['Tag B']}</span>"
                f"<span style='color:var(--text-dim);font-size:.7rem'>({fb}x)</span>"
                f"</div>"
                f"<div style='text-align:right'>"
                f"<span style='color:var(--accent-3);font-weight:800;font-size:1.1rem'>{n}</span>"
                f"<span style='color:var(--text-dim);font-size:.7rem'> co-ocorrencias</span>"
                f"</div></div>",
                unsafe_allow_html=True,
            )

    with t2:
        st.markdown("#### Co-ocorrencias por Obra")
        obra_cooc = fdf.groupby("obra_id").apply(
            lambda x: len(x["tag"].unique()) * (len(x["tag"].unique()) - 1) // 2
        ).reset_index()
        obra_cooc.columns = ["Obra ID", "Pares Possiveis"]
        obra_cooc["Obra"] = obra_cooc["Obra ID"].map(od)
        obra_cooc = obra_cooc.sort_values("Pares Possiveis", ascending=False)
        st.dataframe(obra_cooc[["Obra", "Pares Possiveis"]],
                     use_container_width=True, hide_index=True)

        st.markdown(divider(), unsafe_allow_html=True)
        st.markdown("#### Tags mais frequentemente associadas a cada obra")
        for o in obs:
            ot = fdf[fdf["obra_id"] == o["id"]]
            if ot.empty:
                continue
            top3 = ot["tag"].value_counts().head(5).index.tolist()
            pills = "".join(f"<span class='tag-badge'>{t}</span>" for t in top3)
            st.markdown(
                f"<div class='sc sc-b' style='padding:.85rem 1.3rem;margin:.3rem 0'>"
                f"<strong style='color:var(--accent-1)'>Obra #{o['id']} — {o.get('titulo','')}</strong>"
                f"<div style='margin-top:.5rem'>{pills}</div></div>",
                unsafe_allow_html=True,
            )

    with t3:
        min_cooc = st.number_input("Co-ocorrencias minimas:", 1, 100, 1, key="coo_min")
        filtered_cooc = cooc_df[cooc_df["Co-ocorrencias"] >= min_cooc]
        st.markdown(f"Exibindo **{len(filtered_cooc)}** pares com >= {min_cooc} co-ocorrencia(s)")
        st.dataframe(filtered_cooc, use_container_width=True, hide_index=True)
        st.download_button(
            "Baixar Co-ocorrencias (CSV)",
            filtered_cooc.to_csv(index=False).encode("utf-8"),
            f"coocorrencias_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv",
        )


# ═════════════════════════════════════════════════════════════════
# TAB 6 — USERS & QUESTIONNAIRE
# ═════════════════════════════════════════════════════════════════
def tab_users_quest():
    tdf = all_tags()
    udf = all_users()
    obs = load_obras()
    od  = {o["id"]: o.get("titulo", f"Obra {o['id']}") for o in obs}

    if udf.empty:
        st.info("Nenhum dado de usuario disponivel.")
        return

    st.markdown("### Usuarios e Questionario")

    uct = tdf.groupby("user_id").size().reset_index(name="Total_Tags") if not tdf.empty else pd.DataFrame(columns=["user_id","Total_Tags"])
    uuq = tdf.groupby("user_id")["tag"].nunique().reset_index(name="Tags_Unicas") if not tdf.empty else pd.DataFrame(columns=["user_id","Tags_Unicas"])
    uob = tdf.groupby("user_id")["obra_id"].nunique().reset_index(name="Obras") if not tdf.empty else pd.DataFrame(columns=["user_id","Obras"])
    merged = udf.merge(uct, on="user_id", how="left") \
                .merge(uuq, on="user_id", how="left") \
                .merge(uob, on="user_id", how="left").fillna(0)
    merged["TTR"]     = (merged["Tags_Unicas"] / merged["Total_Tags"].replace(0, np.nan)).fillna(0).round(3)
    merged["Usuario"] = merged.apply(lambda r: r.get("animal_name", r["user_id"][:8]), axis=1)

    c1, c2, c3, c4 = st.columns(4)
    top_u = merged.loc[merged["Total_Tags"].idxmax(), "Usuario"] if not merged.empty else "—"
    with c1: st.markdown(kpi("Participantes",    len(merged),                  "usuarios",       "var(--accent-1)"), unsafe_allow_html=True)
    with c2: st.markdown(kpi("Media Tags/Usr",   f"{merged['Total_Tags'].mean():.1f}", "",       "var(--accent-3)"), unsafe_allow_html=True)
    with c3: st.markdown(kpi("Maior Contribui.", int(merged["Total_Tags"].max()), top_u[:16],    "var(--accent-4)"), unsafe_allow_html=True)
    with c4: st.markdown(kpi("Riqueza Media TTR",f"{merged['TTR'].mean():.2%}", "vocabular",     "var(--accent-2)"), unsafe_allow_html=True)

    st.markdown(divider(), unsafe_allow_html=True)

    t1, t2, t3, t4 = st.tabs([
        "Tabela de Participantes",
        "Perfil Individual",
        "Questionario",
        "Cruzamentos",
    ])

    with t1:
        st.markdown("#### Comparativo Geral")
        dcols = ["Usuario","Total_Tags","Tags_Unicas","TTR","Obras","q1","q2"]
        avail = [c for c in dcols if c in merged.columns]
        disp  = merged[avail].rename(columns={
            "Total_Tags": "Tags Criadas", "Tags_Unicas": "Tags Unicas",
            "Obras": "Obras Etiquetadas", "q1": "Familiaridade c/ Museus",
            "q2": "Conhec. Museologico",
        }).sort_values("Tags Criadas", ascending=False)
        st.dataframe(disp, use_container_width=True, hide_index=True)

        st.markdown(divider(), unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("**Contribuicao por Participante**")
            st.bar_chart(merged.set_index("Usuario")["Total_Tags"].sort_values(ascending=False))
        with c2:
            st.markdown("**Riqueza Vocabular (TTR)**")
            st.bar_chart(merged.set_index("Usuario")["TTR"].sort_values(ascending=False))
        with c3:
            st.markdown("**Obras Etiquetadas**")
            st.bar_chart(merged.set_index("Usuario")["Obras"].sort_values(ascending=False))

    with t2:
        uopts = [f"{r.get('animal_name', r['user_id'][:8])}" for _, r in udf.iterrows()]
        usel  = st.selectbox("Selecione um participante:", uopts, key="ui_sel")
        uidx  = uopts.index(usel)
        uid   = udf.iloc[uidx]["user_id"]
        uanim = udf.iloc[uidx].get("animal_name", uid[:8])

        utags = tdf[tdf["user_id"] == uid] if not tdf.empty else pd.DataFrame()
        if utags.empty:
            st.info("Este participante ainda nao criou tags.")
        else:
            ttl = len(utags); unq = utags["tag"].nunique()
            ttr_u = unq / ttl if ttl else 0
            um  = vocabulary_metrics(utags["tag"].tolist())

            c1, c2, c3, c4 = st.columns(4)
            with c1: st.markdown(kpi("Tags Criadas",  ttl,  "", "var(--accent-1)"), unsafe_allow_html=True)
            with c2: st.markdown(kpi("Tags Unicas",   unq,  f"TTR: {ttr_u:.3f}", "var(--accent-3)"), unsafe_allow_html=True)
            with c3: st.markdown(kpi("Obras Tagueadas", utags["obra_id"].nunique(), "", "var(--accent-4)"), unsafe_allow_html=True)
            with c4: st.markdown(kpi("Entropia H",    f"{um['Entropy']} bits", "Shannon", "var(--accent-2)"), unsafe_allow_html=True)

            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"**Top tags de {uanim}:**")
                st.bar_chart(utags["tag"].value_counts().head(15))
            with c2:
                st.markdown("**Por obra:**")
                st.bar_chart(utags.groupby("obra_id").size().rename(index=od))

            uconns = tag_connections(utags["tag"].tolist(), threshold=0.30)
            if uconns:
                st.markdown("**Conexoes nas tags deste participante (limiar 0.30):**")
                fm = utags["tag"].value_counts().to_dict()
                for c in uconns[:10]:
                    st.markdown(
                        f"<div class='conn-row'>"
                        f"<div style='display:flex;align-items:center;gap:9px;flex-wrap:wrap'>"
                        f"<span class='tag-badge'>{c['tag_a']}</span>"
                        f"<span style='color:var(--text-dim)'>({fm.get(c['tag_a'],0)}x)</span>"
                        f"<span style='color:var(--text-dim)'>&#8596;</span>"
                        f"<span class='tag-badge'>{c['tag_b']}</span>"
                        f"<span style='color:var(--text-dim)'>({fm.get(c['tag_b'],0)}x)</span>"
                        f"</div>"
                        f"<span style='color:var(--text-dim);font-size:.75rem'>"
                        f"{c['similaridade']:.3f} — {c['tipo']}</span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

            st.markdown(divider(), unsafe_allow_html=True)
            ft = utags.copy(); ft["Obra"] = ft["obra_id"].map(od)
            st.dataframe(
                ft[["tag","Obra","timestamp"]].rename(
                    columns={"tag":"Tag","timestamp":"Data/Hora"}
                ), use_container_width=True, hide_index=True,
            )

    with t3:
        st.markdown("#### Respostas do Questionario de Perfil")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Q1 — Familiaridade com Museus**")
            q1c = udf["q1"].value_counts()
            st.bar_chart(q1c)
            st.dataframe((q1c/q1c.sum()*100).round(1).reset_index().rename(columns={"q1":"Resposta","count":"%"}),
                         use_container_width=True, hide_index=True)
        with c2:
            st.markdown("**Q2 — Conhecimento Museologico**")
            q2c = udf["q2"].value_counts()
            st.bar_chart(q2c)
            st.dataframe((q2c/q2c.sum()*100).round(1).reset_index().rename(columns={"q2":"Resposta","count":"%"}),
                         use_container_width=True, hide_index=True)

        st.markdown(divider(), unsafe_allow_html=True)
        st.markdown("**Q3 — Respostas abertas: O que voce entende por tags?**")
        disp = udf.copy()
        disp["Palavras"] = disp["q3"].str.split().str.len()
        if "animal_name" in disp.columns:
            disp = disp.rename(columns={"animal_name": "Usuario Anonimo"})
        st.markdown(f"Comprimento medio: **{disp['Palavras'].mean():.0f} palavras** por participante")
        st.bar_chart(disp["Palavras"].value_counts().sort_index().rename("Respostas"))
        st.markdown(divider(), unsafe_allow_html=True)
        st.dataframe(
            disp[["Usuario Anonimo","q3","Palavras","timestamp"]]
            .sort_values("timestamp", ascending=False)
            .rename(columns={"q3":"Resposta","timestamp":"Data/Hora"}),
            use_container_width=True, hide_index=True,
        )

    with t4:
        if tdf.empty:
            st.info("Dados insuficientes.")
            return
        m = merged.copy()
        st.markdown("#### Cruzamentos: Perfil x Comportamento de Tagging")

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Familiaridade com Museus x Media de Tags**")
            avg_q1 = m.groupby("q1")["Total_Tags"].mean().sort_values(ascending=False)
            st.bar_chart(avg_q1)
            st.dataframe(avg_q1.round(2).reset_index().rename(
                columns={"q1":"Familiaridade","Total_Tags":"Media de Tags"}),
                use_container_width=True, hide_index=True)
        with c2:
            st.markdown("**Conhecimento Museologico x Tags Unicas**")
            avg_q2 = m.groupby("q2")["Tags_Unicas"].mean().sort_values(ascending=False)
            st.bar_chart(avg_q2)
            st.dataframe(avg_q2.round(2).reset_index().rename(
                columns={"q2":"Conhecimento","Tags_Unicas":"Media Tags Unicas"}),
                use_container_width=True, hide_index=True)

        st.markdown(divider(), unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Familiaridade x Riqueza Vocabular (TTR)**")
            st.bar_chart(m.groupby("q1")["TTR"].mean().sort_values(ascending=False))
        with c2:
            st.markdown("**Conhecimento Museologico x TTR**")
            st.bar_chart(m.groupby("q2")["TTR"].mean().sort_values(ascending=False))

        st.markdown(divider(), unsafe_allow_html=True)
        cross = m.groupby("q1").agg(
            Usuarios=("user_id","count"),
            Media_Tags=("Total_Tags","mean"),
            Media_Unicas=("Tags_Unicas","mean"),
            TTR_Medio=("TTR","mean"),
        ).round(2).reset_index()
        cross.columns = ["Familiaridade","Usuarios","Media Tags","Media Unicas","TTR Medio"]
        st.dataframe(cross, use_container_width=True, hide_index=True)

        st.markdown(insight(
            "<strong>Interpretacao:</strong> Compare se participantes mais familiarizados com museus "
            "produzem mais tags, maior diversidade vocabular (TTR) ou vocabulario mais especializado. "
            "TTR proximo de 1.0 indica alta originalidade; proximo de 0 indica repeticao de termos."
        ), unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════
# TAB 7 — OBRAS MANAGEMENT
# ═════════════════════════════════════════════════════════════════
def tab_obras():
    st.markdown("### Gestao de Obras")
    obras = load_obras()
    tdf   = all_tags()
    t1, t2 = st.tabs(["Listar Obras", "Adicionar Nova Obra"])

    with t1:
        if obras:
            for obra in obras:
                oid   = obra["id"]
                tc    = len(tdf[tdf["obra_id"] == oid]) if not tdf.empty else 0
                c1, c2, c3 = st.columns([1, 2, 1])
                with c1:
                    st.image(obra["imagem"], use_container_width=True)
                with c2:
                    st.markdown(f"**#{oid} — {obra.get('titulo','')}**")
                    st.markdown(f"*{obra.get('artista','')} — {obra.get('ano','')}*")
                    st.markdown(f"Tags registradas: **{tc}**")
                    if obra.get("descricao"):
                        st.caption(obra["descricao"])
                with c3:
                    if st.button("Remover", key=f"del_{oid}"):
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
            c1, c2 = st.columns(2)
            with c1:
                titulo  = st.text_input("Titulo da Obra")
                artista = st.text_input("Artista")
            with c2:
                ano    = st.text_input("Ano")
                imagem = st.text_input("URL da Imagem")
            descricao = st.text_area("Descricao (para audiodescricao)", height=100,
                                     placeholder="Descreva a obra para usuarios com deficiencia visual...")
            if st.form_submit_button("Adicionar Obra", use_container_width=True):
                if titulo and artista and ano and imagem:
                    nid = max([o["id"] for o in obras]) + 1 if obras else 1
                    obras.append({
                        "id": nid, "titulo": titulo, "artista": artista,
                        "ano": ano, "imagem": imagem, "descricao": descricao,
                    })
                    save_json_file(OBRAS_FILE, obras)
                    st.success("Obra adicionada com sucesso.")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("Preencha todos os campos obrigatorios.")


# ═════════════════════════════════════════════════════════════════
# TAB 8 — EXPORT
# ═════════════════════════════════════════════════════════════════
def tab_export():
    st.markdown("### Central de Exportacao")
    tdf = all_tags()
    udf = all_users()
    obs = load_obras()

    t1, t2 = st.tabs(["Exportacao Geral", "Por Participante"])

    with t1:
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("#### Tags")
            if not tdf.empty:
                st.download_button("Todas as Tags (CSV)",
                    tdf.to_csv(index=False).encode("utf-8"),
                    f"tags_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv",
                    use_container_width=True)
                freq = tdf["tag"].value_counts().reset_index()
                freq.columns = ["Tag","Frequencia"]
                freq["%"] = (freq["Frequencia"]/freq["Frequencia"].sum()*100).round(2)
                freq["Categoria"] = freq["Tag"].apply(categorize_tag)
                st.download_button("Frequencias com Categorias (CSV)",
                    freq.to_csv(index=False).encode("utf-8"),
                    f"freq_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv",
                    use_container_width=True)
        with c2:
            st.markdown("#### Usuarios")
            if not udf.empty:
                st.download_button("Usuarios (CSV)",
                    udf.to_csv(index=False).encode("utf-8"),
                    f"usuarios_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv",
                    use_container_width=True)
        with c3:
            st.markdown("#### Obras")
            if obs:
                st.download_button("Obras (CSV)",
                    pd.DataFrame(obs).to_csv(index=False).encode("utf-8"),
                    f"obras_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv",
                    use_container_width=True)

        st.markdown(divider(), unsafe_allow_html=True)
        st.markdown("#### Exportar Conexoes de Tags")
        if not tdf.empty:
            thr = st.slider("Limiar de similaridade:", 0.2, 0.9, 0.35, 0.05, key="exp_thr")
            if st.button("Calcular e Exportar Conexoes"):
                with st.spinner("Calculando..."):
                    conns = tag_connections(tdf["tag"].tolist(), threshold=thr)
                if conns:
                    cdf = pd.DataFrame(conns)
                    st.download_button("Baixar Conexoes (CSV)",
                        cdf.to_csv(index=False).encode("utf-8"),
                        f"conexoes_{datetime.now().strftime('%Y%m%d')}.csv","text/csv",
                        use_container_width=True)
                    st.success(f"{len(conns)} conexoes exportadas.")
                else:
                    st.info("Nenhuma conexao encontrada.")

        st.markdown(divider(), unsafe_allow_html=True)
        st.markdown("#### Exportar Co-ocorrencias")
        if not tdf.empty:
            if st.button("Calcular e Exportar Co-ocorrencias"):
                with st.spinner("Calculando..."):
                    cooc = tag_cooccurrence(tdf)
                if not cooc.empty:
                    st.download_button("Baixar Co-ocorrencias (CSV)",
                        cooc.to_csv(index=False).encode("utf-8"),
                        f"coocorrencias_{datetime.now().strftime('%Y%m%d')}.csv","text/csv",
                        use_container_width=True)
                    st.success(f"{len(cooc)} pares exportados.")
                else:
                    st.info("Sem co-ocorrencias.")

    with t2:
        if udf.empty:
            st.info("Nenhum participante cadastrado.")
            return
        uopts = [f"{r.get('animal_name', r['user_id'][:8])}" for _, r in udf.iterrows()]
        usel  = st.selectbox("Selecione um participante:", uopts, key="exp_u")
        uidx  = uopts.index(usel)
        uid   = udf.iloc[uidx]["user_id"]
        uanim = udf.iloc[uidx].get("animal_name", uid[:8])

        st.markdown(f"#### Dados de: **{uanim}**")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("##### Questionario")
            hq = html_quest(uid, uanim, udf)
            if hq:
                st.download_button("Respostas (HTML/PDF)", hq,
                    f"quest_{uid[:8]}.html", "text/html", use_container_width=True)
            ud = udf[udf["user_id"] == uid]
            if not ud.empty:
                st.download_button("Respostas (CSV)",
                    ud.to_csv(index=False).encode("utf-8"),
                    f"quest_{uid[:8]}.csv", "text/csv", use_container_width=True)
        with c2:
            st.markdown("##### Tags Criadas")
            ht = html_tags(uid, uanim, obs, tdf)
            if ht:
                st.download_button("Relatorio de Tags (HTML/PDF)", ht,
                    f"tags_{uid[:8]}.html", "text/html", use_container_width=True)
            ut = get_user_tags(uid)
            if not ut.empty:
                st.download_button("Tags (CSV)",
                    ut.to_csv(index=False).encode("utf-8"),
                    f"tags_{uid[:8]}.csv", "text/csv", use_container_width=True)


# ═════════════════════════════════════════════════════════════════
# MAIN
# ═════════════════════════════════════════════════════════════════
def main():
    load_css()
    inject_accessibility()

    try:
        check_admin()
    except Exception as e:
        st.error(f"Erro ao inicializar dados: {e}")

    defaults = [
        ("user_id",     gen_uid()),
        ("animal_name", generate_animal_name()),
        ("step",        "intro"),
        ("answers",     {}),
    ]
    for k, v in defaults:
        if k not in st.session_state:
            st.session_state[k] = v

    if st.session_state["step"] != "completed":
        show_header("Bem-vindo — complete o questionario para acessar")
        show_intro()
    else:
        animal = st.session_state.get("animal_name", "Visitante")
        show_header(f"Identificado como: {animal}")
        st.markdown("<div class='main-content'>", unsafe_allow_html=True)
        t1, t2 = st.tabs(["Explorar a Galeria", "Area Administrativa"])
        with t1:
            show_obras()
        with t2:
            show_admin()
        st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
