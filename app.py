import streamlit as st
import pandas as pd
import requests
import io
import unicodedata
import urllib.parse

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Caça Leilão Auto", layout="wide", page_icon="🏠")

# --- CSS PERSONALIZADO (DESIGN) ---
st.markdown("""
<style>
    .stApp { background-color: #eef2f6; }
    .card-container { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 20px; padding: 10px; }
    .imovel-card { background: white; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); overflow: hidden; border: 1px solid #e5e7eb; transition: transform 0.2s; }
    .imovel-card:hover { transform: translateY(-5px); box-shadow: 0 10px 15px rgba(0,0,0,0.1); border-color: #f97316; }
    .card-header { background: #1e293b; padding: 15px; color: white; display: flex; justify-content: space-between; align-items: center; border-bottom: 3px solid #f97316; }
    .card-city { font-weight: 800; font-size: 0.9rem; text-transform: uppercase; color: white; }
    .badge { padding: 4px 8px; border-radius: 12px; font-size: 0.7rem; font-weight: 800; text-transform: uppercase; }
    .badge-red { background: #fee2e2; color: #991b1b; }
    .badge-green { background: #dcfce7; color: #166534; }
    .badge-gray { background: #f3f4f6; color: #4b5563; }
    .card-body { padding: 15px; color: #334155; }
    .card-title { font-size: 1.1rem; font-weight: 700; color: #0f172a; margin-bottom: 5px; height: 50px; overflow: hidden; }
    .price-box { background: #fffbeb; border: 1px solid #fcd34d; border-radius: 8px; padding: 10px; margin-top: 10px; }
    .price-value { font-size: 1.4rem; font-weight: 900; color: #b45309; }
    .discount-tag { float: right; background: #16a34a; color: white; padding: 2px 6px; border-radius: 4px; font-size: 0.8rem; font-weight: bold; }
    .btn-action { display: block; width: 100%; text-align: center; background: #ea580c; color: white; padding: 12px; text-decoration: none; font-weight: bold; margin-top: 0; }
    .btn-action:hover { background: #c2410c; color: white; }
    a { text-decoration: none; }
</style>
""", unsafe_allow_html=True)

# --- FUNÇÕES ---
def limpar_texto(texto):
    if not isinstance(texto, str): return str(texto)
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn').lower().strip()

def encontrar_inicio_tabela(conteudo):
    linhas = conteudo.split('\n')
    for i, linha in enumerate(linhas):
        if 'Bairro' in linha and ('Valor' in linha or 'Preço' in linha or 'Venda' in linha):
            return i
    return 0

@st.cache_data(ttl=3600) # Guarda na memória por 1 hora para não baixar toda hora
def baixar_dados(estado):
    url = f"https://venda-imoveis.caixa.gov.br/listaweb/Lista_imoveis_{estado}.csv"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code != 200: return None, f"Erro {r.status_code}: Caixa bloqueou ou site fora do ar."
        
        conteudo = r.content.decode('latin1')
        pular = encontrar_inicio_tabela(conteudo)
        df = pd.read_csv(io.StringIO(conteudo), sep=';', skiprows=pular, on_bad_lines='skip')
        
        # Tratamento
        cols = {c: limpar_texto(c) for c in df.columns}
        df.rename(columns=cols, inplace=True)
        
        col_preco = next((c for c in df.columns if 'preco' in c or 'venda' in c and 'modalidade' not in c), None)
        if not col_preco: return None, "Mudança no formato do arquivo."
        
        def arrumar(v):
            if isinstance(v, str):
                return float(v.replace('R$','').replace(' ','').replace('.','').replace(',','.'))
            return float(v)
            
        df['Venda'] = df[col_preco].apply(arrumar)
        col_aval = next((c for c in df.columns if 'avaliacao' in c), None)
        df['Avaliacao'] = df[col_aval].apply(arrumar) if col_aval else df['Venda']
        df = df[df['Avaliacao'] > 0]
        
        df['Texto'] = df.apply(lambda x: ' '.join(x.astype(str)).lower(), axis=1)
        df['Situacao'] = df['Texto'].apply(lambda x: 'Ocupado' if 'ocupado' in x and 'desocupado' not in x else ('Desocupado' if 'desocupado' in x else 'Indefinido'))
        
        col_tipo = next((c for c in df.columns if 'tipo' in c and 'venda' not in c), None)
        df['Tipo'] = df[col_tipo].str.split(',').str[0].str.upper().str.strip() if col_tipo else "IMÓVEL"
        
        return df, "Sucesso"
    except Exception as e:
        return None, str(e)

# --- INTERFACE ---
st.title("🤖 Rastreador Automático de Leilões")
st.markdown("Monitorando oportunidades direto da Caixa.")

with st.sidebar:
    st.header("⚙️ Controle")
    estado = st.selectbox("Escolha o Estado", ["SP", "RJ", "MG", "PR", "SC", "RS", "BA", "GO", "DF"])
    
    if st.button("🔄 ATUALIZAR DADOS AGORA"):
        st.cache_data.clear() # Força baixar de novo
        
    st.divider()
    st.header("🔍 Filtros")
    df, msg = baixar_dados(estado)
    
    if df is not None:
        cidades = ["Todas"] + sorted(df.iloc[:,0].unique().tolist()) # Assume cidade na col 1 ou acha pelo nome
        col_cidade = next((c for c in df.columns if 'cidade' in c), df.columns[0])
        cidades = ["Todas"] + sorted(df[col_cidade].dropna().unique().tolist())
        
        sel_cidade = st.selectbox("Cidade", cidades)
        sel_tipo = st.selectbox("Tipo", ["Todas"] + sorted(df['Tipo'].unique().tolist()))
        sel_sit = st.selectbox("Ocupação", ["Todas", "Ocupado", "Desocupado"])
        max_price = st.number_input("Preço Máximo", value=0)
        min_desc = st.slider("Desconto Mínimo (%)", 0, 95, 40)
        bairro_busca = st.text_input("Bairro")
    else:
        st.error(msg)

# --- RESULTADOS ---
if df is not None:
    # Aplicar Filtros
    filtro = df.copy()
    if sel_cidade != "Todas": filtro = filtro[filtro[col_cidade] == sel_cidade]
    if sel_tipo != "Todas": filtro = filtro[filtro['Tipo'] == sel_tipo]
    if sel_sit != "Todas": filtro = filtro[filtro['Situacao'] == sel_sit]
    if max_price > 0: filtro = filtro[filtro['Venda'] <= max_price]
    if bairro_busca:
        col_bairro = next((c for c in df.columns if 'bairro' in c), None)
        if col_bairro: filtro = filtro[filtro[col_bairro].astype(str).str.contains(limpar_texto(bairro_busca), case=False)]
        
    filtro['Desconto'] = ((filtro['Avaliacao'] - filtro['Venda']) / filtro['Avaliacao']) * 100
    filtro = filtro[filtro['Desconto'] >= min_desc].sort_values('Desconto', ascending=False)
    
    st.subheader(f"Encontrados: {len(filtro)} imóveis")
    
    # Gerar Cards HTML
    html_cards = "<div class='card-container'>"
    base_url = "https://venda-imoveis.caixa.gov.br/sistema/detalhe-imovel.asp?hdnimovel="
    col_id = next((c for c in df.columns if 'numero' in c and 'imovel' in c), df.columns[0])
    col_bairro = next((c for c in df.columns if 'bairro' in c), 'Bairro')
    col_end = next((c for c in df.columns if 'endereco' in c), '')

    for _, row in filtro.head(50).iterrows():
        tipo_icon = "🏠" if "CASA" in row['Tipo'] else "🏢" if "APART" in row['Tipo'] else "🌳"
        badge_cor = "badge-red" if row['Situacao'] == 'Ocupado' else "badge-green" if row['Situacao'] == 'Desocupado' else "badge-gray"
        icone_sit = "⛔" if row['Situacao'] == 'Ocupado' else "✅" if row['Situacao'] == 'Desocupado' else "❓"
        link = base_url + str(row[col_id])
        maps = f"http://maps.google.com/?q={row[col_end]}, {row[col_cidade]}"
        
        html_cards += f"""
        <div class='imovel-card'>
            <div class='card-header'>
                <span class='card-city'>📍 {row[col_cidade]}</span>
                <span class='badge {badge_cor}'>{icone_sit} {row['Situacao']}</span>
            </div>
            <div class='card-body'>
                <div style='font-size:0.8rem; font-weight:bold; color:#64748b; margin-bottom:5px'>{tipo_icon} {row['Tipo']}</div>
                <div class='card-title'>{row[col_bairro]}</div>
                <a href='{maps}' target='_blank' style='font-size:0.8rem; color:#3b82f6;'>🗺️ {str(row[col_end])[:50]}...</a>
                
                <div class='price-box'>
                    <span class='discount-tag'>-{row['Desconto']:.0f}%</span>
                    <div style='font-size:0.8rem; color:#94a3b8; text-decoration:line-through'>R$ {row['Avaliacao']:,.2f}</div>
                    <div class='price-value'>R$ {row['Venda']:,.2f}</div>
                </div>
            </div>
            <a href='{link}' target='_blank' class='btn-action'>🔥 VER NO SITE</a>
        </div>
        """
    html_cards += "</div>"
    st.markdown(html_cards, unsafe_allow_html=True)

else:
    st.info("👈 Selecione o estado e clique em atualizar para começar.")
