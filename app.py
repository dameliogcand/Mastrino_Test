import streamlit as st
import pandas as pd
import datetime
from datetime import datetime
from io import StringIO
from PyPDF2 import PdfReader

st.set_page_config(layout="wide")
st.title("Gestione Arbitri - Mastrino")

# Funzione per generare le settimane
@st.cache_data
def genera_settimane(inizio, fine):
    settimane = []
    current = inizio
    while current <= fine:
        settimana_fine = current + pd.DateOffset(days=6)
        settimane.append((current, settimana_fine))
        current += pd.DateOffset(days=7)
    return settimane

# Carica anagrafica arbitri
@st.cache_data
def carica_anagrafica():
    df = pd.read_excel("Arbitri.xlsx")
    df["Cod.Mecc."] = df["Cod.Mecc."].astype(str).str.replace(".0", "", regex=False).str.strip()
    df["Età"] = df["Età"].astype(str).str.strip()
    return df

# Carica file gare
@st.cache_data
def carica_gare(file):
    df = pd.read_excel(file, header=None)
    df = df[[1, 2, 3, 6, 16, 17]]  # B, C, D, G, Q, R
    df.columns = ["NumGara", "Categoria", "Girone", "DataGara", "Ruolo", "Cod.Mecc."]
    df["Cod.Mecc."] = df["Cod.Mecc."].astype(str).str.replace(".0", "", regex=False).str.strip()
    df["NumGara"] = df["NumGara"].astype(str).str.replace(".0", "", regex=False).str.strip()
    df["Settimana"] = pd.to_datetime(df["DataGara"], errors='coerce').dt.to_period("W").apply(lambda r: r.start_time)
    return df

# Carica file voti da PDF
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
        if len(parti) >= 5:
            try:
                numgara = str(parti[0]).replace(".0", "").strip()
                oa = float(parti[-2].replace(",", "."))
                ot = float(parti[-1].replace(",", "."))
                dati.append((numgara, oa, ot))
            except:
                continue
    df = pd.DataFrame(dati, columns=["NumGara", "OA", "OT"])
    df["NumGara"] = df["NumGara"].astype(str).str.strip()
    return df

# Carica file indisponibili
@st.cache_data
def carica_indisponibili(file):
    df = pd.read_excel(file)
    df["Cod.Mecc."] = df["Cod.Mecc."].astype(str).str.replace(".0", "", regex=False).str.strip()
    df["Inizio"] = pd.to_datetime(df["Inizio"], errors="coerce")
    df["Fine"] = pd.to_datetime(df["Fine"], errors="coerce")
    return df

# Carica i file
gare_file = st.file_uploader("Carica file CRA01 (Excel)", type="xlsx")
voti_file = st.file_uploader("Carica file Voti (PDF)", type="pdf")
indisponibili_file = st.file_uploader("Carica file Indisponibili (Excel)", type="xlsx")

# Dati fissi
df_arbitri = carica_anagrafica()

if gare_file:
    df_gare = carica_gare(gare_file)
else:
    df_gare = pd.DataFrame()

if voti_file:
    df_voti_raw = carica_voti(voti_file)
else:
    df_voti_raw = pd.DataFrame()

if indisponibili_file:
    df_indisp = carica_indisponibili(indisponibili_file)
else:
    df_indisp = pd.DataFrame()

# Merge gare + voti
if not df_gare.empty and not df_voti_raw.empty:
    df_merged = pd.merge(df_gare, df_voti_raw, on="NumGara", how="left")
else:
    df_merged = df_gare.copy()
    df_merged["OA"] = None
    df_merged["OT"] = None

# Genera settimane test
settimane = genera_settimane(datetime(2025, 5, 1), datetime(2025, 6, 30))

# 🔎 Debug: visualizza colonne disponibili
st.write("📌 Colonne in df_merged:", df_merged.columns.tolist())

# Visualizzazione dati arbitri
for idx, arbitro in df_arbitri.iterrows():
    cod_mecc = str(arbitro["Cod.Mecc."]).strip()

    with st.expander(f"{arbitro['Cognome']} {arbitro['Nome']} ({cod_mecc})", expanded=True):
        col1, col2, col3 = st.columns(3)
        col1.markdown(f"**Sezione:** {arbitro['Sezione']}")
        col2.markdown(f"**Età:** {arbitro['Età']}")

        row_sett = []
        for settimana in settimane:
            settimana_inizio = settimana[0]
            settimana_fine = settimana[1]
            settimana_label = settimana_inizio.strftime("%d/%m")

            # Verifica indisponibilità
            motivo_ind = ""
            if not df_indisp.empty:
                ind_row = df_indisp[
                    (df_indisp["Cod.Mecc."] == cod_mecc) &
                    (df_indisp["Inizio"] <= settimana_fine) &
                    (df_indisp["Fine"] >= settimana_inizio)
                ]
                if not ind_row.empty:
                    motivo_ind = ind_row.iloc[0]["Motivo"]

            # Filtra gare per arbitro e settimana
            gare_sett = df_merged[
                (df_merged["Cod.Mecc."] == cod_mecc) &
                (df_merged["Settimana"] == settimana_inizio)
            ]

            if not gare_sett.empty:
                descrizioni = []
                for _, gara in gare_sett.iterrows():
                    cat = str(gara["Categoria"])
                    gir = str(gara["Girone"])
                    ruolo = gara["Ruolo"]
                    oa = gara["OA"]
                    ot = gara["OT"]
                    voto = f"OA: {oa:.2f}" if not pd.isna(oa) else ""
                    voto += f" OT: {ot:.2f}" if not pd.isna(ot) else ""
                    descrizione = f"{cat} – {gir} – {ruolo}"
                    if voto:
                        descrizione += f" – {voto}"
                    descrizioni.append(descrizione)
                cella = " | ".join(descrizioni)
            elif motivo_ind:
                cella = f"❌ {motivo_ind}"
            else:
                cella = ""

            row_sett.append(cella)

        st.table(pd.DataFrame([row_sett], columns=[s[0].strftime("%d/%m") for s in settimane]))
