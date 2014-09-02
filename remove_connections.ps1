$sessions = iscsicli.exe SessionList | where {$_ -match "(Session Id *: .*)"}
ForEach($session in $sessions){
	$line = $session | where {$_ -match "(Session Id *: )(?<session_id>.*)"}
	$id = $matches.session_id
	echo "Removing session $id"
	iscsicli.exe logouttarget $id
}