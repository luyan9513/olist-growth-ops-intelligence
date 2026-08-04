with ranked as (
    select
        *,
        count(*) over (partition by order_id) as review_record_count,
        row_number() over (
            partition by order_id
            order by review_created_at desc nulls last, review_answered_at desc nulls last, review_id desc
        ) as review_rank
    from {{ ref('stg_order_reviews') }}
    where review_score between 1 and 5
)

select
    order_id,
    review_id,
    review_score,
    review_created_at,
    review_answered_at,
    review_record_count,
    review_score <= 2 as is_low_review
from ranked
where review_rank = 1
