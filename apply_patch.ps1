param(
    [string]$project = $(throw "Please provide a project name (e.g. nova)"),
    [string]$service = $(throw "Please provide the service name."),
    [string]$ref     = $(throw "Please provide a patch ref."),
    [switch]$useCherryPick
    # false by default, e.g. usage -useCherryPick:$true
)

pushd .

$projectRepo = "C:\" + $project
$projPath = @("C:\Program Files (x86)\Cloudbase Solutions\OpenStack\$project\Python27\Lib\site-packages\$project",
              "C:\Program Files (x86)\Cloudbase Solutions\OpenStack\Python27\Lib\site-packages\$project")

net stop $service

foreach($path in $projPath){
   $pathExists = Test-Path $path
   if ($pathExists) {
    remove-item $path -Force -Recurse
   }
}

$pathExists = Test-Path $projectRepo

if (! $pathExists) {
    cd C:\
    git clone https://github.com/openstack/$project
}

cd $projectRepo

if ($useCherryPick){
    $action = "cherry-pick"
}
else{
    $action = "checkout"
}

git fetch https://review.openstack.org/openstack/$project $ref; git $action FETCH_HEAD

if ($LASTEXITCODE){
    throw "Could not fetch the requested change."
}

python.exe setup.py install

net start $service

popd 