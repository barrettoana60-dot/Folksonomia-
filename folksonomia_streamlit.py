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
import math
import re
import unicodedata
from difflib import get_close_matches
from collections import defaultdict
import streamlit.components.v1 as components
from urllib.parse import urlencode, quote_plus
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
warnings.filterwarnings('ignore')

st.set_page_config(
    page_title="Sistema Folksonomia Digital",
    layout="wide",
    initial_sidebar_state="collapsed",
    page_icon="📚"
)

DATA_DIR   = "data"
OBRAS_FILE = os.path.join(DATA_DIR, "obras.json")
TAGS_FILE  = os.path.join(DATA_DIR, "tags.json")
USERS_FILE = os.path.join(DATA_DIR, "users.json")
ADMIN_FILE = os.path.join(DATA_DIR, "admin.json")
ONTOLOGIES_FILE = os.path.join(DATA_DIR, "ontologias.json")
EVENTS_FILE = os.path.join(DATA_DIR, "eventos.json")
METADATA_FILE = os.path.join(DATA_DIR, "metadados_institucionais.json")
OPEN_DATA_FILE = os.path.join(DATA_DIR, "open_data_fontes.json")
INTEROP_FILE = os.path.join(DATA_DIR, "interoperabilidade.json")
ADMIN_USERNAME = "nugep"
ADMIN_PASSWORD = "nugep123"

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

# ── SIMILARIDADE ──────────────────────────────────────────────────────
def ntag(tag):   return tag.lower().strip()
def words(tag):  return set(ntag(tag).split())
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
                if uniq[i] in uniq[j] or uniq[j] in uniq[i]: tipo = "Contenção"
                elif shared: tipo = f"Palavra comum: '{', '.join(shared)}'"
                else: tipo = "Similaridade fonética"
                conns.append({"tag_a":uniq[i],"tag_b":uniq[j],"similaridade":round(s,3),"tipo":tipo})
    conns.sort(key=lambda x: x["similaridade"], reverse=True)
    return conns

def tag_clusters(tags_list, threshold=0.35):
    uniq  = list(set(ntag(t) for t in tags_list))
    conns = tag_connections(uniq, threshold)
    par   = {t:t for t in uniq}
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


STATUS_OPTIONS = ["bruto","sugerido","validado","revisado","publicado"]
THEME_GROUPS = {
    "Religioso": ["religioso","religiao","igreja","santo","santa","cruz","crucifixo","biblia","anjo","oração","oracao","sagrado","sacra","altar","missa"],
    "Guerra": ["guerra","batalha","arma","espada","soldado","militar","combate","violencia","violência","escudo","conflito","canhao","canhão"],
    "Cor": ["azul","vermelho","verde","amarelo","preto","branco","rosa","roxo","lilás","lilas","dourado","prata","cinza","laranja","marrom"],
    "Natureza": ["árvore","arvore","flor","céu","ceu","mar","rio","montanha","sol","lua","estrela","chuva","folha","animal","bosque"],
    "Corpo": ["rosto","olho","mão","mao","corpo","cabeça","cabeca","pé","pe","mão","braço","braco"],
    "Afeto": ["amor","dor","alegria","tristeza","medo","esperança","esperanca","saudade","calma","raiva"],
}

def normalize_text(value):
    value = str(value or "").strip().lower()
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^a-z0-9\s\-_]', ' ', value)
    value = re.sub(r'\s+', ' ', value).strip()
    return value

def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def hash_record(payload):
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()

def safe_int(value, default=0):
    try:
        if value is None:
            return default
        if isinstance(value, str) and not value.strip():
            return default
        return int(float(value))
    except Exception:
        return default

def ledger_label(value, fallback=0):
    number = safe_int(value, fallback)
    return f"REG-{number:06d}"

def normalize_events_dataframe(df):
    if df is None or df.empty:
        return pd.DataFrame()
    norm = df.copy()
    expected_defaults = {
        'ledger_no': None,
        'id': None,
        'timestamp': '—',
        'event_type': '—',
        'actor': 'sistema',
        'actor_role': 'system',
        'entity_type': '—',
        'entity_id': '—',
        'entity_version': 1,
        'origin': 'sistema',
        'automatic': False,
        'status': 'bruto',
        'payload': {},
        'previous_state': None,
        'previous_hash': 'GENESIS',
        'entity_previous_hash': 'GENESIS_ENTITY',
        'semantic_archive_ref': '—',
        'provenance_source': 'sistema',
        'interoperability_refs': [],
        'semantic_snapshot': {},
        'circulation_action': None,
        'circulation_trace': None,
        'event_hash': '',
    }
    for col, default in expected_defaults.items():
        if col not in norm.columns:
            norm[col] = default
    for idx in norm.index:
        if pd.isna(norm.at[idx, 'ledger_no']) or str(norm.at[idx, 'ledger_no']).strip() == '':
            fallback = norm.at[idx, 'id'] if 'id' in norm.columns else idx + 1
            norm.at[idx, 'ledger_no'] = safe_int(fallback, idx + 1)
    norm['ledger_no'] = [safe_int(v, i + 1) for i, v in enumerate(norm['ledger_no'].tolist())]
    norm['entity_version'] = [max(1, safe_int(v, 1)) for v in norm['entity_version'].tolist()]
    norm['entity_id'] = norm['entity_id'].astype(str).replace({'nan': '—', 'None': '—'})
    norm['event_hash'] = norm['event_hash'].astype(str)
    norm['previous_hash'] = norm['previous_hash'].astype(str)
    norm['entity_previous_hash'] = norm['entity_previous_hash'].astype(str)
    return norm

def default_ontologies():
    return [
        {"id": 1, "nome": "Religioso", "categoria": "tema", "descricao": "Vocabulário para referências religiosas e sacras.", "termos": ["religioso","igreja","santo","santa","cruz","anjo","sagrado","altar"], "criado_em": now_str()},
        {"id": 2, "nome": "Guerra", "categoria": "tema", "descricao": "Vocabulário para conflitos, batalhas e violência.", "termos": ["guerra","batalha","arma","soldado","espada","combate","militar"], "criado_em": now_str()},
        {"id": 3, "nome": "Cor", "categoria": "atributo", "descricao": "Vocabulário básico cromático.", "termos": ["azul","vermelho","verde","amarelo","preto","branco","rosa","roxo","dourado"], "criado_em": now_str()},
        {"id": 4, "nome": "Emoção", "categoria": "tema", "descricao": "Vocabulário para afetos e estados emocionais.", "termos": ["triste","alegre","dor","amor","medo","calma","raiva","saudade"], "criado_em": now_str()},
    ]

def default_institution_metadata():
    return {
        "instituicao": "NUGEP / Sistema Folksonomia Digital",
        "colecao": "Acervo experimental",
        "licenca_dados": "Uso interno / open data analítico sob revisão",
        "responsavel": "Administração do sistema",
        "ultima_atualizacao": now_str(),
        "descricao": "Registro analítico e institucional conectado ao fluxo de tags, ontologias, auditoria e proveniência."
    }


def default_open_data_sources():
    return [
        {
            "id": 1,
            "nome": "Wikidata",
            "url": "https://www.wikidata.org/wiki/Wikidata:Data_access",
            "endpoint": "https://www.wikidata.org/w/api.php",
            "tipo": "grafo de conhecimento",
            "licenca": "CC0",
            "autenticacao": "nenhuma",
            "padroes": ["Wikibase", "JSON", "RDF"],
            "descricao": "Base externa para reconciliação de entidades, artistas, lugares, períodos e conceitos.",
            "campos": ["id", "label", "description", "concepturi", "match"],
            "status": "ativo",
            "criado_em": now_str()
        },
        {
            "id": 2,
            "nome": "Europeana",
            "url": "https://pro.europeana.eu/page/apis",
            "endpoint": "https://api.europeana.eu/record/v2/search.json",
            "tipo": "agregador de patrimônio",
            "licenca": "Mista / conforme item",
            "autenticacao": "api_key",
            "padroes": ["EDM", "Dublin Core", "JSON"],
            "descricao": "Fonte para interoperabilidade documental, contexto curatorial e mapeamento de acervos.",
            "campos": ["id", "title", "dcCreator", "type", "dataProvider", "rights"],
            "status": "ativo",
            "criado_em": now_str()
        },
        {
            "id": 3,
            "nome": "IBRAM dados abertos",
            "url": "https://www.gov.br/conecta/catalogo/apis/api-portal-de-dados-abertos",
            "endpoint": "https://dados.gov.br/api/3/action/package_search",
            "tipo": "dados governamentais",
            "licenca": "Aberta / conforme dataset",
            "autenticacao": "token",
            "padroes": ["REST", "JSON", "Portal Brasileiro de Dados Abertos"],
            "descricao": "Referência institucional para conexões com metadados museológicos e registros públicos publicados no Portal de Dados Abertos.",
            "campos": ["title", "notes", "organization", "tags", "resources"],
            "status": "ativo",
            "criado_em": now_str()
        }
    ]

def default_interoperability_registry():
    return [
        {
            "id": 1,
            "dominio_local": "tag",
            "campo_local": "tag",
            "fonte_externa": "Wikidata",
            "campo_externo": "label",
            "tipo_relacao": "closeMatch",
            "objetivo": "Cruzar tags geradas pelos usuários com identificadores externos e ampliar a rede semântica automaticamente.",
            "padrao": "SKOS closeMatch",
            "status": "ativo",
            "modo": "automatico",
            "criado_em": now_str()
        },
        {
            "id": 2,
            "dominio_local": "obra",
            "campo_local": "artista",
            "fonte_externa": "Wikidata",
            "campo_externo": "label",
            "tipo_relacao": "sameAs",
            "objetivo": "Reconciliar autoria local com identificadores externos de artistas.",
            "padrao": "owl:sameAs",
            "status": "ativo",
            "modo": "automatico",
            "criado_em": now_str()
        },
        {
            "id": 3,
            "dominio_local": "metadado_institucional",
            "campo_local": "colecao",
            "fonte_externa": "IBRAM dados abertos",
            "campo_externo": "title",
            "tipo_relacao": "relatedMatch",
            "objetivo": "Conectar a coleção e a instituição a datasets governamentais e catálogos abertos automaticamente.",
            "padrao": "SKOS relatedMatch",
            "status": "ativo",
            "modo": "automatico",
            "criado_em": now_str()
        }
    ]

def ensure_support_files():
    ensure_data_dir()
    if not os.path.exists(ONTOLOGIES_FILE):
        save_json_file(ONTOLOGIES_FILE, default_ontologies())
    if not os.path.exists(EVENTS_FILE):
        save_json_file(EVENTS_FILE, [])
    if not os.path.exists(METADATA_FILE):
        save_json_file(METADATA_FILE, default_institution_metadata())
    if not os.path.exists(OPEN_DATA_FILE):
        save_json_file(OPEN_DATA_FILE, default_open_data_sources())
    if not os.path.exists(INTEROP_FILE):
        save_json_file(INTEROP_FILE, default_interoperability_registry())

def load_ontologies():
    ensure_support_files()
    onts = load_json_file(ONTOLOGIES_FILE, default_ontologies())
    return onts if isinstance(onts, list) else default_ontologies()

def save_ontologies(ontologies):
    return save_json_file(ONTOLOGIES_FILE, ontologies)

def load_institution_metadata():
    ensure_support_files()
    meta = load_json_file(METADATA_FILE, default_institution_metadata())
    if not isinstance(meta, dict):
        meta = default_institution_metadata()
    return meta

def save_institution_metadata(meta):
    meta = dict(meta or {})
    meta["ultima_atualizacao"] = now_str()
    return save_json_file(METADATA_FILE, meta)


def _normalize_status_value(value):
    if isinstance(value, bool):
        return 'ativo' if value else 'inativo'
    txt = str(value or '').strip()
    return txt if txt else 'ativo'


def normalize_open_data_source_entry(item, idx=1):
    if isinstance(item, str):
        return {
            'id': idx,
            'nome': item,
            'url': '',
            'endpoint': '',
            'tipo': 'fonte externa',
            'licenca': 'não informada',
            'autenticacao': 'não informada',
            'padroes': [],
            'descricao': '',
            'campos': [],
            'status': 'ativo',
            'criado_em': now_str(),
        }
    if not isinstance(item, dict):
        return {
            'id': idx,
            'nome': f'Fonte {idx}',
            'url': '',
            'endpoint': '',
            'tipo': 'fonte externa',
            'licenca': 'não informada',
            'autenticacao': 'não informada',
            'padroes': [],
            'descricao': '',
            'campos': [],
            'status': 'ativo',
            'criado_em': now_str(),
        }

    def pick(*keys, default=''):
        for key in keys:
            if key in item and item.get(key) not in [None, '']:
                return item.get(key)
        return default

    padroes = pick('padroes', 'standards', 'schemas', default=[])
    if isinstance(padroes, str):
        padroes = [p.strip() for p in padroes.split(',') if p.strip()]
    elif not isinstance(padroes, list):
        padroes = [str(padroes)] if padroes else []

    campos = pick('campos', 'fields', 'field_names', default=[])
    if isinstance(campos, str):
        campos = [c.strip() for c in campos.split(',') if c.strip()]
    elif not isinstance(campos, list):
        campos = [str(campos)] if campos else []

    nome = pick('nome', 'name', 'title', 'source', 'fonte', 'fonte_externa', default=f'Fonte {idx}')
    url = pick('url', 'site', 'homepage', 'portal_url', default='')
    endpoint = pick('endpoint', 'api', 'api_url', 'endpoint_url', 'base_url', default=url)
    tipo = pick('tipo', 'type', 'categoria', 'category', default='fonte externa')
    licenca = pick('licenca', 'license', default='não informada')
    autenticacao = pick('autenticacao', 'authentication', 'auth', 'auth_type', default='não informada')
    descricao = pick('descricao', 'description', 'summary', default='')
    status = _normalize_status_value(pick('status', 'state', 'situacao', 'ativo', default='ativo'))

    return {
        'id': int(pick('id', default=idx)) if str(pick('id', default=idx)).isdigit() else idx,
        'nome': str(nome),
        'url': str(url or ''),
        'endpoint': str(endpoint or ''),
        'tipo': str(tipo or 'fonte externa'),
        'licenca': str(licenca or 'não informada'),
        'autenticacao': str(autenticacao or 'não informada'),
        'padroes': padroes,
        'descricao': str(descricao or ''),
        'campos': campos,
        'status': status,
        'criado_em': str(pick('criado_em', 'created_at', default=now_str())),
    }


def normalize_open_data_sources(data):
    if isinstance(data, dict):
        for key in ('sources', 'fontes', 'items', 'results', 'data'):
            if isinstance(data.get(key), list):
                data = data.get(key)
                break
        else:
            data = [data]
    if not isinstance(data, list):
        data = default_open_data_sources()
    normalized = [normalize_open_data_source_entry(item, idx=i + 1) for i, item in enumerate(data)]
    return normalized or default_open_data_sources()


def safe_dataframe_view(df, columns):
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return pd.DataFrame(columns=columns)
    out = df.copy()
    for col in columns:
        if col not in out.columns:
            out[col] = '—'
    return out[columns]


def load_open_data_sources():
    ensure_support_files()
    data = load_json_file(OPEN_DATA_FILE, default_open_data_sources())
    normalized = normalize_open_data_sources(data)
    return normalized

def save_open_data_sources(sources):
    return save_json_file(OPEN_DATA_FILE, sources)

def load_interoperability_registry():
    ensure_support_files()
    data = load_json_file(INTEROP_FILE, default_interoperability_registry())
    return data if isinstance(data, list) else default_interoperability_registry()

def save_interoperability_registry(mappings):
    return save_json_file(INTEROP_FILE, mappings)


def all_events():
    ensure_support_files()
    ev = load_json_file(EVENTS_FILE, [])
    return normalize_events_dataframe(pd.DataFrame(ev)) if ev else pd.DataFrame()

def get_last_event_hash():
    events = load_json_file(EVENTS_FILE, [])
    return events[-1]["event_hash"] if events else "GENESIS"

def get_previous_entity_event(events, entity_type, entity_id):
    for event in reversed(events):
        if event.get('entity_type') == entity_type and str(event.get('entity_id')) == str(entity_id):
            return event
    return None

def get_entity_event_count(events, entity_type, entity_id):
    return sum(1 for event in events if event.get('entity_type') == entity_type and str(event.get('entity_id')) == str(entity_id))

def register_event(event_type, actor, actor_role, entity_type, entity_id, payload, origin="sistema", automatic=False, status="bruto", previous_state=None, circulation_action=None, interoperability_refs=None, semantic_snapshot=None, provenance_source=None):
    ensure_support_files()
    events = load_json_file(EVENTS_FILE, [])
    previous_entity_event = get_previous_entity_event(events, entity_type, entity_id)
    entity_version = get_entity_event_count(events, entity_type, entity_id) + 1
    circulation_trace = None
    if circulation_action:
        circulation_trace = {
            "acao": circulation_action,
            "registrado_em": now_str(),
            "responsavel": actor or "sistema",
            "destino": origin,
        }
    record = {
        "id": len(events) + 1,
        "ledger_no": len(events) + 1,
        "timestamp": now_str(),
        "event_type": event_type,
        "actor": actor or "sistema",
        "actor_role": actor_role or "system",
        "entity_type": entity_type,
        "entity_id": entity_id,
        "entity_version": entity_version,
        "origin": origin,
        "automatic": bool(automatic),
        "status": status,
        "payload": payload,
        "previous_state": previous_state,
        "previous_hash": get_last_event_hash(),
        "entity_previous_hash": previous_entity_event.get('event_hash') if previous_entity_event else 'GENESIS_ENTITY',
        "semantic_archive_ref": f"{entity_type}:{entity_id}:v{entity_version}",
        "provenance_source": provenance_source or origin,
        "interoperability_refs": interoperability_refs or [],
        "semantic_snapshot": semantic_snapshot or {},
        "circulation_action": circulation_action,
        "circulation_trace": circulation_trace,
    }
    record["event_hash"] = hash_record(record)
    events.append(record)
    save_json_file(EVENTS_FILE, events)
    return record

def ontology_terms_map(ontologies=None):
    ontologies = ontologies or load_ontologies()
    mapping = {}
    for ont in ontologies:
        for term in ont.get("termos", []):
            mapping[normalize_text(term)] = ont.get("nome", "Ontologia")
    return mapping

def match_ontologies_for_tag(tag, ontologies=None):
    ontologies = ontologies or load_ontologies()
    nt = normalize_text(tag)
    matches = []
    for ont in ontologies:
        for term in ont.get("termos", []):
            nterm = normalize_text(term)
            if nt == nterm or (nterm and (nterm in nt or nt in nterm)):
                matches.append(ont.get("nome", "Ontologia"))
                break
    return sorted(set(matches))

def classify_tag_group(tag):
    nt = normalize_text(tag)
    for group, terms in THEME_GROUPS.items():
        for term in terms:
            nterm = normalize_text(term)
            if nt == nterm or (nterm and (nterm in nt or nt in nterm)):
                return group
    return "Outros"

def levenshtein(a, b):
    a = normalize_text(a)
    b = normalize_text(b)
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        curr = [i]
        for j, cb in enumerate(b, 1):
            cost = 0 if ca == cb else 1
            curr.append(min(curr[-1] + 1, prev[j] + 1, prev[j-1] + cost))
        prev = curr
    return prev[-1]

def build_spell_suggestions(tags_df, ontologies=None):
    if tags_df.empty:
        return pd.DataFrame()
    ontologies = ontologies or load_ontologies()
    tag_counts = tags_df['tag'].value_counts().to_dict()
    vocab = list(tag_counts.keys())
    ontology_terms = []
    for ont in ontologies:
        ontology_terms.extend(ont.get('termos', []))
    reference_terms = sorted(set(vocab + ontology_terms))
    rows = []
    for tag, freq in tag_counts.items():
        normalized_reference = [t for t in reference_terms if normalize_text(t) != normalize_text(tag)]
        close = get_close_matches(tag, normalized_reference, n=3, cutoff=0.78)
        candidate = close[0] if close else None
        if candidate:
            dist = levenshtein(tag, candidate)
            if dist <= 2 or normalize_text(candidate) in normalize_text(tag) or normalize_text(tag) in normalize_text(candidate):
                rows.append({
                    "tag": tag,
                    "frequencia": freq,
                    "sugestao": candidate,
                    "distancia": dist,
                    "grupo_tematico": classify_tag_group(tag),
                    "ontologias": ", ".join(match_ontologies_for_tag(tag, ontologies)) or "—"
                })
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows).sort_values(["distancia", "frequencia"], ascending=[True, False]).drop_duplicates(subset=["tag"])
    return df

def analyze_theme_groups(tags_df):
    if tags_df.empty:
        return pd.DataFrame(columns=["Grupo","Qtd Tags","Tags Únicas"])
    tmp = tags_df.copy()
    tmp['grupo_tematico'] = tmp['tag'].apply(classify_tag_group)
    res = tmp.groupby('grupo_tematico').agg(Qtd_Tags=('tag','count'), Tags_Unicas=('tag','nunique')).reset_index()
    res.columns = ['Grupo','Qtd Tags','Tags Únicas']
    return res.sort_values('Qtd Tags', ascending=False)

def analyze_ontology_usage(tags_df, ontologies=None):
    if tags_df.empty:
        return pd.DataFrame(columns=["Ontologia","Ocorrências","Tags Correspondentes"])
    ontologies = ontologies or load_ontologies()
    rows = []
    for ont in ontologies:
        terms = [normalize_text(t) for t in ont.get('termos', [])]
        matched = []
        for tag in tags_df['tag'].tolist():
            nt = normalize_text(tag)
            if any(t == nt or (t and (t in nt or nt in t)) for t in terms):
                matched.append(tag)
        rows.append({
            "Ontologia": ont.get('nome', 'Ontologia'),
            "Categoria": ont.get('categoria', '—'),
            "Ocorrências": len(matched),
            "Tags Correspondentes": ", ".join(pd.Series(matched).value_counts().head(8).index.tolist()) if matched else "—"
        })
    return pd.DataFrame(rows).sort_values('Ocorrências', ascending=False)

def update_tag_record(tag_id, new_tag=None, new_status=None, admin_user="admin"):
    tags = load_json_file(TAGS_FILE, [])
    for idx, tag in enumerate(tags):
        if tag.get('id') == tag_id:
            previous = dict(tag)
            if new_tag is not None and str(new_tag).strip():
                tag['tag'] = str(new_tag).strip().lower()
                tag['grupo_tematico'] = classify_tag_group(tag['tag'])
                tag['ontologias'] = match_ontologies_for_tag(tag['tag'])
            if new_status is not None and str(new_status).strip():
                tag['status'] = new_status
            tag['ultima_revisao'] = now_str()
            tags[idx] = tag
            save_json_file(TAGS_FILE, tags)
            register_event(
                event_type="human_tag_revision",
                actor=admin_user,
                actor_role="admin",
                entity_type="tag",
                entity_id=tag_id,
                payload=tag,
                origin="revisao_humana",
                automatic=False,
                status=tag.get('status', 'revisado'),
                previous_state=previous,
            )
            st.cache_data.clear()
            return True
    return False

def build_artwork_narration(obra):
    titulo = str(obra.get('titulo', 'obra sem título')).strip()
    artista = str(obra.get('artista', 'autor não identificado')).strip()
    ano = str(obra.get('ano', 'data não informada')).strip()
    descricao = build_audio_description(obra)
    return f"Você está ouvindo a audiodescrição da obra {titulo}, de {artista}, do ano de {ano}. {descricao}"

def render_speech_button(text, label="Ouvir audiodescrição"):
    safe = json.dumps(str(text or ""), ensure_ascii=False)
    safe_label = json.dumps(str(label), ensure_ascii=False)
    uid = hashlib.sha1((str(text) + str(label)).encode('utf-8')).hexdigest()[:10]
    components.html(
        f"""
        <div class='audio-widget' style='margin:8px 0 10px 0'>
          <style>
            .audio-widget *{{font-family:'Times New Roman', Times, serif;}}
            .audio-btn-{uid}{{
              position:relative; display:inline-flex; align-items:center; gap:12px; cursor:pointer;
              border:1px solid rgba(255,255,255,.35); border-radius:999px; padding:14px 24px;
              background:linear-gradient(135deg, rgba(255,255,255,.16), rgba(167,230,255,.18));
              color:white; font-size:18px; font-weight:700; overflow:hidden; transition:transform .2s ease, box-shadow .2s ease;
              box-shadow:0 8px 28px rgba(0,0,0,.22);
            }}
            .audio-btn-{uid}:hover{{transform:translateY(-2px) scale(1.02); box-shadow:0 12px 34px rgba(0,0,0,.28);}}
            .audio-btn-{uid}.playing{{background:linear-gradient(135deg, rgba(105,195,255,.34), rgba(133,255,211,.22));}}
            .audio-pulse-{uid}{{width:14px;height:14px;border-radius:50%;background:#9be7ff;box-shadow:0 0 0 rgba(155,231,255,.65);animation:pulse-{uid} 1.4s infinite;}}
            .audio-btn-{uid}.playing .audio-pulse-{uid}{{background:#8cffbe;}}
            @keyframes pulse-{uid}{{0%{{box-shadow:0 0 0 0 rgba(155,231,255,.65)}}70%{{box-shadow:0 0 0 14px rgba(155,231,255,0)}}100%{{box-shadow:0 0 0 0 rgba(155,231,255,0)}}}}
            .audio-sub-{uid}{{display:block; margin-top:7px; color:rgba(255,255,255,.72); font-size:13px;}}
          </style>
          <button id='audio-btn-{uid}' class='audio-btn-{uid}'>
            <span class='audio-pulse-{uid}'></span>
            <span id='audio-btn-label-{uid}'>{label}</span>
          </button>
          <div class='audio-sub-{uid}'>Clique uma vez para ouvir e novamente para parar.</div>
          <script>
            const text = {safe};
            const baseLabel = {safe_label};
            const btn = document.getElementById('audio-btn-{uid}');
            const labelEl = document.getElementById('audio-btn-label-{uid}');
            let utterance = null;
            let playing = false;
            function syncLabel(){{
              labelEl.textContent = playing ? 'Parar audiodescrição' : baseLabel;
              if (playing) btn.classList.add('playing');
              else btn.classList.remove('playing');
            }}
            function stopSpeech(){{
              window.speechSynthesis.cancel();
              playing = false;
              syncLabel();
            }}
            btn.addEventListener('click', function(){{
              if (playing){{ stopSpeech(); return; }}
              window.speechSynthesis.cancel();
              utterance = new SpeechSynthesisUtterance(text);
              utterance.lang = 'pt-BR';
              utterance.rate = 0.92;
              utterance.pitch = 1.0;
              utterance.onend = function(){{ playing = false; syncLabel(); }};
              utterance.onerror = function(){{ playing = false; syncLabel(); }};
              playing = true;
              syncLabel();
              window.speechSynthesis.speak(utterance);
            }});
            window.addEventListener('beforeunload', stopSpeech);
            syncLabel();
          </script>
        </div>
        """,
        height=105,
    )

def get_accessibility_settings():
    if 'acc_font_size' not in st.session_state:
        st.session_state['acc_font_size'] = 18
    if 'acc_theme' not in st.session_state:
        st.session_state['acc_theme'] = 'Escuro'
    if 'acc_focus_audio' not in st.session_state:
        st.session_state['acc_focus_audio'] = True
    return {
        'font_size': st.session_state['acc_font_size'],
        'theme': st.session_state['acc_theme'],
        'focus_audio': st.session_state['acc_focus_audio']
    }

def apply_accessibility_settings():
    settings = get_accessibility_settings()
    theme = settings['theme']
    font_size = int(settings['font_size'])
    if theme == 'Claro':
        gradient = 'linear-gradient(-45deg,#f7f1e8 0%,#dfe9f3 25%,#f5ede3 50%,#dde7f1 75%,#f7f1e8 100%)'
        fg = '#1a1a1a'
        card = 'rgba(255,255,255,.82)'
        border = 'rgba(0,0,0,.14)'
        accent = '#173b66'
    elif theme == 'Alto Contraste':
        gradient = 'linear-gradient(-45deg,#000000 0%,#111111 25%,#000000 50%,#171717 75%,#000000 100%)'
        fg = '#ffe600'
        card = 'rgba(10,10,10,.92)'
        border = 'rgba(255,230,0,.32)'
        accent = '#ffe600'
    else:
        gradient = 'linear-gradient(-45deg,#000 0%,#001F3F 25%,#000 50%,#001F3F 75%,#000 100%)'
        fg = '#ffffff'
        card = 'rgba(255,255,255,.15)'
        border = 'rgba(255,255,255,.26)'
        accent = '#a7e6ff'
    st.markdown(f"""
    <style>
    *{{font-family:'Times New Roman', Times, serif !important;}}
    .stApp{{
        color:{fg} !important;
        background:{gradient} !important;
        background-size:400% 400% !important;
        animation:bg 15s ease infinite !important;
    }}
    .glass-card,.obra-card,.kpi-card,.sc,.insight,.cluster-wrap{{
        background:{card} !important;
        border-color:{border} !important;
    }}
    .stMarkdown p,
    .stMarkdown li,
    .stCaption,
    .stText,
    .stAlert,
    label,
    .stButton button,
    .stDownloadButton button,
    .stTextInput input,
    .stTextArea textarea,
    .stSelectbox div,
    .stMultiSelect div,
    .stDataFrame,
    .stExpander details summary,
    .audio-block,
    .audio-block *{{
        font-size:{font_size}px !important;
        line-height:1.6 !important;
        word-break:normal !important;
        overflow-wrap:break-word !important;
    }}
    h1{{font-size:{max(28, font_size + 18)}px !important; line-height:1.2 !important;}}
    h2{{font-size:{max(24, font_size + 10)}px !important; line-height:1.25 !important;}}
    h3{{font-size:{max(20, font_size + 6)}px !important; line-height:1.3 !important;}}
    .audio-card{{
        background:{card};
        border:1px solid {border};
        border-radius:22px;
        padding:1.35rem 1.5rem;
        margin-top:1rem;
        box-shadow:0 8px 28px rgba(0,0,0,.18);
    }}
    .audio-label{{
        display:inline-block;
        margin-bottom:.75rem;
        padding:.35rem .8rem;
        border-radius:999px;
        border:1px solid {border};
        background:rgba(255,255,255,.08);
        color:{accent};
        font-weight:700;
    }}
    .audio-title{{font-weight:700; margin-bottom:.45rem; color:{fg};}}
    .audio-meta{{opacity:.88; margin-bottom:.65rem; color:{fg};}}
    .streamlit-expanderHeader{{line-height:1.35 !important;}}
    </style>
    """, unsafe_allow_html=True)

def build_audio_description(obra):
    titulo = str(obra.get('titulo', 'obra')).strip()
    artista = str(obra.get('artista', 'autor não identificado')).strip()
    ano = str(obra.get('ano', 'data não informada')).strip()
    titulo_norm = normalize_text(titulo)
    manual = str(obra.get('audio_descricao', '') or '').strip()

    if 'guernica' in titulo_norm:
        return (
            'Trata-se de uma pintura monumental de caráter histórico, associada à guerra e ao bombardeio da cidade de Guernica. '
            'A imagem se organiza em um grande campo horizontal em preto, branco e cinza. As figuras são cubistas e fragmentadas, '
            'compostas por planos angulosos, rostos quebrados, bocas abertas e membros distorcidos. À esquerda aparece um touro escuro. '
            'Abaixo dele, uma mãe ergue o rosto para o alto enquanto segura o filho morto, num gesto de lamento. No centro, um cavalo ferido ocupa a composição '
            'com a boca aberta, como se gritasse. Acima, uma luz forte lembra ao mesmo tempo uma lâmpada e uma explosão. Ao redor, partes de corpos, mãos, pernas, armas quebradas '
            'e estruturas em ruína sugerem violência, desorientação e destruição.'
        )
    if 'noite estrelada' in titulo_norm or 'starry night' in titulo_norm:
        return (
            'A cena apresenta uma paisagem noturna com forte sensação de movimento. Na parte inferior, vê-se uma vila pequena e silenciosa. '
            'As casas aparecem reduzidas, com telhados inclinados e uma igreja de torre aguda subindo ao centro. Acima da vila, o céu domina quase toda a obra. '
            'Faixas curvas e espirais luminosas cruzam o azul profundo, como se o vento estivesse visível. As estrelas são círculos amarelos intensos com halos vibrantes. '
            'À esquerda, um cipreste escuro sobe verticalmente, alto e ondulante, funcionando como contraste entre a terra e o céu. A composição transmite noite, ritmo, turbulência e contemplação.'
        )
    if 'mona lisa' in titulo_norm:
        return (
            'A obra mostra uma mulher sentada de frente, com o corpo levemente voltado e as mãos cruzadas em primeiro plano. '
            'Ela veste roupas escuras e aparece diante de uma paisagem distante com rios, caminhos e montanhas. O rosto tem expressão serena e ambígua. '
            'A luz é suave, o contorno é delicado e a transição entre sombra e pele acontece de modo gradual, criando profundidade e quietude.'
        )
    if manual:
        return manual
    return (
        f'Trata-se da obra {titulo}, de {artista}, datada de {ano}. '
        'A descrição sonora observa composição, cores dominantes, direção das formas, personagens, objetos, luz, profundidade, clima visual e eixo temático da imagem.'
    )


def render_audio_description_block(obra):
    titulo = obra.get('titulo', '—')
    artista = obra.get('artista', '—')
    ano = obra.get('ano', '—')
    tipo = 'Pintura'
    contexto = 'Leitura descritiva da composição visual'
    if 'guernica' in normalize_text(titulo):
        tipo = 'Pintura histórica / mural moderno'
        contexto = 'Guerra, fragmentação, luto coletivo e linguagem cubista'
    elif 'noite estrelada' in normalize_text(titulo):
        contexto = 'Paisagem noturna, movimento do céu, ritmo visual e contemplação'
    narracao = build_artwork_narration(obra)
    st.markdown(
        f"""
        <div class='audio-card audio-block'>
            <div class='audio-label'>Acessibilidade e audiodescrição</div>
            <div class='audio-title'>Título: {titulo}</div>
            <div class='audio-meta'><strong>Artista:</strong> {artista} &nbsp;•&nbsp; <strong>Ano:</strong> {ano} &nbsp;•&nbsp; <strong>Tipo:</strong> {tipo}</div>
            <div class='audio-meta'><strong>Eixo temático:</strong> {contexto}</div>
        </div>
        """,
        unsafe_allow_html=True
    )
    render_speech_button(narracao, label='Ouvir audiodescrição da obra')

def render_accessibility_panel():
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.markdown("### Acessibilidade", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,1,1])
    with c1:
        st.session_state['acc_theme'] = st.selectbox("Modo visual", ["Escuro","Claro","Alto Contraste"], index=["Escuro","Claro","Alto Contraste"].index(st.session_state.get('acc_theme', 'Escuro')), key='acc_theme_sel')
    with c2:
        st.session_state['acc_font_size'] = st.slider("Tamanho da tipografia", 14, 28, int(st.session_state.get('acc_font_size', 18)), 1, key='acc_font_size_slider')
    with c3:
        st.session_state['acc_focus_audio'] = st.checkbox("Foco em audiodescrição", value=st.session_state.get('acc_focus_audio', True), key='acc_audio_focus')
    st.caption("Animação de fundo preservada, tipografia em Times New Roman, contraste ajustável e audiodescrição com botão animado e controle de parada.")
    st.markdown("</div>", unsafe_allow_html=True)
    apply_accessibility_settings()

def build_graph_svg(nodes, edges, width=920, height=520):
    if not nodes:
        return "<div class='insight'>Sem dados suficientes para gerar o grafo.</div>"
    cx, cy = width/2, height/2
    radius = min(width, height) * 0.34
    parts = [f"<svg viewBox='0 0 {width} {height}' width='100%' height='{height}' xmlns='http://www.w3.org/2000/svg'>"]
    pos = {}
    for i, node in enumerate(nodes):
        angle = (2 * math.pi * i / max(len(nodes), 1)) - math.pi/2
        x = cx + radius * math.cos(angle)
        y = cy + radius * math.sin(angle)
        pos[node['id']] = (x, y)
    for edge in edges:
        a, b, w = edge
        if a in pos and b in pos:
            x1, y1 = pos[a]
            x2, y2 = pos[b]
            parts.append(f"<line x1='{x1:.1f}' y1='{y1:.1f}' x2='{x2:.1f}' y2='{y2:.1f}' stroke='rgba(255,255,255,.35)' stroke-width='{1 + (w*4):.1f}' />")
    for node in nodes:
        x, y = pos[node['id']]
        size = node.get('size', 18)
        color = node.get('color', '#a7e6ff')
        label = node.get('label', node['id'])
        parts.append(f"<circle cx='{x:.1f}' cy='{y:.1f}' r='{size:.1f}' fill='{color}' fill-opacity='0.78' stroke='white' stroke-opacity='0.5' stroke-width='1.5'/>")
        parts.append(f"<text x='{x:.1f}' y='{y + size + 18:.1f}' text-anchor='middle' fill='white' font-size='16' font-family='Times New Roman'>{label}</text>")
    parts.append('</svg>')
    return ''.join(parts)

def build_graph_data(tags_df, threshold=0.35):
    if tags_df.empty:
        return [], []
    counts = tags_df['tag'].value_counts().head(10)
    top_tags = counts.index.tolist()
    conns = tag_connections(top_tags, threshold=threshold)
    nodes = []
    for tag, freq in counts.items():
        nodes.append({
            'id': tag,
            'label': tag[:16],
            'size': 14 + min(freq, 10) * 1.6,
            'color': {'Religioso':'#a78bfa','Guerra':'#f87171','Cor':'#60a5fa','Natureza':'#34d399','Afeto':'#f9a8d4','Outros':'#fcd34d'}.get(classify_tag_group(tag), '#a7e6ff')
        })
    edges = [(c['tag_a'], c['tag_b'], c['similaridade']) for c in conns if c['tag_a'] in top_tags and c['tag_b'] in top_tags]
    return nodes, edges


def build_interoperability_graph_data(tags_df, open_sources=None, mappings=None, threshold=0.35):
    nodes, edges = build_graph_data(tags_df, threshold=threshold)
    node_ids = {n['id'] for n in nodes}
    open_sources = open_sources or load_open_data_sources()
    mappings = mappings or load_interoperability_registry()

    for source in open_sources:
        sid = f"source::{source.get('nome','Fonte')}"
        if sid not in node_ids:
            nodes.append({
                'id': sid,
                'label': str(source.get('nome','Fonte'))[:18],
                'size': 16,
                'color': '#8cf0ff',
                'node_type': 'external_source',
            })
            node_ids.add(sid)

    for mapping in mappings:
        did = f"domain::{mapping.get('dominio_local','dominio')}"
        sid = f"source::{mapping.get('fonte_externa','fonte')}"
        if did not in node_ids:
            nodes.append({
                'id': did,
                'label': str(mapping.get('dominio_local','dominio')).title()[:18],
                'size': 15,
                'color': '#ffd166',
                'node_type': 'local_domain',
            })
            node_ids.add(did)
        if sid not in node_ids:
            nodes.append({
                'id': sid,
                'label': str(mapping.get('fonte_externa','fonte'))[:18],
                'size': 16,
                'color': '#8cf0ff',
                'node_type': 'external_source',
            })
            node_ids.add(sid)
        edges.append((did, sid, 0.95))

    return nodes, edges

def build_graph_3d_component(nodes, edges, height=620):
    if not nodes:
        st.info('Sem dados suficientes para o grafo 3D.')
        return
    node_payload = []
    total = max(len(nodes), 1)
    for i, node in enumerate(nodes):
        angle = 2 * math.pi * i / total
        radius = 180 + (i % 3) * 34
        x = math.cos(angle) * radius
        y = math.sin(angle * 1.7) * 95
        z = math.sin(angle) * radius
        node_payload.append({
            'id': node['id'],
            'label': node.get('label', node['id']),
            'size': float(node.get('size', 18)),
            'color': node.get('color', '#a7e6ff'),
            'x': x,
            'y': y,
            'z': z,
        })
    edge_payload = [{'source': a, 'target': b, 'weight': float(w)} for a, b, w in edges]
    html = f"""
    <div style='background:rgba(255,255,255,.07); border:1px solid rgba(255,255,255,.16); border-radius:22px; overflow:hidden;'>
      <canvas id='g3d' width='1080' height='{height}' style='width:100%; height:{height}px; display:block;'></canvas>
      <div style='padding:10px 16px; color:white; font-family:Times New Roman, serif; font-size:15px;'>Arraste para rotacionar o grafo 3D. Nós azuis representam fontes externas; dourados, domínios locais; demais, tags e relações semânticas.</div>
    </div>
    <script>
      const nodes = {json.dumps(node_payload, ensure_ascii=False)};
      const edges = {json.dumps(edge_payload, ensure_ascii=False)};
      const canvas = document.getElementById('g3d');
      const ctx = canvas.getContext('2d');
      let rotY = 0.004, rotX = -0.002;
      let drag = false, lx = 0, ly = 0;
      const perspective = 680;
      function project(node) {{
        let x = node.x, y = node.y, z = node.z;
        const cosY = Math.cos(rotY), sinY = Math.sin(rotY);
        let x1 = x * cosY - z * sinY;
        let z1 = x * sinY + z * cosY;
        const cosX = Math.cos(rotX), sinX = Math.sin(rotX);
        let y1 = y * cosX - z1 * sinX;
        let z2 = y * sinX + z1 * cosX;
        const scale = perspective / (perspective + z2 + 320);
        return {{
          x: canvas.width / 2 + x1 * scale,
          y: canvas.height / 2 + y1 * scale,
          scale,
          depth: z2,
          size: node.size * scale,
          color: node.color,
          label: node.label,
          id: node.id,
        }};
      }}
      function frame() {{
        ctx.clearRect(0,0,canvas.width,canvas.height);
        if (!drag) {{ rotY += 0.003; rotX += 0.0012; }}
        const projected = Object.fromEntries(nodes.map(n => [n.id, project(n)]));
        edges.forEach(edge => {{
          const a = projected[edge.source], b = projected[edge.target];
          if (!a || !b) return;
          const alpha = Math.max(.15, Math.min(.7, (a.scale + b.scale) / 2));
          ctx.beginPath();
          ctx.strokeStyle = `rgba(180,220,255,${{alpha}})`;
          ctx.lineWidth = 1 + edge.weight * 2.4;
          ctx.moveTo(a.x, a.y);
          ctx.lineTo(b.x, b.y);
          ctx.stroke();
        }});
        Object.values(projected)
          .sort((a,b) => a.depth - b.depth)
          .forEach(node => {{
            ctx.beginPath();
            ctx.fillStyle = node.color;
            ctx.globalAlpha = .88;
            ctx.arc(node.x, node.y, Math.max(4, node.size), 0, Math.PI * 2);
            ctx.fill();
            ctx.globalAlpha = 1;
            ctx.strokeStyle = 'rgba(255,255,255,.55)';
            ctx.lineWidth = 1;
            ctx.stroke();
            ctx.fillStyle = 'rgba(255,255,255,.95)';
            ctx.font = `${{Math.max(12, 12 * node.scale + 8)}}px Times New Roman`;
            ctx.fillText(node.label, node.x + Math.max(8, node.size + 4), node.y + 4);
          }});
        requestAnimationFrame(frame);
      }}
      canvas.addEventListener('mousedown', e => {{ drag = true; lx = e.offsetX; ly = e.offsetY; }});
      canvas.addEventListener('mouseup', () => drag = false);
      canvas.addEventListener('mouseleave', () => drag = false);
      canvas.addEventListener('mousemove', e => {{
        if (!drag) return;
        const dx = e.offsetX - lx, dy = e.offsetY - ly;
        rotY += dx * 0.005;
        rotX += dy * 0.005;
        lx = e.offsetX; ly = e.offsetY;
      }});
      frame();
    </script>
    """
    components.html(html, height=height + 58)

def summarize_interoperability(open_sources=None, mappings=None):
    open_sources = normalize_open_data_sources(open_sources or load_open_data_sources())
    mappings = mappings or load_interoperability_registry()
    rows = []
    for mapping in mappings:
        if not isinstance(mapping, dict):
            continue
        rows.append({
            'Domínio local': mapping.get('dominio_local', mapping.get('domain', '—')),
            'Fonte externa': mapping.get('fonte_externa', mapping.get('source_name', '—')),
            'Padrão': mapping.get('padrao', mapping.get('mapping_standard', '—')),
            'Status': mapping.get('status', '—'),
            'Campos mapeados': ' | '.join(mapping.get('campos_mapeados', [])) if isinstance(mapping.get('campos_mapeados'), list) else str(mapping.get('campos_mapeados', mapping.get('campo_local', '—'))),
        })
    return pd.DataFrame(rows)

def get_secret(name, default=""):
    try:
        if hasattr(st, 'secrets') and name in st.secrets:
            return str(st.secrets[name])
    except Exception:
        pass
    return str(os.getenv(name, default or "") or default or "")


def http_get_json(url, headers=None, timeout=12):
    headers = headers or {}
    req = Request(url, headers={**{"User-Agent": "Mozilla/5.0 FolksonomiaDigital/1.0", "Accept": "application/json"}, **headers})
    try:
        with urlopen(req, timeout=timeout) as resp:
            charset = resp.headers.get_content_charset('utf-8') if hasattr(resp.headers, 'get_content_charset') else 'utf-8'
            raw = resp.read().decode(charset or 'utf-8', errors='replace')
            return json.loads(raw), None
    except HTTPError as e:
        try:
            body = e.read().decode('utf-8', errors='replace')
        except Exception:
            body = ''
        return None, f"HTTP {e.code}: {body[:160]}" if body else f"HTTP {e.code}"
    except URLError as e:
        return None, f"URL error: {e.reason}"
    except Exception as e:
        return None, str(e)


def jaccard_similarity(a, b):
    sa = set(normalize_text(a).split())
    sb = set(normalize_text(b).split())
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / max(1, len(sa | sb))


def score_external_match(local_value, label, description=""):
    base = sim(local_value, label)
    secondary = jaccard_similarity(local_value, label)
    descr_bonus = 0.10 if description and any(tok in normalize_text(description) for tok in normalize_text(local_value).split()[:3]) else 0.0
    return round(min(0.99, max(base, secondary) + descr_bonus), 3)


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_wikidata_matches(term, limit=4):
    params = {
        'action': 'wbsearchentities',
        'search': term,
        'language': 'pt',
        'uselang': 'pt',
        'format': 'json',
        'limit': int(limit),
    }
    url = 'https://www.wikidata.org/w/api.php?' + urlencode(params, quote_via=quote_plus)
    data, err = http_get_json(url)
    rows = []
    if err or not isinstance(data, dict):
        return rows, err
    for item in data.get('search', [])[:limit]:
        label = item.get('label') or item.get('display', {}).get('label', {}).get('value', '')
        desc = item.get('description') or item.get('display', {}).get('description', {}).get('value', '')
        rows.append({
            'fonte_externa': 'Wikidata',
            'identificador_externo': item.get('id', ''),
            'rotulo_externo': label,
            'descricao_externa': desc,
            'url_externa': item.get('concepturi', f"https://www.wikidata.org/wiki/{item.get('id','')}") if item.get('id') else item.get('concepturi', ''),
            'confianca': score_external_match(term, label, desc),
            'metodo_busca': 'wbsearchentities',
        })
    return rows, None


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_europeana_matches(term, limit=4):
    api_key = get_secret('EUROPEANA_API_KEY', '')
    if not api_key:
        return [], 'Europeana requer API key em EUROPEANA_API_KEY.'
    params = {
        'wskey': api_key,
        'query': term,
        'rows': int(limit),
        'profile': 'standard',
    }
    url = 'https://api.europeana.eu/record/v2/search.json?' + urlencode(params, quote_via=quote_plus)
    data, err = http_get_json(url)
    rows = []
    if err or not isinstance(data, dict):
        return rows, err
    for item in data.get('items', [])[:limit]:
        title = ''
        raw_title = item.get('title')
        if isinstance(raw_title, list) and raw_title:
            title = str(raw_title[0])
        elif isinstance(raw_title, str):
            title = raw_title
        creator = item.get('dcCreator') or item.get('edmAgentLabel') or []
        if isinstance(creator, list):
            creator = ', '.join([str(x) for x in creator[:3]])
        desc = creator or str(item.get('type', ''))
        rows.append({
            'fonte_externa': 'Europeana',
            'identificador_externo': item.get('id', ''),
            'rotulo_externo': title,
            'descricao_externa': desc,
            'url_externa': ('https://www.europeana.eu/item/' + str(item.get('id')).strip('/')) if item.get('id') else '',
            'confianca': score_external_match(term, title or desc, desc),
            'metodo_busca': 'Search API',
        })
    return rows, None


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_dadosgov_matches(term, limit=4):
    token = get_secret('DADOS_GOV_BR_TOKEN', '')
    headers = {'Authorization': f'Bearer {token}'} if token else {}
    candidates = [
        'https://dados.gov.br/api/3/action/package_search?' + urlencode({'q': term, 'rows': int(limit)}, quote_via=quote_plus),
        'https://dados.gov.br/api/publico/conjuntos-dados/buscar?' + urlencode({'q': term, 'pagina': 1, 'quantidade': int(limit)}, quote_via=quote_plus),
    ]
    last_err = 'IBRAM dados abertos não retornou resultados.'
    for url in candidates:
        data, err = http_get_json(url, headers=headers)
        if isinstance(data, dict):
            rows = []
            result = data.get('result') if isinstance(data.get('result'), dict) else data
            items = result.get('results') or result.get('datasets') or data.get('results') or []
            for item in items[:limit]:
                title = item.get('title') or item.get('name') or item.get('titulo') or ''
                notes = item.get('notes') or item.get('descricao') or ''
                org = item.get('organization', {}) if isinstance(item.get('organization'), dict) else {}
                org_name = org.get('title') or org.get('name') or ''
                dataset_url = item.get('url') or item.get('link') or ''
                if not dataset_url and item.get('name'):
                    dataset_url = f"https://dados.gov.br/dados/conjuntos-dados/{item.get('name')}"
                rows.append({
                    'fonte_externa': 'IBRAM dados abertos',
                    'identificador_externo': item.get('id') or item.get('name') or title,
                    'rotulo_externo': title,
                    'descricao_externa': f"{org_name} {notes}".strip(),
                    'url_externa': dataset_url,
                    'confianca': score_external_match(term, title or notes, notes),
                    'metodo_busca': 'Portal de Dados Abertos API',
                })
            if rows:
                return rows, None
        last_err = err or last_err
    if not token:
        last_err = 'Portal de Dados Abertos pode exigir token em DADOS_GOV_BR_TOKEN para busca programática.'
    return [], last_err


def build_local_interop_queries(tags_df, obras, meta, limit=12):
    queries = []
    seen = set()
    if tags_df is not None and not tags_df.empty and 'tag' in tags_df.columns:
        for tag, freq in tags_df['tag'].value_counts().head(8).items():
            item = {'dominio_local': 'tag', 'campo_local': 'tag', 'valor_local': str(tag), 'frequencia_local': int(freq)}
            key = (item['dominio_local'], normalize_text(item['valor_local']))
            if key not in seen:
                seen.add(key)
                queries.append(item)
    for obra in (obras or [])[:5]:
        for campo in ['titulo', 'artista']:
            valor = str(obra.get(campo, '')).strip()
            if valor:
                item = {'dominio_local': 'obra', 'campo_local': campo, 'valor_local': valor, 'obra_id': obra.get('id')}
                key = (item['dominio_local'] + ':' + campo, normalize_text(valor))
                if key not in seen:
                    seen.add(key)
                    queries.append(item)
    for campo in ['instituicao', 'colecao', 'descricao']:
        valor = str((meta or {}).get(campo, '')).strip()
        if valor:
            snippet = valor if len(valor) <= 90 else valor[:90]
            item = {'dominio_local': 'metadado_institucional', 'campo_local': campo, 'valor_local': snippet}
            key = (item['dominio_local'] + ':' + campo, normalize_text(snippet))
            if key not in seen:
                seen.add(key)
                queries.append(item)
    return queries[:limit]


def enrich_match_record(base, query_ctx):
    rec = dict(base)
    rec.update({
        'dominio_local': query_ctx.get('dominio_local', '—'),
        'campo_local': query_ctx.get('campo_local', '—'),
        'valor_local': query_ctx.get('valor_local', '—'),
        'frequencia_local': query_ctx.get('frequencia_local', 1),
        'obra_id': query_ctx.get('obra_id'),
        'tipo_relacao': 'closeMatch' if rec.get('confianca', 0) >= 0.72 else 'relatedMatch',
        'status': 'ativo',
        'modo': 'automatico',
        'criado_em': now_str(),
    })
    return rec


def auto_generate_interoperability_mappings(tags_df, obras, meta, limit_per_source=3):
    queries = build_local_interop_queries(tags_df, obras, meta)
    rows = []
    source_status = []
    fetchers = [
        ('Wikidata', fetch_wikidata_matches),
        ('Europeana', fetch_europeana_matches),
        ('IBRAM dados abertos', fetch_dadosgov_matches),
    ]
    next_id = 1
    for q in queries:
        for source_name, fetcher in fetchers:
            matches, err = fetcher(q.get('valor_local', ''), limit=limit_per_source)
            source_status.append({
                'consulta': q.get('valor_local', ''),
                'dominio_local': q.get('dominio_local', '—'),
                'fonte_externa': source_name,
                'status_busca': 'ok' if not err else 'indisponivel',
                'mensagem': err or f"{len(matches)} correspondência(s)",
            })
            for match in matches:
                row = enrich_match_record(match, q)
                row['id'] = next_id
                next_id += 1
                rows.append(row)
    if not rows:
        return pd.DataFrame(), pd.DataFrame(source_status)
    df = pd.DataFrame(rows)
    df = df.sort_values(['confianca', 'frequencia_local'], ascending=[False, False])
    df = df.drop_duplicates(subset=['dominio_local', 'campo_local', 'valor_local', 'fonte_externa', 'identificador_externo'])
    return df.reset_index(drop=True), pd.DataFrame(source_status)


def persist_auto_interoperability(tags_df, obras, meta, actor='admin'):
    matches_df, status_df = auto_generate_interoperability_mappings(tags_df, obras, meta)
    records = matches_df.to_dict(orient='records') if not matches_df.empty else []
    save_interoperability_registry(records)
    summary = {
        'total_conexoes': len(records),
        'fontes_cobertas': sorted(pd.Series([r.get('fonte_externa', '—') for r in records]).dropna().unique().tolist()) if records else [],
        'dominios_locais': sorted(pd.Series([r.get('dominio_local', '—') for r in records]).dropna().unique().tolist()) if records else [],
        'consultas': build_local_interop_queries(tags_df, obras, meta),
        'status_fontes': status_df.to_dict(orient='records') if not status_df.empty else [],
    }
    register_event(
        'interoperability_sync',
        actor,
        'admin',
        'mapeamento_interoperabilidade',
        'auto_sync',
        summary,
        origin='interoperabilidade_automatica',
        automatic=True,
        status='revisado',
        interoperability_refs=summary.get('fontes_cobertas', []),
        semantic_snapshot={'total_conexoes': summary.get('total_conexoes', 0), 'dominios_locais': summary.get('dominios_locais', [])},
        provenance_source='motor_automatico_interoperabilidade',
    )
    return matches_df, status_df


# ── CSS# ── CSS ───────────────────────────────────────────────────────────────
def load_css():
    st.markdown("""
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:'Times New Roman', Times, serif!important}
@keyframes bg{0%{background-position:0% 50%}50%{background-position:100% 50%}100%{background-position:0% 50%}}
.stApp{background:linear-gradient(-45deg,#000 0%,#001F3F 25%,#000 50%,#001F3F 75%,#000 100%);
  background-size:400% 400%;animation:bg 15s ease infinite;color:#e0e0e0}

.top-navbar{position:fixed;top:0;left:0;right:0;z-index:9999;
  background:rgba(255,255,255,.1);backdrop-filter:blur(20px) saturate(180%);
  border-bottom:1px solid rgba(255,255,255,.2);padding:1.4rem 3rem;
  display:flex;justify-content:space-between;align-items:center;
  box-shadow:0 8px 32px rgba(0,0,0,.1)}
.navbar-logo{font-size:1.8rem;font-weight:800;
  background:linear-gradient(135deg,#a7e6ff 0%,#d1baff 100%);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;letter-spacing:-1px}

.main-content{margin-top:120px;padding:2rem 3rem;max-width:1600px;margin-left:auto;margin-right:auto}

.glass-card{background:rgba(255,255,255,.15);backdrop-filter:blur(20px) saturate(180%);
  border:1px solid rgba(255,255,255,.3);border-radius:24px;padding:2.5rem;margin:1.5rem 0;
  box-shadow:0 8px 32px rgba(0,0,0,.1);transition:all .4s cubic-bezier(.4,0,.2,1);
  position:relative;overflow:hidden}
.glass-card::before{content:'';position:absolute;top:0;left:-100%;width:100%;height:100%;
  background:linear-gradient(90deg,transparent,rgba(255,255,255,.3),transparent);transition:left .5s}
.glass-card:hover::before{left:100%}
.glass-card:hover{transform:translateY(-8px) scale(1.02);box-shadow:0 16px 48px rgba(0,0,0,.2);
  border-color:rgba(255,255,255,.5)}

.obra-card{background:rgba(255,255,255,.2);backdrop-filter:blur(15px) saturate(180%);
  border:1px solid rgba(255,255,255,.3);border-radius:20px;overflow:hidden;
  transition:all .4s cubic-bezier(.4,0,.2,1);cursor:pointer;position:relative}
.obra-card::after{content:'';position:absolute;top:0;left:0;right:0;bottom:0;
  background:linear-gradient(135deg,rgba(0,0,0,.3),rgba(0,31,63,.3));opacity:0;transition:opacity .4s}
.obra-card:hover::after{opacity:1}
.obra-card:hover{transform:translateY(-12px) scale(1.03);box-shadow:0 20px 60px rgba(0,31,63,.4);
  border-color:rgba(255,255,255,.6)}
.obra-card img{width:100%;height:280px;object-fit:cover;transition:transform .6s cubic-bezier(.4,0,.2,1)}
.obra-card:hover img{transform:scale(1.15) rotate(2deg)}

.main-title{color:white;font-size:3.5rem;font-weight:800;text-align:center;margin:2rem 0 1rem;
  letter-spacing:-2px;text-shadow:0 4px 20px rgba(0,0,0,.3)}
.subtitle{color:rgba(255,255,255,.95);font-size:1.3rem;text-align:center;margin-bottom:3rem;
  line-height:1.8;font-weight:300}

.tag-badge{display:inline-block;background:rgba(255,255,255,.25);backdrop-filter:blur(10px);
  border:1px solid rgba(255,255,255,.4);color:white;padding:.5rem 1.1rem;border-radius:50px;
  margin:.3rem;font-size:.88rem;font-weight:600;transition:all .3s}
.tag-badge:hover{background:rgba(255,255,255,.4);transform:translateY(-3px) scale(1.05)}
.tag-green {background:rgba(34,197,94,.25)!important;border-color:rgba(34,197,94,.5)!important;color:#dcfce7!important}
.tag-amber {background:rgba(245,158,11,.25)!important;border-color:rgba(245,158,11,.5)!important;color:#fef3c7!important}
.tag-blue  {background:rgba(96,165,250,.25)!important;border-color:rgba(96,165,250,.5)!important;color:#dbeafe!important}

.animal-badge{display:inline-block;background:rgba(167,230,255,.2);border:1px solid rgba(167,230,255,.45);
  color:#a7e6ff;padding:.35rem 1rem;border-radius:50px;font-size:.85rem;font-weight:700}

.kpi-card{background:rgba(255,255,255,.16);backdrop-filter:blur(20px) saturate(180%);
  border:1px solid rgba(255,255,255,.28);border-radius:18px;padding:1.6rem;text-align:center;
  color:white;box-shadow:0 8px 32px rgba(0,0,0,.12);transition:all .4s}
.kpi-card:hover{transform:translateY(-6px) scale(1.04);box-shadow:0 16px 48px rgba(0,31,63,.28)}
.kpi-val{font-size:2.5rem;font-weight:800;margin:.6rem 0;text-shadow:0 4px 20px rgba(0,0,0,.2)}
.kpi-lbl{font-size:.78rem;text-transform:uppercase;letter-spacing:2px;font-weight:600;opacity:.8}
.kpi-sub{font-size:.7rem;opacity:.5;margin-top:.3rem}

.sc{background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.13);border-radius:14px;padding:1.3rem;margin:.7rem 0}
.sc-b{border-left:4px solid #60a5fa;background:rgba(96,165,250,.07)}
.sc-g{border-left:4px solid #34d399;background:rgba(52,211,153,.07)}
.sc-p{border-left:4px solid #a78bfa;background:rgba(167,139,250,.07)}
.sc-a{border-left:4px solid #fbbf24;background:rgba(251,191,36,.07)}

.insight{background:rgba(167,230,255,.1);border:1px solid rgba(167,230,255,.28);border-radius:12px;
  padding:1rem 1.4rem;margin:.6rem 0;color:rgba(255,255,255,.9);font-size:.9rem;line-height:1.7}
.insight strong{color:#a7e6ff}

.conn-row{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;
  background:rgba(255,255,255,.06);border-radius:11px;padding:.85rem 1.2rem;margin:.3rem 0;
  border-left:3px solid rgba(255,255,255,.2);transition:background .2s}
.conn-row:hover{background:rgba(255,255,255,.12)}

.cluster-wrap{background:rgba(255,255,255,.05);border-radius:14px;padding:1.1rem 1.4rem;
  margin:.5rem 0;border:1px solid rgba(255,255,255,.1)}
.cluster-title{font-size:.76rem;text-transform:uppercase;letter-spacing:1.5px;
  color:rgba(167,139,250,.8);margin-bottom:.55rem;font-weight:700}
.cluster-pill{display:inline-flex;align-items:center;gap:5px;background:rgba(168,85,247,.2);
  border:1px solid rgba(168,85,247,.38);border-radius:50px;padding:.32rem .85rem;
  margin:.2rem;font-size:.78rem;font-weight:600;color:#f3e8ff}

.pbar-o{background:rgba(255,255,255,.1);border-radius:50px;height:6px;margin:3px 0;overflow:hidden}
.pbar-i{height:100%;border-radius:50px;transition:width .5s}
.divider{height:1px;background:linear-gradient(90deg,transparent,rgba(255,255,255,.22),transparent);margin:1.6rem 0}

.stButton button{background:rgba(255,255,255,.25)!important;backdrop-filter:blur(15px)!important;
  color:white!important;border:1px solid rgba(255,255,255,.4)!important;border-radius:50px!important;
  padding:1rem 2.5rem!important;font-weight:700!important;font-size:1rem!important;
  transition:all .4s!important;box-shadow:0 8px 25px rgba(0,0,0,.15)!important;
  text-transform:uppercase;letter-spacing:1px}
.stButton button:hover{background:rgba(255,255,255,.4)!important;
  box-shadow:0 12px 40px rgba(0,31,63,.4)!important;
  transform:translateY(-4px) scale(1.05)!important;border-color:rgba(255,255,255,.6)!important}

.stTextInput input,.stTextArea textarea,.stSelectbox select{
  background:rgba(255,255,255,.18)!important;backdrop-filter:blur(10px)!important;
  border:1px solid rgba(255,255,255,.28)!important;color:white!important;
  border-radius:14px!important;padding:.9rem!important;font-weight:500!important}
.stTextInput input::placeholder,.stTextArea textarea::placeholder{color:rgba(255,255,255,.55)!important}
.stTextInput input:focus,.stTextArea textarea:focus{
  border-color:rgba(255,255,255,.6)!important;box-shadow:0 0 0 3px rgba(255,255,255,.18)!important}

label{color:white!important;font-weight:700!important;font-size:1rem!important;
  text-shadow:0 2px 10px rgba(0,0,0,.2)}

.stTabs [data-baseweb="tab-list"]{gap:.7rem;background:rgba(255,255,255,.1);
  backdrop-filter:blur(10px);padding:.45rem;border-radius:14px}
.stTabs [data-baseweb="tab"]{background:rgba(255,255,255,.14);
  border:1px solid rgba(255,255,255,.18);border-radius:10px;color:white;
  padding:.75rem 1.5rem;font-weight:700;transition:all .3s}
.stTabs [data-baseweb="tab"]:hover{background:rgba(255,255,255,.24);transform:translateY(-2px)}
.stTabs [aria-selected="true"]{background:rgba(255,255,255,.33)!important;
  border-color:rgba(255,255,255,.48)!important;box-shadow:0 6px 20px rgba(0,31,63,.25)!important}

.stAlert{background:rgba(255,255,255,.18)!important;backdrop-filter:blur(15px)!important;
  border-radius:14px!important;border-left:4px solid!important;color:white!important}
#MainMenu,footer,header{visibility:hidden}
.stDeployButton{display:none}
[data-testid="stSidebar"]{display:none}
h1,h2,h3,h4,h5,h6{color:white;font-weight:700;text-shadow:0 2px 15px rgba(0,0,0,.3)}
.dataframe{background:rgba(255,255,255,.14)!important;border:1px solid rgba(255,255,255,.2)!important;
  border-radius:14px!important;color:white!important}
.dataframe th{background:rgba(255,255,255,.22)!important;color:white!important;font-weight:700!important}
.dataframe td{color:white!important}
div[data-testid="stTextInput"]>div{background:transparent!important;border:none!important;
  box-shadow:none!important;padding:0!important}
div[data-testid="stTextInput"]{background:transparent!important;border:none!important}
div[data-testid="stTextInput"] input{border-radius:11px!important;
  background:rgba(255,255,255,.14)!important;border:1px solid rgba(255,255,255,.22)!important;
  padding:.75rem 1rem!important}
@media(max-width:768px){.main-title{font-size:2.5rem}.main-content{margin-top:140px;padding:1rem}}
</style>""", unsafe_allow_html=True)

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
    ensure_support_files()
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
    changed = False
    for obra in obras:
        if 'audio_descricao' not in obra:
            obra['audio_descricao'] = f"Audiodescrição de {obra.get('titulo','obra')} por {obra.get('artista','autor não identificado')}, datada de {obra.get('ano','data não informada')}. A obra apresenta composição visual que pode ser descrita e aprofundada pelo setor de documentação."
            changed = True
        if 'metadado_status' not in obra:
            obra['metadado_status'] = 'bruto'
            changed = True
    if changed:
        save_json_file(OBRAS_FILE, obras)
    return obras

def save_answers(uid, animal, answers):
    users = load_json_file(USERS_FILE, [])
    record = {"user_id":uid,"animal_name":animal,
                  "timestamp":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),**answers}
    users.append(record)
    ok = save_json_file(USERS_FILE, users)
    if ok:
        register_event('questionnaire_submission', uid, 'user', 'user_profile', uid, record, origin='questionario', automatic=False, status='bruto')
    return ok

def save_tag(uid, obra_id, tag):
    tags = load_json_file(TAGS_FILE, [])
    clean_tag = tag.lower().strip()
    ontologies = match_ontologies_for_tag(clean_tag)
    record = {
        "id": len(tags) + 1,
        "user_id": uid,
        "obra_id": obra_id,
        "tag": clean_tag,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "bruto",
        "origem": "usuario",
        "automatico": False,
        "grupo_tematico": classify_tag_group(clean_tag),
        "ontologias": ontologies,
        "versao_semantica": 1,
        "proveniencia": {
            "captura": "interface_publica",
            "autor_registro": uid,
            "obra_referenciada": obra_id,
        },
    }
    tags.append(record)
    ok = save_json_file(TAGS_FILE, tags)
    st.cache_data.clear()
    if ok:
        register_event(
            'tag_created', uid, 'user', 'tag', record['id'], record,
            origin='obra', automatic=False, status='bruto',
            semantic_snapshot={
                'grupo_tematico': record['grupo_tematico'],
                'ontologias': ontologies,
            },
            provenance_source='interface_publica',
        )
    return ok

def get_user_tags(uid):
    tags = load_json_file(TAGS_FILE, [])
    ut = [t for t in tags if t['user_id']==uid]
    return pd.DataFrame(ut) if ut else pd.DataFrame()

def get_obra_user_tags(obra_id, uid):
    tags = load_json_file(TAGS_FILE, [])
    f = [t for t in tags if t['obra_id']==obra_id and t['user_id']==uid]
    if f:
        df = pd.DataFrame(f)
        c  = df['tag'].value_counts().reset_index()
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

# ── EXPORTAÇÃO ────────────────────────────────────────────────────────
def html_quest(uid, animal, users_df):
    if users_df.empty: return None
    ud = users_df[users_df['user_id']==uid]
    if ud.empty: return None
    ui = ud.iloc[0]
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<style>*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:sans-serif;background:linear-gradient(135deg,#000,#001F3F);padding:40px;color:white}}
.c{{max-width:900px;margin:0 auto;background:rgba(255,255,255,.15);padding:50px;border-radius:24px;border:1px solid rgba(255,255,255,.3)}}
h1{{text-align:center;margin-bottom:15px;font-size:2.2rem}}
.hi{{text-align:center;margin-bottom:35px;opacity:.9}}
.ab{{background:rgba(167,230,255,.25);border:1px solid rgba(167,230,255,.5);color:#a7e6ff;
  padding:.3rem 1rem;border-radius:50px;font-weight:700;display:inline-block}}
.qb{{margin:22px 0;padding:18px 22px;background:rgba(255,255,255,.1);
  border-left:4px solid rgba(255,255,255,.5);border-radius:12px}}
.q{{font-weight:700;margin-bottom:8px}}.a{{line-height:1.7;opacity:.92}}
.ft{{text-align:center;margin-top:40px;padding-top:18px;
  border-top:1px solid rgba(255,255,255,.2);opacity:.65;font-size:.88rem}}</style></head>
<body><div class="c"><h1>Respostas do Questionário</h1>
<div class="hi">
  <p>Usuário Anônimo: <span class="ab">🐾 {animal}</span></p>
  <p style="margin-top:6px;opacity:.65">Data: {ui.get('timestamp','N/A')}</p>
</div>
<div class="qb"><div class="q">1. Nível de familiaridade com museus</div>
<div class="a">{ui.get('q1','N/A')}</div></div>
<div class="qb"><div class="q">2. Conhecimento sobre documentação museológica</div>
<div class="a">{ui.get('q2','N/A')}</div></div>
<div class="qb"><div class="q">3. O que você entende por 'tags'?</div>
<div class="a">{ui.get('q3','N/A')}</div></div>
<div class="ft">Sistema Folksonomia Digital — Ctrl+P → Salvar como PDF</div>
</div></body></html>"""

def html_tags(uid, animal, obras, tags_df):
    ut = tags_df[tags_df['user_id']==uid] if not tags_df.empty else pd.DataFrame()
    if ut.empty: return None
    od = {o['id']:o for o in obras}
    rows = "".join(
        f"<tr><td>{i+1}</td>"
        f"<td>{od.get(r['obra_id'],{}).get('titulo','Obra '+str(r['obra_id']))}</td>"
        f"<td><span style='background:rgba(255,255,255,.22);padding:3px 10px;border-radius:50px'>{r['tag']}</span></td>"
        f"<td>{r['timestamp']}</td></tr>"
        for i,(_,r) in enumerate(ut.iterrows())
    )
    top = "".join(
        f"<tr><td>{i}</td><td>{t}</td><td>{c}</td></tr>"
        for i,(t,c) in enumerate(ut['tag'].value_counts().head(10).items(),1)
    )
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<style>*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:sans-serif;background:linear-gradient(135deg,#000,#001F3F);padding:40px;color:white}}
.c{{max-width:1100px;margin:0 auto;background:rgba(255,255,255,.15);padding:50px;border-radius:24px;border:1px solid rgba(255,255,255,.3)}}
h1{{text-align:center;margin-bottom:15px;font-size:2.2rem}}
.hi{{text-align:center;margin-bottom:28px;opacity:.9}}
.ab{{background:rgba(167,230,255,.25);border:1px solid rgba(167,230,255,.5);color:#a7e6ff;
  padding:.3rem 1rem;border-radius:50px;font-weight:700;display:inline-block}}
.stats{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin:22px 0}}
.sb{{background:rgba(255,255,255,.14);border:1px solid rgba(255,255,255,.28);
  padding:18px;border-radius:12px;text-align:center}}
.sv{{font-size:2.6rem;font-weight:800}}.sl{{font-size:.82rem;text-transform:uppercase;
  letter-spacing:1.5px;margin-top:7px;opacity:.85}}
table{{width:100%;border-collapse:collapse;margin:18px 0}}
th,td{{padding:13px;text-align:left;border-bottom:1px solid rgba(255,255,255,.14)}}
th{{background:rgba(255,255,255,.18);font-weight:700;text-transform:uppercase;font-size:.82rem}}
tr:nth-child(even){{background:rgba(255,255,255,.04)}}
.ft{{text-align:center;margin-top:38px;padding-top:18px;
  border-top:1px solid rgba(255,255,255,.2);opacity:.65;font-size:.88rem}}</style></head>
<body><div class="c"><h1>Relatório de Tags</h1>
<div class="hi">
  <p>Usuário Anônimo: <span class="ab">🐾 {animal}</span></p>
  <p style="margin-top:6px;opacity:.65">Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
</div>
<div class="stats">
  <div class="sb"><div class="sv">{len(ut)}</div><div class="sl">Total de Tags</div></div>
  <div class="sb"><div class="sv">{ut['tag'].nunique()}</div><div class="sl">Tags Únicas</div></div>
  <div class="sb"><div class="sv">{ut['obra_id'].nunique()}</div><div class="sl">Obras Etiquetadas</div></div>
</div>
<h2 style="margin:28px 0 14px;font-size:1.5rem">Todas as Tags</h2>
<table><thead><tr><th>#</th><th>Obra</th><th>Tag</th><th>Data/Hora</th></tr></thead>
<tbody>{rows}</tbody></table>
<h2 style="margin:28px 0 14px;font-size:1.5rem">Top 10 Tags</h2>
<table><thead><tr><th>Pos.</th><th>Tag</th><th>Freq.</th></tr></thead>
<tbody>{top}</tbody></table>
<div class="ft">Sistema Folksonomia Digital — Ctrl+P → Salvar como PDF</div>
</div></body></html>"""

# ── INTERFACE PRINCIPAL ───────────────────────────────────────────────
def show_header():
    st.markdown(
        "<div class='top-navbar'>"
        "<div class='navbar-logo'>Sistema Folksonomia Digital</div>"
        "</div>", unsafe_allow_html=True)

def main():
    load_css()
    apply_accessibility_settings()
    try: check_admin()
    except Exception as e: st.error(f"Erro ao inicializar: {e}")

    for k,v in [('user_id',gen_uid()),('animal_name',generate_animal_name()),
                ('step','intro'),('answers',{})]:
        if k not in st.session_state: st.session_state[k] = v

    if st.session_state['step'] != 'completed':
        show_intro()
    else:
        show_header()
        st.markdown("<div class='main-content'>", unsafe_allow_html=True)
        t1, t2 = st.tabs([" Explorar Obras"," Área Administrativa"])
        with t1: show_obras()
        with t2: show_admin()
        st.markdown("</div>", unsafe_allow_html=True)

# ── INTRO ─────────────────────────────────────────────────────────────
def show_intro():
    st.markdown("<div class='main-content'>", unsafe_allow_html=True)
    st.markdown("<h1 class='main-title'>Sistema Folksonomia Digital</h1>", unsafe_allow_html=True)
    st.markdown("<p class='subtitle'>Sistema colaborativo de catalogação de obras de arte<br>"
                "Complete o questionário para acessar a plataforma</p>", unsafe_allow_html=True)
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.markdown("<h2 style='text-align:center;margin-bottom:2.2rem;font-size:1.7rem'>"
                "Questionário de Acesso</h2>", unsafe_allow_html=True)
    with st.form("intro_form"):
        c1, c2 = st.columns(2)
        with c1:
            q1 = st.selectbox("1. Qual é o seu nível de familiaridade com museus?",
                ["Nunca visito museus","Visito raramente","Visito ocasionalmente","Visito frequentemente"])
            q2 = st.selectbox("2. Você já ouviu falar sobre documentação museológica?",
                ["Nunca ouvi falar","Já ouvi, mas não sei o que é","Tenho uma ideia básica","Conheço bem o tema"])
        with c2:
            q3 = st.text_area("3. O que você entende por 'tags' ou etiquetas digitais aplicadas a acervo?",
                max_chars=500, height=200, placeholder="Descreva sua compreensão sobre o conceito...")
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
                st.success("Questionário completo! Acesso liberado.")
                st.balloons()
                st.rerun()
    st.markdown("</div></div>", unsafe_allow_html=True)

# ── GALERIA ───────────────────────────────────────────────────────────
def show_obras():
    st.markdown("<h1 class='main-title'>Galeria de Obras de Arte</h1>", unsafe_allow_html=True)
    st.markdown("<p class='subtitle'>Explore as obras e contribua com suas tags descritivas</p>",
                unsafe_allow_html=True)
    render_accessibility_panel()
    obras = load_obras()
    if not obras:
        st.info("Nenhuma obra cadastrada.")
        return
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    c1, c2 = st.columns([2,1])
    with c1:
        sid = st.text_input("Filtrar por número da obra:", "", placeholder="Ex: 1, 2, 3…")
    with c2:
        sord = st.selectbox("Ordenar por:", ["Número (crescente)","Número (decrescente)"])
    st.markdown("</div>", unsafe_allow_html=True)
    filtered = obras
    if sid.strip().isdigit():
        filtered = [o for o in obras if str(o['id'])==sid.strip()]
    filtered = sorted(filtered, key=lambda x: x['id'], reverse=(sord=="Número (decrescente)"))
    st.markdown(f"<div style='text-align:center;color:white;margin:1.8rem 0;"
                f"font-size:1.1rem;font-weight:600'>Exibindo "
                f"<strong style='font-size:1.4rem'>{len(filtered)}</strong> obra(s)</div>",
                unsafe_allow_html=True)
    cols = st.columns(3)
    for i, obra in enumerate(filtered):
        with cols[i%3]:
            st.markdown(f"""<div class='obra-card'>
<img src='{obra['imagem']}' alt='Obra {obra['id']}' />
<div style='padding:1.4rem'>
  <h3 style='font-size:1.05rem;font-weight:700;margin-bottom:.35rem'>Obra #{obra['id']}</h3>
  <p style='font-size:.88rem;opacity:.65'>Adicione uma tag descritiva para esta imagem</p>
</div></div>""", unsafe_allow_html=True)
            if st.button(" Adicionar Tag", key=f"btn_{obra['id']}", use_container_width=True):
                st.session_state['selected_obra'] = obra
                st.rerun()
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
            ut = get_obra_user_tags(obra['id'], st.session_state['user_id'])
            if not ut.empty:
                st.markdown("**Suas Tags:**")
                st.markdown("".join(
                    f"<span class='tag-badge'>{r['tag']} ({r['count']})</span>"
                    for _, r in ut.iterrows()
                ), unsafe_allow_html=True)
            else:
                st.info("Você ainda não criou tags para esta obra")

            render_audio_description_block(obra)

# ── ADMIN ─────────────────────────────────────────────────────────────
def show_admin():
    if 'admin_logged_in' not in st.session_state:
        st.session_state['admin_logged_in'] = False
    if not st.session_state['admin_logged_in']:
        st.markdown("<h1 class='main-title'>Área Administrativa</h1>", unsafe_allow_html=True)
        st.markdown("<p class='subtitle'>Acesso restrito</p>", unsafe_allow_html=True)
        _, c2, _ = st.columns([1,1,1])
        with c2:
            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
            st.markdown("<h2 style='text-align:center;margin-bottom:1.8rem'>"
                        "Login Administrativo</h2>", unsafe_allow_html=True)
            with st.form("login"):
                username = st.text_input("Usuário:", placeholder="Digite seu usuário")
                password = st.text_input("Senha:", type="password", placeholder="Digite sua senha")
                sub = st.form_submit_button("Entrar no Sistema", use_container_width=True)
                if sub:
                    if check_login(username, password):
                        st.session_state['admin_logged_in'] = True
                        st.session_state['admin_username']  = username
                        st.success("Login realizado com sucesso!")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("Credenciais inválidas. Acesso negado.")
            st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.markdown(
            f"<h1 class='main-title'>Dashboard Administrativo</h1>"
            f"<p class='subtitle'>Bem-vindo, "
            f"<strong>{st.session_state.get('admin_username','Admin')}</strong></p>",
            unsafe_allow_html=True)
        tabs = st.tabs([
            " Visão Geral",
            " Análise de Tags",
            " Conexões de Tags",
            " Usuários & Questionário",
            " Ontologias",
            " Validação & Auditoria",
            " Grafo & Open Data",
            " Obras",
            " Exportar"
        ])
        with tabs[0]: tab_overview()
        with tabs[1]: tab_tags()
        with tabs[2]: tab_connections()
        with tabs[3]: tab_users_quest()
        with tabs[4]: tab_ontologies()
        with tabs[5]: tab_validation_audit()
        with tabs[6]: tab_graph_open_data()
        with tabs[7]: tab_obras()
        with tabs[8]: tab_export()
        _, c2, _ = st.columns([1,1,1])
        with c2:
            if st.button(" Sair do Sistema", use_container_width=True):
                st.session_state['admin_logged_in'] = False
                st.rerun()

# ═════════════════════════════════════════════════════════════════════
# ABA 1 — VISÃO GERAL
# ═════════════════════════════════════════════════════════════════════
def tab_overview():
    tdf = all_tags()
    udf = all_users()
    obs = load_obras()

    st.markdown("### Métricas Gerais do Sistema")
    total  = len(tdf) if not tdf.empty else 0
    unicas = tdf['tag'].nunique() if not tdf.empty else 0
    nusers = udf['user_id'].nunique() if not udf.empty else 0
    nobs   = len(obs)
    obs_ct = tdf['obra_id'].nunique() if not tdf.empty else 0

    c1,c2,c3,c4,c5 = st.columns(5)
    for col, lbl, val, sub, clr in [
        (c1,"Total de Tags",     total,   "registros","#a7e6ff"),
        (c2,"Tags Únicas",       unicas,  f"{unicas/total:.0%} do total" if total else "—","#d1baff"),
        (c3,"Participantes",     nusers,  "usuários ativos","#6ee7b7"),
        (c4,"Obras Cadastradas", nobs,    f"{obs_ct} com tags","#fcd34d"),
        (c5,"Média Tags/Usuário",f"{total/nusers:.1f}" if nusers else "—","por participante","#f9a8d4"),
    ]:
        with col: st.markdown(kpi(lbl,val,sub,clr), unsafe_allow_html=True)

    st.markdown(divider(), unsafe_allow_html=True)

    if not udf.empty and not tdf.empty:
        st.markdown("### Participantes Anônimos")
        uct = tdf.groupby('user_id').size().reset_index(name='tags')
        uuq = tdf.groupby('user_id')['tag'].nunique().reset_index(name='unicas')
        m   = udf.merge(uct,on='user_id',how='left').merge(uuq,on='user_id',how='left').fillna(0)
        for _, row in m.iterrows():
            animal = row.get('animal_name','?')
            ts     = row.get('timestamp','N/A')
            nt, nu = int(row['tags']), int(row['unicas'])
            p      = nu/nt if nt>0 else 0
            st.markdown(
                f"<div class='sc sc-b' style='padding:.85rem 1.3rem;margin:.25rem 0'>"
                f"<div style='display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px'>"
                f"<div><span class='animal-badge'>🐾 {animal}</span>"
                f"<span style='color:rgba(255,255,255,.45);font-size:.75rem;margin-left:10px'>Acesso: {ts}</span></div>"
                f"<div style='text-align:right;min-width:170px'>"
                f"<span style='color:white;font-weight:700'>{nt} tags</span>"
                f"<span style='color:rgba(255,255,255,.4);font-size:.78rem'> ({nu} únicas)</span>"
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
# ABA 2 — ANÁLISE DE TAGS (Frequência + Temporal)
# ═════════════════════════════════════════════════════════════════════
def tab_tags():
    tdf = all_tags()
    if tdf.empty:
        st.info("Nenhuma tag disponível.")
        return

    st.markdown("### Análise de Tags")
    t1, t2 = st.tabs([" Frequência e Vocabulário", " Evolução Temporal"])

    # ─── FREQUÊNCIA ───────────────────────────────────────────────────
    with t1:
        freq = tdf['tag'].value_counts().reset_index()
        freq.columns = ['Tag','Frequência']
        total_usos = freq['Frequência'].sum()
        freq['% do Total']  = (freq['Frequência']/total_usos*100).round(2)
        freq['% Acumulada'] = freq['% do Total'].cumsum().round(2)
        freq['Categoria']   = pd.cut(
            freq['Frequência'],
            bins=[0,1,2,5,10,99999],
            labels=['Hapax (1×)','Rara (2×)','Ocasional (3–5×)','Frequente (6–10×)','Muito Frequente (10+×)']
        )

        hapax  = (freq['Frequência']==1).sum()
        lei80  = (freq['% Acumulada']<=80).sum()
        ttr    = len(freq)/total_usos if total_usos else 0
        top1p  = freq.iloc[0]['% do Total'] if not freq.empty else 0

        c1,c2,c3,c4 = st.columns(4)
        with c1: st.markdown(kpi("Vocabulário Total",  len(freq), "tags distintas","#a7e6ff"), unsafe_allow_html=True)
        with c2: st.markdown(kpi("Hapax Legomena",     hapax,     f"{hapax/len(freq):.0%} do vocab.","#f9a8d4"), unsafe_allow_html=True)
        with c3: st.markdown(kpi("80% dos Usos",       f"{lei80} tags","lei de Zipf","#6ee7b7"), unsafe_allow_html=True)
        with c4: st.markdown(kpi("Type-Token Ratio",   f"{ttr:.3f}","riqueza global","#fcd34d"), unsafe_allow_html=True)

        st.markdown(insight(
            f"<strong>Distribuição de Zipf:</strong> As {lei80} tags mais frequentes cobrem 80% de todos os usos. "
            f"Existem {hapax} hapax legomena — termos usados somente uma vez "
            f"({hapax/len(freq):.0%} do vocabulário total). "
            f"TTR global de <strong>{ttr:.3f}</strong> indica "
            f"{'alta' if ttr>0.5 else 'moderada' if ttr>0.25 else 'baixa'} diversidade lexical."
        ), unsafe_allow_html=True)

        st.markdown(divider(), unsafe_allow_html=True)
        st.markdown("#### Frequência — Top 25 Tags")
        st.bar_chart(tdf['tag'].value_counts().head(25))

        st.markdown("#### Tabela Completa de Frequências")
        cat_opts = list(freq['Categoria'].cat.categories)
        cat_sel  = st.multiselect("Filtrar por categoria:", cat_opts, default=cat_opts, key="fc")
        disp = freq[freq['Categoria'].isin(cat_sel)] if cat_sel else freq
        st.dataframe(disp, use_container_width=True, hide_index=True)

        c1, c2 = st.columns(2)
        with c1:
            st.download_button(
                " Frequências (CSV)",
                freq.to_csv(index=False).encode('utf-8'),
                f"frequencias_{datetime.now().strftime('%Y%m%d')}.csv",
                "text/csv", use_container_width=True)
        with c2:
            st.markdown("**Distribuição por Categoria:**")
            cd = freq['Categoria'].value_counts().reset_index()
            cd.columns = ['Categoria','Qtd']
            st.dataframe(cd, use_container_width=True, hide_index=True)

    # ─── TEMPORAL ─────────────────────────────────────────────────────
    with t2:
        st.markdown("#### Evolução Temporal das Tags")
        try:
            tf = tdf.copy()
            tf['ts']    = pd.to_datetime(tf['timestamp'])
            tf['date']  = tf['ts'].dt.date
            tf['ano']   = tf['ts'].dt.year
            tf['mes']   = tf['ts'].dt.month
            tf['dia']   = tf['ts'].dt.day
            tf['hora']  = tf['ts'].dt.hour
            tf['dow']   = tf['ts'].dt.day_name()
            tf['semana']= tf['ts'].dt.isocalendar().week.astype(int)

            # ── KPIs temporais ──
            dias_ativos = tf['date'].nunique()
            media_dia   = len(tf)/dias_ativos if dias_ativos else 0
            pico_dia    = tf.groupby('date').size()
            pico_val    = int(pico_dia.max()) if not pico_dia.empty else 0
            pico_dt     = str(pico_dia.idxmax()) if not pico_dia.empty else "—"

            c1,c2,c3,c4 = st.columns(4)
            with c1: st.markdown(kpi("Dias com Atividade", dias_ativos,"dias","#a7e6ff"), unsafe_allow_html=True)
            with c2: st.markdown(kpi("Média por Dia",      f"{media_dia:.1f}","tags/dia","#6ee7b7"), unsafe_allow_html=True)
            with c3: st.markdown(kpi("Pico de Tags",       pico_val,f"em {pico_dt}","#fcd34d"), unsafe_allow_html=True)
            with c4: st.markdown(kpi("Período Total",      f"{dias_ativos} dias","registrado","#d1baff"), unsafe_allow_html=True)

            st.markdown(divider(), unsafe_allow_html=True)

            # ── Linha: tags por dia ──
            daily = tf.groupby('date').agg(
                Tags=('tag','count'),
                Tags_Unicas=('tag','nunique'),
                Usuarios=('user_id','nunique')
            ).reset_index().rename(columns={'date':'Data'})

            st.markdown("#### Tags Criadas por Dia")
            st.line_chart(daily.set_index('Data')['Tags'])

            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Usuários ativos por dia**")
                st.line_chart(daily.set_index('Data')['Usuarios'])
            with c2:
                st.markdown("**Tags únicas por dia**")
                st.line_chart(daily.set_index('Data')['Tags_Unicas'])

            st.markdown(divider(), unsafe_allow_html=True)

            # ── Por mês ──
            st.markdown("#### Distribuição Mensal")
            meses_pt = {1:"Jan",2:"Fev",3:"Mar",4:"Abr",5:"Mai",6:"Jun",
                        7:"Jul",8:"Ago",9:"Set",10:"Out",11:"Nov",12:"Dez"}
            monthly = tf.groupby(['ano','mes']).agg(
                Tags=('tag','count'),
                Tags_Unicas=('tag','nunique'),
                Usuarios=('user_id','nunique')
            ).reset_index()
            monthly['Mês/Ano'] = monthly['mes'].map(meses_pt)+"/"+monthly['ano'].astype(str)
            monthly = monthly.sort_values(['ano','mes'])

            st.bar_chart(monthly.set_index('Mês/Ano')['Tags'])

            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Usuários únicos por mês**")
                st.bar_chart(monthly.set_index('Mês/Ano')['Usuarios'])
            with c2:
                st.markdown("**Tags únicas por mês**")
                st.bar_chart(monthly.set_index('Mês/Ano')['Tags_Unicas'])

            st.markdown(divider(), unsafe_allow_html=True)

            # ── Por ano ──
            st.markdown("#### Distribuição Anual")
            yearly = tf.groupby('ano').agg(
                Tags=('tag','count'),
                Tags_Unicas=('tag','nunique'),
                Usuarios=('user_id','nunique')
            ).reset_index().rename(columns={'ano':'Ano'})
            st.bar_chart(yearly.set_index('Ano')['Tags'])
            st.dataframe(yearly, use_container_width=True, hide_index=True)

            st.markdown(divider(), unsafe_allow_html=True)

            # ── Distribuição por dia da semana e hora ──
            st.markdown("#### Padrões de Uso")
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Distribuição por Hora do Dia**")
                st.bar_chart(tf['hora'].value_counts().sort_index().rename("Tags"))
            with c2:
                st.markdown("**Distribuição por Dia da Semana**")
                dow_order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
                dow_pt    = {"Monday":"Seg","Tuesday":"Ter","Wednesday":"Qua","Thursday":"Qui",
                             "Friday":"Sex","Saturday":"Sáb","Sunday":"Dom"}
                dow_c = tf['dow'].value_counts().reindex(dow_order,fill_value=0)
                dow_c.index = [dow_pt.get(d,d) for d in dow_c.index]
                st.bar_chart(dow_c.rename("Tags"))

            st.markdown(divider(), unsafe_allow_html=True)

            # ── Tabela consolidada ──
            st.markdown("#### Tabela Detalhada por Dia")
            daily_full = tf.groupby('date').agg(
                Total=('tag','count'),
                Unicas=('tag','nunique'),
                Usuarios=('user_id','nunique'),
                Tag_Mais_Usada=('tag', lambda x: x.value_counts().index[0])
            ).reset_index()
            daily_full.columns = ['Data','Tags Criadas','Tags Únicas','Usuários Ativos','Tag Mais Usada']
            daily_full = daily_full.sort_values('Data',ascending=False)
            st.dataframe(daily_full, use_container_width=True, hide_index=True)

            st.markdown("#### Tabela Mensal Consolidada")
            monthly_full = monthly[['Mês/Ano','Tags','Tags_Unicas','Usuarios']].copy()
            monthly_full.columns = ['Mês/Ano','Tags Criadas','Tags Únicas','Usuários Ativos']
            st.dataframe(monthly_full, use_container_width=True, hide_index=True)

            if len(daily)>1:
                st.markdown(insight(
                    f"<strong>Tendência:</strong> Pico de <strong>{pico_val} tags</strong> em {pico_dt}. "
                    f"Média de <strong>{media_dia:.1f} tags/dia</strong> nos {dias_ativos} dias com atividade. "
                    f"Total de {len(tf)} tags distribuídas ao longo de "
                    f"{monthly['ano'].nunique()} ano(s) e {len(monthly)} mês(es) registrado(s)."
                ), unsafe_allow_html=True)

        except Exception as e:
            st.info(f"Dados insuficientes para análise temporal.")

# ═════════════════════════════════════════════════════════════════════
# ABA 3 — CONEXÕES DE TAGS
# ═════════════════════════════════════════════════════════════════════
def tab_connections():
    tdf  = all_tags()
    obs  = load_obras()
    od   = {o['id']:o['titulo'] for o in obs}
    if tdf.empty:
        st.warning("Nenhuma tag disponível.")
        return

    st.markdown("### Conexões e Agrupamentos de Tags")
    st.markdown(insight(
        "<strong>Como funciona:</strong> O algoritmo combina três métricas — "
        "<strong>Contenção de substring</strong> (ex: 'vaso' → 'vaso verde'), "
        "<strong>Jaccard de palavras</strong> (ex: 'barco preto' ↔ 'barco de barro') e "
        "<strong>Jaccard de trigramas</strong> (similaridade fonética). "
        "Score de 0 (sem relação) a 1 (idênticas)."
    ), unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1: threshold = st.slider("Limiar de similaridade:", 0.20, 0.90, 0.35, 0.05, key="ct")
    with c2: obra_f    = st.selectbox("Filtrar por obra:", ["Todas"]+[f"#{o['id']} — {o['titulo']}" for o in obs], key="co")
    with c3: max_c     = st.number_input("Máx. conexões:", 10, 300, 60, 10, key="cm")

    fdf = tdf.copy()
    if obra_f != "Todas":
        oid = int(obra_f.split("—")[0].replace("#","").strip())
        fdf = tdf[tdf['obra_id']==oid]

    all_t = fdf['tag'].tolist()
    if len(set(all_t)) < 2:
        st.warning("Necessário ao menos 2 tags distintas.")
        return

    with st.spinner("Calculando conexões…"):
        conns    = tag_connections(all_t, threshold=threshold)
        clusters = tag_clusters(all_t, threshold=threshold)

    c1,c2,c3 = st.columns(3)
    with c1: st.markdown(kpi("Total de Conexões", len(conns),   f"limiar ≥ {threshold:.2f}","#a7e6ff"), unsafe_allow_html=True)
    with c2: st.markdown(kpi("Grupos Formados",   len(clusters),"clusters de tags","#d1baff"), unsafe_allow_html=True)
    with c3: st.markdown(kpi("Tags Envolvidas",   len(set(c['tag_a'] for c in conns)|set(c['tag_b'] for c in conns)),
                              "tags conectadas","#6ee7b7"), unsafe_allow_html=True)

    st.markdown(divider(), unsafe_allow_html=True)

    t1, t2 = st.tabs([" Lista de Conexões"," Grupos de Tags"])

    # ── LISTA ─────────────────────────────────────────────────────────
    with t1:
        if not conns:
            st.info("Nenhuma conexão encontrada. Reduza o limiar de similaridade.")
        else:
            tipos    = sorted(set(c['tipo'] for c in conns))
            tipo_sel = st.multiselect("Filtrar por tipo:", tipos, default=tipos, key="tsel")
            cf = [c for c in conns if c['tipo'] in tipo_sel][:max_c]
            freq_map = tdf['tag'].value_counts().to_dict()

            st.markdown(f"Exibindo **{len(cf)}** de **{len(conns)}** conexões")
            st.markdown(divider(), unsafe_allow_html=True)

            for c in cf:
                s   = c['similaridade']
                bar = "█"*int(s*10)+"░"*(10-int(s*10))
                fa  = freq_map.get(c['tag_a'],0)
                fb  = freq_map.get(c['tag_b'],0)
                st.markdown(
                    f"<div class='conn-row'>"
                    f"<div style='display:flex;align-items:center;gap:10px;flex-wrap:wrap'>"
                    f"<span class='tag-badge'>{c['tag_a']}</span>"
                    f"<span style='color:rgba(255,255,255,.3);font-size:.72rem'>({fa}×)</span>"
                    f"<span style='color:rgba(255,255,255,.38)'>↔</span>"
                    f"<span class='tag-badge'>{c['tag_b']}</span>"
                    f"<span style='color:rgba(255,255,255,.3);font-size:.72rem'>({fb}×)</span>"
                    f"</div>"
                    f"<div style='text-align:right;min-width:195px'>"
                    f"<span style='font-family:monospace;color:rgba(255,255,255,.6);font-size:.78rem'>"
                    f"{bar} {s:.3f}</span><br>"
                    f"<span style='font-size:.7rem;color:rgba(255,255,255,.35)'>{c['tipo']}</span>"
                    f"</div></div>", unsafe_allow_html=True)

            st.markdown(divider(), unsafe_allow_html=True)
            st.download_button(
                "⬇️ Baixar conexões (CSV)",
                pd.DataFrame(conns).to_csv(index=False).encode('utf-8'),
                f"conexoes_{datetime.now().strftime('%Y%m%d')}.csv","text/csv")

    # ── CLUSTERS ──────────────────────────────────────────────────────
    with t2:
        if not clusters:
            st.info("Nenhum grupo formado. Reduza o limiar de similaridade.")
        else:
            COLORS = ["#60a5fa","#34d399","#f9a8d4","#fcd34d","#a78bfa",
                      "#f87171","#67e8f9","#86efac","#fb923c","#c084fc"]
            freq_map     = tdf['tag'].value_counts().to_dict()
            cls_sorted   = sorted(clusters, key=len, reverse=True)

            st.markdown(f"**{len(cls_sorted)} grupo(s) de tags relacionadas**")
            st.markdown(divider(), unsafe_allow_html=True)

            for i, cl in enumerate(cls_sorted, 1):
                color      = COLORS[(i-1) % len(COLORS)]
                total_uses = sum(freq_map.get(t,0) for t in cl)
                pills = "".join(
                    f"<span class='cluster-pill'>{t} "
                    f"<span style='opacity:.5;font-size:.7rem'>({freq_map.get(t,0)}×)</span></span>"
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
                "⬇️ Baixar grupos (CSV)",
                summ.to_csv(index=False).encode('utf-8'),
                f"clusters_{datetime.now().strftime('%Y%m%d')}.csv","text/csv")

# ═════════════════════════════════════════════════════════════════════
# ABA 4 — USUÁRIOS & QUESTIONÁRIO (unificado)
# ═════════════════════════════════════════════════════════════════════
def tab_users_quest():
    tdf = all_tags()
    udf = all_users()
    obs = load_obras()
    od  = {o['id']:o['titulo'] for o in obs}

    if udf.empty:
        st.info("Nenhum dado de usuário disponível.")
        return

    st.markdown("### Usuários & Questionário")

    # ── KPIs combinados ──
    uct = tdf.groupby('user_id').size().reset_index(name='Total_Tags') if not tdf.empty else pd.DataFrame(columns=['user_id','Total_Tags'])
    uuq = tdf.groupby('user_id')['tag'].nunique().reset_index(name='Tags_Unicas') if not tdf.empty else pd.DataFrame(columns=['user_id','Tags_Unicas'])
    uob = tdf.groupby('user_id')['obra_id'].nunique().reset_index(name='Obras') if not tdf.empty else pd.DataFrame(columns=['user_id','Obras'])

    merged = udf.merge(uct,on='user_id',how='left') \
                .merge(uuq,on='user_id',how='left') \
                .merge(uob,on='user_id',how='left').fillna(0)
    merged['TTR']     = (merged['Tags_Unicas']/merged['Total_Tags'].replace(0,np.nan)).fillna(0).round(3)
    merged['Usuário'] = merged.apply(lambda r: r.get('animal_name', r['user_id'][:8]), axis=1)

    c1,c2,c3,c4 = st.columns(4)
    top_u = merged.loc[merged['Total_Tags'].idxmax(),'Usuário'] if not merged.empty else "—"
    with c1: st.markdown(kpi("Participantes",       len(merged),"usuários","#a7e6ff"), unsafe_allow_html=True)
    with c2: st.markdown(kpi("Média Tags/Usuário",  f"{merged['Total_Tags'].mean():.1f}","","#6ee7b7"), unsafe_allow_html=True)
    with c3: st.markdown(kpi("Maior Contribuição",  int(merged['Total_Tags'].max()),top_u[:16],"#fcd34d"), unsafe_allow_html=True)
    with c4: st.markdown(kpi("Riqueza Média (TTR)", f"{merged['TTR'].mean():.2%}","vocabular","#d1baff"), unsafe_allow_html=True)

    st.markdown(divider(), unsafe_allow_html=True)

    t1, t2, t3, t4 = st.tabs([
        " Tabela de Participantes",
        " Perfil Individual",
        "Respostas do Questionário",
        " Cruzamentos"
    ])

    # ── TABELA ────────────────────────────────────────────────────────
    with t1:
        st.markdown("#### Comparativo Geral de Participantes")
        dcols = ['Usuário','Total_Tags','Tags_Unicas','TTR','Obras','q1','q2']
        avail = [c for c in dcols if c in merged.columns]
        disp  = merged[avail].rename(columns={
            'Total_Tags':'Tags Criadas','Tags_Unicas':'Tags Únicas',
            'Obras':'Obras Etiquetadas','q1':'Familiaridade c/ Museus',
            'q2':'Conhec. Museológico'
        }).sort_values('Tags Criadas',ascending=False)
        st.dataframe(disp, use_container_width=True, hide_index=True)

        st.markdown(divider(), unsafe_allow_html=True)
        st.markdown("#### Contribuição por Participante")
        st.bar_chart(merged.set_index('Usuário')['Total_Tags'].sort_values(ascending=False))

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Riqueza Vocabular (TTR) por Usuário**")
            st.bar_chart(merged.set_index('Usuário')['TTR'].sort_values(ascending=False))
        with c2:
            st.markdown("**Obras Etiquetadas por Usuário**")
            st.bar_chart(merged.set_index('Usuário')['Obras'].sort_values(ascending=False))

    # ── PERFIL INDIVIDUAL ────────────────────────────────────────────
    with t2:
        st.markdown("#### Perfil Detalhado por Participante")
        uopts = [f"🐾 {r.get('animal_name',r['user_id'][:8])}" for _,r in udf.iterrows()]
        usel  = st.selectbox("Selecione um participante:", uopts, key="ui_sel")
        uidx  = uopts.index(usel)
        uid   = udf.iloc[uidx]['user_id']
        uanim = udf.iloc[uidx].get('animal_name', uid[:8])

        utags = tdf[tdf['user_id']==uid] if not tdf.empty else pd.DataFrame()
        if utags.empty:
            st.info("Este participante ainda não criou tags.")
        else:
            ttl = len(utags); unq = utags['tag'].nunique()
            ttr_u = unq/ttl if ttl else 0

            c1,c2,c3 = st.columns(3)
            with c1: st.markdown(kpi("Tags Criadas", ttl,"","#a7e6ff"), unsafe_allow_html=True)
            with c2: st.markdown(kpi("Tags Únicas",  unq,f"TTR: {ttr_u:.2%}","#6ee7b7"), unsafe_allow_html=True)
            with c3: st.markdown(kpi("Obras Tagueadas",utags['obra_id'].nunique(),"","#fcd34d"), unsafe_allow_html=True)

            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"**Top tags de {uanim}:**")
                st.bar_chart(utags['tag'].value_counts().head(15))
            with c2:
                st.markdown("**Distribuição por obra:**")
                st.bar_chart(utags.groupby('obra_id').size().rename(index=od))

            st.markdown("**Conexões nas tags deste participante (limiar 0.30):**")
            uconns = tag_connections(utags['tag'].tolist(), threshold=0.30)
            if uconns:
                for c in uconns[:10]:
                    freq_map = utags['tag'].value_counts().to_dict()
                    fa = freq_map.get(c['tag_a'],0)
                    fb = freq_map.get(c['tag_b'],0)
                    st.markdown(
                        f"<div class='conn-row'>"
                        f"<div style='display:flex;align-items:center;gap:9px;flex-wrap:wrap'>"
                        f"<span class='tag-badge'>{c['tag_a']}</span>"
                        f"<span style='color:rgba(255,255,255,.3);font-size:.7rem'>({fa}×)</span>"
                        f"<span style='color:rgba(255,255,255,.35)'>↔</span>"
                        f"<span class='tag-badge'>{c['tag_b']}</span>"
                        f"<span style='color:rgba(255,255,255,.3);font-size:.7rem'>({fb}×)</span>"
                        f"</div>"
                        f"<span style='color:rgba(255,255,255,.35);font-size:.75rem'>"
                        f"{c['similaridade']:.3f} · {c['tipo']}</span>"
                        f"</div>", unsafe_allow_html=True)
            else:
                st.info("Nenhuma conexão encontrada nas tags deste participante.")

            st.markdown(divider(), unsafe_allow_html=True)
            st.markdown("**Todas as tags criadas:**")
            ft = utags.copy()
            ft['Obra'] = ft['obra_id'].map(od)
            st.dataframe(
                ft[['tag','Obra','timestamp']].rename(columns={'tag':'Tag','timestamp':'Data/Hora'}),
                use_container_width=True, hide_index=True)

    # ── QUESTIONÁRIO ─────────────────────────────────────────────────
    with t3:
        st.markdown("#### Respostas do Questionário de Perfil")

        c1,c2 = st.columns(2)
        with c1:
            st.markdown("**Q1 — Familiaridade com Museus**")
            q1c = udf['q1'].value_counts()
            st.bar_chart(q1c)
            q1p = (q1c/q1c.sum()*100).round(1).reset_index()
            q1p.columns=['Resposta','%']
            st.dataframe(q1p, use_container_width=True, hide_index=True)

        with c2:
            st.markdown("**Q2 — Conhecimento sobre Documentação Museológica**")
            q2c = udf['q2'].value_counts()
            st.bar_chart(q2c)
            q2p = (q2c/q2c.sum()*100).round(1).reset_index()
            q2p.columns=['Resposta','%']
            st.dataframe(q2p, use_container_width=True, hide_index=True)

        st.markdown(divider(), unsafe_allow_html=True)
        st.markdown("**Q3 — Respostas Abertas: O que você entende por 'tags'?**")
        disp = udf.copy()
        if 'animal_name' in disp.columns:
            disp = disp.rename(columns={'animal_name':'Usuário Anônimo'})
        disp['Palavras'] = disp['q3'].str.split().str.len()
        st.markdown(
            f"Comprimento médio das respostas: "
            f"**{disp['Palavras'].mean():.0f} palavras** por participante"
        )
        st.bar_chart(disp['Palavras'].value_counts().sort_index().rename("Qtd Respostas"))

        st.markdown(divider(), unsafe_allow_html=True)
        st.dataframe(
            disp[['Usuário Anônimo','q3','Palavras','timestamp']]
            .sort_values('timestamp',ascending=False)
            .rename(columns={'q3':'Resposta','timestamp':'Data/Hora'}),
            use_container_width=True, hide_index=True)

    # ── CRUZAMENTOS ───────────────────────────────────────────────────
    with t4:
        if tdf.empty:
            st.info("Dados de tags insuficientes para cruzamentos.")
            return

        st.markdown("#### Cruzamentos: Perfil do Participante × Comportamento de Tagging")

        m = merged.copy()
        m['TTR'] = (m['Tags_Unicas']/m['Total_Tags'].replace(0,np.nan)).fillna(0)

        st.markdown(divider(), unsafe_allow_html=True)
        st.markdown("**Familiaridade com Museus × Média de Tags Criadas**")
        avg_q1 = m.groupby('q1')['Total_Tags'].mean().sort_values(ascending=False)
        st.bar_chart(avg_q1)
        t_q1 = avg_q1.reset_index()
        t_q1.columns = ['Familiaridade','Média de Tags']
        t_q1['Média de Tags'] = t_q1['Média de Tags'].round(2)
        st.dataframe(t_q1, use_container_width=True, hide_index=True)

        st.markdown(divider(), unsafe_allow_html=True)
        st.markdown("**Conhecimento Museológico × Tags Únicas**")
        avg_q2 = m.groupby('q2')['Tags_Unicas'].mean().sort_values(ascending=False)
        st.bar_chart(avg_q2)
        t_q2 = avg_q2.reset_index()
        t_q2.columns = ['Conhecimento','Média Tags Únicas']
        t_q2['Média Tags Únicas'] = t_q2['Média Tags Únicas'].round(2)
        st.dataframe(t_q2, use_container_width=True, hide_index=True)

        st.markdown(divider(), unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Familiaridade × Riqueza Vocabular (TTR)**")
            avg_ttr = m.groupby('q1')['TTR'].mean().sort_values(ascending=False)
            st.bar_chart(avg_ttr)
        with c2:
            st.markdown("**Conhecimento Museológico × TTR**")
            avg_ttr2 = m.groupby('q2')['TTR'].mean().sort_values(ascending=False)
            st.bar_chart(avg_ttr2)

        st.markdown(divider(), unsafe_allow_html=True)
        st.markdown("#### Tabela Consolidada de Cruzamentos")
        cross = m.groupby('q1').agg(
            Usuários     =('user_id','count'),
            Média_Tags   =('Total_Tags','mean'),
            Média_Únicas =('Tags_Unicas','mean'),
            Riqueza_TTR  =('TTR','mean'),
        ).round(2).reset_index()
        cross.columns = ['Familiaridade','Usuários','Média Tags','Média Únicas','Riqueza (TTR)']
        st.dataframe(cross, use_container_width=True, hide_index=True)

        st.markdown(insight(
            "<strong>Interpretação:</strong> Compare se participantes mais familiarizados com museus "
            "produzem mais tags, maior diversidade vocabular (TTR) ou tags mais descritivas. "
            "A riqueza vocabular (TTR) mede a proporção de termos únicos sobre o total criado — "
            "valores próximos de 1.0 indicam alta originalidade e variedade nas tags."
        ), unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════════════════
# ABA 5 — ONTOLOGIAS
# ═════════════════════════════════════════════════════════════════════
def tab_ontologies():
    st.markdown("### Ontologias pré-marcadas e análise semântica")
    tdf = all_tags()
    ontologies = load_ontologies()

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(kpi("Ontologias", len(ontologies), "vocabulários ativos", "#a7e6ff"), unsafe_allow_html=True)
    with c2:
        st.markdown(kpi("Termos Controlados", sum(len(o.get('termos', [])) for o in ontologies), "termos cadastrados", "#6ee7b7"), unsafe_allow_html=True)
    with c3:
        usados = analyze_ontology_usage(tdf, ontologies)
        ocorrencias = int(usados['Ocorrências'].sum()) if not usados.empty else 0
        st.markdown(kpi("Correspondências", ocorrencias, "tags ligadas a ontologias", "#fcd34d"), unsafe_allow_html=True)

    t1, t2, t3 = st.tabs([" Ontologias cadastradas", " Criar ontologia", " Analisar ontologias"])

    with t1:
        if not ontologies:
            st.info("Nenhuma ontologia cadastrada.")
        else:
            for ont in ontologies:
                termos = ont.get('termos', [])
                st.markdown(
                    f"""
                    <div class='glass-card'>
                        <h3 style='margin-bottom:.4rem'>{ont.get('nome','Ontologia')}</h3>
                        <p><strong>Categoria:</strong> {ont.get('categoria','—')}</p>
                        <p><strong>Descrição:</strong> {ont.get('descricao','—')}</p>
                        <p><strong>Termos:</strong> {', '.join(termos) if termos else '—'}</p>
                        <p><strong>Criado em:</strong> {ont.get('criado_em','—')}</p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

    with t2:
        with st.form('nova_ontologia'):
            nome = st.text_input('Nome da ontologia', placeholder='Ex: Iconografia religiosa')
            categoria = st.selectbox('Categoria', ['tema', 'atributo', 'material', 'cor', 'periodo', 'personagem', 'evento'])
            descricao = st.text_area('Descrição', placeholder='Explique para que serve esta ontologia...')
            termos = st.text_area('Termos pré-marcados', placeholder='Separe por vírgula. Ex: santo, altar, cruz, anjo')
            submit = st.form_submit_button('Salvar ontologia')
            if submit:
                if not nome.strip() or not termos.strip():
                    st.error('Preencha ao menos o nome e os termos da ontologia.')
                else:
                    new_id = max([o.get('id', 0) for o in ontologies], default=0) + 1
                    record = {
                        'id': new_id,
                        'nome': nome.strip(),
                        'categoria': categoria,
                        'descricao': descricao.strip(),
                        'termos': [t.strip() for t in termos.split(',') if t.strip()],
                        'criado_em': now_str(),
                    }
                    ontologies.append(record)
                    save_ontologies(ontologies)
                    register_event(
                        'ontology_created',
                        st.session_state.get('admin_username', 'admin'),
                        'admin',
                        'ontologia',
                        new_id,
                        record,
                        origin='gestao_ontologias',
                        automatic=False,
                        status='validado'
                    )
                    st.success('Ontologia criada com sucesso.')
                    st.rerun()

    with t3:
        st.markdown('#### Uso das ontologias sobre as tags existentes')
        usage = analyze_ontology_usage(tdf, ontologies)
        if usage.empty:
            st.info('Ainda não há tags para cruzar com as ontologias.')
        else:
            st.dataframe(usage, use_container_width=True, hide_index=True)
            st.bar_chart(usage.set_index('Ontologia')['Ocorrências'])

        st.markdown(divider(), unsafe_allow_html=True)
        st.markdown('#### Visualização por grupo temático')
        theme_df = analyze_theme_groups(tdf)
        if theme_df.empty:
            st.info('Sem grupos temáticos calculados ainda.')
        else:
            st.dataframe(theme_df, use_container_width=True, hide_index=True)
            st.bar_chart(theme_df.set_index('Grupo')['Qtd Tags'])


# ═════════════════════════════════════════════════════════════════════
# ABA 6 — VALIDAÇÃO E AUDITORIA
# ═════════════════════════════════════════════════════════════════════
def tab_validation_audit():
    st.markdown("### Auditoria semântica, ortográfica e encadeamento de eventos")
    tdf = all_tags()
    udf = all_users()
    events_df = all_events()
    ontologies = load_ontologies()

    if not tdf.empty and 'status' not in tdf.columns:
        tdf['status'] = 'bruto'

    c1, c2, c3, c4 = st.columns(4)
    bruto = int((tdf['status'] == 'bruto').sum()) if not tdf.empty else 0
    sugerido = int((tdf['status'] == 'sugerido').sum()) if not tdf.empty else 0
    audit_events = int(events_df['event_type'].isin(['tag_group_audit', 'orthography_suggestion_logged']).sum()) if not events_df.empty else 0
    eventos = len(events_df) if not events_df.empty else 0
    with c1:
        st.markdown(kpi('Tags brutas', bruto, 'sem apagar o original', '#f87171'), unsafe_allow_html=True)
    with c2:
        st.markdown(kpi('Sugestões registradas', sugerido, 'camada sugestiva', '#fcd34d'), unsafe_allow_html=True)
    with c3:
        st.markdown(kpi('Auditorias semânticas', audit_events, 'comentários e separações', '#6ee7b7'), unsafe_allow_html=True)
    with c4:
        st.markdown(kpi('Eventos no ledger', eventos, 'rastreabilidade encadeada', '#a78bfa'), unsafe_allow_html=True)

    t1, t2, t3 = st.tabs([" Auditoria da separação", " Ortografia sem sobrescrever", " Blockchain documental"])

    with t1:
        if tdf.empty:
            st.info('Nenhuma tag disponível para auditoria.')
        else:
            rev = tdf.copy().sort_values('timestamp', ascending=False)
            rev['grupo_tematico'] = rev['tag'].apply(classify_tag_group)
            if 'ontologias' not in rev.columns:
                rev['ontologias'] = rev['tag'].apply(lambda x: match_ontologies_for_tag(x, ontologies))
            user_map = {}
            if not udf.empty and 'user_id' in udf.columns and 'q1' in udf.columns:
                user_map = udf.set_index('user_id')['q1'].to_dict()
            rev['familiaridade'] = rev['user_id'].map(user_map).fillna('Não informado') if user_map else 'Não informado'
            rev['ontologias_txt'] = rev['ontologias'].apply(lambda x: ', '.join(x) if isinstance(x, list) and x else '—')
            cols = [c for c in ['id','tag','grupo_tematico','ontologias_txt','familiaridade','obra_id','timestamp'] if c in rev.columns]
            st.dataframe(rev[cols].rename(columns={'ontologias_txt':'Ontologias'}), use_container_width=True, hide_index=True)

            cross = rev.groupby(['familiaridade','grupo_tematico']).size().reset_index(name='Qtd')
            if not cross.empty:
                st.markdown('#### Separação temática por familiaridade')
                pivot = cross.pivot(index='familiaridade', columns='grupo_tematico', values='Qtd').fillna(0)
                st.dataframe(pivot, use_container_width=True)

            ids = rev['id'].tolist()
            chosen = st.selectbox('Selecione o ID da tag para auditar', ids, key='audit_tag_id')
            current = rev[rev['id'] == chosen].iloc[0]
            grupos = list(THEME_GROUPS.keys()) + ['Outros']
            with st.form('form_auditoria_tag'):
                sugestao_grupo = st.selectbox('Grupo sugerido para auditoria', grupos, index=grupos.index(current.get('grupo_tematico', 'Outros')) if current.get('grupo_tematico', 'Outros') in grupos else len(grupos)-1)
                observacao = st.text_area('Comentário de auditoria', placeholder='Explique a separação, o vínculo semântico, a familiaridade do usuário e a justificativa documental.')
                ont_ref = st.multiselect('Ontologias relacionadas', [o.get('nome','Ontologia') for o in ontologies], default=current.get('ontologias', []) if isinstance(current.get('ontologias', []), list) else [])
                enviar = st.form_submit_button('Registrar auditoria sem alterar a tag original')
                if enviar:
                    payload = {
                        'tag_original_snapshot': current.to_dict(),
                        'grupo_atual': current.get('grupo_tematico', 'Outros'),
                        'grupo_sugerido': sugestao_grupo,
                        'comentario': observacao.strip(),
                        'familiaridade_usuario': current.get('familiaridade', 'Não informado'),
                        'ontologias_relacionadas': ont_ref,
                    }
                    register_event(
                        'tag_group_audit',
                        st.session_state.get('admin_username', 'admin'),
                        'admin',
                        'tag',
                        int(chosen),
                        payload,
                        origin='auditoria_semantica',
                        automatic=False,
                        status='revisado',
                        previous_state=current.to_dict(),
                        semantic_snapshot={
                            'grupo_sugerido': sugestao_grupo,
                            'ontologias_relacionadas': ont_ref,
                        },
                        provenance_source='auditoria_semantica_manual',
                    )
                    st.success('Auditoria registrada. A tag original permanece intacta.')
                    st.rerun()

    with t2:
        if tdf.empty:
            st.info('Sem tags para analisar.')
        else:
            suggestions = build_spell_suggestions(tdf, ontologies)
            if suggestions.empty:
                st.success('Nenhum possível erro ortográfico encontrado com as regras atuais.')
            else:
                st.dataframe(suggestions, use_container_width=True, hide_index=True)
                tag_map = {r['tag']: r for _, r in suggestions.iterrows()}
                escolha = st.selectbox('Selecione uma tag para registrar sugestão', list(tag_map.keys()), key='spell_tag_choice')
                sug = tag_map[escolha]
                with st.form('form_spell_audit'):
                    comentario = st.text_area('Comentário sobre a sugestão ortográfica', value=f"Sugestão registrada: '{sug['tag']}' -> '{sug['sugestao']}'.")
                    registrar = st.form_submit_button('Registrar sugestão sem sobrescrever a tag')
                    if registrar:
                        target = tdf[tdf['tag'] == escolha].sort_values('id')
                        if not target.empty:
                            row = target.iloc[0].to_dict()
                            register_event(
                                'orthography_suggestion_logged',
                                st.session_state.get('admin_username', 'admin'),
                                'admin',
                                'tag',
                                int(row['id']),
                                {
                                    'tag_original_snapshot': row,
                                    'sugestao_ortografica': str(sug['sugestao']),
                                    'distancia': int(sug['distancia']),
                                    'comentario': comentario.strip(),
                                },
                                origin='auditoria_ortografica',
                                automatic=False,
                                status='sugerido',
                                previous_state=row,
                                semantic_snapshot={'grupo_tematico': row.get('grupo_tematico', classify_tag_group(row.get('tag', '')))},
                                provenance_source='auditoria_ortografica_manual',
                            )
                            st.success('Sugestão registrada na trilha de auditoria sem alterar o dado original.')
                            st.rerun()

    with t3:
        st.markdown('#### Blockchain documental: registro encadeado, proveniência e interoperabilidade')
        if events_df.empty:
            st.info('Nenhum evento foi registrado ainda.')
        else:
            preview = normalize_events_dataframe(events_df).copy().sort_values('ledger_no', ascending=False)
            preview['Registro'] = [ledger_label(v, i + 1) for i, v in enumerate(preview['ledger_no'].tolist())]
            preview['Hash Atual'] = preview['event_hash'].astype(str).str[:16] + '…'
            preview['Hash Anterior'] = preview['previous_hash'].astype(str).str[:16] + '…'
            preview['Hash Entidade'] = preview['entity_previous_hash'].astype(str).str[:16] + '…'
            preview['Entidade'] = preview['entity_type'].astype(str) + ' #' + preview['entity_id'].astype(str)
            preview['Refs externas'] = preview['interoperability_refs'].apply(lambda x: ', '.join(x) if isinstance(x, list) and x else '—')
            cols = [c for c in ['Registro','timestamp','event_type','actor','Entidade','entity_version','status','Hash Atual','Hash Anterior','Hash Entidade','origin','Refs externas'] if c in preview.columns]
            st.dataframe(preview[cols], use_container_width=True, hide_index=True)

            st.markdown(divider(), unsafe_allow_html=True)
            st.markdown('#### Blockchain documental de interoperabilidade')
            st.markdown(insight(
                '<strong>1.</strong> cada alteração em tags, obras, metadados ou sincronizações externas gera um evento numerado; '
                '<strong>2.</strong> cada evento recebe hash próprio e preserva o hash global anterior; '
                '<strong>3.</strong> cada revisão mantém referência ao hash global anterior e ao hash anterior da própria entidade, formando uma cadeia verificável por registro e por entidade; '
                '<strong>4.</strong> a correção humana registra previous_state sem apagar o histórico e sem destruir o dado bruto original; '
                '<strong>5.</strong> cada exportação ou sincronização com Wikidata, Europeana e Portal de Dados Abertos registra trilha de circulação, proveniência, confiança e interoperabilidade.'
            ), unsafe_allow_html=True)

            top_events = preview.head(12)
            for _, row in top_events.iterrows():
                refs = row.get('interoperability_refs', [])
                refs_txt = ', '.join(refs) if isinstance(refs, list) and refs else '—'
                trace = row.get('circulation_trace') or {}
                trace_txt = trace.get('acao', '—') if isinstance(trace, dict) else '—'
                payload = row.get('payload') or {}
                payload_txt = json.dumps(payload, ensure_ascii=False, default=str)[:600]
                st.markdown(
                    f"<div class='sc sc-p'>"
                    f"<strong>{row.get('Registro','—')}</strong> · {row.get('timestamp','—')}<br>"
                    f"Evento: <strong>{row.get('event_type','—')}</strong> · Entidade: <strong>{row.get('entity_type','—')} #{row.get('entity_id','—')}</strong> · Versão: <strong>{row.get('entity_version','—')}</strong><br>"
                    f"Hash atual: <code>{row.get('event_hash','—')}</code><br>"
                    f"Hash global anterior: <code>{row.get('previous_hash','—')}</code><br>"
                    f"Hash anterior da entidade: <code>{row.get('entity_previous_hash','—')}</code><br>"
                    f"Origem: <strong>{row.get('origin','—')}</strong> · Proveniência: <strong>{row.get('provenance_source','—')}</strong><br>"
                    f"Circulação: <strong>{trace_txt}</strong> · Interoperabilidade: <strong>{refs_txt}</strong><br>"
                    f"Snapshot semântico/payload: <code>{payload_txt}</code>"
                    f"</div>", unsafe_allow_html=True
                )


# ═════════════════════════════════════════════════════════════════════
# ABA 7 — GRAFO E OPEN DATA
# ═════════════════════════════════════════════════════════════════════
def tab_graph_open_data():
    st.markdown("### Grafo 3D, open data e interoperabilidade analítica")
    tdf = all_tags()
    meta = load_institution_metadata()
    events_df = all_events()
    open_sources = load_open_data_sources()
    mappings = load_interoperability_registry()
    obras = load_obras()

    t1, t2, t3 = st.tabs([" Grafo 3D conectado", " Motor automático de interoperabilidade", " Circulação e metadados"])

    with t1:
        if tdf.empty:
            st.info('Ainda não há tags suficientes para o grafo.')
        else:
            thr = st.slider('Limiar semântico do grafo', 0.20, 0.90, 0.35, 0.05, key='graph_thr')
            nodes, edges = build_interoperability_graph_data(tdf, open_sources=open_sources, mappings=mappings, threshold=thr)
            build_graph_3d_component(nodes, edges, height=620)
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.markdown(kpi('Nós no grafo', len(nodes), 'tags + entidades + fontes', '#a7e6ff'), unsafe_allow_html=True)
            with c2:
                st.markdown(kpi('Arestas', len(edges), 'ligações locais e externas', '#6ee7b7'), unsafe_allow_html=True)
            with c3:
                st.markdown(kpi('Fontes externas', len(open_sources), 'registradas', '#fcd34d'), unsafe_allow_html=True)
            with c4:
                st.markdown(kpi('Conexões automáticas', len(mappings), 'interoperabilidade persistida', '#d1baff'), unsafe_allow_html=True)
            st.markdown(insight(
                '<strong>Leitura do grafo:</strong> termos locais, artistas, obras e metadados institucionais são reconciliados com entidades e catálogos externos. Cada aresta pode ser rastreada no ledger documental como evento de interoperabilidade, preservando proveniência, confiança, versão e origem da consulta.'
            ), unsafe_allow_html=True)

    with t2:
        st.markdown('#### Mapeamentos automáticos de interoperabilidade')
        st.markdown(insight(
            '<strong>Como funciona:</strong> o sistema não pede que você crie uma conexão manual por item. Ele coleta as tags mais frequentes, títulos, autores e metadados institucionais; depois consulta automaticamente Wikidata, Europeana e o Portal Brasileiro de Dados Abertos para propor correspondências externas e registrar tudo no ledger.'
        ), unsafe_allow_html=True)

        c1, c2 = st.columns([1, 2])
        with c1:
            st.markdown('##### Fontes ativas')
            src_df = pd.DataFrame(normalize_open_data_sources(open_sources))
            st.dataframe(
                safe_dataframe_view(src_df, ['nome', 'tipo', 'autenticacao', 'endpoint', 'status']),
                use_container_width=True,
                hide_index=True,
            )
            if st.button('Atualizar mapeamentos automáticos', use_container_width=True):
                actor = st.session_state.get('admin_username', 'admin')
                matches_df, status_df = persist_auto_interoperability(tdf, obras, meta, actor=actor)
                st.session_state['auto_interop_status_df'] = status_df
                st.session_state['auto_interop_matches_df'] = matches_df
                st.success('Motor de interoperabilidade executado e ledger atualizado.')
                st.rerun()
        with c2:
            st.markdown('##### Metadados institucionais conectados')
            meta_view = pd.DataFrame([
                {'Campo': 'Instituição', 'Valor': meta.get('instituicao', '—')},
                {'Campo': 'Coleção', 'Valor': meta.get('colecao', '—')},
                {'Campo': 'Licença de dados', 'Valor': meta.get('licenca_dados', '—')},
                {'Campo': 'Responsável', 'Valor': meta.get('responsavel', '—')},
                {'Campo': 'Descrição', 'Valor': meta.get('descricao', '—')},
            ])
            st.dataframe(meta_view, use_container_width=True, hide_index=True)

        status_df = st.session_state.get('auto_interop_status_df')
        matches_df = st.session_state.get('auto_interop_matches_df')
        if status_df is None or not isinstance(status_df, pd.DataFrame):
            _, status_df = auto_generate_interoperability_mappings(tdf, obras, meta)
        if matches_df is None or not isinstance(matches_df, pd.DataFrame):
            matches_df = pd.DataFrame(mappings) if mappings else pd.DataFrame()

        st.markdown(divider(), unsafe_allow_html=True)
        st.markdown('##### Estado das buscas externas')
        if isinstance(status_df, pd.DataFrame) and not status_df.empty:
            st.dataframe(status_df, use_container_width=True, hide_index=True)

        st.markdown('##### Conexões encontradas')
        interop_df = summarize_interoperability(open_sources, mappings)
        if interop_df.empty and isinstance(matches_df, pd.DataFrame) and not matches_df.empty:
            interop_df = summarize_interoperability(open_sources, matches_df.to_dict(orient='records'))
        if not interop_df.empty:
            st.dataframe(interop_df, use_container_width=True, hide_index=True)
            grp = interop_df.groupby('Fonte externa').size()
            if not grp.empty:
                st.bar_chart(grp)
        else:
            st.info('Ainda não há conexões externas persistidas. Execute o motor automático.')

    with t3:
        st.markdown('#### Registro consolidado de circulação, proveniência e interoperabilidade')
        st.json(meta)
        st.download_button(
            'Baixar metadados institucionais (JSON)',
            json.dumps(meta, ensure_ascii=False, indent=2).encode('utf-8'),
            'metadados_institucionais.json',
            'application/json',
            use_container_width=True
        )
        if events_df.empty:
            st.info('Sem eventos registrados ainda.')
        else:
            circ = events_df.copy().sort_values('ledger_no', ascending=False)
            circ = circ[circ['event_type'].isin([
                'obra_created','obra_deleted','tag_created','tag_group_audit','orthography_suggestion_logged',
                'ontology_created','institution_metadata_update','interoperability_sync','data_export'
            ])]
            cols = [c for c in ['ledger_no','timestamp','event_type','actor','entity_type','entity_id','entity_version','status','circulation_action','origin','event_hash'] if c in circ.columns]
            st.dataframe(circ[cols], use_container_width=True, hide_index=True)
            st.markdown(insight(
                '<strong>Trilha de circulação:</strong> exportações, auditorias, atualizações institucionais e sincronizações automáticas com open data permanecem encadeadas no mesmo ledger, permitindo rastrear versões, proveniência, circulação e interoperabilidade do arquivo semântico.'
            ), unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════════════════
# ABA 5 — GESTÃO DE OBRAS# ═════════════════════════════════════════════════════════════════════
# ABA 5 — GESTÃO DE OBRAS
# ═════════════════════════════════════════════════════════════════════
def tab_obras():
    st.markdown("### Gestão de Obras")
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
                with c3:
                    if st.button("🗑️ Remover", key=f"del_{obra['id']}"):
                        previous = dict(obra)
                        obras.remove(obra)
                        save_json_file(OBRAS_FILE, obras)
                        register_event('obra_deleted', st.session_state.get('admin_username','admin'), 'admin', 'obra', previous.get('id'), {'obra_removida': previous}, origin='gestao_obras', automatic=False, status=previous.get('metadado_status','revisado'))
                        st.success("Obra removida!")
                        st.cache_data.clear()
                        st.rerun()
                st.divider()
        else:
            st.info("Nenhuma obra cadastrada.")

    with t2:
        with st.form("add_obra"):
            titulo  = st.text_input("Título da Obra")
            artista = st.text_input("Artista")
            ano     = st.text_input("Ano")
            imagem  = st.text_input("URL da Imagem")
            audio_descricao = st.text_area("Audiodescrição detalhada", placeholder="Descreva a composição, cores, enquadramento, figuras e atmosfera da obra...")
            status_meta = st.selectbox("Status do metadado", STATUS_OPTIONS, index=0)
            if st.form_submit_button(" Adicionar Obra"):
                if titulo and artista and ano and imagem:
                    nid = max([o['id'] for o in obras])+1 if obras else 1
                    novo = {"id":nid,"titulo":titulo,"artista":artista,"ano":ano,"imagem":imagem,"audio_descricao": audio_descricao.strip() or f'Audiodescrição de {titulo} por {artista}.', "metadado_status": status_meta}
                    obras.append(novo)
                    save_json_file(OBRAS_FILE, obras)
                    register_event('obra_created', st.session_state.get('admin_username','admin'), 'admin', 'obra', nid, novo, origin='gestao_obras', automatic=False, status=status_meta)
                    st.success("Obra adicionada!")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("Preencha todos os campos!")

# ═════════════════════════════════════════════════════════════════════
# ABA 6 — EXPORTAR
# ═════════════════════════════════════════════════════════════════════
def tab_export():
    st.markdown("### Central de Exportação")
    tdf  = all_tags()
    udf  = all_users()
    obs  = load_obras()

    t1, t2 = st.tabs([" Exportação Geral"," Por Participante"])

    with t1:
        c1,c2,c3 = st.columns(3)
        with c1:
            st.markdown("#### Tags")
            if not tdf.empty:
                clicked = st.download_button(" Todas as Tags (CSV)",
                    tdf.to_csv(index=False).encode('utf-8'),
                    f"tags_{datetime.now().strftime('%Y%m%d')}.csv","text/csv",
                    use_container_width=True)
                if clicked:
                    register_event('data_export', st.session_state.get('admin_username','admin'), 'admin', 'dataset', 'tags_csv', {'linhas': len(tdf)}, origin='exportacao', automatic=False, status='publicado', circulation_action='download_tags_csv')
                freq = tdf['tag'].value_counts().reset_index()
                freq.columns=['Tag','Frequência']
                freq['%']=(freq['Frequência']/freq['Frequência'].sum()*100).round(2)
                clicked = st.download_button(" Frequências (CSV)",
                    freq.to_csv(index=False).encode('utf-8'),
                    f"freq_{datetime.now().strftime('%Y%m%d')}.csv","text/csv",
                    use_container_width=True)
                if clicked:
                    register_event('data_export', st.session_state.get('admin_username','admin'), 'admin', 'dataset', 'frequencias_csv', {'linhas': len(freq)}, origin='exportacao', automatic=False, status='publicado', circulation_action='download_freq_csv')
        with c2:
            st.markdown("#### Usuários")
            if not udf.empty:
                clicked = st.download_button(" Usuários (CSV)",
                    udf.to_csv(index=False).encode('utf-8'),
                    f"usuarios_{datetime.now().strftime('%Y%m%d')}.csv","text/csv",
                    use_container_width=True)
                if clicked:
                    register_event('data_export', st.session_state.get('admin_username','admin'), 'admin', 'dataset', 'usuarios_csv', {'linhas': len(udf)}, origin='exportacao', automatic=False, status='publicado', circulation_action='download_usuarios_csv')
        with c3:
            st.markdown("#### Obras")
            if obs:
                clicked = st.download_button(" Obras (CSV)",
                    pd.DataFrame(obs).to_csv(index=False).encode('utf-8'),
                    f"obras_{datetime.now().strftime('%Y%m%d')}.csv","text/csv",
                    use_container_width=True)
                if clicked:
                    register_event('data_export', st.session_state.get('admin_username','admin'), 'admin', 'dataset', 'obras_csv', {'linhas': len(obs)}, origin='exportacao', automatic=False, status='publicado', circulation_action='download_obras_csv')

        st.markdown(divider(), unsafe_allow_html=True)
        st.markdown("#### Exportar Conexões de Tags")
        if not tdf.empty:
            thr = st.slider("Limiar de similaridade:", 0.2, 0.9, 0.35, 0.05, key="exp_thr")
            if st.button("Gerar arquivo de conexões"):
                with st.spinner("Calculando…"):
                    conns = tag_connections(tdf['tag'].tolist(), threshold=thr)
                if conns:
                    cdf = pd.DataFrame(conns)
                    clicked = st.download_button(" Conexões (CSV)",
                        cdf.to_csv(index=False).encode('utf-8'),
                        f"conexoes_{datetime.now().strftime('%Y%m%d')}.csv","text/csv",
                        use_container_width=True)
                    if clicked:
                        register_event('data_export', st.session_state.get('admin_username','admin'), 'admin', 'dataset', 'conexoes_csv', {'linhas': len(cdf)}, origin='exportacao', automatic=False, status='publicado', circulation_action='download_conexoes_csv')
                    st.success(f"{len(conns)} conexões exportadas.")
                else:
                    st.info("Nenhuma conexão encontrada com este limiar.")

    with t2:
        if udf.empty:
            st.info("Nenhum participante cadastrado.")
            return
        uopts = [f"🐾 {r.get('animal_name',r['user_id'][:8])}" for _,r in udf.iterrows()]
        usel  = st.selectbox("Selecione um participante:", uopts, key="exp_u")
        uidx  = uopts.index(usel)
        uid   = udf.iloc[uidx]['user_id']
        uanim = udf.iloc[uidx].get('animal_name', uid[:8])

        st.markdown(f"#### Dados de: **{uanim}**")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("##### Questionário")
            hq = html_quest(uid, uanim, udf)
            if hq:
                clicked = st.download_button(" Respostas (HTML/PDF)", hq,
                    f"quest_{uid[:8]}.html","text/html", use_container_width=True)
                if clicked:
                    register_event('data_export', st.session_state.get('admin_username','admin'), 'admin', 'dataset', f'quest_{uid[:8]}', {'usuario': uid}, origin='exportacao', automatic=False, status='publicado', circulation_action='download_questionario_html')
            ud = udf[udf['user_id']==uid]
            if not ud.empty:
                clicked = st.download_button(" Respostas (CSV)",
                    ud.to_csv(index=False).encode('utf-8'),
                    f"quest_{uid[:8]}.csv","text/csv", use_container_width=True)
                if clicked:
                    register_event('data_export', st.session_state.get('admin_username','admin'), 'admin', 'dataset', f'quest_csv_{uid[:8]}', {'usuario': uid}, origin='exportacao', automatic=False, status='publicado', circulation_action='download_questionario_csv')
        with c2:
            st.markdown("##### Tags Criadas")
            ht = html_tags(uid, uanim, obs, tdf)
            if ht:
                clicked = st.download_button(" Tags (HTML/PDF)", ht,
                    f"tags_{uid[:8]}.html","text/html", use_container_width=True)
                if clicked:
                    register_event('data_export', st.session_state.get('admin_username','admin'), 'admin', 'dataset', f'tags_html_{uid[:8]}', {'usuario': uid}, origin='exportacao', automatic=False, status='publicado', circulation_action='download_tags_html')
            ut = get_user_tags(uid)
            if not ut.empty:
                clicked = st.download_button(" Tags (CSV)",
                    ut.to_csv(index=False).encode('utf-8'),
                    f"tags_{uid[:8]}.csv","text/csv", use_container_width=True)
                if clicked:
                    register_event('data_export', st.session_state.get('admin_username','admin'), 'admin', 'dataset', f'tags_csv_{uid[:8]}', {'usuario': uid}, origin='exportacao', automatic=False, status='publicado', circulation_action='download_tags_csv_usuario')

if __name__ == "__main__":
    main()
