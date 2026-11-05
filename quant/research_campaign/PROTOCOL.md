# Protocole pré-enregistré : campagne statistique v0.4.0 → v0.4.1

Rédigé et scellé le 2026-11-04, **avant** toute exécution de la phase « avant ». Le pilote de temps
(`results/timing_pilot/`, 2 réplications par scénario) n'a servi qu'à mesurer les durées : ses verdicts n'ont pas été
lus. L'empreinte SHA-256 de ce fichier est enregistrée dans chaque `manifest.json`.

Toute modification ultérieure sera ajoutée en fin de document, section « Écarts au protocole », datée et justifiée.
Le texte au-dessus de cette section ne sera pas réécrit.

## 1. Questions

**Q1.** Sur des données **sans aucun avantage**, construites pour que l'espérance vaille exactement 0, à quelle
fréquence le verdict `EDGE` (« avantage démontré ») est-il rendu ? Les conditions testées couvrent :

- l'indépendance ;
- les rafales de signaux (clusters) ;
- les résultats corrélés dans le temps ;
- les régimes de volatilité ;
- les densités de signaux ;
- la chaîne applicative complète ;
- l'analyse répétée d'un même historique.

**Q2.** Sur des données **avec** un avantage injecté de taille connue, à quelle fréquence est-il détecté (puissance) ?

**Q3.** Si un défaut est établi, une correction choisie **à l'avance**, pour des raisons de principe, le corrige-t-elle
sans annuler la puissance ?

## 2. Référence et critères de décision (fixés avant les résultats)

- **Taux nominal de référence pour `EDGE` : 5 %**, à la demande du propriétaire.
  - La méthode v0.4.0 rejette quand la borne basse d'un intervalle bilatéral à 1 − α est > 0. Avec α = 0,05 pour une
    première étude, c'est un niveau unilatéral nominal de **2,5 %** : `interval()` renvoie les quantiles α/2 et
    1 − α/2 de la distribution bootstrap.
- **Estimation** du taux de faux positifs d'un scénario : k/N, avec intervalle exact de **Clopper–Pearson à 95 %**.
- **Dépassement significatif** : test binomial exact unilatéral de H0 « taux ≤ 5 % ».
  - Il est significatif si p < 0,05 / K, avec **K = 15** tests nuls : C0, C1, N1 à N11, E1, S1. C'est une correction
    de Bonferroni sur les scénarios de la campagne.
  - Sinon, l'écart à 5 % est qualifié de **fluctuation compatible avec 5 %**.
  - Seuils indicatifs avec N = 800 : un dépassement devient significatif à partir de 59/800 (7,4 %). Avec
    N = 1 000 : à partir de 70/1 000 (7,0 %).
- **Écart au niveau de conception** (diagnostic, non bloquant) : même test contre le niveau nominal propre de la
  méthode évaluée.
- **Défaut établi** si au moins un test nul présente un dépassement significatif de 5 %.
- **Puissance** : taux de `EDGE` par scénario de puissance, avec intervalle de Clopper–Pearson.
  - Une méthode corrigée n'est **acceptée** que si :
    1. aucun test nul ne dépasse significativement 5 % ;
    2. la puissance de P3 (≈ +0,20 R) est d'au moins 80 %.
  - Sinon, elle est déclarée « trop conservatrice ». Elle n'est **pas** retouchée pour passer.
- **Ce qui ne sera pas fait** :
  - choisir une méthode, une longueur de bloc ou un seuil d'après les scénarios de cette campagne ;
  - retirer une réplication ;
  - relancer un scénario jusqu'à un résultat favorable.

  Les erreurs d'exécution (`verdict = ERROR`) sont comptées et rapportées. Elles ne sont pas comptées comme des
  faux positifs, mais leur nombre est publié.

## 3. Construction des données (`scenarios.py`)

Tous les scénarios sont **sans coûts**, car le but est de tester l'inférence à la frontière E[R] = 0. Un coût ferait
baisser l'espérance et masquerait les faux positifs.

### Prix : marche aléatoire symétrique sur réseau

- Pas de ±0,125 ; prix = 3 900 + 0,125 × entier, valeurs exactement représentables.
- 120 jours calendaires, jours ouvrés seulement.
- Bougies M1 contiguës ; high et low sont les vrais extrêmes de la trajectoire.
- Stop et objectif sont des multiples entiers du pas, ce qui donne E[R] = 0 exactement (temps d'arrêt d'une
  martingale bornée).
- Deux exceptions sont documentées et **mesurées par regroupement**, pas supposées :
  - convention « stop d'abord » dans une même bougie : biais pessimiste ;
  - stops non alignés de la stratégie baseline réelle : dépassement de moins d'un pas.

### Volatilité (nombre de pas par minute)

| Modèle | Définition |
|---|---|
| `const` | 40 pas par minute |
| `switch` | Markov calme (10) / stress (160), durée moyenne 1 jour |
| `stoch` | log-AR(1), demi-vie 8 h, écart-type 0,9 |

### Signaux (session 12:00–17:00 UTC de la spécification baseline)

| Générateur | Définition |
|---|---|
| `rand` | aléatoires, densité ρ par bougie |
| `burst` | rafales de L bougies consécutives de même sens |
| `rule` | règle causale de momentum (mouvement sur 15 bougies > 2 ATR) |
| `baseline` | vraie stratégie `baseline.ema_trend_3bars` |

- Sens : pile ou face, ou régime de sens indépendant.
- Stop : 1,5 × ATR14 des bougies clôturées, arrondi au réseau. Objectif : rr × stop.

### Résultats corrélés (nuls N10 et N11)

- Régime de dérive caché M ∈ {−1, +1}, probabilité de pas 0,5 ± 0,01.
- Régime de sens D, indépendant de M.
- rr = 1 : la symétrie par réflexion garantit E[R] = 0.

### Puissance

- Le sens vaut M avec probabilité q, l'inverse sinon. Avec rr = 1, E[R] = (2q − 1) × A.
- A est mesuré sur un **pilote séparé** : 40 réplications, q = 1, graines décalées de 10⁶, moyennes regroupées
  uniquement, aucun verdict. On en déduit q = 0,5 + cible / (2A).
- La phase « après » réutilise la calibration de la phase « avant », donc les scénarios sont strictement identiques.
- L'effet réalisé (moyenne regroupée des R) est publié avec chaque résultat.

### Scénarios

| Clé | Famille | Contenu | Réplications |
|---|---|---|---|
| C0 | Codex | Bernoulli p = 0,40, 1 500 signaux indépendants (générateur exact de Codex) | 1 000 (graines 100 à 1 099) |
| C1 | Codex | Résultat commun par groupe de 100, 3 000 signaux (générateur exact de Codex) | 1 000 (graines 400 à 1 399 ; les 60 premières = celles de Codex) |
| N1 | nul | Vol. const., ρ = 0,01 | 800 |
| N2 | nul | Vol. const., ρ = 0,05 | 800 |
| N3 | nul | Vol. const., ρ = 0,2 | 800 |
| N4 | nul | Rafales L = 10 (ρ = 0,05) | 800 |
| N5 | nul | Rafales L = 60 (ρ = 0,1) | 800 |
| N6 | nul | Règle de momentum | 800 |
| N7 | nul | Vol. calme/stress | 800 |
| N8 | nul | Vol. stochastique | 800 |
| N9 | nul | Vol. stochastique + rafales L = 30 | 800 |
| N10 | nul | Résultats corrélés, régimes ~2 h | 800 |
| N11 | nul | Résultats corrélés, régimes ~1 jour | 800 |
| E1 | nul de bout en bout | `run_edge_study` complet : catalogue, stratégie baseline réelle, persistance, règle α, vol. stochastique | 800 |
| S1 | essais multiples | 10 analyses du même historique nul (paramètres et horizons de `SEARCH_VARIANTS`), dans le même catalogue (règle α de l'application) **et** sans correction | 150 historiques |
| P1 | puissance | ≈ +0,05 R, régimes 60 min | 300 |
| P2 | puissance | ≈ +0,10 R, régimes 60 min | 300 |
| P3 | puissance | ≈ +0,20 R, régimes 60 min | 300 |
| P4 | puissance | ≈ +0,10 R, rafales L = 20 | 300 |
| P5 | puissance | ≈ +0,20 R, vol. stochastique | 300 |
| P6 | puissance | ≈ +0,10 R, ρ = 0,01 | 300 |
| P7 | puissance | Avantage conditionnel : signaux informatifs entre 12 h et 14 h seulement (≈ +0,30 R sur ceux-là) | 300 |

### Graines

- `SeedSequence([20261104, indice_du_scénario, réplication]).spawn(2)` donne la graine des données et celle de
  l'évaluation (bootstrap).
- Les scénarios Codex utilisent les graines de Codex (100 + r et 400 + r), avec `n_boot = 300` comme dans son script.
- Tous les autres scénarios utilisent les réglages par défaut de l'application (`StudySettings()`, `n_boot = 2000`,
  horizon 240, 4 fenêtres).

### Chaîne évaluée

- **N et P** : prix → signaux → `label_signals` → `signal_features` → évaluation walk-forward → verdict. C'est le code
  de la version testée, dans l'ordre exact de `run_edge_study`.
- **E1 et S1** : `run_edge_study` lui-même, sur un catalogue temporaire.
- **Premier niveau α** : celui de la version testée pour une première étude.

## 4. Versions évaluées

- **« avant »** : copie figée `frozen/v0.4.0/` (sources et spécifications ; `research_code_hash = f9055832e70d0f32` ;
  empreintes dans `frozen/v0.4.0.SHA256SUMS`).
- **« après »** : le code corrigé, figé à son tour avant exécution, de la même façon.

## 5. Hypothèses de défaut et corrections prévues à l'avance

Une correction n'est appliquée que si le diagnostic de la phase « avant » l'établit.

### H1 : dépendance

Le bootstrap par blocs indexé sur le **numéro** du signal (longueur 2n^(1/3)) sous-estime la variance quand les
résultats se chevauchent ou sont corrélés.

- **Signature attendue** : dépassement dans C1 et N4, N5, N9, N10, N11, mais pas dans C0, N1 et N2.
- **Correction prévue**, fixée maintenant et non ajustée après coup :
  1. **Unités d'inférence = grappes de chevauchement.** Les signaux hors échantillon sont triés par entrée. Un signal
     ouvre une nouvelle grappe si son entrée est **postérieure** à l'instant où les résultats de tous les signaux
     précédents de la grappe sont connus. Cet instant de disponibilité est la **clôture** de la bougie de sortie, pas
     son ouverture (N9 du contre-audit). Sous une nulle de type martingale, des grappes distinctes sont non corrélées.
  2. **Bootstrap par blocs mobiles circulaires sur la suite des grappes.** La longueur de bloc est choisie
     automatiquement par **Politis & White (2004)**, avec la correction de **Patton, Politis & White (2009)** : fenêtre
     « flat-top », sélection de M par la règle de White, bornes [1, n_grappes/3]. Les grappes absorbent la dépendance
     due au chevauchement ; les blocs absorbent la dépendance résiduelle (régimes).
  3. **Statistiques au niveau grappe.** Les sommes de R et de signaux pris sont calculées par grappe ; la moyenne
     filtrée est un estimateur de ratio. AUC et amélioration utilisent les mêmes tirages.
  4. **Effectifs minimaux exprimés en unités indépendantes.** `INSUFFICIENT` si moins de 100 grappes hors
     échantillon ou moins de 50 grappes contenant un signal retenu. Ce sont les seuils actuels, transposés aux grappes.
- **Analyse de sensibilité publiée, sans servir à choisir** : longueur de bloc × 0,5 et × 2 sur N5, N9 et N11, avec
  300 réplications chacun.

### H2 : essais multiples

α_m = 0,05/m n'est pas sommable (Σ α_m ≈ 0,234 pour 60 études). La règle actuelle ne peut donc pas garantir un risque
familial de 5 %. C'est un fait mathématique (audit B04-1) ; S1 en mesure l'effet pratique.

- **Correction prévue**, appliquée parce que la propriété affichée (« niveau relevé ») est fausse par construction :
  - **Dépense de risque sommable** : α_m = 0,05 × 6 / (π² m²), soit Σ ≤ 0,05 et α₁ ≈ 3,04 %.
  - **Famille = toutes les études enregistrées pour le même instrument, la même unité de temps et le même type de
    données**, et non par `dataset_id`, qu'un ré-import d'une sous-période contourne.
  - **Registre d'essais append-only, verrouillé.** Une étude supprimée ou corrompue continue de compter.
  - **Test unilatéral au niveau α_m** : `EDGE` si le quantile α_m de la distribution bootstrap de la moyenne filtrée
    est > 0. Cela aligne le niveau nominal de conception sur la référence de 5 % de la famille.

### H3 : autres causes possibles

Ne pas ajouter de correction non prévue sans écart documenté.

- **Sélection du seuil du filtre** : elle se fait hors test, sur validation interne ; aucun effet attendu.
- **Biais du générateur** : mesuré par la moyenne regroupée des R.
- **Erreurs numériques.**

## 6. Ce que la campagne ne prouvera pas

- L'absence de tout biais sur des données de marché réelles.
- Le contrôle du taux d'erreur sous toutes les formes de dépendance : par exemple, des régimes plus longs que
  l'historique ne sont pas identifiables par rééchantillonnage.
- La rentabilité de quoi que ce soit.

Les verdicts finaux sont limités aux scénarios testés.

## 7. Fichiers

- Code : `scenarios.py` (scénarios), `run_campaign.py` (exécution), `analyze.py` (statistiques et rapport).
- Résultats bruts : `results/<phase>/<scénario>.jsonl`, une ligne par réplication avec graines, empreinte des prix
  (`frame_sha256`), `dataset_id`, verdict, intervalles et sommes regroupées.
- `results/<phase>/manifest.json` : versions, empreintes de code et des sorties, `pip freeze`, durées.

## 8. Commandes

```bash
cd quant
.venv/bin/python research_campaign/run_campaign.py --phase before --src research_campaign/frozen/v0.4.0/src --workers 6
.venv/bin/python research_campaign/run_campaign.py --phase after --src research_campaign/frozen/v0.4.1/src --workers 6 \
    --calibration research_campaign/results/before/calibration.json
.venv/bin/python research_campaign/analyze.py
```

## 9. Écarts au protocole

(Aucun à la date de scellement.)

**Écart 1** (2026-11-04, ≈ 14:58 UTC, pendant la phase « avant », avant toute lecture de ses résultats)

- **Erreur** : le seuil indicatif de la section 2 pour N = 1 000 est faux. Le calcul exact (`analyze.binom_sf`) donne
  P(X ≥ 70) = 0,00347 > 0,05/15, contre P(X ≥ 71) < 0,05/15. Le premier compte significatif est donc **71/1 000**,
  et non 70/1 000. Le seuil pour N = 800 (59/800) est confirmé.
- **Ce qui ne change pas** : la règle de décision, à savoir le test binomial exact contre 0,05/15.

**Fichiers ajoutés après le scellement**, sans incidence sur les scénarios ni sur les graines :

- `analyze.py`, l'analyse prévue en section 2 ;
- `frozen/` (pour « après »).

L'empreinte de `analyze.py` est consignée dans le rapport final.

**Écart 2 — incident** (2026-11-04, ≈ 14:02 UTC, pendant la phase « avant », avant toute lecture de ses résultats)

- **Ce qui s'est passé** : un `ruff check --fix` appliqué par erreur au dossier `research_campaign/` a modifié deux
  fichiers, uniquement pour du tri d'imports et des imports inutilisés :
  - `frozen/v0.4.0/src/ai_trader_optimizer/core.py` ;
  - `run_campaign.py`.
- **Aucun effet sur la phase « avant »** :
  - aucun module du paquet n'importe `core.py`, qui est la référence v0.1 ;
  - les processus de calcul avaient chargé leurs modules au démarrage.
- **Restauration** :
  - `core.py` a été restauré à l'octet près : 88/88 fichiers de `frozen/v0.4.0` sont conformes à
    `frozen/v0.4.0.SHA256SUMS` ;
  - `run_campaign.py` a été restauré depuis la copie scellée (SHA-256 `72855816…`, identique au scellement).
- **Prévention** : ruff n'est plus appliqué à `research_campaign/`.

**Écart 3** (2026-11-04, ≈ 15:12 UTC, avant toute lecture des résultats de la campagne)

- **Sujet** : la règle de grappe de H1, écrite « entrée **postérieure** à l'instant où les résultats sont connus », a
  été implémentée d'abord au sens strict (>).
- **Constat** : un test unitaire de construction sur le générateur de Codex (et non un résultat de campagne) montre
  que, dans les deux conventions, un résultat devient connu à l'instant exact où le signal suivant entre. C'est le cas
  dans le pipeline réel (clôture de la bougie de sortie = ouverture de la suivante) comme chez Codex. Le sens strict
  fusionne alors tout en une seule grappe, alors que ces fenêtres se touchent sans se chevaucher.
- **Décision** : le principe énoncé (« des grappes distinctes sont non corrélées » sous une nulle de type martingale)
  vaut pour une entrée **au même instant ou après** (≥). La règle devient donc ≥.
- **Ce qui ne change pas** : ni le reste de H1, ni H2.

**Écart 4** (2026-11-04, ≈ 22:09 UTC, **après** lecture des résultats « avant », **avant** tout calcul de la phase « après »)

- **4a — Analyse** : `analyze.py` plantait sur E1, dont les lignes (produites par `run_edge_study`) n'ont pas de
  `sum_r`. Correction : l'effet vrai regroupé n'est calculé que sur les lignes qui portent `sum_r`. Aucun verdict,
  aucun taux, aucune règle n'est modifié.
- **4b — Erreur de conception de N10 et N11 (constatée, pas supposée)** : ces scénarios garantissent E[R] = 0 pour
  la moyenne **non filtrée** (vérifié : −0,0000 et −0,0014 R), mais pas pour la moyenne **filtrée** que juge le
  verdict. Les variables « alignées » de `features.py` sont multipliées par le sens du signal ; un régime de dérive
  persistant est donc lisible dans le momentum passé, et le filtre l'exploite réellement. Mesure sur les 800
  réplications indépendantes de la phase « avant » : moyenne filtrée hors échantillon **+0,095 R** [+0,089 ; +0,101]
  (N10) et **+0,213 R** [+0,206 ; +0,219] (N11), AUC 0,553 et 0,609. Ce ne sont **pas** des nuls pour la statistique
  testée : leurs `EDGE` sont des détections d'un avantage conditionnel réel, pas des faux positifs.
  - **Conséquence pour le diagnostic** : le défaut reste établi, par **C1** seul (17,6 %, p ≈ 2·10⁻⁴⁷), scénario
    dont l'effet filtré vrai est ≤ 0 (−0,044 R [−0,069 ; −0,020]).
  - **Conséquence pour l'acceptation** : le critère tel qu'écrit (K = 15 nuls, dont N10 et N11) sera publié tel
    quel ; il ne peut être satisfait que par une méthode **sans puissance** sur N10/N11. L'acceptation est donc
    publiée **deux fois** : (i) critère tel qu'écrit ; (ii) critère sur les 13 nuls valides, N10/N11 étant
    reclassés en scénarios de puissance conditionnelle non planifiés. La lecture (ii) est décidée **après** les
    résultats « avant » et le rapport le dit.
- **4c — Expérience complémentaire, non pré-enregistrée à l'origine** : `N10b_corr_2h_blind` et
  `N11b_corr_1d_blind`. Mêmes données, mêmes graines, mêmes signaux et mêmes résultats que N10/N11 (donc la même
  corrélation temporelle des résultats), mais les lignes de la matrice de variables sont **permutées au hasard entre
  signaux** (graine dérivée de la graine d'évaluation) avant l'apprentissage. Toute prévisibilité est détruite ; la
  dépendance des résultats est conservée. C'est le nul corrélé que N10/N11 visaient. 800 réplications chacun,
  exécutées sur les **deux** copies figées (v0.4.0 et v0.4.1), même critère (5 %, Clopper–Pearson, binomial exact),
  rapporté séparément avec un Bonferroni propre (K = 2).
- **4d — Sensibilité H1** (déjà prévue en H1, non prise en charge par `run_campaign.py`) : exécutée par
  `run_supplement.py`, qui enveloppe `inference.politis_white_block` (× 0,5 et × 2, puis bornes [1, min(3√n, n/3)])
  sans modifier le code évalué. N5, N9, N11 comme prévu, plus N11b. 300 réplications, publiées sans servir à choisir.
- **Ce qui ne change pas** : scénarios, graines, réplications, H1, H2, seuils. `run_campaign.py` et `scenarios.py`
  restent ceux du scellement.

**Écart 5** (2026-11-05, ≈ 01:22 UTC, après lecture des résultats complémentaires)

- **Défaut de mon script** `run_supplement.py` (pas du logiciel évalué) : dans la sensibilité 4d, l'enveloppe
  × 0,5 / × 2 de `politis_white_block` était ré-appliquée à elle-même à chaque tâche d'un même processus de calcul.
  L'échelle se composait (× 2, × 4, …) jusqu'aux bornes ; la médiane des blocs « × 2 » sur N11b valait 68 au lieu
  d'environ 4.
- **Constat** : par la médiane des longueurs de bloc enregistrées, avant toute interprétation de la sensibilité.
- **Décision** : ces résultats sont **invalides**. Ils sont conservés, renommés
  `results/INVALID_supp_sensitivity_v0.4.1_compounding_bug/`, et ne sont pas utilisés.
- **Correction et relance** : l'enveloppe part toujours de la fonction d'origine ; chaque ligne enregistre le bloc
  d'origine et le bloc mis à l'échelle. La sensibilité 4d est relancée à l'identique : mêmes scénarios, mêmes graines,
  300 réplications.
- **Non concernées** : les nuls aveugles 4c, qui n'utilisent pas l'enveloppe (échelle 1,0) ; vérifié, leurs blocs
  médians valent 2.
