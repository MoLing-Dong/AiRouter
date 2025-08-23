# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI Router is an intelligent LLM routing and load balancing system built with FastAPI. It provides a unified OpenAI-compatible API interface for multiple AI service providers with intelligent load balancing, failover, and cost optimization.

## Development Commands

### Environment Setup

```bash
# Install dependencies using uv (recommended)
uv sync

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # Linux/macOS
uv pip install -e .

# Install development dependencies
uv pip install -e ".[dev]"
```

### Running the Application

```bash
# Start application (prevents double process issues)
python run.py

# Alternative startup script
./start.sh

# Docker deployment
./scripts/setup.sh
docker-compose up -d

# View logs
docker-compose logs -f
```

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=term-missing

# Run specific test categories
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
pytest -m "not slow"    # Exclude slow tests
```

### Code Quality

```bash
# Format code
black app/

# Sort imports
isort app/

# Lint code
flake8 app/

# Type checking
mypy app/

# Run all quality checks
black app/ && isort app/ && flake8 app/ && mypy app/
```

## Architecture Overview

### Core Components

1. **FastAPI Application** (`app/core/app.py`): Main FastAPI instance with CORS middleware
2. **Router Service** (`app/services/router.py`): Intelligent request routing with load balancing strategies
3. **Adapter System** (`app/core/adapters/`): Provider-specific adapters for different AI services
4. **Database Layer** (`app/services/`): Repository pattern with transaction management
5. **Model Management** (`app/models/`): Pydantic models and SQLAlchemy entities

### Service Architecture

The project follows a layered architecture:

- **Base Layer**: Transaction management and repository base classes
- **Repository Layer**: Data access objects for models, providers, and API keys
- **Business Service Layer**: Business logic and domain operations
- **Service Factory**: Dependency injection and service lifecycle management

### Supported Providers

- OpenAI (GPT-4, GPT-3.5-turbo, GPT-4-turbo)
- Anthropic (Claude-3-sonnet, Claude-3-haiku)
- Volcengine (火山引擎模型)
- Custom OpenAI-compatible APIs

### Load Balancing Strategies

- Round Robin
- Weighted Round Robin
- Performance Based
- Cost Optimized
- Fallback
- Specified Provider

## Key Files and Patterns

### Entry Points

- `run.py`: Production entry point (no reload)
- `app/main.py`: Application lifecycle management
- `app/core/app.py`: FastAPI app configuration

### Configuration

- `config/settings.py`: Application settings and environment variables
- `pyproject.toml`: Project dependencies and tool configuration

### Database Models

- `app/models/llm_model.py`: LLM model definitions
- `app/models/llm_provider.py`: Provider configurations
- `app/models/llm_model_provider.py`: Model-provider associations

### API Structure

- `app/api/v1/models/`: Model management endpoints
- `app/api/v1/chat/`: Chat completion endpoints
- `app/api/v1/providers.py`: Provider management

## Development Guidelines

### Database Operations

- Use the transaction manager for all database operations
- Repositories provide CRUD operations with validation
- Service factory manages dependency injection

### Adapter Pattern

- All providers inherit from `BaseAdapter` in `app/core/adapters/base.py`
- Implement provider-specific logic in respective adapter files
- Use adapter pool for connection management

### Error Handling

- Use HTTPException for API errors
- Implement proper logging with structured format
- Handle provider failures gracefully with fallback strategies

### Performance Considerations

- Preload models cache on startup
- Use connection pooling for database operations
- Implement health checks for all providers
- Monitor response times and success rates

## Testing Strategy

### Test Structure

- `tests/test_api/`: API endpoint tests
- `tests/test_services/`: Business logic tests
- `tests/test_adapters/`: Adapter functionality tests

### Test Patterns

- Use pytest-asyncio for async tests
- Mock external API calls with httpx
- Test both success and failure scenarios
- Use fixtures for common test data

## Configuration Notes

### Environment Variables

- `DATABASE_URL`: PostgreSQL connection string
- `DEBUG`: Enable/disable debug mode
- `HOST`/`PORT`: Server binding configuration
- Provider API keys are managed through database, not environment variables

### Database Schema

- Models can have multiple providers
- Providers support multiple API keys
- Model-provider associations include weights and priorities
- Health status and performance metrics are tracked automatically

## Common Issues

### Double Process Prevention

- Always use `python run.py` instead of `python app/main.py`
- Reload is disabled to prevent double process issues
- Use `./start.sh` for process management

### Database Migrations

- The project uses SQLAlchemy without Alembic
- Model changes require manual database updates
- Use the transaction manager for schema changes

### Provider Configuration

- API keys are stored in database, not configuration files
- Use the management API to add providers and models
- Health checks run automatically for all providers
