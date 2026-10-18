# 小程序 AI 会员助手（方案 1 落地）

生产级 Python 服务：FastAPI + SSE 流式问答 + 真实向量 RAG + 只读会员工具。

## 架构

```
小程序 -> *-api（鉴权，token 取 memberId，透传 X-Member-Id 请求头）
            -> 本服务 POST /chat（SSE）
                   ├─ RAG：sentence-transformers 多语言 embedding + FAISS 向量索引
                   ├─ 工具：预设只读工具（积分/券/订单），sqlite 以 mode=ro 打开
                   └─ 生成：OpenAI 兼容 LLM（环境变量配置，生产指向公司内部模型）
```

## 方案硬约束落实

1. **身份只从请求头取**：`X-Member-Id` 缺失返回 401；body 只有 question，无权指定身份。
2. **AI 全程只读**：sqlite 以 `mode=ro` 打开，写操作直接抛异常；代码无任何写路径。
3. **只能调预设工具**：`tools.TOOLS` 是封闭注册表，未知工具名直接拒绝；LLM 拿不到 raw SQL。
4. **非公开**：无有效会员头即 401。
5. **答不上转人工**：RAG 最高相似度低于阈值（默认 0.30）直接返回转人工话术。

## 本地运行

```bash
python3 -m pip install -r requirements.txt
python3 scripts/init_db.py        # 建样本会员库
python3 scripts/build_index.py    # 建向量索引（首次会下载 embedding 模型约 500MB）
export MEMBER_ASSISTANT_LLM_API_KEY=你的key
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

测试：

```bash
curl -N -X POST localhost:8001/chat \
  -H "Content-Type: application/json" \
  -H "X-Member-Id: M10001" \
  -d '{"question": "我的积分有多少？"}'
curl localhost:8001/healthz
pytest tests/
```

## Docker 部署

```bash
docker build -t member-assistant .
docker run -d --name member-assistant -p 8001:8001 \
  -e MEMBER_ASSISTANT_LLM_API_KEY=你的key \
  member-assistant
```

## 配置（环境变量，均可加 `MEMBER_ASSISTANT_` 前缀）

| 变量 | 说明 | 默认 |
|---|---|---|
| LLM_BASE_URL | OpenAI 兼容接口地址（生产指向内部模型） | https://opencode.ai/zen/v1 |
| LLM_API_KEY | 模型 key | 空 |
| LLM_MODEL | 模型名 | glm-5.3-flash-free |
| CONFIDENCE_THRESHOLD | RAG 置信度阈值，低于则转人工 | 0.30 |
| PORT | 服务端口 | 8001 |

## 加新知识文档

往 `data/kb/` 里放 `.md`，重新跑 `python3 scripts/build_index.py` 即可，无需改代码。
