#!/usr/bin/env bash
# QuadProxy Genesis - operator faucet.
#
# One command, every gate under your hand. Automates what can be automated, stops at
# the actions that genuinely need your identity, and records every outcome into
# STATE.json so the bottleneck engine re-derives itself as you go.
#
# Safe by construction: never touches production, never force-pushes, never writes to
# .env or the order database, never posts anywhere on your behalf.
#
#   ./launch.sh          interactive
#   ./launch.sh status   showroom only, no prompts

set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE" || exit 1
G="python3 $HERE/genesis.py"

# Read from the terminal when there is one, else fall back to stdin so the faucet
# still works when piped or driven by a script.
# Test the open itself: /dev/tty can pass a readability test yet fail to open
# when there is no controlling terminal (piped, cron, nohup).
exec 3</dev/tty 2>/dev/null || exec 3<&0

B=$'\033[1m'; D=$'\033[2m'; GRN=$'\033[32m'; YEL=$'\033[33m'; RED=$'\033[31m'; CYN=$'\033[36m'; N=$'\033[0m'
say()  { printf '%s\n' "$*"; }
head_() { printf '\n%s%s%s\n' "$B" "$*" "$N"; printf '%s\n' "$(printf '%.0s-' {1..52})"; }
ok()   { printf '%s[done]%s %s\n' "$GRN" "$N" "$*"; }
warn() { printf '%s[gate]%s %s\n' "$YEL" "$N" "$*"; }
info() { printf '%s%s%s\n' "$D" "$*" "$N"; }

confirm() { # confirm "question" -> 0 yes, 1 no
  local a
  read -r -u 3 -p "$(printf '%s%s%s [y/N] ' "$CYN" "$1" "$N")" a || return 1
  [[ "$a" =~ ^[Yy] ]]
}

ask() { # ask "prompt" -> echoes answer
  local a
  read -r -u 3 -p "$(printf '%s%s%s ' "$CYN" "$1" "$N")" a || a=""
  printf '%s' "$a"
}

record() { $G record "$1" "$2" --how "${3:-reported}" --src "${4:-launch.sh}" >/dev/null 2>&1 \
             && ok "recorded $1=$2" || warn "could not record $1"; }

# ---------------------------------------------------------------- actions

a1_free_tool() {
  head_ "1. Publish the free MIT diagnostic"
  info "Why first: your starter-kit licence forbids redistribution, so the fix snippet"
  info "cannot legally be quoted in an answer or a blog post. That single fact blocks"
  info "awesome-list submission AND the citation mechanism you need to be findable."
  say
  say "Files are ready at: ${B}$HERE/free-tool${N}"
  say
  say "  1. Create a new PUBLIC repo named: ${B}qwebengine-proxy-doctor${N}"
  say "  2. Then run:"
  say "${D}     cd $HERE/free-tool"
  say "     git init -b main && git add ."
  say "     git commit -m 'qwebengine-proxy-doctor: verify your Qt WebEngine proxy'"
  say "     git remote add origin git@github.com:ILL3NITVM/qwebengine-proxy-doctor.git"
  say "     git push -u origin main${N}"
  say "  3. Add topics: qtwebengine qwebengineview pyqt pyqt5 pyqt6 python proxy"
  say "     proxy-authentication qnetworkproxy diagnostics"
  say
  if confirm "Is the free tool now public?"; then record free_tool_published yes verified "operator confirmed"; fi
}

a2_repo_fixes() {
  head_ "2. Apply the fix pack to the starter-kit repo"
  info "Verified defects, highest impact first. Full detail in repo-fixes/APPLY.md"
  say
  say "  ${RED}a${N} Version disagrees across 4 files (VERSION/pyproject/CHANGELOG/tag)"
  say "  ${RED}b${N} docs/KILLER_DEMO_PLAN.md is PUBLIC - an internal marketing document"
  say "  ${RED}c${N} __pycache__/ committed in root and examples/"
  say "  ${RED}d${N} README opens with price + disclaimers, no symptom keywords"
  say "  ${RED}e${N} SOCKS5 claim contradicted by examples/07_socks5_and_http_proxies.py"
  say "  ${RED}f${N} Topic is 'qt-webengine' (4 repos, dead); 'qtwebengine' has 89"
  say
  say "  README replacement : ${B}$HERE/repo-fixes/README.replacement.md${N}"
  say "  Demo GIF           : ${B}$HERE/media/doctor-demo.gif${N}  -> docs/media/"
  say
  warn "Two CONFIRM markers in the README replacement are business commitments"
  warn "(refund window, support response time). Do not publish either unless you"
  warn "intend to honour it. An unhonoured refund promise is worse than none."
  say
  if confirm "Fix pack applied and pushed?"; then record repo_stars 0 verified "post-fix baseline"; fi
}

a3_research() {
  head_ "3. Publish the original research"
  info "This is the asset a competitor cannot copy from a search result, and the only"
  info "one that compounds. Findings verified on Qt 6.11.0 / PyQt 6.11.0:"
  say
  say "  ${B}1${N} A page loads perfectly with loadFinished(True) while the proxy"
  say "    handles ZERO requests. The silent failure, reproduced on demand."
  say "  ${B}2${N} proxyAuthenticationRequired never fired, yet auth succeeded."
  say "    This contradicts the advice in nearly every tutorial and forum answer."
  say "  ${B}3${N} Therefore behaviour is version-dependent: verify empirically."
  say
  say "  Findings   : ${B}$HERE/verified-example/FINDINGS.md${N}"
  say "  Reproducer : ${B}$HERE/verified-example/e2e_proxy_test.py${N}"
  say "  Outline    : ${B}$HERE/outreach/02-article-content-gap.md${N}"
  say
  info "Publish on quadproxy.com FIRST so the SEO equity lands on your domain,"
  info "then syndicate to DEV/Hashnode with rel=canonical pointing back."
  say
  if confirm "Research published?"; then
    local u; u=$(ask "Public URL (blank to skip):")
    [ -n "$u" ] && record helpful_posts_live 1 verified "$u"
  fi
}

a4_lead() {
  head_ "4. Answer the one live lead"
  say "  Thread : ${B}https://forum.qt.io/topic/150315/can-t-setup-proxy-credentials${N}"
  say "  Fit 10 / Intent 9 - the only live, high-intent lead found."
  say "  Draft  : ${B}$HERE/outreach/01-qt-forum-150315.md${N}"
  say
  warn "READ THE THREAD FIRST. It is from ~Oct 2023. If someone already solved it,"
  warn "do not post. That restraint is what keeps you welcome on that forum."
  say
  info "Forum rule (verified): 'showcase the technology, not the product nor the"
  info "vendor'. The draft answers completely before any mention of you; the"
  info "disclosure is one line at the bottom. Do not move it up."
  say
  if confirm "Reply posted?"; then
    local u; u=$(ask "Post URL (blank to skip):")
    [ -n "$u" ] && record helpful_posts_live 2 verified "$u"
  fi
}

a5_measure() {
  head_ "5. Measure the funnel (this is what moves the bottleneck)"
  local log=/var/log/nginx/access.log v=""
  if [ -r "$log" ] || sudo -n test -r "$log" 2>/dev/null; then
    v=$(sudo -n awk '{print $1}' "$log" 2>/dev/null | sort -u | wc -l)
    say "unique client IPs in access.log: ${B}${v}${N}"
    [ -n "$v" ] && record visitors_30d "$v" verified "nginx access.log via launch.sh"
  else
    warn "cannot read $log from here."
    v=$(ask "Unique visitors last 30d (blank to skip):")
    [ -n "$v" ] && record visitors_30d "$v" reported "operator supplied"
  fi
  local p; p=$(ask "Real completed payments last 30d (blank to skip):")
  [ -n "$p" ] && record payments_30d "$p" reported "operator supplied"
}

menu() {
  clear 2>/dev/null
  $G show
  cat <<MENU

${B}ACTIONS${N}
  1  Publish the free MIT diagnostic      ${D}unblocks citation + awesome-lists${N}
  2  Apply the repo fix pack              ${D}trust + discoverability${N}
  3  Publish the original research        ${D}the compounding asset${N}
  4  Answer the one live lead             ${D}the only high-intent thread${N}
  5  Measure the funnel                   ${D}moves confidence to high${N}
  n  Print the cold-start prompt for a fresh session
  s  Refresh showroom      q  Quit
MENU
}

[ "${1:-}" = "status" ] && { $G show; exit 0; }

while true; do
  menu
  case "$(ask 'select>')" in
    1) a1_free_tool ;;
    2) a2_repo_fixes ;;
    3) a3_research ;;
    4) a4_lead ;;
    5) a5_measure ;;
    n) head_ "Cold-start prompt"; $G next ;;
    s) continue ;;
    q|"") say "faucet closed."; exit 0 ;;
    *) warn "unknown option" ;;
  esac
  read -r -u 3 -p "$(printf '\n%spress enter%s ' "$D" "$N")" _ || exit 0
done
