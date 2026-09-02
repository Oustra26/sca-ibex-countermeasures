# Contre-mesures aux attaques par canaux auxiliaires sur le cœur RISC-V Ibex

Matériel de reproduction associé au mémoire de Master **« Étude comparative des mesures
de sécurité contre les attaques par canaux auxiliaires (Side-Channel Attacks, SCA) sur
une microarchitecture IBEX »**, ENETP, Bamako.

Ce dépôt rassemble tout ce qui est nécessaire pour reproduire les résultats du mémoire :
l'instrumentation RTL, les programmes de test, et les scripts d'analyse des traces.

---

## Résumé de l'étude

Cinq versions du même calcul sensible (un XOR entre une entrée connue et un secret fixe
`0xBBBBBBBB`) sont exécutées sur le cœur Ibex simulé au niveau RTL, puis attaquées avec
les mêmes méthodes statistiques.

| Version | CPA \|r\| | DPA \|DoM\| | TVLA \|t\| | Latence | Taille `.text` |
|---|---|---|---|---|---|
| Base non protégée | 1,0000 | 6,1746 | 0,4459 | 78 cyc (×1,0) | 1118 o |
| Masquage booléen | 0,4586 | 1,2063 | 1,1632 | 206 cyc (×2,6) | 1218 o (+8,9 %) |
| Randomisation temporelle | 1,0000 (aligné) | 6,1746 (aligné) | < 4,5 | +1324 cyc cumulés | aucun surcoût |
| Équilibrage dual-rail | 1,0000 (rail seul) | 6,1746 (rail seul) | 0,4459 | 138 cyc (×1,8) | 1180 o (+5,5 %) |
| Hybride | 0,4586 | 1,2063 | 1,1632 | 868 cyc (×11,1) | 1256 o (+12,3 %) |

Toutes les campagnes utilisent **N = 16 traces**. Cet échantillon volontairement réduit
suffit à la CPA et à la DPA, mais reste sous le seuil de puissance statistique du test
TVLA : c'est pourquoi tous les `|t|` restent sous 4,5, y compris pour la version non
protégée pourtant entièrement compromise selon la CPA.

---

## Organisation du dépôt

```
rtl/       sca_instrumentation.sv   bloc de sondes à insérer dans ibex_core.sv
sw/        hello_test_*.c           les cinq programmes de test
analysis/  scripts Python d'extraction et d'analyse (CPA, DPA, TVLA)
docs/      build_and_run.md         procédure complète pas à pas
```

---

## Prérequis

- Ubuntu 22.04+ ou WSL/Ubuntu
- [Verilator](https://verilator.org/) — simulation RTL
- [FuseSoC](https://github.com/olofk/fusesoc) — construction du cœur
- Toolchain `riscv32-unknown-elf-gcc`
- GTKWave et `fst2vcd` (paquet `gtkwave`)
- Python 3 avec `vcdvcd`, `numpy`, `scipy`, `matplotlib`
- Yosys (mesure de surface)

---

## Version de référence du cœur Ibex

Ce travail est basé sur le dépôt [lowRISC/ibex](https://github.com/lowRISC/ibex),
configuré en **RV32IMC**.

> **Commit de référence : `À COMPLÉTER`**
> À relever avec `git rev-parse HEAD` dans votre copie du dépôt Ibex.
> Sans cette information, les adresses de programme utilisées par les déclencheurs
> ne correspondront pas, car elles dépendent du code généré par le compilateur.

---

## Démarrage rapide

```bash
# 1. Cloner Ibex et se placer sur le commit de référence
git clone https://github.com/lowRISC/ibex.git
cd ibex && git checkout <COMMIT_DE_REFERENCE>

# 2. Insérer le bloc d'instrumentation dans rtl/ibex_core.sv
#    (voir docs/build_and_run.md pour l'emplacement exact)

# 3. Copier le programme de test de la version voulue
cp ../sca-ibex-countermeasures/sw/hello_test_baseline.c \
   examples/sw/simple_system/hello_test/hello_test.c

# 4. Construire, simuler, analyser
fusesoc --cores-root=. run --target=sim --setup --build lowrisc:ibex:ibex_simple_system
./build/lowrisc_ibex_ibex_simple_system_0/sim-verilator/Vibex_simple_system \
    --meminit=ram,examples/sw/simple_system/hello_test/hello_test.elf --trace
fst2vcd sim.fst -o sim.vcd
python3 ../sca-ibex-countermeasures/analysis/analyse_sca.py --vcd sim.vcd
```

La procédure détaillée figure dans [`docs/build_and_run.md`](docs/build_and_run.md).

---

## Point important : les blocs d'instrumentation sont mutuellement exclusifs

Les déclencheurs de plusieurs versions ciblent la **même adresse de programme**
(`0x00100348` est partagée par le dual-rail, le masquage, la randomisation et le délai
de la version hybride). Un seul bloc doit donc rester actif à la fois dans
`ibex_core.sv` ; les autres sont mis en commentaire.

Cette collision est normale : les cinq programmes sont compilés séparément et
l'éditeur de liens place leurs premières fonctions à des adresses voisines.

---

## Adresses de déclenchement

| Version | Signal | Adresse PC | Opcode attendu |
|---|---|---|---|
| Base | `sca_dbg_trigger` | `0x001003FE` | `0x01184633` (`xor a2,a6,a7`) |
| Masquage | `sca_dbg_trigger_mask_a` | `0x00100348` | `0x00B547B3` (`xor a5,a0,a1`) |
| Masquage | `sca_dbg_trigger_mask_b` | `0x00100350` | `0x00B547B3` |
| Masquage | `sca_dbg_trigger_recombine` | `0x0010035A` | `0x00B547B3` |
| Randomisation | `sca_dbg_trigger_random` | `0x00100348` | — |
| Dual-rail | `sca_dbg_trigger_dual_true` | `0x00100348` | — |
| Dual-rail | `sca_dbg_trigger_dual_false` | `0x00100350` | — |
| Hybride | `sca_dbg_trigger_rand` | `0x00100348` | — |
| Hybride | `sca_dbg_trigger_hyb_mask_a` | `0x00100360` | `0x00B547B3` |
| Hybride | `sca_dbg_trigger_hyb_mask_b` | `0x00100368` | `0x00B547B3` |
| Hybride | `sca_dbg_trigger_hyb_recombine` | `0x00100372` | `0x00B547B3` |

Trois de ces adresses ne sont pas des multiples de quatre (`0x001003FE`, `0x0010035A`,
`0x00100372`). C'est normal en RV32IMC : l'extension C ramène l'alignement `IALIGN` à
16 bits, ce qui rend valide toute adresse paire.

**Si vous recompilez, relevez vos propres adresses** avec :

```bash
riscv32-unknown-elf-objdump -d hello_test.elf | grep -A2 "<mask_share_a>:"
```

---

## Licence

Code sous licence Apache 2.0, comme le cœur Ibex dont ce travail dérive.
Voir [`LICENSE`](LICENSE).

## Citation

Voir [`CITATION.cff`](CITATION.cff).

## Auteur

**Ousmane TRAORÉ** — Master Génie électrique, spécialité Électronique
École Normale d'Enseignement Technique et Professionnel (ENETP), Bamako, Mali
Directeur : Dr. Yahaya COULIBALY — Encadrant : M. Abdramane DRAMÉ
