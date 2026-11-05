# AI Trader Optimizer — moteur quantitatif (v0.5.0)

Moteur local d'analyse, de backtesting et de recherche (XAUUSD / Forex, M1). Il est consommé de deux façons :
- par l'**API HTTP** v1, qu'utilise l'application React (pages Backtests, Validation, Bot Analysis, Audit d'EA) ;
- par une **console de recherche Streamlit**, en français.

Carte complète du dépôt et règles : `../AGENTS.md`. Index de la documentation : `../docs/README.md`.

> **SÉCURITÉ :** simulation uniquement. Aucun accès courtier, aucun identifiant demandé, aucune fonction d'envoi
> d'ordre, trading réel et démo désactivés (non implémentés). Aucun modèle IA entraîné. Une simulation ne garantit
> aucune performance future.

## Démarrer (Mac / Linux ; Windows : `.venv\Scripts\Activate.ps1`)

```bash
cd quant
python3.12 -m venv .venv          # validé avec Python 3.12.14 ; 3.15 n'a pas encore de roues pandas
source .venv/bin/activate
pip install -r requirements.lock  # versions exactes validées (rejeu reproductible)
pip install --no-deps -e .
python -m pytest -q               # 215 tests
streamlit run app.py              # console de recherche : http://localhost:8501 (locale uniquement)
```

### Application complète (React → API Python → moteur)
Deux terminaux, depuis la racine du dépôt :
```bash
pnpm quant:api    # API FastAPI sur 127.0.0.1:8765 (doc interactive : http://127.0.0.1:8765/docs)
pnpm dev          # React sur http://localhost:8080 → page « Backtests » ; /api/v1 relayé vers l'API
```
Vérifications : `pnpm test` (dont l'intégration React ↔ API), `pnpm typecheck`, `node e2e/backtest-flow.mjs`.
Production locale : `pnpm build && pnpm quant:api` puis `pnpm start` (Express relaie `/api/v1`) ; contrôle :
`node e2e/production-smoke.mjs`. Mode de risque imposé : `ATO_RISK_POLICY=supervised pnpm quant:api`.

### Environnement reproductible
Python 3.12.14 + `requirements.lock` (pandas 2.3.3, numpy 2.5.4, pydantic 2.14.2, fastapi 0.162.0, starlette 1.10.0,
streamlit 1.66.1…) ; Node 26.8.1 + pnpm 10.14.0 + `pnpm install --frozen-lockfile`. Ne mettez pas à jour une
bibliothèque scientifique sans relancer la suite et vérifier la reproduction des runs (l'empreinte de code ne couvre pas
les versions de bibliothèques).

Démonstration en ligne de commande (prix fictifs) : `python scripts/demo_cli.py` (ajouter `--legacy-rules` pour les
règles v0.1).

## Parcours utilisateur
1. **Market Data** — importer un CSV historique (`timestamp,open,high,low,close`, ou export MetaTrader 5
   `<DATE> <TIME> <OPEN> …`), indiquer la source et le fuseau. Le fichier est refusé entièrement en cas d'erreur ;
   les trous sont signalés, jamais comblés. Bouton « Générer le jeu synthétique » pour une démo étiquetée.
   Exemple fictif : `examples/SYNTHETIQUE_demo_xauusd_m1.csv` (à déclarer « Synthétique »).
2. **Strategy Lab** — choisir la stratégie (baseline illustrative), ajuster ses paramètres dans leurs bornes,
   comparer des variantes (in-sample / hors échantillon).
3. **Risk Management** / **Settings** — limites de risque (fail-closed) et spécifications RÉELLES du contrat.
4. **Backtesting** — lancer, lire les métriques, exporter CSV/JSON, « Reproduire » (empreintes identiques).
5. **Trade Journal** — chaque transaction rejouée sur graphique, avec la règle et les valeurs connues au moment de
   la décision ; toutes les décisions refusées et leurs raisons.

## Organisation
```
app.py                         interface Streamlit (7 écrans)
src/ai_trader_optimizer/       data · features · strategies · risk · backtest · analytics · storage · ai · execution · ui
                               research (validation hors échantillon, expérimentale) · ea_audit (comportement d'EA,
                               pont MT5 local en lecture seule) · external_lab (simulations MT5 importées) · api
tests/                         pytest ; fixtures/mt5/ = rapports MT5 de référence (SHA-256 vérifiés)
research_campaign/             campagne statistique pré-enregistrée (protocole scellé, copies figées, résultats)
strategies/                    specs YAML versionnées : baseline/ · pilot_trader/ · third_party/
data/lab/                      données locales (non versionnées) : lab.db, raw/, datasets/, runs/
docs/                          architecture, décisions, limites, roadmap, changelog, validations par version,
                               EXTERNAL_LAB / REFERENCE_V370 / SECURITY_V05 (index : ../docs/README.md)
```

## Stratégie de référence
EMA rapide/lente + séquence 3 bougies (R-V-V / V-R-R) sur bougies **clôturées**, entrée à l'ouverture suivante,
SL = k × ATR, TP = R:R × SL. **Uniquement illustrative** : ce n'est pas la stratégie du trader pilote et aucun
avantage statistique n'est supposé. Sa stratégie MACD M15/M1 est un brouillon non exécutable tant que ses règles ne
sont pas formalisées (`strategies/pilot_trader/`).

## Limites principales
Bougies OHLC (pas de ticks), coûts fixes, SL prioritaire si SL et TP dans la même bougie, gaps exécutés au-delà du
stop, pas de marge/swap/conversion, contrat 100 oz/lot = hypothèse. Détails : `docs/KNOWN_LIMITATIONS.md`.

Cahier des charges : `docs/CAHIER_DES_CHARGES.md` · préparation de l'entretien : `docs/ENTRETIEN_TRADER.md`.
