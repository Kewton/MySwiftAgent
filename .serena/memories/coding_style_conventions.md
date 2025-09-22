# Coding Style and Conventions

## Python Code Style

### Type Hints
- **Required**: All function parameters and return types must have type hints
- **Modern Syntax**: Use `X | None` instead of `Optional[X]` (Python 3.10+ style)
- **Strict Mode**: MyPy is configured with strict settings
- **Generics**: Avoid `Any` types, use proper generic types

### Code Formatting
- **Line Length**: 88 characters (Black/Ruff default)
- **Tool**: Ruff for both linting and formatting
- **Import Sorting**: isort integration via Ruff
- **Docstrings**: Required for all public functions and classes

### Naming Conventions
- **Functions/Variables**: snake_case
- **Classes**: PascalCase
- **Constants**: UPPER_SNAKE_CASE
- **Private**: Leading underscore (_private_function)
- **Files**: snake_case.py

### Project Structure Patterns
- **FastAPI**: Follow FastAPI best practices
- **Pydantic**: Use for data validation and serialization
- **Async/Await**: Prefer async functions for I/O operations
- **Dependency Injection**: Use FastAPI's dependency system

### Database Models
- **SQLAlchemy**: Use SQLAlchemy 2.0+ syntax
- **Async**: Use async SQLAlchemy with aiosqlite
- **Naming**: Table names in snake_case, model classes in PascalCase

### API Design
- **REST**: Follow REST conventions
- **Schemas**: Separate request/response schemas
- **Error Handling**: Use FastAPI's HTTPException
- **Validation**: Pydantic for request/response validation

## Testing Conventions

### Structure
- **Unit Tests**: Individual functions/classes in `tests/unit/`
- **Integration Tests**: API endpoints in `tests/integration/`
- **Fixtures**: Shared fixtures in `conftest.py`

### Naming
- **Test Files**: `test_*.py`
- **Test Classes**: `TestClassName`
- **Test Methods**: `test_method_description`

### Coverage
- **Target**: 80%+ for unit tests, 90%+ for integration tests
- **Tools**: pytest-cov for coverage reporting

## Security Best Practices
- **No Secrets**: Never commit API keys, passwords, or tokens
- **Input Validation**: Strict Pydantic validation for all inputs
- **Error Messages**: Don't expose internal implementation details
- **Timeouts**: Set appropriate timeouts for external API calls