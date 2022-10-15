#! /usr/bin/env python3
# coding: utf-8

import time
import sys
import requests
import json
import argparse

# IMPORT LUIS authoring KEY & ENDPOINT
try:
    with open("secrets.txt") as f:
        AUTHORING_KEY = f.readline().strip()
        AUTHORING_ENDPOINT = f.readline().strip()
        PREDICTION_KEY = f.readline().strip()
        PREDICTION_ENDPOINT = f.readline().strip()

except FileNotFoundError:
    print(
        "The secrets.txt file with the AUTHORING_KEY and AUTHORING_ENDPOINT is missing"
    )
    exit(0)


class Evaluating:
    def __init__(self, app_id):
        self.app_id = app_id
        self.operation_id = None
        self.slot_name = "production"
        self.base_url = f"{PREDICTION_ENDPOINT}/luis/v3.0-preview/apps/{self.app_id}/slots/{self.slot_name}/evaluations"

        self.headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Ocp-Apim-Subscription-Key": PREDICTION_KEY
        }

    def _load_json(self, training_json_path):

        try:
            with open(training_json_path) as file:
                return json.load(file)
        except FileNotFoundError as e:
            print(e)
            exit(0)

    def send_batch(self, validation_json_path):

        print(f"Push a batch of validation samples from {validation_json_path}")

        validation_json = {"LabeledTestSetUtterances": self._load_json(validation_json_path)}

        response = requests.post(self.base_url, headers=self.headers, json=validation_json)

        if response:
            self.operation_id = response.json()['operationId']
            print(f"OK --> operationId: {self.operation_id}")
            self.check_status()
            return True

        else:
            print("Error: Status Code", response.status_code)
            return False

    def check_status(self):

        print("Evaluating ", end="", flush=True)

        waiting = True
        while waiting:

            response = requests.get(f"{self.base_url}/{self.operation_id}/status", headers=self.headers)

            if response:
                if response.json()['status'] == 'succeeded':
                    print(" done!")
                    waiting = False
                else:
                    print(".", end="", flush=True)
                    time.sleep(1)
            else:
                print("Error: Status Code", response.status_code)
                return False

        self.get_results()

    def get_results(self):

        print("Fetch results")

        response = requests.get(f"{self.base_url}/{self.operation_id}/result", headers=self.headers)

        if response:
            print("--> JSON:")
            print(json.dumps(response.json(), indent=2))
            return True

        else:
            print("Error: Status Code", response.status_code)
            return False


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('-p', "--valid_path", type=str, required=True, help="The path to the validation json faile")
    parser.add_argument('--app_id', type=str, required=True, help="The LUIS.ai application ID")

    args = parser.parse_args()

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        exit(0)

    if "app_id" in args:
        app_id = args.app_id
    if "valid_path" in args:
        valid_path = args.valid_path

    evaluate = Evaluating(app_id)
    evaluate.send_batch(valid_path)

