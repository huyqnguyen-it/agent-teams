# Sample Service Deployment Guide

## Revision

| Rev | Date       | Scope                   |
| --- | ---------- | ----------------------- |
| 1   | 2026-01-15 | First release           |
| 2   | 2026-02-20 | Search and a new volume |

Note:
 - A variable absent from the manifest takes the Default.
 - Example = the value set on staging; blank = Default.

## Infrastructure Request

New resources this release needs. Prepare them before the Runbook starts.

**New services**

| Service       | Replicas | CPU request | Memory request / limit | Purpose       |
| ------------- | -------- | ----------- | ---------------------- | ------------- |
| sample-search | 1        | `100m`      | `256Mi` / `1Gi`        | Search index. |

**New data stores**

| Volume        | Size   | Access          | Used by       | Retention |
| ------------- | ------ | --------------- | ------------- | --------- |
| `search-data` | `10Gi` | `ReadWriteOnce` | sample-search | 7 days    |

## Before You Start

**Words used in this guide**

| Word   | Meaning                  |
| ------ | ------------------------ |
| API    | The sample-api service   |

**How to deploy one service**

1. Compare the service's variables with its manifest.
2. Apply the manifest.
3. Wait for the rollout.
4. Run the section's **Check**. Do not start the next step until it passes.

**If a step fails**

| You see                     | Likely cause       | What to do              |
| --------------------------- | ------------------ | ----------------------- |
| Pod stays `ContainerCreating` | Volume not bound | Check the volume        |
| Anything else               |                    | Stop, keep the logs, call the service owner |

## Runbook

Order of work for this release. Settings and **Check** are in the named section.

| #   | Step                     | Section       |
| --- | ------------------------ | ------------- |
| 1   | Apply settings           | Settings      |
| 2   | Create the volume        | Data store    |
| 3   | Deploy sample-search     | sample-search |
| 4   | Deploy sample-api        | sample-api    |
| 5   | Smoke test               | —             |

Notes:
 - Rollback: redeploy the previous image tags, in reverse order.
 - Smoke test passes when: a search returns a result.

## Services

| Service       | Image                                     | Tag      |
| ------------- | ----------------------------------------- | -------- |
| sample-api    | `registry.example.com/sample-api`         | `v1.1.0` |
| sample-search | `registry.example.com/sample-search`      | `v1.0.0` |

## System Topology

```
 Browser ──► sample-api ──► database
                 └────────► sample-search ──► search-data
```

## Settings

| Variable    | Type   | Default | Required | Description       |
| ----------- | ------ | ------- | -------- | ----------------- |
| `API_URL`   | URL    | —       | yes      | Public address.   |
| `LOG_LEVEL` | string | `info`  | no       | Logger threshold. |

## Data store

| Item   | Value                 |
| ------ | --------------------- |
| Volume | `search-data`, `10Gi` |
| Mount  | `/data`               |

**Check:** the volume is `Bound`.

## sample-api

**Image:** `registry.example.com/sample-api:v1.1.0`

| Variable       | Type   | Default | Required | Description        |
| -------------- | ------ | ------- | -------- | ------------------ |
| `DATABASE_URL` | URL    | —       | yes      | Primary store.     |
| `SEARCH_URL`   | URL    | unset   | no       | Search endpoint.   |
| `PORT`         | number | `8080`  | no       | HTTP port.         |

**Check:**

```bash
curl -s http://sample-api:8080/health
```

Expected: `200`.

## sample-search

**Image:** `registry.example.com/sample-search:v1.0.0`

| Variable   | Type   | Default | Required | Description  |
| ---------- | ------ | ------- | -------- | ------------ |
| `DATA_DIR` | string | `/data` | no       | Data folder. |

**Check:** `curl -s http://sample-search:9000/health` → 200.

## Post-Deploy Operations

### Rebuild the search index

```bash
curl -X POST http://sample-api:8080/admin/reindex
```

Expected: `202`.

## Change Summary

Everything that changes against Rev 1, in one place. Compare it with the environment before you deploy.

### Services

| Service    | Rev 1    | This release |
| ---------- | -------- | ------------ |
| sample-api | `v1.0.0` | `v1.1.0`     |

New services: sample-search `v1.0.0`.

### Infrastructure

| Item    | Change                     |
| ------- | -------------------------- |
| Volumes | New: `search-data` `10Gi`  |

### Ingress

| Path      | Rev 1 | This release       |
| --------- | ----- | ------------------ |
| `/search` | —     | New: sample-search |

### Environment: renamed

| Service    | Old      | New            |
| ---------- | -------- | -------------- |
| sample-api | `DB_URL` | `DATABASE_URL` |

### Environment: removed

| Service    | Variables    |
| ---------- | ------------ |
| sample-api | `LEGACY_API` |

### Environment: new

| Service    | Variables    |
| ---------- | ------------ |
| sample-api | `SEARCH_URL` |
