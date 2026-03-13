# Acme Corp Engineering Runbook

Last updated: February 3, 2025

## 1. Incident Severity Levels

All production incidents are classified using the following severity levels:

### P1 — Critical
- **Definition**: Complete service outage or data loss affecting all customers
- **Response time**: 15 minutes
- **Resolution target**: 4 hours
- **Escalation**: Automatically pages on-call engineer + Engineering VP + CTO
- **Communication**: Status page updated every 30 minutes, customer email within 1 hour

### P2 — Major
- **Definition**: Significant feature degradation affecting >25% of users
- **Response time**: 30 minutes
- **Resolution target**: 8 hours
- **Escalation**: Pages on-call engineer + team lead
- **Communication**: Status page updated every 60 minutes

### P3 — Minor
- **Definition**: Non-critical feature issue affecting <25% of users
- **Response time**: 4 hours
- **Resolution target**: 48 hours
- **Escalation**: Assigned to on-call engineer via Jira
- **Communication**: Internal Slack notification only

### P4 — Low
- **Definition**: Cosmetic issues, minor UX bugs, non-urgent improvements
- **Response time**: Next business day
- **Resolution target**: Next sprint
- **Escalation**: Added to team backlog

## 2. On-Call Rotation

On-call rotations are managed through PagerDuty and follow a weekly rotation schedule. Each engineering team (Platform, Data, Frontend, Infrastructure) maintains its own rotation.

**On-call responsibilities:**
- Monitor PagerDuty alerts and respond within SLA
- Triage incoming incidents and assign severity levels
- Coordinate with other teams for cross-service incidents
- Hand off unresolved issues with detailed notes at rotation end
- Write post-mortem drafts for P1 and P2 incidents

**Compensation**: On-call engineers receive $500/week stipend plus $200 per P1/P2 incident responded to outside business hours.

**Scheduling**: Rotations are published 4 weeks in advance. Swaps must be arranged directly between engineers and updated in PagerDuty at least 48 hours before the shift begins.

## 3. Deployment Process

Acme Corp uses a progressive deployment pipeline for all production releases:

### Step 1: Staging
- All changes must pass CI (GitHub Actions: lint, test, type-check)
- Merge to `main` auto-deploys to staging environment
- QA team validates staging within 2 business hours

### Step 2: Canary (5%)
- After staging approval, deploy to 5% of production traffic
- Monitor error rates, latency (p50, p95, p99), and business metrics for 30 minutes
- Automatic rollback if error rate exceeds 0.5% or p99 latency exceeds 2x baseline

### Step 3: Progressive Rollout
- 25% → monitor 15 minutes
- 50% → monitor 15 minutes
- 100% → full rollout

### Rollback Procedure
- Any engineer can trigger an immediate rollback via: `acme deploy rollback --service <name>`
- Rollbacks complete within 3 minutes
- All rollbacks must be followed by an incident report within 24 hours

**Deploy freeze**: No deployments are permitted on Fridays after 2 PM PT or during company-wide holidays. Emergency hotfixes require VP Engineering approval.

## 4. Service Level Objectives (SLOs)

| Service | Availability | Latency (p99) | Error Budget (monthly) |
|---------|-------------|----------------|----------------------|
| API Gateway | 99.9% | 500ms | 43.2 minutes downtime |
| Analytics Engine | 99.5% | 2000ms | 3.6 hours downtime |
| Dashboard UI | 99.9% | 1000ms | 43.2 minutes downtime |
| Data Pipeline | 99.0% | N/A (batch) | 7.2 hours downtime |

Error budgets reset on the 1st of each month. When an error budget is exhausted, the team must prioritize reliability work over feature development until the budget resets.

## 5. Post-Mortem Process

Post-mortems are required for all P1 and P2 incidents and optional for P3. They must be completed within 5 business days of incident resolution.

**Post-mortem template:**
1. Incident summary and timeline
2. Root cause analysis (use 5 Whys technique)
3. Impact assessment (users affected, duration, revenue impact)
4. Action items with owners and due dates
5. Lessons learned

Post-mortems are blameless. The goal is systemic improvement, not individual accountability. All post-mortems are shared in the #engineering-postmortems Slack channel and reviewed in the monthly engineering all-hands.

For security-related incidents, see the Security Policy for additional incident reporting requirements and compliance obligations.

## 6. Development Environment Setup

See the Onboarding Guide for complete development environment setup instructions including repository access, local tooling, and cloud credentials.

**Key repositories:**
- `acme-api`: Core API service (Python/FastAPI)
- `acme-dashboard`: Frontend application (React/TypeScript)
- `acme-data`: Data pipeline and ETL (Python/Airflow)
- `acme-infra`: Infrastructure as Code (Terraform)

**Required tools:**
- Docker Desktop 4.x+
- Python 3.12+
- Node.js 20 LTS
- Terraform 1.5+
- AWS CLI v2

## 7. Code Review Standards

All code changes require at least 1 approval from a team member before merging. Changes to infrastructure, security, or shared libraries require 2 approvals.

**Review checklist:**
- Tests pass and coverage does not decrease
- No new linting warnings
- API changes have updated documentation
- Database migrations are backward-compatible
- Secrets are not committed (enforced by pre-commit hooks)
