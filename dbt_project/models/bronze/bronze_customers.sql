{#- BRONZE : copie fidèle de la source, tout en texte, + métadonnées d'ingestion. -#}
select
    *,
    'customers.csv' as _source_file,
    current_timestamp as _ingested_at
from read_csv('{{ var("raw_data_path") }}/customers.csv', header = true, all_varchar = true)
