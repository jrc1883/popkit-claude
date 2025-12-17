# Separation of Concerns Standards

Standards for maintaining clear boundaries and responsibilities in code.

## Core Principles

### SOC-001: Single Responsibility

Each module/class should have one, and only one, reason to change.

**Definition:**
A responsibility is a reason to change. When requirements change, only one class should need modification.

**Indicators of Violation:**
- Class handles multiple domains (user + payment + notification)
- File exceeds 300 lines
- Multiple unrelated imports
- "Manager" or "Handler" suffix doing too much

**Compliance Check:**
- [ ] Each class has a clear, single purpose
- [ ] Classes under 300 lines
- [ ] Method count under 15 per class
- [ ] Cohesive imports (same domain)

### SOC-002: Vertical Slicing

Organize code by feature, not by technical layer alone.

**Feature-Based Structure:**
```
src/
├── users/
│   ├── user.entity.ts
│   ├── user.repository.ts
│   ├── user.service.ts
│   └── user.controller.ts
├── orders/
│   ├── order.entity.ts
│   ├── order.repository.ts
│   └── ...
```

**vs Layer-Based (avoid for large projects):**
```
src/
├── entities/       # All entities together
├── repositories/   # All repositories together
├── services/       # All services together
└── controllers/    # All controllers together
```

**Compliance Check:**
- [ ] Related code grouped together
- [ ] Features can be developed independently
- [ ] Minimal cross-feature dependencies

### SOC-003: Presentation Separation

UI/presentation logic separate from business logic.

**Layers:**
1. **View Layer** - Display and user interaction
2. **ViewModel/Presenter** - Presentation logic
3. **Business Layer** - Domain rules

**Compliance Check:**
- [ ] No business logic in UI components
- [ ] Formatting done in presentation layer
- [ ] Business rules testable without UI

### SOC-004: Data Access Separation

Data access isolated from business logic.

**Pattern:** Repository Pattern

```typescript
// Interface in domain layer
interface UserRepository {
  findById(id: string): Promise<User | null>;
  save(user: User): Promise<void>;
}

// Implementation in infrastructure layer
class PrismaUserRepository implements UserRepository {
  async findById(id: string) {
    return this.prisma.user.findUnique({ where: { id } });
  }
}
```

**Compliance Check:**
- [ ] Business logic doesn't contain SQL/queries
- [ ] Repository interfaces defined abstractly
- [ ] Easy to swap data sources

### SOC-005: Cross-Cutting Concerns

Extract concerns that span multiple modules.

**Cross-Cutting Examples:**
- Logging
- Authentication
- Caching
- Error handling
- Validation

**Implementation Patterns:**
- Middleware (for HTTP)
- Decorators (for classes/methods)
- Aspect-Oriented Programming
- Interceptors

**Compliance Check:**
- [ ] Logging not scattered in business code
- [ ] Auth handled by middleware/decorators
- [ ] Error handling centralized
- [ ] Caching abstracted

### SOC-006: Configuration Separation

Configuration separate from code.

**Levels:**
1. **Environment** - `.env`, environment variables
2. **Application** - `config.ts`, `settings.py`
3. **Feature** - Feature flags, toggles

**Compliance Check:**
- [ ] No hardcoded secrets
- [ ] Environment-specific config in env vars
- [ ] Config loaded at startup, not runtime
- [ ] Sensible defaults for development

### SOC-007: Test Separation

Test code separate from production code.

**Structure:**
```
src/
├── users/
│   ├── user.service.ts
│   └── user.service.test.ts    # Co-located tests
tests/
├── integration/
│   └── user-flow.test.ts       # Integration tests
└── e2e/
    └── user-registration.test.ts
```

**Compliance Check:**
- [ ] Test code not bundled in production
- [ ] Test utilities separate from production
- [ ] Mocks/fixtures organized
- [ ] Test data isolated

### SOC-008: Interface Separation

Interfaces specific to clients that use them.

**ISP Principle:**
No client should depend on methods it doesn't use.

```typescript
// Bad: Fat interface
interface UserService {
  createUser(data: CreateUserData): User;
  deleteUser(id: string): void;
  getUserAnalytics(id: string): Analytics;
  sendUserNotification(id: string, message: string): void;
}

// Good: Segregated interfaces
interface UserCreator {
  createUser(data: CreateUserData): User;
}

interface UserDeleter {
  deleteUser(id: string): void;
}

interface UserAnalytics {
  getUserAnalytics(id: string): Analytics;
}
```

**Compliance Check:**
- [ ] Interfaces are small and focused
- [ ] Clients only depend on what they use
- [ ] No "god interfaces"

## Module Boundary Guidelines

### Clear Boundaries

Each module should:
1. Export a public API
2. Hide implementation details
3. Define clear dependencies
4. Have minimal surface area

**Example:**
```typescript
// users/index.ts (public API)
export { UserService } from './user.service';
export type { User, CreateUserData } from './types';

// Internal - not exported
// user.repository.ts
// user.mapper.ts
```

### Dependency Direction

```
High-level modules ← Low-level modules
   (abstract)         (concrete)
```

**Allowed:**
- Service → Repository interface
- Controller → Service
- Use Case → Entity

**Not Allowed:**
- Entity → Service
- Repository → Controller
- Low-level → High-level

### Communication Patterns

| Pattern | Use When | Example |
|---------|----------|---------|
| Direct Call | Same module | service.createUser() |
| Interface | Cross-module | IUserService |
| Events | Loose coupling | userCreated event |
| Message Queue | Async/distributed | Pub/sub |

## Anti-Patterns

### Mixing Concerns

```typescript
// BAD: Controller with business logic
class UserController {
  async createUser(req, res) {
    // Validation
    if (!req.body.email.includes('@')) {
      return res.status(400).send('Invalid email');
    }

    // Business logic
    const existingUser = await db.user.findUnique({
      where: { email: req.body.email }
    });

    if (existingUser) {
      return res.status(409).send('Email exists');
    }

    // Data access
    const user = await db.user.create({
      data: req.body
    });

    // Response formatting
    res.status(201).json({
      id: user.id,
      email: user.email,
      createdAt: user.createdAt.toISOString()
    });
  }
}
```

### Proper Separation

```typescript
// GOOD: Separated concerns
class UserController {
  constructor(private userService: UserService) {}

  async createUser(req, res) {
    const result = await this.userService.createUser(req.body);
    res.status(201).json(UserPresenter.toResponse(result));
  }
}

class UserService {
  constructor(private userRepo: UserRepository) {}

  async createUser(data: CreateUserData): Promise<User> {
    await this.validateUniqueEmail(data.email);
    return this.userRepo.save(User.create(data));
  }
}
```

## Quality Metrics

| Metric | Target | Description |
|--------|--------|-------------|
| Module size | <500 lines | Per module/class |
| Method count | <15 per class | Public methods |
| Dependencies | <7 per module | External dependencies |
| Cyclomatic complexity | <10 | Per method |
| Coupling | Low | Between modules |
| Cohesion | High | Within modules |
