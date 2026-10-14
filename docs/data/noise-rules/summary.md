# spice-screen lead chromate rules vs the RRUFF Raman library

Candidate spice-screen 0.5.0.dev0; archives excellent_unoriented.zip; complete: True; 5787 spectra read, 5785 covering 840 cm-1, 0 errors.
Cross-check of rule maths against screen_entry(): 192 of 212 sampled spectra agree; mismatches: Axinite-(Fe)__R040074__Raman__785______Raman_Data_Processed__4d938af0ab83eb6a2a746a5ba74e.txt mismatch:diff, Biphosphammite__R070206__Raman__532______Raman_Data_Processed__b298f6e925dd73ba6a096149731a.txt mismatch:diff, Calcioferrite__R120092__Raman__532______Raman_Data_Processed__9131a2d315773e912fc3164dc269.txt mismatch:diff, Fluorapatite__R050122__Raman__780______Raman_Data_Processed__4de1876ee14e5413b35b81e1fe95.txt mismatch:diff+lag, Gunningite__R070571__Raman__532______Raman_Data_Processed__dfc5f2aa1d5be78e0e6ba0240c76.txt mismatch:diff, Inesite__R090030__Raman__780______Raman_Data_Processed__d78e3fa670a0d4ef746b7f966fbd.txt mismatch:diff+lag, Lenoblite__R060761__Raman__785______Raman_Data_Processed__13771acc44e346a7dae6abe08760.txt mismatch:diff, Marialite__R040043__Raman__785______Raman_Data_Processed__6aefdcb3394f36e296665dedad7c.txt mismatch:diff, Natrodufrenite__R070599__Raman__780______Raman_Data_Processed__f796de2857e758d863d7a00a23d4.txt mismatch:diff, Nevadaite__R060775__Raman__532______Raman_Data_Processed__f453f375bde467dae14368bfc8c9.txt mismatch:diff+lag.
0.4.0 rule (diff, SNR 5, no gate) here: crocoite 9/9, non-Cr positives 1512 (0.4.0 audit: 9/9, 1935).

## Rules that keep all crocoite spectra (best first)

| noise | SNR | rel. gate | crocoite | non-Cr flagged | rate | of them Pb | fillers | f=0 | f=0.003 | f=0.01 | f=0.03 | f=0.1 | f=0.3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| lag | 10 | 0.1 | 9/9 | 222 | 0.0389 | 32 | 0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.6848 | 0.9093 |
| lag | 8 | 0.1 | 9/9 | 244 | 0.0427 | 33 | 0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.7551 | 0.9592 |
| lag | 10 | 0.05 | 9/9 | 254 | 0.0445 | 35 | 1 | 0.0 | 0.0 | 0.0 | 0.0 | 0.7664 | 0.9093 |
| lag | 10 | 0.03 | 9/9 | 269 | 0.0471 | 38 | 1 | 0.0 | 0.0 | 0.0 | 0.0408 | 0.7664 | 0.9093 |
| lag | 5 | 0.1 | 9/9 | 279 | 0.0488 | 37 | 0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.8345 | 0.9796 |
| lag | 8 | 0.05 | 9/9 | 281 | 0.0492 | 36 | 1 | 0.0 | 0.0 | 0.0 | 0.0 | 0.8481 | 0.9592 |
| diff | 20 | 0.1 | 9/9 | 291 | 0.0509 | 36 | 0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.5896 | 0.9569 |
| lag | 8 | 0.03 | 9/9 | 308 | 0.0539 | 39 | 2 | 0.0 | 0.0 | 0.0 | 0.2358 | 0.8481 | 0.9592 |
| lag | 10 | 0.01 | 9/9 | 322 | 0.0564 | 56 | 1 | 0.0 | 0.0 | 0.0 | 0.0454 | 0.7664 | 0.9093 |
| diff | 10 | 0.1 | 9/9 | 328 | 0.0574 | 40 | 1 | 0.0 | 0.0 | 0.0 | 0.0 | 0.8209 | 0.9615 |
| lag | 5 | 0.05 | 9/9 | 334 | 0.0585 | 41 | 2 | 0.0045 | 0.0068 | 0.0159 | 0.0272 | 0.9297 | 0.9796 |
| diff | 8 | 0.1 | 9/9 | 335 | 0.0586 | 40 | 1 | 0.0 | 0.0 | 0.0 | 0.0159 | 0.8322 | 0.9615 |

f is the crocoite share of peak height in a crocoite + filler mixture with white noise (0.003 of the strongest band); f=0 is the filler alone. 441 mixtures per fraction.

## Every rule without a gate

| noise | SNR | crocoite | other Cr | non-Cr flagged | rate | fillers flagged | top groups |
|---|---|---|---|---|---|---|---|
| diff | 5 | 9/9 | 27/63 | 1512 | 0.2647 | Albite; Anatase; Aragonite; Baryte; Calcite; Dolomite; Fluorapatite; Goethite; Gypsum; Hematite; Magnetite; Microcline; Muscovite; Orthoclase; Talc | silicate 419; other 264; phosphorus-bearing 225; arsenic-bearing 192; sulfur-bearing 189 |
| diff | 8 | 9/9 | 24/63 | 1003 | 0.1756 | Albite; Baryte; Calcite; Fluorapatite; Goethite; Gypsum; Hematite; Magnetite; Muscovite; Orthoclase | silicate 296; phosphorus-bearing 161; other 160; arsenic-bearing 149; carbon-bearing 91 |
| diff | 10 | 9/9 | 23/63 | 840 | 0.147 | Albite; Baryte; Calcite; Fluorapatite; Hematite; Magnetite; Muscovite; Orthoclase | silicate 256; arsenic-bearing 138; phosphorus-bearing 133; other 127; carbon-bearing 73 |
| diff | 20 | 9/9 | 19/63 | 521 | 0.0912 | Fluorapatite; Muscovite | silicate 154; arsenic-bearing 116; other 74; phosphorus-bearing 58; carbon-bearing 46 |
| scatter | 5 | 8/9 | 8/63 | 322 | 0.0564 | Muscovite | silicate 88; arsenic-bearing 77; other 43; carbon-bearing 41; vanadium-bearing 23 |
| scatter | 8 | 6/9 | 6/63 | 184 | 0.0322 | none | silicate 56; arsenic-bearing 37; carbon-bearing 33; other 21; vanadium-bearing 15 |
| scatter | 10 | 6/9 | 4/63 | 130 | 0.0228 | none | silicate 40; carbon-bearing 30; arsenic-bearing 24; other 12; vanadium-bearing 10 |
| scatter | 20 | 0/9 | 0/63 | 39 | 0.0068 | none | carbon-bearing 20; silicate 5; arsenic-bearing 4; sulfur-bearing 3; other 3 |
| lag | 5 | 9/9 | 16/63 | 612 | 0.1071 | Calcite; Fluorapatite; Hematite; Muscovite; Orthoclase | silicate 179; arsenic-bearing 116; phosphorus-bearing 94; other 79; carbon-bearing 58 |
| lag | 8 | 9/9 | 10/63 | 406 | 0.0711 | Fluorapatite; Muscovite | silicate 113; arsenic-bearing 100; other 48; carbon-bearing 46; phosphorus-bearing 39 |
| lag | 10 | 9/9 | 9/63 | 344 | 0.0602 | Fluorapatite | silicate 97; arsenic-bearing 91; other 40; carbon-bearing 40; phosphorus-bearing 25 |
| lag | 20 | 6/9 | 5/63 | 172 | 0.0301 | none | silicate 48; arsenic-bearing 40; carbon-bearing 30; vanadium-bearing 18; other 16 |

## Crocoite spectra

| file | laser | position | rel. height | SNR diff | SNR scatter | SNR lag |
|---|---|---|---|---|---|---|
| R040053 | 514 | 839.152 | 1.0 | 103.73 | 16.53 | 41.66 |
| R040053 | 532 | 836.0195 | 1.0 | 90.02 | 6.11 | 14.45 |
| R040053 | 785 | 838.9177 | 1.0 | 219.96 | 15.07 | 34.88 |
| R050044 | 514 | 839.152 | 1.0 | 73.23 | 14.42 | 35.63 |
| R050044 | 532 | 834.7499 | 1.0 | 85.17 | 6.45 | 13.25 |
| R050044 | 785 | 838.8911 | 1.0 | 167.05 | 11.01 | 24.81 |
| R050044 | 514 | 833.715 | 1.0 | 25.3 | 4.69 | 10.11 |
| R160016 | 532 | 838.7925 | 1.0 | 149.04 | 10.75 | 23.94 |
| R160016 | 780 | 839.2022 | 1.0 | 185.37 | 13.87 | 31.36 |

RRUFF data: Lafuente et al. (2015). Spectra are not redistributed here.
Made by MV2 of Munim, Inc. with AI agents working in his name.
