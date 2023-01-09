#!/bin/bash

set -e

echo $PWD
ls

# Ensure the jobfile exists
if [[ ! -f "${INPUT_FILENAME}" ]]; then
    printf "${INPUT_FILENAME} does not exist.\n"
    exit 1
fi

# If we are verbatim given a previous filename, use it
if [ ! -z ${INPUT_PREVIOUS_FILENAME} ]; then 
    JOBFILE="${INPUT_PREVIOUS_FILENAME}"
else

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
fi

# Are we globally deploying?
DEPLOY=true
if [[ "${INPUT_DEPLOY}" == "false" ]]; then
    DEPLOY=false
fi

# Do not deploy ever on test
if [[ "${INPUT_TEST}" == "true" ]]; then
    printf "🚧️ This is a test run! Deploy set to false 🚧️\n"
    DEPLOY=false
fi

# If everything not unset and deploy twitter is true, we deploy!
DEPLOY_TWITTER=false
if [ ! -z ${TWITTER_API_KEY+x} ] && [ ! -z ${TWITTER_API_SECRET+x} ] && [ ! -z ${TWITTER_CONSUMER_KEY+x} ] && [ ! -z ${TWITTER_CONSUMER_SECRET+x} ] && [[ "${TWITTER_DEPLOY}" == "true" ]]; then
    DEPLOY_TWITTER=true
fi

# Likewise for mastodon
DEPLOY_MASTODON=false
if [ ! -z ${MASTODON_ACCESS_TOKEN+x} ] && [ ! -z ${MASTODON_API_BASE_URL+x} ] && [[ "${MASTODON_DEPLOY}" == "true" ]]; then
    DEPLOY_MASTODON=true
fi

# And Slack
DEPLOY_SLACK=false
if [ ! -z ${SLACK_WEBHOOK+x} ] && [[ "${SLACK_DEPLOY}" == "true" ]]; then
    DEPLOY_SLACK=true
fi

# And Discord
DEPLOY_DISCORD=false
if [ ! -z ${DISCORD_WEBHOOK+x} ] && [[ "${DISCORD_DEPLOY}" == "true" ]]; then
    DEPLOY_DISCORD=true
fi

# Alert the user everything that will happen
printf "  Global Deploy: ${DEPLOY}\n"
printf "Deploy Mastodon: ${DEPLOY_MASTODON}\n"
printf " Deploy Twitter: ${DEPLOY_TWITTER}\n"
printf " Deploy Discord: ${DEPLOY_DISCORD}\n"
printf "   Deploy Slack: ${DEPLOY_SLACK}\n"
printf "       Original: ${JOBFILE}\n"
printf "        Updated: ${INPUT_FILENAME}\n"
printf "        Hashtag: ${INPUT_HASHTAG}\n"
printf "         Unique: ${INPUT_UNIQUE}\n"
printf "           Keys: ${INPUT_KEYS}\n"
printf "           Test: ${INPUT_TEST}\n"


COMMAND="python ${ACTION_DIR}/find-updates.py update --keys ${INPUT_KEYS} --unique ${INPUT_UNIQUE} --original ${JOBFILE} --updated ${INPUT_FILENAME} --hashtag ${INPUT_HASHTAG}"

if [[ "${DEPLOY}" == "true" ]]; then
    COMMAND="${COMMAND} --deploy"
fi

if [[ "${INPUT_TEST}" == "true" ]]; then
    COMMAND="${COMMAND} --test"
fi

if [[ "${DEPLOY_TWITTER}" == "true" ]]; then
    COMMAND="${COMMAND} --deploy-twitter"
fi

if [[ "${DEPLOY_MASTODON}" == "true" ]]; then
    COMMAND="${COMMAND} --deploy-mastodon"
fi

if [[ "${DEPLOY_SLACK}" == "true" ]]; then
    COMMAND="${COMMAND} --deploy-slack"
fi

if [[ "${DEPLOY_DISCORD}" == "true" ]]; then
    COMMAND="${COMMAND} --deploy-discord"
fi

echo "${COMMAND}"

${COMMAND}
echo $?
