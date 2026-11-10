import Link from "next/link";
import { notFound } from "next/navigation";
import { consoleHref, pageBySlug } from "../pages";

// Validates the slug and renders placeholders. Run and the legacy pages are rendered by
// Workspace in the layout (so their state survives navigation), so they return null here.
// Page files may only export Next's own names, so the page table lives in ../pages.ts.
export default async function ConsolePageRoute({ params }: { params: Promise<{ page: string }> }) {
  const { page: slug } = await params;
  const page = pageBySlug(slug);
  if (!page) notFound();
  if (page.kind !== "placeholder") return null;
  return (
    <section data-page={page.slug} className="bg-panel border border-edge rounded-xl p-8 max-w-xl">
      <h1 className="text-[20px] font-semibold mb-2">{page.label}</h1>
      <p className="text-dim text-[15px] mb-1">{page.blurb}</p>
      <p className="text-dim text-[13px] font-mono mb-5">Built in Phase {page.phase}</p>
      <Link href={consoleHref("run")} className="text-accent text-[14px] underline">Back to Run</Link>
    </section>
  );
}
