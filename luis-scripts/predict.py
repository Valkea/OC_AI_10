#! /usr/bin/env python3
# coding: utf-8

import json
import sys
import argparse

from azure.cognitiveservices.language.luis.runtime import LUISRuntimeClient
from msrest.authentication import CognitiveServicesCredentials

# IMPORT LUIS prediction KEY & ENDPOINT
try:
    with open("secrets.txt") as f:
        AUTHORING_KEY = f.readline().strip()
        AUTHORING_ENDPOINT = f.readline().strip()
        PREDICTION_KEY = f.readline().strip()
        PREDICTION_ENDPOINT = f.readline().strip()
except FileNotFoundError:
    print("The secrets.txt file with the PREDICTION_KEY and PREDICTION_ENDPOINT is missing")
    exit(0)


def predict(app_id, text):

    # --- Connect to LUIS api
    runtimeCredentials = CognitiveServicesCredentials(PREDICTION_KEY)
    clientRuntime = LUISRuntimeClient(
        endpoint=PREDICTION_ENDPOINT, credentials=runtimeCredentials
    )

    # --- Prepare query
    predictionRequest = {"query": text}

    # --- Predict
    predictionResponse = clientRuntime.prediction.get_slot_prediction(
        app_id, "Production", predictionRequest  # Production == slot name
    )

    return predictionResponse


def parseResponse(response):

    print(f"> Received query: {response.query}\n")

    print(f"> Top intent: {response.prediction.top_intent}")
    print(f"> Sentiment: {response.prediction.sentiment}")

    print("> Intents: ")
    for intent in response.prediction.intents:
        print(f"\t{json.dumps(intent)}")

    print(f"> Entities: {response.prediction.entities}")


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('-t', "--text", type=str, required=True, help="The text we want to send to LUIS.ai")
    parser.add_argument('--app_id', type=str, help="The LUIS.ai application ID")

    args = parser.parse_args()

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        exit(0)

    app_id = "3fd78054-d5ab-4617-824a-2feee4341d13"
    text = "I want two small pepperoni pizzas with more salsa"

    if "app_id" in args:
        app_id = args.app_id
    if "text" in args:
        text = args.text

    print(f"AppID: {app_id} \nQUERY: {text}\n")

    try:
        pred = predict(app_id, text)
        parseResponse(pred)
    except Exception as e:
        print(e)
