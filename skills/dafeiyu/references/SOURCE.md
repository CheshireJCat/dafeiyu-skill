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

只有显式 `fetch` 会通过系统 curl 访问上述上游 GitHub HTTPS Release。下载会校验固定版本和 SHA-256，不执行压缩包内容，只安装明确列出的图片和 manifest。工具没有上传、遥测或自动更新逻辑，不读取聊天记录。

`search` 和 `list` 完全离线。缓存默认保存在 `~/.cache/dafeiyu-skill/dafeiyu-001-v1.3.0`；可通过 `DAFEIYU_DATA_DIR` 指定其他个人目录。工具不改动全局 AGENTS.md、Hook 或宿主配置。
