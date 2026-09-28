#!/usr/bin/env python3
"""Фикстуры и харнес для тестов навыка analyze-vk-best-posts (только условные данные)."""
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.dirname(HERE)
SCRIPTS = os.path.join(SKILL_ROOT, "scripts")
sys.path.insert(0, SCRIPTS)

from common import MSK  # noqa: E402
from datetime import datetime, timedelta  # noqa: E402

JPEG_BYTES = bytes.fromhex(
    "ffd8ffe000104a46494600010100000100010000ffdb004300ffffffffffffff"
    "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
    "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
    "ffc0001108000a000a01011100021101031101ffc4001f00000105010101010101"
    "00000000000000000102030405060708090affc400b51000020103030204030505"
    "04040000017d01020300041105122131410613516107227114328191a1082342b1"
    "c11552d1f02433627282090a161718192025262728292a3435363738393a434445"
    "464748494a535455565758595a636465666768696a737475767778797a83848586"
    "8788898a92939495969798999aa2a3a4a5a6a7a8a9aab2b3b4b5b6b7b8b9bac2c3"
    "c4c5c6c7c8c9cad2d3d4d5d6d7d8d9dae1e2e3e4e5e6e7e8e9eaf1f2f3f4f5f6f7"
    "f8f9faffda000c03010002110311003f00f8ba8acaefe07fffda000801010000ff"
    "d9")


def make_workdir():
    d = tempfile.mkdtemp(prefix="vkbp_test_")
    os.makedirs(os.path.join(d, "media", "images"), exist_ok=True)
    os.makedirs(os.path.join(d, "media", "collages"), exist_ok=True)
    os.makedirs(os.path.join(d, "media", "clips"), exist_ok=True)
    return d


def write_json(d, name, data):
    with open(os.path.join(d, name), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)


def fake_run_meta(hours=168):
    end = datetime.now(MSK).replace(microsecond=0)
    start = end - timedelta(hours=hours)
    return {"run_started_at_msk": end.isoformat(),
            "window_start_msk": start.isoformat(),
            "window_end_msk": end.isoformat(),
            "window_hours": hours, "timezone": "Europe/Moscow"}, start, end


def photo_attachment(idx=0):
    return {"type": "photo", "photo": {
        "id": 100 + idx, "sizes": [
            {"type": "m", "url": f"https://im.example/alt_{idx}.jpg", "width": 130, "height": 130},
            {"type": "x", "url": f"https://im.example/big_{idx}.jpg", "width": 1300, "height": 1300}]}}


def clip_video_attachment(owner=-100, vid=5001, inner_type="short_video"):
    att = {"type": "video", "video": {"owner_id": owner, "id": vid,
                                      "title": "<условный клип>"}}
    if inner_type is not None:
        att["video"]["type"] = inner_type
    return att


def build_fixture_posts(with_clip=False, zero_views=True, pinned_old_excluded=True):
    """posts_analyzed.json: 2 сообщества; лучший пост каждого с изображением."""
    meta, ws, we = fake_run_meta()
    now_ts = int(datetime.now(MSK).timestamp())
    posts = [
        # сообщество A: обычный пост выше бенчмарка (лучший, с изображением)
        {"post_id": "-100_1", "owner_id": -100, "item_id": 1, "group_name": "<Группа A>",
         "group_type": "direct", "url": "https://vk.com/wall-100_1",
         "date_ts": now_ts - 3600, "date_msk": "2026-09-27 10:00",
         "text": "<текст поста 1>", "main_type": "Картинка", "has_poll": False,
         "is_giveaway": False, "likes": 30, "comments": 5, "reposts": 5,
         "views": 2000, "views_for_er": 2000, "views_source": "post",
         "er": 40 / 2000, "er_status": "ok",
         "images": [["https://im.example/big_0.jpg", (1300, 1300)]],
         "n_images": 1, "carousel": False, "videos": [], "clips": [],
         "pinned": False, "data_status": "ok"},
        # сообщество A: пост с нулевыми просмотрами -> ER не рассчитан
        {"post_id": "-100_2", "owner_id": -100, "item_id": 2, "group_name": "<Группа A>",
         "group_type": "direct", "url": "https://vk.com/wall-100_2",
         "date_ts": now_ts - 7200, "date_msk": "2026-09-27 09:00",
         "text": "<текст поста 2>", "main_type": "Текстовый пост", "has_poll": False,
         "is_giveaway": False, "likes": 10, "comments": 0, "reposts": 0,
         "views": 0, "views_for_er": 0, "views_source": "post",
         "er": None, "er_status": "ER не рассчитан",
         "images": [], "n_images": 0, "carousel": False, "videos": [], "clips": [],
         "pinned": False, "data_status": "ok"},
        # сообщество B: единственный валидный пост => бенчмарк = его ER => лучший
        {"post_id": "-200_7", "owner_id": -200, "item_id": 7, "group_name": "<Группа B>",
         "group_type": "attention", "url": "https://vk.com/wall-200_7",
         "date_ts": now_ts - 1800, "date_msk": "2026-09-27 11:00",
         "text": "<розыгрыш: подписка, лайк, до 1 числа, определим победителя>",
         "main_type": "Карусель", "has_poll": True, "is_giveaway": True,
         "likes": 20, "comments": 4, "reposts": 2, "views": 1000,
         "views_for_er": 1000, "views_source": "post",
         "er": 26 / 1000, "er_status": "ok",
         "images": [["https://im.example/big_1.jpg", (1300, 1300)],
                    ["https://im.example/big_2.jpg", (1300, 1300)]],
         "n_images": 2, "carousel": True, "videos": [], "clips": [],
         "pinned": False, "data_status": "ok"},
    ]
    if with_clip:
        posts.append(
            {"post_id": "-200_9", "owner_id": -200, "item_id": 9, "group_name": "<Группа B>",
             "group_type": "attention", "url": "https://vk.com/wall-200_9",
             "date_ts": now_ts - 900, "date_msk": "2026-09-27 12:00",
             "text": "<клип-пост>", "main_type": "Клип", "has_poll": False,
             "is_giveaway": False, "likes": 40, "comments": 6, "reposts": 4,
             "views": 100000, "views_for_er": 5000, "views_source": "clip",
             "clip_views_at_collection": 5000,
             "er": 50 / 5000, "er_status": "ok",
             "images": [], "n_images": 0, "carousel": False, "videos": [],
             "clips": [{"owner_id": -200, "id": 5001, "type": "short_video"}],
             "clip_needs_video_get": [],
             "pinned": False, "data_status": "ok"})
    for p in posts:
        bms = [x["er"] for x in posts if x["owner_id"] == p["owner_id"] and x["er"] is not None]
        p["benchmark"] = sum(bms) / len(bms) if bms else None
        if p["er"] is not None and p["benchmark"] is not None:
            p["is_best"] = p["er"] >= p["benchmark"]
            p["result"] = "Лучший" if p["is_best"] else "Обычный"
        else:
            p["is_best"] = False
            p["result"] = "ER не рассчитан"
    return meta, posts


def materialize_media(d, posts):
    """Создаёт файлы медиа, ожидаемые датасетом (условные JPEG-байты)."""
    for p in posts:
        files = []
        for i, (url, _) in enumerate(p.get("images") or []):
            fp = os.path.join(d, "media", "images", f"{p['post_id']}_{i}.jpg")
            with open(fp, "wb") as f:
                f.write(JPEG_BYTES)
            files.append(f"media/images/{p['post_id']}_{i}.jpg")
        if files:
            p["image_files"] = files
            cf = f"media/collages/{p['post_id']}.jpg"
            with open(os.path.join(d, cf), "wb") as f:
                f.write(JPEG_BYTES)
            p["collage_file"] = cf


def base_groups():
    return [
        {"name": "<Группа A>", "type": "direct", "screen_name": "example_a",
         "url": "https://vk.com/example_a", "vk_id": -100, "members_count": 50000,
         "resolved_name": "<Группа A>"},
        {"name": "<Группа B>", "type": "attention", "screen_name": "example_b",
         "url": "https://vk.com/example_b", "vk_id": -200, "members_count": 500000,
         "resolved_name": "<Группа B>"},
    ]


def run_script(script, *args, expect_rc=0, env_extra=None):
    """Запуск сценария как subprocess; возвращает CompletedProcess."""
    import subprocess
    cmd = [sys.executable, os.path.join(SCRIPTS, script), *map(str, args)]
    env = dict(os.environ)
    env.update(env_extra or {})
    p = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if expect_rc is not None:
        assert p.returncode == expect_rc, (
            f"{script} rc={p.returncode} (ожидался {expect_rc})\n"
            f"STDOUT:\n{p.stdout}\nSTDERR:\n{p.stderr}")
    return p


class Harness:
    def __init__(self, with_clip=False):
        self.d = make_workdir()
        self.meta, self.posts = build_fixture_posts(with_clip=with_clip)
        self.comments = [
            {"post_id": "-100_1", "comment_id": 1, "parent_id": 0, "from_id": 11,
             "date_ts": self.meta["window_start_msk"], "text": "<коммент>", "likes": 0},
            {"post_id": "-100_1", "comment_id": 2, "parent_id": 1, "from_id": 12,
             "date_ts": self.meta["window_start_msk"], "text": "<ответ>", "likes": 1},
        ]

    def write_stage1(self):
        write_json(self.d, "run_meta.json", self.meta)
        write_json(self.d, "posts_analyzed.json", self.posts)
        write_json(self.d, "comments_replies.json", self.comments)
        write_json(self.d, "groups.json", base_groups())
        write_json(self.d, "unavailable.json", [])

    def clips_processing(self, status="success"):
        out = []
        for p in self.posts:
            if p["main_type"] == "Клип":
                fpath = None
                if status in ("success", "no_speech"):
                    fpath = f"media/clips/-200_5001.mp4"
                    with open(os.path.join(self.d, fpath), "wb") as fh:
                        fh.write(b"\x00\x00\x00\x18ftypmp42conditional")
                out.append({"post_id": p["post_id"], "post_url": p["url"],
                            "group_name": p["group_name"], "outer_type": "video",
                            "inner_type": "short_video",
                            "clip_views": p.get("clip_views_at_collection"),
                            "file": fpath, "status": status,
                            "transcript": "<расшифровка>" if status == "success"
                            else ("no_speech" if status == "no_speech" else None)})
        return out

    def finalize_outputs(self, broken_media=False, allow_missing_images=False,
                         degrade_clip_status=None, swap_post_views=False):
        """Пишет оставшиеся артефакты финального состояния (для media_gate)."""
        materialize_media(self.d, self.posts)
        if broken_media:
            for p in self.posts:
                if p.get("collage_file"):
                    pass  # путь записан, файла нет — удалим все collage
            for fn in os.listdir(os.path.join(self.d, "media", "collages")):
                os.remove(os.path.join(self.d, "media", "collages", fn))
        if allow_missing_images:
            for p in self.posts:
                p.pop("image_files", None)
                p.pop("collage_file", None)
        clips = self.clips_processing(status=degrade_clip_status or "success")
        if swap_post_views:
            for p in self.posts:
                if p["main_type"] == "Клип":
                    p["views_for_er"] = p["views"]      # подмена!
                    p["views_source"] = "post"          # подмена!
                    p["er"] = (p["likes"] + p["comments"] + p["reposts"]) / p["views"]
        benchmarks = {}
        for p in self.posts:
            if p["er"] is not None:
                benchmarks.setdefault(str(p["owner_id"]), []).append(p["er"])
        benchmarks = {k: sum(v) / len(v) for k, v in benchmarks.items()}
        for p in self.posts:
            b = benchmarks.get(str(p["owner_id"]))
            p["benchmark"] = b
            if p["er"] is not None and b is not None:
                p["is_best"] = p["er"] >= b
                p["result"] = "Лучший" if p["is_best"] else "Обычный"
            else:
                p["is_best"] = False
                p["result"] = "ER не рассчитан"
        write_json(self.d, "posts_analyzed.json", self.posts)
        write_json(self.d, "benchmarks.json", benchmarks)
        write_json(self.d, "clips_processing.json", clips)
        unav = []
        if degrade_clip_status:
            unav.append({"object": "VK Клип -200_5001", "link": "https://vk.com/video-200_5001",
                         "reason": degrade_clip_status})
        write_json(self.d, "unavailable.json", unav)
        return clips

    def build_reports(self):
        run_script("build_outputs.py", "--workdir", self.d)

    def gate(self, extra=()):
        return run_script("media_gate.py", "--workdir", self.d, *extra, expect_rc=None)

    def cleanup(self):
        shutil.rmtree(self.d, ignore_errors=True)
