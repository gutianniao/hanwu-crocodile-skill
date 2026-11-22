# 安装和使用

## 安装到 Codex

1. 解压整个压缩包，找到包含 `SKILL.md` 的 `hanwu-crocodile` 文件夹。
2. 将它放进项目的 `.agents/skills/`，或放进个人目录 `~/.agents/skills/`。目录不存在时可直接创建。最终路径应为 `.agents/skills/hanwu-crocodile/SKILL.md`。
3. 新开一个 Codex 对话，输入 `$hanwu-crocodile 讲讲鳄鱼老师怎样判断周期股值得买入`。

你也可以把解压后的 `SKILL.md` 连同整个文件夹交给支持 Markdown Skill 的工具，并在该工具里调用。不使用终端时，可以直接读 `references/` 里的框架、公开案例和来源导览。包内是编者归纳和来源链接。打开知识星球链接是否需要会员权限，以站点为准。

## 检索公开资料

在装有 Python 3.10 或更高版本的环境中，从 Skill 文件夹运行以下命令。公共检索使用 Python 自带的 SQLite。

```text
python -X utf8 scripts/query.py --public-only find "行业见底" "产能退出" --limit 5
python -X utf8 scripts/query.py show W096
python -X utf8 scripts/query.py catalog --title "中国石油"
```

## 导入自己的资料

先把自己有权使用的导出文件放在本机目录。文本资料支持 TXT、Markdown、CSV、TSV、HTML、DOCX、PPTX、EPUB 和下述 JSONL。需要 PDF 或 XLSX 时，再安装对应依赖。

```text
python -m pip install pymupdf openpyxl
python -X utf8 scripts/import_materials.py "你的资料目录"
python -X utf8 scripts/query.py catalog --kind personal
python -X utf8 scripts/query.py find "公司简称" "单位成本" --kind personal
```

图片型 PDF 可在安装本机 Tesseract 和对应语言数据后加 `--ocr`。默认语言为 `chi_sim+eng`，必要时用 `--tessdata "语言数据目录"` 指定位置。旧版 `.doc` 文件可先转存为 `.docx`。财报图表和扫描数字以原文为准。工作簿公式使用已有的缓存结果。

知识星球等平台的自有导出可整理成 UTF-8 JSONL，每行是一条记录。`title` 和 `text` 必填，`url`、`date`、`author` 和 `channel` 选填。现有的 Markdown、HTML 和文本导出也可直接导入。

```jsonl
{"title":"我的周期研究笔记","text":"先核对产品售价和原料成本的同口径变化。","date":"2026-11-22","author":"我的整理","channel":"个人笔记"}
```

个人索引保存在 `~/.hanwu-crocodile/research.sqlite3`，在 Skill 文件夹之外。公开目录也会进入该索引。每次导入按本次提供的所有路径重建，可同时传多个文件或文件夹。可用环境变量 `HANWU_CROCODILE_INDEX` 改默认路径，也可对导入和查询命令分别指定同一个 `--db`。索引内有提取后的个人资料，分享时发原 ZIP 即可。

## 调用示例

> $hanwu-crocodile 我准备从工程股换到化工股。按鳄鱼老师的方法拆开卖出和买入理由，列出需要验证的公告和行业数据，并测算换仓后的集中度和压力情景。

> $hanwu-crocodile 结合我的财报和研报，按产销量、售价、单位成本、经营现金流做对比，并标上报告期和页码。

> $hanwu-crocodile 整理老师怎么读书和复盘错误。按原文证据给我各一个练习。
