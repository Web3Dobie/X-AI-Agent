from azure.storage.blob import BlobServiceClient, ContentSettings
import os

# Load from env or config
AZURE_CONNECTION_STRING = os.getenv("AZURE_BLOB_CONNECTION_STRING")
AZURE_CONTAINER_NAME = os.getenv("AZURE_BLOB_CONTAINER_NAME", "substack-articles")

def upload_to_blob(filepath: str, blob_name: str = None, content_type: str = "text/markdown") -> str:
    """
    Uploads a file to Azure Blob Storage. Returns the public Blob URL.
    """
    blob_service_client = BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)
    container_client = blob_service_client.get_container_client(AZURE_CONTAINER_NAME)
    if not blob_name:
        blob_name = os.path.basename(filepath)
    with open(filepath, "rb") as data:
        container_client.upload_blob(
            name=blob_name,
            data=data,
            overwrite=True,
            content_settings=ContentSettings(content_type=content_type)
        )
    # Construct the Blob URL (update if your blob is in a different region/custom domain)
    account = blob_service_client.account_name
    blob_url = f"https://{account}.blob.core.windows.net/{AZURE_CONTAINER_NAME}/{blob_name}"
    return blob_url
