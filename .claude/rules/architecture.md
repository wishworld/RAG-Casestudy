# Architecture Rules

## Day 1 Architecture Default

- Build as a **Modular Monolith** first.
- Every module must expose clear **API input/output contracts** (request, response, errors).
- Keep strict **domain boundaries**: no cross-module DB table access, no hidden coupling.
- Use **one deployable unit** until clear scale/team pain appears.
- Design modules so they can be extracted into microservices later without major rewrites.

## Event-Driven Usage (Day 1)

- Use **API-first (sync)** for core request-response actions.
- Add **event-driven (async)** only where decoupling adds clear value:
  - notifications
  - audit logs
  - workflow state changes
  - downstream non-blocking processors (scoring, analytics, CRM updates)
- Publish **domain events** with versioned schemas (e.g., `loan.application.submitted.v1`).
- Make consumers **idempotent** and support retries + dead-letter queue handling.
- Do not use async events for steps requiring immediate user confirmation.

## Reliability and Governance

- Add observability from day 1: structured logs, metrics, trace IDs, audit trail for critical actions.
- For fintech flows, enforce idempotency, retries with backoff, and explicit failure handling.
- Security/compliance by default: authn/authz checks, PII minimization, encryption in transit, auditability.
- Any new feature must include the following. **AI generates all five from a plain-language feature description. The engineer reviews and approves — not writes from scratch.**
  1. Module owner
  2. API contract (request / response / errors)
  3. Event contract (if async is used): event name, version, payload, consumers
  4. Success metric (e.g. p95 latency, error rate threshold)
  5. Failure / rollback path

## Evolution Trigger (When to move beyond Day 1)

Move a module to a separate service only if at least one is true:
- Independent scaling is required
- Independent release cadence is required
- Team ownership boundaries are blocked by monolith
- Reliability isolation is required (failures must not cascade)

Until then, optimize for speed, clarity, and correctness inside the modular monolith.
