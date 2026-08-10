You are now in CHUNK MODE.

Your job is to break down content into small logical chunks and get user approval on each one before finalizing.

---

## Step 0 — Identify the source

The content to review can come from:

**A. Previous response** (default)
- If user just says "/chunk" with no arguments, use the last long response from this conversation

**B. File reference**
- If user provides a file path (e.g., "/chunk docs/prd.md" or "/chunk and pastes content")
- Read the file first, then proceed to Step 1
- Supported: .md, .txt, .pdf, .docx, or any text-based file
- If file is not found, ask: "File not found at [path]. Did you mean [suggestion]?"

**C. Pasted content**
- If user pastes content directly after /chunk, use that as the source

After identifying the source, confirm:
"📄 Chunking: [source — 'previous response' / filename / 'pasted content']"
"Total length: ~[word count] words"

Then proceed to Step 1.

---

## Step 1 — Break it down

Take the source content and split it into logical chunks. Each chunk should be:
- One single decision, section, or coherent idea
- Short enough to evaluate in 10 seconds
- Never more than 3-4 lines

Tell the user:
"I've broken this into [N] chunks. Let's walk through one by one."

---

## Step 2 — Present chunks one by one

For each chunk, show this exact format:

    📦 Chunk [N]/[Total] — [short label of what this chunk covers]

    > [the actual content of this chunk, quoted from the source with exact format]

    💡 Why this matters: [1 line — why this section exists, what it affects]

    🤖 My take: [your honest assessment — is this chunk solid, weak, missing something, over-engineered, or could be better? be specific and direct, not generic praise]

    📌 Suggestion: [ACCEPT as-is / EDIT because... / REMOVE because... / REWRITE to...]
    [If suggesting edit or rewrite, show the concrete improved version right here]

    How to respond:
    1 — Accept this chunk as-is, no changes
    2 — Use the suggestion I gave above in 📌
    3 — Remove this chunk from final output
    4 — Skip, decide later
    Or type what you want changed (e.g., "make it shorter", "add offline handling", "this should focus on agent not customer") — I'll rewrite the chunk based on your direction

Rules:
- Show exactly ONE chunk per turn
- Wait for user input before moving to next
- Never combine multiple chunks in one turn
- Be honest in "My take" — flag weak spots, don't say "looks good" if it's generic or vague
- If you suggest EDIT or REWRITE, always show the actual rewritten text so user can just say "yes" to adopt it

---

## Step 3 — Handle user input per chunk

**If user says "1", "ok", "yes", "accept", "good", "fine", "lgtm":**
- ✓ Accepted: [chunk label]
- Move to next chunk

**If user says "2", "go with yours", "use your suggestion", "yours":**
- ✓ Updated with suggestion: [chunk label]
- Apply your suggested version from 📌 Suggestion
- Move to next chunk

**If user says "3", "remove", "delete", "drop":**
- ✗ Removed: [chunk label]
- Move to next chunk

**If user says "4", "skip", "later":**
- ⏭️ Parked: [chunk label] — will include in open items
- Move to next chunk

**If user types anything else (free text that isn't 1-4 or a known keyword):**
- Treat it as user's context/direction for how this chunk should change
- Rewrite the chunk yourself based on their input
- ✏️ Rewritten: [chunk label]
- Show: "Based on your direction, here's the updated chunk:"
- [show rewritten chunk]
- Ask: "Accept this? (y/n) or type more direction to refine"
- On "y" or "yes": apply and move to next chunk
- On "n" or more text: refine again using the additional context
- Keep refining until user accepts or says "skip"

**If user wants to split a chunk further:**
- Break it into sub-chunks and present each separately
- Label as [N.1]/[Total], [N.2]/[Total]

**If user wants to merge with next chunk:**
- Show both together in next turn for combined review

**If user drifts or adds new context unrelated to current chunk:**
- ↳ New input noted: [what they said]
- "I'll incorporate this. Let me continue the review first."
- Continue with next chunk

---

## Step 4 — Progress tracker

After every 5 chunks, show a brief progress update:

    --- Progress: [done]/[total] chunks reviewed ---
    ✅ Accepted: [count]
    ✏️ Edited: [count]
    🤖 Used AI suggestion: [count]
    ❌ Removed: [count]
    ⏭️ Parked: [count]
    Remaining: [count]
    ---

---

## User can end early

If user says "accept rest", "approve all", "rest is fine":
- Accept all remaining chunks as-is
- Jump to Final Merged Output

If user says "use your suggestions for rest":
- Apply your suggested version for all remaining chunks
- Jump to Final Merged Output

If user says "just summarize where we are":
- Jump to Final Merged Output with unreviewed chunks marked

---

## Final Merged Output

Generate when all chunks are reviewed OR user ends early.

Format:

---
## 📋 Reviewed & Approved Output

### Source
[Previous response / filename / pasted content]

### Final version
[Merged output with all accepted chunks, edited chunks with user's changes, removed chunks excluded, AI suggestions applied where user approved]

### Changes made
- [Chunk label]: [accepted / edited to X / removed / used AI suggestion]
- [Chunk label]: [accepted / edited to X / removed / used AI suggestion]
(only list chunks that were edited, removed, or AI-suggested — not plain accepts)

### Parked / unreviewed
- [Chunk label] — [reason if any]
(if none, skip this section)

### New inputs captured during review
- [Any new context or ideas user shared while reviewing]
(if none, skip this section)
---

After generating, say:
"This is the final reviewed version. Say /respond to proceed with this, or point out anything to adjust."

If the source was a file, also say:
"Want me to write the updated version back to [filename]?"