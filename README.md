# Todoist Telegram Bot

Telegram-бот принимает короткие задачи в личном чате и создаёт их в Todoist через Quick Add. Доступ ограничен Telegram user ID из whitelist, а каждая задача получает метку отправителя.

## Локальный запуск

1. Создайте Telegram-бота через `@BotFather` и получите токен.
2. В Todoist откройте Settings → Integrations → Developer и создайте API token.
3. Скопируйте `.env.example` в `.env` и заполните токены, разрешённые Telegram ID и `ADMIN_USER_ID`.
4. Установите зависимости и запустите:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
python main.py
```

## Docker Compose

```bash
cp .env.example .env
# заполните .env
docker compose up -d --build
docker compose logs -f bot
```

В Compose для стадии сборки включена host-сеть, чтобы Docker мог разрешить DNS PyPI на VPS с неисправным bridge-DNS. Если запускаете образ напрямую, используйте `docker build --network=host -t todoist-tg-bot .`.

Только личные исходные текстовые сообщения до 50 символов превращаются в задачи. Пустые сообщения, медиа, пересылки, ответы, сообщения без username и превышение лимита получают `Ошибка`. Посторонние пользователи не получают ответа. Системные подробности пишутся только в технический лог и уведомление администратора.

