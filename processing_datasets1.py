import asyncio
import json
import os
import csv
import pandas as pd
from openai import AsyncOpenAI
from tenacity import retry, wait_exponential, stop_after_attempt
from tqdm import tqdm

# ==========================================
# 1. 核心配置区
# ==========================================
API_BASE_URL = "https://api.deepseek.com/v1" 
API_KEY = "sk-44ef59c0fe4e47e992fb4e4d985efe3f"
Qianwen_api_key="sk-35805b6e284846f691c01e1b4caf4759"
Qianwen_base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
Qianwen_model="qwen-plus-2025-07-28"

Xiaomi_api_key="sk-c4s1udb9y702t14eb05ijwfcurjfstaqlywlioxoo1rpp6ua"
Xiaomi_base_url="https://api.xiaomimimo.com/v1"
Xiaomi_model="mimo-v2-flash"

# 【修改点 1】切换为 deepseek-chat
MODEL_NAME = "deepseek-chat" 

INPUT_CSV = "raw_multilingual_data.csv"          # 原始数据
OUTPUT_CSV = "new_annotated_data.csv"         # 标注后的打分数据表
OUTPUT_LEXICON_CSV = "extracted_lexicon.csv"  # 提取的敏感词记录表

CONCURRENCY_LIMIT = 50      # 最大并发请求数
BATCH_SAVE_SIZE = 20        # 每处理 20 条强制存盘一次

EXPECTED_KEYS = [
    "Hate_Speech", "Targeted_Harassment", "NSFW_Sexual", 
    "Violence_Incitement", "Dangerous_Ideology", "Profanity_Slang"
]

client = AsyncOpenAI(api_key=Xiaomi_api_key, base_url=Xiaomi_base_url)
semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)

# ==========================================
# 2. 合并任务的 System Prompt
# ==========================================
# (注意：使用 JSON 模式时，Prompt 中必须包含 "JSON" 字眼，这里已经满足)
SYSTEM_PROMPT = """你是一个专业的全球多语言内容安全审核引擎。
你需要同时完成【违规打分】和【敏感词提取】两个任务。

【任务 1：违规打分】
严格按照以下 6 个维度进行二元打分（命中为 1.0，未命中为 0.0）：
- Hate_Speech: 针对种族、宗教、国籍等群体的仇恨与歧视。
- Targeted_Harassment: 针对具体个人的定向网暴或恶意辱骂。
- NSFW_Sexual: 色情、性暗示或违背意愿的性骚扰。
- Violence_Incitement: 明确的物理伤害威胁或煽动暴力。
- Dangerous_Ideology: 支持恐怖主义或极端分裂主义。
- Profanity_Slang: 包含粗俗脏话或冒犯性俚语。

【任务 2：敏感词提取】
如果文本违规，请提取出导致违规的核心“敏感词组（可以是两个或两个以上
不同词组成的词组，用于过滤违规内容，用&连接）/黑话”，并将其归入以下【8个一级分类】之一：
涉敏、涉政、未成年、价值观、宗教、低俗色情、暴力恐怖、违法。
(如果没有敏感词，提取列表为空 []。)

【输出格式要求】
必须且只能返回合法的 JSON 对象。请严格仿照以下格式：
{
  "Hate_Speech": 1.0,
  "Targeted_Harassment": 0.0,
  "NSFW_Sexual": 0.0,
  "Violence_Incitement": 0.0,
  "Dangerous_Ideology": 0.0,
  "Profanity_Slang": 1.0,
  "extracted_items": [
    {"word": "提取出的脏话或黑话", "category": "低俗色情"}
  ]
}"""

# ==========================================
# 3. 异步请求与 JSON 解析
# ==========================================
@retry(wait=wait_exponential(multiplier=1, min=2, max=20), stop=stop_after_attempt(5))
async def annotate_single_text(text: str, index: int) -> dict:
    async with semaphore:
        try:
            response = await client.chat.completions.create(
                model=Xiaomi_model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"输入文本：{text}"}
                ],
                # 【修改点 2】恢复 temperature 和 response_format
                temperature=0.0,  
                response_format={"type": "json_object"} 
            )
            
            # 【修改点 3】由于强制了 JSON 模式，直接 loads 即可，不再需要复杂的正则
            raw_result = response.choices[0].message.content
            parsed_json = json.loads(raw_result)
            
            # 校验打分字段完整性
            if not all(key in parsed_json for key in EXPECTED_KEYS):
                 raise ValueError(f"JSON 缺少核心打分字段: {parsed_json}")
                 
            # 确保提取列表存在
            if "extracted_items" not in parsed_json:
                 parsed_json["extracted_items"] = []
                 
            return {"index": index, "labels": parsed_json, "status": "success"}
            
        except Exception as e:
            raise RuntimeError(f"Index {index} 处理失败: {str(e)}")

# ==========================================
# 4. 辅助函数：微批次安全落盘
# ==========================================
def save_batch_to_disk(results, df):
    new_rows = []
    lexicon_rows = []
    
    for res in results:
        if isinstance(res, Exception):
            continue
            
        idx = res["index"]
        labels = res["labels"]
        
        # 1. 组装主表数据 (打分)
        row_data = {
            "index": idx,
            "text": df.at[idx, 'text'],
            "status": res["status"]
        }
        for key in EXPECTED_KEYS:
            row_data[key] = float(labels.get(key, 0.0))
        new_rows.append(row_data)
        
        # 2. 组装词库表数据 (敏感词)
        for item in labels.get("extracted_items", []):
            word = str(item.get("word", "")).strip()
            category = str(item.get("category", "")).strip()
            if word and category:
                lexicon_rows.append({
                    "source_index": idx,
                    "word": word.lower(),
                    "category": category
                })

    # 追加写入主打分表
    if new_rows:
        new_df = pd.DataFrame(new_rows)
        write_header = not os.path.exists(OUTPUT_CSV)
        new_df.to_csv(OUTPUT_CSV, mode='a', index=False, header=write_header, quoting=csv.QUOTE_MINIMAL)

    # 追加写入敏感词库表
    if lexicon_rows:
        lexicon_df = pd.DataFrame(lexicon_rows)
        write_lexicon_header = not os.path.exists(OUTPUT_LEXICON_CSV)
        lexicon_df.to_csv(OUTPUT_LEXICON_CSV, mode='a', index=False, header=write_lexicon_header, encoding='utf-8-sig', quoting=csv.QUOTE_MINIMAL)

# ==========================================
# 5. 主控流与微批次调度引擎
# ==========================================
async def main():
    print(f"🚀 启动多任务自动流水线 (基于 {Xiaomi_model})...")
    
    # --- 1. 数据加载 ---
    if not os.path.exists(INPUT_CSV):
        print("未找到输入文件，正在生成测试用例...")
        df = pd.DataFrame({
            "text": [
                "I love this beautiful world!", 
                "Maldita puta, te vamos a matar.", 
                "Dasar anjing, orang Cina pulang sana!"
            ]
        })
        df.to_csv(INPUT_CSV, index=False, quoting=csv.QUOTE_MINIMAL)
    else:
        df = pd.read_csv(INPUT_CSV, on_bad_lines='warn', engine='python')

    # --- 2. 严格断点续传检测 ---
    processed_indices = set()
    if os.path.exists(OUTPUT_CSV):
        out_df = pd.read_csv(OUTPUT_CSV)
        if 'index' in out_df.columns:
            processed_indices = set(out_df['index'].tolist())
        print(f"📦 发现断点记录，跳过已处理的 {len(processed_indices)} 条数据...")

    unprocessed_df = df[~df.index.isin(processed_indices)]
    
    if unprocessed_df.empty:
        print("✅ 所有数据已处理完毕！")
        return

    print(f"⚙️ 剩余 {len(unprocessed_df)} 条任务，开始并发处理 (并发: {CONCURRENCY_LIMIT}, 每 {BATCH_SAVE_SIZE} 条存盘一次)...")
    
    # --- 3. 微批次切分与执行 ---
    all_indices = unprocessed_df.index.tolist()
    pbar = tqdm(total=len(all_indices), desc="总进度")
    
    for i in range(0, len(all_indices), BATCH_SAVE_SIZE):
        batch_indices = all_indices[i : i + BATCH_SAVE_SIZE]
        
        batch_tasks = []
        for idx in batch_indices:
            text = df.at[idx, 'text']
            batch_tasks.append(annotate_single_text(text, idx))
            
        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
        
        # 立刻保存到硬盘
        save_batch_to_disk(batch_results, df)
        
        for res in batch_results:
            if isinstance(res, Exception):
                print(f"\n❌ [异常拦截] {res}")
                
        pbar.update(len(batch_indices))

    pbar.close()
    print(f"\n🎉 运行结束！")
    print(f"✔️ 打分结果已增量保存至: {OUTPUT_CSV}")
    print(f"✔️ 敏感词日志已增量保存至: {OUTPUT_LEXICON_CSV}")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())