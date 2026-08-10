# MD ASCII Diagram Rules

Rules for writing Markdown files with ASCII diagrams that survive conversion
to `.docx` / Google Docs without breaking alignment.

**Scope:** any `.md` file containing fenced code blocks with ASCII art
(architecture diagrams, flowcharts, boxes, trees).

---

## Hard rules (must follow)

### R1. Wrap every diagram in a fenced code block tagged `text`
```text
+--------+
|  Box   |
+--------+
```
- Triggers monospace rendering in converters.
- The `text` tag prevents syntax highlighters from mangling the content.

### R2. Use ONE character set per file. Pick one and stick with it.
- **Option A — Pure ASCII:** `+ - | > < * v ^`  (most portable)
- **Option B — Box Drawing Unicode:** `┌ ┐ └ ┘ ─ │ ├ ┤ ┬ ┴ ┼` (prettier)

Never mix `+--+` ASCII boxes with `┌─┐` Unicode boxes in the same file.

### R3. NEVER use `--` (double dash) inside a diagram
Word AutoCorrect converts `--` → `—` (em dash), which shrinks that line by
one character and breaks the right-edge alignment.

- Use `-` (single dash), `:`, or ` - ` instead.
- Applies to labels, separators, comments — anywhere inside the fence.

### R4. Avoid all AutoCorrect-trigger sequences inside diagrams

| Forbidden     | Word converts to       | Use instead       |
|---------------|------------------------|-------------------|
| `--`          | `—` (em dash)          | `-` or `:`        |
| `'text'`      | `'text'` (curly)       | `"text"` or plain |
| `(c) (r) (tm)`| `© ® ™`                | `c`, `r`, `tm`    |
| `1st 2nd 3rd` | superscript            | `1`, `2`, `3`     |
| `http://...`  | auto-hyperlink         | drop the protocol |

### R5. Spaces only — never tabs
Tabs render at unpredictable widths. Configure editor to insert spaces.

### R6. ASCII arrows, not Unicode arrows
- **Use:** `->`, `<-`, `v`, `^`, `<->`
- **Avoid:** `→ ← ▶ ◀ ⇒ ⇐ ↑ ↓`

Even in Box Drawing files, use ASCII arrows. Unicode arrows live in a
different Unicode block with inconsistent widths.

---

## Soft rules (strongly recommended)

### R7. Keep diagram lines under 80 columns
Prevents wrapping in default converter settings. Hard cap: 90.

### R8. Pad lines to equal length within a diagram
```text
Bad:                          Good:
+------+                      +------+
| User | -> +------+          | User | -> +------+
+------+    | API  |          +------+    | API  |
            +------+                      +------+
```
Resists trim-and-reflow in aggressive converters.

### R9. Add a conversion-instruction blockquote at the top of the file
```markdown
> **Conversion note:** Render with `pandoc --wrap=preserve` plus a
> monospace reference template. Default converters may reflow the
> ASCII diagrams below.
```

### R10. One diagram = one fenced block
Don't merge unrelated diagrams. Easier to edit and debug.

---

## Style rules (consistency)

### R11. Standard box style (ASCII option)
```text
+--------+      Top/bottom: + and -
|  Text  |      Sides:      |
+--------+      Corners:    +
```

### R12. Standard arrow style
- Horizontal: `->` or `<-`
- Vertical:   `|` with `v` or `^` at the end
- Bidirectional: `<->`

### R13. Long labels go beside the box, not inside
```text
Bad:                          Good:
+--------------------+        Service A
| Long Service Name  |        +-----+
| with description   |        |     |
+--------------------+        +-----+
```

### R14. One-space padding minimum inside boxes
`| Text |` not `|Text|`.

---

## Anti-rules (do NOT do)

- **A1.** No HTML (`<pre>`, `<div>`, font tags) — not portable, ugly source.
- **A2.** No Mermaid if the requirement is editable ASCII.
- **A3.** No NBSP (`\u00A0`) for padding — invisible chars break future edits.
- **A4.** No tables as diagram substitutes — stops being a diagram.
- **A5.** No pre-processing scripts (sed, etc.) — rules live in the MD itself.
- **A6.** No mixing ASCII and Unicode box chars in the same file.

---

## Validation checklist (before committing)

```text
[ ] Every diagram inside ```text fence
[ ] No `--` anywhere inside fences
[ ] No curly quotes, ©, ®, ™, em dashes
[ ] No tabs (only spaces)
[ ] All lines under 80 columns
[ ] One char set used (ASCII OR Box Drawing)
[ ] ASCII arrows only (-> not →)
[ ] Test convert: pandoc file.md -o /tmp/test.docx
[ ] Open test.docx, spot-check 2-3 diagrams
```

---

## Minimum viable rule set

If you only remember 5 rules:

1. ` ```text ` fence around every diagram
2. Pick ASCII (`+ - |`) OR Box Drawing (`┌ ─ │`) — never both
3. NO `--` inside diagrams (em dash trap)
4. ASCII arrows only: `->` not `→`
5. Spaces, not tabs

---

## Why these rules exist

ASCII art breaks in `.docx` because:
1. Word's default font (Calibri) is **proportional** — chars have different widths
2. Word AutoCorrect silently rewrites `--`, `'...'`, `(c)`, etc.
3. Default Pandoc reflows long lines unless told otherwise

These rules attack all three at the source — in the MD file — so the output
is robust regardless of which converter or template the reader uses.
