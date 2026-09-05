import subprocess
import os

# Global state to hold the queued file path for the current response
_queued_file = None

def get_queued_file():
    global _queued_file
    f = _queued_file
    _queued_file = None # Clear it after reading
    return f

def search_and_send_file(filename: str) -> str:
    """Search for a file on the Mac by name and queue it to be sent to the user's mobile device."""
    global _queued_file
    try:
        # Use mdfind to search for the file
        result = subprocess.run(["mdfind", "-name", filename], capture_output=True, text=True)
        paths = result.stdout.strip().split('\n')
        
        valid_paths = [p for p in paths if p and os.path.isfile(p)]
        
        if not valid_paths:
            return f"I couldn't find any file named '{filename}', Sir."
            
        # Select the first valid match (usually the most relevant or recent)
        best_match = valid_paths[0]
        
        # Queue the file for the API to attach
        _queued_file = best_match
        
        return f"I found the file '{os.path.basename(best_match)}'. I am sending it to your mobile device now, Sir."
        
    except Exception as e:
        return f"I encountered an error while searching for the file: {e}"

FILE_TOOLS = [
    {
        "name": "search_and_send_file",
        "description": "Searches for a file by name on the Mac and sends it securely to the user's mobile device. Use this whenever the user asks for a file.",
        "parameters": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "The name or partial name of the file to search for and send."
                }
            },
            "required": ["filename"]
        },
        "function": search_and_send_file
    }
]
