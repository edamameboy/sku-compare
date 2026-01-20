import streamlit as st
import pandas as pd
from thefuzz import process, fuzz
import io
import re

st.set_page_config(page_title="Funko SKU Validator - Ultra", layout="wide")

# 1. Fungsi Pembersihan SKU (Anti-Gagal)
def clean_sku_final(sku):
    if pd.isna(sku) or sku == "":
        return ""
    # Menghilangkan .0 jika terbaca sebagai float, hapus spasi, dan karakter aneh
    sku_clean = str(sku).split('.')[0]
    return re.sub(r'[^a-zA-Z0-9]', '', sku_clean).upper()

# 2. Load Master Data dari Link Google Sheets User
@st.cache_data
def load_master_data(url):
    # Mengonversi link view menjadi link download CSV
    csv_url = url.replace('/edit?usp=sharing', '/export?format=csv')
    df = pd.read_csv(csv_url)
    # Gunakan kolom sesuai file master user: 'Nama Produk' dan 'SKU'
    df['SKU_CLEAN'] = df['SKU'].apply(clean_sku_final)
    return df

st.title("🧸 Funko Pop SKU Validator (Full Data Engine)")

master_url = "https://docs.google.com/spreadsheets/d/18CGqEdAxexoCNNFBJ9v3xgQBNm7h8ph7-phzz0jo1uA/edit?usp=sharing"

try:
    df_master = load_master_data(master_url)
    st.sidebar.success(f"Master Database Loaded: {len(df_master)} items")
except Exception as e:
    st.sidebar.error(f"Error Master: {e}")

# 3. Upload Data AI (Data B)
file_ai = st.file_uploader("Upload Data B (Pastikan Excel/CSV berisi 7.000+ data)", type=['xlsx', 'csv'])

if file_ai:
    # Menggunakan engine='openpyxl' untuk xlsx agar pembacaan lebih stabil
    if file_ai.name.endswith('.xlsx'):
        df_ai = pd.read_excel(file_ai, engine='openpyxl')
    else:
        df_ai = pd.read_csv(file_ai)
    
    total_rows = len(df_ai)
    st.info(f"Sistem mendeteksi total: **{total_rows}** baris dalam file Anda.")
    
    if st.button("Mulai Proses Validasi Sekarang"):
        results = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Ambil list nama dari master untuk fuzzy matching
        master_names = df_master['Nama Produk'].astype(str).tolist()

        for i in range(total_rows):
            row = df_ai.iloc[i]
            
            # Ambil Nama & SKU dari file AI (TIDAK DIUBAH)
            nama_ai = str(row.get('NAMA PRODUK', row.get('Nama Produk', '')))
            sku_ai_raw = str(row.get('SKU', ''))
            sku_ai_clean = clean_sku_final(sku_ai_raw)

            # Cari kecocokan di master
            match_result = process.extractOne(nama_ai, master_names, scorer=fuzz.token_set_ratio)
            
            if match_result:
                best_match_name, score = match_result[0], match_result[1]
                # Cari baris di master yang sesuai dengan hasil match
                master_row = df_master[df_master['Nama Produk'] == best_match_name].iloc[0]
                sku_master_raw = str(master_row['SKU']).split('.')[0]
                sku_master_clean = master_row['SKU_CLEAN']
                
                # Cek Validitas SKU
                if sku_ai_clean == sku_master_clean and sku_ai_clean != "":
                    verifikasi = "✅ SKU SESUAI"
                elif sku_ai_clean == "":
                    verifikasi = "⚠️ SKU AI KOSONG"
                else:
                    verifikasi = f"❌ SALAH (Master: {sku_master_raw})"
                
                status_match = "PERFECT" if score == 100 else "HIGH" if score >= 80 else "LOW MATCH"
            else:
                score, status_match, verifikasi = 0, "NOT FOUND", "❌ TIDAK DITEMUKAN"

            results.append({
                "NAMA PRODUK": nama_ai,
                "SKU (AI)": sku_ai_raw,
                "Match Score": score,
                "Match Status": status_match,
                "VERIFIKASI SKU MASTER": verifikasi
            })
            
            # Update UI secara berkala
            if i % 100 == 0:
                progress_bar.progress((i + 1) / total_rows)
                status_text.text(f"Memproses data ke-{i+1} dari {total_rows}...")

        df_final = pd.DataFrame(results)
        st.success(f"Selesai! Berhasil memproses {len(df_final)} baris.")
        st.dataframe(df_final, use_container_width=True)

        # 4. Export ke Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_final.to_excel(writer, index=False, sheet_name='Hasil_Validasi')
        
        st.download_button(
            label="📥 Download Hasil Verifikasi (Lengkap)",
            data=output.getvalue(),
            file_name="Hasil_Validasi_Funko_Full.xlsx",
            mime="application/vnd.ms-excel"
        )
