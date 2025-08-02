import streamlit as st
import pandas as pd
import datetime

st.set_page_config(layout="wide")

# Funzione per rinominare le colonne in base al tipo di file
def rinomina_colonne(df, tipo):
    if tipo == "arbitri":
        if len(df.columns) < 6:
            st.error("❌ Il file arbitri ha meno colonne del previsto.")
            st.stop()
        df.columns = ["Cod.Mecc.", "Cognome", "Nome", "Sezione", "Anzianità", "Età"]
    elif tipo == "gare":
        if len(df.columns) < 19:
            st.error("❌ Il file CRA01 ha meno colonne del previsto.")
            st.stop()
        df.columns.values[1] = "NumGara"
        df.columns.values[2] = "Categoria"
        df.columns.values[3] = "Girone"
        df.columns.values[6] = "DataGara"
        df.columns.values[16] = "Ruolo"
        df.columns.values[17] = "Cod.Mecc."
        df.columns.values[18] = "Cognome"
    elif tipo == "voti":
        if len(df.columns) < 10:
            st.error("❌ Il file voti ha meno colonne del previsto.")
            st.stop()
        df.columns.values[0] = "NumGara"
        df.columns.values[8] = "Voto OA"
        df.columns.values[9] = "Voto OT"
    elif tipo == "indisponibili":
        if len(df.columns) < 11:
            st.error("❌ Il file indisponibili ha meno colonne del previsto.")
            st.stop()
        df.columns.values[1] = "Cod.Mecc."
        df.columns.values[8] = "Inizio"
        df.columns.values[9] = "Fine"
        df.columns.values[10] = "Motivo"
    return df

# Funzioni di caricamento file
@st.cache_data
def carica_anagrafica(file):
    df = pd.read_excel(file)
    df = rinomina_colonne(df, "arbitri")
    df["Cod.Mecc."] = df["Cod.Mecc."].astype(str).str[-7:].str.strip()
    return df

@st.cache_data
def carica_gare(file):
    df = pd.read_excel(file, header=0)
    df = rinomina_colonne(df, "gare")
    df["Cod.Mecc."] = df["Cod.Mecc."].astype(str).str[-7:].str.strip()
    df["NumGara"] = df["NumGara"].astype(str).str.replace('.0', '', regex=False).str.strip()
    df["DataGara"] = pd.to_datetime(df["DataGara"], errors="coerce")
    return df

@st.cache_data
def carica_voti(file):
    df = pd.read_excel(file)
    df = rinomina_colonne(df, "voti")
    df["NumGara"] = df["NumGara"].astype(str).str.replace('.0', '', regex=False).str.strip()
    return df

@st.cache_data
def carica_indisponibili(file):
    df = pd.read_excel(file)
    df = rinomina_colonne(df, "indisponibili")
    df["Cod.Mecc."] = df["Cod.Mecc."].astype(str).str[-7:].str.strip()
    df["Inizio"] = pd.to_datetime(df["Inizio"], errors="coerce")
    df["Fine"] = pd.to_datetime(df["Fine"], errors="coerce")
    return df

# Interfaccia utente
st.title("📋 Monitoraggio Gare e Voti Arbitri")

arbitri_file = st.file_uploader("Carica il file Arbitri.xlsx", type="xlsx")
gare_file = st.file_uploader("Carica il file CRA01.xlsx", type="xlsx")
voti_file = st.file_uploader("Carica il file Voti.xlsx", type="xlsx")
indisponibili_file = st.file_uploader("Carica il file Indisponibili.xlsx", type="xlsx")

if arbitri_file:
    df_arbitri = carica_anagrafica(arbitri_file)
    df_gare = carica_gare(gare_file) if gare_file else pd.DataFrame()
    df_voti = carica_voti(voti_file) if voti_file else pd.DataFrame()
    df_indisp = carica_indisponibili(indisponibili_file) if indisponibili_file else pd.DataFrame()

    if not df_voti.empty and not df_gare.empty:
        if "NumGara" not in df_voti.columns or "NumGara" not in df_gare.columns:
            st.error("❌ Colonna 'NumGara' mancante per il merge.")
            st.stop()
        df_merged = pd.merge(df_gare, df_voti, on="NumGara", how="left")
    else:
        df_merged = df_gare.copy()

    # Intervallo test: maggio 2024
    start_date = datetime.datetime(2024, 5, 1)
    end_date = datetime.datetime(2024, 5, 31)
    week_range = pd.date_range(start=start_date, end=end_date, freq="W-SUN")

    for _, arbitro in df_arbitri.iterrows():
        st.markdown("---")
        st.subheader(f"{arbitro['Cognome']} {arbitro['Nome']}")
        col1, col2, col3 = st.columns(3)
        col1.markdown(f"**Cod.Mecc.:** {arbitro['Cod.Mecc.']}")
        col2.markdown(f"**Sezione:** {arbitro['Sezione']}")
        col3.markdown(f"**Età:** {arbitro['Età']}")

        for i in range(len(week_range) - 1):
            week_start = week_range[i]
            week_end = week_range[i + 1]

            settimana = f"**Settimana {week_start.strftime('%d/%m')} – {week_end.strftime('%d/%m')}:**"
            with st.container():
                st.markdown(settimana)

                # Gare
                gare_sett = df_merged[
                    (df_merged["Cod.Mecc."].astype(str).str[-7:] == str(arbitro["Cod.Mecc."])) &
                    (df_merged["Cognome"].str.upper().str.strip() == str(arbitro["Cognome"]).upper().strip()) &
                    (df_merged["DataGara"] >= week_start) & (df_merged["DataGara"] <= week_end)
                ]

                if not gare_sett.empty:
                    for _, gara in gare_sett.iterrows():
                        ruolo = gara["Ruolo"]
                        categoria = gara["Categoria"]
                        girone = str(gara["Girone"]).strip()[-1]
                        voto_oa = gara.get("Voto OA", "")
                        voto_ot = gara.get("Voto OT", "")
                        voti_str = f"OA: {voto_oa}" if pd.notnull(voto_oa) else ""
                        voti_str += f" OT: {voto_ot}" if pd.notnull(voto_ot) else ""
                        st.markdown(f"- {categoria} – {girone} – {ruolo} {voti_str}")
                else:
                    st.markdown("_Nessuna gara assegnata._")

                # Indisponibilità
                if not df_indisp.empty:
                    indisp = df_indisp[
                        (df_indisp["Cod.Mecc."] == arbitro["Cod.Mecc."]) &
                        (df_indisp["Inizio"] <= week_end) & (df_indisp["Fine"] >= week_start)
                    ]
                    for _, row in indisp.iterrows():
                        st.warning(f"Indisponibile: {row['Motivo']} ({row['Inizio'].date()} – {row['Fine'].date()})")
