import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from PyPDF2 import PdfReader

st.set_page_config(layout="wide")
st.title("📊 Visualizzazione Arbitri – Periodo Test")

# ------------------------------------
# 🔁 Rinomina colonne in base al tipo
# ------------------------------------
def rinomina_colonne(df, tipo):
    try:
        if tipo == "arbitri":
            if len(df.columns) < 6:
                st.error("❌ Il file Arbitri ha meno di 6 colonne.")
                st.stop()
            return df.rename(columns={
                df.columns[2]: "Cod.Mecc.",
                df.columns[3]: "Cognome",
                df.columns[4]: "Nome",
                df.columns[5]: "Sezione",
                df.columns[6]: "Età"
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
    except Exception as e:
        st.error(f"Errore durante la rinomina colonne ({tipo}): {e}")
        st.stop()

# -------------------------------
# 📥 Caricamento dati
# -------------------------------
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
    df["DataGara"] = pd.to_datetime(df["DataGara"], errors="coerce")
    return df

@st.cache_data
def carica_voti(file):
    pdf = PdfReader(file)
    text = ""
    for page in pdf.pages:
        text += page.extract_text() + "\n"
    lines = text.splitlines()
    rows = [line.split() for line in lines if line.strip()]
    df = pd.DataFrame(rows)
    if len(df.columns) < 10:
        st.error("❌ Il PDF non contiene abbastanza colonne.")
        st.stop()
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

# -------------------------------
# 📤 Upload file
# -------------------------------
arbitri_file = st.file_uploader("📋 Carica Arbitri.xlsx", type="xlsx")
gare_file = st.file_uploader("📂 Carica CRA01.xlsx", type="xlsx")
voti_file = st.file_uploader("📄 Carica PDF Voti", type="pdf")
indisponibili_file = st.file_uploader("🚫 Carica Indisponibili.xlsx", type="xlsx")

if not arbitri_file:
    st.warning("🔄 Carica almeno il file Arbitri per iniziare.")
    st.stop()

df_arbitri = carica_anagrafica(arbitri_file)
df_gare = carica_gare(gare_file) if gare_file else pd.DataFrame()
df_voti = carica_voti(voti_file) if voti_file else pd.DataFrame()
df_indisp = carica_indisponibili(indisponibili_file) if indisponibili_file else pd.DataFrame()

# -------------------------------
# 🔗 Merge Gare + Voti
# -------------------------------
if "NumGara" in df_gare.columns and "NumGara" in df_voti.columns:
    df_merged = pd.merge(df_gare, df_voti, on="NumGara", how="left")
else:
    st.error("❌ Colonna 'NumGara' mancante per il merge.")
    df_merged = pd.DataFrame()

# -------------------------------
# 📅 Settimane di riferimento
# -------------------------------
inizio, fine = datetime(2025, 5, 1), datetime(2025, 5, 31)
settimane = []
start = inizio
while start <= fine:
    end = start + timedelta(days=6)
    settimane.append((start, end))
    start += timedelta(days=7)

# -------------------------------
# 👤 Visualizzazione arbitri
# -------------------------------
for _, arbitro in df_arbitri.iterrows():
    with st.expander(f"{arbitro['Cognome']} {arbitro['Nome']} – {arbitro['Sezione']}"):
        col1, col2 = st.columns(2)
        col1.markdown(f"**Cod.Mecc.:** {arbitro['Cod.Mecc.']}")
        col2.markdown(f"**Età:** {arbitro['Età']}")

        for inizio_sett, fine_sett in settimane:
            st.markdown(f"📆 **Settimana {inizio_sett.strftime('%d/%m')} – {fine_sett.strftime('%d/%m')}**")
            eventi = []

            # Gare dell'arbitro nella settimana
            gare_sett = df_merged[
                (df_merged["Cod.Mecc."] == arbitro["Cod.Mecc."]) &
                (df_merged["Cognome"].str.upper() == arbitro["Cognome"].upper()) &
                (df_merged["DataGara"] >= inizio_sett) &
                (df_merged["DataGara"] <= fine_sett)
            ]

            for _, gara in gare_sett.iterrows():
                info = f"{gara['Categoria']} – {gara['Girone']} – {gara['Ruolo']}"
                if pd.notna(gara.get("Voto OA")):
                    info += f" – OA: {gara['Voto OA']:.2f}"
                if pd.notna(gara.get("Voto OT")):
                    info += f" OT: {gara['Voto OT']:.2f}"
                eventi.append(info)

            # Indisponibilità nella settimana
            indisponibile = df_indisp[
                (df_indisp["Cod.Mecc."] == arbitro["Cod.Mecc."]) &
                (df_indisp["Inizio"] <= fine_sett) & (df_indisp["Fine"] >= inizio_sett)
            ]
            for _, r in indisponibile.iterrows():
                eventi.append(f"🚫 Indisponibile – {r['Motivo']}")

            if eventi:
                for e in eventi:
                    st.markdown(f"- {e}")
            else:
                st.markdown("_Nessun evento_")
