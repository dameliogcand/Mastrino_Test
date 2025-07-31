import streamlit as st
import pandas as pd
import datetime
from datetime import timedelta
from PyPDF2 import PdfReader
from io import StringIO

st.set_page_config(layout="wide")

# ----------------------------
# FUNZIONI DI CARICAMENTO
# ----------------------------

@st.cache_data
def carica_anagrafica():
    df = pd.read_excel("Arbitri.xlsx")
    df["Cod.Mecc."] = df["Cod.Mecc."].astype(str).str.replace('.0', '', regex=False).str.strip()
    df["Età"] = df["Età"].astype(str)
    return df

@st.cache_data
def carica_gare(file):
    df_raw = pd.read_excel(file, header=None)
    df = pd.DataFrame()
    df["NumGara"] = df_raw.iloc[:, 1].astype(str).str.replace('.0', '', regex=False).str.strip()
    df["Categoria"] = df_raw.iloc[:, 2].astype(str).str.strip()
    df["Girone"] = df_raw.iloc[:, 3].astype(str).str.strip()
    df["DataGara"] = pd.to_datetime(df_raw.iloc[:, 6], errors="coerce")
    df["Ruolo"] = df_raw.iloc[:, 16].astype(str).str.strip()
    df["Cod.Mecc."] = df_raw.iloc[:, 17].astype(str).str.replace('.0', '', regex=False).str.strip()
    return df

@st.cache_data
def carica_voti(file):
    reader = PdfReader(file)
    text = ""
    for page in reader.pages:
        text += page.extract_text()

    righe = text.split("\n")
    dati = []
    for riga in righe:
        parti = riga.split()
        if len(parti) >= 4 and parti[0].isdigit():
            num_gara = parti[0]
            try:
                voto_oa = float(parti[-2].replace(",", "."))
                voto_ot = float(parti[-1].replace(",", "."))
            except:
                voto_oa = voto_ot = None
            dati.append({
                "NumGara": num_gara,
                "Voto.OA": voto_oa,
                "Voto.OT": voto_ot
            })

    df = pd.DataFrame(dati)
    df["NumGara"] = df["NumGara"].astype(str).str.replace('.0', '', regex=False).str.strip()
    return df

@st.cache_data
def carica_indisponibili(file):
    df = pd.read_excel(file)
    df["Cod.Mecc."] = df["Cod.Mecc."].astype(str).str.replace('.0', '', regex=False).str.strip()
    df["Inizio"] = pd.to_datetime(df["Inizio"], errors="coerce")
    df["Fine"] = pd.to_datetime(df["Fine"], errors="coerce")
    return df

# ----------------------------
# COSTRUISCI INTERVALLO SETTIMANE
# ----------------------------

def costruisci_settimane(start_date, end_date):
    settimane = []
    current = start_date
    while current <= end_date:
        settimana = {
            "label": f"{current.strftime('%d/%m')} - {(current + timedelta(days=6)).strftime('%d/%m')}",
            "start_time": current,
            "end_time": current + timedelta(days=7)
        }
        settimane.append(settimana)
        current += timedelta(days=7)
    return settimane

# ----------------------------
# INTERFACCIA STREAMLIT
# ----------------------------

st.title("📅 Gestione Arbitri - Visualizzazione Settimanale")

with st.sidebar:
    st.header("📤 Caricamento File")
    gare_file = st.file_uploader("Carica file CRA01 (Excel)", type=["xlsx"])
    voti_file = st.file_uploader("Carica file PDF Voti", type=["pdf"])
    indisponibili_file = st.file_uploader("Carica file Indisponibilità", type=["xlsx"])

# Caricamento dati
df_arbitri = carica_anagrafica()
df_gare = carica_gare(gare_file) if gare_file else pd.DataFrame()
df_voti_raw = carica_voti(voti_file) if voti_file else pd.DataFrame()
df_indisp = carica_indisponibili(indisponibili_file) if indisponibili_file else pd.DataFrame()

# Merge gare + voti
if not df_voti_raw.empty and not df_gare.empty:
    df_merged = pd.merge(df_gare, df_voti_raw, on="NumGara", how="left")
else:
    df_merged = df_gare.copy()

# Costruzione settimane test
settimane = costruisci_settimane(datetime.date(2025, 5, 1), datetime.date(2025, 6, 30))

# ----------------------------
# VISUALIZZAZIONE
# ----------------------------

for _, arbitro in df_arbitri.iterrows():
    cod_mecc = arbitro["Cod.Mecc."]
    st.markdown(f"### {arbitro['Cognome']} {arbitro['Nome']} ({cod_mecc})")

    col1, col2, col3 = st.columns(3)
    col1.markdown(f"**Sezione:** {arbitro['Sezione']}")
    col2.markdown(f"**Età:** {arbitro['Età']}")

    # Riga delle settimane
    cols = st.columns(len(settimane))
    for i, settimana in enumerate(settimane):
        contenuto = ""

        # ➤ GARE
        gare_sett = df_merged[
            (df_merged["Cod.Mecc."] == cod_mecc) &
            (df_merged["DataGara"].notna()) &
            (df_merged["DataGara"] >= settimana["start_time"]) &
            (df_merged["DataGara"] < settimana["end_time"])
        ]
        for _, gara in gare_sett.iterrows():
            cat = gara["Categoria"]
            girone = gara["Girone"]
            ruolo = gara["Ruolo"]
            voto_oa = gara.get("Voto.OA", "")
            voto_ot = gara.get("Voto.OT", "")
            testo = f"{cat} – {girone} – {ruolo}"
            if pd.notna(voto_oa) or pd.notna(voto_ot):
                testo += f" – OA: {voto_oa} OT: {voto_ot}"
            contenuto += testo + "<br>"

        # ➤ INDISPONIBILITÀ
        if not df_indisp.empty:
            indisps = df_indisp[df_indisp["Cod.Mecc."] == cod_mecc]
            for _, row in indisps.iterrows():
                if pd.isna(row["Inizio"]) or pd.isna(row["Fine"]):
                    continue
                if settimana["start_time"] <= row["Fine"].date() and settimana["end_time"] > row["Inizio"].date():
                    contenuto += f"<span style='color:red;'>INDISP: {row['Motivo']}</span><br>"

        if contenuto == "":
            contenuto = "-"

        cols[i].markdown(contenuto, unsafe_allow_html=True)

