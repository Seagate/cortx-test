"""This Utility function is for downloading files from required sources."""
import urllib3
import requests


def download_file(file_download_path, file_save_path="temp.iso"):
    """
    This function is used to download file update
    :param file_download_path: path from where the file for FW update can be downloaded
    :param file_save_path: The file path to be saved
    """
    # Streaming file to download path
    with requests.get(file_download_path, stream=True) as r:
        r.raise_for_status()
        with open(file_save_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=10240):
                f.write(chunk)
