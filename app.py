import streamlit as st
import pandas as pd
from thefuzz import process, fuzz
import io
import re

st.set_page_config(page_title="Funko SKU Validator - All Floors", layout="wide")

# 1. Fungsi Pembersihan SKU (Anti-Gagal)
def clean_sku_final(sku):
    if pd.isna(sku) or sku == "":
        return ""
    # Menghilangkan .0 jika terbaca sebagai float, hapus spasi, dan karakter non-alfanumerik
    sku_clean = str(sku).split('.')[0]
    return re.sub(r'[^a-zA-Z0-9]', '', sku_clean).upper()

# 2. Load Master Data dari Semua Tab (Lantai 2, 3, 4)
@st.cache_data
def load_all_floors(base_url):
    # ID Spreadsheet dari link Anda
    sheet_id = "18CGqEdAxexoCNNFBJ9v3xgQBNm7h8ph7-phzz0jo1uA"
    
    # Nama-nama tab yang akan diambil
    tabs = ["lantai 2", "lantai 3", "lantai 4"]
    all_data = []
    
    for tab in tabs:
        # Format URL untuk mengambil tab spesifik sebagai CSV
        tab_name_escaped = tab.replace(" ", "%20")
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={tab_name_escaped}"
        
        try:
            df_tab = pd.read_csv(url)
            # Pastikan kolom yang diambil adalah Nama Produk dan SKU
            if 'Nama Produk' in df_tab.columns and 'SKU' in df_tab.columns:
                df_tab = df_tab[['Nama Produk', 'SKU']]
                all_data.append(df_tab)
                st.sidebar.write(f"✅ Tab {tab} berhasil dimuat ({len(df_tab)} baris)")
        except Exception as e:
            st.sidebar.error(f"Gagal memuat tab {tab}: {e}")
            
    # Gabungkan semua tab menjadi satu Master
    if all_data:
        master_combined = pd.concat(all_data, ignore_index=True)
        master_combined['SKU_CLEAN'] = master_combined['SKU'].apply(clean_sku_final)
        return master_combined
    return None

st.title("🧸 Funko Pop SKU Validator (Multi-Floor Engine)")

master_url = "https://docs.google.com/spreadsheets/d/18CGqEdAxexoCNNFBJ9v3xgQBNm7h8ph7-phzz0jo1uA/edit?usp=sharing"

df_master = load_all_floors(master_url)

if df_master is not None:
    st.sidebar.success(f"Total Database Gabungan: {len(df_master)} Baris")
else:
    st.error("Gagal menggabungkan data lantai. Periksa koneksi internet atau nama tab.")

# 3. Upload Data AI (Data B)
file_ai = st.file_uploader("Upload Data B (Hasil AI - 7rb+ data)", type=['xlsx', 'csv'])

if file_ai and df_master is not None:
    # Membaca file AI
    if file_ai.name.endswith('.xlsx'):
        df_ai = pd.read_excel(file_ai, engine='openpyxl')
    else:
        df_ai = pd.read_csv(file_ai)
    
    total_rows = len(df_ai)
    st.info(f"Mendeteksi **{total_rows}** baris dalam file yang Anda upload.")
    
    if st.button("Mulai Validasi Seluruh Lantai"):
        results = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        master_names = df_master['Nama Produk'].astype(str).tolist()

        for i in range(total_rows):
            row = df_ai.iloc[i]
            
            # AMBIL NAMA ASLI (TIDAK DIUBAH)
            nama_ai = str(row.get('NAMA PRODUK', row.get('Nama Produk', '')))
            sku_ai_raw = str(row.get('SKU', ''))
            sku_ai_clean = clean_sku_final(sku_ai_raw)

            # Matching terhadap database gabungan (Lantai 2, 3, 4)
            match_result = process.extractOne(nama_ai, master_names, scorer=fuzz.token_set_ratio)
            
            if match_result:
                best_match_name, score = match_result[0], match_result[1]
                master_row = df_master[df_master['Nama Produk'] == best_match_name].iloc[0]
                sku_master_raw = str(master_row['SKU']).split('.')[0]
                sku_master_clean = master_row['SKU_CLEAN']
                
                # Validasi SKU
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
                "NAMA PRODUK": nama_ai, # Tetap nama asli Anda
                "SKU (AI)": sku_ai_raw,
                "Match Score": score,
                "Match Status": status_match,
                "VERIFIKASI SKU MASTER": verifikasi
            })
            
            if i % 100 == 0:
                progress_bar.progress((i + 1) / total_rows)
                status_text.text(f"Memproses baris ke-{i+1} dari {total_rows}...")

        df_final = pd.DataFrame(results)
        st.success(f"Selesai! Berhasil memproses {len(df_final)} baris data.")
        st.dataframe(df_final, use_container_width=True)

        # 4. Export
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_final.to_excel(writer, index=False, sheet_name='Hasil_Validasi_Semua_Lantai')
        
        st.download_button(
            label="📥 Download Hasil Verifikasi Lengkap",
            data=output.getvalue(),
            file_name="Hasil_Validasi_Funko_Lantai_234.xlsx",
            mime="application/vnd.ms-excel"
        )
