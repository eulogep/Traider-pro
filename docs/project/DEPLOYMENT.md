# Déploiement

La plateforme existe sous deux formes. **Seule la version locale calcule.** La vitrine en ligne montre des résultats
déjà calculés.

| | Plateforme locale | Vitrine en ligne (Netlify) |
|---|---|---|
| Rôle | travailler : importer, simuler, valider, analyser | montrer le projet, par exemple à un trader ou un associé |
| Moteur Python | oui (`pnpm quant:api`) | **non** : réponses pré-calculées, figées dans `showcase/data/` |
| Actions | toutes (import, backtest, étude, analyse d'EA…) | **lecture seule** : toute action affiche « Vitrine en lecture seule » |
| Ordres, courtier | jamais | jamais |
| Adresse | `http://localhost:8080` | site Netlify du dépôt (`tiny-quokka-08661a.netlify.app`) |

## 1. Plateforme locale
Voir `README.md` (« Démarrer ») et `AGENTS.md` §3. Pour une production locale : `pnpm build && pnpm quant:api && pnpm start`.

## 2. Vitrine statique
### Ce qu'elle contient
Le script `quant/scripts/export_showcase.py` lance la **vraie API** sur un catalogue temporaire. Il ne lit ni n'écrit
aucune de vos données, et ne lit pas votre dossier MT5. Il produit :
- une démo **synthétique** étiquetée (60 jours M1), un backtest de la stratégie illustrative et sa robustesse ;
- une étude de validation hors échantillon (méthode expérimentale) ;
- l'import du **vrai rapport MT5** « Gold Grid Strategy V3.70 » (HTML et XLSX des fixtures), avec ses hypothèses de
  réduction du risque aux valeurs par défaut.

Chaque réponse est écrite dans `showcase/data/` sous le nom donné par `showcaseFile()` (`client/lib/quantApi.ts`).
Les deux implémentations sont testées ensemble : `client/lib/showcase.spec.ts` et `quant/tests/test_showcase.py`.
Le fichier `manifest.json` date la génération et contient l'empreinte de chaque fichier.

### Le mettre à jour
```bash
pnpm showcase:data          # recalcule showcase/data/ avec le moteur actuel
pnpm build:showcase         # build VITE_SHOWCASE=1 + copie des données dans dist/spa/showcase/
node e2e/showcase-smoke.mjs # sert dist/spa comme Netlify (fichiers statiques, AUCUNE API) et vérifie chaque page
node e2e/readme-screenshots.mjs  # refait les captures du README (docs/images/) depuis la vitrine
```
Ensuite :
1. commitez `showcase/data/` ;
2. fusionnez sur `main`.

Netlify ne peut pas exécuter Python. Il reconstruit donc l'interface (`pnpm run build:showcase`, voir `netlify.toml`)
à partir des données **commitées**.

### Option recommandée : GitHub Pages (aucun compte tiers)
Adresse : **https://eulogep.github.io/Traider-pro/**.
```bash
pnpm showcase:data   # si le moteur a changé
pnpm deploy:pages    # build sous /Traider-pro/, contrôle 19 points sans API, puis publication de dist/spa sur la branche gh-pages
```
`scripts/deploy-pages.sh` publie seulement `dist/spa`, via un dossier de travail temporaire : votre copie de travail
et vos autres branches ne sont jamais modifiées. La première fois :
1. GitHub → *Settings* → *Pages* → *Source : Deploy from a branch* ;
2. choisir la branche `gh-pages`, dossier `/ (root)`.

### Option Netlify
#### Mettre le site en ligne (une seule fois)
Le site Netlify existant (`tiny-quokka-08661a`) servait une version d'août 2025 : il ne se reconstruisait plus
depuis le dépôt. Deux façons de le rebrancher :
- **Relier le dépôt** (recommandé, ensuite c'est automatique) :
  1. app.netlify.com → le site → *Site configuration* → *Build & deploy* → *Link repository* ;
  2. choisir `eulogep/Traider-pro`, branche `main`. La commande et le dossier sont lus dans `netlify.toml`.

  Chaque fusion sur `main` redéploie alors la vitrine.
- **Envoyer depuis votre Mac** :
  ```bash
  npx netlify-cli login        # ouvre le navigateur une fois
  pnpm build:showcase
  npx netlify-cli deploy --prod --dir dist/spa --site tiny-quokka-08661a
  ```

### Sécurité de la vitrine
- Aucun serveur : l'ancienne fonction Express de Netlify (en panne, « Cannot find module 'express' ») est rangée dans
  `archive/legacy-netlify-functions/`.
- `netlify.toml` ne déclare aucune fonction et pose des en-têtes défensifs : `nosniff`, `DENY` pour l'intégration dans
  un cadre, `Referrer-Policy`.
- Aucune requête `/api/` n'est émise ; `e2e/showcase-smoke.mjs` le vérifie.
- **Tout est public.** Les données publiées sont la démo synthétique et le rapport MT5 V3.70, déjà présents dans le
  dépôt. Ne mettez jamais vos propres historiques ou rapports privés dans `showcase/data/` sans le vouloir.
