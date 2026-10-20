# 大肥鱼 · Dafeiyu Skill

给 Codex 桌面端回复配一张合适的大肥鱼。支持按中文描述、关键词和情绪选图，使用真实本地图片展示；不依赖 DSH、MCP 或模型 API Key。

**图片不随 Skill 分发。** 现已接入 [dsh-meme 图库市场](https://github.com/yyh-001/dsh-meme-packs)和 [DeepSeek 娘 / 梗鲸](https://github.com/the-beating-light-of-the-nail/deepseek-chan-meme-pack)：同步公开目录，离线检索，选中后缓存图片。

| 目录 | 当前覆盖范围 |
| --- | --- |
| DSH 图库市场 | 7 套、431 条：原版大肥鱼、学图、DeepSeek 酱语录、女仆、鲸鱼娘等 |
| 梗鲸 DeepSeek 娘 | 完整 DeepSeek娘 分组，2026-10-20 同步为 2,030 条；不导入其他角色 |

共 8 个可选图库、2,461 条索引记录，来源间有重叠，搜索按 CDN 图片 URL 去重。数量随显式同步变化，不表示同等数量的独立图片。

## 安装到 Codex

需要 Python 3.10+、curl。使用 skills CLI 安装时还需要 Node.js 22.20+。

```sh
npx skills add CheshireJCat/dafeiyu-skill --skill dafeiyu --agent codex --global
```

下一轮或新会话里说：

> 使用 $dafeiyu，同步梗鲸和 DSH 表情目录，找一张“就吃一碗”的大肥鱼，取回后放在回复里。

也可以直接克隆，手工复制 `skills/dafeiyu` 到个人 Skill 目录；不要覆盖已有的定制版本。

## 使用

在已安装 Skill 的目录执行（其他目录调用时换成脚本的绝对路径）：

```sh
python3 scripts/dafeiyu.py sync
python3 scripts/dafeiyu.py packs
python3 scripts/dafeiyu.py search 比心
python3 scripts/dafeiyu.py search 一碗 --pack gengjing --limit 3
python3 scripts/dafeiyu.py fetch --id gengjing/340
python3 scripts/dafeiyu.py fetch --pack dafeiyu-learned
python3 scripts/dafeiyu.py list --pack maid-emoji --limit 10 --offset 0
```

`sync` 显式联网读取 DSH 固定快照与梗鲸实时目录；失败保留旧索引。扩展缓存默认在 `~/.cache/dafeiyu-skill/library`，用 `DAFEIYU_LIBRARY_DIR` 修改。`search`、`list`、`packs` 完全离线。

未缓存候选返回描述、许可、来源和 `fetchArgs`；不会编造路径或 Markdown。按搜索结果的精确 ID 执行 `fetch --id` 后，返回真实绝对路径及可嵌入回复的 Markdown。示例 ID 以后可能从实时目录撤下，以搜索结果为准。

ZIP 图库首次取图时下载整套包并验证上游 SHA-256；CDN 图仅按需取一张，检查图片格式、记录本地 SHA-256，后续离线复用。CDN 未提供发布者哈希，本地哈希不代表上游真实性认证。不默认批量下载完整梗鲸或酱语录图库。

兼容原有 `fetch`（无参数）：仍下载原版 24 张，保留 `DAFEIYU_DATA_DIR` 和 `~/.cache/dafeiyu-skill/dafeiyu-001-v1.3.0`；没有同步扩展目录时 search/list 保持原有行为。Windows 上可用 `python` 替代 `python3`，终端内联图片能力取决于客户端。

希望助手偶尔主动配图时，可以明确告诉它：

> 以后在轻松聊天、感谢或庆祝时，允许使用 $dafeiyu 配一张图；不用每轮发，严肃或紧急话题不用，我说停就停。

安装不会自动修改你的全局指令或新增 Hooks。已有本地版本也不需要为这个公开仓库而替换。

## 发布与许可

- 适配器、脚本与原创规则：MIT。
- 上游描述与关键词：保留 [上游 MIT 声明](skills/dafeiyu/references/UPSTREAM-LICENSE.txt)。
- 图片与扩展元数据：按来源保留 **personal**、**noncommercial-fan**、**CC-BY-NC-SA-4.0** 等许可，**不属于本仓库 MIT 授权**。女仆鲸鱼娘二次设计署名 ZipZipPipe，角色原作上善无形，其他作品来源与约束详见 [来源和数据行为](skills/dafeiyu/references/SOURCE.md)及[上游许可说明](https://github.com/yyh-001/dsh-meme-packs/blob/main/LICENSES.md)。
- skills.sh 可通过上述安装命令发现和安装本 Skill；排行榜与页面收录取决于平台处理，不是 OpenAI 官方目录背书。

本项目是独立社区适配，与 DeepSeek、OpenAI 及上游图库作者没有隶属关系。

## 验证

```sh
python3 -m unittest discover -s tests -v
```

单元测试使用运行时生成的合成数据，不包含或重新分发上游图片。

## English

A context-aware sticker skill for Codex Desktop. Requires Python 3.10+ and curl. Explicitly sync the seven DSH packs and the complete DeepSeek collection linked by the GengJing author's repository, search offline, then fetch the selected image. Archives use upstream SHA-256 verification; individual CDN images use format checks and local cache hashes, not publisher signatures. Licenses and source attribution are returned per pack. The repository does not redistribute images or the extended live catalog. Existing original-24 commands remain supported. Inline local-image rendering depends on the host.
