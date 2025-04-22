from logging import getLogger
from typing import (
    Any,
    ClassVar,
    Dict,
    List,
    Optional,
    Tuple,
    Type,
)

from pydantic.fields import FieldInfo

from fh_pydantic_form.type_helpers import _get_underlying_type_if_optional

logger = getLogger(__name__)


class FieldRendererRegistry:
    """
    Registry for field renderers with support for type and predicate-based registration

    This registry manages:
    - Type-specific renderers (e.g., for str, int, bool)
    - Type-name-specific renderers (by class name)
    - Predicate-based renderers (e.g., for Literal fields)
    - List item renderers for specialized list item rendering

    It uses a singleton pattern to ensure consistent registration across the app.
    """

    _instance = None  # Add class attribute to hold the single instance

    # Use ClassVar for all registry storage
    _type_renderers: ClassVar[Dict[Type, Any]] = {}
    _type_name_renderers: ClassVar[Dict[str, Any]] = {}
    _predicate_renderers: ClassVar[List[Tuple[Any, Any]]] = []
    _list_item_renderers: ClassVar[Dict[Type, Any]] = {}

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            logger.debug("Creating new FieldRendererRegistry singleton instance.")
            cls._instance = super().__new__(cls)
        else:
            logger.debug("Returning existing FieldRendererRegistry singleton instance.")
        return cls._instance

    @classmethod
    def register_type_renderer(cls, field_type: Type, renderer_cls: Any) -> None:
        """Register a renderer for a field type"""
        cls._type_renderers[field_type] = renderer_cls

    @classmethod
    def register_type_name_renderer(
        cls, field_type_name: str, renderer_cls: Any
    ) -> None:
        """Register a renderer for a specific field type name"""
        cls._type_name_renderers[field_type_name] = renderer_cls

    @classmethod
    def register_type_renderer_with_predicate(cls, predicate_func, renderer_cls):
        """
        Register a renderer with a predicate function

        The predicate function should accept a field_info parameter and return
        True if the renderer should be used for that field.
        """
        cls._predicate_renderers.append((predicate_func, renderer_cls))

    @classmethod
    def register_list_item_renderer(cls, item_type: Type, renderer_cls: Any) -> None:
        """Register a renderer for list items of a specific type"""
        cls._list_item_renderers[item_type] = renderer_cls

    @classmethod
    def get_renderer(cls, field_name: str, field_info: FieldInfo) -> Any:
        """
        Get the appropriate renderer for a field

        The selection algorithm:
        1. Check exact type matches
        2. Check predicate renderers (for special cases like Literal fields)
        3. Check for subclass relationships
        4. Fall back to string renderer

        Args:
            field_name: The name of the field being rendered
            field_info: The FieldInfo for the field

        Returns:
            A renderer class appropriate for the field
        """
        # Get the field type (unwrap Optional if present)
        original_annotation = field_info.annotation
        field_type = _get_underlying_type_if_optional(original_annotation)

        # 1. Check exact type matches first
        if field_type in cls._type_renderers:
            return cls._type_renderers[field_type]

        # 2. Check predicates second
        for predicate, renderer in cls._predicate_renderers:
            if predicate(field_info):
                return renderer

        # 3. Check for subclass relationships
        if isinstance(field_type, type):
            for typ, renderer in cls._type_renderers.items():
                try:
                    if isinstance(typ, type) and issubclass(field_type, typ):
                        return renderer
                except TypeError:
                    # Handle non-class types
                    continue

        # 4. Fall back to string renderer
        from_imports = globals()
        return from_imports.get("StringFieldRenderer", None)

    @classmethod
    def get_list_item_renderer(cls, item_type: Type) -> Optional[Any]:
        """
        Get renderer for summarizing list items of a given type

        Args:
            item_type: The type of the list items

        Returns:
            A renderer class for list items, or None if none is registered
        """
        # Check for exact type match
        if item_type in cls._list_item_renderers:
            return cls._list_item_renderers[item_type]

        # Check for subclass matches
        for registered_type, renderer in cls._list_item_renderers.items():
            try:
                if isinstance(registered_type, type) and issubclass(
                    item_type, registered_type
                ):
                    return renderer
            except TypeError:
                continue

        return None
