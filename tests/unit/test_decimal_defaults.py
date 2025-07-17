import sys

sys.path.insert(0, "/Users/oege/projects/fh-pydantic-form/src")

import decimal
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field

from fh_pydantic_form.defaults import default_for_annotation, default_dict_for_model


class TestDecimalDefaults:
    """Test decimal default value handling"""

    def test_decimal_default_for_annotation(self):
        """Test default_for_annotation returns Decimal('0') for Decimal type"""
        default_value = default_for_annotation(decimal.Decimal)

        assert isinstance(default_value, Decimal)
        assert default_value == Decimal("0")

    def test_optional_decimal_default_for_annotation(self):
        """Test default_for_annotation returns None for Optional[Decimal]"""
        default_value = default_for_annotation(Optional[decimal.Decimal])

        assert default_value is None

    def test_decimal_list_default_for_annotation(self):
        """Test default_for_annotation returns empty list for List[Decimal]"""
        default_value = default_for_annotation(List[decimal.Decimal])

        assert default_value == []

    def test_decimal_model_defaults_basic(self):
        """Test default_dict_for_model with basic decimal fields"""

        class DecimalModel(BaseModel):
            amount: Decimal
            optional_amount: Optional[Decimal] = None
            default_amount: Decimal = Decimal("100.00")

        defaults = default_dict_for_model(DecimalModel)

        assert defaults["amount"] == Decimal("0")
        assert defaults["optional_amount"] is None
        assert defaults["default_amount"] == Decimal("100.00")

    def test_decimal_model_defaults_with_factory(self):
        """Test default_dict_for_model with decimal factory defaults"""

        class DecimalFactoryModel(BaseModel):
            base_amount: Decimal
            calculated_amount: Decimal = Field(default_factory=lambda: Decimal("50.25"))
            list_amounts: List[Decimal] = Field(default_factory=list)

        defaults = default_dict_for_model(DecimalFactoryModel)

        assert defaults["base_amount"] == Decimal("0")
        assert defaults["calculated_amount"] == Decimal("50.25")
        assert defaults["list_amounts"] == []

    def test_decimal_model_defaults_complex(self):
        """Test default_dict_for_model with complex decimal model"""

        class ComplexDecimalModel(BaseModel):
            # Required field
            price: Decimal

            # Optional field
            discount: Optional[Decimal] = None

            # Field with default
            tax_rate: Decimal = Decimal("0.08")

            # Field with factory
            processing_fee: Decimal = Field(default_factory=lambda: Decimal("2.50"))

            # List field
            amounts: List[Decimal] = Field(default_factory=list)

        defaults = default_dict_for_model(ComplexDecimalModel)

        assert defaults["price"] == Decimal("0")
        assert defaults["discount"] is None
        assert defaults["tax_rate"] == Decimal("0.08")
        assert defaults["processing_fee"] == Decimal("2.50")
        assert defaults["amounts"] == []

    def test_decimal_model_with_custom_default_method(self):
        """Test model with custom default classmethod"""

        class CustomDefaultDecimalModel(BaseModel):
            amount: Decimal
            rate: Decimal

            @classmethod
            def default(cls):
                return cls(amount=Decimal("999.99"), rate=Decimal("0.15"))

        defaults = default_dict_for_model(CustomDefaultDecimalModel)

        assert defaults["amount"] == Decimal("999.99")
        assert defaults["rate"] == Decimal("0.15")

    def test_decimal_model_with_nested_decimals(self):
        """Test default_dict_for_model with nested models containing decimals"""

        class PricingInfo(BaseModel):
            base_price: Decimal
            discount: Decimal = Decimal("0.10")

        class ProductModel(BaseModel):
            name: str
            pricing: PricingInfo

        defaults = default_dict_for_model(ProductModel)

        assert defaults["name"] == ""
        assert defaults["pricing"]["base_price"] == Decimal("0")
        assert defaults["pricing"]["discount"] == Decimal("0.10")

    def test_decimal_defaults_preserve_precision(self):
        """Test that default values preserve decimal precision"""

        class PrecisionModel(BaseModel):
            high_precision: Decimal = Decimal("3.14159265358979323846")
            currency: Decimal = Decimal("99.99")
            percentage: Decimal = Decimal("0.08250")

        defaults = default_dict_for_model(PrecisionModel)

        # Should preserve exact precision
        assert defaults["high_precision"] == Decimal("3.14159265358979323846")
        assert defaults["currency"] == Decimal("99.99")
        assert defaults["percentage"] == Decimal("0.08250")

    def test_decimal_defaults_with_enum_conversion(self):
        """Test decimal defaults work with enum conversion"""
        from enum import Enum

        class DecimalEnum(Enum):
            SMALL = Decimal("0.01")
            MEDIUM = Decimal("0.50")
            LARGE = Decimal("1.00")

        class EnumDecimalModel(BaseModel):
            size_value: DecimalEnum = DecimalEnum.MEDIUM

        defaults = default_dict_for_model(EnumDecimalModel)

        # Should convert enum to its decimal value
        assert defaults["size_value"] == Decimal("0.50")

    def test_decimal_defaults_negative_values(self):
        """Test decimal defaults with negative values"""

        class NegativeDecimalModel(BaseModel):
            debt: Decimal = Decimal("-100.00")
            adjustment: Decimal = Decimal("-0.05")

        defaults = default_dict_for_model(NegativeDecimalModel)

        assert defaults["debt"] == Decimal("-100.00")
        assert defaults["adjustment"] == Decimal("-0.05")

    def test_decimal_defaults_zero_values(self):
        """Test decimal defaults with various zero representations"""

        class ZeroDecimalModel(BaseModel):
            zero_plain: Decimal = Decimal("0")
            zero_decimal: Decimal = Decimal("0.0")
            zero_currency: Decimal = Decimal("0.00")

        defaults = default_dict_for_model(ZeroDecimalModel)

        assert defaults["zero_plain"] == Decimal("0")
        assert defaults["zero_decimal"] == Decimal("0.0")
        assert defaults["zero_currency"] == Decimal("0.00")

    def test_decimal_defaults_scientific_notation(self):
        """Test decimal defaults with scientific notation"""

        class ScientificDecimalModel(BaseModel):
            small_value: Decimal = Decimal("1.23e-6")
            large_value: Decimal = Decimal("4.56e10")

        defaults = default_dict_for_model(ScientificDecimalModel)

        assert defaults["small_value"] == Decimal("1.23e-6")
        assert defaults["large_value"] == Decimal("4.56e10")

    def test_decimal_list_defaults(self):
        """Test decimal defaults for list fields"""

        class ListDecimalModel(BaseModel):
            amounts: List[Decimal] = Field(default_factory=list)
            prices: List[Decimal] = Field(
                default_factory=lambda: [Decimal("10.00"), Decimal("20.00")]
            )

        defaults = default_dict_for_model(ListDecimalModel)

        assert defaults["amounts"] == []
        assert defaults["prices"] == [Decimal("10.00"), Decimal("20.00")]

    def test_decimal_defaults_type_consistency(self):
        """Test that decimal defaults maintain type consistency"""

        class TypeConsistencyModel(BaseModel):
            decimal_field: Decimal = Decimal("42.42")

        defaults = default_dict_for_model(TypeConsistencyModel)

        # Should be a Decimal, not float or string
        assert isinstance(defaults["decimal_field"], Decimal)
        assert defaults["decimal_field"] == Decimal("42.42")

        # Should not be equal to float (precision difference)
        assert defaults["decimal_field"] != 42.42
