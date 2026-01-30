---
name: fastapi-expert
description: auto-imported from awesome-cursorrules.
---

### fastapi-application-structure.mdc

---
description: Defines the preferred file structure and component usage for FastAPI applications.
globs: **/main.py
---
- File structure: exported router, sub-routes, utilities, static content, types (models, schemas).
- Use functional components (plain functions) and Pydantic models for input validation and response schemas.
- Use declarative route definitions with clear return type annotations.
- Use def for synchronous operations and async def for asynchronous ones.
- Minimize @app.on_event("startup") and @app.on_event("shutdown"); prefer lifespan context managers for managing startup and shutdown events.
- Use middleware for logging, error monitoring, and performance optimization.

### fastapi-database-interaction.mdc

---
description: Specifies the preferred asynchronous database libraries and interaction patterns for FastAPI applications.
globs: **/db/**/*.py
---
- Async database libraries like asyncpg or aiomysql.
- SQLAlchemy 2.0 (if using ORM features).
- Minimize blocking I/O operations; use asynchronous operations for all database calls.

### fastapi-documentation.mdc

---
description: Provides a reminder to refer to the FastAPI documentation for guidance on best practices for data models, path operations, and middleware.
globs: **/routers/**/*.py
---
- Refer to FastAPI documentation for Data Models, Path Operations, and Middleware for best practices.

### fastapi-error-handling.mdc

---
description: Defines how errors should be handled within FastAPI applications using middleware.
globs: **/middleware.py
---
- Use middleware for handling unexpected errors, logging, and error monitoring.
- Prioritize error handling and edge cases.
- Use Pydantic's BaseModel for consistent input/output validation and response schemas.

### fastapi-performance-optimization.mdc

---
description: Optimizes performance in FastAPI APIs by using async functions, caching, and other techniques.
globs: **/api/**/*.py
---
- Optimize for performance using async functions for I/O-bound tasks, caching strategies, and lazy loading.
- Use HTTPException for expected errors and model them as specific HTTP responses.
- Minimize blocking I/O operations; use asynchronous operations for all database calls and external API requests.
- Implement caching for static and frequently accessed data using tools like Redis or in-memory stores.
- Optimize data serialization and deserialization with Pydantic.
- Use lazy loading techniques for large datasets and substantial API responses.

### python-general-coding-style.mdc

---
description: Enforces general Python coding style guidelines, including functional programming preferences and naming conventions.
globs: **/*.py
---
- Write concise, technical responses with accurate Python examples.
- Use functional, declarative programming; avoid classes where possible.
- Prefer iteration and modularization over code duplication.
- Use descriptive variable names with auxiliary verbs (e.g., is_active, has_permission).
- Use lowercase with underscores for directories and files (e.g., routers/user_routes.py).
- Favor named exports for routes and utility functions.
- Use the Receive an Object, Return an Object (RORO) pattern.
- Use def for pure functions and async def for asynchronous operations.
- Use type hints for all function signatures.
- Prefer Pydantic models over raw dictionaries for input validation.
- Avoid unnecessary curly braces in conditional statements.
- For single-line statements in conditionals, omit curly braces.
- Use concise, one-line syntax for simple conditional statements (e.g., if condition: do_something()).

