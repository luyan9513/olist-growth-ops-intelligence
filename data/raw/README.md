# 原始数据目录

本目录不提交原始 CSV。请从 Olist 官方题目指向的数据页面获取公开匿名样本，并在遵守当时数据条款的前提下放入此目录。

必需文件：

- `olist_marketing_qualified_leads_dataset.csv`
- `olist_closed_deals_dataset.csv`
- `olist_sellers_dataset.csv`
- `olist_orders_dataset.csv`
- `olist_order_items_dataset.csv`
- `olist_order_payments_dataset.csv`
- `olist_order_reviews_dataset.csv`
- `olist_products_dataset.csv`
- `olist_customers_dataset.csv`

可选文件：

- `olist_geolocation_dataset.csv`
- `product_category_name_translation.csv`

放置后运行：

```bash
make manifest
```

命令会校验必需文件并在 `data/processed/raw_manifest.json` 生成文件大小和 SHA-256，不会复制或上传数据。
