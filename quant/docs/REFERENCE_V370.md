# Rapport de référence — Gold Grid Strategy V3.70 EA (« Quantum Queen MT5 v3.70 »)

Chaque nombre ci-dessous est **recalculé à partir des deals du rapport**, puis **rapproché du résumé imprimé par MT5**.
Rien n'est repris d'un compte rendu précédent sans vérification.

- Fixture : `quant/tests/fixtures/mt5/`.
- Tests : `quant/tests/test_external_lab.py::test_reference_v370_*`.
- Simulation : `sim_id` `a45999a0c4a1b14f`, `test_key` `056303b9bb3665a3`.

## 1. Sources
| Fichier | SHA-256 | Statut |
|---|---|---|
| `Gold_Grid_V370_MT5_Baseline_2026.html` (UTF-16, 637 010 octets) | `9048261e1d5016ddbe5702e30531490e8dee9d755300b73beb3dac4c4f9309b6` | importé, **validé** |
| `Gold_Grid_V370_MT5_Baseline_2026.xlsx` | `8a75440e24c7219a65c65ab5002fe3574102711f998d9afe6d84e06b2efd9d6e` | importé, **validé** ; **même test** que le HTML (deals identiques) |
| `ReportTester-5058427450.xlsx` | `f6dae967a41011a1ebd2701eadf07450be2bccdbf3d0206dd0fefc6adc0ef78a` | même gabarit, non importé dans les tests |
| `AI_Trader_Optimizer_MT5_Baseline_V370.zip` (CSV extraits du HTML + manifeste) | `5006576c8dc73ba72a766da9b41fedb3b73f02034ccdda0074d6ae506f7b129b` | importé, **partiel** : pas de résumé MT5 à rapprocher ; le manifeste est conservé comme déclaration non vérifiée |
| Graphiques `*.png` exportés par MT5 | — | présents dans `~/Documents/`, non interprétés |
| `.ex5` (3 robots) | — | présents dans `MQL5/Experts/` du terminal ; **jamais exécutés ni lus** |

Emplacements constatés :
- `~/Documents/` ;
- le dossier `Documents` du terminal MT5 (Wine) ;
- export CSV normalisé (deals, ordres, totaux quotidiens, manifeste), placé depuis le 2026-11-05 dans
  `quant/tests/fixtures/mt5/v370_normalized_export/` (fichiers inchangés, déplacés depuis la racine du dépôt).

## 2. Environnement (lu dans le rapport)
| Élément | Valeur |
|---|---|
| Serveur | MetaQuotes-Demo (build 6275) |
| Instrument et unité | XAUUSD, M15 |
| Période demandée | 2026.01.01 – 2026.10.31 |
| Dépôt initial, devise, levier | 10 000 USD, 1:100 |
| Qualité d'historique | 100 % |
| Barres | 13 195 |
| Ticks | 74 962 526 |
| Paramètres | 41, conservés dans l'ordre du rapport |

**Non présents dans le rapport, donc marqués « indisponibles »** : le mode de modélisation (« Every tick »), la latence,
le mode d'optimisation et le libellé « niveau de risque Medium ». Ils sont déclarés par le propriétaire, mais le fichier
ne les contient pas.

Paramètres liés au risque :
- `InpLotsCalc=0`, `InpAutoLotsValue=3`, `InpLotsFixed=0.01`, `InpLotsFixedBalance=500.0` ;
- `InpDDMode=0`, `InpDDValue=0.0`.

Leur signification est une **hypothèse** fondée sur leurs noms (§6).

## 3. Rapprochement MT5 ↔ deals : 23/23 concordants
| Indicateur | MT5 | Recalculé |
|---|---:|---:|
| Total Net Profit | −5 238,26 | −5 238,26 |
| Gross Profit / Gross Loss | 58 491,53 / −63 729,79 | 58 491,53 / −63 729,79 |
| Profit Factor | 0,92 | 0,9178 |
| Total Trades / Total Deals | 314 / 628 | 314 / 628 |
| Profit Trades | 260 (82,80 %) | 260 (82,80 %) |
| Loss Trades | 54 | 54 |
| Long / Short (gagnants) | 216 (84,72 %) / 98 (78,57 %) | identiques |
| Average profit / loss trade | 224,97 / −1 180,18 | 224,97 / −1 180,18 |
| Largest profit / loss trade | 1 664,96 / −6 776,72 | 1 664,96 / −6 776,72 |
| Balance Drawdown Maximal | 51 990,13 (91,61 %) | 51 990,13 (91,61 %) |
| Maximum consecutive wins / losses | 29 / 10 (−51 990,13) | 29 / 10 (−51 990,13) |

Autres indicateurs MT5, conservés tels quels :
- Equity Drawdown Maximal : 52 040,35 (91,62 %) ;
- Sharpe Ratio : −3,11 ;
- Margin Level : 12,43 %.

Ils ne sont **pas** recalculables : il faudrait l'équité entre deux opérations.

Autres contrôles :

| Contrôle | Résultat |
|---|---|
| Colonne Balance | 629/629 cohérentes |
| Ordres | 628 ordres, tous `filled`, pour 628 deals |
| Appariement | **314/314** clôtures expliquées au centime près (taille de contrat 100, déduite) |
| Lignes refusées | 0 |
| Doublons | 0 |

Vocabulaire et décompte :
- 628 ordres (demandes) ≠ 629 deals (628 exécutions + 1 dépôt) ;
- 314 positions ouvertes, 314 trades.

## 4. Divergence de période (documentée avant toute conclusion)
- **Constaté** : dernière opération le **2026-07-30 01:00**, alors que la fin demandée est le **2026-10-31**.
- À cet instant, 5 positions sont fermées avec le commentaire MT5 **`so 12.43%`** (stop-out à 12,43 % de niveau de
  marge), et les 5 autres avec **`end of test`**.
- **Hypothèse** : le testeur a interrompu la simulation parce que le compte ne pouvait plus continuer. Le rapport ne
  donne pas la raison explicitement.

La phrase « résultats du 01/01 au 31/10 » est donc **fausse** : la simulation couvre le 07/01 au 30/07.

## 5. Risk Collapse Analysis : la série des dix pertes finales
| Ouverture (deal, heure) | Prix | Lots | Clôture (deal) | Résultat net | Motif |
|---|---:|---:|---|---:|---|
| #608 22:18 | 4 099,96 | 0,93 | #620 | −6 776,72 | stop-out |
| #609 22:21 | 4 094,30 | 0,93 | #629 | −6 250,34 | fin du test |
| #610 22:22 | 4 090,68 | 0,93 | #621 | −5 913,68 | stop-out |
| #611 22:23 | 4 088,10 | 0,93 | #628 | −5 673,74 | fin du test |
| #612 22:24 | 4 086,42 | 0,93 | #622 | −5 517,50 | stop-out |
| #613 22:26 | 4 084,29 | 0,93 | #627 | −5 319,41 | fin du test |
| #616 22:33 | 4 081,21 | 0,95 | #623 | −5 141,21 | stop-out |
| #617 22:34 | 4 069,15 | 0,95 | #626 | −3 995,51 | fin du test |
| #618 22:46 | 4 067,13 | 0,95 | #624 | −3 803,61 | stop-out |
| #619 22:54 | 4 064,97 | 0,95 | #625 | −3 598,41 | fin du test |
| **Total** | | **9,38** | | **−51 990,13** | 5 stop-out + 5 fin du test |

Toutes les ouvertures datent du 2026-07-29, et toutes les clôtures se font au prix de 4 027,47, le 2026-07-30 à 01:00.

**Constats** :
1. Le solde atteint son plus haut, **56 751,87**, le 29/07 à 22:32, puis tombe à **4 761,74**.
2. 10 positions **BUY** sont ouvertes en **36 minutes**, entre 4 099,96 et 4 064,97, pendant que le prix baisse.
3. Le solde réalisé ne montrait rien de la perte en cours : au stop-out, l'écart estimé entre le solde (49 975,15) et
   l'équité (≈ 6 029) atteint **−43 946**.
4. 82,8 % de trades gagnants, mais une perte moyenne **5,2 fois** plus grande que le gain moyen.
5. Les mois de janvier à juin sont tous positifs : de +1 414 à +16 700. Juillet perd **−42 221**.
6. L'audit de comportement donne le verdict **STOP_OUT**. Il relève jusqu'à 10 positions empilées dans le même sens, et
   125 entrées sur 314 ajoutées alors que la série ouverte perdait.
7. Au pic d'exposition, chaque dollar de baisse de l'or coûtait **938 USD**. Une baisse d'environ **44,5 $** suffisait
   à ramener l'équité estimée à zéro ; le stop-out est arrivé avant, à 37,50 $ de baisse.

**Hypothèses, à confirmer** :
- La taille des lots est **proportionnelle au solde** : 0,163 à 0,170 lot par tranche de 10 000, soit 1 % de variation
  sur 314 ouvertures. Plus le compte gagne, plus chaque position est grosse, ce qui explique les 9,38 lots finaux.
- Le **contrôle de drawdown était désactivé** (`InpDDMode=0`, `InpDDValue=0.0`). Interprétation fondée sur les noms ;
  la documentation de l'éditeur est à consulter.
- Fonctionnement **en grille** : les ajouts se font contre la perte.

## 6. Hypothèses de réduction du risque (aucune n'est un backtest du robot modifié)
| Règle | Valeur | Qualification | Net | DD réalisé max. | Trades conservés | Stop-out encore dans le parcours |
|---|---|---|---:|---:|---:|---|
| Résultat observé | — | — | −5 238,26 | 91,6 % | 314 | oui |
| Arrêt définitif après DD réalisé ≥ X % | 20 % / 50 % | exact | −5 238,26 | 91,6 % | 314 | oui |
| Plus d'entrée après perte journalière ≥ X % | 3 % | approximation | −5 238,26 | 91,6 % | 314 | oui |
| Blocage des entrées si DD d'équité estimé ≥ X % | 20 % | approximation | −7 439,21 | 94,1 % | 298 | oui |
| Lots × k | 0,5 | approximation | −2 619,13 | 77,9 % | 314 | oui |
| Au plus N positions dans le même sens | 5 | approximation | +141,08 | 74,8 % | 284 | oui |
| Au plus N positions dans le même sens | 3 | approximation | +2 301,87 | 60,6 % | 255 | oui |
| Exposition plafonnée à X lots | 3 lots | approximation | +17 197,63 | 41,1 % | 290 | oui |
| Réduction en forte volatilité | — | non simulable | — | — | — | — |

Lecture :
- **Les règles fondées sur les pertes réalisées ne servent à rien ici.** La perte reste latente jusqu'au stop-out ; elle
  devient réalisée d'un coup, au moment où il est trop tard.
- **Bloquer les entrées sur l'équité estimée aggrave le résultat.** Cela retire de petits gains, tandis que la série
  fatale était déjà ouverte.
- **Plafonner l'exposition ou le nombre de positions réduit fortement le drawdown dans l'approximation.** Mais :
  - le robot aurait recalculé ses sorties de panier et ses lots ;
  - le stop-out observé reste dans le parcours.

  Ces chiffres **ne prouvent pas** qu'un tel réglage aurait été rentable. Ils indiquent seulement quoi tester dans le
  Strategy Tester. Un paramètre équivalent existe-t-il dans l'EA ? Les noms ne le disent pas.

## 7. Conclusion pour un trader
- Ce robot a gagné régulièrement pendant six mois, puis a perdu en 2 h 40 plus que tout ce qu'il avait gagné. Le
  compte a été liquidé par le courtier (stop-out) et le test s'est arrêté trois mois avant la date prévue.
- Le taux de réussite de 82,8 % est trompeur. Le risque est concentré dans une série de positions ajoutées contre le
  marché, avec des lots qui grossissent à mesure que le compte gagne.
- **Ne pas l'utiliser tel quel.** Avant toute utilisation en démo :
  1. tester d'autres périodes, en particulier des tendances baissières fortes ;
  2. identifier un réglage de plafond d'exposition ou de drawdown ;
  3. le rejouer dans le Strategy Tester ;
  4. importer le nouveau rapport pour comparaison.
