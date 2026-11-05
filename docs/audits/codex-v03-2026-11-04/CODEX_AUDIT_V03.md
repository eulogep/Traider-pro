# Audit indépendant — AI Trader Optimizer V0.3

Date : 4 novembre 2026 (Europe/Paris). Périmètre : état de travail local de `traider pro`, et non uniquement HEAD. HEAD observé : `2dedf6c758ec124098db5f6abd4076e1d8dd134b`.

**Verdict : NON en l’état pour un socle V0.4 déclaré fiable.** La structure React → FastAPI → Python mérite d’être conservée, mais l’intégrité des preuves persistées, la séparation temporelle IS/OOS et la sauvegarde Git doivent être corrigées avant de bâtir des conclusions financières dessus. Un développement V0.4 reste possible comme laboratoire local expérimental sous ces réserves, sans validation de performance ni exécution réelle.

Aucun fichier du dépôt, index Git, commit, serveur de production ou déploiement n’a été modifié par cet audit. Rapport et sondes créés dans `/private/tmp/codex-audit-v03-u1qibo2e/`. Les tests, builds et jeux de données ont utilisé une copie temporaire du projet. Les dépendances Python installées ont été réutilisées, avec les sources de la copie prioritaires et l’écriture de bytecode désactivée ; les dépendances JavaScript ont été copiées. Aucune installation ni connexion courtier.

## Résultats vérifiés

| Vérification | Statut | Résultat |
|---|---|---|
| Python `pytest -q -p no:cacheprovider` | PASS | 142 tests, 114,07 s |
| Ruff `check --no-cache src tests app.py scripts` | PASS | All checks passed |
| `pnpm test` | PASS | 25 tests, 6 fichiers |
| `pnpm typecheck` | PASS | Aucune erreur |
| `pnpm build` | PASS | SPA et serveur construits |
| Chrome `e2e/backtest-flow.mjs` | PASS | 16/16 |
| Chrome `e2e/backtest-flow.mjs --api-down` | PASS | 3/3 |
| Sonde financière indépendante | PASS | 12/12 cas BUY/SELL × bid/mid × 3 profils de coûts |
| Sondes de défauts | FAIL fonctionnel | Comportements décrits ci-dessous reproduits ; 21 enregistrements dans `evidence.json` |

La première tentative JavaScript dans le sandbox a rencontré `EPERM` à l’ouverture de ports locaux : 17 tests passaient et 8 étaient ignorés. La relance autorisée avec ports locaux a passé les 25 tests. Ce premier résultat n’est pas un défaut du produit. Une première copie de travail avait omis le package source `data` à cause d’une exclusion trop large de la copie ; elle a été corrigée avant les vérifications ci-dessus. Le problème indépendant de `.gitignore` décrit en B1 a ensuite été vérifié directement dans le dépôt original.

Les logs complets sont joints au rapport. Les PASS confirment les affirmations chiffrées du handoff, pas l’exhaustivité de ses garanties.

## Ce que l’audit confirme et ses limites

- Le P&L terminal applique correctement, sur les cas vérifiés, le signe BUY/SELL, la taille du contrat, le spread, deux commissions et deux glissements. Exemple plat avec spread 0,30, glissement 0,05 et commission 3/côté, 0,11 lot et contrat 100 : perte nette **5,06 USD** dans les deux directions. La sonde indépendante vérifie également les identités de capital.
- Le dimensionnement inclut la commission aller-retour et le glissement de sortie ; le spread est déjà incorporé au prix d’entrée. Aucun double prélèvement systématique de spread constaté dans le net.
- Une devise de cotation différente de celle du compte est refusée : **aucune conversion monétaire n’est implémentée**. Les résultats EURJPY/USD ne doivent donc pas être présentés comme pris en charge. Le contrat XAUUSD reste une hypothèse déclarée, pas une spécification vérifiée chez un courtier.
- EMA, ATR, motifs et alignement multi-timeframes examinés sont causaux pour les données valides et alignées. Les tests de préfixe et de perturbation du futur passent. L’entrée utilise le signal de la bougie précédente. Il reste un défaut de frontière temporelle dans la comparaison IS/OOS (B3).
- Stops gapés défavorablement et priorité SL/TP sont couverts ; le cas de gap favorable à l’ouverture révèle I8. L’ordre intrabougie reste inconnu.
- FastAPI expose les 16 routes autorisées, sans route d’ordre ni champ de connexion courtier. Les appels d’ordre du simulateur TS commencent par un garde désactivant l’exécution. Aucun chemin de trading réel identifié dans les modules actifs examinés. L’archive étudiante n’est pas un moteur validé.
- Les identifiants hexadécimaux, SQL paramétré et la liste blanche des exports empêchent les traversées de chemins ordinaires testées. Le nom du fichier uploadé ne devient pas un chemin d’écriture arbitraire.
- Sur le parcours navigateur de développement, les cinq KPI comparés correspondent à l’API et aux résultats persistés. Cette cohérence ne prouve pas que des fichiers modifiés après coup seront détectés (B2).
- Marge, levier, swaps, liquidité, ticks réels et rapprochement avec un courtier ne sont pas validés. Les gaps peuvent dépasser le risque prévu ; ce n’est pas en soi un contournement du Guardian. Le drawdown du Guardian dépend du capital réalisé, et le drawdown MTM présenté dépend des clôtures : ce ne sont pas des limites de perte intrabougie garanties.

## Bloquant

### B1 — Des sources Python indispensables sont ignorées par Git

**Fichiers :** `.gitignore:30` ; `quant/src/ai_trader_optimizer/data/` ; imports de `backtest/engine.py:25`. **Certitude : confirmée par Git.**

**Reproduction :** `git check-ignore -v quant/src/ai_trader_optimizer/data/__init__.py quant/src/ai_trader_optimizer/data/validation.py` renvoie `.gitignore:30:data/` pour les deux fichiers. Le motif non ancré ignore tous les répertoires nommés `data`, y compris le package source. Le moteur est non suivi ; un ajout ordinaire ne sauvegarderait pas ce package. Sans lui, l’import de l’API/du moteur échoue avec `ModuleNotFoundError`.

**Impact :** les tests passent sur une machine contenant des sources invisibles à la sauvegarde Git. L’affirmation « git add ne prend que les bons fichiers » est incomplète : il omet aussi du code nécessaire. Un clone ne pourrait pas reproduire la V0.3 après un ajout naïf.

**Correction proposée :** cibler les répertoires de données runtime par leurs chemins, préserver explicitement les sources, puis vérifier la liste de fichiers préparés et exécuter une installation/test depuis un export ou clone propre. À faire dans un incrément autorisé, sans normalisation massive du travail existant.

### B2 — « Reproduire : identique » ne vérifie pas les résultats effectivement stockés

**Fichiers :** `backtest/engine.py:293`, `backtest/models.py::frame_hash`, `storage/catalog.py:120,161`, `services.py:46-65` (chemins Python relatifs à `quant/src/ai_trader_optimizer/`). **Certitude : reproduite.**

**Reproduction :** créer un run ; modifier seulement `runs/<id>/metrics.json`, en remplaçant `net_pnl` par `987654321`. GET du run sert cette valeur. POST `/reproduce` répond **`identical: true`**, avec les empreintes égales `b4a4649e8bd29cc8`. Autre sonde : modifier en mémoire les métriques et la courbe d’un résultat existant, conserver son manifeste, appeler `save_run` : l’écrasement est accepté, et la nouvelle métrique `123456` est lue ensuite.

**Cause :** l’empreinte ne couvre que trades et décisions, arrondis à huit décimales ; elle n’inclut ni métriques ni equity. La lecture ne recalcule même pas l’empreinte des trades/décisions persistés. `reproduce` compare une nouvelle simulation à l’empreinte déclarée dans le manifeste. `save_run` fait confiance à cette même déclaration.

**Impact :** KPI et courbe peuvent être faux tout en conservant un voyant de reproduction positif. Même une altération des CSV de trades peut passer inaperçue à la lecture. Ce n’est pas une attaque distante démontrée : une corruption, une écriture partielle ou un appel de stockage fautif suffit à rompre la garantie.

**Correction proposée :** empreinte canonique complète des artefacts financiers et décisions ; validation effective à la lecture et avant réutilisation ; recalcul de cohérence trades ↔ métriques ↔ equity ; refus de remplacement d’un run immutable. Distinguer « moteur déterministe » et « artefacts stockés intacts » dans la réponse de reproduction. Un hash local détecte les corruptions, pas un adversaire capable de réécrire toutes les preuves.

### B3 — Chevauchement IS/OOS à la frontière du découpage chronologique

**Fichiers :** `ai/validation.py:15-24`, `services.py:81-86`, `backtest/engine.py:86-89`. **Certitude : reproduite par le même découpage et le moteur.**

**Reproduction :** onze bougies M1 de 12:00 à 12:10, fraction apprentissage 0,5. La coupure est 12:05. Émettre un signal à 12:04 et faire toucher le TP dans la bougie 12:05. Le run IS avec `trade_end=cut` et le run OOS avec `trade_start=cut` exécutent **tous deux** le trade de 12:05, chacun avec **+31,79 USD**. La sonde utilise une stratégie scriptée indépendante ; les bornes sont celles employées par `compare_variants`.

**Cause :** le contrat de `Split.train_end` est exclusif, mais le moteur conserve les bougies dont l’ouverture est `<= trade_end`, puis utilise l’intégralité de leur high/low/close. Une coupure entre deux ouvertures peut également laisser la fin d’une bougie IS déborder au-delà de l’instant de coupure.

**Impact :** les résultats de sélection peuvent exploiter une bougie appartenant à l’évaluation ; l’indépendance temporelle revendiquée n’est plus assurée. Ce défaut concerne la comparaison de variantes Python, pas une fuite détectée dans les EMA de la page React.

**Correction proposée :** définir des intervalles cohérents en temps de disponibilité des bougies, par exemple IS avec clôture `<= cut`, OOS avec entrées `>= cut`, sans réutilisation des résultats de la bougie de frontière. Aligner ou quantifier les coupures, documenter les signaux de warm-up et tester l’absence d’intersection des exécutions et des données évaluées.

## Important

### I1 — Des nombres non finis permettent un backtest financièrement invalide

**Fichiers :** `backtest/models.py::BacktestConfig,ExecutionCosts`, `risk/guardian.py::ContractSpec`, `api/schemas.py::to_jsonable`. **Certitude : reproduite via HTTP.**

**Reproduction :** POST backtest avec un corps JSON contenant `config.initial_equity: 1e309`. Le token JSON numérique déborde en infini après parsing. Réponse **201**, six trades exécutés ; capital initial/final et net P&L deviennent `null`, alors que d’autres métriques restent numériques. Les modèles acceptent aussi `spread=inf` en Python.

**Impact :** le fail-closed sur les paramètres financiers n’est pas effectif ; le formatage `null` masque une entrée invalide en métrique indisponible. Les identités financières et la rejouabilité du manifeste sont compromises.

**Correction proposée :** interdire NaN et infinis dans tous les modèles financiers et les paramètres numériques, poser des bornes opérationnelles, vérifier les intermédiaires et renvoyer 422 avant toute simulation/sauvegarde. Tester aussi les chaînes numériques et les exposants débordants.

### I2 — Le profil de risque enregistré est un défaut, pas une politique imposée

**Fichiers :** `api/app.py:206`, `api/schemas.py::BacktestRequest`, `services.py::default_config`, `client/components/backtest/ConfigPanel.tsx`. **Certitude : reproduite.**

**Reproduction :** enregistrer `max_trades_per_day=1`. Avec configuration omise : trois trades sur trois jours. Envoyer une configuration complète avec maximum 100, pertes/jour désactivées et limites journalière/drawdown à 100 % : **73 trades**, réponse 201. Le manifeste enregistre bien ces nouvelles règles.

**Impact :** une requête peut relâcher toutes les limites du profil affiché comme « enregistré », ainsi que modifier contrat et horaires. Le Guardian respecte la configuration reçue : ce n’est pas un dépassement de ses règles internes ni une possibilité d’ordre réel. En revanche, aucune politique serveur indépendante de l’appelant n’existe.

**Correction proposée :** séparer hypothèses de recherche et limites obligatoires ; résoudre et appliquer la politique côté serveur, refuser les dérogations ou les rendre explicites dans un mode de recherche identifié. Valider le contrat et le symbole côté serveur. Si tout doit rester éditable, présenter honnêtement le profil comme valeurs par défaut, sans prétendre qu’il est incontournable.

### I3 — La limite d’upload intervient après réception du multipart

**Fichiers :** `api/app.py:141-166` et traitement multipart Starlette. **Certitude : réception préalable reproduite ; saturation volontaire non exécutée.**

**Reproduction :** sonde ASGI instrumentant `receive`, limite applicative 1 024 octets, fichier 2 Mio. Au premier appel de `max_upload_bytes`, **2 097 687 octets** ont déjà été reçus. La route renvoie ensuite 413. `UploadFile` a donc déjà été construit ; les fichiers volumineux peuvent être spoolés sur disque avant le contrôle.

**Impact :** le 413 ne constitue pas une borne du coût de réception. À cela s’ajoutent les copies en mémoire et le parsing pandas synchrone dans une route async. Les créations de démos/backtests ne sont ni contingentées ni mises en file.

**Correction proposée :** limiter le corps au niveau ASGI/proxy avant le parseur, compter les octets réellement reçus même sans Content-Length, borner concurrence/stockage et lignes parsées, déplacer les calculs lourds hors de la boucle async. Garder la vérification de route comme seconde barrière.

### I4 — CORS ne bloque pas les écritures d’une origine étrangère

**Fichiers :** `api/app.py:76,141`, `tests/test_api.py::test_cors_only_for_listed_local_origins`. **Certitude : requête ASGI reproduite ; exploitation depuis navigateur tiers non exécutée.**

**Reproduction :** POST multipart `/datasets/import` avec `Origin: https://evil.example` et fichier valide : **201**, données enregistrées, sans `Access-Control-Allow-Origin`. Le test actuel vérifie seulement l’absence d’un en-tête de lecture sur GET. Les navigateurs peuvent émettre certains POST multipart sans préflight ; les protections d’accès réseau local varient et ne doivent pas remplacer une politique de l’application.

**Impact :** CORS protège la lecture JavaScript de la réponse, pas à lui seul la mutation du catalogue. L’écoute loopback limite l’exposition mais ne constitue pas une authentification de l’appelant.

**Correction proposée :** contrôle Origin/Host explicite sur les mutations, protection contre DNS rebinding, et si nécessaire jeton local transmis dans un en-tête obligatoire avec préflight. Tester que les origines interdites ne provoquent aucune écriture. Ne pas annoncer une compromission navigateur démontrée sur cette seule sonde.

### I5 — Import en minuscules accepté, puis dataset déclaré altéré

**Fichiers :** `data/validation.py:304-335`, `storage/catalog.py:104-112`, validation symboles de `api/app.py`. **Certitude : reproduite.**

**Reproduction :** importer le CSV valide avec `symbol=xauusd` : **201**. Le fingerprint a utilisé les minuscules, mais les métadonnées contiennent `XAUUSD`. `load_dataset` recalcule avec les majuscules et échoue : « altéré sur disque (empreinte différente) ».

**Impact :** un import conforme à l’API devient inutilisable pour backtester. Le message d’altération accuse le mauvais problème.

**Correction proposée :** normaliser le symbole une fois avant calcul d’identité, stockage et comparaison ; tester import → sauvegarde → relecture → backtest avec variantes de casse et suffixes autorisés.

### I6 — L’empreinte du dataset ne garantit pas l’identité exacte des entrées

**Fichiers :** `data/validation.py` contrôle `epoch_s`, `data/models.py:107-119`, `storage/catalog.py:85`. **Certitude : deux scénarios reproduits.**

**Reproduction A :** bougies M1 aux heures `12:00:00.500`, `12:01:00.500`, etc. acceptées. Après sauvegarde/relecture, `.500` a disparu sans alerte. **Reproduction B :** deux frames distinctes avec close `100` et `100.00000001` donnent le même ID `a9295dcc876b0456`, à cause de `%.10g`.

**Impact :** les données exécutées peuvent différer des entrées acceptées ; l’empreinte ne détecte pas certaines modifications. La troncature temporelle peut avancer artificiellement la disponibilité des bougies. La pertinence financière de l’écart de prix dépend du pas de cotation, absent ici.

**Correction proposée :** refuser les fractions de seconde pour ces timeframes ou préserver la précision complète ; contrôler l’alignement en nanosecondes ; sérialisation canonique round-trip ou quantification explicite au pas de cotation avant hash ET simulation. Vérifier des altérations fines et le round-trip complet.

### I7 — La provenance d’un dataset existant peut être remplacée sous le même ID

**Fichiers :** `data/models.py::fingerprint`, `storage/catalog.py:88`, `api/app.py::import_dataset`. **Certitude : reproduite.**

**Reproduction :** importer exactement les mêmes octets `neutral.csv` une fois en `synthetic`, puis en `historical`, avec une autre source déclarée. Les deux imports répondent 201 avec **le même ID `2253b32278baa4db`** ; les métadonnées sont remplacées par `INSERT OR REPLACE`. Le contrôle du mot « synth » dans le nom se contourne par un renommage, sans prouver une origine réelle.

**Impact :** une provenance présentée comme immutable devient mutable. Un ancien manifeste peut rester marqué synthétique alors que le catalogue courant et les prochains runs sont marqués historiques ; l’identité du run ne couvre pas cette version de provenance.

**Correction proposée :** séparer identité du contenu et version de provenance ; interdire les remplacements conflictuels, conserver les déclarations et leur historique, relier le manifeste à une provenance immutable. Afficher « historique déclaré par l’utilisateur » tant que la source n’a pas été vérifiée. La détection automatique fiable d’un CSV synthétique n’est pas promise comme solution.

### I8 — Un gap ayant déjà franchi le TP peut être transformé en SL

**Fichiers :** `backtest/engine.py:151-172`. **Certitude : reproduite.**

**Reproduction :** BUY à 100,35, SL 98,35, TP 103,35, position encore ouverte. Bougie suivante : O=105, H=106, L=97, C=99. Le moteur produit **SL à 98,30, −23,21 USD**. Pourtant l’ouverture était déjà au-delà du TP avant toute excursion vers le SL. Selon la convention TP conservatrice actuelle, la sortie aurait dû intervenir à 103,30, **+31,79 USD**.

**Impact :** la priorité stop-first est appliquée même lorsque la chronologie de l’ouverture est connue, inversant le résultat d’un trade. L’hypothèse conservatrice TP au niveau cible n’impose pas d’ignorer un TP déjà franchi à l’ouverture.

**Correction proposée :** traiter d’abord les franchissements à l’ouverture pour les positions existantes, puis les touches intrabougie encore ambiguës. Définir l’ordre avec les sorties horaires/session et tester BUY et SELL, gaps SL et TP, bougies touchant les deux seuils.

### I9 — Publication d’un run non atomique, risque de lecture partielle/concurrence

**Fichiers :** `storage/catalog.py:120-141,155-178`. **Certitude : défaut structurel constaté ; course simultanée et crash non injectés. Limite déjà documentée.**

**Reproduction proposée :** suspendre une sauvegarde après `manifest.json`, avant `trades.csv`, puis GET du run ; `run_dir` considère le manifeste suffisant et `load_run` tente des fichiers absents. Autre test : deux écrivains du même ID, ou arrêt entre fichiers et transaction SQLite.

**Impact :** réponses 500, divergence liste/détails/exports et éventuelle combinaison d’artefacts. La transaction SQLite ne couvre pas les fichiers ; la comparaison préalable d’empreinte n’est pas un verrou.

**Correction proposée :** écrire un répertoire temporaire complet, valider, publier atomiquement avec politique de verrouillage par ID et état de commit ; rendre une sauvegarde identique idempotente sans réécriture ; récupération des runs incomplets. Ajouter une injection déterministe d’interruptions et une lecture concurrente.

### I10 — L’intégration complète est limitée au serveur de développement

**Fichiers :** `vite.config.ts::server.proxy`, `server/node-build.ts:19-27`, `netlify.toml`. **Certitude : lecture du routage ; limite déjà reconnue ; requête au serveur de production non rejouée.**

**Reproduction proposée :** `pnpm build && pnpm start`, démarrer Python, consulter `/api/v1/health` via le port Express. Il n’existe pas de proxy `/api/v1` côté production ; le catch-all API renvoie 404. Netlify redirige vers l’ancien Express, sans moteur Python.

**Impact :** build PASS n’implique pas que l’application construite fournisse le parcours validé en développement. L’expression « intégration terminée » doit être restreinte à ce mode.

**Correction proposée :** définir et tester une topologie locale de distribution supportée avec routage vers Python, ou documenter explicitement la V0.3 comme labo de développement. Aucun déploiement distant n’a été tenté et il n’est pas requis pour corriger ce point.

## Mineur

### M1 — État de pagination et verdict de reproduction conservés entre runs

**Fichiers :** `client/components/backtest/BacktestResults.tsx:48-58`, `client/pages/Backtest.tsx` rendu sans clé de run. **Certitude : lecture du cycle React ; parcours multi-run non rejoué.**

**Reproduction proposée :** afficher une page 2 d’un run avec >25 trades, reproduire ce run, puis sélectionner un run avec <25 trades. `page` et le résultat de mutation ne sont pas réinitialisés : journal potentiellement vide, bornes de pagination incohérentes, ancien message « résultats identiques » encore visible pour le nouveau run.

**Impact :** confusion entre runs sans changement des métriques serveur. **Correction :** clé React par run ou reset des états/mutation sur `runId` ; associer explicitement toute preuve de reproduction au run demandé. Tester aussi le changement pendant la requête.

### M2 — La liste des runs impose USD à des montants d’autres devises

**Fichiers :** `client/pages/Backtest.tsx` appel `fmtSignedMoney(r.net_pnl)` ; `client/lib/format.ts::fmtSignedMoney` ; `storage/catalog.py::list_runs`. **Certitude : lecture directe ; capture multidevise non exécutée.**

**Reproduction proposée :** créer un run EUR avec un contrat cohérent (ex. XAUEUR), puis consulter le sélecteur : formatage USD par défaut. Le détail du run utilise correctement `manifest.config.account_currency`.

**Impact :** une valeur persistée correcte reçoit une mauvaise unité dans la liste. **Correction :** fournir la devise dans chaque résumé et la passer au formateur, ou ne pas afficher de montant tant que cette devise manque ; test de rendu multidevise.

### M3 — Validation temporelle et erreurs de fuseau incomplètes

**Fichiers :** `risk/guardian.py:108-112`, `strategies/base.py::TradingHours._tz`, `backtest/models.py::BacktestConfig`. **Certitude : fuseau invalide reproduit ; fenêtre inversée constatée dans le code.**

**Reproduction :** `risk.day_timezone="Not/AZone"` via POST : **500**, au lieu de 422, car `ZoneInfoNotFoundError` n’est pas convertie en erreur de validation. `trade_start > trade_end` n’a pas de validateur croisé et peut produire une simulation vide plutôt qu’un refus.

**Impact :** requêtes invalides mal expliquées ; l’affirmation générale « erreurs utilisateur → 4xx » est trop large. **Correction :** convertir les exceptions de fuseau en ValueError, typer et normaliser les dates, refuser NaT et les intervalles inversés/vides selon le contrat choisi. Ajouter des tests API sans exception serveur.

### M4 — MAE/MFE exacts en apparence, mais fondés sur toute la bougie de sortie

**Fichiers :** `backtest/engine.py:151-163`, champs `mae_price/mfe_price/mae_r/mfe_r` ; limite déjà documentée. **Certitude : reproduite.**

**Reproduction :** entrée BUY 100,35, bougie O=100, H=1000, L=98, C=100 : SL prioritaire, mais MFE enregistré **899,65**, soit **449,825 R**, sans preuve que ce haut a précédé la fermeture.

**Impact :** excursions impropres à l’apprentissage de règles de sortie ou à une validation du risque sans qualification. **Correction :** stocker des bornes/une qualité « indéterminé OHLC », exposer l’hypothèse dans les exports, ou utiliser des ticks ; ne pas présenter ces excursions comme une trajectoire observée exacte.

## Git, secrets, dépendances et tests manquants

État vérifié : **99 fichiers suivis modifiés**, dont **72 uniquement LF/CRLF** et **27 avec du contenu différent**. Les comptes du handoff sont donc reproduits. `quant/`, les types API et de nombreux ajouts restent non suivis. Aucune opération d’ajout, commit, reset ou push exécutée.

`.env` est toujours suivi et `.gitignore` contient `!.env`. Les variables présentes vérifiées sont une clé publique placeholder et un message non credential ; aucune valeur n’est reproduite ici. Aucun secret actif identifié dans ce fichier. Cela ne constitue pas une certification exhaustive de tout l’historique et de tous les fichiers ignorés. Retirer à terme `.env` du suivi tout en conservant le fichier local, publier un exemple sans secret et faire une détection de secrets avant préparation d’un commit. Une conversion des fins de ligne doit être un changement séparé et relu.

Le hash du code identifie plusieurs sous-packages mais pas les versions de Python/pandas/numpy ; les dépendances Python sont bornées largement et sans verrou déterministe fourni. Le cache du fingerprint suppose un processus redémarré après changement du code. Ces limites sont en partie déjà documentées : enregistrer l’environnement exact et une recette verrouillée, puis vérifier le rejeu depuis un environnement propre. Le fingerprint ne remplace pas le versionnement Git, et les hashes tronqués ne constituent pas une preuve cryptographique d’authenticité.

La couverture positive actuelle est utile, mais doit être complétée en priorité par les scénarios B1–B3 et I1–I8. Les tests d’upload existants prouvent le 413 final, pas le bornage avant réception. Les tests CORS prouvent un en-tête, pas l’absence de mutation. Les tests de reproduction comparent des hashes déclarés sans altérer les artefacts. Les comparaisons TS moteur/API ne vérifient pas tous les champs OpenAPI ; les assertions de type TypeScript ne valident pas le JSON à l’exécution. Les parcours Chrome actuels couvrent un run démo et l’absence initiale d’API, pas une coupure en cours, un changement entre runs, une devise différente ou un import navigateur.

Tests non exécutés : saturation volontaire de disque/mémoire, crash disque injecté, course déterministe de sauvegarde, exécution de l’application construite, clone propre/installations neuves, comparaison ticks/MT5 et exploitation depuis une page web étrangère. Ces limites sont explicitement séparées des défauts reproduits ; aucun compte de trading n’a été utilisé.

## Conditions du passage à V0.4

1. Corriger les trois bloquants et leur ajouter des régressions indépendantes ; vérifier un export Git complet et propre.
2. Refuser les entrées financières non finies, stabiliser identité/provenance des datasets et corriger l’import en minuscules.
3. Définir la politique du profil de risque, corriger les fills à l’ouverture et préserver l’intégrité atomique des runs.
4. Renforcer les mutations locales et la réception des uploads, puis rejouer les suites actuelles et les sondes adversariales.
5. Définir la distribution réellement supportée et enregistrer un environnement reproductible. Conserver l’étiquetage des simulations et les limitations OHLC/marge/devises.

**Verdict final : V0.3 utilisable comme prototype de recherche local, mais pas suffisamment fiable en l’état pour constituer un socle financier validé de V0.4. GO conditionnel après correction et vérification des points ci-dessus ; aucune autorisation d’ordre réel/démo ni preuve de rentabilité ne découle des PASS.**

## Pièces de preuve et relance

Dans le même répertoire que ce rapport : `probes.py`, `evidence.json`, `probes.log`, `financial_probe.py`, `financial-probe.log`, `javascript-tests-unrestricted.log`, `typecheck.log`, `build.log`, `ruff.log`, `e2e.log`, `e2e-api-down.log`. Log Python : `repo/python-tests.log`.

Les sources dans `repo/` sont la copie de travail auditée, hors données utilisateur. Les sondes créent exclusivement des catalogues temporaires. Pour rejouer les sondes avec l’environnement Python existant :

```sh
AUDIT_DIR=/private/tmp/codex-audit-v03-u1qibo2e
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$AUDIT_DIR/repo/quant/src" \
  "$AUDIT_DIR/repo/quant/.venv/bin/python" "$AUDIT_DIR/probes.py"
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$AUDIT_DIR/repo/quant/src" \
  "$AUDIT_DIR/repo/quant/.venv/bin/python" "$AUDIT_DIR/financial_probe.py"
```

L’emplacement `/private/tmp` est autorisé mais temporaire ; le rapport doit être conservé ailleurs par le propriétaire s’il souhaite une archive durable.
