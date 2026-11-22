# 寒武纪的鳄鱼 · 研究 Skill

基于陈泽鑫的公开投资框架整理，覆盖商品周期、公司财报、估值、换仓复盘、读书与人生经验。

## 一键安装到 Codex

Windows 用户在 PowerShell 中运行下面这条命令。

```powershell
& ([scriptblock]::Create((irm 'https://api.github.com/repos/gutianniao/hanwu-crocodile-skill/contents/install.ps1' -Headers @{Accept='application/vnd.github.raw+json'})))
```

脚本校验 `v1.0.0` 安装包后，将 Skill 安装到 `~/.agents/skills/`。如果已安装同名 Skill，脚本会直接退出。安装完成后，新开 Codex 对话，输入 `$hanwu-crocodile` 调用。[查看安装脚本](install.ps1)

也可以把下面这条消息发给 Codex。

```text
$skill-installer 安装 https://github.com/gutianniao/hanwu-crocodile-skill/tree/main/hanwu-crocodile
```

## 一句话安装到豆包工作

在**豆包工作电脑版**打开左侧「技能 · 连接器 · 伙伴」，选择「新建」→「与豆包对话新建技能」，发送下面这条消息。

```text
新建技能 安装：https://github.com/gutianniao/hanwu-crocodile-skill 请导入仓库中的 hanwu-crocodile 技能目录，并保留其子目录和文件。
```

按豆包提示保存，在「我的技能」查看。使用时可以对豆包说「用寒武纪的鳄鱼 Skill 分析这只周期股」。

如果豆包无法读取 GitHub 链接，可以在同一个「新建」菜单选择「上传技能」，从本地选择 [发布版 ZIP](https://github.com/gutianniao/hanwu-crocodile-skill/releases/download/v1.0.0/hanwu-crocodile-skill.zip)。

## 下载与手动安装

- [下载 ZIP](https://github.com/gutianniao/hanwu-crocodile-skill/releases/latest)
- [安装与使用](hanwu-crocodile/INSTALL.md)
- [Skill 入口](hanwu-crocodile/SKILL.md)

解压后，把 `hanwu-crocodile` 文件夹放入项目的 `.agents/skills/`。新开 Codex 对话，输入 `$hanwu-crocodile` 调用。

共享包提供公开资料目录、重点摘要和原文链接。用户也可以在本机导入自己有权使用的资料。
