import streamlit as st
import pandas as pd
from PyPDF2 import PdfReader
from datetime import datetime, timedelta

st.set_page_config(layout="wide")

@st.cache_data
def carica_anagrafica():
    df = pd.read_excel("Arbitri.xlsx")
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
    df["Cod.Mecc."] = df["Cod.Mecc."].astype(str).str.strip()
    df["Inizio"] = pd.to_datetime(df["Inizio"], errors="coerce")
    df["Fine"] = pd.to_datetime(df["Fine"], errors="coerce")
    return df

def estrai_voti_da_pdf(pdf_file):
    reader = PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    righe = text.split("\n")
    dati = []
    for riga in righe:
        parti = riga.strip().split()
        for i in range(len(parti) - 2):
            if parti[i].isdigit():
                try:
                    oa = float(parti[i + 1].replace(",", "."))
                    ot = float(parti[i + 2].replace(",", "."))
                    dati.append({
                        "NumGara": parti[i],
                        "Voto OA": oa,
                        "Voto OT": ot
                    })
                except:
                    continue
    df = pd.DataFrame(dati)
    df["NumGara"] = df["NumGara"].astype(str).str.strip()
    return df

# Periodo di riferimento
data_inizio = datetime(2025, 5, 1)
data_fine = datetime(2025, 6, 30)
settimane = []
data_corrente = data_inizio
while data_corrente <= data_fine:
    fine_settimana = data_corrente + timedelta(days=6)
    settimane.append((data_corrente, fine_settimana))
    data_corrente += timedelta(days=7)

st.title("🟢 Gestione Arbitri - Visualizzazione Settimanale")

# Caricamento file
col1, col2 = st.columns(2)
with col1:
    gare_file = st.file_uploader("📥 Carica file 'cra01.xlsx' (Excel senza intestazioni)", type=["xlsx"])
with col2:
    voti_file = st.file_uploader("📥 Carica file voti PDF", type=["pdf"])
indisponibili_file = st.file_uploader("📥 Carica file indisponibilità (Excel)", type=["xlsx"])

# Caricamento dati
df_arbitri = carica_anagrafica()
df_gare = carica_gare(gare_file) if gare_file else pd.DataFrame()
df_voti_raw = estrai_voti_da_pdf(voti_file) if voti_file else pd.DataFrame()
df_indisp = carica_indisponibili(indisponibili_file) if indisponibili_file else pd.DataFrame()

# Merge gare + voti
if not df_voti_raw.empty and not df_gare.empty:
    df_gare["NumGara"] = df_gare["NumGara"].astype(str).str.strip()
    df_voti_raw["NumGara"] = df_voti_raw["NumGara"].astype(str).str.strip()
    df_merged = pd.merge(df_gare, df_voti_raw, on="NumGara", how="left", suffixes=('', '_voti'))
    df_merged["Cod.Mecc."] = df_merged["Cod.Mecc."].astype(str).str.strip()
else:
    df_merged = df_gare.copy()

# Visualizzazione
for idx, arbitro in df_arbitri.iterrows():
    cod_mecc = str(arbitro["Cod.Mecc."]).strip()
    st.markdown(f"### 👤 {arbitro['Cognome']} {arbitro['Nome']}")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Sezione:** {arbitro['Sezione']}")
    with col2:
        st.markdown(f"**Età:** {arbitro['Età']}")

    cols = st.columns(len(settimane))
    for i, (start, end) in enumerate(settimane):
        cella = ""

        # Gara settimanale
        gare_sett = df_merged[
            (df_merged["Cod.Mecc."] == cod_mecc) &
            (df_merged["DataGara"] >= start) &
            (df_merged["DataGara"] <= end)
        ]
        for _, gara in gare_sett.iterrows():
            cat = gara["Categoria"]
            gir = gara["Girone"]
            ruolo = gara["Ruolo"]
            voto_oa = gara.get("Voto OA", "")
            voto_ot = gara.get("Voto OT", "")
            voto_txt = ""
            if pd.notna(voto_oa):
                voto_txt += f" OA: {voto_oa:.2f}"
            if pd.notna(voto_ot):
                voto_txt += f" OT: {voto_ot:.2f}"
            cella += f"{cat} – {gir} – {ruolo}{voto_txt}\n"

        # Indisponibilità settimanale
        indisp = df_indisp[
            (df_indisp["Cod.Mecc."] == cod_mecc) &
            (df_indisp["Inizio"] <= end) &
            (df_indisp["Fine"] >= start)
        ]
        for _, row in indisp.iterrows():
            motivo = row["motivo"] if "motivo" in row else "Indisponibile"
            cella += f"❌ {motivo}\n"

        if cella == "":
            cella = "-"
        cols[i].markdown(f"**{start.strftime('%d/%m')}**\n\n{cella}")

    st.markdown("---")
