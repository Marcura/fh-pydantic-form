import pytest


@pytest.mark.integration
class TestNestedListMetrics:
    def test_nested_list_item_metrics(self, complex_nested_client, htmx_headers, soup):
        """Test metrics display in nested list structures."""
        # Add a nested tag to main_address
        response = complex_nested_client.post(
            "/form/test_complex_nested/list/add/main_address/tags",
            headers=htmx_headers,
        )
        assert response.status_code == 200
        dom = soup(response.text)
        # Should contain input for new tag
        input_elem = dom.find("input")
        assert input_elem is not None

    def test_dynamic_list_item_metrics(
        self, complex_nested_client, htmx_headers, soup, patch_time
    ):
        """Test metrics for dynamically added list items."""
        # Add two items to main_address.tags
        response1 = complex_nested_client.post(
            "/form/test_complex_nested/list/add/main_address/tags",
            headers=htmx_headers,
        )
        response2 = complex_nested_client.post(
            "/form/test_complex_nested/list/add/main_address/tags",
            headers=htmx_headers,
        )
        assert response1.status_code == 200
        assert response2.status_code == 200
        dom1 = soup(response1.text)
        dom2 = soup(response2.text)
        # Should have different input names/IDs (unless patch_time is used)
        input1 = dom1.find("input")
        input2 = dom2.find("input")
        assert input1 is not None
        assert input2 is not None
        if not patch_time:
            assert input1.get("name") != input2.get("name")
