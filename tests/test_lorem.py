from django.test import SimpleTestCase

from qux.lorem import Lorem


class TestLoremWords(SimpleTestCase):
    def test_default_n_returns_5_words(self):
        result = Lorem.words()
        assert len(result.split()) == 5

    def test_custom_n_returns_n_words(self):
        result = Lorem.words(n=3)
        assert len(result.split()) == 3

    def test_n_zero_returns_empty_string(self):
        result = Lorem.words(n=0)
        assert result == ""

    def test_n_one_returns_single_word(self):
        result = Lorem.words(n=1)
        assert len(result.split()) == 1
        assert " " not in result
