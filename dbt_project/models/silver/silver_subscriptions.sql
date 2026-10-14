{#- On écarte les abonnements incohérents (fin avant début). -#}
with typed as (
    select
        subscription_id,
        customer_id,
        plan_id,
        {{ parse_date('start_date') }} as start_date,
        {{ parse_date('nullif(end_date, \'\')') }} as end_date
    from {{ ref('bronze_subscriptions') }}
)
select * from typed
where end_date is null or end_date >= start_date
