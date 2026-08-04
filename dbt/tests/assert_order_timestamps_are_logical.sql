{{ config(severity='warn') }}

select order_id
from {{ ref('stg_orders') }}
where customer_delivered_at < purchased_at
   or customer_delivered_at < carrier_delivered_at
   or carrier_delivered_at < purchased_at
