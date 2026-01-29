import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import datetime
import hashlib
import base64
import json
import warnings
import plotly.express as px # Importar Plotly para gráficos de pizza

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
            st.error(f"Erro ao ler o arquivo {filepath}. O arquivo pode estar corrompido. Usando dados padrão.")
            return default_data
        except Exception as e:
            st.error(f"Erro inesperado ao carregar {filepath}: {e}. Usando dados padrão.")
            return default_data
    return default_data

def save_json_file(filepath, data):
    ensure_data_dir()
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar o arquivo {filepath}: {e}")
        return False

# ==================== CSS PROFISSIONAL CLARO (com letras pretas) e Liquid Glass ====================
def load_custom_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    * { 
        margin: 0; 
        padding: 0; 
        box-sizing: border-box; 
        font-family: 'Inter', sans-serif !important; 
    }
    .stApp {
        background: linear-gradient(to bottom, #f8fafc 0%, #f1f5f9 100%); /* Fundo claro, branco acinzentado */
        color: #1e293b; /* Cor de texto padrão escura */
    }
    .top-navbar {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        z-index: 9999;
        background: rgba(255, 255, 255, 0.8); /* Fundo branco semi-transparente para Liquid Glass */
        backdrop-filter: blur(10px); /* Efeito de desfoque */
        border-bottom: 1px solid rgba(226, 232, 240, 0.6); /* Borda mais suave */
        padding: 1.2rem 3rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08); /* Sombra mais pronunciada para profundidade */
    }
    .navbar-logo {
        font-size: 1.5rem;
        font-weight: 700;
        color: #1e293b; /* Logo em preto */
        letter-spacing: -0.5px;
    }
    .main-content {
        margin-top: 100px; /* Ajuste para a barra fixa */
        padding: 2rem 3rem;
        max-width: 1600px;
        margin-left: auto;
        margin-right: auto;
    }
    .professional-card {
        background: rgba(255, 255, 255, 0.9); /* Fundo semi-transparente */
        border: 1px solid rgba(226, 232, 240, 0.7); /* Borda suave */
        border-radius: 16px; /* Bordas mais arredondadas */
        padding: 2rem;
        margin: 1.5rem 0;
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.1); /* Sombra para profundidade */
        transition: all 0.4s ease;
        backdrop-filter: blur(8px); /* Efeito de desfoque */
    }
    .professional-card:hover {
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.15);
        border-color: rgba(192, 204, 218, 0.8);
        transform: translateY(-3px); /* Leve elevação ao passar o mouse */
    }
    .obra-card {
        background: rgba(255, 255, 255, 0.9);
        border: 1px solid rgba(226, 232, 240, 0.7);
        border-radius: 16px;
        overflow: hidden;
        transition: all 0.4s ease;
        cursor: pointer;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.08);
        backdrop-filter: blur(5px);
    }
    .obra-card:hover {
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.15);
        transform: translateY(-6px);
        border-color: rgba(148, 163, 184, 0.8);
    }
    .obra-card img {
        width: 100%;
        height: 240px;
        object-fit: cover;
        transition: transform 0.4s ease;
    }
    .obra-card:hover img {
        transform: scale(1.08);
    }
    .main-title {
        color: #1e293b;
        font-size: 2.8rem; /* Um pouco maior */
        font-weight: 800; /* Mais negrito */
        text-align: center;
        margin: 2.5rem 0 1.2rem 0;
        letter-spacing: -1px;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.05); /* Leve sombra no texto */
    }
    .subtitle {
        color: #64748b;
        font-size: 1.2rem; /* Um pouco maior */
        text-align: center;
        margin-bottom: 3rem;
        line-height: 1.7;
    }
    .tag-badge {
        display: inline-block;
        background: rgba(241, 245, 249, 0.7); /* Semi-transparente */
        border: 1px solid rgba(203, 213, 225, 0.6);
        color: #475569;
        padding: 0.6rem 1.2rem; /* Um pouco mais de padding */
        border-radius: 8px; /* Mais arredondado */
        margin: 0.4rem;
        font-size: 0.9rem;
        font-weight: 600;
        transition: all 0.3s ease;
        backdrop-filter: blur(3px);
    }
    .tag-badge:hover {
        background: rgba(226, 232, 240, 0.8);
        border-color: rgba(148, 163, 184, 0.7);
        transform: translateY(-2px);
    }
    .metric-card {
        background: linear-gradient(135deg, rgba(71, 85, 105, 0.9) 0%, rgba(51, 65, 85, 0.95) 100%); /* Gradiente escuro semi-transparente */
        border: none;
        border-radius: 16px;
        padding: 2.2rem; /* Mais padding */
        text-align: center;
        color: white;
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.2); /* Sombra mais forte */
        transition: all 0.4s ease;
        backdrop-filter: blur(8px);
    }
    .metric-card:hover {
        transform: translateY(-6px);
        box-shadow: 0 12px 35px rgba(0, 0, 0, 0.25);
    }
    .metric-value {
        font-size: 3.5rem; /* Maior */
        font-weight: 800; /* Mais negrito */
        margin: 0.6rem 0;
        text-shadow: 1px 1px 3px rgba(0,0,0,0.1);
    }
    .metric-label {
        font-size: 1rem; /* Maior */
        text-transform: uppercase;
        letter-spacing: 1.5px; /* Mais espaçamento */
        font-weight: 700;
        opacity: 0.95;
    }
    .stButton button {
        background: linear-gradient(145deg, #475569 0%, #334155 100%) !important; /* Gradiente para Liquid Glass */
        color: white !important;
        border: none !important;
        border-radius: 12px !important; /* Mais arredondado */
        padding: 1rem 2.5rem !important; /* Mais padding */
        font-weight: 700 !important; /* Mais negrito */
        transition: all 0.4s ease !important;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.15) !important; /* Sombra para profundidade */
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .stButton button:hover {
        background: linear-gradient(145deg, #334155 0%, #1e293b 100%) !important; /* Gradiente mais escuro no hover */
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.25) !important;
        transform: translateY(-3px) !important; /* Efeito de elevação */
    }
    .stTextInput input, .stTextArea textarea, .stSelectbox select {
        background: rgba(255, 255, 255, 0.8) !important; /* Semi-transparente */
        border: 1px solid rgba(203, 213, 225, 0.7) !important;
        color: #1e293b !important;
        border-radius: 10px !important; /* Mais arredondado */
        padding: 0.9rem !important;
        transition: all 0.3s ease !important;
        backdrop-filter: blur(5px);
    }
    .stTextInput input:focus, .stTextArea textarea:focus, .stSelectbox select:focus {
        border-color: #475569 !important; /* Borda mais escura no foco */
        box-shadow: 0 0 0 4px rgba(71, 85, 105, 0.15) !important; /* Sombra de foco mais proeminente */
    }
    label {
        color: #475569 !important;
        font-weight: 700 !important; /* Mais negrito */
        font-size: 0.95rem !important; /* Um pouco maior */
        margin-bottom: 0.6rem !important;
    }
    .stTabs [data-baseweb="tab"] {
        background: rgba(255, 255, 255, 0.7); /* Tabs semi-transparentes */
        border: 1px solid rgba(226, 232, 240, 0.6);
        border-radius: 10px 10px 0 0; /* Mais arredondado */
        color: #64748b;
        padding: 1rem 1.8rem; /* Mais padding */
        font-weight: 600;
        transition: all 0.3s ease;
        backdrop-filter: blur(5px);
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(145deg, #475569 0%, #334155 100%) !important; /* Gradiente para tab ativa */
        color: white !important;
        border-color: #475569 !important;
        box-shadow: 0 -3px 10px rgba(0, 0, 0, 0.1); /* Sombra para tab ativa */
    }
    .status-badge {
        display: inline-block;
        padding: 0.6rem 1.2rem;
        border-radius: 8px;
        font-size: 0.9rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        backdrop-filter: blur(3px);
    }
    .status-high {
        background: rgba(220, 252, 231, 0.8);
        border: 1px solid rgba(134, 239, 172, 0.7);
        color: #166534;
    }
    .status-medium {
        background: rgba(254, 243, 199, 0.8);
        border: 1px solid rgba(252, 211, 77, 0.7);
        color: #92400e;
    }
    .status-low {
        background: rgba(254, 226, 226, 0.8);
        border: 1px solid rgba(252, 165, 165, 0.7);
        color: #991b1b;
    }
    /* Cores para st.info, st.success, st.warning, st.error para texto escuro */
    .stAlert {
        color: #1e293b !important;
        border-radius: 10px !important;
        backdrop-filter: blur(5px);
    }
    .stAlert.info {
        background-color: rgba(224, 242, 254, 0.8) !important;
        border-left: 5px solid #0ea5e9 !important;
    }
    .stAlert.success {
        background-color: rgba(220, 252, 231, 0.8) !important;
        border-left: 5px solid #22c55e !important;
    }
    .stAlert.warning {
        background-color: rgba(254, 243, 199, 0.8) !important;
        border-left: 5px solid #f59e0b !important;
    }
    .stAlert.error {
        background-color: rgba(254, 226, 226, 0.8) !important;
        border-left: 5px solid #ef4444 !important;
    }

    #MainMenu, footer, header {visibility: hidden;}
    .stDeployButton {display: none;}
    [data-testid="stSidebar"] {display: none;} 

    h1, h2, h3, h4, h5, h6 {
        color: #1e293b;
        font-weight: 700; /* Mais negrito */
    }
    .dataframe {
        border: 1px solid rgba(226, 232, 240, 0.7) !important;
        border-radius: 12px !important;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        background: rgba(255, 255, 255, 0.8);
        backdrop-filter: blur(5px);
    }

    /* Estilo para os botões de navegação na parte inferior */
    .bottom-nav-container {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        z-index: 9998; /* Abaixo da navbar superior se houver */
        background: rgba(255, 255, 255, 0.9); /* Fundo branco acinzentado semi-transparente */
        backdrop-filter: blur(12px); /* Efeito de desfoque mais forte */
        border-top: 1px solid rgba(226, 232, 240, 0.6);
        padding: 1rem 3rem;
        display: flex;
        justify-content: center; /* Centraliza os botões */
        gap: 2rem; /* Espaçamento entre os botões */
        box-shadow: 0 -4px 12px rgba(0, 0, 0, 0.08);
        border-radius: 20px 20px 0 0; /* Bordas superiores arredondadas */
    }

    .bottom-nav-button {
        flex-grow: 0; /* Não cresce para preencher o espaço */
        flex-basis: auto; /* Tamanho automático */
        min-width: 180px; /* Largura mínima para os botões */
        background: linear-gradient(145deg, #475569 0%, #334155 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 1rem 2.5rem !important;
        font-weight: 700 !important;
        transition: all 0.4s ease !important;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.15) !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        cursor: pointer;
        text-align: center;
        text-decoration: none; /* Para links, se aplicável */
        display: inline-flex; /* Para alinhar ícones e texto */
        align-items: center;
        justify-content: center;
    }

    .bottom-nav-button:hover {
        background: linear-gradient(145deg, #334155 0%, #1e293b 100%) !important;
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.25) !important;
        transform: translateY(-3px) !important;
    }

    /* Estilo para o botão ativo na navegação inferior */
    .bottom-nav-button.active {
        background: linear-gradient(145deg, #1e293b 0%, #0f172a 100%) !important; /* Cor mais escura para o ativo */
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3) !important;
        transform: translateY(-5px) !important;
        border: 2px solid #64748b !important; /* Borda sutil para destaque */
    }

    @media (max-width: 768px) {
        .main-title { font-size: 2.2rem; }
        .main-content { margin-top: 120px; padding: 1rem; }
        .top-navbar { padding: 1rem 1.5rem; }
        .bottom-nav-container {
            flex-direction: column; /* Empilha os botões em telas pequenas */
            gap: 0.8rem;
            padding: 1rem;
            border-radius: 15px 15px 0 0;
        }
        .bottom-nav-button {
            min-width: unset; /* Remove largura mínima */
            width: 100%; /* Ocupa a largura total */
            padding: 0.8rem 1.5rem !important;
        }
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

def get_user_tags(user_id):
    """Retorna apenas tags do usuário atual"""
    tags = load_json_file(TAGS_FILE, [])
    user_tags = [t for t in tags if t['user_id'] == user_id]
    return pd.DataFrame(user_tags) if user_tags else pd.DataFrame()

def get_tags_for_obra_by_user(obra_id, user_id):
    """Retorna tags de uma obra criadas pelo usuário"""
    tags = load_json_file(TAGS_FILE, [])
    user_obra_tags = [t for t in tags if t['obra_id'] == obra_id and t['user_id'] == user_id]
    if user_obra_tags:
        df = pd.DataFrame(user_obra_tags)
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

def get_user_name_by_id(user_id):
    users_df = load_all_users()
    if not users_df.empty:
        user_row = users_df[users_df['user_id'] == user_id]
        if not user_row.empty:
            return user_row.iloc[0].get('nome', f"Usuário {user_id[:8]}...")
    return f"Usuário {user_id[:8]}..." # Fallback se não encontrar o nome

# ==================== EXPORTAÇÃO PDF/PLANILHA ====================
def generate_user_questionnaire_report(user_id):
    """Gera relatório das respostas do questionário"""
    users_df = load_all_users()
    if users_df.empty:
        return None
    user_data = users_df[users_df['user_id'] == user_id]
    if user_data.empty:
        return None
    user_info = user_data.iloc[0]
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Respostas do Questionário</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ font-family: 'Inter', sans-serif; background: #f8fafc; padding: 40px; color: #1e293b; }}
            .container {{ max-width: 900px; margin: 0 auto; background: white; padding: 50px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.08); }}
            h1 {{ color: #1e293b; text-align: center; margin-bottom: 15px; font-size: 2.2rem; border-bottom: 3px solid #475569; padding-bottom: 20px; }}
            .header-info {{ text-align: center; color: #64748b; margin-bottom: 40px; font-size: 0.95rem; }}
            .question-block {{ margin: 30px 0; padding: 25px; background: #f8fafc; border-left: 4px solid #475569; border-radius: 8px; }}
            .question {{ color: #475569; font-weight: 700; font-size: 1.1rem; margin-bottom: 12px; }}
            .answer {{ color: #1e293b; font-size: 1rem; line-height: 1.7; padding: 10px 0; }}
            .footer {{ text-align: center; margin-top: 50px; padding-top: 25px; border-top: 2px solid #e2e8f0; color: #94a3b8; font-size: 0.85rem; }}
            @media print {{ body {{ background: white; padding: 0; }} .container {{ box-shadow: none; }} }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Respostas do Questionário de Acesso</h1>
            <div class="header-info">
                <p><strong>Nome do Usuário:</strong> {user_info.get('nome', 'N/A')}</p>
                <p><strong>ID do Usuário:</strong> {user_id}</p>
                <p><strong>Data de Resposta:</strong> {user_info.get('timestamp', 'N/A')}</p>
            </div>
            <div class="question-block">
                <div class="question">1. Qual é o seu nível de familiaridade com museus?</div>
                <div class="answer">{user_info.get('q1', 'N/A')}</div>
            </div>
            <div class="question-block">
                <div class="question">2. Você já ouviu falar sobre documentação museológica?</div>
                <div class="answer">{user_info.get('q2', 'N/A')}</div>
            </div>
            <div class="question-block">
                <div class="question">3. O que você entende por 'tags' ou etiquetas digitais aplicadas a acervo?</div>
                <div class="answer">{user_info.get('q3', 'N/A')}</div>
            </div>
            <div class="footer">
                <p>Sistema Folksonomia Digital</p>
                <p style="margin-top: 10px;">Para salvar como PDF: Use Ctrl+P e selecione "Salvar como PDF"</p>
            </div>
        </div>
    </body>
    </html>
    """
    return html

def generate_user_tags_report(user_id, obras):
    """Gera relatório detalhado das tags criadas pelo usuário"""
    user_tags_df = get_user_tags(user_id)
    if user_tags_df.empty:
        return None
    obras_dict = {o['id']: o for o in obras}
    user_name = get_user_name_by_id(user_id)
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Relatório de Tags Criadas</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ font-family: 'Inter', sans-serif; background: #f8fafc; padding: 40px; color: #1e293b; }}
            .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 50px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.08); }}
            h1 {{ color: #1e293b; text-align: center; margin-bottom: 15px; font-size: 2.2rem; border-bottom: 3px solid #475569; padding-bottom: 20px; }}
            .header-info {{ text-align: center; color: #64748b; margin-bottom: 40px; font-size: 0.95rem; }}
            .stats {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin: 30px 0; }}
            .stat-box {{ background: #f1f5f9; border-left: 4px solid #475569; padding: 20px; border-radius: 8px; text-align: center; }}
            .stat-value {{ font-size: 2.5rem; font-weight: 700; color: #475569; }}
            .stat-label {{ color: #64748b; font-size: 0.9rem; text-transform: uppercase; letter-spacing: 1px; margin-top: 8px; }}
            table {{ width: 100%; border-collapse: collapse; margin: 30px 0; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }}
            th, td {{ padding: 15px; text-align: left; border-bottom: 1px solid #e2e8f0; }}
            th {{ background: #475569; color: white; font-weight: 700; text-transform: uppercase; font-size: 0.85rem; letter-spacing: 0.5px; }}
            tr:nth-child(even) {{ background: #f8fafc; }}
            tr:hover {{ background: #f1f5f9; }}
            .tag-highlight {{ background: #f1f5f9; padding: 5px 12px; border-radius: 6px; border: 1px solid #cbd5e1; font-weight: 600; }}
            .footer {{ text-align: center; margin-top: 50px; padding-top: 25px; border-top: 2px solid #e2e8f0; color: #94a3b8; font-size: 0.85rem; }}
            @media print {{ body {{ background: white; padding: 0; }} .container {{ box-shadow: none; }} }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Relatório de Tags Criadas</h1>
            <div class="header-info">
                <p><strong>Nome do Usuário:</strong> {user_name}</p>
                <p><strong>ID do Usuário:</strong> {user_id}</p>
                <p><strong>Data de Geração:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
            </div>
            <div class="stats">
                <div class="stat-box">
                    <div class="stat-value">{len(user_tags_df)}</div>
                    <div class="stat-label">Total de Tags</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value">{len(user_tags_df['tag'].unique())}</div>
                    <div class="stat-label">Tags Únicas</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value">{len(user_tags_df['obra_id'].unique())}</div>
                    <div class="stat-label">Obras Etiquetadas</div>
                </div>
            </div>
            <h2 style="color: #1e293b; margin-top: 40px; margin-bottom: 20px; font-size: 1.5rem;">Tags Detalhadas</h2>
            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Obra</th>
                        <th>Artista</th>
                        <th>Tag Criada</th>
                        <th>Data/Hora</th>
                    </tr>
                </thead>
                <tbody>
    """
    for idx, row in user_tags_df.iterrows():
        obra = obras_dict.get(row['obra_id'], {})
        html += f"""
                        <tr>
                            <td>{idx + 1}</td>
                            <td>{obra.get('titulo', 'N/A')}</td>
                            <td>{obra.get('artista', 'N/A')}</td>
                            <td><span class="tag-highlight">{row['tag']}</span></td>
                            <td>{row['timestamp']}</td>
                        </tr>
        """
    # Top 10 tags mais usadas
    top_tags = user_tags_df['tag'].value_counts().head(10)
    html += """
                </tbody>
            </table>
            <h2 style="color: #1e293b; margin-top: 40px; margin-bottom: 20px; font-size: 1.5rem;">Suas Tags Mais Utilizadas</h2>
            <table>
                <thead>
                    <tr>
                        <th>Posição</th>
                        <th>Tag</th>
                        <th>Frequência</th>
                    </tr>
                </thead>
                <tbody>
    """
    for idx, (tag, count) in enumerate(top_tags.items(), 1):
        html += f"""
                        <tr>
                            <td>{idx}</td>
                            <td><span class="tag-highlight">{tag}</span></td>
                            <td>{count}</td>
                        </tr>
        """
    html += """
                </tbody>
            </table>
            <div class="footer">
                <p>Sistema Folksonomia Digital</p>
                <p style="margin-top: 10px;">Para salvar como PDF: Use Ctrl+P e selecione "Salvar como PDF"</p>
            </div>
        </div>
    </body>
    </html>
    """
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
        pass

    if 'user_id' not in st.session_state:
        st.session_state['user_id'] = generate_user_id()
    if 'step' not in st.session_state:
        st.session_state['step'] = 'intro'
    if 'answers' not in st.session_state:
        st.session_state['answers'] = {}
    if 'current_page' not in st.session_state:
        st.session_state['current_page'] = "Explorar Obras" # Página inicial padrão

    if st.session_state['step'] != 'completed':
        show_intro()
    else:
        show_header()
        st.markdown("<div class='main-content'>", unsafe_allow_html=True)

        # Conteúdo principal da página
        if st.session_state['current_page'] == "Explorar Obras":
            show_obras()
        elif st.session_state['current_page'] == "Área Administrativa":
            show_admin()

        st.markdown("</div>", unsafe_allow_html=True)

        # Nova navegação inferior com botões Liquid Glass
        st.markdown("<div class='bottom-nav-container'>", unsafe_allow_html=True)

        # Botão Explorar Obras
        col1, col2 = st.columns(2)
        with col1:
            if st.markdown(f"""
                <button class='bottom-nav-button {"active" if st.session_state['current_page'] == "Explorar Obras" else ""}' 
                        onclick="window.parent.document.querySelector('[data-testid=\"stFormSubmitButton\"]').click();">
                    Explorar Obras
                </button>
                <style>div[data-testid="stVerticalBlock"] > div > div > div > div:nth-child(1) > div > button {{ display: none; }}</style>
                """, unsafe_allow_html=True):
                st.session_state['current_page'] = "Explorar Obras"
                st.rerun()

        # Botão Área Administrativa
        with col2:
            if st.markdown(f"""
                <button class='bottom-nav-button {"active" if st.session_state['current_page'] == "Área Administrativa" else ""}' 
                        onclick="window.parent.document.querySelector('[data-testid=\"stFormSubmitButton\"]').click();">
                    Área Administrativa
                </button>
                <style>div[data-testid="stVerticalBlock"] > div > div > div > div:nth-child(2) > div > button {{ display: none; }}</style>
                """, unsafe_allow_html=True):
                st.session_state['current_page'] = "Área Administrativa"
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)


def show_intro():
    st.markdown("<div class='main-content'>", unsafe_allow_html=True)
    st.markdown("<h1 class='main-title'>Sistema Folksonomia Digital</h1>", unsafe_allow_html=True)
    st.markdown("<p class='subtitle'>Sistema de catalogação colaborativa de obras de arte<br>Complete o questionário para acessar a plataforma</p>", unsafe_allow_html=True)
    st.markdown("<div class='professional-card'>", unsafe_allow_html=True)
    st.markdown("<h2 style='color: #1e293b; text-align: center; margin-bottom: 2rem; font-size: 1.5rem;'>Questionário de Acesso</h2>", unsafe_allow_html=True)
    with st.form("intro_form"):
        nome_usuario = st.text_input("Seu Nome:", placeholder="Digite seu nome completo")
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
            if not nome_usuario.strip() or not q3.strip():
                st.error("Por favor, preencha seu nome e responda todas as perguntas para continuar!")
            else:
                st.session_state['answers'] = {"nome": nome_usuario, "q1": q1, "q2": q2, "q3": q3}
                save_user_answers(st.session_state['user_id'], st.session_state['answers'])
                st.session_state['step'] = 'completed'
                st.success("Questionário completo! Acesso liberado.")
                st.balloons()
                st.rerun()
    st.markdown("</div></div>", unsafe_allow_html=True)

def show_obras():
    st.markdown("<h1 class='main-title'>Galeria de Obras de Arte</h1>", unsafe_allow_html=True)
    st.markdown("<p class='subtitle'>Explore obras de arte e contribua com tags colaborativas</p>", unsafe_allow_html=True)
    obras = load_obras()
    if not obras:
        st.info("Nenhuma obra cadastrada no momento.")
        return

    st.markdown("<div class='professional-card'>", unsafe_allow_html=True)
    col1, col2 = st.columns([2, 1])
    with col1:
        search = st.text_input("Buscar obra", "", placeholder="Digite título ou artista...")
    with col2:
        sort_by = st.selectbox("Ordenar por:", ["Título", "Artista", "Ano"])
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

    st.markdown(f"<div style='text-align: center; color: #64748b; margin: 2rem 0; font-size: 1.1rem;'>Exibindo <strong style='color: #475569;'>{len(filtered)}</strong> obra(s)</div>", unsafe_allow_html=True)

    cols = st.columns(3)
    for i, obra in enumerate(filtered):
        with cols[i % 3]:
            st.markdown(f"""
            <div class='obra-card'>
                <img src='{obra['imagem']}' alt='{obra['titulo']}' />
                <div style='padding: 1.5rem;'>
                    <h3 style='color: #1e293b; font-size: 1.2rem; font-weight: 700; margin-bottom: 0.5rem;'>{obra['titulo']}</h3>
                    <p style='color: #64748b; font-size: 0.9rem; margin: 0.3rem 0;'><span style='font-weight: 600;'>Artista:</span> {obra['artista']}</p>
                    <p style='color: #94a3b8; font-size: 0.85rem;'><span style='font-weight: 600;'>Ano:</span> {obra['ano']}</p>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Adicionar um identificador único para o formulário de tag
            form_key = f"tag_form_{obra['id']}_{st.session_state['user_id']}"

            if st.button(f"Adicionar Tag", key=f"btn_add_tag_{obra['id']}", use_container_width=True):
                st.session_state['selected_obra'] = obra
                st.rerun()

            if 'selected_obra' in st.session_state and st.session_state['selected_obra']['id'] == obra['id']:
                with st.form(form_key):
                    tag = st.text_input("Sua tag:", key=f"tag_input_{obra['id']}", placeholder="Ex: impressionismo")
                    col_form1, col_form2 = st.columns(2)
                    with col_form1:
                        submitted = st.form_submit_button("Enviar", use_container_width=True)
                    with col_form2:
                        cancel = st.form_submit_button("Cancelar", use_container_width=True)
                    if submitted and tag:
                        save_tag(st.session_state['user_id'], obra['id'], tag)
                        st.success(f"Tag '{tag}' adicionada com sucesso!")
                        del st.session_state['selected_obra']
                        st.rerun()
                    if cancel:
                        del st.session_state['selected_obra']
                        st.rerun()

            tags = get_tags_for_obra_by_user(obra['id'], st.session_state['user_id'])
            if not tags.empty:
                st.markdown("**Suas Tags:**")
                html = ""
                for _, row in tags.iterrows():
                    html += f"<span class='tag-badge'>{row['tag']} ({row['count']})</span>"
                st.markdown(html, unsafe_allow_html=True)
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
            st.markdown("<div class='professional-card'>", unsafe_allow_html=True)
            st.markdown("<h2 style='color: #1e293b; text-align: center; margin-bottom: 2rem;'>Login Administrativo</h2>", unsafe_allow_html=True)
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
        st.markdown(f"<h1 class='main-title'>Dashboard Administrativo</h1><p class='subtitle'>Bem-vindo, <strong style='color: #475569;'>{st.session_state.get('admin_username', 'Admin')}</strong></p>", unsafe_allow_html=True)

        tabs = st.tabs(["Visão Geral", "Análises", "Dados", "Obras", "Exportar Completo", "Exportar Usuários"])

        with tabs[0]:
            show_overview()
        with tabs[1]:
            show_analysis()
        with tabs[2]:
            show_data_analysis()
        with tabs[3]:
            show_manage_obras()
        with tabs[4]:
            show_export_complete()
        with tabs[5]:
            show_export_users()

        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button("Sair do Sistema", use_container_width=True, key="admin_logout_btn"):
                st.session_state['admin_logged_in'] = False
                st.rerun()

def show_overview():
    tags_df = load_all_tags()
    users_df = load_all_users()
    obras = load_obras()

    st.markdown("### Métricas Principais")
    col1, col2, col3, col4 = st.columns(4)
    metrics = [
        ("Usuários", len(users_df['user_id'].unique()) if not users_df.empty else 0),
        ("Total Tags", len(tags_df) if not tags_df.empty else 0),
        ("Tags Únicas", len(tags_df['tag'].unique()) if not tags_df.empty else 0),
        ("Obras", len(obras))
    ]
    for col, (label, value) in zip([col1, col2, col3, col4], metrics):
        with col:
            st.markdown(f"""
            <div class='metric-card'>
                <div class='metric-label'>{label}</div>
                <div class='metric-value'>{value}</div>
            </div>
            """, unsafe_allow_html=True)

    if not tags_df.empty:
        st.markdown("### Rankings")
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

def show_analysis():
    st.markdown("### Análises Gerais")
    tags_df = load_all_tags()
    if tags_df.empty:
        st.info("Não há dados suficientes para análises.")
        return

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Distribuição de Tags (Top 15)")
        counts = tags_df['tag'].value_counts().head(15)
        if not counts.empty:
            fig = px.pie(counts, values=counts.values, names=counts.index, title='Top 15 Tags Mais Utilizadas',
                         hole=0.3, # Para um gráfico de rosca
                         color_discrete_sequence=px.colors.sequential.RdBu) # Paleta de cores
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Não há tags para exibir.")

    with col2:
        st.markdown("#### Obras Mais Tagueadas (Top 10)")
        per_obra = tags_df.groupby('obra_id').size()
        obras = load_obras()
        od = {o['id']: o['titulo'] for o in obras}
        per_obra_named = per_obra.rename(index=od).sort_values(ascending=False).head(10)
        if not per_obra_named.empty:
            fig = px.pie(per_obra_named, values=per_obra_named.values, names=per_obra_named.index, title='Top 10 Obras Mais Tagueadas',
                         hole=0.3,
                         color_discrete_sequence=px.colors.sequential.Plasma)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Não há obras tagueadas para exibir.")

    st.markdown("#### Tags Raras (Top 10 menos usadas)")
    rare_tags = tags_df['tag'].value_counts().tail(10).reset_index()
    rare_tags.columns = ['Tag', 'Quantidade']
    st.dataframe(rare_tags, use_container_width=True, hide_index=True)

def show_data_analysis():
    st.markdown("### Análise Detalhada de Dados")
    tags_df = load_all_tags()
    users_df = load_all_users()
    obras = load_obras()

    if tags_df.empty and users_df.empty:
        st.info("Sem dados suficientes para análise detalhada.")
        return

    tab_overview, tab_tags_detail, tab_questionnaire_analysis = st.tabs(["Visão Geral dos Dados", "Análise de Tags Detalhada", "Análise do Questionário"])

    with tab_overview:
        st.markdown("#### Resumo dos Dados Coletados")
        col1, col2, col3, col4 = st.columns(4)
        metrics = [
            ("Total de Usuários", len(users_df['user_id'].unique()) if not users_df.empty else 0),
            ("Total de Tags", len(tags_df) if not tags_df.empty else 0),
            ("Tags Únicas", len(tags_df['tag'].unique()) if not tags_df.empty else 0),
            ("Total de Obras", len(obras))
        ]
        for col, (label, value) in zip([col1, col2, col3, col4], metrics):
            with col:
                st.markdown(f"""
                <div class='metric-card'>
                    <div class='metric-label'>{label}</div>
                    <div class='metric-value'>{value}</div>
                </div>
                """, unsafe_allow_html=True)

        if not tags_df.empty:
            st.markdown("#### Distribuição das 10 Tags Mais Frequentes")
            top_tags_counts = tags_df['tag'].value_counts().head(10)
            if not top_tags_counts.empty:
                fig = px.pie(top_tags_counts, values=top_tags_counts.values, names=top_tags_counts.index, title='Top 10 Tags Mais Frequentes',
                             hole=0.4, color_discrete_sequence=px.colors.sequential.Viridis)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Não há tags para exibir.")

            st.markdown("#### Distribuição das 10 Obras Mais Tagueadas")
            ot = tags_df.groupby('obra_id').size().reset_index(name='Total')
            od = {o['id']: o['titulo'] for o in obras}
            ot['Obra'] = ot['obra_id'].map(od)
            top_obras_counts = ot[['Obra', 'Total']].sort_values('Total', ascending=False).head(10).set_index('Obra')
            if not top_obras_counts.empty:
                fig = px.pie(top_obras_counts, values=top_obras_counts['Total'], names=top_obras_counts.index, title='Top 10 Obras Mais Tagueadas',
                             hole=0.4, color_discrete_sequence=px.colors.sequential.Magma)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Não há obras tagueadas para exibir.")
        else:
            st.info("Não há tags para exibir rankings e distribuições.")

    with tab_tags_detail:
        st.markdown("#### Análise Aprofundada das Tags")
        if not tags_df.empty:
            st.markdown("##### Todas as Tags e Suas Frequências")
            st.dataframe(tags_df['tag'].value_counts().reset_index().rename(columns={'index': 'Tag', 'tag': 'Frequência Total'}), use_container_width=True, hide_index=True)

            st.markdown("##### Distribuição de Tags Únicas por Obra")
            tags_per_obra_unique = tags_df.groupby('obra_id')['tag'].nunique().reset_index()
            tags_per_obra_unique.columns = ['obra_id', 'Tags Únicas']
            obras_dict = {o['id']: o['titulo'] for o in obras}
            tags_per_obra_unique['Obra'] = tags_per_obra_unique['obra_id'].map(obras_dict)

            top_unique_obra_tags = tags_per_obra_unique.sort_values('Tags Únicas', ascending=False).head(10).set_index('Obra')
            if not top_unique_obra_tags.empty:
                fig = px.pie(top_unique_obra_tags, values=top_unique_obra_tags['Tags Únicas'], names=top_unique_obra_tags.index, title='Top 10 Obras com Mais Tags Únicas',
                             hole=0.4, color_discrete_sequence=px.colors.sequential.Cividis)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Não há tags únicas por obra para exibir.")
            st.dataframe(tags_per_obra_unique[['Obra', 'Tags Únicas']].sort_values('Tags Únicas', ascending=False), use_container_width=True, hide_index=True)

            st.markdown("##### Distribuição de Tags Únicas por Usuário")
            tags_per_user_unique = tags_df.groupby('user_id')['tag'].nunique().reset_index()
            tags_per_user_unique.columns = ['user_id', 'Tags Únicas']
            tags_per_user_unique['Nome do Usuário'] = tags_per_user_unique['user_id'].apply(get_user_name_by_id)

            top_unique_user_tags = tags_per_user_unique.sort_values('Tags Únicas', ascending=False).head(10).set_index('Nome do Usuário')
            if not top_unique_user_tags.empty:
                fig = px.pie(top_unique_user_tags, values=top_unique_user_tags['Tags Únicas'], names=top_unique_user_tags.index, title='Top 10 Usuários com Mais Tags Únicas',
                             hole=0.4, color_discrete_sequence=px.colors.sequential.Inferno)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Não há tags únicas por usuário para exibir.")
            st.dataframe(tags_per_user_unique[['Nome do Usuário', 'Tags Únicas']].sort_values('Tags Únicas', ascending=False), use_container_width=True, hide_index=True)

            st.markdown("##### Análise de Co-ocorrência de Tags (Padrões de Ligação)")
            st.info("Esta análise mostra quais tags tendem a aparecer juntas nas mesmas obras. Isso ajuda a identificar padrões e 'bases' de tagueamento.")

            tags_by_obra = tags_df.groupby('obra_id')['tag'].apply(lambda x: set(x.tolist())).tolist()

            co_occurrence = {}
            for i in range(len(tags_by_obra)):
                for tag1 in tags_by_obra[i]:
                    for tag2 in tags_by_obra[i]:
                        if tag1 != tag2:
                            pair = tuple(sorted((tag1, tag2)))
                            co_occurrence[pair] = co_occurrence.get(pair, 0) + 1

            if co_occurrence:
                co_occurrence_df = pd.DataFrame(co_occurrence.items(), columns=['Par de Tags', 'Frequência'])
                co_occurrence_df['Tag 1'] = co_occurrence_df['Par de Tags'].apply(lambda x: x[0])
                co_occurrence_df['Tag 2'] = co_occurrence_df['Par de Tags'].apply(lambda x: x[1])
                st.dataframe(co_occurrence_df[['Tag 1', 'Tag 2', 'Frequência']].sort_values('Frequência', ascending=False).head(20), use_container_width=True, hide_index=True)
            else:
                st.info("Não há tags suficientes para analisar co-ocorrência.")

            st.markdown("##### Distribuição do Comprimento das Tags")
            if not tags_df.empty:
                tags_df['tag_length'] = tags_df['tag'].str.len()
                length_counts = tags_df['tag_length'].value_counts().sort_index()
                if not length_counts.empty:
                    fig = px.bar(length_counts, x=length_counts.index, y=length_counts.values, title='Distribuição do Comprimento das Tags',
                                 labels={'x':'Comprimento da Tag', 'y':'Frequência'},
                                 color_discrete_sequence=px.colors.sequential.Blues_r)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Não há tags para analisar o comprimento.")
                st.write(f"Média de comprimento das tags: {tags_df['tag_length'].mean():.2f} caracteres")
                st.write(f"Desvio padrão do comprimento das tags: {tags_df['tag_length'].std():.2f} caracteres")
            else:
                st.info("Não há tags para analisar o comprimento.")

        else:
            st.info("Não há tags para análise detalhada.")

    with tab_questionnaire_analysis:
        st.markdown("#### Análise do Questionário de Usuários")
        if not users_df.empty:
            st.markdown("##### Distribuição das Respostas (Q1: Familiaridade com Museus)")
            q1_counts = users_df['q1'].value_counts()
            if not q1_counts.empty:
                fig = px.pie(q1_counts, values=q1_counts.values, names=q1_counts.index, title='Familiaridade com Museus',
                             hole=0.4, color_discrete_sequence=px.colors.sequential.Greens)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Não há respostas para Q1.")

            st.markdown("##### Distribuição das Respostas (Q2: Conhecimento sobre Documentação Museológica)")
            q2_counts = users_df['q2'].value_counts()
            if not q2_counts.empty:
                fig = px.pie(q2_counts, values=q2_counts.values, names=q2_counts.index, title='Conhecimento sobre Documentação Museológica',
                             hole=0.4, color_discrete_sequence=px.colors.sequential.Purples)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Não há respostas para Q2.")

            st.markdown("##### Cruzamento de Dados: Familiaridade com Museus vs. Número de Tags Criadas")
            if not tags_df.empty:
                user_tag_counts = tags_df.groupby('user_id').size().reset_index(name='Total_Tags')
                merged_df = pd.merge(users_df, user_tag_counts, on='user_id', how='left').fillna(0)
                avg_tags_by_familiarity = merged_df.groupby('q1')['Total_Tags'].mean().sort_values(ascending=False)
                if not avg_tags_by_familiarity.empty:
                    fig = px.bar(avg_tags_by_familiarity.reset_index(), x='q1', y='Total_Tags', title='Média de Tags por Familiaridade com Museus',
                                 labels={'q1':'Familiaridade com Museus', 'Total_Tags':'Média de Tags'},
                                 color='q1', color_discrete_sequence=px.colors.sequential.YlGnBu)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Não há dados de tags para cruzar com Q1.")
                st.write("Média de tags criadas por nível de familiaridade com museus:")
                st.dataframe(avg_tags_by_familiarity.reset_index(), use_container_width=True, hide_index=True)
            else:
                st.info("Não há tags para cruzar com os dados do questionário.")

            st.markdown("##### Cruzamento de Dados: Familiaridade com Museus vs. Diversidade de Tags Criadas")
            if not tags_df.empty:
                user_unique_tag_counts = tags_df.groupby('user_id')['tag'].nunique().reset_index(name='Tags_Unicas')
                merged_df_unique = pd.merge(users_df, user_unique_tag_counts, on='user_id', how='left').fillna(0)
                avg_unique_tags_by_familiarity = merged_df_unique.groupby('q1')['Tags_Unicas'].mean().sort_values(ascending=False)
                if not avg_unique_tags_by_familiarity.empty:
                    fig = px.bar(avg_unique_tags_by_familiarity.reset_index(), x='q1', y='Tags_Unicas', title='Média de Tags Únicas por Familiaridade com Museus',
                                 labels={'q1':'Familiaridade com Museus', 'Tags_Unicas':'Média de Tags Únicas'},
                                 color='q1', color_discrete_sequence=px.colors.sequential.OrRd)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Não há dados de tags únicas para cruzar com Q1.")
                st.write("Média de tags únicas criadas por nível de familiaridade com museus:")
                st.dataframe(avg_unique_tags_by_familiarity.reset_index(), use_container_width=True, hide_index=True)
            else:
                st.info("Não há tags para cruzar com os dados do questionário.")

            st.markdown("##### Respostas Abertas (Q3: O que você entende por 'tags'?)")
            st.dataframe(users_df[['user_id', 'nome', 'q3', 'timestamp']].sort_values('timestamp', ascending=False), use_container_width=True, hide_index=True)
            st.info("Para uma análise mais profunda das respostas abertas, seria necessário processamento de linguagem natural (NLP) para identificar temas e padrões.")
        else:
            st.info("Nenhum usuário respondeu ao questionário ainda.")

def show_manage_obras():
    st.markdown("### Gestão de Obras")
    obras = load_obras()
    tab1, tab2 = st.tabs(["Listar Obras", "Adicionar Nova"])

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
                    if st.button("Remover", key=f"del_{obra['id']}"):
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
            titulo = st.text_input("Título da Obra")
            artista = st.text_input("Artista")
            ano = st.text_input("Ano")
            imagem = st.text_input("URL da Imagem")
            if st.form_submit_button("Adicionar Obra"):
                if titulo and artista and ano and imagem:
                    new_id = max([o['id'] for o in obras]) + 1 if obras else 1
                    obras.append({"id": new_id, "titulo": titulo, "artista": artista, "ano": ano, "imagem": imagem})
                    save_json_file(OBRAS_FILE, obras)
                    st.success("Obra adicionada com sucesso!")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("Preencha todos os campos!")

def show_export_complete():
    st.markdown("### Exportação Completa do Sistema")
    tags_df = load_all_tags()
    users_df = load_all_users()
    obras = load_obras()

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Exportar CSV")
        if not tags_df.empty:
            csv = tags_df.to_csv(index=False).encode('utf-8')
            st.download_button("Baixar Todas as Tags (CSV)", csv, f"tags_completo_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv", use_container_width=True)
        if not users_df.empty:
            csv = users_df.to_csv(index=False).encode('utf-8')
            st.download_button("Baixar Todos os Usuários (CSV)", csv, f"usuarios_completo_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv", use_container_width=True)
        if obras:
            csv = pd.DataFrame(obras).to_csv(index=False).encode('utf-8')
            st.download_button("Baixar Todas as Obras (CSV)", csv, f"obras_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv", use_container_width=True)

def show_export_users():
    st.markdown("### Exportar Dados por Usuário")
    users_df = load_all_users()
    obras = load_obras()

    if users_df.empty:
        st.info("Nenhum usuário cadastrado.")
        return

    user_ids = users_df['user_id'].unique().tolist()
    user_options = []
    for user_id in user_ids:
        user_name = get_user_name_by_id(user_id)
        user_options.append(f"{user_name} (ID: {user_id})")

    selected_option = st.selectbox("Selecione o usuário:", user_options)
    selected_user = selected_option.split('(ID: ')[-1].replace(')', '') if selected_option else None

    if selected_user:
        user_name_display = selected_option.split(' (ID:')[0]
        st.markdown(f"#### Dados para o Usuário: **{user_name_display}**")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("##### Questionário")
            html = generate_user_questionnaire_report(selected_user)
            if html:
                st.download_button("Baixar Respostas (HTML/PDF)", html, f"questionario_{selected_user}.html", "text/html", use_container_width=True)
            user_data = users_df[users_df['user_id'] == selected_user]
            if not user_data.empty:
                csv = user_data.to_csv(index=False).encode('utf-8')
                st.download_button("Baixar Respostas (CSV)", csv, f"questionario_{selected_user}.csv", "text/csv", use_container_width=True)
        with col2:
            st.markdown("##### Tags Criadas")
            html = generate_user_tags_report(selected_user, obras)
            if html:
                st.download_button("Baixar Tags (HTML/PDF)", html, f"tags_{selected_user}.html", "text/html", use_container_width=True)
            user_tags = get_user_tags(selected_user)
            if not user_tags.empty:
                csv = user_tags.to_csv(index=False).encode('utf-8')
                st.download_button("Baixar Tags (CSV)", csv, f"tags_{selected_user}.csv", "text/csv", use_container_width=True)

if __name__ == "__main__":
    main()

