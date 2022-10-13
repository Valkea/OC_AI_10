# import json
import time
import uuid

from azure.cognitiveservices.language.luis.authoring import LUISAuthoringClient
from azure.cognitiveservices.language.luis.authoring.models import ApplicationCreateObject
# from azure.cognitiveservices.language.luis.runtime import LUISRuntimeClient
from msrest.authentication import CognitiveServicesCredentials
# from functools import reduce


# IMPORT LUIS authoring KEY & ENDPOINT
try:
    with open("secrets.txt") as f:
        AUTHORING_KEY = f.readline().strip()
        AUTHORING_ENDPOINT = f.readline().strip()

except FileNotFoundError:
    print("The secrets.txt file with the AUTHORING_KEY and AUTHORING_ENDPOINT is missing")
    exit(0)


# We use a UUID to avoid name collisions.
appName = "Contoso Pizza Company " + str(uuid.uuid4())
versionId = "0.1"
intentName = "OrderPizzaIntent"
culture = "en-us"

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


def get_grandchild_id(model, childName, grandChildName):

    theseChildren = next(
        filter((lambda child: child.name == childName), model.children)
    )
    theseGrandchildren = next(
        filter((lambda child: child.name == grandChildName), theseChildren.children)
    )

    grandChildId = theseGrandchildren.id

    return grandChildId


def quickstart():

    # add calls here, remember to indent properly
    client = LUISAuthoringClient(
        AUTHORING_ENDPOINT, CognitiveServicesCredentials(AUTHORING_KEY)
    )

    # define app basics
    appDefinition = ApplicationCreateObject(
        name=appName, initial_version_id=versionId, culture=culture
    )

    # create app
    app_id = client.apps.add(appDefinition)

    # get app id - necessary for all other changes
    print("Created LUIS app with ID {}".format(app_id))

    # create intent
    client.model.add_intent(app_id, versionId, intentName)

    # --------------------------------------
    # Add Prebuilt entity
    client.model.add_prebuilt(app_id, versionId, prebuilt_extractor_names=["number"])

    # define machine-learned entity
    mlEntityDefinition = [
        {
            "name": "Pizza",
            "children": [{"name": "Quantity"}, {"name": "Type"}, {"name": "Size"}],
        },
        {"name": "Toppings", "children": [{"name": "Type"}, {"name": "Quantity"}]},
    ]

    # add entity to app
    modelId = client.model.add_entity(
        app_id, versionId, name="Pizza order", children=mlEntityDefinition
    )

    # define phraselist - add phrases as significant vocabulary to app
    phraseList = {
        "enabledForAllModels": False,
        "isExchangeable": True,
        "name": "QuantityPhraselist",
        "phrases": "few,more,extra",
    }

    # add phrase list to app
    phraseListId = client.features.add_phrase_list(app_id, versionId, phraseList)
    print(phraseListId)

    # Get entity and subentities
    modelObject = client.model.get_entity(app_id, versionId, modelId)
    toppingQuantityId = get_grandchild_id(modelObject, "Toppings", "Quantity")
    pizzaQuantityId = get_grandchild_id(modelObject, "Pizza", "Quantity")

    # add model as feature to subentity model
    prebuiltFeatureRequiredDefinition = {"model_name": "number", "is_required": True}
    client.features.add_entity_feature(
        app_id, versionId, pizzaQuantityId, prebuiltFeatureRequiredDefinition
    )

    # add model as feature to subentity model
    prebuiltFeatureNotRequiredDefinition = {"model_name": "number"}
    client.features.add_entity_feature(
        app_id, versionId, toppingQuantityId, prebuiltFeatureNotRequiredDefinition
    )

    # add phrase list as feature to subentity model
    phraseListFeatureDefinition = {
        "feature_name": "QuantityPhraselist",
        "model_name": None,
    }
    client.features.add_entity_feature(
        app_id, versionId, toppingQuantityId, phraseListFeatureDefinition
    )
    # --------------------------------------

    print("Labeled Example Utterance:", labeledExampleUtteranceWithMLEntity)

    # Add an example for the entity.
    # Enable nested children to allow using multiple models with the same name.
    # The quantity subentity and the phraselist could have the same exact name if this is set to True
    client.examples.add(
        app_id,
        versionId,
        labeledExampleUtteranceWithMLEntity,
        {"enableNestedChildren": True},
    )

    # --------------------------------------

    client.train.train_version(app_id, versionId)
    waiting = True
    while waiting:
        info = client.train.get_status(app_id, versionId)

        # get_status returns a list of training statuses, one for each model. Loop through them and make sure all are done.
        waiting = any(
            map(lambda x: "Queued" == x.details.status or "InProgress" == x.details.status, info)
        )
        if waiting:
            print("Waiting 1 seconds for training to complete...")
            time.sleep(1)
        else:
            print("trained")
            waiting = False

    # --------------------------------------

    # Mark the app as public so we can query it using any prediction endpoint.
    # Note: For production scenarios, you should instead assign the app to your own LUIS prediction endpoint. See:
    # https://docs.microsoft.com/en-gb/azure/cognitive-services/luis/luis-how-to-azure-subscription#assign-a-resource-to-an-app
    client.apps.update_settings(app_id, is_public=True)

    responseEndpointInfo = client.apps.publish(app_id, versionId, is_staging=False)
    print(responseEndpointInfo)


quickstart()
