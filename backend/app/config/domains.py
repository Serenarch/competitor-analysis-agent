"""领域配置：不同领域的分析维度和报告结构"""
from typing import Dict


DOMAIN_TEMPLATES: Dict[str, Dict] = {
    "software": {
        "display_name": "软件产品",
        "focus_areas": ["产品定位", "核心功能", "定价策略", "用户评价", "竞争格局"],
        "report_sections": [
            "竞品概览",
            "核心功能分析",
            "定价策略",
            "用户评价",
            "竞争格局",
            "SWOT 分析",
            "结论与建议",
        ],
        "planner_hint": (
            "这是一个软件/SaaS 产品，关注功能、定价、用户评价、竞争格局。"
            "搜索时应关注官网、G2、Capterra、技术评测博客等。"
        ),
    },
    "product": {
        "display_name": "实体商品",
        "focus_areas": ["产品参数", "价格区间", "用户口碑", "销售渠道", "品牌定位"],
        "report_sections": [
            "产品概览",
            "核心参数",
            "价格分析",
            "用户口碑",
            "渠道分析",
            "SWOT 分析",
            "选购建议",
        ],
        "planner_hint": (
            "这是一个实体商品（如手机、耳机、家电），关注硬件参数、价格、"
            "电商平台口碑、销售渠道、品牌定位。搜索时应关注京东、天猫、亚马逊等电商数据，"
            "以及专业评测网站（如 RTINGS、What Hi-Fi）。"
        ),
    },
    "service": {
        "display_name": "服务",
        "focus_areas": ["服务内容", "收费模式", "客户反馈", "服务范围", "服务质量"],
        "report_sections": [
            "服务概览",
            "服务内容",
            "收费模式",
            "客户反馈",
            "竞争格局",
            "SWOT 分析",
            "建议",
        ],
        "planner_hint": (
            "这是一个服务类产品（如在线课程、咨询、订阅制服务），"
            "关注服务内容、收费模式、客户反馈、服务范围、服务质量。"
        ),
    },
}


def get_domain_template(domain: str) -> Dict:
    """获取领域模板，未指定时默认返回软件领域"""
    return DOMAIN_TEMPLATES.get(domain, DOMAIN_TEMPLATES["software"])


def list_domains() -> list:
    """列出所有支持的领域"""
    return [
        {"key": k, "name": v["display_name"]}
        for k, v in DOMAIN_TEMPLATES.items()
    ]