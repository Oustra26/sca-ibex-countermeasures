# Procédure complète de construction et d'exécution

Cette procédure est rejouée à l'identique pour chacune des cinq versions.
Seuls changent le programme de test (étape 3) et le bloc d'instrumentation
actif (étape 2).

---

## 1. Préparation de l'environnement

```bash
git clone https://github.com/lowRISC/ibex.git
cd ibex
git checkout <COMMIT_DE_REFERENCE>
pip3 install -r python-requirements.txt

# Vérification des outils
verilator --version
fusesoc --version
riscv32-unknown-elf-gcc -v
```

---

## 2. Insertion de l'instrumentation RTL

Ouvrir `rtl/ibex_core.sv` et coller le contenu de `rtl/sca_instrumentation.sv`
à un emplacement où tous les signaux internes référencés sont visibles —
c'est-à-dire après les déclarations de `pc_id`, `instr_valid_id`,
`instr_rdata_alu_id`, `rf_rdata_a/b`, `alu_operand_a/b_ex` et `result_ex`,
avant le `endmodule`.

> **Un seul bloc actif à la fois.** Les déclencheurs de plusieurs versions
> ciblent la même adresse (`0x00100348`). Commentez les blocs des versions
> que vous n'analysez pas, sinon plusieurs déclencheurs s'activeront
> simultanément et les traces seront inexploitables.

Blocs disponibles dans le fichier :

| Bloc | À activer pour |
|---|---|
| `Instrumentation : version de base non protegee` | baseline |
| `Instrumentation : masquage booleen` | masquage |
| `Instrumentation : randomisation temporelle` | randomisation |
| `Instrumentation : equilibrage logique (dual-rail)` | dual-rail |
| `Instrumentation : version hybride` | hybride |

---

## 3. Choix du programme de test

```bash
cp ../sca-ibex-countermeasures/sw/hello_test_baseline.c \
   examples/sw/simple_system/hello_test/hello_test.c
```

Remplacer `hello_test_baseline.c` par la version voulue :
`hello_test_masquage.c`, `hello_test_randomisation.c`,
`hello_test_dualrail.c` ou `hello_test_hybrid.c`.

---

## 4. Construction du modèle Verilator

```bash
fusesoc --cores-root=. run --target=sim --setup --build \
        lowrisc:ibex:ibex_simple_system
```

---

## 5. Compilation du programme

```bash
cd examples/sw/simple_system/hello_test
make
cd -
```

---

## 6. Vérification des adresses de déclenchement

**Étape indispensable après toute recompilation.** Les adresses dépendent du
code généré par le compilateur et changent d'une version à l'autre.

```bash
riscv32-unknown-elf-objdump -d \
  examples/sw/simple_system/hello_test/hello_test.elf | less
```

Repérer l'adresse de l'instruction XOR cible dans chaque fonction, puis
reporter ces valeurs dans les `localparam` ou les comparaisons `pc_id ==`
du bloc d'instrumentation actif.

---

## 7. Simulation avec génération de trace

```bash
./build/lowrisc_ibex_ibex_simple_system_0/sim-verilator/Vibex_simple_system \
    --meminit=ram,examples/sw/simple_system/hello_test/hello_test.elf \
    --trace
```

Produit `sim.fst`.

---

## 8. Conversion et visualisation

```bash
fst2vcd sim.fst -o sim.vcd     # format lisible par vcdvcd
gtkwave sim.fst &              # contrôle visuel
```

Vérifier dans GTKWave que le déclencheur s'active bien **16 fois**, une par
itération. Si ce n'est pas le cas, l'adresse de l'étape 6 est incorrecte.

---

## 9. Mesure de surface

```bash
yosys -p "read_verilog rtl/*.v; synth; stat"
```

---

## 10. Analyse statistique

```bash
python3 ../sca-ibex-countermeasures/analysis/analyse_sca.py \
        --vcd sim.vcd --traces 16 --secret 0xBBBBBBBB
```

---

## Dépannage

**Le déclencheur ne s'active jamais** — l'adresse PC ne correspond pas au
binaire compilé. Reprendre l'étape 6.

**Le déclencheur s'active plus de 16 fois** — plusieurs blocs d'instrumentation
sont actifs simultanément. Revoir l'étape 2.

**Verilator signale des signaux inutilisés** — vérifier que la directive
`/* verilator lint_off UNUSEDSIGNAL */` est bien présente en tête du bloc.

**`trigger_match` non déclaré** — ajouter `logic trigger_match;` avec les
autres déclarations du bloc de la version de base.
