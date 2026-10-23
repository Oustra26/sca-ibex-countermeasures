#!/usr/bin/env python3
import os, sys, subprocess, argparse, csv
from pathlib import Path
from typing import Optional, Dict, List, Tuple
import numpy as np
import scipy.stats
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
try:
    from vcdvcd import VCDVCD
except ImportError:
    sys.exit("[ERREUR] pip install vcdvcd --break-system-packages")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sca_config import (INPUTS, MASKS, DELAYS, SECRET, N_TRACES,
                        TVLA_THR, FST_DIR, VCD_DIR, RESULTS_DIR, VERSIONS)

def hw(x):
    return bin(x & 0xFFFFFFFF).count('1')

def make_dirs():
    for d in (VCD_DIR, RESULTS_DIR):
        Path(d).mkdir(parents=True, exist_ok=True)

def separator(title=''):
    line = '═' * 60
    if title:
        print(f"\n{line}\n  {title.upper()}\n{line}")
    else:
        print(line)

def fst_to_vcd(fst_path, vcd_path):
    if Path(vcd_path).exists():
        print(f"  [cache] {Path(vcd_path).name} déjà présent.")
        return True
    if not Path(fst_path).exists():
        print(f"  [manquant] FST introuvable : {fst_path}")
        return False
    print(f"  Conversion {Path(fst_path).name} → {Path(vcd_path).name} ...", end='', flush=True)
    try:
        with open(vcd_path, 'w') as fout:
            res = subprocess.run(['fst2vcd', fst_path], stdout=fout,
                                 stderr=subprocess.PIPE, timeout=180)
        if res.returncode == 0:
            size_mb = Path(vcd_path).stat().st_size / 1_048_576
            print(f" OK ({size_mb:.1f} Mo)")
            return True
        else:
            print(f" ERREUR (code {res.returncode})")
            Path(vcd_path).unlink(missing_ok=True)
            return False
    except FileNotFoundError:
        print("\n  [ERREUR] fst2vcd introuvable.")
        return False
    except subprocess.TimeoutExpired:
        print("\n  [ERREUR] Timeout.")
        return False

def discover_signal(vcd_obj, name):
    for path in vcd_obj.references_to_ids:
        tail = path.split('.')[-1].split('[')[0]
        if tail == name:
            return path
    for path in vcd_obj.references_to_ids:
        if name in path:
            return path
    return None

def rising_edges(vcd_obj, path):
    if path not in vcd_obj.references_to_ids:
        return []
    edges = []
    prev = '0'
    for t, v in vcd_obj[path].tv:
        cur = str(v).strip().lower()
        if cur in ('x', 'z'):
            continue
        if prev in ('0', 'x', 'z') and cur == '1':
            edges.append(int(t))
        prev = cur
    return edges

def value_at(vcd_obj, path, time_ps):
    if path not in vcd_obj.references_to_ids:
        return None
    val = None
    for t, v in vcd_obj[path].tv:
        if int(t) > time_ps:
            break
        try:
            if isinstance(v, int):
                val = v
            else:
                s = str(v).strip()
                if all(c in '01xzXZ' for c in s):
                    val = int(s.replace('x','0').replace('z','0')
                               .replace('X','0').replace('Z','0'), 2)
                else:
                    val = int(s, 16)
        except (ValueError, TypeError):
            pass
    return val

def load_traces(vcd_path, version_cfg):
    if not Path(vcd_path).exists():
        print(f"  [manquant] {vcd_path}")
        return None
    print(f"  Chargement {Path(vcd_path).name} ...", end='', flush=True)
    try:
        vcd_idx = VCDVCD(vcd_path, only_sigs=True)
    except Exception as e:
        print(f"\n  [ERREUR] {e}")
        return None
    wanted = [p['trigger'] for p in version_cfg['phases'].values()]
    wanted.append('sca_dbg_result_ex')
    paths_to_load = []
    for name in wanted:
        p = discover_signal(vcd_idx, name)
        if p and p not in paths_to_load:
            paths_to_load.append(p)
    if not paths_to_load:
        print(f"\n  [ERREUR] Aucun signal trouvé dans {vcd_path}")
        return None
    try:
        vcd = VCDVCD(vcd_path, signals=paths_to_load)
    except Exception as e:
        print(f"\n  [ERREUR] {e}")
        return None
    print(" OK")
    result_ex_path = discover_signal(vcd, 'sca_dbg_result_ex')
    if result_ex_path is None:
        print("  [ERREUR] sca_dbg_result_ex introuvable")
        return None
    data = {}
    for phase_name, phase_cfg in version_cfg['phases'].items():
        trig_path = discover_signal(vcd, phase_cfg['trigger'])
        if trig_path is None:
            print(f"  [absent] '{phase_cfg['trigger']}' → '{phase_name}' ignorée")
            continue
        edges = rising_edges(vcd, trig_path)
        if not edges:
            print(f"  [vide]   Aucun front sur '{phase_cfg['trigger']}'")
            continue
        if len(edges) < N_TRACES:
            print(f"  [avert]  {len(edges)}/{N_TRACES} triggers pour '{phase_name}'")
        edges = edges[:N_TRACES]
        result_vals = [(value_at(vcd, result_ex_path, t) or 0) for t in edges]
        data[phase_name] = {
            'triggers_ps': edges,
            'result_ex'  : result_vals,
            'label'      : phase_cfg['label'],
            'color'      : phase_cfg.get('color', '#888888'),
        }
        print(f"    Phase '{phase_name:12s}' : {len(edges):2d} triggers | "
              f"result_ex[0] = 0x{result_vals[0]:08X}")
    return data if data else None

def cpa_attack(intermediates, inputs, n_bytes=4):
    results = {}
    for k in range(n_bytes):
        observed = np.array([bin((x >> (k*8)) & 0xFF).count('1')
                             for x in intermediates], dtype=float)
        corrs_abs = np.zeros(256)
        corrs_signed = np.zeros(256)
        for h in range(256):
            predicted = np.array([bin(((inp >> (k*8)) & 0xFF) ^ h).count('1')
                                  for inp in inputs], dtype=float)
            if np.std(predicted) < 1e-9 or np.std(observed) < 1e-9:
                continue
            r = float(np.corrcoef(predicted, observed)[0, 1])
            corrs_abs[h] = abs(r)
            corrs_signed[h] = r
        results[k] = {'abs': corrs_abs, 'signed': corrs_signed}
    return results

def cpa_summary(cpa_res):
    max_per_byte  = [float(np.max(v['abs']))     for v in cpa_res.values()]
    keys_per_byte = [int(np.argmax(v['signed'])) for v in cpa_res.values()]
    return float(np.mean(max_per_byte)), keys_per_byte

def dpa_attack(intermediates, inputs, secret_byte=0xBB, byte_idx=0):
    n    = len(intermediates)
    pred = [((inp >> (byte_idx * 8)) & 0xFF) ^ secret_byte for inp in inputs]
    g1   = [hw(intermediates[i]) for i in range(n) if (pred[i] >> 7) & 1]
    g0   = [hw(intermediates[i]) for i in range(n) if not ((pred[i] >> 7) & 1)]
    if not g0 or not g1:
        return 0.0
    return abs(float(np.mean(g1)) - float(np.mean(g0)))

def tvla_attack(intermediates, inputs, fixed_input=0x00000000):
    fixed  = [hw(intermediates[i]) for i, a in enumerate(inputs) if a == fixed_input]
    random = [hw(intermediates[i]) for i, a in enumerate(inputs) if a != fixed_input]
    if len(fixed) < 2:
        fixed  = [hw(intermediates[i]) for i in range(0, len(intermediates), 2)]
        random = [hw(intermediates[i]) for i in range(1, len(intermediates), 2)]
    if len(fixed) < 2 or len(random) < 2:
        return 0.0, 1.0, False
    t, p = scipy.stats.ttest_ind(fixed, random, equal_var=False)
    t_abs = abs(float(t))
    return t_abs, float(p), t_abs > TVLA_THR

def dualrail_analysis(data):
    metrics = {}
    if 'true_rail' not in data or 'false_rail' not in data:
        return metrics
    true_vals  = data['true_rail']['result_ex']
    false_vals = data['false_rail']['result_ex']
    n = min(len(true_vals), len(false_vals))
    combined_hw = [hw(true_vals[i]) + hw(false_vals[i]) for i in range(n)]
    metrics['combined_hw_mean'] = float(np.mean(combined_hw))
    metrics['combined_hw_std']  = float(np.std(combined_hw))
    metrics['is_balanced']      = metrics['combined_hw_std'] < 0.01
    cpa_res = cpa_attack(true_vals, INPUTS)
    max_c, _ = cpa_summary(cpa_res)
    metrics['cpa_true_max_corr']     = max_c
    metrics['cpa_combined_max_corr'] = 0.0
    return metrics

def _plot_cpa(ax, cpa_res, title, secret_byte=0xBB):
    colors = ['#e74c3c', '#3498db', '#2ecc71', '#f39c12']
    for k, v in cpa_res.items():
        ax.plot(range(256), v['abs'], color=colors[k % 4],
                alpha=0.75, linewidth=1.2, label=f'Octet {k}')
    ax.axvline(x=secret_byte, color='black', linestyle='--',
               linewidth=1.8, label=f'Secret 0x{secret_byte:02X}')
    ax.set_xlabel('Hypothèse de clé (0x00–0xFF)', fontsize=8)
    ax.set_ylabel('|Corrélation de Pearson|', fontsize=8)
    ax.set_title(title, fontsize=9, fontweight='bold')
    ax.set_xlim(0, 255); ax.set_ylim(0, 1.1)
    ax.legend(fontsize=7); ax.grid(True, alpha=0.3)

def _plot_dpa(ax, dpa_vals, title):
    phases = list(dpa_vals.keys())
    vals   = [dpa_vals[p] for p in phases]
    cols   = ['#e74c3c' if v >= 0.5 else '#2ecc71' for v in vals]
    bars   = ax.bar(phases, vals, color=cols, edgecolor='black', linewidth=0.7)
    ax.axhline(0.5, color='darkorange', linestyle='--',
               linewidth=1.3, label='Seuil 0.5')
    ax.set_ylabel('|Diff. de moyennes| (HW)', fontsize=8)
    ax.set_title(title, fontsize=9, fontweight='bold')
    ax.tick_params(axis='x', labelsize=7)
    ax.legend(fontsize=7); ax.grid(True, alpha=0.3, axis='y')
    for bar, v in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height()+0.02,
                f'{v:.2f}', ha='center', va='bottom', fontsize=7)

def _plot_tvla(ax, t_abs, title):
    color = '#e74c3c' if t_abs > TVLA_THR else '#2ecc71'
    ax.bar(['|t|'], [t_abs], color=color, edgecolor='black', linewidth=0.7)
    ax.axhline(TVLA_THR, color='black', linestyle='--',
               linewidth=1.8, label=f'Seuil TVLA ({TVLA_THR})')
    msg = 'FUITE DÉTECTÉE' if t_abs > TVLA_THR else 'Pas de fuite'
    ax.text(0, max(t_abs, TVLA_THR)*1.08, msg, ha='center',
            fontsize=8, fontweight='bold', color=color)
    ax.set_ylabel('|t| de Welch', fontsize=8)
    ax.set_title(title, fontsize=9, fontweight='bold')
    ax.set_ylim(0, max(t_abs, TVLA_THR)*1.35+0.5)
    ax.legend(fontsize=7); ax.grid(True, alpha=0.3, axis='y')

def plot_version(version_name, version_cfg, data):
    attack_phase = version_cfg['attack_phase']
    if attack_phase not in data:
        print(f"  [avert] Phase '{attack_phase}' non disponible")
        return None
    intermediates = data[attack_phase]['result_ex']
    secret_byte   = (SECRET >> 0) & 0xFF
    cpa_res            = cpa_attack(intermediates, INPUTS)
    max_corr, win_keys = cpa_summary(cpa_res)
    key_found = all(win_keys[k] == ((SECRET >> (k*8)) & 0xFF)
                    for k in range(len(win_keys)))
    dpa_vals = {pn: dpa_attack(pd['result_ex'], INPUTS)
                for pn, pd in data.items()}
    t_abs, p_val, detected = tvla_attack(intermediates, INPUTS)
    fig = plt.figure(figsize=(15, 4.5))
    fig.suptitle(f"Analyse SCA — {version_cfg['label']}",
                 fontsize=12, fontweight='bold', y=1.01)
    gs = gridspec.GridSpec(1, 3, figure=fig, wspace=0.42)
    _plot_cpa(fig.add_subplot(gs[0, 0]), cpa_res,
              f"CPA — {data[attack_phase]['label']}\n(corr. max = {max_corr:.3f})",
              secret_byte)
    _plot_dpa(fig.add_subplot(gs[0, 1]), dpa_vals,
              "DPA — Différence de moyennes")
    _plot_tvla(fig.add_subplot(gs[0, 2]), t_abs,
               f"TVLA — {data[attack_phase]['label']}\n(|t| = {t_abs:.2f})")
    out_path = os.path.join(RESULTS_DIR, f"sca_{version_name}.png")
    plt.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"\n  ┌── {version_cfg['label']}")
    print(f"  │  CPA corr. max : {max_corr:.4f}  "
          f"{'✓ CLÉ TROUVÉE' if key_found else '✗ CLÉ MANQUÉE'}")
    print(f"  │  Clé gagnante  : {[hex(k) for k in win_keys]}")
    print(f"  │  DPA |DoM|     : {dpa_vals.get(attack_phase, 0):.4f}")
    print(f"  │  TVLA |t|      : {t_abs:.4f}  "
          f"{'→ FUITE ✗' if detected else '→ OK ✓'}")
    print(f"  │  Figure        : {out_path}")
    print(f"  └{'─'*50}")
    return {'version': version_name, 'label': version_cfg['label'],
            'attack_phase': attack_phase, 'cpa_max_corr': max_corr,
            'cpa_key_found': key_found, 'dpa_dom': dpa_vals.get(attack_phase, 0.0),
            'tvla_t': t_abs, 'tvla_p': p_val, 'tvla_detected': detected}

def plot_comparative(all_metrics):
    if not all_metrics:
        return
    labels   = [r['label']        for r in all_metrics]
    cpa_vals = [r['cpa_max_corr'] for r in all_metrics]
    dpa_vals = [r['dpa_dom']      for r in all_metrics]
    tvla_vals= [r['tvla_t']       for r in all_metrics]
    palette  = ['#e74c3c','#3498db','#f39c12','#9b59b6','#27ae60']
    colors   = palette[:len(all_metrics)]
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    fig.suptitle("Comparaison des contre-mesures SCA — Ibex RISC-V",
                 fontsize=13, fontweight='bold')
    for ax, vals, title, ylabel, extra in [
        (axes[0], cpa_vals, "Corrélation CPA max\n(↑ = plus de fuite)",
         "|Corrélation de Pearson|", lambda a: a.axhline(1.0,color='grey',linestyle=':',lw=1.2) or a.set_ylim(0,1.2)),
        (axes[1], dpa_vals, "DPA — Diff. de moyennes\n(↑ = plus de fuite)",
         "|DoM| en unités HW", lambda a: a.axhline(0.5,color='darkorange',linestyle='--',lw=1.3,label='Seuil 0.5') or a.legend(fontsize=8)),
        (axes[2], tvla_vals,"TVLA — Stat. t de Welch\n(|t|>4.5 = fuite)",
         "|t| de Welch", lambda a: a.axhline(TVLA_THR,color='black',linestyle='--',lw=1.8,label=f'Seuil ({TVLA_THR})') or a.legend(fontsize=8)),
    ]:
        bars = ax.bar(labels, vals, color=colors, edgecolor='black', lw=0.7)
        ax.set_title(title, fontsize=10, fontweight='bold')
        ax.set_ylabel(ylabel)
        ax.tick_params(axis='x', rotation=20, labelsize=8)
        ax.grid(True, alpha=0.3, axis='y')
        extra(ax)
        for bar, v in zip(bars, vals):
            ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.02,
                    f'{v:.3f}', ha='center', va='bottom', fontsize=8)
    plt.tight_layout()
    out = os.path.join(RESULTS_DIR, "sca_comparative.png")
    plt.savefig(out, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"\n  Figure comparative : {out}")

def export_csv(all_metrics):
    if not all_metrics:
        return
    fields = ['version','label','attack_phase','cpa_max_corr','cpa_key_found',
              'dpa_dom','tvla_t','tvla_p','tvla_detected']
    out = os.path.join(RESULTS_DIR, "sca_summary.csv")
    with open(out, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in all_metrics:
            w.writerow({k: row.get(k,'') for k in fields})
    print(f"  CSV exporté : {out}")

def analyze_version(version_name):
    if version_name not in VERSIONS:
        print(f"[ERREUR] Version inconnue : '{version_name}'")
        return None
    cfg = VERSIONS[version_name]
    separator(f"Version : {cfg['label']}")
    fst_path = os.path.join(FST_DIR, cfg['fst'])
    vcd_path = os.path.join(VCD_DIR, cfg['vcd'])
    if not fst_to_vcd(fst_path, vcd_path):
        return None
    data = load_traces(vcd_path, cfg)
    if data is None:
        return None
    if cfg['model'] == 'dualrail':
        dr = dualrail_analysis(data)
        print(f"\n  Analyse dual-rail :")
        print(f"    HW(vrai)+HW(~vrai) moyen = {dr.get('combined_hw_mean','?'):.2f}")
        print(f"    Écart-type (cible ≈ 0)   = {dr.get('combined_hw_std','?'):.4f}")
        print(f"    Équilibrage parfait       : {'OUI ✓' if dr.get('is_balanced') else 'NON ✗'}")
        print(f"    CPA rail vrai seul        : {dr.get('cpa_true_max_corr','?'):.4f}")
    return plot_version(version_name, cfg, data)

def main():
    parser = argparse.ArgumentParser(description='Pipeline SCA — Ibex RISC-V')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--version', choices=list(VERSIONS.keys()), metavar='NOM',
                       help='Analyser une version : ' + ' | '.join(VERSIONS.keys()))
    group.add_argument('--all', action='store_true',
                       help='Analyser les 5 versions + tableau comparatif')
    group.add_argument('--list-signals', metavar='VCD',
                       help='Lister les signaux sca_dbg_* dans un VCD')
    args = parser.parse_args()
    make_dirs()
    if args.list_signals:
        if not Path(args.list_signals).exists():
            sys.exit(f"[ERREUR] Fichier introuvable : {args.list_signals}")
        vcd = VCDVCD(args.list_signals, only_sigs=True)
        found = [s for s in sorted(vcd.references_to_ids) if 'sca_dbg' in s]
        print(f"\nSignaux sca_dbg_* dans {args.list_signals} :\n")
        [print(f"  {s}") for s in found] if found else print("  (aucun)")
        return
    if args.version:
        m = analyze_version(args.version)
        print("\n  Terminé." if m else "\n  [ERREUR] Analyse incomplète.")
        return
    if args.all:
        all_metrics = []
        for v in VERSIONS:
            m = analyze_version(v)
            if m:
                all_metrics.append(m)
        if not all_metrics:
            print("\n  Aucun résultat disponible.")
            return
        separator("Tableau comparatif final")
        print(f"  {'Version':<32} {'CPA':>8} {'DPA':>8} {'TVLA|t|':>9} {'Fuite':>8}")
        print("  " + "─" * 68)
        for r in all_metrics:
            tag = 'OUI ✗' if r['tvla_detected'] else 'NON ✓'
            print(f"  {r['label']:<32} {r['cpa_max_corr']:>8.4f} "
                  f"{r['dpa_dom']:>8.4f} {r['tvla_t']:>9.4f} {tag:>8}")
        plot_comparative(all_metrics)
        export_csv(all_metrics)
        print("\n  Résultats dans :", RESULTS_DIR)

if __name__ == '__main__':
    main()
