import client from "./apiClient";

const localFallbackFix = (finding) => {
  const original = finding?.code_snippet || "";
  const suggestion = finding?.fix_suggestion || "No fix suggestion provided.";
  const header = "// Generated local fallback fix";
  const comment = `// ${suggestion}`;

  return {
    source: "fallback",
    before: original || "// Original code unavailable for this finding",
    after: `${header}\n${comment}\n${original || ""}`.trim(),
    message: "Backend fix endpoint unavailable; generated a local fallback preview from suggestion text.",
  };
};

export const requestFixPreview = async ({ scanId, finding }) => {
  try {
    const response = await client.post(`/api/scan/${scanId}/fix-preview`, {
      finding_id: finding?.id,
      file_path: finding?.file_path,
      line_number: finding?.line_number,
      code_snippet: finding?.code_snippet,
      suggestion: finding?.fix_suggestion,
    });
    return {
      source: "api",
      before: response.data?.before || finding?.code_snippet || "",
      after: response.data?.after || "",
      message: response.data?.message || "Fix preview generated.",
    };
  } catch {
    return localFallbackFix(finding);
  }
};
