#!/usr/bin/env bash
# merge-protected.sh — needs:owner PR'larni Claude merge qiladigan YAGONA yo'l (egasining 2026-11-22 qarori:
# "merge'larni to'liq o'zingga topshiraman"). Oddiy PR'lar uchun — scripts/merge-if-green.sh.
# Foydalanish: scripts/merge-protected.sh <PR raqami> [kutish_soniyasi (default 900)]
# Ishga tushirish har doim main'dagi nusxadan:  git fetch origin main && git show origin/main:scripts/merge-protected.sh | bash -s -- <PR>
#
# Merge faqat quyidagilar bajarilganda:
#   - PR ochiq, draft emas, branch claude/..., base main, konflikt yo'q;
#   - "needs:owner" label'i BOR (bo'lmasa merge-if-green.sh ishlatiladi), "hold" va "alert:*" yo'q;
#   - PR himoya mexanizmining o'ziga tegmaydi (pastdagi GUARDRAILS) — ularni faqat egasi merge qiladi;
#   - shu commit uchun ci va secret-scan muvaffaqiyatli; merge-gate tugagan (qizil bo'lishi mumkin — sababi
#     faqat needs:owner/himoyalangan fayllar ekani yuqoridagi tekshiruvlardan kelib chiqadi);
#   - merge-gate'dan boshqa barcha tekshiruvlar tugagan va qizil emas;
#   - ochiq alert:red-light bo'lsa — hech narsa merge qilinmaydi (tiklash PR'lari ham faqat merge-if-green.sh orqali).
# Merge "sha" bilan: tekshiruvdan keyin PR'ga yangi commit tushsa, GitHub merge'ni rad etadi.
# Chiqish kodlari: 0 — merge qilindi; 1 — xato/qizil yoki ruxsat yo'q; 2 — vaqt tugadi, tekshiruvlar hali tugamagan.
set -euo pipefail

PR="${1:?PR raqamini bering}"
WAIT="${2:-900}"
REQUIRED=(ci secret-scan)
# Himoya mexanizmining o'zi: bularni o'zgartirgan PR'ni faqat egasi merge qiladi (Claude o'z cheklovlarini o'zi yumshatmasin).
GUARDRAILS='^(\.claude/settings\.json|scripts/merge-[^/]*\.sh|\.github/workflows/(merge-gate|main-guard|known-good|secret-scan|weekly-backup)\.ya?ml)$'

url="$(git config --get remote.origin.url)"
REPO="$(printf '%s' "$url" | sed -E 's#\.git$##; s#^.*[:/]([^/]+/[^/]+)$#\1#')"
[[ "$REPO" == */* ]] || { echo "Repo nomini aniqlab bo'lmadi: $url" >&2; exit 1; }

red=$(gh api "repos/$REPO/issues?state=open&labels=alert:red-light&per_page=10" --jq '[.[] | select(.pull_request == null) | .number] | join(" ")')
[[ -z "$red" ]] || { echo "Qizil holat (issue: $red) — needs:owner PR'lar merge qilinmaydi." >&2; exit 1; }

files=$(gh api --paginate "repos/$REPO/pulls/$PR/files?per_page=100" --jq '.[] | .filename, (.previous_filename // empty)')
guard_hits=$(grep -E "$GUARDRAILS" <<<"$files" | sort -u | tr '\n' ' ' || true)
[[ -z "$guard_hits" ]] || { echo "PR himoya mexanizmini o'zgartiradi ($guard_hits) — faqat egasi merge qiladi." >&2; exit 1; }

deadline=$(( $(date +%s) + WAIT ))
while :; do
  pr_json="$(gh api "repos/$REPO/pulls/$PR")"
  state=$(jq -r .state <<<"$pr_json"); draft=$(jq -r .draft <<<"$pr_json")
  head_ref=$(jq -r .head.ref <<<"$pr_json"); base_ref=$(jq -r .base.ref <<<"$pr_json")
  sha=$(jq -r .head.sha <<<"$pr_json"); mergeable=$(jq -r .mergeable <<<"$pr_json")
  labels=$(jq -r '[.labels[].name] | join(",")' <<<"$pr_json")

  [[ "$state" == open ]] || { echo "PR #$PR ochiq emas ($state)." >&2; exit 1; }
  [[ "$draft" == false ]] || { echo "PR #$PR draft — avval ready for review qiling." >&2; exit 1; }
  [[ "$head_ref" == claude/* && "$base_ref" == main ]] || { echo "Branch qoidasi buzilgan: $head_ref -> $base_ref" >&2; exit 1; }
  [[ ",$labels," == *",needs:owner,"* ]] || { echo "needs:owner yo'q — scripts/merge-if-green.sh ishlating." >&2; exit 1; }
  if [[ ",$labels," == *",hold,"* || ",$labels," == *",alert:"* ]]; then
    echo "Taqiqlovchi label'lar: $labels" >&2; exit 1
  fi
  [[ "$mergeable" != false ]] || { echo "PR main bilan konflikt — avval main'ni birlashtiring." >&2; exit 1; }

  runs=$(gh api "repos/$REPO/actions/runs?head_sha=$sha&per_page=100")
  pending=0; failed=""
  for wf in "${REQUIRED[@]}" merge-gate; do
    r=$(jq -c --arg n "$wf" '[.workflow_runs[] | select(.name == $n)] | sort_by(.created_at) | last' <<<"$runs")
    if [[ "$r" == null ]]; then pending=1; continue; fi
    st=$(jq -r .status <<<"$r"); co=$(jq -r .conclusion <<<"$r")
    if [[ "$st" != completed ]]; then pending=1
    elif [[ "$wf" != merge-gate && "$co" != success ]]; then failed+="$wf($co) "; fi
  done

  checks=$(gh api "repos/$REPO/commits/$sha/check-runs?per_page=100")
  latest=$(jq -c '[.check_runs | group_by(.name)[] | sort_by(.started_at) | last | select(.name != "merge-gate")]' <<<"$checks")
  n_pending=$(jq '[.[] | select(.status != "completed")] | length' <<<"$latest")
  n_failed=$(jq -r '[.[] | select(.status == "completed" and (.conclusion | IN("success","skipped","neutral") | not)) | .name] | join(" ")' <<<"$latest")
  (( n_pending > 0 )) && pending=1
  [[ -n "$n_failed" ]] && failed+="$n_failed"

  if [[ -n "$failed" ]]; then echo "Qizil tekshiruvlar: $failed — merge yo'q." >&2; exit 1; fi
  if (( pending == 0 )); then break; fi
  if (( $(date +%s) >= deadline )); then echo "Tekshiruvlar ${WAIT}s ichida tugamadi — keyinroq qayta urinib ko'ring." >&2; exit 2; fi
  sleep 30
done

gh api -X PUT "repos/$REPO/pulls/$PR/merge" -f merge_method=merge -f sha="$sha" \
  -f commit_title="Merge PR #$PR (needs:owner, delegated: merge-protected)" --jq '"merged=\(.merged) \(.sha)"'
