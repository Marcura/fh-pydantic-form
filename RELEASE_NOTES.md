# Release Notes

## Version 0.3.17 (2026-01-19)

### 🎉 New Features

#### ComparisonForm Dynamic Routing via `template_name`
- **NEW**: `ComparisonForm(..., template_name="...")` allows multiple ComparisonForm instances to share the same registered routes
- **NEW**: Template routes accept `fhpf_form_name` to render refresh actions for a specific dynamic form instance
- **PATTERN**: Same pattern as `PydanticForm.template_name` - register routes once on a template, reuse for dynamic instances

### 🔧 Improvements

#### ComparisonForm Handler Enhancements
- **IMPROVED**: Refresh handlers support `fhpf_form_name` for dynamic form prefix handling
- **IMPROVED**: Buttons include `fhpf_form_name` when routing through shared ComparisonForm template routes
- **IMPROVED**: Reset buttons use the client-side snapshot reset for dynamic instances (so each row resets to its own initial values)

### 📚 Documentation
- **UPDATED**: README.md with ComparisonForm `template_name` documentation
- **UPDATED**: `examples/dynamic_forms_example.py` demonstrating ComparisonForm template routes

---

## Version 0.3.16 (2026-01-19)

### ⚠️ Breaking Changes

#### Python Version Requirements
- **DROPPED**: Python 3.10 and 3.11 support
- **REQUIRED**: Python 3.12 or higher now required
- **REASON**: Upstream `fastcore` dependency now uses Python 3.12+ syntax (f-string expressions with backslashes)

### 🔧 Bug Fixes

#### ComparisonForm Recursive Copy
- **FIXED**: Nested list copy now resolves the correct add button by exact list path (avoids picking nested lists)
- **FIXED**: Deep copy logic matches nested containers by list path rather than DOM order
- **FIXED**: List containers now include `data-list-path` for deterministic nested list pairing

#### ComparisonForm List Truncation
- **FIXED**: Copying a shorter list to a longer list now truncates excess target items (e.g., copying 2 items to a 5-item list results in 2 items, not 5)
- **FIXED**: Nested lists within copied items are also truncated (e.g., copying a Section with 1 paragraph to one with 2 paragraphs now results in 1 paragraph)

### 📦 Dependencies
- **ADDED**: `ty` type checker to dev dependencies for consistent type checking in CI

### 🧪 Testing
- **IMPROVED**: Recursive copy tests now assert `data-list-path` contracts and add‑button matching for nested lists
- **IMPROVED**: Consolidated nested list tests to reduce duplication and focus simple list tests on core behavior

---

## Version 0.3.15 (2026-01-16)

### 🔧 Bug Fixes

#### ComparisonForm Copy JS
- **FIXED**: `comparison_form_js()` output no longer mangles `const` declarations (missing spaces), which caused `ReferenceError` and broke copy operations
- **FIXED**: Reassigned bindings in the copy logic now use `let` to avoid `Assignment to constant variable` at runtime

### 🧪 Testing
- **IMPROVED**: Embedded JS moved into packaged assets for consistent syntax checks and easier unit testing
- **ADDED**: JS syntax validation in pytest and pre-commit

---

## Version 0.3.14 (2026-01-16)

### 🎉 New Features

#### Dynamic Forms via `template_name`
- **NEW**: `PydanticForm(..., template_name="...")` to reuse a single registered set of routes for many dynamically named forms
- **NEW**: Template routes accept `fhpf_form_name` to render list/refresh actions for a specific dynamic form instance
- **NEW**: Client-side reset for dynamic forms (restores the initial HTML snapshot)

### 🔧 Improvements

#### ComparisonForm Multi-Instance Support
- **IMPROVED**: Copy + accordion sync is now scoped to each comparison grid (supports multiple ComparisonForms per page)

### 📚 Examples
- **ADDED**: `examples/dynamic_forms_example.py` demonstrating template routes with dynamic forms and ComparisonForm rows

### 🧪 Testing
- **ADDED**: Integration tests for dynamic template routes (`tests/integration/test_dynamic_form_routes.py`)

---

## Version 0.3.13 (2026-01-16)

### 🔧 Bug Fixes

#### Nested Pill Field Copy in ComparisonForm
- **FIXED**: Copying nested `List[Literal]` pill fields inside `List[BaseModel]` items now works correctly
- **FIXED**: `performListCopyByPosition()` now detects and handles pill containers (DIV elements) that don't have a `name` attribute
- **FIXED**: Subfield copy for nested pills (e.g., `reviews[0].aspects`) now properly copies pill values
- **FIXED**: Full list copy now preserves nested pill field values
- **ADDED**: `copyPillContainer()` helper function to centralize pill copy logic across all copy operations

### 📚 Examples
- **ENHANCED**: `copy_example.py` now demonstrates nested pill field copy with `Review.aspects` field

---

## Version 0.3.12 (2026-01-15)

### 🎉 New Features

#### List[Literal] / List[Enum] Pill Fields
- **NEW**: `ListChoiceFieldRenderer` renders `List[Literal]` and `List[Enum]` as pill/tag selectors with add/remove UI
- **ENHANCED**: Pill fields now support reliable copy between ComparisonForm sides (including nested list items)

### 🔧 Bug Fixes & Improvements

#### ComparisonForm Copy Reliability
- **FIXED**: Subfield copy (e.g., `reviews[0].rating`) updates existing target items instead of creating new ones
- **FIXED**: Copy logic handles `new_` placeholder indices for newly added list items
- **IMPROVED**: Full list copy aligns list lengths before copying and preserves accordion state

#### Pill Copy Behavior
- **FIXED**: Copying pill fields now clears extra target pills when the source has fewer selections
- **IMPROVED**: Source/target pill containers are resolved deterministically via form prefix metadata

### 🧪 Testing
- **NEW**: ComparisonForm pill copy tests (top-level and nested list contexts)
- **IMPROVED**: JavaScript helper tests updated to reflect current copy behavior (no expected failures)

---

## Version 0.3.11 (2026-01-08)

### 🔧 Bug Fixes

#### Field Renderer ID Sanitization
- **FIXED**: Sanitize self.prefix in full_card_id as well

---

## Version 0.3.10 (2026-01-07)

### 🔧 Bug Fixes

#### Field Renderer ID Sanitization
- **FIXED**: Field names containing dots or slashes now generate valid CSS selector IDs
- **IMPROVED**: Sanitizes dots and slashes to underscores in field renderers for proper HTMX targeting
- **ENHANCED**: Affects BaseModelFieldRenderer, ListFieldRenderer, and form name handling

---

## Version 0.3.9 (2025-11-19)

### 🔧 Bug Fixes

#### ComparisonForm SkipJsonSchema Fields
- **FIXED**: Nested SkipJsonSchema fields now render correctly in ComparisonForm when included in `keep_skip_json_fields`
- **FIXED**: Both nested BaseModel fields (e.g., `main_address.internal_id`) and List[BaseModel] fields (e.g., `other_addresses.audit_notes`) now work properly
- **ENHANCED**: ComparisonForm now correctly passes `keep_skip_json_pathset` to field renderers

### 🧪 Testing
- **NEW**: Comprehensive test suite for SkipJsonSchema fields in ComparisonForm (8 tests)
- **NEW**: Example demonstrating ComparisonForm with different `keep_skip_json_fields` configurations

### 📦 Dependencies
- **UPDATED**: Migrated from deprecated `tool.uv.dev-dependencies` to `dependency-groups.dev` in pyproject.toml

---

## Version 0.3.8 (2025-10-02)

### 🎉 New Features

#### Intelligent Copying in ComparisonForm
- **NEW**: Comprehensive copy functionality at multiple granularity levels
  - Individual field copying
  - Full nested BaseModel object copying
  - Individual fields within nested models
  - **Full list field copying with automatic length alignment**
  - Individual list item copying with smart insertion


### 🔧 Bug Fixes & Improvements

#### SkipJsonSchema Field Handling
- **FIXED**: SkipJsonSchema fields now properly preserve initial values when provided
- **IMPROVED**: Better handling of skip fields with default values
- **ENHANCED**: More robust field introspection for SkipJsonSchema annotation


## Version 0.3.7 (2025-09-19)

### 🎉 New Features

#### SkipJsonSchema Field Support with Selective Override
- **NEW**: Added comprehensive support for fields marked with `SkipJsonSchema` annotation
- **NEW**: `keep_skip_json_fields` parameter allows selective inclusion of specific SkipJsonSchema fields
  - Supports dot-notation paths for nested fields (e.g., `"addresses.internal_id"`)
  - Enables fine-grained control over which internal fields are exposed in forms
  - Works with complex nested structures and list fields
- **ENHANCED**: SkipJsonSchema fields are automatically excluded from form rendering by default
- **IMPROVED**: Better field introspection for complex type scenarios including optional skip fields

### 🔧 Bug Fixes & Improvements

#### Default Values Handling
- **FIXED**: Default values for simple fields now work correctly without initial values
- **IMPROVED**: Better handling of field defaults when no initial values are provided
- **ENHANCED**: More robust form rendering for fields with default values

#### Documentation & Examples
- **UPDATED**: README.md with SkipJsonSchema handling documentation
- **ENHANCED**: Complex example updated to demonstrate SkipJsonSchema usage patterns
- **IMPROVED**: Better code documentation and examples

### 🧪 Testing
- **NEW**: Comprehensive test coverage for SkipJsonSchema field handling
- **NEW**: Tests for default values behavior without initial values
- **IMPROVED**: Enhanced test coverage for edge cases and type introspection

### 📊 Statistics
- **7 commits** since v0.3.6
- Focus on optional field handling and default value improvements
- Enhanced SkipJsonSchema support with comprehensive testing

**Key Highlights:**
This release significantly improves handling of optional fields, particularly those marked with `SkipJsonSchema`, and fixes important issues with default value handling when no initial values are provided.

---

## Version 0.3.6 (2025-07-21)

- **NEW**: can now pass new metrics_dict to `.with_initial_values()` helper method.

---
## Version 0.3.5 (2025-07-17)

- **NEW**: Added support for `decimal.Decimal` fields with dedicated field renderer
- **FIXED**: Scientific notation display issues in decimal values  
- **IMPROVED**: MyPy type checking compliance

---

## Version 0.3.4 (2025-07-15)

- **NEW**: Added support for Optional[List[..]] types in form fields

## Version 0.3.3 (2025-07-09)

- fix bug where label_color was not passed down in ComparisonForm
## Version 0.3.2 (2025-07-05)

### 🔧 UI/UX Improvements

#### Form Interaction Enhancements
- **IMPROVED**: Better handling of falsy values in StringFieldRenderer for more robust form inputs
- **ENHANCED**: Accordion state preservation across refresh operations for improved user experience
- **FIXED**: Dropdown events no longer trigger accordion sync in comparison forms, preventing UI conflicts

#### String Field Enhancements
- **NEW**: Textarea input support for better handling of longer text fields
- **IMPROVED**: StringFieldRenderer robustness with better code quality and error handling
- **ENHANCED**: Fallback handling for string values with comprehensive test coverage

#### List Management Improvements
- **ENHANCED**: List items now behave like BaseModel accordions for consistent UI patterns
- **IMPROVED**: Better default values for new list items
- **FIXED**: Nested list item accordion synchronization in ComparisonForm

### 🐛 Bug Fixes

#### Performance & Logging
- **FIXED**: Reduced excessive DEBUG logging messages for cleaner console output
- **IMPROVED**: Overall application performance with optimized refresh operations

#### Scroll & Navigation
- **NEW**: Scroll position preservation during form refresh operations
- **ENHANCED**: UI improvements for refresh and reset actions with better visual feedback

### 📚 Documentation & Examples

#### Enhanced Examples
- **UPDATED**: Annotation example with cleanup and improvements
- **IMPROVED**: Comparison example with better demonstration of features
- **ENHANCED**: README.md with updated documentation and usage examples

### 📊 Statistics
- **24 commits** since v0.3.1
- Focus on UI polish, form interaction improvements, and string field enhancements
- Improved logging and performance optimizations
- Enhanced documentation and examples

**Key Highlights:**
This release focuses on improving form interaction quality, with particular attention to string field handling, scroll preservation, and accordion state management. The textarea support and better falsy value handling make forms more robust for real-world usage scenarios.

---

## Version 0.3.1 (2025-06-24)

- fix datetime.time renderer when format is not HH:MM 

## Version 0.3.0 (2025-06-23)

### 🎉 Major Features

#### Metrics and Highlighting System
- **NEW**: Advanced metrics support with `metrics_dict` parameter
  - Field-level metrics with visual highlighting through colored bars
  - Supports numeric metrics with automatic color scaling
  - Nested field metrics support for complex data structures

#### ComparisonForm Component
- **NEW**: Side-by-side form comparison functionality
  - Dual-pane interface for comparing two related forms
  - Synchronized accordion states between left and right forms
  - Independent reset and refresh buttons for each form
#### List Enhancement Features
- **NEW**: List item indexes display for better navigation
- **NEW**: Number of items counter for list fields


### 🔧 Enhancements
#### Examples & Documentation
- **NEW**: `comparison_example.py` demonstrating side-by-side form usage
- **NEW**: `metrics_example.py` showcasing metrics and highlighting features
- **UPDATED**: `complex_example.py` with enhanced examples and descriptions


---

## Version 0.2.5 (2025-06-19)

- Fix bug with empty lists. Now should parse correctly to empty lists instead of returning defaults.
## Version 0.2.4 (2025-06-18)

- Added support for SkipJsonSchema fields. They will automatically be excluded from the form and defaults used for validation. 
## Version 0.2.3 (2025-06-16 )

- Removed the custom css injection for compact spacing. Instead applying to components directly. 


## Version 0.2.2 (2025-06-16 )

- fix left alignment issue with inputs in the presence of outside css influences

## Version 0.2.1 

### 🔧 UI/UX Improvements

#### Compact Layout Enhancements
- **IMPROVED**: Compact mode layout with better spacing and visual hierarchy
  - Input fields now positioned next to labels in compact mode for better space utilization
  - Checkbox fields properly aligned next to their labels for boolean values
  - Refined spacing adjustments for improved visual density

#### Form Structure Simplification
- **SIMPLIFIED**: Removed accordion UI for simple fields to reduce visual complexity
- **ENHANCED**: Better form organization with streamlined interface elements

### 🐛 Bug Fixes

#### List Handling Improvements
- **FIXED**: Nested list functionality with proper rendering and interaction
- **FIXED**: List collapse behavior for better user experience
- **FIXED**: Form-specific list IDs to prevent conflicts in multi-form scenarios
- **FIXED**: List refresh mechanism for dynamic content updates
- **ADDED**: Comprehensive support for nested lists with proper state management

#### Styling & Color Fixes
- **FIXED**: Color assignment issues in UI components
- **IMPROVED**: Better scoped compact CSS to prevent style conflicts

### ✅ Testing & Quality

#### Test Suite Improvements
- **UPDATED**: Enhanced integration tests for enum field renderers
- **FIXED**: Nested list test cases now passing
- **REMOVED**: Outdated accordion tests to match simplified UI

### 📊 Statistics
- **15 commits** since v0.2.0
- Focus on UI polish, nested list support, and compact mode refinements
- Improved test coverage for complex form scenarios

**Key Comparison to v0.2.0:**
While v0.2.0 introduced major features like enum support and compact mode, v0.2.1 focuses on polishing these features with better UX, fixing edge cases in nested lists, and simplifying the overall form interface.

---

## Version 0.2.0 

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
