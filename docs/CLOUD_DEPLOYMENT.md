# Cloud deployment from the start

SafeRecover includes `render.yaml`, so the cloud architecture is versioned with the application. It provisions:

- the FastAPI service;
- an n8n web service;
- the React dashboard as a static site; and
- PostgreSQL shared by SafeRecover and n8n using separate schemas.

## 1. Push the repository to GitHub

Create a new empty repository, add it as the remote, and push the existing commit history.

## 2. Create a Render Blueprint

In Render, choose **New > Blueprint**, select the GitHub repository, and apply `render.yaml`. Render will ask for values marked `sync: false`.

Use these values after the first service URLs are assigned:

| Variable | Service | Value |
|---|---|---|
| `GEMINI_API_KEY` | API | Key created in Google AI Studio |
| `CORS_ORIGINS` | API | Dashboard URL, without a trailing slash |
| `N8N_RETRY_WEBHOOK_URL` | API | `https://<n8n-host>/webhook/saferecover-retry` |
| `N8N_HOST` | n8n | n8n hostname only, without `https://` |
| `WEBHOOK_URL` | n8n | Full n8n URL with trailing slash |
| `SAFERECOVER_API_URL` | n8n | Full FastAPI service URL |
| `VITE_API_URL` | Dashboard | Full FastAPI service URL |

Trigger a new dashboard deploy after setting `VITE_API_URL`, because Vite injects it at build time.

## 3. Configure n8n

Open the deployed n8n service and create its owner login. Import all five JSON files in `n8n/`:

1. `01-invoice-processing.json`
2. `02-legal-document-intake.json`
3. `03-expense-approval.json`
4. `failure-capture-workflow.json`
5. `recovery-runner-workflow.json`

Activate the two SafeRecover control workflows. In each of the three SME workflows, open **Workflow settings** and select **SafeRecover - Failure Capture** as its error workflow. Activate the SME workflows.

## 4. Verify the cloud loop

Send a deliberately conflicting invoice:

```bash
curl -X POST "https://<n8n-host>/webhook/invoice-intake" \
  -H "Content-Type: application/json" \
  -d '{"invoice_number":"INV-1042","supplier_id":"SUP-18","total":12500,"extracted_total":1250,"currency":"GBP"}'
```

The n8n execution should fail, the error workflow should create a SafeRecover event, and the dashboard should show the event as blocked/escalated. No amount should be overwritten.

## Free-tier note

The included plans are suitable for a portfolio demonstration, not production. Free services can sleep or restart, and free Render Postgres databases currently expire after 30 days. For a persistent public portfolio deployment, upgrade the database or replace it with a persistent external PostgreSQL provider and set `DATABASE_URL` and the n8n database variables accordingly.
