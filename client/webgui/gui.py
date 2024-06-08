from client.connection import InputEvents, Connection, generate_random_event_id
from shared.items import Relation, Message

import flask_htmx
import datetime
import flask


app = flask.Flask(
    "ObjectiveChat Web GUI",
    template_folder="client/webgui/templates",
    static_folder="client/webgui/static",
)
htmx = flask_htmx.HTMX(app)


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
        app.route("/send_chat", methods=["POST"])(self.send_chat)

        app.route("/remove_friend", methods=["POST"])(self.remove_friend)
        app.route("/add_friend", methods=["POST"])(self.add_friend)

    def friends(self):
        relations = self.__connection.add_input_event_and_wait_for_response(
            InputEvents.GetRelations(generate_random_event_id())
        ).relations  # type: ignore

        return flask.render_template("friends.jinja2", relations=relations)

    def chat(self, secondary_username: str):
        messages = [
            secondary_username
        ] = self.__connection.add_input_event_and_wait_for_response(
            InputEvents.GetMessages(
                generate_random_event_id(),
                [secondary_username],
                0,  # after=0 means fetch all messages
            )
        ).messages  # type: ignore

        return flask.render_template(
            "chat.jinja2",
            messages=[
                {
                    "sender": message.sender,
                    "content": message.content,
                    "time_sent": datetime.datetime.fromtimestamp(
                        message.time_sent
                    ).strftime("%Y-%m-%d %H:%M:%S"),
                }
                for message in messages[secondary_username]
            ],
        )

    # TODO: Set "HX-Refresh" to "true" in response headers like in the add_friend endpoint
    def send_chat(self):
        pass

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
