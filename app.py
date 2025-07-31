import streamlit as st
import pandas as pd
import datetime
import pdfplumber

st.set_page_config(layout="wide")
st.title("Gestione Arbitri – Stagione 2025")

# 📌 DATE DI TEST
DATA_INIZIO = datetime.date(2025, 5, 1)
DATA_FINE = datetime.date(2025, 6, 30)

@st.cache_data
def carica_anagrafica():
    df = pd.read_excel("Arbitri.xlsx")
    df.columns = df.columns.str.strip()
    df["Cod.Mecc."] = df["Cod.Mecc."].astype(str).str.strip()
    return df

@st.cache_data
def carica_gare(file):
    df = pd.read_csv(file, dtype=str)
    df.columns = df.columns.str.strip()
    df.rename(columns=lambda x: x.strip(), inplace=True)
    df["Cod.Mecc."] = df["Cod.Mecc."].astype(str).str.strip()
    df["NumGara"] = df["NumGara"].astype(str).str.strip()
    df["Data Gara"] = pd.to_datetime(df["Data Gara"], errors='coerce')
    return df

@st.cache_data
def carica_voti(file_pdf):
    with pdfplumber.open(file_pdf) as pdf:
        text = "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())
    righe = text.split("\n")
    dati = []
    for riga in righe:
        parti = riga.strip().split()
        if len(parti) >= 6 and parti[0].isdigit():
            try:
                num_gara = str(parti[0])
                voto_oa = float(parti[-2].replace(",", "."))
                voto_ot = float(parti[-1].replace(",", "."))
                dati.append({"NumGara": num_gara, "Voto OA": voto_oa, "Voto OT": voto_ot})
            except:
                continue
    return pd.DataFrame(dati)

@st.cache_data
def carica_indisponibili(file):
    df = pd.read_excel(file)
    df.columns = df.columns.str.strip()
    df["Cod.Mecc."] = df["Cod.Mecc."].astype(str).str.strip()
    df["Inizio"] = pd.to_datetime(df["Inizio"], errors='coerce')
    df["Fine"] = pd.to_datetime(df["Fine"], errors='coerce')
    return df

def costruisci_settimanale(df_gare, df_voti):
    if not {'NumGara', 'Cod.Mecc.'}.issubset(df_gare.columns):
        st.error("❌ Il file delle gare non contiene le colonne necessarie ('NumGara', 'Cod.Mecc.').")
        st.stop()

    df = df_gare.copy()
    df = df.merge(df_voti, on="NumGara", how="left")
    df["Data Gara"] = pd.to_datetime(df["Data Gara"], errors='coerce')
    df["Settimana"] = df["Data Gara"].dt.to_period("W").apply(lambda r: r.start_time.date())
    return df

# 📥 Upload
st.sidebar.header("Carica i file settimanali")
gare_file = st.sidebar.file_uploader("File CRA01 (.csv)", type="csv")
voti_file = st.sidebar.file_uploader("PDF Voti OA/OT", type="pdf")
indisponibili_file = st.sidebar.file_uploader("Indisponibilità (.xlsx)", type=["xls", "xlsx"])

# 📊 Caricamento dati
df_arbitri = carica_anagrafica()
df_gare = carica_gare(gare_file) if gare_file else pd.DataFrame()
df_voti_raw = carica_voti(voti_file) if voti_file else pd.DataFrame()
df_indisp = carica_indisponibili(indisponibili_file) if indisponibili_file else pd.DataFrame()

df_settimanale = pd.DataFrame()
if not df_voti_raw.empty and not df_gare.empty:
    df_settimanale = costruisci_settimanale(df_gare, df_voti_raw)

# 📅 Genera elenco settimane
sett_inizio = DATA_INIZIO - datetime.timedelta(days=DATA_INIZIO.weekday())
sett_fine = DATA_FINE
settimane = []
while sett_inizio <= sett_fine:
    settimane.append(sett_inizio)
    sett_inizio += datetime.timedelta(days=7)

# 🔍 Filtro opzionale
st.sidebar.header("Filtri")
filtro_girone = st.sidebar.selectbox("Filtra per girone", options=["Tutti"] + sorted(df_gare["Girone"].dropna().unique()) if not df_gare.empty else ["Tutti"])
filtro_settimana = st.sidebar.selectbox("Filtra per settimana", options=["Tutte"] + [str(s) for s in settimane])

# 📋 Visualizzazione
st.subheader("Visualizzazione Arbitri")

for _, arbitro in df_arbitri.iterrows():
    cod_mecc = str(arbitro["Cod.Mecc."]).strip()
    nome = arbitro["Nome"]
    cognome = arbitro["Cognome"]

    if filtro_girone != "Tutti":
        gare_arbitro = df_settimanale[(df_settimanale["Cod.Mecc."] == cod_mecc) & (df_settimanale["Girone"] == filtro_girone)]
        if gare_arbitro.empty:
            continue

    with st.expander(f"{cognome} {nome} ({cod_mecc})"):
        col1, col2, col3 = st.columns(3)
        col1.markdown(f"**Sezione:** {arbitro.get('Sezione','')}")
        col2.markdown(f"**Età:** {arbitro.get('Età','')}")
        col3.markdown(f"**Anzianità:** {arbitro.get('Anzianità','')}")

        cols = st.columns(len(settimane))
        for idx, settimana in enumerate(settimane):
            if filtro_settimana != "Tutte" and str(settimana) != filtro_settimana:
                continue

            with cols[idx]:
                gare_settimana = df_settimanale[
                    (df_settimanale["Cod.Mecc."] == cod_mecc) &
                    (df_settimanale["Settimana"] == settimana)
                ]

                indisp = df_indisp[
                    (df_indisp["Cod.Mecc."] == cod_mecc) &
                    (df_indisp["Inizio"] <= settimana) &
                    (df_indisp["Fine"] >= settimana)
                ]

                if not gare_settimana.empty:
                    for _, gara in gare_settimana.iterrows():
                        cat = gara.get("Categoria", "")
                        gir = gara.get("Girone", "")
                        ruolo = gara.get("Ruolo", "")
                        voto_oa = gara.get("Voto OA", "")
                        voto_ot = gara.get("Voto OT", "")
                        riga = f"**{cat} – {gir} – {ruolo}**"
                        if pd.notna(voto_oa) or pd.notna(voto_ot):
                            riga += f"<br/>OA: {voto_oa if pd.notna(voto_oa) else '-'} | OT: {voto_ot if pd.notna(voto_ot) else '-'}"
                        st.markdown(riga, unsafe_allow_html=True)
                elif not indisp.empty:
                    motivazioni = ", ".join(indisp["Motivazione"].dropna().unique())
                    st.markdown(f"<span style='color:red;font-weight:bold'>❌ {motivazioni}</span>", unsafe_allow_html=True)
                else:
                    st.write("-")

# 📈 Medie voti
if not df_settimanale.empty:
    st.subheader("📊 Media Voti OA/OT")
    medie = df_settimanale.groupby("Cod.Mecc.")[
        ["Voto OA", "Voto OT"]
    ].mean().reset_index()
    df_media = df_arbitri.merge(medie, on="Cod.Mecc.", how="left")
    st.dataframe(df_media[["Cognome", "Nome", "Voto OA", "Voto OT"]].sort_values("Cognome"))
