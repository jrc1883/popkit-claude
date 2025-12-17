# Efficiency Summary Output Style

Use this format to display session efficiency metrics at the end of Power Mode sessions or on-demand.

## Format

### Compact (Status Line)
```
~{tokens_saved}k tokens saved | {efficiency_score}% efficient
```

### Standard Summary
```
+==================================================================+
|                     Session Efficiency Report                     |
+==================================================================+
| Tokens Saved: ~{tokens_estimated_saved}                          |
| Efficiency Score: {efficiency_score}/100                         |
+------------------------------------------------------------------+
| Token Savings Breakdown:                                         |
|   Duplicates skipped: {duplicates_skipped} (~{dup_tokens} tokens)|
|   Pattern matches: {patterns_matched} (~{pattern_tokens} tokens) |
|   Context reuse: {context_reuse} (~{context_tokens} tokens)      |
|   Bug detection: {bugs_detected} (~{bug_tokens} tokens)          |
+------------------------------------------------------------------+
| Collaboration:                                                   |
|   Insights shared: {insights_shared}                             |
|   Insights received: {insights_received}                         |
|   Insight efficiency: {insight_efficiency}%                      |
+------------------------------------------------------------------+
| Session Stats:                                                   |
|   Tool calls: {tool_calls}                                       |
|   Avg resolution time: {avg_resolution_time}ms                   |
+==================================================================+
```

### Detailed Breakdown
```markdown
## Efficiency Report: Session {session_id}

**Overall Score: {efficiency_score}/100**
**Estimated Tokens Saved: ~{tokens_estimated_saved}**

### Token Savings

| Source | Count | Est. Tokens |
|--------|-------|-------------|
| Duplicate insights skipped | {duplicates_skipped} | ~{dup_tokens} |
| Collective patterns matched | {patterns_matched} | ~{pattern_tokens} |
| Semantic context reuse | {context_reuse} | ~{context_tokens} |
| Early bug detection | {bugs_detected} | ~{bug_tokens} |
| Stuck pattern prevention | {stuck_patterns} | ~{stuck_tokens} |

### Collaboration Metrics

- **Insights Shared:** {insights_shared}
- **Insights Received:** {insights_received}
- **Insight Efficiency:** {insight_efficiency}% (received/shared ratio)

### Power Mode (if applicable)

- **Sync Barriers:** {sync_barriers_hit}
- **Duplicate Work Prevented:** {duplicate_work_prevented}

### Interpretation

| Score | Meaning |
|-------|---------|
| 80-100 | Excellent - PopKit is providing significant value |
| 60-79 | Good - Meaningful savings from patterns and dedup |
| 40-59 | Moderate - Some benefits, consider enabling more features |
| 0-39 | Low - Try Power Mode or enable collective learning |
```

## Token Estimation Constants

These constants are used to estimate token savings:

| Event | Estimated Tokens Saved |
|-------|------------------------|
| Duplicate insight skipped | 100 tokens |
| Collective pattern matched | 500 tokens |
| Context reuse (semantic search) | 200 tokens |
| Bug detected early | 300 tokens |
| Stuck pattern prevented | 800 tokens |
| Insight content | ~0.25 tokens/char |

## Usage

Called at:
1. End of Power Mode session
2. `/popkit:stats` command
3. Status line widget (compact format)
4. Cloud dashboard API

## Related

- `hooks/utils/efficiency_tracker.py` - Metrics calculation
- `power-mode/checkin-hook.py` - Data collection
- `cloud-api/src/routes/analytics.ts` - Cloud storage
- `commands/stats.md` - User command
