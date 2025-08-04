from ..strategies.semantic_field_strategy import FieldProcessorManager


def map_result_to_format(source_data, target_fields):
    """
    通用字段映射接口

    Args:
        source_data: AIForge返回的原始数据（data）
        target_fields: 外部期望的字段格式列表，如["title", "content", "url", "pub_time"]

    Returns:
        映射后的结果，保持原有结构但data字段按目标格式映射

    Tips:
        # 两种形式的传参，第2种不指定要求，需要对输出进行映射
        # 1. search_query = f"搜索5条xx的新闻，搜索结果数据要求：title、abstract、url、pub_time字段"
        # 2. search_query = "搜索5条xx的新闻"

        results = AIForgeEngine(api_key=xxx)(search_query)

        # 因为没输出格式要求，这里需要获取到后进行映射
        # 即使指定也不一定能保证，所以最好固定进行映射
        data = map_result_to_format(
            results.get("data", []), ["title", "abstract", "url", "pub_time"]
        )
    """
    processor_manager = FieldProcessorManager()

    # 提取原始数据

    if not source_data:
        return source_data

    # 执行字段映射
    try:
        return processor_manager.process_field(source_data, target_fields)
    except Exception:
        return source_data
