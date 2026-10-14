# Catalogue de métriques

_Généré automatiquement depuis `semantic_manifest.json`._

| Métrique | Type | Définition |
|---|---|---|
| `active_customers` | simple | mesure `active_customers`  |
| `active_customers_prev_month` | derived | `prev`  |
| `arpa` | ratio | `mrr` / `active_customers` — Average Revenue Per Account = MRR / clients actifs. |
| `arr` | derived | `mrr * 12` — Annual Recurring Revenue = MRR x 12. |
| `churned_customers` | simple | mesure `churned_customers`  |
| `customer_churn_rate` | ratio | `churned_customers` / `active_customers_prev_month` — Clients perdus du mois / clients actifs fin du mois précédent. |
| `lost_mrr` | simple | mesure `lost_mrr`  |
| `mrr` | simple | mesure `mrr` — Monthly Recurring Revenue (fin de période). |
| `new_customers` | simple | mesure `new_customers`  |
| `revenue` | simple | mesure `revenue_amount`  |

## Modèles sémantiques

| Modèle | Entités | Dimensions | Mesures |
|---|---|---|---|
| customers | customer | segment, country, industry, signup_date | new_customers |
| plans | plan | plan_name |  |
| mrr_snapshot | snapshot, subscription, customer, plan | snapshot_month | mrr, active_customers |
| churn | churn, customer, plan | churn_date | churned_customers, lost_mrr |
| invoices | invoice, customer, plan | invoice_date | revenue_amount |
