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

# ── CSS ───────────────────────────────────────────────────────────────
def load_css():
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800&display=swap');
*{margin:0;padding:0;box-sizing:border-box;font-family:'Poppins',sans-serif!important}
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
    return obras

def save_answers(uid, animal, answers):
    users = load_json_file(USERS_FILE, [])
    users.append({"user_id":uid,"animal_name":animal,
                  "timestamp":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),**answers})
    return save_json_file(USERS_FILE, users)

def save_tag(uid, obra_id, tag):
    tags = load_json_file(TAGS_FILE, [])
    tags.append({"id":len(tags)+1,"user_id":uid,"obra_id":obra_id,
                 "tag":tag.lower().strip(),
                 "timestamp":datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
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
            " Obras",
            " Exportar"
        ])
        with tabs[0]: tab_overview()
        with tabs[1]: tab_tags()
        with tabs[2]: tab_connections()
        with tabs[3]: tab_users_quest()
        with tabs[4]: tab_obras()
        with tabs[5]: tab_export()
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
                        obras.remove(obra)
                        save_json_file(OBRAS_FILE, obras)
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
            if st.form_submit_button(" Adicionar Obra"):
                if titulo and artista and ano and imagem:
                    nid = max([o['id'] for o in obras])+1 if obras else 1
                    obras.append({"id":nid,"titulo":titulo,"artista":artista,"ano":ano,"imagem":imagem})
                    save_json_file(OBRAS_FILE, obras)
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
                st.download_button(" Todas as Tags (CSV)",
                    tdf.to_csv(index=False).encode('utf-8'),
                    f"tags_{datetime.now().strftime('%Y%m%d')}.csv","text/csv",
                    use_container_width=True)
                freq = tdf['tag'].value_counts().reset_index()
                freq.columns=['Tag','Frequência']
                freq['%']=(freq['Frequência']/freq['Frequência'].sum()*100).round(2)
                st.download_button(" Frequências (CSV)",
                    freq.to_csv(index=False).encode('utf-8'),
                    f"freq_{datetime.now().strftime('%Y%m%d')}.csv","text/csv",
                    use_container_width=True)
        with c2:
            st.markdown("#### Usuários")
            if not udf.empty:
                st.download_button(" Usuários (CSV)",
                    udf.to_csv(index=False).encode('utf-8'),
                    f"usuarios_{datetime.now().strftime('%Y%m%d')}.csv","text/csv",
                    use_container_width=True)
        with c3:
            st.markdown("#### Obras")
            if obs:
                st.download_button(" Obras (CSV)",
                    pd.DataFrame(obs).to_csv(index=False).encode('utf-8'),
                    f"obras_{datetime.now().strftime('%Y%m%d')}.csv","text/csv",
                    use_container_width=True)

        st.markdown(divider(), unsafe_allow_html=True)
        st.markdown("#### Exportar Conexões de Tags")
        if not tdf.empty:
            thr = st.slider("Limiar de similaridade:", 0.2, 0.9, 0.35, 0.05, key="exp_thr")
            if st.button("Gerar arquivo de conexões"):
                with st.spinner("Calculando…"):
                    conns = tag_connections(tdf['tag'].tolist(), threshold=thr)
                if conns:
                    cdf = pd.DataFrame(conns)
                    st.download_button(" Conexões (CSV)",
                        cdf.to_csv(index=False).encode('utf-8'),
                        f"conexoes_{datetime.now().strftime('%Y%m%d')}.csv","text/csv",
                        use_container_width=True)
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
                st.download_button(" Respostas (HTML/PDF)", hq,
                    f"quest_{uid[:8]}.html","text/html", use_container_width=True)
            ud = udf[udf['user_id']==uid]
            if not ud.empty:
                st.download_button(" Respostas (CSV)",
                    ud.to_csv(index=False).encode('utf-8'),
                    f"quest_{uid[:8]}.csv","text/csv", use_container_width=True)
        with c2:
            st.markdown("##### Tags Criadas")
            ht = html_tags(uid, uanim, obs, tdf)
            if ht:
                st.download_button(" Tags (HTML/PDF)", ht,
                    f"tags_{uid[:8]}.html","text/html", use_container_width=True)
            ut = get_user_tags(uid)
            if not ut.empty:
                st.download_button(" Tags (CSV)",
                    ut.to_csv(index=False).encode('utf-8'),
                    f"tags_{uid[:8]}.csv","text/csv", use_container_width=True)

if __name__ == "__main__":
    main()
