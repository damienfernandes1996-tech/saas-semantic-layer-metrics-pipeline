select plan_id, plan_name, monthly_price
from {{ ref('silver_plans') }}
