# Audit initial — AI Trader Optimizer (état au 2026-11-03, avant v0.2)

Auteur : agent de développement (Claude Code). Périmètre : dossier `traider pro/` ouvert dans l'éditeur.

> Document historique : noms de dossiers à la date de l'audit. Depuis le 2026-11-03, `ai-trader-optimizer-v0.1/` → `quant/`
> et `ai-trader-optimizer/` → `archive/legacy-student-ai-trader-optimizer/` (voir `DECISIONS.md`, D-20).

## 1. Ce que contient réellement le workspace

| Dossier | Nature | Suivi Git | Verdict |
|---|---|---|---|
| `./` (racine) | Application **React/Express « Traider Pro »** (template Fusion Starter, Vite, shadcn/ui) | Oui (branche `main`, 99 fichiers modifiés non commités, surtout fins de ligne ; 13 fichiers avec de vraies modifications) | Maquette. Données générées par `Math.random` (35 occurrences), connexion MT5 **simulée** (`client/lib/mt5Service.ts`). Non modifiée dans cette session. |
| `ai-trader-optimizer/` | Ancien script étudiant (yfinance, actions/crypto, RandomForest) | Non suivi | Hors cible (pas de XAUUSD, pas de coûts, ML entraîné sans protocole). Conservé tel quel, non réutilisé. |
| `ai-trader-optimizer-v0.1/` | **Prototype Python v0.1** (Streamlit + moteur `core.py` + 7 tests) | **Non suivi par Git** | Base de travail retenue. |

Points de sécurité relevés sur l'app React (non corrigés, hors périmètre de cette livraison) :
- Le formulaire MT5 demande **login + mot de passe dans le navigateur** (`MT5ConnectionConfig.password`). Contraire à l'exigence « aucun identifiant broker côté front ». À ne jamais relier à un vrai compte.
- Les chiffres affichés (equity 52 340,50 USD, « John Trader »…) sont fictifs et non étiquetés comme tels.
- `.env` est suivi par Git (contient une clé publique Builder.io `VITE_PUBLIC_*` — non secrète par nature, mais le fichier ne doit jamais recevoir de secret).

## 2. Environnement et tests initiaux

- Python par défaut : 3.15.2 (trop récent pour les roues pandas). Environnement créé avec **Python 3.12** : `.venv/` dans le prototype.
- Dépendances installées : pandas 2.3.3, numpy 2.5.4, streamlit 1.66.1, pytest 9.2.0.
- `python -m pytest -q` → **7 passed** (2,0 s).
- `python scripts/demo_cli.py` → 12 trades, P&L −7,00 USD sur données synthétiques.

Sauvegarde intégrale de l'état initial (hors `.venv`) : archive `ai-trader-optimizer-v0.1_original.tgz` dans le scratchpad de session ; le fichier `src/ai_trader_optimizer/core.py` est en outre conservé **inchangé** comme référence figée.

## 3. Analyse du moteur `core.py` (v0.1)

### Ce qui est correct (vérifié)
- Décision sur la **dernière bougie clôturée** (`prior = f.iloc[i-1]`), entrée à l'ouverture suivante : pas de look-ahead dans la boucle.
- EMA (`ewm(adjust=False)`) et ATR (`rolling`) sont causaux.
- Modèle BID cohérent : achat à l'ASK (`open + spread`), sortie long au BID, sortie short à l'ASK ; SL prioritaire si SL et TP dans la même bougie ; gap au-delà du SL → sortie au pire de (SL, open).
- Sizing : lots arrondis **vers le bas**, risque par lot incluant slippage de sortie et commission aller-retour.
- Validation CSV stricte (fuseau explicite, doublons, ordre, OHLC, prix > 0) en mode rejet global.
- Pas d'entrée à travers une minute manquante.

### Défauts constatés (mesurés par sonde, pas supposés)
| # | Gravité | Défaut | Preuve |
|---|---|---|---|
| D1 | **Critique (risque)** | La limite de perte journalière ne tient compte que du P&L réalisé : un trade peut être ouvert alors que son risque prévu dépasse le budget restant. | Limite 0,30 % → perte réelle du jour −0,49 % (−49,17 USD sur 10 000). |
| D2 | Élevée | **Règles cachées** codées en dur : arrêt de la journée après le **premier gain** (`not daily_win`) et après **2 pertes** (`daily_losses < 2`). Non documentées, non configurables. | 2026-09-08 : un seul trade gagnant puis plus rien. |
| D3 | Élevée (traçabilité) | Aucun journal des décisions : 1 290 signaux, 12 trades, aucune raison de refus enregistrée. Impossible de « rejouer » une décision. | Sonde : `signals: 1290 trades: 12`. |
| D4 | Moyenne | ATR = moyenne simple du True Range, pas l'ATR de Wilder (MT5/TradingView). Écart max 0,27 USD sur la démo. Nom « ATR14 » trompeur. | Sonde : `max abs diff 0.273`. |
| D5 | Moyenne | Drawdown calculé sur equity **clôturée** seulement (sous-estime le risque). Pas d'equity mark-to-market. | Code l. 247-252. |
| D6 | Moyenne | Aucun lien run ↔ version de données ↔ version de stratégie ↔ configuration. Résultats non persistés. | — |
| D7 | Moyenne | Métriques incomplètes : pas d'espérance, pas de coûts détaillés (spread/slippage), pas de résultats par période ; profit factor `None` sans explication. | — |
| D8 | Faible | `TestConfig` commence par « Test » : pytest tente de le collecter s'il est importé sous ce nom dans un module de test. | — |
| D9 | Faible | Contrat fixé par défaut à 100 oz sans marquage « hypothèse » ; aucune vérification de devise de cotation vs devise de compte. | — |
| D10 | Faible | Boucle `iloc` ligne par ligne : 63 360 barres en 2,3 s (≈ 14 s pour un an de M1). Acceptable mais améliorable. | Sonde. |
| D11 | Faible | Sessions et réinitialisation journalière forcément en UTC ; fermeture du week-end évaluée en UTC. | — |

### Qualité des tests existants
| Test | Vérifie réellement | Faiblesse |
|---|---|---|
| `test_demo_data_generates_and_runs` | exécution + cohérence nb trades | aucune vérification financière |
| `test_bad_data_requires_explicit_timezone` | rejet sans fuseau | correct |
| `test_duplicate_rejected` / `test_ohlc_invalid_rejected` | rejets | corrects |
| `test_no_trade_before_signal_closed` | signal présent sur la bougie précédente | ne prouve pas l'absence de look-ahead des indicateurs |
| `test_position_size_does_not_exceed_risk_budget_on_entry` | `lots > 0` | **ne teste pas le budget de risque malgré son nom** |
| `test_strict_trade_daily_limit` | ≤ 1 trade/jour | passe trivialement si aucun trade |

Aucun test ne vérifie un P&L calculé à la main, la règle SL/TP même bougie, un gap, la limite journalière, ni la reproductibilité.

## 4. Décision de travail

- Le prototype v0.1 est **réutilisable** : refactorisation progressive vers une architecture modulaire dans le même dossier (pas de renommage pour ne pas casser les chemins existants).
- `core.py` reste intact comme **référence de régression** : un test vérifie que le nouveau moteur, configuré avec les règles v0.1 explicites, reproduit exactement ses trades.
- Les défauts D1–D11 sont traités dans la v0.2 (voir `CHANGELOG.md`, `DECISIONS.md`).
- L'application React n'est pas modifiée ; elle n'est pas reliée aux moteurs Python.
