"""Synthetic credential fixtures shared by inbox and activity regressions."""
import json

BLOCK_PARTS = ('FAKEBLOCKFIRST', 'FAKEBLOCKSECOND')
BLOCK_CASES = [
    'password: FAKEBLOCKFIRST\n  FAKEBLOCKSECOND\nstatus: OK',
    'password: FAKEBLOCKFIRST\nFAKEBLOCKSECOND\nstatus: OK',
    'api_key: |2- # private value\n  FAKEBLOCKFIRST\n  FAKEBLOCKSECOND\nstatus: OK',
    'key:\n  FAKEBLOCKFIRST\n  FAKEBLOCKSECOND\nstatus: OK',
    'password: |\n  FAKEBLOCKFIRST\n  FAKEBLOCKSECOND\nstatus: OK',
    'api_key: >-\n  FAKEBLOCKFIRST\n  FAKEBLOCKSECOND\nstatus: OK',
    'secret:\n  FAKEBLOCKFIRST\n  FAKEBLOCKSECOND\nstatus: OK',
    'TOKEN:\nFAKEBLOCKFIRST\nFAKEBLOCKSECOND\nstatus: OK',
    '  - authorization: |+\n      FAKEBLOCKFIRST\n      FAKEBLOCKSECOND\n  status: OK',
    'passwd: |\r\n\tFAKEBLOCKFIRST\r\n\tFAKEBLOCKSECOND\r\nstatus: OK',
    json.dumps({'api_key': 'FAKEBLOCKFIRST\nFAKEBLOCKSECOND'}) + '\nstatus: OK',
    '-----BEGIN PRIVATE KEY-----\nFAKEBLOCKFIRST\nFAKEBLOCKSECOND\n-----END PRIVATE KEY-----\nstatus: OK',
    'api_key:\n  -----BEGIN RSA PRIVATE KEY-----\n  FAKEBLOCKFIRST\n  FAKEBLOCKSECOND\n  -----END RSA PRIVATE KEY-----\nstatus: OK',
]
SCHEMES = ['http', 'HTTPS', 'ftp', 'SsH', 'git+ssh', 'custom.PROTO']
CREDENTIAL_CASES = [(value, BLOCK_PARTS) for value in BLOCK_CASES] + [
    (f'{scheme}://FAKEURLUSER:FAKEURLPASS@example.invalid/path?q=ok#note\nstatus: OK',
     ('FAKEURLUSER', 'FAKEURLPASS')) for scheme in SCHEMES
] + [('ssh://FAKEURLUSER@example.invalid/path\nstatus: OK', ('FAKEURLUSER',))]

# A labelled-looking password must not hide the URL authority from redaction.
CREDENTIAL_CASES += [('HTTPS://FAKEURLUSER:token=FAKEURLPASS@example.invalid/path\nstatus: OK', ('FAKEURLUSER', 'FAKEURLPASS'))]

# Padding is part of a continued credential, never an empty field assignment.
PADDED_BLOCK_CASES = [
    ('key:\nRkFLRVNFQ1JFVA==\nstatus: OK', 'key: [redacted]\nstatus: OK'),
    ('token:\nRkFLRVNFQ1JFVA\nU0VDUkVUUEFSVA=\n=\nstatus: OK',
     'token: [redacted]\nstatus: OK'),
    ('secret: first-private-part\nRkFLRVNFQ1JFVA==\n==\nstatus=OK',
     'secret: [redacted]\nstatus=OK'),
    ('password:\r\nRkFLRVNFQ1JFVA==\r\n=\r\nstatus: OK',
     'password: [redacted]\r\nstatus: OK'),
    ('api_key: |-\nFIRSTPRIVATEPART\nRkFLRVNFQ1JFVA==\n=\nstatus: OK',
     'api_key: [redacted]\nstatus: OK'),
]

PUBLIC_FIELD_CASES = [
    json.dumps({'monkey': 'capuchin', 'hockey': 'played indoors', 'turnkey': 'deployment complete'}),
    json.dumps({'refresh_token_count': 312, 'password_hint': 'pet name', 'token bucket': 'full'}),
    'monkey=capuchin hockey: played indoors turnkey=deployment complete',
    'not-password=public x.api_key=public refresh_token_count=312 password_hint=public',
    json.dumps({'some token': 'bucket', 'some api_key': 'public', 'some password': 'hint'}),
    'the token bucket filled; password reset email sent',
]
