// Covers the [page] segment only. It cannot show while the layout loads the console data
// (a hard load or router.refresh() blocks until the layout resolves).
export default function Loading() {
  return <p className="text-dim text-[14px] p-2">Loading...</p>;
}
