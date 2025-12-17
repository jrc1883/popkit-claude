# Clean Architecture Standards

Standards for implementing clean architecture principles in PopKit projects.

## Core Principles

### CA-001: Dependency Rule

Dependencies must point inward toward higher-level policies.

```
Outer layers → Inner layers (allowed)
Inner layers → Outer layers (FORBIDDEN)
```

**Layers (outside to inside):**
1. Frameworks & Drivers (UI, DB, Web)
2. Interface Adapters (Controllers, Gateways)
3. Application Business Rules (Use Cases)
4. Enterprise Business Rules (Entities)

**Compliance Check:**
- [ ] No direct imports from outer to inner layers
- [ ] Dependencies inverted through interfaces
- [ ] Framework code isolated to outer ring

### CA-002: Independence from Frameworks

The architecture should not depend on frameworks.

**Requirements:**
- Business logic must work without framework imports
- Framework-specific code isolated to adapters
- Easy to swap frameworks without core changes

**Compliance Check:**
- [ ] Business logic has no framework imports
- [ ] Core entities are plain objects
- [ ] Framework adapters are thin wrappers

### CA-003: Independence from UI

The UI can change without affecting business rules.

**Requirements:**
- Use cases define application behavior
- UI is just a delivery mechanism
- Multiple UIs can use same business logic

**Compliance Check:**
- [ ] Use cases don't reference UI components
- [ ] Business logic testable without UI
- [ ] Clear separation between presentation and domain

### CA-004: Independence from Database

Business rules don't know about database schema.

**Requirements:**
- Entities don't contain SQL/queries
- Repository interfaces in domain layer
- Implementations in infrastructure layer

**Compliance Check:**
- [ ] Domain entities have no DB annotations
- [ ] Repository interfaces are abstract
- [ ] Database operations isolated to gateways

### CA-005: Independence from External Services

Business rules isolated from external APIs.

**Requirements:**
- External APIs accessed through gateways
- Gateway interfaces defined in use case layer
- Implementations in infrastructure layer

**Compliance Check:**
- [ ] External API calls go through gateways
- [ ] Gateway contracts defined abstractly
- [ ] Easy to mock external services

## Layer Structure

### Entities (Core)

```
src/domain/entities/
├── user.ts           # Core business entity
├── order.ts          # Core business entity
└── index.ts          # Barrel export
```

**Rules:**
- Pure business logic only
- No dependencies on other layers
- Framework-agnostic

### Use Cases (Application)

```
src/application/use-cases/
├── create-user.ts    # Application-specific business rule
├── process-order.ts  # Application-specific business rule
└── index.ts          # Barrel export
```

**Rules:**
- Orchestrate entity interactions
- Define input/output boundaries
- No framework dependencies

### Interface Adapters

```
src/adapters/
├── controllers/      # HTTP/REST controllers
├── presenters/       # Response formatters
├── gateways/         # External service implementations
└── repositories/     # Database implementations
```

**Rules:**
- Convert data between formats
- Implement abstract interfaces
- Connect use cases to external world

### Frameworks & Drivers

```
src/infrastructure/
├── web/              # Express/Fastify setup
├── database/         # ORM/Query builder setup
└── config/           # Environment configuration
```

**Rules:**
- Glue code only
- Minimal business logic
- Framework-specific implementations

## Dependency Direction Validation

### Valid Import Patterns

```typescript
// Entity importing nothing (core)
// entity.ts
export class User { ... }

// Use case importing entity
// create-user.ts
import { User } from '../entities/user';

// Controller importing use case
// user-controller.ts
import { CreateUser } from '../../application/use-cases/create-user';

// Infrastructure importing adapters
// server.ts
import { UserController } from '../adapters/controllers/user-controller';
```

### Invalid Import Patterns

```typescript
// WRONG: Entity importing use case
// entity.ts
import { CreateUser } from '../application/create-user'; // ❌

// WRONG: Use case importing controller
// create-user.ts
import { UserController } from '../adapters/controllers'; // ❌

// WRONG: Domain importing infrastructure
// user.ts
import { prisma } from '../infrastructure/database'; // ❌
```

## Testing Strategy

### Unit Tests (Inner Layers)

```typescript
// Test entities in isolation
describe('User', () => {
  it('validates email format', () => {
    expect(() => new User({ email: 'invalid' })).toThrow();
  });
});

// Test use cases with mocked repositories
describe('CreateUser', () => {
  it('creates user with valid data', async () => {
    const mockRepo = { save: jest.fn() };
    const useCase = new CreateUser(mockRepo);
    // ...
  });
});
```

### Integration Tests (Adapters)

```typescript
// Test controllers with real use cases, mocked DB
describe('UserController', () => {
  it('handles POST /users', async () => {
    const response = await request(app)
      .post('/users')
      .send({ email: 'test@example.com' });
    // ...
  });
});
```

### E2E Tests (Full Stack)

```typescript
// Test complete flows
describe('User Registration', () => {
  it('registers and activates user', async () => {
    // Full flow with real database
  });
});
```

## Migration Guide

### From Monolithic to Clean Architecture

1. **Identify Entities** - Extract pure business objects
2. **Define Use Cases** - Extract business operations
3. **Create Interfaces** - Define boundaries
4. **Implement Adapters** - Wrap framework code
5. **Invert Dependencies** - Apply DIP

### Common Refactoring Patterns

| From | To | Pattern |
|------|-----|---------|
| Direct DB calls in handlers | Repository pattern | Extract interface |
| Framework entities | Domain entities | Separate models |
| Mixed concerns in controllers | Use case extraction | Single responsibility |
| Hardcoded external calls | Gateway pattern | Dependency injection |

## Quality Metrics

| Metric | Target | Tool |
|--------|--------|------|
| Layer violations | 0 | detect_patterns.py |
| Test coverage (domain) | >90% | Coverage tools |
| Cyclomatic complexity | <10 | Complexity analyzers |
| Dependencies (inward) | 100% | Import analysis |
