#!/usr/bin/env bash
# Print the tag of the next version, counted from the newest vMAJOR.MINOR.PATCH
# tag (pre-releases do not count). The Release workflow publishes with it.
# Usage: packaging/next_version.sh major|minor|patch [rc]
#   patch: v0.2.3 -> v0.2.4    minor: v0.2.3 -> v0.3.0    major: v0.2.3 -> v1.0.0
#   rc:    a pre-release of that version instead: v0.3.0-rc1, then v0.3.0-rc2...
set -euo pipefail

latest="$(git tag --list 'v*' | grep -E '^v[0-9]+\.[0-9]+\.[0-9]+$' | sort -V | tail -n 1 || true)"
IFS=. read -r major minor patch <<< "${latest:-v0.0.0}"
major="${major#v}"

case "${1:-}" in
    major) major=$((major + 1)) minor=0 patch=0 ;;
    minor) minor=$((minor + 1)) patch=0 ;;
    patch) patch=$((patch + 1)) ;;
    *)
        echo "Usage: $0 major|minor|patch [rc]" >&2
        exit 2
        ;;
esac
tag="v$major.$minor.$patch"

if [[ "${2:-}" == rc ]]; then
    last_rc="$(git tag --list "$tag-rc*" | sed "s/^$tag-rc//" | grep -E '^[0-9]+$' | sort -n | tail -n 1 || true)"
    tag="$tag-rc$((${last_rc:-0} + 1))"
fi

if git rev-parse --quiet --verify "refs/tags/$tag" > /dev/null; then
    echo "The tag $tag already exists" >&2
    exit 1
fi
echo "$tag"
