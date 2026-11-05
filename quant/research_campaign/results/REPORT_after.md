# Campagne — phase « after »

Code évalué : `/Users/eulogemabiala/Desktop/Developer/traider pro/quant/research_campaign/frozen/v0.4.1/src` · version 0.4.1 · `research_code_hash = 5e6a8f926021b343` · arbre source SHA-256 `780f86756a937024…` · numpy 2.5.4 · pandas 2.3.3

Référence 5 % ; dépassement significatif si p < 0,05/15 = 0.00333 (binomial exact unilatéral) ; intervalles de Clopper–Pearson à 95 %.

| Scénario | Famille | N | EDGE | Taux | IC 95 % | p (H0 ≤ 5 %) | Jugement | Effet vrai (R/signal, IC 95 %) | Autres verdicts | Erreurs |
|---|---|---:|---:|---:|---|---:|---|---|---|---:|
| C0_codex_indep | codex | 1000 | 54 | 5,4 % | [4,1 % ; 7,0 %] | 0.3 | compatible avec ≤ 5 % | — | NEGATIVE:7, NO_EDGE:939 | 0 |
| C1_codex_cluster100 | codex | 1000 | 0 | 0,0 % | [0,0 % ; 0,4 %] | 1 | compatible avec ≤ 5 % | — | INSUFFICIENT:1000 | 0 |
| E1_e2e_baseline_stochvol | e2e_null | 800 | 29 | 3,6 % | [2,4 % ; 5,2 %] | 0.97 | compatible avec ≤ 5 % | — | NEGATIVE:8, NO_EDGE:763 | 0 |
| N10_corr_2h | null | 800 | 294 | 36,8 % | [33,4 % ; 40,2 %] | 1.6e-167 | DÉPASSEMENT SIGNIFICATIF de 5 % | -0.0000 [-0.0023 ; +0.0022] | NO_EDGE:506 | 0 |
| N11_corr_1d | null | 796 | 666 | 83,7 % | [80,9 % ; 86,2 %] | 0 | DÉPASSEMENT SIGNIFICATIF de 5 % | -0.0014 [-0.0043 ; +0.0015] | NEGATIVE:1, NO_EDGE:129 | 4 |
| N1_rand_sparse | null | 800 | 47 | 5,9 % | [4,3 % ; 7,7 %] | 0.15 | compatible avec ≤ 5 % | +0.0019 [-0.0036 ; +0.0073] | INSUFFICIENT:41, NEGATIVE:11, NO_EDGE:701 | 0 |
| N2_rand_mid | null | 800 | 39 | 4,9 % | [3,5 % ; 6,6 %] | 0.59 | compatible avec ≤ 5 % | +0.0026 [+0.0003 ; +0.0049] | NEGATIVE:6, NO_EDGE:755 | 0 |
| N3_rand_dense | null | 800 | 41 | 5,1 % | [3,7 % ; 6,9 %] | 0.46 | compatible avec ≤ 5 % | +0.0003 [-0.0009 ; +0.0015] | NEGATIVE:9, NO_EDGE:750 | 0 |
| N4_burst10 | null | 800 | 0 | 0,0 % | [0,0 % ; 0,5 %] | 1 | compatible avec ≤ 5 % | -0.0006 [-0.0057 ; +0.0046] | INSUFFICIENT:800 | 0 |
| N5_burst60 | null | 800 | 0 | 0,0 % | [0,0 % ; 0,5 %] | 1 | compatible avec ≤ 5 % | +0.0040 [-0.0013 ; +0.0093] | INSUFFICIENT:800 | 0 |
| N6_rule_momentum | null | 800 | 38 | 4,8 % | [3,4 % ; 6,5 %] | 0.65 | compatible avec ≤ 5 % | -0.0008 [-0.0027 ; +0.0011] | NEGATIVE:7, NO_EDGE:755 | 0 |
| N7_volswitch | null | 800 | 44 | 5,5 % | [4,0 % ; 7,3 %] | 0.28 | compatible avec ≤ 5 % | -0.0006 [-0.0030 ; +0.0017] | NEGATIVE:7, NO_EDGE:749 | 0 |
| N8_stochvol | null | 800 | 34 | 4,2 % | [3,0 % ; 5,9 %] | 0.86 | compatible avec ≤ 5 % | -0.0018 [-0.0042 ; +0.0005] | NEGATIVE:13, NO_EDGE:753 | 0 |
| N9_stochvol_burst30 | null | 800 | 0 | 0,0 % | [0,0 % ; 0,5 %] | 1 | compatible avec ≤ 5 % | +0.0025 [-0.0022 ; +0.0072] | INSUFFICIENT:800 | 0 |
| P1_edge_005 | power | 300 | 119 | 39,7 % | [34,1 % ; 45,4 %] | 2.3e-73 | (puissance) | +0.0480 [+0.0450 ; +0.0510] | NO_EDGE:181 | 0 |
| P2_edge_010 | power | 300 | 217 | 72,3 % | [66,9 % ; 77,3 %] | 2.4e-209 | (puissance) | +0.1043 [+0.1010 ; +0.1076] | NO_EDGE:83 | 0 |
| P3_edge_020 | power | 300 | 287 | 95,7 % | [92,7 % ; 97,7 %] | 0 | (puissance) | +0.2012 [+0.1979 ; +0.2045] | NO_EDGE:13 | 0 |
| P4_edge_010_burst20 | power | 300 | 0 | 0,0 % | [0,0 % ; 1,2 %] | 1 | (puissance) | +0.1052 [+0.0979 ; +0.1125] | INSUFFICIENT:300 | 0 |
| P5_edge_020_stochvol | power | 300 | 288 | 96,0 % | [93,1 % ; 97,9 %] | 0 | (puissance) | +0.2016 [+0.1980 ; +0.2052] | NO_EDGE:12 | 0 |
| P6_edge_010_sparse | power | 300 | 84 | 28,0 % | [23,0 % ; 33,4 %] | 8.5e-39 | (puissance) | +0.1079 [+0.1003 ; +0.1155] | INSUFFICIENT:8, NO_EDGE:208 | 0 |
| P7_conditional_hours | power | 300 | 242 | 80,7 % | [75,7 % ; 85,0 %] | 4e-254 | (puissance) | +0.0978 [+0.0944 ; +0.1011] | NO_EDGE:58 | 0 |
| S1_search_10_variants · règle α de l’application | essais multiples | 150 | 7 | 4,7 % | [1,9 % ; 9,4 %] | 0.63 | compatible avec ≤ 5 % | — | — | 0 |
| S1_search_10_variants · sans correction | essais multiples | 150 | 18 | 12,0 % | [7,3 % ; 18,3 %] | 0.00054 | (référence) | — | — | 0 |

**Défaut établi (au moins un dépassement significatif) : OUI.** Puissance P3 (≈ +0,20 R) : 95,7 %.
Lecture écart 4b (13 nuls valides, sans N10_corr_2h, N11_corr_1d) : dépassement NON.

Effet filtré hors échantillon (ce que juge `EDGE`), moyenne des réplications [IC 95 %] :

- C0_codex_indep : +0.0006 R [-0.0033 ; +0.0044] (n = 1000)
- C1_codex_cluster100 : -0.0445 R [-0.0687 ; -0.0203] (n = 997)
- E1_e2e_baseline_stochvol : +0.0056 R [+0.0011 ; +0.0101] (n = 800)
- N10_corr_2h : +0.0947 R [+0.0888 ; +0.1007] (n = 800)
- N11_corr_1d : +0.2127 R [+0.2063 ; +0.2191] (n = 796)
- N1_rand_sparse : +0.0077 R [-0.0009 ; +0.0164] (n = 800)
- N2_rand_mid : +0.0061 R [+0.0013 ; +0.0109] (n = 800)
- N3_rand_dense : +0.0021 R [-0.0005 ; +0.0047] (n = 800)
- N4_burst10 : +0.0041 R [-0.0057 ; +0.0140] (n = 800)
- N5_burst60 : +0.0044 R [-0.0059 ; +0.0146] (n = 800)
- N6_rule_momentum : +0.0010 R [-0.0026 ; +0.0045] (n = 800)
- N7_volswitch : +0.0048 R [-0.0001 ; +0.0098] (n = 800)
- N8_stochvol : -0.0025 R [-0.0073 ; +0.0024] (n = 800)
- N9_stochvol_burst30 : +0.0055 R [-0.0039 ; +0.0149] (n = 800)
- P1_edge_005 : +0.0932 R [+0.0851 ; +0.1013] (n = 300)
- P2_edge_010 : +0.1374 R [+0.1300 ; +0.1449] (n = 300)
- P3_edge_020 : +0.2083 R [+0.2015 ; +0.2152] (n = 300)
- P4_edge_010_burst20 : +0.1294 R [+0.1138 ; +0.1450] (n = 300)
- P5_edge_020_stochvol : +0.2385 R [+0.2305 ; +0.2466] (n = 300)
- P6_edge_010_sparse : +0.1177 R [+0.1059 ; +0.1296] (n = 300)
- P7_conditional_hours : +0.1792 R [+0.1701 ; +0.1883] (n = 300)
