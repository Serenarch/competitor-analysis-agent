"""运行 LangSmith 评估（支持单竞品 + 对比模式）"""
import time
from langsmith import Client, evaluate

from app.config import settings  # noqa: F401  触发 LangSmith 环境变量加载
from app.graph.workflow import get_graph
from app.evaluation.dataset import create_or_get_dataset, DATASET_NAME
from app.evaluation.evaluators import ALL_EVALUATORS


def target(inputs: dict) -> dict:
    """被测函数：跑一次完整的竞品分析"""
    graph = get_graph()

    # ------------------------------------------------------------
    # 1. 归一化输入：兼容 competitor / competitors
    # ------------------------------------------------------------
    if "competitors" in inputs and inputs["competitors"]:
        competitors = [c for c in inputs["competitors"] if c]
    elif "competitor" in inputs and inputs["competitor"]:
        competitors = [inputs["competitor"]]
    else:
        competitors = []

    if not competitors:
        return {
            "report": "",
            "all_sources": [],
            "duration_seconds": 0.0,
            "comparison_mode": False,
            "all_summaries_text": "",
            "comparison_matrix": {},
            "error": "no competitors provided",
        }

    comparison_mode = len(competitors) > 1

    # ------------------------------------------------------------
    # 2. 构造初始状态
    # ------------------------------------------------------------
    initial_state = {
        "competitors": competitors,
        "current_competitor": competitors[0],
        "comparison_mode": comparison_mode,
        "competitor": competitors[0],
        "industry": inputs.get("industry"),
        "domain": inputs.get("domain", "software"),
        "focus_areas": inputs.get("focus_areas", []),
        "tasks": [],
        "tasks_per_competitor": {},
        "current_task_index": 0,
        "raw_content": "",
        "raw_sources": [],
        "summaries": [],
        "report": None,
        "report_type": "comparison" if comparison_mode else "single",
        "comparison_matrix": None,
        "comparison_insights": None,
        "retry_count": 0,
        "error": None,
        "status": "pending",
    }

    config = {
        "configurable": {
            "thread_id": f"eval-{'-'.join(competitors)}-{int(time.time())}"
        }
    }

    # ------------------------------------------------------------
    # 3. 执行
    # ------------------------------------------------------------
    start = time.time()
    try:
        result = graph.invoke(initial_state, config=config)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "report": "",
            "all_sources": [],
            "duration_seconds": time.time() - start,
            "comparison_mode": comparison_mode,
            "all_summaries_text": "",
            "comparison_matrix": {},
            "error": f"{type(e).__name__}: {e}",
        }
    duration = time.time() - start

    # ------------------------------------------------------------
    # 4. 汇总来源
    # ------------------------------------------------------------
    all_sources = []
    for s in result.get("summaries", []):
        for src in getattr(s, "sources", []) or []:
            if hasattr(src, "model_dump"):
                all_sources.append(src.model_dump())
            else:
                all_sources.append(src)

        # ------------------------------------------------------------
        # 5. 构造原始 summaries 文本（供 fact_consistency 用）
        # ------------------------------------------------------------
        # 污染检测标志（与 analyzer.py 保持一致）
    POLLUTION_MARKERS = [
        "你是一位竞品分析专家",
        "输出要求：",
        "数据提取要求",
        "关键数据\"部分必须",
        "请基于给定内容",
        "请基于给定的搜索结果",
        "禁止写",
        "明确写\"未找到\"",
        "结构：核心发现",
        "只基于给定内容",
    ]

    def _is_clean(text: str) -> bool:
        """判断 summary 是否干净（未被 prompt 污染）"""
        if not text:
            return False
        hit_count = sum(1 for m in POLLUTION_MARKERS if m in text)
        return hit_count < 2

    summaries = result.get("summaries", [])
    unique = {}
    for s in summaries:
        key = (getattr(s, "competitor", "") or "", s.task_id)
        unique[key] = s

    sorted_summaries = sorted(
        unique.values(),
        key=lambda x: (getattr(x, "competitor", "") or "", x.task_id),
    )

    # 过滤污染内容
    clean_summaries = [
        s for s in sorted_summaries
        if _is_clean(getattr(s, "summary", ""))
    ]

    polluted_count = len(sorted_summaries) - len(clean_summaries)
    if polluted_count > 0:
        print(f"[target] ⚠️ 过滤掉 {polluted_count} 条被污染的 summary")

    all_summaries_text = "\n\n".join([
        f"### [{getattr(s, 'competitor', '') or '未知'}] {s.title}\n{s.summary}"
        for s in clean_summaries
    ])

    # ------------------------------------------------------------
    # 6. 返回评估器需要的所有字段
    # ------------------------------------------------------------
    return {
        "report": result.get("report", "") or "",
        "all_sources": all_sources,
        "duration_seconds": duration,
        "comparison_mode": comparison_mode,
        "all_summaries_text": all_summaries_text,
        "comparison_matrix": result.get("comparison_matrix") or {},
        "comparison_insights": result.get("comparison_insights") or "",
        "report_type": result.get("report_type", "single"),
        "status": result.get("status", "unknown"),
    }


def run_evaluation(max_samples: int = None, experiment_prefix: str = "comparison-baseline-v1"):
    """
    运行评估

    Args:
        max_samples: 限制样本数（None 表示全部）
        experiment_prefix: 实验前缀
    """
    # 确保数据集存在
    create_or_get_dataset()

    # 选择样本
    if max_samples:
        client = Client()
        examples = list(client.list_examples(dataset_name=DATASET_NAME))
        data = examples[:max_samples]
        print(f"📊 使用前 {len(data)} 条样本")
    else:
        data = DATASET_NAME
        print(f"📊 使用全部样本")

    print(f"🔬 实验前缀: {experiment_prefix}")
    print(f"🧪 评估器数量: {len(ALL_EVALUATORS)}")
    print("=" * 60)
    print("开始评估...")
    print("=" * 60)

    results = evaluate(
        target,
        data=data,
        evaluators=ALL_EVALUATORS,
        experiment_prefix=experiment_prefix,
        max_concurrency=1,   # 串行，避免 API 限流
    )

    print("\n" + "=" * 60)
    print("✅ 评估完成")
    print("=" * 60)
    print("\n去 LangSmith 控制台查看详细结果：")
    print("https://smith.langchain.com")
    print(f"\n进入 Datasets → {DATASET_NAME} → Experiments")
    print(f"找到实验：{experiment_prefix}")

    return results


if __name__ == "__main__":
    # 第一次跑：先只跑 3 条（2 单竞品 + 1 对比），约 5~10 分钟
    # 验证流程后再跑全部 7 条
    run_evaluation(max_samples=3, experiment_prefix="comparison-baseline-v1")