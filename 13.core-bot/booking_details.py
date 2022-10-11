# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

from pprint import pprint

class BookingDetails:
    def __init__(
        self,
        destination: str = None,
        origin: str = None,
        budget: int = None,
        currency: str = "",
        travel_date: str = None,
            unsupported_airports=None,
    ):
        if unsupported_airports is None:
            unsupported_airports = []
        self.destination = destination
        self.origin = origin
        self.budget = budget
        self.currency = currency
        self.travel_date = travel_date
        self.unsupported_airports = unsupported_airports

    def __str__(self):
        pprint(vars(self))
