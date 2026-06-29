"""
Bulk Job Seeder — Skreenit
==========================
Generates 500+ realistic job postings across all industries, roles, and
companies. Run once against the production DB:

    python scripts/bulk_jobs_seed.py

It writes SQL to stdout (redirect to a file) OR inserts directly when
--execute flag is passed.

Usage:
    python scripts/bulk_jobs_seed.py > migrations/024_bulk_jobs_seed.sql
    python scripts/bulk_jobs_seed.py --execute
"""

import uuid, json, sys, random
from datetime import datetime, timedelta

# ============================================================
# LOOKUP TABLE IDs (must match DB lookup tables exactly)
# ============================================================

INDUSTRY_IDS = {
    "Information Technology & Enabled Services": "ind-001",
    "Software Development":   "ind-002",
    "E-commerce":             "ind-003",
    "Finance & Banking":      "ind-004",
    "Healthcare":             "ind-005",
    "Education":              "ind-006",
    "Manufacturing":          "ind-007",
    "Retail":                 "ind-008",
    "Hospitality":            "ind-009",
    "Transportation":         "ind-010",
    "Real Estate":            "ind-011",
    "Media & Entertainment":  "ind-012",
    "Telecommunications":     "ind-013",
    "Energy & Utilities":     "ind-014",
    "Agriculture":            "ind-015",
    "Construction":           "ind-016",
    "Consulting":             "ind-017",
    "Legal Services":         "ind-018",
    "Marketing & Advertising":"ind-019",
    "Non-Profit":             "ind-020",
    "Government":             "ind-021",
    "Other":                  "ind-022",
}

DEPT_IDS = {
    "HR & Payroll":         "59684e0c-31d0-11f1-9793-f08cebf81990",
    "Insurance Services":   "59684f5f-31d0-11f1-9793-f08cebf81990",
    "Consulting & Advisory":"59684fd3-31d0-11f1-9793-f08cebf81990",
    "Tech & AI":            "59685011-31d0-11f1-9793-f08cebf81990",
    "Creative & Branding":  "5968504e-31d0-11f1-9793-f08cebf81990",
    "Operations":           "5968509f-31d0-11f1-9793-f08cebf81990",
    "Admin & Compliance":   "5968511b-31d0-11f1-9793-f08cebf81990",
    "Finance":              "59685173-31d0-11f1-9793-f08cebf81990",
    "Sales & Partnerships": "596851f6-31d0-11f1-9793-f08cebf81990",
}

ROLE_IDS = {
    "Executive":          "596915f7-31d0-11f1-9793-f08cebf81990",
    "Senior Executive":   "59691787-31d0-11f1-9793-f08cebf81990",
    "Lead":               "59691834-31d0-11f1-9793-f08cebf81990",
    "Assistant Manager":  "596918b5-31d0-11f1-9793-f08cebf81990",
    "Manager":            "5969192b-31d0-11f1-9793-f08cebf81990",
    "Senior Manager":     "596919af-31d0-11f1-9793-f08cebf81990",
    "Head of Department": "59691a41-31d0-11f1-9793-f08cebf81990",
    "Director":           "59691ac9-31d0-11f1-9793-f08cebf81990",
}

JOB_TYPE_IDS = {
    "onsite": "jobtype-001",
    "remote": "jobtype-002",
    "hybrid": "jobtype-003",
}

EMP_TYPE_IDS = {
    "Full-Time":  "emptype-001",
    "Part-Time":  "emptype-002",
    "Contract":   "emptype-003",
    "Internship": "emptype-004",
    "Freelance":  "emptype-005",
    "Consultant": "emptype-005",
}

EDU_IDS = {
    "High School":          "edu-001",
    "Diploma":              "edu-002",
    "Associate Degree":     "edu-003",
    "Bachelor's Degree":    "edu-004",
    "Master's Degree":      "edu-005",
    "Professional Degree":  "edu-005",
    "Certification":        "edu-002",
}

# ============================================================
# REAL COMPANY + RECRUITER UUIDs (from companies table)
# ============================================================
COMPANIES = [
    {"id": "16ef8a0d-165a-4099-991b-dd36dc47a499", "recruiter": "d06315da-326f-44b1-9049-bc3a704d8c5f",  "name": "Freelancer",                 "city": "Hyderabad",  "state": "Telangana"},
    {"id": "3dd70181-2905-4f41-b074-084c05386b4a", "recruiter": "fd46f8e0-cb83-43d2-a840-d5e26cc72ff9",  "name": "BMG Enterprises",             "city": "Hyderabad",  "state": "Telangana"},
    {"id": "58dd826a-3d5d-4158-aa38-fbd8a60fb43f", "recruiter": "f93e3c1a-dc50-4975-90e8-a826757f9c94",  "name": "BMG One",                     "city": "Mumbai",     "state": "Maharashtra"},
    {"id": "65af104c-8446-4dda-8407-08573b115a08", "recruiter": "e9dcdaad-415b-4a45-b07a-7265394018d2",  "name": "Patwarisaab Proptech",         "city": "Hyderabad",  "state": "Telangana"},
    {"id": "a83fd05a-abc7-4859-af2f-33ea80590180", "recruiter": "59f38e0b-9eb0-4f7c-b6cc-1b09ad2e3161",  "name": "NSP Softech",                  "city": "Bengaluru",  "state": "Karnataka"},
    {"id": "c49c5aed-9b26-4410-accc-3f8701d41402", "recruiter": "demo0001-0000-0000-0000-000000000001",  "name": "NSP Softtech Pvt Ltd",         "city": "Pune",       "state": "Maharashtra"},
    {"id": "d44cb792-7538-4ea0-8f80-39deb09dec7a", "recruiter": "5c6479bc-157e-4de3-af63-37347cd521d8",  "name": "Freelancer (PSK Services)",    "city": "Chennai",    "state": "Tamil Nadu"},
    {"id": "demo0001-0000-0000-0000-000000000002", "recruiter": "demo0001-0000-0000-0000-000000000001",  "name": "Skreenit Demo Company",        "city": "Hyderabad",  "state": "Telangana"},
]

ROLES = [
    "Executive", "Senior Executive", "Lead",
    "Assistant Manager", "Manager", "Senior Manager",
    "Head of Department", "Director",
]

DEPARTMENTS = [
    "HR & Payroll", "Insurance Services", "Consulting & Advisory",
    "Tech & AI", "Creative & Branding", "Operations",
    "Admin & Compliance", "Finance", "Sales & Partnerships",
]

EMPLOYMENT_TYPES = ["Full-Time", "Full-Time", "Full-Time", "Part-Time", "Contract", "Consultant"]
JOB_TYPES        = ["onsite", "onsite", "remote", "hybrid", "hybrid"]
NOTICE_PERIODS   = [0, 15, 30, 30, 60, 90]
EDUCATION        = ["Bachelor's Degree", "Bachelor's Degree", "Master's Degree",
                    "Diploma", "Professional Degree", "Certification"]

CITIES = [
    ("Hyderabad",  "Telangana",    "India"),
    ("Bengaluru",  "Karnataka",    "India"),
    ("Mumbai",     "Maharashtra",  "India"),
    ("Pune",       "Maharashtra",  "India"),
    ("Chennai",    "Tamil Nadu",   "India"),
    ("Delhi",      "Delhi",        "India"),
    ("Gurugram",   "Haryana",      "India"),
    ("Noida",      "Uttar Pradesh","India"),
    ("Kolkata",    "West Bengal",  "India"),
    ("Ahmedabad",  "Gujarat",      "India"),
    ("Kochi",      "Kerala",       "India"),
    ("Jaipur",     "Rajasthan",    "India"),
    ("Chandigarh", "Punjab",       "India"),
    ("Bhubaneswar","Odisha",       "India"),
    ("Visakhapatnam","Andhra Pradesh","India"),
]

# ============================================================
# INDUSTRY DATA — title templates, skills, dept affinity
# ============================================================
INDUSTRY_DATA = {
    "Information Technology & Enabled Services": {
        "functions": [
            ("Software Engineer",         "Tech & AI",           ["Java","Spring Boot","Microservices","REST APIs","SQL"],    (500000, 2500000), (1, 12)),
            ("Data Analyst",              "Tech & AI",           ["Python","SQL","Power BI","Excel","Tableau"],               (400000, 1800000), (1, 8)),
            ("QA Engineer",               "Tech & AI",           ["Selenium","JMeter","TestNG","JIRA","Manual Testing"],      (350000, 1500000), (1, 8)),
            ("DevOps Engineer",           "Tech & AI",           ["AWS","Docker","Kubernetes","Jenkins","Terraform"],         (600000, 2800000), (2, 10)),
            ("Product Manager",           "Operations",          ["Product Roadmap","Agile","Stakeholder Management","Jira"], (1000000, 3000000),(4, 15)),
            ("UI/UX Designer",            "Creative & Branding", ["Figma","Adobe XD","User Research","Prototyping"],         (400000, 1800000), (1, 8)),
            ("Network Administrator",     "Tech & AI",           ["Cisco","CCNA","Firewalls","VPN","LAN/WAN"],               (350000, 1200000), (1, 6)),
            ("Cloud Architect",           "Tech & AI",           ["AWS","Azure","GCP","Terraform","Security"],               (1500000, 4000000),(6, 18)),
            ("IT Support Specialist",     "Operations",          ["Windows","Linux","ITIL","Helpdesk","Troubleshooting"],     (250000, 800000),  (0, 5)),
            ("Business Analyst",          "Consulting & Advisory",["Requirements Analysis","BPMN","SQL","Agile","Visio"],    (500000, 2000000), (2, 10)),
        ],
        "contact": ("Kavya Reddy", "careers@itservices.in"),
    },
    "Software Development": {
        "functions": [
            ("Full Stack Developer",      "Tech & AI",           ["React","Node.js","MongoDB","REST APIs","TypeScript"],     (600000, 2800000), (2, 10)),
            ("Backend Developer",         "Tech & AI",           ["Python","Django","FastAPI","PostgreSQL","Redis"],         (500000, 2500000), (1, 10)),
            ("Frontend Developer",        "Tech & AI",           ["React","Vue.js","CSS","JavaScript","Figma"],             (400000, 2000000), (1, 8)),
            ("Mobile App Developer",      "Tech & AI",           ["Flutter","React Native","iOS","Android","Swift"],        (500000, 2500000), (2, 10)),
            ("ML Engineer",               "Tech & AI",           ["Python","TensorFlow","PyTorch","Scikit-learn","MLOps"],  (800000, 3500000), (3, 12)),
            ("AI Research Engineer",      "Tech & AI",           ["LLMs","NLP","Computer Vision","Python","CUDA"],          (1000000, 4000000),(3, 15)),
            ("Data Engineer",             "Tech & AI",           ["Spark","Kafka","Airflow","dbt","Snowflake"],             (700000, 3000000), (2, 12)),
            ("Security Engineer",         "Tech & AI",           ["Penetration Testing","SIEM","ISO 27001","OWASP","CISSP"],(700000, 3000000), (3, 12)),
            ("Technical Lead",            "Tech & AI",           ["System Design","Microservices","Code Review","Agile"],   (1200000, 4000000),(6, 15)),
            ("Software Architect",        "Tech & AI",           ["System Architecture","AWS","TOGAF","API Design"],        (1800000, 5000000),(8, 20)),
        ],
        "contact": ("Priya Iyer", "hr@softdev.in"),
    },
    "E-commerce": {
        "functions": [
            ("Catalog Manager",           "Operations",          ["Product Cataloguing","Excel","SAP","ERP","Data Entry"],  (300000, 900000),  (1, 5)),
            ("Digital Marketing Manager", "Sales & Partnerships",["SEO","Google Ads","Meta Ads","CRM","Analytics"],        (500000, 2000000), (2, 10)),
            ("Logistics Coordinator",     "Operations",          ["Supply Chain","Warehouse","3PL","Inventory","SAP"],      (300000, 900000),  (1, 6)),
            ("Customer Success Manager",  "Sales & Partnerships",["CRM","Zendesk","Communication","Upselling","NPS"],      (400000, 1500000), (2, 8)),
            ("Growth Hacker",             "Sales & Partnerships",["A/B Testing","Analytics","Email Marketing","SQL"],      (500000, 1800000), (2, 8)),
            ("Marketplace Analyst",       "Operations",          ["Amazon","Flipkart","Analytics","Excel","Market Research"],(350000, 1200000),(1, 6)),
            ("E-commerce Category Head",  "Operations",          ["Category P&L","Vendor Management","Pricing Strategy"],  (1000000, 3000000),(5, 15)),
            ("Returns & Refunds Manager", "Operations",          ["Customer Escalation","CRM","Process Improvement"],       (400000, 1200000), (2, 8)),
            ("Content & Listings Executive","Creative & Branding",["Content Writing","SEO","Photography","Copywriting"],  (250000, 700000),  (0, 4)),
            ("Payments & Fraud Analyst",  "Finance",             ["Payment Gateways","Fraud Detection","SQL","Risk"],      (500000, 1800000), (2, 8)),
        ],
        "contact": ("Meena Sharma", "talent@ecom.in"),
    },
    "Finance & Banking": {
        "functions": [
            ("Financial Analyst",         "Finance",             ["Financial Modelling","Excel","Bloomberg","CFA","Valuation"],(500000, 2000000),(2, 10)),
            ("Credit Analyst",            "Finance",             ["Credit Appraisal","Financial Statements","Risk","RBI"],  (400000, 1500000), (2, 8)),
            ("Risk Manager",              "Finance",             ["Basel III","VaR","Risk Framework","FRM","Stress Testing"],(700000, 2500000),(4, 12)),
            ("Investment Advisor",        "Finance",             ["Mutual Funds","Equity","Portfolio Management","SEBI"],   (400000, 1500000), (2, 8)),
            ("Compliance Officer",        "Admin & Compliance",  ["RBI","SEBI","AML","KYC","Internal Audit"],             (500000, 2000000), (3, 10)),
            ("Relationship Manager",      "Sales & Partnerships",["Client Acquisition","Cross-selling","CRM","Banking"],   (400000, 1500000), (2, 8)),
            ("Treasury Manager",          "Finance",             ["Forex","Liquidity","Money Markets","ALM"],              (800000, 2500000), (5, 15)),
            ("Accounts Manager",          "Finance",             ["Tally","GST","TDS","Financial Reporting","IND AS"],     (350000, 1200000), (2, 8)),
            ("Loan Processing Officer",   "Finance",             ["Mortgage","Credit Decisioning","Documentation","NACH"], (300000, 900000),  (1, 5)),
            ("NBFC Operations Head",      "Operations",          ["Operations Management","Team Leadership","Compliance"],  (1200000, 3500000),(7, 18)),
        ],
        "contact": ("Ramesh Nair", "recruitment@finance.co.in"),
    },
    "Healthcare": {
        "functions": [
            ("Hospital Administrator",    "Operations",          ["Hospital Management","NABH","Patient Care","HMS","P&L"], (500000, 2000000), (3, 12)),
            ("Clinical Research Associate","Tech & AI",          ["GCP","ICH Guidelines","Clinical Trials","Protocol"],    (400000, 1500000), (2, 8)),
            ("Medical Coder",             "Admin & Compliance",  ["ICD-10","CPT","HIPAA","Medical Billing","HIM"],         (300000, 900000),  (1, 5)),
            ("Health Data Analyst",       "Tech & AI",           ["SQL","Python","SPSS","HL7","FHIR","Clinical Data"],    (500000, 1800000), (2, 8)),
            ("Pharmacy Manager",          "Operations",          ["Inventory Management","Drug Dispensing","FDA","CDSCO"], (400000, 1200000), (3, 10)),
            ("Lab Quality Manager",       "Admin & Compliance",  ["NABL","ISO 15189","Quality Systems","Lab Operations"],  (500000, 1800000), (4, 12)),
            ("Healthcare IT Manager",     "Tech & AI",           ["EMR","EHR","HL7","Telemedicine","Epic","Cerner"],       (700000, 2500000), (4, 12)),
            ("Patient Care Coordinator",  "Operations",          ["Patient Scheduling","Insurance","EMR","Communication"], (250000, 700000),  (0, 4)),
            ("Biomedical Engineer",       "Tech & AI",           ["Medical Devices","Calibration","Equipment Maintenance"],(350000, 1200000), (1, 7)),
            ("Health Policy Analyst",     "Consulting & Advisory",["Policy Research","Public Health","NHP","WHO","MOHFW"],(500000, 1800000), (3, 10)),
        ],
        "contact": ("Dr. Ananya Das", "hr@healthcare.org.in"),
    },
    "Education": {
        "functions": [
            ("Academic Coordinator",      "HR & Payroll",        ["Curriculum Design","Student Management","LMS","CBSE"],   (300000, 900000),  (2, 8)),
            ("Curriculum Designer",       "Consulting & Advisory",["Instructional Design","ADDIE","eLearning","Bloom's"],   (400000, 1200000), (3, 10)),
            ("Ed-Tech Developer",         "Tech & AI",           ["React","LMS","SCORM","Moodle","Node.js","Video"],        (400000, 1800000), (2, 8)),
            ("Student Counselor",         "HR & Payroll",        ["Career Counselling","Psychometric Testing","Counselling"],(250000, 700000), (1, 6)),
            ("Training Manager",          "HR & Payroll",        ["L&D","Training Needs Analysis","Facilitation","LMS"],   (500000, 1800000), (4, 12)),
            ("Admission Manager",         "Sales & Partnerships",["Admissions","CRM","Target Achievement","Communication"], (300000, 1000000), (2, 8)),
            ("Placement Officer",         "Sales & Partnerships",["Campus Placements","Industry Connect","MoU","CRM"],     (300000, 900000),  (1, 6)),
            ("School Principal",          "Admin & Compliance",  ["School Administration","Accreditation","CBSE","Parent Engagement"],(600000,2000000),(8,20)),
            ("Online Faculty",            "Consulting & Advisory",["Subject Matter Expertise","Pedagogy","Video Teaching"], (300000, 1000000), (3, 12)),
            ("Research Scholar Coordinator","Tech & AI",         ["Research Methodology","Data Analysis","Grant Writing"],  (400000, 1200000), (3, 10)),
        ],
        "contact": ("Sunita Pillai", "careers@edtech.in"),
    },
    "Manufacturing": {
        "functions": [
            ("Production Manager",        "Operations",          ["Production Planning","Lean","Six Sigma","ISO 9001","OEE"],(600000, 2000000),(4, 15)),
            ("Quality Control Engineer",  "Admin & Compliance",  ["QC","SPC","GD&T","Micrometer","FMEA","PPAP"],          (400000, 1500000), (2, 8)),
            ("Supply Chain Manager",      "Operations",          ["SAP MM","Vendor Management","Incoterms","Procurement"],  (700000, 2500000), (4, 12)),
            ("Process Engineer",          "Tech & AI",           ["AutoCAD","SolidWorks","Kaizen","Process Optimization"],  (400000, 1500000), (2, 8)),
            ("Safety Officer",            "Admin & Compliance",  ["OHSAS 18001","ISO 45001","Accident Investigation","PPE"],(350000, 1200000),(2, 8)),
            ("Plant Maintenance Manager", "Operations",          ["TPM","CMMS","Preventive Maintenance","Hydraulics"],     (600000, 2000000), (5, 15)),
            ("Industrial Engineer",       "Tech & AI",           ["AutoCAD","PLC","Automation","Time Study","Ergonomics"], (400000, 1500000), (2, 8)),
            ("Warehouse Manager",         "Operations",          ["Inventory Management","WMS","FIFO","Logistics","3PL"],  (400000, 1300000), (3, 10)),
            ("EHS Manager",               "Admin & Compliance",  ["Environmental Compliance","EIA","CPCB","Green Audit"],  (600000, 2000000), (5, 12)),
            ("Costing & Estimating Engineer","Finance",          ["BOM Costing","SAP CO","Standard Costing","Variance"],   (400000, 1500000), (2, 8)),
        ],
        "contact": ("Sanjay Patel", "hr@manufacturing.co.in"),
    },
    "Retail": {
        "functions": [
            ("Store Manager",             "Operations",          ["P&L","Visual Merchandising","Team Management","KPIs"],   (400000, 1500000), (3, 10)),
            ("Visual Merchandiser",       "Creative & Branding", ["VM","Planogram","Retail Display","Brand Guidelines"],   (250000, 800000),  (1, 5)),
            ("Inventory Manager",         "Operations",          ["Stock Management","ERP","Demand Forecasting","FIFO"],    (300000, 1000000), (2, 8)),
            ("Customer Experience Manager","Sales & Partnerships",["NPS","CRM","Complaint Resolution","SLA","CSAT"],      (350000, 1200000), (2, 8)),
            ("Retail Sales Executive",    "Sales & Partnerships",["Target Achievement","Product Knowledge","Cross-sell"],  (200000, 600000),  (0, 3)),
            ("Category Manager",          "Operations",          ["Category P&L","Vendor Negotiation","Assortment","CRM"], (600000, 2000000), (4, 12)),
            ("Loss Prevention Manager",   "Admin & Compliance",  ["CCTV","Shrinkage","Security Protocol","Investigations"], (350000, 1200000), (3, 8)),
            ("Franchise Development Manager","Sales & Partnerships",["Franchise Model","Territory Expansion","ROI","Training"],(700000,2500000),(4,12)),
            ("E-commerce Retail Analyst", "Tech & AI",           ["Amazon","Flipkart","Analytics","SEO","PPC"],            (350000, 1200000), (2, 7)),
            ("Supply Chain Coordinator",  "Operations",          ["Vendor Management","Purchase Orders","MRP","Logistics"], (300000, 900000),  (1, 5)),
        ],
        "contact": ("Divya Menon", "talent@retail.in"),
    },
    "Hospitality": {
        "functions": [
            ("Hotel Manager",             "Operations",          ["Front Office","F&B","Housekeeping","RevPAR","PMS"],      (500000, 2000000), (5, 15)),
            ("Event Coordinator",         "Operations",          ["Event Planning","MICE","Vendor Management","Logistics"], (300000, 1000000), (2, 8)),
            ("F&B Manager",               "Operations",          ["Cost Control","Menu Engineering","HACCP","Staff Training"],(500000, 1800000),(4, 12)),
            ("Front Desk Manager",        "Operations",          ["Opera PMS","Guest Relations","Upselling","Complaints"],  (300000, 1000000), (2, 8)),
            ("Guest Relations Executive", "Sales & Partnerships",["Communication","Complaint Handling","VIP Protocol"],    (200000, 600000),  (0, 4)),
            ("Revenue Manager",           "Finance",             ["RevPAR","STR Reports","OTA Management","Forecasting"],  (500000, 1800000), (3, 10)),
            ("Housekeeping Manager",      "Operations",          ["Housekeeping SOPs","Quality Audit","Laundry","GXP"],    (300000, 1000000), (3, 10)),
            ("Sales Manager – MICE",      "Sales & Partnerships",["Corporate Sales","MICE","Banquets","Client Acquisition"],(400000, 1500000),(3, 10)),
            ("Spa & Wellness Manager",    "Operations",          ["Spa Operations","Therapists Training","Revenue","CRM"],  (350000, 1200000), (4, 10)),
            ("Kitchen Manager / Chef",    "Operations",          ["Menu Planning","Kitchen Operations","HACCP","Cost Control"],(400000,1500000),(3,12)),
        ],
        "contact": ("Arun Krishnan", "hr@hospitality.in"),
    },
    "Transportation": {
        "functions": [
            ("Logistics Manager",         "Operations",          ["4PL","Last Mile","Fleet Management","SAP TM","Cost"],    (500000, 2000000), (4, 12)),
            ("Fleet Manager",             "Operations",          ["Vehicle Maintenance","GPS","Fuel Management","FASTag"],  (400000, 1500000), (3, 10)),
            ("Operations Analyst",        "Operations",          ["KPI Reporting","SQL","Excel","Route Optimisation"],     (350000, 1200000), (2, 7)),
            ("Supply Chain Coordinator",  "Operations",          ["Purchase Orders","Vendor Relations","Inventory"],        (300000, 900000),  (1, 5)),
            ("Dispatch Executive",        "Operations",          ["Vehicle Dispatch","Communication","Route Planning","TMS"],(200000, 600000), (0, 3)),
            ("Freight Forwarding Manager","Operations",          ["EXIM","IGCR","Bill of Lading","Customs","Incoterms"],   (600000, 2000000), (5, 12)),
            ("Transport Safety Officer",  "Admin & Compliance",  ["Road Safety","MV Act","Driver Training","CMVR"],        (350000, 1200000), (3, 8)),
            ("Warehouse & Distribution Manager","Operations",    ["Distribution Network","WMS","Cold Chain","3PL"],        (600000, 2000000), (5, 12)),
            ("EV Fleet Analyst",          "Tech & AI",           ["EV Operations","Telematics","Data Analysis","Battery"],  (400000, 1500000), (2, 7)),
            ("Logistics Business Development","Sales & Partnerships",["Business Development","Client Acquisition","CRM"],  (500000, 1800000), (3, 10)),
        ],
        "contact": ("Suresh Gupta", "hr@transport.co.in"),
    },
    "Real Estate": {
        "functions": [
            ("Property Manager",          "Operations",          ["Property Management","Lease","Maintenance","Tenants"],   (400000, 1500000), (3, 10)),
            ("Real Estate Analyst",       "Finance",             ["DCF","Cap Rate","Market Research","Financial Modelling"],(500000, 1800000),(2, 8)),
            ("Sales Agent",               "Sales & Partnerships",["Site Visits","Client Acquisition","CRM","Negotiation"],  (200000, 800000),  (0, 5)),
            ("Valuation Expert",          "Consulting & Advisory",["RERA","Property Valuation","Market Comparison","Report"],(500000,1800000),(3, 10)),
            ("Land Acquisition Manager",  "Operations",          ["Land Records","Revenue","Due Diligence","Negotiation"],  (700000, 2500000), (5, 15)),
            ("Construction Project Manager","Operations",        ["MS Project","Primavera","Quality","Budgeting","RERA"],   (700000, 2500000), (5, 15)),
            ("Interior Designer",         "Creative & Branding", ["AutoCAD","3ds Max","SketchUp","Space Planning"],        (300000, 1200000), (2, 8)),
            ("RERA Compliance Officer",   "Admin & Compliance",  ["RERA","Legal Documentation","Agreement","Litigation"],   (400000, 1500000), (3, 8)),
            ("CRM Executive – Realty",    "Sales & Partnerships",["CRM","Post-Sales","Homebuyer Support","Communication"],  (250000, 700000),  (1, 5)),
            ("Facilities Manager",        "Operations",          ["FM","AMC","Housekeeping","Maintenance","SLA"],           (500000, 1800000), (4, 12)),
        ],
        "contact": ("Neha Joshi", "hr@realty.in"),
    },
    "Media & Entertainment": {
        "functions": [
            ("Content Manager",           "Creative & Branding", ["Content Strategy","SEO","Editorial","CMS","Analytics"],  (400000, 1500000), (2, 8)),
            ("Video Producer",            "Creative & Branding", ["DaVinci Resolve","Premiere Pro","Storytelling","OTT"],   (400000, 1500000), (2, 8)),
            ("Social Media Manager",      "Sales & Partnerships",["Meta","Instagram","LinkedIn","Analytics","Reels"],       (300000, 1200000), (2, 7)),
            ("Creative Director",         "Creative & Branding", ["Brand Direction","Ideation","Team Leadership","AV"],     (1200000, 4000000),(7, 18)),
            ("PR Manager",                "Sales & Partnerships",["Media Relations","Press Releases","Crisis Comms","Events"],(500000,1800000),(3, 10)),
            ("Scriptwriter / Copywriter", "Creative & Branding", ["Screenplay","Brand Voice","Persuasive Copy","UX Writing"],(300000,1200000),(2, 8)),
            ("OTT Product Manager",       "Tech & AI",           ["OTT Platform","Product Management","Analytics","SVOD"],   (1000000,3500000),(4, 12)),
            ("Music Licensing Manager",   "Admin & Compliance",  ["IP","Music Rights","Royalties","IPRS","PPL"],            (400000, 1500000), (3, 10)),
            ("Ad Sales Manager",          "Sales & Partnerships",["Advertising","Revenue","Brand Partnerships","Digital"],  (500000, 2000000), (3, 10)),
            ("Animation Artist",          "Creative & Branding", ["Maya","After Effects","Blender","2D Animation","VFX"],   (300000, 1200000), (2, 8)),
        ],
        "contact": ("Riya Kapoor", "talent@media.in"),
    },
    "Telecommunications": {
        "functions": [
            ("Network Engineer",          "Tech & AI",           ["5G","MPLS","BGP","OSPF","Cisco","Nokia"],               (500000, 2000000), (2, 10)),
            ("RF Engineer",               "Tech & AI",           ["RF Planning","Drive Test","TEMS","2G/3G/4G/5G"],        (400000, 1500000), (2, 8)),
            ("Telecom Analyst",           "Tech & AI",           ["Network KPIs","SQL","OSS/BSS","Reporting","VoLTE"],     (400000, 1500000), (2, 8)),
            ("Project Manager – Telecom", "Operations",          ["Telecom Projects","PMP","Rollout","Tower Infra","PERT"], (700000, 2500000), (5, 12)),
            ("Customer Operations Manager","Operations",         ["SLA","Churn Reduction","Escalation","CSAT","CRM"],      (500000, 1800000), (3, 10)),
            ("VAS Product Manager",       "Tech & AI",           ["VAS","Revenue","Product Lifecycle","USSD","SMSC"],      (700000, 2500000), (4, 12)),
            ("Billing & Revenue Assurance","Finance",            ["CDR","Revenue Leakage","BSS","Billing Reconciliation"], (500000, 1800000), (3, 10)),
            ("Fiber Rollout Coordinator", "Operations",          ["FTTH","Civil","RoW","Fiber Planning","ISP"],             (300000, 1000000), (1, 6)),
            ("Cybersecurity Engineer",    "Tech & AI",           ["SIEM","Firewall","Zero Trust","VAPT","ISO 27001"],      (700000, 2500000), (3, 12)),
            ("Regulatory Affairs Manager","Admin & Compliance",  ["TRAI","DOT Compliance","License","Regulatory Filing"],  (500000, 2000000), (4, 12)),
        ],
        "contact": ("Aditya Singh", "hr@telecom.co.in"),
    },
    "Energy & Utilities": {
        "functions": [
            ("Energy Analyst",            "Finance",             ["Energy Markets","Load Forecasting","Python","Power BI"],  (500000, 1800000), (2, 8)),
            ("Solar Project Manager",     "Operations",          ["Solar EPC","PVsyst","ROI","Grid Connection","BOS"],      (700000, 2500000), (4, 12)),
            ("HSE Officer",               "Admin & Compliance",  ["ISO 45001","OHSAS","Permit to Work","Risk Assessment"],  (350000, 1200000), (2, 8)),
            ("Electrical Engineer",       "Tech & AI",           ["HV Systems","SCADA","Protection Relays","Power Systems"],(500000, 1800000), (2, 10)),
            ("Grid Operations Manager",   "Operations",          ["Load Dispatch","EMS","SLDC","Grid Stability"],           (700000, 2500000), (5, 15)),
            ("Wind Energy Engineer",      "Tech & AI",           ["Wind Turbines","SCADA","P50/P90","CFD","WTG"],           (500000, 1800000), (3, 10)),
            ("Power Purchase Analyst",    "Finance",             ["PPA","Tariff Analysis","DISCOM","Contract Management"],  (500000, 1800000), (2, 8)),
            ("O&M Manager – Renewables",  "Operations",          ["O&M","Predictive Maintenance","KPIs","Asset Management"],(700000,2500000),(5, 12)),
            ("Environment Compliance Officer","Admin & Compliance",["EIA","CPCB Compliance","MOEF","Green Audit"],         (400000, 1500000), (3, 8)),
            ("Battery Storage Engineer",  "Tech & AI",           ["BESS","BMS","Li-ion","SCADA","Energy Storage"],         (600000, 2500000), (3, 10)),
        ],
        "contact": ("Vikram Sharma", "careers@energy.in"),
    },
    "Agriculture": {
        "functions": [
            ("Agri Business Manager",     "Sales & Partnerships",["Agri Value Chain","FPO","CRM","Market Linkage","Kharif"],(500000, 1800000),(3, 10)),
            ("Farm Operations Manager",   "Operations",          ["Farm Management","Irrigation","Crop Protection","GPS"],   (350000, 1200000), (3, 10)),
            ("Agricultural Analyst",      "Finance",             ["Commodity Markets","NCDEX","Price Forecasting","Excel"],  (400000, 1500000), (2, 8)),
            ("Agri Supply Chain Manager", "Operations",          ["Cold Chain","FPO","Procurement","Logistics","APMC"],     (500000, 1800000), (4, 12)),
            ("Quality Inspector – Agri",  "Admin & Compliance",  ["FSSAI","Pesticide Residue","APEDA","Export","QC"],      (300000, 1000000), (2, 7)),
            ("Precision Farming Specialist","Tech & AI",         ["Drone Technology","IoT","Remote Sensing","GIS","NDVI"],  (400000, 1500000), (2, 8)),
            ("Rural Development Officer", "Consulting & Advisory",["NABARD","SHG","MF","CSR","Community Mobilisation"],    (350000, 1200000), (2, 8)),
            ("Crop Research Scientist",   "Tech & AI",           ["Plant Breeding","Genomics","Tissue Culture","Research"],  (500000, 1800000), (4, 12)),
            ("Agricultural Finance Manager","Finance",           ["KCC","Farm Credit","NPA","DCCB","Agriculture Lending"],  (500000, 1800000), (4, 12)),
            ("Irrigation Engineer",       "Tech & AI",           ["Drip Irrigation","Water Management","AutoCAD","Civil"],   (350000, 1200000), (2, 8)),
        ],
        "contact": ("Ravi Kumar", "hr@agribusiness.in"),
    },
    "Construction": {
        "functions": [
            ("Site Engineer",             "Tech & AI",           ["AutoCAD","RCC","Site Management","BOQ","Quantity Survey"],(400000, 1500000),(2, 8)),
            ("Project Manager",           "Operations",          ["MS Project","Primavera","Budgeting","Risk","Quality"],   (700000, 2500000), (5, 15)),
            ("Quantity Surveyor",         "Finance",             ["BOQ","Rate Analysis","Tendering","Cost Reconciliation"],  (400000, 1500000), (2, 8)),
            ("Structural Engineer",       "Tech & AI",           ["ETABS","STAAD Pro","RCC Design","IS Codes","FEM"],      (500000, 1800000), (2, 10)),
            ("Safety Manager",            "Admin & Compliance",  ["IS 18001","OHSAS","Fall Protection","PTW","Incident"],   (400000, 1500000), (3, 10)),
            ("MEP Engineer",              "Tech & AI",           ["HVAC","Electrical","Plumbing","Commissioning","BIM"],    (400000, 1500000), (2, 8)),
            ("BIM Manager",               "Tech & AI",           ["Revit","Navisworks","Clash Detection","LOD","BIM 360"],  (600000, 2500000), (3, 10)),
            ("Contracts Manager",         "Admin & Compliance",  ["FIDIC","Contract Administration","Dispute Resolution"],  (700000, 2500000), (5, 15)),
            ("Liasoning Officer",         "Admin & Compliance",  ["Government Liaison","Building Permits","NOC","RERA"],    (350000, 1200000), (3, 10)),
            ("Interior Project Manager",  "Creative & Branding", ["Interior Design","AutoCAD","Client Management","Budget"],(400000, 1500000),(3, 10)),
        ],
        "contact": ("Hardik Shah", "hr@construction.co.in"),
    },
    "Consulting": {
        "functions": [
            ("Management Consultant",     "Consulting & Advisory",["Strategy","Problem Solving","PowerPoint","Data Analysis"],(700000,3000000),(3, 12)),
            ("Strategy Analyst",          "Consulting & Advisory",["Market Research","PESTLE","Porter's","Financial Modelling"],(500000,2000000),(2, 8)),
            ("Business Analyst",          "Consulting & Advisory",["BPMN","Requirements","Agile","SQL","Visio"],           (500000, 2000000), (2, 8)),
            ("Change Management Lead",    "HR & Payroll",        ["ADKAR","Change Readiness","Training","Stakeholder"],    (700000, 2500000), (5, 12)),
            ("IT Consultant",             "Tech & AI",           ["ERP","SAP","Oracle","Solution Architecture","Pre-sales"],(700000, 3000000),(4, 12)),
            ("HR Consultant",             "HR & Payroll",        ["HR Transformation","Org Design","PMS","C&B"],           (500000, 2000000), (3, 10)),
            ("Digital Transformation Lead","Tech & AI",          ["Cloud","AI","RPA","Digital Strategy","Change"],         (1000000, 4000000),(6, 15)),
            ("Operations Excellence Manager","Operations",        ["Lean","Six Sigma","BPR","KPIs","Continuous Improvement"],(700000,2500000),(5, 12)),
            ("Risk & Compliance Consultant","Admin & Compliance", ["GRC","SOX","Internal Audit","Risk Framework"],         (600000, 2500000), (4, 12)),
            ("Financial Due Diligence Analyst","Finance",        ["M&A","Due Diligence","Valuation","IND AS","IFRS"],     (600000, 2500000), (3, 10)),
        ],
        "contact": ("Pooja Verma", "talent@consulting.in"),
    },
    "Legal Services": {
        "functions": [
            ("Corporate Lawyer",          "Admin & Compliance",  ["Corporate Law","M&A","Due Diligence","Drafting","NCLT"], (700000, 3000000), (3, 12)),
            ("Legal Analyst",             "Admin & Compliance",  ["Legal Research","Contract Review","CLAT","Court Filing"],(400000, 1500000),(2, 7)),
            ("Compliance Manager",        "Admin & Compliance",  ["SEBI","RBI","RERA","SOX","Regulatory Reporting"],       (600000, 2000000), (4, 12)),
            ("Contract Manager",          "Admin & Compliance",  ["Contract Lifecycle","NDA","SLA","Risk","CLM Tools"],    (500000, 2000000), (3, 10)),
            ("IP Specialist",             "Admin & Compliance",  ["Patent Filing","Trademark","Copyright","IP Strategy"],   (500000, 2000000), (3, 10)),
            ("Litigation Manager",        "Admin & Compliance",  ["Civil Litigation","Arbitration","Court Appearances"],    (600000, 2500000), (4, 12)),
            ("Labour Law Advisor",        "HR & Payroll",        ["Labour Laws","ESIC","PF","Minimum Wages","Compliance"],  (400000, 1500000), (3, 10)),
            ("Data Privacy Officer",      "Admin & Compliance",  ["PDPB","GDPR","Data Governance","Privacy Impact"],       (700000, 2500000), (4, 12)),
            ("Legal Tech Manager",        "Tech & AI",           ["Contract AI","CLM","e-Discovery","LegalOps","Automation"],(700000,2500000),(4, 12)),
            ("Company Secretary",         "Admin & Compliance",  ["MCA","ROC","Board Meetings","SEBI Listing","CS Exams"],  (500000, 2000000), (2, 10)),
        ],
        "contact": ("Anjali Gupta", "hr@legalfirm.in"),
    },
    "Marketing & Advertising": {
        "functions": [
            ("Brand Manager",             "Creative & Branding", ["Brand Positioning","P&L","ATL/BTL","Consumer Insights"], (700000, 2500000), (4, 12)),
            ("Digital Marketing Lead",    "Sales & Partnerships",["SEO","SEM","Meta","Google Ads","Marketing Automation"], (500000, 2000000), (3, 10)),
            ("Campaign Manager",          "Sales & Partnerships",["Campaign Planning","ROI","Programmatic","A/B Testing"],  (400000, 1500000), (2, 8)),
            ("SEO Specialist",            "Tech & AI",           ["On-Page","Off-Page","Ahrefs","Semrush","Core Web Vitals"],(300000, 1200000),(1, 6)),
            ("Content Strategist",        "Creative & Branding", ["Content Calendar","Storytelling","SEO","Video","Blog"],  (350000, 1400000), (2, 8)),
            ("Performance Marketing Manager","Sales & Partnerships",["ROAS","Facebook Ads","Google Ads","Attribution","LTV"],(600000,2500000),(3,10)),
            ("Market Research Analyst",   "Consulting & Advisory",["Primary Research","NPS","Focus Groups","SPSS","Syndicated"],(400000,1500000),(2,8)),
            ("CRM & Loyalty Manager",     "Sales & Partnerships",["Salesforce","HubSpot","Lifecycle Marketing","Retention"],(500000,1800000),(3,10)),
            ("Influencer Marketing Manager","Creative & Branding",["Influencer Outreach","UGC","Instagram","Deliverables"],  (350000, 1300000), (2, 7)),
            ("Trade Marketing Manager",   "Sales & Partnerships",["POSM","Channel Strategy","In-store","Distributor"],     (500000, 2000000), (4, 12)),
        ],
        "contact": ("Shreya Malhotra", "talent@adagency.in"),
    },
    "Non-Profit": {
        "functions": [
            ("Program Manager",           "Operations",          ["Project Management","Theory of Change","M&E","Reporting"],(400000, 1500000),(3, 10)),
            ("Fundraising Manager",       "Sales & Partnerships",["Grant Writing","CSR","Donor Relations","Fundraising"],   (400000, 1500000), (3, 10)),
            ("Community Development Officer","Operations",       ["Community Mobilisation","SHG","NABARD","FPO","CSR"],     (250000, 800000),  (1, 6)),
            ("M&E Manager",               "Consulting & Advisory",["Logical Framework","KOBO","Power BI","Theory of Change"],(400000,1500000),(3,10)),
            ("Grant Writer",              "Admin & Compliance",  ["Proposal Writing","CSR Portals","Grant Research","Budget"],(300000,1000000),(2,7)),
            ("Social Worker",             "HR & Payroll",        ["Social Work","MSW","Counselling","Field Visits"],        (200000, 600000),  (1, 5)),
            ("HR & People Operations",    "HR & Payroll",        ["NGO HR","Volunteer Management","Capacity Building"],     (300000, 900000),  (2, 7)),
            ("Communications Manager",    "Creative & Branding", ["Donor Communication","Annual Report","Social Media","PR"],(400000,1500000),(3,10)),
            ("Partnerships Manager",      "Sales & Partnerships",["CSR Partnerships","MoU","Government Liaison","FCRA"],   (400000, 1500000), (3, 10)),
            ("Finance & Admin Manager",   "Finance",             ["Tally","Donor Reporting","FCRA","Budget Tracking"],     (350000, 1200000), (3, 8)),
        ],
        "contact": ("Tara Bhatt", "jobs@nonprofit.org.in"),
    },
    "Government": {
        "functions": [
            ("Policy Analyst",            "Consulting & Advisory",["Public Policy","Evidence-Based Policy","RFP","GoI"],   (500000, 1800000), (3, 10)),
            ("Public Administration Officer","Admin & Compliance",["e-Governance","RTI","File Management","Government"],  (300000, 1000000), (2, 8)),
            ("Urban Planning Specialist", "Consulting & Advisory",["Smart Cities","GIS","Zonal Regulations","UDPFI"],     (500000, 1800000), (3, 10)),
            ("IT Systems Manager",        "Tech & AI",           ["NIC","e-Governance","NICSI","Government IT","OpenData"],(500000, 1800000), (3, 10)),
            ("Procurement Officer",       "Admin & Compliance",  ["GEM Portal","L1 Procurement","Tendering","CPPP"],       (350000, 1200000), (2, 8)),
            ("Statistical Officer",       "Tech & AI",           ["NSSO","MOSPI","Census","Statistical Analysis","SPSS"],  (400000, 1500000), (2, 8)),
            ("RTI Officer",               "Admin & Compliance",  ["RTI Act","Appellate","Record Management"],              (300000, 1000000), (2, 7)),
            ("Social Welfare Officer",    "HR & Payroll",        ["Welfare Schemes","DBT","Beneficiary","Field Visits"],   (300000, 900000),  (1, 5)),
            ("Project Implementation Officer","Operations",      ["PMGSY","RURBAN","Monitoring","Convergence","MIS"],      (400000, 1500000), (2, 8)),
            ("Environment Inspector",     "Admin & Compliance",  ["PCB","CPCB","EIA","NGT","Green Tribunal"],             (350000, 1200000), (2, 8)),
        ],
        "contact": ("Prem Chand", "hr@govtorg.gov.in"),
    },
    "Other": {
        "functions": [
            ("General Manager",           "Operations",          ["P&L Management","Cross-functional","Leadership","Strategy"],(1000000,3500000),(7,20)),
            ("Operations Head",           "Operations",          ["Operations","Scaling","Process Improvement","Team"],    (800000, 3000000), (6, 18)),
            ("Business Development Manager","Sales & Partnerships",["BD","Revenue Growth","Partnerships","Client Acquisition"],(500000,2000000),(3,10)),
            ("Project Manager",           "Operations",          ["PMP","MS Project","Agile","Risk","Stakeholder"],        (600000, 2500000), (4, 12)),
            ("Admin Manager",             "Admin & Compliance",  ["Office Administration","Vendor Management","Compliance"],(300000, 1000000),(2, 8)),
            ("People Operations Manager", "HR & Payroll",        ["HRBP","Talent Acquisition","L&D","Engagement"],        (600000, 2000000), (4, 12)),
            ("Finance Controller",        "Finance",             ["IND AS","MIS","Budgeting","Audit","Tax"],               (700000, 2500000), (5, 15)),
            ("Customer Success Lead",     "Sales & Partnerships",["Account Management","NPS","Upsell","CRM"],              (500000, 1800000), (3, 10)),
            ("Technical Trainer",         "HR & Payroll",        ["Training Design","Delivery","LMS","Assessment"],        (350000, 1200000), (3, 8)),
            ("Sustainability Manager",    "Admin & Compliance",  ["ESG","GRI","Carbon Footprint","ISO 14001","SDGs"],      (600000, 2500000), (4, 12)),
        ],
        "contact": ("Shiv Kumar", "hr@company.in"),
    },
}

# ============================================================
# DESCRIPTION + REQUIREMENTS TEMPLATES
# ============================================================
DESC_TEMPLATES = [
    (
        "We are looking for a dynamic and experienced {title} to join our growing team. "
        "In this role you will be responsible for driving {function} initiatives, "
        "working closely with cross-functional teams, and contributing to organisational goals. "
        "The ideal candidate brings a strong background in {industry}, excellent communication skills, "
        "and a passion for delivering results."
    ),
    (
        "Join our team as a {title} and take ownership of key {function} responsibilities. "
        "You will collaborate with senior leadership and stakeholders to execute strategies, "
        "drive performance, and bring best practices from the {industry} domain. "
        "We value proactive professionals who thrive in fast-paced environments."
    ),
    (
        "We have an exciting opportunity for a {title} to be part of our expanding operations. "
        "You will lead and execute {function} activities, mentor junior team members, "
        "and ensure high-quality output aligned with industry benchmarks in {industry}. "
        "Strong analytical and leadership capabilities are essential for this role."
    ),
]

RESP_TEMPLATES = [
    (
        "• Plan, execute and monitor {function} activities to achieve team targets\n"
        "• Collaborate with internal stakeholders to align on priorities and deliverables\n"
        "• Prepare reports, dashboards and insights for leadership review\n"
        "• Drive continuous improvement in processes and workflows\n"
        "• Mentor and support junior team members to build capability\n"
        "• Stay updated with {industry} trends and best practices"
    ),
    (
        "• Lead end-to-end {function} operations for the assigned portfolio\n"
        "• Build and maintain relationships with key stakeholders and vendors\n"
        "• Ensure compliance with internal policies and external regulations in {industry}\n"
        "• Develop and present insights and recommendations to senior management\n"
        "• Identify opportunities for process optimisation and cost efficiency\n"
        "• Own KPIs and drive accountability across the team"
    ),
]

REQ_TEMPLATES = [
    (
        "• {exp_min}–{exp_max} years of relevant experience in {industry}\n"
        "• {education} in a relevant field\n"
        "• Proficiency in: {skills}\n"
        "• Strong analytical, communication and interpersonal skills\n"
        "• Ability to work independently and collaborate in team settings\n"
        "• Prior experience in a {role} capacity is preferred"
    ),
    (
        "• Minimum {exp_min} years of experience in a {function} role within {industry}\n"
        "• {education} or equivalent qualification\n"
        "• Hands-on expertise in: {skills}\n"
        "• Excellent problem-solving and decision-making abilities\n"
        "• Strong verbal and written communication in English\n"
        "• Must be open to travel if required"
    ),
]


def esc(s):
    return str(s).replace("'", "''").replace("\\", "\\\\")


def gen_sql(jobs):
    lines = [
        "-- ============================================================",
        "-- Migration 024: Bulk Job Seed — 500+ live job postings",
        "-- Generated: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "-- ============================================================",
        "",
        "SET NAMES utf8mb4;",
        "SET FOREIGN_KEY_CHECKS = 0;",
        "",
    ]

    chunk_size = 50
    for i in range(0, len(jobs), chunk_size):
        chunk = jobs[i:i+chunk_size]
        lines.append("INSERT INTO `jobs` (")
        lines.append("  `id`, `job_title`, `description`, `responsibilities`, `requirements`,")
        lines.append("  `company_id`, `created_by`, `job_type`, `status`, `currency`,")
        lines.append("  `skills`, `department`, `role`, `employment_type`,")
        lines.append("  `salary_min`, `salary_max`, `no_of_openings`,")
        lines.append("  `location`, `location_city`, `location_state`, `location_country`,")
        lines.append("  `industry`, `education_qualification`, `experience_min`, `experience_max`,")
        lines.append("  `is_remote`, `notice_period_days`, `diversity_hiring`,")
        lines.append("  `contact_person_name`, `contact_person_email`,")
        lines.append("  `created_at`, `updated_at`")
        lines.append(") VALUES")
        vals = []
        for j in chunk:
            v = (
                f"  ('{j['id']}', '{esc(j['job_title'])}', '{esc(j['description'])}', "
                f"'{esc(j['responsibilities'])}', '{esc(j['requirements'])}',\n"
                f"   '{j['company_id']}', '{j['created_by']}', '{j['job_type']}', 'active', 'INR',\n"
                f"   '{esc(j['skills'])}', '{esc(j['department'])}', '{esc(j['role'])}', '{esc(j['employment_type'])}',\n"
                f"   {j['salary_min']}, {j['salary_max']}, {j['openings']},\n"
                f"   '{esc(j['location'])}', '{esc(j['city'])}', '{esc(j['state'])}', 'India',\n"
                f"   '{esc(j['industry'])}', '{esc(j['education'])}', {j['exp_min']}, {j['exp_max']},\n"
                f"   {j['is_remote']}, {j['notice']}, 0,\n"
                f"   '{esc(j['contact_name'])}', '{esc(j['contact_email'])}',\n"
                f"   '{j['created_at']}', '{j['created_at']}')"
            )
            vals.append(v)
        lines.append(",\n".join(vals) + ";")
        lines.append("")

    lines += [
        "SET FOREIGN_KEY_CHECKS = 1;",
        "",
        f"-- Total jobs inserted: {len(jobs)}",
    ]
    return "\n".join(lines)


def build_jobs():
    random.seed(42)
    jobs = []
    base_dt = datetime.now() - timedelta(days=30)

    company_cycle = 0

    for industry, idata in INDUSTRY_DATA.items():
        functions   = idata["functions"]
        cname, cemail = idata["contact"]

        for role in ROLES:
            for func_tuple in functions:
                func, dept, skills, salary_range, exp_range = func_tuple
                salary_min, salary_max = salary_range
                exp_min, exp_max = exp_range

                # Pick company (cycle through all 8)
                company = COMPANIES[company_cycle % len(COMPANIES)]
                company_cycle += 1

                # Pick city (mix company city with random Indian city)
                if company_cycle % 3 == 0:
                    city_row = random.choice(CITIES)
                    city, state, _ = city_row
                else:
                    city  = company["city"]
                    state = company["state"]

                job_type     = random.choice(JOB_TYPES)
                is_remote    = 1 if job_type == "remote" else 0
                emp_type     = random.choice(EMPLOYMENT_TYPES)
                notice       = random.choice(NOTICE_PERIODS)
                education    = random.choice(EDUCATION)
                openings     = random.choice([1, 1, 1, 2, 2, 3, 5])

                # Adjust salary by role seniority
                role_multiplier = {
                    "Executive": 1.0, "Senior Executive": 1.2, "Lead": 1.4,
                    "Assistant Manager": 1.5, "Manager": 1.8, "Senior Manager": 2.2,
                    "Head of Department": 2.8, "Director": 3.5,
                }
                mult = role_multiplier.get(role, 1.0)
                s_min = int(salary_min * mult / 100000) * 100000
                s_max = int(salary_max * mult / 100000) * 100000
                if s_min >= s_max:
                    s_max = s_min + 500000

                exp_adj_min = exp_min + (ROLES.index(role) * 1)
                exp_adj_max = exp_max + (ROLES.index(role) * 1)

                title = f"{role}, {func}" if role not in ("Executive","Senior Executive") else f"{func} {role}"

                desc_t = random.choice(DESC_TEMPLATES)
                resp_t = random.choice(RESP_TEMPLATES)
                req_t  = random.choice(REQ_TEMPLATES)

                desc  = desc_t.format(title=title, function=func, industry=industry)
                resp  = resp_t.format(function=func, industry=industry)
                req   = req_t.format(
                    exp_min=exp_adj_min, exp_max=exp_adj_max,
                    industry=industry, education=education,
                    skills=", ".join(skills), role=role, function=func,
                )

                created_offset = timedelta(
                    days=random.randint(0, 25),
                    hours=random.randint(8, 18),
                    minutes=random.randint(0, 59)
                )
                created_at = (base_dt + created_offset).strftime("%Y-%m-%d %H:%M:%S")

                jobs.append({
                    "id":            str(uuid.uuid4()),
                    "job_title":     title,
                    "description":   desc,
                    "responsibilities": resp,
                    "requirements":  req,
                    "company_id":    company["id"],
                    "created_by":    company["recruiter"],
                    "job_type":      JOB_TYPE_IDS[job_type],
                    "department":    DEPT_IDS[dept],
                    "role":          ROLE_IDS[role],
                    "employment_type": EMP_TYPE_IDS.get(emp_type, "emptype-001"),
                    "salary_min":    s_min,
                    "salary_max":    s_max,
                    "openings":      openings,
                    "city":          city,
                    "state":         state,
                    "location":      f"{city}, {state}, India",
                    "industry":      INDUSTRY_IDS[industry],
                    "education":     EDU_IDS.get(education, "edu-004"),
                    "exp_min":       exp_adj_min,
                    "exp_max":       exp_adj_max,
                    "is_remote":     is_remote,
                    "notice":        notice,
                    "skills":        json.dumps(skills),
                    "contact_name":  cname,
                    "contact_email": cemail,
                    "created_at":    created_at,
                })

    random.shuffle(jobs)
    return jobs


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    jobs = build_jobs()
    print(f"-- Generated {len(jobs)} job records", file=sys.stderr)

    if "--execute" in sys.argv:
        import os
        import pymysql
        host = os.getenv("DB_HOST", "localhost")
        port = int(os.getenv("DB_PORT", 3306))
        user = os.getenv("DB_USER", "root")
        pw   = os.getenv("DB_PASSWORD", "")
        db   = os.getenv("DB_NAME", "skreenit")

        conn = pymysql.connect(host=host, port=port, user=user, password=pw, database=db, charset="utf8mb4")
        cursor = conn.cursor()
        sql = gen_sql(jobs)
        for stmt in sql.split(";"):
            stmt = stmt.strip()
            if stmt and not stmt.startswith("--"):
                try:
                    cursor.execute(stmt)
                except Exception as e:
                    print(f"ERROR: {e}\nStatement: {stmt[:200]}", file=sys.stderr)
        conn.commit()
        cursor.close()
        conn.close()
        print(f"Inserted {len(jobs)} jobs successfully.", file=sys.stderr)
    else:
        print(gen_sql(jobs))
