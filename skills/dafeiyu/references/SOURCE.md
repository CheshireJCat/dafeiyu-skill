# 来源与使用边界

- 适配器作者：CheshireJCat。选图脚本和本 Skill 的原创规则采用仓库根目录 MIT 许可。
- 上游插件：https://github.com/yyh-001/dsh-meme
- 描述与关键词元数据取自上游提交 `d53f92951e41994c8b978ca7f1c861dca6a8bd4d` 的 `memes/dafeiyu-001/index.db`。保留其 MIT 许可于 `UPSTREAM-LICENSE.txt`。
- 24 张图片由用户在首次执行 fetch 时直接从上游图库 Release 下载，本仓库、GitHub Release 和 Skill 包均不分发图片。
- 固定图库：`dafeiyu-001`，版本 `1.3.0`。
- 上游 Release：https://github.com/yyh-001/dsh-meme-packs/releases/tag/dafeiyu-001-v1.3.0
- 压缩包 SHA-256：`9fca6a4fc101232b39ab79181b9ed1b12289cf4890b3fadac89576545e51b3a4`。
- 图片许可标记为 **personal**，不属于适配器的 MIT 授权。上游明确要求商业使用或再分发前获得权利人许可：https://github.com/yyh-001/dsh-meme-packs/blob/main/LICENSES.md
- manifest.json 随图片保存到用户的本地缓存，便于查看原始许可。

## 网络与本地数据

原始模式下，显式 `fetch` 会通过系统 curl 访问上述上游 GitHub HTTPS Release。下载会校验固定版本和 SHA-256，不执行压缩包内容，只安装明确列出的图片和 manifest。工具没有上传、遥测或自动更新逻辑，不读取聊天记录。

`search` 和 `list` 完全离线。缓存默认保存在 `~/.cache/dafeiyu-skill/dafeiyu-001-v1.3.0`；可通过 `DAFEIYU_DATA_DIR` 指定其他个人目录。工具不改动全局 AGENTS.md、Hook 或宿主配置。


## 扩展来源（2026-10-20）

- DSH 图库：https://github.com/yyh-001/dsh-meme-packs ，固定快照 `1004d77910a4612727b3aba17c683f4b75ec01e5`。`sync` 读取 catalog.json 与 stickers.json，7 套、431 条记录；包含 DeepSeek 酱语录 128 条。扩展元数据仅保存到使用者本地，不随 Skill 发布。
- 梗鲸作者仓库：https://github.com/the-beating-light-of-the-nail/deepseek-chan-meme-pack ，核对提交 `c82a0fb1c8958c2f0d6ea7fa7c12128027cfd7c6` 的说明。作者公开推荐 CDN 热链，并指向完整结构化目录。
- 梗鲸实时目录：https://aigengtu.com/gallery-index.json 。仅使用 DeepSeek娘 分组；本次同步为 2,030 条。实时数量可变化，以 packs 命令输出为准。
- CDN：https://img.aigengtu.com/0_preview/meme/NNN.webp 。按选中项下载，不重新托管，不把 2,030 张批量下载作为默认行为。
- 扩展缓存：`DAFEIYU_LIBRARY_DIR`，默认 `~/.cache/dafeiyu-skill/library`。显式 sync 联网更新目录；fetch 联网取图；search/list/packs 离线。无上传、遥测、Hook 或全局配置修改。
- 随机选图：pick 按最高关键词匹配、近期去重和图库平衡选择；无 --fetch 时完全离线、不写历史，--fetch 显式取图并校验成功后，仅在本地 recent.json 保留最近 20 个选图 ID、图库 ID 和去重标识，不保存聊天或用户信息，不上传记录。这是近期选图记录，不是消息投递回执；删除可重置。

### 许可与署名

以每套上游说明和包内 manifest 为准：[DSH 许可说明](https://github.com/yyh-001/dsh-meme-packs/blob/1004d77910a4612727b3aba17c683f4b75ec01e5/LICENSES.md)。

- dafeiyu-001 / dafeiyu-learned：personal，再分发或商用需权利人许可。
- official-001 / maid-emoji / pack-mvc2p5cv：CC-BY-NC-SA-4.0，需遵循署名、非商业、相同方式共享等条件。
- maid-emoji 的女仆鲸鱼娘二次设计作者：ZipZipPipe；角色原作：上善无形。whale-girl-emoji 是含不同来源作品的同人整理包，详见上游逐项说明。
- deepseek-chan / gengjing / whale-girl-emoji：noncommercial-fan，原画与角色权利归各原作者，不是适配器作者的授权。梗鲸有权利人下架入口；数据源失效或撤下时不得绕过访问限制。

每条输出包含 license、source；已缓存包保存原 manifest 或本地校验记录。ZIP 对上游压缩包 SHA-256 校验；CDN 无发布者哈希，文件签名检查与首次缓存 SHA-256 仅用于格式/本地完整性检查，不代表上游签名认证。
