# Audit quantitatif et IA indépendant — AI Trader Optimizer V0.4.0

Date : 4 novembre 2026, Europe/Paris. Objet : validité des preuves statistiques, labels, modèle, recommandations et robustesse ; sans connexion courtier ni ordre.

**Verdicts :**

- **Fiabilité technique : NO-GO pour déclarer le logiciel financièrement validé.** Les parcours nominaux passent, mais des lectures financières restent non vérifiées et le nouveau stockage des études peut servir un verdict altéré.
- **Fiabilité scientifique du moteur IA : NO-GO.** Le contrôle des essais multiples est incorrect comme garantie familiale, l’inférence sous dépendance est insuffisamment protégée et un modèle numériquement invalide peut conduire à « PRENDRE ».
- **Aptitude à analyser une stratégie réelle XAUUSD : NO-GO pour conclure à un avantage ou recommander des prises de position.** Le logiciel peut servir de laboratoire exploratoire, sous réserves explicites ; aucun avantage réel ni fidélité ticks/courtier n’est démontré.

La régression logistique, les features causales et le walk-forward constituent une base de recherche utile. Les formulations « avantage démontré » et les probabilités affichées dépassent néanmoins ce que les contrôles présents permettent d’établir.

## 1. Périmètre et séparation des versions

Le workspace partagé a évolué de V0.3.1 vers V0.4 pendant le travail. Deux exports distincts ont donc été utilisés :

- Contre-audit V0.3.1 : `/private/tmp/codex-counter-v031-d7c34xx6/CODEX_CONTRE_AUDIT_V031.md`, **239 fichiers**.
- Présent audit V0.4.0 : `/private/tmp/codex-audit-v04-lhxtu170/repo/`, **260 fichiers** ; manifeste SHA-256 `snapshot-manifest.json`. HEAD racine inchangé : `2dedf6c758ec124098db5f6abd4076e1d8dd134b` ; les nouveautés restent dans le worktree.

L’export V0.4 contient exactement l’union des fichiers suivis actuels et non suivis non ignorés, avant ajout séparé des dépendances d’exécution. Les tests n’ont pas mélangé les deux exports. Les sources du dépôt principal et l’index n’ont pas été modifiés par l’auditeur ; les changements observés dans le workspace partagé sont externes à ces sondes. Aucune installation nouvelle, publication ou opération Git destructive n’a été faite.

Dépendances JavaScript copiées ; venv Python existant réutilisé, `PYTHONPATH` prioritaire sur les sources exportées, bytecode désactivé. Les falsifications, modèles défectueux et interruptions concernent exclusivement les répertoires temporaires de l’audit.

## 2. Fonctions et tests vérifiés indépendamment

| Contrôle | Résultat |
|---|---|
| Python | **232 passed**, 326,61 s |
| JavaScript | **32 passed**, 7 fichiers |
| TypeScript strict | **PASS** |
| Build SPA + serveur | **PASS** |
| Ruff | **PASS** |
| Parcours navigateur Backtests | **23/23 PASS** |
| Parcours navigateur API absente | **3/3 PASS** |
| Smoke test de distribution locale construite | **9/9 PASS** |
| Tour complet desktop/mobile, recherche et robustesse | **38/38 PASS**, captures conservées |
| Régressions indépendantes du contre-audit antérieur | Rejouées sur V0.4 ; réserves financières/provenance toujours reproduites |
| Expériences statistiques indépendantes | **180 expériences** : 60 nulles indépendantes, 30 faibles, 30 moyennes, 60 nulles corrélées |

Le premier tour avec captures a échoué parce que le répertoire de sortie fourni n’existait pas ; après création de ce répertoire temporaire, le parcours complet passe. Ce n’était pas un défaut de calcul du produit.

Constats positifs :

- Les features examinées utilisent des fenêtres passées et des bougies clôturées. Les tests par préfixe indépendants à deux indices passent ; aucun accès direct aux futurs prix n’a été trouvé dans ces features.
- Le scaler de la régression est ajusté sur le train. Les labels de train sont filtrés par leur temps de sortie avant la fenêtre test ; le seuil est choisi dans une validation interne plus tardive que le sous-train, puis évalué sur la fenêtre externe.
- Le modèle est une régression logistique L2, Newton/IRLS, `l2=1`, maximum 50 itérations, intercept non pénalisé. Il n’y a pas de modèle complexe caché ni de prétendu apprentissage profond.
- Les 12 features déclarées correspondent aux colonnes calculées : élans en ATR, tendance EMA, position dans le range, corps, régime de volatilité, stop/ATR, coûts/R et heure cyclique.
- Les conventions SL/TP/gaps et les coûts concordent avec le moteur pour les cas SL/TP couverts ; les divergences TIME_EXIT/SESSION_END et portefeuille sont détaillées plus bas.
- Le scénario nominal sans avantage affiche bien « NE PAS TRADER ». Le parcours recherche/robustesse affiche des nombres de l’API, pas des constantes fabriquées.
- **21 routes API quant actives, aucune route d’ordre identifiée** ; aucun import courtier actif ni exécution de trading ajouté. Le Risk Guardian reste séparé du prédicteur ; la séparation ne signifie pas que chaque avis passe déjà ses contrôles.

Ces PASS ne vérifient ni un avantage sur un marché réel, ni la probabilité de profit futur, ni l’absence de toutes les erreurs statistiques.

## 3. Les 2 856 signaux et les expériences annoncées : état de la preuve

Le nombre **2 856** n’a pas pu être rattaché à une expérience exacte : aucune fiche fournissant dataset/version, seed, paramètres et résultats complets de cette affirmation n’a été trouvée dans l’export. Les comptes **1/60, 19/30, 30/30** figurent dans `CHANGELOG.md` et `VALIDATION.md`, mais le protocole intégral des 120 essais, les seeds et la définition quantitative des avantages faible/moyen ne sont pas archivés avec ces chiffres. Les tests versionnables couvrent notamment 12 essais de bruit et une relation plantée ; ils ne constituent pas le journal des 120 essais annoncés.

L’utilisateur a confirmé que Claude ne lui avait communiqué ni dataset, ni seeds, ni script de ces expériences. Après recherche ciblée supplémentaire dans les sources, tests, scripts, configurations et documentation, les affirmations **2 856 signaux, 1/60, 19/30 et 30/30 sont classées NOT_REPRODUCIBLE avec les pièces disponibles**, et non comme chiffres vérifiés. Cela ne bloque pas les autres conclusions. Les résultats ci-dessous sont des **expériences indépendantes avec protocole explicite**, pas une prétendue reproduction exacte des comptes annoncés.

Pour le pipeline concret, la démo `seed=7, days=20`, baseline par défaut, produit :

| Niveau | Nombre |
|---|---:|
| Signaux bruts de la stratégie | 2 439 |
| Signaux étiquetés après filtres de session/horizon | 495 |
| Transactions du moteur avec Risk Guardian | 30 |
| Observations OOS évaluées | 250 |
| Observations OOS retenues par le filtre | 92 |
| Maximum d’horizons de labels simultanés | 4 |
| Paires de labels dont les horizons se chevauchent | 250 |

Les 495 labels ne sont donc ni 495 paris indépendants ni 495 transactions simultanément autorisées. Un même mouvement de prix peut contribuer à plusieurs résultats. Cela est acceptable pour construire des candidats, à condition de traiter explicitement dépendance, exposition et unité statistique.

### Inventaire des éléments effectivement trouvés et des preuves manquantes

| Élément trouvé | Ce qu’il permet de reproduire | Ce qu’il ne prouve pas |
|---|---|---|
| `data/synthetic.py::synthetic_m1_frame` | Générateur paramétré par seed, jours, date et prix de base ; défaut seed 42, 10 jours, début 7 septembre 2026 ; drift sinusoïdal explicite | Aucun rattachement aux 2 856 signaux ni au lot des 120 expériences |
| `quant/examples/SYNTHETIQUE_demo_xauusd_m1.csv` et `scripts/make_example_csv.py` | Exemple synthétique seed 2026, 3 jours, prix arrondis à 2 décimales | Aucun dataset réel de l’annonce |
| `scripts/demo_cli.py` | Backtest synthétique, défaut seed 42 / 10 jours ; option de règles legacy | Aucun protocole de puissance/faux positifs 60/30/30 |
| `tests/test_research.py::_signals` | Nul Bernoulli p=0,40 et relation plantée logistique de coefficient 1,6 ; seeds explicites des tests | Aucune définition séparée/versionnée d’un avantage « faible » et « moyen » de 30 essais chacun |
| Test de bruit versionné | 12 essais, seeds RNG 100–111, 1 500 signaux, 300 bootstrap, seeds bootstrap 0–11 | Ni les 60 essais annoncés ni leur journal individuel |
| Test de relation plantée | Seed RNG 11, 4 000 signaux, 500 bootstrap, seed bootstrap 1 | Ni une réplication de 30 essais ni une puissance estimée sur plusieurs seeds |
| `e2e/pages-tour.mjs` | Démo seed 42 / 60 jours ; notre parcours montre 7 180 candidats, 1 520 étiquetés | Pas les 2 856 observations de l’annonce |
| `quant/strategies/*.yaml` | Baseline versionnée et brouillon du trader ; bornes de paramètres | Pas la configuration exacte des études annoncées |
| `quant/data/lab/studies/` inspecté en lecture seule | Aucune étude disponible trouvée à cet emplacement dans le workspace | Aucun manifeste permettant de rattacher ces annonces à un `study_id` |

**Preuves précises à fournir pour rendre les annonces reproductibles :**

- Pour **2 856** : préciser s’il s’agit de candidats bruts, labels, OOS ou signaux retenus ; octets du dataset ou générateur et arguments complets, `dataset_id`/hash, nature, plage temporelle/timeframe/fuseau, stratégie/spec/version/paramètres, session, contrat/coûts, horizon et règles de sélection des lignes, `study_id`, version/empreinte du code et environnement.
- Pour **60/30/30** : script de boucle, générateur de chaque population et définition numérique des effets faible/moyen, effectifs/dépendances/horizons, liste complète des seeds de génération **et** bootstrap, settings/model/hyperparamètres, correction multiple appliquée, liste des essais inclus/exclus et résultat de chacun, hashes des données et du code.
- Pour les trois expériences : protocole arrêté avant lecture des résultats, journal des essais infructueux et réglages successifs, sorties complètes et intervalles d’incertitude. Un compte rendu textuel ou un test unique avec un seed favorable ne remplace pas ces pièces.

## 4. Expériences statistiques indépendantes et incertitude

Script : `statistical_probes.py`. Pour chaque essai, entrées temporelles espacées d’une minute, 4 features normales indépendantes du résultat ; gain `+1,5 R`, perte `−1 R`, `StudySettings(n_boot=300)`, paramètres de walk-forward par défaut. Les seeds et les résultats individuels sont dans `statistical-evidence.json`.

| Population simulée | Seeds | Espérance vraie | Essais | Verdicts EDGE |
|---|---|---:|---:|---:|
| Bernoulli indépendant p=0,40 | 100–159 | 0 R | 60 | **0** |
| Bernoulli indépendant p=0,45 | 200–229 | +0,125 R | 30 | **19** |
| Bernoulli indépendant p=0,50 | 300–329 | +0,25 R | 30 | **27** |
| Nul p=0,40, résultat commun par groupe de 100 signaux | 400–459 | 0 R | 60 | **8** |

Les trois premiers cas ont 1 500 signaux ; le dernier en a 3 000, mais seulement 30 résultats de groupe indépendants. L’issue du groupe est déclarée connue à sa fin, afin que le test n’invente pas une fuite de label pour provoquer le problème. Le risque examiné est bien la dépendance résiduelle de l’inférence, après purge.

Ces 180 essais ne répliquent pas le protocole inconnu de Claude. Ils suffisent toutefois à montrer qu’un contrôle apparemment satisfaisant sur du bruit indépendant ne se transfère pas automatiquement aux labels corrélés. Le compte **8/60** n’est pas une estimation universelle du taux d’erreur du logiciel : c’est un contre-exemple reproductible à sa portée de validation actuelle.

Intervalles binomiaux exacts bilatéraux à 95 %, calculés par inversion de la loi binomiale :

| Compte | Intervalle du taux sous le protocole considéré |
|---|---|
| Annoncé 1/60 | **0,042 % à 8,94 %** |
| Annoncé 19/30 | **43,86 % à 80,07 %** |
| Annoncé 30/30 | **88,43 % à 100 %** |
| Indépendant 0/60 | **0 % à 5,96 %** |
| Nul corrélé 8/60 | **5,94 % à 24,59 %** |

Ces intervalles portent sur des répétitions indépendantes de l’expérience simulée, pas sur les signaux corrélés à l’intérieur d’un essai. La méthode d’intervalle exact suit l’inversion binomiale décrite par [NIST](https://www.itl.nist.gov/div898/software/dataplot/refman1/auxillar/propconf.htm). Soixante simulations ne prouvent donc pas définitivement le contrôle d’un taux de faux positifs.

Les populations faible/moyenne de notre expérience n’ont **aucune information prédictive dans X** : leur avantage vient du taux de gain de base. Détecter cet avantage ne démontre pas que l’IA reconnaît les bons signaux. Ce point est distinct de la puissance d’un test d’espérance.

## 5. Anomalies bloquantes scientifiques

Les chemins Python abrégés sont relatifs à `quant/src/ai_trader_optimizer/`.

### B04-1 — Le « Bonferroni » séquentiel ne contrôle pas la famille annoncée

**Fichiers :** `research/study.py:256-279`, `list_studies`, `multiple_testing` ; avertissement de `StudyView.tsx`. **Certitude : calcul et scénario de cache reproduits.**

Le m-ième nouvel essai reçoit `alpha=0,05/m`. Les anciens essais restent consultables à leur seuil original ; une étude identique mise en cache conserve sa première correction. Après deux études, les valeurs observées sont **0,05** puis **0,025**, et la première conserve **0,05**. Modifier seulement `n_boot` change aussi l’identifiant et le seed bootstrap.

Le budget cumulé des 60 premiers seuils est **0,2339935**, pas 0,05. À titre de démonstration mathématique indépendante du bootstrap, pour 60 p-values uniformes indépendantes testées avec ces seuils, la probabilité d’au moins un rejet est **21,03 %**. Ce chiffre n’est pas le taux d’EDGE mesuré du logiciel : il montre que cette allocation ne peut pas être présentée comme une garantie familiale à 5 %.

Une correction de Bonferroni pour une famille définie utilise son nombre total de comparaisons ; voir la [documentation primaire R](https://stat.ethz.ch/R-manual/R-devel/library/stats/html/p.adjust.html). Le mécanisme actuel est une suite non sommable, pas un budget alpha contrôlé pour des essais ouverts.

**Impact :** optimisation répétée des paramètres, horizons, folds ou réplications bootstrap peut conserver un ancien EDGE chanceux. Le compteur local par dataset ne couvre pas les variantes presque identiques du même historique, les changements d’identité de dataset, les registres supprimés ou les essais externes. Deux études concurrentes peuvent aussi compter le même nombre de prédécesseurs, faute de registre transactionnel.

**Correction :** définir avant évaluation une famille et corriger/requalifier tous ses résultats, ou employer une procédure séquentielle avec budget total borné (et hypothèses justifiées). Registre immutable et transactionnel des intentions d’essais, identité de la famille de données, plan d’analyse préenregistré, test final futur scellé. Une simple alerte de ne pas relancer ne suffit pas à soutenir le mot « démontré ».

### B04-2 — Le bootstrap par nombre de signaux sous-estime certaines dépendances

**Fichiers :** `research/stats.py::block_length,block_bootstrap_indices`, `research/study.py:151-185`, `research/labels.py`. **Certitude : expérience nulle corrélée reproduite.**

La longueur de bloc est `round(2*n**(1/3))`, sans liaison aux horizons des labels ni aux épisodes de marché. Elle vaut 23 pour 1 500 observations et environ 23 sur les moitiés OOS du contre-exemple de groupes de 100. De nombreuses copies d’un même résultat contribuent donc au seuil d’effectif et à une incertitude trop étroite.

**Reproduction :** la population nulle corrélée de la section 4 produit **8 EDGE/60**, malgré zéro espérance théorique et des features sans information. Les détails de seeds, folds et intervalles sont archivés. Le bootstrap de prédictions OOS déjà calculées ne réentraîne pas non plus toute la procédure de sélection/modélisation dans ses tirages : sa portée est conditionnelle et doit être dite.

**Impact :** 100 signaux OOS et 50 signaux retenus ne garantissent pas 100/50 observations effectives. La dépendance peut survivre à la purge train/test ; celle-ci ne rend pas les résultats de test indépendants entre eux. Des copies de la même évolution de prix peuvent soutenir un faux verdict.

**Correction :** identifier les groupes d’événements/horizons chevauchants ; inférence par blocs temporels ou épisodes justifiés et tests de sensibilité à la longueur de bloc ; mesure d’effectif effectif ; planchers d’épisodes indépendants ; validation sur régimes et données nul dépendant. Selon la cible, rééchantillonner la procédure complète ou limiter clairement le verdict à l’incertitude conditionnelle évaluée.

### B04-3 — Une défaillance numérique du modèle peut produire « PRENDRE »

**Fichiers :** `research/stats.py::LogisticModel.fit,predict_proba`, `research/study.py:295-338,_finite`. **Certitude : reproduit avec le vrai LogisticModel et à la frontière de recommandation.**

**Reproduction :** entraîner le vrai modèle sur 200 lignes de 12 nombres tous finis, égaux à `1e308`, avec deux classes. Le contrôle initial de finitude passe, mais les moyennes/variances débordent ; les coefficients deviennent non finis sans exception. `_latest_opinion` appelé avec ce modèle et `thr=None` renvoie **`probability_win=NaN`, `opinion=PRENDRE`**. Une injection indépendante d’un modèle retournant NaN reproduit le même comportement.

Le test `thr is None or p >= thr` accepte inconditionnellement si le seuil n’a pas été sélectionné. Le contrôle global remplace cet avis par NE PAS TRADER uniquement si le verdict n’est pas EDGE. Il ne vérifie pas la validité de la probabilité ou du modèle. La sérialisation remplace ensuite le nombre non fini par `null`, au lieu d’invalider la décision.

**Portée :** cette sonde valide un défaut de calcul et de logique de recommandation ; elle ne prétend pas que le jeu de prix nominal testé a simultanément produit EDGE et cette panne numérique. Le nominal sans EDGE reste correctement refusé.

**Correction :** contrôler finitude et convergence à chaque étape du fit, au scoring et avant avis ; vérifier p∈[0,1], seuil valide, domaine couvert et modèle valide. Toute invalidité doit produire NE PAS TRADER avec raison explicite et invalider l’étude concernée ; jamais simplement transformer NaN en null tout en conservant PRENDRE. Un modèle sans filtre actif ne doit pas être confondu avec une prédiction validée.

## 6. Anomalies importantes

### I04-1 — Régression d’intégrité : études et avis stockés sans vérification

**Fichiers :** `research/study.py::load_study,list_studies,run_edge_study,_write_atomic`, routes `/research/edge-studies`. **Certitude : reproduit via API et réutilisation.**

Modifier seulement `studies/<id>.json` en remplaçant le verdict par EDGE et l’avis par PRENDRE : GET répond **200** avec le verdict falsifié. Relancer la même étude restitue également le JSON falsifié, avant rechargement du dataset. Aucun checksum/digest/contrôle sémantique analogue à `ato-run/1` n’est appliqué. Le compteur d’essais dépend de ces mêmes fichiers.

**Impact :** une corruption ou un writer fautif suffit à falsifier une conclusion scientifique persistée, et le cache l’entérine. L’atomicité d’un rename n’est pas une preuve d’intégrité. Ce n’est pas une attaque distante démontrée ni une exigence de signature contre l’administrateur local.

**Correction :** appliquer un protocole vérifié aux études, prédictions, modèles et registre d’essais ; ne servir que les octets validés ; distinguer identité du calcul, état du registre et verdict. Tester corruption du détail, des résumés et du modèle. La nouvelle couche a réintroduit la classe de défaut que B2 tentait de fermer.

### I04-2 — L’avantage de candidats seuls n’est pas celui du portefeuille exécutable

**Fichiers :** `research/labels.py`, `research/study.py::evaluate_signals`, `client/components/research/StudyView.tsx`. **Certitude : écart d’échantillon et chevauchements mesurés ; rentabilité d’un portefeuille filtré non démontrée.**

La démo indépendante compte **495 labels contre 30 transactions autorisées**, avec 250 paires d’horizons chevauchants. La courbe cumulée additionne des R par signal, y compris des signaux simultanés ; elle n’est pas une courbe de capital. Les limites journalières, l’occupation d’une position, les tailles minimales, le drawdown et la remise à l’échelle du risque ne sont pas appliqués à cette somme.

La documentation technique dit bien que les candidats sont simulés seuls, ce qui est utile. En revanche, les libellés « stratégie seule », « espérance par trade » et « avantage démontré » doivent être restreints à cet objet. Une espérance positive de tous les candidats ne prouve pas celle du sous-ensemble qu’un portefeuille pourra prendre.

**Correction :** conserver le jeu de candidats pour apprendre, puis rejouer les décisions OOS sélectionnées dans le moteur avec le vrai Guardian et une politique d’allocation figée ; comparer baseline/filtre après coûts sur les mêmes contraintes. Publier séparément espérance des candidats, rendement du portefeuille, exposition, capacité et risque. Aucun résultat de portefeuille filtré de ce type n’a été établi ici.

### I04-3 — La recherche accepte des configurations incompatibles avec le moteur principal

**Fichiers :** `research/study.py:241-270`, `research/labels.py:36-107`, `api/app.py:357-369`. **Certitude : reproduit.**

Trois contre-exemples :

1. Demander un début d’étude dans les cinq dernières bougies : **même study_id**, mêmes **495 labels**. `trade_start/trade_end` ne sont ni appliqués ni inclus dans l’identité.
2. `max_bars_in_trade=1` sur un exemple manuel : moteur **TIME_EXIT, −5,06 USD, −0,2180 R** ; label **TP, +1,3697 R** plus tard. SESSION_END n’est pas non plus modélisé ; ces différences sont reconnues dans le handoff mais pas refusées par le contrat API.
3. Dataset M5 avec stratégie spécifiée M1 : moteur refuse ; recherche **accepte**. En mode supervisé, une requête de recherche avec contrat EURUSD sur dataset XAUUSD-DEMO et limites relâchées répond également **201**, sans passer par `resolve_risk_policy`. Aucune position n’est ouverte, mais l’étude ne possède pas les garanties de domaine du backtest.

**Impact :** « mêmes paramètres/conventions » n’est pas vrai pour tout BacktestConfig accepté. La devise/symbole du contrat peuvent aussi rendre les coûts et le R économiquement incohérents. Cela ne prouve pas un contournement d’ordre réel, qui est absent.

**Correction :** schéma de recherche spécialisé, refus des champs non supportés, validation timeframe/contrat/devise et application ou refus explicite des fenêtres/sorties. Réutiliser une primitive commune de simulation d’un ordre, avec tests de parité couvrant toutes les sorties ; séparer le mode de recherche des attestations de supervision.

### I04-4 — Le dernier signal peut être évalué par un modèle ayant appris son résultat

**Fichiers :** `research/study.py:281-338`. **Certitude : appartenance au train reproduite.**

Dans la démo `seed=7, days=20`, le dernier avis porte sur le signal **25 septembre 2026 à 16:31 UTC** ; son label perdant est connu à la fin de sa bougie de sortie vers 16:34/16:35 et il fait partie des **495 lignes de train** du modèle final. Le dataset se termine à 23:59. Le modèle final apprend tous les labels, puis `_latest_opinion` choisit le dernier signal de toute la série, sans vérifier qu’il soit nouveau, non résolu ou exclu de l’entraînement.

**Impact :** la probabilité de cet avis est une probabilité ajustée sur un historique pouvant inclure sa cible, pas une prévision OOS. Le verdict walk-forward ne devient pas automatiquement faux pour autant ; c’est la recommandation finale qui doit être séparée. Aucun contrôle d’âge/fraîcheur ne rend cet avis applicable à un signal courant.

**Correction :** modèle figé avant le signal noté, contrôle de l’instant de disponibilité des features et labels, séparation explicite de la rétrodiction in-sample et de la recommandation prospective ; pas de PRENDRE pour un signal déjà résolu ou hors fenêtre de fraîcheur.

### I04-5 — Brier et tableaux de calibration ne suffisent pas à valider les probabilités affichées

**Fichiers :** `research/stats.py::calibration_bins`, `research/study.py:163-181,295-338`, `StudyView.tsx`. **Certitude : métriques mesurées ; absence de gate/calibrateur constatée.**

Le Brier OOS et la référence au taux moyen de train sont de bonnes additions. La démo indépendante donne **Brier modèle 0,243083**, référence **0,239138**, skill **−1,65 %**. Le premier bin prédit environ **17,7 %** mais gagne **40 %** sur 50 signaux ; ce n’est pas une calibration validée.

Autre simulation à espérance de base positive mais features non prédictives : verdict **EDGE**, AUC **0,4823**, skill Brier **−0,286 %**, et amélioration moyenne du filtre **−0,08796 R**, non significative. Le texte précise que le gain du filtre n’est pas démontré, mais le gate de l’avis se contente d’EDGE : il n’exige ni gain propre au modèle, ni calibration acceptable.

Il n’y a pas de calibrateur indépendant (Platt/isotonique ou autre), d’intervalle de fiabilité par bin tenant compte de la dépendance, ni de détection OOD. Sur le vrai LogisticModel ajusté sur des entrées modestes, une entrée `[1e9,−1e9]` est scorée à presque 100 %, sans statut hors domaine.

**Correction :** distinguer avantage de base et valeur ajoutée prédictive ; rapporter l’incertitude de calibration, comparer proprement les références, calibrer sur données distinctes si nécessaire et vérifier la calibration après refit. Détecter/hors domaine ou refuser les avis pour domaines insuffisamment représentés. Ne pas présenter la fraction bootstrap positive comme une probabilité bayésienne que la vraie espérance soit positive.

### I04-6 — Monte Carlo : les permutations cassent les régimes de pertes et figent les montants

**Fichiers :** `research/robustness.py`, `client/components/backtest/RobustnessPanel.tsx`. **Certitude : contre-exemple reproduit.**

Série de 100 trades : 50 pertes de 50, puis 50 gains de 50, capital 10 000, limite 20 %. Drawdown réel de cette série : **−25 %**. Sur 1 000 permutations : médiane **−4,91 %**, percentile défavorable **−7,44 %**, pire observé **−10,84 %**, « probabilité d’atteindre la limite » **0 %**.

Ce n’est pas une erreur de calcul de permutation : c’est une autre hypothèse de génération, qui détruit précisément la persistance des pertes observée. Les montants absolus restent fixes et le Guardian n’arrête pas la permutation une fois sa limite atteinte ; les tailles recalculées au capital courant ne sont pas rejouées.

**Impact :** le résultat est une fréquence conditionnelle sous réordonnancement échangeable, pas une probabilité de drawdown futur du système. L’avertissement « les trades passés peuvent être dépassés » ne précise pas cette destruction des dépendances. L’étiquette de probabilité de vraie espérance positive est également plus forte que la fraction de moyennes bootstrap positives réellement calculée.

**Correction :** renommer les mesures conditionnelles, afficher les hypothèses d’échangeabilité et comparer des simulations par blocs/régimes ; ajouter scénarios de coûts/volatilité/pertes corrélées ; rejouer les règles de sizing et d’arrêt si une probabilité de ruine/limite du portefeuille est visée. Ne pas résumer ces permutations comme une garantie de risque.

### I04-7 — Absence de protocole archivé permettant de reproduire les affirmations chiffrées

**Fichiers :** `quant/docs/CHANGELOG.md`, `quant/docs/VALIDATION.md`, `tests/test_research.py`. **Certitude : pièces manquantes dans l’export et recherche ciblée.**

Pas de script complet ni fiche d’expériences avec seeds/réglages pour rattacher exactement les **2 856 signaux**, **1/60**, **19/30**, **30/30**. Nos résultats de bruit/pouvoir diffèrent sur des expériences explicitement définies ; ils ne réfutent pas à eux seuls les comptes annoncés, puisqu’on ignore leur protocole exact.

**Correction :** versionner un générateur indépendant du modèle évalué, toutes les seeds, distributions, définitions d’effet, tailles/effectifs effectifs, paramètres, hashes et résultats de chaque essai ; intervalles sur erreur et puissance ; réplications réservées, non choisies parce qu’elles produisent le compte souhaité. Consigner aussi les essais infructueux et la sélection des règles de verdict.

### I04-8 — Le nouveau GET de robustesse n’applique pas la borne de calculs lourds

**Fichiers :** `api/app.py:348-354`, `research/robustness.py`. **Certitude : code et formes d’allocation constatés ; saturation non exécutée.**

La création d’étude POST entre dans `heavy_job`, mais GET `/backtests/{id}/robustness` recalcule bootstrap et permutations sans ce sémaphore. Les matrices ont une taille proportionnelle à `n_boot × n_trades` et plusieurs copies sont allouées. Des GET concurrents ne sont donc pas couverts par le 429 démontré pour les créations.

**Impact :** régression du bornage de charge de la couche de recherche, même sans mutation ni compte de trading.

**Correction :** borne commune de travail et mémoire, calcul chunké, cache lié au résultat vérifié et aux paramètres, annulation/délais appropriés. Tester des requêtes concurrentes bornées sans épuiser réellement la machine.

### I04-9 — La démo de prix n’est pas un nul à incréments de moyenne conditionnelle nulle

**Fichiers :** `data/synthetic.py:27`, avertissement des prix synthétiques dans `StudyView.tsx`. **Certitude : formule du générateur vérifiée.**

Les incréments sont `Normal(0, 0.8) + 0.10*sin(index/200)`. Leur espérance conditionnelle au temps contient donc une composante déterministe prédictible ; ce n’est pas une marche à incréments identiquement distribués de moyenne nulle. L’interface affirme pourtant que tout avantage trouvé sur ces cotations synthétiques serait « du hasard ou un défaut ».

**Impact :** cette démo ne doit pas servir de contrôle universel « sans structure prédictive ». La composante ne prouve pas qu’une stratégie précise est rentable après les coûts par défaut ; elle suffit à invalider l’affirmation que toute structure détectée serait forcément une erreur. Les essais de bruit versionnés au niveau signaux utilisent un autre générateur ; en l’absence du protocole 60/30/30, rien ne permet d’attribuer le compte annoncé à l’un ou l’autre.

**Correction :** séparer clairement un générateur nul sans composante prédictible, des populations structurées/avec régimes et des scénarios à avantage planté. Nommer les hypothèses et mesurer séparément prédictibilité brute et espérance nette après coûts. Corriger l’avertissement de l’interface pour dire que les données synthétiques ne prouvent aucun avantage de marché réel.

## 7. Mineur : AUC nulle supprimée de l’intervalle

**Fichier :** `research/study.py:160`, expression `auc(...) or np.nan`. **Certitude : injection de valeur légitime reproduite.**

Une AUC de **0** est valide, mais est convertie en NaN dans les tirages bootstrap. En forçant l’utilitaire AUC à retourner 0 pour tous les tirages, l’AUC ponctuelle reste 0 et son intervalle devient `[null,null]`, au lieu de conserver des valeurs nulles au sens numérique.

**Correction :** tester explicitement `is None`, pas la vérité booléenne du nombre. Ajouter des jeux parfaits, inverses et à classe unique.

## 8. Biais temporels et limites des horizons

Aucune fuite directe confirmée dans les 12 features ni dans le scaler par fold. La validation interne des seuils est chronologique ; cependant le modèle qui fournit les scores de validation interne est ensuite réajusté sur davantage de données avant application du seuil numérique, sans calibration de ce changement d’échelle. Ce n’est pas une utilisation directe du test pour ajuster le seuil, mais sa stabilité doit être étudiée.

Les folds ultérieurs utilisent légitimement des labels des périodes précédentes une fois connus : c’est un algorithme adaptatif walk-forward. Cela ne constitue **pas** un test final fixe et scellé. Les utilisateurs peuvent voir tous les résultats et retoucher les hypothèses. La protection contre cette sélection opportuniste ne réside actuellement que dans l’avertissement et le compteur défectueux B04-1.

Le temps de sortie des labels est encore l’ouverture de la bougie qui résout le trade, alors que son high/low/close peut n’être connu qu’à sa clôture. **58 des 495 labels** de la démo ont même `entry_time==exit_time`. Sur une grille homogène, la condition stricte `t_exit < test_start` et la prochaine ouverture testée évitent souvent que cela devienne une fuite effective ; l’audit ne prétend donc pas avoir démontré une fuite générale dans chaque fold actuel. Ce contrat de temps reste impropre à une purge réutilisée sans précaution sur d’autres horizons : distinguer bougie de sortie et disponibilité du résultat.

Enfin `last=i+horizon_bars` inclut les deux extrémités : horizon 240 observe jusqu’à **241 bougies tenues**, horizon 1 jusqu’à deux. La description publique « après 240 bougies » doit être alignée avec cette convention. Les signaux proches de la fin sont écartés avant recherche de leur sortie, même si un SL/TP s’est déjà produit : c’est une troncature conservatrice de l’échantillon, pas la preuve que leur issue est réellement inconnue.

## 9. Recontrôle du socle et Git

Les sondes de l’audit antérieur ont été relancées sur cet export V0.4. Les bons correctifs B1/imports, finitude à l’entrée, garde quant Host/Origin, I8, exactitude des datasets et persistance atomique des runs restent en place ; la suite des régressions passe. **Cela ne clôt pas les réserves du contre-audit V0.3.1.**

Notamment, la collection des backtests sert encore les métriques SQLite sans vérification : **987654321** dans la liste contre **27,366839136113413** au détail vérifié, et reproduction positive pour ce détail. Les prix/P&L incohérents d’une première publication, les données brutes au SHA déclaré incorrect, le contournement de la limite de lignes CR et le contexte supervisé incomplet sont toujours reproductibles. Les modules non couverts par le fingerprint de base et les mutations Express legacy restent à traiter. L’ajout d’une couche IA ne répare pas ces fondations.

État de l’export V0.4 : **102 fichiers suivis**, **158 non suivis versionnables**, aucun ajout effectué par l’auditeur ; **99 fichiers suivis modifiés**, dont **70 seulement par fins de ligne** et **29 avec changement de contenu**. Le package source `data` n’est plus omis ; aucune dépendance, venv ou donnée runtime n’est dans l’export. Les nouveaux modules research, tests et écrans doivent être inclus explicitement dans la future série de commits.

`.env` reste suivi avec son placeholder public et message ; `.env.example` reste à versionner. Recherche de motifs de clés privées/GitHub/OpenAI/AWS/Slack sur les 260 fichiers : aucun secret actif correspondant identifié. Cela ne certifie ni l’ensemble de l’historique ni les fichiers privés ignorés. Le protocole de clone propre et le plan de préparation du contre-audit restent applicables ; ne pas mélanger ces changements avec une normalisation massive CRLF.

## 10. Actions correctives prioritaires

1. Suspendre la portée « avantage démontré / probabilité fiable / PRENDRE » tant que budget d’essais, dépendance et invalidités numériques ne sont pas traités ; conserver des résultats exploratoires clairement nommés.
2. Fermer la lecture financière non vérifiée du socle et protéger études/modèles/registres avec des artefacts vérifiés ; s’assurer que les octets servis correspondent aux preuves.
3. Fixer unités et temps : candidats versus portefeuille, disponibilité des labels, horizons et configuration supportée ; refuser les incohérences plutôt que les ignorer.
4. Préenregistrer features, hyperparamètres, sélection de seuil et famille d’essais ; réserver une période finale réellement vierge ; registre transactionnel avec budget alpha défendable.
5. Valider sur données nulles indépendantes **et dépendantes**, scénarios corrélés, coûts stressés, changements de régimes et différentes longueurs de blocs. Rapporter erreur et puissance avec leur incertitude.
6. Vérifier la valeur ajoutée/calibration OOS et la fraîcheur du scoring ; finaliser un modèle prospective plutôt qu’un avis sur une ligne de train ; effectuer un replay filtré contraint par le Guardian.
7. Ensuite seulement, tester une stratégie XAUUSD explicitement définie et consentie, sur historique réel identifié, contrat/fuseau/coûts vérifiés. Le trader pilote reste une stratégie à formaliser ; la baseline illustrative ne le remplace pas.

## 11. Limites de l’audit et livrables

Aucun test sur courtier, compte démo/réel, carnet d’ordres, ticks ou historique XAUUSD courtier vérifié. Pas de saturation volontaire, fuzzing exhaustif, panne physique, réentraînement intégral à chaque bootstrap ni preuve de validité uniforme sur toutes distributions. Les régimes simulés sont des contre-exemples contrôlés, pas des prévisions du marché. Aucune signature ni conformité réglementaire n’est certifiée.

Les probabilités de succès de simulations et leurs intervalles ne sont pas des probabilités de profit réel. Une AUC correcte ne garantit pas une espérance positive après coûts ; une espérance de base positive ne prouve pas une capacité prédictive. Les verdicts finaux ci-dessous tiennent compte de ces distinctions.

Pièces dans le même répertoire :

- Sources figées : `repo/`, `snapshot-manifest.json`, `files.txt`, `git-audit.json`.
- Sondes : `research_probes.py`, `statistical_probes.py`, `diagnostic_probes.py`, `followup_probes.py`, `nonfinite_model_probe.py`, `prior_regression_probes.py`.
- Preuves : `research-evidence.json`, `statistical-evidence.json`, `statistical-summary.json`, `counter-evidence.json`, `api-routes.json`, logs associés. Le NaN observé est conservé dans les logs bruts et marqué explicitement comme non fini dans le JSON de preuve.
- Tests : `python-tests.log`, `javascript-tests.log`, `typecheck.log`, `build.log`, `ruff.log`, `backtest-browser.log`, `browser-api-down.log`, `production-smoke.log`, `pages-tour-rerun.log`.
- Captures : `screenshots/validation.png`, `screenshots/mobile-research.png`, autres pages desktop/mobile.

Relance : définir `PYTHONDONTWRITEBYTECODE=1`, `PYTHONPATH` vers `repo/quant/src`, puis exécuter les scripts avec `repo/quant/.venv/bin/python`. Les scripts n’utilisent que des données et catalogues temporaires. L’environnement installé doit rester disponible ; une installation neuve n’a pas été certifiée par ce seul export.

## 12. Trois verdicts finaux

| Question | Verdict | Condition pour réexaminer |
|---|---|---|
| Robustesse technique du logiciel | **NO-GO comme version financièrement validée ; prototype fonctionnel** | Fermer les lectures non vérifiées, intégrité des études, contrats de configuration et garde numérique/charge. |
| Fiabilité scientifique du moteur IA | **NO-GO** | Inférence sous dépendance et essais multiples défendables, preuve indépendante de calibration/valeur ajoutée, test final vierge et scoring prospectif. |
| Analyse concluante d’une stratégie XAUUSD réelle | **NO-GO** | Conditions précédentes + règles du trader et données/contrats/coûts réels vérifiés + replay portefeuille contraint, puis validation future. |

**Aucun ordre ni connexion courtier n’a été exécuté. Les PASS techniques permettent de continuer la recherche et de préserver le travail ; ils ne justifient ni « avantage démontré » sur une stratégie réelle ni une recommandation de trading fiable en l’état.**
