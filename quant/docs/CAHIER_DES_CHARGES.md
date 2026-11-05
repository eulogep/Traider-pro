# Cahier des charges — AI Trader Optimizer 2.0

Date : 2026-11-03 | Statut : proposition v0.1 à discuter avec le premier utilisateur

## 1. Objectif

Créer un laboratoire d'analyse et d'expérimentation des stratégies de trading, puis un assistant IA qui **classe** les opportunités, et enfin une exécution contrôlée sur compte de démonstration MT5. Mesure du succès : fiabilité de simulation, traçabilité, sécurité et **amélioration hors échantillon** par rapport au scénario sans IA. Pas de promesse de profit.

## 2. Périmètre

- Premier marché : XAUUSD ; Forex/XAGUSD plus tard. Première interface française.
- Première plateforme de trading cible : MetaTrader 5 (à confirmer avec le trader).
- V0.1 : import M1 CSV, analyse EMA/ATR, stratégie exemple, simulation avec coûts hypothétiques, métriques, export CSV/JSON.
- Hors périmètre V0.1 : connexion broker, recommandations financières personnalisées, exécution réelle, multi-comptes, marketplace, IA décisionnelle en production.

## 3. Rôles

- Développeur : architecture, qualité des données, simulation, sécurité, déploiement, documentation.
- Trader pilote : explique précisément les configurations, fournit sources de données et journal, valide le replay des décisions.
- Audit humain : contrôle de toute nouvelle stratégie, tout changement de risque et toute éventuelle activation de la démo.

## 4. Architecture cible

    Source de prix (CSV / MT5) -> Raw immuable -> Clean validé -> Features/Stratégies
      -> Backtest (traçable, versionné) -> Evaluation hors échantillon -> Modèle IA optionnel
      -> Risk Guardian -> Approbation humaine -> Adapter MT5 DEMO -> Journal d'audit

Une source de vérité pour chaque version de données, de stratégie et de configuration. Les métadonnées stockent version, plage temporelle, broker/symbole, méthode de simulation et hypothèses de coûts.

### Machines / déploiement

- Local sur Mac : interface, collecte de CSV, recherche Python.
- Conteneurs Linux éventuels : dashboard et stockages, mais **pas d'accès direct à l'argent**.
- MT5 : machine Windows dédiée pour l'intégration native Python ou un EA MQL5 dans un terminal MT5. L'hébergement virtuel MQL5 interdit les DLL.
- Ne jamais partager les identifiants du broker par Discord, commit Git ou configuration front-end.

## 5. Données

- Format initial : `timestamp,open,high,low,close` en M1 BID, UTC avec offset explicite.
- Future version : données tick bid/ask, métadonnées de trading/sessions, spread historique, commission, slippage, calendriers d'événements, journaux d'ordres.
- Validation : fuseaux, doublons, trous, OHLC incohérent, split temporel, disponibilité causale des indicateurs.
- **Pas de backfill inventé** : si les données manquent, marquer le trou et ne pas estimer de performance à cet instant.

## 6. Métamodèle d'une stratégie

Stratégie identifiée et versionnée : `id`, `markets`, `timeframes`, `session_timezone`, `signal_conditions`, `exclusions`, `entry_rule`, `exit_rule`, `risk_policy`, `params`, `owner`, `consent_to_share`.

Chaque trade/signal journalisé : `data_version`, `strategy_version`, `decision_time`, `known_features`, `decision`, `risk_rejection_reason`, `fill_assumption`, `exit_reason`, `pnl_after_costs`.

## 7. Sûreté

- Un seul compte démo autorisé pour les premiers tests d'exécution.
- Par défaut aucune transaction ; activation humaine explicite pour toute phase ultérieure.
- Aucune augmentation d'exposition après perte, aucun martingale, maximum de positions et pertes journalières configurés et testés.
- Arrêt d'urgence ; pas de nouvel ordre en cas de pertes, latence, rupture de données ou divergence positions.
- Limiter les accès (lecture seule pour dashboard, secret séparé pour l'EA) ; sauvegardes, logs d'audit, restauration et rollback des versions.
- **Un SL n'assure pas un prix garanti ; limites de pertes peuvent être franchies en cas de gap ou slippage.**

## 8. Protocole d'évaluation

- Baseline déterministe avant IA.
- Split chronologique et hors échantillon conservé intact ; optimisation uniquement sur entraînement/validation.
- Comparaison avec/sans IA sur les mêmes données, mêmes coûts et mêmes conditions.
- Tester hors échantillon, par régimes, spreads dégradés, données manquantes, erreurs réseau, notifications perdues.
- Mesures : nombre de trades, expectancy nette, profit factor, drawdown sur equity **mark-to-market**, Sharpe/Sortino si applicable, coût moyen, dérive live/backtest, incidents d'exécution.
- Échantillon insuffisant = conclusion « non démontré », et non performance annoncée.

## 9. Critères de succès par version

**V0.1** : lancement local, validation des fichiers, stratégie exemple non anticipatrice, export, tests automatisés, mention claire des hypothèses.

**V0.3** : scénario rejoué identiquement entre moteur Python et Strategy Tester MT5 dans des tolérances documentées ; véritables ticks bid/ask, spreads/commissions réalistes.

**V0.4** : IA améliore une métrique définie **avant** l'évaluation, sur le jeu hors échantillon non touché, sans détériorer le risque au-delà des limites acceptées.

**V0.5** : pas de transaction démo involontaire, journaux des refus, reconnexion et comportement fail-safe vérifiés.

**V1.0** : uniquement si résultats démo reproductibles et revue du risque/du cadre juridique ; pas de date garantie.

## 10. Décision de produit / principale tension

Un logiciel d'apprentissage et d'amélioration pour un trader novice a de la valeur même si la stratégie n'a pas encore d'avantage. Un **robot pour gagner automatiquement** n'en a pas tant qu'un avantage net n'est pas démontré. Construire le premier, et ne débloquer le second qu'après preuve.

## 11. Questions de l'entretien avec le trader pilote

1. Quel broker / terminal / fuseau et quelle devise de compte ?
2. Sur quels marchés, unités de temps et heures trade-t-il ?
3. Règles exactes pour acheter, vendre, attendre ? Exemples annotés valides et invalides ?
4. Comment place-t-il SL/TP, dimensionne-t-il les lots et traite-t-il les news ?
5. Dispose-t-il de données broker, journal, historique et autorisation de partager sa stratégie ?
6. Quels résultats vise-t-il vraiment : aide pédagogique, signaux, validation ou automates en démo ?

## 12. Principaux risques et retour arrière

- Overfitting : maintenir une baseline et un jeu test non consulté pendant l'optimisation.
- M1 sans ticks : interdiction de présenter la simulation comme une performance broker.
- Bug broker : désactivation d'exécution par défaut, journal, réconciliation et mode sans ordre.
- Mauvaise version de données : versionner les imports et permettre un rollback.
- Fuite des secrets : aucun mot de passe dans dépôt, rotation des credentials, accès minimum.
- Propriété intellectuelle : toute stratégie antérieure d'un tiers reste séparée et non commercialisable sans accord.
- Droit applicable : revue juridique avant mise à disposition à des tiers, notamment recommandations/exécutions personnalisées.
