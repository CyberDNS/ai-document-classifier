import time
import os
import shutil
from threading import Thread
from watchdog.observers.polling import PollingObserver
from watchdog.events import FileSystemEventHandler
from dotenv import load_dotenv
from api import start_flask_server

# Load environment variables from .env file
load_dotenv()

# Get the SMB share path and data path from environment variables
SMB_SHARE_PATH = os.getenv("SMB_MOUNTPOINT")
DATA_PATH = os.getenv("DATA_PATH")
IMAGES_PATH = os.path.join(DATA_PATH, "images")

# Ensure the images directory exists
os.makedirs(IMAGES_PATH, exist_ok=True)

class ScanHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        if event.src_path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff')):
            print(f"Image file created: {event.src_path}")
            thread = Thread(target=self.copy_and_verify_file, args=(event.src_path,))
            thread.start()
        else:
            print(f"Non-image file created: {event.src_path}")

    def copy_and_verify_file(self, src_path, timeout=30):
        """Copy the file and verify it is fully written before deleting the source file."""
        filename = os.path.basename(src_path)
        dest_path = os.path.join(IMAGES_PATH, filename)

        start_time = time.time()
        while True:
            if self.is_file_fully_written(dest_path):
                print(f"File {dest_path} is fully written.")
                shutil.move(src_path, dest_path)
                print(f"Moved file to: {dest_path}")
                break
            if time.time() - start_time > timeout:
                print(f"Timeout waiting for file {dest_path} to be fully written.")
                break
            time.sleep(1)

    def is_file_fully_written(self, file_path):
        """Check if the file is fully written by comparing its size over time."""
        initial_size = os.path.getsize(file_path)
        time.sleep(10)
        new_size = os.path.getsize(file_path)
        return initial_size == new_size

def start_smb_watcher():
    """Starts the SMB share watcher."""
    print("Initializing ScanHandler...")
    event_handler = ScanHandler()
    observer = PollingObserver()
    watch_path = os.path.join(SMB_SHARE_PATH, "input")
    
    # Check if the watch path exists
    if not os.path.exists(watch_path):
        print(f"Error: Watch path does not exist: {watch_path}")
        return
    
    print(f"Watching path: {watch_path}")
    observer.schedule(event_handler, watch_path, recursive=False)
    observer.start()
    print("Observer started.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping observer...")
        observer.stop()
    observer.join()
    print("Observer stopped.")

if __name__ == "__main__":
    print("Starting SMB watcher and Flask server...")
    watcher_thread = Thread(target=start_smb_watcher)
    flask_thread = Thread(target=start_flask_server)
    watcher_thread.start()
    flask_thread.start()
    watcher_thread.join()
    flask_thread.join()