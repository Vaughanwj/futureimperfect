from __future__ import annotations

from dataclasses import dataclass, field

import requests


class MetaTokenRefreshError(RuntimeError):
    pass


@dataclass
class MetaLongLivedTokenRefresher:
    """Exchanges a still-valid long-lived Meta user token for a fresh one
    with another ~60 days on it (grant_type=fb_exchange_token). Meta does
    not auto-renew these, and a token that expires silently would break
    every future post with no warning - this is meant to run on a weekly
    cron, well inside the 60-day window, so the token never gets close to
    expiry.
    """

    app_id: str
    app_secret: str
    api_version: str = "v21.0"
    session: requests.Session = field(default_factory=requests.Session)

    def refresh(self, current_token: str) -> str:
        resp = self.session.get(
            f"https://graph.facebook.com/{self.api_version}/oauth/access_token",
            params={
                "grant_type": "fb_exchange_token",
                "client_id": self.app_id,
                "client_secret": self.app_secret,
                "fb_exchange_token": current_token,
            },
            timeout=30,
        )
        if not resp.ok:
            raise MetaTokenRefreshError(f"token refresh failed ({resp.status_code}): {resp.text}")
        data = resp.json()
        new_token = data.get("access_token")
        if not new_token:
            raise MetaTokenRefreshError(f"no access_token in refresh response: {data}")
        return new_token
