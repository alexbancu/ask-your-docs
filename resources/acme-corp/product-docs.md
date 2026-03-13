# Acme Analytics — Product Documentation

Last updated: February 10, 2025

## 1. Product Overview

Acme Analytics is a B2B SaaS platform that helps mid-market and enterprise companies transform raw data into actionable business insights. The platform ingests data from 40+ integrations, processes it through customizable pipelines, and presents results in real-time dashboards.

**Key capabilities:**
- Real-time data ingestion and transformation
- Custom dashboard builder with drag-and-drop widgets
- Automated alerting and anomaly detection
- Scheduled report generation and email delivery
- Role-based access control with team workspaces
- REST API for programmatic access

**Current metrics (Q4 2024):**
- 2,800+ active customers
- 15 billion events processed daily
- 99.9% API uptime (trailing 12 months)
- Average query response time: 340ms

## 2. REST API Reference

The Acme Analytics API follows RESTful conventions and uses JSON for request/response bodies.

**Base URL**: `https://api.acmeanalytics.com/v2`

**Authentication**: All API requests require a Bearer token in the Authorization header. API keys can be generated in Settings → API Keys. See the Security Policy for API key management and rotation requirements.

**Rate limits**: 1,000 requests per minute per API key. Burst allowance: 50 requests per second. Rate limit headers are included in all responses (`X-RateLimit-Remaining`, `X-RateLimit-Reset`).

### Key Endpoints

#### Query Data
```
POST /v2/query
Content-Type: application/json
Authorization: Bearer <api_key>

{
  "dataset": "web_analytics",
  "metrics": ["page_views", "unique_visitors"],
  "dimensions": ["page_url", "country"],
  "filters": [{"field": "date", "op": "gte", "value": "2025-01-01"}],
  "limit": 100
}
```

#### List Dashboards
```
GET /v2/dashboards
Authorization: Bearer <api_key>
```

#### Create Alert
```
POST /v2/alerts
Content-Type: application/json
Authorization: Bearer <api_key>

{
  "name": "High Error Rate",
  "dataset": "api_logs",
  "condition": {"metric": "error_rate", "op": "gt", "threshold": 0.05},
  "notify": ["email:team@company.com", "slack:#alerts"]
}
```

#### Export Report
```
POST /v2/reports/export
Content-Type: application/json
Authorization: Bearer <api_key>

{
  "dashboard_id": "dash_abc123",
  "format": "pdf",
  "date_range": {"start": "2025-01-01", "end": "2025-01-31"}
}
```

**Error codes:**
| Code | Meaning |
|------|---------|
| 400 | Bad Request — invalid query syntax |
| 401 | Unauthorized — invalid or expired API key |
| 403 | Forbidden — insufficient permissions |
| 429 | Too Many Requests — rate limit exceeded |
| 500 | Internal Server Error — contact support |

## 3. Data Model

Acme Analytics organizes data into **Datasets**, **Metrics**, and **Dimensions**.

**Datasets**: Logical groupings of related data (e.g., `web_analytics`, `api_logs`, `revenue`). Each customer can create up to 50 datasets on the Standard plan and unlimited datasets on the Enterprise plan.

**Metrics**: Numeric values that can be aggregated (sum, avg, count, min, max, percentiles). Examples: `page_views`, `revenue`, `error_count`.

**Dimensions**: Categorical fields used for grouping and filtering. Examples: `country`, `browser`, `plan_type`.

**Retention**: Raw event data is retained for 13 months. Aggregated data is retained for 3 years. Enterprise customers can configure custom retention policies up to 7 years.

## 4. Integrations

Acme Analytics supports 40+ data source integrations organized by category:

**Web & Mobile**: Google Analytics, Segment, Mixpanel, Amplitude, Firebase
**Cloud Infrastructure**: AWS CloudWatch, Datadog, New Relic, PagerDuty
**Databases**: PostgreSQL, MySQL, MongoDB, Snowflake, BigQuery
**Business Tools**: Salesforce, HubSpot, Stripe, Zendesk, Jira
**Custom**: Webhooks, REST API, CSV upload, S3 bucket sync

Integration setup is self-service through the Integrations page. Most integrations sync data every 5 minutes; batch integrations (CSV, S3) can be configured for hourly or daily sync.

## 5. Pricing Plans

| Feature | Starter | Standard | Enterprise |
|---------|---------|----------|------------|
| Events/month | 10M | 100M | Unlimited |
| Datasets | 5 | 50 | Unlimited |
| Users | 3 | 25 | Unlimited |
| Data retention | 3 months | 13 months | Custom (up to 7 years) |
| API access | Read-only | Full | Full + Admin |
| Support | Email | Email + Chat | Dedicated CSM |
| SSO/SAML | No | No | Yes |
| Price | $99/mo | $499/mo | Custom |

All plans include a 14-day free trial. Annual billing receives a 20% discount.

## 6. Frequently Asked Questions

**Q: How do I reset my API key?**
A: Navigate to Settings → API Keys → click "Rotate Key." The old key remains valid for 24 hours to allow migration. See Security Policy for key rotation best practices.

**Q: Can I export my data?**
A: Yes. Use the Export API endpoint or the Dashboard export feature (PDF, CSV, PNG formats). Enterprise customers also have access to bulk data export via S3.

**Q: What happens if I exceed my event limit?**
A: Events exceeding your plan limit are queued for up to 24 hours. You'll receive an email notification at 80% and 100% of your limit. Upgrade your plan to resume processing immediately.

**Q: Is there a sandbox environment?**
A: Yes. All accounts include a sandbox environment at `https://sandbox.acmeanalytics.com` with sample data for testing API integrations.

## 7. Support

- **Documentation**: docs.acmeanalytics.com
- **Status page**: status.acmeanalytics.com
- **Email**: support@acmeanalytics.com
- **Chat**: Available in-app for Standard and Enterprise plans
- **Emergency**: For P1 issues, email urgent@acmeanalytics.com or call 1-800-ACME-911
