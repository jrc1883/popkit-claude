# Before/After Hero Demo
# Shows the transformation PopKit provides

Output assets/images/before-after.gif

Set FontSize 14
Set Width 900
Set Height 600
Set Theme "Catppuccin Mocha"
Set Padding 20

# "Without PopKit" section
Type "# Without PopKit..."
Enter
Sleep 1s

Type "git status"
Enter
Sleep 500ms
Type "npm run typecheck"
Enter
Sleep 500ms
Type "npm run lint"
Enter
Sleep 500ms
Type "gh issue view 57"
Enter
Sleep 500ms
Type "# Manually check each thing..."
Enter
Sleep 1s

# Clear and show "With PopKit"
Ctrl+L
Sleep 500ms

Type "# With PopKit..."
Enter
Sleep 1s

Type "/popkit:dev work #57"
Enter
Sleep 2s

Type@30ms "✓ Fetched issue #57: Add user authentication"
Enter
Type@30ms "✓ Created worktree: .worktrees/issue-57"
Enter
Type@30ms "✓ Health check: Ready to Code (95/100)"
Enter
Type@30ms "✓ Starting Phase 1: Discovery..."
Enter
Sleep 2s
