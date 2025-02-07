from threading import Thread
import webview
from app import app

def start_flask():
    # Puedes desactivar debug=True para producción.
    app.run(debug=False)

if __name__ == '__main__':
    # Iniciar Flask en un hilo en segundo plano
    flask_thread = Thread(target=start_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # Crear la ventana de la aplicación apuntando a la URL de Flask
    window = webview.create_window("Echo Punto de Venta", "http://127.0.0.1:5000/")
    webview.start()
