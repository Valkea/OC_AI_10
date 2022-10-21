# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import re
import os
import json

from botbuilder.dialogs import (
    ComponentDialog,
    WaterfallDialog,
    WaterfallStepContext,
    DialogTurnResult,
)
from botbuilder.dialogs.prompts import ConfirmPrompt, TextPrompt, PromptOptions
from botbuilder.core import (
    MessageFactory,
    TurnContext,
    BotTelemetryClient,
    NullTelemetryClient,
)
from botbuilder.schema import InputHints, Attachment

from booking_details import BookingDetails
from flight_booking_recognizer import FlightBookingRecognizer
from helpers.luis_helper import LuisHelper, Intent
from .booking_dialog import BookingDialog


class MainDialog(ComponentDialog):
    def __init__(
        self,
        luis_recognizer: FlightBookingRecognizer,
        booking_dialog: BookingDialog,
        booking_details: BookingDetails = None,
        telemetry_client: BotTelemetryClient = None,
    ):
        super(MainDialog, self).__init__(MainDialog.__name__)
        self.telemetry_client = telemetry_client or NullTelemetryClient()

        text_prompt = TextPrompt(TextPrompt.__name__)
        text_prompt.telemetry_client = self.telemetry_client

        booking_dialog.telemetry_client = self.telemetry_client

        wf_dialog = WaterfallDialog(
            "WFDialog", [self.intro_step, self.act_step, self.final_step, self.request_authorization_step]
        )
        wf_dialog.telemetry_client = self.telemetry_client

        self._luis_recognizer = luis_recognizer
        self._booking_dialog = booking_dialog
        self._booking_dialog_id = booking_dialog.id

        if booking_details is None:
            self._booking_details = BookingDetails()
        else:
            self._booking_details = booking_details

        self.add_dialog(text_prompt)
        self.add_dialog(booking_dialog)
        self.add_dialog(ConfirmPrompt(ConfirmPrompt.__name__))
        self.add_dialog(wf_dialog)

        self.initial_dialog_id = "WFDialog"

    async def intro_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        if not self._luis_recognizer.is_configured:
            await step_context.context.send_activity(
                MessageFactory.text(
                    "NOTE: LUIS is not configured. To enable all capabilities, add 'LuisAppId', 'LuisAPIKey' and "
                    "'LuisAPIHostName' to the appsettings.json file.",
                    input_hint=InputHints.ignoring_input,
                )
            )

            return await step_context.next(None)
        message_text = (
            str(step_context.options)
            if step_context.options
            else "What can I help you with today?"
        )
        prompt_message = MessageFactory.text(
            message_text, message_text, InputHints.expecting_input
        )

        return await step_context.prompt(
            TextPrompt.__name__, PromptOptions(prompt=prompt_message)
        )

    async def act_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:

        self.failure_type = None

        if not self._luis_recognizer.is_configured:
            # LUIS is not configured, we just run the BookingDialog path with an empty BookingDetailsInstance.

            return await step_context.begin_dialog(
                # self._booking_dialog_id, BookingDetails()
                self._booking_dialog_id,
                self._booking_details,
            )

        # Call LUIS and gather any potential booking details. (Note the TurnContext has the response to the prompt.)
        intent, luis_result = await LuisHelper.execute_luis_query(
            self._luis_recognizer, step_context.context
        )

        # If Luis didn't find any entity, grab the previous booking details
        if luis_result == BookingDetails():
            luis_result = self._booking_details

        # Pass Luis to the booking dialog for further requests
        self._booking_dialog.init_luis(self._luis_recognizer, step_context.context)

        if intent == Intent.BOOK_FLIGHT.value and luis_result:
            # Show a warning for Origin and Destination if we can't resolve them.
            await MainDialog._show_warning_for_unsupported_cities(
                step_context.context, luis_result
            )

            # Run the BookingDialog giving it whatever details we have from the LUIS call.
            return await step_context.begin_dialog(self._booking_dialog_id, luis_result)

        if intent == Intent.GREET.value:
            hello_text = "Well, hello there! What can I do for you?"
            hello_message = MessageFactory.text(
                hello_text, hello_text, InputHints.ignoring_input
            )
            await step_context.context.send_activity(hello_message)
            # return await step_context.replace_dialog(self.id, hello_message)

        else:
            didnt_understand_text = (
                "Sorry, I didn't get that. Please try asking in a different way"
            )
            didnt_understand_message = MessageFactory.text(
                didnt_understand_text, didnt_understand_text, InputHints.ignoring_input
            )
            await step_context.context.send_activity(didnt_understand_message)

            if type(self.telemetry_client) != NullTelemetryClient:

                max_misunderstanding = 3
                self.telemetry_client.num_misunderstanding += 1

                if self.telemetry_client.num_misunderstanding >= max_misunderstanding:

                    msg_txt = (
                        "We obviously have a communication problem... \n\n"
                        "**Would you allow me to share our conversation with my administrators?**"
                    )

                    self.failure_type = f"Misunderstanding x {max_misunderstanding}"
                    return await self.request_authorization_prompt(step_context, msg_txt)

        return await step_context.next(None)

    async def final_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:

        # If we had Misunderstanding failures, we pass it to the request_authorization_step
        if self.failure_type is not None:
            return await step_context.next(None)

        # If the user completed the booking process, display the answer accordind to its final answer
        if step_context.result is not None and step_context.context.activity.text == "Yes":

            # Now we have all the booking details call the booking service.
            # If the call to the booking service was successful tell the user.

            # result = step_context.result
            # msg_txt = (
            #     f"I have you booked to **{result.destination}** from **{result.origin}** on *{result.openDate}*\n\n"
            #     f"then from **{result.destination}** to **{result.origin}** on *{result.closeDate}* \n\n"
            #     f"for a budget of {result.budget} {result.currency}"
            # )

            msg_txt = "**I booked the following trip for you**"
            message = MessageFactory.text(msg_txt, msg_txt, InputHints.ignoring_input)
            await step_context.context.send_activity(message)

            await self.show_confirmation(step_context)

        elif step_context.context.activity.text == "No":

            # If the user wasn't satified, raise an Insights alert with the conversation log

            msg_txt = (
                "I have noticed that you are not satisfied with my proposal. \n\n"
                "**Would you allow me to share our conversation with my administrators?**"
            )

            self.failure_type = "Booking not confirmed"
            return await self.request_authorization_prompt(step_context, msg_txt)

        step_context.context.activity.text = None
        return await step_context.next(None)

    async def request_authorization_prompt(self, step_context: WaterfallStepContext, msg_txt: str):

        prompt_message = MessageFactory.text(
            msg_txt, msg_txt, InputHints.expecting_input
        )

        # Offer a YES/NO prompt.
        return await step_context.prompt(
            ConfirmPrompt.__name__, PromptOptions(prompt=prompt_message)
        )

    async def request_authorization_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        # Request authorization to send the conversation history if needed

        if type(self.telemetry_client) != NullTelemetryClient:

            if step_context.context.activity.text == "Yes":
                self.telemetry_client.track_failure(f"{self.failure_type} [with history]", history=True)

            elif step_context.context.activity.text == "No":
                self.telemetry_client.track_failure(f"{self.failure_type} [without history]", history=False)

        prompt_message = "What else can I do for you?"
        return await step_context.replace_dialog(self.id, prompt_message)

    @staticmethod
    async def _show_warning_for_unsupported_cities(
        context: TurnContext, luis_result: BookingDetails
    ) -> None:
        if luis_result.unsupported_airports:
            message_text = (
                f"Sorry but the following airports are not supported:"
                f" {', '.join(luis_result.unsupported_airports)}"
            )
            message = MessageFactory.text(
                message_text, message_text, InputHints.ignoring_input
            )
            await context.send_activity(message)

    @staticmethod
    async def show_confirmation(step_context: WaterfallStepContext):
        card = MainDialog.create_confirmation_card(step_context)
        response = MessageFactory.attachment(card)
        await step_context.context.send_activity(response)

    @staticmethod
    def create_confirmation_card(step_context: WaterfallStepContext):

        details = step_context.result

        relative_path = os.path.abspath(os.path.dirname(__file__))
        path = os.path.join(relative_path, "../cards/confirmationCard.json")
        with open(path) as in_file:
            card_template = json.load(in_file)

        template_data = {
            "origin": details.origin,
            "destination": details.destination,
            "origin_tag": details.origin.upper()[:3],
            "destination_tag": details.destination.upper()[:3],
            "openDate": details.openDate,
            "closeDate": details.closeDate,
            "budget": details.budget,
            "currency": details.currency
        }

        card = MainDialog.replace_cards_entities(card_template, template_data)

        return Attachment(
            content_type="application/vnd.microsoft.card.adaptive", content=card
        )

    @staticmethod
    def replace_cards_entities(template: dict, data: dict):
        str_temp = str(template)
        for key in data:
            pattern = "\${" + key + "}"
            str_temp = re.sub(pattern, str(data[key]), str_temp)
        return eval(str_temp)


