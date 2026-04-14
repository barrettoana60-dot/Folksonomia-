import streamlit as st
import pandas as pd
import numpy as np
import os
import json
import base64
import hashlib
import html
import random
import re
import unicodedata
from datetime import datetime
from collections import defaultdict, Counter

warnings_filter = __import__("warnings")
warnings_filter.filterwarnings("ignore")

# ============================================================
# CONFIG
# ============================================================
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
ONTOLOGIES_FILE = os.path.join(DATA_DIR, "ontologias.json")
LEDGER_FILE = os.path.join(DATA_DIR, "ledger.json")
CIRCULATION_FILE = os.path.join(DATA_DIR, "circulacao.json")
OPEN_DATA_FILE = os.path.join(DATA_DIR, "open_data.json")

ADMIN_USERNAME = "nugep"
ADMIN_PASSWORD = "nugep123"

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

STATUS_METADADO = ["bruto", "sugerido", "validado", "revisado", "publicado"]
FONT_OPTIONS = ["16px", "18px", "20px", "22px", "24px"]

SEMANTIC_GROUPS = {
    "religioso": [
        "religioso", "religião", "igreja", "santo", "santa", "cristo", "crucifixo", "bíblia",
        "biblia", "anjo", "divino", "sagrado", "maria", "jesus", "oração", "oracao", "altar"
    ],
    "guerra": [
        "guerra", "batalha", "soldado", "arma", "espada", "escudo", "conflito", "militar",
        "exército", "exercito", "violência", "violencia", "sangue", "morte", "ataque", "defesa"
    ],
    "cor": [
        "azul", "verde", "vermelho", "amarelo", "roxo", "rosa", "preto", "branco", "cinza",
        "laranja", "marrom", "dourado", "prateado", "colorido", "escuro", "claro"
    ],
    "natureza": [
        "árvore", "arvore", "flor", "céu", "ceu", "mar", "rio", "montanha", "sol", "lua",
        "estrela", "nuvem", "terra", "animal", "folha", "grama", "floresta"
    ],
    "emoção": [
        "triste", "feliz", "medo", "angústia", "angustia", "dor", "esperança", "esperanca",
        "alegria", "melancolia", "raiva", "calma", "tensão", "tensao", "solidão", "solidao"
    ],
    "forma": [
        "círculo", "circulo", "quadrado", "triângulo", "triangulo", "linha", "curva", "geometria",
        "simetria", "abstrato", "vertical", "horizontal", "volume"
    ]
}

DEFAULT_ONTOLOGIES = [
    {
        "id": 1,
        "nome": "Cores",
        "descricao": "Vocabulário controlado para identificação cromática.",
        "categoria": "visual",
        "termos": ["azul", "verde", "vermelho", "amarelo", "preto", "branco", "cinza", "dourado"],
        "ativo": True,
        "criado_em": None,
        "atualizado_em": None
    },
    {
        "id": 2,
        "nome": "Temáticas Religiosas",
        "descricao": "Vocabulário controlado para temas religiosos.",
        "categoria": "tema",
        "termos": ["religioso", "sagrado", "anjo", "santo", "jesus", "maria", "altar", "igreja"],
        "ativo": True,
        "criado_em": None,
        "atualizado_em": None
    },
    {
        "id": 3,
        "nome": "Conflito e Guerra",
        "descricao": "Vocabulário controlado para guerra, conflito e violência.",
        "categoria": "tema",
        "termos": ["guerra", "batalha", "arma", "soldado", "militar", "sangue", "ataque"],
        "ativo": True,
        "criado_em": None,
        "atualizado_em": None
    }
]

DEFAULT_OBRAS = [
    {
        "id": 1,
        "titulo": "Guernica",
        "artista": "Pablo Picasso",
        "ano": "1937",
        "imagem": "https://upload.wikimedia.org/wikipedia/en/7/74/PicassoGuernica.jpg",
        "audio_descricao": "Pintura monumental em tons de preto, branco e cinza. A composição é fragmentada, com figuras humanas e animais em sofrimento. Há corpos distorcidos, rostos em desespero, um cavalo ferido ao centro, um touro à esquerda e uma lâmpada acima como foco dramático. A cena transmite violência, ruptura e caos de guerra.",
        "metadados": {
            "instituicao": "Acervo Demonstrativo",
            "origem_registro": "seed",
            "status": "publicado"
        }
    },
    {
        "id": 2,
        "titulo": "A Noite Estrelada",
        "artista": "Vincent van Gogh",
        "ano": "1889",
        "imagem": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ea/Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg/1200px-Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg",
        "audio_descricao": "Paisagem noturna com céu azul profundo e redemoinhos luminosos. As estrelas aparecem como círculos brilhantes em amarelo intenso. A lua também se destaca. Abaixo, um vilarejo calmo contrasta com o movimento vibrante do céu. Um cipreste escuro se ergue em primeiro plano.",
        "metadados": {
            "instituicao": "Acervo Demonstrativo",
            "origem_registro": "seed",
            "status": "publicado"
        }
    },
    {
        "id": 3,
        "titulo": "Mona Lisa",
        "artista": "Leonardo da Vinci",
        "ano": "1503",
        "imagem": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ec/Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_retouched.jpg/800px-Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_retouched.jpg",
        "audio_descricao": "Retrato feminino de meio corpo, com expressão serena e sorriso sutil. A personagem está sentada, com as mãos cruzadas. Ao fundo há uma paisagem distante com rios, caminhos e montanhas. Os tons são suaves, em marrom, verde e azul acinzentado.",
        "metadados": {
            "instituicao": "Acervo Demonstrativo",
            "origem_registro": "seed",
            "status": "publicado"
        }
    }
]

# ============================================================
# CORE UTIL
# ============================================================
def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def ensure_data_dir():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)


def load_json_file(filepath, default):
    ensure_data_dir()
    if os.path.exists(filepath):
        try:
            with open(filepath, "r",