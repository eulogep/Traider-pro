# Campagne — phase « before »

Code évalué : `/Users/eulogemabiala/Desktop/Developer/traider pro/quant/research_campaign/frozen/v0.4.0/src` · version 0.4.0 · `research_code_hash = f9055832e70d0f32` · arbre source SHA-256 `c3ed16841e6ab714…` · numpy 2.5.4 · pandas 2.3.3

Référence 5 % ; dépassement significatif si p < 0,05/15 = 0.00333 (binomial exact unilatéral) ; intervalles de Clopper–Pearson à 95 %.

| Scénario | Famille | N | EDGE | Taux | IC 95 % | p (H0 ≤ 5 %) | Jugement | Effet vrai (R/signal, IC 95 %) | Autres verdicts | Erreurs |
|---|---|---:|---:|---:|---|---:|---|---|---|---:|
| C0_codex_indep | codex | 1000 | 34 | 3,4 % | [2,4 % ; 4,7 %] | 0.99 | compatible avec ≤ 5 % | — | NEGATIVE:10, NO_EDGE:956 | 0 |
| C1_codex_cluster100 | codex | 1000 | 176 | 17,6 % | [15,3 % ; 20,1 %] | 2.3e-47 | DÉPASSEMENT SIGNIFICATIF de 5 % | — | INSUFFICIENT:18, NEGATIVE:151, NO_EDGE:655 | 0 |
| E1_e2e_baseline_stochvol | e2e_null | 800 | 24 | 3,0 % | [1,9 % ; 4,4 %] | 1 | compatible avec ≤ 5 % | — | NEGATIVE:15, NO_EDGE:761 | 0 |
| N10_corr_2h | null | 800 | 212 | 26,5 % | [23,5 % ; 29,7 %] | 3.6e-90 | DÉPASSEMENT SIGNIFICATIF de 5 % | -0.0000 [-0.0023 ; +0.0022] | NO_EDGE:588 | 0 |
| N11_corr_1d | null | 796 | 577 | 72,5 % | [69,2 % ; 75,6 %] | 0 | DÉPASSEMENT SIGNIFICATIF de 5 % | -0.0014 [-0.0043 ; +0.0015] | NEGATIVE:1, NO_EDGE:218 | 4 |
| N1_rand_sparse | null | 800 | 33 | 4,1 % | [2,9 % ; 5,7 %] | 0.89 | compatible avec ≤ 5 % | +0.0019 [-0.0036 ; +0.0073] | INSUFFICIENT:12, NEGATIVE:16, NO_EDGE:739 | 0 |
| N2_rand_mid | null | 800 | 19 | 2,4 % | [1,4 % ; 3,7 %] | 1 | compatible avec ≤ 5 % | +0.0026 [+0.0003 ; +0.0049] | NEGATIVE:9, NO_EDGE:772 | 0 |
| N3_rand_dense | null | 800 | 18 | 2,2 % | [1,3 % ; 3,5 %] | 1 | compatible avec ≤ 5 % | +0.0003 [-0.0009 ; +0.0015] | NEGATIVE:10, NO_EDGE:772 | 0 |
| N4_burst10 | null | 800 | 24 | 3,0 % | [1,9 % ; 4,4 %] | 1 | compatible avec ≤ 5 % | -0.0006 [-0.0057 ; +0.0046] | NEGATIVE:9, NO_EDGE:767 | 0 |
| N5_burst60 | null | 800 | 30 | 3,8 % | [2,5 % ; 5,3 %] | 0.96 | compatible avec ≤ 5 % | +0.0040 [-0.0013 ; +0.0093] | NEGATIVE:16, NO_EDGE:754 | 0 |
| N6_rule_momentum | null | 800 | 26 | 3,2 % | [2,1 % ; 4,7 %] | 0.99 | compatible avec ≤ 5 % | -0.0008 [-0.0027 ; +0.0011] | NEGATIVE:8, NO_EDGE:766 | 0 |
| N7_volswitch | null | 800 | 22 | 2,8 % | [1,7 % ; 4,1 %] | 1 | compatible avec ≤ 5 % | -0.0006 [-0.0030 ; +0.0017] | NEGATIVE:10, NO_EDGE:768 | 0 |
| N8_stochvol | null | 800 | 19 | 2,4 % | [1,4 % ; 3,7 %] | 1 | compatible avec ≤ 5 % | -0.0018 [-0.0042 ; +0.0005] | NEGATIVE:15, NO_EDGE:766 | 0 |
| N9_stochvol_burst30 | null | 800 | 40 | 5,0 % | [3,6 % ; 6,7 %] | 0.52 | compatible avec ≤ 5 % | +0.0025 [-0.0022 ; +0.0072] | NEGATIVE:18, NO_EDGE:742 | 0 |
| P1_edge_005 | power | 300 | 91 | 30,3 % | [25,2 % ; 35,9 %] | 4.6e-45 | (puissance) | +0.0480 [+0.0450 ; +0.0510] | NO_EDGE:209 | 0 |
| P2_edge_010 | power | 300 | 188 | 62,7 % | [56,9 % ; 68,2 %] | 4.8e-163 | (puissance) | +0.1043 [+0.1010 ; +0.1076] | NO_EDGE:112 | 0 |
| P3_edge_020 | power | 300 | 280 | 93,3 % | [89,9 % ; 95,9 %] | 0 | (puissance) | +0.2012 [+0.1979 ; +0.2045] | NO_EDGE:20 | 0 |
| P4_edge_010_burst20 | power | 300 | 69 | 23,0 % | [18,4 % ; 28,2 %] | 1.5e-26 | (puissance) | +0.1052 [+0.0979 ; +0.1125] | INSUFFICIENT:1, NO_EDGE:230 | 0 |
| P5_edge_020_stochvol | power | 300 | 279 | 93,0 % | [89,5 % ; 95,6 %] | 0 | (puissance) | +0.2016 [+0.1980 ; +0.2052] | NO_EDGE:21 | 0 |
| P6_edge_010_sparse | power | 300 | 65 | 21,7 % | [17,1 % ; 26,8 %] | 1.4e-23 | (puissance) | +0.1079 [+0.1003 ; +0.1155] | INSUFFICIENT:5, NO_EDGE:230 | 0 |
| P7_conditional_hours | power | 300 | 225 | 75,0 % | [69,7 % ; 79,8 %] | 3.9e-223 | (puissance) | +0.0978 [+0.0944 ; +0.1011] | NO_EDGE:75 | 0 |
| S1_search_10_variants · règle α de l’application | essais multiples | 150 | 11 | 7,3 % | [3,7 % ; 12,7 %] | 0.13 | compatible avec ≤ 5 % | — | — | 0 |
| S1_search_10_variants · sans correction | essais multiples | 150 | 20 | 13,3 % | [8,3 % ; 19,8 %] | 6.5e-05 | (référence) | — | — | 0 |

**Défaut établi (au moins un dépassement significatif) : OUI.** Puissance P3 (≈ +0,20 R) : 93,3 %.
Lecture écart 4b (13 nuls valides, sans N10_corr_2h, N11_corr_1d) : dépassement OUI.

Effet filtré hors échantillon (ce que juge `EDGE`), moyenne des réplications [IC 95 %] :

- C0_codex_indep : +0.0006 R [-0.0033 ; +0.0044] (n = 1000)
- C1_codex_cluster100 : -0.0445 R [-0.0687 ; -0.0203] (n = 997)
- E1_e2e_baseline_stochvol : +0.0058 R [+0.0012 ; +0.0103] (n = 800)
- N10_corr_2h : +0.0946 R [+0.0887 ; +0.1005] (n = 800)
- N11_corr_1d : +0.2126 R [+0.2062 ; +0.2190] (n = 796)
- N1_rand_sparse : +0.0078 R [-0.0009 ; +0.0164] (n = 800)
- N2_rand_mid : +0.0063 R [+0.0015 ; +0.0111] (n = 800)
- N3_rand_dense : +0.0019 R [-0.0007 ; +0.0045] (n = 800)
- N4_burst10 : +0.0040 R [-0.0059 ; +0.0138] (n = 800)
- N5_burst60 : +0.0042 R [-0.0061 ; +0.0144] (n = 800)
- N6_rule_momentum : +0.0010 R [-0.0025 ; +0.0045] (n = 800)
- N7_volswitch : +0.0048 R [-0.0002 ; +0.0097] (n = 800)
- N8_stochvol : -0.0023 R [-0.0071 ; +0.0025] (n = 800)
- N9_stochvol_burst30 : +0.0052 R [-0.0042 ; +0.0146] (n = 800)
- P1_edge_005 : +0.0934 R [+0.0853 ; +0.1015] (n = 300)
- P2_edge_010 : +0.1373 R [+0.1298 ; +0.1448] (n = 300)
- P3_edge_020 : +0.2081 R [+0.2012 ; +0.2150] (n = 300)
- P4_edge_010_burst20 : +0.1272 R [+0.1115 ; +0.1429] (n = 300)
- P5_edge_020_stochvol : +0.2384 R [+0.2304 ; +0.2465] (n = 300)
- P6_edge_010_sparse : +0.1176 R [+0.1057 ; +0.1294] (n = 300)
- P7_conditional_hours : +0.1790 R [+0.1699 ; +0.1881] (n = 300)
