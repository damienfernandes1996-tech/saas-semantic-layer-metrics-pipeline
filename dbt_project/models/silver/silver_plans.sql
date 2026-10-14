select
    plan_id,
    plan_name,
    {{ parse_amount('monthly_price') }} as monthly_price
from {{ ref('bronze_plans') }}
