from supabase import Client

class SupabaseFileStore:
    def __init__(self, client: Client, bucket: str = "documents"):
        self.client = client
        self.bucket = bucket

    def upload(self, local_path: str, path: str) -> str:
        with open(local_path, "rb") as f:
            self.client.storage.from_(self.bucket).upload(
                path=path,
                file=f,
                file_options={"content-type": "text/plain"},
            )
        return self.client.storage.from_(self.bucket).get_public_url(path)

    def download_to_local(self, path: str, local_path: str) -> None:
        data = self.client.storage.from_(self.bucket).download(path)
        with open(local_path, "wb") as f:
            f.write(data)