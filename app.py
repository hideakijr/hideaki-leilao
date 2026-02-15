import streamlit as st
import pandas as pd
import requests
import io
import unicodedata
import re

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Caça Leilão Pro", layout="wide", page_icon="💎")

# --- CSS (Visual Arremata Completo) ---
st.markdown("""
<style>
    .stApp { background-color: #f8fafc; font-family: 'Segoe UI', Roboto, sans-serif; }
    
    .card-container {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
        gap: 25px;
        padding: 20px;
    }
    
    .imovel-card {
        background: white;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
        border: 1px solid #e2e8f0;
        overflow: hidden;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        transition: transform 0.2s;
        position: relative;
    }
    .imovel-card:hover { transform: translateY(-5px); box-shadow: 0 20px 25px -5px rgba(0,0,0,0.1); border-color: #3b82f6; }

    /* Topo Escuro */
    .header-dark {
        background: #1e293b;
        color: white;
        padding: 12px 15px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
    }
    .badge-discount { background-color: #ef4444; color: white; padding: 4px 8px; border-radius: 4px; font-weight: 800; }

    /* Corpo */
    .card-body { padding: 18px; color: #334155; }
    
    .meta-top { font-size: 0.75rem; color: #64748b; font-weight: 700; text-transform: uppercase; margin-bottom: 5px; }
    
    .card-title {
        font-size: 1.15rem; font-weight: 800; color: #0f172a; margin-bottom: 8px; line-height: 1.3;
        height: 46px; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
    }

    /* Detalhes Físicos (Quartos, Area) */
    .features-row {
        display: flex; gap: 15px; margin-bottom: 12px; font-size: 0.85rem; color: #475569; font-weight: 600;
        border-bottom: 1px solid #f1f5f9; padding-bottom: 10px;
    }
    .feat-item { display: flex; align-items: center; gap: 4px; }

    /* Data do Leilão */
    .date-row {
        display: flex; align-items: center; gap: 6px; font-size: 0.9rem; color: #1e293b; font-weight: 700; margin-bottom: 10px;
    }

    /* Preço */
    .price-section { background: #f8fafc; padding: 10px; border-radius: 8px; margin-top: 5px; border: 1px solid #e2e8f0; }
    .price-label { font-size: 0.7rem; color: #64748b; text-transform: uppercase; font-weight: bold; }
    .price-val { font-size: 1.4rem; color: #1e293b; font-weight: 900; }
    .price-old { font-size: 0.8rem; color: #94a3b8; text-decoration: line-through; }

    /* Tags */
    .tags-row { display: flex; gap: 6px; margin-top: 10px; flex-wrap: wrap; }
    .tag { font-size: 0.7rem; padding: 3px 8px; border-radius: 4px; font-weight: bold; }
    .tag-blue { background: #eff6ff; color: #1d4ed8; border: 1px solid #dbeafe; }
    .tag-green { background: #f0fdf4; color: #15803d; border: 1px solid #bbf7d0; }
    
    .btn-action {
        background: #2563eb; color: white !important; text-align: center; padding: 14px;
        font-weight: 700; text-transform: uppercase; text-decoration: none; font-size: 0.9rem;
        transition: background 0.2s;
    }
    .btn-action:hover { background: #1d4ed8; }

    .status-badge {
        position: absolute; top: 50px; right: 15px; font-size: 0.7rem; padding: 4px 10px;
        border-radius: 20px; font-weight: 800; box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        text-transform: uppercase;
    }
    .st-ocupado { background: #fef2f2; color: #991b1b; border: 1px solid #fecaca; }
    .st-livre { background: #f0fdf4; color: #166534; border: 1px solid #bbf7d0; }
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

# Função para extrair detalhes do texto (Regex)
def extrair_detalhes(texto):
    texto = texto.lower()
    # Quartos
    qtos = re.search(r'(\d+)\s?(quartos|qto)', texto)
    qtos_val = qtos.group(1) if qtos else "-"
    # Área
    area = re.search(r'([\d,.]+)\s?m2', texto)
    area_val = area.group(1) if area else "-"
    # Vagas
    vaga = re.search(r'(\d+)\s?vaga', texto)
    vaga_val = vaga.group(1) if vaga else "-"
    return qtos_val, area_val, vaga_val

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
        
        # Texto Completo
        df['Full_Text'] = df.apply(lambda x: ' '.join(x.astype(str)).lower(), axis=1)
        
        # Extrações
        df['Tipo'] = df['Full_Text'].apply(lambda x: 'APARTAMENTO' if 'apartamento' in x else ('CASA' if 'casa' in x else ('TERRENO' if 'terreno' in x else 'IMÓVEL')))
        df['Sit'] = df['Full_Text'].apply(lambda x: 'Ocupado' if 'ocupado' in x and 'desocupado' not in x else ('Desocupado' if 'desocupado' in x else 'Indefinido'))
        df['FGTS'] = df['Full_Text'].apply(lambda x: True if 'fgts' in x else False)
        
        # Detalhes Físicos (Novo!)
        detalhes = df['Full_Text'].apply(extrair_detalhes)
        df['Qtos'] = detalhes.apply(lambda x: x[0])
        df['Area'] = detalhes.apply(lambda x: x[1])
        df['Vagas'] = detalhes.apply(lambda x: x[2])

        # Modalidade e Data
        col_mod = next((c for c in df.columns if 'modalidade' in c), None)
        df['Mod'] = df[col_mod].astype(str).str.upper() if col_mod else "VENDA ONLINE"
        
        # Tenta achar coluna de Data (ex: Data do Leilao)
        col_data = next((c for c in df.columns if 'data' in c and 'nascimento' not in c), None)
        df['Data_Venda'] = df[col_data] if col_data else "-"

        return df, "Ok"
    except Exception as e: return None, str(e)

# --- INTERFACE ---
st.title("💎 Arremata Clone 3.0 (Full)")

with st.sidebar:
    st.header("Filtros")
    uf = st.selectbox("Estado", ["SP", "RJ", "MG", "PR", "SC", "RS", "BA", "GO", "DF"])
    if st.button("🔄 Atualizar Lista"): st.cache_data.clear()
    
    df, msg = carregar_dados(uf)
    
    if df is not None:
        # Botão de Exportar (Novo!)
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Exportar para Excel/CSV", data=csv, file_name=f"imoveis_{uf}.csv", mime="text/csv")
        
        st.divider()
        cidades = ["Todas"] + sorted(df.iloc[:,0].unique().tolist())
        col_cid = next((c for c in df.columns if 'cidade' in c), df.columns[0])
        cidades = ["Todas"] + sorted(df[col_cid].dropna().unique().tolist())
        sel_cid = st.selectbox("Cidade", cidades)
        
        sel_sit = st.selectbox("Ocupação", ["Todas", "Ocupado", "Desocupado"])
        sel_tipo = st.selectbox("Tipo", ["Todas"] + sorted(df['Tipo'].unique().tolist()))
        max_v = st.number_input("Valor Máximo (R$)", 0)
        desc_min = st.slider("Desconto Mínimo (%)", 0, 95, 40)
        busca = st.text_input("Buscar Bairro")
    else:
        st.error(msg)

# --- CARDS ---
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
    
    st.info(f"Encontrados: {len(f)} imóveis")
    
    html = "<div class='card-container'>"
    base = "https://venda-imoveis.caixa.gov.br/sistema/detalhe-imovel.asp?hdnimovel="
    col_id = next((c for c in df.columns if 'numero' in c and 'imovel' in c), df.columns[0])
    col_bair = next((c for c in df.columns if 'bairro' in c), '')
    col_end = next((c for c in df.columns if 'endereco' in c), '')

    for _, r in f.head(50).iterrows():
        icon = "🏠" if r['Tipo'] == 'CASA' else "🏢" if r['Tipo'] == 'APARTAMENTO' else "🌳"
        link = base + str(r[col_id])
        maps = f"https://www.google.com/maps/search/?api=1&query={r[col_end]}, {r[col_cid]}".replace(" ", "+")
        
        # Tags e Status
        status_html = ""
        if r['Sit'] == 'Ocupado': status_html = f"<div class='status-badge st-ocupado'>⛔ OCUPADO</div>"
        elif r['Sit'] == 'Desocupado': status_html = f"<div class='status-badge st-livre'>✅ DESOCUPADO</div>"
        
        tags_html = ""
        if r['Desc'] > 50: tags_html += "<span class='tag tag-blue'>⚡ Retorno ALTO</span>"
        if r['FGTS']: tags_html += "<span class='tag tag-green'>✅ Aceita FGTS</span>"
        
        # Detalhes Físicos e Data
        data_display = f"📅 {r['Data_Venda']}" if r['Data_Venda'] != "-" else "📅 Venda Online"
        detalhes_fisicos = f"""
        <div class='features-row'>
            <span class='feat-item'>🛏️ {r['Qtos']} qtos</span> | 
            <span class='feat-item'>📏 {r['Area']} m²</span> | 
            <span class='feat-item'>🚗 {r['Vagas']} vg</span>
        </div>
        """

        html += f"""
<div class='imovel-card'>
    <div class='header-dark'>
        <span>{r['Mod'][:20]}</span>
        <span class='badge-discount'>-{r['Desc']:.0f}%</span>
    </div>
    {status_html}
    <div class='card-body'>
        <div class='meta-top'>{icon} {r['Tipo']} • {r[col_cid]}</div>
        <div class='card-title'>{r[col_bair]}</div>
        
        {detalhes_fisicos}
        <div class='date-row'>{data_display}</div>
        
        <div style='font-size:0.8rem; margin-top:5px;'><a href='{maps}' target='_blank' style='color:#3b82f6; text-decoration:none'>📍 Ver Localização</a></div>
        
        <div class='price-section'>
            <div class='price-label'>Lance Inicial</div>
            <div class='price-val'>R$ {r['Venda']:,.2f}</div>
            <div class='price-old'>Avaliação: R$ {r['Avaliacao']:,.2f}</div>
        </div>
        <div class='tags-row'>{tags_html}</div>
    </div>
    <a href='{link}' target='_blank' class='btn-action'>VER DOCUMENTOS E DETALHES</a>
</div>"""
    
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)

elif df is None:
    st.warning("Carregando...")
