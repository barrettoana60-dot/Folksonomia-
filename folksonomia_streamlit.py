"""
Sistema Folksonomia Digital
Para executar: pip install streamlit pandas numpy pillow requests
"""

import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import datetime
import hashlib
import base64
import json
import random
import warnings
from collections import defaultdict
import time

warnings.filterwarnings('ignore')

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

# Configurações de acessibilidade
if 'accessibility' not in st.session_state:
    st.session_state.accessibility = {
        'font_size': 100,  # percentual
        'theme': 'escuro',
        'high_contrast': False,
        'audio_enabled': True
    }

# Listas para nomes de animais
ANIMAIS = [
    "Águia", "Boto", "Capivara", "Doninha", "Ema", "Falcão", "Gavião", "Harpia", "Irara", "Jaguar",
    "Lontra", "Mico", "Onça", "Paca", "Quati", "Raposa", "Tamanduá", "Urubu", "Veado", "Zorrilho",
    "Arara", "Bugio", "Caititu", "Jaguatirica", "Lobo", "Mutum", "Pirarucu", "Tucano", "Sucuri", "Tatu"
]

ADJETIVOS = [
    "Azul", "Bravo", "Calmo", "Dourado", "Esperto", "Feroz", "Gracioso", "Intenso", "Jovial", "Lento",
    "Mágico", "Nobre", "Ousado", "Preciso", "Rápido", "Sábio", "Tímido", "Único", "Valente", "Zeloso",
    "Curioso", "Furtivo", "Altivo", "Sereno", "Vibrante", "Audaz", "Brilhante", "Corajoso", "Distinto", "Elegante"
]

def generate_animal_name():
    random.seed()
    return f"{random.choice(ANIMAIS)} {random.choice(ADJETIVOS)}"

# Funções de acessibilidade
def text_to_speech(text):
    """Converte texto para áudio usando Web Speech API"""
    if not st.session_state.accessibility.get('audio_enabled', False):
        return
    
    audio_js = f"""
    <script>
        function playAudio() {{
            // Cancelar qualquer áudio anterior
            window.speechSynthesis.cancel();
            
            // Criar nova mensagem
            var msg = new SpeechSynthesisUtterance();
            msg.text = {json.dumps(text)};
            msg.lang = 'pt-BR';
            msg.rate = 1.0;
            msg.pitch = 1.0;
            msg.volume = 1.0;
            
            // Tentar encontrar voz em português
            var voices = window.speechSynthesis.getVoices();
            var portugueseVoice = voices.find(function(voice) {{
                return voice.lang.includes('pt') || voice.lang.includes('PT');
            }});
            if (portugueseVoice) {{
                msg.voice = portugueseVoice;
            }}
            
            window.speechSynthesis.speak(msg);
        }}
        
        // Se as vozes já estiverem carregadas
        if (window.speechSynthesis.getVoices().length > 0) {{
            playAudio();
        }} else {{
            window.speechSynthesis.onvoiceschanged = function() {{
                playAudio();
            }};
        }}
    </script>
    """
    st.components.v1.html(audio_js, height=0)

# CSS com painel de acessibilidade flutuante
def load_css():
    font_percent = st.session_state.accessibility['font_size']
    theme = st.session_state.accessibility['theme']
    high_contrast = st.session_state.accessibility['high_contrast']
    
    # Definir cores baseadas no tema
    if theme == 'escuro':
        bg_color = "#0a0a0a"
        text_color = "#ffffff"
        card_bg = "rgba(30, 30, 40, 0.8)"
        border_color = "rgba(255, 255, 255, 0.2)"
        accent_color = "#7aa2f7"
    else:
        bg_color = "#f5f5f5"
        text_color = "#333333"
        card_bg = "rgba(255, 255, 255, 0.9)"
        border_color = "rgba(0, 0, 0, 0.1)"
        accent_color = "#2563eb"
    
    # Alto contraste sobrescreve
    if high_contrast:
        bg_color = "#000000"
        text_color = "#ffffff"
        card_bg = "#ffffff"
        border_color = "#ffffff"
        accent_color = "#ffff00"
    
    css = f"""
    <style>
        /* Reset e fontes */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Inter', sans-serif;
        }}
        
        /* Background principal */
        .stApp {{
            background: {bg_color};
            color: {text_color};
            font-size: {font_percent}%;
        }}
        
        /* Painel de acessibilidade flutuante */
        .accessibility-panel {{
            position: fixed;
            top: 80px;
            right: 20px;
            z-index: 9999;
            background: {card_bg};
            backdrop-filter: blur(10px);
            border: 1px solid {border_color};
            border-radius: 20px;
            padding: 20px;
            width: 280px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
            color: {text_color};
        }}
        
        .accessibility-panel h3 {{
            font-size: 1.1rem;
            margin-bottom: 15px;
            font-weight: 600;
            color: {accent_color};
            text-align: center;
        }}
        
        .accessibility-section {{
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 1px solid {border_color};
        }}
        
        .accessibility-section:last-child {{
            border-bottom: none;
            margin-bottom: 0;
            padding-bottom: 0;
        }}
        
        .section-title {{
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            opacity: 0.7;
            margin-bottom: 10px;
        }}
        
        .font-controls {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 10px;
        }}
        
        .font-btn {{
            background: rgba(128, 128, 128, 0.2);
            border: 1px solid {border_color};
            color: {text_color};
            width: 45px;
            height: 45px;
            border-radius: 12px;
            font-size: 1.4rem;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        
        .font-btn:hover {{
            background: rgba(128, 128, 128, 0.4);
            transform: translateY(-2px);
        }}
        
        .font-size-value {{
            font-size: 1.1rem;
            font-weight: 600;
            min-width: 70px;
            text-align: center;
        }}
        
        .theme-btn {{
            background: rgba(128, 128, 128, 0.2);
            border: 1px solid {border_color};
            color: {text_color};
            padding: 10px;
            border-radius: 12px;
            cursor: pointer;
            transition: all 0.2s;
            text-align: center;
            flex: 1;
        }}
        
        .theme-btn.active {{
            background: {accent_color};
            color: {bg_color};
            border-color: {accent_color};
        }}
        
        .theme-btn:hover {{
            background: rgba(128, 128, 128, 0.4);
        }}
        
        .theme-btn.active:hover {{
            background: {accent_color};
        }}
        
        .contrast-toggle {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 8px 0;
            cursor: pointer;
        }}
        
        .toggle-switch {{
            width: 50px;
            height: 26px;
            background: rgba(128, 128, 128, 0.3);
            border-radius: 30px;
            position: relative;
            transition: all 0.3s;
        }}
        
        .toggle-switch.active {{
            background: {accent_color};
        }}
        
        .toggle-switch::after {{
            content: '';
            position: absolute;
            width: 22px;
            height: 22px;
            background: white;
            border-radius: 50%;
            top: 2px;
            left: 2px;
            transition: all 0.3s;
        }}
        
        .toggle-switch.active::after {{
            left: 26px;
        }}
        
        .audio-btn {{
            background: {accent_color};
            color: {bg_color};
            border: none;
            padding: 12px;
            border-radius: 12px;
            font-weight: 600;
            cursor: pointer;
            width: 100%;
            transition: all 0.2s;
            margin-top: 10px;
        }}
        
        .audio-btn:hover {{
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.3);
        }}
        
        /* Top navbar */
        .top-navbar {{
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            z-index: 9998;
            background: {card_bg};
            backdrop-filter: blur(10px);
            border-bottom: 1px solid {border_color};
            padding: 1rem 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .navbar-logo {{
            font-size: 1.5rem;
            font-weight: 700;
            color: {accent_color};
        }}
        
        .main-content {{
            margin-top: 80px;
            padding: 2rem;
            max-width: 1400px;
            margin-left: auto;
            margin-right: auto;
        }}
        
        /* Cards */
        .glass-card {{
            background: {card_bg};
            backdrop-filter: blur(10px);
            border: 1px solid {border_color};
            border-radius: 24px;
            padding: 2rem;
            margin: 1rem 0;
        }}
        
        .obra-card {{
            background: {card_bg};
            backdrop-filter: blur(10px);
            border: 1px solid {border_color};
            border-radius: 16px;
            overflow: hidden;
            margin-bottom: 1.5rem;
            transition: all 0.3s;
        }}
        
        .obra-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
        }}
        
        .obra-card img {{
            width: 100%;
            height: 250px;
            object-fit: cover;
        }}
        
        .obra-card-content {{
            padding: 1.5rem;
        }}
        
        .tag-badge {{
            display: inline-block;
            background: rgba(128, 128, 128, 0.2);
            border: 1px solid {border_color};
            color: {text_color};
            padding: 0.4rem 1rem;
            border-radius: 30px;
            margin: 0.2rem;
            font-size: 0.9rem;
        }}
        
        /* KPIs */
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin: 1rem 0;
        }}
        
        .kpi-card {{
            background: {card_bg};
            border: 1px solid {border_color};
            border-radius: 16px;
            padding: 1.5rem;
            text-align: center;
        }}
        
        .kpi-value {{
            font-size: 2.5rem;
            font-weight: 700;
            color: {accent_color};
            margin: 0.5rem 0;
        }}
        
        .kpi-label {{
            font-size: 0.9rem;
            opacity: 0.7;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        /* Botões */
        .stButton button {{
            background: {card_bg} !important;
            color: {text_color} !important;
            border: 1px solid {border_color} !important;
            border-radius: 30px !important;
            padding: 0.75rem 1.5rem !important;
            font-weight: 500 !important;
            transition: all 0.3s !important;
        }}
        
        .stButton button:hover {{
            background: rgba(128, 128, 128, 0.3) !important;
            transform: translateY(-2px) !important;
        }}
        
        /* Inputs */
        .stTextInput input, .stTextArea textarea, .stSelectbox select {{
            background: {card_bg} !important;
            color: {text_color} !important;
            border: 1px solid {border_color} !important;
            border-radius: 12px !important;
        }}
        
        /* Tabs */
        .stTabs [data-baseweb="tab-list"] {{
            background: {card_bg};
            border-radius: 30px;
            padding: 0.3rem;
        }}
        
        .stTabs [data-baseweb="tab"] {{
            color: {text_color} !important;
            border-radius: 25px !important;
        }}
        
        .stTabs [aria-selected="true"] {{
            background: {accent_color} !important;
            color: {bg_color} !important;
        }}
        
        /* Headers */
        h1, h2, h3, h4, h5, h6 {{
            color: {text_color};
        }}
        
        /* Hide default elements */
        #MainMenu, footer, header {{
            display: none;
        }}
        
        .stDeployButton {{
            display: none;
        }}
        
        /* Responsive */
        @media (max-width: 768px) {{
            .accessibility-panel {{
                top: 70px;
                right: 10px;
                width: 250px;
            }}
            
            .main-content {{
                padding: 1rem;
            }}
        }}
    </style>
    """
    
    st.markdown(css, unsafe_allow_html=True)

# Painel de acessibilidade flutuante
def accessibility_panel():
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        with st.container():
            # Usando markdown para criar o painel flutuante
            font_current = st.session_state.accessibility['font_size']
            theme_current = st.session_state.accessibility['theme']
            contrast_active = st.session_state.accessibility['high_contrast']
            audio_active = st.session_state.accessibility['audio_enabled']
            
            contrast_class = "active" if contrast_active else ""
            audio_class = "active" if audio_active else ""
            
            painel_html = f"""
            <div class="accessibility-panel">
                <h3>🌓 Acessibilidade</h3>
                
                <div class="accessibility-section">
                    <div class="section-title">📝 Tamanho do Texto</div>
                    <div class="font-controls">
                        <button class="font-btn" onclick="document.getElementById('font-minus').click()">A-</button>
                        <span class="font-size-value">{font_current}%</span>
                        <button class="font-btn" onclick="document.getElementById('font-plus').click()">A+</button>
                    </div>
                </div>
                
                <div class="accessibility-section">
                    <div class="section-title">🎨 Tema</div>
                    <div style="display: flex; gap: 8px;">
                        <button class="theme-btn {'active' if theme_current == 'claro' else ''}" 
                                onclick="document.getElementById('theme-light').click()">Claro</button>
                        <button class="theme-btn {'active' if theme_current == 'escuro' else ''}" 
                                onclick="document.getElementById('theme-dark').click()">Escuro</button>
                    </div>
                </div>
                
                <div class="accessibility-section">
                    <div class="section-title">⚫ Alto Contraste</div>
                    <div class="contrast-toggle" onclick="document.getElementById('contrast-toggle').click()">
                        <span>Ativar</span>
                        <div class="toggle-switch {contrast_class}"></div>
                    </div>
                </div>
                
                <div class="accessibility-section">
                    <div class="section-title">🔊 Áudio</div>
                    <div class="contrast-toggle" onclick="document.getElementById('audio-toggle').click()">
                        <span>Ativar áudio</span>
                        <div class="toggle-switch {audio_class}"></div>
                    </div>
                </div>
            </div>
            """
            
            st.markdown(painel_html, unsafe_allow_html=True)
            
            # Botões invisíveis para controlar as ações
            if st.button("➖", key="font-minus", help="Diminuir fonte"):
                st.session_state.accessibility['font_size'] = max(70, font_current - 10)
                st.rerun()
            
            if st.button("➕", key="font-plus", help="Aumentar fonte"):
                st.session_state.accessibility['font_size'] = min(150, font_current + 10)
                st.rerun()
            
            if st.button("🌞", key="theme-light"):
                st.session_state.accessibility['theme'] = 'claro'
                st.rerun()
            
            if st.button("🌙", key="theme-dark"):
                st.session_state.accessibility['theme'] = 'escuro'
                st.rerun()
            
            if st.button("🎯", key="contrast-toggle"):
                st.session_state.accessibility['high_contrast'] = not st.session_state.accessibility['high_contrast']
                st.rerun()
            
            if st.button("🔊", key="audio-toggle"):
                st.session_state.accessibility['audio_enabled'] = not st.session_state.accessibility['audio_enabled']
                st.rerun()

# Funções de dados
def ensure_data_dir():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

def load_json_file(filepath, default):
    ensure_data_dir()
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return default
    return default

def save_json_file(filepath, data):
    ensure_data_dir()
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar {filepath}: {e}")
        return False

@st.cache_data(ttl=5)
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

def save_tag(uid, obra_id, tag):
    tags = load_json_file(TAGS_FILE, [])
    tags.append({
        "id": len(tags) + 1,
        "user_id": uid,
        "obra_id": obra_id,
        "tag": tag.lower().strip(),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    return save_json_file(TAGS_FILE, tags)

def get_obra_user_tags(obra_id, uid):
    tags = load_json_file(TAGS_FILE, [])
    user_tags = [t for t in tags if t['obra_id'] == obra_id and t['user_id'] == uid]
    if user_tags:
        df = pd.DataFrame(user_tags)
        counts = df['tag'].value_counts().reset_index()
        counts.columns = ['tag', 'count']
        return counts
    return pd.DataFrame(columns=['tag', 'count'])

def all_tags():
    tags = load_json_file(TAGS_FILE, [])
    return pd.DataFrame(tags) if tags else pd.DataFrame()

def all_users():
    users = load_json_file(USERS_FILE, [])
    return pd.DataFrame(users) if users else pd.DataFrame()

def save_answers(uid, animal, answers):
    users = load_json_file(USERS_FILE, [])
    users.append({
        "user_id": uid,
        "animal_name": animal,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        **answers
    })
    return save_json_file(USERS_FILE, users)

def check_login(username, password):
    hashed = hashlib.sha256(password.encode()).hexdigest()
    admin_hashed = hashlib.sha256(ADMIN_PASSWORD.encode()).hexdigest()
    return username == ADMIN_USERNAME and hashed == admin_hashed

def gen_uid():
    return base64.b64encode(os.urandom(12)).decode('ascii')

# Páginas principais
def show_intro():
    st.markdown("<h1 style='text-align: center; margin-bottom: 2rem;'>Sistema Folksonomia Digital</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; margin-bottom: 3rem;'>Sistema colaborativo de catalogação de obras de arte</p>", unsafe_allow_html=True)
    
    with st.form("intro_form"):
        st.markdown("### Questionário de Acesso")
        
        col1, col2 = st.columns(2)
        with col1:
            q1 = st.selectbox(
                "1. Qual é o seu nível de familiaridade com museus?",
                ["Nunca visito museus", "Visito raramente", "Visito ocasionalmente", "Visito frequentemente"]
            )
            q2 = st.selectbox(
                "2. Você já ouviu falar sobre documentação museológica?",
                ["Nunca ouvi falar", "Já ouvi, mas não sei o que é", "Tenho uma ideia básica", "Conheço bem o tema"]
            )
        
        with col2:
            q3 = st.text_area(
                "3. O que você entende por 'tags' ou etiquetas digitais aplicadas a acervo?",
                max_chars=500, height=150,
                placeholder="Descreva sua compreensão sobre o conceito..."
            )
        
        submitted = st.form_submit_button("Acessar Plataforma", use_container_width=True)
        
        if submitted:
            if not q3.strip():
                st.error("Por favor, responda todas as perguntas!")
            else:
                st.session_state['answers'] = {"q1": q1, "q2": q2, "q3": q3}
                save_answers(st.session_state['user_id'], st.session_state['animal_name'], st.session_state['answers'])
                st.session_state['step'] = 'completed'
                st.success("Questionário completo! Acesso liberado.")
                st.balloons()
                st.rerun()

def show_obras():
    st.markdown("<h1 style='text-align: center; margin-bottom: 2rem;'>Galeria de Obras</h1>", unsafe_allow_html=True)
    
    obras = load_obras()
    if not obras:
        st.info("Nenhuma obra cadastrada.")
        return
    
    # Layout em grid
    cols = st.columns(3)
    
    for idx, obra in enumerate(obras):
        with cols[idx % 3]:
            descricao = f"{obra['titulo']} por {obra['artista']}, {obra['ano']}"
            
            st.markdown(f"""
            <div class='obra-card'>
                <img src='{obra['imagem']}' alt='{descricao}'>
                <div class='obra-card-content'>
                    <h3>{obra['titulo']}</h3>
                    <p>{obra['artista']} - {obra['ano']}</p>
            """, unsafe_allow_html=True)
            
            # Botão de áudio
            if st.session_state.accessibility['audio_enabled']:
                if st.button("🔊 Ouvir descrição", key=f"audio_{obra['id']}"):
                    text_to_speech(descricao)
            
            # Botão de tag
            if st.button("➕ Adicionar Tag", key=f"btn_{obra['id']}"):
                st.session_state['selected_obra'] = obra
                st.rerun()
            
            # Formulário de tag
            if 'selected_obra' in st.session_state and st.session_state['selected_obra']['id'] == obra['id']:
                with st.form(f"tag_form_{obra['id']}"):
                    tag = st.text_input("Sua tag:", key=f"tag_{obra['id']}")
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.form_submit_button("Enviar"):
                            save_tag(st.session_state['user_id'], obra['id'], tag)
                            st.success("Tag adicionada!")
                            del st.session_state['selected_obra']
                            st.rerun()
                    with col2:
                        if st.form_submit_button("Cancelar"):
                            del st.session_state['selected_obra']
                            st.rerun()
            
            # Mostrar tags existentes
            user_tags = get_obra_user_tags(obra['id'], st.session_state['user_id'])
            if not user_tags.empty:
                st.markdown("**Suas tags:**")
                tags_html = "".join([f"<span class='tag-badge'>{row['tag']} ({row['count']})</span>" 
                                    for _, row in user_tags.iterrows()])
                st.markdown(tags_html, unsafe_allow_html=True)
            
            st.markdown("</div></div>", unsafe_allow_html=True)

def show_admin():
    st.markdown("<h1 style='text-align: center; margin-bottom: 2rem;'>Área Administrativa</h1>", unsafe_allow_html=True)
    
    if 'admin_logged_in' not in st.session_state:
        st.session_state['admin_logged_in'] = False
    
    if not st.session_state['admin_logged_in']:
        with st.form("login_form"):
            st.markdown("### Login")
            username = st.text_input("Usuário:")
            password = st.text_input("Senha:", type="password")
            
            if st.form_submit_button("Entrar"):
                if check_login(username, password):
                    st.session_state['admin_logged_in'] = True
                    st.success("Login realizado!")
                    st.rerun()
                else:
                    st.error("Credenciais inválidas!")
    else:
        tabs = st.tabs(["Visão Geral", "Tags", "Exportar"])
        
        with tabs[0]:
            st.markdown("### Métricas do Sistema")
            
            tags_df = all_tags()
            users_df = all_users()
            obras = load_obras()
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total de Tags", len(tags_df))
            with col2:
                st.metric("Tags Únicas", tags_df['tag'].nunique() if not tags_df.empty else 0)
            with col3:
                st.metric("Participantes", len(users_df))
            with col4:
                st.metric("Obras", len(obras))
        
        with tabs[1]:
            if not tags_df.empty:
                st.markdown("### Top 10 Tags Mais Usadas")
                top_tags = tags_df['tag'].value_counts().head(10)
                st.bar_chart(top_tags)
            else:
                st.info("Nenhuma tag cadastrada.")
        
        with tabs[2]:
            st.markdown("### Exportar Dados")
            
            if not tags_df.empty:
                csv = tags_df.to_csv(index=False)
                st.download_button("📥 Exportar Tags (CSV)", csv, "tags.csv", "text/csv")
            
            if not users_df.empty:
                csv = users_df.to_csv(index=False)
                st.download_button("📥 Exportar Usuários (CSV)", csv, "usuarios.csv", "text/csv")
        
        if st.button("Sair"):
            st.session_state['admin_logged_in'] = False
            st.rerun()

# Main
def main():
    # Inicializar session state
    if 'user_id' not in st.session_state:
        st.session_state['user_id'] = gen_uid()
    if 'animal_name' not in st.session_state:
        st.session_state['animal_name'] = generate_animal_name()
    if 'step' not in st.session_state:
        st.session_state['step'] = 'intro'
    if 'answers' not in st.session_state:
        st.session_state['answers'] = {}
    
    # Carregar CSS
    load_css()
    
    # Header
    st.markdown("""
    <div class='top-navbar'>
        <div class='navbar-logo'>📚 Folksonomia Digital</div>
        <div style='display: flex; gap: 1rem;'>
            <span>🐾 {}</span>
        </div>
    </div>
    """.format(st.session_state['animal_name']), unsafe_allow_html=True)
    
    # Painel de acessibilidade (só aparece após o questionário)
    if st.session_state['step'] == 'completed':
        accessibility_panel()
    
    # Main content
    st.markdown("<div class='main-content'>", unsafe_allow_html=True)
    
    if st.session_state['step'] != 'completed':
        show_intro()
    else:
        tab1, tab2 = st.tabs(["🖼️ Explorar Obras", "👑 Administração"])
        with tab1:
            show_obras()
        with tab2:
            show_admin()
    
    st.markdown("</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
