#!/usr/bin/env python3

# This script does the following.
# 1. Reads in a current and changed yaml file
# 2. Finds changes between the two
# 3. Post them to slack

import argparse
from datetime import datetime
import requests
import logging
import os
import sys
import yaml

logging.basicConfig(level=logging.INFO)

def read_yaml(filename):
    with open(filename, 'r') as stream:
        content = yaml.load(stream, Loader=yaml.FullLoader)
    return content


def write_file(content, filename):
    with open(filename, "w") as fd:
        fd.write(content)


def get_parser():
    parser = argparse.ArgumentParser(
        description="Job Updater"
    )

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

    updated.add_argument(
        "--updated",
        "-u",
        dest="updated",
        help="The updated file",
    )

    updated.add_argument(
        "--key",
        dest="key",
        help="The key to post to slack",
    )

    return parser


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

    original = read_yaml(args.original)
    updated = read_yaml(args.updated)
        
    # Find new posts in updated
    previous = set()
    new = set()
    for item in original:
        if args.key in item:
            previous.add(item[args.key])

    for item in updated:
        if args.key in item and item[args.key] not in previous:
            new.add(item[args.key])

    if not new:
        print("No new jobs found.")
        print("::set-output name=fields::[]")
        sys.exit(0)

    # Format into slack message
    message = [" - %s" % name for name in new]
    word = "Jobs!"
    if new == 1:
        word = "Job!"
    message = "New %s ⭐️\n" % word + "\n".join(message) 

    # Prepare the data
    webhook = os.environ.get("SLACK_WEBHOOK")
    if not webhook:
        sys.exit("Cannot find SLACK_WEBHOOK in environment.")
    headers = {"Content-type": "application/json"}
    data = {"text": message}
    response = requests.post(webhook, headers=headers, data=data)

    if response.status_code not in [200, 201]:
        print(response)
        sys.exit("Issue with making POST request: %s" % response.reason)    
      
    print("::set-output name=fields::%s" % list(new))

if __name__ == "__main__":
    main()
