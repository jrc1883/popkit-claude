# Input Validation Standard

## Overview

All external input MUST be validated before use. This standard defines patterns for detecting and preventing input validation vulnerabilities.

## Input Validation Patterns

### IV-001: Missing Input Validation

**Severity**: High | **CWE**: CWE-20

All user input must be validated for type, length, format, and range.

**Detect**:
```python
# BAD - Direct use of user input
name = request.form["name"]
save_user(name)

# BAD - No length check
comment = request.json.get("comment")
db.save(comment)
```

**Fix**:
```python
# GOOD - Validate input
from validators import validate_name

name = request.form.get("name", "")
if not validate_name(name):
    raise ValueError("Invalid name")
save_user(name)

# GOOD - Length and type checks
comment = request.json.get("comment", "")
if not isinstance(comment, str) or len(comment) > 10000:
    raise ValueError("Invalid comment")
```

### IV-002: Missing Type Validation

**Severity**: Medium | **CWE**: CWE-20

Input types must be verified before operations.

**Detect**:
```python
# BAD - Assuming type
quantity = request.json["quantity"]
total = price * quantity  # Could be string

# BAD - No type check
user_id = request.args.get("id")
User.query.get(user_id)  # Could be non-integer
```

**Fix**:
```python
# GOOD - Explicit type conversion with validation
try:
    quantity = int(request.json.get("quantity", 0))
    if quantity < 1 or quantity > 1000:
        raise ValueError()
except (TypeError, ValueError):
    abort(400, "Invalid quantity")

# GOOD - Type-safe parsing
user_id = request.args.get("id", type=int)
```

### IV-003: Missing Range Validation

**Severity**: Medium | **CWE**: CWE-129

Numeric inputs must be within expected ranges.

**Detect**:
```python
# BAD - No range check
page = int(request.args.get("page"))
offset = (page - 1) * 100  # Negative pages?

# BAD - Unbounded array access
index = int(request.args.get("index"))
return items[index]  # Index out of bounds?
```

**Fix**:
```python
# GOOD - Range validation
page = int(request.args.get("page", 1))
page = max(1, min(page, 1000))  # Clamp to valid range

# GOOD - Bounds checking
index = int(request.args.get("index", 0))
if 0 <= index < len(items):
    return items[index]
abort(404)
```

### IV-004: Missing Format Validation

**Severity**: Medium | **CWE**: CWE-20

Structured inputs (emails, URLs, dates) must be format-validated.

**Detect**:
```python
# BAD - No email validation
email = request.form["email"]
send_email(email, "Welcome!")

# BAD - No URL validation
callback_url = request.json["callback"]
requests.post(callback_url, data=result)
```

**Fix**:
```python
# GOOD - Format validation
import re
from urllib.parse import urlparse

email = request.form.get("email", "")
if not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
    raise ValueError("Invalid email")

# GOOD - URL validation
callback_url = request.json.get("callback", "")
parsed = urlparse(callback_url)
if parsed.scheme not in ("https",) or parsed.netloc not in ALLOWED_HOSTS:
    raise ValueError("Invalid callback URL")
```

### IV-005: Insufficient Output Encoding

**Severity**: High | **CWE**: CWE-79

Output must be encoded for the context to prevent XSS.

**Detect**:
```python
# BAD - Raw HTML output
return f"<h1>Welcome, {username}</h1>"

# BAD - Unsafe template
template = f"<script>user = '{user_input}'</script>"
```

**Fix**:
```python
# GOOD - HTML encoding
from markupsafe import escape
return f"<h1>Welcome, {escape(username)}</h1>"

# GOOD - JSON encoding in scripts
import json
template = f"<script>user = {json.dumps(user_input)}</script>"

# GOOD - Use template engine auto-escaping
return render_template("page.html", username=username)
```

### IV-006: Missing Content-Type Validation

**Severity**: Medium | **CWE**: CWE-20

File uploads must validate content type, not just extension.

**Detect**:
```python
# BAD - Trust file extension
if filename.endswith(".jpg"):
    save_image(file)

# BAD - Trust Content-Type header
if request.content_type == "image/jpeg":
    process_image(request.data)
```

**Fix**:
```python
# GOOD - Validate actual content
import magic

file_data = file.read()
mime = magic.from_buffer(file_data, mime=True)
if mime not in ("image/jpeg", "image/png"):
    raise ValueError("Invalid file type")

# GOOD - Multiple checks
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
ALLOWED_MIMES = {"image/jpeg", "image/png"}

ext = Path(filename).suffix.lower()
mime = magic.from_buffer(file.read(1024), mime=True)
if ext not in ALLOWED_EXTENSIONS or mime not in ALLOWED_MIMES:
    raise ValueError("Invalid file")
```

### IV-007: Missing Size Limits

**Severity**: Medium | **CWE**: CWE-400

Input sizes must be limited to prevent DoS.

**Detect**:
```python
# BAD - Unlimited file upload
file = request.files["upload"]
file.save(f"/uploads/{file.filename}")

# BAD - Unlimited request body
data = request.get_json()
```

**Fix**:
```python
# GOOD - Size limits
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB

# GOOD - Check before processing
file = request.files.get("upload")
if file:
    file.seek(0, 2)  # Seek to end
    size = file.tell()
    file.seek(0)
    if size > 10 * 1024 * 1024:  # 10MB
        raise ValueError("File too large")
```

### IV-008: Regex DoS (ReDoS)

**Severity**: Medium | **CWE**: CWE-1333

Complex regex patterns can cause denial of service.

**Detect**:
```python
# BAD - Evil regex
pattern = r"^(a+)+$"
re.match(pattern, user_input)  # ReDoS vulnerable

# BAD - Nested quantifiers
pattern = r".*.*.*"
```

**Fix**:
```python
# GOOD - Simple patterns
pattern = r"^a+$"

# GOOD - Timeout protection
import regex  # pip install regex
regex.match(pattern, user_input, timeout=1.0)

# GOOD - Input length limit before regex
if len(user_input) > 1000:
    raise ValueError("Input too long")
re.match(pattern, user_input)
```

## Validation Checklist

| Check ID | Description | Severity |
|----------|-------------|----------|
| IV-001 | Validate all user input | high |
| IV-002 | Verify input types | medium |
| IV-003 | Check numeric ranges | medium |
| IV-004 | Validate structured formats | medium |
| IV-005 | Encode output for context | high |
| IV-006 | Validate file content types | medium |
| IV-007 | Enforce size limits | medium |
| IV-008 | Avoid ReDoS patterns | medium |

## Validation Libraries

- **Pydantic**: Type validation and parsing
- **Cerberus**: Schema-based validation
- **marshmallow**: Serialization/deserialization
- **validators**: Common format validators
- **python-magic**: File type detection

## References

- CWE-20: Improper Input Validation
- CWE-79: Cross-site Scripting (XSS)
- CWE-129: Array Index Error
- CWE-400: Resource Exhaustion
- CWE-1333: Regex DoS
- OWASP Input Validation Cheat Sheet
