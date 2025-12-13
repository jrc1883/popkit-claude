# Command Naming Standards

Standards for naming commands, subcommands, and flags.

## Core Principles

### CN-001: Descriptive Names

Commands should clearly describe their function.

**Guidelines:**
- Use full words over abbreviations
- Verb-first naming pattern
- Self-documenting names

**Examples:**
| Good | Bad | Why |
|------|-----|-----|
| `create-project` | `cp` | Clear vs cryptic |
| `run-tests` | `rt` | Descriptive vs abbreviated |
| `analyze-code` | `ac` | Self-documenting |

### CN-002: Verb-First Pattern

Start commands with action verbs.

**Standard Verbs:**
| Verb | Usage |
|------|-------|
| `create` | Make something new |
| `delete` | Remove something |
| `list` | Show multiple items |
| `show` | Display single item detail |
| `update` | Modify existing item |
| `run` | Execute a process |
| `check` | Validate or verify |

**Pattern:**
```
/namespace:verb-noun
/namespace:verb-noun-modifier
```

**Examples:**
```
/popkit:create-project
/popkit:run-tests --coverage
/popkit:check-status
```

### CN-003: Avoid Abbreviations

Spell out words unless universally understood.

**Acceptable Abbreviations:**
- `init` (initialize)
- `config` (configuration)
- `auth` (authentication)
- `git` (version control)
- `npm` (package manager)

**Avoid:**
- `cfg` → `config`
- `mgr` → `manager`
- `impl` → `implementation`
- `util` → `utility`

### CN-004: Consistent Separators

Use hyphens as word separators.

**Standard:**
```
command-name-here  ✓
commandNameHere    ✗
command_name_here  ✗
```

**Exception:** Environment variables use SCREAMING_SNAKE_CASE

### CN-005: Consistent Verbs

Use the same verb for similar operations across commands.

**Verb Standardization:**
| Standard | Avoid Using |
|----------|-------------|
| `create` | `add`, `new`, `make` |
| `delete` | `remove`, `rm`, `destroy` |
| `list` | `ls`, `show-all`, `get-all` |
| `show` | `get`, `view`, `display` |
| `update` | `edit`, `modify`, `set` |

### CN-006: Namespace Prefix

Use consistent namespace prefix.

**Format:**
```
/namespace:command
```

**PopKit Standard:**
```
/popkit:project
/popkit:git
/popkit:routine
```

### CN-007: Reasonable Length

Keep command names concise but clear.

**Targets:**
| Length | Status |
|--------|--------|
| 5-15 chars | Ideal |
| 15-20 chars | Acceptable |
| 20-30 chars | Warning |
| >30 chars | Too long |

### CN-008: Predictable Subcommands

Use standard subcommands consistently.

**Standard Subcommands:**
| Subcommand | Purpose |
|------------|---------|
| `list` | Show all items |
| `create` | Create new item |
| `show` | Display details |
| `delete` | Remove item |
| `edit` | Modify item |
| `help` | Show help |

## Flag Standards

### Flag Naming

**Long flags:** Full descriptive names
```
--verbose
--output-format
--dry-run
```

**Short flags:** Single meaningful letter
```
-v (verbose)
-o (output)
-n (dry-run)
```

### Common Flags

| Flag | Short | Purpose |
|------|-------|---------|
| `--help` | `-h` | Show help |
| `--verbose` | `-v` | Detailed output |
| `--quiet` | `-q` | Minimal output |
| `--dry-run` | `-n` | Preview mode |
| `--force` | `-f` | Skip confirmations |
| `--output` | `-o` | Output destination |
| `--format` | | Output format |

## Quality Metrics

| Metric | Target |
|--------|--------|
| Verb-first pattern | 100% |
| Descriptive names | 100% |
| Length compliance | >90% |
| Consistent separators | 100% |
