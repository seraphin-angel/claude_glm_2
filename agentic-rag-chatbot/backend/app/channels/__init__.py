"""P3-53: マルチチャネル対応 - チャネルモジュール"""

from app.channels.models import ChannelType, ChannelMessage, ChannelConfig
from app.channels.base import BaseChannelAdapter

__all__ = [
    "ChannelType",
    "ChannelMessage",
    "ChannelConfig",
    "BaseChannelAdapter",
]
