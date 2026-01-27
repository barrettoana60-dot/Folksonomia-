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
    page_title="Folksonomia Digital | Museus Interativos",
    layout="wide",
    initial_sidebar_state="expanded",
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

# ==================== CSS MODERNO E ANIMADO ====================
def load_custom_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&family=Playfair+Display:wght@400;700&display=swap');

    * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
    }

    html, body, [class*="css"] {
        font-family: 'Poppins', sans-serif;
    }

    .stApp {
        background: linear-gradient(-45deg, #ee7752, #e73c7e, #23a6d5, #23d5ab);
        background-size: 400% 400%;
        animation: gradient 15s ease infinite;
    }

    @keyframes gradient {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }

    .main-container {
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(10px);
        border-radius: 20px;
        padding: 30px;
        margin: 20px;
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
        border: 1px solid rgba(255, 255, 255, 0.18);
    }

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1e3c72 0%, #2a5298 100%);
        padding-top: 2rem;
    }

    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {
        color: white;
    }

    .obra-card {
        background: white;
        border-radius: 20px;
        padding: 20px;
        margin: 15px 0;
        box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
    }

    .obra-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 15px 40px rgba(0,0,0,0.2);
    }

    .obra-card img {
        transition: transform 0.3s ease;
        border-radius: 15px;
    }

    .obra-card:hover img {
        transform: scale(1.05);
    }

    .gradient-title {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3rem;
        font-weight: 700;
        font-family: 'Playfair Display', serif;
        text-align: center;
        margin: 30px 0;
        animation: fadeInDown 1s ease;
    }

    @keyframes fadeInDown {
        from {
            opacity: 0;
            transform: translateY(-30px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 15px;
        padding: 25px;
        color: white;
        text-align: center;
        transition: all 0.3s ease;
        box-shadow: 0 5px 15px rgba(0,0,0,0.2);
    }

    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 25px rgba(0,0,0,0.3);
    }

    .metric-value {
        font-size: 2.5rem;
        font-weight: 700;
        margin: 10px 0;
    }

    .metric-label {
        font-size: 1rem;
        opacity: 0.9;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    .tag-badge {
        display: inline-block;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 8px 15px;
        border-radius: 20px;
        margin: 5px;
        font-size: 0.9rem;
        font-weight: 500;
    }

    .stButton button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 25px;
        padding: 12px 30px;
        border: none;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    }

    .stButton button:hover {
        transform: translateY(-3px);
        box-shadow: 0 6px 20px rgba(0,0,0,0.3);
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: transparent;
    }

    .stTabs [data-baseweb="tab"] {
        background-color: rgba(255, 255, 255, 0.2);
        border-radius: 10px 10px 0 0;
        padding: 10px 20px;
        color: white;
        font-weight: 500;
    }

    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    @media (max-width: 768px) {
        .gradient-title {
            font-size: 2rem;
        }
        .metric-value {
            font-size: 1.8rem;
        }
    }
    </style>
    """, unsafe_allow_html=True)

# ==================== FUNÇÕES AUXILIARES ====================

def check_and_init_admin():
    """Inicializa administrador padrão se não existir"""
    admins = load_json_file(ADMIN_FILE, [])
    if not admins:
        hashed_password = hashlib.sha256("admin123".encode()).hexdigest()
        admins.append({
            "id": 1,
            "username": "admin",
            "password": hashed_password
        })
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
    st.cache_data.clear()  # Limpa cache quando nova tag é adicionada
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

# ==================== ANÁLISES ====================

def calculate_tag_diversity(tags_df):
    """Calcula diversidade de tags"""
    if tags_df.empty:
        return 0

    tag_counts = tags_df['tag'].value_counts()
    proportions = tag_counts / tag_counts.sum()
    shannon_index = -sum(proportions * np.log(proportions))
    return shannon_index

def analyze_user_engagement(users_df, tags_df):
    """Análise de engajamento dos usuários"""
    if users_df.empty or tags_df.empty:
        return None

    tags_per_user = tags_df.groupby('user_id').size().reset_index(name='tag_count')

    engagement_stats = {
        'avg_tags_per_user': tags_per_user['tag_count'].mean(),
        'median_tags_per_user': tags_per_user['tag_count'].median(),
        'max_tags_per_user': tags_per_user['tag_count'].max(),
        'total_active_users': len(tags_per_user),
        'total_registered_users': len(users_df)
    }

    return engagement_stats

def get_top_contributors(tags_df, top_n=10):
    """Identifica principais contribuidores"""
    if tags_df.empty:
        return pd.DataFrame()

    contributors = tags_df.groupby('user_id').agg({
        'tag': 'count',
        'timestamp': 'min'
    }).reset_index()

    contributors.columns = ['user_id', 'total_tags', 'first_contribution']
    contributors = contributors.sort_values('total_tags', ascending=False).head(top_n)

    return contributors

def analyze_tag_patterns(tags_df):
    """Analisa padrões nas tags"""
    if tags_df.empty:
        return None

    patterns = {
        'avg_tag_length': tags_df['tag'].str.len().mean(),
        'single_word_tags': sum(tags_df['tag'].str.split().str.len() == 1),
        'multi_word_tags': sum(tags_df['tag'].str.split().str.len() > 1),
        'numeric_tags': sum(tags_df['tag'].str.contains(r'\d', regex=True)),
        'special_char_tags': sum(tags_df['tag'].str.contains(r'[^a-zA-Z0-9\s]', regex=True))
    }

    return patterns

# ==================== INTERFACE PRINCIPAL ====================

def main():
    load_custom_css()

    try:
        check_and_init_admin()
    except Exception as e:
        st.error(f"Erro ao verificar admin: {e}")

    if 'user_id' not in st.session_state:
        st.session_state['user_id'] = generate_user_id()
    if 'step' not in st.session_state:
        st.session_state['step'] = 'intro'
    if 'answers' not in st.session_state:
        st.session_state['answers'] = {}
    if 'current_page' not in st.session_state:
        st.session_state['current_page'] = "Início"

    with st.sidebar:
        st.markdown("""
        <div style='text-align: center; padding: 20px;'>
            <h1 style='color: white; font-family: Playfair Display;'>🎨 Folksonomia</h1>
            <p style='color: rgba(255,255,255,0.8); font-size: 0.9rem;'>Museus Interativos</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        pages = ["🏠 Início", "🖼️ Explorar Obras", "📊 Área Administrativa"]
        page_mapping = {
            "🏠 Início": "Início",
            "🖼️ Explorar Obras": "Explorar Obras",
            "📊 Área Administrativa": "Área Administrativa"
        }

        selected_page = st.radio("Navegação", pages, label_visibility="collapsed")

        page = page_mapping[selected_page]

        if page != st.session_state.get('current_page'):
            st.session_state['current_page'] = page
            st.rerun()

        st.markdown("---")

        st.markdown(f"""
        <div style='background: rgba(255,255,255,0.1); padding: 15px; border-radius: 10px; margin-top: 20px;'>
            <p style='color: white; margin: 0; font-size: 0.8rem;'>ID do Usuário:</p>
            <p style='color: rgba(255,255,255,0.7); margin: 5px 0 0 0; font-size: 0.7rem; word-break: break-all;'>{st.session_state['user_id'][:12]}...</p>
        </div>
        """, unsafe_allow_html=True)

    if st.session_state['current_page'] == "Início":
        show_intro()
    elif st.session_state['current_page'] == "Explorar Obras":
        show_obras()
    elif st.session_state['current_page'] == "Área Administrativa":
        show_admin()

# ==================== PÁGINAS ====================

def show_intro():
    st.markdown("<div class='gradient-title'>Projeto de Folksonomia em Museus</div>", unsafe_allow_html=True)

    st.markdown("""
    <div style='text-align: center; max-width: 800px; margin: 0 auto 40px auto; color: white; font-size: 1.1rem; line-height: 1.8;'>
        Bem-vindo à nossa plataforma interativa de catalogação colaborativa! 
        Explore obras de arte e contribua com suas próprias tags para criar uma taxonomia popular.
    </div>
    """, unsafe_allow_html=True)

    if st.session_state['step'] == 'intro':
        st.markdown("<div class='main-container'>", unsafe_allow_html=True)

        st.markdown("<h2 style='text-align: center; margin-bottom: 30px;'>📋 Questionário Inicial</h2>", unsafe_allow_html=True)

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
                    height=200
                )

            st.markdown("<br>", unsafe_allow_html=True)

            col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])
            with col_btn2:
                submit = st.form_submit_button("✨ Enviar Respostas", use_container_width=True)

            if submit:
                if not q3.strip():
                    st.error("Por favor, responda todas as perguntas!")
                else:
                    st.session_state['answers'] = {"q1": q1, "q2": q2, "q3": q3}
                    save_user_answers(st.session_state['user_id'], st.session_state['answers'])
                    st.session_state['step'] = 'completed'
                    st.success("✅ Respostas enviadas com sucesso!")
                    st.balloons()
                    st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

    else:
        st.success("✅ Questionário concluído com sucesso!")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("""
            <div class='obra-card' style='text-align: center;'>
                <h3 style='color: #667eea;'>🖼️ Explorar</h3>
                <p>Descubra obras incríveis e contribua com suas tags</p>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            st.markdown("""
            <div class='obra-card' style='text-align: center;'>
                <h3 style='color: #764ba2;'>🏷️ Contribuir</h3>
                <p>Ajude a criar uma taxonomia colaborativa</p>
            </div>
            """, unsafe_allow_html=True)

        with col3:
            st.markdown("""
            <div class='obra-card' style='text-align: center;'>
                <h3 style='color: #e73c7e;'>📊 Analisar</h3>
                <p>Veja estatísticas e insights fascinantes</p>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br><br>", unsafe_allow_html=True)

        col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])
        with col_btn2:
            if st.button("🎨 Começar a Explorar", use_container_width=True):
                st.session_state['current_page'] = "Explorar Obras"
                st.rerun()

def show_obras():
    st.markdown("<div class='gradient-title'>Galeria de Obras Interativa</div>", unsafe_allow_html=True)

    if st.session_state['step'] == 'intro':
        st.warning("⚠️ Complete o questionário inicial antes de explorar as obras.")
        if st.button("📋 Ir para o Questionário"):
            st.session_state['current_page'] = "Início"
            st.rerun()
        return

    obras = load_obras()

    if not obras:
        st.info("Nenhuma obra cadastrada.")
        return

    # Filtros
    col_filter1, col_filter2, col_filter3 = st.columns([2, 2, 1])

    with col_filter1:
        search_term = st.text_input("🔍 Buscar obra por título ou artista", "")

    with col_filter2:
        sort_by = st.selectbox("Ordenar por:", ["Título", "Artista", "Ano"])

    with col_filter3:
        view_mode = st.selectbox("Visualização:", ["Grid", "Lista"])

    # Filtrar obras
    filtered_obras = obras
    if search_term:
        filtered_obras = [
            obra for obra in obras
            if search_term.lower() in obra['titulo'].lower() or
               search_term.lower() in obra['artista'].lower()
        ]

    # Ordenar obras
    if sort_by == "Título":
        filtered_obras = sorted(filtered_obras, key=lambda x: x['titulo'])
    elif sort_by == "Artista":
        filtered_obras = sorted(filtered_obras, key=lambda x: x['artista'])
    elif sort_by == "Ano":
        filtered_obras = sorted(filtered_obras, key=lambda x: x['ano'])

    st.markdown(f"""
    <div style='text-align: center; color: white; margin: 20px 0;'>
        <h3>🎨 Mostrando {len(filtered_obras)} obra(s)</h3>
    </div>
    """, unsafe_allow_html=True)

    # Exibir obras
    if view_mode == "Grid":
        cols = st.columns(3)
        for i, obra in enumerate(filtered_obras):
            with cols[i % 3]:
                st.markdown(f"""
                <div class='obra-card'>
                    <img src='{obra['imagem']}' style='width: 100%; border-radius: 15px; margin-bottom: 15px;' />
                    <h3 style='color: #667eea; margin: 10px 0;'>{obra['titulo']}</h3>
                    <p style='color: #666; margin: 5px 0;'><strong>{obra['artista']}</strong></p>
                    <p style='color: #999; margin: 5px 0;'>📅 {obra['ano']}</p>
                </div>
                """, unsafe_allow_html=True)

                if st.button(f"🏷️ Adicionar Tag", key=f"btn_{obra['id']}", use_container_width=True):
                    st.session_state['selected_obra'] = obra
                    st.rerun()

                if 'selected_obra' in st.session_state and st.session_state['selected_obra']['id'] == obra['id']:
                    with st.form(f"tag_form_{obra['id']}"):
                        tag = st.text_input("Digite sua tag:", key=f"tag_input_{obra['id']}", placeholder="ex: guerra, cubismo, história...")

                        col_submit1, col_submit2 = st.columns(2)
                        with col_submit1:
                            submitted = st.form_submit_button("✅ Enviar", use_container_width=True)
                        with col_submit2:
                            cancel = st.form_submit_button("❌ Cancelar", use_container_width=True)

                        if submitted and tag:
                            save_tag(st.session_state['user_id'], obra['id'], tag)
                            st.success(f"Tag '{tag}' adicionada com sucesso! 🎉")
                            st.balloons()
                            del st.session_state['selected_obra']
                            st.rerun()

                        if cancel:
                            del st.session_state['selected_obra']
                            st.rerun()

                    # Mostrar tags populares
                    tags = get_tags_for_obra(obra['id'])
                    if not tags.empty:
                        st.markdown("**🏆 Tags Populares:**")
                        for _, row in tags.head(5).iterrows():
                            st.markdown(f"""
                            <span class='tag-badge'>{row['tag']} ({row['count']})</span>
                            """, unsafe_allow_html=True)
                    else:
                        st.info("Seja o primeiro a adicionar uma tag! 🌟")

    else:  # Modo Lista
        for obra in filtered_obras:
            with st.container():
                st.markdown("<div class='obra-card'>", unsafe_allow_html=True)
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

                    # Tags populares
                    tags = get_tags_for_obra(obra['id'])
                    if not tags.empty:
                        st.markdown("**Tags Populares:**")
                        for _, row in tags.head(10).iterrows():
                            st.markdown(f"""<span class='tag-badge'>{row['tag']} ({row['count']})</span>""", unsafe_allow_html=True)

                st.markdown("</div>", unsafe_allow_html=True)
                st.markdown("---")

def show_admin():
    st.markdown("<div class='gradient-title'>Área Administrativa</div>", unsafe_allow_html=True)

    if 'admin_logged_in' not in st.session_state:
        st.session_state['admin_logged_in'] = False

    if not st.session_state['admin_logged_in']:
        st.markdown("<div class='main-container' style='max-width: 500px; margin: 50px auto;'>", unsafe_allow_html=True)

        st.markdown("<h2 style='text-align: center; margin-bottom: 30px;'>🔐 Login Administrativo</h2>", unsafe_allow_html=True)

        with st.form("login_form"):
            username = st.text_input("👤 Usuário:", placeholder="Digite seu usuário")
            password = st.text_input("🔑 Senha:", type="password", placeholder="Digite sua senha")

            st.markdown("<br>", unsafe_allow_html=True)

            submitted = st.form_submit_button("🚀 Entrar", use_container_width=True)

            if submitted:
                if check_admin_credentials(username, password):
                    st.session_state['admin_logged_in'] = True
                    st.session_state['admin_username'] = username
                    st.success("Login realizado com sucesso! 🎉")
                    st.balloons()
                    st.rerun()
                else:
                    st.error("❌ Credenciais inválidas. Tente novamente.")

        st.markdown("</div>", unsafe_allow_html=True)

        with st.expander("ℹ️ Informações de Acesso"):
            st.info("""
            **Credenciais padrão:**
            - Usuário: `admin`
            - Senha: `admin123`

            Por favor, altere a senha após o primeiro login por segurança.
            """)

    else:
        st.markdown(f"""
        <div style='text-align: right; color: white; margin-bottom: 20px;'>
            Bem-vindo, <strong>{st.session_state.get('admin_username', 'Admin')}</strong>! 👋
        </div>
        """, unsafe_allow_html=True)

        admin_tabs = st.tabs([
            "📊 Dashboard",
            "🖼️ Gerenciar Obras",
            "👥 Administradores"
        ])

        with admin_tabs[0]:
            show_analytics_dashboard()

        with admin_tabs[1]:
            show_manage_obras()

        with admin_tabs[2]:
            show_manage_admins()

        st.markdown("---")
        col_logout1, col_logout2, col_logout3 = st.columns([1, 1, 1])
        with col_logout2:
            if st.button("🚪 Sair do Sistema", use_container_width=True):
                st.session_state['admin_logged_in'] = False
                if 'admin_username' in st.session_state:
                    del st.session_state['admin_username']
                st.rerun()

def show_analytics_dashboard():
    """Dashboard de analytics usando apenas recursos nativos do Streamlit"""

    st.markdown("<h2 style='color: white; margin-bottom: 30px;'>📊 Dashboard de Análise de Dados</h2>", unsafe_allow_html=True)

    tags_df = load_all_tags()
    users_df = load_all_users()
    obras = load_obras()

    # Métricas principais
    st.markdown("### 📈 Métricas Principais")

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
            <div class='metric-label'>Total de Tags</div>
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

    st.markdown("<br><br>", unsafe_allow_html=True)

    if tags_df.empty:
        st.info("📭 Ainda não há dados suficientes para análise. Aguarde as primeiras contribuições!")
        return

    # Análises detalhadas
    viz_tabs = st.tabs([
        "📊 Análise de Tags",
        "👥 Engajamento",
        "📥 Exportar Dados"
    ])

    with viz_tabs[0]:
        st.markdown("### 🏷️ Tags Mais Frequentes")

        tag_counts = tags_df['tag'].value_counts().head(20)

        # Usar bar_chart nativo do Streamlit
        st.bar_chart(tag_counts)

        st.markdown("---")
        st.markdown("### 📋 Lista Completa de Tags")

        all_tags = tags_df['tag'].value_counts().reset_index()
        all_tags.columns = ['Tag', 'Frequência']
        st.dataframe(all_tags, use_container_width=True, height=400)

        st.markdown("---")
        st.markdown("### 🎨 Distribuição por Obra")

        obra_tags = tags_df.groupby('obra_id').size().reset_index(name='count')
        obra_info = pd.DataFrame(obras)
        merged = obra_info.merge(obra_tags, left_on='id', right_on='obra_id', how='left')
        merged['count'] = merged['count'].fillna(0)
        merged_display = merged[['titulo', 'count']].set_index('titulo')

        st.bar_chart(merged_display)

        st.markdown("---")
        st.markdown("### 📊 Padrões de Tags")

        patterns = analyze_tag_patterns(tags_df)
        if patterns:
            col_p1, col_p2, col_p3, col_p4 = st.columns(4)

            with col_p1:
                st.metric("Comprimento Médio", f"{patterns['avg_tag_length']:.1f} caracteres")
            with col_p2:
                st.metric("Tags Simples", patterns['single_word_tags'])
            with col_p3:
                st.metric("Tags Compostas", patterns['multi_word_tags'])
            with col_p4:
                diversity = calculate_tag_diversity(tags_df)
                st.metric("Índice de Diversidade", f"{diversity:.2f}")

    with viz_tabs[1]:
        st.markdown("### 👥 Análise de Engajamento")

        engagement = analyze_user_engagement(users_df, tags_df)

        if engagement:
            col_e1, col_e2, col_e3, col_e4 = st.columns(4)

            with col_e1:
                st.metric("Média Tags/Usuário", f"{engagement['avg_tags_per_user']:.1f}")
            with col_e2:
                st.metric("Mediana Tags/Usuário", f"{engagement['median_tags_per_user']:.1f}")
            with col_e3:
                st.metric("Máx Tags/Usuário", engagement['max_tags_per_user'])
            with col_e4:
                st.metric("Usuários Ativos", engagement['total_active_users'])

        st.markdown("---")
        st.markdown("### 🏆 Top 10 Contribuidores")

        contributors = get_top_contributors(tags_df, 10)
        if not contributors.empty:
            st.dataframe(contributors, use_container_width=True)
        else:
            st.info("Nenhum contribuidor ainda.")

        st.markdown("---")
        st.markdown("### 📈 Evolução Temporal")

        if 'timestamp' in tags_df.columns:
            tags_df['date'] = pd.to_datetime(tags_df['timestamp']).dt.date
            timeline = tags_df.groupby('date').size().reset_index(name='count')
            timeline_display = timeline.set_index('date')
            st.line_chart(timeline_display)

    with viz_tabs[2]:
        st.markdown("### 📥 Exportar Dados")

        col_exp1, col_exp2 = st.columns(2)

        with col_exp1:
            if not tags_df.empty:
                csv_tags = tags_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📄 Download Tags (CSV)",
                    data=csv_tags,
                    file_name=f'tags_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
                    mime='text/csv',
                    use_container_width=True
                )

        with col_exp2:
            if not users_df.empty:
                csv_users = users_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📄 Download Usuários (CSV)",
                    data=csv_users,
                    file_name=f'users_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
                    mime='text/csv',
                    use_container_width=True
                )

def show_manage_obras():
    """Gerenciamento de obras"""
    st.markdown("### 🖼️ Gerenciar Obras")

    obras = load_obras()

    if obras:
        obras_df = pd.DataFrame(obras)
        st.subheader("📚 Obras Cadastradas")
        st.dataframe(obras_df[["id", "titulo", "artista", "ano"]], use_container_width=True)
    else:
        st.write("Nenhuma obra cadastrada.")

    st.markdown("---")
    st.subheader("➕ Adicionar Nova Obra")

    with st.form("adicionar_obra"):
        novo_titulo = st.text_input("Título da Obra:")
        novo_artista = st.text_input("Artista:")
        novo_ano = st.text_input("Ano:")
        imagem_url = st.text_input("URL da Imagem:")

        submit_obra = st.form_submit_button("✅ Adicionar Obra")

        if submit_obra:
            if not novo_titulo or not novo_artista or not imagem_url:
                st.error("❌ Preencha todos os campos obrigatórios!")
            else:
                novo_id = 1
                if obras:
                    ids = [obra["id"] for obra in obras]
                    novo_id = max(ids) + 1

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
                st.success(f"✅ Obra '{novo_titulo}' adicionada com sucesso!")
                st.rerun()

    st.markdown("---")
    st.subheader("❌ Excluir Obra")

    if obras:
        obra_para_excluir = st.selectbox(
            "Selecione a obra para excluir:",
            [""] + [f"{obra['id']}: {obra['titulo']} - {obra['artista']}" for obra in obras]
        )

        if obra_para_excluir and st.button("🗑️ Excluir Obra Selecionada"):
            obra_id = int(obra_para_excluir.split(":")[0])

            # Verificar se há tags associadas
            tags = load_json_file(TAGS_FILE, [])
            has_tags = any(tag['obra_id'] == obra_id for tag in tags)

            if has_tags:
                st.warning("⚠️ Esta obra possui tags associadas. Exclua as tags primeiro na aba de dados.")
            else:
                obras = [o for o in obras if o['id'] != obra_id]
                save_json_file(OBRAS_FILE, obras)
                st.cache_data.clear()
                st.success("✅ Obra excluída com sucesso!")
                st.rerun()
    else:
        st.info("Não há obras para excluir.")

def show_manage_admins():
    """Gerenciamento de administradores"""
    st.subheader("👥 Gerenciar Administradores")

    with st.expander("➕ Adicionar Novo Administrador"):
        with st.form("add_admin_form"):
            new_username = st.text_input("Nome de usuário:")
            new_password = st.text_input("Senha:", type="password")
            confirm_password = st.text_input("Confirmar senha:", type="password")
            submit_admin = st.form_submit_button("✅ Adicionar")

            if submit_admin:
                if new_password != confirm_password:
                    st.error("❌ As senhas não coincidem!")
                elif len(new_password) < 6:
                    st.error("❌ A senha deve ter pelo menos 6 caracteres!")
                else:
                    admins = load_json_file(ADMIN_FILE, [])

                    if any(admin['username'] == new_username for admin in admins):
                        st.error(f"❌ O usuário '{new_username}' já existe!")
                    else:
                        hashed_password = hashlib.sha256(new_password.encode()).hexdigest()
                        new_id = max([admin['id'] for admin in admins]) + 1 if admins else 1
                        admins.append({
                            "id": new_id,
                            "username": new_username,
                            "password": hashed_password
                        })
                        save_json_file(ADMIN_FILE, admins)
                        st.success(f"✅ Administrador '{new_username}' adicionado com sucesso!")
                        st.rerun()

    admins = load_json_file(ADMIN_FILE, [])
    if admins:
        st.markdown("### 📋 Lista de Administradores")
        admins_df = pd.DataFrame(admins)
        st.dataframe(admins_df[["id", "username"]], use_container_width=True)

        with st.expander("❌ Excluir Administrador"):
            admin_para_excluir = st.selectbox(
                "Selecione o administrador:",
                [""] + [admin['username'] for admin in admins]
            )

            if admin_para_excluir and st.button("🗑️ Excluir Administrador"):
                if len(admins) <= 1:
                    st.error("❌ Não é possível excluir o último administrador do sistema!")
                else:
                    admins = [a for a in admins if a['username'] != admin_para_excluir]
                    save_json_file(ADMIN_FILE, admins)
                    st.success(f"✅ Administrador '{admin_para_excluir}' excluído com sucesso!")
                    st.rerun()
    else:
        st.warning("⚠️ Nenhum administrador encontrado no sistema.")

if __name__ == "__main__":
    main()
