# ObjectiveChat
A web-gui chat client, and server, written in Python 3.12

## How it's made
*To all the functional bros out there... Yes I'm using abstract classes and such. And I dont care if its a "waste of time"!*
### Client frontend
For the web-gui I'm using pure htmx/css, *no javascript needed here!*<br>
It's being served with a basic flask app which communicates with the client-side backend through an event queue.

### Client backend ("the middle end")
Communication with the server happens through a packet loop-like structure, with packets and the responses being in a queue until they are handled by the sender.<br>
They are associated with each other by using randomly generated ids, and no, I'm not checking if an id already exists, there is a reason I chose a whole 4 bytes for them, deal with it.

### Server
The server is all one big mess, there is no distinction between what communicates with clients and what communicates with the database. If you dont like it, go <s>fuck</s> fix it yourself.