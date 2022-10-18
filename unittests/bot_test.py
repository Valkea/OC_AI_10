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
    budget="No more than 1500$",
)

DEFAULT_DETAILS_OUTPUT = BookingDetails(
    origin="Paris",
    destination="London",
    openDate=date.today().strftime("%Y-%m-%d"),
    closeDate=(date.today() + timedelta(days=15)).strftime("%Y-%m-%d"),
    budget="1500",
    currency="Dollars",
)


class FakeDialog:
    def __init__(
        self,
        in_details: BookingDetails = None,
        out_details: BookingDetails = None,
        prefiled_booking_details: BookingDetails = None,
    ):

        CONFIG = DefaultConfig()
        RECOGNIZER = FlightBookingRecognizer(CONFIG)
        BOOKING_DIALOG = BookingDialog()
        DIALOG = MainDialog(RECOGNIZER, BOOKING_DIALOG, prefiled_booking_details)

        self.client = DialogTestClient(
            "test",
            DIALOG,
            initial_dialog_options=None,
            middlewares=[DialogTestLogger()],
        )

        self._in = in_details
        self._out = out_details

        if self._in is None:
            self._in = deepcopy(DEFAULT_DETAILS_INPUT)

        if self._out is None:
            self._out = deepcopy(DEFAULT_DETAILS_OUTPUT)

    def get_confirmation_text(self, _type_: int):

        if _type_ == 1:
            return (
                f"Please confirm, I have you traveling \n\n"
                f"- from: **{self._out.origin}** to: **{self._out.destination}** on: *{self._out.openDate}* \n\n"
                f"- then from: **{self._out.destination}** to: **{self._out.origin}** on: *{self._out.closeDate}* \n\n"
                f"with a budget of **{self._out.budget}** {self._out.currency}"
                " (1) Yes or (2) No"
            )
        elif _type_ == 2:
            return (
                f"I have you booked to **{self._out.destination}** from **{self._out.origin}** on *{self._out.openDate}*\n\n"
                f"then from **{self._out.destination}** to **{self._out.origin}** on *{self._out.closeDate}* \n\n"
                f"for a budget of {self._out.budget} {self._out.currency}"
            )

    async def get_intro(self, refTestCase: AsyncTestCase):

        reply = await self.client.send_activity("Hello")
        refTestCase.assertEqual(reply.text, "What can I help you with today?")
        reply = await self.client.send_activity("Book me a trip")

        return reply

    async def get_outro(
        self, refTestCase: AsyncTestCase, last_answer: str, confirm: str = "Yes"
    ):

        reply = await self.client.send_activity(last_answer)
        refTestCase.assertEqual(reply.text, self.get_confirmation_text(1))

        if confirm == "Yes":
            reply = await self.client.send_activity("Yes")
            refTestCase.assertEqual(reply.text, self.get_confirmation_text(2))
            reply = self.client.get_next_reply()
        else:
            reply = await self.client.send_activity("No")

        refTestCase.assertEqual(reply.text, "What else can I do for you?")


class DialogTestClientTest(AsyncTestCase):
    """Tests for dialog test client."""

    def __init__(self, *args, **kwargs):
        super(DialogTestClientTest, self).__init__(*args, **kwargs)
        logging.basicConfig(format="", level=logging.INFO)

    def test_init(self):
        client = DialogTestClient(channel_or_adapter="test", target_dialog=None)
        self.assertIsInstance(client, DialogTestClient)

    async def test_dialog_missing_origin(self):

        details = deepcopy(DEFAULT_DETAILS_OUTPUT)
        details.origin = None
        fd = FakeDialog(prefiled_booking_details=details)

        reply = await fd.get_intro(self)
        self.assertEqual(reply.text, "From what city will you be travelling?")
        await fd.get_outro(self, fd._in.origin)

    async def test_dialog_missing_destination(self):

        details = deepcopy(DEFAULT_DETAILS_OUTPUT)
        details.destination = None
        fd = FakeDialog(prefiled_booking_details=details)

        reply = await fd.get_intro(self)
        self.assertEqual(reply.text, "Where would you like to travel to?")
        await fd.get_outro(self, fd._in.destination)

    async def test_dialog_missing_openDate(self):

        details = deepcopy(DEFAULT_DETAILS_OUTPUT)
        details.openDate = None
        fd = FakeDialog(prefiled_booking_details=details)

        reply = await fd.get_intro(self)
        self.assertEqual(reply.text, "When will you start your travel?")
        await fd.get_outro(self, fd._in.openDate)

    async def test_dialog_missing_closeDate(self):

        details = deepcopy(DEFAULT_DETAILS_OUTPUT)
        details.closeDate = None
        fd = FakeDialog(prefiled_booking_details=details)

        reply = await fd.get_intro(self)
        self.assertEqual(reply.text, "When will you come back?")
        await fd.get_outro(self, fd._in.closeDate)

    async def test_dialog_missing_budget(self):

        details = deepcopy(DEFAULT_DETAILS_OUTPUT)
        details.budget = None
        details.currency = None
        fd = FakeDialog(prefiled_booking_details=details)

        reply = await fd.get_intro(self)
        self.assertEqual(reply.text, "What is your budget for this travel?")
        await fd.get_outro(self, fd._in.budget)

    # async def test_dialog_step_by_step_straight_answers(self):
    # TODO

    async def test_dialog_step_by_step_full_YES(self):

        fd = FakeDialog()
        fd._in.budget = "No more than 1500$"
        fd._out.budget = "1500"
        fd._out.currency = "Dollars"

        reply = await fd.get_intro(self)
        self.assertEqual(reply.text, "From what city will you be travelling?")

        reply = await fd.client.send_activity(fd._in.origin)
        self.assertEqual(reply.text, "When will you start your travel?")

        reply = await fd.client.send_activity(fd._in.openDate)
        self.assertEqual(reply.text, "Where would you like to travel to?")

        reply = await fd.client.send_activity(fd._in.destination)
        self.assertEqual(reply.text, "When will you come back?")

        reply = await fd.client.send_activity(fd._in.closeDate)
        self.assertEqual(reply.text, "What is your budget for this travel?")

        await fd.get_outro(self, fd._in.budget)
        # self.assertEqual(DialogTurnStatus.Complete, fd.client.dialog_turn_result.status)

    async def test_dialog_step_by_step_full_NO(self):

        fd = FakeDialog()
        fd._in.budget = "No more than 1500£"
        fd._out.budget = "1500"
        fd._out.currency = "Pounds"

        reply = await fd.get_intro(self)
        self.assertEqual(reply.text, "From what city will you be travelling?")

        reply = await fd.client.send_activity(fd._in.origin)
        self.assertEqual(reply.text, "When will you start your travel?")

        reply = await fd.client.send_activity(fd._in.openDate)
        self.assertEqual(reply.text, "Where would you like to travel to?")

        reply = await fd.client.send_activity(fd._in.destination)
        self.assertEqual(reply.text, "When will you come back?")

        reply = await fd.client.send_activity(fd._in.closeDate)
        self.assertEqual(reply.text, "What is your budget for this travel?")

        await fd.get_outro(self, fd._in.budget, confirm="No")
        # self.assertEqual(DialogTurnStatus.Complete, fd.client.dialog_turn_result.status)

    async def test_dialog_step_by_step_full_YES_with_wrong_inputs(self):

        fd = FakeDialog()
        fd._in.budget = "No more than 1500€"
        fd._out.budget = "1500"
        fd._out.currency = "Euros"

        reply = await fd.get_intro(self)
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

        await fd.get_outro(self, fd._in.budget)
        # self.assertEqual(DialogTurnStatus.Complete, fd.client.dialog_turn_result.status)
