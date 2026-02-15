import streamlit as st
import pandas as pd
import requests
import io
import unicodedata
import re

# 1. CONFIGURAÇÃO INICIAL (Obrigatório ser a primeira linha do Streamlit)
st.set_page_config(page_title="Caça Leilão Pro", layout="wide", page_icon="💎")

# 2. ESTILO CSS (Design Arremata)
CSS_STYLE = """
<style>
    .stApp { background-color: #f1f5f9; font-family: 'Segoe UI', sans-serif; }
    .card-container { display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 20px; padding: 20px; }
    .imovel-card { background: white; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); border: 1px solid #cbd5e1; overflow: hidden; display: flex; flex-direction: column; justify-content: space-between; position: relative; }
    .header-dark { background: #1e293b; color: white; padding: 12px 15px; display: flex; justify-content: space-between; align-items: center; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; }
    .badge-discount { background-color: #ef4444; color: white; padding: 4px 8px; border-radius: 4px; font-weight: 800; }
    .card-body { padding: 15px; color: #334155; }
    .meta-top { font-size: 0.75rem; color: #64748b; font-weight: 700; text-transform: uppercase; margin-bottom: 5px; }
    .card-title { font-size: 1.1rem; font-weight: 800; color: #0f172a; margin-bottom: 10px; line-height: 1.3; height: 44px; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; }
    .features-row { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 15px; padding-bottom: 10px; border-bottom: 1px solid #f1f5f9; font-size: 0.85rem; font-weight: 600; color: #475569; }
    .analytics-row { display: flex; justify-content: space-between; font-size: 0.8rem; font-weight: bold; color: #059669; background: #ecfdf5; padding: 8px; border-radius: 6px; margin-bottom: 10px; }
    .map-actions { display: flex; gap: 5px; margin-bottom: 10px; }
    .btn-map { flex: 1; text-align: center; padding: 8px; border-radius: 6px; font-size: 0.75rem; font-weight: bold; text-decoration: none; color: white; transition: opacity 0.2s; }
    .btn-google { background-color: #4285F4; }
    .btn-waze { background-color: #33ccff; color: #000; }
    .price-section { background: #f8fafc; padding: 10px; border-radius: 8px; border: 1px solid #e2e8f0; }
    .price-label { font-size: 0.7rem; color: #64748b; text-transform: uppercase; font-weight: bold; }
    .price-val { font-size: 1.4rem; color: #1e293b; font-weight: 900; }
    .price-old { font-size: 0.8rem; color: #94a3b8; text-decoration: line-through; }
    .btn-action { background: #2563eb; color: white !important; text-align: center; padding: 12px; font-weight: 700; text-transform: uppercase; text-decoration: none; font-size: 0.9rem; margin-top: 0; display: block; }
    .btn-action:hover { background: #1d4ed8; }
    .status-badge { position: absolute; top: 45px; right: 15px; font-size: 0.7rem; padding: 3px 8px; border-radius: 20px; font-weight: 800; text-transform: uppercase; z-index: 10; border: 1px solid #bbf7d0; background: #f0fdf4; color: #166534; }
    .st-ocupado { background: #fef2f2; color: #991b1b; border-color: #fecaca; }
</style>
"""
st.markdown(CSS_STYLE, unsafe_allow_html=True)

# 3. FUNÇÕES UTILITÁRIAS
def limpar_texto(t):
    if not isinstance(t, str): return str(t)
    return ''.join(c for c in unicodedata.normalize('NFD', t) if unicodedata.category(c) != 'Mn').lower().strip()

def inicio_tabela(txt):
    for i, l in enumerate(txt.split('\n')):
        if 'Bairro' in l and ('Valor' in l or 'Preço' in l or 'Venda' in l): return i
    return 0

def extrair_medidas(row):
    texto = ' '.join(row.astype(str)).lower()
    
    # Regex seguro para capturar números
    q = re.search(r'(\d+)\s*(quartos|qto|dorm)', texto)
    v = re.search(r'(\d+)\s*(vaga|garagem|vg)', texto)
    ac = re.search(r'(privativa|construida|util|real)\s*[:=]?\s*([\d,.]+)', texto)
    at = re.search(r'(terreno|total|averbada)\s*[:=]?\s*([\d,.]+)', texto)
    
    def limpa(match):
        if not match: return 0.0
        try:
            return float(match.group(2).replace('.', '').replace(',', '.'))
        except:
            return 0.0

    return {
        'qtos': q.group(1) if q else "0",
        'vagas': v.group(1) if v else "0",
        'cons': limpa(ac),
        'terr': limpa(at)
    }

# 4. CARREGAMENTO DE DADOS (BLINDADO)
@st.cache_data(ttl=3600)
def carregar_dados(uf):
    url = f"https://venda-imoveis.caixa.gov.br/listaweb/Lista_imoveis_{uf}.csv"
    try:
        # Download
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=20)
        if r.status_code != 200:
            return None, f"Erro {r.status_code}: Site da Caixa indisponível."
        
        # Leitura
        txt = r.content.decode('latin1')
        pular = inicio_tabela(txt)
        df = pd.read_csv(io.StringIO(txt), sep=';', skiprows=pular, on_bad_lines='skip')
        
        # Limpeza de Colunas
        cols = {c: limpar_texto(c) for c in df.columns}
        df.rename(columns=cols, inplace=True)
        
        # Detecção da Coluna de Preço (Mais Segura)
        col_v = None
        for c in df.columns:
            if ('preco' in c or 'venda' in c) and 'modalidade' not in c:
                col_v = c
                break
        
        if col_v is None:
            return None, "Erro: Não encontrei a coluna de Preço na planilha da Caixa."

        # Conversão de Valores
        def conv(v):
            try:
                s = str(v).replace('R$','').replace(' ','').replace('.','').replace(',','.')
                return float(s)
            except:
                return 0.0
                
        df['Venda'] = df[col_v].apply(conv)
        col_a = next((c for c in df.columns if 'avaliacao' in c), None)
        df['Avaliacao'] = df[col_a].apply(conv) if col_a else df['Venda']
        df = df[df['Avaliacao'] > 0].copy()
        
        # Enriquecimento
        df['Full'] = df.apply(lambda x: ' '.join(x.astype(str)).lower(), axis=1)
        df['Tipo'] = df['Full'].apply(lambda x: 'APARTAMENTO' if 'apartamento' in x else ('CASA' if 'casa' in x else ('TERRENO' if 'terreno' in x else 'IMÓVEL')))
        df['Sit'] = df['Full'].apply(lambda x: 'Ocupado' if 'ocupado' in x and 'desocupado' not in x else ('Desocupado' if 'desocupado' in x else 'Indefinido'))
        
        # Extração de Medidas
        m = df.apply(extrair_medidas, axis=1)
        df['Qtos'] = [x['qtos'] for x in m]
        df['Vagas'] = [x['vagas'] for x in m]
        df['Area_C'] = [x['cons'] for x in m]
        df['Area_T'] = [x['terr'] for x in m]

        col_m = next((c for c in df.columns if 'modalidade' in c), None)
        df['Mod'] = df[col_m].astype(str).str.upper() if col_m else "ONLINE"
        
        return df, "Ok"
    except Exception as e:
        return None, f"Erro técnico: {str(e)}"

# 5. INTERFACE DO USUÁRIO
st.title("💎 Arremata Clone 4.0")

with st.sidebar:
    st.header("Filtros")
    uf = st.selectbox("Estado", ["SP", "RJ", "MG", "PR", "SC", "RS", "BA", "GO", "DF"])
    if st.button("🔄 Atualizar"): 
        st.cache_data.clear()
        
    df, msg = carregar_dados(uf)
    
    if df is not None:
        col_c = next((c for c in df.columns if 'cidade' in c), df.columns[0])
        lista_cidades = sorted(df[col_c].dropna().unique().tolist())
        sel_c = st.selectbox("Cidade", ["Todas"] + lista_cidades)
        max_p = st.number_input("Preço Máximo", 0)
        min_d = st.slider("Desconto % Mínimo", 0, 95, 40)
    else:
        st.error(msg)

# 6. EXIBIÇÃO DOS CARDS
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
        # Links de Mapa
        endereco_full = f"{r[col_end]}, {r[col_b]}, {r[col_c]}".replace(" ", "+")
        link_g = f"https://www.google.com/maps/search/?api=1&query={endereco_full}"
        link_w = f"https://waze.com/ul?q={endereco_full}"
        
        # Cálculos
        lucro = r['Avaliacao'] - r['Venda']
        m2_val = 0
        if r['Area_C'] > 0: m2_val = r['Venda'] / r['Area_C']
        elif r['Area_T'] > 0: m2_val = r['Venda'] / r['Area_T']
        txt_m2 = f"R$ {m2_val:,.0f}/m²" if m2_val > 0 else "-"
        
        # Features
        feats = []
        if r['Qtos'] != "0": feats.append(f"🛏️ {r['Qtos']}")
        if r['Area_C'] > 0: feats.append(f"🏠 {r['Area_C']:.0f}m²")
        if r['Area_T'] > 0: feats.append(f"🌳 {r['Area_T']:.0f}m²")
        if r['Vagas'] != "0": feats.append(f"🚗 {r['Vagas']}")
        
        feats_html = " | ".join(feats) if feats else "⚠️ Ver Edital"
        status_cls = 'st-ocupado' if r['Sit'] == 'Ocupado' else 'st-livre'
        
        # HTML Seguro
        card_html = f"""
        <div class='imovel-card'>
            <div class='header-dark'>
                <span>{r['Mod'][:20]}</span>
                <span class='badge-discount'>-{r['Desc']:.0f}%</span>
            </div>
            <div class='status-badge {status_cls}'>{r['Sit']}</div>
            <div class='card-body'>
                <div class='meta-top'>{r['Tipo']} • {r[col_c]}</div>
                <div class='card-title'>{r[col_b]}</div>
                <div class='features-row'>{feats_html}</div>
                <div class='analytics-row'>
                    <span>💰 Lucro: R$ {lucro:,.0f}</span>
                    <span>📐 {txt_m2}</span>
                </div>
                <div class='map-actions'>
                    <a href='{link_g}' target='_blank' class='btn-map btn-google'>📍 Maps</a>
                    <a href='{link_w}' target='_blank' class='btn-map btn-waze'>🚙 Waze</a>
                </div>
                <div class='price-section'>
                    <div class='price-label'>Lance Inicial</div>
                    <div class='price-val'>R$ {r['Venda']:,.2f}</div>
                    <div class='price-old'>Avaliação: R$ {r['Avaliacao']:,.2f}</div>
                </div>
            </div>
            <a href='{base_cx + str(r[col_id])}' target='_blank' class='btn-action'>VER NA CAIXA</a>
        </div>
        """
        html_out += card_html
    
    st.markdown(html_out + "</div>", unsafe_allow_html=True)
