import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import datetime
import hashlib
import base64
import json
import plotly.express as px
import plotly.graph_objects as go
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
import warnings
warnings.filterwarnings('ignore')

# ==================== CONFIGURAÇÃO ====================
st.set_page_config(
    page_title="Folksonomia Digital Premium",
    layout="wide",
    initial_sidebar_state="collapsed",
    page_icon="🎨"
)

DATA_DIR = "data"
OBRAS_FILE = os.path.join(DATA_DIR, "obras.json")
TAGS_FILE = os.path.join(DATA_DIR, "tags.json")
USERS_FILE = os.path.join(DATA_DIR, "users.json")
ADMIN_FILE = os.path.join(DATA_DIR, "admin.json")
ADMIN_USERNAME = "nugep"
ADMIN_PASSWORD = "nugep123"

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
        except:
            return default_data
    return default_data

def save_json_file(filepath, data):
    ensure_data_dir()
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except:
        return False

# ==================== CSS PREMIUM ====================
def load_premium_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700;900&display=swap');

    * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Poppins', sans-serif !important; }

    /* Background Animado */
    .stApp {
        background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 50%, #0a0e27 100%);
        background-size: 400% 400%;
        animation: gradientWave 15s ease infinite;
    }

    @keyframes gradientWave {
        0%, 100% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
    }

    /* Navbar Premium */
    .top-navbar {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        z-index: 9999;
        background: rgba(10, 14, 39, 0.9);
        backdrop-filter: blur(30px);
        border-bottom: 2px solid rgba(59, 130, 246, 0.3);
        padding: 1.5rem 3rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 10px 50px rgba(0, 0, 0, 0.7);
    }

    .navbar-logo {
        font-size: 2rem;
        font-weight: 900;
        background: linear-gradient(135deg, #3b82f6, #8b5cf6, #ec4899);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        animation: logoFloat 3s ease-in-out infinite;
    }

    @keyframes logoFloat {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-10px); }
    }

    /* Main Content */
    .main-content {
        margin-top: 120px;
        padding: 2rem 3rem;
        max-width: 1800px;
        margin-left: auto;
        margin-right: auto;
    }

    /* Glass Card */
    .glass-card {
        background: rgba(15, 30, 58, 0.7);
        backdrop-filter: blur(20px);
        border: 1px solid rgba(59, 130, 246, 0.3);
        border-radius: 24px;
        padding: 2rem;
        margin: 1.5rem 0;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    }

    .glass-card:hover {
        transform: translateY(-10px);
        box-shadow: 0 20px 60px rgba(59, 130, 246, 0.4);
        border-color: rgba(96, 165, 250, 0.6);
    }

    /* Obra Card 3D Floating */
    .obra-card-premium {
        background: rgba(15, 30, 58, 0.8);
        border: 2px solid rgba(59, 130, 246, 0.4);
        border-radius: 20px;
        overflow: hidden;
        transition: all 0.6s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        cursor: pointer;
        position: relative;
        animation: float 6s ease-in-out infinite;
    }

    @keyframes float {
        0%, 100% { transform: translateY(0) rotateX(0); }
        50% { transform: translateY(-20px) rotateX(5deg); }
    }

    .obra-card-premium:hover {
        transform: translateY(-30px) scale(1.08) rotateY(5deg) !important;
        box-shadow: 0 40px 100px rgba(59, 130, 246, 0.6);
        border-color: rgba(96, 165, 250, 1);
        animation: none;
    }

    .obra-card-premium img {
        width: 100%;
        height: 300px;
        object-fit: cover;
        transition: transform 0.6s ease;
        filter: brightness(0.9);
    }

    .obra-card-premium:hover img {
        transform: scale(1.2) rotate(3deg);
        filter: brightness(1.1) contrast(1.1);
    }

    /* Títulos */
    .main-title {
        color: #e0e7ff;
        font-size: 4rem;
        font-weight: 900;
        text-align: center;
        margin: 2rem 0;
        background: linear-gradient(135deg, #3b82f6, #8b5cf6, #ec4899);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        animation: titlePulse 3s ease-in-out infinite;
    }

    @keyframes titlePulse {
        0%, 100% { transform: scale(1); }
        50% { transform: scale(1.05); }
    }

    .subtitle {
        color: #94a3b8;
        font-size: 1.3rem;
        text-align: center;
        margin-bottom: 3rem;
    }

    /* Tags Modernas */
    .tag-premium {
        display: inline-block;
        background: linear-gradient(135deg, rgba(59, 130, 246, 0.2), rgba(139, 92, 246, 0.2));
        border: 2px solid rgba(59, 130, 246, 0.5);
        color: #93c5fd;
        padding: 0.6rem 1.3rem;
        border-radius: 30px;
        margin: 0.4rem;
        font-size: 0.9rem;
        font-weight: 700;
        transition: all 0.3s ease;
        cursor: pointer;
        position: relative;
        overflow: hidden;
    }

    .tag-premium::before {
        content: '';
        position: absolute;
        top: 50%;
        left: 50%;
        width: 0;
        height: 0;
        border-radius: 50%;
        background: rgba(255, 255, 255, 0.3);
        transform: translate(-50%, -50%);
        transition: width 0.5s, height 0.5s;
    }

    .tag-premium:hover {
        transform: scale(1.2) translateY(-5px);
        box-shadow: 0 10px 30px rgba(59, 130, 246, 0.6);
        border-color: rgba(139, 92, 246, 0.8);
    }

    .tag-premium:hover::before {
        width: 300px;
        height: 300px;
    }

    /* Métricas Premium */
    .metric-premium {
        background: linear-gradient(135deg, #1e40af, #3b82f6, #8b5cf6);
        border: 2px solid rgba(96, 165, 250, 0.5);
        border-radius: 24px;
        padding: 2.5rem;
        text-align: center;
        color: white;
        box-shadow: 0 15px 50px rgba(37, 99, 235, 0.5);
        transition: all 0.4s ease;
        position: relative;
        overflow: hidden;
    }

    .metric-premium::before {
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: radial-gradient(circle, rgba(255,255,255,0.1), transparent);
        animation: rotate 8s linear infinite;
    }

    @keyframes rotate {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }

    .metric-premium:hover {
        transform: translateY(-15px) scale(1.08);
        box-shadow: 0 25px 70px rgba(37, 99, 235, 0.7);
    }

    .metric-value {
        font-size: 4rem;
        font-weight: 900;
        position: relative;
        z-index: 1;
        text-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
    }

    .metric-label {
        font-size: 1.1rem;
        text-transform: uppercase;
        letter-spacing: 2px;
        font-weight: 700;
        position: relative;
        z-index: 1;
    }

    /* Botões Premium */
    .stButton button {
        background: linear-gradient(135deg, #1e40af, #3b82f6) !important;
        color: white !important;
        border: 2px solid #3b82f6 !important;
        border-radius: 16px !important;
        padding: 1rem 3rem !important;
        font-weight: 700 !important;
        font-size: 1.1rem !important;
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275) !important;
        box-shadow: 0 8px 25px rgba(59, 130, 246, 0.4) !important;
        position: relative !important;
        overflow: hidden !important;
    }

    .stButton button::before {
        content: '';
        position: absolute;
        top: 50%;
        left: 50%;
        width: 0;
        height: 0;
        border-radius: 50%;
        background: rgba(255, 255, 255, 0.3);
        transform: translate(-50%, -50%);
        transition: width 0.6s, height 0.6s;
    }

    .stButton button:hover {
        transform: translateY(-10px) scale(1.1) !important;
        box-shadow: 0 20px 50px rgba(59, 130, 246, 0.7) !important;
    }

    .stButton button:hover::before {
        width: 400px;
        height: 400px;
    }

    /* Inputs */
    .stTextInput input, .stTextArea textarea, .stSelectbox select {
        background: rgba(10, 22, 40, 0.9) !important;
        border: 2px solid rgba(59, 130, 246, 0.3) !important;
        color: #e0e7ff !important;
        border-radius: 12px !important;
        padding: 1rem !important;
        transition: all 0.3s ease !important;
    }

    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: #3b82f6 !important;
        box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.2) !important;
        transform: translateY(-3px);
    }

    /* Tabs */
    .stTabs [data-baseweb="tab"] {
        background: rgba(15, 30, 58, 0.6);
        border: 2px solid rgba(59, 130, 246, 0.3);
        border-radius: 16px 16px 0 0;
        color: #94a3b8;
        padding: 1rem 2rem;
        font-weight: 700;
        transition: all 0.3s ease;
    }

    .stTabs [data-baseweb="tab"]:hover {
        transform: translateY(-5px);
        background: rgba(30, 64, 175, 0.5);
    }

    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #1e40af, #3b82f6) !important;
        color: white !important;
        box-shadow: 0 10px 35px rgba(59, 130, 246, 0.5);
    }

    /* Status Badges */
    .status-badge {
        display: inline-block;
        padding: 0.6rem 1.2rem;
        border-radius: 30px;
        font-size: 0.9rem;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    .status-high {
        background: rgba(34, 197, 94, 0.2);
        border: 2px solid rgba(34, 197, 94, 0.6);
        color: #86efac;
        box-shadow: 0 4px 20px rgba(34, 197, 94, 0.4);
    }

    .status-medium {
        background: rgba(251, 191, 36, 0.2);
        border: 2px solid rgba(251, 191, 36, 0.6);
        color: #fcd34d;
        box-shadow: 0 4px 20px rgba(251, 191, 36, 0.4);
    }

    .status-low {
        background: rgba(239, 68, 68, 0.2);
        border: 2px solid rgba(239, 68, 68, 0.6);
        color: #fca5a5;
        box-shadow: 0 4px 20px rgba(239, 68, 68, 0.4);
    }

    /* Hide Streamlit */
    #MainMenu, footer, header {visibility: hidden;}
    .stDeployButton {display: none;}
    [data-testid="stSidebar"] {display: none;}

    /* Responsivo */
    @media (max-width: 768px) {
        .main-title { font-size: 2.5rem; }
        .main-content { margin-top: 140px; padding: 1rem; }
        .metric-value { font-size: 2.5rem; }
    }
    </style>
    """, unsafe_allow_html=True)

# ==================== FUNÇÕES AUXILIARES ====================
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

def save_user_answers(user_id, answers):
    users = load_json_file(USERS_FILE, [])
    users.append({
        "user_id": user_id,
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

def get_tags_for_obra(obra_id):
    tags = load_json_file(TAGS_FILE, [])
    obra_tags = [t for t in tags if t['obra_id'] == obra_id]
    if obra_tags:
        df = pd.DataFrame(obra_tags)
        counts = df['tag'].value_counts().reset_index()
        counts.columns = ["tag", "count"]
        return counts
    return pd.DataFrame(columns=["tag", "count"])

def check_admin_credentials(username, password):
    hashed = hashlib.sha256(password.encode()).hexdigest()
    expected = hashlib.sha256(ADMIN_PASSWORD.encode()).hexdigest()
    return username == ADMIN_USERNAME and hashed == expected

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
    counts = tags_df['tag'].value_counts()
    proportions = counts / counts.sum()
    return -sum(proportions * np.log(proportions + 1e-10))

def calculate_quality_metrics(tags_df):
    if tags_df.empty:
        return None
    metrics = {}
    metrics['specificity'] = len(tags_df['tag'].unique()) / len(tags_df) * 100
    lengths = tags_df['tag'].str.len()
    metrics['consistency'] = 100 - (lengths.std() / lengths.mean() * 100) if lengths.mean() > 0 else 0
    per_obra = tags_df.groupby('obra_id').size()
    metrics['completeness'] = (per_obra >= 3).sum() / len(per_obra) * 100 if len(per_obra) > 0 else 0
    metrics['overall'] = (
        metrics['specificity'] * 0.4 +
        metrics['consistency'] * 0.3 +
        metrics['completeness'] * 0.3
    )
    return metrics

def perform_clustering(tags_df, n_clusters=3):
    """Análise de clustering de tags"""
    if tags_df.empty or len(tags_df['tag'].unique()) < n_clusters:
        return None

    top_tags = tags_df['tag'].value_counts().head(30)
    if len(top_tags) < n_clusters:
        return None

    # Simular clustering por frequência
    tags_sorted = top_tags.sort_values(ascending=False)
    chunk_size = len(tags_sorted) // n_clusters

    clusters = {}
    for i in range(n_clusters):
        start = i * chunk_size
        end = start + chunk_size if i < n_clusters - 1 else len(tags_sorted)
        cluster_tags = tags_sorted.iloc[start:end]
        clusters[f'Grupo {i+1}'] = {
            'tags': cluster_tags.index.tolist(),
            'total': int(cluster_tags.sum()),
            'avg': float(cluster_tags.mean())
        }

    return clusters

# ==================== GRÁFICOS ====================
def create_distribution_chart(tags_df):
    if tags_df.empty:
        return None

    top = tags_df['tag'].value_counts().head(15)

    fig = go.Figure(data=[
        go.Bar(
            x=top.values,
            y=top.index,
            orientation='h',
            marker=dict(
                color=top.values,
                colorscale='Viridis',
                line=dict(color='rgba(59, 130, 246, 0.6)', width=2)
            ),
            text=top.values,
            textposition='outside'
        )
    ])

    fig.update_layout(
        title=dict(text="🏆 Top 15 Tags Mais Utilizadas", font=dict(size=20, color='#e0e7ff')),
        xaxis_title="Frequência",
        yaxis_title="Tag",
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#e0e7ff', size=13),
        height=500,
        margin=dict(l=20, r=20, t=60, b=20)
    )

    return fig

def create_timeline_chart(tags_df):
    if tags_df.empty or 'timestamp' not in tags_df.columns:
        return None

    tags_df['timestamp'] = pd.to_datetime(tags_df['timestamp'])
    tags_df['date'] = tags_df['timestamp'].dt.date
    daily = tags_df.groupby('date').size().reset_index(name='count')

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=daily['date'],
        y=daily['count'],
        mode='lines+markers',
        line=dict(color='#3b82f6', width=3),
        marker=dict(size=10, color='#60a5fa'),
        fill='tozeroy',
        fillcolor='rgba(59, 130, 246, 0.2)'
    ))

    fig.update_layout(
        title=dict(text="📈 Evolução Temporal de Tags", font=dict(size=20, color='#e0e7ff')),
        xaxis_title="Data",
        yaxis_title="Quantidade",
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#e0e7ff', size=13),
        height=400,
        hovermode='x unified'
    )

    return fig

def create_clustering_chart(tags_df):
    """Gráfico de clustering"""
    clusters = perform_clustering(tags_df, 3)
    if not clusters:
        return None

    labels = list(clusters.keys())
    values = [clusters[k]['total'] for k in labels]

    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=.4,
        marker=dict(colors=['#3b82f6', '#8b5cf6', '#ec4899'])
    )])

    fig.update_layout(
        title=dict(text="🔬 Análise de Clustering de Tags", font=dict(size=20, color='#e0e7ff')),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#e0e7ff', size=13),
        height=400
    )

    return fig

def create_heatmap(tags_df, obras):
    """Mapa de calor obra x tags"""
    if tags_df.empty:
        return None

    matrix = tags_df.groupby(['obra_id', 'tag']).size().unstack(fill_value=0)

    if len(matrix.columns) > 10:
        top_tags = tags_df['tag'].value_counts().head(10).index
        matrix = matrix[top_tags]

    obras_dict = {o['id']: o['titulo'] for o in obras}
    obra_names = [obras_dict.get(oid, f'Obra {oid}') for oid in matrix.index]

    fig = go.Figure(data=go.Heatmap(
        z=matrix.values,
        x=matrix.columns,
        y=obra_names,
        colorscale='Viridis',
        text=matrix.values,
        texttemplate='%{text}',
        textfont={"size": 11}
    ))

    fig.update_layout(
        title=dict(text="🔥 Mapa de Calor: Tags por Obra", font=dict(size=20, color='#e0e7ff')),
        xaxis_title="Tags",
        yaxis_title="Obras",
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#e0e7ff', size=12),
        height=500
    )

    return fig

# ==================== INTERFACE ====================
def show_header():
    st.markdown("""
    <div class='top-navbar'>
        <div class='navbar-logo'>🎨 Folksonomia Digital Premium</div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 1])
    with col2:
        if st.button("📚 Explorar Obras", key="nav_obras", use_container_width=True):
            st.session_state['current_page'] = "Explorar Obras"
            st.rerun()
    with col4:
        if st.button("⚙️ Área Admin", key="nav_admin", use_container_width=True):
            st.session_state['current_page'] = "Área Administrativa"
            st.rerun()

def main():
    load_premium_css()

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
    st.markdown("<h1 class='main-title'>🎨 Folksonomia Digital Premium</h1>", unsafe_allow_html=True)
    st.markdown("<p class='subtitle'>Sistema avançado de catalogação colaborativa com IA<br>Complete o questionário para acessar</p>", unsafe_allow_html=True)

    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.markdown("<h2 style='color: #60a5fa; text-align: center; margin-bottom: 2rem;'>📋 Questionário de Acesso</h2>", unsafe_allow_html=True)

    with st.form("intro_form"):
        col1, col2 = st.columns([1, 1])
        with col1:
            q1 = st.selectbox("1️⃣ Familiaridade com museus:",
                ["Nunca visito", "Visito raramente", "Visito ocasionalmente", "Visito frequentemente"])
            q2 = st.selectbox("2️⃣ Conhecimento sobre documentação museológica:",
                ["Nunca ouvi falar", "Já ouvi, mas não sei", "Ideia básica", "Conheço bem"])
        with col2:
            q3 = st.text_area("3️⃣ O que são 'tags' digitais para acervo?",
                max_chars=500, height=200, placeholder="Descreva...")

        col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])
        with col_btn2:
            submit = st.form_submit_button("🚀 Acessar Plataforma", use_container_width=True)

        if submit:
            if not q3.strip():
                st.error("❌ Responda todas as perguntas!")
            else:
                st.session_state['answers'] = {"q1": q1, "q2": q2, "q3": q3}
                save_user_answers(st.session_state['user_id'], st.session_state['answers'])
                st.session_state['step'] = 'completed'
                st.success("✅ Acesso liberado!")
                st.balloons()
                st.rerun()

    st.markdown("</div></div>", unsafe_allow_html=True)

def show_obras():
    st.markdown("<h1 class='main-title'>📚 Galeria de Obras Premium</h1>", unsafe_allow_html=True)
    st.markdown("<p class='subtitle'>Explore obras clássicas com tecnologia de ponta • Contribua com tags inteligentes</p>", unsafe_allow_html=True)

    obras = load_obras()
    if not obras:
        st.info("🎨 Nenhuma obra cadastrada")
        return

    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        search = st.text_input("🔍 Buscar", "", placeholder="Título ou artista...")
    with col2:
        sort_by = st.selectbox("📊 Ordenar:", ["Título", "Artista", "Ano"])
    with col3:
        view = st.selectbox("👁️ Visualizar:", ["Grid", "Lista"])
    st.markdown("</div>", unsafe_allow_html=True)

    filtered = obras
    if search:
        filtered = [o for o in obras if search.lower() in o['titulo'].lower() or search.lower() in o['artista'].lower()]

    if sort_by == "Título":
        filtered = sorted(filtered, key=lambda x: x['titulo'])
    elif sort_by == "Artista":
        filtered = sorted(filtered, key=lambda x: x['artista'])
    else:
        filtered = sorted(filtered, key=lambda x: x['ano'])

    st.markdown(f"<div style='text-align: center; color: #94a3b8; margin: 2rem 0; font-size: 1.2rem;'>Exibindo <strong style='color: #60a5fa;'>{len(filtered)}</strong> obra(s)</div>", unsafe_allow_html=True)

    if view == "Grid":
        cols = st.columns(3)
        for i, obra in enumerate(filtered):
            with cols[i % 3]:
                st.markdown(f"""
                <div class='obra-card-premium'>
                    <img src='{obra['imagem']}' alt='{obra['titulo']}' />
                    <div style='padding: 1.5rem;'>
                        <h3 style='color: #e0e7ff; font-size: 1.3rem; font-weight: 800; margin: 0.5rem 0;'>{obra['titulo']}</h3>
                        <p style='color: #94a3b8; font-size: 0.95rem; margin: 0.3rem 0;'>👨‍🎨 {obra['artista']}</p>
                        <p style='color: #94a3b8; font-size: 0.95rem; margin: 0.3rem 0;'>📅 {obra['ano']}</p>
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
                    html = ""
                    for _, row in tags.head(5).iterrows():
                        html += f"<span class='tag-premium'>{row['tag']} ({row['count']})</span>"
                    st.markdown(html, unsafe_allow_html=True)
                else:
                    st.info("🌟 Seja o primeiro!")

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

            with st.form("login"):
                username = st.text_input("👤 Usuário:", placeholder="Digite")
                password = st.text_input("🔑 Senha:", type="password", placeholder="Digite")
                submitted = st.form_submit_button("🚀 Entrar", use_container_width=True)

                if submitted:
                    if check_admin_credentials(username, password):
                        st.session_state['admin_logged_in'] = True
                        st.session_state['admin_username'] = username
                        st.success("✅ Login OK!")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("❌ Credenciais inválidas")

            st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<h1 class='main-title'>📊 Dashboard Analítico Premium</h1><p class='subtitle'>Bem-vindo, <strong style='color: #60a5fa;'>{st.session_state.get('admin_username', 'Admin')}</strong>! 🚀</p>", unsafe_allow_html=True)

        tabs = st.tabs(["📊 Visão Geral", "📈 Gráficos Avançados", "🔬 ML & IA", "🎯 Qualidade", "🖼️ Obras"])

        with tabs[0]:
            show_overview()
        with tabs[1]:
            show_charts()
        with tabs[2]:
            show_ml_analysis()
        with tabs[3]:
            show_quality()
        with tabs[4]:
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

    st.markdown("### 📈 Métricas em Tempo Real")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total_users = len(users_df['user_id'].unique()) if not users_df.empty else 0
        st.markdown(f"""
        <div class='metric-premium'>
            <div class='metric-label'>👥 Usuários</div>
            <div class='metric-value'>{total_users}</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        total_tags = len(tags_df) if not tags_df.empty else 0
        st.markdown(f"""
        <div class='metric-premium'>
            <div class='metric-label'>🏷️ Tags</div>
            <div class='metric-value'>{total_tags}</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        unique = len(tags_df['tag'].unique()) if not tags_df.empty else 0
        st.markdown(f"""
        <div class='metric-premium'>
            <div class='metric-label'>✨ Únicas</div>
            <div class='metric-value'>{unique}</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div class='metric-premium'>
            <div class='metric-label'>🎨 Obras</div>
            <div class='metric-value'>{len(obras)}</div>
        </div>
        """, unsafe_allow_html=True)

    if not tags_df.empty:
        st.markdown("### 📊 Top Statistics")
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
            st.markdown("#### 🔝 Top 10 Tags")
            top = tags_df['tag'].value_counts().head(10).reset_index()
            top.columns = ['Tag', 'Quantidade']
            st.dataframe(top, use_container_width=True, hide_index=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with col2:
            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
            st.markdown("#### 🎨 Obras Mais Tagueadas")
            ot = tags_df.groupby('obra_id').size().reset_index(name='Total')
            od = {o['id']: o['titulo'] for o in obras}
            ot['Obra'] = ot['obra_id'].map(od)
            st.dataframe(ot[['Obra', 'Total']].sort_values('Total', ascending=False).head(10),
                        use_container_width=True, hide_index=True)
            st.markdown("</div>", unsafe_allow_html=True)

def show_charts():
    st.markdown("### 📈 Gráficos Interativos Avançados")
    tags_df = load_all_tags()

    if tags_df.empty:
        st.info("📊 Dados insuficientes")
        return

    col1, col2 = st.columns(2)

    with col1:
        fig1 = create_distribution_chart(tags_df)
        if fig1:
            st.plotly_chart(fig1, use_container_width=True)

    with col2:
        fig2 = create_timeline_chart(tags_df)
        if fig2:
            st.plotly_chart(fig2, use_container_width=True)

    col3, col4 = st.columns(2)

    with col3:
        fig3 = create_clustering_chart(tags_df)
        if fig3:
            st.plotly_chart(fig3, use_container_width=True)

    with col4:
        obras = load_obras()
        fig4 = create_heatmap(tags_df, obras)
        if fig4:
            st.plotly_chart(fig4, use_container_width=True)

def show_ml_analysis():
    st.markdown("### 🔬 Análises de Machine Learning & IA")
    tags_df = load_all_tags()

    if tags_df.empty:
        st.info("📊 Dados insuficientes para análise ML")
        return

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.markdown("#### 🧠 Clustering Inteligente")
        clusters = perform_clustering(tags_df, 3)
        if clusters:
            for name, data in clusters.items():
                st.markdown(f"**{name}** ({data['total']} tags)")
                st.markdown(f"Tags: {', '.join(data['tags'][:5])}")
                st.markdown(f"Média: {data['avg']:.1f}")
                st.divider()
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.markdown("#### 📊 Diversidade (Shannon)")
        diversity = calculate_tag_diversity(tags_df)
        st.metric("Índice de Diversidade", f"{diversity:.3f}")

        if diversity > 2.5:
            st.success("✅ Alta diversidade de tags!")
        elif diversity > 1.5:
            st.warning("⚠️ Diversidade moderada")
        else:
            st.error("❌ Baixa diversidade")
        st.markdown("</div>", unsafe_allow_html=True)

def show_quality():
    st.markdown("### 🎯 Qualidade das Tags")
    tags_df = load_all_tags()

    if tags_df.empty:
        st.info("📊 Sem dados")
        return

    quality = calculate_quality_metrics(tags_df)
    if quality:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        score = quality['overall']
        status = 'status-high' if score >= 70 else 'status-medium' if score >= 50 else 'status-low'
        status_text = 'Excelente' if score >= 70 else 'Bom' if score >= 50 else 'Regular'

        st.markdown(f"""
        <div style='text-align: center; padding: 3rem;'>
            <h1 style='font-size: 5rem; color: #60a5fa; font-weight: 900;'>{score:.1f}</h1>
            <span class='status-badge {status}'>{status_text}</span>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📌 Especificidade", f"{quality['specificity']:.1f}%")
        with col2:
            st.metric("🎯 Consistência", f"{quality['consistency']:.1f}%")
        with col3:
            st.metric("✅ Completude", f"{quality['completeness']:.1f}%")

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
                        st.cache_data.clear()
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
                    st.error("Preencha tudo!")

if __name__ == "__main__":
    main()
