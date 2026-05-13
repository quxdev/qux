import datetime

from django.test import SimpleTestCase

from qux.utils.date import daterange, eomonth, fomonth


class TestEomonth(SimpleTestCase):
    def test_same_month(self):
        # End of January 2024
        result = eomonth(datetime.date(2024, 1, 15), 0)
        assert result == datetime.date(2024, 1, 31)

    def test_next_month(self):
        result = eomonth(datetime.date(2024, 1, 15), 1)
        assert result == datetime.date(2024, 2, 29)

    def test_leap_year_february(self):
        result = eomonth(datetime.date(2024, 1, 1), 1)
        assert result == datetime.date(2024, 2, 29)

    def test_non_leap_year_february(self):
        result = eomonth(datetime.date(2023, 1, 1), 1)
        assert result == datetime.date(2023, 2, 28)

    def test_december_wrap(self):
        result = eomonth(datetime.date(2024, 11, 15), 1)
        assert result == datetime.date(2024, 12, 31)

    def test_december_to_january_year_wrap(self):
        result = eomonth(datetime.date(2023, 12, 15), 1)
        assert result == datetime.date(2024, 1, 31)

    def test_multiple_months(self):
        result = eomonth(datetime.date(2024, 1, 15), 5)
        assert result == datetime.date(2024, 6, 30)


class TestFomonth(SimpleTestCase):
    def test_first_of_current_month(self):
        result = fomonth(datetime.date(2024, 3, 15), 0)
        assert result == datetime.date(2024, 3, 1)

    def test_first_of_next_month(self):
        result = fomonth(datetime.date(2024, 1, 15), 1)
        assert result == datetime.date(2024, 2, 1)

    def test_first_of_month_several_ahead(self):
        result = fomonth(datetime.date(2024, 1, 15), 3)
        assert result == datetime.date(2024, 4, 1)


class TestDaterange(SimpleTestCase):
    def test_forward_range(self):
        start = datetime.date(2024, 1, 1)
        end = datetime.date(2024, 1, 3)
        result = list(daterange(start, end))
        assert result == [
            datetime.date(2024, 1, 1),
            datetime.date(2024, 1, 2),
            datetime.date(2024, 1, 3),
        ]

    def test_reversed_range(self):
        start = datetime.date(2024, 1, 3)
        end = datetime.date(2024, 1, 1)
        result = list(daterange(start, end))
        assert result == [
            datetime.date(2024, 1, 1),
            datetime.date(2024, 1, 2),
            datetime.date(2024, 1, 3),
        ]

    def test_single_day(self):
        d = datetime.date(2024, 1, 1)
        result = list(daterange(d, d))
        assert result == [d]
