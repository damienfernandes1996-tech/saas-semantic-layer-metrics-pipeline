{#- Churn = fin d'abonnement sans reprise (un upgrade redémarre un abonnement à la date de fin précédente). -#}
with seq as (
    select
        s.*,
        lead(start_date) over (partition by customer_id order by start_date) as next_start
    from {{ ref('silver_subscriptions') }} s
)
select
    subscription_id || '-churn' as churn_id,
    customer_id,
    plan_id,
    end_date as churn_date,
    p.monthly_price as lost_mrr
from seq
join {{ ref('silver_plans') }} p using (plan_id)
where end_date is not null
  and (next_start is null or next_start <> end_date)
