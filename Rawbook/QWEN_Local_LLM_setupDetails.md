# QWEN Local LLM - Setup Details

> **Conversion note:** Render with `pandoc --wrap=preserve` plus a
> monospace reference template. Default converters may reflow the
> ASCII diagrams below.

Local LLM environment: Ollama + qwen2.5:7b on Apple Silicon.
Everything runs on-device. No data leaves the machine.

**Verified:** 2026-08-11

---

## 1. Summary

| Item | Value |
|------|-------|
| Runtime | Ollama 0.32.6 (official macOS app) |
| Model | qwen2.5:7b |
| Model size on disk | 4.7 GB |
| Acceleration | 100% Apple GPU (Metal) |
| Measured speed | ~22 tokens/sec |
| Local API | http://localhost:11434 |
| OpenAI-compatible API | http://localhost:11434/v1 |
| Data privacy | fully local, works offline |

---

## 2. Architecture

```text
+---------------------------------------------------------------+
|                    YOUR MAC (Apple M4)                        |
|                                                               |
|  +----------------+       +--------------------------------+  |
|  | Ollama.app     |       | Ollama server                  |  |
|  | GUI chat       |   ->  | localhost:11434                |  |
|  | menu bar icon  |       |                                |  |
|  +----------------+       |  +--------------------------+  |  |
|                           |  | llama-server (runner)    |  |  |
|  +----------------+       |  | qwen2.5:7b -> Metal GPU  |  |  |
|  | Terminal CLI   |   ->  |  +--------------------------+  |  |
|  | ollama run     |       |                                |  |
|  +----------------+       +--------------------------------+  |
|                                    ^                          |
|  +----------------+                |                          |
|  | Your code      |   -------------+                          |
|  | Python / curl  |   HTTP JSON                               |
|  +----------------+                                           |
+---------------------------------------------------------------+

   No outbound network calls. Inference is on-device.
```

---

## 3. Hardware

| Component | Spec |
|-----------|------|
| Chip | Apple M4 |
| CPU cores | 10 (4 performance + 6 efficiency) |
| GPU cores | 8 |
| Memory | 16 GB unified |
| macOS | 26.3 |

**Why unified memory matters:** CPU and GPU share one memory pool, so
model weights need no copying between them. This is why a 7B model runs
well on a laptop.

---

## 4. Model specification

| Property | Value |
|----------|-------|
| Name | qwen2.5:7b |
| ID | 845dbda0ea48 |
| Architecture | qwen2 |
| Parameters | 7.6 B |
| Quantization | Q4_K_M (4-bit) |
| Native context length | 32768 tokens |
| Running context | 4096 tokens (Ollama default) |
| Embedding length | 3584 |
| Capabilities | completion, tool calling |
| License | Apache 2.0 |

**Quantization explained:** the full model is ~15 GB at 16-bit precision.
Q4_K_M compresses weights to 4-bit, giving 4.7 GB with minor quality
loss. This is what makes it fit in 16 GB alongside normal apps.

---

## 5. Installed paths

```text
/Applications/Ollama.app                 GUI app (560 MB)
/usr/local/bin/ollama                    CLI symlink
~/.ollama/models                         model storage (4.4 GB)
~/Library/LaunchAgents/
    com.user.ollama-env.plist            settings persistence
```

---

## 6. Settings applied

| Variable | Value | Effect |
|----------|-------|--------|
| `OLLAMA_KEEP_ALIVE` | `60s` | unload model 60s after last use |
| `OLLAMA_MAX_LOADED_MODELS` | `1` | prevent two models in RAM at once |

Set via `launchctl setenv`, made permanent by a LaunchAgent at
`~/Library/LaunchAgents/com.user.ollama-env.plist` (runs at every login).

**Verify after reboot:**

```bash
launchctl getenv OLLAMA_KEEP_ALIVE      # expect: 60s
```

**If the value is empty after a reboot,** quit and reopen Ollama once.
This happens if Ollama launches before the LaunchAgent runs.

**To remove persistence:**

```bash
launchctl unload ~/Library/LaunchAgents/com.user.ollama-env.plist
rm ~/Library/LaunchAgents/com.user.ollama-env.plist
```

---

## 7. Memory behaviour

```text
IDLE (no chat for 60+ seconds)
+---------------------------------+
| Ollama app UI          0.46 GB  |
| Model in RAM           0    GB  |   <- unloaded automatically
+---------------------------------+

ACTIVE (during and just after a chat)
+---------------------------------+
| Ollama app UI          0.46 GB  |
| Model weights          4.2  GB  |
| KV cache (context)     0.5  GB  |
+---------------------------------+
| Total                  ~5.2 GB  |
+---------------------------------+
```

The KV cache holds the running conversation. It is created when the model
loads and destroyed when it unloads - it never persists.

Reload after unload takes about 1 second.

**Free memory immediately:**

```bash
ollama stop qwen2.5:7b
```

---

## 8. Command reference

| Task | Command |
|------|---------|
| Open GUI | `open -a Ollama` |
| Chat in terminal | `ollama run qwen2.5:7b` |
| One-shot prompt | `ollama run qwen2.5:7b "your question"` |
| List installed models | `ollama list` |
| Show what is loaded | `ollama ps` |
| Unload model (free RAM) | `ollama stop qwen2.5:7b` |
| Delete model from disk | `ollama rm qwen2.5:7b` |
| Download a model | `ollama pull <model-name>` |
| Model details | `ollama show qwen2.5:7b` |
| Exit interactive chat | `/bye` |
| Update Ollama | menu bar icon -> Restart to update |

There is no `ollama update` command. The app self-updates.

---

## 9. GUI chat

```text
+---------------------------------------------------------------+
| 1. Click the llama icon in the menu bar (top right)            |
| 2. Chat window opens                                           |
| 3. Model dropdown at top -> select  qwen2.5:7b                 |
| 4. Type at the bottom -> press Enter                           |
+---------------------------------------------------------------+
```

If the window does not appear, run `open -a Ollama`.

---

## 10. API - three endpoints

All three serve the same model on the same port.

```text
+--------------------------+-------------------------------------+
| /api/generate            | native, single prompt               |
| /api/chat                | native, multi-turn conversation     |
| /v1/chat/completions     | OpenAI-compatible drop-in           |
+--------------------------+-------------------------------------+
```

### 10.1 Native - single prompt

```bash
curl http://localhost:11434/api/generate -d '{
  "model": "qwen2.5:7b",
  "prompt": "Name one benefit of local LLMs in fintech.",
  "stream": false
}'
```

Read the answer from: `.response`

### 10.2 Native - conversation with system prompt

```bash
curl http://localhost:11434/api/chat -d '{
  "model": "qwen2.5:7b",
  "messages": [
    {"role": "system", "content": "You are a concise fintech analyst."},
    {"role": "user", "content": "What is an Account Aggregator?"}
  ],
  "stream": false
}'
```

Read the answer from: `.message.content`

### 10.3 OpenAI-compatible

```bash
curl http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen2.5:7b",
    "messages": [{"role": "user", "content": "Your question"}],
    "stream": false
  }'
```

Read the answer from: `.choices[0].message.content`

### 10.4 Utility endpoints

```bash
curl http://localhost:11434/api/version    # server version
curl http://localhost:11434/api/tags       # installed models
curl http://localhost:11434/api/ps         # currently loaded models
```

---

## 11. Python

### 11.1 Using the openai library (recommended)

```python
# pip install openai
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama"          # required by the library, ignored by Ollama
)

resp = client.chat.completions.create(
    model="qwen2.5:7b",
    messages=[{"role": "user", "content": "Explain UPI in two lines."}]
)
print(resp.choices[0].message.content)
```

**Why this approach:** any code written for OpenAI works by changing two
lines - `base_url` and `api_key`. The same applies to LangChain,
LlamaIndex and most agent frameworks. This gives a clean swap between
local and hosted models later.

### 11.2 Plain requests, no dependencies

```python
import requests

r = requests.post("http://localhost:11434/api/chat", json={
    "model": "qwen2.5:7b",
    "messages": [{"role": "user", "content": "Explain UPI in two lines."}],
    "stream": False
})
print(r.json()["message"]["content"])
```

---

## 12. Request parameters

| Parameter | Purpose |
|-----------|---------|
| `"stream": true` | tokens arrive as generated instead of all at once |
| `"options": {"temperature": 0}` | deterministic output (default 0.8) |
| `"options": {"num_ctx": 8192}` | override context window for this call |
| `"keep_alive": "0"` | unload immediately after this request |
| `"keep_alive": "-1"` | keep loaded indefinitely |
| `"format": "json"` | force valid JSON output |

### Example: deterministic JSON output

```bash
curl http://localhost:11434/api/generate -d '{
  "model": "qwen2.5:7b",
  "prompt": "List 2 KYC risks as a JSON array",
  "format": "json",
  "options": {"temperature": 0},
  "keep_alive": "0",
  "stream": false
}'
```

**Why temperature 0 matters for evaluation:** the same input produces the
same output every time. This lets you measure your pipeline instead of
measuring random sampling variation.

---

## 13. Health check

Run these to confirm everything works:

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:11434/   # 200
ollama list                                                       # qwen2.5:7b
ollama ps                                                         # shows GPU
```

Expected `ollama ps` output while a model is loaded:

```text
NAME         ID            SIZE     PROCESSOR   CONTEXT   UNTIL
qwen2.5:7b   845dbda0ea48  4.7 GB   100% GPU    4096      59 seconds from now
```

**`PROCESSOR` must read `100% GPU`.** Anything showing CPU means the model
is not fully offloaded to Metal and will run roughly 4x slower.

---

## 14. Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Connection refused on 11434 | server not running | `open -a Ollama` |
| `ollama` command not found | CLI symlink missing | reopen Ollama.app once |
| `ollama ps` shows CPU, not GPU | model too large for VRAM | close other apps, retry |
| Very slow responses | swapping to disk | `ollama stop`, close Chrome |
| Keep-alive back to 5m after reboot | Ollama started before LaunchAgent | quit and reopen Ollama |
| Model missing from GUI dropdown | GUI opened before pull finished | restart Ollama.app |

---

## 15. Why local, for the case study

| Dimension | Local (qwen2.5:7b) | Hosted API |
|-----------|--------------------|------------|
| Data leaves device | never | yes |
| Works offline | yes | no |
| Cost per call | zero | metered |
| Latency | ~22 tok/s | network dependent |
| Capability | modest (7B) | frontier |
| Audit story | full control | vendor dependent |

For regulated fintech work, the "data leaves device" row is the reason
this setup exists. It supports demonstrations where customer PII, data
residency, or auditability rule out sending data to a third party.

---

## 16. Not installed (deliberately out of scope)

```text
[ ] Docker              not needed - would block GPU access on macOS
[ ] Open WebUI          not needed - Ollama has a native GUI
[ ] Embedding models    deferred until RAG work begins
[ ] Vector database     deferred until RAG work begins
[ ] LangChain / Chroma  deferred until RAG work begins
[ ] PostgreSQL          pending - planned as native install + pgvector
```

**Note on Docker:** containers on macOS run inside a Linux VM with no
access to the Apple GPU. Running Ollama in Docker would force CPU-only
inference at roughly a quarter of the speed. Native install is correct
here. Docker remains a reasonable choice later for a vector database,
which needs no GPU.
