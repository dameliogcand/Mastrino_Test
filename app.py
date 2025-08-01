import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from PyPDF2 import PdfReader

st.set_page_config(layout="wide")
st.title("📊 Monitoraggio Arbitri – Periodo di test (01/05/2024 – 31/05/2024)")

# Funzione per caricare l'anagrafica
@st.cache_data
def carica_anagrafica(file):
    df = pd.read_excel(file)
    df = df.rename(columns={
        "Cod.Mecc.": "Cod.Mecc.",
        "Cognome": "Cognome",
        "Nome": "Nome",
        "Sezione": "Sezione",
        "Età": "Età"
    })
    df["Cod.Mecc."] = df["Cod.Mecc."].astype(str).str.replace('.0', '', regex=False).str.strip()
    return df[["Cod.Mecc.", "Cognome", "Nome", "Sezione", "Età"]]

# Funzione per caricare le gare dal file Excel cra01
@st.cache_data
def carica_gare(file):
    df = pd.read_excel(file, header=0)
    df = df.rename(columns={
        "Column2": "NumGara",
        "Column18": "Cod.Mecc.",
        "Column19": "Cognome",
        "Column7": "DataGara",
        "Column3": "Categoria",
        "Column4": "Girone",
        "Column17": "Ruolo"
    })
    df = df[["NumGara", "Cod.Mecc.", "Cognome", "DataGara", "Categoria", "Girone", "Ruolo"]]
    df["NumGara"] = df["NumGara"].astype(str).str.replace('.0', '', regex=False).str.strip()
    df["Cod.Mecc."] = df["Cod.Mecc."].astype(str).str.replace('.0', '', regex=False).str.strip()
    df["DataGara"] = pd.to_datetime(df["DataGara"], errors='coerce')
    return df

# Funzione per caricare i voti da PDF
@st.cache_data
def carica_voti(file):
    reader = PdfReader(file)
    data = []
    for page in reader.pages:
        lines = page.extract_text().split("\n")
        for line in lines:
            parts = line.strip().split()
            if len(parts) >= 10 and parts[0].replace('.', '', 1).isdigit():
                num_gara = parts[0].strip()
                voto_oa = parts[8].replace(",", ".")
                voto_ot = parts[9].replace(",", ".")
                data.append([num_gara, voto_oa, voto_ot])
    df = pd.DataFrame(data, columns=["NumGara", "Voto OA", "Voto OT"])
    df["NumGara"] = df["NumGara"].astype(str).str.replace('.0', '', regex=False).str.strip()
    return df

# Funzione per caricare le indisponibilità
@st.cache_data
def carica_indisponibili(file):
    df = pd.read_excel(file)
    df = df.rename(columns={
        "Cod.Mecc.": "Cod.Mecc.",
        "Inizio": "Inizio",
        "Fine": "Fine",
        "Motivo": "Motivo"
    })
    df["Cod.Mecc."] = df["Cod.Mecc."].astype(str).str.replace('.0', '', regex=False).str.strip()
    df["Inizio"] = pd.to_datetime(df["Inizio"], errors='coerce')
    df["Fine"] = pd.to_datetime(df["Fine"], errors='coerce')
    return df[["Cod.Mecc.", "Inizio", "Fine", "Motivo"]]

# Upload dei file
anagrafica_file = st.file_uploader("📁 Carica il file Arbitri.xlsx", type=["xlsx"], key="arbitri")
gare_file = st.file_uploader("📁 Carica il file CRA01.xlsx", type=["xlsx"], key="gare")
voti_file = st.file_uploader("📁 Carica il file dei voti (.pdf)", type=["pdf"], key="voti")
indisponibili_file = st.file_uploader("📁 Carica il file Indisponibili.xlsx", type=["xlsx"], key="indisp")

if anagrafica_file:
    df_arbitri = carica_anagrafica(anagrafica_file)
else:
    st.stop()

df_gare = carica_gare(gare_file) if gare_file else pd.DataFrame()
df_voti_raw = carica_voti(voti_file) if voti_file else pd.DataFrame()
df_indisp = carica_indisponibili(indisponibili_file) if indisponibili_file else pd.DataFrame()

# Merge gare + voti sul NumGara
if not df_voti_raw.empty and not df_gare.empty:
    st.write("✅ Colonne in df_gare prima del merge:", df_gare.columns.tolist())
    st.write("✅ Colonne in df_voti_raw prima del merge:", df_voti_raw.columns.tolist())

    df_merged = pd.merge(df_gare, df_voti_raw, on="NumGara", how="left")

    st.write("✅ Colonne in df_merged dopo il merge:", df_merged.columns.tolist())
else:
    df_merged = df_gare.copy()

if "Cod.Mecc." not in df_merged.columns:
    st.error("❌ Colonna 'Cod.Mecc.' non trovata nel DataFrame unito.")
    st.write("Colonne disponibili:", df_merged.columns.tolist())
    st.stop()


# Verifica presenza Cod.Mecc.
if "Cod.Mecc." not in df_merged.columns:
    st.error("❌ Colonna 'Cod.Mecc.' non trovata nel DataFrame unito.")
    st.write("Colonne disponibili:", list(df_merged.columns))
    st.stop()

# Settimane del periodo test
inizio_periodo = datetime(2024, 5, 1)
fine_periodo = datetime(2024, 5, 31)
settimane = []
data_corrente = inizio_periodo
while data_corrente <= fine_periodo:
    fine_settimana = data_corrente + timedelta(days=6)
    settimane.append((data_corrente, fine_settimana))
    data_corrente += timedelta(days=7)

# Visualizzazione
for _, arbitro in df_arbitri.iterrows():
    st.markdown(f"### {arbitro['Cognome']} {arbitro['Nome']}")
    col1, col2, col3 = st.columns(3)
    col1.markdown(f"**Cod.Mecc.:** {arbitro['Cod.Mecc.']}")
    col2.markdown(f"**Sezione:** {arbitro['Sezione']}")
    col3.markdown(f"**Età:** {arbitro['Età']}")

    for inizio_sett, fine_sett in settimane:
        st.markdown(f"#### 🗓️ Settimana {inizio_sett.strftime('%d/%m/%Y')} – {fine_sett.strftime('%d/%m/%Y')}")
        gare_sett = df_merged[
            (df_merged["Cod.Mecc."] == arbitro["Cod.Mecc."]) &
            (df_merged["Cognome"].str.upper() == arbitro["Cognome"].upper()) &
            (df_merged["DataGara"] >= inizio_sett) &
            (df_merged["DataGara"] <= fine_sett)
        ]

        indisp_sett = df_indisp[
            (df_indisp["Cod.Mecc."] == arbitro["Cod.Mecc."]) &
            (df_indisp["Inizio"] <= fine_sett) &
            (df_indisp["Fine"] >= inizio_sett)
        ]

        if gare_sett.empty and indisp_sett.empty:
            st.markdown("ℹ️ Nessuna gara o indisponibilità.")
        else:
            for _, gara in gare_sett.iterrows():
                ruolo = gara["Ruolo"]
                cat = gara["Categoria"]
                gir = gara["Girone"]
                voto_oa = gara.get("Voto OA", "")
                voto_ot = gara.get("Voto OT", "")
                descrizione = f"**{cat} – {gir} – {ruolo}**"
                if pd.notna(voto_oa):
                    descrizione += f" – OA: {voto_oa}"
                if pd.notna(voto_ot):
                    descrizione += f" – OT: {voto_ot}"
                st.markdown(descrizione)

            for _, ind in indisp_sett.iterrows():
                motivo = ind["Motivo"]
                st.markdown(f"❌ **Indisponibile:** {motivo}")

st.success("✅ Visualizzazione completata.")
