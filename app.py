import streamlit as st
import pandas as pd
from datetime import datetime
from PyPDF2 import PdfReader
import io

st.set_page_config(layout="wide")

# ------------------------------
# FUNZIONI DI CARICAMENTO DATI
# ------------------------------

@st.cache_data
def carica_anagrafica():
    df = pd.read_excel("Arbitri.xlsx")
    df["Cod.Mecc."] = df["Cod.Mecc."].astype(str).str.replace(".0", "", regex=False).str.strip()
    df["Età"] = df["Età"].astype(str).str.strip()
    return df

@st.cache_data
def carica_gare(file):
    df = pd.read_excel(file, header=None)
    try:
        df = df[[1, 2, 3, 6, 16, 17]]  # Colonne B, C, D, G, Q, R
        df.columns = ["NumGara", "Categoria", "Girone", "DataGara", "Ruolo", "Cod.Mecc."]
        df["Cod.Mecc."] = df["Cod.Mecc."].astype(str).str.replace(".0", "", regex=False).str.strip()
        df["NumGara"] = df["NumGara"].astype(str).str.replace(".0", "", regex=False).str.strip()
        df["Settimana"] = pd.to_datetime(df["DataGara"], errors='coerce').dt.to_period("W").apply(lambda r: r.start_time)
        return df
    except Exception as e:
        st.error(f"Errore nel caricamento del file CRA01: {e}")
        st.stop()

@st.cache_data
def carica_voti(file):
    reader = PdfReader(file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    lines = text.splitlines()
    rows = []
    for line in lines:
        parts = line.strip().split()
        if len(parts) >= 3 and parts[0].isdigit():
            num_gara = parts[0]
            try:
                voto_oa = float(parts[-2].replace(",", "."))
                voto_ot = float(parts[-1].replace(",", "."))
            except:
                voto_oa = voto_ot = None
            rows.append({"NumGara": num_gara, "VotoOA": voto_oa, "VotoOT": voto_ot})
    df = pd.DataFrame(rows)
    df["NumGara"] = df["NumGara"].astype(str).str.replace(".0", "", regex=False).str.strip()
    return df

@st.cache_data
def carica_indisponibili(file):
    df = pd.read_excel(file)
    df["Cod.Mecc."] = df["Cod.Mecc."].astype(str).str.replace(".0", "", regex=False).str.strip()
    df["Inizio"] = pd.to_datetime(df["Inizio"], errors='coerce')
    df["Fine"] = pd.to_datetime(df["Fine"], errors='coerce')
    return df

# ------------------------------
# INTERFACCIA
# ------------------------------

st.title("Gestione Arbitri – Mastro")

# Upload dei file
col1, col2, col3 = st.columns(3)
with col1:
    gare_file = st.file_uploader("Carica file CRA01 (Excel)", type=["xlsx"])
with col2:
    voti_file = st.file_uploader("Carica file Voti (PDF)", type=["pdf"])
with col3:
    indisponibili_file = st.file_uploader("Carica file Indisponibili", type=["xlsx"])

# Caricamento dati
df_arbitri = carica_anagrafica()
df_gare = carica_gare(gare_file) if gare_file else pd.DataFrame()
df_voti_raw = carica_voti(voti_file) if voti_file else pd.DataFrame()
df_indisp = carica_indisponibili(indisponibili_file) if indisponibili_file else pd.DataFrame()

# Merge voti + gare tramite NumGara
if not df_voti_raw.empty and not df_gare.empty:
    df_merged = pd.merge(df_gare, df_voti_raw, on="NumGara", how="left")
else:
    df_merged = df_gare.copy()

# Settimane disponibili
all_weeks = pd.date_range(start="2025-05-01", end="2025-06-30", freq="W-MON")
settimane = [d.date() for d in all_weeks]

# ------------------------------
# VISUALIZZAZIONE PER ARBITRO
# ------------------------------

for _, arbitro in df_arbitri.iterrows():
    cod_mecc = str(arbitro["Cod.Mecc."]).strip()
    st.markdown("---")
    st.subheader(f"{arbitro['Cognome']} {arbitro['Nome']} ({cod_mecc})")
    col1, col2, col3 = st.columns(3)
    col1.markdown(f"**Sezione:** {arbitro['Sezione']}")
    col2.markdown(f"**Età:** {arbitro['Età']}")

    row = st.columns(len(settimane))
    for idx, sett in enumerate(settimane):
        contenuto = ""
        gare_sett = df_merged[
            (df_merged["Cod.Mecc."] == cod_mecc) &
            (pd.to_datetime(df_merged["Settimana"]).dt.date == sett)
        ]
        for _, gara in gare_sett.iterrows():
            categoria = gara["Categoria"]
            girone = gara["Girone"]
            ruolo = gara["Ruolo"]
            voto_oa = gara.get("VotoOA", "")
            voto_ot = gara.get("VotoOT", "")
            contenuto += f"{categoria} – {girone} – {ruolo}"
            if not pd.isna(voto_oa):
                contenuto += f"<br/>OA: {voto_oa:.2f}"
            if not pd.isna(voto_ot):
                contenuto += f"<br/>OT: {voto_ot:.2f}"
            contenuto += "<br/>"

        # Indisponibilità
        if not df_indisp.empty:
            for _, row_ind in df_indisp[df_indisp["Cod.Mecc."] == cod_mecc].iterrows():
                start, end, motivo = row_ind["Inizio"], row_ind["Fine"], row_ind["Motivo"]
                if start.date() <= sett <= end.date():
                    contenuto += f"<span style='color:red;'>INDISP. ({motivo})</span><br/>"

        if contenuto == "":
            contenuto = "–"
        row[idx].markdown(f"<div style='font-size: 12px'>{contenuto}</div>", unsafe_allow_html=True)
