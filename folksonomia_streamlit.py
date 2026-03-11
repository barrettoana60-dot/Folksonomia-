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
import re # Para processamento de texto para audiodescrição e nuvem de palavras
from wordcloud import WordCloud # Para a nuvem de palavras
import matplotlib.pyplot as plt # Para exibir a nuvem de palavras

warnings.filterwarnings('ignore')

# --- Configurações Iniciais ---
st.set_page_config(
    page_title="Sistema Folksonomia Digital",
    layout="wide",
    initial_sidebar_state="collapsed",
    page_icon="📚" # Mantendo o ícone da página, mas removendo emojis do conteúdo
)

DATA_DIR   = "data"
OBRAS_FILE = os.path.join(DATA_DIR, "obras.json")
TAGS_FILE  = os.path.join(DATA_DIR, "tags.json")
USERS_FILE = os.path.join(DATA_DIR, "users.json")
ADMIN_FILE = os.path.join(DATA_DIR, "admin.json")
ADMIN_USERNAME = "nugep"
ADMIN_PASSWORD = "nugep123"

ANIMAIS = [
    "Aguia","Boto","Capivara","Doninha","Ema","Falcao","Gaviao","Harpia","Irara","Jaguar",
    "Lontra","Mico","Onca","Paca","Quati","Raposa","Tamandua","Urubu","Veado","Zorrilho",
    "Arara","Bugio","Caititu","Jaguatirica","Lobo","Mutum","Pirarucu","Tucano","Sucuri","Tatu"
]
ADJETIVOS = [
    "Azul","Bravo","Calmo","Dourado","Esperto","Feroz","Gracioso","Intenso","Jovial","Lento",
    "Magico","Nobre","Ousado","Preciso","Rapido","Sabio","Timido","Unico","Valente","Zeloso",
    "Curioso","Furtivo","Altivo","Sereno","Vibrante","Audaz","Brilhante","Corajoso","Distinto","Elegante"
]

def generate_animal_name():
    random.seed()
    return f"{random.choice(ANIMAIS)} {random.choice(ADJETIVOS)}"

# --- CORE ---
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

# --- SIMILARIDADE ---
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
                if uniq[i] in uniq[j] or uniq[j] in uniq[i]: tipo = "Contencao"
                elif shared: tipo = f"Palavra comum: '{', '.join(shared)}'"
                else: tipo = "Similaridade fonetica"
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

# --- CSS E ACESSIBILIDADE ---
def load_css():
    # Carrega o tema atual (claro/escuro) e o tamanho da fonte
    theme = st.session_state.get('theme', 'dark')
    font_size = st.session_state.get('font_size', '16px')

    # Define as variáveis CSS com base no tema
    if theme == 'light':
        bg_gradient = 'linear-gradient(-45deg, #E0E0E0 0%, #F0F8FF 25%, #E0E0E0 50%, #F0F8FF 75%, #E0E0E0 100%)'
        text_color = '#333333'
        card_bg = 'rgba(255,255,255,0.8)'
        card_border = '1px solid rgba(0,0,0,0.1)'
        card_shadow = '0 8px 32px rgba(0,0,0,0.1)'
        navbar_bg = 'rgba(255,255,255,0.9)'
        navbar_border = '1px solid rgba(0,0,0,0.1)'
        logo_gradient = 'linear-gradient(135deg,#007bff 0%,#6610f2 100%)'
        title_color = '#001F3F'
        subtitle_color = 'rgba(51,51,51,0.9)'
        tag_badge_bg = 'rgba(0,0,0,0.1)'
        tag_badge_border = '1px solid rgba(0,0,0,0.2)'
        tag_badge_color = '#333'
        kpi_card_bg = 'rgba(0,0,0,0.08)'
        kpi_card_border = '1px solid rgba(0,0,0,0.15)'
        kpi_card_color = '#333'
        kpi_val_color = '#007bff'
        insight_bg = 'rgba(0,123,255,0.1)'
        insight_border = '1px solid rgba(0,123,255,0.2)'
        insight_color = '#333'
        insight_strong_color = '#007bff'
        conn_row_bg = 'rgba(0,0,0,0.05)'
        conn_row_border = '1px solid rgba(0,0,0,0.1)'
        cluster_wrap_bg = 'rgba(0,0,0,0.04)'
        cluster_wrap_border = '1px solid rgba(0,0,0,0.1)'
        cluster_title_color = 'rgba(102,16,242,0.8)'
        cluster_pill_bg = 'rgba(102,16,242,0.1)'
        cluster_pill_border = '1px solid rgba(102,16,242,0.2)'
        cluster_pill_color = '#6610f2'
        button_bg = 'rgba(0,0,0,0.15)'
        button_border = '1px solid rgba(0,0,0,0.25)'
        button_color = '#333'
        input_bg = 'rgba(0,0,0,0.1)'
        input_border = '1px solid rgba(0,0,0,0.2)'
        input_color = '#333'
        input_placeholder = 'rgba(51,51,51,0.5)'
        label_color = '#333'
        tabs_bg = 'rgba(0,0,0,0.1)'
        tabs_tab_bg = 'rgba(0,0,0,0.1)'
        tabs_tab_border = '1px solid rgba(0,0,0,0.15)'
        tabs_tab_color = '#333'
        tabs_tab_selected_bg = 'rgba(0,0,0,0.2)'
        tabs_tab_selected_border = '1px solid rgba(0,0,0,0.3)'
        alert_bg = 'rgba(0,0,0,0.1)'
        alert_color = '#333'
        dataframe_bg = 'rgba(0,0,0,0.1)'
        dataframe_border = '1px solid rgba(0,0,0,0.15)'
        dataframe_color = '#333'
        dataframe_th_bg = 'rgba(0,0,0,0.15)'
        dataframe_th_color = '#333'
        obra_card_bg = 'rgba(0,0,0,0.1)'
        obra_card_border = '1px solid rgba(0,0,0,0.15)'
        obra_card_after_bg = 'linear-gradient(135deg,rgba(255,255,255,.3),rgba(240,248,255,.3))'
        animal_badge_bg = 'rgba(0,123,255,0.1)'
        animal_badge_border = '1px solid rgba(0,123,255,0.2)'
        animal_badge_color = '#007bff'
        divider_bg = 'linear-gradient(90deg,transparent,rgba(0,0,0,.22),transparent)'
        tag_green_bg = 'rgba(34,197,94,.1)!important'
        tag_green_border = 'rgba(34,197,94,.3)!important'
        tag_green_color = '#16a34a!important'
        tag_amber_bg = 'rgba(245,158,11,.1)!important'
        tag_amber_border = 'rgba(245,158,11,.3)!important'
        tag_amber_color = '#b45309!important'
        tag_blue_bg = 'rgba(96,165,250,.1)!important'
        tag_blue_border = 'rgba(96,165,250,.3)!important'
        tag_blue_color = '#2563eb!important'
        sc_b_border = '#007bff'
        sc_b_bg = 'rgba(0,123,255,0.07)'
        sc_g_border = '#28a745'
        sc_g_bg = 'rgba(40,167,69,0.07)'
        sc_p_border = '#6610f2'
        sc_p_bg = 'rgba(102,16,242,0.07)'
        sc_a_border = '#ffc107'
        sc_a_bg = 'rgba(255,193,7,0.07)'
        pbar_o_bg = 'rgba(0,0,0,0.1)'
        pbar_i_bg = '#007bff'


    else: # dark theme
        bg_gradient = 'linear-gradient(-45deg,#000 0%,#001F3F 25%,#000 50%,#001F3F 75%,#000 100%)'
        text_color = '#e0e0e0'
        card_bg = 'rgba(255,255,255,0.15)'
        card_border = '1px solid rgba(255,255,255,0.3)'
        card_shadow = '0 8px 32px rgba(0,0,0,0.1)'
        navbar_bg = 'rgba(255,255,255,0.1)'
        navbar_border = '1px solid rgba(255,255,255,0.2)'
        logo_gradient = 'linear-gradient(135deg,#a7e6ff 0%,#d1baff 100%)'
        title_color = 'white'
        subtitle_color = 'rgba(255,255,255,0.95)'
        tag_badge_bg = 'rgba(255,255,255,0.25)'
        tag_badge_border = '1px solid rgba(255,255,255,0.4)'
        tag_badge_color = 'white'
        kpi_card_bg = 'rgba(255,255,255,0.16)'
        kpi_card_border = '1px solid rgba(255,255,255,0.28)'
        kpi_card_color = 'white'
        kpi_val_color = '#a7e6ff'
        insight_bg = 'rgba(167,230,255,0.1)'
        insight_border = '1px solid rgba(167,230,255,0.28)'
        insight_color = 'rgba(255,255,255,0.9)'
        insight_strong_color = '#a7e6ff'
        conn_row_bg = 'rgba(255,255,255,0.06)'
        conn_row_border = '3px solid rgba(255,255,255,0.2)'
        cluster_wrap_bg = 'rgba(255,255,255,0.05)'
        cluster_wrap_border = '1px solid rgba(255,255,255,0.1)'
        cluster_title_color = 'rgba(167,139,250,0.8)'
        cluster_pill_bg = 'rgba(168,85,247,0.2)'
        cluster_pill_border = '1px solid rgba(168,85,247,0.38)'
        cluster_pill_color = '#f3e8ff'
        button_bg = 'rgba(255,255,255,0.25)'
        button_border = '1px solid rgba(255,255,255,0.4)'
        button_color = 'white'
        input_bg = 'rgba(255,255,255,0.18)'
        input_border = '1px solid rgba(255,255,255,0.28)'
        input_color = 'white'
        input_placeholder = 'rgba(255,255,255,0.55)'
        label_color = 'white'
        tabs_bg = 'rgba(255,255,255,0.1)'
        tabs_tab_bg = 'rgba(255,255,255,0.14)'
        tabs_tab_border = '1px solid rgba(255,255,255,0.18)'
        tabs_tab_color = 'white'
        tabs_tab_selected_bg = 'rgba(255,255,255,0.33)'
        tabs_tab_selected_border = '1px solid rgba(255,255,255,0.48)'
        alert_bg = 'rgba(255,255,255,0.18)'
        alert_color = 'white'
        dataframe_bg = 'rgba(255,255,255,0.14)'
        dataframe_border = '1px solid rgba(255,255,255,0.2)'
        dataframe_color = 'white'
        dataframe_th_bg = 'rgba(255,255,255,0.22)'
        dataframe_th_color = 'white'
        obra_card_bg = 'rgba(255,255,255,0.2)'
        obra_card_border = '1px solid rgba(255,255,255,0.3)'
        obra_card_after_bg = 'linear-gradient(135deg,rgba(0,0,0,.3),rgba(0,31,63,.3))'
        animal_badge_bg = 'rgba(167,230,255,.2)'
        animal_badge_border = '1px solid rgba(167,230,255,.45)'
        animal_badge_color = '#a7e6ff'
        divider_bg = 'linear-gradient(90deg,transparent,rgba(255,255,255,.22),transparent)'
        tag_green_bg = 'rgba(34,197,94,.25)!important'
        tag_green_border = 'rgba(34,197,94,.5)!important'
        tag_green_color = '#dcfce7!important'
        tag_amber_bg = 'rgba(245,158,11,.25)!important'
        tag_amber_border = 'rgba(245,158,11,.5)!important'
        tag_amber_color = '#fef3c7!important'
        tag_blue_bg = 'rgba(96,165,250,.25)!important'
        tag_blue_border = 'rgba(96,165,250,.5)!important'
        tag_blue_color = '#dbeafe!important'
        sc_b_border = '#60a5fa'
        sc_b_bg = 'rgba(96,165,250,.07)'
        sc_g_border = '#34d399'
        sc_g_bg = 'rgba(52,211,153,.07)'
        sc_p_border = '#a78bfa'
        sc_p_bg = 'rgba(167,139,250,.07)'
        sc_a_border = '#fbbf24'
        sc_a_bg = 'rgba(251,191,36,.07)'
        pbar_o_bg = 'rgba(255,255,255,.1)'
        pbar_i_bg = '#60a5fa'


    st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800&display=swap');
:root {{
    --font-size-base: {font_size};
    --bg-gradient: {bg_gradient};
    --text-color: {text_color};
    --card-bg: {card_bg};
    --card-border: {card_border};
    --card-shadow: {card_shadow};
    --navbar-bg: {navbar_bg};
    --navbar-border: {navbar_border};
    --logo-gradient: {logo_gradient};
    --title-color: {title_color};
    --subtitle-color: {subtitle_color};
    --tag-badge-bg: {tag_badge_bg};
    --tag-badge-border: {tag_badge_border};
    --tag-badge-color: {tag_badge_color};
    --kpi-card-bg: {kpi_card_bg};
    --kpi-card-border: {kpi_card_border};
    --kpi-card-color: {kpi_card_color};
    --kpi-val-color: {kpi_val_color};
    --insight-bg: {insight_bg};
    --insight-border: {insight_border};
    --insight-color: {insight_color};
    --insight-strong-color: {insight_strong_color};
    --conn-row-bg: {conn_row_bg};
    --conn-row-border: {conn_row_border};
    --cluster-wrap-bg: {cluster_wrap_bg};
    --cluster-wrap-border: {cluster_wrap_border};
    --cluster-title-color: {cluster_title_color};
    --cluster-pill-bg: {cluster_pill_bg};
    --cluster-pill-border: {cluster_pill_border};
    --cluster-pill-color: {cluster_pill_color};
    --button-bg: {button_bg};
    --button-border: {button_border};
    --button-color: {button_color};
    --input-bg: {input_bg};
    --input-border: {input_border};
    --input-color: {input_color};
    --input-placeholder: {input_placeholder};
    --label-color: {label_color};
    --tabs-bg: {tabs_bg};
    --tabs-tab-bg: {tabs_tab_bg};
    --tabs-tab-border: {tabs_tab_border};
    --tabs-tab-color: {tabs_tab_color};
    --tabs-tab-selected-bg: {tabs_tab_selected_bg};
    --tabs-tab-selected-border: {tabs_tab_selected_border};
    --alert-bg: {alert_bg};
    --alert-color: {alert_color};
    --dataframe-bg: {dataframe_bg};
    --dataframe-border: {dataframe_border};
    --dataframe-color: {dataframe_color};
    --dataframe-th-bg: {dataframe_th_bg};
    --dataframe-th-color: {dataframe_th_color};
    --obra-card-bg: {obra_card_bg};
    --obra-card-border: {obra_card_border};
    --obra-card-after-bg: {obra_card_after_bg};
    --animal-badge-bg: {animal_badge_bg};
    --animal-badge-border: {animal_badge_border};
    --animal-badge-color: {animal_badge_color};
    --divider-bg: {divider_bg};
    --tag-green-bg: {tag_green_bg};
    --tag-green-border: {tag_green_border};
    --tag-green-color: {tag_green_color};
    --tag-amber-bg: {tag_amber_bg};
    --tag-amber-border: {tag_amber_border};
    --tag-amber-color: {tag_amber_color};
    --tag-blue-bg: {tag_blue_bg};
    --tag-blue-border: {tag_blue_border};
    --tag-blue-color: {tag_blue_color};
    --sc-b-border: {sc_b_border};
    --sc-b-bg: {sc_b_bg};
    --sc-g-border: {sc_g_border};
    --sc-g-bg: {sc_g_bg};
    --sc-p-border: {sc_p_border};
    --sc-p-bg: {sc_p_bg};
    --sc-a-border: {sc_a_border};
    --sc-a-bg: {sc_a_bg};
    --pbar-o-bg: {pbar_o_bg};
    --pbar-i-bg: {pbar_i_bg};
}}

*{{margin:0;padding:0;box-sizing:border-box;font-family:'Poppins',sans-serif!important}}
html {{ font-size: var(--font-size-base); }}
body {{ font-size: var(--font-size-base); }}

@keyframes bg{{0%{{background-position:0% 50%}}50%{{background-position:100% 50%}}100%{{background-position:0% 50%}}}}
.stApp{{background:var(--bg-gradient);
  background-size:400% 400%;animation:bg 15s ease infinite;color:var(--text-color)}}

.top-navbar{{position:fixed;top:0;left:0;right:0;z-index:9999;
  background:var(--navbar-bg);backdrop-filter:blur(20px) saturate(180%);
  border-bottom:var(--navbar-border);padding:1.4rem 3rem;
  display:flex;justify-content:space-between;align-items:center;
  box-shadow:0 8px 32px rgba(0,0,0,.1)}}
.navbar-logo{{font-size:1.8rem;font-weight:800;
  background:var(--logo-gradient);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;letter-spacing:-1px}}

.main-content{{margin-top:120px;padding:2rem 3rem;max-width:1600px;margin-left:auto;margin-right:auto}}

.glass-card{{background:var(--card-bg);backdrop-filter:blur(20px) saturate(180%);
  border:var(--card-border);border-radius:24px;padding:2.5rem;margin:1.5rem 0;
  box-shadow:var(--card-shadow);transition:all .4s cubic-bezier(.4,0,.2,1);
  position:relative;overflow:hidden}}
.glass-card::before{{content:'';position:absolute;top:0;left:-100%;width:100%;height:100%;
  background:linear-gradient(90deg,transparent,rgba(255,255,255,.3),transparent);transition:left .5s}}
.glass-card:hover::before{{left:100%}}
.glass-card:hover{{transform:translateY(-8px) scale(1.02);box-shadow:0 16px 48px rgba(0,0,0,.2);
  border-color:rgba(255,255,255,.5)}}

.obra-card{{background:var(--obra-card-bg);backdrop-filter:blur(15px) saturate(180%);
  border:var(--obra-card-border);border-radius:20px;overflow:hidden;
  transition:all .4s cubic-bezier(.4,0,.2,1);cursor:pointer;position:relative}}
.obra-card::after{{content:'';position:absolute;top:0;left:0;right:0;bottom:0;
  background:var(--obra-card-after-bg);opacity:0;transition:opacity .4s}}
.obra-card:hover::after{{opacity:1}}
.obra-card:hover{{transform:translateY(-12px) scale(1.03);box-shadow:0 20px 60px rgba(0,31,63,.4);
  border-color:rgba(255,255,255,.6)}}
.obra-card img{{width:100%;height:280px;object-fit:cover;transition:transform .6s cubic-bezier(.4,0,.2,1)}}
.obra-card:hover img{{transform:scale(1.15) rotate(2deg)}}

.main-title{{color:var(--title-color);font-size:3.5rem;font-weight:800;text-align:center;margin:2rem 0 1rem;
  letter-spacing:-2px;text-shadow:0 4px 20px rgba(0,0,0,.3)}}
.subtitle{{color:var(--subtitle-color);font-size:1.3rem;text-align:center;margin-bottom:3rem;
  line-height:1.8;font-weight:300}}

.tag-badge{{display:inline-block;background:var(--tag-badge-bg);backdrop-filter:blur(10px);
  border:var(--tag-badge-border);color:var(--tag-badge-color);padding:.5rem 1.1rem;border-radius:50px;
  margin:.3rem;font-size:.88rem;font-weight:600;transition:all .3s}}
.tag-badge:hover{{background:rgba(255,255,255,.4);transform:translateY(-3px) scale(1.05)}}
.tag-green {{background:var(--tag-green-bg);border-color:var(--tag-green-border);color:var(--tag-green-color)}}
.tag-amber {{background:var(--tag-amber-bg);border-color:var(--tag-amber-border);color:var(--tag-amber-color)}}
.tag-blue  {{background:var(--tag-blue-bg);border-color:var(--tag-blue-border);color:var(--tag-blue-color)}}

.animal-badge{{display:inline-block;background:var(--animal-badge-bg);border:var(--animal-badge-border);
  color:var(--animal-badge-color);padding:.35rem 1rem;border-radius:50px;font-size:.85rem;font-weight:700}}

.kpi-card{{background:var(--kpi-card-bg);backdrop-filter:blur(20px) saturate(180%);
  border:var(--kpi-card-border);border-radius:18px;padding:1.6rem;text-align:center;
  color:var(--kpi-card-color);box-shadow:0 8px 32px rgba(0,0,0,.12);transition:all .4s}}
.kpi-card:hover{{transform:translateY(-6px) scale(1.04);box-shadow:0 16px 48px rgba(0,31,63,.28)}}
.kpi-val{{font-size:2.5rem;font-weight:800;margin:.6rem 0;text-shadow:0 4px 20px rgba(0,0,0,.2); color:var(--kpi-val-color)}}
.kpi-lbl{{font-size:.78rem;text-transform:uppercase;letter-spacing:2px;font-weight:600;opacity:.8}}
.kpi-sub{{font-size:.7rem;opacity:.5;margin-top:.3rem}}

.sc{{background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.13);border-radius:14px;padding:1.3rem;margin:.7rem 0}}
.sc-b{{border-left:4px solid var(--sc-b-border);background:var(--sc-b-bg)}}
.sc-g{{border-left:4px solid var(--sc-g-border);background:var(--sc-g-bg)}}
.sc-p{{border-left:4px solid var(--sc-p-border);background:var(--sc-p-bg)}}
.sc-a{{border-left:4px solid var(--sc-a-border);background:var(--sc-a-bg)}}

.insight{{background:var(--insight-bg);border:var(--insight-border);border-radius:12px;
  padding:1rem 1.4rem;margin:.6rem 0;color:var(--insight-color);font-size:.9rem;line-height:1.7}}
.insight strong{{color:var(--insight-strong-color)}}

.conn-row{{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;
  background:var(--conn-row-bg);border-radius:11px;padding:.85rem 1.2rem;margin:.3rem 0;
  border-left:var(--conn-row-border);transition:background .2s}}
.conn-row:hover{{background:rgba(255,255,255,.12)}}

.cluster-wrap{{background:var(--cluster-wrap-bg);border-radius:14px;padding:1.1rem 1.4rem;
  margin:.5rem 0;border:var(--cluster-wrap-border)}}
.cluster-title{{font-size:.76rem;text-transform:uppercase;letter-spacing:1.5px;
  color:var(--cluster-title-color);margin-bottom:.55rem;font-weight:700}}
.cluster-pill{{display:inline-flex;align-items:center;gap:5px;background:var(--cluster-pill-bg);
  border:var(--cluster-pill-border);border-radius:50px;padding:.32rem .85rem;
  margin:.2rem;font-size:.78rem;font-weight:600;color:var(--cluster-pill-color)}}

.pbar-o{{background:var(--pbar-o-bg);border-radius:50px;height:6px;margin:3px 0;overflow:hidden}}
.pbar-i{{height:100%;border-radius:50px;transition:width .5s; background:var(--pbar-i-bg)}}
.divider{{height:1px;background:var(--divider-bg);margin:1.6rem 0}}

.stButton button{{background:var(--button-bg)!important;backdrop-filter:blur(15px)!important;
  color:var(--button-color)!important;border:var(--button-border)!important;border-radius:50px!important;
  padding:1rem 2.5rem!important;font-weight:700!important;font-size:1rem!important;
  transition:all .4s!important;box-shadow:0 8px 25px rgba(0,0,0,.15)!important;
  text-transform:uppercase;letter-spacing:1px}}
.stButton button:hover{{background:rgba(255,255,255,.4)!important;
  box-shadow:0 12px 40px rgba(0,31,63,.4)!important;
  transform:translateY(-4px) scale(1.05)!important;border-color:rgba(255,255,255,.6)!important}}

.stTextInput input,.stTextArea textarea,.stSelectbox select,.stMultiSelect div[data-baseweb="select"]{{
  background:var(--input-bg)!important;backdrop-filter:blur(10px)!important;
  border:var(--input-border)!important;color:var(--input-color)!important;
  border-radius:14px!important;padding:.9rem!important;font-weight:500!important}}
.stTextInput input::placeholder,.stTextArea textarea::placeholder{{color:var(--input-placeholder)!important}}
.stTextInput input:focus,.stTextArea textarea:focus{{
  border-color:rgba(255,255,255,.6)!important;box-shadow:0 0 0 3px rgba(255,255,255,.18)!important}}

label{{color:var(--label-color)!important;font-weight:700!important;font-size:1rem!important;
  text-shadow:0 2px 10px rgba(0,0,0,.2)}}

.stTabs [data-baseweb="tab-list"]{{gap:.7rem;background:var(--tabs-bg);
  backdrop-filter:blur(10px);padding:.45rem;border-radius:14px}}
.stTabs [data-baseweb="tab"]{{background:var(--tabs-tab-bg);
  border:var(--tabs-tab-border);border-radius:10px;color:var(--tabs-tab-color);
  padding:.75rem 1.5rem;font-weight:700;transition:all .3s}}
.stTabs [data-baseweb="tab"]:hover{{background:rgba(255,255,255,.24);transform:translateY(-2px)}}
.stTabs [aria-selected="true"]{{background:var(--tabs-tab-selected-bg)!important;
  border-color:var(--tabs-tab-selected-border)!important;box-shadow:0 6px 20px rgba(0,31,63,.25)!important}}

.stAlert{{background:var(--alert-bg)!important;backdrop-filter:blur(15px)!important;
  border-radius:14px!important;border-left:4px solid!important;color:var(--alert-color)!important}}
#MainMenu,footer,header{{visibility:hidden}}
.stDeployButton{{display:none}}
[data-testid="stSidebar"]{{display:none}}
h1,h2,h3,h4,h5,h6{{color:var(--title-color);font-weight:700;text-shadow:0 2px 15px rgba(0,0,0,.3)}}
.dataframe{{background:var(--dataframe-bg)!important;border:var(--dataframe-border)!important;
  border-radius:14px!important;color:var(--dataframe-color)!important}}
.dataframe th{{background:var(--dataframe-th-bg)!important;color:var(--dataframe-th-color)!important;font-weight:700!important}}
.dataframe td{{color:var(--dataframe-color)!important}}
div[data-testid="stTextInput"]>div{{background:transparent!important;border:none!important;
  box-shadow:none!important;padding:0!important}}
div[data-testid="stTextInput"]{{background:transparent!important;border:none!important}}
div[data-testid="stTextInput"] input{{border-radius:11px!important;
  background:var(--input-bg)!important;border:var(--input-border)!important;
  padding:.75rem 1rem!important}}
@media(max-width:768px){{.main-title{{font-size:2.5rem}}.main-content{{margin-top:140px;padding:1rem}}}}

/* ARIA attributes for accessibility */
[role="button"], [role="link"], [role="tab"], [role="option"], [role="checkbox"], [role="radio"] {{
    cursor: pointer;
}}
[role="img"] {{
    display: block; /* Ensure images are treated as blocks for screen readers */
}}
</style>""", unsafe_allow_html=True)

# --- HELPERS ---
def kpi(label, value, sub="", color="var(--kpi-val-color)"):
    return (f"<div class='kpi-card' aria-label='Métrica: {label}. Valor: {value}. {sub}'>"
            f"<div class='kpi-lbl'>{label}</div>"
            f"<div class='kpi-val' style='color:{color}'>{value}</div>"
            f"{'<div class=kpi-sub>'+sub+'</div>' if sub else ''}"
            f"</div>")

def insight(text):
    return f"<div class='insight' aria-live='polite'>{text}</div>"

def divider():
    return "<div class='divider' role='separator'></div>"

def pbar(pct, color="var(--pbar-i-bg)"):
    w = min(100, max(0, pct*100))
    return f"<div class='pbar-o' role='progressbar' aria-valuenow='{w:.1f}' aria-valuemin='0' aria-valuemax='100'>" \
           f"<div class='pbar-i' style='width:{w:.1f}%;background:{color}'></div></div>"

# --- DADOS ---
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
         "audiodescricao":"Uma pintura em preto, branco e cinza que retrata o sofrimento de pessoas e animais em meio à guerra, com figuras distorcidas e angústia expressa."},
        {"id":2,"titulo":"A Noite Estrelada","artista":"Vincent van Gogh","ano":"1889",
         "imagem":"https://upload.wikimedia.org/wikipedia/commons/thumb/e/ea/Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg/1200px-Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg",
         "audiodescricao":"Uma paisagem noturna vibrante com um céu turbulento e estrelas brilhantes em espiral, um cipreste escuro em primeiro plano e uma pequena vila pacífica ao fundo."},
        {"id":3,"titulo":"Mona Lisa","artista":"Leonardo da Vinci","ano":"1503",
         "imagem":"https://upload.wikimedia.org/wikipedia/commons/thumb/e/ec/Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_retouched.jpg/800px-Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_retouched.jpg",
         "audiodescricao":"Retrato de uma mulher com um sorriso enigmático, sentada diante de uma paisagem montanhosa e nebulosa. Ela veste roupas escuras e tem as mãos cruzadas."}
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

# --- EXPORTAÇÃO ---
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
<body><div class="c"><h1>Respostas do Questionario</h1>
<div class="hi">
  <p>Usuario Anonimo: <span class="ab"> {animal}</span></p>
  <p style="margin-top:6px;opacity:.65">Data: {ui.get('timestamp','N/A')}</p>
</div>
<div class="qb"><div class="q">1. Nivel de familiaridade com museus</div>
<div class="a">{ui.get('q1','N/A')}</div></div>
<div class="qb"><div class="q">2. Conhecimento sobre documentacao museologica</div>
<div class="a">{ui.get('q2','N/A')}</div></div>
<div class="qb"><div class="q">3. O que voce entende por 'tags'?</div>
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
<body><div class="c"><h1>Relatorio de Tags</h1>
<div class="hi">
  <p>Usuario Anonimo: <span class="ab"> {animal}</span></p>
  <p style="margin-top:6px;opacity:.65">Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
</div>
<div class="stats">
  <div class="sb"><div class="sv">{len(ut)}</div><div class="sl">Total de Tags</div></div>
  <div class="sb"><div class="sv">{ut['tag'].nunique()}</div><div class="sl">Tags Unicas</div></div>
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

# --- INTERFACE PRINCIPAL ---
def show_header():
    st.markdown(
        "<div class='top-navbar' role='navigation' aria-label='Barra de Navegação Principal'>"
        "<div class='navbar-logo' aria-label='Sistema Folksonomia Digital'>Sistema Folksonomia Digital</div>"
        "</div>", unsafe_allow_html=True)

def main():
    # Inicializa estados de sessão para acessibilidade
    if 'theme' not in st.session_state:
        st.session_state['theme'] = 'dark' # Default dark theme
    if 'font_size' not in st.session_state:
        st.session_state['font_size'] = '16px' # Default font size

    load_css() # Carrega o CSS com base no tema e tamanho da fonte

    try: check_admin()
    except Exception as e: st.error(f"Erro ao inicializar: {e}")

    for k,v in [('user_id',gen_uid()),('animal_name',generate_animal_name()),
                ('step','intro'),('answers',{})]:
        if k not in st.session_state: st.session_state[k] = v

    # Sidebar para controles de acessibilidade
    with st.sidebar:
        st.header("Acessibilidade")
        # Botão para alternar tema
        if st.button(f"Alternar para Tema {'Claro' if st.session_state['theme'] == 'dark' else 'Escuro'}", key="theme_toggle"):
            st.session_state['theme'] = 'light' if st.session_state['theme'] == 'dark' else 'dark'
            st.rerun()

        # Slider para tamanho da fonte
        font_size_options = ['14px', '16px', '18px', '20px']
        current_font_idx = font_size_options.index(st.session_state['font_size'])
        selected_font_size = st.select_slider(
            "Tamanho da Fonte",
            options=font_size_options,
            value=st.session_state['font_size'],
            key="font_size_slider"
        )
        if selected_font_size != st.session_state['font_size']:
            st.session_state['font_size'] = selected_font_size
            st.rerun()

    if st.session_state['step'] != 'completed':
        show_intro()
    else:
        show_header()
        st.markdown("<div class='main-content' role='main'>", unsafe_allow_html=True)
        t1, t2 = st.tabs([" Explorar Obras"," Area Administrativa"])
        with t1: show_obras()
        with t2: show_admin()
        st.markdown("</div>", unsafe_allow_html=True)

# --- INTRO ---
def show_intro():
    st.markdown("<div class='main-content' role='main'>", unsafe_allow_html=True)
    st.markdown("<h1 class='main-title' aria-label='Sistema Folksonomia Digital'>Sistema Folksonomia Digital</h1>", unsafe_allow_html=True)
    st.markdown("<p class='subtitle' aria-label='Sistema colaborativo de catalogacao de obras de arte. Complete o questionario para acessar a plataforma.'>Sistema colaborativo de catalogacao de obras de arte<br>Complete o questionario para acessar a plataforma</p>", unsafe_allow_html=True)
    st.markdown("<div class='glass-card' role='form' aria-labelledby='questionario-acesso-titulo'>", unsafe_allow_html=True)
    st.markdown("<h2 id='questionario-acesso-titulo' style='text-align:center;margin-bottom:2.2rem;font-size:1.7rem'>Questionario de Acesso</h2>", unsafe_allow_html=True)
    with st.form("intro_form"):
        c1, c2 = st.columns(2)
        with c1:
            q1 = st.selectbox("1. Qual e o seu nivel de familiaridade com museus?",
                ["Nunca visito museus","Visito raramente","Visito ocasionalmente","Visito frequentemente"],
                key="q1_select", aria_label="Qual e o seu nivel de familiaridade com museus?")
            q2 = st.selectbox("2. Voce ja ouviu falar sobre documentacao museologica?",
                ["Nunca ouvi falar","Ja ouvi, mas nao sei o que e","Tenho uma ideia basica","Conheco bem o tema"],
                key="q2_select", aria_label="Voce ja ouviu falar sobre documentacao museologica?")
        with c2:
            q3 = st.text_area("3. O que voce entende por 'tags' ou etiquetas digitais aplicadas a acervo?",
                max_chars=500, height=200, placeholder="Descreva sua compreensao sobre o conceito...",
                key="q3_textarea", aria_label="O que voce entende por 'tags' ou etiquetas digitais aplicadas a acervo?")
        _, cb, _ = st.columns([1,1,1])
        with cb:
            submit = st.form_submit_button("Acessar Plataforma", use_container_width=True, aria_label="Botao para acessar a plataforma apos preencher o questionario")
        if submit:
            if not q3.strip():
                st.error("Por favor, responda todas as perguntas para continuar!")
            else:
                st.session_state['answers'] = {"q1":q1,"q2":q2,"q3":q3}
                save_answers(st.session_state['user_id'], st.session_state['animal_name'],
                             st.session_state['answers'])
                st.session_state['step'] = 'completed'
                st.success("Questionario completo! Acesso liberado.")
                # st.balloons() # Removido conforme solicitado (sem emojis)
                st.rerun()
    st.markdown("</div></div>", unsafe_allow_html=True)

# --- GALERIA ---
def show_obras():
    st.markdown("<h1 class='main-title' aria-label='Galeria de Obras de Arte'>Galeria de Obras de Arte</h1>", unsafe_allow_html=True)
    st.markdown("<p class='subtitle' aria-label='Explore as obras e contribua com suas tags descritivas'>Explore as obras e contribua com suas tags descritivas</p>",
                unsafe_allow_html=True)
    obras = load_obras()
    if not obras:
        st.info("Nenhuma obra cadastrada.")
        return

    st.markdown("<div class='glass-card' role='region' aria-labelledby='filtros-obras-titulo'>", unsafe_allow_html=True)
    st.markdown("<h2 id='filtros-obras-titulo' style='font-size:1.5rem;margin-bottom:1rem'>Filtros de Obras</h2>", unsafe_allow_html=True)

    # Filtros detalhados
    col_id, col_artist = st.columns(2)
    with col_id:
        sid = st.text_input("Filtrar por numero da obra:", "", placeholder="Ex: 1, 2, 3...", key="filter_id", aria_label="Filtrar por numero da obra")
    with col_artist:
        all_artists = sorted(list(set(o['artista'] for o in obras)))
        selected_artists = st.multiselect("Filtrar por artista:", all_artists, key="filter_artist", aria_label="Filtrar por artista")

    col_year, col_tags = st.columns(2)
    with col_year:
        all_years = sorted(list(set(o['ano'] for o in obras)))
        selected_years = st.multiselect("Filtrar por ano:", all_years, key="filter_year", aria_label="Filtrar por ano")
    with col_tags:
        all_available_tags = sorted(list(set(t['tag'] for t in all_tags().to_dict('records')))) # Pega todas as tags existentes
        selected_tags = st.multiselect("Filtrar por tags existentes:", all_available_tags, key="filter_tags", aria_label="Filtrar por tags existentes")

    sord = st.selectbox("Ordenar por:", ["Numero (crescente)","Numero (decrescente)","Titulo (A-Z)","Titulo (Z-A)","Artista (A-Z)","Artista (Z-A)","Ano (crescente)","Ano (decrescente)"], key="sort_order", aria_label="Ordenar obras por")
    st.markdown("</div>", unsafe_allow_html=True)

    filtered = obras
    if sid.strip().isdigit():
        filtered = [o for o in filtered if str(o['id'])==sid.strip()]
    if selected_artists:
        filtered = [o for o in filtered if o['artista'] in selected_artists]
    if selected_years:
        filtered = [o for o in filtered if o['ano'] in selected_years]
    if selected_tags:
        # Filtra obras que possuem pelo menos UMA das tags selecionadas
        # Para isso, precisamos carregar todas as tags e mapeá-las às obras
        all_tags_df = all_tags()
        obra_ids_with_selected_tags = set(all_tags_df[all_tags_df['tag'].isin(selected_tags)]['obra_id'].unique())
        filtered = [o for o in filtered if o['id'] in obra_ids_with_selected_tags]

    # Ordenação
    if sord == "Numero (crescente)":
        filtered = sorted(filtered, key=lambda x: x['id'])
    elif sord == "Numero (decrescente)":
        filtered = sorted(filtered, key=lambda x: x['id'], reverse=True)
    elif sord == "Titulo (A-Z)":
        filtered = sorted(filtered, key=lambda x: x['titulo'].lower())
    elif sord == "Titulo (Z-A)":
        filtered = sorted(filtered, key=lambda x: x['titulo'].lower(), reverse=True)
    elif sord == "Artista (A-Z)":
        filtered = sorted(filtered, key=lambda x: x['artista'].lower())
    elif sord == "Artista (Z-A)":
        filtered = sorted(filtered, key=lambda x: x['artista'].lower(), reverse=True)
    elif sord == "Ano (crescente)":
        filtered = sorted(filtered, key=lambda x: int(x['ano']) if x['ano'].isdigit() else 9999) # Trata anos não numéricos
    elif sord == "Ano (decrescente)":
        filtered = sorted(filtered, key=lambda x: int(x['ano']) if x['ano'].isdigit() else 0, reverse=True)


    st.markdown(f"<div style='text-align:center;color:var(--text-color);margin:1.8rem 0;"
                f"font-size:1.1rem;font-weight:600' aria-live='polite'>Exibindo "
                f"<strong style='font-size:1.4rem'>{len(filtered)}</strong> obra(s)</div>",
                unsafe_allow_html=True)

    cols = st.columns(3)
    for i, obra in enumerate(filtered):
        with cols[i%3]:
            st.markdown(f"""<div class='obra-card' role='figure' aria-labelledby='obra-titulo-{obra['id']}'>
<img src='{obra['imagem']}' alt='{obra['titulo']} por {obra['artista']}' role='img' aria-describedby='audiodescricao-{obra['id']}' />
<div style='padding:1.4rem'>
  <h3 id='obra-titulo-{obra['id']}' style='font-size:1.05rem;font-weight:700;margin-bottom:.35rem'>Obra #{obra['id']} - {obra['titulo']}</h3>
  <p style='font-size:.88rem;opacity:.65'>{obra['artista']} - {obra['ano']}</p>
  <p id='audiodescricao-{obra['id']}' class='sr-only'>{obra.get('audiodescricao', 'Nao ha audiodescricao disponivel para esta imagem.')}</p>
</div></div>""", unsafe_allow_html=True)

            # Botão de audiodescrição
            if st.button("Ouvir Audiodescricao", key=f"audio_desc_{obra['id']}", use_container_width=True, aria_label=f"Ouvir audiodescricao para a obra {obra['titulo']}"):
                st.info(f"Audiodescricao para '{obra['titulo']}': {obra.get('audiodescricao', 'Nao ha audiodescricao disponivel para esta imagem.')}")

            if st.button("Adicionar Tag", key=f"btn_{obra['id']}", use_container_width=True, aria_label=f"Adicionar tag para a obra {obra['titulo']}"):
                st.session_state['selected_obra'] = obra
                st.rerun()
            if ('selected_obra' in st.session_state and
                    st.session_state['selected_obra']['id'] == obra['id']):
                with st.form(f"tf_{obra['id']}", aria_label=f"Formulario para adicionar tag a obra {obra['titulo']}"):
                    tag = st.text_input("Sua tag:", key=f"t_{obra['id']}",
                                        placeholder="Ex: azul, triste, moderno...", aria_label="Campo para digitar sua tag")
                    ca, cb = st.columns(2)
                    with ca: sub = st.form_submit_button("Enviar", use_container_width=True, aria_label="Botao para enviar a tag")
                    with cb: can = st.form_submit_button("Cancelar", use_container_width=True, aria_label="Botao para cancelar a adicao de tag")
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
                    f"<span class='tag-badge' aria-label='Tag {r['tag']} com {r['count']} usos'>{r['tag']} ({r['count']})</span>"
                    for _, r in ut.iterrows()
                ), unsafe_allow_html=True)
            else:
                st.info("Voce ainda nao criou tags para esta obra")

# --- ADMIN ---
def show_admin():
    if 'admin_logged_in' not in st.session_state:
        st.session_state['admin_logged_in'] = False
    if not st.session_state['admin_logged_in']:
        st.markdown("<h1 class='main-title' aria-label='Area Administrativa'>Area Administrativa</h1>", unsafe_allow_html=True)
        st.markdown("<p class='subtitle' aria-label='Acesso restrito'>Acesso restrito</p>", unsafe_allow_html=True)
        _, c2, _ = st.columns([1,1,1])
        with c2:
            st.markdown("<div class='glass-card' role='form' aria-labelledby='login-admin-titulo'>", unsafe_allow_html=True)
            st.markdown("<h2 id='login-admin-titulo' style='text-align:center;margin-bottom:1.8rem'>Login Administrativo</h2>", unsafe_allow_html=True)
            with st.form("login"):
                username = st.text_input("Usuario:", placeholder="Digite seu usuario", key="admin_username_input", aria_label="Campo de usuario para login administrativo")
                password = st.text_input("Senha:", type="password", placeholder="Digite sua senha", key="admin_password_input", aria_label="Campo de senha para login administrativo")
                sub = st.form_submit_button("Entrar no Sistema", use_container_width=True, aria_label="Botao para entrar no sistema administrativo")
                if sub:
                    if check_login(username, password):
                        st.session_state['admin_logged_in'] = True
                        st.session_state['admin_username']  = username
                        st.success("Login realizado com sucesso!")
                        # st.balloons() # Removido
                        st.rerun()
                    else:
                        st.error("Credenciais invalidas. Acesso negado.")
            st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.markdown(
            f"<h1 class='main-title' aria-label='Dashboard Administrativo'>Dashboard Administrativo</h1>"
            f"<p class='subtitle' aria-label='Bem-vindo, {st.session_state.get('admin_username','Admin')}'>Bem-vindo, "
            f"<strong>{st.session_state.get('admin_username','Admin')}</strong></p>",
            unsafe_allow_html=True)
        tabs = st.tabs([
            " Visao Geral",
            " Analise de Tags",
            " Conexoes de Tags",
            " Usuarios & Questionario",
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
            if st.button("Sair do Sistema", use_container_width=True, aria_label="Botao para sair do sistema administrativo"):
                st.session_state['admin_logged_in'] = False
                st.rerun()

# ═════════════════════════════════════════════════════════════════════
# ABA 1 — VISÃO GERAL
# ═════════════════════════════════════════════════════════════════════
def tab_overview():
    tdf = all_tags()
    udf = all_users()
    obs = load_obras()

    st.markdown("### Metricas Gerais do Sistema")
    total  = len(tdf) if not tdf.empty else 0
    unicas = tdf['tag'].nunique() if not tdf.empty else 0
    nusers = udf['user_id'].nunique() if not udf.empty else 0
    nobs   = len(obs)
    obs_ct = tdf['obra_id'].nunique() if not tdf.empty else 0

    c1,c2,c3,c4,c5 = st.columns(5)
    for col, lbl, val, sub, clr in [
        (c1,"Total de Tags",     total,   "registros","#a7e6ff"),
        (c2,"Tags Unicas",       unicas,  f"{unicas/total:.0%} do total" if total else "—","#d1baff"),
        (c3,"Participantes",     nusers,  "usuarios ativos","#6ee7b7"),
        (c4,"Obras Cadastradas", nobs,    f"{obs_ct} com tags","#fcd34d"),
        (c5,"Media Tags/Usuario",f"{total/nusers:.1f}" if nusers else "—","por participante","#f9a8d4"),
    ]:
        with col: st.markdown(kpi(lbl,val,sub,clr), unsafe_allow_html=True)

    st.markdown(divider(), unsafe_allow_html=True)

    if not udf.empty and not tdf.empty:
        st.markdown("### Participantes Anonimos")
        uct = tdf.groupby('user_id').size().reset_index(name='tags')
        uuq = tdf.groupby('user_id')['tag'].nunique().reset_index(name='unicas')
        m   = udf.merge(uct,on='user_id',how='left').merge(uuq,on='user_id',how='left').fillna(0)
        for _, row in m.iterrows():
            animal = row.get('animal_name','?')
            ts     = row.get('timestamp','N/A')
            nt, nu = int(row['tags']), int(row['unicas'])
            p      = nu/nt if nt>0 else 0
            st.markdown(
                f"<div class='sc sc-b' style='padding:.85rem 1.3rem;margin:.25rem 0' aria-label='Perfil do participante {animal}'>"
                f"<div style='display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px'>"
                f"<div><span class='animal-badge'>{animal}</span>"
                f"<span style='color:rgba(255,255,255,.45);font-size:.75rem;margin-left:10px'>Acesso: {ts}</span></div>"
                f"<div style='text-align:right;min-width:170px'>"
                f"<span style='color:white;font-weight:700'>{nt} tags</span>"
                f"<span style='color:rgba(255,255,255,.4);font-size:.78rem'> ({nu} unicas)</span>"
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
# ABA 2 — ANÁLISE DE TAGS (Frequência + Temporal + Nuvem de Palavras)
# ═════════════════════════════════════════════════════════════════════
def tab_tags():
    tdf = all_tags()
    if tdf.empty:
        st.info("Nenhuma tag disponivel.")
        return

    st.markdown("### Analise de Tags")
    t1, t2, t3 = st.tabs([" Frequencia e Vocabulario", " Evolucao Temporal", " Nuvem de Palavras"])

    # --- FREQUÊNCIA ---
    with t1:
        freq = tdf['tag'].value_counts().reset_index()
        freq.columns = ['Tag','Frequencia']
        total_usos = freq['Frequencia'].sum()
        freq['% do Total']  = (freq['Frequencia']/total_usos*100).round(2)
        freq['% Acumulada'] = freq['% do Total'].cumsum().round(2)
        freq['Categoria']   = pd.cut(
            freq['Frequencia'],
            bins=[0,1,2,5,10,99999],
            labels=['Hapax (1x)','Rara (2x)','Ocasional (3-5x)','Frequente (6-10x)','Muito Frequente (10+x)']
        )

        hapax  = (freq['Frequencia']==1).sum()
        lei80  = (freq['% Acumulada']<=80).sum()
        ttr    = len(freq)/total_usos if total_usos else 0
        top1p  = freq.iloc[0]['% do Total'] if not freq.empty else 0

        c1,c2,c3,c4 = st.columns(4)
        with c1: st.markdown(kpi("Vocabulario Total",  len(freq), "tags distintas","#a7e6ff"), unsafe_allow_html=True)
        with c2: st.markdown(kpi("Hapax Legomena",     hapax,     f"{hapax/len(freq):.0%} do vocab.","#f9a8d4"), unsafe_allow_html=True)
        with c3: st.markdown(kpi("80% dos Usos",       f"{lei80} tags","lei de Zipf","#6ee7b7"), unsafe_allow_html=True)
        with c4: st.markdown(kpi("Type-Token Ratio",   f"{ttr:.3f}","riqueza global","#fcd34d"), unsafe_allow_html=True)

        st.markdown(insight(
            f"<strong>Distribuicao de Zipf:</strong> As {lei80} tags mais frequentes cobrem 80% de todos os usos. "
            f"Existem {hapax} hapax legomena — termos usados somente uma vez "
            f"({hapax/len(freq):.0%} do vocabulario total). "
            f"TTR global de <strong>{ttr:.3f}</strong> indica "
            f"{'alta' if ttr>0.5 else 'moderada' if ttr>0.25 else 'baixa'} diversidade lexical."
        ), unsafe_allow_html=True)

        st.markdown(divider(), unsafe_allow_html=True)
        st.markdown("#### Frequencia - Top 25 Tags")
        st.bar_chart(tdf['tag'].value_counts().head(25))

        st.markdown("#### Tabela Completa de Frequencias")
        cat_opts = list(freq['Categoria'].cat.categories)
        cat_sel  = st.multiselect("Filtrar por categoria:", cat_opts, default=cat_opts, key="fc")
        disp = freq[freq['Categoria'].isin(cat_sel)] if cat_sel else freq
        st.dataframe(disp, use_container_width=True, hide_index=True)

        c1, c2 = st.columns(2)
        with c1:
            st.download_button(
                "Frequencias (CSV)",
                freq.to_csv(index=False).encode('utf-8'),
                f"frequencias_{datetime.now().strftime('%Y%m%d')}.csv",
                "text/csv", use_container_width=True)
        with c2:
            st.markdown("**Distribuicao por Categoria:**")
            cd = freq['Categoria'].value_counts().reset_index()
            cd.columns = ['Categoria','Qtd']
            st.dataframe(cd, use_container_width=True, hide_index=True)

    # --- TEMPORAL ---
    with t2:
        st.markdown("#### Evolucao Temporal das Tags")
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

            # --- KPIs temporais ---
            dias_ativos = tf['date'].nunique()
            media_dia   = len(tf)/dias_ativos if dias_ativos else 0
            pico_dia    = tf.groupby('date').size()
            pico_val    = int(pico_dia.max()) if not pico_dia.empty else 0
            pico_dt     = str(pico_dia.idxmax()) if not pico_dia.empty else "—"

            c1,c2,c3,c4 = st.columns(4)
            with c1: st.markdown(kpi("Dias com Atividade", dias_ativos,"dias","#a7e6ff"), unsafe_allow_html=True)
            with c2: st.markdown(kpi("Media por Dia",      f"{media_dia:.1f}","tags/dia","#6ee7b7"), unsafe_allow_html=True)
            with c3: st.markdown(kpi("Pico de Tags",       pico_val,f"em {pico_dt}","#fcd34d"), unsafe_allow_html=True)
            with c4: st.markdown(kpi("Periodo Total",      f"{dias_ativos} dias","registrado","#d1baff"), unsafe_allow_html=True)

            st.markdown(divider(), unsafe_allow_html=True)

            # --- Linha: tags por dia ---
            daily = tf.groupby('date').agg(
                Tags=('tag','count'),
                Tags_Unicas=('tag','nunique'),
                Usuarios=('user_id','nunique')
            ).reset_index().rename(columns={'date':'Data'})

            st.markdown("#### Tags Criadas por Dia")
            st.line_chart(daily.set_index('Data')['Tags'])

            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Usuarios ativos por dia**")
                st.line_chart(daily.set_index('Data')['Usuarios'])
            with c2:
                st.markdown("**Tags unicas por dia**")
                st.line_chart(daily.set_index('Data')['Tags_Unicas'])

            st.markdown(divider(), unsafe_allow_html=True)

            # --- Por mes ---
            st.markdown("#### Distribuicao Mensal")
            meses_pt = {1:"Jan",2:"Fev",3:"Mar",4:"Abr",5:"Mai",6:"Jun",
                        7:"Jul",8:"Ago",9:"Set",10:"Out",11:"Nov",12:"Dez"}
            monthly = tf.groupby(['ano','mes']).agg(
                Tags=('tag','count'),
                Tags_Unicas=('tag','nunique'),
                Usuarios=('user_id','nunique')
            ).reset_index()
            monthly['Mes/Ano'] = monthly['mes'].map(meses_pt)+"/"+monthly['ano'].astype(str)
            monthly = monthly.sort_values(['ano','mes'])

            st.bar_chart(monthly.set_index('Mes/Ano')['Tags'])

            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Usuarios unicos por mes**")
                st.bar_chart(monthly.set_index('Mes/Ano')['Usuarios'])
            with c2:
                st.markdown("**Tags unicas por mes**")
                st.bar_chart(monthly.set_index('Mes/Ano')['Tags_Unicas'])

            st.markdown(divider(), unsafe_allow_html=True)

            # --- Por ano ---
            st.markdown("#### Distribuicao Anual")
            yearly = tf.groupby('ano').agg(
                Tags=('tag','count'),
                Tags_Unicas=('tag','nunique'),
                Usuarios=('user_id','nunique')
            ).reset_index().rename(columns={'ano':'Ano'})
            st.bar_chart(yearly.set_index('Ano')['Tags'])
            st.dataframe(yearly, use_container_width=True, hide_index=True)

            st.markdown(divider(), unsafe_allow_html=True)

            # --- Distribuicao por dia da semana e hora ---
            st.markdown("#### Padroes de Uso")
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Distribuicao por Hora do Dia**")
                st.bar_chart(tf['hora'].value_counts().sort_index().rename("Tags"))
            with c2:
                st.markdown("**Distribuicao por Dia da Semana**")
                dow_order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
                dow_pt    = {"Monday":"Seg","Tuesday":"Ter","Wednesday":"Qua","Thursday":"Qui",
                             "Friday":"Sex","Saturday":"Sab","Sunday":"Dom"}
                dow_c = tf['dow'].value_counts().reindex(dow_order,fill_value=0)
                dow_c.index = [dow_pt.get(d,d) for d in dow_c.index]
                st.bar_chart(dow_c.rename("Tags"))

            st.markdown(divider(), unsafe_allow_html=True)

            # --- Tabela consolidada ---
            st.markdown("#### Tabela Detalhada por Dia")
            daily_full = tf.groupby('date').agg(
                Total=('tag','count'),
                Unicas=('tag','nunique'),
                Usuarios=('user_id','nunique'),
                Tag_Mais_Usada=('tag', lambda x: x.value_counts().index[0])
            ).reset_index()
            daily_full.columns = ['Data','Tags Criadas','Tags Unicas','Usuarios Ativos','Tag Mais Usada']
            daily_full = daily_full.sort_values('Data',ascending=False)
            st.dataframe(daily_full, use_container_width=True, hide_index=True)

            st.markdown("#### Tabela Mensal Consolidada")
            monthly_full = monthly[['Mes/Ano','Tags','Tags_Unicas','Usuarios']].copy()
            monthly_full.columns = ['Mes/Ano','Tags Criadas','Tags Unicas','Usuarios Ativos']
            st.dataframe(monthly_full, use_container_width=True, hide_index=True)

            if len(daily)>1:
                st.markdown(insight(
                    f"<strong>Tendencia:</strong> Pico de <strong>{pico_val} tags</strong> em {pico_dt}. "
                    f"Media de <strong>{media_dia:.1f} tags/dia</strong> nos {dias_ativos} dias com atividade. "
                    f"Total de {len(tf)} tags distribuidas ao longo de "
                    f"{monthly['ano'].nunique()} ano(s) e {len(monthly)} mes(es) registrado(s)."
                ), unsafe_allow_html=True)

        except Exception as e:
            st.info(f"Dados insuficientes para analise temporal.")

    # --- NUVEM DE PALAVRAS ---
    with t3:
        st.markdown("#### Nuvem de Palavras das Tags")
        if not tdf.empty:
            text = " ".join(tdf['tag'].tolist())

            # Remover caracteres especiais e números, manter apenas letras e espaços
            cleaned_text = re.sub(r'[^a-zA-Z\s]', '', text)

            # Definir stop words em português (pode ser expandido)
            stopwords_pt = set([
                "de", "a", "o", "que", "e", "do", "da", "em", "um", "para", "com", "nao", "uma", "os", "no", "se", "na", "por", "mais", "as", "dos", "das", "como", "mas", "ao", "ele", "das", "eu", "meu", "sua", "ou", "ser", "quando", "muito", "ha", "nos", "ja", "tambem", "so", "pelo", "pela", "ate", "isso", "ela", "entre", "depois", "sem", "mesmo", "aos", "ter", "seus", "quem", "nas", "me", "esse", "eles", "voce", "essa", "num", "nem", "suas", "ja", "foi", "sao", "era", "sobre", "onde", "estas", "este", "isto", "la", "deles", "delas", "fui", "foram", "fomos", "serei", "sera", "seremos", "serao", "fomos", "fosse", "fossem", "sendo", "tendo", "tido", "tinha", "tinham", "tive", "teve", "tiveram", "tivesse", "tivessem", "tenho", "tem", "temos", "tem", "terao", "teremos", "terei", "teria", "teriam", "teriamos", "vez", "vezes", "dia", "dias", "ano", "anos", "mes", "meses", "hora", "horas", "minuto", "minutos", "segundo", "segundos", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc", "etcetera", "etc

