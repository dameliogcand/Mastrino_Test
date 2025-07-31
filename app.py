import streamlit as st
import pandas as pd
import datetime
from PyPDF2 import PdfReader

st.set_page_config(layout="wide")

# Funzione per settare le settimane del periodo di test
def genera_settimane(start_date, end_date):
    settimane = []
    current = start_date
    while current <= end_date:
        fine = current + datetime.timedelta(days=6)
        settimane.append((current, fine))
        current = fine + datetime.timedelta(days=1)
    return settimane

# Carica l'anagrafica fissa
@st.cache_data
def carica_anagrafica():
    df = pd.read_excel("Arbitri.xlsx")
    df["Cod.Mecc."] = df["Cod.Mecc."].astype(str).str.strip()
    return df

# Carica le gare da file Excel senza intestazione
@st.cache_data
def carica_gare(file):
    df = pd.read_excel(file, header=None)
    df_gare = pd.DataFrame({
        "NumGara": df.iloc[:, 1].astype(str).str.strip(),
        "Categoria": df.iloc[:, 2],
        "Girone": df.iloc[:, 3],
        "DataGara": pd.to_datetime(df.iloc[:, 6], errors='coerce'),
        "Ruolo": df.iloc[:, 16],
        "Cod.Mecc.": df.iloc[:, 17].astype(str).str.strip()
    })
    return df_gare

# Estrai i voti OA e OT da PDF
@st.cache_data
def estrai_voti_da_pdf(file):
    reader = PdfReader(file)
    voti = []
    for page in reader.pages:
        text = page.extract_text()
        lines = text.split("\n")
        for line in lines:
            parts = line.split()
            if len(parts) >= 7:
                try:
                    num_gara = parts[0]
                    voto_oa = float(parts[-2].replace(",", "."))
                    voto_ot = float(parts[-1].replace(",", "."))
                    voti.append({
                        "NumGara": num_gara,
                        "Voto OA": voto_oa,
                        "Voto OT": voto_ot
                    })
                except:
                    continue
    return pd.DataFrame(voti)

# Carica indisponibilità da Excel (con colonne Inizio, Fine, Cod.Mecc., Motivo)
@st.cache_data
def carica_indisponibili(file):
    df = pd.read_excel(file)
    df["Cod.Mecc."] = df["Cod.Mecc."].astype(str).str.strip()
    df["Inizio"] = pd.to_datetime(df["Inizio"], errors='coerce')
    df["Fine"] = pd.to_datetime(df["Fine"], errors='coerce')
    df["Motivo"] = df["Motivo"].fillna("")
    return df

# Interfaccia Streamlit
st.title("Gestione Arbitri - Periodo di Test")

# Caricamento file dinamici
gare_file = st.file_uploader("📄 Carica file CRA01 settimanale (.xlsx)", type=["xlsx"])
pdf_file = st.file_uploader("📄 Carica file voti in PDF", type=["pdf"])
indisponibili_file = st.file_uploader("📄 Carica file indisponibilità (.xlsx)", type=["xlsx"])

# Settimane del periodo di test
settimane = genera_settimane(datetime.date(2025, 5, 1), datetime.date(2025, 6, 30))

# Caricamento dati
df_arbitri = carica_anagrafica()
df_gare = carica_gare(gare_file) if gare_file else pd.DataFrame()
df_voti_raw = estrai_voti_da_pdf(pdf_file) if pdf_file else pd.DataFrame()
df_indisp = carica_indisponibili(indisponibili_file) if indisponibili_file else pd.DataFrame()

# Unione voti e gare
if not df_voti_raw.empty and not df_gare.empty:
    if "NumGara" in df_voti_raw.columns and "NumGara" in df_gare.columns:
        df_merged = pd.merge(df_gare, df_voti_raw, on="NumGara", how="left")
    else:
        st.error("❌ Colonne 'NumGara' mancanti nei file. Controlla i dati.")
        st.stop()
else:
    df_merged = df_gare.copy()

# Filtro opzionale
settimana_sel = st.selectbox("📅 Seleziona settimana", settimane, format_func=lambda x: f"{x[0]} - {x[1]}")
giorno_start, giorno_end = settimana_sel

col1, col2 = st.columns([1, 5])

with col1:
    gironi_presenti = df_merged["Girone"].dropna().unique().tolist()
    filtro_girone = st.selectbox("🔤 Filtra per girone", ["Tutti"] + sorted(gironi_presenti))

# Visualizzazione per arbitro
for _, arbitro in df_arbitri.iterrows():
    cod_mecc = str(arbitro["Cod.Mecc."]).strip()

    # Gare settimanali arbitro
    gare_sett = df_merged[
        (df_merged["Cod.Mecc."] == cod_mecc) &
        (df_merged["DataGara"] >= pd.to_datetime(giorno_start)) &
        (df_merged["DataGara"] <= pd.to_datetime(giorno_end))
    ]

    if filtro_girone != "Tutti":
        gare_sett = gare_sett[gare_sett["Girone"] == filtro_girone]

    # Indisponibilità per settimana
    indisps = df_indisp[
        (df_indisp["Cod.Mecc."] == cod_mecc) &
        (df_indisp["Inizio"] <= pd.to_datetime(giorno_end)) &
        (df_indisp["Fine"] >= pd.to_datetime(giorno_start))
    ]

    if gare_sett.empty and indisps.empty:
        continue

    with st.expander(f"👤 {arbitro['Cognome']} {arbitro['Nome']}"):
        col1, col2 = st.columns(2)
        col1.markdown(f"**Sezione:** {arbitro['Sezione']}")
        col2.markdown(f"**Età:** {arbitro['Età']}")

        if not gare_sett.empty:
            for _, gara in gare_sett.iterrows():
                descrizione = f"{gara['Categoria']} – {gara['Girone']} – {gara['Ruolo']}"
                if "Voto OA" in gara and pd.notnull(gara["Voto OA"]):
                    descrizione += f" – OA: {gara['Voto OA']:.2f}"
                if "Voto OT" in gara and pd.notnull(gara["Voto OT"]):
                    descrizione += f" OT: {gara['Voto OT']:.2f}"
                st.markdown(f"✅ {descrizione}")
        else:
            st.info("Nessuna gara assegnata questa settimana.")

        if not indisps.empty:
            for _, ind in indisps.iterrows():
                st.error(f"🚫 Indisponibile ({ind['Motivo']})")
