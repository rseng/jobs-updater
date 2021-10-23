#!/bin/bash

set -e

echo $PWD
ls 

# Ensure the jobfile exists
if [[ ! -f "${INPUT_FILENAME}" ]]; then
    printf "${INPUT_FILENAME} does not exist.\n"
    exit 1
fi

# Wget the comparison file
JOBFILE="https://raw.githubusercontent.com/${{ github.repository }}/${INPUT_MAIN}/${INPUT_FILENAME}"
TMP=$(mktemp -d)

wget ${JOBFILE} -O "${TMP}/${INPUT_FILENAME}"
if [[ "$?" != "0" ]]; then
    printf "Issue getting previous job file ${JOBFILE}\n"
    exit 1
fi

# Required to have slack webhook in environment
if [ -z ${SLACK_WEBHOOK+x} ]; then 
    printf "Please export SLACK_WEBHOOK to use this integration\n"
    exit 1
fi

COMMAND="python ${ACTION_DIR}/find-updates.py update --key ${INPUT_KEY} --original ${TMP}/${INPUT_FILENAME} --updated ${INPUT_FILENAME}"

echo "${COMMAND}"

${COMMAND}
echo $?
