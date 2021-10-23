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

Add an GitHub workflow file in .github/workflows to specify the following:

```yaml
on:
 - pull_request: []

jobs:
  slack-poster:
    runs-on: ubuntu-latest
    name: Run Jobs Slack Poster
    steps:
      - uses: actions/checkout@v2

      - id: changed-files
        uses: jitterbit/get-changed-files@d06c756e3609dd3dd5d302dde8d1339af3f790f2
      - name: Check if Jobs Updated
        id: checker
        run: |
          echo "::set-output name=jobs_updated::false"
          for changed_file in ${{ steps.files.outputs.added_modified }}; do
              printf "Checking changed file ${changed_file}\n"
              if [[ "${changed_file}" == "_data/jobs.yml" ]]; then
                  printf "Found changed jobs!\n"
                  echo "::set-output name=jobs_updated::true"
              fi
          done

      - id: updater
        name: Job Updater
        if: ${{ steps.checker.outputs.jobs_updated == true }}
        uses: rseng/job-updater@main
        env:
          SLACK_WEBHOOK: ${{ secrets.SLACK_WEBHOOK }}
        with:        
          filename: "examples/jobs.yaml"
          key: "url"
          
      - run: echo ${{ steps.updater.outputs.fields }}
        shell: bash
```

