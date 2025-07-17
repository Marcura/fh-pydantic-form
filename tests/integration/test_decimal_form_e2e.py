import sys

sys.path.insert(0, "/Users/oege/projects/fh-pydantic-form/src")

from decimal import Decimal
from typing import List, Optional

import fasthtml.common as fh
import monsterui.all as mui
import pytest
from pydantic import BaseModel, Field, ValidationError
from starlette.testclient import TestClient

from fh_pydantic_form import PydanticForm


class TestDecimalFormE2E:
    """End-to-end tests for decimal form functionality"""

    @pytest.fixture(scope="module")
    def decimal_test_model(self):
        """Test model with decimal fields"""

        class ProductModel(BaseModel):
            name: str
            price: Decimal
            cost: Optional[Decimal] = None
            margin: Decimal = Decimal("0.30")
            tax_rate: Decimal = Decimal("0.08")
            quantities: List[Decimal] = Field(default_factory=list)

        return ProductModel

    @pytest.fixture(scope="module")
    def decimal_client(self, decimal_test_model):
        """TestClient for decimal form testing"""
        form_renderer = PydanticForm("product_form", decimal_test_model)
        app, rt = fh.fast_app(hdrs=[mui.Theme.blue.headers()], pico=False, live=False)

        @rt("/")
        def get():
            return fh.Div(
                mui.Container(
                    mui.CardHeader("Product Form"),
                    mui.Card(
                        mui.CardBody(
                            mui.Form(
                                form_renderer.render_inputs(),
                                mui.Button(
                                    "Submit", type="submit", cls=mui.ButtonT.primary
                                ),
                                hx_post="/submit",
                                hx_target="#result",
                                hx_swap="innerHTML",
                                id="test-form",
                            )
                        ),
                    ),
                    fh.Div(id="result"),
                ),
            )

        @rt("/submit", methods=["POST"])
        async def post_submit(req):
            try:
                validated = await form_renderer.model_validate_request(req)
                return fh.Pre(validated.model_dump_json(indent=2))
            except ValidationError as e:
                return fh.Pre(f"Validation Error: {e.json(indent=2)}")

        return TestClient(app)

    def test_decimal_form_render_structure(self, decimal_client, soup):
        """Test form renders with proper decimal input structure"""
        response = decimal_client.get("/")
        assert response.status_code == 200

        dom = soup(response.text)

        # Check for decimal input fields
        price_input = dom.find("input", {"name": "product_form_price"})
        assert price_input is not None
        assert price_input.get("type") == "number"
        assert price_input.get("step") == "any"

        cost_input = dom.find("input", {"name": "product_form_cost"})
        assert cost_input is not None
        assert cost_input.get("type") == "number"
        assert cost_input.get("step") == "any"

        margin_input = dom.find("input", {"name": "product_form_margin"})
        assert margin_input is not None
        assert margin_input.get("value") == "0.30"  # Default value

    def test_decimal_form_submission_valid(self, decimal_client, htmx_headers):
        """Test submitting valid decimal values"""
        response = decimal_client.post(
            "/submit",
            data={
                "product_form_name": "Test Product",
                "product_form_price": "49.99",
                "product_form_cost": "25.00",
                "product_form_margin": "0.35",
                "product_form_tax_rate": "0.0875",
            },
            headers=htmx_headers,
        )

        assert response.status_code == 200
        response_text = response.text

        # Should contain the submitted values
        assert "Test Product" in response_text
        assert "49.99" in response_text
        assert "25.00" in response_text
        assert "0.35" in response_text
        assert "0.0875" in response_text

    def test_decimal_form_submission_high_precision(self, decimal_client, htmx_headers):
        """Test submitting high precision decimal values"""
        response = decimal_client.post(
            "/submit",
            data={
                "product_form_name": "High Precision Product",
                "product_form_price": "3.14159265358979323846",
                "product_form_cost": "1.41421356237309504880",
                "product_form_margin": "0.12345678901234567890",
            },
            headers=htmx_headers,
        )

        assert response.status_code == 200
        response_text = response.text

        # Should preserve high precision
        assert "3.14159265358979323846" in response_text
        assert "1.41421356237309504880" in response_text

    def test_decimal_form_submission_negative_values(
        self, decimal_client, htmx_headers
    ):
        """Test submitting negative decimal values"""
        response = decimal_client.post(
            "/submit",
            data={
                "product_form_name": "Negative Value Product",
                "product_form_price": "-50.00",
                "product_form_cost": "-20.00",
                "product_form_margin": "-0.10",
            },
            headers=htmx_headers,
        )

        assert response.status_code == 200
        response_text = response.text

        # Should handle negative values
        assert "-50.00" in response_text
        assert "-20.00" in response_text
        assert "-0.10" in response_text

    def test_decimal_form_submission_optional_empty(self, decimal_client, htmx_headers):
        """Test submitting with optional decimal field empty"""
        response = decimal_client.post(
            "/submit",
            data={
                "product_form_name": "Optional Empty Product",
                "product_form_price": "100.00",
                "product_form_cost": "",  # Empty optional field
                "product_form_margin": "0.25",
            },
            headers=htmx_headers,
        )

        assert response.status_code == 200
        response_text = response.text

        # Should handle empty optional field as None
        assert "100.00" in response_text
        assert "null" in response_text.lower() or "none" in response_text.lower()

    def test_decimal_form_submission_invalid_values(self, decimal_client, htmx_headers):
        """Test validation errors with invalid decimal input"""
        response = decimal_client.post(
            "/submit",
            data={
                "product_form_name": "Invalid Product",
                "product_form_price": "not_a_number",
                "product_form_cost": "25.00",
                "product_form_margin": "invalid_decimal",
            },
            headers=htmx_headers,
        )

        assert response.status_code == 200
        response_text = response.text

        # Should contain validation error
        assert "Validation Error" in response_text
        assert "price" in response_text

    def test_decimal_form_submission_missing_required(
        self, decimal_client, htmx_headers
    ):
        """Test validation error with missing required decimal field"""
        response = decimal_client.post(
            "/submit",
            data={
                "product_form_name": "Missing Price Product",
                # Missing required price field
                "product_form_cost": "25.00",
                "product_form_margin": "0.30",
            },
            headers=htmx_headers,
        )

        assert response.status_code == 200
        response_text = response.text

        # Should contain validation error for missing required field
        assert "Validation Error" in response_text

    def test_decimal_form_submission_zero_values(self, decimal_client, htmx_headers):
        """Test submitting zero decimal values"""
        response = decimal_client.post(
            "/submit",
            data={
                "product_form_name": "Zero Value Product",
                "product_form_price": "0",
                "product_form_cost": "0.00",
                "product_form_margin": "0.0",
            },
            headers=htmx_headers,
        )

        assert response.status_code == 200
        response_text = response.text

        # Should handle zero values correctly
        assert "Zero Value Product" in response_text
        # Response should contain some form of zero (0, 0.0, 0.00)
        assert "0" in response_text

    def test_decimal_form_submission_scientific_notation(
        self, decimal_client, htmx_headers
    ):
        """Test submitting decimal values in scientific notation"""
        response = decimal_client.post(
            "/submit",
            data={
                "product_form_name": "Scientific Notation Product",
                "product_form_price": "1.23e2",  # 123.0
                "product_form_cost": "4.56e-2",  # 0.0456
                "product_form_margin": "7.89e1",  # 78.9
            },
            headers=htmx_headers,
        )

        assert response.status_code == 200
        response_text = response.text

        # Should contain the product name (successful validation)
        assert "Scientific Notation Product" in response_text

    def test_decimal_form_with_list_fields(self, decimal_client, htmx_headers):
        """Test decimal form with list of decimal values"""
        response = decimal_client.post(
            "/submit",
            data={
                "product_form_name": "List Product",
                "product_form_price": "100.00",
                "product_form_quantities_0": "5.5",
                "product_form_quantities_1": "10.25",
                "product_form_quantities_2": "3.75",
            },
            headers=htmx_headers,
        )

        assert response.status_code == 200
        response_text = response.text

        # Should contain the list values
        assert "5.5" in response_text
        assert "10.25" in response_text
        assert "3.75" in response_text

    def test_decimal_form_edge_case_very_large(self, decimal_client, htmx_headers):
        """Test with very large decimal values"""
        response = decimal_client.post(
            "/submit",
            data={
                "product_form_name": "Large Value Product",
                "product_form_price": "999999999999.99",
                "product_form_cost": "123456789012.34",
                "product_form_margin": "0.01",
            },
            headers=htmx_headers,
        )

        assert response.status_code == 200
        response_text = response.text

        # Should handle large values
        assert "999999999999.99" in response_text
        assert "123456789012.34" in response_text

    def test_decimal_form_edge_case_very_small(self, decimal_client, htmx_headers):
        """Test with very small decimal values"""
        response = decimal_client.post(
            "/submit",
            data={
                "product_form_name": "Small Value Product",
                "product_form_price": "0.0000000001",
                "product_form_cost": "0.0000000002",
                "product_form_margin": "0.0000000003",
            },
            headers=htmx_headers,
        )

        assert response.status_code == 200
        response_text = response.text

        # Should handle very small values (may be in scientific notation in JSON)
        assert "0.0000000001" in response_text or "1E-10" in response_text

    def test_decimal_form_placeholder_text(self, decimal_client, soup):
        """Test that decimal fields have appropriate placeholder text"""
        response = decimal_client.get("/")
        dom = soup(response.text)

        # Check placeholder text for required field
        price_input = dom.find("input", {"name": "product_form_price"})
        assert price_input is not None
        placeholder = price_input.get("placeholder", "")
        assert "price" in placeholder.lower()
        assert "optional" not in placeholder.lower()

        # Check placeholder text for optional field
        cost_input = dom.find("input", {"name": "product_form_cost"})
        assert cost_input is not None
        placeholder = cost_input.get("placeholder", "")
        assert "cost" in placeholder.lower()
        assert "optional" in placeholder.lower()

    def test_decimal_form_label_structure(self, decimal_client, soup):
        """Test that decimal fields have proper label structure"""
        response = decimal_client.get("/")
        dom = soup(response.text)

        # Check for proper label elements
        labels = dom.find_all("label")
        label_texts = [label.get_text().strip() for label in labels]

        # Should contain formatted field names
        assert any("Price" in text for text in label_texts)
        assert any("Cost" in text for text in label_texts)
        assert any("Margin" in text for text in label_texts)
        assert any("Tax Rate" in text for text in label_texts)
