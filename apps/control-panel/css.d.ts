// Ambient declaration for CSS side-effect imports (e.g. `import "./globals.css"`).
// Next's bundler handles these at build time, but the `next build` type-check pass
// cannot resolve them under tsconfig `moduleResolution: "node"`, failing with
// "Cannot find module or type declarations for side-effect import". This is a
// pre-existing build quirk, independent of the ilyrium schema reconciliation.
declare module "*.css";
