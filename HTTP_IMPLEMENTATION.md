# HTTP Implementation Details

This document describes the HTTP implementation used in the "We are Cooked" game.

## Barebones HTTP Implementation

The game uses a barebones HTTP implementation built on raw sockets, similar to the approach used in the progjar repository examples. This implementation avoids using Python's built-in HTTP libraries and instead handles HTTP requests and responses manually.

### Server Implementation

The server uses a socket-based approach to handle HTTP requests:

1. A socket is created and bound to the specified host and port
2. The server listens for incoming connections
3. When a client connects, a new thread is spawned to handle the connection
4. The thread reads data from the client until a complete HTTP request is received
5. The request is parsed and processed by the `HttpServer` class
6. An appropriate HTTP response is generated and sent back to the client
7. The connection is closed (HTTP/1.0 style)

### Client Implementation

The client also uses a socket-based approach to send HTTP requests:

1. For each request, a new socket connection is created
2. The client sends an HTTP request to the server
3. The client reads the server's response and parses it
4. The client closes the connection after each request (HTTP/1.0 style)
5. A polling thread regularly requests game state updates from the server

## HTTP API Endpoints

### Server Endpoints

- **GET /game_state**: Returns the current game state
- **GET /health**: Simple health check endpoint
- **POST /connect**: Register a new client connection
- **POST /action**: Process client actions (movement, ingredient changes, etc.)
- **POST /disconnect**: Handle client disconnection

### Request/Response Format

All responses are in JSON format with appropriate HTTP status codes:

- 200 OK: Successful request
- 400 Bad Request: Invalid request parameters
- 404 Not Found: Endpoint not found
- 500 Internal Server Error: Server error

## Running the HTTP Version

### Server
```sh
python -m src.server.server
```

### Client
```sh
python -m src.client.http_client_main
```

## Implementation Files

### Server Files
- `src/server/http_server.py`: Contains the HTTP server implementation
- `src/server/server.py`: Entry point for starting the server

### Client Files
- `src/client/http_client.py`: Contains the HTTP client implementation
- `src/client/http_client_main.py`: Entry point for starting the HTTP client
