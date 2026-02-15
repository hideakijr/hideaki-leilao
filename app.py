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
    .card-container { display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 20px; padding: 20px; }
    .imovel-card { background: white; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); border: 1px solid #e2e8f0; overflow: hidden; display: flex; flex-direction: column; justify-content: space-between; position: relative; transition: transform 0.2s; }
    .imovel-card:hover { transform: translateY(-5px); box-shadow: 0 20px 25px -5px rgba(0,0,0,0.1); border-color: #2563eb; }
    .header-dark { background: #1e293b; color: white; padding: 10px 15px; display: flex; justify-content: space-between; align-items: center; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; }
    .badge-discount { background-color: #ef4444; color: white; padding: 3px 8px; border-radius: 4px; font-weight: 800; }
    .card-body { padding: 18px; color: #334155; }
    .meta-top { font-size: 0.75rem; color: #64748b; font-weight: 700; text-transform: uppercase; margin-bottom: 5px; }
    .card-title { font-size: 1.1rem; font-weight: 800; color: #0f172a; margin-bottom: 8px; line-height: 1.3; height: 44px; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; }
    .features-row { display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 12px; font-size: 0.8rem; color: #475569; font-weight: 600; border-bottom: 1px solid #f1f5f9; padding-bottom: 10px; }
    .price-section { background: #f8fafc; padding: 10px; border-radius: 8px; margin-top: 5px; border: 1px solid #e2e8f0; }
    .price-val { font-size: 1.4rem; color: #1e293b; font-weight: 900; }
    .price-old { font-size: 0.8rem; color: #94a3b8; text-decoration: line-through; }
    .btn-action { background: #2563eb; color: white !important; text-align: center; padding: 12px; font-weight: 700; text-transform: uppercase; text-decoration: none; font-size: 0.9rem; transition: background 0.2s; }
    .btn-action:hover { background: #1d4ed8; }
    .status-badge { position: absolute; top: 45px; right: 15px; font-size: 0.7rem; padding: 4px 10px; border-radius: 20px; font-weight: 800; text-transform: uppercase; }
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

def extrair_medidas_caixa(row):
    full_text = ' '.join(row.astype(str)).lower()
    
    # Busca por padrões de texto para áreas, quartos e vagas
    area_c = re.search(r'(area\s+privativa|area\s+construida|area\s+real)\s*[:=]?\s*([\d,.]+)', full_text)
    area_t = re.search(r'(area\s+do\s+terreno|area\s+total|area\s+averbada)\s*[:=]?\s*([\d,.]+)', full_text)
    qtos = re.search(r'(\d+)\s*(quarto|qto|dorm)', full_text)
    vagas = re.search(r'(\d+)\s*(vaga|garagem|vg)', full_text)
    
    def formata_area(match):
        if not match: return "0"
        num = match.group(2).replace('.', '').replace(',', '.')
        try: return str(int(float(num)))
        except: return "0"

    return {
        'cons': formata_area(area_c),
        'terr': formata_area(area_t),
        'qtos': qtos.group(1) if qtos else "0",
        'vagas': vagas.group(1) if vagas else "0"
    }

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
        
        # Inteligência e Extração
        df['Tipo'] = df.apply(lambda x: 'APARTAMENTO' if 'apartamento' in ' '.join(x.astype(str)).lower() else ('CASA' if 'casa' in ' '.join(x.astype(str)).lower() else ('TERRENO' if 'terreno' in ' '.join(x.astype(str)).lower() else 'IMÓVEL')), axis=1)
        df['Sit'] = df.apply(lambda x: 'Ocupado' if 'ocupado' in ' '.join(x.astype(str)).lower() and 'desocupado' not in ' '.join(x.astype(str)).lower() else ('Desocupado' if 'desocupado' in ' '.join(x.astype(str)).lower() else 'Indefinido'), axis=1)
        
        # Aplicação segura do extrator
        medidas_list = df.apply(extrair_medidas_caixa, axis=1)
        df['Qtos'] = [m['qtos'] for m in medidas_list]
        df['Vagas'] = [m['vagas'] for m in medidas_list]
        df['Area_C'] = [m['cons'] for m in medidas_list]
        df['Area_T'] = [m['terr'] for m in medidas_list]

        col_mod = next((c for c in df.columns if 'modalidade' in c), None)
        df['Mod'] = df[col_mod].astype(str).str.upper() if col_mod else "ONLINE"
        
        return df, "Ok"
    except Exception as e: return None, str(e)

# --- INTERFACE ---
st.title("💎 Arremata Clone 3.6")
with st.sidebar:
    st.header("Painel de Controle")
    uf = st.selectbox("Estado", ["SP", "RJ", "MG", "PR", "SC", "RS", "BA", "GO", "DF"])
    if st.button("🔄 Atualizar"): st.cache_data.clear()
    df, msg = carregar_dados(uf)
    if df is not None:
        col_cid = next((c for c in df.columns if 'cidade' in c), df.columns[0])
        sel_cid = st.selectbox("Cidade", ["Todas"] + sorted(df[col_cid].dropna().unique().tolist()))
        sel_tipo = st.selectbox("Tipo", ["Todas"] + sorted(df['Tipo'].unique().tolist()))
        max_v = st.number_input("Preço Máximo", 0)
        desc_min = st.slider("Desconto %", 0, 95, 40)
    else: st.error(msg)

# --- CARDS ---
if df is not None:
    f = df.copy()
    if sel_cid != "Todas": f = f[f[col_cid] == sel_cid]
    if sel_tipo != "Todas": f = f[f['Tipo'] == sel_tipo]
    if max_v > 0: f = f[f['Venda'] <= max_v]
    f['Desc'] = ((f['Avaliacao'] - f['Venda']) / f['Avaliacao']) * 100
    f = f[f['Desc'] >= desc_min].sort_values('Desc', ascending=False)
    
    st.info(f"Encontrados: {len(f)} imóveis")
    html = "<div class='card-container'>"
    base = "https://venda-imoveis.caixa.gov.br/sistema/detalhe-imovel.asp?hdnimovel="
    col_id = next((c for c in df.columns if 'numero' in c and 'imovel' in c), df.columns[0])
    col_bair = next((c for c in df.columns if 'bairro' in c), '')
    col_end = next((c for c in df.columns if 'endereco' in c), '')

    for _, r in f.head(50).iterrows():
        icon = "🏠" if r['Tipo'] == 'CASA' else "🏢" if r['Tipo'] == 'APARTAMENTO' else "🌳"
        status_tag = f"<div class='status-badge {'st-ocupado' if r['Sit']=='Ocupado' else 'st-livre'}'>{r['Sit']}</div>"
        
        # Medidas formatadas para o card
        med_c = f"📏 C: {r['Area_C']}m²" if r['Area_C'] != "0" else ""
        med_t = f"🌳 T: {r['Area_T']}m²" if r['Area_T'] != "0" else ""
        feats = f"🛏️ {r['Qtos']} qtos | {med_c} | {med_t} | 🚗 {r['Vagas']} vg"

        html += f"""
<div class='imovel-card'>
<div class='header-dark'><span>{r['Mod'][:25]}</span><span class='badge-discount'>-{r['Desc']:.0f}%</span></div>
{status_tag}
<div class='card-body'>
<div class='meta-top'>{icon} {r['Tipo']} • {r[col_cid]}</div>
<div class='card-title'>{r[col_bair]}</div>
<div class='features-row'>{feats}</div>
<div class='price-section'>
<div class='price-label'>Lance Inicial</div>
<div class='price-val'>R$ {r['Venda']:,.2f}</div>
<div class='price-old'>Avaliação: R$ {r['Avaliacao']:,.2f}</div>
</div>
</div>
<a href='{base + str(r[col_id])}' target='_blank' class='btn-action'>VER MATRÍCULA E EDITAL</a>
</div>"""
    st.markdown(html + "</div>", unsafe_allow_
