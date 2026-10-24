#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""账号诊断自动算分器（执行层）

输入：抓取落成的 profile.json
输出：score.json（逐项得分 + 模块得分率 + 主要矛盾 + 等级）

评分口径来源：references/{xhs,douyin}-scoring.md
口径若有变更，只改 references/ 下的 md，本脚本的分档值需同步（文件顶部有 ITEM_DEFS）。

用法：
    python score_account.py profile.json [--out score.json]
"""
import argparse
import json
import re
import sys
from pathlib import Path

# ---------- 分项定义（分值必须与 scoring.md 一致） ----------
ITEM_DEFS = {
    "xhs": {
        "M1": {1: ("昵称含搜索词", 4), 2: ("头像可信", 3), 3: ("简介四要素", 5), 4: ("主页九宫格统一", 4)},
        "M2": {5: ("标题前 8 字", 6), 6: ("封面可读性", 6), 7: ("开头钩子", 5), 8: ("价值类型", 4),
               9: ("关键词三层", 3), 10: ("结尾动作", 3), 11: ("可转发实体物", 3)},
        "M3": {12: ("选题分布", 4), 13: ("更新节奏", 4), 14: ("发布时间分布", 3), 15: ("栏目化与同质化", 3)},
        "M4": {16: ("曝光量级", 5), 17: ("点击率", 7), 18: ("互动率", 6), 19: ("涨粉率", 4)},
        "M5": {20: ("主页承接", 5), 21: ("评论承接", 4), 22: ("咨询链路", 3)},
        "M6": {23: ("一句话差异点", 4), 24: ("对标同质度", 2)},
    },
    "douyin": {
        "M1": {1: ("昵称含搜索词", 4), 2: ("头像可信", 3), 3: ("简介四要素", 4), 4: ("主页作品集统一", 3)},
        "M2": {5: ("前 3 秒钩子", 9), 6: ("首帧与标题", 5), 7: ("价值类型", 4), 8: ("关键词与话题", 3),
               9: ("结尾动作", 4), 10: ("可转发实体物", 2), 11: ("完播结构", 5)},
        "M3": {12: ("选题分布", 4), 13: ("更新节奏", 4), 14: ("发布时间分布", 3), 15: ("系列化与同质化", 3)},
        "M4": {16: ("播放量", 5), 17: ("完播率", 9), 18: ("互动率", 8), 19: ("涨粉率", 6)},
        "M5": {20: ("主页承接", 4), 21: ("评论承接", 2), 22: ("咨询链路", 2)},
        "M6": {23: ("一句话差异点", 2), 24: ("对标同质度", 2)},
    },
}

# 词表服务于"陪拍/约拍/人像摄影"这一品类。换赛道时整表替换即可，逻辑不用改。
REGION_WORDS = ["北京", "上海", "广州", "深圳", "杭州", "成都", "重庆", "天津", "南京", "武汉",
                "西安", "苏州", "长沙", "青岛", "厦门", "昆明", "三亚", "郑州", "济南", "沈阳",
                "朝阳", "海淀", "东城", "西城", "丰台", "通州",
                "三里屯", "国贸", "什刹海", "天坛", "地坛", "故宫", "颐和园",
                "紫竹院", "鼓楼", "南锣", "前门", "大栅栏"]
CATEGORY_WORDS = ["陪拍", "约拍", "摄影", "写真", "跟拍", "拍照", "影像", "旅拍", "人像", "机位", "摄像"]
ACTION_WORDS = ["拍", "机位", "攻略", "路线", "约", "出片", "打卡", "怎么", "如何", "推荐", "拍到", "拍出"]
SERVICE_WORDS = ["陪拍", "约拍", "跟拍", "写真", "拍照", "摄影", "摄像", "拍摄"]
NEXTSTEP_WORDS = ["置顶", "收藏", "关注", "主页", "看第一", "第1", "第一条"]
DIFF_WORDS = ["当天", "出图", "精修", "机位熟", "不走冤枉路", "独家", "双机", "1小时", "2小时", "含片"]
MEMORY_COST = ["专业", "用心", "审美在线", "好看"]  # 这些不是差异点

GRADE_TABLE = [(90, "S"), (80, "A"), (70, "B"), (60, "C"), (0, "D")]


def _has_any(text, words):
    return any(w in text for w in words)


def _first8(title):
    return re.sub(r"\s+", "", title or "")[:8]


def _median(nums):
    nums = [n for n in nums if isinstance(n, (int, float))]
    if not nums:
        return None
    nums = sorted(nums)
    n = len(nums)
    return nums[n // 2] if n % 2 else (nums[n // 2 - 1] + nums[n // 2]) / 2


def score_nickname(nick):
    """M1-1：地域+品类=满；只有品类或只有地域=half；都没有=0"""
    nick = nick or ""
    has_region = _has_any(nick, REGION_WORDS)
    has_cat = _has_any(nick, CATEGORY_WORDS)
    if has_region and has_cat:
        return 4.0, "昵称同时含地域词与品类词"
    if has_cat or has_region:
        return 2.0, "昵称只含%s，缺另一半" % ("品类词" if has_cat else "地域词")
    return 0.0, "昵称无地域词也无品类词，搜索匹配不到"


def score_bio(lines, full):
    """M1-3：四要素各 1/4；抖音 4 分按 1 分一项"""
    text = " ".join(lines or [])
    per = full / 4.0
    got, missing = 0.0, []
    # 首句定位：首行须同时含地域与品类（如"北京陪拍｜…"），或出现客户指向语
    first = (lines[0] if lines else "")
    client_phrases = ["我是", "带你", "帮您", "可约", "可拍", "预约"]
    if (_has_any(first, REGION_WORDS) and _has_any(first, CATEGORY_WORDS)) or any(k in first for k in client_phrases):
        got += per
    else:
        missing.append("首句定位句")
    if _has_any(text, REGION_WORDS):
        got += per
    else:
        missing.append("地域")
    if _has_any(text, SERVICE_WORDS):
        got += per
    else:
        missing.append("服务项")
    # 差异点：有可感知差异词且不是"专业/用心"这类空话；带价格数字也算（可感知）
    has_price = bool(re.search(r"\d+\s*(元|块|起)", text))
    has_diff = _has_any(text, DIFF_WORDS) or has_price
    if has_diff:
        got += per
    else:
        missing.append("差异点")
    reason = "缺" + "、".join(missing) if missing else "四要素齐全"
    return round(got, 2), reason


def score_title(note_titles):
    """M2-5（小红书）：逐条看前 8 字是否含地域+动作，按达标比例分档"""
    if not note_titles:
        return None, None, "无笔记标题"
    hit = sum(1 for t in note_titles if _has_any(_first8(t), REGION_WORDS) and _has_any(_first8(t), ACTION_WORDS))
    n = len(note_titles)
    ratio = hit / n
    if ratio >= 0.7:
        s = 6.0
    elif ratio >= 0.4:
        s = 4.0
    elif ratio >= 0.15:
        s = 2.5
    else:
        s = 1.0
    return s, None, "%d/%d 条前 8 字同时含地域与动作（达标率 %.0f%%）" % (hit, n, ratio * 100)


def score_keywords(note_titles):
    """M2-9（小红书）：可测前两层（核心词 1 + 地点词 1），意图词需正文→缺测
    核心词按达标比例给分：≥50% 条达标=1，≥15%=0.5，否则 0"""
    if not note_titles:
        return None, 0, "无标题"
    n = len(note_titles)
    core_ratio = sum(1 for t in note_titles if _has_any(_first8(t), CATEGORY_WORDS)) / n
    core = 1.0 if core_ratio >= 0.5 else (0.5 if core_ratio >= 0.15 else 0.0)
    region = 1 if any(_has_any(t, REGION_WORDS) for t in note_titles) else 0
    return core + region, 2, "核心词 %.1f/1（达标率 %.0f%%）+ 地点词 %d/1；意图词需正文，缺测" % (
        core, core_ratio * 100, region)


def score_selection(note_titles):
    """M3-12：按标题粗分支柱，看最大支柱占比"""
    if not note_titles:
        return None, None, "无标题"
    n = len(note_titles)
    tips = sum(1 for t in note_titles if any(k in t for k in ("攻略", "技巧", "教程", "怎么", "如何", "教学")))
    hot = sum(1 for t in note_titles if any(k in t for k in ("明星", "同款", "热搜", "生日", "夜在", "打卡", "探店")))
    work = n - tips - hot
    biggest = max(tips, hot, work)
    share = biggest / n
    if share > 0.9:
        s = 0.0
    elif share > 0.6:
        s = 2.0
    else:
        s = 4.0
    return s, None, "客片类 %d / 攻略类 %d / 热点类 %d（共 %d 条，最大支柱 %.0f%%）" % (work, tips, hot, n, share * 100)


def score_backend(backend, key, full):
    """M4：有值且≥自身基线=满；≥80%基线=60%；否则 0–30%"""
    if not backend:
        return None, 0, "无后台数据"
    val = backend.get(key)
    base = (backend.get("baseline") or {}).get(key)
    if val is None or base is None:
        return None, 0, "缺 %s 或基线" % key
    if base <= 0:
        return None, 0, "基线无效"
    r = val / base
    s = full if r >= 1.0 else (full * 0.6 if r >= 0.8 else full * 0.3)
    return round(s, 2), full, "%s 实测 %s / 基线 %s（%.0f%%）" % (key, val, base, r * 100)


def manual_or_missing(manual, item_id, full, hint):
    v = (manual or {}).get(str(item_id))
    if v is None:
        return None, 0, "未测：" + hint
    return float(v), full, "人工判分"


def build_items(platform, profile):
    defs = ITEM_DEFS[platform]
    notes = profile.get("notes") or []
    titles = [n.get("title") for n in notes if n.get("title")]
    manual = profile.get("manual") or {}
    backend = profile.get("backend") or {}
    prof = profile.get("profile") or {}
    lines = prof.get("bio_lines") or []

    items = []

    cur = {"mod": None}

    def add(mid, name, full, res, measured_full=None):
        score, mfull, reason = res
        items.append({
            "id": mid, "module": cur["mod"], "name": name, "full": full,
            "score": score,
            "measured_full": (mfull if measured_full is None else measured_full) if score is not None else 0,
            "status": "measured" if score is not None else "missing",
            "reason": reason,
        })

    for mod, mdef in defs.items():
        cur["mod"] = mod
        for mid, (name, full) in mdef.items():
            key = "%d" % mid
            if mid == 1:
                s, r = score_nickname(prof.get("nickname"))
                add(key, name, full, (s, full, r))
            elif mid == 3:
                s, r = score_bio(lines, full)
                add(key, name, full, (s, full, r))
            elif mid == 5 and platform == "xhs":
                s, _, r = score_title(titles)
                add(key, name, full, (s, full, r))
            elif mid == 9 and platform == "xhs":
                s, mf, r = score_keywords(titles)
                add(key, name, full, (s, mf, r))
            elif mid == 12:
                s, _, r = score_selection(titles)
                add(key, name, full, (s, full, r))
            elif mid == 16:
                add(key, name, full, score_backend(backend, "impressions", full))
            elif mid == 17:
                bk = "click_rate" if platform == "xhs" else "completion_rate"
                add(key, name, full, score_backend(backend, bk, full))
            elif mid == 18:
                add(key, name, full, score_backend(backend, "interaction_rate", full))
            elif mid == 19:
                add(key, name, full, score_backend(backend, "follow_rate", full))
            elif mid == 20:
                # 主页承接：可部分自动——简介里有站内下一步词 + 有价格/流程
                has_next = _has_any(" ".join(lines), NEXTSTEP_WORDS)
                has_price = bool(re.search(r"\d+\s*(元|块|起)", " ".join(lines)))
                if has_next and has_price:
                    add(key, name, full, (full, full, "有站内下一步且有价格/流程"))
                elif has_next or has_price:
                    add(key, name, full, (round(full * 0.5, 2), full, "只有站内下一步或只有价格，缺一半"))
                else:
                    add(key, name, full, (round(full * 0.3, 2), full, "无站内下一步，也无价格与流程"))
            else:
                hint = "需看首图/正文/后台记录"
                add(key, name, full, manual_or_missing(manual, mid, full, hint))
    return items


def summarize(items, platform):
    fulls = {m: sum(f for _, f in ITEM_DEFS[platform][m].values()) for m in ITEM_DEFS[platform]}
    modules = {}
    for m in ITEM_DEFS[platform]:
        its = [i for i in items if i["module"] == m]
        measured = [i for i in its if i["status"] == "measured"]
        score = round(sum(i["score"] for i in measured), 2)
        mfull = sum(i["measured_full"] for i in measured)
        modules[m] = {
            "score": score, "full": fulls[m], "measurable_full": mfull,
            "missing_full": fulls[m] - mfull, "rate": round(score / mfull, 4) if mfull else None,
            "measured_items": len(measured), "total_items": len(its),
        }

    total_score = round(sum(v["score"] for v in modules.values()), 2)
    meas_total = sum(v["measurable_full"] for v in modules.values())
    total_full = sum(fulls.values()) or 100
    missing = total_full - meas_total
    converted = round(total_score * 100 / meas_total, 1) if meas_total else None

    # 主要矛盾：实测覆盖不足模块满分 70% 的模块不参与比较（覆盖不足时分不清是真低还是缺测）
    COVERAGE_MIN = 0.7
    NO_ISSUE_MIN = 0.7  # 合格模块最低得分率也≥70% 时，不点名主要矛盾
    excluded, cands = [], []
    for m, v in modules.items():
        if v["measurable_full"] == 0:
            excluded.append({"module": m, "reason": "全模块缺测，不参与比较"})
        elif v["measurable_full"] < v["full"] * COVERAGE_MIN:
            excluded.append({"module": m, "reason": "实测仅覆盖 %.0f%%（%d/%d 分），得分率不可靠" % (
                v["measurable_full"] * 100.0 / v["full"], v["measurable_full"], v["full"])})
        else:
            cands.append((v["rate"], m))

    main = None
    fallback = None
    if not cands:
        # 没有模块达到覆盖率门槛：取覆盖率最高的那个，并标明仅供参考
        best_m = max(modules, key=lambda k: modules[k]["measurable_full"])
        fallback = "无模块实测覆盖达 70%%，主要矛盾仅取覆盖最高的 %s（参考，不作结论）" % best_m
        main = {"module": best_m, "rate": modules[best_m]["rate"], "candidates": [], "low_confidence": True}
    else:
        lowest = min(cands)[0]
        tie = [m for r, m in cands if abs(r - lowest) < 1e-9]
        order = ["M5", "M2", "M3", "M1", "M4", "M6"]  # 影响面：转化>内容>结构>账号>数据>差异化
        if lowest >= NO_ISSUE_MIN:
            # 合格模块里最低的也≥70%：不点名主要矛盾，否则等于把"最高的短板"当病灶
            main = None
            fallback = "可测模块最低得分率 %.0f%%（≥%.0f%%），未见显著主要矛盾%s" % (
                lowest * 100, NO_ISSUE_MIN * 100,
                "；但缺测 %d 分，不能断定没问题" % missing if missing else "")
        else:
            main = {"module": sorted(tie, key=order.index)[0], "rate": lowest,
                    "candidates": [{"module": m, "rate": r} for r, m in sorted(cands)]}
    main_issue = {"main": main, "excluded": excluded, "fallback": fallback}

    grade = "暂不判级（缺测 %d 分）" % missing if missing >= 30 else next(
        g for th, g in GRADE_TABLE if converted >= th)

    return {"modules": modules,
            "total": {"score": total_score, "measurable_full": meas_total,
                      "missing": missing, "converted": converted},
            "main_issue": main_issue, "grade": grade}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("profile_json")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    p = Path(a.profile_json)
    data = json.loads(p.read_text(encoding="utf-8-sig"))  # utf-8-sig：兼容 PowerShell 写出的 BOM
    platform = data.get("platform", "xhs")
    if platform not in ITEM_DEFS:
        sys.exit("platform 只支持 xhs / douyin")

    items = build_items(platform, data)
    s = summarize(items, platform)
    out = {
        "platform": platform,
        "account": (data.get("profile") or {}).get("nickname"),
        "url": data.get("url"),
        "captured_at": data.get("captured_at"),
        "items": items,
        **s,
    }
    text = json.dumps(out, ensure_ascii=False, indent=2)
    if a.out:
        Path(a.out).write_text(text, encoding="utf-8")
        print("已写入 %s" % a.out)
        print("总分 %.1f / %d（缺测 %d 分）→ 折合 %.1f，等级：%s"
              % (s["total"]["score"], s["total"]["measurable_full"],
                 s["total"]["missing"], s["total"]["converted"] or 0, s["grade"]))
        mi = s["main_issue"]["main"]
        if mi and mi.get("rate") is not None:
            print("主要矛盾：%s（得分率 %.0f%%）%s"
                  % (mi["module"], mi["rate"] * 100, "（低可信：覆盖不足）" if mi.get("low_confidence") else ""))
        else:
            print("主要矛盾：无（%s）" % (s["main_issue"].get("fallback") or "无法判定"))
        for ex in s["main_issue"]["excluded"]:
            print("  已排除 %s：%s" % (ex["module"], ex["reason"]))
    else:
        print(text)


if __name__ == "__main__":
    main()
