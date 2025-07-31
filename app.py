import streamlit as st
import pandas as pd
import pdfplumber
import datetime
import os

st.set_page_config(layout="wide")
st.title("Gestione Arbitri – C.A.N. D")

# Upload sezione
st.sidebar.header("📂 Caricamento dati settimanali")

arbitri_file = "Arbitri.xlsx"  # fisso e già incluso
gare_file = st.sidebar.file_uploader("📋 Gare CRA01 (.csv)", type=["csv"])
voti_pdf = st.sidebar.file_uploader("📑 Voti OA/OT (.pdf)", type=["pdf"])
indisponibili_file = st.sidebar.file_uploader("⛔ Indisponibilità (.xlsx)", type=["xlsx"])

# Impostazioni date
DATA_INIZIO = datetime.date(2025, 5, 1)
DATA_FINE = datetime.date(2025, 6, 30)

@st.cache_data
def carica_anagrafica():
    df = pd.read_excel(arbitri_file, dtype=str)
    df["Cod.Mecc."] = df["Cod.Mecc."].str.strip()
    return df

@st.cache_data
def carica_gare(file):
    df = pd.read_csv(file, dtype=str)
    df.columns = [c.strip() for c in df.columns]
    df["Cod.Mecc."] = df["Cod.Mecc."].str.strip()
    df["Data Gara"] = pd.to_datetime(df["Data Gara"], dayfirst=True, errors="coerce")
    return df

@st.cache_data
def carica_voti(pdf_file):
    voti = []
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue
            for line in text.split("\n"):
                if "Gara N." in line:
                    try:
                        numero_gara = line.split("Gara N.")[1].split()[0].strip()
                        voto_oa = voto_ot = ""
                        if "OA:" in line:
                            voto_oa = line.split("OA:")[1].split()[0].strip()
                        if "OT:" in line:
                            voto_ot = line.split("OT:")[1].split()[0].strip()
                        voti.append({"NumGara": numero_gara, "Voto OA": voto_oa, "Voto OT": voto_ot})
                    except:
                        pass
    return pd.DataFrame(voti)

@st.cache_data
def carica_indisponibili(file):
    df = pd.read_excel(file, dtype=str)
    df["Cod.Mecc."] = df["Cod.Mecc."].str.strip()
    df["Data"] = pd.to_datetime(df["Data"], dayfirst=True, errors="coerce")
    return df

# Caricamento dati
if gare_file and voti_pdf:
    df_arbitri = carica_anagrafica()
    df_gare = carica_gare(gare_file)
    df_voti = carica_voti(voti_pdf)

    df_gare["NumGara"] = df_gare["NumGara"].astype(str).str.strip()
    df_voti["NumGara"] = df_voti["NumGara"].astype(str).str.strip()

    df_merge = df_gare.merge(df_voti, on="NumGara", how="left")
    df_merge = df_merge.merge(df_arbitri, on="Cod.Mecc.", how="left")
    df_merge["Settimana"] = df_merge["Data Gara"].dt.to_period("W").apply(lambda r: r.start_time.strftime('%Y-%m-%d'))

    settimana_sel = st.selectbox("📆 Seleziona la settimana", sorted(df_merge["Settimana"].dropna().unique()))
    gironi = df_merge[df_merge["Settimana"] == settimana_sel]["Girone"].dropna().unique()
    girone_sel = st.selectbox("🏟️ Seleziona il girone", sorted(gironi))

    filtro = (df_merge["Settimana"] == settimana_sel) & (df_merge["Girone"] == girone_sel)
    df_settimana = df_merge[filtro].copy()

    if not df_settimana.empty:
        st.subheader(f"Gare settimana {settimana_sel} – Girone {girone_sel}")
        for cod_mecc, gruppo in df_settimana.groupby("Cod.Mecc."):
            arbitro = gruppo.iloc[0]
            col1, col2 = st.columns([1, 4])
            with col1:
                st.markdown(f"**{arbitro['Cognome']} {arbitro['Nome']}**")
                st.markdown(f"`{cod_mecc}` – {arbitro['Ruolo']}")
st.markdown(f"Sezione: {arbitro['Sezione']}  \nEtà: {arbitro['Età']}  \nAnzianità: {arbitro['Anzianità']}")
with col2:
                for _, gara in gruppo.iterrows():
                    info = f"🗓️ {gara['Data Gara'].date()} | Gara {gara['NumGara']} | OA: {gara['Voto OA']} – OT: {gara['Voto OT']}"
                    st.markdown(f"- {info}")

            if indisponibili_file:
                df_ind = carica_indisponibili(indisponibili_file)
                ind_arbitro = df_ind[(df_ind["Cod.Mecc."] == cod_mecc)]
                if not ind_arbitro.empty:
                    ind_sel = ind_arbitro[ind_arbitro["Data"].dt.to_period("W").apply(lambda r: r.start_time.strftime('%Y-%m-%d')) == settimana_sel]
                    for _, ind in ind_sel.iterrows():
                        st.warning(f"⚠️ Indisponibile il {ind['Data'].date()}: {ind['Motivo']}")

        # Calcolo medie voti
        medie = df_settimana.groupby("Cod.Mecc.")[["Voto OA", "Voto OT"]].apply(
            lambda x: pd.to_numeric(x, errors='coerce').mean()).reset_index()
        medie.columns = ["Cod.Mecc.", "Media Voto OA", "Media Voto OT"]
        st.subheader("📊 Medie OA / OT")
        st.dataframe(medie, use_container_width=True)

else:
    st.info("Caricare i file CRA01 (.csv) e PDF voti per iniziare.")
