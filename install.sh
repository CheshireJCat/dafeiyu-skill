#!/bin/sh
# Optional install entrypoint: skills CLI itself does not run skill postinstall hooks.
set -eu

if [ "$#" -gt 1 ]; then
  printf '%s\n' '不支持额外参数。' >&2
  exit 2
fi
case "${1:-}" in
  "") set -- --global ;;
  --project) shift ;;
  *) printf '%s\n' '用法：sh install.sh [--project]（默认安装到个人全局，--project 安装到当前项目）' >&2; exit 2 ;;
esac

npx --yes skills add CheshireJCat/dafeiyu-skill --skill dafeiyu --agent codex --yes "$@"

printf '\n%s\n' \
  '大肥鱼安装命令已完成。' \
  '默认档位：高频（目标约 70%）＋自动调整；已有个人偏好优先。' \
  '未授权主动配图时仍仅响应点播。开启可说：允许 $dafeiyu 主动配图。' \
  '切换：多发点 / 少发点 / 低频 / 标准 / 高频 / 每轮 / 关闭表情包。' \
  '恢复默认：高频＋自动调整。临时调档仅在当前会话有效。' \
  '首次使用可说：使用 $dafeiyu，告诉我当前频率和切换方式。'
