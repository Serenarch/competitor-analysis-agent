"""自定义评估器"""
from typing import Any


# ============================================================
# 评估器 1：章节完整度（规则型，免费）
# ============================================================
def report_sections_completeness(run, example) -> dict:
    """检查报告是否包含所有必需章节"""
    comparison_mode = run.outputs.get("comparison_mode", False)
    if comparison_mode:
        # 对比模式不检查这个评估器
        return {
            "key": "sections_completeness",
            "score": 1.0,
            "comment": "对比模式，跳过单竞品章节检查",
        }

    report = run.outputs.get("report", "")
    expected = example.outputs.get("expected_sections", [])

    if not expected:
        return {"key": "sections_completeness", "score": 0.0}

    hits = sum(1 for s in expected if s in report)
    score = hits / len(expected)

    return {
        "key": "sections_completeness",
        "score": score,
        "comment": f"包含 {hits}/{len(expected)} 个章节",
    }


# ============================================================
# 评估器 2：来源覆盖（规则型，免费）
# ============================================================
def source_coverage(run, example) -> dict:
    """检查来源数量是否达标"""
    sources = run.outputs.get("all_sources", [])
    min_required = example.outputs.get("min_sources", 10)

    # 去重
    unique_urls = set(s.get("url") for s in sources if s.get("url"))
    count = len(unique_urls)

    # 达到要求得 1.0，否则按比例给分
    score = min(1.0, count / min_required) if min_required > 0 else 1.0

    return {
        "key": "source_coverage",
        "score": score,
        "comment": f"{count} 个唯一来源（要求 ≥ {min_required}）",
    }


# ============================================================
# 评估器 3：报告长度（规则型，免费）
# ============================================================
def report_length_score(run, example) -> dict:
    """检查报告长度是否足够"""
    report = run.outputs.get("report", "")
    min_length = example.outputs.get("min_length", 1500)

    length = len(report)
    score = min(1.0, length / min_length) if min_length > 0 else 1.0

    return {
        "key": "report_length",
        "score": score,
        "comment": f"{length} 字符（要求 ≥ {min_length}）",
    }


# ============================================================
# 评估器 4：报告质量（LLM-as-Judge，有成本）
# ============================================================
JUDGE_PROMPT = """你是资深竞品分析专家。请评估以下报告的质量。

报告内容：
{report}

请从三个维度打分（每项 0-10 分）：
1. 信息完整性：是否覆盖了产品定位、功能、定价、用户评价、竞争格局等核心维度
2. 数据支撑：是否有具体的数字、日期、名称等事实性内容
3. 分析深度：是否给出了有洞察力的结论，而非简单罗列信息

只返回 JSON，格式：
{{"completeness": 8, "data_support": 7, "insight_depth": 6, "reason": "简要说明"}}
"""


def report_quality_judge(run, example) -> dict:
    """用 LLM 评估报告质量"""
    from app.llm import get_llm
    import json
    import re

    report = run.outputs.get("report", "")
    if not report:
        return {"key": "report_quality", "score": 0.0, "comment": "报告为空"}

    # 限制长度，避免超上下文
    report_excerpt = report[:6000]

    try:
        llm = get_llm(temperature=0.0)
        response = llm.invoke(JUDGE_PROMPT.format(report=report_excerpt))
        content = response.content

        # 提取 JSON
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if not json_match:
            return {"key": "report_quality", "score": 0.5, "comment": "无法解析评分"}

        data = json.loads(json_match.group())

        # 三项平均，归一化到 0~1
        scores = [
            data.get("completeness", 5),
            data.get("data_support", 5),
            data.get("insight_depth", 5),
        ]
        avg = sum(scores) / len(scores)
        normalized = avg / 10.0

        return {
            "key": "report_quality",
            "score": normalized,
            "comment": f"完整性={scores[0]}, 数据={scores[1]}, 深度={scores[2]}",
        }
    except Exception as e:
        return {"key": "report_quality", "score": 0.0, "comment": f"评估失败: {e}"}

# ============================================================
# 评估器 5：数据密度
# ============================================================
import re

def data_density(run, example) -> dict:
    """统计报告中的数字密度，反映数据支撑程度"""
    report = run.outputs.get("report", "")
    if not report:
        return {"key": "data_density", "score": 0.0, "comment": "报告为空"}

    # 匹配数字（整数、小数、百分比、金额）
    # 排除章节编号（一、二、1. 2. 等）
    text = re.sub(r'^#+\s*\S+\s*', '', report, flags=re.MULTILINE)
    numbers = re.findall(r'\d+(?:\.\d+)?(?:%|万|亿|美元|元|M|B|K)?', text)

    # 排除纯序号
    meaningful = [n for n in numbers if not re.fullmatch(r'\d{1,2}[\.、]?', n)]

    count = len(meaningful)
    # 评分标准：>=30 个数字满分；每 3 个数字给 0.1 分
    score = min(1.0, count / 15.0)

    return {
        "key": "data_density",
        "score": score,
        "comment": f"共 {count} 个数据点（目标 ≥ 15）",
    }


# ============================================================
# 评估器 6：诚实报告
# ============================================================
def honest_reporting(run, example) -> dict:
    """检查 Agent 在数据稀缺时是否诚实报告"""
    report = run.outputs.get("report", "")
    data_expectation = example.outputs.get("data_expectation", "normal")

    if data_expectation != "low":
        return {"key": "honest_reporting", "score": 1.0, "comment": "不适用"}

    # 在数据稀缺场景下，检查是否有"未找到"、"未披露"等诚实说明
    honest_markers = ["未找到", "未披露", "未公开", "暂无", "缺乏", "数据不足"]
    has_marker = any(m in report for m in honest_markers)
    # 检查是否有编造的痕迹（虚构的具体数字）
    has_fabrication = "约" in report and report.count("约") > 5

    score = 1.0 if has_marker and not has_fabrication else 0.3

    return {
        "key": "honest_reporting",
        "score": score,
        "comment": "诚实报告数据缺失" if score > 0.8 else "可能编造数据",
    }

# ============================================================
# 评估器 7：事实一致性
# ============================================================
import re


def _extract_numbers(text: str) -> set:
    """
    从文本中提取所有数字。
    匹配：整数、小数、百分比、金额、万/亿等单位

    过滤规则：
    - 排除章节编号（如 2.1, 3.4）
    - 排除纯序号（1-20 的整数）
    - 排除 Markdown 表格分隔符中的数字
    """
    import re

    # 预处理：去掉章节编号（形如 ## 2.1 xxx 或 ### 2.3 xxx）
    # 这样 2.1 / 3.4 这种章节编号不会被误判为数据
    cleaned = re.sub(r'#+\s*\d+\.\d+\s', '', text)  # 去掉 "## 2.1 " 这种
    cleaned = re.sub(r'^\d+\.\d+\s+', '', cleaned, flags=re.MULTILINE)  # 去掉行首 "2.1 "
    cleaned = re.sub(r'^\d+\.\s+', '', cleaned, flags=re.MULTILINE)  # 去掉行首 "1. "

    patterns = [
        r'\d+\.\d+%',  # 41.78%
        r'\d+%',  # 50%
        r'\$\d+\.?\d*',  # $16, $399.99
        r'\d+\.?\d*\s*万',  # 1300 万
        r'\d+\.?\d*\s*亿',  # 100 亿
        r'\d+\.?\d*',  # 普通数字
    ]
    numbers = set()
    for p in patterns:
        for m in re.findall(p, cleaned):
            numbers.add(m.replace(' ', ''))

    # 过滤掉纯序号（1-20 的整数）
    def is_serial(s: str) -> bool:
        if not s.isdigit():
            return False
        return 1 <= int(s) <= 20

    return {n for n in numbers if not is_serial(n)}


def fact_consistency(run, example) -> dict:
    """
    检查对比报告中的数字是否都出现在原始 summaries 里。

    逻辑：
    1. 从报告里提取所有数字
    2. 从原始 summaries 里提取所有数字（来源真值）
    3. 计算报告数字在真值里的覆盖率

    注意：
    - 只对对比模式生效（单竞品模式跳过）
    - 过滤掉常见的非事实数字（如章节编号 1. 2. 3.）
    """
    report = run.outputs.get("report", "")
    summaries = run.outputs.get("all_summaries_text", "")
    comparison_mode = run.outputs.get("comparison_mode", False)

    if not comparison_mode:
        return {
            "key": "fact_consistency",
            "score": 1.0,
            "comment": "非对比模式，跳过",
        }

    if not report or not summaries:
        return {
            "key": "fact_consistency",
            "score": 0.0,
            "comment": "报告或原文为空",
        }

    report_numbers = _extract_numbers(report)
    source_numbers = _extract_numbers(summaries)


    if not report_numbers:
        return {
            "key": "fact_consistency",
            "score": 1.0,
            "comment": "报告中没有可验证的数字",
        }

    # 计算覆盖率
    matched = report_numbers & source_numbers
    coverage = len(matched) / len(report_numbers)

    # 找出未匹配的数字（可能是幻觉）
    unmatched = report_numbers - source_numbers
    sample_unmatched = list(unmatched)[:5]

    # 评分标准：
    # - 覆盖率 >= 0.9 → 1.0
    # - 覆盖率 0.75~0.9 → 0.8
    # - 覆盖率 0.5~0.75 → 0.5
    # - 覆盖率 < 0.5 → 0.2
    if coverage >= 0.9:
        score = 1.0
        comment = f"数字覆盖率 {coverage:.0%}（{len(matched)}/{len(report_numbers)}）"
    elif coverage >= 0.75:
        score = 0.8
        comment = f"数字覆盖率 {coverage:.0%}，少量未匹配：{sample_unmatched}"
    elif coverage >= 0.5:
        score = 0.5
        comment = f"数字覆盖率 {coverage:.0%}，存在幻觉风险，未匹配示例：{sample_unmatched}"
    else:
        score = 0.2
        comment = f"数字覆盖率仅 {coverage:.0%}，严重幻觉，未匹配示例：{sample_unmatched}"

    return {
        "key": "fact_consistency",
        "score": score,
        "comment": comment,
    }

# ============================================================
# 评估器 8：对比完整度
# ============================================================
def comparison_coverage(run, example) -> dict:
    """
    检查对比报告是否：
    1. 提及所有竞品
    2. 包含对比表格
    3. 有对比矩阵的维度
    """
    comparison_mode = run.outputs.get("comparison_mode", False)
    if not comparison_mode:
        return {
            "key": "comparison_coverage",
            "score": 1.0,
            "comment": "非对比模式，跳过",
        }

    report = run.outputs.get("report", "")
    competitors = example.inputs.get("competitors", []) or []
    matrix = run.outputs.get("comparison_matrix", {}) or {}

    if not competitors:
        return {
            "key": "comparison_coverage",
            "score": 0.0,
            "comment": "未找到竞品列表",
        }

    # 1. 每个竞品是否在报告中出现
    mentioned = sum(1 for c in competitors if c in report)
    coverage = mentioned / len(competitors)

    # 2. 是否有对比表格（至少有 3 行表格）
    table_rows = report.count("\n|")
    has_table = table_rows >= 5

    # 3. 对比矩阵维度数
    dimension_count = len(matrix)
    has_matrix = dimension_count >= 2

    # 综合评分
    score = coverage * 0.5
    if has_table:
        score += 0.25
    if has_matrix:
        score += 0.25

    comment_parts = [
        f"提及 {mentioned}/{len(competitors)} 个竞品",
        f"{'有' if has_table else '无'}对比表格",
        f"矩阵维度 {dimension_count}",
    ]

    return {
        "key": "comparison_coverage",
        "score": round(min(1.0, score), 2),
        "comment": "，".join(comment_parts),
    }


# ============================================================
# 评估器 9：选型建议
# ============================================================
def has_selection_advice(run, example) -> dict:
    """
    检查对比报告是否包含选型建议。
    核心逻辑：定位"选型建议"章节，统计该章节内的列表项和特征。
    """
    import re

    comparison_mode = run.outputs.get("comparison_mode", False)
    if not comparison_mode:
        return {
            "key": "has_selection_advice",
            "score": 1.0,
            "comment": "非对比模式，跳过",
        }

    report = run.outputs.get("report", "")
    if not report:
        return {
            "key": "has_selection_advice",
            "score": 0.0,
            "comment": "报告为空",
        }

    # ============================================================
    # 1. 章节标题检测
    # ============================================================
    section_markers = [
        "选型建议", "选购建议", "场景推荐",
        "如何选择", "推荐选择", "选型指南",
    ]
    has_section = any(m in report for m in section_markers)

    # ============================================================
    # 2. 定位选型章节内容
    # ============================================================
    section_pattern = re.compile(
        r'##+[^\n]*(?:选型建议|选购建议|场景推荐|选型指南)[^\n]*\n'
        r'(.*?)'
        r'(?=\n##+\s|\Z)',
        re.DOTALL,
    )
    match = section_pattern.search(report)
    section_content = match.group(1) if match else ""

    # ============================================================
    # 3. 章节内列表项统计（不要求含关键词）
    # ============================================================
    if section_content:
        # 统计列表项：以数字(1. 2.) 或 - / * 开头
        list_items_in_section = len(re.findall(
            r'^\s*(?:\d+\.|[-*])\s+\S',
            section_content,
            re.MULTILINE,
        ))
    else:
        # 没有明确章节时，全文统计
        list_items_in_section = len(re.findall(
            r'^\s*(?:\d+\.|[-*])\s+\S',
            report,
            re.MULTILINE,
        ))

    # ============================================================
    # 4. 场景段落检测
    # ============================================================
    scene_section_patterns = [
        r'优先选择[^\n]{0,30}的场景',
        r'优先选择[^\n]{0,30}',
        r'谨慎选型[^\n]{0,20}',
        r'[^\n]{1,20}适用场景',
        r'推荐选择[^\n]{0,20}',
        r'不推荐选择[^\n]{0,20}',
        r'适用场景[:：]',
    ]
    scene_section_count = sum(
        len(re.findall(p, report)) for p in scene_section_patterns
    )

    # ============================================================
    # 5. "如果你是..." 句式
    # ============================================================
    scene_patterns = [
        r'如果你是[^，。\n]{1,40}',
        r'若你是[^，。\n]{1,40}',
        r'对于[^，。\n]{1,30}场景',
        r'适用于[^，。\n]{1,30}',
    ]
    scene_count = sum(len(re.findall(p, report)) for p in scene_patterns)

    # ============================================================
    # 6. 推荐关键词
    # ============================================================
    recommend_keywords = ["推荐", "建议选择", "建议使用", "优先选择"]
    recommend_count = sum(report.count(kw) for kw in recommend_keywords)

    # ============================================================
    # 7. 表格形式
    # ============================================================
    table_advice_patterns = [
        r'\|\s*场景\s*\|',
        r'\|[^|\n]*(?:建议选择|推荐|建议)[^|\n]*\|',
        r'\|\s*建议\s*\|',
        r'\|\s*适用场景\s*\|',
    ]
    has_advice_table = any(re.search(p, report) for p in table_advice_patterns)

    # ============================================================
    # 8. 综合评分
    # ============================================================
    score = 0.0

    # 章节标题（基本门槛）
    if has_section:
        score += 0.2

    # 场景段落小标题
    if scene_section_count >= 2:
        score += 0.2
    elif scene_section_count >= 1:
        score += 0.1

    # 章节内列表项（核心指标）
    if list_items_in_section >= 4:
        score += 0.3
    elif list_items_in_section >= 2:
        score += 0.15

    # "如果你是"句式
    if scene_count >= 2:
        score += 0.15
    elif scene_count >= 1:
        score += 0.05

    # 推荐关键词
    if recommend_count >= 3:
        score += 0.2
    elif recommend_count >= 1:
        score += 0.05

    # 表格形式（强结构化）
    if has_advice_table:
        score += 0.3

    comment_parts = [
        f"{'有' if has_section else '无'}选型章节",
        f"列表项 {list_items_in_section}",
        f"场景段 {scene_section_count}",
        f"如果是句 {scene_count}",
        f"推荐词 {recommend_count}",
        f"{'有' if has_advice_table else '无'}表格",
    ]

    return {
        "key": "has_selection_advice",
        "score": round(min(1.0, score), 2),
        "comment": "，".join(comment_parts),
    }
# ============================================================
# 评估器列表
# ============================================================
ALL_EVALUATORS = [
    report_sections_completeness,
    source_coverage,
    report_length_score,
    data_density,
    report_quality_judge,
    honest_reporting,
    fact_consistency,
    comparison_coverage,
    has_selection_advice,
]