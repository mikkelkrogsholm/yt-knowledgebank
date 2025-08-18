# Git Branch Structure - Current Setup

## Branch Overview
Our git repository is now configured with the complete branching strategy for knowledge bank development.

## Branch Structure

### Main Branches
- **`main`** - Production-ready code, stable releases (protected, PR-only)
- **`develop`** - Integration branch, latest development state (default branch)

### Feature Branches (Knowledge Bank Development)
- **`feature/database-foundation`** - Phase 1: SQLite migration and FTS5 setup
- **`feature/semantic-search`** - Phase 2: Vector embeddings and semantic search
- **`feature/knowledge-extraction`** - Phase 3: Entity recognition and topic modeling
- **`feature/knowledge-navigation`** - Phase 4: Knowledge graphs and Q&A system

## Current Status
✅ All branches created and pushed to GitHub
✅ Branch tracking configured for all feature branches  
✅ Ready for modular development approach

## Development Workflow

### Starting Work on a Feature
```bash
# Switch to the appropriate feature branch
git checkout feature/database-foundation

# Pull latest changes
git pull origin feature/database-foundation

# Start development...
```

### Creating Additional Feature Branches
```bash
# Always branch from develop
git checkout develop
git pull origin develop
git checkout -b feature/your-new-feature
git push -u origin feature/your-new-feature
```

### Merging Completed Features
```bash
# When feature is complete, merge to develop
git checkout develop
git pull origin develop
git merge feature/your-completed-feature
git push origin develop

# Delete the feature branch (optional)
git branch -d feature/your-completed-feature
git push origin --delete feature/your-completed-feature
```

### Creating Releases
```bash
# When develop is stable, create PR to main
gh pr create --base main --head develop --title "Release v1.0.0" --body "Release notes..."

# After PR is approved and merged, tag the release
git checkout main
git pull origin main
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin main --tags
```

## Next Steps
1. **Start with Phase 1**: Switch to `feature/database-foundation`
2. **Follow TODO**: Reference `context/knowledge-bank-todo.md` for specific tasks
3. **Test thoroughly**: Ensure Docker builds work before commits
4. **Security check**: Always verify no sensitive data in commits

## GitHub Repository Configuration
- **Main repo**: https://github.com/mikkelkrogsholm/yt-knowledgebank
- **Default branch**: `develop` (set in GitHub Settings → General)
- **Branch protection**: `main` branch protected (requires PRs)
- **All feature branches** available for pull requests and collaboration

### Required GitHub Settings:
1. **Settings → General → Default branch**: Change to `develop`
2. **Settings → Branches**: Add protection rule for `main`
   - Require pull request reviews
   - Require status checks
   - Include administrators

## Commit Convention Examples
```bash
# Feature commits
git commit -m "feat: add SQLite database schema setup"
git commit -m "feat: implement vector similarity search"

# Bug fixes
git commit -m "fix: resolve embedding generation timeout"

# Documentation
git commit -m "docs: update API endpoint documentation"

# Refactoring
git commit -m "refactor: extract search logic into separate module"
```

Remember: Always include the Claude Code signature in significant commits!