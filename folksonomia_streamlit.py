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

    .stApp {
        background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 25%, #0f1937 50%, #1e2749 75%, #0a0e27 100%);
        background-size: 400% 400%;
        animation: gradientShift 15s ease infinite;
    }

    @keyframes gradientShift {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }

    [data-testid="stSidebar"] { display: none; }

    .top-navbar {
        position: fixed; top: 0; left: 0; right: 0; z-index: 9999;
        background: rgba(10, 14, 39, 0.85);
        backdrop-filter: blur(30px) saturate(180%);
        border-bottom: 2px solid rgba(59, 130, 246, 0.3);
        padding: 1.2rem 3rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.6);
    }

    .navbar-logo {
        font-size: 1.8rem; font-weight: 900;
        background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 50%, #ec4899 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: 1px;
    }

    .main-content {
        margin-top: 120px;
        padding: 2rem 3rem;
        max-width: 1800px;
        margin-left: auto;
        margin-right: auto;
    }

    .glass-card {
        background: rgba(15, 30, 58, 0.6);
        backdrop-filter: blur(20px) saturate(180%);
        border: 1px solid rgba(59, 130, 246, 0.2);
        border-radius: 24px;
        padding: 2rem;
        margin: 1.5rem 0;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
        transition: all 0.4s ease;
    }

    .glass-card:hover {
        border-color: rgba(96, 165, 250, 0.6);
        box-shadow: 0 20px 60px rgba(59, 130, 246, 0.4);
        transform: translateY(-8px);
    }

    .obra-card-3d {
        background: rgba(15, 30, 58, 0.8);
        border: 2px solid rgba(59, 130, 246, 0.3);
        border-radius: 20px;
        overflow: hidden;
        transition: all 0.5s ease;
        cursor: pointer;
        animation: floatingCard 6s ease-in-out infinite;
    }

    @keyframes floatingCard {
        0%, 100% { transform: translateY(0px); }
        50% { transform: translateY(-15px); }
    }

    .obra-card-3d:hover {
        transform: translateY(-25px) scale(1.05);
        border-color: rgba(96, 165, 250, 0.8);
        box-shadow: 0 30px 80px rgba(59, 130, 246, 0.5);
        animation: none;
    }

    .obra-card-3d img {
        width: 100%;
        height: 300px;
        object-fit: cover;
        transition: transform 0.6s ease;
    }

    .obra-card-3d:hover img {
        transform: scale(1.15);
    }

    .obra-info-box {
        padding: 1.5rem;
    }

    .obra-title {
        color: #e0e7ff;
        font-size: 1.3rem;
        font-weight: 800;
        margin: 0.5rem 0;
    }

    .obra-info {
        color: #94a3b8;
        font-size: 0.95rem;
        margin: 0.3rem 0;
    }

    .main-title {
        color: #e0e7ff;
        font-size: 3.5rem;
        font-weight: 900;
        text-align: center;
        margin: 2rem 0 1rem 0;
        background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 50%, #ec4899 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: 2px;
    }

    .subtitle {
        color: #94a3b8;
        font-size: 1.2rem;
        text-align: center;
        margin-bottom: 3rem;
        line-height: 1.8;
    }

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
    }

    .tag-badge-modern:hover {
        background: linear-gradient(135deg, rgba(59, 130, 246, 0.4) 0%, rgba(139, 92, 246, 0.4) 100%);
        transform: scale(1.15) translateY(-3px);
        box-shadow: 0 8px 25px rgba(59, 130, 246, 0.5);
    }

    .metric-card-premium {
        background: linear-gradient(135deg, #1e40af 0%, #3b82f6 50%, #8b5cf6 100%);
        border: 2px solid rgba(96, 165, 250, 0.4);
        border-radius: 24px;
        padding: 2.5rem;
        text-align: center;
        color: white;
        box-shadow: 0 10px 40px rgba(37, 99, 235, 0.5);
        transition: all 0.4s ease;
    }

    .metric-card-premium:hover {
        transform: translateY(-10px) scale(1.05);
        box-shadow: 0 20px 60px rgba(37, 99, 235, 0.7);
    }

    .metric-value {
        font-size: 3.5rem;
        font-weight: 900;
        margin: 1rem 0;
        text-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
    }

    .metric-label {
        font-size: 1rem;
        text-transform: uppercase;
        letter-spacing: 2px;
        font-weight: 700;
    }

    .stButton button {
        background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%);
        color: white;
        border: 2px solid #3b82f6;
        border-radius: 16px;
        padding: 0.9rem 2.5rem;
        font-weight: 700;
        transition: all 0.4s ease;
        box-shadow: 0 6px 20px rgba(59, 130, 246, 0.4);
    }

    .stButton button:hover {
        transform: translateY(-5px) scale(1.05);
        box-shadow: 0 12px 35px rgba(59, 130, 246, 0.6);
    }

    .stTextInput input, .stTextArea textarea, .stSelectbox select {
        background: rgba(10, 22, 40, 0.9) !important;
        border: 2px solid rgba(59, 130, 246, 0.3) !important;
        color: #e0e7ff !important;
        border-radius: 12px !important;
        padding: 1rem !important;
    }

    label {
        color: #cbd5e0 !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
    }

    .stTabs [data-baseweb="tab"] {
        background: rgba(15, 30, 58, 0.6);
        border: 2px solid rgba(59, 130, 246, 0.3);
        border-radius: 16px 16px 0 0;
        color: #94a3b8;
        padding: 1rem 2rem;
        font-weight: 600;
    }

    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%);
        color: white;
        box-shadow: 0 8px 30px rgba(59, 130, 246, 0.5);
    }

    .status-badge {
        display: inline-block;
        padding: 0.5rem 1rem;
        border-radius: 25px;
        font-size: 0.85rem;
        font-weight: 700;
        text-transform: uppercase;
    }

    .status-high {
        background: rgba(34, 197, 94, 0.2);
        border: 2px solid rgba(34, 197, 94, 0.5);
        color: #86efac;
    }

    .status-medium {
        background: rgba(251, 191, 36, 0.2);
        border: 2px solid rgba(251, 191, 36, 0.5);
        color: #fcd34d;
    }

    .status-low {
        background: rgba(239, 68, 68, 0.2);
        border: 2px solid rgba(239, 68, 68, 0.5);
        color: #fca5a5;
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display: none;}

    @media (max-width: 768px) {
        .main-title { font-size: 2.5rem; }
        .main-content { margin-top: 160px; padding: 1rem; }
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

# ==================== ANÁLISES ====================
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

# ==================== GRÁFICOS ====================
def create_tags_distribution_chart(tags_df):
    if tags_df.empty:
        return None

    top_tags = tags_df['tag'].value_counts().head(15)

    fig = go.Figure(data=[
        go.Bar(
            x=top_tags.values,
            y=top_tags.index,
            orientation='h',
            marker=dict(color=top_tags.values, colorscale='Viridis')
        )
    ])

    fig.update_layout(
        title="🏆 Top 15 Tags Mais Utilizadas",
        xaxis_title="Frequência",
        yaxis_title="Tag",
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#e0e7ff'),
        height=500
    )

    return fig

def create_engagement_timeline_chart(tags_df):
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
        line=dict(color='#3b82f6', width=3),
        fill='tozeroy',
        fillcolor='rgba(59, 130, 246, 0.2)'
    ))

    fig.update_layout(
        title="📈 Evolução Temporal de Tags",
        xaxis_title="Data",
        yaxis_title="Quantidade",
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#e0e7ff'),
        height=400
    )

    return fig

# ==================== HEADER ====================
def show_header():
    current_page = st.session_state.get('current_page', 'Explorar Obras')

    st.markdown(f"""
    <div class='top-navbar'>
        <div class='navbar-logo'>🎨 Folksonomia Digital</div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 1])
    with col2:
        if st.button("📚 Obras", key="nav_obras_btn", use_container_width=True):
            st.session_state['current_page'] = "Explorar Obras"
            st.rerun()
    with col4:
        if st.button("⚙️ Admin", key="nav_admin_btn", use_container_width=True):
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
                max_chars=500, height=200, placeholder="Descreva sua compreensão...")

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

    st.markdown(f"<div style='text-align: center; color: #94a3b8; margin: 2rem 0;'>Exibindo <strong style='color: #60a5fa;'>{len(filtered_obras)}</strong> obra(s)</div>", unsafe_allow_html=True)

    if view_mode == "Grid":
        cols = st.columns(3)
        for i, obra in enumerate(filtered_obras):
            with cols[i % 3]:
                st.markdown(f"""
                <div class='obra-card-3d'>
                    <img src='{obra['imagem']}' alt='{obra['titulo']}' />
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
                        tag = st.text_input("✨ Sua tag:", key=f"tag_{obra['id']}", placeholder="ex: impressionismo...")
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
        st.markdown(f"<h1 class='main-title'>📊 Dashboard Analítico</h1><p class='subtitle'>Bem-vindo, <strong style='color: #60a5fa;'>{st.session_state.get('admin_username', 'Admin')}</strong>! 👋</p>", unsafe_allow_html=True)

        tabs = st.tabs(["📊 Visão Geral", "📈 Gráficos", "🎯 Qualidade", "🖼️ Obras"])

        with tabs[0]:
            show_overview()
        with tabs[1]:
            show_charts()
        with tabs[2]:
            show_quality()
        with tabs[3]:
            show_manage_obras()

        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button("🚪 Sair", use_container_width=True):
                st.session_state['admin_logged_in'] = False
                st.rerun()

def show_overview():
    tags_df = load_all_tags()
    users_df = load_all_users()
    obras = load_obras()

    st.markdown("### 📈 Métricas Principais")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total_users = len(users_df['user_id'].unique()) if not users_df.empty else 0
        st.markdown(f"""
        <div class='metric-card-premium'>
            <div class='metric-label'>👥 Usuários</div>
            <div class='metric-value'>{total_users}</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        total_tags = len(tags_df) if not tags_df.empty else 0
        st.markdown(f"""
        <div class='metric-card-premium'>
            <div class='metric-label'>🏷️ Total Tags</div>
            <div class='metric-value'>{total_tags}</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        unique_tags = len(tags_df['tag'].unique()) if not tags_df.empty else 0
        st.markdown(f"""
        <div class='metric-card-premium'>
            <div class='metric-label'>✨ Tags Únicas</div>
            <div class='metric-value'>{unique_tags}</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div class='metric-card-premium'>
            <div class='metric-label'>🎨 Obras</div>
            <div class='metric-value'>{len(obras)}</div>
        </div>
        """, unsafe_allow_html=True)

    if not tags_df.empty:
        st.markdown("### 📊 Estatísticas")
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
            st.markdown("#### 🔝 Top 10 Tags")
            top_tags = tags_df['tag'].value_counts().head(10).reset_index()
            top_tags.columns = ['Tag', 'Quantidade']
            st.dataframe(top_tags, use_container_width=True, hide_index=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with col2:
            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
            st.markdown("#### 🎨 Obras Mais Tagueadas")
            obras_tags = tags_df.groupby('obra_id').size().reset_index(name='Total')
            obras_dict = {o['id']: o['titulo'] for o in obras}
            obras_tags['Obra'] = obras_tags['obra_id'].map(obras_dict)
            st.dataframe(obras_tags[['Obra', 'Total']].sort_values('Total', ascending=False).head(10), 
                        use_container_width=True, hide_index=True)
            st.markdown("</div>", unsafe_allow_html=True)

def show_charts():
    st.markdown("### 📈 Gráficos Interativos")
    tags_df = load_all_tags()

    if tags_df.empty:
        st.info("📊 Não há dados suficientes para gerar gráficos.")
        return

    col1, col2 = st.columns(2)

    with col1:
        fig1 = create_tags_distribution_chart(tags_df)
        if fig1:
            st.plotly_chart(fig1, use_container_width=True)

    with col2:
        fig2 = create_engagement_timeline_chart(tags_df)
        if fig2:
            st.plotly_chart(fig2, use_container_width=True)

def show_quality():
    st.markdown("### 🎯 Qualidade das Tags")
    tags_df = load_all_tags()

    if tags_df.empty:
        st.info("📊 Sem dados para análise.")
        return

    quality = calculate_tag_quality_metrics(tags_df)
    if quality:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        score = quality['overall_quality_score']
        status = 'status-high' if score >= 70 else 'status-medium' if score >= 50 else 'status-low'
        status_text = 'Excelente' if score >= 70 else 'Bom' if score >= 50 else 'Regular'

        st.markdown(f"""
        <div style='text-align: center; padding: 2rem;'>
            <h1 style='font-size: 4rem; color: #60a5fa;'>{score:.1f}</h1>
            <span class='status-badge {status}'>{status_text}</span>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Especificidade", f"{quality['specificity']:.1f}%")
        with col2:
            st.metric("Consistência", f"{quality['consistency']:.1f}%")
        with col3:
            st.metric("Completude", f"{quality['completeness']:.1f}%")

def show_manage_obras():
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
            st.info("Nenhuma obra cadastrada")

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
                    st.success("✅ Obra adicionada!")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("Preencha todos os campos!")

if __name__ == "__main__":
    main()
