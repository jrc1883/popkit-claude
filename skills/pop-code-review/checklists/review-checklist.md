# Code Review Checklist

Use this checklist during code reviews. Each item has a confidence threshold - only report issues where you're confident they are genuine problems.

## Pre-Review Setup

- [ ] Identified the scope (staged, branch diff, commit range, or specific files)
- [ ] Have context on what the code is supposed to do
- [ ] Understand the project's conventions and patterns

---

## 1. Simplicity / DRY / Elegance (Threshold: 80+)

### Code Duplication
- [ ] No copy-pasted code blocks that should be functions
- [ ] No repeated logic that should be abstracted
- [ ] No duplicate constants/strings that should be variables

### Unnecessary Complexity
- [ ] No over-engineering for hypothetical requirements
- [ ] No premature optimization
- [ ] No "clever" code that's hard to understand
- [ ] Control flow is straightforward (no deeply nested conditionals)

### Appropriate Abstractions
- [ ] Functions/methods are single-purpose
- [ ] Classes have clear responsibilities
- [ ] No god objects or mega-functions
- [ ] Appropriate use of inheritance vs composition

### Readability
- [ ] Code is self-documenting where possible
- [ ] Comments explain "why" not "what"
- [ ] Names are descriptive and consistent
- [ ] Magic numbers are replaced with named constants

---

## 2. Bugs / Correctness (Threshold: 85+)

### Logic Errors
- [ ] Conditional logic is correct (no inverted conditions)
- [ ] Loop boundaries are correct (no off-by-one errors)
- [ ] Boolean expressions are correct (De Morgan's law violations)
- [ ] Comparison operators are correct (`==` vs `===`, `<` vs `<=`)

### Edge Cases
- [ ] Empty collections handled correctly
- [ ] Null/undefined handled correctly
- [ ] Zero/negative numbers handled correctly
- [ ] Empty strings handled correctly
- [ ] Boundary conditions handled correctly

### Type Safety
- [ ] Types are correct and specific (not `any`)
- [ ] Type guards used where needed
- [ ] Nullable types handled safely
- [ ] Generic types constrained appropriately

### Error Handling
- [ ] Errors are caught at appropriate boundaries
- [ ] Error messages are helpful
- [ ] Resources are cleaned up in error paths
- [ ] Async errors are handled (no unhandled rejections)

### State Management
- [ ] Mutable state is minimized
- [ ] State updates are atomic where needed
- [ ] Race conditions are prevented
- [ ] State is initialized correctly

---

## 3. Conventions / Patterns (Threshold: 75+)

### Project Patterns
- [ ] Follows existing patterns in codebase
- [ ] Uses project's preferred libraries/utilities
- [ ] File organization matches project structure
- [ ] Module boundaries respected

### Naming Conventions
- [ ] Consistent casing (camelCase, PascalCase, snake_case)
- [ ] Naming follows project conventions
- [ ] Boolean names start with is/has/should/can
- [ ] Functions named with verbs, classes with nouns

### Import Organization
- [ ] Imports organized consistently
- [ ] No circular dependencies
- [ ] No unused imports
- [ ] Barrel imports used appropriately

### API Design
- [ ] Function signatures are intuitive
- [ ] Return types are consistent
- [ ] Error returns vs exceptions consistent with project
- [ ] Optional parameters have sensible defaults

---

## 4. Security (Threshold: 90+)

### Input Validation
- [ ] User input is validated
- [ ] Data is sanitized before use
- [ ] No SQL/NoSQL injection vulnerabilities
- [ ] No command injection vulnerabilities

### Authentication/Authorization
- [ ] Auth checks are present where needed
- [ ] Permissions are verified
- [ ] Sensitive data is protected
- [ ] No hardcoded credentials

### Data Handling
- [ ] Sensitive data is not logged
- [ ] Data is encrypted where appropriate
- [ ] PII is handled correctly
- [ ] No exposure of internal errors to users

---

## 5. Performance (Threshold: 70+)

### Algorithmic Efficiency
- [ ] No unnecessary O(n²) or worse algorithms
- [ ] No repeated expensive operations in loops
- [ ] Appropriate data structures used
- [ ] Pagination used for large datasets

### Resource Management
- [ ] Database connections/handles closed
- [ ] Files are closed after use
- [ ] Subscriptions are unsubscribed
- [ ] Event listeners are removed

### Caching
- [ ] Expensive computations are cached where appropriate
- [ ] Cache invalidation is handled correctly
- [ ] No cache stampede vulnerabilities

---

## 6. Testing (Threshold: 80+)

### Test Coverage
- [ ] New code has tests
- [ ] Edge cases are tested
- [ ] Error paths are tested
- [ ] Integration points are tested

### Test Quality
- [ ] Tests are deterministic
- [ ] Tests are isolated
- [ ] Test names are descriptive
- [ ] Assertions are meaningful

---

## Confidence Scoring Guide

| Score | When to Use |
|-------|-------------|
| 100 | Certain bug/vulnerability, can prove it's wrong |
| 90 | Very confident, clear violation of best practice |
| 80 | Confident, this should be changed |
| 70 | Likely issue, worth mentioning |
| 60 | Possible issue, reviewer discretion |
| 50 | Uncertain, needs more context |
| <50 | Probably not a real issue, don't report |

## Filter Rules

**Report (80+):**
- Critical security vulnerabilities
- Obvious bugs
- Clear pattern violations
- Significant performance issues

**Skip (<80):**
- Pre-existing issues not from this change
- Linter-catchable issues
- Personal style preferences
- Hypothetical edge cases unlikely to occur
