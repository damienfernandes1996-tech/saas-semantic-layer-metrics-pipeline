select
    i.invoice_id,
    i.subscription_id,
    i.customer_id,
    s.plan_id,
    i.invoice_date,
    i.amount
from {{ ref('silver_invoices') }} i
join {{ ref('silver_subscriptions') }} s using (subscription_id)
where i.status = 'paid'
