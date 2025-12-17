# Secret Detection Standard

## Overview

All code MUST be free of hardcoded secrets, credentials, and sensitive data. This standard defines patterns to detect and prevent credential exposure.

## Secret Patterns

### SD-001: API Keys

**Severity**: Critical | **CWE**: CWE-798

API keys should never be hardcoded in source code.

**Detect**:
```python
# BAD - Hardcoded API key
api_key = "sk-1234567890abcdef"
API_KEY = "AKIAIOSFODNN7EXAMPLE"
```

**Fix**:
```python
# GOOD - Environment variable
api_key = os.environ.get("API_KEY")

# GOOD - Config file (gitignored)
api_key = config.get("api_key")
```

### SD-002: AWS Access Keys

**Severity**: Critical | **CWE**: CWE-798

AWS access keys (starting with AKIA, ABIA, ACCA, ASIA) must not appear in code.

**Detect**:
```python
# BAD
aws_key = "AKIAIOSFODNN7EXAMPLE"
```

**Fix**:
```python
# GOOD - Use AWS credentials file or environment
import boto3
client = boto3.client('s3')  # Uses default credential chain
```

### SD-003: AWS Secret Keys

**Severity**: Critical | **CWE**: CWE-798

AWS secret access keys are 40-character strings that must be protected.

**Detect**:
```python
# BAD
aws_secret = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
```

### SD-004: Passwords

**Severity**: High | **CWE**: CWE-259

Hardcoded passwords create security vulnerabilities.

**Detect**:
```python
# BAD
password = "mysecretpassword"
db_password = "admin123"
```

**Fix**:
```python
# GOOD - Environment variable
password = os.environ.get("DB_PASSWORD")

# GOOD - Secrets manager
password = secrets_manager.get_secret("db-password")
```

### SD-005: Private Keys

**Severity**: Critical | **CWE**: CWE-321

Private keys in code enable impersonation attacks.

**Detect**:
```
# BAD - Private key in code
-----BEGIN RSA PRIVATE KEY-----
MIIEpQIBAAKCAQEA...
-----END RSA PRIVATE KEY-----
```

**Fix**:
```python
# GOOD - Load from file
with open("/path/to/key.pem", "r") as f:
    private_key = f.read()

# GOOD - Use secrets manager
private_key = secrets_manager.get_secret("ssh-key")
```

### SD-006: JWT Tokens

**Severity**: High | **CWE**: CWE-798

JWT tokens in code may expose authentication capabilities.

**Detect**:
```python
# BAD - Hardcoded JWT
token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0..."
```

### SD-007: GitHub Tokens

**Severity**: Critical | **CWE**: CWE-798

GitHub tokens (ghp_, gho_, ghu_, ghs_, ghr_) enable repository access.

**Detect**:
```python
# BAD
github_token = "ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

**Fix**:
```python
# GOOD - Environment variable
github_token = os.environ.get("GITHUB_TOKEN")

# GOOD - gh CLI auth
# Uses: gh auth token
```

### SD-008: Database Connection Strings

**Severity**: Critical | **CWE**: CWE-798

Connection strings with embedded credentials expose databases.

**Detect**:
```python
# BAD
conn = "mongodb://user:password@host:27017/db"
conn = "postgres://admin:secret@localhost/mydb"
```

**Fix**:
```python
# GOOD - Separate credential handling
user = os.environ.get("DB_USER")
password = os.environ.get("DB_PASSWORD")
conn = f"postgres://{user}:{password}@localhost/mydb"
```

### SD-009: Bearer Tokens

**Severity**: High | **CWE**: CWE-798

Bearer tokens should be dynamically obtained.

**Detect**:
```python
# BAD
headers = {"Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5..."}
```

### SD-010: Generic Secrets

**Severity**: High | **CWE**: CWE-798

Generic patterns like `secret_key`, `token_value` with hardcoded values.

**Detect**:
```python
# BAD
secret_key = "my-super-secret-key-12345"
token_value = "abcdef123456789"
```

## Validation Checklist

| Check ID | Description | Severity |
|----------|-------------|----------|
| SD-001 | No API key assignments | critical |
| SD-002 | No AWS access key IDs | critical |
| SD-003 | No AWS secret keys | critical |
| SD-004 | No password assignments | high |
| SD-005 | No private keys | critical |
| SD-006 | No JWT tokens | high |
| SD-007 | No GitHub tokens | critical |
| SD-008 | No credential connection strings | critical |
| SD-009 | No bearer tokens | high |
| SD-010 | No generic secret patterns | high |

## Acceptable Patterns

The following are NOT flagged:

1. **Placeholder values**: `api_key = "your-api-key-here"`
2. **Environment lookups**: `os.environ.get("KEY")`
3. **Config references**: `config["api_key"]`
4. **Documentation examples**: In `.md` files
5. **Test fixtures**: In `test_*.py` with obvious fake data

## References

- CWE-798: Use of Hard-coded Credentials
- CWE-259: Use of Hard-coded Password
- CWE-321: Use of Hard-coded Cryptographic Key
- OWASP A02:2021 – Cryptographic Failures
