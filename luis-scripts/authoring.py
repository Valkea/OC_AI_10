#! /usr/bin/env python3
# coding: utf-8

import time
import uuid

from azure.cognitiveservices.language.luis.authoring import LUISAuthoringClient
from azure.cognitiveservices.language.luis.authoring.models import ApplicationCreateObject
from msrest.authentication import CognitiveServicesCredentials

# IMPORT LUIS authoring KEY & ENDPOINT
try:
    with open("secrets.txt") as f:
        AUTHORING_KEY = f.readline().strip()
        AUTHORING_ENDPOINT = f.readline().strip()

except FileNotFoundError:
    print(
        "The secrets.txt file with the AUTHORING_KEY and AUTHORING_ENDPOINT is missing"
    )
    exit(0)


def get_grandchild_id(model, childName, grandChildName):

    theseChildren = next(
        filter((lambda child: child.name == childName), model.children)
    )
    theseGrandchildren = next(
        filter((lambda child: child.name == grandChildName), theseChildren.children)
    )

    grandChildId = theseGrandchildren.id

    return grandChildId


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

        self.versionId = versionId

        appDefinition = ApplicationCreateObject(
            name=appName, initial_version_id=versionId, culture=culture
        )

        self.app_id = self.client.apps.add(appDefinition)
        print(f"A LUIS.ai app with ID {self.app_id} was created")

    def create_intent(self, intentName):

        self.client.model.add_intent(self.app_id, self.versionId, intentName)

        print(f"Create Intent: {intentName}")

    def create_entities(self):

        # --- Add Prebuilt entity
        self.client.model.add_prebuilt(
            self.app_id, self.versionId, prebuilt_extractor_names=["number"]
        )

        # --- Define machine-learned entity
        mlEntityDefinition = [
            {
                "name": "Pizza",
                "children": [{"name": "Quantity"}, {"name": "Type"}, {"name": "Size"}],
            },
            {"name": "Toppings", "children": [{"name": "Type"}, {"name": "Quantity"}]},
        ]

        modelId = self.client.model.add_entity(
            self.app_id, self.versionId, name="Pizza order", children=mlEntityDefinition
        )

        # --- Define phraselist - add phrases as significant vocabulary to app
        phraseList = {
            "enabledForAllModels": False,
            "isExchangeable": True,
            "name": "QuantityPhraselist",
            "phrases": "few,more,extra",
        }

        phraseListId = self.client.features.add_phrase_list(
            self.app_id, self.versionId, phraseList
        )

        # --- Get entity and subentities
        modelObject = self.client.model.get_entity(self.app_id, self.versionId, modelId)
        toppingQuantityId = get_grandchild_id(modelObject, "Toppings", "Quantity")
        pizzaQuantityId = get_grandchild_id(modelObject, "Pizza", "Quantity")

        # --- Add model as feature to subentity model
        prebuiltFeatureRequiredDefinition = {
            "model_name": "number",
            "is_required": True,
        }
        self.client.features.add_entity_feature(
            self.app_id, self.versionId, pizzaQuantityId, prebuiltFeatureRequiredDefinition
        )

        # --- Add model as feature to subentity model
        prebuiltFeatureNotRequiredDefinition = {"model_name": "number"}
        self.client.features.add_entity_feature(
            self.app_id,
            self.versionId,
            toppingQuantityId,
            prebuiltFeatureNotRequiredDefinition,
        )

        # --- Add phrase list as feature to subentity model
        phraseListFeatureDefinition = {
            "feature_name": "QuantityPhraselist",
            "model_name": None,
        }
        self.client.features.add_entity_feature(
            self.app_id, self.versionId, toppingQuantityId, phraseListFeatureDefinition
        )

        print("Create Entities")

    def add_trainings(self, training_json):

        # Enable nested children to allow using multiple models with the same name.
        self.client.examples.add(
            self.app_id,
            self.versionId,
            training_json,
            {"enableNestedChildren": True},
        )

        print("Push Trainings")

    def train_model(self):
        # get_status returns a list of training statuses, one for each model.
        # Loop through them and make sure all are done.

        self.client.train.train_version(self.app_id, self.versionId)
        waiting = True
        print("Traing ", end='')
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
                print(".", end='')
                time.sleep(1)
            else:
                print(" done!")
                waiting = False

    def publish(self):
        # Mark the app as public so we can query it using any prediction endpoint.
        # Note: For production scenarios, we need to use the LUIS prediction endpoint.
        self.client.apps.update_settings(self.app_id, is_public=True)

        responseEndpointInfo = self.client.apps.publish(
            self.app_id, self.versionId, is_staging=False
        )
        print(f"Publish: {responseEndpointInfo}")


if __name__ == "__main__":

    authoring = Authoring()
    appName = "Contoso Pizza Company " + str(uuid.uuid4())  # We use a UUID to avoid name collisions.
    versionId = "0.1"
    culture = "en-us"
    intentName = "OrderPizzaIntent"
    training_json = "Blop"

    # Define labeled example
    labeledExampleUtteranceWithMLEntity = {
        "text": "I want two small seafood pizzas with extra cheese.",
        "intentName": intentName,
        "entityLabels": [
            {
                "startCharIndex": 7,
                "endCharIndex": 48,
                "entityName": "Pizza order",
                "children": [
                    {
                        "startCharIndex": 7,
                        "endCharIndex": 30,
                        "entityName": "Pizza",
                        "children": [
                            {
                                "startCharIndex": 7,
                                "endCharIndex": 9,
                                "entityName": "Quantity",
                            },
                            {
                                "startCharIndex": 11,
                                "endCharIndex": 15,
                                "entityName": "Size",
                            },
                            {
                                "startCharIndex": 17,
                                "endCharIndex": 23,
                                "entityName": "Type",
                            },
                        ],
                    },
                    {
                        "startCharIndex": 37,
                        "endCharIndex": 48,
                        "entityName": "Toppings",
                        "children": [
                            {
                                "startCharIndex": 37,
                                "endCharIndex": 41,
                                "entityName": "Quantity",
                            },
                            {
                                "startCharIndex": 43,
                                "endCharIndex": 48,
                                "entityName": "Type",
                            },
                        ],
                    },
                ],
            }
        ],
    }


    authoring.connect()
    authoring.create_app(appName, versionId, culture)
    authoring.create_intent(intentName)
    authoring.create_entities()
    authoring.add_trainings(labeledExampleUtteranceWithMLEntity)
    authoring.train_model()
    authoring.publish()
