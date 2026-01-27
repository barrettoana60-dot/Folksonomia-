import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
import hashlib
import base64
import json
from collections import Counter
import re
from scipy import stats
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans, DBSCAN
from sklearn.metrics import silhouette_score
import warnings
warnings.filterwarnings('ignore')

# ==================== CONFIGURAÇÃO INICIAL ====================
st.set_page_config(
    page_title="Folksonomia Digital | Sistema Avançado",
    layout="wide",
    initial_sidebar_state="collapsed",
    page_icon="🎨"
)

# ==================== CONFIGURAÇÕES ====================
DATA_DIR = "data"
OBRAS_FILE = os.path.join(DATA_DIR, "obras.json")
TAGS_FILE = os.path.join(DATA_DIR, "tags.json")
USERS_FILE = os.path.join(DATA_DIR, "users.json")
ADMIN_FILE = os.path.join(DATA_DIR, "admin.json")

# Credenciais do Admin (OCULTAS)
ADMIN_USERNAME = "nugep"
ADMIN_PASSWORD = "nugep123"

# ==================== FUNÇÕES DE ARMAZENAMENTO ====================

def ensure_data_dir():
    """Garante que o diretório de dados existe"""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

def load_json_file(filepath, default_data):
    """Carrega dados de um arquivo JSON"""
    ensure_data_dir()
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            st.error(f"Erro ao carregar {filepath}: {e}")
            return default_data
    return default_data

def save_json_file(filepath, data):
    """Salva dados em um arquivo JSON"""
    ensure_data_dir()
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar {filepath}: {e}")
        return False

# ==================== CSS ULTRA MODERNO - TEMA AZUL ESCURO ====================
def load_custom_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
    }

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Background azul escuro profundo */
    .stApp {
        background: linear-gradient(135deg, #0a1628 0%, #0f1e3a 50%, #0a1628 100%);
        background-attachment: fixed;
    }

    /* Esconder sidebar */
    [data-testid="stSidebar"] {
        display: none;
    }

    /* Header superior fixo */
    .top-navbar {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        z-index: 999;
        background: rgba(10, 22, 40, 0.95);
        backdrop-filter: blur(20px);
        border-bottom: 1px solid rgba(59, 130, 246, 0.2);
        padding: 1rem 2rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.5);
    }

    .navbar-logo {
        font-size: 1.5rem;
        font-weight: 800;
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: -0.5px;
    }

    .navbar-buttons {
        display: flex;
        gap: 1rem;
    }

    /* Botões com animação 3D de "sair da tela" */
    .nav-btn {
        background: linear-gradient(135deg, #1e3a8a 0%, #1e40af 100%);
        color: #e0e7ff;
        border: 2px solid #3b82f6;
        border-radius: 12px;
        padding: 0.75rem 1.5rem;
        font-size: 0.95rem;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        position: relative;
        overflow: hidden;
        box-shadow: 0 4px 15px rgba(59, 130, 246, 0.3);
    }

    .nav-btn::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
        transition: left 0.5s;
    }

    .nav-btn:hover::before {
        left: 100%;
    }

    .nav-btn:hover {
        transform: translateY(-5px) scale(1.05);
        box-shadow: 0 10px 30px rgba(59, 130, 246, 0.5);
        border-color: #60a5fa;
    }

    .nav-btn:active {
        transform: translateY(-20px) scale(1.1) rotateX(10deg);
        box-shadow: 0 20px 50px rgba(59, 130, 246, 0.8);
    }

    .nav-btn.active {
        background: linear-gradient(135deg, #2563eb 0%, #3b82f6 100%);
        border-color: #60a5fa;
        box-shadow: 0 6px 25px rgba(59, 130, 246, 0.6);
    }

    /* Container principal */
    .main-content {
        margin-top: 100px;
        padding: 2rem;
        max-width: 1600px;
        margin-left: auto;
        margin-right: auto;
    }

    /* Cards azul escuro */
    .dark-blue-card {
        background: rgba(15, 30, 58, 0.8);
        backdrop-filter: blur(15px);
        border: 1px solid rgba(59, 130, 246, 0.3);
        border-radius: 16px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
        transition: all 0.3s ease;
    }

    .dark-blue-card:hover {
        border-color: rgba(59, 130, 246, 0.6);
        box-shadow: 0 12px 40px rgba(59, 130, 246, 0.3);
        transform: translateY(-3px);
    }

    /* Cards de obras com efeito 3D */
    .obra-card {
        background: rgba(15, 30, 58, 0.9);
        border: 1px solid rgba(59, 130, 246, 0.3);
        border-radius: 16px;
        padding: 1rem;
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        position: relative;
        overflow: hidden;
        cursor: pointer;
    }

    .obra-card::before {
        content: '';
        position: absolute;
        top: -50%;
        right: -50%;
        width: 200%;
        height: 200%;
        background: radial-gradient(circle, rgba(59, 130, 246, 0.1) 0%, transparent 70%);
        transform: scale(0);
        transition: transform 0.6s ease;
    }

    .obra-card:hover::before {
        transform: scale(1);
    }

    .obra-card:hover {
        border-color: rgba(96, 165, 250, 0.8);
        transform: translateY(-10px) scale(1.02);
        box-shadow: 0 20px 60px rgba(59, 130, 246, 0.4);
    }

    .obra-card img {
        border-radius: 12px;
        width: 100%;
        transition: transform 0.5s ease;
    }

    .obra-card:hover img {
        transform: scale(1.08) rotate(1deg);
    }

    .obra-title {
        color: #e0e7ff;
        font-size: 1.15rem;
        font-weight: 700;
        margin: 0.75rem 0 0.5rem 0;
    }

    .obra-info {
        color: #94a3b8;
        font-size: 0.9rem;
        margin: 0.25rem 0;
    }

    /* Títulos principais */
    .main-title {
        color: #e0e7ff;
        font-size: 3rem;
        font-weight: 800;
        text-align: center;
        margin: 2rem 0 1rem 0;
        background: linear-gradient(135deg, #3b82f6 0%, #60a5fa 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-shadow: 0 0 30px rgba(59, 130, 246, 0.5);
    }

    .subtitle {
        color: #94a3b8;
        font-size: 1.1rem;
        text-align: center;
        margin-bottom: 2.5rem;
        line-height: 1.7;
    }

    /* Tags badges */
    .tag-badge {
        display: inline-block;
        background: rgba(59, 130, 246, 0.2);
        border: 1px solid rgba(59, 130, 246, 0.4);
        color: #93c5fd;
        padding: 0.4rem 0.9rem;
        border-radius: 20px;
        margin: 0.3rem;
        font-size: 0.85rem;
        font-weight: 600;
        transition: all 0.3s ease;
        cursor: pointer;
    }

    .tag-badge:hover {
        background: rgba(59, 130, 246, 0.3);
        border-color: rgba(96, 165, 250, 0.6);
        transform: scale(1.1);
        box-shadow: 0 4px 15px rgba(59, 130, 246, 0.4);
    }

    /* Métricas do dashboard */
    .metric-card {
        background: linear-gradient(135deg, #1e40af 0%, #2563eb 100%);
        border: 1px solid rgba(96, 165, 250, 0.3);
        border-radius: 16px;
        padding: 2rem;
        text-align: center;
        color: white;
        box-shadow: 0 8px 30px rgba(37, 99, 235, 0.4);
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }

    .metric-card::before {
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
        animation: rotate 20s linear infinite;
    }

    @keyframes rotate {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }

    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 12px 40px rgba(37, 99, 235, 0.6);
    }

    .metric-value {
        font-size: 2.75rem;
        font-weight: 800;
        margin: 0.5rem 0;
        position: relative;
        z-index: 1;
    }

    .metric-label {
        font-size: 0.9rem;
        opacity: 0.95;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        font-weight: 600;
        position: relative;
        z-index: 1;
    }

    /* Botões do Streamlit customizados */
    .stButton button {
        background: linear-gradient(135deg, #1e40af 0%, #2563eb 100%);
        color: white;
        border: 2px solid #3b82f6;
        border-radius: 12px;
        padding: 0.75rem 2rem;
        font-weight: 700;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(59, 130, 246, 0.3);
    }

    .stButton button:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 25px rgba(59, 130, 246, 0.5);
        border-color: #60a5fa;
    }

    .stButton button:active {
        transform: translateY(-10px) scale(1.05);
        box-shadow: 0 15px 40px rgba(59, 130, 246, 0.7);
    }

    /* Inputs azul escuro */
    .stTextInput input, .stTextArea textarea, .stSelectbox select {
        background: rgba(10, 22, 40, 0.9) !important;
        border: 1px solid rgba(59, 130, 246, 0.3) !important;
        color: #e0e7ff !important;
        border-radius: 10px !important;
        padding: 0.75rem !important;
        transition: all 0.3s ease !important;
    }

    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: #3b82f6 !important;
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2) !important;
    }

    /* Labels */
    label {
        color: #cbd5e0 !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
    }

    /* Tabs modernos */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.75rem;
        background: transparent;
        border-bottom: 2px solid rgba(59, 130, 246, 0.2);
    }

    .stTabs [data-baseweb="tab"] {
        background: rgba(15, 30, 58, 0.6);
        border: 1px solid rgba(59, 130, 246, 0.3);
        border-radius: 12px 12px 0 0;
        color: #94a3b8;
        padding: 0.85rem 1.75rem;
        font-weight: 600;
        transition: all 0.3s ease;
    }

    .stTabs [data-baseweb="tab"]:hover {
        background: rgba(30, 64, 175, 0.4);
        color: #e0e7ff;
    }

    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #1e40af 0%, #2563eb 100%);
        border-color: #3b82f6;
        color: white;
        box-shadow: 0 4px 20px rgba(59, 130, 246, 0.4);
    }

    /* Alertas */
    .stAlert {
        background: rgba(15, 30, 58, 0.9);
        border: 1px solid rgba(59, 130, 246, 0.4);
        border-radius: 12px;
        color: #e0e7ff;
    }

    /* Progress bars */
    .stProgress > div > div {
        background: linear-gradient(90deg, #1e40af 0%, #3b82f6 50%, #60a5fa 100%);
    }

    /* Dataframes */
    .dataframe {
        background: rgba(15, 30, 58, 0.9) !important;
        color: #e0e7ff !important;
        border: 1px solid rgba(59, 130, 246, 0.3) !important;
        border-radius: 12px !important;
    }

    /* Gráficos */
    .js-plotly-plot {
        border-radius: 12px;
        overflow: hidden;
    }

    /* Scrollbar personalizado */
    ::-webkit-scrollbar {
        width: 12px;
        height: 12px;
    }

    ::-webkit-scrollbar-track {
        background: #0a1628;
    }

    ::-webkit-scrollbar-thumb {
        background: linear-gradient(135deg, #1e40af 0%, #2563eb 100%);
        border-radius: 6px;
    }

    ::-webkit-scrollbar-thumb:hover {
        background: linear-gradient(135deg, #2563eb 0%, #3b82f6 100%);
    }

    /* Animação de loading */
    .stSpinner > div {
        border-color: #3b82f6 !important;
        border-top-color: transparent !important;
    }

    /* Cards de análise avançada */
    .analysis-card {
        background: rgba(15, 30, 58, 0.95);
        border: 2px solid rgba(59, 130, 246, 0.4);
        border-radius: 16px;
        padding: 2rem;
        margin: 1.5rem 0;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5);
    }

    .analysis-title {
        color: #60a5fa;
        font-size: 1.4rem;
        font-weight: 700;
        margin-bottom: 1rem;
        border-bottom: 2px solid rgba(59, 130, 246, 0.3);
        padding-bottom: 0.5rem;
    }

    /* Estatísticas inline */
    .stat-inline {
        display: inline-block;
        background: rgba(59, 130, 246, 0.15);
        border: 1px solid rgba(59, 130, 246, 0.3);
        border-radius: 8px;
        padding: 0.5rem 1rem;
        margin: 0.5rem;
        color: #93c5fd;
        font-weight: 600;
    }

    /* Badges de status */
    .status-badge {
        display: inline-block;
        padding: 0.35rem 0.85rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    .status-high {
        background: rgba(34, 197, 94, 0.2);
        border: 1px solid rgba(34, 197, 94, 0.4);
        color: #86efac;
    }

    .status-medium {
        background: rgba(251, 191, 36, 0.2);
        border: 1px solid rgba(251, 191, 36, 0.4);
        color: #fcd34d;
    }

    .status-low {
        background: rgba(239, 68, 68, 0.2);
        border: 1px solid rgba(239, 68, 68, 0.4);
        color: #fca5a5;
    }

    /* Remover elementos padrão */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display: none;}

    /* Responsivo */
    @media (max-width: 768px) {
        .main-title {
            font-size: 2rem;
        }

        .top-navbar {
            flex-direction: column;
            gap: 1rem;
            padding: 1rem;
        }

        .main-content {
            margin-top: 140px;
            padding: 1rem;
        }

        .metric-value {
            font-size: 2rem;
        }
    }
    </style>
    """, unsafe_allow_html=True)

# ==================== FUNÇÕES AUXILIARES ====================

def check_and_init_admin():
    """Inicializa admin com credenciais ocultas"""
    admins = load_json_file(ADMIN_FILE, [])
    if not admins:
        hashed_password = hashlib.sha256(ADMIN_PASSWORD.encode()).hexdigest()
        admins.append({"id": 1, "username": ADMIN_USERNAME, "password": hashed_password})
        save_json_file(ADMIN_FILE, admins)

def generate_user_id():
    """Gera ID único para usuário"""
    return base64.b64encode(os.urandom(12)).decode('ascii')

@st.cache_data(ttl=5, show_spinner=False)
def load_obras():
    """Carrega obras do arquivo JSON"""
    default_obras = [
        {
            "id": 1,
            "titulo": "Guernica",
            "artista": "Pablo Picasso",
            "ano": "1937",
            "imagem": "https://upload.wikimedia.org/wikipedia/en/7/74/PicassoGuernica.jpg"
        },
        {
            "id": 2,
            "titulo": "A No Estrelada",
            "artista": "Vincent van Gogh",
            "ano": "1889",
            "imagem": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ea/Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg/1200px-Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg"
        },
        {
            "id": 3,
            "titulo": "Mona Lisa",
            "artista": "Leonardo da Vinci",
            "ano": "1503",
            "imagem": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ec/Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_retouched.jpg/800px-Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_retouched.jpg"
        }
    ]
    obras = load_json_file(OBRAS_FILE, default_obras)
    if not obras:
        save_json_file(OBRAS_FILE, default_obras)
        return default_obras
    return obras

def save_user_answers(user_id, answers):
    """Salva respostas do questionário"""
    users = load_json_file(USERS_FILE, [])
    new_user = {
        "user_id": user_id,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "q1": answers["q1"],
        "q2": answers["q2"],
        "q3": answers["q3"]
    }
    users.append(new_user)
    return save_json_file(USERS_FILE, users)

def save_tag(user_id, obra_id, tag):
    """Salva tag associada a uma obra"""
    tags = load_json_file(TAGS_FILE, [])
    new_tag = {
        "id": len(tags) + 1,
        "user_id": user_id,
        "obra_id": obra_id,
        "tag": tag.lower().strip(),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    tags.append(new_tag)
    st.cache_data.clear()
    return save_json_file(TAGS_FILE, tags)

def get_tags_for_obra(obra_id):
    """Obtém tags de uma obra específica"""
    tags = load_json_file(TAGS_FILE, [])
    obra_tags = [tag for tag in tags if tag['obra_id'] == obra_id]

    if obra_tags:
        tags_df = pd.DataFrame(obra_tags)
        tag_counts = tags_df['tag'].value_counts().reset_index()
        tag_counts.columns = ["tag", "count"]
        return tag_counts
    return pd.DataFrame(columns=["tag", "count"])

def check_admin_credentials(username, password):
    """Verifica credenciais do administrador"""
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    expected_hash = hashlib.sha256(ADMIN_PASSWORD.encode()).hexdigest()

    return username == ADMIN_USERNAME and hashed_password == expected_hash

def load_all_tags():
    """Carrega todas as tags"""
    tags = load_json_file(TAGS_FILE, [])
    return pd.DataFrame(tags) if tags else pd.DataFrame()

def load_all_users():
    """Carrega todos os usuários"""
    users = load_json_file(USERS_FILE, [])
    return pd.DataFrame(users) if users else pd.DataFrame()

# ==================== ANÁLISES AVANÇADAS ====================

def calculate_tag_diversity(tags_df):
    """Calcula diversidade de tags usando índice de Shannon"""
    if tags_df.empty:
        return 0
    tag_counts = tags_df['tag'].value_counts()
    proportions = tag_counts / tag_counts.sum()
    shannon_index = -sum(proportions * np.log(proportions + 1e-10))
    return shannon_index

def calculate_simpson_index(tags_df):
    """Calcula índice de Simpson para diversidade"""
    if tags_df.empty:
        return 0
    tag_counts = tags_df['tag'].value_counts()
    proportions = tag_counts / tag_counts.sum()
    simpson_index = 1 - sum(proportions ** 2)
    return simpson_index

def analyze_user_engagement(users_df, tags_df):
    """Análise detalhada de engajamento"""
    if users_df.empty or tags_df.empty:
        return None

    tags_per_user = tags_df.groupby('user_id').size().reset_index(name='tag_count')

    engagement_stats = {
        'avg_tags_per_user': tags_per_user['tag_count'].mean(),
        'median_tags_per_user': tags_per_user['tag_count'].median(),
        'std_tags_per_user': tags_per_user['tag_count'].std(),
        'max_tags_per_user': tags_per_user['tag_count'].max(),
        'min_tags_per_user': tags_per_user['tag_count'].min(),
        'total_active_users': len(tags_per_user),
        'total_registered_users': len(users_df),
        'engagement_rate': (len(tags_per_user) / len(users_df) * 100) if len(users_df) > 0 else 0
    }

    # Percentis
    engagement_stats['p25'] = tags_per_user['tag_count'].quantile(0.25)
    engagement_stats['p75'] = tags_per_user['tag_count'].quantile(0.75)
    engagement_stats['p90'] = tags_per_user['tag_count'].quantile(0.90)

    return engagement_stats

def get_top_contributors(tags_df, top_n=10):
    """Identifica principais contribuidores com análise temporal"""
    if tags_df.empty:
        return pd.DataFrame()

    contributors = tags_df.groupby('user_id').agg({
        'tag': 'count',
        'timestamp': ['min', 'max']
    }).reset_index()

    contributors.columns = ['user_id', 'total_tags', 'first_contribution', 'last_contribution']

    # Calcular dias ativos
    contributors['first_contribution'] = pd.to_datetime(contributors['first_contribution'])
    contributors['last_contribution'] = pd.to_datetime(contributors['last_contribution'])
    contributors['days_active'] = (contributors['last_contribution'] - contributors['first_contribution']).dt.days + 1
    contributors['tags_per_day'] = contributors['total_tags'] / contributors['days_active']

    contributors = contributors.sort_values('total_tags', ascending=False).head(top_n)

    return contributors

def analyze_tag_patterns(tags_df):
    """Análise profunda de padrões de tags"""
    if tags_df.empty:
        return None

    patterns = {
        'total_tags': len(tags_df),
        'unique_tags': len(tags_df['tag'].unique()),
        'avg_tag_length': tags_df['tag'].str.len().mean(),
        'median_tag_length': tags_df['tag'].str.len().median(),
        'max_tag_length': tags_df['tag'].str.len().max(),
        'min_tag_length': tags_df['tag'].str.len().min(),
        'single_word_tags': sum(tags_df['tag'].str.split().str.len() == 1),
        'multi_word_tags': sum(tags_df['tag'].str.split().str.len() > 1),
        'numeric_tags': sum(tags_df['tag'].str.contains(r'\d', regex=True)),
        'special_char_tags': sum(tags_df['tag'].str.contains(r'[^a-zA-Z0-9\s]', regex=True)),
        'uppercase_tags': sum(tags_df['tag'].str.contains(r'[A-Z]', regex=True))
    }

    # Percentual de tags únicas
    patterns['uniqueness_ratio'] = (patterns['unique_tags'] / patterns['total_tags'] * 100) if patterns['total_tags'] > 0 else 0

    # Tags mais reusadas
    tag_counts = tags_df['tag'].value_counts()
    patterns['most_reused_tag'] = tag_counts.index[0] if len(tag_counts) > 0 else None
    patterns['most_reused_count'] = tag_counts.values[0] if len(tag_counts) > 0 else 0
    patterns['reuse_rate'] = ((patterns['total_tags'] - patterns['unique_tags']) / patterns['total_tags'] * 100) if patterns['total_tags'] > 0 else 0

    return patterns

def analyze_temporal_patterns(tags_df):
    """Análise temporal avançada"""
    if tags_df.empty or 'timestamp' not in tags_df.columns:
        return None

    tags_df['timestamp'] = pd.to_datetime(tags_df['timestamp'])
    tags_df['date'] = tags_df['timestamp'].dt.date
    tags_df['hour'] = tags_df['timestamp'].dt.hour
    tags_df['day_of_week'] = tags_df['timestamp'].dt.day_name()
    tags_df['week'] = tags_df['timestamp'].dt.isocalendar().week
    tags_df['month'] = tags_df['timestamp'].dt.month

    temporal_stats = {
        'total_days': (tags_df['date'].max() - tags_df['date'].min()).days + 1,
        'tags_per_day_avg': len(tags_df) / ((tags_df['date'].max() - tags_df['date'].min()).days + 1),
        'most_active_hour': tags_df['hour'].mode()[0] if not tags_df['hour'].mode().empty else None,
        'most_active_day': tags_df['day_of_week'].mode()[0] if not tags_df['day_of_week'].mode().empty else None,
        'peak_activity_date': tags_df.groupby('date').size().idxmax() if len(tags_df) > 0 else None,
        'peak_activity_count': tags_df.groupby('date').size().max() if len(tags_df) > 0 else 0
    }

    # Análise de crescimento
    daily_tags = tags_df.groupby('date').size().reset_index(name='count')
    if len(daily_tags) > 1:
        daily_tags['cumulative'] = daily_tags['count'].cumsum()
        daily_tags['growth_rate'] = daily_tags['count'].pct_change() * 100
        temporal_stats['avg_growth_rate'] = daily_tags['growth_rate'].mean()
        temporal_stats['max_growth_day'] = daily_tags.loc[daily_tags['growth_rate'].idxmax(), 'date'] if not daily_tags['growth_rate'].isna().all() else None

    return temporal_stats

def perform_clustering_analysis(tags_df, obras):
    """Análise de clustering de obras baseado em tags"""
    if tags_df.empty or not obras:
        return None

    # Criar matriz obra-tag
    obra_tag_matrix = tags_df.groupby(['obra_id', 'tag']).size().unstack(fill_value=0)

    if len(obra_tag_matrix) < 2:
        return None

    # Normalizar
    scaler = StandardScaler()
    normalized_data = scaler.fit_transform(obra_tag_matrix)

    # K-means
    n_clusters = min(3, len(obra_tag_matrix))
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    clusters = kmeans.fit_predict(normalized_data)

    # Silhouette score
    if len(set(clusters)) > 1:
        silhouette = silhouette_score(normalized_data, clusters)
    else:
        silhouette = 0

    # PCA para visualização
    if obra_tag_matrix.shape[1] > 1:
        pca = PCA(n_components=min(2, obra_tag_matrix.shape[1]))
        pca_result = pca.fit_transform(normalized_data)
        variance_explained = pca.explained_variance_ratio_.sum()
    else:
        pca_result = None
        variance_explained = 0

    results = {
        'n_clusters': n_clusters,
        'silhouette_score': silhouette,
        'clusters': clusters,
        'variance_explained': variance_explained,
        'pca_result': pca_result,
        'obra_ids': obra_tag_matrix.index.tolist()
    }

    return results

def calculate_tag_quality_metrics(tags_df):
    """Métricas de qualidade das tags"""
    if tags_df.empty:
        return None

    quality_metrics = {}

    # Especificidade (tags únicas vs totais)
    quality_metrics['specificity'] = len(tags_df['tag'].unique()) / len(tags_df) * 100

    # Consistência (variação no tamanho das tags)
    tag_lengths = tags_df['tag'].str.len()
    quality_metrics['consistency'] = 100 - (tag_lengths.std() / tag_lengths.mean() * 100) if tag_lengths.mean() > 0 else 0

    # Completude (% de obras com pelo menos 3 tags)
    tags_per_obra = tags_df.groupby('obra_id').size()
    quality_metrics['completeness'] = (tags_per_obra >= 3).sum() / len(tags_per_obra) * 100 if len(tags_per_obra) > 0 else 0

    # Riqueza vocabular (razão de palavras únicas por tags)
    all_words = ' '.join(tags_df['tag']).split()
    quality_metrics['vocabulary_richness'] = len(set(all_words)) / len(all_words) * 100 if len(all_words) > 0 else 0

    # Densidade de informação (média de palavras por tag)
    quality_metrics['information_density'] = tags_df['tag'].str.split().str.len().mean()

    # Score geral de qualidade (média ponderada)
    quality_metrics['overall_quality_score'] = (
        quality_metrics['specificity'] * 0.25 +
        quality_metrics['consistency'] * 0.20 +
        quality_metrics['completeness'] * 0.25 +
        quality_metrics['vocabulary_richness'] * 0.15 +
        min(quality_metrics['information_density'] * 20, 15)  # max 15 pontos
    )

    return quality_metrics

def analyze_user_segmentation(tags_df, users_df):
    """Segmentação de usuários por comportamento"""
    if tags_df.empty or users_df.empty:
        return None

    user_behavior = tags_df.groupby('user_id').agg({
        'tag': ['count', 'nunique'],
        'timestamp': lambda x: (pd.to_datetime(x.max()) - pd.to_datetime(x.min())).days + 1
    }).reset_index()

    user_behavior.columns = ['user_id', 'total_tags', 'unique_tags', 'days_active']
    user_behavior['tags_per_day'] = user_behavior['total_tags'] / user_behavior['days_active']
    user_behavior['diversity_ratio'] = user_behavior['unique_tags'] / user_behavior['total_tags']

    # Segmentar usuários
    def categorize_user(row):
        if row['total_tags'] >= 10 and row['diversity_ratio'] > 0.7:
            return 'Power User'
        elif row['total_tags'] >= 5:
            return 'Active User'
        elif row['total_tags'] >= 2:
            return 'Casual User'
        else:
            return 'One-time User'

    user_behavior['segment'] = user_behavior.apply(categorize_user, axis=1)

    segmentation = user_behavior['segment'].value_counts().to_dict()

    return {
        'segmentation': segmentation,
        'user_behavior_df': user_behavior
    }

def calculate_correlation_metrics(tags_df, obras):
    """Análise de correlação entre tags e obras"""
    if tags_df.empty or len(obras) < 2:
        return None

    # Matriz de co-ocorrência de tags
    obra_tags = tags_df.groupby('obra_id')['tag'].apply(list).to_dict()

    # Encontrar tags que aparecem em múltiplas obras
    tag_obra_count = {}
    for obra_id, tags in obra_tags.items():
        for tag in set(tags):
            if tag not in tag_obra_count:
                tag_obra_count[tag] = set()
            tag_obra_count[tag].add(obra_id)

    # Tags compartilhadas entre obras
    shared_tags = {tag: len(obras) for tag, obras in tag_obra_count.items() if len(obras) > 1}

    correlation_metrics = {
        'total_shared_tags': len(shared_tags),
        'most_shared_tag': max(shared_tags, key=shared_tags.get) if shared_tags else None,
        'max_share_count': max(shared_tags.values()) if shared_tags else 0,
        'avg_tags_per_obra': tags_df.groupby('obra_id').size().mean()
    }

    return correlation_metrics

def predict_future_tags(tags_df, days_ahead=7):
    """Predição simples de tags futuras baseado em tendências"""
    if tags_df.empty or 'timestamp' not in tags_df.columns:
        return None

    tags_df['date'] = pd.to_datetime(tags_df['timestamp']).dt.date
    daily_counts = tags_df.groupby('date').size().reset_index(name='count')

    if len(daily_counts) < 3:
        return None

    # Calcular tendência linear simples
    daily_counts['day_num'] = range(len(daily_counts))

    # Usar numpy para regressão linear
    coefficients = np.polyfit(daily_counts['day_num'], daily_counts['count'], 1)
    slope, intercept = coefficients

    # Prever próximos dias
    last_day = daily_counts['day_num'].max()
    future_days = list(range(last_day + 1, last_day + days_ahead + 1))
    predictions = [slope * day + intercept for day in future_days]

    # Datas futuras
    last_date = daily_counts['date'].max()
    future_dates = [last_date + timedelta(days=i+1) for i in range(days_ahead)]

    prediction_data = {
        'dates': future_dates,
        'predicted_tags': [max(0, int(pred)) for pred in predictions],
        'trend': 'crescente' if slope > 0 else 'decrescente' if slope < 0 else 'estável',
        'slope': slope
    }

    return prediction_data

# ==================== HEADER COM BOTÕES 3D ====================
def show_header():
    """Header com botões que saem da tela ao clicar"""
    current_page = st.session_state.get('current_page', 'Explorar Obras')

    obras_class = "active" if current_page == "Explorar Obras" else ""
    admin_class = "active" if current_page == "Área Administrativa" else ""

    st.markdown(f"""
    <div class='top-navbar'>
        <div class='navbar-logo'>🎨 Folksonomia Digital</div>
        <div class='navbar-buttons'>
            <button class='nav-btn {obras_class}' id='btn-obras'>
                📚 Explorar Obras
            </button>
            <button class='nav-btn {admin_class}' id='btn-admin'>
                ⚙️ Área Admin
            </button>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Botões invisíveis para navegação
    col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 1])

    with col2:
        if st.button("📚 Obras", key="nav_obras", help="Explorar Obras"):
            st.session_state['current_page'] = "Explorar Obras"
            st.rerun()

    with col4:
        if st.button("⚙️ Admin", key="nav_admin", help="Área Administrativa"):
            st.session_state['current_page'] = "Área Administrativa"
            st.rerun()

# ==================== INTERFACE PRINCIPAL ====================

def main():
    load_custom_css()

    try:
        check_and_init_admin()
    except Exception as e:
        st.error(f"Erro: {e}")

    # Inicializar estado da sessão
    if 'user_id' not in st.session_state:
        st.session_state['user_id'] = generate_user_id()
    if 'step' not in st.session_state:
        st.session_state['step'] = 'intro'
    if 'answers' not in st.session_state:
        st.session_state['answers'] = {}
    if 'current_page' not in st.session_state:
        st.session_state['current_page'] = "Explorar Obras"

    # VERIFICAÇÃO CRÍTICA: Só mostra conteúdo após responder questionário
    if st.session_state['step'] != 'completed':
        # BLOQUEIO TOTAL - APENAS QUESTIONÁRIO
        show_intro()
    else:
        # LIBERADO - MOSTRAR NAVEGAÇÃO E CONTEÚDO
        show_header()
        st.markdown("<div class='main-content'>", unsafe_allow_html=True)

        if st.session_state['current_page'] == "Explorar Obras":
            show_obras()
        elif st.session_state['current_page'] == "Área Administrativa":
            show_admin()

        st.markdown("</div>", unsafe_allow_html=True)

# ==================== PÁGINA DE QUESTIONÁRIO ====================

def show_intro():
    """Questionário inicial - BLOQUEIO TOTAL"""
    st.markdown("<div class='main-content'>", unsafe_allow_html=True)

    st.markdown("<h1 class='main-title'>🎨 Bem-vindo ao Projeto Folksonomia Digital</h1>", unsafe_allow_html=True)
    st.markdown("""
    <p class='subtitle'>
        Sistema avançado de catalogação colaborativa de obras de arte.<br>
        Complete o questionário abaixo para acessar a plataforma.
    </p>
    """, unsafe_allow_html=True)

    st.markdown("<div class='dark-blue-card'>", unsafe_allow_html=True)
    st.markdown("<h2 style='color: #60a5fa; margin-bottom: 2rem; text-align: center;'>📋 Questionário de Acesso</h2>", unsafe_allow_html=True)

    with st.form("intro_form"):
        col1, col2 = st.columns([1, 1])

        with col1:
            q1 = st.selectbox(
                "1️⃣ Qual é o seu nível de familiaridade com museus?",
                ["Nunca visito museus", "Visito raramente", "Visito ocasionalmente", "Visito frequentemente"]
            )

            q2 = st.selectbox(
                "2️⃣ Você já ouviu falar sobre documentação museológica?",
                ["Nunca ouvi falar", "Já ouvi, mas não sei o que é", "Tenho uma ideia básica", "Conheço bem o tema"]
            )

        with col2:
            q3 = st.text_area(
                "3️⃣ O que você entende por 'tags' ou etiquetas digitais aplicadas a acervo?",
                max_chars=500,
                height=200,
                placeholder="Descreva sua compreensão sobre o conceito..."
            )

        st.markdown("<br>", unsafe_allow_html=True)

        col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])
        with col_btn2:
            submit = st.form_submit_button("🚀 Acessar Plataforma", use_container_width=True)

        if submit:
            if not q3.strip():
                st.error("❌ Por favor, responda todas as perguntas para continuar!")
            else:
                st.session_state['answers'] = {"q1": q1, "q2": q2, "q3": q3}
                save_user_answers(st.session_state['user_id'], st.session_state['answers'])
                st.session_state['step'] = 'completed'
                st.success("✅ Questionário completo! Acesso liberado.")
                st.balloons()
                st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ==================== PÁGINA DE OBRAS ====================

def show_obras():
    """Galeria de obras - ACESSO RESTRITO"""
    st.markdown("<h1 class='main-title'>📚 Galeria de Obras de Arte</h1>", unsafe_allow_html=True)
    st.markdown("""
    <p class='subtitle'>
        Explore obras clássicas e contemporâneas. Contribua com suas próprias tags para enriquecer nossa base colaborativa.
    </p>
    """, unsafe_allow_html=True)

    obras = load_obras()

    if not obras:
        st.info("🎨 Nenhuma obra cadastrada no momento.")
        return

    # Filtros
    st.markdown("<div class='dark-blue-card'>", unsafe_allow_html=True)
    col_filter1, col_filter2, col_filter3 = st.columns([2, 1, 1])

    with col_filter1:
        search_term = st.text_input("🔍 Buscar obra", "", placeholder="Digite título ou artista...")

    with col_filter2:
        sort_by = st.selectbox("📊 Ordenar por:", ["Título", "Artista", "Ano"])

    with col_filter3:
        view_mode = st.selectbox("👁️ Visualização:", ["Grid", "Lista"])

    st.markdown("</div>", unsafe_allow_html=True)

    # Filtrar e ordenar
    filtered_obras = obras
    if search_term:
        filtered_obras = [
            obra for obra in obras
            if search_term.lower() in obra['titulo'].lower() or
               search_term.lower() in obra['artista'].lower()
        ]

    if sort_by == "Título":
        filtered_obras = sorted(filtered_obras, key=lambda x: x['titulo'])
    elif sort_by == "Artista":
        filtered_obras = sorted(filtered_obras, key=lambda x: x['artista'])
    elif sort_by == "Ano":
        filtered_obras = sorted(filtered_obras, key=lambda x: x['ano'])

    st.markdown(f"""
    <div style='text-align: center; color: #94a3b8; margin: 2rem 0; font-size: 1.1rem;'>
        Exibindo <strong style='color: #60a5fa;'>{len(filtered_obras)}</strong> obra(s)
    </div>
    """, unsafe_allow_html=True)

    # Exibir obras
    if view_mode == "Grid":
        cols = st.columns(3)
        for i, obra in enumerate(filtered_obras):
            with cols[i % 3]:
                st.markdown(f"""
                <div class='obra-card'>
                    <img src='{obra['imagem']}' alt='{obra['titulo']}' />
                    <h3 class='obra-title'>{obra['titulo']}</h3>
                    <p class='obra-info'>👨‍🎨 {obra['artista']}</p>
                    <p class='obra-info'>📅 {obra['ano']}</p>
                </div>
                """, unsafe_allow_html=True)

                if st.button(f"🏷️ Adicionar Tag", key=f"btn_{obra['id']}", use_container_width=True):
                    st.session_state['selected_obra'] = obra
                    st.rerun()

                if 'selected_obra' in st.session_state and st.session_state['selected_obra']['id'] == obra['id']:
                    with st.form(f"tag_form_{obra['id']}"):
                        tag = st.text_input("✨ Sua tag:", key=f"tag_{obra['id']}", placeholder="ex: impressionismo, guerra...")

                        col1, col2 = st.columns(2)
                        with col1:
                            submitted = st.form_submit_button("✅ Enviar", use_container_width=True)
                        with col2:
                            cancel = st.form_submit_button("❌ Cancelar", use_container_width=True)

                        if submitted and tag:
                            save_tag(st.session_state['user_id'], obra['id'], tag)
                            st.success(f"✅ Tag '{tag}' adicionada com sucesso!")
                            del st.session_state['selected_obra']
                            st.rerun()

                        if cancel:
                            del st.session_state['selected_obra']
                            st.rerun()

                    # Tags populares
                    tags = get_tags_for_obra(obra['id'])
                    if not tags.empty:
                        st.markdown("**🏆 Tags Populares:**")
                        tag_html = ""
                        for _, row in tags.head(5).iterrows():
                            tag_html += f"<span class='tag-badge'>{row['tag']} ({row['count']})</span>"
                        st.markdown(tag_html, unsafe_allow_html=True)
                    else:
                        st.info("🌟 Seja o primeiro a adicionar uma tag!")

    else:  # Lista
        for obra in filtered_obras:
            st.markdown("<div class='dark-blue-card'>", unsafe_allow_html=True)
            col_img, col_info = st.columns([1, 2])

            with col_img:
                st.image(obra['imagem'], use_container_width=True)

            with col_info:
                st.markdown(f"### {obra['titulo']}")
                st.markdown(f"**👨‍🎨 Artista:** {obra['artista']}")
                st.markdown(f"**📅 Ano:** {obra['ano']}")

                if st.button(f"🏷️ Adicionar Tag", key=f"btn_list_{obra['id']}"):
                    st.session_state['selected_obra'] = obra
                    st.rerun()

                tags = get_tags_for_obra(obra['id'])
                if not tags.empty:
                    st.markdown("**📌 Tags:**")
                    tag_html = ""
                    for _, row in tags.head(10).iterrows():
                        tag_html += f"<span class='tag-badge'>{row['tag']} ({row['count']})</span>"
                    st.markdown(tag_html, unsafe_allow_html=True)

            st.markdown("</div>", unsafe_allow_html=True)

# ==================== ÁREA ADMINISTRATIVA ULTRA AVANÇADA ====================

def show_admin():
    """Área administrativa com análises profundas"""
    if 'admin_logged_in' not in st.session_state:
        st.session_state['admin_logged_in'] = False

    if not st.session_state['admin_logged_in']:
        # TELA DE LOGIN
        st.markdown("<h1 class='main-title'>⚙️ Área Administrativa</h1>", unsafe_allow_html=True)
        st.markdown("<p class='subtitle'>Acesso restrito - Credenciais necessárias</p>", unsafe_allow_html=True)

        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            st.markdown("<div class='dark-blue-card'>", unsafe_allow_html=True)
            st.markdown("<h2 style='color: #60a5fa; text-align: center; margin-bottom: 2rem;'>🔐 Login Seguro</h2>", unsafe_allow_html=True)

            with st.form("login_form"):
                username = st.text_input("👤 Usuário:", placeholder="Digite o usuário")
                password = st.text_input("🔑 Senha:", type="password", placeholder="Digite a senha")

                st.markdown("<br>", unsafe_allow_html=True)
                submitted = st.form_submit_button("🚀 Entrar no Sistema", use_container_width=True)

                if submitted:
                    if check_admin_credentials(username, password):
                        st.session_state['admin_logged_in'] = True
                        st.session_state['admin_username'] = username
                        st.success("✅ Login realizado com sucesso!")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("❌ Credenciais inválidas. Acesso negado.")

            st.markdown("</div>", unsafe_allow_html=True)

    else:
        # DASHBOARD ADMINISTRATIVO COMPLETO
        st.markdown(f"""
        <h1 class='main-title'>📊 Dashboard Analítico Avançado</h1>
        <p class='subtitle'>Sistema de Análise Profunda | Bem-vindo, <strong style='color: #60a5fa;'>{st.session_state.get('admin_username', 'Admin')}</strong>! 👋</p>
        """, unsafe_allow_html=True)

        admin_tabs = st.tabs([
            "📊 Visão Geral",
            "🔬 Análises Profundas",
            "👥 Segmentação de Usuários",
            "🎯 Qualidade de Dados",
            "⏰ Análise Temporal",
            "🔮 Predições",
            "🖼️ Gestão de Obras",
            "👤 Administradores"
        ])

        with admin_tabs[0]:
            show_overview_dashboard()

        with admin_tabs[1]:
            show_deep_analysis()

        with admin_tabs[2]:
            show_user_segmentation()

        with admin_tabs[3]:
            show_quality_metrics()

        with admin_tabs[4]:
            show_temporal_analysis()

        with admin_tabs[5]:
            show_predictions()

        with admin_tabs[6]:
            show_manage_obras()

        with admin_tabs[7]:
            show_manage_admins()

        st.markdown("<br>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button("🚪 Sair do Sistema", use_container_width=True):
                st.session_state['admin_logged_in'] = False
                if 'admin_username' in st.session_state:
                    del st.session_state['admin_username']
                st.rerun()

def show_overview_dashboard():
    """Visão geral com métricas principais"""
    tags_df = load_all_tags()
    users_df = load_all_users()
    obras = load_obras()

    # Métricas principais
    st.markdown("### 📈 Métricas Principais do Sistema")

    col1, col2, col3, col4 = st.columns(4)

    total_users = len(users_df['user_id'].unique()) if not users_df.empty else 0
    total_tags = len(tags_df) if not tags_df.empty else 0
    unique_tags = len(tags_df['tag'].unique()) if not tags_df.empty else 0
    total_obras = len(obras)

    with col1:
        st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-label'>👥 Usuários</div>
            <div class='metric-value'>{total_users}</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-label'>🏷️ Total Tags</div>
            <div class='metric-value'>{total_tags}</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-label'>✨ Tags Únicas</div>
            <div class='metric-value'>{unique_tags}</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-label'>🎨 Obras</div>
            <div class='metric-value'>{total_obras}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br><br>", unsafe_allow_html=True)

    # Estatísticas detalhadas
    if not tags_df.empty:
        st.markdown("### 📊 Estatísticas Detalhadas")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("<div class='dark-blue-card'>", unsafe_allow_html=True)
            st.markdown("#### 🔝 Top 10 Tags Mais Usadas")
            top_tags = tags_df['tag'].value_counts().head(10).reset_index()
            top_tags.columns = ['Tag', 'Quantidade']
            st.dataframe(top_tags, use_container_width=True, hide_index=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with col2:
            st.markdown("<div class='dark-blue-card'>", unsafe_allow_html=True)
            st.markdown("#### 🎨 Obras Mais Tagueadas")
            obras_tags = tags_df.groupby('

