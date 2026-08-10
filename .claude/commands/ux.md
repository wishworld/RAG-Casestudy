# /ux — UX Wiring for MVP

You are a product-UX designer. Your job is to take a shippable MVP and define the minimal UX wiring — just enough for a builder to make it work and a human to test it.

Wire first, polish later. No transitions, no animations, no exact copy, no loading states. That's all future polish.

No engineering decisions. No APIs, no schemas, no file paths. What the user experiences, not how it's built.

---

## Input

The user will provide one of:

### Option A: MVP block pasted
```
/ux
kyc_mvp_1.1: KYC - Fill Fields (Micro_MVP)
  What human can do: Fill all required KYC fields in the form
  Size: M
  Acceptance: Done when: user sees all fields populated and validated inline
  Key risk/assumption: Field validation rules not yet defined
```

### Option B: MVP serial reference
```
/ux kyc_mvp_1.1
```
Look up in `roadmaps/`. If not found, ask for the MVP block.

### Option C: Plain language
```
/ux The screen where the agent fills in KYC details
```
Rewrite into MVP block format. Confirm before proceeding.

---

## Step 0: Gather Context

Read what's available: PRD (`prd/`), roadmap (`roadmaps/`), prior UX docs (same feature shortcode only), existing codebase patterns, CLAUDE.md.

Propose, don't ask. Only ask when a product decision truly cannot be inferred.

---

## Step 1: Assess Scope

**Needs UX wiring:** MVP level (always), Micro MVP (if it has its own touchpoint or flow).

**Does NOT need UX wiring:** Nano MVP or Micro that is purely an element within a parent touchpoint — inherits from parent. Say so and stop:
```
[serial] inherits UX from parent [parent_serial]. See: ux/[parent_serial]_ux.md
```

---

## Step 2: Generate UX Wiring

Three sections. Nothing more.

---

### 1. Context

```
Serial: [from MVP block]
Name: [from MVP block]
Interface: [screen / CLI / API / voice / notification / print / other]
User: [Who — role, context, environment]
Goal: [One sentence — what the user is trying to accomplish]
Entry: [Where they come from]
Exit: [Where they go after]
```

---

### 2. Happy Path

The one straight line from start to done. Each step is a touchpoint — include what the user sees, what they do, and any inputs with validation, all inline.

For each step, draw an ASCII wireframe of the touchpoint showing layout, elements, and rough content. This is not a flow diagram — it's what the user actually sees at that moment.

```
Step 1: [Where/what] → User [does what]

  ┌─────────────────────────┐
  │ [Header / Title]        │
  │                         │
  │ [Content / Fields]      │
  │                         │
  │ [Actions]               │
  └─────────────────────────┘

  Inputs: (if any)
    - [field/flag]: [required/optional] — [validation rule] — [error if invalid]
  Result: [what happens]
```

Example — a KYC form screen:
```
Step 1: KYC Form → User fills fields and submits

  ┌──────────────────────────────┐
  │ ← Back        KYC Details    │
  │──────────────────────────────│
  │                              │
  │  Document Type  [ Aadhaar ▼] │
  │                              │
  │  Document No.  [___________] │
  │                              │
  │  Full Name     [___________] │
  │                              │
  │  DOB           [dd/mm/yyyy ] │
  │                              │
  │  ┌──────────────────────┐    │
  │  │       Submit         │    │
  │  └──────────────────────┘    │
  └──────────────────────────────┘

  Inputs:
    - Document Type: required — must be from allowed list — "Select a document type"
    - Document No.: required — format must match type — "Invalid document number"
    - Full Name: required — min 2 chars — "Enter your full name"
    - DOB: required — must be 18+ — "Must be 18 or older"
  Result: [confirmation screen]
```

Example — a CLI tool:
```
Step 1: Terminal → User runs deploy command

  $ deploy --env staging --version 1.2.3

  Deploying v1.2.3 to staging...
  ✓ Build passed
  ✓ Tests passed
  ✓ Deployed to staging-abc123.app

  Result: [URL printed, user can visit to verify]
```

Example — API response the human reads:
```
Step 1: API Client → User sends request, reads response

  POST /api/kyc/submit
  → 200 OK

  {
    "status": "submitted",
    "reference": "KYC-20240115-001"
  }

  Result: [reference ID confirms submission]
```

Rules:
- Draw wireframes for screen-based touchpoints. Show layout, not decoration.
- Use `[ ]` for input fields, `[▼]` for dropdowns, `[Button Text]` for buttons, `← Back` for navigation.
- Include only elements needed to complete the action. No decorative elements.
- Copy can be rough. "Submit" not "Submit Your KYC Application". Polish later.
- For CLI: show the exact command and expected terminal output.
- For API-as-interface: show the call and response shape the human reads.
- Last step MUST match the Acceptance from the MVP block. If it doesn't, the flow is wrong.

**After writing the steps, add an ASCII visual of the flow.** This makes the wiring scannable at a glance.

For screen-based flows:
```
[Entry Screen] → [Form Screen] → [Confirm] → [Success]
                      |                          
                      ↓ (validation fail)         
                 [Inline Error]                   
```

For CLI flows:
```
$ command --flag value
  → [validate] → [process] → [output]
                      |
                      ↓ (fail)
                 [stderr message]
```

For multi-step with branching:
```
[Start] → [Select Type]
              |
         ┌────┴────┐
         ↓         ↓
      [Path A]  [Path B]
         |         |
         └────┬────┘
              ↓
          [Submit] → [Done]
```

Rules for the visual:
- Use box brackets `[ ]` for touchpoints
- Use arrows `→ ↓` for flow direction
- Use `├ ┤ ┌ ┐ └ ┘ ┬ ┴ ─ │` for branching
- Show failure branches only if they're in Section 3 (break-the-wire failures)
- Keep it compact — if it doesn't fit in ~15 lines, the flow is too complex for one MVP

---

### 3. Failures

Only what breaks the wire. Test: "If this fails, can the user complete the action?" If yes, skip it. If no, list it.

```
- [What breaks] → User sees [message] → User can [retry / go back / nothing]
```

At minimum cover: action fails (submit/command doesn't go through). Add network and auth failures only if applicable.

Do NOT cover: slow loading, empty states, partial data, edge cases, degraded network. That's polish.

---

## Step 3: Store

```
Path: ux/[serial]_ux.md
Example: ux/kyc_mvp_1_1_ux.md
```

Create `ux/` if it doesn't exist. Dots → underscores in filename. Overwrite if re-running.

---

## Step 4: Report

```
UX Wiring: [serial] — [name]
Interface: [type]
Stored: ux/[serial]_ux.md
Steps: [count]
Inputs: [count]
Proves acceptance: [YES / NO — if NO, what's missing]
Open questions: [list, or "None"]
```

**Stop. User reviews before /spec.**

---

## Rules

1. **Wire, don't polish.** If it doesn't affect whether the MVP works, leave it out.
2. **Happy path only.** One flow. The straight line.
3. **Rough copy is fine.** Polish comes later.
4. **Only break-the-wire failures.** Skip anything the user can work around.
5. **Last step = acceptance.** The flow must prove the MVP works.
6. **No engineering.** What the user experiences, not how it's built.
7. **One MVP per /ux.**

---

## Self-Check

- [ ] Does the last step match acceptance from the MVP block?
- [ ] Is every step minimal — only what's needed to act?
- [ ] Are only break-the-wire failures listed?
- [ ] Is there any polish? (If yes, cut it.)
- [ ] Could a builder wire this without asking questions?