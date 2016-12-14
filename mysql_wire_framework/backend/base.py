class ServerImplementation(object):
    def get_display_version(self):
        return "MySQL Wire Server"

    def handle_query(self, query):
        # Maybe have some streaming attempt first - headers then streaming
        # rows as something distinct?
        return self.structured_query_response(query)
