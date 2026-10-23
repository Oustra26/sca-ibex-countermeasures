INPUTS = [
    0x00000000, 0x11111111, 0x22222222, 0x33333333,
    0x44444444, 0x55555555, 0x66666666, 0x77777777,
    0x88888888, 0x99999999, 0xAAAAAAAA, 0xCCCCCCCC,
    0xDDDDDDDD, 0xEEEEEEEE, 0xFFFFFFFF, 0x12345678,
]

MASKS = [
    0x13579BDF, 0x2468ACE0, 0x0F0F0F0F, 0xF0F0F0F0,
    0x55AA55AA, 0xAA55AA55, 0x12345678, 0x87654321,
    0xCAFEBABE, 0x0BADF00D, 0xDEADBEEF, 0x11223344,
    0x55667788, 0xA5A5A5A5, 0x5A5A5A5A, 0x89ABCDEF,
]

DELAYS   = [7, 23, 12, 31, 5, 18, 27, 9, 34, 14, 21, 6, 29, 16, 25, 11]
SECRET   = 0xBBBBBBBB
N_TRACES = 16
TVLA_THR = 4.5

FST_DIR     = "fst_traces"
VCD_DIR     = "vcd_traces"
RESULTS_DIR = "sca_results"

VERSIONS = {
    'baseline': {
        'label': 'Baseline (XOR direct)',
        'fst':   'sim_baseline.fst',
        'vcd':   'sim_baseline.vcd',
        'phases': {
            'xor': {'trigger': 'sca_dbg_trigger', 'label': 'XOR a⊕b', 'color': '#e74c3c'},
        },
        'attack_phase': 'xor',
        'model': 'direct',
    },
    'masking': {
        'label': 'Masquage booléen',
        'fst':   'sim_masking.fst',
        'vcd':   'sim_masking.vcd',
        'phases': {
            'mask_a':    {'trigger': 'sca_dbg_trigger_mask_a',    'label': 'share_a=a⊕m', 'color': '#3498db'},
            'mask_b':    {'trigger': 'sca_dbg_trigger_mask_b',    'label': 'share_b=b⊕m', 'color': '#2980b9'},
            'recombine': {'trigger': 'sca_dbg_trigger_recombine', 'label': 'x=sa⊕sb',     'color': '#1abc9c'},
        },
        'attack_phase': 'mask_a',
        'model': 'masked',
    },
    'temporal': {
        'label': 'Randomisation temporelle',
        'fst':   'sim_temporal.fst',
        'vcd':   'sim_temporal.vcd',
        'phases': {
            'rand_entry': {'trigger': 'sca_dbg_trigger_random', 'label': 'Entrée random_delay', 'color': '#f39c12'},
            'xor':        {'trigger': 'sca_dbg_trigger',        'label': 'XOR a⊕b',            'color': '#e67e22'},
        },
        'attack_phase': 'xor',
        'model': 'direct',
    },
    'dualrail': {
        'label': 'Équilibrage dual-rail',
        'fst':   'sim_dualrail.fst',
        'vcd':   'sim_dualrail.vcd',
        'phases': {
            'true_rail':  {'trigger': 'sca_dbg_trigger_dual_true',  'label': 'Rail vrai x', 'color': '#9b59b6'},
            'false_rail': {'trigger': 'sca_dbg_trigger_dual_false', 'label': 'Rail ~x',     'color': '#8e44ad'},
        },
        'attack_phase': 'true_rail',
        'model': 'dualrail',
    },
    'hybrid': {
        'label': 'Hybride (masquage+randomisation)',
        'fst':   'sim_hybrid.fst',
        'vcd':   'sim_hybrid.vcd',
        'phases': {
            'rand':      {'trigger': 'sca_dbg_trigger_rand',          'label': 'Entrée rand_delay', 'color': '#27ae60'},
            'mask_a':    {'trigger': 'sca_dbg_trigger_hyb_mask_a',    'label': 'share_a=a⊕m',       'color': '#2ecc71'},
            'mask_b':    {'trigger': 'sca_dbg_trigger_hyb_mask_b',    'label': 'share_b=b⊕m',       'color': '#16a085'},
            'recombine': {'trigger': 'sca_dbg_trigger_hyb_recombine', 'label': 'x=sa⊕sb',           'color': '#1abc9c'},
        },
        'attack_phase': 'mask_a',
        'model': 'hybrid',
    },
}
