import asyncio
import json
import os
import csv
import pandas as pd
from openai import AsyncOpenAI
from tenacity import retry, wait_exponential, stop_after_attempt
from tqdm.asyncio import tqdm

# ==========================================
# 1. 核心配置区
# ==========================================
# 替换为你的大模型 API 服务地址。
# 如果是你本地用 vLLM/Ollama 部署的开源模型，通常是 "http://localhost:8000/v1"
API_BASE_URL = "https://api.deepseek.com/v1" 
API_KEY = "sk-91cd4950468741b4b2846713839b3a77"
MODEL_NAME = "deepseek-reasoner" # 或 "gpt-4o", "llama-3-70b"

INPUT_CSV = "raw_multilingual_data.csv"   # 需要标注的原始数据
OUTPUT_CSV = "annotated_data.csv"         # 标注后的输出文件
CONCURRENCY_LIMIT = 50                    # 最大并发请求数 (根据你的 API 速率调整)

# 确保我们的 6 大合规维度完全对齐
EXPECTED_KEYS = [
    "Hate_Speech", "Targeted_Harassment", "NSFW_Sexual", 
    "Violence_Incitement", "Dangerous_Ideology", "Profanity_Slang"
]

# ==========================================
# 2. 客户端与系统提示词初始化
# ==========================================
client = AsyncOpenAI(api_key=API_KEY, base_url=API_BASE_URL)
semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)

SYSTEM_PROMPT = """你是一个专业的全球多语言内容安全审核引擎。
请分析用户输入的文本，并严格按照以下 6 个维度进行二元打分（命中为 1.0，未命中为 0.0）。
维度定义：
- Hate_Speech: 针对种族、宗教、国籍等群体的仇恨与歧视。
- Targeted_Harassment: 针对具体个人的定向网暴或恶意辱骂。
- NSFW_Sexual: 色情、性暗示或违背意愿的性骚扰。
- Violence_Incitement: 明确的物理伤害威胁或煽动暴力。
- Dangerous_Ideology: 支持恐怖主义或极端分裂主义。
- Profanity_Slang: 包含粗俗脏话或冒犯性俚语。

你必须且只能返回一个合法的 JSON 对象，绝对不要输出任何其他解释性文字或 Markdown 标记。
输出格式示例：
{"Hate_Speech": 1.0, "Targeted_Harassment": 0.0, "NSFW_Sexual": 0.0, "Violence_Incitement": 0.0, "Dangerous_Ideology": 0.0, "Profanity_Slang": 1.0}"""

# ==========================================
# 3. 异步请求与容错逻辑
# ==========================================
# 使用 tenacity 实现指数退避重试：最多重试 5 次，间隔时间从 2 秒指数增加到 20 秒
@retry(wait=wait_exponential(multiplier=1, min=2, max=20), stop=stop_after_attempt(5))
async def annotate_single_text(text: str, index: int) -> dict:
    async with semaphore:
        try:
            response = await client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"输入文本：{text}"}
                ],
                temperature=0.0, # 必须设为 0，保证分类任务的确定性和一致性
                response_format={"type": "json_object"} # 强制 JSON 模式
            )
            
            raw_result = response.choices[0].message.content
            print(raw_result)
            parsed_json = json.loads(raw_result)
            
            # 校验大模型是否漏掉了某些标签
            if not all(key in parsed_json for key in EXPECTED_KEYS):
                 raise ValueError(f"JSON 字段不完整: {parsed_json}")
                 
            return {"index": index, "labels": parsed_json, "status": "success"}
            
        except Exception as e:
            # 抛出异常以触发 @retry
            raise RuntimeError(f"Index {index} 标注失败: {str(e)}")

# ==========================================
# 4. 主控流与断点续传机制
# ==========================================
async def main():
    print("🚀 启动自动化多语言数据标注流水线...")
    
    # 1. 加载原始数据
    if not os.path.exists(INPUT_CSV):
        # 如果没有测试文件，我们动态生成几条用于测试
        print("未找到输入文件，正在生成跨国测试用例...")
        df = pd.DataFrame({
            "text": [
                "I love this beautiful world!", # 正常
                "Maldita puta, te vamos a matar.", # 西语: 脏话+暴力威胁
                "Dasar anjing, orang Cina pulang sana!", # 印尼语: 粗口+种族仇恨
                "هؤلاء الكفار يجب أن يموتوا" # 阿拉伯语: 极端意识形态/仇恨
            ]
        })
        df.to_csv(INPUT_CSV, index=False,quoting=csv.QUOTE_MINIMAL)
    else:
        df = pd.read_csv(INPUT_CSV, on_bad_lines='warn', engine='python')

    # 2. 断点续传逻辑
    if os.path.exists(OUTPUT_CSV):
        out_df = pd.read_csv(OUTPUT_CSV)
        processed_indices = set(out_df['index'].tolist())
        print(f"📦 发现已有进度，跳过已处理的 {len(processed_indices)} 条数据...")
    else:
        out_df = pd.DataFrame(columns=['index', 'text'] + EXPECTED_KEYS + ['status'])
        processed_indices = set()

    # 3. 构建待处理任务队列
    tasks = []
    task_indices = []
    for index, row in df.iterrows():
        if index not in processed_indices:
            tasks.append(annotate_single_text(row['text'], index))
            task_indices.append(index)

    if not tasks:
        print("✅ 所有数据已标注完毕！")
        return

    print(f"⚙️ 开始并发处理 {len(tasks)} 条新数据 (最大并发: {CONCURRENCY_LIMIT})...")
    
    # 4. 执行并发并显示进度条
    # tqdm.gather 可以在终端漂亮地展示进度和预估剩余时间
    # results = await tqdm.gather(*tasks, return_exceptions=True)
    # 包装一个带进度条更新的辅助函数
    async def task_with_progress(task, pbar):
        try:
            return await task
        finally:
            pbar.update(1) # 无论成功还是失败，进度条推进一步

    # 使用标准的 tqdm 和原生的 asyncio.gather
    with tqdm(total=len(tasks), desc="标注进度") as pbar:
        wrapped_tasks = [task_with_progress(t, pbar) for t in tasks]
        # 使用原生 asyncio.gather，完美支持 return_exceptions=True，且返回结果顺序与输入一致
        results = await asyncio.gather(*wrapped_tasks, return_exceptions=True)

    # 5. 解析结果并增量保存
    new_rows = []
    for res in results:
        if isinstance(res, Exception):
            # 如果彻底失败（重试 5 次依然报错），记录错误状态，防止阻塞大盘
            # 这里需要从 Exception 对象中提取是哪一个 index 失败的比较麻烦
            # 在实际工程中，通常直接记录到 error.log 中
            print(f"❌ 严重错误: {res}")
            continue
            
        idx = res["index"]
        row_data = {
            "index": idx,
            "text": df.at[idx, 'text'],
            "status": res["status"]
        }
        # 将 6 个维度的分数打平写入字典
        for key in EXPECTED_KEYS:
            row_data[key] = float(res["labels"].get(key, 0.0))
            
        new_rows.append(row_data)

    # 追加写入 CSV
    if new_rows:
        new_df = pd.DataFrame(new_rows)
        if not os.path.exists(OUTPUT_CSV):
            new_df.to_csv(OUTPUT_CSV, index=False)
        else:
            new_df.to_csv(OUTPUT_CSV, mode='a', header=False, index=False)
            
    print(f"🎉 本轮标注完成！共成功处理 {len(new_rows)} 条数据，已保存至 {OUTPUT_CSV}。")

if __name__ == "__main__":
    # 解决 Windows 环境下 asyncio 可能报错的问题
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())