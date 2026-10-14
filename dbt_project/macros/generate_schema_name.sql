{#- Utilise directement le nom de schéma demandé (bronze, silver, gold)
    au lieu du préfixe par défaut "main_". -#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
