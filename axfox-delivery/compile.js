// Deterministic compile of AXFOXRegistry. Settings are pinned explicitly so the
// same input always yields the same bytecode and the same verification metadata.
const fs = require('fs');
const solc = require(process.env.SOLC_PATH);

const SOURCE = 'AXFOXRegistry.sol';
const src = fs.readFileSync('contracts/' + SOURCE, 'utf8');
const evmVersion = process.argv[2] || 'paris';

const input = {
  language: 'Solidity',
  sources: { [SOURCE]: { content: src } },
  settings: {
    optimizer: { enabled: true, runs: 200 },
    evmVersion,
    outputSelection: { '*': { '*': ['abi', 'evm.bytecode.object', 'metadata'] } },
  },
};

const out = JSON.parse(solc.compile(JSON.stringify(input)));
(out.errors || []).forEach(e => console.error(`[${e.severity}] ${e.formattedMessage.trim()}`));
if ((out.errors || []).some(e => e.severity === 'error')) process.exit(1);

const c = out.contracts[SOURCE].AXFOXRegistry;
const result = {
  compilerVersion: solc.version(),
  evmVersion,
  optimizer: { enabled: true, runs: 200 },
  abi: c.abi,
  creationBytecode: '0x' + c.evm.bytecode.object,
  creationBytecodeLength: c.evm.bytecode.object.length / 2,
  metadata: JSON.parse(c.metadata),
};
fs.writeFileSync(`build-${evmVersion}.json`, JSON.stringify(result, null, 2));
console.log(`evmVersion=${evmVersion}`);
console.log(`compiler=${result.compilerVersion}`);
console.log(`bytecode_bytes=${result.creationBytecodeLength}`);
console.log(`bytecode_sha_head=${result.creationBytecode.slice(0, 42)}...`);
