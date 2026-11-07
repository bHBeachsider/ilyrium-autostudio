# Receipt: RELOCATION Phase B, packs and image-LoRA toolchain arrive from slm-foundry

Date: 2026-11-06. Lane: RELOCATION (Phase B). Approver: Brad Upham.
Counterpart receipt (Foundry side): `slm-foundry/docs/receipts/2026-11-06-relocation-packs.md` on branch `claude/relocation-packs`.

## Repository state
- Repository: `ilyrium-autostudio` (origin `bHBeachsider/ilyrium-autostudio`, default branch `main`).
- Branch: `claude/relocation-packs`, created from `origin/main` = `adaf7eb` (2026-10-29, "fix(ledger): route fal adapter writes through lib/ledger SHA-256 chain (#28)"). No fetch was run; `origin/main` is as of the last local fetch.
- Worktree: `C:/Users/bradu/Documents/ilyrium-autostudio-worktrees/relocation-packs` (outside the repository, because `.gitignore` does not cover `.claude/worktrees/` and the main checkout is not to be edited).
- Main checkout `C:/Users/bradu/Documents/ilyrium-autostudio`: on `feat/ily-205-console-p0` (`7c5e17e`), 641 dirty entries belonging to Brad at the start. Not entered for edits; read only (hash comparison of studio files). Dirty state preserved.
- `origin/main` vs the dirty feature branch: `origin/main` already contains `projects/stripe/{_training,render_test,lora_seeds,refs}` and `tools/fal`, so every identical-copy check below was made against `origin/main` content. Nothing needed from the dirty branch was missing from `main` (the dirty branch's extra files are Brad's uncommitted work and were not used).

## What was delivered
Pack code, configs, tests and the image-LoRA toolchain copied (not moved: the Foundry originals are removed only on the Foundry branch) from `slm-foundry` `9cc17bf` and, for untracked files, from the Foundry main checkout working tree. Provenance method: **copy plus receipt** (`git filter-repo` is not installed, and installing it is a download). Bytes were copied exactly, source SHA-256 equals copy SHA-256 for all 78 files, then 8 files were edited (listed below). Files were added with `core.autocrlf=false` so recorded hashes are the blob hashes of the bytes copied (CRLF files stay CRLF).

| destination | content |
|---|---|
| `packs/nast/` | pack, brain, hand, `data_sources/` (from `src/data_sources/`), `tests/` (6 files), `docs/` (3 Nast plan and spec documents), `conftest.py` (new) |
| `packs/broderick/` | brain, hand, specs, `.gitignore`; new `pack.yaml` and `GOVERNANCE.md` (scaffold, rights `pending`) |
| `packs/__init__.py` | new, empty; keeps `packs.nast...` imports resolving from this repository even when the Foundry root is on `sys.path` |
| `training/lora/` | ai-toolkit/vision bootstrap, smoke and diagnostic scripts, box queue scripts, `launch_stripe_train.sh`, `RENDER_COMFYUI.md`, `tests/`, `README.md` (new) |
| `projects/stripe/_training/` | Stripe-specific LoRA scripts and configs |
| `tools/fal/fal_hair2_foundry.py` | the Foundry's differing `fal_hair2.py`; the studio `tools/fal/fal_hair2.py` is untouched |
| `.gitignore` | adds `packs/**/data/`, `packs/**/output/`, `packs/**/outputs/` (data stays out of git) |
| `CLAUDE.md` | two repo-layout lines for `packs/` and `training/lora/` |

Pack data is not in this commit. `packs/nast/pack.yaml` and `packs/broderick/pack.yaml` carry `data:` references to `s3://ilyrium-slm-foundry/datasets/<pack>/<content-hash>/` with `content_hash: pending`, and a `rights:` block with all nine uses `pending`. Three data files that are tracked in the Foundry were **not** copied (below).

## Edits applied after the byte-exact copy
1. `packs/nast/pack.yaml`: added `brain.train_config: brain/config.yaml`, `engine:` (SLM_FOUNDRY_ROOT), `data:` S3 references (hash `pending`), `rights:` (nine uses `pending`). `name`, `shapes`, `governance`, `artifacts_s3`, `brain`, `hand` unchanged.
2. `packs/nast/brain/ground_paine.py`: sys.path setup now inserts this repository's root first and appends the Foundry root from `SLM_FOUNDRY_ROOT` (default: sibling `../slm-foundry`), so the engine module resolves without the Foundry's `packs` package shadowing this one.
3. `packs/nast/data_sources/wikimedia_commons.py`: docstring invocation `python -m packs.nast.data_sources.wikimedia_commons`.
4. `packs/nast/tests/test_commons.py`, `test_loc_fetch.py`, `test_loc_images.py`: import path `src.data_sources.*` to `packs.nast.data_sources.*`.
5. `training/lora/launch_stripe_train.sh`: `HERE` is now the studio root (`../..`) and the local sources are `projects/stripe/_training/...`. The remote (box) destination `~/slm-foundry/packs/stripe/` is unchanged.
6. `training/lora/tests/test_stripe_launch_errors.py`: script path `parents[1] / "launch_stripe_train.sh"`.

## Tests (offline, `HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1`, API-key variables unset, no network, no model calls)
Dependencies available in this environment: Python 3.13.5, pytest, requests, PyYAML. Nothing was installed. The Foundry engine is supplied by `SLM_FOUNDRY_ROOT` (pointed at the Foundry relocation worktree).

| command (from the studio worktree root) | before (in Foundry) | after (here) |
|---|---|---|
| `python -m pytest packs/nast/tests -q -p no:cacheprovider -o addopts=` | 15 (ground_paine 3, build_dataset 3, caption 3, commons 4, loc_fetch 1, loc_images 1) | **15 passed** |
| `python -m pytest training/lora/tests -q -p no:cacheprovider -o addopts=` | 5 | **5 passed** |

Total moved: 20 tests, 20 passed here (Foundry full suite: 1977 passed, 12 skipped before; 1957 passed, 12 skipped after). There are no Broderick tests (none existed). The existing studio suites (`tests/`, `apps/satirist`) were not run and are not affected by these additions.

## Identical files: no copy, hashes recorded
| Foundry untracked file | studio file (byte-identical, not copied) | SHA-256 |
|---|---|---|
| `packs/build_stripe_v2.sh` | `projects/stripe/_training/build_stripe_v2.sh` | `7b32686e936dc947d2992e857ffcd6873289b2f330a15ff93e3e640cc8b8cc00` |
| `packs/compose_stripe.py` | `projects/stripe/render_test/compose_stripe.py` | `1db55b0b2eca1c3209f645020a09372685bd377fc2e487558e97b1ebb170aeaa` |
| `packs/fal_hair.py` | `tools/fal/fal_hair.py` | `1a8d555ac40f1decb367918deb61577a481cc5e988c629637ab7b200a879e228` |
| `packs/fal_mask_sweep.py` | `tools/fal/fal_mask_sweep.py` | `1b9608d704837d15aad017c69e3eefafef1fff935cdfed205da0f3d001d3f6d4` |
| `packs/render_seeds.py` | `projects/stripe/lora_seeds/v6/render_seeds_v6.py` | `dd17180d8d7590e18cb9d53e906549fdc12f9dc0850fbe57a62b10f0639aaa6b` |
| `packs/render_stripe.py` | `projects/stripe/render_test/v3/render_stripe_v3.py` | `e3cc1e6bd2f860b9e93923c3a79e0c54f9fb8bb2bd6a6fef8699ca474588296a` |
| `packs/render_stripe_lora.py` | `projects/stripe/render_test/v4_lora/render_stripe_lora.py` | `e635cccf2ebf3e88d77d43d809b8bd8eb5c3a0f1927b7c843ce04b93b51b7a4c` |
| `packs/render_stripe_lora2.py` | `projects/stripe/render_test/v5_lora/render_stripe_lora2.py` | `990086df562d2647fffbb1700fc75d5bacf4f4bf38ce28849eae549312694ea0` |
| `packs/render_stripe_v2.py` | `projects/stripe/render_test/v6_lora_v2/render_stripe_v2.py` | `82fc36b6825571c4115e2ebff269f2fa87287aa486fe336fd684351f7872ceca` |
| `packs/stripe_flux_char_v2.yaml` | `projects/stripe/_training/stripe_flux_char_v2.yaml` | `eed9958976114e3170381eb4ff8213a204fb6039561b9824e388443c241fd1a5` |

## Differing file kept under a new name
`packs/fal_hair2.py` (SHA-256 `aace6b46b2966904629cd71a5a1629574715bcb5e63645f480f1caa6a0302b40`) differs from `tools/fal/fal_hair2.py` (`b30ab9f02540...`; text-edit variant versus the Foundry's SAM-carve variant). Stored as `tools/fal/fal_hair2_foundry.py`. Nothing overwritten.

## Held back: tracked data files (not copied, not committed here)
The brief keeps pack data out of git. These three are tracked in the Foundry and stay there until the approved data transfer has run:
| path (tracked at 9cc17bf) | bytes | SHA-256 |
|---|---:|---|
| `packs/broderick/brain/data/broderick_operators.jsonl` | 71242 | `a27f5f32d1950581193ee81a4f1266b4f35426bb2029f032d4fc2417024462cc` |
| `packs/nast/brain/gold_seed.jsonl` | 28219 | `23d3ebe9ac303203a45b88c70c70f8b1cfab057f491e24217f6be2bad1b4ad22` |
| `packs/broderick/brain/data/broderick_brain_pairs.jsonl` | 198676 | `417c1fe63bd82476664a6f94f8d5b975a38e95d1ed6607e8ee84dd03d34a5d52` |

## Moved and copied files (78): source, destination, SHA-256 before and after
"before" is the SHA-256 of the source bytes (`git show 9cc17bf:<path>` or the main-checkout working tree for untracked files). "after" is the SHA-256 of the file in this branch at the commit that carries this receipt.

| source (ref) | destination | SHA-256 source | SHA-256 destination (final) | edited |
|---|---|---|---|---|
| `packs/broderick/.gitignore` (9cc17bf) | `packs/broderick/.gitignore` | `2d739f11cf93453afd5cebc949fb7bb2a048299b3da6e7b6abe883a51a0d1236` | `2d739f11cf93453afd5cebc949fb7bb2a048299b3da6e7b6abe883a51a0d1236` | no |
| `packs/broderick/brain/BRODERICK_REVIEW.md` (9cc17bf) | `packs/broderick/brain/BRODERICK_REVIEW.md` | `3c692222d60edfbc20320a3b19587ba91345008ac6fcf073d0a29ff2c4181e90` | `3c692222d60edfbc20320a3b19587ba91345008ac6fcf073d0a29ff2c4181e90` | no |
| `packs/broderick/brain/README.md` (9cc17bf) | `packs/broderick/brain/README.md` | `8b959242821f7d923b674e7123e630fb1e419600fa142bd15654c8b790bbf98e` | `8b959242821f7d923b674e7123e630fb1e419600fa142bd15654c8b790bbf98e` | no |
| `packs/broderick/brain/TRANSCRIPTION_SPEC.md` (9cc17bf) | `packs/broderick/brain/TRANSCRIPTION_SPEC.md` | `3a80080dd43a6fed6cc9c07a4cb4d28b4a6a535ab11e4488f52c87b7fc293473` | `3a80080dd43a6fed6cc9c07a4cb4d28b4a6a535ab11e4488f52c87b7fc293473` | no |
| `packs/broderick/brain/augment_pairs.py` (9cc17bf) | `packs/broderick/brain/augment_pairs.py` | `9e932346f0e6a2814ee3787d7661a3d6bd3fefb259b5e8ee5152371d771dbd2f` | `9e932346f0e6a2814ee3787d7661a3d6bd3fefb259b5e8ee5152371d771dbd2f` | no |
| `packs/broderick/brain/build_review_packet.py` (9cc17bf) | `packs/broderick/brain/build_review_packet.py` | `2ede012a5daeda7bd6f4dbf85a2cf5eb86b40726db6bdaae43ab49330878462c` | `2ede012a5daeda7bd6f4dbf85a2cf5eb86b40726db6bdaae43ab49330878462c` | no |
| `packs/broderick/brain/extract_operators.py` (9cc17bf) | `packs/broderick/brain/extract_operators.py` | `892d158064c812e6cd0ff7005596b35140086b876c2b993a9077dd077e4fdc82` | `892d158064c812e6cd0ff7005596b35140086b876c2b993a9077dd077e4fdc82` | no |
| `packs/broderick/brain/invert_to_pairs.py` (9cc17bf) | `packs/broderick/brain/invert_to_pairs.py` | `2b49ac52b5c34821fcba9bac8eade1a28a8f693f1b5c5537538f434694c8978b` | `2b49ac52b5c34821fcba9bac8eade1a28a8f693f1b5c5537538f434694c8978b` | no |
| `packs/broderick/brain/operator_schema.json` (9cc17bf) | `packs/broderick/brain/operator_schema.json` | `30d8ec35ec1328fbb17e4a882ac6b662b4b2fb059825cd053c51f4fd944b5e9a` | `30d8ec35ec1328fbb17e4a882ac6b662b4b2fb059825cd053c51f4fd944b5e9a` | no |
| `packs/broderick/brain/teacher_prompt.md` (9cc17bf) | `packs/broderick/brain/teacher_prompt.md` | `821eda2315950a3443134032b00b7d4c31b7f3ce0b71895ed5cfaed13be64ef8` | `821eda2315950a3443134032b00b7d4c31b7f3ce0b71895ed5cfaed13be64ef8` | no |
| `packs/broderick/brain/transcribe_panels.py` (9cc17bf) | `packs/broderick/brain/transcribe_panels.py` | `b4745e9f6304123a1bc514f8aea51c2fe73dbdc2d5393813db6e21e6642add40` | `b4745e9f6304123a1bc514f8aea51c2fe73dbdc2d5393813db6e21e6642add40` | no |
| `packs/broderick/hand/character_lora_SPEC.md` (9cc17bf) | `packs/broderick/hand/character_lora_SPEC.md` | `0e390cf505532166586d224f45ca9ef49a50b2256c309e2a99dc930e6d506f71` | `0e390cf505532166586d224f45ca9ef49a50b2256c309e2a99dc930e6d506f71` | no |
| `packs/broderick/hand/flux_char_lora.yaml` (9cc17bf) | `packs/broderick/hand/flux_char_lora.yaml` | `764a2d7a7f7dc9e90bbe4e83070b732cbd7865c3db048cb80994a4a853732299` | `764a2d7a7f7dc9e90bbe4e83070b732cbd7865c3db048cb80994a4a853732299` | no |
| `packs/broderick/hand/flux_dev_lora.yaml` (9cc17bf) | `packs/broderick/hand/flux_dev_lora.yaml` | `84f438b9dc449791c34ad5c7a1a82e1fa02bcff0c5687dfda9881d2319057e07` | `84f438b9dc449791c34ad5c7a1a82e1fa02bcff0c5687dfda9881d2319057e07` | no |
| `packs/broderick/hand/flux_dev_lora_v2.yaml` (9cc17bf) | `packs/broderick/hand/flux_dev_lora_v2.yaml` | `64906b756afe0755e72c9b692a340f914ff031ab0cbea9382609db969ad3b567` | `64906b756afe0755e72c9b692a340f914ff031ab0cbea9382609db969ad3b567` | no |
| `packs/broderick/hand/mine_character.py` (9cc17bf) | `packs/broderick/hand/mine_character.py` | `9e7cbed54a972974ecdaf208cd981a91ed87f8d060bada14ededfd0ee056ebfe` | `9e7cbed54a972974ecdaf208cd981a91ed87f8d060bada14ededfd0ee056ebfe` | no |
| `packs/broderick/hand/stage_grayscale.py` (9cc17bf) | `packs/broderick/hand/stage_grayscale.py` | `fb54c573299ec988c150e1e1d4720135b817bf4ad78b8a678c47781b20cd8e1a` | `fb54c573299ec988c150e1e1d4720135b817bf4ad78b8a678c47781b20cd8e1a` | no |
| `packs/broderick/hand/strip_compositor_SPEC.md` (9cc17bf) | `packs/broderick/hand/strip_compositor_SPEC.md` | `99c7412d9ecf4b62eff4ee38da9a10b0ca5d33e6d8d1aaaffc918163a618e4c1` | `99c7412d9ecf4b62eff4ee38da9a10b0ca5d33e6d8d1aaaffc918163a618e4c1` | no |
| `packs/broderick/hand/train_broderick_flux.sh` (9cc17bf) | `packs/broderick/hand/train_broderick_flux.sh` | `53231e323b6a52701a48e086665c8830962d6e8b9006ae35b1f8162391595582` | `53231e323b6a52701a48e086665c8830962d6e8b9006ae35b1f8162391595582` | no |
| `packs/nast/GOVERNANCE.md` (9cc17bf) | `packs/nast/GOVERNANCE.md` | `8a235d6494d497826b0a72082a355a4c8496d4b4424fd49e3dbb91930f499107` | `8a235d6494d497826b0a72082a355a4c8496d4b4424fd49e3dbb91930f499107` | no |
| `packs/nast/README.md` (9cc17bf) | `packs/nast/README.md` | `6a7db533691b8dd196d85f33533a8060293dc1be32df7336ab3b62d46f27b582` | `6a7db533691b8dd196d85f33533a8060293dc1be32df7336ab3b62d46f27b582` | no |
| `packs/nast/__init__.py` (9cc17bf) | `packs/nast/__init__.py` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | no |
| `packs/nast/brain/build_dataset.py` (9cc17bf) | `packs/nast/brain/build_dataset.py` | `6a6086225f93286846d717da231bd580bd66fd8c346630dce2f16c8c35994616` | `6a6086225f93286846d717da231bd580bd66fd8c346630dce2f16c8c35994616` | no |
| `packs/nast/brain/config.yaml` (9cc17bf) | `packs/nast/brain/config.yaml` | `ffc9147cb4cc36fc2005671516787b709ed0d911056a87139b50bcd98cea0f77` | `ffc9147cb4cc36fc2005671516787b709ed0d911056a87139b50bcd98cea0f77` | no |
| `packs/nast/brain/deploy_box.sh` (9cc17bf) | `packs/nast/brain/deploy_box.sh` | `75e2840f358e422fdb11ba1df2785c5f739ec96330a06ea8febb0f4fba26eeb8` | `75e2840f358e422fdb11ba1df2785c5f739ec96330a06ea8febb0f4fba26eeb8` | no |
| `packs/nast/brain/ground_paine.py` (9cc17bf) | `packs/nast/brain/ground_paine.py` | `86747fa85009a2c9fa89ccf812037b9878b7f0fb3abf51ef043fd9f97f39fbbd` | `f4ef19a83031f0ea307fec03a2880fb4c593abce11c47920208931a618ddb08d` | yes |
| `packs/nast/hand/__init__.py` (9cc17bf) | `packs/nast/hand/__init__.py` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | no |
| `packs/nast/hand/caption.py` (9cc17bf) | `packs/nast/hand/caption.py` | `085e0e3b1e1f68b33d38b2973cd560765c28a3149dfa82ee6a8b6f34b9bb8326` | `085e0e3b1e1f68b33d38b2973cd560765c28a3149dfa82ee6a8b6f34b9bb8326` | no |
| `packs/nast/hand/curate.py` (9cc17bf) | `packs/nast/hand/curate.py` | `42e30722accbd320a6e35565ab12715335de1a5b96d3697066ef0ddad51c2aeb` | `42e30722accbd320a6e35565ab12715335de1a5b96d3697066ef0ddad51c2aeb` | no |
| `packs/nast/hand/flux_lora.yaml` (9cc17bf) | `packs/nast/hand/flux_lora.yaml` | `456b378ca37838357bc72153b79eeef13463a44baa7a99962bb95055bde009ed` | `456b378ca37838357bc72153b79eeef13463a44baa7a99962bb95055bde009ed` | no |
| `packs/nast/hand/run_box.sh` (9cc17bf) | `packs/nast/hand/run_box.sh` | `0ca2c555610e4e4fbacf54e1b46a622aa73d70d0acd863b349fcfd4d53769ed7` | `0ca2c555610e4e4fbacf54e1b46a622aa73d70d0acd863b349fcfd4d53769ed7` | no |
| `packs/nast/hand/run_flux_and_finalize.sh` (9cc17bf) | `packs/nast/hand/run_flux_and_finalize.sh` | `be852f49852a349c7e20ccab4a0b4007ea7de1647ae3dbf659260dc105bf8b14` | `be852f49852a349c7e20ccab4a0b4007ea7de1647ae3dbf659260dc105bf8b14` | no |
| `packs/nast/hand/run_flux_box.sh` (9cc17bf) | `packs/nast/hand/run_flux_box.sh` | `ad435ff129e74486a06e8eee66c2d10c7c6abe473002b49c7adbc5a421b090d5` | `ad435ff129e74486a06e8eee66c2d10c7c6abe473002b49c7adbc5a421b090d5` | no |
| `packs/nast/hand/sdxl_lora.yaml` (9cc17bf) | `packs/nast/hand/sdxl_lora.yaml` | `891851b6bcd27b49332f3e5fa73520615fa8a1bcfbe3ce9ab40873a3a71247cb` | `891851b6bcd27b49332f3e5fa73520615fa8a1bcfbe3ce9ab40873a3a71247cb` | no |
| `packs/nast/hand/train_nast_flux.sh` (9cc17bf) | `packs/nast/hand/train_nast_flux.sh` | `f4029db145ebaa0dfa86b8bc364f152af3cf4089e7d512b27ef50758c0b092e7` | `f4029db145ebaa0dfa86b8bc364f152af3cf4089e7d512b27ef50758c0b092e7` | no |
| `packs/nast/pack.yaml` (9cc17bf) | `packs/nast/pack.yaml` | `6466f25cf2eb2703030b0a601ba97d89f01517f400ed5f16a6f7a73c0889732f` | `2ef87962cd98e8a0010ad55e957e191c2bc14afa929d7807fec0e6ba109eed30` | yes |
| `src/data_sources/__init__.py` (9cc17bf) | `packs/nast/data_sources/__init__.py` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | no |
| `src/data_sources/loc_fetch.py` (9cc17bf) | `packs/nast/data_sources/loc_fetch.py` | `1bce4dac9ab04d54fbb4c0dea7019a784d330c8b18140cdafc0b066c22e17db0` | `1bce4dac9ab04d54fbb4c0dea7019a784d330c8b18140cdafc0b066c22e17db0` | no |
| `src/data_sources/wikimedia_commons.py` (9cc17bf) | `packs/nast/data_sources/wikimedia_commons.py` | `260d5b3890ed24bcbabcf7ca1cb87d29622f56541da5e9364cce99b246574f91` | `76ec3731cccd4c9b66d56af58a3809b816e3f115a909e0c828cb9da618244d88` | yes |
| `tests/test_ground_paine.py` (9cc17bf) | `packs/nast/tests/test_ground_paine.py` | `2fab21b4a314db97a67e53d8f7e2954ab91e74afa4873681f654157b198b04ae` | `2fab21b4a314db97a67e53d8f7e2954ab91e74afa4873681f654157b198b04ae` | no |
| `tests/test_build_dataset.py` (9cc17bf) | `packs/nast/tests/test_build_dataset.py` | `0bc2293e73d674a7026cc0637a02ed1275f4f3759db31be6fcb1f6ff90f88b31` | `0bc2293e73d674a7026cc0637a02ed1275f4f3759db31be6fcb1f6ff90f88b31` | no |
| `tests/test_caption.py` (9cc17bf) | `packs/nast/tests/test_caption.py` | `b787b425b0a7236c68d53adb7796fb429b62a798e43f9a1964d1bd9d7797550a` | `b787b425b0a7236c68d53adb7796fb429b62a798e43f9a1964d1bd9d7797550a` | no |
| `tests/test_commons.py` (9cc17bf) | `packs/nast/tests/test_commons.py` | `8957c83bb60418efeb72f91f150000c934aab2bab1fdcef00e99856f9b62fb69` | `a3134a713fcaba9729fd95503bbf8958d55504572075ed8e9f8962bb5850965f` | yes |
| `tests/test_loc_fetch.py` (9cc17bf) | `packs/nast/tests/test_loc_fetch.py` | `9a098abb25ab2711486ed126e6d1ed53aca18c94ad5bccb0d1a552dfb25d19ec` | `8ddf083de1f38826f95e361632b010e672d1b0c5d094b001a9aceb079101ec28` | yes |
| `tests/test_loc_images.py` (9cc17bf) | `packs/nast/tests/test_loc_images.py` | `b70acae7178b31be3eefc43fd1e5bf8b9e18b663fc214a97e845e72cf9845ebc` | `67e5fe8b9c7f736e6b0270c065e8119b4207f355cb44b982eed0ec7ce20a7256` | yes |
| `docs/plans/2026-06-09-nast-pack-phase0-1.md` (9cc17bf) | `packs/nast/docs/2026-06-09-nast-pack-phase0-1.md` | `478cdaf9fe0dea85c584695d839913c493067b59b415247554ae68ae57ed8440` | `478cdaf9fe0dea85c584695d839913c493067b59b415247554ae68ae57ed8440` | no |
| `docs/plans/2026-06-10-nast-pack-phase2-hand.md` (9cc17bf) | `packs/nast/docs/2026-06-10-nast-pack-phase2-hand.md` | `94742b7533f989e683ad759c13fd091a015e1ded8cd635c1627d3ae1c7016b7a` | `94742b7533f989e683ad759c13fd091a015e1ded8cd635c1627d3ae1c7016b7a` | no |
| `docs/specs/2026-06-09-nast-reference-pack-design.md` (9cc17bf) | `packs/nast/docs/2026-06-09-nast-reference-pack-design.md` | `18dbd70c78617ac64a641888cd810c739306ec866f821f72d107dee539e7d803` | `18dbd70c78617ac64a641888cd810c739306ec866f821f72d107dee539e7d803` | no |
| `packs/stripe/bootstrap_aitk.sh` (9cc17bf) | `training/lora/bootstrap_aitk.sh` | `31c209d46b0d665e9a1d6989ef1eb28a9fa54c294a1682f90e5190d3a88e3901` | `31c209d46b0d665e9a1d6989ef1eb28a9fa54c294a1682f90e5190d3a88e3901` | no |
| `packs/stripe/RENDER_COMFYUI.md` (9cc17bf) | `training/lora/RENDER_COMFYUI.md` | `5c962b8eef5ac9923b4ef2227e4f45ac909efa3786af4c7b303da4b3bd94bf48` | `5c962b8eef5ac9923b4ef2227e4f45ac909efa3786af4c7b303da4b3bd94bf48` | no |
| `infra/bootstrap_vision.sh` (9cc17bf) | `training/lora/bootstrap_vision.sh` | `e802b38d673133115bacf508bf8e8071d6177f363662f72e2d0a3e303d40b2a8` | `e802b38d673133115bacf508bf8e8071d6177f363662f72e2d0a3e303d40b2a8` | no |
| `infra/launch_stripe_train.sh` (9cc17bf) | `training/lora/launch_stripe_train.sh` | `785f46be9ec2fbef016f2eb32e2f8a093a21cbb71d99cb8ae9bbe18b0f067343` | `c131a7f749732c74b67ed2cb137ac95323bf6f49e54844b1a45440e8c147f9d7` | yes |
| `packs/auth_check.sh` (9cc17bf) | `training/lora/auth_check.sh` | `e1a66dd99f0ebd7fd611e34442e7a0cdc104027b3b157f3ea7668e96105a6fb8` | `e1a66dd99f0ebd7fd611e34442e7a0cdc104027b3b157f3ea7668e96105a6fb8` | no |
| `packs/render_samples.py` (9cc17bf) | `training/lora/render_samples.py` | `29eea64650e5d67de7fc2efc5641af9b1fe9459267e83f19d0fd8acab897787c` | `29eea64650e5d67de7fc2efc5641af9b1fe9459267e83f19d0fd8acab897787c` | no |
| `packs/run_broderick_only.sh` (9cc17bf) | `training/lora/run_broderick_only.sh` | `c623a39aa5a2bae1611e363e5cea586e1c29b087676c13665aab2b3d83bfde4a` | `c623a39aa5a2bae1611e363e5cea586e1c29b087676c13665aab2b3d83bfde4a` | no |
| `packs/run_queue.sh` (9cc17bf) | `training/lora/run_queue.sh` | `d54cab92fe52bb3044dbf95ec1d02e255d5ae81edc3afce08eb2b1ba53282cb4` | `d54cab92fe52bb3044dbf95ec1d02e255d5ae81edc3afce08eb2b1ba53282cb4` | no |
| `packs/run_render_validation.sh` (9cc17bf) | `training/lora/run_render_validation.sh` | `40d524762bf59c39a4350117ec321cf7a4db454d71b65d8b0330a37592ddd613` | `40d524762bf59c39a4350117ec321cf7a4db454d71b65d8b0330a37592ddd613` | no |
| `packs/run_train_both.sh` (9cc17bf) | `training/lora/run_train_both.sh` | `b70bbb9f9059441e45d7f9f8af8b3beded282263e7b94198cda3c8dbc47bcae0` | `b70bbb9f9059441e45d7f9f8af8b3beded282263e7b94198cda3c8dbc47bcae0` | no |
| `tests/test_stripe_launch_errors.py` (9cc17bf) | `training/lora/tests/test_stripe_launch_errors.py` | `a6820ea36f62af89d1334905b52ee19a00166b8817ec3a27f5363da52569c53a` | `10bb762733d8658a74e562a345d49b1e554ce7f1ce1c0ef0237fb388c1b0b4ff` | yes |
| `packs/stripe/run_stripe_and_finalize.sh` (9cc17bf) | `projects/stripe/_training/run_stripe_and_finalize.sh` | `129fccb1fceb048930497abfa06ad4dec3eb273849d2822e53babd203025b94b` | `129fccb1fceb048930497abfa06ad4dec3eb273849d2822e53babd203025b94b` | no |
| `packs/stripe/stripe_flux_char_v7_nb.yaml` (9cc17bf) | `projects/stripe/_training/stripe_flux_char_v7_nb.yaml` | `af9a576ac544ffd474f6716080d30776488a1bb4a876f8e270cd9d326bd20993` | `af9a576ac544ffd474f6716080d30776488a1bb4a876f8e270cd9d326bd20993` | no |
| `packs/bootstrap_smoke.sh` (untracked) | `training/lora/bootstrap_smoke.sh` | `e28b42ab0f5726b49f16e9a7d460e114dafe5b0cb172e15fbbf7e1bfa1b750f3` | `e28b42ab0f5726b49f16e9a7d460e114dafe5b0cb172e15fbbf7e1bfa1b750f3` | no |
| `packs/smoke_flux.py` (untracked) | `training/lora/smoke_flux.py` | `1e4c2a5e5e068cede01540b89f20cbf52efb912774733eebb2c180b3d8a9f8dc` | `1e4c2a5e5e068cede01540b89f20cbf52efb912774733eebb2c180b3d8a9f8dc` | no |
| `packs/diag_loras.py` (untracked) | `training/lora/diag_loras.py` | `a8d152c29b6a89f887c380e7a29e6af5b704dd68255da6d444e5577cb8239a23` | `a8d152c29b6a89f887c380e7a29e6af5b704dd68255da6d444e5577cb8239a23` | no |
| `packs/diag_features.py` (untracked) | `training/lora/diag_features.py` | `9aec9156e71773b3207f708746e20e75e4d1c8c42b4c9aa85feff25f47828768` | `9aec9156e71773b3207f708746e20e75e4d1c8c42b4c9aa85feff25f47828768` | no |
| `packs/render_loras.py` (untracked) | `training/lora/render_loras.py` | `ad434f18b6bc239701cd4eb2e533db5db7fddbbd266c4a0c12aa16057a60ee44` | `ad434f18b6bc239701cd4eb2e533db5db7fddbbd266c4a0c12aa16057a60ee44` | no |
| `packs/build_stripe_lora.sh` (untracked) | `projects/stripe/_training/build_stripe_lora.sh` | `417e9521084cc3205c47f6c192f4a7d11b99b9ba0f8537ef925577cfb249d96e` | `417e9521084cc3205c47f6c192f4a7d11b99b9ba0f8537ef925577cfb249d96e` | no |
| `packs/train_stripe.sh` (untracked) | `projects/stripe/_training/train_stripe.sh` | `5d2fe98f5d85b0f5b2cb73488370bb15f6ca47dacb42b1dce5667cc1fa8f5f6f` | `5d2fe98f5d85b0f5b2cb73488370bb15f6ca47dacb42b1dce5667cc1fa8f5f6f` | no |
| `packs/stripe_flux_char.yaml` (untracked) | `projects/stripe/_training/stripe_flux_char.yaml` | `7b0125bc007eb183ed092e27f4f0e03106cd754704f0bbc4b76406c61f0cda14` | `7b0125bc007eb183ed092e27f4f0e03106cd754704f0bbc4b76406c61f0cda14` | no |
| `packs/render_trainset.py` (untracked) | `projects/stripe/_training/render_trainset.py` | `fd9c8c91b03bdc37cbe8b6d6a8346b83c5b965443c642961bda34f5137f92318` | `fd9c8c91b03bdc37cbe8b6d6a8346b83c5b965443c642961bda34f5137f92318` | no |
| `packs/ip_proof.py` (untracked) | `projects/stripe/_training/ip_proof.py` | `0484bb656276b00e9ab34897132290e5c68a094c6c52eccda541c1b38f2442c1` | `0484bb656276b00e9ab34897132290e5c68a094c6c52eccda541c1b38f2442c1` | no |
| `packs/ip_recipe.py` (untracked) | `projects/stripe/_training/ip_recipe.py` | `763b2636323cf621a8345b66cb9fbd5d1e79df91e650f187f7e8446977ed432f` | `763b2636323cf621a8345b66cb9fbd5d1e79df91e650f187f7e8446977ed432f` | no |
| `packs/ip_trainset.py` (untracked) | `projects/stripe/_training/ip_trainset.py` | `b849d5cb504d673a5c57c6e24989af11f1302b7488557eddca2c5027b9217e56` | `b849d5cb504d673a5c57c6e24989af11f1302b7488557eddca2c5027b9217e56` | no |
| `packs/inpaint_hair.py` (untracked) | `projects/stripe/_training/inpaint_hair.py` | `e8dac6a9271781ca8a0bb00d8b7b0a8aaf2b532baad387da589aafb55c6d4d93` | `e8dac6a9271781ca8a0bb00d8b7b0a8aaf2b532baad387da589aafb55c6d4d93` | no |
| `packs/inpaint_speedo.py` (untracked) | `projects/stripe/_training/inpaint_speedo.py` | `2dd69ac502688dfde16e486bb86efcd0000af4158fd45ebbf129477ad9e029f0` | `2dd69ac502688dfde16e486bb86efcd0000af4158fd45ebbf129477ad9e029f0` | no |
| `packs/inpaint_speedo2.py` (untracked) | `projects/stripe/_training/inpaint_speedo2.py` | `c137033de45efb03ae6c9d41ba81aa4f847da29a97d57146f88f0c0aa5464053` | `c137033de45efb03ae6c9d41ba81aa4f847da29a97d57146f88f0c0aa5464053` | no |
| `packs/render_panel4.py` (untracked) | `projects/stripe/_training/render_panel4.py` | `3fb9dfdec0afd2bdb41a4a1a69f06673112c7313afe71a709185674748e65988` | `3fb9dfdec0afd2bdb41a4a1a69f06673112c7313afe71a709185674748e65988` | no |
| `packs/fal_hair2.py` (untracked) | `tools/fal/fal_hair2_foundry.py` | `aace6b46b2966904629cd71a5a1629574715bcb5e63645f480f1caa6a0302b40` | `aace6b46b2966904629cd71a5a1629574715bcb5e63645f480f1caa6a0302b40` | no |

## Deviations from the mapping
1. Identical-copy count: 10 of the 27 untracked files are byte-identical to studio files, as the survey said, but three are identical under a different name (`render_seeds.py` is `lora_seeds/v6/render_seeds_v6.py`; `render_stripe.py` is `render_test/v3/render_stripe_v3.py`; `render_stripe_v2.py` is `render_test/v6_lora_v2/render_stripe_v2.py`). Matching was by content hash across the whole studio tree.
2. `infra/launch_stripe_train.sh` was moved whole to `training/lora/` (not split into generic and Stripe-specific parts); only its local source paths were rewritten. Splitting a bounded-retry launcher is a behaviour change and was left for a deliberate step.
3. Box-side paths (`~/slm-foundry/packs/...`, `~/slm-foundry/.env`) in the box scripts and YAMLs were **not** rewritten (the default said to rewrite). They run on the EC2 box, whose layout is not in any repository, and a rewrite cannot be tested offline. Recorded as an open decision.
4. The six loose Foundry scripts with no mapping row (`auth_check.sh`, `render_samples.py`, `run_queue.sh`, `run_render_validation.sh`, `run_train_both.sh`, `run_broderick_only.sh`) went to `training/lora/` (smallest option, per the Phase A proposal).
5. The three Nast plan and spec documents moved to `packs/nast/docs/` (Q9 default).
6. Untracked Foundry files kept CRLF (they were committed byte-for-byte). Shell scripts among them need `dos2unix` before use on Linux.
7. Three tracked data files are held back (above), against the Phase A mapping that moved tracked data with the pack, because this brief says no data file is committed to any repository.
8. Broderick has no tests to move. Stripe has no `pack.yaml` (image-LoRA work only) and was not scaffolded as a pack.

## Open decisions
1. Box-side path layout for the relocated scripts (item 3 above): Brad.
2. Whether to include the three held-back data files in the S3 transfer packet, and when the Foundry copies may be removed: Brad.
3. Rights records for every artifact (all nine uses `pending`), Broderick and per-artifact Nast: Brad. Storage rights gate the transfer request.
4. Technical reviewer to name in `packs/broderick/GOVERNANCE.md`; real Broderick `train_config`, schema and eval gate (scaffold only): Brad.
5. CRLF normalisation of the shell scripts (item 6): Brad / a later lane.
6. `origin/main` is as of the last local fetch (`adaf7eb`, 2026-10-29); rebase before merging if `main` moved.

## Authority statement
No model calls, training, downloads, installs, AWS, S3, R2 or Neon access, deployment, merge, push, stash, reset, clean, branch deletion or worktree removal occurred. The studio main checkout and the Foundry main checkout were not modified. Commit made with named paths only; not pushed.
