"""Static Q-V slope and local derivatives; charge is per unit area."""
import numpy as np


def extract_qv(voltage, charge_per_area):
    v, q = np.asarray(voltage, dtype=float), np.asarray(charge_per_area, dtype=float)
    if v.ndim != 1 or q.shape != v.shape or len(v) < 3:
        raise ValueError('Need matching one-dimensional arrays with >= 3 points')
    if not np.isfinite(v).all() or not np.isfinite(q).all() or not (np.diff(v) > 0).all():
        raise ValueError('Finite charge and strictly increasing voltage required')
    vc, qc = v-v.mean(), q-q.mean()
    slope = float(np.dot(vc, qc)/np.dot(vc, vc))
    intercept = float(q.mean()-slope*v.mean())
    local = np.gradient(q, v, edge_order=2)
    residual = q-(slope*v+intercept)
    if not np.isfinite([slope, intercept]).all() or not np.isfinite(local).all():
        raise ValueError('Non-finite extraction result')
    return {'slope_F_per_cm2': slope, 'intercept_C_per_cm2': intercept,
            'local_F_per_cm2': local.tolist(), 'fit_residual_C_per_cm2': residual.tolist()}
