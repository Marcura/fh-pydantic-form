import sys

sys.path.insert(0, "/Users/oege/projects/fh-pydantic-form/src")

from decimal import Decimal
from typing import List, Optional

import pytest
from pydantic import BaseModel, Field, ValidationError

from fh_pydantic_form import PydanticForm


class TestDecimalFormIntegration:
    """Integration tests for decimal form handling"""

    @pytest.fixture
    def simple_decimal_model(self):
        """Simple model with decimal fields"""

        class SimpleDecimalModel(BaseModel):
            amount: Decimal
            optional_amount: Optional[Decimal] = None

        return SimpleDecimalModel

    @pytest.fixture
    def complex_decimal_model(self):
        """Complex model with various decimal fields"""

        class ComplexDecimalModel(BaseModel):
            price: Decimal
            cost: Optional[Decimal] = None
            tax_rate: Decimal = Decimal("0.08")
            discount: Optional[Decimal] = Field(default=None)
            total: Decimal = Field(default_factory=lambda: Decimal("0"))
            quantities: List[Decimal] = Field(default_factory=list)

        return ComplexDecimalModel

    @pytest.fixture
    def decimal_form_renderer(self, simple_decimal_model):
        """Form renderer for simple decimal model"""
        return PydanticForm("decimal_test", simple_decimal_model)

    @pytest.fixture
    def complex_decimal_form_renderer(self, complex_decimal_model):
        """Form renderer for complex decimal model"""
        return PydanticForm("complex_decimal_test", complex_decimal_model)

    def test_decimal_form_rendering(self, decimal_form_renderer):
        """Test complete form renders with decimal fields"""
        rendered_form = decimal_form_renderer.render_inputs()

        assert rendered_form is not None
        form_str = str(rendered_form)

        # Should contain decimal input fields
        assert "amount" in form_str.lower()
        assert "optional_amount" in form_str.lower()
        assert 'type="number"' in form_str
        assert 'step="any"' in form_str

    def test_decimal_form_with_initial_values(self, simple_decimal_model):
        """Test form with initial decimal values"""
        initial_values = simple_decimal_model(
            amount=Decimal("99.99"), optional_amount=Decimal("25.50")
        )

        form_renderer = PydanticForm(
            "decimal_test", simple_decimal_model, initial_values=initial_values
        )

        rendered_form = form_renderer.render_inputs()
        form_str = str(rendered_form)

        # Should contain the initial values
        assert "99.99" in form_str
        assert "25.50" in form_str

    def test_decimal_form_with_dict_initial_values(self, simple_decimal_model):
        """Test form with dict initial values containing decimals"""
        initial_dict = {"amount": Decimal("149.99"), "optional_amount": None}

        form_renderer = PydanticForm(
            "decimal_test", simple_decimal_model, initial_values=initial_dict
        )

        rendered_form = form_renderer.render_inputs()
        form_str = str(rendered_form)

        assert "149.99" in form_str

    @pytest.mark.parametrize(
        "form_data,expected_parsed",
        [
            # Basic decimal parsing
            ({"decimal_test_amount": "123.45"}, {"amount": "123.45"}),
            ({"decimal_test_amount": "0"}, {"amount": "0"}),
            ({"decimal_test_amount": "-99.99"}, {"amount": "-99.99"}),
            # Optional field handling
            (
                {"decimal_test_amount": "100.00", "decimal_test_optional_amount": ""},
                {"amount": "100.00", "optional_amount": None},
            ),
            (
                {
                    "decimal_test_amount": "100.00",
                    "decimal_test_optional_amount": "50.25",
                },
                {"amount": "100.00", "optional_amount": "50.25"},
            ),
            # High precision
            (
                {"decimal_test_amount": "3.14159265358979323846"},
                {"amount": "3.14159265358979323846"},
            ),
        ],
    )
    def test_decimal_form_parsing(
        self, decimal_form_renderer, form_data, expected_parsed
    ):
        """Test parsing form data with decimal fields"""
        parsed = decimal_form_renderer.parse(form_data)

        for key, expected_value in expected_parsed.items():
            assert parsed[key] == expected_value

    def test_decimal_form_parsing_missing_required(self, decimal_form_renderer):
        """Test parsing with missing required decimal field"""
        form_data = {"decimal_test_optional_amount": "25.00"}

        parsed = decimal_form_renderer.parse(form_data)

        # Required field should be missing from parsed data
        assert "amount" not in parsed
        assert parsed.get("optional_amount") == "25.00"

    @pytest.mark.asyncio
    async def test_decimal_model_validation_success(
        self, decimal_form_renderer, mocker
    ):
        """Test successful model validation with decimal values"""
        mock_request = mocker.Mock()
        mock_request.form = mocker.AsyncMock(
            return_value={
                "decimal_test_amount": "99.99",
                "decimal_test_optional_amount": "10.50",
            }
        )

        validated_model = await decimal_form_renderer.model_validate_request(
            mock_request
        )

        assert validated_model.amount == Decimal("99.99")
        assert validated_model.optional_amount == Decimal("10.50")

    @pytest.mark.asyncio
    async def test_decimal_model_validation_failure(
        self, decimal_form_renderer, mocker
    ):
        """Test model validation failure with invalid decimal values"""
        mock_request = mocker.Mock()
        mock_request.form = mocker.AsyncMock(
            return_value={
                "decimal_test_amount": "not_a_number",
                "decimal_test_optional_amount": "25.00",
            }
        )

        with pytest.raises(ValidationError) as exc_info:
            await decimal_form_renderer.model_validate_request(mock_request)

        # Should contain validation error for the invalid decimal
        assert "amount" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_decimal_model_validation_missing_required(
        self, decimal_form_renderer, mocker
    ):
        """Test model validation with missing required decimal field"""
        mock_request = mocker.Mock()
        mock_request.form = mocker.AsyncMock(
            return_value={"decimal_test_optional_amount": "25.00"}
        )

        with pytest.raises(ValidationError) as exc_info:
            await decimal_form_renderer.model_validate_request(mock_request)

        # Should contain validation error for missing required field
        assert "amount" in str(exc_info.value)

    def test_complex_decimal_form_rendering(self, complex_decimal_form_renderer):
        """Test complex form with multiple decimal field types"""
        rendered_form = complex_decimal_form_renderer.render_inputs()

        assert rendered_form is not None
        form_str = str(rendered_form)

        # Should contain all decimal fields
        expected_fields = ["price", "cost", "tax_rate", "discount", "total"]
        for field in expected_fields:
            assert field in form_str.lower()

    def test_complex_decimal_form_with_defaults(self, complex_decimal_model):
        """Test complex form uses default values correctly"""
        initial_values = complex_decimal_model(price=Decimal("199.99"))

        form_renderer = PydanticForm(
            "complex_decimal_test", complex_decimal_model, initial_values=initial_values
        )

        rendered_form = form_renderer.render_inputs()
        form_str = str(rendered_form)

        # Should show the provided price
        assert "199.99" in form_str
        # Should show the default tax rate
        assert "0.08" in form_str

    def test_decimal_form_list_parsing(self, complex_decimal_form_renderer):
        """Test parsing decimal list fields"""
        form_data = {
            "complex_decimal_test_price": "100.00",
            "complex_decimal_test_quantities_0": "5.5",
            "complex_decimal_test_quantities_1": "10.25",
            "complex_decimal_test_quantities_2": "3.75",
        }

        parsed = complex_decimal_form_renderer.parse(form_data)

        assert parsed["price"] == "100.00"
        assert parsed["quantities"] == ["5.5", "10.25", "3.75"]

    def test_decimal_form_refresh_preserves_values(self, decimal_form_renderer):
        """Test that form refresh preserves decimal values"""
        # Set initial state
        decimal_form_renderer.values_dict = {
            "amount": Decimal("88.88"),
            "optional_amount": Decimal("22.22"),
        }

        # Create form data as if submitted
        form_data = {
            "decimal_test_amount": "88.88",
            "decimal_test_optional_amount": "22.22",
        }

        parsed = decimal_form_renderer.parse(form_data)

        # Should preserve the decimal values
        assert parsed["amount"] == "88.88"
        assert parsed["optional_amount"] == "22.22"

    def test_decimal_form_reset_to_initial(self, simple_decimal_model):
        """Test that form reset returns to initial decimal values"""
        initial_values = simple_decimal_model(
            amount=Decimal("500.00"), optional_amount=Decimal("100.00")
        )

        form_renderer = PydanticForm(
            "decimal_test", simple_decimal_model, initial_values=initial_values
        )

        # Modify current values
        form_renderer.values_dict = {
            "amount": Decimal("999.99"),
            "optional_amount": Decimal("200.00"),
        }

        # Reset to initial
        form_renderer.reset_state()

        # Should return to initial values
        assert form_renderer.values_dict["amount"] == Decimal("500.00")
        assert form_renderer.values_dict["optional_amount"] == Decimal("100.00")

    def test_decimal_form_excluded_fields(self, complex_decimal_model):
        """Test decimal form with excluded fields"""
        form_renderer = PydanticForm(
            "complex_decimal_test",
            complex_decimal_model,
            exclude_fields=["cost", "discount"],
        )

        rendered_form = form_renderer.render_inputs()
        form_str = str(rendered_form)

        # Should not contain excluded fields
        assert "cost" not in form_str.lower()
        assert "discount" not in form_str.lower()

        # Should contain non-excluded fields
        assert "price" in form_str.lower()
        assert "tax_rate" in form_str.lower()

    def test_decimal_form_disabled_fields(self, complex_decimal_model):
        """Test decimal form with disabled fields"""
        form_renderer = PydanticForm(
            "complex_decimal_test",
            complex_decimal_model,
            disabled_fields=["price", "tax_rate"],
        )

        rendered_form = form_renderer.render_inputs()
        form_str = str(rendered_form)

        # Should contain disabled attributes for specified fields
        assert "disabled" in form_str

    def test_decimal_form_with_metrics(self, simple_decimal_model):
        """Test decimal form with metrics"""
        metrics_dict = {
            "amount": {"metric": 0.85, "color": "green", "comment": "Good value"},
            "optional_amount": {
                "metric": 0.92,
                "color": "blue",
                "comment": "Excellent value",
            },
        }

        form_renderer = PydanticForm(
            "decimal_test", simple_decimal_model, metrics_dict=metrics_dict
        )

        rendered_form = form_renderer.render_inputs()

        # Should render without error
        assert rendered_form is not None
