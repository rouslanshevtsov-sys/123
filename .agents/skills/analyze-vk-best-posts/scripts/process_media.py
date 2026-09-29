#!/usr/bin/env python3
"""Этап 3: медиа — изображения лучших постов, коллажи, VK Клипы, Whisper-расшифровки.

Делает:
1) video.get по всем видео/клипам: подтверждение клипа (items[].type in short_video/clip),
   фиксация просмотров САМОГО клипа на момент сбора; если у клипа просмотры получены —
   ER поста пересчитывается по просмотрам клипа (views_source='clip').
2) Скачивание изображений лучших постов (~1600px, пропорции) в media/images с кэшем.
3) Коллажи в media/collages: 1 — целиком; 2 — рядом; 3–4 — сетка 2×2; >=5 — по 3 в ряд.
4) Скачивание подтверждённых клипов (MP4/HLS/DASH; при пустых files — video.getOembed
   и публичный плеер как fallback статуса). Обычные видео НЕ скачиваются.
5) Локальная расшифровка речи Whisper (модель не слабее small, VAD включён):
   статусы success / no_speech / failed:<причина>; очищенная дословная расшифровка.

Использование: python process_media.py [--workdir DIR] [--whisper-model small]
"""
import argparse
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import CLIP_INNER_TYPES, compute_er, load_json, path, save_json, benchmark_of  # noqa: E402
import vkapi  # noqa: E402

try:
    from PIL import Image
except Exception:  # pragma: no cover
    Image = None

try:
    import requests
except Exception:  # pragma: no cover
    requests = None

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64)"


def download_file(url, dest, session, max_bytes=200 * 1024 * 1024):
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return True, "cached"
    try:
        r = session.get(url, timeout=60, stream=True)
        if r.status_code != 200:
            return False, f"HTTP {r.status_code}"
        head = r.content[:12] if not r.raw else b""
        with open(dest, "wb") as f:
            written = 0
            for chunk in r.iter_content(65536):
                f.write(chunk)
                written += len(chunk)
                if written > max_bytes:
                    return False, "file too large"
        magic_ok = True
        if head:
            magic_ok = head[:3] == b"\xff\xd8\xff" or head[:8] == b"\x89PNG\r\n\x1a\n" \
                or head[4:8] in (b"ftyp",) or head[:4] == b"\x1aE\xdf\xa3"
        return (True, "downloaded") if magic_ok else (False, "not a media file")
    except Exception as e:
        try:
            os.remove(dest)
        except OSError:
            pass
        return False, f"{type(e).__name__}: {e}"


def build_collage(files, dest, cell=800):
    ims = []
    for f in files:
        try:
            im = Image.open(f).convert("RGB")
            im.thumbnail((cell * 2, cell * 2))
            ims.append(im)
        except Exception:
            continue
    n = len(ims)
    if n == 0:
        return None
    if n == 1:
        coll = ims[0]
        coll.thumbnail((1600, 1600))
    else:
        cols = 2 if n <= 4 else 3
        if n == 2:
            cols = 2
        rows = (n + cols - 1) // cols
        cw = ch = cell
        coll = Image.new("RGB", (cols * cw, rows * ch), (255, 255, 255))
        for k, im in enumerate(ims):
            im.thumbnail((cw, ch))
            x = (k % cols) * cw + (cw - im.width) // 2
            y = (k // cols) * ch + (ch - im.height) // 2
            coll.paste(im, (x, y))
    coll.save(dest, quality=85)
    return dest


def transcribe(video_path, model_name):
    """Whisper локально, модель >= small, VAD. Возвращает (status, transcript)."""
    text_parts, had_speech = [], False
    try:
        try:
            from faster_whisper import WhisperModel
            model = WhisperModel(model_name if model_name in
                                 ("small", "medium", "large-v2", "large-v3", "distil-large-v3")
                                 else "small", device="auto", compute_type="int8")
            segments, info = model.transcribe(video_path, language="ru",
                                              vad_filter=True, beam_size=5)
            for s in segments:
                t = (s.text or "").strip()
                if t:
                    had_speech = True
                    text_parts.append(t)
        except ImportError:
            import whisper
            model = whisper.load_model(model_name if model_name != "tiny" else "small")
            res = model.transcribe(video_path, language="ru", vad_filter=True)
            text_parts = [seg["text"].strip() for seg in res.get("segments", [])]
            had_speech = any(text_parts)
    except Exception as e:
        return f"failed:transcription_error:{type(e).__name__}:{str(e)[:120]}", None
    if not had_speech:
        return "no_speech", "no_speech"
    clean = polish_transcript(" ".join(text_parts))
    return "success", clean


def polish_transcript(text):
    """Очищенная дословность: пунктуация от Whisper сохранена, убраны только явные повторы.

    Числа, названия и CTA не изменяются; неразборчивые фрагменты помечаются [неразборчиво].
    """
    text = re.sub(r"\s+", " ", text).strip()
    # удаление явных речевых повторов подряд ("очень очень" -> "очень")
    text = re.sub(r"\b(\w+)(?:\s+\1\b){2,}", r"\1", text, flags=re.I)
    text = re.sub(r"\[(?:без звука|аплодисменты|музыка)\]", "", text, flags=re.I)
    text = re.sub(r"\s+", " ", text).strip()
    return text if text else "[неразборчиво]"


def pick_clip_download_url(item):
    """MP4 > HLS(DASH) из item['files']; возвращает (kind,url) или (None,None)."""
    files = item.get("files") or {}
    for k in ("mp4_max", "mp4_1080", "mp4_720", "mp4_480", "mp4_360"):
        if files.get(k):
            return "mp4", files[k]
    for k in ("hls", "dash"):
        v = files.get(k)
        url = v.get("playlist") if isinstance(v, dict) else v
        if url:
            return k, url
    return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workdir", default=None)
    ap.add_argument("--whisper-model", default="small")
    args = ap.parse_args()
    if args.workdir:
        os.environ["VK_WORK_DIR"] = args.workdir
    if Image is None or requests is None:
        print("STOP: отсутствуют медиазависимости (pillow/requests). Запусти scripts/check_env.py")
        return 1

    posts = load_json("posts_analyzed.json")
    unavailable = load_json("unavailable.json", default=[])
    sess = requests.Session()
    sess.headers["User-Agent"] = USER_AGENT

    # ---------- 1. video.get: подтверждение клипов + просмотры самого клипа ----------
    videoids = {}
    for p in posts:
        for v in (p["videos"] + p["clips"]):
            key = (v.get("owner_id"), v.get("id"))
            videoids[key] = v.get("access_key")
        for v in p.get("clip_needs_video_get", []):
            videoids[(v["owner_id"], v["video_id"])] = v.get("access_key")

    clip_info = {}
    for (own, vid), ak in videoids.items():
        if own is None or vid is None:
            continue
        k = f"{own}_{vid}" + (f"_{ak}" if ak else "")
        r = vkapi.call("video.get", {"videos": k})
        it = (r.get("response", {}).get("items") or [{}])[0] if "response" in r else {}
        inner_type = it.get("type")
        entry = {"inner_type": inner_type, "clip_views": it.get("count_views"),
                 "item": it, "error": None if it else str(r.get("error_msg", "empty"))[:120]}
        if inner_type in CLIP_INNER_TYPES:
            clip_info[f"{own}_{vid}"] = entry
        elif entry["error"]:
            unavailable.append({"object": f"Видео {k}", "link": None,
                                "reason": f"video.get: {entry['error']}"})
    print(f"videos checked: {len(videoids)} | confirmed clips: {len(clip_info)}")

    # applying confirmed clip status + clip views to posts (ER пересчёт по клипу)
    for p in posts:
        if p["main_type"] == "Клип":
            fixed_any = False
            for c in p["clips"] + p.get("clip_needs_video_get", []):
                cid = f"{c.get('owner_id')}_{c.get('id') or c.get('video_id')}"
                info = clip_info.get(cid)
                if info and info.get("clip_views"):
                    p["views_for_er"] = info["clip_views"]
                    p["views_source"] = "clip"
                    p["clip_views_at_collection"] = info["clip_views"]
                    p["er"] = compute_er(p["likes"], p["comments"], p["reposts"],
                                         info["clip_views"])
                    p["er_status"] = "ok" if p["er"] is not None else p["er_status"]
                    fixed_any = True
                    break
            if not fixed_any:
                p["data_status"] = "клип: просмотры клипа недоступны (video.get)"

    # пересчёт бенчмарков после фиксации клиповых ER
    by_owner = {}
    for p in posts:
        by_owner.setdefault(p["owner_id"], []).append(p)
    benchmarks = {}
    for oid, plist in by_owner.items():
        bm = benchmark_of([x["er"] for x in plist])
        benchmarks[str(oid)] = bm
        for x in plist:
            x["benchmark"] = bm
            if x["er"] is not None and bm is not None:
                x["is_best"] = x["er"] >= bm
                x["result"] = "Лучший" if x["is_best"] else "Обычный"
            else:
                x["is_best"] = False
                x["result"] = "ER не рассчитан"

    best_posts = [p for p in posts if p["is_best"]]

    # ---------- 2. изображения лучших постов ----------
    os.makedirs(path("media", "images"), exist_ok=True)
    os.makedirs(path("media", "collages"), exist_ok=True)
    img_fail = 0
    for p in best_posts:
        files = []
        for i, (url, dim) in enumerate(p["images"]):
            if not url:
                continue
            fp = path("media", "images", f"{p['post_id']}_{i}.jpg")
            okk, why = download_file(url, fp, sess)
            if okk:
                files.append(fp)
            else:
                img_fail += 1
                unavailable.append({"object": f"Изображение поста {p['url']}",
                                    "link": url[:200], "reason": f"скачивание: {why}"})
        p["image_files"] = files
        if files:
            cf = path("media", "collages", f"{p['post_id']}.jpg")
            build_collage(files, cf)
            p["collage_file"] = cf if os.path.exists(cf) else None
    imgs_expected = sum(1 for p in best_posts if p["images"])
    imgs_have = sum(1 for p in best_posts if p.get("image_files"))
    print(f"best posts expected images: {imgs_expected}, downloaded: {imgs_have}, failures: {img_fail}")

    # ---------- 3. клипы: скачивание + расшифровка ----------
    os.makedirs(path("media", "clips"), exist_ok=True)
    clips_out = []
    for p in posts:
        if p["main_type"] != "Клип":
            continue
        for c in p["clips"] + p.get("clip_needs_video_get", []):
            cid = f"{c.get('owner_id')}_{c.get('id') or c.get('video_id')}"
            info = clip_info.get(cid)
            if not info:
                continue
            kind, url = pick_clip_download_url(info["item"])
            rec = {"post_id": p["post_id"], "post_url": p["url"],
                   "group_name": p["group_name"],
                   "outer_type": "clip" if "clip" in str(c) else "video",
                   "inner_type": info["inner_type"],
                   "clip_views": info.get("clip_views"),
                   "file": None, "status": None, "transcript": None}
            if url:
                ext = {"mp4": ".mp4", "hls": ".m3u8", "dash": ".mpd"}[kind]
                dest = path("media", "clips", f"{cid}{ext}")
                okk, why = download_file(url, dest, sess)
                if okk and kind == "mp4":
                    rec["file"] = dest
                    st, tr = transcribe(dest, args.whisper_model)
                    rec["status"], rec["transcript"] = st, tr
                elif okk:
                    rec["file"] = dest
                    rec["status"] = f"stream_downloaded:{kind}:transcode_required"
                else:
                    rec["status"] = f"failed:download:{why}"
            else:
                # файлы недоступны → oembed fallback
                oe = vkapi.call("video.getOembed", {"url": f"https://vk.com/video{cid}"})
                if "response" in oe and (oe["response"].get("html") or oe["response"].get("url")):
                    rec["status"] = "failed:files_empty,oembed_player_only,no_direct_video_stream"
                else:
                    rec["status"] = "failed:files_empty_and_oembed_unavailable"
            if rec["status"] not in ("success", "no_speech"):
                unavailable.append({"object": f"VK Клип {cid} (пост {p['post_id']})",
                                    "link": p["url"], "reason": rec["status"]})
            clips_out.append(rec)
            time.sleep(0.1)

    save_json("clips_processing.json", clips_out, indent=2)
    save_json("posts_analyzed.json", posts)
    save_json("benchmarks.json", benchmarks, indent=2)
    save_json("unavailable.json", unavailable, indent=2)

    unprocessed = [c for c in clips_out if c["status"] not in ("success", "no_speech")]
    print(f"confirmed clips: {len(clips_out)} | processed(success/no_speech): "
          f"{len(clips_out)-len(unprocessed)} | unprocessed: {len(unprocessed)}")
    print("MEDIA STAGE DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
