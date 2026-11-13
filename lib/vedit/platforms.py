"""Delivery limits per platform.

These are defaults, not official guarantees: confirm on the platform before
publishing. Durations are in seconds; ``soft_max`` only warns.
"""

PLATFORMS = {
    "reels": {"label": "Instagram Reels", "min_s": 3, "soft_max_s": 90, "max_s": 180, "max_mb": 1024},
    "tiktok": {"label": "TikTok", "min_s": 3, "soft_max_s": 60, "max_s": 180, "max_mb": 500},
    "shorts": {"label": "YouTube Shorts", "min_s": 3, "soft_max_s": 60, "max_s": 180, "max_mb": 1024},
    "meta-ads": {"label": "Meta Ads (vertical)", "min_s": 3, "soft_max_s": 30, "max_s": 60, "max_mb": 500},
}  # fmt: skip

# Shared by every platform above.
ASPECT = (9, 16)
MIN_WIDTH, MIN_HEIGHT = 1080, 1920
TARGET_LUFS = -14.0
TARGET_TP = -1.5
DEFAULT_PLATFORM = "reels"
