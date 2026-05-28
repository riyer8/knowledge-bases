"""
Banking, financial, and credential-related domains that trigger auto-pause.
Add new entries here — nowhere else.
"""

SENSITIVE_DOMAINS: frozenset[str] = frozenset({
    # Banking
    "bankofamerica.com",
    "chase.com",
    "wellsfargo.com",
    "citibank.com",
    "usbank.com",
    "capitalone.com",
    "tdbank.com",
    "pnc.com",
    "regions.com",
    "suntrust.com",
    "ally.com",
    "discover.com",
    "schwab.com",
    "fidelity.com",
    "vanguard.com",
    "etrade.com",
    "robinhood.com",
    "coinbase.com",
    "kraken.com",
    # Payment processors
    "paypal.com",
    "venmo.com",
    "cashapp.com",
    "zelle.com",
    "stripe.com",
    # Tax / government financial
    "irs.gov",
    "turbotax.com",
    "hrblock.com",
    # Password managers / credential stores
    "1password.com",
    "lastpass.com",
    "bitwarden.com",
    "dashlane.com",
    "keeper.io",
    # Healthcare (HIPAA-sensitive)
    "mychart.com",
    "healthgrades.com",
    "webmd.com",
    # Identity / auth
    "accounts.google.com",
    "login.microsoftonline.com",
    "appleid.apple.com",
    "login.yahoo.com",
    "auth.twitter.com",
    "facebook.com/login",
})

SENSITIVE_WINDOW_TITLE_KEYWORDS: frozenset[str] = frozenset({
    "password",
    "login",
    "log in",
    "sign in",
    "signin",
    "credentials",
    "banking",
    "1password",
    "keychain",
    "bitwarden",
    "lastpass",
    "secure note",
    "two-factor",
    "2fa",
    "authenticator",
    "ssn",
    "social security",
})

SENSITIVE_APP_NAMES: frozenset[str] = frozenset({
    "1password",
    "keychain access",
    "lastpass",
    "bitwarden",
    "dashlane",
    "keeper",
    "authy",
    "google authenticator",
    "microsoft authenticator",
})
