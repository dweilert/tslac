from __future__ import annotations

import services.watch_service as svc


def test_start_scan_returns_bool(monkeypatch):
    monkeypatch.setattr(svc.watcher, "start_watch_scan_async", lambda: True)
    assert svc.start_scan() is True

    monkeypatch.setattr(svc.watcher, "start_watch_scan_async", lambda: False)
    assert svc.start_scan() is False


def test_save_watch_config_calls_store(monkeypatch):
    class _Cfg:
        settings = {"x": 1}

    called = {}

    monkeypatch.setattr(svc.watch_store, "load_watch", lambda: _Cfg())

    def fake_save_watch_from_lines(sites_text, topics_text, settings):
        called["args"] = (sites_text, topics_text, settings)

    monkeypatch.setattr(svc.watch_store, "save_watch_from_lines", fake_save_watch_from_lines)

    svc.save_watch_config(sites_text="a\nb", topics_text="t1")
    assert called["args"] == ("a\nb", "t1", {"x": 1})
