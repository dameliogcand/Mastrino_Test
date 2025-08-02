import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from PyPDF2 import PdfReader
import io

st.set_page_config(layout="wide")
st.title("📊 Monitoraggio Arbitri – Periodo di Test")

# Funzione per generare tutte le settimane
def genera_settimane(data_inizio, data_fine):
    settimane = []
    data_corrente = data_inizio
    while data_corrente <= data_fine:
        fine_settimana = data_corrente + timedelta(days=6)
        settimane.append((data_corrente, fine_settimana))
        data_corrente += timedelta(days=7)
    return settimane

# Funzione per rinominare colonne in base ai file
def rinomina_colonne(df, tipo):
    if tipo == "arbitri":
        return df.rename(columns={
            df.columns[1]: "Cod.Mecc.",
            df.columns[2]: "Cognome",
            df.columns[3]: "Nome",
            df.columns[4]: "Sezione",
            df.columns[7]: "Età"
        })
    elif tipo == "gare":
        return df.rename(columns={
            df.columns[1]: "NumGara",
            df.columns[2]: "Categoria",
            df.columns[3]: "Girone",
            df.columns[6]: "DataGara",
            df.columns[16]: "Ruolo",
            df.columns[17]: "Cod.Mecc.",
            df.columns[18]: "Cognome"
        })
    elif tipo == "voti":
        return df.rename(columns={
            df.columns[0]: "NumGara",
            df.columns[8]: "Voto OA",
            df.columns[9]: "Voto OT"
        })
    elif tipo == "indisponibili":
        return df.rename(columns={
            df.columns[1]: "Cod.Mecc.",
            df.columns[8]: "Inizio",
            df.columns[9]: "Fine",
            df.columns[10]: "Motivo"
        })
    return df

# Funzioni di caricamento
@st.cache_data
def carica_anagrafica(uploaded_file):
    df = pd.read_excel(uploaded_file)
    df = rinomina_colonne(df, "arbitri")
    df["Cod.Mecc."] = df["Cod.Mecc."].astype(str).str.replace('.0', '', regex=False).str.strip()
    df["Età"] = df["Età"].astype(str).str.strip()
    return df

@st.cache_data
def carica_gare(uploaded_file):
    df = pd.read_excel(uploaded_file)
    df = rinomina_colonne(df, "gare")
    df["Cod.Mecc."] = df["Cod.Mecc."].astype(str).str.replace('.0', '', regex=False).str.strip()
    df["NumGara"] = df["NumGara"].astype(str).str.replace('.0', '', regex=False).str.strip()
    df["DataGara"] = pd.to_datetime(df["DataGara"], errors="coerce")
    return df

@st.cache_data
def carica_voti(uploaded_file):
    reader = PdfReader(uploaded_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    lines = text.split("\n")
    data = []
    for line in lines:
        cols = line.split()
        if len(cols) >= 10 and cols[0].isdigit():
            numgara = cols[0]
            voto_oa = cols[8].replace(",", ".")
            voto_ot = cols[9].replace(",", ".")
            data.append([numgara, voto_oa, voto_ot])
    df = pd.DataFrame(data, columns=["NumGara", "Voto OA", "Voto OT"])
    df = rinomina_colonne(df, "voti")
    df["NumGara"] = df["NumGara"].astype(str).str.replace('.0', '', regex=False).str.strip()
    return df

@st.cache_data
def carica_indisponibili(uploaded_file):
    df = pd.read_excel(uploaded_file)
    df = rinomina_colonne(df, "indisponibili")
    df["Cod.Mecc."] = df["Cod.Mecc."].astype(str).str.replace('.0', '', regex=False).str.strip()
    df["Inizio"] = pd.to_datetime(df["Inizio"], errors='coerce')
    df["Fine"] = pd.to_datetime(df["Fine"], errors='coerce')
    return df

# Upload file
with st.sidebar:
    arbitri_file = st.file_uploader("📥 Carica file Arbitri (.xlsx)", type=["xlsx"])
    gare_file = st.file_uploader("📥 Carica file Gare CRA01 (.xlsx)", type=["xlsx"])
    voti_file = st.file_uploader("📥 Carica file Voti OA/OT (.pdf)", type=["pdf"])
    indisponibili_file = st.file_uploader("📥 Carica file Indisponibilità (.xlsx)", type=["xlsx"])

# Caricamento dati
if arbitri_file:
    df_arbitri = carica_anagrafica(arbitri_file)
    df_indisp = carica_indisponibili(indisponibili_file) if indisponibili_file else pd.DataFrame()
    df_gare = carica_gare(gare_file) if gare_file else pd.DataFrame()
    df_voti_raw = carica_voti(voti_file) if voti_file else pd.DataFrame()

    # ✅ Verifica colonne chiave
    if 'NumGara' not in df_gare.columns or 'NumGara' not in df_voti_raw.columns:
        st.error("❌ Colonna 'NumGara' mancante per il merge.")
        st.stop()

    # Merge gare + voti
    df_merged = pd.merge(df_gare, df_voti_raw, on="NumGara", how="left")

    if df_merged.empty:
        st.warning("⚠️ Nessuna gara trovata nel file CRA01.")
    else:
        settimane = genera_settimane(datetime(2024, 5, 1), datetime(2024, 5, 31))

        for _, arbitro in df_arbitri.iterrows():
            st.markdown("---")
            st.subheader(f"👤 {arbitro['Cognome']} {arbitro['Nome']} ({arbitro['Cod.Mecc.']})")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f"**Sezione:** {arbitro['Sezione']}")
            with col2:
                st.markdown(f"**Età:** {arbitro['Età']}")

            cod_mecc = arbitro["Cod.Mecc."]
            cognome = arbitro["Cognome"]

            cols = st.columns(len(settimane))
            for idx, (inizio, fine) in enumerate(settimane):
                with cols[idx]:
                    st.markdown(f"**{inizio.strftime('%d/%m')} – {fine.strftime('%d/%m')}**")

                    # Gare
                    gare_sett = df_merged[
                        (df_merged["Cod.Mecc."] == cod_mecc) &
                        (df_merged["Cognome"].str.upper() == cognome.upper()) &
                        (df_merged["DataGara"] >= inizio) &
                        (df_merged["DataGara"] <= fine)
                    ]

                    if not gare_sett.empty:
                        for _, gara in gare_sett.iterrows():
                            cat = gara["Categoria"]
                            gir = gara["Girone"]
                            ruolo = gara["Ruolo"]
                            voto_oa = gara.get("Voto OA", "")
                            voto_ot = gara.get("Voto OT", "")
                            line = f"{cat} – {gir} – {ruolo}"
                            if voto_oa:
                                line += f"  \nOA: {voto_oa}"
                            if voto_ot:
                                line += f"  \nOT: {voto_ot}"
                            st.markdown(line)

                    # Indisponibilità
                    if not df_indisp.empty:
                        indisp = df_indisp[
                            (df_indisp["Cod.Mecc."] == cod_mecc) &
                            (df_indisp["Inizio"] <= fine) &
                            (df_indisp["Fine"] >= inizio)
                        ]
                        if not indisp.empty:
                            for _, row in indisp.iterrows():
                                st.markdown(f"❌ *Indisp.*: {row['Motivo']}")
