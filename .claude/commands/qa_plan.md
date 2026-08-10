# /qa_plan — Automated QA Plan for Claude Code

You are a test engineer. Your job is to take a spec'd MVP and produce a complete test data catalog + detailed test cases. After `/build`, Claude Code reads this and runs every test using whatever tools it has — CLI, bash, headless browser, HTTP calls, DB queries, file checks — without asking questions.

Every test has a named dataset, a concrete expected outcome, and a verification method. Claude Code picks the tool. You define the bar.

---

## Where This Sits

```
/roadmap → /ux → /spec → /qa_plan → /qa_plan_ux → /build → Claude Code runs /qa_plan → then Cursor runs /qa_plan_ux
```

Written before code exists. Executed after `/build`. `/qa_plan` runs first — if it fails, `/qa_plan_ux` is blocked.

This prompt produces two files:
- `tests/[serial]_test_data.md` — shared test data catalog (consumed by `/qa_plan_ux` too)
- `tests/[serial]_qa_plan.md` — test cases

---

## Input

```
/qa_plan kyc_mvp_1.1
```
or paste the MVP block directly.

---

## Step 0: Gather Context

Read in this order:

1. **Spec** (`specs/[serial]_spec.md`) — API contracts, data model, rules. Primary input.
2. **UX doc** (`ux/[serial]_ux.md`) — inputs, validation rules, error messages, failures.
3. **MVP block** (`roadmaps/`) — acceptance criteria.
4. **Prior QA plans** — same feature shortcode. Reuse patterns.
5. **CLAUDE.md / project config** — conventions.

If no spec exists: stop. Say `Run /spec [serial] first.`

---

## Step 1: Test Data Catalog

Before writing any test cases, define ALL test data. This section is stored as a separate file so `/qa_plan_ux` can consume it.

### 1a. Field Inventory

Walk through spec and UX doc. List every field:

```
FIELD INVENTORY
═══════════════

| Field         | Source        | Type    | Required | Constraints                    | Validation error (from UX doc) |
|---------------|---------------|---------|----------|--------------------------------|-------------------------------|
| [field name]  | [Spec §2/§3] | [type]  | [Y/N]    | [from spec — max, min, format] | [from UX doc — exact message] |
| ...           | ...           | ...     | ...      | ...                            | ...                           |
```

### 1b. Valid Data Sets

At least 2. Different values to prove nothing is hardcoded.

```
VALID DATA SETS
═══════════════

valid_[feature]_1:
  [field]: [concrete value]
  [field]: [concrete value]
  ...
  Satisfies: [which constraints this passes]

valid_[feature]_2:
  [field]: [different concrete value]
  [field]: [different concrete value]
  ...
  Satisfies: [same constraints, different data]
```

Rules:
- Every value is concrete. Not "a valid name" — `"Priya Sharma"`.
- Values must be realistic for the UX doc's user context (locale, formats, plausible data).
- The two sets must differ meaningfully.

### 1c. Invalid Data Sets

One per validation rule per field. Each set has exactly ONE invalid field — everything else valid.

```
INVALID DATA SETS
═════════════════

invalid_[field]_empty:
  [field]: "" ← invalid
  [other fields]: [valid values from valid_1]
  Violates: [field] is required
  Expected error: "[exact message from UX doc]"

invalid_[field]_format:
  [field]: [concrete bad value] ← invalid
  [other fields]: [valid values]
  Violates: [field] format constraint
  Expected error: "[exact message from UX doc]"
```

Rules:
- One dataset per rule per field. Isolate what's broken.
- Expected error is exact string from UX doc. If undefined: `⚠️ Error message not defined in UX doc — flag for /ux update`.

### 1d. Boundary Data Sets

Test edges of constraints. Only for fields with numeric/length limits.

```
BOUNDARY DATA SETS
══════════════════

boundary_[field]_min:
  [field]: [minimum valid value]
  [other fields]: [valid values]
  Tests: lower boundary — should PASS

boundary_[field]_min_minus_1:
  [field]: [one below minimum]
  [other fields]: [valid values]
  Tests: below boundary — should FAIL
  Expected error: "[exact message]"

boundary_[field]_max:
  [field]: [maximum valid value]
  Tests: upper boundary — should PASS

boundary_[field]_max_plus_1:
  [field]: [one above maximum]
  Tests: above boundary — should FAIL
  Expected error: "[exact message]"
```

### 1e. Special Input Data Sets [SKIP IF NO TEXT FIELDS]

```
SPECIAL INPUT DATA SETS
═══════════════════════

special_unicode:
  [text field]: "Müller-Straße" or appropriate unicode for user locale
  Tests: unicode handling

special_script_injection:
  [text field]: "<script>alert('x')</script>"
  Tests: XSS sanitization

special_sql_injection:
  [text field]: "'; DROP TABLE users; --"
  Tests: SQL injection

special_whitespace:
  [text field]: "  Priya  Sharma  "
  Tests: whitespace handling
```

Only include injection sets if spec has security constraints. Otherwise skip and note: `Security testing not in scope per spec.`

### 1f. Seed Data

State that must EXIST before tests run. Not test input — prerequisite state.

```
SEED DATA
═════════

seed_[entity]_1:
  Entity: [what — user, org, config]
  Values:
    [field]: [concrete value]
  Purpose: [which tests need this]
  Create via: [API call / DB insert / setup flow]
  Depends on: [other seed, or "None"]
  Verify exists: [how to confirm]
```

List in dependency order. Parents first.

### 1g. Auth Data [SKIP IF NO AUTH IN SPEC]

```
AUTH DATA
═════════

valid_auth:
  Method: [token / session / cookie]
  Obtain via: [login endpoint + credentials / dev token / env var]
  User: [reference seed_[entity]_N]
  Credentials:
    [username]: [concrete value]
    [password]: [concrete value]

invalid_auth_expired:
  Token/value: [concrete expired token or how to generate]

invalid_auth_malformed:
  Token/value: [concrete garbage — e.g., "not-a-real-token-xyz"]

invalid_auth_wrong_role: [SKIP IF NO ROLES]
  User: [seed user with wrong permissions]
  Credentials: ...
```

---

## Step 2: Determine Test Layers

```
Layer           | Applies? | Source               | Dataset type used
────────────────|──────────|──────────────────────|──────────────────
API contract    | [Y/N]    | Spec §2              | valid, invalid
Data integrity  | [Y/N]    | Spec §3              | valid, boundary, special
Business rules  | [Y/N]    | Spec §4              | valid
Input validation| [Y/N]    | UX doc inputs        | invalid, boundary
Failure handling| [Y/N]    | UX doc §3            | valid + simulation
Auth            | [Y/N]    | Spec §2 auth fields  | auth data
Idempotency     | [Y/N]    | Spec §2 write endpoints | valid
End-to-end      | [Y/N]    | MVP acceptance       | valid
```

---

## Step 3: Write Test Cases

### Header

```
Serial: [from MVP block]
Name: [from MVP block]
Spec: specs/[serial]_spec.md
UX doc: ux/[serial]_ux.md or "None"
Test data: tests/[serial]_test_data.md
Acceptance: [from MVP block]
Layers: [from Step 2]
Total tests: [count]
```

### Test Case Format

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TC-[N]: [What is being proven]
Layer: [API / Data / Rule / Validation / Failure / Auth / Idempotency / E2E]
Traces to: [Spec §N or UX doc Step N]
Priority: [GATE / HIGH / MEDIUM]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

GIVEN:
  State: [reference seed data by name]
  Auth: [reference auth dataset, or "none"]

WHEN:
  Action: [API call method+path / form submission / CLI command]
  Dataset: [name from test data catalog]
  Input:
    {
      [field]: [value from named dataset]
    }

THEN:
  Status: [expected HTTP status / exit code / UI state]
  Response:
    {
      [field]: [expected value or type]
    }
  Side effects:
    - [DB: table X row where field=value / None]

VERIFY:
  ✓ [What]: [expected] — by [method]

  Methods (Claude Code picks):
    - HTTP: call endpoint, check response
    - DB: query table, check row
    - File: check existence/content
    - UI: load URL, check element
    - Absence: confirm NOT exists

ON FAIL: [Which requirement is broken]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Priority Levels

```
GATE:  Fail = stop all. System not functional.
HIGH:  Fail = MVP doesn't work.
MEDIUM: Fail = rough edges.
```

### Test Categories (in order)

#### GATE (run first — circuit breakers)

```
TC-1: System reachable → GET health/root → 200
TC-2: Primary endpoint works → POST with valid_1 → success
TC-3: Data persists → submit → row exists in table
All Priority: GATE
```

#### Happy Path (prove acceptance)

```
Source: UX doc happy path + Spec §2 + MVP acceptance
Datasets: valid_[feature]_1, then valid_[feature]_2

  - Full flow: submit → response → persistence
  - Two datasets (no hardcoding)
  - Final assertion = MVP acceptance verbatim
  Priority: HIGH
```

#### API Contract (per endpoint)

```
Source: Spec §2
Per endpoint:
  - Valid → success, match every response field
  - Each required field omitted → error from spec
  - Each error condition → error response
  Priority: HIGH
```

#### Input Validation (per field)

```
Source: UX doc inputs + invalid datasets
Per field:
  - invalid_[field]_empty → error message
  - invalid_[field]_format → error message
  - valid → no error
  Priority: HIGH (required) / MEDIUM (format/range)
```

#### Business Rules (per rule)

```
Source: Spec §4
Per rule:
  - Condition met → outcome (verify side effect)
  - Condition not met → no change
  Priority: HIGH
```

#### Data Integrity (per constraint)

```
Source: Spec §3 + boundary/special datasets
  - Unique: duplicate → error, one row
  - Required at DB: null → rejected
  - Boundary: max → pass, max+1 → fail
  - Special: injection → sanitized/rejected
  Priority: MEDIUM
```

#### Failure Handling (per UX doc §3 failure)

```
Source: UX doc §3
Per failure:
  - Simulate condition → error matches UX doc → NO side effects → retry works

Simulation (Claude Code picks):
  - Server error: mock 500 / env flag
  - Timeout: unreachable host
  - Auth failure: invalid_auth_expired
  - Not simulatable: mark MANUAL
  Priority: HIGH
```

#### Idempotency (per write endpoint)

```
Source: Spec §2 write endpoints
  - Submit once → success
  - Submit again → idempotent or graceful error
  - One record, not two
  Priority: MEDIUM
```

#### Auth [SKIP IF NO AUTH]

```
Source: Spec §2 + auth datasets
  - valid_auth → granted
  - No header → 401
  - invalid_auth_malformed → 401
  - invalid_auth_expired → 401
  - invalid_auth_wrong_role → 403
  - Failure never leaks data
  Priority: HIGH (valid/missing) / MEDIUM (others)
```

---

## Step 4: Environment Setup

```
ENVIRONMENT SETUP
═════════════════

1. SEED DATA (from Step 1f, dependency order):
   [entity, values, create via, verify]

2. AUTH (from Step 1g):
   [how to obtain each token type]

3. MOCKS (from failure tests):
   [what builder must provide]

4. CLEANUP:
   After all: [reset]
   Between tests: [isolation]
```

---

## Step 5: Execution Contract

```
EXECUTION
═════════

Order:
  1. Setup
  2. GATE → fail = STOP
  3. HIGH → fail = BLOCKER
  4. MEDIUM → fail = WARNING
  5. Cleanup

State: ISOLATED by default. SEQUENTIAL only if specified.

Claude Code decides: framework, files, mock implementation, verification tool
Claude Code does NOT decide: data values, expected outcomes, which tests to skip

Report:
  Total | Passed ✅ | Failed ❌ | Blocked ⏭️
  Per failure: TC-N, expected vs actual
  Acceptance: PROVEN / NOT PROVEN

  GATE passed + acceptance PROVEN → /qa_plan_ux can proceed
  GATE failed → /qa_plan_ux BLOCKED
```

---

## Step 6: Coverage Check

```
COVERAGE
════════

MVP acceptance: "[text]"
  Proven by: TC-[N], TC-[M]

Spec §2: [N] endpoints → [N] tested
Spec §3: [N] constraints → [N] tested
Spec §4: [N] rules → [N] tested
UX inputs: [N] fields → [N] validated
UX failures: [N] → [N] simulated

Datasets used: [list]
Datasets unused: [list — flag for review]

GAPS:
  - [gap] → [recommend]
```

---

## Step 7: Store

Two files:

```
Test data: tests/[serial]_test_data.md    ← consumed by /qa_plan_ux
QA plan:   tests/[serial]_qa_plan.md

Example:
  tests/kyc_mvp_1_1_test_data.md
  tests/kyc_mvp_1_1_qa_plan.md
```

The test data catalog (Step 1) is stored separately so `/qa_plan_ux` reads it without parsing the full QA plan.

---

## Step 8: Report

```
QA Plan: [serial] — [name]
Spec: specs/[serial]_spec.md
UX doc: [path or "None"]
Stored:
  Test data: tests/[serial]_test_data.md
  QA plan: tests/[serial]_qa_plan.md

Data:
  Fields: [count]
  Valid sets: [count]
  Invalid sets: [count]
  Boundary sets: [count]
  Special sets: [count]
  Seed entities: [count]

Tests:
  Total: [count]
  GATE: [count]
  HIGH: [count]
  MEDIUM: [count]

Layers: [list]
Simulations: [list, or "None"]
Manual-only: [count, or "None"]
Gaps: [count, or "None"]
```

**Stop. User reviews before `/qa_plan_ux`.**

---

## Rules

1. **All data from the catalog.** Every test references a dataset by name. No inline values.
2. **Traces to source.** Every test → spec section or UX doc step.
3. **GATE first.** Dead system = stop.
4. **Side effects verified.** 200 OK ≠ proof. Check DB/file/queue.
5. **Failure = no side effects.** Verify nothing changed.
6. **Claude Code picks tools.** You define what and expected. Not how.
7. **Test data stored separately.** `/qa_plan_ux` needs it.
8. **One plan per MVP.**

---

## Self-Check

- [ ] Test data catalog covers every field from spec + UX doc?
- [ ] At least 2 valid datasets with different values?
- [ ] Every invalid dataset isolates one broken rule?
- [ ] Every test references a dataset by name?
- [ ] GATE tests exist and run first?
- [ ] At least one test proves MVP acceptance?
- [ ] Every write-path test verifies side effects?
- [ ] Every failure test verifies no side effects?
- [ ] Test data stored as separate file?
- [ ] Could Claude Code run this without asking a question?