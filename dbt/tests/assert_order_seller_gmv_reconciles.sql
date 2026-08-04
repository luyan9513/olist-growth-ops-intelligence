with source_total as (
    select sum(price + freight_value) as gross_value
    from {{ ref('stg_order_items') }}
), modeled_total as (
    select sum(gross_value) as gross_value
    from {{ ref('int_order_seller_items') }}
)

select source_total.gross_value as source_gmv, modeled_total.gross_value as modeled_gmv
from source_total cross join modeled_total
where abs(source_total.gross_value - modeled_total.gross_value) > 0.01
