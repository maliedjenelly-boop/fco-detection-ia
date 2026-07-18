# Abonnements & paiement Stripe — FCO Studio

Documentation de la brique « Abonnements » de l'application (page `💳 Abonnements`).

---

## 1. Grille tarifaire

| Formule | Prix | Équivalent | Ratio | Cible |
|---|---|---|---|---|
| **Découverte** | Gratuit | — | — | Test sans engagement (5 analyses/mois) |
| **Éleveur** | **120 € / an** | 10 € / mois | 1× | Éleveur adhérent |
| **Laboratoire** | **600 € / an** | 50 € / mois | 5× | Laboratoires et cabinets vétérinaires |

### Pourquoi 120 € / an pour l'Éleveur ?
C'est **exactement le chiffre du modèle économique du mémoire** (120 €/adhérent/an).
Le prix affiché dans l'application alimente donc directement les projections de
chiffre d'affaires présentées en soutenance :

| Scénario | Adhérents × 120 €/an | Revenu récurrent |
|---|---|---|
| Prudent | 150 | 18 k€/an |
| Médian | 400 | 48 k€/an |
| Ambitieux | 900 | 108 k€/an |

> Le tarif **Laboratoire n'entre pas** dans ces projections : c'est un segment
> complémentaire. Le modifier ne remet en cause aucun chiffre du mémoire.

---

## 2. Choix technique : Stripe **Payment Links**

Trois intégrations étaient possibles ; c'est la solution **Payment Links** qui a été retenue.

| Solution | Clé secrète requise | Retenue |
|---|---|---|
| Page vitrine simulée | non | non — pas de vrai parcours de paiement |
| **Payment Links** | **non** | ✅ **oui** |
| Stripe Checkout (API + webhooks) | oui (`sk_...`) | non — trop lourd et risqué ici |

**Raison déterminante : le dépôt GitHub est public.** Les Payment Links sont de
simples URL `https://buy.stripe.com/...`, publiques par conception (elles sont
faites pour être diffusées). Aucune clé secrète Stripe n'existe donc dans le
projet, et il n'y a rien à fuiter.

---

## 3. Implémentation dans le code

Tout se trouve dans `corrige/03_app_streamlit.py` :

| Élément | Rôle |
|---|---|
| `PLANS` | Liste des formules (nom, montant, période, fonctionnalités) |
| `_stripe_link(tier)` | Lit l'URL dans `st.secrets["stripe"]`, renvoie `None` si absente |
| `page_abonnements()` | Rend les 3 cartes tarifaires et les boutons |
| CSS `.price`, `.pmo` | Styles des cartes de tarif |

**Comportement de repli :** si aucun lien n'est configuré, le bouton
« S'abonner » s'affiche **grisé et désactivé**, avec la mention
« Lien Stripe à configurer ». L'application reste donc parfaitement
fonctionnelle sans configuration Stripe.

Accès : la page est visible pour **tous les rôles** (`admin`, `laboratoire`, `eleveur`).

---

## 4. Configuration

Les URLs ne sont **jamais** écrites dans le code : elles sont injectées via les secrets.

### En local
Dans `corrige/.streamlit/secrets.toml` (fichier **ignoré par git**) :

```toml
[stripe]
eleveur = "https://buy.stripe.com/test_..."
laboratoire = "https://buy.stripe.com/test_..."
```

### En ligne (Streamlit Community Cloud)
**Settings → Secrets** → coller le même bloc `[stripe]`.

> ⚠️ Ne **pas** y mettre la section `[mysql]` : la base MySQL est en `localhost`,
> inaccessible depuis le cloud. L'application bascule automatiquement sur
> SQLite (`bdd/fco.db`) en ligne — ce repli est prévu dans `load_lab_from_db()`.

---

## 5. Recréer les liens depuis zéro

En cas de perte, les liens sont **toujours récupérables** dans le tableau de bord
Stripe (*Payments → Liens de paiement*). Pour les recréer :

1. [dashboard.stripe.com](https://dashboard.stripe.com) → activer le **Mode test**
2. **Catalogue de produits → + Ajouter un produit**
   - `FCO Studio — Éleveur` · **120 €** · **Récurrent** · **Annuel**
   - `FCO Studio — Laboratoire` · **600 €** · **Récurrent** · **Annuel**
3. Sur chaque tarif : menu **⋯ → Créer un lien de paiement**
4. Copier l'URL **`buy.stripe.com/...`**

> ❌ Ne pas confondre avec l'URL `dashboard.stripe.com/.../payment-links/plink_...`,
> qui est la page d'**administration** du lien : un client y verrait un écran de
> connexion Stripe, pas le paiement.

Le **mode test** ne nécessite **aucune activation de compte** (ni nom légal, ni RIB).

---

## 6. Démonstration en soutenance

Cliquer « S'abonner » ouvre une véritable page de paiement Stripe. Carte de test :

| Champ | Valeur |
|---|---|
| Numéro | `4242 4242 4242 4242` |
| Date d'expiration | n'importe quelle date **future** |
| CVC | 3 chiffres quelconques |

Le paiement aboutit et l'abonnement apparaît dans le dashboard Stripe,
**sans aucun mouvement d'argent réel**.

---

## 7. Passage en production (ultérieur)

1. Activer le compte Stripe (nom légal, adresse, compte bancaire)
2. Basculer en **mode production** et recréer les deux produits/liens
3. Remplacer les URLs dans les secrets (local **et** Streamlit Cloud)

**Aucune modification de code n'est nécessaire** : seules les URLs changent.

---

## 8. Règles de sécurité à respecter

- ❌ Ne **jamais** committer `corrige/.streamlit/secrets.toml` (déjà dans `.gitignore`)
- ❌ Ne **jamais** placer de clé secrète Stripe (`sk_live_...`, `sk_test_...`) dans le dépôt
- ✅ Seul `secrets.toml.example` est versionné, avec des valeurs fictives
- ✅ Les URLs `buy.stripe.com` ne sont pas des secrets, mais restent dans les secrets
  pour rester modifiables sans toucher au code
