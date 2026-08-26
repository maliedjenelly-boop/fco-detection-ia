# -*- coding: utf-8 -*-
# © 2025-2026 MALIEDJE Nelly Leaticia — Tous droits réservés.
# Projet FCO Studio — thèse Mastère Data & IA (RNCP 37137).
# Usage non commercial uniquement. Voir LICENCE.md.
"""Assistants FCO Studio — moteur hybride (base de connaissances + LLM optionnel).

Principe :
- BASE DE CONNAISSANCES : réponses vérifiées, écrites à la main, zéro invention.
  Fonctionne toujours, sans aucune clé API (idéal Streamlit Cloud gratuit).
- LLM (Claude) : activé automatiquement si une clé est présente dans
  .streamlit/secrets.toml -> section [anthropic]. Sinon, repli sur la base de
  connaissances. Le LLM reçoit un cadre strict (ne jamais poser de diagnostic,
  ne rien inventer, rappeler le rôle d'aide à la décision).
- Deux rôles DISTINCTS :
    * "eleveur"    -> langage très simple, pédagogie, prévention.
    * "conseiller" -> langage métier, suivi de dossier, synthèse.

Extension future prévue : brancher une base documentaire (PDF, fiches FCO,
procédures internes) dans `retrieve_context()` sans changer l'interface.
"""
from __future__ import annotations

import re
import streamlit as st

# Modèles par défaut (surchargeables via `model = "..."` dans secrets.toml).
# Gemini est le fournisseur privilégié (offre gratuite via Google AI Studio).
# Anthropic Claude reste pris en charge si une clé [anthropic] est fournie.
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
DEFAULT_ANTHROPIC_MODEL = "claude-opus-5"

DISCLAIMER = ("Rappel : cet outil est une **aide à la décision**. Il ne remplace "
              "pas l'avis d'un vétérinaire ni une confirmation de laboratoire.")

AVATARS = {"eleveur": "🐑", "conseiller": "👨‍💼", "user": "🧑"}


# --------------------------------------------------------------------------- #
#  BASE DE CONNAISSANCES                                                       #
# --------------------------------------------------------------------------- #
# Chaque entrée : (groupes de mots-clés, réponse).
# Un groupe est satisfait si AU MOINS un de ses mots apparaît dans la question.
# Le score d'une entrée = nombre de groupes satisfaits ; la meilleure gagne.

KB_ELEVEUR: list[tuple[list[list[str]], str]] = [
    ([["symptôme", "symptome", "signe", "reconnaît", "reconnait"]],
     "Les principaux signes de la FCO sont : de la **fièvre**, un animal **abattu**, "
     "des **œdèmes de la face**, des **rougeurs, lésions ou ulcères dans la bouche**, "
     "un **écoulement au nez**, parfois des **boiteries**. Dans les cas graves, la "
     "langue peut devenir bleue (d'où le nom « bluetongue »). Ces signes ne sont pas "
     "propres à la FCO : seul un vétérinaire peut confirmer."),
    ([["transmet", "transmis", "attrape", "contamin", "propage", "moucheron", "culicoïd", "culicoid"]],
     "La FCO se transmet par la **piqûre de petits moucherons** (les Culicoïdes). "
     "Elle ne se transmet **pas** directement d'un animal à l'autre par contact. "
     "Comme les moucherons dépendent du climat, la maladie est **saisonnière** "
     "(surtout de la fin de l'été à l'automne)."),
    ([["prévention", "prevention", "protéger", "proteger", "protège", "éviter", "eviter", "troupeau"]],
     "Pour protéger votre troupeau : limitez l'exposition aux moucherons (abris, "
     "insecticides/répulsifs adaptés), surveillez vos animaux régulièrement, isolez "
     "tout animal qui présente des signes, et renseignez-vous sur la **vaccination** "
     "auprès de votre vétérinaire (c'est le moyen le plus efficace contre la FCO). "
     "Signalez rapidement toute suspicion."),
    ([["probabilité", "probabilite", "confiance", "pourcentage", "%", "score", "fiable", "sûr", "sur "]],
     "Le pourcentage affiché est le **niveau de confiance** du modèle, pas une "
     "certitude. Par exemple « suspect à 80 % » veut dire que le modèle penche vers "
     "« signes suspects », mais il peut se tromper. Plus le pourcentage est élevé, "
     "plus le modèle est sûr — mais **seul le vétérinaire ou le laboratoire tranche**."),
    ([["appeler", "vétérinaire", "veterinaire", "véto", "veto", "contacter", "qui prévenir", "prévenir"]],
     "Appelez votre **vétérinaire sanitaire** dès que vous avez un doute : animal "
     "avec de la fièvre, des lésions dans la bouche, des œdèmes, ou un résultat "
     "« signes suspects » dans l'application. La FCO est une maladie **à déclaration "
     "obligatoire** : le vétérinaire préviendra les autorités si besoin. En attendant, "
     "isolez l'animal et ne le déplacez pas."),
    ([["que faire", "première", "premiere", "action", "étape", "etape", "dois-je", "faire quoi", "conduite"]],
     "Si vous avez un doute : 1) **isolez** l'animal suspect du reste du troupeau ; "
     "2) **appelez votre vétérinaire** ; 3) **ne déplacez pas** les animaux avant son "
     "avis ; 4) notez la **date d'apparition** des signes et le **nombre d'animaux** "
     "concernés. L'application vous aide à décider, mais c'est le vétérinaire qui agit."),
    ([["c'est quoi", "qu'est-ce", "définition", "definition", "fco", "fièvre catarrhale", "fievre catarrhale", "bluetongue", "maladie"]],
     "La **FCO (Fièvre Catarrhale Ovine)**, aussi appelée « bluetongue », est une "
     "maladie **virale** des ruminants (moutons, bovins…). Elle est transmise par des "
     "moucherons et fait l'objet d'une **surveillance obligatoire**. Elle n'est pas "
     "dangereuse pour l'homme, mais elle peut affaiblir les animaux et provoquer des "
     "pertes dans l'élevage. La détecter tôt est important."),
]

KB_CONSEILLER: list[tuple[list[list[str]], str]] = [
    ([["étape", "etape", "accompagn", "processus", "démarche", "demarche", "suivi"]],
     "Étapes types d'accompagnement d'un dossier : 1) **recueil** des informations "
     "(exploitation, animaux, résultats disponibles) ; 2) **analyse** des résultats "
     "(laboratoire et/ou image) ; 3) **identification** des points de vigilance et des "
     "informations manquantes ; 4) **restitution** à l'éleveur (synthèse claire) ; "
     "5) **orientation** vers le vétérinaire si nécessaire ; 6) **suivi** et clôture "
     "du dossier."),
    ([["expliqu", "résultat", "resultat", "interpréter", "interpreter", "signifie", "veut dire"]],
     "En langage métier : un résultat **laboratoire « infecté »** signifie que du "
     "virus a été détecté dans l'échantillon (charge virale > 0) ; **« négatif »** "
     "signifie qu'aucune charge n'a été mesurée. Un résultat **image « signes "
     "suspects »** signale des lésions visibles à confirmer. Aucun de ces résultats "
     "n'est un diagnostic : ils orientent l'accompagnement et la décision d'alerter "
     "le vétérinaire."),
    ([["manque", "manquant", "compléter", "completer", "incomplet", "à confirmer", "a confirmer"]],
     "Pour repérer les informations manquantes d'un dossier, vérifiez : identité de "
     "l'exploitation et de l'éleveur, type et nombre d'animaux, résultats de "
     "laboratoire, éventuelles photos, dates, et coordonnées vétérinaires. Le module "
     "« Dossiers / Suivi » indique le statut ; un dossier « Informations manquantes » "
     "signale qu'il faut compléter avant l'accompagnement."),
    ([["surveill", "attention", "prioritaire", "urgent", "vigilance", "risque"]],
     "Les dossiers à surveiller en priorité sont ceux dont le statut est **« À "
     "analyser »** ou **« Informations manquantes »**, et ceux qui présentent des "
     "résultats « infecté » ou « signes suspects ». Le tableau de bord conseiller "
     "affiche ces indicateurs pour vous aider à prioriser."),
    ([["checklist", "check-list", "liste de suivi", "à faire", "a faire", "todo"]],
     "Checklist de suivi type : ☐ exploitation identifiée ☐ résultats laboratoire "
     "récupérés ☐ photos analysées (si disponibles) ☐ points de vigilance notés ☐ "
     "informations manquantes listées ☐ synthèse préparée ☐ vétérinaire contacté si "
     "besoin ☐ dossier mis à jour. Vous pouvez générer cette checklist depuis le "
     "module « Synthèse »."),
    ([["synthèse", "synthese", "compte rendu", "compte-rendu", "rendez-vous", "rdv", "résumé", "resume", "résume", "resume"]],
     "Pour préparer un rendez-vous, la synthèse conseiller reprend : informations "
     "principales du dossier, résultats disponibles, points de vigilance, éléments "
     "manquants, prochaines actions recommandées et date de génération. Générez-la "
     "depuis l'onglet « Synthèse », puis exportez-la en TXT ou Markdown."),
]


def _score(question: str, groups: list[list[str]]) -> int:
    q = question.lower()
    return sum(1 for g in groups if any(w in q for w in g))


def _kb_best(kb, question: str):
    best, best_score = None, 0
    for groups, answer in kb:
        s = _score(question, groups)
        if s > best_score:
            best, best_score = answer, s
    return best if best_score > 0 else None


def _result_explanation(context: dict | None) -> str | None:
    """Réponse spéciale « explique mon résultat » à partir du dernier résultat."""
    res = (context or {}).get("last_result")
    if not res:
        return ("Je n'ai pas encore de résultat pour vous. Lancez d'abord une analyse "
                "dans le **Mode Éleveur** (importez une photo de l'animal), puis "
                "revenez : je pourrai vous expliquer ce qu'il signifie.")
    label = str(res.get("label", "")).lower()
    conf = res.get("confidence")
    conf_txt = f" (confiance {conf:.0%})" if isinstance(conf, (int, float)) else ""
    if label in ("sain", "healthy"):
        return (f"Votre dernier résultat est **« animal sain »**{conf_txt}. Le modèle "
                "n'a pas repéré de signe évocateur de FCO sur la photo. C'est plutôt "
                "rassurant, mais ce n'est pas une garantie : continuez à surveiller "
                "votre animal, et en cas de doute (fièvre, lésions dans la bouche, "
                "œdèmes), contactez votre vétérinaire.")
    return (f"Votre dernier résultat est **« signes suspects de FCO »**{conf_txt}. "
            "Le modèle a repéré sur la photo des éléments qui pourraient évoquer la "
            "maladie. Ce n'est **pas un diagnostic**. Ce qu'il faut faire : isolez "
            "l'animal, ne le déplacez pas, et **appelez votre vétérinaire** pour une "
            "confirmation. Notez la date d'apparition des signes.")


def answer_kb(role: str, question: str, context: dict | None = None) -> str:
    """Réponse issue de la base de connaissances (toujours disponible)."""
    q = question.lower()
    if role == "eleveur" and any(w in q for w in
                                 ["mon résultat", "mon resultat", "explique", "expliquer",
                                  "classé", "classe", "suspect", "mon animal"]):
        exp = _result_explanation(context)
        if exp:
            return exp + "\n\n" + DISCLAIMER
    if role == "conseiller":
        special = _conseiller_dispatch(question, context)
        if special:
            return special
    kb = KB_ELEVEUR if role == "eleveur" else KB_CONSEILLER
    hit = _kb_best(kb, question)
    if hit:
        tail = "\n\n" + DISCLAIMER if role == "eleveur" else ""
        return hit + tail
    # repli
    if role == "eleveur":
        return ("Je ne suis pas sûr de bien comprendre votre question. Je peux vous "
                "aider à : comprendre votre résultat, connaître les symptômes de la "
                "FCO, savoir comment elle se transmet, quand appeler le vétérinaire, "
                "ou comment protéger votre troupeau.\n\n" + DISCLAIMER)
    return ("Je n'ai pas d'information vérifiée sur ce point précis. Je peux vous "
            "aider à : résumer un dossier, lister les informations manquantes, "
            "préparer une synthèse de rendez-vous, expliquer un résultat en langage "
            "métier, ou générer une checklist de suivi.")


def _summarize(d: dict) -> str:
    lignes = [f"**Synthèse du dossier — {d.get('client', 'sans nom')}**", ""]
    lignes.append(f"- Exploitation : {d.get('exploitation') or 'non renseignée'}")
    lignes.append(f"- Statut : {d.get('statut') or 'non défini'}")
    if d.get("notes"):
        lignes.append(f"- Notes : {d['notes']}")
    m = _dossier_missing(d)
    lignes.append("- Informations manquantes : " + (", ".join(m) if m else "aucune apparente"))
    return "\n".join(lignes)


def _dossier_summary(context: dict | None) -> str | None:
    d = (context or {}).get("dossier")
    return _summarize(d) if d else None


def _find_dossier(context: dict | None, question: str):
    """Retrouve un dossier dont le nom de client apparaît dans la question."""
    q = question.lower()
    for x in (context or {}).get("dossiers") or []:
        name = str(x.get("client", "")).strip().lower()
        if name and name in q:
            return x
    return None


def _conseiller_dispatch(question: str, context: dict | None):
    """Réponses métier structurées à partir des dossiers réels. None si aucune."""
    ql = question.lower()
    dossiers = (context or {}).get("dossiers") or []
    if dossiers and any(w in ql for w in ["surveill", "attention", "prioritaire",
                                          "nécessit", "necessit", "à traiter", "a traiter"]):
        a = [x for x in dossiers if x.get("statut") in ("À analyser", "Informations manquantes")]
        if a:
            return ("Dossiers à surveiller en priorité :\n"
                    + "\n".join(f"- **{x.get('client')}** — {x.get('statut')}" for x in a))
        return ("Aucun dossier ne nécessite une attention particulière pour le moment "
                "(aucun « À analyser » ni « Informations manquantes »).")
    d = _find_dossier(context, question) or (context or {}).get("dossier")
    if d:
        if "statut" in ql:
            return f"Statut du dossier **{d.get('client')}** : {d.get('statut', 'non défini')}."
        if any(w in ql for w in ["manque", "manquant", "complét", "complet", "incomplet"]):
            m = _dossier_missing(d)
            return (f"Pour le dossier **{d.get('client')}**, il manque : " + ", ".join(m) + ".") \
                if m else f"Le dossier **{d.get('client')}** ne présente pas d'information manquante apparente."
        if any(w in ql for w in ["résume", "resume", "synthèse", "synthese", "ce dossier", "ce client"]):
            return _summarize(d)
    return None


def _dossier_missing(d: dict) -> list[str]:
    manquants = []
    if not d.get("exploitation"):
        manquants.append("exploitation")
    if not d.get("notes"):
        manquants.append("notes de suivi")
    if not d.get("statut") or d.get("statut") == "À analyser":
        manquants.append("analyse à réaliser")
    return manquants


# --------------------------------------------------------------------------- #
#  BRANCHE LLM (optionnelle)                                                   #
# --------------------------------------------------------------------------- #
def _placeholder(key: str) -> bool:
    """Vrai si la clé est vide ou reste un placeholder du fichier d'exemple."""
    if not key:
        return True
    up = key.upper()
    return "COLLEZ" in up or "VOTRE_CLE" in up or "VOTRE_CLÉ" in up


def _llm_config():
    """Renvoie (provider, api_key, model) ou (None, None, None).

    Ordre de priorité : Gemini (gratuit) puis Anthropic Claude.
    """
    try:
        g = st.secrets["gemini"]
        k = g.get("api_key")
        if not _placeholder(k):
            return "gemini", k, g.get("model", DEFAULT_GEMINI_MODEL)
    except Exception:
        pass
    try:
        a = st.secrets["anthropic"]
        k = a.get("api_key")
        if not _placeholder(k):
            return "anthropic", k, a.get("model", DEFAULT_ANTHROPIC_MODEL)
    except Exception:
        pass
    return None, None, None


def llm_available() -> bool:
    return _llm_config()[0] is not None


def _llm_label() -> str:
    provider = _llm_config()[0]
    return {"gemini": "IA activée (Gemini)",
            "anthropic": "IA activée (Claude)"}.get(provider, "base de connaissances")


def _system_prompt(role: str, context: dict | None) -> str:
    base_regles = (
        "Règles absolues :\n"
        "- Tu es un assistant d'AIDE À LA DÉCISION, jamais un vétérinaire.\n"
        "- Ne pose JAMAIS de diagnostic vétérinaire définitif.\n"
        "- N'invente jamais de chiffres, de procédures administratives, de montants "
        "d'aide, de règles d'indemnisation ni de résultats. Si tu ne sais pas ou que "
        "l'information n'est pas fournie, dis-le clairement.\n"
        "- Rappelle, quand c'est pertinent, qu'une confirmation vétérinaire ou de "
        "laboratoire peut être nécessaire.\n"
        "- Réponds en français, de façon concise.\n"
    )
    if role == "eleveur":
        persona = (
            "Tu es l'assistant d'un ÉLEVEUR dans l'application FCO Studio. Tu expliques "
            "la Fièvre Catarrhale Ovine (FCO) et les résultats de l'application avec des "
            "mots TRÈS SIMPLES, sans jargon, comme à une personne non spécialiste.\n"
        )
        ctx = ""
        res = (context or {}).get("last_result")
        if res:
            ctx = (f"\nDernier résultat de l'éleveur dans l'application : "
                   f"{res.get('label')} (confiance {res.get('confidence')}). "
                   "Utilise-le si on te demande d'expliquer « mon résultat ».")
        faits = ("\nFaits fiables sur la FCO : maladie virale des ruminants, transmise "
                 "par des moucherons (Culicoïdes), à déclaration obligatoire, non "
                 "dangereuse pour l'homme. Signes : fièvre, abattement, œdèmes de la "
                 "face, lésions/ulcères buccaux, écoulement nasal, boiteries, parfois "
                 "langue bleue. Prévention : lutte contre les moucherons et vaccination.")
        return persona + faits + ctx + "\n\n" + base_regles
    # conseiller
    persona = (
        "Tu es l'assistant d'un CONSEILLER Cerfrance qui accompagne des éleveurs. "
        "Tu emploies un langage PROFESSIONNEL et métier (suivi de dossier, synthèse, "
        "organisation). Tu n'es pas un outil de diagnostic vétérinaire : tu aides à "
        "centraliser l'information, préparer des synthèses et organiser le suivi.\n"
    )
    parts = []
    d = (context or {}).get("dossier")
    if d:
        parts.append(f"Dossier actuellement ouvert dans l'interface : {d}.")
    dossiers = (context or {}).get("dossiers") or []
    if dossiers:
        lignes = []
        for x in dossiers[:60]:
            lignes.append(
                f"- Client: {x.get('client')} | Exploitation: {x.get('exploitation') or '—'} "
                f"| Statut: {x.get('statut')} | Notes: {x.get('notes') or '—'}")
        parts.append("Dossiers présents dans la base (tu PEUX répondre à leur sujet, y "
                     "compris si l'utilisateur nomme un client sans l'avoir ouvert) :\n"
                     + "\n".join(lignes))
    else:
        parts.append("Aucun dossier n'est encore enregistré dans la base.")
    ctx = "\n\n".join(parts)
    ctx += ("\n\nRègles d'usage des données : réponds à partir de la liste ci-dessus. "
            "Si un client demandé y figure, utilise ses informations (ne dis pas qu'il "
            "est absent, ne réclame pas des données déjà présentes). S'il n'y figure "
            "vraiment pas, indique clairement qu'il n'est pas dans la base.")
    return persona + "\n\n" + ctx + "\n\n" + base_regles


def _to_messages(history: list[dict]) -> list[dict]:
    """Historique -> messages API (alternance user/assistant), texte simple."""
    msgs = []
    for m in history:
        if m["role"] in ("user", "assistant"):
            msgs.append({"role": m["role"], "content": m["content"]})
    return msgs


def stream_llm(role: str, history: list[dict], context: dict | None):
    """Générateur de texte via le LLM configuré. Repli géré par l'appelant."""
    provider, key, model = _llm_config()
    if provider == "gemini":
        yield from _stream_gemini(key, model, role, history, context)
    elif provider == "anthropic":
        yield from _stream_anthropic(key, model, role, history, context)


def _stream_gemini(key, model, role, history, context):
    from google import genai            # import différé : dépendance optionnelle
    from google.genai import types
    client = genai.Client(api_key=key)
    # Gemini attend les rôles "user" / "model" (l'assistant = "model").
    contents = [{"role": "model" if m["role"] == "assistant" else "user",
                 "parts": [{"text": m["content"]}]}
                for m in history if m["role"] in ("user", "assistant")]
    # thinking_budget=0 : réponse directe (pas de réflexion invisible qui
    # consommerait le budget de tokens sur les modèles Gemini "2.5").
    try:
        thinking = types.ThinkingConfig(thinking_budget=0)
    except Exception:
        thinking = None
    cfg = types.GenerateContentConfig(
        system_instruction=_system_prompt(role, context),
        max_output_tokens=1024,
        thinking_config=thinking)
    for chunk in client.models.generate_content_stream(
            model=model, contents=contents, config=cfg):
        text = getattr(chunk, "text", None)
        if text:
            yield text


def _stream_anthropic(key, model, role, history, context):
    import anthropic                     # import différé : dépendance optionnelle
    client = anthropic.Anthropic(api_key=key)
    with client.messages.stream(
        model=model,
        max_tokens=1024,
        system=_system_prompt(role, context),
        messages=_to_messages(history),
    ) as stream:
        for text in stream.text_stream:
            yield text


# --------------------------------------------------------------------------- #
#  RENDU STREAMLIT DU CHAT                                                     #
# --------------------------------------------------------------------------- #
def render_chat(role: str, suggestions: list[str], context: dict | None = None,
                placeholder: str = "Posez votre question…") -> None:
    key = f"chat_{role}"
    st.session_state.setdefault(key, [])

    top = st.columns([1, 2])
    if top[0].button("🔄 Nouvelle conversation", key=f"new_{role}"):
        st.session_state[key] = []
        st.rerun()
    top[1].caption("Assistant · " + _llm_label())

    # questions suggérées
    clicked = None
    st.caption("Questions fréquentes :")
    scols = st.columns(2)
    for i, q in enumerate(suggestions):
        if scols[i % 2].button(q, key=f"sg_{role}_{i}", use_container_width=True):
            clicked = q

    # historique
    for m in st.session_state[key]:
        with st.chat_message(m["role"], avatar=AVATARS.get(m["role"] if m["role"] == "user" else role)):
            st.markdown(m["content"])

    prompt = st.chat_input(placeholder) or clicked
    if not prompt:
        return

    st.session_state[key].append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar=AVATARS["user"]):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar=AVATARS[role]):
        reply = ""
        if llm_available():
            try:
                reply = st.write_stream(stream_llm(role, st.session_state[key], context))
            except Exception as e:  # repli sur la base de connaissances
                reply = answer_kb(role, prompt, context)
                st.markdown(reply)
                st.caption(f"(IA indisponible, réponse issue de la base de connaissances)")
        else:
            reply = answer_kb(role, prompt, context)
            st.markdown(reply)

    st.session_state[key].append({"role": "assistant", "content": reply})
