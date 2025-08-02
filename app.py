import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from PyPDF2 import PdfReader

st.set_page_config(layout="wide")
st.title("Gestione Arbitri – Periodo di test: Maggio 2025")

# Periodo fisso per test
DATA_INIZIO = datetime(2025, 5, 1)
DATA_FINE = datetime(2025, 5, 31)

def get_settimane():
    settimane = []
    current = DATA_INIZIO
    while current <= DATA_FINE:
        fine_settimana = current + timedelta(days=6)
        settimane.append((current, fine_settimana))
        current += timedelta(weeks=1)
    return settimane

# === FUNZIONI DI CARICAMENTO E RINOMINA ===
@st.cache_data
def carica_anagrafica(file):
    df = pd.read_excel(file)
    df.rename(columns={
        'Cod.Mecc.': 'Cod.Mecc.',
        'Cognome': 'Cognome',
        'Nome': 'Nome',
        'Sezione': 'Sezione',
        'Età': 'Età'
    }, inplace=True)
    df["Cod.Mecc."] = df["Cod.Mecc."].astype(str).str.replace('.0', '', regex=False).str.strip()
    return df[["Cod.Mecc.", "Cognome", "Nome", "Sezione", "Età"]]

@st.cache_data
def carica_gare(file):
    df = pd.read_excel(file)
    df.rename(columns={
        'Column2': 'NumGara',
        'Column18': 'Cod.Mecc.',
        'Column19': 'Cognome',
        'Column7': 'DataGara',
        'Column3': 'Categoria',
        'Column4': 'Girone',
        'Column17': 'Ruolo'
    }, inplace=True)
    df["Cod.Mecc."] = df["Cod.Mecc."].astype(str).str.replace('.0', '', regex=False).str.strip()
    df["NumGara"] = df["NumGara"].astype(str).str.replace('.0', '', regex=False).str.strip()
    df["DataGara"] = pd.to_datetime(df["DataGara"], errors='coerce')
    return df[["NumGara", "Cod.Mecc.", "Cognome", "DataGara", "Categoria", "Girone", "Ruolo"]]

@st.cache_data
def carica_voti(file):
    reader = PdfReader(file)
    text = "\n".join(page.extract_text() for page in reader.pages if page.extract_text())
    righe = [r.strip() for r in text.split('\n') if r.strip()]
    dati = []
    for riga in righe[1:]:  # salta intestazione
        parti = riga.split()
        if len(parti) >= 10:
            num_gara = parti[0].replace('.0', '').strip()
            voto_oa = parti[8].replace(",", ".")
            voto_ot = parti[9].replace(",", ".")
            dati.append([num_gara, voto_oa, voto_ot])
    df = pd.DataFrame(dati, columns=["NumGara", "Voto_OA", "Voto_OT"])
    df["NumGara"] = df["NumGara"].astype(str).str.strip()
    return df

@st.cache_data
def carica_indisponibili(file):
    df = pd.read_excel(file)
    df.rename(columns={
        'Cod.Mecc.': 'Cod.Mecc.',
        'Inizio': 'Inizio',
        'Fine': 'Fine',
        'Motivo': 'Motivo'
    }, inplace=True)
    df["Cod.Mecc."] = df["Cod.Mecc."].astype(str).str.replace('.0', '', regex=False).str.strip()
    df["Inizio"] = pd.to_datetime(df["Inizio"], errors='coerce')
    df["Fine"] = pd.to_datetime(df["Fine"], errors='coerce')
    return df[["Cod.Mecc.", "Inizio", "Fine", "Motivo"]]

# === UPLOAD FILE ===
anagrafica_file = st.file_uploader("Carica il file Arbitri.xlsx", type=["xlsx"])
gare_file = st.file_uploader("Carica il file CRA01.xlsx", type=["xlsx"])
voti_file = st.file_uploader("Carica il file Voti PDF", type=["pdf"])
indisponibili_file = st.file_uploader("Carica il file Indisponibili.xlsx", type=["xlsx"])

if anagrafica_file:
    df_arbitri = carica_anagrafica(anagrafica_file)
    df_gare = carica_gare(gare_file) if gare_file else pd.DataFrame()
    df_voti_raw = carica_voti(voti_file) if voti_file else pd.DataFrame()
    df_indisp = carica_indisponibili(indisponibili_file) if indisponibili_file else pd.DataFrame()

    # Sicurezza sul merge
    if "NumGara" not in df_gare.columns or "NumGara" not in df_voti_raw.columns:
        st.error("❌ Colonna 'NumGara' mancante per il merge.")
        st.stop()

    df_merged = pd.merge(df_gare, df_voti_raw, on="NumGara", how="left")

    settimane = get_settimane()

    for _, arbitro in df_arbitri.iterrows():
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        col1.markdown(f"**{arbitro['Cognome']} {arbitro['Nome']}**")
        col2.markdown(f"**Sezione:** {arbitro['Sezione']}")
        col3.markdown(f"**Età:** {arbitro['Età']}")

        cod_mecc = str(arbitro["Cod.Mecc."]).strip()
        cognome = arbitro["Cognome"].strip().lower()

        cols = st.columns(len(settimane))
        for idx, (inizio, fine) in enumerate(settimane):
            gare_sett = df_merged[
                (df_merged["Cod.Mecc."].astype(str).str.strip() == cod_mecc) &
                (df_merged["Cognome"].str.lower().str.strip() == cognome) &
                (df_merged["DataGara"] >= inizio) &
                (df_merged["DataGara"] <= fine)
            ]

            indisps = df_indisp[
                (df_indisp["Cod.Mecc."] == cod_mecc) &
                (df_indisp["Inizio"] <= fine) &
                (df_indisp["Fine"] >= inizio)
            ]

            with cols[idx]:
                st.markdown(f"**{inizio.strftime('%d/%m')}–{fine.strftime('%d/%m')}**")
                if not gare_sett.empty:
                    for _, gara in gare_sett.iterrows():
                        info = f"{gara['Categoria']} – {gara['Girone']} – {gara['Ruolo']}"
                        if pd.notna(gara['Voto_OA']):
                            info += f"<br/>OA: {gara['Voto_OA']}"
                        if pd.notna(gara['Voto_OT']):
                            info += f" OT: {gara['Voto_OT']}"
                        st.markdown(info, unsafe_allow_html=True)
                elif not indisps.empty:
                    for _, ind in indisps.iterrows():
                        st.warning(f"Ind.: {ind['Motivo']}")
                else:
                    st.markdown("-")
