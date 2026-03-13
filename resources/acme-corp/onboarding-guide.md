# Acme Corp Onboarding Guide

Last updated: January 28, 2025

## 1. Welcome and Day 1 Checklist

Welcome to Acme Corp! Your first day will be spent getting set up and meeting your team. Here's your Day 1 checklist:

- [ ] Pick up your laptop and equipment from IT (Building A, Room 102)
- [ ] Set up your Okta account for Single Sign-On (SSO) — see Security Policy for authentication requirements
- [ ] Activate your @acmecorp.com email
- [ ] Join mandatory Slack channels: #general, #engineering, #your-team, #it-helpdesk
- [ ] Complete I-9 and tax forms in the HR portal
- [ ] Schedule 1:1 with your manager (first week)
- [ ] Attend the New Hire Orientation session at 10 AM (Building A, Conference Room Atlas)
- [ ] Review the Employee Handbook for PTO, benefits, and company policies

**Equipment stipend**: New hires receive a one-time $500 home office stipend. Submit receipts via Expensify within 60 days of your start date. This covers monitors, keyboards, ergonomic accessories, and similar work-from-home equipment. See the Employee Handbook for general expense submission guidelines.

## 2. Team Structure

Acme Corp Engineering is organized into four teams:

### Platform Team (12 engineers)
- **Lead**: Sarah Chen (sarah.chen@acmecorp.com)
- **Focus**: Core API, authentication, billing, and third-party integrations
- **Tech stack**: Python, FastAPI, PostgreSQL, Redis

### Data Team (8 engineers)
- **Lead**: Marcus Rodriguez (marcus.rodriguez@acmecorp.com)
- **Focus**: Data pipeline, ETL, analytics engine, ML models
- **Tech stack**: Python, Apache Airflow, Snowflake, dbt

### Frontend Team (10 engineers)
- **Lead**: Priya Patel (priya.patel@acmecorp.com)
- **Focus**: Dashboard UI, customer-facing web application, design system
- **Tech stack**: React, TypeScript, Tailwind CSS, Storybook

### Infrastructure Team (6 engineers)
- **Lead**: James Kim (james.kim@acmecorp.com)
- **Focus**: Cloud infrastructure, CI/CD, monitoring, security
- **Tech stack**: AWS, Terraform, Kubernetes, Datadog

## 3. Key Contacts

| Role | Name | Email | Slack |
|------|------|-------|-------|
| VP Engineering | David Okafor | david.okafor@acmecorp.com | @david.okafor |
| Director of Engineering | Lisa Tran | lisa.tran@acmecorp.com | @lisa.tran |
| HR Business Partner | Rachel Adams | rachel.adams@acmecorp.com | @rachel.adams |
| IT Administrator | Tom Nguyen | tom.nguyen@acmecorp.com | @tom.nguyen |
| Security Lead | Alex Petrov | alex.petrov@acmecorp.com | @alex.petrov |

## 4. Development Environment Setup

Follow these steps to set up your local development environment:

### Step 1: Repository Access
Request access to the Acme Corp GitHub organization by filing a ticket in #it-helpdesk. Access is typically granted within 2 hours.

### Step 2: Install Required Tools
```bash
# macOS (using Homebrew)
brew install python@3.12 node@20 docker terraform awscli

# Clone the main repositories
git clone git@github.com:acme-corp/acme-api.git
git clone git@github.com:acme-corp/acme-dashboard.git
```

### Step 3: Configure Local Services
```bash
# Start local development stack
cd acme-api
cp .env.example .env  # Fill in local dev credentials
docker-compose up -d  # Starts PostgreSQL, Redis, LocalStack
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

### Step 4: Verify Setup
```bash
# Run the test suite
pytest tests/ -v
# Start the frontend
cd ../acme-dashboard
npm install && npm run dev
```

Your setup is complete when you can access the dashboard at `http://localhost:3000` and the API at `http://localhost:8000/docs`.

## 5. 30/60/90 Day Expectations

### First 30 Days — Learn
- Complete all onboarding tasks and training modules
- Shadow at least 2 on-call shifts (see Engineering Runbook for on-call procedures)
- Ship your first bug fix or small feature (paired with a buddy)
- Attend all team ceremonies: daily standup, sprint planning, retrospective
- Read through team documentation and architecture decision records

### 60 Days — Contribute
- Own and deliver a medium-sized feature independently
- Participate in code reviews (aim for 3+ reviews per week)
- Join the on-call rotation for your team
- Present a topic at the weekly engineering knowledge share

### 90 Days — Impact
- Lead a project from design through deployment
- Identify and propose one process improvement
- Mentor a newer team member or contribute to documentation
- Complete your first performance self-assessment

## 6. Training and Resources

**Required training (complete within 2 weeks):**
- Security Awareness Training (2 hours) — see Security Policy
- Data Privacy and GDPR Compliance (1 hour)
- Acme Analytics Product Overview (1.5 hours)
- Engineering Standards and Code Review (1 hour)

**Recommended resources:**
- Internal wiki: wiki.acmecorp.internal
- Architecture Decision Records: github.com/acme-corp/adr
- Engineering blog: engineering.acmecorp.com
- Slack channels: #tech-talks, #learning-resources, #book-club
