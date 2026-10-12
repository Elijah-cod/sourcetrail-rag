from app import config
from app.config import cpu_threads, get_settings


def test_model_threads_setting_wins(monkeypatch):
    monkeypatch.setenv("MODEL_THREADS", "3")
    get_settings.cache_clear()
    try:
        assert cpu_threads() == 3
    finally:
        get_settings.cache_clear()


def test_threads_follow_the_container_cpu_quota(monkeypatch):
    # A 1-vCPU container on a many-core host: ONNX must not start one thread per host CPU.
    monkeypatch.delenv("MODEL_THREADS", raising=False)
    get_settings.cache_clear()
    monkeypatch.setattr(config, "_cgroup_cpu_quota", lambda: 1)
    monkeypatch.setattr(config.os, "sched_getaffinity", lambda pid: set(range(32)), raising=False)
    try:
        assert cpu_threads() == 1
    finally:
        get_settings.cache_clear()


def test_without_a_quota_all_usable_cpus_are_used(monkeypatch):
    monkeypatch.delenv("MODEL_THREADS", raising=False)
    get_settings.cache_clear()
    monkeypatch.setattr(config, "_cgroup_cpu_quota", lambda: None)
    monkeypatch.setattr(config.os, "sched_getaffinity", lambda pid: {0, 1, 2, 3}, raising=False)
    try:
        assert cpu_threads() == 4
    finally:
        get_settings.cache_clear()
