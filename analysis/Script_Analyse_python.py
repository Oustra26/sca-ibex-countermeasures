import numpy as np
from scipy import stats
import vcdvcd
import matplotlib.pyplot as plt

# ─── Configuration ─────────────────────────────────────────────────────────────
VCD_FILE = "sim.vcd"   # généré par : fst2vcd sim.fst > sim.vcd

# Préfixe hiérarchique — à vérifier dans GTKWave (clic droit → copy name)
PREFIX = "ibex_simple_system.u_core"

SIGNALS = {
    "trigger_base"      : f"{PREFIX}.sca_dbg_trigger",
    "trigger_mask_a"    : f"{PREFIX}.sca_dbg_trigger_mask_a",
    "trigger_mask_b"    : f"{PREFIX}.sca_dbg_trigger_mask_b",
    "trigger_recombine" : f"{PREFIX}.sca_dbg_trigger_recombine",
    "trigger_random"    : f"{PREFIX}.sca_dbg_trigger_random",
    "trigger_dual_true" : f"{PREFIX}.sca_dbg_trigger_dual_true",
    "trigger_dual_false": f"{PREFIX}.sca_dbg_trigger_dual_false",
    "result_ex"         : f"{PREFIX}.sca_dbg_result_ex",
    "alu_op_a"          : f"{PREFIX}.sca_dbg_alu_op_a",
    "alu_op_b"          : f"{PREFIX}.sca_dbg_alu_op_b",
}

N_TRACES = 16

# ─── Parsing VCD ───────────────────────────────────────────────────────────────
def load_vcd(path):
    """Charge le VCD et retourne un dict signal_name → liste (time, int_value)."""
    print(f"Chargement de {path} ...")
    vcd = vcdvcd.VCDVCD(path)
    data = {}
    for name, sig_key in SIGNALS.items():
        try:
            sig = vcd[sig_key]
            # Convertir les valeurs binaires en entiers
            data[name] = [(t, int(v, 2)) for t, v in sig.tv if v not in ('x', 'z')]
        except KeyError:
            print(f"  [ATTENTION] Signal introuvable : {sig_key}")
            data[name] = []
    return data

def get_trigger_times(tv_list):
    """Retourne les instants des fronts montants (0→1)."""
    times = []
    prev = 0
    for t, v in tv_list:
        if v == 1 and prev == 0:
            times.append(t)
        prev = v
    return times

def get_value_at(tv_list, target_time):
    """Valeur du signal la plus récente avant ou à target_time."""
    val = 0
    for t, v in tv_list:
        if t <= target_time:
            val = v
        else:
            break
    return val

def extract_samples(data, trigger_key, data_key, input_key, n=N_TRACES):
    """
    Pour chaque front montant du trigger, extrait (data, input).
    Retourne deux arrays numpy.
    """
    trigger_times = get_trigger_times(data[trigger_key])[:n]
    samples_data  = []
    samples_input = []
    for t in trigger_times:
        samples_data.append(get_value_at(data[data_key], t))
        samples_input.append(get_value_at(data[input_key], t))
    return np.array(samples_data, dtype=np.uint32), \
           np.array(samples_input, dtype=np.uint32)

# ─── Modèles de fuite ──────────────────────────────────────────────────────────
def hw(x):
    return bin(int(x) & 0xFFFFFFFF).count('1')

hw_vec = np.vectorize(hw)

def hd(x, y):
    return hw(x ^ y)

# ─── CPA ───────────────────────────────────────────────────────────────────────
def cpa_32bit(traces, inputs, secret_bytes_range=range(256)):
    """
    CPA octet par octet (4 octets de 0xBBBBBBBB).
    Retourne le meilleur candidat de clé et la corrélation max.
    """
    best_k, best_rho = 0, 0.0
    all_rho = {}

    for k in secret_bytes_range:
        # Modèle HW : HW(input[i] XOR key_hypothesis)
        # On travaille sur l'octet de poids faible pour commencer
        model = hw_vec((inputs & 0xFF) ^ k)
        if np.std(model) < 1e-10 or np.std(traces) < 1e-10:
            continue
        rho, _ = stats.pearsonr(model.astype(float),
                                 (traces & 0xFF).astype(float))
        all_rho[k] = abs(rho)
        if abs(rho) > best_rho:
            best_rho = abs(rho)
            best_k   = k

    return best_k, best_rho, all_rho

# ─── DPA ───────────────────────────────────────────────────────────────────────
def dpa(traces, inputs, key_hyp=0xBB, target_bit=0):
    """
    Différence de moyennes entre les deux groupes définis par
    le bit target_bit du modèle HW(input ^ key_hyp).
    """
    model_bits = np.array(
        [(hw((inp & 0xFF) ^ key_hyp) >> target_bit) & 1 for inp in inputs]
    )
    g0 = traces[model_bits == 0].astype(float)
    g1 = traces[model_bits == 1].astype(float)
    if len(g0) == 0 or len(g1) == 0:
        return 0.0
    return abs(float(np.mean(g1)) - float(np.mean(g0)))

# ─── TVLA ──────────────────────────────────────────────────────────────────────
def tvla(traces_fixed, traces_random):
    """
    Test de Welch. Dans un fichier unique : les 8 premières traces
    = entrées 'faibles' (0x00..0x77), les 8 dernières = entrées 'fortes'
    (0x88..0xFF). Ce n'est qu'une approximation — idéalement deux
    simulations séparées (voir note ci-dessous).
    """
    t_fixed  = traces_fixed.astype(float)
    t_random = traces_random.astype(float)
    if np.std(t_fixed) < 1e-10 or np.std(t_random) < 1e-10:
        return 0.0
    t_stat, _ = stats.ttest_ind(t_fixed, t_random, equal_var=False)
    return abs(t_stat)

# ─── Analyse par version ───────────────────────────────────────────────────────
def analyse_version(name, trigger_key, data, label="result_ex"):
    print(f"\n{'='*55}")
    print(f" Version : {name}")
    print(f"{'='*55}")

    traces, inputs = extract_samples(data, trigger_key, "result_ex", "alu_op_a")
    print(f" Traces extraites : {len(traces)}")

    if len(traces) < 4:
        print(" [ATTENTION] Pas assez de traces — vérifier le nom du signal trigger")
        return

    # CPA
    best_k, best_rho, all_rho = cpa_32bit(traces, inputs)
    print(f" CPA  : meilleure hypothèse = 0x{best_k:02X}  |ρ| = {best_rho:.4f}")

    # DPA
    delta = dpa(traces, inputs, key_hyp=0xBB)
    print(f" DPA  : Δ moyennes (bit 0, k=0xBB) = {delta:.4f}")

    # TVLA (split 50/50 sur les 16 traces)
    mid = len(traces) // 2
    t_val = tvla(traces[:mid], traces[mid:])
    fuite = "FUITE DETECTEE" if t_val > 4.5 else "Pas de fuite (ce split)"
    print(f" TVLA : |t| = {t_val:.4f}  → {fuite}")

    # Graphique CPA
    plt.figure(figsize=(10, 3))
    plt.bar(list(all_rho.keys()), list(all_rho.values()), width=1, color='steelblue')
    plt.axvline(x=0xBB, color='red', linewidth=2,
                linestyle='--', label='k=0xBB (attendu)')
    plt.xlabel("Hypothèse de clé (octet 0)")
    plt.ylabel("|ρ| corrélation")
    plt.title(f"CPA — {name}")
    plt.legend()
    plt.tight_layout()
    fname = f"cpa_{name.lower().replace(' ', '_')}.png"
    plt.savefig(fname, dpi=150)
    print(f" Graphique : {fname}")
    plt.close()

    return {"cpa_rho": best_rho, "cpa_key": best_k,
            "dpa_delta": delta, "tvla_t": t_val}

# ─── Toggle count (énergie relative) ──────────────────────────────────────────
def count_toggles_between(tv_list, t_start, t_end):
    """Compte les transitions entre t_start et t_end."""
    toggles = 0
    prev_val = None
    for t, v in tv_list:
        if t < t_start:
            prev_val = v
            continue
        if t > t_end:
            break
        if prev_val is not None and v != prev_val:
            toggles += 1
        prev_val = v
    return toggles

def energy_estimate(data, trigger_key, signal_keys):
    """
    Estime l'énergie relative de la version via les toggles sur les
    signaux actifs entre le 1er et le dernier trigger.
    """
    t_times = get_trigger_times(data[trigger_key])
    if len(t_times) < 2:
        return 0
    t_start, t_end = t_times[0], t_times[-1]
    total = 0
    for sk in signal_keys:
        total += count_toggles_between(data[sk], t_start, t_end)
    return total

# ─── MAIN ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    data = load_vcd(VCD_FILE)

    energy_signals = ["result_ex", "alu_op_a", "alu_op_b"]
    results = {}

    versions = [
        ("Baseline",      "trigger_base"),
        ("Masquage_A",    "trigger_mask_a"),
        ("Masquage_B",    "trigger_mask_b"),
        ("Masquage_Reco", "trigger_recombine"),
        ("Randomisation", "trigger_random"),
        ("DualRail_True", "trigger_dual_true"),
        ("DualRail_False","trigger_dual_false"),
    ]

    print("\n" + "="*55)
    print(" ESTIMATION ÉNERGIE RELATIVE (toggles)")
    print("="*55)
    for name, trig in versions:
        tg = count_toggles_between(
            data[trig], 0, 999_999_999_999
        ) if data[trig] else 0
        e = energy_estimate(data, trig, energy_signals)
        results[name] = {"energy_toggles": e}
        print(f" {name:20s} : {e:6d} toggles")

    print("\n" + "="*55)
    print(" ANALYSE SCA PAR VERSION")
    print("="*55)
    for name, trig in versions:
        r = analyse_version(name, trig, data)
        if r:
            results[name].update(r)

    # ─── Tableau récapitulatif ─────────────────────────────────────────────────
    print("\n" + "="*70)
    print(f" {'Version':<22} {'CPA ρ':>8} {'Clé':>8} {'DPA Δ':>8} {'TVLA |t|':>10} {'Toggles':>10}")
    print("="*70)
    baseline_e = results.get("Baseline", {}).get("energy_toggles", 1) or 1
    for name, _ in versions:
        r = results.get(name, {})
        e_rel = r.get("energy_toggles", 0) / baseline_e
        print(f" {name:<22}"
              f" {r.get('cpa_rho', 0):>8.4f}"
              f" {'0x'+format(r.get('cpa_key',0),'02X'):>8}"
              f" {r.get('dpa_delta', 0):>8.4f}"
              f" {r.get('tvla_t', 0):>10.4f}"
              f" {e_rel:>9.2f}x")