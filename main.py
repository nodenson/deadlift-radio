from db.schema import init_db
from cli.menu import run_menu
from cli.query_router import handle_archive_query
import sys

if __name__ == "__main__":
    init_db()
    if len(sys.argv) > 1:
        query_text = " ".join(sys.argv[1:])
        handle_archive_query(query_text)
    else:
        run_menu()
