# Injection Prevention Standard

## Overview

All code MUST prevent injection attacks including command injection, code injection, SQL injection, and path traversal. This standard defines patterns to detect and prevent injection vulnerabilities.

## Injection Patterns

### IP-001: Command Injection via os.system

**Severity**: Critical | **CWE**: CWE-78

`os.system()` with string concatenation enables shell injection.

**Detect**:
```python
# BAD - User input in os.system
os.system("ping " + user_input)
os.system(f"echo {user_data}")
```

**Fix**:
```python
# GOOD - Use subprocess with list form
import subprocess
import shlex

subprocess.run(["ping", user_input], check=True)

# GOOD - If shell needed, escape properly
subprocess.run(f"echo {shlex.quote(user_data)}", shell=True)
```

### IP-002: Command Injection via subprocess shell=True

**Severity**: Critical | **CWE**: CWE-78

`subprocess` with `shell=True` and user input is dangerous.

**Detect**:
```python
# BAD
subprocess.run(f"ls {directory}", shell=True)
subprocess.call("cat " + filename, shell=True)
```

**Fix**:
```python
# GOOD - Use list form (no shell)
subprocess.run(["ls", directory], check=True)
subprocess.run(["cat", filename], check=True)

# GOOD - If shell features needed
subprocess.run(
    ["sh", "-c", "ls -la | grep .py"],
    check=True
)
```

### IP-003: Code Injection via eval

**Severity**: Critical | **CWE**: CWE-94

`eval()` with user input enables arbitrary code execution.

**Detect**:
```python
# BAD
result = eval(user_input)
value = eval(request.form['expression'])
```

**Fix**:
```python
# GOOD - Use ast.literal_eval for data structures
import ast
result = ast.literal_eval(user_input)

# GOOD - Use explicit parsing
if user_input == "add":
    result = add_function()
```

### IP-004: Code Injection via exec

**Severity**: Critical | **CWE**: CWE-94

`exec()` with user input enables arbitrary code execution.

**Detect**:
```python
# BAD
exec(user_code)
exec(f"print({user_value})")
```

**Fix**:
```python
# GOOD - Never exec user input
# Use a sandboxed interpreter if dynamic code is required

# GOOD - Pre-defined operations
operations = {
    "sum": lambda x: sum(x),
    "avg": lambda x: sum(x) / len(x)
}
result = operations[user_choice](data)
```

### IP-005: Path Traversal

**Severity**: High | **CWE**: CWE-22

Unsanitized file paths enable directory traversal attacks.

**Detect**:
```python
# BAD
open(f"/uploads/{user_filename}")
Path(base_dir + user_path)
```

**Fix**:
```python
# GOOD - Validate and resolve paths
from pathlib import Path

base = Path("/safe/directory").resolve()
requested = (base / user_filename).resolve()

if not str(requested).startswith(str(base)):
    raise ValueError("Path traversal detected")

# GOOD - Use secure_filename for uploads
from werkzeug.utils import secure_filename
safe_name = secure_filename(user_filename)
```

### IP-006: SQL Injection

**Severity**: Critical | **CWE**: CWE-89

String formatting in SQL queries enables injection.

**Detect**:
```python
# BAD
query = f"SELECT * FROM users WHERE name = '{user_input}'"
cursor.execute("SELECT * FROM users WHERE id = %s" % user_id)
```

**Fix**:
```python
# GOOD - Parameterized queries
cursor.execute("SELECT * FROM users WHERE name = ?", (user_input,))
cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))

# GOOD - ORM
User.query.filter_by(name=user_input).first()
```

### IP-007: Template Injection

**Severity**: High | **CWE**: CWE-94

User input in templates enables server-side template injection.

**Detect**:
```python
# BAD
template = Template(user_template)
render_template_string(user_input)
```

**Fix**:
```python
# GOOD - Use static templates with variables
render_template("page.html", user_data=user_input)

# GOOD - Sandbox template rendering
from jinja2.sandbox import SandboxedEnvironment
env = SandboxedEnvironment()
template = env.from_string(user_template)
```

### IP-008: Unsafe Deserialization

**Severity**: Critical | **CWE**: CWE-502

Deserializing untrusted data enables remote code execution.

**Detect**:
```python
# BAD
pickle.loads(user_data)
yaml.load(user_input)  # Without Loader
marshal.loads(external_data)
```

**Fix**:
```python
# GOOD - Use safe loaders
import yaml
data = yaml.safe_load(user_input)

# GOOD - Use JSON for untrusted data
import json
data = json.loads(user_input)

# GOOD - Validate before deserializing
if is_trusted_source(data):
    obj = pickle.loads(data)
```

## Validation Checklist

| Check ID | Description | Severity |
|----------|-------------|----------|
| IP-001 | No os.system with string concat | critical |
| IP-002 | No subprocess shell=True with user input | critical |
| IP-003 | No eval with user input | critical |
| IP-004 | No exec with user input | critical |
| IP-005 | No unsanitized file paths | high |
| IP-006 | No string-formatted SQL | critical |
| IP-007 | No user input in templates | high |
| IP-008 | No unsafe deserialization | critical |

## Safe Patterns

The following mitigate injection risks:

1. **shlex.quote()**: Escapes shell arguments
2. **List form subprocess**: `subprocess.run(["cmd", arg])`
3. **Parameterized queries**: `cursor.execute("?", (val,))`
4. **ast.literal_eval()**: Safe for data structures
5. **yaml.safe_load()**: Prevents arbitrary code
6. **pathlib resolve()**: Resolves and validates paths

## References

- CWE-78: OS Command Injection
- CWE-89: SQL Injection
- CWE-94: Code Injection
- CWE-22: Path Traversal
- CWE-502: Deserialization of Untrusted Data
- OWASP A03:2021 – Injection
