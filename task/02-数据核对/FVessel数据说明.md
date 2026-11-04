# FVessel 数据说明（核对稿）

> 任务：判断 FVessel 能否作为 AIS 之外的数据源，用于覆盖未开启 AIS 的船舶。
> 依据来源：[GitHub 仓库](https://github.com/gy65896/FVessel)（核对日期 2026-11-02）；标注"未确认"的项待本地下载验证后更新。

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
     |-Video-02_gt_detection.txt        <second>, 0, 框坐标, conf, x, y, z
     |-Video-02_gt_tracking.txt         <second>, <轨迹id>, 框坐标, conf, x, y, z
     |-Video-02_gt_fusion.txt           <second>, <mmsi>, 框坐标, conf, x, y, z   ← 有AIS的船才有mmsi
```

**证据**：README §01_Video+AIS 文件树与字段定义。

## 3. 任务五问

### 3.1 包含哪些文件和内容 —— 已确认

见上文 §1、§2。另有 `01_demo_transform`（AIS 坐标投影到图像的示例代码）与 `02_demo_metric`（MOT 评测代码）。

### 3.2 时间字段能否与 AIS 对齐 —— 可以对齐，精度待验证

- 视频时长边界写在 mp4 文件名里（精确到秒）；AIS CSV 按秒命名；每条 AIS 记录带 `Timestamp`（Unix 毫秒，如 `1652181559844`）；GT 标注以视频第 `<second>` 秒为时间轴。
- 理论上：视频第 N 秒 ↔ 文件名起始时间 + N 秒 ↔ AIS CSV 同名秒文件。
- **未确认**：文件名时间是北京时间还是 UTC、与 AIS `Timestamp` 的时区是否一致、有无秒级偏移——需下载一段数据实际比对后更新。

### 3.3 相机位置与视野 —— 已确认（结构），具体数值按段读取

每段视频附 `camera_para.txt`：相机经纬度、水平/垂直朝向、安装高度、水平/垂直视场角（FoV）、内参（fx, fy, u0, v0）。README 示例：位于 114.32583E, 30.60139N，高 20 m，水平 FoV 55°、垂直 30.94°。机位分两类：桥区（bridge）与岸边（riverside），天气覆盖晴天/多云/低光。

### 3.4 是否标注了无 AIS 的船舶 —— 已确认，这正是本数据集的价值

- `gt_tracking.txt` 给**所有可见船舶**编轨迹 id；`gt_fusion.txt` 只给**有 AIS 的船**标 MMSI。两者之差即"可见但无 AIS"的船舶。
- README 的 V1.0 表格直接给出每段的对比，如：Video-01 共 5 艘 / 有 AIS 4 艘；**Video-10 共 3 艘 / 有 AIS 仅 1 艘**；Video-18 共 10 艘 / 有 AIS 6 艘。
- 注意：MMSI 已为保护隐私替换为随机数，无法对应真实船舶身份。

### 3.5 使用许可 —— 部分未确认

- 仓库 LICENSE 文件为 **MIT License**（Copyright (c) 2023 yuguo，已核对原文）。⚠️ MIT 是软件许可证，对**数据文件本身**的授权范围未在文中明示——**未确认**。
- **V2.0 有额外限制**：2023.08.01 更新说明"需使用机构/学校邮箱申请，仅限研究用途"。
- HuggingFace 数据卡（可能含数据集专用许可）本次核对时页面无法访问——**未确认**，待换网络或镜像重试。
- 竞赛要求"入围总决赛须开源"，若最终材料引用 FVessel 派生数据，需同时满足上述条款并注明出处（引用格式见 README §Citation）。

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
| HF 数据卡与实际文件 | 未确认（页面访问失败），待核 |
| 时间对齐实测 | 未确认，待下载片段验证 |
