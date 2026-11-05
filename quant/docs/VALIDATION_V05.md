# Rapport de validation — v0.5 « External Bot Analysis & Optimization Lab »

Date : 2026-11-05. Logiciel 0.5.0. Moteur inchangé (`backtest-engine/0.3.1`). `research_code_hash` inchangé
(`5e6a8f926021b343`) : la campagne statistique v0.4.1 porte toujours sur le code de recherche en service.
Simulation uniquement : aucun ordre, aucun courtier, aucun commit, push ni déploiement.

## 1. Définition of done
| Critère | État | Preuve |
|---|---|---|
| Rapport MT5 de référence correctement importé | **Oui** : HTML et XLSX, « validé » | `test_reference_v370_html_is_imported_and_matches_every_mt5_figure`, `test_reference_v370_xlsx_is_the_same_test_as_the_html` |
| Métriques extraites = données sources | **Oui** : 23/23 indicateurs MT5 concordants, colonne Balance 629/629 | idem, `REFERENCE_V370.md` §3 |
| Ordres, deals et positions non confondus | **Oui** : 628 ordres, 629 deals (dont 1 dépôt), 314 positions, 314 trades ; BUY `out` ferme SELL | `test_constructed_xlsx_buy_deals_close_sell_positions_collectively` |
| Dix pertes finales identifiées et traçables | **Oui** : deals 620 à 629, −51 990,13, 9,38 lots, 5 stop-out et 5 fin du test | test de référence, parcours navigateur |
| Interface React de consultation | **Oui** : `/bot-analysis` | `SimulationView.spec.tsx`, `pages-tour` |
| Données sources intactes | **Oui** : originaux non touchés ; copies de fixture vérifiées par SHA-256 ; sources stockées en lecture seule | `tests/fixtures/mt5/SHA256SUMS`, test d'altération |
| Tests Python, TypeScript et navigateur | **Oui** (§3) | — |
| Aucun chemin d'exécution d'ordres | **Oui** : liste blanche des routes ; « mt5 » seulement sur 3 routes en lecture seule | `test_no_order_route_and_only_allowlisted_routes`, test d'intégration JS |
| Limites méthodologiques affichées | **Oui** : bandeau « pas un backtest du moteur », constats et hypothèses séparés, qualification des hypothèses, encadré des limites | `SimulationView.spec.tsx` |
| Dossier de contre-audit Codex | **Oui** : `docs/handoffs/CODEX_HANDOFF_V05.md` | — |

## 2. Critères d'acceptation (mission §11)
| # | Critère | Test(s) |
|---|---|---|
| 1 | Import HTML valide | `test_reference_v370_html_*`, `test_constructed_html_is_validated_*` |
| 2 | Import Excel valide | `test_reference_v370_xlsx_*`, `test_constructed_xlsx_*` |
| 3 | Même simulation importée deux fois | `test_the_same_file_imported_twice_is_idempotent`, test API (201 puis 200) |
| 4 | Import contradictoire, même identifiant | `test_same_identifier_with_different_content_is_refused` (409), `test_same_configuration_with_different_deals_is_flagged_contradictory` |
| 5 | Fichier corrompu | `test_corrupt_files_are_refused_and_nothing_is_written` (4 cas) |
| 6 | Archives malveillantes | `test_malicious_archives_are_refused` (5 cas), `test_xlsx_with_a_doctype_or_entity_is_refused` |
| 7 | Données numériques invalides | `test_invalid_numbers_are_rejected_rows_not_guesses` |
| 8 | Transactions incomplètes | `test_incomplete_transactions_are_reported`, `test_a_deals_only_csv_without_mt5_summary_is_partial` |
| 9 | Rapprochement du P&L reconstruit avec MT5 | test de référence (23/23), `..._a_wrong_summary_is_shown_as_a_discrepancy` |
| 10 | BUY/SELL contre OPEN/CLOSE | `test_constructed_xlsx_buy_deals_close_sell_positions_collectively`, `SimulationView.spec` (« clôture ») |
| 11 | Positions multiples et clôtures collectives | idem (panier de 2 SELL fermé à la même seconde), référence (10 positions fermées à 01:00) |
| 12 | Conservation de la configuration d'origine | test de référence (41 paramètres, ordre et valeurs) |
| 13 | Intégrité après import | `test_stored_simulation_and_source_are_read_only_and_tampering_is_detected`, `test_a_modified_source_file_invalidates_the_simulation` |
| 14 | Interface sans données | `pages-tour` : « empty catalogue shows an explicit empty state » |
| 15 | Arrêt de l'API | `backtest-flow --api-down` : « Bot Analysis says offline, shows no simulation and no import form » |

## 3. Résultats
| Suite | Avant v0.5 (KB-001) | Après |
|---|---|---|
| pytest | 280 | **316 passés** |
| ruff | OK | OK |
| Sondes Codex V0.3.1 | 14/14 | 14/14 |
| vitest | 44 | **48 passés** (11 fichiers) |
| typecheck strict | 0 erreur | 0 erreur |
| build | OK | OK |
| `pages-tour` | 43/43 | **52/52** |
| `backtest-flow` | 23/23 | 23/23 |
| `backtest-flow --api-down` | 3/3 | **4/4** |
| `production-smoke` | 9/9 | 9/9 |

## 4. Défauts trouvés pendant le développement (corrigés, pas masqués)
| Défaut | Comment il a été trouvé | Correction |
|---|---|---|
| Limite de corps de 256 Ko sur les routes de téléversement : le vrai rapport (637 Ko) était refusé, y compris sur l'Audit d'EA déjà livré | test API avec la fixture réelle | `UPLOAD_PATHS` étendu, test de régression |
| Tableau des ordres HTML non détecté : MT5 fusionne aussi des cellules de données | lecture du vrai rapport | fin de tableau déterminée par le remplissage des lignes, non par les fusions |
| Lignes XLSX ignorées quand les cellules finales sont vides | test XLSX construit | largeur exigée seulement pour les colonnes obligatoires |
| Appariement FIFO n'expliquant que 299/314 clôtures et scindant les positions finales | rapprochement du profit par clôture | appariement exact par profit MT5 (314/314) ; FIFO et LIFO publiés en alternatives |
| Clôture sans ouverture connue non signalée dans le statut | test « transactions incomplètes » | contrôle « clôtures sans ouverture connue » |
| Résumé de ma fixture construite faux (250 au lieu de 190) | **détecté par le rapprochement lui-même** | fixture corrigée |
| Garde-fou « aucune route mt5 » (Python et JS) contredit par l'autorisation du propriétaire | tests de sécurité | exception explicite pour 3 routes en lecture seule ; le reste reste interdit |

## 5. Fichiers de l'incrément (Audit d'EA, KB-001, pont MT5, v0.5)
- **Nouveaux, Python** :
  - `quant/src/ai_trader_optimizer/ea_audit/{__init__,report,analysis,mt5_local}.py` ;
  - `quant/src/ai_trader_optimizer/external_lab/{__init__,mt5_report,reconstruct,simulation,catalog,whatif}.py`.
- **Modifiés, Python** :
  - `api/app.py` (routes) ;
  - `api/security.py` (`UPLOAD_PATHS`) ;
  - `__init__.py` et `pyproject.toml` (version 0.5.0).
- **Tests** :
  - nouveaux : `quant/tests/test_ea_audit.py`, `quant/tests/test_external_lab.py`, `quant/tests/fixtures/mt5/*` ;
  - modifiés : `quant/tests/test_api.py` (liste blanche) et `client/lib/quantApi.integration.spec.ts`.
- **Nouveaux, React** :
  - `client/components/ea/EaAuditView{,.spec}.tsx`, `client/components/bots/SimulationView{,.spec}.tsx` ;
  - `client/pages/EaAudit.tsx`, `client/pages/BotAnalysis.tsx`.
- **Modifiés, React et outillage** :
  - `client/App.tsx` (CRLF conservé), `client/lib/modules.ts`, `client/lib/quantApi.ts`, `shared/quant-api.ts` ;
  - `e2e/pages-tour.mjs`, `e2e/backtest-flow.mjs`.
- **Documentation** :
  - nouvelle : `quant/docs/{EXTERNAL_LAB,REFERENCE_V370,SECURITY_V05,VALIDATION_V05}.md`, `docs/knowledge/*`,
    `docs/handoffs/CODEX_HANDOFF_V05.md` ;
  - modifiée : `quant/docs/{CHANGELOG,KNOWN_LIMITATIONS,ROADMAP,VALIDATION_V041}.md`.

Non modifiés :
- les originaux du propriétaire (`~/Documents/*`, le dossier MT5) ;
- l'export CSV normalisé de V3.70 (déplacé ensuite, à l'identique, dans `quant/tests/fixtures/mt5/v370_normalized_export/`) ;
- `research/` ;
- le moteur.

## 6. Phase F (IA) : volontairement non commencée
- La mission demande des statistiques descriptives d'abord ; elles sont livrées : rapprochement, mensuel, plus grosses
  pertes, exposition, progression des lots, effondrement, comportement.
- Avec **une** simulation de référence, les 314 trades d'un même test ne sont pas des observations indépendantes. Aucun
  modèle n'a été entraîné.
- Prérequis d'une phase IA :
  1. plusieurs robots, configurations et périodes importés ;
  2. une séparation déclarée à l'avance entre trois ensembles :
     - les données qui servent à formuler les hypothèses ;
     - celles qui servent à choisir les réglages ;
     - celles jamais consultées, réservées à la validation finale ;
  3. un protocole scellé, comme `research_campaign/`.
- Une optimisation rétrospective des règles du §6 du rapport de référence n'est **pas** un avantage démontré.
