---
name: brainstorming
description: "Collaborative design refinement that transforms rough ideas into fully-formed specifications through Socratic questioning. Explores alternatives, validates incrementally, and presents designs in digestible chunks for feedback. Use before writing code or implementation plans when requirements are unclear or multiple approaches exist. Do NOT use when requirements are already well-defined, you're implementing a known pattern, or making small changes - proceed directly to implementation instead."
---

# Brainstorming Ideas Into Designs

## Overview

Help turn ideas into fully formed designs and specs through natural collaborative dialogue.

Start by understanding the current project context, then ask questions one at a time to refine the idea. Once you understand what you're building, present the design in small sections (200-300 words), checking after each section whether it looks right so far.

## User Interaction Pattern

**ALWAYS use AskUserQuestion** for decisions and clarifications:

```
Use AskUserQuestion tool with:
- question: Clear, specific question ending with "?"
- header: Short label (max 12 chars): "Approach", "Auth", "Database"
- options: 2-4 choices with labels and descriptions
- multiSelect: false (unless multiple selections make sense)
```

**NEVER present options as plain text** like "1. Option A, 2. Option B - type 1 or 2".

## The Process

**Understanding the idea:**
- Check out the current project state first (files, docs, recent commits)
- Ask questions one at a time to refine the idea using AskUserQuestion
- Only one question per message - if a topic needs more exploration, break it into multiple questions
- Focus on understanding: purpose, constraints, success criteria

**Exploring approaches:**
- Propose 2-3 different approaches with trade-offs using AskUserQuestion
- Each option should have a clear label and description explaining trade-offs
- Lead with your recommended option by listing it first

**Presenting the design:**
- Once you believe you understand what you're building, present the design
- Break it into sections of 200-300 words
- Ask after each section whether it looks right so far
- Cover: architecture, components, data flow, error handling, testing
- Be ready to go back and clarify if something doesn't make sense

## After the Design

**Documentation:**
- Write the validated design to `docs/plans/YYYY-MM-DD-<topic>-design.md`
- Commit the design document to git

**Implementation (if continuing):**
- Ask: "Ready to set up for implementation?"
- Use pop:using-git-worktrees skill to create isolated workspace
- Use pop:writing-plans skill to create detailed implementation plan

## Key Principles

- **One question at a time** - Don't overwhelm with multiple questions
- **Always use AskUserQuestion** - Interactive prompts, never plain text options
- **YAGNI ruthlessly** - Remove unnecessary features from all designs
- **Explore alternatives** - Always propose 2-3 approaches before settling
- **Incremental validation** - Present design in sections, validate each
- **Be flexible** - Go back and clarify when something doesn't make sense

## PDF Input Support

When provided with a PDF file path (design doc, spec, or requirements), read it first:

```
User: Here's the design doc: /path/to/design.pdf
```

**Process PDF input:**
1. Use Read tool to analyze the PDF content
2. Extract key requirements, constraints, and goals
3. Identify areas that need clarification
4. Use extracted context to inform the brainstorming process

**When reading design PDFs:**
- Look for: objectives, user stories, constraints, success criteria
- Note gaps: missing acceptance criteria, unclear requirements
- Identify: dependencies, technical constraints, timeline pressures
- Flag: ambiguities that need clarification during brainstorming

This allows brainstorming to start from existing documentation rather than from scratch.
