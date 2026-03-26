import pandas as pd
import csv

# 定义文件配置列表
# 每个配置是一个字典，包含：
#   - path: 文件路径
#   - sep: 分隔符（如 ',' 或 '\t'），默认为 ','
#   - tweet_column: 推文所在的列名，默认为 'Tweet'（如果文件没有表头，需额外处理）
#   - header: 是否有表头，默认为 0（第一行是列名），若无表头则设为 None
#   - encoding_try: 可自定义尝试的编码顺序（可选）
file_configs = [
    {   
        ## 印尼印尼语辱骂性语言的数据集id-abusive-language-detection,2016条
        "path": "/home/ninini/Dataset-LLM/Datasets/Indonesia/id-abusive-language-detection/re_dataset_three_labels.csv",
        "sep": ",",
        "tweet_column": "Tweet",
        "header": 0
    },
    {   # 印尼语仇恨言论检测数据集,该数据集包含 713 条印尼语推文
        "path": "/home/ninini/Dataset-LLM/Datasets/Indonesia/id-hatespeech-detection/IDHSD_RIO_unbalanced_713_2017.txt",
        "sep": "\t",
        "tweet_column": "Tweet",
        "header": 0
    },
    {
        #13169条
        "path": "/home/ninini/Dataset-LLM/Datasets/Indonesia/id-multi-label-hate-speech-and-abusive-language-detection/re_dataset.csv",
        "sep": ",",
        "tweet_column": "Tweet",
        "header": 0
    },
    {
        #14306条
        "path": "/home/ninini/Dataset-LLM/Datasets/Indonesia/indonesian-hate-speech-superset/in_hf.csv",
        "sep": ",",
        "tweet_column": "text",
        "header": 0
    },
    # 您可以继续添加更多文件，例如：
    {
        # 7597条
        "path": "/home/ninini/Dataset-LLM/Datasets/Thailand/HateThaiSent/HateThaiSent.csv",
        "sep": ",",
        "tweet_column": "Message",
        "header": 0
    },
    {
        # 45000
        "path": "/home/ninini/Dataset-LLM/HateDay/split_by_country/en.csv",
        "sep": ",",
        "tweet_column": "text",
        "header": 0
    },
    {
        # 45000
        "path": "/home/ninini/Dataset-LLM/HateDay/split_by_country/in.csv",
        "sep": ",",
        "tweet_column": "text",
        "header": 0
    },
    {
        # 45000
        "path": "/home/ninini/Dataset-LLM/HateDay/split_by_country/US.csv",
        "sep": ",",
        "tweet_column": "text",
        "header": 0
    },
    {
        # 132
        "path": "/home/ninini/Dataset-LLM/Datasets/Singapore/Rabakbench/rabakbench_en.csv",
        "sep": ",",
        "tweet_column": "text",
        "header": 0
    },
    {
        # 132
        "path": "/home/ninini/Dataset-LLM/Datasets/Singapore/Rabakbench/rabakbench_ms.csv",
        "sep": ",",
        "tweet_column": "text",
        "header": 0
    },
    {   # 132
        "path": "/home/ninini/Dataset-LLM/Datasets/Singapore/Rabakbench/rabakbench_ta.csv",
        "sep": ",",
        "tweet_column": "text",
        "header": 0
    },
    {
        # 132
        "path": "/home/ninini/Dataset-LLM/Datasets/Singapore/Rabakbench/rabakbench_zh.csv",
        "sep": ",",
        "tweet_column": "text",
        "header": 0
    }
]

def read_file_with_fallback(file_config):
    """
    根据配置尝试多种编码读取文件，返回DataFrame
    """
    file_path = file_config["path"]
    sep = file_config.get("sep", ",")
    header = file_config.get("header", 0)  # 默认第一行为列名
    encoding_list = file_config.get("encoding_try", ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252'])
    
    for enc in encoding_list:
        try:
            df = pd.read_csv(file_path, sep=sep, header=header, encoding=enc)
            print(f"  ✓ 使用编码 {enc} 成功读取 {file_path}")
            return df
        except UnicodeDecodeError:
            continue
        except Exception as e:
            print(f"  ✗ 使用编码 {enc} 读取失败: {e}")
            continue
    # 如果所有编码都失败，使用 latin-1 强制读取（忽略错误）
    print(f"  ⚠ 所有编码均失败，使用 latin-1 强制读取（可能含乱码）")
    return pd.read_csv(file_path, sep=sep, header=header, encoding='latin-1')

def extract_tweets(df, tweet_column):
    """从DataFrame中提取推文列，去空，返回列表"""
    if tweet_column in df.columns:
        tweets = df[tweet_column].dropna().tolist()
        print(f"  提取到 {len(tweets)} 条推文")
        return tweets
    else:
        print(f"  ✗ 未找到列 '{tweet_column}'，实际列名: {df.columns.tolist()}")
        return []

def main():
    all_tweets = []
    for idx, config in enumerate(file_configs, 1):
        print(f"\n处理文件 {idx}: {config['path']}")
        df = read_file_with_fallback(config)
        tweets = extract_tweets(df, config["tweet_column"])
        all_tweets.extend(tweets)
    
    # 汇总保存
    output_df = pd.DataFrame({'tweet': all_tweets})
    output_file = "test_all_tweets_summary.csv"
    output_df.to_csv(output_file, index=False, encoding='utf-8', quoting=csv.QUOTE_MINIMAL)
    print(f"\n✓ 总计提取 {len(all_tweets)} 条推文，已保存至 {output_file}")
    print("CSV 已采用标准转义方式：包含逗号或引号的文本将被自动用双引号括起。")
    print("\n前5条预览：")
    print(output_df.head())

if __name__ == "__main__":
    main()