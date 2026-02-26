# pylint: disable=import-outside-toplevel,wrong-import-position
import io
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock

from django.test import SimpleTestCase


def _ensure_xmlchemy_importable():
    """Ensure xmltodict and dicttoxml are available, mocking if necessary."""
    mocked = []
    if "xmltodict" not in sys.modules:
        mock_xmltodict = MagicMock()
        sys.modules["xmltodict"] = mock_xmltodict
        mocked.append("xmltodict")
    if "dicttoxml" not in sys.modules:
        mock_dicttoxml = MagicMock()
        sys.modules["dicttoxml"] = mock_dicttoxml
        mocked.append("dicttoxml")
    return mocked


_mocked_modules = _ensure_xmlchemy_importable()

from qux.utils.xmlchemy import (
    dict2xml_attr,
)  # noqa: E402  # pylint: disable=wrong-import-position

# Check if real xmltodict/dicttoxml are available
try:
    import xmltodict  # noqa: F401  # pylint: disable=unused-import
    import dicttoxml  # noqa: F401  # pylint: disable=unused-import

    HAS_XMLLIBS = not bool(_mocked_modules)
except (ImportError, AttributeError):
    HAS_XMLLIBS = False


class TestDict2xmlAttr(SimpleTestCase):
    """dict2xml_attr is pure Python with no external deps."""

    def test_dict_with_simple_attributes(self):
        data = {"id": "1", "name": "foo"}
        result = dict2xml_attr(data, rootnode="item")
        assert "<item" in result
        assert 'id="1"' in result
        assert 'name="foo"' in result

    def test_dict_with_nested_dict(self):
        data = {"id": "1", "child": {"name": "bar"}}
        result = dict2xml_attr(data, rootnode="item")
        assert "<child" in result
        assert 'name="bar"' in result

    def test_dict_with_nested_list(self):
        data = {"items": [{"name": "a"}, {"name": "b"}]}
        result = dict2xml_attr(data, rootnode="root")
        assert "<item" in result

    def test_list_input(self):
        data = [{"name": "a"}, {"name": "b"}]
        result = dict2xml_attr(data, rootnode="items")
        assert "<item" in result

    def test_none_rootnode_uses_objects(self):
        data = {"key": "val"}
        result = dict2xml_attr(data)
        assert "<objects" in result

    def test_empty_dict(self):
        data = {}
        result = dict2xml_attr(data, rootnode="empty")
        assert "<empty" in result

    def test_dict_with_children_has_closing_tag(self):
        data = {"child": {"name": "val"}}
        result = dict2xml_attr(data, rootnode="parent")
        assert "</parent>" in result

    def test_dict_no_children_self_closing(self):
        data = {"attr": "val"}
        result = dict2xml_attr(data, rootnode="item")
        assert "/>" in result


@unittest.skipUnless(HAS_XMLLIBS, "xmltodict/dicttoxml not installed")
class TestAlchemyXmltodict(SimpleTestCase):
    def test_file_path_input(self):
        from qux.utils.xmlchemy import alchemy_xmltodict

        xml_content = "<root><item>hello</item></root>"
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".xml", delete=False, encoding="utf-8"
        ) as f:
            f.write(xml_content)
            f.flush()
            path = f.name
        try:
            result = alchemy_xmltodict(path)
            assert result is not None
            assert "root" in result
            assert result["root"]["item"] == "hello"
        finally:
            os.unlink(path)

    def test_buffer_input(self):
        from qux.utils.xmlchemy import alchemy_xmltodict

        xml_content = "<root><name>test</name></root>"
        buf = io.StringIO(xml_content)
        result = alchemy_xmltodict(buf)
        assert result is not None
        assert result["root"]["name"] == "test"

    def test_nonexistent_path_returns_none(self):
        from qux.utils.xmlchemy import alchemy_xmltodict

        result = alchemy_xmltodict("/nonexistent/path/file.xml")
        assert result is None


@unittest.skipUnless(HAS_XMLLIBS, "xmltodict/dicttoxml not installed")
class TestAlchemyDictoxml(SimpleTestCase):
    def test_converts_dict_to_xml(self):
        from qux.utils.xmlchemy import alchemy_dictoxml

        data = {"name": "test", "value": "123"}
        result = alchemy_dictoxml(data)
        assert result is not None
        assert b"name" in result
        assert b"test" in result


class TestAlchemyXmltodictMocked(SimpleTestCase):
    """Cover alchemy_xmltodict and alchemy_dictoxml with mocked imports."""

    def test_alchemy_xmltodict_file_mocked(self):
        import importlib
        from unittest.mock import patch as _patch

        mock_xmltodict = MagicMock()
        mock_xmltodict.parse.return_value = {"root": {"key": "value"}}
        mock_dicttoxml = MagicMock()

        with _patch.dict(
            "sys.modules", {"xmltodict": mock_xmltodict, "dicttoxml": mock_dicttoxml}
        ):
            import qux.utils.xmlchemy as xmlchemy_mod

            importlib.reload(xmlchemy_mod)

            xml_content = "<root><key>value</key></root>"
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".xml", delete=False, encoding="utf-8"
            ) as f:
                f.write(xml_content)
                f.flush()
                path = f.name
            try:
                result = xmlchemy_mod.alchemy_xmltodict(path)
                assert result is not None
                assert result["root"]["key"] == "value"
            finally:
                os.unlink(path)

    def test_alchemy_xmltodict_buffer_mocked(self):
        import importlib
        from unittest.mock import patch as _patch

        mock_xmltodict = MagicMock()
        mock_xmltodict.parse.return_value = {"root": {"name": "test"}}
        mock_dicttoxml = MagicMock()

        with _patch.dict(
            "sys.modules", {"xmltodict": mock_xmltodict, "dicttoxml": mock_dicttoxml}
        ):
            import qux.utils.xmlchemy as xmlchemy_mod

            importlib.reload(xmlchemy_mod)

            buf = io.BytesIO(b"<root><name>test</name></root>")
            with _patch("os.path.exists", return_value=False):
                result = xmlchemy_mod.alchemy_xmltodict(buf)
            assert result is not None
            assert result["root"]["name"] == "test"

    def test_alchemy_xmltodict_none_mocked(self):
        import importlib
        from unittest.mock import patch as _patch

        mock_xmltodict = MagicMock()
        mock_dicttoxml = MagicMock()

        with _patch.dict(
            "sys.modules", {"xmltodict": mock_xmltodict, "dicttoxml": mock_dicttoxml}
        ):
            import qux.utils.xmlchemy as xmlchemy_mod

            importlib.reload(xmlchemy_mod)

            result = xmlchemy_mod.alchemy_xmltodict("/nonexistent/path/file.xml")
            assert result is None

    def test_alchemy_dictoxml_mocked(self):
        import importlib
        from unittest.mock import patch as _patch

        mock_xmltodict = MagicMock()
        mock_dicttoxml = MagicMock()
        mock_dicttoxml.dicttoxml.return_value = b"<name>test</name>"

        with _patch.dict(
            "sys.modules", {"xmltodict": mock_xmltodict, "dicttoxml": mock_dicttoxml}
        ):
            import qux.utils.xmlchemy as xmlchemy_mod

            importlib.reload(xmlchemy_mod)

            data = {"name": "test"}
            result = xmlchemy_mod.alchemy_dictoxml(data)
            assert result == b"<name>test</name>"
