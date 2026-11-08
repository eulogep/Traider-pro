# Outils MetaTrader 5 (Strategy Tester uniquement)

Pilote le **Strategy Tester** de MT5 en ligne de commande (build macOS sous Wine) pour tester **nos** stratégies sur
l'historique du serveur, et les comparer au moteur Python. Simulation uniquement.

| Fichier | Rôle |
|---|---|
| `experts/ATO_ExportBars.mq5` | extrait les bougies réelles en CSV (aucune fonction d'ordre) |
| `experts/ATO_Baseline.mq5` | la stratégie de référence, avec les mêmes règles que le moteur Python |
| `run_tester.py` | compile, écrit la configuration de lancement, lance le testeur, récupère les résultats |
| `compare_engines.py` | compare MT5 et le moteur Python : signaux, trades, résultat |
| `results/` | sorties brutes, régénérables, hors Git |

```bash
# MT5 doit être fermé : le terminal se lance, teste, puis se ferme seul
python3 mt5/run_tester.py compile
python3 mt5/run_tester.py export   --from 2026.01.01 --to 2026.10.31
python3 mt5/run_tester.py baseline --from 2026.01.01 --to 2026.10.31 --model 1   # OHLC M1, quelques secondes
python3 mt5/run_tester.py baseline --from 2026.01.01 --to 2026.10.31 --model 4   # ticks réels, quelques minutes
cd quant && .venv/bin/python ../mt5/compare_engines.py --model 4
```

Dernier résultat : [`../quant/docs/MT5_TEST_BASELINE_2026.md`](../quant/docs/MT5_TEST_BASELINE_2026.md).

## Règles (vérifiées par `quant/tests/test_mt5_experts.py`)
- Les robots refusent de démarrer hors du testeur, et `ATO_Baseline` revérifie avant chaque ordre.
- `AllowLiveTrading=0` dans la configuration de lancement ; aucun identifiant lu, passé ou stocké : le terminal utilise
  le compte qui y est déjà enregistré.
- Seuls nos robots sont lancés, jamais un `.ex5` de tiers.
- Ajouter un robot est un acte conscient : il faut mettre à jour le test.

## À savoir
- **Fuseau du serveur MetaQuotes-Demo : `Europe/Athens`**, mesuré sur la pause quotidienne (162 reprises sur 166 à 18:00
  heure de New York). Un autre serveur peut avoir un autre fuseau : refaire la mesure avant d'importer ses données.
- **Spread** : une bougie M1 enregistre le spread minimal de la minute. Seul le modèle 4 (ticks réels) reflète le spread
  réellement payé.
- **Dossier des fichiers communs** : il suit l'utilisateur Wine (`drive_c/users/<utilisateur macOS>/…/Common/Files/ATO`).
