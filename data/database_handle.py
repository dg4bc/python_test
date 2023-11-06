"""A class which transparently bundles data connection and cursor."""

# External imports
import sqlite3


class DBHandle:
    """A class to facilitate moving data connection and cursor together"""

    def __init__(self) -> None:
        self.connection: sqlite3.Connection = sqlite3.connect("index_constituents.db")
        self.cursor: sqlite3.Cursor = self.connection.cursor()

    def commit(self) -> None:
        """Commits changes across the data connection"""
        self.connection.commit()

    def __del__(self) -> None:
        """Closes the data connection as the handle is destroyed"""
        self.connection.close()

    def contains_table(self, target_table: str) -> bool:
        """
        A utility method to test if the database contains a given table
        :param target_table: The three character prefix string of the index
        :return: True where table is present with entries, or else False
        """
        return (
            self.cursor.execute(
                "".join(
                    [
                        "SELECT count(*) FROM ",
                        "sqlite_master WHERE ",
                        "type='table' AND name='" + target_table + "'",
                    ]
                )
            ).fetchall()[0][0]
            == 1
        )
