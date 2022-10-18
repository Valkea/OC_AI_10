# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

from datatypes_date_time.timex import Timex

from botbuilder.dialogs import WaterfallDialog, WaterfallStepContext, DialogTurnResult
from botbuilder.dialogs.prompts import ConfirmPrompt, TextPrompt, PromptOptions
from botbuilder.core import MessageFactory
from botbuilder.schema import InputHints
from .cancel_and_help_dialog import CancelAndHelpDialog
from .date_resolver_dialog import (
    DateResolverDialog,
    openDateResolverDialog,
    closeDateResolverDialog,
)

from botbuilder.ai.luis import LuisRecognizer
from helpers.luis_helper import LuisHelper, Intent
from botbuilder.core import TurnContext


class BookingDialog(CancelAndHelpDialog):
    def __init__(self, dialog_id: str = None):
        super(BookingDialog, self).__init__(dialog_id or BookingDialog.__name__)

        self.add_dialog(TextPrompt(TextPrompt.__name__))
        self.add_dialog(ConfirmPrompt(ConfirmPrompt.__name__))
        self.add_dialog(DateResolverDialog(DateResolverDialog.__name__))
        self.add_dialog(openDateResolverDialog(openDateResolverDialog.__name__))
        self.add_dialog(closeDateResolverDialog(closeDateResolverDialog.__name__))
        self.add_dialog(
            WaterfallDialog(
                WaterfallDialog.__name__,
                [
                    self.origin_step,
                    self.openDate_step,
                    self.destination_step,
                    self.closeDate_step,
                    self.budget_step,
                    self.confirm_step,
                    self.final_step,
                ],
            )
        )

        self.initial_dialog_id = WaterfallDialog.__name__

    def init_luis(self, luis_recognizer: LuisRecognizer, turn_context: TurnContext):
        self.luis_recognizer = luis_recognizer
        self.turn_context = turn_context

        print("init_luis:", self.luis_recognizer, self.turn_context)

    async def callLuis(self, text):
        # Call LUIS and gather any potential booking details. (Note the TurnContext has the response to the prompt.)
        self.turn_context.activity.text = text
        intent, luis_result = await LuisHelper.execute_luis_query(
            self.luis_recognizer, self.turn_context
        )

        # print("answer:", intent, luis_result)
        return intent, luis_result

    async def parseLuis(self, attr, text):
        intent, luis_result = await self.callLuis(text)
        # print("Luis_result:", luis_result)
        if type(attr) == list:
            for a in attr:
                value = getattr(luis_result, a, None)
                # print(f"On check {a} : {value}")
                if value is not None:
                    return value
            return None
        else:
            return getattr(luis_result, attr, None)

    async def origin_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        """
        If an origin city has not been provided, prompt for one.
        :param step_context:
        :return DialogTurnResult:
        """
        booking_details = step_context.options

        if booking_details.origin is None:
            message_text = "From what city will you be travelling?"
            prompt_message = MessageFactory.text(
                message_text, message_text, InputHints.expecting_input
            )
            return await step_context.prompt(
                TextPrompt.__name__, PromptOptions(prompt=prompt_message)
            )
        return await step_context.next(booking_details.origin)

    async def openDate_step(
        self, step_context: WaterfallStepContext
    ) -> DialogTurnResult:
        """
        If a departure date (openDate) has not been provided, prompt for one.
        :param step_context:
        :return DialogTurnResult:
        """
        booking_details = step_context.options

        # Ask LUIS.ai to check the previous answer (if the field is empty)
        if booking_details.origin is None:
            origin_value = step_context.result
            origin = await self.parseLuis(["origin", "destination"], origin_value)
            booking_details.origin = origin

        # Ask again if the previous answer field is still empty
        if booking_details.origin is None:
            step_context.active_dialog.state["stepIndex"] = (
                int(step_context.active_dialog.state["stepIndex"]) - 2
            )
            return await step_context.next(None)

        # Ask the starting date
        if not booking_details.openDate or self.is_ambiguous(booking_details.openDate):
            return await step_context.begin_dialog(
                openDateResolverDialog.__name__, booking_details.openDate
            )

        return await step_context.next(booking_details.openDate)

    async def destination_step(
        self, step_context: WaterfallStepContext
    ) -> DialogTurnResult:
        """
        If a destination city has not been provided, prompt for one.
        :param step_context:
        :return DialogTurnResult:
        """
        booking_details = step_context.options

        # Capture the response to the previous step's prompt
        if booking_details.openDate is None:
            booking_details.openDate = step_context.result

        if booking_details.destination is None:
            message_text = "Where would you like to travel to?"
            prompt_message = MessageFactory.text(
                message_text, message_text, InputHints.expecting_input
            )
            return await step_context.prompt(
                TextPrompt.__name__, PromptOptions(prompt=prompt_message)
            )

        return await step_context.next(booking_details.destination)

    async def closeDate_step(
        self, step_context: WaterfallStepContext
    ) -> DialogTurnResult:
        """
        If a return date (closeDate) has not been provided, prompt for one.
        :param step_context:
        :return DialogTurnResult:
        """
        booking_details = step_context.options

        # Ask LUIS.ai to check the previous answer (if the field is empty)
        if booking_details.destination is None:
            destination_value = step_context.result
            destination = await self.parseLuis(
                ["origin", "destination"], destination_value
            )
            booking_details.destination = destination

        # Ask again if the previous answer field is still empty
        if booking_details.destination is None:
            step_context.active_dialog.state["stepIndex"] = (
                int(step_context.active_dialog.state["stepIndex"]) - 2
            )
            return await step_context.next(None)

        # Ask the starting date
        if not booking_details.closeDate or self.is_ambiguous(
            booking_details.closeDate
        ):
            return await step_context.begin_dialog(
                closeDateResolverDialog.__name__, booking_details.closeDate
            )

        return await step_context.next(booking_details.closeDate)

    async def budget_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        """
        If a budget has not been provided, prompt for one.
        :param step_context:
        :return DialogTurnResult:
        """
        booking_details = step_context.options

        # Capture the results of the previous step
        if booking_details.closeDate is None:
            booking_details.closeDate = step_context.result

        if booking_details.budget is None:
            message_text = "What is your budget for this travel?"
            prompt_message = MessageFactory.text(
                message_text, message_text, InputHints.expecting_input
            )
            return await step_context.prompt(
                TextPrompt.__name__, PromptOptions(prompt=prompt_message)
            )

        return await step_context.next(booking_details.budget)

    async def confirm_step(
        self, step_context: WaterfallStepContext
    ) -> DialogTurnResult:
        """
        Confirm the information the user has provided.
        :param step_context:
        :return DialogTurnResult:
        """
        booking_details = step_context.options

        # Ask LUIS.ai to check the previous answer (if the field is empty)
        if booking_details.budget is None:
            budget_value = step_context.result
            booking_details.budget = await self.parseLuis(["budget"], budget_value)
            booking_details.currency = await self.parseLuis(["currency"], budget_value)

        if booking_details.currency in (None, ""):
            booking_details.currency = "Euros"

        # Ask again if the previous answer field is still empty
        if booking_details.budget is None:
            step_context.active_dialog.state["stepIndex"] = (
                int(step_context.active_dialog.state["stepIndex"]) - 2
            )
            return await step_context.next(None)

        # Print confirmation message
        message_text = (
            f"Please confirm, I have you traveling \n\n"
            f"- from: **{booking_details.origin}** to: **{booking_details.destination}** on: *{booking_details.openDate}* \n\n"
            f"- then from: **{booking_details.destination}** to: **{booking_details.origin}** on: *{booking_details.closeDate}* \n\n"
            f"with a budget of **{booking_details.budget}** { booking_details.currency }"
        )
        prompt_message = MessageFactory.text(
            message_text, message_text, InputHints.expecting_input
        )

        # Offer a YES/NO prompt.
        return await step_context.prompt(
            ConfirmPrompt.__name__, PromptOptions(prompt=prompt_message)
        )

    async def final_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        """
        Complete the interaction and end the dialog.
        :param step_context:
        :return DialogTurnResult:
        """
        if step_context.result:
            booking_details = step_context.options

            return await step_context.end_dialog(booking_details)
        return await step_context.end_dialog()

    def is_ambiguous(self, timex: str) -> bool:
        timex_property = Timex(timex)
        return "definite" not in timex_property.types
