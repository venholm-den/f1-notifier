# F1 Weekend poster

Posts race-weekend info (schedule, results, standings) into Discord via webhook.

## Secrets

- `DISCORD_F1_WEEKEND_WEBHOOK_URL`

## State

Uses `f1_weekend_state.json` to avoid duplicate posts.

## Data sources

Tries Jolpica (Ergast-compatible) first, then falls back to the legacy Ergast endpoint.
