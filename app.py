import streamlit as st
import pandas as pd
import requests
import io

st.set_page_config(page_title="Leilão Caixa Básico", layout="wide")

# --- CSS SIMPLES ---
st.markdown("""
<style>
    .card { background: white; padding: 20px; border-radius: 10px; border: 1px solid #ddd; margin-bottom: 15px; }
    .price { font-size: 1.5rem; font-weight: bold; color: #1e293b; }
    .btn { display: inline-block; background: #2563eb; color: white !important; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin-top: 10px; }
</style>
""", unsafe_allow_html=True)

# --- CARREGAMENTO DE DADOS ---
@st.cache_data
def carregar(uf):
    # Link oficial da Caixa
    url = f"https://venda-imoveis.caixa.gov.br/listaweb/Lista_imoveis_{uf}.csv"
    
    try:
        # 1. Baixar
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        
        # 2. Ler CSV (Pula a primeira linha que é cabeçalho inútil)
        # O encoding 'latin1' é obrigatório para arquivos do governo no Brasil
        df = pd.read_csv(io.StringIO(r.content.decode('latin1')), sep=';', skiprows=1)
        
        # 3. Limpar nomes das colunas (tudo minúsculo para facilitar)
        df.columns = [c.lower().strip() for c in df.columns]
        
        return df
    except:
        return None

# --- APP ---
st.title("🏡 Leilão Caixa - Versão 1.0")

uf = st.selectbox("Escolha o Estado:", ["SP", "RJ", "MG", "PR", "SC", "RS"])
df = carregar(uf)

if df is not None:
    # Tenta achar a coluna de Cidade
    col_cidade = next((c for c in df.columns if 'cidade' in c), None)
    
    if col_cidade:
        # Filtro de Cidade
        cidades = sorted(df[col_cidade].unique())
        cidade_sel = st.selectbox("Filtrar Cidade:", ["Todas"] + cidades)
        
        if cidade_sel != "Todas":
            df = df[df[col_cidade] == cidade_sel]
            
        st.write(f"**{len(df)} imóveis encontrados.**")
        
        # Procura colunas essenciais
        col_bairro = next((c for c in df.columns if 'bairro' in c), '')
        col_endereco = next((c for c in df.columns if 'endereco' in c), '')
        col_preco = next((c for c in df.columns if 'valor' in c or 'preco' in c), '')
        col_id = next((c for c in df.columns if 'numero' in c and 'imovel' in c), '')

        # Mostra os primeiros 50
        for index, row in df.head(50).iterrows():
            bairro = row[col_bairro] if col_bairro else "Bairro não informado"
            end = row[col_endereco] if col_endereco else "---"
            preco = row[col_preco] if col_preco else "R$ 0,00"
            link = f"https://venda-imoveis.caixa.gov.br/sistema/detalhe-imovel.asp?hdnimovel={row[col_id]}"
            
            st.markdown(f"""
            <div class="card">
                <h3>{bairro}</h3>
                <p>📍 {end}</p>
                <div class="price">R$ {preco}</div>
                <a href="{link}" target="_blank" class="btn">Ver na Caixa</a>
            </div>
            """, unsafe_allow_html=True)
            
    else:
        st.error("Erro: Não achei a coluna de Cidade no arquivo da Caixa.")
else:
    st.error("Não foi possível baixar a lista agora. Tente outro estado.")
