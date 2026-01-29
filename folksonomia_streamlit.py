import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import datetime
import hashlib
import base64
import json
import warnings
# import matplotlib.pyplot as plt # Manter comentado por enquanto, só se for realmente necessário para algo específico
# from wordcloud import WordCloud # Manter comentado, requer instalação e pode ser problemático

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

# ==================== CSS PROFISSIONAL CLARO (com letras pretas) ====================
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
        background: linear-gradient(to bottom, #f8fafc 0%, #f1f5f9 100%); /* Fundo claro */
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
        margin-top: 100px;
        padding: 2rem 3rem;
        max-width: 1600px;
        margin-left: auto;
        margin-right: auto;
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
    #MainMenu, footer, header {visibility: hidden;}
    .stDeployButton {display: none;}
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

# ==================== ANÁLISES ====================
def calculate_quality_metrics(tags_df):
    if tags_df.empty:
        return None
    metrics = {}
    # Especificidade: proporção de tags únicas em relação ao total de tags
    metrics['specificity'] = len(tags_df['tag'].unique()) / len(tags_df) * 100

    # Consistência: variação no comprimento das tags (menor variação = mais consistente)
    lengths = tags_df['tag'].str.len()
    metrics['consistency'] = 100 - (lengths.std() / lengths.mean() * 100) if lengths.mean() > 0 else 0

    # Completude: proporção de obras com um número mínimo de tags (ex: 3)
    per_obra = tags_df.groupby('obra_id').size()
    metrics['completeness'] = (per_obra >= 3).sum() / len(per_obra) * 100 if len(per_obra) > 0 else 0

    # Métrica geral ponderada
    metrics['overall'] = (
        metrics['specificity'] * 0.4 +
        metrics['consistency'] * 0.3 +
        metrics['completeness'] * 0.3
    )
    return metrics

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
            <h2 style="color: #475569; margin-top: 40px; margin-bottom: 20px; font-size: 1.5rem;">Tags Detalhadas</h2>
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
            <h2 style="color: #475569; margin-top: 40px; margin-bottom: 20px; font-size: 1.5rem;">Suas Tags Mais Utilizadas</h2>
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
    col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 1])
    with col2:
        if st.button("Explorar Obras", key="nav_obras", use_container_width=True):
            st.session_state['current_page'] = "Explorar Obras"
            st.rerun()
    with col4:
        if st.button("Área Administrativa", key="nav_admin", use_container_width=True):
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
    st.markdown("<h1 class='main-title'>Sistema Folksonomia Digital</h1>", unsafe_allow_html=True)
    st.markdown("<p class='subtitle'>Sistema de catalogação colaborativa de obras de arte<br>Complete o questionário para acessar a plataforma</p>", unsafe_allow_html=True)
    st.markdown("<div class='professional-card'>", unsafe_allow_html=True)
    st.markdown("<h2 style='color: #475569; text-align: center; margin-bottom: 2rem; font-size: 1.5rem;'>Questionário de Acesso</h2>", unsafe_allow_html=True)
    with st.form("intro_form"):
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
            if not q3.strip():
                st.error("Por favor, responda todas as perguntas para continuar!")
            else:
                st.session_state['answers'] = {"q1": q1, "q2": q2, "q3": q3}
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

    # Exportar dados do usuário
    st.markdown("<div class='professional-card'>", unsafe_allow_html=True)
    st.markdown("### Exportar Seus Dados")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        quest_html = generate_user_questionnaire_report(st.session_state['user_id'])
        if quest_html:
            st.download_button(
                "Baixar Respostas (HTML/PDF)",
                quest_html,
                f"questionario_{st.session_state['user_id']}.html",
                "text/html",
                use_container_width=True
            )
    with col2:
        users_df = load_all_users()
        if not users_df.empty:
            user_data = users_df[users_df['user_id'] == st.session_state['user_id']]
            if not user_data.empty:
                csv = user_data.to_csv(index=False).encode('utf-8')
                st.download_button(
                    "Baixar Respostas (CSV)",
                    csv,
                    f"questionario_{st.session_state['user_id']}.csv",
                    "text/csv",
                    use_container_width=True
                )
    with col3:
        tags_html = generate_user_tags_report(st.session_state['user_id'], obras)
        if tags_html:
            st.download_button(
                "Baixar Tags (HTML/PDF)",
                tags_html,
                f"tags_{st.session_state['user_id']}.html",
                "text/html",
                use_container_width=True
            )
    with col4:
        user_tags_df = get_user_tags(st.session_state['user_id'])
        if not user_tags_df.empty:
            csv = user_tags_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                "Baixar Tags (CSV)",
                csv,
                f"tags_{st.session_state['user_id']}.csv",
                "text/csv",
                use_container_width=True
            )
    st.markdown("</div>", unsafe_allow_html=True)

    # Filtros
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
                    <p style='color: #64748b; font-size: 0.9rem; margin: 0.3rem 0;'>{obra['artista']}</p>
                    <p style='color: #94a3b8; font-size: 0.85rem;'>{obra['ano']}</p>
                </div>
            </div>
            """, unsafe_allow_html=True)
            if st.button(f"Adicionar Tag", key=f"btn_{obra['id']}", use_container_width=True):
                st.session_state['selected_obra'] = obra
                st.rerun()

            if 'selected_obra' in st.session_state and st.session_state['selected_obra']['id'] == obra['id']:
                with st.form(f"tag_form_{obra['id']}"):
                    tag = st.text_input("Sua tag:", key=f"tag_{obra['id']}", placeholder="Ex: impressionismo")
                    col1, col2 = st.columns(2)
                    with col1:
                        submitted = st.form_submit_button("Enviar", use_container_width=True)
                    with col2:
                        cancel = st.form_submit_button("Cancelar", use_container_width=True)
                    if submitted and tag:
                        save_tag(st.session_state['user_id'], obra['id'], tag)
                        st.success(f"Tag '{tag}' adicionada com sucesso!")
                        del st.session_state['selected_obra']
                        st.rerun()
                    if cancel:
                        del st.session_state['selected_obra']
                        st.rerun()
            # Mostrar apenas tags do usuário
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
            st.markdown("<h2 style='color: #475569; text-align: center; margin-bottom: 2rem;'>Login Administrativo</h2>", unsafe_allow_html=True)
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

        # Tabs atualizadas: "Qualidade" mudou para "Dados"
        tabs = st.tabs(["Visão Geral", "Análises", "Dados", "Obras", "Exportar Completo", "Exportar Usuários"])

        with tabs[0]:
            show_overview()
        with tabs[1]:
            show_analysis()
        with tabs[2]: # Chamando a nova função show_data_analysis
            show_data_analysis()
        with tabs[3]:
            show_manage_obras()
        with tabs[4]:
            show_export_complete()
        with tabs[5]:
            show_export_users()

        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button("Sair do Sistema", use_container_width=True):
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
    st.markdown("### Análises Detalhadas")
    tags_df = load_all_tags()
    if tags_df.empty:
        st.info("Não há dados suficientes para análises.")
        return

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Distribuição de Tags")
        # Removendo a opção de "Pizza" para evitar Plotly
        chart_type_tags = st.selectbox("Escolha o tipo de gráfico para Tags:", ["Barras", "Tabela"], key="chart_type_tags_no_plotly")
        counts = tags_df['tag'].value_counts().head(15) # Aumentei para 15 para mais dados

        if chart_type_tags == "Barras":
            st.bar_chart(counts)
        elif chart_type_tags == "Tabela":
            st.dataframe(counts.reset_index().rename(columns={'index': 'Tag', 'tag': 'Frequência'}), use_container_width=True, hide_index=True)

    with col2:
        st.markdown("#### Tags por Obra")
        # Removendo a opção de "Pizza" para evitar Plotly
        chart_type_obras = st.selectbox("Escolha o tipo de gráfico para Obras:", ["Barras", "Tabela"], key="chart_type_obras_no_plotly")
        per_obra = tags_df.groupby('obra_id').size()
        obras = load_obras()
        od = {o['id']: o['titulo'] for o in obras}
        per_obra_named = per_obra.rename(index=od) # Mapeia IDs para títulos

        if chart_type_obras == "Barras":
            st.bar_chart(per_obra_named)
        elif chart_type_obras == "Tabela":
            st.dataframe(per_obra_named.reset_index().rename(columns={'index': 'Obra', 0: 'Frequência'}), use_container_width=True, hide_index=True)

    st.markdown("#### Tags Raras (Top 10 menos usadas)")
    rare_tags = tags_df['tag'].value_counts().tail(10).reset_index()
    rare_tags.columns = ['Tag', 'Quantidade']
    st.dataframe(rare_tags, use_container_width=True, hide_index=True)

def show_data_analysis(): # Função renomeada de show_quality para show_data_analysis
    st.markdown("### Análise de Dados e Qualidade") # Novo título
    tags_df = load_all_tags()
    users_df = load_all_users()
    obras = load_obras()

    if tags_df.empty and users_df.empty:
        st.info("Sem dados suficientes para análise.")
        return

    tab_metrics, tab_patterns, tab_questionnaire = st.tabs(["Métricas de Qualidade", "Padrões e Diversificação", "Análise do Questionário"])

    with tab_metrics:
        st.markdown("#### Métricas de Qualidade das Tags")
        quality = calculate_quality_metrics(tags_df)
        if quality:
            score = quality['overall']
            status = 'status-high' if score >= 70 else 'status-medium' if score >= 50 else 'status-low'
            status_text = 'Excelente' if score >= 70 else 'Bom' if score >= 50 else 'Regular'
            st.markdown(f"""
            <div class='professional-card' style='text-align: center; padding: 3rem;'>
                <h1 style='font-size: 5rem; color: #475569;'>{score:.1f}</h1>
                <span class='status-badge {status}'>{status_text}</span>
            </div>
            """, unsafe_allow_html=True)
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Especificidade", f"{quality['specificity']:.1f}%", help="Porcentagem de tags únicas em relação ao total de tags. Maior = mais específico.")
            with col2:
                st.metric("Consistência", f"{quality['consistency']:.1f}%", help="Medida da uniformidade no comprimento das tags. Maior = mais consistente.")
            with col3:
                st.metric("Completude", f"{quality['completeness']:.1f}%", help="Porcentagem de obras com pelo menos 3 tags. Maior = mais completo.")
        else:
            st.info("Não há tags para calcular as métricas de qualidade.")

    with tab_patterns:
        st.markdown("#### Análise de Padrões e Diversificação")
        if not tags_df.empty:
            st.markdown("##### Tags Repetidas e Frequência")
            st.dataframe(tags_df['tag'].value_counts().reset_index().rename(columns={'index': 'Tag', 'tag': 'Frequência'}), use_container_width=True, hide_index=True)

            st.markdown("##### Diversificação de Tags por Obra")
            tags_per_obra = tags_df.groupby('obra_id')['tag'].nunique().reset_index()
            tags_per_obra.columns = ['obra_id', 'Tags Únicas']
            obras_dict = {o['id']: o['titulo'] for o in obras}
            tags_per_obra['Obra'] = tags_per_obra['obra_id'].map(obras_dict)
            st.dataframe(tags_per_obra[['Obra', 'Tags Únicas']].sort_values('Tags Únicas', ascending=False), use_container_width=True, hide_index=True)

            st.markdown("##### Diversificação de Tags por Usuário")
            tags_per_user = tags_df.groupby('user_id')['tag'].nunique().reset_index()
            tags_per_user.columns = ['user_id', 'Tags Únicas']
            st.dataframe(tags_per_user.sort_values('Tags Únicas', ascending=False), use_container_width=True, hide_index=True)

            st.markdown("##### Análise de Similaridade de Tags (Exemplo - requer lógica avançada)")
            st.info("Para identificar sinônimos ou tags muito similares, seria necessário implementar algoritmos de similaridade textual (ex: embeddings de palavras, distância de Levenshtein).")

        else:
            st.info("Não há tags para analisar padrões e diversificação.")

    with tab_questionnaire:
        st.markdown("#### Análise do Questionário de Usuários")
        if not users_df.empty:
            st.markdown("##### Distribuição das Respostas")
            st.write("1. Qual é o seu nível de familiaridade com museus?")
            # Usando st.bar_chart para a distribuição das respostas do questionário
            st.bar_chart(users_df['q1'].value_counts())

            st.write("2. Você já ouviu falar sobre documentação museológica?")
            st.bar_chart(users_df['q2'].value_counts())

            st.markdown("##### Cruzamento de Dados: Familiaridade com Museus vs. Número de Tags Criadas")
            if not tags_df.empty:
                user_tag_counts = tags_df.groupby('user_id').size().reset_index(name='Total_Tags')
                merged_df = pd.merge(users_df, user_tag_counts, on='user_id', how='left').fillna(0)
                avg_tags_by_familiarity = merged_df.groupby('q1')['Total_Tags'].mean().sort_values(ascending=False)
                st.bar_chart(avg_tags_by_familiarity)
                st.write("Média de tags criadas por nível de familiaridade com museus:")
                st.dataframe(avg_tags_by_familiarity.reset_index(), use_container_width=True, hide_index=True)
            else:
                st.info("Não há tags para cruzar com os dados do questionário.")

            st.markdown("##### Respostas Abertas (Q3)")
            st.dataframe(users_df[['user_id', 'q3', 'timestamp']].sort_values('timestamp', ascending=False), use_container_width=True, hide_index=True)
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
    selected_user = st.selectbox("Selecione o usuário:", user_ids)

    if selected_user:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### Questionário")
            html = generate_user_questionnaire_report(selected_user)
            if html:
                st.download_button("Baixar Respostas (HTML/PDF)", html, f"questionario_{selected_user}.html", "text/html", use_container_width=True)
            user_data = users_df[users_df['user_id'] == selected_user]
            if not user_data.empty:
                csv = user_data.to_csv(index=False).encode('utf-8')
                st.download_button("Baixar Respostas (CSV)", csv, f"questionario_{selected_user}.csv", "text/csv", use_container_width=True)
        with col2:
            st.markdown("#### Tags Criadas")
            html = generate_user_tags_report(selected_user, obras)
            if html:
                st.download_button("Baixar Tags (HTML/PDF)", html, f"tags_{selected_user}.html", "text/html", use_container_width=True)
            user_tags = get_user_tags(selected_user)
            if not user_tags.empty:
                csv = user_tags.to_csv(index=False).encode('utf-8')
                st.download_button("Baixar Tags (CSV)", csv, f"tags_{selected_user}.csv", "text/csv", use_container_width=True)

if __name__ == "__main__":
    main()
