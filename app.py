import streamlit as st
import pandas as pd
from PyPDF2 import PdfReader
from datetime import datetime, timedelta

st.set_page_config(layout="wide")

# --- CONFIG ---
DATA_INIZIO = datetime(2025, 5, 1)
DATA_FINE = datetime(2025, 6, 30)

# --- FUNZIONI ---

@st.cache_data
def carica_anagrafica():
    df = pd.read_excel("Arbitri.xlsx")
    df.columns = df.columns.str.strip()
    df["Cod.Mecc."] = df["Cod.Mecc."].astype(str).str.strip()
    return df

@st.cache_data
def carica_gare(file_excel):
    df = pd.read_excel(file_excel, header=None)
    df = df.rename(columns={
        1: "NumGara",
        2: "Categoria",
        3: "Girone",
        6: "DataGara",
        16: "Ruolo",
        17: "Cod.Mecc."
    })
    df["Cod.Mecc."] = df["Cod.Mecc."].astype(str).str.strip()
    df["NumGara"] = df["NumGara"].astype(str).str.strip()
    df["DataGara"] = pd.to_datetime(df["DataGara"], errors="coerce")
    return df[["Cod.Mecc.", "NumGara", "DataGara", "Categoria", "Girone", "Ruolo"]]

@st.cache_data
def carica_voti(file_pdf):
    reader = PdfReader(file_pdf)
    text = ""
    for page in reader.pages:
        text += page.extract_text()

    records = []
    for line in text.split("\n"):
        parts = line.strip().split()
        if len(parts) >= 6 and parts[0].isdigit():
            numgara = parts[0]
            try:
                voto_oa = float(parts[-2].replace(",", "."))
                voto_ot = float(parts[-1].replace(",", "."))
                records.append({"NumGara": numgara, "Voto OA": voto_oa, "Voto OT": voto_ot})
            except:
                continue

    df = pd.DataFrame(records)
    df["NumGara"] = df["NumGara"].astype(str).str.strip()
    return df

@st.cache_data
def carica_indisponibili(file_excel):
    df = pd.read_excel(file_excel)
    df.columns = df.columns.str.strip()
    df["Cod.Mecc."] = df["Cod.Mecc."].astype(str).str.strip()
    df["Inizio"] = pd.to_datetime(df["Inizio"], errors="coerce")
    df["Fine"] = pd.to_datetime(df["Fine"], errors="coerce")
    df["Motivo"] = df["Motivo"].astype(str)
    return df

def settimana_da_data(data):
    delta = data - DATA_INIZIO
    return (delta.days // 7) + 1

def genera_settimane():
    settimane = []
    data = DATA_INIZIO
    while data <= DATA_FINE:
        fine = data + timedelta(days=6)
        settimane.append((data, fine))
        data += timedelta(days=7)
    return settimane

# --- MAIN ---

st.title("Gestione Arbitri - Gare, Voti, Indisponibilità")

# Upload
gare_file = st.file_uploader("📥 Carica file CRA01 (.xlsx)", type=["xlsx"])
voti_file = st.file_uploader("📥 Carica file Voti (.pdf)", type=["pdf"])
indisponibili_file = st.file_uploader("📥 Carica file Indisponibilità (.xlsx)", type=["xlsx"])

# Caricamento dati
df_arbitri = carica_anagrafica()
df_gare = carica_gare(gare_file) if gare_file else pd.DataFrame()
df_voti_raw = carica_voti(voti_file) if voti_file else pd.DataFrame()
df_indisp = carica_indisponibili(indisponibili_file) if indisponibili_file else pd.DataFrame()

# Merge gare + voti
if not df_gare.empty and not df_voti_raw.empty:
    df_gare = df_gare.copy()
    df_gare["NumGara"] = df_gare["NumGara"].astype(str).str.strip()
    df_merged = pd.merge(df_gare, df_voti_raw, on="NumGara", how="left")
else:
    df_merged = df_gare.copy()

# Settimane
settimane = genera_settimane()
settimane_labels = [f"Sett. {i+1}\n{d1.strftime('%d/%m')} - {d2.strftime('%d/%m')}" for i, (d1, d2) in enumerate(settimane)]

# Visualizzazione
for _, arbitro in df_arbitri.iterrows():
    cod_mecc = arbitro["Cod.Mecc."]
    st.markdown(f"### {arbitro['Cognome']} {arbitro['Nome']} ({cod_mecc})")
    col1, col2 = st.columns(2)
    col1.markdown(f"**Sezione:** {arbitro['Sezione']}")
    col2.markdown(f"**Età:** {arbitro['Età']}")

    sett_row = []
    for i, (inizio, fine) in enumerate(settimane):
        gare_sett = df_merged[
            (df_merged["Cod.Mecc."] == cod_mecc) &
            (df_merged["DataGara"] >= inizio) & (df_merged["DataGara"] <= fine)
        ]

        indisps = df_indisp[
            (df_indisp["Cod.Mecc."] == cod_mecc) &
            (df_indisp["Inizio"] <= fine) & (df_indisp["Fine"] >= inizio)
        ]

        testo = ""
        for _, gara in gare_sett.iterrows():
            cat = gara["Categoria"]
            girone = str(gara["Girone"]).strip()[-1:]  # solo la lettera
            ruolo = gara["Ruolo"]
            voto_oa = gara.get("Voto OA", "")
            voto_ot = gara.get("Voto OT", "")
            riga = f"{cat} – {girone} – {ruolo}"
            if pd.notna(voto_oa):
                riga += f" – OA: {voto_oa:.2f}"
            if pd.notna(voto_ot):
                riga += f" OT: {voto_ot:.2f}"
            testo += riga + "\n"

        for _, row in indisps.iterrows():
            testo += f"🚫 {row['Motivo']}\n"

        if testo.strip() == "":
            testo = "-"
        sett_row.append(testo.strip())

    df_sett = pd.DataFrame([sett_row], columns=settimane_labels, index=[""])
    st.dataframe(df_sett, use_container_width=True)
