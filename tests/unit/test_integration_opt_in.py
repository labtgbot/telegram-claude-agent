import importlib

import tests.integration.test_bot as integration_test_bot


def _reload_integration_tests(monkeypatch, *, enabled: bool):
    if enabled:
        monkeypatch.setenv("INTEGRATION_TEST", "1")
    else:
        monkeypatch.delenv("INTEGRATION_TEST", raising=False)

    return importlib.reload(integration_test_bot)


def _integration_skip_condition(module):
    mark = module.pytestmark.mark

    assert mark.name == "skipif"
    assert mark.kwargs["reason"] == (
        "integration tests require a live proxy; run manually with INTEGRATION_TEST=1"
    )
    assert isinstance(mark.args[0], bool)

    return mark.args[0]


def test_integration_tests_skip_without_opt_in(monkeypatch):
    module = _reload_integration_tests(monkeypatch, enabled=False)

    assert _integration_skip_condition(module) is True


def test_integration_tests_run_with_opt_in(monkeypatch):
    module = _reload_integration_tests(monkeypatch, enabled=True)

    assert _integration_skip_condition(module) is False
