# Third-Party Notices

This project includes or is based on code from the following open source projects:

---

## x402 Protocol - Coinbase

- **Source**: https://github.com/coinbase/x402/tree/main/python/x402
- **License**: Apache-2.0
- **Copyright**: Copyright (c) Coinbase, Inc.
- **Usage**: Vendored in `httpayer/_vendor/x402/` with modifications for HTTPayer integration

### Description
The x402 protocol implementation provides the core functionality for handling HTTP 402 Payment Required responses with cryptographic payment authorization. HTTPayer uses a modified version to support both proxy and relay modes.

### Modifications
- Integration with HTTPayer client architecture
- Additional helper functions for cross-chain payments
- Custom encoding/decoding utilities

---

## x402python - OrbytLabz

- **Source**: https://github.com/OrbytLabz/x402python
- **License**: Apache-2.0
- **Copyright**: Copyright (c) OrbytLabz
- **Usage**: Referenced implementation for Solana x402 protocol support

### Description
The x402python project provides Solana-compatible x402 protocol implementation. HTTPayer's Solana implementation (`httpayer/x402_solana/`) is built using concepts and patterns from this project, adapted for HTTPayer's specific requirements.

---

## Full License Texts

### Apache License 2.0

The Apache-2.0 license text is included in this repository at:
- `httpayer/_vendor/LICENSE-APACHE-2.0`

The full license is also available at: https://www.apache.org/licenses/LICENSE-2.0

---

## Notice

This THIRD_PARTY_NOTICES file is required by the Apache-2.0 license to provide proper attribution to the original authors. HTTPayer Inc. is grateful for the open source contributions that made this SDK possible.

For questions regarding third-party licenses, contact: legal@httpayer.com
