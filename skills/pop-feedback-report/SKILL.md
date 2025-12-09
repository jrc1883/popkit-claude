# Feedback Report

Generate analytics and insights from collected user feedback.

Part of Issue #91 (User Feedback Collection System)
Parent: Epic #88 (Self-Improvement & Learning System)

## When to Use

Invoke this skill when:
- User asks to see feedback statistics
- Reviewing agent or command performance
- Identifying areas for improvement
- Checking for low-rated items that need attention

## Overview

Analyzes collected feedback to provide:
- Overall statistics (total, average rating, trends)
- Per-agent performance breakdown
- Low-rated items flagged for review
- Rating distribution visualizations

## Process

### Step 1: Load Feedback Data

```python
from feedback_store import get_feedback_store

store = get_feedback_store()
stats = store.get_stats()
agent_stats = store.get_agent_stats()
low_rated = store.get_low_rated_items()
```

### Step 2: Generate Report

Present findings in a structured format:

```markdown
## Feedback Report

### Overview

| Metric | Value |
|--------|-------|
| Total Feedback | {total} |
| Average Rating | {avg:.2f}/3 |
| Recent (7 days) | {recent} |
| Low-Rated Items | {low_count} |

### Rating Distribution

```
0 (Harmful)    : ████░░░░░░ 15%
1 (Unhelpful)  : ██░░░░░░░░  8%
2 (Helpful)    : ████████░░ 42%
3 (Very)       : ███████░░░ 35%
```

### Agent Performance

| Agent | Avg Rating | Count | Trend |
|-------|------------|-------|-------|
| code-reviewer | 2.8 | 45 | ↑ |
| bug-whisperer | 2.6 | 23 | → |
| security-auditor | 2.4 | 12 | ↓ |

### Items Needing Attention

These items have average ratings ≤ 1.5:

1. **command:/popkit:debug** (avg: 1.2, count: 5)
   - Last feedback: "Didn't find the actual issue"
   - Suggested action: Review debugging workflow

2. **agent:api-designer** (avg: 1.4, count: 8)
   - Last feedback: "Generated outdated patterns"
   - Suggested action: Update API design templates
```

### Step 3: Offer Actions

Use AskUserQuestion to offer follow-up actions:

```
[AskUserQuestion: What would you like to do?]
- View details for low-rated items
- Export feedback data
- Clear old feedback
- Adjust feedback settings
```

## Output Format

### Quick Summary (Default)

```
## Feedback Summary

📊 **45 total ratings** | Avg: 2.5/3 | 12 this week

Top performers: code-reviewer (2.8), test-writer-fixer (2.7)
Needs attention: api-designer (1.4), debug (1.2)

Run `pop-feedback-report --full` for detailed breakdown.
```

### Full Report

Include all sections above plus:
- Feedback by context type (agent, command, workflow)
- Time trends (last 7/30/90 days)
- Common feedback comments
- Recommendations

## Arguments

| Argument | Description |
|----------|-------------|
| (none) | Quick summary |
| `--full` | Full detailed report |
| `--agent NAME` | Focus on specific agent |
| `--command NAME` | Focus on specific command |
| `--low-rated` | Only show items needing attention |
| `--export FILE` | Export data to JSON file |

## Examples

### Quick Check

```
User: Show feedback summary

Claude: [Invokes pop-feedback-report skill]

## Feedback Summary

📊 **45 total ratings** | Avg: 2.5/3 | 12 this week

Top performers:
- code-reviewer (2.8, 15 ratings)
- test-writer-fixer (2.7, 8 ratings)

Needs attention:
- api-designer (1.4, 8 ratings) ⚠️
```

### Detailed Agent Review

```
User: How is the code-reviewer performing?

Claude: [Invokes pop-feedback-report --agent code-reviewer]

## code-reviewer Feedback Analysis

| Metric | Value |
|--------|-------|
| Total Ratings | 45 |
| Average | 2.8/3 |
| This Week | 8 |

**Rating Distribution:**
- 3 (Very helpful): 55%
- 2 (Helpful): 35%
- 1 (Unhelpful): 8%
- 0 (Harmful): 2%

**Recent Comments:**
- "Great catch on the security issue" (rating: 3)
- "Missed some edge cases" (rating: 2)

**Trend:** ↑ Improving (was 2.5 last month)
```

## Related

- `feedback_store.py` - SQLite storage for feedback
- `feedback_triggers.py` - Feedback timing logic
- `feedback_hook.py` - PostToolUse hook for collection
- `/popkit:dev` - May trigger feedback after workflows

## Implementation Notes

### Visualization

For rating distributions, use simple ASCII bar charts:

```python
def rating_bar(count: int, total: int, width: int = 10) -> str:
    """Generate an ASCII progress bar."""
    if total == 0:
        return "░" * width
    filled = int((count / total) * width)
    return "█" * filled + "░" * (width - filled)
```

### Trend Calculation

Compare current period average to previous period:

```python
def calculate_trend(current_avg: float, previous_avg: float) -> str:
    """Determine trend arrow."""
    diff = current_avg - previous_avg
    if diff > 0.2:
        return "↑"
    elif diff < -0.2:
        return "↓"
    return "→"
```

### Privacy Considerations

When showing feedback comments:
- Only show comments from local storage
- Anonymize any personal information
- Truncate long comments
- Don't expose raw session IDs
