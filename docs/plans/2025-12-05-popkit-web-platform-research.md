# PopKit Web Platform - Research & Feasibility Study

**Date:** December 5, 2025
**Status:** Research Complete - Awaiting Review
**Scope:** Multi-phase epic for model-agnostic web-based development orchestration

---

## Executive Summary

This document explores the feasibility of transforming PopKit from a Claude Code plugin into a **web-based project command center** that orchestrates multiple AI coding assistants (Claude Code, OpenAI Codex CLI, Google Gemini CLI) through a unified interface.

**Key Finding:** This is technically feasible and well-timed. The ecosystem has converged on:
- **MCP (Model Context Protocol)** as a universal tool interface (adopted by Anthropic, OpenAI, Google)
- **Standardized CLI patterns** across all major AI coding tools
- **Mature web terminal technology** (xterm.js powers VS Code, Replit, JupyterLab)

The differentiation: PopKit's **workflow orchestration layer** (agents, skills, Power Mode) becomes the value-add over raw CLI access.

---

## Table of Contents

1. [Vision](#1-vision)
2. [Market Landscape](#2-market-landscape)
3. [Technical Architecture](#3-technical-architecture)
4. [Model-Agnostic Abstraction Layer](#4-model-agnostic-abstraction-layer)
5. [Implementation Phases](#5-implementation-phases)
6. [Business Model Considerations](#6-business-model-considerations)
7. [Risks & Challenges](#7-risks--challenges)
8. [Competitive Analysis](#8-competitive-analysis)
9. [Next Steps](#9-next-steps)
10. [References](#10-references)

---

## 1. Vision

### 1.1 What We're Building

**PopKit Web** - A browser-based "Project Command Center" that:

1. **Manages multiple AI coding sessions** across different projects
2. **Orchestrates workflows** using PopKit's existing agent/skill/command architecture
3. **Supports multiple AI backends** (Claude Code, Codex CLI, Gemini CLI)
4. **Provides programmatic control** over AI coding assistants
5. **Offers team collaboration** features (shared projects, session handoffs)

### 1.2 What This Is NOT

- **Not just a web terminal** - We're not rebuilding ttyd or WebSSH
- **Not a cloud IDE** - We're not competing with Replit/Codespaces for editing
- **Not an AI wrapper** - We're not building ChatGPT with a terminal
- **The orchestration layer is the product** - PopKit's agents, skills, and workflows are the value

### 1.3 Core Value Proposition

```
Raw CLI Tools                    PopKit Web
─────────────                    ─────────────
Claude Code CLI ──┐              ┌───────────────────────────────┐
                  │              │  Unified Workflow Interface    │
Codex CLI ────────┼──► MCP ──►  │  • Multi-project management    │
                  │              │  • Agent orchestration         │
Gemini CLI ───────┘              │  • Power Mode collaboration   │
                                 │  • Session continuity          │
                                 │  • Quality gates               │
                                 └───────────────────────────────┘
```

### 1.4 Why Now?

| Factor | Evidence |
|--------|----------|
| **Claude Code web launched** | Nov 2025 - Anthropic validated browser-based AI coding |
| **MCP universal adoption** | OpenAI adopted MCP in March 2025; Google supports it |
| **CLI convergence** | All major providers now have open-source CLI tools |
| **PopKit maturity** | v0.9.8 with Power Mode, agents, quality gates ready |

---

## 2. Market Landscape

### 2.1 AI Coding CLI Tools (As of Dec 2025)

| Tool | Provider | Model | Open Source | MCP Support |
|------|----------|-------|-------------|-------------|
| **Claude Code** | Anthropic | Claude Opus/Sonnet | No (SDK yes) | Native |
| **Codex CLI** | OpenAI | GPT-5 | Yes | Via adoption |
| **Gemini CLI** | Google | Gemini 3 Pro | Yes (Apache 2.0) | Yes |

**Key Insight:** All three major AI providers now have CLI tools with similar patterns:
- Read/write files locally
- Execute shell commands
- Context window management
- Approval modes for safety

### 2.2 Claude Code Ecosystem

#### Claude Code for Web (Nov 2025)
- Runs on Anthropic-managed infrastructure
- Parallel job execution (multiple sessions)
- Real-time progress tracking
- GitHub integration
- Sandboxed security
- **No local execution** - runs in cloud containers

#### Claude Agent SDK
- Renamed from "Claude Code SDK"
- Subagent architecture for parallelization
- Context isolation between agents
- Long-running agent support via initializer pattern
- MCP tool extensibility

### 2.3 Competitor CLI Comparison

```
┌─────────────────────────────────────────────────────────────────┐
│                    CLI Tool Comparison                          │
├──────────────┬───────────────┬───────────────┬─────────────────┤
│ Feature      │ Claude Code   │ Codex CLI     │ Gemini CLI      │
├──────────────┼───────────────┼───────────────┼─────────────────┤
│ Execution    │ Local + Cloud │ Local only    │ Local only      │
│ Context      │ ~200k tokens  │ Varies by GPT │ 1M tokens       │
│ Multimodal   │ Yes           │ Yes           │ Yes             │
│ Open Source  │ SDK only      │ Full CLI      │ Full CLI        │
│ Free Tier    │ No            │ ChatGPT Plus  │ 1000 req/day    │
│ MCP          │ Native        │ Via adoption  │ Native          │
│ Headless     │ No            │ No            │ Yes             │
│ Custom Cmds  │ Via plugins   │ No            │ Yes (GEMINI.md) │
└──────────────┴───────────────┴───────────────┴─────────────────┘
```

### 2.4 Cloud IDE Landscape

| Platform | Model | Strengths | Limitations |
|----------|-------|-----------|-------------|
| **GitHub Codespaces** | Cloud VMs | GitHub integration | GitHub-only, $0.18/hr |
| **Replit** | Persistent | Social, 50+ languages | Performance at scale |
| **Gitpod/Ona** | Ephemeral | Multi-provider git | No GPU, SaaS only |
| **Coder** | Self-hosted | Enterprise, AI agents | Complex setup |
| **Theia** | Open source | AI-native, vendor-neutral | DIY hosting |

**Gap in Market:** No platform focuses on **orchestrating AI coding tools** as the primary UX.

---

## 3. Technical Architecture

### 3.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         PopKit Web Platform                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                     Web Application (React/Next.js)              │    │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────────┐ │    │
│  │  │ Project Mgr  │ │ Session View │ │ Workflow Orchestrator    │ │    │
│  │  │ • List/CRUD  │ │ • xterm.js   │ │ • Agent routing          │ │    │
│  │  │ • Git repos  │ │ • Real-time  │ │ • Skill invocation       │ │    │
│  │  │ • Settings   │ │ • History    │ │ • Power Mode control     │ │    │
│  │  └──────────────┘ └──────────────┘ └──────────────────────────┘ │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                    │                                     │
│                                    ▼                                     │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                    Orchestration API (Backend)                   │    │
│  │  ┌────────────────────┐  ┌────────────────────────────────────┐ │    │
│  │  │ Session Manager    │  │ Model Abstraction Layer            │ │    │
│  │  │ • WebSocket        │  │ • Provider routing                 │ │    │
│  │  │ • State sync       │  │ • Capability mapping               │ │    │
│  │  │ • Multi-tenant     │  │ • MCP tool normalization           │ │    │
│  │  └────────────────────┘  └────────────────────────────────────┘ │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                    │                                     │
│                                    ▼                                     │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                    Execution Layer                               │    │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐            │    │
│  │  │ Claude Code  │ │ Codex CLI    │ │ Gemini CLI   │            │    │
│  │  │ Container    │ │ Container    │ │ Container    │            │    │
│  │  └──────────────┘ └──────────────┘ └──────────────┘            │    │
│  │                      ▲                                          │    │
│  │                      │                                          │    │
│  │  ┌──────────────────────────────────────────────────────────┐  │    │
│  │  │ Sandboxed File System (per-project)                      │  │    │
│  │  │ • Git clone/sync                                         │  │    │
│  │  │ • Isolated workspace                                     │  │    │
│  │  └──────────────────────────────────────────────────────────┘  │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Key Components

#### 3.2.1 Web Frontend (React/Next.js)

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Terminal UI** | xterm.js | Render AI CLI sessions |
| **Project Manager** | React + ShadCN | CRUD projects, connect repos |
| **Session Grid** | CSS Grid + WebSocket | Multiple parallel sessions |
| **Workflow Panel** | React | PopKit agent/skill controls |
| **Command Palette** | kbar or cmdk | Quick access to /popkit: commands |

#### 3.2.2 Backend API (Node.js/Python)

| Service | Responsibility |
|---------|----------------|
| **Session Manager** | Create/destroy sandboxed environments |
| **WebSocket Gateway** | Real-time terminal I/O streaming |
| **Model Router** | Route requests to appropriate CLI |
| **MCP Bridge** | Normalize tool calls across providers |
| **Auth Service** | User accounts, API key management |
| **Project Store** | Git integration, file persistence |

#### 3.2.3 Execution Layer

**Option A: Containerized CLIs**
```dockerfile
# Example: Claude Code container
FROM node:20-slim
RUN npm install -g @anthropic-ai/claude-code
COPY .claude/ /workspace/.claude/
WORKDIR /workspace
ENTRYPOINT ["claude"]
```

**Option B: Claude Code for Web API** (if exposed)
- Leverage Anthropic's managed infrastructure
- Reduced complexity, but less control

**Option C: Hybrid**
- Use Claude Code for Web when available
- Fall back to containerized CLIs for others

### 3.3 Data Flow

```
User Action                      System Response
───────────                      ───────────────
1. "/popkit:review"        →     Parse command
   (typed in web terminal)

2. Route to agent          →     Load code-reviewer agent config
   (from agents/config.json)

3. Invoke model            →     Select model based on agent.model
                                 (haiku/sonnet/opus)

4. Execute via CLI         →     Send to Claude Code container
                                 (or Codex/Gemini based on project settings)

5. Stream output           →     WebSocket → xterm.js rendering

6. Quality gate            →     Run tsc/build/lint via Bash tool

7. Update status           →     Write to STATUS.json, sync UI
```

---

## 4. Model-Agnostic Abstraction Layer

### 4.1 The Challenge

Each CLI has different:
- Command syntax (`claude`, `codex`, `gemini`)
- Approval modes (auto, manual, etc.)
- Tool naming conventions
- Context window sizes
- Rate limits and pricing

### 4.2 Proposed Abstraction

```typescript
// Universal interface for all AI coding CLIs
interface AICodeAssistant {
  // Identity
  provider: 'anthropic' | 'openai' | 'google';
  model: string;

  // Capabilities
  contextWindow: number;
  supportsMultimodal: boolean;
  supportsMCP: boolean;

  // Session management
  startSession(project: Project): Promise<Session>;
  sendMessage(session: Session, message: string): AsyncIterator<Chunk>;
  cancelSession(session: Session): Promise<void>;

  // Tool execution
  executeTool(tool: MCPTool, args: unknown): Promise<ToolResult>;

  // Configuration
  setApprovalMode(mode: 'auto' | 'confirm' | 'manual'): void;
  setWorkingDirectory(path: string): void;
}

// Provider implementations
class ClaudeCodeAssistant implements AICodeAssistant { ... }
class CodexAssistant implements AICodeAssistant { ... }
class GeminiAssistant implements AICodeAssistant { ... }
```

### 4.3 MCP as the Unifier

MCP provides the standardization layer:

```json
{
  "tool": "file_read",
  "provider_mappings": {
    "claude": { "tool": "Read", "params": { "file_path": "$.path" } },
    "codex": { "tool": "read_file", "params": { "path": "$.path" } },
    "gemini": { "tool": "read", "params": { "file": "$.path" } }
  }
}
```

All providers support MCP, so we can:
1. Define tools in MCP format
2. Let each CLI handle translation
3. Intercept tool calls for PopKit enhancements (quality gates, etc.)

### 4.4 Capability Matrix

```typescript
const CAPABILITY_MATRIX = {
  'claude-code': {
    maxContext: 200_000,
    parallel: true,
    headless: false,
    customCommands: true,  // via plugins
    filePatterns: true,
    approval: ['auto', 'plan', 'manual']
  },
  'codex-cli': {
    maxContext: 128_000,  // GPT-5 varies
    parallel: true,
    headless: false,
    customCommands: false,
    filePatterns: false,
    approval: ['auto', 'suggest', 'manual']
  },
  'gemini-cli': {
    maxContext: 1_000_000,
    parallel: true,
    headless: true,  // Key differentiator
    customCommands: true,  // GEMINI.md
    filePatterns: true,
    approval: ['auto', 'manual']
  }
};
```

### 4.5 PopKit Command Translation

PopKit commands need to translate across CLIs:

| PopKit Command | Claude Code | Codex CLI | Gemini CLI |
|----------------|-------------|-----------|------------|
| `/popkit:review` | Agent + skill invocation | Prompt injection | GEMINI.md custom cmd |
| `/popkit:debug` | bug-whisperer agent | "Debug this" prompt | Custom command |
| `/popkit:morning` | Skill execution | N/A (no equivalent) | Checkpoints |

**Strategy:**
- Tier 1: Works on all CLIs (core functionality)
- Tier 2: Enhanced on Claude Code (full agent support)
- Tier 3: Degraded gracefully on limited CLIs

---

## 5. Implementation Phases

### Phase 0: Foundation (4-6 weeks)
**Goal:** Validate core architecture

- [ ] Web terminal POC with xterm.js + WebSocket
- [ ] Single-model support (Claude Code only)
- [ ] Basic project management (git clone, workspace)
- [ ] Authentication scaffolding
- [ ] PopKit plugin loading in container

**Deliverable:** Working prototype with one project, one session

### Phase 1: Multi-Session Support (4-6 weeks)
**Goal:** Parallel session management

- [ ] Session grid UI (2x2, 3x3 layouts)
- [ ] Independent session state
- [ ] Power Mode integration (Redis or file-based)
- [ ] Session persistence (STATUS.json sync)
- [ ] Quality gate hooks

**Deliverable:** Run multiple Claude Code sessions on same project

### Phase 2: Model Abstraction Layer (6-8 weeks)
**Goal:** Support Codex CLI and Gemini CLI

- [ ] Abstract AI assistant interface
- [ ] Codex CLI container + integration
- [ ] Gemini CLI container + integration
- [ ] MCP tool normalization
- [ ] Capability-aware routing

**Deliverable:** Switch between Claude/Codex/Gemini per project

### Phase 3: Workflow Orchestration (6-8 weeks)
**Goal:** Full PopKit power in web

- [ ] Agent routing from web UI
- [ ] Skill invocation UI
- [ ] Custom command support
- [ ] Morning/nightly routines
- [ ] Workflow visualization

**Deliverable:** Full `/popkit:*` command parity in browser

### Phase 4: Collaboration Features (4-6 weeks)
**Goal:** Team support

- [ ] Multi-user projects
- [ ] Session sharing/handoff
- [ ] Audit logging
- [ ] Role-based access
- [ ] Org-level settings

**Deliverable:** Team workspace with shared projects

### Phase 5: Enterprise & SaaS (Ongoing)
**Goal:** Production readiness

- [ ] Self-hosted deployment option
- [ ] SSO integration (SAML, OIDC)
- [ ] Usage metering and billing
- [ ] SLA monitoring
- [ ] Compliance (SOC2, GDPR)

**Deliverable:** Commercial offering

---

## 6. Business Model Considerations

### 6.1 Potential Models

| Model | Description | Pros | Cons |
|-------|-------------|------|------|
| **Open Core** | Core free, premium features paid | Community growth | Support burden |
| **SaaS** | Hosted service, subscription | Recurring revenue | Infrastructure costs |
| **Enterprise** | On-prem/private cloud | High margins | Sales complexity |
| **Marketplace** | Skills/agents store | Network effects | Quality control |

### 6.2 Pricing Considerations

```
Free Tier:
├── 1 project
├── 1 concurrent session
├── Claude Code only
└── Community support

Pro ($29/mo):
├── 5 projects
├── 3 concurrent sessions
├── All AI providers
├── Power Mode
└── Email support

Team ($99/mo per seat):
├── Unlimited projects
├── 10 concurrent sessions
├── Collaboration features
├── SSO/SAML
├── Priority support

Enterprise (Custom):
├── Self-hosted option
├── Custom agents/skills
├── Dedicated support
├── SLA guarantees
└── Compliance packages
```

### 6.3 Cost Structure

| Cost Center | Estimate | Notes |
|-------------|----------|-------|
| **Compute** | $0.10-0.50/session/hr | Containerized CLIs |
| **Storage** | $0.02/GB/mo | Git repos, session state |
| **AI API** | Pass-through + markup | User's API keys preferred |
| **Infrastructure** | $500-2000/mo base | K8s, Redis, Postgres |

---

## 7. Risks & Challenges

### 7.1 Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **CLI tools change APIs** | High | Medium | Abstract aggressively, version pin |
| **Container security** | Medium | High | Sandboxing, no network by default |
| **WebSocket scaling** | Medium | Medium | Redis pub/sub, horizontal scale |
| **Context window limits** | Low | Medium | Smart summarization, session splitting |

### 7.2 Business Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Anthropic builds this** | High | Critical | Differentiate with multi-model |
| **Pricing pressure** | Medium | Medium | Focus on orchestration value |
| **User adoption** | Medium | High | Start with PopKit community |
| **Support burden** | High | Medium | Documentation, community forums |

### 7.3 Legal Considerations

- **Terms of Service:** Each CLI has ToS; need to ensure compliance
- **API Key Storage:** Users provide own keys; we don't store/use
- **Code Privacy:** All code stays in user's sandboxed environment
- **Open Source Licensing:** Respect Apache 2.0, MIT terms

---

## 8. Competitive Analysis

### 8.1 Direct Competitors

| Competitor | Focus | PopKit Differentiation |
|------------|-------|------------------------|
| **Claude Code Web** | Single model, Anthropic | Multi-model, workflow orchestration |
| **Codex Web** | OpenAI models | Agent architecture, skills |
| **Cursor** | IDE with AI | CLI-first, programmatic |
| **Continue.dev** | IDE extension | Web-first, standalone |

### 8.2 Indirect Competitors

| Competitor | Overlap | Gap We Fill |
|------------|---------|-------------|
| **Replit** | Web-based dev | Not AI-orchestration focused |
| **Coder** | Cloud workspaces | Limited AI integration |
| **LangChain** | Orchestration | Not developer-facing UI |

### 8.3 Unique Positioning

```
         ┌─────────────────────────────────────────────────┐
         │           PopKit Web Positioning                │
         │                                                 │
   IDE   │                        *Claude Code Web        │
  Focus  │    *Cursor                                     │
         │                 ★ PopKit Web                   │
         │    *Continue                                   │
         │                                                 │
Workflow │                        *Coder                  │
  Focus  │    *LangChain          *Replit                 │
         │                                                 │
         └─────────────────────────────────────────────────┘
              Single Model                    Multi-Model
```

---

## 9. Next Steps

### 9.1 Immediate (This Week)

1. **Review this document** with PopKit analysis
2. **Create GitHub epic** with sub-issues for Phase 0
3. **Technical spike:** xterm.js + WebSocket POC
4. **Decision:** Start with Claude Code only or multi-model from day 1?

### 9.2 Short-Term (30 Days)

1. **Phase 0 kickoff** if approved
2. **Architecture RFC** with detailed decisions
3. **Container security research** (gVisor, Firecracker)
4. **User research** with PopKit community

### 9.3 Medium-Term (90 Days)

1. **Alpha release** to selected users
2. **Iterate on UX** based on feedback
3. **Model abstraction layer** design finalization
4. **Partnership exploration** (Anthropic, OpenAI)

### 9.4 Decision Points

| Decision | Options | Recommendation |
|----------|---------|----------------|
| **Frontend framework** | React, Vue, Svelte | Next.js (React) for SSR/SEO |
| **Backend language** | Node.js, Python, Go | Node.js (xterm.js ecosystem) |
| **Container runtime** | Docker, Podman, Firecracker | Docker initially, Firecracker for prod |
| **Database** | Postgres, SQLite, Supabase | Postgres (proven, scalable) |
| **Deployment** | Vercel, Fly.io, AWS, self-host | Fly.io for containers + Vercel for frontend |

---

## 10. References

### 10.1 Official Sources

- [Claude Code on the Web](https://www.anthropic.com/news/claude-code-on-the-web) - Anthropic
- [Claude Agent SDK Overview](https://platform.claude.com/docs/en/agent-sdk/overview) - Anthropic
- [OpenAI Codex CLI](https://github.com/openai/codex) - OpenAI
- [Gemini CLI](https://github.com/google-gemini/gemini-cli) - Google
- [Model Context Protocol](https://modelcontextprotocol.io/) - Anthropic

### 10.2 Web Terminal Technologies

- [xterm.js](https://xtermjs.org/) - Terminal emulator for the web
- [Theia IDE](https://theia-ide.org/) - AI-native open-source IDE

### 10.3 Orchestration Frameworks

- [LangChain/LangGraph](https://www.langchain.com/) - LLM orchestration
- [Cross-Vendor DMF Paper](https://dalehurley.com/posts/cross-vendor-dmf-paper) - Multi-model fusion

### 10.4 Cloud Development Environments

- [Coder](https://coder.com/) - Self-hosted CDEs
- [Gitpod/Ona](https://gitpod.io/) - Cloud workspaces
- [GitHub Codespaces](https://github.com/features/codespaces) - GitHub CDEs

### 10.5 News & Analysis

- [Anthropic brings Claude Code to the web](https://techcrunch.com/2025/10/20/anthropic-brings-claude-code-to-the-web/) - TechCrunch
- [LLM Orchestration in 2025](https://orq.ai/blog/llm-orchestration) - orq.ai
- [MCP Specs Update June 2025](https://auth0.com/blog/mcp-specs-update-all-about-auth/) - Auth0

---

## Appendix A: PopKit Assets to Leverage

### Existing Components Ready for Web

| Component | Web Adaptation Needed |
|-----------|----------------------|
| `agents/config.json` | Load in backend, expose via API |
| `skills/*.md` | Parse and invoke via model |
| `commands/*.md` | Map to UI actions |
| `hooks/*.py` | Run server-side |
| `power-mode/` | Redis already abstracted |
| `output-styles/` | Render in terminal or UI panels |

### Components Needing Redesign

| Component | Reason | Approach |
|-----------|--------|----------|
| File system access | Sandboxed containers | Virtual FS abstraction |
| Git operations | User auth needed | OAuth2 with GitHub/GitLab |
| Terminal I/O | PTY → WebSocket | node-pty + xterm.js |
| Session state | Local files → persistent | Postgres + Redis |

---

## Appendix B: Glossary

| Term | Definition |
|------|------------|
| **CLI** | Command Line Interface |
| **MCP** | Model Context Protocol - tool standardization |
| **CDE** | Cloud Development Environment |
| **PTY** | Pseudo-terminal (Unix terminal emulation) |
| **xterm.js** | JavaScript terminal emulator library |
| **Power Mode** | PopKit's multi-agent orchestration system |
| **Agent** | Specialized AI persona with routing rules |
| **Skill** | Reusable capability/workflow in PopKit |

---

*Document prepared by Claude Code session on 2025-12-05*
*For review with `/popkit:dev` or PopKit Power Mode analysis*
