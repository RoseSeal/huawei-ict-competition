# -*- coding: utf-8 -*-
"""
FVessel V1.0 完整包自动分析（下载完成后运行）
- 从 40GB zip 中只抽取 GT 标注 + AIS CSV + 相机参数（跳过大体积视频）
- 对全部视频计算：可见船舶数（gt_tracking 轨迹数）vs 有 AIS 船数（fusion bbox 对齐）
- 定位"可见船 > 有 AIS 船"的视频（即存在无 AIS 船的 AIS 盲区案例）
- 输出 V1.0普查-结果.csv 并打印摘要
"""
import csv
import datetime
import os
import re
import sys
import zipfile
from collections import defaultdict

ZIP = r"D:\work Buddy\datasets\FVessel_V1.0.zip"
ARIA2 = ZIP + ".aria2"
OUTDIR = r"D:\work Buddy\datasets\extracted\V1.0"
OUTCSV = r"D:\work Buddy\huawei-ict-competition\task\02-数据核对\V1.0普查-结果.csv"

# 0) 下载未完成检查
if os.path.exists(ARIA2):
    print("下载未完成：.aria2 控制文件仍存在")
    sys.exit(2)

z = zipfile.ZipFile(ZIP)
names = z.namelist()
print(f"zip 打开成功，共 {len(names)} 个条目")

tracking_files = sorted(n for n in names if n.endswith("_gt_tracking.txt"))
fusion_files = sorted(n for n in names if n.endswith("_gt_fusion.txt"))
print(f"找到 {len(tracking_files)} 个 tracking, {len(fusion_files)} 个 fusion")

def vid_of(path):
    # 视频目录名，如 .../Video-10/gt/Video-10_gt_tracking.txt → Video-10
    m = re.search(r"(Video-\d+|video-\d+|clip-\d+)", path)
    return m.group(1) if m else os.path.dirname(path)

# 1) 抽取小文件（GT + 相机参数 + AIS CSV），跳过 mp4/图片
targets = []
for n in names:
    if n.endswith("/"):
        continue
    low = n.lower()
    if low.endswith((".mp4", ".jpg", ".png", ".xml")):
        continue
    if "_gt_" in low or "camera_para" in low or "/ais/" in low or "\\ais\\" in low:
        targets.append(n)
print(f"抽取 {len(targets)} 个小文件到 {OUTDIR} ...")
z.extractall(OUTDIR, members=targets)
print("抽取完成")

# 2) 逐视频统计
results = []
for tf in tracking_files:
    vid = vid_of(tf)
    tpath = os.path.join(OUTDIR, tf.replace("/", os.sep))
    fpath = tpath.replace("_gt_tracking.txt", "_gt_fusion.txt")
    if not os.path.exists(fpath):
        continue

    track_ids = set()
    bbox2id = {}
    with open(tpath) as f:
        for r in csv.reader(f):
            if len(r) >= 6 and r[1].isdigit():
                track_ids.add(r[1])
                bbox2id[(r[0], r[2], r[3])] = r[1]

    hit = set()
    with open(fpath) as f:
        for r in csv.reader(f):
            if len(r) >= 6:
                tid = bbox2id.get((r[0], r[2], r[3]))
                if tid:
                    hit.add(tid)

    # AIS 射频范围内 MMSI 数（视频时间窗内）
    ais_dir = os.path.dirname(tpath).replace("gt", "ais")
    mmsi_win, nmsg = set(), 0
    vm = re.search(r"(\d{4})_(\d{2})_(\d{2})_(\d{2})_(\d{2})_(\d{2})_(\d{2})_(\d{2})_(\d{2})", tf)
    # 视频文件名在上级目录，尝试从 zip 名单找
    vmp4 = next((n for n in names if vid_of(n) == vid and n.lower().endswith(".mp4")), None)
    win = None
    if vmp4:
        g = re.search(r"(\d{4})_(\d{2})_(\d{2})_(\d{2})_(\d{2})_(\d{2})_(\d{2})_(\d{2})_(\d{2})", vmp4)
        if g:
            p = g.groups()
            t0 = datetime.datetime(int(p[0]), int(p[1]), int(p[2]), int(p[3]), int(p[4]), int(p[5])).timestamp()
            t1 = datetime.datetime(int(p[0]), int(p[1]), int(p[2]), int(p[6]), int(p[7]), int(p[8])).timestamp()
            win = (t0 * 1000, t1 * 1000)
    if os.path.isdir(ais_dir) and win:
        for fn in os.listdir(ais_dir):
            if not fn.endswith(".csv"):
                continue
            with open(os.path.join(ais_dir, fn)) as f:
                for row in csv.DictReader(f):
                    ts = row.get("timestamp")
                    if ts and win[0] <= int(ts) <= win[1]:
                        mmsi_win.add(row.get("mmsi"))
                        nmsg += 1

    results.append({
        "video": vid,
        "visible": len(track_ids),
        "with_ais": len(hit),
        "no_ais": len(track_ids) - len(hit),
        "ais_mmsi_in_window": len(mmsi_win),
        "ais_msgs": nmsg,
        "track_ids": ",".join(sorted(track_ids, key=int)),
        "ais_ids": ",".join(sorted(hit, key=int)),
    })

results.sort(key=lambda r: (r["no_ais"], r["video"]), reverse=True)

with open(OUTCSV, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=list(results[0].keys()))
    w.writeheader()
    w.writerows(results)

print()
print(f"{'视频':<12}{'可见':>5}{'有AIS':>6}{'无AIS':>6}{'窗内MMSI':>9}")
for r in results:
    flag = "  ← 无AIS船案例" if r["no_ais"] > 0 else ""
    print(f"{r['video']:<12}{r['visible']:>5}{r['with_ais']:>6}{r['no_ais']:>6}{r['ais_mmsi_in_window']:>9}{flag}")
print(f"\n共 {len(results)} 段；存在无 AIS 船的视频：{sum(1 for r in results if r['no_ais']>0)} 段")
print(f"结果已写入 {OUTCSV}")
