# FVessel 数据说明（核对稿）

> 任务：判断 FVessel 能否作为 AIS 之外的数据源，用于覆盖未开启 AIS 的船舶。
> 依据来源：[GitHub 仓库](https://github.com/gy65896/FVessel)（核对日期 2026-11-02）；**2026-11-03 下载 Clip-10 样本包与 V1.0 完整包后完成实测核对，原"未确认"项已全部更新（见 §3.2、§3.5、§5 及[全量普查记录](本地运行记录-数据集获取与全量普查.md)）。**

## 1. 数据集概况

FVessel（TITS 2023 论文配套基准数据集），拍摄于**武汉长江段**（2022 年 5 月），使用 HIKVISION DS-2DC4423IW-D 球机 + Saiyang AIS9000-08 Class-B AIS 接收机采集。含两大部分：

| 部分 | 内容 | 规模 |
|---|---|---|
| 01_Video+AIS | 视频 + 逐秒 AIS CSV + 相机参数 + MOT 格式标注 | V1.0 共 26 段；V2.0 另有 9 段（需申请） |
| 02_Image+xml | 船舶检测图像 + xml 标注（仅 vessel 一类） | V1.0 共 7625 张；V2.0 另有 3728 张 |

**证据**：GitHub README §Introduction、§Details；[下载目录](https://huggingface.co/datasets/gy65896/FVessel/tree/main)。

## 2. 每段视频数据的文件构成

```text
|-ais/                          逐秒一个 CSV（每秒保留每船最新一条）
|    |-2022_05_10_19_21_04.csv
|      字段: Number, MMSI, Lon, Lat, Speed, Course, Heading, Type, Timestamp
|-2022_05_10_19_21_05_19_31_10_b.mp4   文件名即起止时间；b=桥区, r=岸边
|-camera_para.txt               [经度, 纬度, 水平朝向, 垂直朝向, 相机高度, 水平FoV, 垂直FoV, fx, fy, u0, v0]
|-gt/
     |-Video-02_gt.mp4                  逐秒处理的标注视频
     |-Video-02_gt_detection.txt        <frame>, 框坐标, conf, cls, vis
     |-Video-02_gt_tracking.txt         <frame>, <轨迹id>, 框坐标, conf, cls, vis
     |-Video-02_gt_fusion.txt           <frame>, <纳秒时间>, 框坐标, conf, cls, vis
```

**证据**：README §01_Video+AIS 文件树与字段定义。
**⚠️ 实测勘误（2026-11-03）**：README 称 fusion 第 2 列为 mmsi——**实测不符**。真实格式为"帧号 + 纳秒时间戳，**无 id/mmsi 列**"，船只身份须按 `(frame, left, top)` 与 tracking 精确对齐（本批 10 片段匹配率 100%，方法见[片段统计脚本](片段统计.py)）。

## 3. 任务五问

### 3.1 包含哪些文件和内容 —— 已确认

见上文 §1、§2。另有 `01_demo_transform`（AIS 坐标投影到图像的示例代码）与 `02_demo_metric`（MOT 评测代码）。

### 3.2 时间字段能否与 AIS 对齐 —— ✅ 已实测确认（2026-11-03）

- 视频时长边界写在 mp4 文件名里（精确到秒）；AIS CSV 按秒命名；每条 AIS 记录带 `Timestamp`（**UTC Unix 毫秒**）；GT 标注以帧号为时间轴。
- **实测结论**（Clip-10 全部 10 片段）：AIS epoch 按 **UTC+8** 换算后与 CSV 文件名、视频文件名时间窗完全吻合，无未知时区偏移、无秒级漂移，可直接对齐。证据：[片段统计-10片段与V1.0全量.md](片段统计-10片段与V1.0全量.md) §三。

### 3.3 相机位置与视野 —— 已确认（结构），具体数值按段读取

每段视频附 `camera_para.txt`：相机经纬度、水平/垂直朝向、安装高度、水平/垂直视场角（FoV）、内参（fx, fy, u0, v0）。README 示例：位于 114.32583E, 30.60139N，高 20 m，水平 FoV 55°、垂直 30.94°。机位分两类：桥区（bridge）与岸边（riverside），天气覆盖晴天/多云/低光。

### 3.4 是否标注了无 AIS 的船舶 —— 已确认，这正是本数据集的价值

- `gt_tracking.txt` 给**所有可见船舶**编轨迹 id；`gt_fusion.txt` 只覆盖**有 AIS 的船**（无 id 列，按 bbox 对齐后计轨迹数）。两者之差即"可见但无 AIS"的船舶。
- README 的 V1.0 表格给出每段对比；**2026-11-03 已用 V1.0 完整包 26 段全量普查实测证实**：7 段存在无 AIS 船、合计 11 艘。⚠️ **实测与 README 表格存在出入（以实测为准）**：README 列为 Video-01/10/18/21/22/25（6 段），实测为 Video-01/02/08/10/18/21/22（7 段）——**Video-25 实测 8 艘全部有 AIS（README 有误）**，**Video-02/08 实测各有 1 艘无 AIS（README 未列出）**；Video-10 的 3 艘/1 有 AIS 与 README 一致。证据：[V1.0普查-结果.csv](V1.0普查-结果.csv)。
- 注意：MMSI 已为保护隐私替换为随机数，无法对应真实船舶身份。

### 3.5 使用许可 —— ✅ 已核查完毕（2026-11-04，三处来源交叉确认）

- **核查结论**：仓库 LICENSE 为 **MIT License**（Copyright (c) 2023 yuguo，覆盖代码）；**数据文件本身无任何显式许可声明**——已核查三处权威来源并全部确认：① GitHub LICENSE 文件原文；② HF 数据卡（README）全文无 License 章节；③ HF 平台元数据标签仅有 `region:us`，无任何 license 标签（API 实查）。
- **实际含义**：数据按"学术惯例引用使用"处理——引用论文（TITS 2023）+ 注明数据集出处即可；V2.0 另有门槛（2023.08.01 说明：需机构/学校邮箱申请，仅限研究用途）。
- 竞赛要求"入围总决赛须开源"，若最终材料引用 FVessel 派生数据，随材料注明上述出处与许可状态。

## 4. 对"覆盖未开启 AIS 船舶"的初步判断

| 维度 | 结论 |
|---|---|
| 能否提供无 AIS 船舶的观测 | **能**：GT 标注明确区分有/无 AIS 船舶，Video-01/10/18/21/22/25 均含无 AIS 目标 |
| 能否给出无 AIS 船的位置/航速 | **间接**：图像框 + camera_para 内外参可反算，但需自做投影（仓库提供 demo 代码），框本身不直接给出经纬度与航速 |
| 时效 | **无实时性**：2022 年 5 月固定快照，只适合离线评测，不能当实时数据源接入 map-system |
| 与 map-system 的匹配度 | 坐标系不同：map-system 吃 MQTT AIS 报文；FVessel 是"图像框 + 投影"路线，桥区/岸边固定视角也不等于船载视角——只宜作**评测数据集**，不宜作系统输入源 |

## 5. 证据清单

| 项 | 证据 |
|---|---|
| 数据构成/文件字段 | https://github.com/gy65896/FVessel §Details（2026-11-02 核对） |
| 有无 AIS 对比表 | 同上 §01_Video+AIS 的 V1.0 表格 |
| 相机参数格式 | 同上 §(c) camera_para.txt |
| MIT LICENSE | https://github.com/gy65896/FVessel/blob/main/LICENSE（已读原文） |
| V2.0 申请限制 | 同上 README §News 2023.08.01 条目 |
| HF 数据卡与实际文件 | ✅ 已核实（2026-11-03，经 hf-mirror.com 镜像）：数据卡即仓库 README；实际文件清单经 HF API 核实为 `.gitattributes` + `README.md` + `Clip-10.zip`(2.56GB) + `FVessel_V1.0.zip`(40.9GB) + `FVessel_V2.0.zip`(23.0GB)，与 README 描述一致 |
| 时间对齐实测 | ✅ 已实测（2026-11-03）：AIS `Timestamp` 为 UTC 毫秒，按 UTC+8 与 CSV 文件名/视频文件名时间窗完全吻合，见[片段统计-10片段与V1.0全量.md](片段统计-10片段与V1.0全量.md) §三 |
| 无 AIS 船实证 | ✅ 已实测（2026-11-03）：26 段全量普查，7 段存在无 AIS 船共 11 艘，见[V1.0普查-结果.csv](V1.0普查-结果.csv) |
