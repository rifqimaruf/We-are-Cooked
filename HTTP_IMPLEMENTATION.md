# HTTP Implementation for We are Cooked

This document explains the HTTP-based implementation that has been added as an alternative to the original socket-based communication protocol.

## Overview

The original game used direct socket connections with a custom protocol for communication between the server and clients. This new implementation uses HTTP as the communication protocol, which offers several advantages:

- Standard protocol with better compatibility across networks
- Easier debugging using standard tools
- Simpler implementation of client-server communication
- Better error handling and status codes
- Potential for web-based clients in the future

## Architecture

### Server

The HTTP server implementation uses Python's built-in `http.server` module with the following components:

- `ThreadedHTTPServer`: A multi-threaded HTTP server that handles multiple client connections
- `GameHttpHandler`: Handles HTTP requests and manages game state

The server exposes the following endpoints:

- `GET /game_state`: Returns the current game state
- `POST /connect`: Registers a new client and returns initial game state
- `POST /action`: Processes client actions (movement, ingredient changes, etc.)
- `POST /disconnect`: Handles client disconnection
- `GET /health`: Simple health check endpoint

### Client

The HTTP client implementation uses the `requests` library to communicate with the server:

- `HttpNetworkHandler`: Manages HTTP communication with the server
- Polling mechanism to regularly fetch game state updates
- Sends actions to the server as HTTP POST requests

## How It Works

1. **Connection**:
   - Client sends a POST request to `/connect`
   - Server assigns a unique client ID and returns initial game state
   - Client starts polling for game state updates

2. **Game State Updates**:
   - Client regularly polls the `/game_state` endpoint
   - Server returns the current game state as JSON
   - Client updates its local game state based on the response

3. **Actions**:
   - Client sends actions (movement, etc.) as POST requests to `/action`
   - Server processes the action and updates the game state
   - All clients receive the updated state in their next poll

4. **Disconnection**:
   - Client sends a POST request to `/disconnect`
   - Server removes the client from the game

## Running the HTTP Version

### Server
```sh
python -m src.server.http_server_main
```

### Client
```sh
python -m src.client.http_client_main
```

## Advantages Over Socket-Based Implementation

1. **Statelessness**: HTTP is stateless, which simplifies the server implementation
2. **Standard Protocol**: Uses a widely adopted protocol with better tooling
3. **Error Handling**: HTTP status codes provide clear error information
4. **Scalability**: Easier to scale with standard web infrastructure
5. **Debugging**: Can use standard HTTP debugging tools (browser dev tools, Postman, etc.)

## Limitations

1. **Polling Overhead**: Regular polling creates more network traffic than socket-based push notifications
2. **Latency**: HTTP requests may have slightly higher latency than direct sockets
3. **Connection Management**: HTTP doesn't maintain persistent connections by default

## Future Improvements

1. **WebSockets**: Could be implemented for real-time updates without polling
2. **Authentication**: Add proper authentication for clients
3. **Rate Limiting**: Implement rate limiting to prevent abuse
4. **Compression**: Add response compression for larger game states
5. **Web Client**: Create a browser-based client using the HTTP API
