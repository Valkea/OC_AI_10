
import sys
import pathlib
# import pytest
import logging
from datetime import date, timedelta
from copy import deepcopy

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
from booking_details import BookingDetails

DEFAULT_DETAILS_INPUT = BookingDetails(
    origin="Let's start from Paris",
    destination="Can I go to London",
    openDate="today",
    closeDate="in 15 days",
    budget="No more than 1500$"
)

DEFAULT_DETAILS_OUTPUT = BookingDetails(
    origin="Paris",
    destination="London",
    openDate=date.today().strftime("%Y-%m-%d"),
    closeDate=(date.today() + timedelta(days=15)).strftime("%Y-%m-%d"),
    budget="1500",
    currency="Dollars",
)


class FakeDialog():

    def __init__(self, in_dict=None, out_dict=None):

        CONFIG = DefaultConfig()
        RECOGNIZER = FlightBookingRecognizer(CONFIG)
        BOOKING_DIALOG = BookingDialog()
        DIALOG = MainDialog(RECOGNIZER, BOOKING_DIALOG)

        self.client = DialogTestClient(
            "test",
            DIALOG,
            initial_dialog_options=None,
            middlewares=[DialogTestLogger()],
        )

        self._in = in_dict
        self._out = out_dict

        if self._in is None:
            self._in = deepcopy(DEFAULT_DETAILS_INPUT)

        if self._out is None:
            self._out = deepcopy(DEFAULT_DETAILS_OUTPUT)


class DialogTestClientTest(AsyncTestCase):
    """Tests for dialog test client."""

    def __init__(self, *args, **kwargs):
        super(DialogTestClientTest, self).__init__(*args, **kwargs)
        logging.basicConfig(format="", level=logging.INFO)

    def test_init(self):
        client = DialogTestClient(channel_or_adapter="test", target_dialog=None)
        self.assertIsInstance(client, DialogTestClient)

    # async def test_dialog_all_in_on_sentence(self):
    #     # TODO
    #     CONFIG = DefaultConfig()
    #     RECOGNIZER = FlightBookingRecognizer(CONFIG)
    #     BOOKING_DIALOG = BookingDialog()
    #     BOOKING_DETAILS = BookingDetails(
    #         destination="London",
    #         origin="Paris",
    #         budget=555,
    #         currency="Euros",
    #         openDate="2022-10-01",
    #         # closeDate = "2022-10-10",
    #     )
    #     print("Debug:", BOOKING_DETAILS)
    #     DIALOG = MainDialog(RECOGNIZER, BOOKING_DIALOG, BOOKING_DETAILS)

    #     client = DialogTestClient(
    #         "test",
    #         DIALOG,
    #         initial_dialog_options=None,
    #         middlewares=[DialogTestLogger()],
    #     )

    #     reply = await client.send_activity("Hello")
    #     self.assertEqual(reply.text, "What can I help you with today?")

    #     reply = await client.send_activity("Book me a trip")
    #     self.assertEqual(reply.text, "When will you come back?")

    # async def test_dialog_step_by_step_straight_answers(self):
    # TODO

    # async def test_dialog_step_by_step_straight_answers(self):
    # TODO

    async def test_dialog_step_by_step_full_YES(self):

        fd = FakeDialog()
        fd._in.budget = "No more than 1500$"
        fd._out.budget = "1500"
        fd._out.currency = "Dollars"

        confirm_text1 = (
            f"Please confirm, I have you traveling \n\n"
            f"- from: **{fd._out.origin}** to: **{fd._out.destination}** on: *{fd._out.openDate}* \n\n"
            f"- then from: **{fd._out.destination}** to: **{fd._out.origin}** on: *{fd._out.closeDate}* \n\n"
            f"with a budget of **{fd._out.budget}** {fd._out.currency}"
            " (1) Yes or (2) No"
        )

        confirm_text2 = (
            f"I have you booked to **{fd._out.destination}** from **{fd._out.origin}** on *{fd._out.openDate}*\n\n"
            f"then from **{fd._out.destination}** to **{fd._out.origin}** on *{fd._out.closeDate}* \n\n"
            f"for a budget of {fd._out.budget} {fd._out.currency}"
        )

        reply = await fd.client.send_activity("Hello")
        self.assertEqual(reply.text, "What can I help you with today?")

        reply = await fd.client.send_activity("Book me a trip")
        self.assertEqual(reply.text, "From what city will you be travelling?")

        reply = await fd.client.send_activity(fd._in.origin)
        self.assertEqual(reply.text, "When will you start your travel?")

        reply = await fd.client.send_activity(fd._in.openDate)
        self.assertEqual(reply.text, "Where would you like to travel to?")

        reply = await fd.client.send_activity(fd._in.destination)
        self.assertEqual(reply.text, "When will you come back?")

        reply = await fd.client.send_activity(fd._in.closeDate)
        self.assertEqual(reply.text, "What is your budget for this travel?")

        reply = await fd.client.send_activity(fd._in.budget)
        self.assertEqual(reply.text, confirm_text1)

        reply = await fd.client.send_activity("Yes")
        self.assertEqual(reply.text, confirm_text2)

        reply = fd.client.get_next_reply()
        self.assertEqual(reply.text, "What else can I do for you?")

        # self.assertEqual(DialogTurnStatus.Complete, fd.client.dialog_turn_result.status)

    async def test_dialog_step_by_step_full_NO(self):

        fd = FakeDialog()
        fd._in.budget = "No more than 1500£"
        fd._out.budget = "1500"
        fd._out.currency = "Pounds"

        confirm_text1 = (
            f"Please confirm, I have you traveling \n\n"
            f"- from: **{fd._out.origin}** to: **{fd._out.destination}** on: *{fd._out.openDate}* \n\n"
            f"- then from: **{fd._out.destination}** to: **{fd._out.origin}** on: *{fd._out.closeDate}* \n\n"
            f"with a budget of **{fd._out.budget}** {fd._out.currency}"
            " (1) Yes or (2) No"
        )

        reply = await fd.client.send_activity("Hello")
        self.assertEqual(reply.text, "What can I help you with today?")

        reply = await fd.client.send_activity("Book me a trip")
        self.assertEqual(reply.text, "From what city will you be travelling?")

        reply = await fd.client.send_activity(fd._in.origin)
        self.assertEqual(reply.text, "When will you start your travel?")

        reply = await fd.client.send_activity(fd._in.openDate)
        self.assertEqual(reply.text, "Where would you like to travel to?")

        reply = await fd.client.send_activity(fd._in.destination)
        self.assertEqual(reply.text, "When will you come back?")

        reply = await fd.client.send_activity(fd._in.closeDate)
        self.assertEqual(reply.text, "What is your budget for this travel?")

        reply = await fd.client.send_activity(fd._in.budget)
        self.assertEqual(reply.text, confirm_text1)

        reply = await fd.client.send_activity("No")
        self.assertEqual(reply.text, "What else can I do for you?")

        # self.assertEqual(DialogTurnStatus.Complete, fd.client.dialog_turn_result.status)

    async def test_dialog_step_by_step_full_YES_with_wrong_inputs(self):

        fd = FakeDialog()
        fd._in.budget = "No more than 1500€"
        fd._out.budget = "1500"
        fd._out.currency = "Euros"

        confirm_text1 = (
            f"Please confirm, I have you traveling \n\n"
            f"- from: **{fd._out.origin}** to: **{fd._out.destination}** on: *{fd._out.openDate}* \n\n"
            f"- then from: **{fd._out.destination}** to: **{fd._out.origin}** on: *{fd._out.closeDate}* \n\n"
            f"with a budget of **{fd._out.budget}** {fd._out.currency}"
            " (1) Yes or (2) No"
        )

        confirm_text2 = (
            f"I have you booked to **{fd._out.destination}** from **{fd._out.origin}** on *{fd._out.openDate}*\n\n"
            f"then from **{fd._out.destination}** to **{fd._out.origin}** on *{fd._out.closeDate}* \n\n"
            f"for a budget of {fd._out.budget} {fd._out.currency}"
        )

        reply = await fd.client.send_activity("Hello")
        self.assertEqual(reply.text, "What can I help you with today?")

        reply = await fd.client.send_activity("Book me a trip")
        self.assertEqual(reply.text, "From what city will you be travelling?")

        # Give wrong origin Answer
        reply = await fd.client.send_activity("NOT A CITY")
        # Repeat the  previous question
        self.assertEqual(reply.text, "From what city will you be travelling?")

        reply = await fd.client.send_activity(fd._in.origin)
        self.assertEqual(reply.text, "When will you start your travel?")

        # Give wrong starting date Answer
        reply = await fd.client.send_activity("NOT A DATE")
        # Repeat the  previous question
        self.assertEqual(reply.text, "I'm sorry, for best results, please enter your **outbound travel** date including the **month**, **day** and **year**.")

        reply = await fd.client.send_activity(fd._in.openDate)
        self.assertEqual(reply.text, "Where would you like to travel to?")

        # Give wrong destination Answer
        reply = await fd.client.send_activity("NOT A CITY")
        # Repeat the  previous question
        self.assertEqual(reply.text, "Where would you like to travel to?")

        reply = await fd.client.send_activity(fd._in.destination)
        self.assertEqual(reply.text, "When will you come back?")

        # Give wrong returning date Answer
        reply = await fd.client.send_activity("NOT A DATE")
        # Repeat the  previous question
        self.assertEqual(reply.text, "I'm sorry, for best results, please enter your **return travel** date including the **month**, **day** and **year**.")

        reply = await fd.client.send_activity(fd._in.closeDate)
        self.assertEqual(reply.text, "What is your budget for this travel?")

        # Give wrong budget Answer
        reply = await fd.client.send_activity("NOT A BUDGET")
        # Repeat the  previous question
        self.assertEqual(reply.text, "What is your budget for this travel?")

        reply = await fd.client.send_activity(fd._in.budget)
        self.assertEqual(reply.text, confirm_text1)

        reply = await fd.client.send_activity("Yes")
        self.assertEqual(reply.text, confirm_text2)

        reply = fd.client.get_next_reply()
        self.assertEqual(reply.text, "What else can I do for you?")

        # self.assertEqual(DialogTurnStatus.Complete, fd.client.dialog_turn_result.status)
