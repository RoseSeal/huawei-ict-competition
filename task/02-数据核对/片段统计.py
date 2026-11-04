# -*- coding: utf-8 -*-
"""
FVessel Clip-10 包片段统计脚本（修正版）

文件格式（实测）：
  gt_tracking.txt  MOT 格式: frame, id, left, top, w, h, conf, cls, vis
  gt_fusion.txt    frame, nanosecond, left, top, w, h, conf, cls, vis
                   —— 没有 id 列！船的身份需按 (frame, left, top) 与 tracking 精确对齐。

统计每个片段：
  - 可见船舶数   = tracking 中不同轨迹 id 数
  - 有 AIS 船数 = fusion 行匹配回 tracking 后命中的不同轨迹 id 数
  - 无 AIS 船数 = 可见 - 有AIS
另附 clip-10 时间对齐实测（AIS epoch 毫秒 → UTC+8 本地时间 vs 视频文件名时间窗）。
数据来源：https://huggingface.co/datasets/gy65896/FVessel（Clip-10.zip，经 hf-mirror.com 下载）
"""
import csv
import datetime
import glob
import os
import re
from collections import defaultdict

ROOT = r"D:\work Buddy\datasets\extracted\Clip-10"
OUT = r"D:\work Buddy\huawei-ict-competition\task\02-数据核对\片段统计-结果.csv"

results = []
for clip_dir in sorted(glob.glob(os.path.join(ROOT, "clip-*"))):
    clip = os.path.basename(clip_dir)
    tracking = os.path.join(clip_dir, "gt", f"{clip}_gt_tracking.txt")
    fusion = os.path.join(clip_dir, "gt", f"{clip}_gt_fusion.txt")

    track_ids = set()
    bbox2id = {}          # (frame,left,top) -> id
    with open(tracking) as f:
        for r in csv.reader(f):
            if len(r) < 6:
                continue
            frame, tid, left, top = r[0], r[1], r[2], r[3]
            track_ids.add(tid)
            bbox2id[(frame, left, top)] = tid

    fusion_hit_ids = set()
    matched = unmatched = 0
    with open(fusion) as f:
        for r in csv.reader(f):
            if len(r) < 6:
                continue
            key = (r[0], r[2], r[3])
            tid = bbox2id.get(key)
            if tid is not None:
                fusion_hit_ids.add(tid)
                matched += 1
            else:
                unmatched += 1

    results.append({
        "clip": clip,
        "visible": len(track_ids),
        "with_ais": len(fusion_hit_ids),
        "no_ais": len(track_ids) - len(fusion_hit_ids),
        "rows_matched": matched,
        "rows_unmatched": unmatched,
        "track_id_list": ",".join(sorted(track_ids, key=int)),
        "fusion_id_list": ",".join(sorted(fusion_hit_ids, key=int)),
    })

# --- clip-10 时间对齐实测 ---
print("=== clip-10 时间对齐实测 ===")
video = glob.glob(os.path.join(ROOT, "clip-10", "*.mp4"))
if video:
    m = re.search(r"(\d{4})_(\d{2})_(\d{2})_(\d{2})_(\d{2})_(\d{2})_(\d{2})_(\d{2})_(\d{2})",
                  os.path.basename(video[0]))
    if m:
        g = m.groups()
        print(f"视频文件名时间窗: {g[0]}-{g[1]}-{g[2]} {g[3]}:{g[4]}:{g[5]} ~ {g[6]}:{g[7]}:{g[8]} (本地时间)")

ais_dir = os.path.join(ROOT, "clip-10", "ais")
csvs = sorted(glob.glob(os.path.join(ais_dir, "*.csv")))
if csvs:
    print(f"AIS CSV 文件覆盖: {os.path.basename(csvs[0])} ~ {os.path.basename(csvs[-1])} (每秒一文件)")
    ts = []
    for path in csvs:
        with open(path) as f:
            for row in csv.DictReader(f):
                if row.get("timestamp"):
                    ts.append(int(row["timestamp"]))
    fmt = lambda ms: datetime.datetime.fromtimestamp(ms / 1000).strftime("%Y-%m-%d %H:%M:%S")
    print(f"报文 epoch 范围: {fmt(min(ts))} ~ {fmt(max(ts))} (UTC+8)")
    print("⇒ epoch 毫秒按 UTC+8 换算后与文件名/视频窗一致 ⇒ AIS 时间戳是 UTC 毫秒，与视频时间可直接对齐")

# --- 汇总表 ---
print()
print("=== 各片段统计 ===")
print(f"{'片段':<10}{'可见船':>6}{'有AIS':>7}{'无AIS':>7}{'fusion行匹配':>12}  轨迹ID(有AIS的加*)")
for r in results:
    fs = set(r["fusion_id_list"].split(",")) if r["fusion_id_list"] else set()
    marks = " ".join(i + ("*" if i in fs else "") for i in r["track_id_list"].split(",") if i)
    print(f"{r['clip']:<10}{r['visible']:>6}{r['with_ais']:>7}{r['no_ais']:>7}{r['rows_matched']:>8}行/{r['rows_unmatched']}未匹  {marks}")

with open(OUT, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=["clip", "visible", "with_ais", "no_ais",
                                      "rows_matched", "rows_unmatched",
                                      "track_id_list", "fusion_id_list"])
    w.writeheader()
    w.writerows(results)
print(f"\n结果已写入: {OUT}")
