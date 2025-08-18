# YouTube Knowledgebank

## Project Overview
YouTube Knowledgebank is an intelligent knowledge extraction and retrieval system that transforms YouTube videos into a searchable, connected knowledge base with AI-powered insights and semantic understanding.

## Evolution Path
**Phase 1 (Current)**: Basic transcript viewer with timestamp navigation
**Phase 2 (In Development)**: Intelligent knowledge bank with semantic search, entity extraction, and cross-video connections

## Core Functionality

### Current Features
- **Video Processing**: Extract audio from YouTube URLs using yt-dlp
- **Transcription**: High-quality transcription with word-level timestamps via ElevenLabs API
- **Interactive Navigation**: Click transcript segments to jump to specific video timestamps
- **Data Organization**: Each video stored in organized subfolders with metadata and transcripts

### Planned Knowledge Bank Features
- **Semantic Search**: Natural language queries across all transcripts ("What was said about productivity?")
- **Knowledge Extraction**: Auto-identify books, people, concepts, and key insights
- **Cross-Video Connections**: Discover relationships and patterns across your video collection
- **AI-Powered Summaries**: Generate key insights and actionable advice per video/topic
- **Interactive Knowledge Graph**: Visualize connections between ideas, concepts, and entities
- **Question-Answering**: Ask questions and get sourced answers from your knowledge base

## Application Structure

### Pages
1. **Overview Page** (`/`) - Grid view of all processed videos with search functionality
2. **Processing Page** (`/process`) - Interface for submitting YouTube URLs and tracking progress
3. **Video Pages** (`/video/{id}`) - Individual video view with embedded player and clickable transcript
4. **Settings Page** (`/settings`) - API key configuration for ElevenLabs

### Key Features
- **Real-time Progress Tracking**: Server-Sent Events for download and transcription progress
- **Responsive Design**: Side-by-side layout (desktop) and stacked layout (mobile)
- **Docker-First Development**: All development and deployment runs in Docker containers
- **Secure API Key Management**: Settings stored locally, never committed to git

## Technology Stack

### Current Stack
- **Backend**: FastAPI (Python)
- **Frontend**: Jinja2 templates with Tailwind CSS
- **Video Processing**: yt-dlp for YouTube downloads
- **Transcription**: ElevenLabs Scribe API with word-level timestamps
- **Storage**: File-based JSON storage
- **Containerization**: Docker + Docker Compose
- **Video Embedding**: YouTube IFrame Player API

### Knowledge Bank Stack (Planned)
- **Database**: SQLite + FTS5 (full-text search) + sqlite-vec (vector similarity)
- **AI/ML**: OpenAI API for embeddings and language processing
- **Search**: Hybrid semantic + keyword search with relevance ranking
- **Knowledge Graph**: D3.js for interactive visualizations
- **Background Processing**: Async task processing for AI operations

## Development Guidelines
See `context/git-strategy.md` for detailed development workflow, security guidelines, and git branching strategy.

## Knowledge Bank Development
- **PRD**: See `context/knowledge-bank-prd.md` for detailed feature specifications
- **TODO**: See `context/knowledge-bank-todo.md` for modular development plan
- **Architecture**: 4-phase modular development approach with independent feature branches

## Security Notes
- API keys stored in `/data/settings.json` (excluded from git)
- All user data in `/data/` directory is gitignored
- Never commit sensitive information

## Quick Start (Docker-First Approach)
```bash
# Clone and start
git clone git@github.com:mikkelkrogsholm/yt-knowledgebank.git
cd yt-knowledgebank
docker compose up --build

# Access at http://localhost:8765
# Configure ElevenLabs API key in Settings
```

## Development Environment (Docker)
```bash
# All development runs in Docker containers
# No need to install Python, dependencies, or configure local environment

# Start development environment
docker compose up --build

# Run tests in container
docker compose exec app pytest

# Access container shell for debugging
docker compose exec app bash

# View logs
docker compose logs -f app
```