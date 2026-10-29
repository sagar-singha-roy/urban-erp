# Urban Integrated Municipal ERP — 19 Modules & Components Catalogue

Derived from:
- **Urban-ERP-SRS_v2.docx** (Product SRS v0.35, Hake Technologies)
- **Urban-Technical-Architecture_v2.docx** (Technical Architecture v0.1)
- **Urban-ERD-Diagrams-PNG** (Domain Entity-Relationship Diagrams)

---

## Executive Summary of the 19 Modules

| No. | Code | Module Name | Domain | Typical Owner Department | Component/Process Count |
|---|---|---|---|---|---|
| 1 | **PTX** | Property Tax & Revenue Management | Revenue & Billing | Revenue Section / Property Tax Cell | 33 |
| 2 | **WTR** | Water, Sewerage & Utility Billing | Revenue & Billing | Water Supply & Public Health Engineering | 32 |
| 3 | **GRV** | Citizen Service Desk, Grievance & RTI | Citizen Engagement & Welfare | Commissioner's Office / IT Cell / Public Information Cell | 30 |
| 4 | **FIN** | Finance & Accounting | Finance & Administration | Accounts & Finance Section | 30 |
| 5 | **TRL** | Trade Licence Management | Revenue & Billing | Trade Licensing & Public Health | 26 |
| 6 | **UCH** | User Charges Management | Revenue & Billing | Revenue Section / Sanitation | 23 |
| 7 | **SWM** | Solid Waste Management | Infrastructure & Field Ops | Public Health & Sanitation Section | 17 |
| 8 | **HRM** | Payroll & HR Management | Finance & Administration | Administration & Establishment Wing | 19 |
| 9 | **DMS** | Document Management System | Finance & Administration | Central Records & IT Cell | 30 |
| 10 | **ENG** | Engineering Project Management System | Infrastructure & Field Ops | Engineering & Works Wing | 20 |
| 11 | **BPM** | Building Permission Management | Planning & Regulation | Town Planning & Building Scrutiny Section | 22 |
| 12 | **SLM** | Street Light Management | Infrastructure & Field Ops | Electrical & Street Lighting Wing | 12 |
| 13 | **TPL** | Town Planning | Planning & Regulation | Town Planning Section / Master Plan Cell | 23 |
| 14 | **PRK** | Parks & Horticulture Management | Infrastructure & Field Ops | Horticulture & Urban Forestry Section | 18 |
| 15 | **MPM** | Municipal Property Management | Revenue & Billing | Estates & Asset Management Cell | 15 |
| 16 | **LGL** | Legal Case Management | Planning & Regulation | Legal Cell & Court Liaison | 17 |
| 17 | **INV** | Inventory & Stores Management | Finance & Administration | Central Stores & Procurement Section | 17 |
| 18 | **FNC** | Fire NOC Management | Planning & Regulation | Fire Safety Cell & State Fire Service Liaison | 17 |
| 19 | **GSC** | Government Schemes Management | Citizen Engagement & Welfare | Urban Community Development (UCD) & Social Welfare | 14 |

---

## 1. [PTX] Property Tax & Revenue Management

- **Domain**: Revenue & Billing
- **Department**: Revenue Section / Property Tax Cell
- **Total Granular Components**: 33
- **ERD Reference Diagram**: [Urban-ERD-Diagrams-PNG/ptx.png](file:///Users/sagarsingharoy/Documents/urban/Urban-ERD-Diagrams-PNG/ptx.png)

### Granular Components / Feature Processes (RBAC Units)

| Component Code | Component / Process Name | Access Scope & Description |
|---|---|---|
| `PTX-P01` | **Property registration and identification** | Granular RBAC target for module PTX |
| `PTX-P02` | **Legacy data onboarding and state platform sync** | Granular RBAC target for module PTX |
| `PTX-P03` | **Property survey and GIS reconciliation** | Granular RBAC target for module PTX |
| `PTX-P04` | **Property data correction** | Granular RBAC target for module PTX |
| `PTX-P05` | **New assessment – built property** | Granular RBAC target for module PTX |
| `PTX-P06` | **Self-assessment by owner** | Granular RBAC target for module PTX |
| `PTX-P07` | **Apartment / multi-unit assessment** | Granular RBAC target for module PTX |
| `PTX-P08` | **Vacant land tax** | Granular RBAC target for module PTX |
| `PTX-P09` | **Reassessment – addition, alteration, usage or occupancy change** | Granular RBAC target for module PTX |
| `PTX-P10` | **General revision of rates and zones** | Granular RBAC target for module PTX |
| `PTX-P11` | **Back-assessment of unassessed or under-assessed property** | Granular RBAC target for module PTX |
| `PTX-P12` | **Setback verification and deviation penalty** | Granular RBAC target for module PTX |
| `PTX-P13` | **Exemptions, concessions and category rebates** | Granular RBAC target for module PTX |
| `PTX-P31` | **Part-area non-residential use and rooftop installations** | Granular RBAC target for module PTX |
| `PTX-P32` | **Road and location classification for valuation** | Granular RBAC target for module PTX |
| `PTX-P33` | **Self-declared commercial accommodation use** | Granular RBAC target for module PTX |
| `PTX-P14` | **Auto-mutation from registration** | Granular RBAC target for module PTX |
| `PTX-P15` | **Mutation by application** | Granular RBAC target for module PTX |
| `PTX-P16` | **Bifurcation and amalgamation** | Granular RBAC target for module PTX |
| `PTX-P17` | **Demolition and deletion** | Granular RBAC target for module PTX |
| `PTX-P18` | **Periodic demand generation (Telangana: half-yearly)** | Granular RBAC target for module PTX |
| `PTX-P19` | **Bill amendment and demand correction** | Granular RBAC target for module PTX |
| `PTX-P20` | **Bill distribution and notifications** | Granular RBAC target for module PTX |
| `PTX-P21` | **Collection** | Granular RBAC target for module PTX |
| `PTX-P22` | **Cheque bounce, receipt cancellation and refund** | Granular RBAC target for module PTX |
| `PTX-P23` | **Daily reconciliation and remittance** | Granular RBAC target for module PTX |
| `PTX-P24` | **Objection, revision petition and appeal** | Granular RBAC target for module PTX |
| `PTX-P25` | **Interest, penalty and recovery** | Granular RBAC target for module PTX |
| `PTX-P26` | **One-time settlement and interest waiver** | Granular RBAC target for module PTX |
| `PTX-P27` | **Write-off and remission** | Granular RBAC target for module PTX |
| `PTX-P28` | **Certificates** | Granular RBAC target for module PTX |
| `PTX-P29` | **Property tax complaints** | Granular RBAC target for module PTX |
| `PTX-P30` | **Dashboards, DCB and compliance reporting** | Granular RBAC target for module PTX |

---

## 2. [WTR] Water, Sewerage & Utility Billing

- **Domain**: Revenue & Billing
- **Department**: Water Supply & Public Health Engineering
- **Total Granular Components**: 32
- **ERD Reference Diagram**: [Urban-ERD-Diagrams-PNG/wtr.png](file:///Users/sagarsingharoy/Documents/urban/Urban-ERD-Diagrams-PNG/wtr.png)

### Granular Components / Feature Processes (RBAC Units)

| Component Code | Component / Process Name | Access Scope & Description |
|---|---|---|
| `WTR-W01` | **New water connection** | Granular RBAC target for module WTR |
| `WTR-W02` | **New sewerage / UGD connection** | Granular RBAC target for module WTR |
| `WTR-W03` | **Regularisation of unauthorised connection** | Granular RBAC target for module WTR |
| `WTR-W04` | **Bulk / apartment connection with sub-metering** | Granular RBAC target for module WTR |
| `WTR-W05` | **Temporary connection** | Granular RBAC target for module WTR |
| `WTR-W06` | **Ownership transfer** | Granular RBAC target for module WTR |
| `WTR-W07` | **Usage or category change** | Granular RBAC target for module WTR |
| `WTR-W08` | **Pipe size, additional connection or shifting** | Granular RBAC target for module WTR |
| `WTR-W09` | **Metered ↔ non-metered conversion** | Granular RBAC target for module WTR |
| `WTR-W10` | **Temporary disconnection on request and reconnection** | Granular RBAC target for module WTR |
| `WTR-W11` | **Meter installation and register** | Granular RBAC target for module WTR |
| `WTR-W12` | **Meter reading and spot billing** | Granular RBAC target for module WTR |
| `WTR-W13` | **Faulty, stopped, locked or tampered meter** | Granular RBAC target for module WTR |
| `WTR-W14` | **Meter testing on request** | Granular RBAC target for module WTR |
| `WTR-W15` | **Tariff and scheme set-up** | Granular RBAC target for module WTR |
| `WTR-W16` | **Bill generation** | Granular RBAC target for module WTR |
| `WTR-W17` | **Bill amendment** | Granular RBAC target for module WTR |
| `WTR-W18` | **Bill distribution and notifications** | Granular RBAC target for module WTR |
| `WTR-W19` | **Collection** | Granular RBAC target for module WTR |
| `WTR-W20` | **Disconnection for arrears and reconnection** | Granular RBAC target for module WTR |
| `WTR-W21` | **Permanent closure** | Granular RBAC target for module WTR |
| `WTR-W22` | **One-time settlement, write-off and refunds** | Granular RBAC target for module WTR |
| `WTR-W23` | **Bulk water accounting and NRW by zone / DMA** | Granular RBAC target for module WTR |
| `WTR-W24` | **Leak, burst and illegal connection detection** | Granular RBAC target for module WTR |
| `WTR-W25` | **Water quality sampling and contamination response** | Granular RBAC target for module WTR |
| `WTR-W26` | **Supply schedules and planned shutdowns** | Granular RBAC target for module WTR |
| `WTR-W27` | **Tanker water supply** | Granular RBAC target for module WTR |
| `WTR-W28` | **Septic tank desludging and sewer jetting** | Granular RBAC target for module WTR |
| `WTR-W29` | **Service request intake and triage** | Granular RBAC target for module WTR |
| `WTR-W30` | **Dispatch and field resolution** | Granular RBAC target for module WTR |
| `WTR-W31` | **Area incidents and outage communication** | Granular RBAC target for module WTR |
| `WTR-W32` | **Dashboards and reports** | Granular RBAC target for module WTR |

---

## 3. [GRV] Citizen Service Desk, Grievance & RTI

- **Domain**: Citizen Engagement & Welfare
- **Department**: Commissioner's Office / IT Cell / Public Information Cell
- **Total Granular Components**: 30
- **ERD Reference Diagram**: [Urban-ERD-Diagrams-PNG/grv.png](file:///Users/sagarsingharoy/Documents/urban/Urban-ERD-Diagrams-PNG/grv.png)

### Granular Components / Feature Processes (RBAC Units)

| Component Code | Component / Process Name | Access Scope & Description |
|---|---|---|
| `GRV-G01` | **Portal, app and WhatsApp chatbot** | Granular RBAC target for module GRV |
| `GRV-G02` | **Call centre and IVRS** | Granular RBAC target for module GRV |
| `GRV-G03` | **Walk-in and grievance day** | Granular RBAC target for module GRV |
| `GRV-G04` | **Social media requests** | Granular RBAC target for module GRV |
| `GRV-G05` | **Swachhata app and Swachh Bharat integration** | Granular RBAC target for module GRV |
| `GRV-G06` | **Other government portals** | Granular RBAC target for module GRV |
| `GRV-G07` | **QR codes on assets** | Granular RBAC target for module GRV |
| `GRV-G08` | **Public representative referrals** | Granular RBAC target for module GRV |
| `GRV-G09` | **Request taxonomy** | Granular RBAC target for module GRV |
| `GRV-G10` | **Duplicate detection and clubbing** | Granular RBAC target for module GRV |
| `GRV-G11` | **Auto-routing** | Granular RBAC target for module GRV |
| `GRV-G12` | **Transfer, reassign and reject** | Granular RBAC target for module GRV |
| `GRV-G13` | **Linkage to Solid Waste (garbage collection)** | Granular RBAC target for module GRV |
| `GRV-G14` | **Linkage to call for service** | Granular RBAC target for module GRV |
| `GRV-G15` | **SLA timers and escalation** | Granular RBAC target for module GRV |
| `GRV-G16` | **Resolution with evidence** | Granular RBAC target for module GRV |
| `GRV-G17` | **Citizen confirmation and happiness rating** | Granular RBAC target for module GRV |
| `GRV-G18` | **Reopen and re-verification** | Granular RBAC target for module GRV |
| `GRV-G19` | **Verification audits** | Granular RBAC target for module GRV |
| `GRV-G20` | **RTI application intake** | Granular RBAC target for module GRV |
| `GRV-G21` | **Assignment, transfer and third-party notice** | Granular RBAC target for module GRV |
| `GRV-G22` | **Information compilation and reply** | Granular RBAC target for module GRV |
| `GRV-G23` | **First and second appeals** | Granular RBAC target for module GRV |
| `GRV-G24` | **Proactive disclosure and RTI returns** | Granular RBAC target for module GRV |
| `GRV-G25` | **Status and information queries** | Granular RBAC target for module GRV |
| `GRV-G26` | **Knowledge base, FAQs and chatbot** | Granular RBAC target for module GRV |
| `GRV-G27` | **Suggestions and citizen surveys** | Granular RBAC target for module GRV |
| `GRV-G28` | **Hotspots and preventive work** | Granular RBAC target for module GRV |
| `GRV-G29` | **Good governance dashboard** | Granular RBAC target for module GRV |
| `GRV-G30` | **Citizen Happiness Index (CXO view)** | Granular RBAC target for module GRV |

---

## 4. [FIN] Finance & Accounting

- **Domain**: Finance & Administration
- **Department**: Accounts & Finance Section
- **Total Granular Components**: 30
- **ERD Reference Diagram**: [Urban-ERD-Diagrams-PNG/fin.png](file:///Users/sagarsingharoy/Documents/urban/Urban-ERD-Diagrams-PNG/fin.png)

### Granular Components / Feature Processes (RBAC Units)

| Component Code | Component / Process Name | Access Scope & Description |
|---|---|---|
| `FIN-F01` | **Chart of accounts** | Granular RBAC target for module FIN |
| `FIN-F02` | **Funds, banks and service mapping** | Granular RBAC target for module FIN |
| `FIN-F03` | **Vendor and contractor master** | Granular RBAC target for module FIN |
| `FIN-F04` | **Budget preparation** | Granular RBAC target for module FIN |
| `FIN-F05` | **Budget control, commitment and re-appropriation** | Granular RBAC target for module FIN |
| `FIN-F06` | **Grants management** | Granular RBAC target for module FIN |
| `FIN-F07` | **Auto-journals from module postings** | Granular RBAC target for module FIN |
| `FIN-F08` | **Receipt realisation and confirmation** | Granular RBAC target for module FIN |
| `FIN-F09` | **Deposits** | Granular RBAC target for module FIN |
| `FIN-F10` | **Cash and collection remittance** | Granular RBAC target for module FIN |
| `FIN-F11` | **Bills** | Granular RBAC target for module FIN |
| `FIN-F12` | **Statutory deductions and remittances** | Granular RBAC target for module FIN |
| `FIN-F13` | **Payments** | Granular RBAC target for module FIN |
| `FIN-F14` | **Advances and imprest** | Granular RBAC target for module FIN |
| `FIN-F15` | **Payroll accounting** | Granular RBAC target for module FIN |
| `FIN-F16` | **Fixed assets and depreciation** | Granular RBAC target for module FIN |
| `FIN-F17` | **Borrowings and investments** | Granular RBAC target for module FIN |
| `FIN-F18` | **Inventory valuation** | Granular RBAC target for module FIN |
| `FIN-F19` | **GST set-up and output tax invoicing** | Granular RBAC target for module FIN |
| `FIN-F20` | **GST TDS on supplier payments** | Granular RBAC target for module FIN |
| `FIN-F21` | **GST returns and reconciliation** | Granular RBAC target for module FIN |
| `FIN-F22` | **Bank reconciliation** | Granular RBAC target for module FIN |
| `FIN-F23` | **Month-end close** | Granular RBAC target for module FIN |
| `FIN-F24` | **Year-end close** | Granular RBAC target for module FIN |
| `FIN-F25` | **Financial statements** | Granular RBAC target for module FIN |
| `FIN-F26` | **Audit and compliance** | Granular RBAC target for module FIN |
| `FIN-F27` | **Publication of accounts and Finance Commission compliance** | Granular RBAC target for module FIN |
| `FIN-F28` | **Credit rating readiness** | Granular RBAC target for module FIN |
| `FIN-F29` | **Municipal bond lifecycle** | Granular RBAC target for module FIN |
| `FIN-F30` | **Finance dashboards and financial health view** | Granular RBAC target for module FIN |

---

## 5. [TRL] Trade Licence Management

- **Domain**: Revenue & Billing
- **Department**: Trade Licensing & Public Health
- **Total Granular Components**: 26
- **ERD Reference Diagram**: [Urban-ERD-Diagrams-PNG/trl.png](file:///Users/sagarsingharoy/Documents/urban/Urban-ERD-Diagrams-PNG/trl.png)

### Granular Components / Feature Processes (RBAC Units)

| Component Code | Component / Process Name | Access Scope & Description |
|---|---|---|
| `TRL-T01` | **New trade licence** | Granular RBAC target for module TRL |
| `TRL-T02` | **Part-area licence** | Granular RBAC target for module TRL |
| `TRL-T03` | **Temporary and seasonal licence** | Granular RBAC target for module TRL |
| `TRL-T04` | **PG, hostel, co-living and homestay licence** | Granular RBAC target for module TRL |
| `TRL-T21` | **Industry, MSME and startup licensing** | Granular RBAC target for module TRL |
| `TRL-T05` | **Fee set-up** | Granular RBAC target for module TRL |
| `TRL-T06` | **Rebates, exemptions and penalties** | Granular RBAC target for module TRL |
| `TRL-T07` | **Renewal and auto-renewal** | Granular RBAC target for module TRL |
| `TRL-T08` | **Change of trade, area, partners or owner** | Granular RBAC target for module TRL |
| `TRL-T09` | **Shifting of premises** | Granular RBAC target for module TRL |
| `TRL-T10` | **Suspension and cancellation** | Granular RBAC target for module TRL |
| `TRL-T11` | **Surrender and closure** | Granular RBAC target for module TRL |
| `TRL-T12` | **Monthly verification drive** | Granular RBAC target for module TRL |
| `TRL-T13` | **Detection of unlicensed trades** | Granular RBAC target for module TRL |
| `TRL-T14` | **Risk-based inspection** | Granular RBAC target for module TRL |
| `TRL-T15` | **Revision petitions and appeals** | Granular RBAC target for module TRL |
| `TRL-T16` | **Fire NOC check** | Granular RBAC target for module TRL |
| `TRL-T17` | **Other statutory registrations** | Granular RBAC target for module TRL |
| `TRL-T18` | **Establishment master publication** | Granular RBAC target for module TRL |
| `TRL-T19` | **Payment, GST and Finance posting** | Granular RBAC target for module TRL |
| `TRL-T22` | **Vendor survey and Town Vending Committee** | Granular RBAC target for module TRL |
| `TRL-T23` | **Vending plan and zones** | Granular RBAC target for module TRL |
| `TRL-T24` | **Certificate of vending and ID card** | Granular RBAC target for module TRL |
| `TRL-T25` | **Food trucks, mobile food courts and night markets** | Granular RBAC target for module TRL |
| `TRL-T26` | **Vending enforcement, relocation and disputes** | Granular RBAC target for module TRL |
| `TRL-T20` | **Dashboards** | Granular RBAC target for module TRL |

---

## 6. [UCH] User Charges Management

- **Domain**: Revenue & Billing
- **Department**: Revenue Section / Sanitation
- **Total Granular Components**: 23
- **ERD Reference Diagram**: [Urban-ERD-Diagrams-PNG/uch.png](file:///Users/sagarsingharoy/Documents/urban/Urban-ERD-Diagrams-PNG/uch.png)

### Granular Components / Feature Processes (RBAC Units)

| Component Code | Component / Process Name | Access Scope & Description |
|---|---|---|
| `UCH-U01` | **Automatic user registration** | Granular RBAC target for module UCH |
| `UCH-U02` | **Bulk waste generator registration** | Granular RBAC target for module UCH |
| `UCH-U03` | **Category and rate assignment** | Granular RBAC target for module UCH |
| `UCH-U04` | **Charge set-up** | Granular RBAC target for module UCH |
| `UCH-U05` | **Service-linked billing** | Granular RBAC target for module UCH |
| `UCH-U06` | **Demand generation** | Granular RBAC target for module UCH |
| `UCH-U07` | **Combined bill** | Granular RBAC target for module UCH |
| `UCH-U08` | **Collection** | Granular RBAC target for module UCH |
| `UCH-U09` | **Spot fines** | Granular RBAC target for module UCH |
| `UCH-U10` | **Event and one-time charges** | Granular RBAC target for module UCH |
| `UCH-U18` | **Street vending fees and maintenance charges** | Granular RBAC target for module UCH |
| `UCH-U19` | **Booking of parks, grounds and public spaces for gatherings** | Granular RBAC target for module UCH |
| `UCH-U20` | **Industrial and commercial waste charges** | Granular RBAC target for module UCH |
| `UCH-U21` | **Parking on municipal roads, lots and open spaces** | Granular RBAC target for module UCH |
| `UCH-U22` | **Religious processions, festivals and temporary use of roads** | Granular RBAC target for module UCH |
| `UCH-U23` | **Documents, deposits and disputes** | Granular RBAC target for module UCH |
| `UCH-U11` | **Arrears and recovery** | Granular RBAC target for module UCH |
| `UCH-U12` | **Exemptions and concessions** | Granular RBAC target for module UCH |
| `UCH-U13` | **Disputes** | Granular RBAC target for module UCH |
| `UCH-U14` | **Write-off and refunds** | Granular RBAC target for module UCH |
| `UCH-U15` | **Finance posting and GST** | Granular RBAC target for module UCH |
| `UCH-U16` | **Self-declared accommodation use** | Granular RBAC target for module UCH |
| `UCH-U17` | **Dashboards** | Granular RBAC target for module UCH |

---

## 7. [SWM] Solid Waste Management

- **Domain**: Infrastructure & Field Ops
- **Department**: Public Health & Sanitation Section
- **Total Granular Components**: 17
- **ERD Reference Diagram**: [Urban-ERD-Diagrams-PNG/swm.png](file:///Users/sagarsingharoy/Documents/urban/Urban-ERD-Diagrams-PNG/swm.png)

### Granular Components / Feature Processes (RBAC Units)

| Component Code | Component / Process Name | Access Scope & Description |
|---|---|---|
| `SWM-S01` | **Generator register and bulk waste generators** | Granular RBAC target for module SWM |
| `SWM-S02` | **Four-stream source segregation** | Granular RBAC target for module SWM |
| `SWM-S03` | **Door-to-door collection** | Granular RBAC target for module SWM |
| `SWM-S04` | **Secondary collection, transfer and garbage vulnerable points** | Granular RBAC target for module SWM |
| `SWM-S05` | **Street sweeping and beat management** | Granular RBAC target for module SWM |
| `SWM-S06` | **Fleet, routes and optimisation** | Granular RBAC target for module SWM |
| `SWM-S07` | **Processing facilities and mass balance** | Granular RBAC target for module SWM |
| `SWM-S08` | **Landfill and legacy dumpsite remediation** | Granular RBAC target for module SWM |
| `SWM-S09` | **Construction and demolition waste** | Granular RBAC target for module SWM |
| `SWM-S10` | **Special waste streams** | Granular RBAC target for module SWM |
| `SWM-S11` | **Public and community toilets** | Granular RBAC target for module SWM |
| `SWM-S12` | **Sanitation and public health service requests** | Granular RBAC target for module SWM |
| `SWM-S13` | **Sanitation worker safety and welfare** | Granular RBAC target for module SWM |
| `SWM-S14` | **Enforcement and environmental compensation** | Granular RBAC target for module SWM |
| `SWM-S15` | **Swachh Survekshan, star rating and central reporting** | Granular RBAC target for module SWM |
| `SWM-S16` | **Awareness and community engagement** | Granular RBAC target for module SWM |
| `SWM-S17` | **Dashboards** | Granular RBAC target for module SWM |

---

## 8. [HRM] Payroll & HR Management

- **Domain**: Finance & Administration
- **Department**: Administration & Establishment Wing
- **Total Granular Components**: 19
- **ERD Reference Diagram**: [Urban-ERD-Diagrams-PNG/hrm.png](file:///Users/sagarsingharoy/Documents/urban/Urban-ERD-Diagrams-PNG/hrm.png)

### Granular Components / Feature Processes (RBAC Units)

| Component Code | Component / Process Name | Access Scope & Description |
|---|---|---|
| `HRM-H01` | **Organisation and sanctioned posts** | Granular RBAC target for module HRM |
| `HRM-H02` | **Employee master and electronic service register** | Granular RBAC target for module HRM |
| `HRM-H03` | **Recruitment and onboarding** | Granular RBAC target for module HRM |
| `HRM-H04` | **Outsourced workforce and agencies** | Granular RBAC target for module HRM |
| `HRM-H05` | **Attendance and rosters** | Granular RBAC target for module HRM |
| `HRM-H06` | **Leave and holidays** | Granular RBAC target for module HRM |
| `HRM-H07` | **Transfers, postings and tours** | Granular RBAC target for module HRM |
| `HRM-H08` | **Pay structure, revisions and DA** | Granular RBAC target for module HRM |
| `HRM-H09` | **Monthly payroll** | Granular RBAC target for module HRM |
| `HRM-H10` | **Treasury integrate mode** | Granular RBAC target for module HRM |
| `HRM-H11` | **Statutory returns** | Granular RBAC target for module HRM |
| `HRM-H12` | **Loans and advances** | Granular RBAC target for module HRM |
| `HRM-H13` | **Increments, promotions and appraisals** | Granular RBAC target for module HRM |
| `HRM-H14` | **Discipline and service matters** | Granular RBAC target for module HRM |
| `HRM-H15` | **Training and capacity building** | Granular RBAC target for module HRM |
| `HRM-H16` | **Retirement, pension and final settlement** | Granular RBAC target for module HRM |
| `HRM-H17` | **Employee self-service** | Granular RBAC target for module HRM |
| `HRM-H18` | **Health, safety and welfare** | Granular RBAC target for module HRM |
| `HRM-H19` | **Dashboards** | Granular RBAC target for module HRM |

---

## 9. [DMS] Document Management System

- **Domain**: Finance & Administration
- **Department**: Central Records & IT Cell
- **Total Granular Components**: 30
- **ERD Reference Diagram**: [Urban-ERD-Diagrams-PNG/dms.png](file:///Users/sagarsingharoy/Documents/urban/Urban-ERD-Diagrams-PNG/dms.png)

### Granular Components / Feature Processes (RBAC Units)

| Component Code | Component / Process Name | Access Scope & Description |
|---|---|---|
| `DMS-D01` | **Document capture from modules** | Granular RBAC target for module DMS |
| `DMS-D02` | **Inward (dak) registration and scanning** | Granular RBAC target for module DMS |
| `DMS-D03` | **Legacy record digitisation** | Granular RBAC target for module DMS |
| `DMS-D04` | **Field photos, videos and geo-tagged evidence** | Granular RBAC target for module DMS |
| `DMS-D05` | **Maps, plans and drawings** | Granular RBAC target for module DMS |
| `DMS-D06` | **Fetch citizen documents from DigiLocker** | Granular RBAC target for module DMS |
| `DMS-D07` | **Property dossier and ownership chain** | Granular RBAC target for module DMS |
| `DMS-D08` | **Classification scheme and document types** | Granular RBAC target for module DMS |
| `DMS-D09` | **Indexing, linking and duplicates** | Granular RBAC target for module DMS |
| `DMS-D10` | **Search across and inside documents** | Granular RBAC target for module DMS |
| `DMS-D27` | **OCR quality and correction** | Granular RBAC target for module DMS |
| `DMS-D28` | **Indian language support** | Granular RBAC target for module DMS |
| `DMS-D11` | **e-File noting and approval** | Granular RBAC target for module DMS |
| `DMS-D12` | **Digital signing** | Granular RBAC target for module DMS |
| `DMS-D13` | **Templates, generation and QR verification** | Granular RBAC target for module DMS |
| `DMS-D14` | **Outward dispatch** | Granular RBAC target for module DMS |
| `DMS-D15` | **Access control and sharing** | Granular RBAC target for module DMS |
| `DMS-D16` | **Redaction for RTI and public disclosure** | Granular RBAC target for module DMS |
| `DMS-D17` | **Audit trail and court evidence** | Granular RBAC target for module DMS |
| `DMS-D18` | **Personal data protection** | Granular RBAC target for module DMS |
| `DMS-D19` | **Legal hold** | Granular RBAC target for module DMS |
| `DMS-D20` | **Retention schedule** | Granular RBAC target for module DMS |
| `DMS-D21` | **Review, weeding and destruction** | Granular RBAC target for module DMS |
| `DMS-D22` | **Physical record room** | Granular RBAC target for module DMS |
| `DMS-D23` | **Preservation and storage** | Granular RBAC target for module DMS |
| `DMS-D24` | **DigiLocker integration** | Granular RBAC target for module DMS |
| `DMS-D25` | **Citizen document locker** | Granular RBAC target for module DMS |
| `DMS-D29` | **Blockchain anchoring and verification** | Granular RBAC target for module DMS |
| `DMS-D30` | **Translate a document into the user's language** | Granular RBAC target for module DMS |
| `DMS-D26` | **Dashboards** | Granular RBAC target for module DMS |

---

## 10. [ENG] Engineering Project Management System

- **Domain**: Infrastructure & Field Ops
- **Department**: Engineering & Works Wing
- **Total Granular Components**: 20
- **ERD Reference Diagram**: [Urban-ERD-Diagrams-PNG/eng.png](file:///Users/sagarsingharoy/Documents/urban/Urban-ERD-Diagrams-PNG/eng.png)

### Granular Components / Feature Processes (RBAC Units)

| Component Code | Component / Process Name | Access Scope & Description |
|---|---|---|
| `ENG-E01` | **Works demand and prioritisation** | Granular RBAC target for module ENG |
| `ENG-E02` | **Survey, design and estimate** | Granular RBAC target for module ENG |
| `ENG-E03` | **Administrative approval and expenditure sanction** | Granular RBAC target for module ENG |
| `ENG-E04` | **Technical sanction** | Granular RBAC target for module ENG |
| `ENG-E05` | **Tendering** | Granular RBAC target for module ENG |
| `ENG-E06` | **Agreement and work order** | Granular RBAC target for module ENG |
| `ENG-E07` | **Schedule and progress monitoring** | Granular RBAC target for module ENG |
| `ENG-E08` | **e-Measurement Book and test checks** | Granular RBAC target for module ENG |
| `ENG-E09` | **Quality control** | Granular RBAC target for module ENG |
| `ENG-E10` | **Safety, traffic and environment** | Granular RBAC target for module ENG |
| `ENG-E11` | **Utility coordination and road cutting** | Granular RBAC target for module ENG |
| `ENG-E12` | **Running account bills and deductions** | Granular RBAC target for module ENG |
| `ENG-E13` | **Price variation** | Granular RBAC target for module ENG |
| `ENG-E14` | **Completion, defect liability and final bill** | Granular RBAC target for module ENG |
| `ENG-E15` | **Contractor performance and disputes** | Granular RBAC target for module ENG |
| `ENG-E16` | **Road register and pavement condition** | Granular RBAC target for module ENG |
| `ENG-E17` | **Storm water drainage and flood readiness** | Granular RBAC target for module ENG |
| `ENG-E18` | **Road and drain service requests** | Granular RBAC target for module ENG |
| `ENG-E19` | **Scheme and grant project monitoring** | Granular RBAC target for module ENG |
| `ENG-E20` | **Dashboards** | Granular RBAC target for module ENG |

---

## 11. [BPM] Building Permission Management

- **Domain**: Planning & Regulation
- **Department**: Town Planning & Building Scrutiny Section
- **Total Granular Components**: 22
- **ERD Reference Diagram**: [Urban-ERD-Diagrams-PNG/bpm.png](file:///Users/sagarsingharoy/Documents/urban/Urban-ERD-Diagrams-PNG/bpm.png)

### Granular Components / Feature Processes (RBAC Units)

| Component Code | Component / Process Name | Access Scope & Description |
|---|---|---|
| `BPM-B01` | **Integrate or full mode** | Granular RBAC target for module BPM |
| `BPM-B02` | **Pre-application check and fee estimate** | Granular RBAC target for module BPM |
| `BPM-B03` | **Category and risk routing** | Granular RBAC target for module BPM |
| `BPM-B04` | **Application and applicant checks** | Granular RBAC target for module BPM |
| `BPM-B05` | **Automatic plan scrutiny (eDCR)** | Granular RBAC target for module BPM |
| `BPM-B06` | **NOCs and clearances in parallel** | Granular RBAC target for module BPM |
| `BPM-B21` | **Water body, environmental and buffer-zone NOCs** | Granular RBAC target for module BPM |
| `BPM-B22` | **Tree felling, transplantation and groundwater NOC** | Granular RBAC target for module BPM |
| `BPM-B07` | **RERA link** | Granular RBAC target for module BPM |
| `BPM-B08` | **Pre-approval site inspection** | Granular RBAC target for module BPM |
| `BPM-B09` | **Fees, charges, cess and mortgage** | Granular RBAC target for module BPM |
| `BPM-B10` | **Approval, deemed approval and permit** | Granular RBAC target for module BPM |
| `BPM-B11` | **Shortfall, rejection and appeal** | Granular RBAC target for module BPM |
| `BPM-B12` | **Commencement and stage inspections** | Granular RBAC target for module BPM |
| `BPM-B13` | **Deviation monitoring during construction** | Granular RBAC target for module BPM |
| `BPM-B14` | **Revision, revalidation and transfer** | Granular RBAC target for module BPM |
| `BPM-B15` | **Occupancy certificate** | Granular RBAC target for module BPM |
| `BPM-B20` | **Rainwater harvesting certificate** | Granular RBAC target for module BPM |
| `BPM-B16` | **Partial occupancy certificate** | Granular RBAC target for module BPM |
| `BPM-B17` | **Green building and incentives** | Granular RBAC target for module BPM |
| `BPM-B18` | **Public disclosure and permit map** | Granular RBAC target for module BPM |
| `BPM-B19` | **Dashboards and ease-of-doing-business metrics** | Granular RBAC target for module BPM |

---

## 12. [SLM] Street Light Management

- **Domain**: Infrastructure & Field Ops
- **Department**: Electrical & Street Lighting Wing
- **Total Granular Components**: 12
- **ERD Reference Diagram**: [Urban-ERD-Diagrams-PNG/slm.png](file:///Users/sagarsingharoy/Documents/urban/Urban-ERD-Diagrams-PNG/slm.png)

### Granular Components / Feature Processes (RBAC Units)

| Component Code | Component / Process Name | Access Scope & Description |
|---|---|---|
| `SLM-L01` | **Asset inventory and survey** | Granular RBAC target for module SLM |
| `SLM-L02` | **Lighting standards by road class** | Granular RBAC target for module SLM |
| `SLM-L03` | **Fault intake and dispatch** | Granular RBAC target for module SLM |
| `SLM-L04` | **Repair and closure** | Granular RBAC target for module SLM |
| `SLM-L05` | **Planned maintenance** | Granular RBAC target for module SLM |
| `SLM-L06` | **CCMS and smart controls** | Granular RBAC target for module SLM |
| `SLM-L07` | **Burning hours and dark spots** | Granular RBAC target for module SLM |
| `SLM-L08` | **Energy and bill verification** | Granular RBAC target for module SLM |
| `SLM-L09` | **Maintenance contracts and ESCO SLAs** | Granular RBAC target for module SLM |
| `SLM-L10` | **New lights and extensions** | Granular RBAC target for module SLM |
| `SLM-L11` | **Safety and outages** | Granular RBAC target for module SLM |
| `SLM-L12` | **Dashboards** | Granular RBAC target for module SLM |

---

## 13. [TPL] Town Planning

- **Domain**: Planning & Regulation
- **Department**: Town Planning Section / Master Plan Cell
- **Total Granular Components**: 23
- **ERD Reference Diagram**: [Urban-ERD-Diagrams-PNG/tpl.png](file:///Users/sagarsingharoy/Documents/urban/Urban-ERD-Diagrams-PNG/tpl.png)

### Granular Components / Feature Processes (RBAC Units)

| Component Code | Component / Process Name | Access Scope & Description |
|---|---|---|
| `TPL-P01` | **Master plan and zoning layers** | Granular RBAC target for module TPL |
| `TPL-P02` | **Zoning and development control rules** | Granular RBAC target for module TPL |
| `TPL-P03` | **Zoning check and land-use certificate** | Granular RBAC target for module TPL |
| `TPL-P04` | **Change of land use and master plan variation** | Granular RBAC target for module TPL |
| `TPL-P05` | **Master plan roads and road widening** | Granular RBAC target for module TPL |
| `TPL-P06` | **Planning analytics** | Granular RBAC target for module TPL |
| `TPL-P23` | **Restricted and buffer zone catalogue** | Granular RBAC target for module TPL |
| `TPL-P07` | **Layout permission** | Granular RBAC target for module TPL |
| `TPL-P08` | **Layout development works and mortgage release** | Granular RBAC target for module TPL |
| `TPL-P09` | **Open spaces and amenity sites to the ULB** | Granular RBAC target for module TPL |
| `TPL-P10` | **Sub-division and amalgamation of plots** | Granular RBAC target for module TPL |
| `TPL-P11` | **Layout regularisation (LRS)** | Granular RBAC target for module TPL |
| `TPL-P12` | **Building regularisation and penalisation** | Granular RBAC target for module TPL |
| `TPL-P13` | **Unauthorised construction enforcement** | Granular RBAC target for module TPL |
| `TPL-P14` | **Encroachment removal** | Granular RBAC target for module TPL |
| `TPL-P15` | **Transferable development rights (TDR)** | Granular RBAC target for module TPL |
| `TPL-P16` | **Development, impact and open space charges** | Granular RBAC target for module TPL |
| `TPL-P17` | **Advertisements and hoardings** | Granular RBAC target for module TPL |
| `TPL-P18` | **Telecom towers and right of way** | Granular RBAC target for module TPL |
| `TPL-P19` | **Heritage and protected monuments** | Granular RBAC target for module TPL |
| `TPL-P20` | **Street naming and door numbering** | Granular RBAC target for module TPL |
| `TPL-P21` | **Public planning portal** | Granular RBAC target for module TPL |
| `TPL-P22` | **Dashboards** | Granular RBAC target for module TPL |

---

## 14. [PRK] Parks & Horticulture Management

- **Domain**: Infrastructure & Field Ops
- **Department**: Horticulture & Urban Forestry Section
- **Total Granular Components**: 18
- **ERD Reference Diagram**: [Urban-ERD-Diagrams-PNG/prk.png](file:///Users/sagarsingharoy/Documents/urban/Urban-ERD-Diagrams-PNG/prk.png)

### Granular Components / Feature Processes (RBAC Units)

| Component Code | Component / Process Name | Access Scope & Description |
|---|---|---|
| `PRK-K01` | **Parks and open space registry** | Granular RBAC target for module PRK |
| `PRK-K02` | **Tree census and heritage trees** | Granular RBAC target for module PRK |
| `PRK-K03` | **Green cover and heat analysis** | Granular RBAC target for module PRK |
| `PRK-K04` | **Plantation drives and survival audits** | Granular RBAC target for module PRK |
| `PRK-K05` | **Nurseries** | Granular RBAC target for module PRK |
| `PRK-K06` | **Avenues, medians and urban forests** | Granular RBAC target for module PRK |
| `PRK-K07` | **Green budget tracking** | Granular RBAC target for module PRK |
| `PRK-K08` | **Maintenance operations** | Granular RBAC target for module PRK |
| `PRK-K09` | **Play equipment and safety inspections** | Granular RBAC target for module PRK |
| `PRK-K10` | **Visitors, passes and bookings** | Granular RBAC target for module PRK |
| `PRK-K11` | **Adoption and CSR** | Granular RBAC target for module PRK |
| `PRK-K12` | **Tree service requests and emergencies** | Granular RBAC target for module PRK |
| `PRK-K13` | **Private tree cutting as a paid service** | Granular RBAC target for module PRK |
| `PRK-K14` | **Pre-monsoon hazardous tree survey** | Granular RBAC target for module PRK |
| `PRK-K15` | **Felling permissions and compensatory plantation** | Granular RBAC target for module PRK |
| `PRK-K16` | **Green waste and timber** | Granular RBAC target for module PRK |
| `PRK-K17` | **Protection of parks and open spaces** | Granular RBAC target for module PRK |
| `PRK-K18` | **Dashboards** | Granular RBAC target for module PRK |

---

## 15. [MPM] Municipal Property Management

- **Domain**: Revenue & Billing
- **Department**: Estates & Asset Management Cell
- **Total Granular Components**: 15
- **ERD Reference Diagram**: [Urban-ERD-Diagrams-PNG/mpm.png](file:///Users/sagarsingharoy/Documents/urban/Urban-ERD-Diagrams-PNG/mpm.png)

### Granular Components / Feature Processes (RBAC Units)

| Component Code | Component / Process Name | Access Scope & Description |
|---|---|---|
| `MPM-M01` | **Immovable asset register** | Granular RBAC target for module MPM |
| `MPM-M02` | **Movable asset register** | Granular RBAC target for module MPM |
| `MPM-M03` | **Asset intake, capitalisation and depreciation** | Granular RBAC target for module MPM |
| `MPM-M04` | **Land bank and title** | Granular RBAC target for module MPM |
| `MPM-M05` | **Physical verification** | Granular RBAC target for module MPM |
| `MPM-M06` | **Leasing of shops, kiosks, market stalls and spaces** | Granular RBAC target for module MPM |
| `MPM-M07` | **Rent demand, GST and recovery** | Granular RBAC target for module MPM |
| `MPM-M08` | **Halls, crematoria and short-term use** | Granular RBAC target for module MPM |
| `MPM-M09` | **Licences on municipal property** | Granular RBAC target for module MPM |
| `MPM-M10` | **Asset monetisation and PPP** | Granular RBAC target for module MPM |
| `MPM-M11` | **Encroachment protection** | Granular RBAC target for module MPM |
| `MPM-M12` | **Building maintenance and insurance** | Granular RBAC target for module MPM |
| `MPM-M13` | **Disposal and transfer** | Granular RBAC target for module MPM |
| `MPM-M14` | **Land acquisition and surrender** | Granular RBAC target for module MPM |
| `MPM-M15` | **Dashboards** | Granular RBAC target for module MPM |

---

## 16. [LGL] Legal Case Management

- **Domain**: Planning & Regulation
- **Department**: Legal Cell & Court Liaison
- **Total Granular Components**: 17
- **ERD Reference Diagram**: [Urban-ERD-Diagrams-PNG/lgl.png](file:///Users/sagarsingharoy/Documents/urban/Urban-ERD-Diagrams-PNG/lgl.png)

### Granular Components / Feature Processes (RBAC Units)

| Component Code | Component / Process Name | Access Scope & Description |
|---|---|---|
| `LGL-J01` | **Case registration** | Granular RBAC target for module LGL |
| `LGL-J02` | **Court data integration** | Granular RBAC target for module LGL |
| `LGL-J03` | **Legal notices and opinions** | Granular RBAC target for module LGL |
| `LGL-J04` | **Counsel panel and assignment** | Granular RBAC target for module LGL |
| `LGL-J05` | **Para-wise remarks and counter affidavit** | Granular RBAC target for module LGL |
| `LGL-J06` | **Hearings and legal diary** | Granular RBAC target for module LGL |
| `LGL-J17` | **Officer hearing calendar and document readiness** | Granular RBAC target for module LGL |
| `LGL-J07` | **Limitation and deadline engine** | Granular RBAC target for module LGL |
| `LGL-J08` | **Orders, directions and compliance** | Granular RBAC target for module LGL |
| `LGL-J09` | **Contempt risk management** | Granular RBAC target for module LGL |
| `LGL-J10` | **Appeal decisions** | Granular RBAC target for module LGL |
| `LGL-J11` | **Stays and interim orders** | Granular RBAC target for module LGL |
| `LGL-J12` | **Advocate fees and bills** | Granular RBAC target for module LGL |
| `LGL-J13` | **Court-ordered payments and deposits** | Granular RBAC target for module LGL |
| `LGL-J14` | **Settlement, Lok Adalat, mediation and arbitration** | Granular RBAC target for module LGL |
| `LGL-J15` | **Prosecutions by the ULB** | Granular RBAC target for module LGL |
| `LGL-J16` | **Dashboards** | Granular RBAC target for module LGL |

---

## 17. [INV] Inventory & Stores Management

- **Domain**: Finance & Administration
- **Department**: Central Stores & Procurement Section
- **Total Granular Components**: 17
- **ERD Reference Diagram**: [Urban-ERD-Diagrams-PNG/inv.png](file:///Users/sagarsingharoy/Documents/urban/Urban-ERD-Diagrams-PNG/inv.png)

### Granular Components / Feature Processes (RBAC Units)

| Component Code | Component / Process Name | Access Scope & Description |
|---|---|---|
| `INV-V01` | **Item master and catalogue** | Granular RBAC target for module INV |
| `INV-V02` | **Stores and bin locations** | Granular RBAC target for module INV |
| `INV-V03` | **Reorder levels and procurement plan** | Granular RBAC target for module INV |
| `INV-V04` | **Indents from modules** | Granular RBAC target for module INV |
| `INV-V05` | **Purchase route selection** | Granular RBAC target for module INV |
| `INV-V06` | **Purchase orders and vendors** | Granular RBAC target for module INV |
| `INV-V07` | **Goods receipt and inspection** | Granular RBAC target for module INV |
| `INV-V08` | **Issue and returns** | Granular RBAC target for module INV |
| `INV-V09` | **Transfers between stores** | Granular RBAC target for module INV |
| `INV-V10` | **Valuation and costing** | Granular RBAC target for module INV |
| `INV-V11` | **Fuel management** | Granular RBAC target for module INV |
| `INV-V12` | **PPE and uniforms** | Granular RBAC target for module INV |
| `INV-V13` | **Physical verification and cycle counts** | Granular RBAC target for module INV |
| `INV-V14` | **Shelf life and expiry** | Granular RBAC target for module INV |
| `INV-V15` | **Surplus, obsolete and scrap disposal** | Granular RBAC target for module INV |
| `INV-V16` | **Tools and returnable items** | Granular RBAC target for module INV |
| `INV-V17` | **Dashboards** | Granular RBAC target for module INV |

---

## 18. [FNC] Fire NOC Management

- **Domain**: Planning & Regulation
- **Department**: Fire Safety Cell & State Fire Service Liaison
- **Total Granular Components**: 17
- **ERD Reference Diagram**: [Urban-ERD-Diagrams-PNG/fnc.png](file:///Users/sagarsingharoy/Documents/urban/Urban-ERD-Diagrams-PNG/fnc.png)

### Granular Components / Feature Processes (RBAC Units)

| Component Code | Component / Process Name | Access Scope & Description |
|---|---|---|
| `FNC-N01` | **Integrate or full mode** | Granular RBAC target for module FNC |
| `FNC-N02` | **Applicability rules** | Granular RBAC target for module FNC |
| `FNC-N03` | **Provisional NOC at building permission** | Granular RBAC target for module FNC |
| `FNC-N04` | **Occupancy (final) NOC** | Granular RBAC target for module FNC |
| `FNC-N05` | **Renewal and periodic inspection** | Granular RBAC target for module FNC |
| `FNC-N06` | **Fire NOC for establishments** | Granular RBAC target for module FNC |
| `FNC-N07` | **Inspection with checklist** | Granular RBAC target for module FNC |
| `FNC-N08` | **Deficiencies and re-inspection** | Granular RBAC target for module FNC |
| `FNC-N09` | **Third-party fire safety audits** | Granular RBAC target for module FNC |
| `FNC-N10` | **IoT monitoring of fire systems (optional)** | Granular RBAC target for module FNC |
| `FNC-N11` | **Enforcement on unsafe buildings** | Granular RBAC target for module FNC |
| `FNC-N12` | **Temporary NOCs for events and festival stalls** | Granular RBAC target for module FNC |
| `FNC-N13` | **Fees and refunds** | Granular RBAC target for module FNC |
| `FNC-N14` | **NOC register and verification** | Granular RBAC target for module FNC |
| `FNC-N15` | **GIS fire-risk map** | Granular RBAC target for module FNC |
| `FNC-N16` | **Fire incidents and review** | Granular RBAC target for module FNC |
| `FNC-N17` | **Dashboards** | Granular RBAC target for module FNC |

---

## 19. [GSC] Government Schemes Management

- **Domain**: Citizen Engagement & Welfare
- **Department**: Urban Community Development (UCD) & Social Welfare
- **Total Granular Components**: 14
- **ERD Reference Diagram**: [Urban-ERD-Diagrams-PNG/gsc.png](file:///Users/sagarsingharoy/Documents/urban/Urban-ERD-Diagrams-PNG/gsc.png)

### Granular Components / Feature Processes (RBAC Units)

| Component Code | Component / Process Name | Access Scope & Description |
|---|---|---|
| `GSC-C01` | **Scheme catalogue and eligibility rules** | Granular RBAC target for module GSC |
| `GSC-C02` | **Unified beneficiary register** | Granular RBAC target for module GSC |
| `GSC-C03` | **Surveys and identification** | Granular RBAC target for module GSC |
| `GSC-C04` | **Application and eligibility check** | Granular RBAC target for module GSC |
| `GSC-C05` | **Verification, approval and social audit** | Granular RBAC target for module GSC |
| `GSC-C06` | **Housing delivery** | Granular RBAC target for module GSC |
| `GSC-C07` | **Livelihoods, SHGs and street vendors** | Granular RBAC target for module GSC |
| `GSC-C08` | **Sanitation and other household benefits** | Granular RBAC target for module GSC |
| `GSC-C09` | **Concessions in municipal dues** | Granular RBAC target for module GSC |
| `GSC-C10` | **DBT and disbursement** | Granular RBAC target for module GSC |
| `GSC-C11` | **Scheme funds and utilisation** | Granular RBAC target for module GSC |
| `GSC-C12` | **Grievances and transparency** | Granular RBAC target for module GSC |
| `GSC-C13` | **Household convergence view** | Granular RBAC target for module GSC |
| `GSC-C14` | **Dashboards** | Granular RBAC target for module GSC |

---
