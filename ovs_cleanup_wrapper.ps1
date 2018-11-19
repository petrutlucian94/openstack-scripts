Param(
    [switch]$help
)

$helpString = @"
This helper script allows running 'neutron-ovs-cleanup' exactly once per
boot and is intended to be called before launching 'nova-compute'.

This will ensure that stale OVS ports are cleaned up, without affecting
running instances. Note that 'neutron-ovs-cleanup' will remove all the ports
from pre-configured bridges (except for ports that contain certain tags),
while Nova will re-add the VM ports when the serivce starts.

Usage: $PSCommandPath <neutron-ovs-cleanup.exe> [<ovs_cleanup_arg_0> ... <ovs_cleanup_arg_n>]
"@

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$OSRegKey = "hklm://Software/Cloudbase solutions/OpenStack"
$LastExecutionTimestampKey = "LastOvsCleanupTime"
$EventLogSource = "neutron-ovs-cleanup"
$EventLogName = "Application"

# We're ignoring possible errors as the log source may already exist.
New-EventLog -LogName $EventLogName -Source $EventLogSource `
             -ErrorAction SilentlyContinue

function get_utc_iso8601_time() {
    Get-Date(Get-Date).ToUniversalTime() -uformat '+%Y-%m-%dT%H:%M:%S.000Z'
}

function log_eventlog($message, $eventType) {
     Write-EventLog -LogName $EventLogName -Source $EventLogSource `
                    -EntryType $eventType -Message $message `
                    -EventId 1
}

function log_message($message) {
    log_eventlog $message "Information"
    write-host "[$(get_utc_iso8601_time)] $message"
}

function log_error($message) {
    log_eventlog $message "Error"
    write-host  -ForegroundColor red "[$(get_utc_iso8601_time)] ERROR: $message"
}

function set_property($name, $value) {
    set-itemproperty -name $name -path $OSRegKey -value $value
}

function get_property($name, $expectExisting=$false){
    try {
        get-itempropertyvalue -name $name -path $OSRegKey
    }
    catch {
        if ($expectExisting) {
            throw
        }
    }
}

function get_boot_time() {
    [Management.ManagementDateTimeConverter]::ToDateTime(
        $(gwmi win32_operatingsystem).LastBootUpTime)
}

function get_last_execution_timestamp() {
    $timestamp = get_property $LastExecutionTimestampKey
    if ($timestamp) {
        [Management.ManagementDateTimeConverter]::ToDateTime($timestamp)
    }
}

function set_execution_timestamp($datetime) {
    if (!($datetime)){
        $datetime = get-date
    }

    $timestamp = [Management.ManagementDateTimeConverter]::ToDmtfDateTime($datetime)
    set_property $LastExecutionTimestampKey $timestamp
}

if ($help) {
    write-host $helpString
    exit 0
}
elseif ($args.Count -lt 1) {
    log_error ("Expecting at least one argument, providing the " +
               "'neutron-ovs-cleanup' binary path.")
    write-host $helpString
    exit 1
}

try {
    mkdir $OSRegKey -Force
    $bootTime = get_boot_time
    $lastExecutionTime = get_last_execution_timestamp

    log_message "Last OVS cleanup time: $lastExecutionTime"
    log_message "Host boot time: $bootTime"

    if ($lastExecutionTime -gt $bootTime) {
        log_message "OVS cleanup already performed since the host was started."
    }
    else {
        log_message "Performing OVS cleanup."
        set_execution_timestamp
        & $args[0] $args[1..$args.Count]
    }
}
catch {
    $formatstring = "{0} : {1}`n{2}`n" +
                    "    + CategoryInfo          : {3}`n" +
                    "    + FullyQualifiedErrorId : {4}`n"
    $fields = $_.InvocationInfo.MyCommand.Name,
              $_.ErrorDetails.Message,
              $_.InvocationInfo.PositionMessage,
              $_.CategoryInfo.ToString(),
              $_.FullyQualifiedErrorId

    $err = $formatstring -f $fields
    log_error "$err"
    exit 1
}
