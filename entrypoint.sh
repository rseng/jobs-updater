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
PARENT_SHA=$(git log --pretty=%P -n 1 ${CURRENT_SHA} | cut -d ' ' -f 1)
JOBFILE="https://raw.githubusercontent.com/${INPUT_REPO}/${PARENT_SHA}/${INPUT_FILENAME}"
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
    printf "Warning, SLACK_WEBHOOK not found, will not deploy to slack.\n"
fi

# Are we deploying?
DEPLOY=true
if [[ "INPUT_DEPLOY" == "false" ]]; then
    DEPLOY=false
fi

# Do not deploy ever on test
if [[ "INPUT_TEST" == "true" ]]; then
    printf "🚧️ This is a test run! Deploy set to false 🚧️\n"
    DEPLOY=false
fi

if [[ "${DEPLOY}" == "true" ]]; then
  COMMAND="python ${ACTION_DIR}/find-updates.py update --key ${INPUT_KEY} --original ${JOBFILE} --updated ${INPUT_FILENAME} --deploy"
else
  COMMAND="python ${ACTION_DIR}/find-updates.py update --key ${INPUT_KEY} --original ${JOBFILE} --updated ${INPUT_FILENAME}"
fi

echo "${COMMAND}"

${COMMAND}
echo $?
