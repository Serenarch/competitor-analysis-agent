from langchain_text_splitters import MarkdownHeaderTextSplitter

# 定义分块规则：按一级、二级、三级标题切分
HEADERS_TO_SPLIT_ON = [
    ("#", "h1"),
    ("##", "h2"),
    ("###", "h3"),
]

# 初始化分块器，保留标题内容以便检索
markdown_splitter = MarkdownHeaderTextSplitter(
    headers_to_split_on=HEADERS_TO_SPLIT_ON,
    strip_headers=False  # 保留标题，让每个 chunk 都有上下文
)

def split_report(report_text: str) -> list:
    """将 Markdown 报告切分为带元数据的块"""
    return markdown_splitter.split_text(report_text)