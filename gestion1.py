import streamlit as st
import json
import os
from datetime import datetime

# ─── CONFIG ────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Groupe · Suivi Financier",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

DATA_FILE = "projets_data.json"

# ─── STYLE ─────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Fond général blanc */
.stApp {
    background: #f0f4fb;
    color: #1e293b;
}

/* Sidebar bleu */
[data-testid="stSidebar"] {
    background: #1d4ed8 !important;
    border-right: none;
}
[data-testid="stSidebar"] * { color: #ffffff !important; }
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] label { color: #e0eaff !important; }
[data-testid="stSidebar"] .stTextInput input,
[data-testid="stSidebar"] .stNumberInput input,
[data-testid="stSidebar"] .stTextArea textarea {
    background: #2563eb !important;
    border: 1px solid #3b82f6 !important;
    color: #ffffff !important;
    border-radius: 8px !important;
}
[data-testid="stSidebar"] .stTextInput input::placeholder,
[data-testid="stSidebar"] .stNumberInput input::placeholder {
    color: #bfdbfe !important;
}
[data-testid="stSidebar"] [data-baseweb="select"] > div {
    background: #2563eb !important;
    border-color: #3b82f6 !important;
    color: #ffffff !important;
}

/* Titres */
h1, h2, h3 { color: #1e3a8a !important; font-weight: 700; }

/* Cartes projet */
.projet-card {
    background: #ffffff;
    border: 1px solid #bfdbfe;
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 12px;
    box-shadow: 0 1px 4px rgba(30,58,138,0.07);
}

.projet-title {
    font-size: 1.2rem;
    font-weight: 700;
    color: #1e3a8a;
    margin-bottom: 4px;
}

.projet-budget {
    font-size: 0.85rem;
    color: #64748b;
    margin-bottom: 16px;
}

/* Barres de progression */
.progress-wrap {
    background: #dbeafe;
    border-radius: 99px;
    height: 12px;
    width: 100%;
    overflow: hidden;
    margin: 6px 0 2px 0;
}
.progress-bar {
    height: 100%;
    border-radius: 99px;
}
.bar-low  { background: #3b82f6; }
.bar-mid  { background: #f59e0b; }
.bar-high { background: #10b981; }
.bar-full { background: #1d4ed8; }

/* Badges */
.badge {
    display: inline-block;
    padding: 3px 12px;
    border-radius: 99px;
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}
.badge-active  { background: #dbeafe; color: #1d4ed8; }
.badge-complet { background: #d1fae5; color: #059669; }
.badge-archive { background: #fef3c7; color: #d97706; }

/* Metric cards */
.metric-box {
    background: #ffffff;
    border: 1px solid #bfdbfe;
    border-radius: 12px;
    padding: 20px;
    text-align: center;
    box-shadow: 0 1px 4px rgba(30,58,138,0.07);
}
.metric-val {
    font-size: 1.8rem;
    font-weight: 800;
    color: #1d4ed8;
}
.metric-label { font-size: 0.8rem; color: #64748b; margin-top: 4px; }

/* Boutons */
.stButton button {
    border-radius: 8px !important;
    font-weight: 500 !important;
}
.stButton button[kind="primary"] {
    background: #1d4ed8 !important;
    border: none !important;
    color: white !important;
}
.stButton button[kind="primary"]:hover {
    background: #1e40af !important;
}

/* Expander */
[data-testid="stExpander"] {
    background: #ffffff !important;
    border: 1px solid #bfdbfe !important;
    border-radius: 12px !important;
    box-shadow: 0 1px 4px rgba(30,58,138,0.06) !important;
}
[data-testid="stExpander"] summary { color: #1e3a8a !important; font-weight: 600; }

/* Tabs */
.stTabs [data-baseweb="tab-list"] { background: transparent !important; gap: 6px; }
.stTabs [data-baseweb="tab"] {
    background: #ffffff !important;
    border-radius: 8px !important;
    color: #64748b !important;
    border: 1px solid #bfdbfe !important;
}
.stTabs [aria-selected="true"] {
    background: #1d4ed8 !important;
    color: #ffffff !important;
    border-color: #1d4ed8 !important;
}

/* Inputs */
.stTextInput input, .stNumberInput input, .stTextArea textarea {
    background: #ffffff !important;
    border: 1px solid #93c5fd !important;
    color: #1e293b !important;
    border-radius: 8px !important;
}

/* Séparateur */
hr { border-color: #bfdbfe !important; }
</style>
""", unsafe_allow_html=True)

# ─── PERSISTANCE ───────────────────────────────────────────────────────────────
def charger_donnees():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"projets": [], "archives": []}

def sauvegarder_donnees(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ─── SESSION STATE ──────────────────────────────────────────────────────────────
if "data" not in st.session_state:
    st.session_state.data = charger_donnees()

def save():
    sauvegarder_donnees(st.session_state.data)

# ─── HELPERS ───────────────────────────────────────────────────────────────────
def pct_couleur(pct):
    if pct >= 100: return "bar-full"
    if pct >= 70:  return "bar-high"
    if pct >= 40:  return "bar-mid"
    return "bar-low"

def format_fcfa(val):
    try:
        return f"{float(val):,.0f} FCFA".replace(",", " ")
    except:
        return f"{val} FCFA"

def total_projet(projet):
    return sum(b["montant"] for b in projet.get("besoins", []))

def total_verse(projet):
    return sum(b["verse"] for b in projet.get("besoins", []))

def pct_global(projet):
    tot = total_projet(projet)
    return (total_verse(projet) / tot * 100) if tot > 0 else 0

# ─── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style='padding: 16px 0 24px 0;'>
        <div style='font-size:1.4rem;font-weight:800;color:#ffffff;'>
            💰 BESOINS
        </div>
        <div style='font-size:0.75rem;color:#bfdbfe;margin-top:2px;'>Suivi Financier des Projets</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### ➕ Nouveau Projet")
    with st.form("form_projet", clear_on_submit=True):
        nom_projet = st.text_input("Nom du projet", placeholder="Ex: Réhabilitation Route N1")
        budget_total = st.number_input("Budget total estimé (FCFA)", min_value=0.0, step=100000.0)
        desc_projet = st.text_area("Description (optionnel)", height=80)
        submit_projet = st.form_submit_button("Créer le projet", use_container_width=True, type="primary")

    if submit_projet:
        if nom_projet.strip():
            st.session_state.data["projets"].append({
                "id": datetime.now().isoformat(),
                "nom": nom_projet.strip(),
                "budget": budget_total,
                "description": desc_projet,
                "date_creation": datetime.now().strftime("%d/%m/%Y"),
                "besoins": []
            })
            save()
            st.success(f"✅ Projet « {nom_projet} » créé !")
            st.rerun()
        else:
            st.error("Le nom du projet est obligatoire.")

    st.markdown("---")

    # Sélection projet pour ajouter un besoin
    projets_actifs = st.session_state.data.get("projets", [])
    if projets_actifs:
        st.markdown("### 📌 Ajouter un Besoin")
        noms = [p["nom"] for p in projets_actifs]
        projet_sel = st.selectbox("Projet cible", noms)

        with st.form("form_besoin", clear_on_submit=True):
            nom_besoin = st.text_input("Intitulé du besoin", placeholder="Ex: Achat matériaux")
            montant_besoin = st.number_input("Montant total (FCFA)", min_value=0.0, step=10000.0)
            avance_besoin = st.number_input("Avance versée (FCFA)", min_value=0.0, step=10000.0)
            submit_besoin = st.form_submit_button("Ajouter le besoin", use_container_width=True, type="primary")

        if submit_besoin:
            if nom_besoin.strip() and montant_besoin > 0:
                for p in st.session_state.data["projets"]:
                    if p["nom"] == projet_sel:
                        avance_valide = min(avance_besoin, montant_besoin)
                        p["besoins"].append({
                            "id": datetime.now().isoformat(),
                            "nom": nom_besoin.strip(),
                            "montant": montant_besoin,
                            "verse": avance_valide,
                            "date": datetime.now().strftime("%d/%m/%Y"),
                            "archive": avance_valide >= montant_besoin
                        })
                        save()

                        # Auto-archivage projet si tous besoins complets
                        if all(b["archive"] for b in p["besoins"]) and len(p["besoins"]) > 0:
                            p["date_archive"] = datetime.now().strftime("%d/%m/%Y")
                            st.session_state.data["archives"].append(p)
                            st.session_state.data["projets"].remove(p)
                            save()
                            st.success(f"🎉 Projet « {p['nom']} » archivé (100% complété) !")
                        else:
                            st.success(f"✅ Besoin « {nom_besoin} » ajouté !")
                        st.rerun()
            else:
                st.error("Intitulé et montant obligatoires.")

# ─── MAIN ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div style='padding: 8px 0 32px 0;'>
    <h1 style='font-size:2rem;font-weight:800;color:#1e3a8a;margin:0;'>
        Tableau de Bord Financier
    </h1>
    <p style='color:#64748b;margin:4px 0 0 0;font-size:0.95rem;'>
        Suivi des besoins financiers par projet
    </p>
</div>
""", unsafe_allow_html=True)

# ─── MÉTRIQUES GLOBALES ────────────────────────────────────────────────────────
projets = st.session_state.data.get("projets", [])
archives = st.session_state.data.get("archives", [])
all_p = projets + archives

nb_projets        = len(projets)
nb_archives       = len(archives)
total_besoins_amt = sum(total_projet(p) for p in all_p)
total_finance     = sum(total_verse(p) for p in all_p)
total_reste       = total_besoins_amt - total_finance
pct_global_all    = (total_finance / total_besoins_amt * 100) if total_besoins_amt > 0 else 0

# Nombre de besoins actifs (non archivés) sur tous les projets actifs
nb_besoins_actifs = sum(
    len([b for b in p.get("besoins", []) if not b.get("archive")])
    for p in projets
)

c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    st.markdown(f"""
    <div class='metric-box'>
        <div class='metric-val'>{nb_projets}</div>
        <div class='metric-label'>Projets actifs</div>
    </div>""", unsafe_allow_html=True)
with c2:
    st.markdown(f"""
    <div class='metric-box'>
        <div class='metric-val' style='color:#f59e0b;'>{nb_besoins_actifs}</div>
        <div class='metric-label'>Besoins actifs total</div>
    </div>""", unsafe_allow_html=True)
with c3:
    st.markdown(f"""
    <div class='metric-box'>
        <div class='metric-val'>{nb_archives}</div>
        <div class='metric-label'>Projets archivés</div>
    </div>""", unsafe_allow_html=True)
with c4:
    st.markdown(f"""
    <div class='metric-box'>
        <div class='metric-val' style='font-size:1.1rem;color:#38ef7d;'>{format_fcfa(total_finance)}</div>
        <div class='metric-label'>Total financé</div>
    </div>""", unsafe_allow_html=True)
with c5:
    st.markdown(f"""
    <div class='metric-box'>
        <div class='metric-val' style='font-size:1.1rem;color:#f87171;'>{format_fcfa(total_reste)}</div>
        <div class='metric-label'>Reste à verser (global)</div>
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ─── ONGLETS ───────────────────────────────────────────────────────────────────
tab1, tab2 = st.tabs([f"📂 Projets Actifs ({nb_projets})", f"🗄️ Archives ({nb_archives})"])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — PROJETS ACTIFS
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    if not projets:
        st.markdown("""
        <div style='text-align:center;padding:60px 20px;color:#94a3b8;'>
            <div style='font-size:3rem;margin-bottom:12px;'>📭</div>
            <div style='font-size:1.1rem;font-weight:600;color:#1e3a8a;'>
                Aucun projet actif
            </div>
            <div style='font-size:0.85rem;margin-top:6px;'>
                Créez votre premier projet dans le panneau latéral
            </div>
        </div>""", unsafe_allow_html=True)
    else:
        for idx, projet in enumerate(projets):
            besoins = projet.get("besoins", [])
            pct = pct_global(projet)
            t_total = total_projet(projet)
            t_verse = total_verse(projet)
            couleur = pct_couleur(pct)

            nb_actifs_proj = len([b for b in besoins if not b.get("archive")])
            with st.expander(f"📁  {projet['nom']}  —  {pct:.0f}% financé  ·  {nb_actifs_proj} besoin(s) actif(s)", expanded=True):
                # En-tête projet
                col_info, col_badge, col_actions = st.columns([3, 1, 1])
                with col_info:
                    st.markdown(f"""
                    <div class='projet-title'>{projet['nom']}</div>
                    <div class='projet-budget'>
                        Créé le {projet.get('date_creation','—')}
                        {' · ' + projet['description'] if projet.get('description') else ''}
                        {' · Budget estimé : ' + format_fcfa(projet['budget']) if projet.get('budget',0) > 0 else ''}
                    </div>
                    """, unsafe_allow_html=True)
                with col_badge:
                    badge = "badge-complet" if pct >= 100 else "badge-active"
                    label = "Complet" if pct >= 100 else "Actif"
                    st.markdown(f"<span class='badge {badge}'>{label}</span>", unsafe_allow_html=True)
                with col_actions:
                    if st.button("🗑️ Supprimer", key=f"del_proj_{idx}", help="Supprimer ce projet"):
                        st.session_state.data["projets"].pop(idx)
                        save()
                        st.rerun()

                # Barre globale projet + reste à verser
                t_reste_proj = t_total - t_verse
                st.markdown(f"""
                <div style='margin-bottom:4px;display:flex;justify-content:space-between;'>
                    <span style='font-size:0.8rem;color:#64748b;'>Financement global</span>
                    <span style='font-size:0.8rem;font-weight:600;color:#1e293b;'>
                        {format_fcfa(t_verse)} / {format_fcfa(t_total)}
                    </span>
                </div>
                <div class='progress-wrap'>
                    <div class='progress-bar {couleur}' style='width:{min(pct,100):.1f}%;'></div>
                </div>
                <div style='display:flex;justify-content:space-between;font-size:0.75rem;margin-top:4px;margin-bottom:4px;'>
                    <span style='color:#dc2626;font-weight:600;'>
                        Reste à verser : {format_fcfa(t_reste_proj)}
                    </span>
                    <span style='color:#64748b;'>{pct:.1f}%</span>
                </div>
                <div style='display:flex;gap:12px;margin-bottom:16px;margin-top:6px;'>
                    <span style='font-size:0.78rem;background:#dbeafe;color:#1d4ed8;
                                 border-radius:6px;padding:3px 10px;font-weight:600;'>
                        🔵 {nb_actifs_proj} besoin(s) actif(s)
                    </span>
                    <span style='font-size:0.78rem;background:#d1fae5;color:#059669;
                                 border-radius:6px;padding:3px 10px;font-weight:600;'>
                        ✅ {len([b for b in besoins if b.get("archive")])} complété(s)
                    </span>
                </div>
                """, unsafe_allow_html=True)

                # ── Besoins ──
                besoins_actifs   = [b for b in besoins if not b.get("archive")]
                besoins_archives = [b for b in besoins if b.get("archive")]

                if not besoins:
                    st.markdown("<div style='color:#94a3b8;font-size:0.85rem;padding:8px 0;'>Aucun besoin enregistré pour ce projet.</div>", unsafe_allow_html=True)
                else:
                    if besoins_actifs:
                        st.markdown("<div style='font-size:0.75rem;text-transform:uppercase;letter-spacing:0.1em;color:#1d4ed8;font-weight:600;margin-bottom:8px;'>Besoins en cours</div>", unsafe_allow_html=True)
                        # En-tête colonnes
                        st.markdown("""
                        <div style='display:grid;grid-template-columns:2.5fr 3fr 1.4fr 1.4fr 0.6fr;
                                    gap:8px;padding:4px 0 8px 0;border-bottom:1px solid #bfdbfe;margin-bottom:4px;'>
                            <span style='font-size:0.7rem;text-transform:uppercase;letter-spacing:0.08em;color:#64748b;'>Intitulé</span>
                            <span style='font-size:0.7rem;text-transform:uppercase;letter-spacing:0.08em;color:#64748b;'>Progression</span>
                            <span style='font-size:0.7rem;text-transform:uppercase;letter-spacing:0.08em;color:#64748b;text-align:right;'>Montant</span>
                            <span style='font-size:0.7rem;text-transform:uppercase;letter-spacing:0.08em;color:#dc2626;text-align:right;'>Reste</span>
                            <span></span>
                        </div>""", unsafe_allow_html=True)

                        for bidx, besoin in enumerate(besoins_actifs):
                            b_pct  = (besoin["verse"] / besoin["montant"] * 100) if besoin["montant"] > 0 else 0
                            b_col  = pct_couleur(b_pct)
                            b_reste = besoin["montant"] - besoin["verse"]
                            col_n, col_bar, col_v, col_r, col_btn = st.columns([2.5, 3, 1.4, 1.4, 0.6])
                            with col_n:
                                st.markdown(f"<div style='font-size:0.9rem;color:#1e293b;padding-top:8px;'>{besoin['nom']}</div>", unsafe_allow_html=True)
                            with col_bar:
                                st.markdown(f"""
                                <div style='padding-top:10px;'>
                                <div class='progress-wrap'>
                                    <div class='progress-bar {b_col}' style='width:{min(b_pct,100):.1f}%;'></div>
                                </div>
                                <div style='display:flex;justify-content:space-between;font-size:0.7rem;color:#64748b;margin-top:2px;'>
                                    <span>Versé : {format_fcfa(besoin['verse'])}</span>
                                    <span>{b_pct:.0f}%</span>
                                </div>
                                </div>""", unsafe_allow_html=True)
                            with col_v:
                                st.markdown(f"<div style='font-size:0.8rem;color:#64748b;padding-top:8px;text-align:right;'>{format_fcfa(besoin['montant'])}</div>", unsafe_allow_html=True)
                            with col_r:
                                color_reste = "#dc2626" if b_reste > 0 else "#059669"
                                st.markdown(f"<div style='font-size:0.8rem;color:{color_reste};font-weight:600;padding-top:8px;text-align:right;'>{format_fcfa(b_reste)}</div>", unsafe_allow_html=True)
                            with col_btn:
                                real_idx = besoins.index(besoin)
                                if st.button("💸", key=f"pay_{idx}_{real_idx}", help="Ajouter un versement"):
                                    st.session_state[f"pay_mode_{idx}_{real_idx}"] = True

                            # Formulaire de versement inline
                            if st.session_state.get(f"pay_mode_{idx}_{real_idx}"):
                                with st.form(key=f"form_pay_{idx}_{real_idx}"):
                                    reste = besoin["montant"] - besoin["verse"]
                                    nouveau_v = st.number_input(
                                        f"Versement supplémentaire (reste : {format_fcfa(reste)})",
                                        min_value=0.0, max_value=float(reste), step=1000.0
                                    )
                                    c_ok, c_ann = st.columns(2)
                                    with c_ok:
                                        ok = st.form_submit_button("✅ Valider", use_container_width=True, type="primary")
                                    with c_ann:
                                        ann = st.form_submit_button("❌ Annuler", use_container_width=True)

                                    if ok and nouveau_v > 0:
                                        besoin["verse"] += nouveau_v
                                        if besoin["verse"] >= besoin["montant"]:
                                            besoin["archive"] = True
                                            besoin["verse"] = besoin["montant"]
                                        save()
                                        del st.session_state[f"pay_mode_{idx}_{real_idx}"]
                                        # Vérifier si projet entièrement financé
                                        if all(b["archive"] for b in projet["besoins"]):
                                            projet["date_archive"] = datetime.now().strftime("%d/%m/%Y")
                                            st.session_state.data["archives"].append(projet)
                                            st.session_state.data["projets"].pop(idx)
                                            save()
                                            st.success(f"🎉 Projet « {projet['nom']} » archivé !")
                                        st.rerun()
                                    if ann:
                                        del st.session_state[f"pay_mode_{idx}_{real_idx}"]
                                        st.rerun()

                    # Besoins archivés (dans le projet actif)
                    if besoins_archives:
                        st.markdown("<div style='font-size:0.75rem;text-transform:uppercase;letter-spacing:0.1em;color:#059669;font-weight:600;margin:16px 0 8px 0;'>✔ Besoins complétés</div>", unsafe_allow_html=True)
                        for besoin in besoins_archives:
                            st.markdown(f"""
                            <div style='display:flex;justify-content:space-between;align-items:center;
                                        padding:8px 12px;background:#f0fdf4;border:1px solid #bbf7d0;
                                        border-radius:8px;margin-bottom:4px;'>
                                <span style='font-size:0.85rem;color:#94a3b8;text-decoration:line-through;'>{besoin['nom']}</span>
                                <span style='font-size:0.8rem;color:#059669;font-weight:600;'>
                                    {format_fcfa(besoin['montant'])} ✓
                                </span>
                            </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — ARCHIVES (VERSION CORRIGÉE AVEC AFFICHAGE COMPLET)
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    if not archives:
        st.markdown("""
        <div style='text-align:center;padding:60px 20px;color:#94a3b8;'>
            <div style='font-size:3rem;margin-bottom:12px;'>🗄️</div>
            <div style='font-size:1.1rem;font-weight:600;color:#1e3a8a;'>
                Aucun projet archivé
            </div>
            <div style='font-size:0.85rem;margin-top:6px;'>
                Les projets entièrement financés apparaîtront ici
            </div>
        </div>""", unsafe_allow_html=True)
    else:
        for idx, projet in enumerate(archives):
            besoins = projet.get("besoins", [])
            t_total = total_projet(projet)
            t_verse = total_verse(projet)
            
            with st.expander(f"📦  {projet['nom']}  —  {len(besoins)} besoin(s) · {format_fcfa(t_total)}", expanded=False):
                # En-tête projet
                st.markdown(f"""
                <div class='projet-title'>{projet['nom']}</div>
                <div class='projet-budget'>
                    Archivé le {projet.get('date_archive', projet.get('date_creation', '—'))}
                    {' · ' + projet['description'] if projet.get('description') else ''}
                </div>
                <div class='progress-wrap'>
                    <div class='progress-bar bar-full' style='width:100%;'></div>
                </div>
                <div style='text-align:right;font-size:0.75rem;color:#059669;font-weight:600;margin-bottom:16px;'>
                    {format_fcfa(t_verse)} / {format_fcfa(t_total)} — 100% financé ✓
                </div>
                """, unsafe_allow_html=True)
                
                # Liste des besoins archivés
                if besoins:
                    st.markdown("<div style='font-size:0.75rem;text-transform:uppercase;letter-spacing:0.1em;color:#059669;font-weight:600;margin-bottom:8px;'>📋 Détail des besoins complétés</div>", unsafe_allow_html=True)
                    
                    for besoin in besoins:
                        st.markdown(f"""
                        <div style='display:flex;justify-content:space-between;align-items:center;
                                    padding:10px 12px;background:#f0fdf4;border:1px solid #bbf7d0;
                                    border-radius:8px;margin-bottom:6px;'>
                            <div>
                                <span style='font-size:0.9rem;color:#1e293b;font-weight:500;'>{besoin['nom']}</span>
                                <span style='font-size:0.7rem;color:#94a3b8;margin-left:12px;'>{besoin.get('date', '—')}</span>
                            </div>
                            <div>
                                <span style='font-size:0.85rem;color:#059669;font-weight:600;'>
                                    {format_fcfa(besoin['montant'])} ✓
                                </span>
                            </div>
                        </div>""", unsafe_allow_html=True)
                
                # Bouton restaurer
                col1, col2, col3 = st.columns([1,2,1])
                with col2:
                    if st.button("↩️ Restaurer ce projet", key=f"restore_{idx}", use_container_width=True):
                        # Retirer la date d'archive avant restauration
                        if "date_archive" in projet:
                            del projet["date_archive"]
                        st.session_state.data["projets"].append(projet)
                        st.session_state.data["archives"].pop(idx)
                        save()
                        st.success(f"✅ Projet « {projet['nom']} » restauré dans les projets actifs !")
                        st.rerun()
        
        # Bouton vider toutes les archives
        st.markdown("<br>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            if st.button("🗑️ Vider toutes les archives", type="secondary", use_container_width=True):
                st.session_state.data["archives"] = []
                save()
                st.rerun()
