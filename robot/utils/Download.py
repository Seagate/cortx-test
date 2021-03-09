"""This Utility function is for downloading files from required sources."""
import requests


def download_file(file_download_path, file_save_path="temp.iso"):
    """
    This function is used to download file update
    :param file_download_path: File path from where the file for FW update can be downloaded
    :param file_save_path:  The file path to be saved
    :return:  None
    """
    # Streaming file to download path
    with requests.get(file_download_path, stream=True) as result:
        result.raise_for_status()
        with open(file_save_path, 'wb') as file_data:
            for chunk in result.iter_content(chunk_size=10240):
                file_data.write(chunk)
