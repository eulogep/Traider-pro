# Audit de consolidation — workspace `traider pro` (2026-11-03)

Objectif : passer de plusieurs prototypes à **un seul produit** (interface unifiée, backend métier, moteur
quantitatif fiable) sans réécrire ce qui fonctionne et sans opération Git destructive.

## 1. Diagnostic : ce que contient réellement chaque dossier

> Noms à la date du diagnostic. **Renommage effectué depuis** : `ai-trader-optimizer-v0.1/` → `quant/`,
> `ai-trader-optimizer/` → `archive/legacy-student-ai-trader-optimizer/` (voir §6, étape 7).

| Dossier | Rôle réel (vérifié dans le code) | Technologies | Fonctionnel ? | Données |
|---|---|---|---|---|
| `client/` | SPA « Traider Pro » : 7 pages (Index, Dashboard, Trading MT5, Optimizer, Backtest, Automation, Settings), ~8 700 lignes hors `components/ui` | React 18, Vite 7, TypeScript, Tailwind 3, shadcn/Radix, Recharts, React Query (non utilisé pour les données) | Interface **maquette**. Seuls 3 hooks appellent l'API (`useBacktest`, `useOptimizer`, `saveSettings`) ; les pages Backtest/Dashboard/Automation affichent des constantes codées en dur | **Inventées** (constantes, `Math.random`) |
| `client/lib/mt5Service.ts` | « Terminal MT5 » simulé dans le navigateur : prix aléatoires, compte fictif « John Trader », ordres simulés | TS | Simulation seulement : **aucune connexion MT5 réelle** | Aléatoires |
| `server/` | Express 5 intégré à Vite (port 8080) : `/api/analytics/*`, `/api/optimize*`, `/api/backtest*`, `/api/settings*` | Express 5, zod, dotenv | Toutes les routes métier renvoient des **résultats fabriqués** (ex. win rate 78,4 %, profit factor 2,31 ; optimisations `75 + Math.random()*15` %). Seul `/api/settings` persiste réellement (fichier JSON) | Inventées |
| `shared/` | Types TS partagés (`api.ts` d'exemple, `types/trading.ts` non suivi) | TS | Types sans contrat serveur réel | — |
| `netlify/` | Adaptateur serverless de l'Express | serverless-http | Déploiement possible du mock (non vérifié) | — |
| `ai-trader-optimizer/` | **Autre projet** : script étudiant copié d'un autre chemin (`/home/euloge/.../Alternance_Data_System/traider ai`), actions/crypto via yfinance, RandomForest | Python, pandas, sklearn, matplotlib | Non exécutable ici (venv Linux). Backtest **avec look-ahead** (signal et exécution sur la même clôture), sans coûts ; cible ML mal étiquetée sur la dernière ligne ; résultats du README (« win rate 58 % ») non reproductibles | yfinance |
| `ai-trader-optimizer-v0.1/` | **Laboratoire quantitatif v0.2.1** : import validé, stratégies versionnées, backtest sans look-ahead, Risk Guardian, analytics, catalogue reproductible, UI Streamlit 7 écrans | Python 3.12, pandas, pydantic, Streamlit, SQLite | **Oui**, 115 tests | Réelles importées ou synthétiques **étiquetées** |

Les dossiers n'appartiennent pas au même projet : `ai-trader-optimizer/` est un import d'un projet antérieur,
`client/`+`server/`+`shared/` viennent du template Builder.io « Fusion Starter » (dépôt GitHub `eulogep/Traider-pro`),
`ai-trader-optimizer-v0.1/` est le laboratoire construit pour ce projet.

### Duplications
| Fonction | Implémentations existantes | Source de vérité retenue |
|---|---|---|
| Backtest | `ai-trader-optimizer/backtest`, Express `/api/backtest` (mock), `client/pages/Backtest.tsx` (constantes), **moteur Python v0.2** | Moteur Python |
| Indicateurs | `ai-trader-optimizer/analysis` (lib `ta`), **`features/indicators.py`** | Python |
| « Optimisation IA » | Express `/api/optimize` (aléatoire), `Optimizer.tsx`, RandomForest étudiant, **interfaces `ai/`** | Interfaces Python (aucun modèle tant qu'aucun dataset réel) |
| Réglages | `localStorage` + `data/settings.json` (Express) + SQLite du labo | Catalogue Python |
| Types | `shared/types/trading.ts`, interfaces de `mt5Service.ts`, modèles pydantic | Pydantic → TypeScript généré (OpenAPI) |
| Spécifications contrat | `mt5Service` (100 en dur), `shared/instruments.ts` (ajouté), `risk/guardian.py::ContractSpec` | `ContractSpec` Python ; `shared/instruments.ts` reste limité au simulateur pédagogique |

### Technologies réellement utilisées
Node 26 / pnpm 10, React 18, Vite 7, Express 5, TypeScript 5.9 (mode strict activé **dans des modifications non
commitées**), vitest 3 ; Python 3.12, pandas 2.3, numpy 2.5, pydantic 2, Streamlit 1.66, SQLite. Déclarées mais non
utilisées : `three`/`@react-three/*`, `framer-motion`, React Query (pour les données), `MT5_WS_URL`/`MT5_API_KEY`.

## 2. Recommandation : application principale

**Produit unique « AI Trader Optimizer »** composé de :
1. **Interface : le frontend React existant (`client/`)**, réutilisé pour sa coquille (routing, navigation, design
   system shadcn, graphiques Recharts, mise en page des réglages). Ses pages sont rebranchées une à une sur de vraies
   données ; les données inventées disparaissent.
2. **Backend métier + moteur quantitatif : le package Python `ai_trader_optimizer`**, exposé par une API HTTP
   (FastAPI recommandé : schémas pydantic déjà en place, OpenAPI → types TypeScript générés).
3. **Express : retiré à terme.** Il ne contient aucune logique métier réelle ; le garder créerait deux backends.
   Pendant la migration il continue de servir le SPA et les routes mock ; Vite redirige `/api/v1` vers Python.
4. **Streamlit : console de recherche** conservée tant que React n'a pas la parité (Market Data, Strategy Lab,
   Trade Journal, Risk Management n'existent pas côté React). Il appelle les mêmes services Python ; aucun
   doublon de logique.

Pourquoi pas « Streamlit seul » : interface limitée pour un produit (navigation, état, composants riches). Pourquoi
pas « React + Express pour la logique » : réimplémenter en TypeScript le moteur testé et l'écosystème
pandas/ML serait une réécriture inutile et risquée. Pourquoi pas Express + Python : trois runtimes pour un
utilisateur local.

**Décision à valider par vous** avant d'ajouter FastAPI (nouvelle dépendance) — rien n'a été installé à ce titre.

## 3. Interfaces cibles (contrat v1 proposé)

```
React (client/)  ──HTTP JSON /api/v1──►  API Python (ai_trader_optimizer/api, FastAPI)
                                             │  appelle uniquement services.py
                                             ▼
                          services.py → data · strategies · backtest · risk · analytics · storage
```

| Méthode | Route | Corps / réponse |
|---|---|---|
| GET | `/api/v1/health` | version, engine_version, code_hash, `live_trading_enabled: false` |
| GET / POST | `/api/v1/datasets` | liste `DatasetMeta` / import multipart (CSV + source + fuseau + nature) → `QualityReport` (422 si refus) |
| GET | `/api/v1/datasets/{id}` · `/bars?from&to&max_points` | méta + qualité · bougies (sous-échantillonnées) |
| GET | `/api/v1/strategies` | `StrategySpec` + `runnable_problems` |
| POST | `/api/v1/backtests` | `{dataset_id, strategy_key, config: BacktestConfig}` → `{manifest, metrics}` (synchrone : ~4 s pour 1 an M1) |
| GET | `/api/v1/backtests` · `/{run_id}` · `/trades` · `/decisions` · `/equity?max_points` | résultats du catalogue |
| POST | `/api/v1/backtests/{run_id}/reproduce` | `{identical, stored_hash, new_hash}` |
| POST | `/api/v1/variants/compare` | comparaison IS / hors échantillon |
| GET / PUT | `/api/v1/settings/defaults` · `/settings/risk` | coûts, contrat, compte · `RiskConfig` |

Règles : **aucune route d'ordre** ; pas de champ identifiant/mot de passe ; écoute `127.0.0.1` ; erreurs = 4xx
avec message français ; types TS générés dans `shared/api-v1.ts` (jamais écrits à la main).

## 4. Correctifs critiques réalisés (détails et preuves : `docs/CODEX_REVIEW_HANDOFF.md`)

**App React / Express**
- C1 Mot de passe MT5 et token Telegram stockés en clair dans `localStorage` **et** dans `data/settings.json`
  (fichier non ignoré par Git), renvoyés par `GET /api/settings` → nettoyés partout (`shared/security.ts`),
  purge des anciennes valeurs, `data/` ignoré. Test serveur qui **échoue sur le code d'origine** (vérifié).
- C2 CORS ouvert à toute origine → limité à `localhost`/`127.0.0.1`.
- C3 Serveur de dev sur `::` (réseau) et serveur de prod sur toutes les interfaces → `localhost`/`127.0.0.1` par défaut.
- C4 Chemin d'ordres sans aucun contrôle de risque (`placeMarketOrder`, `placePendingOrder`, `closePosition`) → désactivé.
- C5 P&L du simulateur : 100 unités/lot pour tous les symboles (EURUSD 1 000× trop faible), pas de conversion JPY/CHF ;
  spread qui dérivait (l'ASK n'était jamais mis à jour) ; spread en points faux pour l'or et le JPY → `shared/instruments.ts` testé.
- C6 Plantage `TypeError` de `MT5AccountSummary` (Dashboard, Trading) causé par la refonte non commitée de `useMT5.ts`.
- C7 `pnpm start` plantait au démarrage (route `"*"` refusée par Express 5).
- C8 Chiffres inventés présentés comme réels → bannière « Données de démonstration » sur tous les écrans.

**Laboratoire Python (v0.2.0 → v0.2.1)**
- P1 Stop plus proche que spread + glissement : perte réelle 2,2× le risque prévu → refus `STOP_INSIDE_SPREAD`.
- P2 Contrat incohérent avec les données (EURUSD dimensionné avec le contrat or → 50 lots) → `CONTRACT_SYMBOL_MISMATCH`,
  cohérence devise de cotation / symbole.
- P3 Objet stratégie injecté contournant les contrôles (brouillon, martingale, tiers) → refusé.
- P4 Run écrasé par des résultats différents ; `run_id` ignorant la version du code → empreinte de code, refus d'écraser.
- Vérifié sans défaut : signe du P&L SELL, BID/ASK, mid, identités comptables métriques = trades = courbe (16 runs testés).

## 5. Situation Git (lecture seule, rien n'a été modifié dans l'index)

- Dépôt racine `main`, remote `github.com/eulogep/Traider-pro` (+ branche distante `snyk-upgrade-…`). Aucun stash.
- **99 fichiers modifiés avant cette session, dont 86 uniquement par conversion LF→CRLF** ; 13 avec de vrais changements
  (dont `tsconfig.json` en mode strict, refonte `useMT5.ts`, `server/index.ts`). Cette session en modifie 9
  (liste dans le handoff), en préservant leurs fins de ligne CRLF.
- Non suivis : les deux dossiers Python, `README.md`, des fichiers client/server/shared ajoutés, et mes nouveaux fichiers.
- `.env` est **versionné depuis le commit initial** et donc public sur GitHub ; il ne contient que `PING_MESSAGE` et un
  placeholder `__BUILDER_PUBLIC_KEY__` (pas de vraie clé). `.gitignore` contient `!.env` qui force son suivi.
- Simulation `git add -n .` : n'ajouterait ni venv, ni `node_modules`, ni données, ni caches, ni secrets.

### Structure de dépôt proposée (non appliquée)
```
traider pro/                     dépôt unique
├── client/                      interface React (unique UI)
├── shared/                      types TS (api-v1.ts généré) + simulateur pédagogique
├── server/                      Express — retiré à l'étape 5 (ou réduit à un serveur statique)
├── quant/                       ✅ ex-ai-trader-optimizer-v0.1 (package Python + future API + console Streamlit)
├── archive/legacy-student-ai-trader-optimizer/   ✅ ex-ai-trader-optimizer, jamais importé
├── docs/                        documentation produit (ce dossier)
├── .gitattributes               * text=auto eol=lf
└── .env.example                 sans valeur ; .env retiré du suivi
```

## 6. Plan de migration non destructif (chaque étape validée avant la suivante)

| Étape | Action | Réversibilité |
|---|---|---|
| 0 | **Vous** relisez vos 13 vrais changements + mes 8 fichiers ; créez une branche `consolidation` | — |
| 1 | Normaliser les fins de ligne dans un commit dédié (`.gitattributes` + `git add --renormalize .`) **ou** restaurer le LF : supprime 86 diffs parasites | commit isolé, `git revert` |
| 2 | Commit de vos changements réels, puis commit de mes correctifs (séparés) | idem |
| 3 | Commit du laboratoire Python (ignorés vérifiés) ; `git rm --cached .env`, ajout `.env.example`, retrait de `!.env` | le fichier local reste intact |
| 4 | ✅ **Fait (v0.3)** : `ai_trader_optimizer/api` (FastAPI) + tests + proxy Vite `/api/v1` → `127.0.0.1:8765` ; types `shared/quant-api.ts` (écrits à la main, vérifiés par test d'intégration) | ajout pur |
| 5 | 🟡 **En cours** : Backtest ✅ (v0.3). Reste : Dashboard → Settings (risque, contrat, coûts ; suppression des champs secrets) ; créer Market Data, Strategy Lab, Trade Journal, Risk ; Optimizer → « comparaison de variantes » ; Automation et Trading → « non disponible » ou simulateur pédagogique sans ordre | page par page |
| 6 | Supprimer les routes mock Express une fois remplacées ; décider du sort d'Express et de Streamlit | après parité |
| 7 | ✅ **Fait** (2026-11-03) : `mv` vers `quant/` et `archive/` (dossiers non suivis : aucun historique en jeu) | `mv` inverse |

Aucun push sans votre accord.

## 7. Prochaines étapes pour la stratégie du trader
1. Entretien (`quant/docs/ENTRETIEN_TRADER.md`) : règles MACD exactes, horaires/fuseau, SL/TP,
   limites, 3 trades valides + 3 refusés avec captures, export MT5 M1 + M15 de son courtier (avec `<SPREAD>`),
   spécifications réelles du contrat XAUUSD, accord écrit sur l'usage de sa stratégie.
2. Remplir `strategies/pilot_trader/macd_m15_m1.v0.1.0.yaml` → version `1.0.0` `active` ; implémenter la classe
   (MACD et alignement M15→M1 sans fuite déjà testés).
3. Tests « exemples annotés » : chaque trade valide doit être pris, chaque refusé refusé, sur ses données.
4. Backtest sur ses données réelles, comparaison avec la baseline à coûts égaux, période hors échantillon vierge.
5. Seulement ensuite : modèle IA de filtrage (protocole `ai/`), puis éventuellement démo.

## 8. Stratégie de sauvegarde et de commits proposée (v0.3 — rien n'a été appliqué)

État constaté au début de la v0.3 : 99 fichiers suivis modifiés, dont **82 uniquement par CRLF** (vérifié octet par
octet, aucun fichier mixte) et 17 avec un vrai contenu ; après la v0.3 : 27 avec un vrai contenu, 72 CRLF seul.
`.env` : placeholder `__BUILDER_PUBLIC_KEY__` + `PING_MESSAGE`, aucun secret.

1. **Sauvegarde durable avant tout** (le scratchpad de session est temporaire) :
   `git diff --binary > ~/traider-pro-$(date +%F).patch` et
   `tar czf ~/traider-pro-untracked-$(date +%F).tgz --exclude=node_modules --exclude=.venv --exclude=venv --exclude=dist $(git ls-files --others --exclude-standard)`.
2. `git switch -c consolidation/v0.3` (aucun push).
3. **Neutraliser le bruit CRLF sans réécrire les fichiers** : ajouter `.gitattributes` (`* text=auto eol=lf`) ; Git
   compare alors le contenu normalisé et les 72 fichiers CRLF seul disparaissent de `git status`. Les fichiers locaux
   restent CRLF jusqu'à un checkout (pas de normalisation massive).
4. Commits séparés, relus avec `git add -p` :
   a. vos changements d'origine (`tsconfig.json` strict, `useMT5.ts`, `Index.tsx`, …) ;
   b. sécurité 0.2.1 (`shared/security.ts`, `settings.ts`, CORS, écoute locale, ordres désactivés) ;
   c. nettoyage TypeScript v0.3 (imports, `_req`, V3–V6) ;
   d. moteur Python `quant/` (le `.gitignore` exclut `.venv`, caches, `data/lab/`) + `archive/` ;
   e. API + page Backtests + tests + `e2e/` ; f. docs.
   Pour les fichiers qui mêlent vos changements et les miens (`App.tsx`, `mt5Service.ts`, `settingsContext.tsx`,
   `server/index.ts`, `node-build.ts`, `optimization.ts`, `Dashboard.tsx`, `Trading.tsx`, `TradingChart.tsx`,
   `Navigation.tsx`, `MT5Connection.tsx`), utiliser `git add -p` par bloc ou les committer ensemble avec un message explicite.
5. `.env` : `git rm --cached .env`, ajouter `.env.example` sans valeur, retirer `!.env` du `.gitignore`.
6. Vérifier avant chaque commit : `git diff --cached --stat`, `pnpm test`, `pnpm typecheck`, `pnpm quant:test`.

## 9. Plan de commits atomiques après V0.3.1 (à autoriser — rien n'a été appliqué)

Sauvegarde durable **déjà faite** hors du dépôt : `~/traider-pro-backups/2026-11-04-pre-v0.3.1/`
(`tracked-changes.patch` vérifié par application inverse, `untracked-files.tgz` incluant le package `data`,
preuves Codex, `HEAD.txt`, `git-status.txt`). Avant tout commit, refaire une sauvegarde du même type.

1. `git switch -c hardening/v0.3.1`.
2. **Commit 1 — B1 seul** : `.gitignore` (règles ancrées). Vérifier `git check-ignore -v quant/src/ai_trader_optimizer/data/*.py` → rien.
3. **Commit 2 — `.gitattributes`** (`* text=auto eol=lf`) pour neutraliser les 72 fichiers à fins de ligne seules, sans
   réécrire la copie de travail.
4. **Commit 3 — vos changements d'origine** (`git add -p` : `tsconfig.json`, `useMT5.ts`, `Index.tsx`, …).
5. **Commit 4 — sécurité 0.2.1 + nettoyage TS 0.3** ; **Commit 5 — `quant/`** (moteur, API, tests, `requirements.lock`) ;
   **Commit 6 — intégration React + `e2e/`** ; **Commit 7 — docs + `docs/audits/`**.
6. **`.env`** (procédure, sans supprimer le fichier local) :
   ```bash
   cp .env ~/traider-pro-backups/env.backup          # copie de sûreté
   git rm --cached .env                              # retire du suivi, le fichier local reste
   # dans .gitignore : remplacer la ligne « !.env » par « .env » et « .env.* » + « !.env.example »
   git add .env.example .gitignore && git commit -m "Stop tracking .env; add .env.example"
   ```
   L'historique Git conserve l'ancien `.env` (placeholder seulement, aucun secret) ; aucune réécriture d'historique n'est proposée.
7. Avant chaque commit : `git diff --cached --stat`, `pnpm test`, `pnpm typecheck`, `pnpm quant:test`, et une recherche
   de secrets sur les fichiers indexés.
