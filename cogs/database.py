import sqlite3
from pathlib import Path


class Database:

    def __init__(self, path="bot.db"):
        self.path = Path(path)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self.create_tables()

    def create_tables(self):

        self.connection.execute("""
            CREATE TABLE IF NOT EXISTS guild_settings (
                guild_id INTEGER PRIMARY KEY,
                log_channel_id INTEGER,
                automod_links INTEGER DEFAULT 1,
                automod_spam INTEGER DEFAULT 1,
                automod_duplicates INTEGER DEFAULT 1
            )
        """)

        self.connection.commit()

    def get_guild(self, guild_id):

        row = self.connection.execute(
            """
            SELECT *
            FROM guild_settings
            WHERE guild_id = ?
            """,
            (guild_id,)
        ).fetchone()

        if row:
            return row

        self.connection.execute(
            """
            INSERT INTO guild_settings
            (guild_id)
            VALUES (?)
            """,
            (guild_id,)
        )

        self.connection.commit()

        return self.connection.execute(
            """
            SELECT *
            FROM guild_settings
            WHERE guild_id = ?
            """,
            (guild_id,)
        ).fetchone()

    def set_log_channel(self, guild_id, channel_id):

        self.get_guild(guild_id)

        self.connection.execute(
            """
            UPDATE guild_settings
            SET log_channel_id = ?
            WHERE guild_id = ?
            """,
            (channel_id, guild_id)
        )

        self.connection.commit()

    def set_automod(self, guild_id, setting, enabled):

        allowed = {
            "links": "automod_links",
            "spam": "automod_spam",
            "duplicates": "automod_duplicates"
        }

        if setting not in allowed:
            raise ValueError("Invalid AutoMod setting")

        self.get_guild(guild_id)

        column = allowed[setting]

        self.connection.execute(
            f"""
            UPDATE guild_settings
            SET {column} = ?
            WHERE guild_id = ?
            """,
            (1 if enabled else 0, guild_id)
        )

        self.connection.commit()

    def close(self):
        self.connection.close()