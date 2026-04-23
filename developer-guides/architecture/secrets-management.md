# Secrets Management

**Last updated:** 2026-04-23
**Owner:** Tim Gray (solo maintainer)

## Policy

1. **No plaintext secret values in tracked files.** Enforced by the global pre-commit hook at `~/.git-hooks/pre-commit` (13 patterns: Anthropic, OpenAI, Twilio, AWS, Stripe, SendGrid, GitHub, Slack, and private-key blocks).
2. **Secret-pattern env vars** (keys matching `*_KEY`, `*_TOKEN`, `*_SECRET`, `*_AUTH*`, `*_SID`, `*_PASSWORD`, plus `DATABASE_URL`, `GCS_CREDENTIALS_JSON`) live **only** in Railway project variables and in the local dev `.env` (gitignored).
3. **No secret values echoed into Claude Code transcripts.** Enforced by `.claude/hooks/block_unsafe_railway_variables.py`, wired as a `PreToolUse` Bash hook in `.claude/settings.local.json`. Blocks bare `railway variables`, `railway variables --json`, and `railway variables --kv`.
4. **Rotation cadence:** annually, minimum. Next due: **2027-04-23**.

## Why this policy exists

On 2026-04-16 an audit of the sibling project `maia_code` revealed plaintext `ANTHROPIC_API_KEY`, `TWILIO_ACCOUNT_SID`, and `TWILIO_AUTH_TOKEN` committed to git history. During that audit, gcloud-describe commands echoed live secret values into the Claude Code conversation, compounding the exposure. Rotation was successful, but the incident motivated applying the same hardening to every project in this user's workspace.

Vilora was audited 2026-04-23. The repo and git history were clean. All findings were platform-consequences of Railway's plaintext env-var model. This document records the accepted-risk posture and the guardrails installed to prevent regression.

## What's deployed today

All production secrets live in Railway (project "Vilora", environment "production", service "web").

| Env var | Consumer | Notes |
|---|---|---|
| `ANTHROPIC_API_KEY` | `mediation/engine.py`, all Claude calls | |
| `SENDGRID_API_KEY` | `notifications.py` | Transactional email |
| `GCS_CREDENTIALS_JSON` | `storage.py` | Full SA JSON for `vilora-storage@maia-tech.iam.gserviceaccount.com`. See hardening note below. |
| `GCS_BUCKET_NAME` | `storage.py` | Not a secret, just config. |
| `DATABASE_URL` | `models/database.py` via Flask | Postgres URI with embedded password |
| `SECRET_KEY` | Flask session signing | |

Twilio env vars (`TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER`) are referenced by `sms.py` but currently absent from Railway. SMS paths silently no-op in production until configured.

## Accepted risk: Railway plaintext storage

Railway has no Secret-Manager-equivalent retrieval-restricted layer. Every variable in the Railway dashboard is stored and injected as plaintext; reference variables (`${{Service.VAR}}`) resolve to literal values at container start. GCP Secret Manager / AWS Secrets Manager bindings are not available on this platform.

**Threat model we accept:**
- Anyone with Owner/Admin access to the Railway project can read every secret value.
- Anyone with shell access to the dev laptop can read `.env` (which today contains `ANTHROPIC_API_KEY`).
- A Railway breach of the project would expose all five secrets listed above.

**Mitigations in place:**
- GitHub repo is private, single-owner, no forks.
- Railway project is single-owner (one collaborator).
- GCS service account is minimally scoped (see "Service account IAM" below).
- Annual rotation schedule.

**Upgrade paths if risk profile changes** (revenue, team growth, compliance obligations):
- Option B: Introduce Doppler as source of truth with Railway sync. Still plaintext at injection; centralizes rotation/audit/versioning. ~1 day of integration work.
- Option C: Fetch secrets from an external KMS at app startup (GCP Secret Manager, AWS Secrets Manager, Vault). Multi-day work plus ongoing operational cost. Overkill pre-revenue.

## Service account IAM (GCS)

Audit on 2026-04-23 confirmed:

- `vilora-storage@maia-tech.iam.gserviceaccount.com` has **zero** project-level IAM roles.
- Only bucket-level binding: `roles/storage.objectAdmin` on `gs://vilora-uploads`.
- Single user-managed key (created 2026-04-05). No orphaned keys.

Blast radius if the SA private key leaks: read/write/delete objects in `vilora-uploads` only. No project escalation path.

## Deferred hardening: HMAC keys for GCS

The current `storage.py` stuffs the full SA JSON (including private-key block) into `GCS_CREDENTIALS_JSON`. An alternative is to use GCP HMAC keys, which are a scoped access-key/secret pair for the Cloud Storage XML API only.

**Re-evaluate before adopting.** This is a non-trivial migration:
- `google-cloud-storage` Python SDK does not accept HMAC keys. Would require switching to `boto3` pointed at `storage.googleapis.com`.
- Signed URL generation algorithm changes (GCS V4 to S3-style V2). Any code or frontend that parses URL format must be re-tested.
- Test surface: file upload in session, file download, inline preview (images), signed URL expiry, file delete.
- Still requires an SA (HMAC keys inherit the SA's permissions); the win is replacing a 2348-char private key with a 24/40-char access/secret pair.

Budget: ~1-2 hours plus manual end-to-end testing. Re-evaluate risk/reward against whatever the posture is when next considered. Not scheduled.

## How to add a new secret

1. Generate the secret in the provider console (Anthropic, SendGrid, etc.).
2. **Do not paste the value into any tracked file** (`.env.example`, deploy scripts, code, commit message, README, etc.). The pre-commit hook will block patterns it recognizes, but never rely on it.
3. Set the value in Railway via dashboard (preferred) or CLI. If using CLI, pipe from a file so the value does not enter shell history:
   ```bash
   railway variables --set "NEW_SECRET_NAME=$(cat /tmp/secret.txt)"
   rm /tmp/secret.txt
   ```
4. Set the same value in local `.env` for dev. Never commit `.env`.
5. Read from code via `os.environ.get('NEW_SECRET_NAME')`, with graceful fallback if unset (see `sms.py` or `storage.py` for the no-op pattern).
6. If the key name matches a secret pattern and you want to add it to this document, update the table above.

## How to rotate a secret

1. Generate new value in provider console.
2. Update Railway variable (dashboard or CLI as in step 3 above).
3. `railway redeploy` to pick up the new value.
4. Verify the feature still works (for Anthropic: send a test message in a session; for SendGrid: trigger a test notification; for GCS: upload a test file).
5. Revoke or delete the old credential in the provider console.
6. Update local `.env` on dev machine.
7. Update the "next due" date at the top of this document.

## Out of scope

- Local dev flows. `.env` on the dev laptop is expected to be populated and is gitignored. It is a laptop-compromise exposure surface, accepted for now.
- Test fixtures with obviously-fake keys in `tests/`. The pre-commit hook does not false-positive these (all fixtures use `FAKE0000…` placeholders).
- The `.claude/` directory. Gitignored; contains local Claude Code session state only.

## Guardrails installed (2026-04-23)

| Location | What it does |
|---|---|
| `~/.git-hooks/pre-commit` | Global pre-commit hook. Blocks 13 secret patterns. Uses `command grep -En --` to be robust to shell-wrapper environments (e.g. Claude Code's ugrep-as-grep wrapper). |
| `.claude/hooks/block_unsafe_railway_variables.py` | PreToolUse Bash hook. Blocks `railway variables` reads that don't pipe to a keys-only filter. |
| `.claude/settings.local.json` | Wires the Railway hook into Claude Code. |
| `.gitignore` | Comprehensive credential-filename patterns (`creds.json`, `service-account*.json`, `firebase-adminsdk-*.json`, `*.pem`, `*.key`, etc.). |
