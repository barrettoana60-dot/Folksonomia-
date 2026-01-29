import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import datetime
import hashlib
import base64
import json
import warnings
import plotly.express as px # Reintroduzindo Plotly para gráficos de pizza

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
        except json.JSONDecodeError: # Adicionado tratamento para JSON inválido
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

# ==================== CSS PROFISSIONAL CLARO (com letras pretas, liquid glass e animações) ====================
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
        /* Fundo branco acinzentado sutil */
        background: linear-gradient(to bottom, #f8f9fa 0%, #e9ecef 100%); 
        color: #1e293b; /* Cor de texto padrão escura */
    }
    .top-navbar {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        z-index: 9999;
        background: white;
        border-bottom: 2px solid #e2e8f0;
        padding: 1.2rem 3rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
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
    /* Estilo para os botões principais de navegação (Explorar Obras, Área Administrativa) */
    .liquid-glass-button {
        background: rgba(255, 255, 255, 0.3) !important; /* Fundo semi-transparente */
        border: 1px solid rgba(255, 255, 255, 0.6) !important; /* Borda clara */
        backdrop-filter: blur(10px) !important; /* Efeito de vidro embaçado */
        -webkit-backdrop-filter: blur(10px) !important; /* Compatibilidade Safari */
        color: #1e293b !important; /* Texto preto */
        border-radius: 12px !important; /* Bordas mais arredondadas */
        padding: 1rem 2.5rem !important; /* Padding generoso */
        font-weight: 600 !important;
        font-size: 1.1rem !important;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1) !important; /* Sombra suave */
        transition: all 0.3s ease !important; /* Animação suave */
        cursor: pointer !important;
        display: inline-flex; /* Para centralizar o texto */
        align-items: center;
        justify-content: center;
        text-decoration: none; /* Remover sublinhado de links */
    }
    .liquid-glass-button:hover {
        background: rgba(255, 255, 255, 0.5) !important; /* Mais transparente no hover */
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.15) !important; /* Sombra mais pronunciada */
        transform: translateY(-3px) scale(1.02) !important; /* Leve levantamento e aumento */
        border-color: rgba(255, 255, 255, 0.8) !important; /* Borda mais visível */
    }

    .professional-card {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 2rem;
        margin: 1.5rem 0;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
        transition: all 0.3s ease;
    }
    .professional-card:hover {
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
        border-color: #cbd5e1;
    }
    .obra-card {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        overflow: hidden;
        transition: all 0.3s ease;
        cursor: pointer;
    }
    .obra-card:hover {
        box-shadow: 0 8px 20px rgba(0, 0, 0, 0.1);
        transform: translateY(-4px);
        border-color: #94a3b8;
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
        color: #1e293b; /* Título principal em preto */
        font-size: 2.5rem;
        font-weight: 700;
        text-align: center;
        margin: 2rem 0 1rem 0;
        letter-spacing: -0.5px;
    }
    .subtitle {
        color: #64748b; /* Subtítulo em cinza escuro */
        font-size: 1.1rem;
        text-align: center;
        margin-bottom: 2.5rem;
        line-height: 1.6;
    }
    .tag-badge {
        display: inline-block;
        background: #f1f5f9;
        border: 1px solid #cbd5e1;
        color: #475569; /* Texto da tag em cinza escuro */
        padding: 0.5rem 1rem;
        border-radius: 6px;
        margin: 0.3rem;
        font-size: 0.85rem;
        font-weight: 500;
        transition: all 0.2s ease;
    }
    .tag-badge:hover {
        background: #e2e8f0;
        border-color: #94a3b8;
    }
    .metric-card {
        background: linear-gradient(135deg, #475569 0%, #334155 100%);
        border: none;
        border-radius: 10px;
        padding: 2rem;
        text-align: center;
        color: white;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        transition: all 0.3s ease;
    }
    .metric-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 8px 20px rgba(0, 0, 0, 0.15);
    }
    .metric-value {
        font-size: 3rem;
        font-weight: 700;
        margin: 0.5rem 0;
    }
    .metric-label {
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-weight: 600;
        opacity: 0.9;
    }
    /* Botões Streamlit padrão (para formulários, etc.) */
    .stButton button {
        background: #475569 !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.8rem 2rem !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1) !important;
    }
    .stButton button:hover {
        background: #334155 !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15) !important;
        transform: translateY(-2px) !important;
    }
    .stTextInput input, .stTextArea textarea, .stSelectbox select {
        background: white !important;
        border: 1px solid #cbd5e1 !important;
        color: #1e293b !important; /* Input text em preto */
        border-radius: 8px !important;
        padding: 0.8rem !important;
        transition: all 0.2s ease !important;
    }
    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: #64748b !important;
        box-shadow: 0 0 0 3px rgba(100, 116, 139, 0.1) !important;
    }
    label {
        color: #475569 !important; /* Labels em cinza escuro */
        font-weight: 600 !important;
        font-size: 0.9rem !important;
        margin-bottom: 0.5rem !important;
    }
    /* Tabs Streamlit (para navegação secundária) */
    .stTabs [data-baseweb="tab"] {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 8px 8px 0 0;
        color: #64748b; /* Tabs inativas em cinza */
        padding: 0.8rem 1.5rem;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background: #475569 !important;
        color: white !important; /* Tab ativa em branco */
        border-color: #475569 !important;
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
        background: #dcfce7;
        border: 1px solid #86efac;
        color: #166534;
    }
    .status-medium {
        background: #fef3c7;
        border: 1px solid #fcd34d;
        color: #92400e;
    }
    .status-low {
        background: #fee2e2;
        border: 1px solid #fca5a5;
        color: #991b1b;
    }
    /* Cores para st.info, st.success, st.warning, st.error para texto escuro */
    .stAlert {
        color: #1e293b !important; /* Texto escuro para alertas */
    }
    .stAlert.info {
        background-color: #e0f2fe !important; /* Azul claro */
        border-left: 5px solid #0ea5e9 !important;
    }
    .stAlert.success {
        background-color: #dcfce7 !important; /* Verde claro */
        border-left: 5px solid #22c55e !important;
    }
    .stAlert.warning {
        background-color: #fef3c7 !important; /* Amarelo claro */
        border-left: 5px solid #f59e0b !important;
    }
    .stAlert.error {
        background-color: #fee2e2 !important; /* Vermelho claro */
        border-left: 5px solid #ef4444 !important;
    }

    #MainMenu, footer, header {visibility: hidden;}
    .stDeployButton {display: none;}
    /* Removendo o sidebar completamente para controlar a navegação manualmente */
    [data-testid="stSidebar"] {display: none;} 

    h1, h2, h3, h4, h5, h6 {
        color: #1e293b; /* Títulos em preto */
        font-weight: 600;
    }
    .dataframe {
        border: 1px solid #e2e8f0 !important;
        border-radius: 8px !important;
    }
    @media (max-width: 768px) {
        .main-title { font-size: 2rem; }
        .main-content { margin-top: 120px; padding: 1rem; }
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
    # CORREÇÃO AQUI: Removido o 't' duplicado
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

# ==================== ANÁLISES (Função calculate_quality_metrics removida ou esvaziada) ====================
# A função calculate_quality_metrics não é mais usada, pois as métricas genéricas foram removidas.
# Se você quiser adicionar métricas específicas no futuro, pode recriá-la.

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
            body {{ font-family: 'Arial', sans-serif; background: #f8fafc; padding: 40px; color: #1e293b; }}
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
            body {{ font-family: 'Arial', sans-serif; background: #f8fafc; padding: 40px; color: #1e293b; }}
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
            <h2 style="color: #1e293b; margin-top: 40px; margin-bottom: 20px; font-size: 1.5rem;">Top 10 Tags Mais Usadas por Este Usuário</h2>
            <table>
                <thead>
                    <tr>
                        <th>Tag</th>
                        <th>Frequência</th>
                    </tr>
                </thead>
                <tbody>
    """
    for tag, count in top_tags.items():
        html += f"""
                    <tr>
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

# ==================== PÁGINAS DO APP ====================
def main():
    load_custom_css()
    check_and_init_admin()

    if 'user_id' not in st.session_state:
        st.session_state['user_id'] = generate_user_id()
        st.session_state['step'] = 'intro' # 'intro', 'questionnaire', 'completed'

    # Header fixo com logo
    st.markdown(f"""
    <div class='top-navbar'>
        <span class='navbar-logo'>Sistema Folksonomia Digital</span>
        <div>
            {f"<span style='color: #475569; font-weight: 600; margin-right: 1rem;'>Olá, {st.session_state.get('answers', {}).get('nome', 'Visitante')}!</span>" if st.session_state.get('step') == 'completed' else ''}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Conteúdo principal
    st.markdown("<div class='main-content'>", unsafe_allow_html=True)

    # Navegação principal abaixo da barra branca
    if st.session_state.get('step') == 'completed' or st.session_state.get('admin_logged_in'):
        col_nav1, col_nav2, col_nav3 = st.columns([1, 1, 4]) # Ajuste para centralizar e dar espaço
        with col_nav1:
            if st.button("Explorar Obras", key="nav_obras", use_container_width=True, help="Ver e taguear obras de arte", type="secondary"):
                st.session_state['current_page'] = 'obras'
                st.rerun()
        with col_nav2:
            if st.button("Área Administrativa", key="nav_admin", use_container_width=True, help="Gerenciar obras e analisar dados", type="secondary"):
                st.session_state['current_page'] = 'admin'
                st.rerun()
        # Adicionar o estilo liquid-glass-button aos botões de navegação
        st.markdown("""
        <style>
            [data-testid="stButton"] > button[aria-label="Explorar Obras"] {
                background: rgba(255, 255, 255, 0.3) !important;
                border: 1px solid rgba(255, 255, 255, 0.6) !important;
                backdrop-filter: blur(10px) !important;
                -webkit-backdrop-filter: blur(10px) !important;
                color: #1e293b !important;
                border-radius: 12px !important;
                padding: 1rem 2.5rem !important;
                font-weight: 600 !important;
                font-size: 1.1rem !important;
                box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1) !important;
                transition: all 0.3s ease !important;
            }
            [data-testid="stButton"] > button[aria-label="Explorar Obras"]:hover {
                background: rgba(255, 255, 255, 0.5) !important;
                box-shadow: 0 6px 20px rgba(0, 0, 0, 0.15) !important;
                transform: translateY(-3px) scale(1.02) !important;
                border-color: rgba(255, 255, 255, 0.8) !important;
            }
            [data-testid="stButton"] > button[aria-label="Área Administrativa"] {
                background: rgba(255, 255, 255, 0.3) !important;
                border: 1px solid rgba(255, 255, 255, 0.6) !important;
                backdrop-filter: blur(10px) !important;
                -webkit-backdrop-filter: blur(10px) !important;
                color: #1e293b !important;
                border-radius: 12px !important;
                padding: 1rem 2.5rem !important;
                font-weight: 600 !important;
                font-size: 1.1rem !important;
                box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1) !important;
                transition: all 0.3s ease !important;
            }
            [data-testid="stButton"] > button[aria-label="Área Administrativa"]:hover {
                background: rgba(255, 255, 255, 0.5) !important;
                box-shadow: 0 6px 20px rgba(0, 0, 0, 0.15) !important;
                transform: translateY(-3px) scale(1.02) !important;
                border-color: rgba(255, 255, 255, 0.8) !important;
            }
        </style>
        """, unsafe_allow_html=True)
        st.markdown("<div style='margin-top: 2rem;'></div>", unsafe_allow_html=True) # Espaçamento abaixo dos botões

    if st.session_state['step'] == 'intro':
        show_intro()
    elif st.session_state['step'] == 'completed':
        if 'current_page' not in st.session_state:
            st.session_state['current_page'] = 'obras' # Página padrão após o questionário

        if st.session_state['current_page'] == 'obras':
            show_obras()
        elif st.session_state['current_page'] == 'admin':
            show_admin()

    st.markdown("</div>", unsafe_allow_html=True) # Fecha main-content

if __name__ == "__main__":
    main()
