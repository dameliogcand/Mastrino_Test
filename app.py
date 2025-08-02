import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from PyPDF2 import PdfReader

st.set_page_config(layout="wide")

# Mapping colonne per ogni file
MAPPING = {
    "arbitri": {
        1: "Cod.Mecc.",
        2: "Cognome",
        3: "Nome",
        4: "Sezione",
        5: "Età"
    },
    "gare": {
        1: "NumGara",
        2: "Categoria",
        3: "Girone",
        6: "DataGara",
        16: "Ruolo",
        17: "Cod.Mecc.",
        18: "Cognome"
    },
    "voti": {
        0: "NumGara",
        8: "Voto OA",
        9: "Voto OT"
    },
    "indisponibili": {
        1: "Cod.Mecc.",
        8: "Inizio",
        9: "Fine",
        10: "Motivo"
    }
}

def rinomina_colonne(df, tipo):
    mapping = MAPPING[tipo]
    if df.shape[1] < max(mapping.keys()) + 1:
        st.error(f"❌ Il file {tipo.capitalize()} ha meno di {max(mapping.keys()) + 1} colonne.")
        st.stop()
    return df.rename(columns={df.columns[k]: v for k, v in mapping.items()})

@st.cache_data
def carica_anagrafica(file):
    df = pd.read_excel(file)
    df = rinomina_colonne(df, "arbitri")
    df["Cod.Mecc."] = df["Cod.Mecc."].astype(str).str.replace(".0", "", regex=False).str.strip()
    return df

@st.cache_data
def carica_gare(file):
    df = pd.read_excel(file)
    df = rinomina_colonne(df, "gare")
    df["Cod.Mecc."] = df["Cod.Mecc."].astype(str).str.replace(".0", "", regex=False).str.strip()
    df["NumGara"] = df["NumGara"].astype(str).str.replace(".0", "", regex=False).str.strip()
    df["DataGara"] = pd.to_datetime(df["DataGara"], errors='coerce')
    return df

@st.cache_data
def carica_voti(file):
    reader = PdfReader(file)
    text = ""
    for page in reader.pages:
        text += page.extract_text()

    rows = [r.strip() for r in text.split("\n") if r.strip()]
    data = [r.split() for r in rows if len(r.split()) >= 10]
    df = pd.DataFrame(data)
    df = rinomina_colonne(df, "voti")
    df["NumGara"] = df["NumGara"].astype(str).str.replace(".0", "", regex=False).str.strip()
    df["Voto OA"] = pd.to_numeric(df["Voto OA"], errors="coerce")
    df["Voto OT"] = pd.to_numeric(df["Voto OT"], errors="coerce")
    return df

@st.cache_data
def carica_indisponibili(file):
    df = pd.read_excel(file)
    df = rinomina_colonne(df, "indisponibili")
    df["Cod.Mecc."] = df["Cod.Mecc."].astype(str).str.replace(".0", "", regex=False).str.strip()
    df["Inizio"] = pd.to_datetime(df["Inizio"], errors="coerce")
    df["Fine"] = pd.to_datetime(df["Fine"], errors="coerce")
    return df

# Upload
st.title("📊 Monitoraggio Arbitri – Periodo di Test")
arbitri_file = st.file_uploader("📥 Carica file Arbitri.xlsx", type="xlsx")
gare_file = st.file_uploader("📥 Carica file CRA01.xlsx", type="xlsx")
voti_file = st.file_uploader("📥 Carica file Voti (PDF)", type="pdf")
indisponibili_file = st.file_uploader("📥 Carica file Indisponibili.xlsx", type="xlsx")

if arbitri_file:
    df_arbitri = carica_anagrafica(arbitri_file)
    df_gare = carica_gare(gare_file) if gare_file else pd.DataFrame()
    df_voti_raw = carica_voti(voti_file) if voti_file else pd.DataFrame()
    df_indisp = carica_indisponibili(indisponibili_file) if indisponibili_file else pd.DataFrame()

    # Unione gare + voti su NumGara
    if not df_voti_raw.empty and not df_gare.empty:
        if "NumGara" not in df_voti_raw.columns or "NumGara" not in df_gare.columns:
            st.error("❌ Colonna 'NumGara' mancante per il merge.")
            st.stop()
        df_merged = pd.merge(df_gare, df_voti_raw, on="NumGara", how="left")
    else:
        df_merged = df_gare.copy()

    # Settimane test
    start_date = datetime(2025, 5, 1)
    end_date = datetime(2025, 5, 31)
    all_weeks = []
    current = start_date
    while current <= end_date:
        week_end = current + timedelta(days=6)
        all_weeks.append((current, week_end))
        current += timedelta(days=7)

    for _, arbitro in df_arbitri.iterrows():
        st.subheader(f"👤 {arbitro['Cognome']} {arbitro['Nome']}")
        cols = st.columns([1, 1, 1])
        cols[0].markdown(f"**Sezione:** {arbitro['Sezione']}")
        cols[1].markdown(f"**Cod.Mecc.:** {arbitro['Cod.Mecc.']}")
        cols[2].markdown(f"**Età:** {arbitro['Età']}")

        for week_start, week_end in all_weeks:
            settimana = f"🗓 **Settimana {week_start.strftime('%d/%m')} - {week_end.strftime('%d/%m')}**"
            st.markdown(settimana)

            box = ""
            # Gare
            gare_sett = df_merged[
                (df_merged["Cod.Mecc."] == arbitro["Cod.Mecc."]) &
                (df_merged["Cognome"].str.upper() == arbitro["Cognome"].upper()) &
                (df_merged["DataGara"] >= week_start) &
                (df_merged["DataGara"] <= week_end)
            ]

            for _, gara in gare_sett.iterrows():
                riga = f"{gara['Categoria']} – {gara['Girone']} – {gara['Ruolo']}"
                if pd.notna(gara.get("Voto OA")):
                    riga += f" – OA: {gara['Voto OA']:.2f}"
                if pd.notna(gara.get("Voto OT")):
                    riga += f" OT: {gara['Voto OT']:.2f}"
                box += "- " + riga + "\n"

            # Indisponibilità
            indisp_sett = df_indisp[
                (df_indisp["Cod.Mecc."] == arbitro["Cod.Mecc."]) &
                (df_indisp["Inizio"] <= week_end) & (df_indisp["Fine"] >= week_start)
            ]
            for _, indisp in indisp_sett.iterrows():
                box += f"🛑 Indisponibile ({indisp['Motivo']})\n"

            st.code(box if box else "—", language="markdown")
