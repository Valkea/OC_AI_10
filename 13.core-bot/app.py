# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

"""
This sample shows how to create a bot that demonstrates the following:
- Use [LUIS](https://www.luis.ai) to implement core AI capabilities.
- Implement a multi-turn conversation using Dialogs.
- Handle user interruptions for such things as `Help` or `Cancel`.
- Prompt for and validate requests for information from the user.
"""
from http import HTTPStatus

from aiohttp import web
from aiohttp.web import Request, Response, json_response
from botbuilder.core import (
    BotFrameworkAdapterSettings,
    ConversationState,
    MemoryStorage,
    UserState,  # TelemetryLoggerMiddleware,  # ICI
)
from botbuilder.core.integration import aiohttp_error_middleware
from botbuilder.schema import Activity
# from botbuilder.applicationinsights import ApplicationInsightsTelemetryClient # ICI
# from botbuilder.integration.applicationinsights.aiohttp import (
#     AiohttpTelemetryProcessor,
#     bot_telemetry_middleware,
# ) # ICI

from config import DefaultConfig
from dialogs import MainDialog, BookingDialog
from bots import DialogAndWelcomeBot

from adapter_with_error_handler import AdapterWithErrorHandler
from flight_booking_recognizer import FlightBookingRecognizer

CONFIG = DefaultConfig()

# Create adapter.
# See https://aka.ms/about-bot-adapter to learn more about how bots work.
SETTINGS = BotFrameworkAdapterSettings(CONFIG.APP_ID, CONFIG.APP_PASSWORD)

# Create MemoryStorage, UserState and ConversationState
MEMORY = MemoryStorage()
USER_STATE = UserState(MEMORY)
CONVERSATION_STATE = ConversationState(MEMORY)

# Create adapter.
# See https://aka.ms/about-bot-adapter to learn more about how bots work.
ADAPTER = AdapterWithErrorHandler(SETTINGS, CONVERSATION_STATE)

# Create telemetry client.
# Note the small 'client_queue_size'.  This is for demonstration purposes.  Larger queue sizes
# result in fewer calls to ApplicationInsights, improving bot performance at the expense of
# less frequent updates.
# INSTRUMENTATION_KEY = CONFIG.APPINSIGHTS_INSTRUMENTATION_KEY
# TELEMETRY_CLIENT = ApplicationInsightsTelemetryClient(
#     INSTRUMENTATION_KEY, telemetry_processor=AiohttpTelemetryProcessor(), client_queue_size=10
# )

# Code for enabling activity and personal information logging.
# It is **important** to note that due to privacy concerns, in a real-world application you must obtain user consent prior to logging this information.
# TELEMETRY_LOGGER_MIDDLEWARE = TelemetryLoggerMiddleware(telemetry_client=TELEMETRY_CLIENT, log_personal_information=True)
# ADAPTER.use(TELEMETRY_LOGGER_MIDDLEWARE)

# Create dialogs and Bot
RECOGNIZER = FlightBookingRecognizer(CONFIG)
BOOKING_DIALOG = BookingDialog()
DIALOG = MainDialog(RECOGNIZER, BOOKING_DIALOG)
BOT = DialogAndWelcomeBot(CONVERSATION_STATE, USER_STATE, DIALOG)

# ===== Handle basic routes =====

async def home(request):
    # return aiohttp_jinja2.render_template('home.html', request, {})
    return web.Response(
            text='<h1>FlyMyBot is online</h1>You can POST to the BOT api here: /api/messages',
        content_type='text/html')

# ===== Listen for incoming requests on /api/messages =====

async def messages(req: Request) -> Response:
    # Main bot message handler.
    if "application/json" in req.headers["Content-Type"]:
        body = await req.json()
    else:
        return Response(status=HTTPStatus.UNSUPPORTED_MEDIA_TYPE)

    activity = Activity().deserialize(body)
    auth_header = req.headers["Authorization"] if "Authorization" in req.headers else ""

    response = await ADAPTER.process_activity(activity, auth_header, BOT.on_turn)
    if response:
        return json_response(data=response.body, status=response.status)
    return Response(status=HTTPStatus.OK)


# ===== Handle Errors =====

async def handle_404(request):
    # return aiohttp_jinja2.render_template('404.html', request, {})
    return web.Response(
        text='<h1>404 - HTTP Not Found</h1>',
        content_type='text/html')


async def handle_405(request):
    # return aiohttp_jinja2.render_template('405.html', request, {})
    return web.Response(
        text='<h1>405 - HTTP Method Not Allowed</h1><p>This API use POST calls</p>',
        content_type='text/html')


async def handle_500(request):
    # return aiohttp_jinja2.render_template('500.html', request, {})
    return web.Response(
        text='<h1>500 - HTTP Internal Server Error</h1>',
        content_type='text/html')


def create_error_middleware(overrides):
    @web.middleware
    async def error_middleware(request, handler):
        try:
            return await handler(request)
        except web.HTTPException as ex:
            override = overrides.get(ex.status)
            if override:
                resp = await override(request)
                resp.set_status(ex.status)
                return resp

            raise
        except Exception:
            resp = await overrides[500](request)
            resp.set_status(500)
            return resp

    return error_middleware


def setup_middlewares(app):
    error_middleware = create_error_middleware({
        404: handle_404,
        405: handle_405,
        500: handle_500
    })
    app.middlewares.append(error_middleware)
    return app


# ===== Init the aiohttp server =====

def init_func(argv):
    APP = web.Application(middlewares=[aiohttp_error_middleware])
    APP.router.add_post("/api/messages", messages)
    APP.router.add_get("", home)
    APP = setup_middlewares(APP)
    return APP


if __name__ == "__main__":
    APP = init_func(None)

    try:
        web.run_app(APP, host="localhost", port=CONFIG.PORT)
    except Exception as error:
        raise error
