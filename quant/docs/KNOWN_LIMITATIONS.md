# Limites connues — v0.5.0

## Laboratoire de robots externes (v0.5)
- **Pas d'identifiant de position** dans les rapports du testeur. L'appariement ouverture ↔ clôture est reconstruit et
  vérifié par le profit MT5. Deux positions de même volume et même prix restent indiscernables (sans effet sur le
  P&L).
- **Équité estimée aux seuls instants d'opération** : le drawdown d'équité réel, celui imprimé par MT5, peut être plus
  profond.
- **Hypothèses de réduction du risque** : seul l'arrêt définitif à plat est exact. Les autres sont des approximations
  conditionnelles, jamais un backtest du robot modifié.
- **Fonctionnement interne du robot** : tout ce qui le concerne est hypothèse, y compris l'interprétation des noms de
  paramètres.
- **Formats lus** : seulement tels qu'observés (build 6275, en-têtes anglais). Rapports d'optimisation, `.set` et XML
  2003 ne sont pas lus.
- **Modélisation** : mode, latence et niveau de risque déclaré sont absents du rapport, donc marqués « indisponibles ».
- **Pas d'IA** : une seule simulation de référence, dont les trades ne sont pas des observations indépendantes.

## Recherche et statistiques (v0.4.1)
- **Tout résultat de la page Validation est expérimental.** La méthode d'inférence (grappes de chevauchement + blocs
  Politis–White) n'a été évaluée que sur les scénarios synthétiques de `research_campaign/` ; elle n'a pas encore été
  contre-validée indépendamment. `EDGE` s'affiche « indice d'avantage (expérimental) », jamais « démontré ».
- **Le contrôle du taux de faux positifs n'est établi que sur les scénarios testés** (voir `VALIDATION_V041.md` §5).
  Des dépendances plus longues que l'historique (régimes de plusieurs mois) ne sont pas identifiables par
  rééchantillonnage : aucune méthode ne les corrige.
- **Échec mesuré sous des régimes d'un jour** : quand les résultats sont corrélés par des tendances d'environ une
  journée, sans que les variables le révèlent (nul N11b), le taux d'« indice d'avantage » atteint 8 % au lieu de
  ≤ 5 %. Les blocs Politis–White (≈ 2 unités) sont trop courts pour cette dépendance faible mais persistante.
- **Taux observé ≈ 5 % pour un niveau nominal de 3 %** sur les nuls indépendants : l'intervalle est trop étroit
  d'environ 10 à 20 % dans le pipeline.
- **Signaux en rafales** : sur 120 jours, une stratégie qui tire des dizaines de signaux à la suite n'a que quelques
  dizaines d'unités indépendantes. Le verdict est alors « échantillon insuffisant », et un avantage réel de +0,10 R
  n'est jamais détecté.
- **Le bootstrap est conditionnel** : il rééchantillonne les prédictions hors échantillon déjà calculées, sans
  ré-entraîner le modèle ni rejouer le choix du seuil dans chaque tirage.
- **Effet filtré légèrement positif sous le nul exact** (+0,003 R en moyenne, z combiné ≈ 3,9 sur 10 scénarios) et
  **AUC regroupée légèrement < 0,5** : causes non identifiées avec certitude (estimateur de ratio et pondération entre
  fenêtres du walk-forward ancré sont les candidats). Ordre de grandeur sans effet mesurable sur les taux d'erreur,
  mais non expliqué.
- **Avantage de signaux candidats ≠ performance d'un portefeuille exécutable** (audit I04-2) : chaque signal est
  simulé seul, sans contrainte « une position à la fois », sans limites journalières ni dimensionnement. Le rejeu
  portefeuille n'est **pas** implémenté.
- **Scores du modèle non calibrés** (I04-5) : ils classent les signaux, ce ne sont pas des probabilités de gain. Aucun
  calibrateur n'est appris ; l'avis sur un signal est refusé hors du domaine des variables d'entraînement.
- **Règle des essais multiples** : dépense sommable α_m = 0,05·6/(π²m²) par famille « type de données + instrument +
  unité de temps ». Elle protège la famille enregistrée, pas des essais faits ailleurs (autre logiciel, autre copie du
  catalogue, autre symbole déclaré). La seule vraie protection reste une période future jamais utilisée.
- **Monte Carlo d'un run** (I04-6) : réordonnancement échangeable des trades. Il détruit la persistance des pertes et
  ne rejoue ni le dimensionnement ni l'arrêt du Risk Guardian : mesure conditionnelle, pas une probabilité de drawdown.
- **Données de démonstration** (I04-9) : `data/synthetic.py` contient une composante sinusoïdale prédictible ; ce
  n'est pas un nul. Les nuls exacts de la campagne utilisent un autre générateur (`research_campaign/scenarios.py`).
- **Journal du moteur** (contre-audit N9) : `exit_time` reste l'ouverture de la bougie de sortie (moteur inchangé,
  `ENGINE_VERSION` 0.3.1). La couche recherche utilise sa propre colonne `available_time` (clôture de la bougie de
  sortie) ; tout autre consommateur doit faire de même.
- Les hooks React historiques `client/hooks/trading/*` (non utilisés) n'envoient pas l'en-tête `X-ATO-Request` :
  ils seraient refusés par la garde Express s'ils étaient réactivés.

## Audit d'EA
- **Lecteur de rapport non éprouvé** : construit d'après la mise en page MT5 documentée et testé sur des listes
  d'opérations construites. Il n'a pas encore été confronté à un vrai rapport du terminal du trader. Les formats
  inconnus sont refusés, jamais devinés.
- **Drawdown latent invisible** : la liste des opérations ne montre pas les pertes latentes entre deux opérations. Le
  test de résistance part du prix de la dernière opération et ignore le spread, le swap et le stop-out du courtier
  (le compte serait liquidé avant).
- **Seuils de détection** : heuristiques fixes et déclarées (`ea_audit.THRESHOLDS`), non calibrées sur des EAs réels.
  « Aucune signature » n'est pas une preuve de sécurité.
- **Formats non lus** : XLSX et `.set` (paramètres de l'EA) ; le `.ex5` lui-même n'est jamais exécuté ni lu.

## Intégrité et sécurité (v0.3.1)

## Intégrité et sécurité (v0.3.1)
- Les empreintes **détectent** une corruption ; elles ne **prouvent** pas l'authenticité (pas de signature).
- Le verrou de publication utilise `fcntl.flock` : POSIX uniquement (macOS/Linux) ; Windows non supporté.
- L'API n'a pas d'authentification : tout processus local peut l'appeler ; la garde protège surtout contre les pages web.
- Le mode `supervised` impose le profil enregistré, mais ce profil se modifie dans la console Streamlit sans contrôle
  d'accès (outil mono-utilisateur).
- Les runs au format 0.3.0 (sans `integrity.json`) sont refusés comme non vérifiables (aucun n'existait ici).
- Le quota disque est vérifié avant chaque traitement lourd (somme des tailles), pas pendant l'écriture.

## Intégration (v0.3)
- **Seule la page « Backtests » est alimentée par le moteur.** Aperçu, Tableau de bord, Trading MT5, Optimiseur IA,
  Automatisation et Paramètres affichent encore des chiffres de démonstration (bannière sur chacune).
- Profil de risque et contrat **lisibles** depuis React mais **modifiables seulement** dans la console Streamlit.
- Production locale supportée : `pnpm build && pnpm quant:api && pnpm start` (relais `/api/v1`). Netlify non supporté.
- Backtest **synchrone** (~4 s pour un an de M1) ; pas de file d'attente ni d'annulation ; au-delà de
  `ATO_MAX_CONCURRENT_JOBS` traitements simultanés, réponse 429.
- API sans authentification : outil local mono-utilisateur, écoute 127.0.0.1 uniquement.
- Les types TypeScript (`shared/quant-api.ts`) sont écrits à la main ; leur conformité est vérifiée par le test
  d'intégration, pas générés depuis l'OpenAPI.
- Pas de rejeu graphique d'un trade dans React (disponible dans Streamlit → Trade Journal).

## Simulation
1. **Bougies OHLC, pas de ticks** : l'ordre des prix dans une bougie est inconnu. SL prioritaire si SL et TP sont
   touchés dans la même bougie (conservateur, mais peut aussi biaiser dans l'autre sens sur certains motifs).
2. **Spread, glissement et commission constants.** En réalité ils varient (sessions, annonces, volatilité). Le
   spread historique (`<SPREAD>` des exports MT5) est affiché dans le rapport de qualité mais **pas utilisé** par le moteur.
3. TP exécuté au niveau du TP moins le glissement, même en cas de gap favorable (conservateur).
4. Une seule position à la fois. Pas de pyramide, pas de couverture.
5. Pas de marge, effet de levier, stop-out, swap/financement, conversion de devises, rejet ou requote d'ordre,
   liquidité, calendrier économique.
6. Drawdown calculé sur equity clôturée et mark-to-market **aux clôtures** : le drawdown intrabougie réel peut
   être plus profond. MAE/MFE sont des **bornes inférieures** prouvées (la trajectoire intrabougie est inconnue).
7. **Un stop-loss et une limite journalière ne garantissent pas une perte maximale** : les gaps sont exécutés à
   l'ouverture (`SL_GAP`), la perte peut dépasser le risque prévu (compteur « Pertes > risque prévu »).
8. Ce n'est **pas** une simulation d'exécution réaliste ; la V0.3 prévoit une comparaison avec le Strategy Tester MT5
   sur ticks réels.

## Données
9. Le contrat XAUUSD par défaut (100 oz/lot, lot min 0,01) est une **hypothèse** à vérifier chez le courtier.
10. Aucune détection automatique du fuseau d'un export MT5 : l'utilisateur doit le déclarer (souvent Europe/Athens,
    mais pas toujours).
11. La classification des trous (week-end, pause quotidienne, intrajournalier) est heuristique, en UTC.
12. Les jeux de données sont « retirés de l'index » mais leurs fichiers restent sur disque (pas de suppression destructive).

## Statistiques
13. Sharpe/Sortino non calculés. Les intervalles et tests de la page Validation sont expérimentaux (voir plus haut).
14. Moins de 30 trades ⇒ « échantillon insuffisant ». Même au-delà, un backtest ne démontre pas un avantage futur.
15. La comparaison de variantes (Strategy Lab) affiche l'in-sample et l'hors-échantillon : choisir d'après la
    colonne hors échantillon la contamine.

## Logiciel
- La correspondance contrat ↔ symbole se fait par préfixe : un contrat `XAUUSD` accepterait un symbole `XAUUSDT`.
- L'empreinte de code ne couvre pas les versions de pandas/numpy : un changement de bibliothèque peut modifier un
  résultat sans changer le `run_id` (le catalogue refuse alors d'écraser et « Reproduire » signale la différence).
16. Le moteur v0.2 gère des sessions et jours dans le fuseau de la stratégie, mais une seule plage d'horaires par run.
17. Enregistrement d'un run d'un an de M1 : ~9 s (equity complète en CSV.gz) ; chargement ~4 s.
18. L'import via le formulaire Streamlit n'est pas couvert par AppTest ; l'import via l'API (multipart) est testé
    (pytest et vitest), mais pas le clic sur « Importer un CSV » dans le navigateur.
19. Avertissement de dépréciation interne pandas 2.3 × numpy 2.5 (`'generic' unit for NumPy timedelta`) filtré dans
    la configuration pytest ; à revoir lors d'une mise à jour de pandas.
20. Le dossier du prototype n'est **pas suivi par Git** (dépôt racine = app React). Aucun commit n'a été fait ;
    plan proposé dans `../../docs/CONSOLIDATION_AUDIT.md`.
21. L'application React : seule la page « Backtests » est reliée au moteur (v0.3) ; les autres affichent des données
    de démonstration signalées. Secrets non persistés, ordres simulés désactivés.
