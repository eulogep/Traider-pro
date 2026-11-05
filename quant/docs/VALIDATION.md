# Validation hors échantillon — mode d'emploi (v0.4.1, méthode EXPÉRIMENTALE)

Objectif : savoir **avant d'y mettre de l'argent** si les signaux d'une stratégie ont une espérance positive hors
échantillon, et si un modèle sait classer les meilleurs. Aucun logiciel ne prédit le marché avec certitude. Celui-ci
mesure une espérance avec sa marge d'erreur et refuse de conclure quand les données ne le permettent pas.

**Statut : expérimental.** La méthode a été évaluée sur des scénarios synthétiques pré-enregistrés
(`../research_campaign/`, résultats dans `VALIDATION_V041.md`). Elle n'a pas encore été contre-validée de façon
indépendante, ni éprouvée sur des données de marché réelles. Aucun verdict de cette page n'est une preuve de rentabilité.

## Utilisation (page « Validation » de l'application)
1. Importer un historique **réel** : export MT5 « Exporter les barres », M1, plusieurs mois (voir page Instruments).
2. Choisir la stratégie, garder l'horizon (240 bougies) et 4 fenêtres, puis lancer l'étude.
3. Lire le verdict :
   - **Indice d'avantage (expérimental)** : la borne basse unilatérale de l'espérance des signaux retenus, coûts
     supposés inclus, est positive. Elle est calculée au niveau corrigé des essais multiples. Ce n'est **pas** une
     preuve. Étape suivante obligatoire : confirmer sur une période **future** jamais utilisée, puis en compte démo.
   - **Aucun avantage démontré** : résultat compatible avec le hasard. Ne pas trader sur cette base.
   - **Perte attendue mesurée** : avec ces coûts, les signaux perdent, filtrés ou non.
   - **Échantillon insuffisant** : moins de 100 signaux, ou moins de 100 **unités indépendantes** hors échantillon.
     Des signaux dont les résultats se chevauchent dans le temps ne comptent que pour une unité.
   - **Calcul invalide** : un calcul a échoué (valeur non finie, modèle non convergé). Aucune conclusion n'est tirée.
4. **Avis sur le dernier signal** : il n'est donné que pour un signal *nouveau*, dont le résultat n'est pas encore
   connu. Un signal qui a servi à l'apprentissage n'est jamais présenté comme une prévision. Le score affiché est un
   classement **non calibré**, pas une probabilité de gain. Sans indice d'avantage, l'avis est « NE PAS TRADER ».
5. L'onglet **Robustesse** d'un backtest donne des mesures **conditionnelles** : le réordonnancement des trades détruit
   la persistance des pertes et ne rejoue ni le dimensionnement ni le Risk Guardian.

## Règles à respecter (sinon le verdict ne vaut rien)
- Ne pas relancer des études en boucle sur le même historique jusqu'à obtenir un indice d'avantage.
  - Chaque étude est inscrite dans un registre infalsifiable, qui compte aussi les études supprimées.
  - Le niveau exigé se resserre à chaque essai de la même famille (même type de données, même instrument, même unité
    de temps) : α_m = 0,05 × 6 / (π² m²), soit 3,0 % pour la 1ʳᵉ étude, 0,76 % pour la 2ᵉ, 0,34 % pour la 3ᵉ.
  - La seule vraie protection reste une période future jamais vue.
- Utiliser les coûts **réels** du courtier : spread moyen aux heures tradées, commission.
- Données synthétiques : elles servent à tester la méthode uniquement.
- Un indice porte sur des **signaux candidats** pris un par un. Ce n'est pas la performance d'un portefeuille
  exécutable : une position à la fois, limites journalières et dimensionnement ne sont pas rejoués.

## Méthode (résumé)
- **Simulation des signaux** : chaque signal candidat est simulé seul (triple barrière : stop, objectif, horizon) avec
  les conventions du moteur. R est identique au `r_multiple` du moteur pour les trades réellement pris (testé).
- **Disponibilité** : un résultat est disponible à la **clôture** de sa bougie de sortie (`available_time`). Seuls les
  résultats disponibles avant une fenêtre de test servent à l'entraînement (purge).
- **Variables** : 12 variables causales (élan, tendance, volatilité, heure, coût en R…), calculées sur les bougies
  clôturées.
- **Walk-forward ancré** : le seuil du filtre est choisi sur une tranche de validation interne, jamais sur le test.
- **Inférence** (méthode `overlap-clusters-pw`) :
  - les signaux hors échantillon dont les résultats se chevauchent forment une **unité** ;
  - les unités sont rééchantillonnées par blocs circulaires ; la longueur des blocs est choisie automatiquement
    (Politis & White 2004, correction de 2009) ;
  - `EDGE` si le quantile α unilatéral de la moyenne filtrée est > 0.
- **Contrôles numériques** : toute valeur non finie, toute probabilité invalide et tout modèle non convergé mènent à
  un refus.
- **Contrôles mesurés** : taux de faux positifs et puissance sur 24 scénarios synthétiques (avant/après, mêmes
  graines), dans `VALIDATION_V041.md` §5. Les anciens chiffres « 1 sur 60, 19 sur 30, 30 sur 30 » de la v0.4.0
  reposaient sur trop peu d'essais et sur une méthode désormais remplacée ; ils sont retirés (voir
  `REPRODUCTION_V04.md`).

## Premier enseignement (mécanique, valable sur données réelles)
Le poids le plus fort du modèle est **le coût d'un aller-retour exprimé en R** : plus le stop est serré, plus le
spread et la commission mangent l'espérance. C'est le premier point à vérifier avec la stratégie du trader.

## Limites
- Bougies OHLC (pas de ticks), coûts fixes, un seul instrument par étude.
- Régression logistique simple, un choix volontaire : peu de paramètres, donc moins de sur-apprentissage.
- Un historique, même validé, ne garantit aucun résultat futur.
- Liste complète : `KNOWN_LIMITATIONS.md`.
