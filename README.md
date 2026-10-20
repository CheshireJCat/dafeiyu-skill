# 大肥鱼 · Dafeiyu Skill

给 Codex 桌面端回复配一张合适的大肥鱼。支持按中文描述、关键词和情绪选图，使用真实本地图片展示；不依赖 DSH、MCP 或模型 API Key。

**图片不随 Skill 分发。** 首次使用时从 [dsh-meme 上游图库](https://github.com/yyh-001/dsh-meme-packs)下载 24 张个人使用素材，之后离线选图。

## 安装到 Codex

需要 Python 3.10+、curl。使用 skills CLI 安装时还需要 Node.js 22.20+。

```sh
npx skills add CheshireJCat/dafeiyu-skill --skill dafeiyu --agent codex --global
```

下一轮或新会话里说：

> 使用 $dafeiyu，来张比心的大肥鱼。如果还没准备图库，请从上游下载个人使用版本。

也可以直接克隆，手工复制 `skills/dafeiyu` 到个人 Skill 目录；不要覆盖已有的定制版本。

## 使用

在已安装 Skill 的目录执行（其他目录调用时换成脚本的绝对路径）：

```sh
python3 scripts/dafeiyu.py fetch
python3 scripts/dafeiyu.py search 比心
python3 scripts/dafeiyu.py search happy --limit 3
python3 scripts/dafeiyu.py list
```

`fetch` 仅从固定上游 Release 下载，并验证压缩包和图片 SHA-256。`search` 返回候选图片的描述、绝对路径及 Markdown，可直接嵌入 Codex 桌面端回复。默认缓存位于 `~/.cache/dafeiyu-skill/dafeiyu-001-v1.3.0`，可以用 `DAFEIYU_DATA_DIR` 修改。Windows 上可用 `python` 替代 `python3`，终端内联图片能力取决于客户端。

希望助手偶尔主动配图时，可以明确告诉它：

> 以后在轻松聊天、感谢或庆祝时，允许使用 $dafeiyu 配一张图；不用每轮发，严肃或紧急话题不用，我说停就停。

安装不会自动修改你的全局指令或新增 Hooks。已有本地版本也不需要为这个公开仓库而替换。

## 发布与许可

- 适配器、脚本与原创规则：MIT。
- 上游描述与关键词：保留 [上游 MIT 声明](skills/dafeiyu/references/UPSTREAM-LICENSE.txt)。
- 图片：上游标记为 **personal**，商业使用或再分发前需权利人许可；**不属于本仓库 MIT 授权**。详见 [来源和数据行为](skills/dafeiyu/references/SOURCE.md)及[上游许可说明](https://github.com/yyh-001/dsh-meme-packs/blob/main/LICENSES.md)。
- skills.sh 可通过上述安装命令发现和安装本 Skill；排行榜与页面收录取决于平台处理，不是 OpenAI 官方目录背书。

本项目是独立社区适配，与 DeepSeek、OpenAI 及上游图库作者没有隶属关系。

## 验证

```sh
python3 -m unittest discover -s tests -v
```

单元测试使用运行时生成的合成数据，不包含或重新分发上游图片。

## English

A context-aware sticker skill for Codex Desktop. Install with the command above and ask `$dafeiyu` for a reaction. Requires Python 3.10+ and curl. Images are downloaded directly from a pinned upstream release for personal use, verified with SHA-256, then selected offline. This repository distributes the adapter and metadata only, not the images. Image rights are separate from the MIT-licensed adapter. Inline local-image rendering depends on the host; other clients may only show a file link.
