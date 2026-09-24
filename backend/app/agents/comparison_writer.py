"""ComparisonWriter 节点：基于对比矩阵生成对比报告"""
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from app.llm import get_llm
from app.graph.state import CompetitorState
from app.config.domains import get_domain_template


class ComparisonReport(BaseModel):
    report: str = Field(
        ...,
        description="Markdown 格式的对比报告",
        min_length=500,
    )


COMPARISON_WRITER_PROMPT = """你是资深分析师。请基于以下对比矩阵和洞察，生成一份专业的{domain_display}对比分析报告。

对比对象：{competitors}
分析领域：{domain_display}

【对比矩阵】
{matrix}

【对比洞察】
{insights}

【报告结构要求】
报告必须包含以下章节（缺一不可）：

# {title}

## 一、对比概览
用表格列出各对象的关键信息（定位、目标用户、核心优势）

## 二、核心维度对比
对每个对比维度做详细对比，用表格 + 文字分析
每个维度末尾附一段"洞察"

## 三、差异化分析
指出各对象的核心差异和独特优势

## 四、SWOT 对比
用表格对比各对象的优势、劣势、机会、威胁

## 五、选型建议
针对不同场景给出选择建议

【严格的数字保留规则（非常重要）】
1. 报告中的所有数字必须**直接来自对比矩阵**，禁止修改
2. 例如：矩阵里写"$16/月"，报告里必须写"$16/月"，不能改
3. 例如：矩阵里写"1300 万用户"，报告里必须写"1300 万用户"
4. 如果一个数字不确定，宁可不写，也不要用"约"、"大概"来模糊
5. 如果矩阵里没有某个数字，明确写"未找到"

【数据要求】
- 每个对比维度必须有表格
- 每个结论都要有具体数据或事实支撑
- 禁止写"用户很多"、"价格较高"这类模糊表述
- 数据缺失时写"未找到"

【格式要求】
- Markdown 格式
- 章节标题用二级标题（##）
- 表格使用 Markdown 表格语法
"""


def comparison_writer_node(state: CompetitorState) -> dict:
    """对比报告生成节点"""
    competitors = state.get("competitors") or []
    if len(competitors) < 2:
        return {"error": "对比模式需要至少 2 个分析对象"}

    domain = state.get("domain", "software")
    template = get_domain_template(domain)
    matrix = state.get("comparison_matrix") or {}
    insights = state.get("comparison_insights", "")

    print(f"\n[ComparisonWriter] 生成对比报告：{competitors}")

    if not matrix:
        return {
            "report": "# 对比失败\n\n未能生成对比矩阵。",
            "status": "failed",
            "error": "对比矩阵为空",
        }

    # 格式化矩阵
    matrix_lines = []
    for dim, comp_data in matrix.items():
        matrix_lines.append(f"### {dim}")
        for comp, text in comp_data.items():
            matrix_lines.append(f"- **{comp}**: {text}")
        matrix_lines.append("")
    matrix_str = "\n".join(matrix_lines)

    title = " vs ".join(competitors) + f" {template['display_name']}对比分析"

    prompt = ChatPromptTemplate.from_messages([
        ("user", COMPARISON_WRITER_PROMPT),
    ])

    llm = get_llm(temperature=0.3)
    chain = prompt | llm.with_structured_output(ComparisonReport)

    result: ComparisonReport = chain.invoke({
        "competitors": "、".join(competitors),
        "domain_display": template["display_name"],
        "matrix": matrix_str[:10000],
        "insights": insights,
        "title": title,
    })

    print(f"[ComparisonWriter] 报告生成完成，长度：{len(result.report)} 字符")

    return {
        "report": result.report,
        "report_type": "comparison",
        "status": "completed",
    }