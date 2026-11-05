# External Bot Analysis & Optimization Lab (v0.5)

Ce laboratoire analyse des robots MetaTrader 5 externes dont on ne possède que l'exécutable compilé (`.ex5`), à partir
de leurs **rapports de simulation** exportés par le Strategy Tester de MT5.
- Le rapport est traité comme une **donnée non fiable**, jamais comme du code.
- Le `.ex5` n'est ni exécuté, ni lu, ni téléversé : il est refusé avec un code 415.
- Aucune route d'ordre, aucun accès courtier, aucun identifiant MT5 stocké.

Parcours : **Rapport MT5 → Import FastAPI → Validation Python → Stockage immuable → Consultation React (« Bot Analysis »)**.

## 1. Importer un rapport

### 1.1 Depuis MT5
1. Dans le Strategy Tester, lancez le test de l'EA. Le modèle « Chaque tick basé sur des ticks réels » est recommandé.
2. Onglet **Backtest**, clic droit, puis **Rapport** : enregistrez en **HTML** et, si possible, aussi en **Open XML (Excel)**.
   MT5 enregistre par défaut dans le dossier `Documents` de l'utilisateur. Sur macOS, c'est
   `~/Library/Application Support/net.metaquotes.wine.metatrader5/drive_c/users/user/Documents/`.
3. Vous pouvez aussi joindre les graphiques (`.png`) dans un ZIP : ils sont listés, mais ne sont pas interprétés.

### 1.2 Dans l'application
- **Page « Bot Analysis » (`/bot-analysis`)** : choisissez un fichier `.html`, `.htm`, `.xlsx`, `.csv` ou `.zip`, puis
  « Importer ».
- **Rapports trouvés dans le terminal local** : la page liste les rapports du dossier `Documents` et de `MQL5/Files`.
  - La lecture est seule autorisée ; le dossier est configurable par `ATO_MT5_DIR`.
  - Les fichiers `config/` et `*.dat` du terminal ne sont jamais parcourus.
- **API** : `POST /api/v1/external-sims`, en multipart, avec l'en-tête local `X-ATO-Request: 1`.

### 1.3 Formats réellement observés et pris en charge
| Format | Lecture | Contenu extrait |
|---|---|---|
| HTML MT5 (UTF-16, écrit par le testeur) | `html.parser`, bibliothèque standard | réglages, paramètres (« Inputs »), résumé, Orders, Deals |
| XLSX MT5 | ZIP + XML, bibliothèque standard (sans openpyxl), DOCTYPE et ENTITY refusés | idem |
| CSV de deals ou d'ordres (normalisé, séparateur `,`, `;` ou tabulation) | `csv` | Deals et/ou Orders, sans résumé MT5 |
| ZIP de ces fichiers | 1 niveau, 20 fichiers maximum, 60 Mo par fichier, 120 Mo au total, ratio de compression ≤ 200 | un manifeste `.json` est lu comme **déclaration non vérifiée** |

**Non pris en charge** : rapports d'optimisation, `.set` et format XML 2003.

## 2. Ce que le laboratoire distingue toujours
| Notion | Définition | Source |
|---|---|---|
| **Ordre** | demande du robot (état `filled`, `canceled`…) | tableau Orders |
| **Deal** | exécution ; `in` ouvre, `out` ferme, `in/out` retourne | tableau Deals |
| **Position** | ce qu'ouvre un deal `in` | reconstruite |
| **Trade** | une position (ou une part) clôturée, avec son deal d'entrée et son deal de sortie | reconstruit |

- **Le sens d'un deal ne dit jamais s'il ouvre.** Un deal BUY `out` ferme une position SELL.
- **Identifiant de position.** Le rapport du testeur n'en contient pas. L'appariement ouverture ↔ clôture est
  reconstruit selon trois règles :
  1. correspondance exacte du volume et du profit MT5 ;
  2. FIFO ;
  3. LIFO.

  On garde la règle qui explique le plus de profits MT5, et le **taux de vérification est publié**. Sur V3.70,
  314/314 clôtures sont expliquées (FIFO : 299, LIFO : 162).
- **Taille de contrat.** Elle est **déduite** des profits calculés par MT5 lui-même : 100 sur V3.70, à partir de 314
  échantillons. Le profil enregistré ne sert qu'en dernier recours, et il est alors marqué « hypothèse ».

## 3. Validation (avant toute écriture)
Contrôles publiés avec chaque simulation (`validation.checks`) :
1. **Résumé MT5 ↔ deals.** Chaque indicateur MT5 est recalculé à partir des deals, avec pour tolérance l'arrondi du
   chiffre MT5. Indicateurs couverts : profit net, profit et perte bruts, profit factor, trades, deals, gagnants et
   perdants, plus gros et moyens, longs et courts avec leur %, drawdown du solde en montant et en %, séries maximales,
   dépôt initial.
2. **Colonne Balance ↔ cumul des deals.**
3. **Appariement ↔ profit MT5.**
4. **Ordres exécutés ↔ deals.**
5. **Clôtures sans ouverture connue.**
6. **Lignes illisibles** : refusées et listées, jamais devinées.
7. **Doublons de deals** : écartés et listés.

Statut qui en résulte :
- `validé` : tout concorde ;
- `partiel` : un contrôle est impossible, par exemple quand le résumé MT5 est absent d'un CSV ;
- `écarts` : au moins un désaccord.

Un champ absent est marqué **indisponible**, jamais inventé (`availability`).

## 4. Stockage immuable (`<ATO_DATA_DIR>/external/`)
| Élément | Rôle |
|---|---|
| `sources/<sha256>.<ext>` | fichier envoyé, octet pour octet ; création seule, lecture seule (0444) |
| `simulations/<sim_id>.json` | conteneur canonique `{"format": "ato-external-sim/1", "sha256", "simulation"}` ; création seule, lecture seule |
| `imports.jsonl` | journal append-only chaîné par empreintes : chaque tentative, « créée » ou « déjà importée » |

- **Identité** : `sim_id` vaut les 16 premiers caractères de sha256(identité canonique). L'identité comprend robot,
  auto-identification, symbole, unité, serveur, build, période demandée, dépôt, devise, levier, sha256 des paramètres,
  sha256 des deals et sha256 du fichier source.
- **Idempotence** : le même fichier donne le même `sim_id` et les mêmes octets, et le résultat est « déjà importée ».
  Même identifiant mais contenu différent : **409**, rien n'est écrasé.
- **Groupes** :
  - `config_key` regroupe les simulations de même configuration ;
  - `test_key` regroupe celles qui ont en plus les mêmes deals. Le HTML et le XLSX d'un même test sont deux références
    traçables du **même test** ;
  - même configuration avec des deals différents : signalé **contradictoire**.
- **Vérification à chaque lecture** :
  - octets canoniques et empreinte ;
  - identité correspondant à l'id ;
  - source présente avec le même SHA-256 ;
  - indicateurs re-dérivés des deals.

  Une simulation altérée, même ré-empreintée, est refusée (409) et marquée « refusée » dans la liste.
- **Isolation** : ces simulations ne sont **jamais** des runs du moteur. Le catalogue est séparé, et `list_runs()` ne les
  voit pas.

## 5. Schéma d'une simulation (`ato-external-sim/1`)
| Champ | Contenu |
|---|---|
| `sim_id`, `identity`, `config_key`, `test_key` | identité (§4) |
| `versions` | `mt5-report/1` (lecteur), `external-lab/1`, `ea-audit/1` (comportement) |
| `source` | nom, sha256, format, encodage, membres d'archive |
| `declared_manifest` | manifeste JSON fourni, **non vérifié** |
| `robot` | nom (« Expert »), auto-identification (paramètre `InpNoteName`…), version déclarée, site |
| `environment` | serveur, build, société, symbole, unité, période demandée, dépôt, devise, levier, qualité d'historique, barres, ticks, modélisation si présente |
| `inputs` | paramètres d'origine **dans l'ordre du rapport** ; `risk_inputs` est le sous-ensemble lié au risque |
| `metadata` | toutes les paires « Libellé : valeur » du rapport, brutes |
| `reported` | résumé MT5 : `{label, raw, value, pct}`, brut et chiffres lus |
| `recomputed` | les mêmes indicateurs recalculés à partir des deals |
| `reconciliation` | lignes MT5 ↔ recalcul, tolérance, statut |
| `validation` | statut, contrôles, lignes refusées, doublons |
| `period` | période demandée et observée, arrêt anticipé, preuves, interprétation |
| `contract_size` | valeur, source, échantillons |
| `counts` | ordres, deals, positions ouvertes, clôtures, trades |
| `pairing` | règle retenue, clôtures vérifiées, alternatives, volume non apparié |
| `deals`, `orders`, `trades` | données normalisées |
| `timeline` | solde, équité **estimée**, lots ouverts après chaque deal |
| `lot_progression`, `monthly`, `largest_losses` | séries descriptives |
| `collapse` | plus grand épisode de drawdown réalisé : pic, creux, pertes, lots, motifs de clôture, écarts entre entrées |
| `behaviour` | audit grille / martingale / stop-out (`ea_audit`) |
| `findings` | `observed` (constats du rapport) et `hypotheses` (interprétation du code fermé, avec indice) |
| `availability`, `limits` | ce qui manque et ce qu'on ne peut pas conclure |

## 6. API (lecture et import uniquement)
| Méthode | Route | Rôle |
|---|---|---|
| POST | `/api/v1/external-sims` | import d'un fichier (201 « créée », 200 « déjà importée », 409 conflit, 413, 415, 422) |
| POST | `/api/v1/external-sims/from-mt5/{file_id}` | import d'un rapport listé dans le terminal MT5 local (lecture seule) |
| GET | `/api/v1/external-sims` | catalogue vérifié, regroupé par robot, groupes même-test / contradictoire |
| GET | `/api/v1/external-sims/{sim_id}` | simulation complète, vérifiée à la lecture |
| GET | `/api/v1/external-sims/what-if-rules` | règles d'hypothèse disponibles |
| GET | `/api/v1/external-sims/{sim_id}/what-if?rule=&value=` | règle appliquée, **qualifiée** |
| GET | `/api/v1/mt5/local-files` | rapports présents dans le terminal local (lecture seule) |

## 7. Hypothèses de réduction du risque : qualification obligatoire
| Qualification | Sens | Règles |
|---|---|---|
| `exact` | recalcul d'événements observés uniquement | arrêt définitif au premier instant à plat après un drawdown réalisé ≥ X % |
| `approximation` | conditionnelle : les trades conservés sont supposés se clôturer comme observé | plafond de positions, plafond de lots, lots × k, blocage sur drawdown d'équité estimé, arrêt journalier |
| `non_simulable` | données absentes | réduction en forte volatilité : pas de série de prix dans le rapport |

**Une approximation n'est jamais un backtest du robot modifié.** Un robot à panier recalcule ses sorties sur toutes
ses positions. Sa taille de lots suit le solde. Le stop-out dépend de la marge. Pour un vrai résultat, relancez l'EA
dans le Strategy Tester avec un réglage équivalent, puis importez le nouveau rapport pour comparaison.

## 8. Ce qu'on peut et ne peut pas déduire des rapports et des `.ex5`
**On peut** :
- vérifier la cohérence interne du rapport (§3) ;
- reconstruire positions et trades (appariement vérifié) ;
- mesurer exposition, empilement, progression des lots et motifs de clôture (stop-out, fin du test, TP/SL) ;
- dater un arrêt anticipé ;
- identifier les pertes qui font l'effondrement ;
- comparer plusieurs rapports et configurations.

**On ne peut pas** :
- connaître la logique interne du robot : tout ce qui la concerne est **hypothèse**, comme « le contrôle de drawdown
  est désactivé », déduit du nom des paramètres ;
- connaître l'équité réelle entre deux opérations : elle n'est estimée qu'aux instants d'opération ;
- savoir ce que le robot aurait fait avec d'autres règles ;
- vérifier contrat, coûts ou conditions du serveur de démo ;
- garantir qu'un autre marché, une autre période ou d'autres réglages ne déclencheraient pas un autre comportement ;
- affirmer une rentabilité future.

**Du `.ex5` seul** : son nom et sa taille. Le lancer dans le backend est interdit. Le désassembler n'est ni prévu ni
légitime ici.

## 9. Décisions d'architecture
- **Réutilisé** :
  - les lecteurs stricts de nombres et de dates et l'analyseur de tableaux HTML de `ea_audit/` ;
  - l'audit de comportement `ea_audit.analysis` ;
  - `storage.integrity.canonical_json` ;
  - la garde locale et les limites de taille ;
  - `heavy_job` ;
  - le pont MT5 en lecture seule (`ea_audit/mt5_local.py`) ;
  - les composants de page React.
- **Non modifié** : `research/`. `research_code_hash` reste `5e6a8f926021b343`, et la campagne v0.4.1 reste valable. Le
  modèle « création seule et vérification à la lecture » est donc réimplémenté dans `external_lab/catalog.py` au lieu
  d'être extrait de `research/study.py`.
- **Aucune nouvelle dépendance.** L'XLSX est lu avec la bibliothèque standard, ce qui évite aussi les macros et les
  formules.
- **Aucun calcul financier en TypeScript.** La page n'affiche que les chiffres de Python ; même les constats et
  hypothèses sont rédigés côté Python.
