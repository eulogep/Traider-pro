# Stratégies du trader pilote (nouvel ami)

Ce dossier contient **uniquement** les stratégies du trader pilote, séparées des
stratégies de référence (`../baseline/`) et des stratégies d'autres traders (`../third_party/`).

- Une stratégie reste en `status: draft` tant que ses règles ne sont pas formalisées
  et validées avec lui (voir `docs/ENTRETIEN_TRADER.md`).
- Une nouvelle version = un nouveau fichier `<nom>.v<MAJOR.MINOR.PATCH>.yaml` ; ne jamais
  modifier une version déjà utilisée dans un backtest enregistré.
- Aucune règle n'est inventée par le logiciel : les points inconnus vont dans `open_questions`.
