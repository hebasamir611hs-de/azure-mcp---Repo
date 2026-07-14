# Asiacell eCommerce Platform (AsiaMall) — Project Background

> Context for all QA analysis. Read this before analyzing any feature. Items marked
> *(confirm)* are assumptions — verify and correct them as you learn the system.

## Company / Domain
**Asiacell** is an **Iraqi telecommunications operator**. The digital eCommerce system
(**AsiaMall** — asiamall.asiacell.com) covers device sales, SIM purchase & swap, digital
vouchers, partner integrations, and telecom product ordering — delivered via a
**Magento 2-based web storefront**, a **headless API layer** (in active development),
a **mobile webview** embedded in the Asiacell/ODP app, and an **admin backend**
(Magento admin + vendor portal).

## Platforms (Surfaces)
- **Web Storefront** — the AsiaMall website (desktop + responsive mobile), built on
  Magento 2. All customer-facing shopping, checkout, SIM, and voucher journeys.
- **Headless API Layer** — REST APIs being developed to decouple the frontend from
  Magento (Homepage, Category, PDP, Cart, Checkout, SIM, Voucher). Currently under
  the "Headless Implementation" sprint.
- **Mobile (Webview)** — AsiaMall accessed inside the Asiacell ODP mobile app via
  webview; SSO login from the app, Adjust SDK event tracking. Not a standalone native
  app — it is the web storefront rendered in-app.
- **Admin / CMS** — Magento 2 admin panel: product management, vendor management,
  order management, reporting, banner/content scheduling, coupon/promo configuration,
  flash-sale popups, SEO settings.
- **Vendor Portal** — separate login for third-party sellers: product CRUD, order view,
  stock management, notifications.

## Services / Products

### 1. SIM Purchase & Number Reservation
Users purchase new SIM lines (Prepaid, Yooz, Yooz 1M, Yooz Silver, Gold, etc.),
select/reserve mobile numbers (regular or vanity), and complete checkout with delivery
or store pickup. Includes eSIM provisioning with eKYC/KYC-at-delivery.
- Key flows: number selection → reservation (with lock timer) → checkout → payment →
  delivery/pickup → SIM activation.
- Integrations: Asiacell SIM provisioning API, Alsaree3/Talabati delivery, eKYC service.

### 2. SIM Swap
Existing Asiacell subscribers swap their SIM for the same MSISDN. Includes free campaign
SIM swap (eligibility checked via TMF Customer Management API).
- Key flows: enter MSISDN → eligibility check → checkout → payment → delivery.

### 3. Device & Product Sales
Physical products: mobiles, accessories, routers, Mi-Fi devices, lifestyle products.
Multi-vendor marketplace with configurable products (color/storage variants), vendor
price comparison widget, and stock management (Wincash integration for live inventory).
- Key flows: browse catalog → PDP (vendor selection, variant selection) → add to cart →
  checkout → payment → delivery/pickup.

### 4. Digital Vouchers
Purchase of digital voucher/license/subscription products from multiple partners
(Karti Store, etc.). Server-side redirection to partner, multi-vendor voucher support.
- Key flows: select voucher product → select partner → purchase → receive voucher
  via SMS/email.

### 5. Checkout & Payment
Unified checkout supporting logged-in and guest users. Multiple payment methods:
- **DCB (Direct Carrier Billing)** — charge to Asiacell account.
- **Asiapay** — eWallet with dynamic QR for desktop, deep-link for mobile.
- **Cash on Delivery (COD)**.
- **Online Payment** — card-based.
- Selective checkout (choose which cart items to purchase).
- Delivery methods: home delivery (Google Maps address), store pickup.

### 6. User Account & Auth
Registration (email or mobile+OTP), login (email+password, mobile+OTP, social login
via Google/FB/Twitter/Instagram, SSO from ODP app, quick-login on Asiacell network).
Profile management, order history, address book, avatar/photo upload.

### 7. Promotions & Marketing
Flash-sale popups (banner-type and product-specific with countdown timer), coupon codes
(vendor-restricted), pre-orders, price-drop notifications, abandoned-cart recovery,
affiliate program, CVM recommendation engine (persona-based for logged-in users).

### 8. Partners & Integrations
Air & Travel partner products (token-based redirect), Kaspersky license products,
iCenter CSV integration, Rehlat Alsafari popup.

### 9. Admin / CMS
Magento admin for content, product, order, vendor, and reporting management. Includes:
banner scheduling, product reporting (seller-wise), order reports (item-wise, SKU),
SEO management, flash-sale configuration, delivery fee rules, B2B group management.

### 10. Vendor Management
Vendor registration, login (OTP), product CRUD with admin approval, order management,
stock/price update API (token-authenticated), notifications, multi-seller product
assignment.

## Service ↔ Platform Matrix

| Service | Web Storefront | Mobile (Webview) | Headless API | Admin/CMS | Vendor Portal |
|---|---|---|---|---|---|
| SIM Purchase & Reservation | ✅ | ✅ | ✅ (API) | configured | — |
| SIM Swap | ✅ | ✅ | ✅ (API) | configured | — |
| Device & Product Sales | ✅ | ✅ | ✅ (API) | configured | ✅ manages |
| Digital Vouchers | ✅ | ✅ | <!-- TODO: confirm with QA Lead --> | configured | — |
| Checkout & Payment | ✅ | ✅ | ✅ (API) | configured | — |
| User Account & Auth | ✅ | ✅ (SSO) | ✅ (API) | — | — |
| Promotions & Marketing | ✅ | ✅ | <!-- TODO: confirm with QA Lead --> | ✅ configures | — |
| Partners | ✅ | ✅ | — | ✅ configures | — |
| Admin / Reporting | — | — | — | ✅ | — |
| Vendor Management | — | — | ✅ (stock API) | ✅ approves | ✅ |

## Core Business Objects
- **Customer** — registered (email or mobile) or guest buyer.
- **MSISDN / Mobile Number** — the Asiacell number (regular or vanity); locked during
  reservation with a configurable timer.
- **SIM** — physical SIM or eSIM, tied to an MSISDN and a SIM type (Prepaid/Yooz/etc.).
- **Product** — simple or configurable (variants: color, storage); can be multi-vendor.
- **Vendor / Seller** — third-party marketplace seller with own portal.
- **Cart** — standard Magento cart with selective checkout capability.
- **Order** — placed order with status tracking, delivery partner integration.
- **Payment Transaction** — DCB, Asiapay, COD, or online card payment.
- **Digital Voucher** — license/subscription code delivered electronically.
- **Delivery** — home delivery (Talabati/Alsaree3) or store pickup; location-based
  availability from Wincash.
- **Coupon / Promotion** — discount codes, flash-sale rules, price-drop alerts.
- **Affiliate** — customer enrolled in the affiliate/commission program.
- **Review** — product review with rating (approval workflow in admin).

## User Roles
- **Guest** — unauthenticated visitor; can browse, add to cart, guest checkout
  (limited to non-Asiacell products).
- **Registered Customer** — email or mobile-registered; full access to SIM purchase,
  device purchase, order history, profile, reviews, affiliate program.
- **Asiacell Subscriber** — registered customer with an Asiacell MSISDN; can use
  DCB payment, quick-login, SIM swap, number reservation.
- **Vendor / Seller** — third-party seller with vendor portal access.
- **Admin** — Magento admin managing products, orders, content, vendors, reports.
- *(Confirm / add: Asiacell business team roles, delivery partner staff, finance.)*

## Integrations
- **Asiacell SIM Provisioning API** — SIM activation, number reservation, lock/unlock.
- **TMF Forum Customer Management API** — eligibility check for SIM swap campaigns.
- **Asiapay** — eWallet payment (QR code for desktop, deep-link for mobile).
- **DCB Gateway** — direct carrier billing to Asiacell account.
- **Online Payment Gateway** — card payments. <!-- TODO: confirm with QA Lead — provider name -->
- **Talabati** — delivery partner with location-based availability check.
- **Alsaree3** — alternative delivery partner.
- **Wincash** — live inventory/stock system for Asiacell products (store-wise).
- **iCenter** — partner product sync via CSV/API (SKU, stock, price).
- **Karti Store** — digital voucher partner API.
- **eKYC Provider** — ID upload, facial recognition, liveness for SIM purchase.
- **Adjust SDK** — mobile analytics/event tracking (add-to-cart, view-item).
- **Google Tag Manager** — web event tracking.
- **Meta (Facebook/Instagram)** — product catalog sync for social commerce.
- **CVM Recommendation Engine** — persona-based product recommendations.
- **OTP/SMS Provider** — authentication and order notifications.
- **Push Notifications** — app alerts. <!-- TODO: confirm with QA Lead — provider -->

## Environments *(confirm)*
Dev / Staging / UAT / Prod — confirm which exist and how they differ.
URL: asiamall.asiacell.com (prod).

## Compatibility & Localization
- **Web:** desktop + responsive mobile browsers — *(confirm minimum browser versions)*.
- **Mobile Webview:** iOS + Android via ODP app — *(confirm minimum OS versions)*.
- **Languages:** Arabic (RTL) and English — confirmed (translation CRs in backlog).
  Kurdish — *(confirm if supported)*.

## Notes / To Confirm
- Exact DCB flow and provider (is it Asiacell internal or third-party gateway?).
- Whether Asiapay is used only for Asiacell-product vendors or all vendors.
- Delivery fee rules: per-vendor, per-province, free-above-threshold — confirm
  current configuration.
- Wincash inventory sync frequency (real-time or batch).
- eSIM provisioning: is eKYC mandatory for all SIM types or only certain categories?
- B2B customer group restrictions on checkout (shipping methods, payment methods).
