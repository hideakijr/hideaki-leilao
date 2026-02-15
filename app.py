# --- NOVO EXTRATOR DE MEDIDAS E FOTOS ---
def extrair_medidas_detalhadas(texto):
    texto = str(texto).lower()
    # Tenta achar área privativa/construída
    area_c = re.search(r'privativa\s?=\s?([\d,.]+)', texto)
    # Tenta achar área do terreno
    area_t = re.search(r'terreno\s?=\s?([\d,.]+)', texto)
    
    cons = area_c.group(1).replace(',', '.') if area_c else "-"
    terr = area_t.group(1).replace(',', '.') if area_t else "-"
    
    return cons, terr

# No loop dos cards, vamos trocar a linha de medidas por:
# 🏠 Const: {r['Area_Const']}m² | 🌳 Terr: {r['Area_Terr']}m²
