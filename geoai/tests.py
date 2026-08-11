from datetime import date, datetime, timedelta

from django.test import SimpleTestCase
from django.utils import timezone

from .smart_services import _as_aware_datetime, _is_recent


class SmartDateCompatibilityTests(SimpleTestCase):
    def test_datefield_value_is_converted_to_aware_datetime(self):
        value = date.today()
        result = _as_aware_datetime(value)
        self.assertIsInstance(result, datetime)
        self.assertTrue(timezone.is_aware(result))

    def test_datetime_value_is_supported(self):
        value = timezone.now() - timedelta(hours=2)
        self.assertTrue(_is_recent(value, now=timezone.now(), seconds=86400))

    def test_date_value_is_supported(self):
        self.assertTrue(_is_recent(date.today(), now=timezone.now(), seconds=86400))

    def test_future_value_is_not_recent(self):
        future = timezone.now() + timedelta(days=1)
        self.assertFalse(_is_recent(future, now=timezone.now(), seconds=86400))
