import { connect } from "cloudflare:sockets";

/**
 * @param {WebSocket} ws
 * @param {string} hostname
 * @param {number} port
 */
async function serve(ws, hostname, port) {
  const connection = connect({ hostname, port });

  const reader = connection.readable.getReader(),
    writer = connection.writable.getWriter(),
    encoder = new TextEncoder();

  ws.addEventListener("message", ({ data }) => {
    writer.write(typeof data === "string" ? encoder.encode(data) : data);
  });

  ws.addEventListener("close", () => {
    writer.close();
    connection.close();
  });

  // eslint-disable-next-line no-constant-condition
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    ws.send(value);
  }

  ws.close()
}

export default {
  fetch(request) {
    const { searchParams } = new URL(request.url);
    const hostname = searchParams.get("host")?.trim(),
      port = +(searchParams.get("port") ?? 22);

    if (!hostname || !Number.isInteger(port)) {
      return new Response("invalid hostname or port", { status: 400 });
    }

    const upgradeHeader = request.headers.get("Upgrade");
    if (!upgradeHeader || upgradeHeader !== "websocket") {
      return new Response("Expected Upgrade: websocket", { status: 426 });
    }

    const [client, server] = Object.values(new WebSocketPair());

    server.accept();

    serve(server, hostname, port);
    return new Response(null, {
      status: 101,
      webSocket: client,
    });
  },
};
