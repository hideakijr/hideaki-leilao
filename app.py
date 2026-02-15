import streamlit as st
import pandas as pd
import requests
import io
import re

# 1. CONFIGURAÇÃO
st.set_page_config(page_title="Caça Leilão Pro", layout="wide", page_icon="💎")

# 2. CSS (ESTILO)
st.markdown("""
<style>
    .stApp { background-color: #f8fafc; font-family: sans-serif; }
    .card-container { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 20px; padding: 20px; }
    .imovel-card { background: white; border-radius: 10px; border: 1px solid #e2e8f0; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    .header-dark { background: #1e293b; color: white; padding: 10px; display: flex; justify-content: space-between; align-items: center; font-size: 0.75rem; font-weight: bold; }
    .badge-off { background: #ef4444; padding: 2px 6px; border-radius: 4px; }
    .card-body { padding: 15px; color: #334155; }
    .meta { font-size: 0.7rem; color: #64748b; font-weight: bold; text-transform: uppercase; margin-bottom: 5px; }
    .title { font-size: 1.1rem; font-weight: 800; color: #0f172a; margin-bottom: 10px; line-height: 1.2; height: 42px; overflow: hidden; }
    .features { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 10px; font-size: 0.8rem; font-weight: 600; color: #475569; border-bottom: 1px solid #f1f5f9; padding-bottom: 10px; }
    .price-box { background: #f8fafc; padding: 10px; border-radius: 6px; border: 1px solid #cbd5e1; margin-top: 10px; }
    .val { font-size: 1.4rem; color: #1e293b; font-weight: 900; }
    .old { font-size: 0.8rem; color: #94a3b8; text-decoration: line-through; }
    .btn { display: block; background: #2563eb; color: white !important; text-align: center; padding: 12px; font-weight: bold; text-decoration: none; margin-top: 0; }
    .btn:hover { background: #1d4ed8; }
    .maps-row { display: flex; gap: 5px; margin-top: 10px; }
    .btn-map { flex: 1; text-align: center; padding: 6px; border-radius: 4px; font-size: 0.75rem; font-weight: bold; color: white; text-decoration: none; }
</style>
""", unsafe_allow_html=True)

# 3. FUNÇÕES
def limpar(val):
    if not isinstance(val, str): return val
    return val.replace('R$','').replace('.','').replace(',','.').strip()

def get_medidas(texto):
    texto = str(texto).lower()
    q = re.search(r'(\d+)\s*(qto|quart)', texto)
    v = re.search(r'(\d+)\s*(vaga|garag)', texto)
    ac = re.search(r'(privativa|construida|util)\s*[:=]?\s*([\d,.]+)', texto)
    at = re.search(r'(terreno|total)\s*[:=]?\s*([\d,.]+)', texto)
    
    def safe_num(m):
        if not m: return 0
        try: return int(float(m.group(2).replace('.','').replace(',','.')))
        except: return 0
    
    return {'q': q.group(1) if q else "0", 'v': v.group(1) if v else "0", 'c': safe_num(ac), 't': safe_num(at)}

@st.cache_data(ttl=300)
def baixar_caixa(uf):
    url = f"https://venda-imoveis.caixa.gov.br/listaweb/Lista_imoveis_{uf}.csv"
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=25)
        if r.status_code != 200: return None, f"Erro Caixa: {r.status_code}"
        
        # Acha onde começa a tabela
        lines = r.content.decode('latin1').split('\n')
        start = 0
        for i, l in enumerate(lines):
            if 'Bairro' in l and ('Valor' in l or 'Preço' in l):
                start = i
                break
        
        df = pd.read_csv(io.StringIO('\n'.join(lines[start:])), sep=';', on_bad_lines='skip')
        
        # Limpa colunas
        cols = {c: c.lower().strip() for c in df.columns}
        df.rename(columns=cols, inplace=True)
        
        # Acha colunas vitais
        col_venda = next((c for c in df.columns if 'venda' in c or 'preco' in c), None)
        col_cidade = next((c for c in df.columns if 'cidade' in c), df.columns[0])
        
        if not col_venda: return None, "Erro: Coluna de preço não encontrada."
        
        # Converte Preços
        df['Venda'] = df[col_venda].apply(lambda x: float(limpar(x)) if isinstance(x, str) else x)
        col_aval = next((c for c in df.columns if 'avaliacao' in c), None)
        df['Avaliacao'] = df[col_aval].apply(lambda x: float(limpar(x)) if isinstance(x, str) else x) if col_aval else df['Venda']
        df = df[df['Avaliacao'] > 0].copy()
        
        # Processa Texto
        df['Full'] = df.apply(lambda x: ' '.join(x.astype(str)).lower(), axis=1)
        medidas = df['Full'].apply(get_medidas)
        df['Q'] = [m['q'] for m in medidas]
        df['V'] = [m['v'] for m in medidas]
        df['AC'] = [m['c'] for m in medidas]
        df['AT'] = [m['t'] for m in medidas]
        
        return df, "Ok"
        
    except Exception as e: return None, str(e)

# 4. SIDEBAR
with st.sidebar:
    st.header("Painel de Controle")
    uf = st.selectbox("Estado", ["SP", "RJ", "MG", "PR", "SC", "RS", "BA", "GO", "DF"])
    
    if st.button("🔄 Forçar Atualização"): st.cache_data.clear()
    
    status_text = st.empty()
    status_text.text("Conectando à Caixa...")
    
    df, erro = baixar_caixa(uf)
    
    if df is not None:
        status_text.success("Dados carregados!")
        col_cid = next((c for c in df.columns if 'cidade' in c), None)
        cidades = sorted(df[col_cid].unique())
        sel_cidade = st.selectbox("Cidade", ["Todas"] + cidades)
        desc_min = st.slider("Desconto Mínimo", 0, 95, 40)
    else:
        status_text.error("Falha ao carregar.")

# 5. TELA PRINCIPAL (DEBUG)
if df is None:
    st.error(f"⚠️ Não foi possível carregar os imóveis de {uf}.")
    st.warning(f"Detalhe do erro: {erro}")
    st.info("Tente selecionar outro estado ou clique em 'Forçar Atualização'.")

else:
    # Filtros
    f = df.copy()
    col_cid = next((c for c in f.columns if 'cidade' in c), f.columns[0])
    if sel_cidade != "Todas": f = f[f[col_cid] == sel_cidade]
    
    f['Desc'] = ((f['Avaliacao'] - f['Venda']) / f['Avaliacao']) * 100
    f = f[f['Desc'] >= desc_min].sort_values('Desc', ascending=False)
    
    st.subheader(f"Encontrados: {len(f)} oportunidades em {uf}")
    
    html = "<div class='card-container'>"
    
    # Colunas dinâmicas
    col_bairro = next((c for c in f.columns if 'bairro' in c), '')
    col_end = next((c for c in f.columns if 'endereco' in c), '')
    col_id = next((c for c in f.columns if 'numero' in c and 'imovel' in c), '')
    
    for _, r in f.head(50).iterrows():
        # Prepara dados
        tipo = "🏠 CASA" if "casa" in r['Full'] else ("🏢 APTO" if "apartamento" in r['Full'] else "🌳 TERRENO")
        end_map = f"{r[col_end]}, {r[col_cid]}".replace(" ", "+")
        
        # Medidas
        feats = []
        if r['Q'] != "0": feats.append(f"🛏️ {r['Q']}")
        if r['AC'] > 0: feats.append(f"📐 {r['AC']}m²")
        if r['AT'] > 0: feats.append(f"🌳 {r['AT']}m²")
        if r['V'] != "0": feats.append(f"🚗 {r['V']}")
        feat_html = " | ".join(feats) if feats else "⚠️ Ver Edital"
        
        html += f"""
        <div class='imovel-card'>
            <div class='header-dark'>
                <span>ONLINE</span>
                <span class='badge-off'>-{r['Desc']:.0f}% OFF</span>
            </div>
            <div class='card-body'>
                <div class='meta'>{tipo} • {r[col_cid]}</div>
                <div class='title'>{r[col_bairro]}</div>
                <div class='features'>{feat_html}</div>
                
                <div class='maps-row'>
                    <a href='https://maps.google.com/?q={end_map}' target='_blank' class='btn-map' style='background:#4285F4'>📍 Maps</a>
                    <a href='https://waze.com/ul?q={end_map}' target='_blank' class='btn-map' style='background:#33ccff;color:black'>🚙 Waze</a>
                </div>
                
                <div class='price-box'>
                    <div style='display:flex;justify-content:space-between'>
                        <span style='font-size:0.7rem;font-weight:bold;color:#64748b'>LANCE MÍNIMO</span>
                        <span class='old'>Aval: R$ {r['Avaliacao']:,.0f}</span>
                    </div>
                    <div class='val'>R$ {r['Venda']:,.2f}</div>
                </div>
            </div>
            <a href='https://venda-imoveis.caixa.gov.br/sistema/detalhe-imovel.asp?hdnimovel={r[col_id]}' target='_blank' class='btn'>VER NA CAIXA</a>
        </div>
        """
        
    st.markdown(html + "</div>", unsafe_allow_html=True)
