select customer_id, company_name, segment, country, industry, signup_date
from {{ ref('silver_customers') }}
