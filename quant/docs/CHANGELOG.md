# Changelog

## 0.5.0 — 2026-11-05 (External Bot Analysis & Optimization Lab)

Moteur inchangé ; `research_code_hash` inchangé (`5e6a8f926021b343`). Détail : `EXTERNAL_LAB.md`, `REFERENCE_V370.md`,
`SECURITY_V05.md`, `VALIDATION_V05.md` ; contre-audit : `../../docs/CODEX_HANDOFF_V05.md`.
- **Importateur MT5** (`external_lab/`) :
  - formats : HTML (UTF-16), XLSX (bibliothèque standard, DOCTYPE refusé), CSV, ZIP borné ;
  - extraction : réglages, 41 paramètres, résumé MT5 (brut et lu), Orders, Deals ;
  - doublons et lignes illisibles listés, jamais devinés.
- **Reconstruction** :
  - ordres, deals, positions et trades distincts ;
  - appariement vérifié contre le profit MT5 (314/314 sur V3.70) ;
  - taille de contrat déduite des profits MT5.
- **Rapprochement** avec le résumé MT5 : 23 indicateurs, tolérance égale à l'arrondi du chiffre MT5.
- **Catalogue immuable** `external/` :
  - sources et simulations en création seule et lecture seule ;
  - `ato-external-sim/1` vérifié à chaque lecture ;
  - journal chaîné ;
  - idempotence ; 409 sur contenu contradictoire ;
  - groupes « même test » et « contradictoire » ;
  - isolé des runs du moteur.
- **Risk Collapse Analysis** :
  - épisode de drawdown maximal, pertes et lots ;
  - constats séparés des hypothèses ;
  - divergence entre période demandée et période observée.
- **Hypothèses de réduction du risque**, qualifiées `exact` / `approximation` / `non_simulable`.
- **Pont MT5 local en lecture seule**, sur autorisation du propriétaire : rapports du dossier du terminal listés et
  importés. Ni ordre, ni identifiant, ni `.ex5`.
- **Page React « Bot Analysis »** (`/bot-analysis`).
- **Sécurité** : `UPLOAD_PATHS` couvre les routes de téléversement (défaut corrigé : le vrai rapport de 637 Ko était
  refusé).
- **Tests** : `test_external_lab.py` (30, dont le cas réel V3.70 en fixture vérifiée par SHA-256) ; `SimulationView.spec`
  (4) ; `pages-tour` 52 ; `api-down` 4.

### Audit d'EA (même version, issu de `docs/knowledge/KB-001`)

Ajout hors couche `research/` : `research_code_hash` est inchangé (`5e6a8f926021b343`), donc la campagne v0.4.1 reste
valable ; le moteur est inchangé.
- **`ea_audit/`** : lecture d'un rapport MT5, HTML (UTF-16/UTF-8) ou CSV, en-têtes FR/EN.
  - Détection : positions empilées, renforcement contre la perte, lots croissants, martingale après perte, profil
    asymétrique.
  - Verdict `MARTINGALE` / `GRID` / `RISK_SIGNS` / `NO_SIGNATURE` / `INSUFFICIENT`.
  - Test de résistance : mouvement de prix qui viderait le compte à l'exposition maximale.
- **API** : `POST /api/v1/ea-reports/analyze` (sans stockage ; en-tête local obligatoire ; `.ex5` refusé, 415).
- **React** : page « Audit d'EA » (`/ea-audit`).
- **Tests** :
  - `test_ea_audit.py` (16) ;
  - `EaAuditView.spec.tsx` (3) ;
  - parcours `pages-tour` : 43 vérifications, dont l'envoi réel d'un rapport.
- **Base de connaissances** : `docs/knowledge/` (fiche KB-001 : vérification de la synthèse de recherche du
  propriétaire contre le code).

## 0.4.1 — 2026-11-05 (corrections des audits Codex V0.4.0 et contre-audit V0.3.1)

Moteur de backtest inchangé (`ENGINE_VERSION` = `backtest-engine/0.3.1`). Chaque défaut a d'abord été reproduit par un
test qui échouait sur une copie figée de la v0.4.0 (`research_campaign/results/repro_tests/`). Détail, campagne et
verdicts : `VALIDATION_V041.md`.

- **Décisions numériques** (B04-3) : valeur non finie, probabilité hors [0, 1], modèle non convergé ou exception →
  verdict `INVALID` ou avis « NE PAS TRADER ». « PRENDRE » est supprimé.
- **Études scellées** (I04-1) :
  - format `ato-study/2` : JSON canonique et SHA-256 ;
  - vérification stricte à chaque lecture (octets, identité, re-dérivation du verdict) ;
  - publication atomique sans écrasement, fichier en lecture seule ;
  - étude altérée → 409, liste marquée « refusée ».
- **Registre d'essais** : append-only, chaîné par empreintes, verrouillé. Les études supprimées comptent toujours.
- **Avis prospectif** (I04-4) :
  - réservé aux signaux *nouveaux* ;
  - modèle entraîné sur les seuls résultats disponibles à l'instant de décision ;
  - score « non calibré » ; refus hors domaine.
- **Temps** : `labels.available_time` = clôture de la bougie de sortie (contre-audit N9, côté recherche).
- **Configurations non modélisées refusées** (I04-3) : unité de temps, plage horaire, durée maximale, clôture de
  session, contrat.
- **Inférence** (B04-2, protocole H1) :
  - les signaux dont les résultats se chevauchent forment une unité ;
  - bootstrap circulaire par blocs sur les unités, longueur Politis–White ;
  - minimum de 100 unités hors échantillon ;
  - décision unilatérale au niveau α.
- **Essais multiples** (B04-1, protocole H2) : dépense sommable α_m = 0,05·6/(π²m²) ; famille = type de données +
  instrument + unité de temps.
- **Campagne pré-enregistrée** (I04-7) :
  - 13 850 réplications avant et 13 850 après, mêmes graines, plus des expériences complémentaires déclarées
    (écart 4) ;
  - contre-exemple de Codex (C1) : 17,6 % → 0,0 % de faux « avantages » (toutes les études y deviennent
    « insuffisantes ») ;
  - puissance à +0,20 R : 93,3 % → 95,7 % ;
  - aucun dépassement significatif de 5 % sur les 13 nuls pré-enregistrés valides ;
  - **échec** sur le nul complémentaire à résultats corrélés par des régimes d'un jour (N11b) : 8,0 % contre 3,8 % en
    v0.4.0 ;
  - **limites mesurées** : intervalle bootstrap trop étroit d'environ 10 à 20 % (taux observés ≈ 5 % pour un niveau
    nominal de 3 %) ; puissance nulle sur des signaux en rafales avec 120 jours d'historique.
- **API** :
  - robustesse sous `heavy_job`, 429 (I04-8) ;
  - collection des runs vérifiée (N1) ;
  - économie des trades recalculée (N2) ;
  - embargo négatif refusé (N3) ;
  - lignes séparées par CR comptées (N4) ;
  - attestation de politique par requête (N5) ;
  - empreinte de validation (N6) ;
  - preuve brute contrôlée (N7) ;
  - provenance persistée renvoyée (N8).
- **Express** : garde Host/Origin/`X-ATO-Request` sur toutes les mutations (N10).
- **Interface** :
  - résultats marqués « expérimental » ; « avantage démontré » devient « indice d'avantage (expérimental) » ;
  - scores non calibrés ; unités indépendantes affichées ;
  - runs refusés signalés ; Monte Carlo requalifié en mesure conditionnelle (I04-6).
- **Retiré** : les affirmations « 1 faux positif sur 60 », « 19/30 », « 30/30 » (voir `REPRODUCTION_V04.md`).
- **Tests** : 264 tests Python (dont 32 nouveaux) ; nouveaux tests JS `localGuard.spec.ts` (5) et
  `StudyView.spec.tsx` (4).

## 0.4.0 — 2026-11-04 (Validation hors échantillon)

Couche `research/` (aucun changement du moteur de backtest : `ENGINE_VERSION` reste `backtest-engine/0.3.1`,
les runs existants restent reproductibles).
- **Étiquetage de chaque signal** (`research/labels.py`, triple barrière) avec les conventions d'exécution du moteur ;
  test : pour chaque trade du moteur, R étiqueté = `r_multiple` (écart max 2e-16, mêmes motifs de sortie).
- **Variables explicatives causales** (`research/features.py`, `price-action-v1`, 12 variables sans unité) ; test :
  réécrire le futur ne change pas une ligne passée.
- **Évaluation walk-forward purgée** (`research/study.py`) : entraînement ancré, purge des étiquettes chevauchant la
  fenêtre de test, seuil du filtre choisi sur validation interne, régression logistique L2 (numpy, sans nouvelle
  dépendance), AUC, Brier, calibration, bootstrap par blocs, correction de Bonferroni par nombre d'études sur un même jeu.
- **Verdict conservateur** : `EDGE` seulement si la borne basse de l'espérance filtrée hors échantillon est > 0 avec
  ≥ 100 signaux ; avis sur le dernier signal forcé à « NE PAS TRADER » sans avantage démontré. Mesuré : 1 faux positif
  sur 60 jeux de bruit ; avantage faible détecté 19/30, moyen 30/30.
- **Robustesse d'un run** (`research/robustness.py`) : intervalles bootstrap de l'espérance et du win rate, Monte Carlo
  de l'ordre des trades (distribution du drawdown, probabilité d'atteindre la limite du Risk Guardian).
- API : `POST/GET /api/v1/research/edge-studies`, `GET /api/v1/research/edge-studies/{id}`,
  `GET /api/v1/backtests/{run_id}/robustness` (allowlist de routes mise à jour ; garde des mutations inchangée).
- React : page **Validation** (`/research`), onglet **Robustesse** dans Backtests ; refonte de toutes les pages
  (aucun chiffre inventé, plus de formulaire d'identifiant MT5) ; parcours `e2e/pages-tour.mjs` (38 vérifications).
- Tests : `tests/test_research.py` (16) ; 232 tests Python au total.

## 0.3.1 — 2026-11-04 (Financial Integrity Hardening — suite à l'audit Codex V0.3)

Chaque défaut a été reproduit (sonde Codex ou test) avant correction ; régressions dans `tests/test_codex_v03_regressions.py`,
sondes adaptées dans `scripts/codex_probes_v031.py`, preuves d'origine dans `../docs/audits/codex-v03-2026-11-04/`.

### Bloquants
- **B1** `.gitignore` : `data/` non ancré ignorait le package `ai_trader_optimizer/data/` → règles ancrées (`/data/`,
  `/quant/data/`) ; journaux de preuves d'audit ré-inclus. Vérifié par `git check-ignore` et par un export propre installé et testé.
- **B2** Intégrité des runs : format `ato-run/1` (sérialisation canonique, `result_hash` SHA-256 sur trades + décisions +
  equity + métriques, `integrity.json`, `run_digest` indexé), vérification des octets réellement lus, recalcul des métriques,
  refus de toute réécriture d'un run publié, reproduction séparant `deterministic` et `artifacts_intact`.
- **B3** Frontière IS/OOS : `trade_end` borne les **clôtures**, `trade_start` les **ouvertures** ; plus aucun double comptage.

### Importants
- **I1** Types numériques stricts (NaN, infini, chaînes, booléens refusés ; bornes opérationnelles) ; garde-fous sur les
  intermédiaires (taille, risque, P&L, capital).
- **I2** Politique de risque `research` (explicite) / `supervised` (imposée côté serveur).
- **I3** Limite de corps avant parsing multipart, lignes bornées, concurrence (429), quota (507), parsing hors boucle async.
- **I4** Garde Host / Origin / Sec-Fetch-Site / en-tête `X-ATO-Request` sur les mutations.
- **I5** Symbole normalisé avant identité, stockage, comparaison (contrat inclus).
- **I6** Fractions de seconde refusées ; empreinte exacte (`repr`) ; stockage = octets empreintés.
- **I7** Identité du contenu séparée de la provenance ; déclaration contradictoire refusée (409) ; historique des déclarations.
- **I8** Franchissements à l'ouverture traités avant les touches intrabougie (`TP_GAP`, `SL_GAP`).
- **I9** Publication atomique (staging, verrou, renommage), idempotence sans réécriture, reprise après interruption.
- **I10** Relais `/api/v1` en production (`pnpm start`) testé avec la vraie API.

### Mineurs
- **M1** État React réinitialisé à chaque run ; **M2** devise par résumé de run ; **M3** fuseaux invalides et périodes
  inversées/vides → 422 ; **M4** MAE/MFE = bornes inférieures prouvées (`excursion_basis = lower_bound_ohlc`).

### Environnement
- `requirements.lock` (versions exactes, Python 3.12.14) ; `.env.example`.

## 0.3.0 — 2026-11-03 (intégration API + React)

### Ajouté
- **API HTTP v1** `ai_trader_optimizer.api` (FastAPI 0.162, uvicorn) : santé, datasets (liste, détail, démo synthétique,
  import CSV/MT5 limité en taille), stratégies, configuration par défaut, backtests (exécution, liste, détail, trades,
  décisions, courbe de capital, reproduction, exports en liste blanche). Aucune route d'ordre. `pnpm quant:api`.
- **Page React « Backtests » branchée sur le moteur** (`client/pages/Backtest.tsx` + `client/components/backtest/*`,
  `client/lib/quantApi.ts`, `shared/quant-api.ts`) : sélection / import / démo, stratégie et paramètres bornés, capital,
  coûts, période, lancement, indicateurs, courbe, journal, refus, traçabilité, exports, reproduction.
- Proxy Vite `/api/v1` → `127.0.0.1:8765` ; Express contourné pour ces routes.
- Tests : 27 tests API (pytest), 5 tests d'intégration client TS ↔ Vite ↔ FastAPI ↔ moteur (vitest), parcours
  navigateur réel Chrome (`e2e/backtest-flow.mjs`, 16 + 3 vérifications).

### Corrigé
- Catalogue : identifiants validés (16 hex) avant toute construction de chemin (défense contre la traversée).
- Frontend (préexistant) : 8 vraies erreurs TypeScript et 66 symboles inutilisés → `pnpm typecheck` = 0 erreur en
  mode strict. Dont : notifications jamais affichées (état `useToast` non partagé) ; import de réglages qui annonçait
  un succès sans rien appliquer ; `MarketOverview` affichait `price`/`trend` inexistants ; mot de passe MT5 conservé
  inutilement en mémoire (`connectionConfig`).
- Port par défaut de l'API : 8765 (le 8000 était occupé ici par Docker sur toutes les interfaces).

## 0.2.1 — 2026-11-03 (consolidation)

### Corrigé (défauts reproduits par sonde sur 0.2.0 — voir `../../docs/CODEX_REVIEW_HANDOFF.md`)
- Stop plus proche que spread + glissement : perte réelle 2,2× le risque prévu → refus `STOP_INSIDE_SPREAD`.
- Contrat incohérent avec le symbole des données (EURUSD dimensionné avec le contrat or : 50 lots) →
  `CONTRACT_SYMBOL_MISMATCH` ; devise de cotation contrôlée contre le symbole d'une paire.
- `run_backtest(strategy=…)` contournait les contrôles de la spec (brouillon, martingale, tiers) → refusé.
- `save_run` écrasait un run de même identifiant aux résultats différents → refus (`ReproducibilityError`) ;
  `run_id` et manifeste incluent l'empreinte du code (`code_hash`) ; « Reproduire » signale un changement de code.
- Libellé du rejeu : affiche le côté de prix réel des données (BID ou MID).

### Ajouté
- 19 tests de non-régression (`test_regressions_v021.py` + 1 dans `test_risk.py`), dont identités comptables
  (signe SELL, BID/ASK, mid) sur 8 runs. Total : 115 tests.

## 0.2.0 — 2026-11-03

### Corrigé (voir `AUDIT_INITIAL.md`)
- D1 : la limite de perte journalière pouvait être dépassée (risque du trade envisagé ignoré). Idem drawdown.
- D2 : règles cachées (arrêt après premier gain, 2 pertes/jour) rendues explicites et configurables.
- D3 : chaque signal BUY/SELL est journalisé avec sa décision, ses raisons de refus et les valeurs d'indicateurs connues.
- D4 : ATR Wilder disponible ; la méthode utilisée est nommée.
- D5 : equity mark-to-market et drawdown MTM ajoutés.
- D6 : runs liés à une version de données, de stratégie et de configuration (manifeste, empreintes).
- D7 : métriques complétées ; métriques non calculables marquées « indisponible » avec la raison.
- D8 : nouvelle config `BacktestConfig` (l'ancien `TestConfig` reste dans `core.py` figé).
- D9 : contrat marqué « hypothèse » ; refus si devise de cotation ≠ devise du compte.
- D10 : moteur ~4× plus rapide (1 an de M1 en ~4 s).
- D11 : sessions et jour de trading dans un fuseau configurable.
- Conversion des prix exacte au dernier bit (empreintes stables).
- Streamlit limité à `localhost`.

### Ajouté
- Modules `data`, `features`, `strategies`, `risk`, `backtest`, `analytics`, `storage`, `services`, `ai`, `execution`, `ui`.
- Import d'exports MetaTrader 5 ; fuseau déclaré ; rapport de qualité ; classification des trous.
- Rééchantillonnage M1→M15 et alignement causal (préparation MACD M15/M1).
- Spécifications YAML : baseline 1.0.0, brouillon MACD du trader pilote, dossier tiers.
- Sorties : TP, SL, SL_GAP, TIME_EXIT, SESSION_END, END_OF_DATA.
- UI : Dashboard, Market Data, Strategy Lab (paramètres bornés, comparaison de variantes IS/OOS), Backtesting
  (exports CSV/JSON, reproduction), Trade Journal (rejeu graphique), Risk Management, Settings.
- 89 nouveaux tests (96 au total) ; ruff.
- Documentation : architecture, décisions, limites, feuille de route, rapport de tests, prompt de revue Codex, `AGENTS.md`.

## 0.1.0
Prototype initial : Streamlit, import CSV M1, EMA/ATR, stratégie illustrative, simulateur, 7 tests.
