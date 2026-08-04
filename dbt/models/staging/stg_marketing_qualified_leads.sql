select
    nullif(trim(mql_id), '') as mql_id,
    try_cast(first_contact_date as timestamp) as first_contact_at,
    coalesce(nullif(trim(landing_page_id), ''), 'unknown') as landing_page_id,
    coalesce(nullif(trim(origin), ''), 'unknown') as origin,
    nullif(trim(origin), '') is null as is_origin_missing
from {{ source('olist_raw', 'marketing_qualified_leads') }}
