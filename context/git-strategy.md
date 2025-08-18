# Git Strategy & Development Guidelines

## Project Overview
YouTube Knowledgebank - A FastAPI webapp for downloading and transcribing YouTube videos using ElevenLabs API with clickable timestamp navigation.

## Git Strategy

### Branch Structure
- **`main`** - Production-ready, stable code. Always deployable.
- **`develop`** - Integration branch for features. Latest development state.
- **`feature/*`** - Individual feature development (e.g., `feature/search-functionality`)
- **`fix/*`** - Bug fixes (e.g., `fix/timestamp-navigation`)
- **`hotfix/*`** - Critical production fixes that bypass develop

### Workflow
1. **Start new work**: Create branch from `develop`
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feature/your-feature-name
   ```

2. **Development**: Make focused commits
   - Test locally with Docker
   - Keep commits atomic and descriptive
   - Never commit sensitive data (API keys, processed videos)

3. **Before pushing**: 
   ```bash
   git status  # Check no sensitive files are staged
   docker-compose build  # Ensure Docker build works
   ```

4. **Merge back**:
   ```bash
   git checkout develop
   git merge feature/your-feature-name
   git push origin develop
   ```

5. **Release**: Merge `develop` → `main` for releases

### Commit Conventions
Use conventional commits format:
- `feat:` - New features
- `fix:` - Bug fixes  
- `docs:` - Documentation updates
- `style:` - Code formatting (no logic changes)
- `refactor:` - Code restructuring
- `test:` - Adding/updating tests
- `chore:` - Maintenance tasks

Examples:
```
feat: add search functionality to video overview
fix: resolve timestamp navigation jumping to end
docs: update installation instructions
refactor: extract transcript processing into separate module
```

## Security Guidelines

### Never Commit These Files/Patterns:
- `/data/settings.json` - Contains API keys
- `/data/videos/` - User's processed content  
- `.env` files
- Any files containing `sk_` (ElevenLabs API keys)

### Before Every Commit:
1. Run `git status` and verify no sensitive files are staged
2. Check commit diff doesn't contain API keys
3. Ensure `.gitignore` is protecting sensitive data

## Development Environment

### Docker Commands
```bash
# Build and start
docker-compose up --build

# Stop
docker-compose down

# View logs
docker-compose logs -f

# Rebuild after code changes
docker-compose up --build
```

### Local Testing Checklist
- [ ] Docker build completes without errors
- [ ] App starts on port 8765
- [ ] Can process a YouTube video
- [ ] Timestamp navigation works
- [ ] No sensitive data in git status

## Project Structure
```
├── app/                 # Python application
│   ├── main.py         # FastAPI routes
│   ├── processor.py    # YouTube + ElevenLabs logic
│   └── settings.py     # API key management
├── templates/          # Jinja2 HTML templates
├── context/           # Documentation and guides
├── data/              # User data (gitignored)
├── docker-compose.yml # Container orchestration
└── requirements.txt   # Python dependencies
```

## Common Issues & Solutions

### Timestamp Navigation Not Working
- Check browser console for JavaScript errors
- Verify YouTube player API loads properly
- Ensure transcript has `speaker_id` field

### Docker Build Fails
- Check requirements.txt versions
- Verify Dockerfile syntax
- Clear Docker cache: `docker system prune`

### API Key Issues
- Never hardcode keys in source
- Use settings page in webapp to configure
- Check `data/settings.json` exists (but don't commit it)

## Code Quality Standards

### Python Code
- Follow PEP 8 style guidelines
- Use type hints where possible
- Keep functions focused and small
- Add docstrings for complex functions

### JavaScript
- Use modern ES6+ syntax
- Handle async operations properly
- Add error handling for API calls
- Use meaningful variable names

### HTML/CSS
- Use semantic HTML elements
- Maintain responsive design
- Keep Tailwind classes organized
- Test on different screen sizes

## Release Process

1. **Feature Complete**: All features merged to `develop`
2. **Testing**: Thorough testing on `develop` branch
3. **Release Branch**: Create `release/vX.Y.Z` from develop
4. **Final Testing**: Last-minute bug fixes on release branch
5. **Merge to Main**: Merge release branch to `main`
6. **Tag Release**: Tag main with version number
7. **Deploy**: Deploy from `main` branch

## Useful Git Commands

```bash
# Check what would be committed (security check)
git diff --cached

# Unstage a file if accidentally added
git reset HEAD filename

# Create feature branch
git checkout -b feature/new-feature develop

# Safe way to update your branch with latest develop
git checkout develop
git pull origin develop
git checkout feature/your-branch
git rebase develop

# Check git history
git log --oneline --graph

# Check which files are ignored
git status --ignored
```

## Notes for Future Development
- This is a personal use application - privacy concerns are minimal
- Focus on clean, maintainable code over enterprise-level complexity  
- Docker setup ensures consistent development environment
- ElevenLabs API is the transcription provider - check their docs for updates
- YouTube video embedding uses IFrame Player API