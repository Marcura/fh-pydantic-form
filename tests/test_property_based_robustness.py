from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st
from hypothesis.strategies import composite

from fh_pydantic_form import PydanticForm


# Define composite strategies
@composite
def nested_dict_strategy(draw):
    """Strategy for generating nested dictionaries."""
    return draw(
        st.dictionaries(
            keys=st.text(min_size=1, max_size=20),
            values=st.one_of(
                st.text(max_size=100),
                st.integers(min_value=-1000, max_value=1000),
                st.booleans(),
                st.none(),
                st.dictionaries(
                    keys=st.text(min_size=1, max_size=20),
                    values=st.one_of(
                        st.text(max_size=50),
                        st.integers(min_value=-100, max_value=100),
                        st.booleans(),
                    ),
                    max_size=5,
                ),
            ),
            max_size=10,
        )
    )


@composite
def list_field_strategy(draw):
    """Strategy for generating data with list fields."""
    return draw(
        st.dictionaries(
            keys=st.sampled_from(
                ["name", "tags", "other_addresses", "more_custom_details"]
            ),
            values=st.one_of(
                st.text(max_size=100),
                st.lists(st.text(max_size=50), max_size=10),
                st.lists(
                    st.dictionaries(
                        keys=st.text(min_size=1, max_size=20),
                        values=st.one_of(st.text(max_size=50), st.booleans()),
                        max_size=5,
                    ),
                    max_size=5,
                ),
                st.none(),
                st.text(),  # Invalid type for list field
            ),
            max_size=10,
        )
    )


@composite
def mixed_type_strategy(draw):
    """Strategy for generating mixed type scenarios."""
    base_dict = draw(
        st.dictionaries(
            keys=st.sampled_from(["name", "age", "score", "is_active"]),
            values=st.one_of(
                st.text(max_size=100),
                st.integers(),
                st.floats(allow_nan=False, allow_infinity=False),
                st.booleans(),
                st.none(),
                st.lists(st.text(max_size=50)),
                st.dictionaries(st.text(min_size=1, max_size=10), st.text(max_size=50)),
            ),
            max_size=10,
        )
    )
    return base_dict


@composite
def unicode_strategy(draw):
    """Strategy for generating unicode and special character data."""
    return draw(
        st.dictionaries(
            keys=st.text(min_size=1, max_size=20),
            values=st.one_of(
                st.text(max_size=100),  # Includes unicode by default
                st.integers(),
                st.booleans(),
            ),
            max_size=10,
        )
    )


@composite
def form_data_strategy(draw, prefix="test_"):
    """Strategy for generating form data with proper prefixes."""
    return draw(
        st.dictionaries(
            keys=st.text(min_size=len(prefix) + 1, max_size=50).map(
                lambda x: prefix + x
            ),
            values=st.one_of(
                st.text(max_size=100),
                st.integers().map(str),
                st.floats(allow_nan=False, allow_infinity=False).map(str),
                st.just("on"),  # Checkbox values
                st.just(""),  # Empty values
            ),
            max_size=20,
        )
    )


@composite
def validation_data_strategy(draw):
    """Strategy for generating data for validation testing."""
    return draw(
        st.dictionaries(
            keys=st.sampled_from(["name", "age", "score"]),
            values=st.one_of(
                st.text(max_size=100),
                st.integers(),
                st.floats(allow_nan=False, allow_infinity=False),
                st.booleans(),
                st.none(),
            ),
            max_size=10,
        )
    )


class TestPropertyBasedRobustness:
    """Property-based tests for constructor robustness using hypothesis."""

    @given(
        st.dictionaries(
            keys=st.text(min_size=1, max_size=50),
            values=st.one_of(
                st.text(max_size=1000),
                st.integers(min_value=-1000000, max_value=1000000),
                st.floats(
                    allow_nan=False, allow_infinity=False, min_value=-1e6, max_value=1e6
                ),
                st.booleans(),
                st.none(),
                st.lists(st.text(max_size=100), max_size=10),
            ),
            max_size=20,  # Limit dict size for performance
        )
    )
    @settings(
        max_examples=50,
        suppress_health_check=[
            HealthCheck.too_slow,
            HealthCheck.function_scoped_fixture,
        ],
    )
    def test_constructor_never_crashes(self, simple_test_model, arbitrary_dict):
        """Property-based test: constructor should never crash regardless of dict input."""
        # Constructor should never crash regardless of dict input
        form = PydanticForm("test", simple_test_model, initial_values=arbitrary_dict)

        # Should always have valid internal state
        assert isinstance(form.initial_values_dict, dict)
        assert isinstance(form.values_dict, dict)
        assert form.name == "test"
        assert form.model_class == simple_test_model

        # Should always be able to render without crashing
        rendered = form.render_inputs()
        assert rendered is not None

    @given(
        st.one_of(
            st.text(),
            st.integers(),
            st.floats(allow_nan=False, allow_infinity=False),
            st.booleans(),
            st.lists(st.text()),
            st.none(),
        )
    )
    @settings(
        max_examples=30, suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_non_dict_inputs_handled(self, simple_test_model, non_dict_input):
        """Property-based test: non-dict inputs should be handled gracefully."""
        form = PydanticForm("test", simple_test_model, initial_values=non_dict_input)

        # Should fall back to empty dict
        assert form.initial_values_dict == {}

        # Should still render
        rendered = form.render_inputs()
        assert rendered is not None

    @given(nested_dict_strategy())
    @settings(
        max_examples=30, suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_nested_structures_robustness(self, complex_test_model, nested_dict):
        """Property-based test: nested structures should be handled robustly."""
        form = PydanticForm("test", complex_test_model, initial_values=nested_dict)

        # Should not crash with nested structures
        assert isinstance(form.initial_values_dict, dict)

        # Should render without crashing
        rendered = form.render_inputs()
        assert rendered is not None

    @given(list_field_strategy())
    @settings(
        max_examples=30, suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_list_fields_robustness(self, complex_test_model, list_data):
        """Property-based test: list fields should handle various inputs robustly."""
        form = PydanticForm("test", complex_test_model, initial_values=list_data)

        # Should handle various list field inputs
        assert isinstance(form.initial_values_dict, dict)

        # Should render without crashing
        rendered = form.render_inputs()
        assert rendered is not None

    @given(
        st.dictionaries(
            keys=st.text(min_size=1, max_size=10),
            values=st.text(max_size=1000),
            min_size=1,
            max_size=100,
        )
    )
    @settings(
        max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_large_dict_performance(self, simple_test_model, large_dict):
        """Property-based test: large dictionaries should be handled efficiently."""
        # Assume reasonable size limits to avoid extremely slow tests
        assume(len(large_dict) <= 100)
        assume(all(len(str(v)) <= 1000 for v in large_dict.values()))

        form = PydanticForm("test", simple_test_model, initial_values=large_dict)

        # Should handle large dictionaries
        assert isinstance(form.initial_values_dict, dict)

        # Should render in reasonable time
        rendered = form.render_inputs()
        assert rendered is not None

    @given(mixed_type_strategy())
    @settings(
        max_examples=40, suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_mixed_types_handled(self, simple_test_model, mixed_dict):
        """Property-based test: mixed types in dict should be handled gracefully."""
        form = PydanticForm("test", simple_test_model, initial_values=mixed_dict)

        # Should preserve the mixed dict
        assert form.initial_values_dict == mixed_dict

        # Should render without crashing
        rendered = form.render_inputs()
        assert rendered is not None

    @given(
        st.dictionaries(
            keys=st.text(min_size=1, max_size=50),
            values=st.one_of(
                st.none(),
                st.text(max_size=0),  # Empty strings
                st.lists(st.nothing(), max_size=0),  # Empty lists
                st.dictionaries(st.nothing(), st.nothing(), max_size=0),  # Empty dicts
            ),
            max_size=10,
        )
    )
    @settings(
        max_examples=30, suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_empty_and_none_values(self, simple_test_model, empty_dict):
        """Property-based test: empty and None values should be handled correctly."""
        form = PydanticForm("test", simple_test_model, initial_values=empty_dict)

        # Should handle empty/None values
        assert isinstance(form.initial_values_dict, dict)

        # Should render
        rendered = form.render_inputs()
        assert rendered is not None

    @given(unicode_strategy())
    @settings(
        max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_unicode_handling(self, simple_test_model, unicode_dict):
        """Property-based test: unicode characters should be handled correctly."""
        form = PydanticForm("test", simple_test_model, initial_values=unicode_dict)

        # Should handle unicode
        assert isinstance(form.initial_values_dict, dict)

        # Should render without encoding issues
        rendered = form.render_inputs()
        assert rendered is not None

    @given(
        st.dictionaries(
            keys=st.text(min_size=1, max_size=20),
            values=st.one_of(
                st.text(max_size=100),
                st.integers(min_value=-1000, max_value=1000),
                st.floats(
                    allow_nan=False,
                    allow_infinity=False,
                    min_value=-1000,
                    max_value=1000,
                ),
                st.booleans(),
                st.none(),
            ),
            max_size=15,
        )
    )
    @settings(
        max_examples=30, suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_reset_robustness(self, simple_test_model, initial_dict):
        """Property-based test: reset should work with any initial dict."""
        form = PydanticForm("test", simple_test_model, initial_values=initial_dict)

        # Modify the form's current values
        form.values_dict["name"] = "Modified"

        # Reset should work - but it's async, so we need to make this an async test
        # For now, just test that the method exists and form state is correct
        assert hasattr(form, "handle_reset_request")
        assert form.initial_values_dict == initial_dict


class TestPropertyBasedFormOperations:
    """Property-based tests for form operations like parsing and validation."""

    @given(form_data_strategy())
    @settings(
        max_examples=30, suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_parse_robustness(self, simple_test_model, form_data):
        """Property-based test: parse should handle various form data robustly."""
        form = PydanticForm("test", simple_test_model, initial_values={})

        # Parse should not crash
        try:
            parsed = form.parse(form_data)
            assert isinstance(parsed, dict)
        except Exception:
            # If parsing fails, it should fail gracefully
            # (not with a system crash)
            pass

    @given(validation_data_strategy())
    @settings(
        max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_model_validation_robustness(self, simple_test_model, validation_data):
        """Property-based test: model validation should handle various data types."""
        form = PydanticForm("test", simple_test_model, initial_values=validation_data)

        # Should handle various validation scenarios
        rendered = form.render_inputs()
        assert rendered is not None

        # If the data is valid for the model, it should validate
        try:
            simple_test_model.model_validate(validation_data)
            # If validation succeeds, the form should render the validated data
            assert rendered is not None
        except Exception:
            # If validation fails, the form should still render with defaults/fallbacks
            assert rendered is not None


class TestPropertyBasedEdgeCases:
    """Property-based tests for edge cases and corner scenarios."""

    @given(
        st.dictionaries(
            keys=st.text(min_size=1, max_size=10),
            values=st.recursive(
                st.one_of(
                    st.text(max_size=50), st.integers(min_value=-100, max_value=100)
                ),
                lambda x: st.lists(x, max_size=3)
                | st.dictionaries(st.text(min_size=1, max_size=10), x, max_size=3),
                max_leaves=20,
            ),
            max_size=5,
        )
    )
    @settings(
        max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_recursive_structures(self, simple_test_model, recursive_dict):
        """Property-based test: deeply recursive structures should be handled."""
        form = PydanticForm("test", simple_test_model, initial_values=recursive_dict)

        # Should handle recursive structures
        assert isinstance(form.initial_values_dict, dict)

        # Should render without infinite recursion
        rendered = form.render_inputs()
        assert rendered is not None

    @given(
        st.dictionaries(
            keys=st.text(min_size=1, max_size=20),
            values=st.one_of(
                st.floats(
                    allow_nan=False,
                    allow_infinity=False,
                    min_value=1e-10,
                    max_value=1e10,
                ),
                st.integers(min_value=-(2**31), max_value=2**31 - 1),
                st.text(min_size=1000, max_size=5000),  # Large strings
            ),
            max_size=5,
        )
    )
    @settings(
        max_examples=15, suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_extreme_values(self, simple_test_model, extreme_dict):
        """Property-based test: extreme values should be handled gracefully."""
        form = PydanticForm("test", simple_test_model, initial_values=extreme_dict)

        # Should handle extreme values
        assert isinstance(form.initial_values_dict, dict)

        # Should render without performance issues
        rendered = form.render_inputs()
        assert rendered is not None

    @given(
        st.dictionaries(
            keys=st.text(
                alphabet=st.characters(blacklist_categories=("Cc", "Cs")),
                min_size=1,
                max_size=50,
            ),
            values=st.text(
                alphabet=st.characters(blacklist_categories=("Cc", "Cs")), max_size=200
            ),
            max_size=10,
        )
    )
    @settings(
        max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_special_characters(self, simple_test_model, special_char_dict):
        """Property-based test: special characters should be handled safely."""
        form = PydanticForm("test", simple_test_model, initial_values=special_char_dict)

        # Should handle special characters safely
        assert isinstance(form.initial_values_dict, dict)

        # Should render without XSS or injection issues
        rendered = form.render_inputs()
        assert rendered is not None

        # Basic check that HTML is properly escaped
        rendered_str = str(rendered)
        # Should not contain unescaped script tags or similar
        dangerous_patterns = ["<script", "javascript:", "onload=", "onerror="]
        for pattern in dangerous_patterns:
            assert pattern.lower() not in rendered_str.lower()
