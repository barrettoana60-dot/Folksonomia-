import streamlit as st
import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import datetime
import hashlib
import base64
import json
import warnings
warnings.filterwarnings('ignore')

# ==================== CONFIGURAÇÃO ====================
st.set_page_config(
    page_title="Folksonomia",
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

    .stApp {
        background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 50%, #0a0e27 100%);
        background-size: 400% 400%;
        animation: gradientWave 15s ease infinite;
    }

    @keyframes gradientWave {
        0%, 100% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
    }

    .top-navbar {
        position: fixed; top: 0; left: 0; right: 0; z-index: 9999;
        background: rgba(10, 14, 39, 0.9); backdrop-filter: blur(30px);
        border-bottom: 2px solid rgba(59, 130, 246, 0.3);
        padding: 1.5rem 3rem; display: flex;
        justify-content: space-between; align-items: center;
        box-shadow: 0 10px 50px rgba(0, 0, 0, 0.7);
    }

    .navbar-logo {
        font-size: 2rem; font-weight: 900;
        background: linear-gradient(135deg, #3b82f6, #8b5cf6, #ec4899);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        animation: logoFloat 3s ease-in-out infinite;
    }

    @keyframes logoFloat {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-10px); }
    }

    .main-content {
        margin-top: 120px; padding: 2rem 3rem;
        max-width: 1800px; margin-left: auto; margin-right: auto;
    }

    .glass-card {
        background: rgba(15, 30, 58, 0.7); backdrop-filter: blur(20px);
        border: 1px solid rgba(59, 130, 246, 0.3); border-radius: 24px;
        padding: 2rem; margin: 1.5rem 0;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    }

    .glass-card:hover {
        transform: translateY(-10px);
        box-shadow: 0 20px 60px rgba(59, 130, 246, 0.4);
        border-color: rgba(96, 165, 250, 0.6);
    }

    .obra-card-premium {
        background: rgba(15, 30, 58, 0.8);
        border: 2px solid rgba(59, 130, 246, 0.4);
        border-radius: 20px; overflow: hidden;
        transition: all 0.6s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        cursor: pointer; position: relative;
        animation: float 6s ease-in-out infinite;
    }

    @keyframes float {
        0%, 100% { transform: translateY(0) rotateX(0); }
        50% { transform: translateY(-20px) rotateX(5deg); }
    }

    .obra-card-premium:hover {
        transform: translateY(-30px) scale(1.08) rotateY(5deg) !important;
        box-shadow: 0 40px 100px rgba(59, 130, 246, 0.6);
        border-color: rgba(96, 165, 250, 1); animation: none;
    }

    .obra-card-premium img {
        width: 100%; height: 300px; object-fit: cover;
        transition: transform 0.6s ease; filter: brightness(0.9);
    }

    .obra-card-premium:hover img {
        transform: scale(1.2) rotate(3deg);
        filter: brightness(1.1) contrast(1.1);
    }

    .main-title {
        color: #e0e7ff; font-size: 4rem; font-weight: 900;
        text-align: center; margin: 2rem 0;
        background: linear-gradient(135deg, #3b82f6, #8b5cf6, #ec4899);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        animation: titlePulse 3s ease-in-out infinite;
    }

    @keyframes titlePulse {
        0%, 100% { transform: scale(1); }
        50% { transform: scale(1.05); }
    }

    .subtitle {
        color: #94a3b8; font-size: 1.3rem;
        text-align: center; margin-bottom: 3rem;
    }

    .tag-premium {
        display: inline-block;
        background: linear-gradient(135deg, rgba(59, 130, 246, 0.2), rgba(139, 92, 246, 0.2));
        border: 2px solid rgba(59, 130, 246, 0.5); color: #93c5fd;
        padding: 0.6rem 1.3rem; border-radius: 30px; margin: 0.4rem;
        font-size: 0.9rem; font-weight: 700;
        transition: all 0.3s ease; cursor: pointer;
    }

    .tag-premium:hover {
        transform: scale(1.2) translateY(-5px);
        box-shadow: 0 10px 30px rgba(59, 130, 246, 0.6);
    }

    .metric-premium {
        background: linear-gradient(135deg, #1e40af, #3b82f6, #8b5cf6);
        border: 2px solid rgba(96, 165, 250, 0.5);
        border-radius: 24px; padding: 2.5rem;
        text-align: center; color: white;
        box-shadow: 0 15px 50px rgba(37, 99, 235, 0.5);
        transition: all 0.4s ease;
    }

    .metric-premium:hover {
        transform: translateY(-15px) scale(1.08);
        box-shadow: 0 25px 70px rgba(37, 99, 235, 0.7);
    }

    .metric-value {
        font-size: 4rem; font-weight: 900;
        text-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
    }

    .metric-label {
        font-size: 1.1rem; text-transform: uppercase;
        letter-spacing: 2px; font-weight: 700;
    }

    .stButton button {
        background: linear-gradient(135deg, #1e40af, #3b82f6) !important;
        color: white !important; border: 2px solid #3b82f6 !important;
        border-radius: 16px !important; padding: 1rem 3rem !important;
        font-weight: 700 !important; font-size: 1.1rem !important;
        transition: all 0.4s ease !important;
        box-shadow: 0 8px 25px rgba(59, 130, 246, 0.4) !important;
    }

    .stButton button:hover {
        transform: translateY(-10px) scale(1.1) !important;
        box-shadow: 0 20px 50px rgba(59, 130, 246, 0.7) !important;
    }

    .stTextInput input, .stTextArea textarea, .stSelectbox select {
        background: rgba(10, 22, 40, 0.9) !important;
        border: 2px solid rgba(59, 130, 246, 0.3) !important;
        color: #e0e7ff !important; border-radius: 12px !important;
        padding: 1rem !important; transition: all 0.3s ease !important;
    }

    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: #3b82f6 !important;
        box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.2) !important;
    }

    .stTabs [data-baseweb="tab"] {
        background: rgba(15, 30, 58, 0.6);
        border: 2px solid rgba(59, 130, 246, 0.3);
        border-radius: 16px 16px 0 0; color: #94a3b8;
        padding: 1rem 2rem; font-weight: 700;
    }

    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #1e40af, #3b82f6) !important;
        color: white !important;
        box-shadow: 0 10px 35px rgba(59, 130, 246, 0.5);
    }

    .status-badge {
        display: inline-block; padding: 0.6rem 1.2rem;
        border-radius: 30px; font-size: 0.9rem;
        font-weight: 800; text-transform: uppercase;
    }

    .status-high {
        background: rgba(34, 197, 94, 0.2);
        border: 2px solid rgba(34, 197, 94, 0.6);
        color: #86efac;
    }

    .status-medium {
        background: rgba(251, 191, 36, 0.2);
        border: 2px solid rgba(251, 191, 36, 0.6);
        color: #fcd34d;
    }

    .status-low {
        background: rgba(239, 68, 68, 0.2);
        border: 2px solid rgba(239, 68, 68, 0.6);
        color: #fca5a5;
    }

    #MainMenu, footer, header {visibility: hidden;}
    .stDeployButton {display: none;}
    [data-testid="stSidebar"] {display: none;}

    @media (max-width: 768px) {
        .main-title { font-size: 2.5rem; }
        .main-content { margin-top: 140px; padding: 1rem; }
    }
    </style>
    """, unsafe_allow_html=True)

# ==================== FUNÇÕES ====================
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

# ==================== ANÁLISES SIMPLIFICADAS ====================
def calculate_tag_diversity(tags_df):
    """Índice de Shannon para diversidade"""
    if tags_df.empty:
        return 0
    counts = tags_df['tag'].value_counts()
    proportions = counts / counts.sum()
    return -sum(proportions * np.log(proportions + 1e-10))

def calculate_quality_metrics(tags_df):
    """Métricas de qualidade das tags"""
    if tags_df.empty:
        return None

    metrics = {}

    # Especificidade: % de tags únicas
    metrics['specificity'] = len(tags_df['tag'].unique()) / len(tags_df) * 100

    # Consistência: variação no tamanho das tags
    lengths = tags_df['tag'].str.len()
    metrics['consistency'] = 100 - (lengths.std() / lengths.mean() * 100) if lengths.mean() > 0 else 0

    # Completude: obras com pelo menos 3 tags
    per_obra = tags_df.groupby('obra_id').size()
    metrics['completeness'] = (per_obra >= 3).sum() / len(per_obra) * 100 if len(per_obra) > 0 else 0

    # Score geral ponderado
    metrics['overall'] = (
        metrics['specificity'] * 0.4 +
        metrics['consistency'] * 0.3 +
        metrics['completeness'] * 0.3
    )

    return metrics

def simple_clustering(tags_df, n_groups=3):
    """Clustering simples baseado em frequência"""
    if tags_df.empty or len(tags_df['tag'].unique()) < n_groups:
        return None

    top_tags = tags_df['tag'].value_counts().head(30)
    if len(top_tags) < n_groups:
        return None

    # Dividir tags em grupos por frequência
    tags_sorted = top_tags.sort_values(ascending=False)
    chunk_size = len(tags_sorted) // n_groups

    clusters = {}
    for i in range(n_groups):
        start = i * chunk_size
        end = start + chunk_size if i < n_groups - 1 else len(tags_sorted)
        cluster_tags = tags_sorted.iloc[start:end]

        clusters[f'Grupo {i+1}'] = {
            'tags': cluster_tags.index.tolist()[:5],  # Top 5 de cada grupo
            'total': int(cluster_tags.sum()),
            'avg': float(cluster_tags.mean()),
            'size': len(cluster_tags)
        }

    return clusters

def analyze_temporal_patterns(tags_df):
    """Análise temporal de criação de tags"""
    if tags_df.empty or 'timestamp' not in tags_df.columns:
        return None

    try:
        tags_df['timestamp'] = pd.to_datetime(tags_df['timestamp'])
        tags_df['date'] = tags_df['timestamp'].dt.date
        tags_df['hour'] = tags_df['timestamp'].dt.hour

        daily_activity = tags_df.groupby('date').size()
        hourly_activity = tags_df.groupby('hour').size()

        return {
            'total_days': len(daily_activity),
            'avg_per_day': daily_activity.mean(),
            'peak_hour': int(hourly_activity.idxmax()) if not hourly_activity.empty else None,
            'peak_day': str(daily_activity.idxmax()) if not daily_activity.empty else None
        }
    except:
        return None

def analyze_user_engagement(users_df, tags_df):
    """Análise de engajamento dos usuários"""
    if users_df.empty or tags_df.empty:
        return None

    tags_per_user = tags_df.groupby('user_id').size().reset_index(name='tag_count')

    return {
        'total_users': len(users_df),
        'active_users': len(tags_per_user),
        'engagement_rate': (len(tags_per_user) / len(users_df) * 100) if len(users_df) > 0 else 0,
        'avg_tags_per_user': tags_per_user['tag_count'].mean(),
        'median_tags_per_user': tags_per_user['tag_count'].median(),
        'max_tags_user': int(tags_per_user['tag_count'].max()) if not tags_per_user.empty else 0
    }

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
    st.markdown("<p class='subtitle'>Sistema avançado de catalogação colaborativa com análises inteligentes<br>Complete o questionário para acessar</p>", unsafe_allow_html=True)

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
                max_chars=500, height=200, placeholder="Descreva sua compreensão...")

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
                        <h3 style='color: #e0e7ff; font-size: 1.3rem; font-weight: 800;'>{obra['titulo']}</h3>
                        <p style='color: #94a3b8; font-size: 0.95rem;'>👨‍🎨 {obra['artista']}</p>
                        <p style='color: #94a3b8; font-size: 0.95rem;'>📅 {obra['ano']}</p>
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
        st.markdown(f"<h1 class='main-title'>📊 Dashboard Premium</h1><p class='subtitle'>Bem-vindo, <strong style='color: #60a5fa;'>{st.session_state.get('admin_username', 'Admin')}</strong>! 🚀</p>", unsafe_allow_html=True)

        tabs = st.tabs(["📊 Visão Geral", "🔬 Análises Avançadas", "🎯 Qualidade", "📈 Engajamento", "🖼️ Obras"])

        with tabs[0]:
            show_overview()
        with tabs[1]:
            show_advanced_analysis()
        with tabs[2]:
            show_quality()
        with tabs[3]:
            show_engagement()
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

    metrics_data = [
        ("👥 Usuários", len(users_df['user_id'].unique()) if not users_df.empty else 0),
        ("🏷️ Tags", len(tags_df) if not tags_df.empty else 0),
        ("✨ Únicas", len(tags_df['tag'].unique()) if not tags_df.empty else 0),
        ("🎨 Obras", len(obras))
    ]

    for col, (label, value) in zip([col1, col2, col3, col4], metrics_data):
        with col:
            st.markdown(f"""
            <div class='metric-premium'>
                <div class='metric-label'>{label}</div>
                <div class='metric-value'>{value}</div>
            </div>
            """, unsafe_allow_html=True)

    if not tags_df.empty:
        st.markdown("### 📊 Top Rankings")
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
            st.markdown("#### 🔝 Top 15 Tags Mais Utilizadas")
            top = tags_df['tag'].value_counts().head(15).reset_index()
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

def show_advanced_analysis():
    st.markdown("### 🔬 Análises Avançadas com Inteligência")
    tags_df = load_all_tags()

    if tags_df.empty:
        st.info("📊 Dados insuficientes para análise avançada")
        return

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.markdown("#### 🧠 Clustering Inteligente de Tags")
        clusters = simple_clustering(tags_df, 3)
        if clusters:
            for name, data in clusters.items():
                st.markdown(f"**{name}** - {data['size']} tags ({data['total']} usos)")
                st.markdown(f"🏷️ Tags principais: {', '.join(data['tags'])}")
                st.markdown(f"📊 Média de uso: {data['avg']:.1f}")
                st.divider()
        else:
            st.info("Dados insuficientes para clustering")
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.markdown("#### 📊 Índice de Diversidade (Shannon)")
        diversity = calculate_tag_diversity(tags_df)

        # Visual do índice
        st.markdown(f"""
        <div style='text-align: center; padding: 2rem;'>
            <div style='font-size: 3rem; font-weight: 900; color: #60a5fa;'>{diversity:.3f}</div>
            <div style='font-size: 0.9rem; color: #94a3b8; margin-top: 0.5rem;'>ÍNDICE DE SHANNON</div>
        </div>
        """, unsafe_allow_html=True)

        if diversity > 2.5:
            st.success("✅ **Alta diversidade!** As tags são muito variadas.")
        elif diversity > 1.5:
            st.warning("⚠️ **Diversidade moderada.** Há alguma repetição.")
        else:
            st.error("❌ **Baixa diversidade.** Tags muito repetitivas.")

        st.markdown("</div>", unsafe_allow_html=True)

    # Análise Temporal
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.markdown("#### ⏰ Padrões Temporais de Uso")
    temporal = analyze_temporal_patterns(tags_df)
    if temporal:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("📅 Dias Ativos", temporal['total_days'])
        with col2:
            st.metric("📊 Média/Dia", f"{temporal['avg_per_day']:.1f}")
        with col3:
            st.metric("🕐 Hora Pico", f"{temporal['peak_hour']}h" if temporal['peak_hour'] else "N/A")
        with col4:
            st.metric("📆 Dia Pico", temporal['peak_day'] if temporal['peak_day'] else "N/A")
    else:
        st.info("Análise temporal indisponível")
    st.markdown("</div>", unsafe_allow_html=True)

def show_quality():
    st.markdown("### 🎯 Análise de Qualidade das Tags")
    tags_df = load_all_tags()

    if tags_df.empty:
        st.info("📊 Sem dados para análise de qualidade")
        return

    quality = calculate_quality_metrics(tags_df)
    if quality:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        score = quality['overall']
        status = 'status-high' if score >= 70 else 'status-medium' if score >= 50 else 'status-low'
        status_text = 'Excelente' if score >= 70 else 'Bom' if score >= 50 else 'Regular'

        st.markdown(f"""
        <div style='text-align: center; padding: 3rem;'>
            <h1 style='font-size: 5rem; color: #60a5fa; font-weight: 900; margin: 0;'>{score:.1f}</h1>
            <div style='margin: 1rem 0;'>
                <span class='status-badge {status}'>{status_text}</span>
            </div>
            <p style='color: #94a3b8; font-size: 1.1rem; margin-top: 1rem;'>Score Geral de Qualidade</p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("### 📊 Detalhamento das Métricas")
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
            st.markdown("#### 📌 Especificidade")
            st.metric("", f"{quality['specificity']:.1f}%")
            st.markdown("*Proporção de tags únicas no total*")
            st.markdown("</div>", unsafe_allow_html=True)

        with col2:
            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
            st.markdown("#### 🎯 Consistência")
            st.metric("", f"{quality['consistency']:.1f}%")
            st.markdown("*Uniformidade no tamanho das tags*")
            st.markdown("</div>", unsafe_allow_html=True)

        with col3:
            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
            st.markdown("#### ✅ Completude")
            st.metric("", f"{quality['completeness']:.1f}%")
            st.markdown("*Obras com 3+ tags*")
            st.markdown("</div>", unsafe_allow_html=True)

def show_engagement():
    st.markdown("### 📈 Análise de Engajamento dos Usuários")
    tags_df = load_all_tags()
    users_df = load_all_users()

    if tags_df.empty or users_df.empty:
        st.info("📊 Dados insuficientes para análise de engajamento")
        return

    engagement = analyze_user_engagement(users_df, tags_df)

    if engagement:
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
            st.markdown("#### 👥 Taxa de Engajamento")
            st.markdown(f"""
            <div style='text-align: center; padding: 2rem;'>
                <div style='font-size: 3rem; font-weight: 900; color: #60a5fa;'>{engagement['engagement_rate']:.1f}%</div>
                <div style='color: #94a3b8; margin-top: 0.5rem;'>usuários ativos</div>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with col2:
            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
            st.markdown("#### 📊 Média de Tags")
            st.metric("Por Usuário", f"{engagement['avg_tags_per_user']:.1f}")
            st.metric("Mediana", f"{engagement['median_tags_per_user']:.0f}")
            st.markdown("</div>", unsafe_allow_html=True)

        with col3:
            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
            st.markdown("#### 🏆 Recordes")
            st.metric("Usuários Totais", engagement['total_users'])
            st.metric("Usuários Ativos", engagement['active_users'])
            st.metric("Máx Tags/User", engagement['max_tags_user'])
            st.markdown("</div>", unsafe_allow_html=True)

def show_manage_obras():
    st.markdown("### 🖼️ Gestão de Obras")
    obras = load_obras()

    tab1, tab2 = st.tabs(["📋 Listar Obras", "➕ Adicionar Nova Obra"])

    with tab1:
        if obras:
            for obra in obras:
                col1, col2, col3 = st.columns([1, 2, 1])
                with col1:
                    st.image(obra['imagem'], use_container_width=True)
                with col2:
                    st.markdown(f"**{obra['titulo']}**")
                    st.markdown(f"*{obra['artista']} - {obra['ano']}*")
                with col3:
                    if st.button("🗑️ Remover", key=f"del_{obra['id']}"):
                        obras.remove(obra)
                        save_json_file(OBRAS_FILE, obras)
                        st.success("✅ Obra removida!")
                        st.cache_data.clear()
                        st.rerun()
                st.divider()
        else:
            st.info("Nenhuma obra cadastrada")

    with tab2:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        with st.form("add_obra"):
            titulo = st.text_input("📝 Título da Obra")
            artista = st.text_input("👨‍🎨 Nome do Artista")
            ano = st.text_input("📅 Ano de Criação")
            imagem = st.text_input("🖼️ URL da Imagem")

            st.markdown("<br>", unsafe_allow_html=True)
            submitted = st.form_submit_button("➕ Adicionar Obra", use_container_width=True)

            if submitted:
                if titulo and artista and ano and imagem:
                    new_id = max([o['id'] for o in obras]) + 1 if obras else 1
                    obras.append({
                        "id": new_id,
                        "titulo": titulo,
                        "artista": artista,
                        "ano": ano,
                        "imagem": imagem
                    })
                    save_json_file(OBRAS_FILE, obras)
                    st.success("✅ Obra adicionada com sucesso!")
                    st.cache_data.clear()
                    st.balloons()
                    st.rerun()
                else:
                    st.error("❌ Preencha todos os campos!")
        st.markdown("</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
