select
    nullif(trim(seller_id), '') as seller_id,
    nullif(trim(seller_zip_code_prefix), '') as seller_zip_code_prefix,
    coalesce(nullif(trim(seller_city), ''), 'unknown') as seller_city,
    coalesce(nullif(trim(seller_state), ''), 'unknown') as seller_state
from {{ source('olist_raw', 'sellers') }}
