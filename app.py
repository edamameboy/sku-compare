import streamlit as st
import pandas as pd
from thefuzz import process, fuzz
import io

st.set_page_config(page_title="Funko SKU Validator", layout="wide")

st.title("🧸 Funko Pop SKU Validator (Format Optimized)")

# 1. Load Master Data dari Link Google Sheets yang Anda berikan
@st.cache_data
def load_master_data(url):
    csv_url = url.replace('/edit?usp=sharing', '/export?format=csv')
    return pd.read_csv(csv_url)

master_url = "https://docs.google.com/spreadsheets/d/18CGqEdAxexoCNNFBJ9v3xgQBNm7h8ph7-phzz0jo1uA/edit?usp=sharing"

try:
    # Mengambil kolom Nama Produk dan SKU dari master
    df_master = load_master_data(master_url)
    st.success("✅ Terhubung ke Master Database")
except Exception as e:
    st.error(f"Gagal memuat Master Data: {e}")

# 2. Upload Data AI
file_ai = st.file_uploader("Upload Data Hasil AI (Excel/CSV)", type=['xlsx', 'csv'])

if file_ai and 'df_master' in locals():
    if file_ai.name.endswith('.csv'):
        df_ai = pd.read_csv(file_ai)
    else:
        df_ai = pd.read_excel(file_ai)
    
    results = []
    st.info("Memproses validasi berdasarkan format Master Reference...")

    for index, row in df_ai.iterrows():
        # Ambil nama yang diinput AI (asumsi kolom bernama 'Nama Produk' atau 'NAMA PRODUK')
        nama_ai = str(row.get('NAMA PRODUK', row.get('Nama Produk', '')))
        sku_ai = str(row.get('SKU', ''))

        # Cari kemiripan di Master (Tanpa merubah nama asli di master)
        # Menggunakan scorer token_set_ratio agar fleksibel terhadap urutan kata
        match_result = process.extractOne(
            nama_ai, 
            df_master['Nama Produk'].tolist(), 
            scorer=fuzz.token_set_ratio
        )
        
        if match_result:
            match_name, score = match_result[0], match_result[1]
            sku_master = df_master[df_master['Nama Produk'] == match_name]['SKU'].values[0]
            
            # Tentukan Match Status sesuai format file Anda
            if score == 100:
                status = "PERFECT"
            elif score >= 80:
                status = "HIGH"
            elif score > 0:
                status = "LOW MATCH (Check!)"
            else:
                status = "NOT FOUND"
        else:
            match_name, score, sku_master, status = "", 0, "", "NOT FOUND"

        results.append({
            "NAMA PRODUK": match_name, # Tetap menggunakan nama dari Master
            "SKU": sku_master,         # SKU yang seharusnya dari Master
            "Match Score": score,
            "Match Status": status
        })

    # Tampilkan Hasil
    df_final = pd.DataFrame(results)
    st.write("### Preview Hasil (Format Master Reference)")
    st.dataframe(df_final, use_container_width=True)

    # 3. Export ke Excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_final.to_excel(writer, index=False, sheet_name='Master_Reference')
    
    st.download_button(
        label="📥 Download Hasil (Sesuai Format Master_Reference)",
        data=output.getvalue(),
        file_name="Master_Reference_Output.xlsx",
        mime="application/vnd.ms-excel"
    )
