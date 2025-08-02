import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import PyPDF2

st.set_page_config(layout="wide")

# --- Funzione per generare le settimane ---
def genera_settimane(start_date, end_date):
    settimane = []
    current = start_date
    while current <= end_date:
        week_start = current
        week_end = current + timedelta(days=6)
        settimane.append((week_start, week_end))
        current += timedelta(days=7)
    return settimane

SETTIMANE = genera_settimane(datetime(2025, 5, 1), datetime(2025, 5, 31))

# --- Mappature colonne ---
def rinomina_colonne(df, tipo):
    mappature = {
        "arbitri": {
            0: "Cod.Mecc.", 1: "Cognome", 2: "Nome", 3: "Sezione", 4: "Anzianità", 5: "Età"
        },
        "gare": {
            1: "NumGara", 2: "Categoria", 3: "Girone", 6: "DataGara", 16: "Ruolo", 17: "Cod.Mecc.", 18: "Cognome"
        },
        "voti": {
            0: "NumGara", 8: "Voto OA", 9: "Voto OT"
        },
        "indisponibili": {
            0: "Cod.Mecc.", 7: "Inizio", 8: "Fine", 9: "Motivo"
        }
    }
    mappa = mappature.get(tipo)
    if mappa:
        df = df.rename(columns={df.columns[i]: nome for i, nome in mappa.items() if i < len(df.columns)})
    return df

# --- Caricamento file ---
@st.cache_data
def carica_anagrafica(file):
    df = pd.read_excel(file)
    if len(df.columns) < 6:
        st.error("❌ Il file arbitri ha meno colonne del previsto.")
        st.stop()
    df = rinomina_colonne(df, "arbitri")
    df["Cod.Mecc."] = df["Cod.Mecc."].astype(str).str.zfill(8).str.strip()
    df["Cognome"] = df["Cognome"].astype(str).str.strip().str.upper()
    return df

@st.cache_data
def carica_gare(file):
    df = pd.read_excel(file)
    if len(df.columns) < 19:
        st.error("❌ Il file CRA01 ha meno colonne del previsto.")
        st.stop()
    df = rinomina_colonne(df, "gare")
    df["Cod.Mecc."] = df["Cod.Mecc."].astype(str).str.zfill(7).str.strip()
    df["Cognome"] = df["Cognome"].str.strip().str.upper()
    df["NumGara"] = df["NumGara"].astype(str).str.replace(".0", "", regex=False).str.strip()
    df["DataGara"] = pd.to_datetime(df["DataGara"], errors="coerce")
    return df

@st.cache_data
def carica_voti(file):
    reader = PyPDF2.PdfReader(file)
    data = []
    for page in reader.pages:
        text = page.extract_text()
        if not text:
            continue
        for line in text.split("\n"):
            parts = line.split()
            if len(parts) >= 10 and parts[0].isdigit():
                numgara = parts[0].strip()
                voto_oa = parts[8].replace(",", ".").strip()
                voto_ot = parts[9].replace(",", ".").strip()
                data.append({"NumGara": numgara, "Voto OA": voto_oa, "Voto OT": voto_ot})
    df = pd.DataFrame(data)
    df["NumGara"] = df["NumGara"].astype(str).str.strip()
    return df

@st.cache_data
def carica_indisponibili(file):
    df = pd.read_excel(file)
    df = rinomina_colonne(df, "indisponibili")
    df["Cod.Mecc."] = df["Cod.Mecc."].astype(str).str.zfill(8).str.strip()
    df["Inizio"] = pd.to_datetime(df["Inizio"], errors="coerce")
    df["Fine"] = pd.to_datetime(df["Fine"], errors="coerce")
    return df

# --- Caricamento da Streamlit ---
st.title("Gestione Arbitri – Periodo di Test")

arbitri_file = st.file_uploader("📋 Carica file Arbitri.xlsx", type=["xlsx"])
gare_file = st.file_uploader("📑 Carica file CRA01.xlsx", type=["xlsx"])
voti_file = st.file_uploader("📄 Carica file Stampa_Elenco_Voti.pdf", type=["pdf"])
indisponibili_file = st.file_uploader("🚫 Carica file Indisponibili.xlsx", type=["xlsx"])

if arbitri_file:
    df_arbitri = carica_anagrafica(arbitri_file)
    df_gare = carica_gare(gare_file) if gare_file else pd.DataFrame()
    df_voti = carica_voti(voti_file) if voti_file else pd.DataFrame()
    df_indisp = carica_indisponibili(indisponibili_file) if indisponibili_file else pd.DataFrame()

    # --- Merge gare e voti ---
    if "NumGara" not in df_voti.columns or "NumGara" not in df_gare.columns:
        st.error("❌ Colonna 'NumGara' mancante per il merge.")
        st.stop()
    df_merged = pd.merge(df_gare, df_voti, on="NumGara", how="left")

    # --- Visualizzazione Arbitri ---
    for _, arbitro in df_arbitri.iterrows():
        st.markdown("---")
        st.subheader(f"{arbitro['Cognome']} {arbitro['Nome']}")
        col1, col2, col3 = st.columns(3)
        col1.markdown(f"**Cod.Mecc.:** {arbitro['Cod.Mecc.']}")
        col2.markdown(f"**Sezione:** {arbitro['Sezione']}")
        col3.markdown(f"**Età:** {arbitro['Età']}")

        tabella = []
        for settimana in SETTIMANE:
            inizio, fine = settimana
            cella = ""

            gare_sett = df_merged[
                (df_merged["Cod.Mecc."].astype(str).str[-7:] == arbitro["Cod.Mecc."].zfill(8)[-7:]) &
                (df_merged["Cognome"] == arbitro["Cognome"]) &
                (df_merged["DataGara"] >= inizio) &
                (df_merged["DataGara"] <= fine)
            ]

            for _, gara in gare_sett.iterrows():
                cat = gara.get("Categoria", "")
                girone = gara.get("Girone", "")
                ruolo = gara.get("Ruolo", "")
                oa = gara.get("Voto OA", "")
                ot = gara.get("Voto OT", "")
                voti = f"OA: {oa}" if pd.notna(oa) else ""
                voti += f" OT: {ot}" if pd.notna(ot) else ""
                cella += f"{cat} – {girone} – {ruolo} {voti}\n"

            # Indisponibilità
            indisp = df_indisp[
                (df_indisp["Cod.Mecc."] == arbitro["Cod.Mecc."]) &
                (df_indisp["Inizio"] <= fine) &
                (df_indisp["Fine"] >= inizio)
            ]
            for _, r in indisp.iterrows():
                cella += f"INDISP: {r['Motivo']}\n"

            tabella.append(cella.strip())

        df_tab = pd.DataFrame([tabella], columns=[f"{i[0].strftime('%d/%m')} – {i[1].strftime('%d/%m')}" for i in SETTIMANE])
        st.dataframe(df_tab.T, use_container_width=True)
