# 由于运行中下载缓慢且可能由于网络原因失败，这里推荐预下载，单独执行即可

import os
from pathlib import Path
from huggingface_hub import snapshot_download


model_dir = "./src/aiforge/models/sentence_transformers/paraphrase-MiniLM-L6-v2"

model_path = snapshot_download(
    repo_id="sentence-transformers/paraphrase-MiniLM-L6-v2",
    local_dir=model_dir,
    allow_patterns=[
        "config.json",
        "tokenizer_config.json",
        "tokenizer.json",
        "vocab.txt",
        "model.safetensors",
    ],
)

keep_files = {
    "config.json",
    "tokenizer_config.json",
    "tokenizer.json",
    "vocab.txt",
    "model.safetensors",
}


# 遍历目录并删除非必要文件
for item in Path(model_dir).glob("*"):
    if item.is_file() and item.name not in keep_files:
        os.remove(item)
    elif item.is_dir():
        # 删除子目录
        for subitem in item.glob("*"):
            if subitem.is_file() and subitem.name not in keep_files:
                os.remove(subitem)
        # 删除空目录
        if not any(item.iterdir()):
            os.rmdir(item)

print(f"sentence-transformers下载到{model_path}完成")
