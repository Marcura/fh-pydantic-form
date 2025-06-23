import pytest
from pydantic.fields import FieldInfo

from fh_pydantic_form.field_renderers import (
    BooleanFieldRenderer,
    NumberFieldRenderer,
    StringFieldRenderer,
)


@pytest.fixture(scope="module")
def metrics_dict():
    """Sample metrics dictionary for testing."""
    return {
        "name": {"metric": 0.9, "comment": "Good name"},
        "age": {"metric": 0.5, "color": "#FFA500"},
        "is_active": {"metric": 0.8, "comment": "Activity status"},
        "address": {"metric": 0.6, "comment": "Address info"},
        "address.street": {"metric": 0.2, "comment": "Needs improvement"},
        "tags[0]": {"metric": 1.0},
        "addresses[0].city": {"metric": 0.7},
    }


@pytest.fixture
def field_info_factory():
    """Factory to create FieldInfo objects for testing."""

    def _make(annotation, **kwargs):
        return FieldInfo(annotation=annotation, **kwargs)

    return _make


@pytest.mark.integration
class TestFieldMetricsIntegration:
    @pytest.mark.parametrize(
        "renderer_class,field_name,field_type,value",
        [
            (StringFieldRenderer, "name", str, "Alice"),
            (NumberFieldRenderer, "age", int, 42),
            (BooleanFieldRenderer, "is_active", bool, True),
        ],
    )
    def test_field_renderer_with_metrics(
        self,
        renderer_class,
        field_name,
        field_type,
        value,
        metrics_dict,
        field_info_factory,
    ):
        """Test each field renderer type with metrics."""
        field_info = field_info_factory(field_type)
        renderer = renderer_class(
            field_name=field_name,
            field_info=field_info,
            value=value,
            field_path=[field_name],  # Add this line for correct metrics lookup
            metrics_dict=metrics_dict,
        )
        rendered_component = renderer.render()
        # Get actual HTML content instead of string representation
        html = (
            rendered_component.__html__()
            if hasattr(rendered_component, "__html__")
            else str(rendered_component)
        )
        # Should contain metric decoration (border or badge)
        assert "border-left" in html or "badge" in html or "uk-tooltip" in html

    def test_nested_model_metrics_resolution(self, complex_test_model, metrics_dict):
        """Test metrics resolution for nested models."""
        from fh_pydantic_form.field_renderers import BaseModelFieldRenderer

        field_info = FieldInfo(annotation=complex_test_model)
        renderer = BaseModelFieldRenderer(
            field_name="address",
            field_info=field_info,
            value=None,
            field_path=["address"],
            metrics_dict=metrics_dict,
        )
        rendered_component = renderer.render()
        # Get actual HTML content instead of string representation
        html = (
            rendered_component.__html__()
            if hasattr(rendered_component, "__html__")
            else str(rendered_component)
        )
        # Should contain metrics for nested fields if present in metrics_dict
        assert "border-left" in html or "uk-tooltip" in html

    def test_list_field_metrics(self, metrics_dict, field_info_factory):
        """Test metrics for list items with proper path resolution."""
        from typing import List

        from fh_pydantic_form.field_renderers import ListFieldRenderer

        field_info = field_info_factory(List[str])
        renderer = ListFieldRenderer(
            field_name="tags",
            field_info=field_info,
            value=["foo", "bar"],
            field_path=["tags"],
            metrics_dict=metrics_dict,
        )
        rendered_component = renderer.render()
        # Get actual HTML content instead of string representation
        html = (
            rendered_component.__html__()
            if hasattr(rendered_component, "__html__")
            else str(rendered_component)
        )
        # Should contain metrics for at least the first item
        assert "border-left" in html or "badge" in html
