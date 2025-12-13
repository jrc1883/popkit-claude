---
description: "[add|remove|refresh|switch|discover] - Multi-project management"
argument-hint: "<subcommand> [path]"
---

# /popkit:dashboard - Multi-Project Dashboard

Unified view for managing multiple PopKit-enabled projects. Shows health scores, activity status, and enables quick context switching.

## Usage

```
/popkit:dashboard                    # Show dashboard
/popkit:dashboard add <path>         # Add project to registry
/popkit:dashboard remove <name>      # Remove project from registry
/popkit:dashboard refresh [name]     # Refresh health scores
/popkit:dashboard switch <name>      # Switch to project
/popkit:dashboard discover           # Auto-discover projects
```

## Subcommands

| Subcommand | Description |
|------------|-------------|
| (default) | Display the multi-project dashboard |
| `add <path>` | Register a project in the global registry |
| `remove <name>` | Remove a project from the registry |
| `refresh [name]` | Recalculate health scores (all or specific) |
| `switch <name>` | Change working context to a different project |
| `discover` | Auto-discover projects in common locations |

---

## Default: Show Dashboard

Display the full dashboard with all registered projects.

### Instructions

1. **Load the project registry:**
   ```python
   from project_registry import list_projects, format_dashboard

   projects = list_projects()
   print(format_dashboard(projects))
   ```

2. **Display summary statistics:**
   - Total projects registered
   - Healthy (80+), Warning (60-79), Critical (<60), Unknown

3. **Show project table:**
   | Project | Health | Issues | Last Active |
   |---------|--------|--------|-------------|
   | popkit | 92 | 5 | 2 min ago |

4. **Highlight projects needing attention:**
   ```python
   from project_registry import get_unhealthy_projects

   unhealthy = get_unhealthy_projects(threshold=70)
   if unhealthy:
       print("Projects needing attention:")
       for p in unhealthy:
           print(f"  ! {p['name']}: {p['healthScore']}")
   ```

5. **Present quick actions:**
   ```
   Use AskUserQuestion tool with:
   - question: "What would you like to do?"
   - header: "Action"
   - options:
     - label: "Switch project"
       description: "Change to a different project"
     - label: "Refresh health scores"
       description: "Recalculate all health scores"
     - label: "Add project"
       description: "Register a new project"
   - multiSelect: false
   ```

---

## Add Project

Register a new project in the global registry.

```
/popkit:dashboard add /path/to/project
/popkit:dashboard add .                   # Current directory
/popkit:dashboard add . --tags active,client
```

### Instructions

1. **Validate the path:**
   ```python
   from project_registry import detect_project_info

   info = detect_project_info(path)
   if not info:
       print("Error: Not a valid project directory")
       return
   ```

2. **Add to registry:**
   ```python
   from project_registry import add_project

   success, message = add_project(path, tags=tags_list)
   print(message)
   ```

3. **Calculate initial health score:**
   ```python
   from health_calculator import calculate_quick_health
   from project_registry import update_health_score

   score = calculate_quick_health(path)
   update_health_score(info['name'], score)
   ```

4. **Report result:**
   ```
   Added project: popkit
   Path: /Users/dev/popkit
   Health: 92/100
   Tags: active
   ```

### Flags

| Flag | Description |
|------|-------------|
| `--tags <tags>` | Comma-separated tags to apply |

---

## Remove Project

Remove a project from the registry (does not delete files).

```
/popkit:dashboard remove project-name
```

### Instructions

1. **Confirm removal:**
   ```
   Use AskUserQuestion tool with:
   - question: "Remove 'project-name' from dashboard? (Files will not be deleted)"
   - header: "Confirm"
   - options:
     - label: "Yes, remove"
       description: "Unregister from dashboard"
     - label: "Cancel"
       description: "Keep the project registered"
   - multiSelect: false
   ```

2. **Remove from registry:**
   ```python
   from project_registry import remove_project

   success, message = remove_project(identifier)
   print(message)
   ```

---

## Refresh Health Scores

Recalculate health scores for all or specific projects.

```
/popkit:dashboard refresh           # Refresh all projects
/popkit:dashboard refresh popkit    # Refresh specific project
/popkit:dashboard refresh --quick   # Quick refresh (git + activity only)
```

### Instructions

1. **Determine scope:**
   - If project name provided, refresh only that project
   - Otherwise, refresh all registered projects

2. **Calculate health scores:**
   ```python
   from project_registry import list_projects, update_health_score
   from health_calculator import calculate_health_score, calculate_quick_health

   for project in projects_to_refresh:
       if quick_mode:
           score = calculate_quick_health(project['path'])
       else:
           result = calculate_health_score(project['path'])
           score = result['score']

       update_health_score(project['name'], score)
       print(f"{project['name']}: {score}/100")
   ```

3. **Show results summary:**
   ```
   Health Refresh Complete
   -----------------------
   popkit:           92 (+2)
   popkit-cloud:     78 (-3)
   reseller-central: 88 (=)
   ```

### Flags

| Flag | Description |
|------|-------------|
| `--quick` | Quick refresh (git + activity only, faster) |
| `--full` | Full refresh including build and tests (slower) |

---

## Switch Project

Change working context to a different project.

```
/popkit:dashboard switch project-name
```

### Instructions

1. **If no project specified, show selection:**
   ```
   Use AskUserQuestion tool with:
   - question: "Which project would you like to switch to?"
   - header: "Switch"
   - options:
     - label: "popkit"
       description: "Health: 92 | Last: 2 min ago"
     - label: "popkit-cloud"
       description: "Health: 78 | Last: 1 hour ago"
     - label: "reseller-central"
       description: "Health: 88 | Last: 3 days ago"
   - multiSelect: false
   ```

2. **Get project info:**
   ```python
   from project_registry import get_project, touch_project

   project = get_project(identifier)
   if not project:
       print(f"Project not found: {identifier}")
       return
   ```

3. **Update activity and report:**
   ```python
   touch_project(project['path'])

   print(f"Switched to: {project['name']}")
   print(f"Path: {project['path']}")
   print(f"Health: {project['healthScore']}/100")
   ```

4. **Suggest next action:**
   ```
   Use AskUserQuestion tool with:
   - question: "What would you like to do in this project?"
   - header: "Action"
   - options:
     - label: "Morning routine"
       description: "Run health check for this project"
     - label: "See open issues"
       description: "View GitHub issues"
     - label: "Start development"
       description: "Run /popkit:dev workflow"
   - multiSelect: false
   ```

---

## Discover Projects

Auto-discover projects in common development directories.

```
/popkit:dashboard discover
/popkit:dashboard discover ~/projects ~/work
```

### Instructions

1. **Search for projects:**
   ```python
   from project_registry import discover_projects

   # Default: ~/projects, ~/dev, ~/code, ~/workspace
   discovered = discover_projects(search_dirs)
   ```

2. **Show discovered projects:**
   ```
   Discovered 5 projects:
     popkit           /Users/dev/projects/popkit
     my-app           /Users/dev/projects/my-app
     client-website   /Users/dev/work/client-website
   ```

3. **Prompt for registration:**
   ```
   Use AskUserQuestion tool with:
   - question: "Add discovered projects to dashboard?"
   - header: "Register"
   - options:
     - label: "Add all (5)"
       description: "Register all discovered projects"
     - label: "Select individually"
       description: "Choose which projects to add"
     - label: "Cancel"
       description: "Don't add any projects"
   - multiSelect: false
   ```

4. **Register selected projects:**
   ```python
   from project_registry import add_project

   for project in projects_to_add:
       add_project(project['path'])
   ```

---

## Health Score Components

Health scores are calculated from 5 components (20 points each):

| Component | Max | Criteria |
|-----------|-----|----------|
| **Git Status** | 20 | Clean tree (+20), uncommitted (-5/10 files) |
| **Build Status** | 20 | Passed (+20), warnings (-2 each), failed (0) |
| **Test Coverage** | 20 | >80% (+20), 60-80% (+15), <60% (+10) |
| **Issue Health** | 20 | No stale (+20), -2 per stale (>30 days) |
| **Activity** | 20 | Today (+20), week (+15), month (+10) |

---

## Related

- `pop-dashboard` skill - Core implementation
- `/popkit:routine morning` - Single-project health check
- `/popkit:next` - Context-aware recommendations
- `hooks/utils/project_registry.py` - Registry operations
- `hooks/utils/health_calculator.py` - Health calculation
