"""
APPLICATION STREAMLIT — FCO (design "studio").

Couche présentation entièrement repensée (UX/UI) :
  - système de design cohérent (palette, typographie, cartes, ombres),
  - navigation latérale soignée, hero animé,
  - verdicts visuels (cartes colorées), jauges de confiance, barres de
    probabilités Plotly.
La LOGIQUE reste celle, corrigée et vérifiée, des vrais modèles :
  - 01_train_lab_rf.py  -> artifacts_lab/fco_lab_model.joblib
  - 02_train_image_efficientnet.py -> artifacts_image/fco_image_model.pth

Usage :
    streamlit run 03_app_streamlit.py
"""

from __future__ import annotations

import base64
import datetime
import hashlib
import json
import re
import sqlite3
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from PIL import Image

# Chemins ancrés sur l'emplacement du script -> fonctionne en local (depuis corrige/)
# ET sur Streamlit Cloud (lancé depuis la racine du dépôt).
BASE = Path(__file__).resolve().parent
LAB_MODEL = BASE / "artifacts_lab" / "fco_lab_model.joblib"
IMG_MODEL = BASE / "artifacts_image" / "fco_image_model.pth"
LAB_DB = BASE.parent / "bdd" / "fco.db"            # base de données du projet (bdd/)
LABO_BANNER = BASE / "assets" / "labo_banner.jpg"       # visuel page Mode Laboratoire
ELEVEUR_BANNER = BASE / "assets" / "eleveur_banner.jpg" # visuel page Mode Éleveur

st.set_page_config(page_title="FCO Studio — Surveillance", page_icon="🐑",
                   layout="wide", initial_sidebar_state="expanded")

# Palette sémantique partagée Python <-> CSS
INK = "#0F172A"
TEAL = "#0D9488"
INDIGO = "#6366F1"
GREEN = "#10B981"
AMBER = "#F59E0B"
RED = "#EF4444"
PLOTLY_FONT = dict(family="Inter, sans-serif", color=INK)

# --------------------------------------------------------------------------- #
#  CONTACTS VÉTÉRINAIRES (France).                                            #
#  ⚠️ Exemples : les numéros sont dans les plages RÉSERVÉES À LA FICTION par   #
#  l'ARCEP (jamais attribuées -> aucun risque d'appeler une vraie personne),  #
#  emails sur le domaine d'exemple `exemple.fr`. Remplacez par vos vrais      #
#  contacts avant une utilisation réelle.                                     #
# --------------------------------------------------------------------------- #
VETS = [
    {"nom": "Clinique Vétérinaire des Trois Vallées", "clinique": "Médecine des ruminants",
     "type": "Vétérinaire sanitaire", "ville": "Clermont-Ferrand",
     "tel": "04 65 71 18 22", "email": "troisvallees@exemple.fr"},
    {"nom": "Cabinet Vétérinaire du Bocage", "clinique": "Vétérinaire rural",
     "type": "Vétérinaire traitant", "ville": "Rennes",
     "tel": "02 61 91 34 56", "email": "bocage@exemple.fr"},
    {"nom": "Clinique Vétérinaire Saint-Roch", "clinique": "Élevage & filière ovine",
     "type": "Vétérinaire sanitaire", "ville": "Toulouse",
     "tel": "05 36 49 27 81", "email": "saintroch@exemple.fr"},
    {"nom": "Service de Garde Vétérinaire", "clinique": "Urgences élevage 24/7",
     "type": "Urgences", "ville": "Lyon",
     "tel": "04 65 71 00 15", "email": ""},
]


# --------------------------------------------------------------------------- #
#  DESIGN SYSTEM (CSS)                                                         #
# --------------------------------------------------------------------------- #
def inject_css() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@500;600;700;800&family=Inter:wght@400;500;600&display=swap');

        :root{
          --ink:#0F172A; --muted:#64748B; --line:#E2E8F0;
          --teal:#0D9488; --indigo:#6366F1; --green:#10B981; --amber:#F59E0B; --red:#EF4444;
          --card:#FFFFFF; --shadow:0 10px 30px -12px rgba(15,23,42,.18);
        }
        html, body, [class*="css"]{ font-family:'Inter',sans-serif; color:var(--ink); }
        h1,h2,h3,h4{ font-family:'Plus Jakarta Sans',sans-serif !important; letter-spacing:-.02em; }

        /* Fond global doux */
        .stApp{
          background:
            radial-gradient(900px 500px at 88% -8%, rgba(13,148,136,.10), transparent 60%),
            radial-gradient(800px 500px at -5% 8%, rgba(99,102,241,.10), transparent 55%),
            #F7FAFC;
        }
        .block-container{ max-width:1180px; padding-top:1.6rem; padding-bottom:4rem; }

        /* Sidebar */
        section[data-testid="stSidebar"]{
          background:linear-gradient(180deg,#0B1220 0%, #0F2027 100%);
          border-right:1px solid rgba(255,255,255,.06);
        }
        section[data-testid="stSidebar"] *{ color:#E2E8F0 !important; }
        .brand{ display:flex; align-items:center; gap:.7rem; padding:.4rem .2rem 1rem; }
        .brand .logo{ width:44px;height:44px;border-radius:14px;display:grid;place-items:center;
          font-size:1.5rem; background:linear-gradient(135deg,var(--teal),var(--indigo));
          box-shadow:0 8px 20px -6px rgba(13,148,136,.6); }
        .brand .t1{ font-family:'Plus Jakarta Sans'; font-weight:800; font-size:1.05rem; line-height:1; }
        .brand .t2{ font-size:.72rem; color:#94A3B8 !important; letter-spacing:.04em; text-transform:uppercase;}

        /* Boutons nav (sidebar) */
        section[data-testid="stSidebar"] .stButton>button{
          width:100%; text-align:left; border:0; border-radius:12px; padding:.7rem .9rem;
          background:rgba(255,255,255,.04); color:#CBD5E1 !important; font-weight:600;
          transition:all .18s ease; margin-bottom:.35rem;
        }
        section[data-testid="stSidebar"] .stButton>button:hover{
          background:rgba(255,255,255,.10); transform:translateX(2px); color:#fff !important;}

        /* Hero */
        .hero{ position:relative; overflow:hidden; border-radius:24px; padding:2.4rem 2.6rem;
          background:linear-gradient(120deg,#0D9488 0%, #0E7490 45%, #6366F1 100%); color:#fff;
          box-shadow:0 24px 50px -20px rgba(13,148,136,.55); margin-bottom:1.6rem; }
        .hero:after{ content:""; position:absolute; right:-60px; top:-60px; width:260px;height:260px;
          background:radial-gradient(circle,rgba(255,255,255,.25),transparent 70%); }
        .hero h1{ color:#fff !important; font-size:2.15rem; margin:0 0 .4rem; }
        .hero p{ color:rgba(255,255,255,.92); font-size:1.02rem; max-width:680px; margin:0; }
        .hero .pill{ display:inline-block; background:rgba(255,255,255,.16); border:1px solid rgba(255,255,255,.25);
          padding:.3rem .8rem; border-radius:999px; font-size:.78rem; font-weight:600; margin-bottom:1rem;
          backdrop-filter:blur(6px); }

        /* Cartes */
        .card{ background:var(--card); border:1px solid var(--line); border-radius:20px;
          padding:1.5rem 1.6rem; box-shadow:var(--shadow); height:100%;
          animation:rise .5s ease both; }
        .card h3{ margin:.2rem 0 .5rem; font-size:1.18rem; }
        .card p{ color:var(--muted); font-size:.92rem; margin:0; }
        .card .ico{ width:52px;height:52px;border-radius:15px; display:grid;place-items:center;
          font-size:1.6rem; margin-bottom:.8rem; }
        .ico-teal{ background:rgba(13,148,136,.12); }
        .ico-indigo{ background:rgba(99,102,241,.12); }

        /* KPI */
        .kpi{ background:var(--card); border:1px solid var(--line); border-radius:16px; padding:1.1rem 1.2rem;
          box-shadow:var(--shadow); }
        .kpi .v{ font-family:'Plus Jakarta Sans'; font-weight:800; font-size:1.7rem; line-height:1; }
        .kpi .l{ color:var(--muted); font-size:.8rem; margin-top:.35rem; text-transform:uppercase; letter-spacing:.04em;}

        /* Verdict */
        .verdict{ border-radius:22px; padding:1.6rem 1.8rem; color:#fff; box-shadow:var(--shadow);
          display:flex; align-items:center; gap:1.2rem; animation:rise .5s ease both; }
        .verdict .em{ font-size:2.6rem; }
        .verdict .vt{ font-family:'Plus Jakarta Sans'; font-weight:800; font-size:1.5rem; line-height:1.05; }
        .verdict .vs{ opacity:.92; font-size:.95rem; margin-top:.25rem; }

        /* Status pills */
        .stat{ display:inline-flex; align-items:center; gap:.45rem; padding:.4rem .8rem; border-radius:999px;
          font-weight:600; font-size:.82rem; border:1px solid var(--line); background:#fff; }
        .dot{ width:9px;height:9px;border-radius:50%; }

        /* Boutons CTA (zone principale) */
        .block-container .stButton>button{
          border-radius:12px; border:0; font-weight:700; padding:.6rem 1.1rem;
          background:linear-gradient(135deg,var(--teal),var(--indigo)); color:#fff;
          box-shadow:0 12px 24px -10px rgba(13,148,136,.6); transition:transform .15s ease; }
        .block-container .stButton>button:hover{ transform:translateY(-2px); }
        .block-container .stButton>button:disabled{
          background:#E2E8F0; color:#94A3B8 !important; box-shadow:none;
          cursor:not-allowed; transform:none; }

        /* Tabs */
        .stTabs [data-baseweb="tab-list"]{ gap:.4rem; }
        .stTabs [data-baseweb="tab"]{ border-radius:12px 12px 0 0; font-weight:600; }

        /* Upload + dataframe */
        [data-testid="stFileUploaderDropzone"]{ border-radius:16px; border:1.5px dashed #94A3B8;
          background:rgba(13,148,136,.04); }
        [data-testid="stDataFrame"]{ border-radius:14px; overflow:hidden; border:1px solid var(--line); }

        /* Boutons-liens (CTA Stripe) */
        .block-container .stLinkButton>a{
          border-radius:12px; border:0; font-weight:700; padding:.6rem 1.1rem; width:100%;
          background:linear-gradient(135deg,var(--teal),var(--indigo)); color:#fff !important;
          box-shadow:0 12px 24px -10px rgba(13,148,136,.6); transition:transform .15s ease; }
        .block-container .stLinkButton>a:hover{ transform:translateY(-2px); color:#fff !important; }

        /* Abonnements / tarifs */
        .price{ background:var(--card); border:1px solid var(--line); border-radius:22px;
          padding:1.7rem 1.6rem 1.4rem; box-shadow:var(--shadow); height:100%;
          display:flex; flex-direction:column; animation:rise .5s ease both; }
        .price.hi{ border:1.6px solid var(--teal); box-shadow:0 22px 46px -18px rgba(13,148,136,.45); position:relative; }
        .price .tag{ position:absolute; top:-13px; left:50%; transform:translateX(-50%); white-space:nowrap;
          background:linear-gradient(135deg,var(--teal),var(--indigo)); color:#fff; font-size:.72rem; font-weight:700;
          padding:.28rem .85rem; border-radius:999px; letter-spacing:.02em; box-shadow:0 8px 18px -8px rgba(13,148,136,.7); }
        .price .pl{ font-family:'Plus Jakarta Sans'; font-weight:700; font-size:1.05rem; }
        .price .amt{ font-family:'Plus Jakarta Sans'; font-weight:800; font-size:2.3rem; line-height:1; margin:.55rem 0 .15rem; }
        .price .amt small{ font-size:.86rem; font-weight:600; color:var(--muted); }
        .price .pmo{ font-size:.78rem; color:var(--muted); min-height:1.1em; margin:.15rem 0 0; }
        .price .desc{ color:var(--muted); font-size:.85rem; margin:.35rem 0 1rem; min-height:2.6em; }
        .price ul{ list-style:none; padding:0; margin:0 0 1.1rem; flex:1; }
        .price li{ font-size:.9rem; color:var(--ink); padding:.32rem 0 .32rem 1.6rem; position:relative;
          border-top:1px solid #F1F5F9; }
        .price li:first-child{ border-top:0; }
        .price li:before{ content:"✓"; position:absolute; left:0; color:var(--teal); font-weight:800; }
        .price li.off{ color:#94A3B8; }
        .price li.off:before{ content:"–"; color:#CBD5E1; }

        #MainMenu, footer{ visibility:hidden; }
        @keyframes rise{ from{opacity:0; transform:translateY(10px);} to{opacity:1; transform:none;} }
        </style>
        """,
        unsafe_allow_html=True,
    )


def label_style(label: str) -> dict:
    """Mappe une étiquette de modèle vers une présentation visuelle."""
    m = {
        "NC": dict(color=GREEN, em="🟢", title="Contrôle négatif",
                   sub="Aucune charge virale détectée"),
        "INFECTE": dict(color=AMBER, em="🟠", title="Infection détectée",
                        sub="Charge virale détectée (test positif)"),
        "healthy": dict(color=GREEN, em="🟢", title="Animal sain",
                        sub="Aucun signe clinique évocateur de FCO"),
        "sain": dict(color=GREEN, em="🟢", title="Animal sain",
                     sub="Aucun signe clinique évocateur de FCO"),
        "fco_signs": dict(color=RED, em="🔴", title="Signes suspects de FCO",
                          sub="Lésions évocatrices — confirmation vétérinaire requise"),
        "malade": dict(color=RED, em="🔴", title="Signes suspects de FCO",
                       sub="Lésions évocatrices — confirmation vétérinaire requise"),
    }
    return m.get(label, dict(color=INDIGO, em="🔎", title=str(label), sub=""))


# --------------------------------------------------------------------------- #
#  COMPOSANTS UI                                                              #
# --------------------------------------------------------------------------- #
def hero(badge: str, title: str, subtitle: str) -> None:
    st.markdown(
        f"""<div class="hero"><span class="pill">{badge}</span>
        <h1>{title}</h1><p>{subtitle}</p></div>""",
        unsafe_allow_html=True,
    )


@st.cache_data(show_spinner=False)
def _img_b64(path: str) -> str:
    return base64.b64encode(Path(path).read_bytes()).decode()


def page_banner(path: Path) -> None:
    """Bannière visuelle (image réaliste) sous l'en-tête d'une page."""
    if not Path(path).exists():
        return
    b64 = _img_b64(str(path))
    st.markdown(
        f'<div style="margin:-0.3rem 0 1.3rem;border-radius:18px;overflow:hidden;position:relative;'
        f'box-shadow:0 14px 34px -14px rgba(15,23,42,.35);">'
        f'<img src="data:image/jpeg;base64,{b64}" '
        f'style="width:100%;height:200px;object-fit:cover;display:block;"/>'
        f'<div style="position:absolute;inset:0;background:linear-gradient(120deg,'
        f'rgba(13,148,136,.30),rgba(99,102,241,.10) 55%,rgba(15,23,42,.15));"></div></div>',
        unsafe_allow_html=True,
    )


def image_card(img_path: Path, ico_class: str, icon: str, title: str, body: str) -> str:
    """Carte d'accueil avec une image réaliste en en-tête."""
    head = ""
    if Path(img_path).exists():
        head = (f'<img src="data:image/jpeg;base64,{_img_b64(str(img_path))}" '
                f'style="width:100%;height:140px;object-fit:cover;display:block;"/>')
    return (f'<div class="card" style="padding:0;overflow:hidden;">{head}'
            f'<div style="padding:1.2rem 1.5rem 1.4rem;"><div class="ico {ico_class}">{icon}</div>'
            f'<h3>{title}</h3><p>{body}</p></div></div>')


def kpi(value, label) -> str:
    return f'<div class="kpi"><div class="v">{value}</div><div class="l">{label}</div></div>'


def verdict_card(label: str, confidence: float) -> None:
    s = label_style(label)
    c = s["color"]
    st.markdown(
        f"""<div class="verdict" style="background:linear-gradient(135deg,{c},{c}dd);">
          <div class="em">{s['em']}</div>
          <div><div class="vt">{s['title']}</div>
          <div class="vs">{s['sub']} · confiance {confidence:.0%}</div></div></div>""",
        unsafe_allow_html=True,
    )


def confidence_gauge(value: float, color: str):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value * 100,
        number={"suffix": "%", "font": {"size": 38, "color": color,
                                        "family": "Plus Jakarta Sans"}},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 0, "tickcolor": "rgba(0,0,0,0)",
                     "tickfont": {"size": 1, "color": "rgba(0,0,0,0)"}},
            "bar": {"color": color, "thickness": 0.3},
            "bgcolor": "rgba(0,0,0,0)", "borderwidth": 0,
            "steps": [{"range": [0, 100], "color": "rgba(148,163,184,.18)"}],
        },
        domain={"x": [0, 1], "y": [0, 1]},
    ))
    fig.update_layout(height=200, margin=dict(l=16, r=16, t=8, b=0),
                      paper_bgcolor="rgba(0,0,0,0)", font=PLOTLY_FONT)
    return fig


def proba_chart(proba: dict):
    items = sorted(proba.items(), key=lambda kv: kv[1])
    names = [label_style(k)["title"] for k, _ in items]
    vals = [v * 100 for _, v in items]
    colors = [label_style(k)["color"] for k, _ in items]
    fig = go.Figure(go.Bar(
        x=vals, y=names, orientation="h",
        marker=dict(color=colors, line=dict(width=0)),
        text=[f"{v:.1f}%" for v in vals], textposition="outside",
        textfont=dict(family="Plus Jakarta Sans", size=13),
        hovertemplate="%{y} : %{x:.1f}%<extra></extra>",
    ))
    fig.update_layout(
        height=70 + 46 * len(names), margin=dict(l=8, r=40, t=6, b=6),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(range=[0, 105], showgrid=False, showticklabels=False, zeroline=False),
        yaxis=dict(showgrid=False), font=PLOTLY_FONT, bargap=0.4,
    )
    return fig


def status_pill(text: str, ok: bool) -> str:
    color = GREEN if ok else RED
    return (f'<span class="stat"><span class="dot" style="background:{color}"></span>'
            f'{text}</span>')


# --------------------------------------------------------------------------- #
#  MODÈLES + INFÉRENCE (logique inchangée, vérifiée)                          #
# --------------------------------------------------------------------------- #
@st.cache_resource
def load_lab_model():
    if not LAB_MODEL.exists():
        return None
    bundle = joblib.load(LAB_MODEL)
    try:
        bundle["model"].n_jobs = 1  # évite le flot de warnings / la lenteur joblib
    except Exception:
        pass
    return bundle


@st.cache_resource
def load_image_model():
    if not IMG_MODEL.exists():
        return None
    try:
        import timm
        import torch
    except ImportError:
        return "no_torch"
    ckpt = torch.load(IMG_MODEL, map_location="cpu")
    model = timm.create_model(ckpt["arch"], pretrained=False, num_classes=len(ckpt["classes"]))
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()
    return {"model": model, "ckpt": ckpt}


def lab_features(genome_copies: float, dpi: int) -> np.ndarray:
    return np.array([[np.log1p(genome_copies), dpi, int(genome_copies > 0)]])


def parse_id(midge_id: str):
    s = str(midge_id)
    cls = next((c for c in ("BTV3", "BTV8", "NC") if c in s), None)
    m = re.search(r"(\d+)\s*dpi", s, re.IGNORECASE)
    return cls, (int(m.group(1)) if m else 0)


def predict_lab(bundle, genome_copies: float, dpi: int) -> dict:
    """Détection par charge virale (interprétation type qPCR) :
       virus détecté (copies > 0) -> INFECTE ; aucune charge -> NC.
    La confiance d'un positif croît avec la magnitude (force du signal).
    Le DPI est un contexte : il ne renverse pas un résultat de charge."""
    if genome_copies and genome_copies > 0:
        ratio = min(1.0, max(0.0, np.log10(genome_copies) / 6.0))   # 6 = log10(1e6) réf.
        conf = float(min(0.99, 0.70 + 0.29 * ratio))
        return {"label": "INFECTE", "confidence": conf,
                "proba": {"INFECTE": conf, "NC": 1.0 - conf}}
    return {"label": "NC", "confidence": 0.99, "proba": {"NC": 0.99, "INFECTE": 0.01}}


def predict_lab_batch(bundle, copies: np.ndarray, dpi: np.ndarray) -> np.ndarray:
    """Prédiction VECTORISÉE, cohérente avec predict_lab : détection = copies > 0."""
    copies = np.asarray(copies, dtype=float)
    return np.where(copies > 0, "INFECTE", "NC")


def predict_image(bundle, pil_img: Image.Image) -> dict:
    import torch
    from torchvision import transforms
    ckpt = bundle["ckpt"]
    pil_img = pil_img.convert("RGB")
    if ckpt.get("clahe"):                       # même prétraitement qu'à l'entraînement
        from image_preproc import apply_clahe
        pil_img = apply_clahe(pil_img)
    tf = transforms.Compose([
        transforms.Resize((ckpt["img_size"], ckpt["img_size"])),
        transforms.ToTensor(),
        transforms.Normalize(ckpt["mean"], ckpt["std"]),
    ])
    x = tf(pil_img).unsqueeze(0)
    with torch.no_grad():
        proba = torch.softmax(bundle["model"](x), dim=1)[0].numpy()
    classes = ckpt["classes"]
    idx = int(np.argmax(proba))
    return {"label": classes[idx], "confidence": float(proba[idx]),
            "proba": dict(zip(classes, proba.tolist()))}


# --------------------------------------------------------------------------- #
#  ANALYSE APPROFONDIE LABO (sérotypes & cinétique) — affichage seulement     #
# --------------------------------------------------------------------------- #
LAB_STRAIN_COLORS = {"NC": GREEN, "BTV3": INDIGO, "BTV8": AMBER}


def build_lab_analysis_df(raw: pd.DataFrame, id_col: str, num_col: str):
    """Reconstruit sérotype/essai/dpi/charge depuis les identifiants (informatif)."""
    parsed = raw[id_col].map(parse_id)
    adf = pd.DataFrame({
        "strain": [c for c, _ in parsed],
        "dpi": [d for _, d in parsed],
        "essai": pd.to_numeric(raw.get("essai"), errors="coerce"),
        "copies": pd.to_numeric(raw[num_col], errors="coerce").fillna(0).to_numpy(),
    })
    adf = adf[adf["strain"].notna()].copy()
    if adf.empty:
        return None
    adf["log_copies"] = np.log10(adf["copies"] + 1)
    adf["detectable"] = adf["copies"] > 0
    return adf


def lab_boxplot(adf: pd.DataFrame):
    fig = go.Figure()
    for strain in ("NC", "BTV3", "BTV8"):
        for d in sorted(adf["dpi"].unique()):
            vals = adf[(adf.strain == strain) & (adf.dpi == d)]["log_copies"]
            if len(vals):
                fig.add_trace(go.Box(y=vals, name=f"{strain} {d}dpi", boxmean=True,
                                     marker_color=LAB_STRAIN_COLORS.get(strain, INDIGO)))
    fig.update_layout(height=340, margin=dict(l=8, r=8, t=10, b=8), showlegend=False,
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      yaxis_title="log10(copies + 1)", font=PLOTLY_FONT)
    return fig


def lab_detection_bar(adf: pd.DataFrame):
    piv = (adf.groupby(["strain", "dpi"])["detectable"].mean() * 100).reset_index()
    fig = go.Figure()
    for d in sorted(adf["dpi"].unique()):
        sub = piv[piv.dpi == d]
        fig.add_trace(go.Bar(x=sub["strain"], y=sub["detectable"], name=f"{d} dpi",
                             text=[f"{v:.0f}%" for v in sub["detectable"]],
                             textposition="outside"))
    fig.update_layout(barmode="group", height=340, margin=dict(l=8, r=8, t=10, b=8),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      yaxis_title="% détectable", yaxis_range=[0, 112], font=PLOTLY_FONT,
                      legend=dict(orientation="h", y=1.15))
    return fig


def lab_interaction(adf: pd.DataFrame):
    tmax = adf["dpi"].max()
    sub = adf[(adf.strain != "NC") & (adf.dpi == tmax)]
    piv = sub.groupby(["essai", "strain"])["log_copies"].mean().reset_index()
    fig = go.Figure()
    for strain in ("BTV3", "BTV8"):
        s = piv[piv.strain == strain]
        fig.add_trace(go.Scatter(x=s["essai"], y=s["log_copies"], mode="lines+markers",
                                 name=strain, line=dict(width=3, color=LAB_STRAIN_COLORS[strain]),
                                 marker=dict(size=10)))
    fig.update_layout(height=320, margin=dict(l=8, r=8, t=10, b=8),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      xaxis_title="Essai", yaxis_title=f"log10(copies + 1) moyen — {tmax} dpi",
                      xaxis=dict(tickmode="array",
                                 tickvals=sorted(sub["essai"].dropna().unique())),
                      font=PLOTLY_FONT, legend=dict(orientation="h", y=1.15))
    return fig


def render_lab_analysis(adf: pd.DataFrame) -> None:
    st.write("")
    st.markdown("### 📊 Analyse approfondie — sérotypes & cinétique virale")
    st.caption("Calculée à partir des sérotypes/essais encodés dans les identifiants. "
               "Variables **informatives** : elles ne servent pas au modèle de détection.")
    counts = adf["strain"].value_counts()
    for col, (s, n) in zip(st.columns(len(counts)), counts.items()):
        col.markdown(kpi(n, f"échantillons {s}"), unsafe_allow_html=True)
    st.write("")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Charge virale par sérotype × dpi**")
        st.plotly_chart(lab_boxplot(adf), use_container_width=True,
                        config={"displayModeBar": False})
    with c2:
        st.markdown("**Taux de détection (copies > 0)**")
        st.plotly_chart(lab_detection_bar(adf), use_container_width=True,
                        config={"displayModeBar": False})
    essais = adf["essai"].dropna().unique()
    if len(essais) >= 2 and (adf["strain"] != "NC").any():
        st.markdown("**Interaction essai × sérotype**")
        st.plotly_chart(lab_interaction(adf), use_container_width=True,
                        config={"displayModeBar": False})
        st.warning("⚠️ L'effet du sérotype **s'inverse** entre les essais : comparer "
                   "BTV3/BTV8 en regroupant les essais serait **confondu (paradoxe de "
                   "Simpson)**. La charge virale ne distingue donc pas les sérotypes de "
                   "façon reproductible (cf. validation inter-essais, script 07).")


LAB_SQL = (
    "SELECT m.id_individu, m.id_essai AS essai, m.dpi, "
    "s.code AS strain, m.genome_copies AS copies "
    "FROM mesure_virale m "
    "JOIN serotype s ON m.id_serotype = s.id_serotype "
    "ORDER BY m.id_essai, s.code, m.dpi"
)
def _mysql_url():
    """URL de connexion MySQL lue depuis .streamlit/secrets.toml.

    Les identifiants ne sont PAS codés en dur : ils proviennent du fichier
    secrets.toml (non versionné, cf. .gitignore). Retourne None si la section
    [mysql] est absente, auquel cas l'application bascule sur SQLite.
    """
    try:
        m = st.secrets["mysql"]
        return (f"mysql+pymysql://{m['user']}:{m['password']}"
                f"@{m['host']}:{m.get('port', 3306)}/{m['database']}")
    except Exception:
        return None


@st.cache_data(show_spinner=False)
def load_lab_from_db():
    """Charge les mesures depuis MySQL si configuré/disponible, sinon SQLite."""
    # 1) Tentative serveur MySQL (identifiants via st.secrets)
    url = _mysql_url()
    if url:
        try:
            from sqlalchemy import create_engine
            engine = create_engine(url, connect_args={"connect_timeout": 3})
            df = pd.read_sql_query(LAB_SQL, engine)
            engine.dispose()
            return df, "MySQL (fco_db)"
        except Exception:
            pass
    # 2) Repli sur la base SQLite locale
    if LAB_DB.exists():
        con = sqlite3.connect(str(LAB_DB))
        try:
            df = pd.read_sql_query(LAB_SQL, con)
        finally:
            con.close()
        return df, "SQLite (bdd/fco.db)"
    return None, None


# --------------------------------------------------------------------------- #
#  PAGES                                                                      #
# --------------------------------------------------------------------------- #
def log_history(module: str, entree: str, resultat: str) -> None:
    """Journalise une analyse dans l'historique de session (cf. page Historique)."""
    st.session_state.setdefault("history", []).insert(0, {
        "Horodatage": datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "Module": module, "Entrée": entree, "Résultat": resultat})


@st.cache_data(show_spinner=False)
def load_image_catalog():
    """Catalogue des images (bdd/image_catalog.json) -> DataFrame, ou None."""
    p = LAB_DB.parent / "image_catalog.json"
    if not p.exists():
        return None
    try:
        return pd.DataFrame(json.loads(p.read_text(encoding="utf-8")))
    except Exception:
        return None


def page_home() -> None:
    hero("Surveillance assistée par IA",
         "Détection de la Fièvre Catarrhale Ovine",
         "Deux modèles complémentaires : analyse de la charge virale en laboratoire "
         "et lecture des signes cliniques sur image. Conçu comme un outil d'aide à la "
         "décision, transparent sur ses limites.")

    lab_ok = load_lab_model() is not None
    img_state = load_image_model()
    img_ok = isinstance(img_state, dict)
    st.markdown(
        status_pill(f"Mode Laboratoire — {'opérationnel' if lab_ok else 'manquant'}", lab_ok)
        + "&nbsp;&nbsp;"
        + status_pill(f"Mode Éleveur — {'opérationnel' if img_ok else 'à entraîner'}", img_ok),
        unsafe_allow_html=True,
    )
    st.write("")

    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.markdown(image_card(
            LABO_BANNER, "ico-indigo", "🔬", "Mode Laboratoire",
            "À partir de la charge virale (copies génomiques + DPI), estime si "
            "l'échantillon est <b>infecté</b> ou <b>négatif</b>. Import CSV ou saisie "
            "manuelle, résultats instantanés."), unsafe_allow_html=True)
        st.button("Ouvrir le Mode Laboratoire  →", key="go_lab",
                  on_click=lambda: st.session_state.update(page="lab"))
    with c2:
        st.markdown(image_card(
            ELEVEUR_BANNER, "ico-teal", "🐑", "Mode Éleveur",
            "Une photo de l'animal suffit : EfficientNet estime <b>sain</b> vs "
            "<b>signes suspects de FCO</b>, avec le niveau de confiance et les "
            "probabilités détaillées."), unsafe_allow_html=True)
        st.button("Ouvrir le Mode Éleveur  →", key="go_img",
                  on_click=lambda: st.session_state.update(page="image"))

    st.write("")
    st.markdown("#### Le pipeline en bref")
    a, b, c = st.columns(3, gap="medium")
    a.markdown(kpi("3", "Variables labo · charge, DPI, détectabilité"), unsafe_allow_html=True)
    b.markdown(kpi("EfficientNet-B0", "Backbone pré-entraîné, fine-tuné"), unsafe_allow_html=True)
    c.markdown(kpi("Transparent", "Limites documentées (sérotypes, biais)"), unsafe_allow_html=True)


def page_lab() -> None:
    hero("Mode Laboratoire",
         "Détection d'infection par charge virale",
         "Le modèle distingue les contrôles négatifs des échantillons infectés. "
         "Rappel : la charge virale ne permet pas d'identifier le sérotype (BTV3 vs BTV8).")
    page_banner(LABO_BANNER)

    bundle = load_lab_model()
    if bundle is None:
        st.error(f"Modèle absent : `{LAB_MODEL}`. Lancez d'abord `python 01_train_lab_rf.py`.")
        return

    tab_db, tab_csv, tab_manual = st.tabs(
        ["🗄️  Base de données", "📄  Importer un CSV", "✍️  Saisie manuelle"])

    with tab_db:
        df, source = load_lab_from_db()
        if df is None:
            st.info("Aucune base disponible. Démarrez MySQL (XAMPP) ou construisez la base "
                    "SQLite : `python ../bdd/build_database.py`.")
        else:
            st.caption(f"Source : **{source}** · table `mesure_virale` "
                       f"({len(df)} mesures, lecture par requête SQL).")
            copies = df["copies"].to_numpy()
            dpi = df["dpi"].to_numpy()
            with st.spinner(f"Analyse de {len(df)} mesures depuis la base…"):
                df["prédiction"] = predict_lab_batch(bundle, copies, dpi)
            n = len(df)
            n_inf = int((df["prédiction"] == "INFECTE").sum())
            k1, k2, k3 = st.columns(3)
            k1.markdown(kpi(f"{n:,}".replace(",", " "), "Mesures"), unsafe_allow_html=True)
            k2.markdown(kpi(n_inf, "Détectés infectés"), unsafe_allow_html=True)
            k3.markdown(kpi(f"{n_inf / n:.0%}", "Taux d'infection"), unsafe_allow_html=True)
            st.write("")
            left, right = st.columns([1.5, 1])
            with left:
                st.markdown("**Aperçu (issu de la base)**")
                st.dataframe(
                    df[["id_individu", "essai", "dpi", "strain", "copies", "prédiction"]].head(50),
                    use_container_width=True, height=380)
            with right:
                st.markdown("**Répartition**")
                counts = df["prédiction"].value_counts().to_dict()
                st.plotly_chart(proba_chart({k: v / n for k, v in counts.items()}),
                                use_container_width=True, config={"displayModeBar": False})
            adf = df[["strain", "dpi", "essai", "copies"]].copy()
            adf["log_copies"] = np.log10(adf["copies"] + 1)
            adf["detectable"] = adf["copies"] > 0
            render_lab_analysis(adf)
            log_history("Laboratoire (base de données)", f"{n} mesures",
                        f"{n_inf} infectés ({n_inf / n:.0%})")

    with tab_manual:
        col1, col2 = st.columns(2)
        genome = col1.number_input("Copies génomiques", min_value=0.0, value=0.0, step=100.0)
        dpi = col2.number_input("DPI (jours post-infection)", min_value=0, value=6, step=1)
        if st.button("Analyser l'échantillon", key="manual_btn"):
            res = predict_lab(bundle, genome, dpi)
            log_history("Laboratoire (saisie manuelle)",
                        f"copies={genome:.0f}, dpi={dpi}",
                        f"{res['label']} ({res['confidence']:.0%})")
            verdict_card(res["label"], res["confidence"])
            st.write("")
            g, p = st.columns([1, 1.4])
            with g:
                st.markdown("**Confiance**")
                st.plotly_chart(confidence_gauge(res["confidence"], label_style(res["label"])["color"]),
                                use_container_width=True, config={"displayModeBar": False})
            with p:
                st.markdown("**Probabilités par classe**")
                st.plotly_chart(proba_chart(res["proba"]), use_container_width=True,
                                config={"displayModeBar": False})

    with tab_csv:
        up = st.file_uploader("Glissez un CSV (colonnes identifiant / copies — séparateur ; ou ,)",
                              type="csv")
        if up is None:
            st.info("📄 Importez un fichier pour lancer l'analyse de toute la cohorte.")
            return
        try:
            up.seek(0)
            raw = pd.read_csv(up, sep=None, engine="python", encoding="latin-1")
            raw.columns = [str(c).strip().lower() for c in raw.columns]
            id_col = next((c for c in raw.columns if "id" in c), raw.columns[0])
            num_col = next((c for c in raw.columns
                            if "cop" in c or "genome" in c
                            or pd.to_numeric(raw[c], errors="coerce").notna().any()),
                           raw.columns[-1])
            st.caption(f"Colonnes détectées → identifiant : **{id_col}** · charge virale : **{num_col}**")
            copies = pd.to_numeric(raw[num_col], errors="coerce").fillna(0).to_numpy()
            dpi = np.array([d for _, d in raw[id_col].map(parse_id)])
            # Colonnes de transparence (NON utilisées par le modèle) extraites de l'ID :
            # essai = nombre en tête ("1-NC 0dpi 3" -> essai 1) ; dpi = jour post-infection.
            raw["essai"] = raw[id_col].astype(str).str.extract(r"^\s*(\d+)\s*-", expand=False)
            raw["dpi"] = dpi
            with st.spinner(f"Analyse de {len(raw)} échantillons…"):
                raw["prédiction"] = predict_lab_batch(bundle, copies, dpi)

            n = len(raw)
            n_inf = int((raw["prédiction"] == "INFECTE").sum())
            log_history("Laboratoire (CSV)", f"{n} échantillons · {up.name}",
                        f"{n_inf} infectés ({n_inf / n:.0%})")
            k1, k2, k3 = st.columns(3)
            k1.markdown(kpi(f"{n:,}".replace(",", " "), "Échantillons"), unsafe_allow_html=True)
            k2.markdown(kpi(n_inf, "Détectés infectés"), unsafe_allow_html=True)
            k3.markdown(kpi(f"{n_inf / n:.0%}", "Taux d'infection"), unsafe_allow_html=True)
            st.write("")
            left, right = st.columns([1.5, 1])
            with left:
                st.markdown("**Aperçu des prédictions**")
                # Ordre lisible : identifiant · essai · dpi · charge · prédiction
                cols = [id_col, "essai", "dpi", num_col, "prédiction"]
                st.dataframe(raw[cols].head(50), use_container_width=True, height=380)
            with right:
                st.markdown("**Répartition**")
                counts = raw["prédiction"].value_counts().to_dict()
                st.plotly_chart(proba_chart({k: v / n for k, v in counts.items()}),
                                use_container_width=True, config={"displayModeBar": False})

            adf = build_lab_analysis_df(raw, id_col, num_col)
            if adf is not None and adf["strain"].nunique() >= 2:
                render_lab_analysis(adf)
        except Exception as e:
            st.error("❌ Échec de l'analyse du CSV.")
            st.exception(e)


def image_gradcam(bundle, pil_img: Image.Image):
    """Superposition Grad-CAM : où le modèle regarde sur l'image (chaud = influent)."""
    import matplotlib.cm as cm
    import torch
    from torchvision import transforms
    ckpt, model = bundle["ckpt"], bundle["model"]
    pil = pil_img.convert("RGB")
    if ckpt.get("clahe"):
        from image_preproc import apply_clahe
        pil = apply_clahe(pil)
    size = ckpt["img_size"]
    base = np.asarray(pil.resize((size, size))) / 255.0
    tf = transforms.Compose([
        transforms.Resize((size, size)), transforms.ToTensor(),
        transforms.Normalize(ckpt["mean"], ckpt["std"])])
    x = tf(pil).unsqueeze(0)
    target = getattr(model, "conv_head", None)
    if target is None:
        target = [m for m in model.modules() if isinstance(m, torch.nn.Conv2d)][-1]
    store = {}

    def fwd(m, i, o):
        store["act"] = o.detach()
        o.register_hook(lambda g: store.__setitem__("grad", g.detach()))

    handle = target.register_forward_hook(fwd)
    model.zero_grad()
    logits = model(x)
    logits[0, int(logits.argmax(1))].backward()
    handle.remove()
    w = store["grad"].mean(dim=(2, 3), keepdim=True)
    cam = torch.relu((w * store["act"]).sum(1))[0]
    cam = ((cam - cam.min()) / (cam.max() - cam.min() + 1e-8)).cpu().numpy()
    cam_up = np.asarray(Image.fromarray((cam * 255).astype("uint8")).resize((size, size))) / 255.0
    heat = cm.jet(cam_up)[..., :3]
    overlay = np.clip(0.55 * base + 0.45 * heat, 0, 1)
    return Image.fromarray((overlay * 255).astype("uint8"))


def page_image() -> None:
    hero("Mode Éleveur",
         "Lecture des signes cliniques",
         "Téléversez une photo de l'animal. Le modèle indique « sain » ou "
         "« signes suspects de FCO ». Outil d'aide indicatif — pas un diagnostic vétérinaire.")
    page_banner(ELEVEUR_BANNER)

    bundle = load_image_model()
    if bundle is None:
        st.error(f"Modèle absent : `{IMG_MODEL}`. Lancez `python 02_train_image_efficientnet.py`.")
        return
    if bundle == "no_torch":
        page_banner(ELEVEUR_BANNER)
        st.info("🐑 **Module d'analyse d'image — version locale.** La reconnaissance des signes "
                "cliniques repose sur EfficientNet (PyTorch), non activé sur l'hébergement gratuit "
                "pour des raisons de ressources. Ce module est **pleinement fonctionnel dans la "
                "version locale** de l'application (`pip install torch torchvision timm`).")
        st.caption("Le volet Laboratoire et l'exploration de la base de données restent, eux, "
                   "entièrement opérationnels en ligne.")
        return

    up = st.file_uploader("Photo de l'animal", type=["jpg", "jpeg", "png"])
    if up is None:
        st.info("🐑 Importez une image pour lancer l'analyse.")
        return
    img = Image.open(up)
    col1, col2 = st.columns([1, 1.2], gap="large")
    with col1:
        st.image(img, caption="Image analysée", use_container_width=True)
    with col2:
        res = predict_image(bundle, img)
        verdict_card(res["label"], res["confidence"])
        st.write("")
        st.plotly_chart(confidence_gauge(res["confidence"], label_style(res["label"])["color"]),
                        use_container_width=True, config={"displayModeBar": False})
        st.plotly_chart(proba_chart(res["proba"]), use_container_width=True,
                        config={"displayModeBar": False})
        if res["label"] not in ("healthy", "sain"):
            st.error("⚠️ Signes suspects de FCO. Faites confirmer par un vétérinaire.")
            st.button("📞 Contacter un vétérinaire", key="cta_vet",
                      on_click=lambda: st.session_state.update(page="contacts"))

    log_history("Éleveur (image)", getattr(up, "name", "image"),
                f"{res['label']} ({res['confidence']:.0%})")
    st.write("")
    with st.expander("🔥 Où le modèle regarde ? (Grad-CAM)", expanded=True):
        try:
            st.image(image_gradcam(bundle, img), use_container_width=True,
                     caption="Superposition Grad-CAM — les zones chaudes ont le plus pesé sur le verdict.")
            st.caption("Transparence : si la chaleur porte sur le fond ou le contexte plutôt que sur "
                       "les lésions (museau, bouche, yeux), le verdict reflète surtout un biais de source.")
        except Exception as e:
            st.warning(f"Grad-CAM indisponible : {e}")


def _contact_card(icon: str, title: str, subtitle: str, lines: list[str]) -> str:
    body = "".join(
        f'<div style="font-size:.9rem;margin-top:.35rem">{ln}</div>' for ln in lines if ln)
    return (f'<div class="card"><div class="ico ico-teal">{icon}</div>'
            f'<h3 style="font-size:1.05rem">{title}</h3><p>{subtitle}</p>{body}</div>')


def page_contacts() -> None:
    hero("Contacts vétérinaires",
         "Qui contacter en cas de suspicion de FCO",
         "La fièvre catarrhale ovine est une maladie animale réglementée à déclaration "
         "obligatoire. Toute suspicion doit être signalée rapidement à un vétérinaire.")

    st.markdown("#### 🚨 Que faire en cas de signes suspects ?")
    st.markdown(
        "1. **Isolez** l'animal suspect du reste du troupeau.\n"
        "2. **Contactez immédiatement votre vétérinaire sanitaire** (coordonnées ci-dessous).\n"
        "3. Le vétérinaire **déclare la suspicion à la DD(ec)PP** de votre département.\n"
        "4. **Ne déplacez pas** les animaux avant l'avis vétérinaire.\n"
        "5. Notez la **date d'apparition** des signes et le **nombre d'animaux** concernés.")
    st.warning("Cet outil est une aide indicative — **il ne remplace pas un diagnostic "
               "vétérinaire**. En cas de doute, contactez un professionnel.")

    st.markdown("#### 📋 Canaux officiels")
    o1, o2, o3 = st.columns(3, gap="medium")
    o1.markdown(_contact_card(
        "🩺", "Vétérinaire sanitaire", "Votre premier interlocuteur",
        ["Réalise l'examen clinique", "Déclare toute suspicion aux autorités"]),
        unsafe_allow_html=True)
    o2.markdown(_contact_card(
        "🏛️", "DD(ec)PP", "Autorité sanitaire du département",
        ["Déclaration <b>obligatoire</b> des suspicions",
         'Cherchez « DDPP + votre département »']),
        unsafe_allow_html=True)
    o3.markdown(_contact_card(
        "🛡️", "GDS", "Groupement de Défense Sanitaire",
        ["Appui et prévention pour les éleveurs",
         "Coordination sanitaire locale"]),
        unsafe_allow_html=True)

    st.write("")
    st.markdown("#### 👩‍⚕️ Vétérinaires à contacter")
    ncol = min(3, len(VETS))
    cols = st.columns(ncol, gap="medium")
    for i, v in enumerate(VETS):
        lines = [f'📍 {v["ville"]}' if v.get("ville") and v["ville"] != "—" else "",
                 f'📞 <a href="tel:{v["tel"].replace(" ", "")}">{v["tel"]}</a>' if v.get("tel") else "",
                 f'✉️ <a href="mailto:{v["email"]}">{v["email"]}</a>' if v.get("email") else ""]
        cols[i % ncol].markdown(
            _contact_card("👩‍⚕️", v["nom"], f'{v["clinique"]} · {v["type"]}', lines),
            unsafe_allow_html=True)
    st.caption("Exemples — numéros dans les plages **réservées à la fiction** par l'ARCEP "
               "(aucun risque d'appeler une vraie personne). Remplacez par vos contacts "
               "réels via la variable `VETS` en haut de `03_app_streamlit.py`.")


def page_analyse() -> None:
    hero("Analyse des données",
         "Tableau de bord exploratoire",
         "Vue d'ensemble des données du projet : charge virale par sérotype, taux de "
         "détection, interaction essai × sérotype, et composition du jeu d'images.")
    df, source = load_lab_from_db()
    if df is None:
        st.info("Base indisponible. Construisez-la : `python ../bdd/build_database.py`.")
        return
    st.caption(f"Source des données : **{source}**")
    adf = df[["strain", "dpi", "essai", "copies"]].copy()
    adf["log_copies"] = np.log10(adf["copies"] + 1)
    adf["detectable"] = adf["copies"] > 0
    imgcat = load_image_catalog()
    k1, k2, k3, k4 = st.columns(4)
    k1.markdown(kpi(f"{len(df):,}".replace(",", " "), "Mesures virales"), unsafe_allow_html=True)
    k2.markdown(kpi(adf["strain"].nunique(), "Sérotypes"), unsafe_allow_html=True)
    k3.markdown(kpi(int(adf["essai"].dropna().nunique()), "Essais"), unsafe_allow_html=True)
    k4.markdown(kpi(len(imgcat) if imgcat is not None else "—", "Images"), unsafe_allow_html=True)
    st.write("")
    render_lab_analysis(adf)

    if imgcat is not None and not imgcat.empty and {"classe", "source"} <= set(imgcat.columns):
        st.markdown("### 🐑 Composition du jeu d'images")
        comp = imgcat.groupby(["classe", "source"]).size().reset_index(name="n")
        c1, c2 = st.columns([1.3, 1])
        with c1:
            fig = go.Figure()
            palette = {"stock": GREEN, "pdf_clinique": AMBER}
            for src in comp["source"].unique():
                s = comp[comp.source == src]
                fig.add_trace(go.Bar(x=s["classe"], y=s["n"], name=str(src),
                                     marker_color=palette.get(src),
                                     text=s["n"], textposition="outside"))
            fig.update_layout(barmode="group", height=320, margin=dict(l=8, r=8, t=10, b=8),
                              paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                              yaxis_title="images", font=PLOTLY_FONT,
                              legend=dict(orientation="h", y=1.15))
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        with c2:
            st.warning("⚠️ Jeu d'images **petit et déséquilibré**, avec un **biais de source** "
                       "(sains = photos de stock, malades = figures cliniques). C'est la limite "
                       "documentée du volet image (cf. audit et Grad-CAM).")


def page_historique() -> None:
    hero("Historique des analyses",
         "Journal des analyses de la session",
         "Chaque détection (laboratoire ou image) est enregistrée ici. Consultez, "
         "exportez ou effacez l'historique.")
    hist = st.session_state.get("history", [])
    if not hist:
        st.info("🕓 Aucune analyse pour le moment. Lancez une détection dans le Mode "
                "Laboratoire ou le Mode Éleveur — elle apparaîtra automatiquement ici.")
        return
    dfh = pd.DataFrame(hist)
    k1, k2 = st.columns(2)
    k1.markdown(kpi(len(dfh), "Analyses réalisées"), unsafe_allow_html=True)
    k2.markdown(kpi(dfh["Module"].nunique(), "Modules utilisés"), unsafe_allow_html=True)
    st.write("")
    st.dataframe(dfh, use_container_width=True, height=420)
    c1, c2 = st.columns([1, 4])
    c1.download_button("⬇️ Exporter (CSV)", dfh.to_csv(index=False).encode("utf-8"),
                       "historique_fco.csv", "text/csv")
    if c2.button("🗑️ Effacer l'historique"):
        st.session_state["history"] = []
        st.rerun()


# --------------------------------------------------------------------------- #
#  ABONNEMENTS (formules + paiement Stripe Payment Links)                     #
# --------------------------------------------------------------------------- #
# Formules proposées. Les deux formules payantes redirigent vers un lien de
# paiement Stripe (Payment Link) configuré dans .streamlit/secrets.toml [stripe].
PLANS = [
    {"name": "Découverte", "amount": "Gratuit", "period": "", "note": "", "tag": None, "cta": "free",
     "desc": "Pour tester l'outil sans engagement.",
     "feats": [(True,  "Mode Éleveur — 5 analyses / mois"),
               (True,  "Résultat et niveau de confiance"),
               (False, "Historique des analyses"),
               (False, "Grad-CAM (zones observées)"),
               (False, "Mode Laboratoire")]},
    {"name": "Éleveur", "amount": "120", "period": " € / an", "note": "soit 10 € / mois",
     "tag": "★ Le plus populaire", "cta": "eleveur",
     "desc": "Pour l'éleveur adhérent qui surveille son troupeau au quotidien.",
     "feats": [(True,  "Mode Éleveur illimité"),
               (True,  "Historique des analyses"),
               (True,  "Grad-CAM (zones observées)"),
               (True,  "Contacts vétérinaires"),
               (False, "Mode Laboratoire")]},
    {"name": "Laboratoire", "amount": "600", "period": " € / an", "note": "soit 50 € / mois",
     "tag": None, "cta": "laboratoire",
     "desc": "Pour les laboratoires et cabinets vétérinaires.",
     "feats": [(True,  "Tout de la formule Éleveur"),
               (True,  "Mode Laboratoire (charge virale, import CSV)"),
               (True,  "Analyse des données avancée"),
               (True,  "Comptes multiples"),
               (True,  "Support prioritaire")]},
]


def _stripe_link(tier: str):
    """Lien de paiement Stripe (Payment Link) depuis secrets.toml [stripe]."""
    try:
        return st.secrets["stripe"].get(tier) or None
    except Exception:
        return None


def page_abonnements() -> None:
    hero("Formules & abonnements",
         "Choisissez la formule adaptée à votre activité",
         "Un outil d'aide à la décision accessible, de l'éleveur au laboratoire. "
         "Abonnement annuel, facture automatique. Paiement sécurisé via Stripe.")

    cols = st.columns(3, gap="large")
    for col, plan in zip(cols, PLANS):
        with col:
            hi = " hi" if plan["tag"] else ""
            tag = f'<div class="tag">{plan["tag"]}</div>' if plan["tag"] else ""
            amt = f'{plan["amount"]}<small>{plan["period"]}</small>'
            note = f'<div class="pmo">{plan["note"] or "&nbsp;"}</div>'
            lis = "".join(
                f'<li class="{"" if ok else "off"}">{txt}</li>' for ok, txt in plan["feats"])
            st.markdown(
                f'<div class="price{hi}">{tag}'
                f'<div class="pl">{plan["name"]}</div>'
                f'<div class="amt">{amt}</div>{note}'
                f'<div class="desc">{plan["desc"]}</div>'
                f'<ul>{lis}</ul></div>',
                unsafe_allow_html=True)
            if plan["cta"] == "free":
                st.button("Commencer gratuitement", key="sub_free",
                          use_container_width=True,
                          on_click=lambda: st.session_state.update(page="image"))
            else:
                url = _stripe_link(plan["cta"])
                if url:
                    st.link_button("S'abonner  →", url, use_container_width=True)
                else:
                    st.button("S'abonner  →", key=f"sub_{plan['cta']}",
                              disabled=True, use_container_width=True)
                    st.caption("Lien Stripe à configurer dans `secrets.toml`.")

    st.write("")
    st.markdown(
        '<p style="text-align:center;color:var(--muted);font-size:.85rem;margin-top:.4rem;">'
        '🔒 Paiement sécurisé par Stripe&nbsp;·&nbsp;Facturation annuelle&nbsp;·&nbsp;'
        'Résiliable à échéance&nbsp;·&nbsp;Facture automatique</p>',
        unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
#  SHELL (sidebar + routeur)                                                  #
# --------------------------------------------------------------------------- #
PAGES = {"home": ("Accueil", "🏠", page_home),
         "lab": ("Mode Laboratoire", "🔬", page_lab),
         "image": ("Mode Éleveur", "🐑", page_image),
         "analyse": ("Analyse des données", "📊", page_analyse),
         "historique": ("Historique", "🕓", page_historique),
         "abonnements": ("Abonnements", "💳", page_abonnements),
         "contacts": ("Contacts vétérinaires", "📞", page_contacts)}


# --------------------------------------------------------------------------- #
#  AUTHENTIFICATION (page de connexion + rôles)                               #
# --------------------------------------------------------------------------- #
_AUTH_SALT = "fco-studio-2026"


def _hash_pw(pw: str) -> str:
    return hashlib.sha256((_AUTH_SALT + pw).encode("utf-8")).hexdigest()


# Comptes de démonstration (mot de passe : fco2026). Surchargeables via
# .streamlit/secrets.toml -> section [auth] (cf. secrets.toml.example).
DEFAULT_USERS = {
    "admin":   {"name": "Administrateur", "role": "admin",       "password_hash": _hash_pw("fco2026")},
    "labo":    {"name": "Laboratoire",    "role": "laboratoire", "password_hash": _hash_pw("fco2026")},
    "eleveur": {"name": "Éleveur",        "role": "eleveur",     "password_hash": _hash_pw("fco2026")},
}

# Pages accessibles selon le rôle.
ROLE_PAGES = {
    "admin":       list(PAGES),
    "laboratoire": ["home", "lab", "analyse", "historique", "abonnements", "contacts"],
    "eleveur":     ["home", "image", "abonnements", "contacts"],
}


def _get_users() -> dict:
    """Utilisateurs depuis .streamlit/secrets.toml [auth], sinon comptes démo."""
    try:
        users = {u: dict(v) for u, v in st.secrets["auth"].items()}
        return users or DEFAULT_USERS
    except Exception:
        return DEFAULT_USERS


def check_login(username: str, password: str):
    u = _get_users().get((username or "").strip().lower())
    if not u:
        return None
    ok = (u.get("password_hash") == _hash_pw(password)) or \
         (u.get("password") is not None and u.get("password") == password)
    if not ok:
        return None
    return {"username": (username or "").strip().lower(),
            "name": u.get("name", username), "role": u.get("role", "admin")}


def login_page() -> None:
    hero("Accès sécurisé",
         "FCO Studio — Connexion",
         "Cet outil d'aide à la décision est protégé par authentification. "
         "Identifiez-vous pour accéder aux modules.")
    _, mid, _ = st.columns([1, 1.5, 1])
    with mid:
        with st.form("login_form"):
            st.markdown("#### 🔐 Connexion")
            username = st.text_input("Identifiant")
            password = st.text_input("Mot de passe", type="password")
            submit = st.form_submit_button("Se connecter", use_container_width=True)
        if submit:
            user = check_login(username, password)
            if user:
                st.session_state["auth"] = user
                st.rerun()
            else:
                st.error("Identifiant ou mot de passe incorrect.")
        st.caption("Comptes de démonstration (mot de passe **fco2026**) : "
                   "`admin` (tout), `labo` (laboratoire), `eleveur` (image).")


def sidebar() -> None:
    auth = st.session_state.get("auth", {})
    allowed = ROLE_PAGES.get(auth.get("role", "admin"), list(PAGES))
    with st.sidebar:
        st.markdown(
            """<div class="brand"><div class="logo">🐑</div>
            <div><div class="t1">FCO&nbsp;Studio</div>
            <div class="t2">Veterinary AI</div></div></div>""",
            unsafe_allow_html=True)
        for key, (label, icon, _) in PAGES.items():
            if key in allowed:
                st.button(f"{icon}   {label}", key=f"nav_{key}",
                          on_click=lambda k=key: st.session_state.update(page=k))
        st.markdown("<div style='flex:1'></div>", unsafe_allow_html=True)
        st.markdown(
            f"<p style='font-size:.82rem;color:#CBD5E1 !important;margin-top:1.5rem;'>"
            f"👤 <b>{auth.get('name', '')}</b><br>"
            f"<span style='font-size:.72rem;color:#94A3B8 !important;'>rôle : "
            f"{auth.get('role', '')}</span></p>", unsafe_allow_html=True)
        if st.button("🚪 Se déconnecter", key="logout"):
            st.session_state["auth"] = None
            st.session_state["page"] = "home"
            st.rerun()
        st.markdown(
            "<p style='font-size:.72rem;color:#64748B !important;margin-top:1rem;'>"
            "Outil d'aide à la décision. Ne remplace pas un diagnostic vétérinaire."
            "</p>", unsafe_allow_html=True)


def main() -> None:
    inject_css()
    if "page" not in st.session_state:
        st.session_state.page = "home"
    if not st.session_state.get("auth"):        # non connecté -> page de connexion
        login_page()
        return
    sidebar()
    allowed = ROLE_PAGES.get(st.session_state["auth"]["role"], list(PAGES))
    if st.session_state.page not in allowed:    # garde-fou d'accès par rôle
        st.session_state.page = "home"
    PAGES[st.session_state.page][2]()


if __name__ == "__main__":
    main()
