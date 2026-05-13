"""Extended JSON encoder for types stdlib `json` can't serialize.

Living under `qux.utils` (rather than the package root) keeps stdlib `json`
imports safe: `import json` resolves to stdlib unless cwd is literally
inside `src/qux/utils/`.

Use:

    import json
    from qux.utils.json import QuxComplexEncoder
    json.dumps(payload, cls=QuxComplexEncoder)

Coverage:
- objects with `.isoformat()` (datetime, date, time) → ISO-8601 string
- `decimal.Decimal` → string with full precision
- `uuid.UUID` → hex string
- numpy scalars (`np.int64`, `np.float32`, etc.) → native Python type via `.item()`
"""

from __future__ import annotations

import decimal
import json
import uuid
from typing import Any

try:
    import numpy as np
except ImportError:
    np = None  # type: ignore[assignment]


class QuxComplexEncoder(json.JSONEncoder):
    """JSONEncoder that handles datetime, Decimal, UUID, and numpy scalars."""

    def default(self, o: Any) -> Any:
        if hasattr(o, "isoformat"):
            return o.isoformat()
        if isinstance(o, decimal.Decimal):
            return f"{o:f}"
        if isinstance(o, uuid.UUID):
            return o.hex
        if np is not None and isinstance(o, np.generic):
            return o.item()
        return super().default(o)
