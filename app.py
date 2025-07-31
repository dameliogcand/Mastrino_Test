import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from PyPDF2 import PdfReader

# Funzione per generare l'elenco delle settimane calcistiche
def get_week_ranges(start_date, end_date):
    weeks = []
    current = start_date
    while current <= end_date:
        end = current + timedelta(days=6)
        weeks.append((current, end))
        current += timedelta(days=7)
    return weeks

# Carica l'anagrafica degli arbitri (fissa)
@st.cache_data
def carica_anagrafica():
    df = pd.read_excel("Arbitri.xlsx")
    df["Cod.Mecc."] = df["Cod.Mecc."].astype(str).str.strip()
    return df

# Carica il file Excel cra01 (gare)
@st.cache_data
def carica_gare(file):
    df = pd.read_excel(file, header=None)
    df = df[[1, 2, 3, 6, 16, 17]]  # NumGara, Categoria, Girone, DataGara, Ruolo, Cod.Mecc.
    df.columns = ["NumGara", "Categoria", "Girone", "DataGara", "Ruolo", "Cod.Mecc."]
    df["Cod.Mecc."] = df["Cod.Mecc."].astype(str).str.strip()
    df["NumGara"] = df["NumGara"].astype(str).str.strip()
    df["DataGara"] = pd.to_datetime(df["DataGara"], errors="coerce", dayfirst=True)
    return df

# Estrae i voti dal PDF
@st.cache_data
def estrai_voti_da_pdf(file):
    reader = PdfReader(file)
    text = ""
    for page in reader.pages:
        text += page.extract_text()

    righe = text.split("\n")
    voti = []
    for riga in righe:
        parti = riga.split()
        if len(parti) >= 3 and parti[0].isdigit():
            num_gara = parti[0]
            try:
                voto_oa = float(parti[-2].replace(",", "."))
                voto_ot = float(parti[-1].replace(",", "."))
                voti.append({
                    "NumGara": num_gara,
                    "Voto OA": voto_oa,
                    "Voto OT": voto_ot
                })
            except ValueError:
                continue
    return pd.DataFrame(voti)

# Carica indisponibilità
@st.cache_data
def carica_indisponibili(file):
    df = pd.read_excel(file)
    df["Cod.Mecc."] = df["Cod.Mecc."].astype(str).str.strip()
    df["Inizio"] = pd.to_datetime(df["Inizio"], errors='coerce')
    df["Fine"] = pd.to_datetime(df["Fine"], errors='coerce')
    return df

# App Streamlit
st.set_page_config(layout="wide")
st.title("Gestione Arbitri - Settimane Calcistiche")

# Caricamento file settimanali
st.sidebar.header("Caricamento dati settimanali")
gare_file = st.sidebar.file_uploader("Carica file Gare cra01 (Excel)", type=["xls", "xlsx"])
voti_file = st.sidebar.file_uploader("Carica file Voti (PDF)", type="pdf")
indisponibili_file = st.sidebar.file_uploader("Carica file Indisponibilità", type=["xls", "xlsx"])

# Caricamento anagrafica
df_arbitri = carica_anagrafica()

# Inizializza dataframe gare, voti, indisponibilità
df_gare = carica_gare(gare_file) if gare_file else pd.DataFrame()
df_voti_raw = estrai_voti_da_pdf(voti_file) if voti_file else pd.DataFrame()
df_indisp = carica_indisponibili(indisponibili_file) if indisponibili_file else pd.DataFrame()

# Merge gare + voti
if not df_voti_raw.empty and not df_gare.empty:
    df_merged = df_gare.merge(df_voti_raw, on="NumGara", how="left")
else:
    df_merged = df_gare.copy()

# Intervallo settimanale per test
settimane = get_week_ranges(datetime(2025, 5, 1), datetime(2025, 6, 30))

# Visualizzazione
for index, arbitro in df_arbitri.iterrows():
    st.markdown(f"### {arbitro['Cognome']} {arbitro['Nome']} ({arbitro['Cod.Mecc.']})")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Sezione:** {arbitro['Sezione']}")
    with col2:
        st.markdown(f"**Età:** {arbitro['Età']}")

    cod_mecc = arbitro["Cod.Mecc."]
    settori = st.columns(len(settimane))
    for i, (inizio, fine) in enumerate(settimane):
        with settori[i]:
            st.markdown(f"**{inizio.strftime('%d/%m')}**")
            gare_sett = df_merged[
                (df_merged["Cod.Mecc."] == cod_mecc) &
                (df_merged["DataGara"] >= inizio) &
                (df_merged["DataGara"] <= fine)
            ]
            if not gare_sett.empty:
                for _, gara in gare_sett.iterrows():
                    descr = f"{gara['Categoria']} – {gara['Girone']} – {gara['Ruolo']}"
                    if not pd.isna(gara.get("Voto OA")):
                        descr += f" – OA: {gara['Voto OA']:.2f}"
                    if not pd.isna(gara.get("Voto OT")):
                        descr += f" OT: {gara['Voto OT']:.2f}"
                    st.markdown(descr)
            # Indisponibilità
            indisp = df_indisp[
                (df_indisp["Cod.Mecc."] == cod_mecc) &
                (df_indisp["Inizio"] <= fine) &
                (df_indisp["Fine"] >= inizio)
            ]
            if not indisp.empty:
                for _, row in indisp.iterrows():
                    st.markdown(f":red[**Ind.: {row['Motivo']}**]")

    st.markdown("---")
