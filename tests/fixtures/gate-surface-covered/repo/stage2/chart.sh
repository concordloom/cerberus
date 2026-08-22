#!/bin/sh
# Stage 2 for the chart surface. That the chart exists, or was published, is not
# the same fact as what it installs: the image tag inside it is what reaches a
# cluster, and this reads it.
set -e
cd "$(dirname "$0")/.." || exit 1
app_version=$(sed -n 's/^appVersion: *//p' chart/Chart.yaml)
tag=$(sed -n 's/^ *tag: *//p' chart/values.yaml)
if [ -z "$app_version" ]; then
  echo "the chart declares no appVersion" >&2
  exit 1
fi
if [ -z "$tag" ]; then
  echo "the chart values declare no image tag" >&2
  exit 1
fi
if [ "$app_version" != "$tag" ]; then
  echo "the chart ships image tag $tag while its appVersion is $app_version" >&2
  exit 1
fi
