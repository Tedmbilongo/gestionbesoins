"""
Application Streamlit - Suivi budgétaire des comptes de charges (6) et produits (7)
=====================================================================================
Fonctionnalités :
1. Upload du tableau N (FEC / journal comptable)
2. Tri chronologique des écritures
3. Filtre sur les comptes de classe 6 (charges) et 7 (produits)
4. Détection automatique du département à partir du libellé (texte entre la dernière
   parenthèse ouvrante et le tiret qui suit) + saisie manuelle pour les cas non reconnus
5. Cumul par compte du 01/01 à la date choisie par l'utilisateur
6. Saisie manuelle des budgets par compte + calcul du % de budget consommé
7. Upload du tableau N-1 pour comparaison (volume et % vs année précédente)
8. Répartition de tout le travail ci-dessus par département

Format de fichier attendu (séparateur ; , décimales avec virgule) :
Date;Libelle;Compte;Libelle du compte;Debit;Credit
"""

import io
import re
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Suivi Budgétaire - Comptes 6 & 7", layout="wide")

# --------------------------------------------------------------------------------------
# Constantes
# --------------------------------------------------------------------------------------

REQUIRED_COLUMNS = ["Date", "Libelle", "Compte", "Libelle du compte", "Debit", "Credit"]

DEPARTEMENTS = [
    "Produit",
    "Comptabilite & Finances",
    "Marketing & Communication",
    "Operations",
    "Relation clients",
    "IT",
    "Ressources Humaines",
    "Administratif & Juridique",
    "Partenariat",
]

NON_RECONNU = "-- Non reconnu --"

# --------------------------------------------------------------------------------------
# Fonctions utilitaires
# --------------------------------------------------------------------------------------


def parse_montant(serie: pd.Series) -> pd.Series:
    """Convertit une colonne de montants au format français ('1 234,56') en float."""
    return (
        serie.astype(str)
        .str.replace(" ", "", regex=False)
        .str.replace("\u00a0", "", regex=False)  # espace insécable
        .str.replace(",", ".", regex=False)
        .replace("", "0")
        .astype(float)
    )


def extraire_departement_brut(libelle: str):
    """Extrait le texte situé entre la DERNIERE parenthèse ouvrante et le tiret suivant."""
    s = str(libelle)
    idx = s.rfind("(")
    if idx == -1:
        return None
    reste = s[idx + 1:]
    tiret = reste.find("-")
    brut = reste[:tiret] if tiret != -1 else reste.rstrip(")")
    brut = brut.strip()
    return brut if brut else None


def matcher_departement(brut):
    """Fait correspondre le texte brut extrait à un département connu."""
    if brut is None or (isinstance(brut, float) and pd.isna(brut)):
        return None
    r = re.sub(r"[^a-z& ]", "", str(brut).lower()).strip()
    if not r:
        return None
    # 1) correspondance en début de chaîne (ex: "Produit carriere" -> "Produit")
    for d in DEPARTEMENTS:
        if r.startswith(d.lower()):
            return d
    # 2) correspondance par mot entier, tolérant le pluriel (ex: "Partenariats" -> "Partenariat")
    for d in DEPARTEMENTS:
        base = d.lower().rstrip("s")
        if re.search(r"\b" + re.escape(base) + r"s?\b", r):
            return d
    return None


@st.cache_data(show_spinner=False)
def load_fec(file_bytes: bytes) -> pd.DataFrame:
    """Charge un fichier journal (CSV), le nettoie et le trie chronologiquement."""
    df = pd.read_csv(io.BytesIO(file_bytes), sep=";", encoding="utf-8", dtype=str)
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Colonnes manquantes dans le fichier : {missing}")

    df["Debit"] = parse_montant(df["Debit"])
    df["Credit"] = parse_montant(df["Credit"])
    df["Date"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")
    df["Compte"] = df["Compte"].astype(str).str.strip()
    df = df.dropna(subset=["Date"])

    # 1) Tri chronologique du plus ancien au plus récent
    df = df.sort_values("Date").reset_index(drop=True)
    return df


def filtre_comptes_6_7(df: pd.DataFrame) -> pd.DataFrame:
    """Ne garde que les comptes de classe 6 (charges) et 7 (produits)."""
    out = df[df["Compte"].str[0].isin(["6", "7"])].copy()
    out["Nature"] = out["Compte"].str[0].map({"6": "Charge", "7": "Produit"})
    out["Solde_Ligne"] = out.apply(
        lambda r: r["Debit"] - r["Credit"] if r["Compte"][0] == "6" else r["Credit"] - r["Debit"],
        axis=1,
    )
    out["Departement_detecte"] = out["Libelle"].apply(lambda x: matcher_departement(extraire_departement_brut(x)))
    out = out.reset_index(drop=True)
    out["id_ligne"] = out.index
    return out


def appliquer_overrides(df: pd.DataFrame, overrides: dict) -> pd.DataFrame:
    """Applique les départements saisis manuellement par-dessus la détection automatique."""
    df = df.copy()
    df["Departement"] = df.apply(
        lambda r: overrides.get(r["id_ligne"], r["Departement_detecte"]), axis=1
    )
    return df


def cumul_par_compte(df: pd.DataFrame, date_fin: pd.Timestamp) -> pd.DataFrame:
    """Cumule Débit/Crédit/Solde par compte du 01/01 de l'année de date_fin jusqu'à date_fin incluse."""
    date_debut = pd.Timestamp(year=date_fin.year, month=1, day=1)
    periode = df[(df["Date"] >= date_debut) & (df["Date"] <= date_fin)]

    grp = (
        periode.groupby(["Compte", "Libelle du compte", "Nature"], as_index=False)
        .agg(Cumul_Debit=("Debit", "sum"), Cumul_Credit=("Credit", "sum"), Solde_Cumule=("Solde_Ligne", "sum"))
    )
    return grp.sort_values("Compte").reset_index(drop=True)


def cumul_par_departement(df: pd.DataFrame, date_fin: pd.Timestamp) -> pd.DataFrame:
    """Cumule les soldes par département (mini P&L : charges, produits, net) sur la période."""
    date_debut = pd.Timestamp(year=date_fin.year, month=1, day=1)
    periode = df[(df["Date"] >= date_debut) & (df["Date"] <= date_fin)].copy()
    periode["Departement"] = periode["Departement"].fillna("Non affecté")

    pivot = (
        periode.pivot_table(index="Departement", columns="Nature", values="Solde_Ligne", aggfunc="sum", fill_value=0.0)
        .reset_index()
    )
    for col in ["Charge", "Produit"]:
        if col not in pivot.columns:
            pivot[col] = 0.0
    pivot = pivot.rename(columns={"Charge": "Cumul_Charges", "Produit": "Cumul_Produits"})
    pivot["Solde_Net"] = pivot["Cumul_Produits"] - pivot["Cumul_Charges"]
    return pivot.sort_values("Departement").reset_index(drop=True)


def to_excel_bytes(dfs: dict) -> bytes:
    """Exporte plusieurs DataFrames vers un fichier Excel (un onglet par clé)."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for sheet_name, d in dfs.items():
            d.to_excel(writer, sheet_name=sheet_name[:31], index=False)
    return output.getvalue()


# --------------------------------------------------------------------------------------
# Sidebar
# --------------------------------------------------------------------------------------

st.sidebar.header("1. Import des données")

fichier_n = st.sidebar.file_uploader("Tableau N (année en cours)", type=["csv"], key="upload_n")
fichier_n1 = st.sidebar.file_uploader("Tableau N-1 (année précédente) — optionnel", type=["csv"], key="upload_n1")

st.sidebar.markdown("---")
st.sidebar.header("2. Date d'arrêté")

# --------------------------------------------------------------------------------------
# Corps de l'application
# --------------------------------------------------------------------------------------

st.title("📊 Suivi budgétaire — Comptes de charges (6) et produits (7)")

if fichier_n is None:
    st.info("👈 Commencez par importer le tableau N (fichier journal .csv) dans la barre latérale.")
    st.stop()

try:
    df_n_full = load_fec(fichier_n.getvalue())
except ValueError as e:
    st.error(str(e))
    st.stop()

df_n_67 = filtre_comptes_6_7(df_n_full)

if df_n_67.empty:
    st.warning("Aucun compte de classe 6 ou 7 trouvé dans le fichier importé.")
    st.stop()

date_min = df_n_67["Date"].min().date()
date_max = df_n_67["Date"].max().date()

date_choisie = st.sidebar.date_input(
    "Date de calcul du cumul", value=date_max, min_value=date_min, max_value=date_max
)
date_choisie_ts = pd.Timestamp(date_choisie)

st.caption(
    f"Cumul calculé du **01/01/{date_choisie_ts.year}** au **{date_choisie_ts.strftime('%d/%m/%Y')}** "
    f"— {len(df_n_67)} écritures sur comptes 6/7 (fichier trié chronologiquement)."
)

with st.expander("Voir les écritures brutes triées et filtrées (comptes 6 & 7)"):
    st.dataframe(df_n_67.drop(columns=["id_ligne"]), use_container_width=True)

# --------------------------------------------------------------------------------------
# 2bis. Détection / saisie manuelle du département
# --------------------------------------------------------------------------------------

st.markdown("---")
st.header("🏷️ Département par transaction")

if "dept_overrides" not in st.session_state:
    st.session_state["dept_overrides"] = {}

df_n_67 = appliquer_overrides(df_n_67, st.session_state["dept_overrides"])

nb_non_reconnu = df_n_67["Departement"].isna().sum()
nb_total = len(df_n_67)
st.caption(
    f"{nb_total - nb_non_reconnu} / {nb_total} transactions ont un département détecté automatiquement "
    f"à partir du libellé (texte entre la dernière parenthèse et le tiret)."
)

if nb_non_reconnu > 0:
    st.warning(
        f"⚠️ {nb_non_reconnu} transaction(s) sans département reconnu. "
        f"Sélectionnez un département pour chacune ci-dessous :"
    )
    a_completer = df_n_67[df_n_67["Departement"].isna()][
        ["id_ligne", "Date", "Libelle", "Compte", "Libelle du compte", "Debit", "Credit"]
    ].copy()
    a_completer["Departement"] = None

    edite = st.data_editor(
        a_completer,
        column_config={
            "id_ligne": None,  # colonne cachée, sert de clé stable
            "Date": st.column_config.DateColumn(disabled=True, format="DD/MM/YYYY"),
            "Libelle": st.column_config.TextColumn(disabled=True, width="large"),
            "Compte": st.column_config.TextColumn(disabled=True),
            "Libelle du compte": st.column_config.TextColumn(disabled=True),
            "Debit": st.column_config.NumberColumn(disabled=True, format="%.2f"),
            "Credit": st.column_config.NumberColumn(disabled=True, format="%.2f"),
            "Departement": st.column_config.SelectboxColumn(options=DEPARTEMENTS, required=False),
        },
        hide_index=True,
        use_container_width=True,
        key="dept_editor",
    )

    nouveau = False
    for _, r in edite.iterrows():
        if pd.notna(r["Departement"]) and st.session_state["dept_overrides"].get(r["id_ligne"]) != r["Departement"]:
            st.session_state["dept_overrides"][r["id_ligne"]] = r["Departement"]
            nouveau = True
    if nouveau:
        df_n_67 = appliquer_overrides(df_n_67, st.session_state["dept_overrides"])
        st.rerun()
else:
    st.success("✅ Tous les départements ont été reconnus automatiquement.")

cumul_n = cumul_par_compte(df_n_67, date_choisie_ts)
cumul_dept_n = cumul_par_departement(df_n_67, date_choisie_ts)

# --------------------------------------------------------------------------------------
# 3. Budgets par compte (saisie manuelle uniquement)
# --------------------------------------------------------------------------------------

st.markdown("---")
st.header("💰 Budgets par compte (saisie manuelle)")

if "budgets_df" not in st.session_state or set(st.session_state["budgets_df"]["Compte"]) != set(cumul_n["Compte"]):
    base_budget = cumul_n[["Compte", "Libelle du compte"]].copy()
    if "budgets_df" in st.session_state:
        anciens = st.session_state["budgets_df"].set_index("Compte")["Budget"].to_dict()
        base_budget["Budget"] = base_budget["Compte"].map(anciens).fillna(0.0)
    else:
        base_budget["Budget"] = 0.0
    st.session_state["budgets_df"] = base_budget

st.write("Saisissez le budget annuel de chaque compte :")
edited_budgets = st.data_editor(
    st.session_state["budgets_df"],
    column_config={
        "Compte": st.column_config.TextColumn(disabled=True),
        "Libelle du compte": st.column_config.TextColumn(disabled=True),
        "Budget": st.column_config.NumberColumn(format="%.2f"),
    },
    hide_index=True,
    use_container_width=True,
    key="budget_editor",
)
st.session_state["budgets_df"] = edited_budgets

# --------------------------------------------------------------------------------------
# 4. Consolidé N par compte + % budget consommé
# --------------------------------------------------------------------------------------

consolide = cumul_n.merge(edited_budgets[["Compte", "Budget"]], on="Compte", how="left")
consolide["Budget"] = consolide["Budget"].fillna(0.0)
consolide["% Budget consommé"] = consolide.apply(
    lambda r: (abs(r["Solde_Cumule"]) / r["Budget"] * 100) if r["Budget"] not in (0, 0.0) else None, axis=1
)

# --------------------------------------------------------------------------------------
# 4bis. Budgets par département (saisie manuelle uniquement)
# --------------------------------------------------------------------------------------

st.markdown("---")
st.header("💰 Budgets par département (saisie manuelle)")

if (
    "budgets_dept_df" not in st.session_state
    or set(st.session_state["budgets_dept_df"]["Departement"]) != set(cumul_dept_n["Departement"])
):
    base_budget_dept = cumul_dept_n[["Departement"]].copy()
    if "budgets_dept_df" in st.session_state:
        anciens_d = st.session_state["budgets_dept_df"].set_index("Departement")["Budget"].to_dict()
        base_budget_dept["Budget"] = base_budget_dept["Departement"].map(anciens_d).fillna(0.0)
    else:
        base_budget_dept["Budget"] = 0.0
    st.session_state["budgets_dept_df"] = base_budget_dept

st.write("Saisissez le budget annuel de chaque département :")
edited_budgets_dept = st.data_editor(
    st.session_state["budgets_dept_df"],
    column_config={
        "Departement": st.column_config.TextColumn(disabled=True),
        "Budget": st.column_config.NumberColumn(format="%.2f"),
    },
    hide_index=True,
    use_container_width=True,
    key="budget_dept_editor",
)
st.session_state["budgets_dept_df"] = edited_budgets_dept

# --------------------------------------------------------------------------------------
# 5. Comparaison N-1 (optionnelle) — par compte et par département
# --------------------------------------------------------------------------------------

cumul_dept_n1 = None
if fichier_n1 is not None:
    try:
        df_n1_full = load_fec(fichier_n1.getvalue())
        df_n1_67 = filtre_comptes_6_7(df_n1_full)
        df_n1_67["Departement"] = df_n1_67["Departement_detecte"]  # pas de saisie manuelle sur N-1

        date_n1 = pd.Timestamp(year=date_choisie_ts.year - 1, month=date_choisie_ts.month, day=date_choisie_ts.day)
        date_n1 = min(date_n1, df_n1_67["Date"].max()) if not df_n1_67.empty else date_n1

        cumul_n1 = cumul_par_compte(df_n1_67, date_n1)
        cumul_n1_renamed = cumul_n1[["Compte", "Solde_Cumule"]].rename(columns={"Solde_Cumule": "Solde_Cumule_N-1"})
        consolide = consolide.merge(cumul_n1_renamed, on="Compte", how="left")
        consolide["Solde_Cumule_N-1"] = consolide["Solde_Cumule_N-1"].fillna(0.0)
        consolide["Volume vs N-1"] = consolide["Solde_Cumule"] - consolide["Solde_Cumule_N-1"]
        consolide["% vs N-1"] = consolide.apply(
            lambda r: (r["Volume vs N-1"] / abs(r["Solde_Cumule_N-1"]) * 100) if r["Solde_Cumule_N-1"] not in (0, 0.0) else None,
            axis=1,
        )

        cumul_dept_n1 = cumul_par_departement(df_n1_67, date_n1)

        st.caption(
            f"Comparaison N-1 calculée du 01/01/{date_n1.year} au {date_n1.strftime('%d/%m/%Y')} "
            f"(même jour/mois, année précédente)."
        )
    except ValueError as e:
        st.error(f"Erreur sur le fichier N-1 : {e}")

# --------------------------------------------------------------------------------------
# 6. Affichage - Consolidé par compte
# --------------------------------------------------------------------------------------

st.markdown("---")
st.header("📋 Consolidé par compte")

format_dict = {
    "Cumul_Debit": "{:,.2f}",
    "Cumul_Credit": "{:,.2f}",
    "Solde_Cumule": "{:,.2f}",
    "Budget": "{:,.2f}",
    "% Budget consommé": "{:,.1f}%",
}
if "Solde_Cumule_N-1" in consolide.columns:
    format_dict.update(
        {"Solde_Cumule_N-1": "{:,.2f}", "Volume vs N-1": "{:,.2f}", "% vs N-1": "{:,.1f}%"}
    )

st.dataframe(consolide.style.format(format_dict, na_rep="-"), use_container_width=True)

st.subheader("Totaux généraux")
c1, c2, c3 = st.columns(3)
total_charges = consolide.loc[consolide["Nature"] == "Charge", "Solde_Cumule"].sum()
total_produits = consolide.loc[consolide["Nature"] == "Produit", "Solde_Cumule"].sum()
c1.metric("Total Charges cumulées", f"{total_charges:,.2f}")
c2.metric("Total Produits cumulés", f"{total_produits:,.2f}")
c3.metric("Résultat net (Produits - Charges)", f"{total_produits - total_charges:,.2f}")

# --------------------------------------------------------------------------------------
# 7. Affichage - Répartition par département
# --------------------------------------------------------------------------------------

st.markdown("---")
st.header("🏢 Répartition par département")

dept_format = {"Cumul_Charges": "{:,.2f}", "Cumul_Produits": "{:,.2f}", "Solde_Net": "{:,.2f}"}

if cumul_dept_n1 is not None:
    dept_consolide = cumul_dept_n.merge(
        cumul_dept_n1[["Departement", "Solde_Net"]].rename(columns={"Solde_Net": "Solde_Net_N-1"}),
        on="Departement",
        how="left",
    )
    dept_consolide["Solde_Net_N-1"] = dept_consolide["Solde_Net_N-1"].fillna(0.0)
    dept_consolide["Volume vs N-1"] = dept_consolide["Solde_Net"] - dept_consolide["Solde_Net_N-1"]
    dept_consolide["% vs N-1"] = dept_consolide.apply(
        lambda r: (r["Volume vs N-1"] / abs(r["Solde_Net_N-1"]) * 100) if r["Solde_Net_N-1"] not in (0, 0.0) else None,
        axis=1,
    )
    dept_format.update({"Solde_Net_N-1": "{:,.2f}", "Volume vs N-1": "{:,.2f}", "% vs N-1": "{:,.1f}%"})
else:
    dept_consolide = cumul_dept_n

dept_consolide = dept_consolide.merge(edited_budgets_dept, on="Departement", how="left")
dept_consolide["Budget"] = dept_consolide["Budget"].fillna(0.0)
dept_consolide["% Budget consommé"] = dept_consolide.apply(
    lambda r: (abs(r["Solde_Net"]) / r["Budget"] * 100) if r["Budget"] not in (0, 0.0) else None, axis=1
)
dept_format.update({"Budget": "{:,.2f}", "% Budget consommé": "{:,.1f}%"})

st.dataframe(dept_consolide.style.format(dept_format, na_rep="-"), use_container_width=True)

# --------------------------------------------------------------------------------------
# 8. Export
# --------------------------------------------------------------------------------------

st.markdown("---")
excel_bytes = to_excel_bytes(
    {
        "Consolide_par_compte": consolide,
        "Repartition_departement": dept_consolide,
        "Budgets_par_compte": edited_budgets,
        "Budgets_par_departement": edited_budgets_dept,
    }
)
st.download_button(
    "⬇️ Télécharger le consolidé complet (Excel)",
    data=excel_bytes,
    file_name=f"consolide_{date_choisie_ts.strftime('%Y-%m-%d')}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)
