# NFT Art Factory

A draft-first creator workflow for original artwork and AI-generated artwork.

## Creator paths
- **Your own work:** prepare original image files and collection details.
- **AI-created work:** generate drafts through the Cloudflare Workers AI adapter.
- Both paths enter human review before any public upload, mint, or marketplace listing.

## Creator Studio
Run `npm run studio` to generate the local-first creator page at `dist/gallery/index.html`. It previews the collection and lets you select an image, enter its title and description, and download an NFT metadata draft.

**Current boundary:** this browser intake is a local prototype. The selected image is not uploaded to a server, and the metadata draft is not automatically added to the collection. It does not mint, list, or initiate a sale.

## Pipeline
1. Prepare original artwork in `assets/`.
2. Describe items in `collection.json`.
3. Validate and build ERC-721-compatible metadata with `npm run build`.
4. Review creator rights, commercial-use permissions, marketplace eligibility, fees and royalties.
5. Upload approved artwork and metadata to IPFS using the Pinata adapter.
6. Use marketplace integrations only where official APIs support the selected network and account. Wallet signing and irreversible actions require explicit owner approval.

## Commands
- `npm test` — run automated tests.
- `npm run build` — validate collection and build metadata.
- `npm run gallery` — generate the read-only collection gallery.
- `npm run studio` — generate the interactive local-first creator page.
- `npm run generate` — create AI artwork drafts (requires configured provider secrets and explicit draft-only config).
- `npm run pin:approved` — upload only items that have passed the rights and owner-approval gates.

## Provider setup
See [secure provider setup](docs/SETUP_SECRETS.md) and [provider/storage notes](docs/PROVIDERS_AND_STORAGE.md).

## Safety
- Never commit seed phrases, private keys, wallet files, or API secrets.
- Public IPFS uploads are public; only upload after confirming ownership and rights.
- No automatic transaction signing is enabled.
- A listing or asking price is not proof of a completed sale; sales must be verified on-chain.
- Provider free tiers have limits and may change.
