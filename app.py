import streamlit as st
import pandas as pd
import datetime
from PyPDF2 import PdfReader
import io

st.set_page_config(layout="wide")

# Costanti
SETTIMANE = pd.date_range(start="2025-05-01", end="2025-06-30", freq='W-SUN')

# --- FUNZIONI ---

@st.cache_data
def carica_anagrafica():
    df = pd.read_excel("Arbitri.xlsx")
    df["Cod.Mecc."] = df["Cod.Mecc."].astype(str).str.strip()
    return df

@st.cache_data
@st.cache_data
def carica_gare(file):
    df = pd.read_csv(file, header=None, encoding="utf-8")
    df = df[[1, 2, 3, 6, 16, 17]]
    df.columns = ["NumGara", "Categoria", "Girone", "DataGara", "Ruolo", "Cod.Mecc."]
    df["Cod.Mecc."] = df["Cod.Mecc."].astype(str).str.strip()
    df["NumGara"] = df["NumGara"].astype(str).str.strip()
    df["DataGara"] = pd.to_datetime(df["DataGara"], errors="coerce")
    return df

@st.cache_data
def carica_voti(file):
    reader = PdfReader(file)
    text = ""
    for page in reader.pages:
        text += page.extract_text()

    righe = text.split("\n")
    dati = []
    for riga in righe:
        parti = riga.split()
        if len(parti) >= 5 and parti[0].isdigit():
            try:
                num_gara = parti[0]
                voto_oa = float(parti[-2].replace(",", "."))
                voto_ot = float(parti[-1].replace(",", "."))
                dati.append((num_gara, voto_oa, voto_ot))
            except:
                pass

    df = pd.DataFrame(dati, columns=["NumGara", "Voto OA", "Voto OT"])
    df["NumGara"] = df["NumGara"].astype(str).str.strip()
    return df

@st.cache_data
def carica_indisponibili(file):
    df = pd.read_excel(file)
    df["Cod.Mecc."] = df["Cod.Mecc."].astype(str).str.strip()
    df["Inizio"] = pd.to_datetime(df["Inizio"], errors="coerce")
    df["Fine"] = pd.to_datetime(df["Fine"], errors="coerce")
    return df


# --- CARICAMENTI FILE ---
st.title("Gestione Arbitri – Test 01/05/2025 - 30/06/2025")

st.sidebar.header("📂 Carica i file settimanali")
gare_file = st.sidebar.file_uploader("Carica file cra01 (.csv)", type=["csv"])
voti_file = st.sidebar.file_uploader("Carica PDF voti", type=["pdf"])
indisponibili_file = st.sidebar.file_uploader("Carica file indisponibilità (.xlsx)", type=["xlsx"])

df_arbitri = carica_anagrafica()
df_gare = carica_gare(gare_file) if gare_file else pd.DataFrame()
df_voti_raw = carica_voti(voti_file) if voti_file else pd.DataFrame()
df_indisp = carica_indisponibili(indisponibili_file) if indisponibili_file else pd.DataFrame()

# --- UNIONE GARE E VOTI ---
if not df_voti_raw.empty and not df_gare.empty:
    df_voti_raw["NumGara"] = df_voti_raw["NumGara"].astype(str).str.strip()
    df_gare["NumGara"] = df_gare["NumGara"].astype(str).str.strip()

    if "NumGara" in df_voti_raw.columns and "NumGara" in df_gare.columns and "Cod.Mecc." in df_gare.columns:
        df_merged = pd.merge(df_voti_raw, df_gare[["NumGara", "Cod.Mecc."]], on="NumGara", how="left")
        df_merged = df_merged.dropna(subset=["Cod.Mecc."])
        df_gare = pd.merge(df_gare, df_merged, on=["NumGara", "Cod.Mecc."], how="left")
    else:
        st.error("❌ Errore nel merge: colonne 'NumGara' o 'Cod.Mecc.' non trovate.")
        st.stop()

# --- VISUALIZZAZIONE ---
st.header("📋 Anagrafica Arbitri e Dati Settimanali")

for idx, arbitro in df_arbitri.iterrows():
    cod_mecc = arbitro["Cod.Mecc."]
    col1, col2, col3 = st.columns([3, 3, 3])
    col1.markdown(f"### {arbitro['Cognome']} {arbitro['Nome']}")
    col2.markdown(f"**Sezione:** {arbitro['Sezione']}")
    # col3.markdown(f"**Anzianità:** {arbitro['Anzianità']}")  # RIMOSSA su richiesta

    tabella_settimane = []

    for settimana in SETTIMANE:
        casella = ""
        gare_sett = df_gare[(df_gare["Cod.Mecc."] == cod_mecc) &
                            (df_gare["DataGara"].dt.isocalendar().week == settimana.isocalendar().week)]

        for _, gara in gare_sett.iterrows():
            categoria = gara["Categoria"]
            girone = str(gara["Girone"]).strip()
            ruolo = gara["Ruolo"]
            voto_oa = gara.get("Voto OA", "")
            voto_ot = gara.get("Voto OT", "")
            descr = f"{categoria} – {girone} – {ruolo}"
            if pd.notna(voto_oa) or pd.notna(voto_ot):
                descr += f"<br>OA: {voto_oa:.2f} OT: {voto_ot:.2f}"
            casella += descr + "<br><hr>"

        # INDISPONIBILITÀ
        if not df_indisp.empty:
            indisp_sett = df_indisp[df_indisp["Cod.Mecc."] == cod_mecc]
            for _, row in indisp_sett.iterrows():
                start, end, motivo = row["Inizio"], row["Fine"], row["Motivo"]

                # Debug temporaneo
                st.write(f"[DEBUG] {cod_mecc} – Inizio: {start}, Fine: {end}, Motivo: {motivo}, Settimana: {settimana}")

                if settimana.date() >= start.date() and settimana.date() <= end.date():
                    casella += f"<br><span style='color:red; font-size:smaller;'>INDISP: {motivo}</span>"

        tabella_settimane.append(casella if casella else "-")

    df_visual = pd.DataFrame([tabella_settimane], columns=[d.strftime("%d/%m") for d in SETTIMANE])
    st.dataframe(df_visual.style.set_properties(**{"text-align": "left"}), use_container_width=True)
    st.markdown("---")
