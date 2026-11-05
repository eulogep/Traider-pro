# Traider Pro — AI Trader Optimizer

**Laboratoire de recherche et d'analyse pour stratégies de trading sur l'or (XAUUSD) et le Forex.**
Il simule, vérifie et explique. Il ne promet pas de gains.

Interface React + TypeScript, API FastAPI et moteur quantitatif Python (source de vérité de tous les calculs).
**Simulation uniquement** : aucune route d'ordre, aucune connexion à un courtier, aucun identifiant stocké.

## Ce que fait la plateforme

| Page | Rôle |
|---|---|
| **Backtests** | Simule une stratégie sur des bougies M1 importées (exports MT5 ou CSV) avec spread, glissement, commissions et un Risk Guardian qui refuse les trades hors limites. Chaque run est **scellé** : empreinte SHA-256, vérification à la lecture, bouton « Reproduire ». |
| **Validation** | Mesure si les signaux d'une stratégie ont une espérance positive **hors échantillon** (walk-forward purgé, filtre logistique, bootstrap par grappes, registre infalsifiable des essais multiples). Méthode **expérimentale**, évaluée par une campagne statistique pré-enregistrée avant/après (`quant/research_campaign/`). |
| **Bot Analysis** | Analyse des robots MT5 externes dont on n'a que le `.ex5`, à partir de leurs **rapports du Strategy Tester** (HTML, Excel, CSV, ZIP) :<br>• chaque chiffre est rapproché du résumé MT5 ;<br>• ordres, deals, positions et trades sont reconstruits ;<br>• l'import est conservé comme référence immuable ;<br>• la section **Risk Collapse Analysis** sépare les constats des hypothèses ;<br>• les règles alternatives de gestion du risque sont qualifiées (exact, approximation, non simulable). |
| **Audit d'EA** | Détecte, dans un rapport MT5, grille, martingale, positions empilées et stop-out, puis chiffre le mouvement de l'or qui viderait le compte au pire moment. |
| **Stratégies, Instruments, Paramètres** | Règles versionnées, contrat XAUUSD (hypothèse déclarée), profil de risque. |
| **Exécution** | Volontairement **verrouillée**. |

### Cas réel analysé : « Gold Grid Strategy V3.70 EA »

Rapport du Strategy Tester MT5, XAUUSD M15, 10 000 USD. Les **23 indicateurs MT5** sont recalculés à l'identique à
partir des transactions, et les **314 clôtures** sont rattachées à leur ouverture au centime près.

- **Taux de réussite** : 82,8 % de trades gagnants, mais une perte moyenne 5,2 fois plus grande que le gain moyen.
- **Effondrement** : le 30/07/2026, dix positions empilées (9,38 lots) ont perdu **−51 990 USD** et le courtier a
  liquidé le compte (stop-out).
- **Période** : le test s'est arrêté trois mois avant la date demandée.

Rapport complet : [`quant/docs/REFERENCE_V370.md`](quant/docs/REFERENCE_V370.md).

## Vitrine en ligne

Une **vitrine en lecture seule** montre les vraies pages avec des résultats déjà calculés par le moteur : une démo
synthétique et l'analyse complète du rapport V3.70. Rien n'y est calculé et aucun ordre n'est possible. Pour la
mettre à jour ou la mettre en ligne : [`docs/project/DEPLOYMENT.md`](docs/project/DEPLOYMENT.md).

## Démarrer (macOS / Linux)

Prérequis : Node.js ≥ 18, pnpm, Python 3.12.

```bash
git clone https://github.com/eulogep/Traider-pro && cd Traider-pro
pnpm install
cd quant && python3.12 -m venv .venv && .venv/bin/pip install -r requirements.lock && .venv/bin/pip install --no-deps -e . && cd ..

pnpm quant:api   # API Python sur 127.0.0.1:8765
pnpm dev         # interface sur http://localhost:8080
```

## Vérifier

```bash
pnpm quant:test                  # tests Python (316)
pnpm test && pnpm typecheck      # tests TypeScript (48) + typage strict
node e2e/pages-tour.mjs          # parcours navigateur réel (52 vérifications)
```

## Par où commencer

| Fichier | Contenu |
|---|---|
| [`AGENTS.md`](AGENTS.md) | carte du dépôt, règles non négociables, commandes, comment ajouter une page ou une route |
| [`docs/README.md`](docs/README.md) | index de toute la documentation, selon votre rôle (trader, développeur, auditeur) |
| [`quant/README.md`](quant/README.md) | le moteur Python en détail |

## Architecture

```
client/   React (pages, composants) — affiche, ne calcule aucun montant
server/   Express (relais /api/v1 en production, garde des mutations locales)
shared/   types partagés de l'API
quant/    moteur Python : backtest, risque, recherche, ea_audit, external_lab, API FastAPI
docs/     audits indépendants (Codex), passations, base de connaissances, plan de projet
e2e/      parcours navigateur réels (Chrome headless + vraie API)
archive/  ancien code conservé pour mémoire, jamais importé
```

Documentation :
- [`quant/docs/ARCHITECTURE.md`](quant/docs/ARCHITECTURE.md)
- [`quant/docs/VALIDATION_V041.md`](quant/docs/VALIDATION_V041.md)
- [`quant/docs/EXTERNAL_LAB.md`](quant/docs/EXTERNAL_LAB.md)
- [`quant/docs/SECURITY_V05.md`](quant/docs/SECURITY_V05.md)
- [`quant/docs/KNOWN_LIMITATIONS.md`](quant/docs/KNOWN_LIMITATIONS.md)

## Fiabilité : ce qui est vérifié, et ce qui ne l'est pas

- **Audits indépendants** : chaque version a été auditée (rapports dans `docs/audits/`). Chaque défaut a été reproduit
  par un test avant d'être corrigé.
- **Statistiques** : la méthode de la page Validation est **expérimentale**. Dans la campagne, elle garde environ 5 % de
  faux « indices d'avantage » sur des données sans avantage, et jusqu'à 8 % quand le marché suit des tendances d'une
  journée. C'est documenté, pas caché.
- **Robots externes** : leur logique interne n'est jamais lue. Tout ce qui la concerne est présenté comme hypothèse.
- **Conditions non modélisées** : bougies OHLC (pas de ticks), coûts constants, pas de marge ni de swap dans le moteur.

## Licence

**Tous droits réservés**, voir [`LICENSE`](LICENSE). Le dépôt est public pour être consulté ; toute copie, modification,
redistribution ou utilisation commerciale demande un accord écrit. Les composants de tiers gardent leur propre licence
(ex. shadcn/ui, MIT).

## Avertissement de risque

Logiciel de recherche et d'éducation. Aucun résultat simulé n'est une performance réalisable ni une preuve de
rentabilité. Le trading sur l'or, le Forex et les CFD comporte un risque élevé de perte. Ne tradez qu'avec de l'argent
que vous pouvez vous permettre de perdre.
