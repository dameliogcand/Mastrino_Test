import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from PyPDF2 import PdfReader

st.set_page_config(layout="wide")
st.title("Gestione Arbitri - Periodo di Test (01/05/2025 - 30/06/2025)")

# Funzioni per caricare i dati
@st.cache_data
def carica_anagrafica():
    st.write("Colonne in df_merged:", df_merged.columns.tolist())
    df = pd.read_excel("Arbitri.xlsx")
    df.columns = df.columns.str.strip()
    df["Cod.Mecc."] = df["Cod.Mecc."].astype(str).str.replace('.0', '', regex=False).str.strip()
    df["Età"] = df["Età"].astype(str).str.strip()
    return df

@st.cache_data
def carica_gare(file):
    df = pd.read_excel(file, header=None)
    df = df[[2, 3, 4, 7, 17, 18]]  # NumGara, Categoria, Girone, DataGara, Ruolo, Cod.Mecc.
    df.columns = ["Columns2", "Columns3", "Columns4", "Columns7", "Columns17", "Columns18"]
    df["Cod.Mecc."] = df["Cod.Mecc."].astype(str).str.replace('.0', '', regex=False).str.strip()
    df["NumGara"] = df["NumGara"].astype(str).str.replace('.0', '', regex=False).str.strip()
    df["DataGara"] = pd.to_datetime(df["DataGara"], errors="coerce")
    return df

@st.cache_data
def carica_voti(pdf_file):
    reader = PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    lines = text.split("\n")
    records = []
    for line in lines:
        parts = line.strip().split()
        if len(parts) >= 3:
            num_gara = parts[0]
            try:
                voto_oa = float(parts[-2].replace(",", "."))
                voto_ot = float(parts[-1].replace(",", "."))
                records.append({
                    "NumGara": num_gara,
                    "Voto OA": voto_oa,
                    "Voto OT": voto_ot
                })
            except:
                continue
    df = pd.DataFrame(records)
    df["NumGara"] = df["NumGara"].astype(str).str.replace('.0', '', regex=False).str.strip()
    return df

@st.cache_data
def carica_indisponibili(file):
    df = pd.read_excel(file)
    df.columns = df.columns.str.strip()
    df["Cod.Mecc."] = df["Cod.Mecc."].astype(str).str.replace('.0', '', regex=False).str.strip()
    df["Inizio"] = pd.to_datetime(df["Inizio"], errors="coerce")
    df["Fine"] = pd.to_datetime(df["Fine"], errors="coerce")
    return df

# Upload file
st.sidebar.header("Caricamento File Settimanali")
gare_file = st.sidebar.file_uploader("Carica file GARE (.xlsx)", type=["xlsx"])
voti_file = st.sidebar.file_uploader("Carica file VOTI (.pdf)", type=["pdf"])
indisponibili_file = st.sidebar.file_uploader("Carica file INDISPONIBILITÀ (.xlsx)", type=["xlsx"])

# Caricamento anagrafica fissa
df_arbitri = carica_anagrafica()

# Caricamento dinamico
df_gare = carica_gare(gare_file) if gare_file else pd.DataFrame()
df_voti_raw = carica_voti(voti_file) if voti_file else pd.DataFrame()
df_indisp = carica_indisponibili(indisponibili_file) if indisponibili_file else pd.DataFrame()

# Merge voti-gare (tramite NumGara)
if not df_voti_raw.empty and not df_gare.empty:
    if "NumGara" not in df_voti_raw.columns or "NumGara" not in df_gare.columns:
        st.error("❌ Errore: manca la colonna 'NumGara' nei dati.")
        st.stop()
    df_merged = pd.merge(df_gare, df_voti_raw, on="NumGara", how="left")
else:
    df_merged = df_gare.copy()

# Creazione calendario settimanale
start_date = datetime(2025, 5, 1)
end_date = datetime(2025, 6, 30)
weeks = []
current = start_date
while current <= end_date:
    week_start = current
    week_end = current + timedelta(days=6)
    weeks.append((week_start, week_end))
    current += timedelta(days=7)

# Visualizzazione
for _, arbitro in df_arbitri.iterrows():
    st.markdown(f"### {arbitro['Cognome']} {arbitro['Nome']}")
    col1, col2, col3 = st.columns(3)
    col1.markdown(f"**Sezione:** {arbitro['Sezione']}")
    col2.markdown(f"**Età:** {arbitro['Età']}")

    cod_mecc = str(arbitro["Cod.Mecc."]).strip()
    row = []
    for week_start, week_end in weeks:
        cell = ""
        gare_sett = df_merged[
            (df_merged["Cod.Mecc."] == cod_mecc) &
            (df_merged["DataGara"] >= week_start) &
            (df_merged["DataGara"] <= week_end)
        ]
        for _, gara in gare_sett.iterrows():
            info = f"{gara['Categoria']} – {gara['Girone']} – {gara['Ruolo']}"
            if not pd.isna(gara.get("Voto OA")):
                info += f" – OA: {gara['Voto OA']:.2f}"
            if not pd.isna(gara.get("Voto OT")):
                info += f" OT: {gara['Voto OT']:.2f}"
            cell += info + "<br>"

        # Indisponibilità
        if not df_indisp.empty:
            indispo = df_indisp[
                (df_indisp["Cod.Mecc."] == cod_mecc) &
                (df_indisp["Inizio"] <= week_end) &
                (df_indisp["Fine"] >= week_start)
            ]
            for _, row_ind in indispo.iterrows():
                cell += f"<span style='color:red;'>INDISP: {row_ind['Motivo']}</span><br>"

        row.append(cell if cell else "-")

    df_settimane = pd.DataFrame([row], columns=[f"{w[0].strftime('%d/%m')} – {w[1].strftime('%d/%m')}" for w in weeks])
    st.write(df_settimane.style.set_properties(**{"text-align": "left"}).set_table_styles([{
        'selector': 'th',
        'props': [('text-align', 'center')]
    }]))
    st.markdown("---")
