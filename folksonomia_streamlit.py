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
import re
from collections import defaultdict
warnings.filterwarnings('ignore')

st.set_page_config(
    page_title="Sistema Folksonomia Digital",
    layout="wide",
    initial_sidebar_state="collapsed",
    page_icon="\ud83d\udcda"
)

DATA_DIR        = "data"
OBRAS_FILE      = os.path.join(DATA_DIR, "obras.json")
TAGS_FILE       = os.path.join(DATA_DIR, "tags.json")
USERS_FILE      = os.path.join(DATA_DIR, "users.json")
ADMIN_FILE      = os.path.join(DATA_DIR, "admin.json")
CHAIN_FILE      = os.path.join(DATA_DIR, "blockchain.json")
ONTOLOGY_FILE   = os.path.join(DATA_DIR, "ontologias.json")
VALIDATION_FILE = os.path.join(DATA_DIR, "validacoes.json")
ADMIN_USERNAME  = "nugep"
ADMIN_PASSWORD  = "nugep123"

ANIMAIS = [
    "\u00c1guia","Boto","Capivara","Doninha","Ema","Falc\u00e3o","Gavi\u00e3o","Harpia","Irara","Jaguar",
    "Lontra","Mico","On\u00e7a","Paca","Quati","Raposa","Tamandu\u00e1","Urubu","Veado","Zorrilho",
    "Arara","Bugio","Caititu","Jaguatirica","Lobo","Mutum","Pirarucu","Tucano","Sucuri","Tatu"
]
ADJETIVOS = [
    "Azul","Bravo","Calmo","Dourado","Esperto","Feroz","Gracioso","Intenso","Jovial","Lento",
    "M\u00e1gico","Nobre","Ousado","Preciso","R\u00e1pido","S\u00e1bio","T\u00edmido","\u00danico","Valente","Zeloso",
    "Curioso","Furtivo","Altivo","Sereno","Vibrante","Audaz","Brilhante","Corajoso","Distinto","Elegante"
]

TAG_STATUS = ["bruto", "sugerido", "validado", "revisado", "publicado"]

ONTOLOGIAS_DEFAULT = [
    {"id":1,"nome":"Religi\u00e3o","descricao":"Termos religiosos e espirituais","tags":["deus","sagrado","f\u00e9","ora\u00e7\u00e3o","templo","cruz","b\u00edblia","isl\u00e3o","budismo","hindu\u00edsmo","catolicismo","esp\u00edrito","ritual","missa","altar"]},
    {"id":2,"nome":"Guerra","descricao":"Termos relacionados a conflitos e guerra","tags":["guerra","batalha","soldado","arma","bomba","viol\u00eancia","conflito","tropas","invas\u00e3o","resist\u00eancia","morte","sangue","destrui\u00e7\u00e3o","paz","armist\u00edcio"]},
    {"id":3,"nome":"Cor","descricao":"Cores e termos crom\u00e1ticos","tags":["vermelho","azul","verde","amarelo","branco","preto","laranja","roxo","rosa","cinza","dourado","prateado","ocre","turquesa","\u00edndigo"]},
    {"id":4,"nome":"Emo\u00e7\u00e3o","descricao":"Estados emocionais e sentimentos","tags":["alegria","tristeza","raiva","medo","surpresa","nojo","amor","\u00f3dio","ang\u00fastia","esperan\u00e7a","melancolia","euforia","serenidade","nostalgia","solid\u00e3o"]},
    {"id":5,"nome":"Natureza","descricao":"Elementos naturais e ambientais","tags":["\u00e1rvore","\u00e1gua","mar","c\u00e9u","montanha","floresta","animal","planta","sol","lua","nuvem","terra","vento","chuva","neve"]},
    {"id":6,"nome":"Arte","descricao":"Termos art\u00edsticos e est\u00e9ticos","tags":["pintura","escultura","desenho","abstrato","realismo","impressionismo","barroco","renascimento","modernismo","cubismo","expressionismo","surrealismo","fotografia","gravura","mosaico"]},
]

def generate_animal_name():
    random.seed()
    return f"{random.choice(ANIMAIS)} {random.choice(ADJETIVOS)}"

# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
# BLOCKCHAIN / CADEIA DE REGISTROS IMUT\u00c1VEL
# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
def compute_hash(data: dict) -> str:
    serialized = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(serialized.encode('utf-8')).hexdigest()

def get_chain():
    return load_json_file(CHAIN_FILE, [])

def get_last_hash():
    chain = get_chain()
    return chain[-1]["hash"] if chain else "0" * 64

def register_event(event_type: str, payload: dict, user_id: str = "system", origin: str = "human"):
    chain = get_chain()
    previous_hash = get_last_hash()
    block = {
        "index": len(chain),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "event_type": event_type,
        "payload": payload,
        "user_id": user_id,
        "origin": origin,
        "previous_hash": previous_hash,
        "status_metadata": "bruto",
    }
    block["hash"] = compute_hash(block)
    chain.append(block)
    save_json_file(CHAIN_FILE, chain)
    return block["hash"]

def verify_chain_integrity():
    chain = get_chain()
    if not chain:
        return True, []
    errors = []
    for i, block in enumerate(chain):
        stored_hash = block.get("hash", "")
        block_copy = {k: v for k, v in block.items() if k != "hash"}
        computed = compute_hash(block_copy)
        if stored_hash != computed:
            errors.append(f"Bloco #{i} corrompido (hash inv\u00e1lido)")
        if i > 0 and block.get("previous_hash") != chain[i-1].get("hash"):
            errors.append(f"Bloco #{i} com refer\u00eancia anterior inv\u00e1lida")
    return len(errors) == 0, errors

# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
# CORE
# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
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

# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
# ORTOGRAFIA / VALIDA\u00c7\u00c3O
# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
DICIONARIO_PT = {
    "guerra","religiao","religi\u00e3o","cor","arte","natureza","amor","paz","luz","sombra",
    "alegria","tristeza","medo","raiva","azul","vermelho","verde","amarelo","branco","preto",
    "laranja","roxo","rosa","cinza","dourado","prateado","ocre","turquesa","indigo","\u00edndigo",
    "arvore","\u00e1rvore","agua","\u00e1gua","mar","ceu","c\u00e9u","montanha","floresta","animal","planta",
    "sol","lua","nuvem","terra","vento","chuva","neve","fogo","pedra","rio","lago","campo",
    "pintura","escultura","desenho","abstrato","realismo","impressionismo","barroco",
    "renascimento","modernismo","cubismo","expressionismo","surrealismo","fotografia",
    "gravura","mosaico","deus","sagrado","fe","f\u00e9","oracao","ora\u00e7\u00e3o","templo","cruz",
    "biblia","b\u00edblia","espirito","esp\u00edrito","ritual","missa","altar","soldado","arma",
    "bomba","violencia","viol\u00eancia","conflito","morte","sangue","destruicao","destrui\u00e7\u00e3o",
    "triste","feliz","belo","bela","forte","fraco","grande","pequeno","antigo","moderno",
    "claro","escuro","quente","frio","velho","novo","bom","mau","bonito","feio","rico","pobre",
    "homem","mulher","crianca","crian\u00e7a","idoso","jovem","adulto","familia","fam\u00edlia",
    "cidade","campo","pais","pa\u00eds","mundo","universo","historia","hist\u00f3ria","tempo","espaco","espa\u00e7o",
}

def check_spelling(tag: str):
    tag_clean = tag.lower().strip()
    tag_clean = re.sub(r'[^a-z\u00e1\u00e9\u00ed\u00f3\u00fa\u00e0\u00e8\u00ec\u00f2\u00f9\u00e2\u00ea\u00ee\u00f4\u00fb\u00e3\u00f5\u00e4\u00eb\u00ef\u00f6\u00fc\u00e7\s]', '', tag_clean)
    words_in_tag = tag_clean.split()
    unknown = []
    for w in words_in_tag:
        if len(w) > 2 and w not in DICIONARIO_PT:
            unknown.append(w)
    return unknown

def levenshtein(s1, s2):
    if len(s1) < len(s2): return levenshtein(s2, s1)
    if len(s2) == 0: return len(s1)
    prev = list(range(len(s2)+1))
    for i, c1 in enumerate(s1):
        curr = [i+1]
        for j, c2 in enumerate(s2):
            curr.append(min(prev[j+1]+1, curr[j]+1, prev[j]+(c1!=c2)))
        prev = curr
    return prev[-1]

def suggest_corrections(word: str):
    suggestions = []
    for known in DICIONARIO_PT:
        dist = levenshtein(word.lower(), known)
        if dist <= 2:
            suggestions.append((known, dist))
    suggestions.sort(key=lambda x: x[1])
    return [s[0] for s in suggestions[:3]]

# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
# SIMILARIDADE
# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
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
                if uniq[i] in uniq[j] or uniq[j] in uniq[i]: tipo = "Conten\u00e7\u00e3o"
                elif shared: tipo = f"Palavra comum: '{', '.join(shared)}'"
                else: tipo = "Similaridade fon\u00e9tica"
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

# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
# ONTOLOGIAS
# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
def load_ontologias():
    return load_json_file(ONTOLOGY_FILE, ONTOLOGIAS_DEFAULT)

def save_ontologias(data):
    return save_json_file(ONTOLOGY_FILE, data)

def match_tag_to_ontology(tag):
    ontologias = load_ontologias()
    matches = []
    for onto in ontologias:
        for ot in onto["tags"]:
            s = sim(tag, ot)
            if s >= 0.7:
                matches.append({"ontologia": onto["nome"], "tag_onto": ot, "score": round(s,3)})
    matches.sort(key=lambda x: x["score"], reverse=True)
    return matches

def classify_tags_by_ontology(tags_list):
    result = defaultdict(list)
    for tag in tags_list:
        matches = match_tag_to_ontology(tag)
        if matches:
            result[matches[0]["ontologia"]].append(tag)
        else:
            result["N\u00e3o Classificado"].append(tag)
    return dict(result)

# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
# CSS
# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
def load_css():
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IM+Fell+English:ital@0;1&family=Poppins:wght@300;400;500;600;700;800&display=swap');
*{margin:0;padding:0;box-sizing:border-box;}
body, .stApp, .stApp *, div, p, span, button, input, textarea, label, h1, h2, h3, h4, h5, h6 {
  font-family:'Times New Roman', 'IM Fell English', Georgia, serif !important;
}
@keyframes bg{0%{background-position:0% 50%}50%{background-position:100% 50%}100%{background-position:0% 50%}}
.stApp{background:linear-gradient(-45deg,#000 0%,#001F3F 25%,#000 50%,#001F3F 75%,#000 100%);
  background-size:400% 400%;animation:bg 15s ease infinite;color:#e0e0e0}

.top-navbar{position:fixed;top:0;left:0;right:0;z-index:9999;
  background:rgba(255,255,255,.1);backdrop-filter:blur(20px) saturate(180%);
  border-bottom:1px solid rgba(255,255,255,.2);padding:1.4rem 3rem;
  display:flex;justify-content:space-between;align-items:center;
  box-shadow:0 8px 32px rgba(0,0,0,.1)}
.navbar-logo{font-size:1.8rem;font-weight:800;font-family:'Times New Roman',Georgia,serif!important;
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
  letter-spacing:-2px;text-shadow:0 4px 20px rgba(0,0,0,.3);font-family:'Times New Roman',Georgia,serif!important}
.subtitle{color:rgba(255,255,255,.95);font-size:1.3rem;text-align:center;margin-bottom:3rem;
  line-height:1.8;font-weight:300;font-family:'Times New Roman',Georgia,serif!important}

.tag-badge{display:inline-block;background:rgba(255,255,255,.25);backdrop-filter:blur(10px);
  border:1px solid rgba(255,255,255,.4);color:white;padding:.5rem 1.1rem;border-radius:50px;
  margin:.3rem;font-size:.88rem;font-weight:600;transition:all .3s}
.tag-badge:hover{background:rgba(255,255,255,.4);transform:translateY(-3px) scale(1.05)}
.tag-green {background:rgba(34,197,94,.25)!important;border-color:rgba(34,197,94,.5)!important;color:#dcfce7!important}
.tag-amber {background:rgba(245,158,11,.25)!important;border-color:rgba(245,158,11,.5)!important;color:#fef3c7!important}
.tag-blue  {background:rgba(96,165,250,.25)!important;border-color:rgba(96,165,250,.5)!important;color:#dbeafe!important}
.tag-red   {background:rgba(239,68,68,.25)!important;border-color:rgba(239,68,68,.5)!important;color:#fee2e2!important}

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
.sc-r{border-left:4px solid #f87171;background:rgba(248,113,113,.07)}

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

/* Blockchain block style */
.block-card{background:rgba(0,255,180,.06);border:1px solid rgba(0,255,180,.22);border-radius:12px;
  padding:.9rem 1.2rem;margin:.3rem 0;font-family:'Times New Roman',monospace!important;font-size:.78rem}
.block-hash{color:#34d399;font-family:'Times New Roman',monospace!important;font-size:.7rem;word-break:break-all}
.block-type{display:inline-block;background:rgba(52,211,153,.2);border:1px solid rgba(52,211,153,.4);
  color:#6ee7b7;padding:.2rem .7rem;border-radius:50px;font-size:.72rem;font-weight:700;margin-bottom:.4rem}
.chain-valid{background:rgba(52,211,153,.15);border:1px solid rgba(52,211,153,.4);border-radius:10px;
  padding:.6rem 1.2rem;color:#6ee7b7;font-weight:700}
.chain-invalid{background:rgba(239,68,68,.15);border:1px solid rgba(239,68,68,.4);border-radius:10px;
  padding:.6rem 1.2rem;color:#fca5a5;font-weight:700}

/* Validation styles */
.val-ok{color:#34d399;font-weight:700}
.val-err{color:#f87171;font-weight:700}
.val-warn{color:#fbbf24;font-weight:700}
.status-pill{display:inline-block;padding:.2rem .8rem;border-radius:50px;font-size:.72rem;font-weight:700;margin:.1rem}
.status-bruto{background:rgba(156,163,175,.2);border:1px solid rgba(156,163,175,.4);color:#d1d5db}
.status-sugerido{background:rgba(96,165,250,.2);border:1px solid rgba(96,165,250,.4);color:#bfdbfe}
.status-validado{background:rgba(52,211,153,.2);border:1px solid rgba(52,211,153,.4);color:#6ee7b7}
.status-revisado{background:rgba(251,191,36,.2);border:1px solid rgba(251,191,36,.4);color:#fde68a}
.status-publicado{background:rgba(167,139,250,.2);border:1px solid rgba(167,139,250,.4);color:#ddd6fe}

/* Ontology */
.onto-card{background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.15);border-radius:14px;
  padding:1.2rem 1.4rem;margin:.5rem 0;transition:all .3s}
.onto-card:hover{background:rgba(255,255,255,.14);transform:translateY(-3px)}
.onto-name{font-size:1.1rem;font-weight:700;color:#a7e6ff;margin-bottom:.4rem}
.onto-desc{font-size:.82rem;color:rgba(255,255,255,.6);margin-bottom:.6rem}

/* Graph */
.graph-container{background:rgba(0,0,0,.4);border:1px solid rgba(255,255,255,.15);border-radius:18px;
  padding:1rem;margin:1rem 0;min-height:400px;position:relative}

/* Accessibility */
.acessibility-bar{background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.2);
  border-radius:12px;padding:.8rem 1.4rem;margin:.5rem 0;display:flex;align-items:center;gap:1rem;flex-wrap:wrap}
.audiodesc-box{background:rgba(167,230,255,.1);border:1px solid rgba(167,230,255,.3);border-radius:14px;
  padding:1.4rem;margin:1rem 0;color:white;line-height:1.8;font-size:1rem}
.audiodesc-title{color:#a7e6ff;font-weight:700;font-size:1.1rem;margin-bottom:.6rem}

/* Open data */
.opendata-card{background:rgba(52,211,153,.07);border:1px solid rgba(52,211,153,.2);border-radius:14px;
  padding:1.2rem 1.5rem;margin:.5rem 0}

.stButton button{background:rgba(255,255,255,.25)!important;backdrop-filter:blur(15px)!important;
  color:white!important;border:1px solid rgba(255,255,255,.4)!important;border-radius:50px!important;
  padding:1rem 2.5rem!important;font-weight:700!important;font-size:1rem!important;
  transition:all .4s!important;box-shadow:0 8px 25px rgba(0,0,0,.15)!important;
  text-transform:uppercase;letter-spacing:1px;font-family:'Times New Roman',Georgia,serif!important}
.stButton button:hover{background:rgba(255,255,255,.4)!important;
  box-shadow:0 12px 40px rgba(0,31,63,.4)!important;
  transform:translateY(-4px) scale(1.05)!important;border-color:rgba(255,255,255,.6)!important}

.stTextInput input,.stTextArea textarea,.stSelectbox select{
  background:rgba(255,255,255,.18)!important;backdrop-filter:blur(10px)!important;
  border:1px solid rgba(255,255,255,.28)!important;color:white!important;
  border-radius:14px!important;padding:.9rem!important;font-weight:500!important;
  font-family:'Times New Roman',Georgia,serif!important}
.stTextInput input::placeholder,.stTextArea textarea::placeholder{color:rgba(255,255,255,.55)!important}
.stTextInput input:focus,.stTextArea textarea:focus{
  border-color:rgba(255,255,255,.6)!important;box-shadow:0 0 0 3px rgba(255,255,255,.18)!important}

label{color:white!important;font-weight:700!important;font-size:1rem!important;
  text-shadow:0 2px 10px rgba(0,0,0,.2);font-family:'Times New Roman',Georgia,serif!important}

.stTabs [data-baseweb="tab-list"]{gap:.7rem;background:rgba(255,255,255,.1);
  backdrop-filter:blur(10px);padding:.45rem;border-radius:14px}
.stTabs [data-baseweb="tab"]{background:rgba(255,255,255,.14);
  border:1px solid rgba(255,255,255,.18);border-radius:10px;color:white;
  padding:.75rem 1.5rem;font-weight:700;transition:all .3s;font-family:'Times New Roman',Georgia,serif!important}
.stTabs [data-baseweb="tab"]:hover{background:rgba(255,255,255,.24);transform:translateY(-2px)}
.stTabs [aria-selected="true"]{background:rgba(255,255,255,.33)!important;
  border-color:rgba(255,255,255,.48)!important;box-shadow:0 6px 20px rgba(0,31,63,.25)!important}

.stAlert{background:rgba(255,255,255,.18)!important;backdrop-filter:blur(15px)!important;
  border-radius:14px!important;border-left:4px solid!important;color:white!important}
#MainMenu,footer,header{visibility:hidden}
.stDeployButton{display:none}
[data-testid="stSidebar"]{display:none}
h1,h2,h3,h4,h5,h6{color:white;font-weight:700;text-shadow:0 2px 15px rgba(0,0,0,.3);font-family:'Times New Roman',Georgia,serif!important}
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

# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
# HELPERS
# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
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

def status_pill(status):
    return f"<span class='status-pill status-{status}'>{status.upper()}</span>"

# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
# DADOS
# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
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
         "imagem":"https://upload.wikimedia.org/wikipedia/en/7/74/PicassoGuernica.jpg",
         "audiodescricao":"Guernica \u00e9 uma obra monumental de Pablo Picasso, pintada em 1937 em \u00f3leo sobre tela, medindo aproximadamente 3,49 metros de altura por 7,76 metros de largura. A paleta \u00e9 completamente monocrom\u00e1tica, em tons de cinza, preto e branco, transmitindo a aus\u00eancia de vida e cor em meio ao caos da guerra. No centro da composi\u00e7\u00e3o, uma mulher segura um beb\u00ea morto, com o rosto virado para cima em grito de desespero. \u00c0 esquerda, um touro est\u00e1 de p\u00e9, s\u00edmbolo de brutalidade. Ao centro, um cavalo ferido relincha em agonia, com a l\u00edngua em forma de punhal. Uma l\u00e2mpada el\u00e9trica em forma de olho ilumina a cena no topo, como um olho vigilante e impiedoso. Figuras humanas fragmentadas, membros decepados e rostos deformados comp\u00f5em uma cena de horror e lamento coletivo. A obra \u00e9 uma den\u00fancia ao bombardeio da cidade basca de Guernica durante a Guerra Civil Espanhola."},
        {"id":2,"titulo":"A Noite Estrelada","artista":"Vincent van Gogh","ano":"1889",
         "imagem":"https://upload.wikimedia.org/wikipedia/commons/thumb/e/ea/Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg/1200px-Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg",
         "audiodescricao":"A Noite Estrelada foi pintada por Vincent van Gogh em junho de 1889, durante sua interna\u00e7\u00e3o no asilo de Saint-Paul-de-Mausole, em Saint-R\u00e9my-de-Provence. \u00c9 uma obra a \u00f3leo sobre tela de dimens\u00f5es 73,7 cm por 92,1 cm. O c\u00e9u ocupa cerca de dois ter\u00e7os da tela e \u00e9 dominado por redemoinhos de azul profundo e turquesa, com estrelas que irradiam halos de luz amarela e branca. Uma lua crescente brilha intensamente no canto superior direito. O movimento das pinceladas cria uma sensa\u00e7\u00e3o de fluxo cont\u00ednuo, quase auditivo, como se o c\u00e9u estivesse em constante turbul\u00eancia. Na parte inferior, uma vila tranquila com casas de telhados escuros e uma igreja com campan\u00e1rio pontiagudo contrasta com a agita\u00e7\u00e3o celestial. \u00c0 esquerda, um cipreste negro e sinuoso se eleva como uma chama s\u00f3lida, conectando terra e c\u00e9u. A obra transmite ao mesmo tempo beleza e inquieta\u00e7\u00e3o interior, sendo um dos maiores \u00edcones da arte ocidental."},
        {"id":3,"titulo":"Mona Lisa","artista":"Leonardo da Vinci","ano":"1503",
         "imagem":"https://upload.wikimedia.org/wikipedia/commons/thumb/e/ec/Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_retouched.jpg/800px-Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_retouched.jpg",
         "audiodescricao":"A Mona Lisa \u00e9 uma pintura a \u00f3leo sobre painel de madeira de \u00e1lamo, criada por Leonardo da Vinci entre 1503 e 1519, medindo 77 cm de altura por 53 cm de largura. Representa uma mulher de meia-idade sentada em posi\u00e7\u00e3o de tr\u00eas quartos, com as m\u00e3os postas gentilmente sobre os bra\u00e7os de uma cadeira. Seu rosto apresenta a famosa express\u00e3o enigm\u00e1tica, com um sorriso sutil que parece se modificar conforme o \u00e2ngulo de observa\u00e7\u00e3o \u2014 fruto da t\u00e9cnica de sfumato utilizada por Leonardo, que dissolve contornos em suaves grada\u00e7\u00f5es tonais. Os cabelos escuros est\u00e3o cobertos por um v\u00e9u transl\u00facido. O traje \u00e9 de cor escura com detalhes esverdeados. Ao fundo, uma paisagem de montanhas, vales e um lago se estende em n\u00e9voa azulada, criando profundidade por meio da perspectiva atmosf\u00e9rica. A aus\u00eancia de sobrancelhas vis\u00edveis e o olhar direto e penetrante contribuem para o mist\u00e9rio da obra. Pertence ao acervo do Museu do Louvre, em Paris, onde \u00e9 a obra mais visitada do mundo."}
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
    register_event("questionario_respondido", {"user_id":uid,"animal":animal}, uid, "human")
    return save_json_file(USERS_FILE, users)

def save_tag(uid, obra_id, tag):
    tags = load_json_file(TAGS_FILE, [])
    tag_id = len(tags) + 1
    spell_errors = check_spelling(tag)
    onto_matches = match_tag_to_ontology(tag)
    onto_name = onto_matches[0]["ontologia"] if onto_matches else "N\u00e3o Classificado"
    entry = {
        "id": tag_id,
        "user_id": uid,
        "obra_id": obra_id,
        "tag": tag.lower().strip(),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "bruto",
        "origin": "human",
        "spell_errors": spell_errors,
        "ontologia": onto_name,
        "historico": [],
        "validado_por": None,
        "validado_em": None,
    }
    tags.append(entry)
    register_event("tag_criada", {"tag_id":tag_id,"tag":tag,"obra_id":obra_id,"ontologia":onto_name,"spell_errors":spell_errors}, uid, "human")
    st.cache_data.clear()
    return save_json_file(TAGS_FILE, tags)

def update_tag_status(tag_id, new_status, admin_user="admin"):
    tags = load_json_file(TAGS_FILE, [])
    for t in tags:
        if t["id"] == tag_id:
            old_status = t.get("status","bruto")
            t.setdefault("historico", []).append({
                "status_anterior": old_status,
                "status_novo": new_status,
                "alterado_por": admin_user,
                "alterado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            })
            t["status"] = new_status
            t["validado_por"] = admin_user
            t["validado_em"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            register_event("status_tag_alterado", {"tag_id":tag_id,"de":old_status,"para":new_status}, admin_user, "human")
            break
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

# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
# EXPORTA\u00c7\u00c3O HTML
# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
def html_quest(uid, animal, users_df):
    if users_df.empty: return None
    ud = users_df[users_df['user_id']==uid]
    if ud.empty: return None
    ui = ud.iloc[0]
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<style>*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Times New Roman',Georgia,serif;background:linear-gradient(135deg,#000,#001F3F);padding:40px;color:white}}
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
<body><div class="c"><h1>Respostas do Question\u00e1rio</h1>
<div class="hi">
  <p>Usu\u00e1rio An\u00f4nimo: <span class="ab">\ud83d\udc3e {animal}</span></p>
  <p style="margin-top:6px;opacity:.65">Data: {ui.get('timestamp','N/A')}</p>
</div>
<div class="qb"><div class="q">1. N\u00edvel de familiaridade com museus</div>
<div class="a">{ui.get('q1','N/A')}</div></div>
<div class="qb"><div class="q">2. Conhecimento sobre documenta\u00e7\u00e3o museol\u00f3gica</div>
<div class="a">{ui.get('q2','N/A')}</div></div>
<div class="qb"><div class="q">3. O que voc\u00ea entende por 'tags'?</div>
<div class="a">{ui.get('q3','N/A')}</div></div>
<div class="ft">Sistema Folksonomia Digital \u2014 Ctrl+P \u2192 Salvar como PDF</div>
</div></body></html>"""

def html_tags(uid, animal, obras, tags_df):
    ut = tags_df[tags_df['user_id']==uid] if not tags_df.empty else pd.DataFrame()
    if ut.empty: return None
    od = {o['id']:o for o in obras}
    rows = "".join(
        f"<tr><td>{i+1}</td>"
        f"<td>{od.get(r['obra_id'],{}).get('titulo','Obra '+str(r['obra_id']))}</td>"
        f"<td><span style='background:rgba(255,255,255,.22);padding:3px 10px;border-radius:50px'>{r['tag']}</span></td>"
        f"<td>{r.get('status','bruto')}</td>"
        f"<td>{r['timestamp']}</td></tr>"
        for i,(_,r) in enumerate(ut.iterrows())
    )
    top = "".join(
        f"<tr><td>{i}</td><td>{t}</td><td>{c}</td></tr>"
        for i,(t,c) in enumerate(ut['tag'].value_counts().head(10).items(),1)
    )
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<style>*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Times New Roman',Georgia,serif;background:linear-gradient(135deg,#000,#001F3F);padding:40px;color:white}}
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
<body><div class="c"><h1>Relat\u00f3rio de Tags</h1>
<div class="hi">
  <p>Usu\u00e1rio An\u00f4nimo: <span class="ab">\ud83d\udc3e {animal}</span></p>
  <p style="margin-top:6px;opacity:.65">Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
</div>
<div class="stats">
  <div class="sb"><div class="sv">{len(ut)}</div><div class="sl">Total de Tags</div></div>
  <div class="sb"><div class="sv">{ut['tag'].nunique()}</div><div class="sl">Tags \u00danicas</div></div>
  <div class="sb"><div class="sv">{ut['obra_id'].nunique()}</div><div class="sl">Obras Etiquetadas</div></div>
</div>
<h2 style="margin:28px 0 14px;font-size:1.5rem">Todas as Tags</h2>
<table><thead><tr><th>#</th><th>Obra</th><th>Tag</th><th>Status</th><th>Data/Hora</th></tr></thead>
<tbody>{rows}</tbody></table>
<h2 style="margin:28px 0 14px;font-size:1.5rem">Top 10 Tags</h2>
<table><thead><tr><th>Pos.</th><th>Tag</th><th>Freq.</th></tr></thead>
<tbody>{top}</tbody></table>
<div class="ft">Sistema Folksonomia Digital \u2014 Ctrl+P \u2192 Salvar como PDF</div>
</div></body></html>"""

# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
# INTERFACE PRINCIPAL
# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
def show_header():
    st.markdown(
        "<div class='top-navbar'>"
        "<div class='navbar-logo'>Sistema Folksonomia Digital</div>"
        "</div>", unsafe_allow_html=True)

def main():
    load_css()
    try: check_admin()
    except Exception as e: st.error(f"Erro ao inicializar: {e}")

    for k,v in [('user_id',gen_uid()),('animal_name',generate_animal_name()),
                ('step','intro'),('answers',{}),
                ('font_size','normal'),('contrast_mode','normal'),('theme','dark')]:
        if k not in st.session_state: st.session_state[k] = v

    if st.session_state['step'] != 'completed':
        show_intro()
    else:
        show_header()
        st.markdown("<div class='main-content'>", unsafe_allow_html=True)
        t1, t2 = st.tabs([" Explorar Obras"," \u00c1rea Administrativa"])
        with t1: show_obras()
        with t2: show_admin()
        st.markdown("</div>", unsafe_allow_html=True)

# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
# INTRO COM BLOCKCHAIN NO PRIMEIRO ENVIO
# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
def show_intro():
    st.markdown("<div class='main-content'>", unsafe_allow_html=True)
    st.markdown("<h1 class='main-title'>Sistema Folksonomia Digital</h1>", unsafe_allow_html=True)
    st.markdown("<p class='subtitle'>Sistema colaborativo de cataloga\u00e7\u00e3o de obras de arte<br>"
                "Complete o question\u00e1rio para acessar a plataforma</p>", unsafe_allow_html=True)

    # Exibir status do blockchain
    chain = get_chain()
    valid, errs = verify_chain_integrity()
    chain_status = f"<span class='chain-valid'>\ud83d\udd17 Cadeia \u00edntegra \u2014 {len(chain)} registro(s)</span>" if valid else f"<span class='chain-invalid'>\u26a0\ufe0f {len(errs)} erro(s) na cadeia</span>"
    st.markdown(f"<div style='text-align:center;margin-bottom:1.5rem'>{chain_status}</div>", unsafe_allow_html=True)

    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.markdown("<h2 style='text-align:center;margin-bottom:2.2rem;font-size:1.7rem'>"
                "Question\u00e1rio de Acesso</h2>", unsafe_allow_html=True)

    st.markdown("""<div class='insight'>
<strong>\ud83d\udd17 Registro Imut\u00e1vel:</strong> Ao enviar este formul\u00e1rio, sua participa\u00e7\u00e3o ser\u00e1 registrada 
na cadeia de eventos com hash criptogr\u00e1fico SHA-256, garantindo integridade, rastreabilidade e 
prova de altera\u00e7\u00e3o. Cada evento recebe um identificador \u00fanico e refer\u00eancia ao estado anterior.
</div>""", unsafe_allow_html=True)

    with st.form("intro_form"):
        c1, c2 = st.columns(2)
        with c1:
            q1 = st.selectbox("1. Qual \u00e9 o seu n\u00edvel de familiaridade com museus?",
                ["Nunca visito museus","Visito raramente","Visito ocasionalmente","Visito frequentemente"])
            q2 = st.selectbox("2. Voc\u00ea j\u00e1 ouviu falar sobre documenta\u00e7\u00e3o museol\u00f3gica?",
                ["Nunca ouvi falar","J\u00e1 ouvi, mas n\u00e3o sei o que \u00e9","Tenho uma ideia b\u00e1sica","Conhe\u00e7o bem o tema"])
        with c2:
            q3 = st.text_area("3. O que voc\u00ea entende por 'tags' ou etiquetas digitais aplicadas a acervo?",
                max_chars=500, height=200, placeholder="Descreva sua compreens\u00e3o sobre o conceito...")
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
                # Registrar na blockchain
                block_hash = register_event(
                    "acesso_sistema",
                    {
                        "animal": st.session_state['animal_name'],
                        "q1": q1, "q2": q2,
                        "q3_palavras": len(q3.split()),
                        "proveniencia": "formulario_acesso",
                    },
                    st.session_state['user_id'],
                    "human"
                )
                st.session_state['step'] = 'completed'
                st.session_state['entry_hash'] = block_hash
                st.success(f"\u2705 Question\u00e1rio completo! Acesso liberado.")
                st.code(f"Hash do registro: {block_hash}", language=None)
                st.balloons()
                st.rerun()
    st.markdown("</div></div>", unsafe_allow_html=True)

# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
# GALERIA COM ACESSIBILIDADE
# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
def show_obras():
    st.markdown("<h1 class='main-title'>Galeria de Obras de Arte</h1>", unsafe_allow_html=True)
    st.markdown("<p class='subtitle'>Explore as obras e contribua com suas tags descritivas</p>",
                unsafe_allow_html=True)

    # \u2500\u2500 Barra de Acessibilidade \u2500\u2500
    st.markdown("<div class='acessibility-bar'>", unsafe_allow_html=True)
    st.markdown("**\u267f Acessibilidade:**", unsafe_allow_html=True)
    acc1, acc2, acc3, acc4 = st.columns([1,1,1,2])
    with acc1:
        font_size = st.selectbox("Tamanho de Texto:", ["Normal","Grande","Muito Grande"], key="acc_font")
    with acc2:
        contrast  = st.selectbox("Contraste:",        ["Normal","Alto Contraste"],        key="acc_contrast")
    with acc3:
        theme     = st.selectbox("Tema:",             ["Escuro","Claro"],                  key="acc_theme")
    with acc4:
        show_audio = st.checkbox("\ud83c\udfa7 Exibir Audiodescri\u00e7\u00e3o das Obras", value=False, key="acc_audio")
    st.markdown("</div>", unsafe_allow_html=True)

    # Aplicar ajustes de acessibilidade dinamicamente
    font_map = {"Normal":"1rem","Grande":"1.25rem","Muito Grande":"1.5rem"}
    fsize = font_map.get(font_size,"1rem")
    if contrast == "Alto Contraste":
        st.markdown("""<style>
.stApp{filter:contrast(1.6) brightness(1.1)!important}
.tag-badge{background:rgba(255,255,255,.7)!important;color:#000!important;border-color:#fff!important}
</style>""", unsafe_allow_html=True)
    if theme == "Claro":
        st.markdown("""<style>
.stApp{background:linear-gradient(-45deg,#f0f4ff 0%,#e8f0fe 25%,#f5f0ff 50%,#e8f0fe 75%,#f0f4ff 100%)!important;color:#111!important}
h1,h2,h3,h4,h5,h6,label,p,span,.subtitle{color:#111!important;text-shadow:none!important}
.main-title{color:#001F3F!important}
.kpi-card,.glass-card,.obra-card,.tag-badge{background:rgba(0,31,63,.12)!important;border-color:rgba(0,31,63,.3)!important}
.insight{background:rgba(0,31,63,.08)!important;color:#111!important}
.stTextInput input,.stTextArea textarea{color:#111!important;background:rgba(0,31,63,.1)!important}
</style>""", unsafe_allow_html=True)
    if fsize != "1rem":
        st.markdown(f"""<style>
body,.stApp,.stApp *{{font-size:{fsize}!important}}
.main-title{{font-size:calc(3.5rem * {1 if fsize=='1rem' else 1.15 if fsize=='1.25rem' else 1.3})!important}}
</style>""", unsafe_allow_html=True)

    obras = load_obras()
    if not obras:
        st.info("Nenhuma obra cadastrada.")
        return

    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    c1, c2 = st.columns([2,1])
    with c1:
        sid = st.text_input("Filtrar por n\u00famero da obra:", "", placeholder="Ex: 1, 2, 3\u2026")
    with c2:
        sord = st.selectbox("Ordenar por:", ["N\u00famero (crescente)","N\u00famero (decrescente)"])
    st.markdown("</div>", unsafe_allow_html=True)

    filtered = obras
    if sid.strip().isdigit():
        filtered = [o for o in obras if str(o['id'])==sid.strip()]
    filtered = sorted(filtered, key=lambda x: x['id'], reverse=(sord=="N\u00famero (decrescente)"))

    st.markdown(f"<div style='text-align:center;color:white;margin:1.8rem 0;"
                f"font-size:1.1rem;font-weight:600'>Exibindo "
                f"<strong style='font-size:1.4rem'>{len(filtered)}</strong> obra(s)</div>",
                unsafe_allow_html=True)

    cols = st.columns(3)
    for i, obra in enumerate(filtered):
        with cols[i%3]:
            st.markdown(f"""<div class='obra-card'>
<img src='{obra['imagem']}' alt='Obra {obra['id']}: {obra.get("titulo","")}, {obra.get("artista","")}, {obra.get("ano","")}' />
<div style='padding:1.4rem'>
  <h3 style='font-size:1.05rem;font-weight:700;margin-bottom:.35rem'>Obra #{obra['id']}: {obra.get('titulo','')}</h3>
  <p style='font-size:.85rem;opacity:.65;margin-bottom:.3rem'>{obra.get('artista','')} \u2014 {obra.get('ano','')}</p>
  <p style='font-size:.88rem;opacity:.65'>Adicione uma tag descritiva para esta imagem</p>
</div></div>""", unsafe_allow_html=True)

            # Audiodescri\u00e7\u00e3o
            if show_audio and obra.get('audiodescricao'):
                st.markdown(
                    f"<div class='audiodesc-box'>"
                    f"<div class='audiodesc-title'>\ud83c\udfa7 Audiodescri\u00e7\u00e3o</div>"
                    f"<p