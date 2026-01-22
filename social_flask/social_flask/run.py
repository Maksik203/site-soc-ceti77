from app import create_app, ensure_dirs

app = create_app()
ensure_dirs()

if __name__ == "__main__":
    # Запускаем сервер напрямую на локальном IP, чтобы основным адресом был 192.168.0.105:5000
    app.run(host="192.168.0.105", port=5000, debug=True)

