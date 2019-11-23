
#!/usr/bin/env bash
set -e
ROOT_PROJECT="$(dirname "$(dirname "${BASH_SOURCE[0]}")")"

cd $ROOT_PROJECT
make generate-travis-config
cat .travis.yml | grep PYTH | cut -c2- | awk '{$1=$1;print}' | xargs -I {} bash -c "{} make docker-test"
