We cover eight languages (Arabic, English, French, German, Indonesian, Portuguese, Spanish, and Turkish) and four countries where English is the main language on Twitter (United States, India, Nigeria, Kenya).
我们覆盖八种语言（阿拉伯语、英语、法语、德语、印尼语、葡萄牙语、西班牙语和土耳其语），以及四个以英语为推特主要语言的国家（美国、印度、尼日利亚、肯尼亚）。

Column	Description
tweet_id	Unique identifier of the tweet
推文的唯一标识符
class_clean	Cleaned class label: 0 = neutral, 1 = offensive, 2 = hateful (includes political hate)
清理过的类别标签：0 = 中立，1 = 冒犯，2 = 仇恨（含政治仇恨）
twitter_hate	Binary flag for Twitter’s own hate definition (0 = no, 1 = hate; excludes political hate)
推特自身仇恨定义的二进制标志（0 = 否，1 = 仇恨; 排除政治仇恨 ）
violent_hate	Whether hate is violent (incitement, threat, or glorification of violence)
仇恨是否是暴力的（煽动、威胁或美化暴力）
target_majority	Raw target group as provided by annotators
标注符提供的原始目标组
target_category	General category of the target (e.g., religion, gender, ethnicity)
目标的一般类别（例如，宗教、性别、族裔）
total_engagement	Sum of replies, retweets, quotes, and likes within 10 minutes of posting
发帖后10分钟内回复、转发、引用和点赞的总和
weighted  加权	1 if tweet is from engagement-weighted sample, 0 if from regular random sample
如果推文来自互动加权样本，则为 1;如果来自常规随机样本，则为 0
lang_country_hateday	Language or country code for the dataset partition
数据集分区的语言或国家代码
