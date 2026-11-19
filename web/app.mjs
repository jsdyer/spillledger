import {
  byId,
  choices,
  element,
  number,
  sourceLink,
  downloadCsv,
  loadEdition,
  failed,
} from "./ui.mjs";
import { selectedRecords, joined } from "./model.mjs";
try {
  const data = await loadEdition("incidents"),
    records = data.records;
  choices("province", [
    ["all", "Both provinces"],
    ["Nova Scotia", "Nova Scotia"],
    ["British Columbia", "British Columbia"],
  ]);
  const states = [
    ...new Set(records.flatMap((r) => r.claims.map((c) => c.status))),
  ].sort();
  choices("state", [
    ["all", "All report statuses"],
    ...states.map((s) => [s, s]),
  ]);
  const lookup = new Map(records.map((r, i) => [r, String(i)]));
  const label = (r) => r.name + " · " + r.place + " · " + r.date;
  let csv = [];
  function render() {
    const selected = byId("incident").value,
      r = selected === "" ? null : records[Number(selected)];
    byId("detail").hidden = !r;
    if (!r) return;
    byId("name").textContent = r.name + " · " + r.place;
    byId("description").textContent = [
      r.date,
      r.province,
      ...r.description.slice(1),
    ].join(" · ");
    const cards = r.claims.map((claim, i) => {
      const block = element("div");
      block.className = "claim";
      block.append(
        element(
          "h3",
          r.claims.length > 1 ? "Claim " + (i + 1) : "Claim record",
        ),
      );
      const list = element("dl");
      for (const [field, value] of [
        ["Submitted", joined(claim.submission)],
        ["Offer or decision", joined(claim.decision)],
        ["File status", claim.status],
      ]) {
        list.append(element("dt", field), element("dd", value));
      }
      block.append(list);
      return block;
    });
    byId("claims").replaceChildren(...cards);
    byId("recovery").textContent = joined(r.recovery);
    byId("original").replaceChildren(
      sourceLink(
        "Open annual report, p. " + r.page,
        data.source + "#page=" + r.page,
      ),
    );
    csv = [
      [
        "incident",
        "incident_date",
        "province",
        "place",
        "claim_as_printed",
        "decision_as_printed",
        "recovery_as_printed",
        "file_status",
        "source",
      ],
    ];
    r.claims.forEach((c, i) =>
      csv.push([
        r.name,
        r.date,
        r.province,
        r.place,
        c.submission.join(" "),
        c.decision.join(" "),
        i === 0 ? r.recovery.join(" ") : "",
        c.status,
        data.source + "#page=" + c.page,
      ]),
    );
  }
  function filter(preferred = byId("incident").value) {
    const found = selectedRecords(
      records,
      byId("search").value,
      byId("province").value,
      byId("state").value,
    );
    choices(
      "incident",
      found.map((r) => [lookup.get(r), label(r)]),
    );
    if (found.some((r) => lookup.get(r) === preferred))
      byId("incident").value = preferred;
    byId("matchcount").textContent = found.length
      ? number(found.length) + " of " + records.length + " incidents"
      : "No matching incidents. Try another harbour, name or status.";
    render();
  }
  byId("incident").onchange = render;
  byId("search").oninput = () => filter();
  for (const id of ["province", "state"]) byId(id).onchange = () => filter();
  byId("csv").onclick = () => downloadCsv("marine-incident.csv", csv);
  filter(
    lookup.get(
      records.find((r) => r.name === "Cormorant" && r.date.startsWith("2015")),
    ),
  );
} catch {
  failed();
}
