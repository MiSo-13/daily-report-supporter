from app.resource_monitor import ProcessResourceMonitor


def test_format_resource_bytes_as_mb() -> None:
    assert ProcessResourceMonitor._format_bytes(512 * 1024 * 1024) == "512 MB"


def test_format_resource_bytes_as_gb() -> None:
    assert ProcessResourceMonitor._format_bytes(2 * 1024 * 1024 * 1024) == "2.0 GB"
