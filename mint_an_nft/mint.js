import { createUmi } from '@metaplex-foundation/umi-bundle-defaults';
import { createNft, mplTokenMetadata } from '@metaplex-foundation/mpl-token-metadata';
import { irysUploader } from '@metaplex-foundation/umi-uploader-irys';
import {
  keypairIdentity,
  generateSigner,
  percentAmount,
  createGenericFile,
} from '@metaplex-foundation/umi';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import bs58 from 'bs58';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

async function main() {
  console.log('===========================================');
  console.log("  THE PUPPET'S TRUMPET - NFT MINTING");
  console.log('===========================================\n');

  // ── Step 1: Connect to Solana Mainnet ──────────────────────────
  console.log('[1/6] Connecting to Solana Mainnet...');
  const umi = createUmi('https://api.mainnet-beta.solana.com')
    .use(mplTokenMetadata())
    .use(irysUploader());
  console.log('  Connected to mainnet-beta\n');

  // ── Step 2: Load wallet keypair ────────────────────────────────
  console.log('[2/6] Loading wallet...');
  const walletPath = path.join(__dirname, 'wallet.json');
  const walletFile = fs.readFileSync(walletPath, 'utf-8');
  const secretKey = new Uint8Array(JSON.parse(walletFile));
  const keypair = umi.eddsa.createKeypairFromSecretKey(secretKey);
  umi.use(keypairIdentity(keypair));
  console.log(`  Address: ${keypair.publicKey}\n`);

  // ── Step 3: Check balance ──────────────────────────────────────
  console.log('[3/6] Checking wallet balance...');
  const balance = await umi.rpc.getBalance(keypair.publicKey);
  const solBalance = Number(balance.basisPoints) / 1_000_000_000;
  console.log(`  Balance: ${solBalance} SOL`);

  if (solBalance < 0.02) {
    console.error(`\n  ERROR: Insufficient balance!`);
    console.error(`  Need at least 0.02 SOL, but wallet has ${solBalance} SOL.`);
    console.error(`  Send SOL to: ${keypair.publicKey}`);
    process.exit(1);
  }
  console.log('  Balance is sufficient.\n');

  // ── Step 4: Upload image to Arweave via Irys ──────────────────
  console.log('[4/6] Uploading image to Arweave via Irys...');
  console.log('  (This may take a moment for a 7MB file...)');
  const imagePath = path.join(__dirname, 'resources', 'main_image.png');
  const imageBuffer = fs.readFileSync(imagePath);

  const imageFile = createGenericFile(imageBuffer, 'main_image.png', {
    contentType: 'image/png',
  });

  const [imageUri] = await umi.uploader.upload([imageFile]);
  console.log(`  Image URI: ${imageUri}\n`);

  // ── Step 5: Upload metadata to Arweave ─────────────────────────
  console.log('[5/6] Uploading metadata to Arweave...');
  const metadata = {
    name: "The Puppet's Trumpet",
    description:
      'A wooden marionette plays a golden trumpet against a digital circuitry backdrop.',
    image: imageUri,
    attributes: [
      { trait_type: 'Style', value: 'Digital Illustration' },
      { trait_type: 'Subject', value: 'Marionette' },
      { trait_type: 'Instrument', value: 'Trumpet' },
      { trait_type: 'Background', value: 'Digital Circuitry' },
    ],
    properties: {
      files: [{ uri: imageUri, type: 'image/png' }],
      category: 'image',
    },
  };

  const metadataUri = await umi.uploader.uploadJson(metadata);
  console.log(`  Metadata URI: ${metadataUri}\n`);

  // ── Step 6: Mint the NFT ───────────────────────────────────────
  console.log('[6/6] Minting NFT on Solana Mainnet...');
  const mint = generateSigner(umi);

  const tx = await createNft(umi, {
    mint,
    name: "The Puppet's Trumpet",
    uri: metadataUri,
    sellerFeeBasisPoints: percentAmount(0),
  }).sendAndConfirm(umi);

  const signature = bs58.encode(tx.signature);

  console.log('\n===========================================');
  console.log('  NFT MINTED SUCCESSFULLY!');
  console.log('===========================================');
  console.log(`  Name:        The Puppet's Trumpet`);
  console.log(`  Mint:        ${mint.publicKey}`);
  console.log(`  Owner:       ${keypair.publicKey}`);
  console.log(`  Metadata:    ${metadataUri}`);
  console.log(`  Image:       ${imageUri}`);
  console.log(`  Tx Sig:      ${signature}`);
  console.log('');
  console.log('  View on Solscan:');
  console.log(`    https://solscan.io/token/${mint.publicKey}`);
  console.log('  View on Explorer:');
  console.log(`    https://explorer.solana.com/address/${mint.publicKey}`);
  console.log('  Transaction:');
  console.log(`    https://solscan.io/tx/${signature}`);
  console.log('===========================================\n');
}

main().catch((err) => {
  console.error('\nMinting failed:', err.message || err);
  if (err.logs) {
    console.error('Transaction logs:', err.logs);
  }
  process.exit(1);
});
