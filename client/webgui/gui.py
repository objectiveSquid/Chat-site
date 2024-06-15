from client.connection import InputEvents, Connection, generate_random_event_id

import flask_htmx
import datetime
import flask


app = flask.Flask(
    "ObjectiveChat Web GUI",
    template_folder="client/webgui/templates",
    static_folder="client/webgui/static",
)
htmx = flask_htmx.HTMX(app)


def _get_pretty_messages(
    connection: Connection, secondary_username: str
) -> list[dict[str, str]]:
    raw_messages = connection.add_input_event_and_wait_for_response(
        InputEvents.GetMessages(
            generate_random_event_id(),
            secondary_username,
            0,  # after=0 means fetch all messages
        )
    ).messages  # type: ignore

    return [
        {
            "sender": message.sender,
            "content": message.content,
            "time_sent": datetime.datetime.fromtimestamp(message.time_sent).strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
        }
        for message in raw_messages
    ]


@app.route("/empty", methods=["GET"])
def empty():
    return ""


@app.route("/", methods=["GET"])
def index():
    return flask.redirect("/friends")


class WebGUI:
    def __init__(self, connection: Connection) -> None:
        self.__connection = connection

        self.__add_routes()

    def __add_routes(self) -> None:
        app.route("/friends", methods=["GET"])(self.friends)
        app.route("/chat/<secondary_username>", methods=["GET"])(self.chat)
        app.route("/chat_page/<secondary_username>", methods=["GET"])(self.chat_page)
        app.route("/chat_messages/<secondary_username>", methods=["GET"])(
            self.chat_messages
        )
        app.route("/send_message", methods=["POST"])(self.send_message)

        app.route("/remove_friend", methods=["POST"])(self.remove_friend)
        app.route("/add_friend", methods=["POST"])(self.add_friend)

    def friends(self):
        return flask.render_template(
            "friends.jinja2",
            relations=(
                self.__connection.add_input_event_and_wait_for_response(
                    InputEvents.GetRelations(generate_random_event_id())
                ).relations  # type: ignore
            ),
        )

    def chat_page(self, secondary_username: str):
        return flask.render_template(
            "chat_page.jinja2",
            secondary_username=secondary_username,
            relations=self.__connection.add_input_event_and_wait_for_response(
                InputEvents.GetRelations(generate_random_event_id())
            ).relations,  # type: ignore
            messages=_get_pretty_messages(self.__connection, secondary_username),
        )

    def chat_messages(self, secondary_username: str):
        return flask.render_template(
            "chat_messages.jinja2",
            messages=_get_pretty_messages(self.__connection, secondary_username),
        )

    def chat(self, secondary_username: str):
        return flask.render_template(
            "chat.jinja2",
            secondary_username=secondary_username,
            messages=_get_pretty_messages(self.__connection, secondary_username),
        )

    def send_message(self):
        self.__connection.add_input_event_and_wait_for_response(
            InputEvents.SendMessage(
                generate_random_event_id(),
                flask.request.form["receiver"],
                flask.request.form["content"],
            )
        )
        return flask.Response(status=200, headers={"HX-Refresh": "true"})

    def add_friend(self):
        response = self.__connection.add_input_event_and_wait_for_response(
            InputEvents.AddFriend(
                generate_random_event_id(), flask.request.form["username"]
            )
        )
        return flask.Response(
            (
                "Successfully sent friend request"
                if response.success  # type: ignore
                else "Failed to send friend request"
            ),
            headers={"HX-Refresh": "true"},
        )

    def remove_friend(self):
        self.__connection.add_input_event_and_wait_for_response(
            InputEvents.RemoveFriend(
                generate_random_event_id(), flask.request.form["username"]
            )
        )
        return flask.Response(status=200, headers={"HX-Refresh": "true"})
