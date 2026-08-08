# -*- coding: utf-8 -*-
"""Mode Conseiller — FCO Studio.

Destiné aux conseillers Cerfrance qui accompagnent les éleveurs. Orienté MÉTIER
(centralisation, suivi, synthèse), pas diagnostic vétérinaire.

Sections :
  A. Tableau de bord   -> statistiques RÉELLES depuis la base (jamais inventées).
  B. Dossiers / Suivi  -> dossiers gérés dans une base dédiée `conseiller.db`
                          (migration additive : ne touche pas à `fco.db`).
  C. Assistant         -> chatbot métier (module assistant.py).
  D. Synthèse          -> compte rendu exportable (TXT / Markdown).

Réutilise le système de design global (classes CSS .hero/.kpi/.card déjà
injectées par l'application principale).
"""
from __future__ import annotations

import datetime as _dt
import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

import assistant

BASE = Path(__file__).resolve().parent
FCO_DB = BASE.parent / "bdd" / "fco.db"
CONSEIL_DB = BASE.parent / "bdd" / "conseiller.db"

STATUTS = ["À analyser", "En cours", "Informations manquantes",
           "Prêt pour accompagnement", "Clôturé"]


# --------------------------------------------------------------------------- #
#  Base dédiée aux dossiers (migration additive, isolée de fco.db)            #
# --------------------------------------------------------------------------- #
def _conseil_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(CONSEIL_DB))
    conn.execute(
        """CREATE TABLE IF NOT EXISTS dossier_suivi (
              id            INTEGER PRIMARY KEY AUTOINCREMENT,
              client        TEXT NOT NULL,
              exploitation  TEXT,
              statut        TEXT NOT NULL DEFAULT 'À analyser',
              notes         TEXT,
              date_creation TEXT NOT NULL,
              date_maj      TEXT NOT NULL
           )""")
    conn.commit()
    return conn


def list_dossiers(conn) -> pd.DataFrame:
    return pd.read_sql_query(
        "SELECT id, client, exploitation, statut, notes, date_creation, date_maj "
        "FROM dossier_suivi ORDER BY date_maj DESC", conn)


def create_dossier(conn, client, exploitation, statut, notes) -> int:
    now = _dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    cur = conn.execute(
        "INSERT INTO dossier_suivi (client, exploitation, statut, notes, "
        "date_creation, date_maj) VALUES (?,?,?,?,?,?)",
        (client, exploitation, statut, notes, now, now))
    conn.commit()
    return cur.lastrowid


def update_dossier(conn, did, client, exploitation, statut, notes) -> None:
    now = _dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    conn.execute(
        "UPDATE dossier_suivi SET client=?, exploitation=?, statut=?, notes=?, "
        "date_maj=? WHERE id=?",
        (client, exploitation, statut, notes, now, did))
    conn.commit()


# Jeu de dossiers de DÉMONSTRATION (fictifs, pour illustrer l'outil en soutenance).
# Noms d'exploitations volontairement génériques : aucune donnée réelle.
# Format : (client, exploitation, statut, notes, jours_anciennete)
DEMO_DOSSIERS = [
    ("GAEC des Trois Chênes", "Élevage ovin — Aube", "Prêt pour accompagnement",
     "3 brebis avec charge virale positive confirmée au laboratoire. Vaccination "
     "du troupeau à planifier avec le vétérinaire.", 2),
    ("EARL du Val Fleuri", "Bovins lait — Marne", "En cours",
     "Photo analysée : signes suspects de FCO. Vétérinaire contacté, en attente "
     "de confirmation qPCR.", 3),
    ("Ferme de la Prairie", "Ovins & caprins — Haute-Marne", "Informations manquantes",
     "Il manque les résultats de laboratoire et le nombre exact d'animaux concernés.", 5),
    ("SCEA du Grand Pré", "Bovins viande — Aube", "À analyser",
     "Nouvel adhérent, premier signalement. Dossier à instruire.", 1),
    ("GAEC de la Fontaine", "Ovins — Marne", "Clôturé",
     "Contrôle négatif confirmé au laboratoire. Aucune suite. Dossier clos.", 12),
    ("EARL des Coteaux", "Bovins mixte — Ardennes", "En cours",
     "Suivi post-vaccination du troupeau. Rien à signaler pour l'instant.", 7),
    ("Élevage Martin", "Ovins — Aube", "Informations manquantes",
     "Photos floues à reprendre. Coordonnées du vétérinaire sanitaire à confirmer.", 9),
]


def seed_demo(conn) -> int:
    """Insère les dossiers de démonstration absents (idempotent). Renvoie le nombre ajouté."""
    existants = set(pd.read_sql_query("SELECT client FROM dossier_suivi", conn)["client"])
    ajoutes = 0
    for client, exploitation, statut, notes, jours in DEMO_DOSSIERS:
        if client in existants:
            continue
        d = (_dt.datetime.now() - _dt.timedelta(days=jours)).strftime("%Y-%m-%d %H:%M")
        conn.execute(
            "INSERT INTO dossier_suivi (client, exploitation, statut, notes, "
            "date_creation, date_maj) VALUES (?,?,?,?,?,?)",
            (client, exploitation, statut, notes, d, d))
        ajoutes += 1
    conn.commit()
    return ajoutes


# --------------------------------------------------------------------------- #
#  Petits helpers de rendu (réutilisent le CSS global)                        #
# --------------------------------------------------------------------------- #
def _hero(badge: str, title: str, sub: str) -> None:
    st.markdown(f'<div class="hero"><span class="pill">{badge}</span>'
                f'<h1>{title}</h1><p>{sub}</p></div>', unsafe_allow_html=True)


def _kpi(value, label) -> str:
    return f'<div class="kpi"><div class="v">{value}</div><div class="l">{label}</div></div>'


# --------------------------------------------------------------------------- #
#  A. Tableau de bord                                                          #
# --------------------------------------------------------------------------- #
def _dashboard(conn) -> None:
    df = list_dossiers(conn)

    st.markdown("#### Suivi des dossiers")
    if df.empty:
        st.info("Aucun dossier enregistré pour le moment. Créez-en un dans l'onglet "
                "**Dossiers / Suivi**.")
    a, b, c, d = st.columns(4)
    a.markdown(_kpi(len(df), "Dossiers"), unsafe_allow_html=True)
    surveiller = int(df["statut"].isin(["À analyser", "Informations manquantes"]).sum()) if not df.empty else 0
    b.markdown(_kpi(surveiller, "À surveiller"), unsafe_allow_html=True)
    en_cours = int((df["statut"] == "En cours").sum()) if not df.empty else 0
    c.markdown(_kpi(en_cours, "En cours"), unsafe_allow_html=True)
    clotures = int((df["statut"] == "Clôturé").sum()) if not df.empty else 0
    d.markdown(_kpi(clotures, "Clôturés"), unsafe_allow_html=True)

    if not df.empty:
        st.write("")
        rep = df["statut"].value_counts().rename_axis("Statut").reset_index(name="Nombre")
        st.markdown("**Répartition des dossiers par statut**")
        st.bar_chart(rep.set_index("Statut"))
        st.markdown("**Derniers dossiers enregistrés**")
        st.dataframe(df[["client", "exploitation", "statut", "date_maj"]].head(5),
                     use_container_width=True, hide_index=True)

    st.caption("Astuce : l'analyse des données scientifiques (charge virale, "
               "sérotypes, images) est disponible dans le volet « Analyse des données ».")


# --------------------------------------------------------------------------- #
#  B. Dossiers / Suivi                                                         #
# --------------------------------------------------------------------------- #
def _dossiers(conn) -> None:
    st.markdown("#### Dossiers de suivi")
    st.caption("Les dossiers sont stockés dans une base dédiée (`conseiller.db`), "
               "sans modifier les données d'analyses existantes.")

    d1, d2 = st.columns([1.4, 3])
    if d1.button("🧪 Charger des dossiers de démonstration", use_container_width=True):
        n = seed_demo(conn)
        st.success(f"{n} dossier(s) de démonstration ajouté(s).") if n else \
            st.info("Les dossiers de démonstration sont déjà présents.")
        st.rerun()
    d2.caption("Exemples **fictifs** pour illustrer l'outil (aucune donnée réelle).")

    df = list_dossiers(conn)
    options = ["➕ Nouveau dossier"] + [
        f"#{r.id} — {r.client} ({r.statut})" for r in df.itertuples()]
    choix = st.selectbox("Sélectionner un dossier", options, key="cons_sel_dossier")

    if choix.startswith("➕"):
        did, cur = None, {"client": "", "exploitation": "", "statut": STATUTS[0], "notes": ""}
    else:
        did = int(choix.split("—")[0].strip().lstrip("#"))
        row = df[df["id"] == did].iloc[0]
        cur = {"client": row["client"], "exploitation": row["exploitation"] or "",
               "statut": row["statut"], "notes": row["notes"] or ""}
        st.session_state["cons_dossier_courant"] = {
            "id": did, "client": cur["client"], "exploitation": cur["exploitation"],
            "statut": cur["statut"], "notes": cur["notes"]}

    with st.form("form_dossier"):
        client = st.text_input("Client / éleveur *", value=cur["client"])
        exploitation = st.text_input("Exploitation", value=cur["exploitation"])
        statut = st.selectbox("Statut de suivi", STATUTS,
                              index=STATUTS.index(cur["statut"]) if cur["statut"] in STATUTS else 0)
        notes = st.text_area("Notes de suivi", value=cur["notes"], height=120)
        submitted = st.form_submit_button("💾 Enregistrer", use_container_width=True)

    if submitted:
        if not client.strip():
            st.error("Le nom du client est obligatoire.")
        elif did is None:
            new_id = create_dossier(conn, client.strip(), exploitation.strip(), statut, notes.strip())
            st.success(f"Dossier #{new_id} créé.")
            st.rerun()
        else:
            update_dossier(conn, did, client.strip(), exploitation.strip(), statut, notes.strip())
            st.success("Dossier mis à jour.")
            st.rerun()

    if not df.empty:
        st.write("")
        st.markdown("**Tous les dossiers**")
        st.dataframe(df[["id", "client", "exploitation", "statut", "date_maj"]],
                     use_container_width=True, hide_index=True)


# --------------------------------------------------------------------------- #
#  C. Assistant conseiller                                                     #
# --------------------------------------------------------------------------- #
def _assistant(conn) -> None:
    st.markdown("#### Assistant conseiller")
    dossier = st.session_state.get("cons_dossier_courant")
    tous = list_dossiers(conn).to_dict("records")
    if dossier:
        st.caption(f"Dossier ouvert : **{dossier['client']}** ({dossier.get('statut', '')}). "
                   f"L'assistant connaît aussi les **{len(tous)} dossiers** de la base.")
    else:
        st.caption(f"L'assistant connaît les **{len(tous)} dossiers** de la base : "
                   "vous pouvez l'interroger sur n'importe quel client en le nommant.")
    context = {"dossier": dossier, "dossiers": tous}
    assistant.render_chat(
        "conseiller",
        suggestions=[
            "Résume-moi ce dossier.",
            "Quelles informations manquent ?",
            "Prépare une synthèse avant mon rendez-vous.",
            "Quels dossiers nécessitent une attention particulière ?",
            "Génère une checklist d'accompagnement.",
            "Explique le résultat en langage métier.",
        ],
        context=context,
        placeholder="Ex. : résume-moi ce dossier, quelles infos manquent…")


# --------------------------------------------------------------------------- #
#  D. Génération de synthèse                                                   #
# --------------------------------------------------------------------------- #
def _synthese_markdown(d: dict) -> str:
    now = _dt.datetime.now().strftime("%d/%m/%Y %H:%M")
    manquants = assistant._dossier_missing(d) if d else []
    lignes = [
        f"# Synthèse conseiller — {d.get('client', 'sans nom') if d else 'sans dossier'}",
        "",
        "## Informations principales",
        f"- Client / éleveur : {d.get('client', '—') if d else '—'}",
        f"- Exploitation : {(d.get('exploitation') or '—') if d else '—'}",
        f"- Statut de suivi : {d.get('statut', '—') if d else '—'}",
        "",
        "## Notes de suivi",
        (d.get("notes") or "Aucune note.") if d else "Aucun dossier sélectionné.",
        "",
        "## Points de vigilance",
        ("- " + "\n- ".join(manquants)) if manquants else "- Aucun point bloquant identifié.",
        "",
        "## Prochaines actions recommandées",
        "- Compléter les informations manquantes ci-dessus." if manquants else
        "- Poursuivre l'accompagnement selon le statut du dossier.",
        "- Confirmer tout résultat suspect auprès d'un vétérinaire si nécessaire.",
        "",
        f"_Généré le {now} — outil d'aide à la décision, ne remplace pas un avis "
        "vétérinaire._",
    ]
    return "\n".join(lignes)


def _synthese(conn) -> None:
    st.markdown("#### Générer une synthèse")
    dossier = st.session_state.get("cons_dossier_courant")
    if not dossier:
        st.info("Sélectionnez d'abord un dossier dans l'onglet « Dossiers / Suivi ».")
        return
    md = _synthese_markdown(dossier)
    st.markdown(md)
    stamp = _dt.datetime.now().strftime("%Y%m%d")
    nom = f"synthese_{dossier['client'].replace(' ', '_')}_{stamp}"
    c1, c2 = st.columns(2)
    c1.download_button("⬇️ Exporter (Markdown)", md.encode("utf-8"),
                       nom + ".md", "text/markdown", use_container_width=True)
    c2.download_button("⬇️ Exporter (texte)", md.encode("utf-8"),
                       nom + ".txt", "text/plain", use_container_width=True)


# --------------------------------------------------------------------------- #
#  Page principale                                                            #
# --------------------------------------------------------------------------- #
def page_conseiller() -> None:
    _hero("Espace conseiller",
          "Suivi & accompagnement des éleveurs",
          "Centralisez les informations, suivez les dossiers, préparez vos synthèses. "
          "Outil métier d'aide à la décision — pas un diagnostic vétérinaire.")
    conn = _conseil_conn()
    t1, t2, t3, t4 = st.tabs(
        ["📊 Tableau de bord", "🗂️ Dossiers / Suivi", "💬 Assistant", "📝 Synthèse"])
    with t1:
        _dashboard(conn)
    with t2:
        _dossiers(conn)
    with t3:
        _assistant(conn)
    with t4:
        _synthese(conn)
    conn.close()
