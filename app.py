import streamlit as st
import pandas as pd
import requests
import io
import unicodedata
import re
import urllib.parse

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Caça Leilão Pro", layout="wide", page_icon="💎")

# --- CSS (DESIGN MAPS + ANALYTICS) ---
st.markdown("""
<style>
    .stApp { background-color: #f1f5f9; font-family: 'Segoe UI', Roboto, sans-serif; }
    .card-container { display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 20px; padding: 20px; }
    .imovel-card { background: white; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); border: 1px solid #cbd5e1; overflow: hidden; display: flex; flex-direction: column; justify-content: space-between; position: relative; transition: transform 0.2s; }
    .imovel-card:hover { transform: translateY(-5px); box-shadow: 0 20px 25px -5px rgba(0,0,0,0.1); border-color: #3b82f6; }
    .header-dark { background: #0f172a; color: white; padding: 12px 15px; display: flex; justify-content: space-between; align-items: center; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; }
    .badge-discount { background-color: #dc2626; color: white; padding: 3px 8px; border-radius: 4px; font-weight: 800; }
    .card-body { padding: 18px; color: #334155; }
    .meta-top { font-size: 0.75rem; color: #64748b; font-weight: 700; text-transform: uppercase; margin-bottom: 5px; }
    .card-title { font-size: 1.1rem; font-weight: 800; color: #0f172a; margin-bottom: 8px; line-height: 1.3; height: 44px; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; }
    .features-row { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; font-size: 0.8rem; color: #475569; font-weight: 600; border-bottom: 1px solid #e2e8f0; padding-bottom: 10px; }
    .price-section { background: #f8fafc; padding: 10px; border-radius: 8px; margin-top: 5px; border: 1px solid #e2e8f0; display: flex; justify-content: space-between; align-items: center; }
    .price-block { text-align: left; }
    .price-label { font-size: 0.65rem; color: #64748b; text-transform: uppercase; font-weight: bold; }
    .price-val { font-size: 1.3rem; color: #1e293b; font-weight: 900; }
    .price-old { font-size: 0.75rem; color: #94a3b8; text-decoration: line-through; }
    .analytics-row { display: flex; gap: 10px; margin-top: 8px; font-size: 0.75rem; font-weight: bold; color: #059669; background: #ecfdf5; padding: 6px; border-radius: 6px; }
    
    /* Botões de Mapa */
    .map-actions { display: flex; gap: 5px; margin-top: 10px; }
    .btn-map { flex: 1; text-align: center; padding: 6px; border-radius: 6px; font-size: 0.75rem; font-weight: bold; text-decoration: none; color: white; transition: opacity 0.2s; }
    .btn-google { background-color: #4285F4; }
    .btn-waze { background-color: #33ccff; color: black; }
    
    .btn-action { background: #2563eb; color: white !important; text-align: center; padding: 12px; font-weight: 700; text-transform: uppercase; text-decoration: none; font-size: 0.9rem; margin-top: 10px; display: block; }
    .btn-action:hover { background: #1d4ed8; }
    .status-badge { position: absolute; top: 45px; right: 15px; font-size: 0.7rem; padding: 3px 8px; border-radius: 20px; font-weight: 800; text-transform: uppercase; z-index: 10; border: 1px solid #bbf7d0; background: #f0fdf4; color: #166534; }
    .st-ocupado { background: #fef2f2; color: #991b1b; border-color: #fecaca; }
</style>
""", unsafe_allow_html=True)

# --- FUNÇÕES ---
def limpar_texto(t):
    if not isinstance(t, str): return str(t)
    return ''.join(c for c in unicodedata.normalize('NFD', t) if unicodedata.category(c) != 'Mn').lower().strip()

def inicio_tabela(txt):
    linhas = txt.split('\n')
    for i, l in enumerate(linhas):
        if 'Bairro' in l and ('Valor' in l or 'Preço' in l or 'Venda' in l): return i
    return 0

def extrair_medidas(row):
    texto = ' '.join(row.astype(str)).lower()
    q = re.search(r'(\d+)\s*(quarto|qto|dorm)', texto)
    v = re.search(r'(\d+)\s*(vaga|garagem|vg)', texto)
    ac = re.search(r'(privativa|construida|util|real)\s*[:=]?\s*([\d,.]+)', texto)
    at = re.search(r'(terreno|total|averbada)\s*[:=]?\s*([\d,.]+)', texto)
    
    def limpa(match):
        if not match: return 0.0
        try: return float(match.group(2).replace('.', '').replace(',', '.'))
        except: return 0.0

    return {
        'qtos': q.group(1) if q else "0",
        'vagas': v.group(1) if v else "0",
        'cons': limpa(ac),
        'terr': limpa(at)
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
        
        col_v = next((c for c in df.columns if 'preco' in c or 'venda' in c and 'modalidade' not in c), None)
        def conv(v):
            try: return float(str(v).replace('R$','').replace(' ','').replace('.','').replace(',','.'))
            except: return 0.0
        df['Venda'] = df[col_v].apply(conv)
        col_a = next((c for c in df.columns if 'avaliacao' in c), None)
        df['Avaliacao'] = df[col_a].apply(conv) if col_a else df['Venda']
        df = df[df['Avaliacao'] > 0].copy()
        
        # Processamento
        df['Full'] = df.apply(lambda x: ' '.join(x.astype(str)).lower(), axis=1)
        df['Tipo'] = df['Full'].apply(lambda x: 'APARTAMENTO' if 'apartamento' in x else ('CASA' if 'casa' in x else ('TERRENO' if 'terreno' in x else 'IMÓVEL')))
        df['Sit'] = df['Full'].apply(lambda x: 'Ocupado' if 'ocupado' in x and 'desocupado' not in x else ('Desocupado' if 'desocupado' in x else 'Indefinido'))
        
        m = df.apply(extrair_medidas, axis=1)
        df['Qtos'] = [x['qtos'] for x in m]
        df['Vagas'] = [x['vagas'] for x in m]
        df['Area_C'] = [x['cons'] for x in m]
        df['Area_T'] = [x['terr'] for x in m]

        col_m = next((c for c in df.columns if 'modalidade' in c), None)
        df['Mod'] = df[col_m].astype(str).str.upper() if col_m else "ONLINE"
        
        return df, "Ok"
    except Exception as e: return None, str(e)

# --- APP ---
st.title("💎 Arremata Clone 3.9 (Maps + Analytics)")
with st.sidebar:
    st.header("Filtros")
    uf = st.selectbox("Estado", ["SP", "RJ", "MG", "PR", "SC", "RS", "BA", "GO", "DF"])
    if st.button("🔄 Atualizar"): st.cache_data.clear()
    df, msg = carregar_dados(uf)
    if df is not None:
        col_c = next((c for c in df.columns if 'cidade' in c), df.columns[0])
        sel_c = st.selectbox("Cidade", ["Todas"] + sorted(df[col_c].dropna().unique().tolist()))
        max_p = st.number_input("Preço Máximo", 0)
        min_d = st.slider("Desconto % Mínimo", 0, 95, 40)
    else: st.error(msg)

if df is not None:
    f = df.copy()
    if sel_c != "Todas": f = f[f[col_c] == sel_c]
    if max_p > 0: f = f[f['Venda'] <= max_p]
    
    f['Desc'] = ((f['Avaliacao'] - f['Venda']) / f['Avaliacao']) * 100
    f = f[f['Desc'] >= min_d].sort_values('Desc', ascending=False)
    
    st.info(f"Encontrados: {len(f)} imóveis")
    html_out = "<div class='card-container'>"
    base_cx = "https://venda-imoveis.caixa.gov.br/sistema/detalhe-imovel.asp?hdnimovel="
    col_id = next((c for c in df.columns if 'numero' in c and 'imovel' in c), df.columns[0])
    col_end = next((c for c in df.columns if 'endereco' in c), '')
    col_b = next((c for c in df.columns if 'bairro' in c), '')

    for _, r in f.head(50).iterrows():
        # Lógica de Mapas
        endereco_completo = f"{r[col_end]}, {r[col_b]}, {r[col_c]}".replace(" ", "+")
        link_google = f"https://www.google.com/maps/search/?api=1&query={endereco_completo}"
        link_waze = f"https://waze.com/ul?q={endereco_completo}"
        
        # Lógica de Analytics
        lucro_bruto = r['Avaliacao'] - r['Venda']
        preco_m2 = 0
        if r['Area_C'] > 0: preco_m2 = r['Venda'] / r['Area_C']
        elif r['Area_T'] > 0: preco_m2 = r['Venda'] / r['Area_T']
        
        txt_m2 = f"R$ {preco_m2:,.0f}/m²" if preco_m2 > 0 else "-"
        
        # Medidas Visuais
        feats = []
        if r['Qtos'] != "0": feats.append(f"🛏️ {r['Qtos']}")
        if r['Area_C'] > 0: feats.append(f"🏠 {r['Area_C']:.0f}m²")
        if r['Area_T'] > 0: feats.append(f"🌳 {r['Area_T']:.0f}m²")
        feats_html = " | ".join(feats) if feats else "⚠️ Ver Edital"

        status_class = 'st-ocupado' if r['Sit'] == 'Ocupado' else 'st-livre'
        
        html_out += f"""
<div class='imovel-card'>
    <div class='header-dark'>
        <span>{r['Mod'][:20]}</span>
        <span class='badge-discount'>-{r['Desc']:.0f}%</span>
    </div>
    <div class='status-badge {status_class}'>{r['Sit']}</div>
    
    <div class='card-body'>
        <div class='meta-top'>{r['Tipo']} • {r[col_c]}</div>
        <div class='card-title'>{r[col_b]}</div>
        <div class='features-row'>{feats_html}</div>
        
        <div class='analytics-row'>
            <span>💰 Lucro: R$ {lucro_bruto:,.0f}</span>
            <span style='margin-left:auto'>📐 {txt_m2}</span>
        </div>

        <div class='map-actions'>
            <a href='{link_google}' target='_blank' class='btn-map btn-google'>📍 Google Maps</a>
            <a href='{link_waze}' target='_blank' class='btn-map btn-waze'>🚙 Waze</a>
        </div>

        <div class='price-section'>
            <div class='price-block'>
                <div class='price-old'>Avaliação: R$ {r['Avaliacao']:,.0f}</div>
                <div class='price-val'>R$ {r['Venda']:,.0f}</div>
            </div>
        </div>
    </div>
    <a href='{base_cx + str(r[col_id])}' target='_blank' class='btn-action'>VER NA CAIXA</a>
</div>"""
    
    st.markdown(html_out + "</div>", unsafe_allow_html=True)
