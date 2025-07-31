import streamlit as st
import pandas as pd
import datetime
from PyPDF2 import PdfReader

st.set_page_config(layout="wide")

# === Funzione: Carica anagrafica arbitri (fissa) ===
@st.cache_data
def carica_anagrafica():
    df = pd.read_excel("Arbitri.xlsx")
    df["Cod.Mecc."] = df["Cod.Mecc."].astype(str).str.strip()
    return df

# === Funzione: Carica gare da file Excel senza intestazioni ===
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
    df["NumGara"] = df["NumGara"].astype(str).str.strip()
    df["DataGara"] = pd.to_datetime(df["DataGara"], errors="coerce")
    return df

# === Funzione: Estrai voti da PDF ===
@st.cache_data
def estrai_voti(pdf_file):
    reader = PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    righe = text.split("\n")
    dati = []
    for riga in righe:
        parti = riga.split()
        if len(parti) >= 4 and parti[0].isdigit():
            num_gara = parti[0]
            oa = None
            ot = None
            for i in range(1, len(parti) - 1):
                if parti[i] == "OA:":
                    oa = parti[i + 1].replace(",", ".")
                elif parti[i] == "OT:":
                    ot = parti[i + 1].replace(",", ".")
            dati.append({"NumGara": num_gara, "Voto_OA": oa, "Voto_OT": ot})
    return pd.DataFrame(dati)

# === Funzione: Carica indisponibilità ===
@st.cache_data
def carica_indisponibili(file):
    df = pd.read_excel(file)
    df["Cod.Mecc."] = df["Cod.Mecc."].astype(str).str.strip()
    df["Inizio"] = pd.to_datetime(df["Inizio"], errors="coerce")
    df["Fine"] = pd.to_datetime(df["Fine"], errors="coerce")
    return df

# === Funzione: Crea lista settimane ===
def get_settimane(start, end):
    settimane = []
    data = start
    while data <= end:
        fine = data + datetime.timedelta(days=6)
        settimane.append((data, fine))
        data += datetime.timedelta(days=7)
    return settimane

# === Caricamento iniziale ===
st.title("Gestione Arbitri - Gare, Voti, Indisponibilità")
df_arbitri = carica_anagrafica()

# Upload settimanale file
with st.sidebar:
    st.header("📂 Caricamento file")
    gare_file = st.file_uploader("Carica file gare (.xlsx)", type=["xlsx"])
    voti_file = st.file_uploader("Carica file voti (.pdf)", type=["pdf"])
    indisponibili_file = st.file_uploader("Carica indisponibilità (.xlsx)", type=["xlsx"])

# Parsing file
df_gare = carica_gare(gare_file) if gare_file else pd.DataFrame()
df_voti_raw = estrai_voti(voti_file) if voti_file else pd.DataFrame()
df_indisp = carica_indisponibili(indisponibili_file) if indisponibili_file else pd.DataFrame()

# Verifica colonne necessarie prima del merge
if not df_voti_raw.empty and not df_gare.empty:
    if "NumGara" not in df_voti_raw.columns or "NumGara" not in df_gare.columns:
        st.error("❌ Errore: Colonna 'NumGara' mancante in uno dei file.")
        st.stop()
    if "Cod.Mecc." not in df_gare.columns:
        st.error("❌ Errore: Colonna 'Cod.Mecc.' mancante nel file gare.")
        st.stop()
    df_merged = pd.merge(df_gare, df_voti_raw, on="NumGara", how="left")
else:
    df_merged = df_gare.copy()

# Crea settimane dal 01/05/2025 al 30/06/2025
settimane = get_settimane(datetime.date(2025, 5, 1), datetime.date(2025, 6, 30))

# === Visualizzazione per arbitro ===
for _, arbitro in df_arbitri.iterrows():
    cod_mecc = str(arbitro["Cod.Mecc."]).strip()
    st.markdown(f"### {arbitro['Cognome']} {arbitro['Nome']} ({cod_mecc})")

    col1, col2 = st.columns(2)
    col1.markdown(f"**Sezione:** {arbitro['Sezione']}")
    col2.markdown(f"**Età:** {arbitro['Età']}")

    # Visualizzazione griglia settimanale
    cols = st.columns(len(settimane))
    for i, (inizio, fine) in enumerate(settimane):
        label_settimana = f"{inizio.strftime('%d/%m')} - {fine.strftime('%d/%m')}"
        contenuto = ""

        # Gare in settimana
        gare_sett = df_merged[
            (df_merged["Cod.Mecc."] == cod_mecc) &
            (df_merged["DataGara"] >= pd.Timestamp(inizio)) &
            (df_merged["DataGara"] <= pd.Timestamp(fine))
        ]
        for _, gara in gare_sett.iterrows():
            categoria = gara.get("Categoria", "")
            girone = gara.get("Girone", "")
            ruolo = gara.get("Ruolo", "")
            oa = gara.get("Voto_OA", "")
            ot = gara.get("Voto_OT", "")
            contenuto += f"{categoria} – {girone} – {ruolo}"
            if pd.notna(oa):
                contenuto += f"<br/>OA: {oa}"
            if pd.notna(ot):
                contenuto += f"<br/>OT: {ot}"
            contenuto += "<br/><br/>"

        # Indisponibilità in settimana
        if not df_indisp.empty:
            indisp_sett = df_indisp[
                (df_indisp["Cod.Mecc."] == cod_mecc) &
                (df_indisp["Inizio"] <= pd.Timestamp(fine)) &
                (df_indisp["Fine"] >= pd.Timestamp(inizio))
            ]
            for _, row in indisp_sett.iterrows():
                motivo = row.get("Motivo", "")
                contenuto += f"<span style='color:red;'>Indisponibile: {motivo}</span><br/><br/>"

        # Scrittura nella colonna settimanale
        if contenuto:
            cols[i].markdown(f"**{label_settimana}**<br/>{contenuto}", unsafe_allow_html=True)
        else:
            cols[i].markdown(f"**{label_settimana}**<br/><span style='color:gray;'>–</span>", unsafe_allow_html=True)

    st.markdown("---")
