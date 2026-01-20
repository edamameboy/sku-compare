import streamlit as st
import pandas as pd
from thefuzz import process, fuzz
import io

# Konfigurasi Halaman
st.set_page_config(page_title="Funko SKU Validator", layout="wide")

st.title("🧸 Funko Pop SKU Validator")
st.subheader("Validasi Data AI terhadap Master Database Gudang")

# 1. Fungsi Mengambil Master Data dari Google Sheets (Public Link)
def load_master_data(url):
    # Mengubah link edit menjadi link export csv
    csv_url = url.replace('/edit?usp=sharing', '/export?format=csv')
    return pd.read_csv(csv_url)

# URL dari user
master_url = "https://docs.google.com/spreadsheets/d/18CGqEdAxexoCNNFBJ9v3xgQBNm7h8ph7-phzz0jo1uA/edit?usp=sharing"

try:
    df_master = load_master_data(master_url)
    st.success("✅ Berhasil terhubung ke Master Database (Google Sheets)")
except Exception as e:
    st.error(f"Gagal memuat Master Data: {e}")

# 2. Upload Data B (Excel dari AI)
uploaded_file = st.file_uploader("Upload File Excel Hasil AI (Data B)", type=["xlsx"])

if uploaded_file and 'df_master' in locals():
    df_ai = pd.read_excel(uploaded_file)
    
    st.info("Memulai proses perbandingan... Harap tunggu.")
    
    results = []
    
    # Progres bar untuk UX
    progress_bar = st.progress(0)
    total_rows = len(df_ai)

    for index, row in df_ai.iterrows():
        # Ambil input dari AI (Sesuaikan nama kolom di file Excel Anda)
        nama_ai = str(row.get('Nama Produk', '')) 
        sku_ai = str(row.get('SKU', ''))
        
        # Cari kemiripan nama terbaik di Master 
        match, score = process.extractOne(
            nama_ai, 
            df_master['Nama Produk'].tolist(), 
            scorer=fuzz.token_set_ratio
        )
        
        # Ambil SKU asli dari Master berdasarkan nama yang cocok 
        sku_master = df_master[df_master['Nama Produk'] == match]['SKU'].values[0]
        
        # Logika Validasi
        is_sku_match = (sku_ai.strip().upper() == str(sku_master).strip().upper())
        
        status = "✅ VALID" if is_sku_match and score > 90 else "⚠️ PERLU CEK"
        if not is_sku_match:
            keterangan = f"SKU Salah. Seharusnya: {sku_master}"
        elif score < 85:
            keterangan = "Nama tidak terlalu mirip, pastikan item sama."
        else:
            keterangan = "Data Akurat"

        results.append({
            "Nama dari AI": nama_ai,
            "SKU dari AI": sku_ai,
            "Nama di Master (Cocok)": match,
            "SKU di Master": sku_master,
            "Score Kemiripan": f"{score}%",
            "Status": status,
            "Rekomendasi": keterangan
        })
        
        progress_bar.progress((index + 1) / total_rows)

    # Tampilkan Hasil
    df_result = pd.DataFrame(results)
    st.write("### Hasil Perbandingan Data")
    st.dataframe(df_result, use_container_width=True)

    # 3. Export ke Excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_result.to_excel(writer, index=False, sheet_name='Hasil_Validasi_SKU')
    
    st.download_button(
        label="📥 Download Hasil Comparison (Excel)",
        data=output.getvalue(),
        file_name="hasil_validasi_funko.xlsx",
        mime="application/vnd.ms-excel"
    )
