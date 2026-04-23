Spanish Hate Speech Superset
西班牙语仇恨言论超级套装
This dataset is a superset (N=29,855) of posts annotated as hateful or not. It results from the preprocessing and merge of all available Spanish hate speech datasets in April 2024. These datasets were identified through a systematic survey of hate speech datasets conducted in early 2024. We only kept datasets that:
该数据集是注释为仇恨或非仇恨的帖子的超集（N=29,855）。该数据源自 2024 年 4 月对所有可用的西班牙语仇恨言论数据集的预处理和合并。这些数据集是通过 2024 年初对仇恨言论数据集进行的系统调查确定的。我们只保留了以下数据集：

are documented  有文献记载
are publicly available or could be retrieved with the Twitter API
公开获取或可通过 Twitter API 检索
focus on hate speech, defined broadly as "any kind of communication in speech, writing or behavior, that attacks or uses pejorative or discriminatory language with reference to a person or a group on the basis of who they are, in other words, based on their religion, ethnicity, nationality, race, color, descent, gender or other identity factor" (UN, 2019)
重点关注仇恨言论，广义上定义为“任何形式的言论、书写或行为中的交流，基于个人或群体的身份，换言之，基于其宗教、族裔、国籍、种族、肤色、血统、性别或其他身份因素，攻击或使用贬义或歧视性语言”（联合国， 2019)
The survey procedure is further detailed in our survey paper.
调查程序在我们的调查论文中有更详细的说明。

NEW (Nov 2024):  新（2024年11月）：

we now include the post author country location in post_author_country_location when we were available to infer it. The inference uses the Twitter user location and the Google Geocoding API. More details in our survey paper.
我们现在在 post_author_country_location 时将作者后国家的位置纳入推断。推断使用了 Twitter 用户位置和 Google 地理编码 API。更多细节请参见我们的调查论文 。
we now also include posts from datasets that are not publicly available but could be retrieved with the Twitter API
我们现在也包括那些未公开但可通过 Twitter API 检索的数据集中的帖子
Data access and intended use
数据访问及预期使用
Please send an access request detailing how you plan to use the data. The main purpose of this dataset is to train and evaluate hate speech detection models, as well as study hateful discourse online. This dataset is NOT intended to train generative LLMs to produce hateful content.
请发送访问请求，详细说明您计划如何使用这些数据。该数据集的主要目的是训练和评估仇恨言论检测模型，同时研究网络仇恨言论。该数据集并非用于训练生成式大型语言模型以生成仇恨内容。

Columns   柱子
The dataset contains six columns:
该数据集包含六列：

text: the annotated post
正文 ：注释文章
labels: annotation of whether the post is hateful (== 1) or not (==0). As datasets have different annotation schemes, we systematically binarized the labels.
标签 ：注释帖子是否充满仇恨（== 1）或是否（==0）。由于数据集的注释方案不同，我们系统地将标签二进制化。
source: origin of the data (e.g., Twitter)
来源 ：数据来源（例如，Twitter）
dataset: dataset the data is from (see "Datasets" part below)
数据集 ：数据来源数据集（见下文“数据集”部分）
nb_annotators: number of annotators by post
nb_annotators：按帖子划分的注释者数量
tweet_id: tweet ID where available
tweet_id：在有推特的情况下提供推特 ID。
post_author_country_location: post author country location, when it could be inferred. Details on the inference in our survey paper.
post_author_country_location：作者后国家所在地，可能推断出。关于该推断的详细信息，见我们的调查论文 。
Datasets   数据集
The datasets that compose this superset are:
组成该超集的数据集有：

hatEval, SemEval-2019 Task 5: Multilingual Detection of Hate Speech Against Immigrants and Women in Twitter (hateval in the dataset column)
hatEval，2019 年下半年任务 5：在推特上多语言检测针对移民和女性的仇恨言论（ 数据集栏中为仇恨 ）
paper link  论文链接
raw data link  原始数据链
Detecting and Monitoring Hate Speech in Twitter (haternet in the dataset column)
检测和监控 Twitter 中的仇恨言论（ 数据集栏中为仇恨网络 ）
paper link  论文链接
raw data link  原始数据链
Multilingual Resources for Offensive Language Detection (chileno)
多语言资源用于攻击性语言检测（ 智利诺语）
paper link  论文链接
raw data link  原始数据链
Analyzing Zero-Shot transfer Scenarios across Spanish variants for Hate Speech Detection (hascosva)
分析西班牙语版本中零发转运场景以实现仇恨言论检测（hascosva）
paper link  论文链接
raw data link  原始数据链
HOMO-MEX: A Mexican Spanish Annotated Corpus for LGBT+phobia Detection on Twitter (homomex)
HOMO-MEX：推特上的墨西哥西班牙语注释语料库，用于 LGBT+恐惧症检测（homomex）
paper link  论文链接
raw data link  原始数据链
Additional datasets on demand
按需获取的额外数据集
In our survey, we identified one additional dataset that is not public but can be requested to the authors. We include in our dataset posts from this dataset that could be retrieved with the Twitter API. The full list is:
在我们的调查中，我们发现了一个额外的数据集，该数据集非公开，但可以向作者请求。我们在数据集中包含了可用 Twitter API 检索的该数据集帖子。完整列表如下：

Detecting misogyny in Spanish tweets. An approach based on linguistics features and word embeddings
在西班牙语推文中发现厌女症。基于语言学特征和词嵌入的方法
paper link  论文链接
Preprocessing   预处理
We drop duplicates. In case of non-binary labels, the labels are binarized (hate speech or not). We replace all usernames and links by fixed tokens to maximize user privacy. Further details on preprocessing can be found in the preprocessing code here.
我们会丢弃重复的。对于非二元标签，标签是二元化的（无论是否仇恨言论）。我们用固定令牌替换所有用户名和链接，以最大化用户隐私。关于预处理的更多细节可在此处的预处理代码中找到。