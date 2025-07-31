import streamlit as st
import pandas as pd
import datetime
from PyPDF2 import PdfReader

# Impostazioni generali
st.set_page_config(layout="wide")
st.title("Gestione Arbitri – Stagione 2025")

# Periodo test
inizio_periodo = datetime.date(2025, 5, 1)
fine_periodo = datetime.date(2025, 6, 30)

# Calcolo delle settimane calcistiche
def get_settimane(inizio, fine):
    settimane = []
    data = inizio
    while data <= fine:
        lunedi = data - datetime.timedelta(days=data.weekday())
        domenica = lunedi + datetime.timedelta(days=6)
        settimane.append((lunedi, domenica))
        data = domenica + datetime.timedelta(days=1)
    return settimane

settimane = get_settimane(inizio_periodo, fine_periodo)

# Caricamento anagrafica arbitri (fissa)
@st.cache_data
def carica_anagrafica():
    df = pd.read_excel("Arbitri.xlsx")
    df.columns = df.columns.str.strip()
    df["Cod.Mecc."] = df["Cod.Mecc."].astype(str).str.strip()
    return df

# Caricamento gare da file CSV senza intestazioni (cra01)
@st.cache_data
def carica_gare(file):
    df = pd.read_csv(file, header=None)
    df = df[[1, 2, 3, 6, 16, 17]]  # NumGara, Categoria, Girone, DataGara, Ruolo, Cod.Mecc.
    df.columns = ["NumGara", "Categoria", "Girone", "DataGara", "Ruolo", "Cod.Mecc."]
    df["Cod.Mecc."] = df["Cod.Mecc."].astype(str).str.strip()
    df["NumGara"] = df["NumGara"].astype(str).str.strip()
    df["DataGara"] = pd.to_datetime(df["DataGara"], errors="coerce", dayfirst=True)
    return df

# Estrazione voti da PDF
@st.cache_data
def estrai_voti(pdf_file):
    reader = PdfReader(pdf_file)
    testo = ""
    for page in reader.pages:
        testo += page.extract_text()

    righe = testo.split("\n")
    dati = []
    for riga in righe:
        parti = riga.strip().split()
        if len(parti) >= 5 and parti[0].isdigit():
            num_gara = parti[0]
            try:
                voto_oa = float(parti[-2].replace(",", "."))
                voto_ot = float(parti[-1].replace(",", "."))
                dati.append({"NumGara": num_gara, "Voto OA": voto_oa, "Voto OT": voto_ot})
            except:
                continue
    return pd.DataFrame(dati)

# Caricamento indisponibilità (con colonne Inizio, Fine, Motivo, Cod.Mecc.)
@st.cache_data
def carica_indisponibili(file):
    df = pd.read_excel(file)
    df.columns = df.columns.str.strip()
    df["Cod.Mecc."] = df["Cod.Mecc."].astype(str).str.strip()
    df["Inizio"] = pd.to_datetime(df["Inizio"], errors="coerce")
    df["Fine"] = pd.to_datetime(df["Fine"], errors="coerce")
    df["Motivo"] = df["Motivo"].astype(str)
    return df

# Upload dei file settimanali
st.sidebar.header("Carica file settimanali")
gare_file = st.sidebar.file_uploader("File Gare cra01.csv", type="csv")
voti_file = st.sidebar.file_uploader("File Voti (PDF)", type="pdf")
indisponibili_file = st.sidebar.file_uploader("File Indisponibili", type=["xls", "xlsx"])

# Caricamento dei dati
df_arbitri = carica_anagrafica()
df_gare = carica_gare(gare_file) if gare_file else pd.DataFrame()
df_voti_raw = estrai_voti(voti_file) if voti_file else pd.DataFrame()
df_indisp = carica_indisponibili(indisponibili_file) if indisponibili_file else pd.DataFrame()

# Merge voti <-> gare su NumGara, per assegnare i voti agli arbitri
if not df_voti_raw.empty and not df_gare.empty:
    if "NumGara" in df_gare.columns and "NumGara" in df_voti_raw.columns:
        df_gare = df_gare.copy()
        df_voti_raw = df_voti_raw.copy()
        df_gare["NumGara"] = df_gare["NumGara"].astype(str).str.strip()
        df_voti_raw["NumGara"] = df_voti_raw["NumGara"].astype(str).str.strip()
        df_gare = pd.merge(df_gare, df_voti_raw, on="NumGara", how="left")
    else:
        st.error("❌ Errore: colonne 'NumGara' mancanti nei file.")
        st.stop()

# Filtro per settimana
sett_index = st.sidebar.selectbox("Seleziona settimana", list(range(len(settimane))))
sett_start, sett_end = settimane[sett_index]
st.subheader(f"Gare e Voti dal {sett_start.strftime('%d/%m/%Y')} al {sett_end.strftime('%d/%m/%Y')}")

# Visualizzazione
for idx, arbitro in df_arbitri.iterrows():
    cod_mecc = str(arbitro["Cod.Mecc."]).strip()

    # Riga arbitro
    with st.expander(f"👤 {arbitro['Cognome']} {arbitro['Nome']} ({cod_mecc})", expanded=False):
        col1, col2 = st.columns(2)
        col1.markdown(f"**Sezione:** {arbitro['Sezione']}")
        col2.markdown(f"**Età:** {arbitro['Età']}")

        # Gare in settimana
        gare_sett = df_gare[(df_gare["Cod.Mecc."] == cod_mecc) &
                            (df_gare["DataGara"] >= sett_start) &
                            (df_gare["DataGara"] <= sett_end)]

        if not gare_sett.empty:
            for _, gara in gare_sett.iterrows():
                cat = gara["Categoria"]
                gir = str(gara["Girone"])
                ruolo = gara["Ruolo"]
                voto_oa = gara.get("Voto OA", "")
                voto_ot = gara.get("Voto OT", "")
                voto_str = f"OA: {voto_oa:.2f}" if pd.notna(voto_oa) else ""
                voto_str += f" OT: {voto_ot:.2f}" if pd.notna(voto_ot) else ""
                st.markdown(f"- **{cat} – {gir} – {ruolo}** {voto_str}")
        else:
            st.markdown("✅ Nessuna gara in questa settimana.")

        # Indisponibilità
        if not df_indisp.empty:
            indisp_arbitro = df_indisp[df_indisp["Cod.Mecc."] == cod_mecc]
            for _, row in indisp_arbitro.iterrows():
                start, end, motivo = row["Inizio"], row["Fine"], row["Motivo"]
                if start <= sett_end and end >= sett_start:
                    st.error(f"🛑 Indisponibile ({motivo}) dal {start.strftime('%d/%m')} al {end.strftime('%d/%m')}")

