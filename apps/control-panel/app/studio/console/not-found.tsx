import Link from "next/link";
import { consoleHref } from "./pages";

// Rendered inside the console shell when [page]/page.tsx calls notFound().
export default function ConsoleNotFound() {
  return (
    <section data-page="not-found" className="bg-panel border border-edge rounded-xl p-8 max-w-xl">
      <h1 className="text-[20px] font-semibold mb-2">Page not found</h1>
      <p className="text-dim text-[15px] mb-5">There is no console page at this address.</p>
      <Link href={consoleHref("run")} className="text-accent text-[14px] underline">Back to Run</Link>
    </section>
  );
}
