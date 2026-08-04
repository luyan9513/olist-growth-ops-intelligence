select
    nullif(trim(customer_id), '') as customer_id,
    nullif(trim(customer_unique_id), '') as customer_unique_id,
    nullif(trim(customer_zip_code_prefix), '') as customer_zip_code_prefix,
    coalesce(nullif(trim(customer_city), ''), 'unknown') as customer_city,
    coalesce(nullif(trim(customer_state), ''), 'unknown') as customer_state
from {{ source('olist_raw', 'customers') }}
