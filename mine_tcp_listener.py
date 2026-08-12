import socket
import struct
import json


def get_minecraft_status_tcp(ip, port=25565):
    # Создаем TCP сокет вместо UDP
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5.0)

    try:
        sock.connect((ip, port))

        # 1. Формируем пакет Handshake (Протокол TCP)
        host_bytes = ip.encode("utf-8")
        # Сборка полей VarInt (длина + данные)
        packet = b"\x00"  # Packet ID (0x00 для Handshake)
        packet += b"\xff\x05"  # Версия протокола (в данном случае универсальная)
        packet += bytes([len(host_bytes)]) + host_bytes  # Адрес сервера
        packet += bytes([port >> 8, port & 0xFF])  # Порт сервера (2 байта)
        packet += b"\x01"  # Следующее состояние (1 - статус)

        # Добавляем длину всего пакета в начало (VarInt)
        packet = bytes([len(packet)]) + packet
        sock.send(packet)

        # 2. Пакет запроса статуса (Status Request)
        # Длина 1 байт (0x01), ID пакета 1 байт (0x00)
        sock.send(b"\x01\x00")

        # 3. Чтение ответа
        # Сначала считываем длину ответа и ID пакета
        _packet_len = sock.recv(2)  # Пропускаем VarInt длины
        _packet_id = sock.recv(1)  # Пропускаем ID пакета

        # Считываем длину JSON-строки
        json_len = 0
        shift = 0
        while True:
            byte = sock.recv(1)[0]
            json_len |= (byte & 0x7F) << shift
            if not (byte & 0x80):
                break
            shift += 7

        # Получаем сам JSON
        data = b""
        while len(data) < json_len:
            packet = sock.recv(json_len - len(data))
            if not packet:
                break
            data += packet

        # Парсим JSON ответ
        status = json.loads(data.decode("utf-8"))

        players = status.get("players", {})
        print(f"Сервер: {ip}:{port}")
        print(f"Игроков онлайн: {players.get('online', 0)}/{players.get('max', 0)}")
        print(f"Версия: {status.get('version', {}).get('name', 'N/A')}")
        print(
            f"Описание (MOTD): {status.get('description', 'N/A')}"
        )  # Может быть словарем

        # --- Новый блок вывода списка игроков ---
        player_sample = players.get("sample", [])
        if player_sample:
            print("\nСписок игроков онлайн:")
            for player in player_sample:
                # Выводим никнейм игрока
                print(f"- {player.get('name')}")
        else:
            print("Список игроков пуст или скрыт настройками сервера.")

        print()

    except socket.timeout:
        print("Время ожидания ответа от сервера истекло.")
    except Exception as e:
        print(f"Ошибка подключения: {e}")
    finally:
        sock.close()


get_minecraft_status_tcp("play.hypixel.net", 25565)

# Запуск (замените на свой IP и Query порт)
get_minecraft_status_tcp("185.9.145.210", 32290)
