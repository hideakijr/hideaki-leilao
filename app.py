import streamlit as st
import pandas as pd
import requests
import io
import unicodedata
import re

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Caça Leilão Pro", layout="wide", page_icon="💎")

# --- CSS (DESIGN ARREMATA REVISADO) ---
st.markdown("""
<style>
    .stApp { background-color: #f8fafc; font-family: 'Segoe UI', Roboto, sans-serif; }
    .card-container { display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 20px; padding: 20px; }
    .imovel-card { background: white; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); border: 1px solid #e2e8f0; overflow: hidden; display: flex; flex-direction: column; justify-content: space-between; position: relative; }
    .header-dark { background: #1e293b; color: white; padding: 10px 15px; display: flex; justify-content: space-between; align-items: center; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; }
    .badge-discount { background-color: #ef4444; color: white; padding: 3px 8px; border-radius: 4px; font-weight: 800; }
    .card-body { padding: 18px; color: #334155; }
    .meta-top { font-size: 0.75rem; color: #64748b; font-weight: 700; text-transform: uppercase; margin-bottom: 5px; }
    .card-title { font-size: 1.1rem; font-weight: 800; color: #0f172a; margin-bottom: 8px; line-height: 1.3; height: 44px; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; }
    .features-row { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; font-size: 0.8rem; color: #475569; font-weight: 600; border-bottom: 1px solid #f1f5f9; padding-bottom: 10px; align-items: center; }
    .price-section { background: #f8fafc; padding: 10px; border-radius: 8px; margin-top: 5px; border: 1px solid #e2e8f0; }
    .price-val { font-size: 1.4rem; color: #1e293b; font-weight: 900; }
    .price-old { font-size: 0.8rem; color: #94a3b8; text-decoration: line-through; }
    .btn-action { background: #2563eb; color: white !important; text-align: center; padding: 12px; font-weight: 700; text-transform: uppercase; text-decoration: none; font-size: 0.9rem; transition: background 0.2s; }
    .btn-action:hover { background: #1d4ed8; }
    .status-badge { position: absolute; top: 42px; right: 12px; font-size: 0.65rem; padding: 3px 8px; border-radius: 20px; font-weight: 800; text-transform: uppercase; z-index: 10; border: 1px solid #bbf7d0; background: #f0fdf4; color: #166534; }
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

def extrair_medidas_ninja(row):
    # Pega todo o texto disponível na linha para não perder nada
    texto_bruto = ' '.join(row.astype(str)).lower()
    
    # Busca por Quartos
    q = re.search(r'(\d+)\s*(quarto|qto|dorm)', texto_bruto)
    # Busca por Vagas
    v = re.search(r'(\d+)\s*(vaga|garagem|vg)', texto_bruto)
    # Busca por Áreas (Privativa ou Total)
    a_c = re.search(r'(privativa|construida|util|real)\s*[:=]?\s*([\d,.]+)', texto_bruto)
    a_t = re.search(r'(terreno|total|averbada)\s*[:=]?\s*([\d,.]+)', texto_bruto)
    
    def limpa_num(match, group_idx=2):
        if not match: return "0"
        num = match.group(group_idx).replace('.', '').replace(',', '.')
        try: return str(int(float(num)))
        except: return "0"

    return {
        'qtos': q.group(1) if q else "0",
        'vagas': v.group(1) if v else "0",
        'cons': limpa_num(a_c),
        'terr': limpa_num(a_t)
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
        
        # Filtros de Valor
        col_v = next((c for c in df.columns if 'preco' in c or 'venda' in c and 'modalidade' not in c), None)
        def conv_v(v):
            try: return float(str(v).replace('R$','').replace(' ','').replace('.','').replace(',','.'))
            except: return 0.0
            
        df['Venda'] = df[col_v].apply(conv_v)
        col_a = next((c for c in df.columns if 'avaliacao' in c), None)
        df['Avaliacao'] = df[col_a].apply(conv_v) if col_a else df['Venda']
        df = df[df['Avaliacao'] > 0].copy()
        
        # Inteligência
        df['Full'] = df.apply(lambda x: ' '.join(x.astype(str)).lower(), axis=1)
        df['Tipo'] = df['Full'].apply(lambda x: 'APARTAMENTO' if 'apartamento' in x else ('CASA' if 'casa' in x else ('TERRENO' if 'terreno' in x else 'IMÓVEL')))
        df['Sit'] = df['Full'].apply(lambda x: 'Ocupado' if 'ocupado' in x and 'desocupado' not in x else ('Desocupado' if 'desocupado' in x else 'Indefinido'))
        
        # Extração Ninja
        medidas = df.apply(extrair_medidas_ninja, axis=1)
        df['Qtos'] = [m['qtos'] for m in medidas]
        df['Vagas'] = [m['vagas'] for m in medidas]
        df['Area_C'] = [m['cons'] for m in medidas]
        df['Area_T'] = [m['terr'] for m in medidas]

        col_m = next((c for c in df.columns if 'modalidade' in c), None)
        df['Mod'] = df[col_m].astype(str).str.upper() if col_m else "ONLINE"
        
        return df, "Ok"
    except Exception as e: return None, str(e)

# --- INTERFACE ---
st.title("💎 Arremata Clone 3.8")
with st.sidebar:
    st.header("Painel de Controle")
    uf = st.selectbox("Estado", ["SP", "RJ", "MG", "PR", "SC", "RS", "BA", "GO", "DF"])
    if st.button("🔄 Atualizar"): st.cache_data.clear()
    df, msg = carregar_dados(uf)
    if df is not None:
        col_c = next((c for c in df.columns if 'cidade' in c), df.columns[0])
        sel_c = st.selectbox("Cidade", ["Todas"] + sorted(df[col_c].dropna().unique().tolist()))
        sel_t = st.selectbox("Tipo", ["Todas"] + sorted(df['Tipo'].unique().tolist()))
        max_p = st.number_input("Preço Máximo", 0)
        min_d = st.slider("Desconto % Mínimo", 0, 95, 40)
    else: st.error(msg)

# --- CARDS ---
if df is not None:
    f = df.copy()
    if sel_c != "Todas": f = f[f[col_c] == sel_c]
    if sel_t != "Todas": f = f[f['Tipo'] == sel_t]
    if max_p > 0: f = f[f['Venda'] <= max_p]
    
    f['Desc'] = ((f['Avaliacao'] - f['Venda']) / f['Avaliacao']) * 100
    f = f[f['Desc'] >= min_d].sort_values('Desc', ascending=False)
    
    st.info(f"Encontrados: {len(f)} imóveis")
    html_out = "<div class='card-container'>"
    base_l = "https://venda-imoveis.caixa.gov.br/sistema/detalhe-imovel.asp?hdnimovel="
    col_id = next((c for c in df.columns if 'numero' in c and 'imovel' in c), df.columns[0])
    col_b = next((c for c in df.columns if 'bairro' in c), 'Bairro')
    
    for _, r in f.head(50).iterrows():
        tipo_i = "🏢" if r['Tipo'] == 'APARTAMENTO' else "🏠" if r['Tipo'] == 'CASA' else "🌳"
        st_css = 'status-badge st-ocupado' if r['Sit'] == 'Ocupado' else 'status-badge'
        
        # Limpeza visual das medidas (só mostra se for maior que zero)
        feat_list = []
        if r['Qtos'] != "0": feat_list.append(f"🛏️ {r['Qtos']} qtos")
        if r['Area_C'] != "0": feat_list.append(f"📏 C: {r['Area_C']}m²")
        if r['Area_T'] != "0": feat_list.append(f"🌳 T: {r['Area_T']}m²")
        if r['Vagas'] != "0": feat_list.append(f"🚗 {r['Vagas']} vg")
        
        # Se estiver tudo zerado, mostra aviso
        feats_html = " | ".join(feat_list) if feat_list else "⚠️ Medidas no Edital"

        html_out += f"""
<div class='imovel-card'>
<div class='header-dark'><span>{r['Mod'][:25]}</span><span class='badge-discount'>-{r['Desc']:.0f}%</span></div>
<div class='{st_css}'>{r['Sit']}</div>
<div class='card-body'>
<div class='meta-top'>{tipo_i} {r['Tipo']} • {r[col_c]}</div>
<div class='card-title'>{r[col_b]}</div>
<div class='features-row'>{feats_html}</div>
<div class='price-section'>
<div class='price-label'>Lance Inicial</div>
<div class='price-val'>R$ {r['Venda']:,.2f}</div>
<div class='price-old'>Avaliação: R$ {r['Avaliacao']:,.2f}</div>
</div>
</div>
<a href='{base_l + str(r[col_id])}' target='_blank' class='btn-action'>VER MATRÍCULA E EDITAL</a>
</div>"""
    
    st.markdown(html_out + "</div>", unsafe_allow_html=True)
