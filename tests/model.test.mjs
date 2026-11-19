import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
const edition = JSON.parse(
  readFileSync(new URL("../web/data/edition.json", import.meta.url), "utf8"),
);
import { selectedRecords, joined } from "../web/model.mjs";
test("a search across vessel and harbour returns both claims on the one incident", () => {
  const [shelburne] = selectedRecords(
    edition.records,
    "fArLeY Shelburne",
    "Nova Scotia",
    "Open",
  );
  assert.equal(shelburne.date, "2015-06-24");
  assert.equal(shelburne.claims.length, 2);
  assert.ok(
    shelburne.claims.some((c) =>
      joined(c.submission).includes("Town of Shelburne"),
    ),
  );
  assert.deepEqual(
    selectedRecords([shelburne], "", "British Columbia", "all"),
    [],
  );
});
test("no-spill and unpublished stages survive extraction as such", () => {
  const [r] = selectedRecords(
    edition.records,
    "Cormorant 2019",
    "Nova Scotia",
    "all",
  );
  assert.ok(r.description.includes("No spill"));
  assert.equal(joined(r.recovery), "No entry published");
  assert.equal(joined([]), "No entry published");
});
