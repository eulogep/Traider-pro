# Contre-audit indépendant — AI Trader Optimizer V0.3.1

Date : 4 novembre 2026, Europe/Paris. État audité : copie de travail dont HEAD est `2dedf6c758ec124098db5f6abd4076e1d8dd134b`, sans commit des corrections.

**Conclusion : les résultats de tests annoncés sont reproduits et les corrections apportent une amélioration réelle. L’affirmation « 17 anomalies intégralement corrigées » reste trop forte.** Une voie de lecture des résultats financiers échappe toujours à la vérification ; des limites de séparation temporelle, de réception de données et de sécurité applicative restent contournables dans les scénarios ci-dessous.

**Verdict préparation des commits : GO pour préparer une série traçable et explicitement assortie de ces réserves.** Ce GO autorise intellectuellement une préparation de sauvegarde/revue, pas à qualifier cette version de entièrement validée ni à publier. Aucun commit ni changement de l’index n’a été effectué.

**Verdict démarrage V0.4 sur un socle déclaré stabilisé : NO-GO en l’état.** Fermer au minimum N1, N2, N3 et N10, puis les régressions correspondantes avant de construire des conclusions IA dessus. La préservation de cette version dans des commits de travail n’est pas une certification scientifique.

## 1. Méthode et pièces de preuve

Travail dans `/private/tmp/codex-counter-v031-d7c34xx6/`. L’export a été produit à partir de l’union exacte de `git ls-files --cached --others --exclude-standard` : **239 fichiers**, sans `.git`, sans données runtime, caches ou dépendances. Les dépendances ont ensuite été ajoutées séparément pour l’exécution : copie de `node_modules`, lien vers le venv existant avec `PYTHONPATH` pointant sur les sources exportées et `PYTHONDONTWRITEBYTECODE=1`. Le manifeste SHA-256 des sources exportées est conservé dans `snapshot-manifest.json`.

Les quatre hashes des preuves originales archivées dans `docs/audits/codex-v03-2026-11-04/SHA256.json` concordent. Le rapport original, les handoffs, l’architecture, D-27 à D-34, les tests et modules de sécurité ont été lus.

La sonde financière originale a été copiée **sans modification**, et passe. La sonde originale `probes.py` a également été rejouée telle quelle : elle s’arrête avec `KeyError: metrics`, car ses présupposés d’interface ne sont plus valides. Ce n’est pas une validation de correction à lui seul : les sondes indépendantes `counter_probes.py`, `extended_probes.py` et `boundary_and_publication.py` utilisent le Host local et l’en-tête de mutation requis, puis poursuivent chaque attaque séparément. Leurs objectifs financiers et temporels sont conservés.

**Aucun fichier du dépôt principal, index, commit, compte courtier ou déploiement n’a été modifié par cet audit.** Les seules falsifications et interruptions ont porté sur des catalogues et sources temporaires. Une modification temporaire de la tolérance de `storage/integrity.py` dans l’export a servi à tester la couverture du fingerprint, puis a été restaurée.

## 2. Exécutions et résultats exacts

| Contrôle sur l’export | Résultat |
|---|---|
| Python `pytest -q -p no:cacheprovider` | **PASS : 215 tests**, 216,65 s |
| Ruff `check --no-cache src tests app.py scripts` | **PASS** |
| `pnpm test` | **PASS : 30 tests, 7 fichiers** |
| `pnpm typecheck` | **PASS** |
| `pnpm build` | **PASS**, SPA et serveur |
| Chrome `backtest-flow.mjs` | **PASS : 21/21** |
| Chrome `backtest-flow.mjs --api-down` | **PASS : 3/3** |
| Distribution construite `production-smoke.mjs` | **PASS : 9/9** |
| Sonde financière originale | **PASS : 12/12** BUY/SELL × bid/mid × coûts |
| Sondes adaptées du développeur | **14/14 affichés**, avec réserve sur B1 ci-dessous |
| Vérification des dépendances installées | Python **3.12.14** ; **49/49** versions conformes à `requirements.lock` |
| Sondes indépendantes | Résultats détaillés dans les JSON et logs ; défauts N1–N10 reproduits |

La sonde B1 du développeur regarde uniquement stdout de `git check-ignore`, sans vérifier son code retour. Dans l’export sans `.git`, Git échoue et cette sonde affiche pourtant PASS. **Ce PASS particulier n’est pas probant.** B1 a été vérifié séparément contre le vrai dépôt : aucun package Python indispensable n’est ignoré.

L’installation des dépendances à partir de zéro n’a pas été refaite par cet audit ; le test sur export valide les sources nécessaires avec l’environnement installé et vérifié, pas une résolution entièrement neuve des paquets. Le protocole de vrai clone figure plus bas.

## 3. État des 17 anomalies initiales

PASS signifie ici « comportement original corrigé dans le périmètre vérifié », pas absence de tout défaut du module.

| ID | Statut indépendant | Observation |
|---|---|---|
| B1 | **PASS technique** | Package `data` inclus dans les 239 fichiers ; dépendances et sources nécessaires à build/tests présentes. Encore non suivi, comme le reste de `quant/`. |
| B2 | **PARTIEL** | Six artefacts falsifiés sont refusés sur détail/reproduction ; remplacement sans nouveau hash refusé ; collection et validation sémantique incomplètes : N1/N2. |
| B3 | **PARTIEL** | Sonde originale : IS 0 / OOS 1, +31,79 USD seulement en OOS. Bornes M1/M5/M15/H1 et coupures non alignées correctes. Embargo négatif : N3. |
| I1 | **PASS ciblé** | `1e309`, `-1e309`, NaN, chaîne et booléen donnent 422. Injection indépendante d’une sortie infinie : simulation interrompue. Tests d’intermédiaires inclus dans les 215 PASS. |
| I2 | **PARTIEL** | Relâchement des limites RiskConfig et modification du contrat refusés en supervisé ; périmètre et trace de politique incomplets : N5. |
| I3 | **PARTIEL** | Limite d’octets avant parsing effective ; flux JSON coupé après 4 morceaux de 300 octets sur 20 proposés pour 1 Kio. Limite de lignes contournable : N4. |
| I4 | **PARTIEL application** | Garde FastAPI efficace ; variantes Host/Origin refusées ; les mutations Express restent exposées : N10. |
| I5 | **PASS** | Minuscules normalisées, import puis relecture possibles. |
| I6 | **PASS** | `.500` refusé ; différence de prix de 1e-8 identifiée ; round-trip exact couvert et passé. |
| I7 | **PARTIEL** | Nature contradictoire refusée 409 et première déclaration préservée. Réponse d’import et preuve brute : N7/N8. |
| I8 | **PASS** | Ouverture au-delà du TP traitée avant SL intrabougie ; BUY original +31,79 USD. Six cas BUY/SELL du correctif exécutés. |
| I9 | **PASS processus** | Staging, idempotence, tests de 6 écrivains ; interruption indépendante après rename récupérable ; 4 écrivains et lecteur concurrent sans résultat partiel. Pas de certification contre panne électrique. |
| I10 | **PASS local** | Distribution construite transmet réellement les requêtes à Python : 9/9. Netlify demeure hors périmètre supporté. |
| M1 | **PASS parcours** | Remontage par clé de run et scénario navigateur du second run passent. |
| M2 | **PASS ciblé** | Devise du résumé fournie et utilisée ; tests formatage/parcours passent. Pas de capture indépendante d’une stratégie EUR réelle. |
| M3 | **PASS** | Fuseaux invalides et fenêtres invalides refusés en 422. |
| M4 | **PASS hypothèse** | Excursions qualifiées `lower_bound_ohlc` ; ancien scénario ne rapporte plus 449,8 R. Trajectoire tick non reconstituée. |

Le réemploi de la dernière bougie IS pour calculer le signal connu à son heure de clôture et exécuté à la première ouverture OOS est légitime : c’est une observation disponible à la décision, pas l’utilisation de son résultat futur. Aucun nouveau chevauchement sur les horizons de position testés avec coupures valides n’a été constaté ; la position IS est liquidée sur la dernière clôture autorisée. Les perturbations futures M15→M1 ne modifient pas le passé testé.

La sélection opportuniste d’après les colonnes OOS de `compare_variants` reste possible : c’est une limite du protocole humain, déjà avertie, et non une preuve d’avantage. Aucun modèle appris ni mécanisme imposant un test final vierge n’est établi dans cet état V0.3.1.

## 4. Défauts restant reproductibles et nouveaux écarts

Les chemins Python ci-dessous sont relatifs à `quant/src/ai_trader_optimizer/`. Les dix constats comprennent **1 bloquant, 8 importants et 1 mineur**. Certains étendent un défaut ancien ; ils ne sont pas tous causés par les corrections.

### N1 — Bloquant : la collection sert des résultats financiers non vérifiés

**Fichiers :** `storage/catalog.py:281-297`, route GET `/api/v1/backtests`, sélecteur de résultats React. **Lien : B2. Certitude : reproduit.**

**Reproduction :** créer un run sain, modifier uniquement `runs.metrics_json` dans SQLite en donnant `net_pnl=987654321`, sans modifier artefacts, `integrity.json` ni `run_digest`. GET de la collection renvoie **987654321**, GET du détail renvoie **27,366839136113413**, et POST reproduction répond `identical=true`, `deterministic=true`, `artifacts_intact=true`. Une autre sonde altère seulement `trades.csv` : détail 409, mais collection 200 avec chiffres du run corrompu.

**Impact :** un cache SQLite corrompu suffit à afficher une performance fausse dans la liste, tout en conservant un verdict de reproduction positif pour le détail sain. Pas besoin de falsifier toutes les preuves ni de posséder une signature. Il ne s’agit pas d’un accès distant démontré : c’est la détection de corruption locale promise par la V0.3.1 qui reste incomplète.

**Correction :** traiter la collection comme une lecture financière soumise à vérification : dériver ses valeurs des artefacts vérifiés, ou vérifier un cache lié au digest avant de le servir. Refuser/qualifier les runs corrompus sans afficher leurs métriques. Tester chaque voie de lecture, y compris résumés et métadonnées indexées, et distinguer cache, résultat et statut d’intégrité.

### N2 — Important : la cohérence financière n’est pas recalculée à partir des prix

**Fichiers :** `storage/integrity.py:190-228`, `storage/catalog.py:210-229`. **Lien : B2. Certitude : reproduit.**

**Reproduction :** sur un résultat moteur non encore publié dans un nouveau catalogue, ajouter 100 au premier `exit_price`, conserver `net_pnl`, commissions et courbe, recalculer seulement `result_hash` par l’utilitaire officiel. `check_consistency` renvoie une liste vide ; publication et lecture sont acceptées. P&L déclaré : **−23,78908116094501** ; P&L indépendant selon direction, lots, contrat, prix et commission : **−1 723,7890811609452**.

**Impact :** un writer fautif peut publier des prix et montants contradictoires avec des hashes exacts. Recalculer `compute_metrics` valide les agrégats des montants déclarés, pas la formule économique de chaque transaction. Ce scénario n’est pas une falsification cohérente de tous les fichiers et de l’index d’un run déjà publié ; il teste la frontière de première publication.

**Correction :** contrôles indépendants par trade : direction, lots, contrat, P&L prix, commissions, net, capital courant, risque et R ; rapprochement trade/décision, pas uniquement le même ensemble d’identifiants ; vérification chronologique de la courbe. Conserver les contrôles de hashes. Une signature ne corrigerait pas une erreur du writer avant signature.

### N3 — Important : un embargo négatif recrée un chevauchement IS/OOS

**Fichiers :** `ai/validation.py:28-49`. **Lien : B3. Certitude : reproduit.**

**Reproduction :** `chronological_split(..., train_fraction=.5, embargo=Timedelta(minutes=-1))` sur 12:00–12:10 donne IS jusqu’à 12:05 et OOS à partir de 12:04. Un signal à 12:03 dont le trade prend son TP dans la bougie 12:04 est compté dans les deux segments : **+31,79 USD chacun**. `walk_forward_splits` accepte aussi cette valeur : première fin train 12:10, premier début test 12:09.

**Impact :** le moteur respecte désormais ses bornes mais le générateur public de ces bornes peut encore violer leur invariant. Le comparateur actuel, qui utilise l’embargo par défaut nul, n’est pas exposé à cette sonde par l’API. Le risque devient direct dès que V0.4 réutilise ces helpers avec une configuration d’embargo.

**Correction :** refuser tout embargo négatif, intervalles inversés et durées invalides ; valider `train_start < train_end <= test_start < test_end` pour chaque split et ajouter des tests sur toutes les entrées publiques. Ne pas présenter ce cas comme une régression de la correction des bornes du moteur, qui fonctionne.

### N4 — Important : la borne de lignes se contourne avec des fins de ligne CR

**Fichier :** `api/app.py:235`. **Lien : I3. Certitude : reproduit via HTTP.**

**Reproduction :** `ATO_MAX_ROWS=10`, CSV OHLC valide de 30 bougies généré avec `lineterminator='\r'`. Le corps respecte la limite d’octets. Réponse **201**, dataset enregistré avec **30 lignes**. Le comptage ne regarde que `b'\n'`, alors que pandas accepte aussi CR.

**Impact :** la limite métier de lignes annoncée n’est pas appliquée ; des entrées compactes peuvent dépasser le budget de parsing/traitement. La nouvelle limite d’octets reste bien active : le défaut initial de réception totale n’est pas revenu.

**Correction :** compteur d’enregistrements conforme au parseur et postcondition sur le nombre réellement parsé, avec traitement borné/chunké ; couvrir CR, LF, CRLF et champs cités. Ajouter aussi un test de lecture maximale en mémoire avant rejet.

### N5 — Important : le mode supervisé n’identifie pas une politique complète et immutable du run

**Fichiers :** `services.py:83-110`, `backtest/engine.py:311-327`, `storage/catalog.py:259-266`. **Lien : I2/traçabilité. Certitude : reproduit.**

**Reproduction A :** publier un run en recherche, activer `ATO_RISK_POLICY=supervised`, refaire la même requête conforme au profil. Le serveur annonce `mode=supervised, enforced=true` sur `/settings/risk-policy`, mais retourne **201 avec l’ancien manifeste `mode=research, enforced=false`**. Le run_id ignore la politique ; l’idempotence reprend le manifeste ancien.

**Reproduction B :** en mode supervisé, envoyer les mêmes limites RiskConfig et le même contrat, mais coûts à zéro, capital initial 1 milliard et horaires étendus à tous les jours. Réponse **201**, `enforced=true`. Les limites en pourcentage sont bien appliquées : ceci ne démontre pas un dépassement interne du Guardian. En revanche, ces hypothèses peuvent changer fortement le risque absolu et la performance, sans que la portée du label « supervisé » soit suffisamment précise.

**Impact :** la trace ne décrit pas toujours le contexte de la demande actuelle ; le label d’application ne doit pas être interprété comme une validation des coûts, du capital ou du calendrier. Le contrôle champ par champ des limites existantes est utile et son contournement direct n’a pas été reproduit.

**Correction :** définir/versionner un profil serveur explicite et sa portée ; séparer contexte de calcul et contexte de validation. Inclure l’identité pertinente dans la trace ou ajouter une attestation distincte vérifiable de revalidation, sans réécrire l’ancien manifeste. Si le mode doit imposer coûts/capital/horaires, les figer côté serveur ; sinon limiter explicitement le label aux limites RiskConfig et au contrat.

### N6 — Important : le fingerprint omet des nouveaux modules qui influencent les résultats

**Fichier :** `backtest/codehash.py:14-24`. **Lien : reproductibilité. Certitude : reproduit dans la copie, modification restaurée.**

**Reproduction :** modifier la tolérance par défaut de `storage/integrity.py::_close` de `1e-9` à `1e-3`, vider le cache `code_fingerprint`, recalculer : **hash inchangé**. `storage/`, `numeric.py`, `services.py` ne font pas partie des chemins couverts, alors qu’ils définissent désormais sérialisation/fingerprint des résultats, validation et politique. L’exemple de tolérance change l’acceptation de preuves ; une évolution de sérialisation dans ce même fichier changerait directement les empreintes des résultats.

**Impact :** deux versions sémantiquement différentes des protections peuvent porter la même version et empreinte moteur. Les dépendances sont maintenant verrouillées, mais cela ne répare pas ce périmètre de code.

**Correction :** définir une empreinte de calcul et une empreinte de validation/provenance couvrant tous les modules pertinents, ou hasher tout le package avec une liste d’exclusions justifiée. Enregistrer également la recette/env et le commit une fois disponible ; tester une modification comportementale de chaque groupe de modules.

### N7 — Important : le catalogue accepte une preuve brute dont le contenu ne correspond pas au SHA annoncé

**Fichier :** `storage/catalog.py:112-145`. **Lien : I7/provenance. Certitude : reproduit à la frontière de stockage Python.**

**Reproduction :** importer un CSV en mémoire pour obtenir un Dataset et son `raw_sha256`, puis appeler `save_dataset(ds, b'wrong raw bytes')`. Le fichier est publié sous le SHA du CSV original alors que son SHA réel est différent. `load_dataset` réussit ensuite car il ne vérifie que les bougies dérivées.

**Impact :** le lien entre source archivée, métadonnées et données exécutées peut être faux après un appel de writer fautif ou une corruption du brut. La route HTTP courante passe les bons octets dans les cas testés ; aucun contournement de cette route par le client n’est affirmé.

**Correction :** comparer le SHA des octets reçus au SHA déclaré avant écriture, vérifier un fichier brut déjà présent au lieu de le considérer implicitement intact, et proposer une vérification de provenance reliant le brut au dérivé. La distinction contenu/provenance et le refus de nature contradictoire restent de bonnes corrections.

### N8 — Mineur : la réponse d’import décrit une provenance différente de celle qui est persistée

**Fichiers :** `api/app.py:250`, `storage/catalog.py:126-153`. **Lien : intégration après I7. Certitude : reproduit via HTTP.**

**Reproduction :** importer deux fois les mêmes octets et la même nature, d’abord source `probe`, puis source `new source`. Le deuxième POST renvoie `dataset.source='new source'`, tandis que GET du même dataset renvoie `source='probe'`. Le même principe concerne le nom et les notes.

**Impact :** le frontend ou un client peut croire que la deuxième provenance est la provenance primaire, alors qu’elle ne constitue qu’une déclaration historique. Ce n’est plus un écrasement de la première déclaration.

**Correction :** retourner les métadonnées réellement persistées après sauvegarde et exposer séparément la déclaration ajoutée à l’historique. Ajouter une assertion POST/GET sur l’ensemble des champs concernés.

### N9 — Important pour les futurs labels : sortie à la clôture datée à l’ouverture

**Fichiers :** `backtest/engine.py:147,291`, test `test_b3_position_open_at_in_sample_end_is_closed_at_last_in_sample_close`. **Lien : temporalité, défaut antérieur non corrigé. Certitude : reproduit.**

**Reproduction :** position liquidée `END_OF_DATA` au close de la bougie M1 ouverte à 12:02 : prix de sortie **100,95**, mais `exit_time=12:02`. Le manifeste indique correctement la dernière clôture à **12:03**. Le nouveau test fige encore l’heure d’ouverture comme `exit_time`.

**Impact :** la borne IS/OOS du calcul n’est pas erronée sur ce cas, mais le journal donne un résultat disponible une bougie trop tôt si un consommateur interprète `exit_time` comme disponibilité du label. Le risque est important avant d’utiliser les horizons de sortie pour la purge d’un modèle V0.4.

**Correction :** distinguer `exit_bar_open` et heure de sortie/disponibilité. Pour END_OF_DATA, la disponibilité est la clôture ; pour SL/TP intrabougie, fournir une borne de disponibilité conservatrice, pas une heure précise inventée. Pour sorties à l’ouverture, conserver l’ouverture. Ajuster tests et contrats API/IA.

### N10 — Important : la protection des mutations ne couvre pas l’Express encore distribué

**Fichiers :** `server/index.ts` CORS et routes `/api/settings`, `server/routes/settings.ts::resetSettings`, `server/node-build.ts:11-13`. **Lien : I4 à l’échelle du produit. Certitude : reproduit sur le vrai serveur construit.**

**Reproduction :** créer un fichier de réglages sentinelle dans le cwd temporaire du serveur construit. POST `/api/settings/reset`, `Origin: https://evil.example`, `Content-Type: application/x-www-form-urlencoded`, corps vide, sans `X-ATO-Request` : **200**, fichier supprimé. Le même test avec `Host: evil.example` réussit également. Aucun réglage du dépôt principal n’a été utilisé ni supprimé.

**Impact :** la garde protège l’API quant, mais l’application servie inclut toujours des mutations qui acceptent une requête de forme simple inter-origines. Les 9/9 du smoke test ne couvrent pas ce chemin. Ceci prouve une mutation serveur avec ces en-têtes ; une exploitation depuis une page web étrangère réelle n’a pas été exécutée et dépend aussi des protections réseau local du navigateur.

**Correction :** appliquer les contrôles Host/Origin/mutations à tous les endpoints de l’application construite, ou retirer les routes legacy inutilisées. Tester la non-mutation des fichiers pour chaque endpoint POST actif. CORS seul ne suffit toujours pas.

## 5. Git et environnement : risques restant avant la préparation

- **102 fichiers suivis**, **137 fichiers versionnables non suivis**, **aucun changement préparé dans l’index** au début de l’audit. L’export de 239 fichiers correspond à ces deux ensembles ; il ne prédit pas un futur `git add -p` partiel.
- **99 fichiers suivis modifiés**, **72 seulement par fins de ligne**, **27 avec changement de contenu**, comme annoncé. Les diffs fonctionnels doivent être relus sans le bruit CRLF ; ne pas réécrire tout le worktree pendant la préparation.
- Restent indispensables et non suivis : l’ensemble `quant/` (sources, YAML, configuration Streamlit, tests, `pyproject.toml`, `requirements.lock`), `server/quantProxy.ts`, les fichiers nouveaux `server/config`, `controllers`, `middleware`, les types `shared/quant-api.ts`, les clients/hooks/store/composants React nouveaux, les tests et scripts E2E. La liste complète est enregistrée dans `git-audit.json` et `files.txt`.
- B1 est corrigé dans `.gitignore`. L’export ne contient aucun `.venv`, node_modules, egg-info, pyc ou cache. Les logs d’audit sont désormais inclus intentionnellement ; cela ne signifie pas que tout journal futur est exempt de données privées.
- `.env` demeure suivi, `!.env` demeure présent et `.env.example` est encore non suivi. Le `.env` observé contient seulement les deux variables déjà identifiées (placeholder public et message). Aucune valeur n’est reproduite ici. Aucun token actif correspondant aux motifs de clés privées/GitHub/OpenAI/AWS/Slack recherchés dans les 239 fichiers n’a été trouvé. Cette recherche bornée ne certifie pas tout l’historique ni toutes les données ignorées.
- Le plan de commits doit retirer `.env` du suivi en conservant sa copie locale, et inclure son exemple. Les nouveaux fichiers importés doivent être préparés avec les fichiers qui les importent. En particulier, `server/node-build.ts` dépend de `server/quantProxy.ts` : ne pas séparer arbitrairement ces éléments entre commits qui doivent être testables.
- La mention `.gitattributes` dans un plan ne l’a pas créée : vérifier son effet dans une copie avant le commit dédié. Garder distincts le changement de règles Git, les fins de ligne et les modifications métier.
- Les 49 versions verrouillées sont conformes à l’environnement utilisé. Le lock décrit macOS ARM/Python 3.12 ; Windows est explicitement non supporté (`fcntl`). L’installation sur un nouvel environnement et les paquets build ne sont pas certifiés par le simple contrôle des versions installées.

La préparation technique peut donc commencer de façon sûre, avec une liste explicite et des commits de travail honnêtement nommés. **Ne pas préparer une note de version qui clôture les 17 points ni un tag « validé » sur la seule base de ces tests.**

## 6. Protocole de validation depuis un vrai clone après les futurs commits

Ce protocole est proposé, **pas exécuté sur un futur commit inexistant**. Il n’autorise aucune création de commit, mutation d’index ou publication dans le dépôt principal par cet audit.

1. Depuis un clone neuf d’un commit SHA explicitement choisi, enregistrer SHA, branche, remotes, OS, architecture et versions Python/Node/pnpm. Confirmer worktree propre et absence de `.env` suivi ; vérifier les sources avec `git ls-files quant/src` et la présence de toutes les specs/configs/locks requis. Ne pas copier des sources non suivies depuis le poste de développement.
2. Installer PNPM via la version `packageManager`, puis `pnpm install --frozen-lockfile`. Créer un venv Python 3.12 neuf ; `pip install -r quant/requirements.lock`, puis `pip install --no-deps -e ./quant` et `pip check`. Conserver les versions résolues et l’origine des paquets, sans secrets. Toute dépendance de build non verrouillée doit être signalée.
3. Utiliser exclusivement un `ATO_DATA_DIR` temporaire et aucun identifiant ; ne pas importer les données privées du poste. Exécuter les suites Python, Ruff, JavaScript, TypeScript et build ; échouer explicitement si l’intégration Python a été ignorée.
4. Exécuter les trois parcours : navigateur nominal, API hors ligne et distribution locale construite. Vérifier également les mutations legacy et les statuts d’erreur, pas seulement `/api/v1`.
5. Rejouer les sondes indépendantes et les régressions des corrections N1–N10 : index SQLite, premières publications incohérentes, split négatif, CR/LF/CRLF, politique, hash du code, brut, réponses persistées, disponibilité des labels, routes Express.
6. Faire deux runs identiques à partir des mêmes octets importés, config et spec : empreintes identiques, aucune réécriture des artefacts ; vérifier chaque lecture, export et collection. Injecter une corruption après sauvegarde et une interruption avant/après publication dans le catalogue de test.
7. Archiver les commandes, codes retour, logs, captures, hashes des sources/preuves et limites ; vérifier `git status --porcelain` toujours propre après les tests, hors chemins de données explicitement externes. Répéter au moins sur la plateforme cible supportée depuis laquelle le logiciel sera utilisé.

## 7. Limites de ce contre-audit

Pas de saturation de disque/mémoire, panne électrique ou corruption matérielle injectée ; pas de fuzzing exhaustif HTTP, de plateforme Windows ou Netlify, de navigateur tiers hostile, de mesure sur ticks ni de connexion courtier. Les verrous ont été testés au niveau processus/threads via les tests existants et les sondes ; une visibilité incomplète avant insertion SQLite après rename retourne 404 puis récupère correctement au retry, ce qui est acceptable ici. Le quota reste préventif et ne garantit pas une borne absolue durant une écriture.

Les hashes locaux détectent une corruption mais ne prouvent pas l’authenticité contre quelqu’un qui peut réécrire tous les fichiers et l’index. Une signature n’est pas exigée pour ce laboratoire local. En revanche, N1 et N2 ne peuvent pas être écartés par cette limite : ils concernent une lecture non vérifiée ou un writer incohérent.

Les simulations restent OHLC avec coûts fixes, sans marge, financement, conversions ou liquidité ; un TP_GAP au niveau de la cible est une convention conservatrice cohérente, pas une reproduction d’exécution réelle. Les calculs élémentaires BUY/SELL/coûts contrôlés restent corrects. **Robustesse logicielle, fidélité de simulation et rentabilité d’une stratégie sont trois questions distinctes ; aucun des PASS ne démontre la troisième.**

## 8. Verdicts séparés

- **Préparer les commits : GO**, avec inventaire explicite, sauvegarde, conservation des changements du propriétaire, `.env` retiré du suivi dans un incrément autorisé et réserves de cet audit visibles. Aucun feu vert donné pour publier ou déclarer tout corrigé.
- **Commencer V0.4 sur un socle V0.3.1 présenté comme stabilisé : NO-GO**, tant que N1/N2/N3/N10 et les contrats de disponibilité/provenance nécessaires à l’IA ne sont pas traités. Une expérimentation séparée ne doit pas transformer ces limites en preuves financières.

## 9. Artefacts de relance

Sources/export : `repo/`, `files.txt`, `snapshot-manifest.json`. Environnement : `environment.json`. Git/secrets : `git-audit.json` et empreinte initiale de l’index `index.sha256`.

Sondes : `counter_probes.py`, `extended_probes.py`, `boundary_and_publication.py`, `legacy-security.mjs`, `financial_probe.py` original. Preuves : `counter-evidence.json`, `extended-evidence.json`, `boundary-publication-evidence.json`, `legacy-security.log` ; logs de chaque suite dans le même répertoire.

Relance Python depuis le répertoire de ce rapport :

```sh
AUDIT_DIR=/private/tmp/codex-counter-v031-d7c34xx6
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$AUDIT_DIR/repo/quant/src" \
  "$AUDIT_DIR/repo/quant/.venv/bin/python" "$AUDIT_DIR/counter_probes.py"
```

L’emplacement est temporaire ; une copie durable du rapport et des preuves doit être conservée par le propriétaire.

## Addendum de périmètre

Après la capture V0.3.1, le workspace partagé a évolué vers V0.4.0 pendant le contre-audit. Les conclusions ci-dessus portent sur les 239 fichiers figés dans le manifeste de cet audit ; les tests n’ont pas mélangé les deux versions. L’index original est resté inchangé. Un nouvel export distinct sert à l’audit V0.4 demandé ensuite.
