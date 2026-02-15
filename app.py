import streamlit as st
import pandas as pd
import requests
import io
import unicodedata
import re

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Caça Leilão Pro", layout="wide", page_icon="💎")

# --- CSS (DESIGN PROFISSIONAL ARREMATA) ---
st.markdown("""
<style>
    .stApp { background-color: #f8fafc; font-family: 'Segoe UI', Roboto, sans-serif; }
    .card-container { display: grid; grid-template-columns: repeat(auto-fill, minmax(360px, 1fr)); gap: 20px; padding: 20px; }
    .imovel-card { background: white; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); border: 1px solid #e2e8f0; overflow: hidden; display: flex; flex-direction: column; justify-content: space-between; position: relative; transition: transform 0.2s; }
    .imovel-card:hover { transform: translateY(-5px); box-shadow: 0 20px 25px -5px rgba(0,0,0,0.1); border-color: #2563eb; }
    .header-dark { background: #1e293b; color: white; padding: 10px 15px; display: flex; justify-content: space-between; align-items: center; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; }
    .badge-discount { background-color: #ef4444; color: white; padding: 3px 8px; border-radius: 4px; font-weight: 800; }
    .card-body { padding: 18px; color: #334155; }
    .meta-top { font-size: 0.75rem; color: #64748b; font-weight: 700; text-transform: uppercase; margin-bottom: 5px; }
    .card-title { font-size: 1.1rem; font-weight: 800; color: #0f172a; margin-bottom: 8px; line-height: 1.3; height: 44px; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; }
    
    /* Linha de Medidas Detalhada */
    .features-row { display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 12px; font-size: 0.8rem; color: #475569; font-weight: 600; border-bottom: 1px solid #f1f5f9; padding-bottom: 10px; }
    .feat-item { display: flex; align-items: center; gap: 4px; }
    
    .date-row { display: flex; align-items: center; gap: 6px; font-size: 0.85rem; color: #1e293b; font-weight: 700; margin-bottom: 10px; }
    .price-section { background: #f8fafc; padding: 10px; border-radius: 8px; margin-top: 5px; border: 1px solid #e2e8f0; }
    .price-label { font-size: 0.7rem; color: #64748b; text-transform: uppercase; font-weight: bold; }
    .price-val { font-size: 1.4rem; color: #1e293b; font-weight: 900; }
    .price-old { font-size: 0.8rem; color: #94a3b8; text-decoration: line-through; }
    .btn-action { background: #2563eb; color: white !important; text-align: center; padding: 12px; font-weight: 700; text-transform: uppercase; text-decoration: none; font-size: 0.9rem; transition: background 0.2s; }
    .btn-action:hover { background: #1d4ed8; }
    .status-badge { position: absolute; top: 45px; right: 15px; font-size: 0.7rem; padding: 4px 10px; border-radius: 20px; font-weight: 800; box-shadow: 0 2px 5px rgba(0,0,0,0.1); text-transform: uppercase; }
    .st-ocupado { background: #fef2f2; color: #991b1b; border: 1px solid #fecaca; }
    .st-livre { background: #f0fdf4; color: #166534; border: 1px solid #bbf7d0; }
</style>
""", unsafe_allow_html=True)

# --- FUNÇÕES ---
def limpar_texto(t):
    if not isinstance(t, str): return str(t)
    return ''.join(c for c in unicodedata.normalize('NFD', t) if unicodedata.category(c) != 'Mn').lower().strip()

def inicio_tabela(txt):
    for i, l in enumerate(txt.split('\n')):
        if 'Bairro' in l and ('Valor' in l or 'Preço' in l or 'Venda' in l): return i
    return 0

# --- NOVO EXTRATOR DE MEDIDAS (RESOLVE O PROBLEMA DO 0 OU -) ---
def extrair_medidas_caixa(row):
    full_text = ' '.join(row.astype(str)).lower()
    
    # 1. Busca Área Privativa/Construída
    area_c = re.search(r'(area\s+privativa|area\s+construida|area\s+real)\s*=?\s*([\d,.]+)', full_text)
    # 2. Busca Área do Terreno
    area_t = re.search(r'(area\s+do\s+terreno|area\s+total)\s*=?\s*([\d,.]+)', full_text)
    # 3. Busca Quartos e Vagas
    qtos = re.search(r'(\d+)\s*(quarto|qto|dorm)', full_text)
    vagas = re.search(r'(\d+)\s*(vaga|garagem|vg)', full_text)
    
    res = {
        'cons': area_c.group(2).replace(',', '.') if area_c else "0",
        'terr': area_t.group(2).replace(',', '.') if area_t else "0",
        'qtos': qtos.group(1) if qtos else "0",
        'vagas': vagas.group(1) if vagas else "0"
    }
    return res

@st.cache_data(ttl=3600)
def carregar_dados(uf):
    url = f"https://venda-imoveis.caixa.gov.br/listaweb/Lista_imoveis_{uf}.csv"
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        if r.status_code != 200: return None, f"Erro {r.status_code}"
        txt = r.content.decode('latin1')
        pular = inicio_tabela(txt)
        df = pd.read_csv(io.StringIO(txt), sep=';', skiprows=pular, on_bad_lines='skip')
        cols = {c: limpar_texto(c) for c in df.columns}
        df.rename(columns=cols, inplace=True)
        
        col_preco = next((c for c in df.columns if 'preco' in c or 'venda' in c and 'modalidade' not in c), None)
        if not col_preco: return None, "Erro colunas"
        
        def valor(v):
            if isinstance(v, str): return float(v.replace('R$','').replace(' ','').replace('.','').replace(',','.'))
            return float(v)
            
        df['Venda'] = df[col_preco].apply(valor)
        col_aval = next((c for c in df.columns if 'avaliacao' in c), None)
        df['Avaliacao'] = df[col_aval].apply(valor) if col_aval else df['Venda']
        df = df[df['Avaliacao'] > 0]
        
        # Inteligência
        df['Tipo'] = df.apply(lambda x: 'APARTAMENTO' if 'apartamento' in ' '.join(x.astype(str)).lower() else ('CASA' if 'casa' in ' '.join(x.astype(str)).lower() else ('TERRENO' if 'terreno' in ' '.join(x.astype(str)).lower() else 'IMÓVEL')), axis=1)
        df['Sit'] = df.apply(lambda x: 'Ocupado' if 'ocupado' in ' '.join(x.astype(str)).lower() and 'desocupado' not in ' '.join(x.astype(str)).lower() else ('Desocupado' if 'desocupado' in ' '.join(x.astype(str)).lower() else 'Indefinido'), axis=1)
        
        # --- APLICA O SUPER EXTRATOR ---
        medidas = df.apply(extrair_medidas_caixa, axis=1
