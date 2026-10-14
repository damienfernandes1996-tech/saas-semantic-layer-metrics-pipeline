select
    *,
    'subscriptions.csv' as _source_file,
    current_timestamp as _ingested_at
from read_csv('{{ var("raw_data_path") }}/subscriptions.csv', header = true, all_varchar = true)
