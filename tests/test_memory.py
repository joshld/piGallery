"""Exercise monitoring functions without starting the slideshow or Telegram."""
import ast
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, mock_open

import pytest


def gallery_function(name, **namespace):
    source = Path(__file__).resolve().parents[1] / 'gallery.py'
    tree = ast.parse(source.read_text(encoding='utf-8'))
    function = next(node for node in tree.body
                    if isinstance(node, ast.FunctionDef) and node.name == name)
    module = ast.Module(body=[function], type_ignores=[])
    exec(compile(ast.fix_missing_locations(module), str(source), 'exec'), namespace)
    return namespace[name]


@pytest.mark.parametrize('meminfo, expected', [
    ('MemFree: 20480 kB\nMemAvailable: 409600 kB\n', 400),
    ('MemAvailable: 409600 kB\nMemFree: 20480 kB\n', 400),
    ('MemFree: 20480 kB\nMemAvailable: 0 kB\n', 0),
    ('MemFree: 20480 kB\n', 20),
])
def test_available_memory_preference_and_older_kernel_fallback(meminfo, expected):
    read = gallery_function('get_memory_info', open=mock_open(read_data=meminfo),
                            PSUTIL_AVAILABLE=False)
    assert read() == expected


@pytest.mark.parametrize('failure', [FileNotFoundError, PermissionError])
def test_psutil_fallback_when_proc_unreadable(failure):
    read = gallery_function('get_memory_info', open=Mock(side_effect=failure),
                            PSUTIL_AVAILABLE=True,
                            psutil=SimpleNamespace(virtual_memory=lambda: SimpleNamespace(available=400 * 1024**2)))
    assert read() == 400


def test_unknown_memory_does_not_report_zero():
    read = gallery_function('get_memory_info', open=mock_open(read_data='MemAvailable: invalid\n'),
                            PSUTIL_AVAILABLE=False)
    assert read() is None


class StopMonitor(BaseException):
    pass


@pytest.mark.parametrize('available, alerts', [(400, 0), (20, 1), (0, 1), (None, 0)])
def test_monitor_only_alerts_when_available_memory_low(available, alerts):
    def stop(_):
        raise StopMonitor()

    notify = Mock()
    monitor = gallery_function('monitor_system_resources',
                               time=SimpleNamespace(time=lambda: 1000, sleep=stop),
                               get_memory_info=lambda: available,
                               get_cpu_usage=lambda: 0, get_cpu_temperature=lambda: 40)
    with pytest.raises(StopMonitor):
        monitor(notify)
    assert notify.notify_system_alert.call_count == alerts
    if alerts:
        args = notify.notify_system_alert.call_args[0]
        assert args[0] == 'memory'
        assert 'available' in args[1] and 'available' in args[2]
