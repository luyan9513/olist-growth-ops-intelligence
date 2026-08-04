select
    nullif(trim(review_id), '') as review_id,
    nullif(trim(order_id), '') as order_id,
    try_cast(review_score as integer) as review_score,
    try_cast(review_creation_date as timestamp) as review_created_at,
    try_cast(review_answer_timestamp as timestamp) as review_answered_at
from {{ source('olist_raw', 'order_reviews') }}
