"""Teammate model adapter handoff point.

GSK fills this when YASCN and ALIAR deliver their apps. Keeping the adapter here
lets calculation code and endpoint shapes be verified independently meanwhile.
"""


class IntegrationPending(RuntimeError):
    pass


def get_repository():
    raise IntegrationPending("YASCN subscription and ALIAR invoice handoffs are not installed yet")
