#!/usr/bin/env python3

# This script does the following.
# 1. Reads in a current and changed yaml file
# 2. Finds changes between the two
# 3. Post them to slack

import argparse
from datetime import datetime
import requests
import random
import json
import os
import sys
import yaml
import tweepy


def read_yaml(filename):
    with open(filename, "r") as stream:
        content = yaml.load(stream, Loader=yaml.FullLoader)
    return content


def write_file(content, filename):
    with open(filename, "w") as fd:
        fd.write(content)


def get_parser():
    parser = argparse.ArgumentParser(description="Job Updater")

    description = "Find new jobs in a yaml"
    subparsers = parser.add_subparsers(
        help="actions",
        title="actions",
        description=description,
        dest="command",
    )

    update = subparsers.add_parser("update", help="find updates")
    update.add_argument(
        "--original",
        "-o",
        dest="original",
        help="the original file",
    )

    update.add_argument(
        "--deploy",
        "-d",
        dest="deploy",
        action="store_true",
        default=False,
        help="deploy to Slack",
    )

    update.add_argument(
        "--deploy-twitter",
        dest="deploy_twitter",
        action="store_true",
        default=False,
        help="deploy to Twitter (required api token/secret, and consumer token/secret",
    )

    update.add_argument(
        "--test",
        "-t",
        dest="test",
        action="store_true",
        default=False,
        help="do a test run instead",
    )

    update.add_argument(
        "--updated",
        "-u",
        dest="updated",
        help="The updated file",
    )

    update.add_argument(
        "--key",
        dest="key",
        help="The key to post to slack",
    )

    return parser


def get_twitter_client():
    envars = {}
    for envar in [
        "TWITTER_API_KEY",
        "TWITTER_API_SECRET",
        "TWITTER_CONSUMER_KEY",
        "TWITTER_CONSUMER_SECRET",
    ]:
        value = os.environ.get(envar)
        if not value:
            sys.exit("%s is not set, and required when twitter deploy is true!" % envar)
        envars[envar] = value

    return tweepy.Client(
        consumer_key=envars["TWITTER_CONSUMER_KEY"],
        consumer_secret=envars["TWITTER_CONSUMER_SECRET"],
        access_token=envars["TWITTER_API_KEY"],
        access_token_secret=envars["TWITTER_API_SECRET"],
    )


def main():
    parser = get_parser()

    def help(return_code=0):
        parser.print_help()
        sys.exit(return_code)

    # If an error occurs while parsing the arguments, the interpreter will exit with value 2
    args, extra = parser.parse_known_args()
    if not args.command:
        help()

    for filename in [args.original, args.updated]:
        if not os.path.exists(filename):
            sys.exit(f"{filename} does not exist.")

    # Cut out early if we are deploying to twitter but missing envars
    client = None
    if args.deploy_twitter:
        client = get_twitter_client()

    original = read_yaml(args.original)
    updated = read_yaml(args.updated)

    # Find new posts in updated
    previous = set()
    new = set()
    entries = set()
    for item in original:
        if args.key in item:
            previous.add(item[args.key])

    for item in updated:
        if args.key in item and item[args.key] not in previous:
            new.add(item[args.key])

        # Also keep list of all for test
        elif args.key in item and item[args.key]:
            entries.add(item[args.key])

    # Test uses all entries
    if args.test:
        new = entries
    elif not new:
        print("No new jobs found.")
        print("::set-output name=fields::[]")
        print("::set-output name=empty_matrix::true")
        print("::set-output name=matrix::[]")
        sys.exit(0)

    # Prepare the data
    webhook = os.environ.get("SLACK_WEBHOOK")
    if not webhook and args.deploy:
        sys.exit("Cannot find SLACK_WEBHOOK in environment.")

    headers = {"Content-type": "application/json"}
    matrix = []

    # Format into slack messages
    icons = [
        "⭐️",
        "😍️",
        "❤️",
        "👀️",
        "✨️",
        "🤖️",
        "💼️",
        "🤩️",
        "😸️",
        "😻️",
        "👉️",
        "🕶️",
        "🔥️",
        "💻️",
    ]
    for name in new:
        choice = random.choice(icons)
        message = "New Job! %s: %s" % (choice, name)

        # Add the job name to the matrix
        # IMPORTANT: emojis in output mess up the action
        matrix.append([name])
        data = {"text": message, "unfurl_links": True}
        print(data)

        # If we are instructed to deploy to twitter and have a client
        if args.deploy_twitter and client:
            message = "New #RSEng Job! %s: %s" % (choice, name)
            client.create_tweet(text=message)

        # Don't continue if testing
        if not args.deploy or args.test:
            continue

        response = requests.post(webhook, headers=headers, data=json.dumps(data))
        if response.status_code not in [200, 201]:
            print(response)
            sys.exit(
                "Issue with making POST request: %s, %s"
                % (response.reason, response.status_code)
            )

    print("::set-output name=fields::%s" % list(new))
    print("::set-output name=matrix::%s" % json.dumps(matrix))
    print("::set-output name=empty_matrix::false")
    print("matrix: %s" % json.dumps(matrix))
    print("group: %s" % list(new))


if __name__ == "__main__":
    main()
