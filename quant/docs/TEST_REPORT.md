# Rapport de tests — v0.3.1 (2026-11-04)

Environnement : macOS, Python 3.12.14 (`.venv`), pandas 2.3.3, numpy 2.5.4, streamlit 1.66.1, pydantic 2.14.2,
pytest 9.2.0, ruff 0.17.3, fastapi 0.162.0, uvicorn 0.54.0, httpx 0.28.1. Node 26.8.1, pnpm 10.14.0, vitest 3.2.4, Chrome (headless).

Commande : `python -m pytest -q` → **215 passed, 0 failed** (≈ 35 s). `ruff check src tests app.py scripts` → aucune erreur.

| Fichier | Tests | Ce qui est prouvé |
|---|---|---|
| `test_core.py` (v0.1, inchangé) | 7 | Comportement historique du moteur figé |
| `test_engine.py` | 20 | P&L calculé à la main (BUY TP, SELL SL, coûts détaillés) ; SL prioritaire ; gap → sortie à l'ouverture, perte > risque prévu ; fin de données ; pas d'entrée à travers un trou ; pas de ré-entrée dans la bougie de sortie ; une position à la fois ; signal de la dernière bougie jamais exécuté ; sortie temps et fin de session ; fenêtre de test ; marché sans signal ⇒ 0 trade et métriques « indisponibles » ; **causalité des signaux (préfixes)** ; **perturber les prix futurs ne change aucune décision passée** ; reproductibilité (run_id, result_hash) ; manifeste ; **équivalence exacte avec le moteur v0.1** ; journal de décisions complet ; refus d'un timeframe incompatible |
| `test_risk.py` | 18 | Formule de sizing (dépend du capital, du stop, de la taille de contrat) ; arrondi vers le bas, plafond max_lot ; lot minimal ; contrat inconnu / devise incompatible ⇒ 0 trade ; limite journalière avec risque prévu ; démonstration du défaut v0.1 ; arrêt au drawdown max ; pertes consécutives ; trades et pertes par jour ; devise de cotation ≠ compte ; réinitialisation journalière dans un fuseau donné ; horaires dans le fuseau de la stratégie ; martingale refusée ; risque jamais croissant après pertes ; données/stop invalides ; erreur interne ⇒ refus |
| `test_data_validation.py` | 19 | Colonnes manquantes ; doublons (lignes signalées) ; non trié refusé (pas trié) ; prix manquants/non numériques ; OHLC incohérent, prix ≤ 0 ; fuseau absent / déclaré / inconnu ; offsets explicites à travers un changement d'heure ; heure ambiguë et inexistante (DST) refusées ; fuseau mixte ; trous détectés, classés, **non comblés** ; horodatages désalignés ; format MT5 ; timeframe attendu ; empreinte déterministe et sensible ; import exact au dernier bit ; fichiers vides/illisibles |
| `test_indicators_resample.py` | 8 | EMA, SMA, True Range, ATR Wilder et SMA, MACD contre valeurs calculées à la main ; couleur de bougie ; **M15 visible seulement après clôture** ; bougie M15 incomplète non exposée |
| `test_metrics_storage_safety.py` | 7 | Métriques sur trades connus (PF, espérance, payoff, DD, coûts) ; PF indisponible sans perte ; résultats par période ; catalogue aller-retour + **détection d'altération** ; aucune trace `order_send` / `MetaTrader5` dans les sources ; adaptateurs démo/réel refusent ; walk-forward sans chevauchement ni fuite |
| `test_regressions_v021.py` | 18 | Stop dans le spread refusé / stop juste au-delà borné ; contrat ≠ symbole refusé, contrat correct ⇒ taille saine ; suffixes broker ; stratégie injectée (brouillon, tiers, martingale, spec différente) refusée ; catalogue n'écrase jamais des résultats différents ; empreinte de code ; identités comptables BID et MID (8 runs) |
| `test_api.py` | 27 | API v1 : simulation seule, **liste blanche exacte des routes** (aucune route d'ordre), CORS refuse `*` et les origines non locales ; démo déterministe et étiquetée ; import valide / refus global sans stockage / fichier « synthétique » déclaré historique refusé / limite de taille 413 / extension 415 / champs invalides ; stratégies ; le backtest de l'API = `run_backtest` direct (même run_id, même result_hash) ; métriques = trades = courbe = décisions ; idempotence et reproduction ; règles de risque respectées ; 8 paramètres invalides → 422 sans résultat stocké ; stratégie/dataset inconnus ou non exécutables ; contrat inconnu ⇒ 0 trade ; exports + traversée de chemin ; erreur interne ⇒ 500 générique |
| `test_codex_v03_regressions.py` | 73 | Régressions de l'audit Codex V0.3 : B2 (métriques, equity, trades, décisions, manifeste altérés ; falsification cohérente des fichiers + empreintes ; incohérence sémantique ; réécriture refusée ; idempotence sans réécriture ; reproduction déterministe vs intégrité ; empreinte couvrant métriques/equity), B3 (exemple Codex 11 bougies coupure 12:05, coupure non alignée, position ouverte à la frontière, segments disjoints), I1 (11 corps JSON invalides dont `1e309`, chaînes, booléens ; modèles ; garde du Guardian et du moteur), I2 (mode recherche explicite, mode supervisé imposé), I3 (aucun octet lu si Content-Length excessif, flux coupé, lignes, 429, 507), I4 (5 requêtes étrangères refusées sans écriture, origine locale acceptée), I5 (5 orthographes de symbole), I6 (fractions de seconde, écart 1e-8, aller-retour exact), I7 (provenance contradictoire 409, historique), I8 (BUY/SELL, gap favorable/défavorable, ambigu), I9 (interruption, staging résiduel, 6 écrivains concurrents), M2, M3 (6 entrées temporelles invalides), M4 |
| `test_app_ui.py` | 18 | L'app démarre ; les 7 écrans s'affichent sans exception, laboratoire vide et rempli ; un backtest lancé depuis le formulaire est enregistré et signalé « synthétique » ; le bouton « Reproduire » confirme des résultats identiques ; contrat inconnu annoncé sur l'écran risque |

## Frontend / intégration (racine du dépôt)
`pnpm test` → **30 passed** (7 fichiers) ; `pnpm typecheck` → **0 erreur** (mode strict) ; `pnpm build` → OK.

| Fichier | Tests | Ce qui est prouvé |
|---|---|---|
| `client/lib/quantApi.integration.spec.ts` | 6 | Lance la **vraie API Python** et un **vrai serveur Vite** : client TS → proxy → FastAPI → moteur ; paramètres utilisateur transmis ; trades = métriques = courbe ; risque par trade ≤ budget ; résultats persistés identiques ; reproduction et idempotence ; paramètres invalides → 422 sans résultat ; CSV corrompu refusé en entier ; aucune route d'ordre dans l'OpenAPI ; routes Express encore servies |
| `server/quantProxy.spec.ts` | 4 | Relais de production : corps POST, chemin, en-têtes transmis malgré `express.json()` ; routes Express intactes ; 502 si Python absent ; cible non locale refusée (preuve : monté après `express.json`, le test échoue) |
| `client/lib/format.spec.ts` | 3 | Une métrique absente s'affiche « indisponible », jamais 0 ; signe et valeur conservés ; UTC |
| `client/hooks/use-toast.spec.ts` | 2 | Store de notifications partagé (défaut corrigé) et auto-fermeture |
| `server/settings.spec.ts` | 3 | Secrets jamais écrits ni renvoyés ; CORS local |
| `shared/instruments.spec.ts` | 7 | P&L du simulateur pédagogique |
| `client/lib/utils.spec.ts` | 5 | Template |

Preuve que le contournement d'Express est nécessaire : sans lui, 2 des 5 tests d'intégration échouent (POST bloqués).

**Parcours navigateur réel** (`node e2e/backtest-flow.mjs`, Chrome headless piloté par le protocole DevTools) :
**21/21** — état vide explicite, statut moteur issu de l'API, clic « Générer la démo synthétique », clic « Lancer
le backtest », avertissement synthétique, KPI trades / P&L / win rate / profit factor / drawdown **identiques aux
métriques de l'API**, journal rendu, courbe rendue, empreinte affichée = API, « Reproduire » → identique, aucune
exception navigateur ; v0.3.1 : verdict « artefacts intacts · recalcul déterministe », politique « mode recherche »,
second run sans héritage d'état (M1 ; preuve : sans `key` par run, 20/21), devise dans la liste (M2). `--api-down` : **3/3** — état hors ligne explicite, aucun chiffre, bouton désactivé.

**Production locale** (`pnpm build && node e2e/production-smoke.mjs`) : **9/9** — SPA, santé relayée, démo, backtest,
résultats, reproduction, mutation d'origine étrangère 403, mutation sans en-tête 403, routes Express.

**Sondes Codex adaptées** (`scripts/codex_probes_v031.py`) : **14/14** défauts non reproductibles ; sonde financière
d'origine `financial_probe.py` (inchangée) : **12/12**.

## Vérifications manuelles effectuées
- `pnpm quant:api` + `pnpm dev` : `/api/v1/health` via Vite → `ok` ; API à l'écoute sur `127.0.0.1:8765` uniquement ;
  `/backtest` → HTTP 200.
- `streamlit run app.py` en mode headless : `/_stcore/health` → `ok`, page `/backtesting` → HTTP 200.
- `python scripts/demo_cli.py --legacy-rules` → 12 trades, −7,00 USD : identique au v0.1.
- Banc d'essai 1 an de M1 synthétique (375 840 bougies) : validation 3,4 s, backtest 3,9 s, sauvegarde 9,0 s, chargement 3,6 s.

## Non testé
- Upload de fichier via le widget Streamlit (la fonction d'import sous-jacente est testée).
- Clic sur « Importer un CSV » dans le navigateur (l'import est testé via l'API et le client TS).
- Navigateurs autres que Chrome ; affichage mobile.
- Données réelles de courtier : aucune n'était disponible ; tous les tests utilisent des données fictives.
- Comparaison avec le Strategy Tester MT5.
