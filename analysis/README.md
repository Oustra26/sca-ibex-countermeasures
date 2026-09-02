# Scripts d'analyse des traces

Ce dossier doit contenir les scripts Python utilisés pour extraire les signaux
`sca_dbg_*` des traces et calculer les métriques CPA, DPA et TVLA.

## À ajouter

Déposez ici vos scripts existants, par exemple :

- `analyse_sca.py` — extraction des signaux depuis le VCD et calcul des trois métriques
- `plot_results.py` — génération des figures 14 à 16 du mémoire

## Chaîne de traitement

1. Verilator produit `sim.fst`
2. `fst2vcd sim.fst -o sim.vcd` convertit au format lisible par `vcdvcd`
3. Le script Python extrait les valeurs de `sca_dbg_result_ex` aux instants où
   le déclencheur de la version est actif
4. Les métriques sont calculées sur les 16 traces obtenues

## Rappel des formules

**CPA** — corrélation de Pearson entre le modèle de fuite `h = HW(entrée XOR k)`
et la trace observée. La clé retenue maximise `|rho|`.

**DPA** — les traces sont réparties en deux groupes selon le bit de poids fort de
l'octet de poids fort du résultat ; `|DoM|` est la différence des moyennes.

**TVLA** — test de Welch (`scipy.stats.ttest_ind` avec `equal_var=False`) entre un
groupe à entrée fixe et un groupe à entrée aléatoire. Seuil usuel : `|t| > 4,5`.

## Dépendances

```bash
pip install vcdvcd numpy scipy matplotlib
```
