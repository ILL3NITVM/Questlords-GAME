# Reproducing the AXFOXRegistry deployment payload

Deterministic. Same inputs -> same bytecode -> same hash. Verify before you sign.

## Pinned settings

| Setting | Value |
|---|---|
| compiler | `0.8.24+commit.e11b9ed9.Emscripten.clang` |
| evmVersion | `paris` |
| optimizer | enabled, runs = 200 |

**Why `paris` and not `shanghai`:** solc 0.8.24 defaults to `shanghai`, which emits the
`PUSH0` (`0x5f`) opcode. BNB Smart Chain supports it on current nodes, but `paris` avoids
the dependency entirely at a cost of 39 bytes (1553 vs 1514). For a one-shot immutable
registry, maximum compatibility beats 39 bytes. A `shanghai` build is also produced if
you prefer it — the code is identical, only the opcode set differs.

## Reproduce

```bash
npm install solc@0.8.24
SOLC_PATH=./node_modules/solc node compile.js paris
python3 encode.py paris
```

## Expected output (verify these match before signing)

```
compiler        : 0.8.24+commit.e11b9ed9.Emscripten.clang
evmVersion      : paris
optimizer       : enabled=True runs=200
bytecode bytes  : 1553
ctor args bytes : 416
total data bytes: 1969
keccak256(data) : 0xb940a80dfabf84f70d803aa422db686628f073d84b39ef31319d4e7b17c67c96
```

## Constructor arguments

| Param | Type | Value |
|---|---|---|
| `_token` | address | `0x3ABFBDf7a12Cb7589a330A293e91380f84A94444` (EIP-55 checksum **valid**) |
| `_projectName` | string | `AxolotlFox` |
| `_ticker` | string | `AXFOX` |
| `_version` | **string** | `"1"` |
| `_officialWebsite` | string | `https://axfox.quadproxy.com` |

> **`_version` is a string, not a number.** The contract declares `string public version`.
> Encoding it as a uint would produce different bytecode and a contract whose `version()`
> getter does not return `"1"`. The spec said "version: 1"; the type system says otherwise,
> and the type system wins.

## Transaction shape

```json
{ "from": "<connectedAccount>", "value": "0x0", "data": "0x60a06040..." }
```

No `to` key. `buildTx()` asserts its absence, and `deploy()` re-asserts immediately
before `eth_sendTransaction`.
