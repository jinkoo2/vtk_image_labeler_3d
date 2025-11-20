import websocket
import ssl

def on_open(ws):
    print("✅ Connected to server")
    ws.send("Hello from Python client!")

def on_message(ws, message):
    print(f"📨 Received: {message}")

def on_error(ws, error):
    print(f"❌ Error: {error}")

def on_close(ws, close_status_code, close_msg):
    print("🔒 Connection closed")

if __name__ == "__main__":
    websocket.enableTrace(True)

    ws = websocket.WebSocketApp(
        "wss://localhost:8181",
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )

    # If using a self-signed certificate
    ws.run_forever(sslopt={
        "cert_reqs": ssl.CERT_NONE,
        "check_hostname": False,
        "ssl_version": ssl.PROTOCOL_TLSv1_2
    })