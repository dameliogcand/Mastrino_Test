import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from PyPDF2 import PdfReader

st.set_page_config(layout="wide")

# Set intervallo settimane test
DATA_INIZIO = datetime(2024, 5, 1)
DATA_FINE = datetime(2024, 5, 31)

@st.cache_data
def carica_anagrafica():
    file = "Arbitri.xlsx"
    df = pd.read_excel(file)
    df = df.rename(columns={
        'Cod.Mecc.': 'Cod.Mecc.',
        'Cognome': 'Cognome',
        'Nome': 'Nome',
        'Sezione': 'Sezione',
        'Età': 'Età'
    })
    df["Cod.Mecc."] = df["Cod.Mecc."].astype(str).str.replace('.0', '', regex=False).str.strip()
    return df

@st.cache_data
def carica_gare(uploaded_file):
    df = pd.read_excel(uploaded_file)
    colonne = df.columns.tolist()
    mappatura = {
        colonne[1]: "NumGara",
        colonne[2]: "Categoria",
        colonne[3]: "Girone",
        colonne[6]: "DataGara",
        colonne[16]: "Ruolo",
        colonne[17]: "Cod.Mecc.",
        colonne[18]: "Cognome"
    }
    df = df.rename(columns=mappatura)
    df["Cod.Mecc."] = df["Cod.Mecc."].astype(str).str.replace('.0', '', regex=False).str.strip()
    df["NumGara"] = df["NumGara"].astype(str).str.replace('.0', '', regex=False).str.strip()
    df["DataGara"] = pd.to_datetime(df["DataGara"], errors='coerce')
    return df

@st.cache_data
def carica_voti(uploaded_pdf):
    reader = PdfReader(uploaded_pdf)
    text = ""
    for page in reader.pages:
        text += page.extract_text()

    righe = text.split('\n')
    dati = []
    for riga in righe:
        parti = riga.strip().split()
        if len(parti) >= 10:
            try:
                num_gara = parti[0]
                voto_oa = float(parti[8].replace(',', '.'))
                voto_ot = float(parti[9].replace(',', '.'))
                dati.append({"NumGara": num_gara, "Voto OA": voto_oa, "Voto OT": voto_ot})
            except:
                continue
    return pd.DataFrame(dati)

@st.cache_data
def carica_indisponibili(uploaded_file):
    df = pd.read_excel(uploaded_file)
    df = df.rename(columns={
        'Cod.Mecc.': 'Cod.Mecc.',
        'Inizio': 'Inizio',
        'Fine': 'Fine',
        'Motivo': 'Motivo'
    })
    df["Cod.Mecc."] = df["Cod.Mecc."].astype(str).str.replace('.0', '', regex=False).str.strip()
    df["Inizio"] = pd.to_datetime(df["Inizio"], errors='coerce')
    df["Fine"] = pd.to_datetime(df["Fine"], errors='coerce')
    return df

# Upload dei file
st.sidebar.header("Caricamento File")
gare_file = st.sidebar.file_uploader("Carica file CRA01 (.xlsx)", type="xlsx")
voti_file = st.sidebar.file_uploader("Carica PDF voti", type="pdf")
indisponibili_file = st.sidebar.file_uploader("Carica indisponibilità (.xlsx)", type="xlsx")

df_arbitri = carica_anagrafica()
df_gare = carica_gare(gare_file) if gare_file else pd.DataFrame()
df_voti = carica_voti(voti_file) if voti_file else pd.DataFrame()
df_indisp = carica_indisponibili(indisponibili_file) if indisponibili_file else pd.DataFrame()

# Merge voti e gare su NumGara
if not df_gare.empty and not df_voti.empty:
    df_merged = pd.merge(df_gare, df_voti, on="NumGara", how="left")
else:
    df_merged = df_gare.copy()

# Creazione settimane
settimane = []
data_attuale = DATA_INIZIO
while data_attuale <= DATA_FINE:
    fine_settimana = data_attuale + timedelta(days=6)
    settimane.append((data_attuale, fine_settimana))
    data_attuale += timedelta(days=7)

# Visualizzazione
st.title("Visualizzazione Gare e Indisponibilità Arbitri")

for _, arbitro in df_arbitri.iterrows():
    with st.expander(f"{arbitro['Cognome']} {arbitro['Nome']} ({arbitro['Cod.Mecc.']})"):
        col1, col2, col3 = st.columns(3)
        col1.markdown(f"**Sezione:** {arbitro['Sezione']}")
        col2.markdown(f"**Età:** {arbitro['Età']}")

        cod_mecc = str(arbitro["Cod.Mecc."]).strip()
        cognome = arbitro["Cognome"].strip().upper()

        griglia = []
        for inizio_sett, fine_sett in settimane:
            # Gare
            gare_sett = df_merged[
                (df_merged["Cod.Mecc."] == cod_mecc) &
                (df_merged["Cognome"].str.upper().str.strip() == cognome) &
                (df_merged["DataGara"] >= inizio_sett) &
                (df_merged["DataGara"] <= fine_sett)
            ]

            celle = []
            for _, gara in gare_sett.iterrows():
                desc = f"{gara['Categoria']} – {gara['Girone']} – {gara['Ruolo']}"
                if not pd.isna(gara.get("Voto OA")):
                    desc += f" – OA: {gara['Voto OA']:.2f}"
                if not pd.isna(gara.get("Voto OT")):
                    desc += f" – OT: {gara['Voto OT']:.2f}"
                celle.append(desc)

            # Indisponibilità
            indisp = df_indisp[
                (df_indisp["Cod.Mecc."] == cod_mecc) &
                (df_indisp["Inizio"] <= fine_sett) &
                (df_indisp["Fine"] >= inizio_sett)
            ]
            for _, row in indisp.iterrows():
                celle.append(f"❌ {row['Motivo']}")

            griglia.append(", ".join(celle) if celle else "—")

        st.write("### Settimane")
        cols = st.columns(len(settimane))
        for idx, (col, (inizio, fine)) in enumerate(zip(cols, settimane)):
            col.markdown(f"**{inizio.strftime('%d/%m')}–{fine.strftime('%d/%m')}**")
            col.write(griglia[idx])
