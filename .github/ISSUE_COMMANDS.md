# GitHub Issue Commands Quick Reference

## 📋 Common Commands

### Viewing Issues
```bash
# List all open issues
gh issue list

# List with more details
gh issue list --limit 20

# View specific issue
gh issue view 14

# View issue in browser
gh issue view 14 --web

# Search issues
gh issue list --search "Telegram"
```

### Creating Issues
```bash
# Create issue interactively
gh issue create

# Create with title and body
gh issue create --title "New Feature" --body "Description here"

# Create with labels
gh issue create --title "Bug Fix" --label "bug"
```

### Managing Issues
```bash
# Add comment
gh issue comment 14 --body "Working on this now"

# Close issue
gh issue close 14

# Close with comment
gh issue close 14 --comment "Completed all tasks"

# Reopen issue
gh issue reopen 14
```

### Filtering & Searching
```bash
# Show closed issues
gh issue list --state closed

# Show all issues (open + closed)
gh issue list --state all

# Filter by label
gh issue list --label "priority"

# Filter by assignee
gh issue list --assignee @me
```

## 🔗 Linking Issues in Git

### Commit Messages
Reference issues in your commits:
```bash
# Reference an issue
git commit -m "Add feature X (relates to #14)"

# Auto-close issue when merged
git commit -m "Complete feature X

Closes #14"
```

### Keywords that Close Issues
When these appear in commit messages or PR descriptions:
- `Closes #14`
- `Fixes #14`
- `Resolves #14`

## ✅ Using Task Lists

### In Issue Descriptions
```markdown
## Tasks
- [ ] Task 1
- [ ] Task 2
- [x] Task 3 (completed)
```

### In Comments
Add more detailed subtasks in comments:
```markdown
Progress update:
- [x] Setup complete
- [ ] Testing in progress
- [ ] Documentation pending
```

## 🏷️ Working with Labels

```bash
# List all labels
gh label list

# Add label to issue
gh issue edit 14 --add-label "priority"

# Remove label
gh issue edit 14 --remove-label "bug"
```

## 📊 Issue Status & Progress

```bash
# Export to JSON
gh issue list --json number,title,state,labels

# Count issues by state
gh issue list --state all --json state | jq 'group_by(.state)'

# View issue status
gh issue status
```

## 🌐 Web Interface

Open GitHub in browser:
```bash
# View all issues
gh issue list --web

# View specific issue
gh issue view 14 --web

# Open repo issues page
gh browse -- issues
```

## 💡 Pro Tips

1. **Pin Important Issues**: Pin high-priority issues on GitHub web UI
2. **Use Templates**: Create issue templates for common types (bug, feature)
3. **Milestones**: Group issues into version milestones (v1.1, v1.2)
4. **Projects**: Use GitHub Projects for Kanban-style boards
5. **Notifications**: Watch issues to get updates via email

## 📱 GitHub Mobile

Download the GitHub mobile app to:
- Check off task list items on the go
- Comment on issues
- Review and merge PRs
- Get push notifications

## 🚀 Current Issues

View all active piGallery issues:
https://github.com/joshld/piGallery/issues

Key issues:
- #14 - ⭐ Telegram Integration
- #7 - Image Captions
- #8 - Shutdown Button
- #15 - Color Schemes
- #16 - Performance Monitoring
