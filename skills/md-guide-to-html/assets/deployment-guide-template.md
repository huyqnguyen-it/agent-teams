# <Product> Deployment Guide

## Revision

| Rev | Date       | Scope                   |
| --- | ---------- | ----------------------- |

Note:
 - A variable absent from the manifest takes the Default.
 - Example = the value set on staging; blank = Default.

## Infrastructure Request

New resources this release needs. Prepare them before the Runbook starts.

**New services**

| Service       | Replicas | CPU request | Memory request / limit | Purpose       |
| ------------- | -------- | ----------- | ---------------------- | ------------- |

**New data stores**

| Volume        | Size   | Access          | Used by       | Retention |
| ------------- | ------ | --------------- | ------------- | --------- |

## Before You Start

**Words used in this guide**

| Word   | Meaning                  |
| ------ | ------------------------ |

**How to deploy one service**

1. Compare the service's variables with its manifest.
2. Apply the manifest.
3. Wait for the rollout.
4. Run the section's **Check**. Do not start the next step until it passes.

**If a step fails**

| You see                     | Likely cause       | What to do              |
| --------------------------- | ------------------ | ----------------------- |

## Runbook

Order of work for this release. Settings and **Check** are in the named section.

| #   | Step                     | Section       |
| --- | ------------------------ | ------------- |

Notes:
 - Rollback: redeploy the previous image tags, in reverse order.
 - Smoke test passes when: <observable result>.

## Services

| Service       | Image                                     | Tag      |
| ------------- | ----------------------------------------- | -------- |

## System Topology

```
<ASCII diagram of services, stores and telemetry>
```

## Settings

| Variable    | Type   | Default | Required | Description       |
| ----------- | ------ | ------- | -------- | ----------------- |

## Data store

| Item   | Value                 |
| ------ | --------------------- |

**Check:** <how to confirm>.

## <service-name>

**Image:** `<registry>/<image>:<tag>`

| Variable       | Type   | Default | Required | Description        |
| -------------- | ------ | ------- | -------- | ------------------ |

**Check:**

```bash
<command>
```

Expected: <result>.


## Post-Deploy Operations

### <Operation>

```bash
<command>
```

Expected: <result>.

## Change Summary

Everything that changes against Rev 1, in one place. Compare it with the environment before you deploy.

### Services

| Service    | Rev 1    | This release |
| ---------- | -------- | ------------ |

New services: <service> `<tag>`.

### Infrastructure

| Item    | Change                     |
| ------- | -------------------------- |

### Ingress

| Path      | Rev 1 | This release       |
| --------- | ----- | ------------------ |

### Environment: renamed

| Service    | Old      | New            |
| ---------- | -------- | -------------- |

### Environment: removed

| Service    | Variables    |
| ---------- | ------------ |

### Environment: new

| Service    | Variables    |
| ---------- | ------------ |
