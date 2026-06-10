import datetime
from custom_components.grocy.helpers import (
    extract_base_url_and_path,
    serialize_datetime,
    ProductWrapper,
)


def test_extract_base_url_and_path():
    """Verify URL pathing extraction logic."""
    url = "https://grocy.example.com/subfolder/"
    base, path = extract_base_url_and_path(url)
    assert base == "https://grocy.example.com"
    assert path == "subfolder"


def test_serialize_datetime():
    """Verify ISO conversions process correctly."""
    dt = datetime.datetime(2023, 1, 1, 12, 0, 0)
    assert serialize_datetime(dt) == "2023-01-01T12:00:00"
    assert serialize_datetime("string") == "string"


def test_product_wrapper_picture_url():
    """Verify base64 encoding doesn't break string assignments."""

    class DummyProduct:
        picture_file_name = "test.png"

    class DummyResponse:
        product = DummyProduct()

    wrapper = ProductWrapper(DummyResponse())
    assert "productpictures" in wrapper.picture_url
