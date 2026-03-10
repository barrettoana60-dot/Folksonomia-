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
import math
warnings.filterwarnings('ignore')

# ───────────────────────────────────────────────────────────────────────
# CONFIGURAÇÃO BÁSICA
# ───────────────────────────────────────────────────────────────────────
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

AUDIO_DESCRIPTIONS = {
    1: "Guernica, de Pablo Picasso, 1937. Obra monumental em tons de cinza, preto e branco. Representa a tragédia do bombardeio da cidade basca de Guernica durante a Guerra Civil Espanhola. Figuras fragmentadas de humanos e animais expressam angústia, dor e desespero. Uma mãe segura seu filho morto, um touro observa a cena, um cavalo ferido grita ao centro. Composição caótica que simboliza os horrores da guerra.",
    2: "A Noite Estrelada, de Vincent van Gogh, 1889. Paisagem noturna com céu turbilhonante em azuis e dourados intensos. Redemoinhos de tinta representam o vento e o movimento das estrelas sobre a vila de Saint-Rémy-de-Provence. No centro, uma lua crescente brilhante. À esquerda, um cipreste escuro sobe em espiral. Casas com janelas iluminadas trazem calor humano sob o céu dramático.",
    3: "Mona Lisa, de Leonardo da Vinci, 1503-1519. Retrato feminino sobre fundo de paisagem nebulosa. A figura apresenta um sorriso enigmático e ambíguo que mudou ao longo dos séculos. Seus olhos parecem seguir o espectador. Cabelos escuros cobertos por véu translúcido. Técnica de sfumato cria transições suaves entre luz e sombra, conferindo profundidade e realismo à figura."
}

def generate_animal_name():
    random.seed()
    return f"{random.choice(ANIMAIS)} {random.choice(ADJETIVOS)}"

# ───────────────────────────────────────────────────────────────────────
# ARQUIVOS JSON / PERSISTÊNCIA
# ───────────────────────────────────────────────────────────────────────
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

# ───────────────────────────────────────────────────────────────────────
# SIMILARIDADE (Apenas para coocorrência; removi conexões/entropia complexas)
# ───────────────────────────────────────────────────────────────────────
def tag_cooccurrence(tdf, top_n=15):
    if tdf.empty:
        return pd.DataFrame()
    top_tags = tdf['tag'].value_counts().head(top_n).index.tolist()
    user_obra = tdf.groupby(['user_id','obra_id'])['tag'].apply(list).reset_index()
    matrix = pd.DataFrame(0, index=top_tags, columns=top_tags)
    for _, row in user_obra.iterrows():
        session_tags = [t for t in row['tag'] if t in top_tags]
        for i in range(len(session_tags)):
            for j in range(i+1, len(session_tags)):
                t1, t2 = session_tags[i], session_tags[j]
                if t1 != t2:
                    matrix.loc[t1, t2] += 1
                    matrix.loc[t2, t1] += 1
    return matrix

# ───────────────────────────────────────────────────────────────────────
# CSS / TEMA / ACESSIBILIDADE
# ───────────────────────────────────────────────────────────────────────
def load_css():
    theme = st.session_state.get('theme', 'dark')
    font_size = st.session_state.get('font_size', 'medium')
    high_contrast = st.session_state.get('high_contrast', False)

    font_map = {'small':'13px','medium':'15px','large':'17px','xlarge':'20px'}
    base_font = font_map.get(font_size, '15px')

    if theme == 'light':
        bg = "linear-gradient(-45deg,#e8f4fd 0%,#f0f7ff 25%,#e8f4fd 50%,#dbeeff 75%,#e8f4fd 100%)"
        card_bg = "rgba(255,255,255,0.85)"
        card_border = "rgba(0,80,160,0.18)"
        text_color = "#0a1628"
        text_muted = "rgba(10,22,40,0.55)"
        navbar_bg = "rgba(255,255,255,0.88)"
        navbar_border = "rgba(0,80,160,0.15)"
        kpi_bg = "rgba(0,80,160,0.09)"
        kpi_border = "rgba(0,80,160,0.18)"
        badge_bg = "rgba(0,80,160,0.12)"
        badge_border = "rgba(0,80,160,0.3)"
        input_bg = "rgba(0,80,160,0.07)"
        input_border = "rgba(0,80,160,0.25)"
        btn_bg = "rgba(0,80,160,0.14)"
        btn_hover = "rgba(0,80,160,0.28)"
        tab_bg = "rgba(0,80,160,0.07)"
        tab_sel = "rgba(0,80,160,0.22)"
        conn_bg = "rgba(0,80,160,0.06)"
        conn_hover = "rgba(0,80,160,0.13)"
        sc_bg = "rgba(0,80,160,0.05)"
        title_color = "#001F3F"
        subtitle_color = "#1a3a6b"
        logo_grad = "linear-gradient(135deg,#001F3F 0%,#0056b3 100%)"
    else:
        bg = "linear-gradient(-45deg,#000 0%,#001F3F 25%,#000 50%,#001F3F 75%,#000 100%)"
        card_bg = "rgba(255,255,255,0.15)"
        card_border = "rgba(255,255,255,0.3)"
        text_color = "#e0e0e0"
        text_muted = "rgba(255,255,255,0.45)"
        navbar_bg = "rgba(255,255,255,0.1)"
        navbar_border = "rgba(255,255,255,0.2)"
        kpi_bg = "rgba(255,255,255,0.16)"
        kpi_border = "rgba(255,255,255,0.28)"
        badge_bg = "rgba(255,255,255,0.25)"
        badge_border = "rgba(255,255,255,0.4)"
        input_bg = "rgba(255,255,255,0.18)"
        input_border = "rgba(255,255,255,0.28)"
        btn_bg = "rgba(255,255,255,0.25)"
        btn_hover = "rgba(255,255,255,0.4)"
        tab_bg = "rgba(255,255,255,0.1)"
        tab_sel = "rgba(255,255,255,0.33)"
        conn_bg = "rgba(255,255,255,0.06)"
        conn_hover = "rgba(255,255,255,0.12)"
        sc_bg = "rgba(255,255,255,0.07)"
        title_color = "white"
        subtitle_color = "rgba(255,255,255,0.9)"
        logo_grad = "linear-gradient(135deg,#a7e6ff 0%,#d1baff 100%)"

    if high_contrast:
        text_color = "#ffffff" if theme == 'dark' else "#000000"
        card_border = "2px solid " + ("#ffffff" if theme == 'dark' else "#000000")

    st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');
* {{
  margin:0; padding:0; box-sizing:border-box;
  font-family:'Inter',sans-serif!important;
  font-size:{base_font};
}}
@keyframes bgani{{0%{{background-position:0% 50%}}50%{{background-position:100% 50%}}100%{{background-position:0% 50%}}}}
.stApp {{
  background:{bg};
  background-size:400% 400%;
  animation:bgani 18s ease infinite;
  color:{text_color};
}}

.top-navbar {{
  position:fixed; top:0; left:0; right:0; z-index:9999;
  background:{navbar_bg}; backdrop-filter:blur(24px) saturate(180%);
  border-bottom:1px solid {navbar_border};
  padding:1.1rem 2.5rem;
  display:flex; justify-content:space-between; align-items:center;
  box-shadow:0 4px 30px rgba(0,0,0,0.08);
}}
.navbar-logo {{
  font-size:1.5rem; font-weight:900; letter-spacing:-1px;
  background:{logo_grad};
  -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text;
}}
.navbar-sub {{
  font-size:.72rem; font-weight:500;
  color:{text_muted}; letter-spacing:1px; text-transform:uppercase;
}}

.main-content {{
  margin-top:80px; padding:2rem 2.5rem;
  max-width:1700px; margin-left:auto; margin-right:auto;
}}

.glass-card {{
  background:{card_bg}; backdrop-filter:blur(20px) saturate(180%);
  border:1px solid {card_border}; border-radius:24px; padding:2.2rem; margin:1.2rem 0;
  box-shadow:0 8px 32px rgba(0,0,0,0.08);
}}

.main-title {{
  color:{title_color}; font-size:3.2rem; font-weight:900;
  text-align:center; margin:1.5rem 0 .8rem; letter-spacing:-2px;
}}
.subtitle {{
  color:{subtitle_color}; font-size:1.15rem; text-align:center;
  margin-bottom:2.5rem; line-height:1.8; font-weight:400;
}}

.tag-badge {{
  display:inline-flex; align-items:center; gap:4px;
  background:{badge_bg}; border:1px solid {badge_border};
  color:{text_color}; padding:.42rem 1rem; border-radius:50px;
  margin:.25rem; font-size:.84rem; font-weight:600;
}}

.kpi-card {{
  background:{kpi_bg}; backdrop-filter:blur(20px);
  border:1px solid {kpi_border}; border-radius:20px;
  padding:1.6rem; text-align:center; color:{text_color};
}}
.kpi-val {{ font-size:2.4rem; font-weight:900; margin:.5rem 0; }}
.kpi-lbl {{
  font-size:.72rem; text-transform:uppercase; letter-spacing:2px;
  font-weight:700; opacity:.75;
}}

.sc {{
  background:{sc_bg}; border:1px solid {card_border};
  border-radius:14px; padding:1.2rem; margin:.6rem 0;
}}
.sc-g {{ border-left:4px solid #34d399; }}
.sc-b {{ border-left:4px solid #60a5fa; }}

.divider {{
  height:1px;
  background:linear-gradient(90deg,transparent,{card_border},transparent);
  margin:1.8rem 0;
}}

.obra-card {{
  background:{card_bg}; backdrop-filter:blur(15px);
  border:1px solid {card_border}; border-radius:22px; overflow:hidden;
  transition:all .3s; cursor:pointer; position:relative;
}}
.obra-card img {{
  width:100%; height:260px; object-fit:cover;
}}

.obra-list-item {{
  display:flex; gap:1.5rem; align-items:flex-start;
  background:{card_bg}; backdrop-filter:blur(15px);
  border:1px solid {card_border}; border-radius:18px;
  padding:1.2rem; margin:.7rem 0;
}}
.obra-list-img {{
  width:140px; min-width:140px; height:100px; object-fit:cover; border-radius:12px;
}}

#MainMenu, footer, header, .stDeployButton {{
  visibility:hidden;
}}

.stButton button {{
  background:{btn_bg}!important; color:{text_color}!important;
  border:1px solid {badge_border}!important;
  border-radius:14px!important; padding:.75rem 1.8rem!important;
  font-weight:700!important; font-size:.88rem!important;
}}
</style>
""", unsafe_allow_html=True)

# JS ÚNICO PARA ÁUDIO (speechSynthesis)
st.markdown("""
<script>
function speak(text){
  if (!('speechSynthesis' in window)) { alert('Seu navegador não suporta áudio-descrição.'); return; }
  window.speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.lang = 'pt-BR';
  u.rate = 0.88;
  window.speechSynthesis.speak(u);
}
function stopSpeak(){
  if ('speechSynthesis' in window) { window.speechSynthesis.cancel(); }
}
</script>
""", unsafe_allow_html=True)

def render_accessibility_bar():
    theme = st.session_state.get('theme', 'dark')
    font_size = st.session_state.get('font_size', 'medium')

    st.markdown(f"""
<div style="
 position:fixed; top:72px; right:0; z-index:9998;
 background:rgba(0,0,0,0.4); backdrop-filter:blur(20px);
 border-radius:16px 0 0 16px; padding:.55rem .8rem;
 display:flex; flex-direction:column; gap:6px;
">
  <div style="font-size:.58rem;color:rgba(255,255,255,.7);text-transform:uppercase;letter-spacing:1px;text-align:center">
    Texto
  </div>
  <div style="display:flex; flex-direction:column; gap:4px;align-items:center;">
    <span style="font-size:.7rem;color:white;">Tamanho atual: {font_size}</span>
  </div>
</div>
""", unsafe_allow_html=True)

# ───────────────────────────────────────────────────────────────────────
# HELPERS VISUAIS
# ───────────────────────────────────────────────────────────────────────
def kpi(label, value, sub="", color="#a7e6ff"):
    sub_html = f"<div class='kpi-sub'>{sub}</div>" if sub else ""
    return (
        f"<div class='kpi-card'>"
        f"<div class='kpi-lbl'>{label}</div>"
        f"<div class='kpi-val' style='color:{color}'>{value}</div>"
        f"{sub_html}"
        f"</div>"
    )

def divider():
    return "<div class='divider'></div>"

# ───────────────────────────────────────────────────────────────────────
# DADOS (OBRAS / USUÁRIOS / TAGS)
# ───────────────────────────────────────────────────────────────────────
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
         "categoria":"Pintura","tecnica":"Óleo sobre tela","dimensoes":"349.3 × 776.6 cm",
         "descricao":"Obra de protesto contra os bombardeios da Guerra Civil Espanhola",
         "imagem":"https://upload.wikimedia.org/wikipedia/en/7/74/PicassoGuernica.jpg"},
        {"id":2,"titulo":"A Noite Estrelada","artista":"Vincent van Gogh","ano":"1889",
         "categoria":"Pintura","tecnica":"Óleo sobre tela","dimensoes":"73.7 × 92.1 cm",
         "descricao":"Paisagem noturna com céu turbilhonante sobre vila",
         "imagem":"https://upload.wikimedia.org/wikipedia/commons/thumb/e/ea/Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg/1200px-Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg"},
        {"id":3,"titulo":"Mona Lisa","artista":"Leonardo da Vinci","ano":"1503",
         "categoria":"Pintura","tecnica":"Óleo sobre madeira","dimensoes":"77 × 53 cm",
         "descricao":"Retrato de mulher com sorriso enigmático usando técnica de sfumato",
         "imagem":"https://upload.wikimedia.org/wikipedia/commons/thumb/e/ec/Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_retouched.jpg/800px-Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_retouched.jpg"}
    ]
    obras = load_json_file(OBRAS_FILE, default)
    if not obras:
        save_json_file(OBRAS_FILE, default)
        return default
    return obras

def save_answers(uid, animal, answers):
    users = load_json_file(USERS_FILE, [])
    users.append({
        "user_id":uid,
        "animal_name":animal,
        "timestamp":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        **answers
    })
    return save_json_file(USERS_FILE, users)

def save_tag(uid, obra_id, tag):
    tags = load_json_file(TAGS_FILE, [])
    tags.append({
        "id":len(tags)+1,
        "user_id":uid,
        "obra_id":obra_id,
        "tag":tag.lower().strip(),
        "timestamp":datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
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
    return username == ADMIN_USERNAME and h == hashlib.sha256(ADMIN_PASSWORD.encode()).hexdigest()

def all_tags():
    t = load_json_file(TAGS_FILE, [])
    return pd.DataFrame(t) if t else pd.DataFrame()

def all_users():
    u = load_json_file(USERS_FILE, [])
    return pd.DataFrame(u) if u else pd.DataFrame()

# HTML para exportações por usuário (mantido)
def html_quest(uid, animal, users_df):
    if users_df.empty:
        return None
    ud = users_df[users_df['user_id']==uid]
    if ud.empty:
        return None
    ui = ud.iloc[0]
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<style>
body{{font-family:'Inter',sans-serif;background:#000;color:white;padding:40px}}
</style></head><body>
<h1>Respostas do Questionário</h1>
<p>Usuário: {animal}</p>
<p>Data: {ui.get('timestamp','N/A')}</p>
<ul>
<li>Q1: {ui.get('q1','N/A')}</li>
<li>Q2: {ui.get('q2','N/A')}</li>
<li>Q3: {ui.get('q3','N/A')}</li>
</ul>
</body></html>"""

def html_tags(uid, animal, obras, tags_df):
    ut = tags_df[tags_df['user_id']==uid] if not tags_df.empty else pd.DataFrame()
    if ut.empty:
        return None
    od = {o['id']:o for o in obras}
    rows = "".join(
        f"<tr><td>{i+1}</td>"
        f"<td>{od.get(r['obra_id'],{}).get('titulo','Obra '+str(r['obra_id']))}</td>"
        f"<td>{r['tag']}</td><td>{r['timestamp']}</td></tr>"
        for i,(_,r) in enumerate(ut.iterrows())
    )
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<style>
body{{font-family:'Inter',sans-serif;background:#000;color:white;padding:40px}}
table{{border-collapse:collapse;width:100%}}
th,td{{border:1px solid #555;padding:8px}}
</style></head><body>
<h1>Tags do usuário {animal}</h1>
<table><thead><tr><th>#</th><th>Obra</th><th>Tag</th><th>Data</th></tr></thead>
<tbody>{rows}</tbody></table></body></html>"""

# ───────────────────────────────────────────────────────────────────────
# HEADER
# ───────────────────────────────────────────────────────────────────────
def show_header():
    st.markdown(
        "<div class='top-navbar'>"
        "<div>"
        "<div class='navbar-logo'>📚 Folksonomia Digital</div>"
        "<div class='navbar-sub'>Sistema colaborativo de catalogação de arte</div>"
        "</div>"
        "</div>",
        unsafe_allow_html=True
    )

# ───────────────────────────────────────────────────────────────────────
# INTRO / QUESTIONÁRIO
# ───────────────────────────────────────────────────────────────────────
def show_intro():
    st.markdown("<div class='main-content'>", unsafe_allow_html=True)
    st.markdown("<h1 class='main-title'>Sistema Folksonomia Digital</h1>", unsafe_allow_html=True)
    st.markdown(
        "<p class='subtitle'>Sistema colaborativo de catalogação de obras de arte<br>"
        "Contribua com suas perspectivas únicas sobre cada obra</p>",
        unsafe_allow_html=True
    )
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.markdown("<h2 style='text-align:center;margin-bottom:2rem;font-size:1.6rem'>Questionário de Acesso</h2>", unsafe_allow_html=True)

    with st.form("intro_form"):
        c1, c2 = st.columns(2)
        with c1:
            q1 = st.selectbox(
                "1. Nível de familiaridade com museus:",
                ["Nunca visito museus","Visito raramente","Visito ocasionalmente","Visito frequentemente"]
            )
            q2 = st.selectbox(
                "2. Conhecimento sobre documentação museológica:",
                ["Nunca ouvi falar","Já ouvi, mas não sei o que é","Tenho uma ideia básica","Conheço bem o tema"]
            )
        with c2:
            q3 = st.text_area(
                "3. O que você entende por 'tags' ou etiquetas digitais aplicadas a acervo?",
                max_chars=500,
                height=195,
                placeholder="Descreva sua compreensão sobre o conceito de tags em sistemas digitais..."
            )
        submit = st.form_submit_button(" Acessar a Plataforma", use_container_width=True)
        if submit:
            if not q3.strip():
                st.error("Por favor, responda todas as perguntas para continuar!")
            else:
                st.session_state['answers'] = {"q1":q1,"q2":q2,"q3":q3}
                save_answers(st.session_state['user_id'], st.session_state['animal_name'], st.session_state['answers'])
                st.session_state['step'] = 'completed'
                st.success("Questionário completo! Acesso liberado.")
                st.balloons()
                st.rerun()

    st.markdown("</div></div>", unsafe_allow_html=True)

# ───────────────────────────────────────────────────────────────────────
# GALERIA DE OBRAS
# ───────────────────────────────────────────────────────────────────────
def show_obras():
    st.markdown("<h1 class='main-title'>Galeria de Obras de Arte</h1>", unsafe_allow_html=True)
    st.markdown("<p class='subtitle'>Explore, filtre e contribua com suas tags descritivas</p>", unsafe_allow_html=True)
    obras = load_obras()
    tdf   = all_tags()
    if not obras:
        st.info("Nenhuma obra cadastrada.")
        return

    # Filtros simples
    with st.expander("Filtros", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            busca_titulo = st.text_input("Buscar por título:", "")
            busca_artista = st.text_input("Filtrar por artista:", "")
        with col2:
            anos_disponiveis = sorted(set(str(o.get('ano','')) for o in obras if o.get('ano')))
            ano_sel = st.multiselect("Ano(s):", anos_disponiveis)
            categorias = sorted(set(o.get('categoria','Pintura') for o in obras))
            cat_sel = st.multiselect("Categoria:", categorias)
        with col3:
            if not tdf.empty:
                all_unique_tags = sorted(tdf['tag'].unique().tolist())
                tags_filtro = st.multiselect("Obras com estas tags:", all_unique_tags[:50])
            else:
                tags_filtro = []
            sord = st.selectbox("Ordenar por:", [
                "Número ↑","Número ↓","Título A-Z","Título Z-A",
                "Mais tagueadas","Menos tagueadas","Ano ↑","Ano ↓"
            ])

    # modo lista x grade
    col_vm1, col_vm2 = st.columns(2)
    with col_vm1:
        if st.button("⊞ Grade"):
            st.session_state['view_mode'] = 'grid'
    with col_vm2:
        if st.button("☰ Lista"):
            st.session_state['view_mode'] = 'list'
    view_mode = st.session_state.get('view_mode','grid')

    # aplica filtros
    filtered = obras[:]
    if busca_titulo.strip():
        filtered = [o for o in filtered if busca_titulo.lower() in o['titulo'].lower()]
    if busca_artista.strip():
        filtered = [o for o in filtered if busca_artista.lower() in o.get('artista','').lower()]
    if ano_sel:
        filtered = [o for o in filtered if str(o.get('ano','')) in ano_sel]
    if cat_sel:
        filtered = [o for o in filtered if o.get('categoria','Pintura') in cat_sel]
    if tags_filtro and not tdf.empty:
        obras_com_tags = set()
        for tag in tags_filtro:
            obras_com_tags |= set(tdf[tdf['tag']==tag]['obra_id'].tolist())
        filtered = [o for o in filtered if o['id'] in obras_com_tags]

    tag_count_per_obra = {}
    if not tdf.empty:
        tc = tdf.groupby('obra_id').size().to_dict()
        tag_count_per_obra = tc

    def sort_key(o):
        tc = tag_count_per_obra.get(o['id'], 0)
        try:
            yr = int(o.get('ano',0))
        except:
            yr = 0
        if sord == "Número ↑": return o['id']
        if sord == "Número ↓": return -o['id']
        if sord == "Título A-Z": return o['titulo']
        if sord == "Título Z-A": return [-ord(c) for c in o['titulo']]
        if sord == "Mais tagueadas": return -tc
        if sord == "Menos tagueadas": return tc
        if sord == "Ano ↑": return yr
        if sord == "Ano ↓": return -yr
        return o['id']

    try:
        filtered = sorted(filtered, key=sort_key)
    except:
        pass

    st.markdown(
        f"<div style='text-align:center;margin:1.5rem 0;font-size:1rem;font-weight:600'>"
        f"Exibindo <strong style='font-size:1.4rem;color:#60a5fa'>{len(filtered)}</strong> "
        f"de {len(obras)} obra(s) · Modo: {'Grade' if view_mode=='grid' else 'Lista'}"
        f"</div>",
        unsafe_allow_html=True
    )

    if not filtered:
        st.warning("Nenhuma obra encontrada com os filtros aplicados.")
        return

    if view_mode == 'grid':
        render_grid(filtered, tag_count_per_obra, tdf)
    else:
        render_list(filtered, tag_count_per_obra, tdf)

def render_grid(obras, tag_count_per_obra, tdf):
    cols = st.columns(3)
    for i, obra in enumerate(obras):
        with cols[i % 3]:
            tc = tag_count_per_obra.get(obra['id'], 0)
            audio_desc = AUDIO_DESCRIPTIONS.get(obra['id'], obra.get('descricao','Sem descrição.'))
            st.markdown(f"""
<div class='obra-card'>
  <img src='{obra['imagem']}' alt='{obra['titulo']} — {obra.get('artista','')}' />
  <div style='padding:1.2rem'>
    <h3 style='font-size:1rem;font-weight:800;margin-bottom:.2rem'>{obra['titulo']}</h3>
    <p style='font-size:.82rem;opacity:.65;margin-bottom:.3rem'>
      {obra.get('artista','')} · {obra.get('ano','')}
    </p>
    <p style='font-size:.78rem;opacity:.5'>{obra.get('categoria','Pintura')} · {obra.get('tecnica','')}</p>
    <div style='margin-top:.5rem'>
      <span class='tag-badge'> {tc} tags</span>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

            # áudio-descrição: apenas chama speak()
            if st.button("🔊 Ouvir áudio-descrição", key=f"audio_{obra['id']}", use_container_width=True):
                st.markdown(
                    f"<script> speak(`{audio_desc.replace('`','')} `); </script>",
                    unsafe_allow_html=True
                )

            if st.button("Adicionar Tag", key=f"btn_{obra['id']}", use_container_width=True):
                st.session_state['selected_obra'] = obra
                st.rerun()

            if ('selected_obra' in st.session_state and
                st.session_state['selected_obra']['id'] == obra['id']):
                render_tag_form(obra)

            ut = get_obra_user_tags(obra['id'], st.session_state['user_id'])
            if not ut.empty:
                st.markdown("**Suas Tags:**")
                st.markdown("".join(
                    f"<span class='tag-badge'>{r['tag']} "
                    f"<span style='opacity:.5;font-size:.75rem'>({r['count']}×)</span></span>"
                    for _, r in ut.iterrows()
                ), unsafe_allow_html=True)
            else:
                st.markdown(
                    "<div class='sc' style='padding:.6rem;text-align:center;font-size:.82rem;opacity:.55'>"
                    "Você ainda não criou tags para esta obra</div>",
                    unsafe_allow_html=True
                )

def render_list(obras, tag_count_per_obra, tdf):
    for obra in obras:
        tc = tag_count_per_obra.get(obra['id'], 0)
        audio_desc = AUDIO_DESCRIPTIONS.get(obra['id'], obra.get('descricao','Sem descrição.'))
        all_obra_tags = []
        if not tdf.empty:
            obra_tags = tdf[tdf['obra_id']==obra['id']]['tag'].value_counts().head(5)
            all_obra_tags = [f"<span class='tag-badge' style='font-size:.72rem'>{t}</span>" for t in obra_tags.index]

        st.markdown(f"""
<div class='obra-list-item'>
  <img src='{obra['imagem']}' alt='{obra['titulo']}' class='obra-list-img'/>
  <div style='flex:1'>
    <div style='display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px'>
      <div>
        <h3 style='font-size:1.05rem;font-weight:800;margin-bottom:.25rem'>
          #{obra['id']} · {obra['titulo']}
        </h3>
        <p style='font-size:.85rem;opacity:.7;margin-bottom:.2rem'>
          {obra.get('artista','')} · {obra.get('ano','')}
        </p>
        <p style='font-size:.78rem;opacity:.5'>
          {obra.get('categoria','Pintura')} · {obra.get('tecnica','')} · {obra.get('dimensoes','')}
        </p>
      </div>
      <span class='tag-badge'>{tc} tags</span>
    </div>
    <p style='font-size:.82rem;opacity:.65;margin:.5rem 0;line-height:1.6'>
      {obra.get('descricao','')}
    </p>
    <div>{''.join(all_obra_tags) if all_obra_tags else "<span style='font-size:.78rem;opacity:.4'>Sem tags ainda</span>"}</div>
  </div>
</div>
""", unsafe_allow_html=True)

        lc1, lc2 = st.columns(2)
        with lc1:
            if st.button("Adicionar Tag", key=f"list_btn_{obra['id']}", use_container_width=True):
                st.session_state['selected_obra'] = obra
                st.rerun()
        with lc2:
            if st.button("🔊 Ouvir áudio-descrição", key=f"list_audio_{obra['id']}", use_container_width=True):
                st.markdown(
                    f"<script> speak(`{audio_desc.replace('`','')} `); </script>",
                    unsafe_allow_html=True
                )

        if ('selected_obra' in st.session_state and
            st.session_state['selected_obra']['id'] == obra['id']):
            render_tag_form(obra)

        ut = get_obra_user_tags(obra['id'], st.session_state['user_id'])
        if not ut.empty:
            st.markdown("**Suas Tags:** " + "".join(
                f"<span class='tag-badge'>{r['tag']} ({r['count']}×)</span>"
                for _, r in ut.iterrows()
            ), unsafe_allow_html=True)

def render_tag_form(obra):
    with st.form(f"tf_{obra['id']}"):
        tag = st.text_input(
            "Nova tag:",
            key=f"t_{obra['id']}",
            placeholder="Ex: melancólico, azul noturno, abstrato…"
        )
        sugestoes = ["guerra","paz","dor","esperança","escuridão","luz","natureza",
                     "movimento","silêncio","beleza","mistério","emoção"]
        st.markdown(
            "**Sugestões:** " +
            " ".join(f"<span class='tag-badge'>{s}</span>" for s in sugestoes[:8]),
            unsafe_allow_html=True
        )
        ca, cb = st.columns(2)
        with ca:
            sub = st.form_submit_button("Enviar Tag", use_container_width=True)
        with cb:
            can = st.form_submit_button("Cancelar", use_container_width=True)
        if sub and tag:
            if len(tag.strip()) < 2:
                st.error("Tag deve ter ao menos 2 caracteres.")
            else:
                save_tag(st.session_state['user_id'], obra['id'], tag)
                st.success(f"Tag '{tag}' adicionada com sucesso!")
                del st.session_state['selected_obra']
                st.rerun()
        if can:
            del st.session_state['selected_obra']
            st.rerun()

# ───────────────────────────────────────────────────────────────────────
# ÁREA ADMINISTRATIVA (SIMPLIFICADA)
# ───────────────────────────────────────────────────────────────────────
def show_admin():
    if 'admin_logged_in' not in st.session_state:
        st.session_state['admin_logged_in'] = False

    if not st.session_state['admin_logged_in']:
        st.markdown("<h1 class='main-title'>⚙️ Área Administrativa</h1>", unsafe_allow_html=True)
        _, c2, _ = st.columns([1,1,1])
        with c2:
            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
            st.markdown("<h2 style='text-align:center;margin-bottom:1.5rem'>🔐 Login</h2>", unsafe_allow_html=True)
            with st.form("login"):
                username = st.text_input("Usuário:")
                password = st.text_input("Senha:", type="password")
                sub = st.form_submit_button("Entrar no Sistema", use_container_width=True)
                if sub:
                    if check_login(username, password):
                        st.session_state['admin_logged_in'] = True
                        st.session_state['admin_username'] = username
                        st.success("Login realizado!")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("Credenciais inválidas. Acesso negado.")
            st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.markdown(
            f"<h1 class='main-title'>Dashboard Administrativo</h1>"
            f"<p class='subtitle'>Bem-vindo, <strong>{st.session_state.get('admin_username','Admin')}</strong></p>",
            unsafe_allow_html=True
        )
        tabs = st.tabs([
            "Visão Geral",
            "Análise de Tags",
            "Coocorrências",
            "Usuários",
            "Obras",
            "Exportar"
        ])
        with tabs[0]: tab_overview()
        with tabs[1]: tab_tags_simple()
        with tabs[2]: tab_cooccurrence()
        with tabs[3]: tab_users_quest()
        with tabs[4]: tab_obras()
        with tabs[5]: tab_export()

        _, c2, _ = st.columns([1,1,1])
        with c2:
            if st.button("Sair do Sistema", use_container_width=True):
                st.session_state['admin_logged_in'] = False
                st.rerun()

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
    with c1: st.markdown(kpi("Total Tags", total,"registros","#60a5fa"), unsafe_allow_html=True)
    with c2: st.markdown(kpi("Tags Únicas", unicas,"","#a78bfa"), unsafe_allow_html=True)
    with c3: st.markdown(kpi("Participantes", nusers,"usuários","#34d399"), unsafe_allow_html=True)
    with c4: st.markdown(kpi("Obras", nobs,f"{obs_ct} com tags","#fbbf24"), unsafe_allow_html=True)
    with c5:
        media = f"{total/nusers:.1f}" if nusers else "—"
        st.markdown(kpi("Média/Usuário", media,"tags","#f472b6"), unsafe_allow_html=True)

    st.markdown(divider(), unsafe_allow_html=True)

    if not tdf.empty:
        st.markdown("#### Resumo por Obra")
        od = {o['id']:o['titulo'] for o in obs}
        ot = tdf.groupby('obra_id').agg(
            Tags=('tag','count'),
            Tags_Unicas=('tag','nunique'),
            Usuarios=('user_id','nunique')
        ).reset_index()
        ot['Obra'] = ot['obra_id'].map(od)
        st.dataframe(
            ot[['Obra','Tags','Tags_Unicas','Usuarios']].rename(columns={
                'Tags':'Total','Tags_Unicas':'Únicas','Usuarios':'Usuários'
            }).sort_values('Total',ascending=False),
            use_container_width=True,
            hide_index=True
        )

def tab_tags_simple():
    tdf = all_tags()
    if tdf.empty:
        st.info("Nenhuma tag disponível.")
        return

    st.markdown("### Análise de Tags (Frequência)")

    freq = tdf['tag'].value_counts().reset_index()
    freq.columns = ['Tag','Frequência']
    total_usos = freq['Frequência'].sum()
    freq['% do Total']  = (freq['Frequência']/total_usos*100).round(2)
    st.markdown("#### Top 25 Tags")
    st.bar_chart(tdf['tag'].value_counts().head(25))

    st.markdown("#### Tabela Completa")
    st.dataframe(freq, use_container_width=True, hide_index=True)
    st.download_button(
        "Frequências (CSV)",
        freq.to_csv(index=False).encode('utf-8'),
        f"frequencias_{datetime.now().strftime('%Y%m%d')}.csv",
        "text/csv",
        use_container_width=True
    )

def tab_cooccurrence():
    tdf = all_tags()
    obs = load_obras()

    if tdf.empty:
        st.info("Nenhuma tag disponível.")
        return

    st.markdown("### Análise de Coocorrência de Tags")

    c1, c2 = st.columns([1,2])
    with c1:
        top_n = st.slider("Top N tags para matriz:", 5, 20, 10, 1)
        obra_f2 = st.selectbox(
            "Filtrar por obra:",
            ["Todas"]+[f"#{o['id']} — {o['titulo']}" for o in obs]
        )

    fdf2 = tdf.copy()
    if obra_f2 != "Todas":
        oid2 = int(obra_f2.split("—")[0].replace("#","").strip())
        fdf2 = tdf[tdf['obra_id']==oid2]

    matrix = tag_cooccurrence(fdf2, top_n=top_n)

    if matrix.empty:
        st.info("Dados insuficientes para calcular coocorrências.")
        return

    st.dataframe(matrix, use_container_width=True)

    # Top pares
    pairs = []
    tags_list = list(matrix.columns)
    for i, t1_tag in enumerate(tags_list):
        for j, t2_tag in enumerate(tags_list):
            if j > i:
                v = matrix.loc[t1_tag, t2_tag]
                if v > 0:
                    pairs.append({'Tag A': t1_tag, 'Tag B': t2_tag, 'Coocorrências': int(v)})
    if pairs:
        pairs_df = pd.DataFrame(pairs).sort_values('Coocorrências', ascending=False).head(20)
        st.markdown("#### Top Pares de Coocorrência")
        st.dataframe(pairs_df, use_container_width=True, hide_index=True)

def tab_users_quest():
    tdf = all_tags()
    udf = all_users()
    obs = load_obras()

    if udf.empty:
        st.info("Nenhum dado de usuário disponível.")
        return

    st.markdown("### Usuários & Questionário")

    uct = tdf.groupby('user_id').size().reset_index(name='Total_Tags') if not tdf.empty else pd.DataFrame(columns=['user_id','Total_Tags'])
    uuq = tdf.groupby('user_id')['tag'].nunique().reset_index(name='Tags_Unicas') if not tdf.empty else pd.DataFrame(columns=['user_id','Tags_Unicas'])
    uob = tdf.groupby('user_id')['obra_id'].nunique().reset_index(name='Obras') if not tdf.empty else pd.DataFrame(columns=['user_id','Obras'])

    merged = udf.merge(uct,on='user_id',how='left') \
                .merge(uuq,on='user_id',how='left') \
                .merge(uob,on='user_id',how='left').fillna(0)
    merged['Usuário'] = merged.apply(lambda r: r.get('animal_name', r['user_id'][:8]), axis=1)

    st.dataframe(
        merged[['Usuário','Total_Tags','Tags_Unicas','Obras','q1','q2']],
        use_container_width=True,
        hide_index=True
    )

    st.markdown(divider(), unsafe_allow_html=True)
    st.markdown("#### Q3 — Respostas abertas sobre tags")
    disp = merged.copy()
    if 'animal_name' in disp.columns:
        disp = disp.rename(columns={'animal_name':'Usuário Anônimo'})
    st.dataframe(
        disp[['Usuário Anônimo','q3','timestamp']].rename(columns={'q3':'Resposta','timestamp':'Data/Hora'}),
        use_container_width=True,
        hide_index=True
    )

def tab_obras():
    st.markdown("### Gestão de Obras")
    obras = load_obras()
    t1, t2 = st.tabs(["Listar Obras","Adicionar Nova"])

    with t1:
        if obras:
            for obra in obras:
                c1,c2,c3 = st.columns([1,3,1])
                with c1:
                    st.image(obra['imagem'], use_container_width=True)
                with c2:
                    st.markdown(f"**#{obra['id']} — {obra['titulo']}**")
                    st.markdown(f"*{obra.get('artista','')} · {obra.get('ano','')}*")
                    st.markdown(f"Categoria: {obra.get('categoria','—')} · Técnica: {obra.get('tecnica','—')}")
                    st.markdown(f"Dimensões: {obra.get('dimensoes','—')}")
                    if obra.get('descricao'):
                        st.markdown(f"_{obra['descricao']}_")
                with c3:
                    if st.button("Remover", key=f"del_{obra['id']}"):
                        obras.remove(obra)
                        save_json_file(OBRAS_FILE, obras)
                        st.cache_data.clear()
                        st.rerun()
                st.divider()
        else:
            st.info("Nenhuma obra cadastrada.")

    with t2:
        with st.form("add_obra"):
            c1, c2 = st.columns(2)
            with c1:
                titulo   = st.text_input("Título da Obra*")
                artista  = st.text_input("Artista*")
                ano      = st.text_input("Ano*")
                imagem   = st.text_input("URL da Imagem*")
            with c2:
                categoria  = st.selectbox("Categoria:", ["Pintura","Escultura","Fotografia","Gravura","Desenho","Arte Digital","Outro"])
                tecnica    = st.text_input("Técnica:", placeholder="Ex: Óleo sobre tela")
                dimensoes  = st.text_input("Dimensões:", placeholder="Ex: 100 × 80 cm")
                descricao  = st.text_area("Descrição / Áudio-descrição:", height=100,
                                          placeholder="Descrição acessível da obra…")
            if st.form_submit_button("Adicionar Obra", use_container_width=True):
                if titulo and artista and ano and imagem:
                    nid = max([o['id'] for o in obras])+1 if obras else 1
                    obras.append({
                        "id":nid,"titulo":titulo,"artista":artista,"ano":ano,
                        "categoria":categoria,"tecnica":tecnica,"dimensoes":dimensoes,
                        "descricao":descricao,"imagem":imagem
                    })
                    save_json_file(OBRAS_FILE, obras)
                    st.success("Obra adicionada com sucesso!")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("Preencha os campos obrigatórios (*)")

def tab_export():
    st.markdown("### Central de Exportação")
    tdf  = all_tags()
    udf  = all_users()
    obs  = load_obras()

    t1, t2 = st.tabs(["Exportação Geral","Por Participante"])

    with t1:
        c1,c2,c3 = st.columns(3)
        with c1:
            st.markdown("#### Tags")
            if not tdf.empty:
                st.download_button(
                    "Todas as Tags (CSV)",
                    tdf.to_csv(index=False).encode('utf-8'),
                    f"tags_{datetime.now().strftime('%Y%m%d')}.csv",
                    "text/csv",
                    use_container_width=True
                )
                freq = tdf['tag'].value_counts().reset_index()
                freq.columns=['Tag','Frequência']
                freq['%']=(freq['Frequência']/freq['Frequência'].sum()*100).round(2)
                st.download_button(
                    "Frequências (CSV)",
                    freq.to_csv(index=False).encode('utf-8'),
                    f"freq_{datetime.now().strftime('%Y%m%d')}.csv",
                    "text/csv",
                    use_container_width=True
                )
        with c2:
            st.markdown("#### Usuários")
            if not udf.empty:
                st.download_button(
                    "Usuários (CSV)",
                    udf.to_csv(index=False).encode('utf-8'),
                    f"usuarios_{datetime.now().strftime('%Y%m%d')}.csv",
                    "text/csv",
                    use_container_width=True
                )
        with c3:
            st.markdown("#### Obras")
            if obs:
                st.download_button(
                    "Obras (CSV)",
                    pd.DataFrame(obs).to_csv(index=False).encode('utf-8'),
                    f"obras_{datetime.now().strftime('%Y%m%d')}.csv",
                    "text/csv",
                    use_container_width=True
                )

    with t2:
        if udf.empty:
            st.info("Nenhum participante.")
            return
        uopts = [f"🐾 {r.get('animal_name',r['user_id'][:8])}" for _,r in udf.iterrows()]
        usel  = st.selectbox("Participante:", uopts)
        uidx  = uopts.index(usel)
        uid   = udf.iloc[uidx]['user_id']
        uanim = udf.iloc[uidx].get('animal_name', uid[:8])

        st.markdown(f"#### Dados de: **{uanim}**")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("##### Questionário")
            hq = html_quest(uid, uanim, udf)
            if hq:
                st.download_button("Respostas (HTML/PDF)", hq,
                    f"quest_{uid[:8]}.html","text/html", use_container_width=True)
            ud = udf[udf['user_id']==uid]
            if not ud.empty:
                st.download_button(
                    "Respostas (CSV)",
                    ud.to_csv(index=False).encode('utf-8'),
                    f"quest_{uid[:8]}.csv",
                    "text/csv",
                    use_container_width=True
                )
        with c2:
            st.markdown("##### Tags Criadas")
            ht = html_tags(uid, uanim, obs, tdf)
            if ht:
                st.download_button(
                    "Tags (HTML/PDF)", ht,
                    f"tags_{uid[:8]}.html","text/html", use_container_width=True
                )
            ut = get_user_tags(uid)
            if not ut.empty:
                st.download_button(
                    "Tags (CSV)",
                    ut.to_csv(index=False).encode('utf-8'),
                    f"tags_{uid[:8]}.csv",
                    "text/csv",
                    use_container_width=True
                )

# ───────────────────────────────────────────────────────────────────────
# MAIN
# ───────────────────────────────────────────────────────────────────────
def main():
    for k, v in [
        ('user_id', gen_uid()),
        ('animal_name', generate_animal_name()),
        ('step', 'intro'),
        ('answers', {}),
        ('theme', 'dark'),
        ('font_size', 'medium'),
        ('high_contrast', False),
        ('view_mode', 'grid')
    ]:
        if k not in st.session_state:
            st.session_state[k] = v

    load_css()
    render_accessibility_bar()

    try:
        check_admin()
    except Exception as e:
        st.error(f"Erro ao inicializar: {e}")

    # botões simples de acessibilidade na parte superior
    with st.container():
        a1, a2, a3, a4, _ = st.columns([1,1,1,1,4])
        with a1:
            if st.button("🌙/☀️ Tema"):
                st.session_state['theme'] = 'light' if st.session_state['theme']=='dark' else 'dark'
                st.rerun()
        with a2:
            if st.button("A+"):
                sizes = ['small','medium','large','xlarge']
                idx = sizes.index(st.session_state.get('font_size','medium'))
                st.session_state['font_size'] = sizes[min(idx+1, 3)]
                st.rerun()
        with a3:
            if st.button("A-"):
                sizes = ['small','medium','large','xlarge']
                idx = sizes.index(st.session_state.get('font_size','medium'))
                st.session_state['font_size'] = sizes[max(idx-1, 0)]
                st.rerun()
        with a4:
            if st.button("Contraste"):
                st.session_state['high_contrast'] = not st.session_state.get('high_contrast', False)
                st.rerun()

    if st.session_state['step'] != 'completed':
        show_intro()
    else:
        show_header()
        st.markdown("<div class='main-content'>", unsafe_allow_html=True)
        t1, t2 = st.tabs(["Explorar Obras", "Área Administrativa"])
        with t1: show_obras()
        with t2: show_admin()
        st.markdown("</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
