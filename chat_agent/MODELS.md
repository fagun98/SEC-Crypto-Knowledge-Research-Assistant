# Chat agent model roles

| Role | Default model | Env override |
|------|---------------|--------------|
| Answer / synthesis (brain) | `gpt-5.4-mini` | `CHAT_BRAIN_MODEL`, `OPENAI_LLM_MODEL` |
| Query ontology classification | `gpt-5.4-nano` | `CRI_QUERY_CLASSIFIER_MODEL`, `CHAT_NANO_MODEL` |
| Chunk rerank | `gpt-5.4-nano` | `CHAT_RERANK_MODEL`, `CHAT_NANO_MODEL` |
| Ingest chunk classification | `gpt-5.4-nano` | `CRI_CLASSIFIER_MODEL` |

OpenAI positions **GPT-5.4 mini** for coding, sub-agents, and stronger mini-tier reasoning; **GPT-5.4 nano** for classification, extraction, ranking, and other simple high-volume tasks ([model guide](https://developers.openai.com/api/docs/models/gpt-5.4-nano)).

## API pricing (per 1M tokens, standard tier)

Sources: [OpenAI API pricing](https://openai.com/api/pricing/), [GPT-5.4 nano](https://developers.openai.com/api/docs/models/gpt-5.4-nano), [GPT-5 mini](https://developers.openai.com/api/docs/models/gpt-5-mini) — verify on the pricing page before budgeting.

| Model | Input | Cached input | Output |
|-------|------:|-------------:|-------:|
| **gpt-5.4-mini** | $0.75 | $0.075 | $4.50 |
| **gpt-5.4-nano** | $0.20 | $0.02 | $1.25 |
| **gpt-5-mini** | $0.25 | $0.025 | $2.00 |
| **gpt-5-nano** | $0.05 | $0.005 | $0.40 |

Batch API is **50% off** input and output for eligible endpoints.

## Cost comparison (example workloads)

### A) One chat turn (rough order of magnitude)

Assume: query classify ~2K in / 400 out; rerank ~6K in / 800 out; answer ~12K in / 2K out.

| Step | Model | Est. cost |
|------|-------|----------:|
| Classify query | gpt-5.4-nano | ~$0.0009 |
| Rerank ~20 chunks | gpt-5.4-nano | ~$0.0022 |
| HTML answer | gpt-5.4-mini | ~$0.018 |
| **Total (5.4 mini + nano)** | | **~$0.021** |

Same turn if everything used **gpt-5-mini**:

| Step | Est. cost |
|------|----------:|
| Classify + rerank + answer on gpt-5-mini | **~$0.009** |

5.4-mini brain is **more expensive per token** than gpt-5-mini on output ($4.50 vs $2.00 / 1M), but nano steps are cheaper than using mini for classify/rerank. Net: **use nano for classify/rerank, mini only for the final answer** — typically best cost/quality for this pipeline.

### B) 1M input + 200K output (single call)

| Model | Input $ | Output $ | **Total** |
|-------|--------:|---------:|----------:|
| gpt-5.4-mini | 0.75 | 0.90 | **$1.65** |
| gpt-5.4-nano | 0.20 | 0.25 | **$0.45** |
| gpt-5-mini | 0.25 | 0.40 | **$0.65** |
| gpt-5-nano | 0.05 | 0.08 | **$0.13** |

### C) Relative to gpt-5-mini (same 1M in / 200K out)

| Model | vs gpt-5-mini total |
|-------|---------------------|
| gpt-5.4-mini | ~2.5× more expensive |
| gpt-5.4-nano | ~31% cheaper |
| gpt-5-nano | ~80% cheaper |

**gpt-5.4-mini vs gpt-5-mini:** 3× input, 2.25× output — pay more for stronger 5.4-class reasoning.  
**gpt-5.4-nano vs gpt-5-mini:** cheaper on both input and output — prefer nano for classify/rerank.  
**gpt-5.4-nano vs gpt-5-nano:** 4× input, ~3.1× output — 5.4-nano is newer/smarter; 5-nano is the lowest cost tier.

## When to use which in this repo

- **gpt-5.4-mini**: Final RAG answer, long synthesis, citation-heavy HTML.
- **gpt-5.4-nano**: `classify_query`, `rerank_chunks`, optional ingest `classify_chunk`.
- **gpt-5-mini / gpt-5-nano**: Legacy overrides only if you need lowest cost or older snapshots.
