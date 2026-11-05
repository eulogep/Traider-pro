# Handoff — revue indépendante par Codex (V0.3.1 « Financial Integrity Hardening », 2026-11-04)

Tu as audité la V0.3 (rapport et preuves copiés dans `docs/audits/codex-v03-2026-11-04/`, empreintes SHA-256
vérifiées). Cette passation décrit les corrections ; ta mission est de **les contester**. Contexte :
`quant/docs/ARCHITECTURE.md` (sections Intégrité, Temps, Politique de risque, Garde, Production),
`quant/docs/DECISIONS.md` D-27 à D-34, `quant/docs/KNOWN_LIMITATIONS.md`, `quant/AGENTS.md`.

**Règles inchangées :** aucun compte de trading, aucun ordre, aucun secret, aucun push, aucune opération Git destructive ;
rapport dans `docs/CODEX_REVIEW.md` (fichier:ligne, gravité, scénario, test proposé, certitude).

## 1. Reproduire

```bash
pnpm install --frozen-lockfile
cd quant && python3.12 -m venv .venv && .venv/bin/pip install -r requirements.lock && .venv/bin/pip install --no-deps -e . && cd ..
pnpm quant:test                                   # 215 passed
(cd quant && .venv/bin/ruff check --no-cache src tests app.py scripts)   # All checks passed
pnpm test                                         # 30 passed (7 fichiers ; lance la vraie API + Vite)
pnpm typecheck                                    # 0 erreur (strict inchangé)
pnpm build && node e2e/production-smoke.mjs       # 9/9 (pnpm start réel + vraie API)
node e2e/backtest-flow.mjs                        # 21/21 (Chrome headless)
node e2e/backtest-flow.mjs --api-down             # 3/3
(cd quant && .venv/bin/python scripts/codex_probes_v031.py)               # 14/14
```
Résultats obtenus par Claude : exactement ceux-ci, **dans le workspace et dans un export propre** des seuls fichiers
versionnables (239 fichiers, venv recréé depuis `requirements.lock`, `pnpm install --frozen-lockfile --offline`).
Ta sonde financière d'origine `financial_probe.py` (non modifiée) : 12/12. Ton `probes.py` d'origine (interfaces V0.3)
s'arrête dès la 1re sonde avec `KeyError: 'metrics'` : le run falsifié renvoie désormais 409 sans métriques.

## 2. Bilan PASS / FAIL par défaut

| Défaut | Avant (preuve Codex) | V0.3.1 | Correction | Preuve de non-régression |
|---|---|---|---|---|
| B1 | `data/` ignorait le package source | **PASS** | règles ancrées `/data/`, `/quant/data/` ; journaux d'audit ré-inclus | `git check-ignore` : non ignoré ; export propre installé + 215 tests ; sonde B1 |
| B2 | métriques falsifiées servies, `identical: true` ; réécriture acceptée | **PASS** | format `ato-run/1` : canonique, `result_hash` SHA-256 (trades+décisions+equity+métriques), `integrity.json`, `run_digest` indexé, lecture vérifiée, recalcul des métriques, publication immuable | 11 tests `test_b2_*` (5 artefacts altérés, falsification cohérente, incohérence sémantique, réécriture, idempotence, reproduction) ; sondes B2 |
| B3 | même trade +31,79 en IS et OOS | **PASS** | `trade_end` borne les clôtures, `trade_start` les ouvertures | `test_b3_*` (exemple 12:00–12:10 coupure 12:05, coupure non alignée, position ouverte, `compare_variants` disjoint) ; sonde B3 : IS 0 / OOS 1 |
| I1 | `1e309` → 201 | **PASS** | `FiniteFloat`, refus chaînes/booléens, bornes ; gardes sur intermédiaires | 11 corps JSON invalides → 422 sans stockage ; modèles ; garde Guardian + moteur |
| I2 | profil « enregistré » contournable | **PASS** | `ATO_RISK_POLICY` : `research` explicite / `supervised` imposé | `test_i2_*` ; sonde I2 (supervised → 403) ; UI « mode recherche » (E2E) |
| I3 | 2 097 687 octets reçus avant le 413 | **PASS** | garde ASGI avant parsing, lignes, 429, 507, threadpool | 0 octet lu si Content-Length excessif ; flux coupé après 5/64 morceaux ; `test_i3_*` |
| I4 | POST `evil.example` → 201 | **PASS** | Host bouclage (421), Origin, `Sec-Fetch-Site`, en-tête `X-ATO-Request` | 5 requêtes étrangères refusées sans écriture ; via Vite (vitest) ; via `pnpm start` (smoke) |
| I5 | `xauusd` → « altéré » | **PASS** | `normalize_symbol` avant identité/stockage/comparaison (contrat inclus) | 5 orthographes → import + backtest OK ; même identité |
| I6 | `.500` tronqué ; collision 1e-8 | **PASS** | fractions de seconde refusées ; `repr` ; stockage = octets empreintés | `test_i6_*` ; aller-retour identique |
| I7 | provenance remplaçable | **PASS** | identité de contenu ≠ provenance ; 409 si contradictoire ; historique | `test_i7_*` |
| I8 | O=105 au-delà du TP → SL −23,21 | **PASS** | franchissements à l'ouverture d'abord (`TP_GAP`, `SL_GAP`) | 6 cas BUY/SELL × gap favorable/défavorable/ambigu ; sonde I8 : +31,79 |
| I9 | publication non atomique | **PASS** | staging + fsync + vérification + renommage atomique + verrou `flock` | interruption injectée, staging résiduel, 6 écrivains concurrents |
| I10 | pas de `/api/v1` en production | **PASS** | relais `server/quantProxy.ts` monté avant `express.json` | `quantProxy.spec.ts` (échoue si mal monté) ; `production-smoke` 9/9 |
| M1 | état conservé entre runs | **PASS** | `key` par run | E2E « 2e run » (échoue sans `key` : 20/21) |
| M2 | USD imposé dans la liste | **PASS** | `account_currency` par résumé ; montant masqué si inconnue | `test_m2_*`, E2E |
| M3 | fuseau invalide → 500 ; période inversée acceptée | **PASS** | `ValueError` explicites ; dates normalisées UTC ; fenêtre non vide | 6 entrées → 422 ; sonde M3 |
| M4 | MFE 449,8 R après la sortie | **PASS** | bornes inférieures prouvées, `excursion_basis` | `test_m4_*` ; sonde M4 : 0 R |

## 3. Changements d'architecture
- `storage/integrity.py` (nouveau) ; `storage/catalog.py` : publication atomique, lecture vérifiée, provenance
  (`dataset_provenance`), colonne `run_digest` (migration douce).
- `api/security.py` (nouveau, middleware le plus externe) ; `api/app.py` : limites, 409/403/421/429/507, threadpool.
- `numeric.py` (nouveau) : types financiers stricts.
- `services.py` : politique de risque, reproduction à deux verdicts, segments IS/OOS documentés.
- `backtest/engine.py` : fenêtre en temps de disponibilité, ordre ouverture → intrabougie, MAE/MFE bornés, gardes de finitude.
- `server/quantProxy.ts` + `server/node-build.ts` : topologie de production locale.

## 4. Questions pour ta revue
1. La falsification **cohérente** (fichiers + `integrity.json` + index SQLite + métriques recalculées) reste possible par
   construction (D-28). Le compromis est-il acceptable pour un laboratoire local, ou faut-il une signature ?
2. `check_consistency` recalcule les métriques via le même `compute_metrics` : une erreur de ce module serait-elle
   invisible ? Faut-il un calcul indépendant de référence ?
3. Garde : contournable via `Host: localhost.` (point final), IPv6 alternatives (`[::ffff:127.0.0.1]`), Origin `null`,
   requêtes sans Origin depuis un navigateur ancien ?
4. Le relais de production transmet tous les en-têtes du navigateur (dont `Host`) : risque ?
5. Mode `supervised` : la comparaison champ par champ couvre-t-elle toutes les façons de relâcher le risque
   (horaires, `max_bars_in_trade`, coûts plus faibles que la réalité) ?
6. B3 : reste-t-il une fuite via les signaux d'échauffement (décision calculée à la clôture de la dernière bougie IS,
   exécutée à la première ouverture OOS) ? Nous la considérons légitime (information, pas résultat).
7. I8 : la convention TP_GAP au niveau du TP (gap favorable non crédité) est-elle la bonne référence conservatrice ?
8. Tests qui passeraient avec un code faux.

## 5. Fichiers
- **Suivis modifiés cette session (CRLF préservé)** : `.gitignore`, `client/pages/Backtest.tsx`, `server/node-build.ts`.
- **Nouveaux / non suivis modifiés** : `.env.example`, `server/quantProxy.ts`, `server/quantProxy.spec.ts`,
  `e2e/production-smoke.mjs`, `e2e/backtest-flow.mjs`, `shared/quant-api.ts`, `client/lib/quantApi.ts`,
  `client/lib/format.ts`, `client/lib/quantApi.integration.spec.ts`, `client/components/backtest/{BacktestResults,ConfigPanel}.tsx`,
  `docs/audits/codex-v03-2026-11-04/*`, `docs/CODEX_REVIEW_HANDOFF.md`, `docs/CONSOLIDATION_AUDIT.md` ;
  `quant/` : `src/ai_trader_optimizer/{numeric.py, storage/integrity.py, storage/catalog.py, storage/__init__.py,
  api/security.py, api/app.py, api/schemas.py, backtest/engine.py, backtest/models.py, ai/validation.py, data/models.py,
  data/validation.py, data/__init__.py, risk/guardian.py, strategies/base.py, safety.py, services.py, ui/pages_run.py,
  __init__.py}`, `tests/{test_codex_v03_regressions.py, conftest.py, test_api.py, test_engine.py}`,
  `scripts/codex_probes_v031.py`, `requirements.lock`, `pyproject.toml`, docs.
- Seule modification d'un test existant en dehors du renommage `TestClient` → `LocalClient` : la valeur attendue de
  `test_engine.py::test_outside_window_and_trade_end_truncate_data` (12:08 → 12:07), qui figeait la fuite B3 (D-29).
- Aucun commit, reset, clean, push. Sauvegarde durable : `~/traider-pro-backups/2026-11-04-pre-v0.3.1/`.

## 6. Limites restantes
Pas d'authenticité cryptographique ; verrou POSIX seulement ; API sans authentification (local) ; profil de risque
modifiable sans contrôle d'accès dans Streamlit ; OHLC sans ticks ; coûts fixes ; pas de marge/swap/conversion ;
contrat 100 oz = hypothèse ; pas d'écriture de la configuration depuis React (Streamlit uniquement) ; Netlify non supporté ; `.env` encore suivi par Git
(placeholder) ; 72 fichiers à fins de ligne seules. Détail : `quant/docs/KNOWN_LIMITATIONS.md`.

## 7. Refonte de l'interface (après V0.3.1, même jour)
Aucun changement du moteur Python ni de l'API. Objectif : supprimer de l'interface tout chiffre inventé et toute
fausse connectivité, et donner à chaque écran une nature explicite.
- **Cadre** : `client/components/layout/{AppShell,Page}.tsx`, `client/lib/modules.ts` — barre latérale ; chaque page
  est étiquetée *Moteur* (chiffres de l'API), *Référence* (hypothèses / documentation) ou *Verrouillé* ; l'état du moteur
  vient de `/api/v1/health`. Remplace `Navigation.tsx` + `DemoDataBanner.tsx` (fichiers conservés, plus utilisés).
- **Pages réécrites** : Accueil (état du labo en direct), Tableau de bord (runs et jeux de données réels, courbe du
  dernier run, `?run=<id>` ouvre un run dans Backtests), Stratégies (`/optimizer` : fiches, règles, paramètres, questions
  ouvertes du trader, prérequis réels de l'optimisation), Instruments (`/trading` : contrat et coûts du moteur, guide
  d'export MT5, plus aucun formulaire d'identifiant), Exécution (`/automation` : verrous lus sur l'API, profil Risk
  Guardian, feuille de route — aucun interrupteur), Paramètres (lecture seule de la configuration du moteur), 404 FR.
- **Retiré de l'écran** : statistiques fictives (« 78,4 % », « XGBoost implémenté »…), robots et P&L simulés en JS,
  formulaire login / mot de passe MT5, options sans effet. Composants désormais inutilisés, conservés sur disque :
  `MT5Connection.tsx`, `MT5Trading.tsx`, `TradingChart.tsx`, `Placeholder.tsx`, `lib/mt5*.ts(x)`, `hooks/trading/*`
  (suppression seulement sur accord). Sauvegarde avant refonte : `~/traider-pro-backups/2026-11-04-pre-ui-redesign/`.
- **Preuve** : `node e2e/pages-tour.mjs [--shots-dir DIR]` (31 vérifications : chiffres = API, aucun texte fictif, aucun
  champ mot de passe ni interrupteur, 390 px sans défilement horizontal, aucune erreur console).


## 8. V0.4.0 — validation hors échantillon (à relire en priorité)
Nouveau package `quant/src/ai_trader_optimizer/research/` (`labels`, `features`, `stats`, `study`, `robustness`),
routes `research/edge-studies` + `backtests/{id}/robustness`, page React `/research`, onglet Robustesse.
Mode d'emploi et méthode : `quant/docs/VALIDATION.md` ; tests : `quant/tests/test_research.py`.
Questions de revue : fuite d'information possible dans les variables ou la purge ? conventions d'étiquetage
strictement identiques au moteur (cas TIME_EXIT / SESSION_END non modélisés : horizon fixe à la place) ? la règle de
verdict et la correction des essais multiples sont-elles assez conservatrices ? les études stockées
(`quant/data/lab/studies/*.json`, identifiées par empreinte des entrées et du code) n'ont pas de vérification
d'intégrité équivalente à `ato-run/1`.
