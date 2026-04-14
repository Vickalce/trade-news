from datetime import datetime, timezone
from pathlib import Path

from api.core.config import settings



def deliver_stub_alert(channel: str, payload: str) -> str:
    channel_name = channel.lower()
    out_dir = Path(settings.alert_output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"{channel_name}_{stamp}.log"
    out_path.write_text(payload, encoding="utf-8")
    return "delivered"
