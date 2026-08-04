select
    nullif(trim(mql_id), '') as mql_id,
    nullif(trim(seller_id), '') as seller_id,
    nullif(trim(sdr_id), '') as sdr_id,
    nullif(trim(sr_id), '') as sr_id,
    try_cast(won_date as timestamp) as won_at,
    coalesce(nullif(trim(business_segment), ''), 'unknown') as business_segment,
    coalesce(nullif(trim(lead_type), ''), 'unknown') as lead_type,
    coalesce(nullif(trim(lead_behaviour_profile), ''), 'unknown') as lead_behaviour_profile,
    coalesce(nullif(trim(business_type), ''), 'unknown') as business_type,
    try_cast(declared_product_catalog_size as integer) as declared_product_catalog_size,
    try_cast(declared_monthly_revenue as double) as declared_monthly_revenue
from {{ source('olist_raw', 'closed_deals') }}
