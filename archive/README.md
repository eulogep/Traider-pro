# Archive

Code conservé pour mémoire, **jamais importé** par le produit.

- `legacy-student-ai-trader-optimizer/` — ancien script étudiant (actions/crypto via yfinance, RandomForest), copié
  d'un autre projet. Non réutilisé : backtest avec look-ahead (signal et exécution sur la même clôture), aucun coût,
  cible ML mal étiquetée, résultats du README non reproductibles, `venv/` Linux inutilisable sur cette machine.
  Diagnostic : `../docs/project/CONSOLIDATION_AUDIT.md`.

- `legacy-ui-mt5-mock/` — ancienne interface « terminal MT5 » de la v0.2, rangée ici le 2026-11-05 :
  - fichiers : `MT5Connection`, `MT5Trading`, `TradingChart`, `Navigation`, `DemoDataBanner`, hooks `useMT5` et
    `hooks/trading/*`, `mt5Service`, `mt5Store`, page `Placeholder`, types `shared/types/trading.ts` ;
  - plus aucune page ne les importait depuis la refonte de l'interface (vérifié par analyse des imports à partir de
    `client/main.tsx`, du serveur et des tests) ;
  - ils simulaient une connexion et des ordres MT5 que le produit ne fait pas et ne doit pas faire.

  Chemins d'origine conservés sous ce dossier. Le dossier est hors du typage et du build : ces fichiers ne sont pas
  maintenus.

- `legacy-netlify-functions/` : adaptateur `serverless-http` qui exposait l'Express de démonstration sur Netlify.
  Il était en panne en production (« Cannot find module 'express' ») et a été retiré du déploiement le 2026-11-05.
  Netlify ne sert plus que la vitrine statique (`../docs/project/DEPLOYMENT.md`).

Le moteur quantitatif actuel est dans `../quant/` ; l'interface actuelle dans `../client/`.
