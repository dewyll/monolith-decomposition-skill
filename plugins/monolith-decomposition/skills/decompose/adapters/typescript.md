# TypeScript / JavaScript adapter

## Components

A component is a **folder** (often a feature or module folder). In NestJS,
Angular or similar frameworks, a framework module (`billing.module.ts` and
its folder) is the natural component. In monorepos (Nx, Turborepo, pnpm
workspaces), each library/package can be a component via the `explicit`
strategy.

```json
"source_roots": ["src"],
"import_aliases": {"@/": "src/", "@app/": "src/app/"}
```

Copy path aliases from `tsconfig.json` `compilerOptions.paths` into
`import_aliases`, or imports through them will look external.

## Size

`scc` or the built-in counter. Exclude `dist/`, `*.d.ts` if generated,
bundles and `*.min.js`.

## Dependencies

**dependency-cruiser** resolves aliases, re-exports and `require`:

```bash
npx depcruise src --ts-config tsconfig.json -T json \
  | jq -r '.modules[] | .source as $s | .dependencies[] | select(.coreModule | not) | [$s, .resolved] | @tsv' \
  | python3 "$SKILL_DIR/scripts/convert_edges.py" --workspace decomposition \
      --kind files --tool dependency-cruiser -
```

`madge --json src` is a lighter alternative (an object of file to imported
files). Neither sees DI tokens resolved at runtime (NestJS providers by
token, InversifyJS) or event emitters.

## Fitness functions

| Library | Notes |
|---|---|
| **dependency-cruiser** | Forbidden/allowed rules, cycles, orphans; CLI for CI. |
| **eslint-plugin-boundaries** | Element types and allowed dependencies, inside the linter. |
| **Nx `@nx/enforce-module-boundaries`** | Tag-based rules for Nx workspaces. |
| **ArchUnitTS** (npm `archunit`) | ArchUnit-style tests in Jest/Vitest, plus metrics. |

dependency-cruiser, Phase 4 and 5 (`.dependency-cruiser.js`):

```js
module.exports = {
  forbidden: [
    { name: 'no-circular', severity: 'error', comment: 'RFC-0008',
      from: {}, to: { circular: true } },
    { name: 'ordering-not-to-reporting', severity: 'error', comment: 'RFC-0011',
      from: { path: '^src/ordering' }, to: { path: '^src/reporting' } },
    { name: 'notification-lives-in-shared', severity: 'error', comment: 'RFC-0005',
      from: { pathNot: '^src/shared/notification' },
      to: { path: '(^|/)notification/', pathNot: '^src/shared/notification' } },
  ],
  options: { tsConfig: { fileName: 'tsconfig.json' } },
};
```

Run `npx depcruise src --config .dependency-cruiser.js` in CI. Its
`--ignore-known` option with a generated baseline lets existing violations
be burned down gradually.

## Pitfalls

- Barrel files (`index.ts` re-exporting everything) make every importer
  depend on the whole folder; dependency-cruiser follows them, the regex
  extractor sees only the barrel.
- Dynamic `import()` and lazy routes are runtime edges; the built-in
  extractor marks them `dynamic`.
- Front-end and back-end in one repo are usually separate source roots and
  separate domain maps.
