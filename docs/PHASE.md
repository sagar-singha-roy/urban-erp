# Urban Integrated Municipal ERP — Delivery Phases & Module-Wise Component Breakdown

**Source Baseline**:

- `Urban-GWMC-Project-Plan.xlsx` (Hake Technologies | Version 0.1 draft | 23 October 2026)
- `Urban-ERP-SRS_v2.docx` (Product SRS v0.35)
- `Urban-Technical-Architecture_v2.docx` (Technical Architecture v0.1)
- [MODULE_COMPONENTS_CATALOGUE.md](file:///Users/sagarsingharoy/Documents/urban/docs/MODULE_COMPONENTS_CATALOGUE.md)

---

## Executive Phase Matrix

| Phase       | Phase Name                            | Focus Area                                                       | Modules Included                         | Component Count                            | Key Milestones                               |
| ----------- | ------------------------------------- | ---------------------------------------------------------------- | ---------------------------------------- | ------------------------------------------ | -------------------------------------------- |
| **Level 0** | **Platform Super Admin ("The Boss")** | Multi-tier tenancy, cross-state analytics, RBAC & fleet ops      | **ADM (Platform Administration)**        | **28 Components**                          | Continuous Control Plane                     |
| **Phase 0** | **Inception & Mobilisation**          | Infra, State Data Centre approvals, CI/CD, baseline architecture | Platform Foundation                      | Core Baseline                              | M0: Inception complete, Phase 1 build starts |
| **Phase 1** | **Foundation & Revenue Core**         | Core identity, municipal accounting & high-volume revenue        | **PTX, WTR, GRV, FIN, DMS**              | **155 Components**                         | M1: Phase 1 Go-Live & Sign-Off               |
| **Phase 2** | **Regulation & Licensing**            | Spatial compliance, single-window permissions & trades           | **TRL, UCH, BPM, TPL, FNC**              | **111 Components**                         | M2: Phase 2 Go-Live & Sign-Off               |
| **Phase 3** | **Field Operations & Infrastructure** | Public health, works e-MB, electrical assets & open spaces       | **SWM, ENG, SLM, PRK, INV**              | **84 Components**                          | M3: Phase 3 Go-Live & Sign-Off               |
| **Phase 4** | **Administration, Estates & Welfare** | Internal municipal HR, asset protection, legal & DBT schemes     | **HRM, MPM, LGL, GSC**                   | **65 Components**                          | M4: Phase 4 Go-Live & Final Handover         |
| **TOTAL**   | **Enterprise SaaS ERP**               | **Complete Municipal Operating System**                          | **19 Domain Modules + 1 Platform Admin** | **443 Components (415 Domain + 28 Admin)** | **Full Programme Handover**                  |

---

## Phase 1: Foundation & Revenue Core (155 Components)

### 1.1 [PTX] Property Tax & Revenue Management (33 Components)

- `PTX-P01`: Property registration and identification
- `PTX-P02`: Legacy data onboarding and state platform sync
- `PTX-P03`: Property survey and GIS reconciliation
- `PTX-P04`: Property data correction
- `PTX-P05`: New assessment – built property
- `PTX-P06`: Self-assessment by owner
- `PTX-P07`: Apartment / multi-unit assessment
- `PTX-P08`: Vacant land tax
- `PTX-P09`: Reassessment – addition, alteration, usage or occupancy change
- `PTX-P10`: General revision of rates and zones
- `PTX-P11`: Back-assessment of unassessed or under-assessed property
- `PTX-P12`: Setback verification and deviation penalty
- `PTX-P13`: Exemptions, concessions and category rebates
- `PTX-P14`: Auto-mutation from registration
- `PTX-P15`: Mutation by application
- `PTX-P16`: Bifurcation and amalgamation
- `PTX-P17`: Demolition and deletion
- `PTX-P18`: Periodic demand generation (half-yearly)
- `PTX-P19`: Bill amendment and demand correction
- `PTX-P20`: Bill distribution and notifications
- `PTX-P21`: Collection (online, counter, POS, BBPS)
- `PTX-P22`: Cheque bounce, receipt cancellation and refund
- `PTX-P23`: Daily reconciliation and remittance
- `PTX-P24`: Objection, revision petition and appeal
- `PTX-P25`: Interest, penalty and recovery
- `PTX-P26`: One-time settlement and interest waiver
- `PTX-P27`: Write-off and remission
- `PTX-P28`: Property tax certificates (NOC, dues clear)
- `PTX-P29`: Property tax complaints
- `PTX-P30`: Dashboards, DCB and compliance reporting
- `PTX-P31`: Part-area non-residential use and rooftop installations
- `PTX-P32`: Road and location classification for valuation
- `PTX-P33`: Self-declared commercial accommodation use

### 1.2 [WTR] Water, Sewerage & Utility Billing (32 Components)

- `WTR-W01`: New water connection
- `WTR-W02`: New sewerage / UGD connection
- `WTR-W03`: Regularisation of unauthorised connection
- `WTR-W04`: Bulk / apartment connection with sub-metering
- `WTR-W05`: Temporary connection
- `WTR-W06`: Ownership transfer
- `WTR-W07`: Usage or category change
- `WTR-W08`: Disconnection
- `WTR-W09`: Reconnection
- `WTR-W10`: Connection surrender / permanent closure
- `WTR-W11`: Meter installation, replacement and calibration
- `WTR-W12`: Meter reading and spot billing
- `WTR-W13`: Estimated and average billing
- `WTR-W14`: Unmetered flat-rate billing
- `WTR-W15`: Sewerage charge calculation
- `WTR-W16`: Bill generation, adjustment and dispatch
- `WTR-W17`: Collection (counters, digital, BBPS, mPOS)
- `WTR-W18`: Advance payment and deposit ledger
- `WTR-W19`: Dues recovery, interest and penalty
- `WTR-W20`: Defaulter management and red-notice workflow
- `WTR-W21`: Water supply schedule and pressure monitoring
- `WTR-W22`: Water quality testing and potability register
- `WTR-W23`: Bulk water management and NRW estimation
- `WTR-W24`: Pipeline maintenance and breakdown logging
- `WTR-W25`: UGD overflow and blockage clearance
- `WTR-W26`: STP / FSTP intake and discharge monitoring
- `WTR-W27`: Water tanker booking and delivery tracking
- `WTR-W28`: Consumer grievance redressing
- `WTR-W29`: Field inspection and tap testing
- `WTR-W30`: Consumer portal and WhatsApp self-service
- `WTR-W31`: Water & sewerage analytics and DCB reporting
- `WTR-W32`: Rainwater harvesting compliance verification

### 1.3 [GRV] Citizen Service Desk, Grievance & RTI (30 Components)

- `GRV-G01`: Omnichannel grievance intake
- `GRV-G02`: Citizen identity and contact verification
- `GRV-G03`: Auto-routing and ticket classification
- `GRV-G04`: WhatsApp conversational grievance assistant
- `GRV-G05`: Integration with Swachhata / state citizen platforms
- `GRV-G06`: Location geotagging and ward resolution
- `GRV-G07`: Duplicate detection and ticket merging
- `GRV-G08`: Priority and VIP grievance assignment
- `GRV-G09`: SLA calculation and countdown tracking
- `GRV-G10`: Field staff work assignment and dispatch
- `GRV-G11`: Mobile field resolution and photo evidence capture
- `GRV-G12`: Internal transfer and inter-department referral
- `GRV-G13`: Work extension request and approval
- `GRV-G14`: Reopening of unresolved grievances
- `GRV-G15`: Automated escalation and alerts
- `GRV-G16`: Quality audit of resolved complaints
- `GRV-G17`: Citizen feedback and satisfaction rating
- `GRV-G18`: Call centre agent console and outbound IVRS
- `GRV-G19`: Bulk notification and ward announcement broadcasts
- `GRV-G20`: RTI application intake and fee payment
- `GRV-G21`: RTI routing to PIO / APIO
- `GRV-G22`: RTI response preparation and document upload
- `GRV-G23`: RTI first appeal and appellate authority workflow
- `GRV-G24`: RTI second appeal (State Information Commission sync)
- `GRV-G25`: Proactive disclosure register (Section 4 RTI)
- `GRV-G26`: Grievance and RTI dashboards and heatmap
- `GRV-G27`: Ward committee and councillor grievance review
- `GRV-G28`: SLA compliance reporting for commissioner
- `GRV-G29`: Chronic complaint hotspot analysis
- `GRV-G30`: Citizen happiness index tracking

### 1.4 [FIN] Finance & Accounting (30 Components)

- `FIN-F01`: Chart of accounts and NMAM compliance
- `FIN-F02`: Financial year opening and period lock
- `FIN-F03`: Budget preparation, estimates and BE/RE compilation
- `FIN-F04`: Budget allocation, allotment and re-appropriation
- `FIN-F05`: Budgetary control and commitment tracking
- `FIN-F06`: Double-entry journal voucher processing
- `FIN-F07`: Automated revenue collection journals
- `FIN-F08`: Vendor and contractor bill passing
- `FIN-F09`: Payment order and multi-signatory authorisation
- `FIN-F10`: Electronic payment disbursement (e-Payment / PFMS)
- `FIN-F11`: Bank account master and treasury liaison
- `FIN-F12`: Automated bank reconciliation statement (BRS)
- `FIN-F13`: Petty cash and imprest account management
- `FIN-F14`: Inter-bank fund transfers and investment register
- `FIN-F15`: Grants management (State Finance Commission, 15th FC)
- `FIN-F16`: Scheme-wise fund tracking and utilisation certificates (UC)
- `FIN-F17`: Municipal loan and debt servicing register
- `FIN-F18`: TDS and tax deduction at source processing
- `FIN-F19`: GST filing, input tax credit and return generation
- `FIN-F20`: Labour cess and statutory deduction accounting
- `FIN-F21`: Fixed asset capitalisation and depreciation
- `FIN-F22`: General ledger, trial balance and cash book
- `FIN-F23`: Receipt and payment account generation
- `FIN-F24`: Income and expenditure statement
- `FIN-F25`: Balance sheet generation
- `FIN-F26`: Internal audit queries and para management
- `FIN-F27`: CAG / Local Fund Audit (LFA) compliance tracking
- `FIN-F28`: Real-time financial dashboard and liquidity monitor
- `FIN-F29`: Municipal bonds and credit rating tracking
- `FIN-F30`: Year-end closing and financial statement publishing

### 1.5 [DMS] Document Management System (30 Components)

- `DMS-D01`: Document intake from ERP modules
- `DMS-D02`: Direct document upload and scanning
- `DMS-D03`: Optical character recognition (OCR) and text extraction
- `DMS-D04`: Automated classification and metadata tagging
- `DMS-D05`: Barcode and QR code generation for physical files
- `DMS-D06`: Integration with DigiLocker for document fetching
- `DMS-D07`: Property dossier compilation and chain-of-title linking
- `DMS-D08`: Version control, revision tracking and audit trail
- `DMS-D09`: Electronic signing (Aadhaar eSign, DSC USB token)
- `DMS-D10`: Document stamping, watermarking and redaction
- `DMS-D11`: E-noting and green sheet processing
- `DMS-D12`: File movement and dispatch register
- `DMS-D13`: Document access control and confidentiality levels
- `DMS-D14`: Full-text search and faceted document retrieval
- `DMS-D15`: Document expiry, renewal alert and retention policies
- `DMS-D16`: Archival and record room indexation
- `DMS-D17`: Document disposal and shredding compliance
- `DMS-D18`: Physical document tracking (RFID / barcode in record room)
- `DMS-D19`: Bulk document export for audits and courts
- `DMS-D20`: Document sharing via secure time-limited links
- `DMS-D21`: Template management for official orders and NOCs
- `DMS-D22`: Gazette notification repository
- `DMS-D23`: Municipal council resolutions and minutes archive
- `DMS-D24`: Legacy record digitisation tracking
- `DMS-D25`: Public records portal (citizen document access)
- `DMS-D26`: RTI document bundle preparation
- `DMS-D27`: Storage quota and deduplication management
- `DMS-D28`: Document access logs and audit reporting
- `DMS-D29`: Integrity verification and tamper detection (Blockchain anchoring)
- `DMS-D30`: Central document dashboard and metrics

---

## Phase 2: Regulation & Licensing (111 Components)

### 2.1 [TRL] Trade Licence Management (26 Components)

- `TRL-T01`: New trade licence application
- `TRL-T02`: Trade classification and schedule-of-fees mapping
- `TRL-T03`: Dangerous and offensive (D&O) trade scrutiny
- `TRL-T04`: Co-living, hostel and paying-guest licensing
- `TRL-T05`: Factory and industrial establishment licence
- `TRL-T06`: Food and beverage establishment scrutiny
- `TRL-T07`: Trade licence renewal (auto and scrutiny-based)
- `TRL-T08`: Trade amendment (name, ownership, location, area)
- `TRL-T09`: Trade licence cancellation and suspension
- `TRL-T10`: Trade closure and surrender
- `TRL-T11`: Site inspection and verification by health inspector
- `TRL-T12`: Document scrutiny and NOC validation
- `TRL-T13`: Trade licence fee calculation and penalties
- `TRL-T14`: Provisional trade licence issuance
- `TRL-T15`: Final licence generation with QR verification
- `TRL-T16`: Inter-module Fire NOC status verification
- `TRL-T17`: Property tax dues clearance validation
- `TRL-T18`: Trade licence certificate reprint and duplicate
- `TRL-T19`: Unlicensed trade survey and identification
- `TRL-T20`: Show-cause notice and enforcement action
- `TRL-T21`: Trade seizure and sealing workflow
- `TRL-T22`: Street vending zone demarcation and survey
- `TRL-T23`: Street vendor ID card and certificate of vending
- `TRL-T24`: Trade licence demand, collection and balance (DCB)
- `TRL-T25`: WhatsApp and SMS renewal reminders
- `TRL-T26`: Trade licensing dashboards and revenue forecasting

### 2.2 [UCH] User Charges Management (23 Components)

- `UCH-U01`: Automated user charge registration from property data
- `UCH-U02`: Bulk waste generator (BWG) charge setup
- `UCH-U03`: Commercial waste collection fee assessment
- `UCH-U04`: Septage and sewage collection charges
- `UCH-U05`: Trade waste and special bio-waste surcharge
- `UCH-U06`: Street cutting and road restoration fee
- `UCH-U07`: Combined utility billing with property / water
- `UCH-U08`: Standalone user charge demand generation
- `UCH-U09`: Spot fines and sanitation violation penalties
- `UCH-U10`: User charge collection (POS, digital, counter)
- `UCH-U11`: Advance user charge payment ledger
- `UCH-U12`: Defaulter escalation and compounding interest
- `UCH-U13`: Exemption and concession management
- `UCH-U14`: Field sanitation inspector collection sync
- `UCH-U15`: Direct debit and recurring mandate processing
- `UCH-U16`: User charge revision and notification workflow
- `UCH-U17`: Reconciliation and bank remittance
- `UCH-U18`: Citizen protest and charge recalculation
- `UCH-U19`: User charge demand-collection-balance (DCB)
- `UCH-U20`: Mobile notification and invoice delivery
- `UCH-U21`: Public parking fees and contractor collection
- `UCH-U22`: Hoarding, banner and advertisement display fees
- `UCH-U23`: Comprehensive user charges analytics dashboard

### 2.3 [BPM] Building Permissions (22 Components)

- `BPM-B01`: Building permission application intake (TG-bPASS mode)
- `BPM-B02`: Instant approval / self-certification for small plots
- `BPM-B03`: Single-window clearance for medium / large structures
- `BPM-B04`: Pre-construction document validation
- `BPM-B05`: Auto-DCR CAD drawing scrutiny and rule check
- `BPM-B06`: Master plan zoning and land use verification
- `BPM-B07`: Multi-department NOC coordination
- `BPM-B08`: Site inspection scheduling and geo-tagged reports
- `BPM-B09`: Fee calculation, betterment charges and mortgage deed
- `BPM-B10`: Building permit issuance with security barcode
- `BPM-B11`: Permission revocation, cancellation and modification
- `BPM-B12`: Construction stage inspection (plinth, roof level)
- `BPM-B13`: Work commencement notice and inspection logging
- `BPM-B14`: Deviation detection and compounding penalty
- `BPM-B15`: Occupancy certificate (OC) application and issuance
- `BPM-B16`: Partial occupancy certificate
- `BPM-B17`: Demolition permission and debris disposal plan
- `BPM-B18`: Unauthorised construction detection and show cause
- `BPM-B19`: Building sealing and demolition enforcement workflow
- `BPM-B20`: Architect / engineer registration and blacklisting
- `BPM-B21`: Public building register and status transparency
- `BPM-B22`: Building permission analytics and revenue tracking

### 2.4 [TPL] Town Planning (23 Components)

- `TPL-P01`: Master plan GIS layer management and zone lookups
- `TPL-P02`: Change of land use (CLU) application and processing
- `TPL-P03`: Zoning certificate issuance
- `TPL-P04`: Land acquisition and compensation tracking
- `TPL-P05`: Alignment drawing and road widening reservations
- `TPL-P06`: Layout permission application intake
- `TPL-P07`: Layout scrutiny and technical sanction
- `TPL-P08`: Open space and road dedication deeds
- `TPL-P09`: Final layout approval and plot release
- `TPL-P10`: Gated community and township layout clearance
- `TPL-P11`: Layout regularisation scheme (LRS) intake
- `TPL-P12`: LRS scrutiny, penalty calculation and approval
- `TPL-P13`: Unapproved layout detection and red-flagging
- `TPL-P14`: Transferable development rights (TDR) issuance
- `TPL-P15`: TDR bank, ledger and trade validation
- `TPL-P16`: TDR utilisation against building permission
- `TPL-P17`: Heritage structure and conservation zone monitoring
- `TPL-P18`: Lake / waterbody buffer zone enforcement
- `TPL-P19`: Encroachment reporting and field removal tracking
- `TPL-P20`: Town planning notices and orders repository
- `TPL-P21`: Town planning committee resolution records
- `TPL-P22`: Public scrutiny and objections register
- `TPL-P23`: Town planning spatial analytics and growth forecasting

### 2.5 [FNC] Fire NOC Management (17 Components)

- `FNC-N01`: Integration with State Disaster Response and Fire Service
- `FNC-N02`: Fire safety classification and risk grading
- `FNC-N03`: Provisional Fire NOC application for buildings
- `FNC-N04`: Final Occupancy Fire NOC processing
- `FNC-N05`: Fire NOC renewal application
- `FNC-N06`: Event and temporary structure fire safety clearance
- `FNC-N07`: Fire safety checklist verification and equipment audit
- `FNC-N08`: Joint inspection with fire department officers
- `FNC-N09`: Fire safety fee and penalty calculation
- `FNC-N10`: Fire NOC digital certificate issuance with QR
- `FNC-N11`: Automatic periodic fire audit reminders
- `FNC-N12`: Non-compliance notices and evacuation alerts
- `FNC-N13`: Fire NOC revocation and building sealing trigger
- `FNC-N14`: Commercial hazardous material storage verification
- `FNC-N15`: GIS fire risk mapping and hydrant proximity view
- `FNC-N16`: Fire incident reporting and post-disaster audit
- `FNC-N17`: Fire safety compliance dashboard and metrics

---

## Phase 3: Field Operations & Infrastructure (84 Components)

### 3.1 [SWM] Solid Waste Management (17 Components)

- `SWM-S01`: Waste generator categorization and master register
- `SWM-S02`: Bulk waste generator (BWG) on-site processing audit
- `SWM-S03`: Door-to-door collection tracking and RFID logging
- `SWM-S04`: Sanitation worker attendance and route allocation
- `SWM-S05`: Secondary collection and community bin monitoring
- `SWM-S06`: Fleet tracking, route optimisation and GPS playback
- `SWM-S07`: Transfer station intake and weighbridge integration
- `SWM-S08`: Processing facility / compost plant monitoring
- `SWM-S09`: Construction and demolition (C&D) waste pickup
- `SWM-S10`: Hazardous, electronic and sanitary waste logging
- `SWM-S11`: Dump yard / landfill bio-mining and capping tracking
- `SWM-S12`: Blackspot identification and clearance verification
- `SWM-S13`: Swachh Auto Tipper (SAT) maintenance and fuel log
- `SWM-S14`: Ragpicker and informal waste worker formalisation
- `SWM-S15`: Swachh Survekshan indicator tracking and audit
- `SWM-S16`: Citizen waste reporting (overflowing bin, burning)
- `SWM-S17`: Solid waste management operations dashboard

### 3.2 [ENG] Engineering Projects & e-MB (20 Components)

- `ENG-E01`: Works demand generation and council proposal
- `ENG-E02`: Administrative sanction (AS) workflow
- `ENG-E03`: Detailed project report (DPR) and estimate preparation
- `ENG-E04`: Technical sanction (TS) with standard schedule of rates
- `ENG-E05`: Tender preparation and e-Procurement sync
- `ENG-E06`: Work order issuance and contractor assignment
- `ENG-E07`: Milestone planning and project scheduling
- `ENG-E08`: Electronic Measurement Book (e-MB) entry
- `ENG-E09`: Quality control (QC) inspection and test certificate
- `ENG-E10`: Contractor work bill generation from e-MB
- `ENG-E11`: Bill scrutiny, statutory deduction and passing
- `ENG-E12`: Running account (RA) and final bill settlement
- `ENG-E13`: Defect liability period (DLP) and retention release
- `ENG-E14`: Work completion certificate issuance
- `ENG-E15`: GIS project geotagging and progress photo logging
- `ENG-E16`: Road asset register and trenching permission
- `ENG-E17`: Contractor performance rating and blacklisting
- `ENG-E18`: Cost escalation and time extension approvals
- `ENG-E19`: Works audit queries and vigilance enquiry tracking
- `ENG-E20`: Engineering projects executive dashboard

### 3.3 [SLM] Street Light Management (12 Components)

- `SLM-L01`: Street light pole and fixture GIS asset inventory
- `SLM-L02`: Centralised Control and Monitoring System (CCMS) sync
- `SLM-L03`: Fault detection and citizen outage complaint intake
- `SLM-L04`: Auto-dispatch to electrical maintenance contractor
- `SLM-L05`: Field repair verification and before/after photo proof
- `SLM-L06`: Automated switching schedules and dimmer controls
- `SLM-L07`: Burning hours analysis and energy consumption tracking
- `SLM-L08`: Electricity DISCOM meter reading and bill audit
- `SLM-L09`: LED conversion and energy performance contracting
- `SLM-L10`: Preventative maintenance schedule and replacement log
- `SLM-L11`: Contractor SLA and penalty deduction calculator
- `SLM-L12`: Street light operations dashboard and uptime tracker

### 3.4 [PRK] Parks & Horticulture Management (18 Components)

- `PRK-K01`: Municipal park and open space GIS asset register
- `PRK-K02`: Urban tree census and QR-tagging register
- `PRK-K03`: Park maintenance contract management and inspections
- `PRK-K04`: Playground equipment and asset safety check
- `PRK-K05`: Nursery management and plant sapling inventory
- `PRK-K06`: Green belt and central median plantation log
- `PRK-K07`: Haritha Haram / urban greening campaign tracking
- `PRK-K08`: Water supply and sprinkler automation monitoring
- `PRK-K09`: Composting of garden waste in parks
- `PRK-K10`: Park entry ticketing and visitor pass issuance
- `PRK-K11`: Booking of parks / open spaces for public events
- `PRK-K12`: Commercial food kiosk and parking leases in parks
- `PRK-K13`: Vandalism and damage reporting in parks
- `PRK-K14`: Corporate social responsibility (CSR) adoption of parks
- `PRK-K15`: Tree felling / pruning permission and inspection
- `PRK-K16`: Compensatory afforestation tracking and compliance
- `PRK-K17`: Biodiversity register and fauna documentation
- `PRK-K18`: Parks & horticulture dashboard and canopy coverage

### 3.5 [INV] Inventory & Stores (17 Components)

- `INV-V01`: Master item catalogue and classification
- `INV-V02`: Central store and divisional warehouse register
- `INV-V03`: Stock level monitoring and reorder point alerts
- `INV-V04`: Departmental indent intake and approval
- `INV-V05`: Purchase order (PO) generation and vendor linkage
- `INV-V06`: Goods receipt note (GRN) and gate pass logging
- `INV-V07`: Material inspection and quality acceptance
- `INV-V08`: Stock issuance and transfer between departmental stores
- `INV-V09`: Stock return and repair tracking
- `INV-V10`: Scrap, condemned item and auction management
- `INV-V11`: Fuel inventory and vehicle refuelling slip log
- `INV-V12`: Annual physical stock verification and reconciliation
- `INV-V13`: Stock valuation methods (FIFO / Weighted Average)
- `INV-V14`: Emergency procurement and disaster stockpile
- `INV-V15`: Vendor delivery performance and lead time analysis
- `INV-V16`: Integration with Finance module for store ledger
- `INV-V17`: Central stores executive dashboard and stock ledger

---

## Phase 4: Administration, Estates & Welfare (65 Components)

### 4.1 [HRM] Payroll & HR Management (19 Components)

- `HRM-H01`: Sanctioned post and establishment schedule
- `HRM-H02`: Electronic Service Register (e-SR) for municipal staff
- `HRM-H03`: Employee onboarding, deputation and contract staff
- `HRM-H04`: Transfer and posting order processing
- `HRM-H05`: Biometric / geo-fenced attendance tracking
- `HRM-H06`: Leave application, encashment and surrender
- `HRM-H07`: Tour, travel allowance (TA/DA) and advance
- `HRM-H08`: Medical reimbursement claim processing
- `HRM-H09`: Monthly payroll processing and pay-bill passing
- `HRM-H10`: Statutory deductions (CPS/NPS, GPF, PT, IT TDS)
- `HRM-H11`: Festival and special advance disbursement
- `HRM-H12`: Annual increments and promotion workflows
- `HRM-H13`: Disciplinary proceedings and charge memo tracking
- `HRM-H14`: Performance appraisal (PAR / APAR) workflow
- `HRM-H15`: Staff training, capacity building and certifications
- `HRM-H16`: Retirement, superannuation and pension processing
- `HRM-H17`: Gratuity and terminal benefits calculation
- `HRM-H18`: Outsource labour agency billing and compliance
- `HRM-H19`: HR & payroll executive dashboard and headcount stats

### 4.2 [MPM] Municipal Property Management (15 Components)

- `MPM-M01`: Municipal immovable property and land register
- `MPM-M02`: GIS geotagging and boundary demarcation of lands
- `MPM-M03`: Title deed, revenue survey number and patta vault
- `MPM-M04`: Vacant municipal land bank and future use zoning
- `MPM-M05`: Municipal commercial complex and market stall master
- `MPM-M06`: Auction, lease allocation and tenancy agreement
- `MPM-M07`: Lease rent periodic demand and escalation
- `MPM-M08`: Rent collection, receipt generation and arrears
- `MPM-M09`: Lease transfer, subletting and tenancy renewal
- `MPM-M10`: Eviction of overstayed tenants and recovery notices
- `MPM-M11`: Encroachment alert, drone surveillance and removal
- `MPM-M12`: Municipal asset valuation and insurance portfolio
- `MPM-M13`: Maintenance and civil works expenditure tracking
- `MPM-M14`: Revenue sharing from hoardings, towers and ATMs
- `MPM-M15`: Municipal property revenue and asset dashboard

### 4.3 [LGL] Legal Case Management (17 Components)

- `LGL-J01`: Court case registration and litigation tracking
- `LGL-J02`: eCourts / High Court CNR number synchronization
- `LGL-J03`: Departmental assignment and Standing Counsel mapping
- `LGL-J04`: Notice, summon and writ petition document upload
- `LGL-J05`: Counter affidavit and parawise remark drafting
- `LGL-J06`: Hearing date calendar, cause list and diary
- `LGL-J07`: Limitation period calculation and urgency alerts
- `LGL-J08`: Interim stay order and injunction tracking
- `LGL-J09`: Contempt of court warning and priority escalations
- `LGL-J10`: Judgement and final decree repository
- `LGL-J11`: Appeal filing recommendation and deadline tracker
- `LGL-J12`: Legal fee bill verification and payment sanction
- `LGL-J13`: Out-of-court settlement and Lok Adalat matters
- `LGL-J14`: Departmental enquiry and legal opinion requests
- `LGL-J15`: Advocate performance monitoring and empanelment
- `LGL-J16`: Municipal law, rule and bylaw master database
- `LGL-J17`: Legal risk and litigation summary dashboard

### 4.4 [GSC] Government Schemes (14 Components)

- `GSC-C01`: Central and State welfare scheme catalogue
- `GSC-C02`: Beneficiary survey, application intake and KYC
- `GSC-C03`: Socio-economic eligibility scoring and validation
- `GSC-C04`: PMAY-Urban housing application and stage tracking
- `GSC-C05`: Geo-tagged construction stage verification for housing
- `GSC-C06`: Housing allotment lottery and patta certificate
- `GSC-C07`: PM SVANidhi street vendor micro-credit loan link
- `GSC-C08`: Self-Help Group (SHG / MEPMA) group registration
- `GSC-C09`: SHG bank linkage and revolving fund tracking
- `GSC-C10`: Direct Benefit Transfer (DBT) sanction and mandate
- `GSC-C11`: Scheme utilisation certificate (UC) generation
- `GSC-C12`: Beneficiary grievance and assistance desk
- `GSC-C13`: Social audit and third-party verification reports
- `GSC-C14`: Welfare schemes executive dashboard and coverage heatmap

## Level 0: Platform Super Admin ("The Boss") Module: [ADM] (28 Components)

Operates at the global multi-tenant control plane across all States (Tenants) and Cities (Sub-Tenants).

### 0.1 Executive Intelligence (4 Components)

- `ADM-A01`: **Global Command Dashboard** — Pan-state rollup of live revenue, total registered parcels, active grievances, and citizen digital adoption.
- `ADM-A02`: **State & City Benchmarking Matrix** — Comparative league tables, DCB tax recovery percentages, grievance SLA compliance, and Swachh rankings.
- `ADM-A03`: **Consolidated Financial Ledger** — Central grants tracking (15th Finance Commission, AMRUT, SBM) and aggregated multi-tenant balance sheets.
- `ADM-A04`: **Spatial GIS Multi-City Viewer** — Cross-jurisdiction PostGIS map viewer displaying parcels, utilities, zones, and road networks across states.

### 0.2 Tenancy & Hierarchy (4 Components)

- `ADM-T01`: **State Tenant Provisioning** — Onboard and configure Level 1 State entities (e.g. Telangana `TG`, Maharashtra `MH`), timezone, and official language packs.
- `ADM-T02`: **Sub-Tenant (ULB / City) Provisioning** — Create Level 2 child entities (e.g. GWMC, GHMC, CDMA-TP) with ward/zone hierarchies and administrative grades.
- `ADM-T03`: **Tenant Lifecycle & Status Controls** — Suspend, lock, archive, decommission, or put specific tenant workspaces into maintenance mode.
- `ADM-T04`: **White-Labelling & Custom Domain Router** — CNAME mapping, SSL certificate binding, official state emblems, and municipal branding watermarks.

### 0.3 Modules & Subscriptions (4 Components)

- `ADM-S01`: **19-Module Master Catalogue** — Platform-wide repository of the 19 standard municipal modules and their 415 component definitions.
- `ADM-S02`: **State Module Subscription Allocator** — Assign, renew, or revoke module subscriptions for Level 1 State Tenants.
- `ADM-S03`: **Sub-Tenant Cascade Delegation Guard** — Rule engine ensuring child Sub-Tenants only receive module components authorized by their parent State.
- `ADM-S04`: **Quota & Usage Metering** — Per-tenant allocation and tracking of document storage caps (DigiLocker/S3), DLT SMS credits, and API rate limits.

### 0.4 Global Identity & RBAC (5 Components)

- `ADM-R01`: **Global User Administration & Invitations** — Multi-tier user directory to provision, invite, and manage Level 0, Level 1, and Level 2 users.
- `ADM-R02`: **Cross-Tenant Scope & Context Review** — Audit and manage users holding multi-jurisdiction scopes (e.g. regional state directors overseeing multiple ULBs).
- `ADM-R03`: **415 Component RBAC Engine** — Granular permission matrix builder managing `{MODULE}-{ID}:{ACTION}` access rights and role templates.
- `ADM-R04`: **Support Impersonation Hub** — Secure, time-limited, cryptographically audited "Log in as Tenant Officer" facility for Level 3 support.
- `ADM-R05`: **Universal SSO & Keycloak Realms** — Keycloak identity broker managing MeriPehchan, Aadhaar e-Pramaan, SAML/OIDC federations, and MFA rules.

### 0.5 Integrations & Compliance (5 Components)

- `ADM-C01`: **Central Gateway & Rate Limiting** — APISIX / Kong API gateway policies, per-tenant throttling, IP whitelisting, and WAF rules.
- `ADM-C02`: **Payment Switch & Escrow Hub** — Configure aggregator credentials (SBI ePay, BillDesk, Razorpay, BBPS) and route settlements to city treasury bank accounts.
- `ADM-C03`: **State Adapter Gateway** — Connectors for state-wide systems: IGRS land registration sync, eCourts CNR litigation sync, CGF/Treasury, and DISCOMs.
- `ADM-C04`: **CERT-In Immutable Audit Vault** — Append-only security audit log repository with cryptographic hash-chaining across all multi-tenant actions.
- `ADM-C05`: **Data Sovereignty & RLS Verification** — Continuous verification of PostgreSQL Row-Level Security policies to prevent cross-tenant data leakage.

### 0.6 Platform Fleet & Operations (6 Components)

- `ADM-O01`: **Microservice Cluster Health** — Real-time telemetry, pod topology, async worker queues, and connection pool latency for all 19 module services.
- `ADM-O02`: **Multi-Tenant Schema Migrator** — Rolling, zero-downtime database DDL migration executor across all tenant partitions.
- `ADM-O03`: **Scoped Cache Partition Purge** — Targeted invalidation of tenant Redis cache keys (`stats:tenant:{id}:*`) without flushing global shared cache.
- `ADM-O04`: **Backup & Disaster Recovery** — Scheduled snapshot policies, Point-in-Time-Recovery (PITR) drill triggers, and cross-region failover tests.
- `ADM-O05`: **Global Broadcast & Alert Banner** — Platform-wide or state-scoped maintenance notifications, emergency alerts, and system broadcast banners.
- `ADM-O06`: **Version & Release Registry** — Track deployed software versions, manage feature flags, and schedule rollout rings (Canary, Blue/Green).

---

## Component Totals Verification

- **Level 0 (Platform Super Admin - ADM)**: **28 Components**
- **Phase 1 (Domain Revenue Core)**: 33 (PTX) + 32 (WTR) + 30 (GRV) + 30 (FIN) + 30 (DMS) = **155 Components**
- **Phase 2 (Domain Regulation & Licensing)**: 26 (TRL) + 23 (UCH) + 22 (BPM) + 23 (TPL) + 17 (FNC) = **111 Components**
- **Phase 3 (Domain Field Operations & Infrastructure)**: 17 (SWM) + 20 (ENG) + 12 (SLM) + 18 (PRK) + 17 (INV) = **84 Components**
- **Phase 4 (Domain Administration, Estates & Welfare)**: 19 (HRM) + 15 (MPM) + 17 (LGL) + 14 (GSC) = **65 Components**
- **Grand Total Platform Scope**: 28 (Level 0 Admin) + 415 (19 Domain Modules) = **443 Granular RBAC Components**
