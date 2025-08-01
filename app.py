import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from PyPDF2 import PdfReader

st.set_page_config(layout="wide")

# Funzione per caricare l'anagrafica
@st.cache_data
def carica_anagrafica(file):
    df = pd.read_excel(file)
    df = df[["Cod.Mecc.", "Cognome", "Nome", "Sezione", "Età"]]
    df["Cod.Mecc."] = df["Cod.Mecc."].astype(str).str.replace(".0", "", regex=False).str.strip()
    df["Cognome"] = df["Cognome"].str.strip().str.upper()
    return df

# Funzione per caricare il file CRA01
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
    df["Cod.Mecc."] = df["Cod.Mecc."].astype(str).str.replace(".0", "", regex=False).str.strip()
    df["Cognome"] = df["Cognome"].str.strip().str.upper()
    df["NumGara"] = df["NumGara"].astype(str).str.replace(".0", "", regex=False).str.strip()
    df["DataGara"] = pd.to_datetime(df["DataGara"], errors="coerce")
    return df

# Funzione per caricare i voti dal PDF
@st.cache_data
def carica_voti(file):
    reader = PdfReader(file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"

    rows = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 10 and parts[0].isdigit():
            num_gara = parts[0].strip()
            voto_oa = parts[8].replace(",", ".")
            voto_ot = parts[9].replace(",", ".")
            rows.append([num_gara, voto_oa, voto_ot])

    df = pd.DataFrame(rows, columns=["NumGara", "Voto OA", "Voto OT"])
    df["NumGara"] = df["NumGara"].astype(str).str.strip()
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
    df["Cod.Mecc."] = df["Cod.Mecc."].astype(str).str.replace(".0", "", regex=False).str.strip()
    df["Inizio"] = pd.to_datetime(df["Inizio"], errors="coerce")
    df["Fine"] = pd.to_datetime(df["Fine"], errors="coerce")
    return df

# Upload dei file
st.title("Visualizzazione Gare, Voti e Indisponibilità")
anagrafica_file = st.file_uploader("Carica il file ANAGRAFICA (Arbitri.xlsx)", type=["xlsx"])
gare_file = st.file_uploader("Carica il file GARE (cra01.xlsx)", type=["xlsx"])
voti_file = st.file_uploader("Carica il file VOTI (Stampa_Elenco_Voti.pdf)", type=["pdf"])
indisponibili_file = st.file_uploader("Carica il file INDISPONIBILITÀ (Indisponibili.xlsx)", type=["xlsx"])

if anagrafica_file:
    df_arbitri = carica_anagrafica(anagrafica_file)
    df_gare = carica_gare(gare_file) if gare_file else pd.DataFrame()
    df_voti_raw = carica_voti(voti_file) if voti_file else pd.DataFrame()
    df_indisp = carica_indisponibili(indisponibili_file) if indisponibili_file else pd.DataFrame()

    # Merge gare con voti su NumGara
    if not df_voti_raw.empty and not df_gare.empty:
        df_merged = pd.merge(df_gare, df_voti_raw, on="NumGara", how="left")
    else:
        df_merged = df_gare.copy()

    # Periodo fisso di test
    start_date = datetime(2025, 5, 1)
    end_date = datetime(2025, 5, 31)
    num_weeks = (end_date - start_date).days // 7 + 1

    for _, arbitro in df_arbitri.iterrows():
        st.markdown(f"### {arbitro['Cognome']} {arbitro['Nome']}")
        cols = st.columns([1, 1, 1])
        cols[0].markdown(f"**Sezione:** {arbitro['Sezione']}")
        cols[1].markdown(f"**Cod.Mecc.:** {arbitro['Cod.Mecc.']}")
        cols[2].markdown(f"**Età:** {arbitro['Età']}")

        # Riga settimanale
        for w in range(num_weeks):
            week_start = start_date + timedelta(weeks=w)
            week_end = week_start + timedelta(days=6)
            week_label = f"**Settimana {w+1}**<br>{week_start.strftime('%d/%m')} - {week_end.strftime('%d/%m')}"
            st.markdown(week_label, unsafe_allow_html=True)

            box = ""

            # Gare
            gare_sett = df_merged[
                (df_merged["Cod.Mecc."] == arbitro["Cod.Mecc."]) &
                (df_merged["Cognome"] == arbitro["Cognome"]) &
                (df_merged["DataGara"] >= week_start) &
                (df_merged["DataGara"] <= week_end)
            ]
            for _, gara in gare_sett.iterrows():
                cat = gara["Categoria"]
                gir = gara["Girone"]
                ruolo = gara["Ruolo"]
                voto_oa = gara.get("Voto OA", "")
                voto_ot = gara.get("Voto OT", "")
                voti_str = ""
                if pd.notna(voto_oa):
                    voti_str += f" OA: {voto_oa}"
                if pd.notna(voto_ot):
                    voti_str += f" OT: {voto_ot}"
                box += f"**{cat} – {gir} – {ruolo}**{voti_str}<br>"

            # Indisponibilità
            if not df_indisp.empty:
                indisp_sett = df_indisp[
                    (df_indisp["Cod.Mecc."] == arbitro["Cod.Mecc."]) &
                    (df_indisp["Inizio"] <= week_end) &
                    (df_indisp["Fine"] >= week_start)
                ]
                for _, ind in indisp_sett.iterrows():
                    box += f"<span style='color:red'>INDISPONIBILE: {ind['Motivo']}</span><br>"

            if box == "":
                box = "<span style='color:gray'>-</span>"

            st.markdown(f"<div style='border:1px solid #ddd; padding:6px; border-radius:4px; background:#f9f9f9'>{box}</div>", unsafe_allow_html=True)
