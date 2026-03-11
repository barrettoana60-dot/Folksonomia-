"""
Sistema Folksonomia Digital
Para executar: pip install streamlit pandas numpy pillow requests plotly wordcloud matplotlib networkx scikit-learn scipy
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

# Tentar importar bibliotecas opcionais com fallback
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

try:
    import plotly.express as px
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

try:
    from wordcloud import WordCloud
    WORDCLOUD_AVAILABLE = True
except ImportError:
    WORDCLOUD_AVAILABLE = False

try:
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.cluster import KMeans
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

try:
    from scipy.cluster.hierarchy import dendrogram, linkage
    from scipy.spatial.distance import pdist, squareform
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

import re

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
        'font_size': 'medium',
        'theme': 'dark',
        'high_contrast': False,
        'reduce_motion': False,
        'screen_reader': False,
        'audio_descriptions': True
    }

# Mapeamento de tamanhos de fonte
FONT_SIZES = {
    'small': {'base': '14px', 'h1': '2.5rem', 'h2': '2rem', 'h3': '1.5rem'},
    'medium': {'base': '16px', 'h1': '3.5rem', 'h2': '2.8rem', 'h3': '2rem'},
    'large': {'base': '18px', 'h1': '4rem', 'h2': '3.2rem', 'h3': '2.5rem'},
    'x-large': {'base': '20px', 'h1': '4.5rem', 'h2': '3.8rem', 'h3': '3rem'}
}

# Cores para temas
THEMES = {
    'dark': {
        'bg': 'linear-gradient(-45deg,#000 0%,#001F3F 25%,#000 50%,#001F3F 75%,#000 100%)',
        'text': '#e0e0e0',
        'card': 'rgba(255,255,255,.15)',
        'card_hover': 'rgba(255,255,255,.25)',
        'border': 'rgba(255,255,255,.3)',
        'accent': '#a7e6ff',
        'accent2': '#d1baff'
    },
    'light': {
        'bg': 'linear-gradient(135deg, #f5f7fa 0%, #e9ecef 100%)',
        'text': '#2d3436',
        'card': 'rgba(255,255,255,.9)',
        'card_hover': 'rgba(255,255,255,1)',
        'border': 'rgba(0,0,0,.1)',
        'accent': '#0984e3',
        'accent2': '#6c5ce7'
    }
}

ANIMAIS = [
    "Águia","Boto","Capivara","Doninha","Ema","Falcão","Gavião","Harpia","Irara","Jaguar",
    "Lontra","Mico","Onça","Paca","Quati","Raposa","Tamanduá","Urubu","Veado","Zorrilho",
    "Arara","Bugio","Caititu","Jaguatirica","Lobo","Mutum","Pirarucu","Tucano","Sucuri","Tatu"
]
ADJETIVOS = [
    "Azul","Bravo","Calmo","Dourado","Esperto","Feroz","Gracioso","Intenso","Jovial","Lento",
    "Mágico","Nobre","Ousado","Preciso","Rápido","Sábio","Tímido","Único","Valente","Zeloso",
    "Curioso","Furtivo","Altivo","Sereno","Vibrante","Audaz","Brilhante","Corajoso","Distinto","Elegante"
]

def generate_animal_name():
    random.seed()
    return f"{random.choice(ANIMAIS)} {random.choice(ADJETIVOS)}"

# Funções de acessibilidade
def get_font_size_css():
    fs = FONT_SIZES[st.session_state.accessibility['font_size']]
    theme = THEMES[st.session_state.accessibility['theme']]
    contrast_class = 'high-contrast' if st.session_state.accessibility['high_contrast'] else ''
    motion_class = 'reduce-motion' if st.session_state.accessibility['reduce_motion'] else ''
    
    return f"""
    <style>
        :root {{
            --font-size-base: {fs['base']};
            --font-size-h1: {fs['h1']};
            --font-size-h2: {fs['h2']};
            --font-size-h3: {fs['h3']};
            --bg-gradient: {theme['bg']};
            --text-color: {theme['text']};
            --card-bg: {theme['card']};
            --card-hover: {theme['card_hover']};
            --border-color: {theme['border']};
            --accent-color: {theme['accent']};
            --accent-color2: {theme['accent2']};
        }}
        
        .{contrast_class} {{
            --card-bg: rgba(0,0,0,.9) !important;
            --border-color: #fff !important;
        }}
        
        .{motion_class} * {{
            transition: none !important;
            animation: none !important;
        }}
        
        * {{
            font-size: var(--font-size-base);
        }}
        
        h1 {{
            font-size: var(--font-size-h1) !important;
        }}
        
        h2 {{
            font-size: var(--font-size-h2) !important;
        }}
        
        h3 {{
            font-size: var(--font-size-h3) !important;
        }}
    </style>
    """

def accessibility_controls():
    """Controles de acessibilidade na barra lateral"""
    with st.sidebar:
        st.markdown("### Acessibilidade")
        
        # Tamanho da fonte
        st.session_state.accessibility['font_size'] = st.select_slider(
            "Tamanho da Fonte",
            options=['small', 'medium', 'large', 'x-large'],
            value=st.session_state.accessibility['font_size'],
            format_func=lambda x: {
                'small': 'Pequeno',
                'medium': 'Médio',
                'large': 'Grande',
                'x-large': 'Extra Grande'
            }[x]
        )
        
        # Tema
        st.session_state.accessibility['theme'] = st.radio(
            "Tema",
            options=['dark', 'light'],
            format_func=lambda x: 'Escuro' if x == 'dark' else 'Claro',
            horizontal=True
        )
        
        # Alto contraste
        st.session_state.accessibility['high_contrast'] = st.checkbox(
            "Alto Contraste",
            value=st.session_state.accessibility['high_contrast']
        )
        
        # Reduzir movimento
        st.session_state.accessibility['reduce_motion'] = st.checkbox(
            "Reduzir Movimento",
            value=st.session_state.accessibility['reduce_motion']
        )
        
        # Descrições em áudio
        st.session_state.accessibility['audio_descriptions'] = st.checkbox(
            "Descrições em Áudio",
            value=st.session_state.accessibility['audio_descriptions']
        )
        
        st.markdown("---")

# ── CORE ──────────────────────────────────────────────────────────────
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

# ── DESCRIÇÃO DE IMAGENS ─────────────────────────────────────────────
def generate_image_description(image_url):
    """Gera uma descrição textual da imagem para acessibilidade"""
    if not REQUESTS_AVAILABLE or not PIL_AVAILABLE:
        return "Bibliotecas de processamento de imagem não disponíveis."
    
    try:
        response = requests.get(image_url, timeout=5)
        img = Image.open(BytesIO(response.content))
        
        # Extrair metadados básicos
        width, height = img.size
        format_img = img.format
        mode = img.mode
        
        # Análise básica de cores
        img_array = np.array(img)
        if len(img_array.shape) == 3:
            avg_color = np.mean(img_array, axis=(0, 1))
            brightness = np.mean(avg_color)
        else:
            brightness = np.mean(img_array)
        
        description = f"Imagem {width}x{height} pixels, formato {format_img}. "
        
        if brightness < 85:
            description += "Imagem predominantemente escura. "
        elif brightness > 170:
            description += "Imagem predominantemente clara. "
        else:
            description += "Imagem com tons médios. "
            
        return description
    except:
        return "Descrição automática não disponível para esta imagem."

def text_to_speech(text):
    """Simula conversão de texto para áudio (placeholder para API real)"""
    return f"Reproduzindo áudio: {text}"

# ── SIMILARIDADE ──────────────────────────────────────────────────────
def ntag(tag): return tag.lower().strip()
def words(tag): return set(ntag(tag).split())
def ngrams(text, n=3):
    t = ntag(text)
    return set([t]) if len(t) < n else set(t[i:i+n] for i in range(len(t)-n+1))

def sim(t1, t2):
    a, b = ntag(t1), ntag(t2)
    if a == b: return 1.0
    if a in b or b in a:
        return 0.55 + 0.45*(min(len(a),len(b))/max(len(a),len(b)))
    w1,w2 = words(t1),words(t2)
    if w1 and w2:
        j = len(w1&w2)/len(w1|w2)
        if j >= 0.5: return j
    if len(a)>=3 and len(b)>=3:
        ng1,ng2 = ngrams(a),ngrams(b)
        nj = len(ng1&ng2)/len(ng1|ng2) if ng1|ng2 else 0
        if nj > 0:
            wj = len(w1&w2)/len(w1|w2) if w1|w2 else 0
            return 0.6*nj + 0.4*wj
    return 0.0

def tag_connections(tags_list, threshold=0.35):
    uniq = list(set(ntag(t) for t in tags_list))
    conns = []
    for i in range(len(uniq)):
        for j in range(i+1, len(uniq)):
            s = sim(uniq[i], uniq[j])
            if s >= threshold:
                w1,w2 = words(uniq[i]),words(uniq[j])
                shared = w1&w2
                if uniq[i] in uniq[j] or uniq[j] in uniq[i]: 
                    tipo = "Contencao"
                elif shared: 
                    tipo = f"Palavra comum: '{', '.join(shared)}'"
                else: 
                    tipo = "Similaridade fonetica"
                conns.append({"tag_a":uniq[i],"tag_b":uniq[j],"similaridade":round(s,3),"tipo":tipo})
    conns.sort(key=lambda x: x["similaridade"], reverse=True)
    return conns

def tag_clusters(tags_list, threshold=0.35):
    uniq = list(set(ntag(t) for t in tags_list))
    conns = tag_connections(uniq, threshold)
    par = {t:t for t in uniq}
    def find(x):
        while par[x]!=x: par[x]=par[par[x]]; x=par[x]
        return x
    def union(a,b):
        ra,rb = find(a),find(b)
        if ra!=rb: par[ra]=rb
    for c in conns: union(c["tag_a"],c["tag_b"])
    cl = defaultdict(list)
    for t in uniq: cl[find(t)].append(t)
    return [sorted(v) for v in cl.values() if len(v)>1]

# ── ANÁLISE AVANÇADA DE TAGS ─────────────────────────────────────────
def advanced_tag_analysis(tags_df):
    """Análise estatística avançada das tags"""
    analysis = {}
    
    # Estatísticas básicas
    analysis['total_tags'] = len(tags_df)
    analysis['unique_tags'] = tags_df['tag'].nunique()
    analysis['avg_tags_per_user'] = tags_df.groupby('user_id').size().mean()
    
    # Distribuição de frequência
    freq_dist = tags_df['tag'].value_counts()
    analysis['most_common'] = freq_dist.head(10).to_dict()
    analysis['least_common'] = freq_dist.tail(10).to_dict()
    
    # Métricas de diversidade
    analysis['shannon_entropy'] = calculate_shannon_entropy(freq_dist)
    analysis['simpson_index'] = calculate_simpson_index(freq_dist)
    analysis['pielou_evenness'] = analysis['shannon_entropy'] / np.log(len(freq_dist)) if len(freq_dist) > 1 else 0
    
    # Hapax legomena
    analysis['hapax_count'] = (freq_dist == 1).sum()
    analysis['hapax_percentage'] = (analysis['hapax_count'] / analysis['unique_tags'] * 100)
    
    # Análise de comprimento das tags
    tag_lengths = tags_df['tag'].str.len()
    analysis['avg_tag_length'] = tag_lengths.mean()
    analysis['min_tag_length'] = tag_lengths.min()
    analysis['max_tag_length'] = tag_lengths.max()
    
    # Análise temporal
    if 'timestamp' in tags_df.columns:
        tags_df['hour'] = pd.to_datetime(tags_df['timestamp']).dt.hour
        analysis['peak_hour'] = tags_df['hour'].mode().iloc[0] if not tags_df['hour'].empty else None
        analysis['tags_by_hour'] = tags_df['hour'].value_counts().sort_index().to_dict()
    
    return analysis

def calculate_shannon_entropy(freq_dist):
    """Calcula entropia de Shannon para distribuição de tags"""
    probs = freq_dist / freq_dist.sum()
    return -sum(p * np.log(p) for p in probs if p > 0)

def calculate_simpson_index(freq_dist):
    """Calcula índice de Simpson para diversidade"""
    total = freq_dist.sum()
    return 1 - sum((n * (n - 1)) / (total * (total - 1)) for n in freq_dist)

def create_tag_network(tags_df, threshold=0.35):
    """Cria rede de conexões entre tags para visualização"""
    if not NETWORKX_AVAILABLE:
        return None
        
    unique_tags = tags_df['tag'].unique()
    connections = tag_connections(unique_tags, threshold)
    
    G = nx.Graph()
    for tag in unique_tags:
        G.add_node(tag, size=tags_df[tags_df['tag']==tag].shape[0])
    
    for conn in connections:
        G.add_edge(conn['tag_a'], conn['tag_b'], weight=conn['similaridade'])
    
    return G

def hierarchical_clustering(tags_df, n_clusters=5):
    """Agrupamento hierárquico de tags baseado em similaridade"""
    if not SCIPY_AVAILABLE or not SKLEARN_AVAILABLE:
        return None, None
        
    unique_tags = tags_df['tag'].unique()
    if len(unique_tags) < 2:
        return None, None
    
    # Matriz de distância baseada em similaridade
    n = len(unique_tags)
    dist_matrix = np.zeros((n, n))
    for i in range(n):
        for j in range(i+1, n):
            s = sim(unique_tags[i], unique_tags[j])
            dist_matrix[i, j] = 1 - s
            dist_matrix[j, i] = 1 - s
    
    # Agrupamento hierárquico
    linkage_matrix = linkage(squareform(dist_matrix), method='average')
    
    # K-means para clusters finais
    kmeans = KMeans(n_clusters=min(n_clusters, n), random_state=42, n_init=10)
    clusters = kmeans.fit_predict(dist_matrix)
    
    result = {}
    for i, tag in enumerate(unique_tags):
        cluster_id = clusters[i]
        if cluster_id not in result:
            result[cluster_id] = []
        result[cluster_id].append(tag)
    
    return result, linkage_matrix

def generate_wordcloud(tags_df):
    """Gera wordcloud das tags"""
    if not WORDCLOUD_AVAILABLE or not MATPLOTLIB_AVAILABLE:
        return None
        
    text = ' '.join(tags_df['tag'].tolist())
    wordcloud = WordCloud(width=800, height=400, 
                         background_color='white',
                         colormap='viridis',
                         max_words=100).generate(text)
    return wordcloud

# ── FILTROS AVANÇADOS ───────────────────────────────────────────────
def advanced_filters(obras, tags_df):
    """Sistema de filtros avançados para busca de imagens"""
    
    st.markdown("### Filtros Avançados")
    
    with st.expander("Configurar Filtros", expanded=False):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Filtro por palavras-chave
            keywords = st.text_input("Palavras-chave", 
                                     placeholder="Ex: natureza, retrato, abstrato...")
            
            # Filtro por período
            anos = []
            for obra in obras:
                try:
                    ano = int(obra.get('ano', 0))
                    if ano > 0:
                        anos.append(ano)
                except:
                    pass
            
            min_ano = min(anos) if anos else 1400
            max_ano = max(anos) if anos else 2024
            
            year_range = st.slider("Período",
                                   min_value=min_ano,
                                   max_value=max_ano,
                                   value=(min_ano, max_ano))
        
        with col2:
            # Filtro por artista
            artists = list(set([o['artista'] for o in obras]))
            selected_artists = st.multiselect("Artistas", artists)
            
            # Filtro por número de tags
            if not tags_df.empty:
                obra_tags_count = tags_df.groupby('obra_id').size().to_dict()
                min_tags = st.number_input("Mínimo de tags", min_value=0, value=0)
            else:
                obra_tags_count = {}
                min_tags = 0
        
        with col3:
            # Filtro por tags mais usadas
            if not tags_df.empty:
                top_tags = tags_df['tag'].value_counts().head(20).index.tolist()
                selected_tags = st.multiselect("Tags específicas", top_tags)
            else:
                selected_tags = []
            
            # Filtro por popularidade
            if not tags_df.empty:
                obra_popularity = tags_df.groupby('obra_id').size()
                if not obra_popularity.empty:
                    pop_percentile = st.slider("Percentil de popularidade", 0, 100, 0)
                    min_popularity = np.percentile(obra_popularity, pop_percentile)
                else:
                    min_popularity = 0
            else:
                min_popularity = 0
        
        # Ordenação
        sort_by = st.selectbox("Ordenar por",
                               ["ID", "Título", "Artista", "Ano", "Popularidade"])
        
        sort_order = st.radio("Ordem", ["Crescente", "Decrescente"], horizontal=True)
    
    # Aplicar filtros
    filtered_obras = obras.copy()
    
    if keywords:
        keywords_lower = keywords.lower()
        filtered_obras = [o for o in filtered_obras 
                         if keywords_lower in o['titulo'].lower() 
                         or keywords_lower in o['artista'].lower()]
    
    filtered_obras = [o for o in filtered_obras 
                     if year_range[0] <= int(o.get('ano', 0)) <= year_range[1]]
    
    if selected_artists:
        filtered_obras = [o for o in filtered_obras 
                         if o['artista'] in selected_artists]
    
    if min_tags > 0 and obra_tags_count:
        filtered_obras = [o for o in filtered_obras 
                         if obra_tags_count.get(o['id'], 0) >= min_tags]
    
    if selected_tags and not tags_df.empty:
        obra_tags = tags_df.groupby('obra_id')['tag'].apply(list).to_dict()
        filtered_obras = [o for o in filtered_obras 
                         if all(tag in obra_tags.get(o['id'], []) 
                               for tag in selected_tags)]
    
    if min_popularity > 0 and obra_popularity is not None:
        filtered_obras = [o for o in filtered_obras 
                         if obra_popularity.get(o['id'], 0) >= min_popularity]
    
    # Ordenação
    reverse = (sort_order == "Decrescente")
    if sort_by == "ID":
        filtered_obras = sorted(filtered_obras, key=lambda x: x['id'], reverse=reverse)
    elif sort_by == "Título":
        filtered_obras = sorted(filtered_obras, key=lambda x: x['titulo'], reverse=reverse)
    elif sort_by == "Artista":
        filtered_obras = sorted(filtered_obras, key=lambda x: x['artista'], reverse=reverse)
    elif sort_by == "Ano":
        filtered_obras = sorted(filtered_obras, 
                               key=lambda x: int(x.get('ano', 0)), 
                               reverse=reverse)
    elif sort_by == "Popularidade" and not tags_df.empty:
        filtered_obras = sorted(filtered_obras,
                               key=lambda x: obra_popularity.get(x['id'], 0),
                               reverse=reverse)
    
    return filtered_obras

# ── CSS ───────────────────────────────────────────────────────────────
def load_css():
    base_css = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800&display=swap');
    
    * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
        font-family: 'Poppins', sans-serif !important;
    }
    
    .stApp {
        background: var(--bg-gradient);
        background-size: 400% 400%;
        animation: bg 15s ease infinite;
        color: var(--text-color);
    }
    
    @keyframes bg {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    
    /* Barra de acessibilidade */
    .accessibility-bar {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        z-index: 10000;
        background: rgba(0,0,0,.8);
        backdrop-filter: blur(10px);
        padding: 0.5rem 2rem;
        display: flex;
        justify-content: flex-end;
        gap: 1rem;
        border-bottom: 1px solid rgba(255,255,255,.1);
    }
    
    .accessibility-btn {
        background: transparent;
        border: 1px solid rgba(255,255,255,.2);
        color: white;
        padding: 0.3rem 1rem;
        border-radius: 20px;
        cursor: pointer;
        font-size: 0.85rem;
        transition: all 0.3s;
    }
    
    .accessibility-btn:hover {
        background: rgba(255,255,255,.1);
        transform: translateY(-2px);
    }
    
    /* Top navbar */
    .top-navbar {
        position: fixed;
        top: 40px;
        left: 0;
        right: 0;
        z-index: 9999;
        background: var(--card-bg);
        backdrop-filter: blur(20px) saturate(180%);
        border-bottom: 1px solid var(--border-color);
        padding: 1.4rem 3rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 8px 32px rgba(0,0,0,.1);
    }
    
    .navbar-logo {
        font-size: 1.8rem;
        font-weight: 800;
        background: linear-gradient(135deg, var(--accent-color) 0%, var(--accent-color2) 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        letter-spacing: -1px;
    }
    
    .main-content {
        margin-top: 120px;
        padding: 2rem 3rem;
        max-width: 1600px;
        margin-left: auto;
        margin-right: auto;
    }
    
    /* Cards e componentes */
    .glass-card {
        background: var(--card-bg);
        backdrop-filter: blur(20px) saturate(180%);
        border: 1px solid var(--border-color);
        border-radius: 24px;
        padding: 2.5rem;
        margin: 1.5rem 0;
        box-shadow: 0 8px 32px rgba(0,0,0,.1);
        transition: all 0.4s cubic-bezier(.4,0,.2,1);
        position: relative;
        overflow: hidden;
    }
    
    .glass-card:hover {
        background: var(--card-hover);
        transform: translateY(-8px) scale(1.02);
        box-shadow: 0 16px 48px rgba(0,0,0,.2);
        border-color: var(--border-color);
    }
    
    .obra-card {
        background: var(--card-bg);
        backdrop-filter: blur(15px) saturate(180%);
        border: 1px solid var(--border-color);
        border-radius: 20px;
        overflow: hidden;
        transition: all 0.4s cubic-bezier(.4,0,.2,1);
        cursor: pointer;
        position: relative;
    }
    
    .obra-card:hover {
        transform: translateY(-12px) scale(1.03);
        box-shadow: 0 20px 60px rgba(0,31,63,.4);
        border-color: var(--border-color);
    }
    
    .obra-card img {
        width: 100%;
        height: 280px;
        object-fit: cover;
        transition: transform 0.6s cubic-bezier(.4,0,.2,1);
    }
    
    .obra-card:hover img {
        transform: scale(1.15) rotate(2deg);
    }
    
    /* Badges e tags */
    .tag-badge {
        display: inline-block;
        background: var(--card-bg);
        border: 1px solid var(--border-color);
        color: var(--text-color);
        padding: 0.5rem 1.1rem;
        border-radius: 50px;
        margin: 0.3rem;
        font-size: 0.88rem;
        font-weight: 600;
        transition: all 0.3s;
    }
    
    .tag-badge:hover {
        background: var(--card-hover);
        transform: translateY(-3px) scale(1.05);
    }
    
    .tag-green {
        background: rgba(34,197,94,.25) !important;
        border-color: rgba(34,197,94,.5) !important;
        color: #dcfce7 !important;
    }
    
    .tag-amber {
        background: rgba(245,158,11,.25) !important;
        border-color: rgba(245,158,11,.5) !important;
        color: #fef3c7 !important;
    }
    
    .tag-blue {
        background: rgba(96,165,250,.25) !important;
        border-color: rgba(96,165,250,.5) !important;
        color: #dbeafe !important;
    }
    
    /* Botão de áudio */
    .audio-btn {
        background: rgba(167,230,255,.2);
        border: 1px solid rgba(167,230,255,.45);
        color: var(--accent-color);
        padding: 0.3rem 1rem;
        border-radius: 50px;
        font-size: 0.85rem;
        cursor: pointer;
        transition: all 0.3s;
        margin: 0.5rem 0;
    }
    
    .audio-btn:hover {
        background: rgba(167,230,255,.3);
        transform: translateY(-2px);
    }
    
    /* KPIs e métricas */
    .kpi-card {
        background: var(--card-bg);
        backdrop-filter: blur(20px) saturate(180%);
        border: 1px solid var(--border-color);
        border-radius: 18px;
        padding: 1.6rem;
        text-align: center;
        color: var(--text-color);
        box-shadow: 0 8px 32px rgba(0,0,0,.12);
        transition: all 0.4s;
    }
    
    .kpi-card:hover {
        transform: translateY(-6px) scale(1.04);
        box-shadow: 0 16px 48px rgba(0,31,63,.28);
    }
    
    .kpi-val {
        font-size: 2.5rem;
        font-weight: 800;
        margin: 0.6rem 0;
        text-shadow: 0 4px 20px rgba(0,0,0,.2);
        color: var(--accent-color);
    }
    
    .kpi-lbl {
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 2px;
        font-weight: 600;
        opacity: 0.8;
    }
    
    /* Stats cards */
    .stat-card {
        background: var(--card-bg);
        border: 1px solid var(--border-color);
        border-radius: 14px;
        padding: 1.3rem;
        margin: 0.7rem 0;
    }
    
    .stat-blue {
        border-left: 4px solid #60a5fa;
        background: rgba(96,165,250,.07);
    }
    
    .stat-green {
        border-left: 4px solid #34d399;
        background: rgba(52,211,153,.07);
    }
    
    .stat-purple {
        border-left: 4px solid #a78bfa;
        background: rgba(167,139,250,.07);
    }
    
    .stat-amber {
        border-left: 4px solid #fbbf24;
        background: rgba(251,191,36,.07);
    }
    
    /* Insights */
    .insight {
        background: rgba(167,230,255,.1);
        border: 1px solid rgba(167,230,255,.28);
        border-radius: 12px;
        padding: 1rem 1.4rem;
        margin: 0.6rem 0;
        color: var(--text-color);
        font-size: 0.9rem;
        line-height: 1.7;
    }
    
    .insight strong {
        color: var(--accent-color);
    }
    
    /* Conexões */
    .conn-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 8px;
        background: rgba(255,255,255,.06);
        border-radius: 11px;
        padding: 0.85rem 1.2rem;
        margin: 0.3rem 0;
        border-left: 3px solid rgba(255,255,255,.2);
        transition: background 0.2s;
    }
    
    .conn-row:hover {
        background: rgba(255,255,255,.12);
    }
    
    /* Clusters */
    .cluster-wrap {
        background: rgba(255,255,255,.05);
        border-radius: 14px;
        padding: 1.1rem 1.4rem;
        margin: 0.5rem 0;
        border: 1px solid rgba(255,255,255,.1);
    }
    
    .cluster-title {
        font-size: 0.76rem;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        color: rgba(167,139,250,.8);
        margin-bottom: 0.55rem;
        font-weight: 700;
    }
    
    .cluster-pill {
        display: inline-flex;
        align-items: center;
        gap: 5px;
        background: rgba(168,85,247,.2);
        border: 1px solid rgba(168,85,247,.38);
        border-radius: 50px;
        padding: 0.32rem 0.85rem;
        margin: 0.2rem;
        font-size: 0.78rem;
        font-weight: 600;
        color: #f3e8ff;
    }
    
    /* Progress bar */
    .pbar-o {
        background: rgba(255,255,255,.1);
        border-radius: 50px;
        height: 6px;
        margin: 3px 0;
        overflow: hidden;
    }
    
    .pbar-i {
        height: 100%;
        border-radius: 50px;
        transition: width 0.5s;
    }
    
    /* Divider */
    .divider {
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,.22), transparent);
        margin: 1.6rem 0;
    }
    
    /* Botões Streamlit */
    .stButton button {
        background: var(--card-bg) !important;
        backdrop-filter: blur(15px) !important;
        color: var(--text-color) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 50px !important;
        padding: 1rem 2.5rem !important;
        font-weight: 700 !important;
        font-size: 1rem !important;
        transition: all 0.4s !important;
        box-shadow: 0 8px 25px rgba(0,0,0,.15) !important;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    .stButton button:hover {
        background: var(--card-hover) !important;
        box-shadow: 0 12px 40px rgba(0,31,63,.4) !important;
        transform: translateY(-4px) scale(1.05) !important;
        border-color: var(--border-color) !important;
    }
    
    /* Inputs */
    .stTextInput input, .stTextArea textarea, .stSelectbox select {
        background: var(--card-bg) !important;
        backdrop-filter: blur(10px) !important;
        border: 1px solid var(--border-color) !important;
        color: var(--text-color) !important;
        border-radius: 14px !important;
        padding: 0.9rem !important;
        font-weight: 500 !important;
    }
    
    .stTextInput input::placeholder, .stTextArea textarea::placeholder {
        color: rgba(255,255,255,.55) !important;
    }
    
    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: var(--border-color) !important;
        box-shadow: 0 0 0 3px rgba(255,255,255,.18) !important;
    }
    
    /* Labels */
    label {
        color: var(--text-color) !important;
        font-weight: 700 !important;
        font-size: 1rem !important;
        text-shadow: 0 2px 10px rgba(0,0,0,.2);
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.7rem;
        background: var(--card-bg);
        backdrop-filter: blur(10px);
        padding: 0.45rem;
        border-radius: 14px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: var(--card-bg);
        border: 1px solid var(--border-color);
        border-radius: 10px;
        color: var(--text-color);
        padding: 0.75rem 1.5rem;
        font-weight: 700;
        transition: all 0.3s;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background: var(--card-hover);
        transform: translateY(-2px);
    }
    
    .stTabs [aria-selected="true"] {
        background: var(--card-hover) !important;
        border-color: var(--border-color) !important;
        box-shadow: 0 6px 20px rgba(0,31,63,.25) !important;
    }
    
    /* Alerts */
    .stAlert {
        background: var(--card-bg) !important;
        backdrop-filter: blur(15px) !important;
        border-radius: 14px !important;
        border-left: 4px solid !important;
        color: var(--text-color) !important;
    }
    
    /* Hide default elements */
    #MainMenu, footer, header {
        visibility: hidden;
    }
    
    .stDeployButton {
        display: none;
    }
    
    [data-testid="stSidebar"] {
        display: none;
    }
    
    /* Headers */
    h1, h2, h3, h4, h5, h6 {
        color: var(--text-color);
        font-weight: 700;
        text-shadow: 0 2px 15px rgba(0,0,0,.3);
    }
    
    /* Dataframes */
    .dataframe {
        background: var(--card-bg) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 14px !important;
        color: var(--text-color) !important;
    }
    
    .dataframe th {
        background: rgba(255,255,255,.22) !important;
        color: var(--text-color) !important;
        font-weight: 700 !important;
    }
    
    .dataframe td {
        color: var(--text-color) !important;
    }
    
    /* Responsive */
    @media(max-width: 768px) {
        .main-title {
            font-size: 2.5rem;
        }
        
        .main-content {
            margin-top: 140px;
            padding: 1rem;
        }
        
        .top-navbar {
            padding: 1rem;
        }
    }
    </style>
    """
    
    accessibility_css = get_font_size_css()
    st.markdown(base_css + accessibility_css, unsafe_allow_html=True)

# ── HELPERS ───────────────────────────────────────────────────────────
def kpi(label, value, sub="", color="#a7e6ff"):
    return (f"<div class='kpi-card'>"
            f"<div class='kpi-lbl'>{label}</div>"
            f"<div class='kpi-val' style='color:{color}'>{value}</div>"
            f"{'<div class=kpi-sub>'+sub+'</div>' if sub else ''}"
            f"</div>")

def insight(text):
    return f"<div class='insight'>{text}</div>"

def divider():
    return "<div class='divider'></div>"

def pbar(pct, color="#60a5fa"):
    w = min(100, max(0, pct*100))
    return f"<div class='pbar-o'><div class='pbar-i' style='width:{w:.1f}%;background:{color}'></div></div>"

# ── DADOS ─────────────────────────────────────────────────────────────
def check_admin():
    admins = load_json_file(ADMIN_FILE, [])
    if not admins:
        hashed = hashlib.sha256(ADMIN_PASSWORD.encode()).hexdigest()
        save_json_file(ADMIN_FILE, [{"id":1,"username":ADMIN_USERNAME,"password":hashed}])

def gen_uid():
    return base64.b64encode(os.urandom(12)).decode('ascii')

@st.cache_data(ttl=5, show_spinner=False)
def load_obras():
    default = [
        {"id":1,"titulo":"Guernica","artista":"Pablo Picasso","ano":"1937",
         "imagem":"https://upload.wikimedia.org/wikipedia/en/7/74/PicassoGuernica.jpg"},
        {"id":2,"titulo":"A Noite Estrelada","artista":"Vincent van Gogh","ano":"1889",
         "imagem":"https://upload.wikimedia.org/wikipedia/commons/thumb/e/ea/Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg/1200px-Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg"},
        {"id":3,"titulo":"Mona Lisa","artista":"Leonardo da Vinci","ano":"1503",
         "imagem":"https://upload.wikimedia.org/wikipedia/commons/thumb/e/ec/Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_retouched.jpg/800px-Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_retouched.jpg"}
    ]
    obras = load_json_file(OBRAS_FILE, default)
    if not obras:
        save_json_file(OBRAS_FILE, default)
        return default
    return obras

def save_answers(uid, animal, answers):
    users = load_json_file(USERS_FILE, [])
    users.append({"user_id":uid,"animal_name":animal,
                  "timestamp":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),**answers})
    return save_json_file(USERS_FILE, users)

def save_tag(uid, obra_id, tag):
    tags = load_json_file(TAGS_FILE, [])
    tags.append({"id":len(tags)+1,"user_id":uid,"obra_id":obra_id,
                 "tag":tag.lower().strip(),
                 "timestamp":datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
    st.cache_data.clear()
    return save_json_file(TAGS_FILE, tags)

def get_user_tags(uid):
    tags = load_json_file(TAGS_FILE, [])
    ut = [t for t in tags if t['user_id']==uid]
    return pd.DataFrame(ut) if ut else pd.DataFrame()

def get_obra_user_tags(obra_id, uid):
    tags = load_json_file(TAGS_FILE, [])
    f = [t for t in tags if t['obra_id']==obra_id and t['user_id']==uid]
    if f:
        df = pd.DataFrame(f)
        c = df['tag'].value_counts().reset_index()
        c.columns = ["tag","count"]
        return c
    return pd.DataFrame(columns=["tag","count"])

def check_login(username, password):
    h = hashlib.sha256(password.encode()).hexdigest()
    return username==ADMIN_USERNAME and h==hashlib.sha256(ADMIN_PASSWORD.encode()).hexdigest()

def all_tags():
    t = load_json_file(TAGS_FILE, [])
    return pd.DataFrame(t) if t else pd.DataFrame()

def all_users():
    u = load_json_file(USERS_FILE, [])
    return pd.DataFrame(u) if u else pd.DataFrame()

# ── INTERFACE PRINCIPAL ───────────────────────────────────────────────
def show_header():
    # Barra de acessibilidade
    st.markdown("""
    <div class="accessibility-bar">
        <button class="accessibility-btn" onclick="document.body.style.fontSize='large'">
            A+ Aumentar Texto
        </button>
        <button class="accessibility-btn" onclick="document.body.style.fontSize='medium'">
            A- Diminuir Texto
        </button>
        <button class="accessibility-btn" onclick="document.body.classList.toggle('high-contrast')">
            Alto Contraste
        </button>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown(
        "<div class='top-navbar'>"
        "<div class='navbar-logo'>Sistema Folksonomia Digital</div>"
        "</div>", unsafe_allow_html=True)

def main():
    load_css()
    try: check_admin()
    except Exception as e: st.error(f"Erro ao inicializar: {e}")
    
    # Inicializar session state
    for k,v in [('user_id',gen_uid()), ('animal_name',generate_animal_name()),
                ('step','intro'), ('answers',{})]:
        if k not in st.session_state: st.session_state[k] = v
    
    # Controles de acessibilidade
    accessibility_controls()
    
    if st.session_state['step'] != 'completed':
        show_intro()
    else:
        show_header()
        st.markdown("<div class='main-content'>", unsafe_allow_html=True)
        t1, t2 = st.tabs([" Explorar Obras", " Area Administrativa"])
        with t1: show_obras()
        with t2: show_admin()
        st.markdown("</div>", unsafe_allow_html=True)

# ── INTRO ─────────────────────────────────────────────────────────────
def show_intro():
    st.markdown("<div class='main-content'>", unsafe_allow_html=True)
    st.markdown("<h1 class='main-title'>Sistema Folksonomia Digital</h1>", unsafe_allow_html=True)
    st.markdown("<p class='subtitle'>Sistema colaborativo de catalogacao de obras de arte<br>"
                "Complete o questionario para acessar a plataforma</p>", unsafe_allow_html=True)
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.markdown("<h2 style='text-align:center;margin-bottom:2.2rem;font-size:1.7rem'>"
                "Questionario de Acesso</h2>", unsafe_allow_html=True)
    with st.form("intro_form"):
        c1, c2 = st.columns(2)
        with c1:
            q1 = st.selectbox("1. Qual e o seu nivel de familiaridade com museus?",
                ["Nunca visito museus","Visito raramente","Visito ocasionalmente","Visito frequentemente"])
            q2 = st.selectbox("2. Voce ja ouviu falar sobre documentacao museologica?",
                ["Nunca ouvi falar","Ja ouvi, mas nao sei o que e","Tenho uma ideia basica","Conheco bem o tema"])
        with c2:
            q3 = st.text_area("3. O que voce entende por 'tags' ou etiquetas digitais aplicadas a acervo?",
                max_chars=500, height=200, placeholder="Descreva sua compreensao sobre o conceito...")
        _, cb, _ = st.columns([1,1,1])
        with cb:
            submit = st.form_submit_button("Acessar Plataforma", use_container_width=True)
        if submit:
            if not q3.strip():
                st.error("Por favor, responda todas as perguntas para continuar!")
            else:
                st.session_state['answers'] = {"q1":q1,"q2":q2,"q3":q3}
                save_answers(st.session_state['user_id'], st.session_state['animal_name'],
                             st.session_state['answers'])
                st.session_state['step'] = 'completed'
                st.success("Questionario completo! Acesso liberado.")
                st.balloons()
                st.rerun()
    st.markdown("</div></div>", unsafe_allow_html=True)

# ── GALERIA ───────────────────────────────────────────────────────────
def show_obras():
    st.markdown("<h1 class='main-title'>Galeria de Obras de Arte</h1>", unsafe_allow_html=True)
    st.markdown("<p class='subtitle'>Explore as obras e contribua com suas tags descritivas</p>",
                unsafe_allow_html=True)
    
    obras = load_obras()
    tags_df = all_tags()
    
    if not obras:
        st.info("Nenhuma obra cadastrada.")
        return
    
    # Filtros avançados
    filtered_obras = advanced_filters(obras, tags_df)
    
    st.markdown(f"<div style='text-align:center;color:white;margin:1.8rem 0;"
                f"font-size:1.1rem;font-weight:600'>Exibindo "
                f"<strong style='font-size:1.4rem'>{len(filtered_obras)}</strong> obra(s)</div>",
                unsafe_allow_html=True)
    
    # Galeria em grid
    cols = st.columns(3)
    for i, obra in enumerate(filtered_obras):
        with cols[i%3]:
            # Gerar descrição para acessibilidade
            if REQUESTS_AVAILABLE and PIL_AVAILABLE:
                img_desc = generate_image_description(obra['imagem'])
            else:
                img_desc = "Descrição de imagem não disponível"
            
            st.markdown(f"""
            <div class='obra-card'>
                <img src='{obra['imagem']}' alt='{obra['titulo']} - {obra['artista']}' />
                <div style='padding:1.4rem'>
                    <h3 style='font-size:1.05rem;font-weight:700;margin-bottom:.35rem'>
                        Obra #{obra['id']} - {obra['titulo']}
                    </h3>
                    <p style='font-size:.88rem;opacity:.65'>{obra['artista']} - {obra['ano']}</p>
            """, unsafe_allow_html=True)
            
            # Botão de descrição em áudio
            if st.session_state.accessibility['audio_descriptions']:
                if st.button("🔊 Descricao em Audio", key=f"audio_{obra['id']}"):
                    st.info(text_to_speech(f"{obra['titulo']} por {obra['artista']}. {img_desc}"))
            
            # Botão de tag
            if st.button(" Adicionar Tag", key=f"btn_{obra['id']}", use_container_width=True):
                st.session_state['selected_obra'] = obra
                st.rerun()
            
            # Formulário de tag
            if ('selected_obra' in st.session_state and
                    st.session_state['selected_obra']['id'] == obra['id']):
                with st.form(f"tf_{obra['id']}"):
                    tag = st.text_input("Sua tag:", key=f"t_{obra['id']}",
                                        placeholder="Ex: azul, triste, moderno…")
                    ca, cb = st.columns(2)
                    with ca: sub = st.form_submit_button(" Enviar", use_container_width=True)
                    with cb: can = st.form_submit_button(" Cancelar", use_container_width=True)
                    if sub and tag:
                        save_tag(st.session_state['user_id'], obra['id'], tag)
                        st.success(f"Tag '{tag}' adicionada!")
                        del st.session_state['selected_obra']
                        st.rerun()
                    if can:
                        del st.session_state['selected_obra']
                        st.rerun()
            
            # Mostrar tags do usuário
            ut = get_obra_user_tags(obra['id'], st.session_state['user_id'])
            if not ut.empty:
                st.markdown("**Suas Tags:**")
                st.markdown("".join(
                    f"<span class='tag-badge'>{r['tag']} ({r['count']})</span>"
                    for _, r in ut.iterrows()
                ), unsafe_allow_html=True)
            
            st.markdown("</div></div>", unsafe_allow_html=True)

# ── ADMIN ─────────────────────────────────────────────────────────────
def show_admin():
    if 'admin_logged_in' not in st.session_state:
        st.session_state['admin_logged_in'] = False
    
    if not st.session_state['admin_logged_in']:
        st.markdown("<h1 class='main-title'>Area Administrativa</h1>", unsafe_allow_html=True)
        st.markdown("<p class='subtitle'>Acesso restrito</p>", unsafe_allow_html=True)
        _, c2, _ = st.columns([1,1,1])
        with c2:
            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
            st.markdown("<h2 style='text-align:center;margin-bottom:1.8rem'>"
                        "Login Administrativo</h2>", unsafe_allow_html=True)
            with st.form("login"):
                username = st.text_input("Usuario:", placeholder="Digite seu usuario")
                password = st.text_input("Senha:", type="password", placeholder="Digite sua senha")
                sub = st.form_submit_button("Entrar no Sistema", use_container_width=True)
                if sub:
                    if check_login(username, password):
                        st.session_state['admin_logged_in'] = True
                        st.session_state['admin_username'] = username
                        st.success("Login realizado com sucesso!")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("Credenciais invalidas. Acesso negado.")
            st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.markdown(
            f"<h1 class='main-title'>Dashboard Administrativo</h1>"
            f"<p class='subtitle'>Bem-vindo, "
            f"<strong>{st.session_state.get('admin_username','Admin')}</strong></p>",
            unsafe_allow_html=True)
        
        tabs = st.tabs([
            " Visao Geral",
            " Analise de Tags",
            " Analise Avancada de Tags",
            " Conexoes de Tags",
            " Usuarios e Questionario",
            " Obras",
            " Exportar"
        ])
        
        with tabs[0]: tab_overview()
        with tabs[1]: tab_tags()
        with tabs[2]: tab_advanced_tags()
        with tabs[3]: tab_connections()
        with tabs[4]: tab_users_quest()
        with tabs[5]: tab_obras()
        with tabs[6]: tab_export()
        
        _, c2, _ = st.columns([1,1,1])
        with c2:
            if st.button(" Sair do Sistema", use_container_width=True):
                st.session_state['admin_logged_in'] = False
                st.rerun()

# ═════════════════════════════════════════════════════════════════════
# ABA 1 — VISAO GERAL
# ═════════════════════════════════════════════════════════════════════
def tab_overview():
    tdf = all_tags()
    udf = all_users()
    obs = load_obras()

    st.markdown("### Metricas Gerais do Sistema")
    total = len(tdf) if not tdf.empty else 0
    unicas = tdf['tag'].nunique() if not tdf.empty else 0
    nusers = udf['user_id'].nunique() if not udf.empty else 0
    nobs = len(obs)
    obs_ct = tdf['obra_id'].nunique() if not tdf.empty else 0

    c1,c2,c3,c4,c5 = st.columns(5)
    for col, lbl, val, sub, clr in [
        (c1,"Total de Tags", total, "registros","#a7e6ff"),
        (c2,"Tags Unicas", unicas, f"{unicas/total:.0%} do total" if total else "-","#d1baff"),
        (c3,"Participantes", nusers, "usuarios ativos","#6ee7b7"),
        (c4,"Obras Cadastradas", nobs, f"{obs_ct} com tags","#fcd34d"),
        (c5,"Media Tags/Usuario",f"{total/nusers:.1f}" if nusers else "-","por participante","#f9a8d4"),
    ]:
        with col: st.markdown(kpi(lbl,val,sub,clr), unsafe_allow_html=True)

    st.markdown(divider(), unsafe_allow_html=True)

    if not udf.empty and not tdf.empty:
        st.markdown("### Participantes Anonimos")
        uct = tdf.groupby('user_id').size().reset_index(name='tags')
        uuq = tdf.groupby('user_id')['tag'].nunique().reset_index(name='unicas')
        m = udf.merge(uct,on='user_id',how='left').merge(uuq,on='user_id',how='left').fillna(0)
        for _, row in m.iterrows():
            animal = row.get('animal_name','?')
            ts = row.get('timestamp','N/A')
            nt, nu = int(row['tags']), int(row['unicas'])
            p = nu/nt if nt>0 else 0
            st.markdown(
                f"<div class='stat-card stat-blue' style='padding:.85rem 1.3rem;margin:.25rem 0'>"
                f"<div style='display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px'>"
                f"<div><span class='animal-badge'>🐾 {animal}</span>"
                f"<span style='color:rgba(255,255,255,.45);font-size:.75rem;margin-left:10px'>Acesso: {ts}</span></div>"
                f"<div style='text-align:right;min-width:170px'>"
                f"<span style='color:white;font-weight:700'>{nt} tags</span>"
                f"<span style='color:rgba(255,255,255,.4);font-size:.78rem'> ({nu} unicas)</span>"
                f"{pbar(p,'#a7e6ff')}"
                f"<span style='color:rgba(255,255,255,.38);font-size:.7rem'>riqueza: {p:.0%}</span>"
                f"</div></div></div>", unsafe_allow_html=True)

    st.markdown(divider(), unsafe_allow_html=True)

    if not tdf.empty:
        od = {o['id']:o['titulo'] for o in obs}
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### Top 15 Tags Mais Usadas")
            top = tdf['tag'].value_counts().head(15).reset_index()
            top.columns = ['Tag','Qtd']
            top['%'] = (top['Qtd']/top['Qtd'].sum()*100).round(1)
            st.dataframe(top, use_container_width=True, hide_index=True)
        with c2:
            st.markdown("#### Obras Mais Tagueadas")
            ot = tdf.groupby('obra_id').size().reset_index(name='Tags')
            ot['Obra'] = ot['obra_id'].map(od)
            st.dataframe(
                ot[['Obra','Tags']].sort_values('Tags',ascending=False),
                use_container_width=True, hide_index=True)

# ═════════════════════════════════════════════════════════════════════
# ABA 2 — ANALISE DE TAGS (Frequencia + Temporal)
# ═════════════════════════════════════════════════════════════════════
def tab_tags():
    tdf = all_tags()
    if tdf.empty:
        st.info("Nenhuma tag disponivel.")
        return

    st.markdown("### Analise de Tags")
    t1, t2 = st.tabs([" Frequencia e Vocabulario", " Evolucao Temporal"])

    # --- FREQUENCIA ---
    with t1:
        freq = tdf['tag'].value_counts().reset_index()
        freq.columns = ['Tag','Frequencia']
        total_usos = freq['Frequencia'].sum()
        freq['% do Total'] = (freq['Frequencia']/total_usos*100).round(2)
        freq['% Acumulada'] = freq['% do Total'].cumsum().round(2)
        freq['Categoria'] = pd.cut(
            freq['Frequencia'],
            bins=[0,1,2,5,10,99999],
            labels=['Hapax (1x)','Rara (2x)','Ocasional (3-5x)','Frequente (6-10x)','Muito Frequente (10+x)']
        )

        hapax = (freq['Frequencia']==1).sum()
        lei80 = (freq['% Acumulada']<=80).sum()
        ttr = len(freq)/total_usos if total_usos else 0
        top1p = freq.iloc[0]['% do Total'] if not freq.empty else 0

        c1,c2,c3,c4 = st.columns(4)
        with c1: st.markdown(kpi("Vocabulario Total", len(freq), "tags distintas","#a7e6ff"), unsafe_allow_html=True)
        with c2: st.markdown(kpi("Hapax Legomena", hapax, f"{hapax/len(freq):.0%} do vocab.","#f9a8d4"), unsafe_allow_html=True)
        with c3: st.markdown(kpi("80% dos Usos", f"{lei80} tags","lei de Zipf","#6ee7b7"), unsafe_allow_html=True)
        with c4: st.markdown(kpi("Type-Token Ratio", f"{ttr:.3f}","riqueza global","#fcd34d"), unsafe_allow_html=True)

        st.markdown(insight(
            f"<strong>Distribuicao de Zipf:</strong> As {lei80} tags mais frequentes cobrem 80% de todos os usos. "
            f"Existem {hapax} hapax legomena — termos usados somente uma vez "
            f"({hapax/len(freq):.0%} do vocabulario total). "
            f"TTR global de <strong>{ttr:.3f}</strong> indica "
            f"{'alta' if ttr>0.5 else 'moderada' if ttr>0.25 else 'baixa'} diversidade lexical."
        ), unsafe_allow_html=True)

        st.markdown(divider(), unsafe_allow_html=True)
        st.markdown("#### Frequencia — Top 25 Tags")
        
        # Gráfico com matplotlib se plotly não estiver disponível
        if PLOTLY_AVAILABLE:
            fig = px.bar(freq.head(25), x='Tag', y='Frequencia',
                         title='Top 25 Tags Mais Frequentes',
                         color='Frequencia',
                         color_continuous_scale='Viridis')
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font_color='white'
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.bar_chart(freq.head(25).set_index('Tag')['Frequencia'])

        st.markdown("#### Tabela Completa de Frequencias")
        cat_opts = list(freq['Categoria'].cat.categories)
        cat_sel = st.multiselect("Filtrar por categoria:", cat_opts, default=cat_opts, key="fc")
        disp = freq[freq['Categoria'].isin(cat_sel)] if cat_sel else freq
        st.dataframe(disp, use_container_width=True, hide_index=True)

        c1, c2 = st.columns(2)
        with c1:
            st.download_button(
                " Frequencias (CSV)",
                freq.to_csv(index=False).encode('utf-8'),
                f"frequencias_{datetime.now().strftime('%Y%m%d')}.csv",
                "text/csv", use_container_width=True)
        with c2:
            st.markdown("**Distribuicao por Categoria:**")
            cd = freq['Categoria'].value_counts().reset_index()
            cd.columns = ['Categoria','Qtd']
            st.dataframe(cd, use_container_width=True, hide_index=True)

    # --- TEMPORAL ---
    with t2:
        st.markdown("#### Evolucao Temporal das Tags")
        try:
            tf = tdf.copy()
            tf['ts'] = pd.to_datetime(tf['timestamp'])
            tf['date'] = tf['ts'].dt.date
            tf['ano'] = tf['ts'].dt.year
            tf['mes'] = tf['ts'].dt.month
            tf['dia'] = tf['ts'].dt.day
            tf['hora'] = tf['ts'].dt.hour
            tf['dow'] = tf['ts'].dt.day_name()
            tf['semana'] = tf['ts'].dt.isocalendar().week.astype(int)

            # KPIs temporais
            dias_ativos = tf['date'].nunique()
            media_dia = len(tf)/dias_ativos if dias_ativos else 0
            pico_dia = tf.groupby('date').size()
            pico_val = int(pico_dia.max()) if not pico_dia.empty else 0
            pico_dt = str(pico_dia.idxmax()) if not pico_dia.empty else "-"

            c1,c2,c3,c4 = st.columns(4)
            with c1: st.markdown(kpi("Dias com Atividade", dias_ativos,"dias","#a7e6ff"), unsafe_allow_html=True)
            with c2: st.markdown(kpi("Media por Dia", f"{media_dia:.1f}","tags/dia","#6ee7b7"), unsafe_allow_html=True)
            with c3: st.markdown(kpi("Pico de Tags", pico_val,f"em {pico_dt}","#fcd34d"), unsafe_allow_html=True)
            with c4: st.markdown(kpi("Periodo Total", f"{dias_ativos} dias","registrado","#d1baff"), unsafe_allow_html=True)

            st.markdown(divider(), unsafe_allow_html=True)

            # Linha: tags por dia
            daily = tf.groupby('date').agg(
                Tags=('tag','count'),
                Tags_Unicas=('tag','nunique'),
                Usuarios=('user_id','nunique')
            ).reset_index().rename(columns={'date':'Data'})

            st.markdown("#### Tags Criadas por Dia")
            if PLOTLY_AVAILABLE:
                fig = px.line(daily, x='Data', y='Tags',
                             title='Evolucao Diaria de Tags',
                             color_discrete_sequence=['#a7e6ff'])
                fig.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font_color='white'
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.line_chart(daily.set_index('Data')['Tags'])

        except Exception as e:
            st.info(f"Dados insuficientes para analise temporal: {e}")

# ═════════════════════════════════════════════════════════════════════
# ABA 3 — ANALISE AVANCADA DE TAGS
# ═════════════════════════════════════════════════════════════════════
def tab_advanced_tags():
    tdf = all_tags()
    if tdf.empty:
        st.info("Nenhuma tag disponivel.")
        return

    st.markdown("### Analise Avancada de Tags")
    
    t1, t2, t3, t4 = st.tabs([
        " Estatisticas Avancadas",
        " Word Cloud",
        " Rede de Tags",
        " Clustering Hierarquico"
    ])

    with t1:
        st.markdown("#### Metricas Avancadas de Diversidade Lexical")
        
        analysis = advanced_tag_analysis(tdf)
        
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(kpi("Entropia de Shannon", f"{analysis['shannon_entropy']:.3f}",
                           "diversidade lexical", "#a7e6ff"), unsafe_allow_html=True)
            st.markdown(kpi("Indice de Simpson", f"{analysis['simpson_index']:.3f}",
                           "1 = maxima diversidade", "#6ee7b7"), unsafe_allow_html=True)
        with c2:
            st.markdown(kpi("Equitabilidade de Pielou", f"{analysis['pielou_evenness']:.3f}",
                           "uniformidade", "#fcd34d"), unsafe_allow_html=True)
            st.markdown(kpi("Hapax Legomena", f"{analysis['hapax_count']}",
                           f"{analysis['hapax_percentage']:.1f}% do vocabulario", "#f9a8d4"), unsafe_allow_html=True)
        with c3:
            st.markdown(kpi("Comprimento Medio das Tags", f"{analysis['avg_tag_length']:.1f}",
                           "caracteres", "#d1baff"), unsafe_allow_html=True)
            if analysis.get('peak_hour'):
                st.markdown(kpi("Horario de Pico", f"{analysis['peak_hour']:02d}:00",
                               "maior atividade", "#86efac"), unsafe_allow_html=True)

        st.markdown(divider(), unsafe_allow_html=True)
        
        # Distribuicao de comprimento das tags
        st.markdown("#### Distribuicao do Comprimento das Tags")
        tag_lengths = tdf['tag'].str.len()
        if PLOTLY_AVAILABLE:
            fig = px.histogram(x=tag_lengths, nbins=20,
                              title='Distribuicao do Numero de Caracteres por Tag',
                              labels={'x':'Comprimento', 'y':'Frequencia'},
                              color_discrete_sequence=['#a7e6ff'])
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font_color='white'
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.bar_chart(tag_lengths.value_counts().sort_index())

    with t2:
        st.markdown("#### Nuvem de Palavras (Word Cloud)")
        st.markdown("Visualizacao das tags mais frequentes")
        
        if WORDCLOUD_AVAILABLE and MATPLOTLIB_AVAILABLE:
            wordcloud = generate_wordcloud(tdf)
            if wordcloud:
                fig, ax = plt.subplots(figsize=(10, 5))
                ax.imshow(wordcloud, interpolation='bilinear')
                ax.axis('off')
                ax.set_facecolor('none')
                fig.patch.set_alpha(0)
                st.pyplot(fig)
        else:
            st.info("Bibliotecas para word cloud não disponíveis. Instale wordcloud e matplotlib para esta funcionalidade.")

    with t3:
        st.markdown("#### Rede de Conexoes entre Tags")
        st.markdown("Visualizacao em grafo das similaridades entre tags")
        
        if NETWORKX_AVAILABLE and MATPLOTLIB_AVAILABLE:
            threshold = st.slider("Limiar de similaridade para a rede:", 
                                 0.2, 0.8, 0.35, 0.05, key="network_thr")
            
            G = create_tag_network(tdf, threshold)
            
            if G and G.number_of_nodes() > 1:
                # Layout do grafo
                pos = nx.spring_layout(G, k=2, iterations=50)
                
                # Criar figura
                fig, ax = plt.subplots(figsize=(12, 8))
                
                # Tamanhos dos nos baseados na frequencia
                node_sizes = [G.nodes[node]['size'] * 50 for node in G.nodes()]
                
                # Desenhar grafo
                nx.draw_networkx_nodes(G, pos, node_size=node_sizes,
                                     node_color='#a7e6ff', alpha=0.8, ax=ax)
                nx.draw_networkx_edges(G, pos, alpha=0.3,
                                     edge_color='#d1baff', ax=ax)
                nx.draw_networkx_labels(G, pos, font_size=8,
                                       font_color='white', ax=ax)
                
                ax.set_facecolor('none')
                fig.patch.set_alpha(0)
                ax.axis('off')
                
                st.pyplot(fig)
                
                st.markdown(insight(
                    f"<strong>Grafo de Tags:</strong> A rede possui {G.number_of_nodes()} nos "
                    f"e {G.number_of_edges()} conexoes. Nos maiores representam tags mais frequentes."
                ), unsafe_allow_html=True)
            else:
                st.info("Nao ha conexoes suficientes para gerar a rede com este limiar.")
        else:
            st.info("Bibliotecas para visualização de rede não disponíveis. Instale networkx e matplotlib para esta funcionalidade.")

    with t4:
        st.markdown("#### Clustering Hierarquico de Tags")
        st.markdown("Agrupamento automatico de tags por similaridade semantica")
        
        if SCIPY_AVAILABLE and SKLEARN_AVAILABLE and MATPLOTLIB_AVAILABLE:
            n_clusters = st.slider("Numero de clusters:", 2, 10, 5, key="n_clusters")
            
            result, linkage_matrix = hierarchical_clustering(tdf, n_clusters)
            
            if result and linkage_matrix is not None:
                # Dendrograma
                fig, ax = plt.subplots(figsize=(12, 6))
                try:
                    unique_tags = tdf['tag'].unique()
                    dendrogram(linkage_matrix, ax=ax, leaf_rotation=90,
                              leaf_font_size=8, labels=unique_tags[:min(50, len(unique_tags))])
                    ax.set_title('Dendrograma de Agrupamento Hierarquico')
                    ax.set_ylabel('Distancia')
                    ax.set_facecolor('none')
                    fig.patch.set_alpha(0)
                    ax.tick_params(colors='white')
                    ax.title.set_color('white')
                    ax.yaxis.label.set_color('white')
                    st.pyplot(fig)
                    
                    # Mostrar clusters
                    st.markdown("#### Clusters Identificados")
                    for cluster_id, tags in result.items():
                        st.markdown(f"**Cluster {cluster_id + 1}** ({len(tags)} tags)")
                        tag_list = ", ".join(tags[:10])
                        if len(tags) > 10:
                            tag_list += f" e mais {len(tags) - 10}"
                        st.markdown(f"<span class='insight'>{tag_list}</span>", unsafe_allow_html=True)
                except Exception as e:
                    st.info(f"Não foi possível gerar o dendrograma: {e}")
        else:
            st.info("Bibliotecas para clustering não disponíveis. Instale scikit-learn e scipy para esta funcionalidade.")

# ═════════════════════════════════════════════════════════════════════
# ABA 4 — CONEXOES DE TAGS
# ═════════════════════════════════════════════════════════════════════
def tab_connections():
    tdf = all_tags()
    obs = load_obras()
    od = {o['id']:o['titulo'] for o in obs}
    if tdf.empty:
        st.warning("Nenhuma tag disponivel.")
        return

    st.markdown("### Conexoes e Agrupamentos de Tags")
    st.markdown(insight(
        "<strong>Como funciona:</strong> O algoritmo combina tres metricas — "
        "<strong>Contencao de substring</strong> (ex: 'vaso' → 'vaso verde'), "
        "<strong>Jaccard de palavras</strong> (ex: 'barco preto' ↔ 'barco de barro') e "
        "<strong>Jaccard de trigramas</strong> (similaridade fonetica). "
        "Score de 0 (sem relacao) a 1 (identicas)."
    ), unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1: threshold = st.slider("Limiar de similaridade:", 0.20, 0.90, 0.35, 0.05, key="ct")
    with c2: obra_f = st.selectbox("Filtrar por obra:", ["Todas"]+[f"#{o['id']} — {o['titulo']}" for o in obs], key="co")
    with c3: max_c = st.number_input("Max. conexoes:", 10, 300, 60, 10, key="cm")

    fdf = tdf.copy()
    if obra_f != "Todas":
        oid = int(obra_f.split("—")[0].replace("#","").strip())
        fdf = tdf[tdf['obra_id']==oid]

    all_t = fdf['tag'].tolist()
    if len(set(all_t)) < 2:
        st.warning("Necessario ao menos 2 tags distintas.")
        return

    with st.spinner("Calculando conexoes…"):
        conns = tag_connections(all_t, threshold=threshold)
        clusters = tag_clusters(all_t, threshold=threshold)

    c1,c2,c3 = st.columns(3)
    with c1: st.markdown(kpi("Total de Conexoes", len(conns), f"limiar ≥ {threshold:.2f}","#a7e6ff"), unsafe_allow_html=True)
    with c2: st.markdown(kpi("Grupos Formados", len(clusters),"clusters de tags","#d1baff"), unsafe_allow_html=True)
    with c3: st.markdown(kpi("Tags Envolvidas", len(set(c['tag_a'] for c in conns)|set(c['tag_b'] for c in conns)),
                              "tags conectadas","#6ee7b7"), unsafe_allow_html=True)

    st.markdown(divider(), unsafe_allow_html=True)

    t1, t2 = st.tabs([" Lista de Conexoes", " Grupos de Tags"])

    # --- LISTA ---
    with t1:
        if not conns:
            st.info("Nenhuma conexao encontrada. Reduza o limiar de similaridade.")
        else:
            tipos = sorted(set(c['tipo'] for c in conns))
            tipo_sel = st.multiselect("Filtrar por tipo:", tipos, default=tipos, key="tsel")
            cf = [c for c in conns if c['tipo'] in tipo_sel][:max_c]
            freq_map = tdf['tag'].value_counts().to_dict()

            st.markdown(f"Exibindo **{len(cf)}** de **{len(conns)}** conexoes")
            st.markdown(divider(), unsafe_allow_html=True)

            for c in cf:
                s = c['similaridade']
                bar = "█"*int(s*10)+"░"*(10-int(s*10))
                fa = freq_map.get(c['tag_a'],0)
                fb = freq_map.get(c['tag_b'],0)
                st.markdown(
                    f"<div class='conn-row'>"
                    f"<div style='display:flex;align-items:center;gap:10px;flex-wrap:wrap'>"
                    f"<span class='tag-badge'>{c['tag_a']}</span>"
                    f"<span style='color:rgba(255,255,255,.3);font-size:.72rem'>({fa}x)</span>"
                    f"<span style='color:rgba(255,255,255,.38)'>↔</span>"
                    f"<span class='tag-badge'>{c['tag_b']}</span>"
                    f"<span style='color:rgba(255,255,255,.3);font-size:.72rem'>({fb}x)</span>"
                    f"</div>"
                    f"<div style='text-align:right;min-width:195px'>"
                    f"<span style='font-family:monospace;color:rgba(255,255,255,.6);font-size:.78rem'>"
                    f"{bar} {s:.3f}</span><br>"
                    f"<span style='font-size:.7rem;color:rgba(255,255,255,.35)'>{c['tipo']}</span>"
                    f"</div></div>", unsafe_allow_html=True)

            st.markdown(divider(), unsafe_allow_html=True)
            st.download_button(
                " Baixar conexoes (CSV)",
                pd.DataFrame(conns).to_csv(index=False).encode('utf-8'),
                f"conexoes_{datetime.now().strftime('%Y%m%d')}.csv","text/csv")

    # --- CLUSTERS ---
    with t2:
        if not clusters:
            st.info("Nenhum grupo formado. Reduza o limiar de similaridade.")
        else:
            COLORS = ["#60a5fa","#34d399","#f9a8d4","#fcd34d","#a78bfa",
                      "#f87171","#67e8f9","#86efac","#fb923c","#c084fc"]
            freq_map = tdf['tag'].value_counts().to_dict()
            cls_sorted = sorted(clusters, key=len, reverse=True)

            st.markdown(f"**{len(cls_sorted)} grupo(s) de tags relacionadas**")
            st.markdown(divider(), unsafe_allow_html=True)

            for i, cl in enumerate(cls_sorted, 1):
                color = COLORS[(i-1) % len(COLORS)]
                total_uses = sum(freq_map.get(t,0) for t in cl)
                pills = "".join(
                    f"<span class='cluster-pill'>{t} "
                    f"<span style='opacity:.5;font-size:.7rem'>({freq_map.get(t,0)}x)</span></span>"
                    for t in sorted(cl, key=lambda x: freq_map.get(x,0), reverse=True)
                )
                st.markdown(
                    f"<div class='cluster-wrap' style='border-left:3px solid {color}'>"
                    f"<div class='cluster-title'>Grupo {i} · {len(cl)} tags · {total_uses} usos totais</div>"
                    f"{pills}</div>", unsafe_allow_html=True)

            st.markdown(divider(), unsafe_allow_html=True)
            st.markdown("#### Resumo dos Grupos")
            summ = pd.DataFrame([{
                "Grupo": f"Grupo {i}",
                "Qtd Tags": len(cl),
                "Total Usos": sum(freq_map.get(t,0) for t in cl),
                "Tags": ", ".join(sorted(cl,key=lambda x:freq_map.get(x,0),reverse=True)[:6])
                        + ("…" if len(cl)>6 else "")
            } for i,cl in enumerate(cls_sorted,1)])
            st.dataframe(summ, use_container_width=True, hide_index=True)

            st.download_button(
                " Baixar grupos (CSV)",
                summ.to_csv(index=False).encode('utf-8'),
                f"clusters_{datetime.now().strftime('%Y%m%d')}.csv","text/csv")

# ═════════════════════════════════════════════════════════════════════
# ABA 5 — USUARIOS E QUESTIONARIO
# ═════════════════════════════════════════════════════════════════════
def tab_users_quest():
    tdf = all_tags()
    udf = all_users()
    obs = load_obras()
    od = {o['id']:o['titulo'] for o in obs}

    if udf.empty:
        st.info("Nenhum dado de usuario disponivel.")
        return

    st.markdown("### Usuarios e Questionario")

    # KPIs combinados
    uct = tdf.groupby('user_id').size().reset_index(name='Total_Tags') if not tdf.empty else pd.DataFrame(columns=['user_id','Total_Tags'])
    uuq = tdf.groupby('user_id')['tag'].nunique().reset_index(name='Tags_Unicas') if not tdf.empty else pd.DataFrame(columns=['user_id','Tags_Unicas'])
    uob = tdf.groupby('user_id')['obra_id'].nunique().reset_index(name='Obras') if not tdf.empty else pd.DataFrame(columns=['user_id','Obras'])

    merged = udf.merge(uct,on='user_id',how='left') \
                .merge(uuq,on='user_id',how='left') \
                .merge(uob,on='user_id',how='left').fillna(0)
    merged['TTR'] = (merged['Tags_Unicas']/merged['Total_Tags'].replace(0,np.nan)).fillna(0).round(3)
    merged['Usuario'] = merged.apply(lambda r: r.get('animal_name', r['user_id'][:8]), axis=1)

    c1,c2,c3,c4 = st.columns(4)
    top_u = merged.loc[merged['Total_Tags'].idxmax(),'Usuario'] if not merged.empty else "-"
    with c1: st.markdown(kpi("Participantes", len(merged),"usuarios","#a7e6ff"), unsafe_allow_html=True)
    with c2: st.markdown(kpi("Media Tags/Usuario", f"{merged['Total_Tags'].mean():.1f}","","#6ee7b7"), unsafe_allow_html=True)
    with c3: st.markdown(kpi("Maior Contribuicao", int(merged['Total_Tags'].max()),top_u[:16],"#fcd34d"), unsafe_allow_html=True)
    with c4: st.markdown(kpi("Riqueza Media (TTR)", f"{merged['TTR'].mean():.2%}","vocabular","#d1baff"), unsafe_allow_html=True)

    st.markdown(divider(), unsafe_allow_html=True)

    t1, t2, t3, t4 = st.tabs([
        " Tabela de Participantes",
        " Perfil Individual",
        "Respostas do Questionario",
        " Cruzamentos"
    ])

    # --- TABELA ---
    with t1:
        st.markdown("#### Comparativo Geral de Participantes")
        dcols = ['Usuario','Total_Tags','Tags_Unicas','TTR','Obras','q1','q2']
        avail = [c for c in dcols if c in merged.columns]
        disp = merged[avail].rename(columns={
            'Total_Tags':'Tags Criadas','Tags_Unicas':'Tags Unicas',
            'Obras':'Obras Etiquetadas','q1':'Familiaridade c/ Museus',
            'q2':'Conhec. Museologico'
        }).sort_values('Tags Criadas',ascending=False)
        st.dataframe(disp, use_container_width=True, hide_index=True)

        st.markdown(divider(), unsafe_allow_html=True)
        st.markdown("#### Contribuicao por Participante")
        if PLOTLY_AVAILABLE:
            fig = px.bar(merged, x='Usuario', y='Total_Tags',
                        title='Numero de Tags Criadas por Participante',
                        color='Total_Tags',
                        color_continuous_scale='Viridis')
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font_color='white'
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.bar_chart(merged.set_index('Usuario')['Total_Tags'])

    # --- PERFIL INDIVIDUAL ---
    with t2:
        st.markdown("#### Perfil Detalhado por Participante")
        uopts = [f"🐾 {r.get('animal_name',r['user_id'][:8])}" for _,r in udf.iterrows()]
        usel = st.selectbox("Selecione um participante:", uopts, key="ui_sel")
        uidx = uopts.index(usel)
        uid = udf.iloc[uidx]['user_id']
        uanim = udf.iloc[uidx].get('animal_name', uid[:8])

        utags = tdf[tdf['user_id']==uid] if not tdf.empty else pd.DataFrame()
        if utags.empty:
            st.info("Este participante ainda nao criou tags.")
        else:
            ttl = len(utags); unq = utags['tag'].nunique()
            ttr_u = unq/ttl if ttl else 0

            c1,c2,c3 = st.columns(3)
            with c1: st.markdown(kpi("Tags Criadas", ttl,"","#a7e6ff"), unsafe_allow_html=True)
            with c2: st.markdown(kpi("Tags Unicas", unq,f"TTR: {ttr_u:.2%}","#6ee7b7"), unsafe_allow_html=True)
            with c3: st.markdown(kpi("Obras Tagueadas",utags['obra_id'].nunique(),"","#fcd34d"), unsafe_allow_html=True)

            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"**Top tags de {uanim}:**")
                if PLOTLY_AVAILABLE:
                    fig = px.bar(x=utags['tag'].value_counts().head(15).index,
                               y=utags['tag'].value_counts().head(15).values,
                               labels={'x':'Tag', 'y':'Frequencia'},
                               color_discrete_sequence=['#a7e6ff'])
                    fig.update_layout(
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        font_color='white'
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.bar_chart(utags['tag'].value_counts().head(15))
            with c2:
                st.markdown("**Distribuicao por obra:**")
                obra_counts = utags.groupby('obra_id').size()
                obra_counts.index = obra_counts.index.map(od)
                if PLOTLY_AVAILABLE:
                    fig = px.bar(x=obra_counts.index, y=obra_counts.values,
                               labels={'x':'Obra', 'y':'Tags'},
                               color_discrete_sequence=['#d1baff'])
                    fig.update_layout(
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        font_color='white'
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.bar_chart(obra_counts)

    # --- QUESTIONARIO ---
    with t3:
        st.markdown("#### Respostas do Questionario de Perfil")

        c1,c2 = st.columns(2)
        with c1:
            st.markdown("**Q1 — Familiaridade com Museus**")
            q1c = udf['q1'].value_counts()
            if PLOTLY_AVAILABLE:
                fig = px.bar(x=q1c.index, y=q1c.values,
                            labels={'x':'Resposta', 'y':'Quantidade'},
                            color_discrete_sequence=['#a7e6ff'])
                fig.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font_color='white'
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.bar_chart(q1c)

        with c2:
            st.markdown("**Q2 — Conhecimento sobre Documentacao Museologica**")
            q2c = udf['q2'].value_counts()
            if PLOTLY_AVAILABLE:
                fig = px.bar(x=q2c.index, y=q2c.values,
                            labels={'x':'Resposta', 'y':'Quantidade'},
                            color_discrete_sequence=['#d1baff'])
                fig.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font_color='white'
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.bar_chart(q2c)

# ═════════════════════════════════════════════════════════════════════
# ABA 6 — GESTAO DE OBRAS
# ═════════════════════════════════════════════════════════════════════
def tab_obras():
    st.markdown("### Gestao de Obras")
    obras = load_obras()
    t1, t2 = st.tabs(["Listar Obras","Adicionar Nova"])

    with t1:
        if obras:
            for obra in obras:
                c1,c2,c3 = st.columns([1,2,1])
                with c1: st.image(obra['imagem'], use_container_width=True)
                with c2:
                    st.markdown(f"**#{obra['id']} – {obra['titulo']}**")
                    st.markdown(f"*{obra['artista']} — {obra['ano']}*")
                    
                    # Gerar descrição para acessibilidade
                    if st.session_state.accessibility['audio_descriptions'] and REQUESTS_AVAILABLE and PIL_AVAILABLE:
                        img_desc = generate_image_description(obra['imagem'])
                        st.markdown(f"<small>{img_desc}</small>", unsafe_allow_html=True)
                        
                with c3:
                    if st.button(" Remover", key=f"del_{obra['id']}"):
                        obras.remove(obra)
                        save_json_file(OBRAS_FILE, obras)
                        st.success("Obra removida!")
                        st.cache_data.clear()
                        st.rerun()
                st.divider()
        else:
            st.info("Nenhuma obra cadastrada.")

    with t2:
        with st.form("add_obra"):
            titulo = st.text_input("Titulo da Obra")
            artista = st.text_input("Artista")
            ano = st.text_input("Ano")
            imagem = st.text_input("URL da Imagem")
            if st.form_submit_button(" Adicionar Obra"):
                if titulo and artista and ano and imagem:
                    nid = max([o['id'] for o in obras])+1 if obras else 1
                    obras.append({"id":nid,"titulo":titulo,"artista":artista,"ano":ano,"imagem":imagem})
                    save_json_file(OBRAS_FILE, obras)
                    st.success("Obra adicionada!")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("Preencha todos os campos!")

# ═════════════════════════════════════════════════════════════════════
# ABA 7 — EXPORTAR
# ═════════════════════════════════════════════════════════════════════
def tab_export():
    st.markdown("### Central de Exportacao")
    tdf = all_tags()
    udf = all_users()
    obs = load_obras()

    t1, t2 = st.tabs([" Exportacao Geral", " Por Participante"])

    with t1:
        c1,c2,c3 = st.columns(3)
        with c1:
            st.markdown("#### Tags")
            if not tdf.empty:
                st.download_button(" Todas as Tags (CSV)",
                    tdf.to_csv(index=False).encode('utf-8'),
                    f"tags_{datetime.now().strftime('%Y%m%d')}.csv","text/csv",
                    use_container_width=True)
                freq = tdf['tag'].value_counts().reset_index()
                freq.columns=['Tag','Frequencia']
                freq['%']=(freq['Frequencia']/freq['Frequencia'].sum()*100).round(2)
                st.download_button(" Frequencias (CSV)",
                    freq.to_csv(index=False).encode('utf-8'),
                    f"freq_{datetime.now().strftime('%Y%m%d')}.csv","text/csv",
                    use_container_width=True)
        with c2:
            st.markdown("#### Usuarios")
            if not udf.empty:
                st.download_button(" Usuarios (CSV)",
                    udf.to_csv(index=False).encode('utf-8'),
                    f"usuarios_{datetime.now().strftime('%Y%m%d')}.csv","text/csv",
                    use_container_width=True)
        with c3:
            st.markdown("#### Obras")
            if obs:
                st.download_button(" Obras (CSV)",
                    pd.DataFrame(obs).to_csv(index=False).encode('utf-8'),
                    f"obras_{datetime.now().strftime('%Y%m%d')}.csv","text/csv",
                    use_container_width=True)

        st.markdown(divider(), unsafe_allow_html=True)
        st.markdown("#### Exportar Conexoes de Tags")
        if not tdf.empty:
            thr = st.slider("Limiar de similaridade:", 0.2, 0.9, 0.35, 0.05, key="exp_thr")
            if st.button("Gerar arquivo de conexoes"):
                with st.spinner("Calculando…"):
                    conns = tag_connections(tdf['tag'].tolist(), threshold=thr)
                if conns:
                    cdf = pd.DataFrame(conns)
                    st.download_button(" Conexoes (CSV)",
                        cdf.to_csv(index=False).encode('utf-8'),
                        f"conexoes_{datetime.now().strftime('%Y%m%d')}.csv","text/csv",
                        use_container_width=True)
                    st.success(f"{len(conns)} conexoes exportadas.")
                else:
                    st.info("Nenhuma conexao encontrada com este limiar.")

    with t2:
        if udf.empty:
            st.info("Nenhum participante cadastrado.")
            return
        uopts = [f"🐾 {r.get('animal_name',r['user_id'][:8])}" for _,r in udf.iterrows()]
        usel = st.selectbox("Selecione um participante:", uopts, key="exp_u")
        uidx = uopts.index(usel)
        uid = udf.iloc[uidx]['user_id']
        uanim = udf.iloc[uidx].get('animal_name', uid[:8])

        st.markdown(f"#### Dados de: **{uanim}**")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("##### Questionario")
            st.download_button(" Respostas (CSV)",
                udf[udf['user_id']==uid].to_csv(index=False).encode('utf-8'),
                f"quest_{uid[:8]}.csv","text/csv", use_container_width=True)
        with c2:
            st.markdown("##### Tags Criadas")
            ut = get_user_tags(uid)
            if not ut.empty:
                st.download_button(" Tags (CSV)",
                    ut.to_csv(index=False).encode('utf-8'),
                    f"tags_{uid[:8]}.csv","text/csv", use_container_width=True)

if __name__ == "__main__":
    main()
