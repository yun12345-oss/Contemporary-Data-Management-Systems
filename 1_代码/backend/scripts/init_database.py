from app.database import connect, initialize
from app.config import settings

if __name__ == "__main__":
    client = connect()
    initialize(client[settings.database])
    print("MongoDB collections, validators and indexes are ready.")
