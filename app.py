import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from PyPDF2 import PdfReader

st.set_page_config(layout="wide", page_title="Gestione Arbitri – Stagione 2025")

# 📅 Settimane stagione
DATA_INIZIO = datetime(2025, 5, 1)
DATA_FINE = datetime(2025, 6, 30)
SETTIMANE = pd.date_range(start=DATA_INIZIO, end=DATA_FINE, freq='W-MON') - timedelta(days=6)

# 📄 Carica anagrafica
@st.cache_data
def carica_anagrafica():
    df = pd.read_excel("Arbitri.xlsx")
    df["Cod.Mecc."] = df["Cod.Mecc."].apply(lambda x: str(int(float(x))).strip() if pd.notna(x) else "")
    return df

# 📄 Carica gare da Excel (senza intestazioni)
@st.cache_data
def carica_gare(file):
    df = pd.read_excel(file, header=None)
    df_gare = pd.DataFrame({
        "NumGara": df.iloc[:, 1],
        "Categoria": df.iloc[:, 2],
        "Girone": df.iloc[:, 3],
        "DataGara": pd.to_datetime(df.iloc[:, 6], errors="coerce"),
        "Ruolo": df.iloc[:, 16],
        "Cod.Mecc.": df.iloc[:, 17].apply(lambda x: str(int(float(x))).strip() if pd.notna(x) else "")
    })
    return df_gare

# 📄 Estrai voti da PDF
@st.cache_data
def estrai_voti_da_pdf(file):
    reader = PdfReader(file)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    lines = text.split("\n")

    records = []
    for line in lines:
        parts = line.split()
        if len(parts) >= 4:
            try:
                num_gara = int(parts[0])
                voto_oa = float(parts[-2].replace(",", "."))
                voto_ot = float(parts[-1].replace(",", "."))
                records.append({"NumGara": num_gara, "OA": voto_oa, "OT": voto_ot})
            except:
                continue
    return pd.DataFrame(records)

# 📄 Carica indisponibilità
@st.cache_data
def carica_indisponibili(file):
    df = pd.read_excel(file)
    df["Cod.Mecc."] = df["Cod.Mecc."].apply(lambda x: str(int(float(x))).strip() if pd.notna(x) else "")
    df["Inizio"] = pd.to_datetime(df["Inizio"], errors="coerce")
    df["Fine"] = pd.to_datetime(df["Fine"], errors="coerce")
    df["Motivo"] = df["Motivo"].astype(str)
    return df

# 📂 Upload file
st.title("📋 Gestione Arbitri – Stagione 2025")

col1, col2, col3 = st.columns(3)
with col1:
    gare_file = st.file_uploader("📄 Carica file GARE (cra01.xlsx)", type=["xlsx"])
with col2:
    voti_file = st.file_uploader("📄 Carica file VOTI (PDF)", type=["pdf"])
with col3:
    indisponibili_file = st.file_uploader("📄 Carica file INDISPONIBILITÀ", type=["xlsx"])

# 📦 Caricamento dati
df_arbitri = carica_anagrafica()
df_gare = carica_gare(gare_file) if gare_file else pd.DataFrame()
df_voti_raw = estrai_voti_da_pdf(voti_file) if voti_file else pd.DataFrame()
df_indisp = carica_indisponibili(indisponibili_file) if indisponibili_file else pd.DataFrame()

# 🧩 Merge gare + voti
if not df_voti_raw.empty and not df_gare.empty:
    df_merged = pd.merge(df_gare, df_voti_raw, on="NumGara", how="left")
else:
    df_merged = df_gare.copy()

# 📊 Visualizzazione
for _, arbitro in df_arbitri.iterrows():
    cod_mecc = arbitro["Cod.Mecc."]
    nominativo = arbitro["Nominativo"]
    sezione = arbitro["Sezione"]
    eta = int(arbitro["Età"]) if not pd.isna(arbitro["Età"]) else "-"
    
    with st.expander(f"{nominativo} ({cod_mecc})", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Sezione:** {sezione}")
        with col2:
            st.markdown(f"**Età:** {eta}")

        sett_cols = st.columns(len(SETTIMANE))

        for i, inizio_settimana in enumerate(SETTIMANE):
            fine_settimana = inizio_settimana + timedelta(days=6)
            settimana_label = f"{inizio_settimana.strftime('%d/%m')} - {fine_settimana.strftime('%d/%m')}"

            with sett_cols[i]:
                st.markdown(f"**{settimana_label}**")

                # ⚠️ Indisponibilità
                indisps = df_indisp[
                    (df_indisp["Cod.Mecc."] == cod_mecc) &
                    (df_indisp["Inizio"] <= fine_settimana) &
                    (df_indisp["Fine"] >= inizio_settimana)
                ]
                if not indisps.empty:
                    for _, row in indisps.iterrows():
                        st.markdown(f"<span style='color:red'>Indisponibile:<br>{row['Motivo']}</span>", unsafe_allow_html=True)

                # ✅ Gare e voti
                gare_sett = df_merged[
                    (df_merged["Cod.Mecc."] == cod_mecc) &
                    (df_merged["DataGara"] >= inizio_settimana) &
                    (df_merged["DataGara"] <= fine_settimana)
                ]

                if not gare_sett.empty:
                    for _, gara in gare_sett.iterrows():
                        cat_girone = f"{gara['Categoria']} – {gara['Girone']}"
                        ruolo = gara["Ruolo"]
                        voto_oa = f"OA: {gara['OA']:.2f}" if not pd.isna(gara['OA']) else "OA: -"
                        voto_ot = f"OT: {gara['OT']:.2f}" if not pd.isna(gara['OT']) else "OT: -"
                        st.markdown(f"{cat_girone} – {ruolo} – {voto_oa} {voto_ot}")
                elif indisps.empty:
                    st.markdown("<span style='color:#999'>–</span>", unsafe_allow_html=True)
