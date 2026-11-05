# Journal des décisions

Format : date · décision · raison · alternatives écartées.

## 2026-11-03 — v0.2

**D-01 · Développer dans `ai-trader-optimizer-v0.1/` sans renommer le dossier.** *(remplacée par D-20)*
Les chemins existants (README, commandes) restent valides. Le nom du dossier ne reflète plus la version (0.2.0
dans `pyproject.toml`) ; renommage possible plus tard, en une opération isolée.

**D-02 · Conserver `core.py` intact comme référence figée.**
Un test prouve que le nouveau moteur, avec les règles v0.1 rendues explicites (`LEGACY_V01_RISK`), reproduit
exactement ses trades (entrées, sorties, sens, lots, P&L à 0,01 près) sur deux jeux synthétiques. L'application
n'utilise plus `core.py`. Exclu de ruff pour rester identique à l'octet près.

**D-03 · Règles cachées de v0.1 rendues explicites et configurables.**
« Arrêt après le premier gain du jour » (`stop_after_daily_win`) et « 2 pertes max par jour »
(`max_losses_per_day`). Profil par défaut v0.2 : arrêt après gain **désactivé**, 2 pertes/jour conservé.

**D-04 · La limite de perte journalière inclut le risque du trade envisagé (par défaut).**
Corrige le dépassement mesuré (−0,49 % pour une limite de 0,30 %). Idem pour le drawdown maximal.
Désactivable pour reproduire v0.1.

**D-05 · ATR de la baseline 1.0.0 = moyenne simple du True Range (comme v0.1).**
Continuité des résultats. Paramètre `atr_method: wilder` disponible (ATR MT5/TradingView). Toute évolution du
défaut se fera via une nouvelle version de spec (1.1.0), jamais en modifiant 1.0.0.

**D-06 · Spécifications de stratégies en YAML + schéma pydantic (`extra="forbid"`).**
Lisible par le trader, validé strictement, bornes des paramètres déclarées dans le fichier. JSON Schema écarté
(pydantic le génère si besoin via `StrategySpec.model_json_schema()`).

**D-07 · Les stratégies ne fixent jamais la taille des positions.**
Le Risk Guardian calcule la taille ; la martingale/grille est refusée au chargement et par le Guardian ;
`allow_martingale` ne peut pas valoir `True` dans cette version. Le contrôle anti-martingale vérifie que le risque
prévu ≤ % fixe du capital **actuel** (une première version comparait au risque USD du trade précédent : rejetée car
elle refusait des trades légitimes selon l'arrondi des lots).

**D-08 · Fail-closed partout.** Contrat incomplet, devise de cotation ≠ devise du compte (aucune conversion
gérée), données avec trou avant l'entrée, stop invalide, exception dans le Guardian ⇒ refus journalisé.

**D-09 · Import : rejet global, jamais de correction silencieuse.**
Pas de tri automatique, pas de suppression de doublons, pas de comblement de trous. Horodatages sans fuseau
acceptés seulement si l'utilisateur **déclare** le fuseau ; heures ambiguës/inexistantes (DST) refusées.
Conversion décimale exacte (`float()`), car `pd.to_numeric` n'est pas exact au dernier bit (empreintes instables).

**D-10 · Stockage : SQLite (stdlib) + fichiers CSV/CSV.gz.** Pas de PostgreSQL ni de Parquet : inutile pour le
MVP, fichiers lisibles par le trader. Les runs sont identifiés de façon déterministe.

**D-11 · Pas de FastAPI ni de React pour la v0.2.** Streamlit appelle directement les moteurs ; une API n'apporte
pas de valeur tant qu'il n'y a qu'un utilisateur local. L'app React « Traider Pro » existante (racine du dépôt) est
une maquette à données aléatoires ; elle n'a pas été modifiée ni reliée.

**D-12 · Streamlit écoute uniquement sur `localhost`** (`.streamlit/config.toml`) : par défaut il exposait le
laboratoire sur le réseau (URL réseau et externe affichées au démarrage).

**D-13 · Aucun modèle IA entraîné.** Pas de dataset réel adapté ; interfaces et splits chronologiques préparés.

**D-14 · Séparation des stratégies par dossier** : `baseline/`, `pilot_trader/`, `third_party/`. Une stratégie
tierce avec `usage_rights: unclear` est refusée à l'exécution.

**D-16 · (0.2.1) Le Guardian refuse un stop situé dans le spread** plutôt que d'élargir silencieusement le stop :
élargir changerait la stratégie à l'insu de son auteur.

**D-17 · (0.2.1) Correspondance contrat ↔ données par préfixe de symbole** (`XAUUSD.m`, `XAUUSD-DEMO` acceptés ;
`GOLD` exige un contrat nommé `GOLD`). Simple et explicite ; un mauvais préfixe reste possible (question posée à Codex).

**D-18 · (0.2.1) Empreinte du code dans `run_id`.** Couvre `data`, `features`, `strategies`, `backtest`, `risk`,
`analytics`. Les versions de pandas/numpy ne sont pas incluses (à décider).

**D-19 · (0.2.1) Produit cible : React (`client/`) + API Python** ; Streamlit reste la console de recherche jusqu'à la
parité ; Express retiré à terme. Détails et plan : `../../docs/CONSOLIDATION_AUDIT.md`. FastAPI non ajouté sans accord.

**D-20 · (2026-11-03) Renommage des dossiers.** `ai-trader-optimizer-v0.1/` → `quant/` (moteur quantitatif ; la version
vit dans `pyproject.toml`, pas dans un nom de dossier) ; `ai-trader-optimizer/` → `archive/legacy-student-ai-trader-optimizer/`.
`client/`, `server/`, `shared/` inchangés : suivis par Git, modifiés localement par le propriétaire, référencés par Vite,
tsconfig, Netlify et `components.json`. Le nom du package (`ai_trader_optimizer`) et de la distribution ne changent pas.
Les deux dossiers renommés n'étaient pas suivis par Git : déplacement simple (`mv`), pas d'historique à préserver.
Le `.venv` a été recréé (il contient des chemins absolus).

**D-21 · (0.3) FastAPI pour l'API du moteur.** Réutilise les modèles pydantic existants (pas de schéma dupliqué),
OpenAPI gratuite ; starlette/uvicorn étaient déjà installés par Streamlit (installation à blanc vérifiée : aucune
mise à jour forcée). Synchrone : un backtest d'un an tient en ~4 s ; file d'attente reportée.

**D-22 · (0.3) L'API renvoie les résultats relus depuis le catalogue**, pas l'objet en mémoire : ce qui est affiché
est ce qui est stocké et exportable.

**D-23 · (0.3) React = interface principale, Streamlit = console de recherche.** La page Backtest React remplace
l'ancienne maquette (récupérable via Git). Les écrans sans équivalent React (Market Data détaillé, Strategy Lab,
Trade Journal, Risk, Settings du moteur) restent dans Streamlit jusqu'à leur migration.

**D-24 · (0.3) Proxy Vite + contournement d'Express pour `/api/v1`.** Le navigateur ne parle qu'à une origine
(pas de CORS en usage normal). Sans contournement, `express.json()` consomme le corps des POST (prouvé : test en échec).

**D-25 · (0.3) Port 8765** au lieu de 8000, occupé sur cette machine par Docker sur toutes les interfaces
(`localhost` aurait pu atteindre le conteneur via IPv6).

**D-26 · (0.3) Types TS du contrat écrits à la main + test d'intégration contre la vraie API** plutôt qu'un
générateur OpenAPI (nouvelle dépendance npm et modification du lockfile non souhaitées dans cet incrément).

**D-27 · (0.3.1) Empreinte de résultat = SHA-256 complet (64 hex)** sur la sérialisation canonique des artefacts ;
les identifiants de run/données restent des préfixes de 16 hex (adresses, pas preuves).

**D-28 · (0.3.1) Détection de corruption ≠ authenticité.** Pas de signature dans ce prototype local ; documenté.

**D-29 · (0.3.1) Bornes de fenêtre en temps de disponibilité** (`trade_end` sur clôtures, `trade_start` sur ouvertures).
Change la valeur attendue d'un ancien test (`test_outside_window_and_trade_end_truncate_data`) qui figeait la fuite.

**D-30 · (0.3.1) Mode recherche par défaut, mode supervisé imposé côté serveur** (`ATO_RISK_POLICY`), plutôt que
d'interdire toute exploration des hypothèses de risque en recherche.

**D-31 · (0.3.1) Protection des mutations par en-tête personnalisé + Origin/Host** plutôt qu'un jeton secret : outil
local mono-utilisateur, pas de secret à distribuer ; un processus local reste capable d'appeler l'API (pas d'authentification).

**D-32 · (0.3.1) TP franchi à l'ouverture exécuté au niveau du TP** (gap favorable non crédité, cohérent avec la
convention TP conservatrice existante) ; SL franchi à l'ouverture exécuté à l'ouverture (pire que le stop).

**D-33 · (0.3.1) MAE/MFE en bornes inférieures prouvées** plutôt que d'exposer des extrêmes potentiellement postérieurs
à la sortie.

**D-34 · (0.3.1) Provenance : première déclaration immuable**, déclarations de même nature ajoutées à l'historique,
déclaration contradictoire refusée. Le nom du fichier n'est qu'un garde-fou de saisie, pas une vérification.

**D-15 · Python 3.12 pour l'environnement local** : Python 3.15 (défaut Homebrew) n'a pas de roues pandas.
