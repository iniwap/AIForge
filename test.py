from huggingface_hub import snapshot_download

# 下载模型到指定目录
model_path = snapshot_download(
    repo_id="sentence-transformers/paraphrase-MiniLM-L6-v2",
    local_dir="./src/aiforge/models/sentence_transformers/paraphrase-MiniLM-L6-v2",
    local_dir_use_symlinks=False,
)
print(f"模型已下载到: {model_path}")
