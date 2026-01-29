import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import datetime
import hashlib
import base64
import json
import warnings
import plotly.express as px
import plotly.graph_objects as go
from collections import Counter
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

# ==================== CSS MODERNO E DINÂMICO ====================
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
        background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 50%, #ffffff 100%);
        animation: gradientShift 10s ease infinite;
    }

    @keyframes gradientShift {
        0%, 100% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
    }

    .top-navbar {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        z-index: 9999;
        background: rgba(255, 255, 255, 0.98);
        backdrop-filter: blur(20px);
        border-bottom: 2px solid #e9ecef;
        padding: 1.2rem 3rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
    }

    .navbar-logo {
        font-size: 1.6rem;
        font-weight: 800;
        color: #212529;
        letter-spacing: -0.5px;
        background: linear-gradient(135deg, #212529 0%, #495057 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    .main-content {
        margin-top: 100px;
        padding: 2rem 3rem;
        max-width: 1800px;
        margin-left: auto;
        margin-right: auto;
    }

    .modern-card {
        background: white;
        border: 2px solid #e9ecef;
        border-radius: 16px;
        padding: 2.5rem;
        margin: 1.5rem 0;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06);
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        position: relative;
        overflow: hidden;
    }

    .modern-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 4px;
        background: linear-gradient(90deg, #212529, #495057, #6c757d);
        transform: scaleX(0);
        transform-origin: left;
        transition: transform 0.5s ease;
    }

    .modern-card:hover::before {
        transform: scaleX(1);
    }

    .modern-card:hover {
        transform: translateY(-8px);
        box-shadow: 0 12px 32px rgba(0, 0, 0, 0.12);
        border-color: #dee2e6;
    }

    .obra-card {
        background: white;
        border: 2px solid #e9ecef;
        border-radius: 12px;
        overflow: hidden;
        transition: all 0.4s ease;
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
        background: linear-gradient(135deg, rgba(33, 37, 41, 0.05), rgba(108, 117, 125, 0.05));
        opacity: 0;
        transition: opacity 0.4s ease;
        pointer-events: none;
    }

    .obra-card:hover::after {
        opacity: 1;
    }

    .obra-card:hover {
        transform: translateY(-10px) scale(1.02);
        box-shadow: 0 16px 40px rgba(0, 0, 0, 0.15);
        border-color: #adb5bd;
    }

    .obra-card img {
        width: 100%;
        height: 260px;
        object-fit: cover;
        transition: transform 0.5s ease;
    }

    .obra-card:hover img {
        transform: scale(1.1);
    }

    .main-title {
        color: #212529;
        font-size: 3rem;
        font-weight: 800;
        text-align: center;
        margin: 2rem 0 1rem 0;
        letter-spacing: -1px;
        position: relative;
        display: inline-block;
        width: 100%;
    }

    .main-title::after {
        content: '';
        position: absolute;
        bottom: -10px;
        left: 50%;
        transform: translateX(-50%);
        width: 100px;
        height: 4px;
        background: linear-gradient(90deg, #212529, #495057);
        border-radius: 2px;
    }

    .subtitle {
        color: #495057;
        font-size: 1.2rem;
        text-align: center;
        margin-bottom: 3rem;
        line-height: 1.8;
        font-weight: 400;
    }

    .tag-badge {
        display: inline-block;
        background: linear-gradient(135deg, #f8f9fa, #e9ecef);
        border: 2px solid #dee2e6;
        color: #212529;
        padding: 0.6rem 1.2rem;
        border-radius: 8px;
        margin: 0.4rem;
        font-size: 0.9rem;
        font-weight: 600;
        transition: all 0.3s ease;
        cursor: pointer;
    }

    .tag-badge:hover {
        background: linear-gradient(135deg, #212529, #495057);
        color: white;
        border-color: #212529;
        transform: translateY(-3px);
        box-shadow: 0 6px 16px rgba(33, 37, 41, 0.2);
    }

    .metric-card {
        background: linear-gradient(135deg, #212529 0%, #343a40 100%);
        border: none;
        border-radius: 16px;
        padding: 2.5rem;
        text-align: center;
        color: white;
        box-shadow: 0 8px 24px rgba(33, 37, 41, 0.2);
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
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
        background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
        animation: rotate 20s linear infinite;
    }

    @keyframes rotate {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }

    .metric-card:hover {
        transform: translateY(-10px) scale(1.05);
        box-shadow: 0 16px 40px rgba(33, 37, 41, 0.3);
    }

    .metric-value {
        font-size: 3.5rem;
        font-weight: 900;
        margin: 0.5rem 0;
        position: relative;
        z-index: 1;
    }

    .metric-label {
        font-size: 1rem;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        font-weight: 700;
        opacity: 0.95;
        position: relative;
        z-index: 1;
    }

    .stButton button {
        background: linear-gradient(135deg, #212529 0%, #343a40 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 0.9rem 2.5rem !important;
        font-weight: 700 !important;
        font-size: 1rem !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 12px rgba(33, 37, 41, 0.15) !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
    }

    .stButton button:hover {
        background: linear-gradient(135deg, #343a40 0%, #495057 100%) !important;
        box-shadow: 0 8px 20px rgba(33, 37, 41, 0.25) !important;
        transform: translateY(-3px) !important;
    }

    .stTextInput input, .stTextArea textarea, .stSelectbox select {
        background: white !important;
        border: 2px solid #dee2e6 !important;
        color: #212529 !important;
        border-radius: 10px !important;
        padding: 1rem !important;
        transition: all 0.3s ease !important;
        font-weight: 500 !important;
    }

    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: #495057 !important;
        box-shadow: 0 0 0 4px rgba(73, 80, 87, 0.1) !important;
    }

    label {
        color: #212529 !important;
        font-weight: 700 !important;
        font-size: 1rem !important;
        margin-bottom: 0.5rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
        background: transparent;
        border-bottom: 2px solid #e9ecef;
    }

    .stTabs [data-baseweb="tab"] {
        background: white;
        border: 2px solid #dee2e6;
        border-radius: 10px 10px 0 0;
        color: #495057;
        padding: 1rem 2rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        transition: all 0.3s ease;
    }

    .stTabs [data-baseweb="tab"]:hover {
        background: #f8f9fa;
        color: #212529;
    }

    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #212529 0%, #343a40 100%) !important;
        color: white !important;
        border-color: #212529 !important;
        box-shadow: 0 4px 12px rgba(33, 37, 41, 0.2);
    }

    .status-badge {
        display: inline-block;
        padding: 0.6rem 1.2rem;
        border-radius: 8px;
        font-size: 0.9rem;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    .status-high {
        background: #d1e7dd;
        border: 2px solid #0f5132;
        color: #0f5132;
    }

    .status-medium {
        background: #fff3cd;
        border: 2px solid #997404;
        color: #997404;
    }

    .status-low {
        background: #f8d7da;
        border: 2px solid #842029;
        color: #842029;
    }

    #MainMenu, footer, header {visibility: hidden;}
    .stDeployButton {display: none;}
    [data-testid="stSidebar"] {display: none;}

    h1, h2, h3, h4, h5, h6 {
        color: #212529 !important;
        font-weight: 700 !important;
    }

    p, span, div, td, th {
        color: #212529 !important;
    }

    .dataframe {
        border: 2px solid #dee2e6 !important;
        border-radius: 10px !important;
    }

    .dataframe th {
        background: #212529 !important;
        color: white !important;
        font-weight: 700 !important;
    }

    .dataframe td {
        color: #212529 !important;
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

# ==================== ANÁLISES AVANÇADAS ====================
def analyze_tag_patterns(tags_df):
    if tags_df.empty:
        return None

    analysis = {}

    tag_counts = tags_df['tag'].value_counts()
    analysis['total_tags'] = len(tags_df)
    analysis['unique_tags'] = len(tag_counts)
    analysis['repeated_tags'] = len(tag_counts[tag_counts > 1])
    analysis['repetition_rate'] = (analysis['repeated_tags'] / analysis['unique_tags'] * 100) if analysis['unique_tags'] > 0 else 0
    analysis['most_repeated'] = tag_counts.head(10).to_dict()

    analysis['single_word'] = sum(tags_df['tag'].str.split().str.len() == 1)
    analysis['multi_word'] = sum(tags_df['tag'].str.split().str.len() > 1)
    analysis['avg_length'] = tags_df['tag'].str.len().mean()

    analysis['diversity_score'] = (analysis['unique_tags'] / analysis['total_tags'] * 100) if analysis['total_tags'] > 0 else 0

    analysis['consistency_score'] = 100 - (tags_df['tag'].str.len().std() / tags_df['tag'].str.len().mean() * 100) if tags_df['tag'].str.len().mean() > 0 else 0

    return analysis

def analyze_questionnaire_patterns(users_df):
    if users_df.empty:
        return None

    analysis = {}

    if 'q1' in users_df.columns:
        q1_counts = users_df['q1'].value_counts()
        analysis['q1_distribution'] = q1_counts.to_dict()
        analysis['q1_most_common'] = q1_counts.index[0] if len(q1_counts) > 0 else None

    if 'q2' in users_df.columns:
        q2_counts = users_df['q2'].value_counts()
        analysis['q2_distribution'] = q2_counts.to_dict()
        analysis['q2_most_common'] = q2_counts.index[0] if len(q2_counts) > 0 else None

    if 'q3' in users_df.columns:
        q3_texts = users_df['q3'].dropna()
        analysis['q3_avg_length'] = q3_texts.str.len().mean() if not q3_texts.empty else 0
        analysis['q3_total_responses'] = len(q3_texts)

        all_words = ' '.join(q3_texts.str.lower()).split()
        word_counts = Counter(all_words)
        analysis['q3_top_keywords'] = dict(word_counts.most_common(15))

    return analysis

def create_interactive_charts(data, chart_type, title):
    if chart_type == "bar":
        fig = px.bar(
            x=list(data.keys()),
            y=list(data.values()),
            title=title,
            labels={'x': 'Categoria', 'y': 'Quantidade'},
            color=list(data.values()),
            color_continuous_scale='Greys'
        )
    elif chart_type == "pie":
        fig = px.pie(
            values=list(data.values()),
            names=list(data.keys()),
            title=title,
            color_discrete_sequence=px.colors.sequential.gray
        )
    elif chart_type == "line":
        fig = px.line(
            x=list(data.keys()),
            y=list(data.values()),
            title=title,
            labels={'x': 'Categoria', 'y': 'Valor'}
        )
    else:
        fig = go.Figure()

    fig.update_layout(
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(color='#212529', size=12, family='Inter'),
        title_font=dict(size=18, color='#212529', family='Inter'),
        showlegend=True
    )

    return fig

# ==================== EXPORTAÇÃO HTML ====================
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
            body {{ font-family: 'Inter', 'Arial', sans-serif; background: #f8f9fa; padding: 40px; color: #212529; }}
            .container {{ max-width: 900px; margin: 0 auto; background: white; padding: 50px; border-radius: 12px; box-shadow: 0 4px 16px rgba(0,0,0,0.1); }}
            h1 {{ color: #212529; text-align: center; margin-bottom: 15px; font-size: 2.2rem; border-bottom: 3px solid #212529; padding-bottom: 20px; }}
            .header-info {{ text-align: center; color: #495057; margin-bottom: 40px; font-size: 0.95rem; }}
            .question-block {{ margin: 30px 0; padding: 25px; background: #f8f9fa; border-left: 4px solid #212529; border-radius: 8px; }}
            .question {{ color: #212529; font-weight: 700; font-size: 1.1rem; margin-bottom: 12px; }}
            .answer {{ color: #212529; font-size: 1rem; line-height: 1.7; padding: 10px 0; }}
            .footer {{ text-align: center; margin-top: 50px; padding-top: 25px; border-top: 2px solid #dee2e6; color: #6c757d; font-size: 0.85rem; }}
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
            body {{ font-family: 'Inter', 'Arial', sans-serif; background: #f8f9fa; padding: 40px; color: #212529; }}
            .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 50px; border-radius: 12px; box-shadow: 0 4px 16px rgba(0,0,0,0.1); }}
            h1 {{ color: #212529; text-align: center; margin-bottom: 15px; font-size: 2.2rem; border-bottom: 3px solid #212529; padding-bottom: 20px; }}
            .header-info {{ text-align: center; color: #495057; margin-bottom: 40px; font-size: 0.95rem; }}
            .stats {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin: 30px 0; }}
            .stat-box {{ background: #f8f9fa; border-left: 4px solid #212529; padding: 20px; border-radius: 8px; text-align: center; }}
            .stat-value {{ font-size: 2.5rem; font-weight: 700; color: #212529; }}
            .stat-label {{ color: #495057; font-size: 0.9rem; text-transform: uppercase; letter-spacing: 1px; margin-top: 8px; }}
            table {{ width: 100%; border-collapse: collapse; margin: 30px 0; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }}
            th, td {{ padding: 15px; text-align: left; border-bottom: 1px solid #dee2e6; color: #212529; }}
            th {{ background: #212529; color: white; font-weight: 700; text-transform: uppercase; font-size: 0.85rem; letter-spacing: 0.5px; }}
            tr:nth-child(even) {{ background: #f8f9fa; }}
            tr:hover {{ background: #e9ecef; }}
            .tag-highlight {{ background: #e9ecef; padding: 5px 12px; border-radius: 6px; border: 1px solid #dee2e6; font-weight: 600; color: #212529; }}
            .footer {{ text-align: center; margin-top: 50px; padding-top: 25px; border-top: 2px solid #dee2e6; color: #6c757d; font-size: 0.85rem; }}
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

            <h2 style="color: #212529; margin-top: 40px; margin-bottom: 20px; font-size: 1.5rem;">Tags Detalhadas</h2>
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

            <h2 style="color: #212529; margin-top: 40px; margin-bottom: 20px; font-size: 1.5rem;">Suas Tags Mais Utilizadas</h2>
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

    st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
    st.markdown("<h2 style='color: #212529; text-align: center; margin-bottom: 2rem; font-size: 1.5rem;'>Questionário de Acesso</h2>", unsafe_allow_html=True)

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

    st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
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

    st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
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

    st.markdown(f"<div style='text-align: center; color: #495057; margin: 2rem 0; font-size: 1.2rem;'>Exibindo <strong style='color: #212529;'>{len(filtered)}</strong> obra(s)</div>", unsafe_allow_html=True)

    cols = st.columns(3)
    for i, obra in enumerate(filtered):
        with cols[i % 3]:
            st.markdown(f"""
            <div class='obra-card'>
                <img src='{obra['imagem']}' alt='{obra['titulo']}' />
                <div style='padding: 1.5rem;'>
                    <h3 style='color: #212529; font-size: 1.3rem; font-weight: 800; margin-bottom: 0.5rem;'>{obra['titulo']}</h3>
                    <p style='color: #495057; font-size: 1rem; margin: 0.4rem 0; font-weight: 600;'>{obra['artista']}</p>
                    <p style='color: #6c757d; font-size: 0.9rem;'>{obra['ano']}</p>
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
            st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
            st.markdown("<h2 style='color: #212529; text-align: center; margin-bottom: 2rem;'>Login Administrativo</h2>", unsafe_allow_html=True)

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
        st.markdown(f"<h1 class='main-title'>Dashboard Administrativo</h1><p class='subtitle'>Bem-vindo, <strong style='color: #212529;'>{st.session_state.get('admin_username', 'Admin')}</strong></p>", unsafe_allow_html=True)

        tabs = st.tabs(["Visão Geral", "Gráficos Inteligentes", "Análise de Dados", "Obras", "Exportar"])

        with tabs[0]:
            show_overview()
        with tabs[1]:
            show_smart_charts()
        with tabs[2]:
            show_data_analysis()
        with tabs[3]:
            show_manage_obras()
        with tabs[4]:
            show_export_admin()

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

def show_smart_charts():
    st.markdown("### Gráficos Inteligentes e Interativos")

    tags_df = load_all_tags()
    users_df = load_all_users()
    obras = load_obras()

    if tags_df.empty:
        st.info("Não há dados suficientes para gerar gráficos.")
        return

    col1, col2 = st.columns([1, 3])
    with col1:
        chart_option = st.selectbox(
            "Selecione o tipo de análise:",
            ["Top Tags", "Distribuição por Obra", "Timeline de Tags", "Distribuição de Usuários", "Comparativo"]
        )

    if chart_option == "Top Tags":
        top_n = st.slider("Quantidade de tags:", 5, 30, 15)
        top_tags = tags_df['tag'].value_counts().head(top_n)
        fig = create_interactive_charts(top_tags.to_dict(), "bar", f"Top {top_n} Tags Mais Utilizadas")
        st.plotly_chart(fig, use_container_width=True)

    elif chart_option == "Distribuição por Obra":
        tags_per_obra = tags_df.groupby('obra_id').size()
        obras_dict = {o['id']: o['titulo'] for o in obras}
        tags_per_obra.index = tags_per_obra.index.map(lambda x: obras_dict.get(x, f"Obra {x}"))
        fig = create_interactive_charts(tags_per_obra.to_dict(), "pie", "Distribuição de Tags por Obra")
        st.plotly_chart(fig, use_container_width=True)

    elif chart_option == "Timeline de Tags":
        if 'timestamp' in tags_df.columns:
            tags_df['date'] = pd.to_datetime(tags_df['timestamp']).dt.date
            daily_tags = tags_df.groupby('date').size()
            fig = px.line(
                x=daily_tags.index,
                y=daily_tags.values,
                title="Evolução de Tags ao Longo do Tempo",
                labels={'x': 'Data', 'y': 'Quantidade de Tags'}
            )
            fig.update_layout(
                plot_bgcolor='white',
                paper_bgcolor='white',
                font=dict(color='#212529')
            )
            st.plotly_chart(fig, use_container_width=True)

    elif chart_option == "Distribuição de Usuários":
        tags_per_user = tags_df.groupby('user_id').size().value_counts().sort_index()
        fig = px.bar(
            x=tags_per_user.index,
            y=tags_per_user.values,
            title="Distribuição: Quantidade de Tags por Usuário",
            labels={'x': 'Número de Tags', 'y': 'Quantidade de Usuários'},
            color=tags_per_user.values,
            color_continuous_scale='Greys'
        )
        fig.update_layout(
            plot_bgcolor='white',
            paper_bgcolor='white',
            font=dict(color='#212529')
        )
        st.plotly_chart(fig, use_container_width=True)

    elif chart_option == "Comparativo":
        col1, col2 = st.columns(2)
        with col1:
            top_tags = tags_df['tag'].value_counts().head(10)
            fig1 = create_interactive_charts(top_tags.to_dict(), "bar", "Top 10 Tags")
            st.plotly_chart(fig1, use_container_width=True)
        with col2:
            tags_per_obra = tags_df.groupby('obra_id').size().head(10)
            fig2 = px.pie(
                values=tags_per_obra.values,
                names=[f"Obra {i}" for i in tags_per_obra.index],
                title="Distribuição por Obra"
            )
            fig2.update_layout(
                plot_bgcolor='white',
                paper_bgcolor='white',
                font=dict(color='#212529')
            )
            st.plotly_chart(fig2, use_container_width=True)

def show_data_analysis():
    st.markdown("### Análise Profunda de Dados")

    tags_df = load_all_tags()
    users_df = load_all_users()

    tab1, tab2 = st.tabs(["Análise de Tags", "Análise de Questionários"])

    with tab1:
        if tags_df.empty:
            st.info("Não há tags para analisar.")
        else:
            patterns = analyze_tag_patterns(tags_df)

            if patterns:
                st.markdown("#### Padrões e Repetições")
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.metric("Total de Tags", patterns['total_tags'])
                with col2:
                    st.metric("Tags Únicas", patterns['unique_tags'])
                with col3:
                    st.metric("Tags Repetidas", patterns['repeated_tags'])
                with col4:
                    st.metric("Taxa de Repetição", f"{patterns['repetition_rate']:.1f}%")

                st.markdown("#### Diversificação e Consistência")
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric("Score de Diversidade", f"{patterns['diversity_score']:.1f}%")
                    if patterns['diversity_score'] >= 70:
                        st.success("Alta diversificação")
                    elif patterns['diversity_score'] >= 40:
                        st.warning("Diversificação moderada")
                    else:
                        st.error("Baixa diversificação")

                with col2:
                    st.metric("Score de Consistência", f"{patterns['consistency_score']:.1f}%")
                    if patterns['consistency_score'] >= 70:
                        st.success("Alta consistência")
                    elif patterns['consistency_score'] >= 40:
                        st.warning("Consistência moderada")
                    else:
                        st.error("Baixa consistência")

                with col3:
                    st.metric("Tamanho Médio", f"{patterns['avg_length']:.1f} chars")

                st.markdown("#### Tags Mais Repetidas")
                most_repeated_df = pd.DataFrame(
                    list(patterns['most_repeated'].items()),
                    columns=['Tag', 'Frequência']
                )
                st.dataframe(most_repeated_df, use_container_width=True, hide_index=True)

                st.markdown("#### Padrões de Composição")
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Tags de Palavra Única", patterns['single_word'])
                with col2:
                    st.metric("Tags com Múltiplas Palavras", patterns['multi_word'])

    with tab2:
        if users_df.empty:
            st.info("Não há questionários para analisar.")
        else:
            quest_analysis = analyze_questionnaire_patterns(users_df)

            if quest_analysis:
                st.markdown("#### Distribuição de Respostas - Questão 1")
                if 'q1_distribution' in quest_analysis:
                    q1_df = pd.DataFrame(
                        list(quest_analysis['q1_distribution'].items()),
                        columns=['Resposta', 'Quantidade']
                    )
                    fig = create_interactive_charts(
                        quest_analysis['q1_distribution'],
                        "bar",
                        "Familiaridade com Museus"
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    st.dataframe(q1_df, use_container_width=True, hide_index=True)

                st.markdown("#### Distribuição de Respostas - Questão 2")
                if 'q2_distribution' in quest_analysis:
                    q2_df = pd.DataFrame(
                        list(quest_analysis['q2_distribution'].items()),
                        columns=['Resposta', 'Quantidade']
                    )
                    fig = create_interactive_charts(
                        quest_analysis['q2_distribution'],
                        "pie",
                        "Conhecimento sobre Documentação Museológica"
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    st.dataframe(q2_df, use_container_width=True, hide_index=True)

                st.markdown("#### Análise de Texto Livre - Questão 3")
                if 'q3_avg_length' in quest_analysis:
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Respostas Recebidas", quest_analysis['q3_total_responses'])
                    with col2:
                        st.metric("Tamanho Médio", f"{quest_analysis['q3_avg_length']:.0f} chars")

                if 'q3_top_keywords' in quest_analysis:
                    st.markdown("**Palavras-Chave Mais Frequentes:**")
                    keywords_df = pd.DataFrame(
                        list(quest_analysis['q3_top_keywords'].items()),
                        columns=['Palavra', 'Frequência']
                    )
                    st.dataframe(keywords_df, use_container_width=True, hide_index=True)

                    fig = create_interactive_charts(
                        quest_analysis['q3_top_keywords'],
                        "bar",
                        "Top 15 Palavras-Chave em Respostas"
                    )
                    st.plotly_chart(fig, use_container_width=True)

def show_manage_obras():
    st.markdown("### Gestão de Obras")
    obras = load_obras()

    tab1, tab2 = st.tabs(["Listar Obras", "Adicionar Nova"])

    with tab1:
        if obras:
            for obra in obras:
                col1, col2, col3 = st.columns([1, 2, 1])
