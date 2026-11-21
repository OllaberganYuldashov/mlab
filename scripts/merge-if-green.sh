#!/usr/bin/env bash
# merge-if-green.sh — Claude PR'ni faqat shu skript orqali merge qiladi.
# Foydalanish: scripts/merge-if-green.sh <PR raqami> [kutish_soniyasi (default 900)]
#
# Merge faqat quyidagilar bajarilganda:
#   - PR ochiq, draft emas, branch claude/..., base main;
#   - "needs:owner", "hold" yoki "alert:*" label'lari yo'q;
#   - PR'ning oxirgi commit'i uchun merge-gate, ci va secret-scan workflow'lari muvaffaqiyatli;
#   - shu commit'dagi boshqa barcha tekshiruvlar ham tugagan va qizil emas;
#   - ochiq alert:red-light bo'lsa: faqat claude/rollback-* PR va egasining "Ruxsat: ..." izohi bilan.
# Merge "sha" bilan qilinadi: tekshiruvdan keyin PR'ga yangi commit tushsa, GitHub merge'ni rad etadi.
# Chiqish kodlari: 0 — merge qilindi; 1 — xato/qizil (merge yo'q); 2 — vaqt tugadi, tekshiruvlar hali tugamagan.
set -euo pipefail

PR="${1:?PR raqamini bering}"
WAIT="${2:-900}"
REQUIRED=(merge-gate ci secret-scan)

url="$(git config --get remote.origin.url)"
REPO="$(printf '%s' "$url" | sed -E 's#\.git$##; s#^.*[:/]([^/]+/[^/]+)$#\1#')"
[[ "$REPO" == */* ]] || { echo "Repo nomini aniqlab bo'lmadi: $url" >&2; exit 1; }

# Qizil chiroq: ochiq alert:red-light bo'lsa, faqat egasi "Ruxsat: ..." yozgan tiklash PR'i (claude/rollback-*) merge qilinadi
OWNER="${REPO%%/*}"
red=$(gh api "repos/$REPO/issues?state=open&labels=alert:red-light&per_page=10" --jq '[.[] | select(.pull_request == null) | .number] | join(" ")')
if [[ -n "$red" ]]; then
  head_ref=$(gh api "repos/$REPO/pulls/$PR" --jq .head.ref)
  [[ "$head_ref" == claude/rollback-* ]] || { echo "Qizil holat (issue: $red) — faqat ruxsat berilgan tiklash PR'i merge qilinadi." >&2; exit 1; }
  ok=0
  for n in $red; do
    if gh api "repos/$REPO/issues/$n/comments?per_page=100" \
        | jq -r --arg o "$OWNER" '.[] | select((.user.login | ascii_downcase) == ($o | ascii_downcase)) | .body' \
        | grep -qE '^[[:space:]]*Ruxsat:'; then ok=1; fi
  done
  (( ok == 1 )) || { echo "Qizil holat: egasining \"Ruxsat: ...\" izohi yo'q — merge yo'q." >&2; exit 1; }
fi

deadline=$(( $(date +%s) + WAIT ))
while :; do
  pr_json="$(gh api "repos/$REPO/pulls/$PR")"
  state=$(jq -r .state <<<"$pr_json"); draft=$(jq -r .draft <<<"$pr_json")
  head_ref=$(jq -r .head.ref <<<"$pr_json"); base_ref=$(jq -r .base.ref <<<"$pr_json")
  sha=$(jq -r .head.sha <<<"$pr_json"); mergeable=$(jq -r .mergeable <<<"$pr_json")
  bad_labels=$(jq -r '[.labels[].name | select(. == "needs:owner" or . == "hold" or startswith("alert:"))] | join(",")' <<<"$pr_json")

  [[ "$state" == open ]] || { echo "PR #$PR ochiq emas ($state)." >&2; exit 1; }
  [[ "$draft" == false ]] || { echo "PR #$PR draft — avval ready for review qiling." >&2; exit 1; }
  [[ "$head_ref" == claude/* && "$base_ref" == main ]] || { echo "Branch qoidasi buzilgan: $head_ref -> $base_ref" >&2; exit 1; }
  [[ -z "$bad_labels" ]] || { echo "Taqiqlovchi label'lar: $bad_labels — merge'ni egasi hal qiladi." >&2; exit 1; }
  [[ "$mergeable" != false ]] || { echo "PR main bilan konflikt — avval rebase qiling." >&2; exit 1; }

  runs=$(gh api "repos/$REPO/actions/runs?head_sha=$sha&per_page=100")
  pending=0; failed=""
  for wf in "${REQUIRED[@]}"; do
    # Shu commit uchun shu workflow'ning eng oxirgi run'i (label o'zgarsa merge-gate qayta ishlaydi)
    r=$(jq -c --arg n "$wf" '[.workflow_runs[] | select(.name == $n)] | sort_by(.created_at) | last' <<<"$runs")
    if [[ "$r" == null ]]; then pending=1; continue; fi
    st=$(jq -r .status <<<"$r"); co=$(jq -r .conclusion <<<"$r")
    if [[ "$st" != completed ]]; then pending=1
    elif [[ "$co" != success ]]; then failed+="$wf($co) "; fi
  done

  checks=$(gh api "repos/$REPO/commits/$sha/check-runs?per_page=100")
  # Bir xil nomli tekshiruvlardan faqat eng oxirgisi hisobga olinadi
  latest=$(jq -c '[.check_runs | group_by(.name)[] | sort_by(.started_at) | last]' <<<"$checks")
  n_pending=$(jq '[.[] | select(.status != "completed")] | length' <<<"$latest")
  n_failed=$(jq -r '[.[] | select(.status == "completed" and (.conclusion | IN("success","skipped","neutral") | not)) | .name] | join(" ")' <<<"$latest")
  (( n_pending > 0 )) && pending=1
  [[ -n "$n_failed" ]] && failed+="$n_failed"

  if [[ -n "$failed" ]]; then echo "Qizil tekshiruvlar: $failed — merge yo'q." >&2; exit 1; fi
  if (( pending == 0 )); then break; fi
  if (( $(date +%s) >= deadline )); then echo "Tekshiruvlar ${WAIT}s ichida tugamadi — keyingi run'da qayta urinib ko'ring." >&2; exit 2; fi
  sleep 30
done

gh api -X PUT "repos/$REPO/pulls/$PR/merge" -f merge_method=merge -f sha="$sha" \
  -f commit_title="Merge PR #$PR (merge-gate: auto)" --jq '"merged=\(.merged) \(.sha)"'
