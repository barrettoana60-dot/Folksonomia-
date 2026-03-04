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

# ==================== CONFIGURAÇÃO ====================
st.set_page_config(
    page_title="Sistema Folksonomia Digital",
    layout="wide",
    initial_sidebar_state="collapsed",
    page_icon="📚"
)

DATA_DIR = "data"
OBRAS_FILE  = os.path.join(DATA_DIR, "obras.json")
TAGS_FILE   = os.path.join(DATA_DIR, "tags.json")
USERS_FILE  = os.path.join(DATA_DIR, "users.json")
ADMIN_FILE  = os.path.join(DATA_DIR, "admin.json")
ADMIN_USERNAME = "nugep"
ADMIN_PASSWORD = "nugep123"

ANIMAIS = [
    "Águia","Boto","Capivara","Doninha","Ema","Falcão","Gavião",
    "Harpia","Irara","Jaguar","Lontra","Mico","Onça","Paca",
    "Quati","Raposa","Tamanduá","Urubu","Veado","Zorrilho",
    "Arara","Bugio","Caititu","Jaguatirica","Lobo","Mutum",
    "Pirarucu","Tucano","Sucuri","Tatu"
]
ADJETIVOS = [
    "Azul","Bravo","Calmo","Dourado","Esperto","Feroz","Gracioso",
    "Intenso","Jovial","Lento","Mágico","Nobre","Ousado","Preciso",
    "Rápido","Sábio","Tímido","Único","Valente","Zeloso",
    "Curioso","Furtivo","Altivo","Sereno","Vibrante","Audaz",
    "Brilhante","Corajoso","Distinto","Elegante"
]

def generate_animal_name():
    random.seed()
    return f"{random.choice(ANIMAIS)} {random.choice(ADJETIVOS)}"

# ==================== CORE ====================
def ensure_data_dir():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

def load_json_file(filepath, default_data):
    ensure_data_dir()
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return default_data
    return default_data

def save_json_file(filepath, data):
    ensure_data_dir()
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar {filepath}: {e}")
        return False

# ==================== SIMILARIDADE ====================
def normalize_tag(tag):
    return tag.lower().strip()

def get_words(tag):
    return set(normalize_tag(tag).split())

def get_char_ngrams(text, n=3):
    text = normalize_tag(text)
    if len(text) < n:
        return set([text])
    return set(text[i:i+n] for i in range(len(text)-n+1))

def calculate_tag_similarity(tag1, tag2):
    t1, t2 = normalize_tag(tag1), normalize_tag(tag2)
    if t1 == t2:
        return 1.0
    if t1 in t2 or t2 in t1:
        shorter = min(len(t1), len(t2))
        longer  = max(len(t1), len(t2))
        return 0.55 + 0.45 * (shorter / longer)
    w1, w2 = get_words(tag1), get_words(tag2)
    if w1 and w2:
        inter = len(w1 & w2)
        union = len(w1 | w2)
        word_sim = inter / union if union > 0 else 0
        if word_sim >= 0.5:
            return word_sim
    if len(t1) >= 3 and len(t2) >= 3:
        ng1, ng2 = get_char_ngrams(t1), get_char_ngrams(t2)
        inter = len(ng1 & ng2)
        union = len(ng1 | ng2)
        ngram_sim = inter / union if union > 0 else 0
        if ngram_sim > 0:
            word_sim_raw = len(w1&w2)/len(w1|w2) if len(w1|w2)>0 else 0
            return 0.6*ngram_sim + 0.4*word_sim_raw
    return 0.0

def find_tag_connections(tags_list, threshold=0.35):
    unique_tags = list(set(normalize_tag(t) for t in tags_list))
    connections = []
    for i in range(len(unique_tags)):
        for j in range(i+1, len(unique_tags)):
            t1, t2 = unique_tags[i], unique_tags[j]
            score = calculate_tag_similarity(t1, t2)
            if score >= threshold:
                w1, w2 = get_words(t1), get_words(t2)
                shared = w1 & w2
                if t1 in t2 or t2 in t1:
                    tipo = "Contenção"
                elif shared:
                    tipo = f"Palavra comum: '{', '.join(shared)}'"
                else:
                    tipo = "Similaridade fonética"
                connections.append({"tag_a":t1,"tag_b":t2,"similaridade":round(score,3),"tipo":tipo})
    connections.sort(key=lambda x: x["similaridade"], reverse=True)
    return connections

def find_tag_clusters(tags_list, threshold=0.35):
    unique_tags = list(set(normalize_tag(t) for t in tags_list))
    connections = find_tag_connections(unique_tags, threshold)
    parent = {t: t for t in unique_tags}
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
    for conn in connections:
        union(conn["tag_a"], conn["tag_b"])
    clusters = defaultdict(list)
    for tag in unique_tags:
        clusters[find(tag)].append(tag)
    return [sorted(c) for c in clusters.values() if len(c) > 1]

# ==================== CSS ====================
def load_custom_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800&display=swap');
    * { margin:0; padding:0; box-sizing:border-box; font-family:'Poppins',sans-serif !important; }
    @keyframes gradient {
        0%   { background-position:0%   50%; }
        50%  { background-position:100% 50%; }
        100% { background-position:0%   50%; }
    }
    .stApp {
        background: linear-gradient(-45deg,#000000 0%,#001F3F 25%,#000000 50%,#001F3F 75%,#000000 100%);
        background-size:400% 400%; animation:gradient 15s ease infinite; color:#e0e0e0;
    }
    .top-navbar {
        position:fixed; top:0; left:0; right:0; z-index:9999;
        background:rgba(255,255,255,0.1); backdrop-filter:blur(20px) saturate(180%);
        border-bottom:1px solid rgba(255,255,255,0.2); padding:1.5rem 3rem;
        display:flex; justify-content:space-between; align-items:center;
        box-shadow:0 8px 32px rgba(0,0,0,0.1);
    }
    .navbar-logo {
        font-size:1.8rem; font-weight:800;
        background:linear-gradient(135deg,#a7e6ff 0%,#d1baff 100%);
        -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text; letter-spacing:-1px;
    }
    .main-content { margin-top:120px; padding:2rem 3rem; max-width:1600px; margin-left:auto; margin-right:auto; }
    .glass-card {
        background:rgba(255,255,255,0.15); backdrop-filter:blur(20px) saturate(180%);
        border:1px solid rgba(255,255,255,0.3); border-radius:24px; padding:2.5rem; margin:1.5rem 0;
        box-shadow:0 8px 32px rgba(0,0,0,0.1); transition:all 0.4s cubic-bezier(0.4,0,0.2,1);
        position:relative; overflow:hidden;
    }
    .glass-card::before {
        content:''; position:absolute; top:0; left:-100%; width:100%; height:100%;
        background:linear-gradient(90deg,transparent,rgba(255,255,255,0.3),transparent); transition:left 0.5s;
    }
    .glass-card:hover::before { left:100%; }
    .glass-card:hover { transform:translateY(-8px) scale(1.02); box-shadow:0 16px 48px rgba(0,0,0,0.2); border-color:rgba(255,255,255,0.5); }
    .obra-card {
        background:rgba(255,255,255,0.2); backdrop-filter:blur(15px) saturate(180%);
        border:1px solid rgba(255,255,255,0.3); border-radius:20px; overflow:hidden;
        transition:all 0.4s cubic-bezier(0.4,0,0.2,1); cursor:pointer; position:relative;
    }
    .obra-card::after {
        content:''; position:absolute; top:0; left:0; right:0; bottom:0;
        background:linear-gradient(135deg,rgba(0,0,0,0.3),rgba(0,31,63,0.3)); opacity:0; transition:opacity 0.4s;
    }
    .obra-card:hover::after { opacity:1; }
    .obra-card:hover { transform:translateY(-12px) scale(1.03); box-shadow:0 20px 60px rgba(0,31,63,0.4); border-color:rgba(255,255,255,0.6); }
    .obra-card img { width:100%; height:280px; object-fit:cover; transition:transform 0.6s cubic-bezier(0.4,0,0.2,1); }
    .obra-card:hover img { transform:scale(1.15) rotate(2deg); }
    .main-title { color:white; font-size:3.5rem; font-weight:800; text-align:center; margin:2rem 0 1rem 0; letter-spacing:-2px; text-shadow:0 4px 20px rgba(0,0,0,0.3); }
    .subtitle { color:rgba(255,255,255,0.95); font-size:1.3rem; text-align:center; margin-bottom:3rem; line-height:1.8; font-weight:300; }
    .tag-badge {
        display:inline-block; background:rgba(255,255,255,0.25); backdrop-filter:blur(10px);
        border:1px solid rgba(255,255,255,0.4); color:white; padding:0.5rem 1.1rem;
        border-radius:50px; margin:0.3rem; font-size:0.88rem; font-weight:600; transition:all 0.3s;
    }
    .tag-badge:hover { background:rgba(255,255,255,0.4); transform:translateY(-3px) scale(1.05); }
    .tag-green  { background:rgba(34,197,94,0.25)  !important; border-color:rgba(34,197,94,0.5)  !important; color:#dcfce7 !important; }
    .tag-amber  { background:rgba(245,158,11,0.25)  !important; border-color:rgba(245,158,11,0.5)  !important; color:#fef3c7 !important; }
    .tag-blue   { background:rgba(96,165,250,0.25)  !important; border-color:rgba(96,165,250,0.5)  !important; color:#dbeafe !important; }
    .tag-purple { background:rgba(168,85,247,0.25)  !important; border-color:rgba(168,85,247,0.5)  !important; color:#f3e8ff !important; }
    .animal-badge {
        display:inline-block; background:rgba(167,230,255,0.2); border:1px solid rgba(167,230,255,0.45);
        color:#a7e6ff; padding:0.35rem 1rem; border-radius:50px; font-size:0.85rem; font-weight:700;
    }
    .metric-card {
        background:rgba(255,255,255,0.18); backdrop-filter:blur(20px) saturate(180%);
        border:1px solid rgba(255,255,255,0.3); border-radius:20px; padding:1.8rem;
        text-align:center; color:white; box-shadow:0 8px 32px rgba(0,0,0,0.15);
        transition:all 0.4s; position:relative; overflow:hidden;
    }
    .metric-card:hover { transform:translateY(-8px) scale(1.05); box-shadow:0 16px 48px rgba(0,31,63,0.3); }
    .metric-value { font-size:2.8rem; font-weight:800; margin:0.7rem 0; text-shadow:0 4px 20px rgba(0,0,0,0.2); }
    .metric-label { font-size:0.82rem; text-transform:uppercase; letter-spacing:2px; font-weight:600; opacity:0.85; }
    .metric-sub { font-size:0.72rem; opacity:0.55; margin-top:0.3rem; }
    .sc { background:rgba(255,255,255,0.08); border:1px solid rgba(255,255,255,0.15); border-radius:16px; padding:1.5rem; margin:0.8rem 0; }
    .sc-blue   { border-left:4px solid #60a5fa; background:rgba(96,165,250,0.07); }
    .sc-green  { border-left:4px solid #34d399; background:rgba(52,211,153,0.07); }
    .sc-purple { border-left:4px solid #a78bfa; background:rgba(167,139,250,0.07); }
    .sc-amber  { border-left:4px solid #fbbf24; background:rgba(251,191,36,0.07); }
    .sc-red    { border-left:4px solid #f87171; background:rgba(248,113,113,0.07); }
    .insight { background:rgba(167,230,255,0.1); border:1px solid rgba(167,230,255,0.3); border-radius:14px; padding:1.1rem 1.5rem; margin:0.6rem 0; color:rgba(255,255,255,0.9); font-size:0.93rem; line-height:1.7; }
    .insight strong { color:#a7e6ff; }
    .conn-row {
        display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;
        background:rgba(255,255,255,0.06); border-radius:12px; padding:0.9rem 1.2rem; margin:0.3rem 0;
        border-left:3px solid; transition:background 0.2s;
    }
    .conn-row:hover { background:rgba(255,255,255,0.12); }
    .cr-high { border-left-color:#22c55e; }
    .cr-med  { border-left-color:#f59e0b; }
    .cr-low  { border-left-color:#60a5fa; }
    .cluster-wrap { background:rgba(255,255,255,0.05); border-radius:16px; padding:1.2rem 1.5rem; margin:0.5rem 0; border:1px solid rgba(255,255,255,0.1); }
    .cluster-title { font-size:0.78rem; text-transform:uppercase; letter-spacing:1.5px; color:rgba(167,139,250,0.8); margin-bottom:0.6rem; font-weight:700; }
    .cluster-pill { display:inline-flex; align-items:center; gap:5px; background:rgba(168,85,247,0.2); border:1px solid rgba(168,85,247,0.4); border-radius:50px; padding:0.35rem 0.9rem; margin:0.2rem; font-size:0.8rem; font-weight:600; color:#f3e8ff; }
    .pbar-outer { background:rgba(255,255,255,0.1); border-radius:50px; height:6px; margin:3px 0; overflow:hidden; }
    .pbar-inner { height:100%; border-radius:50px; transition:width 0.5s; }
    .divider-glow { height:1px; background:linear-gradient(90deg,transparent,rgba(255,255,255,0.25),transparent); margin:1.8rem 0; }
    .stButton button {
        background:rgba(255,255,255,0.25) !important; backdrop-filter:blur(15px) !important;
        color:white !important; border:1px solid rgba(255,255,255,0.4) !important;
        border-radius:50px !important; padding:1rem 2.5rem !important; font-weight:700 !important;
        font-size:1rem !important; transition:all 0.4s !important; box-shadow:0 8px 25px rgba(0,0,0,0.15) !important;
        text-transform:uppercase; letter-spacing:1px;
    }
    .stButton button:hover {
        background:rgba(255,255,255,0.4) !important; box-shadow:0 12px 40px rgba(0,31,63,0.4) !important;
        transform:translateY(-4px) scale(1.05) !important; border-color:rgba(255,255,255,0.6) !important;
    }
    .stTextInput input, .stTextArea textarea, .stSelectbox select {
        background:rgba(255,255,255,0.2) !important; backdrop-filter:blur(10px) !important;
        border:1px solid rgba(255,255,255,0.3) !important; color:white !important;
        border-radius:16px !important; padding:1rem !important; font-weight:500 !important;
    }
    .stTextInput input::placeholder, .stTextArea textarea::placeholder { color:rgba(255,255,255,0.6) !important; }
    .stTextInput input:focus, .stTextArea textarea:focus { border-color:rgba(255,255,255,0.6) !important; box-shadow:0 0 0 3px rgba(255,255,255,0.2) !important; }
    label { color:white !important; font-weight:700 !important; font-size:1rem !important; text-shadow:0 2px 10px rgba(0,0,0,0.2); }
    .stTabs [data-baseweb="tab-list"] { gap:0.7rem; background:rgba(255,255,255,0.1); backdrop-filter:blur(10px); padding:0.5rem; border-radius:16px; }
    .stTabs [data-baseweb="tab"] { background:rgba(255,255,255,0.15); border:1px solid rgba(255,255,255,0.2); border-radius:12px; color:white; padding:0.8rem 1.6rem; font-weight:700; transition:all 0.3s; }
    .stTabs [data-baseweb="tab"]:hover { background:rgba(255,255,255,0.25); transform:translateY(-2px); }
    .stTabs [aria-selected="true"] { background:rgba(255,255,255,0.35) !important; border-color:rgba(255,255,255,0.5) !important; }
    .stAlert { background:rgba(255,255,255,0.2) !important; backdrop-filter:blur(15px) !important; border-radius:16px !important; border-left:4px solid !important; color:white !important; }
    #MainMenu, footer, header { visibility:hidden; }
    .stDeployButton { display:none; }
    [data-testid="stSidebar"] { display:none; }
    h1,h2,h3,h4,h5,h6 { color:white; font-weight:700; text-shadow:0 2px 15px rgba(0,0,0,0.3); }
    .dataframe { background:rgba(255,255,255,0.15) !important; border:1px solid rgba(255,255,255,0.2) !important; border-radius:16px !important; color:white !important; }
    .dataframe th { background:rgba(255,255,255,0.25) !important; color:white !important; font-weight:700 !important; }
    .dataframe td { color:white !important; }
    div[data-testid="stTextInput"] > div { background:transparent !important; border:none !important; box-shadow:none !important; padding:0 !important; }
    div[data-testid="stTextInput"] { background:transparent !important; border:none !important; }
    div[data-testid="stTextInput"] input { border-radius:12px !important; background:rgba(255,255,255,0.15) !important; border:1px solid rgba(255,255,255,0.25) !important; padding:0.8rem 1rem !important; }
    @media (max-width:768px) { .main-title { font-size:2.5rem; } .main-content { margin-top:140px; padding:1rem; } }
    </style>
    """, unsafe_allow_html=True)

# ==================== HELPERS ====================
def mkmetric(label, value, sub="", color="#a7e6ff"):
    return f"""<div class='metric-card'>
        <div class='metric-label'>{label}</div>
        <div class='metric-value' style='color:{color};'>{value}</div>
        {f"<div class='metric-sub'>{sub}</div>" if sub else ""}
    </div>"""

def mkinsight(text):
    return f"<div class='insight'>{text}</div>"

def mkdivider():
    return "<div class='divider-glow'></div>"

def mkpbar(pct, color="#60a5fa"):
    w = min(100, max(0, pct*100))
    return f"<div class='pbar-outer'><div class='pbar-inner' style='width:{w:.1f}%;background:{color};'></div></div>"

# ==================== DADOS ====================
def check_and_init_admin():
    admins = load_json_file(ADMIN_FILE, [])
    if not admins:
        hashed = hashlib.sha256(ADMIN_PASSWORD.encode()).hexdigest()
        admins.append({"id":1,"username":ADMIN_USERNAME,"password":hashed})
        save_json_file(ADMIN_FILE, admins)

def generate_user_id():
    return base64.b64encode(os.urandom(12)).decode('ascii')

@st.cache_data(ttl=5, show_spinner=False)
def load_obras():
    default = [
        {"id":1,"titulo":"Guernica","artista":"Pablo Picasso","ano":"1937",
         "imagem":"https://upload.wikimedia.org/wikipedia/en/7/74/PicassoGuernica.jpg"},
        {"id":2,"titulo":"A Noite Estrelada","artista":"Vincent van Gogh","ano":"1889",
         "imagem":"https://upload.wikimedia.org/wikipedia/commons/thumb/e/ea/Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg/1200px-Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg"},
        {"id":3,"titulo":"Mona Lisa","artista":"Leonardo da Vinci","ano":"1503",
         "imagem":"https://upload.wikimedia.org/wikipedia/commons/thumb/e/ec/Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_retouched.jpg/800px-Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_retouched.jpg"}
    ]
    obras = load_json_file(OBRAS_FILE, default)
    if not obras:
        save_json_file(OBRAS_FILE, default)
        return default
    return obras

def save_user_answers(user_id, animal_name, answers):
    users = load_json_file(USERS_FILE, [])
    users.append({"user_id":user_id,"animal_name":animal_name,
                  "timestamp":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),**answers})
    return save_json_file(USERS_FILE, users)

def save_tag(user_id, obra_id, tag):
    tags = load_json_file(TAGS_FILE, [])
    tags.append({"id":len(tags)+1,"user_id":user_id,"obra_id":obra_id,
                 "tag":tag.lower().strip(),"timestamp":datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
    st.cache_data.clear()
    return save_json_file(TAGS_FILE, tags)

def get_user_tags(user_id):
    tags = load_json_file(TAGS_FILE, [])
    ut = [t for t in tags if t['user_id']==user_id]
    return pd.DataFrame(ut) if ut else pd.DataFrame()

def get_tags_for_obra_by_user(obra_id, user_id):
    tags = load_json_file(TAGS_FILE, [])
    filtered = [t for t in tags if t['obra_id']==obra_id and t['user_id']==user_id]
    if filtered:
        df = pd.DataFrame(filtered)
        counts = df['tag'].value_counts().reset_index()
        counts.columns = ["tag","count"]
        return counts
    return pd.DataFrame(columns=["tag","count"])

def check_admin_credentials(username, password):
    hashed = hashlib.sha256(password.encode()).hexdigest()
    return username==ADMIN_USERNAME and hashed==hashlib.sha256(ADMIN_PASSWORD.encode()).hexdigest()

def load_all_tags():
    tags = load_json_file(TAGS_FILE, [])
    return pd.DataFrame(tags) if tags else pd.DataFrame()

def load_all_users():
    users = load_json_file(USERS_FILE, [])
    return pd.DataFrame(users) if users else pd.DataFrame()

# ==================== EXPORTAÇÃO ====================
def gen_quest_html(user_id, animal_name, users_df):
    if users_df.empty: return None
    ud = users_df[users_df['user_id']==user_id]
    if ud.empty: return None
    ui = ud.iloc[0]
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Questionário</title>
<style>*{{margin:0;padding:0;box-sizing:border-box}}body{{font-family:sans-serif;background:linear-gradient(135deg,#000,#001F3F);padding:40px;color:white}}
.c{{max-width:900px;margin:0 auto;background:rgba(255,255,255,.15);padding:50px;border-radius:24px;border:1px solid rgba(255,255,255,.3)}}
h1{{text-align:center;margin-bottom:15px;font-size:2.5rem}}.hi{{text-align:center;margin-bottom:40px}}
.at{{background:rgba(167,230,255,.25);border:1px solid rgba(167,230,255,.5);color:#a7e6ff;padding:.3rem 1rem;border-radius:50px;font-weight:700;display:inline-block}}
.qb{{margin:25px 0;padding:20px;background:rgba(255,255,255,.1);border-left:4px solid rgba(255,255,255,.5);border-radius:12px}}
.q{{font-weight:700;margin-bottom:10px}}.a{{line-height:1.7;opacity:.95}}
.ft{{text-align:center;margin-top:40px;padding-top:20px;border-top:1px solid rgba(255,255,255,.2);opacity:.7;font-size:.9rem}}</style></head>
<body><div class="c"><h1>Respostas do Questionário</h1>
<div class="hi"><p>Usuário Anônimo: <span class="at">🐾 {animal_name}</span></p>
<p style="margin-top:6px;opacity:.7">Data: {ui.get('timestamp','N/A')}</p></div>
<div class="qb"><div class="q">1. Nível de familiaridade com museus</div><div class="a">{ui.get('q1','N/A')}</div></div>
<div class="qb"><div class="q">2. Conhecimento sobre documentação museológica</div><div class="a">{ui.get('q2','N/A')}</div></div>
<div class="qb"><div class="q">3. O que você entende por 'tags'?</div><div class="a">{ui.get('q3','N/A')}</div></div>
<div class="ft">Sistema Folksonomia Digital — Ctrl+P → Salvar como PDF</div></div></body></html>"""

def gen_tags_html(user_id, animal_name, obras, tags_df):
    ut = tags_df[tags_df['user_id']==user_id] if not tags_df.empty else pd.DataFrame()
    if ut.empty: return None
    od = {o['id']:o for o in obras}
    rows = "".join(
        f"<tr><td>{i+1}</td><td>{od.get(r['obra_id'],{}).get('titulo','ID:'+str(r['obra_id']))}</td>"
        f"<td><span style='background:rgba(255,255,255,.25);padding:3px 10px;border-radius:50px;'>{r['tag']}</span></td>"
        f"<td>{r['timestamp']}</td></tr>"
        for i,(_,r) in enumerate(ut.iterrows())
    )
    top = "".join(
        f"<tr><td>{i}</td><td>{t}</td><td>{c}</td></tr>"
        for i,(t,c) in enumerate(ut['tag'].value_counts().head(10).items(),1)
    )
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Tags</title>
<style>*{{margin:0;padding:0;box-sizing:border-box}}body{{font-family:sans-serif;background:linear-gradient(135deg,#000,#001F3F);padding:40px;color:white}}
.c{{max-width:1100px;margin:0 auto;background:rgba(255,255,255,.15);padding:50px;border-radius:24px;border:1px solid rgba(255,255,255,.3)}}
h1{{text-align:center;margin-bottom:15px;font-size:2.5rem}}.hi{{text-align:center;margin-bottom:30px}}
.at{{background:rgba(167,230,255,.25);border:1px solid rgba(167,230,255,.5);color:#a7e6ff;padding:.3rem 1rem;border-radius:50px;font-weight:700;display:inline-block}}
.stats{{display:grid;grid-template-columns:repeat(3,1fr);gap:15px;margin:25px 0}}
.sb{{background:rgba(255,255,255,.15);border:1px solid rgba(255,255,255,.3);padding:20px;border-radius:12px;text-align:center}}
.sv{{font-size:2.8rem;font-weight:800}}.sl{{font-size:.85rem;text-transform:uppercase;letter-spacing:1.5px;margin-top:8px;opacity:.85}}
table{{width:100%;border-collapse:collapse;margin:20px 0}}th,td{{padding:14px;text-align:left;border-bottom:1px solid rgba(255,255,255,.15)}}
th{{background:rgba(255,255,255,.2);font-weight:700;text-transform:uppercase;font-size:.85rem}}
tr:nth-child(even){{background:rgba(255,255,255,.04)}}
.ft{{text-align:center;margin-top:40px;padding-top:20px;border-top:1px solid rgba(255,255,255,.2);opacity:.7;font-size:.9rem}}</style></head>
<body><div class="c"><h1>Relatório de Tags</h1>
<div class="hi"><p>Usuário Anônimo: <span class="at">🐾 {animal_name}</span></p>
<p style="margin-top:6px;opacity:.7">Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}</p></div>
<div class="stats">
<div class="sb"><div class="sv">{len(ut)}</div><div class="sl">Total de Tags</div></div>
<div class="sb"><div class="sv">{ut['tag'].nunique()}</div><div class="sl">Tags Únicas</div></div>
<div class="sb"><div class="sv">{ut['obra_id'].nunique()}</div><div class="sl">Obras Etiquetadas</div></div></div>
<h2 style="margin:30px 0 15px;font-size:1.6rem">Todas as Tags</h2>
<table><thead><tr><th>#</th><th>Obra</th><th>Tag</th><th>Data/Hora</th></tr></thead><tbody>{rows}</tbody></table>
<h2 style="margin:30px 0 15px;font-size:1.6rem">Top 10 Tags</h2>
<table><thead><tr><th>Pos.</th><th>Tag</th><th>Freq.</th></tr></thead><tbody>{top}</tbody></table>
<div class="ft">Sistema Folksonomia Digital — Ctrl+P → Salvar como PDF</div></div></body></html>"""

# ==================== INTERFACE ====================
def show_header():
    st.markdown("<div class='top-navbar'><div class='navbar-logo'>Sistema Folksonomia Digital</div></div>",unsafe_allow_html=True)

def main():
    load_custom_css()
    try: check_and_init_admin()
    except Exception as e: st.error(f"Erro ao inicializar admin: {e}")
    if 'user_id'     not in st.session_state: st.session_state['user_id']     = generate_user_id()
    if 'animal_name' not in st.session_state: st.session_state['animal_name'] = generate_animal_name()
    if 'step'        not in st.session_state: st.session_state['step']        = 'intro'
    if 'answers'     not in st.session_state: st.session_state['answers']     = {}
    if st.session_state['step'] != 'completed':
        show_intro()
    else:
        show_header()
        st.markdown("<div class='main-content'>", unsafe_allow_html=True)
        main_tabs = st.tabs(["🖼️ Explorar Obras","🔐 Área Administrativa"])
        with main_tabs[0]: show_obras()
        with main_tabs[1]: show_admin()
        st.markdown("</div>", unsafe_allow_html=True)

def show_intro():
    st.markdown("<div class='main-content'>", unsafe_allow_html=True)
    st.markdown("<h1 class='main-title'>Sistema Folksonomia Digital</h1>",unsafe_allow_html=True)
    st.markdown("<p class='subtitle'>Sistema colaborativo de catalogação de obras de arte<br>Complete o questionário para acessar a plataforma</p>",unsafe_allow_html=True)
    st.markdown("<div class='glass-card'>",unsafe_allow_html=True)
    st.markdown("<h2 style='text-align:center;margin-bottom:2.5rem;font-size:1.8rem;'>Questionário de Acesso</h2>",unsafe_allow_html=True)
    with st.form("intro_form"):
        col1,col2 = st.columns(2)
        with col1:
            q1 = st.selectbox("1. Qual é o seu nível de familiaridade com museus?",
                              ["Nunca visito museus","Visito raramente","Visito ocasionalmente","Visito frequentemente"])
            q2 = st.selectbox("2. Você já ouviu falar sobre documentação museológica?",
                              ["Nunca ouvi falar","Já ouvi, mas não sei o que é","Tenho uma ideia básica","Conheço bem o tema"])
        with col2:
            q3 = st.text_area("3. O que você entende por 'tags' ou etiquetas digitais aplicadas a acervo?",
                              max_chars=500, height=200, placeholder="Descreva sua compreensão sobre o conceito...")
        _,col_btn,_ = st.columns([1,1,1])
        with col_btn:
            submit = st.form_submit_button("Acessar Plataforma", use_container_width=True)
        if submit:
            if not q3.strip():
                st.error("Por favor, responda todas as perguntas para continuar!")
            else:
                st.session_state['answers'] = {"q1":q1,"q2":q2,"q3":q3}
                save_user_answers(st.session_state['user_id'],st.session_state['animal_name'],st.session_state['answers'])
                st.session_state['step'] = 'completed'
                st.success("Questionário completo! Acesso liberado.")
                st.balloons()
                st.rerun()
    st.markdown("</div></div>",unsafe_allow_html=True)

def show_obras():
    st.markdown("<h1 class='main-title'>Galeria de Obras de Arte</h1>",unsafe_allow_html=True)
    st.markdown("<p class='subtitle'>Explore as obras e contribua com suas próprias tags descritivas</p>",unsafe_allow_html=True)
    obras = load_obras()
    if not obras:
        st.info("Nenhuma obra cadastrada no momento.")
        return
    st.markdown("<div class='glass-card'>",unsafe_allow_html=True)
    col1,col2 = st.columns([2,1])
    with col1: search_id = st.text_input("Filtrar por número da obra:","",placeholder="Ex: 1, 2, 3…")
    with col2: sort_order = st.selectbox("Ordenar por:",["Número (crescente)","Número (decrescente)"])
    st.markdown("</div>",unsafe_allow_html=True)
    filtered = obras
    if search_id.strip().isdigit():
        filtered = [o for o in obras if str(o['id'])==search_id.strip()]
    filtered = sorted(filtered, key=lambda x: x['id'], reverse=(sort_order=="Número (decrescente)"))
    st.markdown(f"<div style='text-align:center;color:white;margin:2rem 0;font-size:1.2rem;font-weight:600;'>Exibindo <strong style='font-size:1.5rem;'>{len(filtered)}</strong> obra(s)</div>",unsafe_allow_html=True)
    cols = st.columns(3)
    for i,obra in enumerate(filtered):
        with cols[i%3]:
            st.markdown(f"""<div class='obra-card'>
                <img src='{obra['imagem']}' alt='Obra {obra['id']}' />
                <div style='padding:1.5rem;'>
                    <h3 style='font-size:1.1rem;font-weight:700;margin-bottom:0.4rem;'>Obra #{obra['id']}</h3>
                    <p style='font-size:0.9rem;opacity:0.7;'>Adicione uma tag descritiva para esta imagem</p>
                </div></div>""",unsafe_allow_html=True)
            if st.button(f"🏷️ Adicionar Tag",key=f"btn_{obra['id']}",use_container_width=True):
                st.session_state['selected_obra'] = obra
                st.rerun()
            if 'selected_obra' in st.session_state and st.session_state['selected_obra']['id']==obra['id']:
                with st.form(f"tag_form_{obra['id']}"):
                    tag = st.text_input("Sua tag:",key=f"tag_{obra['id']}",placeholder="Ex: azul, triste, moderno…")
                    ca,cb = st.columns(2)
                    with ca: submitted = st.form_submit_button("✅ Enviar",use_container_width=True)
                    with cb: cancel    = st.form_submit_button("❌ Cancelar",use_container_width=True)
                    if submitted and tag:
                        save_tag(st.session_state['user_id'],obra['id'],tag)
                        st.success(f"Tag '{tag}' adicionada!")
                        del st.session_state['selected_obra']
                        st.rerun()
                    if cancel:
                        del st.session_state['selected_obra']
                        st.rerun()
            tags = get_tags_for_obra_by_user(obra['id'],st.session_state['user_id'])
            if not tags.empty:
                st.markdown("**Suas Tags:**")
                html_tags = "".join(f"<span class='tag-badge'>{r['tag']} ({r['count']})</span>" for _,r in tags.iterrows())
                st.markdown(html_tags,unsafe_allow_html=True)
            else:
                st.info("Você ainda não criou tags para esta obra")

def show_admin():
    if 'admin_logged_in' not in st.session_state:
        st.session_state['admin_logged_in'] = False
    if not st.session_state['admin_logged_in']:
        st.markdown("<h1 class='main-title'>Área Administrativa</h1>",unsafe_allow_html=True)
        st.markdown("<p class='subtitle'>Acesso restrito</p>",unsafe_allow_html=True)
        _,col2,_ = st.columns([1,1,1])
        with col2:
            st.markdown("<div class='glass-card'>",unsafe_allow_html=True)
            st.markdown("<h2 style='text-align:center;margin-bottom:2rem;'>Login Administrativo</h2>",unsafe_allow_html=True)
            with st.form("login"):
                username = st.text_input("Usuário:",placeholder="Digite seu usuário")
                password = st.text_input("Senha:",type="password",placeholder="Digite sua senha")
                submitted = st.form_submit_button("Entrar no Sistema",use_container_width=True)
                if submitted:
                    if check_admin_credentials(username,password):
                        st.session_state['admin_logged_in'] = True
                        st.session_state['admin_username']  = username
                        st.success("Login realizado com sucesso!")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("Credenciais inválidas. Acesso negado.")
            st.markdown("</div>",unsafe_allow_html=True)
    else:
        st.markdown(f"<h1 class='main-title'>Dashboard Administrativo</h1><p class='subtitle'>Bem-vindo, <strong>{st.session_state.get('admin_username','Admin')}</strong></p>",unsafe_allow_html=True)
        tabs = st.tabs([
            "📊 Visão Geral",
            "🏷️ Análise de Tags",
            "🔗 Conexões de Tags",
            "👥 Análise de Usuários",
            "📋 Questionário",
            "🖼️ Obras",
            "📤 Exportar"
        ])
        with tabs[0]: show_overview()
        with tabs[1]: show_tag_analysis()
        with tabs[2]: show_tag_connections()
        with tabs[3]: show_user_analysis()
        with tabs[4]: show_questionnaire_analysis()
        with tabs[5]: show_manage_obras()
        with tabs[6]: show_export_panel()
        _,col2,_ = st.columns([1,1,1])
        with col2:
            if st.button("🚪 Sair do Sistema",use_container_width=True):
                st.session_state['admin_logged_in'] = False
                st.rerun()

# =====================================================================
# ABA 1 — VISÃO GERAL
# =====================================================================
def show_overview():
    tags_df  = load_all_tags()
    users_df = load_all_users()
    obras    = load_obras()

    st.markdown("### 📊 Métricas Gerais do Sistema")
    c1,c2,c3,c4,c5 = st.columns(5)
    total   = len(tags_df) if not tags_df.empty else 0
    unicas  = tags_df['tag'].nunique() if not tags_df.empty else 0
    nusers  = len(users_df['user_id'].unique()) if not users_df.empty else 0
    nobs    = len(obras)
    obs_ct  = tags_df['obra_id'].nunique() if not tags_df.empty else 0

    for col,lbl,val,sub,clr in [
        (c1,"Total de Tags",    total,   "registros","#a7e6ff"),
        (c2,"Tags Únicas",      unicas,  f"{unicas/total:.0%} do total" if total else "—","#d1baff"),
        (c3,"Participantes",    nusers,  "usuários ativos","#6ee7b7"),
        (c4,"Obras Cadastradas",nobs,    f"{obs_ct} com tags","#fcd34d"),
        (c5,"Média Tags/Usuário",f"{total/nusers:.1f}" if nusers else "—","por participante","#f9a8d4"),
    ]:
        with col: st.markdown(mkmetric(lbl,val,sub,clr),unsafe_allow_html=True)

    st.markdown(mkdivider(),unsafe_allow_html=True)

    if not users_df.empty and not tags_df.empty:
        st.markdown("### 🐾 Participantes Anônimos")
        uct = tags_df.groupby('user_id').size().reset_index(name='tags')
        uuq = tags_df.groupby('user_id')['tag'].nunique().reset_index(name='unicas')
        m   = users_df.merge(uct,on='user_id',how='left').merge(uuq,on='user_id',how='left').fillna(0)
        for _,row in m.iterrows():
            animal = row.get('animal_name','?')
            ts     = row.get('timestamp','N/A')
            nt, nu = int(row['tags']), int(row['unicas'])
            pct    = nu/nt if nt>0 else 0
            bar    = mkpbar(pct,"#a7e6ff")
            st.markdown(f"""<div class='sc sc-blue' style='padding:0.9rem 1.3rem;margin:0.3rem 0;'>
                <div style='display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;'>
                    <div><span class='animal-badge'>🐾 {animal}</span>
                    <span style='color:rgba(255,255,255,0.5);font-size:0.78rem;margin-left:10px;'>Acesso: {ts}</span></div>
                    <div style='text-align:right;min-width:180px;'>
                        <span style='color:white;font-weight:700;'>{nt} tags</span>
                        <span style='color:rgba(255,255,255,0.45);font-size:0.8rem;'> ({nu} únicas)</span>
                        {bar}
                        <span style='color:rgba(255,255,255,0.4);font-size:0.72rem;'>riqueza: {pct:.0%}</span>
                    </div>
                </div></div>""",unsafe_allow_html=True)

    st.markdown(mkdivider(),unsafe_allow_html=True)

    if not tags_df.empty:
        od = {o['id']:o['titulo'] for o in obras}
        c1,c2 = st.columns(2)
        with c1:
            st.markdown("#### 🏆 Top 15 Tags Mais Usadas")
            top = tags_df['tag'].value_counts().head(15).reset_index()
            top.columns=['Tag','Qtd']
            top['%']=(top['Qtd']/top['Qtd'].sum()*100).round(1)
            st.dataframe(top,use_container_width=True,hide_index=True)
        with c2:
            st.markdown("#### 🖼️ Obras Mais Tagueadas")
            ot = tags_df.groupby('obra_id').size().reset_index(name='Tags')
            ot['Obra'] = ot['obra_id'].map(od)
            st.dataframe(ot[['Obra','Tags']].sort_values('Tags',ascending=False),use_container_width=True,hide_index=True)

# =====================================================================
# ABA 2 — ANÁLISE DE TAGS
# =====================================================================
def show_tag_analysis():
    tags_df = load_all_tags()
    obras   = load_obras()
    od      = {o['id']:o['titulo'] for o in obras}
    if tags_df.empty:
        st.info("Nenhuma tag disponível.")
        return

    st.markdown("### 🏷️ Análise Completa das Tags")

    tab_freq, tab_morph, tab_obra, tab_tempo, tab_cooc = st.tabs([
        "📈 Frequência & Vocabulário",
        "🔤 Morfologia das Tags",
        "🖼️ Análise por Obra",
        "🕒 Evolução Temporal",
        "🔁 Co-ocorrência"
    ])

    # ---------- FREQUÊNCIA ----------
    with tab_freq:
        freq = tags_df['tag'].value_counts().reset_index()
        freq.columns = ['Tag','Frequência']
        total_usos = freq['Frequência'].sum()
        freq['% do Total']  = (freq['Frequência']/total_usos*100).round(2)
        freq['% Acumulada'] = freq['% do Total'].cumsum().round(2)
        freq['Categoria']   = pd.cut(freq['Frequência'],
                                      bins=[0,1,2,5,10,99999],
                                      labels=['Hapax (1×)','Rara (2×)','Ocasional (3–5×)','Frequente (6–10×)','Muito Frequente (10+×)'])

        hapax   = (freq['Frequência']==1).sum()
        top1pct = freq.iloc[0]['% do Total'] if not freq.empty else 0
        lei80   = (freq['% Acumulada']<=80).sum()
        ttr     = len(freq)/total_usos if total_usos else 0

        c1,c2,c3,c4 = st.columns(4)
        with c1: st.markdown(mkmetric("Vocabulário Total",  len(freq),"tags distintas","#a7e6ff"),unsafe_allow_html=True)
        with c2: st.markdown(mkmetric("Hapax Legomena",     hapax,    f"{hapax/len(freq):.0%} do vocab.","#f9a8d4"),unsafe_allow_html=True)
        with c3: st.markdown(mkmetric("80% dos usos",       f"{lei80} tags","lei de Zipf","#6ee7b7"),unsafe_allow_html=True)
        with c4: st.markdown(mkmetric("Type-Token Ratio",   f"{ttr:.3f}","riqueza global","#fcd34d"),unsafe_allow_html=True)

        st.markdown(mkinsight(
            f"<strong>Distribuição de Zipf:</strong> As {lei80} tags mais frequentes cobrem 80% de todos os usos. "
            f"Há {hapax} hapax legomena ({hapax/len(freq):.0%} do vocabulário) — termos usados somente uma vez. "
            f"O TTR global de <strong>{ttr:.3f}</strong> indica {'alta' if ttr>0.5 else 'moderada' if ttr>0.25 else 'baixa'} diversidade lexical."
        ),unsafe_allow_html=True)

        st.markdown("#### Frequência — Top 25 Tags")
        st.bar_chart(tags_df['tag'].value_counts().head(25))

        st.markdown("#### Tabela Completa de Frequências")
        cat_opts = list(freq['Categoria'].cat.categories)
        cat_sel  = st.multiselect("Filtrar por categoria:",cat_opts,default=cat_opts,key="freq_cat")
        disp = freq[freq['Categoria'].isin(cat_sel)]
        st.dataframe(disp,use_container_width=True,hide_index=True)

        c1,c2 = st.columns(2)
        with c1:
            csv_freq = freq.to_csv(index=False).encode('utf-8')
            st.download_button("⬇️ Frequências (CSV)",csv_freq,f"frequencias_{datetime.now().strftime('%Y%m%d')}.csv","text/csv",use_container_width=True)
        with c2:
            st.markdown("**Distribuição por categoria:**")
            cat_dist = freq['Categoria'].value_counts().reset_index()
            cat_dist.columns=['Categoria','Qtd']
            st.dataframe(cat_dist,use_container_width=True,hide_index=True)

    # ---------- MORFOLOGIA ----------
    with tab_morph:
        tdf = tags_df.copy()
        tdf['n_chars']   = tdf['tag'].str.len()
        tdf['n_words']   = tdf['tag'].str.split().str.len()
        tdf['has_num']   = tdf['tag'].str.contains(r'\d')
        tdf['has_space'] = tdf['tag'].str.contains(' ')
        tdf['first_char']= tdf['tag'].str[0].str.lower()
        tdf['last_char'] = tdf['tag'].str[-1].str.lower()

        c1,c2,c3,c4 = st.columns(4)
        with c1: st.markdown(mkmetric("Média Caracteres",   f"{tdf['n_chars'].mean():.1f}","por tag","#a7e6ff"),unsafe_allow_html=True)
        with c2: st.markdown(mkmetric("Média Palavras",     f"{tdf['n_words'].mean():.2f}","por tag","#d1baff"),unsafe_allow_html=True)
        with c3: st.markdown(mkmetric("Tags Compostas",     f"{tdf['has_space'].sum()}",f"{tdf['has_space'].mean():.0%} do total","#6ee7b7"),unsafe_allow_html=True)
        with c4: st.markdown(mkmetric("Tags c/ Número",     f"{tdf['has_num'].sum()}",f"{tdf['has_num'].mean():.0%} do total","#fcd34d"),unsafe_allow_html=True)

        c1,c2 = st.columns(2)
        with c1:
            st.markdown("#### Distribuição por Nº de Caracteres")
            st.bar_chart(tdf['n_chars'].value_counts().sort_index())
        with c2:
            st.markdown("#### Distribuição por Nº de Palavras")
            st.bar_chart(tdf['n_words'].value_counts().sort_index())

        st.markdown("#### Resumo Morfológico")
        morph = pd.DataFrame({
            'Categoria': ['Palavra simples (1 palavra)','Expressão composta (2+ palavras)','Contém número','Contém espaço'],
            'Qtd':  [(tdf['n_words']==1).sum(),(tdf['n_words']>1).sum(),tdf['has_num'].sum(),tdf['has_space'].sum()]
        })
        morph['%'] = (morph['Qtd']/len(tdf)*100).round(1)
        st.dataframe(morph,use_container_width=True,hide_index=True)

        st.markdown("#### Estatísticas Detalhadas de Comprimento")
        stats_len = tdf['n_chars'].describe().reset_index()
        stats_len.columns=['Métrica','Valor']
        stats_len['Valor'] = stats_len['Valor'].round(2)
        st.dataframe(stats_len,use_container_width=True,hide_index=True)

        st.markdown(mkinsight(
            f"<strong>Padrão morfológico:</strong> {(tdf['n_words']==1).mean():.0%} das tags são palavras simples. "
            f"As tags compostas ({(tdf['n_words']>1).mean():.0%}) tendem a ser mais específicas e descritivas. "
            f"Comprimento médio de <strong>{tdf['n_chars'].mean():.1f} ± {tdf['n_chars'].std():.1f} caracteres</strong>."
        ),unsafe_allow_html=True)

    # ---------- POR OBRA ----------
    with tab_obra:
        st.markdown("#### Análise por Obra")
        obra_opts = ["Todas"] + [f"#{o['id']} — {o['titulo']}" for o in obras]
        obra_sel  = st.selectbox("Selecione uma obra:",obra_opts,key="obra_tag_sel")

        if obra_sel != "Todas":
            oid = int(obra_sel.split("—")[0].replace("#","").strip())
            df_o = tags_df[tags_df['obra_id']==oid]
        else:
            df_o = tags_df

        c1,c2,c3 = st.columns(3)
        riq = df_o['tag'].nunique()/len(df_o) if len(df_o)>0 else 0
        with c1: st.markdown(mkmetric("Tags Nesta Seleção", len(df_o),"total de usos","#a7e6ff"),unsafe_allow_html=True)
        with c2: st.markdown(mkmetric("Tags Únicas",        df_o['tag'].nunique(),"distintas","#6ee7b7"),unsafe_allow_html=True)
        with c3: st.markdown(mkmetric("Riqueza (TTR)",      f"{riq:.2%}","type-token ratio","#fcd34d"),unsafe_allow_html=True)

        st.markdown("#### Top 20 Tags Mais Usadas")
        st.bar_chart(df_o['tag'].value_counts().head(20))

        fo = df_o['tag'].value_counts().reset_index()
        fo.columns=['Tag','Qtd']
        fo['%']=(fo['Qtd']/fo['Qtd'].sum()*100).round(1)
        st.dataframe(fo,use_container_width=True,hide_index=True)

        if obra_sel == "Todas" and len(obras)>1:
            st.markdown("#### Comparativo entre Obras")
            obra_stats = []
            for o in obras:
                sub = tags_df[tags_df['obra_id']==o['id']]
                if sub.empty: continue
                obra_stats.append({
                    "Obra": o['titulo'],
                    "Total Tags": len(sub),
                    "Únicas": sub['tag'].nunique(),
                    "Riqueza (TTR)": round(sub['tag'].nunique()/len(sub),3),
                    "Tag Mais Comum": sub['tag'].value_counts().index[0],
                    "Usuários": sub['user_id'].nunique()
                })
            if obra_stats:
                cmp = pd.DataFrame(obra_stats)
                st.dataframe(cmp,use_container_width=True,hide_index=True)
                st.markdown("**Tags Únicas por Obra:**")
                st.bar_chart(cmp.set_index('Obra')['Únicas'])

    # ---------- TEMPORAL ----------
    with tab_tempo:
        st.markdown("#### Evolução Temporal das Tags")
        try:
            tdf2 = tags_df.copy()
            tdf2['ts']   = pd.to_datetime(tdf2['timestamp'])
            tdf2['date'] = tdf2['ts'].dt.date
            tdf2['hour'] = tdf2['ts'].dt.hour
            tdf2['dow']  = tdf2['ts'].dt.day_name()

            daily = tdf2.groupby('date').agg(
                total=('tag','count'), unicas=('tag','nunique'), usuarios=('user_id','nunique')
            ).reset_index()

            c1,c2 = st.columns(2)
            with c1:
                st.markdown("**Tags criadas por dia**")
                st.line_chart(daily.set_index('date')['total'])
            with c2:
                st.markdown("**Tags únicas por dia**")
                st.line_chart(daily.set_index('date')['unicas'])

            c1,c2 = st.columns(2)
            with c1:
                st.markdown("**Usuários ativos por dia**")
                st.bar_chart(daily.set_index('date')['usuarios'])
            with c2:
                st.markdown("**Distribuição por hora do dia**")
                st.bar_chart(tdf2['hour'].value_counts().sort_index())

            st.markdown("#### Tabela Diária Detalhada")
            st.dataframe(daily.rename(columns={'date':'Data','total':'Tags','unicas':'Únicas','usuarios':'Usuários'}),
                         use_container_width=True,hide_index=True)

            if len(daily)>1:
                st.markdown(mkinsight(
                    f"<strong>Tendência temporal:</strong> Pico de {daily['total'].max()} tags em {daily.loc[daily['total'].idxmax(),'date']}. "
                    f"Média de {daily['total'].mean():.1f} tags por dia ativo."
                ),unsafe_allow_html=True)
        except Exception as e:
            st.info(f"Dados insuficientes para análise temporal. ({e})")

    # ---------- CO-OCORRÊNCIA ----------
    with tab_cooc:
        st.markdown("#### Co-ocorrência de Tags")
        st.info("Tags que aparecem juntas para a mesma obra e usuário revelam padrões de associação semântica.")

        tags_by_u_o = tags_df.groupby(['obra_id','user_id'])['tag'].apply(list).reset_index()
        co_occ = defaultdict(int)
        for _,row in tags_by_u_o.iterrows():
            tl = list(set(row['tag']))
            for i in range(len(tl)):
                for j in range(i+1,len(tl)):
                    pair = tuple(sorted((tl[i],tl[j])))
                    co_occ[pair] += 1

        if co_occ:
            co_df = pd.DataFrame([{"Tag A":k[0],"Tag B":k[1],"Co-ocorrências":v} for k,v in co_occ.items()]) \
                      .sort_values("Co-ocorrências",ascending=False)

            c1,c2,c3 = st.columns(3)
            with c1: st.markdown(mkmetric("Pares Totais",      len(co_df),"","#a7e6ff"),unsafe_allow_html=True)
            with c2: st.markdown(mkmetric("Pares Freq. (≥2×)", (co_df['Co-ocorrências']>=2).sum(),"","#6ee7b7"),unsafe_allow_html=True)
            with c3: st.markdown(mkmetric("Co-oc. Máxima",     co_df['Co-ocorrências'].max(),"vezes juntas","#fcd34d"),unsafe_allow_html=True)

            thr_co = st.slider("Mínimo de co-ocorrências:",1,max(int(co_df['Co-ocorrências'].max()),2),1,key="cooc_thr")
            co_f   = co_df[co_df['Co-ocorrências']>=thr_co]
            st.markdown(f"Exibindo **{len(co_f)}** pares com ≥ {thr_co} co-ocorrência(s)")
            st.dataframe(co_f,use_container_width=True,hide_index=True)

            st.markdown("**Top 20 Pares — Gráfico:**")
            tp = co_f.head(20).copy()
            tp['Par'] = tp['Tag A']+" ↔ "+tp['Tag B']
            st.bar_chart(tp.set_index('Par')['Co-ocorrências'])

            csv_co = co_df.to_csv(index=False).encode('utf-8')
            st.download_button("⬇️ Co-ocorrências (CSV)",csv_co,
                               f"coocorrencias_{datetime.now().strftime('%Y%m%d')}.csv","text/csv")
        else:
            st.info("Não há co-ocorrências suficientes ainda.")

# =====================================================================
# ABA 3 — CONEXÕES DE TAGS
# =====================================================================
def show_tag_connections():
    tags_df = load_all_tags()
    obras   = load_obras()
    od      = {o['id']:o['titulo'] for o in obras}

    if tags_df.empty:
        st.warning("Nenhuma tag disponível.")
        return

    st.markdown("### 🔗 Conexões e Agrupamentos de Tags")
    st.markdown(mkinsight(
        "<strong>Como funciona o algoritmo:</strong> Três métricas combinadas — "
        "<strong>Contenção</strong> (ex: 'vaso' → 'vaso verde'), "
        "<strong>Jaccard de palavras</strong> (palavras em comum, ex: 'barco preto' ↔ 'barco de barro') e "
        "<strong>Jaccard de trigramas</strong> (fonética, ex: 'arte' ≈ 'artes'). "
        "Score: 0 = sem relação · 1 = idênticas."
    ),unsafe_allow_html=True)

    c1,c2,c3 = st.columns(3)
    with c1: threshold = st.slider("Limiar de similaridade:",0.20,0.90,0.35,0.05,key="conn_thr")
    with c2: obra_sel  = st.selectbox("Filtrar por obra:",["Todas"]+[f"#{o['id']} — {o['titulo']}" for o in obras],key="conn_obra")
    with c3: max_conn  = st.number_input("Máx. conexões:",10,300,60,10,key="conn_max")

    fdf = tags_df.copy()
    if obra_sel != "Todas":
        oid_sel = int(obra_sel.split("—")[0].replace("#","").strip())
        fdf = tags_df[tags_df['obra_id']==oid_sel]

    all_tags = fdf['tag'].tolist()
    if len(set(all_tags)) < 2:
        st.warning("Necessário ao menos 2 tags distintas.")
        return

    with st.spinner("Calculando conexões…"):
        connections = find_tag_connections(all_tags, threshold=threshold)
        clusters    = find_tag_clusters(all_tags, threshold=threshold)

    high_c = [c for c in connections if c['similaridade']>=0.7]
    mid_c  = [c for c in connections if 0.5<=c['similaridade']<0.7]
    low_c  = [c for c in connections if c['similaridade']<0.5]

    c1,c2,c3,c4 = st.columns(4)
    with c1: st.markdown(mkmetric("Total Conexões",   len(connections),f"limiar ≥ {threshold:.2f}","#a7e6ff"),unsafe_allow_html=True)
    with c2: st.markdown(mkmetric("Alta (≥0.7)",      len(high_c),"fortes","#6ee7b7"),unsafe_allow_html=True)
    with c3: st.markdown(mkmetric("Média (0.5–0.7)",  len(mid_c),"moderadas","#fcd34d"),unsafe_allow_html=True)
    with c4: st.markdown(mkmetric("Grupos Formados",  len(clusters),"clusters","#d1baff"),unsafe_allow_html=True)

    st.markdown(mkdivider(),unsafe_allow_html=True)

    tab_lista, tab_cluster, tab_explore = st.tabs(["📋 Lista de Conexões","🗂️ Grupos de Tags","🔍 Exploração Interativa"])

    # ---- LISTA
    with tab_lista:
        if not connections:
            st.info("Nenhuma conexão. Reduza o limiar.")
        else:
            tipos    = sorted(set(c['tipo'] for c in connections))
            tipo_sel = st.multiselect("Filtrar por tipo de conexão:",tipos,default=tipos,key="tipo_conn")
            cf       = [c for c in connections if c['tipo'] in tipo_sel][:max_conn]
            freq_map = tags_df['tag'].value_counts().to_dict()

            st.markdown(f"Exibindo **{len(cf)}** conexões")
            for c in cf:
                s   = c['similaridade']
                css = "cr-high" if s>=0.7 else ("cr-med" if s>=0.5 else "cr-low")
                bar = "█"*int(s*10)+"░"*(10-int(s*10))
                fa  = freq_map.get(c['tag_a'],0)
                fb  = freq_map.get(c['tag_b'],0)
                st.markdown(f"""<div class='conn-row {css}'>
                    <div style='display:flex;align-items:center;gap:10px;flex-wrap:wrap;'>
                        <span class='tag-badge'>{c['tag_a']}</span>
                        <span style='color:rgba(255,255,255,0.35);font-size:.75rem;'>({fa}×)</span>
                        <span style='color:rgba(255,255,255,0.4);'>↔</span>
                        <span class='tag-badge'>{c['tag_b']}</span>
                        <span style='color:rgba(255,255,255,0.35);font-size:.75rem;'>({fb}×)</span>
                    </div>
                    <div style='text-align:right;min-width:200px;'>
                        <span style='font-family:monospace;color:rgba(255,255,255,0.65);font-size:.8rem;'>{bar} {s:.3f}</span><br>
                        <span style='font-size:.72rem;color:rgba(255,255,255,0.38);'>{c['tipo']}</span>
                    </div></div>""",unsafe_allow_html=True)

            conn_df = pd.DataFrame(connections)
            st.download_button("⬇️ Conexões (CSV)",conn_df.to_csv(index=False).encode('utf-8'),
                               f"conexoes_{datetime.now().strftime('%Y%m%d')}.csv","text/csv")

    # ---- CLUSTERS
    with tab_cluster:
        if not clusters:
            st.info("Nenhum grupo. Reduza o limiar.")
        else:
            COLORS = ["#60a5fa","#34d399","#f9a8d4","#fcd34d","#a78bfa","#f87171","#67e8f9","#86efac"]
            freq_map = tags_df['tag'].value_counts().to_dict()
            clusters_sorted = sorted(clusters, key=len, reverse=True)
            st.markdown(f"**{len(clusters_sorted)} grupo(s) formado(s)**")

            for i,cluster in enumerate(clusters_sorted,1):
                color      = COLORS[(i-1)%len(COLORS)]
                total_uses = sum(freq_map.get(t,0) for t in cluster)
                tags_html  = "".join(
                    f"<span class='cluster-pill'>{t} <span style='opacity:.55;font-size:.72rem;'>({freq_map.get(t,0)}×)</span></span>"
                    for t in sorted(cluster,key=lambda x: freq_map.get(x,0),reverse=True)
                )
                st.markdown(f"""<div class='cluster-wrap' style='border-left:3px solid {color};'>
                    <div class='cluster-title'>Grupo {i} · {len(cluster)} tags · {total_uses} usos totais</div>
                    {tags_html}</div>""",unsafe_allow_html=True)

            st.markdown("#### Resumo dos Grupos")
            csumm = pd.DataFrame([{
                "Grupo":f"Grupo {i}","Qtd Tags":len(c),
                "Total Usos":sum(freq_map.get(t,0) for t in c),
                "Tags":  ", ".join(sorted(c,key=lambda x:freq_map.get(x,0),reverse=True)[:6])+("…" if len(c)>6 else "")
            } for i,c in enumerate(clusters_sorted,1)])
            st.dataframe(csumm,use_container_width=True,hide_index=True)
            st.download_button("⬇️ Grupos (CSV)",csumm.to_csv(index=False).encode('utf-8'),
                               f"clusters_{datetime.now().strftime('%Y%m%d')}.csv","text/csv")

    # ---- EXPLORAÇÃO INTERATIVA
    with tab_explore:
        all_unique = sorted(set(normalize_tag(t) for t in all_tags))

        st.markdown("#### 🎯 Comparar Duas Tags Específicas")
        c1,c2 = st.columns(2)
        with c1: ta = st.selectbox("Tag A:",all_unique,key="ex_a")
        with c2: tb = st.selectbox("Tag B:",all_unique,key="ex_b")

        if ta and tb and ta != tb:
            s    = calculate_tag_similarity(ta,tb)
            w1,w2= get_words(ta),get_words(tb)
            shared = w1&w2
            ng1,ng2= get_char_ngrams(ta),get_char_ngrams(tb)
            ns   = len(ng1&ng2)/len(ng1|ng2) if ng1|ng2 else 0
            ws   = len(w1&w2)/len(w1|w2) if w1|w2 else 0
            lv   = "🟢 Alta" if s>=0.7 else ("🟡 Média" if s>=0.5 else ("🔵 Baixa" if s>=threshold else "⚪ Abaixo do limiar"))
            st.markdown(f"""<div class='sc sc-purple' style='margin-top:1rem;'>
                <div style='text-align:center;margin-bottom:1rem;'>
                    <span class='tag-badge' style='font-size:1.05rem;'>{ta}</span>
                    <span style='color:rgba(255,255,255,0.5);margin:0 1rem;font-size:1.2rem;'>↔</span>
                    <span class='tag-badge' style='font-size:1.05rem;'>{tb}</span>
                </div>
                <div style='text-align:center;font-size:2.4rem;font-weight:800;color:#d1baff;'>{s:.3f}</div>
                <div style='text-align:center;margin:.4rem 0;font-size:1rem;'>{lv}</div>
                <div style='display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin-top:1.2rem;'>
                    <div style='background:rgba(255,255,255,.06);border-radius:10px;padding:1rem;'>
                        <div style='font-size:.75rem;opacity:.55;text-transform:uppercase;letter-spacing:1px;margin-bottom:.4rem;'>Score Palavras (Jaccard)</div>
                        <div style='font-size:1.4rem;font-weight:700;'>{ws:.3f}</div>
                        <div style='font-size:.8rem;opacity:.55;'>Palavras em comum: {", ".join(shared) if shared else "nenhuma"}</div>
                    </div>
                    <div style='background:rgba(255,255,255,.06);border-radius:10px;padding:1rem;'>
                        <div style='font-size:.75rem;opacity:.55;text-transform:uppercase;letter-spacing:1px;margin-bottom:.4rem;'>Score Trigramas</div>
                        <div style='font-size:1.4rem;font-weight:700;'>{ns:.3f}</div>
                        <div style='font-size:.8rem;opacity:.55;'>Trigramas comuns: {len(ng1&ng2)}/{len(ng1|ng2)}</div>
                    </div>
                </div></div>""",unsafe_allow_html=True)

        st.markdown(mkdivider(),unsafe_allow_html=True)
        st.markdown("#### 🔎 Tags Mais Similares a uma Tag Pivot")
        pivot   = st.selectbox("Tag pivot:",all_unique,key="pivot_sel")
        p_thr   = st.slider("Limiar:",0.1,0.9,0.3,0.05,key="p_thr")

        if pivot:
            freq_map = tags_df['tag'].value_counts().to_dict()
            sims = []
            for t in all_unique:
                if t != pivot:
                    sc = calculate_tag_similarity(pivot,t)
                    if sc >= p_thr:
                        sims.append({"Tag":t,"Similaridade":round(sc,3),"Frequência":freq_map.get(t,0)})
            sims.sort(key=lambda x: x['Similaridade'],reverse=True)
            if sims:
                st.markdown(f"**{len(sims)} tags similares** a `{pivot}` (limiar {p_thr:.2f}):")
                html_s = "".join(
                    f"<span class='tag-badge {'tag-green' if x['Similaridade']>=0.7 else 'tag-amber' if x['Similaridade']>=0.5 else 'tag-blue'}'>"
                    f"{x['Tag']} <span style='opacity:.55;font-size:.72rem;'>{x['Similaridade']:.2f}</span></span>"
                    for x in sims[:30]
                )
                st.markdown(html_s,unsafe_allow_html=True)
                st.dataframe(pd.DataFrame(sims),use_container_width=True,hide_index=True)
            else:
                st.info(f"Nenhuma tag similar a '{pivot}' com limiar {p_thr:.2f}.")

# =====================================================================
# ABA 4 — ANÁLISE DE USUÁRIOS
# =====================================================================
def show_user_analysis():
    tags_df  = load_all_tags()
    users_df = load_all_users()
    obras    = load_obras()
    od       = {o['id']:o['titulo'] for o in obras}
    if tags_df.empty or users_df.empty:
        st.info("Dados insuficientes.")
        return

    st.markdown("### 👥 Análise Comportamental por Usuário")

    uct    = tags_df.groupby('user_id').size().reset_index(name='Total Tags')
    uuq    = tags_df.groupby('user_id')['tag'].nunique().reset_index(name='Tags Únicas')
    uobras = tags_df.groupby('user_id')['obra_id'].nunique().reset_index(name='Obras Etiquetadas')
    ulen   = tags_df.groupby('user_id').apply(lambda x: x['tag'].str.len().mean()).reset_index(name='Comp. Médio')
    uwds   = tags_df.groupby('user_id').apply(lambda x: x['tag'].str.split().str.len().mean()).reset_index(name='Palavras/Tag')

    merged = users_df.merge(uct,on='user_id',how='left').merge(uuq,on='user_id',how='left') \
                     .merge(uobras,on='user_id',how='left').merge(ulen,on='user_id',how='left') \
                     .merge(uwds,on='user_id',how='left').fillna(0)
    merged['Riqueza (TTR)']  = (merged['Tags Únicas']/merged['Total Tags'].replace(0,np.nan)).round(3)
    merged['Usuário']        = merged.apply(lambda r: r.get('animal_name',r['user_id'][:8]),axis=1)
    merged['Comp. Médio']    = merged['Comp. Médio'].round(1)
    merged['Palavras/Tag']   = merged['Palavras/Tag'].round(2)

    c1,c2,c3,c4 = st.columns(4)
    with c1: st.markdown(mkmetric("Participantes",        len(merged),"usuários","#a7e6ff"),unsafe_allow_html=True)
    with c2: st.markdown(mkmetric("Média Tags/Usuário",   f"{merged['Total Tags'].mean():.1f}","","#6ee7b7"),unsafe_allow_html=True)
    top_user = merged.loc[merged['Total Tags'].idxmax(),'Usuário'] if not merged.empty else "—"
    with c3: st.markdown(mkmetric("Maior Contribuição",   int(merged['Total Tags'].max()),top_user[:15],"#fcd34d"),unsafe_allow_html=True)
    with c4: st.markdown(mkmetric("Riqueza Média",        f"{merged['Riqueza (TTR)'].mean():.2%}","vocabular","#d1baff"),unsafe_allow_html=True)

    st.markdown("#### Tabela Comparativa de Participantes")
    dcols = ['Usuário','Total Tags','Tags Únicas','Riqueza (TTR)','Obras Etiquetadas','Comp. Médio','Palavras/Tag']
    st.dataframe(merged[dcols].sort_values('Total Tags',ascending=False),use_container_width=True,hide_index=True)

    st.markdown(mkdivider(),unsafe_allow_html=True)
    st.markdown("#### 🔎 Drill-down por Usuário")

    uopts = [f"🐾 {row.get('animal_name',row['user_id'][:8])}" for _,row in users_df.iterrows()]
    usel  = st.selectbox("Selecione um participante:",uopts,key="user_drill")
    uidx  = uopts.index(usel)
    uid   = users_df.iloc[uidx]['user_id']
    uanim = users_df.iloc[uidx].get('animal_name',uid[:8])

    utags = tags_df[tags_df['user_id']==uid]
    if utags.empty:
        st.info("Este usuário ainda não criou tags.")
    else:
        c1,c2 = st.columns(2)
        with c1:
            st.markdown(f"**Top tags de {uanim}:**")
            st.bar_chart(utags['tag'].value_counts().head(15))
        with c2:
            st.markdown("**Distribuição por obra:**")
            st.bar_chart(utags.groupby('obra_id').size().rename(index=od))

        # Conexões pessoais
        st.markdown(f"**🔗 Conexões nas tags de {uanim} (limiar 0.30):**")
        uconns = find_tag_connections(utags['tag'].tolist(),threshold=0.30)
        if uconns:
            for c in uconns[:12]:
                css = "cr-high" if c['similaridade']>=0.7 else ("cr-med" if c['similaridade']>=0.5 else "cr-low")
                st.markdown(f"""<div class='conn-row {css}' style='margin:0.25rem 0;'>
                    <span class='tag-badge'>{c['tag_a']}</span>
                    <span style='color:rgba(255,255,255,0.35);margin:0 6px;'>↔</span>
                    <span class='tag-badge'>{c['tag_b']}</span>
                    <span style='color:rgba(255,255,255,0.38);font-size:.78rem;margin-left:auto;'>{c['similaridade']:.3f} · {c['tipo']}</span>
                </div>""",unsafe_allow_html=True)
        else:
            st.info("Nenhuma conexão encontrada.")

        st.markdown("**Todas as tags criadas:**")
        ft = utags.copy()
        ft['Obra'] = ft['obra_id'].map(od)
        st.dataframe(ft[['tag','Obra','timestamp']].rename(columns={'tag':'Tag','timestamp':'Data/Hora'}),
                     use_container_width=True,hide_index=True)

# =====================================================================
# ABA 5 — QUESTIONÁRIO
# =====================================================================
def show_questionnaire_analysis():
    users_df = load_all_users()
    tags_df  = load_all_tags()
    if users_df.empty:
        st.info("Nenhum usuário respondeu ainda.")
        return

    st.markdown("### 📋 Análise do Questionário de Perfil")

    c1,c2,c3 = st.columns(3)
    q1dom = users_df['q1'].value_counts().index[0]
    q2dom = users_df['q2'].value_counts().index[0]
    with c1: st.markdown(mkmetric("Respostas",len(users_df),"questionários","#a7e6ff"),unsafe_allow_html=True)
    with c2: st.markdown(mkmetric("Perfil Q1 Dominante",q1dom[:16]+"…" if len(q1dom)>16 else q1dom,"","#6ee7b7"),unsafe_allow_html=True)
    with c3: st.markdown(mkmetric("Perfil Q2 Dominante",q2dom[:16]+"…" if len(q2dom)>16 else q2dom,"","#fcd34d"),unsafe_allow_html=True)

    st.markdown(mkdivider(),unsafe_allow_html=True)

    t1,t2,t3,t4 = st.tabs(["Q1 – Familiaridade","Q2 – Conhecimento","Q3 – Respostas Abertas","📊 Cruzamentos"])

    with t1:
        st.markdown("#### Familiaridade com Museus")
        q1c = users_df['q1'].value_counts()
        st.bar_chart(q1c)
        df1 = (q1c/q1c.sum()*100).round(1).reset_index()
        df1.columns=['Resposta','%']
        st.dataframe(df1,use_container_width=True,hide_index=True)

    with t2:
        st.markdown("#### Conhecimento sobre Documentação Museológica")
        q2c = users_df['q2'].value_counts()
        st.bar_chart(q2c)
        df2 = (q2c/q2c.sum()*100).round(1).reset_index()
        df2.columns=['Resposta','%']
        st.dataframe(df2,use_container_width=True,hide_index=True)

    with t3:
        st.markdown("#### Respostas Abertas — Compreensão sobre Tags")
        disp = users_df.copy()
        if 'animal_name' in disp.columns:
            disp = disp.rename(columns={'animal_name':'Usuário Anônimo'})
        disp['Qtd Palavras Q3'] = disp['q3'].str.split().str.len()
        st.markdown(f"Comprimento médio das respostas: **{disp['Qtd Palavras Q3'].mean():.0f} palavras**")
        st.bar_chart(disp['Qtd Palavras Q3'].value_counts().sort_index())
        st.dataframe(
            disp[['Usuário Anônimo','q3','Qtd Palavras Q3','timestamp']]
            .sort_values('timestamp',ascending=False)
            .rename(columns={'q3':'Resposta','timestamp':'Data'}),
            use_container_width=True,hide_index=True
        )

    with t4:
        if tags_df.empty:
            st.info("Dados de tags insuficientes.")
            return
        uct  = tags_df.groupby('user_id').size().reset_index(name='Total_Tags')
        uuq  = tags_df.groupby('user_id')['tag'].nunique().reset_index(name='Tags_Unicas')
        ulen = tags_df.groupby('user_id').apply(lambda x: x['tag'].str.len().mean()).reset_index(name='Comp_Medio')
        m    = users_df.merge(uct,on='user_id',how='left').merge(uuq,on='user_id',how='left') \
                       .merge(ulen,on='user_id',how='left').fillna(0)
        m['TTR'] = (m['Tags_Unicas']/m['Total_Tags'].replace(0,np.nan)).fillna(0)

        c1,c2 = st.columns(2)
        with c1:
            st.markdown("**Q1: Familiaridade × Média de Tags**")
            st.bar_chart(m.groupby('q1')['Total_Tags'].mean().sort_values(ascending=False))
        with c2:
            st.markdown("**Q2: Conhecimento × Tags Únicas**")
            st.bar_chart(m.groupby('q2')['Tags_Unicas'].mean().sort_values(ascending=False))

        c1,c2 = st.columns(2)
        with c1:
            st.markdown("**Q1: Familiaridade × Riqueza Vocabular (TTR)**")
            st.bar_chart(m.groupby('q1')['TTR'].mean().sort_values(ascending=False))
        with c2:
            st.markdown("**Q1: Familiaridade × Comprimento Médio da Tag**")
            st.bar_chart(m.groupby('q1')['Comp_Medio'].mean().sort_values(ascending=False))

        st.markdown("#### Tabela Completa de Cruzamentos")
        tab_cross = m.groupby('q1').agg(
            Total_Usuarios=('user_id','count'),
            Media_Tags=('Total_Tags','mean'),
            Media_Unicas=('Tags_Unicas','mean'),
            Media_TTR=('TTR','mean'),
            Media_Comp=('Comp_Medio','mean')
        ).round(2).reset_index()
        tab_cross.columns = ['Familiaridade','Usuários','Média Tags','Média Únicas','Riqueza Média','Comp. Médio Tag']
        st.dataframe(tab_cross,use_container_width=True,hide_index=True)

        st.markdown(mkinsight(
            "<strong>Interpretação:</strong> Compare os gráficos acima para identificar se usuários mais familiarizados com museus "
            "produzem mais tags, tags mais diversas (TTR), ou tags mais longas e descritivas. "
            "A riqueza vocabular (TTR) indica a proporção de termos únicos em relação ao total de tags."
        ),unsafe_allow_html=True)

# =====================================================================
# ABA 6 — GESTÃO DE OBRAS
# =====================================================================
def show_manage_obras():
    st.markdown("### 🖼️ Gestão de Obras")
    obras = load_obras()
    t1,t2 = st.tabs(["Listar Obras","Adicionar Nova"])
    with t1:
        if obras:
            for obra in obras:
                c1,c2,c3 = st.columns([1,2,1])
                with c1: st.image(obra['imagem'],use_container_width=True)
                with c2:
                    st.markdown(f"**#{obra['id']} – {obra['titulo']}**")
                    st.markdown(f"*{obra['artista']} — {obra['ano']}*")
                with c3:
                    if st.button("🗑️ Remover",key=f"del_{obra['id']}"):
                        obras.remove(obra)
                        save_json_file(OBRAS_FILE,obras)
                        st.success("Obra removida!")
                        st.cache_data.clear()
                        st.rerun()
                st.divider()
        else:
            st.info("Nenhuma obra cadastrada")
    with t2:
        with st.form("add"):
            titulo  = st.text_input("Título da Obra")
            artista = st.text_input("Artista")
            ano     = st.text_input("Ano")
            imagem  = st.text_input("URL da Imagem")
            if st.form_submit_button("✅ Adicionar Obra"):
                if titulo and artista and ano and imagem:
                    nid = max([o['id'] for o in obras])+1 if obras else 1
                    obras.append({"id":nid,"titulo":titulo,"artista":artista,"ano":ano,"imagem":imagem})
                    save_json_file(OBRAS_FILE,obras)
                    st.success("Obra adicionada com sucesso!")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("Preencha todos os campos!")

# =====================================================================
# ABA 7 — EXPORTAR
# =====================================================================
def show_export_panel():
    st.markdown("### 📤 Central de Exportação")
    tags_df  = load_all_tags()
    users_df = load_all_users()
    obras    = load_obras()

    t1,t2 = st.tabs(["📦 Geral","👤 Por Usuário"])

    with t1:
        c1,c2,c3 = st.columns(3)
        with c1:
            st.markdown("#### 🏷️ Tags")
            if not tags_df.empty:
                st.download_button("⬇️ Tags Completo (CSV)",tags_df.to_csv(index=False).encode('utf-8'),
                                   f"tags_{datetime.now().strftime('%Y%m%d')}.csv","text/csv",use_container_width=True)
                freq=tags_df['tag'].value_counts().reset_index(); freq.columns=['Tag','Freq']
                freq['%']=(freq['Freq']/freq['Freq'].sum()*100).round(2)
                st.download_button("⬇️ Frequências (CSV)",freq.to_csv(index=False).encode('utf-8'),
                                   f"freq_{datetime.now().strftime('%Y%m%d')}.csv","text/csv",use_container_width=True)
        with c2:
            st.markdown("#### 👥 Usuários")
            if not users_df.empty:
                st.download_button("⬇️ Usuários (CSV)",users_df.to_csv(index=False).encode('utf-8'),
                                   f"usuarios_{datetime.now().strftime('%Y%m%d')}.csv","text/csv",use_container_width=True)
        with c3:
            st.markdown("#### 🖼️ Obras")
            if obras:
                st.download_button("⬇️ Obras (CSV)",pd.DataFrame(obras).to_csv(index=False).encode('utf-8'),
                                   f"obras_{datetime.now().strftime('%Y%m%d')}.csv","text/csv",use_container_width=True)

        st.markdown("#### 🔗 Exportar Conexões")
        if not tags_df.empty:
            tex = st.slider("Limiar:",0.2,0.9,0.35,0.05,key="tex")
            if st.button("Gerar conexões",key="gen_conn"):
                with st.spinner("Calculando…"):
                    conns = find_tag_connections(tags_df['tag'].tolist(),threshold=tex)
                if conns:
                    cdf = pd.DataFrame(conns)
                    st.download_button("⬇️ Conexões (CSV)",cdf.to_csv(index=False).encode('utf-8'),
                                       f"conexoes_{datetime.now().strftime('%Y%m%d')}.csv","text/csv",use_container_width=True)
                    st.success(f"{len(conns)} conexões exportadas.")

    with t2:
        if users_df.empty:
            st.info("Nenhum usuário cadastrado.")
            return
        uopts = [f"🐾 {row.get('animal_name',row['user_id'][:8])}" for _,row in users_df.iterrows()]
        usel  = st.selectbox("Selecione:",uopts,key="exp_usel")
        uidx  = uopts.index(usel)
        uid   = users_df.iloc[uidx]['user_id']
        uanim = users_df.iloc[uidx].get('animal_name',uid[:8])

        st.markdown(f"#### Dados de: **{uanim}**")
        c1,c2 = st.columns(2)
        with c1:
            st.markdown("##### 📝 Questionário")
            html = gen_quest_html(uid,uanim,users_df)
            if html:
                st.download_button("⬇️ Respostas (HTML/PDF)",html,f"quest_{uid[:8]}.html","text/html",use_container_width=True)
            ud = users_df[users_df['user_id']==uid]
            if not ud.empty:
                st.download_button("⬇️ Respostas (CSV)",ud.to_csv(index=False).encode('utf-8'),
                                   f"quest_{uid[:8]}.csv","text/csv",use_container_width=True)
        with c2:
            st.markdown("##### 🏷️ Tags")
            html = gen_tags_html(uid,uanim,obras,tags_df)
            if html:
                st.download_button("⬇️ Tags (HTML/PDF)",html,f"tags_{uid[:8]}.html","text/html",use_container_width=True)
            ut = get_user_tags(uid)
            if not ut.empty:
                st.download_button("⬇️ Tags (CSV)",ut.to_csv(index=False).encode('utf-8'),
                                   f"tags_{uid[:8]}.csv","text/csv",use_container_width=True)

if __name__ == "__main__":
    main()
