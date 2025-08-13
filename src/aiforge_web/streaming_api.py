import json
from typing import Dict, Any
import asyncio

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from .streaming_execution_manager import StreamingExecutionManager


def add_streaming_routes(app: FastAPI, forge_components: Dict[str, Any]):
    """添加流式路由"""

    streaming_manager = StreamingExecutionManager(forge_components)

    @app.post("/api/process/stream")
    async def process_instruction_stream(request: Request):
        """流式处理指令"""
        try:
            data = await request.json()
            raw_input = data.get("instruction", "")
            context_data = data.get("context", {})

            if not raw_input:
                return {"error": "指令不能为空"}

            # 返回流式响应
            return StreamingResponse(
                streaming_manager.execute_with_streaming(raw_input, "web", context_data),
                media_type="text/plain",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "Access-Control-Allow-Origin": "*",
                },
            )

        except Exception as e:
            return {"error": f"处理请求时出错: {str(e)}"}

    @app.get("/api/process/stream/test")
    async def test_stream():
        """测试流式端点"""

        async def generate_test():
            for i in range(10):
                yield f"data: {json.dumps({'type': 'progress', 'message': f'测试消息 {i+1}'})}\\n\\n"
                await asyncio.sleep(1)
            yield f"data: {json.dumps({'type': 'complete'})}\\n\\n"

        return StreamingResponse(generate_test(), media_type="text/plain")
