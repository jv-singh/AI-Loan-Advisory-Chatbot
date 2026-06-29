"""
data/synthetic/generate_data.py
─────────────────────────────────
Synthetic Data Generator for Loan Advisory Agent prototype.

Generates realistic loan applicant data covering:
  - Diverse applicant profiles (salaried, self-employed, business owners)
  - Credit bureau records across the full score spectrum
  - Loan applications in various states
  - A SQLite database ready for immediate use

Run:
  python data/synthetic/generate_data.py

Output:
  data/dev.db               → SQLite database with all tables seeded
  data/synthetic/applicants.json     → JSON export of applicant profiles
  data/synthetic/loan_policies.json  → Sample policy rules for RAG ingestion
"""

from __future__ import annotations

import json
import random
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from faker import Faker

fake = Faker("en_IN")  # Indian locale for realistic names, cities
random.seed(42)        # Reproducible synthetic data

# ── Output paths ──────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.parent  # → data/
DB_PATH = BASE_DIR / "dev.db"
SYNTHETIC_DIR = Path(__file__).parent
APPLICANTS_JSON = SYNTHETIC_DIR / "applicants.json"
POLICIES_JSON = SYNTHETIC_DIR / "loan_policies.json"


# ── Profile archetypes ────────────────────────────────────────────────────────
EMPLOYMENT_PROFILES = [
    {
        "type": "salaried",
        "income_range": (25_000, 200_000),
        "years_range": (1, 20),
        "employers": [
            "Infosys Ltd", "TCS", "Wipro", "HCL Technologies",
            "HDFC Bank", "ICICI Bank", "Axis Bank",
            "Reliance Industries", "Tata Motors", "L&T",
        ],
        "designations": [
            "Software Engineer", "Senior Analyst", "Project Manager",
            "Branch Manager", "Marketing Executive", "HR Manager",
        ],
        "weight": 0.55,
    },
    {
        "type": "self_employed_professional",
        "income_range": (40_000, 300_000),
        "years_range": (2, 25),
        "employers": [
            "Self-Employed", "Independent Consultant",
            "XYZ Medical Clinic", "ABC Legal Associates",
        ],
        "designations": ["Doctor", "Chartered Accountant", "Lawyer", "Architect", "Consultant"],
        "weight": 0.25,
    },
    {
        "type": "business",
        "income_range": (30_000, 500_000),
        "years_range": (3, 30),
        "employers": ["Proprietor", "Director", "Partner"],
        "designations": ["Business Owner", "Managing Director", "Partner"],
        "weight": 0.20,
    },
]

LOAN_TYPES = ["home", "personal", "car", "education", "business"]
LOAN_PURPOSES = {
    "home":      ["Purchase of residential property", "Home construction", "Home renovation"],
    "personal":  ["Medical emergency", "Wedding expenses", "Travel", "Debt consolidation"],
    "car":       ["Purchase of new car", "Purchase of used car", "Commercial vehicle"],
    "education": ["MBA studies abroad", "Engineering college fees", "Postgraduate studies"],
    "business":  ["Working capital", "Equipment purchase", "Business expansion"],
}
INDIAN_CITIES = [
    "Mumbai", "Delhi", "Bengaluru", "Hyderabad", "Chennai",
    "Pune", "Kolkata", "Ahmedabad", "Jaipur", "Lucknow",
]
INDIAN_STATES = {
    "Mumbai": "Maharashtra", "Pune": "Maharashtra",
    "Delhi": "Delhi", "Jaipur": "Rajasthan", "Lucknow": "Uttar Pradesh",
    "Bengaluru": "Karnataka", "Hyderabad": "Telangana", "Chennai": "Tamil Nadu",
    "Kolkata": "West Bengal", "Ahmedabad": "Gujarat",
}


def _pick_employment_profile() -> dict:
    weights = [p["weight"] for p in EMPLOYMENT_PROFILES]
    return random.choices(EMPLOYMENT_PROFILES, weights=weights)[0]


def _random_dob(min_age: int = 22, max_age: int = 58) -> str:
    delta_days = random.randint(min_age * 365, max_age * 365)
    dob = datetime.now() - timedelta(days=delta_days)
    return dob.strftime("%Y-%m-%d")


def _random_pan() -> str:
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    return (
        "".join(random.choices(letters, k=5))
        + "".join(random.choices("0123456789", k=4))
        + random.choice(letters)
    )


def _random_timestamp(days_ago_max: int = 365) -> str:
    offset = timedelta(days=random.randint(0, days_ago_max))
    ts = datetime.now(timezone.utc) - offset
    return ts.isoformat()


# ── Schema creation ────────────────────────────────────────────────────────────

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS applicants (
    id TEXT PRIMARY KEY,
    full_name TEXT NOT NULL,
    email TEXT UNIQUE,
    phone TEXT,
    date_of_birth TEXT,
    pan_number TEXT UNIQUE,
    aadhaar_last4 TEXT,
    employer_name TEXT,
    employment_type TEXT,
    designation TEXT,
    monthly_income REAL,
    years_employed REAL,
    residential_status TEXT,
    city TEXT,
    state TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS credit_bureau (
    id TEXT PRIMARY KEY,
    applicant_id TEXT REFERENCES applicants(id),
    credit_score INTEGER,
    total_existing_loans INTEGER,
    monthly_debt_payments REAL,
    credit_history_years REAL,
    defaults_count INTEGER,
    enquiries_last_6m INTEGER,
    score_last_updated TEXT
);

CREATE TABLE IF NOT EXISTS loan_applications (
    id TEXT PRIMARY KEY,
    applicant_id TEXT REFERENCES applicants(id),
    loan_type TEXT,
    requested_amount REAL,
    tenure_years INTEGER,
    purpose TEXT,
    applied_at TEXT,
    status TEXT
);
"""


def generate_applicants(n: int = 30) -> list[dict]:
    """Generate n synthetic applicant profiles."""
    applicants = []

    for _ in range(n):
        profile = _pick_employment_profile()
        income = round(random.uniform(*profile["income_range"]), -2)
        years = round(random.uniform(*profile["years_range"]), 1)
        city = random.choice(INDIAN_CITIES)

        applicant = {
            "id": str(uuid.uuid4()),
            "full_name": fake.name(),
            "email": fake.email(),
            "phone": f"+91{random.randint(7000000000, 9999999999)}",
            "date_of_birth": _random_dob(),
            "pan_number": _random_pan(),
            "aadhaar_last4": str(random.randint(1000, 9999)),
            "employer_name": random.choice(profile["employers"]),
            "employment_type": profile["type"],
            "designation": random.choice(profile["designations"]),
            "monthly_income": income,
            "years_employed": years,
            "residential_status": random.choice(["owned", "rented"]),
            "city": city,
            "state": INDIAN_STATES.get(city, "Maharashtra"),
            "created_at": _random_timestamp(),
        }
        applicants.append(applicant)

    return applicants


def generate_credit_bureau(applicants: list[dict]) -> list[dict]:
    """
    Generate credit bureau records. Score distribution is realistic:
    ~15% excellent, ~30% good, ~30% fair, ~15% poor, ~10% very poor.
    """
    score_distribution = [
        (780, 900, 0.15),  # Excellent
        (710, 779, 0.30),  # Good
        (650, 709, 0.30),  # Fair
        (600, 649, 0.15),  # Poor
        (350, 599, 0.10),  # Very Poor
    ]

    records = []
    for applicant in applicants:
        # Pick score range based on distribution
        ranges, _, weights = zip(*[(r, h, w) for r, h, w in score_distribution])
        chosen_range = random.choices(
            [(lo, hi) for lo, hi, _ in score_distribution],
            weights=[w for _, _, w in score_distribution],
        )[0]
        score = random.randint(*chosen_range)

        # Higher income = lower debt payments (generally)
        income = applicant["monthly_income"]
        debt_ratio = random.uniform(0.10, 0.65)
        monthly_debt = round(income * debt_ratio, -2)

        records.append({
            "id": str(uuid.uuid4()),
            "applicant_id": applicant["id"],
            "credit_score": score,
            "total_existing_loans": random.randint(0, 4),
            "monthly_debt_payments": monthly_debt,
            "credit_history_years": round(random.uniform(0.5, 20), 1),
            "defaults_count": 0 if score > 650 else random.randint(0, 3),
            "enquiries_last_6m": random.randint(0, 8),
            "score_last_updated": _random_timestamp(90),
        })

    return records


def generate_loan_applications(applicants: list[dict]) -> list[dict]:
    """Generate 1–3 loan applications per applicant."""
    applications = []
    statuses = ["pending", "approved", "rejected", "disbursed"]

    for applicant in applicants:
        num_apps = random.choices([1, 2, 3], weights=[0.6, 0.3, 0.1])[0]
        income = applicant["monthly_income"]

        for _ in range(num_apps):
            loan_type = random.choice(LOAN_TYPES)
            max_loan = income * random.randint(20, 60)
            amount = round(random.uniform(50_000, min(max_loan, 10_000_000)), -3)
            tenure = random.choice([1, 2, 3, 5, 7, 10, 15, 20])
            purpose = random.choice(LOAN_PURPOSES.get(loan_type, ["General purpose"]))

            applications.append({
                "id": str(uuid.uuid4()),
                "applicant_id": applicant["id"],
                "loan_type": loan_type,
                "requested_amount": amount,
                "tenure_years": tenure,
                "purpose": purpose,
                "applied_at": _random_timestamp(365),
                "status": random.choices(
                    statuses, weights=[0.30, 0.40, 0.20, 0.10]
                )[0],
            })

    return applications


def generate_loan_policies() -> dict:
    """
    Generate structured loan policy data for JSON export.
    This is also used to create the synthetic policy PDF content.
    """
    return {
        "version": "2024-Q4",
        "last_updated": "2024-11-01",
        "products": {
            "home_loan": {
                "min_amount": 500_000,
                "max_amount": 75_000_000,
                "min_tenure_years": 5,
                "max_tenure_years": 30,
                "base_rate_pct": 8.50,
                "processing_fee_pct": 0.50,
                "min_credit_score": 650,
                "max_ltv_pct": 80,
                "eligible_employment": ["salaried", "self_employed_professional", "business"],
                "required_documents": [
                    "Salary slips (last 3 months)",
                    "Bank statements (last 6 months)",
                    "ITR (last 2 years)",
                    "Property documents",
                    "KYC: Aadhaar + PAN",
                ],
            },
            "personal_loan": {
                "min_amount": 50_000,
                "max_amount": 4_000_000,
                "min_tenure_years": 1,
                "max_tenure_years": 5,
                "base_rate_pct": 10.75,
                "processing_fee_pct": 1.00,
                "min_credit_score": 700,
                "eligible_employment": ["salaried", "self_employed_professional"],
                "required_documents": [
                    "Salary slips (last 3 months)",
                    "Bank statements (last 3 months)",
                    "KYC: Aadhaar + PAN",
                ],
            },
            "car_loan": {
                "min_amount": 100_000,
                "max_amount": 10_000_000,
                "min_tenure_years": 1,
                "max_tenure_years": 7,
                "base_rate_pct": 9.00,
                "processing_fee_pct": 0.50,
                "min_credit_score": 680,
                "eligible_employment": ["salaried", "self_employed_professional", "business"],
                "required_documents": [
                    "Salary slips or ITR",
                    "Bank statements (last 3 months)",
                    "Vehicle quotation/invoice",
                    "KYC: Aadhaar + PAN",
                ],
            },
        },
        "general_eligibility": {
            "min_age": 21,
            "max_age_at_loan_maturity": 65,
            "min_monthly_income_salaried": 25_000,
            "min_monthly_income_self_employed": 40_000,
            "max_debt_to_income_ratio": 0.50,
            "max_loan_to_income_multiplier": 60,
        },
    }


# ── Database population ───────────────────────────────────────────────────────

def seed_database(db_path: Path, n_applicants: int = 30) -> dict:
    """Create and seed the SQLite database."""
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA_SQL)

    applicants = generate_applicants(n_applicants)
    credit_records = generate_credit_bureau(applicants)
    applications = generate_loan_applications(applicants)

    # Insert applicants
    conn.executemany(
        """INSERT OR REPLACE INTO applicants 
           (id, full_name, email, phone, date_of_birth, pan_number, aadhaar_last4,
            employer_name, employment_type, designation, monthly_income, years_employed,
            residential_status, city, state, created_at)
           VALUES (:id,:full_name,:email,:phone,:date_of_birth,:pan_number,:aadhaar_last4,
                   :employer_name,:employment_type,:designation,:monthly_income,
                   :years_employed,:residential_status,:city,:state,:created_at)""",
        applicants,
    )

    conn.executemany(
        """INSERT OR REPLACE INTO credit_bureau
           (id, applicant_id, credit_score, total_existing_loans, monthly_debt_payments,
            credit_history_years, defaults_count, enquiries_last_6m, score_last_updated)
           VALUES (:id,:applicant_id,:credit_score,:total_existing_loans,
                   :monthly_debt_payments,:credit_history_years,:defaults_count,
                   :enquiries_last_6m,:score_last_updated)""",
        credit_records,
    )

    conn.executemany(
        """INSERT OR REPLACE INTO loan_applications
           (id, applicant_id, loan_type, requested_amount, tenure_years, purpose, applied_at, status)
           VALUES (:id,:applicant_id,:loan_type,:requested_amount,:tenure_years,
                   :purpose,:applied_at,:status)""",
        applications,
    )

    conn.commit()
    conn.close()

    return {
        "applicants": len(applicants),
        "credit_records": len(credit_records),
        "applications": len(applications),
    }


# ── Policy document generator ─────────────────────────────────────────────────

def generate_policy_text_docs() -> None:
    """Write plain-text policy documents for RAG ingestion."""
    docs_dir = SYNTHETIC_DIR / "documents"
    docs_dir.mkdir(parents=True, exist_ok=True)

    policies = [
        ("home_loan_policy.txt", """
HOME LOAN POLICY GUIDELINES — v2024.Q4
=======================================

1. ELIGIBILITY CRITERIA
- Minimum age: 21 years; Maximum age at loan maturity: 65 years
- Minimum credit score: 650 (CIBIL)
- Minimum monthly income (salaried): ₹25,000
- Minimum monthly income (self-employed): ₹40,000
- Minimum employment tenure: 2 years (salaried); 3 years (self-employed)
- Maximum Debt-to-Income ratio: 50%

2. LOAN PARAMETERS
- Minimum loan amount: ₹5,00,000
- Maximum loan amount: ₹7,50,00,000
- Maximum LTV (Loan-to-Value): 80% of property value
- Tenure: 5 to 30 years
- Base interest rate: 8.50% p.a. (floating)

3. RATE TIERS
- Credit Score 750+: 8.50% p.a.
- Credit Score 700–749: 9.00% p.a.
- Credit Score 650–699: 9.75% p.a.
- Credit Score below 650: Not eligible

4. PROCESSING FEE
- 0.50% of loan amount (minimum ₹5,000, maximum ₹15,000)
- Non-refundable once loan is sanctioned

5. REQUIRED DOCUMENTS
- KYC: Aadhaar card, PAN card
- Income proof: Salary slips (last 3 months), Form 16
- Bank statements: Last 6 months
- Property documents: Sale deed, NOC from builder
- ITR: Last 2 years with computation

6. PRE-PAYMENT CHARGES
- Floating rate loans: Nil pre-payment charges
- Fixed rate loans: 2% on prepaid amount if within 3 years
"""),
        ("personal_loan_policy.txt", """
PERSONAL LOAN POLICY GUIDELINES — v2024.Q4
===========================================

1. ELIGIBILITY CRITERIA
- Minimum credit score: 700 (CIBIL)
- Eligible employment: Salaried employees and self-employed professionals
- Minimum income: ₹20,000/month (salaried); ₹30,000/month (self-employed)
- Minimum employment: 1 year at current employer
- Maximum age: 60 years at loan maturity

2. LOAN PARAMETERS
- Amount: ₹50,000 to ₹40,00,000
- Tenure: 12 to 60 months
- Base interest rate: 10.75% p.a.

3. RATE TIERS (PERSONAL LOAN)
- Excellent credit (750+): 10.75% p.a.
- Good credit (700–749): 11.50% p.a.
- Fair credit (650–699): 13.00% p.a.
- Below 650: Application rejected

4. PROCESSING FEE
- 1.00% of loan amount (minimum ₹2,500)

5. REQUIRED DOCUMENTS
- KYC: Aadhaar card, PAN card, passport-size photograph
- Salary slips: Last 3 months
- Bank statements: Last 3 months
- Employment letter or offer letter

6. REJECTION CRITERIA (AUTOMATIC)
- Active default on any existing loan
- More than 3 credit enquiries in past 6 months
- Debt-to-income ratio above 45%
- Income not verifiable through payroll or ITR
"""),
        ("emi_and_interest_guide.txt", """
EMI CALCULATION GUIDE
=====================

STANDARD EMI FORMULA:
EMI = P × r × (1 + r)^n / ((1 + r)^n − 1)

Where:
  P = Principal loan amount
  r = Monthly interest rate (Annual rate ÷ 12 ÷ 100)
  n = Loan tenure in months

EXAMPLE CALCULATIONS:

Home Loan — ₹30,00,000 at 8.5% for 20 years (240 months):
  Monthly rate r = 8.5 / 12 / 100 = 0.007083
  EMI = ₹26,035 per month
  Total interest paid = ₹32,48,456
  Total repayment = ₹62,48,456

Personal Loan — ₹5,00,000 at 11% for 3 years (36 months):
  Monthly rate r = 11 / 12 / 100 = 0.009167
  EMI = ₹16,370 per month
  Total interest paid = ₹89,317
  Total repayment = ₹5,89,317

REDUCING BALANCE METHOD:
Interest each month is calculated on the outstanding principal, not
the original loan amount. This means early payments have more interest
and late payments have more principal — the crossover is typically
at 40–60% of the loan tenure.

PRE-PAYMENT IMPACT:
A single pre-payment of ₹1,00,000 in year 3 of a 20-year home loan
can reduce the total tenure by approximately 2–3 years and save
₹3–5 lakh in interest (depending on the rate and timing).

PART-PAYMENT STRATEGY:
Optimal time to part-pay: within the first 5 years, when the interest
component of each EMI is highest.
"""),
        ("eligibility_quick_reference.txt", """
LOAN ELIGIBILITY QUICK REFERENCE CARD
======================================

MINIMUM CREDIT SCORES BY PRODUCT:
  Home Loan:         650+
  Personal Loan:     700+
  Car Loan:          680+
  Education Loan:    620+
  Business Loan:     680+

INCOME REQUIREMENTS:
  Salaried (Home):          ₹25,000/month minimum
  Salaried (Personal):      ₹20,000/month minimum
  Self-Employed (Home):     ₹40,000/month minimum
  Business (Business Loan): ₹30,000/month net profit

DEBT-TO-INCOME LIMITS:
  Home Loan:         50% max DTI
  Personal Loan:     45% max DTI
  Car Loan:          50% max DTI
  Education Loan:    55% max DTI (considering future income)

MAXIMUM LOAN AMOUNTS (INCOME MULTIPLES):
  Home Loan:    60–80x monthly income (based on property value)
  Personal Loan: 24–40x monthly income
  Car Loan:      36x monthly income
  Business Loan: 50–60x monthly income

AUTOMATIC REJECTION TRIGGERS:
  ✗ Active loan default in last 3 years
  ✗ Debt-to-income ratio > 60%
  ✗ Fraudulent or mismatched documentation
  ✗ High fraud detection score (≥60 points)
  ✗ Age > 65 at loan maturity
  ✗ Credit score below product minimum

SPECIAL CASES:
  • Women applicants: Additional 0.05% rate concession on home loans
  • Green home loans: 0.10% rate concession for IGBC-rated buildings
  • First-time buyers: No LTV restriction on property < ₹35,00,000
"""),
    ]

    for filename, content in policies:
        (docs_dir / filename).write_text(content.strip(), encoding="utf-8")
        print(f"  ✓ Generated: {filename}")


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from rich.console import Console
    from rich.table import Table

    console = Console()
    console.print("\n[bold cyan]Loan Advisory Agent — Synthetic Data Generator[/bold cyan]\n")

    # 1. Seed database
    console.print("[bold]Step 1:[/bold] Creating SQLite database...")
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    stats = seed_database(DB_PATH, n_applicants=30)

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Table", style="cyan")
    table.add_column("Records", justify="right")
    for name, count in stats.items():
        table.add_row(name.replace("_", " ").title(), str(count))

    console.print(table)
    console.print(f"[green]✓ Database created at:[/green] {DB_PATH}\n")

    # 2. Export JSON
    console.print("[bold]Step 2:[/bold] Exporting JSON files...")
    applicants = generate_applicants(30)
    APPLICANTS_JSON.write_text(json.dumps(applicants[:5], indent=2), encoding="utf-8")
    POLICIES_JSON.write_text(json.dumps(generate_loan_policies(), indent=2), encoding="utf-8")
    console.print(f"[green]✓ applicants.json and loan_policies.json created[/green]\n")

    # 3. Policy documents
    console.print("[bold]Step 3:[/bold] Generating policy text documents for RAG...")
    generate_policy_text_docs()
    console.print(f"[green]✓ Policy documents created in data/synthetic/documents/[/green]\n")

    console.print("[bold green]🎉 Synthetic data generation complete![/bold green]")
    console.print("\nNext step: Run the document ingestion pipeline:")
    console.print("[yellow]  python -m backend.rag.document_processor --docs-dir ./data/synthetic/documents[/yellow]\n")