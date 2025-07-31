import streamlit as st
import pandas as pd
import datetime
from PyPDF2 import PdfReader

st.set_page_config(layout="wide")
st.title("📋 Gestione Arbitri – Stagione 2025")

# 📌 FUNZIONE: Caricamento anagrafica arbitri
@st.cache_data
def carica_anagrafica():
    df = pd.read_excel("Arbitri.xlsx")
    df["Cod.Mecc."] = df["Cod.Mecc."].astype(str).str.strip()
    return df

# 📌 FUNZIONE: Caricamento gare da CRA01
@st.cache_data
def carica_gare(file):
    df = pd.read_csv(file, header=None)
    df.columns = [f"Col{i}" for i in range(24)]
    df.rename(columns={
        2: "NumGara",
        3: "Categoria",
        4: "Girone",
        7: "DataGara",
        17: "Ruolo",
        18: "Cod.Mecc."
    }, inplace=True)
    df["Cod.Mecc."] = df["Cod.Mecc."].astype(str).str.strip()
    return df[["NumGara", "Categoria", "Girone", "DataGara", "Ruolo", "Cod.Mecc."]]

# 📌 FUNZIONE: Estrai voti da PDF
def estrai_voti_da_pdf(pdf_file):
    reader = PdfReader(pdf_file)
    text = "\n".join(page.extract_text() for page in reader.pages)
    righe = text.split("\n")

    records = []
    for riga in righe:
        if "OA:" in riga or "OT:" in riga:
            try:
                parti = riga.split()
                num_gara = next(p for p in parti if p.isdigit())
                oa = ot = None
                for i, p in enumerate(parti):
                    if p == "OA:":
                        oa = float(parti[i+1].replace(",", "."))
                    if p == "OT:":
                        ot = float(parti[i+1].replace(",", "."))
                records.append({"NumGara": int(num_gara), "OA": oa, "OT": ot})
            except:
                continue

    return pd.DataFrame(records)

# 📌 FUNZIONE: Calcolo settimana calcistica
def calcola_settimana(data):
    inizio_stagione = datetime.date(2025, 5, 1)
    fine_stagione = datetime.date(2025, 6, 30)
    if not (inizio_stagione <= data.date() <= fine_stagione):
        return None
    return (data.date() - inizio_stagione).days // 7 + 1

# 📌 Upload dei file
gare_file = st.file_uploader("📂 Carica file CRA01 (.csv)", type=["csv"])
voti_file = st.file_uploader("📂 Carica file PDF voti", type=["pdf"])

# 📌 Carica dati
df_arbitri = carica_anagrafica()
df_gare = carica_gare(gare_file) if gare_file else pd.DataFrame()
df_voti_raw = estrai_voti_da_pdf(voti_file) if voti_file else pd.DataFrame()

# 📌 Merge gare con voti
if not df_voti_raw.empty and not df_gare.empty:
    if "NumGara" not in df_gare.columns or "Cod.Mecc." not in df_gare.columns:
        st.error("❌ Colonne 'NumGara' o 'Cod.Mecc.' mancanti nel file CRA01.")
        st.stop()

    df_voti = df_voti_raw.merge(df_gare[["NumGara", "Cod.Mecc."]], on="NumGara", how="left")
else:
    df_voti = pd.DataFrame()

# 📌 Visualizzazione per arbitro
for _, arbitro in df_arbitri.iterrows():
    cod_mecc = str(arbitro["Cod.Mecc."]).strip()
    st.markdown(f"### {arbitro['Cognome']} {arbitro['Nome']}")
    st.markdown(f"Sezione: {arbitro['Sezione']} | Età: {arbitro['Età']} | Anzianità: {arbitro['Data']}")

    settimanali = {}
    if not df_gare.empty:
        gare_arbitro = df_gare[df_gare["Cod.Mecc."] == cod_mecc]
        for _, gara in gare_arbitro.iterrows():
            data = pd.to_datetime(gara["DataGara"], errors="coerce")
            settimana = calcola_settimana(data)
            if settimana:
                key = f"Settimana {settimana}"
                descrizione = f"{gara['Categoria']} – {gara['Girone']} – {gara['Ruolo']}"
                voto = ""
                if not df_voti.empty:
                    voto_row = df_voti[(df_voti["Cod.Mecc."] == cod_mecc) & (df_voti["NumGara"] == gara["NumGara"])]
                    if not voto_row.empty:
                        oa = voto_row["OA"].values[0]
                        ot = voto_row["OT"].values[0]
                        voto = f" OA: {oa:.2f}" if pd.notna(oa) else ""
                        voto += f" OT: {ot:.2f}" if pd.notna(ot) else ""
                settimanali.setdefault(key, []).append(descrizione + voto)

    if settimanali:
        for sett, eventi in settimanali.items():
            st.markdown(f"**{sett}**")
            for e in eventi:
                st.markdown(f"- {e}")
    st.markdown("---")
