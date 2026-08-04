select
    i.seller_id,
    i.primary_category_name,
    date_trunc('week', o.purchased_at)::date as week_start,
    count(distinct i.order_id) as order_count,
    sum(i.item_count) as item_count,
    sum(i.gross_value) as gross_value
from {{ ref('int_order_seller_items') }} i
inner join {{ ref('int_order_enriched') }} o using (order_id)
where o.purchased_at is not null
  and o.order_status not in ('canceled', 'unavailable')
group by i.seller_id, i.primary_category_name, week_start
