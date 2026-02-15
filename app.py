import streamlit as st
import pandas as pd
import requests
import io
import unicodedata

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Caça Leilão Auto", layout="wide", page_icon="🏠")

# --- CSS (Visual) ---
st.markdown("""
<style>
    .stApp { background-color: #f0f2f6; }
    div.block-container { padding-top: 2rem; }
    .card-container { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; }
    .imovel-card { background: white; border-radius: 15px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); overflow: hidden; border: 1px solid #e0e0e0; transition: transform 0.2s; display: flex; flex-direction: column; justify-content: space-between; }
    .imovel-card:hover { transform: translateY(-5px); box-shadow: 0 10px 20px rgba(0,0,0,0.1); border-color: #ff8c00; }
    .card-header { background: #1a202c; padding: 15px; display: flex; justify-content: space-between; align-items: center; border-bottom: 3px solid #ff8c00; }
    .card-city { color: white; font-weight: bold; font-size: 0.9rem; text-transform: uppercase; }
    .badge { padding: 4px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: 800; text-transform: uppercase; }
    .bg-red { background-color: #fee2e2; color: #991b1b; }
    .bg-green { background-color: #dcfce7; color: #166534; }
    .bg-gray { background-color: #edf2f7; color: #4a5568; }
    .card-body { padding: 15px; color: #4a5568; }
    .card-type { font-size: 0.8rem; font-weight: bold; color: #718096; margin-bottom: 5px; text-transform: uppercase; }
    .card-bairro { font-size: 1.1rem; font-weight: 800; color: #2d3748; margin-bottom: 5px; line-height: 1.2; }
    .map-link { font-size: 0.85rem; color: #3182ce; text-decoration: none; font-weight: 500; display: block; margin-bottom: 15px; }
    .map-link:hover { text-decoration: underline; color: #2c5282; }
    .price-box { background: #fffaf0; border: 1px solid #fbd38d; border-radius: 10px; padding: 12px; text-align: center; }
    .price-old { font-size: 0.85rem; color: #a0aec0; text-decoration: line-through; }
    .price-new { font-size: 1.5rem; font-weight: 900; color: #c05621; }
    .discount { background: #48bb78; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: bold; float: right; }
    .btn-site { display: block; width: 100%; text-align: center; background: #ed8936; color: white !important; padding: 15px; text-decoration: none; font-weight: 800; text-transform: uppercase; letter-spacing: 1px; transition: background 0.3s; }
    .btn-site:hover { background: #dd6b20; }
</style>
""", unsafe_allow_html=True)

# --- LÓGICA ---
def limpar_texto(t):
    if not isinstance(t, str): return str(t)
    return ''.join(c for c in unicodedata.normalize('NFD', t) if unicodedata.category(c) != 'Mn').lower().strip()

def inicio_tabela(txt):
    for i, l in enumerate(txt.split('\n')):
        if 'Bairro' in l and ('Valor' in l or 'Preço' in l or 'Venda' in l): return i
    return 0

@st.cache_data(ttl=3600)
def carregar_dados(uf):
    url = f"https://venda-imoveis.caixa.gov.br/listaweb/Lista_imoveis_{uf}.csv"
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        if r.status_code != 200: return None, f"Erro {r.status_code}: Bloqueio ou site fora do ar."
        
        txt = r.content.decode('latin1')
        pular = inicio_tabela(txt)
        df = pd.read_csv(io.StringIO(txt), sep=';', skiprows=pular, on_bad_lines='skip')
        
        cols = {c: limpar_texto(c) for c in df.columns}
        df.rename(columns=cols, inplace=True)
        
        col_preco = next((c for c in df.columns if 'preco' in c or 'venda' in c and 'modalidade' not in c), None)
        if not col_preco: return None, "Formato do arquivo mudou."
        
        def valor(v):
            if isinstance(v, str): return float(v.replace('R$','').replace(' ','').replace('.','').replace(',','.'))
            return float(v)
            
        df['Venda'] = df[col_preco].apply(valor)
        col_aval = next((c for c in df.columns if 'avaliacao' in c), None)
        df['Avaliacao'] = df[col_aval].apply(valor) if col_aval else df['Venda']
        df = df[df['Avaliacao'] > 0]
        
        df['Texto'] = df.apply(lambda x: ' '.join(x.astype(str)).lower(), axis=1)
        df['Sit'] = df['Texto'].apply(lambda x: 'Ocupado' if 'ocupado' in x and 'desocupado' not in x else ('Desocupado' if 'desocupado' in x else 'Indefinido'))
        
        col_tipo = next((c for c in df.columns if 'tipo' in c and 'venda' not in c), None)
        df['Tipo'] = df[col_tipo].str.split(',').str[0].str.upper().str.strip() if col_tipo else "IMÓVEL"
        
        return df, "Ok"
    except Exception as e: return None, str(e)

# --- TELA ---
st.title("🏡 Caçador de Leilão Auto")
st.markdown("Monitoramento em tempo real direto da Caixa.")

with st.sidebar:
    st.header("Painel de Controle")
    uf = st.selectbox("Estado", ["SP", "RJ", "MG", "PR", "SC", "RS", "BA", "GO", "DF"])
    if st.button("🔄 Forçar Atualização"): st.cache_data.clear()
    
    df, msg = carregar_dados(uf)
    
    if df is not None:
        st.divider()
        st.subheader("Filtros")
        
        col_cid = next((c for c in df.columns if 'cidade' in c), df.columns[0])
        cidades = ["Todas"] + sorted(df[col_cid].dropna().unique().tolist())
        sel_cid = st.selectbox("Cidade", cidades)
        
        sel_sit = st.selectbox("Ocupação", ["Todas", "Ocupado", "Desocupado"])
        sel_tipo = st.selectbox("Tipo", ["Todas"] + sorted(df['Tipo'].unique().tolist()))
        max_v = st.number_input("Valor Máximo (R$)", 0)
        desc_min = st.slider("Desconto Mínimo", 0, 95, 40)
        busca = st.text_input("Buscar Bairro ou Rua")
    else:
        st.error(msg)

# --- CARDS ---
if df is not None:
    # Filtragem
    f = df.copy()
    if sel_cid != "Todas": f = f[f[col_cid] == sel_cid]
    if sel_sit != "Todas": f = f[f['Sit'] == sel_sit]
    if sel_tipo != "Todas": f = f[f['Tipo'] == sel_tipo]
    if max_v > 0: f = f[f['Venda'] <= max_v]
    if busca: 
        col_bairro = next((c for c in df.columns if 'bairro' in c), None)
        if col_bairro: f = f[f[col_bairro].astype(str).str.contains(limpar_texto(busca), case=False)]
        
    f['Desc'] = ((f['Avaliacao'] - f['Venda']) / f['Avaliacao']) * 100
    f = f[f['Desc'] >= desc_min].sort_values('Desc', ascending=False)
    
    st.success(f"Encontrados: {len(f)} oportunidades")
    
    # GERAÇÃO HTML (SEM INDENTAÇÃO PARA NÃO DAR ERRO)
    html = "<div class='card-container'>"
    base = "https://venda-imoveis.caixa.gov.br/sistema/detalhe-imovel.asp?hdnimovel="
    col_id = next((c for c in df.columns if 'numero' in c and 'imovel' in c), df.columns[0])
    col_end = next((c for c in df.columns if 'endereco' in c), '')
    col_bair = next((c for c in df.columns if 'bairro' in c), '')

    for _, r in f.head(50).iterrows():
        cor_bg = "bg-red" if r['Sit'] == 'Ocupado' else "bg-green" if r['Sit'] == 'Desocupado' else "bg-gray"
        icon = "⛔" if r['Sit'] == 'Ocupado' else "✅" if r['Sit'] == 'Desocupado' else "❔"
        link = base + str(r[col_id])
        # Link do Maps corrigido
        ende_maps = f"{r[col_end]}, {r[col_cid]}".replace(" ", "+")
        maps = f"https://www.google.com/maps/search/?api=1&query={ende_maps}"
        
        # O HTML abaixo está 'colado' na esquerda propositalmente para não quebrar
        html += f"""
<div class='imovel-card'>
    <div class='card-header'>
        <span class='card-city'>📍 {r[col_cid]}</span>
        <span class='badge {cor_bg}'>{icon} {r['Sit']}</span>
    </div>
    <div class='card-body'>
        <div class='card-type'>{r['Tipo']}</div>
        <div class='card-bairro'>{r[col_bair]}</div>
        <a href='{maps}' target='_blank' class='map-link'>🗺️ Ver no Mapa</a>
        <div class='price-box'>
            <span class='discount'>-{r['Desc']:.0f}% OFF</span>
            <div class='price-old'>Avaliação: R$ {r['Avaliacao']:,.2f}</div>
            <div class='price-new'>R$ {r['Venda']:,.2f}</div>
        </div>
    </div>
    <a href='{link}' target='_blank' class='btn-site'>🔥 Ver Detalhes</a>
</div>"""
    
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)

elif df is None:
    st.info("Aguardando dados... Se demorar, a Caixa pode estar instável.")
