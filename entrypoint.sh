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
JOBFILE="https://raw.githubusercontent.com/${INPUT_REPO}/${INPUT_MAIN}/${INPUT_FILENAME}"
TMP=$(mktemp -d)

BASENAME=$(basename ${INPUT_FILENAME})
wget ${JOBFILE} -O "${TMP}/${BASENAME}"
if [[ "$?" != "0" ]]; then
    printf "Issue getting previous job file ${JOBFILE}\n"
    exit 1
fi

JOBFILE="${TMP}/${BASENAME}"
if [[ ! -f "${JOBFILE}" ]]; then
    printf "${JOBFILE} does not exist.\n"
    exit 1
fi

# Required to have slack webhook in environment
if [ -z ${SLACK_WEBHOOK+x} ]; then 
    printf "Please export SLACK_WEBHOOK to use this integration\n"
    exit 1
fi

COMMAND="python ${ACTION_DIR}/find-updates.py update --key ${INPUT_KEY} --original ${JOBFILE} --updated ${INPUT_FILENAME}"

echo "${COMMAND}"

${COMMAND}
echo $?
