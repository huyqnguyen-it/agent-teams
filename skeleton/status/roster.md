# Roster

States: `running`, `parked (since HH:MM)`, `stopped`. A parked agent waits for a follow-up and is stopped after `PARK_TTL_MIN` minutes (60) without a message. `capacity-check.sh` counts `running` and `parked` rows against `ceiling`.

| Agent | Role | Host | Model | State |
|---|---|---|---|---|
