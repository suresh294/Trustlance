import { Contract, BrowserProvider, parseEther } from 'ethers';

export const CHAIN_ID = 80002;
export const CHAIN_HEX = '0x13882';
export const EXPLORER_URL = 'https://amoy.polygonscan.com/tx/';
// Must match the escrow deployment used by the existing jobs API.
export const ESCROW_ADDRESS = '0x9AF814D18DD67B09CceA594d54f625fd63D0B870';
export const REPUTATION_ADDRESS = '0x7D5D056f9F8Aa0b55E11cCB4bDb58CFCA7C80f51';

// Loaded from the deployed Hardhat artifact; no contract interface is invented here.
import artifact from '../../../blockchain/artifacts/contracts/FreelanceEscrow.sol/FreelanceEscrow.json';
export const ESCROW_ABI = artifact.abi;

export function isMetaMaskAvailable() {
  return typeof window !== 'undefined' && Boolean(window.ethereum);
}

export function getProvider() {
  if (!isMetaMaskAvailable()) throw new Error('Please install MetaMask to continue.');
  return new BrowserProvider(window.ethereum);
}

export async function getNetwork() {
  return getProvider().getNetwork();
}

export async function ensurePolygonAmoy() {
  const provider = getProvider();
  const network = await provider.getNetwork();
  if (Number(network.chainId) === CHAIN_ID) return provider;
  try {
    await window.ethereum.request({ method: 'wallet_switchEthereumChain', params: [{ chainId: CHAIN_HEX }] });
  } catch (error) {
    if (error?.code === 4902) {
      await window.ethereum.request({
        method: 'wallet_addEthereumChain',
        params: [{ chainId: CHAIN_HEX, chainName: 'Polygon Amoy', nativeCurrency: { name: 'POL', symbol: 'POL', decimals: 18 }, rpcUrls: ['https://rpc-amoy.polygon.technology'], blockExplorerUrls: ['https://amoy.polygonscan.com'] }],
      });
    } else throw error;
  }
  return new BrowserProvider(window.ethereum);
}

export async function connectWallet() {
  const provider = await ensurePolygonAmoy();
  const accounts = await provider.send('eth_requestAccounts', []);
  if (!accounts[0]) throw new Error('No MetaMask account is connected.');
  return accounts[0];
}

export async function switchWallet() {
  await ensurePolygonAmoy();
  if (!isMetaMaskAvailable()) throw new Error('Please install MetaMask to continue.');
  try {
    await window.ethereum.request({
      method: 'wallet_requestPermissions',
      params: [{ eth_accounts: {} }],
    });
  } catch (error) {
    // Older wallet versions may not expose permission re-selection.
    if (error?.code !== -32601 && error?.code !== -32004) throw error;
  }
  const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });
  if (!accounts[0]) throw new Error('No MetaMask account is connected.');
  return accounts[0];
}

export async function getConnectedAccount() {
  const provider = getProvider();
  const accounts = await provider.send('eth_accounts', []);
  return accounts[0] || '';
}

export async function getSigner(expectedAddress = '') {
  const provider = await ensurePolygonAmoy();
  const signer = await provider.getSigner();
  const address = await signer.getAddress();
  if (expectedAddress && address.toLowerCase() !== expectedAddress.toLowerCase()) {
    throw new Error(`Wrong wallet connected. Connect ${expectedAddress}.`);
  }
  return signer;
}

export async function getEscrowContract(expectedAddress = '') {
  const signer = await getSigner(expectedAddress);
  return new Contract(ESCROW_ADDRESS, ESCROW_ABI, signer);
}

export function transactionUrl(hash) {
  return `${EXPLORER_URL}${hash}`;
}

export { parseEther };
