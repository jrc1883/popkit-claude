# Slash Command Discovery Demo
# Generated from screenshots in screenshots/ directory
#
# NOTE: This VHS tape CANNOT accurately show Claude Code's dropdown menu UI.
# VHS only works with terminal output, not GUI elements.
#
# RECOMMENDATION: Use annotated screenshot (05-popkit-highlighted.png) instead
# for documentation, as it shows the actual UI that users will see.
#
# This tape shows the *concept* of the workflow, but not the actual visual experience.

Output ../../../images/slash-command-discovery.gif

Set FontSize 14
Set Width 900
Set Height 600
Set Theme "Catppuccin Mocha"
Set Padding 20

# Clear screen for clean start
Ctrl+L
Sleep 1s

# Simulate the typing sequence
# In reality, dropdown appears as GUI overlay - we can only show the typing
Type "/"
Sleep 300ms

Type "d"
Sleep 200ms

Type "e"
Sleep 200ms

Type "v"
Sleep 500ms

# At this point, the dropdown would show in Claude Code UI with popkit:dev highlighted
# We cannot show this in VHS, so we'll show it in a comment simulation

Hide
Type "# 💡 At this moment, Claude Code shows a dropdown menu with:"
Enter
Type "#    ╭─────────────────────────────────────────╮"
Enter
Type "#    │ ▶ popkit:dev          (first match!) │"
Enter
Type "#    │   dev-server                            │"
Enter
Type "#    │   devtools                              │"
Enter
Type "#    │   development:start                     │"
Enter
Type "#    ╰─────────────────────────────────────────╯"
Enter
Enter
Type "# The key insight: typing just '/dev' brings up 'popkit:dev'"
Enter
Type "# without needing to type the full 'popkit:' prefix!"
Enter
Sleep 2s
Show

# Clear the simulation
Ctrl+L
Sleep 500ms

# Show the Tab completion result
Type "/popkit:dev"
Sleep 500ms

# Add subcommand
Type " work"
Sleep 300ms

# Add issue number
Type " #57"
Sleep 500ms

# Execute
Enter
Sleep 1s

# Show PopKit output
Type@30ms "✓ Fetched issue #57: Implement user authentication"
Enter
Type@30ms "✓ Created worktree: .worktrees/issue-57"
Enter
Type@30ms "✓ Branch: claude/issue-57-user-auth"
Enter
Type@30ms "✓ Health check: Ready to Code (95/100)"
Enter
Type@30ms "✓ Starting Phase 1: Discovery..."
Enter

Sleep 3s

# Final message about efficiency
Ctrl+L
Sleep 500ms

Type@20ms "────────────────────────────────────────────────"
Enter
Type@20ms "  💡 EFFICIENCY TIP"
Enter
Type@20ms "────────────────────────────────────────────────"
Enter
Enter
Type@20ms "  Instead of:  /popkit:dev work #57"
Enter
Type@20ms "               ^^^^^^^ 7 extra characters"
Enter
Enter
Type@20ms "  Just type:   /dev work #57"
Enter
Type@20ms "               ^^^^ semantic search finds it!"
Enter
Enter
Type@20ms "────────────────────────────────────────────────"
Enter

Sleep 3s
