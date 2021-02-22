# .. _persister_example:

import os


class FilesystemPersister:
    @classmethod
    def load_cassette(cls, cassette_path, serializer):
        try:
            with open(cassette_path) as f:
                cassette_content = f.read()
        except OSError:
            raise ValueError("Cassette not found.")
        cassette = serializer.deserialize(cassette_content, serializer)
        return cassette

    @staticmethod
    def save_cassette(cassette_path, cassette_dict, serializer):
        data = serializer.serialize(cassette_dict)
        dirname, filename = os.path.split(cassette_path)
        if dirname and not os.path.exists(dirname):
            os.makedirs(dirname)
        with open(cassette_path, "a+") as f:
            f.write(data)
