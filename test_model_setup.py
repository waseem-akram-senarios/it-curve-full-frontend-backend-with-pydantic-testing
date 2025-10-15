#!/usr/bin/env python3
"""
Test script to verify model cache setup
"""

import os
import sys
from pathlib import Path

def test_model_cache():
    """Test if model cache is properly set up"""
    print("🧪 Testing model cache setup...")
    
    # Check cache directory
    cache_dir = Path.home() / ".cache" / "livekit"
    if cache_dir.exists():
        print(f"✅ Cache directory exists: {cache_dir}")
    else:
        print(f"❌ Cache directory missing: {cache_dir}")
        return False
    
    # Check environment variable
    env_cache = os.environ.get("LIVEKIT_CACHE_DIR")
    if env_cache:
        print(f"✅ Environment variable set: {env_cache}")
    else:
        print("❌ LIVEKIT_CACHE_DIR not set")
        return False
    
    # Check LiveKit imports
    try:
        from livekit.plugins import silero
        from livekit.plugins.turn_detector.english import EnglishModel
        print("✅ LiveKit plugins imported successfully")
    except ImportError as e:
        print(f"❌ LiveKit import error: {e}")
        return False
    
    print("🎉 Model cache setup verified!")
    return True

if __name__ == "__main__":
    success = test_model_cache()
    sys.exit(0 if success else 1)
