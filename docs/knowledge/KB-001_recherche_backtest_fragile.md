# KB-001 — « Du Backtest Fragile à la Plateforme de Recherche Financière »

**Source** : `Du Backtest Fragile à la Plateforme de Recherche Financière _ Une Architecture pour la Fiabilité
Scientifique de l'AI Trader Optimizer.md`, à la racine du dépôt. 107 lignes, SHA-256 `99ef3b51…a3766c1d17fbfc81b7b81a50c1a884fdfd5`.

**Nature** : synthèse de recherche rédigée par le propriétaire avec une quarantaine de liens web. Elle couvre :
- le résumé de l'audit Codex V0.3 ;
- les méthodes de validation ;
- la rétro-ingénierie des EAs MT5 ;
- l'intégration courtier ;
- le risque XAUUSD ;
- une feuille de route.

**Vérifiée le** 2026-11-05 contre le code v0.4.1.

## 1. Qualité des sources citées

- **Citations peu solides.** Beaucoup de citations sont des blogs, des pages commerciales ou une publication
  Facebook. Plusieurs ne soutiennent pas l'affirmation à laquelle elles sont attachées : par exemple, une publication
  Facebook sur la qualité des données MT5 est citée pour le défaut `.gitignore` B1, et un blog de courtier pour la
  garde du risque I2.
- **Ce qui sert de référence ici** :
  - les rapports Codex archivés (`docs/audits/`) ;
  - White (2000), *A Reality Check for Data Snooping* ;
  - Bailey & López de Prado (2014), *The Deflated Sharpe Ratio* ;
  - Politis & White (2004).
- **Le reste** est traité comme une piste, pas comme une preuve.

## 2. Vérification des affirmations

| # | Affirmation de la source | État réel du projet (v0.4.1) | Exact ? | Décision |
|---|---|---|---|---|
| 1 | B1 corrigé : « les paquets de sources sont maintenant inclus dans le suivi Git » | `quant/` **n'est pas suivi par Git** : `git ls-files quant` est vide (KNOWN_LIMITATIONS n° 20). Le paquet `data` est présent sur disque, ce que Codex a vérifié (« PASS technique »). | **Faux** pour le suivi Git | Inchangé : commit seulement avec l'accord du propriétaire (`docs/CONSOLIDATION_AUDIT.md`) |
| 2 | B2/B3/I1–I10 corrigés en V0.3.1, « base solide » | Le contre-audit Codex V0.3.1 a trouvé **6 corrections partielles** et N1–N10 ; elles sont traitées en v0.4.1 (`VALIDATION_V041.md` §7) | **Incomplet** | Déjà traité |
| 3 | I4 : « jeton CSRF adapté aux mutations » | Le projet utilise un en-tête personnalisé `X-ATO-Request` plus un contrôle Host/Origin, côté FastAPI et côté Express (N10), et non un jeton CSRF | **Inexact** (mécanisme différent, même objectif) | Inchangé |
| 4 | WFA : ré-optimiser les paramètres fenêtre par fenêtre, mesurer leur stabilité | Le walk-forward existe pour la validation des signaux (modèle ré-entraîné) et la comparaison IS/OOS de variantes. Il n'y a pas de mesure de stabilité des paramètres optimaux. | Exact en principe | Backlog (§4, B5) |
| 5 | Monte Carlo : DD95 « estimation bien plus réaliste », « valeur incontestable » pour les métriques de chemin | **Contredit par Codex I04-6.** Sur 50 pertes suivies de 50 gains, le drawdown réel vaut −25 %, mais le percentile défavorable des permutations n'est que −7,44 %. Le réordonnancement échangeable détruit la persistance des pertes et **sous-estime** le DD95. | **Faux** dans sa généralité | L'interface le qualifie de « mesure conditionnelle » ; Monte Carlo par blocs au backlog |
| 6 | DSR : « probabilité que la meilleure performance parmi K stratégies soit due au hasard » ; rejet si < 0,5, potentiel si > 0,95 | Le DSR est la probabilité que le vrai Sharpe dépasse le Sharpe maximal attendu sous le nul, compte tenu de K essais, de l'asymétrie et de l'aplatissement. Ce n'est **pas** la probabilité d'un « vrai edge ». Il suppose K honnête : notre **registre d'essais chaîné** le fournit déjà pour les études. | Formulation inexacte, idée juste | **Backlog prioritaire** (§4, B1) |
| 7 | Test de permutation (signaux aléatoires, rendements réels) → p-valeur | Valide seulement si les rendements sont échangeables. La campagne v0.4.1 montre que la dépendance temporelle fausse ce type de test : faux positifs à 17,6 % sur le contre-exemple de Codex (C1), et 8 % sous des régimes d'un jour avec la nouvelle méthode (N11b). | Incomplet (hypothèse non dite) | Pas de permutation iid ; permutation par blocs à envisager dans une campagne |
| 8 | Adopter `vectorbt`, `NautilusTrader` ou `Manifold-BT` | Le moteur actuel est vérifié à l'octet : les étiquettes égalent le `r_multiple` du moteur à 2e-16 près, et les runs sont scellés et reproductibles. Une migration perdrait cette preuve sans défaut démontré. | — | **Écarté** (réécriture injustifiée) |
| 9 | Pont ZeroMQ EA↔Python, package `MetaTrader5`, API hébergée (TickerAll) | **Révisé le 2026-11-05** : le propriétaire autorise la connexion à MT5 « seulement si cela sert ». Le package `MetaTrader5` n'existe pas pour macOS (vérifié par pip). ZeroMQ exigerait une DLL Windows dans Wine pour une latence inutile ici. Une API tierce demanderait de confier ses identifiants. | Exact techniquement | **Retenu sous une autre forme** : pont MT5 local en **lecture seule** sur les dossiers du terminal (`ea_audit/mt5_local.py`), sans ordre ni identifiant. Voir `quant/docs/SECURITY_V05.md`. |
| 10 | Ticks réels et spread bid/ask variable | Le moteur travaille sur des bougies OHLC avec un spread constant. La colonne `<SPREAD>` des exports MT5 est lue et affichée, mais pas utilisée par le moteur. | Exact (limite réelle) | Backlog (§4, B4) |
| 11 | Sizing : (équité × % risque) / (distance du stop en $ × 100 oz) | C'est la formule du Risk Guardian (`risk/guardian.py`), testée dans `test_risk.py`, avec arrondi vers le bas et lot maximal. | **Exact**, déjà fait | — |
| 12 | Limites de drawdown journalière (2–3 %) **et hebdomadaire** (5–8 %), DD statique contre DD suiveur | La limite journalière existe (1 % par défaut). Le drawdown maximal est mesuré depuis le **pic** (suiveur). **Il n'y a pas de limite hebdomadaire ni de DD statique.** | Exact (manque réel) | Backlog (§4, B3) |
| 13 | Exposition corrélée entre instruments | Une étude ou un run porte sur un seul instrument et une seule position : le sujet ne se pose pas encore | — | Au moment du multi-instrument |
| 14 | Stress sur crises (2008, 2010, COVID) | Possible dès qu'un historique réel couvrant ces périodes est importé. Les historiques M1 des courtiers remontent souvent moins loin. | Exact | Backlog (§4, B2) |
| 15 | Trois EAs de Thybor (« Gold Grid Strategy V3.70 », « Gold Grid Strategy X V4.1 », « Gold EA ») : les « Grid » sont un signal d'alarme | Aucun de ces fichiers n'est dans le dépôt. Le moteur **interdit** grille et martingale pour ses propres stratégies (`MARTINGALE_FORBIDDEN`), mais rien n'analysait un EA externe. | Exact | **Construit** : page Audit d'EA (§3) |
| 16 | Rétro-ingénierie : lots qui augmentent après une perte, positions simultanées, placement des stops | Ces signatures se lisent dans la liste des opérations d'un rapport MT5, sans le code source | Exact | **Construit** (§3) |

## 3. Ce qui a été construit à partir de cette source : Audit d'EA

**Pourquoi c'est l'atout le plus utile pour protéger l'argent.** Un EA de grille ou de martingale affiche souvent des
mois de petits gains réguliers. Son risque n'apparaît dans aucune métrique de rentabilité : il est dans le
**mécanisme**. L'audit le rend visible et le chiffre, avant que de l'argent ne soit engagé.

- **Moteur** (`quant/src/ai_trader_optimizer/ea_audit/`) :
  - **lecture** : rapport MT5 HTML (UTF-16 ou UTF-8) ou CSV, en-têtes anglais ou français, tableau repéré par ses
    colonnes ; lignes illisibles comptées et montrées, jamais devinées ;
  - **reconstruction** : positions en FIFO, séries de positions d'un même sens ;
  - **signatures**, avec des seuils fixes et déclarés (`THRESHOLDS`) :

    | Code | Ce qui est détecté |
    |---|---|
    | `STACKING` | Positions empilées dans le même sens |
    | `AVERAGING_DOWN` | Ajouts pendant que la série perd |
    | `LOT_ESCALATION` | Lots croissants dans une série |
    | `MARTINGALE_AFTER_LOSS` | Lot augmenté après une série perdante |
    | `ASYMMETRIC` | Beaucoup de petits gains, une perte énorme |
    | `OPEN_AT_END` | Positions encore ouvertes à la fin du rapport |

  - **verdicts** : `MARTINGALE`, `GRID`, `RISK_SIGNS`, `NO_SIGNATURE` (« pas une preuve de sécurité ») et
    `INSUFFICIENT` ;
  - **test de résistance** : à l'exposition maximale réellement atteinte, mouvement de prix qui ramènerait l'équité
    estimée à la moitié du solde, puis à zéro. Le stop-out du courtier est ignoré, il interviendrait avant.
- **API** : `POST /api/v1/ea-reports/analyze`.
  - En-tête local obligatoire et taille bornée.
  - Extension contrôlée : un `.ex5` est refusé (415).
  - Rien n'est enregistré et aucun terminal n'est contacté.
- **Interface** : page « Audit d'EA » (`/ea-audit`), avec la procédure d'export MT5, le verdict, les mécanismes, le
  test de résistance, la lecture du rapport et les limites.
- **Tests** :
  - `quant/tests/test_ea_audit.py` (16) : martingale de grille, grille à lot constant, martingale après perte à une
    seule position, stratégie simple, chiffres du stress, CSV avec virgule décimale, lignes refusées, API ;
  - `client/components/ea/EaAuditView.spec.tsx` (3) ;
  - parcours navigateur : envoi réel d'un rapport par le champ fichier, 43/43.

**Limites, dites aussi dans l'application.**
- **Mise à jour du 2026-11-05** : le lecteur a été confronté au vrai rapport de « Gold Grid Strategy V3.70 EA ».
  - Lecture : 629 deals, 0 ligne refusée.
  - Net et trades égaux au résumé MT5.
  - Verdict `STOP_OUT` : le compte a été liquidé le 30/07/2026.
  - Analyse complète dans `quant/docs/REFERENCE_V370.md`.
  - Il reste à obtenir les rapports des deux autres EAs.
- Le drawdown latent entre deux opérations n'est pas visible dans la liste des opérations.
- Les seuils sont des heuristiques déclarées, pas une calibration sur des EAs réels.

## 4. Backlog issu de cette source (par valeur pour la décision)

| Id | Élément | Pourquoi | Prérequis |
|---|---|---|---|
| B1 | **Deflated Sharpe Ratio (et PSR)** sur les runs et études, avec K pris dans le registre d'essais | Corrige le biais de sélection quand on teste beaucoup de variantes ; K est déjà compté de façon infalsifiable | Définir la série de rendements (par trade ou journalière) ; valider sur la campagne avant affichage |
| B2 | **Stress de l'audit d'EA sur l'historique réel importé** : combien de fois l'or a-t-il bougé de la distance « compte à zéro » pendant la durée de vie d'une série ? | Transforme un chiffre abstrait en fréquence observée sur XAUUSD | Historique M1 réel du courtier |
| B3 | **Limite de perte hebdomadaire et DD statique** dans le Risk Guardian | Recommandation standard sur l'or, absente aujourd'hui | Nouvelle `ENGINE_VERSION` (la limite change les décisions) |
| B4 | **Spread variable** à partir de `<SPREAD>` MT5 | Un spread fixe sur l'or est une source majeure d'optimisme | Option du modèle d'exécution, tests d'identité comptable |
| B5 | **Stabilité des paramètres en walk-forward** | Indice de sur-ajustement quand l'optimum saute d'une fenêtre à l'autre | Aucun |
| B6 | Lecture des rapports MT5 **XLSX** et des fichiers `.set` (paramètres de l'EA) | Croiser le comportement observé avec les réglages (multiplicateur de lot, pas de grille) | Un exemple réel de chaque format |

## 5. Écarté, et pourquoi

| Élément | Raison |
|---|---|
| ZeroMQ, package `MetaTrader5`, API hébergée | Inutiles ou risqués sur ce poste ; remplacés par un pont local en lecture seule (révision du 2026-11-05) |
| Migration vers vectorbt, Nautilus ou Manifold-BT | Réécriture du moteur sans défaut démontré, avec perte de la traçabilité vérifiée |
| Monte Carlo par permutation iid comme mesure du « pire cas » | Sous-estime le risque quand les pertes se suivent (Codex I04-6) |
| Interpréter DSR > 0,95 comme « potentiel réel » | Un DSR élevé corrige la sélection ; il ne prouve ni l'exécution, ni les coûts, ni la persistance |
| Exécution d'un robot sur compte démo (feuille de route V0.7 de la source) | Hors périmètre tant qu'aucune stratégie n'a survécu au rejeu portefeuille et à une période future |
