try:
    import simplejson as json
except ImportError:
    import json


class JsonSerializer:
    @staticmethod
    def deserialize(cassette_string):
        return json.loads(cassette_string)

    @staticmethod
    def serialize(cassette_dict):
        try:
            return json.dumps(cassette_dict, indent=4)
        except UnicodeDecodeError as original:  # py2
            raise UnicodeDecodeError(
                original.encoding,
                b"Error serializing cassette to JSON",
                original.start,
                original.end,
                original.args[-1] + error_message,
            )
        except TypeError:  # py3
            raise TypeError(error_message)
