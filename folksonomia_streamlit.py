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

# ==================== CSS ====================
def load_custom_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    * { margin: 0; padding: 0; box-sizing: border-box; }
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp {
        background: linear-gradient(135deg, #0a1628 0%, #0f1e3a 50%, #0a1628 100%);
        background-attachment: fixed;
    }
    [data-testid="stSidebar"] { display: none; }
    .top-navbar {
        position: fixed; top: 0; left: 0; right: 0; z-index: 999;
        background: rgba(10, 22, 40, 0.95); backdrop-filter: blur(20px);
        border-bottom: 1px solid rgba(59, 130, 246, 0.2);
        padding: 1rem 2rem; display: flex; justify-content: space-between;
        align-items: center; box-shadow: 0 4px 30px rgba(0, 0, 0, 0.5);
    }
    .navbar-logo {
        font-size: 1.5rem; font-weight: 800;
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    }
    .navbar-buttons { display: flex; gap: 1rem; }
    .nav-btn {
        background: linear-gradient(135deg, #1e3a8a 0%, #1e40af 100%);
        color: #e0e7ff; border: 2px solid #3b82f6; border-radius: 12px;
        padding: 0.75rem 1.5rem; font-size: 0.95rem; font-weight: 600;
        cursor: pointer; transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        position: relative; overflow: hidden; box-shadow: 0 4px 15px rgba(59, 130, 246, 0.3);
    }
    .nav-btn:hover {
        transform: translateY(-5px) scale(1.05);
        box-shadow: 0 10px 30px rgba(59, 130, 246, 0.5);
    }
    .nav-btn.active {
        background: linear-gradient(135deg, #2563eb 0%, #3b82f6 100%);
        border-color: #60a5fa; box-shadow: 0 6px 25px rgba(59, 130, 246, 0.6);
    }
    .main-content {
        margin-top: 100px; padding: 2rem; max-width: 1600px;
        margin-left: auto; margin-right: auto;
    }
    .dark-blue-card {
        background: rgba(15, 30, 58, 0.8); backdrop-filter: blur(15px);
        border: 1px solid rgba(59, 130, 246, 0.3); border-radius: 16px;
        padding: 1.5rem; margin: 1rem 0; box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
        transition: all 0.3s ease;
    }
    .dark-blue-card:hover {
        border-color: rgba(59, 130, 246, 0.6);
        box-shadow: 0 12px 40px rgba(59, 130, 246, 0.3);
        transform: translateY(-3px);
    }
    .obra-card {
        background: rgba(15, 30, 58, 0.9); border: 1px solid rgba(59, 130, 246, 0.3);
        border-radius: 16px; padding: 1rem;
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        position: relative; overflow: hidden; cursor: pointer;
    }
    .obra-card:hover {
        border-color: rgba(96, 165, 250, 0.8);
        transform: translateY(-10px) scale(1.02);
        box-shadow: 0 20px 60px rgba(59, 130, 246, 0.4);
    }
    .obra-card img {
        border-radius: 12px; width: 100%; transition: transform 0.5s ease;
    }
    .obra-card:hover img { transform: scale(1.08) rotate(1deg); }
    .obra-title {
        color: #e0e7ff; font-size: 1.15rem; font-weight: 700;
        margin: 0.75rem 0 0.5rem 0;
    }
    .obra-info { color: #94a3b8; font-size: 0.9rem; margin: 0.25rem 0; }
    .main-title {
        color: #e0e7ff; font-size: 3rem; font-weight: 800; text-align: center;
        margin: 2rem 0 1rem 0;
        background: linear-gradient(135deg, #3b82f6 0%, #60a5fa 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    }
    .subtitle {
        color: #94a3b8; font-size: 1.1rem; text-align: center;
        margin-bottom: 2.5rem; line-height: 1.7;
    }
    .tag-badge {
        display: inline-block; background: rgba(59, 130, 246, 0.2);
        border: 1px solid rgba(59, 130, 246, 0.4); color: #93c5fd;
        padding: 0.4rem 0.9rem; border-radius: 20px; margin: 0.3rem;
        font-size: 0.85rem; font-weight: 600; transition: all 0.3s ease;
        cursor: pointer;
    }
    .tag-badge:hover {
        background: rgba(59, 130, 246, 0.3); border-color: rgba(96, 165, 250, 0.6);
        transform: scale(1.1); box-shadow: 0 4px 15px rgba(59, 130, 246, 0.4);
    }
    .metric-card {
        background: linear-gradient(135deg, #1e40af 0%, #2563eb 100%);
        border: 1px solid rgba(96, 165, 250, 0.3); border-radius: 16px;
        padding: 2rem; text-align: center; color: white;
        box-shadow: 0 8px 30px rgba(37, 99, 235, 0.4);
        transition: all 0.3s ease; position: relative; overflow: hidden;
    }
    .metric-card:hover {
        transform: translateY(-5px); box-shadow: 0 12px 40px rgba(37, 99, 235, 0.6);
    }
    .metric-value {
        font-size: 2.75rem; font-weight: 800; margin: 0.5rem 0;
        position: relative; z-index: 1;
    }
    .metric-label {
        font-size: 0.9rem; opacity: 0.95; text-transform: uppercase;
        letter-spacing: 1.5px; font-weight: 600; position: relative; z-index: 1;
    }
    .stButton button {
        background: linear-gradient(135deg, #1e40af 0%, #2563eb 100%);
        color: white; border: 2px solid #3b82f6; border-radius: 12px;
        padding: 0.75rem 2rem; font-weight: 700; transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(59, 130, 246, 0.3);
    }
    .stButton button:hover {
        transform: translateY(-3px); box-shadow: 0 8px 25px rgba(59, 130, 246, 0.5);
    }
    .stTextInput input, .stTextArea textarea, .stSelectbox select {
        background: rgba(10, 22, 40, 0.9) !important;
        border: 1px solid rgba(59, 130, 246, 0.3) !important;
        color: #e0e7ff !important; border-radius: 10px !important;
        padding: 0.75rem !important; transition: all 0.3s ease !important;
    }
    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: #3b82f6 !important;
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2) !important;
    }
    label {
        color: #cbd5e0 !important; font-weight: 600 !important;
        font-size: 0.95rem !important;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.75rem; background: transparent;
        border-bottom: 2px solid rgba(59, 130, 246, 0.2);
    }
    .stTabs [data-baseweb="tab"] {
        background: rgba(15, 30, 58, 0.6);
        border: 1px solid rgba(59, 130, 246, 0.3);
        border-radius: 12px 12px 0 0; color: #94a3b8;
        padding: 0.85rem 1.75rem; font-weight: 600;
        transition: all 0.3s ease;
    }
    .stTabs [data-baseweb="tab"]:hover {
        background: rgba(30, 64, 175, 0.4); color: #e0e7ff;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #1e40af 0%, #2563eb 100%);
        border-color: #3b82f6; color: white;
        box-shadow: 0 4px 20px rgba(59, 130, 246, 0.4);
    }
    .status-badge {
        display: inline-block; padding: 0.35rem 0.85rem;
        border-radius: 20px; font-size: 0.8rem; font-weight: 700;
        text-transform: uppercase; letter-spacing: 0.5px;
    }
    .status-high {
        background: rgba(34, 197, 94, 0.2);
        border: 1px solid rgba(34, 197, 94, 0.4); color: #86efac;
    }
    .status-medium {
        background: rgba(251, 191, 36, 0.2);
        border: 1px solid rgba(251, 191, 36, 0.4); color: #fcd34d;
    }
    .status-low {
        background: rgba(239, 68, 68, 0.2);
        border: 1px solid rgba(239, 68, 68, 0.4); color: #fca5a5;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display: none;}
    @media (max-width: 768px) {
        .main-title { font-size: 2rem; }
        .top-navbar { flex-direction: column; gap: 1rem; padding: 1rem; }
        .main-content { margin-top: 140px; padding: 1rem; }
        .metric-value { font-size: 2rem; }
    }
    </style>
    """, unsafe_allow_html=True)

# ==================== FUNÇÕES ====================

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

def show_header():
    current_page = st.session_state.get('current_page', 'Explorar Obras')
    obras_class = "active" if current_page == "Explorar Obras" else ""
    admin_class = "active" if current_page == "Área Administrativa" else ""
    st.markdown(f"""
    <div class='top-navbar'>
        <div class='navbar-logo'>🎨 Folksonomia Digital</div>
        <div class='navbar-buttons'>
            <button class='nav-btn {obras_class}'>📚 Explorar Obras</button>
            <button class='nav-btn {admin_class}'>⚙️ Área Admin</button>
        </div>
    </div>
    """, unsafe_allow_html=True)
    col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 1])
    with col2:
        if st.button("📚 Obras", key="nav_obras"):
            st.session_state['current_page'] = "Explorar Obras"
            st.rerun()
    with col4:
        if st.button("⚙️ Admin", key="nav_admin"):
            st.session_state['current_page'] = "Área Administrativa"
            st.rerun()

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
    st.markdown("<div class='dark-blue-card'>", unsafe_allow_html=True)
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
    st.markdown("<div class='dark-blue-card'>", unsafe_allow_html=True)
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
                            tag_html += f"<span class='tag-badge'>{row['tag']} ({row['count']})</span>"
                        st.markdown(tag_html, unsafe_allow_html=True)
                    else:
                        st.info("🌟 Seja o primeiro a adicionar uma tag!")
    else:
        for obra in filtered_obras:
            st.markdown("<div class='dark-blue-card'>", unsafe_allow_html=True)
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
                        tag_html += f"<span class='tag-badge'>{row['tag']} ({row['count']})</span>"
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
                        st.success("✅ Login realizado!")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("❌ Credenciais inválidas.")
            st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<h1 class='main-title'>📊 Dashboard Analítico</h1><p class='subtitle'>Bem-vindo, <strong style='color: #60a5fa;'>{st.session_state.get('admin_username', 'Admin')}</strong>! 👋</p>", unsafe_allow_html=True)
        tabs = st.tabs(["📊 Visão Geral", "🔬 Análises", "🎯 Qualidade", "🖼️ Obras", "👤 Admin"])
        with tabs[0]:
            show_overview()
        with tabs[1]:
            show_analysis()
        with tabs[2]:
            show_quality()
        with tabs[3]:
            show_manage_obras_admin()
        with tabs[4]:
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
        st.markdown(f"<div class='metric-card'><div class='metric-label'>👥 Usuários</div><div class='metric-value'>{len(users_df['user_id'].unique()) if not users_df.empty else 0}</div></div>", unsafe_allow_html=True)
    with col2:
        st.markdown(f"<div class='metric-card'><div class='metric-label'>🏷️ Total Tags</div><div class='metric-value'>{len(tags_df) if not tags_df.empty else 0}</div></div>", unsafe_allow_html=True)
    with col3:
        st.markdown(f"<div class='metric-card'><div class='metric-label'>✨ Tags Únicas</div><div class='metric-value'>{len(tags_df['tag'].unique()) if not tags_df.empty else 0}</div></div>", unsafe_allow_html=True)
    with col4:
        st.markdown(f"<div class='metric-card'><div class='metric-label'>🎨 Obras</div><div class='metric-value'>{len(obras)}</div></div>", unsafe_allow_html=True)
    if not tags_df.empty:
        st.markdown("### 📊 Estatísticas")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("<div class='dark-blue-card'>", unsafe_allow_html=True)
            st.markdown("#### 🔝 Top 10 Tags")
            top_tags = tags_df['tag'].value_counts().head(10).reset_index()
            top_tags.columns = ['Tag', 'Quantidade']
            st.dataframe(top_tags, use_container_width=True, hide_index=True)
            st.markdown("</div>", unsafe_allow_html=True)
        with col2:
            st.markdown("<div class='dark-blue-card'>", unsafe_allow_html=True)
            st.markdown("#### 🎨 Obras Mais Tagueadas")
            obras_tags = tags_df.groupby('obra_id').size().reset_index(name='Total')
            obras_dict = {o['id']: o['titulo'] for o in obras}
            obras_tags['Obra'] = obras_tags['obra_id'].map(obras_dict)
            st.dataframe(obras_tags[['Obra', 'Total']].sort_values('Total', ascending=False).head(10), use_container_width=True, hide_index=True)
            st.markdown("</div>", unsafe_allow_html=True)

def show_analysis():
    st.markdown("### 🔬 Análises Avançadas")
    tags_df = load_all_tags()
    users_df = load_all_users()
    if tags_df.empty:
        st.info("📊 Não há dados suficientes.")
        return
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("<div class='dark-blue-card'>", unsafe_allow_html=True)
        st.markdown("#### 🌈 Diversidade")
        shannon = calculate_tag_diversity(tags_df)
        st.markdown(f"**Índice de Shannon:** `{shannon:.3f}`")
        st.markdown("</div>", unsafe_allow_html=True)
    with col2:
        st.markdown("<div class='dark-blue-card'>", unsafe_allow_html=True)
        st.markdown("#### 📈 Engajamento")
        engagement = analyze_user_engagement(users_df, tags_df)
        if engagement:
            st.markdown(f"**Taxa:** `{engagement['engagement_rate']:.1f}%`")
            st.markdown(f"**Média Tags/User:** `{engagement['avg_tags_per_user']:.2f}`")
        st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<div class='dark-blue-card'>", unsafe_allow_html=True)
    st.markdown("#### 🔍 Padrões")
    patterns = analyze_tag_patterns(tags_df)
    if patterns:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Unicidade", f"{patterns['uniqueness_ratio']:.1f}%")
        with col2:
            st.metric("Tamanho Médio", f"{patterns['avg_tag_length']:.1f}")
        with col3:
            st.metric("Taxa Reuso", f"{patterns['reuse_rate']:.1f}%")
    st.markdown("</div>", unsafe_allow_html=True)

def show_quality():
    st.markdown("### 🎯 Qualidade")
    tags_df = load_all_tags()
    if tags_df.empty:
        st.info("📊 Sem dados.")
        return
    quality = calculate_tag_quality_metrics(tags_df)
    if quality:
        st.markdown("<div class='dark-blue-card'>", unsafe_allow_html=True)
        score = quality['overall_quality_score']
        status = 'status-high' if score >= 70 else 'status-medium' if score >= 50 else 'status-low'
        st.markdown(f"<div style='text-align: center; padding: 2rem;'><h1 style='font-size: 4rem; color: #60a5fa;'>{score:.1f}</h1><span class='status-badge {status}'>{'Excelente' if score >= 70 else 'Bom' if score >= 50 else 'Regular'}</span></div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Especificidade", f"{quality['specificity']:.1f}%")
        with col2:
            st.metric("Consistência", f"{quality['consistency']:.1f}%")
        with col3:
            st.metric("Completude", f"{quality['completeness']:.1f}%")

def show_manage_obras_admin():
    st.markdown("### 🖼️ Gestão de Obras")
    obras = load_obras()
    tab1, tab2 = st.tabs(["📋 Listar", "➕ Adicionar"])
    with tab1:
        if obras:
            for obra in obras:
                col1, col2, col3 = st.columns([1, 2, 1])
                with col1:
                    st.image(obra['imagem'], use_container_width=True)
                with col2:
                    st.markdown(f"**{obra['titulo']}**")
                    st.markdown(f"{obra['artista']} - {obra['ano']}")
                with col3:
                    if st.button("🗑️ Remover", key=f"del_{obra['id']}"):
                        obras.remove(obra)
                        save_json_file(OBRAS_FILE, obras)
                        st.success("Removida!")
                        st.rerun()
                st.divider()
        else:
            st.info("Nenhuma obra")
    with tab2:
        with st.form("add_obra"):
            titulo = st.text_input("Título")
            artista = st.text_input("Artista")
            ano = st.text_input("Ano")
            imagem = st.text_input("URL Imagem")
            if st.form_submit_button("➕ Adicionar"):
                if titulo and artista and ano and imagem:
                    new_id = max([o['id'] for o in obras]) + 1 if obras else 1
                    obras.append({"id": new_id, "titulo": titulo, "artista": artista, "ano": ano, "imagem": imagem})
                    save_json_file(OBRAS_FILE, obras)
                    st.success("✅ Adicionada!")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("Preencha todos os campos!")

def show_admin_info():
    st.markdown("### 👤 Informações")
    st.markdown("<div class='dark-blue-card'>", unsafe_allow_html=True)
    st.markdown(f"**Usuário:** `{st.session_state.get('admin_username', 'N/A')}`")
    st.markdown(f"**Data/Hora:** `{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}`")
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<div class='dark-blue-card'>", unsafe_allow_html=True)
    st.markdown("#### 💾 Exportar Dados")
    tags_df = load_all_tags()
    users_df = load_all_users()
    obras = load_obras()
    col1, col2, col3 = st.columns(3)
    with col1:
        if not users_df.empty:
            csv = users_df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Usuários", csv, "usuarios.csv", "text/csv", use_container_width=True)
    with col2:
        if not tags_df.empty:
            csv = tags_df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Tags", csv, "tags.csv", "text/csv", use_container_width=True)
    with col3:
        if obras:
            csv = pd.DataFrame(obras).to_csv(index=False).encode('utf-8')
            st.download_button("📥 Obras", csv, "obras.csv", "text/csv", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
