# Feuille de route

Aucune date garantie. Chaque étape ne démarre qu'après validation de la précédente.

## v0.2 — livrée (2026-11-03)
Architecture modulaire, import validé (CSV/MT5), stratégies YAML versionnées, moteur avec journal de décisions,
Risk Guardian fail-closed, analytics, catalogue SQLite reproductible, UI Streamlit 7 écrans, 96 tests.

## v0.2.1 — livrée (2026-11-03)
Consolidation : 4 défauts du moteur corrigés, 8 défauts de l'app React/Express corrigés, plan d'unification.

## v0.3.0 — livrée (2026-11-03)
API FastAPI v1, page React « Backtests » branchée sur le moteur, tests d'intégration et parcours navigateur,
`pnpm typecheck` à 0 erreur.

## v0.3.1 — livrée (2026-11-04)
Durcissement après l'audit Codex V0.3 : 3 bloquants, 10 importants, 4 mineurs corrigés et prouvés (voir CHANGELOG).

## v0.4.0 — livrée (2026-11-04)
Validation hors échantillon (étiquetage de tous les signaux, walk-forward purgé, filtre logistique, bootstrap, verdict
corrigé des essais multiples), robustesse Monte Carlo d'un run, page React « Validation », refonte de l'interface.
Mode d'emploi : `VALIDATION.md`.

## v0.4.1 — livrée (2026-11-04)
Correctifs des audits Codex V0.4.0 et contre-audit V0.3.1 : décisions NaN/exception → refus, études scellées
(`ato-study/2`, empreinte, vérification à la lecture, publication atomique, registre d'essais chaîné), avis réservé aux
signaux nouveaux, inférence par grappes de chevauchement et dépense d'α sommable (après campagne pré-enregistrée
avant/après), N1–N8 et N10 du contre-audit. Résultats : `VALIDATION_V041.md`.

## v0.5.0 — livrée (2026-11-05)
External Bot Analysis & Optimization Lab : import vérifié des rapports MT5, catalogue immuable, Risk Collapse Analysis,
hypothèses qualifiées, pont MT5 local en lecture seule, page « Bot Analysis ». Cas de référence : `REFERENCE_V370.md`.

## v0.5.x — suite du laboratoire
1. Importer les rapports des deux autres EAs (« Gold Grid Strategy X V4.1 », « Gold EA ») et d'autres périodes de V3.70.
2. Comparaison de configurations : tableau de plusieurs simulations d'un même robot.
3. Si l'EA a un réglage équivalent, le rejouer dans le Strategy Tester et comparer, au lieu d'approximer.
4. Lecture des `.set` et des rapports d'optimisation, sur exemples réels.
5. Phase IA seulement après plusieurs robots et périodes, avec un protocole scellé (formulation / sélection /
   validation jamais consultée).

## v0.4.2 — restant avant tout usage sur données réelles
1. Contre-validation indépendante (Codex) de la campagne et des correctifs (`../../docs/CODEX_HANDOFF_V041.md`).
2. Rejeu portefeuille des signaux filtrés avec le moteur (une position, limites, dimensionnement) — audit I04-2.
3. Calibration des scores (sur validation, jamais sur test) ou maintien explicite de « non calibré » — I04-5.
4. Monte Carlo par blocs avec rejeu du sizing et du Risk Guardian — I04-6.
5. Heure de disponibilité dans le journal du moteur (contre-audit N9), avec nouvelle `ENGINE_VERSION`.
6. Expliquer l'effet filtré résiduel (+0,003 R) et l'AUC < 0,5 observés sous le nul exact.

## v0.5 — prochain incrément recommandé
0. Importer plusieurs mois d'historique M1 réel du courtier du trader et lancer une étude sur la baseline (point de départ).
1. **Entretien avec le trader pilote** puis stratégie MACD M15/M1 (voir ci-dessous, inchangé).
2. Migrer vers React : Market Data (rapport de qualité, trous), Trade Journal (rejeu graphique), Risk Management et
   Settings du moteur (`PUT /api/v1/settings/*`), puis Dashboard ; retirer les routes mock Express correspondantes.
3. Relais `/api/v1` dans le serveur de production Express (ou service statique par FastAPI) + test.
4. Commits propres selon le plan (`../../docs/CONSOLIDATION_AUDIT.md` §6), après votre accord.

## v0.3 (ancien plan, toujours valable pour la stratégie)
1. **Entretien avec le trader pilote** (`ENTRETIEN_TRADER.md`) → formaliser sa stratégie MACD M15/M1
   dans `strategies/pilot_trader/` (statut `draft` → `active`) avec exemples de trades valides / invalides.
2. Implémenter la stratégie MACD multi-timeframe (l'infrastructure `resample_ohlc` / `align_higher_timeframe`
   est testée) + tests « exemples annotés du trader ».
3. Spread variable issu de la colonne `<SPREAD>` MT5 (option du modèle d'exécution).
4. Rapport de walk-forward sur la baseline (pas d'optimisation : mesure de stabilité).
5. Revue indépendante Codex (`CODEX_REVIEW_PROMPT.md`) et intégration des corrections validées.
6. Mettre le prototype sous contrôle de version (dépôt dédié ou sous-dossier commité).

## v0.4 — rejouer sur ticks
Export ticks bid/ask ; comparaison avec le Strategy Tester MT5 dans des tolérances documentées.

## v0.5 — IA de classement des signaux
Modèle simple (logistique / arbres, puis XGBoost si utile) filtrant les signaux de la baseline, calibration,
walk-forward avec embargo, jeu de test final vierge, `ModelCard` versionnée, comparaison à la baseline à coûts égaux.
Optuna seulement sur train/validation.

## v0.6 — compte démo
Adaptateur démo dans un processus séparé (identifiants hors dépôt), approbation humaine, journal d'audit,
arrêt d'urgence, réconciliation des positions. Activation explicite.

## v1.0 — éventuel
Uniquement si résultats démo reproductibles, revue du risque et du cadre juridique. Le mode réel reste absent d'ici là.
