#!/bin/bash
TOP_DIR=~/devstack

set -e

source $TOP_DIR/functions-common
source $TOP_DIR/functions
source $TOP_DIR/lib/stack

extract_localrc_section $TOP_DIR/local.conf $TOP_DIR/localrc $TOP_DIR/.localrc.auto
source $TOP_DIR/stackrc

source $TOP_DIR/lib/libraries
source $TOP_DIR/lib/database
source $TOP_DIR/lib/rpc_backend

source $TOP_DIR/lib/apache
source $TOP_DIR/lib/tls

source $TOP_DIR/lib/infra
source $TOP_DIR/lib/libraries
source $TOP_DIR/lib/lvm
source $TOP_DIR/lib/horizon
source $TOP_DIR/lib/keystone
source $TOP_DIR/lib/glance
source $TOP_DIR/lib/nova
source $TOP_DIR/lib/placement
source $TOP_DIR/lib/cinder
source $TOP_DIR/lib/swift
source $TOP_DIR/lib/neutron
source $TOP_DIR/lib/ldap
source $TOP_DIR/lib/dstat
source $TOP_DIR/lib/tcpdump
source $TOP_DIR/lib/etcd3

# ~/devstack/.stackenv must first be moved or updated
source ~/devstack/openrc admin admin

source /opt/stack/octavia/devstack/settings

echo "Initializing DB backends"
initialize_database_backends

echo "stack install"
. /opt/stack/octavia/devstack/plugin.sh stack install
echo "echo post-config"
. /opt/stack/octavia/devstack/plugin.sh stack post-config
echo "stack extra"
. /opt/stack/octavia/devstack/plugin.sh stack extra

