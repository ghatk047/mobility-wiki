#!/usr/bin/env python3
"""
taxonomy.py — Mobility & Micromobility Process Wiki catalogue.

18 L1 domains / 74 L2 groups / 357 processes, in three tiers:
  Tier 1  shared marketplace core        6 domains  122 processes
  Tier 2  archetype-specific operations  5 domains  120 processes
  Tier 3  cross-cutting enterprise       7 domains  115 processes

PID format: MM-{L1}-{L2}-{NN}
"""

# (icon, display name, url slug, tier)
L1_META = {
    # ── Tier 1 — shared marketplace core ────────────────────────────────────
    "MD": ("\U0001F500", "Marketplace Matching & Dispatch",       "marketplace-dispatch",   1),
    "PX": ("\U0001F4B2", "Dynamic Pricing & Incentives",          "pricing-incentives",     1),
    "SL": ("\U0001F464", "Driver, Courier & Rider Lifecycle",     "supply-lifecycle",       1),
    "TS": ("\U0001F6E1",  "Trust & Safety",                        "trust-safety",           1),
    "PF": ("\U0001F4B3", "Payments & Financial Operations",       "payments-finops",        1),
    "CX": ("\U0001F91D", "Customer Experience & Support",         "customer-experience",    1),
    # ── Tier 2 — archetype-specific operations ──────────────────────────────
    "AV": ("\U0001F916", "Autonomous Vehicle Operations",         "av-operations",          2),
    "MF": ("\U0001F6F4", "Micromobility Fleet Operations",        "micromobility-fleet",    2),
    "LM": ("\U0001F4E6", "Last-Mile Delivery Operations",         "last-mile-delivery",     2),
    "AM": ("\U0001F681", "eVTOL & Advanced Air Mobility",         "evtol-air-mobility",     2),
    "DD": ("\U0001F6F8", "Drone Delivery Operations",             "drone-delivery",         2),
    # ── Tier 3 — cross-cutting enterprise ───────────────────────────────────
    "VA": ("\U0001F697", "Vehicle & Asset Management",            "vehicle-asset",          3),
    "RC": ("⚖",      "Regulatory & Municipal Compliance",     "regulatory-compliance",  3),
    "TD": ("\U0001F5FA",  "Technology, Data & Mapping",            "technology-data",        3),
    "GM": ("\U0001F4E3", "Marketing & Growth",                    "marketing-growth",       3),
    "FN": ("\U0001F4B0", "Finance, Accounting & IR",              "finance-ir",             3),
    "HR": ("\U0001F465", "HR & Corporate Workforce",              "hr-workforce",           3),
    "SE": ("\U0001F33F", "Sustainability & Fleet Electrification", "sustainability",        3),
}

TIER_LABEL = {
    1: "Shared Marketplace Core",
    2: "Archetype-Specific Operations",
    3: "Cross-Cutting Enterprise",
}

# Which archetypes each L1 principally speaks to. Drives registry slice injection.
L1_ARCHETYPES = {
    "MD": ["ride-hail", "last-mile-delivery", "micromobility", "autonomous-ride-hail"],
    "PX": ["ride-hail", "last-mile-delivery", "micromobility"],
    "SL": ["ride-hail", "last-mile-delivery", "micromobility"],
    "TS": ["ride-hail", "last-mile-delivery", "micromobility", "autonomous-ride-hail"],
    "PF": ["ride-hail", "last-mile-delivery", "micromobility", "shared-enterprise"],
    "CX": ["ride-hail", "last-mile-delivery", "micromobility", "shared-enterprise"],
    "AV": ["autonomous-ride-hail"],
    "MF": ["micromobility"],
    "LM": ["last-mile-delivery"],
    "AM": ["evtol"],
    "DD": ["drone-delivery"],
    "VA": ["micromobility", "autonomous-ride-hail", "shared-enterprise"],
    "RC": ["ride-hail", "micromobility", "autonomous-ride-hail", "drone-delivery", "evtol"],
    "TD": ["ride-hail", "autonomous-ride-hail", "micromobility", "shared-enterprise"],
    "GM": ["ride-hail", "last-mile-delivery", "micromobility", "shared-enterprise"],
    "FN": ["shared-enterprise"],
    "HR": ["shared-enterprise"],
    "SE": ["micromobility", "shared-enterprise"],
}

# (l1, l2, l2_name, l2_slug, [process names])
TAXONOMY = [

# ═══════════════ TIER 1 — SHARED MARKETPLACE CORE (122) ═══════════════

("MD", "DM", "Demand Forecasting & Supply Positioning", "demand-supply-positioning", [
    "Short-Horizon Demand Forecasting by H3 Cell and Time Bucket",
    "Supply Positioning Guidance and Driver Heat Map Publication",
    "Event and Weather Demand Shock Modelling",
    "Marketplace Balance Monitoring and Undersupply Alerting",
    "Airport and Venue Queue Management",
    "Cross-Modal Supply Substitution Between Ride-Hail, Scooter and Delivery",
]),
("MD", "MA", "Matching & Assignment Engines", "matching-assignment", [
    "Rider-to-Driver Assignment and Dispatch Offer Generation",
    "Offer Acceptance, Timeout and Reoffer Cascade",
    "Autonomous Vehicle Eligibility Screening and Mixed-Fleet Assignment",
    "Courier Assignment for Merchant Order Pickup",
    "Reassignment After Driver Cancellation or No-Show",
    "Matching Model Deployment, Shadow Testing and Rollback",
]),
("MD", "RO", "Routing, ETA & Navigation", "routing-eta", [
    "Route Generation and Turn-by-Turn Navigation Delivery",
    "ETA Prediction and Residual Correction with DeepETA",
    "Pickup Point Selection and Complex Venue Handling",
    "Traffic Incident Ingestion and Dynamic Rerouting",
    "ETA Accuracy Monitoring and Model Drift Detection",
]),
("MD", "BA", "Batching, Pooling & Multi-Stop", "batching-pooling", [
    "Shared Ride Pooling and Co-Rider Matching",
    "Multi-Order Delivery Batching and Sequence Optimisation",
    "Multi-Stop Trip Construction and Waypoint Validation",
    "Batch Break-Up and De-Pooling on Service Risk",
    "Pooling Detour Tolerance and Rider Compensation Rules",
]),

("PX", "SP", "Surge & Dynamic Pricing", "surge-dynamic-pricing", [
    "Real-Time Surge Multiplier Calculation and Zone Publication",
    "Upfront Fare Quotation and Price Lock Management",
    "Price Elasticity Testing and Experiment Governance",
    "Surge Cap Enforcement During Declared Emergencies",
    "Fare Component Breakdown and Rider Price Transparency",
]),
("PX", "IN", "Supply-Side Incentives", "supply-incentives", [
    "Driver and Courier Quest and Streak Bonus Design",
    "Incentive Budget Allocation Across Markets",
    "Incentive Payout Calculation and Dispute Handling",
    "Incentive Effectiveness Measurement and Incrementality Testing",
    "Referral Bonus Programme Administration",
]),
("PX", "PR", "Demand Promotions & Discounts", "demand-promotions", [
    "Promotion Code Creation, Targeting and Redemption Control",
    "First-Ride and Win-Back Offer Campaigns",
    "Merchant-Funded and Platform-Funded Discount Split",
    "Promotion Abuse Detection and Code Throttling",
]),
("PX", "SB", "Subscriptions & Membership", "subscriptions", [
    "Membership Tier Design and Benefit Configuration",
    "Subscription Enrolment, Billing and Renewal",
    "Membership Churn Prediction and Save Offers",
    "Cross-Vertical Benefit Entitlement and Redemption",
]),

("SL", "ON", "Onboarding & Verification", "onboarding-verification", [
    "Driver and Courier Signup and Identity Verification",
    "Document Collection, OCR Extraction and Expiry Tracking",
    "Vehicle Inspection and Eligibility Verification",
    "Insurance Certificate Validation and Coverage Confirmation",
    "Market-Specific Licensing and TNC Permit Verification",
    "First-Trip Activation and Onboarding Funnel Recovery",
]),
("SL", "EN", "Engagement, Ratings & Quality", "engagement-ratings", [
    "Two-Sided Rating Collection and Aggregation",
    "Quality Score Calculation and Tiering",
    "Low-Rating Coaching and Improvement Pathways",
    "Acceptance and Completion Rate Monitoring",
    "Recognition Programmes and Top-Performer Benefits",
]),
("SL", "DA", "Deactivation, Appeals & Reinstatement", "deactivation-appeals", [
    "Deactivation Trigger Evaluation and Evidence Review",
    "Notice, Explanation and Statutory Deactivation Rights",
    "Appeal Intake, Independent Review and Determination",
    "Reinstatement, Reactivation Conditions and Monitoring",
]),
("SL", "RD", "Rider & Consumer Account Lifecycle", "rider-account-lifecycle", [
    "Consumer Registration, Verification and Fraud Screening",
    "Account Recovery and Credential Reset",
    "Consumer Standards Enforcement and Account Restriction",
    "Account Closure and Data Deletion Request Handling",
]),
("SL", "CL", "Gig Classification & Worker Benefits", "gig-classification", [
    "Worker Classification Assessment Under Prop 22 and State Tests",
    "Engaged-Time Earnings Guarantee Calculation and Top-Up",
    "Healthcare Stipend Eligibility and Disbursement",
    "Occupational Accident Coverage Administration",
]),

("TS", "BC", "Background Checks & Screening", "background-checks", [
    "Initial Criminal and Motor Vehicle Record Screening",
    "Continuous Monitoring and Re-Screening Cadence",
    "Adverse Action Notice and Adjudication Workflow",
    "Screening Vendor Management and Data Quality Assurance",
    "International Market Screening Equivalence Mapping",
    "Identity Re-Verification and Account Sharing Detection",
]),
("TS", "IR", "Incident Detection & Response", "incident-response", [
    "In-Trip Safety Signal Detection and Ride Check Triggering",
    "Emergency Assistance Button and Public Safety Handoff",
    "Post-Trip Safety Report Intake and Triage",
    "Serious Incident Investigation and Case Management",
    "Critical Incident Escalation and Executive Notification",
    "Safety Transparency Reporting and Disclosure",
]),
("TS", "IC", "Insurance & Claims", "insurance-claims", [
    "Period-Based Insurance Coverage Determination",
    "First Notice of Loss Intake and Claim Setup",
    "Claim Investigation, Liability Assessment and Reserve Setting",
    "Third-Party Bodily Injury and Property Damage Settlement",
    "Insurance Programme Renewal and Captive Risk Retention",
]),
("TS", "FR", "Fraud, Abuse & Account Integrity", "fraud-integrity", [
    "Payment Fraud Detection and Transaction Blocking",
    "Collusive Driver-Rider Fraud Ring Detection",
    "GPS Spoofing and Trip Manipulation Detection",
    "Promotion and Incentive Abuse Investigation",
    "Account Takeover Detection and Remediation",
]),

("PF", "RP", "Consumer Payments", "consumer-payments", [
    "Payment Method Tokenisation and Vaulting",
    "Trip and Order Authorisation, Capture and Settlement",
    "Failed Payment Retry and Outstanding Balance Recovery",
    "Refund, Credit and Goodwill Adjustment Processing",
    "Chargeback Representment and Dispute Defence",
]),
("PF", "PO", "Driver, Courier & Merchant Payouts", "payouts", [
    "Earnings Calculation and Trip-Level Ledger Posting",
    "Weekly Payout Run and Bank Disbursement",
    "Instant Cash-Out and Real-Time Payment Rails",
    "Merchant Settlement and Commission Netting",
    "Payout Failure Investigation and Reissue",
]),
("PF", "TX", "Tax, 1099 & Cross-Border", "tax-compliance", [
    "1099-NEC and 1099-K Preparation and Furnishing",
    "Taxpayer Identification Collection and TIN Matching",
    "Sales, Use and Marketplace Facilitator Tax Remittance",
    "VAT and GST Determination for International Markets",
    "Cross-Border Payout FX Management and Transfer Pricing",
]),
("PF", "RC", "Revenue Recognition & Reconciliation", "revenue-reconciliation", [
    "Gross Bookings to Net Revenue Bridge Construction",
    "Payment Processor Reconciliation and Break Investigation",
    "Deferred Revenue and Subscription Recognition",
    "Unclaimed Property and Escheatment Handling",
]),

("CX", "SU", "Support Operations & Contact Handling", "support-operations", [
    "Contact Routing, Prioritisation and Queue Management",
    "In-App Self-Service Deflection and Help Content",
    "Live Agent Handling and Escalation Pathways",
    "Support Workforce Forecasting and Scheduling",
    "Support Quality Assurance and Agent Coaching",
]),
("CX", "RS", "Resolution, Refunds & Adjustments", "resolution-refunds", [
    "Fare and Order Adjustment Adjudication",
    "Missing, Incorrect and Damaged Order Resolution",
    "Lost Item Recovery and Return Coordination",
    "Cancellation Fee Waiver Determination",
    "Goodwill Credit Policy and Abuse Control",
]),
("CX", "AC", "Accessibility & Inclusive Service", "accessibility", [
    "Wheelchair Accessible Vehicle Request Fulfilment",
    "Service Animal Policy Enforcement and Denial Investigation",
    "Assistive Technology and Screen Reader Compatibility",
    "Non-Smartphone and Low-Connectivity Access Channels",
]),
("CX", "VO", "Voice of Customer & CSAT", "voice-of-customer", [
    "CSAT and NPS Instrumentation and Sampling",
    "Verbatim Feedback Classification and Theme Extraction",
    "Regulator and Media Complaint Handling",
    "Closed-Loop Feedback to Product and Operations",
]),

# ═══════════════ TIER 2 — ARCHETYPE-SPECIFIC OPERATIONS (120) ═══════════════

("AV", "FO", "Driverless Fleet & Depot Operations", "driverless-fleet-ops", [
    "Daily Fleet Readiness Check and Release to Service",
    "Depot Charging, Cleaning and Turnaround Sequencing",
    "Sensor Calibration and Pre-Departure Validation",
    "Autonomous Dispatch to Demand and Idle Vehicle Staging",
    "Vehicle Recovery and Roadside Retrieval",
    "Fleet Availability Monitoring and Service Level Management",
    "End-of-Day Return, Data Offload and Overnight Servicing",
]),
("AV", "RA", "Remote Assistance & Fleet Response", "remote-assistance", [
    "Remote Assistance Request Triage and Operator Assignment",
    "Guidance Provision for Ambiguous Road Scenarios",
    "Field Fleet Response Dispatch to Stranded Vehicle",
    "Emergency Responder Interaction and Vehicle Handover",
    "Passenger-Initiated Support During a Driverless Ride",
    "Remote Assistance Event Logging and Pattern Analysis",
]),
("AV", "SV", "Safety Case, Disengagement & Incident Reporting", "safety-disengagement", [
    "Disengagement Capture, Classification and Root Cause Analysis",
    "Annual DMV Disengagement and Collision Report Preparation",
    "Collision Investigation and Regulator Notification",
    "Safety Case Construction and Evidence Assurance",
    "Simulation Regression Testing of Incident Scenarios",
    "Operational Design Domain Restriction and Service Suspension",
]),
("AV", "PM", "AV Permitting & Market Launch", "av-permitting-launch", [
    "State AV Testing and Deployment Permit Application",
    "CPUC Driverless Deployment Authority Filing",
    "New Market Mapping, Validation and Geofence Definition",
    "Closed-Course and Supervised Public Road Validation",
    "Public Service Opening and Rider Waitlist Release",
    "Geofence Expansion and Freeway Operations Authorisation",
]),

("MF", "CH", "Charging, Battery Swap & Energy", "charging-energy", [
    "Battery State of Charge Monitoring and Swap Prioritisation",
    "Field Battery Swap Route Planning and Execution",
    "Warehouse Charging Bay Operations and Throughput Management",
    "Gig Charger Network Onboarding and Task Payout",
    "Battery Health Diagnostics and Cell Degradation Tracking",
    "Charging Energy Cost Management and Tariff Optimisation",
]),
("MF", "RB", "Rebalancing & Redistribution", "rebalancing", [
    "Demand-Driven Redistribution Target Setting by Zone",
    "Rebalancing Van Route Planning and Load Optimisation",
    "Overnight Sweep and Morning Deployment Execution",
    "Clustering and Vehicle Pile-Up Remediation",
    "Redistribution Cost per Vehicle Tracking and Optimisation",
    "Seasonal and Weather-Driven Fleet Withdrawal",
]),
("MF", "IO", "Vehicle Telemetry, IoT & Diagnostics", "telemetry-iot", [
    "IoT Module Provisioning and SIM Lifecycle Management",
    "Real-Time Vehicle State Ingestion and Event Streaming",
    "Remote Lock, Unlock and Immobilisation Commands",
    "Fault Code Detection and Automatic Out-of-Service Flagging",
    "Firmware Over-the-Air Update Rollout and Rollback",
    "GPS Drift and Location Accuracy Remediation",
    "Vehicle Loss, Theft and Recovery Tracking",
]),
("MF", "PK", "Parking, Right-of-Way & Rider Compliance", "parking-compliance", [
    "Geofence Configuration for No-Ride, Slow and No-Park Zones",
    "End-of-Ride Parking Photo Verification and Adjudication",
    "AI On-Vehicle Detection of Sidewalk and Tandem Riding",
    "Improper Parking Report Intake and Field Response",
    "Municipal Impound Recovery and Fine Processing",
    "Rider Education, Warnings and Progressive Enforcement",
]),

("LM", "MI", "Merchant Integration & Menu Operations", "merchant-integration", [
    "Merchant Onboarding, Verification and Store Activation",
    "POS Integration and Order Injection Configuration",
    "Menu Ingestion, Modifier Mapping and Photo Enrichment",
    "Price and Availability Synchronisation",
    "Store Hours, Holiday and Temporary Closure Management",
    "Merchant Performance Monitoring and Remediation",
]),
("LM", "CA", "Courier Assignment & Dispatch Quality", "courier-dispatch", [
    "Order Readiness Prediction and Courier Arrival Timing",
    "Courier Offer Construction and Pay Transparency",
    "Wait-Time Management and Merchant Delay Handling",
    "Multi-Apping and Concurrent Order Detection",
    "Dispatch Quality Monitoring and Late Order Intervention",
    "Peak Period Supply Shortfall and Order Throttling",
]),
("LM", "OF", "Order Fulfilment & Handoff", "order-fulfilment", [
    "Order Placement, Confirmation and Merchant Acceptance",
    "Pickup Verification and Order Contents Confirmation",
    "Contactless Delivery and Drop-Off Photo Proof",
    "Alcohol and Age-Restricted Item Delivery Verification",
    "Undeliverable Order Handling and Disposition",
    "Substitution and Out-of-Stock Resolution for Retail Orders",
]),
("LM", "DS", "Dark Stores, Ghost Kitchens & Retail", "dark-stores-retail", [
    "Ghost Kitchen Site Selection and Virtual Brand Launch",
    "Dark Store Inventory Accuracy and Replenishment",
    "In-Store Shopper Picking and Staging Operations",
    "Grocery and Convenience Catalogue Management",
    "Cold Chain Handling for Grocery and Pharmacy Orders",
    "Retail Partner Fulfilment SLA Management",
]),

("AM", "CE", "Type Certification & Airworthiness", "type-certification", [
    "Certification Basis Negotiation and Means of Compliance Agreement",
    "Conforming Aircraft Build and Configuration Control",
    "Structural, Propulsion and Systems Compliance Testing",
    "Type Inspection Authorization Readiness and FAA Flight Test",
    "Production Certificate and Manufacturing Conformity",
    "International Validation and Bilateral Certification Pathways",
]),
("AM", "FL", "Flight Operations & Part 135", "flight-operations", [
    "Part 135 Air Carrier Certificate Application and Proving Runs",
    "Operations Specifications Development and Amendment",
    "Pilot Type Rating, Training and Currency Management",
    "Flight Release, Dispatch and Weight and Balance",
    "Continuing Airworthiness and Maintenance Control",
    "Safety Management System and Voluntary Reporting",
]),
("AM", "VP", "Vertiport Operations & Ground Handling", "vertiport-operations", [
    "Vertiport Site Selection, Design and Regulatory Approval",
    "Vertiport Slot Allocation and Schedule Coordination",
    "Aircraft Turnaround, Charging and Ground Servicing",
    "Passenger Processing, Security and Boarding",
    "Vertipad Surface Operations and Ground Movement Control",
    "Adverse Weather and Vertiport Capacity Reduction",
]),
("AM", "AT", "Airspace Integration & UAM Traffic Management", "airspace-integration", [
    "UAM Corridor Definition and Route Structure Design",
    "PSU Service Onboarding and Operational Intent Sharing",
    "Strategic Deconfliction and Demand Capacity Balancing",
    "Tactical Separation and Off-Nominal Operations Support",
    "ATC Coordination at Controlled Airspace Boundaries",
]),

("DD", "RG", "BVLOS Authorisation & Regulatory Pathway", "bvlos-authorisation", [
    "Part 107 Waiver Application and Justification Package",
    "Part 135 Air Carrier Certification for Package Delivery",
    "Proposed Part 108 Readiness Assessment and Gap Analysis",
    "Operational Risk Assessment and SORA-Style Safety Case",
    "Community Engagement and Noise Impact Consultation",
    "State and Local Drone Ordinance Compliance Mapping",
]),
("DD", "FO", "Flight Operations & Nest Management", "drone-flight-ops", [
    "Nest Site Selection, Build-Out and Commissioning",
    "Daily Airworthiness Check and Aircraft Release",
    "Mission Planning, Launch Authorisation and Monitoring",
    "Remote Pilot Supervision and Multi-Aircraft Ratio Management",
    "Aborted Mission and Return-to-Nest Handling",
    "Aircraft Maintenance, Battery Cycling and Component Retirement",
]),
("DD", "PH", "Package Handling, Loading & Handoff", "package-handling", [
    "Order Eligibility Screening by Weight, Size and Contents",
    "Package Preparation, Containerisation and Loading",
    "Delivery Zone Suitability and Drop Point Assessment",
    "Tethered Droid Lowering and Precision Delivery",
    "Failed Delivery, Retrieval and Customer Redress",
    "Restricted, Hazardous and Temperature-Sensitive Item Handling",
]),
("DD", "AD", "Airspace Deconfliction & Detect-and-Avoid", "deconfliction-daa", [
    "USS Onboarding and ASTM F3548 Strategic Coordination",
    "Pre-Flight Airspace Query and Constraint Ingestion",
    "In-Flight Detect-and-Avoid and Conflict Resolution",
    "Crewed Aircraft Encounter Reporting and Analysis",
    "Temporary Flight Restriction and Emergency Airspace Response",
]),

# ═══════════════ TIER 3 — CROSS-CUTTING ENTERPRISE (115) ═══════════════

("VA", "AQ", "Fleet Acquisition & Financing", "fleet-acquisition", [
    "Vehicle Specification and Supplier Selection",
    "Fleet Purchase, Lease and Asset-Backed Financing",
    "Vehicle Import, Homologation and Registration",
    "Fleet Sizing and Capital Allocation by Market",
]),
("VA", "MN", "Maintenance, Repair & Depot", "maintenance-repair", [
    "Preventive Maintenance Scheduling and Compliance",
    "Corrective Repair Intake, Triage and Turnaround",
    "Field Repair versus Warehouse Return Decisioning",
    "Spare Parts Inventory and Consumption Forecasting",
    "Depot Capacity Planning and Technician Productivity",
]),
("VA", "LC", "Asset Lifecycle, Depreciation & Disposal", "asset-lifecycle", [
    "Asset Register Maintenance and Serial Number Traceability",
    "Depreciation Policy and Useful Life Reassessment",
    "Impairment Testing and Write-Down Approval",
    "End-of-Life Disposal, Resale and Secondary Market",
]),
("VA", "WH", "Warranty, Parts & Supply Chain", "warranty-parts", [
    "Warranty Claim Submission and Supplier Recovery",
    "Supplier Quality Escalation and Corrective Action",
    "Component Recall Identification and Fleet Sweep",
    "Inbound Logistics and Customs for Vehicles and Parts",
]),

("RC", "TN", "TNC Licensing & State Regulation", "tnc-licensing", [
    "State TNC Permit Application and Annual Renewal",
    "Regulatory Trip Data Reporting and Audit Response",
    "Statutory Insurance Minimum Compliance by Period",
    "Airport Operating Agreement Negotiation and Fee Remittance",
    "Regulatory Change Monitoring and Impact Assessment",
]),
("RC", "MU", "Municipal Permits & Scooter Programs", "municipal-permits", [
    "Micromobility Permit Application and Competitive Bid Response",
    "Fleet Cap Compliance Monitoring and Reporting",
    "MDS and GBFS Feed Provisioning to City Agencies",
    "Permit Condition Breach Remediation and Penalty Response",
    "City Relationship Management and Programme Renewal",
]),
("RC", "DP", "Data Privacy & Mandated Data Sharing", "data-privacy", [
    "Location Data Minimisation and Retention Policy",
    "Data Subject Access, Deletion and Portability Requests",
    "Municipal Data Sharing Privacy Impact Assessment",
    "Law Enforcement Request Review and Disclosure",
    "Cross-Border Data Transfer Mechanism Management",
]),
("RC", "AV", "AV & Aviation Regulatory Affairs", "av-aviation-regulatory", [
    "Federal AV Rulemaking Engagement and Comment Filing",
    "FAA Rulemaking Participation Including Proposed Part 108",
    "Exemption and Special Authority Petition Management",
    "Regulator Briefing and Safety Data Disclosure",
    "International Regulatory Harmonisation Tracking",
]),
("RC", "LB", "Labour, Accessibility & Local Ordinance", "labour-local-ordinance", [
    "Minimum Earnings Ordinance Compliance by Jurisdiction",
    "Deactivation Protection Law Compliance",
    "Accessibility Mandate Compliance and Reporting",
    "Local Ordinance Litigation and Ballot Measure Response",
]),

("TD", "MP", "Mapping, Geospatial & Localisation", "mapping-geospatial", [
    "Base Map Ingestion, Conflation and Quality Control",
    "High-Definition Map Build and Change Detection",
    "Geofence and Zone Authoring Toolchain",
    "Address, Access Point and Pickup Location Curation",
    "Map Release Management and Fleet Distribution",
]),
("TD", "ML", "ML Platform & Model Operations", "ml-platform", [
    "Feature Store Design and Feature Freshness Management",
    "Model Training Pipeline and Experiment Tracking",
    "Online Prediction Serving and Latency Budget Management",
    "Model Monitoring, Drift Detection and Retraining Triggers",
    "Model Governance, Fairness Review and Approval",
]),
("TD", "PL", "Platform Engineering & Reliability", "platform-reliability", [
    "Service Level Objective Definition and Error Budget Policy",
    "Incident Detection, On-Call Response and Postmortem",
    "Capacity Planning and Peak Event Readiness",
    "Release Engineering, Canary and Progressive Rollout",
    "Security Vulnerability Management and Patch Cadence",
]),
("TD", "TL", "Telematics & Device Management", "telematics-devices", [
    "Device Fleet Inventory and Connectivity Monitoring",
    "Telemetry Schema Evolution and Backward Compatibility",
    "Edge Data Buffering and Intermittent Connectivity Handling",
    "Device Security, Attestation and Key Rotation",
    "Telemetry Cost Management and Sampling Strategy",
]),

("GM", "AQ", "Performance Marketing & Acquisition", "performance-marketing", [
    "Paid Channel Budget Allocation and Bid Management",
    "Attribution Modelling and Incrementality Measurement",
    "Creative Testing and Landing Experience Optimisation",
    "Supply-Side Recruitment Marketing for Drivers and Couriers",
]),
("GM", "BR", "Brand, Partnerships & Communications", "brand-partnerships", [
    "Brand Positioning and Campaign Development",
    "Strategic Partnership and Co-Marketing Execution",
    "Public Relations and Crisis Communications",
]),
("GM", "LC", "City Launch & Market Growth", "city-launch", [
    "New City Feasibility Assessment and Go or No-Go",
    "Launch Playbook Execution and Supply Seeding",
    "Post-Launch Growth Diagnostics and Corrective Action",
]),
("GM", "LY", "Loyalty & Retention", "loyalty-retention", [
    "Loyalty Programme Design and Points Economy Management",
    "Lifecycle Messaging and Reactivation Campaigns",
    "Churn Prediction and Retention Offer Targeting",
]),

("FN", "FP", "Planning & Unit Economics", "planning-unit-economics", [
    "Annual Operating Plan and Quarterly Reforecast",
    "Contribution Margin Modelling by Trip, Order and Vehicle",
    "Market-Level Profitability Review and Investment Gating",
    "Scenario Planning for Regulatory and Demand Shocks",
]),
("FN", "AC", "Accounting, Close & Controls", "accounting-close", [
    "Monthly Close Calendar and Task Orchestration",
    "Marketplace Revenue Recognition Under ASC 606",
    "Balance Sheet Reconciliation and Flux Analysis",
    "Internal Control Testing and Audit Support",
]),
("FN", "TR", "Treasury & Capital", "treasury-capital", [
    "Cash Positioning and Liquidity Forecasting",
    "Debt Facility Management and Covenant Monitoring",
    "Foreign Exchange Exposure and Hedging",
    "Equity and Convertible Financing Execution",
]),
("FN", "IR", "Investor Relations & Reporting", "investor-relations", [
    "Quarterly Earnings Preparation and Disclosure Review",
    "Analyst and Investor Engagement Programme",
    "Key Operating Metric Definition and Disclosure Governance",
]),

("HR", "TA", "Talent Acquisition", "talent-acquisition", [
    "Workforce Requisition Approval and Headcount Control",
    "Sourcing, Interviewing and Offer Management",
    "Onboarding and First Ninety Days Enablement",
]),
("HR", "OP", "People Operations & Compensation", "people-operations", [
    "Compensation Benchmarking and Annual Review Cycle",
    "Equity Grant Administration and Vesting Management",
    "Benefits Enrolment and Global Programme Administration",
]),
("HR", "FW", "Frontline & Warehouse Workforce", "frontline-workforce", [
    "Warehouse and Depot Shift Scheduling",
    "Frontline Safety Training and Certification",
    "Frontline Attrition Management and Labour Supply Planning",
]),
("HR", "CU", "Culture & Employee Relations", "culture-employee-relations", [
    "Employee Engagement Survey and Action Planning",
    "Workplace Investigation and Grievance Handling",
    "Performance Management and Calibration",
]),

("SE", "EV", "EV Transition & Charging Infrastructure", "ev-transition", [
    "Fleet Electrification Roadmap and Vehicle Transition",
    "Charging Infrastructure Siting and Partner Selection",
    "Driver EV Adoption Incentives and Rental Programmes",
    "Grid Interconnection and Demand Charge Management",
]),
("SE", "CB", "Carbon Accounting & Reporting", "carbon-accounting", [
    "Scope 1 and 2 Emissions Inventory Compilation",
    "Scope 3 Emissions from Contractor Vehicle Miles",
    "Per-Trip and Per-Delivery Emissions Calculation",
    "Sustainability Disclosure and Assurance",
]),
("SE", "CE", "Battery Circularity & End-of-Life", "battery-circularity", [
    "Battery Second-Life Assessment and Repurposing",
    "Battery Collection, Transport and Recycling Compliance",
    "Vehicle Component Refurbishment and Reuse",
]),
("SE", "UR", "Urban Impact & Mode Shift", "urban-impact", [
    "Mode Shift Measurement and Car Trip Displacement",
    "Equity Zone Service Provision and Affordability Programmes",
    "Curb Space and Public Realm Impact Assessment",
]),
]


def build_catalogue():
    out = []
    for l1, l2, l2_name, l2_slug, names in TAXONOMY:
        for i, name in enumerate(names, start=1):
            pid = f"MM-{l1}-{l2}-{i:02d}"
            out.append({
                "pid": pid, "slug": pid.lower(),
                "l1": l1, "l1_name": L1_META[l1][1], "l1_icon": L1_META[l1][0],
                "l1_slug": L1_META[l1][2], "tier": L1_META[l1][3],
                "l2": l2, "l2_name": l2_name, "l2_slug": l2_slug,
                "name": name,
                "path": f"{L1_META[l1][2]}/{l2_slug}/{pid.lower()}/index.html",
            })
    return out


PROCESSES = build_catalogue()
BY_PID = {p["pid"]: p for p in PROCESSES}

EXPECTED_TOTAL = 357
assert len(PROCESSES) == EXPECTED_TOTAL, \
    f"catalogue is {len(PROCESSES)} processes, expected {EXPECTED_TOTAL}"
assert len({p["pid"] for p in PROCESSES}) == EXPECTED_TOTAL, "duplicate PIDs in catalogue"
assert len(L1_META) == 18, f"{len(L1_META)} L1 domains, expected 18"
assert len(TAXONOMY) == 74, f"{len(TAXONOMY)} L2 groups, expected 74"


if __name__ == "__main__":
    from collections import Counter
    c = Counter(p["l1"] for p in PROCESSES)
    l2c = Counter(t[0] for t in TAXONOMY)
    print(f"{'L1':<4}{'tier':<6}{'domain':<42}{'L2':>4}{'procs':>7}")
    print("-" * 63)
    for tier in (1, 2, 3):
        for code, (icon, name, slug, t) in L1_META.items():
            if t != tier:
                continue
            print(f"{code:<4}{tier:<6}{name:<42}{l2c[code]:>4}{c[code]:>7}")
        sub = sum(c[k] for k, v in L1_META.items() if v[3] == tier)
        print(f"{'':4}{'':6}{TIER_LABEL[tier] + ' subtotal':<42}"
              f"{sum(l2c[k] for k, v in L1_META.items() if v[3] == tier):>4}{sub:>7}")
        print("-" * 63)
    print(f"{'':4}{'':6}{'TOTAL':<42}{len(TAXONOMY):>4}{len(PROCESSES):>7}")
