#!/bin/sh

IMAGES="/home/ubuntu/images"
LOG_DIR=$IMAGES"/nova_test.log"
hypervisor='nova:WIN-H64MI10EC61'

image_names=("dynamic" "fixed")
types=("vhd" "vhdx")

echo "" > $LOG_DIR
echo "Instance   :   Status" >> $LOG_DIR

for type in "${types[@]}"
do
    ext=".$type"
    for image in "${image_names[@]}"
    do
        image_name=$image"_"$type
        snapshot="snapshot_$image_name"
        image_path=$IMAGES"/"$image$ext
        glance image-create --name=$image_name --disk-format=vhd --container-format=bare < $image_path --progres

        nova boot $image_name --image=$image_name --flavor=1 --availability-zone=$hypervisor --poll

        nova image-create $image_name $snapshot --poll
        nova boot $snapshot --image=$snapshot --flavor=1 --availability-zone=$hypervisor --poll

        status1=`nova show $image_name | awk 'FNR == 4 {print $4}'`
        status2=`nova show $snapshot | awk 'FNR == 4 {print $4}'`

        echo "$image_name   :   $status1"  >> $LOG_DIR
        echo "$snapshot   :   $status2" >> $LOG_DIR

        nova delete $image_name
        nova delete $snapshot
        glance image-delete $image_name
        glance image-delete $snapshot
    done
done