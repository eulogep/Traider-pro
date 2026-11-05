# Rapport de sécurité — v0.5 (Audit d'EA, pont MT5 local, laboratoire de robots externes)

Périmètre : `ea_audit/`, `external_lab/`, les routes `/api/v1/ea-reports/*`, `/api/v1/mt5/*` et `/api/v1/external-sims/*`,
ainsi que les pages `/ea-audit` et `/bot-analysis`.

## 1. Décision du propriétaire et périmètre retenu
- **Autorisation du 2026-11-05** : connexion à MT5 « seulement si cela sert ».
- **Retenu** : un **pont local en lecture seule**. Les rapports et exports présents dans le dossier du terminal installé
  sur cette machine sont listés, puis lus à la demande.
- **Écarté**, car inutile ou risqué :

  | Option | Raison |
  |---|---|
  | Package Python `MetaTrader5` | Windows uniquement, inexistant pour macOS (vérifié par pip) |
  | Pont ZeroMQ | DLL Windows dans Wine, pour une latence sans intérêt en recherche |
  | API hébergée tierce | elle obligerait à confier ses identifiants à un tiers |

- **Toujours interdit** : envoi d'ordres (réels ou démo), accès au courtier, lecture ou stockage d'identifiants,
  exécution d'un `.ex5`.

## 2. Contrôles en place
| Risque | Contrôle | Preuve |
|---|---|---|
| Envoi d'ordres | aucune route d'ordre ; le mot « mt5 » n'est permis que pour 3 routes en lecture seule, listées explicitement | `tests/test_api.py::test_no_order_route_and_only_allowlisted_routes`, `client/lib/quantApi.integration.spec.ts` |
| Requête d'une page web étrangère (CSRF, DNS rebinding) | garde FastAPI (Host/Origin en boucle locale, en-tête `X-ATO-Request` sur toute mutation), inchangée | `test_api_import_requires_the_local_mutation_header`, `test_api_requires_the_local_mutation_header` |
| Exécution de code | `.ex5` et extensions inconnues refusés (415) ; HTML lu par `html.parser`, sans script ni ressource externe ; XLSX lu comme XML de données, **DOCTYPE/ENTITY refusés** ; formules non évaluées (seule la valeur en cache est lue) ; pas de macro | `test_api_refuses_executables_and_unreadable_reports`, `test_xlsx_with_a_doctype_or_entity_is_refused` |
| Archives malveillantes | ZIP sur 1 niveau, ≤ 20 fichiers, ≤ 60 Mo par fichier et 120 Mo au total, ratio ≤ 200, taille réelle relue (jamais celle déclarée), chemins absolus, `..` ou lecteur Windows refusés, liens symboliques refusés | `test_malicious_archives_are_refused` (5 cas) |
| Déni de service | corps borné par la garde **avant** l'analyse (`ATO_MAX_UPLOAD_MB`), relu par morceaux ; ≤ 400 000 lignes ; ≤ 200 000 deals ; calcul sous `heavy_job` (429 si saturé) | `test_api_accepts_a_real_sized_report_on_the_audit_route` |
| Traversée de chemin (pont MT5) | le client ne fournit **jamais** de chemin, seulement un id de 16 hexadécimaux issu de la liste ; lien symbolique sortant du dossier non suivi ; `config/` et `*.dat` jamais parcourus | `test_local_mt5_files_are_listed_read_only_without_config_or_symlinks`, `test_local_mt5_unknown_ids_and_paths_are_refused` |
| Écriture avant validation | analyse et validation complètes en mémoire, puis publication | `test_corrupt_files_are_refused_and_nothing_is_written` |
| Falsification des résultats | source et simulation en création seule et lecture seule (0444) ; conteneur canonique et SHA-256 ; vérification à chaque lecture, re-dérivation des indicateurs comprise ; journal des imports chaîné | `test_stored_simulation_and_source_are_read_only_and_tampering_is_detected`, `test_a_modified_source_file_invalidates_the_simulation` |
| Confusion avec les runs du moteur | catalogue séparé `external/`, format propre, jamais listé comme run | `test_external_simulations_are_isolated_from_engine_runs` |
| Données personnelles | un rapport du testeur ne contient pas d'identifiant de compte (fixture vérifiée) ; seul le nom du fichier est conservé dans le journal | contrôle manuel de la fixture |

## 3. Défaut de sécurité trouvé et corrigé pendant le développement
- **Constat** : la garde n'accordait la grande limite de corps (`ATO_MAX_UPLOAD_MB`) qu'à `/datasets/import`. Les
  nouvelles routes de téléversement étaient donc limitées à 256 Ko, et le **vrai rapport (637 Ko) était refusé**.
- **Pourquoi cela n'avait pas été vu** : le parcours navigateur de l'Audit d'EA utilisait un petit rapport construit.
- **Correction** : `UPLOAD_PATHS` couvre désormais les deux routes d'import.
- **Régression** : test avec la fixture réelle.
- **Effet de bord** : aucun. Les autres routes gardent la limite JSON.

## 4. Risques restants
- La lecture HTML utilise `html.parser`, robuste mais non durci contre des documents pathologiques au-delà des bornes de
  taille et de lignes.
- Le parseur XML de la bibliothèque standard est protégé contre l'expansion d'entités par le refus des DOCTYPE. Les
  autres attaques XML connues supposent des entités ou des DTD externes, donc elles sont aussi refusées.
- L'API n'a pas d'authentification : c'est un outil local mono-utilisateur sur 127.0.0.1, protégé contre les pages web
  par la garde.
- Le dossier MT5 lu par le pont est celui de l'utilisateur. Un autre logiciel local pourrait y déposer un rapport
  piégé ; il resterait traité comme une donnée non fiable, avec les mêmes bornes.
- Aucune signature cryptographique : les empreintes détectent une altération, elles ne prouvent pas l'auteur.
