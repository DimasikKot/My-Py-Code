import json
import socket
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
import asyncio

# Токен бота
BOT_TOKEN = "7675878838:AAHkKDVMsluFQcEcZcPgEe6jsi3ERJiWrFA"

# Данные сервера
SERVER_IP = "185.9.145.210"
SERVER_PORT = 32290

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


def get_minecraft_status(ip, port=25565):
    """Получение статуса Minecraft сервера через TCP"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5.0)

    try:
        sock.connect((ip, port))

        # Handshake пакет
        host_bytes = ip.encode("utf-8")
        packet = b"\x00"
        packet += b"\xff\x05"
        packet += bytes([len(host_bytes)]) + host_bytes
        packet += bytes([port >> 8, port & 0xFF])
        packet += b"\x01"
        packet = bytes([len(packet)]) + packet
        sock.send(packet)

        # Запрос статуса
        sock.send(b"\x01\x00")

        # Чтение ответа
        sock.recv(2)  # длина
        sock.recv(1)  # ID пакета

        # Чтение JSON
        json_len = 0
        shift = 0
        while True:
            byte = sock.recv(1)[0]
            json_len |= (byte & 0x7F) << shift
            if not (byte & 0x80):
                break
            shift += 7

        data = b""
        while len(data) < json_len:
            packet = sock.recv(json_len - len(data))
            if not packet:
                break
            data += packet

        status = json.loads(data.decode("utf-8"))

        players = status.get("players", {})
        version = status.get("version", {}).get("name", "N/A")
        description = status.get("description", "N/A")

        # Обработка MOTD (может быть строкой или словарем)
        if isinstance(description, dict):
            description = description.get("text", "N/A")

        # Список игроков
        player_list = players.get("sample", [])
        players_online = (
            "\n".join([f"• {p.get('name')}" for p in player_list])
            if player_list
            else "Нет игроков онлайн"
        )

        return {
            "online": players.get("online", 0),
            "max": players.get("max", 0),
            "version": version,
            "motd": description,
            "players_list": players_online,
            "players_sample": player_list,  # Сохраняем список для /info
        }

    except socket.timeout:
        return {"error": "⏰ Сервер не отвечает (таймаут)"}
    except Exception as e:
        return {"error": f"❌ Ошибка: {str(e)}"}
    finally:
        sock.close()


@dp.message(Command("smp", "purmur", "purpur", "vanilla"))
async def cmd_info1(message: Message):
    """Обработчик команды /info - показывает полную информацию со списком игроков"""
    # Отправляем первое сообщение "Загрузка..."
    loading_msg = await message.reply("🔄 Получение информации о сервере...")

    status = get_minecraft_status("purmur.exaroton.me", 58386)

    if "error" in status:
        # Редактируем сообщение с ошибкой
        await loading_msg.edit_text(f"❌ {status['error']}")
        # Обратный отсчет для ошибки
        for i in range(15, 0, -1):
            await loading_msg.edit_text(
                f"❌ {status['error']}\n\n⏳ Сообщение будет удалено через {i} сек..."
            )
            await asyncio.sleep(1)
        await loading_msg.delete()
        return

    # Полная информация со списком игроков
    response = (
        f"🎮 **Полная информация о сервере PurMur Vanilla**\n"
        f"📌 **IP:** `purmur.exaroton.me:58386`\n"
        f"📡 **Версия:** {status['version']}\n"
        f"👥 **Игроки:** {status['online']}/{status['max']}\n"
        f"📝 **MOTD:** {status['motd']}\n\n"
        f"**📋 Список игроков онлайн:**\n{status['players_list']}"
    )

    # Редактируем сообщение с информацией
    await loading_msg.edit_text(response, parse_mode="Markdown")

    # 🔥 ОБРАТНЫЙ ОТСЧЕТ до удаления
    for i in range(15, 0, -1):
        # Добавляем таймер в конец сообщения
        timer_text = f"\n\n⏳ Сообщение будет удалено через {i} сек..."
        await loading_msg.edit_text(response + timer_text, parse_mode="Markdown")
        await asyncio.sleep(1)

    # Удаляем сообщение
    await loading_msg.delete()


@dp.message(Command("create", "info"))
async def cmd_info(message: Message):
    """Обработчик команды /info - показывает полную информацию со списком игроков"""
    # Отправляем первое сообщение "Загрузка..."
    loading_msg = await message.reply("🔄 Получение информации о сервере...")

    status = get_minecraft_status(SERVER_IP, SERVER_PORT)

    if "error" in status:
        # Редактируем сообщение с ошибкой
        await loading_msg.edit_text(f"❌ {status['error']}")
        # Обратный отсчет для ошибки
        for i in range(15, 0, -1):
            await loading_msg.edit_text(
                f"❌ {status['error']}\n\n⏳ Сообщение будет удалено через {i} сек..."
            )
            await asyncio.sleep(1)
        await loading_msg.delete()
        return

    # Полная информация со списком игроков
    response = (
        f"🎮 **Полная информация о сервере PurMur Create**\n"
        f"📌 **IP:** `{SERVER_IP}:{SERVER_PORT}`\n"
        f"📡 **Версия:** {status['version']}\n"
        f"👥 **Игроки:** {status['online']}/{status['max']}\n"
        f"📝 **MOTD:** {status['motd']}\n\n"
        f"**📋 Список игроков онлайн:**\n{status['players_list']}"
    )

    # Редактируем сообщение с информацией
    await loading_msg.edit_text(response, parse_mode="Markdown")

    # 🔥 ОБРАТНЫЙ ОТСЧЕТ до удаления
    for i in range(15, 0, -1):
        # Добавляем таймер в конец сообщения
        timer_text = f"\n\n⏳ Сообщение будет удалено через {i} сек..."
        await loading_msg.edit_text(response + timer_text, parse_mode="Markdown")
        await asyncio.sleep(1)

    # Удаляем сообщение
    await loading_msg.delete()


async def main():
    """Запуск бота"""
    print("🤖 Бот запущен!")
    print(f"📡 Сервер: {SERVER_IP}:{SERVER_PORT}")
    print("✅ Бот отвечает на сообщения краткой информацией")
    print("✅ /info показывает полную информацию со списком игроков")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
