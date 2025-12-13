# Screenshots for Slash Command Discovery Demo

## Purpose

This directory contains screenshots that demonstrate the slash command discovery feature in Claude Code, specifically showing how typing `/dev` auto-suggests `popkit:dev` without needing to type the full `popkit:` prefix.

## Screenshot Capture Instructions

### Prerequisites

1. **Clean Claude Code session** - Start fresh to avoid clutter
2. **PopKit installed** - Ensure PopKit plugin is active
3. **Screenshot tool** - Use macOS Screenshot (Cmd+Shift+4) or equivalent
4. **Consistent terminal theme** - Use Catppuccin Mocha or similar dark theme

### Screenshots to Capture

Capture the following screenshots in sequence:

#### 1. `01-type-slash.png`
- **Action:** Type `/` character only
- **What to show:** Claude Code command palette appears with initial list
- **Focus:** Show the `/` character and empty/partial dropdown
- **Timing:** Immediate (0ms baseline)

#### 2. `02-type-d.png`
- **Action:** Type `d` after the slash (now showing `/d`)
- **What to show:** Dropdown begins filtering to commands starting with or containing 'd'
- **Focus:** Show `/d` in command line, filtered dropdown
- **Timing:** ~200ms after step 1

#### 3. `03-type-de.png`
- **Action:** Type `e` character (now showing `/de`)
- **What to show:** Dropdown narrows further to commands matching 'de'
- **Focus:** Show `/de` in command line, more focused dropdown
- **Timing:** ~400ms after step 1

#### 4. `04-type-dev.png`
- **Action:** Type `v` character (now showing `/dev`)
- **What to show:** Dropdown shows all commands matching 'dev'
- **Focus:** Show `/dev` in command line, full dropdown with matches
- **Timing:** ~600ms after step 1
- **Key point:** This is where `popkit:dev` should appear in dropdown

#### 5. `05-popkit-highlighted.png` ⭐ **MOST IMPORTANT**
- **Action:** Wait briefly after typing `/dev`
- **What to show:** `popkit:dev` highlighted as the first/top match in dropdown
- **Focus:** Show clear highlighting of `popkit:dev` command
- **Timing:** ~1000ms after step 1
- **Key insight:** Despite not typing "popkit:", the command appears first due to semantic search
- **Note:** This screenshot demonstrates the core feature - take time to get this perfect!

#### 6. `06-tab-completion.png`
- **Action:** Press Tab key to accept the suggestion
- **What to show:** Full `/popkit:dev` command now appears in command line
- **Focus:** Show command line with complete `/popkit:dev`, dropdown dismissed
- **Timing:** ~1500ms after step 1

#### 7. `07-add-work.png`
- **Action:** Type ` work` (space + work) after `/popkit:dev`
- **What to show:** Command line now shows `/popkit:dev work`
- **Focus:** Show subcommand being added
- **Timing:** ~2000ms after step 1

#### 8. `08-add-issue-number.png`
- **Action:** Type ` #57` after `work`
- **What to show:** Complete command: `/popkit:dev work #57`
- **Focus:** Show full command with issue reference
- **Timing:** ~2500ms after step 1

#### 9. `09-execute-command.png`
- **Action:** Press Enter to execute
- **What to show:** Command output beginning to appear
- **Focus:** Show immediate feedback from PopKit (fetching issue, creating worktree, etc.)
- **Timing:** ~3000ms after step 1

## Screenshot Guidelines

### Composition

- **Consistent window size:** Keep Claude Code window same size for all screenshots
- **Clean background:** Minimize visual noise, focus on command palette
- **Clear text:** Ensure text is readable at 900x600 resolution
- **Cursor visibility:** Make sure cursor is visible where relevant

### What to Include

✅ **Include:**
- Command line with text being typed
- Dropdown menu (when visible)
- Relevant command palette UI
- Clear highlighting of selected item

❌ **Exclude:**
- Unrelated windows or applications
- Personal information (file paths with usernames, etc.)
- Distracting desktop background
- System notifications

### Technical Specs

- **Format:** PNG (lossless)
- **Resolution:** Native retina resolution (will be scaled to 900x600 for VHS)
- **Color space:** sRGB
- **Naming:** Use exact filenames listed above (01-type-slash.png, etc.)

## After Capturing Screenshots

### Review Checklist

- [ ] All 9 screenshots captured
- [ ] Screenshots are in correct sequence
- [ ] Text is clear and readable
- [ ] Dropdown highlighting is visible in step 5
- [ ] No personal information visible
- [ ] Consistent window size across all screenshots

### Generate VHS Tape (Future)

Once screenshots are captured, you can generate the VHS tape using:

```bash
# Future command (not yet implemented)
/popkit:vhs analyze packages/plugin/assets/tapes/core-features/slash-command-discovery/
/popkit:vhs generate packages/plugin/assets/tapes/core-features/slash-command-discovery/
```

For now, use these screenshots to:
1. **Create annotated documentation** showing the workflow
2. **Manually write VHS tape** based on screenshot sequence
3. **Provide as reference** when designing other demos

## VHS Tape Limitations

**Important:** VHS (the terminal recording tool) **cannot show actual dropdown menus** from Claude Code's UI, since those are GUI elements, not terminal output.

### Recommended Approaches

1. **Annotated Screenshot** (Recommended)
   - Use screenshot #5 (`05-popkit-highlighted.png`)
   - Add arrows and labels showing the key insight
   - Include in README as primary documentation

2. **VHS with ASCII Simulation**
   - Create VHS tape that types the commands
   - Use comments or ASCII art to *simulate* dropdown
   - Less accurate but shows the typing flow

3. **Hybrid Approach**
   - Use annotated screenshot for the dropdown moment
   - Use VHS for the command execution portion
   - Two separate assets working together

## Questions or Issues?

If you encounter issues capturing these screenshots:

1. **Dropdown not appearing:** Ensure PopKit is properly installed and activated
2. **Wrong commands appearing:** Check that `/dev` matches PopKit's command names
3. **Highlighting unclear:** Adjust terminal theme or contrast
4. **Technical issues:** Consult the VHS research document for troubleshooting

---

**Status:** 🟡 Awaiting screenshots (0/9 captured)

**Last updated:** 2025-12-12
