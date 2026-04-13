from __future__ import annotations

import base64
import hashlib
import json
import math
import os
import random
import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

try:
    import networkx as nx
    HAS_NETWORKX = True
except Exception:
    nx = None
    HAS_NETWORKX = False

import numpy as np
import pandas as pd

try:
    import plotly.express as px
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except Exception:
    px = None
    go = None
    HAS_PLOTLY = False

import streamlit as st

try:
    from sklearn.cluster import AgglomerativeClustering
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import accuracy_score
    from sklearn.metrics.pairwise import cosine_similarity
    from sklearn.model_selection import train_test_split
    HAS_SKLEARN = True
except Exception:
    AgglomerativeClustering = None
    TfidfVectorizer = None
    LogisticRegression = None
    accuracy_score = None
    cosine_similarity = None
    train_test_split = None
    HAS_SKLEARN = False

st.set_page_config(page_title="folksonomia", layout="wide", initial_sidebar_state="collapsed")


def safe_plotly_chart(fig: Any, *, use_container_width: bool = True) -> None:
    if HAS_PLOTLY and fig is not None:
        st.plotly_chart(fig, use_container_width=use_container_width)


def render_bar_chart_df(df: pd.DataFrame, x: str, y: str, *, orientation: str = "v", height: int = 360) -> None:
    if df is None or df.empty:
        st.info("Dados insuficientes para visualização.")
        return
    if HAS_PLOTLY:
        fig = px.bar(df, x=x, y=y, orientation=orientation)
        fig.update_layout(
            height=height,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=10, r=10, t=20, b=10),
        )
        safe_plotly_chart(fig, use_container_width=True)
        return
    fallback = df[[x, y]].copy()
    if orientation == "h":
        fallback = fallback.set_index(y)[x]
    else:
        fallback = fallback.set_index(x)[y]
    st.bar_chart(fallback)


def render_pie_chart_df(df: pd.DataFrame, names: str, values: str, *, height: int = 320) -> None:
    if df is None or df.empty:
        st.info("Dados insuficientes para visualização.")
        return
    if HAS_PLOTLY:
        fig = px.pie(df, names=names, values=values)
        fig.update_layout(height=height, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        safe_plotly_chart(fig, use_container_width=True)
        return
    st.bar_chart(df.set_index(names)[values])


def greedy_cluster_terms(values: Sequence[str], threshold: float = 0.66) -> List[List[str]]:
    unique_values = [value for value in dict.fromkeys([str(v).strip() for v in values if str(v).strip()])]
    if len(unique_values) < 2:
        return []
    groups: List[List[str]] = []
    for term in unique_values:
        placed = False
        for group in groups:
            ref = group[0]
            if hybrid_similarity(term, ref) >= threshold:
                group.append(term)
                placed = True
                break
        if not placed:
            groups.append([term])
    ordered = [sorted(group) for group in groups if len(group) > 1]
    ordered.sort(key=lambda item: (-len(item), item[0]))
    return ordered


def concept_similarity_rows(tag_text: str, rows: Sequence[Dict[str, Any]], top_k: int = 5) -> List[Dict[str, Any]]:
    scored: List[Dict[str, Any]] = []
    for row in rows:
        label = str(row.get("label", "")).strip()
        text_blob = str(row.get("text", label)).strip()
        score = max(hybrid_similarity(tag_text, label), hybrid_similarity(tag_text, text_blob))
        new_row = dict(row)
        new_row["similarity"] = float(score)
        scored.append(new_row)
    scored.sort(key=lambda item: item.get("similarity", 0.0), reverse=True)
    return scored[:top_k]

APP_TITLE = "folksonomia"
APP_ROOT = Path("data_folksonomia")
WORKS_FILE = APP_ROOT / "works.json"
USERS_FILE = APP_ROOT / "users.json"
TAGS_FILE = APP_ROOT / "tags.json"
CONCEPTS_FILE = APP_ROOT / "concepts.json"
VALIDATIONS_FILE = APP_ROOT / "validations.json"
SUGGESTIONS_FILE = APP_ROOT / "suggestions.json"
AUTOMATIONS_FILE = APP_ROOT / "automations.json"
MODEL_FILE = APP_ROOT / "model_state.json"
SETTINGS_FILE = APP_ROOT / "settings.json"
REPORTS_FILE = APP_ROOT / "reports.json"
ADMIN_FILE = APP_ROOT / "admin.json"

ADMIN_USERNAME = "nugep239@"
ADMIN_PASSWORD = "Artemis289@"
ENTITY_LABELS = ["pessoa", "lugar", "periodo", "material", "tecnica", "iconografia", "tema", "evento_historico", "grupo_social_cultural"]

PSEUDONYM_WORDS_A = ['Neblina','Atlas','Veludo','Orvalho','Prisma','Argila','Cromo','Cedro','Miragem','Aurora','Sombra','Bruma','Linho','Vidro','Marfim','Lótus','Névoa','Basalto','Íris','Nuvem','Fresta','Nexo','Lavra','Ângulo','Traço','Grão','Eco','Silêncio','Ponte','Lume','Gravura','Carta','Janela','Fôlego','Memória','Tecido','Arquivo','Escala','Rastro','Rumor','Tempo','Limiar','Pulso','Museu','Luz','Matiz','Camada','Grafo']
PSEUDONYM_WORDS_B = ['Claro','Sutil','Profundo','Moderno','Linear','Translúcido','Quieto','Semântico','Conectado','Analítico','Curatorial','Expandido','Aberto','Lento','Emergente','Refinado','Plural','Contextual','Digital','Relacional','Sensível','Institucional','Popular','Interligado','Latente','Vivo','Estrutural','Inteligente','Sintético','Dialógico','Contínuo','Documental','Participativo','Interpretativo','Experimental','Lexical','Temporal','Híbrido','Assistido','Persistente','Reconciliado','Desambiguado','Técnico','Social','Incremental','Curvo','Axial','Radial','Preciso']
STOPWORDS_PT = {'a','ao','aos','as','com','como','da','das','de','do','dos','e','em','entre','era','estar','foi','há','já','mais','muita','muitas','muito','muitos','na','nas','no','nos','não','o','os','ou','outra','outras','outro','outros','para','por','pouca','poucas','pouco','poucos','que','se','sem','ser','sim','sob','sobre','são','tais','tal','ter','um','uma','umas','uns','à','às','é'}
SEED_VOCAB = {'pessoa': ['artista','autor','retratado','mulher','homem','criança','anjo','santo','santa','virgem','maria','jesus','rei','rainha','soldado','camponês','pescador','músico','poeta','nobre','escravizado','trabalhador','operário','dançarina','mãe','pai','família','casal','autorretrato','personagem','figura humana','busto','grupo','multidão','povo','índio','indígena','africano','afro-brasileiro','europeu','colonizador','missionário','navegador','monarca','cavaleiro','pastor','profeta','apóstolo','deusa','deus','herói','heroína','guerreiro','sacerdote','monge','freira','senhora','menino','menina','jovem','idoso','mulher negra','mulher branca','homem negro','homem branco','companheira','viúva','esposa','marinheiro','cientista','curador','colecionador','pintor','escultor','arquiteto','artesão','tecelã','lavrador','bordadeira','curandeira','xamã','sambista','capoeirista','parteira','líder','trabalhadora','chefe de família','protagonista'],
 'lugar': ['rio de janeiro','brasil','lisboa','madrid','paris','roma','londres','américa','europa','africa','ásia','oceania','cidade','campo','praia','mar','porto','igreja','capela','templo','praça','rua','casa','palácio','favela','sertão','amazônia','bahia','minas gerais','pernambuco','são paulo','recife','salvador','niterói','museu','galeria','atelier','oficina','navio','floresta','montanha','rio','deserto','paisagem','interior','jardim','quintal','cozinha','sala','quarto','janela','varanda','terreiro','aldeia','quilombo','engenho','fazenda','mercado','hospital','escola','biblioteca','arquivo','acervo','ateliê','centro histórico','subúrbio','periferia','lago','ponte','estrada','cemitério','estação','metrô','porto seguro','ibero-américa','península','catedral','mosteiro','convento','ruína','sítio arqueológico'],
 'periodo': ['renascimento','barroco','rococó','neoclassicismo','romantismo','realismo','impressionismo','pós-impressionismo','modernismo','contemporâneo','medieval','antiguidade','século xvi','século xvii','século xviii','século xix','século xx','século xxi','colônia','império','república','ditadura','vanguarda','art déco','art nouveau','anos 1920','anos 1930','anos 1940','anos 1950','anos 1960','anos 1970','anos 1980','anos 1990','período colonial','período imperial','primeira república','segunda guerra','belle époque','era moderna','idade média','idade contemporânea','brasil colonial','brasil império','primeiro reinado','segundo reinado','primeira metade do século xx','segunda metade do século xx','virada do século','pós-guerra','tempo presente','contemporaneidade','passado','memória histórica'],
 'material': ['ouro','prata','bronze','ferro','aço','madeira','papel','tela','canvas','linho','algodão','barro','argila','terracota','porcelana','cerâmica','vidro','marfim','pedra','mármore','granito','gesso','tinta','óleo','aquarela','nanquim','grafite','carvão','pastel','pigmento','verniz','resina','plástico','acrílico','tecido','couro','osso','concha','madrepérola','folha de ouro','papel fotográfico','negativo','filme','poliéster','metal','latão','cobre','alumínio','bambu','palha','fibra','lã','seda','miçanga','pérola','semente','papelão','papel machê','betume','cimento','concreto','azulejo','esmalte','bordado','linha','barbante'],
 'tecnica': ['óleo sobre tela','aquarela','desenho','gravura','litografia','xilogravura','serigrafia','fotografia','colagem','escultura','modelagem','bordado','crochê','tecelagem','entalhe','fundição','esmaltagem','têmpera','mosaico','fresco','aguada','spray','estêncil','instalação','performance','vídeo','arte digital','impressão 3d','fotomontagem','assemblage','ponta seca','água-forte','água-tinta','cerâmica','pintura mural','grafite urbano','monotipia','gravura em metal','escultura em madeira','escultura em bronze','dobradura','costura','aplique','fusão','lapidação','fundição por cera perdida','xilo','tapeçaria','aerografia','relevo','baixo-relevo','alto-relevo','encáustica','gouache','pastel seco','pastel oleoso'],
 'iconografia': ['crucificação','anunciação','natividade','pietá','sagrada família','última ceia','madona','coroação','martírio','batalha','retratos oficiais','paisagem marinha','natureza-morta','vanitas','caça','colheita','festa','carnaval','procissão','trabalho','maternidade','família','escravidão','abolição','independência','mitologia','alegoria','trindade','santo antônio','são jorge','virgem maria','menino jesus','anjos','bandeira','barco','cavalo','flor','fruta','mesa posta','janela','espelho','violão','tambor','máscara','coroa','espada','livro','mapa','cidade ideal','naufrágio','dança','corpo','olhar','mão','casa','refeição','rede','ninho','tecido','costura','mulher chefe de família','ancestralidade','resistência'],
 'tema': ['religião','devoção','memória','identidade','ancestralidade','gênero','família','liderança feminina','trabalho','violência','guerra','paz','amor','solidão','natureza','urbanidade','poder','colonialismo','escravidão','resistência','território','migração','cotidiano','infância','velhice','celebração','luto','ritual','afeto','cuidado','maternidade','paternidade','saudade','esperança','fé','opressão','liberdade','desigualdade','classe social','raça','representação','corpo','política','nação','patrimônio','museu','documentação','arquivo','coleção','tecnologia','inovação','folksonomia','participação','acessibilidade','inclusão','curadoria','educação','comunidade','cultura popular','tradição','modernidade','futuro','tempo','silêncio','movimento'],
 'evento_historico': ['independência do brasil','abolição da escravidão','proclamação da república','segunda guerra mundial','primeira guerra mundial','revolução industrial','revolução francesa','descobrimento','chegada da corte','semana de 22','ditadura militar','redemocratização','queda da monarquia','guerra do paraguai','revolta da vacina','revolta da chibata','cabanagem','inconfidência mineira','conjuração baiana','revolução de 1930','golpe de 1964','diretas já','era vargas','confederação do equador','guerra fria','pós-abolição','expansão colonial','missões jesuíticas','reforma protestante','contrarreforma','concílio de trento'],
 'grupo_social_cultural': ['indígena','quilombola','afro-brasileiro','imigrante','camponês','elite','nobreza','clero','trabalhadores','mulheres','homens','crianças','idosos','famílias','comunidade','povo','pescadores','marinheiros','artistas','artesãos','moradores de favela','periferia','comunidade tradicional','ribeirinhos','povos originários','diáspora africana','irmandade','confraria','coletivo','movimento social','chefes de família','mães solo','operariado','burguesia','soldados','estudantes','migrantes','refugiados','sertanejos']}

SEED_CONCEPTS = []
for _cat_idx, (_cat, _samples) in enumerate(SEED_VOCAB.items(), 1):
    for _s_idx, _sample in enumerate(_samples, 1):
        SEED_CONCEPTS.append({
            'id': f'seed-{_cat_idx:02d}-{_s_idx:03d}',
            'label': _sample,
            'category': _cat,
            'aliases': [],
            'status': 'active',
            'source': 'seed'
        })

DEFAULT_WORKS = [
    {'title': 'Guernica', 'artist': 'Pablo Picasso', 'year': '1937',
     'description': 'Grande pintura histórica marcada por dor, fragmentação, guerra, corpo, cavalo, lâmpada e denúncia da violência.',
     'image_url': 'https://upload.wikimedia.org/wikipedia/en/7/74/PicassoGuernica.jpg',
     'institutional_tags': ['guerra', 'violência', 'corpo', 'modernismo', 'espanha']},
    {'title': 'A Noite Estrelada', 'artist': 'Vincent van Gogh', 'year': '1889',
     'description': 'Paisagem noturna em turbilhão cromático, céu, vila, ciprestes, movimento, emoção e atmosfera.',
     'image_url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/e/ea/Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg/1200px-Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg',
     'institutional_tags': ['paisagem', 'noite', 'céu', 'pós-impressionismo', 'emoção']},
    {'title': 'Mona Lisa', 'artist': 'Leonardo da Vinci', 'year': '1503',
     'description': 'Retrato em meio-corpo com sorriso enigmático, figura feminina, paisagem e refinamento renascentista.',
     'image_url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/e/ec/Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_retouched.jpg/800px-Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_retouched.jpg',
     'institutional_tags': ['retrato', 'mulher', 'renascimento', 'paisagem', 'olhar']},
]

DEFAULT_AUTOMATIONS = {
    "enabled": True,
    "min_confidence_auto_classify": 0.84,
    "min_similarity_auto_link": 0.88,
    "min_frequency_candidate_concept": 3,
    "auto_classify": True,
    "auto_link_concepts": False,
    "auto_generate_reports": True,
    "auto_flag_ambiguity": True,
    "auto_create_candidate_concepts": True,
}
DEFAULT_SETTINGS = {
    "public_intro_enabled": True,
    "require_comment": False,
    "show_semantic_suggestions": True,
    "show_related_works": True,
    "allow_guest_mode": True,
}

CSS_BLOCK = r"""
<style>
@import url("https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;500;600;700&display=swap");
:root {
    --glass: rgba(255,255,255,0.20);
    --glass-strong: rgba(255,255,255,0.30);
    --line: rgba(255,255,255,0.52);
    --text-0: #171717;
    --text-1: #242424;
    --text-2: #4a4a4a;
    --text-3: #6a6a6a;
    --shadow-soft: 0 18px 44px rgba(0,0,0,0.08);
    --shadow-hover: 0 24px 54px rgba(0,0,0,0.12);
}
html, body, [class*="css"], [data-testid="stMarkdownContainer"], p, span, label, div, button {
    font-family: "Times New Roman", Georgia, "Cormorant Garamond", serif !important;
}
@keyframes liquidShift {
    0% { background-position: 0% 50%, 100% 0%, 0% 100%, 50% 50%; }
    50% { background-position: 100% 50%, 0% 100%, 100% 0%, 50% 50%; }
    100% { background-position: 0% 50%, 100% 0%, 0% 100%, 50% 50%; }
}
@keyframes cardFloat {
    0% { transform: translateY(0px); }
    50% { transform: translateY(-5px); }
    100% { transform: translateY(0px); }
}
@keyframes shinePass {
    0% { left: -120%; }
    100% { left: 120%; }
}
body {
    background: linear-gradient(130deg, #d9d9d9 0%, #efefef 30%, #fafafa 58%, #d8d8d8 100%);
}
.stApp {
    color: var(--text-1);
    background:
        radial-gradient(circle at 14% 18%, rgba(255,255,255,0.78) 0%, rgba(255,255,255,0.08) 30%, transparent 58%),
        radial-gradient(circle at 84% 14%, rgba(255,255,255,0.65) 0%, rgba(255,255,255,0.06) 24%, transparent 50%),
        radial-gradient(circle at 80% 80%, rgba(255,255,255,0.54) 0%, rgba(255,255,255,0.05) 20%, transparent 42%),
        linear-gradient(135deg, #d3d3d3 0%, #ededed 32%, #fafafa 56%, #dddddd 100%);
    background-size: 180% 180%, 180% 180%, 180% 180%, 180% 180%;
    background-attachment: fixed;
    animation: liquidShift 18s ease-in-out infinite;
}
#MainMenu, footer, header, .stDeployButton { visibility: hidden; }
[data-testid="InputInstructions"], .stTextArea [data-testid="InputInstructions"] { display: none !important; }
section.main > div { padding-top: 0.4rem; }
.block-container { max-width: 1650px; padding-top: 1rem; padding-bottom: 3rem; }
.topbar {
    position: sticky; top: 0.55rem; z-index: 40;
    display: flex; justify-content: space-between; align-items: center; gap: 1rem;
    padding: 1rem 1.25rem; border-radius: 26px;
    background: rgba(255,255,255,0.24); border: 1px solid rgba(255,255,255,0.58);
    backdrop-filter: blur(28px) saturate(168%); -webkit-backdrop-filter: blur(28px) saturate(168%);
    box-shadow: 0 18px 46px rgba(0,0,0,0.08), inset 0 1px 0 rgba(255,255,255,0.70);
}
.brand-title { font-size: 2rem; font-weight: 700; letter-spacing: -0.05em; text-transform: lowercase; color: #1a1a1a; }
.hero-panel, .panel {
    background: rgba(255,255,255,0.22); border: 1px solid rgba(255,255,255,0.56);
    border-radius: 30px; backdrop-filter: blur(28px) saturate(168%); -webkit-backdrop-filter: blur(28px) saturate(168%);
    box-shadow: 0 20px 52px rgba(0,0,0,0.10), inset 0 1px 0 rgba(255,255,255,0.76);
}
.hero-panel { padding: 1.4rem 2rem; margin-top: 1rem; }
.hero-title { font-size: 4.2rem; line-height: 0.92; letter-spacing: -0.06em; color: #1f1f1f; margin: 0; }
.hero-microgrid, .metric-strip { display: grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap: 0.8rem; margin-top: 1rem; }
.kpi-box, .metric-card, .story-card, .preview-card, .work-card, .queue-card, .suggestion-card, .tag-compact-box {
    background: rgba(255,255,255,0.20); border: 1px solid rgba(255,255,255,0.52); border-radius: 26px;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.70), 0 12px 30px rgba(0,0,0,0.06);
}
.kpi-box, .metric-card { padding: 1rem; min-height: 112px; }
.kpi-label, .metric-caption, .story-title, .work-section-label {
    font-size: 0.74rem; text-transform: uppercase; letter-spacing: 0.18em; color: #727272;
}
.kpi-value, .metric-number { font-size: 2.2rem; color: #202020; letter-spacing: -0.05em; font-weight: 700; margin-top: 0.35rem; }
.kpi-foot, .metric-note, .work-card-meta { font-size: 0.82rem; color: #666666; margin-top: 0.3rem; }
.preview-card, .story-card, .queue-card, .suggestion-card, .tag-compact-box { padding: 1rem; }
.preview-card-title, .panel-title, .work-card-title { color: #202020; letter-spacing: -0.05em; }
.preview-card-title { font-size: 1.5rem; }
.panel { padding: 1.15rem; margin-top: 1rem; }
.panel-title { font-size: 2rem; }
.panel-subtitle, .preview-card-copy, .story-copy, .queue-text, .suggestion-meta, .work-card-text, .graph-note { color: #4a4a4a; line-height: 1.8; }
.work-card {
    position: relative; overflow: hidden; padding: 0.72rem; min-height: 280px;
    background: rgba(255,255,255,0.24);
    transition: transform 0.45s ease, box-shadow 0.45s ease, border-color 0.45s ease;
    cursor: pointer;
}
.work-card::before {
    content: ""; position: absolute; top: 0; left: -140%; width: 60%; height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.42), transparent);
    transform: skewX(-18deg);
}
.work-card:hover::before { animation: shinePass 0.9s ease forwards; }
.work-card:hover {
    transform: translateY(-8px) scale(1.015);
    box-shadow: 0 28px 56px rgba(0,0,0,0.12), inset 0 1px 0 rgba(255,255,255,0.76);
    border-color: rgba(255,255,255,0.70);
}
.work-card img {
    width: 100%; height: 240px; object-fit: cover; border-radius: 22px; display: block;
    transition: transform 0.70s ease, filter 0.70s ease;
}
.work-card:hover img { transform: scale(1.05); filter: saturate(1.04) contrast(1.03); }
/* compact tag input panel */
.tag-inline-panel {
    background: rgba(255,255,255,0.26);
    border: 1px solid rgba(255,255,255,0.60);
    border-radius: 26px;
    padding: 1.2rem 1.4rem;
    margin-top: 1.2rem;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.72), 0 14px 32px rgba(0,0,0,0.07);
    backdrop-filter: blur(24px);
}
.tag-inline-title { font-size: 1.1rem; font-weight: 700; color: #1a1a1a; letter-spacing: -0.03em; margin-bottom: 0.3rem; }
.tag-inline-sub { font-size: 0.82rem; color: #666; margin-bottom: 0.7rem; }
.tag-chip, .badge-soft {
    display: inline-flex; align-items: center; padding: 0.42rem 0.78rem; border-radius: 999px; margin: 0.18rem 0.18rem 0.18rem 0;
    background: rgba(255,255,255,0.22); border: 1px solid rgba(255,255,255,0.46); color: #2e2e2e; font-size: 0.84rem;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.60);
}
.soft-line { width: 100%; height: 1px; background: linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.82) 50%, transparent 100%); margin: 0.8rem 0 1rem 0; }
.stTabs [data-baseweb="tab-list"] {
    gap: 0.6rem; padding: 0.45rem; border-radius: 20px; background: rgba(255,255,255,0.18); border: 1px solid rgba(255,255,255,0.46);
    backdrop-filter: blur(18px);
}
.stTabs [data-baseweb="tab"] {
    background: rgba(255,255,255,0.18); border: 1px solid rgba(255,255,255,0.44); border-radius: 15px; color: #383838; font-weight: 600;
    transition: transform 0.25s ease, background 0.25s ease, box-shadow 0.25s ease;
}
.stTabs [data-baseweb="tab"]:hover { transform: translateY(-2px); background: rgba(255,255,255,0.26); }
.stTabs [aria-selected="true"] {
    background: rgba(255,255,255,0.34) !important; color: #1f1f1f !important; box-shadow: 0 8px 22px rgba(0,0,0,0.06) !important;
}
.stButton > button, .stDownloadButton > button {
    min-height: 46px; padding: 0.70rem 1.05rem !important; border-radius: 18px !important;
    background: rgba(255,255,255,0.22) !important; border: 1px solid rgba(255,255,255,0.54) !important; color: #1f1f1f !important;
    font-weight: 600 !important; box-shadow: inset 0 1px 0 rgba(255,255,255,0.70), 0 10px 22px rgba(0,0,0,0.06) !important;
    transition: transform 0.28s ease, box-shadow 0.28s ease, background 0.28s ease !important;
    backdrop-filter: blur(18px) saturate(150%) !important;
}
.stButton > button:hover, .stDownloadButton > button:hover {
    background: rgba(255,255,255,0.30) !important; transform: translateY(-3px) scale(1.01); box-shadow: 0 16px 30px rgba(0,0,0,0.08) !important;
}
.stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] > div, .stMultiSelect div[data-baseweb="select"] > div, .stNumberInput input {
    background: rgba(255,255,255,0.22) !important; border: 1px solid rgba(255,255,255,0.54) !important; border-radius: 18px !important;
    color: #1b1b1b !important; -webkit-text-fill-color: #1b1b1b !important; caret-color: #1b1b1b !important;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.68) !important; backdrop-filter: blur(18px) !important;
    font-weight: 600 !important;
}
.stTextArea textarea, textarea, .stTextInput input, input {
    color: #1b1b1b !important;
    -webkit-text-fill-color: #1b1b1b !important;
    opacity: 1 !important;
    caret-color: #1b1b1b !important;
    font-weight: 600 !important;
}
.stTextArea textarea::placeholder, textarea::placeholder, .stTextInput input::placeholder {
    color: #777777 !important;
    -webkit-text-fill-color: #777777 !important;
    opacity: 1 !important;
    font-weight: 400 !important;
}
.stSelectbox div[data-baseweb="select"] *, .stMultiSelect div[data-baseweb="select"] * { color: #2c2c2c !important; }
[data-testid="stMarkdownContainer"] p, [data-testid="stMarkdownContainer"] li, [data-testid="stMarkdownContainer"] span { color: #3d3d3d !important; }
[data-testid="stWidgetLabel"] p, [data-testid="stWidgetLabel"] span, [data-testid="stWidgetLabel"] label,
label, .stSelectbox label, .stTextArea label, .stTextInput label, .stMultiSelect label, .stNumberInput label { color: #2f2f2f !important; font-weight: 600 !important; }
.stAlert {
    background: rgba(255,255,255,0.22) !important; border: 1px solid rgba(255,255,255,0.54) !important; border-radius: 18px !important;
    backdrop-filter: blur(18px) !important;
}
[data-testid="stDataFrame"] {
    background: rgba(255,255,255,0.18) !important; border-radius: 18px !important; border: 1px solid rgba(255,255,255,0.40) !important; overflow: hidden;
}
.tag-preview-wrap { display: flex; flex-wrap: wrap; gap: 0.35rem; margin-top: 0.8rem; }
.tag-mini-note { font-size: 0.88rem; color: #555; margin-top: 0.35rem; }
.tag-compact-box { padding: 0.9rem; }
.summary-block {
    background: rgba(255,255,255,0.18);
    border: 1px solid rgba(255,255,255,0.48);
    border-radius: 22px;
    padding: 1rem 1.1rem;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.70), 0 12px 26px rgba(0,0,0,0.06);
    color: #333333;
    line-height: 1.8;
    margin-bottom: 0.8rem;
}
.summary-block strong { color: #141414; }
[data-testid="stSidebar"] { display: none; }
@media (max-width: 1100px) {
    .hero-microgrid, .metric-strip { grid-template-columns: repeat(2, minmax(0,1fr)); }
}
@media (max-width: 640px) {
    .hero-title { font-size: 2.8rem; }
    .hero-microgrid, .metric-strip { grid-template-columns: 1fr; }
    .work-card img { height: 200px; }
}
</style>
"""


@dataclass
class WorkRecord:
    id: str = ""
    title: str = ""
    artist: str = ""
    year: str = ""
    description: str = ""
    image_url: str = ""
    institutional_tags: List[str] = None
    museum: str = ""
    collection: str = ""
    place: str = ""
    period: str = ""
    technique: str = ""
    material: str = ""
    external_reference_label: str = ""
    external_reference_url: str = ""
    created_at: str = ""

@dataclass
class UserRecord:
    id: str = ""
    pseudonym: str = ""
    created_at: str = ""
    profile_familiarity: str = ""
    profile_documentation: str = ""
    profile_tags_understanding: str = ""

@dataclass
class TagRecord:
    id: str = ""
    work_id: str = ""
    user_id: str = ""
    tag: str = ""
    normalized_tag: str = ""
    comment: str = ""
    created_at: str = ""
    entity_prediction: str = ""
    entity_confidence: float = 0.0
    concept_id: str = ""
    concept_label: str = ""
    status: str = "pending"

@dataclass
class ValidationRecord:
    id: str = ""
    tag_id: str = ""
    validator: str = ""
    validated_entity: str = ""
    validated_concept_id: str = ""
    validated_concept_label: str = ""
    decision: str = ""
    notes: str = ""
    created_at: str = ""

@dataclass
class SuggestionRecord:
    id: str = ""
    tag_id: str = ""
    rule_name: str = ""
    suggestion_type: str = ""
    payload: Dict[str, Any] = None
    status: str = "open"
    created_at: str = ""


def now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def make_id(prefix: str) -> str:
    token = base64.urlsafe_b64encode(os.urandom(9)).decode("ascii").rstrip("=")
    return f"{prefix}-{token}"

def ensure_app_root() -> None:
    APP_ROOT.mkdir(exist_ok=True, parents=True)

def read_json(path: Path, default: Any) -> Any:
    ensure_app_root()
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default

def write_json(path: Path, payload: Any) -> None:
    ensure_app_root()
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

def normalize_text(value: str) -> str:
    value = (value or "").strip().lower()
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[_\-]+", " ", value)
    value = re.sub(r"[^a-z0-9\s]", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value

def tokenize(value: str) -> List[str]:
    text = normalize_text(value)
    return [part for part in text.split() if part and part not in STOPWORDS_PT]

def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default

def hash_password(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

def generate_pseudonym() -> str:
    return f"{random.choice(PSEUDONYM_WORDS_A)} {random.choice(PSEUDONYM_WORDS_B)}"

OPEN_DATA_SEEDS = {
    "guernica": {
        "museum": "Museo Reina Sofía",
        "collection": "Colección permanente",
        "place": "Madrid",
        "period": "modernismo",
        "technique": "óleo sobre tela",
        "material": "tela",
        "external_reference_label": "Wikidata",
        "external_reference_url": "https://www.wikidata.org/wiki/Q175036",
        "external_entities": ["Picasso", "Guerra Civil Espanhola", "arte moderna europeia"],
    },
    "a noite estrelada": {
        "museum": "Museum of Modern Art (MoMA)",
        "collection": "Painting and Sculpture",
        "place": "Nova York",
        "period": "pós-impressionismo",
        "technique": "óleo sobre tela",
        "material": "tela",
        "external_reference_label": "Wikidata",
        "external_reference_url": "https://www.wikidata.org/wiki/Q219831",
        "external_entities": ["Van Gogh", "paisagem noturna", "pós-impressionismo"],
    },
    "mona lisa": {
        "museum": "Musée du Louvre",
        "collection": "Département des Peintures",
        "place": "Paris",
        "period": "renascimento",
        "technique": "óleo sobre madeira",
        "material": "madeira",
        "external_reference_label": "Wikidata",
        "external_reference_url": "https://www.wikidata.org/wiki/Q12418",
        "external_entities": ["Leonardo da Vinci", "retrato", "Renascimento italiano"],
    },
}

def resolve_work_metadata(work: Dict[str, Any]) -> Dict[str, Any]:
    title_key = normalize_text(work.get("title", ""))
    seed = OPEN_DATA_SEEDS.get(title_key, {})
    return {
        "museum": work.get("museum") or seed.get("museum", ""),
        "collection": work.get("collection") or seed.get("collection", ""),
        "place": work.get("place") or seed.get("place", ""),
        "period": work.get("period") or seed.get("period", ""),
        "technique": work.get("technique") or seed.get("technique", ""),
        "material": work.get("material") or seed.get("material", ""),
        "external_reference_label": work.get("external_reference_label") or seed.get("external_reference_label", ""),
        "external_reference_url": work.get("external_reference_url") or seed.get("external_reference_url", ""),
        "external_entities": work.get("external_entities") or seed.get("external_entities", []),
    }

def semantic_tag_links(values: Sequence[str], threshold: float = 0.58) -> List[Dict[str, Any]]:
    unique_values = [v for v in dict.fromkeys([str(v).strip() for v in values if str(v).strip()])]
    rows = []
    for idx, source in enumerate(unique_values):
        for target in unique_values[idx + 1:]:
            score = hybrid_similarity(source, target)
            if score >= threshold:
                relation = "ortografia próxima" if trigram_similarity(source, target) >= 0.72 and jaccard_words(source, target) < 0.35 else "campo semântico comum"
                rows.append({"tag_a": source, "tag_b": target, "score": round(float(score), 3), "relation": relation})
    rows.sort(key=lambda r: r["score"], reverse=True)
    return rows

def typo_candidate_rows(values: Sequence[str], threshold: float = 0.78) -> List[Dict[str, Any]]:
    unique_values = [v for v in dict.fromkeys([str(v).strip() for v in values if str(v).strip()])]
    rows = []
    for idx, source in enumerate(unique_values):
        for target in unique_values[idx + 1:]:
            na, nb = normalize_text(source), normalize_text(target)
            if not na or not nb or na == nb:
                continue
            tri = trigram_similarity(source, target)
            jac = jaccard_words(source, target)
            if tri >= threshold or (tri >= 0.70 and jac >= 0.50):
                rows.append({"termo_a": source, "termo_b": target, "similaridade_trigrama": round(float(tri), 3), "sobreposição_palavras": round(float(jac), 3)})
    rows.sort(key=lambda r: (r["similaridade_trigrama"], r["sobreposição_palavras"]), reverse=True)
    return rows

def temporal_bucket(value: Any) -> str:
    try:
        dt = pd.to_datetime(value)
        return dt.strftime("%Y-%m")
    except Exception:
        return ""

def to_dataframe(items: List[Dict[str, Any]]) -> pd.DataFrame:
    return pd.DataFrame(items) if items else pd.DataFrame()

def first_sentence(text: str, default: str = "") -> str:
    text = (text or "").strip()
    if not text:
        return default
    parts = re.split(r"(?<=[.!?])\s+", text)
    return parts[0].strip() if parts else text

def jaccard_words(a: str, b: str) -> float:
    wa, wb = set(tokenize(a)), set(tokenize(b))
    if not wa and not wb:
        return 0.0
    return len(wa & wb) / max(1, len(wa | wb))

def char_trigrams(text: str) -> set:
    text = normalize_text(text)
    if len(text) <= 3:
        return {text} if text else set()
    return {text[i:i+3] for i in range(len(text)-2)}

def trigram_similarity(a: str, b: str) -> float:
    ta, tb = char_trigrams(a), char_trigrams(b)
    if not ta and not tb:
        return 0.0
    return len(ta & tb) / max(1, len(ta | tb))

def hybrid_similarity(a: str, b: str) -> float:
    na, nb = normalize_text(a), normalize_text(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    if na in nb or nb in na:
        base = min(len(na), len(nb)) / max(len(na), len(nb))
        return 0.60 + (0.40 * base)
    return 0.55 * trigram_similarity(na, nb) + 0.45 * jaccard_words(na, nb)


class JsonStore:
    def __init__(self) -> None:
        ensure_app_root()
        self.bootstrap()

    def bootstrap(self) -> None:
        write_json(ADMIN_FILE, {"username": ADMIN_USERNAME, "password": hash_password(ADMIN_PASSWORD)})
        if not WORKS_FILE.exists():
            works = []
            for item in DEFAULT_WORKS:
                works.append(asdict(WorkRecord(
                    id=make_id("work"), title=item["title"], artist=item["artist"],
                    year=item["year"], description=item["description"],
                    image_url=item["image_url"], institutional_tags=item["institutional_tags"],
                    created_at=now_iso(),
                )))
            write_json(WORKS_FILE, works)
        if not USERS_FILE.exists():
            write_json(USERS_FILE, [])
        if not TAGS_FILE.exists():
            write_json(TAGS_FILE, [])
        if not CONCEPTS_FILE.exists():
            write_json(CONCEPTS_FILE, SEED_CONCEPTS)
        if not VALIDATIONS_FILE.exists():
            write_json(VALIDATIONS_FILE, [])
        if not SUGGESTIONS_FILE.exists():
            write_json(SUGGESTIONS_FILE, [])
        if not AUTOMATIONS_FILE.exists():
            write_json(AUTOMATIONS_FILE, DEFAULT_AUTOMATIONS)
        if not MODEL_FILE.exists():
            write_json(MODEL_FILE, {"last_trained_at": "", "sample_count": 0, "accuracy": 0.0})
        if not SETTINGS_FILE.exists():
            write_json(SETTINGS_FILE, DEFAULT_SETTINGS)
        if not REPORTS_FILE.exists():
            write_json(REPORTS_FILE, [])

    def admin_ok(self, username: str, password: str) -> bool:
        data = read_json(ADMIN_FILE, {})
        return username == data.get("username") and hash_password(password) == data.get("password")

    def works(self) -> List[Dict[str, Any]]:
        items = read_json(WORKS_FILE, [])
        normalized_items = []
        for work in items:
            if not isinstance(work, dict):
                continue
            meta = resolve_work_metadata(work)
            updated = dict(work)
            for key, value in meta.items():
                if key not in updated or updated.get(key) in [None, ""]:
                    updated[key] = value
            if "institutional_tags" not in updated or updated["institutional_tags"] is None:
                updated["institutional_tags"] = []
            normalized_items.append(updated)
        return normalized_items

    def save_works(self, items: List[Dict[str, Any]]) -> None:
        write_json(WORKS_FILE, items)

    def users(self) -> List[Dict[str, Any]]:
        return read_json(USERS_FILE, [])

    def save_users(self, items: List[Dict[str, Any]]) -> None:
        write_json(USERS_FILE, items)

    def tags(self) -> List[Dict[str, Any]]:
        return read_json(TAGS_FILE, [])

    def save_tags(self, items: List[Dict[str, Any]]) -> None:
        write_json(TAGS_FILE, items)

    def concepts(self) -> List[Dict[str, Any]]:
        return read_json(CONCEPTS_FILE, [])

    def save_concepts(self, items: List[Dict[str, Any]]) -> None:
        write_json(CONCEPTS_FILE, items)

    def validations(self) -> List[Dict[str, Any]]:
        return read_json(VALIDATIONS_FILE, [])

    def save_validations(self, items: List[Dict[str, Any]]) -> None:
        write_json(VALIDATIONS_FILE, items)

    def suggestions(self) -> List[Dict[str, Any]]:
        return read_json(SUGGESTIONS_FILE, [])

    def save_suggestions(self, items: List[Dict[str, Any]]) -> None:
        write_json(SUGGESTIONS_FILE, items)

    def automations(self) -> Dict[str, Any]:
        return read_json(AUTOMATIONS_FILE, DEFAULT_AUTOMATIONS.copy())

    def save_automations(self, items: Dict[str, Any]) -> None:
        write_json(AUTOMATIONS_FILE, items)

    def model_state(self) -> Dict[str, Any]:
        return read_json(MODEL_FILE, {"last_trained_at": "", "sample_count": 0, "accuracy": 0.0})

    def save_model_state(self, items: Dict[str, Any]) -> None:
        write_json(MODEL_FILE, items)

    def settings(self) -> Dict[str, Any]:
        return read_json(SETTINGS_FILE, DEFAULT_SETTINGS.copy())

    def save_settings(self, items: Dict[str, Any]) -> None:
        write_json(SETTINGS_FILE, items)

    def reports(self) -> List[Dict[str, Any]]:
        return read_json(REPORTS_FILE, [])

    def save_reports(self, items: List[Dict[str, Any]]) -> None:
        write_json(REPORTS_FILE, items)

    def create_or_get_user(self, familiarity: str, documentation: str, understanding: str) -> Dict[str, Any]:
        if st.session_state.get("session_user_id"):
            existing = self.find_user(st.session_state["session_user_id"])
            if existing:
                return existing
        users = self.users()
        user = asdict(UserRecord(
            id=make_id("user"), pseudonym=generate_pseudonym(), created_at=now_iso(),
            profile_familiarity=familiarity, profile_documentation=documentation,
            profile_tags_understanding=understanding,
        ))
        users.append(user)
        self.save_users(users)
        st.session_state["session_user_id"] = user["id"]
        return user

    def find_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        for item in self.users():
            resolved_id = item.get("id") or item.get("user_id")
            if resolved_id == user_id:
                if item.get("id") != resolved_id:
                    item["id"] = resolved_id
                return item
        return None

    def add_work(self, title, artist, year, description, image_url, institutional_tags,
                 museum="", collection="", place="", period="", technique="", material="",
                 external_reference_label="", external_reference_url="") -> Dict[str, Any]:
        items = self.works()
        payload = asdict(WorkRecord(
            id=make_id("work"), title=title.strip(), artist=artist.strip(), year=year.strip(),
            description=description.strip(), image_url=image_url.strip(),
            institutional_tags=[t.strip() for t in institutional_tags if t.strip()],
            museum=museum.strip(), collection=collection.strip(), place=place.strip(),
            period=period.strip(), technique=technique.strip(), material=material.strip(),
            external_reference_label=external_reference_label.strip(),
            external_reference_url=external_reference_url.strip(), created_at=now_iso(),
        ))
        payload["external_entities"] = resolve_work_metadata(payload).get("external_entities", [])
        items.append(payload)
        self.save_works(items)
        return payload

    def update_work(self, work_id: str, updates: Dict[str, Any]) -> None:
        items = self.works()
        for work in items:
            if work.get("id") == work_id:
                work.update(updates)
                break
        self.save_works(items)

    def add_concept(self, label: str, category: str, aliases: List[str], source: str = "manual") -> Dict[str, Any]:
        items = self.concepts()
        concept = {"id": make_id("concept"), "label": label.strip(), "category": category.strip(),
                   "aliases": [a.strip() for a in aliases if a.strip()], "status": "active", "source": source}
        items.append(concept)
        self.save_concepts(items)
        return concept

    def submit_tag(self, work_id: str, user_id: str, tag: str, comment: str, ml: "SemanticLearner") -> Dict[str, Any]:
        items = self.tags()
        prediction = ml.predict_entity(tag)
        concept = ml.suggest_concept(tag)
        payload = asdict(TagRecord(
            id=make_id("tag"), work_id=work_id, user_id=user_id,
            tag=tag.strip(), normalized_tag=normalize_text(tag), comment=comment.strip(),
            created_at=now_iso(), entity_prediction=prediction.get("label", ""),
            entity_confidence=safe_float(prediction.get("confidence", 0.0)),
            concept_id=concept.get("id", "") if concept else "",
            concept_label=concept.get("label", "") if concept else "", status="pending",
        ))
        items.append(payload)
        self.save_tags(items)
        return payload

    def update_tag(self, tag_id: str, updates: Dict[str, Any]) -> None:
        items = self.tags()
        for tag in items:
            if tag.get("id") == tag_id:
                tag.update(updates)
                break
        self.save_tags(items)

    def add_validation(self, tag_id, validator, validated_entity, validated_concept_id, validated_concept_label, decision, notes) -> Dict[str, Any]:
        items = self.validations()
        payload = asdict(ValidationRecord(
            id=make_id("validation"), tag_id=tag_id, validator=validator,
            validated_entity=validated_entity, validated_concept_id=validated_concept_id,
            validated_concept_label=validated_concept_label, decision=decision, notes=notes, created_at=now_iso(),
        ))
        items.append(payload)
        self.save_validations(items)
        return payload

    def add_suggestion(self, tag_id, rule_name, suggestion_type, payload) -> Dict[str, Any]:
        items = self.suggestions()
        suggestion = asdict(SuggestionRecord(
            id=make_id("sugg"), tag_id=tag_id, rule_name=rule_name,
            suggestion_type=suggestion_type, payload=payload, status="open", created_at=now_iso(),
        ))
        items.append(suggestion)
        self.save_suggestions(items)
        return suggestion

    def close_suggestion(self, suggestion_id: str, status: str = "resolved") -> None:
        items = self.suggestions()
        for s in items:
            if s.get("id") == suggestion_id:
                s["status"] = status
                break
        self.save_suggestions(items)


class SemanticLearner:
    def __init__(self, store: JsonStore) -> None:
        self.store = store
        self.entity_vectorizer = None
        self.entity_model = None
        self.entity_labels: List[str] = []
        self.entity_accuracy: float = 0.0
        self.entity_samples: int = 0
        self.concept_vectorizer = None
        self.concept_matrix = None
        self.concept_rows: List[Dict[str, Any]] = []
        self.train()

    def build_training_corpus(self) -> pd.DataFrame:
        rows = []
        for label, samples in SEED_VOCAB.items():
            for sample in samples:
                rows.append({"text": sample, "label": label, "source": "seed"})
        for concept in self.store.concepts():
            category = str(concept.get("category", "")).strip()
            if not category:
                continue
            label = str(concept.get("label", "")).strip()
            if label:
                rows.append({"text": label, "label": category, "source": "concept"})
            for alias in concept.get("aliases", []) or []:
                if str(alias).strip():
                    rows.append({"text": str(alias).strip(), "label": category, "source": "alias"})
        for work in self.store.works():
            meta = resolve_work_metadata(work)
            description = work.get("description", "")
            for tag in work.get("institutional_tags", []) or []:
                rows.append({"text": f"{tag} {description}".strip(), "label": "tema", "source": "institutional"})
            field_map = {"place": "lugar", "period": "periodo", "technique": "tecnica", "material": "material"}
            for field, lbl in field_map.items():
                value = str(meta.get(field, "")).strip()
                if value:
                    rows.append({"text": value, "label": lbl, "source": "metadata"})
            artist = str(work.get("artist", "")).strip()
            if artist:
                rows.append({"text": artist, "label": "pessoa", "source": "artist"})
        tag_index = {item.get("id"): item for item in self.store.tags()}
        for validation in self.store.validations():
            if validation.get("decision") not in {"approved", "auto-approved", "linked"}:
                continue
            tag_row = tag_index.get(validation.get("tag_id"))
            if not tag_row:
                continue
            entity = validation.get("validated_entity") or tag_row.get("entity_prediction") or "tema"
            tag_text = " ".join([str(tag_row.get("tag", "")), str(tag_row.get("comment", ""))]).strip()
            if tag_text:
                rows.append({"text": tag_text, "label": entity, "source": "validation"})
            if validation.get("validated_concept_label"):
                rows.append({"text": validation.get("validated_concept_label"), "label": entity, "source": "concept"})
        df = pd.DataFrame(rows)
        if df.empty:
            return df
        df = df[df["text"].astype(str).str.strip() != ""]
        return df.reset_index(drop=True)

    def build_concept_matrix(self) -> None:
        concepts = [c for c in self.store.concepts() if c.get("status") != "archived"]
        rows = []
        for c in concepts:
            alias_text = " ".join(c.get("aliases", []))
            rows.append({"id": c.get("id", ""), "label": c.get("label", ""), "category": c.get("category", ""),
                         "text": f"{c.get('label', '')} {alias_text} {c.get('category', '')}".strip()})
        self.concept_rows = rows
        if not rows or not HAS_SKLEARN:
            self.concept_vectorizer = None
            self.concept_matrix = None
            return
        self.concept_vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=1)
        self.concept_matrix = self.concept_vectorizer.fit_transform([r["text"] for r in rows])

    def train(self) -> None:
        corpus = self.build_training_corpus()
        self.entity_samples = int(len(corpus))
        if (not HAS_SKLEARN) or len(corpus) < 20 or corpus["label"].nunique() < 2:
            self.entity_vectorizer = None
            self.entity_model = None
            self.entity_labels = []
            self.entity_accuracy = 0.0
            self.build_concept_matrix()
            return
        vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=1, sublinear_tf=True)
        X = vectorizer.fit_transform(corpus["text"])
        y = corpus["label"].astype(str).values
        try:
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.20, random_state=42, stratify=y)
            model = LogisticRegression(max_iter=1200, multi_class="auto")
            model.fit(X_train, y_train)
            preds = model.predict(X_test)
            self.entity_accuracy = float(accuracy_score(y_test, preds))
        except Exception:
            model = LogisticRegression(max_iter=1200, multi_class="auto")
            model.fit(X, y)
            self.entity_accuracy = 0.0
        self.entity_vectorizer = vectorizer
        self.entity_model = model
        self.entity_labels = sorted(set(y))
        self.build_concept_matrix()
        self.store.save_model_state({
            "last_trained_at": now_iso(),
            "sample_count": self.entity_samples,
            "accuracy": round(float(self.entity_accuracy), 4),
        })

    def heuristic_entity(self, text: str) -> str:
        score_map = defaultdict(float)
        for label, samples in SEED_VOCAB.items():
            for sample in samples[:80]:
                score = hybrid_similarity(text, sample)
                if score > score_map[label]:
                    score_map[label] = score
        if not score_map:
            return "tema"
        best_label, best_score = max(score_map.items(), key=lambda r: r[1])
        return best_label if best_score >= 0.30 else "tema"

    def predict_entity(self, text: str) -> Dict[str, Any]:
        sample = (text or "").strip()
        if not sample:
            return {"label": "", "confidence": 0.0, "proba": {}}
        if self.entity_vectorizer is None or self.entity_model is None:
            label = self.heuristic_entity(sample)
            return {"label": label, "confidence": 0.55, "proba": {label: 0.55}}
        X = self.entity_vectorizer.transform([sample])
        probs = self.entity_model.predict_proba(X)[0]
        idx = int(np.argmax(probs))
        label = str(self.entity_model.classes_[idx])
        return {"label": label, "confidence": float(probs[idx]),
                "proba": {cls: float(p) for cls, p in zip(self.entity_model.classes_, probs)}}

    def suggest_concept(self, tag_text: str) -> Dict[str, Any]:
        results = self.suggest_concepts(tag_text, top_k=1)
        return results[0] if results else {}

    def suggest_concepts(self, tag_text: str, top_k: int = 5) -> List[Dict[str, Any]]:
        if not self.concept_rows:
            return []
        if (not HAS_SKLEARN) or self.concept_vectorizer is None or self.concept_matrix is None:
            return concept_similarity_rows(tag_text, self.concept_rows, top_k=top_k)
        X = self.concept_vectorizer.transform([tag_text])
        sims = cosine_similarity(X, self.concept_matrix)[0]
        idxs = np.argsort(sims)[::-1][:top_k]
        out = []
        for idx in idxs:
            row = dict(self.concept_rows[int(idx)])
            row["similarity"] = float(sims[int(idx)])
            out.append(row)
        return out

    def related_tags(self, values: Sequence[str], reference: str, top_k: int = 8) -> List[Tuple[str, float]]:
        seen = set()
        rows = []
        for value in values:
            value = str(value).strip()
            if not value or value in seen:
                continue
            seen.add(value)
            score = hybrid_similarity(reference, value)
            if score > 0:
                rows.append((value, score))
        rows.sort(key=lambda r: r[1], reverse=True)
        return rows[:top_k]

    def cluster_terms(self, values: Sequence[str], threshold: float = 0.66) -> List[List[str]]:
        unique_values = [v for v in dict.fromkeys([str(v).strip() for v in values if str(v).strip()])]
        if len(unique_values) < 2:
            return []
        if not HAS_SKLEARN:
            return greedy_cluster_terms(unique_values, threshold=threshold)
        vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=1)
        X = vectorizer.fit_transform(unique_values)
        similarity = cosine_similarity(X)
        distance = 1 - similarity
        model = AgglomerativeClustering(metric="precomputed", linkage="average",
                                         distance_threshold=max(0.001, 1 - threshold), n_clusters=None)
        labels = model.fit_predict(distance)
        groups = defaultdict(list)
        for term, label in zip(unique_values, labels):
            groups[int(label)].append(term)
        ordered = [sorted(g) for g in groups.values() if len(g) > 1]
        ordered.sort(key=lambda g: (-len(g), g[0]))
        return ordered

    def term_features(self, tag_text: str) -> Dict[str, Any]:
        tokens = tokenize(tag_text)
        prediction = self.predict_entity(tag_text)
        concepts = self.suggest_concepts(tag_text, top_k=3)
        return {"normalized": normalize_text(tag_text), "token_count": len(tokens), "tokens": tokens,
                "entity": prediction.get("label", ""), "confidence": prediction.get("confidence", 0.0), "concepts": concepts}


def build_tag_dataframe(store: JsonStore) -> pd.DataFrame:
    tags = to_dataframe(store.tags())
    if tags.empty:
        return tags
    tags["tag"] = tags["tag"].astype(str)
    tags["normalized_tag"] = tags["normalized_tag"].astype(str) if "normalized_tag" in tags.columns else tags["tag"].map(normalize_text)
    users = to_dataframe(store.users())
    works = to_dataframe(store.works())
    concepts = to_dataframe(store.concepts())
    validations = to_dataframe(store.validations())
    if not works.empty:
        work_cols = [c for c in ["id", "title", "artist", "year", "museum", "collection", "place", "period", "technique", "material"] if c in works.columns]
        tags = tags.merge(works[work_cols].rename(columns={
            "id": "work_id", "title": "work_title", "artist": "work_artist", "year": "work_year",
            "museum": "work_museum", "collection": "work_collection", "place": "work_place",
            "period": "work_period", "technique": "work_technique", "material": "work_material",
        }), on="work_id", how="left")
    if not users.empty:
        user_cols = [c for c in ["id", "pseudonym", "profile_familiarity"] if c in users.columns]
        tags = tags.merge(users[user_cols].rename(columns={"id": "user_id", "pseudonym": "user_pseudonym"}), on="user_id", how="left")
    if not concepts.empty and "concept_id" in tags.columns:
        tags = tags.merge(
            concepts[[c for c in ["id", "label", "category"] if c in concepts.columns]].rename(
                columns={"id": "concept_id", "label": "concept_resolved_label", "category": "concept_resolved_category"}),
            on="concept_id", how="left")
    if not validations.empty:
        latest = validations.sort_values("created_at").groupby("tag_id").tail(1)
        tags = tags.merge(
            latest[[c for c in ["tag_id", "validated_entity", "validated_concept_label", "decision", "notes"] if c in latest.columns]],
            left_on="id", right_on="tag_id", how="left")
    tags["created_at"] = tags["created_at"].astype(str)
    tags["created_ts"] = pd.to_datetime(tags["created_at"], errors="coerce")
    tags["created_date"] = tags["created_ts"].dt.date.astype(str)
    tags["created_hour"] = tags["created_ts"].dt.hour.fillna(0).astype(int)
    tags["created_weekday"] = tags["created_ts"].dt.day_name().fillna("")
    tags["created_month"] = tags["created_ts"].dt.strftime("%Y-%m").fillna("")
    tags["is_validated"] = tags.get("decision", pd.Series([""] * len(tags))).fillna("").isin(["approved", "auto-approved", "linked"])
    return tags

def build_public_metrics(tags_df, works_df, users_df) -> Dict[str, Any]:
    total_tags = int(len(tags_df)) if not tags_df.empty else 0
    unique_tags = int(tags_df["normalized_tag"].nunique()) if not tags_df.empty else 0
    active_users = int(users_df["id"].nunique()) if not users_df.empty else 0
    tagged_works = int(tags_df["work_id"].nunique()) if not tags_df.empty else 0
    return {
        "total_tags": total_tags, "unique_tags": unique_tags, "active_users": active_users,
        "works": int(len(works_df)) if not works_df.empty else 0, "tagged_works": tagged_works,
        "lexical_density": float(unique_tags / total_tags) if total_tags else 0.0,
    }


def _analysis_summary_blocks(store: JsonStore, ml: SemanticLearner) -> Dict[str, str]:
    tags_df = build_tag_dataframe(store)
    validations_df = to_dataframe(store.validations())
    concepts_df = to_dataframe(store.concepts())
    if tags_df.empty:
        return {
            "ml": "Nenhuma tag registrada ainda. O modelo usará apenas o vocabulário inicial até receber marcações validadas.",
            "validation": "Nenhuma tag disponível para curadoria. Aguarde a participação do público.",
            "graph": "A rede será construída automaticamente quando obras, tags e conceitos começarem a acumular relações.",
        }
    total = len(tags_df)
    unique = int(tags_df["normalized_tag"].nunique())
    validated = int(tags_df.get("is_validated", pd.Series([False]*len(tags_df))).sum())
    pending = total - validated
    density = f"{unique/total:.2f}" if total else "0.00"
    entity_dist = tags_df["entity_prediction"].replace("", "tema").value_counts().head(4)
    entity_text = " · ".join([f"{idx} ({int(val)})" for idx, val in entity_dist.items()]) if not entity_dist.empty else "sem dados"
    concept_hits = tags_df["concept_label"].fillna("").astype(str)
    concept_hits = concept_hits[concept_hits.str.strip() != ""].value_counts().head(4)
    concept_text = " · ".join([f"{idx} ({int(val)})" for idx, val in concept_hits.items()]) if not concept_hits.empty else "nenhum ainda"
    typo_count = len(typo_candidate_rows(tags_df["tag"].tolist(), threshold=0.80))
    semantic_count = len(semantic_tag_links(tags_df["tag"].tolist(), threshold=0.60))
    work_density = tags_df.groupby("work_title").agg(tags=("id", "count")).reset_index().sort_values("tags", ascending=False)
    work_text = " · ".join([f"{r['work_title']} ({int(r['tags'])})" for _, r in work_density.head(3).iterrows()]) if not work_density.empty else "sem dados"
    ml_text = (f"O modelo está treinado com {ml.entity_samples} amostras e estima acurácia de {ml.entity_accuracy:.2f}. "
               f"As categorias mais frequentes no vocabulário atual são: {entity_text}. "
               f"Conceitos mais acionados via reconciliação: {concept_text}. "
               f"Cada validação aprovada alimenta o corpus e aprimora previsões futuras.")
    val_text = (f"Base atual: {total} marcações, {unique} formas únicas (densidade {density}). "
                f"{validated} já validadas, {pending} aguardando revisão curatorial. "
                f"Obras com mais marcações: {work_text}. "
                f"Ligações semânticas detectadas: {semantic_count}. "
                f"Possíveis variantes ortográficas: {typo_count}.")
    graph_text = (f"A rede integra {len(concepts_df)} conceitos ativos e {len(validations_df)} validações. "
                  f"Cada obra conecta artista, museu, coleção, lugar, período, técnica, material, "
                  f"tags institucionais, tags do público e referências externas (open data). "
                  f"Ligações semânticas entre tags ampliam a rede com {semantic_count} conexões adicionais.")
    return {"ml": ml_text, "validation": val_text, "graph": graph_text}


def build_knowledge_graph(store: JsonStore) -> Any:
    works = store.works()
    concepts = {c.get("id"): c for c in store.concepts() if isinstance(c, dict) and c.get("id")}
    tags_df = build_tag_dataframe(store)
    users = {}
    for idx, user in enumerate(store.users()):
        if not isinstance(user, dict):
            continue
        uid = user.get("id") or user.get("user_id") or f"legacy-{idx}"
        normalized = dict(user)
        normalized["id"] = uid
        users[uid] = normalized
    semantic_links = semantic_tag_links(tags_df["tag"].tolist(), threshold=0.60) if not tags_df.empty else []
    typo_links = typo_candidate_rows(tags_df["tag"].tolist(), threshold=0.80) if not tags_df.empty else []
    node_map: Dict[str, Dict[str, Any]] = {}
    edge_keys = set()
    edges: List[Dict[str, Any]] = []

    def add_node(node_id: str, kind: str, label: str, subtitle: str = "") -> None:
        if node_id and node_id not in node_map:
            node_map[node_id] = {"id": node_id, "kind": kind, "label": label, "subtitle": subtitle}

    def add_edge(source: str, target: str, relation: str) -> None:
        if not source or not target:
            return
        key = tuple(sorted([str(source), str(target)])) + (relation,)
        if key not in edge_keys:
            edge_keys.add(key)
            edges.append({"source": source, "target": target, "relation": relation})

    for work in works:
        meta = resolve_work_metadata(work)
        wid = work.get("id", "")
        add_node(wid, "work", work.get("title", ""), work.get("artist", ""))
        artist_node = f"artist::{normalize_text(work.get('artist', ''))}"
        add_node(artist_node, "artist", work.get("artist", ""), "artista")
        add_edge(wid, artist_node, "created_by")
        for field, kind, relation in [
            (meta.get("museum", ""), "museum", "held_by"),
            (meta.get("collection", ""), "collection", "belongs_to_collection"),
            (meta.get("place", ""), "place", "located_in"),
            (meta.get("period", ""), "period", "historical_period"),
            (meta.get("technique", ""), "technique", "uses_technique"),
            (meta.get("material", ""), "material", "uses_material"),
        ]:
            if field:
                nid = f"{kind}::{normalize_text(field)}"
                add_node(nid, kind, field, "metadado")
                add_edge(wid, nid, relation)
        for tag in work.get("institutional_tags", []) or []:
            nid = f"inst::{normalize_text(tag)}"
            add_node(nid, "institutional_tag", tag, "vocabulário institucional")
            add_edge(wid, nid, "institutional")
        for ext in meta.get("external_entities", []) or []:
            en = f"extentity::{normalize_text(ext)}"
            add_node(en, "external_entity", ext, "open data")
            add_edge(wid, en, "contextualized_by")

    for user in users.values():
        add_node(user["id"], "user", user.get("pseudonym", ""), user.get("profile_familiarity", ""))
    for cid, c in concepts.items():
        add_node(cid, "concept", c.get("label", ""), c.get("category", ""))
    if not tags_df.empty:
        for _, tag in tags_df.iterrows():
            tid = tag.get("id", "")
            add_node(tid, "tag", tag.get("tag", ""), tag.get("entity_prediction", ""))
            if tag.get("work_id"):
                add_edge(tag.get("work_id"), tid, "tagged")
            if tag.get("user_id"):
                add_edge(tag.get("user_id"), tid, "created")
            if tag.get("concept_id") and tag.get("concept_id") in concepts:
                add_edge(tid, tag.get("concept_id"), "reconciled")
            if tag.get("entity_prediction"):
                en = f"entity::{normalize_text(tag.get('entity_prediction', ''))}"
                add_node(en, "entity_class", tag.get("entity_prediction", ""), "categoria")
                add_edge(tid, en, "classified_as")
    for row in semantic_links[:120]:
        a, b = f"surface::{normalize_text(row['tag_a'])}", f"surface::{normalize_text(row['tag_b'])}"
        add_node(a, "tag_surface", row["tag_a"], "forma livre")
        add_node(b, "tag_surface", row["tag_b"], "forma livre")
        add_edge(a, b, row["relation"])
    for row in typo_links[:80]:
        a, b = f"typo::{normalize_text(row['termo_a'])}", f"typo::{normalize_text(row['termo_b'])}"
        add_node(a, "typo_candidate", row["termo_a"], "variante")
        add_node(b, "typo_candidate", row["termo_b"], "variante")
        add_edge(a, b, "possible_spelling_variant")
    return {"nodes": list(node_map.values()), "edges": edges}


def _graph_payload(graph: Any) -> Dict[str, Any]:
    if isinstance(graph, dict):
        return {"nodes": graph.get("nodes", []), "edges": graph.get("edges", [])}
    if HAS_NETWORKX and nx is not None and hasattr(graph, "nodes"):
        nodes = [dict({"id": nid}, **attrs) for nid, attrs in graph.nodes(data=True)]
        edges = [{"source": s, "target": t, **dict(attrs)} for s, t, attrs in graph.edges(data=True)]
        return {"nodes": nodes, "edges": edges}
    return {"nodes": [], "edges": []}


def _edge_count_map(edges: Sequence[Dict[str, Any]]) -> Dict[str, int]:
    counts: Counter = Counter()
    for edge in edges:
        if edge.get("source"):
            counts[str(edge["source"])] += 1
        if edge.get("target"):
            counts[str(edge["target"])] += 1
    return counts


def _manual_3d_layout(nodes: Sequence[Dict[str, Any]], edges: Sequence[Dict[str, Any]]) -> Dict[str, Tuple[float, float, float]]:
    counts = _edge_count_map(edges)
    groups = defaultdict(list)
    for row in nodes:
        groups[str(row.get("kind", "outro"))].append(row)
    kind_order = sorted(groups.keys())
    pos: Dict[str, Tuple[float, float, float]] = {}
    kind_radius = max(2.0, 1.3 + len(kind_order) * 0.22)
    for ki, kind in enumerate(kind_order):
        group = groups[kind]
        base_angle = (2 * math.pi * ki) / max(len(kind_order), 1)
        cx = math.cos(base_angle) * kind_radius
        cy = math.sin(base_angle) * kind_radius
        cz = ((ki % 5) - 2) * 0.75
        local_radius = 0.8 + min(len(group), 24) * 0.03
        for idx, row in enumerate(group):
            nid = str(row.get("id", ""))
            phi = (2 * math.pi * idx) / max(len(group), 1)
            rx = local_radius * math.cos(phi)
            ry = local_radius * math.sin(phi)
            rz = (idx % 3 - 1) * 0.4
            pos[nid] = (cx + rx, cy + ry, cz + rz)
    return pos


def graph_to_plot_3d(payload: Dict[str, Any], max_nodes: int = 220) -> Any:
    if not HAS_PLOTLY or go is None:
        return None
    nodes = payload.get("nodes", [])
    edges = payload.get("edges", [])
    if not nodes:
        return None
    degree = _edge_count_map(edges)
    nodes = sorted(nodes, key=lambda r: degree.get(str(r.get("id", "")), 0), reverse=True)[:max_nodes]
    keep = {str(r.get("id", "")) for r in nodes}
    edges = [e for e in edges if str(e.get("source", "")) in keep and str(e.get("target", "")) in keep]
    pos = _manual_3d_layout(nodes, edges)
    if HAS_NETWORKX and nx is not None:
        g = nx.Graph()
        for row in nodes:
            g.add_node(str(row.get("id", "")), **row)
        for edge in edges:
            g.add_edge(str(edge.get("source", "")), str(edge.get("target", "")))
        try:
            pos = nx.spring_layout(g, dim=3, seed=42, k=max(0.38, 2.2 / math.sqrt(max(len(g.nodes()), 4))), iterations=100)
        except Exception:
            pass

    kind_colors = {
        "work": "#243B53", "tag": "#5C677D", "user": "#9C6644", "concept": "#2F4858",
        "institutional_tag": "#6C757D", "artist": "#3D405B", "museum": "#6D597A",
        "collection": "#588157", "place": "#7F5539", "period": "#4361EE",
        "technique": "#6B705C", "material": "#A68A64", "external_entity": "#7B2CBF",
        "tag_surface": "#495057", "typo_candidate": "#BC6C25", "entity_class": "#1D3557",
    }

    ex, ey, ez = [], [], []
    for edge in edges:
        s, t = str(edge.get("source", "")), str(edge.get("target", ""))
        if s not in pos or t not in pos:
            continue
        x0, y0, z0 = pos[s]
        x1, y1, z1 = pos[t]
        ex.extend([x0, x1, None])
        ey.extend([y0, y1, None])
        ez.extend([z0, z1, None])

    edge_trace = go.Scatter3d(x=ex, y=ey, z=ez, mode="lines",
                               line=dict(color="rgba(70,70,70,0.28)", width=2),
                               hoverinfo="none", name="ligações")

    xs, ys, zs, colors, sizes, texts = [], [], [], [], [], []
    for row in nodes:
        nid = str(row.get("id", ""))
        if nid not in pos:
            continue
        x, y, z = pos[nid]
        xs.append(x); ys.append(y); zs.append(z)
        kind = str(row.get("kind", "outro"))
        colors.append(kind_colors.get(kind, "#444444"))
        deg = degree.get(nid, 1)
        sizes.append(min(24, 6 + deg * 0.65))
        texts.append(f"{row.get('label', nid)}<br>{kind}<br>{row.get('subtitle', '')}<br>grau {deg}")

    node_trace = go.Scatter3d(x=xs, y=ys, z=zs, mode="markers", text=texts,
                               hovertemplate="%{text}<extra></extra>",
                               marker=dict(size=sizes, color=colors, opacity=0.92,
                                           line=dict(color="rgba(255,255,255,0.85)", width=1.4)), name="nós")

    label_rows = sorted([(degree.get(str(r.get("id", "")), 0), r) for r in nodes], reverse=True)[:28]
    lx, ly, lz, lt = [], [], [], []
    for _, row in label_rows:
        nid = str(row.get("id", ""))
        if nid in pos:
            x, y, z = pos[nid]
            lx.append(x); ly.append(y); lz.append(z)
            lt.append(str(row.get("label", ""))[:32])

    text_trace = go.Scatter3d(x=lx, y=ly, z=lz, mode="text", text=lt,
                               textfont=dict(size=11, color="#1f1f1f"), hoverinfo="none", showlegend=False)

    fig = go.Figure(data=[edge_trace, node_trace, text_trace])
    fig.update_layout(
        height=720, margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        scene=dict(
            xaxis=dict(visible=False, showbackground=False),
            yaxis=dict(visible=False, showbackground=False),
            zaxis=dict(visible=False, showbackground=False),
            bgcolor="rgba(0,0,0,0)",
            camera=dict(eye=dict(x=1.7, y=1.7, z=1.18))
        ),
        legend=dict(orientation="h", yanchor="bottom", y=0.01, xanchor="left", x=0.01,
                    bgcolor="rgba(255,255,255,0.22)")
    )
    return fig


def generate_semantic_report(store: JsonStore, ml: SemanticLearner) -> Dict[str, Any]:
    tags_df = build_tag_dataframe(store)
    if tags_df.empty:
        return {}
    top_tags = tags_df["normalized_tag"].value_counts().head(15).to_dict()
    grouped = tags_df["entity_prediction"].replace("", "não previsto").fillna("não previsto").value_counts().to_dict()
    clusters = ml.cluster_terms(tags_df["tag"].dropna().astype(str).tolist(), threshold=0.66)
    report = {
        "id": make_id("report"), "created_at": now_iso(), "top_tags": top_tags,
        "entity_distribution": grouped, "cluster_count": len(clusters),
        "clusters_preview": clusters[:12], "total_tags": int(len(tags_df)),
        "unique_tags": int(tags_df["normalized_tag"].nunique()),
    }
    reports = store.reports()
    reports.append(report)
    store.save_reports(reports)
    return report


def run_automation_engine(store: JsonStore, ml: SemanticLearner) -> List[Dict[str, Any]]:
    settings = store.automations()
    if not settings.get("enabled", True):
        return []
    tags = store.tags()
    suggestions = store.suggestions()
    existing_keys = {(s.get("tag_id"), s.get("rule_name"), s.get("suggestion_type")) for s in suggestions if s.get("status") == "open"}
    concept_by_id = {c.get("id"): c for c in store.concepts()}
    concept_freq = Counter([normalize_text(c.get("label", "")) for c in store.concepts()])
    created = []
    for tag in tags:
        tag_id = tag.get("id")
        text = tag.get("tag", "")
        prediction = ml.predict_entity(text)
        if settings.get("auto_classify") and prediction.get("confidence", 0.0) >= settings.get("min_confidence_auto_classify", 0.84):
            key = (tag_id, "auto_classify", "entity")
            if key not in existing_keys and tag.get("entity_prediction") != prediction.get("label"):
                created.append(store.add_suggestion(tag_id, "auto_classify", "entity",
                                                     {"entity": prediction.get("label"), "confidence": round(prediction.get("confidence", 0.0), 4)}))
                existing_keys.add(key)
        concept = ml.suggest_concept(text)
        if concept and concept.get("similarity", 0.0) >= settings.get("min_similarity_auto_link", 0.88):
            key = (tag_id, "auto_link_concept", "concept")
            if key not in existing_keys and tag.get("concept_id") != concept.get("id"):
                created.append(store.add_suggestion(tag_id, "auto_link_concept", "concept",
                                                     {"concept_id": concept.get("id"), "concept_label": concept.get("label"),
                                                      "category": concept.get("category"), "similarity": round(concept.get("similarity", 0.0), 4)}))
                existing_keys.add(key)
    if settings.get("auto_create_candidate_concepts"):
        freq = Counter([normalize_text(t.get("tag", "")) for t in tags])
        for text, count in freq.items():
            if not text or count < settings.get("min_frequency_candidate_concept", 3):
                continue
            if concept_freq.get(text):
                continue
            base_tag = next((t for t in tags if normalize_text(t.get("tag", "")) == text), None)
            if not base_tag:
                continue
            key = (base_tag.get("id"), "candidate_concept", "concept_candidate")
            if key in existing_keys:
                continue
            prediction = ml.predict_entity(text)
            created.append(store.add_suggestion(base_tag.get("id"), "candidate_concept", "concept_candidate",
                                                  {"label": text, "category": prediction.get("label", "tema"), "frequency": int(count)}))
            existing_keys.add(key)
    if settings.get("auto_generate_reports", True):
        reports = store.reports()
        should_make = True
        if reports:
            try:
                last = datetime.strptime(reports[-1]["created_at"], "%Y-%m-%d %H:%M:%S")
                should_make = datetime.now() - last > timedelta(hours=12)
            except Exception:
                should_make = True
        if should_make and len(tags) >= 3:
            generate_semantic_report(store, ml)
    return created


def render_css() -> None:
    st.markdown(CSS_BLOCK, unsafe_allow_html=True)


def init_session() -> None:
    defaults = {
        "admin_authenticated": False,
        "session_user_id": st.session_state.get("session_user_id", ""),
        "intro_complete": st.session_state.get("intro_complete", False),
        "selected_work_id": st.session_state.get("selected_work_id", ""),
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def topbar(store: JsonStore) -> None:
    st.markdown("<div class='topbar'><div><div class='brand-title'>folksonomia</div></div></div>", unsafe_allow_html=True)


def hero_panel(store: JsonStore) -> None:
    st.markdown("<div class='hero-panel'><div class='hero-title'>folksonomia</div></div>", unsafe_allow_html=True)


def open_panel(title: str, subtitle: str = "") -> None:
    sub = f"<div class='panel-subtitle'>{subtitle}</div>" if subtitle else ""
    st.markdown(f"<div class='panel'><div class='panel-title'>{title}</div>{sub}", unsafe_allow_html=True)


def close_panel() -> None:
    st.markdown("</div>", unsafe_allow_html=True)


def intro_flow(store: JsonStore) -> None:
    open_panel("bem-vindo", "responda às perguntas abaixo para acessar as obras.")
    with st.form("intro_form"):
        c1, c2 = st.columns(2)
        with c1:
            familiarity = st.selectbox("Com que frequência você visita museus?", ["nunca", "raramente", "às vezes", "frequentemente"])
            documentation = st.selectbox("Você conhece o conceito de documentação museológica?", ["não conheço", "conheço um pouco", "conheço bem", "trabalho com isso"])
        with c2:
            understanding = st.text_area("O que são tags para você? Como você as usaria para descrever uma obra de arte?",
                                          height=190, placeholder="Escreva com suas palavras, sem preocupação com acertar...")
        submitted = st.form_submit_button("Acessar as obras →")
        if submitted:
            if not understanding.strip():
                st.warning("Por favor, preencha o campo sobre tags para continuar.")
            else:
                store.create_or_get_user(familiarity, documentation, understanding)
                st.session_state["intro_complete"] = True
                st.rerun()
    close_panel()


def render_public_explore(store: JsonStore, ml: SemanticLearner) -> None:
    """Public gallery: click image → compact inline tag input (no image repeat)."""
    user = store.find_user(st.session_state.get("session_user_id", ""))
    works = store.works()[:3]
    open_panel("obras", "Clique em uma imagem para adicionar sua tag.")
    if not user or not works:
        close_panel()
        return

    selected_id = st.session_state.get("selected_work_id", "")
    cols = st.columns(len(works))
    for idx, work in enumerate(works):
        with cols[idx]:
            is_selected = (work.get("id") == selected_id)
            border_style = "border: 2px solid rgba(30,30,30,0.40);" if is_selected else ""
            st.markdown(f"<div class='work-card' style='{border_style}'>", unsafe_allow_html=True)
            st.image(work.get("image_url"), use_container_width=True)
            btn_label = "✕ fechar" if is_selected else "＋ adicionar tag"
            if st.button(btn_label, key=f"sel-{work.get('id')}", use_container_width=True):
                st.session_state["selected_work_id"] = "" if is_selected else work.get("id")
                st.rerun()
            wt = work.get("title", "")
            wa = work.get("artist", "")
            wy = work.get("year", "")
            st.markdown(f"<div style='margin-top:0.5rem;font-size:0.82rem;color:#555;text-align:center'>{wt} · {wa} · {wy}</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

    # Compact inline tag input — no image repeat
    if selected_id:
        selected = next((w for w in works if w.get("id") == selected_id), None)
        if selected:
            tags_df = build_tag_dataframe(store)
            mine = tags_df[(tags_df["work_id"] == selected_id) & (tags_df["user_id"] == user.get("id"))] if not tags_df.empty else pd.DataFrame()
            all_work_tags = tags_df[tags_df["work_id"] == selected_id] if not tags_df.empty else pd.DataFrame()

            st.markdown(f"""
            <div class='tag-inline-panel'>
                <div class='tag-inline-title'>→ {selected.get('title')}</div>
                <div class='tag-inline-sub'>Digite uma palavra ou expressão que descreva o que você vê nesta imagem.</div>
            </div>
            """, unsafe_allow_html=True)

            with st.form(f"tag-form-inline-{selected_id}", clear_on_submit=True):
                tag_value = st.text_input("Sua tag", placeholder="ex: tristeza, azul, mulher trabalhando, campo aberto…", label_visibility="collapsed")
                submitted = st.form_submit_button("Registrar →", use_container_width=True)
                if submitted:
                    if not tag_value.strip():
                        st.warning("Escreva uma tag antes de registrar.")
                    else:
                        store.submit_tag(selected.get("id"), user.get("id"), tag_value, "", ml)
                        run_automation_engine(store, ml)
                        st.success(f"Tag \"{tag_value.strip()}\" registrada.")
                        st.rerun()

            if not mine.empty:
                mine_counts = mine["tag"].value_counts().reset_index()
                mine_counts.columns = ["tag", "n"]
                st.markdown("<div style='margin-top:0.5rem;font-size:0.8rem;color:#666'>Suas tags nesta obra:</div>", unsafe_allow_html=True)
                chips = "".join([f"<span class='tag-chip'>{r['tag']}</span>" for _, r in mine_counts.iterrows()])
                st.markdown(f"<div class='tag-preview-wrap'>{chips}</div>", unsafe_allow_html=True)

            if not all_work_tags.empty and len(all_work_tags) >= 3:
                top = all_work_tags["tag"].value_counts().head(8)
                st.markdown("<div style='margin-top:0.5rem;font-size:0.8rem;color:#666'>Tags mais usadas por todos:</div>", unsafe_allow_html=True)
                chips2 = "".join([f"<span class='tag-chip'>{t} <small style='opacity:.6'>×{c}</small></span>" for t, c in top.items()])
                st.markdown(f"<div class='tag-preview-wrap'>{chips2}</div>", unsafe_allow_html=True)
    close_panel()


def render_public_semantics(store: JsonStore, ml: SemanticLearner) -> None:
    tags_df = build_tag_dataframe(store)
    open_panel("explorar conceitos", "Busque um termo e veja como o sistema o interpreta semanticamente.")
    query = st.text_input("Termo de busca", placeholder="ex: mulher, barroco, ouro, trabalho, rio de janeiro…")
    if query.strip():
        features = ml.term_features(query)
        st.markdown(f"""
        <div class='summary-block'>
            <strong>Interpretação:</strong> O sistema classifica <em>{query}</em> como 
            <strong>{features.get('entity')}</strong> com confiança de {features.get('confidence', 0.0):.0%}.
        </div>
        """, unsafe_allow_html=True)
        for concept in features.get("concepts", []):
            st.markdown(f"<span class='tag-chip'>{concept.get('label')} · {concept.get('category')} · {concept.get('similarity', 0.0):.0%}</span>", unsafe_allow_html=True)
        if not tags_df.empty:
            related = ml.related_tags(tags_df["tag"].astype(str).tolist(), query, top_k=12)
            if related:
                st.markdown("<div style='margin-top:1rem;font-size:0.85rem;color:#555'>Termos próximos no vocabulário do público:</div>", unsafe_allow_html=True)
                for term, score in related:
                    if score > 0.3:
                        st.markdown(f"<span class='tag-chip'>{term} · {score:.0%}</span>", unsafe_allow_html=True)
    else:
        st.caption("Use um termo para ativar a camada de interpretação semântica.")
    close_panel()


def render_public_history(store: JsonStore) -> None:
    user = store.find_user(st.session_state.get("session_user_id", ""))
    open_panel("meu histórico", "Suas contribuições nesta sessão.")
    if not user:
        st.info("Nenhum perfil ativo nesta sessão.")
        close_panel()
        return
    tags_df = build_tag_dataframe(store)
    mine = tags_df[tags_df["user_id"] == user.get("id")] if not tags_df.empty else pd.DataFrame()
    if mine.empty:
        st.info("Você ainda não registrou nenhuma tag. Acesse a aba Obras para começar.")
        close_panel()
        return
    total = int(len(mine))
    unique = int(mine["normalized_tag"].nunique())
    ttr = unique / total if total else 0.0
    st.markdown(f"""
    <div class="metric-strip">
        <div class="metric-card"><div class="metric-caption">Nome da sessão</div><div class="metric-number" style="font-size:1.2rem">{user.get('pseudonym')}</div></div>
        <div class="metric-card"><div class="metric-caption">Tags enviadas</div><div class="metric-number">{total}</div></div>
        <div class="metric-card"><div class="metric-caption">Palavras únicas</div><div class="metric-number">{unique}</div></div>
        <div class="metric-card"><div class="metric-caption">Variedade</div><div class="metric-number">{ttr:.2f}</div><div class="metric-note">Diversidade lexical (0–1)</div></div>
    </div>
    """, unsafe_allow_html=True)
    top = mine["tag"].value_counts().head(20).rename_axis("tag").reset_index(name="frequência")
    render_bar_chart_df(top, x="frequência", y="tag", orientation="h", height=400)
    close_panel()


def render_admin_login(store: JsonStore) -> None:
    open_panel("área administrativa", "Acesso restrito à equipe curatorial.")
    with st.form("admin-login"):
        username = st.text_input("Login")
        password = st.text_input("Senha", type="password")
        submitted = st.form_submit_button("Entrar →", use_container_width=True)
        if submitted:
            if store.admin_ok(username, password):
                st.session_state["admin_authenticated"] = True
                st.success("Acesso liberado.")
                st.rerun()
            else:
                st.error("Credenciais inválidas.")
    close_panel()


def render_admin_dashboard(store: JsonStore, ml: SemanticLearner) -> None:
    tags_df = build_tag_dataframe(store)
    users_df = to_dataframe(store.users())
    concepts_df = to_dataframe(store.concepts())
    works_df = to_dataframe(store.works())
    open_panel("painel geral")
    total_tags = int(len(tags_df)) if not tags_df.empty else 0
    unique_tags = int(tags_df["normalized_tag"].nunique()) if not tags_df.empty else 0
    st.markdown(f"""
    <div class="metric-strip">
        <div class="metric-card"><div class="metric-caption">Participantes</div><div class="metric-number">{int(users_df['id'].nunique()) if not users_df.empty else 0}</div></div>
        <div class="metric-card"><div class="metric-caption">Obras</div><div class="metric-number">{int(len(works_df)) if not works_df.empty else 0}</div></div>
        <div class="metric-card"><div class="metric-caption">Vocabulário único</div><div class="metric-number">{unique_tags}</div></div>
        <div class="metric-card"><div class="metric-caption">Amostras de treino</div><div class="metric-number">{ml.entity_samples}</div></div>
    </div>
    """, unsafe_allow_html=True)
    c1, c2 = st.columns([1.08, 0.92])
    with c1:
        if not tags_df.empty:
            entity_counts = tags_df["entity_prediction"].replace("", "não classificado").fillna("não classificado").value_counts().rename_axis("categoria").reset_index(name="frequência")
            render_bar_chart_df(entity_counts, x="categoria", y="frequência", height=360)
        else:
            st.info("Ainda não há tags para analisar.")
    with c2:
        validations_df = to_dataframe(store.validations())
        open_suggs = [s for s in store.suggestions() if s.get("status") == "open"]
        st.markdown(f"""
        <div class='story-card'>
            <div class='story-title'>Resumo curatorial</div>
            <div class='story-copy'>
                Conceitos ativos: {len(concepts_df)}<br>
                Validações registradas: {len(validations_df)}<br>
                Sugestões pendentes: {len(open_suggs)}<br>
                Acurácia estimada do modelo: {ml.entity_accuracy:.2f}
            </div>
        </div>
        """, unsafe_allow_html=True)
        if not works_df.empty:
            filled = {col: int(works_df[col].fillna("").astype(str).str.strip().ne("").sum())
                      for col in ["museum", "collection", "place", "period", "technique", "material"]
                      if col in works_df.columns}
            meta_df = pd.DataFrame({"campo": list(filled.keys()), "preenchido": list(filled.values())})
            render_bar_chart_df(meta_df, x="campo", y="preenchido", height=280)
    if not tags_df.empty:
        st.markdown("<div class='soft-line'></div>", unsafe_allow_html=True)
        c3, c4 = st.columns(2)
        with c3:
            top_tags = tags_df["tag"].value_counts().head(12).rename_axis("tag").reset_index(name="frequência")
            render_bar_chart_df(top_tags, x="tag", y="frequência", height=320)
        with c4:
            typo_rows = pd.DataFrame(typo_candidate_rows(tags_df["tag"].tolist(), threshold=0.80))
            if not typo_rows.empty:
                st.markdown("<div class='story-card'><div class='story-title'>Possíveis variações ortográficas</div><div class='story-copy'>Pares para revisão curatorial.</div></div>", unsafe_allow_html=True)
                st.dataframe(typo_rows.head(12), use_container_width=True, hide_index=True)
            else:
                st.info("Nenhuma variação ortográfica detectada ainda.")
    close_panel()


def render_admin_validation(store: JsonStore, ml: SemanticLearner) -> None:
    tags_df = build_tag_dataframe(store)
    suggestions_df = to_dataframe(store.suggestions())
    concepts = store.concepts()
    concept_options = {f"{c.get('label')} · {c.get('category')}": c for c in concepts}
    open_panel("validação e curadoria")
    if tags_df.empty:
        st.info("Nenhuma tag registrada ainda.")
        close_panel()
        return
    summaries = _analysis_summary_blocks(store, ml)
    st.markdown(f"<div class='summary-block'><strong>Situação atual.</strong> {summaries['validation']}</div>", unsafe_allow_html=True)

    semantic_rows = pd.DataFrame(semantic_tag_links(tags_df["tag"].tolist(), threshold=0.60))
    typo_rows = pd.DataFrame(typo_candidate_rows(tags_df["tag"].tolist(), threshold=0.80))
    work_time = tags_df.groupby(["work_title", "created_month"]).agg(tags=("id", "count"), vocabulário=("normalized_tag", "nunique")).reset_index() if not tags_df.empty else pd.DataFrame()

    tabs = st.tabs(["Fila de validação", "Ligações semânticas", "Variações ortográficas", "Obras"])
    with tabs[0]:
        subset = tags_df.sort_values("created_at", ascending=False).head(20)
        open_suggestions = suggestions_df[suggestions_df["status"] == "open"] if not suggestions_df.empty else pd.DataFrame()
        for _, row in subset.iterrows():
            related_suggestions = open_suggestions[open_suggestions["tag_id"] == row.get("id")] if not open_suggestions.empty else pd.DataFrame()
            st.markdown(f"""
            <div class='queue-card'>
                <div class='story-title'>{row.get('tag')} — {row.get('work_title', 'obra desconhecida')}</div>
                <div class='queue-text'>
                    Categoria prevista: <strong>{row.get('entity_prediction', '—')}</strong> 
                    (confiança {safe_float(row.get('entity_confidence', 0.0)):.0%})<br>
                    Conceito vinculado: {row.get('concept_label', '') or '—'} · 
                    Museu: {row.get('work_museum', '') or '—'} · 
                    Período: {row.get('work_period', '') or '—'}
                </div>
            </div>
            """, unsafe_allow_html=True)
            if not related_suggestions.empty:
                for _, srow in related_suggestions.iterrows():
                    payload_str = json.dumps(srow.get('payload', {}), ensure_ascii=False)
                    st.markdown(f"<div class='suggestion-card'><div class='story-title'>Sugestão automática: {srow.get('rule_name')}</div><div class='suggestion-meta'>{payload_str}</div></div>", unsafe_allow_html=True)
            with st.form(f"validate-{row.get('id')}"):
                c1, c2 = st.columns(2)
                with c1:
                    default_entity = row.get("entity_prediction") if row.get("entity_prediction") in ENTITY_LABELS else "tema"
                    entity_choice = st.selectbox("Categoria correta", ENTITY_LABELS, index=ENTITY_LABELS.index(default_entity), key=f"ent-{row.get('id')}")
                    concept_choice = st.selectbox("Conceito reconciliado", ["nenhum"] + list(concept_options.keys()), key=f"con-{row.get('id')}")
                with c2:
                    decision = st.selectbox("Decisão", ["approved", "linked", "rejected"], key=f"dec-{row.get('id')}")
                    notes = st.text_area("Notas curatoriais", height=90, key=f"notes-{row.get('id')}")
                if st.form_submit_button("Salvar validação"):
                    cid, clabel = "", ""
                    if concept_choice != "nenhum":
                        cp = concept_options[concept_choice]
                        cid, clabel = cp.get("id", ""), cp.get("label", "")
                    store.add_validation(row.get("id"), "admin", entity_choice, cid, clabel, decision, notes)
                    updates = {"status": "validated" if decision != "rejected" else "rejected", "entity_prediction": entity_choice, "entity_confidence": 1.0}
                    if cid:
                        updates["concept_id"] = cid
                        updates["concept_label"] = clabel
                    store.update_tag(row.get("id"), updates)
                    if not related_suggestions.empty:
                        for _, srow in related_suggestions.iterrows():
                            store.close_suggestion(srow.get("id"), status="resolved")
                    ml.train()
                    st.success("Validação salva e modelo atualizado.")
                    st.rerun()
    with tabs[1]:
        st.markdown("<div class='summary-block'>Tags do público que compartilham campo semântico ou ortografia próxima — úteis para reconciliação e normalização do vocabulário.</div>", unsafe_allow_html=True)
        if semantic_rows.empty:
            st.info("Ainda não há ligações semânticas suficientes.")
        else:
            render_bar_chart_df(semantic_rows.head(18), x="tag_a", y="score", height=360)
            st.dataframe(semantic_rows.head(30), use_container_width=True, hide_index=True)
    with tabs[2]:
        st.markdown("<div class='summary-block'>Pares de termos com alta similaridade formal — candidatos a unificação ou desambiguação no vocabulário controlado.</div>", unsafe_allow_html=True)
        if typo_rows.empty:
            st.info("Nenhuma variação ortográfica forte encontrada.")
        else:
            st.dataframe(typo_rows.head(30), use_container_width=True, hide_index=True)
    with tabs[3]:
        work_summary = tags_df.groupby("work_title").agg(tags=("id", "count"), vocabulário=("normalized_tag", "nunique")).reset_index().sort_values("tags", ascending=False)
        if not work_summary.empty:
            render_bar_chart_df(work_summary.head(12), x="work_title", y="tags", height=340)
            if not work_time.empty and HAS_PLOTLY:
                fig = px.line(work_time.sort_values("created_month"), x="created_month", y="tags", color="work_title", markers=True)
                fig.update_layout(height=340, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=10, r=10, t=20, b=10))
                safe_plotly_chart(fig, use_container_width=True)
            st.dataframe(work_summary, use_container_width=True, hide_index=True)
        else:
            st.info("Sem dados suficientes por obra.")
    close_panel()


def render_admin_concepts(store: JsonStore, ml: SemanticLearner) -> None:
    concepts_df = to_dataframe(store.concepts())
    open_panel("conceitos e ontologia")
    t1, t2 = st.tabs(["Listar conceitos", "Criar conceito"])
    with t1:
        if concepts_df.empty:
            st.info("Sem conceitos cadastrados.")
        else:
            search = st.text_input("Buscar conceito", key="concept-search")
            view = concepts_df.copy()
            if search.strip():
                mask = view["label"].astype(str).str.contains(search, case=False, na=False) | view["category"].astype(str).str.contains(search, case=False, na=False)
                view = view[mask]
            st.dataframe(view[[c for c in ["label", "category", "aliases", "status", "source"] if c in view.columns]], use_container_width=True, hide_index=True)
    with t2:
        with st.form("create-concept"):
            c1, c2 = st.columns(2)
            with c1:
                label = st.text_input("Rótulo do conceito")
                category = st.selectbox("Categoria", ENTITY_LABELS)
            with c2:
                aliases = st.text_input("Sinônimos (separados por vírgula)")
                source = st.selectbox("Origem", ["manual", "candidate", "imported"])
            if st.form_submit_button("Criar conceito"):
                if not label.strip():
                    st.warning("Escreva um rótulo.")
                else:
                    store.add_concept(label, category, [p.strip() for p in aliases.split(",") if p.strip()], source)
                    ml.train()
                    st.success("Conceito criado.")
                    st.rerun()
    close_panel()


def render_admin_ml(store: JsonStore, ml: SemanticLearner) -> None:
    model_info = store.model_state()
    tags_df = build_tag_dataframe(store)
    summaries = _analysis_summary_blocks(store, ml)
    open_panel("machine learning")
    st.markdown(f"""
    <div class="metric-strip">
        <div class="metric-card"><div class="metric-caption">Último treino</div><div class="metric-number" style="font-size:1rem">{model_info.get('last_trained_at') or '—'}</div></div>
        <div class="metric-card"><div class="metric-caption">Amostras</div><div class="metric-number">{model_info.get('sample_count', 0)}</div></div>
        <div class="metric-card"><div class="metric-caption">Acurácia</div><div class="metric-number">{model_info.get('accuracy', 0.0):.2f}</div></div>
        <div class="metric-card"><div class="metric-caption">Categorias</div><div class="metric-number">{len(ml.entity_labels)}</div></div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown(f"<div class='summary-block'><strong>Estado do modelo.</strong> {summaries['ml']}</div>", unsafe_allow_html=True)
    c1, c2 = st.columns([1.05, 0.95])
    with c1:
        query = st.text_input("Testar uma palavra", placeholder="ex: soldado, aquarela, barroco…")
        if query.strip():
            pred = ml.predict_entity(query)
            st.markdown(f"<div class='suggestion-card'><div class='story-title'>Previsão para &ldquo;{query}&rdquo;</div><div class='suggestion-meta'>Categoria: <strong>{pred.get('label')}</strong> · Confiança: {pred.get('confidence', 0.0):.0%}</div></div>", unsafe_allow_html=True)
            concepts = ml.suggest_concepts(query, 5)
            if concepts:
                chips = "".join([f"<span class='tag-chip'>{c.get('label')} · {c.get('category')} · {c.get('similarity', 0.0):.0%}</span>" for c in concepts])
                st.markdown(f"<div class='tag-preview-wrap'>{chips}</div>", unsafe_allow_html=True)
        if not tags_df.empty:
            predicted = tags_df["entity_prediction"].replace("", "não classificado").value_counts().rename_axis("categoria").reset_index(name="frequência")
            render_bar_chart_df(predicted, x="categoria", y="frequência", height=340)
    with c2:
        if st.button("Re-treinar modelo agora", use_container_width=True):
            ml.train()
            st.success("Modelo atualizado.")
            st.rerun()
        st.markdown("""
        <div class='story-card'>
            <div class='story-title'>Como funciona</div>
            <div class='story-copy'>
                O modelo aprende com o vocabulário inicial de referência, com os metadados das obras 
                (técnica, período, lugar) e com cada validação aprovada pela curadoria. 
                Quanto mais validações, mais preciso fica.
            </div>
        </div>
        """, unsafe_allow_html=True)
        if not tags_df.empty and "entity_confidence" in tags_df.columns:
            conf = tags_df["entity_confidence"].fillna(0).astype(float)
            conf_df = pd.DataFrame({
                "faixa": ["baixa (0–39%)", "média (40–69%)", "alta (70–100%)"],
                "quantidade": [int((conf < 0.40).sum()), int(((conf >= 0.40) & (conf < 0.70)).sum()), int((conf >= 0.70).sum())]
            })
            render_bar_chart_df(conf_df, x="faixa", y="quantidade", height=260)
    close_panel()


def render_admin_automation(store: JsonStore, ml: SemanticLearner) -> None:
    tags_df = build_tag_dataframe(store)
    open_panel("análise temporal")
    if tags_df.empty:
        st.info("A análise temporal será exibida assim que houver marcações registradas.")
        close_panel()
        return

    tags_df["created_ts"] = pd.to_datetime(tags_df["created_at"], errors="coerce")
    tags_df = tags_df.sort_values("created_ts")
    daily = tags_df.groupby("created_date").agg(tags=("id", "count"), vocabulário=("normalized_tag", "nunique"), participantes=("user_id", "nunique")).reset_index()
    monthly = tags_df.groupby("created_month").agg(tags=("id", "count"), vocabulário=("normalized_tag", "nunique")).reset_index()
    hourly = tags_df.groupby("created_hour").agg(tags=("id", "count")).reset_index()
    weekday_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    weekday_pt = {"Monday": "Seg", "Tuesday": "Ter", "Wednesday": "Qua", "Thursday": "Qui", "Friday": "Sex", "Saturday": "Sáb", "Sunday": "Dom"}
    weekday = tags_df.groupby("created_weekday").agg(tags=("id", "count")).reset_index()
    if not weekday.empty:
        weekday["sort"] = weekday["created_weekday"].map(lambda v: weekday_order.index(v) if v in weekday_order else 99)
        weekday = weekday.sort_values("sort")
        weekday["dia"] = weekday["created_weekday"].map(lambda v: weekday_pt.get(v, v))

    lexical_curve = []
    seen = set()
    for _, row in tags_df.iterrows():
        seen.add(row.get("normalized_tag", ""))
        lexical_curve.append({"data": row.get("created_at", ""), "vocabulário acumulado": len(seen)})
    lexical_df = pd.DataFrame(lexical_curve)

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(f"<div class='metric-card'><div class='metric-caption'>Dias ativos</div><div class='metric-number'>{daily['created_date'].nunique()}</div></div>", unsafe_allow_html=True)
    with c2: st.markdown(f"<div class='metric-card'><div class='metric-caption'>Pico diário</div><div class='metric-number'>{int(daily['tags'].max())}</div><div class='metric-note'>tags no dia mais intenso</div></div>", unsafe_allow_html=True)
    with c3: st.markdown(f"<div class='metric-card'><div class='metric-caption'>Média diária</div><div class='metric-number'>{daily['tags'].mean():.1f}</div></div>", unsafe_allow_html=True)
    with c4: st.markdown(f"<div class='metric-card'><div class='metric-caption'>Vocabulário total</div><div class='metric-number'>{int(tags_df['normalized_tag'].nunique())}</div></div>", unsafe_allow_html=True)

    tabs = st.tabs(["Ritmo diário", "Sazonalidade", "Crescimento lexical"])
    with tabs[0]:
        if HAS_PLOTLY:
            fig = go.Figure()
            fig.add_scatter(x=daily["created_date"], y=daily["tags"], mode="lines+markers", name="Tags")
            fig.add_scatter(x=daily["created_date"], y=daily["participantes"], mode="lines+markers", name="Participantes")
            fig.update_layout(height=380, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=10, r=10, t=20, b=10))
            safe_plotly_chart(fig, use_container_width=True)
        else:
            st.line_chart(daily.set_index("created_date")[["tags", "participantes"]])
    with tabs[1]:
        c1, c2 = st.columns(2)
        with c1:
            render_bar_chart_df(hourly, x="created_hour", y="tags", height=300)
        with c2:
            if not weekday.empty:
                render_bar_chart_df(weekday[["dia", "tags"]], x="dia", y="tags", height=300)
        if not monthly.empty:
            render_bar_chart_df(monthly, x="created_month", y="tags", height=300)
    with tabs[2]:
        if not lexical_df.empty:
            if HAS_PLOTLY:
                fig = px.line(lexical_df, x="data", y="vocabulário acumulado", markers=True)
                fig.update_layout(height=380, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=10, r=10, t=20, b=10))
                safe_plotly_chart(fig, use_container_width=True)
            else:
                st.line_chart(lexical_df.set_index("data")["vocabulário acumulado"])
            st.markdown("<div class='summary-block'>Quando a curva cresce rapidamente, o público está trazendo termos novos. Quando estabiliza, o vocabulário converge para eixos já conhecidos — sinal de que reconciliação e validação devem ser priorizadas.</div>", unsafe_allow_html=True)
    close_panel()


def render_admin_graph(store: JsonStore) -> None:
    open_panel("teia de conhecimento 3D")
    graph = build_knowledge_graph(store)
    payload = _graph_payload(graph)
    summaries = _analysis_summary_blocks(store, SemanticLearner(store))
    node_df = pd.DataFrame(payload.get("nodes", []))
    edge_df = pd.DataFrame(payload.get("edges", []))
    node_count = len(node_df)
    edge_count = len(edge_df)

    if HAS_PLOTLY:
        fig = graph_to_plot_3d(payload, max_nodes=240)
        if fig is not None:
            safe_plotly_chart(fig, use_container_width=True)
        else:
            st.info("Dados insuficientes para renderizar a rede.")
    else:
        # Fallback: show distributions without the "install plotly" message
        if not node_df.empty and "kind" in node_df.columns:
            kinds = node_df["kind"].value_counts().rename_axis("tipo").reset_index(name="nós")
            render_bar_chart_df(kinds, x="tipo", y="nós", height=320)
        if not edge_df.empty and "relation" in edge_df.columns:
            rels = edge_df["relation"].value_counts().rename_axis("relação").reset_index(name="arestas")
            render_bar_chart_df(rels.head(15), x="relação", y="arestas", height=280)

    st.markdown(f"<div class='summary-block'><strong>Rede conectada.</strong> {summaries['graph']} Nós: {node_count} · Arestas: {edge_count}.</div>", unsafe_allow_html=True)

    tabs = st.tabs(["Relações", "Metadados e open data", "Nós mais conectados"])
    with tabs[0]:
        if not edge_df.empty and "relation" in edge_df.columns:
            rels = edge_df["relation"].value_counts().rename_axis("relação").reset_index(name="quantidade")
            render_bar_chart_df(rels.head(18), x="relação", y="quantidade", height=320)
            st.dataframe(rels.head(20), use_container_width=True, hide_index=True)
        else:
            st.info("Sem relações suficientes.")
    with tabs[1]:
        works_df = to_dataframe(store.works())
        if not works_df.empty:
            cols = [c for c in ["title", "artist", "museum", "collection", "place", "period", "technique", "material", "external_reference_label"] if c in works_df.columns]
            st.dataframe(works_df[cols], use_container_width=True, hide_index=True)
        else:
            st.info("Sem obras cadastradas.")
    with tabs[2]:
        counts = _edge_count_map(payload.get("edges", []))
        connected_rows = [{"rótulo": r.get("label", ""), "tipo": r.get("kind", ""), "grau": counts.get(str(r.get("id", "")), 0)} for r in payload.get("nodes", [])]
        connected_df = pd.DataFrame(connected_rows).sort_values("grau", ascending=False)
        if not connected_df.empty:
            render_bar_chart_df(connected_df.head(16), x="rótulo", y="grau", height=320)
            st.dataframe(connected_df.head(24), use_container_width=True, hide_index=True)
        else:
            st.info("Sem dados suficientes.")
    close_panel()


def render_admin_data(store: JsonStore, ml: SemanticLearner) -> None:
    def build_pdf_bytes() -> bytes:
        from io import BytesIO
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        from reportlab.lib.utils import simpleSplit

        tags_df = build_tag_dataframe(store)
        works_df = to_dataframe(store.works())
        concepts_df = to_dataframe(store.concepts())
        validations_df = to_dataframe(store.validations())
        metrics = build_public_metrics(tags_df, works_df, to_dataframe(store.users()))

        buffer = BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        margin = 42
        y = height - 44

        def line(text_value: str = "", font_name: str = "Times-Roman", font_size: int = 11, gap: int = 16) -> None:
            nonlocal y
            chunks = simpleSplit(str(text_value), font_name, font_size, width - margin * 2)
            pdf.setFont(font_name, font_size)
            for chunk in chunks:
                if y < 58:
                    pdf.showPage()
                    y = height - 44
                    pdf.setFont(font_name, font_size)
                pdf.drawString(margin, y, chunk)
                y -= gap

        def spacer(n: int = 10) -> None:
            nonlocal y
            y -= n
            if y < 58:
                pdf.showPage()
                y = height - 44

        pdf.setTitle("Relatório Folksonomia")
        line("folksonomia — relatório administrativo", "Times-Bold", 20, 22)
        line(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", "Times-Roman", 11, 18)
        spacer(6)
        line("1. Métricas gerais", "Times-Bold", 16, 20)
        for lbl, val in [("Obras", metrics.get("works", 0)), ("Tags total", metrics.get("total_tags", 0)),
                          ("Vocabulário único", metrics.get("unique_tags", 0)), ("Participantes", metrics.get("active_users", 0)),
                          ("Acurácia do modelo", f"{store.model_state().get('accuracy', 0.0):.2f}")]:
            line(f"{lbl}: {val}")
        spacer(8)
        if not works_df.empty:
            line("2. Obras e metadados", "Times-Bold", 16, 20)
            for _, row in works_df.iterrows():
                line(f"- {row.get('title', '')} | {row.get('artist', '')} | {row.get('year', '')}", "Times-Bold", 12, 16)
                for fld, lbl in [("museum", "Museu"), ("period", "Período"), ("technique", "Técnica"), ("material", "Material")]:
                    if str(row.get(fld, "")).strip():
                        line(f"  {lbl}: {row.get(fld, '')}")
                spacer(3)
        if not tags_df.empty:
            line("3. Tags mais frequentes", "Times-Bold", 16, 20)
            for tag, count in tags_df["tag"].value_counts().head(20).items():
                line(f"- {tag}: {count}")
            spacer(5)
            clusters = ml.cluster_terms(tags_df["tag"].astype(str).tolist(), threshold=0.66)
            line("4. Agrupamentos semânticos", "Times-Bold", 16, 20)
            for idx, cluster in enumerate(clusters[:15], 1):
                line(f"- Grupo {idx}: {', '.join(cluster)}")
        if not validations_df.empty:
            spacer(5)
            line("5. Validações recentes", "Times-Bold", 16, 20)
            for _, row in validations_df.tail(30).iterrows():
                line(f"- {row.get('created_at', '')} | {row.get('decision', '')} | {row.get('validated_entity', '')} | {row.get('validated_concept_label', '')}")
        pdf.save()
        buffer.seek(0)
        return buffer.getvalue()

    open_panel("obras e exportação")
    works = store.works()
    t1, t2, t3, t4 = st.tabs(["Obras", "Nova obra", "Exportar CSV", "Exportar PDF"])

    with t1:
        if not works:
            st.info("Nenhuma obra cadastrada.")
        else:
            works_df = to_dataframe(works)
            display_cols = [c for c in ["title", "artist", "year", "museum", "collection", "period", "technique", "material", "created_at"] if c in works_df.columns]
            st.dataframe(works_df[display_cols], use_container_width=True, hide_index=True)
            for work in works:
                meta = resolve_work_metadata(work)
                c1, c2, c3 = st.columns([0.8, 1.8, 0.6])
                with c1:
                    st.image(work.get("image_url"), use_container_width=True)
                with c2:
                    info = " · ".join([p for p in [work.get("artist"), work.get("year"), meta.get("museum"), meta.get("period")] if p])
                    st.markdown(f"<div class='story-card'><div class='story-title'>{work.get('title')}</div><div class='story-copy'>{info}<br>{first_sentence(work.get('description'))}</div></div>", unsafe_allow_html=True)
                with c3:
                    if st.button("Excluir", key=f"del-{work.get('id')}", use_container_width=True):
                        store.save_works([w for w in store.works() if w.get("id") != work.get("id")])
                        store.save_tags([t for t in store.tags() if t.get("work_id") != work.get("id")])
                        ml.train()
                        st.success("Obra excluída.")
                        st.rerun()
                st.markdown("<div class='soft-line'></div>", unsafe_allow_html=True)

    with t2:
        with st.form("new-work"):
            c1, c2, c3 = st.columns(3)
            with c1:
                title = st.text_input("Título")
                artist = st.text_input("Artista")
                year = st.text_input("Ano")
                image_url = st.text_input("URL da imagem")
            with c2:
                museum = st.text_input("Museu / Instituição")
                collection = st.text_input("Coleção")
                place = st.text_input("Lugar")
                period = st.text_input("Período")
            with c3:
                technique = st.text_input("Técnica")
                material = st.text_input("Material")
                ext_label = st.text_input("Rótulo open data")
                ext_url = st.text_input("URL open data")
            tags_field = st.text_input("Tags institucionais (separadas por vírgula)")
            description = st.text_area("Descrição", height=100)
            if st.form_submit_button("Adicionar obra"):
                if not title.strip() or not artist.strip():
                    st.warning("Preencha ao menos título e artista.")
                else:
                    store.add_work(title, artist, year, description, image_url,
                                   [p.strip() for p in tags_field.split(",") if p.strip()],
                                   museum=museum, collection=collection, place=place, period=period,
                                   technique=technique, material=material,
                                   external_reference_label=ext_label, external_reference_url=ext_url)
                    ml.train()
                    st.success("Obra adicionada.")
                    st.rerun()

    with t3:
        works_df = to_dataframe(store.works())
        tags_df = build_tag_dataframe(store)
        concepts_df = to_dataframe(store.concepts())
        validations_df = to_dataframe(store.validations())
        users_df = to_dataframe(store.users())
        st.download_button("Obras (CSV)", works_df.to_csv(index=False).encode("utf-8"), "obras.csv", "text/csv", use_container_width=True)
        st.download_button("Tags (CSV)", tags_df.to_csv(index=False).encode("utf-8"), "tags.csv", "text/csv", use_container_width=True)
        st.download_button("Conceitos (CSV)", concepts_df.to_csv(index=False).encode("utf-8"), "conceitos.csv", "text/csv", use_container_width=True)
        st.download_button("Validações (CSV)", validations_df.to_csv(index=False).encode("utf-8"), "validacoes.csv", "text/csv", use_container_width=True)
        st.download_button("Participantes (CSV)", users_df.to_csv(index=False).encode("utf-8"), "participantes.csv", "text/csv", use_container_width=True)

    with t4:
        try:
            pdf_bytes = build_pdf_bytes()
            st.markdown("<div class='summary-block'>Relatório completo com métricas, metadados das obras, tags, agrupamentos semânticos, conceitos e validações.</div>", unsafe_allow_html=True)
            st.download_button("Baixar relatório PDF", pdf_bytes, "relatorio_folksonomia.pdf", "application/pdf", use_container_width=True)
        except Exception as exc:
            st.warning(f"PDF indisponível nesta execução: {exc}")
    close_panel()


def render_footer() -> None:
    st.markdown("<div style='text-align:center;margin-top:1.5rem;margin-bottom:2rem;font-size:0.82rem;color:#666'>folksonomia · interface translúcida · aprendizagem incremental · análise semântica participativa</div>", unsafe_allow_html=True)


def main() -> None:
    render_css()
    store = JsonStore()
    init_session()
    ml = SemanticLearner(store)
    run_automation_engine(store, ml)

    if not st.session_state.get("intro_complete", False) and store.settings().get("public_intro_enabled", True):
        hero_panel(store)
        intro_flow(store)
        render_footer()
        return

    topbar(store)
    hero_panel(store)

    public_tabs = st.tabs(["obras", "descoberta", "meu histórico", "administração"])
    with public_tabs[0]:
        render_public_explore(store, ml)
    with public_tabs[1]:
        render_public_semantics(store, ml)
    with public_tabs[2]:
        render_public_history(store)
    with public_tabs[3]:
        if not st.session_state.get("admin_authenticated", False):
            render_admin_login(store)
        else:
            admin_tabs = st.tabs(["painel geral", "validação", "conceitos", "machine learning", "análise temporal", "grafo 3D", "obras e dados"])
            with admin_tabs[0]:
                render_admin_dashboard(store, ml)
            with admin_tabs[1]:
                render_admin_validation(store, ml)
            with admin_tabs[2]:
                render_admin_concepts(store, ml)
            with admin_tabs[3]:
                render_admin_ml(store, ml)
            with admin_tabs[4]:
                render_admin_automation(store, ml)
            with admin_tabs[5]:
                render_admin_graph(store)
            with admin_tabs[6]:
                render_admin_data(store, ml)
            if st.button("Sair da administração", use_container_width=True):
                st.session_state["admin_authenticated"] = False
                st.rerun()
    render_footer()


if __name__ == "__main__":
    main()
