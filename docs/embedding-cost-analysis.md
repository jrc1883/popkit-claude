# PopKit Cloud: Embedding Cost Analysis

**Part of Issue #70 - Embedding-Enhanced Check-ins**

## Voyage AI Pricing

We use `voyage-3-lite` model for insights (cheaper than full voyage-3):

| Model | Dimensions | Cost per 1M tokens |
|-------|------------|-------------------|
| voyage-3 | 1024 | $0.06 |
| voyage-3-lite | 512 | $0.02 |
| voyage-code-3 | 1024 | $0.06 |

**Free Tier**: 50M tokens/month (worth ~$1 on voyage-3-lite)

## Token Usage Per Insight

Based on testing:
- Average insight: ~15 tokens
- Query for search: ~5 tokens

## Usage Scenarios

### Light User (Solo Developer)
- 10 Power Mode sessions/month
- 5 insights per session
- 3 searches per session

**Monthly usage:**
- Insights: 10 × 5 × 15 = 750 tokens
- Searches: 10 × 3 × 5 = 150 tokens
- **Total: ~900 tokens**
- **Cost: $0.000018 (~$0.00)**

### Medium User (Active Developer)
- 50 Power Mode sessions/month
- 10 insights per session
- 10 searches per session

**Monthly usage:**
- Insights: 50 × 10 × 15 = 7,500 tokens
- Searches: 50 × 10 × 5 = 2,500 tokens
- **Total: ~10,000 tokens**
- **Cost: $0.0002 (~$0.00)**

### Heavy User (Team Lead / Power User)
- 200 Power Mode sessions/month
- 20 insights per session
- 20 searches per session

**Monthly usage:**
- Insights: 200 × 20 × 15 = 60,000 tokens
- Searches: 200 × 20 × 5 = 20,000 tokens
- **Total: ~80,000 tokens**
- **Cost: $0.0016 (~$0.00)**

### Team (10 Heavy Users)
- 800,000 tokens/month
- **Cost: $0.016/month**

## Scaling Analysis

| Users | Sessions/mo | Tokens/mo | Cost/mo |
|-------|-------------|-----------|---------|
| 100 | 5,000 | 5M | $0.10 |
| 1,000 | 50,000 | 50M | $1.00 |
| 10,000 | 500,000 | 500M | $10.00 |
| 100,000 | 5M | 5B | $100.00 |

## Free Tier Impact

Voyage free tier: 50M tokens/month

This covers:
- **~5,000 active users** at light usage
- **~500 active users** at medium usage
- **~60 active users** at heavy usage

## Sustainability Model

### Option 1: Absorb Cost (Recommended Initially)
At <1000 users, cost is negligible ($1-10/month)

### Option 2: Pass Through (Pro/Team Tiers)
Include in Pro ($9/mo) and Team ($29/mo) pricing:
- Pro: ~$0.10 embedding cost margin
- Team: ~$1.00 embedding cost margin

### Option 3: Metered (Future)
Track per-user embedding usage:
- Free: 10K tokens/month
- Pro: 100K tokens/month
- Team: 1M tokens/month

## Recommendation

**Absorb costs initially** - embeddings are nearly free:
- 10,000 users × medium usage = $10/month
- This is less than a cup of coffee

**Monitor usage** via the `/embeddings/usage` endpoint.

**Consider metering** only if:
- Costs exceed $100/month
- Individual users abuse the system (>1M tokens)

## Implementation Notes

1. **Deduplication saves money** - 0.90 threshold prevents redundant embeddings
2. **voyage-3-lite is sufficient** - 512 dimensions works well for insights
3. **Batch where possible** - reduces API calls
4. **Cache embeddings** - never re-embed the same content

## Cost Tracking

The cloud API tracks:
```
GET /v1/embeddings/usage

{
  "today": {
    "tokens": 54,
    "requests": 4,
    "cost": 0.000001
  },
  "total_insights": 4,
  "model": "voyage-3-lite",
  "dimensions": 512
}
```

Monitor this to validate assumptions.

---

**Conclusion**: Embedding costs are negligible (~$0.00-0.01/user/month). Safe to include in all tiers with no metering initially.
