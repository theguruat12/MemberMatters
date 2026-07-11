import pytest
from rest_framework import status

from api_metrics.models import Metric

pytestmark = pytest.mark.django_db

URL = "/api/update-prom-metrics/"


def _create_all_metrics():
    """Create one latest row for every metric type, with the data shapes the
    endpoint expects when pushing values into the Prometheus gauges."""
    Metric.objects.create(
        name=Metric.MetricName.MEMBER_COUNT_TOTAL,
        data=[{"state": "active", "total": 5}],
    )
    Metric.objects.create(
        name=Metric.MetricName.MEMBER_COUNT_6_MONTHS,
        data=[{"state": "active", "total": 3}],
    )
    Metric.objects.create(
        name=Metric.MetricName.MEMBER_COUNT_12_MONTHS,
        data=[{"state": "active", "total": 2}],
    )
    Metric.objects.create(
        name=Metric.MetricName.SUBSCRIPTION_COUNT_TOTAL,
        data=[{"state": "active", "total": 4}],
    )
    Metric.objects.create(
        name=Metric.MetricName.MEMBERBUCKS_BALANCE_TOTAL,
        data={"value": 123.45},
    )
    Metric.objects.create(
        name=Metric.MetricName.MEMBERBUCKS_TRANSACTIONS_TOTAL,
        data=[{"type": "stripe", "total": 50.0}],
    )


def test_update_prom_metrics_succeeds_with_data(api_client):
    """Regression: /api/update-prom-metrics/ must not 500 when metric rows exist.

    Before the fix, getattr(api_metrics.metrics, metric.name) raised
    AttributeError -- the module is imported as `api_metrics`, so
    `api_metrics.metrics` resolved to a non-existent attribute and the endpoint
    returned 500 on every Celery push. It is now getattr(api_metrics,
    metric.name, None).
    """
    _create_all_metrics()

    response = api_client.post(URL)

    assert response.status_code == status.HTTP_200_OK


def test_update_prom_metrics_succeeds_with_no_data(api_client):
    """With no metric rows the loop is skipped and the endpoint still returns 200."""
    response = api_client.post(URL)

    assert response.status_code == status.HTTP_200_OK
