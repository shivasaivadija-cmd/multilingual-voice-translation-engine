import pytest
import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def sample_audio_float32():
    """Generate a sample 1-second 16kHz sine wave."""
    import numpy as np
    t = np.linspace(0, 1, 16000)
    return np.sin(2 * np.pi * 440 * t).astype(np.float32)

@pytest.fixture
def silent_audio():
    """Generate 1 second of silence."""
    import numpy as np
    return np.zeros(16000, dtype=np.float32)

@pytest.fixture
def sample_audio_bytes():
    """Generate PCM16 bytes."""
    import numpy as np
    t = np.linspace(0, 1, 16000)
    audio = np.sin(2 * np.pi * 440 * t).astype(np.float32)
    return (audio * 32767).astype(np.int16).tobytes()