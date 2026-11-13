#!/usr/bin/env bash
# Run once in Google Cloud Shell while logged in as an authorized project administrator.
# This creates a keyless Google -> GitHub trust relationship, NOT a Firebase deployment.
set -euo pipefail
PROJECT=higi-8b169
PROJECT_NUMBER=568171802572
ACCOUNT=higi-rtdb-deployer@higi-8b169.iam.gserviceaccount.com
POOL=github-higi
PROVIDER=rtdb-rules
ROLE=higiRtdbRulesDeployer
REPO=higicrossword/Higi-Releases
REPO_ID=1376018131
WORKFLOW_REF="${REPO}/.github/workflows/higi-rtdb-rules.yml@refs/heads/main"
CONDITION="assertion.repository=='${REPO}' && assertion.repository_id=='${REPO_ID}' && assertion.ref=='refs/heads/main' && assertion.event_name=='workflow_dispatch' && assertion.environment=='higi-firebase-rules' && assertion.workflow_ref=='${WORKFLOW_REF}'"
ACTUAL="$(gcloud projects describe "$PROJECT" --format='value(projectNumber)')"
[[ "$ACTUAL" == "$PROJECT_NUMBER" ]] || { echo 'BLOCKED: project number mismatch'; exit 1; }
gcloud config set project "$PROJECT" >/dev/null
gcloud services enable iam.googleapis.com iamcredentials.googleapis.com sts.googleapis.com --project="$PROJECT"
if ! gcloud iam service-accounts describe "$ACCOUNT" --project="$PROJECT" >/dev/null 2>&1; then
  gcloud iam service-accounts create higi-rtdb-deployer --project="$PROJECT" --display-name='Higi GitHub RTDB rules publisher (keyless)'
fi
if gcloud iam roles describe "$ROLE" --project="$PROJECT" >/dev/null 2>&1; then
  EXISTING="$(gcloud iam roles describe "$ROLE" --project="$PROJECT" --format='value(includedPermissions)' | tr ';' '\n' | sort)"
  # Do not silently replace or broaden an existing role. Audit it before use.
  [[ -n "$EXISTING" ]] || { echo 'BLOCKED: existing custom role has no readable permissions'; exit 1; }
else
  gcloud iam roles create "$ROLE" --project="$PROJECT" \
    --title='Higi RTDB rules deployment' \
    --description='RTDB update includes full database write capability; only use behind restricted WIF and GitHub approval' \
    --permissions=firebasedatabase.instances.get,firebasedatabase.instances.update,firebase.projects.get,resourcemanager.projects.get \
    --stage=GA
fi
gcloud projects add-iam-policy-binding "$PROJECT" \
  --member="serviceAccount:${ACCOUNT}" \
  --role="projects/${PROJECT}/roles/${ROLE}" >/dev/null
if ! gcloud iam workload-identity-pools describe "$POOL" --project="$PROJECT" --location=global >/dev/null 2>&1; then
  gcloud iam workload-identity-pools create "$POOL" --project="$PROJECT" --location=global --display-name='Higi GitHub Actions'
fi
if gcloud iam workload-identity-pools providers describe "$PROVIDER" --project="$PROJECT" \
    --workload-identity-pool="$POOL" --location=global >/dev/null 2>&1; then
  CURRENT="$(gcloud iam workload-identity-pools providers describe "$PROVIDER" --project="$PROJECT" \
    --workload-identity-pool="$POOL" --location=global --format='value(attributeCondition)')"
  [[ "$CURRENT" == "$CONDITION" ]] || { echo 'BLOCKED: existing OIDC provider condition differs'; exit 1; }
else
  gcloud iam workload-identity-pools providers create-oidc "$PROVIDER" \
    --project="$PROJECT" --location=global --workload-identity-pool="$POOL" \
    --display-name='Higi RTDB rules guarded workflow' \
    --issuer-uri=https://token.actions.githubusercontent.com \
    --attribute-mapping='google.subject=assertion.sub,attribute.repository=assertion.repository' \
    --attribute-condition="$CONDITION"
fi
gcloud iam service-accounts add-iam-policy-binding "$ACCOUNT" --project="$PROJECT" \
  --role=roles/iam.workloadIdentityUser \
  --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL}/attribute.repository/${REPO}" >/dev/null
echo 'COMPLETE: Google Cloud identity configured; no Firebase rules were published.'
echo 'Next: create the GitHub environment higi-firebase-rules with REQUIRED reviewers.'
echo 'Add an environment secret HIGI_RULES_BACKUP_PASSWORD (32+ characters, never paste in chat).'
