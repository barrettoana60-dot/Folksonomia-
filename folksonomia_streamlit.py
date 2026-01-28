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
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
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
ADMIN_USERNAME = "nugep"
ADMIN_PASSWORD = "nugep123"

# ==================== FUNÇÕES DE ARMAZENAMENTO ====================
def ensure_data_dir():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

def load_json_file(filepath, default_data):
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
    ensure_data_dir()
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar {filepath}: {e}")
        return False

# ==================== CSS ULTRA MODERNO ====================
def load_custom_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800;900&display=swap');

    * { margin: 0; padding: 0; box-sizing: border-box; }
    html, body, [class*="css"] { 
        font-family: 'Poppins', sans-serif !important;
        scroll-behavior: smooth;
    }

    /* ========== BACKGROUND ANIMADO ========== */
    .stApp {
        background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 25%, #0f1937 50%, #1e2749 75%, #0a0e27 100%);
        background-size: 400% 400%;
        animation: gradientShift 15s ease infinite;
        position: relative;
        overflow-x: hidden;
    }

    @keyframes gradientShift {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }

    /* Particles effect */
    .stApp::before {
        content: '';
        position: fixed;
        top: 0; left: 0; right: 0; bottom: 0;
        background-image: 
            radial-gradient(2px 2px at 20% 30%, rgba(59, 130, 246, 0.3), transparent),
            radial-gradient(2px 2px at 60% 70%, rgba(139, 92, 246, 0.3), transparent),
            radial-gradient(1px 1px at 50% 50%, rgba(96, 165, 250, 0.2), transparent);
        background-size: 200px 200px, 300px 300px, 150px 150px;
        animation: particlesFloat 20s linear infinite;
        pointer-events: none;
        z-index: 1;
    }

    @keyframes particlesFloat {
        from { transform: translateY(0); }
        to { transform: translateY(-100px); }
    }

    [data-testid="stSidebar"] { display: none; }

    /* ========== NAVBAR 3D LEVITANTE ========== */
    .top-navbar {
        position: fixed; top: 0; left: 0; right: 0; z-index: 9999;
        background: rgba(10, 14, 39, 0.85);
        backdrop-filter: blur(30px) saturate(180%);
        border-bottom: 2px solid rgba(59, 130, 246, 0.3);
        padding: 1.2rem 3rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 
            0 10px 40px rgba(0, 0, 0, 0.6),
            0 0 80px rgba(59, 130, 246, 0.1);
    }

    .navbar-logo {
        font-size: 1.8rem;
        font-weight: 900;
        background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 50%, #ec4899 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        text-shadow: 0 0 30px rgba(59, 130, 246, 0.5);
        letter-spacing: 1px;
        animation: logoGlow 3s ease-in-out infinite;
    }

    @keyframes logoGlow {
        0%, 100% { filter: drop-shadow(0 0 10px rgba(59, 130, 246, 0.5)); }
        50% { filter: drop-shadow(0 0 20px rgba(139, 92, 246, 0.8)); }
    }

    .navbar-buttons {
        display: flex;
        gap: 1.5rem;
    }

    /* ========== BOTÕES 3D ULTRA MODERNOS ========== */
    .nav-btn-3d {
        position: relative;
        background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%);
        color: white;
        border: none;
        border-radius: 16px;
        padding: 1rem 2.5rem;
        font-size: 1rem;
        font-weight: 700;
        cursor: pointer;
        overflow: hidden;
        transform-style: preserve-3d;
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        box-shadow: 
            0 10px 30px rgba(59, 130, 246, 0.4),
            0 0 0 2px rgba(59, 130, 246, 0.2),
            inset 0 -5px 20px rgba(0, 0, 0, 0.2);
    }

    .nav-btn-3d::before {
        content: '';
        position: absolute;
        top: 0; left: -100%;
        width: 100%; height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent);
        transition: left 0.5s;
    }

    .nav-btn-3d:hover {
        transform: translateY(-15px) scale(1.1) rotateX(10deg);
        box-shadow: 
            0 25px 60px rgba(59, 130, 246, 0.6),
            0 0 100px rgba(139, 92, 246, 0.4),
            0 0 0 3px rgba(96, 165, 250, 0.4),
            inset 0 -8px 30px rgba(0, 0, 0, 0.3);
    }

    .nav-btn-3d:hover::before {
        left: 100%;
    }

    .nav-btn-3d.active {
        background: linear-gradient(135deg, #8b5cf6 0%, #ec4899 100%);
        box-shadow: 
            0 15px 40px rgba(139, 92, 246, 0.6),
            0 0 80px rgba(236, 72, 153, 0.4);
        animation: pulseActive 2s ease-in-out infinite;
    }

    @keyframes pulseActive {
        0%, 100% { box-shadow: 0 15px 40px rgba(139, 92, 246, 0.6), 0 0 80px rgba(236, 72, 153, 0.4); }
        50% { box-shadow: 0 20px 50px rgba(139, 92, 246, 0.8), 0 0 100px rgba(236, 72, 153, 0.6); }
    }

    /* ========== CONTEÚDO PRINCIPAL ========== */
    .main-content {
        margin-top: 120px;
        padding: 2rem 3rem;
        max-width: 1800px;
        margin-left: auto;
        margin-right: auto;
        position: relative;
        z-index: 2;
    }

    /* ========== CARDS GLASSMORPHISM ========== */
    .glass-card {
        background: rgba(15, 30, 58, 0.6);
        backdrop-filter: blur(20px) saturate(180%);
        border: 1px solid rgba(59, 130, 246, 0.2);
        border-radius: 24px;
        padding: 2rem;
        margin: 1.5rem 0;
        box-shadow: 
            0 8px 32px rgba(0, 0, 0, 0.4),
            0 0 0 1px rgba(255, 255, 255, 0.05) inset;
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        position: relative;
        overflow: hidden;
    }

    .glass-card::before {
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: radial-gradient(circle, rgba(59, 130, 246, 0.1) 0%, transparent 70%);
        opacity: 0;
        transition: opacity 0.4s;
    }

    .glass-card:hover {
        border-color: rgba(96, 165, 250, 0.6);
        box-shadow: 
            0 20px 60px rgba(59, 130, 246, 0.4),
            0 0 100px rgba(139, 92, 246, 0.2),
            0 0 0 1px rgba(255, 255, 255, 0.1) inset;
        transform: translateY(-8px);
    }

    .glass-card:hover::before {
        opacity: 1;
    }

    /* ========== OBRAS COM EFEITO 3D FLOATING ========== */
    .obra-card-3d {
        background: rgba(15, 30, 58, 0.8);
        backdrop-filter: blur(15px);
        border: 2px solid rgba(59, 130, 246, 0.3);
        border-radius: 20px;
        padding: 0;
        overflow: hidden;
        position: relative;
        transform-style: preserve-3d;
        transition: all 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        cursor: pointer;
        animation: floatingCard 6s ease-in-out infinite;
    }

    @keyframes floatingCard {
        0%, 100% { transform: translateY(0px) rotateX(0deg); }
        50% { transform: translateY(-15px) rotateX(2deg); }
    }

    .obra-card-3d:hover {
        transform: translateY(-25px) scale(1.05) rotateX(5deg) rotateY(5deg);
        border-color: rgba(96, 165, 250, 0.8);
        box-shadow: 
            0 30px 80px rgba(59, 130, 246, 0.5),
            0 0 120px rgba(139, 92, 246, 0.3),
            0 0 0 3px rgba(255, 255, 255, 0.1) inset;
        animation: none;
    }

    .obra-image-container {
        position: relative;
        overflow: hidden;
        height: 300px;
    }

    .obra-card-3d img {
        width: 100%;
        height: 100%;
        object-fit: cover;
        transition: transform 0.6s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        filter: brightness(0.9);
    }

    .obra-card-3d:hover img {
        transform: scale(1.15) rotate(2deg);
        filter: brightness(1.1) saturate(1.2);
    }

    .obra-overlay {
        position: absolute;
        top: 0; left: 0; right: 0; bottom: 0;
        background: linear-gradient(180deg, transparent 0%, rgba(0,0,0,0.8) 100%);
        opacity: 0;
        transition: opacity 0.4s;
    }

    .obra-card-3d:hover .obra-overlay {
        opacity: 1;
    }

    .obra-info-box {
        padding: 1.5rem;
        position: relative;
        z-index: 2;
    }

    .obra-title {
        color: #e0e7ff;
        font-size: 1.3rem;
        font-weight: 800;
        margin: 0.5rem 0;
        text-shadow: 0 2px 10px rgba(0, 0, 0, 0.5);
    }

    .obra-info {
        color: #94a3b8;
        font-size: 0.95rem;
        margin: 0.3rem 0;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    /* ========== TÍTULOS ANIMADOS ========== */
    .main-title {
        color: #e0e7ff;
        font-size: 3.5rem;
        font-weight: 900;
        text-align: center;
        margin: 2rem 0 1rem 0;
        background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 50%, #ec4899 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        text-shadow: 0 0 80px rgba(59, 130, 246, 0.5);
        animation: titleFloat 3s ease-in-out infinite;
        letter-spacing: 2px;
    }

    @keyframes titleFloat {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-10px); }
    }

    .subtitle {
        color: #94a3b8;
        font-size: 1.2rem;
        text-align: center;
        margin-bottom: 3rem;
        line-height: 1.8;
        font-weight: 300;
    }

    /* ========== TAGS MODERNAS ========== */
    .tag-badge-modern {
        display: inline-block;
        background: linear-gradient(135deg, rgba(59, 130, 246, 0.2) 0%, rgba(139, 92, 246, 0.2) 100%);
        border: 2px solid rgba(59, 130, 246, 0.4);
        color: #93c5fd;
        padding: 0.6rem 1.2rem;
        border-radius: 25px;
        margin: 0.4rem;
        font-size: 0.9rem;
        font-weight: 600;
        transition: all 0.3s ease;
        cursor: pointer;
        position: relative;
        overflow: hidden;
    }

    .tag-badge-modern::before {
        content: '';
        position: absolute;
        top: 50%; left: 50%;
        width: 0; height: 0;
        border-radius: 50%;
        background: rgba(59, 130, 246, 0.4);
        transform: translate(-50%, -50%);
        transition: width 0.4s, height 0.4s;
    }

    .tag-badge-modern:hover {
        background: linear-gradient(135deg, rgba(59, 130, 246, 0.4) 0%, rgba(139, 92, 246, 0.4) 100%);
        border-color: rgba(96, 165, 250, 0.8);
        transform: scale(1.15) translateY(-3px);
        box-shadow: 0 8px 25px rgba(59, 130, 246, 0.5);
    }

    .tag-badge-modern:hover::before {
        width: 300px;
        height: 300px;
    }

    /* ========== MÉTRICAS ANIMADAS ========== */
    .metric-card-premium {
        background: linear-gradient(135deg, #1e40af 0%, #3b82f6 50%, #8b5cf6 100%);
        border: 2px solid rgba(96, 165, 250, 0.4);
        border-radius: 24px;
        padding: 2.5rem;
        text-align: center;
        color: white;
        box-shadow: 
            0 10px 40px rgba(37, 99, 235, 0.5),
            0 0 80px rgba(139, 92, 246, 0.3);
        transition: all 0.4s ease;
        position: relative;
        overflow: hidden;
    }

    .metric-card-premium::before {
        content: '';
        position: absolute;
        top: -50%; left: -50%;
        width: 200%; height: 200%;
        background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
        animation: rotateGlow 8s linear infinite;
    }

    @keyframes rotateGlow {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }

    .metric-card-premium:hover {
        transform: translateY(-10px) scale(1.05);
        box-shadow: 
            0 20px 60px rgba(37, 99, 235, 0.7),
            0 0 120px rgba(139, 92, 246, 0.5);
    }

    .metric-value {
        font-size: 3.5rem;
        font-weight: 900;
        margin: 1rem 0;
        position: relative;
        z-index: 1;
        text-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        animation: countUp 2s ease-out;
    }

    @keyframes countUp {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .metric-label {
        font-size: 1rem;
        opacity: 0.95;
        text-transform: uppercase;
        letter-spacing: 2px;
        font-weight: 700;
        position: relative;
        z-index: 1;
    }

    /* ========== BOTÕES STREAMLIT CUSTOMIZADOS ========== */
    .stButton button {
        background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%);
        color: white;
        border: 2px solid #3b82f6;
        border-radius: 16px;
        padding: 0.9rem 2.5rem;
        font-weight: 700;
        font-size: 1rem;
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        box-shadow: 0 6px 20px rgba(59, 130, 246, 0.4);
        position: relative;
        overflow: hidden;
    }

    .stButton button::before {
        content: '';
        position: absolute;
        top: 50%; left: 50%;
        width: 0; height: 0;
        border-radius: 50%;
        background: rgba(255, 255, 255, 0.3);
        transform: translate(-50%, -50%);
        transition: width 0.6s, height 0.6s;
    }

    .stButton button:hover {
        transform: translateY(-5px) scale(1.05);
        box-shadow: 0 12px 35px rgba(59, 130, 246, 0.6);
        border-color: #60a5fa;
    }

    .stButton button:hover::before {
        width: 300px;
        height: 300px;
    }

    /* ========== INPUTS MODERNOS ========== */
    .stTextInput input, .stTextArea textarea, .stSelectbox select {
        background: rgba(10, 22, 40, 0.9) !important;
        border: 2px solid rgba(59, 130, 246, 0.3) !important;
        color: #e0e7ff !important;
        border-radius: 12px !important;
        padding: 1rem !important;
        transition: all 0.3s ease !important;
        font-family: 'Poppins', sans-serif !important;
    }

    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: #3b82f6 !important;
        box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.2) !important;
        transform: translateY(-2px);
    }

    label {
        color: #cbd5e0 !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
        margin-bottom: 0.5rem !important;
    }

    /* ========== TABS ESTILIZADAS ========== */
    .stTabs [data-baseweb="tab-list"] {
        gap: 1rem;
        background: transparent;
        border-bottom: 2px solid rgba(59, 130, 246, 0.2);
        padding-bottom: 0;
    }

    .stTabs [data-baseweb="tab"] {
        background: rgba(15, 30, 58, 0.6);
        border: 2px solid rgba(59, 130, 246, 0.3);
        border-radius: 16px 16px 0 0;
        color: #94a3b8;
        padding: 1rem 2rem;
        font-weight: 600;
        transition: all 0.3s ease;
        border-bottom: none;
    }

    .stTabs [data-baseweb="tab"]:hover {
        background: rgba(30, 64, 175, 0.4);
        color: #e0e7ff;
        transform: translateY(-3px);
    }

    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%);
        border-color: #60a5fa;
        color: white;
        box-shadow: 0 8px 30px rgba(59, 130, 246, 0.5);
        transform: translateY(-5px);
    }

    /* ========== STATUS BADGES ========== */
    .status-badge {
        display: inline-block;
        padding: 0.5rem 1rem;
        border-radius: 25px;
        font-size: 0.85rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    .status-high {
        background: rgba(34, 197, 94, 0.2);
        border: 2px solid rgba(34, 197, 94, 0.5);
        color: #86efac;
        box-shadow: 0 4px 15px rgba(34, 197, 94, 0.3);
    }

    .status-medium {
        background: rgba(251, 191, 36, 0.2);
        border: 2px solid rgba(251, 191, 36, 0.5);
        color: #fcd34d;
        box-shadow: 0 4px 15px rgba(251, 191, 36, 0.3);
    }

    .status-low {
        background: rgba(239, 68, 68, 0.2);
        border: 2px solid rgba(239, 68, 68, 0.5);
        color: #fca5a5;
        box-shadow: 0 4px 15px rgba(239, 68, 68, 0.3);
    }

    /* ========== SCROLLBAR ========== */
    ::-webkit-scrollbar {
        width: 12px;
    }

    ::-webkit-scrollbar-track {
        background: rgba(10, 22, 40, 0.5);
    }

    ::-webkit-scrollbar-thumb {
        background: linear-gradient(180deg, #3b82f6 0%, #8b5cf6 100%);
        border-radius: 10px;
    }

    ::-webkit-scrollbar-thumb:hover {
        background: linear-gradient(180deg, #60a5fa 0%, #a78bfa 100%);
    }

    /* ========== LOADING ANIMATION ========== */
    @keyframes spin {
        to { transform: rotate(360deg); }
    }

    .loading-spinner {
        border: 4px solid rgba(59, 130, 246, 0.2);
        border-top-color: #3b82f6;
        border-radius: 50%;
        width: 40px;
        height: 40px;
        animation: spin 1s linear infinite;
    }

    /* ========== HIDE STREAMLIT ELEMENTS ========== */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display: none;}
    header {visibility: hidden;}

    /* ========== RESPONSIVE ========== */
    @media (max-width: 768px) {
        .main-title { font-size: 2.5rem; }
        .top-navbar { 
            flex-direction: column; 
            gap: 1rem; 
            padding: 1rem; 
        }
        .main-content { 
            margin-top: 160px; 
            padding: 1rem; 
        }
        .metric-value { font-size: 2.5rem; }
        .nav-btn-3d {
            padding: 0.8rem 1.5rem;
            font-size: 0.9rem;
        }
    }
    </style>
    """, unsafe_allow_html=True)

# ==================== FUNÇÕES AUXILIARES ====================
def check_and_init_admin():
    admins = load_json_file(ADMIN_FILE, [])
    if not admins:
        hashed_password = hashlib.sha256(ADMIN_PASSWORD.encode()).hexdigest()
        admins.append({"id": 1, "username": ADMIN_USERNAME, "password": hashed_password})
        save_json_file(ADMIN_FILE, admins)

def generate_user_id():
    return base64.b64encode(os.urandom(12)).decode('ascii')

@st.cache_data(ttl=5, show_spinner=False)
def load_obras():
    default_obras = [
        {
            "id": 1, "titulo": "Guernica", "artista": "Pablo Picasso", "ano": "1937",
            "imagem": "https://upload.wikimedia.org/wikipedia/en/7/74/PicassoGuernica.jpg"
        },
        {
            "id": 2, "titulo": "A Noite Estrelada", "artista": "Vincent van Gogh", "ano": "1889",
            "imagem": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ea/Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg/1200px-Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg"
        },
        {
            "id": 3, "titulo": "Mona Lisa", "artista": "Leonardo da Vinci", "ano": "1503",
            "imagem": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ec/Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_retouched.jpg/800px-Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_retouched.jpg"
        }
    ]
    obras = load_json_file(OBRAS_FILE, default_obras)
    if not obras:
        save_json_file(OBRAS_FILE, default_obras)
        return default_obras
    return obras

def save_user_answers(user_id, answers):
    users = load_json_file(USERS_FILE, [])
    new_user = {
        "user_id": user_id,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "q1": answers["q1"], "q2": answers["q2"], "q3": answers["q3"]
    }
    users.append(new_user)
    return save_json_file(USERS_FILE, users)

def save_tag(user_id, obra_id, tag):
    tags = load_json_file(TAGS_FILE, [])
    new_tag = {
        "id": len(tags) + 1, "user_id": user_id, "obra_id": obra_id,
        "tag": tag.lower().strip(),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    tags.append(new_tag)
    st.cache_data.clear()
    return save_json_file(TAGS_FILE, tags)

def get_tags_for_obra(obra_id):
    tags = load_json_file(TAGS_FILE, [])
    obra_tags = [tag for tag in tags if tag['obra_id'] == obra_id]
    if obra_tags:
        tags_df = pd.DataFrame(obra_tags)
        tag_counts = tags_df['tag'].value_counts().reset_index()
        tag_counts.columns = ["tag", "count"]
        return tag_counts
    return pd.DataFrame(columns=["tag", "count"])

def check_admin_credentials(username, password):
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    expected_hash = hashlib.sha256(ADMIN_PASSWORD.encode()).hexdigest()
    return username == ADMIN_USERNAME and hashed_password == expected_hash

def load_all_tags():
    tags = load_json_file(TAGS_FILE, [])
    return pd.DataFrame(tags) if tags else pd.DataFrame()

def load_all_users():
    users = load_json_file(USERS_FILE, [])
    return pd.DataFrame(users) if users else pd.DataFrame()

# ==================== ANÁLISES AVANÇADAS ====================
def calculate_tag_diversity(tags_df):
    if tags_df.empty:
        return 0
    tag_counts = tags_df['tag'].value_counts()
    proportions = tag_counts / tag_counts.sum()
    shannon_index = -sum(proportions * np.log(proportions + 1e-10))
    return shannon_index

def analyze_user_engagement(users_df, tags_df):
    if users_df.empty or tags_df.empty:
        return None
    tags_per_user = tags_df.groupby('user_id').size().reset_index(name='tag_count')
    return {
        'avg_tags_per_user': tags_per_user['tag_count'].mean(),
        'median_tags_per_user': tags_per_user['tag_count'].median(),
        'total_active_users': len(tags_per_user),
        'total_registered_users': len(users_df),
        'engagement_rate': (len(tags_per_user) / len(users_df) * 100) if len(users_df) > 0 else 0
    }

def analyze_tag_patterns(tags_df):
    if tags_df.empty:
        return None
    patterns = {
        'total_tags': len(tags_df),
        'unique_tags': len(tags_df['tag'].unique()),
        'avg_tag_length': tags_df['tag'].str.len().mean(),
    }
    patterns['uniqueness_ratio'] = (patterns['unique_tags'] / patterns['total_tags'] * 100) if patterns['total_tags'] > 0 else 0
    patterns['reuse_rate'] = ((patterns['total_tags'] - patterns['unique_tags']) / patterns['total_tags'] * 100) if patterns['total_tags'] > 0 else 0
    return patterns

def calculate_tag_quality_metrics(tags_df):
    if tags_df.empty:
        return None
    quality_metrics = {}
    quality_metrics['specificity'] = len(tags_df['tag'].unique()) / len(tags_df) * 100
    tag_lengths = tags_df['tag'].str.len()
    quality_metrics['consistency'] = 100 - (tag_lengths.std() / tag_lengths.mean() * 100) if tag_lengths.mean() > 0 else 0
    tags_per_obra = tags_df.groupby('obra_id').size()
    quality_metrics['completeness'] = (tags_per_obra >= 3).sum() / len(tags_per_obra) * 100 if len(tags_per_obra) > 0 else 0
    quality_metrics['overall_quality_score'] = (
        quality_metrics['specificity'] * 0.4 +
        quality_metrics['consistency'] * 0.3 +
        quality_metrics['completeness'] * 0.3
    )
    return quality_metrics

def perform_tag_clustering(tags_df, n_clusters=5):
    """Análise de clustering de tags similares"""
    if tags_df.empty or len(tags_df['tag'].unique()) < n_clusters:
        return None

    tag_counts = tags_df['tag'].value_counts().head(50)
    if len(tag_counts) < n_clusters:
        return None

    # Simulação de clustering baseado em frequência
    tags_sorted = tag_counts.sort_values(ascending=False)
    clusters = {}
    chunk_size = len(tags_sorted) // n_clusters

    for i in range(n_clusters):
        start_idx = i * chunk_size
        end_idx = start_idx + chunk_size if i < n_clusters - 1 else len(tags_sorted)
        cluster_tags = tags_sorted.iloc[start_idx:end_idx]
        clusters[f'Cluster {i+1}'] = {
            'tags': cluster_tags.index.tolist(),
            'total_usage': cluster_tags.sum()
        }

    return clusters

def analyze_temporal_patterns(tags_df):
    """Análise temporal de criação de tags"""
    if tags_df.empty or 'timestamp' not in tags_df.columns:
        return None

    tags_df['timestamp'] = pd.to_datetime(tags_df['timestamp'])
    tags_df['date'] = tags_df['timestamp'].dt.date
    tags_df['hour'] = tags_df['timestamp'].dt.hour

    daily_tags = tags_df.groupby('date').size()
    hourly_tags = tags_df.groupby('hour').size()

    return {
        'daily_activity': daily_tags,
        'hourly_activity': hourly_tags,
        'peak_hour': hourly_tags.idxmax() if not hourly_tags.empty else None,
        'peak_day': daily_tags.idxmax() if not daily_tags.empty else None
    }

# ==================== GRÁFICOS INTERATIVOS ====================
def create_tags_distribution_chart(tags_df):
    """Gráfico de distribuição de tags"""
    if tags_df.empty:
        return None

    top_tags = tags_df['tag'].value_counts().head(15)

    fig = go.Figure(data=[
        go.Bar(
            x=top_tags.values,
            y=top_tags.index,
            orientation='h',
            marker=dict(
                color=top_tags.values,
                colorscale='Viridis',
                line=dict(color='rgba(59, 130, 246, 0.6)', width=2)
            ),
            text=top_tags.values,
            textposition='auto',
        )
    ])

    fig.update_layout(
        title="🏆 Top 15 Tags Mais Utilizadas",
        xaxis_title="Frequência",
        yaxis_title="Tag",
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#e0e7ff', size=12),
        height=500,
        margin=dict(l=20, r=20, t=60, b=20)
    )

    return fig

def create_engagement_timeline_chart(tags_df):
    """Gráfico de linha temporal de engajamento"""
    if tags_df.empty or 'timestamp' not in tags_df.columns:
        return None

    tags_df['timestamp'] = pd.to_datetime(tags_df['timestamp'])
    tags_df['date'] = tags_df['timestamp'].dt.date
    daily_tags = tags_df.groupby('date').size().reset_index(name='count')

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=daily_tags['date'],
        y=daily_tags['count'],
        mode='lines+markers',
        name='Tags Criadas',
        line=dict(color='#3b82f6', width=3),
        marker=dict(size=8, color='#60a5fa', line=dict(color='white', width=2)),
        fill='tozeroy',
        fillcolor='rgba(59, 130, 246, 0.2)'
    ))

    fig.update_layout(
        title="📈 Evolução Temporal de Tags",
        xaxis_title="Data",
        yaxis_title="Quantidade de Tags",
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#e0e7ff', size=12),
        height=400,
        hovermode='x unified'
    )

    return fig

def create_obras_heatmap(tags_df, obras):
    """Mapa de calor de tags por obra"""
    if tags_df.empty:
        return None

    obra_tag_matrix = tags_df.groupby(['obra_id', 'tag']).size().unstack(fill_value=0)

    # Limitar a top 10 tags e obras
    if len(obra_tag_matrix.columns) > 10:
        top_tags = tags_df['tag'].value_counts().head(10).index
        obra_tag_matrix = obra_tag_matrix[top_tags]

    obras_dict = {o['id']: o['titulo'] for o in obras}
    obra_names = [obras_dict.get(obra_id, f'Obra {obra_id}') for obra_id in obra_tag_matrix.index]

    fig = go.Figure(data=go.Heatmap(
        z=obra_tag_matrix.values,
        x=obra_tag_matrix.columns,
        y=obra_names,
        colorscale='Viridis',
        text=obra_tag_matrix.values,
        texttemplate='%{text}',
        textfont={"size": 10},
        colorbar=dict(title="Freq.")
    ))

    fig.update_layout(
        title="🔥 Mapa de Calor: Tags por Obra",
        xaxis_title="Tags",
        yaxis_title="Obras",
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#e0e7ff', size=11),
        height=500
    )

    return fig

def create_user_activity_chart(users_df, tags_df):
    """Gráfico de atividade de usuários"""
    if users_df.empty or tags_df.empty:
        return None

    user_activity = tags_df.groupby('user_id').size().reset_index(name='tags_count')
    user_activity = user_activity.sort_values('tags_count', ascending=False).head(20)

    fig = go.Figure(data=[
        go.Bar(
            x=list(range(1, len(user_activity) + 1)),
            y=user_activity['tags_count'],
            marker=dict(
                color=user_activity['tags_count'],
                colorscale='Blues',
                line=dict(color='rgba(96, 165, 250, 0.6)', width=2)
            ),
            text=user_activity['tags_count'],
            textposition='outside',
        )
    ])

    fig.update_layout(
        title="👥 Top 20 Usuários Mais Ativos",
        xaxis_title="Usuário (Ranking)",
        yaxis_title="Quantidade de Tags",
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#e0e7ff', size=12),
        height=400
    )

    return fig

def create_tag_length_distribution(tags_df):
    """Distribuição do tamanho das tags"""
    if tags_df.empty:
        return None

    tag_lengths = tags_df['tag'].str.len()

    fig = go.Figure(data=[go.Histogram(
        x=tag_lengths,
        nbinsx=20,
        marker=dict(
            color='#8b5cf6',
            line=dict(color='#a78bfa', width=2)
        )
    )])

    fig.update_layout(
        title="📏 Distribuição do Tamanho das Tags",
        xaxis_title="Comprimento (caracteres)",
        yaxis_title="Frequência",
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#e0e7ff', size=12),
        height=350
    )

    return fig

# ==================== HEADER MODERNO ====================
def show_header():
    current_page = st.session_state.get('current_page', 'Explorar Obras')
    obras_class = "active" if current_page == "Explorar Obras" else ""
    admin_class = "active" if current_page == "Área Administrativa" else ""

    st.markdown(f"""
    <div class='top-navbar'>
        <div class='navbar-logo'>🎨 Folksonomia Digital</div>
        <div class='navbar-buttons'>
            <button class='nav-btn-3d {obras_class}' id='nav_obras'>📚 Explorar Obras</button>
            <button class='nav-btn-3d {admin_class}' id='nav_admin'>⚙️ Área Admin</button>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 1])
    with col2:
        if st.button("📚 Obras", key="nav_obras_btn"):
            st.session_state['current_page'] = "Explorar Obras"
            st.rerun()
    with col4:
        if st.button("⚙️ Admin", key="nav_admin_btn"):
            st.session_state['current_page'] = "Área Administrativa"
            st.rerun()

# ==================== MAIN ====================
def main():
    load_custom_css()

    try:
        check_and_init_admin()
    except:
        pass

    if 'user_id' not in st.session_state:
        st.session_state['user_id'] = generate_user_id()
    if 'step' not in st.session_state:
        st.session_state['step'] = 'intro'
    if 'answers' not in st.session_state:
        st.session_state['answers'] = {}
    if 'current_page' not in st.session_state:
        st.session_state['current_page'] = "Explorar Obras"

    if st.session_state['step'] != 'completed':
        show_intro()
    else:
        show_header()
        st.markdown("<div class='main-content'>", unsafe_allow_html=True)

        if st.session_state['current_page'] == "Explorar Obras":
            show_obras()
        elif st.session_state['current_page'] == "Área Administrativa":
            show_admin()

        st.markdown("</div>", unsafe_allow_html=True)

def show_intro():
    st.markdown("<div class='main-content'>", unsafe_allow_html=True)
    st.markdown("<h1 class='main-title'>🎨 Bem-vindo ao Projeto Folksonomia Digital</h1>", unsafe_allow_html=True)
    st.markdown("<p class='subtitle'>Sistema avançado de catalogação colaborativa de obras de arte.<br>Complete o questionário abaixo para acessar a plataforma.</p>", unsafe_allow_html=True)

    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.markdown("<h2 style='color: #60a5fa; margin-bottom: 2rem; text-align: center;'>📋 Questionário de Acesso</h2>", unsafe_allow_html=True)

    with st.form("intro_form"):
        col1, col2 = st.columns([1, 1])
        with col1:
            q1 = st.selectbox("1️⃣ Qual é o seu nível de familiaridade com museus?",
                ["Nunca visito museus", "Visito raramente", "Visito ocasionalmente", "Visito frequentemente"])
            q2 = st.selectbox("2️⃣ Você já ouviu falar sobre documentação museológica?",
                ["Nunca ouvi falar", "Já ouvi, mas não sei o que é", "Tenho uma ideia básica", "Conheço bem o tema"])
        with col2:
            q3 = st.text_area("3️⃣ O que você entende por 'tags' ou etiquetas digitais aplicadas a acervo?",
                max_chars=500, height=200, placeholder="Descreva sua compreensão sobre o conceito...")

        st.markdown("<br>", unsafe_allow_html=True)
        col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])
        with col_btn2:
            submit = st.form_submit_button("🚀 Acessar Plataforma", use_container_width=True)

        if submit:
            if not q3.strip():
                st.error("❌ Por favor, responda todas as perguntas!")
            else:
                st.session_state['answers'] = {"q1": q1, "q2": q2, "q3": q3}
                save_user_answers(st.session_state['user_id'], st.session_state['answers'])
                st.session_state['step'] = 'completed'
                st.success("✅ Acesso liberado!")
                st.balloons()
                st.rerun()

    st.markdown("</div></div>", unsafe_allow_html=True)

def show_obras():
    st.markdown("<h1 class='main-title'>📚 Galeria de Obras de Arte</h1>", unsafe_allow_html=True)
    st.markdown("<p class='subtitle'>Explore obras clássicas e contemporâneas. Contribua com tags para enriquecer nossa base colaborativa.</p>", unsafe_allow_html=True)

    obras = load_obras()
    if not obras:
        st.info("🎨 Nenhuma obra cadastrada.")
        return

    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    col_filter1, col_filter2, col_filter3 = st.columns([2, 1, 1])
    with col_filter1:
        search_term = st.text_input("🔍 Buscar obra", "", placeholder="Digite título ou artista...")
    with col_filter2:
        sort_by = st.selectbox("📊 Ordenar por:", ["Título", "Artista", "Ano"])
    with col_filter3:
        view_mode = st.selectbox("👁️ Visualização:", ["Grid", "Lista"])
    st.markdown("</div>", unsafe_allow_html=True)

    filtered_obras = obras
    if search_term:
        filtered_obras = [o for o in obras if search_term.lower() in o['titulo'].lower() or search_term.lower() in o['artista'].lower()]

    if sort_by == "Título":
        filtered_obras = sorted(filtered_obras, key=lambda x: x['titulo'])
    elif sort_by == "Artista":
        filtered_obras = sorted(filtered_obras, key=lambda x: x['artista'])
    elif sort_by == "Ano":
        filtered_obras = sorted(filtered_obras, key=lambda x: x['ano'])

    st.markdown(f"<div style='text-align: center; color: #94a3b8; margin: 2rem 0; font-size: 1.1rem;'>Exibindo <strong style='color: #60a5fa;'>{len(filtered_obras)}</strong> obra(s)</div>", unsafe_allow_html=True)

    if view_mode == "Grid":
        cols = st.columns(3)
        for i, obra in enumerate(filtered_obras):
            with cols[i % 3]:
                st.markdown(f"""
                <div class='obra-card-3d'>
                    <div class='obra-image-container'>
                        <img src='{obra['imagem']}' alt='{obra['titulo']}' />
                        <div class='obra-overlay'></div>
                    </div>
                    <div class='obra-info-box'>
                        <h3 class='obra-title'>{obra['titulo']}</h3>
                        <p class='obra-info'>👨‍🎨 {obra['artista']}</p>
                        <p class='obra-info'>📅 {obra['ano']}</p>
                    </div>
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
                            st.success(f"✅ Tag '{tag}' adicionada!")
                            del st.session_state['selected_obra']
                            st.rerun()
                        if cancel:
                            del st.session_state['selected_obra']
                            st.rerun()

                tags = get_tags_for_obra(obra['id'])
                if not tags.empty:
                    st.markdown("**🏆 Tags Populares:**")
                    tag_html = ""
                    for _, row in tags.head(5).iterrows():
                        tag_html += f"<span class='tag-badge-modern'>{row['tag']} ({row['count']})</span>"
                    st.markdown(tag_html, unsafe_allow_html=True)
                else:
                    st.info("🌟 Seja o primeiro a adicionar uma tag!")
    else:
        for obra in filtered_obras:
            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
            col_img, col_info = st.columns([1, 2])
            with col_img:
                st.image(obra['imagem'], use_container_width=True)
            with col_info:
                st.markdown(f"### {obra['titulo']}")
                st.markdown(f"**👨‍🎨 Artista:** {obra['artista']}")
                st.markdown(f"**📅 Ano:** {obra['ano']}")
                tags = get_tags_for_obra(obra['id'])
                if not tags.empty:
                    st.markdown("**📌 Tags:**")
                    tag_html = ""
                    for _, row in tags.head(10).iterrows():
                        tag_html += f"<span class='tag-badge-modern'>{row['tag']} ({row['count']})</span>"
                    st.markdown(tag_html, unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

def show_admin():
    if 'admin_logged_in' not in st.session_state:
        st.session_state['admin_logged_in'] = False

    if not st.session_state['admin_logged_in']:
        st.markdown("<h1 class='main-title'>⚙️ Área Administrativa</h1>", unsafe_allow_html=True)
        st.markdown("<p class='subtitle'>Acesso restrito - Credenciais necessárias</p>", unsafe_allow_html=True)

        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
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
                        st.success("✅ Login realizado!")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("❌ Credenciais inválidas.")

            st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<h1 class='main-title'>📊 Dashboard Analítico Premium</h1><p class='subtitle'>Bem-vindo, <strong style='color: #60a5fa;'>{st.session_state.get('admin_username', 'Admin')}</strong>! 👋</p>", unsafe_allow_html=True)

        tabs = st.tabs(["📊 Visão Geral", "🔬 Análises Avançadas", "📈 Gráficos Interativos", "🎯 Qualidade", "🖼️ Obras", "👤 Admin"])

        with tabs[0]:
            show_overview()
        with tabs[1]:
            show_advanced_analysis()
        with tabs[2]:
            show_interactive_charts()
        with tabs[3]:
            show_quality()
        with tabs[4]:
            show_manage_obras_admin()
        with tabs[5]:
            show_admin_info()

        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button("🚪 Sair", use_container_width=True):
                st.session_state['admin_logged_in'] = False
                if 'admin_username' in st.session_state:
                    del st.session_state['admin_username']
                st.rerun()

def show_overview():
    tags_df = load_all_tags()
    users_df = load_all_users()
    obras = load_obras()

    st.markdown("### 📈 Métricas Principais")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f
