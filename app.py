import streamlit as st
import pandas as pd
import requests
import io
import re

st.set_page_config(page_title="Caça Leilão Pro", layout="wide", page_icon="💎")

st.markdown("""
<style>
    .stApp { background-color: #f1f5f9; font-family: 'Segoe UI', sans-serif; }
    .card-container { display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 20px; padding: 20px; }
    .imovel-card { background: white; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); border: 1px solid #cbd5e1; overflow: hidden; display: flex; flex-direction: column; justify-content: space-between; }
    .header-dark { background: #1e293b; color: white; padding: 12px; display: flex; justify-content: space-between; align-items: center; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; }
    .badge-desc { background-color: #ef4444; color: white; padding: 4px 8px; border-radius: 4px; font-weight: 800; }
    .card-body { padding: 15px; color: #334155; }
    .meta-top { font-size: 0.75rem; color: #64748b; font-weight: 700; text-transform: uppercase; margin-bottom: 5px; }
    .card-title { font-size: 1.1rem; font-weight: 800; color: #0f172a; margin-bottom: 10px; height: 45px; overflow: hidden; }
    .features { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 15px; padding-bottom: 10px; border-bottom: 1px solid #f1f5f9; font-size: 0.85rem; font-weight: 600; color: #475569; }
    .analytics { display: flex; justify-content: space-between; font-size: 0.8rem; font-weight: bold; color: #059669; background: #ecfdf5; padding: 8px; border-radius: 6px; margin-bottom: 10px; }
    .map-btns { display: flex; gap: 5px; margin-bottom: 10px; }
    .btn-map { flex: 1; text-align: center; padding: 8px; border-radius: 6px; font-size: 0.75rem; font-weight: bold; text-decoration: none; color: white; }
    .g-map { background-color: #4285F4; }
    .w-map { background-color: #33ccff; color: #000; }
    .prices { background: #f8fafc; padding: 10px; border-radius: 8px; border: 1px solid #e2e8f0; }
    .p-val { font-size: 1.4rem; color: #1e293b; font-weight: 900; }
    .p-old { font-size: 0.8rem; color: #94a3b8; text-decoration: line-through; }
    .btn-go { background: #2563eb; color: white !important; text-align: center; padding: 12px; font-weight: 700; text-transform: uppercase; text-decoration: none; display: block; }
    .btn-go:hover { background: #1d4ed8; }
    .status { position: absolute; top: 45px; right: 15px; font-size: 0.7rem; padding: 3px 8px; border-radius: 20px; font-weight: 800; text-transform: uppercase; background: #f0fdf4; color: #166534; border: 1px solid #bbf7d0; }
    .occ { background: #fef2f2; color: #991b1b; border-color: #fecaca; }
</style>
""", unsafe_allow_html=True)

def limpar(t):
    return str(t).replace('R$','').replace('.','').replace(',','.').strip()

def get_medidas(row):
    txt = ' '.join(row.astype(str)).lower()
    q = re.search(r'(\d+)\s*(qto|quart)', txt)
    v = re.search(r'(\d+)\s*(vaga|garag)', txt)
    ac = re.search(r'(privativa|construida|util)\s*[:=]?\s*([\d,.]+)', txt)
    at = re.search(r'(terreno|total)\s*[:=]?\s*([\d,.]+)', txt)
    
    def n(m): 
        if not m: return 0
        try: return int(float(m.group(2).replace('.','').replace(',','.')))
        except: return 0
        
    return {'q': q.group(1) if q else "0", 'v': v.group(1) if v else "0", 'c': n(ac), 't': n(at)}

@st.cache_data(ttl=3600)
def load_data(uf):
    url = f"https://venda-imoveis.caixa.gov.br/listaweb/Lista_imoveis_{uf}.csv"
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        if r.status_code != 200: return None, "Erro Caixa"
        
        df = pd.read_csv(io.StringIO(r.content.decode('latin1')), sep=';', skiprows=1, on_bad_lines='skip')
        cols = {c: unicodedata.normalize('NFD', c).encode('ascii', 'ignore').decode('utf-8').lower() for c in df.columns}
        df.rename(columns=cols, inplace=True)
        
        col_v = next((c for c in df.columns if 'preco' in c or 'venda' in c), None)
        if not col_v: return None, "Erro Colunas"
        
        df['Venda'] = df[col_v].apply(lambda x: float(limpar(x)) if isinstance(x, str) else x)
        col_a = next((c for c in df.columns if 'avaliacao' in c), None)
        df['Avaliacao'] = df[col_a].apply(lambda x: float(limpar(x)) if isinstance(x, str) else x) if col_a else df['Venda']
        df = df[df['Avaliacao'] > 0].copy()
        
        df['Full'] = df.apply(lambda x: ' '.join(x.astype(str)).lower(), axis=1)
        df['Tipo'] = df['Full'].apply(lambda x: 'APTO' if 'apartamento' in x else ('CASA' if 'casa' in x else 'TERRENO'))
        df['Sit'] = df['Full'].apply(lambda x: 'OCUPADO' if 'ocupado' in x and 'desocupado' not in x else 'DESOCUPADO')
        
        m = df.apply(get_medidas, axis=1)
        df['Q'] = [x['q'] for x in m]
        df['V'] = [x['v'] for x in m]
        df['AC'] = [x['c'] for x in m]
        df['AT'] = [x['t'] for x in m]
        
        return df, "Ok"
    except Exception as e: return None, str(e)

st.title("💎 Arremata Clone 4.0")
with st.sidebar:
    st.header("Filtros")
    uf = st.selectbox("UF", ["SP", "RJ", "MG", "PR", "SC", "RS", "BA", "GO", "DF"])
    if st.button("Atualizar"): st.cache_data.clear()
    df, msg = load_data(uf)
    
    if df is not None:
        col_c = next((c for c in df.columns if 'cidade' in c), df.columns[0])
        cid = st.selectbox("Cidade", ["Todas"] + sorted(df[col_c].dropna().unique().tolist()))
        if cid != "Todas": df = df[df[col_c] == cid]
        
        max_p = st.number_input("Max R$", 0)
        if max_p > 0: df = df[df['Venda'] <= max_p]
        
        desc = st.slider("Desconto %", 0, 95, 40)
        df['Desc'] = ((df['Avaliacao'] - df['Venda']) / df['Avaliacao']) * 100
        df = df[df['Desc'] >= desc].sort_values('Desc', ascending=False)
    else: st.error(msg)

if df is not None:
    st.info(f"{len(df)} Imóveis")
    html = "<div class='card-container'>"
    base = "https://venda-imoveis.caixa.gov.br/sistema/detalhe-imovel.asp?hdnimovel="
    col_id = next((c for c in df.columns if 'numero' in c and 'imovel' in c), df.columns[0])
    col_end = next((c for c in df.columns if 'endereco' in c), '')
    col_b = next((c for c in df.columns if 'bairro' in c), '')

    for _, r in df.head(50).iterrows():
        end = f"{r[col_end]}, {r[col_b]}, {r[col_c]}".replace(" ", "+")
        m2 = r['Venda']/r['AC'] if r['AC'] > 0 else (r['Venda']/r['AT'] if r['AT'] > 0 else 0)
        
        feats = []
        if r['Q'] != "0": feats.append(f"🛏️ {r['Q']}")
        if r['AC'] > 0: feats.append(f"🏠 {r['AC']}m²")
        if r['AT'] > 0: feats.append(f"🌳 {r['AT']}m²")
        if r['V'] != "0": feats.append(f"🚗 {r['V']}")
        
        st_cls = 'status occ' if r['Sit'] == 'OCUPADO' else 'status'
        
        html += f"""
<div class='imovel-card'>
    <div class='header-dark'><span>ONLINE</span><span class='badge-desc'>-{r['Desc']:.0f}%</span></div>
    <div class='{st_cls}'>{r['Sit']}</div>
    <div class='card-body'>
        <div class='meta-top'>{r['Tipo']} • {r[col_c]}</div>
        <div class='card-title'>{r[col_b]}</div>
        <div class='features'>{' | '.join(feats) if feats else '⚠️ Ver Edital'}</div>
        <div class='analytics'><span>💰 Lucro: {(r['Avaliacao']-r['Venda']):,.0f}</span><span>📐 R$ {m2:,.0f}/m²</span></div>
        <div class='map-btns'>
            <a href='http://maps.google.com/?q={end}' target='_blank' class='btn-map g-map'>📍 Maps</a>
            <a href='https://waze.com/ul?q={end}' target='_blank' class='btn-map w-map'>🚙 Waze</a>
        </div>
        <div class='prices'>
            <div style='font-size:0.7rem;font-weight:bold;color:#64748b'>LANCE INICIAL</div>
            <div class='p-val'>R$ {r['Venda']:,.2f}</div>
            <div class='p-old'>Avaliação: R$ {r['Avaliacao']:,.2f}</div>
        </div>
    </div>
    <a href='{base + str(r[col_id])}' target='_blank' class='btn-go'>VER NA CAIXA</a>
</div>"""
    st.markdown(html + "</div>", unsafe_allow_html=True)
