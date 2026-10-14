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

last = kpi.iloc[-1]; prev12 = kpi.iloc[-13]
ymonth = last["month"]
def sub(df, col, key): return df[df.month == ymonth].set_index(col)[key].sort_values(ascending=False)
c3 = kpi.tail(3)["customer_churn_rate"].mean()
data = {
    "months": kpi["month"].tolist(),
    "kpi": {c: kpi[c].round(4).tolist() for c in kpi.columns if c != "month"},
    "seg": {s: seg[seg.customer__segment == s].set_index("month")["mrr"].reindex(kpi["month"]).fillna(0).tolist() for s in seg.customer__segment.unique()},
    "plan": {s: plan[plan.plan__plan_name == s].set_index("month")["mrr"].reindex(kpi["month"]).fillna(0).tolist() for s in plan.plan__plan_name.unique()},
    "country": sub(ctry, "customer__country", "mrr").round(0).to_dict(),
    "industry": sub(ind, "customer__industry", "mrr").round(0).to_dict(),
    "churn_seg": churn_seg.groupby("customer__segment")[["churned_customers", "lost_mrr"]].sum().to_dict("index"),
    "nrr_months": nrr["month"].tolist(), "nrr": nrr["nrr"].tolist(), "logo": nrr["logo_retention"].tolist(),
    "cards": {
        "mrr": float(last["mrr"]), "mrr_yoy": float(last["mrr"] / prev12["mrr"] - 1),
        "arr": float(last["arr"]), "active": int(last["active_customers"]),
        "active_yoy": float(last["active_customers"] / prev12["active_customers"] - 1),
        "arpa": float(last["arpa"]), "arpa_yoy": float(last["arpa"] / prev12["arpa"] - 1),
        "churn3": float(c3), "nrr": float(nrr["nrr"].iloc[-1]), "logo": float(nrr["logo_retention"].iloc[-1]),
        "month": ymonth,
    },
}
chartjs = (ROOT / "scripts" / "vendor" / "chart.umd.js").read_text()
tpl = (ROOT / "scripts" / "dashboard_template.html").read_text()
html = tpl.replace("/*CHARTJS*/", chartjs).replace("/*DATA*/", "const D = " + json.dumps(data) + ";")
(ROOT / "docs").mkdir(exist_ok=True)
(ROOT / "docs" / "dashboard.html").write_text(html)
print("docs/dashboard.html écrit", len(html) // 1024, "Ko")
