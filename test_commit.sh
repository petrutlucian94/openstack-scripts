#!/bin/bash

IGNORED_RULES=${1:-""}
IGNORED_FILES=${2:-""}
PYTHON_BIN=${3:-"python"}

files=$(git show --pretty=format:"" --name-only --diff-filter='ACMRTUXB')

if [ ! -z "$IGNORED_FILES" ]; then
    files=$(echo $files | tr " " "\n" | grep -v "$IGNORED_FILES")
fi

echo "Files changed by last commit:"
echo $files

echo "Running flake8"

if [ -z "$IGNORED_RULES" ]; then
    $PYTHON_BIN -m flake8 $files
else
    $PYTHON_BIN -m flake8 $files --ignore $IGNORED_RULES
fi

if [[ $? != 0 ]]; then
   echo "Flake8 tests failed. Aborting running unit tests"
   exit 1
fi

echo "Running unit tests"
$PYTHON_BIN -m nose $files
