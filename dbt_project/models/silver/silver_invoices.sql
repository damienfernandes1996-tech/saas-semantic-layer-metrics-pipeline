{#- Dédoublonnage des factures, dates/montants normalisés, rejet des factures orphelines. -#}
with typed as (
    select
        invoice_id,
        subscription_id,
        {{ parse_date('invoice_date') }} as invoice_date,
        {{ parse_amount('amount') }} as amount,
        status,
        row_number() over (partition by invoice_id order by invoice_date) as rn
    from {{ ref('bronze_invoices') }}
)
select t.invoice_id, t.subscription_id, s.customer_id, t.invoice_date, t.amount, t.status
from typed t
join {{ ref('silver_subscriptions') }} s using (subscription_id)
where t.rn = 1
