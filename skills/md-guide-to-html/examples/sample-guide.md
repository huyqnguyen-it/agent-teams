# Sample Service Guide

## Revision

| Rev | Date       | Scope         |
| --- | ---------- | ------------- |
| 1   | 2026-01-15 | First release |

## Runbook

Order of work for this release. Settings and **Check** are in the named section.

| #   | Step                 | Section      |
| --- | -------------------- | ------------ |
| 1   | Create the settings  | Settings     |
| 2   | Deploy the API       | sample-api   |
| 3   | Run the smoke test   | —            |

## System Topology

```
 Browser ──► sample-api ──► database
```

## Settings

| Variable    | Type   | Default | Required | Description        |
| ----------- | ------ | ------- | -------- | ------------------ |
| `API_URL`   | URL    | —       | yes      | Public address.    |
| `LOG_LEVEL` | string | `info`  | no       | Logger threshold.  |

## sample-api

**Image:** `registry.example.com/sample-api:v1.0.0`

| Variable       | Type   | Default | Required | Description     |
| -------------- | ------ | ------- | -------- | --------------- |
| `DATABASE_URL` | URL    | —       | yes      | Primary store.  |
| `PORT`         | number | `8080`  | no       | HTTP port.      |

**Check:**

```bash
curl -s http://sample-api:8080/health
```

Expected: `200`.
