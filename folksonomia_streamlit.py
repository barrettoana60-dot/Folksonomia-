import streamlit as st
import sqlite3
import pandas as pd
import numpy as np
import os
import io
import re
import json
import math
import base64
import hashlib
import random
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

st.set_page_config(page_title="Folksonomia", layout="wide", initial_sidebar_state="collapsed")

APP_TITLE = "Folksonomia"
DB_PATH = "folksonomia.db"
ADMIN_LOGIN = os.getenv("FOLKSONOMIA_ADMIN_LOGIN", "Artemis289@")
ADMIN_PASSWORD = os.getenv("FOLKSONOMIA_ADMIN_PASSWORD", "nugep239@")

ANIMAIS = ["Águia","Boto","Capivara","Doninha","Ema","Falcão","Gavião","Harpia","Irara","Jaguar","Lontra","Mico","Onça","Paca","Quati","Raposa","Tamanduá","Urubu","Veado","Zorrilho","Arara","Bugio","Caititu","Jaguatirica","Lobo","Mutum","Pirarucu","Tucano","Sucuri","Tatu"]
ADJETIVOS = ["Sereno","Nobre","Claro","Sutil","Firme","Elegante","Veloz","Brando","Preciso","Silencioso","Curioso","Vívido","Lúcido","Distinto","Suave","Altivo","Brilhante","Calmo","Furtivo","Raro"]
STOPWORDS_PT = {"de","da","do","das","dos","e","o","a","os","as","um","uma","uns","umas","para","por","com","sem","sob","sobre","entre","na","no","nas","nos","ao","aos","que","em","como","mais","menos","muito","pouco","ser","estar","ter","ou","se"}
VOCAB_BASE = {"azulado":"azul","azul escuro":"azul","azul claro":"azul","avermelhado":"vermelho","esverdeado":"verde","amarelado":"amarelo","dourada":"dourado","dourado":"dourado","sombrio":"escuro","obscuro":"escuro","melancolica":"melancólico","melancolico":"melancólico","tristonho":"triste","alegria":"alegre","feliz":"alegre","velocidade":"movimento","dinamismo":"movimento","religioso":"religião","sagrado":"religião","bélico":"guerra","guerreiro":"guerra","feminina":"feminino","masculina":"masculino","floral":"flor","botânico":"natureza","natural":"natureza","animal":"fauna","humano":"figura humana","retrato":"figura humana","rostos":"rosto","faces":"rosto"}
TERMOS_DIFICEIS = {"ontologia":"estrutura conceitual usada para organizar entidades e relações entre termos","desambiguação":"processo de decidir qual significado ou entidade correta um nome representa","curatorial":"relativo à curadoria, à seleção, interpretação e organização de conteúdos","semântica":"relativa ao significado das palavras, conceitos e relações","vocabulário controlado":"lista padronizada de termos preferenciais para evitar variações desnecessárias"}

def inject_theme():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;500;600;700&family=Inter:wght@300;400;500;600;700&display=swap');
    :root { --text:#171717; }
    html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; color: var(--text); }
    .stApp { background: radial-gradient(circle at 10% 20%, rgba(255,255,255,0.98), rgba(245,245,245,0.95) 35%, rgba(232,232,232,0.95) 100%), linear-gradient(180deg, #f7f7f7, #efefef); color: var(--text); }
    h1, h2, h3, h4, h5, h6 { font-family: 'Cormorant Garamond', serif !important; letter-spacing: -0.02em; color: #111 !important; }
    .glass-card { background: linear-gradient(180deg, rgba(255,255,255,0.42), rgba(255,255,255,0.22)); border: 1px solid rgba(255,255,255,0.78); backdrop-filter: blur(22px) saturate(180%); border-radius: 32px; padding: 1.35rem; margin: 0.55rem 0 1rem 0; box-shadow: 0 12px 40px rgba(0,0,0,0.08); }
    .metric-box { background: linear-gradient(180deg, rgba(255,255,255,0.46), rgba(255,255,255,0.24)); border: 1px solid rgba(255,255,255,0.82); backdrop-filter: blur(20px); border-radius: 24px; box-shadow: 0 12px 40px rgba(0,0,0,0.08); padding: 1.1rem 1rem; min-height: 126px; }
    .metric-label { font-size: 0.78rem; color: rgba(20,20,20,0.58); text-transform: uppercase; letter-spacing: 0.15em; font-weight: 700; }
    .metric-value { font-family: 'Cormorant Garamond', serif !important; font-size: 2.6rem; font-weight: 700; color: #111; margin-top: 0.2rem; }
    .metric-sub { font-size: 0.82rem; color: rgba(20,20,20,0.55); margin-top: 0.1rem; }
    .section-title { font-size: 2.1rem; margin-bottom: 0.35rem; }
    .section-subtitle { color: rgba(20,20,20,0.55); line-height: 1.8; font-size: 0.98rem; }
    .tag-pill { display: inline-block; padding: 0.45rem 0.86rem; border-radius: 999px; background: rgba(255,255,255,0.38); border: 1px solid rgba(255,255,255,0.78); color: rgba(20,20,20,0.72); font-size: 0.84rem; margin: 0.15rem; }
    .insight { background: linear-gradient(180deg, rgba(255,255,255,0.40), rgba(255,255,255,0.18)); border: 1px solid rgba(255,255,255,0.80); border-radius: 22px; padding: 1rem 1.05rem; color: rgba(20,20,20,0.74); line-height: 1.75; box-shadow: 0 12px 40px rgba(0,0,0,0.08); }
    .stButton button, .stDownloadButton button { background: linear-gradient(180deg, rgba(255,255,255,0.60), rgba(255,255,255,0.32)) !important; color: #121212 !important; border: 1px solid rgba(255,255,255,0.85) !important; border-radius: 999px !important; box-shadow: 0 12px 40px rgba(0,0,0,0.08) !important; backdrop-filter: blur(18px) !important; padding: 0.75rem 1.2rem !important; font-weight: 600 !important; }
    .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] > div, .stMultiSelect div[data-baseweb="select"] > div, .stNumberInput input { background: rgba(255,255,255,0.32) !important; border: 1px solid rgba(255,255,255,0.82) !important; border-radius: 18px !important; box-shadow: 0 12px 40px rgba(0,0,0,0.08) !important; color: #111 !important; backdrop-filter: blur(18px) !important; }
    .stTabs [data-baseweb="tab-list"] { gap: 0.5rem; background: rgba(255,255,255,0.24); border: 1px solid rgba(255,255,255,0.74); border-radius: 22px; padding: 0.4rem; backdrop-filter: blur(18px); }
    .stTabs [data-baseweb="tab"] { border-radius: 999px; background: rgba(255,255,255,0.20); color: rgba(20,20,20,0.72); border: 1px solid rgba(255,255,255,0.50); padding: 0.65rem 1rem; }
    .stTabs [aria-selected="true"] { background: rgba(255,255,255,0.62) !important; color: #111 !important; border: 1px solid rgba(255,255,255,0.90) !important; box-shadow: 0 12px 40px rgba(0,0,0,0.08) !important; }
    #MainMenu, footer, header { visibility: hidden; }
    [data-testid="stSidebar"] { display: none; }
    </style>
    """, unsafe_allow_html=True)

def now_str(): return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
def sha256_text(text): return hashlib.sha256(text.encode("utf-8")).hexdigest()
def generate_uid(): return base64.urlsafe_b64encode(os.urandom(12)).decode("utf-8").replace("=", "")
def generate_animal_name(): return f"{random.choice(ANIMAIS)} {random.choice(ADJETIVOS)}"
def normalize_text(text): return re.sub(r"\s+", " ", (text or "").strip().lower())
def tokenize(text): return [t for t in re.findall(r"[a-zA-ZÀ-ÿ0-9-]+", normalize_text(text)) if t not in STOPWORDS_PT]

def normalize_tag(tag):
    base = normalize_text(tag)
    if base in VOCAB_BASE: return VOCAB_BASE[base], 0.95
    toks = tokenize(base)
    for tk in toks:
        if tk in VOCAB_BASE: return VOCAB_BASE[tk], 0.85
    repl = {"ç":"c","ã":"a","á":"a","à":"a","â":"a","é":"e","ê":"e","í":"i","ó":"o","ô":"o","õ":"o","ú":"u"}
    for k,v in repl.items(): base = base.replace(k,v)
    return base, 0.62

def infer_semantic_category(tag_norm):
    mapping = {"azul":"cor","vermelho":"cor","verde":"cor","amarelo":"cor","dourado":"cor","escuro":"luminosidade","claro":"luminosidade","triste":"emoção","alegre":"emoção","melancólico":"emoção","guerra":"tema","religião":"tema","natureza":"tema","fauna":"tema","movimento":"dinâmica","figura humana":"representação","rosto":"representação","feminino":"gênero representado","masculino":"gênero representado","flor":"elemento"}
    return mapping.get(tag_norm, "livre")

def soft_similarity(a, b):
    a = normalize_text(a); b = normalize_text(b)
    if not a or not b: return 0.0
    if a == b: return 1.0
    if a in b or b in a: return 0.82
    sa, sb = set(tokenize(a)), set(tokenize(b))
    if sa or sb:
        inter = len(sa & sb); union = len(sa | sb)
        if union > 0: return inter / union
    return 0.0

def extract_entities(text):
    tokens = re.findall(r"\b[A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][a-záàâãéêíóôõúç]+(?:\s+[A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][a-záàâãéêíóôõúç]+)*", text or "")
    return list(dict.fromkeys([t.strip() for t in tokens if len(t.strip()) > 2]))

def simplify_text(text):
    out = text or ""
    for termo, definicao in TERMOS_DIFICEIS.items():
        out = re.sub(rf"\b{re.escape(termo)}\b", f"{termo} ({definicao})", out, flags=re.IGNORECASE)
    return out

def describe_image_from_metadata(obra):
    return ". ".join([f"Título: {obra.get('titulo','sem título')}", f"Artista: {obra.get('artista','não informado')}", f"Ano: {obra.get('ano','não informado')}", f"Descrição: {obra.get('descricao','sem descrição')}"])

def get_conn(): return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = get_conn(); cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS admins (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password_hash TEXT, created_at TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, user_uid TEXT UNIQUE, animal_name TEXT, q1 TEXT, q2 TEXT, q3 TEXT, created_at TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS obras (id INTEGER PRIMARY KEY AUTOINCREMENT, titulo TEXT, artista TEXT, ano TEXT, imagem TEXT, descricao TEXT, texto_curatorial TEXT, cronologia TEXT, tecnica TEXT, material TEXT, origem TEXT, created_at TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS tags (id INTEGER PRIMARY KEY AUTOINCREMENT, user_uid TEXT, obra_id INTEGER, tag_original TEXT, tag_normalizada TEXT, categoria_semantica TEXT, confianca REAL, origem TEXT, created_at TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS relacoes (id INTEGER PRIMARY KEY AUTOINCREMENT, origem_tipo TEXT, origem_id TEXT, destino_tipo TEXT, destino_id TEXT, relacao TEXT, peso REAL, created_at TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS validacoes (id INTEGER PRIMARY KEY AUTOINCREMENT, item_tipo TEXT, item_id TEXT, acao TEXT, observacao TEXT, validado_por TEXT, created_at TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS automacoes (id INTEGER PRIMARY KEY AUTOINCREMENT, titulo TEXT, tipo TEXT, payload TEXT, status TEXT, created_at TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS acessibilidade (id INTEGER PRIMARY KEY AUTOINCREMENT, user_uid TEXT, font_scale REAL, high_contrast INTEGER, simplificar_textos INTEGER, audio_descricao INTEGER, created_at TEXT, updated_at TEXT)")
    conn.commit()
    if cur.execute("SELECT COUNT(*) FROM admins").fetchone()[0] == 0:
        cur.execute("INSERT INTO admins (username, password_hash, created_at) VALUES (?, ?, ?)", (ADMIN_LOGIN, sha256_text(ADMIN_PASSWORD), now_str())); conn.commit()
    if cur.execute("SELECT COUNT(*) FROM obras").fetchone()[0] == 0:
        obras_seed = [
            ("Guernica","Pablo Picasso","1937","https://upload.wikimedia.org/wikipedia/en/7/74/PicassoGuernica.jpg","Pintura de grande escala associada ao trauma da guerra.","A obra articula sofrimento, fragmentação, violência e impacto político por meio de uma composição densa e expressiva.","1937 — Guerra Civil Espanhola","Óleo sobre tela","Tela","Espanha",now_str()),
            ("A Noite Estrelada","Vincent van Gogh","1889","https://upload.wikimedia.org/wikipedia/commons/thumb/e/ea/Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg/1200px-Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg","Paisagem noturna de forte intensidade cromática.","A pintura enfatiza ritmo, movimento celeste, vibração luminosa e sensibilidade atmosférica.","1889 — Saint-Rémy","Óleo sobre tela","Tela","Países Baixos / França",now_str()),
            ("Mona Lisa","Leonardo da Vinci","1503","https://upload.wikimedia.org/wikipedia/commons/thumb/e/ec/Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_retouched.jpg/800px-Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_retouched.jpg","Retrato icônico da tradição renascentista.","A obra articula retrato, enigma, equilíbrio compositivo e refinamento técnico da pintura renascentista.","c. 1503 — Renascimento","Óleo sobre madeira","Madeira","Itália",now_str())]
        cur.executemany("INSERT INTO obras (titulo, artista, ano, imagem, descricao, texto_curatorial, cronologia, tecnica, material, origem, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", obras_seed)
        conn.commit()
    conn.close()

def login_ok(username, password):
    conn = get_conn(); cur = conn.cursor(); row = cur.execute("SELECT username, password_hash FROM admins WHERE username = ?", (username,)).fetchone(); conn.close()
    return bool(row) and sha256_text(password) == row[1]

def get_all_obras(): conn = get_conn(); df = pd.read_sql_query("SELECT * FROM obras ORDER BY id ASC", conn); conn.close(); return df

def get_all_users(): conn = get_conn(); df = pd.read_sql_query("SELECT * FROM users ORDER BY id DESC", conn); conn.close(); return df

def get_all_tags(): conn = get_conn(); df = pd.read_sql_query("SELECT * FROM tags ORDER BY id DESC", conn); conn.close(); return df

def save_user_questionnaire(user_uid, animal_name, q1, q2, q3):
    conn = get_conn(); cur = conn.cursor(); cur.execute("INSERT OR IGNORE INTO users (user_uid, animal_name, q1, q2, q3, created_at) VALUES (?, ?, ?, ?, ?, ?)", (user_uid, animal_name, q1, q2, q3, now_str())); conn.commit(); conn.close()

def save_tag(user_uid, obra_id, tag_original, origem="usuario"):
    tag_norm, conf = normalize_tag(tag_original); categoria = infer_semantic_category(tag_norm)
    conn = get_conn(); cur = conn.cursor(); cur.execute("INSERT INTO tags (user_uid, obra_id, tag_original, tag_normalizada, categoria_semantica, confianca, origem, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (user_uid, obra_id, tag_original.strip(), tag_norm, categoria, conf, origem, now_str())); conn.commit(); conn.close()

def save_obra(titulo, artista, ano, imagem, descricao, texto_curatorial, cronologia, tecnica, material, origem):
    conn = get_conn(); cur = conn.cursor(); cur.execute("INSERT INTO obras (titulo, artista, ano, imagem, descricao, texto_curatorial, cronologia, tecnica, material, origem, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (titulo, artista, ano, imagem, descricao, texto_curatorial, cronologia, tecnica, material, origem, now_str())); conn.commit(); conn.close()

def remove_obra(obra_id):
    conn = get_conn(); cur = conn.cursor(); cur.execute("DELETE FROM tags WHERE obra_id = ?", (obra_id,)); cur.execute("DELETE FROM obras WHERE id = ?", (obra_id,)); conn.commit(); conn.close()

def get_user_tags(user_uid): conn = get_conn(); df = pd.read_sql_query("SELECT * FROM tags WHERE user_uid = ? ORDER BY id DESC", conn, params=(user_uid,)); conn.close(); return df

def save_validacao(item_tipo, item_id, acao, observacao, validado_por):
    conn = get_conn(); cur = conn.cursor(); cur.execute("INSERT INTO validacoes (item_tipo, item_id, acao, observacao, validado_por, created_at) VALUES (?, ?, ?, ?, ?, ?)", (item_tipo, str(item_id), acao, observacao, validado_por, now_str())); conn.commit(); conn.close()

def save_relacao(origem_tipo, origem_id, destino_tipo, destino_id, relacao, peso=1.0):
    conn = get_conn(); cur = conn.cursor(); cur.execute("INSERT INTO relacoes (origem_tipo, origem_id, destino_tipo, destino_id, relacao, peso, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)", (origem_tipo, str(origem_id), destino_tipo, str(destino_id), relacao, float(peso), now_str())); conn.commit(); conn.close()

def save_automacao(titulo, tipo, payload, status="gerada"):
    conn = get_conn(); cur = conn.cursor(); cur.execute("INSERT INTO automacoes (titulo, tipo, payload, status, created_at) VALUES (?, ?, ?, ?, ?)", (titulo, tipo, json.dumps(payload, ensure_ascii=False), status, now_str())); conn.commit(); conn.close()

def save_accessibility_settings(user_uid, font_scale=1.0, high_contrast=0, simplificar_textos=0, audio_descricao=0):
    conn = get_conn(); cur = conn.cursor(); row = cur.execute("SELECT id FROM acessibilidade WHERE user_uid = ?", (user_uid,)).fetchone()
    if row:
        cur.execute("UPDATE acessibilidade SET font_scale = ?, high_contrast = ?, simplificar_textos = ?, audio_descricao = ?, updated_at = ? WHERE user_uid = ?", (font_scale, high_contrast, simplificar_textos, audio_descricao, now_str(), user_uid))
    else:
        cur.execute("INSERT INTO acessibilidade (user_uid, font_scale, high_contrast, simplificar_textos, audio_descricao, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)", (user_uid, font_scale, high_contrast, simplificar_textos, audio_descricao, now_str(), now_str()))
    conn.commit(); conn.close()

def get_accessibility_settings(user_uid):
    conn = get_conn(); cur = conn.cursor(); row = cur.execute("SELECT font_scale, high_contrast, simplificar_textos, audio_descricao FROM acessibilidade WHERE user_uid = ?", (user_uid,)).fetchone(); conn.close()
    if row: return {"font_scale": row[0], "high_contrast": row[1], "simplificar_textos": row[2], "audio_descricao": row[3]}
    return {"font_scale": 1.0, "high_contrast": 0, "simplificar_textos": 0, "audio_descricao": 0}

def recommend_tags_for_obra(obra_row, tags_df, top_n=8):
    if tags_df.empty:
        base = []
        for field in ["descricao", "texto_curatorial", "titulo", "tecnica", "material", "origem"]: base.extend(tokenize(str(obra_row.get(field, ""))))
        return [t for t, _ in Counter([b for b in base if len(b) > 3]).most_common(top_n)]
    obra_tags = tags_df[tags_df["obra_id"] == obra_row["id"]]
    if not obra_tags.empty: return obra_tags["tag_normalizada"].value_counts().head(top_n).index.tolist()
    corpus = " ".join([str(obra_row.get(c, "")) for c in ["titulo", "descricao", "texto_curatorial", "cronologia", "tecnica", "material"]])
    return [t for t, _ in Counter([t for t in tokenize(corpus) if len(t) > 3]).most_common(top_n)]

def extract_topics_from_obra(obra_row):
    text = " ".join([str(obra_row.get("titulo", "")), str(obra_row.get("descricao", "")), str(obra_row.get("texto_curatorial", "")), str(obra_row.get("cronologia", "")), str(obra_row.get("tecnica", "")), str(obra_row.get("material", "")), str(obra_row.get("origem", ""))])
    return [t for t, _ in Counter([t for t in tokenize(text) if len(t) > 3]).most_common(12)]

def build_entity_candidates(obras_df):
    entities = []
    for _, obra in obras_df.iterrows():
        entities.append({"nome": obra["titulo"], "tipo": "obra", "nome_canonico": obra["titulo"]})
        if obra["artista"]: entities.append({"nome": obra["artista"], "tipo": "autor", "nome_canonico": obra["artista"]})
        for ent in extract_entities(str(obra.get("texto_curatorial", ""))): entities.append({"nome": ent, "tipo": "entidade_extraida", "nome_canonico": ent})
    out, seen = [], set()
    for item in entities:
        key = (normalize_text(item["nome"]), item["tipo"])
        if key not in seen: seen.add(key); out.append(item)
    return pd.DataFrame(out)

def generate_semantic_flow_report(obras_df, tags_df):
    report = []
    for _, obra in obras_df.iterrows():
        obra_tags = tags_df[tags_df["obra_id"] == obra["id"]] if not tags_df.empty else pd.DataFrame()
        report.append({"Obra": obra["titulo"], "Autor": obra["artista"], "Tags": len(obra_tags), "Tags Únicas": obra_tags["tag_normalizada"].nunique() if not obra_tags.empty else 0, "Categorias": obra_tags["categoria_semantica"].nunique() if not obra_tags.empty else 0, "Tópicos Extraídos": ", ".join(extract_topics_from_obra(obra)[:5])})
    return report

def auto_generate_relations(obras_df, tags_df):
    generated = []
    for _, obra in obras_df.iterrows():
        generated.append(("obra", obra["id"], "autor", obra["artista"], "criada_por", 1.0))
        if obra.get("material"): generated.append(("obra", obra["id"], "material", obra["material"], "usa_material", 0.92))
        if obra.get("tecnica"): generated.append(("obra", obra["id"], "tecnica", obra["tecnica"], "usa_tecnica", 0.92))
        if obra.get("origem"): generated.append(("obra", obra["id"], "origem", obra["origem"], "origem_geografica", 0.88))
    if not tags_df.empty:
        grouped = tags_df.groupby(["obra_id", "tag_normalizada"]).size().reset_index(name="peso")
        for _, row in grouped.iterrows(): generated.append(("obra", row["obra_id"], "tag", row["tag_normalizada"], "recebe_tag", float(row["peso"])))
    return generated

def generate_curatorial_queue(tags_df):
    if tags_df.empty: return pd.DataFrame(columns=["tag_original", "tag_normalizada", "motivo", "confianca"])
    queue = []; counts = tags_df["tag_normalizada"].value_counts().to_dict()
    for _, row in tags_df.iterrows():
        motivo = None
        if row["confianca"] < 0.70: motivo = "normalização com baixa confiança"
        elif len(str(row["tag_original"])) <= 2: motivo = "tag muito curta"
        elif counts.get(row["tag_normalizada"], 0) == 1: motivo = "termo único para revisão"
        if motivo: queue.append({"tag_original": row["tag_original"], "tag_normalizada": row["tag_normalizada"], "motivo": motivo, "confianca": row["confianca"]})
    return pd.DataFrame(queue)

def automation_suggestions(obras_df, tags_df):
    suggestions = []
    for _, obra in obras_df.iterrows():
        obra_tags = tags_df[tags_df["obra_id"] == obra["id"]] if not tags_df.empty else pd.DataFrame()
        if obra_tags.empty:
            suggestions.append({"tipo": "sugestao_tag", "titulo": f"Sugestões automáticas para {obra['titulo']}", "payload": {"obra_id": int(obra['id']), "tags": recommend_tags_for_obra(obra, tags_df, 6)}})
        else:
            cats = obra_tags["categoria_semantica"].value_counts().to_dict()
            if cats.get("livre", 0) > max(2, len(obra_tags) * 0.45):
                suggestions.append({"tipo": "revisao_semantica", "titulo": f"Revisar vocabulário de {obra['titulo']}", "payload": {"obra_id": int(obra['id']), "motivo": "muitas tags livres"}})
    return suggestions

def render_topbar():
    st.markdown(f"<div class='glass-card'><div class='section-title'>{APP_TITLE}</div><div class='section-subtitle'>camadas semânticas, análise museológica, curadoria digital e automação</div></div>", unsafe_allow_html=True)

def metric_card(label, value, sub=""):
    st.markdown(f"<div class='metric-box'><div class='metric-label'>{label}</div><div class='metric-value'>{value}</div><div class='metric-sub'>{sub}</div></div>", unsafe_allow_html=True)

def section_header(title, subtitle=""):
    st.markdown(f"<div class='glass-card'><div class='section-title'>{title}</div><div class='section-subtitle'>{subtitle}</div></div>", unsafe_allow_html=True)

def insight_box(text): st.markdown(f"<div class='insight'>{text}</div>", unsafe_allow_html=True)

def divider(): st.markdown("<hr>", unsafe_allow_html=True)

def render_accessibility_panel(user_uid):
    cfg = get_accessibility_settings(user_uid)
    with st.expander("Acessibilidade e leitura assistida", expanded=False):
        c1, c2, c3, c4 = st.columns(4)
        with c1: font_scale = st.slider("Tamanho da fonte", 0.8, 1.6, float(cfg["font_scale"]), 0.1)
        with c2: high_contrast = st.toggle("Alto contraste", value=bool(cfg["high_contrast"]))
        with c3: simplificar = st.toggle("Explicar termos difíceis", value=bool(cfg["simplificar_textos"]))
        with c4: audio_desc = st.toggle("Audiodescrição textual", value=bool(cfg["audio_descricao"]))
        if st.button("Salvar preferências de acessibilidade", key="save_access"):
            save_accessibility_settings(user_uid, font_scale=font_scale, high_contrast=int(high_contrast), simplificar_textos=int(simplificar), audio_descricao=int(audio_desc)); st.success("Preferências salvas."); st.rerun()

def bootstrap_session():
    if "user_uid" not in st.session_state: st.session_state["user_uid"] = generate_uid()
    if "animal_name" not in st.session_state: st.session_state["animal_name"] = generate_animal_name()
    if "questionnaire_done" not in st.session_state: st.session_state["questionnaire_done"] = False
    if "selected_obra" not in st.session_state: st.session_state["selected_obra"] = None
    if "admin_logged" not in st.session_state: st.session_state["admin_logged"] = False

def intro_screen():
    st.markdown(f"<div class='glass-card'><div class='section-title'>{APP_TITLE}</div><div class='section-subtitle'>plataforma de folksonomia com base museológica, camada semântica, leitura inteligente, curadoria digital e análise de fluxo informacional.</div></div>", unsafe_allow_html=True)
    with st.form("questionario_inicial"):
        c1, c2 = st.columns(2)
        with c1:
            q1 = st.selectbox("Qual é a sua frequência de visita a museus?", ["Nunca", "Raramente", "Ocasionalmente", "Frequentemente"])
            q2 = st.selectbox("Você já ouviu falar sobre documentação museológica?", ["Nenhum conhecimento", "Pouco", "Intermediário", "Avançado"])
        with c2:
            q3 = st.text_area("O que você entende por tags aplicadas a acervos?", height=220, placeholder="Escreva com suas palavras.")
        submitted = st.form_submit_button("Liberar acesso")
        if submitted:
            if not q3.strip(): st.error("Preencha a resposta aberta para continuar.")
            else:
                save_user_questionnaire(st.session_state["user_uid"], st.session_state["animal_name"], q1, q2, q3.strip())
                st.session_state["questionnaire_done"] = True; st.success("Acesso liberado."); st.rerun()

def obra_detail_overlay(obra, tags_df, user_uid):
    user_tags = tags_df[(tags_df["obra_id"] == obra["id"]) & (tags_df["user_uid"] == user_uid)] if not tags_df.empty else pd.DataFrame()
    all_tags = tags_df[tags_df["obra_id"] == obra["id"]] if not tags_df.empty else pd.DataFrame()
    recs = recommend_tags_for_obra(obra, tags_df, top_n=8)
    cfg = get_accessibility_settings(user_uid)
    descricao = simplify_text(obra["descricao"]) if cfg["simplificar_textos"] else obra["descricao"]
    texto_curatorial = simplify_text(obra["texto_curatorial"]) if cfg["simplificar_textos"] else obra["texto_curatorial"]
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    c1, c2 = st.columns([1.1, 1])
    with c1:
        st.image(obra["imagem"], use_container_width=True)
        if cfg["audio_descricao"]: insight_box(describe_image_from_metadata(obra))
    with c2:
        st.markdown(f"### {obra['titulo']}")
        st.markdown(f"**Artista:** {obra['artista']}")
        st.markdown(f"**Ano:** {obra['ano']}")
        st.markdown(f"**Técnica:** {obra['tecnica']}")
        st.markdown(f"**Material:** {obra['material']}")
        st.markdown(f"**Origem:** {obra['origem']}")
        st.markdown(f"**Cronologia:** {obra['cronologia']}")
        st.markdown(f"**Descrição:** {descricao}")
        st.markdown(f"**Texto curatorial:** {texto_curatorial}")
        st.markdown("**Sugestões automáticas de tags**")
        st.markdown("".join([f"<span class='tag-pill'>{r}</span>" for r in recs]), unsafe_allow_html=True)
        with st.form(f"form_tag_{obra['id']}"):
            tag = st.text_input("Inserir tag")
            sub = st.form_submit_button("Salvar tag")
            if sub:
                if tag.strip(): save_tag(user_uid, int(obra["id"]), tag.strip()); st.success("Tag salva."); st.rerun()
                else: st.error("Digite uma tag válida.")
        if not user_tags.empty:
            st.markdown("**Suas tags nesta obra**")
            st.markdown("".join([f"<span class='tag-pill'>{row['tag_normalizada']}</span>" for _, row in user_tags.iterrows()]), unsafe_allow_html=True)
        if not all_tags.empty:
            st.markdown("**Vocabulário mais usado nesta obra**")
            vc = all_tags["tag_normalizada"].value_counts().head(12)
            st.markdown("".join([f"<span class='tag-pill'>{idx} ({val})</span>" for idx, val in vc.items()]), unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

def public_gallery():
    obras_df, tags_df, user_uid = get_all_obras(), get_all_tags(), st.session_state["user_uid"]
    section_header("Explorar obras", "clique em uma obra para abrir o painel translúcido de marcação, leitura semântica e sugestões automáticas")
    render_accessibility_panel(user_uid)
    c1, c2 = st.columns([1, 1])
    with c1: filtro = st.text_input("Filtrar por título, autor ou ano")
    with c2: ordenar = st.selectbox("Ordenar", ["id crescente", "id decrescente", "título", "artista", "ano"])
    df = obras_df.copy()
    if filtro.strip():
        ft = filtro.strip().lower()
        df = df[df["titulo"].str.lower().str.contains(ft, na=False) | df["artista"].str.lower().str.contains(ft, na=False) | df["ano"].astype(str).str.lower().str.contains(ft, na=False)]
    if ordenar == "id crescente": df = df.sort_values("id")
    elif ordenar == "id decrescente": df = df.sort_values("id", ascending=False)
    elif ordenar == "título": df = df.sort_values("titulo")
    elif ordenar == "artista": df = df.sort_values("artista")
    elif ordenar == "ano": df = df.sort_values("ano")
    cols = st.columns(3)
    for i, (_, obra) in enumerate(df.iterrows()):
        with cols[i % 3]:
            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
            st.image(obra["imagem"], use_container_width=True)
            st.markdown(f"### {obra['titulo']}")
            st.caption(f"{obra['artista']} · {obra['ano']}")
            st.write(obra["descricao"])
            if st.button("Abrir obra", key=f"abrir_{obra['id']}"): st.session_state["selected_obra"] = int(obra["id"]); st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
    if st.session_state.get("selected_obra"):
        selected = obras_df[obras_df["id"] == st.session_state["selected_obra"]]
        if not selected.empty:
            obra_detail_overlay(selected.iloc[0], tags_df, user_uid)
            if st.button("Fechar painel"): st.session_state["selected_obra"] = None; st.rerun()

def overview_tab(obras_df, users_df, tags_df):
    section_header("Visão geral", "indicadores centrais do sistema e do tráfego informacional")
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: metric_card("Obras", len(obras_df), "base museológica")
    with c2: metric_card("Usuários", users_df["user_uid"].nunique() if not users_df.empty else 0, "participantes")
    with c3: metric_card("Tags", len(tags_df), "coleta total")
    with c4: metric_card("Tags únicas", tags_df["tag_normalizada"].nunique() if not tags_df.empty else 0, "vocabulário")
    with c5: metric_card("Média por usuário", f"{len(tags_df)/max(users_df['user_uid'].nunique(),1):.1f}" if not users_df.empty else "0", "produção lexical")
    if not tags_df.empty:
        c1, c2 = st.columns(2)
        with c1: st.markdown("### Top tags normalizadas"); st.bar_chart(tags_df["tag_normalizada"].value_counts().head(20))
        with c2: st.markdown("### Categorias semânticas"); st.bar_chart(tags_df["categoria_semantica"].value_counts())
        insight_box("A camada semântica consolida variações lexicais e torna possível observar o fluxo entre termos livres, termos controlados, temas, cores, emoções e elementos de representação.")

def temporal_tab(tags_df):
    section_header("Análise temporal", "ritmo de criação de tags, dias ativos, frequência e evolução do vocabulário")
    if tags_df.empty: st.info("Ainda não há dados temporais suficientes."); return
    tf = tags_df.copy(); tf["created_at"] = pd.to_datetime(tf["created_at"]); tf["data"] = tf["created_at"].dt.date; tf["mes"] = tf["created_at"].dt.to_period("M").astype(str); tf["hora"] = tf["created_at"].dt.hour
    daily = tf.groupby("data").size()
    c1, c2, c3, c4 = st.columns(4)
    with c1: metric_card("Dias ativos", len(daily), "atividade registrada")
    with c2: metric_card("Pico diário", int(daily.max()), f"em {daily.idxmax()}")
    with c3: metric_card("Média diária", f"{daily.mean():.1f}", "tags por dia")
    with c4: metric_card("Horas ativas", tf["hora"].nunique(), "distribuição horária")
    c1, c2 = st.columns(2)
    with c1: st.markdown("### Tags por dia"); st.line_chart(daily)
    with c2: st.markdown("### Tags por mês"); st.bar_chart(tf.groupby("mes").size())
    st.markdown("### Distribuição por hora"); st.bar_chart(tf.groupby("hora").size())

def lexical_tab(tags_df):
    section_header("Vocabulário e semântica", "riqueza lexical, frequência, consolidação e fila curatorial")
    if tags_df.empty: st.info("Ainda não há tags para análise lexical."); return
    freq = tags_df["tag_normalizada"].value_counts().reset_index(); freq.columns = ["Tag", "Frequência"]
    total = freq["Frequência"].sum(); vocab = freq["Tag"].nunique(); hapax = int((freq["Frequência"] == 1).sum()); ttr = vocab / total if total else 0
    c1, c2, c3, c4 = st.columns(4)
    with c1: metric_card("Vocabulário", vocab, "termos distintos")
    with c2: metric_card("Hapax", hapax, "uso único")
    with c3: metric_card("TTR", f"{ttr:.3f}", "riqueza lexical")
    with c4: metric_card("Categorias", tags_df["categoria_semantica"].nunique(), "camada semântica")
    c1, c2 = st.columns(2)
    with c1: st.markdown("### Frequência das tags"); st.dataframe(freq.head(50), use_container_width=True, hide_index=True)
    with c2: st.markdown("### Fila de revisão curatorial"); st.dataframe(generate_curatorial_queue(tags_df).head(50), use_container_width=True, hide_index=True)

def semantic_flow_tab(obras_df, tags_df):
    section_header("Tráfego de informações", "circulação entre obra, tema, técnica, material, autor, tag e leitura semântica")
    report = pd.DataFrame(generate_semantic_flow_report(obras_df, tags_df))
    if report.empty: st.info("Ainda não há dados suficientes para o fluxo informacional."); return
    st.dataframe(report, use_container_width=True, hide_index=True)
    density = report[["Obra", "Tags", "Tags Únicas", "Categorias"]].copy(); density["Pontuação de densidade"] = density["Tags"] + density["Tags Únicas"] + density["Categorias"]
    st.markdown("### Obras por densidade semântica"); st.bar_chart(density.set_index("Obra")["Pontuação de densidade"])

def graph_tab(obras_df, tags_df):
    section_header("Grafo de conhecimento", "rede simplificada de entidades e relações em forma tabular e lógica")
    relations = auto_generate_relations(obras_df, tags_df)
    if not relations: st.info("Ainda não há relações suficientes para o grafo."); return
    df = pd.DataFrame(relations, columns=["origem_tipo", "origem_id", "destino_tipo", "destino_id", "relacao", "peso"])
    st.dataframe(df.head(200), use_container_width=True, hide_index=True)
    c1, c2 = st.columns(2)
    with c1: st.markdown("### Relações por tipo"); st.bar_chart(df["relacao"].value_counts())
    with c2: st.markdown("### Destinos por classe"); st.bar_chart(df["destino_tipo"].value_counts())
    if st.button("Persistir relações automáticas no banco"):
        for row in relations: save_relacao(*row)
        st.success("Relações salvas.")

def automation_tab(obras_df, tags_df):
    section_header("Automação", "sugestões geradas a partir do aprendizado e das regras de análise")
    suggestions = automation_suggestions(obras_df, tags_df)
    if not suggestions: st.info("Nenhuma automação sugerida no momento."); return
    for i, sug in enumerate(suggestions, start=1):
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.markdown(f"### {sug['titulo']}"); st.json(sug["payload"])
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Registrar automação", key=f"auto_save_{i}"): save_automacao(sug["titulo"], sug["tipo"], sug["payload"], "gerada"); st.success("Automação registrada.")
        with c2:
            if st.button("Marcar como revisada", key=f"auto_rev_{i}"): save_validacao("automacao", i, "revisada", sug["titulo"], ADMIN_LOGIN); st.success("Validação registrada.")
        st.markdown("</div>", unsafe_allow_html=True)

def admin_login_screen():
    section_header("Área administrativa", "acesso restrito à camada de validação humana e análise curatorial")
    with st.form("admin_login_form"):
        username = st.text_input("Login"); password = st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar"):
            if login_ok(username, password): st.session_state["admin_logged"] = True; st.success("Login realizado."); st.rerun()
            else: st.error("Credenciais inválidas.")

def curadoria_tab(obras_df, tags_df):
    section_header("Curadoria digital", "validação humana da extração, revisão semântica e consolidação do vocabulário")
    queue = generate_curatorial_queue(tags_df)
    if queue.empty: st.success("Nenhum item crítico na fila de curadoria.")
    else:
        st.dataframe(queue, use_container_width=True, hide_index=True)
        with st.form("validacao_curatorial"):
            item_tipo = st.selectbox("Tipo de item", ["tag", "relacao", "automacao", "entidade"])
            item_id = st.text_input("Identificador do item")
            acao = st.selectbox("Ação", ["aprovado", "corrigido", "rejeitado", "mesclado"])
            observacao = st.text_area("Observação")
            if st.form_submit_button("Registrar validação"): save_validacao(item_tipo, item_id, acao, observacao, ADMIN_LOGIN); st.success("Validação registrada.")
    st.markdown("### Entidades candidatas"); st.dataframe(build_entity_candidates(obras_df), use_container_width=True, hide_index=True)

def obras_tab(obras_df):
    section_header("Gestão de obras", "cadastro, revisão e remoção da base museológica")
    t1, t2 = st.tabs(["Listagem", "Adicionar obra"])
    with t1:
        if obras_df.empty: st.info("Não há obras cadastradas.")
        else:
            for _, obra in obras_df.iterrows():
                st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
                c1, c2, c3 = st.columns([1, 2, 1])
                with c1: st.image(obra["imagem"], use_container_width=True)
                with c2:
                    st.markdown(f"### {obra['titulo']}"); st.markdown(f"**Artista:** {obra['artista']}"); st.markdown(f"**Ano:** {obra['ano']}"); st.markdown(f"**Descrição:** {obra['descricao']}")
                with c3:
                    if st.button("Remover", key=f"rem_{obra['id']}"): remove_obra(int(obra["id"])); st.success("Obra removida."); st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)
    with t2:
        with st.form("add_obra_form"):
            titulo = st.text_input("Título"); artista = st.text_input("Artista"); ano = st.text_input("Ano"); imagem = st.text_input("URL da imagem")
            descricao = st.text_area("Descrição"); texto_curatorial = st.text_area("Texto curatorial"); cronologia = st.text_input("Cronologia"); tecnica = st.text_input("Técnica"); material = st.text_input("Material"); origem = st.text_input("Origem")
            if st.form_submit_button("Adicionar obra"):
                if titulo and artista and ano and imagem: save_obra(titulo, artista, ano, imagem, descricao, texto_curatorial, cronologia, tecnica, material, origem); st.success("Obra adicionada."); st.rerun()
                else: st.error("Preencha os campos essenciais.")

def export_tab(obras_df, users_df, tags_df):
    section_header("Exportação", "saídas para análise externa e preservação do trabalho documental")
    c1, c2, c3 = st.columns(3)
    with c1: st.download_button("Exportar obras em CSV", obras_df.to_csv(index=False).encode("utf-8"), "obras.csv", "text/csv")
    with c2: st.download_button("Exportar usuários em CSV", users_df.to_csv(index=False).encode("utf-8"), "usuarios.csv", "text/csv")
    with c3: st.download_button("Exportar tags em CSV", tags_df.to_csv(index=False).encode("utf-8"), "tags.csv", "text/csv")
    report = pd.DataFrame(generate_semantic_flow_report(obras_df, tags_df))
    if not report.empty: st.download_button("Exportar relatório de fluxo semântico", report.to_csv(index=False).encode("utf-8"), "fluxo_semantico.csv", "text/csv")

def admin_panel():
    obras_df, users_df, tags_df = get_all_obras(), get_all_users(), get_all_tags()
    tabs = st.tabs(["Visão geral","Temporal","Vocabulário","Fluxo informacional","Grafo","Curadoria","Obras","Exportação","Automação"])
    with tabs[0]: overview_tab(obras_df, users_df, tags_df)
    with tabs[1]: temporal_tab(tags_df)
    with tabs[2]: lexical_tab(tags_df)
    with tabs[3]: semantic_flow_tab(obras_df, tags_df)
    with tabs[4]: graph_tab(obras_df, tags_df)
    with tabs[5]: curadoria_tab(obras_df, tags_df)
    with tabs[6]: obras_tab(obras_df)
    with tabs[7]: export_tab(obras_df, users_df, tags_df)
    with tabs[8]: automation_tab(obras_df, tags_df)
    if st.button("Sair da área administrativa"): st.session_state["admin_logged"] = False; st.rerun()

def main():
    inject_theme(); init_db()
    bootstrap_session(); render_topbar()
    if not st.session_state["questionnaire_done"]: intro_screen(); return
    public_tab, admin_tab = st.tabs(["Plataforma", "Área administrativa"])
    with public_tab: public_gallery()
    with admin_tab:
        if not st.session_state["admin_logged"]: admin_login_screen()
        else: admin_panel()

if __name__ == "__main__":
    main()