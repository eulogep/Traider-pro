# Test de la stratégie de référence dans MetaTrader 5 (2026-11-08)

**Conclusion : sur ces données réelles, la stratégie de référence perd de l'argent.** Elle n'est pas à utiliser.
Elle est illustrative par construction (`strategies/baseline/ema_trend_3bars.v1.0.0.yaml`) : ce test ne dit rien d'une
autre stratégie, ni du marché en général.

En revanche, ce test apporte le **premier contrôle indépendant du moteur Python sur données réelles** : deux moteurs
écrits séparément arrivent au même résultat.

## 1. Cadre
| Élément | Valeur |
|---|---|
| Outil | Strategy Tester de MT5 (build 6304), lancé par `mt5/run_tester.py` |
| Serveur | MetaQuotes-Demo : **ni le courtier du trader, ni un compte réel** |
| Données | XAUUSD M1, 2026-01-01 → 2026-10-30, 286 442 bougies, 0 rejetée par le validateur du moteur |
| Contrat | 100 oz/lot, **lu sur le serveur** (hypothèse du moteur confirmée pour ce serveur) |
| Capital, levier | 10 000 USD, 1:100 |
| Règles | EMA 20/50 + séquence de 3 bougies, SL 1,5 × ATR14, TP 1,5 R, 12 h–17 h UTC, lundi–vendredi |
| Risque | 0,25 % par trade, 2 trades et 2 pertes par jour, perte journalière 1 %, drawdown 10 % |
| Commission, glissement | aucun : ceux du serveur de démo, donc des coûts **favorables** |

**Aucun ordre n'a atteint le compte.** Le journal du terminal ne contient aucune opération de trading, et il indique
« 0 positions, 0 orders » à chaque lancement. Les ordres sont simulés par le testeur ; les robots refusent de démarrer
ailleurs (§6).

## 2. Résultats
| | MT5, OHLC M1 | MT5, ticks réels (qualité 99 %) | Python, coûts OHLC | Python, coûts ticks réels | Python, coûts prudents |
|---|---:|---:|---:|---:|---:|
| Spread | variable (0,075 $ en moyenne à l'entrée) | variable (0,186 $ en moyenne à l'entrée) | 0,075 $ | 0,186 $ | 0,30 $ + 0,05 $ de glissement + 3 $/lot/côté |
| **Résultat net** | **−737,77 $** | **−728,70 $** | −731,54 $ | −783,40 $ | −845,20 $ |
| Trades | 401 | 351 | 402 | 355 | 344 |
| Trades gagnants | 36,66 % | 36,18 % | 36,82 % | 36,06 % | 36,92 % |
| Profit factor | 0,87 | 0,86 | 0,87 | 0,85 | 0,83 |
| Drawdown du solde | 9,94 % | 9,91 % | 9,88 % | 9,92 % | 9,98 % |
| Dernier trade | 12/10 | 07/09 | — | — | — |

- **Seuil d'équilibre** : avec un objectif de 1,5 R, il faut 40 % de trades gagnants, hors coûts. La stratégie en
  obtient environ 36 %.
- **Arrêt par le Risk Guardian** : le budget de drawdown bloque les entrées avant la fin de la période. Sans cette
  limite, les pertes auraient pu continuer. Le résultat net est donc **plafonné par le garde-fou**, et il ne mesure pas
  tout le potentiel de perte de la stratégie.
- **Le spread compte** : en ticks réels, il est 2,5 fois plus élevé à l'entrée qu'en OHLC, car une bougie M1 enregistre
  le spread minimal de la minute. Le mode OHLC est donc optimiste sur ce point.

## 3. Contrôle indépendant du moteur Python
Même stratégie, mêmes bougies, deux moteurs (`mt5/compare_engines.py`) :

| Niveau | OHLC M1 | Ticks réels |
|---|---:|---:|
| Signaux Python / MT5 | 30 110 / 30 110 | 30 110 / 30 138 |
| Signaux communs, même sens | **30 110, soit 100 %** | 30 109, soit 100 % des communs |
| Trades communs (même bougie de signal) | 398 sur 402 / 401 | 349 sur 355 / 351 |
| Même issue (gain ou perte), sur les trades communs | 396 sur 398 | 345 sur 349 |
| Écart médian par trade | 0,01 $ | 0,38 $ |

Les rapports MT5 sont aussi passés par le laboratoire `external_lab` : statut **validé** pour le modèle OHLC, seul
importé dans le catalogue (voir §5), et appariement à **401/401** et **351/351** clôtures sur les deux modèles. Aucune
signature de grille ni de martingale n'est détectée sur le modèle OHLC, comme attendu pour une stratégie à une seule
position.

**Limites de ce contrôle.**
- **Écarts restants** : ils sont attendus (spread constant ou variable, ordre des prix dans la bougie), mais ils n'ont
  pas été analysés un par un.
- **29 signaux propres à MT5 en ticks réels : cause établie.** Ils tombent tous dans un **trou de 5 h 30 de
  l'historique M1** du serveur (du 26/02 à 21:47 au 27/02 à 03:17, heure serveur), alors que les ticks réels couvrent
  cette période. Ce n'est pas un écart entre moteurs, mais une limite des données M1. Le signal propre à Python est à la
  sortie de ce trou (le 27/02 à 01:22 UTC).
- **Sous-estimation du spread** : le moteur Python utilise un spread constant, ce qui reste une limite connue
  (`KNOWN_LIMITATIONS.md`).

## 4. Validation hors échantillon sur ces données réelles
Une **seule** étude, réglages par défaut, coûts volontairement favorables (spread 0,075 $, sans commission). Elle est
inscrite au registre comme étude n° 1 de la famille `historical:XAUUSD:M1` (α = 3,04 %, `study_id` `e46e04c8cce681b8`).

| Mesure | Valeur |
|---|---|
| **Verdict** | **`NO_EDGE` — aucun avantage démontré** |
| Signaux candidats / étiquetés / hors échantillon | 30 110 / 6 752 / 3 404 (1 709 unités indépendantes) |
| Tous les signaux hors échantillon | **−0,060 R** par signal, IC [−0,122 ; −0,0004] |
| Signaux retenus par le filtre (1 600) | −0,020 R, IC [−0,109 ; +0,068] |
| Gain apporté par le filtre | +0,040 R, IC [−0,020 ; +0,098] : non démontré |
| Classement du modèle (AUC) | 0,516, IC [0,485 ; 0,540] : non démontré |

La méthode reste **expérimentale** (`VALIDATION_V041.md`) : son défaut connu est de produire trop de faux « indices
d'avantage », pas d'en manquer. Il ne remet donc pas en cause ce verdict négatif, mais un seul test sur dix mois ne
démontre pas non plus qu'aucune variante ne pourrait fonctionner.

## 5. Données
- **Bougies, décisions, rapports** : régénérables dans `mt5/results/` (hors Git, 25 Mo environ).
- **Catalogue local de l'application** : jeu de données « XAUUSD M1 réel — MetaQuotes-Demo », backtest `5b57d856963dabc6`,
  étude `e46e04c8cce681b8`, simulation externe `8b11cf9547471398` (OHLC). Visibles dans l'application locale.
- **Fuseau du serveur : `Europe/Athens`, mesuré et non supposé.** Avec ce fuseau, la pause quotidienne se termine à
  18:00 heure de New York sur 162 reprises sur 166, y compris pendant les semaines de décalage des changements d'heure
  américain et européen. Une première hypothèse (New York + 7 h) était fausse et a été corrigée avant tout test.

## 6. Sécurité
- `ATO_Baseline` et `ATO_ExportBars` **refusent de démarrer hors du testeur** (`MQL_TESTER`). `ATO_Baseline` revérifie
  ce drapeau avant chaque ordre ; `ATO_ExportBars` ne contient aucune fonction d'ordre.
- `run_tester.py` lance le terminal avec `AllowLiveTrading=0`, sans fournir ni lire d'identifiant, refuse de démarrer si
  MT5 est déjà ouvert, et le terminal se ferme seul à la fin. Il ne peut lancer que nos deux robots.
- Ces verrous sont vérifiés par `quant/tests/test_mt5_experts.py`.
- Les `.ex5` de tiers n'ont pas été lancés.

## 7. Ce qu'il ne faut pas en conclure, et la suite
- **Ce n'est pas un verdict sur le XAUUSD**, ni sur la stratégie du trader pilote, qui reste à formaliser.
- **Pas d'optimisation à ce stade.** Chercher les réglages qui auraient gagné sur ces dix mois produirait un faux
  avantage. Toute nouvelle variante doit être fixée à l'avance, comptée dans le registre et confirmée sur une période
  jamais utilisée.
- **Prochaines étapes utiles** :
  1. formaliser la stratégie du trader (`ENTRETIEN_TRADER.md`) et la tester de la même façon ;
  2. refaire ce test avec l'historique et les coûts de **son courtier** ;
  3. tester d'autres périodes, 2024 et 2025 étant disponibles sur ce serveur.
