# AGENTS.md — conventions pour tout agent (Claude, Codex…) travaillant sur AI Trader Optimizer

## Exigences permanentes de sécurité (non négociables)
- **Aucun ordre sur un compte, réel ou démo** (seul le Strategy Tester, via `../mt5/`, simule des ordres) : ne jamais ajouter `order_send`, `import MetaTrader5`, appel réseau vers un courtier,
  ni modifier `LIVE_TRADING_ENABLED` / `DEMO_TRADING_ENABLED` dans `src/ai_trader_optimizer/safety.py`.
  `tests/test_metrics_storage_safety.py::test_no_broker_order_path_in_sources` doit rester vert.
- **Aucun secret ni identifiant** dans le code, les YAML, les tests ou les logs. Pas de formulaire de mot de passe.
- Pas de push, déploiement, exposition réseau (`.streamlit/config.toml` : `address = "localhost"`) ni migration
  destructive sans accord explicite du propriétaire.
- Ne jamais présenter un résultat comme une performance attendue. Les données synthétiques sont toujours étiquetées.

## Règles d'ingénierie
- Source de vérité : `storage/catalog.py` (SQLite + fichiers). Données brutes et validées immuables.
- **Fail-closed** : en cas de doute (contrat, données, stop, exception), le Risk Guardian refuse.
- **Pas de look-ahead** : une stratégie renvoie, ligne *i*, uniquement ce qui est connu à la clôture de *i* ; le
  moteur exécute à l'ouverture de *i+1*. Tout nouvel indicateur/stratégie doit passer le test de causalité par
  préfixe et le test de perturbation du futur (`tests/test_engine.py`).
- Les stratégies ne dimensionnent jamais les positions ; martingale/grille interdites.
- **Versionnement** : ne jamais modifier une spec YAML déjà utilisée par un run ; créer `nom.vX.Y.Z.yaml`.
- Stratégies du trader pilote dans `strategies/pilot_trader/`, tiers dans `strategies/third_party/`
  (refusées tant que `usage_rights: unclear`). Ne jamais inventer les règles du trader : `open_questions`.
- `src/ai_trader_optimizer/core.py` = référence v0.1 **figée** (test d'équivalence). Ne pas la modifier.
- Toute métrique non calculable honnêtement vaut `None` avec une raison dans `metrics["unavailable"]`.
- IA : modèle simple d'abord, comparé à la baseline à coûts égaux, validation chronologique/walk-forward,
  jeu de test final jamais utilisé pour l'ajustement.

## Commandes
```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'
python -m pytest -q            # doit rester 100 % vert
ruff check src tests app.py scripts
streamlit run app.py
python -m ai_trader_optimizer.api   # API v1, 127.0.0.1:8765
```
- L'API (`src/ai_trader_optimizer/api/`) ne doit **jamais** exposer de route d'ordre : `tests/test_api.py` vérifie la
  liste blanche exacte des routes. Toute nouvelle route doit y être ajoutée consciemment.
- React n'effectue aucun calcul financier : il affiche les valeurs de l'API (`shared/quant-api.ts`).

## Documentation à tenir à jour
`docs/ARCHITECTURE.md`, `ROADMAP.md`, `DECISIONS.md`, `TEST_REPORT.md` (résultats exacts, jamais supposés),
`KNOWN_LIMITATIONS.md`, `CHANGELOG.md`. UI et messages utilisateur en français.
