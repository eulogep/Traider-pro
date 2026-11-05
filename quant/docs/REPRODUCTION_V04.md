# Reproduction des chiffres annoncés pour la v0.4.0

Rédigé le 2026-11-04 (≈ 13:15 UTC) pour l'audit indépendant de la v0.4. Document purement descriptif : aucun
changement du moteur ni de la couche `research/`, aucun commit.

Les heures sont en UTC. Elles viennent de la transcription de la session Claude Code qui a produit la v0.4.0, copiée
dans `~/traider-pro-backups/2026-11-04-v04-evidence/session_transcript.jsonl`.

---

## 0. Synthèse

Ce document distingue deux types de preuves :

- **Original** : produit par l'exécution d'origine.
- **Ré-exécution** : relancé aujourd'hui avec le code actuel.

Une ré-exécution n'est pas l'exécution d'origine.

| Chiffre annoncé | Expérience | Sortie originale sauvegardée ? | Ré-exécution du 2026-11-04 |
|---|---|---|---|
| 2 856 signaux exploitables | A (06:38:26Z) | **Oui**, par chance (dossier temporaire non effacé) | Identique : 14 000 candidats, 2 856 étiquetés, 1 418 testés hors échantillon, verdict `NEGATIVE` |
| 1 faux positif sur 60 jeux de bruit | B (06:40:39Z) | **Non** : seuls les totaux ont été affichés, aucun fichier écrit | Totaux identiques : 59 `NO_EDGE` / 1 `EDGE` |
| Avantage faible détecté 19/30 | B | Non (idem) | Identique : 19 `EDGE` / 11 `NO_EDGE` |
| Avantage moyen détecté 30/30 | B | Non (idem) | Identique : 30 `EDGE` |
| R étiqueté = R du moteur (écart 2,2·10⁻¹⁶) | C (06:38:07Z) | Non (sortie console seulement) | Identique sur les données d'origine (16 trades) et sur celles de A (172 trades) |

Les sorties originales de B et de C n'existent que sous forme de texte console dans la transcription. Les fichiers
détaillés par seed listés plus bas viennent de la ré-exécution.

**Pourquoi l'audit n'a pas reproduit A.** Les études trouvées dans le dossier d'audit portent sur
`seed 7 · 20 j` (dataset `84e2fe997b00fa7e`, 495 signaux). Le chiffre 2 856 vient de `seed 7 · 120 j`
(dataset `be3cc3903c0713ea`). Ce paramètre n'était écrit nulle part dans le compte rendu : c'est une omission de ma part.

**Pourquoi l'audit n'a pas reproduit B.** Le protocole de B n'était pas documenté. Le script d'audit
`statistical_probes.py` utilise un autre protocole :

| | Audit (`statistical_probes.py`) | Expérience B |
|---|---|---|
| Effet testé | décalage du taux de gain global (p = 0,45 / 0,50) | effet **conditionnel** à une variable |
| Signaux par jeu | 1 500 | 2 000 |
| Seeds | autres | `1000+s` |

Les deux protocoles mesurent des choses différentes. On ne peut donc pas attendre les mêmes chiffres.

---

## 1. Jeux de données

### Expérience A : `be3cc3903c0713ea`

| Champ | Valeur |
|---|---|
| Construction | `ai_trader_optimizer.data.synthetic.synthetic_dataset(seed=7, days=120)` (marche aléatoire, fausses cotations) |
| Nom | `DÉMO — prix synthétiques (fausses cotations) · seed 7 · 120 j` |
| Symbole / période / type | `XAUUSD-DEMO`, M1, `synthetic` |
| Bougies | 123 840, du `2026-09-07T00:00:00Z` au `2027-01-04T23:59:00Z` |
| `dataset_id` | `be3cc3903c0713ea` |
| SHA-256 des octets canoniques (`canonical_bytes`, = CSV décompressé) | `62a2d6d9bc2177750b3511c44bbcafb570af9a884a00fdd20ac444489b4cf006` |
| SHA-256 du fichier stocké `be3cc3903c0713ea.csv.gz` | `2e42858875c8b8eaed0a3cd8771bb02e75428f6a283ff0eb7389687ae3bef1e2` |

- Le `dataset_id` est le préfixe de 16 caractères de sha256(`ato-dataset/2|XAUUSD-DEMO|M1|<side>|` + octets canoniques).
- La ré-exécution régénère des octets **identiques** au fichier original (`dataset_bytes_identical_to_original: true`).

### Expérience B : pas de jeu de données

Les signaux (horodatages, variables, R) sont générés en mémoire par le script (§3). Aucun prix n'est utilisé, et ni la
stratégie ni l'étiquetage n'interviennent.

### Expérience C : deux jeux

- Original : `synthetic_dataset(seed=42, days=10)`.
- Ré-exécution : ce même jeu, plus celui de A.

---

## 2. Seeds

| Expérience | Usage | Valeur |
|---|---|---|
| A | prix synthétiques | `7` |
| A | bootstrap par blocs (`evaluate_signals`) | `int(study_id[:8], 16)`. Original : `study_id = 7a506077f5e641c8`, seed **2052087927**. Ré-exécution : `af9136fc422b7374`, seed 2945529596 |
| B | données du seed `s` | `np.random.default_rng(1000 + s)` |
| B | évaluation (bootstrap) | `seed = s` |
| B | plages de `s` | bruit : `s` de 0 à 59 ; faible et moyen : `s` de 0 à 29 (mêmes seeds pour les deux) |
| C | prix synthétiques | `42` (original) ; `42` et `7` (ré-exécution) |

**Point important pour l'audit.** Le `study_id` est un hachage des entrées **et** de `research_code_hash()`. Cette
fonction hache le code du moteur et chaque fichier `research/*.py`. Conséquences :

- La moindre modification d'un octet dans ces fichiers change la seed du bootstrap.
- Les intervalles de confiance changent donc légèrement, mais les estimations ponctuelles restent identiques.

C'est ce qui s'est passé entre l'exécution A et la ré-exécution (§6, A).

---

## 3. Scripts et commandes exactes (originaux, recopiés de la transcription)

Ces scripts ont été lancés depuis `quant/` avec `.venv/bin/python -` (script passé en heredoc). Ils n'ont **pas** été
enregistrés comme fichiers dans le dépôt.

### A : étude sur 120 jours (2026-11-04T06:38:26Z)

```python
import time, tempfile, json
from ai_trader_optimizer.data.synthetic import synthetic_dataset
from ai_trader_optimizer.strategies import load_catalog
from ai_trader_optimizer.storage import LabCatalog
import ai_trader_optimizer.services as sv
from ai_trader_optimizer.research import run_edge_study
cat = LabCatalog(tempfile.mkdtemp())
ds = synthetic_dataset(7, 120)
cat.save_dataset(ds)
spec = [s for s in load_catalog().specs.values() if s.status=="active"][0]
cfg = sv.default_config(cat)
t=time.time(); st = run_edge_study(cat, ds.meta.dataset_id, spec, cfg); print("time", round(time.time()-t,2))
r = st["result"]
print(st["signals"], r["n_oos"], r.get("n_taken"))
for k in ("baseline","filtered","improvement","auc","brier"): print(k, r.get(k))
print(r["verdict"]); print([ (f["fold"], f.get("n_train"), f.get("n_test"), f.get("threshold"), f.get("auc")) for f in r["folds"]])
print(st["final_model"]["latest_signal"], st["final_model"]["weights"][:3])
t=time.time(); st2 = run_edge_study(cat, ds.meta.dataset_id, spec, cfg); print("cached", st2["study_id"]==st["study_id"], round(time.time()-t,3))
```

Sortie console originale :

```
time 1.78
{'candidates': 14000, 'labelled': 2856, 'exit_reasons': {'SL': 1772, 'TP': 1084}} 1418 880
baseline {'mean_r': -0.14430252513077516, 'ci': (-0.2178925142583492, -0.06490746249274686), 'win_rate': 0.36812411847672777, 'p_positive': 0.0, 'rating': 'négatif'}
filtered {'mean_r': -0.13276737122657414, 'ci': (-0.23052888482577039, -0.038734527787848944), 'win_rate': 0.37272727272727274, 'p_positive': 0.0035, 'rating': 'négatif'}
improvement {'mean_r': 0.011535153904201012, 'ci': (-0.04930032368774763, 0.07266845962076833), 'rating': 'non démontré'}
auc {'value': 0.5096918616584565, 'ci': (0.46853132149356386, 0.5500953381743704), 'rating': 'non démontré'}
brier {'model': 0.23538678677753447, 'reference': 0.23293254978798167, 'skill': -0.010536256061193239}
{'code': 'NEGATIVE', 'confidence': '95,0 %', 'title': 'Perte attendue démontrée', ...}
[(1, 1438, 369, 0.426826355592379, 0.48829599798640827), (2, 1807, 337, 0.3344020561567622, 0.5259098852670769), (3, 2144, 338, 0.348180807248065, 0.4959014873335559), (4, 2482, 374, 0.3426503871967231, 0.5343337597104795)]
cached True 0.001
```

### B : calibration du détecteur sur signaux artificiels (2026-11-04T06:40:39Z)

```python
import numpy as np
from ai_trader_optimizer.research.study import evaluate_signals, StudySettings
def sig(n, rng, beta):
    t=np.sort(rng.integers(0,10**15,n)).astype(np.int64); X=rng.normal(size=(n,6))
    p=1/(1+np.exp(-(np.log(0.4/0.6)+beta*X[:,0]))); win=rng.random(n)<p
    return t,t+10**9,X,np.where(win,1.5,-1.0)
for beta,label in [(0,"bruit"),(0.3,"faible"),(0.6,"moyen")]:
    codes={}
    for s in range(60 if beta==0 else 30):
        rng=np.random.default_rng(1000+s); out=evaluate_signals(*sig(2000,rng,beta),StudySettings(n_boot=300),seed=s)
        c=out["verdict"]["code"]; codes[c]=codes.get(c,0)+1
    print(label, codes)
```

Sortie console originale (c'est la seule trace de l'exécution d'origine) :

```
bruit {'NO_EDGE': 59, 'EDGE': 1}
faible {'EDGE': 19, 'NO_EDGE': 11}
moyen {'EDGE': 30}
```

### C : étiquettes contre moteur (2026-11-04T06:38:07Z, seed 42, 10 jours)

```python
# (imports : synthetic_dataset, load_catalog, run_backtest, label_signals, build_strategy, services, LabCatalog, tempfile)
ds = synthetic_dataset(42, 10)
spec = [s for s in load_catalog().specs.values() if s.status=="active"][0]
cat = LabCatalog(tempfile.mkdtemp()); cfg = sv.default_config(cat)
res = run_backtest(ds, spec, cfg)
sig = build_strategy(spec, cfg.strategy_params).compute(ds.bars.reset_index(drop=True))
lab = label_signals(ds, spec, cfg, sig, 240)
m = res.trades.merge(lab, left_on="signal_time", right_on="signal_time", how="left")
cmp = m[m.exit_reason_x.isin(["SL","TP","SL_GAP","TP_GAP"])]
print(len(res.trades), len(cmp), (cmp.r_multiple - cmp.r).abs().max(), (cmp.exit_reason_x==cmp.exit_reason_y).all())
```

Sortie originale : `16 16 2.220446049250313e-16 True`.

Le test permanent `tests/test_research.py::test_labels_equal_engine_r_multiple_for_every_traded_signal` vérifie la
même propriété avec une tolérance `atol=1e-12` (données de la fixture du test).

### État du code au moment des exécutions

La reconstitution s'appuie sur la transcription et sur les dates de modification des fichiers.

| Heure (UTC) | Événement | Effet sur les chiffres |
|---|---|---|
| 06:37:40 | dernière réécriture complète de `research/study.py` | — |
| 06:38:07 | **C** | — |
| 06:38:26 | **A** (`code_hash 6c3576817392c550`, `software_version 0.3.1` dans le fichier produit) | — |
| 06:38:46 | `_latest_opinion` limité aux signaux en session | Change l'avis sur le dernier signal et le hachage de code ; **pas** `evaluate_signals` |
| 06:39:19 | `_finite()` : NaN/inf écrits `null` ; la fonction renvoie le fichier persisté | Sérialisation seulement |
| 06:40:39 | **B** | — |
| 06:41:56 | `zip(..., strict=True)` dans `study.py` (ruff B905) | Aucun : les longueurs sont égales |
| 06:42:52 | `__version__` passe de 0.3.1 à 0.4.0 | Métadonnée |

- `evaluate_signals`, `stats.py`, `labels.py` et `features.py` n'ont pas changé après 06:38 UTC.
- Aucun paquet Python n'a été installé ou mis à jour après le 2026-11-03 à 19:45 UTC (ajout de fastapi et httpx).

Empreintes SHA-256 actuelles :

| Fichier | SHA-256 |
|---|---|
| `research/__init__.py` | `a54b60fc117d49aac2b0985c2b090a925d98c809869fb34993c0e1442c63e751` |
| `research/features.py` | `c47d554a65dcda14b08efcf21c13e29845ff000fc2479dbd81b0446a28b40b3b` |
| `research/labels.py` | `c15beddc4e57de49feaf0fcbbe8088f87a070987180d5ccd6f79f6ea25f93781` |
| `research/robustness.py` | `7d2e2556bffcb3b9ebbacdf6a4b12dc7ba94aa4d7f8592348bf64e525466eb71` |
| `research/stats.py` | `fc7d71d680c42fc9e91c5f0b82bb5f256c1a9c99b6bb40edf52251c4d25e3cbf` |
| `research/study.py` | `34cbf66cf5c1c64d85d6bfe6d8731248f0d429cd4738bf6f84d667487dc716bf` |
| `tests/test_research.py` | `edcf6d26f7af3f9e1ea1b3b17a74ad818055165b5082a7bce264b0384fb31163` |

`research_code_hash()` vaut actuellement `f9055832e70d0f32`, la même valeur que dans les études de l'audit.
`ENGINE_VERSION` vaut `backtest-engine/0.3.1`.

---

## 4. Paramètres

### Stratégie (A et C)

`baseline.ema_trend_3bars@1.0.0`, « Baseline — tendance EMA + séquence 3 bougies ». C'est une stratégie
**illustrative**, pas celle du trader. On la sélectionne comme la première spécification `status == "active"` du
catalogue.

| Paramètre | Valeur |
|---|---|
| `ema_fast` | 20 |
| `ema_slow` | 50 |
| `atr_period` | 14 |
| `atr_method` | `sma` |
| `sl_atr_mult` | 1.5 |
| `rr` | 1.5 |
| `warmup_bars` | 50 |

### Configuration et coûts (A et C)

`services.default_config(cat)` est appelé sur un catalogue **vide**, ce qui donne les valeurs par défaut documentées :

- spread 0.3 ;
- glissement 0.05 ;
- commission 3.0 par lot et par côté ;
- contrat `XAUUSD_HYPOTHETICAL` ;
- sessions de la spécification.

La configuration complète est enregistrée dans `rerun_A_report.json` (clé `config`).

Attention : avec un catalogue qui contient des réglages sauvegardés (page Paramètres / Streamlit), les coûts changent,
et donc tous les chiffres aussi.

### Étude (A)

`StudySettings()` par défaut :

| Paramètre | Valeur |
|---|---|
| `horizon_bars` | 240 |
| `folds` | 4 |
| `initial_train_fraction` | 0.5 |
| `l2` | 1.0 |
| `n_boot` | **2000** |
| `min_train` | 100 |

Ensemble de variables : `price-action-v1` (12 variables). Correction de Bonferroni : alpha = 0,05 / 1, car c'est la
première étude sur ce jeu dans un catalogue neuf. Une étude lancée dans un catalogue qui contient déjà des études sur le
même jeu utilise un alpha plus petit.

### Expérience B

- Fonction pure `evaluate_signals` uniquement. Ni la stratégie, ni l'étiquetage, ni les 12 variables réelles
  n'interviennent.
- 2 000 signaux par jeu, horodatages uniformes, chaque signal se dénouant en 1 seconde. Les signaux sont donc
  quasi indépendants et la purge n'a presque pas d'effet.
- 6 variables N(0,1). Probabilité de gain : `logit(p) = log(0,4/0,6) + beta·X₀`, avec beta = 0 (bruit), 0,3 (faible),
  0,6 (moyen).
- Gain +1,5 R, perte −1 R. Avec beta = 0, l'espérance vraie est 0,4 × 1,5 − 0,6 = 0.
- **`StudySettings(n_boot=300)`**, et non 2 000 comme dans l'application. Les autres réglages sont ceux par défaut.
  Alpha = 0,05.

---

## 5. Versions

| Composant | Version |
|---|---|
| Python | 3.12.14 (Homebrew, Clang 21), macOS Darwin 25.2.0 arm64 |
| numpy | 2.5.4 |
| pandas | 2.3.3 |
| pydantic | 2.14.2 |
| fastapi | 0.162.0 |
| pytest | 9.2.0 |
| ruff | 0.17.3 |
| Paquet `ai_trader_optimizer` | installé en mode éditable depuis `quant/` |

- La liste complète est dans `pip_freeze_now.txt` (§6), extraite du même `.venv` que celui des exécutions.
- Contraintes déclarées : `quant/pyproject.toml` et `quant/requirements.lock`.
- La couche `research/` n'utilise que numpy et pandas.

---

## 6. Résultats détaillés et fichiers

Les preuves ont été copiées hors du dépôt, sans rien y modifier, dans
`~/traider-pro-backups/2026-11-04-v04-evidence/` (empreintes dans `SHA256SUMS.txt`).

| Fichier | Nature | SHA-256 |
|---|---|---|
| `original_run_A/studies/7a506077f5e641c8.json` | **Original** A (`created_at 2026-11-04T06:38:31Z`), copié depuis `$TMPDIR/tmp3kulpho2/` | `ee24b75746b6e705feaf904c70c59218b65baae16f27c98c8e1eb92c8cfb7c53` |
| `original_run_A/datasets/be3cc3903c0713ea.csv.gz` | **Original** A, données | `2e42858875c8b8eaed0a3cd8771bb02e75428f6a283ff0eb7389687ae3bef1e2` |
| `original_run_A/lab.db` | **Original** A, catalogue SQLite | `2631135387fd0bb3fa64b54ca5dc818da26d92477ca3a028711a17c64da004ba` |
| `session_transcript.jsonl` | **Original** : transcription (scripts et sorties console de A, B et C) | `ad9ca8e59fc394763d153f9fa6e5f437dec5823403bfd6d04904836a5fdf7ff9` |
| `pip_freeze_now.txt` | environnement | `101cd9786ad549d9d336f89687f2aa1dbb125a65bd645e31b5ebdf8229701e74` |
| `rerun_2026-11-04/rerun_A_study.py` | Ré-exécution A | `0a3112d517dc61604566f278d7a3b11cdbf3a8a0af1a07214d30a6d6c906e3c0` |
| `rerun_2026-11-04/check_A_original_seed.py` | Contrôle A avec la seed originale | `46b0ec5bdd29d9e46b47205479985b7bccbb794ba74b1ac0d2050b476dae84eb` |
| `rerun_2026-11-04/rerun_B_calibration.py` | Ré-exécution B (calcul identique, ajout d'une sortie par seed) | `f143a4248e73885b483fe1a2e2fe4b449ac6a82e313f8dde9ec7539b3344d61b` |
| `rerun_2026-11-04/rerun_C_labels_vs_engine.py` | Ré-exécution C | `a5ec2cb0de4e9a83468fa6b32853f63f8d7ebc640f536537108453b5ef2b9a80` |
| `rerun_2026-11-04/out/rerun_A_report.json` | Sortie ré-exécution A | `e584f74c97de6a31e2188f125cf8600da4d2ebff11d1879cf676f1f69a7add67` |
| `rerun_2026-11-04/out/tmpm6wt5sge/studies/af9136fc422b7374.json` | Étude ré-exécutée | `906e541874bba4348c63187cda627236d722163adebe04d5aeec058454981a54` |
| `rerun_2026-11-04/out/rerun_B_per_seed.json` | Sortie ré-exécution B, **une ligne par seed** | `65508e8eb23c2adb9686bb949bf0951796497bbf85a4eea27f498ec86e70356f` |
| `rerun_2026-11-04/out/rerun_C_output.txt` | Sortie ré-exécution C | `7d99645cfa0c0cacc96c200a82d31788b6e1a5ad447259fd716dd213f906a9b3` |

### A, résultats originaux

Lus dans `7a506077f5e641c8.json`.

| Mesure | Valeur |
|---|---|
| Signaux candidats | 14 000 |
| Signaux étiquetés | 2 856 (SL 1 772, TP 1 084) |
| Testés hors échantillon | 1 418 |
| Pris par le filtre | 880 |
| Baseline | −0,1443 R, IC 95 % [−0,2179 ; −0,0649] |
| Filtré | −0,1328 R, IC 95 % [−0,2305 ; −0,0387] |
| Gain du filtre | +0,0115 R, IC 95 % [−0,0493 ; +0,0727] |
| AUC | 0,5097, IC 95 % [0,4685 ; 0,5501] |
| Brier skill | −0,011 |
| Verdict | `NEGATIVE` |

Particularités du fichier original :

- `software_version` vaut `0.3.1` : la version a été changée après coup.
- L'avis sur le dernier signal porte sur un signal **hors session** (23:58, p = 0,94). C'est le défaut corrigé
  à 06:38:46.

### A, ré-exécution (code actuel)

- Données identiques à l'octet près.
- `signals` identique.
- Identiques à l'original : `n_oos`, `n_taken`, `folds` (effectifs, seuils, AUC par fenêtre), `calibration`, `brier`,
  `verdict`.
- Les estimations ponctuelles (`mean_r`, `win_rate`, AUC) sont identiques. Seules les **bornes des intervalles**
  diffèrent légèrement, parce que la seed du bootstrap a changé (`study_id` différent, voir §2). Exemple : IC baseline
  [−0,2205 ; −0,0669] au lieu de [−0,2179 ; −0,0649].
- **Contrôle décisif** (`check_A_original_seed.py`) : avec les mêmes entrées et la seed originale 2052087927, le code
  actuel de `evaluate_signals` redonne **tous** les champs de `result` du fichier original à l'identique
  (« champs différents de l'original : aucun »).
- Avis actuel sur le dernier signal : 2027-01-04 16:55, BUY, p = 0,393, « NE PAS TRADER ».

### B, ré-exécution

| Scénario | Résultat |
|---|---|
| Bruit (60 jeux) | 59 `NO_EDGE`, 1 `EDGE` |
| Faible (30 jeux) | 19 `EDGE`, 11 `NO_EDGE` |
| Moyen (30 jeux) | 30 `EDGE` |

- Ces totaux sont identiques à la sortie originale.
- Le faux positif est le jeu `data_seed 1010` / `eval_seed 10` : n_oos = 1 047, IC filtré [+0,0030 ; +0,1891], baseline
  +0,086 R alors que l'espérance vraie est 0.
- Le nombre de signaux testés par jeu va de 940 à 1 047.

### C, ré-exécution

| Données | Trades du moteur | Comparés | Écart max | Motifs de sortie |
|---|---|---|---|---|
| seed 42, 10 j | 16 | 16 | 2,22·10⁻¹⁶ | identiques |
| seed 7, 120 j | 172 | 172 | 2,22·10⁻¹⁶ | identiques |

Tous les trades du moteur sont sortis en SL ou en TP.

---

## 7. Reproduire depuis une copie propre

**Attention : `quant/` n'est pas suivi par Git.** Un `git clone` du commit `2dedf6c` ne contient **pas** la couche
`research/`. Une copie propre veut donc dire une copie du répertoire de travail, par exemple l'instantané `repo/` de
l'audit, dont il faut vérifier les empreintes du §3.

```bash
cd quant
python3.12 -m venv .venv && .venv/bin/pip install -e ".[dev]"   # versions : comparer à pip_freeze_now.txt (§5)
# Contrôle d'intégrité : research_code_hash() doit valoir f9055832e70d0f32 (sinon les IC de A différeront légèrement)
.venv/bin/python -c "from ai_trader_optimizer.research.study import research_code_hash as h; print(h())"
E=~/traider-pro-backups/2026-11-04-v04-evidence      # ou une copie de ce dossier
.venv/bin/python $E/rerun_2026-11-04/rerun_A_study.py $E/original_run_A /tmp/repro_A    # 2 856 / 1 418 / NEGATIVE
.venv/bin/python $E/rerun_2026-11-04/check_A_original_seed.py $E/original_run_A        # « aucun » champ différent
.venv/bin/python $E/rerun_2026-11-04/rerun_B_calibration.py /tmp/repro_B                # 59/1, 19/11, 30 (≈ 17 s)
.venv/bin/python $E/rerun_2026-11-04/rerun_C_labels_vs_engine.py                        # 16/16 et 172/172, 2.22e-16
```

Si le dossier de preuves n'est pas accessible, les scripts A, B et C du §3 suffisent :

- A régénère lui-même les données ; on vérifie le SHA-256 canonique `62a2d6d9…`.
- B et C n'ont besoin d'aucun fichier.

Il faut toujours partir d'un catalogue **vide** (`tempfile.mkdtemp()`). Sinon, les réglages sauvegardés et les
études antérieures (Bonferroni) modifient les résultats.

Le niveau de reproductibilité attendu :

| Expérience | Ce qui doit coïncider |
|---|---|
| A | Signaux, folds et estimations ponctuelles identiques quel que soit le code de `research/`. IC identiques seulement si `research_code_hash()` est le même ; sinon, utiliser `check_A_original_seed.py` |
| B et C | Résultats exacts, qui ne dépendent pas du hachage de code |

Dans tous les cas : même numpy (2.5.x) et même plateforme. Le générateur PCG64 est stable, mais l'algèbre linéaire peut
différer au dernier bit entre plateformes. Ces écarts infimes ne devraient pas changer les verdicts, mais cela n'a pas
été vérifié sur une autre machine.

---

## 8. Ce que ces chiffres ne démontrent pas (corrections du compte rendu)

1. **« 2 856 signaux au lieu de quelques dizaines » : formulation inexacte.**
   - Sur les mêmes données, le moteur (Risk Guardian compris) prend **172** trades, pas « quelques dizaines ».
   - La comparaison correcte : 2 856 signaux étiquetés pour l'étude contre 172 trades dans le backtest.
2. **B ne valide pas l'outil de bout en bout.**
   - B teste seulement l'étage statistique `evaluate_signals`, avec des signaux indépendants, 6 variables artificielles,
     et `n_boot=300` au lieu de 2 000.
   - Ni l'étiquetage, ni les variables réelles, ni la dépendance temporelle des vrais signaux n'interviennent.
   - « Faible » et « moyen » sont des noms donnés à beta = 0,3 et beta = 0,6, pas des tailles d'effet mesurées en R.
3. **Les échantillons sont petits.** Intervalles de Clopper-Pearson à 95 % (calcul de l'audit) :

   | Résultat | Intervalle 95 % |
   |---|---|
   | 1/60 faux positifs | 0,04 % à 8,9 % |
   | 19/30 | 44 % à 80 % |
   | 30/30 | 88 % à 100 % |

   « 1 faux positif sur 60 » ne prouve donc pas un taux de 1,7 %.
4. **Signaux corrélés.** Le script d'audit (`correlated_null_60`, signaux groupés par 100) obtient un taux de faux
   positifs dont l'intervalle va de 5,9 % à 24,6 %.
   - Je ne l'ai pas re-vérifié, mais c'est cohérent avec la limite du point 2 : B n'a pas testé ce cas.
   - Les vrais signaux d'une stratégie sont groupés dans le temps. **Le taux de faux positifs annoncé ne doit pas être
     considéré comme établi pour des données réelles** tant que ce cas n'est pas traité.
5. **L'écart 2,2·10⁻¹⁶ porte sur des trades sortis en SL ou TP.**
   - Le script ne compare que les sorties SL, TP, SL_GAP et TP_GAP. Sur les deux jeux mesurés, tous les trades étaient
     dans ce cas.
   - Une sortie d'une autre nature (fin de session, clôture forcée par le risque) n'a pas été comparée.

---

## 9. Proposition : nouvelle campagne reproductible

Ce serait une **nouvelle** expérience, à présenter comme telle. Elle n'est pas lancée, car elle demande d'ajouter un
script au projet.

1. **Fichier versionné.** Un script `quant/scripts/research_campaign_v04.py` avec ses paramètres pré-déclarés en tête
   du fichier, avant toute exécution. Il écrit une sortie JSON par seed et un manifeste qui contient :
   - `research_code_hash`, `ENGINE_VERSION`, `pip freeze`, la plateforme ;
   - le SHA-256 de chaque jeu ;
   - le SHA-256 de chaque sortie.
2. **Réglages de l'application.** `n_boot = 2000` et Bonferroni désactivé (alpha = 0,05), puisque chaque jeu est neuf.
3. **Bruit indépendant.** 500 jeux, ce qui donne un intervalle sur le taux de faux positifs d'environ ± 2 points.
4. **Bruit corrélé.** 500 jeux, avec des signaux groupés comme dans la réalité : grappes de durée variable et
   chevauchement des horizons. Ce cas décide si le verdict tient sur données réelles.
5. **Chaîne complète.** 200 seeds de prix synthétiques (marche aléatoire, donc aucun avantage par construction) passés
   par `run_edge_study` de bout en bout. On mesure le taux de faux `EDGE` de l'outil réel.
6. **Puissance.** Effets plantés exprimés en espérance R (+0,05, +0,10, +0,20 R), 200 jeux chacun, signaux corrélés.
7. **Critère publié d'avance.** Taux de faux positifs ≤ 5 % (borne haute de l'IC ≤ 7,5 %) sur les cas 4 et 5. Sinon :
   - le verdict `EDGE` est suspendu dans l'interface ;
   - la méthode est corrigée, par exemple avec des blocs plus longs, un bootstrap sur les grappes ou un embargo.

Si le cas 4 confirme le constat de l'audit, la correction touchera `research/stats.py` et `research/study.py` (pas le
moteur de backtest). Elle ne sera faite qu'avec votre accord.
