{#- Normalise les pays écrits de plusieurs façons (nom, code ISO, casse, espaces). -#}
{% macro clean_country(col) -%}
    case upper(trim({{ col }}))
        when 'FRANCE' then 'France'            when 'FR' then 'France'
        when 'GERMANY' then 'Germany'          when 'DE' then 'Germany'
        when 'SPAIN' then 'Spain'              when 'ES' then 'Spain'
        when 'ITALY' then 'Italy'              when 'IT' then 'Italy'
        when 'UNITED KINGDOM' then 'United Kingdom'
        when 'UK' then 'United Kingdom'        when 'GB' then 'United Kingdom'
        when 'NETHERLANDS' then 'Netherlands'  when 'NL' then 'Netherlands'
        when 'BELGIUM' then 'Belgium'          when 'BE' then 'Belgium'
        when 'SWITZERLAND' then 'Switzerland'  when 'CH' then 'Switzerland'
        else null
    end
{%- endmacro %}

{#- Lit une date au format ISO (AAAA-MM-JJ) ou JJ/MM/AAAA. -#}
{% macro parse_date(col) -%}
    coalesce(try_cast({{ col }} as date), cast(try_strptime({{ col }}, '%d/%m/%Y') as date))
{%- endmacro %}

{#- Convertit un montant texte ("49.00" ou "49,00") en décimal. -#}
{% macro parse_amount(col) -%}
    try_cast(replace({{ col }}, ',', '.') as decimal(10, 2))
{%- endmacro %}
