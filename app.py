import streamlit as st
import pandas as pd
from thefuzz import process, fuzz
import io
import re

st.set_page_config(page_title="Funko SKU Validator - Full Data", layout="wide")

# Fungsi pembersih SKU yang lebih kuat
def clean_sku_robust(sku):
    if pd.isna(sku) or sku == "":
        return ""
    # Ubah ke string, hapus '.0' jika terbaca sebagai float excel
    sku_str = str(sku).replace('.0', '').strip()
    # Hanya ambil karakter alfanumerik & jadikan uppercase
    return re.sub(r'[^a-zA-Z0-9]', '', sku_str).upper()

@st.cache_data
def load_master_data(url):
    csv_url = url.replace('/edit?usp=sharing', '/export?format=csv')
    df = pd.read_csv(csv_url)
    # Simpan versi clean SKU di master untuk perbandingan cepat
    df['SKU_CLEAN'] = df['SKU'].apply(clean_sku_robust)
    return df

st.title("🧸 Funko Pop SKU Validator (Full 7k Data Check)")

master_url = "https://docs.google.com/spreadsheets/d/18CGqEdAxexoCNNFBJ9v3xgQBNm7h8ph7-phzz0jo1uA/edit?usp=sharing"

try:
    df_master = load_master_data(master_url)
    st.sidebar.success(f"Database Master: {len(df_master)} Baris")
except Exception as e:
    st.error(f"Gagal koneksi ke Google Sheets: {e}")

file_ai = st.file_uploader("Upload Data B (Pastikan file berisi 7rb+ baris)", type=['xlsx', 'csv'])

if file_ai and 'df_master' in locals():
    # Load data AI tanpa menghilangkan baris apapun
    df_ai = pd.read_excel(file_ai) if file_ai.name.endswith('.xlsx') else pd.read_csv(file_ai)
    total_rows = len(df_ai)
    st.sidebar.info(f"Data AI Terdeteksi: {total_rows} Baris")
    
    results = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Loop menggunakan index asli agar jumlah baris tidak berubah
    for i in range(total_rows):
        row = df_ai.iloc[i]
        
        # Ambil data asli (Nama & SKU dari AI)
        nama_ai = str(row.get('NAMA PRODUK', row.get('Nama Produk', '')))
        sku_ai_raw = str(row.get('SKU', ''))
        sku_ai_clean = clean_sku_robust(sku_ai_raw)

        # Proses Matching Nama
        match_result = process.extractOne(
            nama_ai, 
            df_master['Nama Produk'].tolist(), 
            scorer=fuzz.token_set_ratio
        )
        
        if match_result:
            match_name_master, score = match_result[0], match_result[1]
            row_master = df_master[df_master['Nama Produk'] == match_name_master].iloc[0]
            sku_master_raw = str(row_master['SKU'])
            sku_master_clean = row_master['SKU_CLEAN']
            
            # Validasi SKU
            if sku_ai_clean == "" or sku_master_clean == "":
                verifikasi = "⚠️ SKU KOSONG"
            elif sku_ai_clean == sku_master_clean:
                verifikasi = "✅ SKU SESUAI"
            else:
                verifikasi = f"❌ SALAH (Master: {sku_master_raw})"
            
            status_match = "PERFECT" if score == 100 else "HIGH" if score >= 80 else "LOW MATCH"
        else:
            score, status_match, verifikasi = 0, "NOT FOUND", "❌ TIDAK DITEMUKAN"

        # Simpan hasil (Urutan baris TETAP SAMA dengan file asli)
        results.append({
            "NAMA PRODUK (ASLI)": nama_ai,
            "SKU (AI)": sku_ai_raw,
            "Match Score": score,
            "Match Status": status_match,
            "VERIFIKASI SKU MASTER": verifikasi
        })
        
        # Update progress setiap 100 baris agar tidak lambat
        if i % 100 == 0 or i == total_rows - 1:
            progress_bar.progress((i + 1) / total_rows)
            status_text.text(f"Memproses baris ke-{i+1} dari {total_rows}...")

    df_final = pd.DataFrame(results)
    st.write(f"### Hasil Validasi ({len(df_final)} baris)")
    st.dataframe(df_final, use_container_width=True)

    # Export
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_final.to_excel(writer, index=False, sheet_name='Validasi_Full')
    
    st.download_button("📥 Download Hasil Verifikasi (7rb+ Baris)", output.getvalue(), "Hasil_Validasi_Lengkap.xlsx")
