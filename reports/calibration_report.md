# Macro calibration report

- Mode: full
- Measured per-run wall time: **27 ms**
- Wall-clock budget: 150 s
- runs/eval: 1  |  maxfev: 2000  |  evaluations actually run: 1998
- Stop reason (cap hit): **maxfev/convergence**
- Free params: base_conversion_rate, complex_contagion_threshold, secularization_term, persecution_severity, inter_region_decay, fertility_adv, martyrdom_amplification, nominal_to_practicing_ratio
- Notes: runs/eval=1 (model deterministic -> seed-averaging is a no-op, so 1/eval is used to maximize evaluations); fixed=[]
- Objective: start (midpoint) = 13.58549 -> best = 1.25091

## Calibrated parameters

| parameter | value | bounds |
|---|---:|---|
| base_conversion_rate | 0.1243 | [0.02, 0.8] |
| complex_contagion_threshold | 0.4000 | [0.0, 0.4] |
| secularization_term | 0.1891 | [0.0, 0.6] |
| persecution_severity | 0.3596 | [0.0, 1.0] |
| inter_region_decay | 0.3967 | [0.0, 0.95] |
| fertility_adv | 0.0000 | [0.0, 0.12] |
| martyrdom_amplification | 1.7278 | [0.0, 4.0] |
| nominal_to_practicing_ratio | 0.3876 | [0.02, 0.9] |

## Simulated vs anchor Christian% (residuals)

### GLOBAL

| year | sim % | anchor % | residual | confidence |
|---:|---:|---:|---:|---|
| 30 | 0.00 | 0.00 | -0.00 | Speculative |
| 100 | 3.68 | 0.41 | +3.27 | Speculative |
| 300 | 1.89 | 3.16 | -1.27 | Low |
| 313 | 1.96 | 3.68 | -1.73 | Low |
| 500 | 2.84 | 12.44 | -9.59 | Low |
| 1000 | 6.65 | 20.36 | -13.71 | Low |
| 1054 | 10.00 | 21.43 | -11.43 | Low |
| 1500 | 11.41 | 20.45 | -9.04 | Medium |
| 1517 | 11.44 | 20.90 | -9.46 | Medium |
| 1800 | 28.60 | 23.33 | +5.26 | Medium |
| 1900 | 30.08 | 34.44 | -4.36 | High |
| 1970 | 30.97 | 33.24 | -2.27 | High |
| 2000 | 41.00 | 32.52 | +8.48 | High |
| 2025 | 46.45 | 31.85 | +14.60 | High |

### Roman/Mediterranean

| year | sim % | anchor % | residual | confidence |
|---:|---:|---:|---:|---|
| 30 | 0.00 | 0.00 | -0.00 | Speculative |
| 100 | 8.69 | 1.17 | +7.53 | Speculative |
| 300 | 4.44 | 9.65 | -5.20 | Low |
| 313 | 4.77 | 11.23 | -6.46 | Low |
| 500 | 6.81 | 42.00 | -35.19 | Low |

### Western Europe

| year | sim % | anchor % | residual | confidence |
|---:|---:|---:|---:|---|
| 1000 | 33.58 | 73.68 | -40.11 | Low |
| 1500 | 34.90 | 81.43 | -46.53 | Low |
| 1900 | 84.41 | 70.37 | +14.04 | High |
| 1970 | 78.92 | 79.07 | -0.15 | High |
| 2000 | 67.53 | 61.22 | +6.30 | High |
| 2025 | 60.19 | 51.00 | +9.19 | High |

### Eastern Europe & Russia

| year | sim % | anchor % | residual | confidence |
|---:|---:|---:|---:|---|
| 1000 | 17.24 | 60.00 | -42.76 | Low |
| 1900 | 58.00 | 80.00 | -22.00 | High |
| 1970 | 56.23 | 36.11 | +20.12 | High |
| 2000 | 53.03 | 63.23 | -10.21 | High |
| 2025 | 49.84 | 73.53 | -23.69 | High |

### Middle East & North Africa

| year | sim % | anchor % | residual | confidence |
|---:|---:|---:|---:|---|
| 1000 | 1.68 | 17.14 | -15.46 | Low |
| 1500 | 0.32 | 10.00 | -9.68 | Medium |
| 1900 | 0.10 | 24.44 | -24.35 | High |
| 1970 | 0.19 | 9.23 | -9.04 | High |
| 2000 | 5.55 | 4.33 | +1.22 | High |
| 2025 | 20.74 | 3.00 | +17.74 | High |

### Sub-Saharan Africa

| year | sim % | anchor % | residual | confidence |
|---:|---:|---:|---:|---|
| 1900 | 7.08 | 9.47 | -2.39 | High |
| 1970 | 28.85 | 48.28 | -19.43 | High |
| 2000 | 47.92 | 56.72 | -8.80 | High |
| 2025 | 54.49 | 58.33 | -3.84 | High |

### South Asia

| year | sim % | anchor % | residual | confidence |
|---:|---:|---:|---:|---|
| 1900 | 0.95 | 1.72 | -0.77 | High |
| 2025 | 31.71 | 3.59 | +28.12 | High |

### East Asia

| year | sim % | anchor % | residual | confidence |
|---:|---:|---:|---:|---|
| 1900 | 3.15 | 0.44 | +2.70 | High |
| 2025 | 56.00 | 7.50 | +48.50 | High |

### Southeast Asia

| year | sim % | anchor % | residual | confidence |
|---:|---:|---:|---:|---|
| 1900 | 0.65 | 3.75 | -3.10 | High |
| 2025 | 16.88 | 23.19 | -6.31 | High |

### Latin America

| year | sim % | anchor % | residual | confidence |
|---:|---:|---:|---:|---|
| 1900 | 69.21 | 95.39 | -26.17 | High |
| 1970 | 78.67 | 94.74 | -16.07 | High |
| 2000 | 82.91 | 90.39 | -7.48 | High |
| 2025 | 83.76 | 90.91 | -7.15 | High |

### North America

| year | sim % | anchor % | residual | confidence |
|---:|---:|---:|---:|---|
| 1900 | 74.77 | 96.34 | -21.57 | High |
| 1970 | 74.04 | 91.30 | -17.27 | High |
| 2000 | 64.66 | 80.64 | -15.99 | High |
| 2025 | 57.92 | 72.00 | -14.08 | High |

**Mean absolute residual across scored anchors: 13.17 percentage points** (54 anchors).

_A symmetric 8-global-parameter model cannot perfectly separate every region (e.g. settler-colonial vs mission-field Christianization, or indigenous house-church growth). Residuals above are reported honestly; Phase 2 adds finer structure and ABC-SMC calibration._