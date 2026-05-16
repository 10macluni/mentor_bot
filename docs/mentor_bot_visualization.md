# Как работает Universal Mentor Bot

## 1. Общая архитектура

```mermaid
flowchart LR
    U[Пользователи Discord\nНовичок / Ментор / Админ] --> C[Slash-команды + Modals + Buttons]
    C --> B[MentorBot\nbot/main.py]
    B --> CG[Cogs\nmentor/newbie/admin/sessions/reputation/notifications]
    CG --> S[Services\nmatching/sessions/reputation/reports/logging]
    S --> DB[(SQLite MVP\nSQLAlchemy async)]
    B --> P[GamePlugin Registry]
    P --> A[ark_se plugin\nспециализации, правила, теги, сроки]
    S --> D[Discord API\nроли, ЛС, приватные каналы]
```

## 2. Основной пользовательский поток

```mermaid
sequenceDiagram
    participant Mentor as Ментор
    participant Admin as Админ
    participant Newbie as Новичок
    participant Bot as Mentor Bot
    participant DB as БД
    participant Discord as Discord Server

    Mentor->>Bot: /mentor_register
    Bot->>Mentor: Модальная анкета
    Mentor->>Bot: Ник, UTC, языки, специализации, опыт, лимит, расписание
    Bot->>DB: Mentor(status=pending)
    Bot->>Admin: Уведомление о новой заявке
    Admin->>Bot: /admin_approve @mentor
    Bot->>DB: status=approved
    Bot->>Discord: Выдать роль «Ментор»

    Newbie->>Bot: /find_mentor
    Bot->>Newbie: Модальная анкета
    Newbie->>Bot: Ник, UTC, язык, потребности, комментарий
    Bot->>DB: Newbie(status=searching)
    Bot->>DB: Найти approved mentors + active session counts
    Bot->>Bot: Матчинг: язык → UTC ≤ 3 → специализация → лимит → рейтинг
    Bot->>Newbie: До 5 кандидатов + кнопки «Отправить запрос»
    Newbie->>Bot: Выбирает ментора
    Bot->>Mentor: ЛС с запросом: принять / отклонить
    Mentor->>Bot: Принять
    Bot->>Discord: Создать приватный канал mentor-mentor-newbie
    Bot->>DB: MentorSession(active, expires_at=+14 дней)
```

## 3. Алгоритм матчинга

```mermaid
flowchart TD
    N[Анкета новичка] --> G{Та же игра?\ngame_key совпадает}
    G -- нет --> X[Исключить]
    G -- да --> L{Язык совпадает?}
    L -- нет --> X
    L -- да --> T{Разница UTC ≤ 3 часа?}
    T -- нет --> X
    T -- да --> SP{Есть пересечение специализаций?}
    SP -- нет --> X
    SP -- да --> CAP{Активных новичков < лимита?}
    CAP -- нет --> X
    CAP -- да --> SCORE[Скоринг:\nrating*100 + sessions*2 + overlap*10 - timezone_delta]
    SCORE --> TOP[Отсортировать по рейтингу/score/опыту]
    TOP --> RESULT[Показать топ-5 кандидатов]
```

## 4. Жизненный цикл сессии

```mermaid
stateDiagram-v2
    [*] --> pending_request: Новичок отправил запрос
    pending_request --> active: Ментор принял
    pending_request --> rejected: Ментор отклонил
    pending_request --> expired: 24 часа без ответа

    active --> completed: /finish_session или кнопка завершения
    active --> expired: Истёк срок 14 дней
    active --> active: /extend_session
    active --> report_open: /report или кнопка жалобы

    report_open --> active: Жалоба dismissed
    report_open --> banned: Жалоба confirmed + /admin_ban
    completed --> reviews: /review от участников
    reviews --> archived: Канал перенесён в архив
    archived --> [*]
```

## 5. Безопасность PVP-сервера

```mermaid
flowchart LR
    A[Только approved менторы] --> B[Приватный канал]
    B --> C[Логирование сообщений\nChannelLog]
    C --> D[Модераторские команды\n/admin_logs /admin_sessions]
    B --> E[Напоминания безопасности\nкаждые 3 дня]
    B --> F[Кнопка /report]
    F --> R[Report(open)]
    R --> M[Модератор решает]
    M --> OK[Dismiss / Resolve]
    M --> BAN[/admin_ban\nстатус banned + снять роль]
```

## 6. Что делает плагин ARK SE

Плагин `ark_se` добавляет игровые правила без изменения ядра бота:

- игровые подписи: «Игровой ник в ARK»;
- специализации: базостроение, приручение, PvP, фарм, навигация, общее менторство;
- PVP safety rules: не передавать координаты базы, пароли, PIN-коды, доступ к хранилищам;
- теги отзывов для ментора и новичка;
- дефолтный срок сессии: 14 дней;
- карантин нового ментора: 3 первые сессии.

## 7. Команды по ролям

| Роль | Основные команды |
|---|---|
| Новичок | `/find_mentor`, `/profile`, `/report`, `/review` |
| Ментор | `/mentor_register`, `/profile`, `/finish_session`, `/extend_session`, `/review` |
| Админ | `/admin_approve`, `/admin_reject`, `/admin_ban`, `/admin_unban`, `/admin_settings`, `/admin_stats` |
| Модератор | `/admin_sessions`, `/admin_logs`, `/resolve_report` |
