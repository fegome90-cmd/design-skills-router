#!/usr/bin/env python3
"""Run the installed-CLI tests under a POSIX C locale, minus documented exclusions.

CI calls this with LC_ALL=C, PYTHONUTF8=0 and PYTHONCOERCECLOCALE=0, so the
filesystem encoding is ASCII. The excluded tests pass non-ASCII command-line
arguments to a subprocess on purpose; POSIX cannot encode them in that
locale, so they fail in the test harness before the CLI runs. They still run
in the normal UTF-8 steps. An exclusion that no longer names a discovered
test is an error, so the list cannot go stale.
"""

from __future__ import annotations

import sys
import unittest

START = 'packages/cli/tests'
REASON = 'Passes non-ASCII argv, which an ASCII filesystem encoding cannot represent.'
EXCLUDED = {
    'test_installed_cli.InstalledCliTests.test_json_streams_preserve_unicode_with_redirected_cp1252_output': REASON,
    'test_installed_cli.InstalledCliTests.test_pretty_status_escapes_values_unrepresentable_in_console_encoding': REASON,
    'test_mcp_operation_policy.InstalledOperationPolicyTests.test_search_denied_without_index_or_ledger_mutation': REASON,
    'test_mcp_operation_policy.InstalledOperationPolicyTests.test_unrestricted_catalog_metadata_and_four_operations': REASON,
    'test_mcp_parity.InstalledMcpParityTests.test_g5_contract_through_installed_cli_and_stdio': REASON,
}


def flatten(suite):
    for test in suite:
        if isinstance(test, unittest.TestSuite):
            yield from flatten(test)
        else:
            yield test


def main() -> int:
    tests = list(flatten(unittest.defaultTestLoader.discover(START)))
    ids = {test.id() for test in tests}
    stale = sorted(set(EXCLUDED) - ids)
    if stale:
        print('Stale exclusions: ' + ', '.join(stale), file=sys.stderr)
        return 2
    for test_id, reason in EXCLUDED.items():
        print(f'excluded: {test_id}: {reason}', file=sys.stderr)
    kept = [test for test in tests if test.id() not in EXCLUDED]
    result = unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(kept))
    return 0 if result.wasSuccessful() and result.testsRun == len(kept) else 1


if __name__ == '__main__':
    sys.exit(main())
