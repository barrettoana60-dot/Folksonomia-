import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import datetime
import hashlib
import base64
import json
from collections import Counter
import re

# ==================== CONFIGURAÇÃO INICIAL ====================
st.set_page_config(
    page_title="Folksonomia Digital | Museus",
    layout="wide",
    initial_sidebar_state="collapsed",
    page_icon="🎨"
)

# ==================== PATHS DOS ARQUIVOS JSON ====================
DATA_DIR = "data"
OBRAS_FILE = os.path.join(DATA_DIR, "obras.json")
TAGS_FILE = os.path.join(DATA_DIR, "tags.json")
USERS_FILE = os.path.join(DATA_DIR, "users.json")
ADMIN_FILE = os.path.join(DATA_DIR, "admin.json")

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

# ==================== CSS ULTRA MODERNO - GLASSMORPHISM ====================
def load_custom_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Playfair+Display:wght@400;600;700&display=swap');

    * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
    }

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Background minimalista */
    .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }

    /* Esconder sidebar padrão */
    [data-testid="stSidebar"] {
        display: none;
    }

    /* Navbar superior com glassmorphism */
    .navbar {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        z-index: 999;
        background: rgba(255, 255, 255, 0.25);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border-bottom: 1px solid rgba(255, 255, 255, 0.3);
        padding: 1rem 2rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.1);
    }

    .navbar-logo {
        font-family: 'Playfair Display', serif;
        font-size: 1.5rem;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    .navbar-buttons {
        display: flex;
        gap: 1rem;
    }

    /* Botões liquid glass */
    .glass-button {
        background: rgba(255, 255, 255, 0.4);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.5);
        border-radius: 12px;
        padding: 0.75rem 1.5rem;
        color: #333;
        font-weight: 500;
        text-decoration: none;
        transition: all 0.3s ease;
        cursor: pointer;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
    }

    .glass-button:hover {
        background: rgba(255, 255, 255, 0.6);
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.15);
    }

    .glass-button.active {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: 1px solid transparent;
    }

    /* Container principal */
    .main-content {
        margin-top: 100px;
        padding: 2rem;
        max-width: 1400px;
        margin-left: auto;
        margin-right: auto;
    }

    /* Cards com glassmorphism */
    .glass-card {
        background: rgba(255, 255, 255, 0.7);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border-radius: 20px;
        padding: 2rem;
        border: 1px solid rgba(255, 255, 255, 0.3);
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.1);
        transition: all 0.3s ease;
    }

    .glass-card:hover {
        box-shadow: 0 12px 40px 0 rgba(31, 38, 135, 0.15);
        transform: translateY(-5px);
    }

    /* Título principal */
    .main-title {
        font-family: 'Playfair Display', serif;
        font-size: 3rem;
        font-weight: 700;
        text-align: center;
        margin: 2rem 0;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        animation: fadeIn 1s ease;
    }

    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(-20px); }
        to { opacity: 1; transform: translateY(0); }
    }

    /* Subtítulo */
    .subtitle {
        text-align: center;
        color: #666;
        font-size: 1.1rem;
        margin-bottom: 3rem;
        line-height: 1.6;
    }

    /* Cards de obras */
    .obra-card {
        background: rgba(255, 255, 255, 0.9);
        backdrop-filter: blur(15px);
        border-radius: 20px;
        padding: 1.5rem;
        border: 1px solid rgba(255, 255, 255, 0.4);
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.1);
        transition: all 0.4s cubic-bezier(0.165, 0.84, 0.44, 1);
        overflow: hidden;
    }

    .obra-card:hover {
        transform: translateY(-10px) scale(1.02);
        box-shadow: 0 15px 45px 0 rgba(31, 38, 135, 0.2);
    }

    .obra-card img {
        border-radius: 15px;
        transition: transform 0.4s ease;
        width: 100%;
    }

    .obra-card:hover img {
        transform: scale(1.05);
    }

    .obra-title {
        font-family: 'Playfair Display', serif;
        font-size: 1.3rem;
        font-weight: 600;
        color: #333;
        margin: 1rem 0 0.5rem 0;
    }

    .obra-info {
        color: #666;
        font-size: 0.95rem;
        margin: 0.25rem 0;
    }

    /* Tag badges */
    .tag-badge {
        display: inline-block;
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
        border: 1px solid rgba(102, 126, 234, 0.3);
        color: #667eea;
        padding: 0.4rem 0.8rem;
        border-radius: 20px;
        margin: 0.25rem;
        font-size: 0.85rem;
        font-weight: 500;
        transition: all 0.3s ease;
    }

    .tag-badge:hover {
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.2) 0%, rgba(118, 75, 162, 0.2) 100%);
        transform: scale(1.05);
    }

    /* Métricas */
    .metric-card {
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.9) 0%, rgba(118, 75, 162, 0.9) 100%);
        backdrop-filter: blur(10px);
        border-radius: 15px;
        padding: 2rem;
        color: white;
        text-align: center;
        transition: all 0.3s ease;
        border: 1px solid rgba(255, 255, 255, 0.2);
    }

    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 30px rgba(102, 126, 234, 0.3);
    }

    .metric-value {
        font-size: 2.5rem;
        font-weight: 700;
        margin: 0.5rem 0;
    }

    .metric-label {
        font-size: 0.9rem;
        opacity: 0.9;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-weight: 500;
    }

    /* Botões do Streamlit customizados */
    .stButton button {
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.9) 0%, rgba(118, 75, 162, 0.9) 100%);
        backdrop-filter: blur(10px);
        color: white;
        border-radius: 12px;
        padding: 0.75rem 2rem;
        border: 1px solid rgba(255, 255, 255, 0.2);
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
    }

    .stButton button:hover {
        transform: translateY(-3px);
        box-shadow: 0 6px 25px rgba(102, 126, 234, 0.4);
        background: linear-gradient(135deg, rgba(102, 126, 234, 1) 0%, rgba(118, 75, 162, 1) 100%);
    }

    /* Inputs modernos */
    .stTextInput input, .stTextArea textarea, .stSelectbox select {
        background: rgba(255, 255, 255, 0.9);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(0, 0, 0, 0.1);
        border-radius: 12px;
        padding: 0.75rem;
        transition: all 0.3s ease;
    }

    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
    }

    /* Tabs modernos */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
        background: transparent;
        border-bottom: none;
    }

    .stTabs [data-baseweb="tab"] {
        background: rgba(255, 255, 255, 0.5);
        backdrop-filter: blur(10px);
        border-radius: 12px 12px 0 0;
        padding: 0.75rem 1.5rem;
        border: 1px solid rgba(255, 255, 255, 0.3);
        color: #666;
        font-weight: 500;
    }

    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.9) 0%, rgba(118, 75, 162, 0.9) 100%);
        color: white;
        border: 1px solid rgba(255, 255, 255, 0.2);
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

        .navbar {
            flex-direction: column;
            gap: 1rem;
            padding: 1rem;
        }

        .navbar-buttons {
            width: 100%;
            justify-content: center;
        }

        .main-content {
            margin-top: 150px;
            padding: 1rem;
        }
    }
    </style>
    """, unsafe_allow_html=True)

# ==================== NAVBAR COMPONENT ====================
def show_navbar(current_page):
    """Exibe a navbar superior com glassmorphism"""
    navbar_html = f"""
    <div class='navbar'>
        <div class='navbar-logo'>🎨 Folksonomia Digital</div>
        <div class='navbar-buttons'>
            <a class='glass-button {"active" if current_page == "Explorar Obras" else ""}' 
               onclick='setPage("Explorar Obras")' style='cursor: pointer;'>
                🖼️ Explorar Obras
            </a>
            <a class='glass-button {"active" if current_page == "Área Administrativa" else ""}' 
               onclick='setPage("Área Administrativa")' style='cursor: pointer;'>
                📊 Área Admin
            </a>
        </div>
    </div>
    """
    st.markdown(navbar_html, unsafe_allow_html=True)

    # JavaScript para navegação
    st.markdown("""
    <script>
    function setPage(page) {
        window.parent.postMessage({type: 'streamlit:setComponentValue', value: page}, '*');
    }
    </script>
    """, unsafe_allow_html=True)

# ==================== FUNÇÕES AUXILIARES ====================

def check_and_init_admin():
    """Inicializa administrador padrão"""
    admins = load_json_file(ADMIN_FILE, [])
    if not admins:
        hashed_password = hashlib.sha256("admin123".encode()).hexdigest()
        admins.append({"id": 1, "username": "admin", "password": hashed_password})
        save_json_file(ADMIN_FILE, admins)

def generate_user_id():
    """Gera ID único para usuário"""
    return base64.b64encode(os.urandom(12)).decode('ascii')

@st.cache_data(ttl=5, show_spinner=False)
def load_obras():
    """Carrega obras do arquivo JSON"""
    default_obras = [{
        "id": 1,
        "titulo": "Guernica",
        "artista": "Pablo Picasso",
        "ano": "1937",
        "imagem": "https://upload.wikimedia.org/wikipedia/en/7/74/PicassoGuernica.jpg"
    }]
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
    admins = load_json_file(ADMIN_FILE, [])
    hashed_password = hashlib.sha256(password.encode()).hexdigest()

    for admin in admins:
        if admin['username'] == username and admin['password'] == hashed_password:
            return True
    return False

def load_all_tags():
    """Carrega todas as tags"""
    tags = load_json_file(TAGS_FILE, [])
    return pd.DataFrame(tags) if tags else pd.DataFrame()

def load_all_users():
    """Carrega todos os usuários"""
    users = load_json_file(USERS_FILE, [])
    return pd.DataFrame(users) if users else pd.DataFrame()

def calculate_tag_diversity(tags_df):
    """Calcula diversidade de tags"""
    if tags_df.empty:
        return 0
    tag_counts = tags_df['tag'].value_counts()
    proportions = tag_counts / tag_counts.sum()
    shannon_index = -sum(proportions * np.log(proportions))
    return shannon_index

def analyze_user_engagement(users_df, tags_df):
    """Análise de engajamento"""
    if users_df.empty or tags_df.empty:
        return None

    tags_per_user = tags_df.groupby('user_id').size().reset_index(name='tag_count')

    return {
        'avg_tags_per_user': tags_per_user['tag_count'].mean(),
        'median_tags_per_user': tags_per_user['tag_count'].median(),
        'max_tags_per_user': tags_per_user['tag_count'].max(),
        'total_active_users': len(tags_per_user),
        'total_registered_users': len(users_df)
    }

def get_top_contributors(tags_df, top_n=10):
    """Identifica principais contribuidores"""
    if tags_df.empty:
        return pd.DataFrame()

    contributors = tags_df.groupby('user_id').agg({
        'tag': 'count',
        'timestamp': 'min'
    }).reset_index()

    contributors.columns = ['user_id', 'total_tags', 'first_contribution']
    return contributors.sort_values('total_tags', ascending=False).head(top_n)

def analyze_tag_patterns(tags_df):
    """Analisa padrões nas tags"""
    if tags_df.empty:
        return None

    return {
        'avg_tag_length': tags_df['tag'].str.len().mean(),
        'single_word_tags': sum(tags_df['tag'].str.split().str.len() == 1),
        'multi_word_tags': sum(tags_df['tag'].str.split().str.len() > 1),
        'numeric_tags': sum(tags_df['tag'].str.contains(r'\d', regex=True)),
        'special_char_tags': sum(tags_df['tag'].str.contains(r'[^a-zA-Z0-9\s]', regex=True))
    }

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

    # Verificar se o questionário foi respondido
    if st.session_state['step'] == 'intro':
        show_intro()
    else:
        # Mostrar navbar apenas após questionário
        col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 1])
        with col2:
            if st.button("🖼️ Explorar Obras", use_container_width=True, 
                        type="primary" if st.session_state['current_page'] == "Explorar Obras" else "secondary"):
                st.session_state['current_page'] = "Explorar Obras"
                st.rerun()
        with col4:
            if st.button("📊 Área Admin", use_container_width=True,
                        type="primary" if st.session_state['current_page'] == "Área Administrativa" else "secondary"):
                st.session_state['current_page'] = "Área Administrativa"
                st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)

        # Renderizar página atual
        if st.session_state['current_page'] == "Explorar Obras":
            show_obras()
        elif st.session_state['current_page'] == "Área Administrativa":
            show_admin()

# ==================== PÁGINA INICIAL (QUESTIONÁRIO) ====================

def show_intro():
    st.markdown("<div class='main-content'>", unsafe_allow_html=True)

    st.markdown("<h1 class='main-title'>Folksonomia em Museus</h1>", unsafe_allow_html=True)
    st.markdown("""
    <p class='subtitle'>
        Bem-vindo à nossa plataforma de catalogação colaborativa.<br>
        Contribua com sua percepção para criar uma taxonomia popular de obras de arte.
    </p>
    """, unsafe_allow_html=True)

    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.markdown("<h2 style='text-align: center; margin-bottom: 2rem; color: #333;'>📋 Questionário Inicial</h2>", unsafe_allow_html=True)

    with st.form("intro_form"):
        col1, col2 = st.columns([1, 1])

        with col1:
            q1 = st.selectbox(
                "Qual é o seu nível de familiaridade com museus?",
                ["Nunca visito museus", "Visito raramente", "Visito ocasionalmente", "Visito frequentemente"]
            )

            q2 = st.selectbox(
                "Você já ouviu falar sobre documentação museológica?",
                ["Nunca ouvi falar", "Já ouvi, mas não sei o que é", "Tenho uma ideia básica", "Conheço bem o tema"]
            )

        with col2:
            q3 = st.text_area(
                "O que você entende por 'tags' ou etiquetas digitais aplicadas a acervo?",
                max_chars=500,
                height=200,
                placeholder="Digite sua resposta aqui..."
            )

        st.markdown("<br>", unsafe_allow_html=True)

        col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])
        with col_btn2:
            submit = st.form_submit_button("✨ Começar", use_container_width=True)

        if submit:
            if not q3.strip():
                st.error("Por favor, responda todas as perguntas!")
            else:
                st.session_state['answers'] = {"q1": q1, "q2": q2, "q3": q3}
                save_user_answers(st.session_state['user_id'], st.session_state['answers'])
                st.session_state['step'] = 'completed'
                st.success("✅ Obrigado! Redirecionando...")
                st.balloons()
                st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ==================== PÁGINA DE OBRAS ====================

def show_obras():
    st.markdown("<div class='main-content'>", unsafe_allow_html=True)

    st.markdown("<h1 class='main-title'>Galeria de Obras</h1>", unsafe_allow_html=True)
    st.markdown("""
    <p class='subtitle'>
        Explore as obras e contribua com suas próprias tags para enriquecer nossa base de conhecimento colaborativo.
    </p>
    """, unsafe_allow_html=True)

    obras = load_obras()

    if not obras:
        st.info("Nenhuma obra cadastrada.")
        return

    # Filtros em glass card
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    col_filter1, col_filter2, col_filter3 = st.columns([2, 1, 1])

    with col_filter1:
        search_term = st.text_input("🔍 Buscar obra", "", placeholder="Digite título ou artista...")

    with col_filter2:
        sort_by = st.selectbox("Ordenar por:", ["Título", "Artista", "Ano"])

    with col_filter3:
        view_mode = st.selectbox("Visualização:", ["Grid", "Lista"])

    st.markdown("</div>", unsafe_allow_html=True)

    # Filtrar e ordenar obras
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
    <div style='text-align: center; color: #666; margin: 2rem 0;'>
        <h3>Mostrando {len(filtered_obras)} obra(s)</h3>
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
                        tag = st.text_input("Sua tag:", key=f"tag_{obra['id']}", placeholder="ex: guerra, cubismo...")

                        col1, col2 = st.columns(2)
                        with col1:
                            submitted = st.form_submit_button("✅ Enviar", use_container_width=True)
                        with col2:
                            cancel = st.form_submit_button("❌ Cancelar", use_container_width=True)

                        if submitted and tag:
                            save_tag(st.session_state['user_id'], obra['id'], tag)
                            st.success(f"Tag '{tag}' adicionada! 🎉")
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
                        st.info("Seja o primeiro! 🌟")

    else:  # Lista
        for obra in filtered_obras:
            st.markdown("<div class='glass-card' style='margin-bottom: 1.5rem;'>", unsafe_allow_html=True)
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
                    st.markdown("**Tags:**")
                    tag_html = ""
                    for _, row in tags.head(10).iterrows():
                        tag_html += f"<span class='tag-badge'>{row['tag']} ({row['count']})</span>"
                    st.markdown(tag_html, unsafe_allow_html=True)

            st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

# ==================== ÁREA ADMINISTRATIVA ====================

def show_admin():
    st.markdown("<div class='main-content'>", unsafe_allow_html=True)

    if 'admin_logged_in' not in st.session_state:
        st.session_state['admin_logged_in'] = False

    if not st.session_state['admin_logged_in']:
        st.markdown("<h1 class='main-title'>Área Administrativa</h1>", unsafe_allow_html=True)

        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
            st.markdown("<h2 style='text-align: center; margin-bottom: 2rem;'>🔐 Login</h2>", unsafe_allow_html=True)

            with st.form("login_form"):
                username = st.text_input("👤 Usuário:", placeholder="Digite seu usuário")
                password = st.text_input("🔑 Senha:", type="password", placeholder="Digite sua senha")

                st.markdown("<br>", unsafe_allow_html=True)
                submitted = st.form_submit_button("🚀 Entrar", use_container_width=True)

                if submitted:
                    if check_admin_credentials(username, password):
                        st.session_state['admin_logged_in'] = True
                        st.session_state['admin_username'] = username
                        st.success("Login realizado! 🎉")
                        st.rerun()
                    else:
                        st.error("❌ Credenciais inválidas.")

            st.markdown("</div>", unsafe_allow_html=True)

            with st.expander("ℹ️ Acesso padrão"):
                st.info("**Usuário:** admin\n\n**Senha:** admin123")

    else:
        st.markdown(f"""
        <h1 class='main-title'>Dashboard Administrativo</h1>
        <p class='subtitle'>Bem-vindo, <strong>{st.session_state.get('admin_username', 'Admin')}</strong>! 👋</p>
        """, unsafe_allow_html=True)

        admin_tabs = st.tabs(["📊 Analytics", "🖼️ Obras", "👥 Admins"])

        with admin_tabs[0]:
            show_analytics_dashboard()

        with admin_tabs[1]:
            show_manage_obras()

        with admin_tabs[2]:
            show_manage_admins()

        st.markdown("<br>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button("🚪 Sair", use_container_width=True):
                st.session_state['admin_logged_in'] = False
                if 'admin_username' in st.session_state:
                    del st.session_state['admin_username']
                st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

def show_analytics_dashboard():
    """Dashboard com visualizações nativas"""

    tags_df = load_all_tags()
    users_df = load_all_users()
    obras = load_obras()

    # Métricas
    col1, col2, col3, col4 = st.columns(4)

    total_users = len(users_df['user_id'].unique()) if not users_df.empty else 0
    total_tags = len(tags_df) if not tags_df.empty else 0
    unique_tags = len(tags_df['tag'].unique()) if not tags_df.empty else 0
    total_obras = len(obras)

    with col1:
        st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-label'>Usuários</div>
            <div class='metric-value'>{total_users}</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-label'>Tags</div>
            <div class='metric-value'>{total_tags}</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-label'>Tags Únicas</div>
            <div class='metric-value'>{unique_tags}</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-label'>Obras</div>
            <div class='metric-value'>{total_obras}</div>
        </div>
        """, unsafe_allow_html=True)

    if tags_df.empty:
        st.info("📭 Aguardando dados...")
        return

    st.markdown("<br><br>", unsafe_allow_html=True)

    # Análises
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.markdown("### 📊 Tags Mais Frequentes")
    tag_counts = tags_df['tag'].value_counts().head(20)
    st.bar_chart(tag_counts)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.markdown("### 🎨 Por Obra")
        obra_tags = tags_df.groupby('obra_id').size().reset_index(name='count')
        obra_info = pd.DataFrame(obras)
        merged = obra_info.merge(obra_tags, left_on='id', right_on='obra_id', how='left')
        merged['count'] = merged['count'].fillna(0)
        merged_display = merged[['titulo', 'count']].set_index('titulo')
        st.bar_chart(merged_display)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_chart2:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.markdown("### 📈 Evolução")
        if 'timestamp' in tags_df.columns:
            tags_df['date'] = pd.to_datetime(tags_df['timestamp']).dt.date
            timeline = tags_df.groupby('date').size().reset_index(name='count')
            timeline_display = timeline.set_index('date')
            st.line_chart(timeline_display)
        st.markdown("</div>", unsafe_allow_html=True)

    # Dados brutos
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.markdown("### 📋 Dados Completos")
    all_tags = tags_df['tag'].value_counts().reset_index()
    all_tags.columns = ['Tag', 'Frequência']
    st.dataframe(all_tags, use_container_width=True, height=300)
    st.markdown("</div>", unsafe_allow_html=True)

    # Download
    st.markdown("<br>", unsafe_allow_html=True)
    col_down1, col_down2, col_down3 = st.columns([1, 1, 1])
    with col_down2:
        if not tags_df.empty:
            csv_tags = tags_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Exportar CSV",
                data=csv_tags,
                file_name=f'tags_{datetime.now().strftime("%Y%m%d")}.csv',
                mime='text/csv',
                use_container_width=True
            )

def show_manage_obras():
    """Gerenciar obras"""
    obras = load_obras()

    if obras:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.markdown("### 📚 Obras Cadastradas")
        obras_df = pd.DataFrame(obras)
        st.dataframe(obras_df[["id", "titulo", "artista", "ano"]], use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.markdown("### ➕ Nova Obra")

    with st.form("adicionar_obra"):
        novo_titulo = st.text_input("Título:")
        novo_artista = st.text_input("Artista:")
        novo_ano = st.text_input("Ano:")
        imagem_url = st.text_input("URL da Imagem:")

        if st.form_submit_button("✅ Adicionar", use_container_width=True):
            if novo_titulo and novo_artista and imagem_url:
                novo_id = max([obra["id"] for obra in obras]) + 1 if obras else 1
                nova_obra = {
                    "id": novo_id,
                    "titulo": novo_titulo,
                    "artista": novo_artista,
                    "ano": novo_ano,
                    "imagem": imagem_url
                }
                obras.append(nova_obra)
                save_json_file(OBRAS_FILE, obras)
                st.cache_data.clear()
                st.success("✅ Obra adicionada!")
                st.rerun()
            else:
                st.error("❌ Preencha todos os campos!")

    st.markdown("</div>", unsafe_allow_html=True)

def show_manage_admins():
    """Gerenciar admins"""
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.markdown("### 👥 Administradores")

    admins = load_json_file(ADMIN_FILE, [])
    if admins:
        admins_df = pd.DataFrame(admins)
        st.dataframe(admins_df[["id", "username"]], use_container_width=True)

    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.markdown("### ➕ Novo Admin")

    with st.form("add_admin"):
        new_user = st.text_input("Usuário:")
        new_pass = st.text_input("Senha:", type="password")
        confirm_pass = st.text_input("Confirmar:", type="password")

        if st.form_submit_button("✅ Adicionar", use_container_width=True):
            if new_pass == confirm_pass and len(new_pass) >= 6:
                if not any(a['username'] == new_user for a in admins):
                    hashed = hashlib.sha256(new_pass.encode()).hexdigest()
                    new_id = max([a['id'] for a in admins]) + 1 if admins else 1
                    admins.append({"id": new_id, "username": new_user, "password": hashed})
                    save_json_file(ADMIN_FILE, admins)
                    st.success("✅ Admin adicionado!")
                    st.rerun()
                else:
                    st.error("❌ Usuário já existe!")
            else:
                st.error("❌ Senhas não coincidem ou muito curtas!")

    st.markdown("</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
