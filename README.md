# ObjectiveChat
A web-gui chat client, and server, written in Python 3.12

## Todo
  - Add caching to packet queue
  - Add smooth edges to the web pages
  - Make navbar

## How it's made
*To all the functional bros out there... Yes I'm using abstract classes and such. And I dont care if its a "waste of time"!*
### Client frontend
For the web-gui I'm using pure htmx/css, *no javascript needed here!*<br>
It's being served with a basic flask app which communicates with the client-side backend through an event queue.

Right now the chat gets reloaded every second, and theres no caching... <i>bruh</i>

### Client backend ("the middle end")
Communication with the server happens through a packet loop-like structure, with packets and the responses being in a queue until they are handled by the sender.<br>
They are associated with each other by using randomly generated ids, and no, I'm not checking if an id already exists, there is a reason I chose a whole 4 bytes for them, deal with it.

### Server
The server is all one big mess, there is no distinction between what communicates with clients and what communicates with the database. If you dont like it, go <s>fuck</s> <u>fix it</u> yourself.