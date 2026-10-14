{#- Snapshot mensuel : 1 ligne par abonnement actif à chaque fin de mois. -#}
with months as (
    select cast(last_day(d) as date) as snapshot_month
    from generate_series(date '2023-01-01', date '2025-12-01', interval 1 month) as t(d)
)
select
    s.subscription_id || '-' || strftime(m.snapshot_month, '%Y%m') as snapshot_id,
    m.snapshot_month,
    s.subscription_id,
    s.customer_id,
    s.plan_id,
    p.monthly_price as mrr
from months m
join {{ ref('silver_subscriptions') }} s
  on s.start_date <= m.snapshot_month
 and (s.end_date is null or s.end_date > m.snapshot_month)
join {{ ref('silver_plans') }} p using (plan_id)
