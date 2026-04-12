
import streamlit as st
import pandas as pd
import numpy as np
import os
import re
import json
import random
import hashlib
import base64
import unicodedata
from datetime import datetime
from collections import defaultdict, Counter
from itertools import combinations

warnings_filter = __import__("warnings")
warnings_filter.filterwarnings("ignore")

st.set_page_config(
    page_title="Sistema Folksonomia Digital Semântico",
    layout="wide",
    initial_sidebar_state="collapsed",
    page_icon="🧠"
)

# ──────────────────────────────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────────────────────────────
DATA_DIR = "data"
OBRAS_FILE = os.path.join(DATA_DIR, "obras.json")
TAGS_FILE = os.path.join(DATA_DIR, "tags.json")
USERS_FILE = os.path.join(DATA_DIR, "users.json")
ADMIN_FILE = os.path.join(DATA_DIR, "admin.json")
CONCEPTS_FILE = os.path.join(DATA_DIR, "concepts.json")
VALIDATIONS_FILE = os.path.join(DATA_DIR, "validations.json")

ADMIN_USERNAME = "nugep"
ADMIN_PASSWORD = "nugep123"

STOPWORDS_PT = {
    "a","o","e","de","da","do","das","dos","em","na","no","nas","nos","um","uma",
    "uns","umas","para","por","com","sem","sobre","sob","ao","aos","à","às","que",
    "se","como","mais","menos","muito","muita","muitos","muitas","ser","estar",
    "foi","são","é","ou","pela","pelo","pelas","pelos","lhe","me","te","seu",
    "sua","seus","suas","este","esta","esses","essas","isso","isto","aquele",
    "aquela","aqueles","aquelas","deu","tem","têm","já","ainda"
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


# ──────────────────────────────────────────────────────────────────────
# UTILS
# ──────────────────────────────────────────────────────────────────────
def ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def load_json_file(filepath, default):
    ensure_data_dir()
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    return default


def save_json_file(filepath, data):
    ensure_data_dir()
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return True


def gen_uid():
    return base64.b64encode(os.urandom(12)).decode("ascii")


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def generate_animal_name():
    random.seed()
    return f"{random.choice(ANIMAIS)} {random.choice(ADJETIVOS)}"


def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def strip_accents(text):
    if text is None:
        return ""
    text = str(text)
    return "".join(
        c for c in unicodedata.normalize("NFKD", text)
        if not unicodedata.combining(c)
    )


def normalize_text(text):
    text = strip_accents(text).lower().strip()
    text = re.sub(r"[^a-z0-9\s\-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def tokenize(text):
    norm = normalize_text(text)
    tokens = [t for t in norm.split() if t and t not in STOPWORDS_PT]
    return tokens


def safe_list(x):
    return x if isinstance(x, list) else []


def join_unique(values):
    out = []
    seen = set()
    for v in values:
        if v and v not in seen:
            seen.add(v)
            out.append(v)
    return out


def levenshtein_ratio_simple(a, b):
    a = normalize_text(a)
    b = normalize_text(b)
    if not a and not b:
        return 1.0
    if a == b:
        return 1.0
    if not a or not b:
        return 0.0
    m, n = len(a), len(b)
    dp = list(range(n + 1))
    for i in range(1, m + 1):
        prev = dp[0]
        dp[0] = i
        for j in range(1, n + 1):
            temp = dp[j]
            cost = 0 if a[i - 1] == b[j - 1] else 1
            dp[j] = min(dp[j] + 1, dp[j - 1] + 1, prev + cost)
            prev = temp
    dist = dp[n]
    return 1 - dist / max(m, n)


def jaccard_words(a, b):
    sa = set(tokenize(a))
    sb = set(tokenize(b))
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def ngrams(text, n=3):
    text = normalize_text(text)
    if len(text) < n:
        return {text} if text else set()
    return {text[i:i+n] for i in range(len(text) - n + 1)}


def trigram_similarity(a, b):
    na = ngrams(a, 3)
    nb = ngrams(b, 3)
    if not na and not nb:
        return 1.0
    if not na or not nb:
        return 0.0
    return len(na & nb) / len(na | nb)


def combined_similarity(a, b):
    na = normalize_text(a)
    nb = normalize_text(b)
    if na == nb:
        return 1.0
    contain = 0.85 if na and nb and (na in nb or nb in na) else 0.0
    return max(
        contain,
        round(0.45 * jaccard_words(a, b) + 0.35 * trigram_similarity(a, b) + 0.20 * levenshtein_ratio_simple(a, b), 4)
    )


# ──────────────────────────────────────────────────────────────────────
# DEFAULT DATA
# ──────────────────────────────────────────────────────────────────────
def default_obras():
    return [
        {
            "id": 1,
            "titulo": "Guernica",
            "artista": "Pablo Picasso",
            "ano": "1937",
            "imagem": "https://upload.wikimedia.org/wikipedia/en/7/74/PicassoGuernica.jpg",
            "descricao": "Pintura monumental em preto, branco e cinza que aborda guerra, dor, violência, sofrimento, fragmentação e desespero.",
            "temas": ["guerra", "violência", "sofrimento", "memória", "dor"],
            "materiais": ["óleo", "tela"],
            "tecnicas": ["pintura"],
            "periodo": "século XX"
        },
        {
            "id": 2,
            "titulo": "A Noite Estrelada",
            "artista": "Vincent van Gogh",
            "ano": "1889",
            "imagem": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ea/Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg/1200px-Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg",
            "descricao": "Paisagem noturna com céu estrelado, lua, vila e ciprestes. Destacam-se movimento, azul intenso, amarelo luminoso, emoção e atmosfera.",
            "temas": ["paisagem", "noite", "céu", "emoção", "natureza"],
            "materiais": ["óleo", "tela"],
            "tecnicas": ["pintura"],
            "periodo": "século XIX"
        },
        {
            "id": 3,
            "titulo": "Mona Lisa",
            "artista": "Leonardo da Vinci",
            "ano": "1503",
            "imagem": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ec/Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_retouched.jpg/800px-Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_retouched.jpg",
            "descricao": "Retrato feminino com fundo de paisagem, sorriso enigmático, composição equilibrada e grande atenção à expressão e à técnica.",
            "temas": ["retrato", "mulher", "expressão", "renascimento"],
            "materiais": ["óleo", "madeira"],
            "tecnicas": ["pintura"],
            "periodo": "século XVI"
        }
    ]


def default_concepts():
    return [
        {"id": "tema_guerra", "label": "guerra", "aliases": ["conflito", "violência bélica", "violencia", "combate"], "category": "tema", "uri": "https://www.wikidata.org/wiki/Q198"},
        {"id": "tema_sofrimento", "label": "sofrimento", "aliases": ["dor", "agonia", "tristeza", "desespero"], "category": "tema", "uri": "https://www.wikidata.org/wiki/Q177058"},
        {"id": "tema_paisagem", "label": "paisagem", "aliases": ["campo", "vista", "cenário", "cenario"], "category": "tema", "uri": "https://www.wikidata.org/wiki/Q191163"},
        {"id": "tema_ceu", "label": "céu", "aliases": ["ceu", "firmamento"], "category": "tema", "uri": "https://www.wikidata.org/wiki/Q527"},
        {"id": "tema_noite", "label": "noite", "aliases": ["noturno", "escuro"], "category": "tema", "uri": "https://www.wikidata.org/wiki/Q575"},
        {"id": "tema_retrato", "label": "retrato", "aliases": ["rosto", "figura humana", "face"], "category": "tema", "uri": "https://www.wikidata.org/wiki/Q192110"},
        {"id": "tema_mulher", "label": "mulher", "aliases": ["feminino", "senhora", "garota"], "category": "tema", "uri": "https://www.wikidata.org/wiki/Q467"},
        {"id": "tema_memoria", "label": "memória", "aliases": ["memoria", "lembrança", "recordação"], "category": "tema", "uri": "https://www.wikidata.org/wiki/Q857698"},
        {"id": "tema_natureza", "label": "natureza", "aliases": ["natural", "paisagem natural"], "category": "tema", "uri": "https://www.wikidata.org/wiki/Q7860"},
        {"id": "cor_azul", "label": "azul", "aliases": ["azulado"], "category": "cor", "uri": "https://www.wikidata.org/wiki/Q1088"},
        {"id": "cor_amarelo", "label": "amarelo", "aliases": ["dourado"], "category": "cor", "uri": "https://www.wikidata.org/wiki/Q2720565"},
        {"id": "cor_branco", "label": "branco", "aliases": ["claro"], "category": "cor", "uri": "https://www.wikidata.org/wiki/Q23444"},
        {"id": "cor_preto", "label": "preto", "aliases": ["escuro"], "category": "cor", "uri": "https://www.wikidata.org/wiki/Q23445"},
        {"id": "mat_oleo", "label": "óleo", "aliases": ["oleo", "óleo sobre tela"], "category": "material", "uri": "https://www.wikidata.org/wiki/Q296955"},
        {"id": "mat_tela", "label": "tela", "aliases": ["canvas"], "category": "material", "uri": "https://www.wikidata.org/wiki/Q4259259"},
        {"id": "mat_madeira", "label": "madeira", "aliases": ["painel de madeira"], "category": "material", "uri": "https://www.wikidata.org/wiki/Q287"},
        {"id": "tec_pintura", "label": "pintura", "aliases": ["quadro", "pintado"], "category": "técnica", "uri": "https://www.wikidata.org/wiki/Q3305213"},
        {"id": "per_seculo_xvi", "label": "século XVI", "aliases": ["seculo xvi", "renascimento"], "category": "período", "uri": "https://www.wikidata.org/wiki/Q1477"},
        {"id": "per_seculo_xix", "label": "século XIX", "aliases": ["sec xix", "pos impressionismo", "pós-impressionismo"], "category": "período", "uri": "https://www.wikidata.org/wiki/Q695269"},
        {"id": "per_seculo_xx", "label": "século XX", "aliases": ["sec x", "moderno", "modernidade"], "category": "período", "uri": "https://www.wikidata.org/wiki/Q6927"},
        {"id": "emo_tristeza", "label": "tristeza", "aliases": ["melancolia", "depressivo", "angústia", "angustia"], "category": "emoção", "uri": "https://www.wikidata.org/wiki/Q491"},
        {"id": "emo_esperanca", "label": "esperança", "aliases": ["esperanca", "otimismo"], "category": "emoção", "uri": "https://www.wikidata.org/wiki/Q18524218"},
        {"id": "emo_misterio", "label": "mistério", "aliases": ["misterio", "enigmático", "enigmatico"], "category": "emoção", "uri": "https://www.wikidata.org/wiki/Q244157"},
        {"id": "tema_estrela", "label": "estrela", "aliases": ["estrelado", "estrelas"], "category": "tema", "uri": "https://www.wikidata.org/wiki/Q523"},
        {"id": "tema_lua", "label": "lua", "aliases": ["luar"], "category": "tema", "uri": "https://www.wikidata.org/wiki/Q405"},
        {"id": "tema_violencia", "label": "violência", "aliases": ["violencia", "agressão", "agressao"], "category": "tema", "uri": "https://www.wikidata.org/wiki/Q1520311"}
    ]


# ──────────────────────────────────────────────────────────────────────
# INITIALIZATION
# ──────────────────────────────────────────────────────────────────────
def check_admin():
    admins = load_json_file(ADMIN_FILE, [])
    if not admins:
        save_json_file(ADMIN_FILE, [{"id": 1, "username": ADMIN_USERNAME, "password": hash_password(ADMIN_PASSWORD)}])


def init_data():
    ensure_data_dir()
    if not os.path.exists(OBRAS_FILE):
        save_json_file(OBRAS_FILE, default_obras())
    if not os.path.exists(CONCEPTS_FILE):
        save_json_file(CONCEPTS_FILE, default_concepts())
    if not os.path.exists(TAGS_FILE):
        save_json_file(TAGS_FILE, [])
    if not os.path.exists(USERS_FILE):
        save_json_file(USERS_FILE, [])
    if not os.path.exists(VALIDATIONS_FILE):
        save_json_file(VALIDATIONS_FILE, [])
    check_admin()


@st.cache_data(ttl=5, show_spinner=False)
def load_obras():
    obras = load_json_file(OBRAS_FILE, default_obras())
    if not obras:
        obras = default_obras()
        save_json_file(OBRAS_FILE, obras)
    return obras


@st.cache_data(ttl=5, show_spinner=False)
def load_concepts():
    concepts = load_json_file(CONCEPTS_FILE, default_concepts())
    if not concepts:
        concepts = default_concepts()
        save_json_file(CONCEPTS_FILE, concepts)
    return concepts


def load_tags_df():
    tags = load_json_file(TAGS_FILE, [])
    return pd.DataFrame(tags) if tags else pd.DataFrame()


def load_users_df():
    users = load_json_file(USERS_FILE, [])
    return pd.DataFrame(users) if users else pd.DataFrame()


def load_validations_df():
    vals = load_json_file(VALIDATIONS_FILE, [])
    return pd.DataFrame(vals) if vals else pd.DataFrame()


# ──────────────────────────────────────────────────────────────────────
# CONCEPT / SEMANTIC ENGINE
# ──────────────────────────────────────────────────────────────────────
def concept_index():
    concepts = load_concepts()
    idx = []
    for c in concepts:
        aliases = join_unique([c.get("label", "")] + safe_list(c.get("aliases", [])))
        idx.append({
            "id": c["id"],
            "label": c["label"],
            "label_norm": normalize_text(c["label"]),
            "aliases": aliases,
            "aliases_norm": [normalize_text(a) for a in aliases],
            "category": c.get("category", "tema"),
            "uri": c.get("uri", "")
        })
    return idx


def find_best_concepts(tag_text, top_n=5):
    candidates = []
    for c in concept_index():
        best_score = 0.0
        best_alias = ""
        for alias in c["aliases"]:
            score = combined_similarity(tag_text, alias)
            if score > best_score:
                best_score = score
                best_alias = alias
        if best_score >= 0.30:
            candidates.append({
                "concept_id": c["id"],
                "label": c["label"],
                "category": c["category"],
                "score": round(best_score, 4),
                "matched_alias": best_alias,
                "uri": c.get("uri", "")
            })
    candidates.sort(key=lambda x: x["score"], reverse=True)
    return candidates[:top_n]


def extract_entities_from_obra(obra):
    entities = []
    if not obra:
        return entities
    if obra.get("artista"):
        entities.append({"type": "artista", "value": obra["artista"]})
    if obra.get("titulo"):
        entities.append({"type": "obra", "value": obra["titulo"]})
    if obra.get("ano"):
        entities.append({"type": "ano", "value": obra["ano"]})
    for t in safe_list(obra.get("temas")):
        entities.append({"type": "tema_institucional", "value": t})
    for m in safe_list(obra.get("materiais")):
        entities.append({"type": "material_institucional", "value": m})
    for tec in safe_list(obra.get("tecnicas")):
        entities.append({"type": "tecnica_institucional", "value": tec})
    if obra.get("periodo"):
        entities.append({"type": "periodo_institucional", "value": obra["periodo"]})
    return entities


def out_of_description(tag_text, obra):
    if not obra:
        return False
    desc = " ".join([
        obra.get("descricao", ""),
        " ".join(safe_list(obra.get("temas"))),
        " ".join(safe_list(obra.get("materiais"))),
        " ".join(safe_list(obra.get("tecnicas"))),
        obra.get("periodo", ""),
        obra.get("titulo", ""),
        obra.get("artista", "")
    ])
    desc_tokens = set(tokenize(desc))
    tag_tokens = set(tokenize(tag_text))
    if not tag_tokens:
        return False
    return len(tag_tokens & desc_tokens) == 0


def analyze_tag_semantics(tag_text, obra=None):
    tag_norm = normalize_text(tag_text)
    suggestions = find_best_concepts(tag_text, top_n=5)
    best = suggestions[0] if suggestions else None

    matched = []
    categories = []
    confidence = 0.0
    status = "novo_termo"
    if best:
        confidence = best["score"]
        matched = [best["concept_id"]]
        categories = [best["category"]]
        if confidence >= 0.86:
            status = "reconciliado"
        elif confidence >= 0.55:
            status = "sugerido"
        else:
            status = "novo_termo"

    entities = extract_entities_from_obra(obra)
    tag_tokens = tokenize(tag_text)
    desc_out = out_of_description(tag_text, obra)

    return {
        "normalized_tag": tag_norm,
        "tokens": tag_tokens,
        "status": status,
        "confidence": round(confidence, 4),
        "matched_concept_ids": matched,
        "categories": categories,
        "suggestions": suggestions,
        "entities_context": entities,
        "out_of_description": desc_out
    }


def suggest_tags_for_obra(obra, current_tags_df=None):
    suggestions = []
    if not obra:
        return suggestions

    for source in [
        safe_list(obra.get("temas")),
        safe_list(obra.get("materiais")),
        safe_list(obra.get("tecnicas")),
        [obra.get("periodo", "")],
        tokenize(obra.get("descricao", ""))
    ]:
        for item in source:
            txt = str(item).strip()
            if txt and normalize_text(txt) not in {normalize_text(x) for x in suggestions}:
                suggestions.append(txt)

    concept_hits = []
    for s in suggestions[:20]:
        for c in find_best_concepts(s, top_n=1):
            concept_hits.append(c["label"])

    suggestions = join_unique(suggestions + concept_hits)

    if current_tags_df is not None and not current_tags_df.empty:
        top_obra = current_tags_df[current_tags_df["obra_id"] == obra["id"]]["tag"].value_counts().head(5).index.tolist()
        suggestions = join_unique(suggestions + top_obra)

    return [s for s in suggestions if len(normalize_text(s)) >= 3][:12]


def enqueue_validation(tag_record):
    validations = load_json_file(VALIDATIONS_FILE, [])
    existing = [v for v in validations if v.get("tag_id") == tag_record["id"]]
    if existing:
        return
    validations.append({
        "id": len(validations) + 1,
        "tag_id": tag_record["id"],
        "tag": tag_record["tag"],
        "normalized_tag": tag_record.get("normalized_tag", ""),
        "obra_id": tag_record.get("obra_id"),
        "status": "pendente",
        "confidence": tag_record.get("confidence", 0.0),
        "suggestions": tag_record.get("suggestions", []),
        "matched_concept_ids": tag_record.get("matched_concept_ids", []),
        "timestamp": now_str(),
        "decision_timestamp": "",
        "decision_note": ""
    })
    save_json_file(VALIDATIONS_FILE, validations)


def save_answers(uid, animal, answers):
    users = load_json_file(USERS_FILE, [])
    exists = [u for u in users if u.get("user_id") == uid]
    if exists:
        return True
    users.append({
        "user_id": uid,
        "animal_name": animal,
        "timestamp": now_str(),
        **answers
    })
    return save_json_file(USERS_FILE, users)


def save_tag(uid, obra_id, tag_text):
    tags = load_json_file(TAGS_FILE, [])
    obras = load_obras()
    obra = next((o for o in obras if o["id"] == obra_id), None)
    semantic = analyze_tag_semantics(tag_text, obra)

    tag_record = {
        "id": len(tags) + 1,
        "user_id": uid,
        "obra_id": obra_id,
        "tag": tag_text.strip().lower(),
        "timestamp": now_str(),
        "normalized_tag": semantic["normalized_tag"],
        "semantic_status": semantic["status"],
        "confidence": semantic["confidence"],
        "matched_concept_ids": semantic["matched_concept_ids"],
        "categories": semantic["categories"],
        "out_of_description": semantic["out_of_description"],
        "suggestions": semantic["suggestions"],
        "tokens": semantic["tokens"]
    }
    tags.append(tag_record)
    save_json_file(TAGS_FILE, tags)

    if semantic["status"] != "reconciliado":
        enqueue_validation(tag_record)

    st.cache_data.clear()
    return tag_record


def get_user_tags(uid):
    df = load_tags_df()
    if df.empty:
        return pd.DataFrame()
    return df[df["user_id"] == uid].copy()


def get_obra_user_tags(obra_id, uid):
    df = load_tags_df()
    if df.empty:
        return pd.DataFrame(columns=["tag", "count"])
    f = df[(df["obra_id"] == obra_id) & (df["user_id"] == uid)]
    if f.empty:
        return pd.DataFrame(columns=["tag", "count"])
    c = f["tag"].value_counts().reset_index()
    c.columns = ["tag", "count"]
    return c


def check_login(username, password):
    return username == ADMIN_USERNAME and hash_password(password) == hash_password(ADMIN_PASSWORD)


# ──────────────────────────────────────────────────────────────────────
# GRAPH / NETWORK LOGIC
# ──────────────────────────────────────────────────────────────────────
def build_knowledge_graph():
    tags_df = load_tags_df()
    obras = load_obras()
    concepts = {c["id"]: c for c in load_concepts()}

    nodes = []
    edges = []

    for o in obras:
        nodes.append({"node_id": f"obra_{o['id']}", "label": o["titulo"], "type": "obra"})
        nodes.append({"node_id": f"artist_{normalize_text(o['artista'])}", "label": o["artista"], "type": "artista"})
        edges.append({"source": f"obra_{o['id']}", "target": f"artist_{normalize_text(o['artista'])}", "relation": "criada_por"})

        for t in safe_list(o.get("temas")):
            nid = f"inst_{normalize_text(t)}"
            nodes.append({"node_id": nid, "label": t, "type": "tema_institucional"})
            edges.append({"source": f"obra_{o['id']}", "target": nid, "relation": "tema_institucional"})

    if not tags_df.empty:
        for _, row in tags_df.iterrows():
            tnode = f"tag_{row['id']}"
            onode = f"obra_{int(row['obra_id'])}"
            nodes.append({"node_id": tnode, "label": row["tag"], "type": "tag"})
            edges.append({"source": onode, "target": tnode, "relation": "recebeu_tag"})

            for cid in safe_list(row.get("matched_concept_ids", [])):
                concept = concepts.get(cid)
                if concept:
                    cnode = f"concept_{cid}"
                    nodes.append({"node_id": cnode, "label": concept["label"], "type": "conceito"})
                    edges.append({"source": tnode, "target": cnode, "relation": "reconciliada_com"})

        tag_groups = tags_df.groupby("obra_id")
        for obra_id, group in tag_groups:
            tags = group["tag"].tolist()
            ids = group["id"].tolist()
            for (tag_a, id_a), (tag_b, id_b) in combinations(zip(tags, ids), 2):
                s = combined_similarity(tag_a, tag_b)
                if s >= 0.50:
                    edges.append({
                        "source": f"tag_{id_a}",
                        "target": f"tag_{id_b}",
                        "relation": "coocorre_semelhante",
                        "weight": round(s, 3)
                    })

    nodes_df = pd.DataFrame(nodes).drop_duplicates(subset=["node_id"])
    edges_df = pd.DataFrame(edges).drop_duplicates()
    return nodes_df, edges_df


def concept_label_from_id(concept_id):
    for c in load_concepts():
        if c["id"] == concept_id:
            return c["label"]
    return concept_id


# ──────────────────────────────────────────────────────────────────────
# METRICS
# ──────────────────────────────────────────────────────────────────────
def semantic_metrics(tags_df):
    if tags_df.empty:
        return {
            "total": 0,
            "reconciliado": 0,
            "sugerido": 0,
            "novo": 0,
            "fora_descricao": 0,
            "cobertura_semantica": 0.0
        }
    total = len(tags_df)
    reconciliado = int((tags_df["semantic_status"] == "reconciliado").sum()) if "semantic_status" in tags_df else 0
    sugerido = int((tags_df["semantic_status"] == "sugerido").sum()) if "semantic_status" in tags_df else 0
    novo = int((tags_df["semantic_status"] == "novo_termo").sum()) if "semantic_status" in tags_df else 0
    fora_desc = int(tags_df["out_of_description"].fillna(False).sum()) if "out_of_description" in tags_df else 0
    return {
        "total": total,
        "reconciliado": reconciliado,
        "sugerido": sugerido,
        "novo": novo,
        "fora_descricao": fora_desc,
        "cobertura_semantica": round((reconciliado + sugerido) / total if total else 0.0, 4)
    }


# ──────────────────────────────────────────────────────────────────────
# CSS
# ──────────────────────────────────────────────────────────────────────
def load_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800&display=swap');
    *{font-family:'Poppins',sans-serif!important}
    .stApp{
        background:linear-gradient(-45deg,#000 0%,#001f3f 25%,#07122a 55%,#001f3f 75%,#000 100%);
        background-size:400% 400%;
        animation:bg 16s ease infinite;
        color:#e8eef7;
    }
    @keyframes bg{
      0%{background-position:0% 50%}
      50%{background-position:100% 50%}
      100%{background-position:0% 50%}
    }
    .top-navbar{
        position:fixed; top:0; left:0; right:0; z-index:9999;
        background:rgba(255,255,255,.08);
        backdrop-filter:blur(18px) saturate(180%);
        border-bottom:1px solid rgba(255,255,255,.14);
        padding:1.1rem 2rem;
        display:flex; justify-content:space-between; align-items:center;
    }
    .navbar-logo{
        font-size:1.4rem; font-weight:800;
        background:linear-gradient(135deg,#a7e6ff 0%,#d1baff 100%);
        -webkit-background-clip:text; -webkit-text-fill-color:transparent;
    }
    .main-content{margin-top:100px;padding:1.2rem 2rem;max-width:1600px;margin-left:auto;margin-right:auto}
    .glass-card{
        background:rgba(255,255,255,.10);
        backdrop-filter:blur(18px) saturate(180%);
        border:1px solid rgba(255,255,255,.16);
        border-radius:22px; padding:1.4rem; margin:1rem 0;
        box-shadow:0 10px 28px rgba(0,0,0,.14);
    }
    .main-title{
        font-size:3rem; font-weight:800; color:white; text-align:center;
        margin:1.4rem 0 .7rem; letter-spacing:-1.5px;
    }
    .subtitle{
        font-size:1.06rem; text-align:center; color:rgba(255,255,255,.88);
        margin-bottom:1.8rem;
    }
    .tag-badge{
        display:inline-block; padding:.35rem .9rem; margin:.2rem;
        border-radius:999px; font-size:.8rem; font-weight:600;
        background:rgba(255,255,255,.14); border:1px solid rgba(255,255,255,.22); color:white;
    }
    .tag-green{background:rgba(34,197,94,.18)!important;border-color:rgba(34,197,94,.42)!important;color:#dcfce7!important}
    .tag-amber{background:rgba(245,158,11,.18)!important;border-color:rgba(245,158,11,.42)!important;color:#fef3c7!important}
    .tag-blue{background:rgba(96,165,250,.18)!important;border-color:rgba(96,165,250,.42)!important;color:#dbeafe!important}
    .obra-card{
        background:rgba(255,255,255,.10);
        border:1px solid rgba(255,255,255,.18);
        border-radius:18px; overflow:hidden;
        box-shadow:0 12px 28px rgba(0,0,0,.14);
    }
    .kpi-card{
        background:rgba(255,255,255,.10);
        border:1px solid rgba(255,255,255,.18);
        border-radius:18px; padding:1rem; text-align:center;
        box-shadow:0 8px 22px rgba(0,0,0,.1);
    }
    .kpi-lbl{font-size:.75rem; text-transform:uppercase; letter-spacing:1.5px; opacity:.76}
    .kpi-val{font-size:2rem; font-weight:800; margin:.4rem 0}
    .kpi-sub{font-size:.72rem; opacity:.55}
    .insight{
        background:rgba(167,230,255,.08);
        border:1px solid rgba(167,230,255,.22);
        border-radius:12px; padding:.9rem 1.05rem; margin:.6rem 0; line-height:1.7;
    }
    .divider{height:1px;background:linear-gradient(90deg,transparent,rgba(255,255,255,.22),transparent);margin:1.3rem 0}
    .conn-row{
        display:flex; justify-content:space-between; align-items:center; gap:10px;
        background:rgba(255,255,255,.05); border-radius:12px; padding:.8rem 1rem; margin:.35rem 0;
    }
    .cluster-wrap{
        background:rgba(255,255,255,.06); border-radius:14px; padding:1rem; margin:.5rem 0;
        border:1px solid rgba(255,255,255,.08)
    }
    .small-muted{font-size:.78rem; color:rgba(255,255,255,.62)}
    .metric-pill{
        display:inline-flex;align-items:center;gap:5px;
        padding:.3rem .75rem;border-radius:999px;
        background:rgba(255,255,255,.10);border:1px solid rgba(255,255,255,.16);margin:.15rem;
        font-size:.76rem;
    }
    .stButton button{
        border-radius:999px!important;
        background:rgba(255,255,255,.16)!important;
        border:1px solid rgba(255,255,255,.22)!important;
        color:white!important;font-weight:700!important;
    }
    .stTextInput input,.stTextArea textarea,.stSelectbox select{
        background:rgba(255,255,255,.12)!important;
        color:white!important; border-radius:14px!important;
        border:1px solid rgba(255,255,255,.18)!important;
    }
    .stTabs [data-baseweb="tab-list"]{
        gap:.5rem;background:rgba(255,255,255,.08);padding:.35rem;border-radius:12px;
    }
    .stTabs [data-baseweb="tab"]{
        background:rgba(255,255,255,.08); border-radius:10px;
        border:1px solid rgba(255,255,255,.12); color:white;
    }
    .stTabs [aria-selected="true"]{
        background:rgba(255,255,255,.20)!important;
    }
    #MainMenu, footer, header {visibility:hidden;}
    [data-testid="stSidebar"]{display:none}
    </style>
    """, unsafe_allow_html=True)


def kpi(label, value, sub="", color="#a7e6ff"):
    return (
        f"<div class='kpi-card'>"
        f"<div class='kpi-lbl'>{label}</div>"
        f"<div class='kpi-val' style='color:{color}'>{value}</div>"
        f"{f'<div class=kpi-sub>{sub}</div>' if sub else ''}"
        f"</div>"
    )


def insight(text):
    return f"<div class='insight'>{text}</div>"


def divider():
    return "<div class='divider'></div>"


def show_header():
    st.markdown(
        "<div class='top-navbar'>"
        "<div class='navbar-logo'>Sistema Folksonomia Digital Semântico</div>"
        "<div class='small-muted'>Camada inspirada no Prado: reconciliação + validação + grafo</div>"
        "</div>",
        unsafe_allow_html=True
    )


# ──────────────────────────────────────────────────────────────────────
# INTRO
# ──────────────────────────────────────────────────────────────────────
def show_intro():
    st.markdown("<div class='main-content'>", unsafe_allow_html=True)
    st.markdown("<h1 class='main-title'>Sistema Folksonomia Digital Semântico</h1>", unsafe_allow_html=True)
    st.markdown(
        "<p class='subtitle'>Folksonomia com sugestões inteligentes, reconciliação conceitual, "
        "fila de validação e grafo de conhecimento</p>",
        unsafe_allow_html=True
    )
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.markdown(
        "<h2 style='text-align:center;margin-bottom:1.6rem'>Questionário de Acesso</h2>",
        unsafe_allow_html=True
    )
    with st.form("intro_form"):
        c1, c2 = st.columns(2)
        with c1:
            q1 = st.selectbox(
                "1. Qual é o seu nível de familiaridade com museus?",
                ["Nunca visito museus", "Visito raramente", "Visito ocasionalmente", "Visito frequentemente"]
            )
            q2 = st.selectbox(
                "2. Você já ouviu falar sobre documentação museológica?",
                ["Nunca ouvi falar", "Já ouvi, mas não sei o que é", "Tenho uma ideia básica", "Conheço bem o tema"]
            )
        with c2:
            q3 = st.text_area(
                "3. O que você entende por 'tags' ou etiquetas digitais aplicadas a acervo?",
                max_chars=500,
                height=220,
                placeholder="Descreva sua compreensão..."
            )
        submitted = st.form_submit_button("Acessar Plataforma", use_container_width=True)
        if submitted:
            if not q3.strip():
                st.error("Preencha todas as perguntas.")
            else:
                st.session_state["answers"] = {"q1": q1, "q2": q2, "q3": q3}
                save_answers(st.session_state["user_id"], st.session_state["animal_name"], st.session_state["answers"])
                st.session_state["step"] = "completed"
                st.success("Acesso liberado.")
                st.rerun()
    st.markdown("</div></div>", unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────
# PUBLIC WORKS
# ──────────────────────────────────────────────────────────────────────
def show_semantic_preview(obra, user_tag_input):
    if not user_tag_input.strip():
        return
    analysis = analyze_tag_semantics(user_tag_input, obra)
    color_class = "tag-green" if analysis["status"] == "reconciliado" else "tag-amber" if analysis["status"] == "sugerido" else "tag-blue"

    st.markdown("**Pré-leitura semântica da tag:**")
    st.markdown(
        f"<span class='tag-badge {color_class}'>status: {analysis['status']}</span>"
        f"<span class='tag-badge'>confiança: {analysis['confidence']:.2f}</span>"
        f"<span class='tag-badge'>fora da descrição: {'sim' if analysis['out_of_description'] else 'não'}</span>",
        unsafe_allow_html=True
    )
    if analysis["suggestions"]:
        st.markdown("**Conceitos sugeridos:**")
        st.markdown("".join([
            f"<span class='tag-badge'>{s['label']} · {s['category']} · {s['score']:.2f}</span>"
            for s in analysis["suggestions"][:5]
        ]), unsafe_allow_html=True)


def show_obras():
    st.markdown("<h1 class='main-title'>Galeria de Obras</h1>", unsafe_allow_html=True)
    st.markdown(
        "<p class='subtitle'>Agora com camada semântica inspirada no Prado: sugestões, reconciliação e leitura contextual</p>",
        unsafe_allow_html=True
    )
    obras = load_obras()
    tags_df = load_tags_df()

    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    c1, c2 = st.columns([2, 1])
    with c1:
        search = st.text_input("Filtrar por número, título ou artista:", "", placeholder="Ex: 1, Picasso, Noite...")
    with c2:
        sort_opt = st.selectbox("Ordenar por:", ["Número (crescente)", "Número (decrescente)", "Título"])
    st.markdown("</div>", unsafe_allow_html=True)

    filtered = obras
    s = normalize_text(search)
    if s:
        filtered = [
            o for o in obras
            if s in normalize_text(str(o["id"])) or s in normalize_text(o["titulo"]) or s in normalize_text(o["artista"])
        ]

    if sort_opt == "Número (descrescente)":
        filtered = sorted(filtered, key=lambda x: x["id"], reverse=True)
    elif sort_opt == "Título":
        filtered = sorted(filtered, key=lambda x: normalize_text(x["titulo"]))
    else:
        filtered = sorted(filtered, key=lambda x: x["id"])

    st.markdown(
        f"<div style='text-align:center;margin:.8rem 0 1rem;color:white'>Exibindo <strong>{len(filtered)}</strong> obra(s)</div>",
        unsafe_allow_html=True
    )

    cols = st.columns(3)
    for i, obra in enumerate(filtered):
        with cols[i % 3]:
            st.markdown(
                f"""
                <div class='obra-card'>
                    <img src="{obra['imagem']}" style="width:100%;height:260px;object-fit:cover;">
                    <div style="padding:1rem 1rem .3rem">
                        <h3 style="margin:0 0 .35rem">{obra['titulo']}</h3>
                        <div class='small-muted'>{obra['artista']} · {obra['ano']}</div>
                        <div style="margin:.8rem 0">{''.join([f"<span class='metric-pill'>{t}</span>" for t in safe_list(obra.get('temas'))[:4]])}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

            if st.button("Detalhar e adicionar tag", key=f"obra_{obra['id']}", use_container_width=True):
                st.session_state["selected_obra"] = obra["id"]
                st.rerun()

            if st.session_state.get("selected_obra") == obra["id"]:
                st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
                st.markdown(f"**Descrição institucional:** {obra.get('descricao', 'Sem descrição')}")
                st.markdown("**Sugestões inteligentes de tags:**")
                suggestions = suggest_tags_for_obra(obra, tags_df)
                st.markdown("".join([f"<span class='tag-badge'>{x}</span>" for x in suggestions]), unsafe_allow_html=True)

                with st.form(f"tag_form_{obra['id']}"):
                    tag_input = st.text_input("Sua tag livre:", placeholder="Ex: dor, céu, retrato, azul...")
                    submitted = st.form_submit_button("Salvar tag", use_container_width=True)
                    if submitted:
                        if not tag_input.strip():
                            st.error("Digite uma tag.")
                        else:
                            record = save_tag(st.session_state["user_id"], obra["id"], tag_input)
                            status_msg = (
                                "Tag reconciliada automaticamente."
                                if record["semantic_status"] == "reconciliado"
                                else "Tag salva e enviada para validação semântica."
                            )
                            st.success(status_msg)
                            st.session_state["selected_obra"] = None
                            st.rerun()

                live_input = st.text_input(
                    "Pré-visualizar leitura semântica da sua tag:",
                    key=f"preview_{obra['id']}",
                    placeholder="Digite antes de salvar, se quiser testar"
                )
                show_semantic_preview(obra, live_input)

                utags = get_obra_user_tags(obra["id"], st.session_state["user_id"])
                if not utags.empty:
                    st.markdown("**Suas tags nesta obra:**")
                    st.markdown(
                        "".join([f"<span class='tag-badge'>{row['tag']} ({row['count']})</span>" for _, row in utags.iterrows()]),
                        unsafe_allow_html=True
                    )

                all_obra_tags = tags_df[tags_df["obra_id"] == obra["id"]].copy() if not tags_df.empty else pd.DataFrame()
                if not all_obra_tags.empty:
                    st.markdown("**Top tags da obra:**")
                    top_tags = all_obra_tags["tag"].value_counts().head(8)
                    st.markdown(
                        "".join([f"<span class='tag-badge tag-blue'>{idx} ({val})</span>" for idx, val in top_tags.items()]),
                        unsafe_allow_html=True
                    )

                if st.button("Fechar", key=f"close_{obra['id']}", use_container_width=True):
                    st.session_state["selected_obra"] = None
                    st.rerun()

                st.markdown("</div>", unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────
# ADMIN
# ──────────────────────────────────────────────────────────────────────
def show_admin():
    if "admin_logged_in" not in st.session_state:
        st.session_state["admin_logged_in"] = False

    if not st.session_state["admin_logged_in"]:
        st.markdown("<h1 class='main-title'>Área Administrativa</h1>", unsafe_allow_html=True)
        st.markdown("<p class='subtitle'>Acesso restrito</p>", unsafe_allow_html=True)
        _, middle, _ = st.columns([1, 1, 1])
        with middle:
            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
            with st.form("login_form"):
                username = st.text_input("Usuário")
                password = st.text_input("Senha", type="password")
                submitted = st.form_submit_button("Entrar", use_container_width=True)
                if submitted:
                    if check_login(username, password):
                        st.session_state["admin_logged_in"] = True
                        st.success("Login realizado.")
                        st.rerun()
                    else:
                        st.error("Credenciais inválidas.")
            st.markdown("</div>", unsafe_allow_html=True)
        return

    st.markdown("<h1 class='main-title'>Dashboard Semântico</h1>", unsafe_allow_html=True)
    st.markdown(
        "<p class='subtitle'>Camadas implementadas: sugestões inteligentes, reconciliação, fila de validação, entidades, grafo e análise de conectividade</p>",
        unsafe_allow_html=True
    )

    tabs = st.tabs([
        "Visão Geral",
        "Camada Semântica",
        "Fila de Validação",
        "Grafo de Conhecimento",
        "Conexões de Tags",
        "Usuários",
        "Obras",
        "Exportar"
    ])

    with tabs[0]:
        tab_overview()
    with tabs[1]:
        tab_semantic()
    with tabs[2]:
        tab_validation_queue()
    with tabs[3]:
        tab_graph()
    with tabs[4]:
        tab_connections()
    with tabs[5]:
        tab_users()
    with tabs[6]:
        tab_obras()
    with tabs[7]:
        tab_export()

    if st.button("Sair da área administrativa", use_container_width=True):
        st.session_state["admin_logged_in"] = False
        st.rerun()


# ──────────────────────────────────────────────────────────────────────
# ADMIN TABS
# ──────────────────────────────────────────────────────────────────────
def tab_overview():
    tags_df = load_tags_df()
    users_df = load_users_df()
    obras = load_obras()
    metrics = semantic_metrics(tags_df)

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown(kpi("Total de tags", metrics["total"], "registros", "#a7e6ff"), unsafe_allow_html=True)
    with c2:
        st.markdown(kpi("Reconciliadas", metrics["reconciliado"], "alto grau de confiança", "#6ee7b7"), unsafe_allow_html=True)
    with c3:
        st.markdown(kpi("Sugeridas", metrics["sugerido"], "aguardam revisão ou confirmação", "#fcd34d"), unsafe_allow_html=True)
    with c4:
        st.markdown(kpi("Novos termos", metrics["novo"], "vocabulário emergente", "#f9a8d4"), unsafe_allow_html=True)
    with c5:
        st.markdown(kpi("Cobertura semântica", f"{metrics['cobertura_semantica']:.0%}", "reconciliado + sugerido", "#d1baff"), unsafe_allow_html=True)

    st.markdown(divider(), unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(kpi("Participantes", users_df["user_id"].nunique() if not users_df.empty else 0, "", "#a7e6ff"), unsafe_allow_html=True)
    with c2:
        st.markdown(kpi("Obras", len(obras), "", "#6ee7b7"), unsafe_allow_html=True)
    with c3:
        st.markdown(kpi("Tags fora da descrição", metrics["fora_descricao"], "potencial out-of-summary", "#fcd34d"), unsafe_allow_html=True)

    st.markdown(insight(
        "<strong>Leitura do modelo:</strong> a camada implementada aproxima o sistema de uma lógica inspirada no Prado. "
        "As tags livres continuam existindo, mas agora podem ser lidas semanticamente, reconciliadas a conceitos e "
        "encaminhadas para validação humana quando necessário."
    ), unsafe_allow_html=True)

    if not tags_df.empty:
        st.markdown("#### Distribuição por status semântico")
        st.bar_chart(tags_df["semantic_status"].value_counts())

        cat_counter = Counter()
        for cats in tags_df["categories"].fillna("").tolist():
            if isinstance(cats, list):
                for c in cats:
                    cat_counter[c] += 1
        if cat_counter:
            st.markdown("#### Distribuição por categoria conceitual")
            st.bar_chart(pd.Series(cat_counter).sort_values(ascending=False))

        st.markdown("#### Top 20 tags")
        st.bar_chart(tags_df["tag"].value_counts().head(20))


def tab_semantic():
    tags_df = load_tags_df()
    concepts_df = pd.DataFrame(load_concepts())

    st.markdown("### Camada Semântica")
    st.markdown(insight(
        "<strong>Implementação incluída:</strong> normalização textual, matching de aliases, sugestão de conceitos, "
        "tipificação por categoria, detecção de tags fora da descrição e fila de validação humana."
    ), unsafe_allow_html=True)

    t1, t2, t3 = st.tabs(["Vocabulário controlado", "Tags analisadas", "Testar reconciliação"])

    with t1:
        st.markdown("#### Conceitos cadastrados")
        st.dataframe(concepts_df[["id", "label", "category", "uri"]], use_container_width=True, hide_index=True)

        st.markdown(divider(), unsafe_allow_html=True)
        st.markdown("#### Adicionar novo conceito")
        with st.form("new_concept"):
            c1, c2 = st.columns(2)
            with c1:
                label = st.text_input("Rótulo canônico")
                category = st.selectbox("Categoria", ["tema", "cor", "material", "técnica", "período", "emoção"])
            with c2:
                aliases = st.text_input("Aliases separados por vírgula")
                uri = st.text_input("URI opcional")
            submitted = st.form_submit_button("Adicionar conceito", use_container_width=True)
            if submitted:
                if label.strip():
                    concepts = load_json_file(CONCEPTS_FILE, default_concepts())
                    cid = f"{category}_{normalize_text(label).replace(' ', '_')}"
                    if not any(c["id"] == cid for c in concepts):
                        concepts.append({
                            "id": cid,
                            "label": label.strip(),
                            "aliases": [a.strip() for a in aliases.split(",") if a.strip()],
                            "category": category,
                            "uri": uri.strip()
                        })
                        save_json_file(CONCEPTS_FILE, concepts)
                        st.cache_data.clear()
                        st.success("Conceito adicionado.")
                        st.rerun()
                    else:
                        st.warning("Esse conceito já existe.")

    with t2:
        if tags_df.empty:
            st.info("Ainda não há tags.")
        else:
            display = tags_df.copy()
            display["conceitos"] = display["matched_concept_ids"].apply(lambda ids: ", ".join([concept_label_from_id(i) for i in ids]) if isinstance(ids, list) else "")
            display["categorias"] = display["categories"].apply(lambda c: ", ".join(c) if isinstance(c, list) else "")
            cols = ["id", "obra_id", "tag", "semantic_status", "confidence", "categorias", "conceitos", "out_of_description", "timestamp"]
            st.dataframe(display[cols].sort_values("id", ascending=False), use_container_width=True, hide_index=True)

            st.markdown(divider(), unsafe_allow_html=True)
            st.markdown("#### Tags emergentes fora da descrição institucional")
            out_df = display[display["out_of_description"] == True][["obra_id", "tag", "semantic_status", "conceitos", "timestamp"]]
            if out_df.empty:
                st.info("Nenhuma tag marcada como out-of-description.")
            else:
                st.dataframe(out_df, use_container_width=True, hide_index=True)

    with t3:
        st.markdown("#### Teste manual de reconciliação")
        obras = load_obras()
        obra_options = {f"#{o['id']} — {o['titulo']}": o for o in obras}
        selected_label = st.selectbox("Contexto de obra", list(obra_options.keys()))
        obra = obra_options[selected_label]
        text = st.text_input("Digite uma tag para testar")
        if text.strip():
            result = analyze_tag_semantics(text, obra)
            st.json(result)


def update_validation(decision_id, new_status, selected_concept_id="", note=""):
    vals = load_json_file(VALIDATIONS_FILE, [])
    tags = load_json_file(TAGS_FILE, [])
    for v in vals:
        if v["id"] == decision_id:
            v["status"] = new_status
            v["decision_timestamp"] = now_str()
            v["decision_note"] = note
            if selected_concept_id:
                v["matched_concept_ids"] = [selected_concept_id]

            for t in tags:
                if t["id"] == v["tag_id"]:
                    if new_status == "aprovado":
                        if selected_concept_id:
                            t["matched_concept_ids"] = [selected_concept_id]
                            concept = next((c for c in load_concepts() if c["id"] == selected_concept_id), None)
                            t["categories"] = [concept["category"]] if concept else t.get("categories", [])
                        t["semantic_status"] = "reconciliado"
                        t["confidence"] = max(float(t.get("confidence", 0.0)), 0.90)
                    elif new_status == "rejeitado":
                        t["semantic_status"] = "novo_termo"
                    break
            break

    save_json_file(VALIDATIONS_FILE, vals)
    save_json_file(TAGS_FILE, tags)
    st.cache_data.clear()


def tab_validation_queue():
    vals_df = load_validations_df()
    concepts = load_concepts()

    st.markdown("### Fila de Validação")
    st.markdown(insight(
        "<strong>Função equivalente à supervisão documental:</strong> "
        "tags não reconciliadas automaticamente são enviadas para revisão humana, em linha com o padrão "
        "de automação + validação discutido no documento e no caso do Prado."
    ), unsafe_allow_html=True)

    if vals_df.empty:
        st.info("Nenhuma validação pendente.")
        return

    pending = vals_df[vals_df["status"] == "pendente"].copy()
    if pending.empty:
        st.success("Nenhuma pendência. Todas as validações já foram tratadas.")
        st.dataframe(vals_df.sort_values("id", ascending=False), use_container_width=True, hide_index=True)
        return

    st.markdown(f"**Pendências atuais:** {len(pending)}")
    for _, row in pending.sort_values("confidence").iterrows():
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.markdown(f"**Tag #{row['tag_id']}** · `{row['tag']}` · confiança `{row['confidence']:.2f}`")
        st.markdown(f"**Obra:** {row['obra_id']}")
        suggestions = row["suggestions"] if isinstance(row["suggestions"], list) else []
        if suggestions:
            st.markdown("**Sugestões automáticas:**")
            st.markdown("".join([
                f"<span class='tag-badge'>{s['label']} · {s['category']} · {s['score']:.2f}</span>"
                for s in suggestions[:5]
            ]), unsafe_allow_html=True)
        else:
            st.markdown("<span class='small-muted'>Sem sugestão automática forte.</span>", unsafe_allow_html=True)

        concept_options = {"— sem vínculo —": ""}
        for c in concepts:
            concept_options[f"{c['label']} · {c['category']}"] = c["id"]

        c1, c2, c3 = st.columns([2, 1, 1])
        with c1:
            selected = st.selectbox(
                f"Escolha um conceito para a tag #{row['tag_id']}",
                list(concept_options.keys()),
                key=f"concept_{row['id']}"
            )
            note = st.text_input("Nota da validação", key=f"note_{row['id']}")
        with c2:
            if st.button("Aprovar", key=f"approve_{row['id']}", use_container_width=True):
                update_validation(row["id"], "aprovado", concept_options[selected], note)
                st.success("Validação aprovada.")
                st.rerun()
        with c3:
            if st.button("Rejeitar", key=f"reject_{row['id']}", use_container_width=True):
                update_validation(row["id"], "rejeitado", "", note)
                st.warning("Validação rejeitada.")
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)


def tab_graph():
    st.markdown("### Grafo de Conhecimento")
    st.markdown(insight(
        "<strong>Camada tipo Prado implementada:</strong> obras, artistas, tags e conceitos agora podem ser lidos "
        "como nós e relações. O sistema não fica mais só em lista de tags; ele passa a estruturar conexões."
    ), unsafe_allow_html=True)

    nodes_df, edges_df = build_knowledge_graph()

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(kpi("Nós", len(nodes_df), "", "#a7e6ff"), unsafe_allow_html=True)
    with c2:
        st.markdown(kpi("Relações", len(edges_df), "", "#6ee7b7"), unsafe_allow_html=True)
    with c3:
        st.markdown(kpi("Tipos de relação", edges_df["relation"].nunique() if not edges_df.empty else 0, "", "#fcd34d"), unsafe_allow_html=True)

    if not nodes_df.empty:
        st.markdown("#### Distribuição de tipos de nós")
        st.bar_chart(nodes_df["type"].value_counts())

    if not edges_df.empty:
        st.markdown("#### Distribuição de relações")
        st.bar_chart(edges_df["relation"].value_counts())

    t1, t2 = st.tabs(["Nós", "Relações"])
    with t1:
        st.dataframe(nodes_df.sort_values(["type", "label"]), use_container_width=True, hide_index=True)
    with t2:
        st.dataframe(edges_df.sort_values("relation"), use_container_width=True, hide_index=True)


def tag_connections(tags_list, threshold=0.35):
    uniq = list(dict.fromkeys([normalize_text(t) for t in tags_list if str(t).strip()]))
    original_lookup = {}
    for t in tags_list:
        nt = normalize_text(t)
        if nt and nt not in original_lookup:
            original_lookup[nt] = t

    conns = []
    for i in range(len(uniq)):
        for j in range(i + 1, len(uniq)):
            s = combined_similarity(uniq[i], uniq[j])
            if s >= threshold:
                ta = original_lookup.get(uniq[i], uniq[i])
                tb = original_lookup.get(uniq[j], uniq[j])
                if uniq[i] in uniq[j] or uniq[j] in uniq[i]:
                    tipo = "Contenção"
                elif jaccard_words(uniq[i], uniq[j]) >= 0.5:
                    tipo = "Coocorrência lexical"
                else:
                    tipo = "Proximidade semântica/fonética"
                conns.append({"tag_a": ta, "tag_b": tb, "similaridade": round(s, 3), "tipo": tipo})
    conns.sort(key=lambda x: x["similaridade"], reverse=True)
    return conns


def tag_clusters(tags_list, threshold=0.35):
    uniq = list(dict.fromkeys([normalize_text(t) for t in tags_list if str(t).strip()]))
    parent = {u: u for u in uniq}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for c in tag_connections(tags_list, threshold):
        union(normalize_text(c["tag_a"]), normalize_text(c["tag_b"]))

    groups = defaultdict(list)
    original_lookup = {}
    for t in tags_list:
        nt = normalize_text(t)
        if nt and nt not in original_lookup:
            original_lookup[nt] = t
    for u in uniq:
        groups[find(u)].append(original_lookup.get(u, u))
    return [sorted(v) for v in groups.values() if len(v) > 1]


def tab_connections():
    tags_df = load_tags_df()
    if tags_df.empty:
        st.info("Nenhuma tag disponível.")
        return

    st.markdown("### Conexões de Tags")
    st.markdown(insight(
        "<strong>Implementação alinhada ao documento:</strong> tags são tratadas como rede, "
        "com análise de proximidade, coocorrência, grupos emergentes e vocabulário relacional."
    ), unsafe_allow_html=True)

    obras = load_obras()
    obra_map = {f"#{o['id']} — {o['titulo']}": o["id"] for o in obras}
    c1, c2, c3 = st.columns(3)
    with c1:
        threshold = st.slider("Limiar de similaridade", 0.20, 0.95, 0.35, 0.05)
    with c2:
        obra_label = st.selectbox("Filtrar por obra", ["Todas"] + list(obra_map.keys()))
    with c3:
        max_show = st.number_input("Máx. conexões", min_value=10, max_value=300, value=60, step=10)

    filtered = tags_df.copy()
    if obra_label != "Todas":
        filtered = filtered[filtered["obra_id"] == obra_map[obra_label]]

    tag_list = filtered["tag"].tolist()
    if len(set([normalize_text(x) for x in tag_list])) < 2:
        st.warning("É preciso ter pelo menos duas tags distintas.")
        return

    conns = tag_connections(tag_list, threshold)
    clusters = tag_clusters(tag_list, threshold)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(kpi("Conexões", len(conns), "", "#a7e6ff"), unsafe_allow_html=True)
    with c2:
        st.markdown(kpi("Grupos", len(clusters), "", "#6ee7b7"), unsafe_allow_html=True)
    with c3:
        st.markdown(kpi("Tags distintas", filtered["tag"].nunique(), "", "#fcd34d"), unsafe_allow_html=True)

    t1, t2 = st.tabs(["Lista de conexões", "Grupos"])
    with t1:
        if not conns:
            st.info("Nenhuma conexão encontrada.")
        else:
            for c in conns[:int(max_show)]:
                st.markdown(
                    f"<div class='conn-row'>"
                    f"<div><span class='tag-badge'>{c['tag_a']}</span> ↔ "
                    f"<span class='tag-badge'>{c['tag_b']}</span></div>"
                    f"<div><span class='metric-pill'>{c['tipo']}</span>"
                    f"<span class='metric-pill'>{c['similaridade']:.3f}</span></div>"
                    f"</div>",
                    unsafe_allow_html=True
                )
            st.download_button(
                "Baixar conexões CSV",
                pd.DataFrame(conns).to_csv(index=False).encode("utf-8"),
                "conexoes_tags.csv",
                "text/csv",
                use_container_width=True
            )

    with t2:
        if not clusters:
            st.info("Nenhum grupo formado.")
        else:
            for i, cluster in enumerate(sorted(clusters, key=len, reverse=True), start=1):
                st.markdown(
                    f"<div class='cluster-wrap'><strong>Grupo {i}</strong><br>{''.join([f'<span class=tag-badge>{c}</span>' for c in cluster])}</div>",
                    unsafe_allow_html=True
                )


def tab_users():
    users_df = load_users_df()
    tags_df = load_tags_df()
    obras = load_obras()
    obra_map = {o["id"]: o["titulo"] for o in obras}

    st.markdown("### Usuários e respostas")
    if users_df.empty:
        st.info("Nenhum usuário registrado.")
        return

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(kpi("Usuários", users_df["user_id"].nunique(), "", "#a7e6ff"), unsafe_allow_html=True)
    with c2:
        st.markdown(kpi("Média de tags/usuário", f"{(len(tags_df)/max(len(users_df),1)):.1f}", "", "#6ee7b7"), unsafe_allow_html=True)
    with c3:
        richness = 0.0
        if not tags_df.empty:
            richness = tags_df["tag"].nunique() / len(tags_df)
        st.markdown(kpi("Riqueza global", f"{richness:.2%}", "TTR global", "#fcd34d"), unsafe_allow_html=True)

    t1, t2 = st.tabs(["Tabela", "Perfis individuais"])
    with t1:
        merged = users_df.copy()
        if not tags_df.empty:
            per_user = tags_df.groupby("user_id").agg(total_tags=("tag", "count"), tags_unicas=("tag", "nunique"), obras=("obra_id", "nunique")).reset_index()
            merged = merged.merge(per_user, on="user_id", how="left")
        merged = merged.fillna(0)
        st.dataframe(merged, use_container_width=True, hide_index=True)

    with t2:
        labels = [f"🐾 {row.get('animal_name', row['user_id'][:8])}" for _, row in users_df.iterrows()]
        selected = st.selectbox("Selecione o participante", labels)
        idx = labels.index(selected)
        uid = users_df.iloc[idx]["user_id"]
        user_tags = tags_df[tags_df["user_id"] == uid].copy() if not tags_df.empty else pd.DataFrame()
        if user_tags.empty:
            st.info("Esse participante ainda não criou tags.")
        else:
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Top tags do participante**")
                st.bar_chart(user_tags["tag"].value_counts().head(12))
            with c2:
                st.markdown("**Obras mais tagueadas**")
                by_obra = user_tags["obra_id"].value_counts().rename(index=obra_map)
                st.bar_chart(by_obra)

            display = user_tags.copy()
            display["conceitos"] = display["matched_concept_ids"].apply(lambda ids: ", ".join([concept_label_from_id(i) for i in ids]) if isinstance(ids, list) else "")
            st.dataframe(display[["obra_id", "tag", "semantic_status", "confidence", "conceitos", "timestamp"]], use_container_width=True, hide_index=True)


def tab_obras():
    st.markdown("### Gestão de Obras")
    obras = load_obras()
    t1, t2 = st.tabs(["Listar obras", "Adicionar nova"])

    with t1:
        if not obras:
            st.info("Nenhuma obra cadastrada.")
        for obra in obras:
            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
            c1, c2, c3 = st.columns([1.1, 2, 1])
            with c1:
                st.image(obra["imagem"], use_container_width=True)
            with c2:
                st.markdown(f"**#{obra['id']} — {obra['titulo']}**")
                st.markdown(f"{obra['artista']} · {obra['ano']}")
                st.markdown(f"<span class='small-muted'>{obra.get('descricao','')}</span>", unsafe_allow_html=True)
                st.markdown("".join([f"<span class='metric-pill'>{x}</span>" for x in safe_list(obra.get("temas"))]), unsafe_allow_html=True)
            with c3:
                if st.button("Remover", key=f"remove_obra_{obra['id']}", use_container_width=True):
                    new_obras = [o for o in obras if o["id"] != obra["id"]]
                    save_json_file(OBRAS_FILE, new_obras)
                    st.cache_data.clear()
                    st.success("Obra removida.")
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    with t2:
        with st.form("add_obra"):
            c1, c2 = st.columns(2)
            with c1:
                titulo = st.text_input("Título")
                artista = st.text_input("Artista")
                ano = st.text_input("Ano")
                imagem = st.text_input("URL da imagem")
            with c2:
                descricao = st.text_area("Descrição")
                temas = st.text_input("Temas separados por vírgula")
                materiais = st.text_input("Materiais separados por vírgula")
                tecnicas = st.text_input("Técnicas separadas por vírgula")
                periodo = st.text_input("Período")
            submitted = st.form_submit_button("Adicionar obra", use_container_width=True)
            if submitted:
                if titulo.strip() and artista.strip():
                    nid = max([o["id"] for o in obras], default=0) + 1
                    obras.append({
                        "id": nid,
                        "titulo": titulo.strip(),
                        "artista": artista.strip(),
                        "ano": ano.strip(),
                        "imagem": imagem.strip(),
                        "descricao": descricao.strip(),
                        "temas": [x.strip() for x in temas.split(",") if x.strip()],
                        "materiais": [x.strip() for x in materiais.split(",") if x.strip()],
                        "tecnicas": [x.strip() for x in tecnicas.split(",") if x.strip()],
                        "periodo": periodo.strip()
                    })
                    save_json_file(OBRAS_FILE, obras)
                    st.cache_data.clear()
                    st.success("Obra adicionada.")
                    st.rerun()
                else:
                    st.error("Preencha pelo menos título e artista.")


def tab_export():
    st.markdown("### Exportação")
    tags_df = load_tags_df()
    users_df = load_users_df()
    obras_df = pd.DataFrame(load_obras())
    vals_df = load_validations_df()
    nodes_df, edges_df = build_knowledge_graph()

    c1, c2, c3 = st.columns(3)
    with c1:
        if not tags_df.empty:
            st.download_button("Tags CSV", tags_df.to_csv(index=False).encode("utf-8"), "tags.csv", "text/csv", use_container_width=True)
        if not vals_df.empty:
            st.download_button("Validações CSV", vals_df.to_csv(index=False).encode("utf-8"), "validacoes.csv", "text/csv", use_container_width=True)
    with c2:
        if not users_df.empty:
            st.download_button("Usuários CSV", users_df.to_csv(index=False).encode("utf-8"), "usuarios.csv", "text/csv", use_container_width=True)
        if not nodes_df.empty:
            st.download_button("Nós do grafo CSV", nodes_df.to_csv(index=False).encode("utf-8"), "grafo_nos.csv", "text/csv", use_container_width=True)
    with c3:
        if not obras_df.empty:
            st.download_button("Obras CSV", obras_df.to_csv(index=False).encode("utf-8"), "obras.csv", "text/csv", use_container_width=True)
        if not edges_df.empty:
            st.download_button("Relações do grafo CSV", edges_df.to_csv(index=False).encode("utf-8"), "grafo_relacoes.csv", "text/csv", use_container_width=True)


# ──────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────
def main():
    init_data()
    load_css()

    for key, value in [
        ("user_id", gen_uid()),
        ("animal_name", generate_animal_name()),
        ("step", "intro"),
        ("answers", {})
    ]:
        if key not in st.session_state:
            st.session_state[key] = value

    if st.session_state["step"] != "completed":
        show_intro()
        return

    show_header()
    st.markdown("<div class='main-content'>", unsafe_allow_html=True)
    t1, t2 = st.tabs(["Explorar Obras", "Área Administrativa"])
    with t1:
        show_obras()
    with t2:
        show_admin()
    st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
