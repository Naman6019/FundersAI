/**
 * Composes the label shown for a scheme read out of `mutual_fund_core_snapshot`.
 *
 * AMFI's NAVAll feed used to bake the plan and option into the scheme name
 * ("HDFC Flexi Cap Fund - Direct Plan - Growth Option"). It now publishes them as
 * separate columns, so `scheme_name` is bare and several rows of the same fund share it:
 * Direct/Regular × Growth/IDCW all read "HDFC Flexi Cap Fund". `plan_type` and
 * `option_type` are what tell them apart, so any user-facing list must show them.
 *
 * Rows written before the format change still carry the plan/option inside the name; the
 * suffix is not appended twice in that case.
 */

export interface SchemeIdentityFields {
  scheme_name?: string | null;
  plan_type?: string | null;
  option_type?: string | null;
}

/** True when the name already spells out this qualifier, as legacy rows do. */
function nameAlreadyStates(name: string, qualifier: string): boolean {
  const haystack = name.toLowerCase();
  // "Direct Plan" is already stated by a name containing "direct"; same for the option.
  return qualifier
    .toLowerCase()
    .split(/\s+/)
    .filter((word) => word.length > 2)
    .every((word) => haystack.includes(word));
}

export function schemeDisplayName(row: SchemeIdentityFields): string {
  const name = String(row.scheme_name ?? "").trim();
  if (!name) return "Unnamed scheme";

  const qualifiers = [row.plan_type, row.option_type]
    .map((value) => String(value ?? "").trim())
    .filter((value) => value.length > 0)
    .filter((value) => !nameAlreadyStates(name, value));

  return qualifiers.length > 0 ? `${name} · ${qualifiers.join(" · ")}` : name;
}
