from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from qux.utils.mysql import resetsequence


class TestResetSequence(SimpleTestCase):
    def test_none_is_noop(self):
        # Should return immediately without error
        result = resetsequence(None)
        assert result is None

    @patch("qux.utils.mysql.connection")
    def test_with_sequence_sql(self, mock_connection):
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_connection.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_connection.ops.sequence_reset_sql.return_value = [
            "SELECT setval('seq', 1);",
        ]

        model1 = MagicMock()
        resetsequence([model1])

        mock_cursor.execute.assert_called_once_with("SELECT setval('seq', 1);")

    @patch("qux.utils.mysql.connection")
    def test_empty_sequence_sql_falls_back_to_alter(self, mock_connection):
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_connection.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_connection.ops.sequence_reset_sql.return_value = []

        model1 = MagicMock()
        model1._meta.db_table = "my_table"
        mock_connection.ops.quote_name.return_value = "`my_table`"

        resetsequence([model1])

        mock_connection.ops.quote_name.assert_called_once_with("my_table")
        mock_cursor.execute.assert_called_once_with("ALTER TABLE `my_table` AUTO_INCREMENT = 1;")
