"""建议（ADVISORY）与其后场景变化的对照统计。仅依赖标准库。

用法：python3 -I advisory_stats.py <SSE日志> <后端日志> [v]
  SSE 日志：B2 附录 B 的 sse_capture.py 输出（接收时间 \t 事件类型 \t JSON）。
  后端日志：须含 SceneRiskStateTracker、AdvisoryService 的 INFO/WARN 行；
            含 AgentLoopOrchestrator 的 DEBUG 行时输出每次生成的工具调用序列。
  第三个参数任意值：同时输出每条建议的 evidence_items。

输出末尾的“场景 05 判定”按 B1-场景05 卡片的口径计算：
  覆盖   目标处于 WARNING 及以上期间，存在未过期、未被顶替且 affected_targets 含该目标的建议。
         相隔不超过 2 s 的未覆盖片段合并为一段（阈值处等级逐帧往返）。
  生成   每次触发的结果；迭代超限次数。
  数值   建议文本中的本船航向与触发时、发布时 SSE 帧中的本船 COG 比较，容差 1°。
         由正则提取，输出原句供人工确认。
  错误码 生成失败后 2 s 内的 ERROR 事件 error_code。

时间以首条 RISK_UPDATE 的接收时间为 +0 s。SSE 日志的接收时间按 UTC+8 解析。
时长与帧滞后只统计含目标的帧：目标清理后补发的空帧沿用旧时间戳，不计入。
帧间隔为相邻两帧接收时间之差；主机休眠时进程整体暂停，帧滞后不变而帧间隔变大。
"""
import json
import re
import sys
from datetime import datetime, timedelta, timezone

TZ8 = timezone(timedelta(hours=8))


def parse_ts(s):
    """解析 ISO 时间；小数秒位数不定时补齐到 6 位。"""
    s = s.replace('Z', '+00:00')
    if '.' in s:
        head, rest = s.split('.', 1)
        frac, tz = rest[:-6], rest[-6:]
        s = head + '.' + (frac + '000000')[:6] + tz
    return datetime.fromisoformat(s).timestamp()


def recv_ts(s):
    return datetime.fromisoformat(s).replace(tzinfo=TZ8).timestamp()


def load(path):
    """返回 (frames, advisories, errors)。frames 为 (帧时间, 接收时间, {目标: 指标})。"""
    frames, advs, errs = [], [], []
    for line in open(path, encoding='utf-8'):
        p = line.rstrip('\n').split('\t', 2)
        if len(p) < 3:
            continue
        recv = recv_ts(p[0])
        if p[1] == 'ADVISORY':
            advs.append((recv, json.loads(p[2])))
        elif p[1] == 'ERROR':
            errs.append((recv, json.loads(p[2])))
        elif p[1] == 'RISK_UPDATE':
            d = json.loads(p[2])
            tg = {}
            for t in d.get('targets') or []:
                ra = t.get('risk_assessment') or {}
                cpa = ra.get('cpa_metrics') or {}
                tg[t['id']] = dict(level=ra.get('risk_level') or 'SAFE',
                                   dcpa=cpa.get('dcpa_nm'), tcpa=cpa.get('tcpa_sec'))
            own = (d.get('own_ship') or {}).get('dynamics') or {}
            frames.append((parse_ts(d['timestamp']), recv, tg, own))
    return frames, advs, errs


def load_backend(path):
    """返回 (建议相关事件, {快照版本: (触发时间, 目标)}, 每次触发的生成记录)。"""
    events, trig, runs = [], {}, []
    for line in open(path, encoding='utf-8', errors='replace'):
        m = re.match(r'(\d{4}-\d\d-\d\dT[\d:.]+\+08:00)\s+(\w+).*?: (.*)', line)
        if not m:
            continue
        t, level, msg = datetime.fromisoformat(m.group(1)).timestamp(), m.group(2), m.group(3).strip()
        mm = re.search(r'Advisory triggered: dedup=\w+ targets=\[(.*?)\] snapshot=(\d+)', msg)
        if mm:
            trig[int(mm.group(2))] = (t, mm.group(1))
            runs.append(dict(t=t, targets=mm.group(1), tools=[], end=None, outcome='未结束'))
        mm = re.search(r'Agent tool iteration=\d+ tool=(\w+)', msg)
        if mm and runs and runs[-1]['end'] is None:
            runs[-1]['tools'].append(mm.group(1))
        if runs and runs[-1]['end'] is None:
            if 'Advisory published' in msg:
                runs[-1].update(end=t, outcome='已发布')
            elif 'exceeded max iterations' in msg:
                runs[-1].update(end=t, outcome='超出迭代上限')
            elif 'Advisory discarded' in msg or 'Advisory generation failed' in msg:
                runs[-1].update(end=t, outcome='丢弃/失败')
        if 'Advisory' in msg and level != 'DEBUG':
            events.append((t, msg))
    return events, trig, runs


def main():
    sse, backend = sys.argv[1], sys.argv[2]
    verbose = len(sys.argv) > 3
    fr, advs, errs = load(sse)
    events, trig, runs = load_backend(backend)
    t0 = fr[0][1]
    rel = lambda t: f"+{t - t0:.0f}s"

    def at(t, tid):
        best = None
        for _, r, tg, _ in fr:
            if r > t:
                break
            if tid in tg:
                best = tg[tid]
        return best

    def fmt(x):
        return '无' if x is None else f"{x['level']} dcpa={x['dcpa']:.3f} tcpa={x['tcpa']:.0f}"

    live = [(w, r) for w, r, tg, _ in fr if tg]
    max_lag = max(r - w for w, r in live)
    max_gap = max(b[1] - a[1] for a, b in zip(live, live[1:]))
    print(f"帧数={len(fr)}（含目标的帧 {len(live)}） 时长={live[-1][1] - t0:.0f}s "
          f"最大帧滞后={max_lag:.1f}s 最大帧间隔={max_gap:.1f}s "
          f"建议={len(advs)} 错误事件={len(errs)} 触发={len(trig)}")

    def own_cog(t):
        best = None
        for _, r, _, own in fr:
            if r > t:
                break
            best = own.get('cog')
        return best

    print("\n-- 目标等级时间线（接收时间）")
    for tid in sorted({i for _, _, tg, _ in fr for i in tg}):
        prev, out = None, []
        for _, r, tg, _ in fr:
            k = tg[tid]['level'] if tid in tg else 'ABSENT'
            if k != prev:
                x = tg.get(tid)
                out.append(f"{rel(r)} {k}" + (f"(dcpa={x['dcpa']:.2f},tcpa={x['tcpa']:.0f})"
                                               if x and x['dcpa'] is not None else ''))
                prev = k
        print(f" {tid}: " + " -> ".join(out))

    print("\n-- 后端建议事件")
    for t, msg in events:
        print(f" {rel(t)} {msg[:170]}")

    codes = {}
    for _, e in errs:
        codes[e.get('error_code')] = codes.get(e.get('error_code'), 0) + 1
    print("\n-- 错误事件按 error_code 计数:", codes)

    print("\n-- 每次触发的生成过程")
    for r in runs:
        dur = f"{r['end'] - r['t']:.1f}s" if r['end'] else 'n/a'
        print(f" {rel(r['t'])} targets=[{r['targets']}] {r['outcome']} 耗时={dur} 工具调用={len(r['tools'])}: "
              + ", ".join(r['tools']))

    print("\n-- 建议")
    for i, (recv, a) in enumerate(advs):
        nxt = advs[i + 1][0] if i + 1 < len(advs) else None
        vu = parse_ts(a['valid_until'])
        end = min(x for x in (vu, nxt, fr[-1][1]) if x is not None)
        why = '到期' if end == vu else ('被顶替' if end == nxt else '日志结束')
        tr = trig.get(a.get('snapshot_version'))
        gen = f"{recv - tr[0]:.1f}s" if tr else 'n/a'
        act = a.get('recommended_action') or {}
        print(f"\n#{i + 1} snapshot={a.get('snapshot_version')} 触发={rel(tr[0]) if tr else 'n/a'} 发布={rel(recv)} "
              f"生成耗时={gen} 等级={a.get('risk_level')} 显示至={rel(end)}（{why}；显示 {end - recv:.0f}s） "
              f"发布时本船COG={own_cog(recv)}")
        print(f"   动作: {act.get('type')} / {act.get('urgency')} : {act.get('description')}")
        print(f"   摘要: {a.get('summary')}")
        if verbose:
            for e in a.get('evidence_items') or []:
                print(f"   依据: {e}")
        for tid in a.get('affected_targets') or []:
            seq = [(r, tg[tid]) for _, r, tg, _ in fr if recv <= r <= end and tid in tg]
            lv_runs = []
            for r, x in seq:
                if not lv_runs or lv_runs[-1][1] != x['level']:
                    lv_runs.append((r, x['level']))
            print(f"   目标 {tid}: 触发时[{fmt(at(tr[0], tid)) if tr else 'n/a'}] 发布时[{fmt(at(recv, tid))}] "
                  f"结束时[{fmt(at(end, tid))}]")
            print("      显示期间: " + " -> ".join(f"{rel(r)} {l}" for r, l in lv_runs))

    # 探索性统计，不是正式的覆盖指标：只看是否存在未过期、未被顶替的建议，
    # 不检查该建议是否针对当前风险最高的目标。每帧的等级保持到下一帧的接收时间。
    shown = []
    for i, (recv, a) in enumerate(advs):
        nxt = advs[i + 1][0] if i + 1 < len(advs) else float('inf')
        shown.append((recv, min(parse_ts(a['valid_until']), nxt)))
    rank = {'SAFE': 0, 'CAUTION': 1, 'WARNING': 2, 'ALARM': 3}
    for label, floor in (('WARNING 及以上', 2), ('全部非 SAFE', 1)):
        total, pieces = 0.0, []
        for (_, r1, tg, _), (_, r2, _, _) in zip(fr, fr[1:]):
            if not tg or max(rank[x['level']] for x in tg.values()) < floor:
                continue
            total += r2 - r1
            cuts = [(r1, r2)]
            for s0, e0 in shown:
                cuts = [seg for a0, b0 in cuts
                        for seg in ((a0, min(b0, s0)), (max(a0, e0), b0)) if seg[1] > seg[0]]
            for a0, b0 in cuts:
                if pieces and abs(pieces[-1][1] - a0) < 1e-6:
                    pieces[-1] = (pieces[-1][0], b0)
                else:
                    pieces.append((a0, b0))
        none = sum(b0 - a0 for a0, b0 in pieces)
        print(f"\n-- {label}：共 {total:.1f}s，其中没有未过期建议 {none:.1f}s（{100 * none / total:.1f}%）")
        for a0, b0 in pieces:
            if b0 - a0 >= 5:
                print(f" {rel(a0)} ~ {rel(b0)}（{b0 - a0:.1f}s）")

    # ---------- 场景 05 判定 ----------
    print("\n== 场景 05 判定 ==")
    RESP, MERGE, TOL = 30.0, 2.0, 1.0
    valid = max_lag <= 5.0 and max_gap <= 5.0 and bool(trig)
    print(f"\n-- 运行有效条件：最大帧滞后 {max_lag:.1f}s，最大帧间隔 {max_gap:.1f}s，触发 {len(trig)} 次"
          f" -> {'有效' if valid else '无效，本次不计'}（滞后与间隔均不超过 5s，且有触发）")
    shown_t = []
    for i, (recv, a) in enumerate(advs):
        nxt = advs[i + 1][0] if i + 1 < len(advs) else float('inf')
        shown_t.append((recv, min(parse_ts(a['valid_until']), nxt), set(a.get('affected_targets') or [])))

    print("\n-- 预期 1 覆盖（按目标；WARNING 及以上）")
    sum_total = sum_none = 0.0
    ok1 = True
    for tid in sorted({i for _, _, tg, _ in fr for i in tg}):
        total, pieces, first = 0.0, [], None
        for (_, r1, tg, _), (_, r2, _, _) in zip(fr, fr[1:]):
            if tid not in tg or rank[tg[tid]['level']] < 2:
                continue
            if first is None:
                first = r1
            total += r2 - r1
            cuts = [(r1, r2)]
            for s0, e0, ids in shown_t:
                if tid in ids:
                    cuts = [seg for a0, b0 in cuts
                            for seg in ((a0, min(b0, s0)), (max(a0, e0), b0)) if seg[1] > seg[0]]
            for a0, b0 in cuts:
                if pieces and a0 - pieces[-1][1] <= MERGE:
                    pieces[-1] = (pieces[-1][0], b0)
                else:
                    pieces.append((a0, b0))
        if first is None:
            print(f" {tid}: 未进入 WARNING")
            continue
        none = sum(b0 - a0 for a0, b0 in pieces)
        cover = [s0 for s0, e0, ids in shown_t if tid in ids and e0 > first]
        resp = max(0.0, min(cover) - first) if cover else None
        longest = max((b0 - a0 for a0, b0 in pieces), default=0.0)
        late = [(a0, b0) for a0, b0 in pieces if b0 - a0 > RESP]
        sum_total += total
        sum_none += none
        ok1 = ok1 and resp is not None and resp <= RESP and not late
        print(f" {tid}: WARNING 及以上 {total:.1f}s，未覆盖 {none:.1f}s（{100 * none / total:.1f}%）；"
              f"进入 WARNING 于 {rel(first)}，首条覆盖建议 "
              + (f"{resp:.1f}s 后" if resp is not None else "无") + f"；最长未覆盖段 {longest:.1f}s")
        for a0, b0 in pieces:
            if b0 - a0 >= 5:
                print(f"    未覆盖 {rel(a0)} ~ {rel(b0)}（{b0 - a0:.1f}s）")
    if sum_total:
        print(f" 合计：{sum_total:.1f} 目标·秒，未覆盖 {sum_none:.1f}（{100 * sum_none / sum_total:.1f}%）")
    print(f" 判定：{'符合' if ok1 else '不符合'}（首条覆盖建议不晚于 {RESP:.0f}s，且无超过 {RESP:.0f}s 的未覆盖段）")

    print("\n-- 预期 2 生成")
    n_iter = sum(1 for r in runs if r['outcome'] == '超出迭代上限')
    n_pub = sum(1 for r in runs if r['outcome'] == '已发布')
    print(f" 触发 {len(runs)}，发布 {n_pub}，迭代超限 {n_iter}，其他 {len(runs) - n_pub - n_iter}")
    print(f" 判定：{'符合' if n_iter == 0 else '不符合'}（迭代超限次数为 0）")

    print("\n-- 预期 3 本船航向数值")
    pat = re.compile(r'(?:航向|COG|cog)\s*[(（]?\s*(?:从|为|是|[=:：])?\s*(\d+(?:\.\d+)?)\s*(?:度|°)?')
    n_val = n_bad = 0
    for i, (recv, a) in enumerate(advs):
        tr = trig.get(a.get('snapshot_version'))
        refs = [c for c in ((own_cog(tr[0]) if tr else None), own_cog(recv)) if c is not None]
        act = a.get('recommended_action') or {}
        texts = [('action', act.get('description') or '')]
        texts += [('summary', x) for x in re.split(r'[。；;]', a.get('summary') or '') if '本船' in x]
        texts += [('evidence', e) for e in a.get('evidence_items') or []
                  if '本船' in e or 'own_ship' in e]
        for src, text in texts:
            for m in pat.finditer(text):
                v = float(m.group(1))
                good = any(abs(v - c) <= TOL for c in refs)
                n_val += 1
                n_bad += 0 if good else 1
                print(f" #{i + 1} [{src}] {v:g}，本船 COG {'/'.join(f'{c:g}' for c in refs)} -> "
                      f"{'一致' if good else '不一致'}｜{text.strip()[:70]}")
    print(f" 提取 {n_val} 处，不一致 {n_bad} 处")
    print(f" 判定：{'符合' if n_bad == 0 else '不符合'}（提取结果须人工确认）")

    print("\n-- 预期 4 失败时的错误码")
    bad4 = 0
    for r in runs:
        if r['outcome'] in ('已发布', '未结束'):
            continue
        codes4 = [e.get('error_code') for t, e in errs if r['end'] - 1 <= t <= r['end'] + 2]
        match = r['outcome'] != '超出迭代上限' or 'ADVISORY_SCHEMA_FAILED' not in codes4
        bad4 += 0 if match and codes4 else 1
        print(f" {rel(r['t'])} {r['outcome']} -> ERROR {codes4 or '无'}")
    print(f" 判定：{'符合' if bad4 == 0 else '不符合'}（每次失败有 ERROR 事件，且迭代超限不报为 ADVISORY_SCHEMA_FAILED）")

if __name__ == '__main__':
    main()
