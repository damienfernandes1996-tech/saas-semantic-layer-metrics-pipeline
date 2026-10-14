"""Vérifie que les résultats de la couche sémantique = SQL indépendant sur la couche gold."""
import os, subprocess
from pathlib import Path
import duckdb, pandas as pd, pytest

ROOT = Path(__file__).resolve().parents[1]
DBT = ROOT / "dbt_project"
MF = "/usr/local/bin/mf" if os.path.exists("/usr/local/bin/mf") else "mf"


def mf_query(metrics, group_by, tmp_path):
    out = tmp_path / "out.csv"
    subprocess.run([MF, "query", "--metrics", metrics, "--group-by", group_by, "--csv", str(out)],
                   cwd=DBT, env={**os.environ, "DBT_PROFILES_DIR": "."}, check=True, stdout=subprocess.DEVNULL)
    return pd.read_csv(out)


class _Con:
    """Connexion ouverte à la demande : DuckDB n'autorise qu'un accès à la fois avec MetricFlow."""
    def _run(self, q, fn):
        c = duckdb.connect(str(DBT / "warehouse.duckdb"), read_only=True)
        try:
            return fn(c.sql(q))
        finally:
            c.close()

    def sql(self, q):
        class R:
            def df(_s): return self._run(q, lambda r: r.df())
            def fetchone(_s): return self._run(q, lambda r: r.fetchone())
        return R()


@pytest.fixture
def con():
    return _Con()


def test_mrr_matches_sql(con, tmp_path):
    sl = mf_query("mrr", "metric_time__month", tmp_path)
    sl["m"] = pd.to_datetime(sl["metric_time__month"]).dt.strftime("%Y-%m")
    sql = con.sql("""select strftime(snapshot_month,'%Y-%m') m, sum(mrr) mrr
                     from gold.fct_mrr_snapshot group by 1""").df()
    merged = sl.merge(sql, on="m", suffixes=("_sl", "_sql"))
    assert len(merged) == len(sql) > 0
    assert (merged["mrr_sl"] == merged["mrr_sql"]).all()


def test_mrr_yearly_is_last_month_not_sum(con, tmp_path):
    """Mesure semi-additive : le MRR annuel = MRR de décembre, pas la somme des 12 mois."""
    sl = mf_query("mrr", "metric_time__year", tmp_path)
    sl["y"] = pd.to_datetime(sl["metric_time__year"]).dt.year
    sql = con.sql("""select 2025 y, sum(mrr) mrr from gold.fct_mrr_snapshot
                     where snapshot_month = date '2025-12-31'""").df().iloc[0]
    assert sl.loc[sl.y == 2025, "mrr"].iloc[0] == sql["mrr"]


def test_churned_customers_matches_sql(con, tmp_path):
    sl = mf_query("churned_customers", "metric_time__year", tmp_path)
    sl["y"] = pd.to_datetime(sl["metric_time__year"]).dt.year
    sql = con.sql("select year(churn_date) y, count(*) n from gold.fct_churn group by 1").df()
    merged = sl.merge(sql, on="y")
    assert (merged["churned_customers"] == merged["n"]).all() and len(merged) == len(sql)


def test_revenue_matches_sql(con, tmp_path):
    sl = mf_query("revenue", "metric_time__year", tmp_path)
    total = sl["revenue"].sum()
    assert abs(total - float(con.sql("select sum(amount) from gold.fct_invoices").fetchone()[0])) < 0.01


def test_arr_is_12x_mrr(tmp_path):
    df = mf_query("mrr,arr", "metric_time__month", tmp_path)
    assert (df["arr"] == df["mrr"] * 12).all()
