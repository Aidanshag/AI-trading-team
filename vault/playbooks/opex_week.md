---
type: playbook
triggers: [monthly index options expiration, quarterly expiration, VIX expiration]
applies_to: [index_macro]
---

# Opex week

## Trigger

- Third Friday of each month (monthly opex).
- Third Friday of Mar/Jun/Sep/Dec (quarterly / triple witching).
- VIX expiration: Wednesday before monthly opex.

## What agents must NOT do

- Do not assume trend continuation into opex; dealer-gamma pinning is real.
- Do not initiate short-vol structures into opex if VIX term is backwardated.

## Preferred structures

- Pin-risk plays: defined-risk iron flies / condors at high-gamma strikes.
- Post-opex Monday: mean-reversion setups in [[ES]] / [[NQ]] after opex-induced pinning.

## What to watch

- Dealer gamma positioning estimates (SpotGamma / SqueezeMetrics).
- Put wall / call wall levels — these often act as magnets or barriers.
- VIX term-structure shape (contango vs backwardation) on Thursday.

## Exit

- Same session for intraday; post-opex swing setups must close by Wednesday following.
