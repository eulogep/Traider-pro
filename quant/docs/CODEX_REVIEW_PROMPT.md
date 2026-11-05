# Prompt de revue indépendante — à donner à Codex

> Version la plus récente (workspace complet, correctifs 0.2.1) : `../../docs/handoffs/CODEX_REVIEW_HANDOFF.md`.

Tu es relecteur indépendant d'un laboratoire de backtesting Python (XAUUSD, M1) situé dans
`quant/`. Il ne doit **jamais** envoyer d'ordre à un courtier. Lis d'abord `AGENTS.md`,
`docs/ARCHITECTURE.md`, `docs/DECISIONS.md`, `docs/KNOWN_LIMITATIONS.md`.

Installation : `python3.12 -m venv .venv && .venv/bin/pip install -e '.[dev]' && .venv/bin/python -m pytest -q`.

Ne modifie pas le code directement : produis un rapport (fichier `docs/CODEX_REVIEW.md`) listant chaque problème avec
fichier:ligne, gravité, scénario concret qui le déclenche, et si possible un test pytest qui échoue aujourd'hui.

## Points à auditer en priorité
1. **Fuites temporelles** — `backtest/engine.py` : la décision à la bougie *i* ne lit-elle vraiment que
   `signals[i-1]` ? `strategies/ema_trend_3bars.py`, `features/indicators.py`, `data/resample.py`
   (`align_higher_timeframe`) : une valeur future peut-elle entrer ?
2. **Calcul financier** — prix d'entrée/sortie BID/ASK, gaps (`SL_GAP`), TP, commissions, `spread_cost`,
   `slippage_cost`, `r_multiple`, equity MTM, drawdown (`analytics/metrics.py`). Vérifie les signes pour les SELL.
   Cas `price_side = "mid"`.
3. **Sizing et risque** — `risk/guardian.py` : `position_size`, arrondi, `max_lot`, budget journalier avec risque
   prévu, drawdown, pertes consécutives (`scope` day/run), réinitialisation journalière par fuseau, contrôle
   anti-martingale `RISK_ABOVE_BUDGET`. Un chemin peut-il ouvrir un trade alors que le Guardian aurait dû refuser ?
   Une exception peut-elle contourner le fail-closed ?
4. **Gestion des positions** — sortie et nouvelle entrée dans la même bougie, sorties temps/session avant SL/TP,
   position ouverte à travers un trou, `END_OF_DATA` avec `trade_end`.
5. **Validation des données** — `data/validation.py` : fuseaux, DST, détection du timeframe (mode des écarts),
   désalignement, classification des trous, format MT5, exactitude des flottants, empreinte `fingerprint`.
6. **Reproductibilité** — `run_id`/`result_hash` couvrent-ils tout ce qui influe sur le résultat ?
   `storage/catalog.py` : détection d'altération, injection SQL (requêtes paramétrées ?), chemins.
7. **Sécurité** — aucune dépendance réseau / broker ; `.streamlit/config.toml` limite à localhost ; aucun secret.
8. **Tests insuffisants** — repère les tests qui passeraient même si le code était faux.
9. **Régressions** — `tests/test_core.py` et le test d'équivalence avec `core.py` (référence v0.1 figée).

Les propositions seront évaluées et testées avant intégration ; signale ton niveau de certitude pour chacune.
