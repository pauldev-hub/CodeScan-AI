import client from "./apiClient";

const localFallbackFix = (finding) => {
  const original = finding?.code_snippet || "";
  const suggestion = finding?.fix_suggestion || "No fix suggestion provided.";
  const commentPrefix = finding?.input_language === "python" ? "#" : "//";
  const header = `${commentPrefix} Generated local fallback fix`;
  const comment = `${commentPrefix} ${suggestion}`;

  return {
    source: "fallback",
    before: original || "// Original code unavailable for this finding",
    after: `${header}\n${comment}\n${original || ""}`.trim(),
    message: "Backend fix endpoint unavailable; generated a local fallback preview from suggestion text.",
    language: finding?.input_language || "javascript",
    change_summary: ["Inserted the stored fix suggestion above the original code snippet."],
    edit_hints: ["Use Edit code to tailor the fix before applying it in your real file."],
    diff_stats: {
      before_lines: (original || "").split("\n").length,
      after_lines: (`${header}\n${comment}\n${original || ""}`.trim()).split("\n").length,
      added_lines: 2,
      removed_lines: 0,
      changed_lines: 0,
    },
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
      language: response.data?.language || finding?.input_language || "javascript",
      change_summary: response.data?.change_summary || [],
      rationale: response.data?.rationale || [],
      edit_hints: response.data?.edit_hints || [],
      diff_stats: response.data?.diff_stats || null,
    };
  } catch {
    return localFallbackFix(finding);
  }
};
