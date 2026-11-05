# Handoff — contre-validation indépendante de la V0.4.1 (2026-11-05)

Tu as audité la V0.4.0 (`docs/audits/codex-audit-v04-lhxtu170/`) et contre-audité la V0.3.1
(`docs/audits/codex-counter-v031-d7c34xx6/`). Les deux rapports sont archivés avec leurs empreintes
(`docs/audits/SHA256SUMS_2026-11-04.txt`).

La V0.4.1 prétend corriger une partie de tes constats. **Ta mission est de contester ces corrections et la campagne
statistique, pas de les confirmer.**

Documents de référence :
- `quant/docs/VALIDATION_V041.md` : synthèse, tableaux et verdicts ;
- `quant/research_campaign/PROTOCOL.md` : protocole scellé et écarts datés (§9) ;
- `quant/docs/REPRODUCTION_V04.md`.

**Règles inchangées.**
- Aucun compte de trading, aucun ordre, aucun secret, aucun push, aucune opération Git destructive.
- Le dépôt n'a reçu aucun commit : `quant/` n'est pas suivi par Git. Travaille sur une copie.
- Rapport dans `docs/CODEX_REVIEW_V041.md`. Pour chaque constat : fichier:ligne, gravité, scénario, test proposé,
  certitude.

## 1. Reproduire

```bash
cd quant
.venv/bin/python -m pytest -q                      # attendu : tout passe
.venv/bin/ruff check --no-cache src tests app.py scripts
(cd research_campaign/frozen && shasum -a 256 -c v0.4.0.SHA256SUMS && shasum -a 256 -c v0.4.1.SHA256SUMS)
diff -rq --exclude __pycache__ src research_campaign/frozen/v0.4.1/src   # attendu : vide
.venv/bin/python research_campaign/analyze.py      # régénère REPORT_*.md / COMPARISON.md depuis les jsonl
cd .. && pnpm test && pnpm typecheck && pnpm build
```

Pour recalculer une réplication de la campagne : `run_campaign.run_one(...)`. Les graines sont dans chaque ligne
jsonl : `data_seed` et `eval_seed`. Un échantillon suffit, la campagne complète demande environ 11 h sur 6 cœurs.

## 2. Ce qui est affirmé (à réfuter)

| Affirmation | Où la vérifier |
|---|---|
| B04-2 : sur ton contre-exemple de groupes de 100, la v0.4.0 donne 17,6 % d'`EDGE` (176 sur 1 000) et la v0.4.1 0 % (1 000 `INSUFFICIENT`, 15 unités) | `results/{before,after}/C1_codex_cluster100.jsonl` |
| Aucun dépassement significatif de 5 % sur 13 nuls (Bonferroni K = 15) | `results/COMPARISON.md` |
| Puissance : P3 (+0,20 R) 93,3 % → 95,7 % ; P2 (+0,10 R) 62,7 % → 72,3 % | idem |
| B04-1 : la dépense α_m = 0,05·6/(π²m²) par famille « type:symbole:unité » ramène S1 de 7,3 % à 4,7 % | `research/registry.py`, S1 |
| B04-3 : aucune exception ni NaN ne produit un avis favorable | `tests/test_v041_research_safety.py` |
| I04-1 : une étude altérée, même ré-empreintée, est refusée ; le registre chaîné survit aux suppressions | idem et `research/study.py::_verify` |
| I04-4 : l'avis n'est donné que sur un signal « nouveau », par un modèle entraîné sur les seuls résultats disponibles | `study.py::_prospective_opinion` |
| N1 à N8 et N10 corrigés | `tests/test_v041_v031_partials.py`, `server/localGuard.spec.ts` |

## 3. Ce que je sais être faible : examine en priorité

0. **Échec de la v0.4.1 sous des régimes d'un jour (N11b, nul aveugle complémentaire).**
   - Résultat : 8,0 % [6,2 ; 10,2] d'`EDGE`, contre 3,8 % en v0.4.0 sur les mêmes données. Fichiers
     `results/supp_blind_v0.4.{0,1}/`.
   - Mon diagnostic : Politis–White retient des blocs de 2 unités, alors que la corrélation, faible à chaque décalage,
     se cumule sur un jour. L'écart-type standardisé vaut 1,34.
   - Propose une correction **de principe** à pré-enregistrer (plancher de bloc en temps calendaire, blocs par jour,
     rééchantillonnage complet…), et non une correction choisie pour passer N11b.
   - La sensibilité de l'écart 4d a été relancée après un bug de mon script (écart 5). Les résultats invalides sont
     conservés à part.
1. **Niveau nominal non tenu (§5.7 de VALIDATION_V041).**
   - Constat : ≈ 5 % d'`EDGE` sous les nuls indépendants pour α₁ = 3,04 %.
   - Le bootstrap isolé est calibré sur iid ; la dispersion réelle de la moyenne filtrée dans le pipeline dépasse
     l'estimation bootstrap de 10 à 20 %.
   - Mon hypothèse : bootstrap conditionnel dans un walk-forward ancré, où la sélection dépend des résultats des
     fenêtres précédentes. **Confirme ou réfute-la**, par exemple en rééchantillonnant la procédure complète sur
     quelques centaines de nuls.
2. **Effet filtré positif sous le nul exact** : +0,003 R, z combiné ≈ 3,9. **AUC regroupée < 0,5** : z ≈ −10,8.
   Cause non démontrée. Une fuite subtile est-elle exclue ?
3. **N10 et N11 étaient mal spécifiés.** Je les ai reclassés **après** avoir vu les résultats « avant » (écart 4b).
   - Juge si ce reclassement est légitime ou s'il s'agit d'un ajustement opportuniste.
   - Les nuls aveugles de remplacement N10b et N11b (permutation des variables) sont-ils de vrais nuls corrélés ?
4. **Les rafales sont « corrigées » par refus.**
   - C1, N4, N5, N9 et P4 sont tous `INSUFFICIENT` : la puissance est nulle sur les stratégies en rafales sur 120
     jours.
   - Le seuil de 100 unités est-il justifié ?
   - La définition des unités est la règle ≥ de l'écart 3 : entrée au plus tôt à l'instant où le résultat devient
     connu. Est-elle correcte ?
5. **Longueur de bloc Politis–White** (`inference.py::politis_white_block`) : vérifie l'implémentation (fenêtre
   flat-top, règle de M, constante du bootstrap circulaire) contre l'article, et la sensibilité (écart 4d).
6. **Ce qui n'est pas fait** :
   - I04-2 : rejeu portefeuille ;
   - I04-5 : calibrateur ;
   - I04-6 : Monte Carlo par blocs avec sizing ;
   - I04-9 : le générateur de démo reste non nul ;
   - N9 : journal du moteur ;
   - les hooks legacy `client/hooks/trading/*` n'ont pas l'en-tête.
7. **Garde Express** (`server/middleware/localMutationGuard.ts`) : contournements possibles ? Exemples : `Host` avec
   port, IPv6 `[::1]`, absence d'`Origin` sur une requête simple, `X-Forwarded-*`.

## 4. Fichiers modifiés

La liste exacte figure dans `quant/docs/VALIDATION_V041.md` §9, calculée contre la sauvegarde
`~/traider-pro-backups/2026-11-04-pre-v0.4.1/SHA256SUMS.txt`. Code de recherche concerné :
- `quant/src/ai_trader_optimizer/research/{inference,registry}.py` (nouveaux) ;
- `quant/src/ai_trader_optimizer/research/{study,stats,labels,robustness,__init__}.py`.

## 5. Verdicts demandés

Donne trois verdicts séparés :
1. fiabilité technique ;
2. fiabilité statistique sur les scénarios testés, en disant si mes conclusions de `VALIDATION_V041.md` §11 sont
   trop favorables ;
3. aptitude à évaluer des stratégies réelles sur XAUUSD.
