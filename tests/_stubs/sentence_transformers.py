class SentenceTransformer:
    """Minimal stub of sentence_transformers.SentenceTransformer used for tests.

    This avoids importing heavy libraries (torch, numpy) during test runs in
    environments where those packages aren't installed.
    """
    def __init__(self, model_name: str):
        self.model_name = model_name

    def encode(self, text, convert_to_numpy=False):
        # Return a fixed-length list of zeros (mock embedding)
        return [0.0] * 384
