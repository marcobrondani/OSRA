#!/usr/bin/env python3
"""
OSRA weight sensitivity check.

Re-scores every calibration convergence point under alternative weights for
the two weighted factors, regulatory exposure and blast radius, and reports
whether the within-scenario ranking changes. Categories are not tested here
because they come from the three convergence conditions, not from the score.

Run:  python3 weight_sensitivity.py
Data: the per-factor scores published in OSRA_Scoring_Calibration (four
scenarios, five factors, scored before Materialisation Horizon was added) and
the EuroBank Sentinel worked example (six factors).

Factor order in each row: regulatory exposure, detection deficit, trust depth,
blast radius, remediation complexity, materialisation horizon (None where the
scenario predates the sixth factor).
"""

from itertools import combinations

SCENARIOS = {
    "EuroBank Sentinel (finance, six factors)": {
        "CP1 base model behaviour change": (5, 5, 4, 5, 4, 5),
        "CP2 sanctions data integrity": (5, 5, 3, 5, 3, 5),
        "CP3 co-located monitoring": (4, 5, 4, 5, 4, 3),
        "CP4 vendor knowledge concentration": (3, 2, 3, 3, 3, 2),
        "CP5 GPU silent data corruption": (3, 5, 2, 2, 4, 5),
    },
    "StreamPay (digital services)": {
        "SP-CP1 LLM API dependency": (5, 4, 4, 5, 5, None),
        "SP-CP2 device fingerprinting": (3, 4, 3, 3, 3, None),
        "SP-CP3 RAG database integrity": (3, 3, 1, 4, 2, None),
        "SP-CP4 cross-border regulatory": (4, 2, 2, 3, 4, None),
    },
    "MedAssist (healthcare)": {
        "MH-CP1 model opacity": (5, 5, 5, 5, 5, None),
        "MH-CP4 physician over-reliance": (5, 5, 3, 5, 5, None),
        "MH-CP2 EHR integration fragility": (4, 4, 3, 4, 4, None),
        "MH-CP3 MDR certification scope": (4, 2, 3, 3, 3, None),
        "MH-CP5 cross-border patient data": (3, 2, 2, 2, 3, None),
    },
    "RouteOptima (logistics)": {
        "TL-CP1 maps platform dependency": (2, 4, 3, 4, 4, None),
        "TL-CP3 fleet GPS data": (2, 3, 2, 3, 2, None),
        "TL-CP2 demand model drift": (2, 3, 1, 4, 2, None),
        "TL-CP5 weather data quality": (1, 3, 2, 2, 1, None),
        "TL-CP4 single-region concentration": (2, 1, 1, 5, 4, None),
    },
    "GridSense (energy)": {
        "NW-CP1 OEM total dependency": (4, 5, 5, 5, 5, None),
        "NW-CP4 maintenance decision risk": (5, 4, 4, 4, 4, None),
        "NW-CP2 offshore connectivity": (3, 4, 3, 4, 4, None),
        "NW-CP3 training data mismatch": (3, 4, 4, 3, 3, None),
        "NW-CP5 grid reporting": (3, 2, 2, 2, 2, None),
    },
}

BASELINE = (1.5, 1.5)
WEIGHT_SETS = [
    (1.0, 1.0),
    (1.5, 1.5),
    (2.0, 2.0),
    (1.5, 1.0),
    (1.0, 1.5),
    (2.0, 1.5),
    (1.5, 2.0),
    (3.0, 3.0),
]


def score(factors, w_reg, w_blast, five_factor=False):
    """Weighted total. five_factor=True drops materialisation horizon so that
    scenarios scored before the sixth factor existed can be compared."""
    reg, det, trust, blast, remed, horizon = factors
    total = reg * w_reg + det + trust + blast * w_blast + remed
    if horizon is not None and not five_factor:
        total += horizon
    return total


def ranking(points, w_reg, w_blast):
    return sorted(points, key=lambda k: (-score(points[k], w_reg, w_blast), k))


def kendall_tau(a, b):
    """Kendall tau-a between two orderings of the same items."""
    pos_a = {k: i for i, k in enumerate(a)}
    pos_b = {k: i for i, k in enumerate(b)}
    concordant = discordant = 0
    for x, y in combinations(a, 2):
        s = (pos_a[x] - pos_a[y]) * (pos_b[x] - pos_b[y])
        if s > 0:
            concordant += 1
        elif s < 0:
            discordant += 1
    n = len(a)
    return (concordant - discordant) / (n * (n - 1) / 2)


def main():
    print("| Scenario | Weights (reg, blast) | Ranking | Top point unchanged | Kendall tau vs 1.5/1.5 |")
    print("|---|---|---|---|---|")
    for name, points in SCENARIOS.items():
        base = ranking(points, *BASELINE)
        for w in WEIGHT_SETS:
            r = ranking(points, *w)
            order = " > ".join(k.split()[0] for k in r)
            print(
                f"| {name} | {w[0]}, {w[1]} | {order} | "
                f"{'yes' if r[0] == base[0] else 'no'} | {kendall_tau(base, r):.2f} |"
            )
    print()
    # Cross-scenario comparison on five factors for every scenario, EuroBank
    # included, so that the four calibration scenarios and the worked example
    # sit on the same basis. Within-scenario rankings above use every factor
    # a scenario was scored on.
    print("| Weights (reg, blast) | Scenario maxima on five factors, high to low |")
    print("|---|---|")
    for w in WEIGHT_SETS:
        maxima = sorted(
            ((max(score(f, *w, five_factor=True) for f in pts.values()), n) for n, pts in SCENARIOS.items()),
            reverse=True,
        )
        print(f"| {w[0]}, {w[1]} | " + ", ".join(f"{n.split(' (')[0]} {m:.1f}" for m, n in maxima) + " |")
    print()
    # Ties at the baseline, since the ranking is what the score is for.
    print("Score ties at baseline weights:")
    for name, points in SCENARIOS.items():
        seen = {}
        for k, f in points.items():
            seen.setdefault(score(f, *BASELINE), []).append(k.split()[0])
        ties = [v for v in seen.values() if len(v) > 1]
        print(f"  {name}: {ties if ties else 'none'}")


if __name__ == "__main__":
    main()
