import streamlit as st
import pandas as pd
from thefuzz import process, fuzz
import io
import re

st.set_page_config(page_title="Funko SKU Validator PRO", layout="wide")

# Fungsi untuk membersihkan SKU agar pembandingan akurat
def clean_sku(sku):
    if pd.isna(sku): return ""
    # Menghapus spasi dan karakter non-alfanumerik, lalu buat huruf besar
    return re.sub(r'[^a-zA-Z0-9]', '', str(sku)).upper()

@st.cache_data
def load_master_data(url):
    csv_url = url.replace('/edit?usp=sharing', '/export?format=csv')
    df = pd.read_csv(csv_url)
    # Bersihkan SKU Master saat load
    df['SKU_CLEAN'] = df['SKU'].apply(clean_sku)
    return df

st.title("🧸 Funko Pop SKU Validator (High Accuracy)")

master_url = "https://docs.google.com/spreadsheets/d/18CGqEdAxexoCNNFBJ9v3xgQBNm7h8ph7-phzz0jo1uA/edit?usp=sharing"

try:
    df_master = load_master_data(master_url)
    st.success(f"✅ Master Database Terhubung ({len(df_master)} data)")
except Exception as e:
    st.error(f"Gagal memuat Master Data: {e}")

file_ai = st.file_uploader("Upload Data B (Hasil AI)", type=['xlsx', 'csv'])

if file_ai and 'df_master' in locals():
    df_ai = pd.read_excel(file_ai) if file_ai.name.endswith('.xlsx') else pd.read_csv(file_ai)
    
    results = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for index, row in df_ai.iterrows():
        nama_asli_ai = str(row.get('NAMA PRODUK', row.get('Nama Produk', '')))
        sku_ai_raw = str(row.get('SKU', ''))
        sku_ai_clean = clean_sku(sku_ai_raw)

        # 1. Cari kecocokan Nama di Master
        match_result = process.extractOne(
            nama_asli_ai, 
            df_master['Nama Produk'].tolist(), 
            scorer=fuzz.token_set_ratio
        )
        
        if match_result:
            match_name_master, score = match_result[0], match_result[1]
            # Ambil data master yang cocok
            row_master = df_master[df_master['Nama Produk'] == match_name_master].iloc[0]
            sku_master_raw = str(row_master['SKU'])
            sku_master_clean = row_master['SKU_CLEAN']
            
            # 2. Logika Validasi SKU yang Lebih Fleksibel
            # Cek apakah SKU AI ada di Master (setelah dibersihkan)
            is_match = (sku_ai_clean == sku_master_clean)
            
            if is_match:
                verifikasi = "✅ SKU SESUAI"
            else:
                verifikasi = f"❌ SALAH (Master: {sku_master_raw})"
            
            status_match = "PERFECT" if score == 100 else "HIGH" if score >= 80 else "LOW MATCH"
        else:
            score, status_match, verifikasi = 0, "NOT FOUND", "❌ TIDAK DITEMUKAN"

        results.append({
            "NAMA PRODUK": nama_asli_ai,
            "SKU (AI)": sku_ai_raw,
            "Match Score": score,
            "Match Status": status_match,
            "VERIFIKASI SKU MASTER": verifikasi
        })
        
        progress_bar.progress((index + 1) / len(df_ai))
        status_text.text(f"Memproses: {int((index+1)/len(df_ai)*100)}%")

    df_final = pd.DataFrame(results)
    st.dataframe(df_final, use_container_width=True)

    # Export
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_final.to_excel(writer, index=False, sheet_name='Validasi')
    st.download_button("📥 Download Hasil Verifikasi", output.getvalue(), "Hasil_Validasi.xlsx")
