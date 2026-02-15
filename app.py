import streamlit as st
import pandas as pd
import requests
import io
import unicodedata
import re

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Caça Leilão Pro", layout="wide", page_icon="💎")

# --- CSS (ESTILO ARREMATA) ---
st.markdown("""
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
    .status-badge { position: absolute; top: 45px; right: 15
