# Acme Corp Security Policy

Last updated: January 20, 2025

## 1. Data Protection

Acme Corp is committed to protecting customer data and maintaining the highest security standards.

### Encryption
- **Data at rest**: All data is encrypted using AES-256 encryption. Database encryption is managed through AWS KMS with automatic key rotation every 90 days.
- **Data in transit**: All communications use TLS 1.3. HTTP connections are automatically redirected to HTTPS. Certificate management is handled through AWS Certificate Manager.
- **Backup encryption**: All backups are encrypted with separate KMS keys and stored in geographically redundant locations (US-East-1 and US-West-2).

### PII Handling
Personally Identifiable Information (PII) is classified as Restricted data and subject to additional controls:
- PII must be tagged in the data catalog before processing
- Access to PII requires explicit approval from the Data Protection Officer (DPO)
- PII is automatically masked in non-production environments
- Retention: PII is purged 30 days after account deletion unless legally required
- Customer data is never used for model training or analytics without explicit consent

### Data Classification
| Level | Examples | Access | Storage |
|-------|----------|--------|---------|
| Public | Marketing content, docs | All employees | Any approved system |
| Internal | Internal wikis, roadmap | Employees + contractors | Corporate systems |
| Confidential | Customer data, financials | Need-to-know basis | Encrypted systems only |
| Restricted | PII, credentials, keys | Explicit DPO approval | Encrypted + audited |

## 2. Authentication and Access Control

### Single Sign-On (SSO)
All Acme Corp systems use Okta as the identity provider for Single Sign-On. Employees must authenticate through Okta to access any corporate resource. SSO session timeout is set to 12 hours.

### Multi-Factor Authentication (MFA)
MFA is mandatory for all employees and enforced through Okta. Supported methods:
- Hardware security keys (YubiKey) — preferred for engineering and admin roles
- TOTP authenticator apps (Google Authenticator, Authy)
- Okta push notifications

SMS-based MFA is not permitted due to SIM-swapping risks.

### Password Policy
- Minimum length: 16 characters
- Must include: uppercase, lowercase, numbers, and special characters
- Password history: last 12 passwords cannot be reused
- Maximum age: 90 days
- Account lockout: 5 failed attempts → 30-minute lockout
- Passwords must not appear in known breach databases (checked via Have I Been Pwned API)

### Role-Based Access Control (RBAC)
Access to systems follows the principle of least privilege:

| Role | Permissions | Approval |
|------|------------|----------|
| Developer | Read/write to team repos, staging environment | Team lead |
| Senior Developer | Above + production read access | Team lead |
| Team Lead | Above + production deploy, on-call management | Engineering VP |
| Engineering VP | Above + infrastructure changes, vendor access | CTO |
| Admin | Full access to all systems | CTO + Security Lead |

Access reviews are conducted quarterly. Unused accounts are deactivated after 30 days of inactivity.

## 3. Compliance

### SOC 2 Type II
Acme Corp maintains SOC 2 Type II certification, audited annually by Deloitte. Our latest audit (completed September 2024) covers:
- Security
- Availability
- Processing Integrity
- Confidentiality

Audit reports are available to customers under NDA. Contact security@acmecorp.com to request a copy.

### GDPR
Acme Corp is fully GDPR compliant for EU customer data:
- Data Processing Agreements (DPA) are available for all customers
- EU customer data is processed and stored in the EU-West-1 (Ireland) region
- Data Subject Access Requests (DSAR) are fulfilled within 30 days
- A Data Protection Officer (DPO) is appointed: privacy@acmecorp.com

### Additional Compliance
- **CCPA**: California Consumer Privacy Act compliant
- **HIPAA**: Available for Enterprise Healthcare customers (BAA required)
- **ISO 27001**: Certification in progress (target: Q3 2025)

## 4. Incident Response

### Reporting Security Incidents
All security incidents must be reported immediately through one of the following channels:
- Slack: #security-incidents (for internal reports)
- Email: security@acmecorp.com
- PagerDuty: Security team escalation (for after-hours emergencies)
- Anonymous: ethics hotline at 1-800-ACME-ETH

See the Engineering Runbook for general incident severity levels and escalation procedures.

### Security Incident Classification
| Severity | Description | Response Time |
|----------|-------------|---------------|
| SEV-1 | Active breach, data exfiltration | Immediate (< 15 min) |
| SEV-2 | Vulnerability actively exploited | < 1 hour |
| SEV-3 | Vulnerability discovered, not exploited | < 24 hours |
| SEV-4 | Policy violation, misconfiguration | < 72 hours |

### Breach Notification
In the event of a confirmed data breach:
- Affected customers are notified within 72 hours (GDPR requirement)
- Regulatory authorities are notified as required by applicable law
- A public incident report is published within 30 days
- Free credit monitoring is offered to affected individuals when PII is involved

## 5. Vendor Security

All third-party vendors with access to Acme Corp data must:
- Complete the Vendor Security Questionnaire
- Demonstrate SOC 2 Type II or equivalent certification
- Sign a Data Processing Agreement (DPA)
- Undergo annual security review

**Approved vendors**: AWS, Google Cloud, Okta, PagerDuty, Datadog, GitHub, Slack, Jira, Snowflake. New vendor requests require Security Lead approval and a minimum 2-week review period.

### API Key Management
- API keys must be stored in AWS Secrets Manager or HashiCorp Vault — never in source code
- Keys must be rotated every 90 days
- Separate keys for development, staging, and production environments
- Revoke keys immediately when an employee with access leaves the company
