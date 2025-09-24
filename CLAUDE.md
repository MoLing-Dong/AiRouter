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

### Important Startup Notes

```bash
# Always use run.py for production (prevents double process issues)
python run.py

# The application uses a two-phase startup:
# 1. run.py - Main entry point with lifespan management
# 2. app/main.py - Application core (should not be run directly)
# WARNING: Using "python app/main.py" directly causes double process issues
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

The system implements 8 sophisticated load balancing strategies:

1. **auto** - Automatically selects the best provider based on health, performance, and cost
2. **specified_provider** - Routes to a specific provider as requested
3. **fallback** - Tries preferred provider first, falls back to others
4. **weighted_round_robin** - Distributes load based on configured weights
5. **least_connections** - Selects provider with fewest active connections
6. **response_time** - Prioritizes providers with fastest response times
7. **cost_optimized** - Balances cost and performance metrics
8. **hybrid** - Combines multiple factors for optimal selection

Strategy configuration is stored in the database and applied per-model basis.

## Key Files and Patterns

### Entry Points

- `run.py`: Production entry point (no reload, prevents double processes)
- `app/main.py`: Application lifecycle management with lifespan events
- `app/core/app.py`: FastAPI app configuration with CORS middleware

### Smart Routing System

The core routing logic is implemented in `app/services/router.py`:

1. **SmartRouter class**: Handles intelligent provider selection
2. **RouteRequest method**: Main routing logic with strategy execution
3. **Health-aware routing**: Only routes to healthy providers
4. **Performance tracking**: Monitors response times, success rates, and costs
5. **Statistics management**: Tracks request counters and failure rates

### Adapter Pool Management

- `app/services/adapter_pool.py`: Manages adapter lifecycle and connection pooling
- `app/core/adapters/`: Provider-specific implementations
- Health checks are performed automatically on startup and at configured intervals

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
- Provider-specific implementations in `app/core/adapters/`
- Adapter pool manages connection lifecycle and health monitoring
- Health status is tracked in real-time and affects routing decisions

### Model Availability Logic

The `get_available_models` method in `app/services/adapter_manager.py` has been enhanced to:

- Only return models with at least one healthy provider
- Filter out models with all providers in unhealthy/degraded states
- Ensure `available_models` endpoint only shows healthy models
- Apply the same filtering to both `get_available_models` and `get_available_models_fast`

### Error Handling

- Use HTTPException for API errors with proper status codes
- Structured logging with performance metrics
- Graceful fallback strategies when providers fail
- Health status affects provider selection automatically

### Performance Considerations

- Models cache preloaded on startup for faster first request
- Connection pooling for database operations with configurable pool sizes
- Automatic health checks with configurable intervals
- Performance metrics tracking: response times, success rates, costs
- Available models are filtered by health status to prevent routing to unhealthy providers

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
- Load balancing strategies are configurable per-model in the database

### Environment Configuration

Key environment variables in `.env`:

- `LOAD_BALANCING_STRATEGY=auto` - Global default strategy
- `LOAD_BALANCING_HEALTH_CHECK_INTERVAL=30` - Health check frequency
- `LOAD_BALANCING_MAX_RETRIES=3` - Maximum retry attempts
- `DATABASE_URL` - PostgreSQL connection string
- `DEBUG` - Enable/disable debug mode (affects logging and error details)

### Database Schema Relationships

- Models can have multiple providers (one-to-many relationship)
- Providers can have multiple API keys (for rotation/backup)
- Model-provider associations include weights, priorities, and strategy configs
- Health status and performance metrics are tracked automatically and updated in real-time
