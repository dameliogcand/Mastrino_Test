import streamlit as st
import pandas as pd
import pdfplumber
from datetime import datetime, timedelta

st.set_page_config(layout="wide")

DATA_INIZIO = datetime(2025, 5, 1)
DATA_FINE = datetime(2025, 6, 30)

@st.cache_data
def carica_anagrafica():
    df = pd.read_excel("Arbitri.xlsx")
    df.columns = [c.strip() for c in df.columns]
    if "Cod.Mecc." not in df.columns:
        st.error(f"❌ Colonna 'Cod.Mecc.' non trovata. Colonne disponibili: {df.columns.tolist()}")
        st.stop()
    df["Cod.Mecc."] = df["Cod.Mecc."].astype(str).str.strip()
    return df

@st.cache_data
def carica_gare(uploaded_file):
    df = pd.read_csv(uploaded_file, header=None)
    colonne = [
        "NumGara", "CodGara", "Org", "Categoria", "Girone", "Turno", "Data", "Ora",
        "CodSoc1", "Squadra1", "CodSoc2", "Squadra2", "CodCampo", "Campo", "Località",
        "Cod.Mecc.", "Ruolo", "CodFisc", "Cognome", "Nome", "Sezione", "Designatore", "Altro"
    ]
    if len(df.columns) < len(colonne):
        st.error("❌ Il file gare non ha abbastanza colonne.")
        st.stop()
    df.columns = colonne + [f"Extra_{i}" for i in range(len(df.columns) - len(colonne))]
    df["Cod.Mecc."] = df["Cod.Mecc."].astype(str).str.strip()
    df["NumGara"] = df["NumGara"].astype(str).str.strip()
    df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
    return df

@st.cache_data
def carica_indisponibili(uploaded_file):
    df = pd.read_excel(uploaded_file)
    df.columns = [str(c).strip().lower() for c in df.columns]
    if "cod.mecc." not in df.columns or "inizio" not in df.columns or "fine" not in df.columns:
        st.error(f"❌ Colonne richieste non trovate. Trovate: {list(df.columns)}")
        st.stop()
    df["cod.mecc."] = df["cod.mecc."].astype(str).str.strip()
    df["inizio"] = pd.to_datetime(df["inizio"], errors="coerce")
    df["fine"] = pd.to_datetime(df["fine"], errors="coerce")
    expanded = []
    for _, row in df.iterrows():
        if pd.notnull(row["inizio"]) and pd.notnull(row["fine"]):
            for d in pd.date_range(row["inizio"], row["fine"], freq="D"):
                expanded.append({
                    "Cod.Mecc.": row["cod.mecc."],
                    "Data": d,
                    "Motivazione": row.get("motivazione", "")
                })
    return pd.DataFrame(expanded)

def estrai_voti_da_pdf(pdf_file):
    with pdfplumber.open(pdf_file) as pdf:
        text = ""
        for page in pdf.pages:
            text += page.extract_text() + "\n"

    righe = text.split("\n")
    records = []
    for riga in righe:
        if "NumGara" in riga or not riga.strip():
            continue
        parts = riga.strip().split()
        try:
            numgara = next((x for x in parts if x.isdigit() and len(x) >= 6), None)
            oa = float(next(x for x in parts if x.replace(",", ".").replace(".", "").isdigit()))
            ot = float(next(x for x in reversed(parts) if x.replace(",", ".").replace(".", "").isdigit()))
            records.append({
                "NumGara": str(numgara),
                "Voto OA": oa,
                "Voto OT": ot
            })
        except:
            continue
    return pd.DataFrame(records)

def settimana_da_data(data):
    inizio_settimana = data - timedelta(days=data.weekday())
    return inizio_settimana.strftime("%Y-%m-%d")

# --- App principale ---
st.title("Gestione Arbitri - CRA Test (01/05/2025 - 30/06/2025)")

# Upload settimanali
col1, col2, col3 = st.columns(3)
with col1:
    gare_file = st.file_uploader("📥 Carica file gare (cra01.csv)", type="csv")
with col2:
    voti_file = st.file_uploader("📥 Carica file voti (PDF)", type="pdf")
with col3:
    indisponibili_file = st.file_uploader("📥 Carica file indisponibilità (Excel)", type="xlsx")

# Caricamento dati
df_arbitri = carica_anagrafica()
df_gare = carica_gare(gare_file) if gare_file else pd.DataFrame()
df_voti_raw = estrai_voti_da_pdf(voti_file) if voti_file else pd.DataFrame()
df_indisp = carica_indisponibili(indisponibili_file) if indisponibili_file else pd.DataFrame()

# Collegamento voti con Cod.Mecc. tramite NumGara
if not df_voti_raw.empty and not df_gare.empty:
    if "NumGara" not in df_voti_raw.columns or "Cod.Mecc." not in df_gare.columns:
        st.error("❌ Colonna 'NumGara' o 'Cod.Mecc.' mancante.")
        st.stop()
    df_merge = pd.merge(df_voti_raw, df_gare[["NumGara", "Cod.Mecc."]], on="NumGara", how="left")
else:
    df_merge = pd.DataFrame()

# Calcolo settimane
settimane = pd.date_range(DATA_INIZIO, DATA_FINE, freq="W-MON")
sett_str = [d.strftime("%Y-%m-%d") for d in settimane]

# Layout arbitri
for _, arbitro in df_arbitri.iterrows():
    with st.expander(f"{arbitro['Cognome']} {arbitro['Nome']} - {arbitro['Cod.Mecc.']}"):
        col1, col2, col3 = st.columns(3)
        col1.markdown(f"**Sezione:** {arbitro.get('Sezione', '')}")
        col2.markdown(f"**Età:** {arbitro.get('Età', '')}")
        col3.markdown(f"**Anzianità:** {arbitro.get('Anzianità', '')}")

        tabella = []
        for s in settimane:
            data_str = s.strftime("%Y-%m-%d")
            inizio = s
            fine = s + timedelta(days=6)

            # Gare arbitro in settimana
            gare_settimana = df_gare[
                (df_gare["Cod.Mecc."] == arbitro["Cod.Mecc."]) &
                (df_gare["Data"] >= inizio) & (df_gare["Data"] <= fine)
            ]
            righe = []
            for _, g in gare_settimana.iterrows():
                voto_row = df_merge[df_merge["NumGara"] == str(g["NumGara"])]
                voto_oa = voto_row["Voto OA"].values[0] if not voto_row.empty else ""
                voto_ot = voto_row["Voto OT"].values[0] if not voto_row.empty else ""
                righe.append(f"Gara {g['NumGara']} - OA: {voto_oa} OT: {voto_ot}")

            # Indisponibilità
            indisp = df_indisp[
                (df_indisp["Cod.Mecc."] == arbitro["Cod.Mecc."]) &
                (df_indisp["Data"] >= inizio) & (df_indisp["Data"] <= fine)
            ]
            if not indisp.empty:
                righe.append("❌ Indisponibile")

            tabella.append(", ".join(righe) if righe else "-")

        df_sett = pd.DataFrame([tabella], columns=sett_str)
        st.dataframe(df_sett)
