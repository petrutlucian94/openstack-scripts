# Neutron Hyperv Agent relies on switch port names to match the vnic name and port id.
#
# In case of vnics *manually* connected to vswitches, this won't be the case, which would
# trick Neutron into thinking that the ports are not connected to any vswitch and fail while
# attempting to reconnect them.
#
# Use this script to fix such port name mismatches, allowing Neutron to pick up the ports.
# Future versions of Neutron Hyperv Agent will gracefully handle such edge cases by default.
Param(
    [Parameter(Mandatory=$True)]
    [string]$PortId
)


$nic = gwmi -ns root/virtualization/v2 `
            -class "Msvm_SyntheticEthernetPortSettingData" | `
                ? ElementName -eq $PortId
$switch_port = gwmi -ns root/virtualization/v2 `
                    -class "Msvm_EthernetPortAllocationSettingData" | `
                         ? Parent -eq $nic
$switch_port_name = $switch_port.ElementName

if ($switch_port_name -ne $PortId) {
    Write-Host ("Switch port ElementName ($switch_port_name) does not " +
                "match port id ($PortId). Updating it.")

    $switch_port.ElementName = $PortId
    $vs_man_svc = gwmi -ns root/virtualization/v2 `
                       -class Msvm_VirtualSystemManagementService
    $vs_man_svc.ModifyResourceSettings($switch_port.GetText(2))
}
else {
    write-host "Switch port ElementName already matches the port id ($PortId)."
}
