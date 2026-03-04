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
OBRAS_FILE = os.path.join(DATA_DIR, "obras.json")
TAGS_FILE = os.path.join(DATA_DIR, "tags.json")
USERS_FILE = os.path.join(DATA_DIR, "users.json")
ADMIN_FILE = os.path.join(DATA_DIR, "admin.json")
ADMIN_USERNAME = "nugep"
ADMIN_PASSWORD = "nugep123"

# ==================== NOMES DE ANIMAIS ANÔNIMOS ====================
ANIMAIS = [
    "Águia", "Boto", "Capivara", "Doninha", "Ema", "Falcão", "Gavião",
    "Harpia", "Irara", "Jaguar", "Lontra", "Mico", "Onça", "Paca",
    "Quati", "Raposa", "Tamanduá", "Urubu", "Veado", "Zorrilho",
    "Arara", "Bugio", "Caititu", "Jaguatirica", "Lobo", "Mutum",
    "Pirarucu", "Tucano", "Sucuri", "Tatu"
]
ADJETIVOS = [
    "Azul", "Bravo", "Calmo", "Dourado", "Esperto", "Feroz", "Gracioso",
    "Intenso", "Jovial", "Lento", "Mágico", "Nobre", "Ousado", "Preciso",
    "Rápido", "Sábio", "Tímido", "Único", "Valente", "Zeloso",
    "Curioso", "Furtivo", "Altivo", "Sereno", "Vibrante", "Audaz",
    "Brilhante", "Corajoso", "Distinto", "Elegante"
]

def generate_animal_name():
    random.seed()
    animal = random.choice(ANIMAIS)
    adj = random.choice(ADJETIVOS)
    return f"{animal} {adj}"

# ==================== FUNÇÕES CORE ====================
def ensure_data_dir():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

def load_json_file(filepath, default_data):
    ensure_data_dir()
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            st.error(f"Erro ao ler {filepath}. Usando dados padrão.")
            return default_data
        except Exception as e:
            st.error(f"Erro inesperado ao carregar {filepath}: {e}")
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

# ==================== SIMILARIDADE DE TAGS ====================
def normalize_tag(tag):
    """Normaliza a tag para comparação"""
    return tag.lower().strip()

def get_words(tag):
    """Retorna conjunto de palavras de uma tag"""
    return set(normalize_tag(tag).split())

def get_char_ngrams(text, n=3):
    """Retorna n-gramas de caracteres"""
    text = normalize_tag(text)
    if len(text) < n:
        return set([text])
    return set(text[i:i+n] for i in range(len(text) - n + 1))

def calculate_tag_similarity(tag1, tag2):
    """
    Calcula similaridade entre duas tags usando múltiplos métodos:
    - Contenção de substring (vaso → vaso verde)
    - Jaccard de palavras (barco preto ↔ barco de barro)
    - Jaccard de n-gramas de caracteres
    Retorna score entre 0 e 1.
    """
    t1 = normalize_tag(tag1)
    t2 = normalize_tag(tag2)

    if t1 == t2:
        return 1.0

    # Contenção de substring
    if t1 in t2 or t2 in t1:
        shorter = min(len(t1), len(t2))
        longer = max(len(t1), len(t2))
        return 0.55 + 0.45 * (shorter / longer)

    # Jaccard de palavras
    w1, w2 = get_words(tag1), get_words(tag2)
    if w1 and w2:
        inter = len(w1 & w2)
        union = len(w1 | w2)
        word_sim = inter / union if union > 0 else 0
        if word_sim >= 0.5:
            return word_sim

    # Jaccard de n-gramas (trigramas)
    if len(t1) >= 3 and len(t2) >= 3:
        ng1 = get_char_ngrams(t1)
        ng2 = get_char_ngrams(t2)
        inter = len(ng1 & ng2)
        union = len(ng1 | ng2)
        ngram_sim = inter / union if union > 0 else 0
        if ngram_sim > 0:
            # Combina com jaccard de palavras
            word_sim_raw = len(w1 & w2) / len(w1 | w2) if len(w1 | w2) > 0 else 0
            return 0.6 * ngram_sim + 0.4 * word_sim_raw

    return 0.0

def find_tag_connections(tags_list, threshold=0.35):
    """
    Encontra conexões entre tags similares.
    Retorna lista de (tag1, tag2, score, tipo_conexao).
    """
    unique_tags = list(set(normalize_tag(t) for t in tags_list))
    connections = []

    for i in range(len(unique_tags)):
        for j in range(i + 1, len(unique_tags)):
            t1, t2 = unique_tags[i], unique_tags[j]
            score = calculate_tag_similarity(t1, t2)
            if score >= threshold:
                # Determina tipo de conexão
                if t1 in t2 or t2 in t1:
                    tipo = "Contenção"
                else:
                    w1, w2 = get_words(t1), get_words(t2)
                    shared = w1 & w2
                    if shared:
                        tipo = f"Palavra comum: '{', '.join(shared)}'"
                    else:
                        tipo = "Similaridade fonética"
                connections.append({
                    "tag_a": t1,
                    "tag_b": t2,
                    "similaridade": round(score, 3),
                    "tipo": tipo
                })

    connections.sort(key=lambda x: x["similaridade"], reverse=True)
    return connections

def find_tag_clusters(tags_list, threshold=0.35):
    """
    Agrupa tags em clusters usando Union-Find (componentes conectados).
    """
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

    return [sorted(cluster) for cluster in clusters.values() if len(cluster) > 1]

# ==================== CSS ====================
def load_custom_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800&display=swap');

    * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Poppins', sans-serif !important; }

    @keyframes gradient {
        0%   { background-position: 0%   50%; }
        50%  { background-position: 100% 50%; }
        100% { background-position: 0%   50%; }
    }

    .stApp {
        background: linear-gradient(-45deg, #000000 0%, #001F3F 25%, #000000 50%, #001F3F 75%, #000000 100%);
        background-size: 400% 400%;
        animation: gradient 15s ease infinite;
        color: #e0e0e0;
    }

    .top-navbar {
        position: fixed; top: 0; left: 0; right: 0; z-index: 9999;
        background: rgba(255,255,255,0.1);
        backdrop-filter: blur(20px) saturate(180%);
        -webkit-backdrop-filter: blur(20px) saturate(180%);
        border-bottom: 1px solid rgba(255,255,255,0.2);
        padding: 1.5rem 3rem;
        display: flex; justify-content: space-between; align-items: center;
        box-shadow: 0 8px 32px rgba(0,0,0,0.1);
    }
    .navbar-logo {
        font-size: 1.8rem; font-weight: 800;
        background: linear-gradient(135deg, #a7e6ff 0%, #d1baff 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
        letter-spacing: -1px;
    }
    .main-content { margin-top: 120px; padding: 2rem 3rem; max-width: 1600px; margin-left: auto; margin-right: auto; }

    .glass-card {
        background: rgba(255,255,255,0.15); backdrop-filter: blur(20px) saturate(180%);
        -webkit-backdrop-filter: blur(20px) saturate(180%);
        border: 1px solid rgba(255,255,255,0.3); border-radius: 24px; padding: 2.5rem; margin: 1.5rem 0;
        box-shadow: 0 8px 32px rgba(0,0,0,0.1); transition: all 0.4s cubic-bezier(0.4,0,0.2,1);
        position: relative; overflow: hidden;
    }
    .glass-card::before {
        content: ''; position: absolute; top: 0; left: -100%;
        width: 100%; height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent);
        transition: left 0.5s;
    }
    .glass-card:hover::before { left: 100%; }
    .glass-card:hover { transform: translateY(-8px) scale(1.02); box-shadow: 0 16px 48px rgba(0,0,0,0.2); border-color: rgba(255,255,255,0.5); }

    .obra-card {
        background: rgba(255,255,255,0.2); backdrop-filter: blur(15px) saturate(180%);
        -webkit-backdrop-filter: blur(15px) saturate(180%);
        border: 1px solid rgba(255,255,255,0.3); border-radius: 20px; overflow: hidden;
        transition: all 0.4s cubic-bezier(0.4,0,0.2,1); cursor: pointer; position: relative;
    }
    .obra-card::after {
        content: ''; position: absolute; top: 0; left: 0; right: 0; bottom: 0;
        background: linear-gradient(135deg, rgba(0,0,0,0.3), rgba(0,31,63,0.3)); opacity: 0; transition: opacity 0.4s;
    }
    .obra-card:hover::after { opacity: 1; }
    .obra-card:hover { transform: translateY(-12px) scale(1.03); box-shadow: 0 20px 60px rgba(0,31,63,0.4); border-color: rgba(255,255,255,0.6); }
    .obra-card img { width: 100%; height: 280px; object-fit: cover; transition: transform 0.6s cubic-bezier(0.4,0,0.2,1); }
    .obra-card:hover img { transform: scale(1.15) rotate(2deg); }

    .main-title { color: white; font-size: 3.5rem; font-weight: 800; text-align: center; margin: 2rem 0 1rem 0; letter-spacing: -2px; text-shadow: 0 4px 20px rgba(0,0,0,0.3); }
    .subtitle { color: rgba(255,255,255,0.95); font-size: 1.3rem; text-align: center; margin-bottom: 3rem; line-height: 1.8; font-weight: 300; text-shadow: 0 2px 10px rgba(0,0,0,0.2); }

    .tag-badge {
        display: inline-block; background: rgba(255,255,255,0.25); backdrop-filter: blur(10px);
        border: 1px solid rgba(255,255,255,0.4); color: white; padding: 0.6rem 1.2rem;
        border-radius: 50px; margin: 0.4rem; font-size: 0.9rem; font-weight: 600;
        transition: all 0.3s cubic-bezier(0.4,0,0.2,1); box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    .tag-badge:hover { background: rgba(255,255,255,0.4); transform: translateY(-3px) scale(1.05); box-shadow: 0 8px 25px rgba(0,31,63,0.4); }

    .animal-badge {
        display: inline-block; background: rgba(167,230,255,0.25); backdrop-filter: blur(10px);
        border: 1px solid rgba(167,230,255,0.5); color: #a7e6ff; padding: 0.4rem 1rem;
        border-radius: 50px; font-size: 0.85rem; font-weight: 700;
    }

    .connection-card {
        background: rgba(255,255,255,0.12); border: 1px solid rgba(255,255,255,0.25);
        border-radius: 16px; padding: 1.2rem 1.5rem; margin: 0.5rem 0;
        transition: all 0.3s ease;
    }
    .connection-card:hover { background: rgba(255,255,255,0.2); transform: translateX(4px); }
    .conn-score-high  { border-left: 4px solid #22c55e; }
    .conn-score-med   { border-left: 4px solid #f59e0b; }
    .conn-score-low   { border-left: 4px solid #60a5fa; }

    .cluster-card {
        background: rgba(209,186,255,0.15); border: 1px solid rgba(209,186,255,0.35);
        border-radius: 16px; padding: 1.2rem 1.5rem; margin: 0.5rem 0;
    }

    .metric-card {
        background: rgba(255,255,255,0.2); backdrop-filter: blur(20px) saturate(180%);
        border: 1px solid rgba(255,255,255,0.3); border-radius: 20px; padding: 2.5rem;
        text-align: center; color: white; box-shadow: 0 8px 32px rgba(0,0,0,0.15);
        transition: all 0.4s cubic-bezier(0.4,0,0.2,1); position: relative; overflow: hidden;
    }
    .metric-card:hover { transform: translateY(-8px) scale(1.05); box-shadow: 0 16px 48px rgba(0,31,63,0.3); border-color: rgba(255,255,255,0.5); }
    .metric-value { font-size: 3.5rem; font-weight: 800; margin: 1rem 0; text-shadow: 0 4px 20px rgba(0,0,0,0.2); position: relative; z-index: 1; }
    .metric-label { font-size: 1rem; text-transform: uppercase; letter-spacing: 2px; font-weight: 600; opacity: 0.95; position: relative; z-index: 1; }

    .stButton button {
        background: rgba(255,255,255,0.25) !important; backdrop-filter: blur(15px) !important;
        color: white !important; border: 1px solid rgba(255,255,255,0.4) !important;
        border-radius: 50px !important; padding: 1rem 2.5rem !important; font-weight: 700 !important;
        font-size: 1rem !important; transition: all 0.4s cubic-bezier(0.4,0,0.2,1) !important;
        box-shadow: 0 8px 25px rgba(0,0,0,0.15) !important; text-transform: uppercase; letter-spacing: 1px;
    }
    .stButton button:hover {
        background: rgba(255,255,255,0.4) !important; box-shadow: 0 12px 40px rgba(0,31,63,0.4) !important;
        transform: translateY(-4px) scale(1.05) !important; border-color: rgba(255,255,255,0.6) !important;
    }

    .stTextInput input, .stTextArea textarea, .stSelectbox select {
        background: rgba(255,255,255,0.2) !important; backdrop-filter: blur(10px) !important;
        border: 1px solid rgba(255,255,255,0.3) !important; color: white !important;
        border-radius: 16px !important; padding: 1rem !important; transition: all 0.3s ease !important;
        font-weight: 500 !important;
    }
    .stTextInput input::placeholder, .stTextArea textarea::placeholder { color: rgba(255,255,255,0.6) !important; }
    .stTextInput input:focus, .stTextArea textarea:focus { border-color: rgba(255,255,255,0.6) !important; box-shadow: 0 0 0 3px rgba(255,255,255,0.2) !important; background: rgba(255,255,255,0.3) !important; }

    label { color: white !important; font-weight: 700 !important; font-size: 1rem !important; margin-bottom: 0.8rem !important; text-shadow: 0 2px 10px rgba(0,0,0,0.2); letter-spacing: 0.5px; }

    .stTabs [data-baseweb="tab-list"] { gap: 1rem; background: rgba(255,255,255,0.1); backdrop-filter: blur(10px); padding: 0.5rem; border-radius: 16px; }
    .stTabs [data-baseweb="tab"] { background: rgba(255,255,255,0.15); backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.2); border-radius: 12px; color: white; padding: 1rem 2rem; font-weight: 700; transition: all 0.3s cubic-bezier(0.4,0,0.2,1); }
    .stTabs [data-baseweb="tab"]:hover { background: rgba(255,255,255,0.25); transform: translateY(-2px); }
    .stTabs [aria-selected="true"] { background: rgba(255,255,255,0.35) !important; border-color: rgba(255,255,255,0.5) !important; box-shadow: 0 8px 25px rgba(0,31,63,0.3) !important; }

    .stAlert { background: rgba(255,255,255,0.2) !important; backdrop-filter: blur(15px) !important; border-radius: 16px !important; border-left: 4px solid !important; color: white !important; font-weight: 500 !important; }

    #MainMenu, footer, header { visibility: hidden; }
    .stDeployButton { display: none; }
    [data-testid="stSidebar"] { display: none; }

    h1, h2, h3, h4, h5, h6 { color: white; font-weight: 700; text-shadow: 0 2px 15px rgba(0,0,0,0.3); }

    .dataframe { background: rgba(255,255,255,0.15) !important; backdrop-filter: blur(10px) !important; border: 1px solid rgba(255,255,255,0.2) !important; border-radius: 16px !important; color: white !important; }
    .dataframe th { background: rgba(255,255,255,0.25) !important; color: white !important; font-weight: 700 !important; }
    .dataframe td { color: white !important; }

    div[data-testid="stTextInput"] > div { background: transparent !important; backdrop-filter: none !important; border: none !important; box-shadow: none !important; padding: 0 !important; }
    div[data-testid="stTextInput"] { background: transparent !important; border: none !important; box-shadow: none !important; }
    div[data-testid="stTextInput"] input { border-radius: 12px !important; background: rgba(255,255,255,0.15) !important; border: 1px solid rgba(255,255,255,0.25) !important; padding: 0.8rem 1rem !important; color: white !important; }

    @media (max-width: 768px) { .main-title { font-size: 2.5rem; } .main-content { margin-top: 140px; padding: 1rem; } .top-navbar { padding: 1rem 1.5rem; } }
    </style>
    """, unsafe_allow_html=True)

# ==================== FUNÇÕES DE DADOS ====================
def check_and_init_admin():
    admins = load_json_file(ADMIN_FILE, [])
    if not admins:
        hashed = hashlib.sha256(ADMIN_PASSWORD.encode()).hexdigest()
        admins.append({"id": 1, "username": ADMIN_USERNAME, "password": hashed})
        save_json_file(ADMIN_FILE, admins)

def generate_user_id():
    return base64.b64encode(os.urandom(12)).decode('ascii')

@st.cache_data(ttl=5, show_spinner=False)
def load_obras():
    default = [
        {"id": 1, "titulo": "Guernica", "artista": "Pablo Picasso", "ano": "1937",
         "imagem": "https://upload.wikimedia.org/wikipedia/en/7/74/PicassoGuernica.jpg"},
        {"id": 2, "titulo": "A Noite Estrelada", "artista": "Vincent van Gogh", "ano": "1889",
         "imagem": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ea/Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg/1200px-Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg"},
        {"id": 3, "titulo": "Mona Lisa", "artista": "Leonardo da Vinci", "ano": "1503",
         "imagem": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ec/Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_retouched.jpg/800px-Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_retouched.jpg"}
    ]
    obras = load_json_file(OBRAS_FILE, default)
    if not obras:
        save_json_file(OBRAS_FILE, default)
        return default
    return obras

def save_user_answers(user_id, animal_name, answers):
    users = load_json_file(USERS_FILE, [])
    users.append({
        "user_id": user_id,
        "animal_name": animal_name,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        **answers
    })
    return save_json_file(USERS_FILE, users)

def save_tag(user_id, obra_id, tag):
    tags = load_json_file(TAGS_FILE, [])
    tags.append({
        "id": len(tags) + 1,
        "user_id": user_id,
        "obra_id": obra_id,
        "tag": tag.lower().strip(),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    st.cache_data.clear()
    return save_json_file(TAGS_FILE, tags)

def get_user_tags(user_id):
    tags = load_json_file(TAGS_FILE, [])
    user_tags = [t for t in tags if t['user_id'] == user_id]
    return pd.DataFrame(user_tags) if user_tags else pd.DataFrame()

def get_tags_for_obra_by_user(obra_id, user_id):
    tags = load_json_file(TAGS_FILE, [])
    filtered = [t for t in tags if t['obra_id'] == obra_id and t['user_id'] == user_id]
    if filtered:
        df = pd.DataFrame(filtered)
        counts = df['tag'].value_counts().reset_index()
        counts.columns = ["tag", "count"]
        return counts
    return pd.DataFrame(columns=["tag", "count"])

def check_admin_credentials(username, password):
    hashed = hashlib.sha256(password.encode()).hexdigest()
    return username == ADMIN_USERNAME and hashed == hashlib.sha256(ADMIN_PASSWORD.encode()).hexdigest()

def load_all_tags():
    tags = load_json_file(TAGS_FILE, [])
    return pd.DataFrame(tags) if tags else pd.DataFrame()

def load_all_users():
    users = load_json_file(USERS_FILE, [])
    return pd.DataFrame(users) if users else pd.DataFrame()

def get_animal_name_by_id(user_id):
    users = load_json_file(USERS_FILE, [])
    for u in users:
        if u.get('user_id') == user_id:
            return u.get('animal_name', f"Usuário {user_id[:6]}")
    return f"Usuário {user_id[:6]}"

# ==================== EXPORTAÇÃO ====================
def generate_user_questionnaire_report(user_id, animal_name):
    users_df = load_all_users()
    if users_df.empty:
        return None
    user_data = users_df[users_df['user_id'] == user_id]
    if user_data.empty:
        return None
    user_info = user_data.iloc[0]
    html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Respostas do Questionário</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family: 'Poppins', sans-serif; background: linear-gradient(135deg,#000000 0%,#001F3F 100%); padding:40px; color:white; }}
.container {{ max-width:900px; margin:0 auto; background:rgba(255,255,255,0.15); padding:50px; border-radius:24px; border:1px solid rgba(255,255,255,0.3); }}
h1 {{ text-align:center; margin-bottom:15px; font-size:2.5rem; }}
.header-info {{ text-align:center; margin-bottom:40px; font-size:1rem; opacity:0.9; }}
.animal-tag {{ display:inline-block; background:rgba(167,230,255,0.25); border:1px solid rgba(167,230,255,0.5); color:#a7e6ff; padding:0.3rem 1rem; border-radius:50px; font-weight:700; }}
.question-block {{ margin:30px 0; padding:25px; background:rgba(255,255,255,0.1); border-left:4px solid rgba(255,255,255,0.5); border-radius:16px; }}
.question {{ font-weight:700; font-size:1.1rem; margin-bottom:12px; }}
.answer {{ font-size:1rem; line-height:1.7; padding:10px 0; opacity:0.95; }}
.footer {{ text-align:center; margin-top:50px; padding-top:25px; border-top:2px solid rgba(255,255,255,0.2); opacity:0.8; font-size:0.9rem; }}
</style></head>
<body><div class="container">
<h1>Respostas do Questionário</h1>
<div class="header-info">
<p><strong>Usuário Anônimo:</strong> <span class="animal-tag">🐾 {animal_name}</span></p>
<p style="margin-top:8px"><strong>Data:</strong> {user_info.get('timestamp','N/A')}</p>
</div>
<div class="question-block"><div class="question">1. Qual é o seu nível de familiaridade com museus?</div><div class="answer">{user_info.get('q1','N/A')}</div></div>
<div class="question-block"><div class="question">2. Você já ouviu falar sobre documentação museológica?</div><div class="answer">{user_info.get('q2','N/A')}</div></div>
<div class="question-block"><div class="question">3. O que você entende por 'tags' ou etiquetas digitais aplicadas a acervo?</div><div class="answer">{user_info.get('q3','N/A')}</div></div>
<div class="footer"><p>Sistema Folksonomia Digital</p><p style="margin-top:10px">Para salvar como PDF: Ctrl+P → "Salvar como PDF"</p></div>
</div></body></html>"""
    return html

def generate_user_tags_report(user_id, animal_name, obras):
    user_tags_df = get_user_tags(user_id)
    if user_tags_df.empty:
        return None
    obras_dict = {o['id']: o for o in obras}
    html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Relatório de Tags</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:'Poppins',sans-serif; background:linear-gradient(135deg,#000000 0%,#001F3F 100%); padding:40px; color:white; }}
.container {{ max-width:1200px; margin:0 auto; background:rgba(255,255,255,0.15); padding:50px; border-radius:24px; border:1px solid rgba(255,255,255,0.3); }}
h1 {{ text-align:center; margin-bottom:15px; font-size:2.5rem; }}
.header-info {{ text-align:center; margin-bottom:40px; font-size:1rem; opacity:0.9; }}
.animal-tag {{ display:inline-block; background:rgba(167,230,255,0.25); border:1px solid rgba(167,230,255,0.5); color:#a7e6ff; padding:0.3rem 1rem; border-radius:50px; font-weight:700; }}
.stats {{ display:grid; grid-template-columns:repeat(3,1fr); gap:20px; margin:30px 0; }}
.stat-box {{ background:rgba(255,255,255,0.15); border:1px solid rgba(255,255,255,0.3); padding:25px; border-radius:16px; text-align:center; }}
.stat-value {{ font-size:3rem; font-weight:800; }}
.stat-label {{ font-size:0.95rem; text-transform:uppercase; letter-spacing:1.5px; margin-top:10px; opacity:0.9; }}
table {{ width:100%; border-collapse:collapse; margin:30px 0; }}
th,td {{ padding:18px; text-align:left; border-bottom:1px solid rgba(255,255,255,0.2); }}
th {{ background:rgba(255,255,255,0.2); font-weight:700; text-transform:uppercase; font-size:0.9rem; }}
tr:nth-child(even) {{ background:rgba(255,255,255,0.05); }}
.tag-hl {{ background:rgba(255,255,255,0.25); padding:6px 14px; border-radius:50px; border:1px solid rgba(255,255,255,0.4); font-weight:600; }}
.footer {{ text-align:center; margin-top:50px; padding-top:25px; border-top:2px solid rgba(255,255,255,0.2); opacity:0.8; font-size:0.9rem; }}
</style></head>
<body><div class="container">
<h1>Relatório de Tags Criadas</h1>
<div class="header-info">
<p><strong>Usuário Anônimo:</strong> <span class="animal-tag">🐾 {animal_name}</span></p>
<p style="margin-top:8px"><strong>Gerado em:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
</div>
<div class="stats">
<div class="stat-box"><div class="stat-value">{len(user_tags_df)}</div><div class="stat-label">Total de Tags</div></div>
<div class="stat-box"><div class="stat-value">{len(user_tags_df['tag'].unique())}</div><div class="stat-label">Tags Únicas</div></div>
<div class="stat-box"><div class="stat-value">{len(user_tags_df['obra_id'].unique())}</div><div class="stat-label">Obras Etiquetadas</div></div>
</div>
<h2 style="margin-top:40px;margin-bottom:20px;font-size:1.8rem">Tags Detalhadas</h2>
<table><thead><tr><th>#</th><th>Obra (ID)</th><th>Tag Criada</th><th>Data/Hora</th></tr></thead><tbody>"""
    for idx, row in user_tags_df.iterrows():
        obra = obras_dict.get(row['obra_id'], {})
        html += f"<tr><td>{idx+1}</td><td>{obra.get('titulo','ID:'+str(row['obra_id']))}</td><td><span class='tag-hl'>{row['tag']}</span></td><td>{row['timestamp']}</td></tr>"
    top_tags = user_tags_df['tag'].value_counts().head(10)
    html += """</tbody></table>
<h2 style="margin-top:40px;margin-bottom:20px;font-size:1.8rem">Tags Mais Utilizadas</h2>
<table><thead><tr><th>Posição</th><th>Tag</th><th>Frequência</th></tr></thead><tbody>"""
    for idx, (tag, count) in enumerate(top_tags.items(), 1):
        html += f"<tr><td>{idx}</td><td><span class='tag-hl'>{tag}</span></td><td>{count}</td></tr>"
    html += """</tbody></table>
<div class="footer"><p>Sistema Folksonomia Digital</p><p style="margin-top:10px">Para salvar como PDF: Ctrl+P → "Salvar como PDF"</p></div>
</div></body></html>"""
    return html

# ==================== INTERFACE ====================
def show_header():
    st.markdown("""
    <div class='top-navbar'>
        <div class='navbar-logo'>Sistema Folksonomia Digital</div>
    </div>
    """, unsafe_allow_html=True)

def main():
    load_custom_css()
    try:
        check_and_init_admin()
    except Exception as e:
        st.error(f"Erro ao inicializar admin: {e}")

    if 'user_id' not in st.session_state:
        st.session_state['user_id'] = generate_user_id()
    if 'animal_name' not in st.session_state:
        st.session_state['animal_name'] = generate_animal_name()
    if 'step' not in st.session_state:
        st.session_state['step'] = 'intro'
    if 'answers' not in st.session_state:
        st.session_state['answers'] = {}

    if st.session_state['step'] != 'completed':
        show_intro()
    else:
        show_header()
        st.markdown("<div class='main-content'>", unsafe_allow_html=True)
        main_tabs = st.tabs(["🖼️ Explorar Obras", "🔐 Área Administrativa"])
        with main_tabs[0]:
            show_obras()
        with main_tabs[1]:
            show_admin()
        st.markdown("</div>", unsafe_allow_html=True)

def show_intro():
    st.markdown("<div class='main-content'>", unsafe_allow_html=True)
    st.markdown("<h1 class='main-title'>Sistema Folksonomia Digital</h1>", unsafe_allow_html=True)
    st.markdown("<p class='subtitle'>Sistema colaborativo de catalogação de obras de arte<br>Complete o questionário para acessar a plataforma</p>", unsafe_allow_html=True)

    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.markdown("<h2 style='text-align:center;margin-bottom:2.5rem;font-size:1.8rem;'>Questionário de Acesso</h2>", unsafe_allow_html=True)

    with st.form("intro_form"):
        col1, col2 = st.columns([1, 1])
        with col1:
            q1 = st.selectbox("1. Qual é o seu nível de familiaridade com museus?",
                              ["Nunca visito museus", "Visito raramente", "Visito ocasionalmente", "Visito frequentemente"])
            q2 = st.selectbox("2. Você já ouviu falar sobre documentação museológica?",
                              ["Nunca ouvi falar", "Já ouvi, mas não sei o que é", "Tenho uma ideia básica", "Conheço bem o tema"])
        with col2:
            q3 = st.text_area("3. O que você entende por 'tags' ou etiquetas digitais aplicadas a acervo?",
                              max_chars=500, height=200, placeholder="Descreva sua compreensão sobre o conceito...")

        col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])
        with col_btn2:
            submit = st.form_submit_button("Acessar Plataforma", use_container_width=True)

        if submit:
            if not q3.strip():
                st.error("Por favor, responda todas as perguntas para continuar!")
            else:
                st.session_state['answers'] = {"q1": q1, "q2": q2, "q3": q3}
                save_user_answers(
                    st.session_state['user_id'],
                    st.session_state['animal_name'],
                    st.session_state['answers']
                )
                st.session_state['step'] = 'completed'
                st.success("Questionário completo! Acesso liberado.")
                st.balloons()
                st.rerun()

    st.markdown("</div></div>", unsafe_allow_html=True)

def show_obras():
    st.markdown("<h1 class='main-title'>Galeria de Obras de Arte</h1>", unsafe_allow_html=True)
    st.markdown("<p class='subtitle'>Explore as obras e contribua com suas próprias tags descritivas</p>", unsafe_allow_html=True)

    obras = load_obras()
    if not obras:
        st.info("Nenhuma obra cadastrada no momento.")
        return

    # Barra de busca – apenas por ID (sem revelar título/artista ao usuário)
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    col1, col2 = st.columns([2, 1])
    with col1:
        search_id = st.text_input("Filtrar por número da obra:", "", placeholder="Ex: 1, 2, 3…")
    with col2:
        sort_order = st.selectbox("Ordenar por:", ["Número (crescente)", "Número (decrescente)"])
    st.markdown("</div>", unsafe_allow_html=True)

    filtered = obras
    if search_id.strip().isdigit():
        filtered = [o for o in obras if str(o['id']) == search_id.strip()]

    if sort_order == "Número (decrescente)":
        filtered = sorted(filtered, key=lambda x: x['id'], reverse=True)
    else:
        filtered = sorted(filtered, key=lambda x: x['id'])

    st.markdown(f"<div style='text-align:center;color:white;margin:2rem 0;font-size:1.2rem;font-weight:600;'>Exibindo <strong style='font-size:1.5rem;'>{len(filtered)}</strong> obra(s)</div>", unsafe_allow_html=True)

    cols = st.columns(3)
    for i, obra in enumerate(filtered):
        with cols[i % 3]:
            # USUÁRIO vê apenas imagem + número da obra (SEM título, artista ou ano)
            st.markdown(f"""
            <div class='obra-card'>
                <img src='{obra['imagem']}' alt='Obra {obra['id']}' />
                <div style='padding:1.5rem;'>
                    <h3 style='font-size:1.1rem;font-weight:700;margin-bottom:0.4rem;'>Obra #{obra['id']}</h3>
                    <p style='font-size:0.9rem;opacity:0.7;'>Adicione uma tag descritiva para esta imagem</p>
                </div>
            </div>
            """, unsafe_allow_html=True)

            if st.button(f"🏷️ Adicionar Tag", key=f"btn_{obra['id']}", use_container_width=True):
                st.session_state['selected_obra'] = obra
                st.rerun()

            if 'selected_obra' in st.session_state and st.session_state['selected_obra']['id'] == obra['id']:
                with st.form(f"tag_form_{obra['id']}"):
                    tag = st.text_input("Sua tag:", key=f"tag_{obra['id']}", placeholder="Ex: azul, triste, moderno…")
                    col_a, col_b = st.columns(2)
                    with col_a:
                        submitted = st.form_submit_button("✅ Enviar", use_container_width=True)
                    with col_b:
                        cancel = st.form_submit_button("❌ Cancelar", use_container_width=True)

                    if submitted and tag:
                        save_tag(st.session_state['user_id'], obra['id'], tag)
                        st.success(f"Tag '{tag}' adicionada!")
                        del st.session_state['selected_obra']
                        st.rerun()
                    if cancel:
                        del st.session_state['selected_obra']
                        st.rerun()

            tags = get_tags_for_obra_by_user(obra['id'], st.session_state['user_id'])
            if not tags.empty:
                st.markdown("**Suas Tags:**")
                html_tags = "".join(
                    f"<span class='tag-badge'>{row['tag']} ({row['count']})</span>"
                    for _, row in tags.iterrows()
                )
                st.markdown(html_tags, unsafe_allow_html=True)
            else:
                st.info("Você ainda não criou tags para esta obra")

def show_admin():
    if 'admin_logged_in' not in st.session_state:
        st.session_state['admin_logged_in'] = False

    if not st.session_state['admin_logged_in']:
        st.markdown("<h1 class='main-title'>Área Administrativa</h1>", unsafe_allow_html=True)
        st.markdown("<p class='subtitle'>Acesso restrito</p>", unsafe_allow_html=True)

        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
            st.markdown("<h2 style='text-align:center;margin-bottom:2rem;'>Login Administrativo</h2>", unsafe_allow_html=True)
            with st.form("login"):
                username = st.text_input("Usuário:", placeholder="Digite seu usuário")
                password = st.text_input("Senha:", type="password", placeholder="Digite sua senha")
                submitted = st.form_submit_button("Entrar no Sistema", use_container_width=True)
                if submitted:
                    if check_admin_credentials(username, password):
                        st.session_state['admin_logged_in'] = True
                        st.session_state['admin_username'] = username
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
            "📊 Visão Geral",
            "📈 Análises",
            "🔗 Conexões de Tags",
            "📋 Dados",
            "🖼️ Obras",
            "📤 Exportar Completo",
            "👤 Exportar Usuários"
        ])

        with tabs[0]: show_overview()
        with tabs[1]: show_analysis()
        with tabs[2]: show_tag_connections()
        with tabs[3]: show_data_analysis()
        with tabs[4]: show_manage_obras()
        with tabs[5]: show_export_complete()
        with tabs[6]: show_export_users()

        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button("🚪 Sair do Sistema", use_container_width=True):
                st.session_state['admin_logged_in'] = False
                st.rerun()

# ==================== VISÃO GERAL ====================
def show_overview():
    tags_df = load_all_tags()
    users_df = load_all_users()
    obras = load_obras()

    st.markdown("### 📊 Métricas Principais")
    col1, col2, col3, col4 = st.columns(4)
    metrics = [
        ("Usuários", len(users_df['user_id'].unique()) if not users_df.empty else 0),
        ("Total Tags",  len(tags_df) if not tags_df.empty else 0),
        ("Tags Únicas", len(tags_df['tag'].unique()) if not tags_df.empty else 0),
        ("Obras",       len(obras))
    ]
    for col, (label, value) in zip([col1, col2, col3, col4], metrics):
        with col:
            st.markdown(f"<div class='metric-card'><div class='metric-label'>{label}</div><div class='metric-value'>{value}</div></div>", unsafe_allow_html=True)

    if not users_df.empty:
        st.markdown("### 🐾 Usuários Anônimos (Nomes de Animais)")
        for _, row in users_df.iterrows():
            animal = row.get('animal_name', '?')
            uid = row.get('user_id', '')[:8]
            ts = row.get('timestamp', 'N/A')
            n_tags = len(tags_df[tags_df['user_id'] == row.get('user_id', '')]) if not tags_df.empty else 0
            st.markdown(
                f"<span class='animal-badge'>🐾 {animal}</span> &nbsp; "
                f"<span style='color:rgba(255,255,255,0.6);font-size:0.85rem;'>ID: {uid}… | Acesso: {ts} | Tags criadas: {n_tags}</span>",
                unsafe_allow_html=True
            )

    if not tags_df.empty:
        st.markdown("### 🏆 Rankings")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### Top 15 Tags Mais Utilizadas")
            top = tags_df['tag'].value_counts().head(15).reset_index()
            top.columns = ['Tag', 'Quantidade']
            st.dataframe(top, use_container_width=True, hide_index=True)
        with col2:
            st.markdown("#### Obras Mais Tagueadas")
            ot = tags_df.groupby('obra_id').size().reset_index(name='Total')
            od = {o['id']: o['titulo'] for o in obras}
            ot['Obra'] = ot['obra_id'].map(od)
            st.dataframe(ot[['Obra', 'Total']].sort_values('Total', ascending=False).head(10),
                         use_container_width=True, hide_index=True)

# ==================== ANÁLISES ====================
def show_analysis():
    st.markdown("### 📈 Análises Gerais")
    tags_df = load_all_tags()
    users_df = load_all_users()
    obras = load_obras()

    if tags_df.empty:
        st.info("Não há dados suficientes para análises.")
        return

    # ---- KPIs avançados
    st.markdown("#### 🔢 Indicadores Avançados")
    total_tags   = len(tags_df)
    unique_tags  = tags_df['tag'].nunique()
    n_users_with_tags = tags_df['user_id'].nunique()
    avg_tags_user = total_tags / n_users_with_tags if n_users_with_tags else 0
    vocab_richness = unique_tags / total_tags if total_tags else 0       # type-token ratio
    obras_covered = tags_df['obra_id'].nunique()

    col1, col2, col3 = st.columns(3)
    kpis = [
        ("Média Tags/Usuário", f"{avg_tags_user:.1f}"),
        ("Riqueza Vocabular", f"{vocab_richness:.2%}"),
        ("Obras com Tags",    f"{obras_covered}/{len(obras)}")
    ]
    for col, (label, value) in zip([col1, col2, col3], kpis):
        with col:
            st.markdown(f"<div class='metric-card'><div class='metric-label'>{label}</div><div class='metric-value' style='font-size:2.2rem'>{value}</div></div>", unsafe_allow_html=True)

    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Distribuição de Tags (Top 15)")
        counts = tags_df['tag'].value_counts().head(15)
        st.bar_chart(counts)
    with col2:
        st.markdown("#### Obras Mais Tagueadas (Top 10)")
        per_obra = tags_df.groupby('obra_id').size()
        od = {o['id']: o['titulo'] for o in obras}
        per_obra_named = per_obra.rename(index=od).sort_values(ascending=False).head(10)
        st.bar_chart(per_obra_named)

    # ---- Distribuição de comprimento
    st.markdown("#### 📏 Comprimento das Tags")
    tags_df['tag_len'] = tags_df['tag'].str.len()
    tags_df['word_count'] = tags_df['tag'].str.split().str.len()
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Distribuição por nº de caracteres**")
        st.bar_chart(tags_df['tag_len'].value_counts().sort_index())
    with col2:
        st.markdown("**Distribuição por nº de palavras**")
        st.bar_chart(tags_df['word_count'].value_counts().sort_index())

    col_a, col_b = st.columns(2)
    with col_a:
        st.write(f"📏 Média de caracteres por tag: **{tags_df['tag_len'].mean():.2f}**")
        st.write(f"📏 Desvio padrão: **{tags_df['tag_len'].std():.2f}**")
    with col_b:
        st.write(f"💬 Média de palavras por tag: **{tags_df['word_count'].mean():.2f}**")
        st.write(f"💬 Tags multipalavra: **{(tags_df['word_count'] > 1).sum()}** ({(tags_df['word_count'] > 1).mean():.1%})")

    # ---- Tags raras
    st.markdown("#### 🔍 Tags Raras (usadas apenas uma vez)")
    rare = tags_df['tag'].value_counts()
    rare_tags = rare[rare == 1].reset_index()
    rare_tags.columns = ['Tag', 'Frequência']
    st.write(f"Total de tags únicas (hapax legomena): **{len(rare_tags)}** — {len(rare_tags)/len(rare):.1%} do vocabulário total")
    st.dataframe(rare_tags.head(20), use_container_width=True, hide_index=True)

    # ---- Evolução temporal
    st.markdown("#### 🕒 Evolução Temporal das Tags")
    try:
        tags_df['ts'] = pd.to_datetime(tags_df['timestamp'])
        tags_df['date'] = tags_df['ts'].dt.date
        daily = tags_df.groupby('date').size().reset_index(name='Tags Criadas')
        daily = daily.set_index('date')
        st.line_chart(daily)
    except Exception:
        st.info("Dados insuficientes para análise temporal.")

    # ---- Tags por usuário (identificadas por nome animal)
    if not users_df.empty and not tags_df.empty:
        st.markdown("#### 🐾 Participação por Usuário")
        user_tag_ct = tags_df.groupby('user_id').size().reset_index(name='Total Tags')
        user_unique_ct = tags_df.groupby('user_id')['tag'].nunique().reset_index(name='Tags Únicas')
        merged = user_tag_ct.merge(user_unique_ct, on='user_id')
        animal_map = {row['user_id']: row.get('animal_name', row['user_id'][:8])
                      for _, row in users_df.iterrows()}
        merged['Usuário'] = merged['user_id'].map(animal_map)
        merged['Riqueza'] = (merged['Tags Únicas'] / merged['Total Tags']).round(3)
        st.dataframe(
            merged[['Usuário', 'Total Tags', 'Tags Únicas', 'Riqueza']]
            .sort_values('Total Tags', ascending=False),
            use_container_width=True, hide_index=True
        )

# ==================== CONEXÕES DE TAGS ====================
def show_tag_connections():
    st.markdown("### 🔗 Análise de Conexões e Similaridade entre Tags")
    st.info(
        "Esta seção identifica automaticamente tags semanticamente relacionadas usando "
        "três métricas combinadas: contenção de substring, similaridade de palavras (Jaccard) "
        "e similaridade de n-gramas de caracteres."
    )

    tags_df = load_all_tags()
    if tags_df.empty:
        st.warning("Nenhuma tag disponível para analisar.")
        return

    obras = load_obras()
    od = {o['id']: o['titulo'] for o in obras}

    # Controles
    col1, col2, col3 = st.columns(3)
    with col1:
        threshold = st.slider("Limiar de similaridade:", 0.20, 0.90, 0.35, 0.05,
                              help="Mínimo de similaridade para exibir uma conexão")
    with col2:
        obra_filter = st.selectbox("Filtrar por obra:", ["Todas"] + [f"{o['id']} – {o['titulo']}" for o in obras])
    with col3:
        max_connections = st.number_input("Máx. conexões exibidas:", 10, 500, 50, 10)

    # Filtrar tags
    filtered_tags_df = tags_df.copy()
    if obra_filter != "Todas":
        obra_id_sel = int(obra_filter.split("–")[0].strip())
        filtered_tags_df = tags_df[tags_df['obra_id'] == obra_id_sel]

    all_tags_list = filtered_tags_df['tag'].tolist()
    if len(set(all_tags_list)) < 2:
        st.warning("São necessárias ao menos 2 tags distintas para analisar conexões.")
        return

    with st.spinner("Calculando similaridades entre tags…"):
        connections = find_tag_connections(all_tags_list, threshold=threshold)

    st.markdown(f"**{len(connections)} conexão(ões) encontrada(s)** com limiar ≥ {threshold:.2f}")

    # ---- Tabs de apresentação
    tab1, tab2, tab3 = st.tabs(["📋 Lista de Conexões", "🗂️ Grupos (Clusters)", "📊 Matriz de Similaridade"])

    with tab1:
        if not connections:
            st.info("Nenhuma conexão encontrada. Reduza o limiar de similaridade.")
        else:
            for conn in connections[:max_connections]:
                score = conn['similaridade']
                css_cls = "conn-score-high" if score >= 0.7 else ("conn-score-med" if score >= 0.5 else "conn-score-low")
                score_bar = "█" * int(score * 10) + "░" * (10 - int(score * 10))
                st.markdown(f"""
                <div class='connection-card {css_cls}'>
                    <div style='display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;'>
                        <div>
                            <span class='tag-badge'>{conn['tag_a']}</span>
                            <span style='color:rgba(255,255,255,0.6);margin:0 8px;'>↔</span>
                            <span class='tag-badge'>{conn['tag_b']}</span>
                        </div>
                        <div style='text-align:right;'>
                            <div style='font-family:monospace;color:rgba(255,255,255,0.8);font-size:0.85rem;'>{score_bar} {score:.3f}</div>
                            <div style='font-size:0.8rem;color:rgba(255,255,255,0.55);margin-top:2px;'>{conn['tipo']}</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            # Download CSV de conexões
            conn_df = pd.DataFrame(connections[:max_connections])
            csv_conn = conn_df.to_csv(index=False).encode('utf-8')
            st.download_button("⬇️ Baixar Conexões (CSV)", csv_conn,
                               f"conexoes_tags_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv")

    with tab2:
        clusters = find_tag_clusters(all_tags_list, threshold=threshold)
        if not clusters:
            st.info("Nenhum grupo formado. Reduza o limiar de similaridade.")
        else:
            st.markdown(f"**{len(clusters)} grupo(s) de tags relacionadas encontrado(s):**")
            for i, cluster in enumerate(sorted(clusters, key=len, reverse=True), 1):
                tags_html = "".join(f"<span class='tag-badge'>{t}</span>" for t in cluster)
                st.markdown(f"""
                <div class='cluster-card'>
                    <div style='font-size:0.85rem;color:rgba(209,186,255,0.8);margin-bottom:8px;font-weight:700;'>
                        Grupo {i} &nbsp;·&nbsp; {len(cluster)} tags relacionadas
                    </div>
                    {tags_html}
                </div>
                """, unsafe_allow_html=True)

            # Estatísticas de clusters
            st.markdown("#### Estatísticas dos Grupos")
            cluster_stats = pd.DataFrame({
                'Grupo': [f"Grupo {i}" for i in range(1, len(clusters)+1)],
                'Tamanho': [len(c) for c in clusters],
                'Tags': [", ".join(c[:5]) + ("…" if len(c) > 5 else "") for c in clusters]
            }).sort_values('Tamanho', ascending=False)
            st.dataframe(cluster_stats, use_container_width=True, hide_index=True)

    with tab3:
        # Matriz de similaridade para as top tags
        top_n = min(20, len(set(all_tags_list)))
        top_tags_list = tags_df['tag'].value_counts().head(top_n).index.tolist()
        if len(top_tags_list) < 2:
            st.info("Tags insuficientes para a matriz.")
        else:
            st.markdown(f"#### Matriz de Similaridade (Top {top_n} tags mais frequentes)")
            matrix = np.zeros((len(top_tags_list), len(top_tags_list)))
            for i, t1 in enumerate(top_tags_list):
                for j, t2 in enumerate(top_tags_list):
                    matrix[i][j] = calculate_tag_similarity(t1, t2)
            matrix_df = pd.DataFrame(matrix, index=top_tags_list, columns=top_tags_list)
            st.dataframe(matrix_df.round(3), use_container_width=True)

            # Pares mais similares excluindo diagonal
            upper = matrix_df.where(np.triu(np.ones(matrix_df.shape), k=1).astype(bool))
            flat = upper.stack().reset_index()
            flat.columns = ['Tag A', 'Tag B', 'Similaridade']
            flat = flat.sort_values('Similaridade', ascending=False)
            st.markdown("**Top 10 pares mais similares:**")
            st.dataframe(flat.head(10), use_container_width=True, hide_index=True)

# ==================== DADOS DETALHADOS ====================
def show_data_analysis():
    st.markdown("### 📋 Análise Detalhada de Dados")
    tags_df = load_all_tags()
    users_df = load_all_users()
    obras = load_obras()

    if tags_df.empty and users_df.empty:
        st.info("Sem dados suficientes para análise detalhada.")
        return

    tab_ov, tab_tags, tab_quest, tab_cross = st.tabs([
        "Visão Geral", "Análise de Tags", "Questionário", "Cruzamentos"
    ])

    with tab_ov:
        st.markdown("#### Resumo dos Dados Coletados")
        col1, col2, col3, col4 = st.columns(4)
        metrics = [
            ("Total Usuários", len(users_df['user_id'].unique()) if not users_df.empty else 0),
            ("Total Tags",     len(tags_df) if not tags_df.empty else 0),
            ("Tags Únicas",    tags_df['tag'].nunique() if not tags_df.empty else 0),
            ("Total Obras",    len(obras))
        ]
        for col, (label, value) in zip([col1, col2, col3, col4], metrics):
            with col:
                st.markdown(f"<div class='metric-card'><div class='metric-label'>{label}</div><div class='metric-value'>{value}</div></div>", unsafe_allow_html=True)

        if not tags_df.empty:
            st.markdown("#### Top 10 Tags Mais Frequentes")
            st.bar_chart(tags_df['tag'].value_counts().head(10))
            st.markdown("#### Distribuição por Obra")
            ot = tags_df.groupby('obra_id').size().reset_index(name='Total')
            od = {o['id']: o['titulo'] for o in obras}
            ot['Obra'] = ot['obra_id'].map(od)
            st.bar_chart(ot[['Obra', 'Total']].sort_values('Total', ascending=False).head(10).set_index('Obra'))

    with tab_tags:
        st.markdown("#### Frequências de Todas as Tags")
        if not tags_df.empty:
            freq = tags_df['tag'].value_counts().reset_index()
            freq.columns = ['Tag', 'Frequência']
            freq['% do Total'] = (freq['Frequência'] / freq['Frequência'].sum() * 100).round(2)
            freq['Freq. Acumulada %'] = freq['% do Total'].cumsum().round(2)
            st.dataframe(freq, use_container_width=True, hide_index=True)

            st.markdown("#### Tags Únicas por Obra")
            uniq_obra = tags_df.groupby('obra_id')['tag'].nunique().reset_index()
            uniq_obra.columns = ['obra_id', 'Tags Únicas']
            od = {o['id']: o['titulo'] for o in obras}
            uniq_obra['Obra'] = uniq_obra['obra_id'].map(od)
            st.bar_chart(uniq_obra.sort_values('Tags Únicas', ascending=False).set_index('Obra')['Tags Únicas'])

            st.markdown("#### Tags Únicas por Usuário (Animais)")
            uniq_user = tags_df.groupby('user_id')['tag'].nunique().reset_index()
            uniq_user.columns = ['user_id', 'Tags Únicas']
            if not users_df.empty:
                animal_map = {r['user_id']: r.get('animal_name', r['user_id'][:8]) for _, r in users_df.iterrows()}
                uniq_user['Usuário'] = uniq_user['user_id'].map(animal_map)
            else:
                uniq_user['Usuário'] = uniq_user['user_id'].str[:8]
            st.dataframe(uniq_user[['Usuário', 'Tags Únicas']].sort_values('Tags Únicas', ascending=False),
                         use_container_width=True, hide_index=True)

            st.markdown("#### Co-ocorrência de Tags (mesma obra)")
            tags_by_obra = tags_df.groupby('obra_id')['tag'].apply(lambda x: list(set(x))).tolist()
            co_occ = defaultdict(int)
            for tag_group in tags_by_obra:
                for i in range(len(tag_group)):
                    for j in range(i + 1, len(tag_group)):
                        pair = tuple(sorted((tag_group[i], tag_group[j])))
                        co_occ[pair] += 1
            if co_occ:
                co_df = pd.DataFrame(
                    [{"Tag A": k[0], "Tag B": k[1], "Co-ocorrências": v} for k, v in co_occ.items()]
                ).sort_values("Co-ocorrências", ascending=False)
                st.dataframe(co_df.head(30), use_container_width=True, hide_index=True)
            else:
                st.info("Dados insuficientes para análise de co-ocorrência.")

    with tab_quest:
        if users_df.empty:
            st.info("Nenhum usuário respondeu ao questionário ainda.")
        else:
            st.markdown("#### Q1 – Familiaridade com Museus")
            st.bar_chart(users_df['q1'].value_counts())
            st.markdown("#### Q2 – Conhecimento sobre Documentação Museológica")
            st.bar_chart(users_df['q2'].value_counts())
            st.markdown("#### Q3 – Respostas Abertas ('O que são tags?')")
            disp = users_df.copy()
            if 'animal_name' in disp.columns:
                disp = disp.rename(columns={'animal_name': 'Usuário Anônimo'})
            st.dataframe(disp[['Usuário Anônimo', 'q3', 'timestamp']].sort_values('timestamp', ascending=False),
                         use_container_width=True, hide_index=True)

    with tab_cross:
        if users_df.empty or tags_df.empty:
            st.info("Dados insuficientes para cruzamentos.")
            return

        st.markdown("#### Familiaridade com Museus vs. Média de Tags Criadas")
        user_ct = tags_df.groupby('user_id').size().reset_index(name='Total_Tags')
        merged = users_df.merge(user_ct, on='user_id', how='left').fillna(0)
        avg_fam = merged.groupby('q1')['Total_Tags'].mean().sort_values(ascending=False)
        st.bar_chart(avg_fam)
        st.dataframe(avg_fam.reset_index().rename(columns={'q1':'Familiaridade','Total_Tags':'Média de Tags'}),
                     use_container_width=True, hide_index=True)

        st.markdown("#### Conhecimento Museológico vs. Diversidade de Tags")
        user_uniq = tags_df.groupby('user_id')['tag'].nunique().reset_index(name='Tags_Unicas')
        merged2 = users_df.merge(user_uniq, on='user_id', how='left').fillna(0)
        avg_know = merged2.groupby('q2')['Tags_Unicas'].mean().sort_values(ascending=False)
        st.bar_chart(avg_know)
        st.dataframe(avg_know.reset_index().rename(columns={'q2':'Conhecimento','Tags_Unicas':'Média Tags Únicas'}),
                     use_container_width=True, hide_index=True)

        st.markdown("#### Correlação: Comprimento Médio da Tag vs. Familiaridade com Museus")
        tags_df['tag_len'] = tags_df['tag'].str.len()
        avg_len_user = tags_df.groupby('user_id')['tag_len'].mean().reset_index(name='Comp_Medio')
        merged3 = users_df.merge(avg_len_user, on='user_id', how='left').fillna(0)
        corr_data = merged3.groupby('q1')['Comp_Medio'].mean().sort_values(ascending=False)
        st.bar_chart(corr_data)

# ==================== GESTÃO DE OBRAS ====================
def show_manage_obras():
    st.markdown("### 🖼️ Gestão de Obras")
    obras = load_obras()

    tab1, tab2 = st.tabs(["Listar Obras", "Adicionar Nova"])
    with tab1:
        if obras:
            for obra in obras:
                col1, col2, col3 = st.columns([1, 2, 1])
                with col1:
                    st.image(obra['imagem'], use_container_width=True)
                with col2:
                    st.markdown(f"**#{obra['id']} – {obra['titulo']}**")
                    st.markdown(f"*{obra['artista']} — {obra['ano']}*")
                with col3:
                    if st.button("🗑️ Remover", key=f"del_{obra['id']}"):
                        obras.remove(obra)
                        save_json_file(OBRAS_FILE, obras)
                        st.success("Obra removida!")
                        st.cache_data.clear()
                        st.rerun()
                st.divider()
        else:
            st.info("Nenhuma obra cadastrada")

    with tab2:
        with st.form("add"):
            titulo  = st.text_input("Título da Obra")
            artista = st.text_input("Artista")
            ano     = st.text_input("Ano")
            imagem  = st.text_input("URL da Imagem")
            if st.form_submit_button("✅ Adicionar Obra"):
                if titulo and artista and ano and imagem:
                    new_id = max([o['id'] for o in obras]) + 1 if obras else 1
                    obras.append({"id": new_id, "titulo": titulo, "artista": artista, "ano": ano, "imagem": imagem})
                    save_json_file(OBRAS_FILE, obras)
                    st.success("Obra adicionada com sucesso!")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("Preencha todos os campos!")

# ==================== EXPORTAÇÃO COMPLETA ====================
def show_export_complete():
    st.markdown("### 📤 Exportação Completa do Sistema")
    tags_df  = load_all_tags()
    users_df = load_all_users()
    obras    = load_obras()

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Exportar CSV")
        if not tags_df.empty:
            csv = tags_df.to_csv(index=False).encode('utf-8')
            st.download_button("⬇️ Todas as Tags (CSV)", csv, f"tags_completo_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv", use_container_width=True)
        if not users_df.empty:
            export_users = users_df.copy()
            csv = export_users.to_csv(index=False).encode('utf-8')
            st.download_button("⬇️ Todos os Usuários (CSV)", csv, f"usuarios_completo_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv", use_container_width=True)
        if obras:
            csv = pd.DataFrame(obras).to_csv(index=False).encode('utf-8')
            st.download_button("⬇️ Todas as Obras (CSV)", csv, f"obras_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv", use_container_width=True)

    with col2:
        st.markdown("#### Exportar Conexões de Tags")
        if not tags_df.empty:
            all_tags_list = tags_df['tag'].tolist()
            threshold_exp = st.slider("Limiar para exportação:", 0.2, 0.9, 0.35, 0.05, key="exp_thresh")
            connections = find_tag_connections(all_tags_list, threshold=threshold_exp)
            if connections:
                conn_df = pd.DataFrame(connections)
                csv_conn = conn_df.to_csv(index=False).encode('utf-8')
                st.download_button("⬇️ Conexões de Tags (CSV)", csv_conn, f"conexoes_tags_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv", use_container_width=True)
                st.info(f"{len(connections)} conexões encontradas com limiar {threshold_exp:.2f}")

# ==================== EXPORTAÇÃO POR USUÁRIO ====================
def show_export_users():
    st.markdown("### 👤 Exportar Dados por Usuário")
    users_df = load_all_users()
    obras    = load_obras()

    if users_df.empty:
        st.info("Nenhum usuário cadastrado.")
        return

    user_ids = users_df['user_id'].unique().tolist()
    user_options = []
    for uid in user_ids:
        animal = users_df[users_df['user_id'] == uid].iloc[0].get('animal_name', uid[:8])
        user_options.append(f"🐾 {animal} (ID: {uid})")

    selected_option = st.selectbox("Selecione o usuário:", user_options)
    selected_user   = selected_option.split('(ID: ')[-1].replace(')', '').strip() if selected_option else None

    if selected_user:
        animal_disp = selected_option.split('(ID:')[0].replace('🐾', '').strip()
        st.markdown(f"#### Dados para o Usuário: **{animal_disp}**")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("##### Questionário")
            html = generate_user_questionnaire_report(selected_user, animal_disp)
            if html:
                st.download_button("⬇️ Respostas (HTML/PDF)", html, f"questionario_{selected_user[:8]}.html", "text/html", use_container_width=True)
            user_data = users_df[users_df['user_id'] == selected_user]
            if not user_data.empty:
                csv = user_data.to_csv(index=False).encode('utf-8')
                st.download_button("⬇️ Respostas (CSV)", csv, f"questionario_{selected_user[:8]}.csv", "text/csv", use_container_width=True)

        with col2:
            st.markdown("##### Tags Criadas")
            html = generate_user_tags_report(selected_user, animal_disp, obras)
            if html:
                st.download_button("⬇️ Tags (HTML/PDF)", html, f"tags_{selected_user[:8]}.html", "text/html", use_container_width=True)
            user_tags = get_user_tags(selected_user)
            if not user_tags.empty:
                csv = user_tags.to_csv(index=False).encode('utf-8')
                st.download_button("⬇️ Tags (CSV)", csv, f"tags_{selected_user[:8]}.csv", "text/csv", use_container_width=True)

        # Conexões de tags desse usuário
        user_tags_df = get_user_tags(selected_user)
        if not user_tags_df.empty and len(user_tags_df) >= 2:
            st.markdown("##### 🔗 Conexões nas Tags deste Usuário")
            user_conn = find_tag_connections(user_tags_df['tag'].tolist(), threshold=0.35)
            if user_conn:
                for c in user_conn[:15]:
                    st.markdown(
                        f"<span class='tag-badge'>{c['tag_a']}</span> ↔ "
                        f"<span class='tag-badge'>{c['tag_b']}</span> "
                        f"<span style='color:rgba(255,255,255,0.5);font-size:0.8rem;'>score: {c['similaridade']:.3f} | {c['tipo']}</span>",
                        unsafe_allow_html=True
                    )
            else:
                st.info("Nenhuma conexão forte encontrada nas tags deste usuário.")

if __name__ == "__main__":
    main()
