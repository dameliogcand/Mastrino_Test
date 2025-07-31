import streamlit as st
import pandas as pd
from PyPDF2 import PdfReader
from datetime import datetime, timedelta

st.set_page_config(layout="wide")

# Funzioni di caricamento

@st.cache_data
def carica_anagrafica():
    df = pd.read_excel("Arbitri.xlsx")
    df.columns = df.columns.str.strip()
    df["Cod.Mecc."] = df["Cod.Mecc."].astype(str).str.strip()
    return df

@st.cache_data
def carica_gare(file):
    df = pd.read_excel(file, header=None)
    df = df.rename(columns={
        1: "NumGara",
        2: "Categoria",
        3: "Girone",
        6: "DataGara",
        16: "Ruolo",
        17: "Cod.Mecc."
    })
    df = df[["Cod.Mecc.", "NumGara", "DataGara", "Categoria", "Girone", "Ruolo"]]
    df["Cod.Mecc."] = df["Cod.Mecc."].astype(str).str.strip()
    df["NumGara"] = df["NumGara"].astype(str).str.strip()
    df["DataGara"] = pd.to_datetime(df["DataGara"], errors="coerce")
    return df

@st.cache_data
def carica_indisponibili(file):
    df = pd.read_excel(file)
    df.columns = df.columns.str.strip()
    df["Cod.Mecc."] = df["Cod.Mecc."].astype(str).str.strip()
    df["Inizio"] = pd.to_datetime(df["Inizio"], errors='coerce')
    df["Fine"] = pd.to_datetime(df["Fine"], errors='coerce')
    df["Motivo"] = df["Motivo"].astype(str)
    return df

@st.cache_data
def estrai_voti_da_pdf(pdf_file):
    reader = PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    righe = text.split("\n")

    voti = []
    for riga in righe:
        parti = riga.split()
        if len(parti) >= 3:
            numgara = parti[0]
            try:
                oa = float(parti[-2].replace(",", "."))
                ot = float(parti[-1].replace(",", "."))
                voti.append({"NumGara": numgara, "OA": oa, "OT": ot})
            except:
                continue
    df_voti = pd.DataFrame(voti)
    df_voti["NumGara"] = df_voti["NumGara"].astype(str).str.strip()
    return df_voti

# Interfaccia

st.title("📋 Gestione Arbitri – Visualizzazione settimanale")

with st.sidebar:
    gare_file = st.file_uploader("📥 Carica il file CRA01 (Excel)", type=["xlsx"])
    voti_file = st.file_uploader("📥 Carica il PDF Voti OA/OT", type=["pdf"])
    indisponibili_file = st.file_uploader("📥 Carica il file Indisponibili (Excel)", type=["xlsx"])

# Caricamento dati
df_arbitri = carica_anagrafica()
df_gare = carica_gare(gare_file) if gare_file else pd.DataFrame()
df_voti_raw = estrai_voti_da_pdf(voti_file) if voti_file else pd.DataFrame()
df_indisp = carica_indisponibili(indisponibili_file) if indisponibili_file else pd.DataFrame()

# Merge gare + voti
df_merged = pd.merge(df_gare, df_voti_raw, on="NumGara", how="left")
if "Cod.Mecc." not in df_merged.columns:
    st.error("❌ Colonna 'Cod.Mecc.' mancante nel dataframe gare.")
    st.stop()

# Settimane calcistiche
start = datetime(2025, 5, 1)
end = datetime(2025, 6, 30)
settimane = []
current = start
while current <= end:
    fine = current + timedelta(days=6)
    settimane.append((current, fine))
    current = fine + timedelta(days=1)

# Visualizzazione
for _, arbitro in df_arbitri.iterrows():
    cod_mecc = arbitro["Cod.Mecc."]
    with st.expander(f"{arbitro['Cognome']} {arbitro['Nome']} ({cod_mecc})"):
        col1, col2, col3 = st.columns(3)
        col1.markdown(f"**Sezione:** {arbitro['Sezione']}")
        col2.markdown(f"**Età:** {arbitro['Età']}")

        for inizio, fine in settimane:
            col = st.columns(1)[0]
            settimana_label = f"🗓 {inizio.strftime('%d/%m')} – {fine.strftime('%d/%m')}"
            settimana_df = df_merged[
                (df_merged["Cod.Mecc."] == cod_mecc) &
                (df_merged["DataGara"] >= inizio) &
                (df_merged["DataGara"] <= fine)
            ]

            testo = ""
            for _, gara in settimana_df.iterrows():
                cat = gara["Categoria"]
                gir = gara["Girone"]
                ruolo = gara["Ruolo"]
                oa = f"OA: {gara['OA']:.2f}" if pd.notna(gara['OA']) else "OA: –"
                ot = f"OT: {gara['OT']:.2f}" if pd.notna(gara['OT']) else "OT: –"
                testo += f"**{cat} – {gir} – {ruolo}**  \n{oa} {ot}\n\n"

            # Indisponibilità
            indisps = df_indisp[
                (df_indisp["Cod.Mecc."] == cod_mecc) &
                (df_indisp["Inizio"] <= fine) & (df_indisp["Fine"] >= inizio)
            ]
            for _, ind in indisps.iterrows():
                motivo = ind["Motivo"]
                testo += f"❌ *Indisp.*: {motivo}\n\n"

            if testo == "":
                testo = "—"

            col.markdown(f"**{settimana_label}**\n\n{testo}")
