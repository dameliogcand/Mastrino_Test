import streamlit as st
import pandas as pd
import pdfplumber
from datetime import datetime, timedelta
import io

st.set_page_config(page_title="Gestione Arbitri", layout="wide")
st.title("\U0001F4C4 Gestione Arbitri – C.A.N. D")

# Funzione per ottenere tutte le settimane tra due date
def get_weeks(start_date, end_date):
    weeks = []
    current = start_date
    while current <= end_date:
        weeks.append(current)
        current += timedelta(days=7)
    return weeks

# Caricamento anagrafica fissa
@st.cache_data

def carica_anagrafica():
    df = pd.read_excel("Arbitri.xlsx")
    df.columns = df.columns.str.strip()
    df["Cod.Mecc."] = df["Cod.Mecc."].astype(str).str.strip()
    return df

# Caricamento gare da CRA01 settimanale
@st.cache_data

def carica_gare(file):
    df = pd.read_csv(file, header=None)
    if df.shape[1] != 24:
        st.warning(f"\u26a0\ufe0f Il file CRA01 ha {df.shape[1]} colonne.")
        return pd.DataFrame()
    df.columns = [
        "NumGara", "Giornata", "Categoria", "Fascia", "Turno", "Altro1", "Data", "Ora",
        "Cod_Squadra1", "Nome_Squadra1", "Cod_Squadra2", "Nome_Squadra2", "CodCampo",
        "NomeCampo", "Localita", "ID_Gara", "Ruolo", "Cod.Mecc.", "Cognome", "Nome",
        "Altro2", "Sezione", "Altro3", "Altro4"
    ]
    df["Cod.Mecc."] = df["Cod.Mecc."].astype(str).str.strip()
    df["NumGara"] = df["NumGara"].astype(str).str.strip()
    return df[["NumGara", "Cod.Mecc.", "Data"]]

# Estrazione voti da PDF settimanale
@st.cache_data

def estrai_voti(pdf_file):
    text = ""
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text += page.extract_text() + "\n"
    righe = text.split("\n")
    records = []
    for r in righe:
        parts = r.split()
        if len(parts) >= 3 and parts[0].isdigit():
            numgara = parts[0]
            voto = parts[-1].replace(",", ".")
            tipo = parts[-2].upper()
            if tipo in ["OA", "OT"]:
                records.append((numgara, tipo, voto))
    df = pd.DataFrame(records, columns=["NumGara", "Tipo", "Voto"])
    df = df.pivot_table(index="NumGara", columns="Tipo", values="Voto", aggfunc="first").reset_index()
    df["NumGara"] = df["NumGara"].astype(str).str.strip()
    return df

# Caricamento indisponibilità
@st.cache_data

def carica_indisponibili(file):
    df = pd.read_excel(file)
    df.columns = df.columns.str.strip()
    df["Cod.Mecc."] = df["Cod.Mecc."].astype(str).str.strip()
    df["Data"] = pd.to_datetime(df["Data"], errors='coerce')
    return df

# Periodo di test: dal 01/05/2025 al 30/06/2025
start_test = datetime(2025, 5, 1)
end_test = datetime(2025, 6, 30)
settimane = get_weeks(start_test, end_test)

# Caricamento file settimanali
gare_file = st.file_uploader("Carica file CRA01 (.csv)", type=["csv"])
voti_file = st.file_uploader("Carica file voti (.pdf)", type=["pdf"])
indisponibili_file = st.file_uploader("Carica file indisponibilità (.xlsx)", type=["xlsx"])

# Caricamento e unione dati se disponibili
df_arbitri = carica_anagrafica()
df_gare = carica_gare(gare_file) if gare_file else pd.DataFrame()
df_voti_raw = estrai_voti(voti_file) if voti_file else pd.DataFrame()
df_indisp = carica_indisponibili(indisponibili_file) if indisponibili_file else pd.DataFrame()

# Merge voti con Cod.Mecc. usando NumGara tramite df_gare
if not df_voti_raw.empty and not df_gare.empty:
    if "NumGara" in df_gare.columns and "Cod.Mecc." in df_gare.columns:
        df_voti = df_voti_raw.merge(df_gare[["NumGara", "Cod.Mecc."]], on="NumGara", how="left")
    else:
        st.error("\u274c File CRA01 non contiene le colonne richieste per il merge ('NumGara' e 'Cod.Mecc.')")
        st.stop()
else:
    df_voti = pd.DataFrame()

# Visualizzazione
for idx, arbitro in df_arbitri.iterrows():
    with st.expander(f"{arbitro['Cognome']} {arbitro['Nome']} ({arbitro['Cod.Mecc.']})"):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"**Sezione:** {arbitro['Sezione']}")
            st.markdown(f"**Età:** {arbitro['Età']}")
            st.markdown(f"**Anzianità:** {arbitro['Fascia']}")

        codice = arbitro["Cod.Mecc."]

        # Riga settimanale con gare/voti/indisponibilità
        for week_start in settimane:
            week_str = week_start.strftime("%d/%m/%Y")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f"**Settimana** {week_str}")
            with col2:
                # Gara
                if not df_gare.empty:
                    gare = df_gare[(df_gare["Cod.Mecc."] == codice) & (pd.to_datetime(df_gare["Data"]) >= week_start) & (pd.to_datetime(df_gare["Data"]) < week_start + timedelta(days=7))]
                    for _, g in gare.iterrows():
                        st.markdown(f"Gara {g['NumGara']}")
            with col3:
                # Voti
                if not df_voti.empty:
                    voti = df_voti[df_voti["Cod.Mecc."] == codice]
                    if not voti.empty:
                        for _, v in voti.iterrows():
                            st.markdown(f"OA: {v.get('OA', '-')}, OT: {v.get('OT', '-')}")
                # Indisponibilità
                if not df_indisp.empty:
                    indisps = df_indisp[(df_indisp["Cod.Mecc."] == codice) & (df_indisp["Data"] >= week_start) & (df_indisp["Data"] < week_start + timedelta(days=7))]
                    for _, i in indisps.iterrows():
                        st.markdown(f"\u274c Indisp: {i['Motivazione']}")
