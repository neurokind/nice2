import asyncio

from telegram_service import TelegramService, TelegramServiceError


MENU = """
=== Telegram Console Client ===
1) Authorize / reconnect
2) Show dialogs
3) Show recent messages with user/chat
4) Send message
5) Show typing status (and then send)
6) React to message
0) Exit
"""


async def handle_menu(service: TelegramService) -> None:
    while True:
        print(MENU)
        choice = input("Choose action: ").strip()

        if choice == "0":
            print("Bye.")
            return

        try:
            if choice == "1":
                await service.connect()
                me = await service.client.get_me()
                print(f"Authorized as: {me.first_name} (id={me.id})")

            elif choice == "2":
                dialogs = await service.list_dialogs(limit=30)
                for d in dialogs:
                    uname = f"@{d.username}" if d.username else "-"
                    print(f"{d.peer_id} | {d.title} | {uname}")

            elif choice == "3":
                target = input("Target (@username, phone, id): ").strip()
                msgs = await service.get_recent_messages(target, limit=20)
                for m in msgs:
                    text = m.text if m.text else "<empty>"
                    print(f"[{m.msg_id}] {m.date_iso} sender={m.sender_id}: {text}")

            elif choice == "4":
                target = input("Target (@username, phone, id): ").strip()
                text = input("Message: ").strip()
                if not text:
                    print("Empty message skipped.")
                    continue
                await service.send_message(target, text)
                print("Sent.")

            elif choice == "5":
                target = input("Target (@username, phone, id): ").strip()
                text = input("Message after typing status: ").strip()
                if not text:
                    print("Empty message skipped.")
                    continue
                await service.set_typing(target, seconds=3)
                await service.send_message(target, text)
                print("Typing shown, message sent.")

            elif choice == "6":
                target = input("Target (@username, phone, id): ").strip()
                msg_id_raw = input("Message id: ").strip()
                emoji = input("Emoji (example: 👍): ").strip()
                if not msg_id_raw.isdigit():
                    print("Message id must be integer.")
                    continue
                await service.react_to_message(target, int(msg_id_raw), emoji)
                print("Reaction sent.")

            else:
                print("Unknown command.")

        except TelegramServiceError as exc:
            print(f"Service error: {exc}")
        except Exception as exc:  # noqa: BLE001
            print(f"Unexpected error: {exc}")


async def main() -> None:
    service = TelegramService()
    try:
        await handle_menu(service)
    finally:
        await service.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
