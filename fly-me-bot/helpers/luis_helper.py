# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

from enum import Enum
from typing import Dict
from botbuilder.ai.luis import LuisRecognizer
from botbuilder.core import IntentScore, TopIntent, TurnContext

from booking_details import BookingDetails


class Intent(Enum):
    BOOK_FLIGHT = "BookFlight"
    GREET = "Greet"
    QUIT = "Quit"
    CANCEL = "Cancel"
    NONE_INTENT = "None"


def top_intent(intents: Dict[Intent, dict]) -> TopIntent:
    max_intent = Intent.NONE_INTENT
    max_value = 0.0

    for intent, value in intents:
        intent_score = IntentScore(value)
        if intent_score.score > max_value:
            max_intent, max_value = intent, intent_score.score

    return TopIntent(max_intent, max_value)


class LuisHelper:
    @staticmethod
    async def execute_luis_query(
        luis_recognizer: LuisRecognizer, turn_context: TurnContext, check_intent=True
    ) -> (Intent, object):
        """
        Returns an object with preformatted LUIS results for the bot's dialogs to consume.
        """
        result = None
        intent = None

        try:
            recognizer_result = await luis_recognizer.recognize(turn_context)

            intent = (
                sorted(
                    recognizer_result.intents,
                    key=recognizer_result.intents.get,
                    reverse=True,
                )[:1][0]
                if recognizer_result.intents
                else None
            )

            print(f"INTENT:{intent}")
            print(recognizer_result)

            if intent == Intent.BOOK_FLIGHT.value or check_intent is False:
                result = BookingDetails()

                # We need to get the result from the LUIS JSON which at every level returns an array.

                # --- Entity:To ---
                to_entities = recognizer_result.entities.get("$instance", {}).get(
                    "To", []
                )

                if len(to_entities) > 0:

                    # if recognizer_result.entities.get("To", [{"$instance": {}}])[0]["$instance"]:
                    if recognizer_result.entities["To"]:
                        result.destination = to_entities[0]["text"].capitalize()
                    else:
                        result.unsupported_airports.append(
                            to_entities[0]["text"].capitalize()
                        )

                # --- Entity:From ---
                from_entities = recognizer_result.entities.get("$instance", {}).get(
                    "From", []
                )
                if len(from_entities) > 0:

                    if recognizer_result.entities["From"]:
                        result.origin = from_entities[0]["text"].capitalize()
                    else:
                        result.unsupported_airports.append(
                            from_entities[0]["text"].capitalize()
                        )

                # --- Entity:budget ---
                budget_entities = recognizer_result.entities.get("$instance", {}).get(
                    "budget", []
                )
                money_entities = recognizer_result.entities.get("money", [])

                if len(money_entities) > 0:
                    result.budget = money_entities[0]["number"]
                    result.currency = money_entities[0]["units"] + "s"

                elif len(budget_entities) > 0:
                    result.budget = budget_entities[0]["text"]

                # --- Entity:openDate ---
                openDate_entities = recognizer_result.entities.get("$instance", {}).get(
                    "openDate", []
                )
                if len(openDate_entities) > 0:
                    if recognizer_result.entities["openDate"]:
                        result.openDate = openDate_entities[0]["text"]

                # --- Entity:closeDate ---
                closeDate_entities = recognizer_result.entities.get(
                    "$instance", {}
                ).get("closeDate", [])
                if len(closeDate_entities) > 0:
                    if recognizer_result.entities["closeDate"]:
                        result.closeDate = closeDate_entities[0]["text"]

                print(f"result:{result}")

        except Exception as exception:
            print(exception)

        return intent, result
