---
name: dafeiyu
description: 在 Codex 桌面端回复中使用大肥鱼表情包。用户点播大肥鱼、斗图，或已同意在轻松聊天、感谢、鼓励和庆祝时配图时使用。从本地图库选图，不用于生成新表情包。
---

# 大肥鱼表情包

按语境选一张大肥鱼，以 Markdown 图片嵌入 Codex 桌面端回复。仓库只包含规则、元数据和工具；图片由用户从上游下载到个人本地缓存，不随本 Skill 分发。

## 初次准备

使用 Python 3.10+ 和 curl，无需 pip、API Key、MCP 或 DSH。以下命令都在本 SKILL.md 所在目录执行；从其他目录调用时使用脚本的真实绝对路径。

先试 `python3 scripts/dafeiyu.py search 比心`。若提示图库缺失，向用户说明：首次会从 yyh-001/dsh-meme-packs 下载约 920 KiB 的 24 张图片，图库标记为 personal，仅供个人使用，再分发或商用需权利人许可。用户要求安装或使用这套个人图库时，可执行：

```sh
python3 scripts/dafeiyu.py fetch
```

下载仅发生在显式 fetch；固定上游版本 1.3.0，校验压缩包及每张图片的 SHA-256。缓存目录由 `DAFEIYU_DATA_DIR` 指定，默认 `~/.cache/dafeiyu-skill/dafeiyu-001-v1.3.0`。已有缓存不会被静默覆盖。

## 选图和回复

```sh
python3 scripts/dafeiyu.py search 比心
python3 scripts/dafeiyu.py search happy --limit 3
python3 scripts/dafeiyu.py list
```

- 返回候选的 ID、画面描述、真实绝对路径和 Markdown。选最贴切的一张，把 `markdown` 字段原样作为图片放进回复，不用代码块包裹。
- 不输出 DSH 的 `[表情: 描述]` 标记、file:// URL、相对图片路径或虚构路径。文件丢失、损坏、无匹配时正常用文字回答；按需要说明问题，不静默下载或更新。
- 显式点播时可简短文字配图；只要图时直接给图。通常一轮最多一张，用户要求多张时按需提供。
- 主动配图需尊重用户的偏好，适用于感谢、轻松玩笑、鼓励和有事实依据的庆祝。不要每轮发，也避免连续多轮主动配图或重复同一张。用户说停就停。
- 严肃话题、紧急排障、明显焦虑或悲伤、严格 JSON/代码/补丁等输出通常不用。表情不能替代实质任务和验证，不能用点赞图暗示未验证的成功，不用嫌弃图责怪用户。
- 保留用户的语言和语气，不强制更换人格，也不自动改动全局 AGENTS.md。
- 纯终端和其他客户端可能不能内联显示本地图片；必要时返回文件路径，不声称已经验证其渲染。

来源、素材许可与隐私行为见 [SOURCE.md](references/SOURCE.md)。元数据见 [catalog.json](references/catalog.json)，脚本会按需读取，无需预先全部加载。
