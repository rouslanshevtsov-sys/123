#!/usr/bin/env python3
"""Негативные тесты навыка analyze-vk-best-posts: проверки должны БЛОКИРОВАТЬ запуск.

Случаи:
- отсутствующий / повреждённый / неполный competitor_set.json;
- недопустимый тип конкурента;
- отсутствие VK-токена;
- TLS/сетевая ошибка транспорта (после исчерпания повторов — фиксация в unavailable);
- ноль скачанных изображений при ожидавшихся;
- ноль скачанных клипов при подтверждённых клипах;
- необработанный клип (failed:*);
- повреждённые медиапути;
- деградированный запуск без согласия пользователя и с согласием;
- подмена просмотров клипа просмотрами поста -> валидатор отклоняет.
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import Harness, SCRIPTS, run_script, write_json  # noqa: E402

sys.path.insert(0, SCRIPTS)


def _expect_fail(proc, needle):
    assert proc.returncode != 0 or "STOP" in proc.stdout or needle in proc.stdout + proc.stderr, \
        f"ожидалась блокировка '{needle}', получили:\n{proc.stdout}\n{proc.stderr}"


def test_missing_competitor_set():
    h = Harness()
    try:
        p = run_script("check_env.py", "--workdir", h.d, expect_rc=None,
                       env_extra={"VK_TOKEN": "dummy-token-for-tests"})
        assert p.returncode == 1 and "Входной файл не найден" in p.stdout
    finally:
        h.cleanup()


def test_corrupted_competitor_set():
    h = Harness()
    try:
        with open(os.path.join(h.d, "competitor_set.json"), "w") as f:
            f.write("{ not valid json ]")
        p = run_script("check_env.py", "--workdir", h.d, expect_rc=None,
                       env_extra={"VK_TOKEN": "dummy-token-for-tests"})
        assert p.returncode == 1 and "Повреждённый JSON" in p.stdout
    finally:
        h.cleanup()


def test_incomplete_competitor_set():
    h = Harness()
    try:
        write_json(h.d, "competitor_set.json", {"competitors": [
            {"name": "<A>", "type": "direct"}]})  # нет ссылки/id
        p = run_script("check_env.py", "--workdir", h.d, expect_rc=None,
                       env_extra={"VK_TOKEN": "dummy-token-for-tests"})
        assert p.returncode == 1 and "нет ссылки/идентификатора сообщества VK" in p.stdout
    finally:
        h.cleanup()


def test_bad_type():
    h = Harness()
    try:
        write_json(h.d, "competitor_set.json", {"competitors": [
            {"name": "<A>", "type": "weird", "vk_url": "https://vk.com/x"}]})
        p = run_script("check_env.py", "--workdir", h.d, expect_rc=None,
                       env_extra={"VK_TOKEN": "dummy-token-for-tests"})
        assert p.returncode == 1 and "недопустимый тип" in p.stdout
    finally:
        h.cleanup()


def test_no_token():
    h = Harness()
    try:
        write_json(h.d, "competitor_set.json", {"competitors": [
            {"name": "<A>", "type": "direct", "vk_url": "https://vk.com/example_a"}]})
        env = dict(os.environ)
        env.pop("VK_TOKEN", None)
        cmd_env = {k: v for k, v in env.items() if k != "VK_TOKEN"}
        p = run_script("check_env.py", "--workdir", h.d, expect_rc=None,
                       env_extra={"VK_TOKEN": ""})
        # пустая строка фолбэкнется на .token — проверим явное удаление через subprocess env
        import subprocess
        pp = subprocess.run([sys.executable, os.path.join(SCRIPTS, "check_env.py"),
                             "--workdir", h.d], capture_output=True, text=True, env=cmd_env)
        assert pp.returncode == 1 and "Токен VK API не найден" in pp.stdout
    finally:
        h.cleanup()


def test_tls_error_recorded_as_unavailable():
    """TLS-исключение транспорта: после ретраев метод помечается ошибкой, пост уходит
    в unavailable с причиной, collect_posts не падает молча."""
    h = Harness()
    try:
        write_json(h.d, "competitors_resolved.json", [
            {"name": "<Группа A>", "type": "direct", "screen_name": "example_a",
             "group_id": None, "url": "https://vk.com/example_a"}])
        import vkapi
        calls = {"n": 0}

        def tls_transport(method, params):
            calls["n"] += 1
            raise OSError("SSLError: TLS handshake failed")

        vkapi.set_transport(tls_transport)
        orig_sleep = vkapi.time.sleep
        vkapi.time.sleep = lambda s: None
        vkapi.call.__defaults__ = (2, 0.01, *()) if False else vkapi.call.__defaults__
        os.environ["VK_WORK_DIR"] = h.d
        os.environ["VK_TOKEN"] = "dummy-token-for-tests"
        # уменьшим число повторов для теста
        orig_call = vkapi.call
        vkapi.call = lambda m, p=None, **kw: orig_call(m, p, max_retries=2, retry_pause=0.01)
        try:
            import collect_posts
            rc = collect_posts.main()
        finally:
            vkapi.call = orig_call
            vkapi.time.sleep = orig_sleep
            vkapi.set_transport(None)
        assert rc == 0
        unav = json.load(open(os.path.join(h.d, "unavailable.json"), encoding="utf-8"))
        assert any("TLS" in u["reason"] or "groups.getById" in u["reason"] or
                   "SSLError" in u["reason"] for u in unav), unav
    finally:
        h.cleanup()


def test_zero_images_blocks_gate():
    h = Harness(with_clip=False)
    try:
        h.write_stage1()
        h.finalize_outputs(allow_missing_images=True)
        h.build_reports()
        g = h.gate()
        assert g.returncode == 1 and "МЕДИАШЛЮЗ" in g.stdout and "изображения" in g.stdout, g.stdout
    finally:
        h.cleanup()


def test_zero_clips_downloaded_blocks_gate():
    """Подтверждённые клипы есть, но ни один не скачан/обработан (clips_processing пуст)."""
    h = Harness(with_clip=True)
    try:
        h.write_stage1()
        h.finalize_outputs()
        write_json(h.d, "clips_processing.json", [])   # имитация «ноль скачанных клипов»
        h.build_reports()
        g = h.gate()
        assert g.returncode == 1 and "clips_processing.json пуст" in g.stdout, g.stdout
    finally:
        h.cleanup()


def test_unprocessed_clip_blocks_gate():
    h = Harness(with_clip=True)
    try:
        h.write_stage1()
        h.finalize_outputs(degrade_clip_status="failed:download:HTTP 403")
        h.build_reports()
        g = h.gate()
        assert g.returncode == 1 and "необработанные подтверждённые клипы" in g.stdout, g.stdout
        # с ЯВНЫМ согласием пользователя — разрешено
        g2 = h.gate(extra=("--allow-degraded",))
        assert g2.returncode == 0 and "разрешён явным согласием" in g2.stdout, g2.stdout
    finally:
        h.cleanup()


def test_broken_media_paths_block_gate():
    h = Harness(with_clip=False)
    try:
        h.write_stage1()
        h.finalize_outputs(broken_media=True)
        h.build_reports()
        g = h.gate()
        assert g.returncode == 1 and "Медиапуть повреждён" in g.stdout, g.stdout
    finally:
        h.cleanup()


def test_degraded_without_consent_blocked():
    """Деградированный запуск (нет обязательных файлов) без --allow-degraded блокируется."""
    h = Harness(with_clip=False)
    try:
        h.write_stage1()
        # нет ни dataset, ни xlsx, ни clips — полностью деградированный итог
        g = h.gate()
        assert g.returncode == 1, g.stdout
        assert "Файл не найден" in g.stdout
        assert "Завершение заблокировано" in g.stdout
    finally:
        h.cleanup()


def test_validator_rejects_post_views_substitution():
    """Подмена просмотров клипа просмотрами поста: валидатор обязан отклонить,
    даже если арифметика ER внутри себя корректна."""
    h = Harness(with_clip=True)
    try:
        h.write_stage1()
        h.finalize_outputs(swap_post_views=True)
        h.build_reports()
        g = h.gate()
        assert g.returncode == 1, g.stdout
        out = g.stdout
        assert "views_source != 'clip'" in out or "по просмотрам клипа" in out, out
    finally:
        h.cleanup()


ALL_TESTS = [v for k, v in sorted(globals().items()) if k.startswith("test_")]

if __name__ == "__main__":
    failed = 0
    for fn in ALL_TESTS:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except Exception as e:
            failed += 1
            print(f"FAIL {fn.__name__}: {e}")
    sys.exit(1 if failed else 0)
