
#!/usr/bin/env bash
set -e
ROOT_PROJECT="$(dirname "$(dirname "${BASH_SOURCE[0]}")")"

cd $ROOT_PROJECT
make generate-travis-config

list_envs() {
    cat .travis.yml | grep PYTH | cut -c2- | awk '{$1=$1;print}'
}


if type "xpanes" &> /dev/null; then
    declare -a CMDS
    while read -r ENV
    do
        CMDS+=("$ENV make docker-test")
    done < <(list_envs)

    xpanes --desync -t -e "${CMDS[@]}"
else
    list_envs | xargs -I {} bash -c "{} make docker-test"
fi
