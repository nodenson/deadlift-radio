from db.schema import init_db
from cli.menu import run_menu

if __name__ == "__main__":
    init_db()
    run_menu()