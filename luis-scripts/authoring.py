#! /usr/bin/env python3
# coding: utf-8

import os
import time
import uuid
import sys
import json
import pathlib

from azure.cognitiveservices.language.luis.authoring import LUISAuthoringClient
from azure.cognitiveservices.language.luis.authoring.models import (
    ApplicationCreateObject,
    WordListObject,
)
from azure.cognitiveservices.language.luis.authoring.models._models_py3 import (
    ErrorResponseException,
)
from msrest.authentication import CognitiveServicesCredentials

# IMPORT LUIS authoring KEY & ENDPOINT
try:
    with open(pathlib.Path(os.path.dirname(__file__), "secrets.txt")) as f:
        AUTHORING_KEY = f.readline().strip()
        AUTHORING_ENDPOINT = f.readline().strip()

except FileNotFoundError:
    print(
        "The secrets.txt file with the AUTHORING_KEY and AUTHORING_ENDPOINT is missing"
    )
    exit(0)


def get_grandchild_id(model, childName, grandChildName=None):

    theseChildren = next(
        filter((lambda child: child.name == childName), model.children)
    )
    returnId = theseChildren

    if grandChildName is not None:
        theseGrandchildren = next(
            filter((lambda child: child.name == grandChildName), theseChildren.children)
        )

        returnId = theseGrandchildren.id

    return returnId


class Authoring:
    def __init__(self):
        self.client = None
        self.app_id = None
        self.versionId = None

    def connect(self):

        self.client = LUISAuthoringClient(
            AUTHORING_ENDPOINT, CognitiveServicesCredentials(AUTHORING_KEY)
        )

        print("Connect to LUIS.ai")

    def create_app(self, appName, versionId, culture):

        print("Create Entities ", end="")

        self.versionId = versionId

        appDefinition = ApplicationCreateObject(
            name=appName, initial_version_id=versionId, culture=culture
        )

        self.app_id = self.client.apps.add(appDefinition)
        print(f"--> a LUIS.ai app with ID {self.app_id} was created")

    def create_intent(self, intentName):

        print(f"Create Intent: {intentName}")
        self.client.model.add_intent(self.app_id, self.versionId, intentName)

    def create_entities(self):

        print("Create Entities")

        # --- Add Prebuilt entities
        self.client.model.add_prebuilt(
            self.app_id,
            self.versionId,
            prebuilt_extractor_names=["money", "geographyV2", "datetimeV2"],
        )

        # --- Add Closed list entities
        airports = [
            WordListObject(
                canonical_form="New York",
                list=[
                    "NY",
                    "New York",
                    "New-York",
                    "NewYork",
                    "new york",
                    "new-york",
                    "newyork",
                    "NEW YORK",
                    "NEW-YORK",
                    "NEWYORK",
                ],
            ),
            WordListObject(canonical_form="Paris", list=["paris", "PARIS"]),
            WordListObject(
                canonical_form="London",
                list=["london", "LONDON", "Londres", "londres", "LONDRES"],
            ),
            WordListObject(canonical_form="Milan", list=["milan", "MILAN"]),
        ]

        self.client.model.add_closed_list(
            self.app_id,
            self.versionId,
            sub_lists=airports,
            name="Airport",
            custom_headers=None,
            raw=False,
        )

        # --- Add Machine-learned entities
        mlEntityDefinition = [{"name": "Airport", "children": []}]

        ent_From = self.client.model.add_entity(
            self.app_id, self.versionId, name="From", children=mlEntityDefinition
        )
        ent_To = self.client.model.add_entity(
            self.app_id, self.versionId, name="To", children=mlEntityDefinition
        )
        ent_openDate = self.client.model.add_entity(
            self.app_id, self.versionId, name="openDate", children=None
        )
        ent_closeDate = self.client.model.add_entity(
            self.app_id, self.versionId, name="closeDate", children=None
        )
        ent_budget = self.client.model.add_entity(
            self.app_id, self.versionId, name="budget", children=None
        )

        # --- Add model as feature to subentity models
        self.client.features.add_entity_feature(
            self.app_id,
            self.versionId,
            ent_From,
            {"model_name": "geographyV2", "is_required": False},
        )

        self.client.features.add_entity_feature(
            self.app_id,
            self.versionId,
            ent_To,
            {"model_name": "geographyV2", "is_required": False},
        )

        self.client.features.add_entity_feature(
            self.app_id,
            self.versionId,
            ent_openDate,
            {"model_name": "datetimeV2", "is_required": False},
        )

        self.client.features.add_entity_feature(
            self.app_id,
            self.versionId,
            ent_closeDate,
            {"model_name": "datetimeV2", "is_required": False},
        )

        self.client.features.add_entity_feature(
            self.app_id,
            self.versionId,
            ent_budget,
            {"model_name": "money", "is_required": False},
        )

        # --- Get entity and subentities & set features
        modelObject = self.client.model.get_entity(
            self.app_id, self.versionId, ent_From
        )
        ent_FromAirport = get_grandchild_id(modelObject, "Airport").id

        self.client.features.add_entity_feature(
            self.app_id,
            self.versionId,
            ent_FromAirport,
            {"model_name": "Airport", "is_required": True},
        )

        modelObject = self.client.model.get_entity(self.app_id, self.versionId, ent_To)
        ent_ToAirport = get_grandchild_id(modelObject, "Airport").id

        self.client.features.add_entity_feature(
            self.app_id,
            self.versionId,
            ent_ToAirport,
            {"model_name": "Airport", "is_required": True},
        )

        # --- Add patterns
        # TODO

        # --- Add Phraselist
        # TODO

    def _load_training_json(self, training_json_path):

        try:
            with open(training_json_path) as file:
                return json.load(file)
        except FileNotFoundError as e:
            print(e)
            exit(0)

    def _split_training_json(self, training_json, step_size=100):
        for index in range(0, len(training_json), step_size):
            yield training_json[index : index + step_size]

    def add_training(self, training_json):

        print("Push one training sample")

        # Enable nested children to allow using multiple models with the same name.
        self.client.examples.add(
            self.app_id,
            self.versionId,
            training_json,
            {"enableNestedChildren": True},
        )

    def add_trainings(self, training_json_path):

        print(f"Push a batch of training samples from {training_json_path}")

        batch_size = 100
        training_json = self._load_training_json(training_json_path)
        for i, subbatch in enumerate(
            self._split_training_json(training_json, batch_size)
        ):

            print(f"--> send batch #{i} [from {i*batch_size} to {(i+1)*batch_size}]")

            # Enable nested children to allow using multiple models with the same name.
            self.client.examples.batch(
                self.app_id,
                self.versionId,
                subbatch,
                {"enableNestedChildren": True},
            )

    def train_model(self):
        # get_status returns a list of training statuses, one for each model.
        # Loop through them and make sure all are done.

        self.client.train.train_version(self.app_id, self.versionId)
        waiting = True
        print("Training ", end="", flush=True)
        while waiting:
            info = self.client.train.get_status(self.app_id, self.versionId)

            waiting = any(
                map(
                    lambda x: "Queued" == x.details.status
                    or "InProgress" == x.details.status,
                    info,
                )
            )

            if waiting:
                print(".", end="", flush=True)
                time.sleep(1)
            else:
                print(" done!")
                waiting = False

    def publish(self):
        # Mark the app as public so we can query it using any prediction endpoint.
        # Note: For production scenarios, we need to use the LUIS prediction endpoint.

        print("Publish ", end="", flush=True)

        try:
            self.client.apps.update_settings(self.app_id, is_public=True)

            responseEndpointInfo = self.client.apps.publish(
                self.app_id, self.versionId, is_staging=False
            )

            print(responseEndpointInfo)
        except ErrorResponseException as e:
            print(f"publish error: {e}")


if __name__ == "__main__":

    if len(sys.argv) == 1:
        print(
            "Please provide the path to the JSON file containing the training uterrances"
        )
        exit(0)

    authoring = Authoring()
    appName = "FlightBooking " + str(
        uuid.uuid4()
    )  # We use a UUID to avoid name collisions.

    authoring.connect()
    authoring.create_app(appName, "0.1", "en-us")
    authoring.create_intent("BookFlight")
    # authoring.create_intent("Cancel")
    authoring.create_intent("Greet")
    authoring.create_intent("Quit")
    authoring.create_entities()
    authoring.add_trainings(sys.argv[1])
    authoring.train_model()
    authoring.publish()
