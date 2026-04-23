# id-abusive-language-detection

## About this data
Here we provide our dataset for abusive language detection in the Indonesian language. This dataset is provided in two types of labeling:
* In **re_dataset_two_labels.csv**, the dataset coded into two labels, that are `1` (*not abusive language*) and `2` (*abusive language*);
* In **re_dataset_three_labels.csv**, the dataset coded into three labels, that are  `1` (*not abusive language*), `2` (*abusive but not offensive*), and `3` (*offensive language*).

Due to the Twitter's Terms of Service, we do not provide the tweet ID. All username and URL in this dataset are changed into USER and URL. 

For text normalization in our experiment, we build small typo and slang words dictionaries named **kamusalay.csv**, that contain two columns (first columns are the typo and slang words, and the second one is the formal words). Here the examples of mapping:
* beud --> banget
* jgn --> jangan
* loe --> kamu

## More detail
If you want to know how this dataset was build (including the explanation of crawling and annotation technique) and how we did our experiment in abusive language detection in Indonesian language using this dataset, you can read our paper in here: https://www.sciencedirect.com/science/article/pii/S1877050918314583.

## How to cite us
This dataset can be used for free, but if you want to publish paper/publication using this dataset, please cite this publication:

**Ibrohim, M.O., Budi, I.. A Dataset and Preliminaries Study for Abusive Language Detection in Indonesian Social Media. Procedia Computer Science 2018;135:222-229.** (Every paper template may have different citation writting. For LaTex user, you can see **citation.bib**).

## License
<a rel="license" href="http://creativecommons.org/licenses/by-nc-sa/4.0/"><img alt="Creative Commons License" style="border-width:0" src="https://i.creativecommons.org/l/by-nc-sa/4.0/88x31.png" /></a><br />This work is licensed under a <a rel="license" href="http://creativecommons.org/licenses/by-nc-sa/4.0/">Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License</a>.

# id-abusive-language-detection

## 关于此数据

我们在此提供用于检测印尼语辱骂性语言的数据集。该数据集提供两种标签：

* 在 **re_dataset_two_labels.csv** 中，数据集被编码为两个标签，分别为 `1`（*非辱骂性语言*）和 `2`（*辱骂性语言*）；

* 在 **re_dataset_three_labels.csv** 中，数据集被编码为三个标签，分别为 `1`（*非辱骂性语言*）、`2`（*辱骂性但不冒犯*）和 `3`（*冒犯性语言*）。

由于 Twitter 的服务条款，我们不提供推文 ID。此数据集中的所有用户名和 URL 均已替换为 USER 和 URL。

为了进行文本规范化，我们在实验中构建了名为 **kamusalay.csv** 的小型拼写错误和俚语词典，其中包含两列（第一列是拼写错误和俚语，第二列是正式用语）。以下是映射示例：

* beud --> banget

* jgn --> jangan

* loe --> kamu

## 更多详情

如果您想了解该数据集的构建过程（包括爬取和标注技术的说明）以及我们如何使用该数据集进行印尼语粗俗语言检测实验，您可以阅读我们的论文：https://www.sciencedirect.com/science/article/pii/S1877050918314583。

## 如何引用我们

本数据集可免费使用，但如果您想使用本数据集发表论文/出版物，请引用以下出版物：

**Ibrohim, M.O., Budi, I.. A Dataset and Preliminaries Study for Abusive Language Detection in Indonesian Social Media. Procedia Computer Science 2018;135:222-229.**（每篇论文的引用格式可能有所不同。LaTeX 用户可参考 **citation.bib** 文件）。

## 许可

<a rel="license" href="http://creativecommons.org/licenses/by-nc-sa/4.0/"><img alt="知识共享许可" style="border-width:0" src="https://i.creativecommons.org/l/by-nc-sa/4.0/88x31.png" /></a><br />本作品采用<a rel="license" href="http://creativecommons.org/licenses/by-nc-sa/4.0/">知识共享署名-非商业性使用-相同方式共享 4.0 国际许可协议</a>进行许可。