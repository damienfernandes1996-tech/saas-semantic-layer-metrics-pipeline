"""Interroge la couche sémantique (MetricFlow) et exporte CSV + graphiques."""
import shutil, subprocess, os, sys
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
DBT = ROOT / "dbt_project"
MF = shutil.which("mf") if "metafont" not in (shutil.which("mf") or "") else None
MF = "/usr/local/bin/mf" if os.path.exists("/usr/local/bin/mf") else MF


def mf(metrics, group_by, out, where=None):
    cmd = [MF, "query", "--metrics", metrics, "--group-by", group_by,
           "--order", group_by.split(",")[0], "--csv", str(out)]
    if where:
        cmd += ["--where", where]
    subprocess.run(cmd, cwd=DBT, env={**os.environ, "DBT_PROFILES_DIR": "."}, check=True,
                   stdout=subprocess.DEVNULL)
    return pd.read_csv(out)


def main():
    ex, fig = ROOT / "exports", ROOT / "docs" / "figures"
    ex.mkdir(exist_ok=True); fig.mkdir(parents=True, exist_ok=True)

    m = mf("mrr,arr,active_customers,arpa,churned_customers,lost_mrr,customer_churn_rate",
           "metric_time__month", ex / "kpi_monthly.csv")
    m["metric_time__month"] = pd.to_datetime(m["metric_time__month"])
    seg = mf("mrr", "metric_time__month,customer__segment", ex / "mrr_by_segment.csv")
    seg["metric_time__month"] = pd.to_datetime(seg["metric_time__month"])
    pl = mf("mrr", "metric_time__month,plan__plan_name", ex / "mrr_by_plan.csv")
    pl["metric_time__month"] = pd.to_datetime(pl["metric_time__month"])

    plt.rcParams.update({"axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 130})

    s = seg.pivot(index="metric_time__month", columns="customer__segment", values="mrr")
    ax = s.plot.area(figsize=(9, 4.5), alpha=.85)
    ax.set(title="MRR par segment (métrique `mrr` de la couche sémantique)", xlabel="", ylabel="€ / mois")
    plt.tight_layout(); plt.savefig(fig / "mrr_by_segment.png"); plt.close()

    p = pl.pivot(index="metric_time__month", columns="plan__plan_name", values="mrr")
    ax = p.plot.area(figsize=(9, 4.5), alpha=.85)
    ax.set(title="MRR par plan", xlabel="", ylabel="€ / mois")
    plt.tight_layout(); plt.savefig(fig / "mrr_by_plan.png"); plt.close()

    fig2, axes = plt.subplots(1, 2, figsize=(11, 4))
    axes[0].plot(m["metric_time__month"], m["arpa"]); axes[0].set_title("ARPA (ratio MRR / clients actifs)")
    axes[1].plot(m["metric_time__month"], m["customer_churn_rate"] * 100, color="C3")
    axes[1].set_title("Taux de churn mensuel (%)")
    plt.tight_layout(); plt.savefig(fig / "arpa_churn.png"); plt.close()
    print("Exports et figures générés.")


if __name__ == "__main__":
    main()
