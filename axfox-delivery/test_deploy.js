// Tests the deployment control's safety properties against a mock EIP-1193 provider.
const assert = require('assert');
const path = require('path');

const ADDR = "0x203f3D9E101a8A2ADb4c49652eFB1240174a5569";
const DEPLOYED = "0x1111111111111111111111111111111111111111";

function encStr(s) {
  const hex = Buffer.from(s, 'utf8').toString('hex');
  const len = (s.length).toString(16).padStart(64, '0');
  const body = hex.padEnd(Math.ceil(hex.length / 64) * 64, '0');
  return '0x' + (32).toString(16).padStart(64, '0') + len + body;
}

function mock(opts = {}) {
  const sent = [];
  let polls = 0;
  return {
    sent, get polls() { return polls; },
    async request({ method, params }) {
      switch (method) {
        case 'eth_chainId': return opts.chainId || '0x38';
        case 'eth_accounts': return [ADDR];
        case 'eth_estimateGas': return '0x4c4b40';
        case 'eth_sendTransaction': sent.push(params[0]); return '0xdeadbeef';
        case 'eth_getTransactionReceipt':
          polls++;
          if (polls < (opts.receiptAfter ?? 1)) return null;
          return { transactionHash: '0xdeadbeef', contractAddress: DEPLOYED,
                   blockNumber: '0x2a', status: opts.status || '0x1' };
        case 'eth_call': {
          const sel = params[0].data;
          if (sel === '0xfc0c546a') return '0x' + '0'.repeat(24) +
            (opts.token || "3ABFBDf7a12Cb7589a330A293e91380f84A94444").toLowerCase();
          if (sel === '0x9a33e300') return encStr(opts.name || 'AxolotlFox');
          if (sel === '0x8ba47bdd') return encStr('AXFOX');
          if (sel === '0x54fd4d50') return encStr('1');
          if (sel === '0xbf3d9995') return encStr('https://axfox.quadproxy.com');
        }
      }
      throw new Error('unexpected method ' + method);
    }
  };
}

let fails = 0;
const check = (name, cond, extra='') => {
  if (!cond) fails++;
  console.log(`${cond ? 'PASS' : 'FAIL'}  ${name}${extra ? '  ' + extra : ''}`);
};

(async () => {
  global.window = global;
  global.ethereum = mock();
  delete require.cache[require.resolve('./public/axfox-registry-deploy.js')];
  require('./public/axfox-registry-deploy.js');
  const M = global.AXFOXRegistryDeploy;

  // 1. transaction shape
  const tx = M._internal.buildTx(ADDR);
  check("tx omits 'to' (contract creation)", !('to' in tx));
  check("tx value is exactly zero", tx.value === '0x0');
  check("tx carries creation data", tx.data.startsWith('0x60a06040'));

  // 2. preview
  const p = await M.preview();
  check("preview action is CREATE CONTRACT", p.action === 'CREATE CONTRACT');
  check("preview reports real gas estimate", p.estimatedGas === 5000000, `gas=${p.estimatedGas}`);
  check("preview exposes data hash", /^0x[0-9a-f]{64}$/.test(p.deploymentDataHash));
  check("preview confirms no 'to'", p.hasToProperty === false);
  check("preview names real compiler", p.compiler.startsWith('0.8.24+commit'));

  // 3. the human gate
  let blocked = false;
  try { await M.deploy('deploy axfox registry'); } catch { blocked = true; }
  check("wrong-case phrase is REJECTED", blocked && global.ethereum.sent.length === 0);
  blocked = false;
  try { await M.deploy(''); } catch { blocked = true; }
  check("empty phrase is REJECTED", blocked && global.ethereum.sent.length === 0);

  // 4. wrong network refusal
  global.ethereum = mock({ chainId: '0x1' });
  let netBlocked = false;
  try { await M.deploy(M.CONFIRM_PHRASE); } catch { netBlocked = true; }
  check("wrong network is REFUSED", netBlocked && global.ethereum.sent.length === 0);

  // 5. correct phrase + correct network sends exactly one tx, still without 'to'
  global.ethereum = mock();
  const h = await M.deploy(M.CONFIRM_PHRASE);
  check("exact phrase sends the tx", h === '0xdeadbeef' && global.ethereum.sent.length === 1);
  check("sent tx still omits 'to'", !('to' in global.ethereum.sent[0]));

  // 6. receipt polling with backoff
  global.ethereum = mock({ receiptAfter: 3 });
  const r = await M.waitForReceipt('0xdeadbeef', { initialDelayMs: 5, maxDelayMs: 10 });
  check("polls until receipt appears", global.ethereum.polls === 3, `polls=${global.ethereum.polls}`);
  check("receipt extracts contractAddress", r.contractAddress === DEPLOYED);
  check("receipt extracts blockNumber", r.blockNumber === 42);
  check("receipt marks success", r.succeeded === true);
  check("receipt builds BscScan links", r.bscscanContract.includes('bscscan.com/address/'));

  // 7. timeout path returns null rather than hanging
  global.ethereum = mock({ receiptAfter: 999 });
  const t = await M.waitForReceipt('0xdeadbeef', { timeoutMs: 60, initialDelayMs: 5, maxDelayMs: 10 });
  check("bounded timeout returns null", t === null);

  // 8. on-chain verification, matching
  global.ethereum = mock();
  const v = await M.verifyOnChain(DEPLOYED);
  check("all getters verify", v.verified === true, JSON.stringify(v.values.ticker));
  check("token getter decodes", v.values.token.toLowerCase().endsWith('84a94444'));
  check("version decodes as string '1'", v.values.version === '1');

  // 9. verification DETECTS a mismatch (the check that matters)
  global.ethereum = mock({ name: 'WrongProject' });
  const bad = await M.verifyOnChain(DEPLOYED);
  check("mismatch is DETECTED", bad.verified === false && bad.mismatches[0].getter === 'projectName');

  console.log(fails ? `\n${fails} FAILURE(S)` : '\nALL PASS');
  process.exit(fails ? 1 : 0);
})();
