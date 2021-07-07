#!/bin/bash -x

DATA_DIR="/opt/stack/data"
VOLUME_GROUP_NAME="stack-volumes-lvmdriver-1"
VOLUME_BACKING_FILE_SIZE=24G

. ~/devstack/lib/lvm

init_lvm_volume_group $VOLUME_GROUP_NAME $VOLUME_BACKING_FILE_SIZE
