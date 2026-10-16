# spice-screen grain mode vs the RRUFF Raman library

spice-screen 0.6.0.dev0 (sha256 435e387ee904), complete: True. Spectra read: 5787 (errors 0); covering 840 cm-1: 5785; 0.5.0 positive (840 cm-1 band, noise lag): 688; grain-mode positive: 168. Self-check: 0 spectra where the audit's rule and grain_check() disagree.

Thresholds (fixed before this audit): {"stretch_left": [780.0, 815.0], "stretch_right": [865.0, 900.0], "apex_search": [790.0, 890.0], "apex_range": [830.0, 850.0], "fingerprint": [200.0, 1100.0], "dominance_min": 0.5, "half_width": 60.0, "bend_left": [260.0, 315.0], "bend_right": [415.0, 470.0], "bend_range": [320.0, 410.0], "bend_ratio_min": 0.15, "bend_laser_min_nm": 700.0}

## Crocoite (PbCrO4)

| RRUFF ID | laser | 0.5.0 | grain | apex | dominance | bend ratio | failed | skipped |
|---|---|---|---|---|---|---|---|---|
| R040053 | 514 | positive | screen-positive | 839 | 1 | 0.0484 | - | - |
| R040053 | 532 | positive | screen-positive | 836 | 1 | 0.04 | - | - |
| R040053 | 785 | positive | screen-positive | 839 | 1 | 0.71 | - | - |
| R050044 | 514 | positive | screen-positive | 839 | 1 | 0.0593 | - | - |
| R050044 | 532 | positive | screen-positive | 835 | 1 | 0.0547 | - | - |
| R050044 | 785 | positive | screen-positive | 839 | 1 | 0.579 | - | - |
| R050044 | 514 | positive | screen-positive | 834 | 1 | 0.0913 | - | - |
| R160016 | 532 | positive | screen-positive | 839 | 1 | 0.126 | - | - |
| R160016 | 780 | positive | screen-positive | 839 | 1 | 0.821 | - | - |

## By class and laser

| class / laser | covered | 0.5.0 positive | grain positive | grain inconclusive by failed gates |
|---|---|---|---|---|
| crocoite/nir | 3 | 3 | 3 | - |
| crocoite/visible | 6 | 6 | 6 | - |
| filler/nir | 88 | 5 | 0 | dominance 4, apex+dominance 1 |
| filler/visible | 139 | 5 | 0 | apex+dominance 3, dominance 2 |
| lead_pigment/nir | 15 | 8 | 0 | dominance 6, apex+dominance 1, dominance+bend 1 |
| lead_pigment/visible | 23 | 13 | 0 | dominance 13 |
| other/nir | 2322 | 244 | 43 | dominance 95, apex+dominance 56, bend 31, apex 8, dominance+bend 7, apex+bend 4 |
| other/unknown | 14 | 1 | 1 | - |
| other/visible | 3112 | 387 | 105 | dominance 158, apex+dominance 105, apex 19 |
| other_cr/nir | 29 | 8 | 5 | dominance 1, apex 1, apex+dominance 1 |
| other_cr/visible | 34 | 8 | 5 | apex+dominance 2, apex 1 |

## Minerals without chromium that pass grain mode

| mineral | chemistry | laser | apex | dominance | bend ratio | skipped |
|---|---|---|---|---|---|---|
| Adamite | Zn_2_(AsO_4_)(OH) | 532 | 844 | 1 | 0.117 | - |
| Anorthoroselite | Ca_2_Co(AsO_4_)_2_·2H_2_O | 532 | 836 | 1 | 0.189 | - |
| Anorthoroselite | Ca_2_Co(AsO_4_)_2_·2H_2_O | 780 | 836 | 1 | 0.286 | - |
| Arhbarite | Cu_2_Mg(AsO_4_)(OH)_3_ | 532 | 845 | 1 | 0.101 | - |
| Arhbarite | Cu_2_Mg(AsO_4_)(OH)_3_ | 785 | 842 | 1 | 0.2 | - |
| Arseniopleite | NaCaMnMn_2_(AsO_4_)_3_ | 532 | 841 | 1 | 0.0767 | - |
| Arseniopleite | NaCaMnMn_2_(AsO_4_)_3_ | 532 | 841 | 1 | 0.0965 | - |
| Artesunate |  | 532 | 835 | 0.632 | 1.21 | - |
| Artesunate |  | 780 | 835 | 0.637 | 1.12 | - |
| Arthurite | CuFe^3+^_2_(AsO_4_)_2_(OH)_2_·4H_2_O | 532 | 845 | 1 | 0.0679 | - |
| Asisite | Pb_7_SiO_8_Cl_2_ | 780 | 842 | 0.518 | 0.378 | - |
| Atelestite | Bi_2_O(AsO_4_)(OH) | 532 | 834 | 1 | 0.181 | - |
| Atelestite | Bi_2_O(AsO_4_)(OH) | 780 | 834 | 0.733 | 0.206 | - |
| Bassetite | Fe^2+^(UO_2_)_2_(PO_4_)_2_(H_2_O)_10_ | 532 | 841 | 1 | 0.0226 | - |
| Belovite-(Ce) | NaCeSr_3_(PO_4_)_3_F | 532 | 848 | 1 | 0.256 | - |
| Benyacarite | (H_2_O)_2_Mn_2_(Ti_2_Fe^3+^)(PO_4_)_4_(OF)(H_2_O)_10_·4H_2_O | 532 | 834 | 1 | 0.123 | - |
| Benyacarite | (H_2_O)_2_Mn_2_(Ti_2_Fe^3+^)(PO_4_)_4_(OF)(H_2_O)_10_·4H_2_O | 780 | 833 | 1 | 0.212 | - |
| Beudantite | PbFe^3+^_3_(AsO_4_)(SO_4_)(OH)_6_ | 532 | 845 | 1 | 0.0937 | - |
| Beudantite | PbFe^3+^_3_(AsO_4_)(SO_4_)(OH)_6_ | 785 | 849 | 0.996 | 0.355 | - |
| Beudantite | PbFe^3+^_3_(AsO_4_)(SO_4_)(OH)_6_ | 532 | 845 | 0.811 | 0.125 | - |
| Beudantite | PbFe^3+^_3_(AsO_4_)(SO_4_)(OH)_6_ | 532 | 847 | 0.977 | 0.0277 | - |
| Beudantite | PbFe^3+^_3_(AsO_4_)(SO_4_)(OH)_6_ | 785 | 846 | 1 | 0.318 | - |
| Blatonite | (UO_2_)(CO_3_)·H_2_O | 532 | 837 | 1 | 0.0981 | - |
| Cabalzarite | CaMg_2_(AsO_4_)_2_·2H_2_O | 532 | 844 | 1 | 0.187 | - |
| Cahnite | Ca_2_B(AsO_4_)(OH)_4_ | 532 | 841 | 1 | 0.17 | - |
| Cahnite | Ca_2_B(AsO_4_)(OH)_4_ | 532 | 844 | 1 | 0.126 | - |
| Cahnite | Ca_2_B(AsO_4_)(OH)_4_ | 780 | 843 | 1 | 0.3 | - |
| Carminite | PbFe^3+^_2_(AsO_4_)_2_(OH)_2_ | 532 | 844 | 1 | 0.372 | - |
| Caryinite | NaCaCaMn_2_(AsO_4_)_3_ | 532 | 838 | 1 | 0.0945 | - |
| Caryinite | NaCaCaMn_2_(AsO_4_)_3_ | 780 | 840 | 1 | 0.387 | - |
| Cechite | PbFe^2+^(VO_4_)(OH) | 532 | 838 | 1 | 0.592 | - |
| Cechite | PbFe^2+^(VO_4_)(OH) | 532 | 837 | 1 | 0.707 | - |
| Chalcophyllite | Cu_18_Al_2_(AsO_4_)_4_(SO_4_)_3_(OH)_24_·36H_2_O | 532 | 838 | 1 | 0.294 | - |
| Chinchorroite | Na_2_Mg_5_(As_2_O_7_)_2_(AsO_3_OH)_2_(H_2_O)_10_ | 532 | 845 | 1 | 0.393 | - |
| Chondrodite | Mg_5_(SiO_4_)_2_F_2_ | 514 | 844 | 1 | 0.0112 | - |
| Chondrodite | Mg_5_(SiO_4_)_2_F_2_ | 532 | 845 | 1 | 0.0302 | - |
| Chondrodite | Mg_5_(SiO_4_)_2_F_2_ | 532 | 846 | 1 | 0.0825 | - |
| Clinoclase | Cu_3_(AsO_4_)(OH)_3_ | 532 | 834 | 1 | 0.0302 | - |
| Clinoclase | Cu_3_(AsO_4_)(OH)_3_ | 532 | 834 | 1 | 0.0324 | - |
| Clinohumite | Mg_9_(SiO_4_)_4_F_2_ | 532 | 833 | 1 | 0.0403 | - |
| Cobaltarthurite | CoFe^3+^_2_(AsO_4_)_2_(OH)_2_·4H_2_O | 532 | 837 | 1 | 0.176 | - |
| Cobaltarthurite | CoFe^3+^_2_(AsO_4_)_2_(OH)_2_·4H_2_O | 785 | 839 | 1 | 0.198 | - |
| Coconinoite | Fe^3+^_2_Al_2_(UO_2_)_2_(PO_4_)_4_(SO_4_)(OH)_2_·20H_2_O | 532 | 843 | 1 | 0.082 | - |
| Conichalcite | CaCu(AsO_4_)(OH) | 532 | 833 | 1 | 0.141 | - |
| Conichalcite | CaCu(AsO_4_)(OH) | 532 | 833 | 1 | 0.115 | - |
| Conichalcite | CaCu(AsO_4_)(OH) | 532 | 833 | 1 | 0.115 | - |
| Conichalcite | CaCu(AsO_4_)(OH) | 532 | 835 | 1 | 0.261 | - |
| Conichalcite | CaCu(AsO_4_)(OH) | 780 | 834 | 1 | 0.39 | - |
| Cuprozheshengite | Pb_4_CuZn_2_(AsO_4_)_2_(PO_4_)_2_(OH)_2_ | 532 | 840 | 0.636 | 1.27 | - |
| Dacostaite | K(Mg_2_Al)[Mg(H_2_O)_6_]_2_(AsO_4_)_2_F_6_·2H_2_O | 633 | 837 | 1 | 0.282 | - |
| Descloizite | PbZn(VO_4_)(OH) | 514 | 842 | 1 | 0.185 | - |
| Descloizite | PbZn(VO_4_)(OH) | 532 | 844 | 1 | 0.143 | - |
| Descloizite | PbZn(VO_4_)(OH) | 785 | 846 | 1 | 0.162 | - |
| Descloizite | PbZn(VO_4_)(OH) | 532 | 842 | 1 | 0.171 | - |
| Descloizite | PbZn(VO_4_)(OH) | 780 | 840 | 1 | 0.619 | - |
| Descloizite | PbZn(VO_4_)(OH) | 532 | 841 | 1 | 0.214 | - |
| Descloizite | PbZn(VO_4_)(OH) | 780 | 838 | 1 | 0.48 | - |
| Dewindtite | H_2_Pb_3_(UO_2_)_6_O_4_(PO_4_)_4_·12H_2_O | 780 | 833 | 1 | 0.508 | - |
| Diamond | C | 532 | 843 | 0.735 | 0.638 | - |
| Dmitryvarlamovite | Ti_2_(Fe^3+^Nb)O_8_ | 633 | 838 | 0.743 | 0.956 | - |
| Esperite | PbCa_2_(ZnSiO_4_)_3_ | 780 | 846 | 1 | 0.262 | - |
| Esperite | PbCa_2_(ZnSiO_4_)_3_ | 785 | 846 | 1 | 0.271 | - |
| Euchroite | Cu_2_(AsO_4_)(OH)·3H_2_O | 532 | 836 | 1 | 0.142 | - |
| Euxenite-(Y) | Y(NbTi)O_6_ | 532 | 844 | 1 | 0.808 | - |
| Fayalite | Fe^2+^_2_(SiO_4_) | 532 | 846 | 1 | 0.0274 | - |
| Fianelite | Mn^2+^_2_V_2_O_7_·2H_2_O | 532 | 844 | 1 | 0.046 | - |
| Fluorite | CaF_2_ | 514 | 842 | 1 | 0.504 | - |
| Gaitite | Ca_2_Zn(AsO_4_)_2_·2H_2_O | 532 | 837 | 1 | 0.125 | - |
| Gaitite | Ca_2_Zn(AsO_4_)_2_·2H_2_O | 780 | 837 | 1 | 0.283 | - |
| Gilmarite | Cu^2+^_3_(AsO_4_)(OH)_3_ | 532 | 840 | 1 | 0.156 | - |
| Hochleitnerite | [(H_2_O)K]Mn_2_(Ti_2_Fe^3+^)(PO_4_)_4_O_2_(H_2_O)_10_·4H_2_O | 532 | 835 | 0.991 | 0.124 | - |
| Humite | Mg_7_(SiO_4_)_3_F_2_ | 532 | 836 | 1 | 0.0211 | - |
| Humite | Mg_7_(SiO_4_)_3_F_2_ | 532 | 837 | 1 | 0.0227 | - |
| Jamesite | Pb_2_ZnFe^3+^_2_(Fe^3+^,Zn)_4_(AsO_4_)_4_(OH)_8_(OH,O)_2_ | 532 | 844 | 0.926 | 0.191 | - |
| Jamesite | Pb_2_ZnFe^3+^_2_(Fe^3+^,Zn)_4_(AsO_4_)_4_(OH)_8_(OH,O)_2_ | 780 | 845 | 1 | 0.291 | - |
| Johannite | Cu(UO_2_)_2_(SO_4_)_2_(OH)_2_·8H_2_O | 532 | 834 | 1 | 0.0147 | - |
| Juanitaite | (Cu,Ca,Fe)_10_Bi(AsO_4_)_4_(OH)_11_·2H_2_O | 532 | 840 | 1 | 0.403 | - |
| Kinoite | Ca_2_Cu_2_Si_3_O_10_·2H_2_O | 785 | 848 | 0.524 | 0.819 | - |
| Kurchatovite | CaMgB_2_O_5_ | 532 | 841 | 1 | 0.0284 | - |
| Lavenite | (Na,Ca)_4_(Mn^2+^,Fe^2+^)_2_(Zr,Ti,Nb)_2_(Si_2_O_7_)_2_(O,F)_4_ | 532 | 841 | 1 | 0.0846 | - |
| Lavenite | (Na,Ca)_4_(Mn^2+^,Fe^2+^)_2_(Zr,Ti,Nb)_2_(Si_2_O_7_)_2_(O,F)_4_ | 780 | 841 | 0.997 | 0.612 | - |
| Liskeardite | (Al,Fe)_32_(AsO_4_)_18_(OH)_42_(H_2_O)_22_·52H_2_O | 532 | 845 | 0.594 | 1.3 | - |
| Lobanovite | K_2_Na(Fe^2+^_4_Mg_2_Na)Ti_2_(Si_4_O_12_)_2_O_2_(OH)_4_ | 532 | 837 | 1 | 0.322 | - |
| Lobanovite | K_2_Na(Fe^2+^_4_Mg_2_Na)Ti_2_(Si_4_O_12_)_2_O_2_(OH)_4_ | 780 | 837 | 1 | 0.308 | - |
| Magnesiofluckite | CaMg(AsO_3_OH)_2_(H_2_O)_2_ | ? | 843 | 1 | 0.328 | - |
| Metakottigite | (Zn,Fe^3+^)_3_(AsO_4_)_2_·8(H_2_O,OH) | 532 | 845 | 1 | 0.609 | - |
| Namibite | Cu(BiO)_2_(VO_4_)(OH) | 532 | 840 | 1 | 0.11 | - |
| Namibite | Cu(BiO)_2_(VO_4_)(OH) | 785 | 846 | 1 | 0.208 | - |
| Namibite | Cu(BiO)_2_(VO_4_)(OH) | 532 | 846 | 1 | 0.132 | - |
| Namibite | Cu(BiO)_2_(VO_4_)(OH) | 780 | 844 | 1 | 0.204 | - |
| Nickeltalmessite | Ca_2_Ni(AsO_4_)_2_·2H_2_O | 532 | 835 | 1 | 0.287 | - |
| Nickeltalmessite | Ca_2_Ni(AsO_4_)_2_·2H_2_O | 780 | 835 | 1 | 0.384 | - |
| Paradamite | Zn_2_(AsO_4_)(OH) | 532 | 836 | 1 | 0.0952 | - |
| Ringwoodite | SiMg_2_O_4_ | 532 | 834 | 0.978 | 0.0491 | - |
| Riosecoite | Ca_2_Mg(AsO_3_OH)_3_(H_2_O)_2_ | 532 | 835 | 0.65 | 0.303 | - |
| Rooseveltite | Bi(AsO_4_) | 532 | 839 | 1 | 0.259 | - |
| Roselite | Ca_2_Co(AsO_4_)_2_·2H_2_O | 532 | 842 | 1 | 0.358 | - |
| Rruffite | Ca_2_Cu(AsO_4_)_2_·2H_2_O | 532 | 839 | 1 | 0.241 | - |
| Rruffite | Ca_2_Cu(AsO_4_)_2_·2H_2_O | 780 | 838 | 1 | 0.211 | - |
| Rruffite | Ca_2_Cu(AsO_4_)_2_·2H_2_O | 532 | 839 | 1 | 0.229 | - |
| Rruffite | Ca_2_Cu(AsO_4_)_2_·2H_2_O | 780 | 837 | 1 | 0.411 | - |
| Saleeite | Mg(UO_2_)_2_(PO_4_)_2_(H_2_O)_10_ | 532 | 836 | 1 | 0.0615 | - |
| Sarkinite | Mn^2+^_2_(AsO_4_)(OH) | 532 | 835 | 1 | 0.0454 | - |
| Schmitterite | (UO_2_)(Te^4+^O_3_) | 532 | 833 | 0.539 | 0.438 | - |
| Schoepite | (UO_2_)_4_O(OH)_6_(H_2_O)_6_ | 780 | 841 | 1 | 0.164 | - |
| Sofiite | Zn_2_(Se^4+^O_3_)Cl_2_ | 532 | 847 | 1 | 0.0382 | - |
| Sperlingite | (H_2_O)K(Mn^2+^Fe^3+^)(Al_2_Ti)(PO_4_)_4_[O(OH)][(H_2_O)_9_(OH)]·4H_2_O | 532 | 839 | 1 | 0.202 | - |
| Stenhuggarite | CaFe^3+^Sb^3+^As^3+^_2_O_7_ | 532 | 836 | 0.87 | 0.298 | - |
| Strashimirite | Cu_4_(AsO_4_)_2_(OH)_2_·2.5H_2_O | 532 | 846 | 1 | 0.0238 | - |
| Sulfadoxine |  | 532 | 835 | 0.876 | 0.11 | - |
| Sulfadoxine |  | 780 | 835 | 0.582 | 0.198 | - |
| Symplesite | Fe^2+^_3_(AsO_4_)_2_·8H_2_O | 532 | 846 | 0.511 | 0.855 | - |
| Szaibelyite | MgBO_2_(OH) | 532 | 834 | 1 | 0.256 | - |
| Szaibelyite | MgBO_2_(OH) | 780 | 834 | 1 | 0.298 | - |
| Talmessite | Ca_2_Mg(AsO_4_)_2_·2H_2_O | 532 | 838 | 1 | 0.202 | - |
| Talmessite | Ca_2_Mg(AsO_4_)_2_·2H_2_O | 780 | 836 | 1 | 0.458 | - |
| Talmessite | Ca_2_Mg(AsO_4_)_2_·2H_2_O | 532 | 835 | 1 | 0.235 | - |
| Talmessite | Ca_2_Mg(AsO_4_)_2_·2H_2_O | 532 | 837 | 1 | 0.353 | - |
| Talmessite | Ca_2_Mg(AsO_4_)_2_·2H_2_O | 780 | 837 | 1 | 0.385 | - |
| Tangeite | CaCu(VO_4_)(OH) | 532 | 843 | 1 | 0.219 | - |
| Tangeite | CaCu(VO_4_)(OH) | 785 | 843 | 1 | 0.342 | - |
| Tephroite | Mn^2+^_2_(SiO_4_) | 532 | 839 | 1 | 0.0686 | - |
| Tephroite | Mn^2+^_2_(SiO_4_) | 532 | 841 | 1 | 0.0583 | - |
| Tephroite | Mn^2+^_2_(SiO_4_) | 532 | 840 | 1 | 0.113 | - |
| Tephroite | Mn^2+^_2_(SiO_4_) | 780 | 839 | 0.998 | 0.208 | - |
| Ternesite | Ca_5_(SiO_4_)_2_(SO_4_) | 532 | 833 | 0.626 | 0.163 | - |
| Ternesite | Ca_5_(SiO_4_)_2_(SO_4_) | 780 | 833 | 0.539 | 0.228 | - |
| Theisite | Cu_5_Zn_5_(AsO_4_)_2_(OH)_14_ | 532 | 835 | 1 | 0.128 | - |
| Thometzekite | PbCu^2+^_2_(AsO_4_)_2_·2H_2_O | 532 | 836 | 1 | 0.394 | - |
| Thometzekite | PbCu^2+^_2_(AsO_4_)_2_·2H_2_O | 780 | 833 | 1 | 0.422 | - |
| Thometzekite | PbCu^2+^_2_(AsO_4_)_2_·2H_2_O | 532 | 837 | 1 | 0.117 | - |
| Tsumcorite | PbZn_2_(AsO_4_)_2_·2H_2_O | 532 | 834 | 1 | 0.141 | - |
| Tsumcorite | PbZn_2_(AsO_4_)_2_·2H_2_O | 780 | 834 | 1 | 0.204 | - |
| Tyrolite | Ca_2_Cu_9_(AsO_4_)_4_(CO_3_)(OH)_8_·11H_2_O | 532 | 847 | 1 | 0.192 | - |
| Tyrolite | Ca_2_Cu_9_(AsO_4_)_4_(CO_3_)(OH)_8_·11H_2_O | 532 | 845 | 1 | 0.321 | - |
| Uranoclite | (UO_2_)_2_(OH)_2_Cl_2_(H_2_O)_4_ | 532 | 844 | 1 | 0.0842 | - |
| Uroxite | [(UO_2_)_2_(C_2_O_4_)(OH)_2_(H_2_O)_2_]·H_2_O | 532 | 842 | 1 | 0.0447 | - |
| Vladimirite | Ca_4_(AsO_4_)_2_(AsO_3_OH)·4H_2_O | 532 | 844 | 1 | 0.152 | - |
| Vladimirite | Ca_4_(AsO_4_)_2_(AsO_3_OH)·4H_2_O | 780 | 843 | 1 | 0.253 | - |
| Vladimirite | Ca_4_(AsO_4_)_2_(AsO_3_OH)·4H_2_O | 532 | 844 | 1 | 0.133 | - |
| Vladimirite | Ca_4_(AsO_4_)_2_(AsO_3_OH)·4H_2_O | 780 | 843 | 1 | 0.178 | - |
| Walpurgite | Bi_4_O_4_(UO_2_)(AsO_4_)_2_·2H_2_O | 532 | 836 | 0.757 | 0.104 | - |
| Walpurgite | Bi_4_O_4_(UO_2_)(AsO_4_)_2_·2H_2_O | 780 | 835 | 0.565 | 0.477 | - |
| Wendwilsonite | Ca_2_Mg(AsO_4_)_2_·2H_2_O | 532 | 840 | 1 | 0.232 | - |
| Wendwilsonite | Ca_2_Mg(AsO_4_)_2_·2H_2_O | 780 | 840 | 1 | 0.238 | - |
| Wendwilsonite | Ca_2_Mg(AsO_4_)_2_·2H_2_O | 532 | 840 | 1 | 0.148 | - |
| Wendwilsonite | Ca_2_Mg(AsO_4_)_2_·2H_2_O | 780 | 840 | 1 | 0.31 | - |
| Wendwilsonite | Ca_2_Mg(AsO_4_)_2_·2H_2_O | 532 | 840 | 1 | 0.148 | - |
| Wiserite | Mn^2+^_14_(B_2_O_5_)_4_(OH)_8_·(Si,Mg)(O,OH)_4_Cl | 532 | 838 | 1 | 0.0352 | - |

## Other chromium-bearing minerals that pass

Edoylerite (532), Georgerobinsonite (532), Georgerobinsonite (780), Hemihedrite (532), Hemihedrite (780), Iranite (780), Petterdite (532), Petterdite (780), Phoenicochroite (532)

## Nearby thresholds

| rule | published | crocoite NIR | crocoite visible | no-Cr NIR | no-Cr visible | no-Cr laser unknown | mix_f=0 | mix_f=0.1 | mix_f=0.3 | mix_f=0.5 | mix_f=0.7 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| apex+dom>=0.3+bend>=0.1 |  | 3 | 6 | 56 | 112 | 1 | 0 | 0 | 0.948 | 0.954 | 0.994 |
| apex+dom>=0.3+bend>=0.15 |  | 3 | 6 | 48 | 112 | 1 | 0 | 0 | 0.948 | 0.954 | 0.994 |
| apex+dom>=0.3+bend>=0.3 |  | 3 | 6 | 26 | 112 | 1 | 0 | 0 | 0.948 | 0.954 | 0.994 |
| apex+dom>=0.5+bend>=0.1 |  | 3 | 6 | 51 | 105 | 1 | 0 | 0 | 0.085 | 0.954 | 0.994 |
| apex+dom>=0.5+bend>=0.15 | yes | 3 | 6 | 43 | 105 | 1 | 0 | 0 | 0.085 | 0.954 | 0.994 |
| apex+dom>=0.5+bend>=0.3 |  | 3 | 6 | 21 | 105 | 1 | 0 | 0 | 0.085 | 0.954 | 0.994 |
| apex+dom>=0.7+bend>=0.1 |  | 3 | 6 | 45 | 98 | 1 | 0 | 0 | 0.0392 | 0.954 | 0.994 |
| apex+dom>=0.7+bend>=0.15 |  | 3 | 6 | 37 | 98 | 1 | 0 | 0 | 0.0392 | 0.954 | 0.994 |
| apex+dom>=0.7+bend>=0.3 |  | 3 | 6 | 17 | 98 | 1 | 0 | 0 | 0.0392 | 0.954 | 0.994 |
| dom>=0.3+bend>=0.1 |  | 3 | 6 | 68 | 137 | 1 | 0 | 0 | 0.948 | 0.954 | 0.994 |
| dom>=0.3+bend>=0.15 |  | 3 | 6 | 57 | 137 | 1 | 0 | 0 | 0.948 | 0.954 | 0.994 |
| dom>=0.3+bend>=0.3 |  | 3 | 6 | 31 | 137 | 1 | 0 | 0 | 0.948 | 0.954 | 0.994 |
| dom>=0.5+bend>=0.1 |  | 3 | 6 | 62 | 124 | 1 | 0 | 0 | 0.085 | 0.954 | 0.994 |
| dom>=0.5+bend>=0.15 |  | 3 | 6 | 51 | 124 | 1 | 0 | 0 | 0.085 | 0.954 | 0.994 |
| dom>=0.5+bend>=0.3 |  | 3 | 6 | 26 | 124 | 1 | 0 | 0 | 0.085 | 0.954 | 0.994 |
| dom>=0.7+bend>=0.1 |  | 3 | 6 | 50 | 109 | 1 | 0 | 0 | 0.0392 | 0.954 | 0.994 |
| dom>=0.7+bend>=0.15 |  | 3 | 6 | 40 | 109 | 1 | 0 | 0 | 0.0392 | 0.954 | 0.994 |
| dom>=0.7+bend>=0.3 |  | 3 | 6 | 18 | 109 | 1 | 0 | 0 | 0.0392 | 0.954 | 0.994 |

## Crocoite in filler (same laser class)

765 mixtures from 9 crocoite and 34 filler spectra (errors 0). f is a peak-height fraction, not a mass fraction; f=0 is the filler alone (false flags).

| laser, fraction | n | 0.5.0 flags | grain flags |
|---|---|---|---|
| nir f=0 | 51 | 0 | 0 |
| nir f=0.1 | 51 | 1 | 0 |
| nir f=0.3 | 51 | 1 | 0.118 |
| nir f=0.5 | 51 | 1 | 1 |
| nir f=0.7 | 51 | 1 | 1 |
| visible f=0 | 102 | 0.0098 | 0 |
| visible f=0.1 | 102 | 0.873 | 0 |
| visible f=0.3 | 102 | 0.922 | 0.0686 |
| visible f=0.5 | 102 | 0.931 | 0.931 |
| visible f=0.7 | 102 | 0.99 | 0.99 |

RRUFF data: Lafuente et al. (2015), The power of databases: the RRUFF project. Spectra are not redistributed here.
