# Release Notes

## Version 0.2.0 (2025-01-06)

### 🎉 Major Features

#### Enum Support
- **NEW**: Full support for Python enums in forms
  - Standard Python enums rendered as dropdown selects
  - Literal enums supported with proper type handling
  - Comprehensive enum field rendering and validation
- Added `literal_enum_example.py` demonstrating enum usage patterns

#### Default Values System
- **NEW**: Comprehensive default values handling
  - Added `defaults.py` module for centralized default value management
  - Support for exclude fields with intelligent default value detection
  - Default values automatically applied from field definitions
  - Enhanced field parsing with default value preservation

#### Enhanced Initial Values Support
- **NEW**: `initial_values` now supports passing a dictionary
- Partial dictionaries supported - no need to provide complete data
- Robust handling of schema drift - gracefully handles missing or extra fields
- Backward compatible with existing usage patterns

#### Compact UI Mode
- **NEW**: `spacing="compact"` parameter for denser form layouts
- Improved visual density for complex forms
- Better space utilization without sacrificing usability

### 🔧 Enhancements

#### Core Library Improvements
- Enhanced `field_renderers.py` with robust enum handling (+432 lines)
- Expanded `form_parser.py` with improved parsing logic (+75 lines)
- Significant improvements to `form_renderer.py` (+311 lines)
- New `type_helpers.py` module for advanced type introspection (+106 lines)
- Added `ui_style.py` for better UI consistency (+123 lines)

#### Testing & Quality
- **Comprehensive test coverage**: Added 8,156+ lines of tests
- New test categories:
  - `integration/`: End-to-end enum testing
  - `property/`: Property-based robustness testing with Hypothesis
  - `unit/`: Focused unit tests for new modules
- Added test markers for better test organization: `enum`, `integration`, `property`, `unit`, `slow`

#### Examples & Documentation
- Enhanced `complex_example.py` with descriptions and advanced patterns (+597 lines)
- Updated README with enum usage examples and expanded documentation (+463 lines)
- Added comprehensive examples for various use cases

### 🐛 Bug Fixes
- Fixed custom field list add functionality
- Improved color handling in UI components
- Enhanced field exclusion logic
- Better handling of optional imports

### 📦 Dependencies & Build
- Updated project metadata in `pyproject.toml`
- Enhanced build configuration with proper exclusions for tests and examples
- Added development dependencies for testing: `hypothesis`, `pytest-mock`, `pytest-asyncio`

### 📊 Statistics
- **33 files changed**
- **8,156 additions, 318 deletions**
- **20+ new commits** since v0.1.3
- Significantly expanded test coverage and documentation

---

## Version 0.1.3 (2024-04-23)

Previous stable release focusing on core form functionality and basic field rendering.