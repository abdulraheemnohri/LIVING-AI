#!/usr/bin/env bash
# Download the configured LiteRT-LM model safely. No download occurs unless invoked.
set -Eeuo pipefail
cd "$(dirname "$0")/.."
if [[ -f .env ]]; then set -a; . ./.env; set +a; fi

repo_id="${LIVING_AI_LITERTLM_REPO:-litert-community/gemma-4-E2B-it-litert-lm}"
filename="${LIVING_AI_LITERTLM_FILENAME:-gemma-4-E2B-it.litertlm}"
model_path="${LIVING_AI_LITERTLM_MODEL_PATH:-models/litert/gemma-4-E2B-it.litertlm}"
max_bytes="${LIVING_AI_MODEL_MAX_DOWNLOAD_BYTES:-5000000000}"
mkdir -p "$(dirname "$model_path")"

if [[ -s "$model_path" ]]; then
  echo "Model already exists: $model_path"
  echo "Use a separate reviewed process to replace it; this downloader will not overwrite it."
  exit 0
fi
command -v curl >/dev/null 2>&1 || { echo "curl is required." >&2; exit 1; }
command -v df >/dev/null 2>&1 || { echo "df is required." >&2; exit 1; }

url="https://huggingface.co/$repo_id/resolve/main/$filename"
dest_dir="$(dirname "$model_path")"
tmp="$model_path.part"
available_kb="$(df -Pk "$dest_dir" | awk 'NR==2 {print $4}')"
if [[ -z "$available_kb" || "$available_kb" -lt 5500000 ]]; then
  echo "Insufficient free disk space (need approximately 5.5 GB free). Check: $dest_dir" >&2
  exit 1
fi

echo "Model repository: $repo_id"
echo "Destination: $model_path"
echo "This may download multiple gigabytes and use mobile data."
echo "If this is not the intended model, stop now."
curl --fail --location --retry 3 --retry-delay 2 --continue-at - \
  --max-filesize "$max_bytes" --output "$tmp" "$url"
[[ -s "$tmp" ]] || { echo "Downloaded file is empty." >&2; exit 1; }
# Guard against an HTML error page being saved as a model.
if head -c 256 "$tmp" | grep -Eiq '<!doctype html|<html'; then
  echo "The server returned HTML instead of a model artifact; refusing installation." >&2
  rm -f "$tmp"
  exit 1
fi
mv -- "$tmp" "$model_path"
sha256sum "$model_path" > "$model_path.sha256"
echo "Download finished. SHA-256 recorded at $model_path.sha256"
echo "Verify the hash against the official model publisher before relying on this artifact."
