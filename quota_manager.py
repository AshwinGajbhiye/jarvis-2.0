import os
import json
import hashlib
from datetime import datetime

from config import Config

class QuotaManager:
    """Manages local tracking of API key quotas to avoid hitting rate limits blindly."""
    
    # 1500 for gemini-flash-latest free tier
    MAX_QUOTA_PER_DAY = 1500 

    def __init__(self):
        self.quota_file = os.path.join(Config.HISTORY_DIR, "quota.json")
        os.makedirs(Config.HISTORY_DIR, exist_ok=True)
        self.usage = self._load()

    def _hash_key(self, api_key: str) -> str:
        """Hash the API key so we don't store it in plain text."""
        if not api_key:
            return "none"
        return hashlib.sha256(api_key.encode()).hexdigest()[:12]

    def _load(self) -> dict:
        """Load the quota file from disk."""
        if os.path.exists(self.quota_file):
            try:
                with open(self.quota_file, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save(self):
        """Save the quota file to disk."""
        try:
            with open(self.quota_file, "w") as f:
                json.dump(self.usage, f)
        except Exception as e:
            print(f"Failed to save quota: {e}")

    def _get_entry(self, api_key: str) -> dict:
        """Get the quota entry for a specific key, resetting it if it's a new day."""
        key_hash = self._hash_key(api_key)
        today = datetime.now().strftime("%Y-%m-%d")

        if key_hash not in self.usage:
            self.usage[key_hash] = {"date": today, "remaining": self.MAX_QUOTA_PER_DAY}
        else:
            # Reset quota if it's a new day
            if self.usage[key_hash].get("date") != today:
                self.usage[key_hash] = {"date": today, "remaining": self.MAX_QUOTA_PER_DAY}

        return self.usage[key_hash]

    def get_remaining(self, api_key: str) -> int:
        """Get the remaining quota for an API key."""
        entry = self._get_entry(api_key)
        return entry.get("remaining", self.MAX_QUOTA_PER_DAY)

    def decrement(self, api_key: str, amount: int = 1):
        """Decrement the quota for an API key after a successful request."""
        if not api_key:
            return
            
        entry = self._get_entry(api_key)
        remaining = entry.get("remaining", self.MAX_QUOTA_PER_DAY)
        
        # Don't go below 0
        new_remaining = max(0, remaining - amount)
        self.usage[self._hash_key(api_key)]["remaining"] = new_remaining
        self._save()

    def set_exhausted(self, api_key: str):
        """Force the quota to 0 if a 429 Quota Exceeded error is explicitly caught."""
        if not api_key:
            return
            
        entry = self._get_entry(api_key)
        self.usage[self._hash_key(api_key)]["remaining"] = 0
        self._save()

