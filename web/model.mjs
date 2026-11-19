export function selectedRecords(records, query, province, status) {
  const words = query.trim().toLowerCase().split(/\s+/).filter(Boolean);
  return records.filter(
    (r) =>
      (province === "all" || province === r.province) &&
      (status === "all" || r.claims.some((c) => c.status === status)) &&
      words.every((w) =>
        [r.name, r.date, r.province, ...r.description]
          .join(" ")
          .toLowerCase()
          .includes(w),
      ),
  );
}
export function joined(lines) {
  const text = (lines || []).join(" ");
  return !text || text === "-" ? "No entry published" : text;
}
