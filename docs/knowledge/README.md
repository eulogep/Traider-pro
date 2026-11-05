# Base de connaissances — AI Trader Optimizer

Les sources externes y sont **vérifiées contre le code avant d'être utilisées**. Chaque fiche dit :
- ce que la source affirme ;
- ce qui est exact et ce qui est faux pour CE projet ;
- ce qui a été retenu, et ce qui a été écarté, avec la raison.

Une affirmation n'entre dans le logiciel qu'après vérification (test, mesure ou code lu).

| Fiche | Source | Date | Ce qu'elle a produit |
|---|---|---|---|
| [KB-001](KB-001_recherche_backtest_fragile.md) | « Du Backtest Fragile à la Plateforme de Recherche Financière », synthèse de recherche du propriétaire | 2026-11-05 | Page **Audit d'EA** (`/ea-audit`) : détection grille/martingale et test de résistance à partir d'un rapport MT5 ; backlog priorisé (DSR, limite hebdomadaire, spread variable, stress sur l'historique réel) |

## Règles d'usage
1. **Une source n'est pas une preuve.** Une citation n'est retenue que si elle soutient réellement l'affirmation à
   laquelle elle est attachée. Les articles de recherche (White 2000, Bailey & López de Prado 2014, Politis & White
   2004) priment sur les blogs et les pages commerciales.
2. **Les contraintes du projet priment sur les recommandations externes** :
   - aucune connexion à un courtier ;
   - aucun ordre ;
   - pas de réécriture du moteur sans défaut démontré ;
   - pas de calcul financier en TypeScript.
3. **Toute méthode statistique nouvelle** passe par un protocole pré-enregistré (`quant/research_campaign/`), jamais par
   un réglage sur les résultats.
4. **Ajouter une source** : créer `KB-NNN_<sujet>.md` sur le modèle de KB-001, avec :
   - le SHA-256 du fichier source ;
   - le tableau « affirmation → état du projet → exact ? → décision » ;
   - la liste de ce qui a été construit ou écarté.
