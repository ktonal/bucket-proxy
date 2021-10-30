from app.main import app


class Client:
    """quick and dirty wrapper to call the app's endpoints"""
    _app = app

    def __init__(self):
        self._routes = {r.endpoint.__name__: r.endpoint for r in self._app.routes}

    def __getattr__(self, item):
        return self._routes[item]


if __name__ == '__main__':
    client = Client()

    print(client.list_tables())
    # print(client.get_table("verdiX"))
