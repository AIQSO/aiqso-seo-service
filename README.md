# AIQSO SEO Service

Enterprise SEO auditing, rank tracking, and optimization platform.

## Features

- **Technical SEO Audits**: 24+ checks for meta tags, content, performance, and configuration
- **Rank Tracking**: Daily keyword position monitoring via SerpBear integration
- **Performance Audits**: Google Lighthouse integration for Core Web Vitals
- **AI-Powered Insights**: Content analysis and recommendations using Claude
- **Client Dashboard**: White-label reporting and historical tracking
- **API Access**: RESTful API for integrations

## Architecture

```
┌─────────────────────────────────────────────┐
│         AIQSO Website (Next.js)             │
│         - Service Pages                     │
│         - Client Portal                     │
│         - Admin Dashboard                   │
└─────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────┐
│      AIQSO SEO Service (FastAPI)            │
│                                             │
│  ├── /api/audit      - Run SEO audits       │
│  ├── /api/rankings   - Track keywords       │
│  ├── /api/lighthouse - Performance audits   │
│  ├── /api/reports    - Generate reports     │
│  └── /api/clients    - Client management    │
└─────────────────────────────────────────────┘
                    │
        ┌───────────┼───────────┐
        ▼           ▼           ▼
┌──────────┐ ┌──────────┐ ┌──────────┐
│ SerpBear │ │Lighthouse│ │PostgreSQL│
│  :3000   │ │  CI      │ │  :5432   │
└──────────┘ └──────────┘ └──────────┘
```

## Service Tiers

| Tier | Price | Keywords | Sites | Audits | Features |
|------|-------|----------|-------|--------|----------|
| Starter | $500/mo | 50 | 1 | Weekly | Basic reports |
| Professional | $1,500/mo | 200 | 3 | Daily | AI insights |
| Enterprise | $3,500/mo | 500 | 10 | Real-time | Full API |
| Agency | $5,000/mo | 1000+ | Unlimited | Custom | White-label |

## Quick Start

```bash
# Clone and setup
git clone https://github.com/qvidal01/aiqso-seo-service.git
cd aiqso-seo-service

# Install dependencies
pip install -r requirements.txt

# Run development server
uvicorn app.main:app --reload --port 8002
```

## Environment Variables

```bash
DATABASE_URL=postgresql://user:pass@localhost:5432/seo_service
SERPBEAR_API_URL=http://localhost:3000/api
SERPBEAR_API_KEY=your_api_key
SCRAPING_API_KEY=your_scrapingant_key
ANTHROPIC_API_KEY=your_claude_key
```

## Deployment

Deploy on Proxmox LXC with Docker Compose:

```bash
docker-compose up -d
```

## License

Proprietary - AIQSO LLC
