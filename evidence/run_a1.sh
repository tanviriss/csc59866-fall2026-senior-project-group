#!/usr/bin/env bash
export PATH="$HOME/Downloads/terraform_1.17.2_darwin_arm64:$PATH"

cd "$(dirname "$0")/a1-project" || exit 1
OUT="../a1-experiment.txt"
: > "$OUT"

log() { echo "$@" | tee -a "$OUT"; }

run() {
  label="$1"; shift
  log ""
  log "=== $label ==="
  log "\$ $*"
  "$@" >> "$OUT" 2>&1
  log "exit code: $?"
}

log "Date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
log "OS: $(sw_vers -productName) $(sw_vers -productVersion)"

run "Terraform version" terraform version

rm -f demo.txt terraform.tfstate terraform.tfstate.backup

run "init" terraform init -input=false

run "apply (creates demo.txt)" terraform apply -auto-approve -input=false

run "Run 1: no change" terraform plan -refresh-only -detailed-exitcode -input=false

rm -f demo.txt
log ""
log "(demo.txt deleted by hand, outside Terraform)"

run "Run 2: after the hand change" terraform plan -refresh-only -detailed-exitcode -input=false

run "Run 3: same command again" terraform plan -refresh-only -detailed-exitcode -input=false

terraform plan -refresh-only -detailed-exitcode -input=false -json > run4.json 2>&1
code=$?

log ""
log "=== Run 4: JSON output after the hand change ==="
log "exit code: $code"
log "lines mentioning resource_drift: $(grep -c resource_drift run4.json)"

cat run4.json >> "$OUT"
rm -f run4.json

run "Run 5: failure case (folder does not exist)" terraform -chdir=does-not-exist plan -refresh-only -detailed-exitcode -input=false
