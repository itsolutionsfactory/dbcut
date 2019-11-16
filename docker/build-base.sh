#!/bin/bash
set -e
set -x

export LC_ALL=C
export DEBIAN_FRONTEND=noninteractive

apt-get update

if apt-cache show 'default-libmysqlclient-dev' 2>/dev/null | grep -q '^Version:'; then
    apt-get install -y --no-install-recommends default-libmysqlclient-dev
else
    apt-get install -y --no-install-recommends libmysqlclient-dev
fi

apt-get install -y libpq-dev make

# Cleanup
apt-get clean -y
apt-get autoclean -y
apt-get autoremove -y
apt-get purge -y --auto-remove

rm -f /etc/dpkg/dpkg.cfg.d/02apt-speedup
rm -rf /tmp/* /var/tmp/*
rm -rf /var/lib/apt/lists/*
rm -rf /root/.cache
rm -rf /var/cache/debconf/*-old
rm -rf /var/lib/apt/lists/*
