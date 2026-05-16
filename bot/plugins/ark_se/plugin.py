from bot.plugins.base import GamePlugin, ReviewFieldSet, Specialization

ARK_SE_PLUGIN = GamePlugin(
    key="ark_se",
    name="ARK: Survival Evolved",
    mentor_nick_label="Игровой ник в ARK",
    newbie_nick_label="Игровой ник в ARK",
    specializations=(
        Specialization("base_building", "🏗️ Базостроение", "Строительство, расположение и защита базы"),
        Specialization("taming", "🦖 Приручение", "Тейминг, разведение и уход за динозаврами"),
        Specialization("pvp", "⚔️ PvP-бой", "Рейды, оборона, снаряжение и позиционка"),
        Specialization("farming", "🌾 Фарм и экономика", "Ресурсы, крафт и экономика племени"),
        Specialization("navigation", "🗺️ Навигация и выживание", "Карта, биомы, боссы и маршруты"),
        Specialization("general", "📋 Общее менторство", "Базовое обучение и ответы на разные вопросы"),
    ),
    safety_rules=(
        "Не передавайте координаты базы, пароли, PIN-коды и доступ к хранилищам.",
        "Не показывайте внутреннюю планировку базы без необходимости.",
        "Сообщайте модераторам о попытках выведать критичную информацию.",
        "Первые менторства нового ментора проходят под расширенным наблюдением модераторов.",
    ),
    review_tags=ReviewFieldSet(
        mentor_tags=("Помог найти группу", "Научил PvP", "Был терпелив", "Рекомендую"),
        newbie_tags=("Был вовлечён", "Задавал вопросы", "Рекомендую другим менторам"),
    ),
    default_session_days=14,
    quarantine_sessions=3,
)
