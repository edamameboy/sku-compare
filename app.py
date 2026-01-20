import streamlit as st
import pandas as pd
from thefuzz import process, fuzz
import io
import time

st.set_page_config(page_title="Funko SKU Validator", layout="wide")

st.title("🧸 Funko Pop SKU Validator")
st.markdown("Aplikasi ini akan membandingkan data AI Anda dengan Master Database tanpa mengubah nama produk asli.")

# 1. Load Master Data (Database Utama)
@st.cache_data
def load_master_data(url):
    csv_url = url.replace('/edit?usp=sharing', '/export?format=csv')
    return pd.read_csv(csv_url)

master_url = "https://docs.google.com/spreadsheets/d/18CGqEdAxexoCNNFBJ9v3xgQBNm7h8ph7-phzz0jo1uA/edit?usp=sharing"

try:
    df_master = load_master_data(master_url)
    st.success("✅ Master Database Terhubung")
except Exception as e:
    st.error(f"Gagal memuat Master Data: {e}")

# 2. Upload Data AI (Data B)
file_ai = st.file_uploader("Upload Data B (Hasil AI)", type=['xlsx', 'csv'])

if file_ai and 'df_master' in locals():
    if file_ai.name.endswith('.csv'):
        df_ai = pd.read_csv(file_ai)
    else:
        df_ai = pd.read_excel(file_ai)
    
    results = []
    
    # UI Progress
    st.write("### Memproses Data...")
    progress_text = st.empty()
    progress_bar = st.progress(0)
    
    total_rows = len(df_ai)

    for index, row in df_ai.iterrows():
        # AMBIL DATA ASLI DARI AI (TIDAK DIUBAH)
        nama_asli_ai = str(row.get('NAMA PRODUK', row.get('Nama Produk', '')))
        sku_ai = str(row.get('SKU', '')).strip()

        # Proses Mencari Match di Master untuk Validasi SKU
        match_result = process.extractOne(
            nama_asli_ai, 
            df_master['Nama Produk'].tolist(), 
            scorer=fuzz.token_set_ratio
        )
        
        if match_result:
            match_name_master, score = match_result[0], match_result[1]
            sku_master = str(df_master[df_master['Nama Produk'] == match_name_master]['SKU'].values[0]).strip()
            
            # Tentukan Match Status (Sesuai format Master_Reference)
            if score == 100: status_match = "PERFECT"
            elif score >= 80: status_match = "HIGH"
            elif score > 0: status_match = "LOW MATCH (Check!)"
            else: status_match = "NOT FOUND"
            
            # VALIDASI SKU (Kolom Paling Kanan)
            if sku_ai.upper() == sku_master.upper():
                verifikasi_sku = "✅ SKU SESUAI"
            else:
                verifikasi_sku = f"❌ TIDAK SESUAI (Master: {sku_master})"
        else:
            score = 0
            status_match = "NOT FOUND"
            verifikasi_sku = "❌ DATA TIDAK DITEMUKAN"

        # Simpan hasil dengan Nama Produk ASLI dari file AI
        results.append({
            "NAMA PRODUK": nama_asli_ai,  # NAMA TIDAK BERUBAH
            "SKU": sku_ai,               # SKU DARI AI
            "Match Score": score,
            "Match Status": status_match,
            "VERIFIKASI SKU MASTER": verifikasi_sku # TABEL BARU PALING KANAN
        })
        
        # Update Progress Bar
        percent_complete = int(((index + 1) / total_rows) * 100)
        progress_bar.progress(percent_complete)
        progress_text.text(f"Proses: {percent_complete}% ({index + 1}/{total_rows} baris)")

    # Tampilkan Hasil
    df_final = pd.DataFrame(results)
    st.write("### Hasil Akhir")
    st.dataframe(df_final, use_container_width=True)

    # 3. Export ke Excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_final.to_excel(writer, index=False, sheet_name='Hasil_Pengecekan')
    
    st.download_button(
        label="📥 Download Hasil Verifikasi (Excel)",
        data=output.getvalue(),
        file_name="Verifikasi_SKU_Funko.xlsx",
        mime="application/vnd.ms-excel"
    )
