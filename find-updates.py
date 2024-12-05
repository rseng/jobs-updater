#!/usr/bin/env python3

# This script does the following.
# 1. Reads in a current and changed yaml file
# 2. Finds changes between the two
# 3. Post them to slack
# 4. Optionally post them to Twitter, Mastodon, Discord, etc.

import argparse
import json
import os
import random
import sys

import requests
import tweepy
import yaml
from atproto import Client as BlueskyClient
from atproto import client_utils
from mastodon import Mastodon

# Shared headers for slack / discord
headers = {"Content-type": "application/json"}
success_codes = [200, 201, 204]


icons = [
    "⭐️",
    "😍️",
    "❤️",
    "👀️",
    "✨️",
    "🤖️",
    "😎️",
    "💼️",
    "🤩️",
    "🥑",
    "🥳",
    "🎉",
    "😸️",
    "😻️",
    "👉️",
    "🕶️",
    "🔥️",
    "💻️",
]


def read_yaml(filename):
    """
    Read yaml from file.
    """
    with open(filename, "r") as stream:
        content = yaml.load(stream, Loader=yaml.FullLoader)
    return content


def write_file(content, filename):
    """
    Write yaml to file.
    """
    with open(filename, "w") as fd:
        fd.write(content)


def set_env_and_output(name, value):
    """
    helper function to echo a key/value pair to the environment file

    Parameters:
    name (str)  : the name of the environment variable
    value (str) : the value to write to file
    """
    for env_var in ("GITHUB_ENV", "GITHUB_OUTPUT"):
        environment_file_path = os.environ.get(env_var)
        print("Writing %s=%s to %s" % (name, value, env_var))

        with open(environment_file_path, "a") as environment_file:
            environment_file.write("%s=%s\n" % (name, value))


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
        "--hashtag",
        dest="hashtag",
        default="#RSEng",
        help="A hashtag (starting with #) to include in the post, defaults to #RSEng",
    )

    update.add_argument(
        "--deploy-twitter",
        dest="deploy_twitter",
        action="store_true",
        default=False,
        help="deploy to Twitter (required api token/secret, and consumer token/secret)",
    )

    update.add_argument(
        "--deploy-slack",
        dest="deploy_slack",
        action="store_true",
        default=False,
        help="deploy to Slack (required webhook URL in environment)",
    )

    update.add_argument(
        "--deploy-discord",
        dest="deploy_discord",
        action="store_true",
        default=False,
        help="deploy to Discord (required webhook URL in environment)",
    )

    update.add_argument(
        "--deploy-bluesky",
        dest="deploy_bluesky",
        action="store_true",
        default=False,
        help="deploy to BlueSky (required user/pass in environment)",
    )

    update.add_argument(
        "--deploy-mastodon",
        dest="deploy_mastodon",
        action="store_true",
        default=False,
        help="deploy to Mastodon (required access token, and API base URL)",
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
        "--keys",
        dest="keys",
        help="The keys (comma separated list) to post to slack or Twitter",
    )

    update.add_argument(
        "--unique",
        dest="unique",
        help="The key to use to determine uniqueness (defaults to url)",
        default="url",
    )

    return parser


def get_required_envars(required, client_name):
    """
    Get and return a set of required environment variables.
    """
    envars = {}
    for envar in required:
        value = os.environ.get(envar)
        if not value:
            sys.exit(
                f"{envar} is not set, and required when {client_name} deploy is true!"
            )
        envars[envar] = value
    return envars


def get_twitter_client():
    """
    Get a Twitter client, also ensure all needed envars are provided.
    """
    required = [
        "TWITTER_API_KEY",
        "TWITTER_API_SECRET",
        "TWITTER_CONSUMER_KEY",
        "TWITTER_CONSUMER_SECRET",
    ]
    envars = get_required_envars(required, "twitter")
    return tweepy.Client(
        consumer_key=envars["TWITTER_CONSUMER_KEY"],
        consumer_secret=envars["TWITTER_CONSUMER_SECRET"],
        access_token=envars["TWITTER_API_KEY"],
        access_token_secret=envars["TWITTER_API_SECRET"],
    )


def get_bluesky_client():
    """
    Get a BlueSky (atproto) client, also ensure all needed envars are provided.
    """
    required = [
        "BLUESKY_PASSWORD",
        "BLUESKY_EMAIL",
    ]
    client = BlueskyClient()
    envars = get_required_envars(required, "bluesky")
    client.login(envars["BLUESKY_EMAIL"], envars["BLUESKY_PASSWORD"])
    return client


def get_mastodon_client():
    """
    Get a Mastodon client, requiring a token and base URL.
    """
    required = [
        "MASTODON_ACCESS_TOKEN",
        "MASTODON_API_BASE_URL",
    ]
    envars = get_required_envars(required, "mastodon")
    return Mastodon(
        access_token=envars["MASTODON_ACCESS_TOKEN"],
        api_base_url=envars["MASTODON_API_BASE_URL"],
    )


def prepare_post(entry, keys, without_url=False):
    """
    Prepare the post.

    There should be a descriptor for all fields except for url.
    """
    post = ""
    for key in keys:
        if key in entry:
            # For BlueSky, we include the url separately with the title
            if key in ["url", "title"] and without_url:
                continue
            if key == "url":
                post = post + entry[key] + "\n"
            else:
                post = post + key.capitalize() + ": " + entry[key] + "\n"
    return post


def deploy_slack(webhook, message):
    """
    Deploy a post to slack
    """
    data = {"text": message, "unfurl_links": True}
    response = requests.post(webhook, headers=headers, data=json.dumps(data))
    if response.status_code not in success_codes:
        print(response)
        sys.exit(
            "Issue with making Slack POST request: %s, %s"
            % (response.reason, response.status_code)
        )


def deploy_bluesky(client, entry, keys, hashtag):
    """
    Deploy to bluesky. We add the job link separately.
    """
    tb = client_utils.TextBuilder()

    # Prepare the post, but without the url
    post = prepare_post(entry, keys, without_url=True)
    choice = random.choice(icons)
    message = f"New {hashtag} Job! {choice}\n"
    print(message)

    # Add the text to the textbuilder
    tb.text(message)
    tb.link(entry["title"], entry["url"])
    tb.text("\n" + post)
    response = client.send_post(tb)
    print(f"Posted to bluesky {response.uri}: {response.cid}")


def deploy_discord(webhook, message):
    """
    Deploy a post to Discord
    """
    data = {"content": message}
    response = requests.post(webhook, headers=headers, data=json.dumps(data))
    if response.status_code not in success_codes:
        print(response)
        sys.exit(
            "Issue with making Discord POST request: %s, %s"
            % (response.reason, response.status_code)
        )


def deploy_twitter(client, message):
    """
    Deploy to Twitter.

    Twitter supports emojis, so we add them back.
    """
    try:
        client.create_tweet(text=message)
    except Exception as e:
        print(f"Issue posting tweet: {e}, and length is {len(message)}")


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

    # Deploying to Twitter?
    twitter_client = None
    if args.deploy_twitter:
        twitter_client = get_twitter_client()

    mastodon_client = None
    if args.deploy_mastodon:
        mastodon_client = get_mastodon_client()

    # Deploying to BlueSky?
    bluesky_client = None
    if args.deploy_bluesky:
        bluesky_client = get_bluesky_client()

    # Prepare webhooks for slack and mastodon
    slack_webhook = os.environ.get("SLACK_WEBHOOK")
    discord_webhook = os.environ.get("DISCORD_WEBHOOK")

    # Get original and updated jobs
    original = read_yaml(args.original)
    updated = read_yaml(args.updated)

    # Parse keys into list
    keys = [x for x in args.keys.split(",") if x]

    # Find new posts in updated
    previous = set()
    missing_count = 0
    for item in original:
        if args.unique in item:
            previous.add(item[args.unique])
        else:
            missing_count += 1

    # Warn the user if some are missing the unique key
    if missing_count:
        print(f"Warning: key {args.unique} is missing in {missing_count} items.")

    # Create a lookup by the unique id
    new = []
    entries = []
    for item in updated:
        if args.unique in item and item[args.unique] not in previous:
            new.append(item)

        # Also keep list of all for test
        elif args.unique in item and item[args.unique]:
            entries.append(item)

    # Test uses all entries
    if args.test:
        new = entries
    elif not new:
        print("No new jobs found.")
        set_env_and_output("fields", "[]")
        set_env_and_output("matrix", "[]")
        set_env_and_output("empty_matrix", "true")
        sys.exit(0)

    matrix = []

    for entry in new:
        # Prepare the post
        post = prepare_post(entry, keys)
        choice = random.choice(icons)
        message = f"New {args.hashtag} Job! {choice}: {post}"
        newline_message = f"New {args.hashtag} Job! {choice}\n{post}"
        print(message)

        # Convert dates, etc. back to string
        filtered = {}
        for k, v in entry.items():
            try:
                filtered[k] = json.dumps(v)
            except:
                continue

        # Add the job name to the matrix
        # IMPORTANT: emojis in output can mess up some of the services
        matrix.append(filtered)

        # Don't continue if testing or global deploy is false
        if not args.deploy or args.test is True:
            continue

        # If we are instructed to deploy to twitter and have a client
        if args.deploy_twitter and twitter_client:
            deploy_twitter(twitter_client, newline_message)

        if args.deploy_bluesky and bluesky_client:
            deploy_bluesky(bluesky_client, entry, keys, args.hashtag)

        # If we are instructed to deploy to mastodon and have a client
        if args.deploy_mastodon and mastodon_client:
            mastodon_client.toot(status=message)

        # Deploy to Slack
        if slack_webhook is not None and args.deploy_slack:
            deploy_slack(slack_webhook, message)

        # Deploy to Discord
        if discord_webhook is not None and args.deploy_discord:
            deploy_discord(discord_webhook, message)

    set_env_and_output("fields", json.dumps(keys))
    set_env_and_output("matrix", json.dumps(matrix))
    set_env_and_output("empty_matrix", "false")
    print("matrix: %s" % json.dumps(matrix))
    print("group: %s" % new)


if __name__ == "__main__":
    main()
