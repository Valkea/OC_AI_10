
import sys
import pathlib
# import pytest
import logging
from datetime import date, timedelta

from aiounittest import AsyncTestCase
from botbuilder.testing import DialogTestClient, DialogTestLogger
from botbuilder.dialogs import (
    ComponentDialog,
    DialogContext,
    DialogTurnResult,
    DialogTurnStatus,
    PromptOptions,
    TextPrompt,
    WaterfallDialog,
    WaterfallStepContext,
)

# current = pathlib.Path(__file__).parent.parent
# libpath = current.joinpath("../13.core-bot/dialogs")

libpath = pathlib.Path("13.core-bot")
sys.path.append(str(libpath))

from flight_booking_recognizer import FlightBookingRecognizer
from config import DefaultConfig
from dialogs import MainDialog, BookingDialog
from bots import DialogAndWelcomeBot



class DialogTestClientTest(AsyncTestCase):
    """Tests for dialog test client."""

    def __init__(self, *args, **kwargs):
        super(DialogTestClientTest, self).__init__(*args, **kwargs)
        logging.basicConfig(format="", level=logging.INFO)

    def test_init(self):
        client = DialogTestClient(channel_or_adapter="test", target_dialog=None)
        self.assertIsInstance(client, DialogTestClient)

    async def test_dialog_step_bystep_full_YES(self):
        CONFIG = DefaultConfig()
        RECOGNIZER = FlightBookingRecognizer(CONFIG)
        BOOKING_DIALOG = BookingDialog()
        DIALOG = MainDialog(RECOGNIZER, BOOKING_DIALOG)

        client = DialogTestClient(
            "test",
            DIALOG,
            initial_dialog_options=None,
            middlewares=[DialogTestLogger()],
        )

        in_From = "Let's start from Paris"
        in_To = "Can I go to London"
        in_openDate = "today"
        in_closeDate = "in 15 days"
        in_budget = "No more than 1500$"


        out_From = "Paris"
        out_To = "London"
        out_openDate = date.today().strftime("%Y-%m-%d")
        out_closeDate = (date.today() + timedelta(days=15)).strftime("%Y-%m-%d")
        out_budget = "1500"
        out_currency = "Dollars"

        confirm_text1 = (
            f"Please confirm, I have you traveling \n\n"
            f"- from: **{out_From}** to: **{out_To}** on: *{out_openDate}* \n\n"
            f"- then from: **{out_To}** to: **{out_From}** on: *{out_closeDate}* \n\n"
            f"with a budget of **{out_budget}** {out_currency}"
            " (1) Yes or (2) No"
        )

        confirm_text2 = (
            f"I have you booked to **{out_To}** from **{out_From}** on *{out_openDate}*\n\n"
            f"then from **{out_To}** to **{out_From}** on *{out_closeDate}* \n\n"
            f"for a budget of {out_budget} {out_currency}"
        )

        reply = await client.send_activity("Hello")
        self.assertEqual(reply.text, "What can I help you with today?")

        reply = await client.send_activity("Book me a trip")
        self.assertEqual(reply.text, "From what city will you be travelling?")

        reply = await client.send_activity(in_From)
        self.assertEqual(reply.text, "When will you start your travel?")

        reply = await client.send_activity(in_openDate)
        self.assertEqual(reply.text, "Where would you like to travel to?")

        reply = await client.send_activity(in_To)
        self.assertEqual(reply.text, "When will you come back?")

        reply = await client.send_activity(in_closeDate)
        self.assertEqual(reply.text, "What is your budget for this travel?")

        reply = await client.send_activity(in_budget)
        self.assertEqual(reply.text, confirm_text1)

        reply = await client.send_activity("Yes")
        self.assertEqual(reply.text, confirm_text2)

        reply = client.get_next_reply()
        self.assertEqual(reply.text, "What else can I do for you?")

        # self.assertEqual(DialogTurnStatus.Complete, client.dialog_turn_result.status)

    async def test_dialog_step_bystep_full_NO(self):
        CONFIG = DefaultConfig()
        RECOGNIZER = FlightBookingRecognizer(CONFIG)
        BOOKING_DIALOG = BookingDialog()
        DIALOG = MainDialog(RECOGNIZER, BOOKING_DIALOG)

        client = DialogTestClient(
            "test",
            DIALOG,
            initial_dialog_options=None,
            middlewares=[DialogTestLogger()],
        )

        in_From = "Let's start from Paris"
        in_To = "Can I go to London"
        in_openDate = "today"
        in_closeDate = "in 15 days"
        in_budget = "No more than 1500£"

        out_From = "Paris"
        out_To = "London"
        out_openDate = date.today().strftime("%Y-%m-%d")
        out_closeDate = (date.today() + timedelta(days=15)).strftime("%Y-%m-%d")
        out_budget = "1500"
        out_currency = "Pounds"

        confirm_text1 = (
            f"Please confirm, I have you traveling \n\n"
            f"- from: **{out_From}** to: **{out_To}** on: *{out_openDate}* \n\n"
            f"- then from: **{out_To}** to: **{out_From}** on: *{out_closeDate}* \n\n"
            f"with a budget of **{out_budget}** {out_currency}"
            " (1) Yes or (2) No"
        )

        reply = await client.send_activity("Hello")
        self.assertEqual(reply.text, "What can I help you with today?")

        reply = await client.send_activity("Book me a trip")
        self.assertEqual(reply.text, "From what city will you be travelling?")

        reply = await client.send_activity(in_From)
        self.assertEqual(reply.text, "When will you start your travel?")

        reply = await client.send_activity(in_openDate)
        self.assertEqual(reply.text, "Where would you like to travel to?")

        reply = await client.send_activity(in_To)
        self.assertEqual(reply.text, "When will you come back?")

        reply = await client.send_activity(in_closeDate)
        self.assertEqual(reply.text, "What is your budget for this travel?")

        reply = await client.send_activity(in_budget)
        self.assertEqual(reply.text, confirm_text1)

        reply = await client.send_activity("No")
        self.assertEqual(reply.text, "What else can I do for you?")

        # self.assertEqual(DialogTurnStatus.Complete, client.dialog_turn_result.status)

    async def test_dialog_step_bystep_full_YES_with_wrong_inputs(self):
        CONFIG = DefaultConfig()
        RECOGNIZER = FlightBookingRecognizer(CONFIG)
        BOOKING_DIALOG = BookingDialog()
        DIALOG = MainDialog(RECOGNIZER, BOOKING_DIALOG)

        client = DialogTestClient(
            "test",
            DIALOG,
            initial_dialog_options=None,
            middlewares=[DialogTestLogger()],
        )

        in_From = "Let's start from Paris"
        in_To = "Can I go to London"
        in_openDate = "today"
        in_closeDate = "in 15 days"
        in_budget = "No more than 1500€"

        out_From = "Paris"
        out_To = "London"
        out_openDate = date.today().strftime("%Y-%m-%d")
        out_closeDate = (date.today() + timedelta(days=15)).strftime("%Y-%m-%d")
        out_budget = "1500"
        out_currency = "Euros"

        confirm_text1 = (
            f"Please confirm, I have you traveling \n\n"
            f"- from: **{out_From}** to: **{out_To}** on: *{out_openDate}* \n\n"
            f"- then from: **{out_To}** to: **{out_From}** on: *{out_closeDate}* \n\n"
            f"with a budget of **{out_budget}** {out_currency}"
            " (1) Yes or (2) No"
        )

        confirm_text2 = (
            f"I have you booked to **{out_To}** from **{out_From}** on *{out_openDate}*\n\n"
            f"then from **{out_To}** to **{out_From}** on *{out_closeDate}* \n\n"
            f"for a budget of {out_budget} {out_currency}"
        )

        reply = await client.send_activity("Hello")
        self.assertEqual(reply.text, "What can I help you with today?")

        reply = await client.send_activity("Book me a trip")
        self.assertEqual(reply.text, "From what city will you be travelling?")

        # Give wrong origin Answer
        reply = await client.send_activity("NOT A CITY")
        # Repeat the  previous question
        self.assertEqual(reply.text, "From what city will you be travelling?")

        reply = await client.send_activity(in_From)
        self.assertEqual(reply.text, "When will you start your travel?")

        # Give wrong starting date Answer
        reply = await client.send_activity("NOT A DATE")
        # Repeat the  previous question
        self.assertEqual(reply.text, "I'm sorry, for best results, please enter your **outbound travel** date including the **month**, **day** and **year**.")

        reply = await client.send_activity(in_openDate)
        self.assertEqual(reply.text, "Where would you like to travel to?")

        # Give wrong destination Answer
        reply = await client.send_activity("NOT A CITY")
        # Repeat the  previous question
        self.assertEqual(reply.text, "Where would you like to travel to?")

        reply = await client.send_activity(in_To)
        self.assertEqual(reply.text, "When will you come back?")

        # Give wrong returning date Answer
        reply = await client.send_activity("NOT A DATE")
        # Repeat the  previous question
        self.assertEqual(reply.text, "I'm sorry, for best results, please enter your **return travel** date including the **month**, **day** and **year**.")

        reply = await client.send_activity(in_closeDate)
        self.assertEqual(reply.text, "What is your budget for this travel?")

        # Give wrong budget Answer
        reply = await client.send_activity("NOT A BUDGET")
        # Repeat the  previous question
        self.assertEqual(reply.text, "What is your budget for this travel?")

        reply = await client.send_activity(in_budget)
        self.assertEqual(reply.text, confirm_text1)

        reply = await client.send_activity("Yes")
        self.assertEqual(reply.text, confirm_text2)

        reply = client.get_next_reply()
        self.assertEqual(reply.text, "What else can I do for you?")

        # self.assertEqual(DialogTurnStatus.Complete, client.dialog_turn_result.status)
