export const byId = (id) => document.getElementById(id);
export function element(tag, text) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  return node;
}
export function choices(id, pairs) {
  byId(id).replaceChildren(
    ...pairs.map(([value, label]) => new Option(label, value)),
  );
}
export function sourceLink(label, url) {
  const anchor = element("a", label);
  anchor.href = url;
  return anchor;
}
export function downloadCsv(filename, rows) {
  const csv =
    rows
      .map((row) =>
        row
          .map((v) => '"' + String(v ?? "").replaceAll('"', '""') + '"')
          .join(","),
      )
      .join("\r\n") + "\r\n";
  const url = URL.createObjectURL(
    new Blob([csv], { type: "text/csv;charset=utf-8" }),
  );
  const a = element("a");
  a.download = filename;
  a.href = url;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
export const number = (value) =>
  value == null
    ? "Unreported"
    : value.toLocaleString("en-CA", { maximumFractionDigits: 2 });
export async function loadEdition(unit) {
  const response = await fetch("./data/edition.json");
  if (!response.ok) throw Error("No edition");
  const data = await response.json();
  byId("edition").textContent =
    number(data.count) +
    " " +
    unit +
    " · " +
    data.coverage +
    " · Sources retrieved " +
    data.retrieved +
    " UTC";
  return data;
}
export function failed() {
  byId("edition").textContent =
    "The records could not load. Reload this page or open the source guide.";
}
