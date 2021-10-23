# Jobs Updater

The jobs updater is a simple GitHub action application to, given some trigger
and a yaml file with a list of jobs (or other links):

```
- name: My Job
  ...
  url: https://my-job.org/12345
```

The action will inspect the file to determine lines that are newly added,
given a field of interest, extract this field, and then post to a Slack channel.
This is custom made to help the [US-RSE](https://github.com/US-RSE/usrse.github.io) site
to have job updates posted to slack!

## Quickstart

1. Create a [webhook app](https://api.slack.com/messaging/webhooks#getting_started) and grab the URL and save to `SLACK_WEBHOOK` in your repository secrets.
2. Add a GitHub workflow file, as shown below, with your desired triggers.

For more details on the above, keep reading.

## 1. Slack Setup

You'll want to [follow the instructions here](https://api.slack.com/messaging/webhooks#getting_started) to create a webhook
for your slack community and channel of interest. This usually means first creating an application and selecting your slack
community.

1. For the kind of app, you'll want to select the first box for incoming webhooks.

You can then use the example to test the webhook with curl

```bash
curl -X POST -H 'Content-type: application/json' --data '{"text":"Hello, World!"}' YOUR_WEBHOOK_URL_HERE
```

Click on "Add new webhook to workspace" and then test the provided url with the bot. Copy the webhook URL
and put it in a safe place. We will want to keep this URL as a secret in our eventual GitHub workflow.


## 2. Usage

Add an GitHub workflow file in .github/workflows to specify the following. Note that
the workflow below will do the check and update on the opening of a pull request.

```yaml
on:
  pull_request:
    paths:
      - '_data/jobs.yml'
    types:
      - opened
    branches:
      - main

jobs:
  slack-poster:
    runs-on: ubuntu-latest
    name: Run Jobs Slack Poster
    steps:
      - uses: actions/checkout@v2
      - id: updater
        name: Job Updater
        uses: rseng/jobs-updater@main
        env:
          SLACK_WEBHOOK: ${{ secrets.SLACK_WEBHOOK }}
        with:        
          filename: "_data/jobs.yml"
          key: "url"
          
      - run: echo ${{ steps.updater.outputs.fields }}
        shell: bash
```

