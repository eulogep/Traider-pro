# Handoff — contre-audit indépendant de la v0.5 « External Bot Analysis & Optimization Lab » (2026-11-05)

**Ta mission : contester** l'importateur MT5, le catalogue immuable, les reconstructions et les hypothèses de réduction
du risque.

Documents de référence :
- `quant/docs/EXTERNAL_LAB.md` : import, schéma, architecture et limites ;
- `quant/docs/REFERENCE_V370.md` : cas de référence ;
- `quant/docs/SECURITY_V05.md` ;
- `quant/docs/VALIDATION_V05.md`.

Le handoff v0.4.1 (`docs/handoffs/CODEX_HANDOFF_V041.md`) reste ouvert et séparé.

**Règles**
- Aucun compte de trading, aucun ordre, aucun secret, aucun push, aucune opération Git destructive.
- Ne lance **jamais** un `.ex5`.
- Travaille sur une copie. Le dépôt n'a pas de commit et `quant/` n'est pas suivi par Git.
- Rapport attendu dans `docs/CODEX_REVIEW_V05.md`. Pour chaque constat : fichier:ligne, gravité, scénario, test
  proposé, certitude.

## 1. Reproduire
```bash
cd quant
(cd tests/fixtures/mt5 && shasum -a 256 -c SHA256SUMS)          # fixtures intactes
.venv/bin/python -m pytest -q                                   # 316 passés
.venv/bin/python -m pytest -q tests/test_external_lab.py tests/test_ea_audit.py
.venv/bin/ruff check --no-cache src tests app.py scripts
cd .. && pnpm test && pnpm typecheck && pnpm build
node e2e/pages-tour.mjs                                         # 52/52 (importe le vrai rapport par l'interface)
node e2e/backtest-flow.mjs --api-down                           # 4/4
```

Import manuel du cas de référence :
```bash
cd quant && .venv/bin/python - <<'EOF'
import tempfile; from pathlib import Path
from ai_trader_optimizer.external_lab import catalog as C
s = C.import_file(Path(tempfile.mkdtemp()), "r.html",
                  Path("tests/fixtures/mt5/Gold_Grid_V370_MT5_Baseline_2026.html").read_bytes(), 100.0, "codex")["simulation"]
print(s["validation"]["status"], s["pairing"], s["collapse"]["losing_total"])
EOF
```

## 2. Affirmations à réfuter
| Affirmation | Où |
|---|---|
| Les 23 indicateurs MT5 du rapport V3.70 sont recalculés à l'arrondi près à partir des deals | `external_lab/reconstruct.py::deal_metrics`, `reconcile` |
| 314/314 clôtures sont expliquées par l'appariement « match » (profit MT5 reproduit au centime) ; FIFO 299, LIFO 162 | `reconstruct.py::_pair` |
| La taille de contrat (100) est **déduite** des profits MT5, non supposée | `infer_contract_size` |
| Les dix pertes finales (deals 620 à 629) font −51 990,13, sur 9,38 lots, avec 5 stop-out et 5 fin du test | `collapse` |
| Le test s'arrête le 30/07 au lieu du 31/10, au moment du stop-out | `period_check` |
| Le HTML et le XLSX donnent les mêmes deals (même `test_key`) | catalogue |
| Une simulation altérée, même ré-empreintée, est refusée | `catalog.verify`, `simulation.semantic_problems` |
| Les archives et XLSX malveillants sont refusés avant toute écriture | `mt5_report._zip_members`, `_xml` |

## 3. Points faibles connus : examine en priorité
1. **Appariement sans identifiant de position.** La règle « match » choisit, parmi les positions de même volume, celle
   dont le profit reproduit le profit MT5.
   - Deux positions de même volume et même prix d'entrée sont indiscernables. Le choix n'a pas d'effet sur le P&L, mais
     il en a un sur les durées.
   - Choisir la règle qui « explique le plus » est-il légitime ? C'est une identification, pas un ajustement d'un
     résultat, mais conteste-le.
2. **Équité estimée** : elle est marquée au prix du deal, aux seuls instants d'opération. Elle sous-estime la perte
   latente réelle entre deux opérations. MT5 donne un drawdown d'équité de 52 040,35, contre 51 990,13 en solde.
3. **Hypothèses de réduction du risque.**
   - Seul « arrêt définitif à plat après un drawdown réalisé » est qualifié `exact`. Les autres sont des
     `approximation`, et le stop-out observé reste dans leur parcours.
   - Vérifie qu'aucune n'est présentée comme un backtest.
   - Le résultat « plafond à 3 lots : +17 198 » est-il trop visible malgré ses réserves ?
4. **Hypothèses sur le robot** (`simulation.findings`) :
   - « contrôle de drawdown désactivé » est déduit des seuls noms `InpDDMode=0` et `InpDDValue=0.0` ;
   - « lots proportionnels au solde » repose sur un coefficient de variation de 1 %.

   Les libellés « hypothèse » sont-ils suffisants ?
5. **Lecteur** :
   - formats seulement tels qu'observés sur un build MT5 (6275) et en anglais ;
   - les en-têtes français sont prévus mais jamais confrontés à un vrai rapport français ;
   - les rapports d'optimisation et les `.set` ne sont pas lus.
6. **Pont MT5 local** (`ea_audit/mt5_local.py`) : liste des dossiers, liens symboliques, fichiers géants, concurrence
   avec MT5 en train d'écrire. Le mot « mt5 » est autorisé sur 3 routes seulement : la liste blanche est-elle étanche ?
7. **Garde de taille** : `UPLOAD_PATHS` a été corrigé pendant le développement (§3 de `SECURITY_V05.md`). Reste-t-il
   une route de téléversement non couverte ?
8. **Phase IA** : non commencée, volontairement (`VALIDATION_V05.md` §6).

## 4. Verdicts demandés
Donne trois verdicts séparés :
1. fiabilité de l'import et de l'intégrité ;
2. exactitude des analyses et honnêteté des qualifications ;
3. utilité pour décider de ne pas utiliser, ou de retester, un robot externe.
