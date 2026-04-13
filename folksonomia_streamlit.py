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
    --text-0: #1b1b1b;
    --text-1: #2e2e2e;
    --text-2: #555555;
    --shadow-soft: 0 18px 44px rgba(0,0,0,0.08);
    --shadow-hover: 0 24px 54px rgba(0,0,0,0.12);
}
html, body, [class*="css"], [data-testid="stMarkdownContainer"], .st-emotion-cache-10trblm, .st-emotion-cache-16idsys, p, span, label, div {
    font-family: "Times New Roman", Georgia, "Cormorant Garamond", serif !important;
}
@keyframes liquidShift {
    0% { background-position: 0% 50%, 100% 0%, 0% 100%, 50% 50%; }
    50% { background-position: 100% 50%, 0% 100%, 100% 0%, 50% 50%; }
    100% { background-position: 0% 50%, 100% 0%, 0% 100%, 50% 50%; }
}
@keyframes cardFloat {
    0% { transform: translateY(0px); }
    50% { transform: translateY(-4px); }
    100% { transform: translateY(0px); }
}
@keyframes shinePass {
    0% { left: -120%; }
    100% { left: 120%; }
}
body {
    background: linear-gradient(130deg, #dadada 0%, #eeeeee 30%, #f8f8f8 58%, #d9d9d9 100%);
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
.brand-title { font-family: "Times New Roman", Georgia, serif; font-size: 2rem; font-weight: 700; letter-spacing: -0.05em; text-transform: lowercase; color: #1a1a1a; }
.brand-subtitle { font-size: 0.76rem; color: #5f5f5f; letter-spacing: 0.18em; text-transform: uppercase; }
.status-chip {
    display: inline-flex; align-items: center; min-height: 36px; padding: 0.6rem 1rem; border-radius: 999px;
    background: rgba(255,255,255,0.22); border: 1px solid rgba(255,255,255,0.52); color: #414141; font-size: 0.82rem;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.64); backdrop-filter: blur(18px);
}
.hero-panel, .panel {
    background: rgba(255,255,255,0.22); border: 1px solid rgba(255,255,255,0.56);
    border-radius: 30px; backdrop-filter: blur(28px) saturate(168%); -webkit-backdrop-filter: blur(28px) saturate(168%);
    box-shadow: 0 20px 52px rgba(0,0,0,0.10), inset 0 1px 0 rgba(255,255,255,0.76);
}
.hero-panel { padding: 2rem; margin-top: 1rem; }
.hero-grid { display: grid; grid-template-columns: 1.15fr 0.85fr; gap: 1.2rem; }
.hero-kicker { font-size: 0.84rem; text-transform: uppercase; letter-spacing: 0.20em; color: #6b6b6b; }
.hero-title { font-family: "Times New Roman", Georgia, serif; font-size: 4.2rem; line-height: 0.92; letter-spacing: -0.06em; color: #1f1f1f; }
.hero-copy { margin-top: 1rem; font-size: 1rem; line-height: 1.9; color: #404040; }
.hero-microgrid, .metric-strip { display: grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap: 0.8rem; margin-top: 1rem; }
.kpi-box, .metric-card, .story-card, .preview-card, .work-card, .queue-card, .suggestion-card {
    background: rgba(255,255,255,0.20); border: 1px solid rgba(255,255,255,0.52); border-radius: 26px;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.70), 0 12px 30px rgba(0,0,0,0.06);
}
.kpi-box, .metric-card { padding: 1rem; min-height: 112px; }
.kpi-label, .metric-caption, .story-title, .work-section-label {
    font-size: 0.74rem; text-transform: uppercase; letter-spacing: 0.18em; color: #727272;
}
.kpi-value, .metric-number { font-family: "Times New Roman", Georgia, serif; font-size: 2.2rem; color: #202020; letter-spacing: -0.05em; font-weight: 700; margin-top: 0.35rem; }
.kpi-foot, .metric-note, .work-card-meta { font-size: 0.82rem; color: #666666; margin-top: 0.3rem; }
.preview-card, .story-card, .queue-card, .suggestion-card { padding: 1rem; }
.preview-card-title, .panel-title, .work-card-title { font-family: "Times New Roman", Georgia, serif; color: #202020; letter-spacing: -0.05em; }
.preview-card-title { font-size: 1.5rem; }
.panel { padding: 1.15rem; margin-top: 1rem; }
.panel-title { font-size: 2rem; }
.panel-subtitle, .preview-card-copy, .story-copy, .queue-text, .suggestion-meta, .work-card-text, .graph-note { color: #4a4a4a; line-height: 1.8; }
.work-card {
    position: relative; overflow: hidden; padding: 0.72rem; min-height: 400px;
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
    width: 100%; height: 320px; object-fit: cover; border-radius: 22px; display: block;
    transition: transform 0.70s ease, filter 0.70s ease;
}
.work-card:hover img { transform: scale(1.08); filter: saturate(1.04) contrast(1.03); }
.work-card-title { font-size: 1.55rem; margin-top: 0.8rem; }
.work-card-text { font-size: 0.92rem; min-height: 92px; margin-top: 0.75rem; }
.work-grid-note {
    font-size: 0.9rem; color: #555555; line-height: 1.8; margin-bottom: 1rem;
}
.tag-chip, .badge-soft {
    display: inline-flex; align-items: center; padding: 0.42rem 0.78rem; border-radius: 999px; margin: 0.18rem 0.18rem 0.18rem 0;
    background: rgba(255,255,255,0.22); border: 1px solid rgba(255,255,255,0.46); color: #363636; font-size: 0.82rem;
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
    min-height: 48px; padding: 0.76rem 1.12rem !important; border-radius: 18px !important;
    background: rgba(255,255,255,0.22) !important; border: 1px solid rgba(255,255,255,0.54) !important; color: #2f2f2f !important;
    font-weight: 600 !important; box-shadow: inset 0 1px 0 rgba(255,255,255,0.70), 0 10px 22px rgba(0,0,0,0.06) !important;
    transition: transform 0.28s ease, box-shadow 0.28s ease, background 0.28s ease !important;
    backdrop-filter: blur(18px) saturate(150%) !important;
}
.stButton > button:hover, .stDownloadButton > button:hover {
    background: rgba(255,255,255,0.30) !important; transform: translateY(-3px) scale(1.01); box-shadow: 0 16px 30px rgba(0,0,0,0.08) !important;
}
.stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] > div, .stMultiSelect div[data-baseweb="select"] > div, .stNumberInput input {
    background: rgba(255,255,255,0.22) !important; border: 1px solid rgba(255,255,255,0.54) !important; border-radius: 18px !important; color: #2b2b2b !important;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.68) !important; backdrop-filter: blur(18px) !important;
}
.stAlert {
    background: rgba(255,255,255,0.22) !important; border: 1px solid rgba(255,255,255,0.54) !important; border-radius: 18px !important;
    backdrop-filter: blur(18px) !important;
}
[data-testid="stDataFrame"] {
    background: rgba(255,255,255,0.18) !important; border-radius: 18px !important; border: 1px solid rgba(255,255,255,0.40) !important; overflow: hidden;
}
[data-testid="stSidebar"] { display: none; }
@media (max-width: 1100px) { .hero-grid { grid-template-columns: 1fr; } .hero-microgrid, .metric-strip { grid-template-columns: repeat(2, minmax(0,1fr)); } }
@media (max-width: 640px) { .hero-title { font-size: 2.8rem; } .hero-microgrid, .metric-strip { grid-template-columns: 1fr; } .work-card img { height: 250px; } }
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
            for item in DEFAULT_WORKS:
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
        return read_json(WORKS_FILE, [])

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
            if item.get("id") == user_id:
                return item
        return None

    def add_work(self, title: str, artist: str, year: str, description: str, image_url: str, institutional_tags: List[str]) -> Dict[str, Any]:
        items = self.works()
        payload = asdict(WorkRecord(
            id=make_id("work"),
            title=title.strip(),
            artist=artist.strip(),
            year=year.strip(),
            description=description.strip(),
            image_url=image_url.strip(),
            institutional_tags=[t.strip() for t in institutional_tags if t.strip()],
            created_at=now_iso(),
        ))
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
    users = to_dataframe(store.users())
    works = to_dataframe(store.works())
    concepts = to_dataframe(store.concepts())
    validations = to_dataframe(store.validations())
    if not works.empty:
        tags = tags.merge(works[["id", "title", "artist", "year"]].rename(columns={"id": "work_id", "title": "work_title", "artist": "work_artist", "year": "work_year"}), on="work_id", how="left")
    if not users.empty:
        tags = tags.merge(users[["id", "pseudonym"]].rename(columns={"id": "user_id", "pseudonym": "user_pseudonym"}), on="user_id", how="left")
    if not concepts.empty and "concept_id" in tags.columns:
        tags = tags.merge(concepts[["id", "label", "category"]].rename(columns={"id": "concept_id", "label": "concept_resolved_label", "category": "concept_resolved_category"}), on="concept_id", how="left")
    if not validations.empty:
        latest = validations.sort_values("created_at").groupby("tag_id").tail(1)
        tags = tags.merge(latest[["tag_id", "validated_entity", "validated_concept_label", "decision"]], left_on="id", right_on="tag_id", how="left")
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


def build_knowledge_graph(store: JsonStore) -> nx.Graph:
    graph = nx.Graph()
    works = store.works()
    concepts = {concept["id"]: concept for concept in store.concepts()}
    users = {user["id"]: user for user in store.users()}
    tags = store.tags()
    for work in works:
        graph.add_node(work["id"], kind="work", label=work.get("title", ""), subtitle=work.get("artist", ""))
        for tag in work.get("institutional_tags", []):
            node_id = f"inst::{normalize_text(tag)}"
            graph.add_node(node_id, kind="institutional_tag", label=tag, subtitle="institucional")
            graph.add_edge(work["id"], node_id, relation="institutional")
    for user in users.values():
        graph.add_node(user["id"], kind="user", label=user.get("pseudonym", ""), subtitle=user.get("profile_familiarity", ""))
    for concept_id, concept in concepts.items():
        graph.add_node(concept_id, kind="concept", label=concept.get("label", ""), subtitle=concept.get("category", ""))
    for tag in tags:
        tag_node = tag["id"]
        graph.add_node(tag_node, kind="tag", label=tag.get("tag", ""), subtitle=tag.get("entity_prediction", ""))
        if tag.get("work_id"):
            graph.add_edge(tag.get("work_id"), tag_node, relation="tagged")
        if tag.get("user_id"):
            graph.add_edge(tag.get("user_id"), tag_node, relation="created")
        if tag.get("concept_id") and tag.get("concept_id") in concepts:
            graph.add_edge(tag_node, tag.get("concept_id"), relation="reconciled")
    return graph


def graph_to_plot(graph: nx.Graph, max_nodes: int = 120) -> go.Figure:
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
    tags_df = build_tag_dataframe(store)
    metrics = build_public_metrics(tags_df, to_dataframe(store.works()), to_dataframe(store.users()))
    model = store.model_state()
    user_name = ""
    if st.session_state.get("session_user_id"):
        user = store.find_user(st.session_state["session_user_id"])
        user_name = user.get("pseudonym", "") if user else ""
    chips = [f"<span class='status-chip'>obras {metrics.get('works', 0)}</span>", f"<span class='status-chip'>tags {metrics.get('total_tags', 0)}</span>", f"<span class='status-chip'>modelo {model.get('sample_count', 0)} amostras</span>"]
    if user_name:
        chips.append(f"<span class='status-chip'>perfil {user_name}</span>")
    html = f"<div class='topbar'><div><div class='brand-title'>{APP_TITLE}</div><div class='brand-subtitle'>liquid glass semantic interface</div></div><div>{''.join(chips)}</div></div>"
    st.markdown(html, unsafe_allow_html=True)


def hero_panel(store: JsonStore) -> None:
    tags_df = build_tag_dataframe(store)
    works_df = to_dataframe(store.works())
    users_df = to_dataframe(store.users())
    metrics = build_public_metrics(tags_df, works_df, users_df)
    recent_report = store.reports()[-1] if store.reports() else {}
    html = f"""
    <div class="hero-panel">
        <div class="hero-grid">
            <div>
                <div class="hero-kicker">camada semântica participativa com aprendizado contínuo</div>
                <div class="hero-title">folksonomia</div>
                <div class="hero-copy">
                    Interface translúcida com foco em documentação museológica, NLU aplicada a tags livres,
                    reconciliação conceitual, grafo de conhecimento e automação supervisionada.
                    O sistema preserva a linguagem do público e cria uma camada interpretativa acima dela.
                </div>
                <div class="hero-microgrid">
                    <div class="kpi-box"><div class="kpi-label">total de tags</div><div class="kpi-value">{metrics.get('total_tags', 0)}</div><div class="kpi-foot">camada social registrada</div></div>
                    <div class="kpi-box"><div class="kpi-label">vocabulário único</div><div class="kpi-value">{metrics.get('unique_tags', 0)}</div><div class="kpi-foot">diversidade lexical</div></div>
                    <div class="kpi-box"><div class="kpi-label">participantes</div><div class="kpi-value">{metrics.get('active_users', 0)}</div><div class="kpi-foot">perfis anônimos</div></div>
                    <div class="kpi-box"><div class="kpi-label">densidade lexical</div><div class="kpi-value">{metrics.get('lexical_density', 0.0):.2f}</div><div class="kpi-foot">unique over total</div></div>
                </div>
            </div>
            <div>
                <div class="preview-card">
                    <div>
                        <div class="preview-card-title">aprendizado real e automação curatorial</div>
                        <div class="preview-card-copy">
                            O modelo aprende com vocabulário seed, descrição de obras, validações administrativas e padrões de uso.
                            Sugestões de entidade, aproximação conceitual, ambiguidades e conceitos candidatos são gerados automaticamente.
                        </div>
                    </div>
                    <div class="story-copy">
                        último relatório {recent_report.get('created_at', 'ainda não gerado')}<br>
                        clusters {recent_report.get('cluster_count', 0)}<br>
                        tags {recent_report.get('total_tags', 0)}
                    </div>
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


def intro_flow(store: JsonStore) -> None:
    open_panel("acesso inicial", "primeiro responda ao questionário. só depois a interface de marcação das obras será liberada.")
    with st.form("intro_form"):
        c1, c2 = st.columns(2)
        with c1:
            familiarity = st.selectbox("1. qual é a sua frequência de visita a museus?", ["nunca", "raramente", "ocasionalmente", "frequentemente"])
            documentation = st.selectbox("2. você já ouviu falar sobre documentação museológica?", ["nenhum", "básico", "intermediário", "avançado"])
        with c2:
            understanding = st.text_area("3. o que você entende por tags aplicadas a acervos?\n\ndescreva com suas palavras.", height=190, placeholder="escreva com suas palavras")
        submitted = st.form_submit_button("liberar acesso às obras")
        if submitted:
            if not understanding.strip():
                st.warning("preencha o campo sobre tags para continuar.")
            else:
                store.create_or_get_user(familiarity, documentation, understanding)
                st.session_state["intro_complete"] = True
                st.rerun()
    close_panel()


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
    open_panel("explorar obras", "as imagens aparecem lado a lado em liquid glass. nenhum título, artista, técnica ou registro textual é exibido durante a marcação para evitar influência.")
    if not user:
        st.info("responda ao questionário inicial para liberar o acesso às obras.")
        close_panel()
        return
    st.markdown("<div class='work-grid-note'>clique em uma imagem para abrir o campo de tag. durante a marcação, o sistema oculta dados textuais da obra.</div>", unsafe_allow_html=True)
    if not works:
        st.info("nenhuma obra cadastrada.")
        close_panel()
        return

    col_count = 4 if len(works) >= 4 else 3 if len(works) == 3 else 2 if len(works) == 2 else 1
    cols = st.columns(col_count)
    for idx, work in enumerate(works):
        with cols[idx % col_count]:
            st.markdown("<div class='work-card'>", unsafe_allow_html=True)
            st.image(work.get("image_url"), use_container_width=True)
            if st.button("abrir campo de tag", key=f"public-open-{work.get('id')}", use_container_width=True):
                st.session_state["selected_work_id"] = work.get("id")
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    selected_id = st.session_state.get("selected_work_id", "")
    if selected_id:
        selected = next((w for w in works if w.get("id") == selected_id), None)
        if selected:
            st.markdown("<div class='soft-line'></div>", unsafe_allow_html=True)
            open_panel("imagem selecionada", "escreva apenas a sua percepção livre. a interface continua sem exibir dados textuais da obra.")
            c1, c2 = st.columns([1.05, 0.95])
            with c1:
                st.image(selected.get("image_url"), use_container_width=True)
            with c2:
                with st.form(f"tag-form-{selected_id}"):
                    tag_value = st.text_input("sua tag", placeholder="escreva sua tag")
                    submitted = st.form_submit_button("registrar tag", use_container_width=True)
                    if submitted:
                        if not tag_value.strip():
                            st.warning("escreva uma tag antes de registrar.")
                        else:
                            store.submit_tag(selected.get("id"), user.get("id"), tag_value, "", ml)
                            run_automation_engine(store, ml)
                            st.success("tag registrada.")
                            st.rerun()
                if st.button("fechar imagem", key=f"close-public-{selected_id}", use_container_width=True):
                    st.session_state["selected_work_id"] = ""
                    st.rerun()
            close_panel()
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
    open_panel("área administrativa", "login para validação, treinamento do modelo, automação e gestão de conceitos.")
    with st.form("admin_login_form"):
        username = st.text_input("usuário")
        password = st.text_input("senha", type="password")
        submitted = st.form_submit_button("entrar na administração")
        if submitted:
            if store.admin_ok(username.strip(), password.strip()):
                st.session_state["admin_authenticated"] = True
                st.rerun()
            else:
                st.error("credenciais inválidas.")
    close_panel()


def render_admin_dashboard(store: JsonStore, ml: SemanticLearner) -> None:
    tags_df = build_tag_dataframe(store)
    users_df = to_dataframe(store.users())
    concepts_df = to_dataframe(store.concepts())
    open_panel("painel administrativo", "métricas amplas, monitoramento do modelo e estado da automação semântica.")
    html = f"""
    <div class="metric-strip">
        <div class="metric-card"><div class="metric-caption">usuários</div><div class="metric-number">{int(users_df['id'].nunique()) if not users_df.empty else 0}</div><div class="metric-note">perfis criados</div></div>
        <div class="metric-card"><div class="metric-caption">conceitos</div><div class="metric-number">{int(len(concepts_df)) if not concepts_df.empty else 0}</div><div class="metric-note">camada ontológica mínima</div></div>
        <div class="metric-card"><div class="metric-caption">amostras de treino</div><div class="metric-number">{ml.entity_samples}</div><div class="metric-note">seed mais validações</div></div>
        <div class="metric-card"><div class="metric-caption">acurácia estimada</div><div class="metric-number">{ml.entity_accuracy:.2f}</div><div class="metric-note">classificação de entidades</div></div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)
    c1, c2 = st.columns([1.05, 0.95])
    with c1:
        if not tags_df.empty:
            entity_counts = tags_df["entity_prediction"].replace("", "não previsto").fillna("não previsto").value_counts().rename_axis("categoria").reset_index(name="frequência")
            render_bar_chart_df(entity_counts, x="categoria", y="frequência", height=360)
    with c2:
        suggestions_df = to_dataframe(store.suggestions())
        validations_df = to_dataframe(store.validations())
        open_count = int(len(suggestions_df[suggestions_df["status"] == "open"])) if not suggestions_df.empty else 0
        approval_count = int(len(validations_df[validations_df["decision"].isin(["approved", "auto-approved", "linked"])])) if not validations_df.empty else 0
        st.markdown(f"<div class='story-card'><div class='story-title'>fila curatorial</div><div class='story-copy'>sugestões abertas {open_count}<br>validações aprovadas {approval_count}<br>modo de automação {'ativo' if store.automations().get('enabled', True) else 'inativo'}</div></div>", unsafe_allow_html=True)
        recent = store.reports()[-1] if store.reports() else {}
        st.markdown(f"<div class='story-card'><div class='story-title'>último relatório</div><div class='story-copy'>data {recent.get('created_at', 'não disponível')}<br>clusters {recent.get('cluster_count', 0)}<br>tags {recent.get('total_tags', 0)}</div></div>", unsafe_allow_html=True)
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
    settings = store.automations()
    suggestions_df = to_dataframe(store.suggestions())
    open_panel("automação", "regras para classificação automática, ligação conceitual, sinalização de ambiguidades e geração de relatórios.")
    with st.form("automation-form"):
        c1, c2 = st.columns(2)
        with c1:
            enabled = st.checkbox("ativar automação", value=settings.get("enabled", True))
            auto_classify = st.checkbox("classificação automática", value=settings.get("auto_classify", True))
            auto_link = st.checkbox("ligação automática a conceitos", value=settings.get("auto_link_concepts", False))
            auto_report = st.checkbox("gerar relatórios automaticamente", value=settings.get("auto_generate_reports", True))
        with c2:
            min_conf = st.slider("limiar de confiança para classificar", 0.50, 0.99, float(settings.get("min_confidence_auto_classify", 0.84)), 0.01)
            min_sim = st.slider("limiar de similaridade para ligar conceito", 0.50, 0.99, float(settings.get("min_similarity_auto_link", 0.88)), 0.01)
            min_freq = st.slider("frequência mínima para conceito candidato", 2, 12, int(settings.get("min_frequency_candidate_concept", 3)), 1)
            auto_ambiguity = st.checkbox("sinalizar ambiguidades automaticamente", value=settings.get("auto_flag_ambiguity", True))
            auto_candidate = st.checkbox("criar conceitos candidatos automaticamente", value=settings.get("auto_create_candidate_concepts", True))
        submitted = st.form_submit_button("salvar regras")
        if submitted:
            store.save_automations({
                "enabled": enabled,
                "min_confidence_auto_classify": min_conf,
                "min_similarity_auto_link": min_sim,
                "min_frequency_candidate_concept": min_freq,
                "auto_classify": auto_classify,
                "auto_link_concepts": auto_link,
                "auto_generate_reports": auto_report,
                "auto_flag_ambiguity": auto_ambiguity,
                "auto_create_candidate_concepts": auto_candidate,
            })
            run_automation_engine(store, ml)
            st.success("regras salvas e automação executada.")
            st.rerun()
    if st.button("executar automação agora", use_container_width=True):
        created = run_automation_engine(store, ml)
        st.success(f"automação executada. {len(created)} nova(s) sugestão(ões) criada(s).")
        st.rerun()
    if not suggestions_df.empty:
        st.dataframe(suggestions_df.sort_values("created_at", ascending=False)[[c for c in ["rule_name", "suggestion_type", "status", "payload", "created_at"] if c in suggestions_df.columns]], use_container_width=True, hide_index=True)
    close_panel()


def render_admin_graph(store: JsonStore) -> None:
    open_panel("grafo de conhecimento", "obras, usuários, tags, conceitos e eixos institucionais conectados como rede consultável.")
    graph = build_knowledge_graph(store)
    if HAS_NETWORKX and HAS_PLOTLY:
        safe_plotly_chart(graph_to_plot(graph, max_nodes=140), use_container_width=True)
        node_count = graph.number_of_nodes()
        edge_count = graph.number_of_edges()
    else:
        node_count = len(graph.get("nodes", []))
        edge_count = len(graph.get("edges", []))
        st.info("visualização interativa do grafo indisponível neste ambiente. o app segue funcionando com o resumo estrutural.")
        node_df = pd.DataFrame(graph.get("nodes", []))
        if not node_df.empty and "kind" in node_df.columns:
            st.bar_chart(node_df["kind"].value_counts())
    st.markdown(f"<div class='story-card'><div class='story-title'>estrutura atual</div><div class='graph-note'>nós {node_count} · arestas {edge_count}. O grafo incorpora obras, usuários, conceitos, tags livres e tags institucionais.</div></div>", unsafe_allow_html=True)
    close_panel()


def render_admin_data(store: JsonStore, ml: SemanticLearner) -> None:
    def build_detailed_pdf_bytes() -> bytes:
        from io import BytesIO
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        from reportlab.lib.utils import simpleSplit

        tags_df = build_tag_dataframe(store)
        works_df = to_dataframe(store.works())
        concepts_df = to_dataframe(store.concepts())
        validations_df = to_dataframe(store.validations())
        reports = store.reports()
        latest_report = reports[-1] if reports else {}
        metrics = build_public_metrics(tags_df, works_df, to_dataframe(store.users()))

        buffer = BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        margin = 42
        y = height - 44

        def line(text_value: str = "", font_name: str = "Times-Roman", font_size: int = 11, gap: int = 16) -> None:
            nonlocal y
            txt = str(text_value)
            chunks = simpleSplit(txt, font_name, font_size, width - margin * 2)
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
        line("Relatório detalhado da base, da camada semântica e da automação administrativa", "Times-Roman", 12, 18)
        line(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", "Times-Roman", 11, 18)
        spacer(6)

        line("1. Métricas gerais", "Times-Bold", 16, 20)
        line(f"Total de obras: {metrics.get('works', 0)}")
        line(f"Obras tagueadas: {metrics.get('tagged_works', 0)}")
        line(f"Total de tags: {metrics.get('total_tags', 0)}")
        line(f"Vocabulário único: {metrics.get('unique_tags', 0)}")
        line(f"Participantes: {metrics.get('active_users', 0)}")
        line(f"Densidade lexical: {metrics.get('lexical_density', 0.0):.3f}")
        line(f"Amostras do modelo: {store.model_state().get('sample_count', 0)}")
        line(f"Acurácia estimada do modelo: {store.model_state().get('accuracy', 0.0):.2f}")
        spacer(8)

        if not works_df.empty:
            line("2. Obras cadastradas", "Times-Bold", 16, 20)
            for _, row in works_df.iterrows():
                tags_text = ", ".join(row.get("institutional_tags", [])[:8]) if isinstance(row.get("institutional_tags"), list) else str(row.get("institutional_tags", ""))
                line(f"- {row.get('title', '')} | {row.get('artist', '')} | {row.get('year', '')}", "Times-Bold", 12, 16)
                if str(row.get("description", "")).strip():
                    line(f"  Descrição: {row.get('description', '')}")
                if tags_text:
                    line(f"  Tags institucionais: {tags_text}")
                spacer(4)

        if not tags_df.empty:
            line("3. Camada social e vocabulário", "Times-Bold", 16, 20)
            top_tags = tags_df["tag"].value_counts().head(25)
            for tag, count in top_tags.items():
                line(f"- {tag}: {count} ocorrência(s)")
            spacer(8)

            line("4. Distribuição por categoria prevista", "Times-Bold", 16, 20)
            entity_counts = tags_df["entity_prediction"].replace("", "não previsto").fillna("não previsto").value_counts()
            for entity, count in entity_counts.items():
                line(f"- {entity}: {count}")
            spacer(8)

            clusters = ml.cluster_terms(tags_df["tag"].astype(str).tolist(), threshold=0.66)
            line("5. Agrupamentos semânticos sugeridos", "Times-Bold", 16, 20)
            if clusters:
                for idx, cluster in enumerate(clusters[:20], 1):
                    line(f"- Grupo {idx}: {', '.join(cluster)}")
            else:
                line("- Ainda não há agrupamentos suficientemente robustos.")
            spacer(8)

        if not concepts_df.empty:
            line("6. Conceitos reconciliados", "Times-Bold", 16, 20)
            for _, row in concepts_df.head(40).iterrows():
                alias_text = ", ".join(row.get("aliases", [])[:6]) if isinstance(row.get("aliases"), list) else str(row.get("aliases", ""))
                line(f"- {row.get('label', '')} | categoria {row.get('category', '')} | origem {row.get('source', '')}")
                if alias_text:
                    line(f"  Alias: {alias_text}")
            spacer(8)

        if not validations_df.empty:
            line("7. Validações administrativas", "Times-Bold", 16, 20)
            for _, row in validations_df.tail(40).iterrows():
                line(f"- {row.get('created_at', '')} | decisão {row.get('decision', '')} | entidade {row.get('validated_entity', '')} | conceito {row.get('validated_concept_label', '')}")
                if str(row.get("notes", "")).strip():
                    line(f"  Observações: {row.get('notes', '')}")
            spacer(8)

        if latest_report:
            line("8. Último relatório automático", "Times-Bold", 16, 20)
            line(f"Gerado em: {latest_report.get('created_at', '')}")
            line(f"Total de tags no relatório: {latest_report.get('total_tags', 0)}")
            line(f"Vocabulário único: {latest_report.get('unique_tags', 0)}")
            line(f"Clusters identificados: {latest_report.get('cluster_count', 0)}")
            preview = latest_report.get("clusters_preview", [])
            for idx, cluster in enumerate(preview[:10], 1):
                line(f"- Preview {idx}: {', '.join(cluster)}")

        pdf.save()
        buffer.seek(0)
        return buffer.getvalue()

    open_panel("obras e exportação", "gestão administrativa de obras, remoção, cadastro e download detalhado em csv e pdf.")
    works = store.works()
    t1, t2, t3, t4 = st.tabs(["obras", "nova obra", "exportação csv", "exportação pdf"])

    with t1:
        if not works:
            st.info("não há obras cadastradas.")
        else:
            works_df = to_dataframe(works)
            st.dataframe(works_df[[c for c in ["title", "artist", "year", "institutional_tags", "created_at"] if c in works_df.columns]], use_container_width=True, hide_index=True)
            st.markdown("<div class='soft-line'></div>", unsafe_allow_html=True)
            for work in works:
                c1, c2, c3 = st.columns([0.9, 1.7, 0.7])
                with c1:
                    st.image(work.get("image_url"), use_container_width=True)
                with c2:
                    st.markdown(f"<div class='story-card'><div class='story-title'>{work.get('title')}</div><div class='story-copy'>{work.get('artist')} · {work.get('year')}<br>{work.get('description')}</div></div>", unsafe_allow_html=True)
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
            c1, c2 = st.columns(2)
            with c1:
                title = st.text_input("título")
                artist = st.text_input("artista")
                year = st.text_input("ano")
            with c2:
                image_url = st.text_input("url da imagem")
                tags = st.text_input("tags institucionais separadas por vírgula")
            description = st.text_area("descrição", height=120)
            submitted = st.form_submit_button("adicionar obra")
            if submitted:
                if not title.strip() or not artist.strip():
                    st.warning("preencha ao menos título e artista.")
                else:
                    store.add_work(title, artist, year, description, image_url, [part.strip() for part in tags.split(",") if part.strip()])
                    ml.train()
                    st.success("obra adicionada.")
                    st.rerun()

    with t3:
        works_df = to_dataframe(store.works())
        tags_df = build_tag_dataframe(store)
        concepts_df = to_dataframe(store.concepts())
        validations_df = to_dataframe(store.validations())
        users_df = to_dataframe(store.users())
        st.download_button("baixar obras em csv", works_df.to_csv(index=False).encode("utf-8"), "obras_folksonomia.csv", "text/csv", use_container_width=True)
        st.download_button("baixar tags em csv", tags_df.to_csv(index=False).encode("utf-8"), "tags_folksonomia.csv", "text/csv", use_container_width=True)
        st.download_button("baixar conceitos em csv", concepts_df.to_csv(index=False).encode("utf-8"), "conceitos_folksonomia.csv", "text/csv", use_container_width=True)
        st.download_button("baixar validações em csv", validations_df.to_csv(index=False).encode("utf-8"), "validacoes_folksonomia.csv", "text/csv", use_container_width=True)
        st.download_button("baixar usuários em csv", users_df.to_csv(index=False).encode("utf-8"), "usuarios_folksonomia.csv", "text/csv", use_container_width=True)

    with t4:
        try:
            pdf_bytes = build_detailed_pdf_bytes()
            st.markdown("<div class='story-card'><div class='story-title'>relatório administrativo em pdf</div><div class='story-copy'>o arquivo reúne métricas gerais, obras cadastradas, top tags, categorias previstas pelo modelo, agrupamentos semânticos, conceitos reconciliados, validações e o último relatório automático.</div></div>", unsafe_allow_html=True)
            st.download_button("baixar relatório detalhado em pdf", pdf_bytes, "relatorio_detalhado_folksonomia.pdf", "application/pdf", use_container_width=True)
        except Exception as exc:
            st.warning(f"não foi possível gerar o pdf nesta execução: {exc}")

    close_panel()


def render_footer() -> None:
    st.markdown("<div class='story-copy' style='text-align:center;margin-top:1rem;margin-bottom:2rem'>folksonomia · interface translúcida · tipografia serifada · aprendizagem incremental · automação supervisionada</div>", unsafe_allow_html=True)


def main() -> None:
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

    public_tabs = st.tabs(["explorar obras", "meu histórico", "administração"])
    with public_tabs[0]:
        render_public_explore(store, ml)
    with public_tabs[1]:
        render_public_history(store)
    with public_tabs[2]:
        if not st.session_state.get("admin_authenticated", False):
            render_admin_login(store)
        else:
            admin_tabs = st.tabs(["painel", "validação", "conceitos", "machine learning", "automação", "grafo", "dados"])
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


if __name__ == "__main__":
    main()
