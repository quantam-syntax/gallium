# GDM progress

## Done

- Created an isolated React/Vite frontend starter in `gdm/`.
- Added the initial Brightloop welcome screen and responsive base styles.

## Next

- Build contract-shaped mock data and the admin/staff and customer navigation.
- Implement the seeded demo path, prioritizing the Billing Control Tower.
- Replace mock calls with API calls as endpoints are handed off.

## Blocked

- No blockers for the starter. Backend endpoints are still being handed off;
  keep the initial UI aligned to `../CONTRACT.md` and report any mismatches to GSK.

## API response mismatches

- None observed; the starter does not call the API yet.

## Verification

- `npm run build`: passed with Vite 6.4.5; production bundle generated successfully.

## Commands for GSK

- Start: `cd gdm && npm run dev`
- Build: `cd gdm && npm run build`
