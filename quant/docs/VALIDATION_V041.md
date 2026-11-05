# Validation V0.4.1 — corrections des audits Codex et campagne statistique avant/après

Date : 2026-11-04 → 2026-11-05. Logiciel 0.4.1, moteur inchangé (`backtest-engine/0.3.1`).
Simulation uniquement : aucun ordre réel ou démo, aucune connexion courtier, aucun déploiement, aucun commit ni push.

Audits traités :
- `docs/audits/codex-audit-v04-lhxtu170/CODEX_AUDIT_V040_QUANT_IA.md` : audit V0.4.0, B04-1 à B04-3 et I04-1 à I04-9 ;
- `docs/audits/codex-counter-v031-d7c34xx6/CODEX_CONTRE_AUDIT_V031.md` : contre-audit V0.3.1, N1 à N10.

## 0. Synthèse

| Question | Réponse courte |
|---|---|
| Le défaut signalé par Codex (B04-2) est-il réel ? | **Oui.** Sur son contre-exemple (C1), la v0.4.0 conclut « avantage » dans **17,6 %** des cas [15,3 ; 20,1] au lieu de ≤ 5 % (p ≈ 2·10⁻⁴⁷), alors que l'effet réel est ≤ 0. |
| La correction pré-déclarée le corrige-t-elle ? | **Oui sur C1 : 0,0 %** [0 ; 0,4]. Aucun dépassement significatif de 5 % sur les 13 nuls pré-enregistrés valides. C1 et les rafales sont corrigés par **refus de conclure** (`INSUFFICIENT`), pas par une décision juste. |
| Garde-t-elle de la puissance ? | **Oui sur données peu dépendantes** : +0,20 R détecté à 95,7 % (93,3 % avant) et +0,10 R à 72,3 % (62,7 %). **Non sur signaux en rafales** : 0 % (23 % avant), faute d'unités indépendantes en 120 jours. |
| Résultats corrélés par des régimes d'un jour (nul aveugle N11b, complémentaire) ? | **Échec : 8,0 %** [6,2 ; 10,2], dépassement significatif de 5 %. La v0.4.0 faisait 3,8 % sur les mêmes données (§5.5). |
| Le taux nominal annoncé est-il tenu ? | **Non, pas exactement.** Le seuil de conception est de 3,04 %. Les taux observés valent ≈ 4,2 à 5,9 % sur les nuls indépendants. L'intervalle bootstrap est trop étroit d'environ 10 à 20 % **dans le pipeline**, alors qu'il est calibré sur données iid isolées (§5.7). Le logiciel ne prétend donc contrôler que la référence de 5 %, et seulement sur les scénarios testés. |
| « Avantage démontré » | **Retiré.** Il est remplacé par « Indice d'avantage hors échantillon — expérimental ». |

Mon protocole contenait une erreur de conception, constatée et documentée (écart 4) : N10 et N11 n'étaient pas des
nuls pour la statistique testée (§5.4).

## 1. Preuves sécurisées

- **Rapports Codex** : les manifestes ont été vérifiés (7/7 et 9/9 fichiers).
  - Copie en dépôt dans `docs/audits/codex-counter-v031-d7c34xx6/` et `docs/audits/codex-audit-v04-lhxtu170/`, sans
    `.env` ni instantané de dépôt.
  - `docs/audits/SHA256SUMS_2026-11-04.txt` couvre 204 fichiers, 0 différence avec les originaux.
- **Copie intégrale** (tar) dans `~/traider-pro-backups/2026-11-04-codex-audits/` :
  - `codex-audit-v04-lhxtu170.tar`, SHA-256 `28ca45a3…` ;
  - `codex-counter-v031-d7c34xx6.tar`, SHA-256 `4c66df28…` ;
  - `SHA256SUMS.txt`.
- **Sauvegarde de l'arbre avant V0.4.1** dans `~/traider-pro-backups/2026-11-04-pre-v0.4.1/` :
  - `worktree.tar` : 466 fichiers suivis et non suivis, SHA-256 `e9e08d69…` ;
  - `SHA256SUMS.txt`, `git-status.txt`, `HEAD.txt` (`2dedf6c`) et `staged.txt` (vide) ;
  - restauration vérifiée : 0 échec.
- **Preuves de reproduction V0.4** : `~/traider-pro-backups/2026-11-04-v04-evidence/`, détaillées dans
  `REPRODUCTION_V04.md`.

## 2. Décisions numériques (B04-3)

**Reproduction.** Tests écrits d'abord, exécutés sur la copie figée v0.4.0 :
`tests/test_v041_research_safety.py`, 15 échecs sur 17, journal dans
`research_campaign/results/repro_tests/v0.4.0_frozen.log`. En v0.4.0, un modèle produisant des NaN pouvait conduire
à « PRENDRE ».

**Correction.**

| Frontière | Comportement v0.4.1 |
|---|---|
| Modèle (`stats.py`) | `LogisticModel.fit` refuse les entrées non finies, les étiquettes non binaires et l'absence d'une des deux classes. Il calcule sous `np.errstate(raise)`, contrôle chaque pas de Newton et lève `ModelError` en cas de non-convergence. `predict_proba` exige des sorties finies dans [0, 1]. |
| Évaluation (`study.py`) | Toute `ModelError`, exception ou probabilité invalide donne le verdict **`INVALID`**, jamais `EDGE`. Les valeurs descriptives non finies sont listées dans `numerical_issues`. |
| Avis | Seuls trois avis existent : « FAVORABLE — EXPÉRIMENTAL », « IGNORER » et « NE PAS TRADER ». Toute porte non franchie, avis inconnu compris, donne « NE PAS TRADER » avec ses raisons. « PRENDRE » n'existe plus. |
| API et stockage | Une étude dont le verdict ne se re-dérive pas de ses chiffres est refusée (§3). |
| Interface | Un code d'avis inconnu s'affiche « NE PAS TRADER » (`StudyView.spec.tsx`). |

Tests : 19 dans `test_v041_research_safety.py` (NaN, overflow, exception, AUC nulle conservée, configurations non
modélisées, 429) et 4 dans `StudyView.spec.tsx`.

## 3. Intégrité des études (I04-1)

**Intégrité du fichier**, mêmes garanties que les runs de backtest :
- **Format** `ato-study/2` : le conteneur est le JSON canonique de `{"format", "sha256", "study"}`, avec
  `sha256 = SHA-256(JSON canonique du corps)`.
- **Lecture stricte** :
  - les octets doivent être exactement canoniques ;
  - l'empreinte doit correspondre ;
  - l'identité doit concorder : `id(identity) == study_id == nom du fichier` ;
  - **contrôle sémantique** : le verdict et l'avis sont recalculés à partir des chiffres stockés. Une falsification
    ré-empreintée est détectée (test dédié).
- **Publication et protection** : `os.link` sans écrasement, puis fichier en lecture seule (0444). Une étude altérée
  donne un 409 via l'API ; dans la liste, elle est « refusée », sans chiffres.
- **Identification** : le corps porte l'identifiant et le SHA-256 du jeu de données, les variables, la stratégie et ses
  paramètres, les coûts, la version logicielle et `research_code_hash`.
- **Registre d'essais** :
  - `studies/registry.jsonl`, append-only, chaîné : chaque ligne contient `prev`, `entry` et `hash` ;
  - verrou `fcntl` sur `registry.lock` ;
  - une étude supprimée ou corrompue compte toujours ;
  - si le registre est altéré, aucune nouvelle étude n'est possible (409) tant qu'un humain n'a pas examiné le
    registre.

**Reproductibilité du calcul**, vérifiée séparément :
- même entrée, même identifiant, même octets : test `test_research.py` ;
- graine du bootstrap dérivée de l'identifiant ;
- empreinte du code de recherche dans l'étude ;
- reproduction exacte de l'étude d'origine v0.4.0 avec sa graine d'origine : `REPRODUCTION_V04.md` §8.

Non couvert : pas de signature cryptographique. Les empreintes détectent une altération, elles ne prouvent pas
l'auteur.

## 4. Évaluation temporelle (I04-4, N9)

- **Disponibilité d'un résultat** : `labels.available_time` correspond à la clôture de la bougie de sortie. Avant,
  c'était l'ouverture (N9, côté recherche). Les purges et l'entraînement utilisent cette colonne.
- **Rôles des signaux**, affichés dans l'avis :
  - « entraînement » : le résultat a servi à l'apprentissage ;
  - « résolu » : le résultat est connu ;
  - « non exploitable » ;
  - « nouveau » : le résultat est encore inconnu.

  Seul un signal « nouveau » reçoit un avis. Le modèle de l'avis est entraîné **uniquement** sur les résultats
  disponibles avant l'instant de décision. Un signal d'entraînement n'est jamais présenté comme une prévision
  indépendante.
- **Seuil du filtre** : il est choisi sur une tranche de validation interne, dont les résultats sont disponibles avant
  le test. Le nombre de signaux de validation est enregistré pour chaque fenêtre.
- **Étiquettes qui se chevauchent** : les signaux hors échantillon dont les fenêtres de résultat se recouvrent forment
  une seule unité d'inférence (§5.2).
- **Hors domaine** : l'avis est refusé si les variables d'un signal sortent de l'étendue d'entraînement (marge 0,5 σ).
- **Restant** : le journal du moteur garde `exit_time` = ouverture de la bougie de sortie, car le moteur n'a pas été
  modifié faute de défaut de calcul démontré. Ce point est documenté dans `KNOWN_LIMITATIONS.md`.

## 5. Campagne statistique (B04-1, B04-2, I04-7)

Dossier `quant/research_campaign/`. Le protocole `PROTOCOL.md` a été scellé le 2026-11-04 à 13:32:07 UTC (SHA-256 au
scellement `11d013bf…`, enregistrement dans `PROTOCOL.seal.txt`). Il contient quatre écarts datés (§9 du protocole) ;
sa version finale a pour SHA-256 `0163eb41…`.

### 5.1 Plan pré-enregistré
- **Nul exact** : marche aléatoire symétrique sur réseau (pas 0,125, binaire exact). Les hauts et bas sont les vrais
  extrêmes et les barrières sont des multiples du réseau, d'où E[R] = 0 exactement, sans coûts.
- **Scénarios** : 22.
  - C0 et C1 : générateurs exacts de Codex.
  - N1 à N3 : densités de signaux.
  - N4, N5 et N9 : rafales de 10, 60 et 30 signaux.
  - N6 : règle de momentum causale.
  - N7 : volatilité calme/stress.
  - N8 : volatilité stochastique.
  - N10 et N11 : résultats « corrélés ».
  - E1 : chaîne applicative complète via `run_edge_study`, avec catalogue, stratégie baseline réelle, persistance et
    règle α.
  - S1 : 10 analyses du même historique.
  - P1 à P7 : puissance, avec avantage injecté de +0,05 à +0,20 R, en rafales, avec volatilité stochastique, rare ou
    conditionnel.
- **Réplications** : 1 000 (Codex), 800 (nuls), 150 (S1), 300 (puissance).
- **Graines** : `SeedSequence([20261104, indice, réplication])`.
- **Critère** :
  - référence 5 % ; Clopper–Pearson à 95 % ;
  - test binomial exact unilatéral, avec Bonferroni K = 15 (p < 0,00333) ;
  - acceptation d'une correction : aucun nul en dépassement et puissance P3 ≥ 80 %.
- **Corrections fixées avant les résultats** : H1 (inférence par grappes) et H2 (dépense sommable), §5.2.
- **Phases et code évalué** :

  | Phase | Code | `research_code_hash` | Arbre source | Durée |
  |---|---|---|---|---|
  | « avant » | copie figée v0.4.0 | `f9055832e70d0f32` | `c3ed1684…` | 30 750 s |
  | « après » | copie figée v0.4.1 | `5e6a8f926021b343` | `780f8675…` | 8 806 s |

  - Mêmes graines et même calibration de puissance (`results/before/calibration.json`) dans les deux phases.
  - La phase « avant » a partagé la machine avec les tests et parcours navigateur, d'où sa durée plus longue.
  - Le code de travail est identique à la copie figée v0.4.1 (`diff -rq` vide).
  - Ajout postérieur (2026-11-05) : `ea_audit/` et sa route dans `api/app.py`. Ils sont hors `research/`, et
    `research_code_hash` est inchangé (`5e6a8f926021b343`) ; la campagne porte donc toujours sur le code de
    recherche en service. Voir `docs/knowledge/KB-001`.

### 5.2 Corrections pré-déclarées
- **H1** (`research/inference.py`, méthode `overlap-clusters-pw`) :
  - unités = grappes de chevauchement : un signal ouvre une nouvelle unité si son entrée est ≥ l'instant où tous les
    résultats de l'unité courante sont disponibles ;
  - bootstrap circulaire par blocs sur la suite des unités, longueur Politis–White 2004 avec la correction de 2009,
    bornée à [1, min(3√n, n/3)] ;
  - moyenne filtrée en estimateur de ratio ;
  - `INSUFFICIENT` sous 100 unités hors échantillon ou 50 unités retenues ;
  - `EDGE` si le quantile α unilatéral de la moyenne filtrée est > 0.
- **H2** (`research/registry.py`) : α_m = 0,05·6/(π²m²), dont la somme sur m est ≤ 0,05. Valeurs : α₁ = 3,04 %,
  α₂ = 0,76 %. Famille = type + instrument + unité de temps.
- **Activation** : après le diagnostic, par `ACTIVE = CLUSTERS` et `USE_SPENDING = True`, sans aucun réglage d'après
  les résultats.

### 5.3 Résultats bruts : avant / après (même scénarios, mêmes graines)

Fichiers :
- par réplication : `results/before/*.jsonl` et `results/after/*.jsonl` ;
- résumés : `results/summary_*.json`, `results/REPORT_*.md` et `results/COMPARISON.md` ;
- manifestes : `results/*/manifest.json`, avec les versions, `pip freeze`, les empreintes des sorties et les durées.

| Scénario | Nature | Avant : EDGE [IC 95 %] | Après : EDGE [IC 95 %] | Après : verdicts |
|---|---|---|---|---|
| C0 Codex indépendant | nul | 3,4 % [2,4 ; 4,7] | 5,4 % [4,1 ; 7,0] | — |
| **C1 Codex groupes de 100** | nul | **17,6 % [15,3 ; 20,1] — dépassement** | **0,0 % [0 ; 0,4]** | 1 000 `INSUFFICIENT` (15 unités) |
| N1 signaux rares | nul | 4,1 % [2,9 ; 5,7] | 5,9 % [4,3 ; 7,7] | 41 `INSUFFICIENT` |
| N2 densité moyenne | nul | 2,4 % [1,4 ; 3,7] | 4,9 % [3,5 ; 6,6] | — |
| N3 dense | nul | 2,2 % [1,3 ; 3,5] | 5,1 % [3,7 ; 6,9] | — |
| N4 rafales de 10 | nul | 3,0 % [1,9 ; 4,4] | 0,0 % [0 ; 0,5] | 800 `INSUFFICIENT` (66 unités) |
| N5 rafales de 60 | nul | 3,8 % [2,5 ; 5,3] | 0,0 % [0 ; 0,5] | 800 `INSUFFICIENT` (30 unités) |
| N6 règle momentum | nul | 3,2 % [2,1 ; 4,7] | 4,8 % [3,4 ; 6,5] | — |
| N7 volatilité calme/stress | nul | 2,8 % [1,7 ; 4,1] | 5,5 % [4,0 ; 7,3] | — |
| N8 volatilité stochastique | nul | 2,4 % [1,4 ; 3,7] | 4,2 % [3,0 ; 5,9] | — |
| N9 vol. stoch. + rafales de 30 | nul | 5,0 % [3,6 ; 6,7] | 0,0 % [0 ; 0,5] | 800 `INSUFFICIENT` (52 unités) |
| E1 chaîne complète | nul | 3,0 % [1,9 ; 4,4] | 3,6 % [2,4 ; 5,2] | — |
| S1 10 analyses, règle de l'application | nul (famille) | 7,3 % [3,7 ; 12,7] | 4,7 % [1,9 ; 9,4] | — |
| S1 sans correction (référence) | — | 13,3 % [8,3 ; 19,8] | 12,0 % [7,3 ; 18,3] | — |
| N10 « corrélé » 2 h | **mal spécifié** (§5.4) | 26,5 % | 36,8 % | — |
| N11 « corrélé » 1 j | **mal spécifié** (§5.4) | 72,5 % | 83,7 % | 4 `ERROR` (prix ≤ 0) dans chaque phase |
| P1 +0,05 R | puissance | 30,3 % [25,2 ; 35,9] | 39,7 % [34,1 ; 45,4] | — |
| P2 +0,10 R | puissance | 62,7 % [56,9 ; 68,2] | 72,3 % [66,9 ; 77,3] | — |
| **P3 +0,20 R** | puissance | **93,3 %** [89,9 ; 95,9] | **95,7 %** [92,7 ; 97,7] | — |
| **P4 +0,10 R en rafales de 20** | puissance | 23,0 % [18,4 ; 28,2] | **0,0 %** [0 ; 1,2] | 300 `INSUFFICIENT` (48 unités) |
| P5 +0,20 R, vol. stochastique | puissance | 93,0 % | 96,0 % | — |
| P6 +0,10 R, signaux rares | puissance | 21,7 % | 28,0 % | 8 `INSUFFICIENT` |
| P7 avantage conditionnel 12-14 h | puissance | 75,0 % | 80,7 % | — |

Notes sur le tableau :
- Les 4 `ERROR` de N11 viennent du générateur : la marche descend sous 0 et le logiciel refuse à juste titre des prix
  ≤ 0. Ils sont comptés et publiés, sans être comptés comme faux positifs.
- Effets réalisés (moyenne des réplications, publiés dans `REPORT_*.md`) :
  - **P1** : +0,048 R sur l'ensemble et +0,093 R sur les signaux filtrés ;
  - **P3** : +0,201 R sur l'ensemble et +0,208 R sur les signaux filtrés.

**Décisions selon les critères :**
- **Défaut établi avant** : oui, par C1. La signature prévue (C1, N4, N5, N9, N10, N11) n'est observée qu'en partie :
  les rafales N4, N5 et N9 ne dépassaient pas 5 %.
- **Acceptation tel qu'écrit** (K = 15) : **non remplie**, à cause de N10 et N11 (§5.4).
- **Acceptation sur les 13 nuls valides** (lecture décidée après les résultats « avant », écart 4b) : **remplie**,
  avec aucun dépassement et une puissance P3 de 95,7 % ≥ 80 %.

### 5.4 Erreur de conception de N10 et N11 (constatée)
- **Ce que garantissaient ces scénarios** : E[R] = 0 pour la moyenne **non filtrée**. Mesures : −0,0000 R et
  −0,0014 R.
- **Ce qu'ils ne garantissaient pas** : E[R] = 0 pour la moyenne **filtrée**, celle que juge le verdict.
  - Les variables « alignées » sont multipliées par le sens du signal ; le régime de dérive persistant est donc lisible
    dans le momentum passé.
  - Hors échantillon, la moyenne filtrée vaut **+0,095 R** [+0,089 ; +0,101] (N10) et **+0,213 R** [+0,206 ; +0,219]
    (N11), avec une AUC de 0,55 et 0,61.
- **Conclusion** : ce sont des détections d'un avantage conditionnel réel, pas des faux positifs. La méthode corrigée
  détecte d'ailleurs davantage (36,8 % et 83,7 %).
- **Remplacement** : écart 4c, ci-dessous.

### 5.5 Expériences complémentaires (écart 4c, déclarées avant la phase « après »)
- **Construction** : N10b et N11b reprennent les données, signaux et résultats de N10/N11 (mêmes graines, vérifié à
  l'octet sur une réplication). Les lignes de variables sont permutées entre signaux : la prévisibilité est détruite,
  la corrélation temporelle des résultats est conservée.
- **Critère** : 800 réplications, Bonferroni K = 2.

| Scénario | v0.4.0 (legacy) : EDGE [IC 95 %] | v0.4.1 (grappes) : EDGE [IC 95 %] | Effet filtré vrai |
|---|---|---|---|
| N10b : résultats corrélés, régimes ~2 h, aveugle | 3,5 % [2,3 ; 5,0] | 5,8 % [4,2 ; 7,6], p = 0,18 | +0,005 R [+0,000 ; +0,009] |
| **N11b : résultats corrélés, régimes ~1 jour, aveugle** | 3,8 % [2,6 ; 5,3] | **8,0 % [6,2 ; 10,2], p = 0,00017 : DÉPASSEMENT SIGNIFICATIF** | +0,000 R [−0,005 ; +0,005] |

**La méthode v0.4.1 échoue sur N11b, et elle y fait moins bien que la v0.4.0 sur les mêmes données.**

- **Mécanisme mesuré.** L'écart-type standardisé, qui vaut 1 si la méthode est calibrée, s'établit à 1,34 en v0.4.1
  contre 1,13 en v0.4.0.
  - La longueur de bloc Politis–White médiane vaut 2 unités. La corrélation due à un régime d'un jour est faible à
    chaque décalage, sous le seuil de significativité de la règle de White (2·√(log₁₀ n / n) ≈ 0,07 pour
    n ≈ 500 unités). Elle se cumule pourtant sur des dizaines d'unités.
  - Les blocs fixes de la v0.4.0 (≈ 17 signaux) en couvraient une partie, avec en outre un niveau nominal plus bas
    (2,5 % contre 3,04 %).
- **Facteurs qui s'ajoutent** : l'étroitesse conditionnelle propre au pipeline (§5.7, facteur ≈ 1,1 sur les nuls
  indépendants) et cette dépendance de régime non capturée.
- **Pas de correction ajustée ici.** Un plancher de longueur de bloc, ou des blocs en temps calendaire plutôt qu'en
  unités, sont des corrections de principe possibles. Les choisir maintenant d'après N11b serait ajuster la méthode sur
  la campagne : elles sont renvoyées à une nouvelle campagne pré-enregistrée (handoff Codex, point 1).
- **Portée** : des régimes de tendance de l'ordre d'une journée sont plausibles sur XAUUSD. Ce défaut touche donc
  directement l'usage réel.

### 5.6 Sensibilité de H1 à la longueur de bloc (écart 4d, descriptive)

Relancée après correction d'un bug de mon script (écart 5 : l'échelle se composait d'une tâche à l'autre ; résultats
invalides conservés à part, non utilisés). Bloc Politis–White médian d'origine : 1 à 2 unités. 300 réplications.

| Scénario | × 0,5 (bloc médian 1) | × 1 (campagne) | × 2 (bloc médian 4) |
|---|---|---|---|
| N5 rafales de 60 | 0,0 % (tous `INSUFFICIENT`) | 0,0 % | 0,0 % |
| N9 vol. stoch. + rafales de 30 | 0,0 % (tous `INSUFFICIENT`) | 0,0 % | 0,0 % |
| N11 (avantage conditionnel réel) | 82,6 % | 83,7 % | 82,6 % |
| **N11b (nul aveugle, régimes ~1 j)** | **7,7 %** [4,9 ; 11,3] | **8,0 %** | **6,7 %** [4,1 ; 10,1] |

Ce qu'on en tire :
- La conclusion ne dépend pas d'un réglage fin de la longueur de bloc.
- Sur N11b, doubler les blocs ne ramène pas le taux sous 5 % de façon sûre : la dépendance d'un jour réclame des
  blocs bien plus longs que ce que la règle de White détecte.
- Ces résultats ne servent pas à choisir une longueur.

### 5.7 Pourquoi les taux dépassent le niveau de conception (diagnostic)

Sur les nuls indépendants de la phase « après », le taux d'`EDGE` vaut 4,2 à 6,2 % pour un niveau unilatéral de
conception α₁ = 3,04 %. L'écart est significatif contre 3,04 % sur 6 des 8 nuls (p < 0,005), mais compatible avec la
référence de 5 % (p ≥ 0,15).

**Mesure.** Rapport entre la dispersion réelle de la moyenne filtrée d'une réplication à l'autre et l'écart-type
implicite du bootstrap :

| | Avant (legacy) | Après (grappes) |
|---|---|---|
| Écart-type de (moyenne / écart-type bootstrap), 1 attendu | 1,01 à 1,09 | 1,04 à 1,16 |

**Test isolé.** Même calcul sur données iid, hors pipeline (300 réplications, n = 150 ou 1 500, prise aléatoire de
10 % ou 50 %) :

| Méthode | Écart-type standardisé | Rejet | Niveau nominal |
|---|---|---|---|
| Legacy | 0,97 à 1,02 | 1,0 à 1,7 % | 2,5 % |
| Grappes | 0,95 à 0,99 | 1,7 à 3,0 % | 3,04 % |

**Le bootstrap est donc calibré en lui-même ; l'excès vient du pipeline.**

**Cause la plus probable (non démontrée formellement).** Le bootstrap est **conditionnel** : il traite comme fixes les
signaux retenus. Or, dans le walk-forward ancré, les résultats d'une fenêtre de test entrent dans l'apprentissage des
fenêtres suivantes, et la sélection de chaque fenêtre dépend donc des résultats des précédentes. Les mêmes symptômes
sont observés sur tous les nuls :
- un léger décalage positif de la moyenne filtrée : +0,003 R en moyenne, z combiné ≈ 3,9 ;
- une AUC regroupée légèrement < 0,5 : z combiné ≈ −10,8, un effet prudent.

**Correction de principe.** Rééchantillonner la procédure complète (ré-entraînement dans chaque tirage) ou étalonner
le seuil sur des nuls. Elle n'a **pas** été appliquée : elle n'était pas pré-déclarée, et la choisir maintenant
reviendrait à ajuster la méthode sur cette campagne. C'est le premier point du handoff Codex.

### 5.8 Échecs expliqués
- **P4 : 0 % de puissance.** 592 signaux, mais seulement 48 unités indépendantes en 120 jours. La règle « ≥ 100
  unités » refuse de conclure, et aucune méthode honnête ne peut détecter +0,10 R avec 48 résultats indépendants.
  - L'ancien 23 % reposait sur un comptage de signaux qui ne sont pas indépendants : l'ancienne méthode conclut
    pareillement sur C1, où l'effet est nul.
  - Pour une stratégie en rafales, il faut un historique beaucoup plus long. L'interface affiche le nombre d'unités
    indépendantes.
- **C1, N4, N5 et N9 à 0 %** : par refus (`INSUFFICIENT`), pas par une décision « pas d'avantage ». C'est le
  comportement voulu (« on ne sait pas »), et non une preuve de calibration sur ces dépendances.
- **S1** : la règle de l'application ramène le risque familial de 13,3 % / 12,0 % sans correction à 7,3 %, puis 4,7 %.
  Avec 150 historiques, l'intervalle reste large ([1,9 ; 9,4] %).

## 6. Conclusions présentées à l'utilisateur

- Tout résultat de la page Validation porte un bandeau **« expérimental »** (`study-experimental`).
- `EDGE` s'affiche « Indice d'avantage hors échantillon — expérimental » ; la liste l'affiche « indice
  (expérimental) ».
- `NEGATIVE` s'affiche « Perte attendue mesurée ».
- **Scores** : présentés comme « non calibrés » ; la calibration est marquée « non validée » ; aucune probabilité
  n'est affichée comme fiable.
- **Unités** : le nombre d'unités indépendantes et la règle de décision réellement appliquée sont affichés.
- **Signaux candidats et performance exécutable** : la distinction est rappelée dans l'étude et dans
  `VALIDATION.md`.
- **Robustesse** : le Monte Carlo est requalifié en « mesure conditionnelle, pas une probabilité de drawdown ». La
  part des tirages > 0 n'est pas une probabilité.
- **Données synthétiques** : un avertissement corrigé (I04-9) précise qu'elles peuvent contenir des régularités
  artificielles et ne prouvent rien.

## 7. Anomalies : état après V0.4.1

Gravité selon Codex. « Corrigé » = reproduit par un test qui échouait sur la v0.4.0, puis passe en v0.4.1.

### 7.1 Audit V0.4.0

| ID | Gravité | Sujet | État | Preuve |
|---|---|---|---|---|
| B04-1 | Bloquant | Bonferroni non sommable, famille contournable | **Corrigé** (H2) ; S1 7,3 % → 4,7 % | registre, `test_research.py`, campagne S1 |
| B04-2 | Bloquant | Bootstrap ignorant les dépendances | **Corrigé sur le chevauchement** (C1 17,6 % → 0 %) ; **reste** l'étroitesse conditionnelle (§5.7) | campagne, `test_v041_inference.py` |
| B04-3 | Bloquant | NaN → « PRENDRE » | **Corrigé** | `test_v041_research_safety.py` |
| I04-1 | Important | Études non vérifiées | **Corrigé** | idem (falsification, ré-empreinte, registre) |
| I04-2 | Important | Candidats ≠ portefeuille | **Non corrigé** ; distinction affichée | — (v0.4.2) |
| I04-3 | Important | Configurations non modélisées | **Corrigé** (refus) | 5 cas paramétrés |
| I04-4 | Important | Avis sur un signal appris | **Corrigé** | rôles, modèle « à la date de décision » |
| I04-5 | Important | Probabilités non calibrées | **Partiel** : libellés et porte hors domaine ; pas de calibrateur | `StudyView.spec.tsx` |
| I04-6 | Important | Monte Carlo échangeable | **Partiel** : requalifié ; pas de simulation par blocs ni de rejeu du sizing | — |
| I04-7 | Important | Protocole non archivé | **Corrigé** : `REPRODUCTION_V04.md` et campagne archivée | — |
| I04-8 | Important | GET robustesse hors `heavy_job` | **Corrigé** (429) | test 429 |
| I04-9 | Important | Démo non nulle | **Partiel** : avertissement corrigé, nul exact séparé ; générateur de démo inchangé | — |
| Mineur | Mineur | AUC nulle supprimée | **Corrigé** | test AUC = 0 |

### 7.2 Contre-audit V0.3.1 (les 6 anomalies PARTIEL sur 17)

B2, B3, I2, I3, I4 et I7 correspondent à N1 à N10. Classement par gravité, données et sécurité d'abord.

| ID | Gravité | Domaine | État | Test (échoue en v0.4.0, passe en v0.4.1) |
|---|---|---|---|---|
| N1 | Bloquant | Intégrité des données | **Corrigé** : la collection ne sert que des runs vérifiés ; les autres sont « refusés » sans chiffres | `test_n1_*` (2) |
| N2 | Important | Intégrité financière | **Corrigé** : prix, PnL, commission, equity, R et chronologie recalculés | `test_n2_*` |
| N3 | Important | Séparation temporelle | **Corrigé** : embargo négatif refusé | `test_n3_*` |
| N10 | Important | Sécurité API | **Corrigé** : garde Express Host, Origin et `X-ATO-Request` | `server/localGuard.spec.ts` (3 échecs sur 5 avant) |
| N4 | Important | Bornes d'entrée | **Corrigé** : CR compté | `test_n4_*` |
| N5 | Important | Contrôle du risque | **Corrigé** : attestation `request_policy` par requête | `test_n5_*` |
| N6 | Important | Reproductibilité | **Corrigé** : `validation_fingerprint` | `test_n6_*` |
| N7 | Important | Intégrité des données | **Corrigé** : SHA-256 de la preuve brute vérifié | `test_n7_*` |
| N8 | Mineur | Provenance | **Corrigé** | `test_n8_*` |
| N9 | Important (futurs labels) | Temps | **Partiel** : `available_time` côté recherche ; journal du moteur inchangé | `test_label_outcomes_are_available_only_at_the_close_of_the_exit_bar` |

Les 11 autres anomalies de V0.3.1 restent au statut **PASS** de Codex. Les sondes V0.3.1 (14/14) repassent ;
elles n'ont pas été ré-auditées au-delà.

## 8. Tests : avant / après

| Suite | v0.4.0 (avant) | v0.4.1 (après) |
|---|---|---|
| pytest | 232 passés | **264 passés** |
| Nouveaux tests Python sur v0.4.0 figée | 24 sur 26 en échec : 15 sur 17 (sécurité recherche) et 9 sur 9 (N1–N8) | tous passent |
| ruff | OK | OK |
| Sondes Codex V0.3.1 | 14/14 | 14/14 |
| vitest | — | **41/41** (9 fichiers) |
| `localGuard.spec.ts` sur l'ancien serveur | 3 sur 5 en échec | 5/5 |
| typecheck (strict) | 0 erreur | 0 erreur |
| build | OK | OK |
| Parcours navigateur `pages-tour` | 38/38 | 38/38 |
| `backtest-flow` | 23/23 | 23/23 |
| `api-down` | 3/3 | 3/3 |
| `production-smoke` | 9/9 | 9/9 |

Journaux de reproduction : `research_campaign/results/repro_tests/`.

## 9. Fichiers modifiés (par rapport à `~/traider-pro-backups/2026-11-04-pre-v0.4.1/SHA256SUMS.txt`)

**Modifiés (27)** :
- `client/components/backtest/RobustnessPanel.tsx`
- `client/components/research/StudyView.tsx`
- `client/lib/settingsContext.tsx`
- `client/pages/Dashboard.tsx`
- `client/pages/Research.tsx`
- `e2e/backtest-flow.mjs`
- `quant/docs/CHANGELOG.md`
- `quant/docs/KNOWN_LIMITATIONS.md`
- `quant/docs/ROADMAP.md`
- `quant/docs/VALIDATION.md`
- `quant/pyproject.toml`
- `quant/src/ai_trader_optimizer/__init__.py`
- `quant/src/ai_trader_optimizer/ai/validation.py`
- `quant/src/ai_trader_optimizer/api/app.py`
- `quant/src/ai_trader_optimizer/backtest/codehash.py`
- `quant/src/ai_trader_optimizer/research/__init__.py`
- `quant/src/ai_trader_optimizer/research/labels.py`
- `quant/src/ai_trader_optimizer/research/robustness.py`
- `quant/src/ai_trader_optimizer/research/stats.py`
- `quant/src/ai_trader_optimizer/research/study.py`
- `quant/src/ai_trader_optimizer/services.py`
- `quant/src/ai_trader_optimizer/storage/catalog.py`
- `quant/src/ai_trader_optimizer/storage/integrity.py`
- `quant/tests/test_research.py`
- `server/index.ts`
- `server/settings.spec.ts`
- `shared/quant-api.ts`

**Nouveaux, hors campagne (10)** :
- `client/components/research/StudyView.spec.tsx`
- `docs/CODEX_HANDOFF_V041.md`
- `quant/docs/VALIDATION_V041.md`
- `quant/src/ai_trader_optimizer/research/inference.py`
- `quant/src/ai_trader_optimizer/research/registry.py`
- `quant/tests/test_v041_inference.py`
- `quant/tests/test_v041_research_safety.py`
- `quant/tests/test_v041_v031_partials.py`
- `server/localGuard.spec.ts`
- `server/middleware/localMutationGuard.ts`

**Nouveaux, campagne** : `quant/research_campaign/` :
- `PROTOCOL.md`, `PROTOCOL.seal.txt`, `scenarios.py`, `run_campaign.py`, `analyze.py`, `run_supplement.py` ;
- `frozen/v0.4.0` et `frozen/v0.4.1`, avec leurs `SHA256SUMS` ;
- `results/`.

**Documentation** : `quant/docs/VALIDATION_V041.md` (nouveau), `VALIDATION.md`, `CHANGELOG.md`,
`KNOWN_LIMITATIONS.md`, `ROADMAP.md` et `docs/CODEX_HANDOFF_V041.md` (nouveau).

Aucun fichier supprimé. Fins de ligne préservées : CRLF pour les fichiers suivis qui l'étaient, LF pour les nouveaux.

## 10. Reproduire

```bash
cd quant
.venv/bin/python -m pytest -q
.venv/bin/python research_campaign/run_campaign.py --phase before --src research_campaign/frozen/v0.4.0/src --workers 6
.venv/bin/python research_campaign/run_campaign.py --phase after --src research_campaign/frozen/v0.4.1/src --workers 6 \
    --calibration research_campaign/results/before/calibration.json
.venv/bin/python research_campaign/run_supplement.py --part blind --src research_campaign/frozen/v0.4.0/src --tag v0.4.0
.venv/bin/python research_campaign/run_supplement.py --part blind --src research_campaign/frozen/v0.4.1/src --tag v0.4.1
.venv/bin/python research_campaign/run_supplement.py --part sensitivity --src research_campaign/frozen/v0.4.1/src --tag v0.4.1
.venv/bin/python research_campaign/analyze.py
(cd research_campaign/frozen && shasum -a 256 -c v0.4.1.SHA256SUMS)
```

Environnement : Python 3.12.14, numpy 2.5.4, pandas 2.3.3 (le `pip freeze` complet est dans chaque manifeste).

## 11. Verdicts

1. **Fiabilité technique : bonne dans le périmètre testé.**
   - Les défauts d'intégrité, de NaN, de temps et de sécurité signalés ont été reproduits, puis corrigés et testés.
   - Restent : le rejeu portefeuille (I04-2), le calibrateur (I04-5), le Monte Carlo par blocs (I04-6) et le journal
     du moteur (N9).
2. **Fiabilité statistique : améliorée, pas acquise.**
   - Le faux positif de Codex est supprimé. Aucun dépassement de 5 % n'est constaté sur les 13 nuls pré-enregistrés
     valides, et la puissance est conservée sur données peu dépendantes.
   - **Mais la nouvelle méthode dépasse 5 % (8,0 %) sous des résultats corrélés par des régimes d'un jour** (N11b),
     là où l'ancienne restait à 3,8 %. Aucune des deux méthodes n'est donc fiable sous toutes les dépendances
     testées.
   - Mais le niveau nominal (3 %) n'est pas tenu (≈ 5 % observé), pour une cause identifiée et non corrigée (§5.7).
   - La puissance est nulle sur les stratégies en rafales avec des historiques courts.
   - Le verdict « avantage démontré » n'est **pas** valide et a été retiré. Le verdict expérimental contrôle au mieux
     la référence de 5 %, sur les scénarios étudiés uniquement.
3. **Aptitude à des stratégies réelles sur XAUUSD : NON, pas encore pour engager de l'argent.**
   - L'outil peut servir à **écarter** des stratégies (perte mesurée, aucun indice) et à mesurer l'effet des coûts.
   - Il ne doit pas servir à autoriser une stratégie avant trois étapes :
     1. une contre-validation indépendante ;
     2. le rejeu portefeuille ;
     3. une confirmation sur une période future jamais utilisée, puis en démo.
   - Aucune donnée synthétique de cette campagne ne dit quoi que ce soit de la rentabilité d'une stratégie réelle.
