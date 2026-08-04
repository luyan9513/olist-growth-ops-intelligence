{{ config(severity='warn') }}

select d.mql_id
from {{ ref('stg_closed_deals') }} d
inner join {{ ref('stg_marketing_qualified_leads') }} m using (mql_id)
where d.won_at < m.first_contact_at
