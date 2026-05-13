"""Random-string / random-number generators.

Use stdlib :mod:`random` for arithmetic randomness; use this module for string
or numeric-string identifiers (codes, slugs, throwaway IDs).

Note on shadowing: `qux.utils.random` shares its leaf name with stdlib
`random`. Living under `qux.utils` (rather than the package root) means the
collision only triggers if scripts are run with cwd inside `src/qux/utils/`
itself — vanishingly unlikely. From a normal venv with `qux` installed,
`import random` always resolves to stdlib.
"""

from __future__ import annotations

import random
import string


def random_string(length: int = 8) -> str:
    """Return ``length`` ASCII letters chosen with stdlib `random.choice`."""
    letters = string.ascii_letters
    return "".join(random.choice(letters) for _ in range(length))


def random_number(length: int = 10) -> str:
    """Return ``length`` decimal digits chosen with stdlib `random.choice`. String form."""
    numbers = string.digits
    return "".join(random.choice(numbers) for _ in range(length))
