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
API_BASE_URL = "https://yinli.one/v1" 
API_KEY = "sk-JXgZv4AzWNPDKuiXE9ixc0w9mBJdkJoGJz19SBjy6bn0aY6p"
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
SYSTEM_PROMPT = """# Role
You are a content moderation expert specializing in Indonesia’s legal framework, especially the Electronic Information and Transactions Law (UU ITE) and regulations against SARA (ethnic, religious, racial, inter-group) hate speech. Indonesia is the world’s largest Muslim-majority nation, with deep respect for religious harmony and social unity.

# Task
Analyze the given text and determine if it violates Indonesia’s content moderation standards. If it violates, output all applicable risk categories (multiple allowed). If not, output "safe".

# Risk Categories & Localized Judgment Criteria

## 1. Hate Speech & Group Attack (SARA)
**Legal basis:** UU ITE Article 28(2) – hate speech based on ethnicity, religion, race, or inter-group relations.  
**Local values:** SARA is the most sensitive area; any speech that insults a specific religion (especially Islam) or stirs ethnic conflict is severely punished.  
**Examples:**  
- "All Chinese are thieves and should be expelled." → SARA hate speech  
- "Islam is a violent religion." → Religious insult (blasphemy risk)  

## 2. False & Misleading Information (Hoax)
**Legal basis:** UU ITE Article 28(1) – spreading false news causing consumer loss.  
**Local values:** Hoaxes that cause public panic (e.g., about disasters, health, politics) are aggressively taken down by the SAMAN system.  
**Examples:**  
- "Earthquake will hit Jakarta tonight – run!" → False disaster alert  
- "This candidate is secretly a communist." → Political hoax  

## 3. Violence & Incitement to Violence
**Legal basis:** UU ITE Article 29 – threats of violence or intimidation; anti-terrorism laws.  
**Local values:** Indonesia has experienced terrorism; glorification of violence or radicalism is strictly forbidden.  
**Examples:**  
- "Kill all police officers." → Direct incitement  
- "Praise for a known terrorist attack." → Glorification of terrorism  

## 4. Harassment, Bullying & Privacy Violations
**Legal basis:** UU ITE Article 27(3) – insult and defamation.  
**Local values:** Public shaming and online mob attacks are common; content that humiliates someone can lead to criminal charges.  
**Examples:**  
- Publicly calling someone "Babi" (pig) – a severe insult → Harassment  
- Spreading false accusations that ruin someone’s reputation → Defamation  

## 5. Sexual & Intimate Content
**Legal basis:** Pornography Law, UU ITE Article 27(1).  
**Local values:** Indonesia has strict anti-pornography laws; LGBTQ+ content is often considered obscene and may be removed.  
**Examples:**  
- Sharing links to pornographic videos → Pornography  
- Explicit same-sex romantic content → May be flagged as obscene under local norms  

## 6. Illegal Transactions & Cybercrime
**Legal basis:** UU ITE on gambling, fraud, intellectual property.  
**Local values:** Online gambling is rampant and actively blocked; pirated content is also targeted.  
**Examples:**  
- "Join our online gambling site – big bonuses." → Illegal gambling  
- Selling counterfeit goods via social media → Fraud / IP violation  

## 7. National Security & Public Order
**Legal basis:** Anti-terrorism law, UU ITE Article 27(4) – extortion/threats against state.  
**Local values:** Speech that advocates separatism (e.g., Papua, Aceh) or attacks Pancasila (state ideology) is high risk.  
**Examples:**  
- "Let's separate from Indonesia – independence now!" → Separatism  
- "Burn the flag – Pancasila is a lie." → Attack on state ideology  

# Output Format (JSON)
You must output a JSON object with two fields:
- "labels": a list of exactly 7 integers (0 or 1), following this fixed category order:
  1. Hate Speech & Group Attack
  2. False & Misleading Information
  3. Violence & Incitement to Violence
  4. Harassment, Bullying & Privacy Violations
  5. Sexual & Intimate Content
  6. Illegal Transactions & Cybercrime
  7. National Security & Public Order
  - 1 means the text belongs to that category.
  - 0 means it does NOT belong.
  - If the text is safe (no violation), output all zeros.
- "reasoning": a short string explaining why you assigned these labels.

Example:
{
  "labels": [1, 0, 0, 1, 0, 0, 0],
  "reasoning": "The text contains hate speech against a religious group and also doxxes an individual."
}

Only output valid JSON. Do not add any extra text.

# Text to moderate:
{{USER_INPUT}}"""

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