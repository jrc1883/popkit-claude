# Access Control Standard

## Overview

All code MUST implement proper access controls to prevent unauthorized access to resources. This standard defines patterns for detecting and preventing access control vulnerabilities.

## Access Control Patterns

### AC-001: Missing Authentication Checks

**Severity**: Critical | **CWE**: CWE-306

Sensitive operations must verify user authentication.

**Detect**:
```python
# BAD - No auth check before sensitive operation
@app.route("/admin/delete-user/<id>")
def delete_user(id):
    User.query.get(id).delete()
```

**Fix**:
```python
# GOOD - Authentication required
@app.route("/admin/delete-user/<id>")
@login_required
def delete_user(id):
    if not current_user.is_admin:
        abort(403)
    User.query.get(id).delete()
```

### AC-002: Missing Authorization Checks

**Severity**: Critical | **CWE**: CWE-862

Operations must verify user has permission for the action.

**Detect**:
```python
# BAD - No authorization check
@app.route("/document/<id>")
def view_document(id):
    return Document.query.get(id)
```

**Fix**:
```python
# GOOD - Authorization check
@app.route("/document/<id>")
@login_required
def view_document(id):
    doc = Document.query.get(id)
    if doc.owner_id != current_user.id:
        abort(403)
    return doc
```

### AC-003: Insecure Direct Object Reference (IDOR)

**Severity**: High | **CWE**: CWE-639

Direct database IDs in URLs enable unauthorized access.

**Detect**:
```python
# BAD - Direct ID reference without ownership check
@app.route("/api/orders/<order_id>")
def get_order(order_id):
    return Order.query.get(order_id).to_dict()
```

**Fix**:
```python
# GOOD - Verify ownership
@app.route("/api/orders/<order_id>")
@login_required
def get_order(order_id):
    order = Order.query.filter_by(
        id=order_id,
        user_id=current_user.id
    ).first_or_404()
    return order.to_dict()
```

### AC-004: Privilege Escalation

**Severity**: Critical | **CWE**: CWE-269

Users must not be able to elevate their own privileges.

**Detect**:
```python
# BAD - User can set their own role
@app.route("/api/profile", methods=["PUT"])
def update_profile():
    data = request.json
    current_user.role = data.get("role")  # Dangerous!
    current_user.save()
```

**Fix**:
```python
# GOOD - Whitelist allowed fields
ALLOWED_PROFILE_FIELDS = ["name", "email", "avatar"]

@app.route("/api/profile", methods=["PUT"])
@login_required
def update_profile():
    data = request.json
    for field in ALLOWED_PROFILE_FIELDS:
        if field in data:
            setattr(current_user, field, data[field])
    current_user.save()
```

### AC-005: Weak Session Management

**Severity**: High | **CWE**: CWE-384

Sessions must be securely managed.

**Detect**:
```python
# BAD - Session ID in URL
@app.route("/dashboard?session=<sid>")

# BAD - Predictable session IDs
session_id = str(user.id)

# BAD - Session doesn't expire
session.permanent = True  # Without timeout
```

**Fix**:
```python
# GOOD - Secure session configuration
app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=timedelta(hours=1)
)

# GOOD - Regenerate session on login
@app.route("/login", methods=["POST"])
def login():
    if authenticate(user):
        session.regenerate()
        session["user_id"] = user.id
```

### AC-006: CORS Misconfiguration

**Severity**: High | **CWE**: CWE-942

CORS must not allow arbitrary origins.

**Detect**:
```python
# BAD - Allow all origins
CORS(app, origins="*")

# BAD - Reflect origin
response.headers["Access-Control-Allow-Origin"] = request.headers.get("Origin")
```

**Fix**:
```python
# GOOD - Explicit allowed origins
CORS(app, origins=["https://app.example.com", "https://admin.example.com"])

# GOOD - Validate origin
ALLOWED_ORIGINS = {"https://app.example.com"}
origin = request.headers.get("Origin")
if origin in ALLOWED_ORIGINS:
    response.headers["Access-Control-Allow-Origin"] = origin
```

## Validation Checklist

| Check ID | Description | Severity |
|----------|-------------|----------|
| AC-001 | Auth check before sensitive ops | critical |
| AC-002 | Authorization check for resources | critical |
| AC-003 | IDOR prevention via ownership | high |
| AC-004 | No user-controlled privilege fields | critical |
| AC-005 | Secure session management | high |
| AC-006 | Restrictive CORS configuration | high |

## Secure Patterns

1. **@login_required**: Enforce authentication
2. **ownership checks**: Verify user owns resource
3. **field whitelisting**: Only allow specific updates
4. **role-based access**: Check permissions before actions
5. **secure cookies**: HttpOnly, Secure, SameSite
6. **explicit CORS**: Named origins only

## References

- CWE-306: Missing Authentication
- CWE-862: Missing Authorization
- CWE-639: Insecure Direct Object Reference
- CWE-269: Improper Privilege Management
- CWE-384: Session Fixation
- CWE-942: CORS Misconfiguration
- OWASP A01:2021 – Broken Access Control
