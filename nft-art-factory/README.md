# NFT Art Factory

A separate, isolated NFT workflow inside the AI Shorts Factory repository.

## Pipeline
1. Prepare original artwork in `assets/`.
2. Describe each work in `collection.json`.
3. Run the metadata builder and validation.
4. Upload artwork + JSON metadata to an IPFS-compatible pinning provider (provider adapter is a later step; credentials must be GitHub Actions secrets, never committed).
5. Review marketplace/network eligibility, fees, royalties and creator terms.
6. Mint/list through a marketplace adapter only where its documented API supports it. Wallet signing and irreversible blockchain actions require an explicit owner approval step.

## Two ways to add artwork

- **Your own artwork:** add the file under `assets/` and prepare its intake record using `workflows/artwork-intake.example.json`.
- **AI-created artwork:** configure a provider using `workflows/ai-generation.example.json`. Provider execution is not enabled until a real provider adapter and its server-side credentials are configured.
- Both routes feed the same review and marketplace pipeline. Draft-only is the default; rights review and owner approval are required before minting/listing.

See [`docs/CREATOR_WORKFLOWS.md`](docs/CREATOR_WORKFLOWS.md) for the full process.
See [`docs/SETUP_SECRETS.md`](docs/SETUP_SECRETS.md) for secure provider setup.\nSee [`docs/SETUP_SECRETS.md`](docs/SETUP_SECRETS.md) for secure provider setup.

## Current MVP
- Validates collection and item fields.
- Checks that referenced local artwork files exist.
- Generates ERC-721-compatible JSON metadata into `dist/metadata/`.
- Produces a build manifest.
- GitHub Actions can run the validation/build on demand.

## Run locally
```bash
cd nft-art-factory
npm run build
```

Use `collection.example.json` as a template and copy it to `collection.json`. Put artwork files under `assets/`.

## Important safety and marketplace constraints
- Never put seed phrases, private keys, wallet JSON files, or API secrets in the repository.
- No automatic transaction signing is enabled. Minting and listing are irreversible/financial actions and must be confirmed by the wallet owner.
- Marketplace APIs and eligibility differ by country, chain and collection. Do not assume OpenSea or any specific marketplace is available to every creator. Select a marketplace only after checking its current terms and API support for the creator's actual location.
- A displayed asking price is not proof of a completed sale. Track on-chain sale transactions separately.
- Only upload artwork you own or are licensed to use.

## AI generation and IPFS storage

- Cloudflare Workers AI adapter for FLUX.1 [schnell], with a draft-only generation queue.
- Pinata public IPFS upload adapter, gated by explicit rights and owner approval.
- See [`docs/PROVIDERS_AND_STORAGE.md`](docs/PROVIDERS_AND_STORAGE.md) for setup, current limits, and safety boundaries.

## Planned adapters
- IPFS pinning provider
- Marketplace capability/eligibility checker
- Marketplace listing adapter (only for officially documented APIs)
- Sales and royalty tracker

The adapters are intentionally not represented as complete until tested against a real provider account and network.
