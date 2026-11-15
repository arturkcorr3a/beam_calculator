#!/usr/bin/env bash
# Pack the app folder built by build_linux.sh (dist/beam_calculator/) as an RPM
# in dist/. Needs rpmbuild (Fedora: sudo dnf install rpm-build).
# Usage: packaging/build_rpm.sh [version]      (default: git describe)
set -euo pipefail

cd "$(dirname "$0")/.."
repo="$(pwd)"
version="${1:-$(git describe --tags --always --dirty)}"
# RPM versions take no "-" and no leading "v": v0.1.0-rc1 becomes 0.1.0~rc1
rpm_version="${version#v}"
rpm_version="${rpm_version//-/\~}"

if [[ ! -x dist/beam_calculator/beam_calculator ]]; then
    echo "dist/beam_calculator/ not found: run packaging/build_linux.sh first" >&2
    exit 1
fi

rpmbuild -bb packaging/linux/beam_calculator.rpm.spec \
    --define "_topdir $repo/build/rpm" \
    --define "_rpmdir $repo/dist" \
    --define "_build_name_fmt %%{NAME}-%%{VERSION}-%%{RELEASE}.%%{ARCH}.rpm" \
    --define "app_version $rpm_version" \
    --define "repo_dir $repo" \
    --define "app_dir $repo/dist/beam_calculator"
ls dist/beam_calculator-"$rpm_version"-*.rpm
