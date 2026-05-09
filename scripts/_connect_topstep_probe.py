"""Internal probe for connect-topstep.ps1. Do not run directly."""

import json
import sys

from tools.projectx_client import ProjectXClient, ProjectXError


def main() -> int:
    try:
        c = ProjectXClient()
        c.authenticate()
        print("AUTH_OK")
        accounts = c.get_accounts(only_active=True)
        print("ACCOUNTS_JSON::" + json.dumps(accounts, default=str))
        return 0
    except ProjectXError as e:
        print(f"AUTH_FAIL::{e}")
        return 1
    except Exception as e:
        print(f"AUTH_EXCEPTION::{type(e).__name__}: {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
