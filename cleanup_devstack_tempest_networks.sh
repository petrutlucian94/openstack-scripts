for f in `neutron router-list | grep -v router1 | awk 'FNR>=3 {print $2}'`; do neutron router-gateway-clear $f; done
for f in `neutron router-list | grep -v router1 | awk 'FNR>=3 {print $2}'`; do \
    neutron router-interface-delete $f $(openstack router show $f -c interfaces_info -f value | cut -d " " -f 2  | tr -d '",'); \
done
for f in `neutron router-list | grep -v router1 | awk 'FNR>=3 {print $2}'`; do neutron router-delete $f; done
for f in `neutron subnet-list | grep -v private | grep -v public | awk 'FNR>=3 {print $2}'`; do neutron subnet-delete $f; done
for f in `neutron net-list | grep -v private | grep -v public | awk 'FNR>=3 {print $2}'`; do neutron net-delete $f; done
