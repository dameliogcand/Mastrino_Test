import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from PyPDF2 import PdfReader

st.set_page_config(layout="wide")

# Funzione per caricare anagrafica
@st.cache_data
def carica_anagrafica():
    df = pd.read_excel("Arbitri.xlsx")
    df["Cod.Mecc."] = df["Cod.Mecc."].astype(str).str.strip()
    return df

# Funzione per caricare gare da Excel senza intestazioni
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
    df["Cod.Mecc."] = df["Cod.Mecc."].astype(str).str.strip()
    df["DataGara"] = pd.to_datetime(df["DataGara"], errors='coerce')
    return df

# Funzione per caricare voti da PDF
@st.cache_data
def carica_voti_da_pdf(pdf_file):
    reader = PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text()

    righe = text.split("\n")
    dati = []
    for riga in righe:
        if "OA:" in riga and "OT:" in riga:
            parti = riga.split()
            try:
                num_gara = next(p for p in parti if p.isdigit() and len(p) >= 4)
                oa = float(next(p.split(":")[1] for p in parti if p.startswith("OA:")))
                ot = float(next(p.split(":")[1] for p in parti if p.startswith("OT:")))
                dati.append({"NumGara": num_gara, "Voto OA": oa, "Voto OT": ot})
            except Exception:
                continue
    return pd.DataFrame(dati)

# Funzione per caricare indisponibilità
@st.cache_data
def carica_indisponibili(file):
    df = pd.read_excel(file)
    df["Cod.Mecc."] = df["Cod.Mecc."].astype(str).str.strip()
    df["Inizio"] = pd.to_datetime(df["Inizio"], errors='coerce')
    df["Fine"] = pd.to_datetime(df["Fine"], errors='coerce')
    return df

# Inizio Streamlit
st.title("Gestione Arbitri – Gare, Voti e Indisponibilità")

df_arbitri = carica_anagrafica()

gare_file = st.file_uploader("📥 Carica file gare (cra01.xlsx)", type=["xlsx"])
pdf_file = st.file_uploader("📥 Carica PDF voti", type=["pdf"])
indisponibili_file = st.file_uploader("📥 Carica file indisponibilità", type=["xlsx"])

df_gare = carica_gare(gare_file) if gare_file else pd.DataFrame()
df_voti_raw = carica_voti_da_pdf(pdf_file) if pdf_file else pd.DataFrame()
df_indisp = carica_indisponibili(indisponibili_file) if indisponibili_file else pd.DataFrame()

# Merge voti -> gare tramite NumGara -> otteniamo Cod.Mecc. e poi uniamo ai voti
if not df_voti_raw.empty and not df_gare.empty:
    df_gare["NumGara"] = df_gare["NumGara"].astype(str)
    df_voti_raw["NumGara"] = df_voti_raw["NumGara"].astype(str)
    df_merged = pd.merge(df_gare, df_voti_raw, on="NumGara", how="left")
else:
    df_merged = df_gare.copy()

# Intervallo settimane
inizio = datetime(2025, 5, 1)
fine = datetime(2025, 6, 30)
settimane = []
data = inizio
while data <= fine:
    inizio_sett = data
    fine_sett = data + timedelta(days=6)
    settimane.append((inizio_sett, fine_sett))
    data += timedelta(days=7)

# Visualizzazione
for _, arbitro in df_arbitri.iterrows():
    cod_mecc = arbitro["Cod.Mecc."]
    st.markdown(f"### {arbitro['Cognome']} {arbitro['Nome']}")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Sezione:** {arbitro['Sezione']}")
    with col2:
        st.markdown(f"**Età:** {arbitro['Età']}")

    cols = st.columns(len(settimane))
    for i, (start, end) in enumerate(settimane):
        settimana_label = f"{start.strftime('%d/%m')}–{end.strftime('%d/%m')}"
        cella = ""

        # Cerca gare
        gare_sett = df_merged[
            (df_merged["Cod.Mecc."] == cod_mecc) &
            (df_merged["DataGara"] >= start) &
            (df_merged["DataGara"] <= end)
        ]

        for _, gara in gare_sett.iterrows():
            info = f"{gara['Categoria']} – {gara['Girone']} – {gara['Ruolo']}"
            if pd.notna(gara.get("Voto OA")):
                info += f" – OA: {gara['Voto OA']:.2f}"
            if pd.notna(gara.get("Voto OT")):
                info += f" OT: {gara['Voto OT']:.2f}"
            cella += info + "\n"

        # Cerca indisponibilità
        indisp_sett = df_indisp[
            (df_indisp["Cod.Mecc."] == cod_mecc) &
            (df_indisp["Inizio"] <= end) & (df_indisp["Fine"] >= start)
        ]
        for _, ind in indisp_sett.iterrows():
            cella += f"❌ {ind['Motivo']}\n"

        cols[i].markdown(f"**{settimana_label}**\n\n{cella}" if cella else f"**{settimana_label}**\n\n—")
