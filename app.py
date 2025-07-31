import streamlit as st
import pandas as pd
import datetime
import pdfplumber

st.set_page_config(layout="wide")
st.title("🧾 Gestione Arbitri – C.A.N. D")

# -------------------------------
# FUNZIONI DI CARICAMENTO DATI
# -------------------------------

@st.cache_data
def carica_anagrafica():
    df = pd.read_excel("Arbitri.xlsx", dtype=str)
    df.columns = df.columns.str.strip()
    df["Cod.Mecc."] = df["Cod.Mecc."].str.strip()
    return df

@st.cache_data
def carica_gare(uploaded_file):
    df = pd.read_csv(uploaded_file, header=None, dtype=str)
    df = df.iloc[:, :24]
    df.columns = [
        "IDGara", "NumGara", "Categoria", "Giornata", "Turno", "TipoGara", "Data", "Ora",
        "ID_Squadra1", "Squadra1", "ID_Squadra2", "Squadra2", "IDCampo", "Campo", "Località",
        "Matricola", "Ruolo", "Cod.Mecc.", "Cognome", "Nome", "IDSezione", "Sezione", "Fascia", "Note"
    ]
    df["Cod.Mecc."] = df["Cod.Mecc."].str.strip()
    df["NumGara"] = df["NumGara"].str.strip()
    return df

@st.cache_data
def carica_indisponibili(uploaded_file):
    df = pd.read_excel(uploaded_file, dtype=str)
    df.columns = df.columns.str.strip()
    df["Cod.Mecc."] = df["Cod.Mecc."].str.strip()
    return df

@st.cache_data
def estrai_voti_da_pdf(uploaded_pdf):
    voti = []
    with pdfplumber.open(uploaded_pdf) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            for line in text.split('\n'):
                parts = line.split()
                if len(parts) >= 5 and parts[0].isdigit():
                    numgara = parts[0]
                    voto_oa = parts[-2].replace(",", ".")
                    voto_ot = parts[-1].replace(",", ".")
                    voti.append({"NumGara": numgara, "Voto OA": voto_oa, "Voto OT": voto_ot})
    return pd.DataFrame(voti)

# -------------------------------
# CARICAMENTO BASE
# -------------------------------

df_arbitri = carica_anagrafica()

# -------------------------------
# UPLOAD FILE SETTIMANALI
# -------------------------------

col1, col2, col3 = st.columns(3)

with col1:
    gare_file = st.file_uploader("📂 Carica file CRA01 (CSV)", type=["csv"])

with col2:
    voti_pdf = st.file_uploader("📂 Carica file voti OA/OT (PDF)", type=["pdf"])

with col3:
    indisponibili_file = st.file_uploader("📂 Carica file indisponibilità (Excel)", type=["xlsx"])

# -------------------------------
# PROCESSAMENTO FILE CARICATI
# -------------------------------

if gare_file and voti_pdf:
    df_gare = carica_gare(gare_file)
    df_voti = estrai_voti_da_pdf(voti_pdf)

    # 🔗 Match NumGara con Cod.Mecc.
    df_voti = df_voti.merge(df_gare[["NumGara", "Cod.Mecc."]], on="NumGara", how="left")
    df_voti["Cod.Mecc."] = df_voti["Cod.Mecc."].str.strip()

    # 🧩 Merge con anagrafica
    df_finale = df_arbitri.merge(df_voti, on="Cod.Mecc.", how="left")

    # 📆 Calcolo settimana
    df_gare["Data"] = pd.to_datetime(df_gare["Data"], dayfirst=True)
    df_gare["Settimana"] = df_gare["Data"].dt.strftime("%Y-%W")
    df_voti = df_voti.merge(df_gare[["NumGara", "Settimana"]], on="NumGara", how="left")

    # 👀 Visualizzazione arbitri
    for _, arbitro in df_arbitri.iterrows():
        st.markdown("---")
        st.subheader(f"{arbitro['Cognome']} {arbitro['Nome']} ({arbitro['Cod.Mecc.']})")
        st.markdown(f"**Sezione**: {arbitro['Sezione']} &nbsp;&nbsp; | &nbsp;&nbsp; **Età**: {arbitro['Età']} &nbsp;&nbsp; | &nbsp;&nbsp; **Anzianità**: {arbitro['Data']}")

        # 📊 Voti per arbitro
        voti_arbitro = df_voti[df_voti["Cod.Mecc."] == arbitro["Cod.Mecc."]]
        settimane = sorted(voti_arbitro["Settimana"].dropna().unique())

        for settimana in settimane:
            voti_sett = voti_arbitro[voti_arbitro["Settimana"] == settimana]
            for _, row in voti_sett.iterrows():
                st.markdown(f"- **Settimana {settimana}**: Gara {row['NumGara']} — OA: {row['Voto OA']}, OT: {row['Voto OT']}")

        # 🚫 Indisponibilità
        if indisponibili_file:
            df_indisp = carica_indisponibili(indisponibili_file)
            indisp_arbitro = df_indisp[df_indisp["Cod.Mecc."] == arbitro["Cod.Mecc."]]
            for _, r in indisp_arbitro.iterrows():
                st.markdown(f"🟥 **Indisponibile**: {r['Data']} — {r['Motivazione']}")

else:
    st.warning("⚠️ Caricare sia il file CRA01 che il PDF dei voti per visualizzare i dati.")
