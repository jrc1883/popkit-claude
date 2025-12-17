---
name: smoke-test
description: "Use after updating PopKit or starting a new session to verify the plugin is functioning correctly. Runs quick runtime health checks: API connectivity, hooks responding, commands available, and cloud registration. Do NOT use for deep testing - use pop-plugin-test for comprehensive validation."
---

# PopKit Smoke Test

## Overview

Quick runtime health verification for installed PopKit. Unlike `pop-plugin-test` which validates internal structure, this skill verifies the **runtime environment** is working correctly.

**Announce at start:** "I'm running a smoke test to verify PopKit is working correctly."

## What It Tests

### 1. Plugin Loading
- PopKit commands are available (`/popkit:*`)
- Skills can be invoked via Skill tool
- Agent routing is functional

### 2. Hook Health
- Hooks are responding (not blocking)
- JSON protocol working
- Check-in hook (if Power Mode) responding

### 3. Cloud Connectivity
- `POPKIT_API_KEY` is set
- API endpoint is reachable
- Project can register/update

### 4. Session State
- STATUS.json readable/writable
- Session capture working
- Context can be restored

## Execution Protocol

### Quick Smoke Test (Default)

```
I'll run a quick smoke test to verify PopKit is functioning.

Testing Plugin Loading...
[PASS] Commands available (/popkit:git, /popkit:dev, etc.)
[PASS] Skills invocable via Skill tool
[PASS] Agent routing functional

Testing Hook Health...
[PASS] Pre-tool-use hook responding
[PASS] Post-tool-use hook responding
[PASS] JSON protocol valid

Testing Cloud Connectivity...
[PASS] POPKIT_API_KEY set
[PASS] API endpoint reachable (popkit-cloud.josephcardillo.workers.dev)
[PASS] Project registration successful

Testing Session State...
[PASS] STATUS.json writable
[PASS] Session ID generated

═══════════════════════════════════════
PopKit Smoke Test: ALL PASS (10/10)
═══════════════════════════════════════
```

### Verbose Mode

```
Running verbose smoke test with timing...

Testing Plugin Loading...
[PASS] Commands available (23 commands found) [12ms]
[PASS] Skills invocable (36 skills found) [8ms]
[PASS] Agent routing functional (routing config valid) [15ms]

Testing Hook Health...
[PASS] Pre-tool-use hook responding [45ms]
[PASS] Post-tool-use hook responding [38ms]
[PASS] JSON protocol valid (tested 3 exchanges) [22ms]

Testing Cloud Connectivity...
[PASS] POPKIT_API_KEY set (pk_live_****) [0ms]
[PASS] API endpoint reachable [234ms]
[PASS] Project registration successful (session #5) [189ms]
[PASS] Activity tracking working [156ms]

Testing Session State...
[PASS] STATUS.json writable [8ms]
[PASS] Session ID generated (sess_abc123) [0ms]
[PASS] Feedback store initialized [12ms]

═══════════════════════════════════════
PopKit Smoke Test: ALL PASS (13/13)
Total Time: 739ms
═══════════════════════════════════════

Project registered as: abc123def456 (popkit)
Session count: 5
Last health score: 85
```

## Test Implementation

### 1. Plugin Loading Test

```python
# Test commands exist
commands = glob.glob("commands/*.md")
assert len(commands) > 0, "No commands found"

# Test skills exist
skills = glob.glob("skills/*/SKILL.md")
assert len(skills) > 0, "No skills found"

# Test routing config valid
config = json.load(open("agents/config.json"))
assert "keywords" in config, "No routing keywords"
```

### 2. Hook Health Test

```python
# Test hook responds
input_data = {"tool_name": "Read", "tool_input": {"file_path": "/test"}}
result = run_hook("pre-tool-use.py", input_data)
assert "decision" in result, "Hook did not respond"
assert result["decision"] in ["allow", "block", "modify"], "Invalid decision"
```

### 3. Cloud Connectivity Test

```python
# Test API key
api_key = os.environ.get("POPKIT_API_KEY")
assert api_key, "POPKIT_API_KEY not set"

# Test API reachable
from utils.project_client import ProjectClient
client = ProjectClient(api_key=api_key)
result = client.register_project()
assert result, "Registration failed"
assert result.status == "registered", f"Unexpected status: {result.status}"
```

### 4. Session State Test

```python
# Test STATUS.json
status_path = Path(".claude/STATUS.json")
status_path.parent.mkdir(exist_ok=True)

# Write test
status_path.write_text(json.dumps({"test": True}))
assert status_path.exists(), "Could not write STATUS.json"

# Read test
data = json.loads(status_path.read_text())
assert data.get("test") == True, "Could not read STATUS.json"
```

## Failure Handling

### Common Failures

| Failure | Cause | Resolution |
|---------|-------|------------|
| `POPKIT_API_KEY not set` | Missing env var | Set API key in .env or environment |
| `API endpoint unreachable` | Network issue or API down | Check network, try again |
| `Hook not responding` | Python error in hook | Check hook logs, run `python hook.py` manually |
| `Commands not available` | Plugin not installed | Run `/plugin install popkit@popkit-plugin` |
| `Routing config invalid` | JSON parse error | Validate `agents/config.json` |

### Recovery Suggestions

If smoke test fails:

1. **Plugin not loaded?**
   - Restart Claude Code
   - Verify plugin installed: `/plugin list`
   - Reinstall: `/plugin install popkit@popkit-plugin`

2. **Cloud not connecting?**
   - Check `POPKIT_API_KEY` is valid
   - Test manually: `curl https://popkit-cloud.josephcardillo.workers.dev/v1/health`
   - Check for firewall/proxy issues

3. **Hooks failing?**
   - Check Python installed: `python --version`
   - Run hook manually: `echo '{}' | python hooks/pre-tool-use.py`
   - Check for syntax errors

## Integration

### Run After Plugin Update

```
/plugin update popkit@popkit-plugin
# [Claude Code restarts]
# Use smoke-test skill to verify
```

### Run at Session Start

The smoke test can be triggered automatically at session start to verify everything is working. This is optional and can be enabled in settings.

### Cross-Project Verification

From the main PopKit monorepo, you can verify all installed projects:

```
/popkit:project observe

# See which projects are registering
# Identify projects with registration failures
# Check health scores across all projects
```

## Output

- Console test results (always)
- `.claude/smoke-test-results.json` (optional)
- Cloud activity update (if cloud connected)

## Related

| Tool | Purpose |
|------|---------|
| `pop-plugin-test` | Deep internal validation (structure, schemas) |
| `pop-morning-routine` | Daily health check with health score |
| `/popkit:project observe` | Cross-project observability dashboard |
