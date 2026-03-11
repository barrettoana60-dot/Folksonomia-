import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
import os
from datetime import datetime
import hashlib, base64, json, random, warnings, math
from collections import defaultdict
warnings.filterwarnings('ignore')

st.set_page_config(page_title="Sistema Folksonomia Digital",
                   layout="wide", initial_sidebar_state="collapsed", page_icon="📚")

DATA_DIR   = "data"
OBRAS_FILE = os.path.join(DATA_DIR,"obras.json")
TAGS_FILE  = os.path.join(DATA_DIR,"tags.json")
USERS_FILE = os.path.join(DATA_DIR,"users.json")
ADMIN_FILE = os.path.join(DATA_DIR,"admin.json")
ADMIN_USERNAME = "nugep"
ADMIN_PASSWORD = "nugep123"

ANIMAIS   = ["Águia","Boto","Capivara","Doninha","Ema","Falcão","Gavião","Harpia","Irara","Jaguar",
             "Lontra","Mico","Onça","Paca","Quati","Raposa","Tamanduá","Urubu","Veado","Zorrilho",
             "Arara","Bugio","Caititu","Jaguatirica","Lobo","Mutum","Pirarucu","Tucano","Sucuri","Tatu"]
ADJETIVOS = ["Azul","Bravo","Calmo","Dourado","Esperto","Feroz","Gracioso","Intenso","Jovial","Lento",
             "Mágico","Nobre","Ousado","Preciso","Rápido","Sábio","Tímido","Único","Valente","Zeloso",
             "Curioso","Furtivo","Altivo","Sereno","Vibrante","Audaz","Brilhante","Corajoso","Distinto","Elegante"]

AUDIO_DESCRIPTIONS = {
    1: "Guernica. Obra de Pablo Picasso, criada em 1937. Pintura monumental em preto, branco e cinza, com quase 4 metros de altura por quase 8 de largura. Representa o bombardeio da cidade basca de Guernica na Guerra Civil Espanhola. Ao centro, um cavalo ferido com a boca aberta em agonia. À esquerda, uma mãe segura seu bebê morto, a cabeça jogada para trás em grito de desespero. Um touro observa a cena no canto superior esquerdo. Figuras humanas fragmentadas expressam horror e sofrimento. Uma lamparina ilumina a cena de cima. A obra é símbolo universal contra a violência da guerra.",
    2: "A Noite Estrelada. Pintura de Vincent van Gogh, de 1889. Óleo sobre tela de 73 por 92 centímetros. Paisagem noturna com céu dramático e turbilhonante, dominado por redemoinhos de azul profundo e branco dourado. Onze estrelas brilhantes e uma lua crescente iluminam o céu em movimento. À esquerda, um cipreste escuro sobe em espiral como uma chama. Na parte inferior, uma pequena vila tranquila com uma igreja cujo campanário aponta para o céu. Criada quando Van Gogh estava internado num sanatório em Saint-Rémy-de-Provence, na França. Pinceladas curtas transmitem movimento, emoção e intensidade ao céu noturno.",
    3: "Mona Lisa. Obra de Leonardo da Vinci, pintada entre 1503 e 1519. Óleo sobre madeira de álamo, com 77 centímetros de altura por 53 de largura. Retrato de mulher jovem, possivelmente Lisa Gherardini, esposa de um mercador florentino. A figura está sentada em posição de três quartos com as mãos sobrepostas no colo. Seu famoso sorriso é sutil e ambíguo, parecendo mudar conforme o ângulo de visão. Os olhos escuros parecem acompanhar quem a observa. Ao fundo, paisagem nebulosa com caminhos, pontes e água, pintada com a técnica de sfumato de Leonardo. Exposta no Museu do Louvre em Paris.",
}

def generate_animal_name():
    random.seed(); return f"{random.choice(ANIMAIS)} {random.choice(ADJETIVOS)}"

# ── CORE ──────────────────────────────────────────────────────────────
def ensure_data_dir():
    if not os.path.exists(DATA_DIR): os.makedirs(DATA_DIR)

def load_json_file(fp, default):
    ensure_data_dir()
    if os.path.exists(fp):
        try:
            with open(fp,'r',encoding='utf-8') as f: return json.load(f)
        except: return default
    return default

def save_json_file(fp, data):
    ensure_data_dir()
    try:
        with open(fp,'w',encoding='utf-8') as f: json.dump(data,f,ensure_ascii=False,indent=2)
        return True
    except Exception as e: st.error(f"Erro ao salvar: {e}"); return False

# ── SIMILARIDADE ──────────────────────────────────────────────────────
def ntag(t): return t.lower().strip()
def words(t): return set(ntag(t).split())
def ngrams(text,n=3):
    t=ntag(text); return set([t]) if len(t)<n else set(t[i:i+n] for i in range(len(t)-n+1))

def sim(t1,t2):
    a,b=ntag(t1),ntag(t2)
    if a==b: return 1.0
    if a in b or b in a: return 0.55+0.45*(min(len(a),len(b))/max(len(a),len(b)))
    w1,w2=words(t1),words(t2)
    if w1 and w2:
        j=len(w1&w2)/len(w1|w2)
        if j>=0.5: return j
    if len(a)>=3 and len(b)>=3:
        ng1,ng2=ngrams(a),ngrams(b)
        nj=len(ng1&ng2)/len(ng1|ng2) if ng1|ng2 else 0
        if nj>0:
            wj=len(w1&w2)/len(w1|w2) if w1|w2 else 0
            return 0.6*nj+0.4*wj
    return 0.0

def tag_connections(tags_list,threshold=0.35):
    uniq=list(set(ntag(t) for t in tags_list)); conns=[]
    for i in range(len(uniq)):
        for j in range(i+1,len(uniq)):
            s=sim(uniq[i],uniq[j])
            if s>=threshold:
                w1,w2=words(uniq[i]),words(uniq[j]); shared=w1&w2
                if uniq[i] in uniq[j] or uniq[j] in uniq[i]: tipo="Contenção"
                elif shared: tipo=f"Palavra comum: '{', '.join(shared)}'"
                else: tipo="Similaridade fonética"
                conns.append({"tag_a":uniq[i],"tag_b":uniq[j],"similaridade":round(s,3),"tipo":tipo})
    conns.sort(key=lambda x:x["similaridade"],reverse=True); return conns

def tag_clusters(tags_list,threshold=0.35):
    uniq=list(set(ntag(t) for t in tags_list)); conns=tag_connections(uniq,threshold)
    par={t:t for t in uniq}
    def find(x):
        while par[x]!=x: par[x]=par[par[x]]; x=par[x]
        return x
    def union(a,b):
        ra,rb=find(a),find(b)
        if ra!=rb: par[ra]=rb
    for c in conns: union(c["tag_a"],c["tag_b"])
    cl=defaultdict(list)
    for t in uniq: cl[find(t)].append(t)
    return [sorted(v) for v in cl.values() if len(v)>1]

# ── ÁUDIO REAL via components.html ────────────────────────────────────
def audio_speak(texto, key="spk"):
    safe = (texto.replace("\\","").replace("`","'")
                 .replace('"',"'").replace("\n"," ").replace("\r",""))
    components.html(f"""<!DOCTYPE html><html><head>
<style>
body{{margin:0;padding:5px 2px;background:transparent;font-family:Inter,sans-serif}}
.row{{display:flex;gap:6px;align-items:center;flex-wrap:wrap;margin-bottom:5px}}
button{{padding:6px 16px;border-radius:50px;font-size:12px;font-weight:700;
  cursor:pointer;transition:all .2s;outline:none}}
.play{{background:rgba(52,211,153,.25);color:#34d399;
  border:1px solid rgba(52,211,153,.5)}}
.play:hover{{background:rgba(52,211,153,.45)}}
.stop{{background:rgba(248,113,113,.2);color:#f87171;
  border:1px solid rgba(248,113,113,.45)}}
.stop:hover{{background:rgba(248,113,113,.4)}}
#st{{font-size:11px;color:rgba(180,210,255,.55);margin-left:4px}}
#txt{{font-size:11.5px;color:rgba(180,210,255,.72);line-height:1.55;
  background:rgba(52,211,153,.06);border:1px solid rgba(52,211,153,.2);
  border-radius:8px;padding:6px 10px;margin-top:3px;
  max-height:72px;overflow:auto}}
</style></head><body>
<div class="row">
  <button class="play" onclick="falar()">&#9654; Reproduzir</button>
  <button class="stop" onclick="parar()">&#9632; Parar</button>
  <span id="st"></span>
</div>
<div id="txt">{safe[:240]}{'…' if len(safe)>240 else ''}</div>
<script>
var TEXTO = `{safe}`;
function falar() {{
  if (!('speechSynthesis' in window)) {{
    document.getElementById('st').innerText = '⚠ Navegador sem suporte a voz';
    return;
  }}
  window.speechSynthesis.cancel();
  var u = new SpeechSynthesisUtterance(TEXTO);
  u.lang = 'pt-BR'; u.rate = 0.87; u.pitch = 1.0; u.volume = 1.0;
  function go() {{
    var vs = window.speechSynthesis.getVoices();
    var pt = vs.find(function(v) {{
      return v.lang && (v.lang.indexOf('pt') === 0);
    }});
    if (pt) u.voice = pt;
    u.onstart = function() {{ document.getElementById('st').innerText = '🔊 Reproduzindo…'; }};
    u.onend   = function() {{ document.getElementById('st').innerText = '✅ Concluído'; }};
    u.onerror = function(e) {{ document.getElementById('st').innerText = '⚠ ' + e.error; }};
    window.speechSynthesis.speak(u);
  }}
  var vs = window.speechSynthesis.getVoices();
  if (vs && vs.length > 0) {{ go(); }}
  else {{
    window.speechSynthesis.onvoiceschanged = function() {{ go(); }};
    window.speechSynthesis.getVoices();
    setTimeout(go, 400);
  }}
}}
function parar() {{
  window.speechSynthesis.cancel();
  document.getElementById('st').innerText = '⏹ Parado';
}}
</script></body></html>""", height=120, key=key)

# ── CSS ───────────────────────────────────────────────────────────────
def load_css():
    theme = st.session_state.get('theme','dark')
    fs    = int(st.session_state.get('font_size',16))
    hc    = st.session_state.get('high_contrast',False)

    if theme=='light':
        bg="#eef2fb"; card_bg="rgba(255,255,255,.93)"; card_brd="rgba(0,70,160,.18)"
        txt="#0d1b2e"; txt_m="rgba(13,27,46,.48)"; nav_bg="rgba(255,255,255,.93)"
        badge_bg="rgba(0,70,160,.09)"; badge_brd="rgba(0,70,160,.26)"
        btn_bg="rgba(0,70,160,.11)"; btn_hov="rgba(0,70,160,.24)"
        tab_bg="rgba(0,70,160,.07)"; tab_sel="rgba(0,70,160,.20)"
        sc_bg="rgba(0,70,160,.05)"; conn_bg="rgba(0,70,160,.04)"; conn_hov="rgba(0,70,160,.12)"
        inp_bg="rgba(0,70,160,.06)"; inp_brd="rgba(0,70,160,.22)"
        title_c="#0a172a"; sub_c="#1a3a6b"
        logo_grad="linear-gradient(135deg,#0048b3,#00a0cc)"
        kpi_bg="rgba(0,70,160,.08)"; kpi_brd="rgba(0,70,160,.18)"
        pbar_bg="rgba(0,70,160,.12)"
    else:
        bg="#050d1a"; card_bg="rgba(255,255,255,.09)"; card_brd="rgba(255,255,255,.16)"
        txt="#dce8f5"; txt_m="rgba(220,232,245,.40)"; nav_bg="rgba(5,13,26,.90)"
        badge_bg="rgba(255,255,255,.11)"; badge_brd="rgba(255,255,255,.23)"
        btn_bg="rgba(255,255,255,.11)"; btn_hov="rgba(255,255,255,.24)"
        tab_bg="rgba(255,255,255,.07)"; tab_sel="rgba(255,255,255,.20)"
        sc_bg="rgba(255,255,255,.06)"; conn_bg="rgba(255,255,255,.05)"; conn_hov="rgba(255,255,255,.10)"
        inp_bg="rgba(255,255,255,.09)"; inp_brd="rgba(255,255,255,.19)"
        title_c="#ffffff"; sub_c="rgba(255,255,255,.80)"
        logo_grad="linear-gradient(135deg,#7dd3fc,#c4b5fd)"
        kpi_bg="rgba(255,255,255,.09)"; kpi_brd="rgba(255,255,255,.17)"
        pbar_bg="rgba(255,255,255,.09)"

    hc_extra = f"body,.stApp,.stApp *{{color:{txt}!important;}}" if hc else ""

    st.markdown(f"""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

/* ═══ FONT SIZE — propagação completa ═══ */
html {{font-size:{fs}px!important;}}
body {{font-size:{fs}px!important;}}
.stApp, .stApp *:not(h1):not(h2):not(h3):not(h4):not(.kpi-val) {{
  font-family:'Inter',sans-serif!important;
}}
.stApp p,.stApp span,.stApp div,.stApp label,
.stApp input,.stApp textarea,.stApp li,
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] span,
[data-testid="stMarkdownContainer"] li,
.element-container p,.element-container span,
.stTextInput input,.stTextArea textarea,
.stSelectbox select, .stDataFrame td, .dataframe td
{{font-size:{fs}px!important;font-family:'Inter',sans-serif!important;}}
h1{{font-size:calc({fs}px * 2.0)!important;}}
h2{{font-size:calc({fs}px * 1.5)!important;}}
h3{{font-size:calc({fs}px * 1.22)!important;}}
h4{{font-size:calc({fs}px * 1.08)!important;}}
.stTabs [data-baseweb="tab"] span,
.stTabs [data-baseweb="tab"]{{font-size:calc({fs}px * 0.86)!important;}}
.stButton button{{font-size:calc({fs}px * 0.88)!important;}}
.tag-badge,.cluster-pill,.animal-badge,.kpi-lbl,.kpi-sub,.conn-row,.sc,.insight,
.obra-card,.obra-list-item,.filter-panel,.cluster-title,
.navbar-logo,.navbar-sub,.main-title,.subtitle
{{font-size:inherit!important;}}
{hc_extra}

/* ═══ BASE ═══ */
*{{margin:0;padding:0;box-sizing:border-box;font-family:'Inter',sans-serif!important;}}
@keyframes bgani{{0%{{background-position:0% 50%}}50%{{background-position:100% 50%}}100%{{background-position:0% 50%}}}}
@keyframes fadeUp{{from{{opacity:0;transform:translateY(16px)}}to{{opacity:1;transform:translateY(0)}}}}

.stApp{{
  background:{bg};
  {'animation:bgani 20s ease infinite;background:linear-gradient(-45deg,#050d1a 0%,#001230 35%,#050d1a 60%,#001a3a 85%,#050d1a 100%);background-size:400% 400%;' if theme=='dark' else ''}
  color:{txt};
}}

/* ═══ NAVBAR ═══ */
.top-navbar{{
  position:fixed;top:0;left:0;right:0;z-index:9999;
  background:{nav_bg};backdrop-filter:blur(22px) saturate(180%);
  border-bottom:1px solid {card_brd};padding:.85rem 2.5rem;
  display:flex;justify-content:space-between;align-items:center;
  box-shadow:0 2px 18px rgba(0,0,0,.14);
}}
.navbar-logo{{
  font-size:calc({fs}px * 1.35);font-weight:900;letter-spacing:-.5px;
  background:{logo_grad};-webkit-background-clip:text;
  -webkit-text-fill-color:transparent;background-clip:text;
}}
.navbar-sub{{font-size:calc({fs}px * 0.67);font-weight:500;color:{txt_m};
  letter-spacing:1px;text-transform:uppercase;margin-top:2px;}}

/* ═══ ACCESSIBILITY BAR ═══ */
.access-bar-wrap{{
  background:{sc_bg};border:1px solid {card_brd};border-radius:12px;
  padding:.55rem 1rem;margin:.45rem 0 .7rem;
  display:flex;align-items:center;gap:.4rem;flex-wrap:wrap;
}}
.access-label{{font-size:calc({fs}px * 0.68);font-weight:800;opacity:.52;
  text-transform:uppercase;letter-spacing:1px;margin-right:.3rem;white-space:nowrap;}}
.access-fsinfo{{font-size:calc({fs}px * 0.78);font-weight:700;opacity:.65;
  padding:.3rem .6rem;background:{kpi_bg};border-radius:8px;white-space:nowrap;}}

/* ═══ MAIN ═══ */
.main-content{{margin-top:68px;padding:1.5rem 2.2rem;max-width:1700px;margin-left:auto;margin-right:auto;}}

/* ═══ GLASS CARD ═══ */
.glass-card{{
  background:{card_bg};backdrop-filter:blur(20px) saturate(180%);
  border:1px solid {card_brd};border-radius:22px;padding:1.9rem;margin:.9rem 0;
  box-shadow:0 5px 26px rgba(0,0,0,.09);transition:all .35s cubic-bezier(.4,0,.2,1);
  position:relative;overflow:hidden;animation:fadeUp .45s ease both;
}}
.glass-card:hover{{transform:translateY(-5px);box-shadow:0 14px 44px rgba(0,0,0,.14);border-color:{badge_brd};}}

/* ═══ OBRA CARDS ═══ */
.obra-card{{
  background:{card_bg};backdrop-filter:blur(15px);
  border:1px solid {card_brd};border-radius:20px;overflow:hidden;
  transition:all .4s cubic-bezier(.4,0,.2,1);position:relative;
}}
.obra-card:hover{{transform:translateY(-10px) scale(1.02);
  box-shadow:0 18px 52px rgba(0,0,0,.22);border-color:{badge_brd};}}
.obra-card img{{width:100%;height:248px;object-fit:cover;
  transition:transform .6s cubic-bezier(.4,0,.2,1);display:block;}}
.obra-card:hover img{{transform:scale(1.09);}}
.obra-num{{position:absolute;top:10px;left:10px;z-index:10;
  background:rgba(0,0,0,.6);backdrop-filter:blur(8px);
  color:white;padding:.2rem .65rem;border-radius:50px;
  font-size:calc({fs}px * 0.72);font-weight:800;letter-spacing:1px;}}

/* ═══ LIST ITEM ═══ */
.obra-list-item{{
  display:flex;gap:1.1rem;align-items:flex-start;
  background:{card_bg};backdrop-filter:blur(15px);
  border:1px solid {card_brd};border-radius:17px;padding:1rem;margin:.5rem 0;
  transition:all .3s cubic-bezier(.4,0,.2,1);animation:fadeUp .4s ease both;
}}
.obra-list-item:hover{{transform:translateX(5px);border-color:{badge_brd};
  box-shadow:0 5px 22px rgba(0,0,0,.11);}}
.obra-list-img{{width:128px;min-width:128px;height:88px;object-fit:cover;border-radius:10px;}}

/* ═══ TYPOGRAPHY ═══ */
.main-title{{
  color:{title_c};font-size:calc({fs}px * 2.1);font-weight:900;
  text-align:center;margin:1.4rem 0 .7rem;letter-spacing:-1.5px;animation:fadeUp .55s ease both;
}}
.subtitle{{
  color:{sub_c};font-size:calc({fs}px * 1.04);text-align:center;
  margin-bottom:2.2rem;line-height:1.75;font-weight:400;animation:fadeUp .65s ease both;
}}

/* ═══ TAGS ═══ */
.tag-badge{{
  display:inline-flex;align-items:center;gap:3px;
  background:{badge_bg};backdrop-filter:blur(8px);
  border:1px solid {badge_brd};color:{txt};
  padding:.35rem .88rem;border-radius:50px;margin:.2rem;
  font-size:calc({fs}px * 0.82);font-weight:600;transition:all .22s;
}}
.tag-badge:hover{{background:{btn_hov};transform:translateY(-2px) scale(1.05);}}
.tag-green{{background:rgba(34,197,94,.18)!important;border-color:rgba(34,197,94,.4)!important;color:#86efac!important;}}
.tag-blue {{background:rgba(96,165,250,.18)!important;border-color:rgba(96,165,250,.4)!important;color:#bfdbfe!important;}}
.tag-amber{{background:rgba(251,191,36,.18)!important;border-color:rgba(251,191,36,.4)!important;color:#fde68a!important;}}
.tag-rose {{background:rgba(244,63,94,.18)!important;border-color:rgba(244,63,94,.4)!important;color:#fecdd3!important;}}
.animal-badge{{
  display:inline-flex;align-items:center;gap:5px;
  background:rgba(125,211,252,.14);border:1px solid rgba(125,211,252,.32);
  color:#7dd3fc;padding:.33rem .9rem;border-radius:50px;
  font-size:calc({fs}px * 0.82);font-weight:700;
}}

/* ═══ KPI ═══ */
.kpi-card{{
  background:{kpi_bg};backdrop-filter:blur(16px);
  border:1px solid {kpi_brd};border-radius:18px;padding:1.3rem;
  text-align:center;color:{txt};
  box-shadow:0 4px 18px rgba(0,0,0,.07);transition:all .35s cubic-bezier(.4,0,.2,1);
  animation:fadeUp .5s ease both;
}}
.kpi-card:hover{{transform:translateY(-7px) scale(1.03);box-shadow:0 13px 40px rgba(0,0,0,.13);}}
.kpi-val{{font-size:calc({fs}px * 1.85);font-weight:900;margin:.4rem 0;letter-spacing:-1px;}}
.kpi-lbl{{font-size:calc({fs}px * 0.68);text-transform:uppercase;letter-spacing:2px;font-weight:700;opacity:.7;}}
.kpi-sub{{font-size:calc({fs}px * 0.64);opacity:.44;margin-top:.26rem;}}

/* ═══ BLOCKS ═══ */
.sc    {{background:{sc_bg};border:1px solid {card_brd};border-radius:13px;padding:1rem;margin:.5rem 0;}}
.sc-b  {{border-left:4px solid #60a5fa!important;background:rgba(96,165,250,.07)!important;}}
.sc-g  {{border-left:4px solid #34d399!important;background:rgba(52,211,153,.07)!important;}}
.sc-p  {{border-left:4px solid #a78bfa!important;background:rgba(167,139,250,.07)!important;}}
.sc-a  {{border-left:4px solid #fbbf24!important;background:rgba(251,191,36,.07)!important;}}
.sc-r  {{border-left:4px solid #f87171!important;background:rgba(248,113,113,.07)!important;}}
.insight{{background:rgba(96,165,250,.08);border:1px solid rgba(96,165,250,.2);
  border-radius:13px;padding:.85rem 1.22rem;margin:.5rem 0;color:{txt};line-height:1.75;}}
.insight strong{{color:#60a5fa;}}

/* ═══ CONNECTIONS ═══ */
.conn-row{{
  display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:7px;
  background:{conn_bg};border-radius:12px;padding:.7rem 1.05rem;margin:.24rem 0;
  border-left:3px solid rgba(96,165,250,.28);transition:background .2s,transform .2s;
  animation:fadeUp .4s ease both;
}}
.conn-row:hover{{background:{conn_hov};transform:translateX(4px);}}

/* ═══ CLUSTERS ═══ */
.cluster-wrap{{
  background:{sc_bg};border-radius:14px;padding:1rem 1.2rem;
  margin:.4rem 0;border:1px solid {card_brd};transition:all .3s;animation:fadeUp .5s ease both;
}}
.cluster-wrap:hover{{border-color:{badge_brd};box-shadow:0 5px 18px rgba(0,0,0,.08);}}
.cluster-title{{font-size:calc({fs}px * 0.70);text-transform:uppercase;letter-spacing:1.5px;
  color:rgba(167,139,250,.85);margin-bottom:.52rem;font-weight:800;}}
.cluster-pill{{
  display:inline-flex;align-items:center;gap:4px;
  background:rgba(168,85,247,.16);border:1px solid rgba(168,85,247,.3);
  border-radius:50px;padding:.26rem .76rem;margin:.16rem;
  font-size:calc({fs}px * 0.76);font-weight:600;color:#f3e8ff;transition:all .2s;
}}
.cluster-pill:hover{{background:rgba(168,85,247,.32);transform:scale(1.05);}}

/* ═══ MISC ═══ */
.pbar-o{{background:{pbar_bg};border-radius:50px;height:5px;margin:3px 0;overflow:hidden;}}
.pbar-i{{height:100%;border-radius:50px;transition:width .6s cubic-bezier(.4,0,.2,1);}}
.divider{{height:1px;background:linear-gradient(90deg,transparent,{card_brd},transparent);margin:1.5rem 0;}}
.filter-panel{{background:{card_bg};backdrop-filter:blur(16px);
  border:1px solid {card_brd};border-radius:18px;padding:1.2rem;margin:.7rem 0;}}

/* ═══ STREAMLIT OVERRIDES ═══ */
.stButton button{{
  background:{btn_bg}!important;backdrop-filter:blur(12px)!important;
  color:{txt}!important;border:1px solid {badge_brd}!important;
  border-radius:12px!important;padding:.65rem 1.5rem!important;
  font-weight:700!important;transition:all .28s!important;
  box-shadow:0 3px 10px rgba(0,0,0,.07)!important;
}}
.stButton button:hover{{
  background:{btn_hov}!important;box-shadow:0 7px 26px rgba(0,0,0,.14)!important;
  transform:translateY(-3px) scale(1.03)!important;
}}
.stTextInput input,.stTextArea textarea{{
  background:{inp_bg}!important;backdrop-filter:blur(8px)!important;
  border:1px solid {inp_brd}!important;color:{txt}!important;
  border-radius:11px!important;padding:.72rem!important;font-weight:500!important;
}}
.stTextInput input::placeholder,.stTextArea textarea::placeholder{{color:{txt_m}!important;}}
.stTextInput input:focus,.stTextArea textarea:focus{{
  border-color:rgba(96,165,250,.7)!important;
  box-shadow:0 0 0 3px rgba(96,165,250,.13)!important;
}}
label{{color:{txt}!important;font-weight:700!important;}}
.stTabs [data-baseweb="tab-list"]{{
  gap:.4rem;background:{tab_bg};backdrop-filter:blur(8px);
  padding:.35rem;border-radius:13px;border:1px solid {card_brd};
}}
.stTabs [data-baseweb="tab"]{{
  background:transparent;border:1px solid transparent;border-radius:9px;
  color:{txt};padding:.56rem 1.15rem;font-weight:700;transition:all .22s;
}}
.stTabs [data-baseweb="tab"]:hover{{background:{conn_hov};transform:translateY(-1px);}}
.stTabs [aria-selected="true"]{{background:{tab_sel}!important;border-color:{badge_brd}!important;
  box-shadow:0 3px 10px rgba(0,0,0,.1)!important;}}
.stAlert{{background:{card_bg}!important;backdrop-filter:blur(12px)!important;
  border-radius:13px!important;border-left:4px solid!important;color:{txt}!important;}}
.dataframe{{background:{card_bg}!important;border:1px solid {card_brd}!important;border-radius:13px!important;}}
.dataframe th{{background:{kpi_bg}!important;color:{txt}!important;
  font-weight:800!important;font-size:calc({fs}px * 0.77)!important;
  text-transform:uppercase;letter-spacing:.5px;}}
.dataframe td{{color:{txt}!important;}}
h1,h2,h3,h4,h5,h6{{color:{title_c};font-weight:800;}}
#MainMenu,footer,header,.stDeployButton{{visibility:hidden;}}
[data-testid="stSidebar"]{{display:none;}}
div[data-testid="stTextInput"]>div{{background:transparent!important;border:none!important;
  box-shadow:none!important;padding:0!important;}}
div[data-testid="stTextInput"]{{background:transparent!important;border:none!important;}}
@media(max-width:768px){{
  .main-title{{font-size:calc({fs}px * 1.6);}}
  .main-content{{margin-top:120px;padding:.85rem .9rem;}}
}}
</style>""", unsafe_allow_html=True)

# ── HELPERS ───────────────────────────────────────────────────────────
def kpi(label, value, sub="", color="#7dd3fc"):
    return (f"<div class='kpi-card'>"
            f"<div class='kpi-lbl'>{label}</div>"
            f"<div class='kpi-val' style='color:{color}'>{value}</div>"
            f"{'<div class=kpi-sub>'+str(sub)+'</div>' if sub else ''}"
            f"</div>")

def insight(text):  return f"<div class='insight'>{text}</div>"
def divider():      return "<div class='divider'></div>"
def pbar(pct, c="#60a5fa"):
    w = min(100, max(0, pct*100))
    return f"<div class='pbar-o'><div class='pbar-i' style='width:{w:.1f}%;background:{c}'></div></div>"

# ── DADOS ─────────────────────────────────────────────────────────────
def check_admin():
    if not load_json_file(ADMIN_FILE, []):
        save_json_file(ADMIN_FILE, [{"id":1,"username":ADMIN_USERNAME,
            "password":hashlib.sha256(ADMIN_PASSWORD.encode()).hexdigest()}])

def gen_uid():
    return base64.b64encode(os.urandom(12)).decode('ascii')

@st.cache_data(ttl=5, show_spinner=False)
def load_obras():
    default = [
        {"id":1,"titulo":"Guernica","artista":"Pablo Picasso","ano":"1937",
         "categoria":"Pintura","tecnica":"Óleo sobre tela","dimensoes":"349×776 cm",
         "descricao":"Protesto monumental contra o bombardeio da Guerra Civil Espanhola",
         "imagem":"https://upload.wikimedia.org/wikipedia/en/7/74/PicassoGuernica.jpg"},
        {"id":2,"titulo":"A Noite Estrelada","artista":"Vincent van Gogh","ano":"1889",
         "categoria":"Pintura","tecnica":"Óleo sobre tela","dimensoes":"73.7×92.1 cm",
         "descricao":"Paisagem noturna turbilhonante sobre vila de Saint-Rémy",
         "imagem":"https://upload.wikimedia.org/wikipedia/commons/thumb/e/ea/Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg/1200px-Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg"},
        {"id":3,"titulo":"Mona Lisa","artista":"Leonardo da Vinci","ano":"1503",
         "categoria":"Pintura","tecnica":"Óleo sobre madeira","dimensoes":"77×53 cm",
         "descricao":"Retrato feminino com sorriso enigmático usando sfumato",
         "imagem":"https://upload.wikimedia.org/wikipedia/commons/thumb/e/ec/Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_retouched.jpg/800px-Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_retouched.jpg"},
    ]
    obras = load_json_file(OBRAS_FILE, default)
    if not obras: save_json_file(OBRAS_FILE, default); return default
    return obras

def save_answers(uid, animal, answers):
    users = load_json_file(USERS_FILE, [])
    users.append({"user_id":uid,"animal_name":animal,
                  "timestamp":datetime.now().strftime("%Y-%m-%d %H:%M:%S"), **answers})
    return save_json_file(USERS_FILE, users)

def save_tag(uid, obra_id, tag):
    tags = load_json_file(TAGS_FILE, [])
    tags.append({"id":len(tags)+1,"user_id":uid,"obra_id":obra_id,
                 "tag":tag.lower().strip(),
                 "timestamp":datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
    st.cache_data.clear()
    return save_json_file(TAGS_FILE, tags)

def get_obra_user_tags(obra_id, uid):
    tags = load_json_file(TAGS_FILE, [])
    f = [t for t in tags if t['obra_id']==obra_id and t['user_id']==uid]
    if f:
        df = pd.DataFrame(f)
        c  = df['tag'].value_counts().reset_index(); c.columns=["tag","count"]
        return c
    return pd.DataFrame(columns=["tag","count"])

def check_login(u, p):
    return (u==ADMIN_USERNAME and
            hashlib.sha256(p.encode()).hexdigest()==hashlib.sha256(ADMIN_PASSWORD.encode()).hexdigest())

def all_tags():
    t = load_json_file(TAGS_FILE, [])
    return pd.DataFrame(t) if t else pd.DataFrame()

def all_users():
    u = load_json_file(USERS_FILE, [])
    return pd.DataFrame(u) if u else pd.DataFrame()

def get_user_tags(uid):
    tags = load_json_file(TAGS_FILE, [])
    ut = [t for t in tags if t['user_id']==uid]
    return pd.DataFrame(ut) if ut else pd.DataFrame()

# ── HTML EXPORTS ──────────────────────────────────────────────────────
def html_quest(uid, animal, users_df):
    if users_df.empty: return None
    ud = users_df[users_df['user_id']==uid]
    if ud.empty: return None
    ui = ud.iloc[0]
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<style>*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:Inter,sans-serif;background:linear-gradient(135deg,#050d1a,#001230);padding:40px;color:white}}
.c{{max-width:840px;margin:0 auto;background:rgba(255,255,255,.12);padding:45px;border-radius:22px;border:1px solid rgba(255,255,255,.2)}}
h1{{text-align:center;margin-bottom:14px;font-size:1.8rem;font-weight:900}}
.hi{{text-align:center;margin-bottom:30px;opacity:.85}}
.ab{{background:rgba(125,211,252,.2);border:1px solid rgba(125,211,252,.4);color:#7dd3fc;padding:.26rem .88rem;border-radius:50px;font-weight:700;display:inline-block}}
.qb{{margin:18px 0;padding:15px 18px;background:rgba(255,255,255,.09);border-left:4px solid rgba(255,255,255,.38);border-radius:11px}}
.q{{font-weight:800;margin-bottom:7px;font-size:.8rem;text-transform:uppercase;letter-spacing:.5px;opacity:.6}}
.a{{line-height:1.7;opacity:.92}}
.ft{{text-align:center;margin-top:34px;padding-top:14px;border-top:1px solid rgba(255,255,255,.14);opacity:.44;font-size:.78rem}}</style></head>
<body><div class="c"><h1>Respostas do Questionário</h1>
<div class="hi"><p>Usuário: <span class="ab">🐾 {animal}</span></p>
<p style="margin-top:5px;opacity:.5">Data: {ui.get('timestamp','N/A')}</p></div>
<div class="qb"><div class="q">1. Familiaridade com museus</div><div class="a">{ui.get('q1','N/A')}</div></div>
<div class="qb"><div class="q">2. Conhecimento museológico</div><div class="a">{ui.get('q2','N/A')}</div></div>
<div class="qb"><div class="q">3. O que você entende por tags?</div><div class="a">{ui.get('q3','N/A')}</div></div>
<div class="ft">Sistema Folksonomia Digital — Ctrl+P para salvar como PDF</div>
</div></body></html>"""

def html_tags(uid, animal, obras, tags_df):
    ut = tags_df[tags_df['user_id']==uid] if not tags_df.empty else pd.DataFrame()
    if ut.empty: return None
    od = {o['id']:o for o in obras}
    rows = "".join(
        f"<tr><td>{i+1}</td>"
        f"<td>{od.get(r['obra_id'],{}).get('titulo','Obra '+str(r['obra_id']))}</td>"
        f"<td><span style='background:rgba(255,255,255,.2);padding:3px 9px;border-radius:50px'>{r['tag']}</span></td>"
        f"<td>{r['timestamp']}</td></tr>"
        for i,(_,r) in enumerate(ut.iterrows()))
    top = "".join(f"<tr><td>{i}</td><td>{t}</td><td>{c}</td></tr>"
                  for i,(t,c) in enumerate(ut['tag'].value_counts().head(10).items(),1))
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<style>*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:Inter,sans-serif;background:linear-gradient(135deg,#050d1a,#001230);padding:40px;color:white}}
.c{{max-width:1080px;margin:0 auto;background:rgba(255,255,255,.12);padding:45px;border-radius:22px;border:1px solid rgba(255,255,255,.2)}}
h1,h2{{font-weight:900}}h1{{text-align:center;margin-bottom:14px;font-size:1.8rem}}
.hi{{text-align:center;margin-bottom:24px;opacity:.85}}
.ab{{background:rgba(125,211,252,.2);border:1px solid rgba(125,211,252,.4);color:#7dd3fc;padding:.26rem .88rem;border-radius:50px;font-weight:700;display:inline-block}}
.stats{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:18px 0}}
.sb{{background:rgba(255,255,255,.12);padding:14px;border-radius:11px;text-align:center}}
.sv{{font-size:2.1rem;font-weight:900}}
.sl{{font-size:.72rem;text-transform:uppercase;letter-spacing:1.4px;margin-top:5px;opacity:.72}}
table{{width:100%;border-collapse:collapse;margin:14px 0}}
th,td{{padding:11px;text-align:left;border-bottom:1px solid rgba(255,255,255,.1)}}
th{{background:rgba(255,255,255,.14);font-weight:800;text-transform:uppercase;font-size:.74rem;letter-spacing:.5px}}
tr:nth-child(even){{background:rgba(255,255,255,.04)}}
.ft{{text-align:center;margin-top:34px;padding-top:14px;border-top:1px solid rgba(255,255,255,.14);opacity:.44;font-size:.78rem}}</style></head>
<body><div class="c"><h1>Relatório de Tags</h1>
<div class="hi"><p>Usuário: <span class="ab">🐾 {animal}</span></p>
<p style="margin-top:5px;opacity:.5">Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}</p></div>
<div class="stats">
<div class="sb"><div class="sv">{len(ut)}</div><div class="sl">Total de Tags</div></div>
<div class="sb"><div class="sv">{ut['tag'].nunique()}</div><div class="sl">Tags Únicas</div></div>
<div class="sb"><div class="sv">{ut['obra_id'].nunique()}</div><div class="sl">Obras</div></div>
</div>
<h2 style="margin:24px 0 12px;font-size:1.3rem">Todas as Tags</h2>
<table><thead><tr><th>#</th><th>Obra</th><th>Tag</th><th>Data/Hora</th></tr></thead>
<tbody>{rows}</tbody></table>
<h2 style="margin:24px 0 12px;font-size:1.3rem">Top 10 Tags</h2>
<table><thead><tr><th>Pos.</th><th>Tag</th><th>Freq.</th></tr></thead>
<tbody>{top}</tbody></table>
<div class="ft">Sistema Folksonomia Digital — Ctrl+P para salvar como PDF</div>
</div></body></html>"""

# ── HEADER ────────────────────────────────────────────────────────────
def show_header():
    st.markdown(
        "<div class='top-navbar'>"
        "<div>"
        "<div class='navbar-logo'>📚 Folksonomia Digital</div>"
        "<div class='navbar-sub'>Sistema colaborativo de catalogação de arte</div>"
        "</div></div>", unsafe_allow_html=True)

# ── BARRA DE ACESSIBILIDADE ────────────────────────────────────────────
def show_accessibility_bar():
    fs    = int(st.session_state.get('font_size', 16))
    theme = st.session_state.get('theme', 'dark')
    hc    = st.session_state.get('high_contrast', False)

    st.markdown(f"""
<div class='access-bar-wrap'>
  <span class='access-label'>♿ Acessibilidade</span>
  <span class='access-fsinfo'>Fonte: {fs}px</span>
</div>""", unsafe_allow_html=True)

    c1, c2, c3, c4, c5, c6, c7 = st.columns([.55,.55,.55,.55,.55, 1.0, 1.1])
    with c1:
        if st.button("A―", key="fs_down", help="Reduzir fonte"):
            st.session_state['font_size'] = max(12, fs - 2)
            st.rerun()
    with c2:
        if st.button("A", key="fs_reset", help="Fonte padrão 16px"):
            st.session_state['font_size'] = 16
            st.rerun()
    with c3:
        if st.button("A＋", key="fs_up", help="Aumentar fonte"):
            st.session_state['font_size'] = min(26, fs + 2)
            st.rerun()
    with c4:
        if st.button("A＋＋", key="fs_xl", help="Fonte grande"):
            st.session_state['font_size'] = min(26, fs + 4)
            st.rerun()
    with c5:
        # spacer
        st.markdown("")
    with c6:
        lbl = "☀️ Modo Claro" if theme=='dark' else "🌙 Modo Escuro"
        if st.button(lbl, key="theme_btn"):
            st.session_state['theme'] = 'light' if theme=='dark' else 'dark'
            st.rerun()
    with c7:
        lbl2 = "🔲 Contraste ✓" if hc else "🔳 Alto Contraste"
        if st.button(lbl2, key="hc_btn"):
            st.session_state['high_contrast'] = not hc
            st.rerun()

# ── MAIN ──────────────────────────────────────────────────────────────
def main():
    for k, v in [
        ('user_id',       gen_uid()),
        ('animal_name',   generate_animal_name()),
        ('step',          'intro'),
        ('answers',       {}),
        ('theme',         'dark'),
        ('font_size',     16),
        ('high_contrast', False),
        ('view_mode',     'grid'),
    ]:
        if k not in st.session_state:
            st.session_state[k] = v

    load_css()
    try: check_admin()
    except Exception as e: st.error(f"Erro ao inicializar: {e}")

    if st.session_state['step'] != 'completed':
        show_intro()
    else:
        show_header()
        st.markdown("<div class='main-content'>", unsafe_allow_html=True)
        show_accessibility_bar()
        t1, t2 = st.tabs(["🖼️  Explorar Obras", "⚙️  Área Administrativa"])
        with t1: show_obras()
        with t2: show_admin()
        st.markdown("</div>", unsafe_allow_html=True)

# ── INTRO ─────────────────────────────────────────────────────────────
def show_intro():
    st.markdown("<div class='main-content'>", unsafe_allow_html=True)
    show_accessibility_bar()
    st.markdown("<h1 class='main-title'>📚 Sistema Folksonomia Digital</h1>", unsafe_allow_html=True)
    st.markdown(
        "<p class='subtitle'>Sistema colaborativo de catalogação de obras de arte<br>"
        "Complete o questionário para acessar a plataforma</p>", unsafe_allow_html=True)

    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.markdown("<h2 style='text-align:center;margin-bottom:1.7rem'>📋 Questionário de Acesso</h2>",
                unsafe_allow_html=True)
    with st.form("intro_form"):
        c1, c2 = st.columns(2)
        with c1:
            q1 = st.selectbox("1. Nível de familiaridade com museus:", [
                "Nunca visito museus","Visito raramente",
                "Visito ocasionalmente","Visito frequentemente"])
            q2 = st.selectbox("2. Conhecimento sobre documentação museológica:", [
                "Nunca ouvi falar","Já ouvi, mas não sei o que é",
                "Tenho uma ideia básica","Conheço bem o tema"])
        with c2:
            q3 = st.text_area(
                "3. O que você entende por 'tags' ou etiquetas digitais aplicadas a acervo?",
                max_chars=500, height=170,
                placeholder="Descreva sua compreensão sobre tags em sistemas digitais…")
        _, cb, _ = st.columns([1,1,1])
        with cb:
            submit = st.form_submit_button("🚀 Acessar a Plataforma", use_container_width=True)
        if submit:
            if not q3.strip():
                st.error("Por favor, responda todas as perguntas!")
            else:
                st.session_state['answers'] = {"q1":q1,"q2":q2,"q3":q3}
                save_answers(st.session_state['user_id'],
                             st.session_state['animal_name'],
                             st.session_state['answers'])
                st.session_state['step'] = 'completed'
                st.success("✅ Questionário completo! Acesso liberado.")
                st.balloons(); st.rerun()
    st.markdown("</div></div>", unsafe_allow_html=True)

# ── GALERIA ───────────────────────────────────────────────────────────
def show_obras():
    st.markdown("<h1 class='main-title'>🎨 Galeria de Obras</h1>", unsafe_allow_html=True)
    st.markdown("<p class='subtitle'>Explore, filtre e contribua com suas tags descritivas</p>",
                unsafe_allow_html=True)
    obras = load_obras(); tdf = all_tags()
    if not obras: st.info("Nenhuma obra cadastrada."); return

    with st.expander("🔍 Filtros & Visualização", expanded=True):
        st.markdown("<div class='filter-panel'>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1:
            b_titulo  = st.text_input("🔎 Título:", placeholder="Ex: Guernica…", key="ft")
            b_artista = st.text_input("🎨 Artista:", placeholder="Ex: Van Gogh…", key="fa")
        with c2:
            anos    = sorted(set(str(o.get('ano','')) for o in obras if o.get('ano')))
            ano_sel = st.multiselect("📅 Ano(s):", anos, key="fano")
            cats    = sorted(set(o.get('categoria','Pintura') for o in obras))
            cat_sel = st.multiselect("📂 Categoria:", cats, key="fcat")
        with c3:
            tags_f = []
            if not tdf.empty:
                all_utags = sorted(tdf['tag'].unique().tolist())
                tags_f = st.multiselect("🏷️ Obras com tag:", all_utags[:60], key="ftag")
            sord = st.selectbox("📊 Ordenar:", [
                "Número ↑","Número ↓","Título A–Z","Título Z–A",
                "Mais tagueadas","Menos tagueadas","Ano ↑","Ano ↓"], key="fsord")
        st.markdown("</div>", unsafe_allow_html=True)

    vm1, vm2, _ = st.columns([.6,.6,6])
    with vm1:
        if st.button("⊞ Grade", key="vg"):
            st.session_state['view_mode']='grid'; st.rerun()
    with vm2:
        if st.button("☰ Lista", key="vl"):
            st.session_state['view_mode']='list'; st.rerun()
    view_mode = st.session_state.get('view_mode','grid')

    filtered = obras[:]
    if b_titulo.strip():  filtered = [o for o in filtered if b_titulo.lower()  in o['titulo'].lower()]
    if b_artista.strip(): filtered = [o for o in filtered if b_artista.lower() in o.get('artista','').lower()]
    if ano_sel:           filtered = [o for o in filtered if str(o.get('ano','')) in ano_sel]
    if cat_sel:           filtered = [o for o in filtered if o.get('categoria','') in cat_sel]
    if tags_f and not tdf.empty:
        oc = set()
        for tg in tags_f: oc |= set(tdf[tdf['tag']==tg]['obra_id'].tolist())
        filtered = [o for o in filtered if o['id'] in oc]

    tc_map = {} if tdf.empty else tdf.groupby('obra_id').size().to_dict()

    def skey(o):
        tc = tc_map.get(o['id'],0)
        try: yr = int(o.get('ano',0))
        except: yr = 0
        if sord=="Número ↑":        return  o['id']
        if sord=="Número ↓":        return -o['id']
        if sord=="Título A–Z":      return  o['titulo']
        if sord=="Título Z–A":      return [-ord(c) for c in o['titulo']]
        if sord=="Mais tagueadas":  return -tc
        if sord=="Menos tagueadas": return  tc
        if sord=="Ano ↑":           return  yr
        if sord=="Ano ↓":           return -yr
        return o['id']
    try: filtered = sorted(filtered, key=skey)
    except: pass

    st.markdown(
        f"<div style='text-align:center;margin:1rem 0;font-weight:600'>"
        f"Exibindo <strong style='color:#7dd3fc;font-size:1.2em'>{len(filtered)}</strong>"
        f" de {len(obras)} obra(s)</div>", unsafe_allow_html=True)

    if not filtered: st.warning("Nenhuma obra encontrada."); return

    if view_mode == 'grid': render_grid(filtered, tc_map, tdf)
    else:                   render_list(filtered, tc_map, tdf)

# ── GRID ──────────────────────────────────────────────────────────────
def render_grid(obras, tc_map, tdf):
    cols = st.columns(3)
    for i, obra in enumerate(obras):
        with cols[i%3]:
            tc = tc_map.get(obra['id'],0)
            dk = f"show_desc_{obra['id']}"
            st.markdown(f"""
<div class='obra-card'>
  <span class='obra-num'>#{obra['id']}</span>
  <img src='{obra['imagem']}' alt='{obra["titulo"]}' />
  <div style='padding:1rem'>
    <h3 style='font-weight:800;margin-bottom:.18rem'>{obra['titulo']}</h3>
    <p style='font-size:.8rem;opacity:.55;margin-bottom:.2rem'>{obra.get('artista','')} · {obra.get('ano','')}</p>
    <p style='font-size:.72rem;opacity:.4'>{obra.get('tecnica','')} · {obra.get('dimensoes','')}</p>
    <div style='margin-top:.45rem'><span class='tag-badge tag-blue'>🏷️ {tc} tag{'s' if tc!=1 else ''}</span></div>
  </div>
</div>""", unsafe_allow_html=True)

            # Botão áudio — toggle
            if st.button("🔊 Áudio-Descrição", key=f"adbtn_{obra['id']}",
                         use_container_width=True, help="Ouvir descrição acessível"):
                st.session_state[dk] = not st.session_state.get(dk, False)
                st.rerun()

            if st.session_state.get(dk, False):
                texto = AUDIO_DESCRIPTIONS.get(obra['id'], obra.get('descricao','Sem descrição.'))
                st.markdown(
                    f"<div class='sc sc-g' style='padding:.7rem;margin:.2rem 0'>"
                    f"<strong style='color:#34d399;font-size:.8rem'>🔊 {obra['titulo']}</strong>"
                    f"</div>", unsafe_allow_html=True)
                audio_speak(texto, key=f"spk_{obra['id']}")

            if st.button("🏷️ Adicionar Tag", key=f"btn_{obra['id']}", use_container_width=True):
                st.session_state['selected_obra'] = obra; st.rerun()

            if st.session_state.get('selected_obra',{}).get('id') == obra['id']:
                render_tag_form(obra)

            ut = get_obra_user_tags(obra['id'], st.session_state['user_id'])
            if not ut.empty:
                st.markdown("**Suas Tags:**")
                st.markdown("".join(
                    f"<span class='tag-badge'>{r['tag']} <span style='opacity:.4;font-size:.72rem'>({r['count']}×)</span></span>"
                    for _,r in ut.iterrows()), unsafe_allow_html=True)
            else:
                st.markdown(
                    "<div style='text-align:center;font-size:.78rem;opacity:.35;padding:.35rem'>Sem tags suas ainda</div>",
                    unsafe_allow_html=True)

# ── LIST ──────────────────────────────────────────────────────────────
def render_list(obras, tc_map, tdf):
    for obra in obras:
        tc = tc_map.get(obra['id'],0)
        dk = f"show_desc_list_{obra['id']}"
        top_tags = []
        if not tdf.empty:
            ot = tdf[tdf['obra_id']==obra['id']]['tag'].value_counts().head(6)
            top_tags = list(ot.index)

        st.markdown(f"""
<div class='obra-list-item'>
  <img src='{obra['imagem']}' alt='{obra["titulo"]}' class='obra-list-img'/>
  <div style='flex:1'>
    <div style='display:flex;justify-content:space-between;flex-wrap:wrap;gap:5px'>
      <div>
        <h3 style='font-weight:800;margin-bottom:.16rem'>#{obra['id']} · {obra['titulo']}</h3>
        <p style='font-size:.8rem;opacity:.6'>{obra.get('artista','')} · {obra.get('ano','')} · {obra.get('categoria','')}</p>
        <p style='font-size:.72rem;opacity:.4;margin-top:.1rem'>{obra.get('tecnica','')} · {obra.get('dimensoes','')}</p>
      </div>
      <span class='tag-badge tag-blue'>🏷️ {tc}</span>
    </div>
    <p style='font-size:.8rem;opacity:.55;margin:.4rem 0;line-height:1.55'>{obra.get('descricao','')}</p>
    <div>{''.join(f"<span class='tag-badge' style='font-size:.7rem'>{t}</span>" for t in top_tags)
          if top_tags else "<span style='font-size:.73rem;opacity:.3'>Sem tags ainda</span>"}</div>
  </div>
</div>""", unsafe_allow_html=True)

        lc1, lc2 = st.columns(2)
        with lc1:
            if st.button("🏷️ Tag", key=f"lb_{obra['id']}", use_container_width=True):
                st.session_state['selected_obra'] = obra; st.rerun()
        with lc2:
            if st.button("🔊 Áudio", key=f"la_{obra['id']}", use_container_width=True):
                st.session_state[dk] = not st.session_state.get(dk,False); st.rerun()

        if st.session_state.get(dk, False):
            texto = AUDIO_DESCRIPTIONS.get(obra['id'], obra.get('descricao','Sem descrição.'))
            st.markdown(f"<div class='sc sc-g'><strong style='color:#34d399'>🔊 {obra['titulo']}</strong></div>",
                        unsafe_allow_html=True)
            audio_speak(texto, key=f"lspk_{obra['id']}")

        if st.session_state.get('selected_obra',{}).get('id') == obra['id']:
            render_tag_form(obra)

        ut = get_obra_user_tags(obra['id'], st.session_state['user_id'])
        if not ut.empty:
            st.markdown("**Suas Tags:** " + "".join(
                f"<span class='tag-badge'>{r['tag']} ({r['count']}×)</span>"
                for _,r in ut.iterrows()), unsafe_allow_html=True)
        st.markdown(divider(), unsafe_allow_html=True)

def render_tag_form(obra):
    with st.form(f"tf_{obra['id']}"):
        tag = st.text_input("Nova tag:", placeholder="Ex: melancólico, azul noturno, abstrato…",
                            key=f"ti_{obra['id']}")
        st.markdown("<span style='font-size:.73rem;opacity:.42'>Sugestões: guerra · paz · luz · escuridão · natureza · movimento · emoção · cor</span>",
                    unsafe_allow_html=True)
        ca, cb = st.columns(2)
        with ca: sub = st.form_submit_button("✅ Enviar Tag", use_container_width=True)
        with cb: can = st.form_submit_button("✕ Cancelar",   use_container_width=True)
        if sub and tag:
            if len(tag.strip()) < 2: st.error("Tag deve ter ao menos 2 caracteres.")
            else:
                save_tag(st.session_state['user_id'], obra['id'], tag)
                st.success(f"✅ Tag '{tag}' adicionada!")
                del st.session_state['selected_obra']; st.rerun()
        if can: del st.session_state['selected_obra']; st.rerun()

# ── ADMIN ─────────────────────────────────────────────────────────────
def show_admin():
    if 'admin_logged_in' not in st.session_state:
        st.session_state['admin_logged_in'] = False
    if not st.session_state['admin_logged_in']:
        st.markdown("<h1 class='main-title'>⚙️ Área Administrativa</h1>", unsafe_allow_html=True)
        _, c2, _ = st.columns([1,1,1])
        with c2:
            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
            st.markdown("<h2 style='text-align:center;margin-bottom:1.4rem'>🔐 Login</h2>",
                        unsafe_allow_html=True)
            with st.form("login"):
                username = st.text_input("Usuário:")
                password = st.text_input("Senha:", type="password")
                sub = st.form_submit_button("Entrar no Sistema", use_container_width=True)
                if sub:
                    if check_login(username, password):
                        st.session_state['admin_logged_in'] = True
                        st.session_state['admin_username']  = username
                        st.success("✅ Login realizado!"); st.balloons(); st.rerun()
                    else: st.error("❌ Credenciais inválidas.")
            st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.markdown(
            f"<h1 class='main-title'>📊 Dashboard Administrativo</h1>"
            f"<p class='subtitle'>Bem-vindo, <strong>{st.session_state.get('admin_username','Admin')}</strong></p>",
            unsafe_allow_html=True)

        tabs = st.tabs([
            "📈 Visão Geral",
            "🔤 Análise de Tags",
            "🔗 Conexões de Tags",
            "🗺️ Mapeamento das Obras",
            "👥 Usuários",
            "🖼️ Obras",
            "📥 Exportar",
        ])
        with tabs[0]: tab_overview()
        with tabs[1]: tab_tags()
        with tabs[2]: tab_connections()
        with tabs[3]: tab_diversity_map()
        with tabs[4]: tab_users()
        with tabs[5]: tab_obras_admin()
        with tabs[6]: tab_export()

        st.markdown("<br>", unsafe_allow_html=True)
        _, c2, _ = st.columns([1,1,1])
        with c2:
            if st.button("🚪 Sair do Sistema", use_container_width=True):
                st.session_state['admin_logged_in'] = False; st.rerun()

# ═══════════════════════════════════════════════════════════════════════
# ABA 1 — VISÃO GERAL
# ═══════════════════════════════════════════════════════════════════════
def tab_overview():
    tdf = all_tags(); udf = all_users(); obs = load_obras()
    st.markdown("### 📈 Métricas Gerais")

    total  = len(tdf) if not tdf.empty else 0
    unicas = tdf['tag'].nunique() if not tdf.empty else 0
    nusers = udf['user_id'].nunique() if not udf.empty else 0
    nobs   = len(obs)
    obs_ct = tdf['obra_id'].nunique() if not tdf.empty else 0

    c1,c2,c3,c4,c5 = st.columns(5)
    for col,lbl,val,sub,clr in [
        (c1,"Total Tags",    total,   "registros","#7dd3fc"),
        (c2,"Tags Únicas",   unicas,  f"{unicas/total:.0%} do total" if total else "—","#c4b5fd"),
        (c3,"Participantes", nusers,  "usuários ativos","#6ee7b7"),
        (c4,"Obras",         nobs,    f"{obs_ct} com tags","#fcd34d"),
        (c5,"Média/Usuário", f"{total/nusers:.1f}" if nusers else "—","tags","#f9a8d4"),
    ]:
        with col: st.markdown(kpi(lbl,val,sub,clr), unsafe_allow_html=True)

    st.markdown(divider(), unsafe_allow_html=True)

    if not tdf.empty:
        od = {o['id']:o['titulo'] for o in obs}
        c1,c2 = st.columns(2)
        with c1:
            st.markdown("#### 🏆 Top 15 Tags")
            top = tdf['tag'].value_counts().head(15).reset_index(); top.columns=['Tag','Qtd']
            top['%'] = (top['Qtd']/top['Qtd'].sum()*100).round(1)
            st.dataframe(top, use_container_width=True, hide_index=True)
        with c2:
            st.markdown("#### 🖼️ Engajamento por Obra")
            ot = tdf.groupby('obra_id').agg(
                Tags=('tag','count'), Unicas=('tag','nunique'), Usuarios=('user_id','nunique')
            ).reset_index()
            ot['Obra'] = ot['obra_id'].map(od)
            ot['TTR']  = (ot['Unicas']/ot['Tags']).round(2)
            st.dataframe(ot[['Obra','Tags','Unicas','Usuarios','TTR']]
                         .sort_values('Tags',ascending=False),
                         use_container_width=True, hide_index=True)

    st.markdown(divider(), unsafe_allow_html=True)
    if not udf.empty and not tdf.empty:
        st.markdown("### 👥 Participantes")
        uct = tdf.groupby('user_id').size().reset_index(name='tags')
        uuq = tdf.groupby('user_id')['tag'].nunique().reset_index(name='unicas')
        m   = udf.merge(uct,on='user_id',how='left').merge(uuq,on='user_id',how='left').fillna(0)
        mx  = m['tags'].max() if m['tags'].max()>0 else 1
        for _,row in m.iterrows():
            animal = row.get('animal_name','?'); ts = row.get('timestamp','N/A')
            nt,nu  = int(row['tags']),int(row['unicas'])
            p      = nu/nt if nt>0 else 0
            st.markdown(
                f"<div class='sc sc-b' style='padding:.75rem 1.1rem;margin:.18rem 0'>"
                f"<div style='display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:7px'>"
                f"<div><span class='animal-badge'>🐾 {animal}</span>"
                f"<span style='opacity:.3;font-size:.7rem;margin-left:9px'>{ts}</span></div>"
                f"<div style='text-align:right;min-width:185px'>"
                f"<strong style='color:#7dd3fc'>{nt}</strong> tags · "
                f"<span style='opacity:.5;font-size:.78rem'>{nu} únicas · TTR {p:.0%}</span>"
                f"{pbar(nt/mx,'#7dd3fc')}"
                f"</div></div></div>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════
# ABA 2 — ANÁLISE DE TAGS (sem coocorrência, sem entropia)
# ═══════════════════════════════════════════════════════════════════════
def tab_tags():
    tdf = all_tags()
    if tdf.empty: st.info("Nenhuma tag disponível."); return
    st.markdown("### 🔤 Análise de Tags")
    t1, t2 = st.tabs(["📊 Frequência & Vocabulário", "⏱️ Evolução Temporal"])

    with t1:
        freq = tdf['tag'].value_counts().reset_index()
        freq.columns = ['Tag','Frequência']
        total_usos = freq['Frequência'].sum()
        freq['% Total']  = (freq['Frequência']/total_usos*100).round(2)
        freq['% Acum.']  = freq['% Total'].cumsum().round(2)
        freq['Compr.']   = freq['Tag'].str.len()
        freq['Palavras'] = freq['Tag'].str.split().str.len()
        freq['Categoria'] = pd.cut(freq['Frequência'],
            bins=[0,1,2,5,10,99999],
            labels=['Hapax (1×)','Rara (2×)','Ocasional (3–5×)','Frequente (6–10×)','Muito Frequente (10+×)'])

        hapax    = (freq['Frequência']==1).sum()
        lei80    = (freq['% Acum.']<=80).sum()
        ttr_g    = len(freq)/total_usos if total_usos else 0
        med_len  = freq['Compr.'].mean()
        multi_w  = (freq['Palavras']>1).sum()

        c1,c2,c3,c4,c5,c6 = st.columns(6)
        for col,lbl,val,sub,clr in [
            (c1,"Vocabulário",  len(freq),     "termos distintos","#7dd3fc"),
            (c2,"Hapax",        hapax,          f"{hapax/len(freq):.0%} vocab.","#f9a8d4"),
            (c3,"80% dos Usos", f"{lei80} tags","Zipf","#6ee7b7"),
            (c4,"TTR Global",   f"{ttr_g:.3f}", "riqueza lexical","#fcd34d"),
            (c5,"Compr. Médio", f"{med_len:.1f}","chars/tag","#c4b5fd"),
            (c6,"Compostas",    multi_w,        f"{multi_w/len(freq):.0%} vocab.","#fb923c"),
        ]:
            with col: st.markdown(kpi(lbl,val,sub,clr), unsafe_allow_html=True)

        st.markdown(insight(
            f"<strong>Distribuição de Zipf:</strong> apenas {lei80} tags cobrem 80% dos usos. "
            f"<strong>{hapax} hapax legomena</strong> ({hapax/len(freq):.0%} do vocabulário) foram usados apenas 1×. "
            f"TTR global <strong>{ttr_g:.3f}</strong> → "
            f"{'alta' if ttr_g>0.5 else 'moderada' if ttr_g>0.25 else 'baixa'} diversidade lexical."
        ), unsafe_allow_html=True)

        st.markdown(divider(), unsafe_allow_html=True)
        c1,c2 = st.columns([3,2])
        with c1:
            st.markdown("#### Top 25 Tags mais usadas")
            st.bar_chart(tdf['tag'].value_counts().head(25))
        with c2:
            st.markdown("#### Distribuição por comprimento (chars)")
            st.bar_chart(freq['Compr.'].value_counts().sort_index().rename("Tags"))

        st.markdown(divider(), unsafe_allow_html=True)
        st.markdown("#### 📋 Tabela Completa de Frequências")
        fc1,fc2,fc3 = st.columns([2,1,1])
        with fc1:
            cat_sel = st.multiselect("Categoria:", list(freq['Categoria'].cat.categories),
                                     default=list(freq['Categoria'].cat.categories), key="fc")
        with fc2: min_freq = st.number_input("Freq. mínima:", 1, 999, 1, key="mf")
        with fc3: busca_t  = st.text_input("Buscar tag:", key="bt")

        disp = freq[freq['Categoria'].isin(cat_sel)] if cat_sel else freq
        disp = disp[disp['Frequência']>=min_freq]
        if busca_t.strip():
            disp = disp[disp['Tag'].str.contains(busca_t.lower().strip(), na=False)]
        st.dataframe(disp, use_container_width=True, hide_index=True)

        c1,c2 = st.columns(2)
        with c1:
            st.download_button("⬇️ Frequências (CSV)",
                freq.to_csv(index=False).encode('utf-8'),
                f"freq_{datetime.now().strftime('%Y%m%d')}.csv","text/csv",
                use_container_width=True)
        with c2:
            st.markdown("**Por categoria:**")
            cd = freq['Categoria'].value_counts().reset_index(); cd.columns=['Categoria','Qtd']
            st.dataframe(cd, use_container_width=True, hide_index=True)

    with t2:
        try:
            tf = tdf.copy(); tf['ts'] = pd.to_datetime(tf['timestamp'])
            tf['date'] = tf['ts'].dt.date
            tf['hora'] = tf['ts'].dt.hour
            tf['dow']  = tf['ts'].dt.day_name()

            dias   = tf['date'].nunique()
            m_dia  = len(tf)/dias if dias else 0
            pd_dia = tf.groupby('date').size()
            pico_v = int(pd_dia.max()) if not pd_dia.empty else 0
            pico_d = str(pd_dia.idxmax()) if not pd_dia.empty else "—"

            c1,c2,c3,c4 = st.columns(4)
            for col,lbl,val,sub,clr in [
                (c1,"Dias Ativos", dias,   "","#7dd3fc"),
                (c2,"Média/Dia",   f"{m_dia:.1f}","tags","#6ee7b7"),
                (c3,"Pico",        pico_v, f"em {pico_d}","#fcd34d"),
                (c4,"Período",     f"{dias}d","total","#c4b5fd"),
            ]:
                with col: st.markdown(kpi(lbl,val,sub,clr), unsafe_allow_html=True)

            st.markdown(divider(), unsafe_allow_html=True)
            daily = tf.groupby('date').agg(
                Tags=('tag','count'), Unicas=('tag','nunique'), Usuarios=('user_id','nunique')
            ).reset_index().rename(columns={'date':'Data'})
            c1,c2 = st.columns(2)
            with c1: st.markdown("#### Tags por dia"); st.line_chart(daily.set_index('Data')['Tags'])
            with c2: st.markdown("#### Usuários por dia"); st.line_chart(daily.set_index('Data')['Usuarios'])

            c1,c2 = st.columns(2)
            with c1:
                st.markdown("#### Por hora do dia")
                st.bar_chart(tf['hora'].value_counts().sort_index().rename("Tags"))
            with c2:
                st.markdown("#### Por dia da semana")
                dow_o  = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
                dow_pt = {"Monday":"Seg","Tuesday":"Ter","Wednesday":"Qua","Thursday":"Qui",
                          "Friday":"Sex","Saturday":"Sáb","Sunday":"Dom"}
                dow_c = tf['dow'].value_counts().reindex(dow_o, fill_value=0)
                dow_c.index = [dow_pt.get(d,d) for d in dow_c.index]
                st.bar_chart(dow_c.rename("Tags"))

            st.markdown(divider(), unsafe_allow_html=True)
            st.markdown("#### Tabela diária detalhada")
            daily_f = tf.groupby('date').agg(
                Total=('tag','count'), Unicas=('tag','nunique'), Usuarios=('user_id','nunique'),
                Top=('tag', lambda x: x.value_counts().index[0])
            ).reset_index()
            daily_f.columns = ['Data','Tags','Únicas','Usuários','Tag Mais Usada']
            st.dataframe(daily_f.sort_values('Data',ascending=False),
                         use_container_width=True, hide_index=True)
        except:
            st.info("Dados insuficientes para análise temporal.")

# ═══════════════════════════════════════════════════════════════════════
# ABA 3 — CONEXÕES DE TAGS
# ═══════════════════════════════════════════════════════════════════════
def tab_connections():
    tdf = all_tags(); obs = load_obras()
    if tdf.empty: st.warning("Nenhuma tag disponível."); return

    st.markdown("### 🔗 Conexões e Agrupamentos de Tags")
    st.markdown(insight(
        "<strong>Algoritmo:</strong> Contenção de substring + Jaccard de palavras + Jaccard de trigramas. "
        "Score de 0 (sem relação) a 1 (idênticas)."
    ), unsafe_allow_html=True)

    c1,c2,c3 = st.columns(3)
    with c1: threshold = st.slider("Limiar de similaridade:", 0.20, 0.90, 0.35, 0.05, key="ct")
    with c2: obra_f    = st.selectbox("Filtrar por obra:", ["Todas"] +
                          [f"#{o['id']} — {o['titulo']}" for o in obs], key="co")
    with c3: max_c     = st.number_input("Máx. conexões:", 10, 300, 60, 10, key="cm")

    fdf = tdf.copy()
    if obra_f != "Todas":
        oid = int(obra_f.split("—")[0].replace("#","").strip())
        fdf = tdf[tdf['obra_id']==oid]

    all_t = fdf['tag'].tolist()
    if len(set(all_t)) < 2: st.warning("Necessário ao menos 2 tags distintas."); return

    with st.spinner("Calculando conexões…"):
        conns    = tag_connections(all_t, threshold=threshold)
        clusters = tag_clusters(all_t, threshold=threshold)

    n_inv   = len(set(c['tag_a'] for c in conns) | set(c['tag_b'] for c in conns))
    density = (2*len(conns)) / (len(set(all_t))*(len(set(all_t))-1)) if len(set(all_t))>1 else 0

    c1,c2,c3,c4 = st.columns(4)
    with c1: st.markdown(kpi("Conexões",       len(conns),  f"limiar ≥{threshold:.2f}","#7dd3fc"), unsafe_allow_html=True)
    with c2: st.markdown(kpi("Grupos",         len(clusters),"clusters","#c4b5fd"),                 unsafe_allow_html=True)
    with c3: st.markdown(kpi("Tags Conectadas",n_inv,       "","#6ee7b7"),                          unsafe_allow_html=True)
    with c4: st.markdown(kpi("Dens. de Rede",  f"{density:.3f}","0=esparsa","#fcd34d"),             unsafe_allow_html=True)

    st.markdown(divider(), unsafe_allow_html=True)
    t1, t2 = st.tabs(["📋 Lista de Conexões", "🔵 Grupos de Tags"])

    with t1:
        if not conns: st.info("Nenhuma conexão. Reduza o limiar.")
        else:
            tipos    = sorted(set(c['tipo'] for c in conns))
            tipo_sel = st.multiselect("Tipo:", tipos, default=tipos, key="tsel")
            cf       = [c for c in conns if c['tipo'] in tipo_sel][:max_c]
            fm       = tdf['tag'].value_counts().to_dict()
            st.markdown(f"Exibindo **{len(cf)}** de **{len(conns)}** conexões")
            st.markdown(divider(), unsafe_allow_html=True)
            for c in cf:
                s   = c['similaridade']
                bar = "█"*int(s*10) + "░"*(10-int(s*10))
                fa  = fm.get(c['tag_a'],0); fb = fm.get(c['tag_b'],0)
                clr = "#6ee7b7" if s>0.7 else "#fcd34d" if s>0.5 else "#7dd3fc"
                st.markdown(
                    f"<div class='conn-row'>"
                    f"<div style='display:flex;align-items:center;gap:8px;flex-wrap:wrap'>"
                    f"<span class='tag-badge'>{c['tag_a']}</span>"
                    f"<span style='opacity:.28;font-size:.7rem'>({fa}×)</span>"
                    f"<span style='opacity:.26'>↔</span>"
                    f"<span class='tag-badge'>{c['tag_b']}</span>"
                    f"<span style='opacity:.28;font-size:.7rem'>({fb}×)</span>"
                    f"</div>"
                    f"<div style='text-align:right;min-width:180px'>"
                    f"<span style='font-family:monospace;color:{clr};font-size:.78rem'>{bar} {s:.3f}</span><br>"
                    f"<span style='font-size:.68rem;opacity:.33'>{c['tipo']}</span>"
                    f"</div></div>", unsafe_allow_html=True)
            st.markdown(divider(), unsafe_allow_html=True)
            st.download_button("⬇️ Conexões (CSV)",
                pd.DataFrame(conns).to_csv(index=False).encode('utf-8'),
                f"conexoes_{datetime.now().strftime('%Y%m%d')}.csv","text/csv")

    with t2:
        if not clusters: st.info("Nenhum grupo. Reduza o limiar.")
        else:
            COLORS = ["#7dd3fc","#6ee7b7","#f9a8d4","#fcd34d","#c4b5fd",
                      "#f87171","#67e8f9","#86efac","#fb923c","#e879f9"]
            fm       = tdf['tag'].value_counts().to_dict()
            cls_sort = sorted(clusters, key=len, reverse=True)
            st.markdown(f"**{len(cls_sort)} grupo(s) de tags semanticamente relacionadas**")
            st.markdown(divider(), unsafe_allow_html=True)
            for i, cl in enumerate(cls_sort, 1):
                color = COLORS[(i-1) % len(COLORS)]
                total_u = sum(fm.get(t,0) for t in cl)
                pills = "".join(
                    f"<span class='cluster-pill'>{t} <span style='opacity:.38;font-size:.67rem'>({fm.get(t,0)}×)</span></span>"
                    for t in sorted(cl, key=lambda x: fm.get(x,0), reverse=True))
                st.markdown(
                    f"<div class='cluster-wrap' style='border-left:4px solid {color}'>"
                    f"<div class='cluster-title'>Grupo {i} · {len(cl)} tags · {total_u} usos</div>"
                    f"{pills}</div>", unsafe_allow_html=True)
            st.markdown(divider(), unsafe_allow_html=True)
            summ = pd.DataFrame([{
                "Grupo": f"Grupo {i}","Tags": len(cl),
                "Usos": sum(fm.get(t,0) for t in cl),
                "Amostra": ", ".join(sorted(cl,key=lambda x:fm.get(x,0),reverse=True)[:5]) +
                           ("…" if len(cl)>5 else "")
            } for i,cl in enumerate(cls_sort,1)])
            st.dataframe(summ, use_container_width=True, hide_index=True)
            st.download_button("⬇️ Grupos (CSV)",
                summ.to_csv(index=False).encode('utf-8'),
                f"clusters_{datetime.now().strftime('%Y%m%d')}.csv","text/csv")

# ═══════════════════════════════════════════════════════════════════════
# ABA 4 — MAPEAMENTO DE DIVERSIDADE & CRIAÇÃO DAS OBRAS
# ═══════════════════════════════════════════════════════════════════════
def tab_diversity_map():
    tdf = all_tags(); obs = load_obras(); udf = all_users()
    od  = {o['id']: o for o in obs}
    if tdf.empty: st.info("Nenhuma tag disponível ainda."); return

    st.markdown("### 🗺️ Mapeamento de Diversidade & Criação das Obras")
    st.markdown(insight(
        "Visualize <strong>como cada obra foi explorada</strong> pelos participantes: "
        "quanta riqueza vocabular cada obra gerou, como o vocabulário cresceu ao longo do tempo, "
        "quais termos são exclusivos de cada obra e quais atravessam o acervo inteiro."
    ), unsafe_allow_html=True)

    # ─── CARDS DE PERFIL POR OBRA ────────────────────────────────────
    st.markdown(divider(), unsafe_allow_html=True)
    st.markdown("#### 📊 Perfil de Cada Obra")

    obra_stats = []
    for obra in obs:
        ot = tdf[tdf['obra_id']==obra['id']]
        if ot.empty:
            obra_stats.append({'id':obra['id'],'titulo':obra['titulo'],
                'artista':obra.get('artista',''),'ano':obra.get('ano',''),
                'total':0,'unicas':0,'usuarios':0,'ttr':0.0,
                'hapax':0,'tags_usuario':0.0,'tag_mais':'—','tag_freq':0})
            continue
        fq   = ot['tag'].value_counts()
        tot  = len(ot); uniq = ot['tag'].nunique(); usu = ot['user_id'].nunique()
        obra_stats.append({
            'id':obra['id'],'titulo':obra['titulo'],
            'artista':obra.get('artista',''),'ano':obra.get('ano',''),
            'total':tot,'unicas':uniq,'usuarios':usu,
            'ttr':round(uniq/tot if tot else 0,3),
            'hapax':int((fq==1).sum()),
            'tags_usuario':round(tot/usu if usu else 0,1),
            'tag_mais':fq.index[0] if len(fq) else '—',
            'tag_freq':int(fq.iloc[0]) if len(fq) else 0,
        })
    odf = pd.DataFrame(obra_stats)

    ncols = min(len(obs), 3)
    cols_o = st.columns(ncols)
    for i, row in odf.iterrows():
        with cols_o[i % ncols]:
            ttr_clr = "#6ee7b7" if row['ttr']>0.7 else "#fcd34d" if row['ttr']>0.4 else "#f9a8d4"
            st.markdown(f"""
<div class='sc sc-b' style='padding:1rem;text-align:center'>
  <div style='font-weight:800;font-size:.9rem;margin-bottom:.28rem'>{row['titulo']}</div>
  <div style='font-size:.7rem;opacity:.46;margin-bottom:.6rem'>{row['artista']} · {row['ano']}</div>
  <div style='display:grid;grid-template-columns:1fr 1fr;gap:5px;margin-bottom:.42rem'>
    <div style='background:rgba(125,211,252,.12);padding:.38rem;border-radius:8px'>
      <div style='font-size:1.22rem;font-weight:900;color:#7dd3fc'>{row['total']}</div>
      <div style='font-size:.58rem;opacity:.46;text-transform:uppercase'>total tags</div>
    </div>
    <div style='background:rgba(196,181,253,.12);padding:.38rem;border-radius:8px'>
      <div style='font-size:1.22rem;font-weight:900;color:#c4b5fd'>{row['unicas']}</div>
      <div style='font-size:.58rem;opacity:.46;text-transform:uppercase'>únicas</div>
    </div>
    <div style='background:rgba(110,231,183,.12);padding:.38rem;border-radius:8px'>
      <div style='font-size:1.22rem;font-weight:900;color:#6ee7b7'>{row['usuarios']}</div>
      <div style='font-size:.58rem;opacity:.46;text-transform:uppercase'>usuários</div>
    </div>
    <div style='background:rgba(252,211,77,.12);padding:.38rem;border-radius:8px'>
      <div style='font-size:1.22rem;font-weight:900;color:{ttr_clr}'>{row['ttr']:.2f}</div>
      <div style='font-size:.58rem;opacity:.46;text-transform:uppercase'>TTR</div>
    </div>
  </div>
  <span class='tag-badge' style='font-size:.7rem'>🏷 {row['tag_mais']}</span>
  <span style='font-size:.68rem;opacity:.38'>({row['tag_freq']}×)</span>
  {pbar(row['ttr'], ttr_clr)}
  <span style='font-size:.62rem;opacity:.36'>riqueza vocabular (TTR)</span>
</div>""", unsafe_allow_html=True)

    st.markdown(divider(), unsafe_allow_html=True)

    # ─── COMPARATIVO VISUAL ──────────────────────────────────────────
    st.markdown("#### 📈 Comparativo Visual entre Obras")
    odf_d = odf[odf['total']>0]
    if not odf_d.empty:
        c1,c2 = st.columns(2)
        with c1:
            st.markdown("**Total de tags por obra**")
            st.bar_chart(odf_d.set_index('titulo')['total'])
        with c2:
            st.markdown("**Riqueza vocabular (TTR) por obra**")
            st.bar_chart(odf_d.set_index('titulo')['ttr'])
        c1,c2 = st.columns(2)
        with c1:
            st.markdown("**Tags únicas por obra**")
            st.bar_chart(odf_d.set_index('titulo')['unicas'])
        with c2:
            st.markdown("**Usuários que etiquetaram cada obra**")
            st.bar_chart(odf_d.set_index('titulo')['usuarios'])

    st.markdown(divider(), unsafe_allow_html=True)

    # ─── MAPA DE CALOR: USUÁRIO × OBRA ──────────────────────────────
    st.markdown("#### 🔥 Mapa de Calor — Contribuição por Usuário × Obra")
    st.markdown(insight(
        "<strong>Cada célula</strong> indica quantas tags um participante criou para aquela obra. "
        "Células mais brilhantes = maior volume de contribuição."
    ), unsafe_allow_html=True)

    if not udf.empty and not tdf.empty:
        pivot = tdf.groupby(['user_id','obra_id']).size().unstack(fill_value=0)
        uid_to_name = {r['user_id']: r.get('animal_name', r['user_id'][:8])
                       for _, r in udf.iterrows()}
        oid_to_name = {o['id']: o['titulo'] for o in obs}
        pivot.index   = [uid_to_name.get(u, u[:8]) for u in pivot.index]
        pivot.columns = [oid_to_name.get(c, str(c)) for c in pivot.columns]
        max_v = pivot.values.max() if pivot.values.max()>0 else 1

        def cell_color(v, mx):
            if v==0: return "rgba(255,255,255,0.04)"
            pct = v/mx
            r = int(30  + pct*(125-30))
            g = int(100 + pct*(211-100))
            b = int(180 + pct*(252-180))
            return f"rgb({r},{g},{b})"

        hdr = "<div style='display:flex;gap:3px;margin-bottom:4px;padding-left:115px'>"
        for col in pivot.columns:
            hdr += (f"<div style='min-width:88px;max-width:88px;font-size:.67rem;"
                    f"opacity:.58;font-weight:700;overflow:hidden;white-space:nowrap;"
                    f"text-overflow:ellipsis;text-align:center'>{col}</div>")
        hdr += "</div>"

        rows_html = hdr
        for rname, rvals in pivot.iterrows():
            row_h = "<div style='display:flex;gap:3px;align-items:center;margin-bottom:3px'>"
            row_h += (f"<div style='min-width:112px;max-width:112px;font-size:.67rem;"
                      f"font-weight:700;opacity:.66;text-align:right;padding-right:7px;"
                      f"overflow:hidden;white-space:nowrap;text-overflow:ellipsis'>{rname}</div>")
            for cname in pivot.columns:
                v  = rvals.get(cname,0)
                bg = cell_color(v, max_v)
                tx = str(int(v)) if v>0 else ""
                tc = "white" if v/max_v>0.3 else "rgba(255,255,255,.38)"
                row_h += (f"<div style='min-width:88px;max-width:88px;height:34px;"
                           f"background:{bg};border-radius:7px;display:flex;align-items:center;"
                           f"justify-content:center;font-size:.78rem;font-weight:800;color:{tc}'>"
                           f"{tx}</div>")
            row_h += "</div>"
            rows_html += row_h

        st.markdown(
            f"<div style='overflow-x:auto;padding:1rem;background:rgba(255,255,255,.04);"
            f"border-radius:16px;border:1px solid rgba(255,255,255,.08)'>{rows_html}</div>",
            unsafe_allow_html=True)

        st.markdown(divider(), unsafe_allow_html=True)
        st.markdown("#### 📋 Tabela — Usuário × Obra")
        pivot_d = pivot.copy()
        pivot_d['TOTAL'] = pivot_d.sum(axis=1)
        st.dataframe(pivot_d.sort_values('TOTAL',ascending=False), use_container_width=True)

    st.markdown(divider(), unsafe_allow_html=True)

    # ─── CURVA DE CRESCIMENTO VOCABULAR ─────────────────────────────
    st.markdown("#### ⏳ Crescimento do Vocabulário ao Longo do Tempo")
    st.markdown(insight(
        "<strong>Cada linha</strong> mostra quantos termos únicos (vocabulário acumulado) "
        "uma obra coletou cronologicamente. "
        "Curvas que sobem rapidamente = obra que estimulou diversidade vocabular logo no início."
    ), unsafe_allow_html=True)
    try:
        tf_all = tdf.copy(); tf_all['ts'] = pd.to_datetime(tf_all['timestamp'])
        tf_all = tf_all.sort_values('ts')
        growth = {}
        for obra in obs:
            ot = tf_all[tf_all['obra_id']==obra['id']].copy()
            if ot.empty: continue
            seen = set(); records = []
            for _, r in ot.iterrows():
                seen.add(r['tag'])
                records.append({'ts': r['ts'].date(), 'vocab': len(seen)})
            s = pd.DataFrame(records).drop_duplicates('ts').set_index('ts')['vocab']
            growth[obra['titulo']] = s
        if growth:
            gdf = pd.DataFrame(growth).sort_index().fillna(method='ffill')
            st.line_chart(gdf)
        else: st.info("Dados insuficientes.")
    except: st.info("Dados insuficientes para curva de crescimento.")

    st.markdown(divider(), unsafe_allow_html=True)

    # ─── VOCABULÁRIO EXCLUSIVO POR OBRA ─────────────────────────────
    st.markdown("#### 🔐 Vocabulário Exclusivo por Obra")
    st.markdown(insight(
        "<strong>Tags exclusivas</strong> foram usadas em apenas uma obra — "
        "revelam o vocabulário único que cada obra evoca."
    ), unsafe_allow_html=True)

    obra_tag_sets = {}
    for obra in obs:
        obra_tag_sets[obra['id']] = set(tdf[tdf['obra_id']==obra['id']]['tag'].unique())

    for obra in obs:
        excl = obra_tag_sets[obra['id']].copy()
        for oid2, t2 in obra_tag_sets.items():
            if oid2 != obra['id']: excl -= t2
        ot_obra = tdf[tdf['obra_id']==obra['id']]
        excl_freq = {t: int(ot_obra[ot_obra['tag']==t].shape[0]) for t in excl}
        excl_s = sorted(excl_freq.items(), key=lambda x: x[1], reverse=True)

        st.markdown(f"<div class='sc sc-p' style='padding:.95rem;margin:.4rem 0'>",
                    unsafe_allow_html=True)
        st.markdown(f"**{obra['titulo']}** — {len(excl)} tag(s) exclusiva(s)")
        if excl_s:
            pills = "".join(
                f"<span class='tag-badge tag-blue'>{t} "
                f"<span style='opacity:.42;font-size:.7rem'>({f}×)</span></span>"
                for t,f in excl_s[:25])
            st.markdown(pills + ("…" if len(excl_s)>25 else ""), unsafe_allow_html=True)
        else:
            st.markdown("<span style='opacity:.38;font-size:.82rem'>Nenhuma tag exclusiva ainda</span>",
                        unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(divider(), unsafe_allow_html=True)

    # ─── TAGS COMPARTILHADAS ENTRE OBRAS ────────────────────────────
    st.markdown("#### 🔁 Tags Compartilhadas entre Obras")
    st.markdown(insight(
        "Tags que aparecem em <strong>mais de uma obra</strong> revelam conceitos transversais — "
        "temas que os participantes identificam em múltiplas obras."
    ), unsafe_allow_html=True)

    if len(obs) >= 2:
        tag_to_obras = {}
        for obra in obs:
            for t in obra_tag_sets[obra['id']]:
                tag_to_obras.setdefault(t, []).append(obra['titulo'])
        shared = {t: ol for t, ol in tag_to_obras.items() if len(ol)>1}
        shared_s = sorted(shared.items(), key=lambda x: len(x[1]), reverse=True)

        if shared_s:
            for tag, obras_list in shared_s[:30]:
                obras_str = " · ".join(obras_list)
                st.markdown(
                    f"<div class='conn-row'>"
                    f"<span class='tag-badge'>{tag}</span>"
                    f"<span style='opacity:.48;font-size:.8rem;flex:1;padding:0 .5rem'>{obras_str}</span>"
                    f"<span class='tag-badge tag-amber'>{len(obras_list)} obras</span>"
                    f"</div>", unsafe_allow_html=True)

            st.markdown(divider(), unsafe_allow_html=True)
            sh_df = pd.DataFrame([{
                "Tag": t, "Obras": ", ".join(ol), "Qtd Obras": len(ol)
            } for t, ol in shared_s])
            st.dataframe(sh_df, use_container_width=True, hide_index=True)
            st.download_button("⬇️ Tags Compartilhadas (CSV)",
                sh_df.to_csv(index=False).encode('utf-8'),
                f"tags_compartilhadas_{datetime.now().strftime('%Y%m%d')}.csv","text/csv")
        else:
            st.info("Nenhuma tag compartilhada entre obras ainda.")

# ═══════════════════════════════════════════════════════════════════════
# ABA 5 — USUÁRIOS
# ═══════════════════════════════════════════════════════════════════════
def tab_users():
    tdf = all_tags(); udf = all_users(); obs = load_obras()
    od  = {o['id']:o['titulo'] for o in obs}
    if udf.empty: st.info("Nenhum participante ainda."); return

    st.markdown("### 👥 Usuários & Questionário")
    uct = tdf.groupby('user_id').size().reset_index(name='Total') if not tdf.empty else pd.DataFrame(columns=['user_id','Total'])
    uuq = tdf.groupby('user_id')['tag'].nunique().reset_index(name='Unicas') if not tdf.empty else pd.DataFrame(columns=['user_id','Unicas'])
    uob = tdf.groupby('user_id')['obra_id'].nunique().reset_index(name='Obras') if not tdf.empty else pd.DataFrame(columns=['user_id','Obras'])
    m   = udf.merge(uct,on='user_id',how='left').merge(uuq,on='user_id',how='left').merge(uob,on='user_id',how='left').fillna(0)
    m['TTR'] = (m['Unicas']/m['Total'].replace(0,np.nan)).fillna(0).round(3)
    m['Usuário'] = m.apply(lambda r: r.get('animal_name', r['user_id'][:8]), axis=1)

    c1,c2,c3,c4 = st.columns(4)
    top_u = m.loc[m['Total'].idxmax(),'Usuário'] if not m.empty else "—"
    with c1: st.markdown(kpi("Participantes",      len(m),              "","#7dd3fc"),  unsafe_allow_html=True)
    with c2: st.markdown(kpi("Média Tags/Usuário", f"{m['Total'].mean():.1f}","","#6ee7b7"), unsafe_allow_html=True)
    with c3: st.markdown(kpi("Maior Contribuição", int(m['Total'].max()), top_u[:16],"#fcd34d"), unsafe_allow_html=True)
    with c4: st.markdown(kpi("TTR Médio",          f"{m['TTR'].mean():.2%}","riqueza","#c4b5fd"), unsafe_allow_html=True)

    st.markdown(divider(), unsafe_allow_html=True)
    t1,t2,t3,t4 = st.tabs(["📋 Tabela Geral","👤 Perfil Individual","📝 Questionário","🔄 Cruzamentos"])

    with t1:
        dcols = ['Usuário','Total','Unicas','TTR','Obras']
        if 'q1' in m.columns: dcols += ['q1','q2']
        st.dataframe(
            m[dcols].rename(columns={'Total':'Tags','Unicas':'Tags Únicas','Obras':'Obras Etiquetadas',
                                     'q1':'Familiaridade','q2':'Conhec. Museológico'})
            .sort_values('Tags',ascending=False),
            use_container_width=True, hide_index=True)
        st.markdown(divider(), unsafe_allow_html=True)
        c1,c2 = st.columns(2)
        with c1: st.markdown("**Tags por participante**"); st.bar_chart(m.set_index('Usuário')['Total'].sort_values(ascending=False))
        with c2: st.markdown("**TTR por participante**");  st.bar_chart(m.set_index('Usuário')['TTR'].sort_values(ascending=False))

    with t2:
        uopts = [f"🐾 {r.get('animal_name',r['user_id'][:8])}" for _,r in udf.iterrows()]
        usel  = st.selectbox("Participante:", uopts, key="ui_sel")
        uidx  = uopts.index(usel)
        uid   = udf.iloc[uidx]['user_id']
        uanim = udf.iloc[uidx].get('animal_name', uid[:8])
        utags = tdf[tdf['user_id']==uid] if not tdf.empty else pd.DataFrame()
        if utags.empty: st.info("Participante sem tags.")
        else:
            ttl = len(utags); unq = utags['tag'].nunique()
            ttr_u = unq/ttl if ttl else 0
            c1,c2,c3 = st.columns(3)
            with c1: st.markdown(kpi("Tags",   ttl,"","#7dd3fc"), unsafe_allow_html=True)
            with c2: st.markdown(kpi("Únicas", unq,f"TTR {ttr_u:.2%}","#6ee7b7"), unsafe_allow_html=True)
            with c3: st.markdown(kpi("Obras",  utags['obra_id'].nunique(),"etiquetadas","#fcd34d"), unsafe_allow_html=True)
            c1,c2 = st.columns(2)
            with c1:
                st.markdown(f"**Top tags de {uanim}:**")
                st.bar_chart(utags['tag'].value_counts().head(15))
            with c2:
                st.markdown("**Por obra:**")
                st.bar_chart(utags.groupby('obra_id').size().rename(index=od))
            ft = utags.copy(); ft['Obra'] = ft['obra_id'].map(od)
            st.dataframe(ft[['tag','Obra','timestamp']].rename(
                columns={'tag':'Tag','timestamp':'Data/Hora'}),
                use_container_width=True, hide_index=True)

    with t3:
        c1,c2 = st.columns(2)
        with c1:
            st.markdown("**Q1 — Familiaridade com Museus**")
            q1c = udf['q1'].value_counts()
            st.bar_chart(q1c)
            q1p = (q1c/q1c.sum()*100).round(1).reset_index(); q1p.columns=['Resposta','%']
            st.dataframe(q1p, use_container_width=True, hide_index=True)
        with c2:
            st.markdown("**Q2 — Conhecimento Museológico**")
            q2c = udf['q2'].value_counts()
            st.bar_chart(q2c)
            q2p = (q2c/q2c.sum()*100).round(1).reset_index(); q2p.columns=['Resposta','%']
            st.dataframe(q2p, use_container_width=True, hide_index=True)
        st.markdown(divider(), unsafe_allow_html=True)
        st.markdown("**Q3 — Respostas Abertas**")
        disp = udf.copy()
        if 'animal_name' in disp.columns: disp = disp.rename(columns={'animal_name':'Usuário'})
        disp['Palavras'] = disp['q3'].str.split().str.len()
        st.markdown(f"Média: **{disp['Palavras'].mean():.0f} palavras** por resposta")
        st.bar_chart(disp['Palavras'].value_counts().sort_index().rename("Respostas"))
        st.dataframe(
            disp[['Usuário','q3','Palavras','timestamp']].sort_values('timestamp',ascending=False)
            .rename(columns={'q3':'Resposta','timestamp':'Data/Hora'}),
            use_container_width=True, hide_index=True)

    with t4:
        if tdf.empty: st.info("Dados insuficientes."); return
        c1,c2 = st.columns(2)
        with c1:
            st.markdown("**Familiaridade × Média de Tags**")
            st.bar_chart(m.groupby('q1')['Total'].mean().sort_values(ascending=False) if 'q1' in m.columns else pd.Series())
        with c2:
            st.markdown("**Conhecimento × Tags Únicas**")
            st.bar_chart(m.groupby('q2')['Unicas'].mean().sort_values(ascending=False) if 'q2' in m.columns else pd.Series())
        st.markdown(divider(), unsafe_allow_html=True)
        if 'q1' in m.columns:
            cross = m.groupby('q1').agg(
                Usuários=('user_id','count'), Média_Tags=('Total','mean'),
                Média_Únicas=('Unicas','mean'), TTR=('TTR','mean')
            ).round(2).reset_index()
            cross.columns = ['Familiaridade','Usuários','Média Tags','Média Únicas','TTR']
            st.dataframe(cross, use_container_width=True, hide_index=True)
            st.markdown(insight(
                "<strong>TTR próximo de 1.0</strong> = alta originalidade vocabular. "
                "Compare se maior familiaridade com museus produz vocabulário mais rico."
            ), unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════
# ABA 6 — OBRAS ADMIN
# ═══════════════════════════════════════════════════════════════════════
def tab_obras_admin():
    st.markdown("### 🖼️ Gestão de Obras")
    obras = load_obras()
    t1,t2 = st.tabs(["📋 Listar","➕ Adicionar"])

    with t1:
        if obras:
            for obra in obras:
                c1,c2,c3 = st.columns([1,3,1])
                with c1: st.image(obra['imagem'], use_container_width=True)
                with c2:
                    st.markdown(f"**#{obra['id']} — {obra['titulo']}**")
                    st.markdown(f"*{obra.get('artista','')} · {obra.get('ano','')}*")
                    st.markdown(f"{obra.get('categoria','—')} · {obra.get('tecnica','—')} · {obra.get('dimensoes','—')}")
                    if obra.get('descricao'): st.markdown(f"_{obra['descricao']}_")
                with c3:
                    if st.button("🗑️ Remover", key=f"del_{obra['id']}"):
                        obras.remove(obra)
                        save_json_file(OBRAS_FILE, obras)
                        st.cache_data.clear(); st.rerun()
                st.divider()
        else: st.info("Nenhuma obra cadastrada.")

    with t2:
        with st.form("add_obra"):
            c1,c2 = st.columns(2)
            with c1:
                titulo  = st.text_input("Título*")
                artista = st.text_input("Artista*")
                ano     = st.text_input("Ano*")
                imagem  = st.text_input("URL da Imagem*")
            with c2:
                categoria = st.selectbox("Categoria:", ["Pintura","Escultura","Fotografia","Gravura","Desenho","Arte Digital","Outro"])
                tecnica   = st.text_input("Técnica:", placeholder="Ex: Óleo sobre tela")
                dimensoes = st.text_input("Dimensões:", placeholder="Ex: 100×80 cm")
                descricao = st.text_area("Descrição / Áudio-descrição:", height=90,
                                          placeholder="Texto acessível para pessoas com deficiência visual…")
            if st.form_submit_button("➕ Adicionar Obra", use_container_width=True):
                if titulo and artista and ano and imagem:
                    nid = max([o['id'] for o in obras])+1 if obras else 1
                    obras.append({"id":nid,"titulo":titulo,"artista":artista,"ano":ano,
                                  "categoria":categoria,"tecnica":tecnica,"dimensoes":dimensoes,
                                  "descricao":descricao,"imagem":imagem})
                    save_json_file(OBRAS_FILE, obras)
                    st.success("✅ Obra adicionada!")
                    st.cache_data.clear(); st.rerun()
                else: st.error("Preencha os campos obrigatórios (*)")

# ═══════════════════════════════════════════════════════════════════════
# ABA 7 — EXPORTAR
# ═══════════════════════════════════════════════════════════════════════
def tab_export():
    st.markdown("### 📥 Central de Exportação")
    tdf = all_tags(); udf = all_users(); obs = load_obras()
    t1,t2 = st.tabs(["🌍 Dados Gerais","👤 Por Participante"])

    with t1:
        c1,c2,c3 = st.columns(3)
        with c1:
            st.markdown("#### 🏷️ Tags")
            if not tdf.empty:
                st.download_button("⬇️ Todas as Tags (CSV)",
                    tdf.to_csv(index=False).encode('utf-8'),
                    f"tags_{datetime.now().strftime('%Y%m%d')}.csv","text/csv",
                    use_container_width=True)
                freq = tdf['tag'].value_counts().reset_index(); freq.columns=['Tag','Freq']
                freq['%'] = (freq['Freq']/freq['Freq'].sum()*100).round(2)
                st.download_button("⬇️ Frequências (CSV)",
                    freq.to_csv(index=False).encode('utf-8'),
                    f"freq_{datetime.now().strftime('%Y%m%d')}.csv","text/csv",
                    use_container_width=True)
        with c2:
            st.markdown("#### 👥 Usuários")
            if not udf.empty:
                st.download_button("⬇️ Usuários (CSV)",
                    udf.to_csv(index=False).encode('utf-8'),
                    f"usuarios_{datetime.now().strftime('%Y%m%d')}.csv","text/csv",
                    use_container_width=True)
        with c3:
            st.markdown("#### 🖼️ Obras")
            if obs:
                st.download_button("⬇️ Obras (CSV)",
                    pd.DataFrame(obs).to_csv(index=False).encode('utf-8'),
                    f"obras_{datetime.now().strftime('%Y%m%d')}.csv","text/csv",
                    use_container_width=True)
        st.markdown(divider(), unsafe_allow_html=True)
        st.markdown("#### 🔗 Exportar Conexões")
        if not tdf.empty:
            thr = st.slider("Limiar:", 0.20, 0.90, 0.35, 0.05, key="exp_thr")
            if st.button("Gerar e exportar conexões"):
                with st.spinner("Calculando…"):
                    conns = tag_connections(tdf['tag'].tolist(), threshold=thr)
                if conns:
                    st.download_button("⬇️ Conexões (CSV)",
                        pd.DataFrame(conns).to_csv(index=False).encode('utf-8'),
                        f"conexoes_{datetime.now().strftime('%Y%m%d')}.csv","text/csv",
                        use_container_width=True)
                    st.success(f"✅ {len(conns)} conexões geradas.")
                else: st.info("Nenhuma conexão com este limiar.")

    with t2:
        if udf.empty: st.info("Nenhum participante."); return
        uopts = [f"🐾 {r.get('animal_name',r['user_id'][:8])}" for _,r in udf.iterrows()]
        usel  = st.selectbox("Participante:", uopts, key="exp_u")
        uidx  = uopts.index(usel)
        uid   = udf.iloc[uidx]['user_id']
        uanim = udf.iloc[uidx].get('animal_name', uid[:8])

        st.markdown(f"#### Dados de **{uanim}**")
        c1,c2 = st.columns(2)
        with c1:
            st.markdown("##### 📝 Questionário")
            hq = html_quest(uid, uanim, udf)
            if hq:
                st.download_button("⬇️ Respostas (HTML → PDF)", hq,
                    f"quest_{uid[:8]}.html","text/html", use_container_width=True)
            ud = udf[udf['user_id']==uid]
            if not ud.empty:
                st.download_button("⬇️ Respostas (CSV)", ud.to_csv(index=False).encode('utf-8'),
                    f"quest_{uid[:8]}.csv","text/csv", use_container_width=True)
        with c2:
            st.markdown("##### 🏷️ Tags")
            ht = html_tags(uid, uanim, obs, tdf)
            if ht:
                st.download_button("⬇️ Tags (HTML → PDF)", ht,
                    f"tags_{uid[:8]}.html","text/html", use_container_width=True)
            ut = get_user_tags(uid)
            if not ut.empty:
                st.download_button("⬇️ Tags (CSV)", ut.to_csv(index=False).encode('utf-8'),
                    f"tags_{uid[:8]}.csv","text/csv", use_container_width=True)

# ── ENTRY POINT ───────────────────────────────────────────────────────
if __name__ == "__main__":
    main()
