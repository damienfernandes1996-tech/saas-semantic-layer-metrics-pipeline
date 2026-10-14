{#- SILVER : typage, normalisation des pays, dédoublonnage (on garde la ligne "propre", non écrite en MAJUSCULES). -#}
with ranked as (
    select
        customer_id,
        company_name,
        segment,
        {{ clean_country('country') }} as country,
        nullif(trim(industry), '') as industry,
        {{ parse_date('signup_date') }} as signup_date,
        row_number() over (
            partition by customer_id
            order by (company_name = upper(company_name)), company_name
        ) as rn
    from {{ ref('bronze_customers') }}
)
select customer_id, company_name, segment, country, coalesce(industry, 'Unknown') as industry, signup_date
from ranked
where rn = 1
