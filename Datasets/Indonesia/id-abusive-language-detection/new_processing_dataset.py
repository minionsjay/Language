"""
使用大模型 API 对 CSV 中的文本进行多标签分类标注（7 个类别）。
支持异步并发、断点续传、批量写入。
所有配置请在 main() 函数中修改。
"""
import argparse

import asyncio
import json
import os
import sys
from typing import List, Dict, Any

import pandas as pd
from openai import AsyncOpenAI
from tqdm.asyncio import tqdm


# ==================== 辅助函数（无需修改） ====================
def get_system_prompt(country: str) -> str:
    """根据国家返回对应的系统提示词（7 分类，输出 labels 向量）"""

#     base_prompt = """You are a content moderation expert. Analyze the given text and determine which of the following 7 categories it violates (multiple allowed). Output a JSON with "labels" (list of 7 integers, 0/1) and "reasoning" (short explanation).

# Fixed category order:
# 1. Hate Speech & Group Attack
# 2. False & Misleading Information
# 3. Violence & Incitement to Violence
# 4. Harassment, Bullying & Privacy Violations
# 5. Sexual & Intimate Content
# 6. Illegal Transactions & Cybercrime
# 7. National Security & Public Order

# Output format example:
# {"labels": [1,0,0,1,0,0,0], "reasoning": "The text contains hate speech and doxxing."}
# If no violation, output all zeros: {"labels": [0,0,0,0,0,0,0], "reasoning": "Safe content."}
# Only output valid JSON, no extra text.
# """
#     if country == "Singapore":
#         additional = """
# Special focus for Singapore (OSRA Act): 
# - Hate speech includes incitement of enmity based on race/religion.
# - Harassment includes doxxing, online stalking, impersonation, defamation.
# - False information that harms public health/safety is critical.
# - Violence incitement is strictly forbidden.
# """
#     elif country == "Indonesia":
#         additional = """
# Special focus for Indonesia (UU ITE, SARA):
# - Hate speech targeting ethnicity, religion, race, inter-group (SARA) is most sensitive.
# - False information (hoax) that causes public panic is aggressively removed.
# - Pornography and LGBTQ+ content may be considered obscene.
# - Gambling promotion is illegal.
# """
#     elif country == "Thailand":
#         additional = """
# Special focus for Thailand (CCA, Lèse Majesté):
# - Any negative comment about the monarchy (king, queen, heir) is a serious crime (Article 112).
# - False information that harms national security or causes public panic is prohibited.
# - Obscene content and gambling are illegal.
# - Criticism of military or government may threaten public order.
# """
#     else:
#         additional = ""
#     return base_prompt + additional
    prompt = """# Role
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
    return prompt


def load_progress(output_csv: str) -> int:
    """读取已标注的行数（假设输出文件已存在且保留了原始顺序）"""
    if os.path.exists(output_csv):
        try:
            df_done = pd.read_csv(output_csv)
            return len(df_done)
        except Exception:
            return 0
    return 0


def save_batch(df_original: pd.DataFrame, start_idx: int, end_idx: int, results: List[Dict], output_csv: str):
    """
    将一批标注结果合并到原始数据，并写入文件。
    如果文件已存在则追加，否则新建。
    结果中包含原始所有列 + labels + reasoning。
    """
    batch_original = df_original.iloc[start_idx:end_idx].copy()
    batch_original["labels"] = [r.get("labels", "[0,0,0,0,0,0,0]") for r in results]
    batch_original["reasoning"] = [r.get("reasoning", "") for r in results]
    
    if not os.path.exists(output_csv) or start_idx == 0:
        batch_original.to_csv(output_csv, index=False, mode='w')
    else:
        batch_original.to_csv(output_csv, index=False, mode='a', header=False)


async def call_api(
    client: AsyncOpenAI,
    system_prompt: str,
    user_text: str,
    semaphore: asyncio.Semaphore,
    model_name: str,
    max_retries: int = 3,        # 改为整数，默认3
    retry_delay: float = 2.0
) -> Dict[str, Any]:
    """单次 API 调用，带重试和并发控制"""
    async with semaphore:
        for attempt in range(max_retries):   # 现在 max_retries 是整数，没问题
            try:
                response = await client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_text}
                    ],
                    temperature=0.0,
                    max_tokens=500,
                    response_format={"type": "json_object"}
                )
                content = response.choices[0].message.content
                parsed = json.loads(content)
                if "labels" not in parsed:
                    parsed["labels"] = [0]*7
                if "reasoning" not in parsed:
                    parsed["reasoning"] = ""
                if len(parsed["labels"]) != 7:
                    parsed["labels"] = [0]*7
                parsed["labels"] = [int(x) for x in parsed["labels"]]
                return parsed
            except Exception as e:
                if attempt == max_retries - 1:
                    print(f"API call failed after {max_retries} attempts: {e}")
                    return {"labels": [0]*7, "reasoning": f"API error: {str(e)}"}
                await asyncio.sleep(retry_delay * (attempt + 1))
        return {"labels": [0]*7, "reasoning": "Unknown error"}


async def process_batch(
    client: AsyncOpenAI,
    df: pd.DataFrame,
    start_idx: int,
    end_idx: int,
    system_prompt: str,
    semaphore: asyncio.Semaphore,
    text_col: str,
    model_name: str,
    max_retries: int = 3,
    retry_delay: float = 2.0
) -> List[Dict]:
    """处理一批文本（异步并发）"""
    tasks = []
    for idx in range(start_idx, end_idx):
        text = str(df.iloc[idx][text_col])
        if not text or text == "nan":
            text = ""
        # 使用闭包传递参数
        async def single_call(t=text):
            return await call_api(
                client, system_prompt, t, semaphore,
                model_name=model_name,
                max_retries=max_retries,
                retry_delay=retry_delay
            )
        tasks.append(single_call())
    results = await tqdm.gather(*tasks, desc=f"Processing rows {start_idx}-{end_idx-1}")
    return results

# ==================== 主函数 ====================
# async def main():
#     # ========== 在这里修改你的配置 ==========
#     # 文件路径
#     INPUT_CSV = "new_dataset.csv"           # 原始数据文件
#     OUTPUT_CSV = f"output_labeled.csv" # 标注结果文件（自动创建/续写）
    
#     # 数据列名
#     TEXT_COL = "Tweet"                 # 待标注的文本所在的列名
    
#     # 大模型 API 配置
#     # API_BASE = "https://yinli.one/v1"
#     # API_KEY = "sk-JXgZv4AzWNPDKuiXE9ixc0w9mBJdkJoGJz19SBjy6bn0aY6p"
#     # MODEL_NAME = "o3-mini-low"

#     ## 小米
#     API_KEY="sk-c4s1udb9y702t14eb05ijwfcurjfstaqlywlioxoo1rpp6ua"
#     API_BASE="https://api.xiaomimimo.com/v1"
#     MODEL_NAME="mimo-v2-flash"
    
#     # 请求参数
#     MAX_CONCURRENT = 50               # 最大并发请求数
#     BATCH_SIZE = 20                   # 每处理多少条写入一次文件
    
#     # 国家/地区（用于提示词，可选 "Singapore", "Indonesia", "Thailand"）
#     COUNTRY = "Indonesia"
    
#     # 可选：完全自定义系统提示词（如果不为空，则忽略 COUNTRY）
#     CUSTOM_SYSTEM_PROMPT = None
#     # ======================================
    
#     # 读取原始 CSV
#     if not os.path.exists(INPUT_CSV):
#         print(f"Input file not found: {INPUT_CSV}")
#         sys.exit(1)
#     df = pd.read_csv(INPUT_CSV)
#     total_rows = len(df)
#     print(f"Total rows: {total_rows}")
    
#     # 确定已处理行数
#     processed = load_progress(OUTPUT_CSV)
#     if processed >= total_rows:
#         print("All rows already labeled. Exiting.")
#         return
#     print(f"Resuming from row {processed} (already labeled {processed} rows)")
    
#     # 初始化 OpenAI 客户端
#     client = AsyncOpenAI(base_url=API_BASE, api_key=API_KEY)
    
#     # 确定系统提示词
#     if CUSTOM_SYSTEM_PROMPT:
#         system_prompt = CUSTOM_SYSTEM_PROMPT
#     else:
#         system_prompt = get_system_prompt(COUNTRY)
#     print("Using system prompt:\n", system_prompt[:200], "...\n")
    
#     semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    
#     # 分批处理
#     for batch_start in range(processed, total_rows, BATCH_SIZE):
#         batch_end = min(batch_start + BATCH_SIZE, total_rows)
#         print(f"\nProcessing batch {batch_start}-{batch_end-1}...")
#         results = await process_batch(
#             client, df, batch_start, batch_end, system_prompt, semaphore,
#             text_col=TEXT_COL, model_name=MODEL_NAME
#         )
#         save_batch(df, batch_start, batch_end, results, OUTPUT_CSV)
#         print(f"Batch saved to {OUTPUT_CSV}")
    
#     print(f"\nAll done. Labeled file saved to {OUTPUT_CSV}")


# if __name__ == "__main__":
#     asyncio.run(main())

# ==================== 修改后的主函数 ====================
async def main(args):
    # 输入文件校验
    if not os.path.exists(args.input):
        print(f"Input file not found: {args.input}")
        sys.exit(1)
    
    # 自动生成输出文件名：输入文件名_模型名_labeled.csv
    if args.output:
        output_csv = args.output
    else:
        base_name = os.path.splitext(os.path.basename(args.input))[0]
        safe_model_name = args.model.replace("/", "_").replace("\\", "_")
        output_csv = f"{base_name}_{safe_model_name}_labeled.csv"
    
    # 读取数据
    df = pd.read_csv(args.input)
    total_rows = len(df)
    print(f"Total rows: {total_rows}")
    
    # 断点续传
    processed = load_progress(output_csv)
    if processed >= total_rows:
        print("All rows already labeled. Exiting.")
        return
    print(f"Resuming from row {processed} (already labeled {processed} rows)")
    
    # 初始化客户端
    client = AsyncOpenAI(base_url=args.api_base, api_key=args.api_key)
    
    # 系统提示词
    if args.custom_prompt:
        system_prompt = args.custom_prompt
    else:
        system_prompt = get_system_prompt(args.country)
    print("Using system prompt:\n", system_prompt[:200], "...\n")
    
    semaphore = asyncio.Semaphore(args.max_concurrent)
    
    # 分批处理
    for batch_start in range(processed, total_rows, args.batch_size):
        batch_end = min(batch_start + args.batch_size, total_rows)
        print(f"\nProcessing batch {batch_start}-{batch_end-1}...")
        results = await process_batch(
            client, df, batch_start, batch_end, system_prompt, semaphore,
            text_col=args.text_col, model_name=args.model
        )
        save_batch(df, batch_start, batch_end, results, output_csv)
        print(f"Batch saved to {output_csv}")
    
    print(f"\nAll done. Labeled file saved to {output_csv}")

if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(description="Batch labeling using LLM API")
    parser.add_argument("--input", "-i", required=True, help="Input CSV file path")
    parser.add_argument("--output", "-o", default=None, help="Output CSV file path (auto-generated if not given)")
    parser.add_argument("--text-col", default="Tweet", help="Column name containing text to label")
    parser.add_argument("--model", "-m", default="mimo-v2-flash", help="Model name")
    parser.add_argument("--api-base", default="https://api.xiaomimimo.com/v1", help="API base URL")
    parser.add_argument("--api-key", default="sk-c4s1udb9y702t14eb05ijwfcurjfstaqlywlioxoo1rpp6ua", help="API key")
    parser.add_argument("--max-concurrent", type=int, default=50, help="Max concurrent requests")
    parser.add_argument("--batch-size", type=int, default=20, help="Batch size for saving")
    parser.add_argument("--country", default="Indonesia", help="Country for default prompt (Singapore/Indonesia/Thailand)")
    parser.add_argument("--custom-prompt", default=None, help="Fully custom system prompt (overrides --country)")
    
    args = parser.parse_args()
    asyncio.run(main(args))