"""Construit docs/dashboard.html (autonome) à partir de la couche sémantique MetricFlow."""
import json, os, subprocess
from pathlib import Path
import duckdb, pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DBT = ROOT / "dbt_project"
MF = "/usr/local/bin/mf" if os.path.exists("/usr/local/bin/mf") else "mf"
TMP = ROOT / "exports"
TMP.mkdir(exist_ok=True)


def mf(metrics, group_by, name):
    out = TMP / f"{name}.csv"
    subprocess.run([MF, "query", "--metrics", metrics, "--group-by", group_by, "--order",
                    group_by.split(",")[0], "--csv", str(out)], cwd=DBT, check=True,
                   env={**os.environ, "DBT_PROFILES_DIR": "."}, stdout=subprocess.DEVNULL)
    df = pd.read_csv(out)
    df.columns = [c.replace("metric_time__month", "month") for c in df.columns]
    df["month"] = pd.to_datetime(df["month"]).dt.strftime("%Y-%m")
    return df[(df.month >= "2023-01") & (df.month <= "2025-12")]


kpi = mf("mrr,arr,active_customers,arpa,new_customers,churned_customers,lost_mrr,customer_churn_rate,revenue",
         "metric_time__month", "kpi_monthly").fillna(0).reset_index(drop=True)
seg = mf("mrr", "metric_time__month,customer__segment", "mrr_by_segment")
plan = mf("mrr", "metric_time__month,plan__plan_name", "mrr_by_plan")
ctry = mf("mrr,active_customers", "metric_time__month,customer__country", "mrr_by_country")
ind = mf("mrr", "metric_time__month,customer__industry", "mrr_by_industry")
churn_seg = mf("churned_customers,lost_mrr", "metric_time__month,customer__segment", "churn_by_segment")

# NRR / rétention logo 12 mois : SQL sur la couche gold (hors métriques MetricFlow)
con = duckdb.connect(str(DBT / "warehouse.duckdb"), read_only=True)
nrr = con.sql("""
with m as (select snapshot_month, customer_id, sum(mrr) mrr from gold.fct_mrr_snapshot group by 1,2),
months as (select distinct snapshot_month from m)
select strftime(cur.snapshot_month, '%Y-%m') as month,
       round(100.0 * sum(c.mrr) / sum(p.mrr), 1) as nrr,
       round(100.0 * count(c.customer_id) / count(p.customer_id), 1) as logo_retention
from months cur
join m p on p.snapshot_month = last_day(cur.snapshot_month - interval 12 month)
left join m c on c.snapshot_month = cur.snapshot_month and c.customer_id = p.customer_id
group by cur.snapshot_month order by 1
""").df()
con.close()

months = kpi["month"].tolist()


def series(df, col, key):
    """{valeur: [série alignée sur months]} pour une dimension donnée."""
    out = {}
    for v in sorted(df[col].dropna().unique()):
        out[v] = df[df[col] == v].set_index("month")[key].reindex(months).fillna(0).round(2).tolist()
    return out


data = {
    "months": months,
    "kpi": {c: kpi[c].round(4).tolist() for c in kpi.columns if c != "month"},
    "seg": series(seg, "customer__segment", "mrr"),
    "plan": {k: series(plan, "plan__plan_name", "mrr")[k] for k in ["Starter", "Growth", "Scale"]},
    "country": series(ctry, "customer__country", "mrr"),
    "industry": series(ind, "customer__industry", "mrr"),
    "lost_seg": series(churn_seg, "customer__segment", "lost_mrr"),
    "churn_seg": series(churn_seg, "customer__segment", "churned_customers"),
    "nrr_months": nrr["month"].tolist(), "nrr": nrr["nrr"].tolist(), "logo": nrr["logo_retention"].tolist(),
}
chartjs = (ROOT / "scripts" / "vendor" / "chart.umd.js").read_text()
tpl = (ROOT / "scripts" / "dashboard_template.html").read_text()
html = tpl.replace("/*CHARTJS*/", chartjs).replace("/*DATA*/", "const D = " + json.dumps(data) + ";")
(ROOT / "docs").mkdir(exist_ok=True)
(ROOT / "docs" / "dashboard.html").write_text(html)
(ROOT / "docs" / "index.html").write_text(html)  # page d'accueil GitHub Pages
print("docs/dashboard.html écrit", len(html) // 1024, "Ko")
