import { loadConsoleData } from "./data";
import Workspace from "./Workspace";
import { KeysProvider } from "./keys/KeysProvider";

// Always renders fresh. Must stay here (not only on a page): the layout now owns the data
// load, and without it `next build` could run the queries at build time.
export const dynamic = "force-dynamic";

// The shell. It sits above the [page] segment, so Workspace (and the Run it keeps alive)
// is not remounted when the page changes. It does not receive the [page] param; the page
// validates its own slug.
export default async function ConsoleLayout({ children }: { children: React.ReactNode }) {
  const data = await loadConsoleData();
  return (
    <KeysProvider>
      <Workspace {...data}>{children}</Workspace>
    </KeysProvider>
  );
}
