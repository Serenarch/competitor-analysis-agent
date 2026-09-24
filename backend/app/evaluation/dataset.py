"""创建 LangSmith 评估数据集（含单竞品和对比模式）"""
from langsmith import Client
from app.config import settings
DATASET_NAME = "competitor-analysis-eval-v1"


def create_or_get_dataset():
    """创建或获取评估数据集"""
    client = Client()

    # 1. 尝试获取已存在的数据集
    try:
        dataset = client.read_dataset(dataset_name=DATASET_NAME)
        print(f"✅ 数据集已存在: {DATASET_NAME}")
    except Exception:
        dataset = client.create_dataset(
            dataset_name=DATASET_NAME,
            description="竞品分析 Agent 的评估数据集（含单竞品 + 对比模式）",
        )
        print(f"✅ 创建数据集: {DATASET_NAME}")

    # 2. 检查是否已有样本
    existing = list(client.list_examples(dataset_id=dataset.id))
    if existing:
        print(f"⚠️  已有 {len(existing)} 条样本，跳过创建")
        print(f"   如需新增样本，请先删除数据集或改用其他名字")
        return dataset

    # 3. 定义所有样本
    examples = [
        # ========================================================
        # 单竞品样本（5 条）
        # ========================================================
        {
            "inputs": {
                "competitor": "Notion",
                "industry": "生产力工具",
                "domain": "software",
            },
            "outputs": {
                "expected_sections": [
                    "竞品概览", "核心功能", "定价", "用户评价",
                    "竞争格局", "SWOT", "结论"
                ],
                "min_sources": 10,
                "min_length": 1500,
            },
        },
        {
            "inputs": {
                "competitor": "Figma",
                "industry": "设计工具",
                "domain": "software",
            },
            "outputs": {
                "expected_sections": [
                    "竞品概览", "核心功能", "定价", "用户评价",
                    "竞争格局", "SWOT", "结论"
                ],
                "min_sources": 10,
                "min_length": 1500,
            },
        },
        {
            "inputs": {
                "competitor": "Linear",
                "industry": "项目管理",
                "domain": "software",
            },
            "outputs": {
                "expected_sections": [
                    "竞品概览", "核心功能", "定价", "用户评价",
                    "竞争格局", "SWOT", "结论"
                ],
                "min_sources": 10,
                "min_length": 1500,
            },
        },
        {
            "inputs": {
                "competitor": "Slack",
                "industry": "团队协作",
                "domain": "software",
            },
            "outputs": {
                "expected_sections": [
                    "竞品概览", "核心功能", "定价", "用户评价",
                    "竞争格局", "SWOT", "结论"
                ],
                "min_sources": 10,
                "min_length": 1500,
            },
        },
        {
            "inputs": {
                "competitor": "飞书",
                "industry": "办公协作",
                "domain": "software",
            },
            "outputs": {
                "expected_sections": [
                    "竞品概览", "核心功能", "定价", "用户评价",
                    "竞争格局", "SWOT", "结论"
                ],
                "min_sources": 10,
                "min_length": 1500,
            },
        },

        # ========================================================
        # 对比模式样本（2 条）
        # ========================================================
        {
            "inputs": {
                "competitors": ["Notion", "Figma"],
                "industry": "生产力工具",
                "domain": "software",
            },
            "outputs": {
                "expected_sections": [
                    "对比概览", "核心维度对比", "差异化分析",
                    "SWOT", "选型建议",
                ],
                "min_sources": 20,
                "min_length": 3000,
            },
        },
        {
            "inputs": {
                "competitors": ["Slack", "飞书"],
                "industry": "团队协作",
                "domain": "software",
            },
            "outputs": {
                "expected_sections": [
                    "对比概览", "核心维度对比", "差异化分析",
                    "SWOT", "选型建议",
                ],
                "min_sources": 20,
                "min_length": 3000,
            },
        },
    ]

    # 4. 批量创建样本
    for ex in examples:
        client.create_example(
            inputs=ex["inputs"],
            outputs=ex["outputs"],
            dataset_id=dataset.id,
        )

    print(f"✅ 创建了 {len(examples)} 条评估样本")
    print(f"   - 单竞品样本: 5 条")
    print(f"   - 对比模式样本: 2 条")
    return dataset


if __name__ == "__main__":
    create_or_get_dataset()