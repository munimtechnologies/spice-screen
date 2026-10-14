# Band shape vs spice-screen's 840 cm-1 lead chromate flags (RRUFF)

Base verdicts: spice-screen 0.4.0 verdicts (published audit CSV). Spectra read: 5787 (errors 0); covering 840 cm-1: 5785; 0.4.0-positive and covered: 1972. Mixtures: 1836 (9 crocoite x 34 filler spectra x 6 fractions; 0.4.0 run on each: True).

## Crocoite spectra

| file | laser | 0.4.0 | apex | apex ok | dominance | FWHM | bend ratio | bend peaks |
|---|---|---|---|---|---|---|---|---|
| R040053 | 514 | screen-positive | 839 | True | 1 | 10.2 | 0.0484 | 0 |
| R040053 | 532 | screen-positive | 836 | True | 1 | 28.5 | 0.04 | 0 |
| R040053 | 785 | screen-positive | 839 | True | 1 | 11.1 | 0.71 | 4 |
| R050044 | 514 | screen-positive | 839 | True | 1 | 11.4 | 0.0593 | 2 |
| R050044 | 532 | screen-positive | 835 | True | 1 | 28.4 | 0.0547 | 2 |
| R050044 | 785 | screen-positive | 839 | True | 1 | 13.5 | 0.579 | 4 |
| R050044 | 514 | screen-positive | 834 | True | 1 | 37.5 | 0.0913 | 2 |
| R160016 | 532 | screen-positive | 839 | True | 1 | 16 | 0.126 | 2 |
| R160016 | 780 | screen-positive | 839 | True | 1 | 13.1 | 0.821 | 4 |

## Features among 0.4.0 positives (min / p10 / median / p90 / max)

| class | n | apex ok | dominance | FWHM (cm-1) | bend ratio |
|---|---|---|---|---|---|
| crocoite | 9 | 9 | 1 / 1 / 1 / 1 / 1 | 10.2 / 11.1 / 13.5 / 28.5 / 37.5 | 0.04 / 0.0484 / 0.0913 / 0.71 / 0.821 |
| lead pigments | 25 | 25 | 0.593 / 0.882 / 1 / 1 / 1 | 2.3 / 4.67 / 6.36 / 10.6 / 29.9 | -2.01 / 0.0121 / 0.213 / 10.6 / 297 |
| fillers | 57 | 53 | 0.0652 / 0.252 / 0.713 / 1 / 1 | 1.15 / 1.69 / 3.9 / 40.9 / 59.5 | -13.1 / -0.0001 / 3.06 / 45.8 / 358 |
| vanadium-bearing (no Cr) | 48 | 41 | 0.0001 / 0.171 / 1 / 1 / 1 | 0.45 / 3.29 / 17.8 / 34.4 / 54.5 | 0.01 / 0.162 / 1.72 / 20 / 3.01e+03 |
| arsenic-bearing (no Cr) | 198 | 190 | 0.0033 / 0.575 / 1 / 1 / 1 | 1.31 / 2.27 / 19.7 / 47.5 / 92.6 | -7.64 / 0.0952 / 0.382 / 584 / 7.88e+03 |
| silicates (no Cr) | 611 | 515 | 0.0002 / 0.0636 / 0.586 / 1 / 1 | 0.08 / 1.74 / 12 / 43.4 / 73.5 | -7.13 / 0.33 / 9.04 / 64.7 / 1.38e+04 |
| all other no-Cr | 1853 | 1616 | 0 / 0.138 / 0.844 / 1 / 1 | 0 / 1.89 / 12.4 / 43.5 / 92.6 | -7.64 / 0.198 / 6.11 / 78.8 / 1.38e+04 |

## Shortlist (keeps every crocoite spectrum; mixtures at f=0.03/0.1 within 5 points of no gate)

| rule | crocoite | other Cr | no-Cr | lead pigments | fillers | f=0 | f=0.003 | f=0.01 | f=0.03 | f=0.1 | f=0.3 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| none | 9/9 | 28 | 1880/1935 | 25 | 57 | 0.0817 | 0.0719 | 0.19 | 0.778 | 0.944 | 0.977 |
| apex+dom>=0.5+fwhm<=45 | 9/9 | 17 | 1170/1935 | 25 | 32 | 0.0425 | 0.0523 | 0.163 | 0.729 | 0.928 | 0.974 |
| dom>=0.5+fwhm<=45 | 9/9 | 17 | 1244/1935 | 25 | 33 | 0.0588 | 0.0654 | 0.183 | 0.748 | 0.935 | 0.974 |
| apex+dom>=0.5 | 9/9 | 25 | 1282/1935 | 25 | 36 | 0.0523 | 0.0556 | 0.163 | 0.732 | 0.938 | 0.977 |
| dom>=0.5 | 9/9 | 25 | 1383/1935 | 25 | 38 | 0.0784 | 0.0719 | 0.186 | 0.752 | 0.944 | 0.977 |
| apex+fwhm<=45 | 9/9 | 19 | 1571/1935 | 25 | 49 | 0.0458 | 0.0523 | 0.167 | 0.755 | 0.928 | 0.974 |
| apex | 9/9 | 27 | 1694/1935 | 25 | 53 | 0.0556 | 0.0556 | 0.167 | 0.758 | 0.938 | 0.977 |
| fwhm<=45 | 9/9 | 20 | 1719/1935 | 25 | 52 | 0.0621 | 0.0654 | 0.186 | 0.774 | 0.935 | 0.974 |
| none | 9/9 | 28 | 1880/1935 | 25 | 57 | 0.0817 | 0.0719 | 0.19 | 0.778 | 0.944 | 0.977 |

Detection columns are the share of crocoite-in-filler mixtures flagged by 0.4.0 AND the gates; f=0 is the filler alone (false flags). f is a peak-height fraction, not a mass fraction.

RRUFF data: Lafuente et al. (2015), The power of databases: the RRUFF project. Spectra are not redistributed here.
