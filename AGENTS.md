# AGENTS.md — guide d'entrée pour toute personne ou tout agent (Claude, Codex…) qui travaille sur ce dépôt

**Traider Pro / AI Trader Optimizer** est un laboratoire de recherche en **simulation uniquement** pour stratégies de
trading sur l'or (XAUUSD) et le Forex.

| Couche | Rôle |
|---|---|
| Interface React | **affiche** |
| Moteur Python (`quant/`) | **calcule** : il est la seule source de vérité financière |
| Express | relais local et garde des mutations |

À lire d'abord : `README.md`, puis `docs/README.md` (index de toute la documentation). Les règles spécifiques au
moteur sont dans `quant/AGENTS.md` ; elles s'appliquent en plus de celles-ci.

## 1. Règles non négociables
1. **Aucun ordre, réel ou démo.**
   - Ne jamais ajouter de route d'ordre, d'appel à un courtier, d'`order_send` ni d'`import MetaTrader5`.
   - Ne jamais activer `LIVE_TRADING_ENABLED` / `DEMO_TRADING_ENABLED` (`quant/src/ai_trader_optimizer/safety.py`).
   - Les listes blanches de routes doivent rester vertes : `quant/tests/test_api.py` et
     `client/lib/quantApi.integration.spec.ts`.
2. **MT5 en lecture seule seulement.** Le propriétaire a autorisé, le 2026-11-05, un pont **local** qui lit les
   rapports du terminal installé (`quant/src/ai_trader_optimizer/ea_audit/mt5_local.py`).
   - Ne jamais lire `config/` ni `*.dat`.
   - Ne jamais exécuter un `.ex5`.
   - Le mot « mt5 » n'est permis que sur les routes en lecture seule listées dans ces tests. On étend la liste
     explicitement ; on ne renomme jamais une route pour la contourner.
3. **Aucun secret** dans le code, les tests, les logs ou les commits. `.env` ne contient que des placeholders ; le
   modèle est `.env.example`.
4. **Aucun calcul financier en TypeScript.** React affiche les valeurs de l'API (`shared/quant-api.ts`), y compris les
   textes de constats et d'hypothèses.
5. **Ne jamais présenter un résultat simulé comme une performance réalisable**, ni une méthode expérimentale comme
   validée. Les approximations sont qualifiées (`exact` / `approximation` / `non_simulable`).
6. **Méthodes statistiques** : on ne les change qu'à travers un protocole pré-enregistré
   (`quant/research_campaign/PROTOCOL.md`). Règles à respecter :
   - écarts datés avant exécution ;
   - jamais de réglage choisi d'après les résultats ;
   - ne pas lancer `ruff --fix` dans ce dossier.
7. **Préserver le travail du propriétaire.**
   - Pas de reset, clean, suppression destructive, commit, push ou déploiement sans accord explicite.
   - Les fichiers suivis sont en CRLF dans la copie de travail mais stockés en LF : indexer avec
     `git -c core.autocrlf=input add …`, et ne jamais normaliser massivement les fins de ligne.
8. **Intégrité.** Runs, études et simulations externes sont publiés en création seule, en lecture seule, vérifiés à
   chaque lecture. Ne jamais « réparer » un artefact à la main : le refaire.

## 2. Carte du dépôt
```
client/                 React 18 + TypeScript + Vite + Tailwind (pages dans client/pages, composants par domaine)
  components/<domaine>/ backtest, research, bots (Bot Analysis), ea (Audit d'EA), layout, ui (bibliothèque shadcn)
  lib/                  quantApi.ts (client de l'API v1), format.ts, modules.ts (navigation), settingsContext
server/                 Express : relais /api/v1 → Python (quantProxy.ts), garde des mutations (middleware/)
shared/                 types partagés ; quant-api.ts = contrat TypeScript de l'API Python
quant/                  moteur Python 3.12 (paquet ai_trader_optimizer) — voir quant/README.md
  src/…/backtest        moteur de simulation (versionné : ENGINE_VERSION)
  src/…/risk            Risk Guardian (fail-closed)
  src/…/research        validation hors échantillon (expérimentale) — figée par research_code_hash
  src/…/ea_audit        audit de comportement d'EA + pont MT5 local en lecture seule
  src/…/external_lab    import, vérification, catalogue et analyse des simulations MT5 externes
  src/…/storage         catalogue, intégrité, publication atomique
  src/…/api             FastAPI (127.0.0.1:8765), garde locale, liste blanche des routes
  tests/                pytest ; tests/fixtures/mt5 = rapports MT5 de référence (SHA-256 vérifiés)
  research_campaign/    campagne statistique scellée (protocole, copies figées, résultats bruts)
  docs/                 documentation technique et rapports de version
docs/                   audits indépendants, passations Codex, base de connaissances, plan de projet
e2e/                    parcours navigateur réels (Chrome headless + vraie API)
archive/                code conservé pour mémoire, jamais importé (exclu du typage et du build)
```

## 3. Commandes
```bash
pnpm install
cd quant && python3.12 -m venv .venv && .venv/bin/pip install -r requirements.lock && .venv/bin/pip install --no-deps -e . && cd ..
pnpm quant:api            # API Python (redémarrer après toute modification Python : pas de rechargement auto)
pnpm dev                  # interface sur http://localhost:8080 (proxy /api/v1 → Python)

pnpm quant:test           # pytest (doit rester 100 % vert)
(cd quant && .venv/bin/ruff check --no-cache src tests app.py scripts)
pnpm test && pnpm typecheck && pnpm build
node e2e/pages-tour.mjs && node e2e/backtest-flow.mjs && node e2e/backtest-flow.mjs --api-down
pnpm build && node e2e/production-smoke.mjs
```

## 4. Ajouter quelque chose
| Je veux… | Étapes |
|---|---|
| **Une page** | 1. `client/pages/MaPage.tsx`<br>2. route dans `client/App.tsx`, au-dessus du `*`<br>3. entrée dans `client/lib/modules.ts`, avec son statut `engine` / `reference` / `locked`<br>4. étape dans `e2e/pages-tour.mjs`, avec la largeur téléphone |
| **Une route d'API** | 1. handler dans `quant/src/ai_trader_optimizer/api/app.py`<br>2. ajout **conscient** à `ALLOWED_ROUTES` (`quant/tests/test_api.py`)<br>3. type dans `shared/quant-api.ts`, méthode dans `client/lib/quantApi.ts`<br>4. si elle reçoit un fichier : l'ajouter à `UPLOAD_PATHS` (`api/security.py`) |
| **Un calcul financier** | 1. en Python, avec test<br>2. si cela change des décisions du moteur : nouvelle `ENGINE_VERSION` |
| **Une source externe (article, recherche)** | fiche `docs/knowledge/KB-NNN_*.md` (affirmation → état du code → exact ? → décision) avant de coder |
| **Un rapport MT5 de référence** | `quant/tests/fixtures/mt5/`, avec mise à jour de `SHA256SUMS` |

## 5. Documentation à tenir à jour
- `quant/docs/CHANGELOG.md`
- `quant/docs/KNOWN_LIMITATIONS.md`
- `quant/docs/ROADMAP.md`
- `quant/docs/DECISIONS.md`
- le rapport de validation de la version en cours (`quant/docs/VALIDATION_V*.md`), avec les résultats **exacts**,
  jamais supposés
- une passation dans `docs/handoffs/` pour chaque contre-audit

L'interface et les messages utilisateur sont en français.
