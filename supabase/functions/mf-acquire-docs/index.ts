import { AwsClient } from "npm:aws4fetch@1.0.20";

type DocumentInput = {
  document_type?: string;
  source_url?: string;
  url?: string;
  discovery_page_url?: string;
  expected_file_type?: string;
  file_ext?: string;
  report_month?: string;
  title?: string;
  reuse_as_portfolio?: boolean;
};

type AmcSource = {
  code: string;
  name: string;
  baseUrl: string;
  factsheetPageUrl: string;
  portfolioPageUrl: string;
  allowedHostSuffixes: string[];
};

type DiscoveryCandidate = DocumentInput & {
  score: number;
};

const AMCS: Record<string, AmcSource> = {
  axis: {
    code: "AXIS",
    name: "Axis Mutual Fund",
    baseUrl: "https://www.axismf.com",
    factsheetPageUrl: "https://www.axismf.com/downloads",
    portfolioPageUrl: "https://www.axismf.com/downloads",
    allowedHostSuffixes: ["axismf.com"],
  },
  hdfc: {
    code: "HDFC",
    name: "HDFC Mutual Fund",
    baseUrl: "https://www.hdfcfund.com",
    factsheetPageUrl: "https://www.hdfcfund.com/mutual-funds/factsheets",
    portfolioPageUrl: "https://www.hdfcfund.com/statutory-disclosure/portfolio/monthly-portfolio",
    allowedHostSuffixes: ["hdfcfund.com"],
  },
};

const BLOCKED_HOSTS = [
  "groww.in",
  "valueresearchonline.com",
  "moneycontrol.com",
  "morningstar.in",
  "advisorKhoj.com",
].map((host) => host.toLowerCase());

const EXT_TO_CONTENT_TYPE: Record<string, string> = {
  ".pdf": "application/pdf",
  ".xls": "application/vnd.ms-excel",
  ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  ".xlsm": "application/vnd.ms-excel.sheet.macroEnabled.12",
};

Deno.serve(async (request) => {
  if (request.method === "OPTIONS") {
    return jsonResponse({ status: "ok" });
  }
  if (request.method === "GET") {
    return jsonResponse({ status: "ok", function: "mf-acquire-docs" });
  }
  if (request.method !== "POST") {
    return jsonResponse({ status: "error", reason: "method_not_allowed" }, 405);
  }

  const auth = validateAuth(request);
  if (!auth.ok) {
    return jsonResponse({ status: "error", reason: auth.reason }, auth.status);
  }

  let body: Record<string, unknown> = {};
  try {
    body = await request.json();
  } catch {
    body = {};
  }

  const amcKey = normalizeAmc(String(body.amc || "axis"));
  const source = AMCS[amcKey];
  if (!source) {
    return jsonResponse({ status: "error", reason: "unsupported_amc", amc: amcKey }, 400);
  }

  const docs = normalizeDocuments(source, body);
  if (!docs.length) {
    const discoveredDocs = await discoverOfficialDocuments(source, body);
    docs.push(...discoveredDocs);
  }
  if (!docs.length) {
    return jsonResponse({ status: "error", reason: "no_document_urls", amc: source.code }, 400);
  }

  const dryRun = truthy(body.dry_run);
  const acquired: Record<string, unknown>[] = [];
  const failed: Record<string, unknown>[] = [];

  if (!dryRun) {
    await upsertAmcSource(source);
  }

  for (const doc of docs) {
    try {
      const result = await acquireOne(source, doc, dryRun);
      if (String(result.status) === "ingested" || String(result.status) === "skipped") {
        acquired.push(result);
      } else {
        failed.push(result);
      }
    } catch (error) {
      failed.push({
        status: "error",
        reason: error instanceof Error ? error.message : String(error),
        source_url: String(doc.source_url || doc.url || ""),
        document_type: normalizeDocumentType(doc.document_type),
      });
    }
  }

  const status = acquired.length && !failed.length ? "ok" : acquired.length ? "partial" : "error";
  const responseStatus = status === "error" ? 502 : 200;
  return jsonResponse({ status, amc: source.code, dry_run: dryRun, acquired_documents: acquired, failed_documents: failed }, responseStatus);
});

function validateAuth(request: Request): { ok: true } | { ok: false; status: number; reason: string } {
  const expected = Deno.env.get("MF_EDGE_ACQUIRE_KEY")?.trim();
  if (!expected) {
    return { ok: false, status: 500, reason: "mf_edge_acquire_key_not_configured" };
  }
  const auth = request.headers.get("authorization") || "";
  const bearer = auth.toLowerCase().startsWith("bearer ") ? auth.slice(7).trim() : "";
  const headerKey = request.headers.get("x-edge-acquire-key")?.trim() || "";
  if (bearer !== expected && headerKey !== expected) {
    return { ok: false, status: 401, reason: "unauthorized" };
  }
  return { ok: true };
}

async function acquireOne(source: AmcSource, doc: DocumentInput, dryRun: boolean): Promise<Record<string, unknown>> {
  const documentType = normalizeDocumentType(doc.document_type);
  const sourceUrl = String(doc.source_url || doc.url || "").trim();
  if (!["factsheet", "portfolio_disclosure"].includes(documentType)) {
    return { status: "error", reason: "unsupported_document_type", document_type: documentType, source_url: sourceUrl };
  }
  const officialUrlIssue = validateOfficialUrl(source, sourceUrl);
  if (officialUrlIssue) {
    return { status: "error", reason: officialUrlIssue, document_type: documentType, source_url: sourceUrl };
  }

  const downloaded = await downloadOfficialDocument(source, doc, documentType, sourceUrl);
  if ("reason" in downloaded) {
    return { status: "error", ...downloaded, document_type: documentType, source_url: sourceUrl };
  }

  const targetTypes = documentType === "factsheet" && truthy(doc.reuse_as_portfolio)
    ? ["factsheet", "portfolio_disclosure"]
    : [documentType];
  const rows: Record<string, unknown>[] = [];

  for (const targetType of targetTypes) {
    const row = await storeOne(source, downloaded, targetType, dryRun);
    if (targetType !== documentType) {
      row.reused_from_document_type = documentType;
    }
    rows.push(row);
  }

  if (rows.length === 1) {
    return rows[0];
  }
  const failed = rows.filter((row) => String(row.status) === "error");
  return {
    status: failed.length ? "error" : "ingested",
    source_url: sourceUrl,
    document_type: documentType,
    acquired_documents: rows,
  };
}

async function storeOne(
  source: AmcSource,
  downloaded: {
    bytes: Uint8Array;
    checksum: string;
    sourceUrl: string;
    discoveryPageUrl: string;
    fileName: string;
    fileExt: string;
    contentType: string;
    reportMonth: string | null;
  },
  documentType: string,
  dryRun: boolean,
): Promise<Record<string, unknown>> {
  const duplicateId = dryRun ? null : await findDuplicate(downloaded.checksum, source.code, documentType, downloaded.reportMonth);
  if (duplicateId) {
    return {
      status: "skipped",
      reason: "duplicate_checksum",
      source_document_id: duplicateId,
      checksum: downloaded.checksum,
      source_url: downloaded.sourceUrl,
      document_type: documentType,
      report_month: downloaded.reportMonth,
    };
  }

  const storageKey = buildStorageKey(source.code, downloaded.reportMonth, documentType, downloaded.fileName, downloaded.checksum);
  const rawBucket = requiredEnv("R2_RAW_BUCKET");
  const storagePath = `r2://${rawBucket}/${storageKey}`;

  if (dryRun) {
    return {
      status: "ingested",
      dry_run: true,
      checksum: downloaded.checksum,
      source_url: downloaded.sourceUrl,
      document_type: documentType,
      report_month: downloaded.reportMonth,
      storage_backend: "r2",
      storage_bucket: rawBucket,
      storage_key: storageKey,
    };
  }

  await uploadToR2(rawBucket, storageKey, downloaded.bytes, downloaded.contentType);
  const row = await insertRawDocument({
    amc_name: source.name,
    amc_code: source.code,
    document_type: documentType,
    source_document_type: documentType,
    report_month: downloaded.reportMonth,
    source_url: downloaded.sourceUrl,
    discovery_page_url: downloaded.discoveryPageUrl,
    file_name: downloaded.fileName,
    file_ext: downloaded.fileExt,
    storage_path: storagePath,
    storage_backend: "r2",
    storage_bucket: rawBucket,
    storage_key: storageKey,
    storage_metadata: {
      acquired_by: "supabase_edge_function",
      source_manifest: {
        amc: source.code,
        document_type: documentType,
        report_month: downloaded.reportMonth,
        source_url: downloaded.sourceUrl,
        discovery_page_url: downloaded.discoveryPageUrl,
        expected_file_type: downloaded.fileExt,
        checksum: downloaded.checksum,
        acquisition_status: "acquired",
      },
    },
    checksum: downloaded.checksum,
    content_type: downloaded.contentType,
    file_size_bytes: downloaded.bytes.byteLength,
    parse_status: "pending",
    downloaded_at: new Date().toISOString(),
    parser_version: "mf_edge_acquire_v1",
  });

  return {
    status: "ingested",
    source_document_id: row.id,
    checksum: downloaded.checksum,
    source_url: downloaded.sourceUrl,
    discovery_page_url: downloaded.discoveryPageUrl,
    document_type: documentType,
    report_month: downloaded.reportMonth,
    storage_backend: "r2",
    storage_bucket: rawBucket,
    storage_key: storageKey,
  };
}

async function downloadOfficialDocument(
  source: AmcSource,
  doc: DocumentInput,
  documentType: string,
  sourceUrl: string,
): Promise<
  | {
    bytes: Uint8Array;
    checksum: string;
    sourceUrl: string;
    discoveryPageUrl: string;
    fileName: string;
    fileExt: string;
    contentType: string;
    reportMonth: string | null;
  }
  | { reason: string; http_status?: number }
> {
  const response = await fetch(sourceUrl, {
    headers: {
      "User-Agent": Deno.env.get("MF_USER_AGENT") || "Mozilla/5.0 FundersAI/1.0",
      "Accept": "application/pdf,application/vnd.ms-excel,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,*/*",
      "Referer": source.baseUrl,
    },
  });
  if (!response.ok) {
    return { reason: "download_http_error", http_status: response.status };
  }

  const bytes = new Uint8Array(await response.arrayBuffer());
  if (!bytes.byteLength) {
    return { reason: "empty_body" };
  }
  if (looksLikeHtml(bytes)) {
    return { reason: "html_body" };
  }

  const contentType = normalizeContentType(response.headers.get("content-type"));
  const fileExt = normalizeExtension(doc.expected_file_type || doc.file_ext || sourceUrl, contentType);
  if (!EXT_TO_CONTENT_TYPE[fileExt]) {
    return { reason: "unsupported_file_type" };
  }
  const mismatch = validateBodyShape(bytes, fileExt);
  if (mismatch) {
    return { reason: mismatch };
  }

  return {
    bytes,
    checksum: await sha256Hex(bytes),
    sourceUrl,
    discoveryPageUrl: String(doc.discovery_page_url || sourceUrl),
    fileName: fileNameFromUrl(sourceUrl, fileExt),
    fileExt,
    contentType: contentType || EXT_TO_CONTENT_TYPE[fileExt],
    reportMonth: normalizeReportMonth(doc.report_month) || detectReportMonth(`${sourceUrl} ${doc.title || ""}`),
  };
}

async function uploadToR2(bucket: string, key: string, bytes: Uint8Array, contentType: string): Promise<void> {
  const endpoint = requiredEnv("R2_ENDPOINT").replace(/\/+$/, "");
  const aws = new AwsClient({
    accessKeyId: requiredEnv("R2_ACCESS_KEY_ID"),
    secretAccessKey: requiredEnv("R2_SECRET_ACCESS_KEY"),
    service: "s3",
    region: "auto",
  });
  const url = `${endpoint}/${encodeURIComponent(bucket)}/${key.split("/").map(encodeURIComponent).join("/")}`;
  const response = await aws.fetch(url, {
    method: "PUT",
    body: bytes,
    headers: { "Content-Type": contentType },
  });
  if (!response.ok) {
    throw new Error(`r2_upload_failed:${response.status}`);
  }
}

async function upsertAmcSource(source: AmcSource): Promise<void> {
  const response = await supabaseFetch("mf_amc_sources?on_conflict=amc_code", {
    method: "POST",
    headers: { "Prefer": "resolution=merge-duplicates" },
    body: JSON.stringify({
      amc_code: source.code,
      amc_name: source.name,
      listing_url: source.factsheetPageUrl,
      base_url: source.baseUrl,
      adapter_key: source.code.toLowerCase(),
      factsheet_page_url: source.factsheetPageUrl,
      portfolio_disclosure_page_url: source.portfolioPageUrl,
      is_enabled: true,
      updated_at: new Date().toISOString(),
    }),
  });
  if (!response.ok) {
    throw new Error(`source_upsert_failed:${response.status}:${await response.text()}`);
  }
}

async function findDuplicate(checksum: string, amcCode: string, documentType: string, reportMonth: string | null): Promise<string | null> {
  const params = new URLSearchParams();
  params.set("select", "id");
  params.set("checksum", `eq.${checksum}`);
  params.set("amc_code", `eq.${amcCode}`);
  params.set("document_type", `eq.${documentType}`);
  params.set("limit", "1");
  if (reportMonth) {
    params.set("report_month", `eq.${reportMonth}`);
  }
  const response = await supabaseFetch(`mf_raw_documents?${params.toString()}`, { method: "GET" });
  if (!response.ok) {
    throw new Error(`duplicate_lookup_failed:${response.status}:${await response.text()}`);
  }
  const rows = await response.json();
  return rows?.[0]?.id || null;
}

async function insertRawDocument(payload: Record<string, unknown>): Promise<Record<string, unknown>> {
  const response = await supabaseFetch("mf_raw_documents", {
    method: "POST",
    headers: { "Prefer": "return=representation" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(`raw_document_insert_failed:${response.status}:${await response.text()}`);
  }
  const rows = await response.json();
  return rows[0] || {};
}

async function supabaseFetch(path: string, init: RequestInit): Promise<Response> {
  const supabaseUrl = requiredEnv("SUPABASE_URL").replace(/\/+$/, "");
  const serviceKey = requiredEnv("SUPABASE_SERVICE_ROLE_KEY");
  const headers = new Headers(init.headers);
  headers.set("apikey", serviceKey);
  headers.set("Authorization", `Bearer ${serviceKey}`);
  headers.set("Content-Type", "application/json");
  return fetch(`${supabaseUrl}/rest/v1/${path}`, {
    ...init,
    headers,
  });
}

function normalizeDocuments(source: AmcSource, body: Record<string, unknown>): DocumentInput[] {
  const bodyDocs = Array.isArray(body.documents) ? body.documents as DocumentInput[] : [];
  if (bodyDocs.length) {
    return bodyDocs;
  }

  const docs: DocumentInput[] = [];
  const envPrefix = `MF_${source.code}`;
  for (const [documentType, suffix] of [["factsheet", "FACTSHEET"], ["portfolio_disclosure", "PORTFOLIO"]] as const) {
    const urls = splitUrls(Deno.env.get(`${envPrefix}_${suffix}_DOCUMENT_URLS`) || "");
    for (const sourceUrl of urls) {
      docs.push({
        document_type: documentType,
        source_url: sourceUrl,
        reuse_as_portfolio: documentType === "factsheet" && truthy(Deno.env.get("MF_ALLOW_FACTSHEET_AS_PORTFOLIO")),
      });
    }
  }
  return docs;
}

async function discoverOfficialDocuments(source: AmcSource, body: Record<string, unknown>): Promise<DocumentInput[]> {
  const maxDocuments = positiveInt(body.max_documents, positiveInt(Deno.env.get("MF_EDGE_MAX_DISCOVERED_DOCUMENTS"), 4));
  const pages = [
    {
      documentType: "factsheet",
      url: String(body.factsheet_page_url || Deno.env.get(`MF_${source.code}_FACTSHEET_PAGE_URL`) || source.factsheetPageUrl),
    },
    {
      documentType: "portfolio_disclosure",
      url: String(body.portfolio_page_url || Deno.env.get(`MF_${source.code}_PORTFOLIO_PAGE_URL`) || source.portfolioPageUrl),
    },
  ];

  const candidates: DiscoveryCandidate[] = [];
  for (const page of pages) {
    candidates.push(...await discoverDocumentsFromPage(source, page.url, page.documentType));
  }

  return dedupeDiscoveryCandidates(candidates)
    .sort((left, right) => right.score - left.score)
    .slice(0, maxDocuments)
    .map(({ score: _score, ...doc }) => doc);
}

async function discoverDocumentsFromPage(source: AmcSource, pageUrl: string, documentType: string): Promise<DiscoveryCandidate[]> {
  const officialUrlIssue = validateOfficialUrl(source, pageUrl);
  if (officialUrlIssue) {
    return [];
  }
  const pageExt = normalizeExtension(pageUrl, "");
  if (pageExt) {
    return [{
      document_type: documentType,
      source_url: pageUrl,
      discovery_page_url: pageUrl,
      expected_file_type: pageExt,
      report_month: detectReportMonth(pageUrl) || undefined,
      score: scoreDiscoveredDocument(documentType, pageUrl, pageUrl),
    }];
  }

  const response = await fetch(pageUrl, {
    headers: {
      "User-Agent": Deno.env.get("MF_USER_AGENT") || "Mozilla/5.0 FundersAI/1.0",
      "Accept": "text/html,application/xhtml+xml,application/json,*/*",
      "Referer": source.baseUrl,
    },
  });
  if (!response.ok) {
    return [];
  }

  const pageText = await response.text();
  const candidates = [
    ...extractAnchorDocumentLinks(source, pageUrl, pageText, documentType),
    ...extractTextDocumentLinks(source, pageUrl, pageText, documentType),
  ];
  return dedupeDiscoveryCandidates(candidates);
}

function extractAnchorDocumentLinks(source: AmcSource, pageUrl: string, pageText: string, documentType: string): DiscoveryCandidate[] {
  const candidates: DiscoveryCandidate[] = [];
  const anchorPattern = /<a\b[^>]*href\s*=\s*["']([^"']+)["'][^>]*>([\s\S]*?)<\/a>/gi;
  for (const match of pageText.matchAll(anchorPattern)) {
    const sourceUrl = normalizeDiscoveredUrl(pageUrl, match[1]);
    const title = stripHtml(match[2]);
    const candidate = buildDiscoveryCandidate(source, pageUrl, sourceUrl, title, documentType);
    if (candidate) {
      candidates.push(candidate);
    }
  }
  return candidates;
}

function extractTextDocumentLinks(source: AmcSource, pageUrl: string, pageText: string, documentType: string): DiscoveryCandidate[] {
  const candidates: DiscoveryCandidate[] = [];
  const urlPattern = /https?:\\?\/\\?\/[^\s"'<>]+?\.(?:pdf|xlsx?|xlsm)(?:\?[^\s"'<>]*)?/gi;
  for (const match of pageText.matchAll(urlPattern)) {
    const sourceUrl = normalizeDiscoveredUrl(pageUrl, match[0]);
    const candidate = buildDiscoveryCandidate(source, pageUrl, sourceUrl, match[0], documentType);
    if (candidate) {
      candidates.push(candidate);
    }
  }
  return candidates;
}

function buildDiscoveryCandidate(
  source: AmcSource,
  discoveryPageUrl: string,
  sourceUrl: string,
  title: string,
  documentType: string,
): DiscoveryCandidate | null {
  if (!sourceUrl || validateOfficialUrl(source, sourceUrl)) {
    return null;
  }
  const fileExt = normalizeExtension(sourceUrl, "");
  if (!EXT_TO_CONTENT_TYPE[fileExt]) {
    return null;
  }
  const text = `${title} ${sourceUrl}`;
  const score = scoreDiscoveredDocument(documentType, title, sourceUrl);
  if (score <= 0) {
    return null;
  }
  return {
    document_type: documentType,
    source_url: sourceUrl,
    discovery_page_url: discoveryPageUrl,
    expected_file_type: fileExt,
    report_month: detectReportMonth(text) || undefined,
    title: title || fileNameFromUrl(sourceUrl, fileExt),
    reuse_as_portfolio: documentType === "factsheet" && truthy(Deno.env.get("MF_ALLOW_FACTSHEET_AS_PORTFOLIO")),
    score,
  };
}

function scoreDiscoveredDocument(documentType: string, title: string, sourceUrl: string): number {
  const text = `${title} ${sourceUrl}`.toLowerCase();
  const reportMonth = detectReportMonth(text);
  let score = reportMonth ? Number(reportMonth.slice(0, 4)) * 12 + Number(reportMonth.slice(5, 7)) : 0;

  if (documentType === "factsheet") {
    if (/\bfact[\s_-]*sheet\b|\bfactsheet\b|\bfundamentals\b/.test(text)) score += 10000;
    if (/\bportfolio\b|\bholding\b|\bdisclosure\b/.test(text)) score -= 5000;
  } else {
    if (/\bportfolio\b|\bholding\b|\bdisclosure\b/.test(text)) score += 10000;
    if (/\bfact[\s_-]*sheet\b|\bfactsheet\b|\bfundamentals\b/.test(text)) score -= 5000;
  }

  if (/\bmonthly\b|\bmonth\b/.test(text)) score += 250;
  return score;
}

function dedupeDiscoveryCandidates(candidates: DiscoveryCandidate[]): DiscoveryCandidate[] {
  const bestByUrl = new Map<string, DiscoveryCandidate>();
  for (const candidate of candidates) {
    const key = String(candidate.source_url || "").toLowerCase();
    const existing = bestByUrl.get(key);
    if (!existing || candidate.score > existing.score) {
      bestByUrl.set(key, candidate);
    }
  }
  return [...bestByUrl.values()];
}

function normalizeDiscoveredUrl(pageUrl: string, rawValue: string): string {
  const cleaned = htmlDecode(String(rawValue || ""))
    .replaceAll("\\/", "/")
    .replace(/^["']+|["']+$/g, "")
    .trim();
  if (!cleaned) {
    return "";
  }
  try {
    return new URL(cleaned, pageUrl).toString();
  } catch {
    return "";
  }
}

function stripHtml(value: string): string {
  return htmlDecode(String(value || "").replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim());
}

function htmlDecode(value: string): string {
  return value
    .replaceAll("&amp;", "&")
    .replaceAll("&quot;", '"')
    .replaceAll("&#39;", "'")
    .replaceAll("&lt;", "<")
    .replaceAll("&gt;", ">");
}

function validateOfficialUrl(source: AmcSource, sourceUrl: string): string | null {
  let url: URL;
  try {
    url = new URL(sourceUrl);
  } catch {
    return "invalid_url";
  }
  if (!["http:", "https:"].includes(url.protocol)) {
    return "invalid_url_scheme";
  }
  const host = url.hostname.toLowerCase();
  if (BLOCKED_HOSTS.some((blocked) => host === blocked || host.endsWith(`.${blocked}`))) {
    return "third_party_source_blocked";
  }
  const official = source.allowedHostSuffixes.some((suffix) => host === suffix || host.endsWith(`.${suffix}`));
  return official ? null : "non_official_host";
}

function buildStorageKey(amcCode: string, reportMonth: string | null, documentType: string, fileName: string, checksum: string): string {
  const month = reportMonth ? reportMonth.slice(0, 7) : "unknown-month";
  const ext = normalizeExtension(fileName, "");
  const stem = safePart(fileName.replace(/\.[^.]+$/, "")).slice(0, 80) || "document";
  return [
    "raw",
    safePart(amcCode.toLowerCase()),
    safePart(month),
    safePart(documentType),
    `${stem}-${checksum.slice(0, 12)}${ext}`,
  ].join("/");
}

function fileNameFromUrl(sourceUrl: string, fileExt: string): string {
  const url = new URL(sourceUrl);
  const candidate = decodeURIComponent(url.pathname.split("/").pop() || "").trim();
  if (candidate && /\.[a-z0-9]{2,5}$/i.test(candidate)) {
    return safeFileName(candidate);
  }
  return `official-document${fileExt}`;
}

function normalizeExtension(value: unknown, contentType = ""): string {
  const text = String(value || "").toLowerCase().split("?")[0];
  const match = text.match(/\.(pdf|xlsx?|xlsm)$/i);
  if (match) {
    return `.${match[1].toLowerCase()}`;
  }
  if (contentType.includes("pdf")) return ".pdf";
  if (contentType.includes("spreadsheetml")) return ".xlsx";
  if (contentType.includes("excel")) return ".xls";
  return "";
}

function normalizeContentType(value: string | null): string {
  return String(value || "").split(";")[0].trim().toLowerCase();
}

function validateBodyShape(bytes: Uint8Array, fileExt: string): string | null {
  if (fileExt === ".pdf" && bytesToAscii(bytes.slice(0, 5)) !== "%PDF-") {
    return "invalid_pdf_body";
  }
  if ((fileExt === ".xlsx" || fileExt === ".xlsm") && bytesToAscii(bytes.slice(0, 2)) !== "PK") {
    return "invalid_xlsx_body";
  }
  return null;
}

function looksLikeHtml(bytes: Uint8Array): boolean {
  const head = bytesToAscii(bytes.slice(0, 256)).trim().toLowerCase();
  return head.startsWith("<!doctype html") || head.startsWith("<html") || head.includes("<title>");
}

function bytesToAscii(bytes: Uint8Array): string {
  return new TextDecoder("utf-8", { fatal: false }).decode(bytes);
}

async function sha256Hex(bytes: Uint8Array): Promise<string> {
  const hash = new Uint8Array(await crypto.subtle.digest("SHA-256", bytes));
  return [...hash].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

function normalizeReportMonth(value: unknown): string | null {
  const text = String(value || "").trim();
  const match = text.match(/^(\d{4})-(\d{2})(?:-\d{2})?$/);
  return match ? `${match[1]}-${match[2]}-01` : null;
}

function detectReportMonth(text: string): string | null {
  const lower = text.toLowerCase();
  const year = lower.match(/\b(20\d{2})\b/)?.[1];
  const months = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"];
  const monthIndex = months.findIndex((month) => lower.includes(month));
  if (!year || monthIndex < 0) return null;
  return `${year}-${String(monthIndex + 1).padStart(2, "0")}-01`;
}

function normalizeDocumentType(value: unknown): string {
  const text = String(value || "factsheet").trim().toLowerCase().replace(/[-\s]+/g, "_");
  if (text === "portfolio" || text === "monthly_portfolio") return "portfolio_disclosure";
  return text;
}

function normalizeAmc(value: string): string {
  return value.trim().toLowerCase();
}

function splitUrls(value: string): string[] {
  return value.split(/[\n,]+/).map((part) => part.trim()).filter(Boolean);
}

function truthy(value: unknown): boolean {
  return ["1", "true", "yes", "on"].includes(String(value || "").trim().toLowerCase());
}

function positiveInt(value: unknown, fallback: number): number {
  const parsed = Number.parseInt(String(value || ""), 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

function safePart(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9._-]+/g, "-").replace(/^-+|-+$/g, "");
}

function safeFileName(value: string): string {
  return value.replace(/[\\/:*?"<>|]+/g, "-").replace(/\s+/g, "-").slice(0, 120);
}

function requiredEnv(name: string): string {
  const value = Deno.env.get(name)?.trim();
  if (!value) {
    throw new Error(`${name.toLowerCase()}_not_configured`);
  }
  return value;
}

function jsonResponse(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload, null, 2), {
    status,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Headers": "authorization,content-type,x-edge-acquire-key",
      "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
    },
  });
}
