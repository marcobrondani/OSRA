#!/usr/bin/env python3
"""
OSRA weight sensitivity check.

Re-scores every calibration finding under alternative weights for the two
weighted factors, regulatory exposure and blast radius, and reports whether
the ranking changes. Categories are not tested here because they come from the
three convergence conditions, not from the score; the category of each finding
is recorded as data and the ranking is taken within the category order, as the
architecture document (Phase 4, Step 4.3) specifies.

Run:  python3 weight_sensitivity.py
Data: the per-factor scores published in OSRA_Scoring_Calibration and the
EuroBank Sentinel worked example, all on six factors.

Factor order in each row: regulatory exposure, detection deficit, trust depth,
blast radius, remediation complexity, materialisation horizon. The horizon for
the four original calibration scenarios was added in v1.2 (see the calibration
document, v1.2 six-factor rescoring). Five-factor totals, which drop the
horizon, are printed for comparison with the tables scored before it existed.
"""

from itertools import combinations

CATEGORY_ORDER = {
    "Critical Convergence": 0,
    "Convergence Point": 1,
    "Concentration Risk": 2,
}

CC, CP, CR = "Critical Convergence", "Convergence Point", "Concentration Risk"

SCENARIOS = {
    "EuroBank Sentinel (finance)": {
        "CP1 base model behaviour change": (CC, (5, 5, 4, 5, 4, 5)),
        "CP2 sanctions data integrity": (CC, (5, 5, 3, 5, 3, 5)),
        "CP3 co-located monitoring": (CC, (4, 5, 4, 5, 4, 3)),
        "CP4 vendor knowledge concentration": (CP, (3, 2, 3, 3, 3, 2)),
        "CP5 GPU silent data corruption": (CP, (3, 5, 2, 2, 4, 5)),
    },
    "StreamPay (digital services)": {
        "SP-CP1 LLM API dependency": (CC, (5, 4, 4, 5, 5, 5)),
        "SP-CP2 device fingerprinting": (CC, (3, 4, 3, 3, 3, 5)),
        "SP-CP3 RAG database integrity": (CP, (3, 3, 1, 4, 2, 5)),
        "SP-CP4 cross-border regulatory": (CP, (4, 2, 2, 3, 4, 1)),
    },
    "MedAssist (healthcare)": {
        "MH-CP1 model opacity": (CC, (5, 5, 5, 5, 5, 5)),
        "MH-CP4 physician over-reliance": (CC, (5, 5, 3, 5, 5, 5)),
        "MH-CP2 EHR integration fragility": (CC, (4, 4, 3, 4, 4, 5)),
        "MH-CP3 MDR certification scope": (CP, (4, 2, 3, 3, 3, 2)),
        "MH-CP5 cross-border patient data": (CP, (3, 2, 2, 2, 3, 1)),
    },
    "RouteOptima (logistics)": {
        "TL-CP1 maps platform dependency": (CC, (2, 4, 3, 4, 4, 5)),
        "TL-CP3 fleet GPS data": (CC, (2, 3, 2, 3, 2, 5)),
        "TL-CP2 demand model drift": (CP, (2, 3, 1, 4, 2, 5)),
        "TL-CP5 weather data quality": (CP, (1, 3, 2, 2, 1, 5)),
        "TL-CP4 single-region concentration": (CR, (2, 1, 1, 5, 4, 3)),
    },
    "GridSense (energy)": {
        "NW-CP1 OEM total dependency": (CC, (4, 5, 5, 5, 5, 5)),
        "NW-CP4 maintenance decision risk": (CC, (5, 4, 4, 4, 4, 5)),
        "NW-CP2 offshore connectivity": (CC, (3, 4, 3, 4, 4, 3)),
        "NW-CP3 training data mismatch": (CC, (3, 4, 4, 3, 3, 5)),
        "NW-CP5 grid reporting": (CP, (3, 2, 2, 2, 2, 3)),
    },
    "Autopilot (IT managed services, agentic)": {
        "AO-CP1 model provider tool-use behaviour": (CC, (4, 5, 4, 5, 4, 5)),
        "AO-CP2 cross-tenant agent credentials": (CC, (5, 4, 2, 5, 3, 5)),
        "AO-CP3 community MCP server supply chain": (CC, (4, 5, 4, 4, 2, 3)),
        "AO-CP4 human approval effectiveness": (CC, (3, 5, 1, 5, 3, 5)),
        "AO-CP5 runbook knowledge base integrity": (CP, (3, 4, 1, 4, 2, 5)),
        "AO-CP6 secrets vault single point": (CR, (3, 1, 1, 4, 4, 3)),
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
    totals can be compared with the tables scored before the sixth factor."""
    reg, det, trust, blast, remed, horizon = factors
    total = reg * w_reg + det + trust + blast * w_blast + remed
    if not five_factor:
        total += horizon
    return total


def ranking(points, w_reg, w_blast):
    """Category order first, then score, then the tie-break in Step 4.3:
    regulatory exposure, blast radius, materialisation horizon, detection
    deficit. Findings still level after that are listed by name and need a
    practitioner's recorded decision."""

    def key(name):
        category, f = points[name]
        reg, det, _, blast, _, horizon = f
        return (CATEGORY_ORDER[category], -score(f, w_reg, w_blast), -reg, -blast, -horizon, -det, name)

    return sorted(points, key=key)


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
    print("Baseline scores (weights 1.5, 1.5)")
    print("| Scenario | Finding | Category | Six factors | Five factors |")
    print("|---|---|---|---|---|")
    for name, points in SCENARIOS.items():
        for k in ranking(points, *BASELINE):
            category, f = points[k]
            print(f"| {name} | {k} | {category} | {score(f, *BASELINE):.1f} | {score(f, *BASELINE, five_factor=True):.1f} |")
    print()
    print("| Scenario | Weights (reg, blast) | Ranking | Top finding unchanged | Kendall tau vs 1.5/1.5 |")
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
    # Cross-scenario comparison of scenario maxima on six factors. OSRA does not
    # recommend comparing scores across organisations; this is printed only to
    # show what the weights do to the cross-sector picture.
    print("| Weights (reg, blast) | Scenario maxima on six factors, high to low |")
    print("|---|---|")
    for w in WEIGHT_SETS:
        maxima = sorted(
            ((max(score(f, *w) for _, f in pts.values()), n) for n, pts in SCENARIOS.items()),
            reverse=True,
        )
        print(f"| {w[0]}, {w[1]} | " + ", ".join(f"{n.split(' (')[0]} {m:.1f}" for m, n in maxima) + " |")
    print()
    # Score ties within a category at the baseline, which the tie-break decides.
    print("Score ties within a category at baseline weights:")
    for name, points in SCENARIOS.items():
        seen = {}
        for k, (category, f) in points.items():
            seen.setdefault((category, score(f, *BASELINE)), []).append(k.split()[0])
        ties = [v for v in seen.values() if len(v) > 1]
        print(f"  {name}: {ties if ties else 'none'}")


if __name__ == "__main__":
    main()
