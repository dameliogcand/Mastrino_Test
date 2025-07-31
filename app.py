import streamlit as st
import pandas as pd
import pdfplumber
import datetime

st.set_page_config(layout="wide")
st.title("📋 Gestione Arbitri – C.A.N. D")

DATA_INIZIO = datetime.date(2025, 5, 1)
DATA_FINE = datetime.date(2025, 6, 30)

@st.cache_data
def carica_anagrafica():
    df = pd.read_excel("Arbitri.xlsx", dtype=str)
    df.columns = df.iloc[0]
    df = df[1:]
    df["Cod.Mecc."] = df["Cod.Mecc."].astype(str).str.strip()
    return df

@st.cache_data
def carica_gare(uploaded_file):
    df = pd.read_csv(uploaded_file, header=None, dtype=str)
    df = df.iloc[:, :24]  # Prime 24 colonne utili
    df.columns = [
        "IDGara", "NumGara", "Categoria", "Giornata", "Turno", "TipoGara", "Data", "Ora",
        "ID_Squadra1", "Squadra1", "ID_Squadra2", "Squadra2", "IDCampo", "Campo", "Località",
        "Matricola", "Ruolo", "Cod.Mecc.", "Cognome", "Nome", "IDSezione", "Sezione", "Fascia", "Note"
    ]
    df["Cod.Mecc."] = df["Cod.Mecc."].astype(str).str.strip()
    df["Data"] = pd.to_datetime(df["Data"], format="%d/%m/%Y", errors="coerce")
    return df

@st.cache_data
def carica_voti(voti_pdf):
    with pdfplumber.open(voti_pdf) as pdf:
        text = "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())
    rows = []
    for line in text.split("\n"):
        parts = line.split()
        try:
            numgara = int(parts[0])
            ruolo = parts[8]
            voto_raw = parts[-1].replace(",", ".")
            voto = float(voto_raw)
            if ruolo in ["OA", "OT"]:
                rows.append({"NumGara": str(numgara), "Ruolo": ruolo, "Voto": voto})
        except:
            continue
    return pd.DataFrame(rows)

@st.cache_data
def carica_indisponibilita(file):
    df = pd.read_excel(file, dtype=str)
    df.columns = df.iloc[0]
    df = df[1:]
    df["Cod.Mecc."] = df["Cod.Mecc."].astype(str).str.strip()
    df["Data"] = pd.to_datetime(df["Data"], format="%d/%m/%Y", errors="coerce")
    return df

def settimana_riferimento(data):
    if pd.isna(data): return None
    lunedi = data - datetime.timedelta(days=data.weekday())
    return f"{lunedi.strftime('%d/%m')} - {(lunedi + datetime.timedelta(days=6)).strftime('%d/%m')}"

# === Caricamento file ===
st.sidebar.header("📤 Carica i file settimanali")
gare_file = st.sidebar.file_uploader("CRA01 (.csv)", type=["csv"])
voti_file = st.sidebar.file_uploader("Voti (.pdf)", type=["pdf"])
indisp_file = st.sidebar.file_uploader("Indisponibilità (.xlsx)", type=["xlsx"])

df_arbitri = carica_anagrafica()

if gare_file and voti_file:
    df_gare = carica_gare(gare_file)
    df_voti = carica_voti(voti_file)

    # Unione voti con gare
    df_voti = df_voti.merge(df_gare[["NumGara", "Cod.Mecc."]], on="NumGara", how="left")
    pivot_voti = df_voti.pivot_table(index="Cod.Mecc.", columns="Ruolo", values="Voto", aggfunc="mean").reset_index()
    pivot_voti.columns.name = None
    pivot_voti = pivot_voti.rename(columns={"OA": "Media OA", "OT": "Media OT"})

    # Gare con settimana
    df_gare["Settimana"] = df_gare["Data"].apply(settimana_riferimento)

    # Tabelle settimanali
    sett_gare = df_gare.groupby(["Cod.Mecc.", "Settimana"]).agg({
        "NumGara": lambda x: ", ".join(x),
        "Ruolo": lambda x: ", ".join(x)
    }).reset_index()

    # Merge anagrafica + voti + gare
    df_tot = df_arbitri.merge(sett_gare, on="Cod.Mecc.", how="left")
    df_tot = df_tot.merge(pivot_voti, on="Cod.Mecc.", how="left")

    # === Indisponibilità ===
    if indisp_file:
        df_indisp = carica_indisponibilita(indisp_file)
        df_indisp["Settimana"] = df_indisp["Data"].apply(settimana_riferimento)

        sett_indisp = df_indisp.groupby(["Cod.Mecc.", "Settimana"])["Motivo"].apply(lambda x: "⚠️ " + " | ".join(x)).reset_index()
        df_tot = df_tot.merge(sett_indisp, on=["Cod.Mecc.", "Settimana"], how="left")

    # === Visualizzazione ===
    st.success("✅ Dati caricati correttamente!")

    settimane_uniche = sorted(sett_gare["Settimana"].dropna().unique().tolist())

    colonne = ["Cod.Mecc.", "Nome", "Cognome", "Sezione", "Età"] + settimane_uniche
    visual = pd.DataFrame(columns=colonne)

    for idx, row in df_arbitri.iterrows():
        riga = {
            "Cod.Mecc.": row["Cod.Mecc."],
            "Nome": row["Nome"],
            "Cognome": row["Cognome"],
            "Sezione": row["Sezione"],
            "Età": row["Età"]
        }
        codmecc = row["Cod.Mecc."]
        for settimana in settimane_uniche:
            gare = sett_gare[(sett_gare["Cod.Mecc."] == codmecc) & (sett_gare["Settimana"] == settimana)]
            indisp = ""
            if indisp_file:
                ind = sett_indisp[(sett_indisp["Cod.Mecc."] == codmecc) & (sett_indisp["Settimana"] == settimana)]
                if not ind.empty:
                    indisp = ind["Motivo"].values[0]
            cella = ""
            if not gare.empty:
                cella = f"Gara: {gare['NumGara'].values[0]} ({gare['Ruolo'].values[0]})"
            if indisp:
                cella += f" {indisp}"
            riga[settimana] = cella
        visual = pd.concat([visual, pd.DataFrame([riga])], ignore_index=True)

    st.dataframe(visual, use_container_width=True)

    st.subheader("📊 Medie OA / OT")
    medie = df_arbitri[["Cod.Mecc."]].merge(pivot_voti, on="Cod.Mecc.", how="left")
    st.dataframe(medie, use_container_width=True)
else:
    st.warning("📥 Carica almeno il file CRA01 e il file Voti PDF.")
