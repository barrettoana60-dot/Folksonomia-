import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import datetime
import hashlib
import base64
import json
import warnings
import plotly.express as px # Importar Plotly para gráficos de barras avançados

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

# ==================== CSS MODERNO CINZA-BRANCO E DINÂMICO ====================
def load_custom_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    * { 
        margin: 0; 
        padding: 0; 
        box-sizing: border-box; 
        font-family: 'Inter', sans-serif !important; 
    }
    .stApp {
        background: #f0f2f5; /* Cinza muito claro, quase branco */
        color: #2c3e50; /* Cor de texto padrão escura */
    }
    .top-navbar {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        z-index: 9999;
        background: #ffffff; /* Branco puro para a barra superior */
        border-bottom: 1px solid #e0e6ed; /* Borda suave */
        padding: 1.2rem 3rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05); /* Sombra sutil */
    }
    .navbar-logo {
        font-size: 1.6rem;
        font-weight: 800;
        color: #2c3e50; /* Logo em cinza escuro */
        letter-spacing: -0.8px;
    }
    .main-content {
        margin-top: 100px; /* Ajuste para a barra fixa */
        padding: 2rem 3rem;
        max-width: 1600px;
        margin-left: auto;
        margin-right: auto;
    }
    .professional-card {
        background: #ffffff; /* Branco para os cards */
        border: 1px solid #e0e6ed;
        border-radius: 12px;
        padding: 2rem;
        margin: 1.5rem 0;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
        transition: all 0.3s ease;
    }
    .professional-card:hover {
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
        border-color: #cdd5df;
        transform: translateY(-2px);
    }
    .obra-card {
        background: #ffffff;
        border: 1px solid #e0e6ed;
        border-radius: 12px;
        overflow: hidden;
        transition: all 0.3s ease;
        cursor: pointer;
        box-shadow: 0 3px 10px rgba(0, 0, 0, 0.04);
    }
    .obra-card:hover {
        box-shadow: 0 6px 18px rgba(0, 0, 0, 0.08);
        transform: translateY(-4px);
        border-color: #aeb8c4;
    }
    .obra-card img {
        width: 100%;
        height: 240px;
        object-fit: cover;
        transition: transform 0.3s ease;
    }
    .obra-card:hover img {
        transform: scale(1.05);
    }
    .main-title {
        color: #2c3e50;
        font-size: 2.6rem;
        font-weight: 800;
        text-align: center;
        margin: 2.5rem 0 1.2rem 0;
        letter-spacing: -0.8px;
    }
    .subtitle {
        color: #7f8c8d; /* Cinza médio */
        font-size: 1.1rem;
        text-align: center;
        margin-bottom: 3rem;
        line-height: 1.6;
    }
    .tag-badge {
        display: inline-block;
        background: #ecf0f1; /* Cinza claro */
        border: 1px solid #dce0e6;
        color: #34495e; /* Cinza escuro */
        padding: 0.5rem 1rem;
        border-radius: 8px;
        margin: 0.3rem;
        font-size: 0.85rem;
        font-weight: 600;
        transition: all 0.2s ease;
    }
    .tag-badge:hover {
        background: #dce0e6;
        border-color: #bdc3c7;
        transform: translateY(-1px);
    }
    .metric-card {
        background: linear-gradient(135deg, #34495e 0%, #2c3e50 100%); /* Gradiente de cinza escuro */
        border: none;
        border-radius: 12px;
        padding: 2rem;
        text-align: center;
        color: white;
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.15);
        transition: all 0.3s ease;
    }
    .metric-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
    }
    .metric-value {
        font-size: 3.2rem;
        font-weight: 800;
        margin: 0.5rem 0;
    }
    .metric-label {
        font-size: 0.95rem;
        text-transform: uppercase;
        letter-spacing: 1.2px;
        font-weight: 700;
        opacity: 0.9;
    }
    .stButton button {
        background: linear-gradient(145deg, #3498db 0%, #2980b9 100%) !important; /* Azul vibrante para botões */
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 0.9rem 2.2rem !important;
        font-weight: 700 !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 3px 10px rgba(0, 0, 0, 0.1) !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .stButton button:hover {
        background: linear-gradient(145deg, #2980b9 0%, #2c3e50 100%) !important; /* Azul mais escuro no hover */
        box-shadow: 0 6px 18px rgba(0, 0, 0, 0.15) !important;
        transform: translateY(-2px) !important;
    }
    .stTextInput input, .stTextArea textarea, .stSelectbox select {
        background: #ffffff !important;
        border: 1px solid #dce0e6 !important;
        color: #2c3e50 !important;
        border-radius: 10px !important;
        padding: 0.8rem !important;
        transition: all 0.2s ease !important;
    }
    .stTextInput input:focus, .stTextArea textarea:focus, .stSelectbox select:focus {
        border-color: #3498db !important; /* Borda azul no foco */
        box-shadow: 0 0 0 3px rgba(52, 152, 219, 0.2) !important;
    }
    label {
        color: #34495e !important;
        font-weight: 700 !important;
        font-size: 0.9rem !important;
        margin-bottom: 0.5rem !important;
    }
    .stTabs [data-baseweb="tab"] {
        background: #ecf0f1; /* Cinza claro para tabs inativas */
        border: 1px solid #dce0e6;
        border-radius: 8px 8px 0 0;
        color: #7f8c8d;
        padding: 0.8rem 1.5rem;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(145deg, #3498db 0%, #2980b9 100%) !important; /* Azul para tab ativa */
        color: white !important;
        border-color: #3498db !important;
        box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.1);
    }
    .status-badge {
        display: inline-block;
        padding: 0.5rem 1rem;
        border-radius: 6px;
        font-size: 0.85rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .status-high {
        background: #d4edda; /* Verde claro */
        border: 1px solid #28a745;
        color: #155724;
    }
    .status-medium {
        background: #fff3cd; /* Amarelo claro */
        border: 1px solid #ffc107;
        color: #856404;
    }
    .status-low {
        background: #f8d7da; /* Vermelho claro */
        border: 1px solid #dc3545;
        color: #721c24;
    }
    /* Cores para st.info, st.success, st.warning, st.error */
    .stAlert {
        color: #2c3e50 !important;
        border-radius: 10px !important;
    }
    .stAlert.info {
        background-color: #e7f3ff !important; /* Azul claro */
        border-left: 5px solid #007bff !important;
    }
    .stAlert.success {
        background-color: #d4edda !important; /* Verde claro */
        border-left: 5px solid #28a745 !important;
    }
    .stAlert.warning {
        background-color: #fff3cd !important; /* Amarelo claro */
        border-left: 5px solid #ffc107 !important;
    }
    .stAlert.error {
        background-color: #f8d7da !important; /* Vermelho claro */
        border-left: 5px solid #dc3545 !important;
    }

    #MainMenu, footer, header {visibility: hidden;}
    .stDeployButton {display: none;}
    [data-testid="stSidebar"] {display: none;} 

    h1, h2, h3, h4, h5, h6 {
        color: #2c3e50;
        font-weight: 700;
    }
    .dataframe {
        border: 1px solid #e0e6ed !important;
        border-radius: 10px !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.03);
        background: #ffffff;
    }

    /* Estilo para os botões de navegação principais (Explorar Obras, Área Administrativa) */
    .main-nav-buttons-container {
        display: flex;
        justify-content: center;
        gap: 1.5rem;
        margin-bottom: 2rem; /* Espaço abaixo dos botões */
        padding-top: 1rem; /* Espaço acima dos botões */
        border-bottom: 1px solid #e0e6ed; /* Linha sutil para separar do conteúdo */
        padding-bottom: 1.5rem;
    }

    .main-nav-button {
        background: linear-gradient(145deg, #3498db 0%, #2980b9 100%) !important; /* Azul vibrante */
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 1rem 2.5rem !important;
        font-weight: 700 !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 3px 10px rgba(0, 0, 0, 0.1) !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        cursor: pointer;
        text-align: center;
        text-decoration: none;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-width: 200px; /* Largura mínima para botões */
    }

    .main-nav-button:hover {
        background: linear-gradient(145deg, #2980b9 0%, #2c3e50 100%) !important;
        box-shadow: 0 6px 18px rgba(0, 0, 0, 0.15) !important;
        transform: translateY(-2px) !important;
    }

    .main-nav-button.active {
        background: linear-gradient(145deg, #2c3e50 0%, #1c2833 100%) !important; /* Cinza escuro para o ativo */
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2) !important;
        transform: translateY(-1px) !important;
        border: 2px solid #7f8c8d !important; /* Borda sutil para destaque */
    }

    @media (max-width: 768px) {
        .main-title { font-size: 2rem; }
        .main-content { margin-top: 120px; padding: 1rem; }
        .top-navbar { padding: 1rem 1.5rem; }
        .main-nav-buttons-container {
            flex-direction: column;
            gap: 0.8rem;
            padding: 1rem;
        }
        .main-nav-button {
            min-width: unset;
            width: 100%;
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
            body {{ font-family: 'Inter', sans-serif; background: #f0f2f5; padding: 40px; color: #2c3e50; }}
            .container {{ max-width: 900px; margin: 0 auto; background: white; padding: 50px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.08); }}
            h1 {{ color: #2c3e50; text-align: center; margin-bottom: 15px; font-size: 2.2rem; border-bottom: 3px solid #34495e; padding-bottom: 20px; }}
            .header-info {{ text-align: center; color: #7f8c8d; margin-bottom: 40px; font-size: 0.95rem; }}
            .question-block {{ margin: 30px 0; padding: 25px; background: #ecf0f1; border-left: 4px solid #3498db; border-radius: 8px; }}
            .question {{ color: #34495e; font-weight: 700; font-size: 1.1rem; margin-bottom: 12px; }}
            .answer {{ color: #2c3e50; font-size: 1rem; line-height: 1.7; padding: 10px 0; }}
            .footer {{ text-align: center; margin-top: 50px; padding-top: 25px; border-top: 2px solid #e0e6ed; color: #aeb8c4; font-size: 0.85rem; }}
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
            body {{ font-family: 'Inter', sans-serif; background: #f0f2f5; padding: 40px; color: #2c3e50; }}
            .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 50px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.08); }}
            h1 {{ color: #2c3e50; text-align: center; margin-bottom: 15px; font-size: 2.2rem; border-bottom: 3px solid #34495e; padding-bottom: 20px; }}
            .header-info {{ text-align: center; color: #7f8c8d; margin-bottom: 40px; font-size: 0.95rem; }}
            .stats {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin: 30px 0; }}
            .stat-box {{ background: #ecf0f1; border-left: 4px solid #3498db; padding: 20px; border-radius: 8px; text-align: center; }}
            .stat-value {{ font-size: 2.5rem; font-weight: 700; color: #34495e; }}
            .stat-label {{ color: #7f8c8d; font-size: 0.9rem; text-transform: uppercase; letter-spacing: 1px; margin-top: 8px; }}
            table {{ width: 100%; border-collapse: collapse; margin: 30px 0; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }}
            th, td {{ padding: 15px; text-align: left; border-bottom: 1px solid #e0e6ed; }}
            th {{ background: #34495e; color: white; font-weight: 700; text-transform: uppercase; font-size: 0.85rem; letter-spacing: 0.5px; }}
            tr:nth-child(even) {{ background: #ecf0f1; }}
            tr:hover {{ background: #dce0e6; }}
            .tag-highlight {{ background: #dce0e6; padding: 5px 12px; border-radius: 6px; border: 1px solid #bdc3c7; font-weight: 600; }}
            .footer {{ text-align: center; margin-top: 50px; padding-top: 25px; border-top: 2px solid #e0e6ed; color: #aeb8c4; font-size: 0.85rem; }}
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
            <h2 style="color: #2c3e50; margin-top: 40px; margin-bottom: 20px; font-size: 1.5rem;">Tags Detalhadas</h2>
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
            <h2 style="color: #2c3e50; margin-top: 40px; margin-bottom: 20px; font-size: 1.5rem;">Suas Tags Mais Utilizadas</h2>
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

        # Nova navegação principal com botões no topo do conteúdo
        st.markdown("<div class='main-nav-buttons-container'>", unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Explorar Obras", key="nav_explorar_obras", use_container_width=True):
                st.session_state['current_page'] = "Explorar Obras"
                st.rerun()
            # Adiciona CSS para o botão ativo
            if st.session_state['current_page'] == "Explorar Obras":
                st.markdown(f"""
                    <style>
                        div[data-testid="stVerticalBlock"] > div > div > div > div:nth-child(1) > div > button {{
                            background: linear-gradient(145deg, #2c3e50 0%, #1c2833 100%) !important;
                            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2) !important;
                            transform: translateY(-1px) !important;
                            border: 2px solid #7f8c8d !important;
                        }}
                    </style>
                """, unsafe_allow_html=True)

        with col2:
            if st.button("Área Administrativa", key="nav_area_admin", use_container_width=True):
                st.session_state['current_page'] = "Área Administrativa"
                st.rerun()
            # Adiciona CSS para o botão ativo
            if st.session_state['current_page'] == "Área Administrativa":
                st.markdown(f"""
                    <style>
                        div[data-testid="stVerticalBlock"] > div > div > div > div:nth-child(2) > div > button {{
                            background: linear-gradient(145deg, #2c3e50 0%, #1c2833 100%) !important;
                            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2) !important;
                            transform: translateY(-1px) !important;
                            border: 2px solid #7f8c8d !important;
                        }}
                    </style>
                """, unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True) # Fecha o container dos botões de navegação

        # Conteúdo principal da página
        if st.session_state['current_page'] == "Explorar Obras":
            show_obras()
        elif st.session_state['current_page'] == "Área Administrativa":
            show_admin()

        st.markdown("</div>", unsafe_allow_html=True)


def show_intro():
    st.markdown("<div class='main-content'>", unsafe_allow_html=True)
    st.markdown("<h1 class='main-title'>Sistema Folksonomia Digital</h1>", unsafe_allow_html=True)
    st.markdown("<p class='subtitle'>Sistema de catalogação colaborativa de obras de arte<br>Complete o questionário para acessar a plataforma</p>", unsafe_allow_html=True)
    st.markdown("<div class='professional-card'>", unsafe_allow_html=True)
    st.markdown("<h2 style='color: #2c3e50; text-align: center; margin-bottom: 2rem; font-size: 1.5rem;'>Questionário de Acesso</h2>", unsafe_allow_html=True)
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

    st.markdown(f"<div style='text-align: center; color: #7f8c8d; margin: 2rem 0; font-size: 1.1rem;'>Exibindo <strong style='color: #34495e;'>{len(filtered)}</strong> obra(s)</div>", unsafe_allow_html=True)

    cols = st.columns(3)
    for i, obra in enumerate(filtered):
        with cols[i % 3]:
            st.markdown(f"""
            <div class='obra-card'>
                <img src='{obra['imagem']}' alt='{obra['titulo']}' />
                <div style='padding: 1.5rem;'>
                    <h3 style='color: #2c3e50; font-size: 1.2rem; font-weight: 700; margin-bottom: 0.5rem;'>{obra['titulo']}</h3>
                    <p style='color: #7f8c8d; font-size: 0.9rem; margin: 0.3rem 0;'><span style='font-weight: 600;'>Artista:</span> {obra['artista']}</p>
                    <p style='color: #aeb8c4; font-size: 0.85rem;'><span style='font-weight: 600;'>Ano:</span> {obra['ano']}</p>
                </div>
            </div>
            """, unsafe_allow_html=True)

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
            st.markdown("<h2 style='color: #2c3e50; text-align: center; margin-bottom: 2rem;'>Login Administrativo</h2>", unsafe_allow_html=True)
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
        st.markdown(f"<h1 class='main-title'>Dashboard Administrativo</h1><p class='subtitle'>Bem-vindo, <strong style='color: #34495e;'>{st.session_state.get('admin_username', 'Admin')}</strong></p>", unsafe_allow_html=True)

        tabs = st.tabs(["Visão Geral", "Análises", "Dados Detalhados", "Gestão de Obras", "Exportar Completo", "Exportar Usuários"])

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
        ("Usuários Ativos", len(users_df['user_id'].unique()) if not users_df.empty else 0),
        ("Total de Tags", len(tags_df) if not tags_df.empty else 0),
        ("Tags Únicas", len(tags_df['tag'].unique()) if not tags_df.empty else 0),
        ("Obras Cadastradas", len(obras))
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
        st.markdown("### Rankings de Engajamento")
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
    else:
        st.info("Não há dados de tags para exibir rankings.")

def show_analysis():
    st.markdown("### Análises Visuais de Dados")
    tags_df = load_all_tags()
    users_df = load_all_users()
    obras = load_obras()

    if tags_df.empty and users_df.empty:
        st.info("Não há dados suficientes para análises visuais.")
        return

    st.markdown("#### Distribuição das 15 Tags Mais Frequentes")
    if not tags_df.empty:
        top_tags_counts = tags_df['tag'].value_counts().head(15).reset_index()
        top_tags_counts.columns = ['Tag', 'Frequência']
        fig = px.bar(top_tags_counts, x='Tag', y='Frequência', title='Top 15 Tags Mais Frequentes',
                     color='Frequência', color_continuous_scale=px.colors.sequential.Blues,
                     template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Não há tags para exibir a distribuição.")

    st.markdown("#### Distribuição das 10 Obras Mais Tagueadas")
    if not tags_df.empty:
        ot = tags_df.groupby('obra_id').size().reset_index(name='Total')
        od = {o['id']: o['titulo'] for o in obras}
        ot['Obra'] = ot['obra_id'].map(od)
        top_obras_counts = ot[['Obra', 'Total']].sort_values('Total', ascending=False).head(10)
        fig = px.bar(top_obras_counts, x='Obra', y='Total', title='Top 10 Obras Mais Tagueadas',
                     color='Total', color_continuous_scale=px.colors.sequential.Greens,
                     template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Não há obras tagueadas para exibir a distribuição.")

    st.markdown("#### Distribuição do Comprimento das Tags")
    if not tags_df.empty:
        tags_df['tag_length'] = tags_df['tag'].str.len()
        length_counts = tags_df['tag_length'].value_counts().sort_index().reset_index()
        length_counts.columns = ['Comprimento da Tag', 'Frequência']
        fig = px.bar(length_counts, x='Comprimento da Tag', y='Frequência', title='Distribuição do Comprimento das Tags',
                     color='Frequência', color_continuous_scale=px.colors.sequential.Purples,
                     template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)
        st.write(f"Média de comprimento das tags: **{tags_df['tag_length'].mean():.2f}** caracteres")
        st.write(f"Desvio padrão do comprimento das tags: **{tags_df['tag_length'].std():.2f}** caracteres")
    else:
        st.info("Não há tags para analisar o comprimento.")

def show_data_analysis():
    st.markdown("### Análise Detalhada de Dados e Conexões")
    tags_df = load_all_tags()
    users_df = load_all_users()
    obras = load_obras()

    if tags_df.empty and users_df.empty:
        st.info("Sem dados suficientes para análise detalhada.")
        return

    st.markdown("#### Dados de Usuários e Suas Tags")
    if not users_df.empty:
        user_tag_counts = tags_df.groupby('user_id').agg(
            total_tags=('tag', 'count'),
            tags_unicas=('tag', 'nunique'),
            obras_taguadas=('obra_id', 'nunique')
        ).reset_index()

        users_with_tags = pd.merge(users_df, user_tag_counts, on='user_id', how='left').fillna(0)
        users_with_tags['Nome do Usuário'] = users_with_tags['user_id'].apply(get_user_name_by_id)

        st.dataframe(users_with_tags[['Nome do Usuário', 'total_tags', 'tags_unicas', 'obras_taguadas', 'timestamp']].sort_values('total_tags', ascending=False), use_container_width=True, hide_index=True)
    else:
        st.info("Nenhum usuário cadastrado ou tags criadas.")

    st.markdown("#### Análise de Co-ocorrência de Tags (Padrões de Ligação)")
    st.info("Esta análise identifica quais tags são frequentemente usadas juntas em uma mesma obra, revelando padrões de tagueamento e possíveis relações semânticas.")

    if not tags_df.empty:
        # Criar uma lista de sets de tags por obra para co-ocorrência
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

            st.markdown("##### Top 20 Pares de Tags Mais Co-ocorrentes")
            st.dataframe(co_occurrence_df[['Tag 1', 'Tag 2', 'Frequência']].sort_values('Frequência', ascending=False).head(20), use_container_width=True, hide_index=True)

            # Análise mais profunda: Sugestão de tags relacionadas
            st.markdown("##### Sugestão de Tags Relacionadas (Baseado em Co-ocorrência)")
            selected_tag = st.selectbox("Selecione uma tag para ver suas co-ocorrências:", sorted(tags_df['tag'].unique().tolist()))
            if selected_tag:
                related_tags = co_occurrence_df[(co_occurrence_df['Tag 1'] == selected_tag) | (co_occurrence_df['Tag 2'] == selected_tag)]
                if not related_tags.empty:
                    # Extrair a tag oposta e somar frequências
                    related_counts = {}
                    for _, row in related_tags.iterrows():
                        other_tag = row['Tag 2'] if row['Tag 1'] == selected_tag else row['Tag 1']
                        related_counts[other_tag] = related_counts.get(other_tag, 0) + row['Frequência']

                    related_df = pd.DataFrame(related_counts.items(), columns=['Tag Relacionada', 'Frequência de Co-ocorrência']).sort_values('Frequência de Co-ocorrência', ascending=False)

                    st.dataframe(related_df, use_container_width=True, hide_index=True)

                    fig_related = px.bar(related_df.head(10), x='Tag Relacionada', y='Frequência de Co-ocorrência',
                                         title=f'Tags Mais Relacionadas a "{selected_tag}"',
                                         color='Frequência de Co-ocorrência', color_continuous_scale=px.colors.sequential.Oranges,
                                         template="plotly_white")
                    st.plotly_chart(fig_related, use_container_width=True)
                else:
                    st.info(f"Não foram encontradas co-ocorrências para a tag '{selected_tag}'.")
        else:
            st.info("Não há tags suficientes para analisar co-ocorrência.")
    else:
        st.info("Não há tags para análise detalhada de conexões.")

    st.markdown("#### Análise do Questionário de Usuários")
    if not users_df.empty:
        st.markdown("##### Distribuição das Respostas (Q1: Familiaridade com Museus)")
        q1_counts = users_df['q1'].value_counts().reset_index()
        q1_counts.columns = ['Nível de Familiaridade', 'Contagem']
        fig_q1 = px.bar(q1_counts, x='Nível de Familiaridade', y='Contagem', title='Familiaridade com Museus',
                        color='Contagem', color_continuous_scale=px.colors.sequential.Greens,
                        template="plotly_white")
        st.plotly_chart(fig_q1, use_container_width=True)

        st.markdown("##### Distribuição das Respostas (Q2: Conhecimento sobre Documentação Museológica)")
        q2_counts = users_df['q2'].value_counts().reset_index()
        q2_counts.columns = ['Nível de Conhecimento', 'Contagem']
        fig_q2 = px.bar(q2_counts, x='Nível de Conhecimento', y='Contagem', title='Conhecimento sobre Documentação Museológica',
                        color='Contagem', color_continuous_scale=px.colors.sequential.Purples,
                        template="plotly_white")
        st.plotly_chart(fig_q2, use_container_width=True)

        st.markdown("##### Correlação: Familiaridade com Museus vs. Número de Tags Criadas")
        if not tags_df.empty:
            user_tag_counts = tags_df.groupby('user_id').size().reset_index(name='Total_Tags')
            merged_df = pd.merge(users_df, user_tag_counts, on='user_id', how='left').fillna(0)
            avg_tags_by_familiarity = merged_df.groupby('q1')['Total_Tags'].mean().reset_index()
            fig_corr_q1_tags = px.bar(avg_tags_by_familiarity, x='q1', y='Total_Tags',
                                      title='Média de Tags Criadas por Nível de Familiaridade com Museus',
                                      labels={'q1':'Familiaridade com Museus', 'Total_Tags':'Média de Tags'},
                                      color='Total_Tags', color_continuous_scale=px.colors.sequential.YlGnBu,
                                      template="plotly_white")
            st.plotly_chart(fig_corr_q1_tags, use_container_width=True)
            st.dataframe(avg_tags_by_familiarity.rename(columns={'q1': 'Familiaridade com Museus', 'Total_Tags': 'Média de Tags'}), use_container_width=True, hide_index=True)
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
