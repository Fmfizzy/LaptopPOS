from app import create_app
import webbrowser
import threading
import time

def open_browser():
    time.sleep(1.5)  # Give the server a moment to start
    webbrowser.open('http://127.0.0.1:5000')

app = create_app()

if __name__ == '__main__':
    threading.Thread(target=open_browser).start()
    app.run(host='127.0.0.1', port=5000)
