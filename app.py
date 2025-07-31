import streamlit as st
import pandas as pd
from PyPDF2 import PdfReader
from datetime import datetime, timedelta

st.set_page_config(layout="wide")

# ---------------------- FUNZIONI ----------------------

@st.cache_data
def carica_anagrafica():
    df = pd.read_excel("Arbitri.xlsx")
    df.columns = df.columns.str.strip()
    df["Cod.Mecc."] = df["Cod.Mecc."].astype(str).str.strip()
    return df

@st.cache_data
def carica_gare(file):
    df = pd.read_csv(file, header=None)
    df = df[[1, 2, 3, 6, 16, 17]]
    df.columns = ["NumGara", "Categoria", "Girone", "DataGara", "Ruolo", "Cod.Mecc."]
    df["Cod.Mecc."] = df["Cod.Mecc."].astype(str).str.strip()
    df["DataGara"] = pd.to_datetime(df["DataGara"], errors='coerce', dayfirst=True)
    return df

@st.cache_data
def carica_voti_pdf(file):
    reader = PdfReader(file)
    text = ""
    for page in reader.pages:
        text += page.extract_text()

    lines = text.split('\n')
    data = []
    for line in lines:
        parts = line.strip().split()
        if len(parts) >= 4:
            try:
                numgara = str(int(parts[0]))
                voto_oa = float(parts[-2].replace(",", "."))
                voto_ot = float(parts[-1].replace(",", "."))
                data.append((numgara, voto_oa, voto_ot))
            except:
                continue
    df = pd.DataFrame(data, columns=["NumGara", "Voto OA", "Voto OT"])
    return df

@st.cache_data
def carica_indisponibili(file):
    df = pd.read_excel(file)
    df.columns = df.columns.str.strip()
    df["Cod.Mecc."] = df["Cod.Mecc."].astype(str).str.strip()
    df["Inizio"] = pd.to_datetime(df["Inizio"], errors='coerce')
    df["Fine"] = pd.to_datetime(df["Fine"], errors='coerce')
    return df

def get_settimane(start, end):
    current = start
    settimane = []
    while current <= end:
        settimana = current.strftime("%d/%m/%Y")
        settimane.append((settimana, current))
        current += timedelta(days=7)
    return settimane

# ---------------------- INTERFACCIA ----------------------

st.title("Gestione Arbitri - Stagione di test")

anagrafica_df = carica_anagrafica()

gare_file = st.file_uploader("📥 Carica file cra01.csv", type=["csv"])
voti_file = st.file_uploader("📥 Carica file voti PDF", type=["pdf"])
indisponibili_file = st.file_uploader("📥 Carica file indisponibilità", type=["xlsx"])

df_gare = carica_gare(gare_file) if gare_file else pd.DataFrame()
df_voti_raw = carica_voti_pdf(voti_file) if voti_file else pd.DataFrame()
df_indisp = carica_indisponibili(indisponibili_file) if indisponibili_file else pd.DataFrame()

# Merge voti → gare (tramite NumGara)
if not df_voti_raw.empty and not df_gare.empty:
    df_gare["NumGara"] = df_gare["NumGara"].astype(str).str.strip()
    df_voti_raw["NumGara"] = df_voti_raw["NumGara"].astype(str).str.strip()
    df_gare = df_gare.merge(df_voti_raw, on="NumGara", how="left")

# Costruisci dizionario delle gare per arbitro
gare_dict = {}
for _, row in df_gare.iterrows():
    cod = row["Cod.Mecc."]
    settimana = row["DataGara"] - timedelta(days=row["DataGara"].weekday())
    entry = f"{row['Categoria']} – {row['Girone']} – {row['Ruolo']}"
    if not pd.isna(row.get("Voto OA")):
        entry += f" – OA: {row['Voto OA']:.2f}"
    if not pd.isna(row.get("Voto OT")):
        entry += f" OT: {row['Voto OT']:.2f}"
    gare_dict.setdefault(cod, {}).setdefault(settimana, []).append(entry)

# Costruisci dizionario delle indisponibilità per arbitro
indisp_dict = {}
for _, row in df_indisp.iterrows():
    cod = row["Cod.Mecc."]
    start, end, motivo = row["Inizio"], row["Fine"], row["Motivo"]
    current = start
    while current <= end:
        week = current - timedelta(days=current.weekday())
        indisp_dict.setdefault(cod, {})[week] = motivo
        current += timedelta(days=1)

# Calcolo delle settimane
settimane = get_settimane(datetime(2025,5,1), datetime(2025,6,30))

# ---------------------- VISUALIZZAZIONE ----------------------

for _, arbitro in anagrafica_df.iterrows():
    with st.expander(f"{arbitro['Cognome']} {arbitro['Nome']} ({arbitro['Cod.Mecc.']})"):
        col1, col2, col3 = st.columns(3)
        col1.markdown(f"**Sezione:** {arbitro['Sezione']}")
        col2.markdown(f"**Età:** {arbitro['Età']}")

        cod = str(arbitro["Cod.Mecc."]).strip()
        data_settimanale = []
        for settimana, start_data in settimane:
            gare = gare_dict.get(cod, {}).get(start_data, [])
            indisponibile = indisp_dict.get(cod, {}).get(start_data, "")
            cella = ""
            if gare:
                cella += " | ".join(gare)
            if indisponibile:
                cella += f"\n🟥 Indisponibile: {indisponibile}"
            data_settimanale.append(cella if cella else "-")

        df_settimane = pd.DataFrame([data_settimanale], columns=[s[0] for s in settimane])
        st.dataframe(df_settimane, use_container_width=True)

# ---------------------- FINE ----------------------
