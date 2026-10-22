# Model Tier Routing — Essentials

Không phải mọi agent cần model mạnh nhất. Match model capability với task complexity → tối ưu cost + quality.

## Model tier mapping

Claude family (có thể adapt cho other providers):

| Tier | Model (Claude) | Use case | Cost ratio |
|---|---|---|---|
| **lite** | Haiku 4.5 | Classification, routing, simple decision | 1x |
| **balanced** | Sonnet 4.6 | Implementation, test writing, code review bình thường | 3-4x |
| **deep** | Opus 4.7 | Spec decomposition, architecture, critical review | 10-15x |

## Default routing

| Role | Tier default | Rationale |
|---|---|---|
| `architect` | deep (opus) | Decomposition + decisions critical |
| `orchestrator` | balanced (sonnet) | Coordinate + routing |
| `implementer` | balanced (sonnet) | Code implementation standard |
| `qa` | balanced (sonnet) | Test writing + assertion review |
| `reviewer` | deep (opus) | Independent audit — depth matter |
| `debugger` | balanced (sonnet) → deep if stuck | Logic trace |
| `classifier` | lite (haiku) | Fast triage |
| `script runner` | — (no model) | Gradle/scripts không cần AI |

## Decision criteria

### Chọn **deep** (opus) khi:
- Design decision irreversible (public API, DB schema, architecture)
- Spec ambiguous cần nhiều interpretation
- Review critical path (auth, payment, migration)
- Debug concurrency bug subtle
- Multiple hypothesis cần evaluate parallel

### Chọn **balanced** (sonnet) khi:
- Implementation theo plan rõ
- Test write theo contract
- Code review standard
- Refactor preserve-behavior
- Routine bugfix với cause rõ

### Chọn **lite** (haiku) khi:
- Task classification (feature vs bugfix vs refactor)
- Routing decision (team vs single vs parallel)
- Simple validation (schema check, format)
- Metadata extract (parse spec header)

### Chọn **no model** (script) khi:
- Gradle run (`./gradlew ...`)
- Git operations (`git status`, `git diff`)
- File manipulation (format, lint auto-fix)
- CI steps (build artifact, upload)
- Verification gate chạy

## Config

### Overlay default

```yaml
# overlay.yaml
orchestration:
  model_tier:
    default:
      architect: deep
      orchestrator: balanced
      implementer: balanced
      test_engineer: balanced
      reviewer: deep
      debugger: balanced
      classifier: lite
```

### Task-level override

```yaml
# plans/FEAT-104.yaml
model_tier:
  implementer: lite        # Budget mode cho task simple
  reviewer: deep           # Keep reviewer quality
```

## Agent prompt — tier hint

Khi spawn subagent, pass tier hint trong `Task()`:

```python
Task(
    subagent_type="general-purpose",
    description="...",
    prompt=f"""
    [Tier: deep]
    You are reviewer agent. Audit critical path.
    ...
    """,
    # Model selection platform-dependent (Claude Code auto)
)
```

Claude Code (Opus 4.7) tự chọn model based on task complexity. User không control model explicit; harness document tier intent → agent runtime adapt.

## Cost estimation per task

Example feature task:

| Phase | Role | Tier | Est. tokens | Cost multiplier |
|---|---|---|---|---|
| Classification | classifier | lite | 500 | 1x |
| Decomposition | architect | deep | 3,000 | 10x |
| Implementation | implementer | balanced | 8,000 | 3x |
| Test writing | qa | balanced | 2,000 | 3x |
| Review | reviewer | deep | 4,000 | 10x |
| **Total** | | | 17,500 | — |

Total cost ≈ 17.5k × ~$3/M tokens = **$0.05** per feature (rough estimate, varies theo provider pricing).

## Trade-offs

### Pros tier routing

- Cost giảm 30-50% so với "all opus"
- Latency giảm (lite model faster)
- Classification quyết định nhanh

### Cons tier routing

- **Over-tier**: dùng lite cho task complex → wrong output, phải retry
- **Under-tier**: dùng opus cho task trivial → waste
- Tier override add complexity cho user
- Claude Code có thể auto-pick, override khó enforce

### Khi KHÔNG tier routing

- Project nhỏ, 1 model đủ fast
- User không muốn config
- Provider không hỗ trợ multi-tier (Haiku unavailable)

## Multi-provider consideration

Nếu dùng Codex / Gemini / local LLM:

| Provider | Lite equivalent | Balanced | Deep |
|---|---|---|---|
| Anthropic | Haiku | Sonnet | Opus |
| OpenAI | GPT-4o-mini | GPT-4o | o1 |
| Google | Gemini Flash | Gemini Pro | Gemini Ultra |
| Local (via Ollama) | Llama 8B | Mistral/Qwen 32B | — |

Harness document tier intent agnostic; agent runtime map tới actual model.

## Monitoring (Phase 3)

Dashboard track:
- Cost per tier (daily/weekly)
- Task success rate per tier
- Escalation rate (lite → balanced → deep)
- ROI tier routing vs flat opus

## Common mistakes

| Mistake | Fix |
|---|---|
| Dùng opus cho mọi task | Enable tier routing, measure |
| Dùng haiku cho architect decomposition | Deep tier mandatory cho design decision |
| Reviewer tier balanced → miss subtle issue | Keep reviewer tier deep |
| Classifier tier balanced → waste | Lite đủ cho triage |
| Over-override giữa chừng task | Set tier ở start task, không mid-way change |

## References

- `knowledge/agent-orchestration/essentials.md` — mode routing (orthogonal với tier)
- `agents/*.md` — role mindset (tier-agnostic)
- Provider pricing docs (external)
- `blueprints/task-contract/template.yaml §model_tier`
