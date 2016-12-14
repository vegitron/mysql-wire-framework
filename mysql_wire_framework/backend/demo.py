from mysql_wire_framework.backend.base import ServerImplementation


class DemoBackend(ServerImplementation):
    def get_display_version(self):
        return "Demo Backend Implementation"

    def structured_query_response(self, query):
        data = { "headers": [
                             { "name": "Col1", "type": int },
                             { "name": "Col2", "type": str },
                            ],
                 "rows": [
                            [1, "OK"],
                            [1, "A"],
                            [2, "B"],
                            [4, "C"],
                            [10, "D"],
                            [122, "E"],
                            [11, "Last one"],
                        ]
                    }

        return data

