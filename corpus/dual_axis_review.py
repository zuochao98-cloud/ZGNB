#!/usr/bin/env python3
"""
双轴 Skill 质量评审。

轴 A（确定性检查）：复用 corpus/quality_check.py 的 12 项规则，输出 0-100 分。
轴 B（LLM 深度评审）：由 LLM 从角色一致性、表达 DNA、诚实边界、可维护性四个维度评分。

用法:
    python3 dual_axis_review.py <SKILL.md路径>
    python3 dual_axis_review.py <SKILL.md路径> --json
    python3 dual_axis_review.py <SKILL.md路径> --skip-llm   # 只跑轴 A

环境变量:
    LLM_API_KEY     # 必填（或 ANTHROPIC_API_KEY），否则轴 B 自动跳过
    LLM_BASE_URL    # 可选，默认 MiniMax 兼容端点
    LLM_MODEL       # 可选
"""

import json
import os
import subprocess
import sys
from pathlib import Path


def _run_axis_a(skill_path: Path) -> dict:
    """调用 quality_check.py --json 获取轴 A 结果。"""
    cmd = [sys.executable, str(Path(__file__).parent / "quality_check.py"), str(skill_path), "--json"]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if proc.returncode not in (0, 1):
        # quality_check 在检查失败时 exit 1，但仍会输出 JSON；其他退出码才说明脚本异常
        raise RuntimeError(f"quality_check.py 执行异常: {proc.stderr or proc.stdout}")
    return json.loads(proc.stdout)


def _load_skill_content(skill_path: Path) -> str:
    return skill_path.read_text(encoding="utf-8")


def _build_llm_prompt(skill_content: str) -> tuple[str, str]:
    """构造轴 B 评审的系统提示词与用户消息。"""
    system_prompt = """你是一名严谨的 Skill 质量评审员，专门评估「zettaranc（万千）」角色扮演 Skill 的质量。
请从以下 4 个维度对给定的 SKILL.md 内容进行评审，每个维度给出 0-25 分，并附 1-2 句理由。
只输出 JSON，不要任何额外解释。

JSON 格式：
{
  "dimensions": [
    {"name": "角色一致性", "score": 0-25, "reason": "..."},
    {"name": "表达DNA", "score": 0-25, "reason": "..."},
    {"name": "诚实边界", "score": 0-25, "reason": "..."},
    {"name": "可维护性", "score": 0-25, "reason": "..."}
  ],
  "total_score": 0-100,
  "summary": "一句话总结"
}

评分标准：
- 角色一致性：是否用「我」而非第三人称；是否有职业背书开场；是否保持 Z 哥口吻而非 AI 味。
- 表达DNA：是否分 1/2/3/4 点拆解；是否用具体数字/案例；是否以金句或反问收尾；是否使用算账句/死规矩体。
- 诚实边界：是否明确标注公开表达与真实想法的差异；是否说明语料截止和数据局限；是否有强制免责声明。
- 可维护性：结构是否清晰（路由/契约/运行时/安全边界）；引用是否明确；是否避免过长段落。"""

    user_message = f"请评审以下 SKILL.md 内容：\n\n```markdown\n{skill_content[:12000]}\n```"
    return system_prompt, user_message


def _parse_llm_score(raw: str) -> dict:
    """从 LLM 输出中提取 JSON。"""
    # 尝试直接解析
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # 尝试从 markdown 代码块中提取
    import re

    code_block = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
    if code_block:
        try:
            return json.loads(code_block.group(1))
        except json.JSONDecodeError:
            pass

    raise ValueError(f"无法解析 LLM 评审输出: {raw[:200]}")


def _run_axis_b(skill_path: Path) -> dict | None:
    """运行 LLM 深度评审。无 API key 时返回 None。"""
    api_key = os.getenv("LLM_API_KEY", "") or os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        return None

    # 将项目根目录加入路径以导入 modules.llm_providers
    project_root = Path(__file__).parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    from modules.llm_providers import MiniMaxProvider

    skill_content = _load_skill_content(skill_path)
    system_prompt, user_message = _build_llm_prompt(skill_content)

    provider = MiniMaxProvider(api_key=api_key)
    raw = provider.generate(system_prompt, user_message, temperature=0.3)

    if raw.startswith("["):
        # API 返回错误信息
        return {"error": raw, "total_score": 0}

    try:
        return _parse_llm_score(raw)
    except ValueError as e:
        return {"error": str(e), "total_score": 0}


def _calculate_blended_score(axis_a_score: int, axis_b_score: int | None, axis_b_weight: float = 0.3) -> int:
    """综合评分：默认轴 B 占 30%。"""
    if axis_b_score is None:
        return axis_a_score
    blended = axis_a_score * (1 - axis_b_weight) + axis_b_score * axis_b_weight
    return int(round(blended))


def main():
    args = sys.argv[1:]
    json_mode = "--json" in args
    skip_llm = "--skip-llm" in args
    if json_mode:
        args.remove("--json")
    if skip_llm:
        args.remove("--skip-llm")

    if not args:
        print("用法: python3 dual_axis_review.py <SKILL.md路径> [--json] [--skip-llm]")
        sys.exit(1)

    skill_path = Path(args[0])
    if not skill_path.exists():
        print(f"❌ 文件不存在: {skill_path}")
        sys.exit(1)

    axis_a = _run_axis_a(skill_path)
    axis_a_score = axis_a.get("score", 0)

    axis_b = None
    axis_b_error = None
    if not skip_llm:
        axis_b = _run_axis_b(skill_path)
        if axis_b and "error" in axis_b:
            axis_b_error = axis_b["error"]
            axis_b = None

    axis_b_score = axis_b.get("total_score") if axis_b else None
    blended_score = _calculate_blended_score(axis_a_score, axis_b_score)

    result = {
        "file": str(skill_path),
        "axis_a": {
            "name": "确定性质量检查",
            "score": axis_a_score,
            "passed": axis_a.get("passed", 0),
            "total": axis_a.get("total", 0),
            "all_passed": axis_a.get("all_passed", False),
        },
        "axis_b": {
            "name": "LLM 深度评审",
            "score": axis_b_score,
            "details": axis_b.get("dimensions") if axis_b else None,
            "summary": axis_b.get("summary") if axis_b else None,
            "skipped": skip_llm,
            "error": axis_b_error,
        },
        "blended_score": blended_score,
    }

    if json_mode:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("=" * 60)
        print(f"双轴 Skill 质量评审: {skill_path.name}")
        print("=" * 60)
        print(f"轴 A 确定性检查: {axis_a_score}/100 ({axis_a.get('passed', 0)}/{axis_a.get('total', 0)} 通过)")
        if axis_b:
            print(f"轴 B LLM 深度评审: {axis_b_score}/100")
            for dim in axis_b.get("dimensions", []):
                print(f"  - {dim['name']}: {dim['score']}/25 | {dim['reason']}")
            print(f"  总结: {axis_b.get('summary', '')}")
        elif skip_llm:
            print("轴 B LLM 深度评审: 已跳过 (--skip-llm)")
        elif axis_b_error:
            print(f"轴 B LLM 深度评审: 跳过 | 原因: {axis_b_error}")
        else:
            print("轴 B LLM 深度评审: 跳过 | 原因: 未配置 LLM_API_KEY 或 ANTHROPIC_API_KEY")
        print("-" * 60)
        print(f"综合得分: {blended_score}/100")
        if blended_score >= 90:
            print("🎉 质量优秀")
        elif blended_score >= 75:
            print("⚠️ 质量良好，仍有提升空间")
        else:
            print("❌ 建议迭代后再交付")

    # 任意一轴未达 60 分即视为不通过
    axis_a_ok = axis_a_score >= 60
    axis_b_ok = axis_b_score is None or axis_b_score >= 60
    sys.exit(0 if (axis_a_ok and axis_b_ok) else 1)


if __name__ == "__main__":
    main()
