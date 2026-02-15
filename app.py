import streamlit as st
import pandas as pd
import requests
import io
import unicodedata

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Caça Leilão Pro", layout="wide", page_icon="💎")

# --- DESIGN "ARREMATA STYLE" ---
st.markdown("""
<style>
    /* Fundo geral mais claro */
    .stApp { background-color: #f3f4f6; font-family: 'Roboto', sans-serif; }
    
    /* Container dos Cards */
    .card-container {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
        gap: 25px;
        padding: 10px;
    }
    
    /* O Cartão em si */
    .imovel-card {
        background: white;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        overflow: hidden;
        border: 1px solid #e5e7eb;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        transition: transform 0.2s, box-shadow 0.2s;
        position: relative; /* Para posicionar as etiquetas */
    }
    .imovel-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 12px 24px rgba(0,0,0,0.12);
        border-color: #2563eb;
    }

    /* ETIQUETAS DO TOPO */
    .top-badges {
        display: flex;
        justify-content: space-between;
        background: #1f2937; /* Fundo escuro igual arremata */
        padding: 8px 12px;
        color: white;
        font-weight: bold;
        font-size: 0.75rem;
        text-transform: uppercase;
    }
    .discount-badge {
        background: #ef4444; /* Vermelho */
        color: white;
        padding: 2px 8px;
        border-radius: 4px;
        font-weight: 800;
    }

    /* CORPO DO CARTÃO */
    .card-body { padding: 16px; color: #374151; }
    
    .card-title {
        font-size: 0.95rem;
        font-weight: 800;
        color: #111827;
        margin-bottom: 4px;
        text-transform: uppercase;
        height: 40px; /* Altura fixa para alinhar */
        overflow: hidden;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
    }
    
    .card-bairro { font-size: 0.85rem; color: #6b7280; margin-bottom: 12px; font-weight: 500; }

    /* PREÇOS */
    .price-section { margin: 15px 0; border-top: 1px dashed #e5e7eb; padding-top: 10px; }
    .price-label { font-size: 0.7rem; color: #9ca3af; text-transform: uppercase; }
    .price-old { text-decoration: line-through; color: #9ca3af; font-size: 0.85rem; margin-bottom: 2px; }
    .price-new { font-size: 1.4rem; font-weight: 900; color: #111827; letter-spacing: -0.5px; }

    /* POTENCIAL E TAGS */
    .tags-container { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 15px; }
    .tag { font-size: 0.7rem; padding: 4px 8px; border-radius: 6px; font-weight: bold; display: flex; align-items: center; gap: 4px; }
    .tag-fgts { background: #dcfce7; color: #166534; border: 1px solid #86efac; }
    .tag-return-high { background: #dbeafe; color: #1e40af; border: 1px solid #93c5fd; }
    .tag-return-med { background: #fef3c7; color: #92400e; border: 1px solid #fcd34d; }
    
    /* BOTÃO */
    .btn-action {
        display: block;
        width: 100%;
        text-align: center;
        background: #2563eb; /* Azul Arremata */
        color: white !important;
        padding: 12px;
        text-decoration: none;
        font-weight: 700;
        font-size: 0.9rem;
        text-transform: uppercase;
        transition: background 0.2s;
    }
    .btn-action:hover { background: #1d4ed8; }
    
    /* Status Badge flutuante */
    .status-float { position: absolute; top: 40px; right: 10px; font-size: 0.7rem; padding: 3px 8px; border-radius: 12px; font-weight: bold; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    .status-ocupado { background: #fee2e2; color: #991b1b; }
    .status-livre { background: #dcfce7; color: #166534; }
    
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
        if r.status_code != 200: return None, f"Erro {r.status_code}"
        
        txt = r.content.decode('latin1')
        pular = inicio_tabela(txt)
        df = pd.read_csv(io.StringIO(txt), sep=';', skiprows=pular, on_bad_lines='skip')
        
        cols = {c: limpar_texto(c) for c in df.columns}
        df.rename(columns=cols, inplace=True)
        
        col_preco = next((c for c in df.columns if 'preco' in c or 'venda' in c and 'modalidade' not in c), None)
        if not col_preco: return None, "Formato mudou."
        
        def valor(v):
            if isinstance(v, str): return float(v.replace('R$','').replace(' ','').replace('.','').replace(',','.'))
            return float(v)
            
        df['Venda'] = df[col_preco].apply(valor)
        col_aval = next((c for c in df.columns if 'avaliacao' in c), None)
        df['Avaliacao'] = df[col_aval].apply(valor) if col_aval else df['Venda']
        df = df[df['Avaliacao'] > 0]
        
        # Inteligência de Texto
        df['Texto'] = df.apply(lambda x: ' '.join(x.astype(str)).lower(), axis=1)
        
        # 1. Ocupação
        df['Sit'] = df['Texto'].apply(lambda x: 'Ocupado' if 'ocupado' in x and 'desocupado' not in x else ('Desocupado' if 'desocupado' in x else 'Indefinido'))
        
        # 2. FGTS
        df['FGTS'] = df['Texto'].apply(lambda x: True if 'fgts' in x else False)
        
        # 3. Tipo
        col_tipo = next((c for c in df.columns if 'tipo' in c and 'venda' not in c), None)
        df['Tipo'] = df[col_tipo].str.split(',').str[0].str.upper().str.strip() if col_tipo else "IMÓVEL"
        
        # 4. Modalidade (Tentativa)
        col_mod = next((c for c in df.columns if 'modalidade' in c), None)
        if col_mod:
            df['Mod'] = df[col_mod].astype(str).str.upper()
        else:
            df['Mod'] = "VENDA ONLINE" # Padrão
        
        return df, "Ok"
    except Exception as e: return None, str(e)

# --- INTERFACE ---
st.title("💎 Arremata Clone (Beta)")

with st.sidebar:
    st.header("Filtros")
    uf = st.selectbox("Estado", ["SP", "RJ", "MG", "PR", "SC", "RS", "BA", "GO", "DF"])
    if st.button("🔄 Atualizar"): st.cache_data.clear()
    
    df, msg = carregar_dados(uf)
    
    if df is not None:
        cidades = ["Todas"] + sorted(df.iloc[:,0].unique().tolist()) # Fallback
        col_cid = next((c for c in df.columns if 'cidade' in c), df.columns[0])
        cidades = ["Todas"] + sorted(df[col_cid].dropna().unique().tolist())
        sel_cid = st.selectbox("Cidade", cidades)
        
        sel_sit = st.selectbox("Ocupação", ["Todas", "Ocupado", "Desocupado"])
        sel_tipo = st.selectbox("Tipo", ["Todas"] + sorted(df['Tipo'].unique().tolist()))
        max_v = st.number_input("Valor Máximo", 0)
        desc_min = st.slider("Desconto Mínimo %", 0, 95, 40)
        busca = st.text_input("Bairro")
    else:
        st.error(msg)

# --- RENDERIZAÇÃO ---
if df is not None:
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
    
    st.info(f"Mostrando {len(f)} imóveis em destaque")
    
    html = "<div class='card-container'>"
    base = "https://venda-imoveis.caixa.gov.br/sistema/detalhe-imovel.asp?hdnimovel="
    col_id = next((c for c in df.columns if 'numero' in c and 'imovel' in c), df.columns[0])
    col_bair = next((c for c in df.columns if 'bairro' in c), '')
    col_end = next((c for c in df.columns if 'endereco' in c), '')

    for _, r in f.head(50).iterrows():
        # Lógica de Design
        discount = f"{r['Desc']:.0f}%"
        modalidade = r['Mod'][:20] # Limita tamanho
        
        # Potencial de Retorno
        if r['Desc'] > 50:
            potencial_html = "<div class='tag tag-return-high'>⚡ Retorno ALTO</div>"
        elif r['Desc'] > 30:
            potencial_html = "<div class='tag tag-return-med'>📈 Retorno MÉDIO</div>"
        else:
            potencial_html = ""
            
        # FGTS
        fgts_html = "<div class='tag tag-fgts'>✅ Aceita FGTS</div>" if r['FGTS'] else ""
        
        # Status Flutuante
        if r['Sit'] == 'Ocupado':
            status_html = "<div class='status-float status-ocupado'>⛔ OCUPADO</div>"
        elif r['Sit'] == 'Desocupado':
            status_html = "<div class='status-float status-livre'>✅ DESOCUPADO</div>"
        else:
            status_html = ""

        link = base + str(r[col_id])
        maps = f"https://www.google.com/maps/search/?api=1&query={r[col_end]}, {r[col_cid]}".replace(" ", "+")
        
        html += f"""
        <div class='imovel-card'>
            <div class='top-badges'>
                <span>{modalidade}</span>
                <span class='discount-badge'>{discount} OFF</span>
            </div>
            
            {status_html}
            
            <div class='card-body'>
                <div style='font-size:0.75rem; color:#6b7280; font-weight:bold; margin-bottom:5px'>
                    {r['Tipo']} • {r[col_cid]}
                </div>
                
                <div class='card-title'>{r[col_bair]}</div>
                <div class='card-bairro'>
                    <a href='{maps}' target='_blank' style='color:#2563eb; text-decoration:none'>📍 Ver no Mapa</a>
                </div>
                
                <div class='price-section'>
                    <div class='price-label'>Valor de Venda</div>
                    <div class='price-new'>R$ {r['Venda']:,.2f}</div>
                    <div class='price-old'>Avaliado em: R$ {r['Avaliacao']:,.2f}</div>
                </div>
                
                <div class='tags-container'>
                    {potencial_html}
                    {fgts_html}
                </div>
            </div>
            
            <a href='{link}' target='_blank' class='btn-action'>VER DETALHES</a>
        </div>
        """
    
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)

elif df is None:
    st.warning("Aguardando dados da Caixa...")
