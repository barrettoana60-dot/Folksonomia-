from __future__ import annotations

import base64
import hashlib
import json
import math
import os
import random
import re
import unicodedata
import uuid
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
import streamlit.components.v1 as components

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

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import simpleSplit
    HAS_REPORTLAB = True
except Exception:
    A4 = None
    canvas = None
    simpleSplit = None
    HAS_REPORTLAB = False

st.set_page_config(page_title="folksonomia", layout="wide", initial_sidebar_state="collapsed")


def safe_plotly_chart(fig: Any, *, use_container_width: bool = True) -> None:
    if HAS_PLOTLY and fig is not None:
        st.plotly_chart(fig, use_container_width=use_container_width)


def render_bar_chart_df(df: pd.DataFrame, x: str, y: str, *, orientation: str = "v", height: int = 360) -> None:
    if df is None or df.empty:
        st.info("dados insuficientes para visualização.")
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
        st.info("dados insuficientes para visualização.")
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

PSEUDONYM_WORDS_A = ['Neblina',
 'Atlas',
 'Veludo',
 'Orvalho',
 'Prisma',
 'Argila',
 'Cromo',
 'Cedro',
 'Miragem',
 'Aurora',
 'Sombra',
 'Bruma',
 'Linho',
 'Vidro',
 'Marfim',
 'Lótus',
 'Névoa',
 'Basalto',
 'Íris',
 'Nuvem',
 'Fresta',
 'Nexo',
 'Lavra',
 'Ângulo',
 'Traço',
 'Grão',
 'Eco',
 'Silêncio',
 'Ponte',
 'Lume',
 'Gravura',
 'Carta',
 'Janela',
 'Fôlego',
 'Memória',
 'Tecido',
 'Arquivo',
 'Escala',
 'Rastro',
 'Rumor',
 'Tempo',
 'Limiar',
 'Pulso',
 'Museu',
 'Luz',
 'Matiz',
 'Camada',
 'Grafo']
PSEUDONYM_WORDS_B = ['Claro',
 'Sutil',
 'Profundo',
 'Moderno',
 'Linear',
 'Translúcido',
 'Quieto',
 'Semântico',
 'Conectado',
 'Analítico',
 'Curatorial',
 'Expandido',
 'Aberto',
 'Lento',
 'Emergente',
 'Refinado',
 'Plural',
 'Contextual',
 'Digital',
 'Relacional',
 'Sensível',
 'Institucional',
 'Popular',
 'Interligado',
 'Latente',
 'Vivo',
 'Estrutural',
 'Inteligente',
 'Sintético',
 'Dialógico',
 'Contínuo',
 'Documental',
 'Participativo',
 'Interpretativo',
 'Experimental',
 'Lexical',
 'Temporal',
 'Híbrido',
 'Assistido',
 'Persistente',
 'Reconciliado',
 'Desambiguado',
 'Técnico',
 'Social',
 'Incremental',
 'Curvo',
 'Axial',
 'Radial',
 'Preciso']
STOPWORDS_PT = {'a',
 'ao',
 'aos',
 'as',
 'com',
 'como',
 'da',
 'das',
 'de',
 'do',
 'dos',
 'e',
 'em',
 'entre',
 'era',
 'estar',
 'foi',
 'há',
 'já',
 'mais',
 'muita',
 'muitas',
 'muito',
 'muitos',
 'na',
 'nas',
 'no',
 'nos',
 'não',
 'o',
 'os',
 'ou',
 'outra',
 'outras',
 'outro',
 'outros',
 'para',
 'por',
 'pouca',
 'poucas',
 'pouco',
 'poucos',
 'que',
 'se',
 'sem',
 'ser',
 'sim',
 'sob',
 'sobre',
 'são',
 'tais',
 'tal',
 'ter',
 'um',
 'uma',
 'umas',
 'uns',
 'à',
 'às',
 'é'}
SEED_VOCAB = {'pessoa': ['artista',
            'autor',
            'retratado',
            'mulher',
            'homem',
            'criança',
            'anjo',
            'santo',
            'santa',
            'virgem',
            'maria',
            'jesus',
            'rei',
            'rainha',
            'soldado',
            'camponês',
            'pescador',
            'músico',
            'poeta',
            'nobre',
            'escravizado',
            'trabalhador',
            'operário',
            'dançarina',
            'mãe',
            'pai',
            'família',
            'casal',
            'autorretrato',
            'personagem',
            'figura humana',
            'busto',
            'grupo',
            'multidão',
            'povo',
            'índio',
            'indígena',
            'africano',
            'afro-brasileiro',
            'europeu',
            'colonizador',
            'missionário',
            'navegador',
            'monarca',
            'cavaleiro',
            'pastor',
            'profeta',
            'apóstolo',
            'deusa',
            'deus',
            'herói',
            'heroína',
            'guerreiro',
            'sacerdote',
            'monge',
            'freira',
            'senhora',
            'menino',
            'menina',
            'jovem',
            'idoso',
            'mulher negra',
            'mulher branca',
            'homem negro',
            'homem branco',
            'companheira',
            'viúva',
            'esposa',
            'marinheiro',
            'cientista',
            'curador',
            'colecionador',
            'pintor',
            'escultor',
            'arquiteto',
            'artesão',
            'tecelã',
            'lavrador',
            'bordadeira',
            'curandeira',
            'xamã',
            'sambista',
            'capoeirista',
            'parteira',
            'líder',
            'trabalhadora',
            'chefe de família',
            'protagonista'],
 'lugar': ['rio de janeiro',
           'brasil',
           'lisboa',
           'madrid',
           'paris',
           'roma',
           'londres',
           'américa',
           'europa',
           'africa',
           'ásia',
           'oceania',
           'cidade',
           'campo',
           'praia',
           'mar',
           'porto',
           'igreja',
           'capela',
           'templo',
           'praça',
           'rua',
           'casa',
           'palácio',
           'favela',
           'sertão',
           'amazônia',
           'bahia',
           'minas gerais',
           'pernambuco',
           'são paulo',
           'recife',
           'salvador',
           'niterói',
           'museu',
           'galeria',
           'atelier',
           'oficina',
           'navio',
           'floresta',
           'montanha',
           'rio',
           'deserto',
           'paisagem',
           'interior',
           'jardim',
           'quintal',
           'cozinha',
           'sala',
           'quarto',
           'janela',
           'varanda',
           'terreiro',
           'aldeia',
           'quilombo',
           'engenho',
           'fazenda',
           'mercado',
           'hospital',
           'escola',
           'biblioteca',
           'arquivo',
           'acervo',
           'ateliê',
           'centro histórico',
           'subúrbio',
           'periferia',
           'lago',
           'ponte',
           'estrada',
           'cemitério',
           'estação',
           'metrô',
           'porto seguro',
           'ibero-américa',
           'península',
           'catedral',
           'mosteiro',
           'convento',
           'ruína',
           'sítio arqueológico'],
 'periodo': ['renascimento',
             'barroco',
             'rococó',
             'neoclassicismo',
             'romantismo',
             'realismo',
             'impressionismo',
             'pós-impressionismo',
             'modernismo',
             'contemporâneo',
             'medieval',
             'antiguidade',
             'século xvi',
             'século xvii',
             'século xviii',
             'século xix',
             'século xx',
             'século xxi',
             'colônia',
             'império',
             'república',
             'ditadura',
             'vanguarda',
             'art déco',
             'art nouveau',
             'anos 1920',
             'anos 1930',
             'anos 1940',
             'anos 1950',
             'anos 1960',
             'anos 1970',
             'anos 1980',
             'anos 1990',
             'período colonial',
             'período imperial',
             'primeira república',
             'segunda guerra',
             'belle époque',
             'era moderna',
             'idade média',
             'idade contemporânea',
             'brasil colonial',
             'brasil império',
             'primeiro reinado',
             'segundo reinado',
             'primeira metade do século xx',
             'segunda metade do século xx',
             'virada do século',
             'pós-guerra',
             'tempo presente',
             'contemporaneidade',
             'passado',
             'memória histórica'],
 'material': ['ouro',
              'prata',
              'bronze',
              'ferro',
              'aço',
              'madeira',
              'papel',
              'tela',
              'canvas',
              'linho',
              'algodão',
              'barro',
              'argila',
              'terracota',
              'porcelana',
              'cerâmica',
              'vidro',
              'marfim',
              'pedra',
              'mármore',
              'granito',
              'gesso',
              'tinta',
              'óleo',
              'aquarela',
              'nanquim',
              'grafite',
              'carvão',
              'pastel',
              'pigmento',
              'verniz',
              'resina',
              'plástico',
              'acrílico',
              'tecido',
              'couro',
              'osso',
              'concha',
              'madrepérola',
              'folha de ouro',
              'papel fotográfico',
              'negativo',
              'filme',
              'poliéster',
              'metal',
              'latão',
              'cobre',
              'alumínio',
              'bambu',
              'palha',
              'fibra',
              'lã',
              'seda',
              'miçanga',
              'pérola',
              'semente',
              'papelão',
              'papel machê',
              'betume',
              'cimento',
              'concreto',
              'azulejo',
              'esmalte',
              'bordado',
              'linha',
              'barbante'],
 'tecnica': ['óleo sobre tela',
             'aquarela',
             'desenho',
             'gravura',
             'litografia',
             'xilogravura',
             'serigrafia',
             'fotografia',
             'colagem',
             'escultura',
             'modelagem',
             'bordado',
             'crochê',
             'tecelagem',
             'entalhe',
             'fundição',
             'esmaltagem',
             'têmpera',
             'mosaico',
             'fresco',
             'aguada',
             'spray',
             'estêncil',
             'instalação',
             'performance',
             'vídeo',
             'arte digital',
             'impressão 3d',
             'fotomontagem',
             'assemblage',
             'ponta seca',
             'água-forte',
             'água-tinta',
             'cerâmica',
             'pintura mural',
             'grafite urbano',
             'monotipia',
             'gravura em metal',
             'escultura em madeira',
             'escultura em bronze',
             'dobradura',
             'costura',
             'aplique',
             'fusão',
             'lapidação',
             'fundição por cera perdida',
             'xilo',
             'tapeçaria',
             'aerografia',
             'relevo',
             'baixo-relevo',
             'alto-relevo',
             'encáustica',
             'gouache',
             'pastel seco',
             'pastel oleoso'],
 'iconografia': ['crucificação',
                 'anunciação',
                 'natividade',
                 'pietá',
                 'sagrada família',
                 'última ceia',
                 'madona',
                 'coroação',
                 'martírio',
                 'batalha',
                 'retratos oficiais',
                 'paisagem marinha',
                 'natureza-morta',
                 'vanitas',
                 'caça',
                 'colheita',
                 'festa',
                 'carnaval',
                 'procissão',
                 'trabalho',
                 'maternidade',
                 'família',
                 'escravidão',
                 'abolição',
                 'independência',
                 'mitologia',
                 'alegoria',
                 'trindade',
                 'santo antônio',
                 'são jorge',
                 'virgem maria',
                 'menino jesus',
                 'anjos',
                 'bandeira',
                 'barco',
                 'cavalo',
                 'flor',
                 'fruta',
                 'mesa posta',
                 'janela',
                 'espelho',
                 'violão',
                 'tambor',
                 'máscara',
                 'coroa',
                 'espada',
                 'livro',
                 'mapa',
                 'cidade ideal',
                 'naufrágio',
                 'dança',
                 'corpo',
                 'olhar',
                 'mão',
                 'casa',
                 'refeição',
                 'rede',
                 'ninho',
                 'tecido',
                 'costura',
                 'mulher chefe de família',
                 'ancestralidade',
                 'resistência'],
 'tema': ['religião',
          'devoção',
          'memória',
          'identidade',
          'ancestralidade',
          'gênero',
          'família',
          'liderança feminina',
          'trabalho',
          'violência',
          'guerra',
          'paz',
          'amor',
          'solidão',
          'natureza',
          'urbanidade',
          'poder',
          'colonialismo',
          'escravidão',
          'resistência',
          'território',
          'migração',
          'cotidiano',
          'infância',
          'velhice',
          'celebração',
          'luto',
          'ritual',
          'afeto',
          'cuidado',
          'maternidade',
          'paternidade',
          'saudade',
          'esperança',
          'fé',
          'opressão',
          'liberdade',
          'desigualdade',
          'classe social',
          'raça',
          'representação',
          'corpo',
          'política',
          'nação',
          'patrimônio',
          'museu',
          'documentação',
          'arquivo',
          'coleção',
          'tecnologia',
          'inovação',
          'folksonomia',
          'participação',
          'acessibilidade',
          'inclusão',
          'curadoria',
          'educação',
          'comunidade',
          'cultura popular',
          'tradição',
          'modernidade',
          'futuro',
          'tempo',
          'silêncio',
          'movimento'],
 'evento_historico': ['independência do brasil',
                      'abolição da escravidão',
                      'proclamação da república',
                      'segunda guerra mundial',
                      'primeira guerra mundial',
                      'revolução industrial',
                      'revolução francesa',
                      'descobrimento',
                      'chegada da corte',
                      'semana de 22',
                      'ditadura militar',
                      'redemocratização',
                      'queda da monarquia',
                      'guerra do paraguai',
                      'revolta da vacina',
                      'revolta da chibata',
                      'cabanagem',
                      'inconfidência mineira',
                      'conjuração baiana',
                      'revolução de 1930',
                      'golpe de 1964',
                      'diretas já',
                      'era vargas',
                      'confederação do equador',
                      'guerra fria',
                      'pós-abolição',
                      'expansão colonial',
                      'missões jesuíticas',
                      'reforma protestante',
                      'contrarreforma',
                      'concílio de trento'],
 'grupo_social_cultural': ['indígena',
                           'quilombola',
                           'afro-brasileiro',
                           'imigrante',
                           'camponês',
                           'elite',
                           'nobreza',
                           'clero',
                           'trabalhadores',
                           'mulheres',
                           'homens',
                           'crianças',
                           'idosos',
                           'famílias',
                           'comunidade',
                           'povo',
                           'pescadores',
                           'marinheiros',
                           'artistas',
                           'artesãos',
                           'moradores de favela',
                           'periferia',
                           'comunidade tradicional',
                           'ribeirinhos',
                           'povos originários',
                           'diáspora africana',
                           'irmandade',
                           'confraria',
                           'coletivo',
                           'movimento social',
                           'chefes de família',
                           'mães solo',
                           'operariado',
                           'burguesia',
                           'soldados',
                           'estudantes',
                           'migrantes',
                           'refugiados',
                           'sertanejos']}
SEED_CONCEPTS = [{'id': 'seed-01-001', 'label': 'artista', 'category': 'pessoa', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-01-002', 'label': 'autor', 'category': 'pessoa', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-01-003', 'label': 'retratado', 'category': 'pessoa', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-01-004', 'label': 'mulher', 'category': 'pessoa', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-01-005', 'label': 'homem', 'category': 'pessoa', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-01-006', 'label': 'criança', 'category': 'pessoa', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-01-007', 'label': 'anjo', 'category': 'pessoa', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-01-008', 'label': 'santo', 'category': 'pessoa', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-01-009', 'label': 'santa', 'category': 'pessoa', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-01-010', 'label': 'virgem', 'category': 'pessoa', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-01-011', 'label': 'maria', 'category': 'pessoa', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-01-012', 'label': 'jesus', 'category': 'pessoa', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-01-013', 'label': 'rei', 'category': 'pessoa', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-01-014', 'label': 'rainha', 'category': 'pessoa', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-01-015', 'label': 'soldado', 'category': 'pessoa', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-01-016', 'label': 'camponês', 'category': 'pessoa', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-01-017', 'label': 'pescador', 'category': 'pessoa', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-01-018', 'label': 'músico', 'category': 'pessoa', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-01-019', 'label': 'poeta', 'category': 'pessoa', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-01-020', 'label': 'nobre', 'category': 'pessoa', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-01-021',
  'label': 'escravizado',
  'category': 'pessoa',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-01-022',
  'label': 'trabalhador',
  'category': 'pessoa',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-01-023', 'label': 'operário', 'category': 'pessoa', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-01-024', 'label': 'dançarina', 'category': 'pessoa', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-01-025', 'label': 'mãe', 'category': 'pessoa', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-01-026', 'label': 'pai', 'category': 'pessoa', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-01-027', 'label': 'família', 'category': 'pessoa', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-01-028', 'label': 'casal', 'category': 'pessoa', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-01-029',
  'label': 'autorretrato',
  'category': 'pessoa',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-01-030',
  'label': 'personagem',
  'category': 'pessoa',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-01-031',
  'label': 'figura humana',
  'category': 'pessoa',
  'aliases': ['figura-humana', 'figura_humana'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-01-032', 'label': 'busto', 'category': 'pessoa', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-01-033', 'label': 'grupo', 'category': 'pessoa', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-01-034', 'label': 'multidão', 'category': 'pessoa', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-01-035', 'label': 'povo', 'category': 'pessoa', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-01-036', 'label': 'índio', 'category': 'pessoa', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-01-037', 'label': 'indígena', 'category': 'pessoa', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-01-038', 'label': 'africano', 'category': 'pessoa', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-01-039',
  'label': 'afro-brasileiro',
  'category': 'pessoa',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-01-040', 'label': 'europeu', 'category': 'pessoa', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-01-041',
  'label': 'colonizador',
  'category': 'pessoa',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-01-042',
  'label': 'missionário',
  'category': 'pessoa',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-01-043', 'label': 'navegador', 'category': 'pessoa', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-01-044', 'label': 'monarca', 'category': 'pessoa', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-01-045', 'label': 'cavaleiro', 'category': 'pessoa', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-01-046', 'label': 'pastor', 'category': 'pessoa', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-01-047', 'label': 'profeta', 'category': 'pessoa', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-01-048', 'label': 'apóstolo', 'category': 'pessoa', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-01-049', 'label': 'deusa', 'category': 'pessoa', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-01-050', 'label': 'deus', 'category': 'pessoa', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-01-051', 'label': 'herói', 'category': 'pessoa', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-01-052', 'label': 'heroína', 'category': 'pessoa', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-01-053', 'label': 'guerreiro', 'category': 'pessoa', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-01-054', 'label': 'sacerdote', 'category': 'pessoa', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-01-055', 'label': 'monge', 'category': 'pessoa', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-01-056', 'label': 'freira', 'category': 'pessoa', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-01-057', 'label': 'senhora', 'category': 'pessoa', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-01-058', 'label': 'menino', 'category': 'pessoa', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-01-059', 'label': 'menina', 'category': 'pessoa', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-01-060', 'label': 'jovem', 'category': 'pessoa', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-01-061', 'label': 'idoso', 'category': 'pessoa', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-01-062',
  'label': 'mulher negra',
  'category': 'pessoa',
  'aliases': ['mulher-negra', 'mulher_negra'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-01-063',
  'label': 'mulher branca',
  'category': 'pessoa',
  'aliases': ['mulher-branca', 'mulher_branca'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-01-064',
  'label': 'homem negro',
  'category': 'pessoa',
  'aliases': ['homem-negro', 'homem_negro'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-01-065',
  'label': 'homem branco',
  'category': 'pessoa',
  'aliases': ['homem-branco', 'homem_branco'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-01-066',
  'label': 'companheira',
  'category': 'pessoa',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-01-067', 'label': 'viúva', 'category': 'pessoa', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-01-068', 'label': 'esposa', 'category': 'pessoa', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-01-069',
  'label': 'marinheiro',
  'category': 'pessoa',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-01-070', 'label': 'cientista', 'category': 'pessoa', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-01-071', 'label': 'curador', 'category': 'pessoa', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-01-072',
  'label': 'colecionador',
  'category': 'pessoa',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-01-073', 'label': 'pintor', 'category': 'pessoa', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-01-074', 'label': 'escultor', 'category': 'pessoa', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-01-075', 'label': 'arquiteto', 'category': 'pessoa', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-01-076', 'label': 'artesão', 'category': 'pessoa', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-01-077', 'label': 'tecelã', 'category': 'pessoa', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-01-078', 'label': 'lavrador', 'category': 'pessoa', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-01-079',
  'label': 'bordadeira',
  'category': 'pessoa',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-01-080',
  'label': 'curandeira',
  'category': 'pessoa',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-01-081', 'label': 'xamã', 'category': 'pessoa', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-01-082', 'label': 'sambista', 'category': 'pessoa', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-01-083',
  'label': 'capoeirista',
  'category': 'pessoa',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-01-084', 'label': 'parteira', 'category': 'pessoa', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-01-085', 'label': 'líder', 'category': 'pessoa', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-01-086',
  'label': 'trabalhadora',
  'category': 'pessoa',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-01-087',
  'label': 'chefe de família',
  'category': 'pessoa',
  'aliases': ['chefe-de-família', 'chefe_de_família'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-01-088',
  'label': 'protagonista',
  'category': 'pessoa',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-02-001',
  'label': 'rio de janeiro',
  'category': 'lugar',
  'aliases': ['rio-de-janeiro', 'rio_de_janeiro'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-02-002', 'label': 'brasil', 'category': 'lugar', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-02-003', 'label': 'lisboa', 'category': 'lugar', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-02-004', 'label': 'madrid', 'category': 'lugar', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-02-005', 'label': 'paris', 'category': 'lugar', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-02-006', 'label': 'roma', 'category': 'lugar', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-02-007', 'label': 'londres', 'category': 'lugar', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-02-008', 'label': 'américa', 'category': 'lugar', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-02-009', 'label': 'europa', 'category': 'lugar', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-02-010', 'label': 'africa', 'category': 'lugar', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-02-011', 'label': 'ásia', 'category': 'lugar', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-02-012', 'label': 'oceania', 'category': 'lugar', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-02-013', 'label': 'cidade', 'category': 'lugar', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-02-014', 'label': 'campo', 'category': 'lugar', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-02-015', 'label': 'praia', 'category': 'lugar', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-02-016', 'label': 'mar', 'category': 'lugar', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-02-017', 'label': 'porto', 'category': 'lugar', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-02-018', 'label': 'igreja', 'category': 'lugar', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-02-019', 'label': 'capela', 'category': 'lugar', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-02-020', 'label': 'templo', 'category': 'lugar', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-02-021', 'label': 'praça', 'category': 'lugar', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-02-022', 'label': 'rua', 'category': 'lugar', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-02-023', 'label': 'casa', 'category': 'lugar', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-02-024', 'label': 'palácio', 'category': 'lugar', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-02-025', 'label': 'favela', 'category': 'lugar', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-02-026', 'label': 'sertão', 'category': 'lugar', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-02-027', 'label': 'amazônia', 'category': 'lugar', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-02-028', 'label': 'bahia', 'category': 'lugar', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-02-029',
  'label': 'minas gerais',
  'category': 'lugar',
  'aliases': ['minas-gerais', 'minas_gerais'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-02-030', 'label': 'pernambuco', 'category': 'lugar', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-02-031',
  'label': 'são paulo',
  'category': 'lugar',
  'aliases': ['são-paulo', 'são_paulo'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-02-032', 'label': 'recife', 'category': 'lugar', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-02-033', 'label': 'salvador', 'category': 'lugar', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-02-034', 'label': 'niterói', 'category': 'lugar', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-02-035', 'label': 'museu', 'category': 'lugar', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-02-036', 'label': 'galeria', 'category': 'lugar', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-02-037', 'label': 'atelier', 'category': 'lugar', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-02-038', 'label': 'oficina', 'category': 'lugar', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-02-039', 'label': 'navio', 'category': 'lugar', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-02-040', 'label': 'floresta', 'category': 'lugar', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-02-041', 'label': 'montanha', 'category': 'lugar', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-02-042', 'label': 'rio', 'category': 'lugar', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-02-043', 'label': 'deserto', 'category': 'lugar', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-02-044', 'label': 'paisagem', 'category': 'lugar', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-02-045', 'label': 'interior', 'category': 'lugar', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-02-046', 'label': 'jardim', 'category': 'lugar', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-02-047', 'label': 'quintal', 'category': 'lugar', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-02-048', 'label': 'cozinha', 'category': 'lugar', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-02-049', 'label': 'sala', 'category': 'lugar', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-02-050', 'label': 'quarto', 'category': 'lugar', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-02-051', 'label': 'janela', 'category': 'lugar', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-02-052', 'label': 'varanda', 'category': 'lugar', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-02-053', 'label': 'terreiro', 'category': 'lugar', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-02-054', 'label': 'aldeia', 'category': 'lugar', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-02-055', 'label': 'quilombo', 'category': 'lugar', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-02-056', 'label': 'engenho', 'category': 'lugar', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-02-057', 'label': 'fazenda', 'category': 'lugar', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-02-058', 'label': 'mercado', 'category': 'lugar', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-02-059', 'label': 'hospital', 'category': 'lugar', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-02-060', 'label': 'escola', 'category': 'lugar', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-02-061', 'label': 'biblioteca', 'category': 'lugar', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-02-062', 'label': 'arquivo', 'category': 'lugar', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-02-063', 'label': 'acervo', 'category': 'lugar', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-02-064', 'label': 'ateliê', 'category': 'lugar', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-02-065',
  'label': 'centro histórico',
  'category': 'lugar',
  'aliases': ['centro-histórico', 'centro_histórico'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-02-066', 'label': 'subúrbio', 'category': 'lugar', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-02-067', 'label': 'periferia', 'category': 'lugar', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-02-068', 'label': 'lago', 'category': 'lugar', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-02-069', 'label': 'ponte', 'category': 'lugar', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-02-070', 'label': 'estrada', 'category': 'lugar', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-02-071', 'label': 'cemitério', 'category': 'lugar', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-02-072', 'label': 'estação', 'category': 'lugar', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-02-073', 'label': 'metrô', 'category': 'lugar', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-02-074',
  'label': 'porto seguro',
  'category': 'lugar',
  'aliases': ['porto-seguro', 'porto_seguro'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-02-075',
  'label': 'ibero-américa',
  'category': 'lugar',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-02-076', 'label': 'península', 'category': 'lugar', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-02-077', 'label': 'catedral', 'category': 'lugar', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-02-078', 'label': 'mosteiro', 'category': 'lugar', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-02-079', 'label': 'convento', 'category': 'lugar', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-02-080', 'label': 'ruína', 'category': 'lugar', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-02-081',
  'label': 'sítio arqueológico',
  'category': 'lugar',
  'aliases': ['sítio-arqueológico', 'sítio_arqueológico'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-03-001',
  'label': 'renascimento',
  'category': 'periodo',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-03-002', 'label': 'barroco', 'category': 'periodo', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-03-003', 'label': 'rococó', 'category': 'periodo', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-03-004',
  'label': 'neoclassicismo',
  'category': 'periodo',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-03-005',
  'label': 'romantismo',
  'category': 'periodo',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-03-006', 'label': 'realismo', 'category': 'periodo', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-03-007',
  'label': 'impressionismo',
  'category': 'periodo',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-03-008',
  'label': 'pós-impressionismo',
  'category': 'periodo',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-03-009',
  'label': 'modernismo',
  'category': 'periodo',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-03-010',
  'label': 'contemporâneo',
  'category': 'periodo',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-03-011', 'label': 'medieval', 'category': 'periodo', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-03-012',
  'label': 'antiguidade',
  'category': 'periodo',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-03-013',
  'label': 'século xvi',
  'category': 'periodo',
  'aliases': ['século-xvi', 'século_xvi'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-03-014',
  'label': 'século xvii',
  'category': 'periodo',
  'aliases': ['século-xvii', 'século_xvii'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-03-015',
  'label': 'século xviii',
  'category': 'periodo',
  'aliases': ['século-xviii', 'século_xviii'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-03-016',
  'label': 'século xix',
  'category': 'periodo',
  'aliases': ['século-xix', 'século_xix'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-03-017',
  'label': 'século xx',
  'category': 'periodo',
  'aliases': ['século-xx', 'século_xx'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-03-018',
  'label': 'século xxi',
  'category': 'periodo',
  'aliases': ['século-xxi', 'século_xxi'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-03-019', 'label': 'colônia', 'category': 'periodo', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-03-020', 'label': 'império', 'category': 'periodo', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-03-021',
  'label': 'república',
  'category': 'periodo',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-03-022', 'label': 'ditadura', 'category': 'periodo', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-03-023',
  'label': 'vanguarda',
  'category': 'periodo',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-03-024',
  'label': 'art déco',
  'category': 'periodo',
  'aliases': ['art-déco', 'art_déco'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-03-025',
  'label': 'art nouveau',
  'category': 'periodo',
  'aliases': ['art-nouveau', 'art_nouveau'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-03-026',
  'label': 'anos 1920',
  'category': 'periodo',
  'aliases': ['anos-1920', 'anos_1920'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-03-027',
  'label': 'anos 1930',
  'category': 'periodo',
  'aliases': ['anos-1930', 'anos_1930'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-03-028',
  'label': 'anos 1940',
  'category': 'periodo',
  'aliases': ['anos-1940', 'anos_1940'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-03-029',
  'label': 'anos 1950',
  'category': 'periodo',
  'aliases': ['anos-1950', 'anos_1950'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-03-030',
  'label': 'anos 1960',
  'category': 'periodo',
  'aliases': ['anos-1960', 'anos_1960'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-03-031',
  'label': 'anos 1970',
  'category': 'periodo',
  'aliases': ['anos-1970', 'anos_1970'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-03-032',
  'label': 'anos 1980',
  'category': 'periodo',
  'aliases': ['anos-1980', 'anos_1980'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-03-033',
  'label': 'anos 1990',
  'category': 'periodo',
  'aliases': ['anos-1990', 'anos_1990'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-03-034',
  'label': 'período colonial',
  'category': 'periodo',
  'aliases': ['período-colonial', 'período_colonial'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-03-035',
  'label': 'período imperial',
  'category': 'periodo',
  'aliases': ['período-imperial', 'período_imperial'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-03-036',
  'label': 'primeira república',
  'category': 'periodo',
  'aliases': ['primeira-república', 'primeira_república'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-03-037',
  'label': 'segunda guerra',
  'category': 'periodo',
  'aliases': ['segunda-guerra', 'segunda_guerra'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-03-038',
  'label': 'belle époque',
  'category': 'periodo',
  'aliases': ['belle-époque', 'belle_époque'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-03-039',
  'label': 'era moderna',
  'category': 'periodo',
  'aliases': ['era-moderna', 'era_moderna'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-03-040',
  'label': 'idade média',
  'category': 'periodo',
  'aliases': ['idade-média', 'idade_média'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-03-041',
  'label': 'idade contemporânea',
  'category': 'periodo',
  'aliases': ['idade-contemporânea', 'idade_contemporânea'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-03-042',
  'label': 'brasil colonial',
  'category': 'periodo',
  'aliases': ['brasil-colonial', 'brasil_colonial'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-03-043',
  'label': 'brasil império',
  'category': 'periodo',
  'aliases': ['brasil-império', 'brasil_império'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-03-044',
  'label': 'primeiro reinado',
  'category': 'periodo',
  'aliases': ['primeiro-reinado', 'primeiro_reinado'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-03-045',
  'label': 'segundo reinado',
  'category': 'periodo',
  'aliases': ['segundo-reinado', 'segundo_reinado'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-03-046',
  'label': 'primeira metade do século xx',
  'category': 'periodo',
  'aliases': ['primeira-metade-do-século-xx', 'primeira_metade_do_século_xx'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-03-047',
  'label': 'segunda metade do século xx',
  'category': 'periodo',
  'aliases': ['segunda-metade-do-século-xx', 'segunda_metade_do_século_xx'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-03-048',
  'label': 'virada do século',
  'category': 'periodo',
  'aliases': ['virada-do-século', 'virada_do_século'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-03-049',
  'label': 'pós-guerra',
  'category': 'periodo',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-03-050',
  'label': 'tempo presente',
  'category': 'periodo',
  'aliases': ['tempo-presente', 'tempo_presente'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-03-051',
  'label': 'contemporaneidade',
  'category': 'periodo',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-03-052', 'label': 'passado', 'category': 'periodo', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-03-053',
  'label': 'memória histórica',
  'category': 'periodo',
  'aliases': ['memória-histórica', 'memória_histórica'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-04-001', 'label': 'ouro', 'category': 'material', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-04-002', 'label': 'prata', 'category': 'material', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-04-003', 'label': 'bronze', 'category': 'material', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-04-004', 'label': 'ferro', 'category': 'material', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-04-005', 'label': 'aço', 'category': 'material', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-04-006', 'label': 'madeira', 'category': 'material', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-04-007', 'label': 'papel', 'category': 'material', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-04-008', 'label': 'tela', 'category': 'material', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-04-009', 'label': 'canvas', 'category': 'material', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-04-010', 'label': 'linho', 'category': 'material', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-04-011', 'label': 'algodão', 'category': 'material', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-04-012', 'label': 'barro', 'category': 'material', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-04-013', 'label': 'argila', 'category': 'material', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-04-014',
  'label': 'terracota',
  'category': 'material',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-04-015',
  'label': 'porcelana',
  'category': 'material',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-04-016',
  'label': 'cerâmica',
  'category': 'material',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-04-017', 'label': 'vidro', 'category': 'material', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-04-018', 'label': 'marfim', 'category': 'material', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-04-019', 'label': 'pedra', 'category': 'material', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-04-020', 'label': 'mármore', 'category': 'material', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-04-021', 'label': 'granito', 'category': 'material', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-04-022', 'label': 'gesso', 'category': 'material', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-04-023', 'label': 'tinta', 'category': 'material', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-04-024', 'label': 'óleo', 'category': 'material', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-04-025',
  'label': 'aquarela',
  'category': 'material',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-04-026', 'label': 'nanquim', 'category': 'material', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-04-027', 'label': 'grafite', 'category': 'material', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-04-028', 'label': 'carvão', 'category': 'material', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-04-029', 'label': 'pastel', 'category': 'material', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-04-030',
  'label': 'pigmento',
  'category': 'material',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-04-031', 'label': 'verniz', 'category': 'material', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-04-032', 'label': 'resina', 'category': 'material', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-04-033',
  'label': 'plástico',
  'category': 'material',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-04-034',
  'label': 'acrílico',
  'category': 'material',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-04-035', 'label': 'tecido', 'category': 'material', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-04-036', 'label': 'couro', 'category': 'material', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-04-037', 'label': 'osso', 'category': 'material', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-04-038', 'label': 'concha', 'category': 'material', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-04-039',
  'label': 'madrepérola',
  'category': 'material',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-04-040',
  'label': 'folha de ouro',
  'category': 'material',
  'aliases': ['folha-de-ouro', 'folha_de_ouro'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-04-041',
  'label': 'papel fotográfico',
  'category': 'material',
  'aliases': ['papel-fotográfico', 'papel_fotográfico'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-04-042',
  'label': 'negativo',
  'category': 'material',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-04-043', 'label': 'filme', 'category': 'material', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-04-044',
  'label': 'poliéster',
  'category': 'material',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-04-045', 'label': 'metal', 'category': 'material', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-04-046', 'label': 'latão', 'category': 'material', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-04-047', 'label': 'cobre', 'category': 'material', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-04-048',
  'label': 'alumínio',
  'category': 'material',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-04-049', 'label': 'bambu', 'category': 'material', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-04-050', 'label': 'palha', 'category': 'material', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-04-051', 'label': 'fibra', 'category': 'material', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-04-052', 'label': 'lã', 'category': 'material', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-04-053', 'label': 'seda', 'category': 'material', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-04-054', 'label': 'miçanga', 'category': 'material', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-04-055', 'label': 'pérola', 'category': 'material', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-04-056', 'label': 'semente', 'category': 'material', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-04-057', 'label': 'papelão', 'category': 'material', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-04-058',
  'label': 'papel machê',
  'category': 'material',
  'aliases': ['papel-machê', 'papel_machê'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-04-059', 'label': 'betume', 'category': 'material', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-04-060', 'label': 'cimento', 'category': 'material', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-04-061',
  'label': 'concreto',
  'category': 'material',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-04-062', 'label': 'azulejo', 'category': 'material', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-04-063', 'label': 'esmalte', 'category': 'material', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-04-064', 'label': 'bordado', 'category': 'material', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-04-065', 'label': 'linha', 'category': 'material', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-04-066',
  'label': 'barbante',
  'category': 'material',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-05-001',
  'label': 'óleo sobre tela',
  'category': 'tecnica',
  'aliases': ['óleo-sobre-tela', 'óleo_sobre_tela'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-05-002', 'label': 'aquarela', 'category': 'tecnica', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-05-003', 'label': 'desenho', 'category': 'tecnica', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-05-004', 'label': 'gravura', 'category': 'tecnica', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-05-005',
  'label': 'litografia',
  'category': 'tecnica',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-05-006',
  'label': 'xilogravura',
  'category': 'tecnica',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-05-007',
  'label': 'serigrafia',
  'category': 'tecnica',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-05-008',
  'label': 'fotografia',
  'category': 'tecnica',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-05-009', 'label': 'colagem', 'category': 'tecnica', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-05-010',
  'label': 'escultura',
  'category': 'tecnica',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-05-011',
  'label': 'modelagem',
  'category': 'tecnica',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-05-012', 'label': 'bordado', 'category': 'tecnica', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-05-013', 'label': 'crochê', 'category': 'tecnica', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-05-014',
  'label': 'tecelagem',
  'category': 'tecnica',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-05-015', 'label': 'entalhe', 'category': 'tecnica', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-05-016', 'label': 'fundição', 'category': 'tecnica', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-05-017',
  'label': 'esmaltagem',
  'category': 'tecnica',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-05-018', 'label': 'têmpera', 'category': 'tecnica', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-05-019', 'label': 'mosaico', 'category': 'tecnica', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-05-020', 'label': 'fresco', 'category': 'tecnica', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-05-021', 'label': 'aguada', 'category': 'tecnica', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-05-022', 'label': 'spray', 'category': 'tecnica', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-05-023', 'label': 'estêncil', 'category': 'tecnica', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-05-024',
  'label': 'instalação',
  'category': 'tecnica',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-05-025',
  'label': 'performance',
  'category': 'tecnica',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-05-026', 'label': 'vídeo', 'category': 'tecnica', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-05-027',
  'label': 'arte digital',
  'category': 'tecnica',
  'aliases': ['arte-digital', 'arte_digital'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-05-028',
  'label': 'impressão 3d',
  'category': 'tecnica',
  'aliases': ['impressão-3d', 'impressão_3d'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-05-029',
  'label': 'fotomontagem',
  'category': 'tecnica',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-05-030',
  'label': 'assemblage',
  'category': 'tecnica',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-05-031',
  'label': 'ponta seca',
  'category': 'tecnica',
  'aliases': ['ponta-seca', 'ponta_seca'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-05-032',
  'label': 'água-forte',
  'category': 'tecnica',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-05-033',
  'label': 'água-tinta',
  'category': 'tecnica',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-05-034', 'label': 'cerâmica', 'category': 'tecnica', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-05-035',
  'label': 'pintura mural',
  'category': 'tecnica',
  'aliases': ['pintura-mural', 'pintura_mural'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-05-036',
  'label': 'grafite urbano',
  'category': 'tecnica',
  'aliases': ['grafite-urbano', 'grafite_urbano'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-05-037',
  'label': 'monotipia',
  'category': 'tecnica',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-05-038',
  'label': 'gravura em metal',
  'category': 'tecnica',
  'aliases': ['gravura-em-metal', 'gravura_em_metal'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-05-039',
  'label': 'escultura em madeira',
  'category': 'tecnica',
  'aliases': ['escultura-em-madeira', 'escultura_em_madeira'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-05-040',
  'label': 'escultura em bronze',
  'category': 'tecnica',
  'aliases': ['escultura-em-bronze', 'escultura_em_bronze'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-05-041',
  'label': 'dobradura',
  'category': 'tecnica',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-05-042', 'label': 'costura', 'category': 'tecnica', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-05-043', 'label': 'aplique', 'category': 'tecnica', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-05-044', 'label': 'fusão', 'category': 'tecnica', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-05-045',
  'label': 'lapidação',
  'category': 'tecnica',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-05-046',
  'label': 'fundição por cera perdida',
  'category': 'tecnica',
  'aliases': ['fundição-por-cera-perdida', 'fundição_por_cera_perdida'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-05-047', 'label': 'xilo', 'category': 'tecnica', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-05-048',
  'label': 'tapeçaria',
  'category': 'tecnica',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-05-049',
  'label': 'aerografia',
  'category': 'tecnica',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-05-050', 'label': 'relevo', 'category': 'tecnica', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-05-051',
  'label': 'baixo-relevo',
  'category': 'tecnica',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-05-052',
  'label': 'alto-relevo',
  'category': 'tecnica',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-05-053',
  'label': 'encáustica',
  'category': 'tecnica',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-05-054', 'label': 'gouache', 'category': 'tecnica', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-05-055',
  'label': 'pastel seco',
  'category': 'tecnica',
  'aliases': ['pastel-seco', 'pastel_seco'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-05-056',
  'label': 'pastel oleoso',
  'category': 'tecnica',
  'aliases': ['pastel-oleoso', 'pastel_oleoso'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-06-001',
  'label': 'crucificação',
  'category': 'iconografia',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-06-002',
  'label': 'anunciação',
  'category': 'iconografia',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-06-003',
  'label': 'natividade',
  'category': 'iconografia',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-06-004',
  'label': 'pietá',
  'category': 'iconografia',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-06-005',
  'label': 'sagrada família',
  'category': 'iconografia',
  'aliases': ['sagrada-família', 'sagrada_família'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-06-006',
  'label': 'última ceia',
  'category': 'iconografia',
  'aliases': ['última-ceia', 'última_ceia'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-06-007',
  'label': 'madona',
  'category': 'iconografia',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-06-008',
  'label': 'coroação',
  'category': 'iconografia',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-06-009',
  'label': 'martírio',
  'category': 'iconografia',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-06-010',
  'label': 'batalha',
  'category': 'iconografia',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-06-011',
  'label': 'retratos oficiais',
  'category': 'iconografia',
  'aliases': ['retratos-oficiais', 'retratos_oficiais'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-06-012',
  'label': 'paisagem marinha',
  'category': 'iconografia',
  'aliases': ['paisagem-marinha', 'paisagem_marinha'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-06-013',
  'label': 'natureza-morta',
  'category': 'iconografia',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-06-014',
  'label': 'vanitas',
  'category': 'iconografia',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-06-015', 'label': 'caça', 'category': 'iconografia', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-06-016',
  'label': 'colheita',
  'category': 'iconografia',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-06-017',
  'label': 'festa',
  'category': 'iconografia',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-06-018',
  'label': 'carnaval',
  'category': 'iconografia',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-06-019',
  'label': 'procissão',
  'category': 'iconografia',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-06-020',
  'label': 'trabalho',
  'category': 'iconografia',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-06-021',
  'label': 'maternidade',
  'category': 'iconografia',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-06-022',
  'label': 'família',
  'category': 'iconografia',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-06-023',
  'label': 'escravidão',
  'category': 'iconografia',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-06-024',
  'label': 'abolição',
  'category': 'iconografia',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-06-025',
  'label': 'independência',
  'category': 'iconografia',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-06-026',
  'label': 'mitologia',
  'category': 'iconografia',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-06-027',
  'label': 'alegoria',
  'category': 'iconografia',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-06-028',
  'label': 'trindade',
  'category': 'iconografia',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-06-029',
  'label': 'santo antônio',
  'category': 'iconografia',
  'aliases': ['santo-antônio', 'santo_antônio'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-06-030',
  'label': 'são jorge',
  'category': 'iconografia',
  'aliases': ['são-jorge', 'são_jorge'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-06-031',
  'label': 'virgem maria',
  'category': 'iconografia',
  'aliases': ['virgem-maria', 'virgem_maria'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-06-032',
  'label': 'menino jesus',
  'category': 'iconografia',
  'aliases': ['menino-jesus', 'menino_jesus'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-06-033',
  'label': 'anjos',
  'category': 'iconografia',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-06-034',
  'label': 'bandeira',
  'category': 'iconografia',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-06-035',
  'label': 'barco',
  'category': 'iconografia',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-06-036',
  'label': 'cavalo',
  'category': 'iconografia',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-06-037', 'label': 'flor', 'category': 'iconografia', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-06-038',
  'label': 'fruta',
  'category': 'iconografia',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-06-039',
  'label': 'mesa posta',
  'category': 'iconografia',
  'aliases': ['mesa-posta', 'mesa_posta'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-06-040',
  'label': 'janela',
  'category': 'iconografia',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-06-041',
  'label': 'espelho',
  'category': 'iconografia',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-06-042',
  'label': 'violão',
  'category': 'iconografia',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-06-043',
  'label': 'tambor',
  'category': 'iconografia',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-06-044',
  'label': 'máscara',
  'category': 'iconografia',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-06-045',
  'label': 'coroa',
  'category': 'iconografia',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-06-046',
  'label': 'espada',
  'category': 'iconografia',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-06-047',
  'label': 'livro',
  'category': 'iconografia',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-06-048', 'label': 'mapa', 'category': 'iconografia', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-06-049',
  'label': 'cidade ideal',
  'category': 'iconografia',
  'aliases': ['cidade-ideal', 'cidade_ideal'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-06-050',
  'label': 'naufrágio',
  'category': 'iconografia',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-06-051',
  'label': 'dança',
  'category': 'iconografia',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-06-052',
  'label': 'corpo',
  'category': 'iconografia',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-06-053',
  'label': 'olhar',
  'category': 'iconografia',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-06-054', 'label': 'mão', 'category': 'iconografia', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-06-055', 'label': 'casa', 'category': 'iconografia', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-06-056',
  'label': 'refeição',
  'category': 'iconografia',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-06-057', 'label': 'rede', 'category': 'iconografia', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-06-058',
  'label': 'ninho',
  'category': 'iconografia',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-06-059',
  'label': 'tecido',
  'category': 'iconografia',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-06-060',
  'label': 'costura',
  'category': 'iconografia',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-06-061',
  'label': 'mulher chefe de família',
  'category': 'iconografia',
  'aliases': ['mulher-chefe-de-família', 'mulher_chefe_de_família'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-06-062',
  'label': 'ancestralidade',
  'category': 'iconografia',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-06-063',
  'label': 'resistência',
  'category': 'iconografia',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-07-001', 'label': 'religião', 'category': 'tema', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-07-002', 'label': 'devoção', 'category': 'tema', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-07-003', 'label': 'memória', 'category': 'tema', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-07-004', 'label': 'identidade', 'category': 'tema', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-07-005',
  'label': 'ancestralidade',
  'category': 'tema',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-07-006', 'label': 'gênero', 'category': 'tema', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-07-007', 'label': 'família', 'category': 'tema', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-07-008',
  'label': 'liderança feminina',
  'category': 'tema',
  'aliases': ['liderança-feminina', 'liderança_feminina'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-07-009', 'label': 'trabalho', 'category': 'tema', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-07-010', 'label': 'violência', 'category': 'tema', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-07-011', 'label': 'guerra', 'category': 'tema', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-07-012', 'label': 'paz', 'category': 'tema', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-07-013', 'label': 'amor', 'category': 'tema', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-07-014', 'label': 'solidão', 'category': 'tema', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-07-015', 'label': 'natureza', 'category': 'tema', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-07-016', 'label': 'urbanidade', 'category': 'tema', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-07-017', 'label': 'poder', 'category': 'tema', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-07-018',
  'label': 'colonialismo',
  'category': 'tema',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-07-019', 'label': 'escravidão', 'category': 'tema', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-07-020', 'label': 'resistência', 'category': 'tema', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-07-021', 'label': 'território', 'category': 'tema', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-07-022', 'label': 'migração', 'category': 'tema', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-07-023', 'label': 'cotidiano', 'category': 'tema', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-07-024', 'label': 'infância', 'category': 'tema', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-07-025', 'label': 'velhice', 'category': 'tema', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-07-026', 'label': 'celebração', 'category': 'tema', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-07-027', 'label': 'luto', 'category': 'tema', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-07-028', 'label': 'ritual', 'category': 'tema', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-07-029', 'label': 'afeto', 'category': 'tema', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-07-030', 'label': 'cuidado', 'category': 'tema', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-07-031', 'label': 'maternidade', 'category': 'tema', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-07-032', 'label': 'paternidade', 'category': 'tema', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-07-033', 'label': 'saudade', 'category': 'tema', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-07-034', 'label': 'esperança', 'category': 'tema', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-07-035', 'label': 'fé', 'category': 'tema', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-07-036', 'label': 'opressão', 'category': 'tema', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-07-037', 'label': 'liberdade', 'category': 'tema', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-07-038',
  'label': 'desigualdade',
  'category': 'tema',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-07-039',
  'label': 'classe social',
  'category': 'tema',
  'aliases': ['classe-social', 'classe_social'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-07-040', 'label': 'raça', 'category': 'tema', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-07-041',
  'label': 'representação',
  'category': 'tema',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-07-042', 'label': 'corpo', 'category': 'tema', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-07-043', 'label': 'política', 'category': 'tema', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-07-044', 'label': 'nação', 'category': 'tema', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-07-045', 'label': 'patrimônio', 'category': 'tema', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-07-046', 'label': 'museu', 'category': 'tema', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-07-047',
  'label': 'documentação',
  'category': 'tema',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-07-048', 'label': 'arquivo', 'category': 'tema', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-07-049', 'label': 'coleção', 'category': 'tema', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-07-050', 'label': 'tecnologia', 'category': 'tema', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-07-051', 'label': 'inovação', 'category': 'tema', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-07-052', 'label': 'folksonomia', 'category': 'tema', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-07-053',
  'label': 'participação',
  'category': 'tema',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-07-054',
  'label': 'acessibilidade',
  'category': 'tema',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-07-055', 'label': 'inclusão', 'category': 'tema', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-07-056', 'label': 'curadoria', 'category': 'tema', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-07-057', 'label': 'educação', 'category': 'tema', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-07-058', 'label': 'comunidade', 'category': 'tema', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-07-059',
  'label': 'cultura popular',
  'category': 'tema',
  'aliases': ['cultura-popular', 'cultura_popular'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-07-060', 'label': 'tradição', 'category': 'tema', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-07-061', 'label': 'modernidade', 'category': 'tema', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-07-062', 'label': 'futuro', 'category': 'tema', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-07-063', 'label': 'tempo', 'category': 'tema', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-07-064', 'label': 'silêncio', 'category': 'tema', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-07-065', 'label': 'movimento', 'category': 'tema', 'aliases': [], 'status': 'active', 'source': 'seed'},
 {'id': 'seed-08-001',
  'label': 'independência do brasil',
  'category': 'evento_historico',
  'aliases': ['independência-do-brasil', 'independência_do_brasil'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-08-002',
  'label': 'abolição da escravidão',
  'category': 'evento_historico',
  'aliases': ['abolição-da-escravidão', 'abolição_da_escravidão'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-08-003',
  'label': 'proclamação da república',
  'category': 'evento_historico',
  'aliases': ['proclamação-da-república', 'proclamação_da_república'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-08-004',
  'label': 'segunda guerra mundial',
  'category': 'evento_historico',
  'aliases': ['segunda-guerra-mundial', 'segunda_guerra_mundial'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-08-005',
  'label': 'primeira guerra mundial',
  'category': 'evento_historico',
  'aliases': ['primeira-guerra-mundial', 'primeira_guerra_mundial'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-08-006',
  'label': 'revolução industrial',
  'category': 'evento_historico',
  'aliases': ['revolução-industrial', 'revolução_industrial'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-08-007',
  'label': 'revolução francesa',
  'category': 'evento_historico',
  'aliases': ['revolução-francesa', 'revolução_francesa'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-08-008',
  'label': 'descobrimento',
  'category': 'evento_historico',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-08-009',
  'label': 'chegada da corte',
  'category': 'evento_historico',
  'aliases': ['chegada-da-corte', 'chegada_da_corte'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-08-010',
  'label': 'semana de 22',
  'category': 'evento_historico',
  'aliases': ['semana-de-22', 'semana_de_22'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-08-011',
  'label': 'ditadura militar',
  'category': 'evento_historico',
  'aliases': ['ditadura-militar', 'ditadura_militar'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-08-012',
  'label': 'redemocratização',
  'category': 'evento_historico',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-08-013',
  'label': 'queda da monarquia',
  'category': 'evento_historico',
  'aliases': ['queda-da-monarquia', 'queda_da_monarquia'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-08-014',
  'label': 'guerra do paraguai',
  'category': 'evento_historico',
  'aliases': ['guerra-do-paraguai', 'guerra_do_paraguai'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-08-015',
  'label': 'revolta da vacina',
  'category': 'evento_historico',
  'aliases': ['revolta-da-vacina', 'revolta_da_vacina'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-08-016',
  'label': 'revolta da chibata',
  'category': 'evento_historico',
  'aliases': ['revolta-da-chibata', 'revolta_da_chibata'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-08-017',
  'label': 'cabanagem',
  'category': 'evento_historico',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-08-018',
  'label': 'inconfidência mineira',
  'category': 'evento_historico',
  'aliases': ['inconfidência-mineira', 'inconfidência_mineira'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-08-019',
  'label': 'conjuração baiana',
  'category': 'evento_historico',
  'aliases': ['conjuração-baiana', 'conjuração_baiana'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-08-020',
  'label': 'revolução de 1930',
  'category': 'evento_historico',
  'aliases': ['revolução-de-1930', 'revolução_de_1930'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-08-021',
  'label': 'golpe de 1964',
  'category': 'evento_historico',
  'aliases': ['golpe-de-1964', 'golpe_de_1964'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-08-022',
  'label': 'diretas já',
  'category': 'evento_historico',
  'aliases': ['diretas-já', 'diretas_já'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-08-023',
  'label': 'era vargas',
  'category': 'evento_historico',
  'aliases': ['era-vargas', 'era_vargas'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-08-024',
  'label': 'confederação do equador',
  'category': 'evento_historico',
  'aliases': ['confederação-do-equador', 'confederação_do_equador'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-08-025',
  'label': 'guerra fria',
  'category': 'evento_historico',
  'aliases': ['guerra-fria', 'guerra_fria'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-08-026',
  'label': 'pós-abolição',
  'category': 'evento_historico',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-08-027',
  'label': 'expansão colonial',
  'category': 'evento_historico',
  'aliases': ['expansão-colonial', 'expansão_colonial'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-08-028',
  'label': 'missões jesuíticas',
  'category': 'evento_historico',
  'aliases': ['missões-jesuíticas', 'missões_jesuíticas'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-08-029',
  'label': 'reforma protestante',
  'category': 'evento_historico',
  'aliases': ['reforma-protestante', 'reforma_protestante'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-08-030',
  'label': 'contrarreforma',
  'category': 'evento_historico',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-08-031',
  'label': 'concílio de trento',
  'category': 'evento_historico',
  'aliases': ['concílio-de-trento', 'concílio_de_trento'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-09-001',
  'label': 'indígena',
  'category': 'grupo_social_cultural',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-09-002',
  'label': 'quilombola',
  'category': 'grupo_social_cultural',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-09-003',
  'label': 'afro-brasileiro',
  'category': 'grupo_social_cultural',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-09-004',
  'label': 'imigrante',
  'category': 'grupo_social_cultural',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-09-005',
  'label': 'camponês',
  'category': 'grupo_social_cultural',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-09-006',
  'label': 'elite',
  'category': 'grupo_social_cultural',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-09-007',
  'label': 'nobreza',
  'category': 'grupo_social_cultural',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-09-008',
  'label': 'clero',
  'category': 'grupo_social_cultural',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-09-009',
  'label': 'trabalhadores',
  'category': 'grupo_social_cultural',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-09-010',
  'label': 'mulheres',
  'category': 'grupo_social_cultural',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-09-011',
  'label': 'homens',
  'category': 'grupo_social_cultural',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-09-012',
  'label': 'crianças',
  'category': 'grupo_social_cultural',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-09-013',
  'label': 'idosos',
  'category': 'grupo_social_cultural',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-09-014',
  'label': 'famílias',
  'category': 'grupo_social_cultural',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-09-015',
  'label': 'comunidade',
  'category': 'grupo_social_cultural',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-09-016',
  'label': 'povo',
  'category': 'grupo_social_cultural',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-09-017',
  'label': 'pescadores',
  'category': 'grupo_social_cultural',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-09-018',
  'label': 'marinheiros',
  'category': 'grupo_social_cultural',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-09-019',
  'label': 'artistas',
  'category': 'grupo_social_cultural',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-09-020',
  'label': 'artesãos',
  'category': 'grupo_social_cultural',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-09-021',
  'label': 'moradores de favela',
  'category': 'grupo_social_cultural',
  'aliases': ['moradores-de-favela', 'moradores_de_favela'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-09-022',
  'label': 'periferia',
  'category': 'grupo_social_cultural',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-09-023',
  'label': 'comunidade tradicional',
  'category': 'grupo_social_cultural',
  'aliases': ['comunidade-tradicional', 'comunidade_tradicional'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-09-024',
  'label': 'ribeirinhos',
  'category': 'grupo_social_cultural',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-09-025',
  'label': 'povos originários',
  'category': 'grupo_social_cultural',
  'aliases': ['povos-originários', 'povos_originários'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-09-026',
  'label': 'diáspora africana',
  'category': 'grupo_social_cultural',
  'aliases': ['diáspora-africana', 'diáspora_africana'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-09-027',
  'label': 'irmandade',
  'category': 'grupo_social_cultural',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-09-028',
  'label': 'confraria',
  'category': 'grupo_social_cultural',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-09-029',
  'label': 'coletivo',
  'category': 'grupo_social_cultural',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-09-030',
  'label': 'movimento social',
  'category': 'grupo_social_cultural',
  'aliases': ['movimento-social', 'movimento_social'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-09-031',
  'label': 'chefes de família',
  'category': 'grupo_social_cultural',
  'aliases': ['chefes-de-família', 'chefes_de_família'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-09-032',
  'label': 'mães solo',
  'category': 'grupo_social_cultural',
  'aliases': ['mães-solo', 'mães_solo'],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-09-033',
  'label': 'operariado',
  'category': 'grupo_social_cultural',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-09-034',
  'label': 'burguesia',
  'category': 'grupo_social_cultural',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-09-035',
  'label': 'soldados',
  'category': 'grupo_social_cultural',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-09-036',
  'label': 'estudantes',
  'category': 'grupo_social_cultural',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-09-037',
  'label': 'migrantes',
  'category': 'grupo_social_cultural',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-09-038',
  'label': 'refugiados',
  'category': 'grupo_social_cultural',
  'aliases': [],
  'status': 'active',
  'source': 'seed'},
 {'id': 'seed-09-039',
  'label': 'sertanejos',
  'category': 'grupo_social_cultural',
  'aliases': [],
  'status': 'active',
  'source': 'seed'}]
DEFAULT_WORKS = [{'title': 'Guernica',
  'artist': 'Pablo Picasso',
  'year': '1937',
  'description': 'Grande pintura histórica marcada por dor, fragmentação, guerra, corpo, cavalo, lâmpada e denúncia da '
                 'violência.',
  'image_url': 'https://upload.wikimedia.org/wikipedia/en/7/74/PicassoGuernica.jpg',
  'institutional_tags': ['guerra', 'violência', 'corpo', 'modernismo', 'espanha']},
 {'title': 'A Noite Estrelada',
  'artist': 'Vincent van Gogh',
  'year': '1889',
  'description': 'Paisagem noturna em turbilhão cromático, céu, vila, ciprestes, movimento, emoção e atmosfera.',
  'image_url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/e/ea/Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg/1200px-Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg',
  'institutional_tags': ['paisagem', 'noite', 'céu', 'pós-impressionismo', 'emoção']},
 {'title': 'Mona Lisa',
  'artist': 'Leonardo da Vinci',
  'year': '1503',
  'description': 'Retrato em meio-corpo com sorriso enigmático, figura feminina, paisagem e refinamento renascentista.',
  'image_url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/e/ec/Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_retouched.jpg/800px-Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_retouched.jpg',
  'institutional_tags': ['retrato', 'mulher', 'renascimento', 'paisagem', 'olhar']},
 {'title': 'Operários',
  'artist': 'Tarsila do Amaral',
  'year': '1933',
  'description': 'Composição modernista com múltiplos rostos em camadas, industrialização, povo, trabalho e '
                 'diversidade social.',
  'image_url': 'https://upload.wikimedia.org/wikipedia/pt/8/88/Operarios_-_Tarsila_do_Amaral.jpg',
  'institutional_tags': ['trabalho', 'modernismo', 'indústria', 'povo', 'rosto']},
 {'title': 'Abaporu',
  'artist': 'Tarsila do Amaral',
  'year': '1928',
  'description': 'Figura monumental em cenário solar, cacto, deformação poética, antropofagia e invenção moderna.',
  'image_url': 'https://upload.wikimedia.org/wikipedia/pt/0/05/Tarsila_do_Amaral_-_Abaporu.jpg',
  'institutional_tags': ['modernismo', 'corpo', 'sol', 'paisagem', 'antropofagia']},
 {'title': 'A Redenção de Cam',
  'artist': 'Modesto Brocos',
  'year': '1895',
  'description': 'Cena familiar do final do século XIX que mobiliza debates sobre raça, branqueamento, maternidade e '
                 'ideologia.',
  'image_url': 'https://upload.wikimedia.org/wikipedia/commons/0/0c/A_Reden%C3%A7%C3%A3o_de_Cam_-_Modesto_Brocos.jpg',
  'institutional_tags': ['família', 'raça', 'século xix', 'ideologia', 'maternidade']}]
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
.brand-subtitle { font-size: 0.76rem; color: #5f5f5f; letter-spacing: 0.18em; text-transform: uppercase; }
.hero-panel, .panel {
    background: rgba(255,255,255,0.22); border: 1px solid rgba(255,255,255,0.56);
    border-radius: 30px; backdrop-filter: blur(28px) saturate(168%); -webkit-backdrop-filter: blur(28px) saturate(168%);
    box-shadow: 0 20px 52px rgba(0,0,0,0.10), inset 0 1px 0 rgba(255,255,255,0.76);
}
.hero-panel { padding: 2rem; margin-top: 1rem; }
.hero-grid { display: grid; grid-template-columns: 1fr; gap: 1.2rem; }
.hero-kicker { font-size: 0.84rem; text-transform: uppercase; letter-spacing: 0.20em; color: #6b6b6b; }
.hero-title { font-size: 4.2rem; line-height: 0.92; letter-spacing: -0.06em; color: #1f1f1f; }
.hero-copy { margin-top: 1rem; font-size: 1rem; line-height: 1.9; color: #404040; }
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
    position: relative; overflow: hidden; padding: 0.72rem; min-height: 350px;
    background: rgba(255,255,255,0.24);
    transition: transform 0.45s ease, box-shadow 0.45s ease, border-color 0.45s ease;
    animation: cardFloat 7s ease-in-out infinite;
}
.work-card::before {
    content: ""; position: absolute; top: 0; left: -140%; width: 60%; height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.42), transparent);
    transform: skewX(-18deg);
}
.work-card:hover::before { animation: shinePass 0.9s ease forwards; }
.work-card:hover {
    transform: translateY(-10px) scale(1.02);
    box-shadow: 0 28px 56px rgba(0,0,0,0.12), inset 0 1px 0 rgba(255,255,255,0.76);
    border-color: rgba(255,255,255,0.70);
}
.work-card img {
    width: 100%; height: 300px; object-fit: cover; border-radius: 22px; display: block;
    transition: transform 0.70s ease, filter 0.70s ease;
}
.work-card:hover img { transform: scale(1.08); filter: saturate(1.04) contrast(1.03); }
.work-grid-note { font-size: 0.9rem; color: #555555; line-height: 1.8; margin-bottom: 1rem; }
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
}
.stTextArea textarea, textarea, .stTextInput input, input {
    color: #1b1b1b !important;
    -webkit-text-fill-color: #1b1b1b !important;
    opacity: 1 !important;
    caret-color: #1b1b1b !important;
}
.stTextArea textarea::placeholder, textarea::placeholder, .stTextInput input::placeholder {
    color: #666666 !important;
    -webkit-text-fill-color: #666666 !important;
    opacity: 1 !important;
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
.compact-image-box img { border-radius: 22px; }
[data-testid="stSidebar"] { display: none; }
@media (max-width: 1100px) {
    .hero-microgrid, .metric-strip { grid-template-columns: repeat(2, minmax(0,1fr)); }
}
@media (max-width: 640px) {
    .hero-title { font-size: 2.8rem; }
    .hero-microgrid, .metric-strip { grid-template-columns: 1fr; }
    .work-card img { height: 250px; }
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
        "museum": "Museo Nacional Centro de Arte Reina Sofía",
        "collection": "Colección permanente",
        "place": "Madrid",
        "period": "modernismo do século XX",
        "technique": "óleo sobre tela",
        "material": "tela",
        "external_reference_label": "Wikidata / Wikipedia",
        "external_reference_url": "https://www.wikidata.org/wiki/Q175036",
        "external_entities": ["Picasso", "Guerra Civil Espanhola", "arte moderna europeia"],
    },
    "a noite estrelada": {
        "museum": "The Museum of Modern Art",
        "collection": "Painting and Sculpture",
        "place": "New York",
        "period": "pós-impressionismo",
        "technique": "óleo sobre tela",
        "material": "tela",
        "external_reference_label": "Wikidata / Wikipedia",
        "external_reference_url": "https://www.wikidata.org/wiki/Q219831",
        "external_entities": ["Vincent van Gogh", "paisagem noturna", "pós-impressionismo"],
    },
    "mona lisa": {
        "museum": "Musée du Louvre",
        "collection": "Département des Peintures",
        "place": "Paris",
        "period": "renascimento",
        "technique": "óleo sobre madeira",
        "material": "madeira",
        "external_reference_label": "Wikidata / Wikipedia",
        "external_reference_url": "https://www.wikidata.org/wiki/Q12418",
        "external_entities": ["Leonardo da Vinci", "retrato", "Renascimento italiano"],
    },
}

def resolve_work_metadata(work: Dict[str, Any]) -> Dict[str, Any]:
    title_key = normalize_text(work.get("title", ""))
    seed = OPEN_DATA_SEEDS.get(title_key, {})
    merged = {
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
    return merged

def semantic_tag_links(values: Sequence[str], threshold: float = 0.58) -> List[Dict[str, Any]]:
    unique_values = [value for value in dict.fromkeys([str(v).strip() for v in values if str(v).strip()])]
    rows: List[Dict[str, Any]] = []
    for idx, source in enumerate(unique_values):
        for target in unique_values[idx + 1:]:
            score = hybrid_similarity(source, target)
            if score >= threshold:
                relation = "ortografia próxima" if trigram_similarity(source, target) >= 0.72 and jaccard_words(source, target) < 0.35 else "campo semântico comum"
                rows.append({
                    "tag_a": source,
                    "tag_b": target,
                    "score": round(float(score), 3),
                    "relation": relation,
                })
    rows.sort(key=lambda item: item["score"], reverse=True)
    return rows

def typo_candidate_rows(values: Sequence[str], threshold: float = 0.78) -> List[Dict[str, Any]]:
    unique_values = [value for value in dict.fromkeys([str(v).strip() for v in values if str(v).strip()])]
    rows: List[Dict[str, Any]] = []
    for idx, source in enumerate(unique_values):
        for target in unique_values[idx + 1:]:
            n_source = normalize_text(source)
            n_target = normalize_text(target)
            if not n_source or not n_target or n_source == n_target:
                continue
            tri = trigram_similarity(source, target)
            jac = jaccard_words(source, target)
            if tri >= threshold or (tri >= 0.70 and jac >= 0.50):
                rows.append({
                    "termo_a": source,
                    "termo_b": target,
                    "similaridade_trigrama": round(float(tri), 3),
                    "sobreposição_palavras": round(float(jac), 3),
                })
    rows.sort(key=lambda item: (item["similaridade_trigrama"], item["sobreposição_palavras"]), reverse=True)
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
    wa = set(tokenize(a))
    wb = set(tokenize(b))
    if not wa and not wb:
        return 0.0
    return len(wa & wb) / max(1, len(wa | wb))


def char_trigrams(text: str) -> set[str]:
    text = normalize_text(text)
    if len(text) <= 3:
        return {text} if text else set()
    return {text[i:i+3] for i in range(len(text)-2)}


def trigram_similarity(a: str, b: str) -> float:
    ta = char_trigrams(a)
    tb = char_trigrams(b)
    if not ta and not tb:
        return 0.0
    return len(ta & tb) / max(1, len(ta | tb))


def hybrid_similarity(a: str, b: str) -> float:
    na = normalize_text(a)
    nb = normalize_text(b)
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
            for item in DEFAULT_WORKS[:3]:
                works.append(asdict(WorkRecord(
                    id=make_id("work"),
                    title=item["title"],
                    artist=item["artist"],
                    year=item["year"],
                    description=item["description"],
                    image_url=item["image_url"],
                    institutional_tags=item["institutional_tags"],
                    created_at=now_iso(),
                )))
            write_json(WORKS_FILE, works)
        else:
            works = read_json(WORKS_FILE, [])
            legacy_titles = {"Guernica", "A Noite Estrelada", "Mona Lisa", "Operários", "Abaporu", "A Redenção de Cam"}
            current_titles = {item.get("title", "") for item in works if isinstance(item, dict)}
            if len(works) >= 6 and current_titles.issubset(legacy_titles):
                write_json(WORKS_FILE, works[:3])
        if not USERS_FILE.exists():
            write_json(USERS_FILE, [])
        else:
            users = read_json(USERS_FILE, [])
            changed = False
            for index, user in enumerate(users):
                if isinstance(user, dict):
                    resolved_id = user.get("id") or user.get("user_id")
                    if not resolved_id:
                        resolved_id = f"legacy-user-{index+1}"
                    if user.get("id") != resolved_id:
                        user["id"] = resolved_id
                        changed = True
            if changed:
                write_json(USERS_FILE, users)
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
        changed = False
        normalized_items: List[Dict[str, Any]] = []
        for work in items:
            if not isinstance(work, dict):
                continue
            meta = resolve_work_metadata(work)
            updated = dict(work)
            defaults = {
                "institutional_tags": updated.get("institutional_tags") or [],
                "museum": meta.get("museum", ""),
                "collection": meta.get("collection", ""),
                "place": meta.get("place", ""),
                "period": meta.get("period", ""),
                "technique": meta.get("technique", ""),
                "material": meta.get("material", ""),
                "external_reference_label": meta.get("external_reference_label", ""),
                "external_reference_url": meta.get("external_reference_url", ""),
                "external_entities": meta.get("external_entities", []),
            }
            for key, value in defaults.items():
                if key not in updated or updated.get(key) in [None, ""]:
                    updated[key] = value
                    if work.get(key) != value:
                        changed = True
            normalized_items.append(updated)
        if changed:
            write_json(WORKS_FILE, normalized_items)
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
            id=make_id("user"),
            pseudonym=generate_pseudonym(),
            created_at=now_iso(),
            profile_familiarity=familiarity,
            profile_documentation=documentation,
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


    def add_work(
        self,
        title: str,
        artist: str,
        year: str,
        description: str,
        image_url: str,
        institutional_tags: List[str],
        museum: str = "",
        collection: str = "",
        place: str = "",
        period: str = "",
        technique: str = "",
        material: str = "",
        external_reference_label: str = "",
        external_reference_url: str = "",
    ) -> Dict[str, Any]:
        items = self.works()
        payload = asdict(WorkRecord(
            id=make_id("work"),
            title=title.strip(),
            artist=artist.strip(),
            year=year.strip(),
            description=description.strip(),
            image_url=image_url.strip(),
            institutional_tags=[t.strip() for t in institutional_tags if t.strip()],
            museum=museum.strip(),
            collection=collection.strip(),
            place=place.strip(),
            period=period.strip(),
            technique=technique.strip(),
            material=material.strip(),
            external_reference_label=external_reference_label.strip(),
            external_reference_url=external_reference_url.strip(),
            created_at=now_iso(),
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
        concept = {
            "id": make_id("concept"),
            "label": label.strip(),
            "category": category.strip(),
            "aliases": [alias.strip() for alias in aliases if alias.strip()],
            "status": "active",
            "source": source,
        }
        items.append(concept)
        self.save_concepts(items)
        return concept

    def submit_tag(self, work_id: str, user_id: str, tag: str, comment: str, ml: "SemanticLearner") -> Dict[str, Any]:
        items = self.tags()
        prediction = ml.predict_entity(tag)
        concept = ml.suggest_concept(tag)
        payload = asdict(TagRecord(
            id=make_id("tag"),
            work_id=work_id,
            user_id=user_id,
            tag=tag.strip(),
            normalized_tag=normalize_text(tag),
            comment=comment.strip(),
            created_at=now_iso(),
            entity_prediction=prediction.get("label", ""),
            entity_confidence=safe_float(prediction.get("confidence", 0.0)),
            concept_id=concept.get("id", "") if concept else "",
            concept_label=concept.get("label", "") if concept else "",
            status="pending",
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

    def add_validation(self, tag_id: str, validator: str, validated_entity: str, validated_concept_id: str, validated_concept_label: str, decision: str, notes: str) -> Dict[str, Any]:
        items = self.validations()
        payload = asdict(ValidationRecord(
            id=make_id("validation"),
            tag_id=tag_id,
            validator=validator,
            validated_entity=validated_entity,
            validated_concept_id=validated_concept_id,
            validated_concept_label=validated_concept_label,
            decision=decision,
            notes=notes,
            created_at=now_iso(),
        ))
        items.append(payload)
        self.save_validations(items)
        return payload

    def add_suggestion(self, tag_id: str, rule_name: str, suggestion_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        items = self.suggestions()
        suggestion = asdict(SuggestionRecord(
            id=make_id("sugg"),
            tag_id=tag_id,
            rule_name=rule_name,
            suggestion_type=suggestion_type,
            payload=payload,
            status="open",
            created_at=now_iso(),
        ))
        items.append(suggestion)
        self.save_suggestions(items)
        return suggestion

    def close_suggestion(self, suggestion_id: str, status: str = "resolved") -> None:
        items = self.suggestions()
        for suggestion in items:
            if suggestion.get("id") == suggestion_id:
                suggestion["status"] = status
                break
        self.save_suggestions(items)


class SemanticLearner:
    def __init__(self, store: JsonStore) -> None:
        self.store = store
        self.entity_vectorizer: Optional[TfidfVectorizer] = None
        self.entity_model: Optional[LogisticRegression] = None
        self.entity_labels: List[str] = []
        self.entity_accuracy: float = 0.0
        self.entity_samples: int = 0
        self.concept_vectorizer: Optional[TfidfVectorizer] = None
        self.concept_matrix = None
        self.concept_rows: List[Dict[str, Any]] = []
        self.train()

    def build_training_corpus(self) -> pd.DataFrame:
        rows: List[Dict[str, str]] = []
        for label, samples in SEED_VOCAB.items():
            for sample in samples:
                rows.append({"text": sample, "label": label, "source": "seed"})
        for work in self.store.works():
            description = work.get("description", "")
            for tag in work.get("institutional_tags", []):
                rows.append({"text": f"{tag} {description}".strip(), "label": "tema", "source": "work"})
        tag_index = {item.get("id"): item for item in self.store.tags()}
        for validation in self.store.validations():
            if validation.get("decision") not in {"approved", "auto-approved", "linked"}:
                continue
            tag_row = tag_index.get(validation.get("tag_id"))
            if not tag_row:
                continue
            entity = validation.get("validated_entity") or tag_row.get("entity_prediction") or "tema"
            rows.append({"text": " ".join([tag_row.get("tag", ""), tag_row.get("comment", "")]).strip(), "label": entity, "source": "validation"})
            if validation.get("validated_concept_label"):
                rows.append({"text": validation.get("validated_concept_label"), "label": entity, "source": "concept"})
        df = pd.DataFrame(rows)
        if df.empty:
            return df
        df = df[df["text"].astype(str).str.strip() != ""]
        return df.reset_index(drop=True)

    def build_concept_matrix(self) -> None:
        concepts = [concept for concept in self.store.concepts() if concept.get("status") != "archived"]
        rows = []
        for concept in concepts:
            alias_text = " ".join(concept.get("aliases", []))
            rows.append({
                "id": concept.get("id", ""),
                "label": concept.get("label", ""),
                "category": concept.get("category", ""),
                "text": f"{concept.get('label', '')} {alias_text} {concept.get('category', '')}".strip(),
            })
        self.concept_rows = rows
        if not rows or not HAS_SKLEARN:
            self.concept_vectorizer = None
            self.concept_matrix = None
            return
        self.concept_vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=1)
        self.concept_matrix = self.concept_vectorizer.fit_transform([row["text"] for row in rows])

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
        best_label, best_score = max(score_map.items(), key=lambda item: item[1])
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
        return {"label": label, "confidence": float(probs[idx]), "proba": {cls: float(prob) for cls, prob in zip(self.entity_model.classes_, probs)}}

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
        rows.sort(key=lambda item: item[1], reverse=True)
        return rows[:top_k]

    def cluster_terms(self, values: Sequence[str], threshold: float = 0.66) -> List[List[str]]:
        unique_values = [value for value in dict.fromkeys([str(v).strip() for v in values if str(v).strip()])]
        if len(unique_values) < 2:
            return []
        if not HAS_SKLEARN:
            return greedy_cluster_terms(unique_values, threshold=threshold)
        vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=1)
        X = vectorizer.fit_transform(unique_values)
        similarity = cosine_similarity(X)
        distance = 1 - similarity
        model = AgglomerativeClustering(metric="precomputed", linkage="average", distance_threshold=max(0.001, 1 - threshold), n_clusters=None)
        labels = model.fit_predict(distance)
        groups = defaultdict(list)
        for term, label in zip(unique_values, labels):
            groups[int(label)].append(term)
        ordered = [sorted(group) for group in groups.values() if len(group) > 1]
        ordered.sort(key=lambda item: (-len(item), item[0]))
        return ordered

    def term_features(self, tag_text: str) -> Dict[str, Any]:
        tokens = tokenize(tag_text)
        prediction = self.predict_entity(tag_text)
        concepts = self.suggest_concepts(tag_text, top_k=3)
        return {
            "normalized": normalize_text(tag_text),
            "token_count": len(tokens),
            "tokens": tokens,
            "entity": prediction.get("label", ""),
            "confidence": prediction.get("confidence", 0.0),
            "concepts": concepts,
        }



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
        work_cols = [c for c in ["id", "title", "artist", "year", "museum", "collection", "place", "period", "technique", "material", "external_reference_label", "external_reference_url"] if c in works.columns]
        tags = tags.merge(
            works[work_cols].rename(
                columns={
                    "id": "work_id",
                    "title": "work_title",
                    "artist": "work_artist",
                    "year": "work_year",
                    "museum": "work_museum",
                    "collection": "work_collection",
                    "place": "work_place",
                    "period": "work_period",
                    "technique": "work_technique",
                    "material": "work_material",
                    "external_reference_label": "work_external_label",
                    "external_reference_url": "work_external_url",
                }
            ),
            on="work_id",
            how="left",
        )
    if not users.empty:
        user_cols = [c for c in ["id", "pseudonym", "profile_familiarity", "profile_documentation"] if c in users.columns]
        tags = tags.merge(users[user_cols].rename(columns={"id": "user_id", "pseudonym": "user_pseudonym"}), on="user_id", how="left")
    if not concepts.empty and "concept_id" in tags.columns:
        tags = tags.merge(
            concepts[[c for c in ["id", "label", "category", "source"] if c in concepts.columns]].rename(
                columns={"id": "concept_id", "label": "concept_resolved_label", "category": "concept_resolved_category", "source": "concept_source"}
            ),
            on="concept_id",
            how="left",
        )
    if not validations.empty:
        latest = validations.sort_values("created_at").groupby("tag_id").tail(1)
        tags = tags.merge(
            latest[[c for c in ["tag_id", "validated_entity", "validated_concept_label", "decision", "notes"] if c in latest.columns]],
            left_on="id",
            right_on="tag_id",
            how="left",
        )
    tags["created_at"] = tags["created_at"].astype(str)
    tags["created_ts"] = pd.to_datetime(tags["created_at"], errors="coerce")
    tags["created_date"] = tags["created_ts"].dt.date.astype(str)
    tags["created_hour"] = tags["created_ts"].dt.hour.fillna(0).astype(int)
    tags["created_weekday"] = tags["created_ts"].dt.day_name().fillna("")
    tags["created_month"] = tags["created_ts"].dt.strftime("%Y-%m").fillna("")
    tags["is_validated"] = tags.get("decision", pd.Series([""] * len(tags))).fillna("").isin(["approved", "auto-approved", "linked"])
    return tags

def build_public_metrics(tags_df: pd.DataFrame, works_df: pd.DataFrame, users_df: pd.DataFrame) -> Dict[str, Any]:
    total_tags = int(len(tags_df)) if not tags_df.empty else 0
    unique_tags = int(tags_df["normalized_tag"].nunique()) if not tags_df.empty else 0
    active_users = int(users_df["id"].nunique()) if not users_df.empty else 0
    tagged_works = int(tags_df["work_id"].nunique()) if not tags_df.empty else 0
    lexical_density = float(unique_tags / total_tags) if total_tags else 0.0
    return {
        "total_tags": total_tags,
        "unique_tags": unique_tags,
        "active_users": active_users,
        "works": int(len(works_df)) if not works_df.empty else 0,
        "tagged_works": tagged_works,
        "lexical_density": lexical_density,
    }



def build_knowledge_graph(store: JsonStore) -> Any:
    works = store.works()
    concepts = {concept.get("id"): concept for concept in store.concepts() if isinstance(concept, dict) and concept.get("id")}
    tags_df = build_tag_dataframe(store)
    users = {}
    for index, user in enumerate(store.users()):
        if not isinstance(user, dict):
            continue
        resolved_id = user.get("id") or user.get("user_id") or f"legacy-user-{index+1}"
        normalized = dict(user)
        normalized["id"] = resolved_id
        users[resolved_id] = normalized

    semantic_links = semantic_tag_links(tags_df["tag"].tolist(), threshold=0.60) if not tags_df.empty else []
    typo_links = typo_candidate_rows(tags_df["tag"].tolist(), threshold=0.80) if not tags_df.empty else []

    if HAS_NETWORKX and nx is not None:
        graph = nx.Graph()
        def add_node(node_id: str, **attrs: Any) -> None:
            if not node_id:
                return
            if not graph.has_node(node_id):
                graph.add_node(node_id, **attrs)

        for work in works:
            meta = resolve_work_metadata(work)
            work_id = work.get("id", "")
            add_node(work_id, kind="work", label=work.get("title", ""), subtitle=work.get("artist", ""))
            artist_node = f"artist::{normalize_text(work.get('artist', ''))}"
            add_node(artist_node, kind="artist", label=work.get("artist", ""), subtitle="autor")
            graph.add_edge(work_id, artist_node, relation="created_by")

            for field, kind, relation in [
                (meta.get("museum", ""), "museum", "held_by"),
                (meta.get("collection", ""), "collection", "belongs_to_collection"),
                (meta.get("place", ""), "place", "located_in"),
                (meta.get("period", ""), "period", "historical_period"),
                (meta.get("technique", ""), "technique", "uses_technique"),
                (meta.get("material", ""), "material", "uses_material"),
            ]:
                if field:
                    node_id = f"{kind}::{normalize_text(field)}"
                    add_node(node_id, kind=kind, label=field, subtitle="metadado museológico")
                    graph.add_edge(work_id, node_id, relation=relation)

            for tag in work.get("institutional_tags", []) or []:
                node_id = f"inst::{normalize_text(tag)}"
                add_node(node_id, kind="institutional_tag", label=tag, subtitle="vocabulário institucional")
                graph.add_edge(work_id, node_id, relation="institutional")

            ext_label = meta.get("external_reference_label", "")
            ext_url = meta.get("external_reference_url", "")
            if ext_label or ext_url:
                ext_node = f"external::{normalize_text(work.get('title', work_id))}"
                add_node(ext_node, kind="external_reference", label=ext_label or "open data", subtitle=ext_url)
                graph.add_edge(work_id, ext_node, relation="external_reference")
            for ext_entity in meta.get("external_entities", []) or []:
                ext_entity_node = f"extentity::{normalize_text(ext_entity)}"
                add_node(ext_entity_node, kind="external_entity", label=ext_entity, subtitle="open data conectado")
                graph.add_edge(work_id, ext_entity_node, relation="contextualized_by")

        for user in users.values():
            add_node(user["id"], kind="user", label=user.get("pseudonym", ""), subtitle=user.get("profile_familiarity", ""))

        for concept_id, concept in concepts.items():
            add_node(concept_id, kind="concept", label=concept.get("label", ""), subtitle=concept.get("category", ""))

        if not tags_df.empty:
            for _, tag in tags_df.iterrows():
                tag_node = tag.get("id", "")
                add_node(tag_node, kind="tag", label=tag.get("tag", ""), subtitle=tag.get("entity_prediction", ""))
                if tag.get("work_id"):
                    graph.add_edge(tag.get("work_id"), tag_node, relation="tagged")
                if tag.get("user_id"):
                    graph.add_edge(tag.get("user_id"), tag_node, relation="created")
                if tag.get("concept_id") and tag.get("concept_id") in concepts:
                    graph.add_edge(tag_node, tag.get("concept_id"), relation="reconciled")
                if tag.get("entity_prediction"):
                    entity_node = f"entity::{normalize_text(tag.get('entity_prediction', ''))}"
                    add_node(entity_node, kind="entity_class", label=tag.get("entity_prediction", ""), subtitle="categoria prevista")
                    graph.add_edge(tag_node, entity_node, relation="classified_as")
                if tag.get("work_id"):
                    work = next((w for w in works if w.get("id") == tag.get("work_id")), None)
                    if work:
                        for inst_tag in work.get("institutional_tags", []) or []:
                            if hybrid_similarity(tag.get("tag", ""), inst_tag) >= 0.58:
                                inst_node = f"inst::{normalize_text(inst_tag)}"
                                add_node(inst_node, kind="institutional_tag", label=inst_tag, subtitle="vocabulário institucional")
                                graph.add_edge(tag_node, inst_node, relation="approaches_institutional_term")

        for row in semantic_links[:120]:
            a = f"surface::{normalize_text(row['tag_a'])}"
            b = f"surface::{normalize_text(row['tag_b'])}"
            add_node(a, kind="tag_surface", label=row["tag_a"], subtitle="surface form")
            add_node(b, kind="tag_surface", label=row["tag_b"], subtitle="surface form")
            graph.add_edge(a, b, relation=row["relation"])
        for row in typo_links[:80]:
            a = f"typo::{normalize_text(row['termo_a'])}"
            b = f"typo::{normalize_text(row['termo_b'])}"
            add_node(a, kind="typo_candidate", label=row["termo_a"], subtitle="variante ortográfica")
            add_node(b, kind="typo_candidate", label=row["termo_b"], subtitle="variante ortográfica")
            graph.add_edge(a, b, relation="possible_spelling_variant")
        return graph

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
        work_id = work.get("id", "")
        add_node(work_id, "work", work.get("title", ""), work.get("artist", ""))
        artist_node = f"artist::{normalize_text(work.get('artist', ''))}"
        add_node(artist_node, "artist", work.get("artist", ""), "autor")
        add_edge(work_id, artist_node, "created_by")
        for field, kind, relation in [
            (meta.get("museum", ""), "museum", "held_by"),
            (meta.get("collection", ""), "collection", "belongs_to_collection"),
            (meta.get("place", ""), "place", "located_in"),
            (meta.get("period", ""), "period", "historical_period"),
            (meta.get("technique", ""), "technique", "uses_technique"),
            (meta.get("material", ""), "material", "uses_material"),
        ]:
            if field:
                node_id = f"{kind}::{normalize_text(field)}"
                add_node(node_id, kind, field, "metadado museológico")
                add_edge(work_id, node_id, relation)
        for tag in work.get("institutional_tags", []) or []:
            node_id = f"inst::{normalize_text(tag)}"
            add_node(node_id, "institutional_tag", tag, "vocabulário institucional")
            add_edge(work_id, node_id, "institutional")
        ext_label = meta.get("external_reference_label", "")
        ext_url = meta.get("external_reference_url", "")
        if ext_label or ext_url:
            ext_node = f"external::{normalize_text(work.get('title', work_id))}"
            add_node(ext_node, "external_reference", ext_label or "open data", ext_url)
            add_edge(work_id, ext_node, "external_reference")
        for ext_entity in meta.get("external_entities", []) or []:
            ext_entity_node = f"extentity::{normalize_text(ext_entity)}"
            add_node(ext_entity_node, "external_entity", ext_entity, "open data conectado")
            add_edge(work_id, ext_entity_node, "contextualized_by")

    for user in users.values():
        add_node(user["id"], "user", user.get("pseudonym", ""), user.get("profile_familiarity", ""))
    for concept_id, concept in concepts.items():
        add_node(concept_id, "concept", concept.get("label", ""), concept.get("category", ""))
    if not tags_df.empty:
        for _, tag in tags_df.iterrows():
            tag_node = tag.get("id", "")
            add_node(tag_node, "tag", tag.get("tag", ""), tag.get("entity_prediction", ""))
            if tag.get("work_id"):
                add_edge(tag.get("work_id"), tag_node, "tagged")
            if tag.get("user_id"):
                add_edge(tag.get("user_id"), tag_node, "created")
            if tag.get("concept_id") and tag.get("concept_id") in concepts:
                add_edge(tag_node, tag.get("concept_id"), "reconciled")
            if tag.get("entity_prediction"):
                entity_node = f"entity::{normalize_text(tag.get('entity_prediction', ''))}"
                add_node(entity_node, "entity_class", tag.get("entity_prediction", ""), "categoria prevista")
                add_edge(tag_node, entity_node, "classified_as")
    for row in semantic_links[:120]:
        a = f"surface::{normalize_text(row['tag_a'])}"
        b = f"surface::{normalize_text(row['tag_b'])}"
        add_node(a, "tag_surface", row["tag_a"], "surface form")
        add_node(b, "tag_surface", row["tag_b"], "surface form")
        add_edge(a, b, row["relation"])
    for row in typo_links[:80]:
        a = f"typo::{normalize_text(row['termo_a'])}"
        b = f"typo::{normalize_text(row['termo_b'])}"
        add_node(a, "typo_candidate", row["termo_a"], "variante ortográfica")
        add_node(b, "typo_candidate", row["termo_b"], "variante ortográfica")
        add_edge(a, b, "possible_spelling_variant")
    return {"nodes": list(node_map.values()), "edges": edges}

def graph_to_plot(graph: Any, max_nodes: int = 120) -> Any:
    if not (HAS_NETWORKX and HAS_PLOTLY and nx is not None and go is not None):
        return None
    sub_nodes = list(graph.nodes())[:max_nodes]
    g = graph.subgraph(sub_nodes).copy()
    if len(g.nodes()) == 0:
        return go.Figure()
    pos = nx.spring_layout(g, seed=42, k=0.9 / math.sqrt(max(len(g.nodes()), 2)))
    edge_x, edge_y = [], []
    for source, target in g.edges():
        x0, y0 = pos[source]
        x1, y1 = pos[target]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])
    edge_trace = go.Scatter(x=edge_x, y=edge_y, mode="lines", line=dict(width=0.7, color="rgba(80,80,80,0.35)"), hoverinfo="none")
    kind_style = {"work": {"symbol": "square", "size": 18}, "tag": {"symbol": "circle", "size": 11}, "user": {"symbol": "diamond", "size": 14}, "concept": {"symbol": "hexagon", "size": 16}, "institutional_tag": {"symbol": "x", "size": 12}}
    xs, ys, texts, symbols, sizes = [], [], [], [], []
    for node, attrs in g.nodes(data=True):
        x, y = pos[node]
        xs.append(x)
        ys.append(y)
        texts.append(f"{attrs.get('label', node)}<br>{attrs.get('kind', '')}<br>{attrs.get('subtitle', '')}")
        style = kind_style.get(attrs.get("kind"), {"symbol": "circle", "size": 10})
        symbols.append(style["symbol"])
        sizes.append(style["size"])
    node_trace = go.Scatter(
        x=xs, y=ys, text=texts, hovertemplate="%{text}<extra></extra>", mode="markers",
        marker=dict(size=sizes, symbol=symbols, color="rgba(120,120,120,0.82)", line=dict(color="rgba(255,255,255,0.72)", width=1.1)),
    )
    fig = go.Figure(data=[edge_trace, node_trace])
    fig.update_layout(height=650, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=0, r=0, t=0, b=0), xaxis=dict(visible=False), yaxis=dict(visible=False))
    return fig


def generate_semantic_report(store: JsonStore, ml: SemanticLearner) -> Dict[str, Any]:
    tags_df = build_tag_dataframe(store)
    if tags_df.empty:
        return {}
    top_tags = tags_df["normalized_tag"].value_counts().head(15).to_dict()
    grouped = tags_df["entity_prediction"].replace("", "não previsto").fillna("não previsto").value_counts().to_dict() if "entity_prediction" in tags_df.columns else {}
    clusters = ml.cluster_terms(tags_df["tag"].dropna().astype(str).tolist(), threshold=0.66)
    report = {
        "id": make_id("report"),
        "created_at": now_iso(),
        "top_tags": top_tags,
        "entity_distribution": grouped,
        "cluster_count": len(clusters),
        "clusters_preview": clusters[:12],
        "total_tags": int(len(tags_df)),
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
                created.append(store.add_suggestion(tag_id, "auto_classify", "entity", {"entity": prediction.get("label"), "confidence": round(prediction.get("confidence", 0.0), 4)}))
                existing_keys.add(key)
        concept = ml.suggest_concept(text)
        if concept and concept.get("similarity", 0.0) >= settings.get("min_similarity_auto_link", 0.88):
            key = (tag_id, "auto_link_concept", "concept")
            if key not in existing_keys and tag.get("concept_id") != concept.get("id"):
                created.append(store.add_suggestion(tag_id, "auto_link_concept", "concept", {"concept_id": concept.get("id"), "concept_label": concept.get("label"), "category": concept.get("category"), "similarity": round(concept.get("similarity", 0.0), 4)}))
                existing_keys.add(key)
        if settings.get("auto_flag_ambiguity") and tag.get("entity_prediction") and tag.get("concept_id") and tag.get("concept_id") in concept_by_id:
            linked_concept = concept_by_id[tag.get("concept_id")]
            if linked_concept.get("category") and tag.get("entity_prediction") != linked_concept.get("category") and safe_float(tag.get("entity_confidence", 0.0)) >= 0.60:
                key = (tag_id, "auto_flag_ambiguity", "ambiguity")
                if key not in existing_keys:
                    created.append(store.add_suggestion(tag_id, "auto_flag_ambiguity", "ambiguity", {"predicted": tag.get("entity_prediction"), "concept_category": linked_concept.get("category"), "reason": "divergência entre categoria prevista e conceito reconciliado"}))
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
            created.append(store.add_suggestion(base_tag.get("id"), "candidate_concept", "concept_candidate", {"label": text, "category": prediction.get("label", "tema"), "frequency": int(count)}))
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
    html = f"<div class='topbar'><div><div class='brand-title'>{APP_TITLE}</div><div class='brand-subtitle'>liquid glass semantic interface</div></div><div></div></div>"
    st.markdown(html, unsafe_allow_html=True)



def hero_panel(store: JsonStore) -> None:
    html = f"""
    <div class="hero-panel">
        <div class="hero-grid" style="grid-template-columns: 1fr;">
            <div>
                <div class="hero-kicker">camada semântica participativa com aprendizado contínuo</div>
                <div class="hero-title">folksonomia</div>
                <div class="hero-copy">
                    Interface translúcida com foco em documentação museológica, NLU aplicada a tags livres,
                    reconciliação conceitual, grafo de conhecimento, metadados museológicos, ligações semânticas
                    e análise temporal supervisionada.
                </div>
            </div>
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

def open_panel(title: str, subtitle: str) -> None:
    st.markdown(f"<div class='panel'><div class='panel-title'>{title}</div><div class='panel-subtitle'>{subtitle}</div>", unsafe_allow_html=True)


def close_panel() -> None:
    st.markdown("</div>", unsafe_allow_html=True)



def render_public_overview(store: JsonStore, ml: SemanticLearner) -> None:
    tags_df = build_tag_dataframe(store)
    works_df = to_dataframe(store.works())
    users_df = to_dataframe(store.users())
    metrics = build_public_metrics(tags_df, works_df, users_df)
    open_panel("camada pública", "visão geral da participação, da diversidade lexical e da estrutura semântica ativa.")
    html = f"""
    <div class="metric-strip">
        <div class="metric-card"><div class="metric-caption">obras disponíveis</div><div class="metric-number">{metrics.get('works', 0)}</div><div class="metric-note">base inicial de objetos</div></div>
        <div class="metric-card"><div class="metric-caption">obras tagueadas</div><div class="metric-number">{metrics.get('tagged_works', 0)}</div><div class="metric-note">objetos com linguagem social</div></div>
        <div class="metric-card"><div class="metric-caption">amostras do modelo</div><div class="metric-number">{store.model_state().get('sample_count', 0)}</div><div class="metric-note">treino incremental</div></div>
        <div class="metric-card"><div class="metric-caption">acurácia estimada</div><div class="metric-number">{store.model_state().get('accuracy', 0.0):.2f}</div><div class="metric-note">classificação de entidades</div></div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)
    c1, c2 = st.columns([1.1, 0.9])
    with c1:
        if not tags_df.empty:
            top_tags = tags_df["tag"].value_counts().head(15).rename_axis("tag").reset_index(name="frequência")
            render_bar_chart_df(top_tags, x="frequência", y="tag", orientation="h", height=430)
        else:
            st.info("ainda não existem tags suficientes para visualizar tendências.")
    with c2:
        recent = store.reports()[-5:][::-1]
        if recent:
            for report in recent:
                chips = "".join([f"<span class='tag-chip'>{' · '.join(cluster[:3])}</span>" for cluster in report.get("clusters_preview", [])[:4]])
                st.markdown(f"<div class='story-card'><div class='story-title'>relatório semântico</div><div class='story-copy'>gerado em {report.get('created_at')}<br>total de tags {report.get('total_tags',0)} · vocabulário único {report.get('unique_tags',0)}</div><div style='margin-top:0.6rem'>{chips}</div></div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='story-card'><div class='story-title'>relatórios semânticos</div><div class='story-copy'>a automação criará relatórios quando houver volume suficiente de linguagem social.</div></div>", unsafe_allow_html=True)
    close_panel()



def render_public_explore(store: JsonStore, ml: SemanticLearner) -> None:
    user = store.find_user(st.session_state.get("session_user_id", ""))
    works = store.works()
    open_panel("explorar obras", "clique na imagem para abrir um campo compacto de marcação. a interface pública não exibe metadados analíticos nem informações curatoriais detalhadas durante a tagueação.")
    if not user or not works:
        close_panel()
        return

    works = works[:3]
    cols = st.columns(3 if len(works) >= 3 else len(works))
    for idx, work in enumerate(works):
        with cols[idx % len(cols)]:
            st.markdown("<div class='work-card'>", unsafe_allow_html=True)
            st.image(work.get("image_url"), use_container_width=True)
            if st.button("marcar esta imagem", key=f"public-open-{work.get('id')}", use_container_width=True):
                st.session_state["selected_work_id"] = work.get("id")
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    selected_id = st.session_state.get("selected_work_id", "")
    if selected_id:
        selected = next((w for w in works if w.get("id") == selected_id), None)
        if selected:
            related = build_tag_dataframe(store)
            mine = related[(related["work_id"] == selected_id) & (related["user_id"] == user.get("id"))] if not related.empty else pd.DataFrame()
            st.markdown("<div class='soft-line'></div>", unsafe_allow_html=True)
            c1, c2 = st.columns([0.9, 1.1])
            with c1:
                st.markdown("<div class='tag-compact-box compact-image-box'>", unsafe_allow_html=True)
                st.image(selected.get("image_url"), use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)
            with c2:
                st.markdown("<div class='tag-compact-box'>", unsafe_allow_html=True)
                with st.form(f"tag-form-{selected_id}", clear_on_submit=True):
                    tag_value = st.text_input("sua tag", placeholder="escreva uma palavra ou pequena expressão")
                    submitted = st.form_submit_button("registrar tag", use_container_width=True)
                    if submitted:
                        if not tag_value.strip():
                            st.warning("escreva uma tag antes de registrar.")
                        else:
                            store.submit_tag(selected.get("id"), user.get("id"), tag_value, "", ml)
                            run_automation_engine(store, ml)
                            st.success("tag registrada.")
                            st.rerun()
                if not mine.empty:
                    mine_counts = mine["tag"].value_counts().reset_index()
                    mine_counts.columns = ["tag", "frequência"]
                    st.markdown("<div class='tag-mini-note'>suas tags nesta imagem</div>", unsafe_allow_html=True)
                    st.markdown("<div class='tag-preview-wrap'>" + "".join([f"<span class='tag-chip'>{row['tag']} {int(row['frequência'])}</span>" for _, row in mine_counts.iterrows()]) + "</div>", unsafe_allow_html=True)
                else:
                    st.markdown("<div class='tag-mini-note'>suas tags ainda não apareceram aqui.</div>", unsafe_allow_html=True)
                if st.button("fechar imagem", key=f"close-public-{selected_id}", use_container_width=True):
                    st.session_state["selected_work_id"] = ""
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)
    close_panel()

def render_work_detail(store: JsonStore, ml: SemanticLearner, work_id: str) -> None:
    work = next((w for w in store.works() if w.get("id") == work_id), None)
    if not work:
        return
    tags_df = build_tag_dataframe(store)
    related_df = tags_df[tags_df["work_id"] == work_id] if not tags_df.empty else pd.DataFrame()
    open_panel("obra em foco", f"{work.get('title')} · {work.get('artist')} · {work.get('year')}")
    c1, c2 = st.columns(2)
    with c1:
        st.image(work.get("image_url"), use_container_width=True)
        st.markdown(f"<div class='story-card'><div class='story-title'>descrição</div><div class='story-copy'>{work.get('description')}</div></div>", unsafe_allow_html=True)
    with c2:
        st.markdown("<div class='story-card'><div class='story-title'>eixos institucionais</div><div style='margin-top:0.5rem'>" + "".join([f"<span class='tag-chip'>{tag}</span>" for tag in work.get("institutional_tags", [])]) + "</div></div>", unsafe_allow_html=True)
        if not related_df.empty:
            counts = related_df["tag"].value_counts().head(12)
            st.markdown("<div class='story-card'><div class='story-title'>top tags sociais</div><div style='margin-top:0.5rem'>" + "".join([f"<span class='tag-chip'>{tag} {count}</span>" for tag, count in counts.items()]) + "</div></div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='story-card'><div class='story-title'>camada social</div><div class='story-copy'>esta obra ainda não recebeu marcações públicas.</div></div>", unsafe_allow_html=True)
    if not related_df.empty:
        st.markdown("<div class='soft-line'></div>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            clusters = ml.cluster_terms(related_df["tag"].astype(str).tolist(), threshold=0.66)
            st.markdown("agrupamentos sugeridos")
            if clusters:
                for cluster in clusters[:10]:
                    st.markdown("".join([f"<span class='tag-chip'>{term}</span>" for term in cluster]), unsafe_allow_html=True)
            else:
                st.caption("sem agrupamentos robustos ainda.")
        with c2:
            entity_counts = related_df["entity_prediction"].replace("", "não previsto").fillna("não previsto").value_counts().rename_axis("categoria").reset_index(name="frequência")
            render_pie_chart_df(entity_counts, names="categoria", values="frequência", height=320)
    if st.button("fechar painel da obra", key="close-work-panel", use_container_width=True):
        st.session_state["selected_work_id"] = ""
        st.rerun()
    close_panel()


def render_public_contribute(store: JsonStore, ml: SemanticLearner) -> None:
    open_panel("contribuir", "a marcação pública agora acontece diretamente em explorar obras, com a imagem limpa e sem dados textuais que possam influenciar o participante.")
    st.markdown("<div class='story-card'><div class='story-title'>marcação deslocada para a galeria</div><div class='story-copy'>clique em explorar obras para abrir cada imagem e registrar a tag em um painel translúcido. toda a análise semântica profunda foi deslocada para a área administrativa.</div></div>", unsafe_allow_html=True)
    close_panel()


def render_public_semantics(store: JsonStore, ml: SemanticLearner) -> None:
    tags_df = build_tag_dataframe(store)
    open_panel("descoberta semântica", "busca conceitual, leitura de entidades, variantes, relações e obras próximas.")
    query = st.text_input("termo de partida", placeholder="experimente mulher, barroco, ouro, trabalho, rio de janeiro")
    if query.strip():
        features = ml.term_features(query)
        st.markdown(f"<div class='suggestion-card'><div class='suggestion-title'>classificação prevista</div><div class='suggestion-meta'>categoria {features.get('entity')} · confiança {features.get('confidence', 0.0):.2f}<br>tokens {', '.join(features.get('tokens', [])) or 'nenhum'}</div></div>", unsafe_allow_html=True)
        for concept in features.get("concepts", []):
            st.markdown(f"<span class='tag-chip'>{concept.get('label')} · {concept.get('category')} · similaridade {concept.get('similarity', 0.0):.2f}</span>", unsafe_allow_html=True)
        if not tags_df.empty:
            related = ml.related_tags(tags_df["tag"].astype(str).tolist(), query, top_k=12)
            st.markdown("<div class='soft-line'></div>", unsafe_allow_html=True)
            st.markdown("variantes e aproximações")
            for term, score in related:
                st.markdown(f"<span class='tag-chip'>{term} · {score:.2f}</span>", unsafe_allow_html=True)
            tag_matches = tags_df[tags_df["tag"].astype(str).str.contains(query, case=False, na=False)]
            if not tag_matches.empty:
                st.markdown("<div class='soft-line'></div>", unsafe_allow_html=True)
                st.markdown("obras relacionadas")
                for work_id in tag_matches["work_id"].unique().tolist()[:10]:
                    work = next((w for w in store.works() if w.get("id") == work_id), None)
                    if work:
                        st.markdown(f"<div class='queue-card'><div class='story-title'>{work.get('title')}</div><div class='queue-text'>{work.get('artist')} · {work.get('year')}<br>{first_sentence(work.get('description'))}</div></div>", unsafe_allow_html=True)
    else:
        st.caption("use um termo para ativar a camada de interpretação semântica.")
    close_panel()


def render_public_history(store: JsonStore) -> None:
    user = store.find_user(st.session_state.get("session_user_id", ""))
    open_panel("meu histórico", "trajetória individual de participação, riqueza lexical e automações abertas.")
    if not user:
        st.info("sem perfil ativo nesta sessão.")
        close_panel()
        return
    tags_df = build_tag_dataframe(store)
    mine = tags_df[tags_df["user_id"] == user.get("id")] if not tags_df.empty else pd.DataFrame()
    if mine.empty:
        st.info("você ainda não registrou tags nesta sessão.")
        close_panel()
        return
    total = int(len(mine))
    unique = int(mine["normalized_tag"].nunique())
    ttr = unique / total if total else 0.0
    html = f"""
    <div class="metric-strip">
        <div class="metric-card"><div class="metric-caption">perfil</div><div class="metric-number">{user.get('pseudonym')}</div><div class="metric-note">anonimização local</div></div>
        <div class="metric-card"><div class="metric-caption">tags criadas</div><div class="metric-number">{total}</div><div class="metric-note">contribuições da sessão</div></div>
        <div class="metric-card"><div class="metric-caption">vocabulário único</div><div class="metric-number">{unique}</div><div class="metric-note">variedade lexical</div></div>
        <div class="metric-card"><div class="metric-caption">ttr</div><div class="metric-number">{ttr:.2f}</div><div class="metric-note">unique over total</div></div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)
    top = mine["tag"].value_counts().head(20).rename_axis("tag").reset_index(name="frequência")
    render_bar_chart_df(top, x="frequência", y="tag", orientation="h", height=400)
    st.dataframe(mine[[c for c in ["tag", "comment", "work_title", "entity_prediction", "entity_confidence", "concept_label", "created_at"] if c in mine.columns]], use_container_width=True, hide_index=True)
    close_panel()



def render_admin_login(store: JsonStore) -> None:
    open_panel("área administrativa", "login para validação, treinamento do modelo, análise temporal, grafo de conhecimento e gestão de conceitos.")
    with st.form("admin-login"):
        username = st.text_input("login administrativo")
        password = st.text_input("senha administrativa", type="password")
        submitted = st.form_submit_button("entrar na administração", use_container_width=True)
        if submitted:
            if store.admin_ok(username, password):
                st.session_state["admin_authenticated"] = True
                st.success("acesso administrativo liberado.")
                st.rerun()
            else:
                st.error("credenciais inválidas.")
    close_panel()

def render_admin_dashboard(store: JsonStore, ml: SemanticLearner) -> None:
    tags_df = build_tag_dataframe(store)
    users_df = to_dataframe(store.users())
    concepts_df = to_dataframe(store.concepts())
    works_df = to_dataframe(store.works())
    open_panel("painel administrativo", "síntese da camada semântica, vocabulário social, metadados museológicos e reconciliação inspirada na lógica de grafos e supervisão curatorial.")
    total_tags = int(len(tags_df)) if not tags_df.empty else 0
    unique_tags = int(tags_df["normalized_tag"].nunique()) if not tags_df.empty else 0
    html = f"""
    <div class="metric-strip">
        <div class="metric-card"><div class="metric-caption">usuários</div><div class="metric-number">{int(users_df['id'].nunique()) if not users_df.empty else 0}</div><div class="metric-note">perfis criados</div></div>
        <div class="metric-card"><div class="metric-caption">obras</div><div class="metric-number">{int(len(works_df)) if not works_df.empty else 0}</div><div class="metric-note">base museológica</div></div>
        <div class="metric-card"><div class="metric-caption">vocabulário único</div><div class="metric-number">{unique_tags}</div><div class="metric-note">formas sociais distintas</div></div>
        <div class="metric-card"><div class="metric-caption">amostras de treino</div><div class="metric-number">{ml.entity_samples}</div><div class="metric-note">seed mais validações</div></div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)
    c1, c2 = st.columns([1.08, 0.92])
    with c1:
        if not tags_df.empty:
            entity_counts = tags_df["entity_prediction"].replace("", "não previsto").fillna("não previsto").value_counts().rename_axis("categoria").reset_index(name="frequência")
            render_bar_chart_df(entity_counts, x="categoria", y="frequência", height=360)
            st.markdown("<div class='story-card'><div class='story-title'>leitura semântica do vocabulário</div><div class='story-copy'>o modelo cruza tags livres, validações e descrições das obras para sugerir categorias de entidade. a marcação social permanece livre, mas ganha uma camada interpretativa acima dela.</div></div>", unsafe_allow_html=True)
        else:
            st.info("ainda não há tags para sintetizar a camada semântica.")
    with c2:
        validations_df = to_dataframe(store.validations())
        open_count = int(len(to_dataframe(store.suggestions())[lambda df: df["status"] == "open"])) if len(store.suggestions()) else 0
        st.markdown(f"<div class='story-card'><div class='story-title'>curadoria documental</div><div class='story-copy'>conceitos ativos {len(concepts_df)}<br>validações registradas {len(validations_df)}<br>sugestões em aberto {open_count}<br>acurácia estimada {ml.entity_accuracy:.2f}</div></div>", unsafe_allow_html=True)
        if not works_df.empty:
            metadata_filled = {}
            for column in ["museum", "collection", "place", "period", "technique", "material"]:
                metadata_filled[column] = int(works_df[column].fillna("").astype(str).str.strip().ne("").sum()) if column in works_df.columns else 0
            meta_df = pd.DataFrame({"metadado": list(metadata_filled.keys()), "obras preenchidas": list(metadata_filled.values())})
            render_bar_chart_df(meta_df, x="metadado", y="obras preenchidas", height=320)
    if not tags_df.empty:
        st.markdown("<div class='soft-line'></div>", unsafe_allow_html=True)
        c3, c4 = st.columns(2)
        with c3:
            top_tags = tags_df["tag"].value_counts().head(12).rename_axis("tag").reset_index(name="frequência")
            st.markdown("<div class='story-card'><div class='story-title'>núcleo lexical</div><div class='story-copy'>top termos que estruturam a leitura pública do conjunto.</div></div>", unsafe_allow_html=True)
            render_bar_chart_df(top_tags, x="tag", y="frequência", height=320)
        with c4:
            typo_rows = pd.DataFrame(typo_candidate_rows(tags_df["tag"].tolist(), threshold=0.80))
            if not typo_rows.empty:
                st.markdown("<div class='story-card'><div class='story-title'>variações ortográficas e quase duplicatas</div><div class='story-copy'>pares com proximidade formal alta para revisão administrativa.</div></div>", unsafe_allow_html=True)
                st.dataframe(typo_rows.head(12), use_container_width=True, hide_index=True)
            else:
                st.markdown("<div class='story-card'><div class='story-title'>variações ortográficas</div><div class='story-copy'>a base ainda não apresenta pares robustos de possível erro ortográfico.</div></div>", unsafe_allow_html=True)
    close_panel()

def render_admin_validation(store: JsonStore, ml: SemanticLearner) -> None:
    tags_df = build_tag_dataframe(store)
    suggestions_df = to_dataframe(store.suggestions())
    concepts = store.concepts()
    concept_options = {f"{c.get('label')} · {c.get('category')}": c for c in concepts}
    open_panel("validação e supervisão", "fila administrativa para aprovar entidades, ligar conceitos e alimentar o aprendizado do modelo.")
    if tags_df.empty:
        st.info("não há tags registradas.")
        close_panel()
        return
    subset = tags_df.sort_values("created_at", ascending=False).head(20)
    open_suggestions = suggestions_df[suggestions_df["status"] == "open"] if not suggestions_df.empty else pd.DataFrame()
    for _, row in subset.iterrows():
        related_suggestions = open_suggestions[open_suggestions["tag_id"] == row.get("id")] if not open_suggestions.empty else pd.DataFrame()
        st.markdown(f"<div class='queue-card'><div class='story-title'>{row.get('tag')} · {row.get('work_title', '')}</div><div class='queue-text'>comentário {row.get('comment', '') or 'sem comentário'}<br>previsão {row.get('entity_prediction', '')} · confiança {safe_float(row.get('entity_confidence', 0.0)):.2f}<br>conceito atual {row.get('concept_label', '') or 'não ligado'}</div></div>", unsafe_allow_html=True)
        if not related_suggestions.empty:
            for _, srow in related_suggestions.iterrows():
                st.markdown(f"<div class='suggestion-card'><div class='suggestion-title'>{srow.get('rule_name')}</div><div class='suggestion-meta'>{json.dumps(srow.get('payload', {}), ensure_ascii=False)}</div></div>", unsafe_allow_html=True)
        with st.form(f"validate-{row.get('id')}"):
            c1, c2 = st.columns(2)
            with c1:
                default_entity = row.get("entity_prediction") if row.get("entity_prediction") in ENTITY_LABELS else "tema"
                entity_choice = st.selectbox("categoria validada", ENTITY_LABELS, index=ENTITY_LABELS.index(default_entity), key=f"ent-{row.get('id')}")
                concept_choice = st.selectbox("conceito reconciliado", ["nenhum"] + list(concept_options.keys()), key=f"con-{row.get('id')}")
            with c2:
                decision = st.selectbox("decisão", ["approved", "linked", "rejected"], key=f"dec-{row.get('id')}")
                notes = st.text_area("notas curatoriais", height=90, key=f"notes-{row.get('id')}")
            submitted = st.form_submit_button("registrar validação")
            if submitted:
                concept_id = ""
                concept_label = ""
                if concept_choice != "nenhum":
                    concept_payload = concept_options[concept_choice]
                    concept_id = concept_payload.get("id", "")
                    concept_label = concept_payload.get("label", "")
                store.add_validation(row.get("id"), "admin", entity_choice, concept_id, concept_label, decision, notes)
                updates = {"status": "validated" if decision != "rejected" else "rejected", "entity_prediction": entity_choice, "entity_confidence": 1.0}
                if concept_id:
                    updates["concept_id"] = concept_id
                    updates["concept_label"] = concept_label
                store.update_tag(row.get("id"), updates)
                if not related_suggestions.empty:
                    for _, srow in related_suggestions.iterrows():
                        store.close_suggestion(srow.get("id"), status="resolved")
                ml.train()
                st.success("validação registrada e modelo atualizado.")
                st.rerun()
    close_panel()


def render_admin_concepts(store: JsonStore, ml: SemanticLearner) -> None:
    concepts_df = to_dataframe(store.concepts())
    open_panel("conceitos e ontologia mínima", "micro-ontologia de partida com categorias, aliases, origem e reconciliação manual.")
    t1, t2 = st.tabs(["listar conceitos", "criar conceito"])
    with t1:
        if concepts_df.empty:
            st.info("sem conceitos cadastrados.")
        else:
            search = st.text_input("buscar conceito", key="concept-search")
            view = concepts_df.copy()
            if search.strip():
                mask = view["label"].astype(str).str.contains(search, case=False, na=False) | view["category"].astype(str).str.contains(search, case=False, na=False)
                view = view[mask]
            st.dataframe(view[[c for c in ["label", "category", "aliases", "status", "source"] if c in view.columns]], use_container_width=True, hide_index=True)
    with t2:
        with st.form("create-concept"):
            c1, c2 = st.columns(2)
            with c1:
                label = st.text_input("rótulo do conceito")
                category = st.selectbox("categoria", ENTITY_LABELS)
            with c2:
                aliases = st.text_input("aliases separados por vírgula")
                source = st.selectbox("origem", ["manual", "candidate", "imported"])
            submitted = st.form_submit_button("criar conceito")
            if submitted:
                if not label.strip():
                    st.warning("escreva um rótulo para criar o conceito.")
                else:
                    store.add_concept(label, category, [part.strip() for part in aliases.split(",") if part.strip()], source)
                    ml.train()
                    st.success("conceito criado e camada semântica atualizada.")
                    st.rerun()
    close_panel()


def render_admin_ml(store: JsonStore, ml: SemanticLearner) -> None:
    model_info = store.model_state()
    open_panel("aprendizado de máquina", "modelo real de classificação de entidades com amostras seed, validações e re-treinamento incremental.")
    html = f"""
    <div class="metric-strip">
        <div class="metric-card"><div class="metric-caption">último treino</div><div class="metric-number">{model_info.get('last_trained_at', '') or 'agora'}</div><div class="metric-note">estado persistido</div></div>
        <div class="metric-card"><div class="metric-caption">amostras</div><div class="metric-number">{model_info.get('sample_count', 0)}</div><div class="metric-note">vocabulário e validações</div></div>
        <div class="metric-card"><div class="metric-caption">acurácia</div><div class="metric-number">{model_info.get('accuracy', 0.0):.2f}</div><div class="metric-note">estimativa offline</div></div>
        <div class="metric-card"><div class="metric-caption">classes</div><div class="metric-number">{len(ml.entity_labels)}</div><div class="metric-note">tipos semânticos</div></div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)
    c1, c2 = st.columns([1.0, 1.0])
    with c1:
        query = st.text_input("teste rápido do modelo", placeholder="escreva um termo para prever a categoria")
        if query.strip():
            pred = ml.predict_entity(query)
            st.markdown(f"<div class='suggestion-card'><div class='suggestion-title'>previsão</div><div class='suggestion-meta'>categoria {pred.get('label')} · confiança {pred.get('confidence', 0.0):.2f}</div></div>", unsafe_allow_html=True)
            for concept in ml.suggest_concepts(query, 5):
                st.markdown(f"<span class='tag-chip'>{concept.get('label')} · {concept.get('category')} · {concept.get('similarity', 0.0):.2f}</span>", unsafe_allow_html=True)
    with c2:
        if st.button("re-treinar modelo agora", use_container_width=True):
            ml.train()
            st.success("modelo re-treinado com a base atual.")
            st.rerun()
        st.markdown("<div class='story-card'><div class='story-title'>como o modelo aprende</div><div class='story-copy'>amostras seed alimentam o arranque inicial. Cada validação administrativa volta para o corpus de treino, alterando o comportamento do classificador nas próximas previsões.</div></div>", unsafe_allow_html=True)
    close_panel()



def render_admin_automation(store: JsonStore, ml: SemanticLearner) -> None:
    tags_df = build_tag_dataframe(store)
    works_df = to_dataframe(store.works())
    open_panel("análise temporal", "ritmo das marcações, recorrências por obra, distribuição horária, ligações entre tags e indícios de erro ortográfico ao longo do tempo.")
    if tags_df.empty:
        st.info("a análise temporal será exibida quando houver tags registradas.")
        close_panel()
        return

    tags_df["created_ts"] = pd.to_datetime(tags_df["created_at"], errors="coerce")
    tags_df = tags_df.sort_values("created_ts")
    daily = tags_df.groupby("created_date").agg(tags=("id", "count"), vocabulário=("normalized_tag", "nunique"), participantes=("user_id", "nunique")).reset_index()
    monthly = tags_df.groupby("created_month").agg(tags=("id", "count"), vocabulário=("normalized_tag", "nunique")).reset_index()
    hourly = tags_df.groupby("created_hour").agg(tags=("id", "count")).reset_index()
    weekday_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    weekday_map = {"Monday": "Seg", "Tuesday": "Ter", "Wednesday": "Qua", "Thursday": "Qui", "Friday": "Sex", "Saturday": "Sáb", "Sunday": "Dom"}
    weekday = tags_df.groupby("created_weekday").agg(tags=("id", "count")).reset_index()
    if not weekday.empty:
        weekday["sort"] = weekday["created_weekday"].map(lambda value: weekday_order.index(value) if value in weekday_order else 99)
        weekday = weekday.sort_values("sort")
        weekday["dia"] = weekday["created_weekday"].map(lambda value: weekday_map.get(value, value))
    work_time = tags_df.groupby("work_title").agg(tags=("id", "count"), vocabulário=("normalized_tag", "nunique")).reset_index().sort_values("tags", ascending=False)
    cluster_rows = semantic_tag_links(tags_df["tag"].tolist(), threshold=0.60)
    typo_rows = typo_candidate_rows(tags_df["tag"].tolist(), threshold=0.80)

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(f"<div class='metric-card'><div class='metric-caption'>dias ativos</div><div class='metric-number'>{daily['created_date'].nunique()}</div><div class='metric-note'>com registros</div></div>", unsafe_allow_html=True)
    with c2: st.markdown(f"<div class='metric-card'><div class='metric-caption'>pico diário</div><div class='metric-number'>{int(daily['tags'].max())}</div><div class='metric-note'>tags no dia mais intenso</div></div>", unsafe_allow_html=True)
    with c3: st.markdown(f"<div class='metric-card'><div class='metric-caption'>média diária</div><div class='metric-number'>{daily['tags'].mean():.1f}</div><div class='metric-note'>tags por dia</div></div>", unsafe_allow_html=True)
    with c4: st.markdown(f"<div class='metric-card'><div class='metric-caption'>ligações semânticas</div><div class='metric-number'>{len(cluster_rows)}</div><div class='metric-note'>pares com campo comum</div></div>", unsafe_allow_html=True)

    st.markdown("<div class='soft-line'></div>", unsafe_allow_html=True)
    t1, t2, t3, t4 = st.tabs(["séries temporais", "obras no tempo", "ligações e ortografia", "tabelas"])

    with t1:
        st.markdown("<div class='story-card'><div class='story-title'>produção temporal de tags</div><div class='story-copy'>a curva diária permite observar aceleração, retração e estabilidade do vocabulário social. no espírito do modelo semântico do Prado, o tempo passa a ser uma dimensão de leitura documental.</div></div>", unsafe_allow_html=True)
        if HAS_PLOTLY:
            fig = go.Figure()
            fig.add_scatter(x=daily["created_date"], y=daily["tags"], mode="lines+markers", name="tags")
            fig.add_scatter(x=daily["created_date"], y=daily["vocabulário"], mode="lines+markers", name="vocabulário")
            fig.update_layout(height=360, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=10, r=10, t=20, b=10))
            safe_plotly_chart(fig, use_container_width=True)
        else:
            st.line_chart(daily.set_index("created_date")[["tags", "vocabulário"]])
        c1, c2 = st.columns(2)
        with c1:
            render_bar_chart_df(hourly, x="created_hour", y="tags", height=300)
        with c2:
            if not weekday.empty:
                render_bar_chart_df(weekday[["dia", "tags"]], x="dia", y="tags", height=300)
            else:
                st.info("sem dados suficientes por dia da semana.")

    with t2:
        st.markdown("<div class='story-card'><div class='story-title'>obras e densidade temporal</div><div class='story-copy'>esta leitura cruza frequência de marcação e variedade lexical por obra, articulando a camada social às unidades documentais do museu.</div></div>", unsafe_allow_html=True)
        render_bar_chart_df(work_time.head(12), x="work_title", y="tags", height=320)
        if not monthly.empty:
            render_bar_chart_df(monthly, x="created_month", y="tags", height=320)
        dense_df = tags_df.groupby(["work_title", "created_month"]).agg(tags=("id", "count")).reset_index()
        if not dense_df.empty:
            pivot = dense_df.pivot(index="created_month", columns="work_title", values="tags").fillna(0)
            st.dataframe(pivot, use_container_width=True)

    with t3:
        c1, c2 = st.columns(2)
        with c1:
            if cluster_rows:
                st.markdown("<div class='story-card'><div class='story-title'>tags ligadas por eixo comum</div><div class='story-copy'>pares e aproximações em que o sistema detecta vizinhança semântica, coesão lexical ou aproximação entre vocabulário social e institucional.</div></div>", unsafe_allow_html=True)
                st.dataframe(pd.DataFrame(cluster_rows).head(25), use_container_width=True, hide_index=True)
            else:
                st.info("ainda não há ligações semânticas suficientes.")
        with c2:
            if typo_rows:
                st.markdown("<div class='story-card'><div class='story-title'>erros ortográficos e variantes</div><div class='story-copy'>pareamentos para revisão documental, úteis para desambiguação e consolidação de conceitos.</div></div>", unsafe_allow_html=True)
                st.dataframe(pd.DataFrame(typo_rows).head(25), use_container_width=True, hide_index=True)
            else:
                st.info("não foram encontrados pares fortes de variante ortográfica.")

    with t4:
        recent = tags_df[[c for c in ["created_at", "tag", "work_title", "entity_prediction", "concept_label", "work_museum", "work_period"] if c in tags_df.columns]].sort_values("created_at", ascending=False)
        st.dataframe(recent, use_container_width=True, hide_index=True)
    close_panel()


def render_admin_graph(store: JsonStore) -> None:
    open_panel("grafo de conhecimento", "rede que conecta obras, artistas, metadados museológicos, vocabulário institucional, tags livres, conceitos reconciliados e referências externas.")
    graph = build_knowledge_graph(store)
    tags_df = build_tag_dataframe(store)
    works_df = to_dataframe(store.works())
    typo_df = pd.DataFrame(typo_candidate_rows(tags_df["tag"].tolist(), threshold=0.80)) if not tags_df.empty else pd.DataFrame()
    semantic_df = pd.DataFrame(semantic_tag_links(tags_df["tag"].tolist(), threshold=0.60)) if not tags_df.empty else pd.DataFrame()

    if HAS_NETWORKX and HAS_PLOTLY and nx is not None and hasattr(graph, "number_of_nodes"):
        fig = graph_to_plot(graph, max_nodes=180)
        if fig is not None:
            safe_plotly_chart(fig, use_container_width=True)
        node_count = graph.number_of_nodes()
        edge_count = graph.number_of_edges()
        node_rows = [{"kind": data.get("kind", ""), "label": data.get("label", ""), "subtitle": data.get("subtitle", "")} for _, data in graph.nodes(data=True)]
        edge_rows = [{"relation": data.get("relation", "")} for _, _, data in graph.edges(data=True)]
        node_df = pd.DataFrame(node_rows)
        edge_df = pd.DataFrame(edge_rows)
    else:
        node_df = pd.DataFrame(graph.get("nodes", [])) if isinstance(graph, dict) else pd.DataFrame()
        edge_df = pd.DataFrame(graph.get("edges", [])) if isinstance(graph, dict) else pd.DataFrame()
        node_count = len(node_df)
        edge_count = len(edge_df)
        if not node_df.empty and "kind" in node_df.columns:
            st.markdown("**distribuição de nós por tipo**")
            st.bar_chart(node_df["kind"].value_counts())
        if not edge_df.empty and "relation" in edge_df.columns:
            st.markdown("**relações registradas**")
            st.bar_chart(edge_df["relation"].value_counts())

    st.markdown(f"<div class='story-card'><div class='story-title'>estrutura conectada</div><div class='graph-note'>nós {node_count} · arestas {edge_count}. a rede articula camada social, metadados do museu, eixos institucionais e pontos de open data em um arranjo mais próximo do modelo de conhecimento expandido citado no caso do Prado.</div></div>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        if not node_df.empty and "kind" in node_df.columns:
            kinds = node_df["kind"].value_counts().rename_axis("tipo").reset_index(name="quantidade")
            render_bar_chart_df(kinds, x="tipo", y="quantidade", height=320)
        else:
            st.info("sem nós suficientes para sintetizar.")
    with c2:
        if not edge_df.empty and "relation" in edge_df.columns:
            relations = edge_df["relation"].value_counts().rename_axis("relação").reset_index(name="quantidade")
            render_bar_chart_df(relations.head(15), x="relação", y="quantidade", height=320)
        else:
            st.info("sem relações suficientes para sintetizar.")

    st.markdown("<div class='soft-line'></div>", unsafe_allow_html=True)
    t1, t2, t3 = st.tabs(["metadados interligados", "ligações entre tags", "variações ortográficas"])
    with t1:
        if not works_df.empty:
            meta_cols = [c for c in ["title", "artist", "museum", "collection", "place", "period", "technique", "material", "external_reference_label"] if c in works_df.columns]
            st.dataframe(works_df[meta_cols], use_container_width=True, hide_index=True)
        else:
            st.info("sem obras cadastradas.")
    with t2:
        if not semantic_df.empty:
            st.dataframe(semantic_df.head(40), use_container_width=True, hide_index=True)
        else:
            st.info("sem ligações fortes entre tags ainda.")
    with t3:
        if not typo_df.empty:
            st.dataframe(typo_df.head(40), use_container_width=True, hide_index=True)
        else:
            st.info("sem variantes ortográficas detectadas.")
    close_panel()


def render_admin_data(store: JsonStore, ml: SemanticLearner) -> None:
    def build_detailed_pdf_bytes() -> bytes:
        from io import BytesIO
        if not HAS_REPORTLAB:
            raise ModuleNotFoundError("reportlab")

        tags_df = build_tag_dataframe(store)
        works_df = to_dataframe(store.works())
        concepts_df = to_dataframe(store.concepts())
        validations_df = to_dataframe(store.validations())
        metrics = build_public_metrics(tags_df, works_df, to_dataframe(store.users()))
        semantic_rows = semantic_tag_links(tags_df["tag"].tolist(), threshold=0.60) if not tags_df.empty else []
        typo_rows = typo_candidate_rows(tags_df["tag"].tolist(), threshold=0.80) if not tags_df.empty else []
        daily = tags_df.groupby("created_date").agg(tags=("id", "count"), vocabulário=("normalized_tag", "nunique")).reset_index() if not tags_df.empty else pd.DataFrame()

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

        def spacer(amount: int = 10) -> None:
            nonlocal y
            y -= amount
            if y < 58:
                pdf.showPage()
                y = height - 44

        pdf.setTitle("Relatório detalhado de folksonomia")
        line("folksonomia", "Times-Bold", 22, 22)
        line("Relatório administrativo aprofundado da camada semântica, metadados museológicos, ligações entre tags e análise temporal", "Times-Roman", 12, 18)
        line(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", "Times-Roman", 11, 18)
        spacer(6)

        line("1. Métricas gerais", "Times-Bold", 16, 20)
        for label, value in [
            ("Total de obras", metrics.get("works", 0)),
            ("Obras tagueadas", metrics.get("tagged_works", 0)),
            ("Total de tags", metrics.get("total_tags", 0)),
            ("Vocabulário único", metrics.get("unique_tags", 0)),
            ("Participantes", metrics.get("active_users", 0)),
            ("Densidade lexical", f"{metrics.get('lexical_density', 0.0):.3f}"),
            ("Amostras do modelo", store.model_state().get("sample_count", 0)),
            ("Acurácia estimada do modelo", f"{store.model_state().get('accuracy', 0.0):.2f}"),
        ]:
            line(f"{label}: {value}")
        spacer(8)

        if not works_df.empty:
            line("2. Obras, metadados e pontos de open data", "Times-Bold", 16, 20)
            for _, row in works_df.iterrows():
                line(f"- {row.get('title', '')} | {row.get('artist', '')} | {row.get('year', '')}", "Times-Bold", 12, 16)
                for field, label in [
                    ("museum", "Museu"),
                    ("collection", "Coleção"),
                    ("place", "Lugar"),
                    ("period", "Período"),
                    ("technique", "Técnica"),
                    ("material", "Material"),
                    ("external_reference_label", "Referência externa"),
                ]:
                    if str(row.get(field, "")).strip():
                        line(f"  {label}: {row.get(field, '')}")
                if str(row.get("description", "")).strip():
                    line(f"  Descrição: {row.get('description', '')}")
                if isinstance(row.get("institutional_tags"), list) and row.get("institutional_tags"):
                    line(f"  Tags institucionais: {', '.join(row.get('institutional_tags', [])[:10])}")
                spacer(3)

        if not tags_df.empty:
            line("3. Camada social, semântica e tempo", "Times-Bold", 16, 20)
            top_tags = tags_df["tag"].value_counts().head(20)
            for tag, count in top_tags.items():
                line(f"- {tag}: {count} ocorrência(s)")
            spacer(5)
            entity_counts = tags_df["entity_prediction"].replace("", "não previsto").fillna("não previsto").value_counts()
            line("4. Categorias previstas", "Times-Bold", 16, 20)
            for entity, count in entity_counts.items():
                line(f"- {entity}: {count}")
            spacer(5)
            if not daily.empty:
                line("5. Série temporal diária", "Times-Bold", 16, 20)
                for _, row in daily.tail(20).iterrows():
                    line(f"- {row.get('created_date', '')}: tags {row.get('tags', 0)} | vocabulário {row.get('vocabulário', 0)}")
                spacer(5)
            clusters = ml.cluster_terms(tags_df["tag"].astype(str).tolist(), threshold=0.66)
            line("6. Agrupamentos semânticos", "Times-Bold", 16, 20)
            if clusters:
                for idx, cluster in enumerate(clusters[:15], 1):
                    line(f"- Grupo {idx}: {', '.join(cluster)}")
            else:
                line("- Ainda não há agrupamentos suficientemente robustos.")
            spacer(5)

        if semantic_rows:
            line("7. Ligações entre tags por eixo comum", "Times-Bold", 16, 20)
            for row in semantic_rows[:25]:
                line(f"- {row['tag_a']} ↔ {row['tag_b']} | score {row['score']} | {row['relation']}")
            spacer(5)

        if typo_rows:
            line("8. Variantes ortográficas e quase duplicatas", "Times-Bold", 16, 20)
            for row in typo_rows[:25]:
                line(f"- {row['termo_a']} ↔ {row['termo_b']} | trigramas {row['similaridade_trigrama']} | palavras {row['sobreposição_palavras']}")
            spacer(5)

        if not concepts_df.empty:
            line("9. Conceitos reconciliados", "Times-Bold", 16, 20)
            for _, row in concepts_df.head(40).iterrows():
                alias_text = ", ".join(row.get("aliases", [])[:6]) if isinstance(row.get("aliases"), list) else str(row.get("aliases", ""))
                line(f"- {row.get('label', '')} | categoria {row.get('category', '')} | origem {row.get('source', '')}")
                if alias_text:
                    line(f"  Alias: {alias_text}")
            spacer(5)

        if not validations_df.empty:
            line("10. Validações administrativas", "Times-Bold", 16, 20)
            for _, row in validations_df.tail(40).iterrows():
                line(f"- {row.get('created_at', '')} | decisão {row.get('decision', '')} | entidade {row.get('validated_entity', '')} | conceito {row.get('validated_concept_label', '')}")
                if str(row.get("notes", "")).strip():
                    line(f"  Observações: {row.get('notes', '')}")

        pdf.save()
        buffer.seek(0)
        return buffer.getvalue()

    open_panel("obras e exportação", "gestão administrativa de obras, cadastro enriquecido de metadados e download detalhado em csv e pdf.")
    works = store.works()
    t1, t2, t3, t4 = st.tabs(["obras", "nova obra", "exportação csv", "exportação pdf"])

    with t1:
        if not works:
            st.info("não há obras cadastradas.")
        else:
            works_df = to_dataframe(works)
            display_cols = [c for c in ["title", "artist", "year", "museum", "collection", "period", "technique", "material", "institutional_tags", "created_at"] if c in works_df.columns]
            st.dataframe(works_df[display_cols], use_container_width=True, hide_index=True)
            st.markdown("<div class='soft-line'></div>", unsafe_allow_html=True)
            for work in works:
                meta = resolve_work_metadata(work)
                c1, c2, c3 = st.columns([0.8, 1.8, 0.7])
                with c1:
                    st.image(work.get("image_url"), use_container_width=True)
                with c2:
                    info = "<br>".join([part for part in [
                        f"{work.get('artist')} · {work.get('year')}",
                        meta.get("museum", ""),
                        meta.get("period", ""),
                        meta.get("technique", ""),
                        meta.get("material", ""),
                    ] if part])
                    st.markdown(f"<div class='story-card'><div class='story-title'>{work.get('title')}</div><div class='story-copy'>{info}<br>{work.get('description')}</div></div>", unsafe_allow_html=True)
                with c3:
                    if st.button("excluir obra", key=f"delete-work-{work.get('id')}", use_container_width=True):
                        remaining = [item for item in store.works() if item.get("id") != work.get("id")]
                        store.save_works(remaining)
                        remaining_tags = [item for item in store.tags() if item.get("work_id") != work.get("id")]
                        store.save_tags(remaining_tags)
                        ml.train()
                        st.success("obra excluída com suas marcações associadas.")
                        st.rerun()
                st.markdown("<div class='soft-line'></div>", unsafe_allow_html=True)

    with t2:
        with st.form("new-work"):
            c1, c2, c3 = st.columns(3)
            with c1:
                title = st.text_input("título")
                artist = st.text_input("artista")
                year = st.text_input("ano")
                image_url = st.text_input("url da imagem")
            with c2:
                museum = st.text_input("museu / instituição")
                collection = st.text_input("coleção")
                place = st.text_input("lugar")
                period = st.text_input("período")
            with c3:
                technique = st.text_input("técnica")
                material = st.text_input("material")
                external_reference_label = st.text_input("rótulo open data")
                external_reference_url = st.text_input("url open data")
            tags = st.text_input("tags institucionais separadas por vírgula")
            description = st.text_area("descrição", height=120)
            submitted = st.form_submit_button("adicionar obra")
            if submitted:
                if not title.strip() or not artist.strip():
                    st.warning("preencha ao menos título e artista.")
                else:
                    store.add_work(
                        title, artist, year, description, image_url, [part.strip() for part in tags.split(",") if part.strip()],
                        museum=museum, collection=collection, place=place, period=period, technique=technique, material=material,
                        external_reference_label=external_reference_label, external_reference_url=external_reference_url,
                    )
                    ml.train()
                    st.success("obra adicionada.")
                    st.rerun()

    with t3:
        works_df = to_dataframe(store.works())
        tags_df = build_tag_dataframe(store)
        concepts_df = to_dataframe(store.concepts())
        validations_df = to_dataframe(store.validations())
        users_df = to_dataframe(store.users())
        semantic_df = pd.DataFrame(semantic_tag_links(tags_df["tag"].tolist(), threshold=0.60)) if not tags_df.empty else pd.DataFrame()
        typo_df = pd.DataFrame(typo_candidate_rows(tags_df["tag"].tolist(), threshold=0.80)) if not tags_df.empty else pd.DataFrame()
        st.download_button("baixar obras em csv", works_df.to_csv(index=False).encode("utf-8"), "obras_folksonomia.csv", "text/csv", use_container_width=True)
        st.download_button("baixar tags em csv", tags_df.to_csv(index=False).encode("utf-8"), "tags_folksonomia.csv", "text/csv", use_container_width=True)
        st.download_button("baixar conceitos em csv", concepts_df.to_csv(index=False).encode("utf-8"), "conceitos_folksonomia.csv", "text/csv", use_container_width=True)
        st.download_button("baixar validações em csv", validations_df.to_csv(index=False).encode("utf-8"), "validacoes_folksonomia.csv", "text/csv", use_container_width=True)
        st.download_button("baixar usuários em csv", users_df.to_csv(index=False).encode("utf-8"), "usuarios_folksonomia.csv", "text/csv", use_container_width=True)
        if not semantic_df.empty:
            st.download_button("baixar ligações semânticas em csv", semantic_df.to_csv(index=False).encode("utf-8"), "ligacoes_semanticas.csv", "text/csv", use_container_width=True)
        if not typo_df.empty:
            st.download_button("baixar variantes ortográficas em csv", typo_df.to_csv(index=False).encode("utf-8"), "variantes_ortograficas.csv", "text/csv", use_container_width=True)

    with t4:
        try:
            pdf_bytes = build_detailed_pdf_bytes()
            st.markdown("<div class='story-card'><div class='story-title'>relatório administrativo em pdf</div><div class='story-copy'>o arquivo reúne métricas gerais, metadados das obras, top tags, categorias previstas pelo modelo, agrupamentos, ligações entre tags, variantes ortográficas, conceitos reconciliados, validações e análise temporal.</div></div>", unsafe_allow_html=True)
            st.download_button("baixar relatório detalhado em pdf", pdf_bytes, "relatorio_detalhado_folksonomia.pdf", "application/pdf", use_container_width=True)
        except Exception as exc:
            st.warning(f"não foi possível gerar o pdf nesta execução: {exc}")

    close_panel()


def render_footer() -> None:
    st.markdown("<div class='story-copy' style='text-align:center;margin-top:1rem;margin-bottom:2rem'>folksonomia · interface translúcida · tipografia serifada · aprendizagem incremental · análise temporal semântica</div>", unsafe_allow_html=True)


def _legacy_main_1() -> None:
    render_css()
    store = JsonStore()
    init_session()
    ml = SemanticLearner(store)
    run_automation_engine(store, ml)

    if not st.session_state.get("intro_complete", False) and store.settings().get("public_intro_enabled", True):
        intro_flow(store)
        render_footer()
        return

    topbar(store)
    hero_panel(store)

    public_tabs = st.tabs(["explorar obras", "administração"])
    with public_tabs[0]:
        render_public_explore(store, ml)
    with public_tabs[1]:
        if not st.session_state.get("admin_authenticated", False):
            render_admin_login(store)
        else:
            admin_tabs = st.tabs(["painel geral", "validação", "conceitos", "machine learning", "análise temporal", "grafo", "dados e obras"])
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
            if st.button("sair da administração", use_container_width=True):
                st.session_state["admin_authenticated"] = False
                st.rerun()
    render_footer()


# ===== PATCH V3: teia 3D, validação expandida, temporal enxuto, ML com resumos =====

def render_css_patch_v3() -> None:
    st.markdown("""
    <style>
    .hero-copy { display:none !important; }
    .hero-panel { padding: 1.35rem 1.5rem !important; }
    .hero-title { margin-top: 0.35rem; margin-bottom: 0.2rem; }
    .panel-subtitle:empty { display:none !important; }
    .stTextArea textarea,
    .stTextInput input,
    textarea,
    input,
    [data-baseweb="input"] input,
    [data-baseweb="textarea"] textarea,
    [data-baseweb="base-input"] textarea,
    [data-baseweb="base-input"] input {
        color: #111111 !important;
        -webkit-text-fill-color: #111111 !important;
        caret-color: #111111 !important;
        text-shadow: none !important;
        font-weight: 600 !important;
    }
    .stTextArea textarea::selection,
    .stTextInput input::selection,
    textarea::selection,
    input::selection {
        background: rgba(40,40,40,0.18) !important;
        color: #111111 !important;
    }
    .stTextArea textarea::placeholder,
    .stTextInput input::placeholder,
    textarea::placeholder,
    input::placeholder {
        color: #6f6f6f !important;
        -webkit-text-fill-color: #6f6f6f !important;
        opacity: 1 !important;
    }
    .work-card { min-height: 320px !important; }
    .work-card img { height: 260px !important; }
    .tag-compact-box {
        max-width: 780px !important;
        margin: 0.75rem auto 0 auto !important;
        padding: 0.95rem 1rem !important;
    }
    .public-selected-image {
        max-width: 980px !important;
        margin: 0 auto !important;
        border-radius: 24px !important;
        overflow: hidden !important;
        background: rgba(255,255,255,0.18) !important;
        border: 1px solid rgba(255,255,255,0.52) !important;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.72), 0 12px 28px rgba(0,0,0,0.07) !important;
        padding: 0.7rem !important;
    }
    .public-selected-image img { border-radius: 20px !important; }
    .summary-block {
        background: rgba(255,255,255,0.18);
        border: 1px solid rgba(255,255,255,0.48);
        border-radius: 22px;
        padding: 1rem 1.1rem;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.70), 0 12px 26px rgba(0,0,0,0.06);
        color: #333333;
        line-height: 1.8;
    }
    .summary-block strong { color: #141414; }
    .story-card p, .summary-block p { color: #333333 !important; }
    </style>
    """, unsafe_allow_html=True)


def hero_panel(store: JsonStore) -> None:
    html = """
    <div class="hero-panel">
        <div class="hero-grid" style="grid-template-columns: 1fr;">
            <div>
                <div class="hero-kicker">camada semântica participativa com aprendizado contínuo</div>
                <div class="hero-title">folksonomia</div>
            </div>
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def _graph_payload(graph: Any) -> Dict[str, Any]:
    if HAS_NETWORKX and nx is not None and hasattr(graph, "nodes"):
        nodes = []
        for node_id, attrs in graph.nodes(data=True):
            row = dict(attrs)
            row["id"] = node_id
            nodes.append(row)
        edges = []
        for source, target, attrs in graph.edges(data=True):
            edges.append({"source": source, "target": target, **dict(attrs)})
        return {"nodes": nodes, "edges": edges}
    if isinstance(graph, dict):
        return {"nodes": graph.get("nodes", []), "edges": graph.get("edges", [])}
    return {"nodes": [], "edges": []}


def _edge_count_map(edges: Sequence[Dict[str, Any]]) -> Dict[str, int]:
    counts = Counter()
    for edge in edges:
        a = str(edge.get("source", ""))
        b = str(edge.get("target", ""))
        if a:
            counts[a] += 1
        if b:
            counts[b] += 1
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
        center_x = math.cos(base_angle) * kind_radius
        center_y = math.sin(base_angle) * kind_radius
        center_z = ((ki % 5) - 2) * 0.75
        local_radius = 0.8 + min(len(group), 24) * 0.03
        for idx, row in enumerate(group):
            nid = str(row.get("id", ""))
            h = sum(ord(ch) for ch in nid) % 1000
            phi = (2 * math.pi * idx) / max(len(group), 1)
            theta = ((h % 360) / 360.0) * math.pi
            rx = local_radius * math.cos(phi) * max(0.35, math.sin(theta))
            ry = local_radius * math.sin(phi) * max(0.35, math.sin(theta))
            rz = local_radius * math.cos(theta) * 0.85
            pos[nid] = (center_x + rx, center_y + ry, center_z + rz)
    return pos


def graph_to_plot_3d(graph: Any, max_nodes: int = 220) -> Any:
    if not HAS_PLOTLY or go is None:
        return None
    payload = _graph_payload(graph)
    nodes = payload["nodes"]
    edges = payload["edges"]
    if not nodes:
        return None
    degree = _edge_count_map(edges)
    nodes = sorted(nodes, key=lambda row: degree.get(str(row.get("id", "")), 0), reverse=True)[:max_nodes]
    keep = {str(row.get("id", "")) for row in nodes}
    edges = [edge for edge in edges if str(edge.get("source", "")) in keep and str(edge.get("target", "")) in keep]
    if HAS_NETWORKX and nx is not None:
        g = nx.Graph()
        for row in nodes:
            g.add_node(str(row.get("id", "")), **row)
        for edge in edges:
            g.add_edge(str(edge.get("source", "")), str(edge.get("target", "")), **edge)
        try:
            pos = nx.spring_layout(g, dim=3, seed=42, k=max(0.38, 2.2 / math.sqrt(max(len(g.nodes()), 4))), iterations=120)
        except Exception:
            pos = _manual_3d_layout(nodes, edges)
    else:
        pos = _manual_3d_layout(nodes, edges)

    kind_colors = {
        "work": "#243B53",
        "tag": "#5C677D",
        "user": "#9C6644",
        "concept": "#2F4858",
        "institutional_tag": "#6C757D",
        "artist": "#3D405B",
        "museum": "#6D597A",
        "collection": "#588157",
        "place": "#7F5539",
        "period": "#4361EE",
        "technique": "#6B705C",
        "material": "#A68A64",
        "external_entity": "#7B2CBF",
        "external_reference": "#8D99AE",
        "tag_surface": "#495057",
        "typo_candidate": "#BC6C25",
        "entity_class": "#1D3557",
    }

    ex, ey, ez = [], [], []
    for edge in edges:
        s = str(edge.get("source", ""))
        t = str(edge.get("target", ""))
        if s not in pos or t not in pos:
            continue
        x0, y0, z0 = pos[s]
        x1, y1, z1 = pos[t]
        ex.extend([x0, x1, None])
        ey.extend([y0, y1, None])
        ez.extend([z0, z1, None])

    edge_trace = go.Scatter3d(
        x=ex, y=ey, z=ez,
        mode="lines",
        line=dict(color="rgba(70,70,70,0.28)", width=2),
        hoverinfo="none",
        name="ligações"
    )

    xs, ys, zs, colors, sizes, texts = [], [], [], [], [], []
    for row in nodes:
        nid = str(row.get("id", ""))
        if nid not in pos:
            continue
        x, y, z = pos[nid]
        xs.append(x)
        ys.append(y)
        zs.append(z)
        kind = str(row.get("kind", "outro"))
        colors.append(kind_colors.get(kind, "#444444"))
        deg = degree.get(nid, 1)
        sizes.append(min(24, 6 + deg * 0.65))
        label = row.get("label", nid)
        subtitle = row.get("subtitle", "")
        texts.append(f"{label}<br>{kind}<br>{subtitle}<br>grau {deg}")

    node_trace = go.Scatter3d(
        x=xs, y=ys, z=zs,
        mode="markers",
        text=texts,
        hovertemplate="%{text}<extra></extra>",
        marker=dict(
            size=sizes,
            color=colors,
            opacity=0.92,
            line=dict(color="rgba(255,255,255,0.85)", width=1.4),
        ),
        name="nós"
    )

    label_rows = []
    for row in nodes:
        nid = str(row.get("id", ""))
        if nid in pos and degree.get(nid, 0) >= 3:
            label_rows.append((degree.get(nid, 0), row))
    label_rows = sorted(label_rows, key=lambda item: item[0], reverse=True)[:28]
    lx, ly, lz, lt = [], [], [], []
    for _, row in label_rows:
        nid = str(row.get("id", ""))
        x, y, z = pos[nid]
        lx.append(x)
        ly.append(y)
        lz.append(z)
        lt.append(str(row.get("label", ""))[:34])

    text_trace = go.Scatter3d(
        x=lx, y=ly, z=lz,
        mode="text",
        text=lt,
        textfont=dict(size=11, color="#1f1f1f"),
        hoverinfo="none",
        showlegend=False
    )

    fig = go.Figure(data=[edge_trace, node_trace, text_trace])
    fig.update_layout(
        height=760,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        scene=dict(
            xaxis=dict(visible=False, showbackground=False),
            yaxis=dict(visible=False, showbackground=False),
            zaxis=dict(visible=False, showbackground=False),
            bgcolor="rgba(0,0,0,0)",
            camera=dict(eye=dict(x=1.7, y=1.7, z=1.18))
        ),
        legend=dict(orientation="h", yanchor="bottom", y=0.01, xanchor="left", x=0.01, bgcolor="rgba(255,255,255,0.22)")
    )
    return fig


def _analysis_summary_blocks(store: JsonStore, ml: SemanticLearner) -> Dict[str, str]:
    tags_df = build_tag_dataframe(store)
    validations_df = to_dataframe(store.validations())
    concepts_df = to_dataframe(store.concepts())
    if tags_df.empty:
        return {
            "ml": "Ainda não há tags suficientes para síntese do aprendizado.",
            "validation": "A fila de validação será enriquecida quando a marcação pública começar a formar recorrências.",
            "graph": "A teia 3D aparecerá densamente conectada quando obras, tags e conceitos passarem a compartilhar relações."
        }
    total = len(tags_df)
    unique = int(tags_df["normalized_tag"].nunique())
    validated = int(tags_df.get("is_validated", pd.Series([False]*len(tags_df))).sum())
    pending = total - validated
    entity_dist = tags_df["entity_prediction"].replace("", "tema").value_counts().head(5)
    entity_text = ", ".join([f"{idx} {int(val)}" for idx, val in entity_dist.items()]) if not entity_dist.empty else "sem distribuição ainda"
    concept_hits = tags_df["concept_label"].fillna("").astype(str)
    concept_hits = concept_hits[concept_hits.str.strip() != ""].value_counts().head(5)
    concept_text = ", ".join([f"{idx} {int(val)}" for idx, val in concept_hits.items()]) if not concept_hits.empty else "sem conceitos ligados"
    typo_rows = typo_candidate_rows(tags_df["tag"].tolist(), threshold=0.80)
    semantic_rows = semantic_tag_links(tags_df["tag"].tolist(), threshold=0.60)
    work_density = tags_df.groupby("work_title").agg(tags=("id", "count"), voc=("normalized_tag", "nunique")).reset_index().sort_values(["tags", "voc"], ascending=False)
    work_text = ", ".join([f"{row['work_title']} {int(row['tags'])}" for _, row in work_density.head(4).iterrows()]) if not work_density.empty else "sem densidade por obra"
    validation_text = f"Total {total} marcações, {unique} formas únicas, {validated} já validadas e {pending} pendentes. Obras mais densas: {work_text}. Ligações semânticas detectadas: {len(semantic_rows)}. Variantes ortográficas fortes: {len(typo_rows)}."
    ml_text = f"O modelo está treinado com {ml.entity_samples} amostras, acurácia estimada em {ml.entity_accuracy:.2f}, e lê principalmente {entity_text}. Conceitos mais acionados: {concept_text}. Cada validação aprovada retorna ao corpus de treino e altera as próximas previsões."
    graph_text = f"A teia conecta obras, artistas, museu, coleção, lugar, período, técnica, material, tags institucionais, tags livres, conceitos reconciliados e pontos de open data externo. No momento, há {len(concepts_df)} conceitos ativos e {len(validations_df)} validações persistidas."
    return {"ml": ml_text, "validation": validation_text, "graph": graph_text}


def render_public_explore(store: JsonStore, ml: SemanticLearner) -> None:
    user = store.find_user(st.session_state.get("session_user_id", ""))
    works = store.works()
    open_panel("explorar obras", "")
    if not user or not works:
        close_panel()
        return

    works = works[:3]
    cols = st.columns(3 if len(works) >= 3 else max(1, len(works)))
    for idx, work in enumerate(works):
        with cols[idx % len(cols)]:
            st.markdown("<div class='work-card'>", unsafe_allow_html=True)
            st.image(work.get("image_url"), use_container_width=True)
            if st.button("marcar esta imagem", key=f"public-open-v3-{work.get('id')}", use_container_width=True):
                st.session_state["selected_work_id"] = work.get("id")
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    selected_id = st.session_state.get("selected_work_id", "")
    if selected_id:
        selected = next((w for w in works if w.get("id") == selected_id), None)
        if selected:
            tags_df = build_tag_dataframe(store)
            mine = tags_df[(tags_df["work_id"] == selected_id) & (tags_df["user_id"] == user.get("id"))] if not tags_df.empty else pd.DataFrame()
            st.markdown("<div class='soft-line'></div>", unsafe_allow_html=True)
            st.markdown("<div class='public-selected-image'>", unsafe_allow_html=True)
            st.image(selected.get("image_url"), use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("<div class='tag-compact-box'>", unsafe_allow_html=True)
            with st.form(f"tag-form-v3-{selected_id}", clear_on_submit=True):
                tag_value = st.text_input("sua tag", placeholder="escreva uma palavra ou pequena expressão")
                submitted = st.form_submit_button("registrar tag", use_container_width=True)
                if submitted:
                    if not tag_value.strip():
                        st.warning("escreva uma tag antes de registrar.")
                    else:
                        store.submit_tag(selected.get("id"), user.get("id"), tag_value, "", ml)
                        run_automation_engine(store, ml)
                        st.success("tag registrada.")
                        st.rerun()
            if not mine.empty:
                mine_counts = mine["tag"].value_counts().reset_index()
                mine_counts.columns = ["tag", "frequência"]
                st.markdown("<div class='tag-preview-wrap'>" + "".join([f"<span class='tag-chip'>{row['tag']} {int(row['frequência'])}</span>" for _, row in mine_counts.iterrows()]) + "</div>", unsafe_allow_html=True)
            if st.button("fechar imagem", key=f"close-public-v3-{selected_id}", use_container_width=True):
                st.session_state["selected_work_id"] = ""
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
    close_panel()


def render_admin_validation(store: JsonStore, ml: SemanticLearner) -> None:
    tags_df = build_tag_dataframe(store)
    suggestions_df = to_dataframe(store.suggestions())
    concepts = store.concepts()
    concept_options = {f"{c.get('label')} · {c.get('category')}": c for c in concepts}
    open_panel("validação e supervisão", "fila curatorial, conexões entre tags, variantes ortográficas e leitura cruzada por obra.")
    if tags_df.empty:
        st.info("não há tags registradas.")
        close_panel()
        return

    summaries = _analysis_summary_blocks(store, ml)
    st.markdown(f"<div class='summary-block'><strong>síntese curatorial.</strong> {summaries['validation']}</div>", unsafe_allow_html=True)

    semantic_rows = pd.DataFrame(semantic_tag_links(tags_df["tag"].tolist(), threshold=0.60))
    typo_rows = pd.DataFrame(typo_candidate_rows(tags_df["tag"].tolist(), threshold=0.80))
    work_time = tags_df.groupby(["work_title", "created_month"]).agg(tags=("id", "count"), vocabulário=("normalized_tag", "nunique")).reset_index()
    relation_by_work = semantic_rows.copy()
    tabs = st.tabs(["fila de validação", "ligações entre tags", "variações ortográficas", "obras e conexões"])
    with tabs[0]:
        subset = tags_df.sort_values("created_at", ascending=False).head(20)
        open_suggestions = suggestions_df[suggestions_df["status"] == "open"] if not suggestions_df.empty else pd.DataFrame()
        for _, row in subset.iterrows():
            related_suggestions = open_suggestions[open_suggestions["tag_id"] == row.get("id")] if not open_suggestions.empty else pd.DataFrame()
            st.markdown(f"<div class='queue-card'><div class='story-title'>{row.get('tag')} · {row.get('work_title', '')}</div><div class='queue-text'>previsão {row.get('entity_prediction', '')} · confiança {safe_float(row.get('entity_confidence', 0.0)):.2f}<br>conceito atual {row.get('concept_label', '') or 'não ligado'}<br>museu {row.get('work_museum', '') or 'não informado'} · período {row.get('work_period', '') or 'não informado'} · técnica {row.get('work_technique', '') or 'não informada'}</div></div>", unsafe_allow_html=True)
            if not related_suggestions.empty:
                for _, srow in related_suggestions.iterrows():
                    st.markdown(f"<div class='suggestion-card'><div class='suggestion-title'>{srow.get('rule_name')}</div><div class='suggestion-meta'>{json.dumps(srow.get('payload', {}), ensure_ascii=False)}</div></div>", unsafe_allow_html=True)
            with st.form(f"validate-v3-{row.get('id')}"):
                c1, c2 = st.columns(2)
                with c1:
                    default_entity = row.get("entity_prediction") if row.get("entity_prediction") in ENTITY_LABELS else "tema"
                    entity_choice = st.selectbox("categoria validada", ENTITY_LABELS, index=ENTITY_LABELS.index(default_entity), key=f"ent-v3-{row.get('id')}")
                    concept_choice = st.selectbox("conceito reconciliado", ["nenhum"] + list(concept_options.keys()), key=f"con-v3-{row.get('id')}")
                with c2:
                    decision = st.selectbox("decisão", ["approved", "linked", "rejected"], key=f"dec-v3-{row.get('id')}")
                    notes = st.text_area("notas curatoriais", height=90, key=f"notes-v3-{row.get('id')}")
                submitted = st.form_submit_button("registrar validação")
                if submitted:
                    concept_id = ""
                    concept_label = ""
                    if concept_choice != "nenhum":
                        concept_payload = concept_options[concept_choice]
                        concept_id = concept_payload.get("id", "")
                        concept_label = concept_payload.get("label", "")
                    store.add_validation(row.get("id"), "admin", entity_choice, concept_id, concept_label, decision, notes)
                    updates = {"status": "validated" if decision != "rejected" else "rejected", "entity_prediction": entity_choice, "entity_confidence": 1.0}
                    if concept_id:
                        updates["concept_id"] = concept_id
                        updates["concept_label"] = concept_label
                    store.update_tag(row.get("id"), updates)
                    if not related_suggestions.empty:
                        for _, srow in related_suggestions.iterrows():
                            store.close_suggestion(srow.get("id"), status="resolved")
                    ml.train()
                    st.success("validação registrada e modelo atualizado.")
                    st.rerun()
    with tabs[1]:
        st.markdown("<div class='story-card'><div class='story-title'>campos semânticos compartilhados</div><div class='story-copy'>as tags aparecem por eixos comuns, coocorrência lexical, aproximação conceitual e pontes entre vocabulário social, metadados museológicos e referências externas.</div></div>", unsafe_allow_html=True)
        if semantic_rows.empty:
            st.info("ainda não há ligações semânticas suficientes.")
        else:
            semantic_rows["força"] = semantic_rows.get("score", semantic_rows.get("similaridade", 0.0))
            render_bar_chart_df(semantic_rows.head(18), x="tag_a", y="força", height=360)
            st.dataframe(semantic_rows.head(30), use_container_width=True, hide_index=True)
    with tabs[2]:
        st.markdown("<div class='story-card'><div class='story-title'>desambiguação ortográfica</div><div class='story-copy'>pares fortes de quase duplicata ajudam a consolidar grafias, revisar ruído e preservar a fala do público sem achatá-la prematuramente.</div></div>", unsafe_allow_html=True)
        if typo_rows.empty:
            st.info("não foram encontrados pares fortes de variante ortográfica.")
        else:
            if "score" in typo_rows.columns:
                render_bar_chart_df(typo_rows.head(18), x="termo_a", y="score", height=360)
            st.dataframe(typo_rows.head(30), use_container_width=True, hide_index=True)
    with tabs[3]:
        st.markdown("<div class='story-card'><div class='story-title'>obras no fluxo documental</div><div class='story-copy'>cada obra é lida por densidade de marcação, diversidade lexical e recorrência temporal. isso aproxima a documentação social da unidade museológica e do modelo conectado do Prado.</div></div>", unsafe_allow_html=True)
        work_summary = tags_df.groupby(["work_title", "work_museum", "work_period", "work_technique", "work_material"]).agg(tags=("id", "count"), vocabulário=("normalized_tag", "nunique")).reset_index().sort_values(["tags", "vocabulário"], ascending=False)
        if not work_summary.empty:
            render_bar_chart_df(work_summary.head(12), x="work_title", y="tags", height=340)
            if not work_time.empty and HAS_PLOTLY:
                fig = px.line(work_time.sort_values("created_month"), x="created_month", y="tags", color="work_title", markers=True)
                fig.update_layout(height=360, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=10, r=10, t=20, b=10))
                safe_plotly_chart(fig, use_container_width=True)
            st.dataframe(work_summary.head(20), use_container_width=True, hide_index=True)
        else:
            st.info("sem dados suficientes por obra.")
    close_panel()


def render_admin_ml(store: JsonStore, ml: SemanticLearner) -> None:
    model_info = store.model_state()
    tags_df = build_tag_dataframe(store)
    summaries = _analysis_summary_blocks(store, ml)
    open_panel("machine learning", "aprendizado supervisionado com seed vocab, metadados museológicos, conceitos, validações e sumários interpretativos.")
    html = f"""
    <div class="metric-strip">
        <div class="metric-card"><div class="metric-caption">último treino</div><div class="metric-number">{model_info.get('last_trained_at', '') or 'agora'}</div><div class="metric-note">estado persistido</div></div>
        <div class="metric-card"><div class="metric-caption">amostras</div><div class="metric-number">{model_info.get('sample_count', 0)}</div><div class="metric-note">seed, validação e metadados</div></div>
        <div class="metric-card"><div class="metric-caption">acurácia</div><div class="metric-number">{model_info.get('accuracy', 0.0):.2f}</div><div class="metric-note">estimativa offline</div></div>
        <div class="metric-card"><div class="metric-caption">classes</div><div class="metric-number">{len(ml.entity_labels)}</div><div class="metric-note">tipos semânticos</div></div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)
    st.markdown(f"<div class='summary-block'><strong>sumário do aprendizado.</strong> {summaries['ml']}</div>", unsafe_allow_html=True)
    c1, c2 = st.columns([1.05, 0.95])
    with c1:
        query = st.text_input("teste rápido do modelo", placeholder="escreva um termo para prever a categoria")
        if query.strip():
            pred = ml.predict_entity(query)
            st.markdown(f"<div class='suggestion-card'><div class='suggestion-title'>previsão</div><div class='suggestion-meta'>categoria {pred.get('label')} · confiança {pred.get('confidence', 0.0):.2f}</div></div>", unsafe_allow_html=True)
            concepts = ml.suggest_concepts(query, 6)
            if concepts:
                st.markdown("<div class='tag-preview-wrap'>" + "".join([f"<span class='tag-chip'>{c.get('label')} · {c.get('category')} · {c.get('similarity', 0.0):.2f}</span>" for c in concepts]) + "</div>", unsafe_allow_html=True)
        if not tags_df.empty:
            predicted = tags_df["entity_prediction"].replace("", "tema").value_counts().rename_axis("categoria").reset_index(name="frequência")
            render_bar_chart_df(predicted, x="categoria", y="frequência", height=340)
    with c2:
        if st.button("re-treinar modelo agora", use_container_width=True):
            ml.train()
            st.success("modelo re-treinado com a base atual.")
            st.rerun()
        st.markdown("<div class='story-card'><div class='story-title'>aprendizado efetivo</div><div class='story-copy'>o modelo não usa só vocabulário seed. ele incorpora descrições de obras, tags institucionais, metadados museológicos e validações administrativas, gerando previsões mais estáveis e resumos analíticos sobre o que foi encontrado.</div></div>", unsafe_allow_html=True)
        if not tags_df.empty and "entity_confidence" in tags_df.columns:
            conf = tags_df["entity_confidence"].fillna(0).astype(float)
            conf_df = pd.DataFrame({"faixa": ["0.00–0.39", "0.40–0.69", "0.70–1.00"], "quantidade": [int(((conf < 0.40)).sum()), int(((conf >= 0.40) & (conf < 0.70)).sum()), int((conf >= 0.70).sum())]})
            render_bar_chart_df(conf_df, x="faixa", y="quantidade", height=280)
    close_panel()


def render_admin_automation(store: JsonStore, ml: SemanticLearner) -> None:
    tags_df = build_tag_dataframe(store)
    open_panel("análise temporal", "ritmo, sazonalidade, distribuição horária e crescimento do vocabulário. sem tabelas, apenas leitura temporal conectada.")
    if tags_df.empty:
        st.info("a análise temporal será exibida quando houver tags registradas.")
        close_panel()
        return

    tags_df["created_ts"] = pd.to_datetime(tags_df["created_at"], errors="coerce")
    tags_df = tags_df.sort_values("created_ts")
    daily = tags_df.groupby("created_date").agg(tags=("id", "count"), vocabulário=("normalized_tag", "nunique"), participantes=("user_id", "nunique")).reset_index()
    monthly = tags_df.groupby("created_month").agg(tags=("id", "count"), vocabulário=("normalized_tag", "nunique")).reset_index()
    hourly = tags_df.groupby("created_hour").agg(tags=("id", "count")).reset_index()
    weekday_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    weekday_map = {"Monday": "Seg", "Tuesday": "Ter", "Wednesday": "Qua", "Thursday": "Qui", "Friday": "Sex", "Saturday": "Sáb", "Sunday": "Dom"}
    weekday = tags_df.groupby("created_weekday").agg(tags=("id", "count")).reset_index()
    if not weekday.empty:
        weekday["sort"] = weekday["created_weekday"].map(lambda value: weekday_order.index(value) if value in weekday_order else 99)
        weekday = weekday.sort_values("sort")
        weekday["dia"] = weekday["created_weekday"].map(lambda value: weekday_map.get(value, value))

    lexical_curve = []
    seen = set()
    for _, row in tags_df.iterrows():
        seen.add(row.get("normalized_tag", ""))
        lexical_curve.append({"created_at": row.get("created_at", ""), "vocabulário_acumulado": len(seen)})
    lexical_df = pd.DataFrame(lexical_curve)

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(f"<div class='metric-card'><div class='metric-caption'>dias ativos</div><div class='metric-number'>{daily['created_date'].nunique()}</div><div class='metric-note'>com registros</div></div>", unsafe_allow_html=True)
    with c2: st.markdown(f"<div class='metric-card'><div class='metric-caption'>pico diário</div><div class='metric-number'>{int(daily['tags'].max())}</div><div class='metric-note'>dia mais intenso</div></div>", unsafe_allow_html=True)
    with c3: st.markdown(f"<div class='metric-card'><div class='metric-caption'>média diária</div><div class='metric-number'>{daily['tags'].mean():.1f}</div><div class='metric-note'>tags por dia</div></div>", unsafe_allow_html=True)
    with c4: st.markdown(f"<div class='metric-card'><div class='metric-caption'>vocabulário final</div><div class='metric-number'>{int(tags_df['normalized_tag'].nunique())}</div><div class='metric-note'>formas normalizadas</div></div>", unsafe_allow_html=True)

    st.markdown("<div class='summary-block'><strong>leitura temporal.</strong> O tempo é tratado como camada documental: a curva diária mostra intensidade de participação, a distribuição horária indica momentos de ativação e o vocabulário acumulado revela quando novas formas entram na rede social de descrição.</div>", unsafe_allow_html=True)

    tabs = st.tabs(["ritmo diário", "sazonalidade", "crescimento lexical"])
    with tabs[0]:
        if HAS_PLOTLY:
            fig = go.Figure()
            fig.add_scatter(x=daily["created_date"], y=daily["tags"], mode="lines+markers", name="tags")
            fig.add_scatter(x=daily["created_date"], y=daily["participantes"], mode="lines+markers", name="participantes")
            fig.update_layout(height=380, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=10, r=10, t=20, b=10))
            safe_plotly_chart(fig, use_container_width=True)
        else:
            st.line_chart(daily.set_index("created_date")[["tags", "participantes"]])
    with tabs[1]:
        c1, c2 = st.columns(2)
        with c1:
            render_bar_chart_df(hourly, x="created_hour", y="tags", height=320)
        with c2:
            if not weekday.empty:
                render_bar_chart_df(weekday[["dia", "tags"]], x="dia", y="tags", height=320)
            else:
                st.info("sem dados suficientes por dia da semana.")
        if not monthly.empty:
            render_bar_chart_df(monthly, x="created_month", y="tags", height=320)
    with tabs[2]:
        if not lexical_df.empty:
            if HAS_PLOTLY:
                fig = px.line(lexical_df, x="created_at", y="vocabulário_acumulado", markers=True)
                fig.update_layout(height=380, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=10, r=10, t=20, b=10))
                safe_plotly_chart(fig, use_container_width=True)
            else:
                st.line_chart(lexical_df.set_index("created_at")["vocabulário_acumulado"])
            st.markdown("<div class='story-card'><div class='story-title'>expansão do vocabulário</div><div class='story-copy'>quando a curva sobe rápido, a camada pública está trazendo termos novos; quando estabiliza, a descrição converge ou se concentra em eixos já conhecidos.</div></div>", unsafe_allow_html=True)
    close_panel()


def render_admin_graph(store: JsonStore) -> None:
    open_panel("teia 3d do conhecimento", "rede espacial conectando obras, palavras, conceitos, metadados museológicos e open data externo.")
    graph = build_knowledge_graph(store)
    payload = _graph_payload(graph)
    fig = graph_to_plot_3d(payload, max_nodes=240)
    summaries = _analysis_summary_blocks(store, SemanticLearner(store))
    if fig is not None:
        safe_plotly_chart(fig, use_container_width=True)
    else:
        st.markdown("<div class='story-card'><div class='story-title'>visualização resumida da teia</div><div class='story-copy'>a teia tridimensional não foi carregada nesta execução, mas a estrutura conectiva segue disponível nos núcleos, metadados e palavras centrais abaixo.</div></div>", unsafe_allow_html=True)
    node_df = pd.DataFrame(payload.get("nodes", []))
    edge_df = pd.DataFrame(payload.get("edges", []))
    node_count = len(node_df)
    edge_count = len(edge_df)
    st.markdown(f"<div class='summary-block'><strong>rede conectada.</strong> {summaries['graph']} Nós {node_count} e arestas {edge_count}. A teia articula a marcação social com metadados museológicos, conceitos reconciliados e pontos externos de referência, formando um arranjo conectado e organizável para leitura curatorial.</div>", unsafe_allow_html=True)
    tabs = st.tabs(["relações dominantes", "open data e metadados", "palavras mais conectadas"])
    with tabs[0]:
        if not edge_df.empty and "relation" in edge_df.columns:
            relations = edge_df["relation"].value_counts().rename_axis("relação").reset_index(name="quantidade")
            render_bar_chart_df(relations.head(18), x="relação", y="quantidade", height=340)
            st.dataframe(relations.head(20), use_container_width=True, hide_index=True)
        else:
            st.info("sem relações suficientes para sintetizar.")
    with tabs[1]:
        works_df = to_dataframe(store.works())
        if not works_df.empty:
            cols = [c for c in ["title", "artist", "museum", "collection", "place", "period", "technique", "material", "external_reference_label"] if c in works_df.columns]
            st.dataframe(works_df[cols], use_container_width=True, hide_index=True)
        else:
            st.info("sem metadados suficientes.")
    with tabs[2]:
        counts = _edge_count_map(payload.get("edges", []))
        connected_rows = []
        for row in payload.get("nodes", []):
            nid = str(row.get("id", ""))
            connected_rows.append({"rótulo": row.get("label", ""), "tipo": row.get("kind", ""), "grau": counts.get(nid, 0)})
        connected_df = pd.DataFrame(connected_rows).sort_values("grau", ascending=False)
        if not connected_df.empty:
            render_bar_chart_df(connected_df.head(16), x="rótulo", y="grau", height=340)
            st.dataframe(connected_df.head(24), use_container_width=True, hide_index=True)
        else:
            st.info("sem nós conectados suficientes.")
    close_panel()


# fortalecimento do corpus de treino com metadados e conceitos
def _patched_build_training_corpus(self) -> pd.DataFrame:
    rows: List[Dict[str, str]] = []
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
        field_map = {
            "place": "lugar",
            "period": "periodo",
            "technique": "tecnica",
            "material": "material",
            "museum": "lugar",
            "collection": "tema",
        }
        for field, label in field_map.items():
            value = str(meta.get(field, "")).strip()
            if value:
                rows.append({"text": value, "label": label, "source": "metadata"})
                rows.append({"text": f"{value} {description}".strip(), "label": label, "source": "metadata_context"})
        artist = str(work.get("artist", "")).strip()
        if artist:
            rows.append({"text": artist, "label": "pessoa", "source": "artist"})
        for ext in meta.get("external_entities", []) or []:
            ext = str(ext).strip()
            if ext:
                rows.append({"text": ext, "label": "tema", "source": "open_data"})
    tag_index = {item.get("id"): item for item in self.store.tags()}
    for validation in self.store.validations():
        if validation.get("decision") not in {"approved", "auto-approved", "linked"}:
            continue
        tag_row = tag_index.get(validation.get("tag_id"))
        if not tag_row:
            continue
        entity = validation.get("validated_entity") or tag_row.get("entity_prediction") or "tema"
        tag_text = " ".join([str(tag_row.get("tag", "")).strip(), str(tag_row.get("comment", "")).strip()]).strip()
        if tag_text:
            rows.append({"text": tag_text, "label": entity, "source": "validation"})
        if validation.get("validated_concept_label"):
            rows.append({"text": validation.get("validated_concept_label"), "label": entity, "source": "validation_concept"})
        if validation.get("notes"):
            rows.append({"text": validation.get("notes"), "label": entity, "source": "validation_notes"})
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df = df[df["text"].astype(str).str.strip() != ""]
    return df.reset_index(drop=True)


SemanticLearner.build_training_corpus = _patched_build_training_corpus


def _legacy_main_2() -> None:
    render_css()
    render_css_patch_v3()
    store = JsonStore()
    init_session()
    ml = SemanticLearner(store)
    run_automation_engine(store, ml)

    if not st.session_state.get("intro_complete", False) and store.settings().get("public_intro_enabled", True):
        intro_flow(store)
        render_footer()
        return

    topbar(store)
    hero_panel(store)

    public_tabs = st.tabs(["explorar obras", "administração"])
    with public_tabs[0]:
        render_public_explore(store, ml)
    with public_tabs[1]:
        if not st.session_state.get("admin_authenticated", False):
            render_admin_login(store)
        else:
            admin_tabs = st.tabs(["painel geral", "validação", "conceitos", "machine learning", "análise temporal", "grafo", "dados e obras"])
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
            if st.button("sair da administração", use_container_width=True):
                st.session_state["admin_authenticated"] = False
                st.rerun()
    render_footer()



# patched below


def render_css_patch_v4() -> None:
    st.markdown("""
    <style>
    .hero-panel {display:none !important;}
    .story-copy {display:none !important;}
    .public-guide {
        margin: 0.4rem 0 1rem 0;
        color: #3a3a3a;
        font-size: 1.02rem;
        line-height: 1.7;
    }
    .public-grid-note {
        color: #555555;
        font-size: 0.92rem;
        margin-bottom: 0.9rem;
    }
    .work-card {
        min-height: 250px !important;
        padding: 0.65rem !important;
        border-radius: 22px !important;
        transition: transform 0.25s ease, box-shadow 0.25s ease, border-color 0.25s ease !important;
    }
    .work-card:hover {
        transform: translateY(-3px) !important;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.78), 0 16px 32px rgba(0,0,0,0.08) !important;
    }
    .work-card.is-selected {
        border: 1px solid rgba(55,55,55,0.22) !important;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.84), 0 18px 34px rgba(0,0,0,0.09) !important;
    }
    .work-card img {
        height: 210px !important;
        object-fit: cover !important;
        border-radius: 18px !important;
        cursor: pointer !important;
    }
    .public-image-click {
        text-align:center;
        color:#525252;
        font-size:0.86rem;
        margin-top:0.45rem;
        letter-spacing:0.01em;
    }
    .mini-tag-panel {
        margin-top: 0.65rem;
        padding: 0.8rem 0.9rem;
        border-radius: 18px;
        background: rgba(255,255,255,0.24);
        border: 1px solid rgba(255,255,255,0.58);
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.82), 0 12px 22px rgba(0,0,0,0.05);
    }
    .mini-tag-title {
        color: #222222;
        font-size: 0.95rem;
        font-weight: 700;
        margin-bottom: 0.45rem;
    }
    .mini-tag-help {
        color: #565656;
        font-size: 0.84rem;
        line-height: 1.5;
        margin-bottom: 0.55rem;
    }
    .tag-preview-wrap {
        display:flex;
        flex-wrap:wrap;
        gap:0.42rem;
        margin-top:0.7rem;
    }
    .tag-chip {
        display:inline-flex;
        align-items:center;
        gap:0.28rem;
        padding:0.36rem 0.7rem;
        border-radius:999px;
        background: rgba(255,255,255,0.55);
        color:#1f1f1f;
        border:1px solid rgba(255,255,255,0.8);
        font-size:0.82rem;
        font-weight:600;
    }
    .panel-title {
        color: #151515 !important;
    }
    .panel-subtitle {
        color: #555555 !important;
    }
    .summary-block,
    .story-card,
    .suggestion-card,
    .queue-card {
        background: rgba(255,255,255,0.20) !important;
        border: 1px solid rgba(255,255,255,0.56) !important;
        color: #222222 !important;
    }
    .story-title, .suggestion-title {
        color: #151515 !important;
    }
    .story-copy, .suggestion-meta, .queue-text {
        color: #404040 !important;
    }
    .stTextInput input,
    .stTextArea textarea,
    [data-baseweb="input"] input,
    [data-baseweb="textarea"] textarea {
        background: rgba(255,255,255,0.84) !important;
        color: #101010 !important;
        -webkit-text-fill-color: #101010 !important;
        caret-color: #101010 !important;
        border: 1px solid rgba(35,35,35,0.15) !important;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.95), 0 3px 10px rgba(0,0,0,0.04) !important;
        font-weight: 600 !important;
    }
    .stTextInput input::placeholder,
    .stTextArea textarea::placeholder {
        color: #6b6b6b !important;
        -webkit-text-fill-color: #6b6b6b !important;
        opacity: 1 !important;
    }
    .stButton button, button[kind="secondary"] {
        min-height: 2.7rem !important;
    }
    .tiny-action button {
        min-height: 2.2rem !important;
        font-size: 0.88rem !important;
    }
    .web-like-note {
        color:#474747;
        font-size:0.92rem;
        line-height:1.65;
        margin-top:0.55rem;
    }
    </style>
    """, unsafe_allow_html=True)


def hero_panel(store: JsonStore) -> None:
    return None


def render_footer() -> None:
    return None


def render_public_explore(store: JsonStore, ml: SemanticLearner) -> None:
    user = store.find_user(st.session_state.get("session_user_id", ""))
    works = store.works()
    open_panel("explorar obras", "toque em uma imagem para abrir um campo curto de marcação. os títulos e metadados ficam ocultos nesta etapa para não influenciar sua leitura.")
    if not user or not works:
        close_panel()
        return

    works = works[:3]
    st.markdown("<div class='public-guide'>Escolha uma imagem e escreva uma palavra ou pequena expressão que melhor represente o que você percebe nela.</div>", unsafe_allow_html=True)
    st.markdown("<div class='public-grid-note'>As informações analíticas e curatoriais ficam restritas à área administrativa. Aqui, o foco é apenas a sua marcação.</div>", unsafe_allow_html=True)

    selected_id = st.session_state.get("selected_work_id", "")
    cols = st.columns(3 if len(works) >= 3 else max(1, len(works)))
    for idx, work in enumerate(works):
        wid = work.get("id")
        is_selected = str(selected_id) == str(wid)
        with cols[idx % len(cols)]:
            st.markdown(f"<div class='work-card {'is-selected' if is_selected else ''}'>", unsafe_allow_html=True)
            st.image(work.get("image_url"), use_container_width=True)
            st.markdown("<div class='public-image-click'>clique abaixo para marcar esta imagem</div>", unsafe_allow_html=True)
            tiny_cols = st.columns([1, 1])
            with tiny_cols[0]:
                if st.button("marcar", key=f"public-open-v4-{wid}", use_container_width=True):
                    st.session_state["selected_work_id"] = wid
                    st.rerun()
            with tiny_cols[1]:
                if is_selected and st.button("fechar", key=f"public-close-v4-{wid}", use_container_width=True):
                    st.session_state["selected_work_id"] = ""
                    st.rerun()

            if is_selected:
                tags_df = build_tag_dataframe(store)
                mine = tags_df[(tags_df["work_id"] == wid) & (tags_df["user_id"] == user.get("id"))] if not tags_df.empty else pd.DataFrame()
                st.markdown("<div class='mini-tag-panel'>", unsafe_allow_html=True)
                st.markdown("<div class='mini-tag-title'>registre sua tag</div>", unsafe_allow_html=True)
                st.markdown("<div class='mini-tag-help'>Use uma palavra ou expressão curta. Você pode registrar mais de uma tag, uma por vez.</div>", unsafe_allow_html=True)
                with st.form(f"tag-form-inline-{wid}", clear_on_submit=True):
                    tag_value = st.text_input("sua tag", placeholder="ex.: silêncio, azul, movimento, retrato")
                    submitted = st.form_submit_button("registrar tag", use_container_width=True)
                    if submitted:
                        if not tag_value.strip():
                            st.warning("escreva uma tag antes de registrar.")
                        else:
                            store.submit_tag(wid, user.get("id"), tag_value, "", ml)
                            run_automation_engine(store, ml)
                            st.success("tag registrada.")
                            st.rerun()
                if not mine.empty:
                    mine_counts = mine["tag"].value_counts().reset_index()
                    mine_counts.columns = ["tag", "frequência"]
                    chips = "".join([f"<span class='tag-chip'>{row['tag']} · {int(row['frequência'])}</span>" for _, row in mine_counts.iterrows()])
                    st.markdown("<div class='mini-tag-help'>suas tags nesta imagem</div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='tag-preview-wrap'>{chips}</div>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

    close_panel()


def render_admin_graph(store: JsonStore) -> None:
    open_panel("teia 3d do conhecimento", "rede espacial de palavras, obras, conceitos, metadados museológicos e referências externas conectadas em uma única estrutura.")
    graph = build_knowledge_graph(store)
    payload = _graph_payload(graph)
    fig = graph_to_plot_3d(payload, max_nodes=260)
    summaries = _analysis_summary_blocks(store, SemanticLearner(store))
    node_df = pd.DataFrame(payload.get("nodes", []))
    edge_df = pd.DataFrame(payload.get("edges", []))
    node_count = len(node_df)
    edge_count = len(edge_df)

    st.markdown(
        f"<div class='summary-block'><strong>leitura integrada.</strong> {summaries['graph']} A rede atual reúne {node_count} nós e {edge_count} relações. O objetivo desta visualização é mostrar como a linguagem do público se liga aos metadados institucionais, aos conceitos reconciliados e às referências externas em um mesmo espaço analítico.</div>",
        unsafe_allow_html=True
    )

    if fig is not None:
        safe_plotly_chart(fig, use_container_width=True)

    tabs = st.tabs(["núcleos da rede", "metadados conectados", "palavras centrais"])
    with tabs[0]:
        if not edge_df.empty and "relation" in edge_df.columns:
            relations = edge_df["relation"].value_counts().rename_axis("relação").reset_index(name="quantidade")
            st.markdown("<div class='story-card'><div class='story-title'>ligações predominantes</div><div class='story-copy'>esta camada mostra quais tipos de relação mais sustentam a teia: marcação social, reconciliação conceitual, metadados museológicos e vínculos externos.</div></div>", unsafe_allow_html=True)
            render_bar_chart_df(relations.head(18), x="relação", y="quantidade", height=340)
        else:
            st.markdown("<div class='web-like-note'>A rede ainda está começando. Quando novas tags e validações entrarem, os núcleos da teia ficarão mais densos.</div>", unsafe_allow_html=True)
    with tabs[1]:
        works_df = to_dataframe(store.works())
        if not works_df.empty:
            view_cols = [c for c in ["title", "artist", "museum", "collection", "place", "period", "technique", "material", "external_reference_label"] if c in works_df.columns]
            st.markdown("<div class='story-card'><div class='story-title'>camadas documentais</div><div class='story-copy'>os metadados institucionais ajudam a estabilizar a leitura das tags e a aproximar a marcação livre de uma estrutura documental consistente.</div></div>", unsafe_allow_html=True)
            st.dataframe(works_df[view_cols], use_container_width=True, hide_index=True)
        else:
            st.markdown("<div class='web-like-note'>Ainda não há metadados suficientes cadastrados para esta leitura.</div>", unsafe_allow_html=True)
    with tabs[2]:
        counts = _edge_count_map(payload.get("edges", []))
        connected_rows = []
        for row in payload.get("nodes", []):
            nid = str(row.get("id", ""))
            connected_rows.append({"rótulo": row.get("label", ""), "tipo": row.get("kind", ""), "grau": counts.get(nid, 0)})
        connected_df = pd.DataFrame(connected_rows).sort_values("grau", ascending=False)
        if not connected_df.empty:
            st.markdown("<div class='story-card'><div class='story-title'>centros de gravidade vocabular</div><div class='story-copy'>os nós com maior grau funcionam como pontes entre obras, conceitos e descrições. Eles ajudam a encontrar convergências temáticas, redundâncias e ausências documentais.</div></div>", unsafe_allow_html=True)
            render_bar_chart_df(connected_df.head(16), x="rótulo", y="grau", height=340)
        else:
            st.markdown("<div class='web-like-note'>Ainda não há nós centrais suficientes para a leitura de centralidade.</div>", unsafe_allow_html=True)
    close_panel()


def render_admin_dashboard(store: JsonStore, ml: SemanticLearner) -> None:
    tags_df = build_tag_dataframe(store)
    works_df = to_dataframe(store.works())
    validations_df = to_dataframe(store.validations())
    concepts_df = to_dataframe(store.concepts())
    summaries = _analysis_summary_blocks(store, ml)

    total_tags = int(len(tags_df))
    unique_tags = int(tags_df["normalized_tag"].nunique()) if not tags_df.empty and "normalized_tag" in tags_df.columns else 0
    participants = int(tags_df["user_id"].nunique()) if not tags_df.empty and "user_id" in tags_df.columns else len(store.users())
    lexical_density = safe_float(unique_tags / total_tags, 0.0) if total_tags else 0.0
    open_panel("painel geral", "visão resumida do estado atual da documentação social, da validação curatorial e da aprendizagem do sistema.")
    html = f"""
    <div class="metric-strip">
        <div class="metric-card"><div class="metric-caption">obras</div><div class="metric-number">{len(works_df)}</div><div class="metric-note">imagens disponíveis</div></div>
        <div class="metric-card"><div class="metric-caption">tags</div><div class="metric-number">{total_tags}</div><div class="metric-note">marcações registradas</div></div>
        <div class="metric-card"><div class="metric-caption">validações</div><div class="metric-number">{len(validations_df)}</div><div class="metric-note">retorno curatorial</div></div>
        <div class="metric-card"><div class="metric-caption">conceitos</div><div class="metric-number">{len(concepts_df)}</div><div class="metric-note">camada reconciliada</div></div>
        <div class="metric-card"><div class="metric-caption">vocabulário registrado</div><div class="metric-number">{lexical_density:.2f}</div><div class="metric-note">termos distintos</div></div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)
    st.markdown(f"<div class='summary-block'><strong>resumo analítico.</strong> {summaries['validation']}</div>", unsafe_allow_html=True)

    col1, col2 = st.columns([1.15, 0.85])
    with col1:
        st.markdown("<div class='story-card'><div class='story-title'>o que observar neste painel</div><div class='story-copy'>acompanhe o crescimento das marcações, a diversidade do vocabulário, a necessidade de validação e as conexões que começam a surgir entre tags, conceitos e metadados.</div></div>", unsafe_allow_html=True)
        if not tags_df.empty:
            work_counts = tags_df.groupby("work_title").agg(tags=("id", "count")).reset_index().sort_values("tags", ascending=False)
            render_bar_chart_df(work_counts.head(12), x="work_title", y="tags", height=340)
    with col2:
        st.markdown("<div class='story-card'><div class='story-title'>aprendizagem em uso</div><div class='story-copy'>o sistema aprende com vocabulário seed, metadados das obras e validações administrativas. À medida que a base cresce, as previsões de entidade e as aproximações conceituais tendem a ficar mais estáveis.</div></div>", unsafe_allow_html=True)
        entity_df = pd.DataFrame()
        if not tags_df.empty and "entity_prediction" in tags_df.columns:
            entity_df = tags_df["entity_prediction"].replace("", "tema").value_counts().rename_axis("categoria").reset_index(name="frequência")
        if not entity_df.empty:
            render_bar_chart_df(entity_df.head(10), x="categoria", y="frequência", height=290)
    close_panel()


def _legacy_main_3() -> None:
    render_css()
    render_css_patch_v3()
    render_css_patch_v4()
    store = JsonStore()
    init_session()
    ml = SemanticLearner(store)
    run_automation_engine(store, ml)

    if not st.session_state.get("intro_complete", False) and store.settings().get("public_intro_enabled", True):
        intro_flow(store)
        return

    topbar(store)

    public_tabs = st.tabs(["explorar obras", "administração"])
    with public_tabs[0]:
        render_public_explore(store, ml)
    with public_tabs[1]:
        if not st.session_state.get("admin_authenticated", False):
            render_admin_login(store)
        else:
            admin_tabs = st.tabs(["painel geral", "validação", "conceitos", "machine learning", "análise temporal", "teia 3d", "dados e obras"])
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
            if st.button("sair da administração", use_container_width=True):
                st.session_state["admin_authenticated"] = False
                st.rerun()




def build_accessibility_context(store: JsonStore) -> Dict[str, Any]:
    works = store.works()
    if not works:
        return {"title": "", "text": "Nenhuma imagem está disponível no momento.", "gloss": "SEM IMAGEM", "work_id": ""}
    selected_id = str(st.session_state.get("selected_work_id", "") or "")
    selected = None
    for work in works:
        if str(work.get("id", "")) == selected_id:
            selected = work
            break
    if selected is None:
        selected = works[0]
    work_id = str(selected.get("id", ""))
    tags_df = build_tag_dataframe(store)
    user_id = st.session_state.get("session_user_id", "")
    mine = pd.DataFrame()
    if not tags_df.empty:
        mine = tags_df[(tags_df["work_id"].astype(str) == work_id)]
        if user_id and "user_id" in tags_df.columns:
            mine = mine[mine["user_id"].astype(str) == str(user_id)]
    my_tags = []
    if not mine.empty and "tag" in mine.columns:
        my_tags = mine["tag"].astype(str).tolist()[:8]
    inst_tags = selected.get("institutional_tags", []) or []
    meta_bits = [
        selected.get("artist", ""),
        selected.get("year", ""),
        selected.get("museum", ""),
        selected.get("period", ""),
        selected.get("technique", ""),
        selected.get("material", ""),
    ]
    meta_bits = [str(v).strip() for v in meta_bits if str(v).strip()]
    description = str(selected.get("description", "") or "").strip()
    tag_phrase = ", ".join(my_tags) if my_tags else "ainda sem marcações pessoais registradas"
    institutional_phrase = ", ".join(inst_tags[:6]) if inst_tags else "sem descritores institucionais visíveis"
    readable = []
    readable.append(f"Imagem selecionada: {selected.get('title', 'obra sem título')}. ")
    if description:
        readable.append(f"Descrição textual disponível: {description} ")
    if meta_bits:
        readable.append(f"Metadados de apoio: {'; '.join(meta_bits)}. ")
    readable.append(f"Suas tags atuais nesta imagem: {tag_phrase}. ")
    readable.append(f"Descritores institucionais relacionados: {institutional_phrase}. ")
    readable.append("Esta leitura acessível pode apoiar compreensão textual, locução e acompanhamento visual do conteúdo.")
    text_value = "".join(readable)
    gloss = libras_gloss(text_value)
    return {
        "title": str(selected.get("title", "obra")),
        "text": text_value,
        "gloss": gloss,
        "work_id": work_id,
        "image_url": str(selected.get("image_url", "")),
    }


def libras_gloss(text_value: str) -> str:
    stop = {
        "a", "o", "as", "os", "de", "da", "do", "das", "dos", "e", "é", "um", "uma", "para",
        "com", "em", "na", "no", "nas", "nos", "por", "que", "se", "ao", "aos", "à", "às",
    }
    normalized = normalize_text(text_value).upper().split()
    tokens = [token for token in normalized if token and token.lower() not in stop]
    if not tokens:
        return "SEM TEXTO"
    return " · ".join(tokens[:18])


def render_accessibility_css_patch() -> None:
    st.session_state.setdefault("font_scale", 1.0)
    st.session_state.setdefault("high_contrast", False)
    scale = float(st.session_state.get("font_scale", 1.0))
    contrast = bool(st.session_state.get("high_contrast", False))
    text0 = "#101010" if contrast else "#171717"
    text1 = "#191919" if contrast else "#242424"
    text2 = "#303030" if contrast else "#4a4a4a"
    bg = "rgba(255,255,255,0.28)" if contrast else "rgba(255,255,255,0.20)"
    border = "rgba(0,0,0,0.20)" if contrast else "rgba(255,255,255,0.52)"
    css = f"""
    <style>
    :root {{ --user-font-scale: {scale:.2f}; }}
    html, body, [class*='css'], [data-testid='stMarkdownContainer'], p, span, label, div, button, input, textarea, select {{
        font-size: calc(1rem * var(--user-font-scale));
    }}
    :root {{
        --glass: {bg};
        --glass-strong: rgba(255,255,255,0.34);
        --line: {border};
        --text-0: {text0};
        --text-1: {text1};
        --text-2: {text2};
    }}
    .access-card {{
        background: rgba(255,255,255,0.22);
        border: 1px solid rgba(255,255,255,0.45);
        border-radius: 22px;
        padding: 1rem 1.2rem;
        box-shadow: 0 16px 32px rgba(0,0,0,0.06);
        margin-bottom: 1rem;
    }}
    .access-title {{ font-size: 1.12rem; font-weight: 700; color: var(--text-0); margin-bottom: .35rem; }}
    .access-copy {{ color: var(--text-1); line-height: 1.65; }}
    .access-mini {{ color: var(--text-2); font-size: .95rem; line-height: 1.5; }}
    .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb='select'] > div {{
        color: #111111 !important;
        background: rgba(255,255,255,0.88) !important;
    }}
    .stTextArea textarea::placeholder, .stTextInput input::placeholder {{ color: #555555 !important; opacity: 1 !important; }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


def _escape_js(text_value: str) -> str:
    return json.dumps(text_value, ensure_ascii=False)


def render_accessibility_avatar(text_value: str, gloss: str) -> None:
    safe_text = _escape_js(text_value)
    safe_gloss = _escape_js(gloss)
    html = f"""
    <div style="background:rgba(255,255,255,.22);border:1px solid rgba(255,255,255,.45);border-radius:24px;padding:16px;box-shadow:0 18px 36px rgba(0,0,0,.06);">
      <div style="display:flex;gap:16px;align-items:center;flex-wrap:wrap;">
        <div style="flex:0 0 210px;display:flex;justify-content:center;align-items:center;">
          <div class="avatar-scene">
            <div class="avatar-wrap">
              <div class="avatar-head"><div class="eye left"></div><div class="eye right"></div><div class="mouth"></div></div>
              <div class="avatar-body"></div>
              <div class="avatar-arm left" id="armLeft"></div>
              <div class="avatar-arm right" id="armRight"></div>
            </div>
          </div>
        </div>
        <div style="flex:1 1 320px;min-width:240px;">
          <div style="font-family:'Times New Roman',serif;font-size:1.08rem;font-weight:700;color:#171717;margin-bottom:8px;">apoio acessível</div>
          <div id="speechText" style="font-family:'Times New Roman',serif;color:#2a2a2a;line-height:1.6;margin-bottom:10px;">{text_value}</div>
          <div style="font-family:'Times New Roman',serif;font-size:.95rem;color:#555;line-height:1.5;margin-bottom:12px;"><strong>glosa de apoio:</strong> {gloss}</div>
          <div style="display:flex;gap:10px;flex-wrap:wrap;">
            <button onclick="readText()" style="border:none;border-radius:999px;padding:10px 16px;background:#0e1a2c;color:#fff;font-family:'Times New Roman',serif;cursor:pointer;">ouvir texto</button>
            <button onclick="stopText()" style="border:none;border-radius:999px;padding:10px 16px;background:#dcdcdc;color:#111;font-family:'Times New Roman',serif;cursor:pointer;">parar</button>
            <button onclick="playGloss()" style="border:none;border-radius:999px;padding:10px 16px;background:#f0f0f0;color:#111;font-family:'Times New Roman',serif;cursor:pointer;">apoio libras</button>
          </div>
        </div>
      </div>
    </div>
    <style>
      .avatar-scene {{ width:180px; height:220px; perspective:800px; display:flex; align-items:center; justify-content:center; }}
      .avatar-wrap {{ position:relative; width:140px; height:200px; transform-style:preserve-3d; animation:spinSoft 7s ease-in-out infinite; }}
      .avatar-head {{ position:absolute; top:10px; left:35px; width:70px; height:70px; background:linear-gradient(145deg,#f3d2b6,#e7bf9a); border-radius:50%; box-shadow:inset -8px -6px 18px rgba(0,0,0,.10); transform:translateZ(24px); }}
      .eye {{ position:absolute; top:28px; width:8px; height:8px; background:#222; border-radius:50%; }}
      .eye.left {{ left:18px; }} .eye.right {{ right:18px; }}
      .mouth {{ position:absolute; left:24px; bottom:16px; width:22px; height:10px; border-bottom:3px solid #884d4d; border-radius:0 0 18px 18px; animation:talk 1.2s infinite ease-in-out; }}
      .avatar-body {{ position:absolute; top:76px; left:28px; width:84px; height:88px; border-radius:28px 28px 20px 20px; background:linear-gradient(145deg,#172742,#0e1a2c); transform:translateZ(10px); }}
      .avatar-arm {{ position:absolute; top:88px; width:18px; height:70px; border-radius:20px; background:linear-gradient(145deg,#1b2f4f,#101a2b); transform-origin:top center; }}
      .avatar-arm.left {{ left:16px; animation:armLeft 2s ease-in-out infinite; }}
      .avatar-arm.right {{ right:16px; animation:armRight 2s ease-in-out infinite; }}
      @keyframes spinSoft {{ 0%,100%{{transform:rotateY(-10deg)}} 50%{{transform:rotateY(10deg)}} }}
      @keyframes talk {{ 0%,100%{{transform:scaleY(1)}} 50%{{transform:scaleY(.55)}} }}
      @keyframes armLeft {{ 0%,100%{{transform:rotate(14deg)}} 50%{{transform:rotate(-28deg)}} }}
      @keyframes armRight {{ 0%,100%{{transform:rotate(-14deg)}} 50%{{transform:rotate(28deg)}} }}
    </style>
    <script>
      const fullText = {safe_text};
      const glossText = {safe_gloss};
      function readText() {{
        if ('speechSynthesis' in window) {{
          window.speechSynthesis.cancel();
          const utter = new SpeechSynthesisUtterance(fullText);
          utter.lang = 'pt-BR';
          utter.rate = 0.95;
          window.speechSynthesis.speak(utter);
        }}
      }}
      function stopText() {{ if ('speechSynthesis' in window) window.speechSynthesis.cancel(); }}
      function playGloss() {{
        const target = document.getElementById('speechText');
        if (!target) return;
        target.innerText = glossText;
        setTimeout(() => {{ target.innerText = fullText; }}, 6000);
      }}
    </script>
    """
    components.html(html, height=340)


def render_accessibility_hub(store: JsonStore) -> None:
    payload = build_accessibility_context(store)
    with st.expander("acessibilidade", expanded=False):
        c1, c2 = st.columns([0.92, 1.08])
        with c1:
            st.session_state["font_scale"] = st.slider("tamanho das letras", min_value=0.90, max_value=1.40, value=float(st.session_state.get("font_scale", 1.0)), step=0.05)
            st.session_state["high_contrast"] = st.toggle("contraste reforçado", value=bool(st.session_state.get("high_contrast", False)))
            st.markdown(f"<div class='access-card'><div class='access-title'>interpretação textual</div><div class='access-copy'>{payload['text']}</div></div>", unsafe_allow_html=True)
            st.markdown("<div class='access-card'><div class='access-title'>áudio descrição e leitura em voz alta</div><div class='access-mini'>Use os controles ao lado para ouvir a descrição da imagem selecionada. O avatar 3D de apoio também apresenta uma glosa visual resumida para acompanhamento.</div></div>", unsafe_allow_html=True)
        with c2:
            render_accessibility_avatar(payload["text"], payload["gloss"])


def _legacy_main_4() -> None:
    render_css()
    render_css_patch_v3()
    render_css_patch_v4()
    init_session()
    render_accessibility_css_patch()
    store = JsonStore()
    ml = SemanticLearner(store)
    run_automation_engine(store, ml)

    if not st.session_state.get("intro_complete", False) and store.settings().get("public_intro_enabled", True):
        intro_flow(store)
        return

    topbar(store)

    public_tabs = st.tabs(["explorar obras", "administração"])
    with public_tabs[0]:
        render_accessibility_hub(store)
        render_public_explore(store, ml)
    with public_tabs[1]:
        if not st.session_state.get("admin_authenticated", False):
            render_admin_login(store)
        else:
            admin_tabs = st.tabs(["painel geral", "validação", "conceitos", "machine learning", "análise temporal", "teia 3d", "dados e obras"])
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
            if st.button("sair da administração", use_container_width=True):
                st.session_state["admin_authenticated"] = False
                st.rerun()




# ===== OVERRIDE FINAL: interface focada no pedido do usuário =====

def render_admin_dashboard(store: JsonStore, ml: SemanticLearner) -> None:
    tags_df = to_dataframe(store.tags())
    works_df = to_dataframe(store.works())
    validations_df = to_dataframe(store.validations())
    summaries = _analysis_summary_blocks(store, ml)

    total_tags = int(len(tags_df))
    participants = int(tags_df["user_id"].nunique()) if not tags_df.empty and "user_id" in tags_df.columns else len(store.users())
    pending = int((validations_df["decision"].astype(str).str.lower() == "pending").sum()) if not validations_df.empty and "decision" in validations_df.columns else 0
    approved = int((validations_df["decision"].astype(str).str.lower() == "approved").sum()) if not validations_df.empty and "decision" in validations_df.columns else 0
    search_ready = int(tags_df["normalized_tag"].astype(str).nunique()) if not tags_df.empty and "normalized_tag" in tags_df.columns else 0

    open_panel("painel geral", "acompanhe o que foi coletado, o que está pendente de supervisão e como a busca conectada está sendo formada a partir de metadados, tags livres e validações.")
    html = f"""
    <div class="metric-strip">
        <div class="metric-card"><div class="metric-caption">obras</div><div class="metric-number">{len(works_df)}</div><div class="metric-note">itens monitorados</div></div>
        <div class="metric-card"><div class="metric-caption">tags coletadas</div><div class="metric-number">{total_tags}</div><div class="metric-note">entrada do público</div></div>
        <div class="metric-card"><div class="metric-caption">participantes</div><div class="metric-number">{participants}</div><div class="metric-note">sessões registradas</div></div>
        <div class="metric-card"><div class="metric-caption">fila curatorial</div><div class="metric-number">{pending}</div><div class="metric-note">itens pendentes</div></div>
        <div class="metric-card"><div class="metric-caption">busca conectada</div><div class="metric-number">{search_ready}</div><div class="metric-note">termos prontos para recuperação</div></div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)
    st.markdown(f"<div class='summary-block'><strong>síntese da supervisão.</strong> {summaries.get('validation','sem dados suficientes no momento.')}</div>", unsafe_allow_html=True)

    c1, c2 = st.columns([1.1, 0.9])
    with c1:
        st.markdown("<div class='story-card'><div class='story-title'>foco deste painel</div><div class='story-copy'>o objetivo aqui não é medir vocabulário registrado, mas acompanhar coleta, validação, preenchimento, comparativos entre obras e consolidação da busca documental. as marcações do público entram, passam por verificação, comparação com metadados e podem voltar para supervisão curatorial.</div></div>", unsafe_allow_html=True)
        if not tags_df.empty and 'work_title' in tags_df.columns:
            work_counts = tags_df.groupby('work_title').agg(tags=('id','count')).reset_index().sort_values('tags', ascending=False)
            work_counts.columns = ['obra','tags coletadas']
            render_bar_chart_df(work_counts.head(10), x='obra', y='tags coletadas', height=320)
    with c2:
        st.markdown(f"<div class='story-card'><div class='story-title'>estado da validação</div><div class='story-copy'>validações concluídas {approved}<br>pendências {pending}<br>termos integrados à busca {search_ready}<br>aprendizado incremental ativo {ml.entity_accuracy:.2f}</div></div>", unsafe_allow_html=True)
        if not tags_df.empty and 'entity_prediction' in tags_df.columns:
            entity_df = tags_df['entity_prediction'].replace('', 'tema').astype(str).value_counts().rename_axis('categoria').reset_index(name='ocorrências')
            render_bar_chart_df(entity_df.head(8), x='categoria', y='ocorrências', height=280)
    close_panel()


def render_admin_ml_focus(store: JsonStore, ml: SemanticLearner) -> None:
    open_panel("compreensão de linguagem natural e aprendizagem", "o mecanismo aprende com descrições, metadados museológicos, tags institucionais, tags livres e validações curatoriais, aproximando-se da lógica de reconhecimento de entidades, desambiguação e supervisão progressiva descrita para o caso do Prado.")
    tags_df = to_dataframe(store.tags())
    works_df = to_dataframe(store.works())
    validations_df = to_dataframe(store.validations())
    st.markdown("<div class='summary-block'><strong>como o mecanismo aprende.</strong> A cada nova validação, o sistema reaproveita o termo marcado, os metadados da obra, os vínculos com museu, técnica, material, período e os exemplos anteriores para melhorar a sugestão de categoria e conceito. A meta é reduzir supervisão intensiva ao longo do tempo, sem eliminar a revisão documental.</div>", unsafe_allow_html=True)
    examples = []
    if not tags_df.empty:
        sample = tags_df.head(3)
        for _, row in sample.iterrows():
            examples.append({
                'tag': row.get('tag',''),
                'obra': row.get('work_title',''),
                'previsão': row.get('entity_prediction',''),
                'conceito': row.get('concept_label',''),
                'museu': row.get('work_museum',''),
            })
    if examples:
        st.markdown("#### exemplos de aprendizagem")
        st.dataframe(pd.DataFrame(examples), use_container_width=True, hide_index=True)
    if not works_df.empty:
        search_rows = []
        for _, row in works_df.head(12).iterrows():
            search_rows.append({
                'obra': row.get('title',''),
                'artista': row.get('artist',''),
                'museu': row.get('museum',''),
                'período': row.get('period',''),
                'técnica': row.get('technique',''),
                'material': row.get('material',''),
            })
        st.markdown("#### campos usados na busca conectada")
        st.dataframe(pd.DataFrame(search_rows), use_container_width=True, hide_index=True)
    close_panel()


def render_admin_temporal_focus(store: JsonStore, ml: SemanticLearner) -> None:
    tags_df = to_dataframe(store.tags())
    open_panel("análise temporal", "acompanhe as tags criadas por dia, mês e ano, com detalhamento do que apareceu em cada período e quais obras concentraram maior circulação de informação.")
    if tags_df.empty or 'created_at' not in tags_df.columns:
        st.info('ainda não há tags suficientes para leitura temporal.')
        close_panel()
        return
    frame = tags_df.copy()
    frame['created_at'] = pd.to_datetime(frame['created_at'], errors='coerce')
    frame = frame.dropna(subset=['created_at'])
    if frame.empty:
        st.info('os registros temporais ainda não estão completos.')
        close_panel()
        return
    frame['dia'] = frame['created_at'].dt.date.astype(str)
    frame['mes'] = frame['created_at'].dt.to_period('M').astype(str)
    frame['ano'] = frame['created_at'].dt.year.astype(str)
    t1, t2, t3 = st.tabs(['por dia', 'por mês', 'por ano'])
    with t1:
        day_counts = frame.groupby('dia').agg(tags=('id','count')).reset_index().sort_values('dia')
        render_line_chart_df(day_counts, x='dia', y='tags', height=300)
        detail = frame.groupby('dia').agg(tags=('tag', lambda x: ', '.join(pd.Series(x).astype(str).head(12))), total=('id','count')).reset_index().sort_values('dia', ascending=False)
        st.dataframe(detail, use_container_width=True, hide_index=True)
    with t2:
        month_counts = frame.groupby('mes').agg(tags=('id','count')).reset_index().sort_values('mes')
        render_bar_chart_df(month_counts, x='mes', y='tags', height=300)
        detail = frame.groupby('mes').agg(tags=('tag', lambda x: ', '.join(pd.Series(x).astype(str).head(12))), total=('id','count')).reset_index().sort_values('mes', ascending=False)
        st.dataframe(detail, use_container_width=True, hide_index=True)
    with t3:
        year_counts = frame.groupby('ano').agg(tags=('id','count')).reset_index().sort_values('ano')
        render_bar_chart_df(year_counts, x='ano', y='tags', height=260)
        detail = frame.groupby('ano').agg(tags=('tag', lambda x: ', '.join(pd.Series(x).astype(str).head(12))), total=('id','count')).reset_index().sort_values('ano', ascending=False)
        st.dataframe(detail, use_container_width=True, hide_index=True)
    close_panel()


def _legacy_main_5() -> None:
    render_css()
    render_css_patch_v3()
    render_css_patch_v4()
    init_session()
    render_accessibility_css_patch()
    store = JsonStore()
    ml = SemanticLearner(store)
    run_automation_engine(store, ml)

    if not st.session_state.get('intro_complete', False) and store.settings().get('public_intro_enabled', True):
        intro_flow(store)
        return

    topbar(store)

    public_tabs = st.tabs(['explorar obras', 'administração'])
    with public_tabs[0]:
        render_public_explore(store, ml)
        render_accessibility_hub(store)
    with public_tabs[1]:
        if not st.session_state.get('admin_authenticated', False):
            render_admin_login(store)
        else:
            admin_tabs = st.tabs(['painel', 'validação', 'busca e aprendizagem', 'análise temporal', 'teia 3d', 'dados e obras'])
            with admin_tabs[0]:
                render_admin_dashboard(store, ml)
            with admin_tabs[1]:
                render_admin_validation(store, ml)
                render_admin_concepts(store, ml)
            with admin_tabs[2]:
                render_admin_ml_focus(store, ml)
            with admin_tabs[3]:
                render_admin_temporal_focus(store, ml)
            with admin_tabs[4]:
                render_admin_graph(store)
            with admin_tabs[5]:
                render_admin_data(store, ml)
            if st.button('sair da administração', use_container_width=True):
                st.session_state['admin_authenticated'] = False
                st.rerun()




# ===== OVERRIDE FINAL 2: foco real em validação, temporalidade, acessibilidade e teia 3D =====

def intro_flow(store: JsonStore) -> None:
    st.markdown("<div style='height:.35rem'></div>", unsafe_allow_html=True)
    st.markdown("<div class='panel' style='padding:1.3rem 1.3rem 1rem 1.3rem'><div class='panel-title'>questionário inicial</div><div class='panel-subtitle'>responda às três perguntas para liberar a marcação das imagens.</div>", unsafe_allow_html=True)

    st.session_state.setdefault("intro_familiarity", "nunca")
    st.session_state.setdefault("intro_documentation", "nenhum")
    st.session_state.setdefault("intro_understanding", "")

    c1, c2 = st.columns(2)
    with c1:
        familiarity = st.selectbox(
            "1. qual é a sua frequência de visita a museus?",
            ["nunca", "raramente", "ocasionalmente", "frequentemente"],
            key="intro_familiarity",
        )
        documentation = st.selectbox(
            "2. você já ouviu falar sobre documentação museológica?",
            ["nenhum", "básico", "intermediário", "avançado"],
            key="intro_documentation",
        )
    with c2:
        understanding = st.text_area(
            "3. o que você entende por tags aplicadas a acervos?",
            height=180,
            placeholder="descreva com suas palavras",
            key="intro_understanding",
        )

    if st.button("liberar acesso às obras", key="intro_submit", use_container_width=True):
        if not str(understanding).strip():
            st.warning("preencha a terceira resposta para continuar.")
        else:
            user = store.create_or_get_user(familiarity, documentation, understanding)
            if isinstance(user, dict):
                uid = str(user.get("id") or user.get("user_id") or "")
                if uid:
                    st.session_state["session_user_id"] = uid
            st.session_state["intro_complete"] = True
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def _public_user(store: JsonStore) -> Optional[Dict[str, Any]]:
    uid = str(st.session_state.get("session_user_id", "") or "")
    if not uid:
        return None
    return store.find_user(uid)


def render_public_explore(store: JsonStore, ml: SemanticLearner) -> None:
    user = _public_user(store)
    works = store.works()[:3]
    if not user or not works:
        st.info("nenhuma obra está disponível no momento.")
        return

    tags_df = build_tag_dataframe(store)
    cols = st.columns(3 if len(works) >= 3 else max(1, len(works)))
    for idx, work in enumerate(works):
        wid = str(work.get("id", ""))
        with cols[idx % len(cols)]:
            st.markdown("<div class='work-card' style='padding:.55rem'>", unsafe_allow_html=True)
            st.image(work.get("image_url"), use_container_width=True)
            if st.button("Marcar", key=f"public_mark_{wid}", use_container_width=True):
                st.session_state["selected_work_id"] = wid
                st.rerun()
            if str(st.session_state.get("selected_work_id", "")) == wid:
                st.markdown("<div class='tag-compact-box' style='margin-top:.65rem;padding:.8rem'>", unsafe_allow_html=True)
                tag_value = st.text_input(
                    "sua tag",
                    key=f"tag_inline_{wid}",
                    placeholder="escreva uma palavra ou pequena expressão",
                    label_visibility="collapsed",
                )
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("Registrar", key=f"save_inline_{wid}", use_container_width=True):
                        if not str(tag_value).strip():
                            st.warning("escreva uma tag para registrar.")
                        else:
                            store.submit_tag(wid, user.get("id"), tag_value, "", ml)
                            run_automation_engine(store, ml)
                            st.session_state[f"tag_inline_{wid}"] = ""
                            st.rerun()
                with c2:
                    if st.button("Fechar", key=f"close_inline_{wid}", use_container_width=True):
                        st.session_state["selected_work_id"] = ""
                        st.rerun()
                mine = pd.DataFrame()
                if not tags_df.empty:
                    mine = tags_df[(tags_df["work_id"].astype(str) == wid) & (tags_df["user_id"].astype(str) == str(user.get("id", "")))]
                if not mine.empty:
                    counts = mine["tag"].astype(str).value_counts().reset_index()
                    counts.columns = ["tag", "frequência"]
                    st.markdown("<div class='tag-mini-note'>suas tags nesta imagem</div>", unsafe_allow_html=True)
                    st.markdown("<div class='tag-preview-wrap'>" + "".join([f"<span class='tag-chip'>{row['tag']} {int(row['frequência'])}</span>" for _, row in counts.iterrows()]) + "</div>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)


def _connected_search(store: JsonStore, query: str) -> pd.DataFrame:
    qn = normalize_text(query)
    if not qn:
        return pd.DataFrame()
    tags_df = build_tag_dataframe(store)
    works_df = to_dataframe(store.works())
    concepts_df = to_dataframe(store.concepts())
    rows: List[Dict[str, Any]] = []
    if not tags_df.empty:
        for _, row in tags_df.iterrows():
            hay = " ".join([
                str(row.get("tag", "")), str(row.get("normalized_tag", "")), str(row.get("work_title", "")),
                str(row.get("work_artist", "")), str(row.get("work_museum", "")), str(row.get("work_place", "")),
                str(row.get("work_period", "")), str(row.get("work_technique", "")), str(row.get("work_material", "")),
                str(row.get("concept_resolved_label", "")), str(row.get("validated_concept_label", "")), str(row.get("validated_entity", "")),
            ])
            hn = normalize_text(hay)
            score = 0.0
            if qn in hn:
                score += 1.0
            score += similarity_score(qn, str(row.get("tag", "")))
            score += similarity_score(qn, str(row.get("concept_resolved_label", "")))
            score += 0.6 * similarity_score(qn, str(row.get("work_title", "")))
            score += 0.4 * similarity_score(qn, str(row.get("work_artist", "")))
            score += 0.3 * similarity_score(qn, str(row.get("work_material", "")))
            score += 0.3 * similarity_score(qn, str(row.get("work_technique", "")))
            if score > 0.35:
                rows.append({
                    "tipo": "tag",
                    "score": round(score, 3),
                    "entrada": row.get("tag", ""),
                    "obra": row.get("work_title", ""),
                    "artista": row.get("work_artist", ""),
                    "museu": row.get("work_museum", ""),
                    "categoria_prevista": row.get("entity_prediction", ""),
                    "conceito": row.get("concept_resolved_label", "") or row.get("validated_concept_label", ""),
                })
    if not works_df.empty:
        for _, row in works_df.iterrows():
            hay = " ".join([str(row.get(c, "")) for c in ["title", "artist", "museum", "collection", "place", "period", "technique", "material", "description"]])
            hn = normalize_text(hay)
            score = 0.0
            if qn in hn:
                score += 1.0
            for c, w in [("title", 0.9), ("artist", 0.7), ("museum", 0.6), ("period", 0.6), ("technique", 0.6), ("material", 0.6), ("place", 0.5), ("description", 0.4)]:
                score += w * similarity_score(qn, str(row.get(c, "")))
            if score > 0.4:
                rows.append({
                    "tipo": "metadado",
                    "score": round(score, 3),
                    "entrada": row.get("title", ""),
                    "obra": row.get("title", ""),
                    "artista": row.get("artist", ""),
                    "museu": row.get("museum", ""),
                    "categoria_prevista": "metadado",
                    "conceito": row.get("period", "") or row.get("technique", "") or row.get("material", ""),
                })
    if not concepts_df.empty:
        for _, row in concepts_df.iterrows():
            label = str(row.get("label", ""))
            score = similarity_score(qn, label)
            if qn in normalize_text(label):
                score += 1.0
            if score > 0.4:
                rows.append({
                    "tipo": "conceito",
                    "score": round(score, 3),
                    "entrada": label,
                    "obra": "",
                    "artista": "",
                    "museu": "",
                    "categoria_prevista": row.get("category", ""),
                    "conceito": label,
                })
    if not rows:
        return pd.DataFrame(columns=["tipo", "score", "entrada", "obra", "artista", "museu", "categoria_prevista", "conceito"])
    return pd.DataFrame(rows).sort_values(["score", "tipo"], ascending=[False, True]).head(30)


def render_admin_dashboard(store: JsonStore, ml: SemanticLearner) -> None:
    tags_df = build_tag_dataframe(store)
    works_df = to_dataframe(store.works())
    validations_df = to_dataframe(store.validations())
    total_tags = int(len(tags_df)) if not tags_df.empty else 0
    participants = int(tags_df["user_id"].nunique()) if not tags_df.empty and "user_id" in tags_df.columns else len(store.users())
    pending = int((validations_df.get("decision", pd.Series(dtype=str)).astype(str).str.lower() == "pending").sum()) if not validations_df.empty else 0
    approved = int((validations_df.get("decision", pd.Series(dtype=str)).astype(str).str.lower().isin(["approved", "linked", "auto-approved"])) .sum()) if not validations_df.empty else 0
    search_terms = int(tags_df.get("normalized_tag", pd.Series(dtype=str)).astype(str).nunique()) if not tags_df.empty else 0
    open_panel("painel", "acompanhe o que foi coletado, o que está em validação e o que já pode circular na busca conectada entre metadados, tags e conceitos.")
    st.markdown(f"""
    <div class='metric-strip'>
        <div class='metric-card'><div class='metric-caption'>obras</div><div class='metric-number'>{len(works_df)}</div><div class='metric-note'>itens monitorados</div></div>
        <div class='metric-card'><div class='metric-caption'>tags coletadas</div><div class='metric-number'>{total_tags}</div><div class='metric-note'>entrada do público</div></div>
        <div class='metric-card'><div class='metric-caption'>participantes</div><div class='metric-number'>{participants}</div><div class='metric-note'>sessões registradas</div></div>
        <div class='metric-card'><div class='metric-caption'>fila curatorial</div><div class='metric-number'>{pending}</div><div class='metric-note'>aguardando supervisão</div></div>
        <div class='metric-card'><div class='metric-caption'>termos na busca</div><div class='metric-number'>{search_terms}</div><div class='metric-note'>vocabulário recuperável</div></div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown(f"<div class='summary-block'><strong>síntese do acompanhamento.</strong> validações concluídas {approved}. pendências {pending}. o painel prioriza coleta, supervisão, recuperação e circulação de informação entre a linguagem do público e os metadados institucionais.</div>", unsafe_allow_html=True)
    c1, c2 = st.columns([1.1, 0.9])
    with c1:
        st.markdown("<div class='story-card'><div class='story-title'>o que a instituição coleta</div><div class='story-copy'>acompanhe onde há mais marcações, onde surgem conflitos de preenchimento, quais obras concentram vocabulário social e onde ainda faltam campos para estabilizar a documentação.</div></div>", unsafe_allow_html=True)
        if not tags_df.empty and 'work_title' in tags_df.columns:
            flow = tags_df.groupby('work_title').agg(tags=('id','count')).reset_index().sort_values('tags', ascending=False)
            flow.columns = ['obra', 'tags coletadas']
            render_bar_chart_df(flow.head(10), x='obra', y='tags coletadas', height=320)
    with c2:
        st.markdown("<div class='story-card'><div class='story-title'>busca documental em formação</div><div class='story-copy'>cada validação devolve ao sistema exemplos que aproximam tags livres, conceitos e metadados. a meta é fazer a busca encontrar obra, artista, técnica, material, lugar e tema a partir das expressões usadas pelas pessoas.</div></div>", unsafe_allow_html=True)
        if not tags_df.empty and 'entity_prediction' in tags_df.columns:
            entity_df = tags_df['entity_prediction'].replace('', 'tema').astype(str).value_counts().rename_axis('categoria').reset_index(name='ocorrências')
            render_bar_chart_df(entity_df.head(8), x='categoria', y='ocorrências', height=280)
    close_panel()


def render_admin_ml_focus(store: JsonStore, ml: SemanticLearner) -> None:
    tags_df = build_tag_dataframe(store)
    open_panel("busca e aprendizagem", "o mecanismo aprende com metadados, tags criadas, conceitos validados e exemplos curatoriais para melhorar a recuperação e a leitura das marcações.")
    st.markdown("<div class='summary-block'><strong>aprendizagem em uso.</strong> esta área aproxima o comportamento descrito para o caso do Prado: reconhecimento de entidades, desambiguação, aproximação conceitual, revisão progressiva e redução de erro por supervisão continuada.</div>", unsafe_allow_html=True)
    query = st.text_input("buscar na rede documental", placeholder="busque por tema, material, técnica, artista, lugar, museu ou uma tag criada pelo público", key="connected_search_input")
    if query.strip():
        results = _connected_search(store, query)
        if results.empty:
            st.info("nenhuma conexão forte apareceu com este termo ainda.")
        else:
            st.markdown("#### resultados conectados")
            st.dataframe(results, use_container_width=True, hide_index=True)
            st.markdown(f"<div class='story-card'><div class='story-title'>síntese da busca</div><div class='story-copy'>o termo procurado cruzou metadados institucionais, tags públicas e conceitos reconciliados. os resultados acima mostram por onde a busca já consegue circular com base no que foi aprendido até agora.</div></div>", unsafe_allow_html=True)
    if not tags_df.empty:
        sample = tags_df[['tag','work_title','entity_prediction','concept_resolved_label','work_museum','work_period','work_technique','work_material']].head(12).copy()
        sample.columns = ['tag criada', 'obra', 'categoria sugerida', 'conceito', 'museu', 'período', 'técnica', 'material']
        st.markdown("#### exemplos usados para aprender")
        st.dataframe(sample, use_container_width=True, hide_index=True)
    close_panel()


def render_admin_temporal_focus(store: JsonStore, ml: SemanticLearner) -> None:
    tags_df = build_tag_dataframe(store)
    open_panel("análise temporal", "acompanhe as tags criadas por dia, mês e ano, vendo o que apareceu em cada período e como a circulação de termos vai se consolidando.")
    if tags_df.empty or 'created_ts' not in tags_df.columns:
        st.info('ainda não há marcações suficientes para a leitura temporal.')
        close_panel()
        return
    frame = tags_df.copy()
    frame['created_ts'] = pd.to_datetime(frame['created_ts'], errors='coerce')
    frame = frame.dropna(subset=['created_ts'])
    if frame.empty:
        st.info('os registros temporais ainda não estão completos.')
        close_panel()
        return
    frame['dia'] = frame['created_ts'].dt.strftime('%Y-%m-%d')
    frame['mes'] = frame['created_ts'].dt.strftime('%Y-%m')
    frame['ano'] = frame['created_ts'].dt.strftime('%Y')
    t1, t2, t3 = st.tabs(['por dia', 'por mês', 'por ano'])
    def detail_block(df, period_col, limit=8):
        grouped = df.groupby(period_col).agg(total=('id','count')).reset_index().sort_values(period_col, ascending=False)
        for _, period in grouped.head(limit).iterrows():
            p = period[period_col]
            subset = df[df[period_col] == p]
            top_tags = subset['tag'].astype(str).value_counts().head(8)
            works = subset['work_title'].astype(str).value_counts().head(3)
            tags_line = ' · '.join([f"{k} {v}" for k, v in top_tags.items()]) or 'sem detalhamento'
            works_line = ' · '.join([f"{k} {v}" for k, v in works.items()]) or 'sem obras destacadas'
            st.markdown(f"<div class='story-card'><div class='story-title'>{p}</div><div class='story-copy'>tags registradas {int(len(subset))}<br>termos observados {tags_line}<br>obras em destaque {works_line}</div></div>", unsafe_allow_html=True)
    with t1:
        day_counts = frame.groupby('dia').agg(tags=('id','count')).reset_index().sort_values('dia')
        render_line_chart_df(day_counts, x='dia', y='tags', height=280)
        detail_block(frame, 'dia', limit=10)
    with t2:
        month_counts = frame.groupby('mes').agg(tags=('id','count')).reset_index().sort_values('mes')
        render_bar_chart_df(month_counts, x='mes', y='tags', height=280)
        detail_block(frame, 'mes', limit=8)
    with t3:
        year_counts = frame.groupby('ano').agg(tags=('id','count')).reset_index().sort_values('ano')
        render_bar_chart_df(year_counts, x='ano', y='tags', height=240)
        detail_block(frame, 'ano', limit=6)
    close_panel()


def render_admin_graph(store: JsonStore) -> None:
    open_panel("teia 3d", "rede de compartilhamento e interoperabilidade entre obra, artista, museu, coleção, lugar, período, técnica, material, tags, conceitos e referências externas. arraste a teia para explorar as conexões em três dimensões.")
    graph = build_knowledge_graph(store)
    payload = _graph_payload(graph)
    fig = graph_to_plot_3d(payload, max_nodes=280)
    node_count = len(payload.get('nodes', []))
    edge_count = len(payload.get('edges', []))
    st.markdown(f"<div class='summary-block'><strong>rede conectada.</strong> a teia atual reúne {node_count} nós e {edge_count} relações. o foco aqui é mostrar circulação, interoperabilidade e compartilhamento de informação entre metadados da instituição, linguagem do público, conceitos reconciliados e referências externas.</div>", unsafe_allow_html=True)
    if fig is not None:
        safe_plotly_chart(fig, use_container_width=True)
    else:
        st.info('a teia 3d precisa do plotly para ser exibida nesta execução.')
    edge_df = pd.DataFrame(payload.get('edges', []))
    if not edge_df.empty and 'relation' in edge_df.columns:
        rel = edge_df['relation'].astype(str).value_counts().head(12)
        st.markdown("<div class='story-card'><div class='story-title'>ligações ativas na teia</div><div class='story-copy'>" + ' · '.join([f"{k} {v}" for k, v in rel.items()]) + "</div></div>", unsafe_allow_html=True)
    close_panel()


def main() -> None:
    render_css()
    render_css_patch_v3()
    render_css_patch_v4()
    render_accessibility_css_patch()
    init_session()
    store = JsonStore()
    ml = SemanticLearner(store)
    run_automation_engine(store, ml)

    if not st.session_state.get('intro_complete', False) and store.settings().get('public_intro_enabled', True):
        intro_flow(store)
        return

    topbar(store)
    public_tabs = st.tabs(['explorar obras', 'administração'])
    with public_tabs[0]:
        render_public_explore(store, ml)
        render_accessibility_hub(store)
    with public_tabs[1]:
        if not st.session_state.get('admin_authenticated', False):
            render_admin_login(store)
        else:
            admin_tabs = st.tabs(['painel', 'validação', 'busca e aprendizagem', 'análise temporal', 'teia 3d', 'dados e obras'])
            with admin_tabs[0]:
                render_admin_dashboard(store, ml)
            with admin_tabs[1]:
                render_admin_validation(store, ml)
                render_admin_concepts(store, ml)
            with admin_tabs[2]:
                render_admin_ml_focus(store, ml)
            with admin_tabs[3]:
                render_admin_temporal_focus(store, ml)
            with admin_tabs[4]:
                render_admin_graph(store)
            with admin_tabs[5]:
                render_admin_data(store, ml)
            if st.button('sair da administração', key='admin_logout_final', use_container_width=True):
                st.session_state['admin_authenticated'] = False
                st.rerun()

if __name__ == '__main__':
    main()
