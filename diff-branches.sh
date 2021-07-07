#!/bin/bash
# usage: cd $project; diff-branches.sh origin/master origin/stable/stein

FROM_BRANCH=$1
TO_BRANCH=$2
VERBOSE=${3:-"false"}

#FROM_BRANCH=${*: -2:1} # next to last argument
#TO_BRANCH=${*: -1:1} # last argument

SUBCOMMAND="show"

if [ $# -gt 3 ];
then
    COMMAND=$1
fi

if [ $# -gt 4 ];
then
    OPTS=$2
fi

from_branch_log="from_branch_log"
to_branch_log="to_branch_log"

git log --no-color --oneline --no-merges --topo-order --since="6 months ago" $FROM_BRANCH | grep -v "Updated from global requirements" > $from_branch_log
git log --no-color --oneline --no-merges --topo-order --since="1 year ago" $TO_BRANCH | grep -v "Updated from global requirements" > $to_branch_log

# comm separates output in 3 columns: unique to A, unique to B, present in both.
# -12 means that columns 1 and 2 are excluded from output.
comm -23 <(cat $from_branch_log | cut -b 9- | sort) <(cat $to_branch_log | cut -b 9- | sort) > diff.txt

commit_ids=()

while read commit
do
    line=`grep -F "$commit" $from_branch_log`
    commit_id=`echo $line | awk '{ print $1 }'`
    commit_ids+=( "$commit_id" )

    if [ $VERBOSE = "false" ];
    then
        echo $line
    fi
done < diff.txt

if [ $VERBOSE = "true" ];
then
    git show ${commit_ids[@]}
fi
