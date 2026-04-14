
from __future__ import annotations

import base64
import hashlib
import html
import json
import math
import os
import random
import re
import textwrap
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

try:
    import networkx as nx
except Exception:  # pragma: no cover
    nx = None

try:
    import plotly.graph_objects as go
except Exception:  # pragma: no cover
    go = None

APP_TITLE = "Folksonomia Semântica Museológica"
DATA_DIR = Path("data_semantica")
FILES = {
    "obras": DATA_DIR / "obras.json",
    "tags": DATA_DIR / "tags.json",
    "users": DATA_DIR / "users.json",
    "admins": DATA_DIR / "admins.json",
    "ontologies": DATA_DIR / "ontologies.json",
    "semantic_entities": DATA_DIR / "semantic_entities.json",
    "semantic_links": DATA_DIR / "semantic_links.json",
    "validation_queue": DATA_DIR / "validation_queue.json",
    "ledger": DATA_DIR / "ledger.json",
    "exports": DATA_DIR / "exports.json",
}
ADMIN_USERNAME = "nugep"
ADMIN_PASSWORD = "nugep123"

ANIMAIS = [
    "Águia", "Boto", "Capivara", "Doninha", "Ema", "Falcão", "Gavião", "Harpia",
    "Irara", "Jaguar", "Lontra", "Mico", "Onça", "Paca", "Quati", "Raposa",
    "Tamanduá", "Urubu", "Veado", "Zorrilho", "Arara", "Bugio", "Caititu",
    "Jaguatirica", "Lobo", "Mutum", "Pirarucu", "Tucano", "Sucuri", "Tatu",
]
ADJETIVOS = [
    "Azul", "Bravo", "Calmo", "Dourado", "Esperto", "Feroz", "Gracioso", "Intenso",
    "Jovial", "Lento", "Mágico", "Nobre", "Ousado", "Preciso", "Rápido", "Sábio",
    "Tímido", "Único", "Valente", "Zeloso", "Curioso", "Furtivo", "Altivo",
    "Sereno", "Vibrante", "Audaz", "Brilhante", "Corajoso", "Distinto", "Elegante",
]


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def slug(text: str) -> str:
    text = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode("utf-8")
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    return text or "item"


def normalize(text: str) -> str:
    text = str(text or "").strip().lower()
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("utf-8")
    text = re.sub(r"\s+", " ", text)
    return text


def sha(data: Any) -> str:
    return hashlib.sha256(json.dumps(data, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def human_id(prefix: str) -> str:
    token = base64.b64encode(os.urandom(9)).decode("ascii").replace("/", "").replace("+", "")
    return f"{prefix}_{token[:12]}"


def animal_name() -> str:
    return f"{random.choice(ANIMAIS)} {random.choice(ADJETIVOS)}"


def ensure_dirs() -> None:
    DATA_DIR.mkdir(exist_ok=True, parents=True)


def read_json(path: Path, default: Any) -> Any:
    ensure_dirs()
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    return default


def write_json(path: Path, data: Any) -> bool:
    ensure_dirs()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return True


DEFAULT_ONTOLOGIES: List[Dict[str, Any]] = [
    {
        "id": "onto_museologia_central",
        "nome": "Ontologia Museológica Central",
        "descricao": "Estrutura-base para objetos museológicos, autores, documentos e relações curatoriais.",
        "namespace": "http://folksonomia.local/ontology/museologia#",
        "ativa": True,
        "classes": [
            {"id": "obra", "nome": "Obra", "descricao": "Item museológico principal"},
            {"id": "autor", "nome": "Autor", "descricao": "Pessoa ou coletividade criadora"},
            {"id": "colecao", "nome": "Coleção", "descricao": "Conjunto institucional"},
            {"id": "material", "nome": "Material", "descricao": "Matéria constitutiva"},
            {"id": "tecnica", "nome": "Técnica", "descricao": "Técnica ou modo de produção"},
            {"id": "tema", "nome": "Tema", "descricao": "Tema iconográfico ou conceitual"},
            {"id": "periodo", "nome": "Período", "descricao": "Recorte cronológico"},
            {"id": "documento", "nome": "Documento", "descricao": "Documento de arquivo ou apoio"},
            {"id": "entidade", "nome": "Entidade", "descricao": "Entidade reconhecida automaticamente"},
        ],
        "propriedades": [
            {"id": "criado_por", "nome": "criado_por", "dominio": "obra", "alcance": "autor"},
            {"id": "pertence_a", "nome": "pertence_a", "dominio": "obra", "alcance": "colecao"},
            {"id": "tem_material", "nome": "tem_material", "dominio": "obra", "alcance": "material"},
            {"id": "tem_tecnica", "nome": "tem_tecnica", "dominio": "obra", "alcance": "tecnica"},
            {"id": "tem_tema", "nome": "tem_tema", "dominio": "obra", "alcance": "tema"},
            {"id": "situada_em", "nome": "situada_em", "dominio": "obra", "alcance": "periodo"},
            {"id": "referenciada_em", "nome": "referenciada_em", "dominio": "obra", "alcance": "documento"},
            {"id": "relaciona_entidade", "nome": "relaciona_entidade", "dominio": "obra", "alcance": "entidade"},
        ],
        "termos_controlados": {
            "tema": [
                "religiosidade", "guerra", "natureza", "retrato", "cidade", "trabalho",
                "família", "território", "memória", "identidade", "ancestralidade",
                "resistência", "cotidiano", "corpo", "paisagem",
            ],
            "material": [
                "óleo sobre tela", "papel", "madeira", "metal", "cerâmica", "tecido",
                "fotografia", "vídeo", "documento textual", "misto",
            ],
            "tecnica": [
                "pintura", "escultura", "desenho", "gravura", "colagem", "fotografia",
                "audiovisual", "arte digital", "instalação",
            ],
        },
        "mapeamentos_folksonomia": [
            {"livre": "azul", "controlado": "paisagem", "tipo": "tema"},
            {"livre": "religioso", "controlado": "religiosidade", "tipo": "tema"},
            {"livre": "família", "controlado": "família", "tipo": "tema"},
            {"livre": "tela", "controlado": "óleo sobre tela", "tipo": "material"},
        ],
    },
    {
        "id": "onto_acessibilidade",
        "nome": "Ontologia de Acessibilidade Museológica",
        "descricao": "Categorias para recursos de acessibilidade e mediação.",
        "namespace": "http://folksonomia.local/ontology/access#",
        "ativa": True,
        "classes": [
            {"id": "recurso", "nome": "RecursoAcessibilidade", "descricao": "Recurso de inclusão"},
            {"id": "audio_desc", "nome": "Audiodescricao", "descricao": "Descrição narrada"},
            {"id": "contraste", "nome": "Contraste", "descricao": "Ajustes visuais"},
            {"id": "fonte", "nome": "Fonte", "descricao": "Escala tipográfica"},
            {"id": "libras", "nome": "Libras", "descricao": "Mediação em Libras"},
        ],
        "propriedades": [
            {"id": "possui_recurso", "nome": "possui_recurso", "dominio": "obra", "alcance": "recurso"},
            {"id": "narra", "nome": "narra", "dominio": "audio_desc", "alcance": "obra"},
        ],
        "termos_controlados": {
            "recurso": [
                "audiodescrição", "alto contraste", "tamanho ampliado", "fundo branco",
                "leitura simplificada", "tecla de navegação", "libras",
            ]
        },
        "mapeamentos_folksonomia": [],
    },
    {
        "id": "onto_curadoria_validacao",
        "nome": "Ontologia de Curadoria e Validação",
        "descricao": "Estados de revisão humana para extrações e metadados.",
        "namespace": "http://folksonomia.local/ontology/validation#",
        "ativa": True,
        "classes": [
            {"id": "extracao", "nome": "ExtracaoIA", "descricao": "Dado sugerido automaticamente"},
            {"id": "revisao", "nome": "RevisaoHumana", "descricao": "Revisão documental"},
            {"id": "estado", "nome": "EstadoValidacao", "descricao": "Status do item"},
        ],
        "propriedades": [
            {"id": "foi_validado_por", "nome": "foi_validado_por", "dominio": "extracao", "alcance": "revisao"},
            {"id": "tem_estado", "nome": "tem_estado", "dominio": "extracao", "alcance": "estado"},
        ],
        "termos_controlados": {
            "estado": ["pendente", "aprovado", "corrigido", "rejeitado", "publicado"]
        },
        "mapeamentos_folksonomia": [],
    },
]

DEFAULT_OBRAS: List[Dict[str, Any]] = [
    {
        "id": 1,
        "obra_uid": "obra_guernica",
        "titulo": "Guernica",
        "artista": "Pablo Picasso",
        "ano": "1937",
        "colecao": "Museo Reina Sofía",
        "periodo": "Século XX",
        "material": "óleo sobre tela",
        "tecnica": "pintura",
        "dimensoes": "349 cm × 776 cm",
        "proveniencia": "Espanha",
        "cronologia": "Contexto da Guerra Civil Espanhola",
        "texto_curatorial": "Guernica articula fragmentação, dor, violência e memória histórica em uma composição monumental.",
        "descricao_museologica": "Pintura de grande formato, em preto, branco e cinza, que apresenta figuras humanas e animais em composição dramática.",
        "enciclopedia": "A obra se tornou símbolo universal contra a guerra e a violência sobre civis.",
        "arquivo": "Dossiê curatorial, documentação de circulação e reprodução institucional.",
        "audio_descricao": "Obra em preto, branco e cinza. Em grande superfície horizontal, figuras humanas, um cavalo e um touro aparecem de forma fragmentada e dramática, sugerindo dor, caos e destruição.",
        "imagem": "https://upload.wikimedia.org/wikipedia/en/7/74/PicassoGuernica.jpg",
        "ontologias": ["onto_museologia_central", "onto_acessibilidade", "onto_curadoria_validacao"],
        "tema_tags": ["guerra", "memória", "violência", "resistência"],
        "acessibilidade": {
            "audiodescricao": True,
            "alto_contraste": True,
            "fonte_ampliada": True,
            "fundo_branco": True
        },
        "status_validacao": "publicado",
    },
    {
        "id": 2,
        "obra_uid": "obra_noite_estrelada",
        "titulo": "A Noite Estrelada",
        "artista": "Vincent van Gogh",
        "ano": "1889",
        "colecao": "Museum of Modern Art",
        "periodo": "Século XIX",
        "material": "óleo sobre tela",
        "tecnica": "pintura",
        "dimensoes": "73,7 cm × 92,1 cm",
        "proveniencia": "França",
        "cronologia": "Produzida durante a permanência em Saint-Rémy.",
        "texto_curatorial": "A pintura apresenta um céu em movimento, uso expressivo da cor e uma relação intensa entre emoção e paisagem.",
        "descricao_museologica": "Vista noturna com espirais luminosas no céu, vila ao fundo e cipreste escuro em primeiro plano.",
        "enciclopedia": "É uma das obras mais conhecidas da arte ocidental.",
        "arquivo": "Correspondências e referências curatoriais sobre sua recepção histórica.",
        "audio_descricao": "Paisagem noturna com céu azul profundo, estrelas circulares e espirais luminosas. Na frente, um cipreste alto e escuro. Ao fundo, uma pequena vila e colinas.",
        "imagem": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ea/Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg/1200px-Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg",
        "ontologias": ["onto_museologia_central", "onto_acessibilidade", "onto_curadoria_validacao"],
        "tema_tags": ["paisagem", "natureza", "céu", "emoção"],
        "acessibilidade": {
            "audiodescricao": True,
            "alto_contraste": True,
            "fonte_ampliada": True,
            "fundo_branco": True
        },
        "status_validacao": "publicado",
    },
    {
        "id": 3,
        "obra_uid": "obra_mona_lisa",
        "titulo": "Mona Lisa",
        "artista": "Leonardo da Vinci",
        "ano": "1503",
        "colecao": "Museu do Louvre",
        "periodo": "Renascimento",
        "material": "óleo sobre madeira",
        "tecnica": "pintura",
        "dimensoes": "77 cm × 53 cm",
        "proveniencia": "Itália",
        "cronologia": "Associada ao alto Renascimento italiano.",
        "texto_curatorial": "O retrato é marcado pela composição equilibrada, sfumato e ambiguidade expressiva.",
        "descricao_museologica": "Retrato de mulher sentada, mãos sobrepostas, vestes escuras e paisagem ao fundo.",
        "enciclopedia": "É um dos retratos mais reproduzidos e debatidos da história da arte.",
        "arquivo": "Dossiê de conservação e estudos de atribuição.",
        "audio_descricao": "Retrato de uma mulher sentada, com expressão serena e leve sorriso. Ao fundo, uma paisagem montanhosa e sinuosa.",
        "imagem": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ec/Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_retouched.jpg/800px-Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_retouched.jpg",
        "ontologias": ["onto_museologia_central", "onto_acessibilidade", "onto_curadoria_validacao"],
        "tema_tags": ["retrato", "identidade", "renascimento"],
        "acessibilidade": {
            "audiodescricao": True,
            "alto_contraste": True,
            "fonte_ampliada": True,
            "fundo_branco": True
        },
        "status_validacao": "publicado",
    },
]

MATERIALS = {
    "óleo": "óleo sobre tela",
    "papel": "papel",
    "madeira": "madeira",
    "metal": "metal",
    "cerâmica": "cerâmica",
    "ceramica": "cerâmica",
    "tecido": "tecido",
    "fotografia": "fotografia",
    "vídeo": "vídeo",
    "video": "vídeo",
    "documento": "documento textual",
    "tela": "óleo sobre tela",
}
TECHNIQUES = {
    "pintura": "pintura",
    "escultura": "escultura",
    "gravura": "gravura",
    "desenho": "desenho",
    "colagem": "colagem",
    "fotografia": "fotografia",
    "instalação": "instalação",
    "instalacao": "instalação",
    "vídeo": "audiovisual",
    "video": "audiovisual",
}
THEMES = {
    "guerra": "guerra",
    "memória": "memória",
    "memoria": "memória",
    "identidade": "identidade",
    "retrato": "retrato",
    "natureza": "natureza",
    "paisagem": "paisagem",
    "corpo": "corpo",
    "família": "família",
    "familia": "família",
    "trabalho": "trabalho",
    "território": "território",
    "territorio": "território",
    "ancestralidade": "ancestralidade",
    "religioso": "religiosidade",
    "religiosidade": "religiosidade",
    "cidade": "cidade",
    "resistência": "resistência",
    "resistencia": "resistência",
}
KNOWN_AUTHORS = [
    "Pablo Picasso", "Vincent van Gogh", "Leonardo da Vinci", "Tarsila do Amaral",
    "Anita Malfatti", "Candido Portinari", "Alice Neel", "Panmela Castro",
]
KNOWN_COLLECTIONS = [
    "Museu do Louvre", "Museo Reina Sofía", "Museum of Modern Art", "Metropolitan Museum of Art",
    "Museu Nacional de Belas Artes", "Museu de Arte de São Paulo",
]


@dataclass
class LedgerEvent:
    index: int
    timestamp: str
    event_type: str
    actor_id: str
    actor_name: str
    entity_type: str
    entity_id: str
    action: str
    payload: Dict[str, Any]
    previous_hash: str
    event_hash: str
    signature_hint: str


def bootstrap() -> None:
    ensure_dirs()
    if not FILES["obras"].exists():
        write_json(FILES["obras"], DEFAULT_OBRAS)
    if not FILES["tags"].exists():
        write_json(FILES["tags"], [])
    if not FILES["users"].exists():
        write_json(FILES["users"], [])
    if not FILES["ontologies"].exists():
        write_json(FILES["ontologies"], DEFAULT_ONTOLOGIES)
    if not FILES["semantic_entities"].exists():
        write_json(FILES["semantic_entities"], [])
    if not FILES["semantic_links"].exists():
        write_json(FILES["semantic_links"], [])
    if not FILES["validation_queue"].exists():
        write_json(FILES["validation_queue"], [])
    if not FILES["exports"].exists():
        write_json(FILES["exports"], [])
    if not FILES["ledger"].exists():
        write_json(FILES["ledger"], [])
    if not FILES["admins"].exists():
        admins = [{
            "id": "admin_root",
            "username": ADMIN_USERNAME,
            "password_hash": hashlib.sha256(ADMIN_PASSWORD.encode()).hexdigest(),
            "display_name": "NUGEP",
        }]
        write_json(FILES["admins"], admins)
    if not read_json(FILES["ledger"], []):
        append_ledger_event(
            event_type="system_bootstrap",
            actor_id="system",
            actor_name="System",
            entity_type="system",
            entity_id="bootstrap",
            action="create_defaults",
            payload={"obras": len(DEFAULT_OBRAS), "ontologias": len(DEFAULT_ONTOLOGIES)},
        )


def load_table(name: str) -> List[Dict[str, Any]]:
    return read_json(FILES[name], [])


def save_table(name: str, rows: List[Dict[str, Any]]) -> bool:
    return write_json(FILES[name], rows)


def append_ledger_event(
    event_type: str,
    actor_id: str,
    actor_name: str,
    entity_type: str,
    entity_id: str,
    action: str,
    payload: Dict[str, Any],
) -> LedgerEvent:
    ledger = read_json(FILES["ledger"], [])
    prev_hash = ledger[-1]["event_hash"] if ledger else "GENESIS"
    raw = {
        "timestamp": now_str(),
        "event_type": event_type,
        "actor_id": actor_id,
        "actor_name": actor_name,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "action": action,
        "payload": payload,
        "previous_hash": prev_hash,
    }
    event_hash = sha(raw)
    event = LedgerEvent(
        index=len(ledger),
        timestamp=raw["timestamp"],
        event_type=event_type,
        actor_id=actor_id,
        actor_name=actor_name,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        payload=payload,
        previous_hash=prev_hash,
        event_hash=event_hash,
        signature_hint=hashlib.sha256(f"{actor_id}:{event_hash}".encode()).hexdigest()[:16],
    )
    ledger.append(asdict(event))
    write_json(FILES["ledger"], ledger)
    return event


def verify_ledger() -> Dict[str, Any]:
    ledger = read_json(FILES["ledger"], [])
    if not ledger:
        return {"ok": True, "message": "Ledger vazio.", "tampered_at": None}
    prev = "GENESIS"
    for idx, event in enumerate(ledger):
        raw = {
            "timestamp": event["timestamp"],
            "event_type": event["event_type"],
            "actor_id": event["actor_id"],
            "actor_name": event["actor_name"],
            "entity_type": event["entity_type"],
            "entity_id": event["entity_id"],
            "action": event["action"],
            "payload": event["payload"],
            "previous_hash": event["previous_hash"],
        }
        expected = sha(raw)
        if event["previous_hash"] != prev or event["event_hash"] != expected:
            return {"ok": False, "message": "Quebra de integridade detectada.", "tampered_at": idx}
        prev = event["event_hash"]
    return {"ok": True, "message": "Cadeia íntegra.", "tampered_at": None}


def current_actor() -> Tuple[str, str]:
    if st.session_state.get("admin_logged_in"):
        return "admin:" + st.session_state.get("admin_username", "admin"), st.session_state.get("admin_username", "Admin")
    return st.session_state.get("user_id", "anon"), st.session_state.get("animal_name", "Visitante")


def login_ok(username: str, password: str) -> bool:
    admins = read_json(FILES["admins"], [])
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    return any(a["username"] == username and a["password_hash"] == password_hash for a in admins)


def init_session() -> None:
    defaults = {
        "user_id": human_id("usr"),
        "animal_name": animal_name(),
        "step": "intro",
        "admin_logged_in": False,
        "admin_username": "",
        "selected_obra_id": None,
        "contrast_mode": False,
        "font_scale": 1.0,
        "show_white_bg": True,
        "show_access_panel": True,
        "reader_last_text": "",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def css() -> str:
    font_scale = st.session_state.get("font_scale", 1.0)
    contrast = st.session_state.get("contrast_mode", False)
    bg = "#ffffff" if st.session_state.get("show_white_bg", True) else "#f4f7fb"
    text = "#171717" if not contrast else "#000000"
    muted = "#4b5563" if not contrast else "#111111"
    card = "rgba(255,255,255,0.90)" if not contrast else "rgba(255,255,255,0.98)"
    border = "rgba(148,163,184,0.28)" if not contrast else "rgba(0,0,0,0.38)"
    shadow = "0 18px 48px rgba(15,23,42,0.08)"
    button_bg = "rgba(255,255,255,0.70)" if not contrast else "rgba(255,255,255,0.96)"
    accent = "#355df4" if not contrast else "#000000"
    sidebar_bg = "linear-gradient(180deg, #111827 0%, #1f2937 100%)"
    return f"""
    <style>
    * {{
        font-family: "Times New Roman", Times, serif !important;
        box-sizing: border-box;
    }}
    html, body, [class*="css"] {{
        font-size: {font_scale:.2f}rem;
    }}
    body {{ color: {text}; }}
    .stApp {{
        background: {bg};
        color: {text};
    }}
    [data-testid="stSidebar"] {{
        background: {sidebar_bg};
        border-right: 1px solid rgba(255,255,255,0.08);
    }}
    [data-testid="stSidebar"] * {{
        color: #f8fafc !important;
    }}
    [data-testid="stSidebar"] hr {{
        border-color: rgba(255,255,255,0.10) !important;
    }}
    [data-testid="stSidebar"] .stRadio label {{
        color: #f8fafc !important;
    }}
    h1,h2,h3,h4,h5,h6,p,span,label,div,li {{
        color: {text};
    }}
    .main-shell {{
        max-width: 1560px;
        margin: 0 auto;
        padding: 1rem 1.6rem 4rem 1.6rem;
    }}
    .hero {{
        padding: 2rem 2.2rem;
        border-radius: 30px;
        background: linear-gradient(135deg, rgba(255,255,255,0.96), rgba(242,246,255,0.92));
        border: 1px solid {border};
        box-shadow: {shadow};
        margin: 0.2rem 0 1.2rem 0;
    }}
    .hero h1 {{
        font-size: clamp(2.3rem, 4vw, 4rem);
        line-height: 1.05;
        margin-bottom: 0.4rem;
        color: {text};
    }}
    .glass {{
        background: {card};
        backdrop-filter: blur(18px) saturate(150%);
        border: 1px solid {border};
        border-radius: 24px;
        padding: 1.2rem 1.3rem;
        box-shadow: {shadow};
    }}
    .section-card {{
        background: {card};
        backdrop-filter: blur(18px) saturate(150%);
        border: 1px solid {border};
        border-radius: 26px;
        padding: 1.35rem 1.35rem;
        box-shadow: {shadow};
        margin: 0.9rem 0;
    }}
    .metric-card {{
        background: {card};
        backdrop-filter: blur(20px);
        border: 1px solid {border};
        border-radius: 22px;
        padding: 1.1rem 1.2rem;
        box-shadow: {shadow};
        min-height: 136px;
    }}
    .metric-label {{
        font-size: 0.84rem;
        text-transform: uppercase;
        letter-spacing: 0.08rem;
        color: {muted};
    }}
    .metric-value {{
        font-size: 2.1rem;
        font-weight: 700;
        margin-top: 0.45rem;
        color: {text};
    }}
    .metric-sub {{
        font-size: 0.94rem;
        color: {muted};
        margin-top: 0.32rem;
    }}
    .chip {{
        display: inline-block;
        padding: 0.34rem 0.9rem;
        border-radius: 999px;
        margin: 0.18rem;
        background: rgba(53,93,244,0.10);
        border: 1px solid rgba(53,93,244,0.22);
        color: {accent};
        font-size: 0.96rem;
    }}
    .work-card {{
        background: {card};
        border: 1px solid {border};
        border-radius: 28px;
        padding: 1.2rem;
        box-shadow: {shadow};
        margin-bottom: 1.15rem;
    }}
    .work-meta {{
        background: rgba(243,246,252,0.86);
        border: 1px solid {border};
        border-radius: 20px;
        padding: 1rem;
        margin-bottom: 0.9rem;
    }}
    .work-caption {{
        font-size: 1rem;
        line-height: 1.75;
        color: {muted};
    }}
    .tag-zone {{
        background: rgba(247,249,252,0.94);
        border: 1px dashed rgba(53,93,244,0.25);
        border-radius: 22px;
        padding: 1rem 1rem 0.4rem 1rem;
        margin-top: 0.9rem;
    }}
    .tag-help {{
        font-size: 0.94rem;
        color: {muted};
        margin-bottom: 0.6rem;
    }}
    .mini-title {{
        font-size: 1.08rem;
        font-weight: 700;
        margin-bottom: 0.35rem;
        color: {text};
    }}
    .side-access {{
        position: static;
        width: min(100%, 360px);
        margin: 0 0 1rem auto;
        background: {card};
        border: 1px solid {border};
        border-radius: 22px;
        padding: 1rem;
        box-shadow: {shadow};
    }}
    .side-access h4 {{
        margin: 0 0 0.45rem 0;
        font-size: 1.1rem;
        color: {text};
    }}
    .mini-help {{
        font-size: 0.92rem;
        color: {muted};
        line-height: 1.55;
    }}
    .ledger-row {{
        border-left: 4px solid {accent};
        background: rgba(53,93,244,0.05);
        padding: 0.78rem 0.9rem;
        border-radius: 14px;
        margin: 0.38rem 0;
    }}
    .validation-card {{
        border-left: 5px solid #eab308;
        background: rgba(234,179,8,0.08);
        border-radius: 18px;
        padding: 0.95rem;
        margin-bottom: 0.75rem;
    }}
    .ontology-block {{
        border-left: 5px solid #7c3aed;
        background: rgba(124,58,237,0.08);
        border-radius: 18px;
        padding: 0.95rem;
        margin-bottom: 0.75rem;
    }}
    .timeline-block {{
        border-left: 5px solid #0ea5e9;
        background: rgba(14,165,233,0.08);
        border-radius: 18px;
        padding: 0.95rem;
        margin-bottom: 0.75rem;
    }}
    .stButton > button, .stDownloadButton > button {{
        width: 100%;
        border-radius: 999px !important;
        border: 1px solid {border} !important;
        background: {button_bg} !important;
        color: {text} !important;
        backdrop-filter: blur(18px) saturate(140%) !important;
        box-shadow: {shadow} !important;
        font-weight: 700 !important;
        padding: 0.72rem 1.05rem !important;
    }}
    .stButton > button:hover, .stDownloadButton > button:hover {{
        border-color: rgba(53,93,244,0.42) !important;
        transform: translateY(-1px);
    }}
    .stTextInput input, .stTextArea textarea, .stSelectbox select, .stMultiSelect div[data-baseweb="select"], .stNumberInput input {{
        border-radius: 16px !important;
        background: rgba(255,255,255,0.96) !important;
        border: 1px solid {border} !important;
        color: {text} !important;
    }}
    .stTextArea textarea {{
        min-height: 120px;
        line-height: 1.55;
    }}
    .stTabs [data-baseweb="tab-list"] {{
        gap: 0.45rem;
        background: rgba(255,255,255,0.75);
        border-radius: 16px;
        padding: 0.38rem;
    }}
    .stTabs [data-baseweb="tab"] {{
        border-radius: 12px;
        background: rgba(255,255,255,0.82);
        border: 1px solid {border};
        padding: 0.65rem 0.95rem;
    }}
    .stTabs [aria-selected="true"] {{
        background: rgba(53,93,244,0.12) !important;
    }}
    details {{
        background: rgba(248,250,252,0.96);
        border: 1px solid {border};
        border-radius: 18px;
        padding: 0.2rem 0.8rem;
    }}
    summary {{
        color: {text} !important;
        font-weight: 700;
    }}
    .small-note {{
        font-size: 0.92rem;
        color: {muted};
    }}
    footer, #MainMenu, header {{
        visibility: hidden;
    }}
    @media (max-width: 980px) {{
        .main-shell {{
            padding: 0.8rem 0.9rem 3rem 0.9rem;
        }}
        .side-access {{
            width: 100%;
            margin-left: 0;
        }}
    }}
    </style>
    """


def render_shell_start() -> None:
    st.markdown(css(), unsafe_allow_html=True)
    st.markdown("<div class='main-shell'>", unsafe_allow_html=True)


def render_shell_end() -> None:
    st.markdown("</div>", unsafe_allow_html=True)


def hero(title: str, subtitle: str) -> None:
    st.markdown(
        f"""
        <div class="hero">
            <h1 style="margin:0 0 0.3rem 0;">{html.escape(title)}</h1>
            <p style="margin:0;" class="small-note">{html.escape(subtitle)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def card_metric(label: str, value: Any, sub: str = "") -> str:
    return f"""
    <div class="metric-card">
        <div class="metric-label">{html.escape(str(label))}</div>
        <div class="metric-value">{html.escape(str(value))}</div>
        <div class="metric-sub">{html.escape(str(sub))}</div>
    </div>
    """


def speech_button(text: str, key: str, label: str = "Ouvir audiodescrição") -> None:
    clean_text = str(text or "").strip()
    if not clean_text:
        st.caption("Audiodescrição não cadastrada para esta obra.")
        return
    safe_text = json.dumps(clean_text)
    safe_id = re.sub(r"[^a-zA-Z0-9_-]", "_", key)
    components.html(
        f"""
        <div style="margin:0.25rem 0 0.4rem 0;">
            <button id="{safe_id}" onclick="(function(){{
                const utter = new SpeechSynthesisUtterance({safe_text});
                utter.lang = 'pt-BR';
                window.speechSynthesis.cancel();
                window.speechSynthesis.speak(utter);
            }})()" style="
                width:100%;
                border-radius:999px;
                padding:0.82rem 1rem;
                border:1px solid rgba(148,163,184,0.35);
                background:rgba(255,255,255,0.94);
                cursor:pointer;
                font-family:'Times New Roman', serif;
                font-size:1rem;
                font-weight:700;">{html.escape(label)}</button>
        </div>
        """,
        height=72,
    )


def access_panel() -> None:
    if not st.session_state.get("show_access_panel", True):
        return
    st.markdown(
        """
        <div class="side-access">
            <h4>Acessibilidade</h4>
            <div class="mini-help">Painel visível em todo o sistema para contraste, escala da fonte, fundo branco e audiodescrição. Nesta versão ele fica integrado ao layout, sem sobrepor o conteúdo.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def access_controls_inline() -> None:
    with st.expander("Acessibilidade do sistema", expanded=False):
        c1, c2, c3 = st.columns(3)
        with c1:
            st.session_state["font_scale"] = st.slider(
                "Escala da fonte",
                min_value=0.90,
                max_value=1.50,
                value=float(st.session_state.get("font_scale", 1.0)),
                step=0.05,
            )
        with c2:
            st.session_state["contrast_mode"] = st.toggle(
                "Alto contraste",
                value=bool(st.session_state.get("contrast_mode", False)),
            )
        with c3:
            st.session_state["show_white_bg"] = st.toggle(
                "Fundo branco",
                value=bool(st.session_state.get("show_white_bg", True)),
            )


def ngram_set(text: str, n: int = 3) -> set:
    text = normalize(text)
    if len(text) < n:
        return {text} if text else set()
    return {text[i:i+n] for i in range(len(text) - n + 1)}


def similarity(a: str, b: str) -> float:
    aa = normalize(a)
    bb = normalize(b)
    if not aa or not bb:
        return 0.0
    if aa == bb:
        return 1.0
    if aa in bb or bb in aa:
        return 0.65
    sa = set(aa.split())
    sb = set(bb.split())
    word_j = len(sa & sb) / len(sa | sb) if (sa | sb) else 0.0
    nga = ngram_set(aa)
    ngb = ngram_set(bb)
    ng_j = len(nga & ngb) / len(nga | ngb) if (nga | ngb) else 0.0
    return round(0.55 * ng_j + 0.45 * word_j, 4)


def save_user_answers(answers: Dict[str, Any]) -> None:
    users = load_table("users")
    user = {
        "user_id": st.session_state["user_id"],
        "animal_name": st.session_state["animal_name"],
        "timestamp": now_str(),
        **answers,
    }
    users.append(user)
    save_table("users", users)
    actor_id, actor_name = current_actor()
    append_ledger_event(
        event_type="questionnaire_completed",
        actor_id=actor_id,
        actor_name=actor_name,
        entity_type="user",
        entity_id=user["user_id"],
        action="submit_questionnaire",
        payload=answers,
    )


def all_obras_df() -> pd.DataFrame:
    return pd.DataFrame(load_table("obras"))


def all_tags_df() -> pd.DataFrame:
    return pd.DataFrame(load_table("tags"))


def all_users_df() -> pd.DataFrame:
    return pd.DataFrame(load_table("users"))


def all_entities_df() -> pd.DataFrame:
    return pd.DataFrame(load_table("semantic_entities"))


def all_links_df() -> pd.DataFrame:
    return pd.DataFrame(load_table("semantic_links"))


def ontology_df() -> pd.DataFrame:
    return pd.DataFrame(load_table("ontologies"))


def validation_df() -> pd.DataFrame:
    return pd.DataFrame(load_table("validation_queue"))


def ledger_df() -> pd.DataFrame:
    return pd.DataFrame(load_table("ledger"))


def record_tag(obra_id: int, tag_text: str) -> None:
    tags = load_table("tags")
    tag = {
        "id": len(tags) + 1,
        "tag_uid": human_id("tag"),
        "user_id": st.session_state["user_id"],
        "animal_name": st.session_state["animal_name"],
        "obra_id": obra_id,
        "tag": normalize(tag_text),
        "original_tag": tag_text.strip(),
        "timestamp": now_str(),
        "mapped_controlled_term": map_tag_to_controlled(tag_text),
        "validation_status": "pendente",
    }
    tags.append(tag)
    save_table("tags", tags)
    actor_id, actor_name = current_actor()
    append_ledger_event(
        event_type="tag_created",
        actor_id=actor_id,
        actor_name=actor_name,
        entity_type="tag",
        entity_id=tag["tag_uid"],
        action="create_tag",
        payload={"obra_id": obra_id, "tag": tag["tag"], "mapped": tag["mapped_controlled_term"]},
    )
    queue = load_table("validation_queue")
    queue.append({
        "id": human_id("val"),
        "origin": "tag",
        "source_id": tag["tag_uid"],
        "obra_id": obra_id,
        "suggested_value": tag["tag"],
        "controlled_value": tag["mapped_controlled_term"],
        "kind": "tag_ontology_alignment",
        "status": "pendente",
        "confidence": round(0.55 + min(len(tag["tag"]) / 20, 0.35), 2),
        "created_at": now_str(),
        "reviewed_at": "",
        "review_note": "",
    })
    save_table("validation_queue", queue)


def map_tag_to_controlled(tag_text: str) -> str:
    tag = normalize(tag_text)
    for onto in load_table("ontologies"):
        mappings = onto.get("mapeamentos_folksonomia", [])
        for item in mappings:
            if normalize(item.get("livre")) == tag:
                return item.get("controlado", "")
    if tag in MATERIALS:
        return MATERIALS[tag]
    if tag in TECHNIQUES:
        return TECHNIQUES[tag]
    if tag in THEMES:
        return THEMES[tag]
    return ""


def extract_entities_for_obra(obra: Dict[str, Any]) -> List[Dict[str, Any]]:
    text_fields = [
        obra.get("titulo", ""),
        obra.get("artista", ""),
        obra.get("colecao", ""),
        obra.get("periodo", ""),
        obra.get("cronologia", ""),
        obra.get("texto_curatorial", ""),
        obra.get("descricao_museologica", ""),
        obra.get("enciclopedia", ""),
        obra.get("arquivo", ""),
        " ".join(obra.get("tema_tags", [])),
    ]
    corpus = " ".join(str(x) for x in text_fields if x).strip()

    results: List[Dict[str, Any]] = []
    seen = set()

    def add_entity(label: str, etype: str, confidence: float, origin: str) -> None:
        norm = normalize(label)
        if not norm or (etype, norm) in seen:
            return
        seen.add((etype, norm))
        results.append({
            "id": human_id("ent"),
            "obra_id": obra["id"],
            "obra_uid": obra.get("obra_uid", ""),
            "label": label.strip(),
            "label_norm": norm,
            "entity_type": etype,
            "confidence": round(confidence, 2),
            "origin": origin,
            "created_at": now_str(),
            "status": "pendente",
            "canonical_label": disambiguate_label(label, etype),
        })

    for author in KNOWN_AUTHORS:
        if normalize(author) in normalize(corpus):
            add_entity(author, "autor", 0.95, "rule_known_author")

    for col in KNOWN_COLLECTIONS:
        if normalize(col) in normalize(corpus):
            add_entity(col, "colecao", 0.90, "rule_known_collection")

    if obra.get("artista"):
        add_entity(obra["artista"], "autor", 0.98, "field_artista")
    if obra.get("colecao"):
        add_entity(obra["colecao"], "colecao", 0.96, "field_colecao")
    if obra.get("periodo"):
        add_entity(obra["periodo"], "periodo", 0.90, "field_periodo")
    if obra.get("material"):
        add_entity(obra["material"], "material", 0.94, "field_material")
    if obra.get("tecnica"):
        add_entity(obra["tecnica"], "tecnica", 0.94, "field_tecnica")

    for term in obra.get("tema_tags", []):
        add_entity(term, "tema", 0.88, "field_tema_tags")

    # Capitalized token groups as probable named entities.
    candidates = set(re.findall(r"\b[A-ZÁÉÍÓÚÂÊÔÃÕÇ][\wÁÉÍÓÚÂÊÔÃÕÇà-ú-]+(?:\s+[A-ZÁÉÍÓÚÂÊÔÃÕÇ][\wÁÉÍÓÚÂÊÔÃÕÇà-ú-]+){0,3}", corpus))
    for cand in candidates:
        if len(cand) > 2 and normalize(cand) not in {normalize(x) for x in ["Guerra Civil Espanhola", "Século XX", "Renascimento"]}:
            add_entity(cand, "entidade_nomeada", 0.62, "regex_capitalized_phrase")

    for key, val in MATERIALS.items():
        if key in normalize(corpus):
            add_entity(val, "material", 0.80, "rule_material_keyword")
    for key, val in TECHNIQUES.items():
        if key in normalize(corpus):
            add_entity(val, "tecnica", 0.80, "rule_tecnica_keyword")
    for key, val in THEMES.items():
        if key in normalize(corpus):
            add_entity(val, "tema", 0.78, "rule_tema_keyword")

    return results


def disambiguate_label(label: str, entity_type: str) -> str:
    norm = normalize(label)
    if entity_type == "autor":
        for author in KNOWN_AUTHORS:
            if similarity(author, label) >= 0.75:
                return author
    if entity_type == "colecao":
        for col in KNOWN_COLLECTIONS:
            if similarity(col, label) >= 0.75:
                return col
    if entity_type == "tema":
        for key, val in THEMES.items():
            if similarity(key, norm) >= 0.85:
                return val
    return label.strip()


def persist_extractions(obra: Dict[str, Any], extracted: List[Dict[str, Any]]) -> int:
    if not extracted:
        return 0
    entities = load_table("semantic_entities")
    links = load_table("semantic_links")
    queue = load_table("validation_queue")

    existing = {(e["obra_id"], e["entity_type"], e["label_norm"]) for e in entities}
    new_count = 0
    for ent in extracted:
        key = (ent["obra_id"], ent["entity_type"], ent["label_norm"])
        if key in existing:
            continue
        entities.append(ent)
        existing.add(key)
        new_count += 1

        prop = infer_property_for_entity_type(ent["entity_type"])
        link = {
            "id": human_id("lnk"),
            "obra_id": obra["id"],
            "source_uid": obra.get("obra_uid"),
            "target_entity_id": ent["id"],
            "relation": prop,
            "weight": ent["confidence"],
            "validated": False,
            "created_at": now_str(),
        }
        links.append(link)

        queue.append({
            "id": human_id("val"),
            "origin": "semantic_extraction",
            "source_id": ent["id"],
            "obra_id": obra["id"],
            "suggested_value": ent["label"],
            "controlled_value": ent["canonical_label"],
            "kind": ent["entity_type"],
            "status": "pendente",
            "confidence": ent["confidence"],
            "created_at": now_str(),
            "reviewed_at": "",
            "review_note": "",
        })

        actor_id, actor_name = current_actor()
        append_ledger_event(
            event_type="semantic_extraction_created",
            actor_id=actor_id,
            actor_name=actor_name,
            entity_type="semantic_entity",
            entity_id=ent["id"],
            action="extract_entity",
            payload={"obra_id": obra["id"], "label": ent["label"], "entity_type": ent["entity_type"]},
        )
    save_table("semantic_entities", entities)
    save_table("semantic_links", links)
    save_table("validation_queue", queue)
    return new_count


def infer_property_for_entity_type(entity_type: str) -> str:
    return {
        "autor": "criado_por",
        "colecao": "pertence_a",
        "material": "tem_material",
        "tecnica": "tem_tecnica",
        "tema": "tem_tema",
        "periodo": "situada_em",
    }.get(entity_type, "relaciona_entidade")


def graph_from_data() -> Tuple[Any, List[Dict[str, Any]]]:
    if nx is None:
        return None, []
    obras = load_table("obras")
    entities = load_table("semantic_entities")
    links = load_table("semantic_links")
    tags = load_table("tags")

    G = nx.Graph()
    nodes_meta: List[Dict[str, Any]] = []

    for obra in obras:
        node_id = f"obra:{obra['id']}"
        G.add_node(node_id, label=obra["titulo"], group="obra")
        nodes_meta.append({"node_id": node_id, "label": obra["titulo"], "group": "obra"})

    entity_by_id = {e["id"]: e for e in entities}
    for ent in entities:
        node_id = f"ent:{ent['id']}"
        G.add_node(node_id, label=ent["canonical_label"], group=ent["entity_type"])
        nodes_meta.append({"node_id": node_id, "label": ent["canonical_label"], "group": ent["entity_type"]})

    for link in links:
        s = f"obra:{link['obra_id']}"
        ent = entity_by_id.get(link["target_entity_id"])
        if not ent:
            continue
        t = f"ent:{ent['id']}"
        G.add_edge(s, t, weight=link.get("weight", 0.5), relation=link.get("relation", "relaciona"))

    # Folksonomia nodes
    grouped_tags = defaultdict(list)
    for tag in tags:
        grouped_tags[(tag["obra_id"], tag["tag"])].append(tag)
    for (obra_id, tag_text), rows in grouped_tags.items():
        node_id = f"tag:{slug(tag_text)}:{obra_id}"
        G.add_node(node_id, label=tag_text, group="tag")
        nodes_meta.append({"node_id": node_id, "label": tag_text, "group": "tag"})
        G.add_edge(f"obra:{obra_id}", node_id, weight=min(1.0, 0.2 + 0.1 * len(rows)), relation="tag")
    return G, nodes_meta


def render_plotly_graph() -> None:
    G, meta = graph_from_data()
    if G is None or go is None:
        st.info("Instale plotly e networkx para visualizar a teia 3D.")
        return
    if len(G.nodes) == 0:
        st.info("Sem nós suficientes para a teia 3D.")
        return
    pos = nx.spring_layout(G, dim=3, seed=42, k=0.9 / math.sqrt(max(len(G.nodes), 1)))
    edge_x, edge_y, edge_z = [], [], []
    for e0, e1 in G.edges():
        x0, y0, z0 = pos[e0]
        x1, y1, z1 = pos[e1]
        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]
        edge_z += [z0, z1, None]

    nodes = list(G.nodes())
    x = [pos[n][0] for n in nodes]
    y = [pos[n][1] for n in nodes]
    z = [pos[n][2] for n in nodes]
    labels = [G.nodes[n].get("label", n) for n in nodes]
    groups = [G.nodes[n].get("group", "outro") for n in nodes]

    color_map = {
        "obra": "#325bff",
        "autor": "#8b5cf6",
        "colecao": "#0ea5e9",
        "material": "#10b981",
        "tecnica": "#f59e0b",
        "tema": "#ef4444",
        "periodo": "#14b8a6",
        "tag": "#64748b",
        "entidade_nomeada": "#a855f7",
    }
    colors = [color_map.get(g, "#94a3b8") for g in groups]
    sizes = [16 if g == "obra" else 9 if g == "tag" else 11 for g in groups]
    hover = [f"{lab}<br>Tipo: {grp}" for lab, grp in zip(labels, groups)]

    fig = go.Figure()
    fig.add_trace(go.Scatter3d(
        x=edge_x, y=edge_y, z=edge_z,
        mode="lines",
        line=dict(width=2, color="rgba(100,116,139,0.45)"),
        hoverinfo="none",
        name="Relações"
    ))
    fig.add_trace(go.Scatter3d(
        x=x, y=y, z=z,
        mode="markers+text",
        text=labels,
        textposition="top center",
        hovertext=hover,
        hoverinfo="text",
        marker=dict(size=sizes, color=colors, opacity=0.88),
        name="Nós"
    ))
    fig.update_layout(
        height=720,
        margin=dict(l=0, r=0, t=15, b=0),
        scene=dict(
            xaxis=dict(showbackground=False, visible=False),
            yaxis=dict(showbackground=False, visible=False),
            zaxis=dict(showbackground=False, visible=False),
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True)


def intro_page() -> None:
    hero(APP_TITLE, "Plataforma com base museológica, ontologias, extração semântica, teia 3D, ledger analítico e validação humana.")
    access_controls_inline()
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown("### Questionário de entrada")
    with st.form("intro_form"):
        c1, c2 = st.columns(2)
        with c1:
            q1 = st.selectbox(
                "Qual é o seu nível de familiaridade com museus?",
                ["Nunca visito", "Raramente", "Ocasionalmente", "Frequentemente", "Profissional da área"],
            )
            q2 = st.selectbox(
                "Você já ouviu falar sobre documentação museológica?",
                ["Nunca ouvi falar", "Já ouvi, mas não sei o que é", "Tenho uma ideia básica", "Conheço bem", "Atuo com isso"],
            )
        with c2:
            q3 = st.text_area(
                "O que você entende por tags, ontologias ou metadados em acervos?",
                height=180,
                placeholder="Escreva livremente.",
            )
        ok = st.form_submit_button("Entrar na plataforma")
        if ok:
            if not q3.strip():
                st.error("Preencha a resposta aberta.")
            else:
                save_user_answers({"q1": q1, "q2": q2, "q3": q3})
                st.session_state["step"] = "completed"
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def public_area() -> None:
    hero("Explorar obras e contribuir", f"Usuário anônimo: {st.session_state['animal_name']}")
    access_controls_inline()
    obras = load_table("obras")

    c1, c2 = st.columns([2, 1])
    with c1:
        filtro = st.text_input("Filtrar obras por título, artista, período ou material")
    with c2:
        ordenacao = st.selectbox("Ordenar", ["ID crescente", "ID decrescente", "Título"])
    filtered = obras
    if filtro.strip():
        nf = normalize(filtro)
        filtered = [
            o for o in obras
            if nf in normalize(o["titulo"]) or nf in normalize(o["artista"]) or nf in normalize(o.get("periodo", "")) or nf in normalize(o.get("material", ""))
        ]
    if ordenacao == "ID crescente":
        filtered = sorted(filtered, key=lambda x: x["id"])
    elif ordenacao == "ID decrescente":
        filtered = sorted(filtered, key=lambda x: x["id"], reverse=True)
    else:
        filtered = sorted(filtered, key=lambda x: normalize(x["titulo"]))

    if not filtered:
        st.info("Nenhuma obra encontrada com esse filtro.")
        return

    ut = all_tags_df()
    for obra in filtered:
        st.markdown("<div class='work-card'>", unsafe_allow_html=True)
        left, right = st.columns([1.1, 1], gap="large")
        with left:
            st.image(obra["imagem"], use_container_width=True)
            st.markdown(f"### #{obra['id']} — {obra['titulo']}")
            st.markdown(f"<div class='work-caption'>{html.escape(obra.get('descricao_museologica', ''))}</div>", unsafe_allow_html=True)
            speech_button(obra.get("audio_descricao", ""), key=f"speech_{obra['id']}")
        with right:
            st.markdown("<div class='work-meta'>", unsafe_allow_html=True)
            st.markdown(f"""**Artista:** {obra['artista']}  
**Ano:** {obra['ano']}  
**Período:** {obra.get('periodo','—')}""")
            st.markdown(f"""**Material:** {obra.get('material','—')}  
**Técnica:** {obra.get('tecnica','—')}  
**Coleção:** {obra.get('colecao','—')}""")
            onto_html = " ".join([f"<span class='chip'>{html.escape(str(x))}</span>" for x in obra.get("ontologias", [])]) or "<span class='small-note'>Sem ontologia associada.</span>"
            st.markdown("**Ontologias associadas:**", unsafe_allow_html=True)
            st.markdown(onto_html, unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

            with st.expander("Texto curatorial, enciclopédico e relações semânticas", expanded=False):
                st.write(obra.get("texto_curatorial", ""))
                st.write(obra.get("enciclopedia", ""))
                rel = obra.get("arquivo", "")
                if rel:
                    st.markdown(f"**Arquivo/institucional:** {rel}")

            st.markdown("<div class='tag-zone'>", unsafe_allow_html=True)
            st.markdown("<div class='mini-title'>Adicionar tag</div>", unsafe_allow_html=True)
            st.markdown("<div class='tag-help'>Escreva uma ou mais palavras que descrevam a obra. Você pode usar cor, tema, emoção, material, técnica ou contexto. O sistema vai alinhar a tag às ontologias e registrar a trilha analítica.</div>", unsafe_allow_html=True)
            sugestoes = obra.get("tags_sugeridas", [])[:8]
            if sugestoes:
                st.markdown("**Sugestões rápidas:**", unsafe_allow_html=True)
                st.markdown(" ".join([f"<span class='chip'>{html.escape(str(s))}</span>" for s in sugestoes]), unsafe_allow_html=True)
            with st.form(f"tag_form_{obra['id']}", clear_on_submit=True):
                tag = st.text_area(
                    "Tag livre",
                    height=110,
                    placeholder="Ex.: guerra, dor, preto e branco, cavalo, fragmentação, sofrimento coletivo...",
                )
                sent = st.form_submit_button("Salvar tag")
                if sent:
                    if tag.strip():
                        record_tag(obra["id"], tag)
                        st.success("Tag registrada e enviada para alinhamento/validação.")
                        st.rerun()
                    else:
                        st.error("Digite uma tag antes de salvar.")
            if not ut.empty:
                local = ut[(ut["obra_id"] == obra["id"]) & (ut["user_id"] == st.session_state["user_id"])]
                if not local.empty:
                    st.markdown("**Suas tags nesta obra:**")
                    st.markdown(" ".join([f"<span class='chip'>{html.escape(str(t))}</span>" for t in local['original_tag'].fillna(local['tag']).tolist()]), unsafe_allow_html=True)
                else:
                    st.caption("Você ainda não adicionou tags para esta obra.")
            st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)


def admin_login_or_dashboard() -> None:
    if not st.session_state.get("admin_logged_in"):
        hero("Área administrativa", "Login restrito para gestão museológica, semântica, blockchain analítico e acessibilidade.")
        access_controls_inline()
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        with st.form("admin_login"):
            username = st.text_input("Usuário")
            password = st.text_input("Senha", type="password")
            ok = st.form_submit_button("Entrar")
            if ok:
                if login_ok(username, password):
                    st.session_state["admin_logged_in"] = True
                    st.session_state["admin_username"] = username
                    append_ledger_event(
                        event_type="admin_login",
                        actor_id=f"admin:{username}",
                        actor_name=username,
                        entity_type="admin",
                        entity_id=username,
                        action="login",
                        payload={"status": "ok"},
                    )
                    st.rerun()
                st.error("Credenciais inválidas.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    hero("Dashboard administrativo", "Seis camadas do sistema, com foco reforçado em acessibilidade transversal e trilha de proveniência analítica.")
    access_controls_inline()
    tabs = st.tabs([
        "Visão geral",
        "Base museológica",
        "Ontologias",
        "Camada semântica",
        "Teia 3D",
        "Validação humana",
        "Ledger analítico",
        "Acessibilidade",
        "Exportação",
    ])
    with tabs[0]:
        admin_overview()
    with tabs[1]:
        admin_museum_base()
    with tabs[2]:
        admin_ontologies()
    with tabs[3]:
        admin_semantic_layer()
    with tabs[4]:
        admin_graph_layer()
    with tabs[5]:
        admin_validation_layer()
    with tabs[6]:
        admin_ledger_layer()
    with tabs[7]:
        admin_accessibility_layer()
    with tabs[8]:
        admin_export_layer()

    if st.button("Sair da área administrativa"):
        append_ledger_event(
            event_type="admin_logout",
            actor_id=f"admin:{st.session_state.get('admin_username', 'admin')}",
            actor_name=st.session_state.get("admin_username", "admin"),
            entity_type="admin",
            entity_id=st.session_state.get("admin_username", "admin"),
            action="logout",
            payload={"status": "ok"},
        )
        st.session_state["admin_logged_in"] = False
        st.session_state["admin_username"] = ""
        st.rerun()


def admin_overview() -> None:
    obras = all_obras_df()
    tags = all_tags_df()
    users = all_users_df()
    ontos = ontology_df()
    validations = validation_df()
    ledger = ledger_df()
    entities = all_entities_df()

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        st.markdown(card_metric("Obras", len(obras), "base museológica"), unsafe_allow_html=True)
    with c2:
        st.markdown(card_metric("Tags", len(tags), "folksonomia"), unsafe_allow_html=True)
    with c3:
        st.markdown(card_metric("Usuários", users["user_id"].nunique() if not users.empty else 0, "participantes"), unsafe_allow_html=True)
    with c4:
        st.markdown(card_metric("Ontologias", len(ontos), "pré-carregadas e editáveis"), unsafe_allow_html=True)
    with c5:
        st.markdown(card_metric("Entidades", len(entities), "extrações e relações"), unsafe_allow_html=True)
    with c6:
        st.markdown(card_metric("Pendências", int((validations["status"] == "pendente").sum()) if not validations.empty else 0, "fila humana"), unsafe_allow_html=True)

    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown("### Diagnóstico estrutural")
    st.markdown("""
    - **Camada 1:** base museológica com obras, textos curatoriais, cronologias, enciclopédia e arquivo.
    - **Camada 2:** ontologias e vocabulários híbridos pré-marcados.
    - **Camada 3:** leitura semântica por regras, entidades e desambiguação.
    - **Camada 4:** grafo de conhecimento 3D com obras, entidades e tags.
    - **Camada 5:** ledger analítico append-only com hash encadeado.
    - **Camada 6:** validação humana para revisar extrações e alinhamentos.
    """)
    if not tags.empty:
        st.markdown("### Evolução temporal das tags")
        tf = tags.copy()
        tf["timestamp"] = pd.to_datetime(tf["timestamp"], errors="coerce")
        tf["dia"] = tf["timestamp"].dt.date
        daily = tf.groupby("dia").size().rename("Tags")
        st.line_chart(daily)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown("### Eventos recentes do ledger")
    if ledger.empty:
        st.info("Sem eventos.")
    else:
        recent = ledger.sort_values("index", ascending=False).head(10)
        for _, row in recent.iterrows():
            st.markdown(
                f"<div class='ledger-row'><strong>{row['event_type']}</strong> · {row['action']} · "
                f"{row['entity_type']} / {row['entity_id']}<br><span class='small-note'>{row['timestamp']} · hash {row['event_hash'][:18]}…</span></div>",
                unsafe_allow_html=True,
            )
    st.markdown("</div>", unsafe_allow_html=True)


def admin_museum_base() -> None:
    obras = load_table("obras")
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown("### Gestão da base museológica")
    t1, t2 = st.tabs(["Listar e excluir", "Adicionar/editar"])
    with t1:
        if not obras:
            st.info("Nenhuma obra cadastrada.")
        for obra in obras:
            with st.container():
                c1, c2, c3 = st.columns([1, 2.6, 0.8])
                with c1:
                    st.image(obra["imagem"], use_container_width=True)
                with c2:
                    st.markdown(f"#### #{obra['id']} — {obra['titulo']}")
                    st.write(f"**Artista:** {obra['artista']} · **Ano:** {obra['ano']} · **Coleção:** {obra.get('colecao','—')}")
                    st.write(f"**Material:** {obra.get('material','—')} · **Técnica:** {obra.get('tecnica','—')}")
                    st.caption(obra.get("descricao_museologica", ""))
                with c3:
                    if st.button("Excluir obra", key=f"del_obra_{obra['id']}"):
                        new_rows = [o for o in obras if o["id"] != obra["id"]]
                        save_table("obras", new_rows)
                        actor_id, actor_name = current_actor()
                        append_ledger_event(
                            event_type="obra_deleted",
                            actor_id=actor_id,
                            actor_name=actor_name,
                            entity_type="obra",
                            entity_id=str(obra["id"]),
                            action="delete",
                            payload={"titulo": obra["titulo"]},
                        )
                        st.rerun()
                st.divider()
    with t2:
        existing_ids = [o["id"] for o in obras] or [0]
        with st.form("form_add_obra"):
            c1, c2 = st.columns(2)
            with c1:
                titulo = st.text_input("Título")
                artista = st.text_input("Artista")
                ano = st.text_input("Ano")
                colecao = st.text_input("Coleção")
                periodo = st.text_input("Período")
                material = st.text_input("Material")
                tecnica = st.text_input("Técnica")
                dimensoes = st.text_input("Dimensões")
            with c2:
                proveniencia = st.text_input("Proveniência")
                cronologia = st.text_area("Cronologia", height=90)
                texto_curatorial = st.text_area("Texto curatorial", height=110)
                descricao_museologica = st.text_area("Descrição museológica", height=110)
                enciclopedia = st.text_area("Enciclopédia / contexto", height=90)
                arquivo = st.text_area("Arquivo / dossiê", height=90)
                audio_descricao = st.text_area("Audiodescrição", height=110)
                imagem = st.text_input("URL da imagem")
            tema_tags = st.text_input("Temas iniciais separados por vírgula", placeholder="guerra, memória, resistência")
            ontologias_sel = st.multiselect(
                "Ontologias associadas",
                [o["id"] for o in load_table("ontologies")],
                default=[o["id"] for o in load_table("ontologies")][:2],
            )
            ok = st.form_submit_button("Salvar nova obra")
            if ok:
                if not (titulo and artista and imagem):
                    st.error("Título, artista e imagem são obrigatórios.")
                else:
                    nid = max(existing_ids) + 1
                    obra = {
                        "id": nid,
                        "obra_uid": human_id("obra"),
                        "titulo": titulo,
                        "artista": artista,
                        "ano": ano,
                        "colecao": colecao,
                        "periodo": periodo,
                        "material": material,
                        "tecnica": tecnica,
                        "dimensoes": dimensoes,
                        "proveniencia": proveniencia,
                        "cronologia": cronologia,
                        "texto_curatorial": texto_curatorial,
                        "descricao_museologica": descricao_museologica,
                        "enciclopedia": enciclopedia,
                        "arquivo": arquivo,
                        "audio_descricao": audio_descricao,
                        "imagem": imagem,
                        "ontologias": ontologias_sel,
                        "tema_tags": [x.strip() for x in tema_tags.split(",") if x.strip()],
                        "acessibilidade": {
                            "audiodescricao": bool(audio_descricao.strip()),
                            "alto_contraste": True,
                            "fonte_ampliada": True,
                            "fundo_branco": True,
                        },
                        "status_validacao": "pendente",
                    }
                    obras.append(obra)
                    save_table("obras", obras)
                    actor_id, actor_name = current_actor()
                    append_ledger_event(
                        event_type="obra_created",
                        actor_id=actor_id,
                        actor_name=actor_name,
                        entity_type="obra",
                        entity_id=str(nid),
                        action="create",
                        payload={"titulo": titulo, "artista": artista, "ontologias": ontologias_sel},
                    )
                    st.success("Obra cadastrada.")
                    st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def admin_ontologies() -> None:
    ontologies = load_table("ontologies")
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown("### Ontologias e vocabulários híbridos")
    t1, t2 = st.tabs(["Ontologias carregadas", "Nova ontologia"])
    with t1:
        for onto in ontologies:
            st.markdown(
                f"<div class='ontology-block'><strong>{onto['nome']}</strong><br>"
                f"<span class='small-note'>{onto.get('descricao','')}</span><br>"
                f"<span class='small-note'>Namespace: {onto.get('namespace','')}</span></div>",
                unsafe_allow_html=True,
            )
            c1, c2, c3 = st.columns(3)
            with c1:
                st.write("**Classes**")
                for item in onto.get("classes", []):
                    st.markdown(f"- {item['nome']}")
            with c2:
                st.write("**Propriedades**")
                for item in onto.get("propriedades", []):
                    st.markdown(f"- {item['nome']} ({item['dominio']} → {item['alcance']})")
            with c3:
                st.write("**Termos controlados**")
                for cat, vals in onto.get("termos_controlados", {}).items():
                    st.markdown(f"**{cat}**: {', '.join(vals[:8])}")
            if st.button("Excluir ontologia", key=f"del_onto_{onto['id']}"):
                if len(ontologies) <= 1:
                    st.error("Mantenha pelo menos uma ontologia.")
                else:
                    ontologies = [o for o in ontologies if o["id"] != onto["id"]]
                    save_table("ontologies", ontologies)
                    actor_id, actor_name = current_actor()
                    append_ledger_event(
                        event_type="ontology_deleted",
                        actor_id=actor_id,
                        actor_name=actor_name,
                        entity_type="ontology",
                        entity_id=onto["id"],
                        action="delete",
                        payload={"nome": onto["nome"]},
                    )
                    st.rerun()
            st.divider()
    with t2:
        with st.form("new_ontology"):
            nome = st.text_input("Nome")
            descricao = st.text_area("Descrição", height=90)
            namespace = st.text_input("Namespace", value=f"http://folksonomia.local/ontology/{slug(now_str())}#")
            classes_raw = st.text_area("Classes (uma por linha)", value="obra\nautor\ntema")
            props_raw = st.text_area("Propriedades (formato: nome|dominio|alcance)", value="criado_por|obra|autor\ntem_tema|obra|tema")
            terms_raw = st.text_area("Termos controlados (formato: categoria: termo1, termo2)", value="tema: memória, identidade, território")
            ok = st.form_submit_button("Criar ontologia")
            if ok:
                onto = {
                    "id": "onto_" + slug(nome),
                    "nome": nome,
                    "descricao": descricao,
                    "namespace": namespace,
                    "ativa": True,
                    "classes": [{"id": slug(c), "nome": c.strip(), "descricao": ""} for c in classes_raw.splitlines() if c.strip()],
                    "propriedades": [],
                    "termos_controlados": {},
                    "mapeamentos_folksonomia": [],
                }
                for line in props_raw.splitlines():
                    if "|" in line:
                        p = [x.strip() for x in line.split("|")]
                        if len(p) == 3:
                            onto["propriedades"].append({"id": slug(p[0]), "nome": p[0], "dominio": p[1], "alcance": p[2]})
                for line in terms_raw.splitlines():
                    if ":" in line:
                        cat, vals = line.split(":", 1)
                        onto["termos_controlados"][cat.strip()] = [v.strip() for v in vals.split(",") if v.strip()]
                ontologies.append(onto)
                save_table("ontologies", ontologies)
                actor_id, actor_name = current_actor()
                append_ledger_event(
                    event_type="ontology_created",
                    actor_id=actor_id,
                    actor_name=actor_name,
                    entity_type="ontology",
                    entity_id=onto["id"],
                    action="create",
                    payload={"nome": onto["nome"], "classes": len(onto["classes"])},
                )
                st.success("Ontologia criada.")
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def admin_semantic_layer() -> None:
    obras = load_table("obras")
    entities = all_entities_df()
    links = all_links_df()
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown("### Camada semântica e leitura inteligente")
    if obras:
        options = {f"#{o['id']} — {o['titulo']}": o for o in obras}
        selected_label = st.selectbox("Escolha uma obra para processar", list(options.keys()))
        obra = options[selected_label]
        c1, c2 = st.columns([1, 1])
        with c1:
            if st.button("Executar extração semântica desta obra"):
                extracted = extract_entities_for_obra(obra)
                new_count = persist_extractions(obra, extracted)
                st.success(f"{new_count} entidades novas persistidas.")
                st.rerun()
        with c2:
            if st.button("Executar para todas as obras"):
                total_new = 0
                for item in obras:
                    total_new += persist_extractions(item, extract_entities_for_obra(item))
                st.success(f"{total_new} entidades novas persistidas no lote.")
                st.rerun()
        with st.expander("Pré-visualização da extração", expanded=True):
            preview = pd.DataFrame(extract_entities_for_obra(obra))
            if preview.empty:
                st.info("Sem itens extraídos.")
            else:
                st.dataframe(preview, use_container_width=True, hide_index=True)

    st.markdown("### Entidades persistidas")
    if entities.empty:
        st.info("Nenhuma entidade persistida ainda.")
    else:
        st.dataframe(entities.sort_values("created_at", ascending=False), use_container_width=True, hide_index=True)

    st.markdown("### Relações semânticas")
    if links.empty:
        st.info("Nenhum link semântico persistido.")
    else:
        st.dataframe(links.sort_values("created_at", ascending=False), use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)


def admin_graph_layer() -> None:
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown("### Teia visual 3D")
    st.caption("A teia consolida obras, entidades semânticas e tags de folksonomia em uma rede única.")
    render_plotly_graph()

    entities = all_entities_df()
    tags = all_tags_df()
    if not entities.empty:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Entidades por tipo**")
            st.bar_chart(entities["entity_type"].value_counts())
        with c2:
            if not tags.empty:
                st.markdown("**Top tags**")
                st.bar_chart(tags["tag"].value_counts().head(15))
    st.markdown("</div>", unsafe_allow_html=True)


def admin_validation_layer() -> None:
    queue = load_table("validation_queue")
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown("### Camada humana de validação")
    pending = [q for q in queue if q["status"] == "pendente"]
    st.caption("Esta fila permite revisar extrações automáticas e alinhamentos ontológicos antes da publicação.")
    if not pending:
        st.success("Nenhuma pendência.")
    for item in pending[:50]:
        st.markdown(
            f"<div class='validation-card'><strong>{item['kind']}</strong> · origem: {item['origin']} · obra #{item['obra_id']}<br>"
            f"Sugestão: <strong>{item['suggested_value']}</strong><br>"
            f"Controlado/canônico: <strong>{item.get('controlled_value','')}</strong><br>"
            f"<span class='small-note'>Confiança: {item['confidence']} · criado em {item['created_at']}</span></div>",
            unsafe_allow_html=True,
        )
        c1, c2, c3 = st.columns(3)
        if c1.button("Aprovar", key=f"approve_{item['id']}"):
            update_validation_status(item["id"], "aprovado", "Aprovado sem alteração")
            st.rerun()
        if c2.button("Corrigir", key=f"correct_{item['id']}"):
            update_validation_status(item["id"], "corrigido", "Corrigido pela equipe")
            st.rerun()
        if c3.button("Rejeitar", key=f"reject_{item['id']}"):
            update_validation_status(item["id"], "rejeitado", "Rejeitado pela equipe")
            st.rerun()

    qdf = validation_df()
    if not qdf.empty:
        st.markdown("### Histórico de validação")
        st.dataframe(qdf.sort_values("created_at", ascending=False), use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)


def update_validation_status(item_id: str, status: str, note: str) -> None:
    queue = load_table("validation_queue")
    for item in queue:
        if item["id"] == item_id:
            item["status"] = status
            item["review_note"] = note
            item["reviewed_at"] = now_str()
            actor_id, actor_name = current_actor()
            append_ledger_event(
                event_type="validation_updated",
                actor_id=actor_id,
                actor_name=actor_name,
                entity_type="validation_queue",
                entity_id=item_id,
                action=status,
                payload={"kind": item["kind"], "source_id": item["source_id"], "note": note},
            )
            break
    save_table("validation_queue", queue)


def admin_ledger_layer() -> None:
    ledger = load_table("ledger")
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown("### Ledger analítico tipo blockchain")
    st.markdown("""
    Este módulo não usa blockchain pública. Ele aplica um **ledger append-only com hash encadeado**, o que
    registra autoria, proveniência, alteração e integridade de cada evento crítico do sistema.
    """)
    verification = verify_ledger()
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(card_metric("Eventos", len(ledger), "histórico encadeado"), unsafe_allow_html=True)
    with c2:
        st.markdown(card_metric("Integridade", "OK" if verification["ok"] else "Falha", verification["message"]), unsafe_allow_html=True)
    with c3:
        st.markdown(card_metric("Último hash", ledger[-1]["event_hash"][:16] + "…" if ledger else "—", "âncora atual"), unsafe_allow_html=True)
    if ledger:
        df = pd.DataFrame(ledger)
        st.dataframe(df.sort_values("index", ascending=False), use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)


def admin_accessibility_layer() -> None:
    obras = load_table("obras")
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown("### Acessibilidade transversal")
    st.markdown("""
    Recursos aplicados globalmente:
    - fundo branco como padrão
    - tipografia Times New Roman
    - botões em estilo liquid glass
    - alto contraste
    - escala tipográfica ajustável
    - audiodescrição por síntese de voz no navegador
    """)
    access_controls_inline()
    st.markdown("### Auditoria de acessibilidade por obra")
    rows = []
    for obra in obras:
        acc = obra.get("acessibilidade", {})
        rows.append({
            "Obra": obra["titulo"],
            "Audiodescrição": acc.get("audiodescricao", False),
            "Alto contraste": acc.get("alto_contraste", False),
            "Fonte ampliada": acc.get("fonte_ampliada", False),
            "Fundo branco": acc.get("fundo_branco", False),
            "Texto de audiodescrição": bool(obra.get("audio_descricao", "").strip()),
        })
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    if obras:
        sel = st.selectbox("Testar audiodescrição", [o["titulo"] for o in obras], key="access_speech_test")
        obra = next(o for o in obras if o["titulo"] == sel)
        speech_button(obra.get("audio_descricao", "Sem audiodescrição."), key=f"access_speech_test_btn_{obra['id']}", label="Reproduzir audiodescrição")
    st.markdown("</div>", unsafe_allow_html=True)


def admin_export_layer() -> None:
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown("### Exportação de dados")
    obras = all_obras_df()
    tags = all_tags_df()
    entities = all_entities_df()
    links = all_links_df()
    ledger = ledger_df()
    queue = validation_df()

    exports = {
        "obras.csv": obras.to_csv(index=False).encode("utf-8"),
        "tags.csv": tags.to_csv(index=False).encode("utf-8"),
        "entidades.csv": entities.to_csv(index=False).encode("utf-8"),
        "links.csv": links.to_csv(index=False).encode("utf-8"),
        "ledger.csv": ledger.to_csv(index=False).encode("utf-8"),
        "validacao.csv": queue.to_csv(index=False).encode("utf-8"),
    }
    for fname, content in exports.items():
        st.download_button(f"Baixar {fname}", data=content, file_name=fname, mime="text/csv")
    st.markdown("</div>", unsafe_allow_html=True)


def sidebar_navigation() -> str:
    with st.sidebar:
        st.markdown(f"## {APP_TITLE}")
        st.caption("Sistema em 6 camadas + ledger analítico")
        area = st.radio("Navegação", ["Público", "Administrativo"])
        st.markdown("---")
        st.markdown(f"**Usuário:** {st.session_state.get('animal_name','Visitante')}")
        st.markdown(f"**ID:** {st.session_state.get('user_id','—')[:16]}")
        st.markdown("---")
        st.markdown("**Focos centrais desta versão**")
        st.markdown("- ledger encadeado")
        st.markdown("- acessibilidade transversal")
        st.markdown("- ontologias pré-marcadas")
        st.markdown("- base museológica expandida")
        st.markdown("- fila de validação humana")
    return area


def run() -> None:
    st.set_page_config(page_title=APP_TITLE, layout="wide", initial_sidebar_state="collapsed", page_icon="🧠")
    bootstrap()
    init_session()
    render_shell_start()
    access_panel()
    area = sidebar_navigation()

    if st.session_state.get("step") != "completed":
        intro_page()
    else:
        if area == "Público":
            public_area()
        else:
            admin_login_or_dashboard()

    render_shell_end()


if __name__ == "__main__":
    run()
