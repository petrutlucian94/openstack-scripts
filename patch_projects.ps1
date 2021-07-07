$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$env:Path += ";C:\Program Files\Git\cmd\"

function get_utc_iso8601_time() {
    Get-Date(Get-Date).ToUniversalTime() -uformat '+%Y-%m-%dT%H:%M:%S.000Z'
}

function safe_exec($cmd) {
    # The idea is to prevent powershell from treating stderr output
    # as an error when calling executables, relying on the return code
    # (which unfortunately doesn't always happen by default,
    # especially in case of remote sessions).
    log_message "cmd /c `"$cmd 2>&1`""
    cmd /c "$cmd 2>&1"
    if ($LASTEXITCODE) {
        throw "Command failed: $cmd"
    }
}

function log_message($message) {
    echo "[$(get_utc_iso8601_time)] $message"
}

function remove_dir($path)
{
    # Uses rmdir to overcome MAX_PATH limitation
    safe_exec "rmdir /S /Q $path"
}

function ensure_dir_exists($path) {
    if (!(test-path $path)) {
        mkdir $path | out-null
    }
}

function check_remove_dir($path)
{
    if (Test-Path $path) {
        remove_dir $path
    }
}

function git_clone_pull($path, $url, $ref="master", $shallow=$false)
{
    log_message "Cloning / pulling: $url, branch: $ref. Path: $path."

    pushd .
    try
    {
        if (!(Test-Path -path $path))
        {
            if ($shallow) {
                safe_exec "git clone -q -b $ref $url $path --depth=1"
            }
            else {
                safe_exec "git clone -q $url $path"
            }

            cd $path
        }
        else
        {
            cd $path

            safe_exec "git remote set-url origin $url"
            safe_exec "git fetch"
            safe_exec "git reset --hard"
            safe_exec "git clean -f -d"

            $outstandigCommits = $(git rev-list origin/stable/queens..HEAD).Count
            if ($outstandigCommits) {
                log_message "Found $outstandigCommits outstanding commits. Rolling back."
                safe_exec "git reset HEAD~$outstandigCommits --hard"
            }
        }

        safe_exec "git checkout $ref"

        if ((git tag) -contains $ref) {
            log_message "Got tag $ref instead of a branch."
            log_message "Skipping doing a pull."
        }
        elseif ($(git log -1 --pretty=format:"%H").StartsWith($ref)){
            log_message "Got a commit id instead of a branch."
            log_message "Skipping doing a pull."
        }
        else {
            safe_exec "git pull"
        }
    }
    finally
    {
        popd
    }
}

function pip_install($package, $allow_dev=$false, $update=$false)
{
    $dev = ""
    if ($allow_dev) {
        $dev = "--pre"
    }

    $u = ""
    if($update) {
        $u = "-U"
    }

    safe_exec "python -m pip install $dev $u $package"
}

function pull_install($path, $url, $branch="master", $requirements=$null)
{
    git_clone_pull $path $url $branch

    $update = $false
    if ($requirements)
    {
        # update the given project's requirements with the given requirements.
        safe_exec "update-requirements --source=`"$requirements`" $path"

        # NOTE(claudiub): we need to force the pip update because the given
        # project might already installed, in which case pip will skip the
        # installation (requirement already satisfied).
        $update = $true
    }

    pushd .
    try
    {
        cd $path

        # Remove build directory
        check_remove_dir "build"

        # Remove Python compiled files
        Get-ChildItem  -include "*.pyc" -recurse | foreach ($_) {remove-item $_.fullname}

        pip_install . -update $update
    }
    finally
    {
        popd
    }
}

function prepare_requirements_cap() {
    pull_install "requirements" "https://github.com/openstack/requirements" "stable/queens"

    $upper_constraints_file = $(Resolve-Path ".\requirements\upper-constraints.txt").Path
    # We comment out the following libs from the constraints file, ensuring
    # that we're going to stick with the requested versions.
    $(gc $upper_constraints_file) -replace '^(os-win|os-vif|cffi|lxml|netifaces)', '# $1' | sc $upper_constraints_file

    $env:PIP_CONSTRAINT = $upper_constraints_file
    log_message "Upper constraints file: $env:PIP_CONSTRAINT"
}

function apply_gerrit_patch($project, $ref) {
    safe_exec "git fetch https://git.openstack.org/openstack/$project $ref"
    safe_exec "git cherry-pick FETCH_HEAD"
}

function patch_projects() {
    log_message "Patching projects"

    $requirementsDir = "$pwd/requirements"

    log_message "Patching compute-hyperv"
    git_clone_pull "compute-hyperv" "https://github.com/openstack/compute-hyperv" "stable/queens"
    pushd compute-hyperv
    # metrics fix
    apply_gerrit_patch "compute-hyperv" "refs/changes/59/605359/7"

    # failover listener fix
    apply_gerrit_patch "compute-hyperv" "refs/changes/61/607861/1"

    # Sync requirements, otherwise some patches won't apply properly. We're overriding those anyway.
    apply_gerrit_patch "compute-hyperv" "refs/changes/61/551461/4"
    apply_gerrit_patch "compute-hyperv" "refs/changes/84/560484/1"
    apply_gerrit_patch "compute-hyperv" "refs/changes/06/555406/3"


    # Add distributed locks, fixing failover race conditions
    apply_gerrit_patch "compute-hyperv" "refs/changes/16/609016/2"
    apply_gerrit_patch "compute-hyperv" "refs/changes/17/609017/3"

    popd

    pip_install ".\compute-hyperv" -update $true

    log_message "Patching networking-hyperv"
    pull_install "networking-hyperv" "https://github.com/openstack/networking-hyperv" "stable/queens" "$requirementsDir"

    log_message "Patching os-win"
    git_clone_pull "os-win" "https://github.com/openstack/os-win" "master"
    safe_exec "update-requirements --source=`"$requirementsDir`" `"os-win`""
    pushd os-win
    # clusterutils refactoring
    apply_gerrit_patch "os-win" "refs/changes/11/607611/3"

    # port binding fix
    apply_gerrit_patch "os-win" "refs/changes/93/606893/1"
    popd

    pip_install ".\os-win" -update $true

}

# We don't care about other services, for now.
$openstackServices = @("nova-compute", "neutron-ovs-agent")

function stop_services() {
    log_message "Stoping services: $openstackServices"
    $openstackServices | % { stop-service $_ }
}

function start_services() {
    log_message "Starting services: $openstackServices"
    $openstackServices | % { start-service $_ }
}

$openstackProjectDir = "C:\OpenStack\build"
$pythonDir = "C:\Program Files\Cloudbase Solutions\OpenStack\Nova\Python27"
$pythonScriptsDir = "$pythonDir\Scripts"

# make sure that we're using the right python dir
$env:Path = "$pythonDir;$pythonScriptsDir;$env:Path"

ensure_dir_exists $openstackProjectDir
pushd $openstackProjectDir
try {
    prepare_requirements_cap

    stop_services
    patch_projects
    start_services
}
finally {
    popd
}
