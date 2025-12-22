#!/bin/bash
set -e
sum1=$(md5sum arch_check.py | awk '{print $1}')
sum2=$(md5sum pyproject.toml | awk '{print $1}')
sed -i "s/^md5sums=('SKIP' 'SKIP')/md5sums=('$sum1' '$sum2')/" PKGBUILD