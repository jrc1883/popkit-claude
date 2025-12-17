# File Access Standards

Standards for efficient file operations in plugins.

## Core Principles

### FA-001: Minimize Reads Per Operation

Each operation should read minimal files.

**Targets:**
| Operation Type | Target | Warning | Critical |
|----------------|--------|---------|----------|
| Skill invocation | <3 reads | 3-5 | >5 |
| Agent activation | <5 reads | 5-8 | >8 |
| Hook execution | <2 reads | 2-4 | >4 |

**Guidelines:**
- Read config once, pass as parameter
- Cache frequently accessed files
- Combine related reads

### FA-002: Read Caching

Cache file contents appropriately.

**Cache Strategy:**
```python
from functools import lru_cache
from pathlib import Path

@lru_cache(maxsize=32)
def read_config(path: str) -> dict:
    return json.loads(Path(path).read_text())
```

**When to Cache:**
- Configuration files (rarely change)
- Static reference data
- Parsed YAML/JSON

**When NOT to Cache:**
- User-generated content
- Files modified during session
- Large binary files

### FA-003: Selective Reading

Read only necessary portions.

**Frontmatter Extraction:**
```python
def read_frontmatter(path: Path) -> dict:
    content = path.read_text()
    if content.startswith('---'):
        end = content.find('---', 3)
        return yaml.safe_load(content[3:end])
    return {}
```

**Incremental Reading:**
```python
def read_first_n_lines(path: Path, n: int = 50) -> str:
    with open(path) as f:
        return ''.join(f.readline() for _ in range(n))
```

### FA-004: Efficient Glob Patterns

Use specific patterns over wildcards.

**Pattern Specificity:**
```python
# Good: Specific pattern
list(project_dir.glob("skills/pop-*/SKILL.md"))

# Bad: Overly broad
list(project_dir.rglob("*.md"))
```

**Exclusions:**
```python
def safe_glob(pattern: str) -> list:
    results = []
    for path in project_dir.rglob(pattern):
        if "node_modules" not in str(path):
            if "__pycache__" not in str(path):
                results.append(path)
    return results
```

### FA-005: Grep Efficiency

Optimize search operations.

**File Type Filtering:**
```bash
# Good: Filter by type
rg "pattern" --type py --type ts

# Bad: Search everything
rg "pattern"
```

**Early Termination:**
```python
def find_first_match(pattern: str, files: list) -> str:
    for file in files:
        content = file.read_text()
        if pattern in content:
            return str(file)  # Stop after first match
    return None
```

### FA-006: Recursive Operation Control

Limit recursive operations.

**Depth Limits:**
```python
def limited_walk(root: Path, max_depth: int = 3):
    def walk(path: Path, depth: int):
        if depth > max_depth:
            return
        yield path
        if path.is_dir():
            for child in path.iterdir():
                yield from walk(child, depth + 1)

    yield from walk(root, 0)
```

**Exclusion Patterns:**
```python
EXCLUDE_DIRS = {
    'node_modules', '__pycache__', '.git',
    'dist', 'build', 'coverage', '.next'
}

def should_process(path: Path) -> bool:
    return not any(excl in path.parts for excl in EXCLUDE_DIRS)
```

### FA-007: Write Batching

Combine related write operations.

**Batch Pattern:**
```python
class BatchWriter:
    def __init__(self):
        self.pending = {}

    def queue(self, path: str, content: str):
        self.pending[path] = content

    def flush(self):
        for path, content in self.pending.items():
            Path(path).write_text(content)
        self.pending.clear()
```

**Atomic Writes:**
```python
import tempfile
import shutil

def atomic_write(path: Path, content: str):
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write(content)
        temp_path = f.name
    shutil.move(temp_path, path)
```

### FA-008: State File Management

Efficient state persistence.

**Single State File:**
```python
# Good: One state file
STATE_FILE = ".popkit/state.json"

def save_state(state: dict):
    Path(STATE_FILE).write_text(json.dumps(state, indent=2))

# Bad: Multiple small files
def save_state(state: dict):
    for key, value in state.items():
        Path(f".popkit/{key}.json").write_text(json.dumps(value))
```

**Cleanup:**
```python
def cleanup_temp_files(age_hours: int = 24):
    import time
    cutoff = time.time() - (age_hours * 3600)

    for temp_file in Path(".popkit/temp").glob("*"):
        if temp_file.stat().st_mtime < cutoff:
            temp_file.unlink()
```

## Anti-Patterns

### Read in Loop
```python
# Bad
for item in items:
    config = read_config()  # Reads same file N times
    process(item, config)

# Good
config = read_config()  # Read once
for item in items:
    process(item, config)
```

### Unbounded Glob
```python
# Bad
all_files = list(Path('.').rglob('*'))

# Good
py_files = list(Path('src').glob('**/*.py'))
```

## Quality Metrics

| Metric | Target | Description |
|--------|--------|-------------|
| Reads/operation | <5 | Average file reads |
| Cache hit rate | >80% | Config cache effectiveness |
| Glob scope | Limited | No unbounded rglob |
| Write batching | Yes | Related writes combined |
