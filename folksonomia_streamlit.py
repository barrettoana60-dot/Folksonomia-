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

# ==================== CSS GLASSMORPHISM MODERNO ====================
def load_custom_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800&display=swap');

    * { 
        margin: 0; 
        padding: 0; 
        box-sizing: border-box; 
        font-family: 'Poppins', sans-serif !important; 
    }

    @keyframes gradient {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }

    @keyframes float {
        0%, 100% { transform: translateY(0px); }
        50% { transform: translateY(-20px); }
    }

    @keyframes pulse {
        0%, 100% { transform: scale(1); }
        50% { transform: scale(1.05); }
    }

    @keyframes shimmer {
        0% { background-position: -1000px 0; }
        100% { background-position: 1000px 0; }
    }

    .stApp {
        background: linear-gradient(-45deg, #667eea 0%, #764ba2 25%, #f093fb 50%, #4facfe 75%, #00f2fe 100%);
        background-size: 400% 400%;
        animation: gradient 15s ease infinite;
        color: #1e293b;
    }

    .top-navbar {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        z-index: 9999;
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(20px) saturate(180%);
        -webkit-backdrop-filter: blur(20px) saturate(180%);
        border-bottom: 1px solid rgba(255, 255, 255, 0.2);
        padding: 1.5rem 3rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
    }

    .navbar-logo {
        font-size: 1.8rem;
        font-weight: 800;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        letter-spacing: -1px;
        animation: pulse 2s ease-in-out infinite;
    }

    .main-content {
        margin-top: 120px;
        padding: 2rem 3rem;
        max-width: 1600px;
        margin-left: auto;
        margin-right: auto;
    }

    .glass-card {
        background: rgba(255, 255, 255, 0.15);
        backdrop-filter: blur(20px) saturate(180%);
        -webkit-backdrop-filter: blur(20px) saturate(180%);
        border: 1px solid rgba(255, 255, 255, 0.3);
        border-radius: 24px;
        padding: 2.5rem;
        margin: 1.5rem 0;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
        overflow: hidden;
    }

    .glass-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
        transition: left 0.5s;
    }

    .glass-card:hover::before {
        left: 100%;
    }

    .glass-card:hover {
        transform: translateY(-8px) scale(1.02);
        box-shadow: 0 16px 48px rgba(0, 0, 0, 0.2);
        border-color: rgba(255, 255, 255, 0.5);
    }

    .obra-card {
        background: rgba(255, 255, 255, 0.2);
        backdrop-filter: blur(15px) saturate(180%);
        -webkit-backdrop-filter: blur(15px) saturate(180%);
        border: 1px solid rgba(255, 255, 255, 0.3);
        border-radius: 20px;
        overflow: hidden;
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        cursor: pointer;
        position: relative;
    }

    .obra-card::after {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.3), rgba(118, 75, 162, 0.3));
        opacity: 0;
        transition: opacity 0.4s;
    }

    .obra-card:hover::after {
        opacity: 1;
    }

    .obra-card:hover {
        transform: translateY(-12px) scale(1.03);
        box-shadow: 0 20px 60px rgba(102, 126, 234, 0.4);
        border-color: rgba(255, 255, 255, 0.6);
    }

    .obra-card img {
        width: 100%;
        height: 280px;
        object-fit: cover;
        transition: transform 0.6s cubic-bezier(0.4, 0, 0.2, 1);
    }

    .obra-card:hover img {
        transform: scale(1.15) rotate(2deg);
    }

    .main-title {
        color: white;
        font-size: 3.5rem;
        font-weight: 800;
        text-align: center;
        margin: 2rem 0 1rem 0;
        letter-spacing: -2px;
        text-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        animation: float 3s ease-in-out infinite;
    }

    .subtitle {
        color: rgba(255, 255, 255, 0.95);
        font-size: 1.3rem;
        text-align: center;
        margin-bottom: 3rem;
        line-height: 1.8;
        font-weight: 300;
        text-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
    }

    .tag-badge {
        display: inline-block;
        background: rgba(255, 255, 255, 0.25);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.4);
        color: white;
        padding: 0.6rem 1.2rem;
        border-radius: 50px;
        margin: 0.4rem;
        font-size: 0.9rem;
        font-weight: 600;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
    }

    .tag-badge:hover {
        background: rgba(255, 255, 255, 0.4);
        transform: translateY(-3px) scale(1.05);
        box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
    }

    .metric-card {
        background: rgba(255, 255, 255, 0.2);
        backdrop-filter: blur(20px) saturate(180%);
        border: 1px solid rgba(255, 255, 255, 0.3);
        border-radius: 20px;
        padding: 2.5rem;
        text-align: center;
        color: white;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
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
        background: radial-gradient(circle, rgba(255, 255, 255, 0.1) 0%, transparent 70%);
        animation: pulse 3s ease-in-out infinite;
    }

    .metric-card:hover {
        transform: translateY(-8px) scale(1.05);
        box-shadow: 0 16px 48px rgba(102, 126, 234, 0.3);
        border-color: rgba(255, 255, 255, 0.5);
    }

    .metric-value {
        font-size: 3.5rem;
        font-weight: 800;
        margin: 1rem 0;
        text-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
        position: relative;
        z-index: 1;
    }

    .metric-label {
        font-size: 1rem;
        text-transform: uppercase;
        letter-spacing: 2px;
        font-weight: 600;
        opacity: 0.95;
        position: relative;
        z-index: 1;
    }

    .stButton button {
        background: rgba(255, 255, 255, 0.25) !important;
        backdrop-filter: blur(15px) !important;
        color: white !important;
        border: 1px solid rgba(255, 255, 255, 0.4) !important;
        border-radius: 50px !important;
        padding: 1rem 2.5rem !important;
        font-weight: 700 !important;
        font-size: 1rem !important;
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1) !important;
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15) !important;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    .stButton button:hover {
        background: rgba(255, 255, 255, 0.4) !important;
        box-shadow: 0 12px 40px rgba(102, 126, 234, 0.4) !important;
        transform: translateY(-4px) scale(1.05) !important;
        border-color: rgba(255, 255, 255, 0.6) !important;
    }

    .stButton button:active {
        transform: translateY(-2px) scale(1.02) !important;
    }

    .stTextInput input, .stTextArea textarea, .stSelectbox select {
        background: rgba(255, 255, 255, 0.2) !important;
        backdrop-filter: blur(10px) !important;
        border: 1px solid rgba(255, 255, 255, 0.3) !important;
        color: white !important;
        border-radius: 16px !important;
        padding: 1rem !important;
        transition: all 0.3s ease !important;
        font-weight: 500 !important;
    }

    .stTextInput input::placeholder, .stTextArea textarea::placeholder {
        color: rgba(255, 255, 255, 0.6) !important;
    }

    .stTextInput input:focus, .stTextArea textarea:focus, .stSelectbox select:focus {
        border-color: rgba(255, 255, 255, 0.6) !important;
        box-shadow: 0 0 0 3px rgba(255, 255, 255, 0.2) !important;
        background: rgba(255, 255, 255, 0.3) !important;
    }

    label {
        color: white !important;
        font-weight: 700 !important;
        font-size: 1rem !important;
        margin-bottom: 0.8rem !important;
        text-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
        letter-spacing: 0.5px;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 1rem;
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        padding: 0.5rem;
        border-radius: 16px;
    }

    .stTabs [data-baseweb="tab"] {
        background: rgba(255, 255, 255, 0.15);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 12px;
        color: white;
        padding: 1rem 2rem;
        font-weight: 700;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }

    .stTabs [data-baseweb="tab"]:hover {
        background: rgba(255, 255, 255, 0.25);
        transform: translateY(-2px);
    }

    .stTabs [aria-selected="true"] {
        background: rgba(255, 255, 255, 0.35) !important;
        border-color: rgba(255, 255, 255, 0.5) !important;
        box-shadow: 0 8px 25px rgba(102, 126, 234, 0.3) !important;
    }

    .status-badge {
        display: inline-block;
        padding: 0.6rem 1.2rem;
        border-radius: 50px;
        font-size: 0.9rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1px;
        backdrop-filter: blur(10px);
    }

    .status-high {
        background: rgba(34, 197, 94, 0.3);
        border: 1px solid rgba(34, 197, 94, 0.5);
        color: #dcfce7;
    }

    .status-medium {
        background: rgba(245, 158, 11, 0.3);
        border: 1px solid rgba(245, 158, 11, 0.5);
        color: #fef3c7;
    }

    .status-low {
        background: rgba(239, 68, 68, 0.3);
        border: 1px solid rgba(239, 68, 68, 0.5);
        color: #fee2e2;
    }

    .stAlert {
        background: rgba(255, 255, 255, 0.2) !important;
        backdrop-filter: blur(15px) !important;
        border-radius: 16px !important;
        border-left: 4px solid !important;
        color: white !important;
        font-weight: 500 !important;
    }

    .stAlert.info { border-left-color: #3b82f6 !important; }
    .stAlert.success { border-left-color: #22c55e !important; }
    .stAlert.warning { border-left-color: #f59e0b !important; }
    .stAlert.error { border-left-color: #ef4444 !important; }

    #MainMenu, footer, header {visibility: hidden;}
    .stDeployButton {display: none;}
    [data-testid="stSidebar"] {display: none;} 

    h1, h2, h3, h4, h5, h6 {
        color: white;
        font-weight: 700;
        text-shadow: 0 2px 15px rgba(0, 0, 0, 0.3);
    }

    .dataframe {
        background: rgba(255, 255, 255, 0.15) !important;
        backdrop-filter: blur(10px) !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        border-radius: 16px !important;
        color: white !important;
    }

    .dataframe th {
        background: rgba(255, 255, 255, 0.25) !important;
        color: white !important;
        font-weight: 700 !important;
    }

    .dataframe td {
        color: white !important;
    }

    @media (max-width: 768px) {
        .main-title { font-size: 2.5rem; }
        .main-content { margin-top: 140px; padding: 1rem; }
        .top-navbar { padding: 1rem 1.5rem; }
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
    tags = load_json_file(TAGS_FILE, [])
    user_tags = [t for t in tags if t['user_id'] == user_id]
    return pd.DataFrame(user_tags) if user_tags else pd.DataFrame()

def get_tags_for_obra_by_user(obra_id, user_id):
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
    # Removido o campo 'nome' do questionário, então o nome do usuário será o ID truncado
    return f"Usuário {user_id[:8]}"

# ==================== EXPORTAÇÃO ====================
def generate_user_questionnaire_report(user_id):
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
            body {{ font-family: 'Poppins', sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 40px; color: white; }}
            .container {{ max-width: 900px; margin: 0 auto; background: rgba(255, 255, 255, 0.15); backdrop-filter: blur(20px); padding: 50px; border-radius: 24px; box-shadow: 0 8px 32px rgba(0,0,0,0.2); border: 1px solid rgba(255, 255, 255, 0.3); }}
            h1 {{ text-align: center; margin-bottom: 15px; font-size: 2.5rem; text-shadow: 0 4px 20px rgba(0, 0, 0, 0.3); }}
            .header-info {{ text-align: center; margin-bottom: 40px; font-size: 1rem; opacity: 0.9; }}
            .question-block {{ margin: 30px 0; padding: 25px; background: rgba(255, 255, 255, 0.1); border-left: 4px solid rgba(255, 255, 255, 0.5); border-radius: 16px; }}
            .question {{ font-weight: 700; font-size: 1.1rem; margin-bottom: 12px; }}
            .answer {{ font-size: 1rem; line-height: 1.7; padding: 10px 0; opacity: 0.95; }}
            .footer {{ text-align: center; margin-top: 50px; padding-top: 25px; border-top: 2px solid rgba(255, 255, 255, 0.2); opacity: 0.8; font-size: 0.9rem; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📋 Respostas do Questionário</h1>
            <div class="header-info">
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
        <title>Relatório de Tags</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ font-family: 'Poppins', sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 40px; color: white; }}
            .container {{ max-width: 1200px; margin: 0 auto; background: rgba(255, 255, 255, 0.15); backdrop-filter: blur(20px); padding: 50px; border-radius: 24px; box-shadow: 0 8px 32px rgba(0,0,0,0.2); border: 1px solid rgba(255, 255, 255, 0.3); }}
            h1 {{ text-align: center; margin-bottom: 15px; font-size: 2.5rem; text-shadow: 0 4px 20px rgba(0, 0, 0, 0.3); }}
            .header-info {{ text-align: center; margin-bottom: 40px; font-size: 1rem; opacity: 0.9; }}
            .stats {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin: 30px 0; }}
            .stat-box {{ background: rgba(255, 255, 255, 0.15); border: 1px solid rgba(255, 255, 255, 0.3); padding: 25px; border-radius: 16px; text-align: center; }}
            .stat-value {{ font-size: 3rem; font-weight: 800; text-shadow: 0 4px 20px rgba(0, 0, 0, 0.2); }}
            .stat-label {{ font-size: 0.95rem; text-transform: uppercase; letter-spacing: 1.5px; margin-top: 10px; opacity: 0.9; }}
            table {{ width: 100%; border-collapse: collapse; margin: 30px 0; }}
            th, td {{ padding: 18px; text-align: left; border-bottom: 1px solid rgba(255, 255, 255, 0.2); }}
            th {{ background: rgba(255, 255, 255, 0.2); font-weight: 700; text-transform: uppercase; font-size: 0.9rem; letter-spacing: 1px; }}
            tr:nth-child(even) {{ background: rgba(255, 255, 255, 0.05); }}
            tr:hover {{ background: rgba(255, 255, 255, 0.1); }}
            .tag-highlight {{ background: rgba(255, 255, 255, 0.25); padding: 6px 14px; border-radius: 50px; border: 1px solid rgba(255, 255, 255, 0.4); font-weight: 600; }}
            .footer {{ text-align: center; margin-top: 50px; padding-top: 25px; border-top: 2px solid rgba(255, 255, 255, 0.2); opacity: 0.8; font-size: 0.9rem; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🏷️ Relatório de Tags Criadas</h1>
            <div class="header-info">
                <p><strong>Usuário:</strong> {user_name}</p>
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
            <h2 style="margin-top: 40px; margin-bottom: 20px; font-size: 1.8rem;">📊 Tags Detalhadas</h2>
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
    top_tags = user_tags_df['tag'].value_counts().head(10)
    html += """
                </tbody>
            </table>
            <h2 style="margin-top: 40px; margin-bottom: 20px; font-size: 1.8rem;">⭐ Suas Tags Mais Utilizadas</h2>
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
        <div class='navbar-logo'>✨ Folksonomia Digital</div>
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

    if st.session_state['step'] != 'completed':
        show_intro()
    else:
        show_header()
        st.markdown("<div class='main-content'>", unsafe_allow_html=True)
        main_tabs = st.tabs(["🎨 Explorar Obras", "⚙️ Área Administrativa"])
        with main_tabs[0]:
            show_obras()
        with main_tabs[1]:
            show_admin()
        st.markdown("</div>", unsafe_allow_html=True)

def show_intro():
    st.markdown("<div class='main-content'>", unsafe_allow_html=True)
    st.markdown("<h1 class='main-title'>✨ Folksonomia Digital</h1>", unsafe_allow_html=True)
    st.markdown("<p class='subtitle'>Sistema colaborativo de catalogação de obras de arte<br>Complete o questionário para acessar a plataforma</p>", unsafe_allow_html=True)

    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.markdown("<h2 style='text-align: center; margin-bottom: 2.5rem; font-size: 1.8rem;'>📋 Questionário de Acesso</h2>", unsafe_allow_html=True)

    with st.form("intro_form"):
        # Removido o campo 'nome_usuario' conforme solicitado
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
            submit = st.form_submit_button("🚀 Acessar Plataforma", use_container_width=True)

        if submit:
            if not q3.strip(): # Apenas q3 é obrigatório agora
                st.error("⚠️ Por favor, responda todas as perguntas para continuar!")
            else:
                st.session_state['answers'] = {"q1": q1, "q2": q2, "q3": q3} # 'nome' não é mais salvo
                save_user_answers(st.session_state['user_id'], st.session_state['answers'])
                st.session_state['step'] = 'completed'
                st.success("✅ Questionário completo! Acesso liberado.")
                st.balloons()
                st.rerun()

    st.markdown("</div></div>", unsafe_allow_html=True)

def show_obras():
    st.markdown("<h1 class='main-title'>🎨 Galeria de Obras de Arte</h1>", unsafe_allow_html=True)
    st.markdown("<p class='subtitle'>Explore obras de arte e contribua com tags colaborativas</p>", unsafe_allow_html=True)

    obras = load_obras()
    if not obras:
        st.info("Nenhuma obra cadastrada no momento.")
        return

    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    col1, col2 = st.columns([2, 1])
    with col1:
        search = st.text_input("🔍 Buscar obra", "", placeholder="Digite título ou artista...")
    with col2:
        sort_by = st.selectbox("📊 Ordenar por:", ["Título", "Artista", "Ano"])
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

    st.markdown(f"<div style='text-align: center; color: white; margin: 2rem 0; font-size: 1.2rem; font-weight: 600;'>Exibindo <strong style='font-size: 1.5rem;'>{len(filtered)}</strong> obra(s)</div>", unsafe_allow_html=True)

    cols = st.columns(3)
    for i, obra in enumerate(filtered):
        with cols[i % 3]:
            st.markdown(f"""
            <div class='obra-card'>
                <img src='{obra['imagem']}' alt='{obra['titulo']}' />
                <div style='padding: 1.8rem;'>
                    <h3 style='font-size: 1.3rem; font-weight: 700; margin-bottom: 0.8rem;'>{obra['titulo']}</h3>
                    <p style='font-size: 1rem; margin: 0.5rem 0; opacity: 0.9;'>🎭 {obra['artista']}</p>
                    <p style='font-size: 0.95rem; opacity: 0.8;'>📅 {obra['ano']}</p>
                </div>
            </div>
            """, unsafe_allow_html=True)

            if st.button(f"🏷️ Adicionar Tag", key=f"btn_{obra['id']}", use_container_width=True):
                st.session_state['selected_obra'] = obra
                st.rerun()

            if 'selected_obra' in st.session_state and st.session_state['selected_obra']['id'] == obra['id']:
                with st.form(f"tag_form_{obra['id']}"):
                    tag = st.text_input("Sua tag:", key=f"tag_{obra['id']}", placeholder="Ex: impressionismo")
                    col1, col2 = st.columns(2)
                    with col1:
                        submitted = st.form_submit_button("✅ Enviar", use_container_width=True)
                    with col2:
                        cancel = st.form_submit_button("❌ Cancelar", use_container_width=True)

                    if submitted and tag:
                        save_tag(st.session_state['user_id'], obra['id'], tag)
                        st.success(f"✨ Tag '{tag}' adicionada com sucesso!")
                        del st.session_state['selected_obra']
                        st.rerun()
                    if cancel:
                        del st.session_state['selected_obra']
                        st.rerun()

            tags = get_tags_for_obra_by_user(obra['id'], st.session_state['user_id'])
            if not tags.empty:
                st.markdown("**🏷️ Suas Tags:**")
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
        st.markdown("<h1 class='main-title'>⚙️ Área Administrativa</h1>", unsafe_allow_html=True)
        st.markdown("<p class='subtitle'>Acesso restrito</p>", unsafe_allow_html=True)

        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
            st.markdown("<h2 style='text-align: center; margin-bottom: 2rem;'>🔐 Login Administrativo</h2>", unsafe_allow_html=True)

            with st.form("login"):
                username = st.text_input("👤 Usuário:", placeholder="Digite seu usuário")
                password = st.text_input("🔑 Senha:", type="password", placeholder="Digite sua senha")
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
        st.markdown(f"<h1 class='main-title'>📊 Dashboard Administrativo</h1><p class='subtitle'>Bem-vindo, <strong>{st.session_state.get('admin_username', 'Admin')}</strong></p>", unsafe_allow_html=True)

        tabs = st.tabs(["📈 Visão Geral", "🔍 Análises", "📊 Dados", "🎨 Obras", "📦 Exportar Completo", "👥 Exportar Usuários"])

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
            if st.button("🚪 Sair do Sistema", use_container_width=True):
                st.session_state['admin_logged_in'] = False
                st.rerun()

def show_overview():
    tags_df = load_all_tags()
    users_df = load_all_users()
    obras = load_obras()

    st.markdown("### 📊 Métricas Principais")
    col1, col2, col3, col4 = st.columns(4)

    metrics = [
        ("👥 Usuários", len(users_df['user_id'].unique()) if not users_df.empty else 0),
        ("🏷️ Total Tags", len(tags_df) if not tags_df.empty else 0),
        ("✨ Tags Únicas", len(tags_df['tag'].unique()) if not tags_df.empty else 0),
        ("🎨 Obras", len(obras))
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
        st.markdown("### 🏆 Rankings")
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### 🔝 Top 15 Tags Mais Utilizadas")
            top = tags_df['tag'].value_counts().head(15).reset_index()
            top.columns = ['Tag', 'Quantidade']
            st.dataframe(top, use_container_width=True, hide_index=True)

        with col2:
            st.markdown("#### 🎨 Obras Mais Tagueadas")
            ot = tags_df.groupby('obra_id').size().reset_index(name='Total')
            od = {o['id']: o['titulo'] for o in obras}
            ot['Obra'] = ot['obra_id'].map(od)
            st.dataframe(ot[['Obra', 'Total']].sort_values('Total', ascending=False).head(10),
                         use_container_width=True, hide_index=True)

def show_analysis():
    st.markdown("### 📈 Análises Gerais")
    tags_df = load_all_tags()

    if tags_df.empty:
        st.info("Não há dados suficientes para análises.")
        return

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 📊 Distribuição de Tags (Top 15)")
        counts = tags_df['tag'].value_counts().head(15)
        st.bar_chart(counts)

    with col2:
        st.markdown("#### 🎨 Obras Mais Tagueadas (Top 10)")
        per_obra = tags_df.groupby('obra_id').size()
        obras = load_obras()
        od = {o['id']: o['titulo'] for o in obras}
        per_obra_named = per_obra.rename(index=od).sort_values(ascending=False).head(10)
        st.bar_chart(per_obra_named)

    st.markdown("#### 🔍 Tags Raras (Top 10 menos usadas)")
    rare_tags = tags_df['tag'].value_counts().tail(10).reset_index()
    rare_tags.columns = ['Tag', 'Quantidade']
    st.dataframe(rare_tags, use_container_width=True, hide_index=True)

def show_data_analysis():
    st.markdown("### 📊 Análise Detalhada de Dados")
    tags_df = load_all_tags()
    users_df = load_all_users()
    obras = load_obras()

    if tags_df.empty and users_df.empty:
        st.info("Sem dados suficientes para análise detalhada.")
        return

    tab_overview, tab_tags_detail, tab_questionnaire_analysis = st.tabs(["📋 Visão Geral", "🏷️ Análise de Tags", "📝 Análise do Questionário"])

    with tab_overview:
        st.markdown("#### 📊 Resumo dos Dados Coletados")
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
            st.markdown("#### 📊 Distribuição das 10 Tags Mais Frequentes")
            top_tags_counts = tags_df['tag'].value_counts().head(10)
            st.bar_chart(top_tags_counts)

            st.markdown("#### 🎨 Distribuição das 10 Obras Mais Tagueadas")
            ot = tags_df.groupby('obra_id').size().reset_index(name='Total')
            od = {o['id']: o['titulo'] for o in obras}
            ot['Obra'] = ot['obra_id'].map(od)
            top_obras_counts = ot[['Obra', 'Total']].sort_values('Total', ascending=False).head(10).set_index('Obra')
            st.bar_chart(top_obras_counts)

    with tab_tags_detail:
        st.markdown("#### 🔍 Análise Aprofundada das Tags")

        if not tags_df.empty:
            st.markdown("##### 📋 Todas as Tags e Suas Frequências")
            all_tags_freq = tags_df['tag'].value_counts().reset_index()
            all_tags_freq.columns = ['Tag', 'Frequência Total']
            st.dataframe(all_tags_freq, use_container_width=True, hide_index=True)

            st.markdown("##### 🎨 Distribuição de Tags Únicas por Obra")
            tags_per_obra_unique = tags_df.groupby('obra_id')['tag'].nunique().reset_index()
            tags_per_obra_unique.columns = ['obra_id', 'Tags Únicas']
            obras_dict = {o['id']: o['titulo'] for o in obras}
            tags_per_obra_unique['Obra'] = tags_per_obra_unique['obra_id'].map(obras_dict)
            top_unique_obra_tags = tags_per_obra_unique.sort_values('Tags Únicas', ascending=False).head(10).set_index('Obra')
            st.bar_chart(top_unique_obra_tags)
            st.dataframe(tags_per_obra_unique[['Obra', 'Tags Únicas']].sort_values('Tags Únicas', ascending=False), use_container_width=True, hide_index=True)

            st.markdown("##### 👥 Distribuição de Tags Únicas por Usuário")
            tags_per_user_unique = tags_df.groupby('user_id')['tag'].nunique().reset_index()
            tags_per_user_unique.columns = ['user_id', 'Tags Únicas']
            tags_per_user_unique['Nome do Usuário'] = tags_per_user_unique['user_id'].apply(get_user_name_by_id)
            top_unique_user_tags = tags_per_user_unique.sort_values('Tags Únicas', ascending=False).head(10).set_index('Nome do Usuário')
            st.bar_chart(top_unique_user_tags)
            st.dataframe(tags_per_user_unique[['Nome do Usuário', 'Tags Únicas']].sort_values('Tags Únicas', ascending=False), use_container_width=True, hide_index=True)

            st.markdown("##### 🔗 Análise de Co-ocorrência de Tags")
            st.info("Esta análise mostra quais tags tendem a aparecer juntas nas mesmas obras.")
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

            st.markdown("##### 📏 Distribuição do Comprimento das Tags")
            if not tags_df.empty:
                tags_df['tag_length'] = tags_df['tag'].str.len()
                st.bar_chart(tags_df['tag_length'].value_counts().sort_index())
                st.write(f"**Média de comprimento das tags:** {tags_df['tag_length'].mean():.2f} caracteres")
                st.write(f"**Desvio padrão do comprimento das tags:** {tags_df['tag_length'].std():.2f} caracteres")

    with tab_questionnaire_analysis:
        st.markdown("#### 📝 Análise do Questionário de Usuários")

        if not users_df.empty:
            st.markdown("##### 📊 Distribuição das Respostas (Q1: Familiaridade com Museus)")
            q1_counts = users_df['q1'].value_counts()
            st.bar_chart(q1_counts)

            st.markdown("##### 📊 Distribuição das Respostas (Q2: Conhecimento sobre Documentação Museológica)")
            q2_counts = users_df['q2'].value_counts()
            st.bar_chart(q2_counts)

            if not tags_df.empty:
                st.markdown("##### 🔄 Cruzamento: Familiaridade com Museus vs. Número de Tags Criadas")
                user_tag_counts = tags_df.groupby('user_id').size().reset_index(name='Total_Tags')
                merged_df = pd.merge(users_df, user_tag_counts, on='user_id', how='left').fillna(0)
                avg_tags_by_familiarity = merged_df.groupby('q1')['Total_Tags'].mean().sort_values(ascending=False)
                st.bar_chart(avg_tags_by_familiarity)
                st.write("**Média de tags criadas por nível de familiaridade com museus:**")
                st.dataframe(avg_tags_by_familiarity.reset_index(), use_container_width=True, hide_index=True)

                st.markdown("##### 🔄 Cruzamento: Familiaridade com Museus vs. Diversidade de Tags")
                user_unique_tag_counts = tags_df.groupby('user_id')['tag'].nunique().reset_index(name='Tags_Unicas')
                merged_df_unique = pd.merge(users_df, user_unique_tag_counts, on='user_id', how='left').fillna(0)
                avg_unique_tags_by_familiarity = merged_df_unique.groupby('q1')['Tags_Unicas'].mean().sort_values(ascending=False)
                st.bar_chart(avg_unique_tags_by_familiarity)
                st.write("**Média de tags únicas criadas por nível de familiaridade com museus:**")
                st.dataframe(avg_unique_tags_by_familiarity.reset_index(), use_container_width=True, hide_index=True)

            st.markdown("##### 📝 Respostas Abertas (Q3: O que você entende por 'tags'?)")
            st.dataframe(users_df[['user_id', 'q3', 'timestamp']].sort_values('timestamp', ascending=False), use_container_width=True, hide_index=True)
            st.info("💡 Para análise mais profunda das respostas abertas, seria necessário processamento de linguagem natural (NLP).")
        else:
            st.info("Nenhum usuário respondeu ao questionário ainda.")

def show_manage_obras():
    st.markdown("### 🎨 Gestão de Obras")
    obras = load_obras()

    tab1, tab2 = st.tabs(["📋 Listar Obras", "➕ Adicionar Nova"])

    with tab1:
        if obras:
            for obra in obras:
                col1, col2, col3 = st.columns([1, 2, 1])
                with col1:
                    st.image(obra['imagem'], use_container_width=True)
                with col2:
                    st.markdown(f"**{obra['titulo']}**")
                    st.markdown(f"*{obra['artista']} - {obra['ano']}*")
                with col3: # <-- Onde o erro estava, agora corrigido
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
        with st.form("add"):
            titulo = st.text_input("📝 Título da Obra")
            artista = st.text_input("🎭 Artista")
            ano = st.text_input("📅 Ano")
            imagem = st.text_input("🖼️ URL da Imagem")

            if st.form_submit_button("✅ Adicionar Obra"):
                if titulo and artista and ano and imagem:
                    new_id = max([o['id'] for o in obras]) + 1 if obras else 1
                    obras.append({"id": new_id, "titulo": titulo, "artista": artista, "ano": ano, "imagem": imagem})
                    save_json_file(OBRAS_FILE, obras)
                    st.success("✅ Obra adicionada com sucesso!")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("⚠️ Preencha todos os campos!")

def show_export_complete():
    st.markdown("### 📦 Exportação Completa do Sistema")
    tags_df = load_all_tags()
    users_df = load_all_users()
    obras = load_obras()

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 📊 Exportar CSV")
        if not tags_df.empty:
            csv = tags_df.to_csv(index=False).encode('utf-8')
            st.download_button("⬇️ Baixar Todas as Tags (CSV)", csv, f"tags_completo_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv", use_container_width=True)

        if not users_df.empty:
            csv = users_df.to_csv(index=False).encode('utf-8')
            st.download_button("⬇️ Baixar Todos os Usuários (CSV)", csv, f"usuarios_completo_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv", use_container_width=True)

        if obras:
            csv = pd.DataFrame(obras).to_csv(index=False).encode('utf-8')
            st.download_button("⬇️ Baixar Todas as Obras (CSV)", csv, f"obras_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv", use_container_width=True)

def show_export_users():
    st.markdown("### 👥 Exportar Dados por Usuário")
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
            st.markdown("##### 📋 Questionário")
            html = generate_user_questionnaire_report(selected_user)
            if html:
                st.download_button("⬇️ Baixar Respostas (HTML/PDF)", html, f"questionario_{selected_user}.html", "text/html", use_container_width=True)

            user_data = users_df[users_df['user_id'] == selected_user]
            if not user_data.empty:
                csv = user_data.to_csv(index=False).encode('utf-8')
                st.download_button("⬇️ Baixar Respostas (CSV)", csv, f"questionario_{selected_user}.csv", "text/csv", use_container_width=True)

        with col2:
            st.markdown("##### 🏷️ Tags Criadas")
            html = generate_user_tags_report(selected_user, obras)
            if html:
                st.download_button("⬇️ Baixar Tags (HTML/PDF)", html, f"tags_{selected_user}.html", "text/html", use_container_width=True)

            user_tags = get_user_tags(selected_user)
            if not user_tags.empty:
                csv = user_tags.to_csv(index=False).encode('utf-8')
                st.download_button("⬇️ Baixar Tags (CSV)", csv, f"tags_{selected_user}.csv", "text/csv", use_container_width=True)

if __name__ == "__main__":
    main()
