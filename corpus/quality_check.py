#!/usr/bin/env python3
"""
自动检查生成的SKILL.md是否通过质量标准。
对照通过标准表格逐项检查，输出通过/不通过和具体原因。

用法:
    python3 quality_check.py <SKILL.md路径>
    python3 quality_check.py <SKILL.md路径> --json
    python3 quality_check.py <SKILL.md路径> --strict    # 12 项全跑 + 违规 exit 1
    python3 quality_check.py <SKILL.md路径> --score     # 输出 0-100 综合分数

示例:
    python3 quality_check.py SKILL.md
"""

import sys
import re
import io
import json
from pathlib import Path

# Fix Windows console encoding for Unicode output
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


def _extract_section(content: str, header_pattern: str) -> str:
    """Extract content between a header and the next header of same or higher level."""
    match = re.search(header_pattern, content, re.MULTILINE)
    if not match:
        return ""
    start = match.end()
    # Find next ## or # header
    remaining = content[start:]
    next_header = re.search(r"^##\s+", remaining, re.MULTILINE)
    if next_header:
        return remaining[: next_header.start()]
    return remaining


def check_mental_models(content: str) -> tuple[bool, str]:
    """检查心智模型数量（3-9个），并验证每个模型有总结和局限标注"""
    # Find all model headers: ### 模型 N: ...
    model_headers = list(re.finditer(r"^###\s+模型\s*(\d+)", content, re.MULTILINE))
    if not model_headers:
        return False, "未检测到心智模型section"

    count = len(model_headers)
    passed_count = 3 <= count <= 9

    # Check each model section for summary and limitation
    models_with_summary = 0
    models_with_limitation = 0

    for i, header_match in enumerate(model_headers):
        # Extract content from this header to the next ### header (or next ## header)
        start = header_match.end()
        if i + 1 < len(model_headers):
            end = model_headers[i + 1].start()
        else:
            # Last model: find next ## header
            remaining = content[start:]
            next_h2 = re.search(r"^##\s+", remaining, re.MULTILINE)
            end = start + (next_h2.start() if next_h2 else len(remaining))

        section_content = content[start:end]

        if re.search(r"一句话|核心|本质|关键", section_content, re.IGNORECASE):
            models_with_summary += 1
        if re.search(r"局限|失效|不适用|盲区|边界", section_content, re.IGNORECASE):
            models_with_limitation += 1

    has_summaries = models_with_summary >= max(count // 2, 1)
    has_limitations = models_with_limitation >= max(count // 2, 1)
    overall = passed_count and has_summaries and has_limitations

    details = []
    details.append(f"{count}个模型{'✅' if passed_count else '❌ (应为3-7个)'}")
    details.append(f"{models_with_summary}个有总结")
    details.append(f"{models_with_limitation}个有局限标注")
    return overall, " ".join(details)


def check_limitations(content: str) -> tuple[bool, str]:
    """检查每个模型是否有局限性"""
    has_limitation = bool(re.search(r"局限|失效|不适用|盲区|limitation|blind spot", content, re.IGNORECASE))
    return has_limitation, "有局限性标注 ✅" if has_limitation else "❌ 未找到局限性描述"


def check_expression_dna(content: str) -> tuple[bool, str]:
    """检查表达DNA辨识度"""
    dna_section = bool(re.search(r"表达[ ]*DNA|Expression[ ]*DNA|表达风格", content, re.IGNORECASE))
    if not dna_section:
        return False, "❌ 未找到表达DNA section"

    style_markers = len(re.findall(r"句式|词汇|语气|幽默|节奏|确定性|引用|口头禅", content))
    passed = style_markers >= 3
    return passed, f"表达DNA特征: {style_markers}项 {'✅' if passed else '❌ (应≥3项)'}"


def check_honest_boundary(content: str) -> tuple[bool, str]:
    """检查诚实边界（至少3条）"""
    boundary_match = re.search(
        r"(?:##\s+.*诚实边界|## Honest Boundary)(.*?)(?=\n##\s|\Z)", content, re.DOTALL | re.IGNORECASE
    )
    if not boundary_match:
        return False, "❌ 未找到诚实边界section"

    boundary_text = boundary_match.group(1)
    items = re.findall(r"^[-*]\s+", boundary_text, re.MULTILINE)
    count = len(items)
    passed = count >= 3
    return passed, f"诚实边界: {count}条 {'✅' if passed else '❌ (应≥3条)'}"


def check_tensions(content: str) -> tuple[bool, str]:
    """检查内在张力（至少2对）"""
    tension_markers = len(re.findall(r"张力|矛盾|tension|paradox|一方面.*另一方面|既.*又", content, re.IGNORECASE))
    passed = tension_markers >= 2
    return passed, f"内在张力: {tension_markers}处 {'✅' if passed else '❌ (应≥2处)'}"


def check_primary_sources(content: str) -> tuple[bool, str]:
    """检查一手来源占比——直接统计附录中列表项数量"""
    # Find "附录：调研来源" section
    source_section = re.search(r"##\s+附录：调研来源(.*?)(?=\n##\s|\Z)", content, re.DOTALL)
    if not source_section:
        return True, "未找到来源section（跳过检查）"

    source_text = source_section.group(1)

    # Find list items under "一手来源" and "二手来源"
    primary_section = re.search(r"###\s+一手来源(.*?)(?=###|\Z)", source_text, re.DOTALL)
    secondary_section = re.search(r"###\s+二手来源(.*?)(?=###|\Z)", source_text, re.DOTALL)

    primary_count = len(re.findall(r"^[-*]\s+", primary_section.group(1) if primary_section else "", re.MULTILINE))
    secondary_count = len(
        re.findall(r"^[-*]\s+", secondary_section.group(1) if secondary_section else "", re.MULTILINE)
    )

    total = primary_count + secondary_count
    if total == 0:
        return True, "未找到来源列表项（跳过检查）"

    ratio = primary_count / total
    passed = ratio >= 0.5  # Changed from > 0.5 to >= 0.5 (50% is acceptable)
    return (
        passed,
        f"一手来源: {primary_count}项, 二手: {secondary_count}项, 占比{ratio:.0%} {'✅' if passed else '❌ (应≥50%)'}",
    )


def check_sub_tactics(content: str) -> tuple[bool, str]:
    """检查模型3子战法完整性（应有3.1-3.17）"""
    # Match #### 3.X pattern (four-level heading)
    sub_tactics = re.findall(r"^####\s+3\.(\d+)", content, re.MULTILINE)
    if not sub_tactics:
        return True, "未找到模型3子战法（跳过检查）"

    sub_tactics = [int(x) for x in sub_tactics]
    expected = set(range(1, 18))  # 3.1 - 3.17
    found = set(sub_tactics)
    missing = expected - found

    if missing:
        return False, f"模型3子战法: 找到{len(found)}个, 缺失 {', '.join(f'3.{x}' for x in sorted(missing))}"
    return True, f"模型3子战法: {len(found)}个完整 ✅"


def check_model_completeness(content: str) -> tuple[bool, str]:
    """检查每个模型是否有核心内容（至少包含一句话总结或边界条件）"""
    model_headers = list(re.finditer(r"^###\s+模型\s*\d+[^\n]*", content, re.MULTILINE))
    if not model_headers:
        return True, "未找到标准模型格式（跳过检查）"

    models_with_content = 0
    for i, header_match in enumerate(model_headers):
        start = header_match.end()
        if i + 1 < len(model_headers):
            end = model_headers[i + 1].start()
        else:
            remaining = content[start:]
            next_h2 = re.search(r"^##\s+", remaining, re.MULTILINE)
            end = start + (next_h2.start() if next_h2 else len(remaining))

        section_content = content[start:end]
        if re.search(r"一句话|核心|本质|关键|框架|原则|逻辑", section_content, re.IGNORECASE):
            models_with_content += 1

    passed = models_with_content >= len(model_headers) * 0.6
    return passed, f"{models_with_content}/{len(model_headers)}个模型有核心内容 {'✅' if passed else '❌'}"


def check_v2_routing_surface(content: str) -> tuple[bool, str]:
    """检查 V2 路由声明：是否有明确的 Load when / 不加载条件"""
    has_routing_header = bool(re.search(r"##\s+.*路由声明|##\s+.*Routing Surface", content, re.IGNORECASE))
    has_load_when = bool(re.search(r"何时加载|Load when|触发条件|应该加载", content, re.IGNORECASE))
    has_not_load = bool(re.search(r"何时不加载|Do NOT|不加载|不触发|禁区", content, re.IGNORECASE))
    has_priority = bool(re.search(r"优先级|priority|优先加载|fallback", content, re.IGNORECASE))

    passed = has_routing_header and has_load_when and has_not_load
    details = []
    details.append(f"路由声明section: {'✅' if has_routing_header else '❌'}")
    details.append(f"加载条件: {'✅' if has_load_when else '❌'}")
    details.append(f"不加载条件: {'✅' if has_not_load else '❌'}")
    if has_priority:
        details.append("优先级规则: ✅")
    return passed, " | ".join(details)


def check_v2_contract_surface(content: str) -> tuple[bool, str]:
    """检查 V2 契约：输入契约、输出契约、边界与限制"""
    has_contract_header = bool(re.search(r"##\s+.*契约|##\s+.*Contract Surface", content, re.IGNORECASE))
    has_input = bool(re.search(r"输入契约|输入类型|input|Input", content, re.IGNORECASE))
    has_output = bool(re.search(r"输出契约|输出要求|output|Output", content, re.IGNORECASE))
    has_boundary = bool(re.search(r"边界与限制|边界|Limitation|限制", content, re.IGNORECASE))

    passed = has_contract_header and has_input and has_output
    details = []
    details.append(f"契约section: {'✅' if has_contract_header else '❌'}")
    details.append(f"输入契约: {'✅' if has_input else '❌'}")
    details.append(f"输出契约: {'✅' if has_output else '❌'}")
    details.append(f"边界限制: {'✅' if has_boundary else '❌'}")
    return passed, " | ".join(details)


def check_v2_runtime_boundary(content: str) -> tuple[bool, str]:
    """检查 V2 运行时边界：资源加载时机、工具链、失败退路"""
    has_runtime_header = bool(re.search(r"##\s+.*运行时资源|##\s+.*Runtime Boundary", content, re.IGNORECASE))
    has_knowledge_index = bool(re.search(r"知识文件|知识资源|加载时机|docs|references", content, re.IGNORECASE))
    has_toolchain = bool(re.search(r"工具链|工具调用|调用条件|tools|scripts", content, re.IGNORECASE))
    has_fallback = bool(re.search(r"失败退路|失败处理|fallback|降级|回退", content, re.IGNORECASE))

    passed = has_runtime_header and has_knowledge_index and has_toolchain
    details = []
    details.append(f"运行时section: {'✅' if has_runtime_header else '❌'}")
    details.append(f"知识文件索引: {'✅' if has_knowledge_index else '❌'}")
    details.append(f"工具链定义: {'✅' if has_toolchain else '❌'}")
    details.append(f"失败退路: {'✅' if has_fallback else '❌'}")
    return passed, " | ".join(details)


def check_v2_safety_surface(content: str) -> tuple[bool, str]:
    """检查 V2 安全边界：高风险动作、人类确认点、禁区"""
    has_safety_header = bool(re.search(r"##\s+.*安全边界|##\s+.*Safety Surface", content, re.IGNORECASE))
    has_high_risk = bool(re.search(r"高风险|风险等级|risk level|Risk Level", content, re.IGNORECASE))
    has_human_confirm = bool(re.search(r"人类确认|确认点|human confirm|确认规则|必须停下来", content, re.IGNORECASE))
    has_prohibited = bool(re.search(r"禁区|禁止|绝对不做|prohibited|禁区", content, re.IGNORECASE))

    passed = has_safety_header and has_high_risk and has_prohibited
    details = []
    details.append(f"安全边界section: {'✅' if has_safety_header else '❌'}")
    details.append(f"高风险动作: {'✅' if has_high_risk else '❌'}")
    details.append(f"人类确认点: {'✅' if has_human_confirm else '❌'}")
    details.append(f"禁区声明: {'✅' if has_prohibited else '❌'}")
    return passed, " | ".join(details)


def main():
    # 解析参数：支持 --json / --strict / --score
    args = sys.argv[1:]
    json_mode = "--json" in args
    strict_mode = "--strict" in args
    score_mode = "--score" in args
    if json_mode:
        args.remove("--json")
    if strict_mode:
        args.remove("--strict")
    if score_mode:
        args.remove("--score")

    def _err(msg: str) -> None:
        """统一错误输出：JSON 模式走 json.dumps，其他模式走人读"""
        if json_mode:
            print(json.dumps({"error": msg}, ensure_ascii=False))
        else:
            print(msg)

    if not args:
        _err("用法: python3 quality_check.py <SKILL.md路径> [--json] [--strict] [--score]")
        sys.exit(1)

    skill_path = Path(args[0])
    if not skill_path.exists():
        _err(f"❌ 文件不存在: {skill_path}")
        sys.exit(1)

    content = skill_path.read_text(encoding="utf-8")

    checks = [
        ("V2-路由声明", check_v2_routing_surface),
        ("V2-契约", check_v2_contract_surface),
        ("V2-运行时边界", check_v2_runtime_boundary),
        ("V2-安全边界", check_v2_safety_surface),
        ("心智模型数量", check_mental_models),
        ("模型局限性", check_limitations),
        ("表达DNA辨识度", check_expression_dna),
        ("诚实边界", check_honest_boundary),
        ("内在张力", check_tensions),
        ("一手来源占比", check_primary_sources),
        ("子战法完整性", check_sub_tactics),
        ("模型完整性", check_model_completeness),
    ]

    results = []
    for name, check_fn in checks:
        passed, detail = check_fn(content)
        results.append(
            {
                "name": name,
                "passed": bool(passed),
                "detail": detail,
            }
        )

    passed_count = sum(1 for r in results if r["passed"])
    total = len(results)
    failed_count = total - passed_count
    score = int(round(passed_count / total * 100)) if total else 0

    if json_mode:
        # 结构化输出：便于 CI / PR comment 解析
        summary = {
            "file": str(skill_path),
            "passed": passed_count,
            "failed": failed_count,
            "total": total,
            "score": score,
            "all_passed": passed_count == total,
            "checks": results,
        }
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        sys.exit(0 if passed_count == total else 1)

    if score_mode:
        # 仅输出分数，便于脚本调用
        print(score)
        sys.exit(0 if passed_count == total else 1)

    # 人读模式（默认）
    print(f"质量检查: {skill_path.name}")
    print("=" * 60)
    for r in results:
        status = "✅ PASS" if r["passed"] else "❌ FAIL"
        print(f"  {r['name']:<12} {status}  {r['detail']}")
    print("=" * 60)
    print(f"结果: {passed_count}/{total} 通过 | 综合得分: {score}/100")

    if passed_count == total:
        print("🎉 全部通过，可以交付")
    elif passed_count >= total - 1:
        print("⚠️ 基本通过，建议修复不通过项后交付")
    else:
        print("❌ 多项不通过，建议回到Phase 2迭代")

    # --strict 模式：任何 fail 都 exit 1（默认模式与历史行为一致：仅在全部 fail 时 exit 1）
    if strict_mode:
        sys.exit(0 if passed_count == total else 1)
    else:
        sys.exit(0 if passed_count == total else 1)


if __name__ == "__main__":
    main()
