"""Génère des fichiers CSV "bruts" d'une activité SaaS B2B par abonnement.

Toutes les données sont SYNTHÉTIQUES (aucune donnée réelle). Les fichiers sont
volontairement imparfaits, comme des exports de systèmes sources :
  - doublons de clients, pays écrits de plusieurs façons, secteur manquant ;
  - dates dans deux formats (ISO et JJ/MM/AAAA) ;
  - montants avec virgule décimale ;
  - factures en double, factures orphelines (abonnement inconnu) ;
  - abonnements dont la date de fin précède la date de début.
La couche silver du pipeline dbt a pour rôle de corriger tout cela.
"""

from __future__ import annotations

import argparse
import csv
import random
from datetime import date, timedelta
from pathlib import Path

PLANS = [("P1", "Starter", 49), ("P2", "Growth", 149), ("P3", "Scale", 399)]
PRICE = {p[0]: p[2] for p in PLANS}
MONTHLY_CHURN = {"P1": 0.040, "P2": 0.025, "P3": 0.012}
MONTHLY_UPGRADE = {"P1": 0.035, "P2": 0.020, "P3": 0.0}
NEXT_PLAN = {"P1": "P2", "P2": "P3"}

COUNTRIES = {
    "France": ["France", "france", "FR", " France "],
    "Germany": ["Germany", "germany", "DE"],
    "Spain": ["Spain", "ES", "spain"],
    "Italy": ["Italy", "IT"],
    "United Kingdom": ["United Kingdom", "UK", "GB"],
    "Netherlands": ["Netherlands", "NL"],
    "Belgium": ["Belgium", "BE"],
    "Switzerland": ["Switzerland", "CH"],
}
COUNTRY_WEIGHTS = [34, 18, 10, 8, 14, 7, 5, 4]
INDUSTRIES = ["Software", "Retail", "Healthcare", "Finance", "Manufacturing", "Logistics"]
SEGMENTS = {"SMB": 0.55, "Mid-Market": 0.33, "Enterprise": 0.12}
SEGMENT_CHURN = {"SMB": 1.35, "Mid-Market": 1.0, "Enterprise": 0.45}

# ---------- dynamique du business (événements datés) ----------
SCALE_LAUNCH = date(2023, 9, 1)  # le plan Scale n'existe pas avant


def in_range(d: date, a: date, b: date) -> bool:
    return a <= d <= b


def signup_weight(m: date) -> float:
    """Poids d'inscription d'un mois : tendance x saisonnalité x événements."""
    k = (m.year - 2023) * 12 + m.month - 1
    trend = 1.0 + 0.045 * k if k < 24 else 2.08 + 0.01 * (k - 24)  # croissance qui ralentit en 2025
    season = {1: 1.25, 2: 1.0, 3: 1.05, 4: 1.0, 5: 1.0, 6: 0.95, 7: 0.85,
              8: 0.55, 9: 1.35, 10: 1.25, 11: 1.0, 12: 0.7}[m.month]
    w = trend * season
    if in_range(m, date(2024, 3, 1), date(2024, 4, 30)):
        w *= 1.7          # campagne marketing / lancement produit
    if in_range(m, date(2025, 2, 1), date(2025, 4, 30)):
        w *= 0.65         # tassement du marché
    return w


def churn_multiplier(d: date) -> float:
    """Multiplicateur de churn selon la date (saisonnalité + chocs)."""
    mult = {1: 1.3, 12: 1.2, 8: 1.1}.get(d.month, 1.0)
    if in_range(d, date(2024, 7, 1), date(2024, 9, 30)):
        mult *= 2.3       # hausse de prix -> vague de résiliations
    if in_range(d, date(2025, 2, 1), date(2025, 3, 31)):
        mult *= 1.6       # arrivée d'un concurrent
    if d < date(2023, 7, 1):
        mult *= 0.5       # jeune base de clients, peu de résiliations au début
    return mult


def upgrade_multiplier(d: date) -> float:
    if in_range(d, date(2024, 10, 1), date(2024, 11, 30)):
        return 2.8        # campagne d'upsell
    return 1.0


PLAN_BY_SEGMENT = {
    "SMB": [("P1", 0.70), ("P2", 0.30)],
    "Mid-Market": [("P1", 0.20), ("P2", 0.60), ("P3", 0.20)],
    "Enterprise": [("P2", 0.30), ("P3", 0.70)],
}

START = date(2023, 1, 1)
END = date(2025, 12, 31)  # date d'arrêté des données


def add_months(d: date, n: int) -> date:
    y, m = divmod(d.month - 1 + n, 12)
    year, month = d.year + y, m + 1
    for day in (d.day, 30, 29, 28):
        try:
            return date(year, month, day)
        except ValueError:
            continue
    raise ValueError


def weighted(rng: random.Random, pairs):
    r, acc = rng.random(), 0.0
    for value, w in pairs:
        acc += w
        if r <= acc:
            return value
    return pairs[-1][0]


def generate(n_customers: int, seed: int, out: Path) -> dict:
    rng = random.Random(seed)
    out.mkdir(parents=True, exist_ok=True)

    customers, subscriptions, invoices = [], [], []
    sub_seq = inv_seq = 0
    months = [add_months(START, k) for k in range(35)]  # jan. 2023 -> nov. 2025
    month_w = [signup_weight(m) * rng.lognormvariate(0, 0.18) for m in months]  # bruit mensuel

    for i in range(1, n_customers + 1):
        cid = f"C{i:05d}"
        m0 = rng.choices(months, weights=month_w)[0]
        signup = m0 + timedelta(days=rng.randrange(0, 28))
        # mix de segments : grands comptes signés surtout en fin de trimestre, PME poussées par la campagne
        seg_w = dict(SEGMENTS)
        if signup.month in (3, 6, 9, 12):
            seg_w["Enterprise"] *= 2.4
        if in_range(signup, date(2024, 3, 1), date(2024, 4, 30)):
            seg_w["SMB"] *= 1.6
        tot = sum(seg_w.values())
        segment = weighted(rng, [(k, v / tot) for k, v in seg_w.items()])
        country = rng.choices(list(COUNTRIES), weights=COUNTRY_WEIGHTS)[0]
        industry = rng.choice(INDUSTRIES)
        customers.append(
            {
                "customer_id": cid,
                "company_name": f"Company {i:04d}",
                "segment": segment,
                "country": rng.choice(COUNTRIES[country]),
                "industry": "" if rng.random() < 0.05 else industry,
                "signup_date": signup.isoformat(),
            }
        )

        plan = weighted(rng, PLAN_BY_SEGMENT[segment])
        if plan == "P3" and signup < SCALE_LAUNCH:
            plan = "P2"
        sub_start = signup
        while True:
            sub_seq += 1
            sid = f"S{sub_seq:06d}"
            renewal = add_months(sub_start, 1)
            end_date, upgraded = None, False
            cursor, k = renewal, 1
            while cursor <= END:
                u = rng.random()
                p_churn = min(0.5, MONTHLY_CHURN[plan] * SEGMENT_CHURN[segment] * churn_multiplier(cursor))
                p_up = MONTHLY_UPGRADE[plan] * upgrade_multiplier(cursor)
                if plan == "P2" and cursor < SCALE_LAUNCH:
                    p_up = 0.0
                if u < p_churn:
                    end_date = cursor
                    break
                if u < p_churn + p_up:
                    end_date, upgraded = cursor, True
                    break
                k += 1
                cursor = add_months(sub_start, k)
            subscriptions.append(
                {
                    "subscription_id": sid,
                    "customer_id": cid,
                    "plan_id": plan,
                    "start_date": sub_start.isoformat(),
                    "end_date": end_date.isoformat() if end_date else "",
                    "status": "ended" if end_date else "active",
                }
            )
            # factures mensuelles : une par mois de service
            billing, j = sub_start, 0
            while billing <= END and (end_date is None or billing < end_date):
                inv_seq += 1
                status = rng.choices(["paid", "failed", "refunded"], weights=[94, 4, 2])[0]
                invoices.append(
                    {
                        "invoice_id": f"I{inv_seq:07d}",
                        "subscription_id": sid,
                        "invoice_date": billing,
                        "amount": PRICE[plan],
                        "status": status,
                    }
                )
                j += 1
                billing = add_months(sub_start, j)
            if upgraded:
                plan, sub_start = NEXT_PLAN[plan], end_date
            else:
                break

    # ---------- défauts de qualité volontaires ----------
    dup_customers = rng.sample(customers, k=int(0.02 * len(customers)))
    for c in dup_customers:
        customers.append({**c, "company_name": c["company_name"].upper()})

    bad_subs = rng.sample(
        [s for s in subscriptions if s["end_date"]], k=max(1, int(0.005 * len(subscriptions)))
    )
    for s in bad_subs:
        s["end_date"] = (date.fromisoformat(s["start_date"]) - timedelta(days=5)).isoformat()

    for inv in invoices:
        d = inv["invoice_date"]
        inv["invoice_date"] = d.strftime("%d/%m/%Y") if rng.random() < 0.02 else d.isoformat()
        inv["amount"] = (
            f"{inv['amount']},00" if rng.random() < 0.03 else f"{inv['amount']}.00"
        )
    dup_inv = rng.sample(invoices, k=int(0.01 * len(invoices)))
    invoices.extend(dict(i) for i in dup_inv)
    for i in rng.sample(invoices, k=int(0.003 * len(invoices))):
        i["subscription_id"] = "S999999"  # orphelines
    rng.shuffle(invoices)

    def dump(name: str, rows: list[dict]) -> None:
        with open(out / name, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)

    dump("plans.csv", [{"plan_id": p, "plan_name": n, "monthly_price": f"{pr}.00"} for p, n, pr in PLANS])
    dump("customers.csv", customers)
    dump("subscriptions.csv", subscriptions)
    dump("invoices.csv", invoices)
    return {
        "customers": len(customers),
        "subscriptions": len(subscriptions),
        "invoices": len(invoices),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--customers", type=int, default=1500)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", type=Path, default=Path("data/raw"))
    a = ap.parse_args()
    counts = generate(a.customers, a.seed, a.out)
    print(f"Fichiers bruts écrits dans {a.out} :", counts)


if __name__ == "__main__":
    main()
