#!/usr/bin/env python3
"""Build the exact AXFOXRegistry deployment payload and verify its inputs."""
import json, sys
from eth_abi import encode
from eth_utils import keccak, to_checksum_address, is_checksum_address

TOKEN   = "0x3ABFBDf7a12Cb7589a330A293e91380f84A94444"
NAME    = "AxolotlFox"
TICKER  = "AXFOX"
VERSION = "1"                                # NOTE: contract declares `string version`
WEBSITE = "https://axfox.quadproxy.com"

evm = sys.argv[1] if len(sys.argv) > 1 else "paris"
build = json.load(open(f"build-{evm}.json"))

print("=== ADDRESS VALIDATION ===")
try:
    cs = to_checksum_address(TOKEN)
    print(f"token as supplied : {TOKEN}")
    print(f"EIP-55 checksum   : {cs}")
    print(f"supplied is valid : {is_checksum_address(TOKEN)}")
    if cs != TOKEN:
        print(f"!! MISMATCH - supplied casing is NOT the EIP-55 checksum form")
except Exception as e:
    print("INVALID ADDRESS:", e); sys.exit(1)

# Confirm the constructor signature matches what we are encoding.
ctor = next(x for x in build["abi"] if x["type"] == "constructor")
types = [i["type"] for i in ctor["inputs"]]
names = [i["name"] for i in ctor["inputs"]]
print("\n=== CONSTRUCTOR ===")
print("order :", list(zip(names, types)))
assert types == ["address", "string", "string", "string", "string"], f"unexpected: {types}"

args = encode(types, [cs, NAME, TICKER, VERSION, WEBSITE])
bytecode = build["creationBytecode"]
data = bytecode + args.hex()

print("\n=== DEPLOYMENT PAYLOAD ===")
print(f"compiler        : {build['compilerVersion']}")
print(f"evmVersion      : {build['evmVersion']}")
print(f"optimizer       : enabled={build['optimizer']['enabled']} runs={build['optimizer']['runs']}")
print(f"bytecode bytes  : {build['creationBytecodeLength']}")
print(f"ctor args bytes : {len(args)}")
print(f"total data bytes: {len(bytes.fromhex(data[2:]))}")
print(f"keccak256(data) : 0x{keccak(hexstr=data).hex()}")
print(f"data head       : {data[:66]}...")
print(f"data tail       : ...{data[-64:]}")

out = {
    "compilerVersion": build["compilerVersion"],
    "evmVersion": build["evmVersion"],
    "optimizer": build["optimizer"],
    "constructorArgs": {"_token": cs, "_projectName": NAME, "_ticker": TICKER,
                        "_version": VERSION, "_officialWebsite": WEBSITE},
    "constructorArgsEncoded": "0x" + args.hex(),
    "creationBytecode": bytecode,
    "deploymentData": data,
    "deploymentDataHash": "0x" + keccak(hexstr=data).hex(),
    "abi": build["abi"],
}
json.dump(out, open(f"deployment-{evm}.json", "w"), indent=2)
print(f"\nwrote deployment-{evm}.json")

print("\n=== TRANSACTION SHAPE (note: no 'to' key) ===")
tx = {"from": "<connectedAccount>", "value": "0x0", "data": data[:20] + "...(truncated)"}
print(json.dumps(tx, indent=2))
print("keys:", sorted(tx.keys()), "-> 'to' absent:", "to" not in tx)
