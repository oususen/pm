# 7-App Structure (v1)

This project is organized into seven functional domains for easier search and maintenance.

## Domains
- orders (受注)
- production (生産)
- purchase (仕入)
- shipping (出荷)
- inventory (在庫)
- quality (品質)
- masters (マスタ)

## Backend (Django)
- `pm_backend/orders/` is the primary app container.
  - Domain packages live in `pm_backend/orders/domains/`.
  - Aggregators keep legacy import paths working:
    - `pm_backend/orders/models.py`
    - `pm_backend/orders/serializers.py`
    - `pm_backend/orders/views.py`

Domain mapping:
- orders: `pm_backend/orders/domains/orders/`
  - models/serializers/views/services for order intake and staging
- production: `pm_backend/orders/domains/production/`
  - planning, realtime, backlog, gantt, and execution APIs
- shipping: `pm_backend/orders/domains/shipping/`
  - shipment actuals + shipping order document services
- inventory: `pm_backend/orders/domains/inventory/`
  - placeholder; `inventory_calculator.py` is used by production APIs
- quality: `pm_backend/orders/domains/quality/`
  - placeholder; scrap models grouped here
- purchase: `pm_backend/orders/domains/purchase/`
  - placeholder
- masters: `pm_backend/masters/`

## Frontend (Vue)
- Views: `pm-ui/src/views/`
  - `orders/`, `production/`, `purchase/`, `shipping/`, `masters/`
  - `inventory/` (placeholder menu + moved inventory screens)
  - `quality/` (placeholder menu)
- Routers: `pm-ui/src/router/`
  - `orders.js`, `production.js`, `purchase.js`, `shipping.js`, `masters.js`
  - `inventory.js`, `quality.js`
- Navigation: `pm-ui/src/components/GlobalNavigation.vue`, `pm-ui/src/components/SideMenu.vue`

Notes:
- Inventory/quality routes are placeholders. Existing inventory screens are kept for future use.
