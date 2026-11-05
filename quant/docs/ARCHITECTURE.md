# Architecture — AI Trader Optimizer (à jour v0.5.0)

> Les sections ci-dessous décrivent le socle v0.3.1 (intégrité, temps, risque, garde, production), toujours en
> vigueur. Couches ajoutées depuis : `research/` (v0.4, voir `VALIDATION.md` et `VALIDATION_V041.md`),
> `ea_audit/` et `external_lab/` (v0.5, voir `EXTERNAL_LAB.md` et `SECURITY_V05.md`).

> Plan de migration : `../../docs/project/CONSOLIDATION_AUDIT.md`. Audit indépendant : `../../docs/audits/codex-v03-2026-11-04/`.

## Intégrité des runs (format `ato-run/1`, `storage/integrity.py`)

| Élément | Définition |
|---|---|
| Sérialisation canonique | CSV : colonnes dans l'ordre du moteur, `\n`, RFC 4180 ; floats `repr` (aller-retour exact) ; booléens `true`/`false` ; horodatages ISO-8601 UTC ; manquant = champ vide ; valeur non finie **refusée**. JSON : clés triées, séparateurs compacts, `allow_nan=False`. |
| `result_hash` (64 hex) | SHA-256 des octets canoniques de `trades.csv`, `decisions.csv`, equity (CSV non compressé), `metrics.json`, dans cet ordre, chacun préfixé par nom et longueur. Identifie le **résultat du calcul**. |
| `integrity.json` | SHA-256 de chaque fichier stocké (manifeste inclus) + `run_digest` ; `run_digest` est aussi écrit dans l'index SQLite à la publication. |
| Lecture | Chaque artefact est lu **une fois** ; ce sont ces octets qui sont vérifiés (empreintes, `run_digest`, index, `result_hash`) puis parsés ; les métriques sont **recalculées** depuis journal + courbe + décisions et comparées (`check_consistency`). Tout écart → `CorruptRunError` → HTTP 409, rien n'est servi. Les exports servent les octets vérifiés. |
| Publication | Préparation complète dans `runs/.staging/<id>-<aléa>/`, `fsync`, relecture vérifiée, **renommage atomique** vers `runs/<id>/`, puis ligne d'index (INSERT, jamais REPLACE). Verrou exclusif par run (`fcntl.flock`). Même run + même résultat = idempotent sans réécriture ; résultat différent = refus ; run existant corrompu = jamais écrasé. |
| Reproduction | `artifacts_intact` (les fichiers passent la vérification) **et** `deterministic` (un nouveau calcul donne le même `result_hash` que celui des octets vérifiés) ; `identical` = les deux. |
| Limite | Détection de **corruption**, pas preuve d'**authenticité** : qui peut réécrire fichiers, `integrity.json` et index peut forger un run cohérent (il faudrait une signature). |

## Temps et fenêtres d'évaluation (B3)

- Bougie : `timestamp` = ouverture *t* ; clôture = *t + timeframe* ; ses informations (et un signal calculé dessus) sont disponibles à la clôture.
- `trade_end = E` : seules les bougies dont la **clôture ≤ E** sont chargées ; une position encore ouverte est fermée à la clôture de la dernière de ces bougies (`END_OF_DATA`).
- `trade_start = S` : les ordres ne sont exécutés qu'aux **ouvertures ≥ S** et la courbe évaluée commence là ; les bougies antérieures ne servent qu'à l'échauffement des indicateurs (observations, jamais résultats).
- Découpage IS/OOS (`chronological_split`, `compare_variants`) : IS avec `trade_end = C`, OOS avec `trade_start = C` → aucune bougie ne fournit de résultat aux deux segments ; une coupure non alignée est arrondie à l'ouverture suivante pour l'OOS. Le manifeste enregistre `evaluation_window` (première ouverture évaluée, dernière clôture évaluée).

## Politique de risque (I2)

`ATO_RISK_POLICY` (choisie par qui lance l'API, jamais par l'appelant) : **`research`** (défaut) — limites et contrat
sont des hypothèses modifiables, chaque résultat l'indique (`manifest.risk_policy.enforced = false`) ; **`supervised`** —
le profil enregistré et le contrat sont imposés, une requête ne peut être que plus stricte (sinon 403). Prérequis de tout
futur mode supervisé ou d'exécution.

## Garde des requêtes locales (I3, I4 — `api/security.py`)

Middleware le plus externe, avant tout parsing : `Host` de bouclage obligatoire (421, anti DNS rebinding) ; pour les
mutations, `Sec-Fetch-Site: cross-site` refusé, `Origin` présent ⇒ origine de bouclage ou listée, en-tête `X-ATO-Request: 1`
obligatoire (403) ; `Content-Length` > limite refusé sans lire le corps, corps sans longueur compté et coupé à la limite
(413). Puis : nombre de lignes borné avant pandas (`ATO_MAX_ROWS`), traitements lourds limités (`ATO_MAX_CONCURRENT_JOBS`
→ 429), quota disque (`ATO_MAX_STORAGE_MB` → 507), parsing hors de la boucle async.

## Topologie de production locale supportée (I10)

```
pnpm build && pnpm quant:api && pnpm start
navigateur → Express 127.0.0.1:PORT ─ /api/v1/* relayé tel quel (server/quantProxy.ts, monté AVANT express.json)
                                     │                         → FastAPI 127.0.0.1:8765 (QUANT_API_URL, bouclage imposé)
                                     ├ /api/* (autres) → routes Express
                                     └ reste → SPA construit
```
Netlify ne peut pas faire tourner le moteur Python : il ne sert qu'une **vitrine statique en lecture seule**, faite
de réponses pré-calculées (`../../docs/project/DEPLOYMENT.md`).

> Plan de migration et diagnostic du workspace : `../../docs/project/CONSOLIDATION_AUDIT.md`.

**Aucun chemin d'exécution vers un courtier** n'existe dans cette version.

## Système (v0.3)

```
Navigateur ── http://localhost:8080 ──► Vite (dev) ─┬─ /api/v1/*  ──proxy──► FastAPI 127.0.0.1:8765
  React (client/)                                   │                     quant/src/ai_trader_optimizer/api
  page /backtest = moteur Python                    │                         │ services.py uniquement
                                                    │                         ▼
                                                    │        data · strategies · backtest · risk · analytics
                                                    │                         │
                                                    │                         ▼
                                                    │        storage/catalog.py (SQLite + fichiers) = source de vérité
                                                    └─ /api/* (autres) ──► Express (mocks + /api/settings), SPA
Console de recherche : Streamlit (quant/app.py) ── appelle les mêmes services Python (pas de doublon de calcul).
```

Règles de frontière :
* **React affiche, Python calcule.** Aucun calcul financier en TypeScript (`client/lib/format.ts` ne fait que formater ;
  une valeur absente s'affiche « indisponible », jamais 0).
* Le contrat est `shared/quant-api.ts` (types) + `client/lib/quantApi.ts` (unique client HTTP). Il est vérifié de bout
  en bout contre la vraie API par `client/lib/quantApi.integration.spec.ts`.
* L'API renvoie ce qui a été **persisté** (relu dans le catalogue après l'exécution), pas une copie en mémoire.
* Le plugin Vite n'envoie pas `/api/v1` à Express (son `express.json()` consommerait le corps des POST — prouvé par test).
* Express n'est pas retiré : seules `POST /api/settings` (Settings) et le service du SPA en production sont encore utiles ;
  `/api/analytics/*`, `/api/optimize*`, `/api/backtest*` ne sont appelées par aucune page (hooks `useBacktest`,
  `useOptimizer`, `useTrading` non utilisés).

### API v1 (`api/app.py`)

| Méthode | Route | Rôle |
|---|---|---|
| GET | `/api/v1/health` | versions, `code_hash`, `live_trading_enabled: false`, `order_routes: 0` |
| GET | `/api/v1/datasets`, `/api/v1/datasets/{id}` | catalogue, méta + rapport de qualité |
| POST | `/api/v1/datasets/demo` | jeu **synthétique** déterministe (graine, jours) |
| POST | `/api/v1/datasets/import` | multipart CSV/MT5 ; ≤ `ATO_MAX_UPLOAD_MB` (50) ; refus global → 422 + rapport |
| GET | `/api/v1/strategies` | specs + `runnable` + raisons |
| GET | `/api/v1/settings/defaults` | `BacktestConfig` par défaut (Settings + profil de risque enregistrés) |
| GET | `/api/v1/reference/rejection-reasons` | libellés FR des codes de refus |
| POST | `/api/v1/backtests` | `{dataset_id, strategy_key, config?, label?}` → `{run_id, manifest, metrics}` |
| GET | `/api/v1/backtests[/{run_id}[/trades\|/decisions\|/equity]]` | résultats persistés |
| POST | `/api/v1/backtests/{run_id}/reproduce` | relance depuis le manifeste, compare les empreintes |
| GET | `/api/v1/backtests/{run_id}/export/{name}` | liste blanche : trades.csv, decisions.csv, equity.csv.gz, metrics.json, manifest.json |

Erreurs : 404 (inconnu), 409 (run existant aux résultats différents), 413 (upload trop gros), 415 (extension),
422 (validation : bornes de paramètres, coûts négatifs, champ inconnu, stratégie non exécutable, données refusées),
500 générique sans détail interne. Identifiants = empreintes 16 hex (motif vérifié dans l'API **et** le catalogue).
CORS : liste explicite d'origines locales (`ATO_CORS_ORIGINS`), `*` refusé. Écoute `127.0.0.1` ; une autre adresse
exige `ATO_API_ALLOW_REMOTE=1` (pas d'authentification : outil local mono-utilisateur).

## Moteur quantitatif

Monolithe Python modulaire, local, sans microservice.

## Flux

```
CSV (standard / export MT5)                         strategies/*.yaml (specs versionnées)
      │ read_source (octets bruts, SHA-256)                   │ load_catalog (schéma pydantic)
      ▼                                                       ▼
data/validation.py ── refus global si erreur ──►  strategies/registry.py ─► Strategy.compute(bars)
      │ QualityReport (erreurs / avertissements / trous)      │  signal, reason, sl/tp distance, features
      ▼                                                       │  (ligne i = info connue à la CLÔTURE de i)
Dataset (bars UTC + DatasetMeta, dataset_id = empreinte)      │
      │                                                       ▼
      └──────────────► backtest/engine.py ◄──── risk/guardian.py (indépendant, fail-closed)
                         │  décision à l'ouverture de i+1 ; SL/TP intrabougie ; coûts
                         ▼
               BacktestResult : trades, decisions (toutes, avec raisons + features),
               equity (clôturée + MTM), metrics (analytics/metrics.py), manifest
                         │
                         ▼
               storage/catalog.py : SQLite lab.db + fichiers (raw / datasets / runs)
                         │
                         ▼
               ui/ (Streamlit) : Dashboard · Market Data · Strategy Lab · Backtesting ·
                                 Trade Journal · Risk Management · Settings
```

## Modules (`src/ai_trader_optimizer/`)

| Module | Rôle | Points clés |
|---|---|---|
| `safety.py` | Interrupteurs permanents | `LIVE_TRADING_ENABLED = False`, `DEMO_TRADING_ENABLED = False`, `DataKind` (synthétique / historique / compte démo) |
| `data/` | Market Data Manager | Validation fail-closed, fuseaux explicites ou déclarés (DST ambigu refusé), format MT5, trous classés jamais comblés, empreinte `dataset_id`, rééchantillonnage M1→M15 et alignement causal |
| `features/indicators.py` | Indicateurs causaux | EMA, SMA, True Range, ATR (Wilder ou SMA), MACD, couleur de bougie |
| `strategies/` | Strategy Engine | `StrategySpec` (schéma validé), `Strategy` (interface), registre YAML, refus des brouillons / martingales / tiers aux droits non clarifiés |
| `risk/guardian.py` | Risk Guardian | Sizing = f(capital, % risque, distance stop, contrat réel) ; limites jour / drawdown / pertes ; budget de risque prévu ; refus si contrat inconnu ; erreurs internes ⇒ refus |
| `backtest/` | Moteur | Une position, sans look-ahead, modèle BID/ASK à spread fixe, SL prioritaire, gaps, sorties temps / session / fin de données, journal de toutes les décisions, manifeste |
| `analytics/metrics.py` | Performance | P&L, win rate, PF, espérance (USD et R), DD clôturé et MTM, coûts, par période, métriques indisponibles expliquées |
| `storage/catalog.py` | Source de vérité locale | SQLite + fichiers immuables par convention, détection d'altération |
| `api/` | API HTTP v1 (FastAPI) | Enveloppes minces autour de `services.py` ; aucune route d'ordre ; validation par les modèles pydantic du domaine |
| `services.py` | Orchestration | Configs par défaut, exécution + sauvegarde, reproduction d'un run, comparaison de variantes IS/OOS |
| `ai/` | Futur module IA | Interfaces `FeatureExtractor`, `SignalScorer`, `ModelCard` ; splits chronologiques et walk-forward testés. Aucun modèle entraîné |
| `execution/adapters.py` | Adaptateurs | `SimulationAdapter` seulement ; `DemoAccountAdapter` / `LiveAccountAdapter` lèvent `ExecutionDisabledError` |
| `core.py` | **Référence v0.1 figée** | Non utilisée par l'app ; sert au test de non-régression |
| `research/` | Validation hors échantillon (v0.4, **expérimentale**) | Étiquetage triple barrière, variables causales, walk-forward purgé, filtre logistique, inférence par grappes (`inference.py`), registre d'essais chaîné (`registry.py`), études scellées `ato-study/2`. Figé par `research_code_hash` : ne change qu'à travers `research_campaign/` |
| `ea_audit/` | Audit d'EA (v0.5) | Lecture de rapports MT5 (HTML/CSV), signatures grille / martingale / stop-out, test de résistance ; `mt5_local.py` = pont **lecture seule** vers les dossiers du terminal MT5 local |
| `external_lab/` | Laboratoire de robots externes (v0.5) | `mt5_report.py` (HTML/XLSX/CSV/ZIP → grille → tableaux), `reconstruct.py` (positions, trades, rapprochement MT5, effondrement), `simulation.py` (enregistrement `ato-external-sim/1`), `catalog.py` (stockage immuable `external/`), `whatif.py` (hypothèses qualifiées) |

## Conventions temporelles

- `timestamp` = heure d'**ouverture** de la bougie, en UTC.
- Un signal sur la bougie *i* est connu à `timestamp[i] + timeframe` et exécuté à l'ouverture de *i+1*,
  uniquement si *i+1* suit immédiatement *i* (aucun trou).
- Une bougie de contexte (ex. M15) n'est visible qu'une fois **clôturée** (`available_at <= clôture de la bougie M1`).

## Séparation des données

| Niveau | Emplacement | Modifiable ? |
|---|---|---|
| Brut | `data/lab/raw/<sha256>.csv` | Non (octets d'origine) |
| Validé | `data/lab/datasets/<dataset_id>.csv.gz` | Non (empreinte vérifiée au chargement) |
| Dérivé | `data/lab/runs/<run_id>/` (trades, décisions, equity, métriques, manifeste) | Régénérable |

## Traçabilité et reproductibilité

`run_id = sha256(dataset_id, strategy key, spec_hash, paramètres, configuration complète, version moteur, code_hash)`.
Un run existant n'est jamais écrasé par un résultat différent (`ReproducibilityError` → HTTP 409).
`result_hash = sha256(trades, décisions)`. Le bouton « Reproduire » relance un run depuis son manifeste et compare
les empreintes ; il refuse si la spécification de stratégie a changé (il faut créer une nouvelle version).

## AI (préparé, non implémenté)

Ordre imposé : baseline déterministe → modèle simple (régression logistique / arbres) filtrant les signaux de la
baseline → comparaison sur mêmes données et mêmes coûts, validation walk-forward avec embargo, jeu de test final
jamais utilisé pour l'ajustement. Le modèle ne dimensionne pas les positions et ne contourne jamais le Risk Guardian.

## Exécution future (non implémentée)

Simulation → compte démo (V0.5, après validation humaine) → réel (absent ; validation humaine, technique et
réglementaire préalable). Les identifiants vivront hors du dépôt, dans un processus séparé.
