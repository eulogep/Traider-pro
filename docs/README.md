# Documentation — par où commencer

| Je suis… | Je lis d'abord |
|---|---|
| Nouveau sur le projet | [`../README.md`](../README.md) (ce que fait la plateforme), puis [`../AGENTS.md`](../AGENTS.md) (carte du dépôt, règles, commandes) |
| Utilisateur (trader) | [`../quant/docs/VALIDATION.md`](../quant/docs/VALIDATION.md) (lire un verdict), [`../quant/docs/EXTERNAL_LAB.md`](../quant/docs/EXTERNAL_LAB.md) §1 (importer un rapport MT5), [`../quant/docs/REFERENCE_V370.md`](../quant/docs/REFERENCE_V370.md) (exemple complet) |
| Développeur | [`../quant/docs/ARCHITECTURE.md`](../quant/docs/ARCHITECTURE.md), [`../quant/docs/DECISIONS.md`](../quant/docs/DECISIONS.md), [`../quant/docs/KNOWN_LIMITATIONS.md`](../quant/docs/KNOWN_LIMITATIONS.md), [`../quant/AGENTS.md`](../quant/AGENTS.md) |
| Auditeur (Codex…) | la dernière passation dans [`handoffs/`](handoffs/), puis le rapport de validation de la version |

## Le produit et son cadre
| Document | Contenu |
|---|---|
| [`../quant/docs/CAHIER_DES_CHARGES.md`](../quant/docs/CAHIER_DES_CHARGES.md) | objectifs, exigences et interdits du projet |
| [`../quant/docs/ENTRETIEN_TRADER.md`](../quant/docs/ENTRETIEN_TRADER.md) | questions à poser au trader pilote avant de coder sa stratégie |
| [`../quant/docs/ROADMAP.md`](../quant/docs/ROADMAP.md) | versions livrées et prochaines étapes |
| [`../quant/docs/CHANGELOG.md`](../quant/docs/CHANGELOG.md) | changements par version |
| [`project/CONSOLIDATION_AUDIT.md`](project/CONSOLIDATION_AUDIT.md) | diagnostic initial du dépôt et plan de consolidation (2026-11-03) |
| [`project/DEPLOYMENT.md`](project/DEPLOYMENT.md) | plateforme locale et vitrine statique en ligne : mise à jour et mise en ligne |

## Technique
| Document | Contenu |
|---|---|
| [`../quant/docs/ARCHITECTURE.md`](../quant/docs/ARCHITECTURE.md) | modules, intégrité des runs, conventions de temps, garde, production locale |
| [`../quant/docs/DECISIONS.md`](../quant/docs/DECISIONS.md) | journal des décisions et de leurs raisons |
| [`../quant/docs/KNOWN_LIMITATIONS.md`](../quant/docs/KNOWN_LIMITATIONS.md) | tout ce que le logiciel ne fait pas ou fait de façon approchée |
| [`../quant/docs/EXTERNAL_LAB.md`](../quant/docs/EXTERNAL_LAB.md) | importateur MT5, schéma `ato-external-sim/1`, API, limites des rapports et des `.ex5` |
| [`../quant/docs/SECURITY_V05.md`](../quant/docs/SECURITY_V05.md) | contrôles de sécurité de l'import, du pont MT5 et des archives |

## Validation et preuves (par version)
| Version | Document |
|---|---|
| v0.5.0 | [`../quant/docs/VALIDATION_V05.md`](../quant/docs/VALIDATION_V05.md), cas de référence [`../quant/docs/REFERENCE_V370.md`](../quant/docs/REFERENCE_V370.md), test dans MT5 [`../quant/docs/MT5_TEST_BASELINE_2026.md`](../quant/docs/MT5_TEST_BASELINE_2026.md) |
| v0.4.1 | [`../quant/docs/VALIDATION_V041.md`](../quant/docs/VALIDATION_V041.md), campagne [`../quant/research_campaign/PROTOCOL.md`](../quant/research_campaign/PROTOCOL.md) (résultats bruts dans `../quant/research_campaign/results/`) |
| v0.4.0 | [`../quant/docs/REPRODUCTION_V04.md`](../quant/docs/REPRODUCTION_V04.md) (reconstitution des chiffres annoncés) |
| v0.3.1 | [`../quant/docs/TEST_REPORT.md`](../quant/docs/TEST_REPORT.md) (historique) |
| avant v0.2 | [`../quant/docs/AUDIT_INITIAL.md`](../quant/docs/AUDIT_INITIAL.md) |

## Audits indépendants et passations
- **`audits/`** : rapports Codex et leurs pièces, **conservés tels quels** (preuves, empreintes dans
  `audits/SHA256SUMS_2026-11-04.txt`) :

  | Dossier | Version auditée | Verdict |
  |---|---|---|
  | `codex-v03-2026-11-04/` | V0.3 | NON en l'état |
  | `codex-counter-v031-d7c34xx6/` | V0.3.1 (contre-audit) | 6 corrections partielles |
  | `codex-audit-v04-lhxtu170/` | V0.4.0 (audit quant et IA) | NO-GO comme version validée ; prototype fonctionnel |

  On n'y modifie rien, même un lien.
- **`handoffs/`** : ce que chaque version demande à l'auditeur de contester :
  - [`CODEX_REVIEW_HANDOFF.md`](handoffs/CODEX_REVIEW_HANDOFF.md) : v0.3.1 ;
  - [`CODEX_HANDOFF_V041.md`](handoffs/CODEX_HANDOFF_V041.md) : v0.4.1 ;
  - [`CODEX_HANDOFF_V05.md`](handoffs/CODEX_HANDOFF_V05.md) : v0.5.
- [`../quant/docs/CODEX_REVIEW_PROMPT.md`](../quant/docs/CODEX_REVIEW_PROMPT.md) : prompt d'origine de la première revue
  (historique).

## Base de connaissances
- [`knowledge/`](knowledge/) : chaque source externe est vérifiée contre le code avant d'être utilisée.
- Les sources elles-mêmes sont dans [`knowledge/sources/`](knowledge/sources/).

## Données de référence
- [`../quant/tests/fixtures/mt5/`](../quant/tests/fixtures/mt5/) : rapports MT5 réels de « Gold Grid Strategy V3.70 »
  (HTML, XLSX) et leur export CSV normalisé, avec SHA-256. Les tests vérifient que ces fichiers n'ont pas changé.

## Conventions
- **Langue** : documentation et interface en français ; code et commentaires en anglais.
- **Résultats** : on publie des résultats **exacts et datés**, jamais supposés. Toute affirmation chiffrée renvoie à un
  test, à un journal ou à un fichier de résultats.
- **Mise à jour** : un document périmé est soit mis à jour, soit marqué « historique » avec un renvoi vers le
  document courant.
