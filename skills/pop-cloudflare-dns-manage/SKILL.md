---
name: cloudflare-dns-manage
description: "Manage Cloudflare DNS records - list zones, add/update/delete records, configure proxy settings, and manage SSL/TLS. Useful for domain configuration and infrastructure management."
---

# Cloudflare DNS Management

## Overview

Manage DNS records for domains in your Cloudflare account. List, create, update, and delete records with full control over proxy settings and TTL.

**Core principle:** DNS changes are powerful - always confirm before modifications.

**Trigger:** Manual invocation for DNS operations, or as part of deployment workflows

## Prerequisites

- Cloudflare account with API token
- `CLOUDFLARE_API_TOKEN` environment variable set
- Token must have DNS edit permissions

## Critical Rules

1. **ALWAYS list before modify** - Show existing records first
2. **CONFIRM destructive operations** - Delete requires explicit confirmation
3. **Preserve proxy settings** - Don't accidentally disable Cloudflare proxy
4. **Use appropriate TTL** - Auto (1) for proxied, explicit for DNS-only
5. **Document changes** - Add comments to records

## DNS Record Types

| Type | Purpose | Example |
|------|---------|---------|
| A | IPv4 address | `192.168.1.1` |
| AAAA | IPv6 address | `2001:db8::1` |
| CNAME | Alias to another domain | `example.com` |
| TXT | Text record (SPF, DKIM, verification) | `"v=spf1 ..."` |
| MX | Mail server | `mail.example.com` (with priority) |
| NS | Nameserver | `ns1.example.com` |
| CAA | Certificate Authority Authorization | `0 issue "letsencrypt.org"` |
| SRV | Service record | `_sip._tcp.example.com` |

## Process

### Operation 1: List Zones (Domains)

```python
from hooks.utils.cloudflare_api import CloudflareClient

client = CloudflareClient()
zones = client.list_zones()

print("Your Cloudflare Zones:")
print("=" * 50)
for zone in zones:
    print(f"  {zone.name}")
    print(f"    ID: {zone.id}")
    print(f"    Status: {zone.status}")
    print()
```

Output:
```
Your Cloudflare Zones:
==================================================
  thehouseofdeals.com
    ID: 15e73cdb377dc43b27a93b27f7cbc71d
    Status: active

  unjoe.me
    ID: c85da93ad9ef11e0c1c8bedd376e8d57
    Status: active
```

### Operation 2: List DNS Records

```python
def list_records(domain: str, record_type: str = None):
    """List DNS records for a domain."""
    client = CloudflareClient()

    zone = client.get_zone_by_name(domain)
    if not zone:
        print(f"ERROR: Zone not found: {domain}")
        return

    records = client.list_dns_records(zone.id, record_type=record_type)

    print(f"DNS Records for {domain}:")
    print("=" * 70)
    print(f"{'Type':<8} {'Name':<35} {'Content':<25} {'Proxy'}")
    print("-" * 70)

    for record in records:
        proxy = "Yes" if record.proxied else "No"
        name = record.name.replace(f".{domain}", "") if record.name != domain else "@"
        content = record.content[:22] + "..." if len(record.content) > 25 else record.content
        print(f"{record.type:<8} {name:<35} {content:<25} {proxy}")
```

Output:
```
DNS Records for thehouseofdeals.com:
======================================================================
Type     Name                                Content                   Proxy
----------------------------------------------------------------------
CNAME    api                                 popkit-cloud-api.worke... Yes
CNAME    dev                                 66dfd820-fbb8-45a0-835... Yes
TXT      _acme-challenge                     "JW5tjIkvfv0ANeicg6Wq9... No
TXT      default._domainkey                  "v=DKIM1; p=MIIBIjANBg... No
TXT      _dmarc                              "v=DMARC1; p=quarantine... No
```

### Operation 3: Create DNS Record

```
Use AskUserQuestion tool with:
- question: "What type of DNS record do you want to create?"
- header: "Record Type"
- options:
  - label: "CNAME"
    description: "Alias to another domain (most common)"
  - label: "A"
    description: "Point to IPv4 address"
  - label: "TXT"
    description: "Text record (verification, SPF, etc.)"
  - label: "MX"
    description: "Mail server record"
- multiSelect: false
```

```python
def create_record(
    domain: str,
    record_type: str,
    name: str,
    content: str,
    proxied: bool = True,
    comment: str = None
):
    """Create a new DNS record."""
    client = CloudflareClient()

    zone = client.get_zone_by_name(domain)
    if not zone:
        raise ValueError(f"Zone not found: {domain}")

    # Check if record exists
    full_name = f"{name}.{domain}" if name != "@" else domain
    existing = client.list_dns_records(zone.id, name=full_name)

    if existing:
        print(f"WARNING: Record already exists: {full_name}")
        print(f"  Current: {existing[0].type} -> {existing[0].content}")
        # Use AskUserQuestion to confirm overwrite
        return None

    record = client.create_dns_record(
        zone.id,
        record_type=record_type,
        name=name,
        content=content,
        proxied=proxied,
        comment=comment
    )

    print(f"Created DNS record:")
    print(f"  Type: {record.type}")
    print(f"  Name: {record.name}")
    print(f"  Content: {record.content}")
    print(f"  Proxied: {record.proxied}")

    return record
```

### Operation 4: Update DNS Record

```python
def update_record(
    domain: str,
    name: str,
    content: str = None,
    proxied: bool = None,
    comment: str = None
):
    """Update an existing DNS record."""
    client = CloudflareClient()

    zone = client.get_zone_by_name(domain)
    if not zone:
        raise ValueError(f"Zone not found: {domain}")

    full_name = f"{name}.{domain}" if name != "@" else domain
    records = client.list_dns_records(zone.id, name=full_name)

    if not records:
        raise ValueError(f"Record not found: {full_name}")

    record = records[0]

    print(f"Updating record: {full_name}")
    print(f"  Current: {record.content}")
    if content:
        print(f"  New: {content}")

    updated = client.update_dns_record(
        zone.id,
        record.id,
        content=content,
        proxied=proxied,
        comment=comment
    )

    print(f"Record updated successfully")
    return updated
```

### Operation 5: Delete DNS Record

```
Use AskUserQuestion tool with:
- question: "Are you sure you want to delete this DNS record? This cannot be undone."
- header: "Confirm Delete"
- options:
  - label: "Yes, delete it"
    description: "Permanently remove the record"
  - label: "No, cancel"
    description: "Keep the record"
- multiSelect: false
```

```python
def delete_record(domain: str, name: str):
    """Delete a DNS record."""
    client = CloudflareClient()

    zone = client.get_zone_by_name(domain)
    if not zone:
        raise ValueError(f"Zone not found: {domain}")

    full_name = f"{name}.{domain}" if name != "@" else domain
    records = client.list_dns_records(zone.id, name=full_name)

    if not records:
        raise ValueError(f"Record not found: {full_name}")

    record = records[0]

    print(f"Deleting record:")
    print(f"  Type: {record.type}")
    print(f"  Name: {record.name}")
    print(f"  Content: {record.content}")

    # Require confirmation
    # AskUserQuestion should have been called before this

    success = client.delete_dns_record(zone.id, record.id)

    if success:
        print("Record deleted successfully")
    else:
        print("ERROR: Failed to delete record")

    return success
```

### Operation 6: Toggle Proxy Status

```python
def toggle_proxy(domain: str, name: str, enable: bool):
    """Enable or disable Cloudflare proxy (orange cloud)."""
    client = CloudflareClient()

    zone = client.get_zone_by_name(domain)
    if not zone:
        raise ValueError(f"Zone not found: {domain}")

    full_name = f"{name}.{domain}" if name != "@" else domain
    records = client.list_dns_records(zone.id, name=full_name)

    if not records:
        raise ValueError(f"Record not found: {full_name}")

    record = records[0]

    if record.type not in ["A", "AAAA", "CNAME"]:
        raise ValueError(f"Proxy not supported for {record.type} records")

    action = "Enabling" if enable else "Disabling"
    print(f"{action} proxy for {full_name}...")

    updated = client.update_dns_record(
        zone.id,
        record.id,
        proxied=enable
    )

    status = "enabled" if updated.proxied else "disabled"
    print(f"Proxy {status} for {full_name}")

    return updated
```

## Common DNS Configurations

### Subdomain to Worker

```
Type: CNAME
Name: api
Content: my-worker.workers.dev
Proxied: Yes
```

### Subdomain to External Service

```
Type: CNAME
Name: status
Content: statuspage.io
Proxied: No (external service needs direct access)
```

### Email Configuration (MX)

```
Type: MX
Name: @ (root domain)
Content: mx.example.com
Priority: 10
```

### SPF Record

```
Type: TXT
Name: @ (root domain)
Content: "v=spf1 include:_spf.google.com ~all"
```

### Domain Verification

```
Type: TXT
Name: @ (or specific subdomain)
Content: "google-site-verification=abc123..."
```

## Output Format

```
Cloudflare DNS Management
═════════════════════════

Domain: thehouseofdeals.com
Zone ID: 15e73cdb377dc43b27a93b27f7cbc71d

Current DNS Records (6 total):
┌──────────┬─────────────────────────────┬─────────────────────────┬───────┐
│ Type     │ Name                        │ Content                 │ Proxy │
├──────────┼─────────────────────────────┼─────────────────────────┼───────┤
│ CNAME    │ api                         │ popkit-cloud-api.work...│ Yes   │
│ CNAME    │ dev                         │ 66dfd820-fbb8-45a0...   │ Yes   │
│ TXT      │ _acme-challenge             │ "JW5tjIkvfv0ANeicg...   │ No    │
│ TXT      │ default._domainkey          │ "v=DKIM1; p=MIIBIj...   │ No    │
│ TXT      │ _dmarc                      │ "v=DMARC1; p=quara...   │ No    │
│ TXT      │ _domainkey                  │ "o=-"                   │ No    │
└──────────┴─────────────────────────────┴─────────────────────────┴───────┘

Actions Available:
  1. Create new record
  2. Update existing record
  3. Delete record
  4. Toggle proxy status
  5. Export DNS records
```

## Security Considerations

1. **Proxy sensitive subdomains** - Hide origin IP for security
2. **Use CAA records** - Restrict which CAs can issue certificates
3. **Verify SPF/DKIM/DMARC** - Prevent email spoofing
4. **Monitor DNS changes** - Use Cloudflare audit logs
5. **Avoid wildcard A records** - Be explicit about subdomains

## Integration

**Utility:** Uses `hooks/utils/cloudflare_api.py` for all operations

**Used by:**
- `pop-cloudflare-worker-deploy` - Sets up Worker DNS
- `pop-cloudflare-pages-deploy` - Sets up Pages DNS
- `/popkit:deploy` command - Infrastructure configuration

## Related Skills

| Skill | Relationship |
|-------|--------------|
| `pop-cloudflare-worker-deploy` | Uses DNS for Worker routing |
| `pop-cloudflare-pages-deploy` | Uses DNS for Pages custom domains |
| `pop-security-scan` | Can audit DNS configuration |

## CLI Quick Reference

```bash
# List zones
python -c "from hooks.utils.cloudflare_api import list_zones; print([z.name for z in list_zones()])"

# List records for domain
python -c "from hooks.utils.cloudflare_api import *; z = get_zone_by_name('example.com'); print([r.name for r in list_dns_records(z.id)])"

# Create CNAME
python -c "from hooks.utils.cloudflare_api import *; z = get_zone_by_name('example.com'); create_dns_record(z.id, 'CNAME', 'api', 'my-worker.workers.dev')"
```
