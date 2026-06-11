# WOQOD — Project Background

> Context for all QA analysis. Read this before analyzing any feature. Items marked
> *(confirm)* are assumptions — verify and correct them as you learn the system.

## Company / Domain
WOQOD is a **Qatar-based company in the fuels and vehicles domain**. The digital
system covers fueling and payment, vehicle inspection & licensing, bookings, and
related services — delivered across a mobile app, several websites, and an admin
backend.

## Platforms (Surfaces)
- **Mobile App (iOS + Android)** — the unified app that contains **all** services
  (WOQOD Tag, FAHES, Booking, Qjet content).
- **Websites:**
  - **WOQOD website** — account and WOQOD Tag top-up.
  - **FAHES website** — vehicle inspection & licensing booking and payment.
  - **Qjet website** — Qjet service content.
- **CMS** — admin backend that controls content, settings, configuration, and logs
  for the WOQOD website, FAHES website, Qjet website, and the mobile app.

## Services / Products

### 1. WOQOD Tag
A **physical tag installed on the user's vehicle** that pairs with the **fuel gun** to
enable fueling and **payment at the pump** directly from the user's WOQOD account.
- Users **top up** their WOQOD account via the **mobile app** or the **WOQOD website**.
- Key flows: top-up, balance management, physical fueling + payment at the gun,
  transaction history.

### 2. FAHES
Vehicle **inspection and licensing** service. Users **book and pay separately** for
inspection/licensing of their vehicle, primarily through the **FAHES website**.
- Key flows: book an inspection/licensing appointment, pay, view/manage/track bookings.

### 3. Booking System
The system that **monitors and manages bookings** — users' bookings, vehicles,
appointment slots, holidays, and availability. Underpins FAHES and any other bookable
service.
- Key entities: booking, vehicle, appointment slot, holiday / availability calendar.

### 4. Qjet
A service under the WOQOD umbrella, surfaced as **content** on the **Qjet website**
(and within the mobile app).

### 5. CMS
Admin / control system to manage **content, settings, and configuration** for the
WOQOD website, FAHES website, Qjet website, and the mobile app — plus **logs** for
these services.
- Key flows: edit content, change settings/configuration per surface, view logs.

## Service ↔ Platform Matrix
*(Adjust where reality differs — e.g. if FAHES is also reachable from the WOQOD site.)*

| Service | Mobile App | WOQOD Web | FAHES Web | Qjet Web | CMS |
|---|---|---|---|---|---|
| WOQOD Tag (top-up / fuel / pay) | ✅ | ✅ | — | — | configured via CMS |
| FAHES (inspection / licensing) | ✅ | — | ✅ | — | configured via CMS |
| Booking | ✅ | — | ✅ | — | configured via CMS |
| Qjet (content) | ✅ | — | — | ✅ | configured via CMS |
| Content / settings / logs | (target) | (target) | (target) | (target) | ✅ controls all |

## Core Business Objects
- **User / Account** — the WOQOD customer and their account.
- **WOQOD Account Balance** — funds topped up, spent at the pump.
- **WOQOD Tag** — the physical device on the vehicle (paired to vehicle/account).
- **Vehicle** — the user's car(s).
- **Top-up Transaction** — adding funds (app / web).
- **Fueling Transaction** — fuel dispensed + payment at the gun.
- **FAHES Booking** — inspection / licensing appointment.
- **Payment** — top-up payment, FAHES payment.
- **Appointment Slot** — a bookable time.
- **Holiday / Availability** — calendar constraints on slots.
- **Content Item / Setting / Configuration** — CMS-managed.
- **Log Entry** — CMS-visible activity / records.

## User Roles
- **Guest** — unauthenticated visitor (browse content, limited actions).
- **Registered Customer** — has an account, tag, and vehicles; can top up, fuel, and book.
- **CMS Admin** — manages content / settings / configuration / logs across surfaces.
- *(Confirm / add: FAHES staff or inspector, corporate accounts, finance roles, etc.)*

## Integrations *(confirm)*
- **Payment gateway** — top-up and FAHES payments.
- **Fuel pump / tag system** — physical tag ↔ pump authorization at the station.
- **OTP / SMS provider** — authentication / verification.
- **Push notifications** — app alerts.
- *(Add: ERP/SAP, maps, identity provider, etc., if applicable.)*

## Environments *(confirm)*
Dev / QA / UAT / Prod — confirm which exist and how they differ.

## Compatibility & Localization
- **Mobile:** iOS and Android — *(confirm minimum OS versions and device classes.)*
- **Web:** supported browsers — *(confirm.)*
- **Languages:** Arabic (RTL) and English — *(confirm full coverage.)*

## Notes / To Confirm
- Exact split of services across the WOQOD vs FAHES vs Qjet websites.
- Whether top-up and fueling payment use the same gateway.
- Tag pairing / registration flow (who installs it, how it links to a vehicle/account).
- Booking rules: cancellation, rescheduling, no-show, holiday blocking.
